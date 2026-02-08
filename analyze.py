"""
Deep analysis of RIDB data for RV classification.

Goals:
1. Understand what the data actually says (not what we assume)
2. Find every inconsistency and document it
3. Build a normalization strategy
4. Compute honest facility-level aggregations from campsite data
"""
import sqlite3
import sys

DB_PATH = "ridb.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

# ============================================================
section("1. ATTRIBUTE NAMES - Every unique attribute in the dataset")
# ============================================================
c.execute("""
    SELECT attribute_name, COUNT(*) cnt,
           COUNT(DISTINCT campsite_id) sites
    FROM campsite_attributes
    GROUP BY attribute_name
    ORDER BY cnt DESC
""")
print(f"{'Attribute Name':45s} {'Count':>10s} {'Sites':>10s}")
print("-" * 67)
for r in c.fetchall():
    print(f"{r[0]:45s} {r[1]:>10,} {r[2]:>10,}")

# ============================================================
section("2. EQUIPMENT NAMES - Every unique equipment type")
# ============================================================
c.execute("""
    SELECT equipment_name, COUNT(*) cnt,
           COUNT(DISTINCT campsite_id) sites,
           ROUND(AVG(CASE WHEN max_length > 0 THEN max_length END), 1) avg_len,
           MAX(max_length) max_len,
           MIN(CASE WHEN max_length > 0 THEN max_length END) min_len
    FROM campsite_equipment
    GROUP BY equipment_name
    ORDER BY cnt DESC
""")
print(f"{'Equipment':30s} {'Count':>8s} {'Sites':>8s} {'AvgLen':>8s} {'MaxLen':>8s} {'MinLen':>8s}")
print("-" * 73)
for r in c.fetchall():
    print(f"{r[0]:30s} {r[1]:>8,} {r[2]:>8,} {str(r[3] or ''):>8s} {str(r[4] or ''):>8s} {str(r[5] or ''):>8s}")

# ============================================================
section("3. CAMPSITE TYPES - Full distribution")
# ============================================================
c.execute("""
    SELECT campsite_type, COUNT(*) cnt,
           SUM(campsite_reservable) reservable,
           type_of_use,
           COUNT(DISTINCT facility_id) facilities
    FROM campsites
    GROUP BY campsite_type, type_of_use
    ORDER BY cnt DESC
""")
print(f"{'Type':45s} {'Use':>10s} {'Count':>8s} {'Resv':>8s} {'Facs':>6s}")
print("-" * 80)
for r in c.fetchall():
    print(f"{r[0] or 'NULL':45s} {r[3] or 'NULL':>10s} {r[1]:>8,} {r[2]:>8,} {r[4]:>6,}")

# ============================================================
section("4. DRIVEWAY ENTRY - The pull-through vs back-in mess")
# ============================================================
c.execute("""
    SELECT attribute_value, COUNT(*) cnt
    FROM campsite_attributes
    WHERE attribute_name = 'Driveway Entry'
    GROUP BY attribute_value
    ORDER BY cnt DESC
""")
print(f"{'Value':35s} {'Count':>10s} {'Normalized':>20s}")
print("-" * 67)
for r in c.fetchall():
    val = r[0] or ''
    low = val.strip().lower()
    if 'pull' in low or 'thru' in low or 'through' in low:
        norm = 'PULL-THROUGH'
    elif 'back' in low:
        norm = 'BACK-IN'
    elif 'parallel' in low:
        norm = 'PARALLEL'
    elif low in ('', 'n/a', 'na'):
        norm = 'UNKNOWN'
    else:
        norm = f'??? ({val})'
    print(f"{repr(val):35s} {r[1]:>10,} {norm:>20s}")

# ============================================================
section("5. HOOKUP VALUES - Water, Sewer, Electric inconsistency")
# ============================================================
for attr in ['Water Hookup', 'Sewer Hookup', 'Electricity Hookup']:
    print(f"\n  --- {attr} ---")
    c.execute("""
        SELECT attribute_value, COUNT(*) cnt
        FROM campsite_attributes
        WHERE attribute_name = ?
        GROUP BY attribute_value
        ORDER BY cnt DESC
    """, (attr,))
    total_with = 0
    total_without = 0
    for r in c.fetchall():
        val = r[0] or ''
        low = val.strip().lower()
        # Determine if this means "has hookup"
        if attr == 'Electricity Hookup':
            has = low not in ('', 'n/a', 'na', 'no', '0', 'none')
        else:
            has = low in ('yes', 'y') or low == attr.lower().replace(' hookup', ' hookup')

        marker = 'YES' if has else 'no'
        print(f"    {repr(val):35s} {r[1]:>8,}  -> {marker}")
        if has:
            total_with += r[1]
        else:
            total_without += r[1]

    c.execute("SELECT COUNT(DISTINCT campsite_id) FROM campsite_attributes WHERE attribute_name = ?", (attr,))
    reported = c.fetchone()[0]
    print(f"    Has hookup: {total_with:,} | No hookup: {total_without:,} | Not reported: {132974 - reported:,}")

# ============================================================
section("6. MAX VEHICLE LENGTH - Zero vs missing vs real")
# ============================================================
c.execute("""
    SELECT
        CASE
            WHEN CAST(attribute_value AS INTEGER) = 0 THEN '0 (zero)'
            WHEN CAST(attribute_value AS INTEGER) BETWEEN 1 AND 15 THEN '1-15 ft (small)'
            WHEN CAST(attribute_value AS INTEGER) BETWEEN 16 AND 25 THEN '16-25 ft (med)'
            WHEN CAST(attribute_value AS INTEGER) BETWEEN 26 AND 35 THEN '26-35 ft (large)'
            WHEN CAST(attribute_value AS INTEGER) BETWEEN 36 AND 45 THEN '36-45 ft (xl)'
            WHEN CAST(attribute_value AS INTEGER) > 45 THEN '46+ ft (xxl)'
            ELSE 'non-numeric'
        END as bucket,
        COUNT(*) cnt,
        MIN(attribute_value) min_val,
        MAX(attribute_value) max_val
    FROM campsite_attributes
    WHERE attribute_name = 'Max Vehicle Length'
    GROUP BY bucket
    ORDER BY cnt DESC
""")
print(f"{'Bucket':25s} {'Count':>10s} {'Min':>10s} {'Max':>10s}")
print("-" * 57)
for r in c.fetchall():
    print(f"{r[0]:25s} {r[1]:>10,} {r[2]:>10s} {r[3]:>10s}")

c.execute("SELECT COUNT(DISTINCT campsite_id) FROM campsite_attributes WHERE attribute_name = 'Max Vehicle Length'")
reported = c.fetchone()[0]
print(f"\nReported: {reported:,} | Not reported: {132974 - reported:,}")

# ============================================================
section("7. FACILITY TYPES vs ACTUAL CAMPSITES")
# ============================================================
c.execute("""
    SELECT f.facility_type,
           COUNT(DISTINCT f.facility_id) total_facilities,
           COUNT(DISTINCT cs.facility_id) has_campsites,
           COUNT(cs.campsite_id) total_sites
    FROM facilities f
    LEFT JOIN campsites cs ON f.facility_id = cs.facility_id
    GROUP BY f.facility_type
    ORDER BY total_facilities DESC
""")
print(f"{'Facility Type':30s} {'Facilities':>12s} {'w/ Sites':>10s} {'Campsites':>12s}")
print("-" * 66)
for r in c.fetchall():
    pct = (r[2] / r[1] * 100) if r[1] > 0 else 0
    print(f"{r[0] or 'NULL':30s} {r[1]:>12,} {r[2]:>8,} ({pct:4.0f}%) {r[3]:>10,}")

# ============================================================
section("8. ORGANIZATIONS - Who actually has campgrounds")
# ============================================================
c.execute("""
    SELECT o.org_abbrev, o.org_name,
           COUNT(DISTINCT f.facility_id) total_fac,
           COUNT(DISTINCT CASE WHEN cs.campsite_id IS NOT NULL THEN f.facility_id END) fac_w_sites,
           COUNT(cs.campsite_id) total_sites,
           COUNT(DISTINCT CASE WHEN ce.equipment_name IN ('RV', 'RV/MOTORHOME') THEN cs.campsite_id END) rv_sites
    FROM facilities f
    JOIN organizations o ON f.parent_org_id = o.org_id
    LEFT JOIN campsites cs ON f.facility_id = cs.facility_id
    LEFT JOIN campsite_equipment ce ON cs.campsite_id = ce.campsite_id
    GROUP BY o.org_id
    HAVING total_fac > 5
    ORDER BY total_sites DESC
""")
print(f"{'Org':8s} {'Name':35s} {'Facs':>6s} {'w/Sites':>8s} {'Camps':>8s} {'RV':>8s}")
print("-" * 76)
for r in c.fetchall():
    print(f"{r[0]:8s} {r[1]:35s} {r[2]:>6,} {r[3]:>8,} {r[4]:>8,} {r[5]:>8,}")

# ============================================================
section("9. DISPERSED CAMPING SIGNALS - BLM/FS without reservations")
# ============================================================
c.execute("""
    SELECT o.org_abbrev,
           COUNT(DISTINCT f.facility_id) total,
           COUNT(DISTINCT CASE WHEN f.reservable = 0 THEN f.facility_id END) not_reservable,
           COUNT(DISTINCT CASE WHEN f.facility_reservation_url = '' OR f.facility_reservation_url IS NULL THEN f.facility_id END) no_res_url,
           COUNT(DISTINCT CASE WHEN cs.campsite_id IS NULL THEN f.facility_id END) no_campsites,
           COUNT(DISTINCT CASE WHEN f.facility_type = 'Facility' THEN f.facility_id END) generic_type
    FROM facilities f
    JOIN organizations o ON f.parent_org_id = o.org_id
    LEFT JOIN campsites cs ON f.facility_id = cs.facility_id
    WHERE o.org_abbrev IN ('BLM', 'FS', 'NPS', 'USACE', 'FWS', 'BOR')
    GROUP BY o.org_abbrev
    ORDER BY total DESC
""")
print(f"{'Org':8s} {'Total':>8s} {'NotResv':>8s} {'NoURL':>8s} {'NoCamps':>8s} {'Generic':>8s}")
print("-" * 49)
for r in c.fetchall():
    print(f"{r[0]:8s} {r[1]:>8,} {r[2]:>8,} {r[3]:>8,} {r[4]:>8,} {r[5]:>8,}")

# ============================================================
section("10. CAMPSITE TYPE vs EQUIPMENT - Cross reference")
# ============================================================
c.execute("""
    SELECT cs.campsite_type,
           COUNT(DISTINCT cs.campsite_id) total,
           COUNT(DISTINCT CASE WHEN ce.equipment_name IN ('RV', 'RV/MOTORHOME') THEN cs.campsite_id END) has_rv_equip,
           COUNT(DISTINCT CASE WHEN ce.equipment_name = 'Trailer' THEN cs.campsite_id END) has_trailer,
           COUNT(DISTINCT CASE WHEN ce.equipment_name = 'FIFTH WHEEL' THEN cs.campsite_id END) has_5th,
           COUNT(DISTINCT CASE WHEN ce.equipment_name = 'Tent' THEN cs.campsite_id END) has_tent
    FROM campsites cs
    LEFT JOIN campsite_equipment ce ON cs.campsite_id = ce.campsite_id
    GROUP BY cs.campsite_type
    HAVING total > 100
    ORDER BY total DESC
""")
print(f"{'Campsite Type':40s} {'Total':>8s} {'RV':>8s} {'Trail':>8s} {'5thWh':>8s} {'Tent':>8s}")
print("-" * 75)
for r in c.fetchall():
    print(f"{r[0] or 'NULL':40s} {r[1]:>8,} {r[2]:>8,} {r[3]:>8,} {r[4]:>8,} {r[5]:>8,}")

# ============================================================
section("11. COORDINATES QUALITY")
# ============================================================
c.execute("""
    SELECT
        'facilities' as entity,
        COUNT(*) total,
        SUM(CASE WHEN facility_latitude = 0 AND facility_longitude = 0 THEN 1 ELSE 0 END) zero_coords,
        SUM(CASE WHEN facility_latitude != 0 AND facility_longitude != 0 THEN 1 ELSE 0 END) valid_coords,
        SUM(CASE WHEN facility_latitude IS NULL OR facility_longitude IS NULL THEN 1 ELSE 0 END) null_coords
    FROM facilities
""")
r = c.fetchone()
print(f"Facilities: {r[1]:,} total | {r[3]:,} valid | {r[2]:,} zero | {r[4]:,} null")

c.execute("""
    SELECT
        'campsites' as entity,
        COUNT(*) total,
        SUM(CASE WHEN campsite_latitude = 0 AND campsite_longitude = 0 THEN 1 ELSE 0 END) zero_coords,
        SUM(CASE WHEN campsite_latitude != 0 AND campsite_longitude != 0 THEN 1 ELSE 0 END) valid_coords
    FROM campsites
""")
r = c.fetchone()
print(f"Campsites:  {r[1]:,} total | {r[3]:,} valid | {r[2]:,} zero")

# Facilities that HAVE campsites but zero coords themselves
c.execute("""
    SELECT COUNT(DISTINCT f.facility_id)
    FROM facilities f
    JOIN campsites cs ON f.facility_id = cs.facility_id
    WHERE f.facility_latitude = 0 AND f.facility_longitude = 0
""")
print(f"Facilities with campsites but zero coords: {c.fetchone()[0]:,}")

print("\n\nAnalysis complete.")
conn.close()
