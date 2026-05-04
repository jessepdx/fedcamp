"""
Incremental RIDB sync + pipeline + cleaning orchestrator.

Pulls only records changed since last sync (using the RIDB lastupdated filter),
re-runs the normalization pipeline, then runs the post-pipeline cleaning /
enrichment scripts.

Usage:
    python sync.py                       # incremental from last_sync_date
    python sync.py --since 2026-02-01    # override start date
    python sync.py --skip-pull           # skip API pull, run pipeline + cleaning
    python sync.py --skip-pipeline       # only do the API pull
    python sync.py --skip-coords         # skip coords backfill
    python sync.py --skip-seasonal       # skip seasonal scrape
"""
import argparse
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


def load_env():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()

API_KEY = os.environ.get("RIDB_API_KEY", "")
BASE = "https://ridb.recreation.gov/api/v1"
HDR = {"apikey": API_KEY, "accept": "application/json"}
DB_PATH = "ridb.db"
REQUEST_INTERVAL = 1.5

last_request_time = 0.0
api_call_count = 0


def rate_limit():
    global last_request_time
    elapsed = time.time() - last_request_time
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    last_request_time = time.time()


def fetch(endpoint, retries=3):
    global api_call_count
    for attempt in range(retries):
        rate_limit()
        api_call_count += 1
        try:
            r = requests.get(BASE + endpoint, headers=HDR, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"  ERROR {r.status_code}: {r.text[:200]}")
        except requests.exceptions.RequestException as e:
            print(f"  Request error: {e}")
        if attempt < retries - 1:
            time.sleep(5)
    return None


def to_ridb_date(iso_date):
    """Normalize to YYYY-MM-DD for the lastupdated query.

    Note: docs/etl_update_plan.md claims MM-DD-YYYY, but that format is
    silently ignored by the API. The API actually accepts ISO YYYY-MM-DD.
    """
    return iso_date[:10]


def get_last_sync_date(conn):
    row = conn.execute(
        "SELECT value FROM n_meta WHERE key = 'last_sync_date'"
    ).fetchone()
    if row and row[0]:
        return row[0][:10]
    row = conn.execute("SELECT MAX(last_updated) FROM facilities").fetchone()
    if row and row[0]:
        return row[0][:10]
    return (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")


def assert_raw_tables(conn):
    expected = {"facilities", "campsites", "campsite_attributes",
                "campsite_equipment", "facility_addresses",
                "facility_activities", "media"}
    have = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    missing = expected - have
    if missing:
        sys.exit(f"ERROR: {DB_PATH} is missing raw tables: {sorted(missing)}.\n"
                 f"This script needs the unpurged RIDB DB. See "
                 f"docs/etl_update_plan.md.")


def pull_changed_facilities(conn, since_date):
    print(f"\n=== FACILITIES (lastupdated >= {since_date}) ===")
    cur = conn.cursor()
    api_date = to_ridb_date(since_date)
    offset = 0
    limit = 50
    changed_ids = []

    while True:
        data = fetch(
            f"/facilities?lastupdated={api_date}"
            f"&limit={limit}&offset={offset}&full=true"
        )
        if not data or not data.get("RECDATA"):
            break

        if offset == 0:
            total = data.get("METADATA", {}).get("RESULTS", {}).get("TOTAL_COUNT")
            if total is not None:
                print(f"  Total changed facilities: {total}")

        for fac in data["RECDATA"]:
            fid = fac.get("FacilityID")
            cur.execute("""INSERT OR REPLACE INTO facilities
                (facility_id, facility_name, facility_type, facility_description,
                 facility_directions, facility_phone, facility_email,
                 facility_latitude, facility_longitude, facility_reservation_url,
                 facility_map_url, facility_use_fee, facility_ada_access,
                 facility_accessibility_text, reservable, enabled, stay_limit,
                 keywords, parent_org_id, parent_rec_area_id, legacy_facility_id,
                 last_updated)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                fid, fac.get("FacilityName"),
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
                fac.get("LegacyFacilityID"), fac.get("LastUpdatedDate"),
            ))

            # Only rewrite addresses/activities if the API actually returned
            # the field. An absent key means "API didn't include it" — not
            # "facility has none" — so don't wipe existing good data on it.
            if "FACILITYADDRESS" in fac:
                cur.execute(
                    "DELETE FROM facility_addresses WHERE facility_id = ?", (fid,)
                )
                for addr in fac.get("FACILITYADDRESS") or []:
                    cur.execute("""INSERT OR REPLACE INTO facility_addresses
                        (facility_address_id, facility_id, address_type,
                         street1, street2, street3, city, state_code,
                         postal_code, country_code)
                        VALUES (?,?,?,?,?,?,?,?,?,?)""", (
                        addr.get("FacilityAddressID"), fid,
                        addr.get("FacilityAddressType"),
                        addr.get("FacilityStreetAddress1"),
                        addr.get("FacilityStreetAddress2"),
                        addr.get("FacilityStreetAddress3"),
                        addr.get("City"), addr.get("AddressStateCode"),
                        addr.get("PostalCode"), addr.get("AddressCountryCode"),
                    ))

            if "ACTIVITY" in fac:
                cur.execute(
                    "DELETE FROM facility_activities WHERE facility_id = ?", (fid,)
                )
                for act in fac.get("ACTIVITY") or []:
                    cur.execute("""INSERT OR REPLACE INTO facility_activities
                        (facility_id, activity_id, activity_name)
                        VALUES (?,?,?)""", (
                        fid, act.get("ActivityID"), act.get("ActivityName"),
                    ))

            changed_ids.append(fid)

        conn.commit()
        sys.stdout.write(f"\r  pulled {len(changed_ids)} facilities")
        sys.stdout.flush()

        if len(data["RECDATA"]) < limit:
            break
        offset += limit

    print(f"\n  {len(changed_ids)} facilities updated")
    return changed_ids


def repull_campsites_for_facilities(conn, facility_ids, label="CAMPSITES"):
    if not facility_ids:
        return 0, 0
    print(f"\n=== {label} for {len(facility_ids)} facilities ===")
    cur = conn.cursor()
    total_sites = 0
    facs_with_sites = 0
    start = time.time()

    for i, fid in enumerate(facility_ids):
        # Fetch the first page BEFORE any DELETEs. If the API errors (None)
        # or returns a missing/empty RECDATA, skip this facility entirely
        # rather than wiping its existing campsite data.
        first = fetch(f"/facilities/{fid}/campsites?limit=50&offset=0")
        if first is None or "RECDATA" not in first:
            # transient error or unexpected shape — leave existing data alone
            continue

        cur.execute("""DELETE FROM campsite_attributes
            WHERE campsite_id IN (SELECT campsite_id FROM campsites
                                  WHERE facility_id = ?)""", (fid,))
        cur.execute("""DELETE FROM campsite_equipment
            WHERE campsite_id IN (SELECT campsite_id FROM campsites
                                  WHERE facility_id = ?)""", (fid,))
        cur.execute("DELETE FROM campsites WHERE facility_id = ?", (fid,))

        limit = 50
        offset = 0
        site_count = 0
        data = first

        while data and data.get("RECDATA"):
            for cs in data["RECDATA"]:
                csid = cs.get("CampsiteID")
                cur.execute("""INSERT OR REPLACE INTO campsites
                    (campsite_id, facility_id, campsite_name, campsite_type,
                     type_of_use, loop, campsite_accessible, campsite_reservable,
                     campsite_latitude, campsite_longitude, created_date,
                     last_updated)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    csid, fid, cs.get("CampsiteName"),
                    cs.get("CampsiteType"), cs.get("TypeOfUse"), cs.get("Loop"),
                    1 if cs.get("CampsiteAccessible") else 0,
                    1 if cs.get("CampsiteReservable") else 0,
                    cs.get("CampsiteLatitude"), cs.get("CampsiteLongitude"),
                    cs.get("CreatedDate"), cs.get("LastUpdatedDate"),
                ))

                for attr in cs.get("ATTRIBUTES", []) or []:
                    cur.execute("""INSERT OR REPLACE INTO campsite_attributes
                        (campsite_id, attribute_name, attribute_value)
                        VALUES (?,?,?)""", (
                        csid, attr.get("AttributeName"), attr.get("AttributeValue"),
                    ))

                for eq in cs.get("PERMITTEDEQUIPMENT", []) or []:
                    max_len = eq.get("MaxLength", 0)
                    try:
                        max_len = float(max_len)
                    except (ValueError, TypeError):
                        max_len = 0
                    cur.execute("""INSERT OR REPLACE INTO campsite_equipment
                        (campsite_id, equipment_name, max_length)
                        VALUES (?,?,?)""", (
                        csid, eq.get("EquipmentName"), max_len,
                    ))

                site_count += 1

            if len(data["RECDATA"]) < limit:
                break
            offset += limit
            data = fetch(f"/facilities/{fid}/campsites?limit={limit}&offset={offset}")

        if site_count > 0:
            facs_with_sites += 1
            total_sites += site_count

        conn.commit()
        elapsed = time.time() - start
        rate = (i + 1) / elapsed if elapsed > 0 else 0
        eta = (len(facility_ids) - i - 1) / rate / 60 if rate > 0 else 0
        pct = (i + 1) / len(facility_ids) * 100
        sys.stdout.write(
            f"\r  [{pct:5.1f}%] {i + 1}/{len(facility_ids)} | "
            f"{facs_with_sites} with sites | {total_sites} sites | "
            f"ETA {eta:.1f}m"
        )
        sys.stdout.flush()

    print(f"\n  {total_sites} campsites across {facs_with_sites} facilities")
    return facs_with_sites, total_sites


def repull_media_for_facilities(conn, facility_ids):
    if not facility_ids:
        return 0
    print(f"\n=== MEDIA for {len(facility_ids)} facilities ===")
    cur = conn.cursor()
    total = 0

    for i, fid in enumerate(facility_ids):
        cur.execute(
            "DELETE FROM media WHERE entity_id = ? AND entity_type = 'Facility'",
            (fid,),
        )

        data = fetch(f"/facilities/{fid}/media?limit=50")
        if data and data.get("RECDATA"):
            for m in data["RECDATA"]:
                cur.execute("""INSERT OR REPLACE INTO media
                    (entity_media_id, entity_id, entity_type, media_type,
                     url, title, subtitle, description, credits,
                     height, width, is_primary, is_preview, is_gallery,
                     embed_code)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    m.get("EntityMediaID"), fid, "Facility",
                    m.get("MediaType"), m.get("URL"), m.get("Title"),
                    m.get("Subtitle"), m.get("Description"), m.get("Credits"),
                    m.get("Height"), m.get("Width"),
                    1 if m.get("IsPrimary") else 0,
                    1 if m.get("IsPreview") else 0,
                    1 if m.get("IsGallery") else 0,
                    m.get("EmbedCode"),
                ))
                total += 1

        conn.commit()
        pct = (i + 1) / len(facility_ids) * 100
        sys.stdout.write(
            f"\r  [{pct:5.1f}%] {i + 1}/{len(facility_ids)} | {total} media"
        )
        sys.stdout.flush()

    print(f"\n  {total} facility-level media records")
    return total


def update_sync_date(db_path=DB_PATH):
    """Write last_sync_date to n_meta. Call this AFTER the pipeline runs —
    normalize.py does DELETE FROM n_meta and would wipe an earlier write."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO n_meta (key, value, updated_at) VALUES ('last_sync_date', ?, ?)",
        (today, now),
    )
    conn.commit()
    conn.close()
    return today


def run_step(args, label):
    print(f"\n=== {label} ===")
    t0 = time.time()
    result = subprocess.run(args, check=False)
    if result.returncode != 0:
        print(f"  FAILED with exit code {result.returncode}")
        return False
    print(f"  done in {time.time() - t0:.1f}s")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since", help="Force start date (YYYY-MM-DD)")
    p.add_argument("--skip-pull", action="store_true",
                   help="Skip API pull, run pipeline + cleaning only")
    p.add_argument("--skip-pipeline", action="store_true")
    p.add_argument("--skip-coords", action="store_true")
    p.add_argument("--skip-seasonal", action="store_true")
    args = p.parse_args()

    if not Path(DB_PATH).exists():
        sys.exit(f"ERROR: {DB_PATH} not found")

    if not args.skip_pull and not API_KEY:
        sys.exit("ERROR: RIDB_API_KEY not set in environment or .env")

    t_start = time.time()
    print(f"sync.py — {datetime.now().isoformat(timespec='seconds')}")
    print(f"Database: {os.path.abspath(DB_PATH)}")

    conn = sqlite3.connect(DB_PATH)
    assert_raw_tables(conn)

    changed_ids = []
    site_facs = 0
    site_total = 0
    media_total = 0

    if not args.skip_pull:
        since = args.since or get_last_sync_date(conn)
        print(f"Syncing changes since: {since}\n")

        changed_ids = pull_changed_facilities(conn, since)

        if changed_ids:
            site_facs, site_total = repull_campsites_for_facilities(
                conn, changed_ids, label="CAMPSITES (changed facilities)"
            )
            media_total = repull_media_for_facilities(conn, changed_ids)

    conn.close()

    py = sys.executable
    if not args.skip_pipeline:
        for script, label in [
            ("normalize.py", "PHASE 1 — normalize"),
            ("rollup.py", "PHASE 2 — rollup"),
            ("classify.py", "PHASE 3 — classify"),
            ("prepare_db.py", "PHASE 4 — prepare_db"),
        ]:
            if not run_step([py, script], label):
                sys.exit(1)

    if not args.skip_coords:
        run_step([py, "scripts/backfill_coords.py"],
                 "CLEANING — backfill_coords")

    if not args.skip_seasonal:
        run_step([py, "scripts/scrape_seasonal.py"],
                 "CLEANING — scrape_seasonal")

    if not args.skip_pull:
        synced_to = update_sync_date()
        print(f"\nlast_sync_date set to {synced_to}")

    elapsed = time.time() - t_start
    print("\n" + "=" * 60)
    print("SYNC COMPLETE")
    print("=" * 60)
    print(f"  API calls:           {api_call_count:,}")
    print(f"  Changed facilities:  {len(changed_ids):,}")
    print(f"  Campsites refreshed: {site_total:,} across {site_facs} facilities")
    print(f"  Media records:       {media_total:,}")
    print(f"  Total time:          {elapsed / 60:.1f} min")


if __name__ == "__main__":
    main()
