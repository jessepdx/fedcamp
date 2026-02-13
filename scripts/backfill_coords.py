#!/usr/bin/env python3
"""
backfill_coords.py — Fetch coordinates for facilities with NULL lat/lon
from the recreation.gov campground API.

The RIDB API returns 0/0 for these facilities, but recreation.gov's
frontend API often has real coordinates.

Resumable via JSON cache. Run with --dry-run to preview without DB changes.

Usage:
    python scripts/backfill_coords.py              # scrape + update DB
    python scripts/backfill_coords.py --dry-run    # scrape only, no DB update
    python scripts/backfill_coords.py --apply-only # apply cached results to DB
"""

import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DB_PATH = "ridb.db"
CACHE_PATH = "scripts/coords_cache.json"
CAMPGROUND_API = "https://www.recreation.gov/api/camps/campgrounds/{}"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
REQUEST_DELAY = 1.0  # ~1 req/sec


def fetch_coords(facility_id):
    """Fetch coordinates from recreation.gov campground API.
    Returns (lat, lon) or (None, None).
    """
    url = CAMPGROUND_API.format(facility_id)
    req = Request(url, headers=HEADERS)
    for attempt in range(4):
        try:
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cg = data.get("campground", data)
                lat = cg.get("facility_latitude")
                lon = cg.get("facility_longitude")
                if lat and lon and lat != 0 and lon != 0:
                    return float(lat), float(lon)
                return None, None
        except HTTPError as e:
            if e.code in (400, 404):
                return None, None
            if e.code == 429:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
                continue
            return None, None
        except (URLError, TimeoutError, OSError):
            return None, None
    return None, None


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)


def get_missing_facilities(conn):
    rows = conn.execute("""
        SELECT facility_id, facility_name
        FROM n_facility_rollup
        WHERE camping_type IN ('DEVELOPED', 'PRIMITIVE', 'DISPERSED')
          AND latitude IS NULL
        ORDER BY facility_id
    """).fetchall()
    return [(str(r[0]), r[1]) for r in rows]


def scrape(conn):
    facilities = get_missing_facilities(conn)
    total = len(facilities)
    print(f"Facilities missing coords: {total}")

    cache = load_cache()
    already = sum(1 for fid, _ in facilities if fid in cache)
    if already:
        print(f"  {already} cached, {total - already} to scrape")

    to_scrape = [(fid, name) for fid, name in facilities if fid not in cache]
    if not to_scrape:
        print("  All cached — nothing to scrape")
        return cache

    est_min = len(to_scrape) * REQUEST_DELAY / 60
    print(f"\nScraping {len(to_scrape)} facilities (~{est_min:.0f} min)...\n")

    found = 0
    not_found = 0

    for i, (fid, name) in enumerate(to_scrape):
        lat, lon = fetch_coords(fid)
        cache[fid] = {"lat": lat, "lon": lon}

        if lat is not None:
            found += 1
            print(f"  [{i+1}/{len(to_scrape)}] {(name or 'Unknown')[:50]} -> ({lat:.4f}, {lon:.4f})")
        else:
            not_found += 1

        if (i + 1) % 50 == 0:
            save_cache(cache)
            print(f"  [{i+1}/{len(to_scrape)}] ... {found} found, {not_found} missing")

        time.sleep(REQUEST_DELAY)

    save_cache(cache)

    # Count totals across entire cache (including previously cached)
    all_found = sum(1 for v in cache.values() if v["lat"] is not None)
    all_missing = sum(1 for v in cache.values() if v["lat"] is None)
    print(f"\nDone. Total: {all_found} found, {all_missing} still missing")
    return cache


def apply_to_db(conn, cache):
    updates = [(v["lat"], v["lon"], int(k))
               for k, v in cache.items() if v["lat"] is not None]
    if not updates:
        print("No coordinates to update.")
        return

    print(f"\nUpdating {len(updates)} facilities in n_facility_rollup...")
    conn.executemany("""
        UPDATE n_facility_rollup
        SET latitude = ?, longitude = ?, coords_valid = 1
        WHERE facility_id = ?
    """, updates)
    conn.commit()

    # Verify
    remaining = conn.execute("""
        SELECT COUNT(*) FROM n_facility_rollup
        WHERE camping_type IN ('DEVELOPED', 'PRIMITIVE', 'DISPERSED')
          AND latitude IS NULL
    """).fetchone()[0]
    print(f"  Done. {remaining} facilities still missing coords.")


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    apply_only = "--apply-only" in args

    sys.stdout.reconfigure(line_buffering=True)

    print(f"Coordinate Backfill — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Source: recreation.gov campground API")
    if dry_run:
        print("Mode: DRY RUN")
    elif apply_only:
        print("Mode: APPLY ONLY")
    print()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if apply_only:
        cache = load_cache()
        if not cache:
            print("No cache found. Run scraper first.")
            conn.close()
            return 1
        print(f"Loaded {len(cache)} cached results")
    else:
        # Clear old RIDB API cache (all nulls)
        if os.path.exists(CACHE_PATH):
            old = load_cache()
            if old and all(v["lat"] is None for v in old.values()):
                print("Clearing stale RIDB cache (all nulls)...\n")
                os.remove(CACHE_PATH)
        cache = scrape(conn)

    if not dry_run:
        apply_to_db(conn, cache)

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
