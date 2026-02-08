"""Part 5: Sections 14-17 — Permits, Addresses, Data Freshness, Edge Cases"""
import sqlite3

DB_PATH = "ridb.db"
conn = sqlite3.connect(DB_PATH)
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
section(14, "PERMIT ENTRANCES")
# ============================================================

p("Total: {:,}".format(query("SELECT COUNT(*) FROM permit_entrances")[0][0]))
p("\nBy type:")
for r in query("""SELECT permit_entrance_type, COUNT(*) FROM permit_entrances
    GROUP BY permit_entrance_type ORDER BY COUNT(*) DESC"""):
    p(f"  {r[0] or 'NULL':30s}: {r[1]:>5,}")

# Which facilities have permits
p("\nFacilities with permit entrances:")
fac_w_permits = query("SELECT COUNT(DISTINCT facility_id) FROM permit_entrances")[0][0]
p(f"  {fac_w_permits:,} facilities")

# Permits by org
p("\nPermit entrances by organization:")
for r in query("""SELECT o.org_abbrev, COUNT(*) c
    FROM permit_entrances pe
    JOIN facilities f ON pe.facility_id = f.facility_id
    JOIN organizations o ON f.parent_org_id = o.org_id
    GROUP BY o.org_id ORDER BY c DESC"""):
    p(f"  {r[0]:8s}: {r[1]:>5,}")

# ============================================================
section(15, "ADDRESSES - State coverage")
# ============================================================

p("Facility addresses:")
p(f"  Total address records: {query('SELECT COUNT(*) FROM facility_addresses')[0][0]:,}")
empty = ""
unique_states = query('SELECT COUNT(DISTINCT state_code) FROM facility_addresses WHERE state_code != ?', (empty,))[0][0]
p(f"  Unique states: {unique_states}")

p("\nAll states/territories represented:")
for r in query("""SELECT state_code, COUNT(*) c FROM facility_addresses
    WHERE state_code != '' GROUP BY state_code ORDER BY c DESC"""):
    p(f"  {r[0]:5s}: {r[1]:>6,}")

p("\nRec area addresses:")
p(f"  Total: {query('SELECT COUNT(*) FROM rec_area_addresses')[0][0]:,}")
unique_ra_states = query('SELECT COUNT(DISTINCT state_code) FROM rec_area_addresses WHERE state_code != ?', (empty,))[0][0]
p(f"  Unique states: {unique_ra_states}")

# Facilities without addresses
p("\nFacilities without any address record:")
total_fac = query("SELECT COUNT(*) FROM facilities")[0][0]
fac_w_addr = query("SELECT COUNT(DISTINCT facility_id) FROM facility_addresses")[0][0]
p(f"  {total_fac - fac_w_addr:,} facilities have no address")

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

# Most recently updated
p("\nMost recently updated facilities (top 10):")
for r in query("""SELECT facility_name, last_updated FROM facilities
    WHERE last_updated != '' ORDER BY last_updated DESC LIMIT 10"""):
    p(f"  {r[1]:25s} {r[0]}")

p("\nOldest last_updated facilities (top 10):")
for r in query("""SELECT facility_name, last_updated FROM facilities
    WHERE last_updated != '' ORDER BY last_updated ASC LIMIT 10"""):
    p(f"  {r[1]:25s} {r[0]}")

# ============================================================
section(17, "EDGE CASES AND ANOMALIES")
# ============================================================

# Orphaned campsites
p("Orphaned campsites (facility_id not in facilities table):")
orphans = query("""SELECT COUNT(*) FROM campsites
    WHERE facility_id NOT IN (SELECT facility_id FROM facilities)""")[0][0]
p(f"  {orphans:,}")

# Non-Campground facilities with campsites
p("\nNon-Campground facilities that have campsites:")
for r in query("""SELECT f.facility_type, COUNT(DISTINCT f.facility_id) facs, COUNT(cs.campsite_id) sites
    FROM facilities f
    JOIN campsites cs ON f.facility_id = cs.facility_id
    WHERE f.facility_type != 'Campground'
    GROUP BY f.facility_type ORDER BY sites DESC"""):
    p(f"  {r[0]:30s}: {r[1]:>5,} facilities, {r[2]:>6,} campsites")

# MANAGEMENT campsites
mgmt_type = "MANAGEMENT"
p("\nMANAGEMENT campsites — deeper look:")
p(f"  Total: {query('SELECT COUNT(*) FROM campsites WHERE campsite_type = ?', (mgmt_type,))[0][0]:,}")
resv = query('SELECT SUM(campsite_reservable) FROM campsites WHERE campsite_type = ?', (mgmt_type,))[0][0]
p(f"  Reservable: {resv or 0:,}")
mgmt_equip = query("""SELECT ce.equipment_name, COUNT(*) FROM campsites cs
    JOIN campsite_equipment ce ON cs.campsite_id = ce.campsite_id
    WHERE cs.campsite_type = 'MANAGEMENT'
    GROUP BY ce.equipment_name ORDER BY COUNT(*) DESC LIMIT 5""")
if mgmt_equip:
    p(f"  Top equipment: {', '.join(f'{r[0]}({r[1]:,})' for r in mgmt_equip)}")

# MANAGEMENT campsite orgs
p("\n  MANAGEMENT campsites by org:")
for r in query("""SELECT o.org_abbrev, COUNT(*) c
    FROM campsites cs
    JOIN facilities f ON cs.facility_id = f.facility_id
    JOIN organizations o ON f.parent_org_id = o.org_id
    WHERE cs.campsite_type = 'MANAGEMENT'
    GROUP BY o.org_id ORDER BY c DESC"""):
    p(f"    {r[0]:8s}: {r[1]:>6,}")

# Duplicate facility names
p("\nMost common facility names (possible duplicates):")
for r in query("""SELECT facility_name, COUNT(*) c FROM facilities
    GROUP BY facility_name HAVING c > 3 ORDER BY c DESC LIMIT 15"""):
    p(f"  {r[0]:45s}: {r[1]:>3} occurrences")

# Bad coords
p("\nCampsites with potentially bad non-zero coords:")
bad = query("""SELECT COUNT(*) FROM campsites
    WHERE campsite_latitude != 0
    AND (campsite_latitude < -90 OR campsite_latitude > 90
         OR campsite_longitude < -180 OR campsite_longitude > 180)""")[0][0]
p(f"  Out of range: {bad:,}")

# Shared coordinates
p("\nMost-shared facility coordinates (potential data entry errors):")
for r in query("""SELECT facility_latitude, facility_longitude, COUNT(*) c
    FROM facilities
    WHERE facility_latitude != 0 AND facility_longitude != 0
    GROUP BY facility_latitude, facility_longitude
    HAVING c > 5
    ORDER BY c DESC LIMIT 10"""):
    p(f"  ({r[0]:.6f}, {r[1]:.6f}): {r[2]:>4} facilities share this exact point")

# Facilities with description containing RV keywords
p("\nFacility descriptions mentioning RV-related terms:")
rv_terms = [
    ("rv", "RV"),
    ("motorhome", "motorhome"),
    ("fifth wheel", "fifth wheel"),
    ("hookup", "hookup"),
    ("dump station", "dump station"),
    ("pull-through", "pull-through"),
    ("pull through", "pull through"),
    ("full hook", "full hook"),
    ("electric hook", "electric hook"),
    ("water hook", "water hook"),
    ("sewer hook", "sewer hook"),
    ("30 amp", "30 amp"),
    ("50 amp", "50 amp"),
    ("generator", "generator"),
    ("slide out", "slide out"),
    ("slideout", "slideout"),
    ("not recommended for rv", "not recommended for rv"),
    ("no rv", "no rv"),
    ("gravel road", "gravel road"),
    ("dirt road", "dirt road"),
    ("paved road", "paved road"),
    ("high clearance", "high clearance"),
    ("4wd", "4wd"),
    ("four wheel", "four wheel"),
    ("dispersed", "dispersed"),
    ("primitive", "primitive"),
    ("boondock", "boondock"),
    ("dry camp", "dry camp"),
    ("vault toilet", "vault toilet"),
    ("potable water", "potable water"),
]
for term_sql, term_label in rv_terms:
    cnt = query(f"SELECT COUNT(*) FROM facilities WHERE LOWER(facility_description) LIKE ?",
                (f"%{term_sql}%",))[0][0]
    if cnt > 0:
        p(f"  '{term_label}': {cnt:>6,} facilities")

# Campsites with conflicting data
p("\nCampsites typed 'TENT ONLY' but with RV equipment:")
tent_w_rv = query("""SELECT COUNT(DISTINCT cs.campsite_id)
    FROM campsites cs
    JOIN campsite_equipment ce ON cs.campsite_id = ce.campsite_id
    WHERE cs.campsite_type LIKE '%TENT%'
    AND ce.equipment_name IN ('RV', 'Trailer', 'FIFTH WHEEL')""")[0][0]
p(f"  {tent_w_rv:,}")

p("\nCampsites typed 'RV' but with NO RV/Trailer equipment:")
rv_no_equip = query("""SELECT COUNT(*) FROM campsites cs
    WHERE cs.campsite_type LIKE '%RV%'
    AND cs.campsite_id NOT IN (
        SELECT campsite_id FROM campsite_equipment
        WHERE equipment_name IN ('RV', 'Trailer', 'FIFTH WHEEL', 'PICKUP CAMPER')
    )""")[0][0]
p(f"  {rv_no_equip:,}")

# Day use vs overnight
p("\nType of use breakdown by campsite type:")
for r in query("""SELECT campsite_type, type_of_use, COUNT(*) c
    FROM campsites
    GROUP BY campsite_type, type_of_use
    ORDER BY campsite_type, c DESC"""):
    p(f"  {r[0]:35s} {r[1]:12s}: {r[2]:>8,}")

conn.close()

with open("analysis_part5.txt", "w") as f:
    f.write("\n".join(out))
print("\n=== Part 5 complete, written to analysis_part5.txt ===")
