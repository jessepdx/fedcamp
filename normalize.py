"""
Phase 1: Data Normalization for RV Camping Finder

Pivots the 2.4M EAV campsite_attributes into flat typed rows,
normalizes dirty field values, parses facility descriptions for
RV signals, and standardizes equipment names.

Creates new n_* tables alongside raw data (never modifies originals).
Idempotent: safe to re-run (DELETE + re-INSERT per table).

Usage:
    python normalize.py
"""

import re
import sqlite3
import sys
import time
from datetime import datetime, timezone

DB_PATH = "ridb.db"
SCHEMA_VERSION = "1"

# ============================================================
# SCHEMA
# ============================================================

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS n_campsite (
    campsite_id         TEXT PRIMARY KEY,
    facility_id         TEXT NOT NULL,

    -- From campsites table
    campsite_type       TEXT,
    type_of_use         TEXT,
    campsite_accessible INTEGER,
    campsite_reservable INTEGER,

    -- Driveway
    driveway_entry      TEXT,       -- BACK_IN | PULL_THROUGH | PARALLEL | NULL
    driveway_surface    TEXT,       -- PAVED | GRAVEL | GRASS | NULL
    driveway_length_ft  INTEGER,
    driveway_grade      TEXT,       -- SLIGHT | MODERATE | SEVERE | NULL

    -- Hookups
    has_water_hookup    INTEGER,    -- 1, 0, NULL (not reported)
    has_sewer_hookup    INTEGER,    -- 1, 0, NULL
    has_electric_hookup INTEGER,    -- 1, 0, NULL
    electric_amps       TEXT,       -- e.g. '50/30/20'
    max_electric_amps   INTEGER,    -- highest amp available
    has_full_hookup     INTEGER,    -- 1 if water+sewer+electric, else 0

    -- Vehicle
    max_vehicle_length  INTEGER,    -- feet, NULL if missing/unparseable
    max_vehicle_length_raw TEXT,    -- original string for audit

    -- Access
    site_access         TEXT,       -- DRIVE_IN | HIKE_IN | WALK_IN | BOAT_IN | BIKE | NULL

    -- Clearance
    overhead_clearance_ft INTEGER,

    -- Capacity
    max_num_people      INTEGER,
    max_num_vehicles    INTEGER,
    capacity_rating     TEXT,       -- SINGLE | DOUBLE | TRIPLE | QUAD | GROUP | NULL

    -- Amenities
    pets_allowed        INTEGER,    -- 1, 0, NULL
    campfire_allowed    INTEGER,    -- 1, 0, NULL
    shade               TEXT,       -- FULL | YES | NO | NULL

    -- Metadata
    normalized_at       TEXT
);

CREATE TABLE IF NOT EXISTS n_campsite_equipment (
    campsite_id         TEXT NOT NULL,
    equipment_category  TEXT NOT NULL,   -- RV | TRAILER | FIFTH_WHEEL | TENT | etc.
    equipment_name_raw  TEXT NOT NULL,
    max_length_ft       INTEGER,
    PRIMARY KEY (campsite_id, equipment_category)
);

DROP TABLE IF EXISTS n_facility;
CREATE TABLE IF NOT EXISTS n_facility (
    facility_id                 TEXT PRIMARY KEY,

    -- Coordinate quality
    coords_valid                INTEGER NOT NULL,
    facility_latitude_clean     REAL,
    facility_longitude_clean    REAL,

    -- Description signals
    desc_mentions_rv            INTEGER DEFAULT 0,
    desc_mentions_hookups       INTEGER DEFAULT 0,
    desc_mentions_full_hookup   INTEGER DEFAULT 0,
    desc_mentions_electric      INTEGER DEFAULT 0,
    desc_mentions_water_hookup  INTEGER DEFAULT 0,
    desc_mentions_sewer         INTEGER DEFAULT 0,
    desc_mentions_dump_station  INTEGER DEFAULT 0,
    desc_mentions_pull_through  INTEGER DEFAULT 0,
    desc_mentions_generator     INTEGER DEFAULT 0,
    desc_rv_not_recommended     INTEGER DEFAULT 0,
    desc_road_paved             INTEGER DEFAULT 0,
    desc_road_gravel            INTEGER DEFAULT 0,
    desc_road_dirt              INTEGER DEFAULT 0,
    desc_road_high_clearance    INTEGER DEFAULT 0,
    desc_road_4wd               INTEGER DEFAULT 0,
    desc_mentions_dispersed     INTEGER DEFAULT 0,
    desc_mentions_primitive     INTEGER DEFAULT 0,
    desc_mentions_vault_toilet  INTEGER DEFAULT 0,
    desc_mentions_potable_water INTEGER DEFAULT 0,
    desc_max_rv_length          INTEGER,
    desc_plain_text             TEXT,

    -- Condition signals
    desc_seasonal_closure       INTEGER DEFAULT 0,
    desc_winter_closure         INTEGER DEFAULT 0,
    desc_mentions_snow          INTEGER DEFAULT 0,
    desc_fire_restrictions      INTEGER DEFAULT 0,
    desc_mentions_elevation     INTEGER DEFAULT 0,
    desc_elevation_ft           INTEGER,
    desc_remote_no_cell         INTEGER DEFAULT 0,
    desc_flood_risk             INTEGER DEFAULT 0,

    normalized_at               TEXT
);

CREATE TABLE IF NOT EXISTS n_meta (
    key         TEXT PRIMARY KEY,
    value       TEXT,
    updated_at  TEXT
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_nc_facility ON n_campsite(facility_id);
CREATE INDEX IF NOT EXISTS idx_nc_entry ON n_campsite(driveway_entry);
CREATE INDEX IF NOT EXISTS idx_nc_electric ON n_campsite(has_electric_hookup);
CREATE INDEX IF NOT EXISTS idx_nc_water ON n_campsite(has_water_hookup);
CREATE INDEX IF NOT EXISTS idx_nc_sewer ON n_campsite(has_sewer_hookup);
CREATE INDEX IF NOT EXISTS idx_nc_access ON n_campsite(site_access);
CREATE INDEX IF NOT EXISTS idx_nc_vlen ON n_campsite(max_vehicle_length);
CREATE INDEX IF NOT EXISTS idx_nc_full ON n_campsite(has_full_hookup);
CREATE INDEX IF NOT EXISTS idx_ne_campsite ON n_campsite_equipment(campsite_id);
CREATE INDEX IF NOT EXISTS idx_ne_category ON n_campsite_equipment(equipment_category);
CREATE INDEX IF NOT EXISTS idx_nf_coords ON n_facility(coords_valid);
CREATE INDEX IF NOT EXISTS idx_nf_rv_warn ON n_facility(desc_rv_not_recommended);
"""

# ============================================================
# PARSE HELPERS
# ============================================================

def parse_driveway_entry(val):
    if val is None:
        return None
    v = val.strip().lower()
    if not v or v == 'n/a':
        return None
    if 'pull' in v or 'thru' in v or 'through' in v:
        return 'PULL_THROUGH'
    if 'back' in v:
        return 'BACK_IN'
    if 'parallel' in v:
        return 'PARALLEL'
    return None


def parse_driveway_surface(val):
    if val is None:
        return None
    v = val.strip().lower()
    if not v or v == 'n/a':
        return None
    if v == 'paved':
        return 'PAVED'
    if v == 'gravel':
        return 'GRAVEL'
    if v == 'grass':
        return 'GRASS'
    return None  # misplaced values like 'Pull-through', 'Slight'


def parse_driveway_grade(val):
    if val is None:
        return None
    v = val.strip().lower()
    if not v or v == 'n/a':
        return None
    if v == 'slight':
        return 'SLIGHT'
    if v == 'moderate':
        return 'MODERATE'
    if v == 'severe':
        return 'SEVERE'
    return None


def parse_water_hookup(val):
    if val is None:
        return None
    v = val.strip().lower()
    if not v:
        return None
    if v in ('yes', 'y', 'water hookup'):
        return 1
    if v in ('no',):
        return 0
    return None


def parse_sewer_hookup(val):
    if val is None:
        return None
    v = val.strip().lower()
    if not v:
        return None
    if v in ('yes', 'y', 'sewer hookup'):
        return 1
    if v in ('no',):
        return 0
    return None


def parse_electric(val):
    """Returns (has_electric, electric_amps_str, max_amps_int)."""
    if val is None:
        return (None, None, None)
    v = val.strip().lower()
    if not v or v in ('n/a', 'electricity hookup'):
        return (None, None, None)
    if v == 'no':
        return (0, None, None)
    if v == 'yes':
        return (1, None, None)
    # Parse amp values: strip 'amp'/'amps', split on '/'
    cleaned = v.replace('amp', '').replace('amps', '').strip()
    parts = [p.strip() for p in cleaned.split('/') if p.strip()]
    amps = set()
    for p in parts:
        try:
            a = int(p)
            if a > 0:
                amps.add(a)
        except ValueError:
            pass
    if amps:
        sorted_amps = sorted(amps, reverse=True)
        return (1, '/'.join(str(a) for a in sorted_amps), sorted_amps[0])
    return (None, None, None)


def parse_full_hookup(val):
    """Returns (has_full, amps_int) from Full Hookup attribute."""
    if val is None:
        return (False, None)
    v = val.strip().lower()
    if not v or v in ('n/a', 'no', 'full hookup'):
        # 'Full Hookup' as value (just the label) — means yes but no amp info
        if v == 'full hookup':
            return (True, None)
        return (False, None)
    # Try to parse amps
    try:
        a = int(v)
        if a > 0:
            return (True, a)
    except ValueError:
        pass
    return (True, None)


def parse_max_vehicle_length(val):
    """Returns (clean_int, raw_string)."""
    if val is None:
        return (None, None)
    raw = val.strip()
    if not raw or raw.lower() in ('n/a', 'none', 'nan'):
        return (None, raw or None)
    # Strip trailing ' or "ft"
    cleaned = raw.replace("'", '').replace('"', '').replace('ft', '').replace('feet', '').strip()
    try:
        length = int(float(cleaned))
    except (ValueError, OverflowError):
        return (None, raw)
    if length <= 0 or length > 150:
        return (None, raw)
    return (length, raw)


def parse_site_access(val):
    if val is None:
        return None
    v = val.strip().lower()
    if not v or v == 'n/a':
        return None
    # Handle comma-separated multi-access
    parts = [p.strip() for p in v.split(',')]
    # Priority: drive > walk > bike > hike > boat
    access_map = {
        'drive-in': 'DRIVE_IN', 'drive in': 'DRIVE_IN', 'drive-up': 'DRIVE_IN',
        'walk-in': 'WALK_IN',
        'bike': 'BIKE',
        'hike-in': 'HIKE_IN', 'hike in': 'HIKE_IN',
        'boat-in': 'BOAT_IN', 'boat in': 'BOAT_IN',
    }
    priority = ['DRIVE_IN', 'WALK_IN', 'BIKE', 'HIKE_IN', 'BOAT_IN']
    found = set()
    for p in parts:
        mapped = access_map.get(p)
        if mapped:
            found.add(mapped)
    if not found:
        return None
    for prio in priority:
        if prio in found:
            return prio
    return None


def parse_capacity_rating(val):
    if val is None:
        return None
    v = val.strip().lower()
    if not v or v == 'n/a':
        return None
    if v in ('single', 'single '):
        return 'SINGLE'
    if v in ('double',):
        return 'DOUBLE'
    if v in ('triple',):
        return 'TRIPLE'
    if v in ('quad',):
        return 'QUAD'
    if v in ('group',):
        return 'GROUP'
    return None


def parse_shade(val):
    if val is None:
        return None
    v = val.strip().lower()
    if not v:
        return None
    if v == 'full':
        return 'FULL'
    if v in ('yes',):
        return 'YES'
    if v in ('no',):
        return 'NO'
    if v in ('partial', 'shade'):
        return 'PARTIAL'
    return None


def parse_bool_attr(val):
    """Generic yes/no/null parser."""
    if val is None:
        return None
    v = val.strip().lower()
    if not v:
        return None
    if v in ('yes', 'y', 'domestic', 'domestic,horse', 'horse'):
        return 1
    if v in ('no',):
        return 0
    # For attributes like 'Pets Allowed' appearing as value
    if 'allowed' in v or 'yes' in v:
        return 1
    return None


def parse_int_attr(val):
    """Parse integer from attribute value."""
    if val is None:
        return None
    v = val.strip()
    if not v or v.lower() in ('n/a', ''):
        return None
    try:
        n = int(float(v))
        return n if n > 0 else None
    except (ValueError, OverflowError):
        return None


def parse_overhead_clearance(val):
    """Parse overhead clearance — mix of numbers and text."""
    if val is None:
        return None
    v = val.strip().lower()
    if not v or v in ('n/a', '0', 'open', 'no overhead cover', 'tree overhang', 'infinate', 'infinite'):
        return None
    # Strip units
    cleaned = v.replace("'", '').replace('feet', '').replace('ffet', '').replace('ft', '').strip()
    try:
        n = int(float(cleaned))
        return n if 5 <= n <= 100 else None
    except (ValueError, OverflowError):
        return None


# ============================================================
# EQUIPMENT NORMALIZATION
# ============================================================

EQUIPMENT_MAP = {
    'RV':                   'RV',
    'RV/MOTORHOME':         'RV',
    'Trailer':              'TRAILER',
    'FIFTH WHEEL':          'FIFTH_WHEEL',
    'PICKUP CAMPER':        'PICKUP_CAMPER',
    'POP UP':               'POP_UP',
    'CARAVAN/CAMPER VAN':   'CAMPER_VAN',
    'VEHICLE':              'VEHICLE',
    'CAR':                  'VEHICLE',
    'Tent':                 'TENT',
    'SMALL TENT':           'TENT',
    'LARGE TENT OVER 9X12`': 'TENT',
    'Boat':                 'BOAT',
    'Hammock':              'HAMMOCK',
    'Horse':                'HORSE',
}


# ============================================================
# FACILITY DESCRIPTION PARSING
# ============================================================

_HTML_TAG_RE = re.compile(r'<[^>]+>')
_HTML_ENTITY_RE = re.compile(r'&(amp|lt|gt|quot|#\d+|#x[0-9a-fA-F]+);')

def _decode_entity(m):
    e = m.group(1)
    if e == 'amp': return '&'
    if e == 'lt': return '<'
    if e == 'gt': return '>'
    if e == 'quot': return '"'
    if e.startswith('#x'):
        return chr(int(e[2:], 16))
    if e.startswith('#'):
        return chr(int(e[1:]))
    return m.group(0)

def strip_html(html):
    if not html:
        return ''
    text = _HTML_TAG_RE.sub(' ', html)
    text = _HTML_ENTITY_RE.sub(_decode_entity, text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# Compiled regex patterns for description parsing
_DESC_PATTERNS = {
    'desc_mentions_rv':            re.compile(r'\brv\b|motorhome|motor home', re.I),
    'desc_mentions_hookups':       re.compile(r'hook[\s-]?up', re.I),
    'desc_mentions_full_hookup':   re.compile(r'full hook', re.I),
    'desc_mentions_electric':      re.compile(r'electric hook|electr?ic site|\b30[\s-]?amp\b|\b50[\s-]?amp\b|\b20[\s-]?amp\b', re.I),
    'desc_mentions_water_hookup':  re.compile(r'water hook', re.I),
    'desc_mentions_sewer':         re.compile(r'sewer hook|sewer connection', re.I),
    'desc_mentions_dump_station':  re.compile(r'dump station', re.I),
    'desc_mentions_pull_through':  re.compile(r'pull[\s-]?through', re.I),
    'desc_mentions_generator':     re.compile(r'generator', re.I),
    'desc_rv_not_recommended':     re.compile(
        r'not recommended for rv|not recommended for motor|no rv[s ]|'
        r'rvs are not|rv access is not|motorhomes are not recommended|'
        r'trailers and motorhomes are not recommended|'
        r'not suitable for rv|not accessible.{0,20}rv', re.I),
    'desc_road_paved':             re.compile(r'paved road|paved access', re.I),
    'desc_road_gravel':            re.compile(r'gravel road|gravel access', re.I),
    'desc_road_dirt':              re.compile(r'dirt road|dirt access', re.I),
    'desc_road_high_clearance':    re.compile(r'high[\s-]clearance', re.I),
    'desc_road_4wd':               re.compile(r'\b4wd\b|4[\s-]wheel|four[\s-]?wheel drive', re.I),
    'desc_mentions_dispersed':     re.compile(r'dispersed', re.I),
    'desc_mentions_primitive':     re.compile(r'primitive', re.I),
    'desc_mentions_vault_toilet':  re.compile(r'vault toilet', re.I),
    'desc_mentions_potable_water': re.compile(r'potable water|drinking water', re.I),
    'desc_seasonal_closure':       re.compile(r'seasonal closure|seasonally closed|closed for the season|open seasonally|seasonal access', re.I),
    'desc_winter_closure':         re.compile(r'winter closure|closed in winter|closed during winter|snow closes|closed for winter|winter months.*closed', re.I),
    'desc_mentions_snow':          re.compile(r'\bsnow\b|snowfall|snow pack|snowbound|snowed in', re.I),
    'desc_fire_restrictions':      re.compile(r'fire restrict|fire ban|no campfire|campfire.{0,20}prohibit|burn ban|fire.{0,10}not (allowed|permitted)', re.I),
    'desc_mentions_elevation':     re.compile(r'\b\d{1,2},?\d{3}\s*(?:feet|foot|ft|\')\s*(?:elevation|elev\.?|above sea level)|elevation.{0,15}\d{1,2},?\d{3}', re.I),
    'desc_remote_no_cell':         re.compile(r'no cell|no cellular|no (cell\s*)?phone|no (cell\s*)?service|remote area|no reception|limited cell|poor cell', re.I),
    'desc_flood_risk':             re.compile(r'flash flood|flood risk|flood prone|flooding|high water|flood warning', re.I),
}

_RV_LENGTH_RE = re.compile(
    r'(?:rv|motorhome|trailer|vehicle)s?\s+(?:up to|limited to|maximum|max\.?)\s+(\d+)\s*(?:feet|foot|ft|\')|'
    r'(?:maximum|max\.?)\s+(?:rv|motorhome|trailer|vehicle)\s+(?:length|size)\s*(?:is|of|:)?\s*(\d+)|'
    r'(\d+)\s*(?:feet|foot|ft|\')\s+(?:rv|motorhome|trailer|vehicle)\s+(?:limit|max)',
    re.I
)

_ELEVATION_RE = re.compile(
    r'(\d{1,2}),?(\d{3})\s*(?:feet|foot|ft|\')\s*(?:elevation|elev\.?|above sea level)|'
    r'elevation\s*(?:is|of|:)?\s*(?:approximately\s*)?(\d{1,2}),?(\d{3})',
    re.I
)

def parse_description_signals(html):
    text = strip_html(html)
    signals = {}
    for key, pat in _DESC_PATTERNS.items():
        signals[key] = 1 if pat.search(text) else 0

    # Parse RV length from prose
    rv_len = None
    m = _RV_LENGTH_RE.search(text)
    if m:
        for g in m.groups():
            if g:
                try:
                    n = int(g)
                    if 15 <= n <= 100:
                        rv_len = n
                except ValueError:
                    pass
                break
    signals['desc_max_rv_length'] = rv_len

    # Parse elevation from prose
    elev_ft = None
    em = _ELEVATION_RE.search(text)
    if em:
        # Groups come in pairs: (thousands, hundreds) from two patterns
        for i in range(0, len(em.groups()), 2):
            g1, g2 = em.group(i + 1), em.group(i + 2)
            if g1 and g2:
                try:
                    elev_ft = int(g1) * 1000 + int(g2)
                    if elev_ft < 100 or elev_ft > 15000:
                        elev_ft = None
                except ValueError:
                    pass
                break
    signals['desc_elevation_ft'] = elev_ft

    signals['desc_plain_text'] = text
    return signals


# ============================================================
# NORMALIZATION FUNCTIONS
# ============================================================

# Attributes we pivot from the EAV table
PIVOT_ATTRS = [
    'Driveway Entry',
    'Driveway Surface',
    'Driveway Length',
    'Driveway Grade',
    'Water Hookup',
    'Sewer Hookup',
    'Electricity Hookup',
    'Full Hookup',
    'Max Vehicle Length',
    'Site Access',
    'Site Height/Overhead Clearance',
    'Max Num of People',
    'Max Num of Vehicles',
    'Capacity/Size Rating',
    'Pets Allowed',
    'Campfire Allowed',
    'Shade',
]


def normalize_campsites(conn):
    """Pivot campsite_attributes into flat n_campsite rows."""
    print("  Pivoting campsite attributes...")
    c = conn.cursor()

    # Build the pivot query
    cases = []
    for i, attr in enumerate(PIVOT_ATTRS):
        cases.append(
            f"MAX(CASE WHEN ca.attribute_name = '{attr}' THEN ca.attribute_value END) AS a{i}"
        )
    case_sql = ',\n        '.join(cases)

    pivot_sql = f"""
    SELECT
        cs.campsite_id,
        cs.facility_id,
        cs.campsite_type,
        cs.type_of_use,
        cs.campsite_accessible,
        cs.campsite_reservable,
        {case_sql}
    FROM campsites cs
    LEFT JOIN campsite_attributes ca ON cs.campsite_id = ca.campsite_id
        AND ca.attribute_name IN ({','.join('?' for _ in PIVOT_ATTRS)})
    GROUP BY cs.campsite_id
    """

    c.execute(pivot_sql, PIVOT_ATTRS)
    rows = c.fetchall()
    print(f"  Fetched {len(rows):,} campsite rows")

    now = datetime.now(timezone.utc).isoformat()
    batch = []
    for row in rows:
        (campsite_id, facility_id, campsite_type, type_of_use,
         accessible, reservable,
         raw_entry, raw_surface, raw_driveway_len, raw_grade,
         raw_water, raw_sewer, raw_electric, raw_full_hookup,
         raw_max_vlen, raw_access, raw_clearance,
         raw_max_people, raw_max_vehicles, raw_capacity,
         raw_pets, raw_campfire, raw_shade) = row

        driveway_entry = parse_driveway_entry(raw_entry)
        driveway_surface = parse_driveway_surface(raw_surface)
        driveway_length = parse_int_attr(raw_driveway_len)
        driveway_grade = parse_driveway_grade(raw_grade)

        has_water = parse_water_hookup(raw_water)
        has_sewer = parse_sewer_hookup(raw_sewer)
        has_electric, electric_amps, max_amps = parse_electric(raw_electric)

        # Full Hookup overrides
        full_flag, full_amps = parse_full_hookup(raw_full_hookup)
        if full_flag:
            has_water = 1
            has_sewer = 1
            has_electric = 1
            if full_amps and (max_amps is None or full_amps > max_amps):
                max_amps = full_amps
                electric_amps = str(full_amps)

        has_full = 1 if (has_water == 1 and has_sewer == 1 and has_electric == 1) else 0

        max_vlen, max_vlen_raw = parse_max_vehicle_length(raw_max_vlen)
        site_access = parse_site_access(raw_access)
        overhead = parse_overhead_clearance(raw_clearance)
        max_people = parse_int_attr(raw_max_people)
        max_vehicles = parse_int_attr(raw_max_vehicles)
        capacity = parse_capacity_rating(raw_capacity)
        pets = parse_bool_attr(raw_pets)
        campfire = parse_bool_attr(raw_campfire)
        shade = parse_shade(raw_shade)

        batch.append((
            campsite_id, facility_id, campsite_type, type_of_use,
            accessible, reservable,
            driveway_entry, driveway_surface, driveway_length, driveway_grade,
            has_water, has_sewer, has_electric, electric_amps, max_amps, has_full,
            max_vlen, max_vlen_raw,
            site_access, overhead,
            max_people, max_vehicles, capacity,
            pets, campfire, shade,
            now,
        ))

    c.execute("DELETE FROM n_campsite")
    c.executemany("""
        INSERT INTO n_campsite VALUES (
            ?,?,?,?,?,?,
            ?,?,?,?,
            ?,?,?,?,?,?,
            ?,?,
            ?,?,
            ?,?,?,
            ?,?,?,
            ?
        )
    """, batch)
    print(f"  Inserted {len(batch):,} n_campsite rows")


def normalize_equipment(conn):
    """Normalize equipment names and clean max_length."""
    print("  Normalizing equipment...")
    c = conn.cursor()
    c.execute("SELECT campsite_id, equipment_name, max_length FROM campsite_equipment")
    raw = c.fetchall()

    # Group by (campsite_id, category) — take max length per category
    grouped = {}
    for campsite_id, equip_name, max_len in raw:
        category = EQUIPMENT_MAP.get(equip_name)
        if category is None:
            category = equip_name.upper().replace(' ', '_')

        length = None
        if max_len is not None and max_len > 0 and max_len <= 150:
            length = int(max_len)

        key = (campsite_id, category)
        if key not in grouped:
            grouped[key] = (equip_name, length)
        else:
            existing_name, existing_len = grouped[key]
            # Keep the higher max_length
            if length is not None and (existing_len is None or length > existing_len):
                grouped[key] = (equip_name, length)

    batch = []
    for (campsite_id, category), (raw_name, length) in grouped.items():
        batch.append((campsite_id, category, raw_name, length))

    c.execute("DELETE FROM n_campsite_equipment")
    c.executemany(
        "INSERT INTO n_campsite_equipment VALUES (?,?,?,?)",
        batch
    )
    print(f"  Inserted {len(batch):,} n_campsite_equipment rows ({len(raw):,} raw → {len(batch):,} deduplicated)")


def normalize_facilities(conn):
    """Parse facility descriptions and flag coordinates."""
    print("  Normalizing facilities...")
    c = conn.cursor()
    c.execute("""
        SELECT facility_id, facility_latitude, facility_longitude, facility_description
        FROM facilities
    """)
    rows = c.fetchall()
    now = datetime.now(timezone.utc).isoformat()

    batch = []
    for fid, lat, lon, desc in rows:
        coords_valid = 1 if (lat != 0 or lon != 0) else 0
        lat_clean = lat if coords_valid else None
        lon_clean = lon if coords_valid else None

        signals = parse_description_signals(desc or '')

        batch.append((
            fid, coords_valid, lat_clean, lon_clean,
            signals['desc_mentions_rv'],
            signals['desc_mentions_hookups'],
            signals['desc_mentions_full_hookup'],
            signals['desc_mentions_electric'],
            signals['desc_mentions_water_hookup'],
            signals['desc_mentions_sewer'],
            signals['desc_mentions_dump_station'],
            signals['desc_mentions_pull_through'],
            signals['desc_mentions_generator'],
            signals['desc_rv_not_recommended'],
            signals['desc_road_paved'],
            signals['desc_road_gravel'],
            signals['desc_road_dirt'],
            signals['desc_road_high_clearance'],
            signals['desc_road_4wd'],
            signals['desc_mentions_dispersed'],
            signals['desc_mentions_primitive'],
            signals['desc_mentions_vault_toilet'],
            signals['desc_mentions_potable_water'],
            signals['desc_max_rv_length'],
            signals['desc_plain_text'],
            signals['desc_seasonal_closure'],
            signals['desc_winter_closure'],
            signals['desc_mentions_snow'],
            signals['desc_fire_restrictions'],
            signals['desc_mentions_elevation'],
            signals['desc_elevation_ft'],
            signals['desc_remote_no_cell'],
            signals['desc_flood_risk'],
            now,
        ))

    c.execute("DELETE FROM n_facility")
    c.executemany("""
        INSERT INTO n_facility VALUES (
            ?,?,?,?,
            ?,?,?,?,?,?,?,?,?,?,
            ?,?,?,?,?,?,?,?,?,
            ?,?,
            ?,?,?,?,?,?,?,?,
            ?
        )
    """, batch)
    print(f"  Inserted {len(batch):,} n_facility rows")


def update_meta(conn):
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    meta = [
        ('schema_version', SCHEMA_VERSION, now),
        ('last_normalize_run', now, now),
    ]
    # Row counts
    for table in ['n_campsite', 'n_campsite_equipment', 'n_facility']:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        meta.append((f'{table}_count', str(count), now))

    c.execute("DELETE FROM n_meta")
    c.executemany("INSERT INTO n_meta VALUES (?,?,?)", meta)


# ============================================================
# VALIDATION
# ============================================================

def validate(conn):
    """Run post-normalization sanity checks."""
    c = conn.cursor()
    print("\n" + "=" * 60)
    print("  VALIDATION")
    print("=" * 60)
    errors = 0

    # 1. Row count
    c.execute("SELECT COUNT(*) FROM campsites")
    raw_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM n_campsite")
    norm_count = c.fetchone()[0]
    ok = raw_count == norm_count
    print(f"  Row count: campsites={raw_count:,}  n_campsite={norm_count:,}  {'OK' if ok else 'FAIL'}")
    if not ok:
        errors += 1

    # 2. Driveway entry values
    c.execute("SELECT DISTINCT driveway_entry FROM n_campsite WHERE driveway_entry IS NOT NULL")
    vals = {r[0] for r in c.fetchall()}
    allowed = {'BACK_IN', 'PULL_THROUGH', 'PARALLEL'}
    bad = vals - allowed
    print(f"  Driveway entry values: {vals or '{NULL only}'}  {'OK' if not bad else 'FAIL: ' + str(bad)}")
    if bad:
        errors += 1

    # 3. Hookup values
    for col in ['has_water_hookup', 'has_sewer_hookup', 'has_electric_hookup']:
        c.execute(f"SELECT DISTINCT {col} FROM n_campsite WHERE {col} IS NOT NULL")
        vals = {r[0] for r in c.fetchall()}
        ok = vals <= {0, 1}
        print(f"  {col} values: {vals}  {'OK' if ok else 'FAIL'}")
        if not ok:
            errors += 1

    # 4. Max vehicle length range
    c.execute("SELECT MIN(max_vehicle_length), MAX(max_vehicle_length) FROM n_campsite WHERE max_vehicle_length IS NOT NULL")
    mn, mx = c.fetchone()
    ok = mn is None or (mn >= 1 and mx <= 150)
    print(f"  Max vehicle length range: {mn}-{mx}  {'OK' if ok else 'FAIL'}")
    if not ok:
        errors += 1

    # 5. Max electric amps
    c.execute("SELECT DISTINCT max_electric_amps FROM n_campsite WHERE max_electric_amps IS NOT NULL")
    vals = {r[0] for r in c.fetchall()}
    reasonable = all(1 <= v <= 200 for v in vals)
    print(f"  Electric amps values: {sorted(vals) if len(vals) <= 15 else f'{len(vals)} distinct'}  {'OK' if reasonable else 'WARN'}")

    # 6. Zero-coord facilities
    c.execute("SELECT COUNT(*) FROM n_facility WHERE coords_valid = 0")
    zero_ct = c.fetchone()[0]
    print(f"  Facilities with zero coords: {zero_ct:,}")

    # 7. Equipment categories
    c.execute("SELECT DISTINCT equipment_category FROM n_campsite_equipment ORDER BY equipment_category")
    cats = [r[0] for r in c.fetchall()]
    print(f"  Equipment categories: {cats}")

    # 8. Distribution summaries
    print("\n  --- Distribution Summaries ---")
    for col, label in [
        ('driveway_entry', 'Driveway Entry'),
        ('driveway_surface', 'Driveway Surface'),
        ('site_access', 'Site Access'),
        ('capacity_rating', 'Capacity Rating'),
    ]:
        c.execute(f"""
            SELECT {col}, COUNT(*) FROM n_campsite
            GROUP BY {col} ORDER BY COUNT(*) DESC
        """)
        print(f"\n  {label}:")
        for val, cnt in c.fetchall():
            print(f"    {val or 'NULL':20s} {cnt:>8,}")

    # Hookup coverage
    print("\n  Hookup Coverage:")
    for col, label in [
        ('has_water_hookup', 'Water'),
        ('has_sewer_hookup', 'Sewer'),
        ('has_electric_hookup', 'Electric'),
        ('has_full_hookup', 'Full'),
    ]:
        c.execute(f"""
            SELECT {col}, COUNT(*) FROM n_campsite
            GROUP BY {col} ORDER BY {col}
        """)
        print(f"  {label}:")
        for val, cnt in c.fetchall():
            lbl = {None: 'not reported', 0: 'no', 1: 'yes'}.get(val, str(val))
            print(f"    {lbl:20s} {cnt:>8,}")

    # Max vehicle length distribution
    print("\n  Max Vehicle Length Buckets:")
    c.execute("""
        SELECT
            CASE
                WHEN max_vehicle_length IS NULL THEN 'unknown'
                WHEN max_vehicle_length <= 20 THEN '1-20 ft'
                WHEN max_vehicle_length <= 30 THEN '21-30 ft'
                WHEN max_vehicle_length <= 40 THEN '31-40 ft'
                WHEN max_vehicle_length <= 50 THEN '41-50 ft'
                WHEN max_vehicle_length <= 60 THEN '51-60 ft'
                ELSE '61+ ft'
            END as bucket,
            COUNT(*)
        FROM n_campsite
        GROUP BY bucket
        ORDER BY bucket
    """)
    for bucket, cnt in c.fetchall():
        print(f"    {bucket:20s} {cnt:>8,}")

    # Cross-validation: RV equipment but zero vehicle length
    c.execute("""
        SELECT COUNT(DISTINCT nc.campsite_id)
        FROM n_campsite nc
        JOIN n_campsite_equipment ne ON nc.campsite_id = ne.campsite_id
        WHERE ne.equipment_category = 'RV'
        AND nc.max_vehicle_length IS NULL
    """)
    rv_no_len = c.fetchone()[0]
    print(f"\n  Cross-check: RV equipment + unknown vehicle length: {rv_no_len:,}")

    # Cross-validation: HIKE_IN with RV equipment
    c.execute("""
        SELECT COUNT(DISTINCT nc.campsite_id)
        FROM n_campsite nc
        JOIN n_campsite_equipment ne ON nc.campsite_id = ne.campsite_id
        WHERE ne.equipment_category = 'RV'
        AND nc.site_access = 'HIKE_IN'
    """)
    hike_rv = c.fetchone()[0]
    print(f"  Cross-check: HIKE_IN + RV equipment: {hike_rv:,}")

    # Description signal counts
    print("\n  Facility Description Signals:")
    signal_cols = [
        'desc_mentions_rv', 'desc_mentions_hookups', 'desc_mentions_full_hookup',
        'desc_mentions_dump_station', 'desc_mentions_pull_through',
        'desc_rv_not_recommended', 'desc_road_gravel', 'desc_road_dirt',
        'desc_road_high_clearance', 'desc_road_4wd',
        'desc_mentions_dispersed', 'desc_mentions_primitive',
        'desc_mentions_vault_toilet', 'desc_mentions_potable_water',
        'desc_seasonal_closure', 'desc_winter_closure', 'desc_mentions_snow',
        'desc_fire_restrictions', 'desc_mentions_elevation',
        'desc_remote_no_cell', 'desc_flood_risk',
    ]
    for col in signal_cols:
        c.execute(f"SELECT SUM({col}) FROM n_facility")
        cnt = c.fetchone()[0] or 0
        print(f"    {col:40s} {cnt:>6,}")

    c.execute("SELECT COUNT(*) FROM n_facility WHERE desc_max_rv_length IS NOT NULL")
    rv_len_ct = c.fetchone()[0]
    print(f"    {'desc_max_rv_length (parsed)':40s} {rv_len_ct:>6,}")

    c.execute("SELECT COUNT(*) FROM n_facility WHERE desc_elevation_ft IS NOT NULL")
    elev_ct = c.fetchone()[0]
    print(f"    {'desc_elevation_ft (parsed)':40s} {elev_ct:>6,}")

    print(f"\n  Validation errors: {errors}")
    return errors


# ============================================================
# MAIN
# ============================================================

def main():
    start = time.time()
    print(f"Phase 1 Normalization — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    print("\n1. Creating schema...")
    conn.executescript(SCHEMA_SQL)

    print("\n2. Normalizing campsites...")
    normalize_campsites(conn)

    print("\n3. Normalizing equipment...")
    normalize_equipment(conn)

    print("\n4. Normalizing facilities...")
    normalize_facilities(conn)

    print("\n5. Creating indexes...")
    conn.executescript(INDEX_SQL)

    print("\n6. Updating metadata...")
    update_meta(conn)

    conn.commit()
    elapsed = time.time() - start
    print(f"\nNormalization complete in {elapsed:.1f}s")

    errors = validate(conn)
    conn.close()

    return 1 if errors > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
