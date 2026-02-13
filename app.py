"""
RV Camping Finder — Flask Web Application

Usage:
    python app.py
    # Opens at http://localhost:5000
"""

import os
import time
import threading
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, g, jsonify, send_file
import db
import stats

PST = timezone(timedelta(hours=-8))

# Simple in-memory rate limiter for API endpoints
_rate_lock = threading.Lock()
_rate_buckets = {}  # ip -> [timestamps]
API_RATE_LIMIT = 60   # requests per window
API_RATE_WINDOW = 60   # seconds


def _check_rate_limit(ip):
    """Return (allowed, remaining, retry_after). Prunes stale entries."""
    now = time.monotonic()
    cutoff = now - API_RATE_WINDOW
    with _rate_lock:
        hits = _rate_buckets.get(ip, [])
        hits = [t for t in hits if t > cutoff]
        if len(hits) >= API_RATE_LIMIT:
            retry = hits[0] - cutoff
            _rate_buckets[ip] = hits
            return False, 0, retry
        hits.append(now)
        _rate_buckets[ip] = hits
        # Prune stale IPs periodically (keep dict from growing unbounded)
        if len(_rate_buckets) > 5000:
            stale = [k for k, v in _rate_buckets.items()
                     if not v or v[-1] < cutoff]
            for k in stale:
                del _rate_buckets[k]
        return True, API_RATE_LIMIT - len(hits), 0

# Winter months where seasonal/winter-closure campgrounds are likely closed
WINTER_MONTHS = {11, 12, 1, 2, 3, 4}  # Nov–Apr

app = Flask(__name__)


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net https://connect.facebook.net; "
        "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
        "img-src 'self' https://*.tile.openstreetmap.org https://cdn.recreation.gov https://www.facebook.com data:; "
        "connect-src 'self' https://raw.githubusercontent.com https://www.facebook.com https://script.google.com; "
        "font-src 'self'"
    )
    return response

AMENITY_FILTERS = [
    ("FULL_HOOKUPS",     "Full Hookups"),
    ("ELECTRIC_HOOKUP",  "Electric Hookup"),
    ("50_AMP",           "50 Amp"),
    ("WATER_HOOKUP",     "Water Hookup"),
    ("PULL_THROUGH",     "Pull-Through Sites"),
    ("BIG_RIG_FRIENDLY", "Big Rig Friendly"),
    ("PAVED_ACCESS",     "Paved Access"),
    ("DUMP_STATION",     "Dump Station"),
    ("POTABLE_WATER",    "Potable Water"),
    ("RESERVABLE",       "Reservable"),
]

ROAD_ACCESS_OPTIONS = [
    ("PAVED",          "Paved"),
    ("GRAVEL",         "Gravel"),
    ("DIRT",           "Dirt"),
    ("HIGH_CLEARANCE", "High Clearance"),
    ("4WD_REQUIRED",   "4WD Required"),
]

SEASONAL_OPTIONS = [
    ("OPEN_YEAR_ROUND",      "Open Year-Round"),
    ("SEASONAL_CLOSURE",     "Seasonal Closure"),
    ("WINTER_CLOSURE",       "Winter Closure"),
    ("TEMPORARILY_CLOSED",   "Temporarily Closed"),
    ("PERMANENTLY_CLOSED",   "Permanently Closed"),
]

FIRE_OPTIONS = [
    ("CAMPFIRES_ALLOWED", "Campfires Allowed"),
    ("RESTRICTIONS",      "Fire Restrictions"),
    ("NO_CAMPFIRES",      "No Campfires"),
]

CAMPING_TYPES = [
    ("DEVELOPED",  "Developed Campgrounds"),
    ("PRIMITIVE",  "Primitive Campgrounds"),
    ("DISPERSED",  "Dispersed / Boondocking"),
]

AGENCIES = [
    ("FS",    "USDA Forest Service"),
    ("BLM",   "Bureau of Land Management"),
    ("USACE", "US Army Corps of Engineers"),
    ("NPS",   "National Park Service"),
    ("BOR",   "Bureau of Reclamation"),
    ("FWS",   "US Fish & Wildlife Service"),
]


@app.context_processor
def inject_now():
    now = datetime.now(PST)
    return {"now_pst": now, "current_month": now.month}


@app.before_request
def before_request():
    # Rate-limit API endpoints (60 req/min per IP)
    if request.path.startswith("/api/"):
        ip = request.remote_addr
        allowed, remaining, retry_after = _check_rate_limit(ip)
        if not allowed:
            resp = jsonify({"error": "rate limit exceeded"})
            resp.status_code = 429
            resp.headers["Retry-After"] = str(int(retry_after) + 1)
            return resp
    g.conn = db.get_connection()


@app.teardown_request
def teardown_request(exception):
    conn = getattr(g, "conn", None)
    if conn:
        conn.close()


@app.route("/")
def index():
    states = db.get_states(g.conn)
    state_counts = {s["state_code"]: s["facility_count"] for s in states}
    return render_template("map.html", state_counts=state_counts)


@app.route("/search-form")
def search_form():
    states = db.get_states(g.conn)
    return render_template("index.html",
                           states=states,
                           amenity_filters=AMENITY_FILTERS,
                           camping_types=CAMPING_TYPES,
                           agencies=AGENCIES,
                           road_access_options=ROAD_ACCESS_OPTIONS,
                           seasonal_options=SEASONAL_OPTIONS,
                           fire_options=FIRE_OPTIONS)


@app.route("/search")
def search():
    states = [s.strip() for s in request.args.getlist("state") if s.strip()]
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius = request.args.get("radius", 100, type=float)
    ct = request.args.getlist("camping_type")
    tags = request.args.getlist("tag")
    agencies = request.args.getlist("agency")
    road_access = request.args.getlist("road_access")
    seasonal = request.args.getlist("seasonal_status")
    fire = request.args.getlist("fire_status")
    rv_length = request.args.get("rv_length", type=int)
    page = request.args.get("page", 1, type=int)
    view = request.args.get("view", "list")

    if not ct:
        ct = ["DEVELOPED"]

    offset = (page - 1) * 25

    filter_kwargs = dict(
        camping_types=ct, tag_filters=tags, agencies=agencies,
        road_access=road_access or None,
        seasonal_status=seasonal or None,
        fire_status=fire or None,
        min_rv_length=rv_length,
    )

    if lat is not None and lon is not None:
        results = db.search_by_location(
            g.conn, lat, lon, radius,
            limit=25, offset=offset, **filter_kwargs)
        total = db.get_search_count(
            g.conn, lat=lat, lon=lon, radius_miles=radius, **filter_kwargs)
        search_desc = f"Within {int(radius)} miles of {lat:.2f}, {lon:.2f}"
    elif states:
        results = db.search_by_state(
            g.conn, states,
            limit=25, offset=offset, **filter_kwargs)
        total = db.get_search_count(
            g.conn, state_codes=states, **filter_kwargs)
        search_desc = "States: " + ", ".join(states) if len(states) > 1 else f"State: {states[0]}"
    else:
        results = []
        total = 0
        search_desc = ""

    has_more = (offset + len(results)) < total

    ctx = dict(
        results=results, total=total, page=page, has_more=has_more,
        states=states, lat=lat, lon=lon,
        radius=radius, camping_types=ct, tag_filters=tags,
        selected_agencies=agencies,
        selected_road_access=road_access,
        selected_seasonal=seasonal,
        selected_fire=fire,
        rv_length=rv_length,
        search_desc=search_desc,
        view=view,
        amenity_filters=AMENITY_FILTERS,
        camping_type_options=CAMPING_TYPES,
        agency_options=AGENCIES,
        road_access_options=ROAD_ACCESS_OPTIONS,
        seasonal_options=SEASONAL_OPTIONS,
        fire_options=FIRE_OPTIONS,
    )

    # htmx partial
    if request.headers.get("HX-Request"):
        return render_template("_results_cards.html", **ctx)

    return render_template("results.html", **ctx)


@app.route("/facility/<facility_id>")
def facility(facility_id):
    data = db.get_facility(g.conn, facility_id)
    if not data:
        return render_template("404.html"), 404

    nearby = db.get_nearby(
        g.conn, facility_id,
        data.get("latitude"), data.get("longitude"))

    return render_template("facility.html", f=data, nearby=nearby)


@app.route("/map")
def map_view():
    """Redirect /map to / (map is now the home page)."""
    from flask import redirect, url_for
    return redirect(url_for("index"))


@app.route("/api/pins")
def api_pins():
    states = [s.strip() for s in request.args.getlist("state") if s.strip()]
    if not states:
        return jsonify([])
    ct = request.args.getlist("camping_type") or ["DEVELOPED", "PRIMITIVE", "DISPERSED"]
    results = db.search_by_state(g.conn, states, camping_types=ct, limit=500, offset=0)
    pins = []
    for r in results:
        if r.get("latitude") and r.get("longitude"):
            pins.append({
                "facility_id": r["facility_id"],
                "facility_name": r["facility_name"],
                "latitude": r["latitude"],
                "longitude": r["longitude"],
                "camping_type": r.get("camping_type"),
                "total_campsites": r.get("total_campsites", 0),
                "road_access": r.get("road_access"),
                "org_abbrev": r.get("org_abbrev"),
                "seasonal_status": r.get("seasonal_status"),
            })
    return jsonify(pins)


@app.route("/api/search")
def api_search():
    states = [s.strip() for s in request.args.getlist("state") if s.strip()]
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius = request.args.get("radius", 100, type=float)
    ct = request.args.getlist("camping_type")
    tags = request.args.getlist("tag")
    agencies = request.args.getlist("agency")
    road_access = request.args.getlist("road_access")
    seasonal = request.args.getlist("seasonal_status")
    fire = request.args.getlist("fire_status")
    rv_length = request.args.get("rv_length", type=int)
    limit = min(request.args.get("limit", 25, type=int), 100)
    offset = request.args.get("offset", 0, type=int)

    if not ct:
        ct = ["DEVELOPED"]

    filter_kwargs = dict(
        camping_types=ct, tag_filters=tags, agencies=agencies,
        road_access=road_access or None,
        seasonal_status=seasonal or None,
        fire_status=fire or None,
        min_rv_length=rv_length,
    )

    if lat is not None and lon is not None:
        results = db.search_by_location(
            g.conn, lat, lon, radius,
            limit=limit, offset=offset, **filter_kwargs)
        total = db.get_search_count(
            g.conn, lat=lat, lon=lon, radius_miles=radius, **filter_kwargs)
    elif states:
        results = db.search_by_state(
            g.conn, states,
            limit=limit, offset=offset, **filter_kwargs)
        total = db.get_search_count(
            g.conn, state_codes=states, **filter_kwargs)
    else:
        return jsonify({"error": "state or lat/lon required"}), 400

    return jsonify({"total": total, "results": results})


@app.route("/api/facility/<facility_id>")
def api_facility(facility_id):
    data = db.get_facility(g.conn, facility_id)
    if not data:
        return jsonify({"error": "facility not found"}), 404
    return jsonify(data)


@app.route("/api/states")
def api_states():
    return jsonify(db.get_states(g.conn))


@app.route("/api/download")
def api_download():
    return send_file(db.DB_PATH, as_attachment=True, download_name="fedcamp.db")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/stats")
def site_stats():
    data = stats.get_stats()
    data["top_facilities"] = stats.resolve_facility_names(
        g.conn, data["top_facilities"])
    return render_template("stats.html", stats=data)


# Template filters
@app.template_filter("tag_display")
def tag_display(tag):
    return tag.replace("_", " ").title()


@app.template_filter("condition_color")
def condition_color(value):
    """Color for condition pills."""
    colors = {
        # Road access
        'PAVED': '#2d7d46', 'GRAVEL': '#6c757d', 'DIRT': '#d4782f',
        'HIGH_CLEARANCE': '#c0392b', '4WD_REQUIRED': '#c0392b',
        # Seasonal
        'OPEN_YEAR_ROUND': '#2d7d46', 'SEASONAL_CLOSURE': '#c49f17',
        'WINTER_CLOSURE': '#d4782f',
        'TEMPORARILY_CLOSED': '#c0392b', 'PERMANENTLY_CLOSED': '#7f1d1d',
        # Fire
        'CAMPFIRES_ALLOWED': '#2d7d46', 'RESTRICTIONS': '#c49f17',
        'NO_CAMPFIRES': '#c0392b',
        # Boondock
        'EASY': '#2d7d46', 'MODERATE': '#c49f17', 'ROUGH': '#c0392b',
        'UNKNOWN': '#95a5a6',
    }
    return colors.get(value, '#95a5a6')


@app.template_filter("likely_open")
def likely_open(seasonal_status):
    """Estimate if a campground is likely open right now based on PST month."""
    month = datetime.now(PST).month
    if seasonal_status == "OPEN_YEAR_ROUND":
        return True
    if seasonal_status in ("PERMANENTLY_CLOSED", "TEMPORARILY_CLOSED"):
        return False
    if seasonal_status in ("WINTER_CLOSURE", "SEASONAL_CLOSURE"):
        return month not in WINTER_MONTHS
    return None  # UNKNOWN


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "").lower() == "true", port=5000)
