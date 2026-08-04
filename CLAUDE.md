# CLAUDE.md

## Project: Campdex

Federal campground search tool built on RIDB (recreation.gov) data. Python + SQLite + Flask. Live at campdex.com. (Formerly "RV Camping Finder" / "FedCamp" — the user-facing name is now **Campdex**; the downloadable database is still published as `fedcamp.db`.)

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
2. `rollup.py` — facility-level `n_facility_rollup` (81 cols, 15,573 rows)
3. `classify.py` — `n_facility_score` + `n_facility_tags` (per-rig-tier 0–100 scores)
4. `prepare_db.py` — app indexes, photo mapping, state normalization, state cache

### Web App
- `app.py` — Flask routes: `/` (map), `/search`, `/search-form`, `/facility/<id>`, `/about`, `/stats`, plus JSON API (`/api/pins`, `/api/search`, `/api/facility/<id>`, `/api/states`, `/api/download`)
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
- **NEVER filter `facility_addresses` on `address_type = 'Physical'`.** This was once listed here as the convention and it caused a production bug where state search returned ~2% of results (Oregon: 12 of 604). Two reasons it's wrong:
  1. `Physical` is the **rarest** address type in the data — 1,812 rows vs 12,796 `Default` and 1,820 `Mailing` (Oregon: 46 facilities with a `Physical` row vs 867 with `Default`) — so the filter drops ~85% of facilities.
  2. A `WHERE fa.state_code IN (...)` predicate on a LEFT-JOINed table silently degrades the LEFT JOIN to an INNER JOIN (NULLs from unmatched rows never satisfy the predicate), so facilities without a `Physical` row vanish entirely instead of surviving with NULL city/state.

  Instead, join addresses through the shared `PREFERRED_ADDRESS_JOIN` fragment in `db.py`: a correlated subquery that selects exactly one address row per facility, ranked by (has non-empty `state_code`) → `Physical` → `Default` → `Mailing` → other, tie-broken on `facility_address_id` so the choice is deterministic. This dedupes without dropping anyone.
- Haversine requires registering math functions via `conn.create_function()`
- SQLite HAVING requires GROUP BY; use WHERE with repeated expression instead
- State codes normalized to 2-letter codes in `prepare_db.py`
- 388 orphan facilities exist (campsites referencing missing facility_ids)
- Only dependency beyond stdlib is Flask

## Known Issues

- **State dropdown counts read slightly high.** `n_state_cache` (built in `prepare_db.py`, powers `/api/states`) counts a facility in *every* state it has an address row for, while search assigns each facility exactly one preferred address — so cross-state facilities inflate the dropdown: CA advertises 857 but 820 are reachable via search, WA 262 vs 249. The proper fix belongs in `prepare_db.py` and requires regenerating the production database; deliberately deferred.
- **Bare searches undercount vs the dropdown.** `db.py` defaults `camping_type` to `["DEVELOPED"]`, so `/api/search?state=OR` with no `camping_type` params returns 237 while the dropdown advertises 604 (all three camping types).
- **Recommended long-term fix for both:** precompute `city`/`state_code` into `n_facility_rollup` in `prepare_db.py` (using the preferred-address ranking) and derive `n_state_cache` from that single per-facility value.

## Rules

- **Always update CHANGELOG.md** when making any code changes, before committing. Follow the existing format (semver, grouped by Added/Changed/Fixed/Removed).
- **Commit between changes.** After completing each distinct feature or fix, commit before starting the next one. This keeps changes reversible and avoids large uncommitted diffs.
- Keep `ridb.db` and `*.db-journal` out of git (in .gitignore).
