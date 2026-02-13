# FedCamp

Search and explore campgrounds on federal public lands. Built on the [Recreation Information Database (RIDB)](https://ridb.recreation.gov/), the official federal database covering campgrounds managed by the Forest Service, BLM, National Park Service, Army Corps of Engineers, Bureau of Reclamation, and Fish & Wildlife Service.

## What It Does

FedCamp takes the raw RIDB data (132K campsites across 15K+ facilities), normalizes and enriches it through a multi-phase pipeline, then serves it through a Flask web app with an interactive map.

**Map homepage** — Auto-detects your location and loads campground pins for the current viewport. Pan and zoom to explore freely — pins update automatically. Filter bar below the map narrows results by camping type, agency, road access, hookups, and RV length.

**Condition indicators** — Instead of abstract scores, each campground shows practical info:
- **Road Access** — Paved, Gravel, Dirt, High Clearance, or 4WD Required
- **Seasonal Status** — Open Year-Round, Seasonal Closure, or Winter Closure
- **Campfire Status** — Allowed, Restrictions, or No Campfires
- **Elevation** — Parsed from facility descriptions
- **Max RV Length** — From campsite data, equipment records, or descriptions
- **Boondock Accessibility** — Easy, Moderate, or Rough (dispersed sites)

**Search & filters** — Search by state or proximity. Filter by camping type (Developed, Primitive, Dispersed), road access, season, fire status, managing agency, and amenities (hookups, pull-through, dump station, etc.).

**Facility detail pages** — Conditions grid, feature tags, campground stats, location map, photo gallery with lightbox, description, directions, activities, and nearby campgrounds.

## Architecture

```
Data Pipeline:  normalize.py -> rollup.py -> classify.py -> prepare_db.py
Web App:        app.py (Flask) + db.py (queries) + stats.py + templates/ + static/
Database:       ridb.db (SQLite, ~72MB app-only, not included in repo)
```

### Data Pipeline

Run in order — each phase is idempotent (safe to re-run):

| Phase | Script | What It Does |
|-------|--------|-------------|
| 1 | `normalize.py` | Pivots the raw EAV attribute tables into flat, typed campsite rows. Parses facility descriptions with 27 regex patterns to extract signals (hookups, road type, elevation, seasonal closures, fire restrictions, etc.). |
| 2 | `rollup.py` | Aggregates campsite-level data up to facility level. 81 columns covering site counts, hookup stats, max RV length, surface types, driveway breakdown, access modes, campfire data, and description signals. Infers camping type (Developed/Primitive/Dispersed) via a 16-step decision tree. |
| 3 | `classify.py` | Classifies each facility into condition categories (road access, seasonal status, fire status, boondock accessibility). Generates feature tags across 8 categories. |
| 4 | `prepare_db.py` | Creates app indexes, builds photo mapping table, normalizes state codes, and caches state-level counts. |

### Web App

- **`app.py`** — Flask routes: `/` (map), `/search`, `/search-form`, `/facility/<id>`, `/about`, `/stats`
- **`db.py`** — All SQL queries with haversine distance calculations. No Flask dependency.
- **`stats.py`** — Caddy access log parser for `/stats` page (standalone, no Flask dependency)
- **`templates/`** — Jinja2 templates using Pico CSS, Leaflet.js, and htmx (all from CDN)
- **`static/`** — `style.css` + `app.js`

### JSON API

Public API for integration with chatbots and custom tools:

- **`GET /api/pins?south=&north=&west=&east=`** — Map pins by viewport bounds (with optional filter params)
- **`GET /api/search?state=XX`** — Search by state or lat/lon with full filters
- **`GET /api/facility/<id>`** — Full facility detail
- **`GET /api/states`** — State list with facility counts
- **`GET /api/download`** — Download the SQLite database

Rate limited to 60 requests/minute per IP.

### Data Collection Scripts

The scripts in `scripts/` pull data from the RIDB API. They require an API key set as the `RIDB_API_KEY` environment variable. Get a free key at [ridb.recreation.gov](https://ridb.recreation.gov/).

## Setup

### Prerequisites

- Python 3.9+
- A populated `ridb.db` SQLite database (see Data Collection below)

### Install & Run

```bash
python -m venv venv
source venv/bin/activate
pip install flask

# Run the pipeline (requires ridb.db with raw data)
python normalize.py
python rollup.py
python classify.py
python prepare_db.py

# Start the app
python app.py
# Open http://localhost:5000
```

### Data Collection

To build the database from scratch, get a free RIDB API key from [ridb.recreation.gov](https://ridb.recreation.gov/), then:

```bash
export RIDB_API_KEY="your-key-here"
python scripts/pull_ridb_data.py        # Facilities, rec areas, orgs
python scripts/pull_campsites_bulk.py   # Campsites with attributes & equipment
python scripts/pull_extras.py           # Links, activities, permit entrances
python scripts/pull_remaining.py        # Media, tours, events
```

This takes several hours due to API rate limits (50 req/min).

## Data Coverage

- **15,449** facilities across **50** states and territories
- **132,974** campsites with typed attributes
- **6,356** campable facilities (Developed + Primitive + Dispersed)
- **2,523** facilities with photos
- **~94%** of campable facilities have valid coordinates
- **6 federal agencies**: Forest Service, BLM, NPS, Army Corps, Bureau of Reclamation, Fish & Wildlife

## Deployment

Live at **https://fedcamp.cloudromeo.com**

- AWS Lightsail nano instance (Ubuntu 24.04, us-west-2)
- Caddy (auto HTTPS via Let's Encrypt) → gunicorn (2 workers) → Flask
- Deploy with `./deploy.sh` (code only) or `./deploy.sh --db` (with database)

## Tech Stack

- **Backend**: Python 3.9, Flask, SQLite
- **Frontend**: Pico CSS, Leaflet.js, htmx (all CDN, no build step)
- **No external dependencies** beyond Flask + gunicorn (stdlib only for pipeline scripts)

## License

Data sourced from [RIDB](https://ridb.recreation.gov/) (public domain federal data).
