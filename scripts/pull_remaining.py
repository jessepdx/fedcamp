"""
Pull remaining data: media (288K), rec area activities, tours, events.
Get everything.
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
        CREATE TABLE IF NOT EXISTS media (
            entity_media_id TEXT PRIMARY KEY,
            entity_id TEXT,
            entity_type TEXT,
            media_type TEXT,
            url TEXT,
            title TEXT,
            subtitle TEXT,
            description TEXT,
            credits TEXT,
            height INTEGER,
            width INTEGER,
            is_primary INTEGER,
            is_preview INTEGER,
            is_gallery INTEGER,
            embed_code TEXT
        );

        CREATE TABLE IF NOT EXISTS rec_area_activities (
            rec_area_id TEXT,
            activity_id INTEGER,
            activity_name TEXT,
            description TEXT,
            fee_description TEXT,
            PRIMARY KEY (rec_area_id, activity_id)
        );

        CREATE TABLE IF NOT EXISTS tours (
            tour_id TEXT PRIMARY KEY,
            facility_id TEXT,
            tour_name TEXT,
            tour_type TEXT,
            tour_description TEXT,
            tour_duration INTEGER,
            tour_accessible INTEGER,
            created_date TEXT,
            last_updated TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            entity_id TEXT,
            entity_type TEXT,
            event_name TEXT,
            event_description TEXT,
            event_start_date TEXT,
            event_end_date TEXT,
            event_fee_description TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_media_entity ON media(entity_id, entity_type);
        CREATE INDEX IF NOT EXISTS idx_media_type ON media(media_type);
    """)
    conn.commit()

def pull_media(conn):
    """Pull all 288K media records"""
    print("=== PULLING MEDIA ===")
    c = conn.cursor()

    # Check existing
    c.execute("SELECT COUNT(*) FROM media")
    existing = c.fetchone()[0]
    offset = (existing // 50) * 50
    count = existing

    if existing > 0:
        print(f"  Resuming from {existing:,} existing records (offset {offset})")

    limit = 50
    total = None
    batch = []
    start = time.time()

    while True:
        data = fetch(f"/media?limit={limit}&offset={offset}")
        if not data or not data.get("RECDATA") or len(data["RECDATA"]) == 0:
            break

        if total is None:
            total = data["METADATA"]["RESULTS"]["TOTAL_COUNT"]
            print(f"  Total media: {total:,}")
            est = (total - count) / (50 / REQUEST_INTERVAL) / 60
            print(f"  Estimated time remaining: ~{est:.0f} minutes")

        for m in data["RECDATA"]:
            batch.append((
                m.get("EntityMediaID"), m.get("EntityID"), m.get("EntityType"),
                m.get("MediaType"), m.get("URL"), m.get("Title"),
                m.get("Subtitle"), m.get("Description"), m.get("Credits"),
                m.get("Height"), m.get("Width"),
                1 if m.get("IsPrimary") else 0,
                1 if m.get("IsPreview") else 0,
                1 if m.get("IsGallery") else 0,
                m.get("EmbedCode")
            ))
            count += 1

        if len(batch) >= 500:
            c.executemany("""INSERT OR REPLACE INTO media
                (entity_media_id, entity_id, entity_type, media_type, url, title,
                 subtitle, description, credits, height, width,
                 is_primary, is_preview, is_gallery, embed_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", batch)
            conn.commit()
            batch = []

        elapsed = time.time() - start
        rate = (count - existing) / elapsed if elapsed > 0 else 0
        remaining = total - count
        eta = remaining / rate / 60 if rate > 0 else 0
        pct = count / total * 100 if total else 0
        print(f"  [{pct:5.1f}%] {count:,}/{total:,} | {rate:.0f}/sec | ETA: {eta:.0f}min", end="\r")
        sys.stdout.flush()

        if len(data["RECDATA"]) < limit:
            break
        offset += limit

    # Final batch
    if batch:
        c.executemany("""INSERT OR REPLACE INTO media
            (entity_media_id, entity_id, entity_type, media_type, url, title,
             subtitle, description, credits, height, width,
             is_primary, is_preview, is_gallery, embed_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", batch)
        conn.commit()

    elapsed = time.time() - start
    print(f"\n  Done! {count:,} media in {elapsed/60:.1f} minutes")

def pull_rec_area_activities(conn):
    """Pull activities for each rec area"""
    print("\n=== PULLING REC AREA ACTIVITIES ===")
    c = conn.cursor()

    # Check if we already have them
    c.execute("SELECT COUNT(*) FROM rec_area_activities")
    if c.fetchone()[0] > 0:
        print("  Already populated, skipping")
        return

    # Get all rec area IDs
    c.execute("SELECT rec_area_id FROM rec_areas")
    ra_ids = [r[0] for r in c.fetchall()]
    print(f"  Checking {len(ra_ids):,} rec areas...")

    count = 0
    start = time.time()
    for i, ra_id in enumerate(ra_ids):
        data = fetch(f"/recareas/{ra_id}/activities?limit=50")
        if data and data.get("RECDATA"):
            for act in data["RECDATA"]:
                c.execute("""INSERT OR REPLACE INTO rec_area_activities
                    (rec_area_id, activity_id, activity_name, description, fee_description)
                    VALUES (?, ?, ?, ?, ?)""", (
                    ra_id, act.get("ActivityID"), act.get("ActivityName"),
                    act.get("RecAreaActivityDescription"),
                    act.get("RecAreaActivityFeeDescription")
                ))
                count += 1

        if (i + 1) % 50 == 0:
            conn.commit()
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(ra_ids) - i - 1) / rate / 60 if rate > 0 else 0
            print(f"  {i+1:,}/{len(ra_ids):,} rec areas | {count:,} activities | ETA: {eta:.0f}min", end="\r")
            sys.stdout.flush()

    conn.commit()
    print(f"\n  Done! {count:,} rec area activities")

def pull_tours(conn):
    """Pull all tours"""
    print("\n=== PULLING TOURS ===")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tours")
    if c.fetchone()[0] > 0:
        print("  Already populated, skipping")
        return

    offset = 0
    limit = 50
    count = 0
    while True:
        data = fetch(f"/tours?limit={limit}&offset={offset}")
        if not data or not data.get("RECDATA") or len(data["RECDATA"]) == 0:
            break
        for t in data["RECDATA"]:
            c.execute("""INSERT OR REPLACE INTO tours
                (tour_id, facility_id, tour_name, tour_type, tour_description,
                 tour_duration, tour_accessible, created_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                t.get("TourID"), t.get("FacilityID"), t.get("TourName"),
                t.get("TourType"), t.get("TourDescription"),
                t.get("TourDuration"), 1 if t.get("TourAccessible") else 0,
                t.get("CreatedDate"), t.get("LastUpdatedDate")
            ))
            count += 1
        conn.commit()
        print(f"  {count:,} tours", end="\r")
        if len(data["RECDATA"]) < limit:
            break
        offset += limit
    print(f"\n  Done! {count:,} tours")

def pull_events(conn):
    """Pull all events (only 3)"""
    print("\n=== PULLING EVENTS ===")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM events")
    if c.fetchone()[0] > 0:
        print("  Already populated, skipping")
        return

    data = fetch("/events?limit=50")
    count = 0
    if data and data.get("RECDATA"):
        for ev in data["RECDATA"]:
            c.execute("""INSERT OR REPLACE INTO events
                (event_id, entity_id, entity_type, event_name, event_description,
                 event_start_date, event_end_date, event_fee_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (
                ev.get("EventID"), ev.get("EntityID"), ev.get("EntityType"),
                ev.get("EventName"), ev.get("Description"),
                ev.get("EventStartDate"), ev.get("EventEndDate"),
                ev.get("EventFeeDescription")
            ))
            count += 1
    conn.commit()
    print(f"  Done! {count:,} events")

def print_summary(conn):
    c = conn.cursor()
    print("\n" + "=" * 60)
    print("COMPLETE DATABASE SUMMARY")
    print("=" * 60)

    all_tables = [
        "organizations", "rec_areas", "rec_area_addresses", "rec_area_activities",
        "facilities", "facility_addresses", "facility_activities",
        "campsites", "campsite_attributes", "campsite_equipment",
        "links", "media", "activities", "permit_entrances", "tours", "events"
    ]

    import os
    for t in all_tables:
        try:
            c.execute(f"SELECT COUNT(*) FROM {t}")
            cnt = c.fetchone()[0]
            print(f"  {t:30s}: {cnt:>12,}")
        except:
            print(f"  {t:30s}: TABLE MISSING")

    db_size = os.path.getsize(DB_PATH)
    print(f"\n  Database file size: {db_size / 1024 / 1024:.1f} MB")

    # Media breakdown
    print("\n  Media by type:")
    c.execute("SELECT media_type, entity_type, COUNT(*) FROM media GROUP BY media_type, entity_type ORDER BY COUNT(*) DESC LIMIT 10")
    for r in c.fetchall():
        print(f"    {r[0]:15s} ({r[1]:10s}): {r[2]:>8,}")

def main():
    conn = sqlite3.connect(DB_PATH)
    init_tables(conn)

    try:
        # Big one first
        pull_media(conn)

        # Rec area activities (per rec area, ~3671 requests)
        pull_rec_area_activities(conn)

        # Tours (599 total, ~12 requests)
        pull_tours(conn)

        # Events (3 total, 1 request)
        pull_events(conn)

        print_summary(conn)

    except KeyboardInterrupt:
        print("\n\nInterrupted! Saving...")
        conn.commit()
        print_summary(conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
