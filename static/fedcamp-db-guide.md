# FedCamp Database Guide

SQLite database of federal campgrounds in the United States, sourced from the [Recreation Information Database (RIDB)](https://ridb.recreation.gov).

Covers campgrounds managed by USDA Forest Service (FS), Bureau of Land Management (BLM), National Park Service (NPS), US Army Corps of Engineers (USACE), Bureau of Reclamation (BOR), and US Fish & Wildlife Service (FWS).

---

## Quick Start

```sql
sqlite3 fedcamp.db

-- All developed campgrounds in Oregon with full hookups
SELECT r.facility_name, r.total_campsites, r.max_rv_length,
       fa.city, c.road_access, c.seasonal_status
FROM n_facility_rollup r
JOIN n_facility_conditions c ON r.facility_id = c.facility_id
LEFT JOIN facility_addresses fa
    ON r.facility_id = fa.facility_id AND fa.address_type = 'Physical'
JOIN n_facility_tags t ON r.facility_id = t.facility_id AND t.tag = 'FULL_HOOKUPS'
WHERE fa.state_code = 'OR' AND r.camping_type = 'DEVELOPED'
ORDER BY r.total_campsites DESC;
```

---

## Tables

### n_facility_rollup (15,449 rows)

The main table. One row per facility with aggregated campsite stats.

| Column | Description |
|--------|-------------|
| `facility_id` | Primary key, matches RIDB facility ID |
| `facility_name` | Campground name |
| `facility_type` | RIDB type (Campground, Facility, etc.) |
| `org_abbrev` | Managing agency: FS, BLM, NPS, USACE, BOR, FWS |
| `org_name` | Full agency name |
| `latitude`, `longitude` | Facility coordinates |
| `coords_valid` | 1 if coordinates are usable for geo queries |
| `camping_type` | **DEVELOPED**, **PRIMITIVE**, **DISPERSED**, DAY_USE, or NON_CAMPING |
| `camping_type_confidence` | How confident the classification is (HIGH, MEDIUM, LOW) |
| `total_campsites` | Total campsite count |
| `overnight_sites` | Sites for overnight use |
| `rv_type_sites` | Sites typed as RV in RIDB |
| `sites_accepting_rv` | Sites that accept RVs (broader than rv_type) |
| `tent_only_sites` | Tent-only sites |
| `group_sites` | Group camping sites |
| `has_water_hookup` .. `has_full_hookup` | Boolean (0/1) hookup availability |
| `water_hookup_sites` .. `full_hookup_sites` | Count of sites with each hookup type |
| `max_amps` | Highest amperage available (e.g. 30, 50) |
| `has_pullthrough` | Boolean, pull-through sites exist |
| `pullthrough_sites`, `backin_sites` | Site counts by driveway type |
| `paved_sites`, `gravel_sites` | Site counts by surface |
| `surface_predominant` | Most common surface type |
| `max_rv_length` | Max RV/trailer length in feet (best of 3 sources) |
| `reservable` | Whether facility is reservable on recreation.gov |
| `desc_*` | Boolean flags parsed from facility descriptions (hookups, road type, dispersed, primitive, seasonal, fire, elevation, etc.) |
| `campfire_yes_sites`, `campfire_no_sites` | Site counts allowing/disallowing campfires |

### n_facility_conditions (15,449 rows)

Classified conditions for each facility, derived from campsite data and description parsing.

| Column | Description |
|--------|-------------|
| `facility_id` | Foreign key to n_facility_rollup |
| `road_access` | PAVED, GRAVEL, DIRT, HIGH_CLEARANCE, 4WD_REQUIRED, or UNKNOWN |
| `driveway_surface` | Predominant campsite driveway surface |
| `seasonal_status` | OPEN_YEAR_ROUND, SEASONAL_CLOSURE, WINTER_CLOSURE, TEMPORARILY_CLOSED, PERMANENTLY_CLOSED, or UNKNOWN |
| `fire_status` | CAMPFIRES_ALLOWED, RESTRICTIONS, NO_CAMPFIRES, or UNKNOWN |
| `elevation_ft` | Elevation in feet (parsed from descriptions, may be NULL) |
| `boondock_accessibility` | For primitive/dispersed: EASY, MODERATE, ROUGH, or UNKNOWN |
| `max_rv_length` | Max RV length from conditions analysis |

### n_facility_tags (27,958 rows)

Feature tags assigned to facilities. A facility can have many tags.

| Column | Description |
|--------|-------------|
| `facility_id` | Foreign key to n_facility_rollup |
| `tag` | Tag name (see list below) |
| `tag_category` | WARNING, RIG_SIZE, HOOKUP, ACCESS, or STYLE |
| `display_order` | Sort order for display |

**Common tags:** FULL_HOOKUPS, ELECTRIC_HOOKUP, 50_AMP, WATER_HOOKUP, PULL_THROUGH, BIG_RIG_FRIENDLY, PAVED_ACCESS, DUMP_STATION, POTABLE_WATER, RESERVABLE, RV_NOT_RECOMMENDED, WALK_IN_ONLY, HIKE_IN, BOAT_IN, TENT_ONLY, DISPERSED_CAMPING, PRIMITIVE

### n_facility_photo (2,523 rows)

Best campsite photo for each facility (not all facilities have photos).

| Column | Description |
|--------|-------------|
| `facility_id` | Foreign key to n_facility_rollup |
| `photo_url` | Full URL to image on cdn.recreation.gov |
| `photo_title` | Photo caption |
| `photo_source` | Source attribution |

### facilities (15,061 rows)

Raw RIDB facility records with descriptions and contact info.

| Column | Description |
|--------|-------------|
| `facility_id` | Primary key |
| `facility_name` | Official name |
| `facility_description` | HTML description (may be lengthy) |
| `facility_directions` | HTML driving directions |
| `facility_phone`, `facility_email` | Contact info |
| `facility_reservation_url` | Link to recreation.gov booking page |
| `facility_use_fee` | Fee information |
| `stay_limit` | Maximum stay in days |
| `facility_ada_access` | ADA accessibility notes |

### facility_addresses (16,328 rows)

Physical and mailing addresses. **Always filter on `address_type = 'Physical'`** to avoid duplicates.

| Column | Description |
|--------|-------------|
| `facility_id` | Foreign key to facilities |
| `address_type` | **Physical** or Mailing |
| `city`, `state_code`, `postal_code` | Location |
| `street1` | Street address |

### facility_activities (48,795 rows)

Activities available at each facility.

| Column | Description |
|--------|-------------|
| `facility_id` | Foreign key to facilities |
| `activity_name` | e.g. "Camping", "Fishing", "Hiking" |

### campsites (132,974 rows)

Individual campsite records. Linked to facilities.

| Column | Description |
|--------|-------------|
| `campsite_id` | Primary key |
| `facility_id` | Foreign key to facilities |
| `campsite_name` | Site name/number |
| `campsite_type` | STANDARD, GROUP, CABIN, EQUESTRIAN, etc. |
| `type_of_use` | Overnight or Day |
| `loop` | Loop name within campground |

### media (32,500 rows)

Photos linked to campsites (not facilities directly).

| Column | Description |
|--------|-------------|
| `entity_id` | campsite_id (when entity_type = 'Campsite') |
| `entity_type` | Always 'Campsite' in this dataset |
| `media_type` | Image |
| `url` | Full image URL |
| `title`, `description` | Caption and description |

### organizations (33 rows)

Federal agencies that manage facilities.

| Column | Description |
|--------|-------------|
| `org_id` | Primary key |
| `org_name` | Full name |
| `org_abbrev` | Short code: FS, BLM, NPS, USACE, BOR, FWS |

### n_state_cache (50 rows)

Pre-computed campground counts per state.

| Column | Description |
|--------|-------------|
| `state_code` | 2-letter state code |
| `facility_count` | Number of campable facilities |

---

## Common Queries

### Campgrounds near a location (haversine)

SQLite doesn't have trig functions built in. Register them first if using a script, or use the bounding-box approach:

```sql
-- Bounding box: campgrounds within ~50 miles of Portland, OR
SELECT r.facility_name, fa.city, fa.state_code, r.total_campsites
FROM n_facility_rollup r
JOIN facility_addresses fa
    ON r.facility_id = fa.facility_id AND fa.address_type = 'Physical'
WHERE r.camping_type IN ('DEVELOPED', 'PRIMITIVE', 'DISPERSED')
  AND r.latitude BETWEEN 44.78 AND 46.22
  AND r.longitude BETWEEN -123.67 AND -121.53
ORDER BY r.total_campsites DESC;
```

### Big rig friendly campgrounds

```sql
SELECT r.facility_name, r.max_rv_length, r.pullthrough_sites,
       r.full_hookup_sites, fa.state_code
FROM n_facility_rollup r
JOIN n_facility_conditions c ON r.facility_id = c.facility_id
JOIN facility_addresses fa
    ON r.facility_id = fa.facility_id AND fa.address_type = 'Physical'
WHERE r.camping_type = 'DEVELOPED'
  AND r.max_rv_length >= 40
  AND c.road_access = 'PAVED'
ORDER BY r.full_hookup_sites DESC
LIMIT 25;
```

### BLM dispersed camping areas

```sql
SELECT r.facility_name, c.boondock_accessibility, c.road_access,
       fa.city, fa.state_code
FROM n_facility_rollup r
JOIN n_facility_conditions c ON r.facility_id = c.facility_id
LEFT JOIN facility_addresses fa
    ON r.facility_id = fa.facility_id AND fa.address_type = 'Physical'
WHERE r.camping_type = 'DISPERSED'
  AND r.org_abbrev = 'BLM'
ORDER BY fa.state_code, r.facility_name;
```

### Facilities with specific amenities

```sql
-- Campgrounds with both electric hookups and dump stations
SELECT r.facility_name, fa.state_code
FROM n_facility_rollup r
JOIN facility_addresses fa
    ON r.facility_id = fa.facility_id AND fa.address_type = 'Physical'
WHERE r.facility_id IN (
    SELECT facility_id FROM n_facility_tags WHERE tag = 'ELECTRIC_HOOKUP'
)
AND r.facility_id IN (
    SELECT facility_id FROM n_facility_tags WHERE tag = 'DUMP_STATION'
)
ORDER BY fa.state_code, r.facility_name;
```

---

## Notes

- **Campable facilities** (DEVELOPED + PRIMITIVE + DISPERSED): 6,356 of 15,449 total
- About 20% of facilities lack valid coordinates
- 819 NPS/FS/BLM/USACE campgrounds have 0 campsite records in RIDB but are classified as DEVELOPED (low confidence)
- `facility_description` and `facility_directions` contain HTML
- Data sourced from RIDB as of early 2026 — conditions change, always verify before traveling
