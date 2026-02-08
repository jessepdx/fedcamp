# Changelog

All notable changes to the RV Camping Finder project.

## [0.8.1] — 2026-02-08

### Fixed
- 819 campgrounds (NPS, FS, BLM, USACE) missing from search results — facilities with `facility_type = 'Campground'` but zero campsite records in RIDB were misclassified as NON_CAMPING
- Campable facility count: 5,521 → 6,356

## [0.8.0] — 2026-02-08

### Added
- AWS Lightsail deployment (Ubuntu 24.04, nano instance, us-west-2)
- Live at https://fedcamp.cloudromeo.com
- `deploy.sh` — one-command SCP deploy script (`--db` flag to include database)
- `requirements.txt` — Flask + gunicorn
- Caddy reverse proxy with automatic HTTPS (Let's Encrypt)
- gunicorn WSGI server (2 workers) managed by systemd

## [0.7.3] — 2026-02-07

### Changed
- Purged 13 raw/intermediate tables from ridb.db (361MB → 72MB, 80% reduction)
- Archived full database as ridb_full.db for pipeline re-runs
- App database now contains only the 12 tables needed at runtime

### Removed
- Raw RIDB tables: campsite_attributes (2.4M rows), campsite_equipment (432K rows)
- Intermediate pipeline tables: n_campsite, n_campsite_equipment, n_facility
- Unused tables: links, rec_areas, rec_area_addresses, rec_area_activities, activities, permit_entrances, tours, events

## [0.7.2] — 2026-02-07

### Changed
- Moved data collection scripts (`pull_ridb_data.py`, `pull_campsites_bulk.py`, `pull_extras.py`, `pull_remaining.py`) to `scripts/`
- Moved reference docs (`PLAN.md`, `TODO.md`, `DB_ANALYSIS.md`, `etl_update_plan.md`) to `docs/`

### Removed
- Deleted scratch/analysis files (`analyze.py`, `deep_analysis.py`, `analysis_part*`, `_p3*.py`)
- Deleted one-off API exploration scripts (`fetch_ridb.py`, `explore_api.py`, `test_auth.py`, `test_auth2.py`)
- Deleted log files (`pull_log.txt`, `pull_extras_log.txt`, `pull_remaining_log.txt`)

## [0.7.1] — 2026-02-07

### Added
- `/api/pins?state=XX` JSON endpoint for campground map pins
- Auto-detect user's state on load via geolocation + point-in-polygon
- Campground pins preloaded on the map for the user's state automatically
- Hover over pins shows tooltip (name, site count, agency)
- Click a pin opens facility detail in a new tab (preserves map position)
- Click a state boundary to load that state's campgrounds

### Changed
- Map view is now the default home page (`/`)
- Clean map — removed state choropleth coloring, legend, and hover info panel
- Search form moved to `/search-form` with "Advanced Search" heading
- Nav updated: Map (home) | Search | About
- `/map` redirects to `/` for backwards compatibility

### Removed
- State color gradient (choropleth) and campground count legend
- "Hover over a state" info control

## [0.7.0] — 2026-02-07

### Added
- Geolocation "Search Nearby" — browser-based location detection replaces manual lat/lon entry
- "Use My Location" button with status feedback (locating, success, error)
- Form validation prevents submit without location set (nearby mode) or state selected
- Condition indicators: road access, seasonal status, campfire status, elevation, boondock accessibility
- Condition-based filters on search form and results filter drawer (Road Access, Season, Campfires)
- 8 new description signals parsed in normalize.py (seasonal closure, winter closure, snow, fire restrictions, elevation, remote/no-cell, flood risk)
- Campfire aggregation from campsite data (campfire_yes_sites, campfire_no_sites)
- `n_facility_conditions` table with classified road access, season, fire, elevation, boondock, max RV length

### Changed
- Results map markers colored by camping type (Developed/Primitive/Dispersed) instead of score
- State search sorted by total campsites (descending) instead of score
- About page rewritten to describe condition indicators instead of scoring methodology

### Removed
- Rig size tier scoring system (Tent/Small/Medium/Large 0-100 scores)
- `n_facility_score` table and all score-related columns
- Rig size selector dropdown and minimum score slider
- Score badges (single, triple, and quad) from result cards
- Score panel and breakdown table from facility detail page
- `score_color` and `confidence_color` template filters
- Manual lat/lon input fields (replaced by geolocation)

## [0.6.2] — 2026-02-07

### Fixed
- Clicking facility photos now opens a fullscreen lightbox instead of downloading
- Lightbox shows photo with caption, closes on click or Escape key

## [0.6.1] — 2026-02-07

### Added
- Slide-out filter drawer on results page (pops out from left)
- Filters: rig size, min score, camping type, agency, amenities — all pre-populated with current selections
- "Filters" button in results header toggles the drawer
- Dark overlay backdrop when drawer is open

## [0.6.0] — 2026-02-07

### Added
- Interactive US state map page (`/map`) with Leaflet choropleth
- States colored by campground count (green gradient)
- Click any state to search its campgrounds
- Hover tooltip shows state name and campground count
- Color legend and info panel
- "Map" link added to navigation bar

## [0.5.2] — 2026-02-07

### Added
- Agency filter (FS, BLM, USACE, NPS, BOR, FWS) on search form — leave unchecked for all
- Agency filtering works with both state and location searches

## [0.5.1] — 2026-02-07

### Fixed
- Result card stat pills and nearby items use light background for readability (replaced dark Pico CSS variable)

## [0.5.0] — 2026-02-07

### Added
- Tent camping tier with dedicated scoring (comp_tent_sites, comp_tent_amenities, comp_tent_access)
- Tent scores for all DEVELOPED, PRIMITIVE, and DISPERSED facilities
- Tent campers scored on: site availability, amenities (water, toilets), and access (walk-in/hike-in are positives)
- T/S/M/L quad score badges when no rig is selected

### Changed
- Score schema expanded: score_tent, score_label_tent, penalty_tent, plus 3 tent component columns
- Rig selector dropdown includes "Tent" option
- Dispersed facilities now get tent scores (RV scores remain NULL)

## [0.4.3] — 2026-02-07

### Changed
- Rig size is now optional — defaults to "Any / All Sizes"
- Search results show S/M/L triple score badges when no rig is selected
- Selecting a rig filters and sorts by that tier's score

## [0.4.2] — 2026-02-07

### Fixed
- All tags (search results, activities, features) now use lighter backgrounds for better readability

## [0.4.1] — 2026-02-07

### Added
- "View on Recreation.gov" link on facility detail page (links to real campground page)
- Recreation.gov link on each search result card

## [0.4.0] — 2026-02-07

### Added
- Flask web application (`app.py`, `db.py`, `prepare_db.py`)
- Search by state or lat/lon proximity with configurable radius (25–200 mi)
- Three rig size tiers: Small, Medium, Large — each shows its own score
- Amenity tag filters: Full Hookups, Electric, Pull-Through, Big Rig Friendly, etc.
- Minimum score slider and camping type toggles
- Results page with score badges, stats, photos, and top tags per facility
- Map view with color-coded Leaflet markers (score-based colors)
- Facility detail page: component score breakdown, tag groups, stats, map, photo gallery, nearby campgrounds, activities, reservation links
- htmx "Load More" pagination on results
- About page explaining scoring methodology
- State code normalization (full names like "ARIZONA" → "AZ", junk values nulled)
- `n_facility_photo` table mapping facilities to their best campsite photo
- `n_state_cache` table for fast state dropdown loading
- App-specific indexes on facility_addresses, campsites, media, facility_activities

### Technical
- Haversine distance via custom SQLite math functions (radians, cos, sin, acos)
- Bounding box pre-filter keeps geo queries fast on 15K rows
- Pico CSS + Leaflet.js + htmx loaded from CDN — no build step
- Server-rendered Jinja2 templates, no JavaScript framework

## [0.3.0] — 2026-02-07

### Added
- `classify.py` — RV suitability scoring and feature tags
- `n_facility_score` table: per-rig-tier scores (0–100) for Small/Medium/Large
- Five component scores: Length Fit, Hookup Quality, Driveway, RV Welcome, Inventory
- Tier-specific weights (large rigs prioritize length + hookups, small rigs prioritize welcome + inventory)
- Multiplicative penalty system (RV not recommended, hike/boat-in, 4WD, primitive)
- Data confidence metric (0–100) based on 8 data completeness signals
- Boondock accessibility rating (Easy/Moderate/Rough) for dispersed sites
- `n_facility_tags` table: 22 feature tags across 5 categories (WARNING, RIG_SIZE, HOOKUP, ACCESS, STYLE)
- Score labels: EXCELLENT, GOOD, FAIR, POOR, MARGINAL, NOT_SUITABLE

## [0.2.0] — 2026-02-07

### Added
- `rollup.py` — facility-level aggregation from campsite data
- `n_facility_rollup` table: 71 columns covering site counts, hookup stats, max RV length, surface types, driveway breakdown, access modes, description signals, activity signals
- Camping type inference via 16-step priority decision tree (DEVELOPED/PRIMITIVE/DISPERSED/DAY_USE/NON_CAMPING)
- Description enrichment: overrides boolean hookup/pullthrough flags from facility description text
- Three-source max RV length resolution (equipment, attributes, description parsing)
- Handles 388 orphaned facilities (campsites referencing missing facility_ids)

## [0.1.0] — 2026-02-07

### Added
- `normalize.py` — EAV pivot to flat campsite table
- `n_campsite` table: 132,974 rows with typed, cleaned attributes (driveway, hookups, amps, vehicle length, site access, shade, pets, campfire)
- `n_campsite_equipment` table: 392,604 rows with normalized equipment names (15 raw → 11 categories)
- `n_facility` table: 15,061 rows with description-parsed signals (20 regex patterns, RV length extraction)
- `n_meta` table for pipeline metadata tracking
- 17 parser helper functions for dirty data cleanup

## [0.0.0] — 2026-02-07

### Added
- Initial project: RIDB API data pipeline and analysis scripts
- `fetch_ridb.py`, `pull_ridb_data.py`, `pull_campsites_bulk.py`, `pull_extras.py`, `pull_remaining.py` — data collection from recreation.gov API
- `analyze.py`, `deep_analysis.py`, analysis_part*.py — exploratory data analysis
- `PLAN.md` — project roadmap
- `DB_ANALYSIS.md` — comprehensive database analysis report
- SQLite database with 132K campsites, 2.4M attributes, 432K equipment records, 15K facilities across 33 federal agencies
