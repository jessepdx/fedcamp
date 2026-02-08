"""Test more auth patterns for RIDB API"""
import requests
import urllib.request
import json
import os

API_KEY = os.environ.get("RIDB_API_KEY", "")
BASE = "https://ridb.recreation.gov/api/v1"

# Try with exact headers from the docs
print("=== Test with exact doc headers ===")
r = requests.get(f"{BASE}/facilities?limit=1", headers={
    "accept": "application/json",
    "apikey": API_KEY
})
print(f"Status: {r.status_code}")
print(f"Response: {r.text[:300]}\n")

# Try with urllib to rule out requests library issues
print("=== Test with urllib (no requests lib) ===")
req = urllib.request.Request(
    f"{BASE}/organizations?limit=1",
    headers={"apikey": API_KEY, "Accept": "application/json"}
)
try:
    with urllib.request.urlopen(req) as resp:
        data = resp.read().decode()
        print(f"Status: {resp.status}")
        print(f"Response: {data[:300]}")
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print(f"Response: {e.read().decode()[:300]}")

# Check if the key format even looks right
print(f"\n=== Key info ===")
print(f"Key: {API_KEY}")
print(f"Length: {len(API_KEY)}")
print(f"Looks like UUID: {len(API_KEY) == 36 and API_KEY.count('-') == 4}")

# Try the "use our data" page link
print("\n=== Test recreation.gov/use-our-data endpoint ===")
r = requests.get("https://www.recreation.gov/api/search?query=yellowstone&limit=1")
print(f"Status: {r.status_code}")
print(f"Response: {r.text[:300]}")
