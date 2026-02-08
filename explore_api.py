"""
Explore the full RIDB API structure - every endpoint, every field
"""
import requests
import json
import time
import os

API_KEY = os.environ.get("RIDB_API_KEY", "")
BASE = "https://ridb.recreation.gov/api/v1"
HDR = {"apikey": API_KEY, "accept": "application/json"}

def fetch(endpoint):
    r = requests.get(f"{BASE}{endpoint}", headers=HDR)
    if r.status_code == 200:
        return r.json()
    print(f"  ERROR {r.status_code}: {r.text[:200]}")
    return None

def show(label, data, depth=0):
    """Pretty print structure info"""
    prefix = "  " * depth
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                print(f"{prefix}{k}: ({type(v).__name__})")
                show(label, v, depth + 1)
            else:
                val_str = str(v)[:80]
                print(f"{prefix}{k}: {val_str}  [{type(v).__name__}]")
    elif isinstance(data, list):
        if len(data) > 0:
            print(f"{prefix}[{len(data)} items] first item:")
            show(label, data[0], depth + 1)
        else:
            print(f"{prefix}[empty list]")

print("=" * 70)
print("RIDB API DATA STRUCTURE EXPLORATION")
print("=" * 70)

# 1. Facilities with full detail
print("\n### FACILITIES (full=true) ###")
data = fetch("/facilities?limit=1&full=true&query=campground")
if data:
    print(f"METADATA: {json.dumps(data.get('METADATA', {}), indent=2)}")
    if data.get("RECDATA"):
        print("\nFacility record structure:")
        show("facility", data["RECDATA"][0])

time.sleep(0.5)

# 2. A specific facility with campsites
print("\n\n### FACILITY DETAIL + CAMPSITES ###")
# Find a campground with campsites
data = fetch("/facilities?limit=5&full=true&query=campground&activity=CAMPING")
if data and data.get("RECDATA"):
    for fac in data["RECDATA"]:
        fid = fac["FacilityID"]
        name = fac["FacilityName"]
        # Try to get campsites
        cs = fetch(f"/facilities/{fid}/campsites?limit=2")
        time.sleep(0.3)
        if cs and cs.get("RECDATA") and len(cs["RECDATA"]) > 0:
            print(f"\nFound campsites at: {name} (ID: {fid})")
            print(f"Total campsites: {cs['METADATA']['RESULTS']['TOTAL_COUNT']}")
            print("\nCampsite record structure:")
            show("campsite", cs["RECDATA"][0])

            # Also show the full JSON of first campsite for all fields
            print("\n--- Full first campsite JSON ---")
            print(json.dumps(cs["RECDATA"][0], indent=2, default=str)[:3000])
            break

time.sleep(0.5)

# 3. Recreation Areas
print("\n\n### RECREATION AREAS ###")
data = fetch("/recareas?limit=1&full=true")
if data:
    print(f"Total rec areas: {data['METADATA']['RESULTS']['TOTAL_COUNT']}")
    if data.get("RECDATA"):
        print("\nRec area structure:")
        show("recarea", data["RECDATA"][0])

time.sleep(0.5)

# 4. Organizations
print("\n\n### ORGANIZATIONS ###")
data = fetch("/organizations?limit=50")
if data:
    print(f"Total orgs: {data['METADATA']['RESULTS']['TOTAL_COUNT']}")
    if data.get("RECDATA"):
        print("\nOrg structure:")
        show("org", data["RECDATA"][0])
        print("\n--- All organizations ---")
        for org in data["RECDATA"]:
            print(f"  {org.get('OrgID')}: {org.get('OrgAbbrevName', 'N/A')} - {org.get('OrgName')}")

time.sleep(0.5)

# 5. Activities
print("\n\n### ACTIVITIES ###")
data = fetch("/activities?limit=100")
if data:
    print(f"Total activities: {data['METADATA']['RESULTS']['TOTAL_COUNT']}")
    if data.get("RECDATA"):
        print("\nActivity structure:")
        show("activity", data["RECDATA"][0])
        print("\n--- All activities ---")
        for act in data["RECDATA"]:
            print(f"  {act.get('ActivityID')}: {act.get('ActivityName')}")

time.sleep(0.5)

# 6. Check campsite-specific attributes for a facility with RV sites
print("\n\n### CAMPSITE ATTRIBUTES (looking for RV-related fields) ###")
data = fetch("/facilities?limit=10&query=RV+campground")
if data and data.get("RECDATA"):
    for fac in data["RECDATA"]:
        fid = fac["FacilityID"]
        name = fac["FacilityName"]
        cs = fetch(f"/facilities/{fid}/campsites?limit=5")
        time.sleep(0.3)
        if cs and cs.get("RECDATA") and len(cs["RECDATA"]) > 0:
            print(f"\nRV facility: {name} (ID: {fid})")
            print(f"Total campsites: {cs['METADATA']['RESULTS']['TOTAL_COUNT']}")
            for i, site in enumerate(cs["RECDATA"][:3]):
                print(f"\n  Campsite {i+1}: {site.get('CampsiteName', 'N/A')}")
                print(f"    Type: {site.get('CampsiteType', 'N/A')}")
                print(f"    Accessible: {site.get('CampsiteAccessible', 'N/A')}")
                print(f"    Reservable: {site.get('CampsiteReservable', 'N/A')}")
                # Show ATTRIBUTES and PERMITTEDEQUIPMENT - these are key for RV
                attrs = site.get("ATTRIBUTES", [])
                if attrs:
                    print(f"    ATTRIBUTES ({len(attrs)}):")
                    for a in attrs:
                        print(f"      {a.get('AttributeName', 'N/A')}: {a.get('AttributeValue', 'N/A')}")
                equip = site.get("PERMITTEDEQUIPMENT", [])
                if equip:
                    print(f"    PERMITTEDEQUIPMENT ({len(equip)}):")
                    for e in equip:
                        print(f"      {e.get('EquipmentName', 'N/A')}: max {e.get('MaxLength', 'N/A')}ft")
            break

print("\n\nDone exploring.")
