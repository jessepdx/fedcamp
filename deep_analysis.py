"""
Deep data analysis of RIDB SQLite database.
No assumptions. Just look at what's actually there.
"""
import sqlite3
import os

DB_PATH = "ridb.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

out = []
def p(s=""):
    out.append(s)
    print(s)

def section(n, title):
    p(f"\n{'='*80}")
    p(f"  {n}. {title}")
    p(f"{'='*80}")

def query(sql, params=None):
    if params:
        c.execute(sql, params)
    else:
        c.execute(sql)
    return c.fetchall()

# ============================================================
section(1, "DATABASE OVERVIEW")
# ============================================================
tables = query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
p(f"Tables: {len(tables)}")
for t in tables:
    name = t[0]
    cnt = query(f"SELECT COUNT(*) FROM [{name}]")[0][0]
    p(f"  {name:30s}: {cnt:>12,}")
p(f"\nDB file: {os.path.getsize(DB_PATH) / 1024 / 1024:.1f} MB")

# ============================================================
section(2, "FACILITIES - Shape of the data")
# ============================================================

# Completeness of every column
p("Column completeness (non-null, non-empty):")
cols = [r[1] for r in query("PRAGMA table_info(facilities)")]
for col in cols:
    total = query("SELECT COUNT(*) FROM facilities")[0][0]
    filled = query(f"SELECT COUNT(*) FROM facilities WHERE [{col}] IS NOT NULL AND [{col}] != ''")[0][0]
    pct = filled / total * 100
    p(f"  {col:35s}: {filled:>8,} / {total:,}  ({pct:5.1f}%)")

# Facility types
p("\nFacility types:")
for r in query("SELECT facility_type, COUNT(*) c FROM facilities GROUP BY facility_type ORDER BY c DESC"):
    p(f"  {r[0] or 'NULL':35s}: {r[1]:>8,}")

# Enabled vs disabled
p("\nEnabled status:")
for r in query("SELECT enabled, COUNT(*) FROM facilities GROUP BY enabled"):
    p(f"  enabled={r[0]}: {r[1]:,}")

# Reservable
p("\nReservable:")
for r in query("SELECT reservable, COUNT(*) FROM facilities GROUP BY reservable"):
    p(f"  reservable={r[0]}: {r[1]:,}")

# Reservable BY type
p("\nReservable by facility type:")
for r in query("""SELECT facility_type,
    COUNT(*) total,
    SUM(reservable) resv,
    ROUND(SUM(reservable)*100.0/COUNT(*),1) pct
    FROM facilities GROUP BY facility_type ORDER BY total DESC"""):
    p(f"  {r[0] or 'NULL':25s}: {r[2]:>6,} / {r[1]:>6,} reservable ({r[3]}%)")

# ============================================================
section(3, "FACILITIES - Geographic coverage")
# ============================================================

p("Coordinate quality:")
for r in query("""SELECT
    COUNT(*) total,
    SUM(CASE WHEN facility_latitude = 0 AND facility_longitude = 0 THEN 1 ELSE 0 END) zero,
    SUM(CASE WHEN facility_latitude != 0 AND facility_longitude != 0 THEN 1 ELSE 0 END) valid,
    SUM(CASE WHEN facility_latitude IS NULL THEN 1 ELSE 0 END) null_lat
FROM facilities"""):
    p(f"  Total: {r[0]:,}")
    p(f"  Valid coords: {r[1]:,} (lat/lon both non-zero)")
    p(f"  Zero coords: {r[2]:,}")
    p(f"  NULL coords: {r[3]:,}")

# Latitude range (sanity check — should be ~18 to ~72 for US)
p("\nLatitude range (non-zero):")
for r in query("""SELECT MIN(facility_latitude), MAX(facility_latitude),
    AVG(facility_latitude), MIN(facility_longitude), MAX(facility_longitude)
    FROM facilities WHERE facility_latitude != 0"""):
    p(f"  Lat: {r[0]:.4f} to {r[1]:.4f} (avg {r[2]:.4f})")
    p(f"  Lon: {r[3]:.4f} to {r[4]:.4f}")

# Outliers — anything outside US bounds
p("\nCoords outside continental US (lat not 24-50, lon not -125 to -66):")
cnt = query("""SELECT COUNT(*) FROM facilities
    WHERE facility_latitude != 0
    AND (facility_latitude < 24 OR facility_latitude > 72
         OR facility_longitude < -180 OR facility_longitude > -60)""")[0][0]
p(f"  {cnt:,} facilities")
if cnt > 0 and cnt < 30:
    for r in query("""SELECT facility_name, facility_latitude, facility_longitude,
        fa.state_code
        FROM facilities f
        LEFT JOIN facility_addresses fa ON f.facility_id = fa.facility_id
        WHERE f.facility_latitude != 0
        AND (f.facility_latitude < 24 OR f.facility_latitude > 72)
        LIMIT 15"""):
        p(f"    {r[0]:40s} ({r[1]:.2f}, {r[2]:.2f}) state={r[3]}")

# By state
p("\nFacilities by state (top 25):")
for r in query("""SELECT fa.state_code, COUNT(DISTINCT f.facility_id) c
    FROM facilities f
    JOIN facility_addresses fa ON f.facility_id = fa.facility_id
    WHERE fa.state_code != '' AND fa.state_code IS NOT NULL
    GROUP BY fa.state_code ORDER BY c DESC LIMIT 25"""):
    p(f"  {r[0]:5s}: {r[1]:>6,}")

# States with zero-coord facilities
p("\nStates with most zero-coord facilities:")
for r in query("""SELECT fa.state_code, COUNT(DISTINCT f.facility_id) c
    FROM facilities f
    JOIN facility_addresses fa ON f.facility_id = fa.facility_id
    WHERE f.facility_latitude = 0 AND f.facility_longitude = 0
    AND fa.state_code != ''
    GROUP BY fa.state_code ORDER BY c DESC LIMIT 10"""):
    p(f"  {r[0]:5s}: {r[1]:>6,}")

# ============================================================
section(4, "FACILITIES <-> CAMPSITES relationship")
# ============================================================

total_fac = query("SELECT COUNT(*) FROM facilities")[0][0]
fac_w_sites = query("SELECT COUNT(DISTINCT facility_id) FROM campsites")[0][0]
fac_wo_sites = total_fac - fac_w_sites

p(f"Facilities total: {total_fac:,}")
p(f"Facilities WITH campsites: {fac_w_sites:,}")
p(f"Facilities WITHOUT campsites: {fac_wo_sites:,}")

# Campsites per facility distribution
p("\nCampsites per facility distribution:")
for r in query("""
    WITH fac_counts AS (
        SELECT facility_id, COUNT(*) cnt FROM campsites GROUP BY facility_id
    )
    SELECT
        CASE
            WHEN cnt = 1 THEN '1'
            WHEN cnt BETWEEN 2 AND 5 THEN '2-5'
            WHEN cnt BETWEEN 6 AND 10 THEN '6-10'
            WHEN cnt BETWEEN 11 AND 25 THEN '11-25'
            WHEN cnt BETWEEN 26 AND 50 THEN '26-50'
            WHEN cnt BETWEEN 51 AND 100 THEN '51-100'
            WHEN cnt BETWEEN 101 AND 200 THEN '101-200'
            WHEN cnt BETWEEN 201 AND 500 THEN '201-500'
            WHEN cnt > 500 THEN '500+'
        END bucket,
        COUNT(*) facilities,
        SUM(cnt) campsites,
        MIN(cnt) min_sites,
        MAX(cnt) max_sites
    FROM fac_counts GROUP BY bucket
    ORDER BY min_sites
"""):
    p(f"  {r[0]:10s}: {r[1]:>6,} facilities ({r[2]:>8,} campsites)")

# Biggest facilities
p("\nLargest facilities by campsite count:")
for r in query("""SELECT f.facility_name, o.org_abbrev, COUNT(cs.campsite_id) cnt
    FROM facilities f
    JOIN campsites cs ON f.facility_id = cs.facility_id
    LEFT JOIN organizations o ON f.parent_org_id = o.org_id
    GROUP BY f.facility_id ORDER BY cnt DESC LIMIT 15"""):
    p(f"  {r[1]:6s} {r[0]:50s}: {r[2]:>5,} sites")

# ============================================================
section(5, "CAMPSITES - Shape of the data")
# ============================================================

p("Column completeness:")
cs_cols = [r[1] for r in query("PRAGMA table_info(campsites)")]
for col in cs_cols:
    total = 132974
    filled = query(f"SELECT COUNT(*) FROM campsites WHERE [{col}] IS NOT NULL AND [{col}] != '' AND [{col}] != 0")[0][0]
    pct = filled / total * 100
    p(f"  {col:25s}: {filled:>10,} / {total:,}  ({pct:5.1f}%)")

# Type of use
p("\nType of use:")
for r in query("SELECT type_of_use, COUNT(*) FROM campsites GROUP BY type_of_use ORDER BY COUNT(*) DESC"):
    p(f"  {r[0] or 'NULL':15s}: {r[1]:>8,}")

# Campsite types — full list
p("\nAll campsite types:")
for r in query("SELECT campsite_type, COUNT(*) c FROM campsites GROUP BY campsite_type ORDER BY c DESC"):
    p(f"  {r[0] or 'NULL':45s}: {r[1]:>8,}")

# Reservable
p("\nReservable campsites:")
for r in query("SELECT campsite_reservable, COUNT(*) FROM campsites GROUP BY campsite_reservable"):
    label = "Yes" if r[0] == 1 else "No"
    p(f"  {label}: {r[1]:,}")

# Accessible
p("\nAccessible campsites:")
for r in query("SELECT campsite_accessible, COUNT(*) FROM campsites GROUP BY campsite_accessible"):
    label = "Yes" if r[0] == 1 else "No"
    p(f"  {label}: {r[1]:,}")

# Coordinate quality
p("\nCampsite coordinate quality:")
for r in query("""SELECT
    SUM(CASE WHEN campsite_latitude != 0 AND campsite_longitude != 0 THEN 1 ELSE 0 END) valid,
    SUM(CASE WHEN campsite_latitude = 0 AND campsite_longitude = 0 THEN 1 ELSE 0 END) zero
FROM campsites"""):
    p(f"  Valid: {r[0]:,}")
    p(f"  Zero: {r[1]:,}")

# Loop field
p("\nLoop field (campsite grouping within facility):")
has_loop = query("SELECT COUNT(*) FROM campsites WHERE loop != '' AND loop IS NOT NULL")[0][0]
unique_loops = query("SELECT COUNT(DISTINCT loop) FROM campsites WHERE loop != '' AND loop IS NOT NULL")[0][0]
p(f"  Has loop value: {has_loop:,}")
p(f"  Unique loop names: {unique_loops:,}")

# ============================================================
section(6, "CAMPSITE ATTRIBUTES - Complete inventory")
# ============================================================

p("Total attribute records: {:,}".format(query("SELECT COUNT(*) FROM campsite_attributes")[0][0]))
p("Unique attribute names: {:,}".format(query("SELECT COUNT(DISTINCT attribute_name) FROM campsite_attributes")[0][0]))

p("\nAll attributes by frequency:")
for r in query("""SELECT attribute_name, COUNT(*) cnt,
    COUNT(DISTINCT attribute_value) unique_vals
    FROM campsite_attributes
    GROUP BY attribute_name ORDER BY cnt DESC"""):
    p(f"  {r[0]:45s}: {r[1]:>10,} records, {r[2]:>6,} unique values")

# For each major attribute, show full value distribution
major_attrs = [
    "Driveway Entry", "Driveway Surface", "Driveway Length", "Driveway Grade",
    "Max Vehicle Length", "Site Access", "Water Hookup", "Sewer Hookup",
    "Electricity Hookup", "Full Hookup", "Double Driveway",
    "Capacity/Size Rating", "Shade", "Proximity to Water",
    "Shower/Bath Type", "Accessibility",
    "IS EQUIPMENT MANDATORY", "Campfire Allowed", "Pets Allowed",
    "Site Rating", "Condition Rating", "Location Rating",
    "Checkout Time", "Checkin Time"
]

for attr in major_attrs:
    rows = query("""SELECT attribute_value, COUNT(*) c
        FROM campsite_attributes WHERE attribute_name = ?
        GROUP BY attribute_value ORDER BY c DESC""", (attr,))
    if rows:
        total = sum(r[1] for r in rows)
        p(f"\n  --- {attr} ({total:,} records, {len(rows)} unique values) ---")
        for r in rows[:25]:  # top 25 values
            pct = r[1] / total * 100
            p(f"    {repr(r[0]):40s}: {r[1]:>8,} ({pct:5.1f}%)")
        if len(rows) > 25:
            p(f"    ... and {len(rows)-25} more values")

# ============================================================
section(7, "CAMPSITE EQUIPMENT - Complete inventory")
# ============================================================

p("Total equipment records: {:,}".format(query("SELECT COUNT(*) FROM campsite_equipment")[0][0]))
p("Unique equipment names: {:,}".format(query("SELECT COUNT(DISTINCT equipment_name) FROM campsite_equipment")[0][0]))

p("\nAll equipment types:")
for r in query("""SELECT equipment_name, COUNT(*) cnt,
    COUNT(DISTINCT campsite_id) sites,
    MIN(CASE WHEN max_length > 0 THEN max_length END) min_len,
    MAX(max_length) max_len,
    AVG(CASE WHEN max_length > 0 THEN max_length END) avg_len,
    SUM(CASE WHEN max_length = 0 THEN 1 ELSE 0 END) zero_len
    FROM campsite_equipment GROUP BY equipment_name ORDER BY cnt DESC"""):
    p(f"  {r[0]:30s}: {r[1]:>8,} records | len: {r[3] or 0:.0f}-{r[4]:.0f}ft (avg {r[5] or 0:.0f}) | zero_len: {r[6]:,}")

# Max length distribution for RV specifically
p("\nRV max_length distribution:")
for r in query("""
    SELECT
        CASE
            WHEN max_length = 0 THEN '0 (zero/unknown)'
            WHEN max_length BETWEEN 1 AND 15 THEN '1-15 ft'
            WHEN max_length BETWEEN 16 AND 20 THEN '16-20 ft'
            WHEN max_length BETWEEN 21 AND 25 THEN '21-25 ft'
            WHEN max_length BETWEEN 26 AND 30 THEN '26-30 ft'
            WHEN max_length BETWEEN 31 AND 35 THEN '31-35 ft'
            WHEN max_length BETWEEN 36 AND 40 THEN '36-40 ft'
            WHEN max_length BETWEEN 41 AND 45 THEN '41-45 ft'
            WHEN max_length BETWEEN 46 AND 60 THEN '46-60 ft'
            WHEN max_length > 60 THEN '60+ ft'
        END bucket,
        COUNT(*) cnt
    FROM campsite_equipment
    WHERE equipment_name = 'RV'
    GROUP BY bucket ORDER BY MIN(max_length)
"""):
    p(f"  {r[0]:25s}: {r[1]:>8,}")

# ============================================================
section(8, "ORGANIZATIONS - Deep look")
# ============================================================

p("All organizations with facility and campsite stats:")
for r in query("""
    SELECT o.org_id, o.org_abbrev, o.org_name, o.org_type,
        COUNT(DISTINCT f.facility_id) facs,
        SUM(CASE WHEN f.facility_type = 'Campground' THEN 1 ELSE 0 END) campgrounds,
        SUM(CASE WHEN f.facility_type = 'Facility' THEN 1 ELSE 0 END) generic,
        SUM(CASE WHEN f.reservable = 1 THEN 1 ELSE 0 END) reservable,
        SUM(CASE WHEN f.facility_latitude != 0 THEN 1 ELSE 0 END) has_coords,
        SUM(CASE WHEN f.facility_description != '' AND f.facility_description IS NOT NULL THEN 1 ELSE 0 END) has_desc
    FROM organizations o
    LEFT JOIN facilities f ON o.org_id = f.parent_org_id
    GROUP BY o.org_id ORDER BY facs DESC
"""):
    p(f"  {r[1]:8s} {r[2]:45s}")
    p(f"         type={r[3]:15s} facs={r[4]:>5,} campgr={r[5]:>5,} generic={r[6]:>5,} resv={r[7]:>5,} coords={r[8]:>5,} desc={r[9]:>5,}")

# ============================================================
section(9, "REC AREAS <-> FACILITIES relationship")
# ============================================================

total_ra = query("SELECT COUNT(*) FROM rec_areas")[0][0]
p(f"Total rec areas: {total_ra:,}")

# How many facilities link to a rec area
fac_w_ra = query("SELECT COUNT(*) FROM facilities WHERE parent_rec_area_id != '' AND parent_rec_area_id IS NOT NULL")[0][0]
fac_wo_ra = total_fac - fac_w_ra
p(f"Facilities with parent rec area: {fac_w_ra:,}")
p(f"Facilities without: {fac_wo_ra:,}")

# Rec areas with facilities
ra_w_fac = query("""SELECT COUNT(DISTINCT parent_rec_area_id)
    FROM facilities WHERE parent_rec_area_id != '' AND parent_rec_area_id IS NOT NULL""")[0][0]
p(f"Rec areas referenced by facilities: {ra_w_fac:,}")
p(f"Rec areas with no facilities linked: {total_ra - ra_w_fac:,}")

# Rec area coordinate quality
p("\nRec area coordinates:")
for r in query("""SELECT
    SUM(CASE WHEN rec_area_latitude != 0 AND rec_area_longitude != 0 THEN 1 ELSE 0 END) valid,
    SUM(CASE WHEN rec_area_latitude = 0 AND rec_area_longitude = 0 THEN 1 ELSE 0 END) zero
FROM rec_areas"""):
    p(f"  Valid: {r[0]:,}")
    p(f"  Zero: {r[1]:,}")

# Rec area descriptions
p("\nRec area description completeness:")
has_desc = query("SELECT COUNT(*) FROM rec_areas WHERE rec_area_description != '' AND rec_area_description IS NOT NULL")[0][0]
has_dir = query("SELECT COUNT(*) FROM rec_areas WHERE rec_area_directions != '' AND rec_area_directions IS NOT NULL")[0][0]
p(f"  Has description: {has_desc:,} / {total_ra:,}")
p(f"  Has directions: {has_dir:,} / {total_ra:,}")

# ============================================================
section(10, "LINKS - What URLs exist")
# ============================================================

p("Total links: {:,}".format(query("SELECT COUNT(*) FROM links")[0][0]))
p("\nBy link_type and entity_type:")
for r in query("""SELECT link_type, entity_type, COUNT(*) c
    FROM links GROUP BY link_type, entity_type ORDER BY c DESC"""):
    p(f"  {r[0]:35s} ({r[1]:10s}): {r[2]:>6,}")

# Links per facility
p("\nFacility link coverage:")
fac_w_links = query("""SELECT COUNT(DISTINCT entity_id) FROM links
    WHERE entity_type = 'Facility'""")[0][0]
p(f"  Facilities with links: {fac_w_links:,} / {total_fac:,}")

# URL domains
p("\nTop URL domains in links:")
for r in query("""
    SELECT
        CASE
            WHEN url LIKE '%recreation.gov%' THEN 'recreation.gov'
            WHEN url LIKE '%fs.usda.gov%' OR url LIKE '%fs.fed.us%' THEN 'fs.usda.gov'
            WHEN url LIKE '%nps.gov%' THEN 'nps.gov'
            WHEN url LIKE '%blm.gov%' THEN 'blm.gov'
            WHEN url LIKE '%usace.army.mil%' OR url LIKE '%sam.usace%' THEN 'usace.army.mil'
            WHEN url LIKE '%fws.gov%' THEN 'fws.gov'
            WHEN url LIKE '%usbr.gov%' THEN 'usbr.gov'
            WHEN url LIKE '%facebook.com%' THEN 'facebook.com'
            WHEN url LIKE '%youtube.com%' THEN 'youtube.com'
            WHEN url LIKE '%instagram.com%' THEN 'instagram.com'
            WHEN url LIKE '%twitter.com%' OR url LIKE '%x.com%' THEN 'twitter/x.com'
            WHEN url LIKE '%google.com%' THEN 'google.com'
            ELSE 'other'
        END domain,
        COUNT(*) c
    FROM links WHERE url != '' GROUP BY domain ORDER BY c DESC
"""):
    p(f"  {r[0]:25s}: {r[1]:>6,}")

# ============================================================
section(11, "FACILITY ACTIVITIES - What activities exist")
# ============================================================

p("Total activity assignments: {:,}".format(query("SELECT COUNT(*) FROM facility_activities")[0][0]))
p("Unique activities: {:,}".format(query("SELECT COUNT(DISTINCT activity_name) FROM facility_activities")[0][0]))
p("Facilities with activities: {:,}".format(query("SELECT COUNT(DISTINCT facility_id) FROM facility_activities")[0][0]))

p("\nAll activities:")
for r in query("""SELECT activity_name, COUNT(*) c, COUNT(DISTINCT facility_id) facs
    FROM facility_activities GROUP BY activity_name ORDER BY c DESC"""):
    p(f"  {r[0]:45s}: {r[1]:>6,} assignments ({r[2]:>5,} facilities)")

# ============================================================
section(12, "CROSS-REFERENCE: Campsite type vs attributes present")
# ============================================================

p("Which campsite types have which attributes (% of sites with that attribute):")
types_to_check = ['STANDARD NONELECTRIC', 'STANDARD ELECTRIC', 'RV NONELECTRIC',
                   'RV ELECTRIC', 'TENT ONLY NONELECTRIC', 'MANAGEMENT',
                   'CABIN NONELECTRIC', 'CABIN ELECTRIC', 'WALK TO', 'BOAT IN']
attrs_to_check = ['Driveway Entry', 'Driveway Surface', 'Max Vehicle Length',
                   'Water Hookup', 'Sewer Hookup', 'Electricity Hookup',
                   'Pets Allowed', 'Campfire Allowed', 'Site Access']

# Build header
header = f"{'Type':30s}"
for a in attrs_to_check:
    header += f" {a[:8]:>8s}"
p(header)
p("-" * len(header))

for ct in types_to_check:
    total = query("SELECT COUNT(*) FROM campsites WHERE campsite_type = ?", (ct,))[0][0]
    row = f"{ct:30s}"
    for attr in attrs_to_check:
        has = query("""SELECT COUNT(DISTINCT cs.campsite_id)
            FROM campsites cs
            JOIN campsite_attributes ca ON cs.campsite_id = ca.campsite_id
            WHERE cs.campsite_type = ? AND ca.attribute_name = ?""", (ct, attr))[0][0]
        pct = has / total * 100 if total > 0 else 0
        row += f" {pct:>7.0f}%"
    p(row)

# ============================================================
section(13, "CROSS-REFERENCE: Campsite type vs equipment present")
# ============================================================

p("Which campsite types allow which equipment (% of sites):")
equip_to_check = ['RV', 'Trailer', 'FIFTH WHEEL', 'Tent', 'SMALL TENT',
                   'PICKUP CAMPER', 'CARAVAN/CAMPER VAN', 'Boat']

header = f"{'Type':30s}"
for e in equip_to_check:
    header += f" {e[:8]:>8s}"
p(header)
p("-" * len(header))

for ct in types_to_check:
    total = query("SELECT COUNT(*) FROM campsites WHERE campsite_type = ?", (ct,))[0][0]
    row = f"{ct:30s}"
    for equip in equip_to_check:
        has = query("""SELECT COUNT(DISTINCT cs.campsite_id)
            FROM campsites cs
            JOIN campsite_equipment ce ON cs.campsite_id = ce.campsite_id
            WHERE cs.campsite_type = ? AND ce.equipment_name = ?""", (ct, equip))[0][0]
        pct = has / total * 100 if total > 0 else 0
        row += f" {pct:>7.0f}%"
    p(row)

# ============================================================
section(14, "PERMIT ENTRANCES")
# ============================================================

p("Total: {:,}".format(query("SELECT COUNT(*) FROM permit_entrances")[0][0]))
p("\nBy type:")
for r in query("""SELECT permit_entrance_type, COUNT(*) FROM permit_entrances
    GROUP BY permit_entrance_type ORDER BY COUNT(*) DESC"""):
    p(f"  {r[0] or 'NULL':30s}: {r[1]:>5,}")

# ============================================================
section(15, "ADDRESSES - State coverage")
# ============================================================

p("Facility addresses:")
p(f"  Total address records: {query('SELECT COUNT(*) FROM facility_addresses')[0][0]:,}")
empty = ""
p(f"  Unique states: {query('SELECT COUNT(DISTINCT state_code) FROM facility_addresses WHERE state_code != ?', (empty,))[0][0]}")

p("\nAll states/territories represented:")
for r in query("""SELECT state_code, COUNT(*) c FROM facility_addresses
    WHERE state_code != '' GROUP BY state_code ORDER BY c DESC"""):
    p(f"  {r[0]:5s}: {r[1]:>6,}")

p("\nRec area addresses:")
p(f"  Total: {query('SELECT COUNT(*) FROM rec_area_addresses')[0][0]:,}")
p(f"  Unique states: {query('SELECT COUNT(DISTINCT state_code) FROM rec_area_addresses WHERE state_code != ?', (empty,))[0][0]}")

# ============================================================
section(16, "DATA FRESHNESS - Last updated dates")
# ============================================================

p("Facility last_updated distribution:")
for r in query("""SELECT SUBSTR(last_updated, 1, 4) year, COUNT(*) c
    FROM facilities WHERE last_updated != '' GROUP BY year ORDER BY year"""):
    p(f"  {r[0]}: {r[1]:>6,}")

p("\nCampsite last_updated distribution:")
for r in query("""SELECT SUBSTR(last_updated, 1, 4) year, COUNT(*) c
    FROM campsites WHERE last_updated != '' AND last_updated IS NOT NULL GROUP BY year ORDER BY year"""):
    p(f"  {r[0]}: {r[1]:>6,}")

p("\nRec area last_updated distribution:")
for r in query("""SELECT SUBSTR(last_updated, 1, 4) year, COUNT(*) c
    FROM rec_areas WHERE last_updated != '' GROUP BY year ORDER BY year"""):
    p(f"  {r[0]}: {r[1]:>6,}")

# ============================================================
section(17, "EDGE CASES AND ANOMALIES")
# ============================================================

# Campsites that belong to facilities not in our facilities table
p("Orphaned campsites (facility_id not in facilities table):")
orphans = query("""SELECT COUNT(*) FROM campsites
    WHERE facility_id NOT IN (SELECT facility_id FROM facilities)""")[0][0]
p(f"  {orphans:,}")

# Facilities with campsites but type != Campground
p("\nNon-Campground facilities that have campsites:")
for r in query("""SELECT f.facility_type, COUNT(DISTINCT f.facility_id) facs, COUNT(cs.campsite_id) sites
    FROM facilities f
    JOIN campsites cs ON f.facility_id = cs.facility_id
    WHERE f.facility_type != 'Campground'
    GROUP BY f.facility_type ORDER BY sites DESC"""):
    p(f"  {r[0]:30s}: {r[1]:>5,} facilities, {r[2]:>6,} campsites")

# Campsites with type 'MANAGEMENT' — what are these?
p("\nMANAGEMENT campsites — deeper look:")
mgmt_type = "MANAGEMENT"
p(f"  Total: {query('SELECT COUNT(*) FROM campsites WHERE campsite_type = ?', (mgmt_type,))[0][0]:,}")
p(f"  Reservable: {query('SELECT SUM(campsite_reservable) FROM campsites WHERE campsite_type = ?', (mgmt_type,))[0][0]:,}")
mgmt_equip = query("""SELECT ce.equipment_name, COUNT(*) FROM campsites cs
    JOIN campsite_equipment ce ON cs.campsite_id = ce.campsite_id
    WHERE cs.campsite_type = 'MANAGEMENT'
    GROUP BY ce.equipment_name ORDER BY COUNT(*) DESC LIMIT 5""")
if mgmt_equip:
    p(f"  Top equipment: {', '.join(f'{r[0]}({r[1]:,})' for r in mgmt_equip)}")

# Duplicate facility names
p("\nMost common facility names (possible duplicates):")
for r in query("""SELECT facility_name, COUNT(*) c FROM facilities
    GROUP BY facility_name HAVING c > 3 ORDER BY c DESC LIMIT 15"""):
    p(f"  {r[0]:45s}: {r[1]:>3} occurrences")

# Campsites with negative or absurd coordinates
p("\nCampsites with potentially bad non-zero coords:")
bad = query("""SELECT COUNT(*) FROM campsites
    WHERE campsite_latitude != 0
    AND (campsite_latitude < -90 OR campsite_latitude > 90
         OR campsite_longitude < -180 OR campsite_longitude > 180)""")[0][0]
p(f"  Out of range: {bad:,}")

# Facilities with identical lat/lon (might be copy-paste errors)
p("\nMost-shared facility coordinates (potential data entry errors):")
for r in query("""SELECT facility_latitude, facility_longitude, COUNT(*) c
    FROM facilities
    WHERE facility_latitude != 0 AND facility_longitude != 0
    GROUP BY facility_latitude, facility_longitude
    HAVING c > 5
    ORDER BY c DESC LIMIT 10"""):
    p(f"  ({r[0]:.6f}, {r[1]:.6f}): {r[2]:>4} facilities share this exact point")

p("\n\nAnalysis complete.")
conn.close()

# Write to file
with open("DB_ANALYSIS.md", "w") as f:
    f.write("# RIDB Database Analysis\n\n")
    f.write("Generated from `ridb.db` — raw analysis, no assumptions.\n\n")
    f.write("```\n")
    f.write("\n".join(out))
    f.write("\n```\n")

print("\nWritten to DB_ANALYSIS.md")
