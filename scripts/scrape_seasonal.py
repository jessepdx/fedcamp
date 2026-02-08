"""
Scrape Recreation.gov API for Seasonal/Closure Status

Queries the recreation.gov public API for campground notices and availability
data to reclassify facilities with UNKNOWN seasonal status.

Sources:
  1. Campground notices API — closure alerts, seasonal info, warnings
  2. Availability API (fallback) — per-site availability for current month

Results cached in scripts/seasonal_cache.json for resumability.
Database updates applied in a final batch.

Usage:
    python scripts/scrape_seasonal.py             # scrape + update DB
    python scripts/scrape_seasonal.py --dry-run    # scrape only, no DB update
    python scripts/scrape_seasonal.py --apply-only # apply cached results to DB
"""

import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DB_PATH = "ridb.db"
CACHE_PATH = "scripts/seasonal_cache.json"

CAMPGROUND_API = "https://www.recreation.gov/api/camps/campgrounds/{}"
AVAILABILITY_API = "https://www.recreation.gov/api/camps/availability/campground/{}/month?start_date={}"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

REQUEST_DELAY = 0.2  # seconds between requests (~5 req/sec)


# ============================================================
# NOTICE PARSING
# ============================================================

def classify_from_notices(notices):
    """Parse campground notices for seasonal/closure keywords.

    Returns (status, notice_text) or (None, None) if no match.
    """
    if not notices:
        return None, None

    # Combine all active notice texts
    texts = []
    for notice in notices:
        text = notice.get("notice_text", "") or ""
        if text:
            texts.append(text)

    if not texts:
        return None, None

    combined = " ".join(texts).lower()

    # Priority 1: Permanently closed
    if any(p in combined for p in (
        "permanently closed", "closed indefinitely",
        "closed until further notice",
    )):
        return "PERMANENTLY_CLOSED", " | ".join(texts)

    # Priority 2: Temporarily closed
    if any(p in combined for p in (
        "temporarily closed",
        "closed for the 2026 season",
        "closed for the 2025 season",
        "closed due to",
        "closed for construction",
        "closed for renovation",
        "closed for repair",
        "closed for restoration",
        "closed for rehabilitation",
    )):
        return "TEMPORARILY_CLOSED", " | ".join(texts)

    # "closed for the [year] season" — generic year
    if re.search(r"closed for the \d{4} season", combined):
        return "TEMPORARILY_CLOSED", " | ".join(texts)

    # Priority 3: Winter closure
    if any(p in combined for p in (
        "closed for the winter", "closed during winter",
        "winter closure", "snow closes",
        "snowfall closes", "closed due to snow",
        "closed when snow",
    )):
        return "WINTER_CLOSURE", " | ".join(texts)

    # Priority 4: Seasonal closure
    if any(p in combined for p in (
        "open from", "closed for the season",
        "seasonal campground", "seasonally",
        "seasonal closure", "typically open",
        "usually open", "open memorial",
    )):
        return "SEASONAL_CLOSURE", " | ".join(texts)

    # "Open [month] through [month]"
    if re.search(r"open\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+through", combined):
        return "SEASONAL_CLOSURE", " | ".join(texts)

    # Priority 5: Year-round
    if any(p in combined for p in (
        "open year-round", "open year round",
        "open all year", "year-round camping",
        "year round camping",
    )):
        return "OPEN_YEAR_ROUND", " | ".join(texts)

    return None, " | ".join(texts)


def classify_from_availability(availability_data):
    """Check availability API response for closure signals.

    Returns status string or None.
    """
    campsites = availability_data.get("campsites", {})

    if not campsites:
        return None  # no_data — FCFS or not on recreation.gov

    total_slots = 0
    not_available = 0
    available_or_reserved = 0
    not_reservable = 0

    for site_id, site_data in campsites.items():
        avails = site_data.get("availabilities", {})
        for date, status in avails.items():
            total_slots += 1
            if status == "Not Available":
                not_available += 1
            elif status in ("Available", "Reserved"):
                available_or_reserved += 1
            elif status == "Not Reservable":
                not_reservable += 1

    if total_slots == 0:
        return None

    # 100% Not Reservable — FCFS, no signal
    if not_reservable == total_slots:
        return None

    # Has bookable/booked sites — it's open
    if available_or_reserved > 0:
        return "OPEN_YEAR_ROUND"

    # 100% Not Available (excluding Not Reservable)
    reservable_slots = total_slots - not_reservable
    if reservable_slots > 0 and not_available >= reservable_slots:
        return "SEASONAL_CLOSURE"

    return None


# ============================================================
# API CALLS
# ============================================================

def fetch_json(url):
    """Fetch JSON from a URL with standard headers. Returns dict or None."""
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            return None
        raise
    except (URLError, TimeoutError):
        return None


def fetch_notices(facility_id):
    """Fetch campground notices from recreation.gov API."""
    url = CAMPGROUND_API.format(facility_id)
    data = fetch_json(url)
    if not data:
        return []

    campground = data.get("campground", data)
    notices = campground.get("notices", [])
    return notices


def fetch_availability(facility_id):
    """Fetch current month availability from recreation.gov API."""
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    date_str = quote(start.strftime("%Y-%m-%dT00:00:00.000Z"))
    url = AVAILABILITY_API.format(facility_id, date_str)
    return fetch_json(url)


# ============================================================
# CACHE
# ============================================================

def load_cache():
    """Load cached results from disk."""
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    """Save cache to disk."""
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


# ============================================================
# MAIN
# ============================================================

def get_unknown_facilities(conn):
    """Get campable facilities with UNKNOWN seasonal status."""
    rows = conn.execute("""
        SELECT r.facility_id, r.facility_name
        FROM n_facility_rollup r
        JOIN n_facility_conditions c ON r.facility_id = c.facility_id
        WHERE r.camping_type IN ('DEVELOPED', 'PRIMITIVE', 'DISPERSED')
          AND c.seasonal_status = 'UNKNOWN'
        ORDER BY r.facility_id
    """).fetchall()
    return [(str(r[0]), r[1]) for r in rows]


def scrape(conn, dry_run=False):
    """Scrape recreation.gov for seasonal data."""
    facilities = get_unknown_facilities(conn)
    print(f"Found {len(facilities):,} UNKNOWN campable facilities")

    cache = load_cache()
    already_cached = sum(1 for fid, _ in facilities if fid in cache)
    if already_cached:
        print(f"  {already_cached:,} already in cache, {len(facilities) - already_cached:,} to scrape")

    to_scrape = [(fid, name) for fid, name in facilities if fid not in cache]

    if not to_scrape:
        print("  Nothing to scrape — all facilities cached")
        return cache

    print(f"\nScraping {len(to_scrape):,} facilities (~{len(to_scrape) * REQUEST_DELAY / 60:.0f} min)...\n")

    classified = 0
    errors = 0
    notice_hits = 0
    avail_hits = 0

    for i, (fid, name) in enumerate(to_scrape):
        try:
            # Step 1: Check notices
            notices = fetch_notices(fid)
            status, notice_text = classify_from_notices(notices)
            source = "notice"

            if status:
                notice_hits += 1
            else:
                # Step 2: Fallback to availability
                time.sleep(REQUEST_DELAY)
                avail_data = fetch_availability(fid)
                if avail_data:
                    status = classify_from_availability(avail_data)
                    source = "availability"
                    if status:
                        avail_hits += 1

            cache[fid] = {
                "status": status,
                "source": source if status else "none",
                "notice_text": notice_text,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

            if status:
                classified += 1

            # Progress
            if (i + 1) % 100 == 0 or (i + 1) == len(to_scrape):
                pct = (i + 1) / len(to_scrape) * 100
                print(f"  [{i+1:>5,}/{len(to_scrape):,}] {pct:5.1f}%  classified={classified}  "
                      f"notice={notice_hits} avail={avail_hits} err={errors}")
                save_cache(cache)

        except Exception as e:
            errors += 1
            print(f"  ERROR facility {fid} ({name}): {e}")
            cache[fid] = {
                "status": None,
                "source": "error",
                "notice_text": str(e),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

        time.sleep(REQUEST_DELAY)

    save_cache(cache)
    print(f"\nScraping complete:")
    print(f"  Total scraped: {len(to_scrape):,}")
    print(f"  Classified:    {classified}")
    print(f"  From notices:  {notice_hits}")
    print(f"  From avail:    {avail_hits}")
    print(f"  Errors:        {errors}")

    return cache


def apply_to_db(conn, cache):
    """Apply cached results to n_facility_conditions."""
    updates = {fid: entry for fid, entry in cache.items() if entry.get("status")}

    if not updates:
        print("No reclassifications to apply")
        return

    print(f"\nApplying {len(updates):,} reclassifications to database...")

    # Count by status
    counts = {}
    for entry in updates.values():
        s = entry["status"]
        counts[s] = counts.get(s, 0) + 1

    for status, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {status:25s} {cnt:>5,}")

    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    for fid, entry in updates.items():
        c.execute("""
            UPDATE n_facility_conditions
            SET seasonal_status = ?, classified_at = ?
            WHERE facility_id = ?
        """, (entry["status"], now, fid))

    conn.commit()
    print(f"\n  Updated {c.rowcount if len(updates) == 1 else len(updates)} rows")

    # Print new distribution
    print("\n  --- New Seasonal Status Distribution (campable) ---")
    rows = conn.execute("""
        SELECT c.seasonal_status, COUNT(*)
        FROM n_facility_conditions c
        JOIN n_facility_rollup r ON c.facility_id = r.facility_id
        WHERE r.camping_type IN ('DEVELOPED', 'PRIMITIVE', 'DISPERSED')
        GROUP BY c.seasonal_status
        ORDER BY COUNT(*) DESC
    """).fetchall()
    for status, cnt in rows:
        print(f"  {status:25s} {cnt:>6,}")


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    apply_only = "--apply-only" in args

    print(f"Recreation.gov Seasonal Scraper — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {DB_PATH}")
    print(f"Cache:    {CACHE_PATH}")
    if dry_run:
        print("Mode:     DRY RUN (no DB updates)")
    elif apply_only:
        print("Mode:     APPLY ONLY (no scraping)")
    print()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if apply_only:
        cache = load_cache()
        if not cache:
            print("ERROR: No cache file found. Run scraper first.")
            conn.close()
            return 1
        print(f"Loaded {len(cache):,} cached results")
    else:
        cache = scrape(conn)

    if not dry_run:
        apply_to_db(conn, cache)

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
