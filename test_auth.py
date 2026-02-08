"""Test different auth methods for RIDB API"""
import requests
import os

API_KEY = os.environ.get("RIDB_API_KEY", "")
BASE_URL = "https://ridb.recreation.gov/api/v1"
URL = f"{BASE_URL}/organizations?limit=1"

# Method 1: apikey header
print("1. Header: apikey")
r = requests.get(URL, headers={"apikey": API_KEY})
print(f"   {r.status_code}: {r.text[:200]}\n")

# Method 2: x-api-key header
print("2. Header: x-api-key")
r = requests.get(URL, headers={"x-api-key": API_KEY})
print(f"   {r.status_code}: {r.text[:200]}\n")

# Method 3: Authorization Bearer
print("3. Header: Authorization Bearer")
r = requests.get(URL, headers={"Authorization": f"Bearer {API_KEY}"})
print(f"   {r.status_code}: {r.text[:200]}\n")

# Method 4: Query param apikey
print("4. Query param: apikey")
r = requests.get(f"{URL}&apikey={API_KEY}")
print(f"   {r.status_code}: {r.text[:200]}\n")

# Method 5: Query param api_key
print("5. Query param: api_key")
r = requests.get(f"{URL}&api_key={API_KEY}")
print(f"   {r.status_code}: {r.text[:200]}\n")

# Method 6: Combined header + query
print("6. Combined: apikey header + query param")
r = requests.get(f"{URL}&apikey={API_KEY}", headers={"apikey": API_KEY})
print(f"   {r.status_code}: {r.text[:200]}\n")

# Method 7: Accept header included
print("7. Header: apikey + Accept json")
r = requests.get(URL, headers={"apikey": API_KEY, "Accept": "application/json"})
print(f"   {r.status_code}: {r.text[:200]}\n")

# Method 8: Try the full URL with different base
print("8. Different base URL pattern")
r = requests.get(f"https://ridb.recreation.gov/api/v1/organizations?limit=1&apikey={API_KEY}")
print(f"   {r.status_code}: {r.text[:200]}\n")
