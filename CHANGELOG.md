# Changelog

All notable changes to the RV Camping Finder project.

## [0.9.3] — 2026-02-13

### Fixed
- Map pins on mobile: tapping a pin no longer zooms out to state level (click events no longer bubble through pins to the state boundary layer)

### Added
- `scripts/backfill_coords.py` — fetches missing coordinates from recreation.gov campground API (recovered 545 of 970 facilities, coverage 86% → 94%)
- Coordinate backfill step documented in ETL pipeline (`docs/etl_update_plan.md`)

## [0.9.2] — 2026-02-13

### Added
- Public `/stats` page showing site usage metrics parsed from Caddy access logs
- Summary cards: unique visitors, page views, API requests, days of data
- Daily activity sparkline (CSS-only bar chart)
- Top campgrounds, states, referrers, and pages with horizontal bar charts
- `stats.py` module — standalone log parser with 5-minute cache (no Flask dependency)
- Bot filtering (50+ crawler patterns), Facebook/Reddit referrer normalization
- Graceful "no data" fallback for local development
- Nav link to Stats page
- `CADDY_LOG_DIR` env var override for testing

## [0.9.1] — 2026-02-13

### Added
- Multi-state search: select multiple states on the advanced search form (hold Ctrl/Cmd)
- API supports multiple `state` params: `/api/search?state=OR&state=WA`
- Filter drawer and pagination preserve multi-state selections

## [0.9.0] — 2026-02-13

### Added
- Public JSON API: `/api/search`, `/api/facility/<id>`, `/api/states`
- Search API supports all existing filters (state, lat/lon, camping type, agency, road access, seasonal status, fire status, RV length, amenity tags)
- Pagination via `limit` (max 100) and `offset` params
- Enables integration with AI chatbots (ChatGPT, Claude) and custom tools
- API rate limiting: 60 requests/minute per IP (returns 429 with Retry-After header)
- API documentation section on About page with endpoint reference, parameter list, examples, and chatbot integration instructions
- `/api/download` endpoint — download the full SQLite database file
- Database guide (`fedcamp-db-guide.md`) — table descriptions, column reference, and example queries

## [0.8.8] — 2026-02-13

### Fixed
- Campsite photos broken on live site — CSP img-src allowed `ridb-img.s3.us-west-2.amazonaws.com` but 99.6% of images come from `cdn.recreation.gov`
- Fee section showing raw HTML tags — strip HTML from `facility_use_fee`, hide empty-but-truthy values like `<ul><li></li></ul>`
- Empty HTML in `facility_description` and `facility_directions` showing blank sections (41 + 10 affected facilities)

### Added
- RV length filter on search form and results filter drawer — enter rig length in feet to exclude campgrounds confirmed too short (sites with unknown max length still appear)
- GitHub repo link in site footer
- Feedback form on About page (submits to Google Sheets)

## [0.8.7] — 2026-02-10

### Fixed
- Filter drawer overflows viewport on phones under 340px wide (now caps at 100vw)
- Nearby campgrounds grid causes horizontal scroll on narrow screens
- Map pins on mobile: tapping now shows a popup with name/details and a link, instead of immediately navigating away

### Changed
- Map heights moved from inline styles to CSS classes (enables media query overrides)
- Map page min-height reduced from 400px to 300px

### Added
- Pin color legend on map page (Developed, Primitive, Dispersed, Seasonal, Closed)
- 768px breakpoint: shorter maps, tighter grids, wrapped header links, smaller nav text
- 480px breakpoint: stacked layouts for header links, search toggle, geo-locate row; single-column tag/nearby grids; reduced map heights and container padding

## [0.8.6] — 2026-02-09

### Added
- Date-aware seasonal status: facility banners and result pills now show "Likely Open" or "Likely Closed" based on current month (PST)
- `likely_open` Jinja2 template filter using PST timezone (winter = Nov–Apr)
- `now_pst` and `current_month` injected into all templates via context processor

### Changed
- Seasonal/winter closure banners on facility detail pages show current month and estimated open/closed status
- Result card pills turn red with "Likely Closed" suffix during winter months for seasonal/winter closure campgrounds

## [0.8.5] — 2026-02-08

### Added
- `scripts/scrape_seasonal.py` — scrapes recreation.gov API for campground notices and availability data to reclassify UNKNOWN seasonal statuses
- Resumable scraping with JSON cache (`scripts/seasonal_cache.json`)
- `--dry-run` and `--apply-only` modes for flexible usage
- Notice-based classification: permanently closed, temporarily closed, winter closure, seasonal closure, open year-round
- Availability API fallback: detects closed campgrounds from 100% "Not Available" sites

## [0.8.4] — 2026-02-08

### Added
- Seasonal/closure warning banners on facility detail pages (Seasonal, Winter Closure, Temporarily Closed, Permanently Closed)
- Two new seasonal statuses: `TEMPORARILY_CLOSED` and `PERMANENTLY_CLOSED`
- Map pins turn orange for seasonal/winter closures, red for temporarily/permanently closed
- Seasonal status shown in map pin tooltips

### Changed
- More aggressive seasonal classification from facility descriptions — reclassified 606 facilities from UNKNOWN (patterns: "open year-round", "open from [month]", "closed for the season", "permanently closed", "closed due to", winter/snow closures)
- `classify.py` now reads raw facility descriptions for enhanced seasonal parsing (not just rollup boolean flags)

## [0.8.3] — 2026-02-08

### Added
- Google Maps / Apple Maps button on facility detail pages (auto-detects platform)

### Changed
- Renamed "Search" nav link to "Advanced Search"

## [0.8.2] — 2026-02-08

### Fixed
- Disabled Flask debug mode in production (was exposing Werkzeug interactive debugger)
- Added security headers: CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- Added SRI integrity hashes to all CDN resources (Pico CSS, Leaflet, htmx)
- Removed `| safe` from `street1` and `facility_use_fee` fields (not HTML)
- CSP allows Facebook in-app browser scripts (links shared on Facebook failed to load)
- Fixed wrong SRI hashes for Leaflet JS and htmx (curl wasn't following unpkg redirects)
- Map page shows fallback link to search form if JS fails to load

## [0.8.1] — 2026-02-08

### Added
- "Limited data" notice on NPS facility detail pages that lack campsite records, with link to Recreation.gov

### Removed
- `docs/TODO.md` — open items migrated to GitHub Issues (#5, #6)

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
