"""
RV Camping Finder — Flask Web Application

Usage:
    python app.py
    # Opens at http://localhost:5000
"""

import os
from flask import Flask, render_template, request, g, jsonify
import db

app = Flask(__name__)


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
        "img-src 'self' https://*.tile.openstreetmap.org https://ridb-img.s3.us-west-2.amazonaws.com data:; "
        "connect-src 'self' https://raw.githubusercontent.com; "
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
    ("OPEN_YEAR_ROUND",   "Open Year-Round"),
    ("SEASONAL_CLOSURE",  "Seasonal Closure"),
    ("WINTER_CLOSURE",    "Winter Closure"),
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


@app.before_request
def before_request():
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
    state = request.args.get("state", "").strip()
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius = request.args.get("radius", 100, type=float)
    ct = request.args.getlist("camping_type")
    tags = request.args.getlist("tag")
    agencies = request.args.getlist("agency")
    road_access = request.args.getlist("road_access")
    seasonal = request.args.getlist("seasonal_status")
    fire = request.args.getlist("fire_status")
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
    )

    if lat is not None and lon is not None:
        results = db.search_by_location(
            g.conn, lat, lon, radius,
            limit=25, offset=offset, **filter_kwargs)
        total = db.get_search_count(
            g.conn, lat=lat, lon=lon, radius_miles=radius, **filter_kwargs)
        search_desc = f"Within {int(radius)} miles of {lat:.2f}, {lon:.2f}"
    elif state:
        results = db.search_by_state(
            g.conn, state,
            limit=25, offset=offset, **filter_kwargs)
        total = db.get_search_count(
            g.conn, state_code=state, **filter_kwargs)
        search_desc = f"State: {state}"
    else:
        results = []
        total = 0
        search_desc = ""

    has_more = (offset + len(results)) < total

    ctx = dict(
        results=results, total=total, page=page, has_more=has_more,
        state=state, lat=lat, lon=lon,
        radius=radius, camping_types=ct, tag_filters=tags,
        selected_agencies=agencies,
        selected_road_access=road_access,
        selected_seasonal=seasonal,
        selected_fire=fire,
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
    state = request.args.get("state", "").strip()
    if not state:
        return jsonify([])
    ct = request.args.getlist("camping_type") or ["DEVELOPED", "PRIMITIVE", "DISPERSED"]
    results = db.search_by_state(g.conn, state, camping_types=ct, limit=500, offset=0)
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
            })
    return jsonify(pins)


@app.route("/about")
def about():
    return render_template("about.html")


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
        # Fire
        'CAMPFIRES_ALLOWED': '#2d7d46', 'RESTRICTIONS': '#c49f17',
        'NO_CAMPFIRES': '#c0392b',
        # Boondock
        'EASY': '#2d7d46', 'MODERATE': '#c49f17', 'ROUGH': '#c0392b',
        'UNKNOWN': '#95a5a6',
    }
    return colors.get(value, '#95a5a6')


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "").lower() == "true", port=5000)
