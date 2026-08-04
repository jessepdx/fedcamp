# ACTIVE Network / ReserveAmerica API — State Park Data

## Overview

The [ACTIVE Network Campground API](https://developer.active.com/docs/read/Campground_APIs) provides
access to campground data from ReserveAmerica, covering ~97% of US and Canadian state/provincial parks.
This would add thousands of **state park** campgrounds to Campdex, which currently only has federal land
(RIDB data).

## Endpoints

All endpoints return **XML** and require an `api_key` parameter.

### 1. Campground Search
```
GET http://api.amp.active.com/camping/campgrounds?pstate={state}&api_key={key}
```

| Param | Description |
|-------|-------------|
| `pstate` | 2-letter state code |
| `pname` | Park name substring |
| `siteType` | 2001=RV, 2003=Tent, 2002=Trailer, 10001=Cabin, 3001=Horse, 2004=Boat, 9002=Group, 9001=Day Use |
| `amenity` | 4001=Biking, 4002=Boating, 4003=Equipment Rental, 4004=Fishing, 4005=Golf, 4006=Hiking, 4007=Horseback Riding, 4008=Hunting, 4009=Rec Activities, 4010=Scenic Trails, 4011=Sports, 4012=Beach/Water, 4013=Winter |
| `eqplen` | Min RV length (feet) |
| `Maxpeople` | Max occupancy |
| `hookup` | 3002=15A, 3003=20A, 3004=30A, 3005=50A |
| `water` | 3006 or 3007 |
| `sewer` | 3007 |
| `pull` | 3008 (pull-through) |
| `pets` | 3010 |
| `waterfront` | 3011 |
| `landmarkLat`, `landmarkLong` | Geo search (200mi radius) |
| `landmarkName` | Required=true with lat/lon |

**Response fields:** `facilityID`, `facilityName`, `contractID`, `contractType` (PRIVATE/FEDERAL),
`state`, `latitude`, `longitude`, `faciltyPhoto`, `sitesWithAmps`, `sitesWithPetsAllowed`,
`sitesWithSewerHookup`, `sitesWithWaterHookup`, `sitesWithWaterfront`

### 2. Campground Details
```
GET http://api.amp.active.com/camping/campground/details?contractCode={state}&parkId={id}&api_key={key}
```

Returns: name, address, coordinates, description, directions, alerts, phone numbers, photos (180x120),
amenities with distances, reservation URL.

### 3. Campsite Search
```
GET http://api.amp.active.com/camping/campsites?contractCode={state}&parkId={id}&api_key={key}
```

Same filters as campground search. Returns per-site: `SiteId`, `Site` (name), `SiteType`,
`Maxeqplen`, `Maxpeople`, `Loop`, hookup/pet/waterfront flags.

## Rate Limits

- **2 calls/second**
- **5,000 calls/day**
- Per API key, not per IP

## Western States on ReserveAmerica

These western states use ReserveAmerica and would be accessible via the API:

| State | ReserveAmerica URL |
|-------|-------------------|
| AK | alaskastateparks.reserveamerica.com |
| CA | reservecalifornia.com |
| CO | coloradostateparks.reserveamerica.com |
| MT | montanastateparks.reserveamerica.com |
| NV | reservenevada.com |
| NH | newhampshirestateparks.reserveamerica.com |
| NM | newmexicostateparks.reserveamerica.com |
| NE | nebraskastateparks.reserveamerica.com |
| OK | okstateparks.reserveamerica.com |
| UT | utahstateparks.reserveamerica.com |

### States with other/custom systems (not in API)

| State | System |
|-------|--------|
| AZ | State-specific |
| ID | getoutside.idaho.gov |
| OR | stateparks.oregon.gov |
| WA | washington.goingtocamp.com |
| WY | reserve.wyoming.gov |
| HI | explore.ehawaii.gov |

## Data Mapping to Campdex

| ACTIVE Field | Campdex Column |
|-------------|----------------|
| `facilityID` + `contractID` | `facility_id` (need composite key or new ID scheme) |
| `facilityName` | `facility_name` |
| `state` | state_code |
| `latitude`, `longitude` | `latitude`, `longitude` |
| `contractType` | Can filter: FEDERAL (skip, already have), STATE, PRIVATE |
| `sitesWithAmps` | `has_electric_hookup` |
| `sitesWithWaterHookup` | `has_water_hookup` |
| `sitesWithSewerHookup` | `has_sewer_hookup` |
| `siteType=2001` count | `sites_accepting_rv` |
| `siteType=2003` count | `sites_accepting_tent` |
| `Maxeqplen` | `max_rv_length` |

## Implementation Plan

### Phase 1: Data Pull
1. Register for API key at developer.active.com
2. Write `scripts/pull_active_data.py`:
   - Loop through all 50 states with `pstate=XX`
   - Parse XML responses
   - Store in `active_campgrounds` table
   - Skip `contractType=FEDERAL` (already in RIDB)
3. For each campground, call details endpoint for descriptions/amenities
4. Respect rate limits: 2/sec, 5K/day → ~40 states per day at search level

### Phase 2: Normalize
5. Map ACTIVE fields to `n_facility_rollup` schema
6. Generate composite facility IDs (e.g., prefix `A-` to avoid RIDB collisions)
7. Add `data_source` column to `n_facility_rollup` (values: `ridb`, `active`)

### Phase 3: Integrate
8. Update `db.py` queries — no changes needed if data lands in same tables
9. Update stats/counts on homepage
10. Add "State Park" to camping_type or org_abbrev

## Risks & Notes

- **API may be unmaintained** — user comments suggest intermittent issues since ~2020
- **HTTP only** — HTTPS causes content decoding errors per docs
- **XML only** — no JSON support
- **Photo URLs** — may return 404s; prepend `http://www.reserveamerica.com` to `faciltyPhoto`
- **5K/day limit** — full data pull across all states + details will take multiple days
- **Deduplication** — some federal campgrounds appear in both RIDB and ReserveAmerica
- Test with one state first (e.g., UT or CO) before full pull
