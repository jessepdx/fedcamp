"""Part 4: Sections 12-13 -- Cross-references: campsite type vs attributes and equipment"""
import sqlite3

DB_PATH = "ridb.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

out = []
def p(s=""):
    out.append(s)
    print(s)

def section(n, title):
    nl = chr(10)
    eq = "=" * 80
    p(nl + eq)
    p(f"  {n}. {title}")
    p(eq)

def query(sql, params=None):
    if params:
        c.execute(sql, params)
    else:
        c.execute(sql)
    return c.fetchall()

# ============================================================
section(12, "CROSS-REFERENCE: Campsite type vs attributes present")
# ============================================================

p("Which campsite types have which attributes (% of sites with that attribute):")
types_to_check = ["STANDARD NONELECTRIC", "STANDARD ELECTRIC", "RV NONELECTRIC",
                   "RV ELECTRIC", "TENT ONLY NONELECTRIC", "MANAGEMENT",
                   "CABIN NONELECTRIC", "CABIN ELECTRIC", "WALK TO", "BOAT IN"]
attrs_to_check = ["Driveway Entry", "Driveway Surface", "Max Vehicle Length",
                   "Water Hookup", "Sewer Hookup", "Electricity Hookup",
                   "Pets Allowed", "Campfire Allowed", "Site Access"]

hdr_type = "Type"
header = f"{hdr_type:30s}"
for a in attrs_to_check:
    short = a[:8]
    header += f" {short:>8s}"
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
equip_to_check = ["RV", "Trailer", "FIFTH WHEEL", "Tent", "SMALL TENT",
                   "PICKUP CAMPER", "CARAVAN/CAMPER VAN", "Boat"]

header = f"{hdr_type:30s}"
for e in equip_to_check:
    short = e[:8]
    header += f" {short:>8s}"
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

conn.close()

nl = chr(10)
with open("analysis_part4.txt", "w") as f:
    f.write(nl.join(out))
print(nl + "=== Part 4 complete, written to analysis_part4.txt ===")
