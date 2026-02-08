
section(9, "REC AREAS <-> FACILITIES relationship")

total_ra = query("SELECT COUNT(*) FROM rec_areas")[0][0]
p(f"Total rec areas: {total_ra:,}")

fac_w_ra = query("SELECT COUNT(*) FROM facilities WHERE parent_rec_area_id != '' AND parent_rec_area_id IS NOT NULL")[0][0]
fac_wo_ra = total_fac - fac_w_ra
p(f"Facilities with parent rec area: {fac_w_ra:,}")
p(f"Facilities without: {fac_wo_ra:,}")

ra_w_fac = query("""SELECT COUNT(DISTINCT parent_rec_area_id)
    FROM facilities WHERE parent_rec_area_id != '' AND parent_rec_area_id IS NOT NULL""")[0][0]
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
has_desc = query("SELECT COUNT(*) FROM rec_areas WHERE rec_area_description != '' AND rec_area_description IS NOT NULL")[0][0]
has_dir = query("SELECT COUNT(*) FROM rec_areas WHERE rec_area_directions != '' AND rec_area_directions IS NOT NULL")[0][0]
p(f"  Has description: {has_desc:,} / {total_ra:,}")
p(f"  Has directions: {has_dir:,} / {total_ra:,}")
