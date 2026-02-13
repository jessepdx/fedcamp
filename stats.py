"""
stats.py — Caddy access log parser for site usage stats

Parses Caddy JSON access logs server-side and returns a stats dict.
5-minute in-memory cache to avoid re-parsing on every request.
No Flask dependency (same pattern as db.py).
"""

import glob
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs

PST = timezone(timedelta(hours=-8))

# Cache
_cache = {"data": None, "ts": 0}
CACHE_TTL = 300  # 5 minutes

# Default log directory (Caddy on Lightsail)
DEFAULT_LOG_DIR = "/var/log/caddy"

# Bot detection — common crawlers and bots
BOT_RE = re.compile(
    r"bot|crawl|spider|slurp|bingpreview|facebookexternalhit|"
    r"twitterbot|linkedinbot|embedly|quora|pinterest|redditbot|"
    r"applebot|yandex|semrush|ahref|mj12bot|dotbot|petalbot|"
    r"bytespider|gptbot|claudebot|chatgpt|ccbot|dataforseo|"
    r"google-inspectiontool|googleother",
    re.IGNORECASE,
)

# Paths to ignore (static assets, favicon, etc.)
IGNORE_RE = re.compile(
    r"^/static/|^/favicon|\.ico$|\.js$|\.css$|\.png$|\.jpg$|\.svg$|\.woff"
)


def get_stats():
    """Return cached stats dict. Re-parses logs if cache is stale."""
    now = time.time()
    if _cache["data"] and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]

    data = _parse_logs()
    _cache["data"] = data
    _cache["ts"] = now
    return data


def resolve_facility_names(conn, facility_counts):
    """Replace (facility_id, count) tuples with (id, name, count).

    Looks up names from n_facility_rollup. Returns list of dicts.
    """
    if not facility_counts:
        return []

    ids = [fc[0] for fc in facility_counts]
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        "SELECT facility_id, facility_name FROM n_facility_rollup "
        "WHERE facility_id IN ({})".format(placeholders),
        ids,
    ).fetchall()
    name_map = {str(r["facility_id"]): r["facility_name"] for r in rows}

    return [
        {
            "facility_id": fid,
            "facility_name": name_map.get(fid, f"Facility {fid}"),
            "count": count,
        }
        for fid, count in facility_counts
    ]


def _parse_logs():
    """Parse all Caddy JSON log files and return stats dict."""
    log_dir = os.environ.get("CADDY_LOG_DIR", DEFAULT_LOG_DIR)
    log_files = sorted(glob.glob(os.path.join(log_dir, "access.log*")))

    if not log_files:
        return _empty_stats()

    visitors = set()       # unique IPs (non-bot)
    page_views = Counter()  # path -> count
    api_requests = 0
    bot_count = 0
    facility_views = Counter()  # facility_id -> count
    state_searches = Counter()  # state_code -> count
    referrers = Counter()       # domain -> count
    daily_views = Counter()     # date_str -> count

    for log_file in log_files:
        try:
            with open(log_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    _process_entry(
                        entry, visitors, page_views, facility_views,
                        state_searches, referrers, daily_views,
                    )
                    # Count bots and API separately
                    req = entry.get("request", {})
                    ua = _get_ua(req)
                    uri = req.get("uri", "")

                    if BOT_RE.search(ua):
                        bot_count += 1
                        continue

                    if uri.startswith("/api/"):
                        api_requests += 1
        except (IOError, OSError):
            continue

    # Sort and limit top lists
    top_facilities = facility_views.most_common(10)
    top_states = state_searches.most_common(10)
    top_referrers = referrers.most_common(10)
    top_pages = page_views.most_common(10)

    # Daily views sorted by date
    sorted_days = sorted(daily_views.items())
    max_day = max(daily_views.values()) if daily_views else 0

    return {
        "unique_visitors": len(visitors),
        "total_page_views": sum(page_views.values()),
        "api_requests": api_requests,
        "bot_requests": bot_count,
        "top_facilities": top_facilities,
        "top_states": top_states,
        "top_referrers": top_referrers,
        "top_pages": top_pages,
        "views_by_day": sorted_days,
        "max_day_views": max_day,
        "log_days": len(daily_views),
        "generated_at": datetime.now(PST).strftime("%b %d, %Y %I:%M %p PST"),
        "has_data": True,
    }


def _process_entry(entry, visitors, page_views, facility_views,
                    state_searches, referrers, daily_views):
    """Process a single log entry, updating counters."""
    req = entry.get("request", {})
    uri = req.get("uri", "")
    ua = _get_ua(req)
    status = entry.get("status", 0)

    # Skip bots
    if BOT_RE.search(ua):
        return

    # Skip non-2xx
    if not (200 <= status < 400):
        return

    # Skip static assets
    if IGNORE_RE.search(uri):
        return

    # Skip API requests from page-view counting
    if uri.startswith("/api/"):
        return

    # Parse path (strip query string)
    path = uri.split("?")[0].rstrip("/") or "/"

    # Unique visitor
    ip = req.get("remote_ip", "")
    if ip:
        visitors.add(ip)

    # Page view
    page_views[path] += 1

    # Daily views
    ts = entry.get("ts", 0)
    if ts:
        try:
            dt = datetime.fromtimestamp(ts, tz=PST)
            daily_views[dt.strftime("%Y-%m-%d")] += 1
        except (OSError, ValueError, OverflowError):
            pass

    # Facility views
    if path.startswith("/facility/"):
        fid = path.split("/facility/")[-1]
        if fid and fid.isdigit():
            facility_views[fid] += 1

    # State searches (from query params)
    if path in ("/search", "/api/search", "/api/pins"):
        qs = uri.split("?", 1)[1] if "?" in uri else ""
        params = parse_qs(qs)
        for sc in params.get("state", []):
            sc = sc.strip().upper()
            if len(sc) == 2 and sc.isalpha():
                state_searches[sc] += 1

    # Referrer tracking
    referer = _get_header(req, "Referer") or _get_header(req, "referer")

    # Also detect Facebook via fbclid param
    if not referer and "fbclid" in uri:
        referer = "https://facebook.com"

    if referer:
        try:
            parsed = urlparse(referer)
            domain = parsed.hostname or ""
            # Skip self-referrals
            if domain and "fedcamp" not in domain and "localhost" not in domain:
                # Normalize Facebook domains
                if "facebook" in domain or "fbclid" in uri:
                    domain = "facebook.com"
                elif "reddit" in domain:
                    domain = "reddit.com"
                elif "google" in domain:
                    domain = "google.com"
                elif "t.co" == domain or "twitter" in domain or "x.com" == domain:
                    domain = "x.com"
                referrers[domain] += 1
        except (ValueError, AttributeError):
            pass


def _get_ua(req):
    """Extract User-Agent string from Caddy request headers."""
    headers = req.get("headers", {})
    ua_list = headers.get("User-Agent", [])
    if isinstance(ua_list, list) and ua_list:
        return ua_list[0]
    if isinstance(ua_list, str):
        return ua_list
    return ""


def _get_header(req, name):
    """Extract a single header value from Caddy request headers."""
    headers = req.get("headers", {})
    val = headers.get(name, [])
    if isinstance(val, list) and val:
        return val[0]
    if isinstance(val, str):
        return val
    return ""


def _empty_stats():
    """Return empty stats dict (no log files available)."""
    return {
        "unique_visitors": 0,
        "total_page_views": 0,
        "api_requests": 0,
        "bot_requests": 0,
        "top_facilities": [],
        "top_states": [],
        "top_referrers": [],
        "top_pages": [],
        "views_by_day": [],
        "max_day_views": 0,
        "log_days": 0,
        "generated_at": datetime.now(PST).strftime("%b %d, %Y %I:%M %p PST"),
        "has_data": False,
    }
