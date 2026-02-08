"""
RIDB Data Fetcher - Pull all recreation data and store in SQLite
"""
import requests
import json
import time
import os

API_KEY = os.environ.get("RIDB_API_KEY", "")
BASE_URL = "https://ridb.recreation.gov/api/v1"
HEADERS = {"apikey": API_KEY, "Accept": "application/json"}

def test_api():
    """Test different endpoints to understand the API structure"""

    # Test facilities endpoint
    print("=" * 60)
    print("TESTING RIDB API")
    print("=" * 60)

    endpoints = [
        "/facilities?limit=2",
        "/recareas?limit=2",
        "/organizations?limit=2",
        "/campsites?limit=2",
    ]

    for ep in endpoints:
        url = f"{BASE_URL}{ep}"
        print(f"\n--- GET {ep} ---")
        resp = requests.get(url, headers=HEADERS)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            # Show structure
            if isinstance(data, dict):
                print(f"Top-level keys: {list(data.keys())}")
                for k, v in data.items():
                    if isinstance(v, list) and len(v) > 0:
                        print(f"  '{k}' has {len(v)} items")
                        print(f"  First item keys: {list(v[0].keys())}")
                        print(f"  First item sample:")
                        print(json.dumps(v[0], indent=2, default=str)[:2000])
                    elif isinstance(v, (int, float, str)):
                        print(f"  '{k}': {v}")
            elif isinstance(data, list) and len(data) > 0:
                print(f"Array with {len(data)} items")
                print(f"First item keys: {list(data[0].keys())}")
                print(json.dumps(data[0], indent=2, default=str)[:2000])
        else:
            print(f"Response: {resp.text[:500]}")

        time.sleep(0.3)

    # Also test facility-specific campsites endpoint
    print(f"\n--- Testing facility-specific campsites ---")
    # First get a facility ID
    resp = requests.get(f"{BASE_URL}/facilities?limit=1&query=campground", headers=HEADERS)
    if resp.status_code == 200:
        data = resp.json()
        if "RECDATA" in data and len(data["RECDATA"]) > 0:
            fac_id = data["RECDATA"][0].get("FacilityID")
            print(f"Using FacilityID: {fac_id}")

            # Get campsites for this facility
            cs_resp = requests.get(f"{BASE_URL}/facilities/{fac_id}/campsites?limit=2", headers=HEADERS)
            print(f"Campsites status: {cs_resp.status_code}")
            if cs_resp.status_code == 200:
                cs_data = cs_resp.json()
                if isinstance(cs_data, dict):
                    print(f"Top-level keys: {list(cs_data.keys())}")
                    for k, v in cs_data.items():
                        if isinstance(v, list) and len(v) > 0:
                            print(f"  '{k}' first item keys: {list(v[0].keys())}")
                            print(json.dumps(v[0], indent=2, default=str)[:2000])
                        elif isinstance(v, (int, float, str)):
                            print(f"  '{k}': {v}")

    # Test total counts
    print(f"\n--- Checking total record counts ---")
    for entity in ["facilities", "recareas", "organizations"]:
        resp = requests.get(f"{BASE_URL}/{entity}?limit=1&offset=0", headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            metadata = data.get("METADATA", {})
            total = metadata.get("RESULTS", {}).get("TOTAL_COUNT", "unknown")
            print(f"  {entity}: {total} total records")

if __name__ == "__main__":
    test_api()
