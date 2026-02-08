
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
