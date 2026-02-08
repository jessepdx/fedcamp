"""
Pull remaining useful endpoints: links, activities, permitentrances
"""
import requests
import sqlite3
import time
import sys
import os

API_KEY = os.environ.get("RIDB_API_KEY", "")
BASE = "https://ridb.recreation.gov/api/v1"
HDR = {"apikey": API_KEY, "accept": "application/json"}
DB_PATH = "ridb.db"
REQUEST_INTERVAL = 1.35

last_request_time = 0

def rate_limit():
    global last_request_time
    elapsed = time.time() - last_request_time
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    last_request_time = time.time()

def fetch(endpoint, retries=3):
    for attempt in range(retries):
        rate_limit()
        try:
            r = requests.get(f"{BASE}{endpoint}", headers=HDR, timeout=30)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"\n  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"\n  ERROR {r.status_code}: {r.text[:200]}")
                if attempt < retries - 1:
                    time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"\n  Request error: {e}")
            if attempt < retries - 1:
                time.sleep(5)
    return None

def init_tables(conn):
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS links (
            entity_link_id TEXT PRIMARY KEY,
            entity_id TEXT,
            entity_type TEXT,
            link_type TEXT,
            title TEXT,
            description TEXT,
            url TEXT
        );

        CREATE TABLE IF NOT EXISTS activities (
            activity_id INTEGER PRIMARY KEY,
            activity_name TEXT,
            activity_level INTEGER,
            activity_parent_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS permit_entrances (
            permit_entrance_id TEXT PRIMARY KEY,
            facility_id TEXT,
            permit_entrance_name TEXT,
            permit_entrance_type TEXT,
            permit_entrance_description TEXT,
            district TEXT,
            town TEXT,
            latitude REAL,
            longitude REAL,
            is_active INTEGER,
            created_date TEXT,
            last_updated TEXT
        );
    """)
    conn.commit()

def pull_paginated(endpoint, table_name, row_fn, conn):
    """Generic paginated puller"""
    c = conn.cursor()
    offset = 0
    limit = 50
    total = None
    count = 0
    start = time.time()

    while True:
        data = fetch(f"{endpoint}?limit={limit}&offset={offset}")
        if not data or not data.get("RECDATA") or len(data["RECDATA"]) == 0:
            break

        if total is None:
            total = data["METADATA"]["RESULTS"]["TOTAL_COUNT"]
            print(f"  Total: {total:,}")

        for rec in data["RECDATA"]:
            row_fn(c, rec)
            count += 1

        conn.commit()

        elapsed = time.time() - start
        rate = count / elapsed if elapsed > 0 else 0
        eta = (total - count) / rate / 60 if rate > 0 else 0
        pct = count / total * 100 if total else 0
        print(f"  [{pct:5.1f}%] {count:,}/{total:,} | ETA: {eta:.0f}min", end="\r")
        sys.stdout.flush()

        if len(data["RECDATA"]) < limit:
            break
        offset += limit

    elapsed = time.time() - start
    print(f"\n  Done! {count:,} {table_name} in {elapsed/60:.1f} minutes")

def insert_link(c, rec):
    c.execute("""INSERT OR REPLACE INTO links
        (entity_link_id, entity_id, entity_type, link_type, title, description, url)
        VALUES (?, ?, ?, ?, ?, ?, ?)""", (
        rec.get("EntityLinkID"), rec.get("EntityID"), rec.get("EntityType"),
        rec.get("LinkType"), rec.get("Title"), rec.get("Description"), rec.get("URL")
    ))

def insert_activity(c, rec):
    c.execute("""INSERT OR REPLACE INTO activities
        (activity_id, activity_name, activity_level, activity_parent_id)
        VALUES (?, ?, ?, ?)""", (
        rec.get("ActivityID"), rec.get("ActivityName"),
        rec.get("ActivityLevel"), rec.get("ActivityParentID")
    ))

def insert_permit(c, rec):
    c.execute("""INSERT OR REPLACE INTO permit_entrances
        (permit_entrance_id, facility_id, permit_entrance_name, permit_entrance_type,
         permit_entrance_description, district, town, latitude, longitude,
         is_active, created_date, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
        rec.get("PermitEntranceID"), rec.get("FacilityID"),
        rec.get("PermitEntranceName"), rec.get("PermitEntranceType"),
        rec.get("PermitEntranceDescription"), rec.get("District"),
        rec.get("Town"), rec.get("Latitude"), rec.get("Longitude"),
        1 if rec.get("IsActive") else 0,
        rec.get("CreatedDate"), rec.get("LastUpdatedDate")
    ))

def main():
    conn = sqlite3.connect(DB_PATH)
    init_tables(conn)

    print("=== PULLING LINKS ===")
    pull_paginated("/links", "links", insert_link, conn)

    print("\n=== PULLING ACTIVITIES ===")
    pull_paginated("/activities", "activities", insert_activity, conn)

    print("\n=== PULLING PERMIT ENTRANCES ===")
    pull_paginated("/permitentrances", "permit entrances", insert_permit, conn)

    # Summary
    c = conn.cursor()
    print("\n" + "=" * 50)
    for t in ["links", "activities", "permit_entrances"]:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t:25s}: {c.fetchone()[0]:>8,}")

    # Show link types
    print("\n  Link types:")
    c.execute("SELECT link_type, entity_type, COUNT(*) FROM links GROUP BY link_type, entity_type ORDER BY COUNT(*) DESC LIMIT 15")
    for r in c.fetchall():
        print(f"    {r[0]:30s} ({r[1]:10s}): {r[2]:>6,}")

    conn.close()

if __name__ == "__main__":
    main()
