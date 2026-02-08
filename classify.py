"""
Phase 3: Campground Condition Classification & Tagging

Reads n_facility_rollup and produces:
  - n_facility_conditions: practical condition indicators per facility
    (road access, seasonal status, fire status, elevation, etc.)
  - n_facility_tags: feature tags/badges per facility

Replaces the old scoring system with actionable condition data.

Dependencies: Phase 2 (rollup.py) must have run first.

Usage:
    python classify.py
"""

import sqlite3
import sys
import time
from datetime import datetime, timezone

DB_PATH = "ridb.db"

# ============================================================
# SCHEMA
# ============================================================

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS n_facility_conditions (
    facility_id             TEXT PRIMARY KEY,

    road_access             TEXT,       -- PAVED / GRAVEL / DIRT / HIGH_CLEARANCE / 4WD_REQUIRED / UNKNOWN
    driveway_surface        TEXT,       -- PAVED / GRAVEL / MIXED / UNKNOWN
    seasonal_status         TEXT,       -- OPEN_YEAR_ROUND / SEASONAL_CLOSURE / WINTER_CLOSURE / UNKNOWN
    fire_status             TEXT,       -- CAMPFIRES_ALLOWED / RESTRICTIONS / NO_CAMPFIRES / UNKNOWN
    elevation_ft            INTEGER,
    boondock_accessibility  TEXT,       -- EASY / MODERATE / ROUGH / UNKNOWN
    max_rv_length           INTEGER,

    classified_at           TEXT
);

CREATE TABLE IF NOT EXISTS n_facility_tags (
    facility_id     TEXT NOT NULL,
    tag             TEXT NOT NULL,
    tag_category    TEXT NOT NULL,
    display_order   INTEGER NOT NULL,
    PRIMARY KEY (facility_id, tag)
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_nfc_road ON n_facility_conditions(road_access);
CREATE INDEX IF NOT EXISTS idx_nfc_season ON n_facility_conditions(seasonal_status);
CREATE INDEX IF NOT EXISTS idx_nfc_fire ON n_facility_conditions(fire_status);
CREATE INDEX IF NOT EXISTS idx_nfc_elev ON n_facility_conditions(elevation_ft);
CREATE INDEX IF NOT EXISTS idx_nfc_boondock ON n_facility_conditions(boondock_accessibility);
CREATE INDEX IF NOT EXISTS idx_nft_tag ON n_facility_tags(tag);
CREATE INDEX IF NOT EXISTS idx_nft_cat ON n_facility_tags(tag_category);
CREATE INDEX IF NOT EXISTS idx_nft_fac ON n_facility_tags(facility_id);
"""

# ============================================================
# CONDITION CLASSIFICATION FUNCTIONS
# ============================================================

def classify_road_access(r):
    """Determine road access level from description and campsite signals."""
    if r['desc_road_4wd']:
        return '4WD_REQUIRED'
    if r['desc_road_high_clearance']:
        return 'HIGH_CLEARANCE'
    if r['desc_road_dirt'] and not r['desc_road_paved']:
        return 'DIRT'
    if r['desc_road_gravel'] and not r['desc_road_paved']:
        return 'GRAVEL'
    if r['desc_road_paved'] or r['surface_predominant'] == 'PAVED':
        return 'PAVED'
    if r['surface_predominant'] == 'GRAVEL':
        return 'GRAVEL'
    if r['paved_sites'] > 0:
        return 'PAVED'
    if r['gravel_sites'] > 0:
        return 'GRAVEL'
    return 'UNKNOWN'


def classify_driveway_surface(r):
    """Determine driveway surface from campsite data."""
    sp = r['surface_predominant']
    if sp:
        return sp
    if r['paved_sites'] > 0 and r['gravel_sites'] > 0:
        return 'MIXED'
    if r['paved_sites'] > 0:
        return 'PAVED'
    if r['gravel_sites'] > 0:
        return 'GRAVEL'
    return 'UNKNOWN'


def classify_seasonal_status(r):
    """Determine seasonal availability from description signals."""
    if r['desc_winter_closure']:
        return 'WINTER_CLOSURE'
    if r['desc_seasonal_closure']:
        return 'SEASONAL_CLOSURE'
    # If no closure signals and it's a developed campground, likely year-round
    if r['camping_type'] == 'DEVELOPED' and not r['desc_mentions_snow']:
        return 'OPEN_YEAR_ROUND'
    return 'UNKNOWN'


def classify_fire_status(r):
    """Determine campfire/fire restriction status."""
    if r['desc_fire_restrictions']:
        return 'RESTRICTIONS'
    # Use campsite-level campfire data
    campfire_yes = r.get('campfire_yes_sites', 0) or 0
    campfire_no = r.get('campfire_no_sites', 0) or 0
    if campfire_no > 0 and campfire_yes == 0:
        return 'NO_CAMPFIRES'
    if campfire_yes > 0:
        return 'CAMPFIRES_ALLOWED'
    return 'UNKNOWN'


def classify_boondock(r):
    """Boondock accessibility for dispersed/primitive."""
    if r['desc_road_4wd']:
        return 'ROUGH'
    if r['desc_road_high_clearance']:
        return 'ROUGH'
    if r['desc_road_dirt'] and not r['desc_road_paved']:
        return 'MODERATE'
    if r['desc_road_gravel'] and not r['desc_road_paved']:
        return 'MODERATE'
    if r['desc_road_paved']:
        return 'EASY'
    return 'UNKNOWN'


# ============================================================
# TAGS
# ============================================================

def compute_tags(r):
    tags = []
    o = 0  # display_order counter

    # --- Warnings (category=WARNING, shown first) ---
    if r['desc_rv_not_recommended']:
        tags.append(('RV_NOT_RECOMMENDED', 'WARNING', o)); o += 1
    if r['site_access_predominant'] in ('HIKE_IN', 'WALK_IN', 'BOAT_IN') and r['drive_in_sites'] == 0:
        tags.append(('NO_DRIVE_IN_ACCESS', 'WARNING', o)); o += 1
    if r['desc_road_4wd']:
        tags.append(('4WD_REQUIRED', 'WARNING', o)); o += 1
    if r['desc_road_high_clearance']:
        tags.append(('HIGH_CLEARANCE', 'WARNING', o)); o += 1
    if r['max_rv_length'] is not None and r['max_rv_length'] < 25:
        tags.append(('LENGTH_RESTRICTED', 'WARNING', o)); o += 1
    if r['desc_remote_no_cell']:
        tags.append(('REMOTE_NO_CELL', 'WARNING', o)); o += 1
    if r['desc_flood_risk']:
        tags.append(('FLOOD_RISK', 'WARNING', o)); o += 1

    # --- Seasonal (category=SEASONAL) ---
    if r['desc_seasonal_closure'] or r['desc_winter_closure']:
        tags.append(('SEASONAL_CLOSURE', 'SEASONAL', o)); o += 1
    if r['desc_mentions_snow']:
        tags.append(('SNOW_AREA', 'SEASONAL', o)); o += 1

    # --- Fire (category=FIRE) ---
    if r['desc_fire_restrictions']:
        tags.append(('FIRE_RESTRICTIONS', 'FIRE', o)); o += 1

    # --- Environment (category=ENVIRONMENT) ---
    elev = r.get('desc_elevation_ft')
    if elev and elev >= 7000:
        tags.append(('HIGH_ELEVATION', 'ENVIRONMENT', o)); o += 1

    # --- Rig size (category=RIG_SIZE) ---
    max_len = r['max_rv_length']
    if (max_len is not None and max_len >= 45 and r['has_pullthrough']
            and r['surface_predominant'] in ('PAVED', 'GRAVEL', 'MIXED')):
        tags.append(('BIG_RIG_FRIENDLY', 'RIG_SIZE', o)); o += 1
    if r['has_pullthrough']:
        tags.append(('PULL_THROUGH', 'RIG_SIZE', o)); o += 1
    if r['backin_sites'] > 0 and r['pullthrough_sites'] == 0:
        tags.append(('BACK_IN_ONLY', 'RIG_SIZE', o)); o += 1

    # --- Hookup / Power (category=HOOKUP) ---
    if r['has_full_hookup']:
        tags.append(('FULL_HOOKUPS', 'HOOKUP', o)); o += 1
    elif r['has_electric_hookup']:
        tags.append(('ELECTRIC_HOOKUP', 'HOOKUP', o)); o += 1
    elif r['has_water_hookup']:
        tags.append(('WATER_HOOKUP', 'HOOKUP', o)); o += 1

    if r['max_amps'] is not None:
        if r['max_amps'] >= 50:
            tags.append(('50_AMP', 'HOOKUP', o)); o += 1
        elif r['max_amps'] >= 30:
            tags.append(('30_AMP', 'HOOKUP', o)); o += 1

    if (r['camping_type'] == 'DEVELOPED' and not r['has_electric_hookup']
            and not r['has_water_hookup']):
        tags.append(('DRY_CAMPING', 'HOOKUP', o)); o += 1

    # --- Access / Road (category=ACCESS) ---
    if r['desc_road_paved'] or r['surface_predominant'] == 'PAVED':
        tags.append(('PAVED_ACCESS', 'ACCESS', o)); o += 1
    if r['desc_road_gravel'] and not r['desc_road_paved']:
        tags.append(('GRAVEL_ROAD', 'ACCESS', o)); o += 1
    if r['desc_road_dirt'] and not r['desc_road_paved']:
        tags.append(('DIRT_ROAD', 'ACCESS', o)); o += 1

    # --- Camping style (category=STYLE) ---
    if r['camping_type'] == 'DISPERSED':
        tags.append(('BOONDOCKING', 'STYLE', o)); o += 1
    if r['camping_type'] == 'PRIMITIVE':
        tags.append(('PRIMITIVE', 'STYLE', o)); o += 1
    if r['desc_mentions_generator']:
        tags.append(('GENERATOR_MENTIONED', 'STYLE', o)); o += 1
    if r['desc_mentions_dump_station']:
        tags.append(('DUMP_STATION', 'STYLE', o)); o += 1
    if r['desc_mentions_potable_water']:
        tags.append(('POTABLE_WATER', 'STYLE', o)); o += 1
    if r['desc_mentions_vault_toilet']:
        tags.append(('VAULT_TOILET', 'STYLE', o)); o += 1
    if r['reservable']:
        tags.append(('RESERVABLE', 'STYLE', o)); o += 1

    return tags


# ============================================================
# MAIN PIPELINE
# ============================================================

ROLLUP_COLUMNS = [
    'facility_id', 'facility_name', 'facility_type', 'org_abbrev', 'org_name',
    'parent_rec_area_id', 'reservable',
    'latitude', 'longitude', 'coords_valid',
    'total_campsites', 'overnight_sites', 'day_use_sites',
    'rv_type_sites', 'tent_only_sites', 'standard_sites', 'group_sites',
    'cabin_sites', 'equestrian_sites', 'walk_hike_boat_sites', 'management_sites',
    'sites_accepting_rv', 'sites_accepting_tent',
    'has_water_hookup', 'has_sewer_hookup', 'has_electric_hookup', 'has_full_hookup',
    'water_hookup_sites', 'sewer_hookup_sites', 'electric_hookup_sites', 'full_hookup_sites',
    'max_amps',
    'has_pullthrough', 'pullthrough_sites', 'backin_sites', 'parallel_sites',
    'paved_sites', 'gravel_sites', 'surface_predominant',
    'max_rv_length', 'max_rv_length_equip', 'max_rv_length_attr', 'max_rv_length_desc',
    'site_access_predominant', 'drive_in_sites', 'walk_in_sites', 'hike_in_sites', 'boat_in_sites',
    'desc_mentions_rv', 'desc_mentions_hookups', 'desc_mentions_full_hookup',
    'desc_mentions_electric', 'desc_mentions_dump_station', 'desc_mentions_pull_through',
    'desc_mentions_generator', 'desc_rv_not_recommended',
    'desc_road_paved', 'desc_road_gravel', 'desc_road_dirt',
    'desc_road_high_clearance', 'desc_road_4wd',
    'desc_mentions_dispersed', 'desc_mentions_primitive',
    'desc_mentions_vault_toilet', 'desc_mentions_potable_water',
    'desc_seasonal_closure', 'desc_winter_closure', 'desc_mentions_snow',
    'desc_fire_restrictions', 'desc_mentions_elevation', 'desc_elevation_ft',
    'desc_remote_no_cell', 'desc_flood_risk',
    'campfire_yes_sites', 'campfire_no_sites',
    'has_camping_activity', 'has_rv_activity', 'has_dispersed_activity',
    'camping_type', 'camping_type_confidence',
]


def classify(conn):
    c = conn.cursor()

    col_sql = ', '.join(ROLLUP_COLUMNS)
    c.execute(f"SELECT {col_sql} FROM n_facility_rollup")
    rows = c.fetchall()
    print(f"  Loaded {len(rows):,} facilities from rollup")

    now = datetime.now(timezone.utc).isoformat()
    cond_batch = []
    tag_batch = []

    for row in rows:
        r = dict(zip(ROLLUP_COLUMNS, row))
        fid = r['facility_id']

        # Compute tags for all facilities
        tags = compute_tags(r)
        for tag, cat, order in tags:
            tag_batch.append((fid, tag, cat, order))

        # Classify conditions
        road = classify_road_access(r)
        surface = classify_driveway_surface(r)
        season = classify_seasonal_status(r)
        fire = classify_fire_status(r)
        elev = r.get('desc_elevation_ft')
        boondock = classify_boondock(r) if r['camping_type'] in ('DISPERSED', 'PRIMITIVE') else None
        max_rv = r['max_rv_length']

        cond_batch.append((
            fid, road, surface, season, fire, elev, boondock, max_rv, now,
        ))

    # Write conditions
    c = conn.cursor()
    c.execute("DELETE FROM n_facility_conditions")
    c.executemany("""
        INSERT INTO n_facility_conditions VALUES (?,?,?,?,?,?,?,?,?)
    """, cond_batch)
    print(f"  Inserted {len(cond_batch):,} condition rows")

    c.execute("DELETE FROM n_facility_tags")
    c.executemany("INSERT INTO n_facility_tags VALUES (?,?,?,?)", tag_batch)
    print(f"  Inserted {len(tag_batch):,} tag rows")


# ============================================================
# VALIDATION
# ============================================================

def validate(conn):
    c = conn.cursor()
    print("\n" + "=" * 60)
    print("  VALIDATION")
    print("=" * 60)
    errors = 0

    # 1. Row counts
    c.execute("SELECT COUNT(*) FROM n_facility_rollup")
    rollup_ct = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM n_facility_conditions")
    cond_ct = c.fetchone()[0]
    ok = rollup_ct == cond_ct
    print(f"  Row count: rollup={rollup_ct:,}  conditions={cond_ct:,}  {'OK' if ok else 'FAIL'}")
    if not ok:
        errors += 1

    # 2. Road access distribution
    print("\n  --- Road Access ---")
    c.execute("""
        SELECT road_access, COUNT(*)
        FROM n_facility_conditions
        GROUP BY road_access
        ORDER BY COUNT(*) DESC
    """)
    for val, cnt in c.fetchall():
        print(f"    {val or 'NULL':20s} {cnt:>6,}")

    # 3. Seasonal status distribution
    print("\n  --- Seasonal Status ---")
    c.execute("""
        SELECT seasonal_status, COUNT(*)
        FROM n_facility_conditions
        GROUP BY seasonal_status
        ORDER BY COUNT(*) DESC
    """)
    for val, cnt in c.fetchall():
        print(f"    {val or 'NULL':20s} {cnt:>6,}")

    # 4. Fire status distribution
    print("\n  --- Fire Status ---")
    c.execute("""
        SELECT fire_status, COUNT(*)
        FROM n_facility_conditions
        GROUP BY fire_status
        ORDER BY COUNT(*) DESC
    """)
    for val, cnt in c.fetchall():
        print(f"    {val or 'NULL':20s} {cnt:>6,}")

    # 5. Elevation
    c.execute("SELECT COUNT(*) FROM n_facility_conditions WHERE elevation_ft IS NOT NULL")
    elev_ct = c.fetchone()[0]
    c.execute("SELECT MIN(elevation_ft), MAX(elevation_ft), AVG(elevation_ft) FROM n_facility_conditions WHERE elevation_ft IS NOT NULL")
    mn, mx, avg = c.fetchone()
    print(f"\n  Elevation: {elev_ct:,} facilities, range {mn}-{mx} ft, avg {avg:.0f} ft")

    # 6. Boondock accessibility
    print("\n  --- Boondock Accessibility ---")
    c.execute("""
        SELECT boondock_accessibility, COUNT(*)
        FROM n_facility_conditions
        WHERE boondock_accessibility IS NOT NULL
        GROUP BY boondock_accessibility
        ORDER BY COUNT(*) DESC
    """)
    for acc, cnt in c.fetchall():
        print(f"    {acc:15s} {cnt:>6,}")

    # 7. FULL_HOOKUPS tag only when has_full_hookup
    c.execute("""
        SELECT COUNT(*) FROM n_facility_tags t
        JOIN n_facility_rollup fr ON t.facility_id = fr.facility_id
        WHERE t.tag = 'FULL_HOOKUPS' AND fr.has_full_hookup = 0
    """)
    bad = c.fetchone()[0]
    print(f"\n  FULL_HOOKUPS tag without data: {bad}  {'OK' if bad == 0 else 'FAIL'}")
    if bad:
        errors += 1

    # Tag counts
    print("\n  --- Tag Frequency ---")
    c.execute("""
        SELECT tag_category, tag, COUNT(*)
        FROM n_facility_tags
        GROUP BY tag_category, tag
        ORDER BY tag_category, COUNT(*) DESC
    """)
    cur_cat = None
    for cat, tag, cnt in c.fetchall():
        if cat != cur_cat:
            print(f"  {cat}:")
            cur_cat = cat
        print(f"    {tag:30s} {cnt:>6,}")

    print(f"\n  Validation errors: {errors}")
    return errors


# ============================================================
# MAIN
# ============================================================

def main():
    start = time.time()
    print(f"Phase 3 Classification — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # Pre-flight
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM n_facility_rollup")
    cnt = c.fetchone()[0]
    print(f"  Pre-flight: n_facility_rollup = {cnt:,} rows")
    if cnt == 0:
        print("  ERROR: n_facility_rollup is empty. Run rollup.py first.")
        return 1

    print("\n1. Creating schema...")
    conn.execute("DROP TABLE IF EXISTS n_facility_score")
    conn.execute("DROP TABLE IF EXISTS n_facility_conditions")
    conn.execute("DROP TABLE IF EXISTS n_facility_tags")
    conn.executescript(SCHEMA_SQL)

    print("\n2. Classifying conditions and tagging...")
    classify(conn)

    print("\n3. Creating indexes...")
    conn.executescript(INDEX_SQL)

    print("\n4. Updating metadata...")
    now = datetime.now(timezone.utc).isoformat()
    c.execute("DELETE FROM n_meta WHERE key LIKE 'classify_%'")
    for table in ['n_facility_conditions', 'n_facility_tags']:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = c.fetchone()[0]
        c.execute("INSERT OR REPLACE INTO n_meta VALUES (?,?,?)",
                  (f'classify_{table}_count', str(cnt), now))
    c.execute("INSERT OR REPLACE INTO n_meta VALUES (?,?,?)",
              ('classify_last_run', now, now))

    conn.commit()
    elapsed = time.time() - start
    print(f"\nClassification complete in {elapsed:.1f}s")

    errors = validate(conn)
    conn.close()
    return 1 if errors > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
