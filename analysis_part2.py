"""Part 2: Sections 6-7 — Campsite Attributes and Equipment"""
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
        for r in rows[:25]:
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

conn.close()

with open("analysis_part2.txt", "w") as f:
    f.write("\n".join(out))
print("\n=== Part 2 complete, written to analysis_part2.txt ===")
