"""Part 3: Sections 8-11 — Organizations, Rec Areas, Links, Activities"""
import sqlite3

DB_PATH = "ridb.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

out = []
def p(s=""):
    out.append(s)
    print(s)

EQ80 = "=" * 80
def section(n, title):
    p(f"\n{EQ80}")
    p(f"  {n}. {title}")
    p(f"{EQ80}")

def query(sql, params=None):
    if params:
        c.execute(sql, params)
    else:
        c.execute(sql)
    return c.fetchall()

section(8, "ORGANIZATIONS - Deep look")

total_fac = query("SELECT COUNT(*) FROM facilities")[0][0]

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

p("\nCampsites per organization:")
for r in query("""
    SELECT o.org_abbrev, o.org_name,
        COUNT(DISTINCT f.facility_id) fac_w_sites,
        COUNT(cs.campsite_id) total_sites
    FROM organizations o
    JOIN facilities f ON o.org_id = f.parent_org_id
    JOIN campsites cs ON f.facility_id = cs.facility_id
    GROUP BY o.org_id ORDER BY total_sites DESC
"""):
    p(f"  {r[0]:8s} {r[1]:40s}: {r[2]:>5,} facilities, {r[3]:>8,} campsites")

section(9, "REC AREAS <-> FACILITIES relationship")

total_ra = query("SELECT COUNT(*) FROM rec_areas")[0][0]
p(f"Total rec areas: {total_ra:,}")

empty = ""
fac_w_ra = query("SELECT COUNT(*) FROM facilities WHERE parent_rec_area_id != ? AND parent_rec_area_id IS NOT NULL", (empty,))[0][0]
fac_wo_ra = total_fac - fac_w_ra
p(f"Facilities with parent rec area: {fac_w_ra:,}")
p(f"Facilities without: {fac_wo_ra:,}")

ra_w_fac = query("SELECT COUNT(DISTINCT parent_rec_area_id) FROM facilities WHERE parent_rec_area_id != ? AND parent_rec_area_id IS NOT NULL", (empty,))[0][0]
p(f"Rec areas referenced by facilities: {ra_w_fac:,}")
p(f"Rec areas with no facilities linked: {total_ra - ra_w_fac:,}")

p("\nRec area coordinates:")
for r in query("""SELECT
    SUM(CASE WHEN rec_area_latitude != 0 AND rec_area_longitude != 0 THEN 1 ELSE 0 END) valid,
    SUM(CASE WHEN rec_area_latitude = 0 AND rec_area_longitude = 0 THEN 1 ELSE 0 END) zero
FROM rec_areas"""):
    p(f"  Valid: {r[0]:,}")
    p(f"  Zero: {r[1]:,}")

p("\nRec area description completeness:")
has_desc = query("SELECT COUNT(*) FROM rec_areas WHERE rec_area_description != ? AND rec_area_description IS NOT NULL", (empty,))[0][0]
has_dir = query("SELECT COUNT(*) FROM rec_areas WHERE rec_area_directions != ? AND rec_area_directions IS NOT NULL", (empty,))[0][0]
p(f"  Has description: {has_desc:,} / {total_ra:,}")
p(f"  Has directions: {has_dir:,} / {total_ra:,}")

section(10, "LINKS - What URLs exist")

p("Total links: {:,}".format(query("SELECT COUNT(*) FROM links")[0][0]))
p("\nBy link_type and entity_type:")
for r in query("""SELECT link_type, entity_type, COUNT(*) c
    FROM links GROUP BY link_type, entity_type ORDER BY c DESC"""):
    p(f"  {r[0]:35s} ({r[1]:10s}): {r[2]:>6,}")

p("\nFacility link coverage:")
fac_w_links = query("SELECT COUNT(DISTINCT entity_id) FROM links WHERE entity_type = 'Facility'")[0][0]
p(f"  Facilities with links: {fac_w_links:,} / {total_fac:,}")

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

section(11, "FACILITY ACTIVITIES - What activities exist")

p("Total activity assignments: {:,}".format(query("SELECT COUNT(*) FROM facility_activities")[0][0]))
p("Unique activities: {:,}".format(query("SELECT COUNT(DISTINCT activity_name) FROM facility_activities")[0][0]))
p("Facilities with activities: {:,}".format(query("SELECT COUNT(DISTINCT facility_id) FROM facility_activities")[0][0]))

p("\nAll activities:")
for r in query("""SELECT activity_name, COUNT(*) c, COUNT(DISTINCT facility_id) facs
    FROM facility_activities GROUP BY activity_name ORDER BY c DESC"""):
    p(f"  {r[0]:45s}: {r[1]:>6,} assignments ({r[2]:>5,} facilities)")

conn.close()

with open("analysis_part3.txt", "w") as f:
    f.write("\n".join(out))
print("\n=== Part 3 complete, written to analysis_part3.txt ===")
