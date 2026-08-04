"""
Campdex — Flask Web Application

Usage:
    python app.py
    # Opens at http://localhost:5000
"""

import os
import time
import threading
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
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


def _client_ip():
    """Return the real client IP for rate-limiting purposes.

    Behind Caddy -> gunicorn on 127.0.0.1, request.remote_addr is always
    127.0.0.1, which collapses the per-IP limit into one global bucket
    shared by every visitor. Cloudflare sets CF-Connecting-IP to the true
    client address and Caddy passes it through untouched.

    This trusts the incoming headers, which is only sound while the origin
    is reached exclusively through Cloudflare -- a client hitting the origin
    IP directly can forge them. Firewalling :80/:443 to Cloudflare's
    published ranges is what closes that gap.
    """
    cf = request.headers.get("CF-Connecting-IP")
    if cf:
        return cf.strip()
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        # Leftmost entry is the original client; the rest are proxy hops.
        return fwd.split(",")[0].strip()
    return request.remote_addr


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
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net https://connect.facebook.net https://www.googletagmanager.com https://www.google-analytics.com; "
        "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
        "img-src 'self' https://*.tile.openstreetmap.org https://cdn.recreation.gov https://unpkg.com https://www.facebook.com https://www.google-analytics.com https://www.googletagmanager.com data:; "
        "connect-src 'self' https://www.facebook.com https://script.google.com https://www.google-analytics.com https://*.google-analytics.com https://*.analytics.google.com https://www.googletagmanager.com; "
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
        ip = _client_ip()
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
    return render_template("map.html")


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

    # Next-page URL for the htmx "Load More" button. `page` must be stripped
    # from the incoming query string rather than appended to: an htmx request
    # for page 2 already carries page=2, so appending would build
    # "?page=2&page=3", and request.args.get("page") reads the first value —
    # pinning Load More on page 2 forever.
    next_args = request.args.to_dict(flat=False)
    next_args.pop("page", None)
    next_args["page"] = [page + 1]
    next_page_url = "/search?" + urlencode(next_args, doseq=True)

    ctx = dict(
        results=results, total=total, page=page, has_more=has_more,
        next_page_url=next_page_url,
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
    south = request.args.get("south", type=float)
    north = request.args.get("north", type=float)
    west = request.args.get("west", type=float)
    east = request.args.get("east", type=float)
    if None in (south, north, west, east):
        return jsonify({"error": "south, north, west, east required"}), 400

    ct = request.args.getlist("camping_type") or None
    agencies = request.args.getlist("agency") or None
    road_access = request.args.getlist("road_access") or None
    styles = request.args.getlist("style") or None
    hookups = request.args.getlist("hookup") or None
    min_rv = request.args.get("min_rv_length", type=int)

    pins = db.search_pins_by_bounds(
        g.conn, south, north, west, east,
        camping_types=ct, agencies=agencies,
        road_access=road_access, styles=styles,
        hookups=hookups, min_rv_length=min_rv)
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


# Acronyms / abbreviations to preserve when title-casing ALL-CAPS names
_TITLE_KEEP_UPPER = {
    "US", "USA", "BLM", "NPS", "FS", "USFS", "USACE", "BOR", "FWS",
    "RV", "ATV", "OHV", "NF", "NP", "NRA", "NWR", "SP", "CG", "II", "III",
    "IV", "VI", "VII", "VIII", "IX", "XI", "XII",
    "CCC",  # Civilian Conservation Corps — appears in several camp names
}

# Two-letter state codes that are also ordinary English words. In trailing
# position these are far more often the word than the state: real names include
# "JARVIES FAMILY BOAT IN" (boat-in, not Indiana) and "JOHN SPALDING REC AR"
# (Rec Area, not Arkansas). Still honoured inside parens, e.g. "NORTH FORK (WY)".
_AMBIGUOUS_STATE_CODES = {"IN", "OR", "AR", "ME", "HI", "OK", "LA", "PA", "DE"}

# State codes: only kept uppercase as the final word or right after a comma,
# so "WALK-IN" / "DRIVE IN" don't become "Walk-IN" / "Drive IN"
_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}

_TITLE_KEEP_LOWER = {"a", "an", "and", "at", "by", "de", "del", "for", "in",
                     "la", "of", "on", "or", "the", "to"}


@app.template_filter("smart_title")
def smart_title(name):
    """Title-case ALL-CAPS strings, preserving acronyms and state codes.

    Mixed-case strings are returned untouched.
    """
    if not name or not isinstance(name, str):
        return name
    letters = [c for c in name if c.isalpha()]
    if not letters or not all(c.isupper() for c in letters):
        return name  # already mixed-case (or no letters) — leave alone

    def fix_word(word, is_first, is_last, keep_state):
        # Core word without surrounding punctuation like ( ) , . / -
        core = word.strip("()[],.&/-'\"")
        if not core:
            return word
        if core in _TITLE_KEEP_UPPER:
            return word
        in_parens = word.startswith("(")
        if core in _STATE_CODES and (in_parens or
                                     (keep_state and
                                      core not in _AMBIGUOUS_STATE_CODES)):
            return word
        # Small words stay lowercase in the middle only — never as the first or
        # last word, or "BOAT IN" would render "Boat in".
        if not is_first and not is_last and core.lower() in _TITLE_KEEP_LOWER:
            return word.lower()
        # Handle hyphen/slash compounds (e.g. WALK-IN, PINE/OAK) and names
        # glued to an opening paren (BLUFF VIEW(CLEARWATER LAKE)). The
        # startswith guard keeps a standalone "(WY)" intact for the state
        # check above rather than splitting it into an empty first part.
        # Only the leading part inherits is_first, so WALK-IN -> Walk-in.
        for sep in ("-", "/", "("):
            if sep in word and not word.startswith(sep):
                parts = word.split(sep)
                return sep.join(
                    fix_word(p, is_first and i == 0,
                             is_last and i == len(parts) - 1, False)
                    for i, p in enumerate(parts))
        # O'BRIEN -> O'Brien (leading single letter + apostrophe)
        if "'" in word:
            head, _, tail = word.partition("'")
            if len(head) == 1 and len(tail) > 1:
                return head.upper() + "'" + fix_word(tail, False, is_last, False)
        # Capitalize first alphabetic char, lowercase the rest
        out, seen_alpha = [], False
        for c in word:
            if c.isalpha() and not seen_alpha:
                out.append(c.upper())
                seen_alpha = True
            else:
                out.append(c.lower())
        result = "".join(out)
        # McDonald, not Mcdonald. Every MC* word in the data (20 of them) is a
        # genuine surname. Mac is deliberately NOT handled: the only MAC* word
        # present is MACKINAW, which is correctly "Mackinaw", not "MacKinaw".
        if len(result) > 3 and result[:2] == "Mc" and result[2].isalpha():
            result = "Mc" + result[2].upper() + result[3:]
        return result

    words = name.split()
    fixed = []
    for i, w in enumerate(words):
        after_comma = i > 0 and words[i - 1].endswith(",")
        is_last = i == len(words) - 1
        keep_state = is_last or after_comma
        fixed.append(fix_word(w, i == 0, is_last, keep_state))
    return " ".join(fixed)


@app.template_filter("condition_color")
def condition_color(value):
    """Color for condition pills."""
    # All backgrounds meet WCAG AA (>= 4.5:1) against white pill text:
    #   #2d7d46 5.08:1, #6c757d 4.69:1, #a85a1e 5.06:1, #c0392b 5.44:1,
    #   #8a6d10 4.91:1, #7f1d1d 10.02:1, #5f6e6f 5.32:1
    colors = {
        # Road access
        'PAVED': '#2d7d46', 'GRAVEL': '#6c757d', 'DIRT': '#a85a1e',
        'HIGH_CLEARANCE': '#c0392b', '4WD_REQUIRED': '#c0392b',
        # Seasonal
        'OPEN_YEAR_ROUND': '#2d7d46', 'SEASONAL_CLOSURE': '#8a6d10',
        'WINTER_CLOSURE': '#a85a1e',
        'TEMPORARILY_CLOSED': '#c0392b', 'PERMANENTLY_CLOSED': '#7f1d1d',
        # Fire
        'CAMPFIRES_ALLOWED': '#2d7d46', 'RESTRICTIONS': '#8a6d10',
        'NO_CAMPFIRES': '#c0392b',
        # Boondock
        'EASY': '#2d7d46', 'MODERATE': '#8a6d10', 'ROUGH': '#c0392b',
        'UNKNOWN': '#5f6e6f',
    }
    return colors.get(value, '#5f6e6f')


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
