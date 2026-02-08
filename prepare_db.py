"""
Phase 4 prep: Create app indexes, photo mapping table, and state cache.

Run once before starting the Flask app.

Usage:
    python prepare_db.py
"""

import sqlite3
import time
from datetime import datetime, timezone

DB_PATH = "ridb.db"

# Full state/territory name → 2-letter code
STATE_NAME_TO_CODE = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    # Territories
    "american samoa": "AS", "guam": "GU", "puerto rico": "PR",
    "us virgin islands": "VI", "virgin islands": "VI",
    "northern mariana islands": "MP", "district of columbia": "DC",
    "federated states of micronesia": "FM",
}

# Valid 2-letter codes (states + territories)
VALID_CODES = set(STATE_NAME_TO_CODE.values())


def normalize_state_code(raw):
    """Normalize a raw state_code value to a 2-letter code, or None if invalid."""
    if not raw:
        return None
    cleaned = raw.strip().upper()
    if cleaned in VALID_CODES:
        return cleaned
    # Try as full name
    lookup = raw.strip().lower()
    if lookup in STATE_NAME_TO_CODE:
        return STATE_NAME_TO_CODE[lookup]
    return None


def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"Phase 4 DB Prep — {ts}")
    print(f"Database: {DB_PATH}\n")

    t0 = time.time()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ------------------------------------------------------------------
    # 1. App indexes
    # ------------------------------------------------------------------
    print("1. Creating app indexes...")

    indexes = [
        ("idx_fa_facility", "facility_addresses(facility_id, address_type)"),
        ("idx_campsites_facility", "campsites(facility_id)"),
        ("idx_media_preview", "media(entity_id, entity_type, is_preview)"),
        ("idx_fac_act_facility", "facility_activities(facility_id)"),
    ]

    for name, defn in indexes:
        cur.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {defn}")
        print(f"  {name}")

    # ------------------------------------------------------------------
    # 2. Photo mapping table (facility_id -> best photo URL)
    # ------------------------------------------------------------------
    print("\n2. Building photo mapping table...")

    cur.execute("DROP TABLE IF EXISTS n_facility_photo")
    cur.execute("""
        CREATE TABLE n_facility_photo (
            facility_id     TEXT PRIMARY KEY,
            photo_url       TEXT,
            photo_title     TEXT,
            photo_source    TEXT
        )
    """)

    # Use campsite photos grouped by facility — pick the primary/preview one
    cur.execute("""
        INSERT INTO n_facility_photo (facility_id, photo_url, photo_title, photo_source)
        SELECT
            c.facility_id,
            m.url,
            COALESCE(m.title, ''),
            'campsite_media'
        FROM media m
        JOIN campsites c ON m.entity_id = c.campsite_id
        WHERE m.entity_type = 'Campsite'
          AND m.media_type = 'Image'
        GROUP BY c.facility_id
        HAVING m.entity_media_id = MIN(m.entity_media_id)
    """)

    photo_count = cur.execute("SELECT COUNT(*) FROM n_facility_photo").fetchone()[0]
    print(f"  {photo_count:,} facilities with photos")

    # ------------------------------------------------------------------
    # 3. Normalize state codes in facility_addresses
    # ------------------------------------------------------------------
    print("\n3. Normalizing state codes...")

    conn.create_function("norm_state", 1, normalize_state_code)

    # Find all distinct raw values that need fixing
    raw_states = cur.execute(
        "SELECT DISTINCT state_code FROM facility_addresses "
        "WHERE state_code IS NOT NULL AND state_code <> ''"
    ).fetchall()

    fixes = 0
    nulled = 0
    for (raw,) in raw_states:
        normed = normalize_state_code(raw)
        if normed is None:
            # Invalid — null it out
            cur.execute(
                "UPDATE facility_addresses SET state_code = NULL WHERE state_code = ?",
                (raw,))
            cnt = cur.rowcount
            nulled += cnt
            print(f"  '{raw}' -> NULL ({cnt} rows)")
        elif normed != raw:
            cur.execute(
                "UPDATE facility_addresses SET state_code = ? WHERE state_code = ?",
                (normed, raw))
            cnt = cur.rowcount
            fixes += cnt
            print(f"  '{raw}' -> '{normed}' ({cnt} rows)")

    print(f"  Fixed {fixes} rows, nulled {nulled} invalid rows")

    # ------------------------------------------------------------------
    # 4. State cache table
    # ------------------------------------------------------------------
    print("\n4. Building state cache...")

    cur.execute("DROP TABLE IF EXISTS n_state_cache")
    cur.execute("""
        CREATE TABLE n_state_cache (
            state_code      TEXT PRIMARY KEY,
            facility_count  INTEGER NOT NULL
        )
    """)

    cur.execute("""
        INSERT INTO n_state_cache (state_code, facility_count)
        SELECT fa.state_code, COUNT(DISTINCT r.facility_id)
        FROM facility_addresses fa
        JOIN n_facility_rollup r ON fa.facility_id = r.facility_id
        WHERE r.camping_type IN ('DEVELOPED', 'PRIMITIVE', 'DISPERSED')
          AND fa.state_code IS NOT NULL AND fa.state_code <> ''
        GROUP BY fa.state_code
        ORDER BY fa.state_code
    """)

    state_count = cur.execute("SELECT COUNT(*) FROM n_state_cache").fetchone()[0]
    total_fac = cur.execute("SELECT SUM(facility_count) FROM n_state_cache").fetchone()[0]
    print(f"  {state_count} states/territories, {total_fac:,} campable facilities")

    # ------------------------------------------------------------------
    # 5. Update metadata
    # ------------------------------------------------------------------
    cur.execute("""
        INSERT OR REPLACE INTO n_meta (key, value)
        VALUES ('phase4_prep_at', ?)
    """, (ts,))

    conn.commit()
    conn.close()

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
