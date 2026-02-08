"""
RIDB Full Data Pull → SQLite

Pulls all facilities, campsites (with attributes & equipment), rec areas,
and organizations from the RIDB API and stores them in a local SQLite database.

Rate limit: 50 requests/min → we pace at ~45/min to be safe.
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

# Rate limiting: 50/min max, we'll do ~40/min to be safe
REQUEST_INTERVAL = 1.5  # seconds between requests
last_request_time = 0

def rate_limit():
    global last_request_time
    elapsed = time.time() - last_request_time
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    last_request_time = time.time()

def fetch(endpoint, retries=3):
    """Fetch from RIDB API with rate limiting and retries"""
    for attempt in range(retries):
        rate_limit()
        try:
            r = requests.get(f"{BASE}{endpoint}", headers=HDR, timeout=30)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                # Rate limited - back off
                wait = 30 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ERROR {r.status_code}: {r.text[:200]}")
                if attempt < retries - 1:
                    time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"  Request error: {e}")
            if attempt < retries - 1:
                time.sleep(5)
    return None

def init_db():
    """Create SQLite database with all tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.executescript("""
        DROP TABLE IF EXISTS organizations;
        DROP TABLE IF EXISTS rec_areas;
        DROP TABLE IF EXISTS rec_area_addresses;
        DROP TABLE IF EXISTS facilities;
        DROP TABLE IF EXISTS facility_addresses;
        DROP TABLE IF EXISTS facility_activities;
        DROP TABLE IF EXISTS campsites;
        DROP TABLE IF EXISTS campsite_attributes;
        DROP TABLE IF EXISTS campsite_equipment;

        CREATE TABLE organizations (
            org_id TEXT PRIMARY KEY,
            org_name TEXT,
            org_abbrev TEXT,
            org_type TEXT,
            org_jurisdiction TEXT,
            org_url TEXT,
            org_image_url TEXT,
            parent_org_id TEXT
        );

        CREATE TABLE rec_areas (
            rec_area_id TEXT PRIMARY KEY,
            rec_area_name TEXT,
            rec_area_description TEXT,
            rec_area_directions TEXT,
            rec_area_fee_description TEXT,
            rec_area_phone TEXT,
            rec_area_email TEXT,
            rec_area_latitude REAL,
            rec_area_longitude REAL,
            rec_area_reservation_url TEXT,
            reservable INTEGER,
            stay_limit TEXT,
            parent_org_id TEXT,
            last_updated TEXT
        );

        CREATE TABLE rec_area_addresses (
            rec_area_address_id TEXT PRIMARY KEY,
            rec_area_id TEXT,
            address_type TEXT,
            street1 TEXT,
            street2 TEXT,
            street3 TEXT,
            city TEXT,
            state_code TEXT,
            postal_code TEXT,
            country_code TEXT,
            FOREIGN KEY (rec_area_id) REFERENCES rec_areas(rec_area_id)
        );

        CREATE TABLE facilities (
            facility_id TEXT PRIMARY KEY,
            facility_name TEXT,
            facility_type TEXT,
            facility_description TEXT,
            facility_directions TEXT,
            facility_phone TEXT,
            facility_email TEXT,
            facility_latitude REAL,
            facility_longitude REAL,
            facility_reservation_url TEXT,
            facility_map_url TEXT,
            facility_use_fee TEXT,
            facility_ada_access TEXT,
            facility_accessibility_text TEXT,
            reservable INTEGER,
            enabled INTEGER,
            stay_limit TEXT,
            keywords TEXT,
            parent_org_id TEXT,
            parent_rec_area_id TEXT,
            legacy_facility_id TEXT,
            last_updated TEXT
        );

        CREATE TABLE facility_addresses (
            facility_address_id TEXT PRIMARY KEY,
            facility_id TEXT,
            address_type TEXT,
            street1 TEXT,
            street2 TEXT,
            street3 TEXT,
            city TEXT,
            state_code TEXT,
            postal_code TEXT,
            country_code TEXT,
            FOREIGN KEY (facility_id) REFERENCES facilities(facility_id)
        );

        CREATE TABLE facility_activities (
            facility_id TEXT,
            activity_id INTEGER,
            activity_name TEXT,
            PRIMARY KEY (facility_id, activity_id),
            FOREIGN KEY (facility_id) REFERENCES facilities(facility_id)
        );

        CREATE TABLE campsites (
            campsite_id TEXT PRIMARY KEY,
            facility_id TEXT,
            campsite_name TEXT,
            campsite_type TEXT,
            type_of_use TEXT,
            loop TEXT,
            campsite_accessible INTEGER,
            campsite_reservable INTEGER,
            campsite_latitude REAL,
            campsite_longitude REAL,
            created_date TEXT,
            last_updated TEXT,
            FOREIGN KEY (facility_id) REFERENCES facilities(facility_id)
        );

        CREATE TABLE campsite_attributes (
            campsite_id TEXT,
            attribute_name TEXT,
            attribute_value TEXT,
            PRIMARY KEY (campsite_id, attribute_name),
            FOREIGN KEY (campsite_id) REFERENCES campsites(campsite_id)
        );

        CREATE TABLE campsite_equipment (
            campsite_id TEXT,
            equipment_name TEXT,
            max_length REAL,
            PRIMARY KEY (campsite_id, equipment_name),
            FOREIGN KEY (campsite_id) REFERENCES campsites(campsite_id)
        );
    """)

    conn.commit()
    return conn

def pull_organizations(conn):
    """Pull all organizations"""
    print("\n=== PULLING ORGANIZATIONS ===")
    data = fetch("/organizations?limit=100")
    if not data or not data.get("RECDATA"):
        print("  Failed to fetch organizations")
        return

    c = conn.cursor()
    count = 0
    for org in data["RECDATA"]:
        c.execute("""INSERT OR REPLACE INTO organizations
            (org_id, org_name, org_abbrev, org_type, org_jurisdiction, org_url, org_image_url, parent_org_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (
            org.get("OrgID"), org.get("OrgName"), org.get("OrgAbbrevName"),
            org.get("OrgType"), org.get("OrgJurisdictionType"),
            org.get("OrgURLAddress"), org.get("OrgImageURL"), org.get("OrgParentID")
        ))
        count += 1

    conn.commit()
    print(f"  Stored {count} organizations")

def pull_rec_areas(conn):
    """Pull all recreation areas (paginated)"""
    print("\n=== PULLING RECREATION AREAS ===")
    c = conn.cursor()
    offset = 0
    limit = 50
    total = None
    count = 0

    while True:
        data = fetch(f"/recareas?limit={limit}&offset={offset}&full=true")
        if not data or not data.get("RECDATA"):
            break

        if total is None:
            total = data["METADATA"]["RESULTS"]["TOTAL_COUNT"]
            print(f"  Total rec areas: {total}")

        for ra in data["RECDATA"]:
            c.execute("""INSERT OR REPLACE INTO rec_areas
                (rec_area_id, rec_area_name, rec_area_description, rec_area_directions,
                 rec_area_fee_description, rec_area_phone, rec_area_email,
                 rec_area_latitude, rec_area_longitude, rec_area_reservation_url,
                 reservable, stay_limit, parent_org_id, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                ra.get("RecAreaID"), ra.get("RecAreaName"), ra.get("RecAreaDescription"),
                ra.get("RecAreaDirections"), ra.get("RecAreaFeeDescription"),
                ra.get("RecAreaPhone"), ra.get("RecAreaEmail"),
                ra.get("RecAreaLatitude"), ra.get("RecAreaLongitude"),
                ra.get("RecAreaReservationURL"), 1 if ra.get("Reservable") else 0,
                ra.get("StayLimit"), ra.get("ParentOrgID"), ra.get("LastUpdatedDate")
            ))

            # Addresses
            for addr in ra.get("RECAREAADDRESS", []):
                c.execute("""INSERT OR REPLACE INTO rec_area_addresses
                    (rec_area_address_id, rec_area_id, address_type, street1, street2, street3,
                     city, state_code, postal_code, country_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                    addr.get("RecAreaAddressID"), ra.get("RecAreaID"),
                    addr.get("RecAreaAddressType"),
                    addr.get("RecAreaStreetAddress1"), addr.get("RecAreaStreetAddress2"),
                    addr.get("RecAreaStreetAddress3"), addr.get("City"),
                    addr.get("AddressStateCode"), addr.get("PostalCode"),
                    addr.get("AddressCountryCode")
                ))

            count += 1

        conn.commit()
        print(f"  Progress: {count}/{total} rec areas", end="\r")

        if len(data["RECDATA"]) < limit:
            break
        offset += limit

    print(f"\n  Stored {count} rec areas")

def pull_facilities(conn):
    """Pull all facilities (paginated)"""
    print("\n=== PULLING FACILITIES ===")
    c = conn.cursor()
    offset = 0
    limit = 50
    total = None
    count = 0

    while True:
        data = fetch(f"/facilities?limit={limit}&offset={offset}&full=true")
        if not data or not data.get("RECDATA"):
            break

        if total is None:
            total = data["METADATA"]["RESULTS"]["TOTAL_COUNT"]
            print(f"  Total facilities: {total}")

        for fac in data["RECDATA"]:
            c.execute("""INSERT OR REPLACE INTO facilities
                (facility_id, facility_name, facility_type, facility_description,
                 facility_directions, facility_phone, facility_email,
                 facility_latitude, facility_longitude, facility_reservation_url,
                 facility_map_url, facility_use_fee, facility_ada_access,
                 facility_accessibility_text, reservable, enabled, stay_limit,
                 keywords, parent_org_id, parent_rec_area_id, legacy_facility_id, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                fac.get("FacilityID"), fac.get("FacilityName"),
                fac.get("FacilityTypeDescription"), fac.get("FacilityDescription"),
                fac.get("FacilityDirections"), fac.get("FacilityPhone"),
                fac.get("FacilityEmail"), fac.get("FacilityLatitude"),
                fac.get("FacilityLongitude"), fac.get("FacilityReservationURL"),
                fac.get("FacilityMapURL"), fac.get("FacilityUseFeeDescription"),
                fac.get("FacilityAdaAccess"), fac.get("FacilityAccessibilityText"),
                1 if fac.get("Reservable") else 0,
                1 if fac.get("Enabled") else 0,
                fac.get("StayLimit"), fac.get("Keywords"),
                fac.get("ParentOrgID"), fac.get("ParentRecAreaID"),
                fac.get("LegacyFacilityID"), fac.get("LastUpdatedDate")
            ))

            # Addresses
            for addr in fac.get("FACILITYADDRESS", []):
                c.execute("""INSERT OR REPLACE INTO facility_addresses
                    (facility_address_id, facility_id, address_type, street1, street2, street3,
                     city, state_code, postal_code, country_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                    addr.get("FacilityAddressID"), fac.get("FacilityID"),
                    addr.get("FacilityAddressType"),
                    addr.get("FacilityStreetAddress1"), addr.get("FacilityStreetAddress2"),
                    addr.get("FacilityStreetAddress3"), addr.get("City"),
                    addr.get("AddressStateCode"), addr.get("PostalCode"),
                    addr.get("AddressCountryCode")
                ))

            # Activities
            for act in fac.get("ACTIVITY", []):
                c.execute("""INSERT OR REPLACE INTO facility_activities
                    (facility_id, activity_id, activity_name)
                    VALUES (?, ?, ?)""", (
                    fac.get("FacilityID"), act.get("ActivityID"), act.get("ActivityName")
                ))

            count += 1

        conn.commit()
        print(f"  Progress: {count}/{total} facilities", end="\r")

        if len(data["RECDATA"]) < limit:
            break
        offset += limit

    print(f"\n  Stored {count} facilities")

def pull_campsites(conn):
    """Pull campsites for every facility that is a campground-type.
    This is the big one - we need to hit /facilities/{id}/campsites for each."""
    print("\n=== PULLING CAMPSITES ===")
    c = conn.cursor()

    # Get all facility IDs where there might be campsites
    # Focus on campground-like facilities first
    c.execute("""SELECT facility_id, facility_name FROM facilities
        WHERE facility_type IN ('Campground', 'Facility')
        OR facility_type LIKE '%Camp%'
        ORDER BY facility_id""")
    facilities = c.fetchall()
    print(f"  Checking {len(facilities)} facilities for campsites...")

    total_campsites = 0
    facilities_with_sites = 0
    skipped = 0

    for i, (fac_id, fac_name) in enumerate(facilities):
        # Check if we already have campsites for this facility (for resume capability)
        c.execute("SELECT COUNT(*) FROM campsites WHERE facility_id = ?", (fac_id,))
        existing = c.fetchone()[0]
        if existing > 0:
            skipped += 1
            total_campsites += existing
            if skipped <= 5 or skipped % 100 == 0:
                print(f"  Skipping {fac_id} ({fac_name}) - already has {existing} campsites")
            continue

        # Fetch campsites for this facility
        offset = 0
        limit = 50
        site_count = 0

        while True:
            data = fetch(f"/facilities/{fac_id}/campsites?limit={limit}&offset={offset}")
            if not data or not data.get("RECDATA") or len(data["RECDATA"]) == 0:
                break

            for cs in data["RECDATA"]:
                c.execute("""INSERT OR REPLACE INTO campsites
                    (campsite_id, facility_id, campsite_name, campsite_type,
                     type_of_use, loop, campsite_accessible, campsite_reservable,
                     campsite_latitude, campsite_longitude, created_date, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                    cs.get("CampsiteID"), fac_id, cs.get("CampsiteName"),
                    cs.get("CampsiteType"), cs.get("TypeOfUse"), cs.get("Loop"),
                    1 if cs.get("CampsiteAccessible") else 0,
                    1 if cs.get("CampsiteReservable") else 0,
                    cs.get("CampsiteLatitude"), cs.get("CampsiteLongitude"),
                    cs.get("CreatedDate"), cs.get("LastUpdatedDate")
                ))

                # Attributes
                for attr in cs.get("ATTRIBUTES", []):
                    c.execute("""INSERT OR REPLACE INTO campsite_attributes
                        (campsite_id, attribute_name, attribute_value)
                        VALUES (?, ?, ?)""", (
                        cs.get("CampsiteID"), attr.get("AttributeName"),
                        attr.get("AttributeValue")
                    ))

                # Permitted Equipment
                for eq in cs.get("PERMITTEDEQUIPMENT", []):
                    max_len = eq.get("MaxLength", 0)
                    try:
                        max_len = float(max_len)
                    except (ValueError, TypeError):
                        max_len = 0
                    c.execute("""INSERT OR REPLACE INTO campsite_equipment
                        (campsite_id, equipment_name, max_length)
                        VALUES (?, ?, ?)""", (
                        cs.get("CampsiteID"), eq.get("EquipmentName"), max_len
                    ))

                site_count += 1

            if len(data["RECDATA"]) < limit:
                break
            offset += limit

        if site_count > 0:
            facilities_with_sites += 1
            total_campsites += site_count

        conn.commit()

        # Progress
        elapsed_pct = (i + 1) / len(facilities) * 100
        print(f"  [{elapsed_pct:5.1f}%] {i+1}/{len(facilities)} facilities | "
              f"{facilities_with_sites} with sites | "
              f"{total_campsites} total campsites | "
              f"Current: {fac_name[:40]}", end="\r")
        sys.stdout.flush()

    print(f"\n  Done! {total_campsites} campsites across {facilities_with_sites} facilities")
    if skipped > 0:
        print(f"  (Skipped {skipped} facilities that already had campsites)")

def print_summary(conn):
    """Print database summary"""
    c = conn.cursor()
    print("\n" + "=" * 60)
    print("DATABASE SUMMARY")
    print("=" * 60)

    tables = ["organizations", "rec_areas", "facilities", "campsites",
              "campsite_attributes", "campsite_equipment",
              "facility_addresses", "facility_activities", "rec_area_addresses"]

    for table in tables:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        print(f"  {table:30s}: {count:>10,} rows")

    # Campsite type distribution
    print("\n  Campsite Types:")
    c.execute("SELECT campsite_type, COUNT(*) as cnt FROM campsites GROUP BY campsite_type ORDER BY cnt DESC LIMIT 15")
    for row in c.fetchall():
        print(f"    {row[0]:40s}: {row[1]:>8,}")

    # Equipment types
    print("\n  Equipment Types:")
    c.execute("SELECT equipment_name, COUNT(*) as cnt FROM campsite_equipment GROUP BY equipment_name ORDER BY cnt DESC")
    for row in c.fetchall():
        print(f"    {row[0]:40s}: {row[1]:>8,}")

    # Key attributes for RV
    print("\n  RV-relevant Attributes:")
    rv_attrs = ["Max Vehicle Length", "Driveway Entry", "Water Hookup",
                "Sewer Hookup", "Electricity Hookup", "Driveway Surface",
                "Driveway Length", "Driveway Grade"]
    for attr in rv_attrs:
        c.execute("SELECT COUNT(*) FROM campsite_attributes WHERE attribute_name = ?", (attr,))
        count = c.fetchone()[0]
        if count > 0:
            c.execute("""SELECT attribute_value, COUNT(*) FROM campsite_attributes
                WHERE attribute_name = ? GROUP BY attribute_value ORDER BY COUNT(*) DESC LIMIT 5""", (attr,))
            vals = c.fetchall()
            val_str = ", ".join(f"{v[0]}({v[1]})" for v in vals[:5])
            print(f"    {attr:30s}: {count:>8,} sites  [{val_str}]")

    db_size = os.path.getsize(DB_PATH)
    print(f"\n  Database file size: {db_size / 1024 / 1024:.1f} MB")

def main():
    print("RIDB Full Data Pull")
    print(f"Database: {os.path.abspath(DB_PATH)}")
    print(f"API Base: {BASE}")

    # Check if DB already exists (for resume)
    resuming = os.path.exists(DB_PATH)
    if resuming:
        print("Existing database found - will resume where possible")
        conn = sqlite3.connect(DB_PATH)
        # Check if tables exist
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        if not tables:
            print("  Empty database, starting fresh")
            conn.close()
            conn = init_db()
    else:
        conn = init_db()

    try:
        # 1. Organizations (fast, small)
        pull_organizations(conn)

        # 2. Recreation Areas
        pull_rec_areas(conn)

        # 3. Facilities
        pull_facilities(conn)

        # 4. Campsites (the big one - per facility)
        pull_campsites(conn)

        # Summary
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
