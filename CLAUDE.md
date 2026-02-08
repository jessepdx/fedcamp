# CLAUDE.md

## Project: RV Camping Finder

Federal campground search tool built on RIDB (recreation.gov) data. Python + SQLite + Flask.

## Architecture

```
Data Pipeline:  normalize.py → rollup.py → classify.py → prepare_db.py
Web App:        app.py (Flask) + db.py (queries) + templates/ + static/
Data Collection: scripts/ (pull_ridb_data.py, pull_campsites_bulk.py, etc.)
Reference Docs: docs/ (PLAN.md, TODO.md, DB_ANALYSIS.md, etl_update_plan.md)
Database:       ridb.db (SQLite, 370MB, gitignored)
```

### Pipeline (run in order)
1. `normalize.py` — EAV pivot → flat `n_campsite`, `n_campsite_equipment`, `n_facility`
2. `rollup.py` — facility-level `n_facility_rollup` (71 cols, 15,449 rows)
3. `classify.py` — `n_facility_score` + `n_facility_tags` (per-rig-tier 0–100 scores)
4. `prepare_db.py` — app indexes, photo mapping, state normalization, state cache

### Web App
- `app.py` — Flask routes: `/`, `/search`, `/facility/<id>`, `/about`
- `db.py` — all SQL queries, no Flask dependency
- `templates/` — Jinja2 (Pico CSS + Leaflet + htmx from CDN)
- `static/` — style.css + app.js

## Commands

```bash
source venv/bin/activate
python app.py              # Start dev server on :5000
python normalize.py        # Re-run Phase 1
python rollup.py           # Re-run Phase 2
python classify.py         # Re-run Phase 3
python prepare_db.py       # Re-run Phase 4 prep
```

## Key Conventions

- All normalized tables use `n_` prefix
- Scripts are idempotent (DROP/DELETE + re-INSERT)
- `facility_addresses` filter on `address_type = 'Physical'` to avoid duplicates
- Haversine requires registering math functions via `conn.create_function()`
- SQLite HAVING requires GROUP BY; use WHERE with repeated expression instead
- State codes normalized to 2-letter codes in `prepare_db.py`
- 388 orphan facilities exist (campsites referencing missing facility_ids)
- Only dependency beyond stdlib is Flask

## Rules

- **Always update CHANGELOG.md** when making any code changes, before committing. Follow the existing format (semver, grouped by Added/Changed/Fixed/Removed).
- **Commit between changes.** After completing each distinct feature or fix, commit before starting the next one. This keeps changes reversible and avoids large uncommitted diffs.
- Keep `ridb.db` and `*.db-journal` out of git (in .gitignore).
