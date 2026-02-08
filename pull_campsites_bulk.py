"""
Bulk campsite pull from /campsites endpoint.
Much faster than per-facility: ~2,660 requests vs ~13,800.

Adds to existing ridb.db that already has orgs, rec_areas, and facilities.
"""
import requests
import sqlite3
import json
import time
import sys
import os

API_KEY = os.environ.get("RIDB_API_KEY", "")
BASE = "https://ridb.recreation.gov/api/v1"
HDR = {"apikey": API_KEY, "accept": "application/json"}
DB_PATH = "ridb.db"
REQUEST_INTERVAL = 1.35  # ~44 req/min, under 50 limit

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

def get_existing_count(conn):
    """Check how many campsites we already have"""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM campsites")
    return c.fetchone()[0]

def pull_campsites_bulk(conn):
    """Pull all campsites via the global /campsites endpoint"""
    c = conn.cursor()

    existing = get_existing_count(conn)
    print(f"  Existing campsites in DB: {existing}")

    # Resume from where we left off
    # The global endpoint returns campsites in a consistent order,
    # so we can skip pages we've already fetched
    offset = (existing // 50) * 50  # Round down to nearest page boundary
    if offset > 0:
        print(f"  Resuming from offset {offset} (approx {existing} already stored)")
    limit = 50  # API max per page
    total = None
    count = existing  # Start from existing for accurate progress
    batch_campsites = []
    batch_attrs = []
    batch_equip = []
    start_time = time.time()

    while True:
        data = fetch(f"/campsites?limit={limit}&offset={offset}")
        if not data or not data.get("RECDATA") or len(data["RECDATA"]) == 0:
            break

        if total is None:
            total = data["METADATA"]["RESULTS"]["TOTAL_COUNT"]
            print(f"  Total campsites to pull: {total:,}")
            est_time = (total / limit) * REQUEST_INTERVAL / 60
            print(f"  Estimated time: ~{est_time:.0f} minutes")

        for cs in data["RECDATA"]:
            csid = cs.get("CampsiteID")
            batch_campsites.append((
                csid, cs.get("FacilityID"), cs.get("CampsiteName"),
                cs.get("CampsiteType"), cs.get("TypeOfUse"), cs.get("Loop"),
                1 if cs.get("CampsiteAccessible") else 0,
                1 if cs.get("CampsiteReservable") else 0,
                cs.get("CampsiteLatitude"), cs.get("CampsiteLongitude"),
                cs.get("CreatedDate"), cs.get("LastUpdatedDate")
            ))

            for attr in cs.get("ATTRIBUTES", []):
                batch_attrs.append((
                    csid, attr.get("AttributeName"), attr.get("AttributeValue")
                ))

            for eq in cs.get("PERMITTEDEQUIPMENT", []):
                max_len = eq.get("MaxLength", 0)
                try:
                    max_len = float(max_len)
                except (ValueError, TypeError):
                    max_len = 0
                batch_equip.append((
                    csid, eq.get("EquipmentName"), max_len
                ))

            count += 1

        # Batch insert every 500 campsites
        if len(batch_campsites) >= 500:
            c.executemany("""INSERT OR REPLACE INTO campsites
                (campsite_id, facility_id, campsite_name, campsite_type,
                 type_of_use, loop, campsite_accessible, campsite_reservable,
                 campsite_latitude, campsite_longitude, created_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", batch_campsites)
            c.executemany("""INSERT OR REPLACE INTO campsite_attributes
                (campsite_id, attribute_name, attribute_value)
                VALUES (?, ?, ?)""", batch_attrs)
            c.executemany("""INSERT OR REPLACE INTO campsite_equipment
                (campsite_id, equipment_name, max_length)
                VALUES (?, ?, ?)""", batch_equip)
            conn.commit()
            batch_campsites = []
            batch_attrs = []
            batch_equip = []

        # Progress
        elapsed = time.time() - start_time
        rate = count / elapsed if elapsed > 0 else 0
        eta = (total - count) / rate / 60 if rate > 0 else 0
        pct = count / total * 100 if total else 0
        print(f"  [{pct:5.1f}%] {count:,}/{total:,} campsites | "
              f"{rate:.0f}/sec | ETA: {eta:.0f}min", end="\r")
        sys.stdout.flush()

        if len(data["RECDATA"]) < limit:
            break
        offset += limit

    # Final batch
    if batch_campsites:
        c.executemany("""INSERT OR REPLACE INTO campsites
            (campsite_id, facility_id, campsite_name, campsite_type,
             type_of_use, loop, campsite_accessible, campsite_reservable,
             campsite_latitude, campsite_longitude, created_date, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", batch_campsites)
        c.executemany("""INSERT OR REPLACE INTO campsite_attributes
            (campsite_id, attribute_name, attribute_value)
            VALUES (?, ?, ?)""", batch_attrs)
        c.executemany("""INSERT OR REPLACE INTO campsite_equipment
            (campsite_id, equipment_name, max_length)
            VALUES (?, ?, ?)""", batch_equip)
        conn.commit()

    elapsed = time.time() - start_time
    print(f"\n  Done! {count:,} campsites in {elapsed/60:.1f} minutes")

def print_summary(conn):
    c = conn.cursor()
    print("\n" + "=" * 60)
    print("DATABASE SUMMARY")
    print("=" * 60)

    tables = ["organizations", "rec_areas", "facilities", "campsites",
              "campsite_attributes", "campsite_equipment"]
    for table in tables:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = c.fetchone()[0]
        print(f"  {table:30s}: {cnt:>10,}")

    print("\n  Campsite Types:")
    c.execute("""SELECT campsite_type, COUNT(*) cnt FROM campsites
        GROUP BY campsite_type ORDER BY cnt DESC LIMIT 20""")
    for row in c.fetchall():
        print(f"    {row[0] or 'NULL':40s}: {row[1]:>8,}")

    print("\n  Equipment Types:")
    c.execute("""SELECT equipment_name, COUNT(*) cnt FROM campsite_equipment
        GROUP BY equipment_name ORDER BY cnt DESC""")
    for row in c.fetchall():
        print(f"    {row[0] or 'NULL':40s}: {row[1]:>8,}")

    print("\n  Key RV Attributes:")
    rv_attrs = ["Max Vehicle Length", "Driveway Entry", "Water Hookup",
                "Sewer Hookup", "Electricity Hookup", "Driveway Surface",
                "Driveway Length", "Driveway Grade", "Site Access",
                "Campfire Allowed", "Pets Allowed", "Shade"]
    for attr in rv_attrs:
        c.execute("SELECT COUNT(*) FROM campsite_attributes WHERE attribute_name = ?", (attr,))
        cnt = c.fetchone()[0]
        if cnt > 0:
            c.execute("""SELECT attribute_value, COUNT(*) FROM campsite_attributes
                WHERE attribute_name = ? GROUP BY attribute_value ORDER BY COUNT(*) DESC LIMIT 5""", (attr,))
            vals = c.fetchall()
            val_str = ", ".join(f"{v[0]}({v[1]:,})" for v in vals[:5])
            print(f"    {attr:30s}: {cnt:>8,}  [{val_str}]")

    # Facilities with campsites
    c.execute("""SELECT COUNT(DISTINCT facility_id) FROM campsites""")
    fac_w_sites = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM facilities")
    total_fac = c.fetchone()[0]
    print(f"\n  Facilities with campsites: {fac_w_sites:,} of {total_fac:,}")

    # RV equipment stats
    c.execute("""SELECT COUNT(DISTINCT facility_id) FROM campsites
        WHERE campsite_id IN (SELECT campsite_id FROM campsite_equipment WHERE equipment_name = 'RV')""")
    rv_facs = c.fetchone()[0]
    print(f"  Facilities with RV-equipped sites: {rv_facs:,}")

    db_size = os.path.getsize(DB_PATH)
    print(f"\n  Database file size: {db_size / 1024 / 1024:.1f} MB")

def main():
    print("RIDB Bulk Campsite Pull")
    print(f"Database: {os.path.abspath(DB_PATH)}")

    conn = sqlite3.connect(DB_PATH)

    try:
        pull_campsites_bulk(conn)
        print_summary(conn)
    except KeyboardInterrupt:
        print("\n\nInterrupted! Saving progress...")
        conn.commit()
        print_summary(conn)
    finally:
        conn.close()
        print(f"\nDatabase saved to: {os.path.abspath(DB_PATH)}")

if __name__ == "__main__":
    main()
