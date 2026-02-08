# RV Camping Finder — Project Plan

## What We Have (Feb 7, 2026)

### SQLite Database: `ridb.db` (261 MB)

All data pulled from RIDB API (`https://ridb.recreation.gov/api/v1`).

| Table | Records | Status |
|---|---|---|
| organizations | 33 | COMPLETE |
| rec_areas | 3,671 | COMPLETE |
| rec_area_addresses | 3,878 | COMPLETE |
| facilities | 15,061 | COMPLETE |
| facility_addresses | 16,328 | COMPLETE |
| facility_activities | 48,795 | COMPLETE |
| campsites | 132,974 | COMPLETE |
| campsite_attributes | 2,423,061 | COMPLETE |
| campsite_equipment | 431,992 | COMPLETE |
| links | 64,550 | COMPLETE |
| activities | 154 | COMPLETE |
| permit_entrances | 857 | COMPLETE |

### Not Yet Pulled

| Endpoint | Records | Notes |
|---|---|---|
| media | 288,892 | Image/video URLs + metadata. Not actual images — just catalog of what photos exist on recreation.gov CDN. Useful for app frontend later, not needed for data analysis or classification. ~2hr pull. |
| rec_area_activities | ~15,000 est | Per-rec-area activity lists. ~82 min pull. |
| tours | 599 | Cave tours, guided walks. Not camping-relevant. |
| events | 3 | Basically empty. |

**Decision:** Pull media and rec_area_activities later when building the frontend. Everything needed for data analysis and classification is already in the DB.

---

## What the Data Tells Us

### The Good
- 132,974 campsites with 2.4M attributes and 432K equipment records
- Equipment data (RV, Trailer, Fifth Wheel, max lengths) is relatively clean
- Campsite types clearly distinguish RV vs tent vs group vs management
- 5,172 facilities have campsite data
- 14,267 facilities have text descriptions — many contain RV info, road conditions, dispersed camping signals

### The Dirty
- **Driveway Entry**: 12 spellings for 3 things (Back-in, Pull-through, Parallel)
- **Water Hookup**: "Yes", "Y", "Water Hookup", "No", "", "NO" — 6 ways to say yes/no
- **Sewer Hookup**: 4 variants of yes/no, 122,700 sites don't report at all
- **Electricity Hookup**: Stored as amps (50, 30, 20/30/50, etc.) not yes/no — 60+ distinct values
- **Max Vehicle Length**: "0" appears 10,913 times (zero or unreported?), text values like "One Car", "45'"
- **Site Access**: "Drive-In" vs "Drive In" vs "Hike-In" vs "Hike In"
- **Coordinates**: 2,587 facilities have 0,0 coords, 361 of those actually have campsites

### The Missing
- 87,356 campsites don't report water hookup at all
- 122,700 don't report sewer
- 88,550 don't report electricity
- 29,765 don't report max vehicle length
- ~30,000 don't report driveway entry
- BLM: 1,100 of 1,249 facilities have zero campsites (dispersed land, not a data gap)
- USFS: 6,399 of 9,602 facilities have zero campsites

---

## Understanding Federal Camping (see FEDERAL_CAMPING_DEEP_DIVE.md)

### Two Worlds
1. **Developed campgrounds** — in the database, reservable, numbered sites, attributes. This is what RIDB covers.
2. **Dispersed/boondocking** — NOT in the database by design. BLM and USFS land where you just find a flat spot. The Federal Camping Data Standard explicitly excludes this.

### Agency Character
- **BLM**: 98% dispersed. 1,249 facilities but only 149 have campsites. The rest are trailheads, day-use, or unnamed public land. RV boondocking central.
- **USFS**: Mix of developed campgrounds and dispersed. 9,602 facilities, 3,203 with campsites. Road conditions (gravel, dirt, 4WD) are the #1 RV concern. MVUMs determine road legality.
- **NPS**: Developed campgrounds, reservation-heavy, RV length limits matter. Good data when present.
- **USACE**: Hidden gems. Water-adjacent, well-maintained, often full hookups, cheaper than NPS. 2,108 facilities, 994 with campsites. Under-discovered.
- **BOR**: Small player, similar to USACE. 18 facilities with data, reservoir camping.
- **FWS**: Niche. 162 facilities, only 7 with campsites. Wildlife refuges, not camping destinations.

### What Campers Need That the Data Doesn't Provide
- Road conditions / surface type to reach the campground
- Cell signal
- Real-time availability / current conditions
- Nearby dump stations, water fills, services
- Seasonal closures
- The entire dispersed camping universe

### What We CAN Infer
- Dispersed vs developed: org (BLM/FS) + no reservation URL + no campsites + generic facility type
- Road difficulty: free-text descriptions mention "gravel road" (357), "dirt road" (334), "high clearance" (206), "4wd" (115)
- RV warnings: "not recommended" (204), "no rv" (49), vehicle length limits in prose
- Facilities: "vault toilet" (2,422), "potable water" (581), "dump station" (680), "hookup" (1,264)

---

## TODO: Next Steps

### Phase 1: Data Normalization
- [ ] Normalize driveway entry → BACK_IN, PULL_THROUGH, PARALLEL, UNKNOWN
- [ ] Normalize hookups → boolean has_water, has_sewer, has_electric + electric_amps
- [ ] Parse max vehicle length → clean integer (handle 0, text values, missing)
- [ ] Normalize site access → DRIVE_IN, HIKE_IN, WALK_IN, BOAT_IN, UNKNOWN
- [ ] Normalize equipment names → merge RV/RV_MOTORHOME, standardize casing
- [ ] Parse facility descriptions → extract road conditions, RV warnings, amenity mentions
- [ ] Fix/flag 0,0 coordinates

### Phase 2: Facility-Level Aggregation
- [ ] Compute per-facility: total_campsites, rv_sites, tent_only_sites
- [ ] Compute per-facility: has_hookups, hookup_types, max_amps
- [ ] Compute per-facility: has_pullthrough, pullthrough_count, backin_count
- [ ] Compute per-facility: max_rv_length (from equipment + attributes)
- [ ] Compute per-facility: driveway_surface, paved_sites, gravel_sites
- [ ] Compute per-facility: overnight_sites vs day_use_sites
- [ ] Infer camping_type: developed, primitive, dispersed, day_use

### Phase 3: Classification
- [ ] Design new classification system (not the old 5-tier)
- [ ] Separate developed campground classification from dispersed/boondocking
- [ ] RV suitability scoring that accounts for rig size
- [ ] Validate against known campgrounds (spot-check real facilities)

### Phase 4: App / Frontend
- [ ] Pull media records (288K image URLs) for campground photos
- [ ] Pull rec_area_activities for activity filtering
- [ ] Design API / data service
- [ ] Build frontend (Python-based? or keep React?)
