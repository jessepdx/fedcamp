# ETL Incremental Update Plan

> **Status**: Implemented as `sync.py` (root). First successful run: 2026-05-04.

## Overview

The RIDB API supports a `lastupdated` query parameter on `/facilities` that returns records modified since a given date. This enables incremental syncs instead of full re-pulls (which take hours due to the 50 req/min rate limit).

> **API quirk**: the date format is **`YYYY-MM-DD`**, not `MM-DD-YYYY`. A wrong format is silently ignored — the endpoint returns *all* records as if no filter were given. The original plan documented the wrong format; this was caught in the 2026-05-04 run when the filter returned 15,245 facilities for a one-month window.
>
> **API quirk #2**: `/campsites?lastupdated=…` ignores the filter entirely and returns the full ~134K-row set regardless. The original plan's "Step 5: Check for Changed Campsites Independently" was therefore dropped — campsite changes are caught only via their parent facility.

## Current Data Profile (as of 2026-05-04)

| Table | Rows | Has `last_updated` |
|-------|------|--------------------|
| facilities | 15,220 | Yes |
| campsites | 133,814 | Yes |
| campsite_attributes | 2,436,021 | No (child of campsites) |
| campsite_equipment | 436,075 | No (child of campsites) |
| rec_areas | 3,671 | Yes |
| media | 35,105 | No |
| facility_activities | 48,795 | No |
| permit_entrances | 857 | Yes |

## Typical Monthly Change Volume

- **Facilities**: 50–200/month, occasionally 500–800/month, with rare bulk-stamp events (~15K) where RIDB re-touches `LastUpdatedDate` on every record without changing data
- **API calls per sync**: ~200–2,000 (vs ~5,000+ for full pull)
- **Time estimate**: 5–60 min depending on changed-facility count
- **Bulk-stamp months**: a sync starting from before the bulk-stamp date will fan-out to *every* facility (~12 hours). Use `--since <date-after-stamp>` to skip.

## Implementation: `sync.py`

CLI:
```bash
python sync.py                           # incremental from last_sync_date
python sync.py --since 2026-04-01        # override start date
python sync.py --skip-pull               # only run pipeline + cleaning
python sync.py --skip-pipeline           # only run API pull
python sync.py --skip-coords             # skip backfill_coords
python sync.py --skip-seasonal           # skip scrape_seasonal
```

### Step 1: Read last sync timestamp

```python
SELECT value FROM n_meta WHERE key = 'last_sync_date'
# Falls back to MAX(last_updated) FROM facilities, then 30 days ago.
```

### Step 2: Fetch changed facilities

```
GET /api/v1/facilities?lastupdated=YYYY-MM-DD&limit=50&offset=0&full=true
```

Paginate through all results. For each facility:

1. `INSERT OR REPLACE INTO facilities (…)`
2. If the response contains `FACILITYADDRESS`: `DELETE FROM facility_addresses WHERE facility_id = ?` then re-insert. (Skip if the field is absent — that's an API omission, not "really has none".)
3. Same pattern for `ACTIVITY` → `facility_activities`.

### Step 3: Re-pull campsites for changed facilities

For each changed facility ID:

```
GET /api/v1/facilities/{id}/campsites?limit=50&offset=0
```

Each campsite response includes nested `ATTRIBUTES` and `PERMITTEDEQUIPMENT` arrays.

**Safety pattern**: fetch the first page *before* deleting. If the fetch errors or returns no `RECDATA`, skip the facility — don't wipe existing good data on a transient failure. Only when the first page comes back valid:

1. `DELETE FROM campsite_attributes WHERE campsite_id IN (SELECT … WHERE facility_id = ?)`
2. `DELETE FROM campsite_equipment   WHERE campsite_id IN (SELECT … WHERE facility_id = ?)`
3. `DELETE FROM campsites             WHERE facility_id = ?`
4. Insert fresh campsite + attribute + equipment rows from this and subsequent pages.

### Step 4: Re-pull facility-level media

For each changed facility:

```
GET /api/v1/facilities/{id}/media?limit=50
```

Replace `media` rows where `entity_id = facility_id AND entity_type = 'Facility'`.

> Note: campsite-level media (`entity_type = 'Campsite'`) is *not* refreshed by sync — it's only obtainable via the global `/media` endpoint or per-campsite calls. `n_facility_photo` is built from campsite media, so its row count won't grow until a full media re-pull. Existing photos are preserved.

### Step 5: Re-run the pipeline

`sync.py` invokes each script as a subprocess. Total ~12s.

```bash
python normalize.py    # ~11s — pivots EAV, parses descriptions
python rollup.py       # ~1s  — aggregates to facility level
python classify.py     # ~1s  — conditions + tags
python prepare_db.py   # ~1s  — indexes, photos, state cache
```

### Step 6: Post-pipeline cleaning / enrichment

Both scripts are resumable via JSON cache and idempotent.

```bash
python scripts/backfill_coords.py   # fills NULL coords from recreation.gov campground API
python scripts/scrape_seasonal.py   # scrapes seasonal status (closures, winter, etc.)
```

These run **after** the pipeline because the pipeline rebuilds `n_facility_rollup` and `n_facility_conditions` from scratch — the cleaning scripts then apply their cached results to the rebuilt tables.

- `backfill_coords.py`: cache at `scripts/coords_cache.json`. ~16 min on first run, seconds on re-runs (only new NULL-coord facilities are scraped).
- `scrape_seasonal.py`: cache at `scripts/seasonal_cache.json`. Targets only `UNKNOWN` campable facilities, so re-runs are fast.

### Step 7: Update sync timestamp

**Order matters**: `normalize.py` does `DELETE FROM n_meta` and rewrites it, so writing `last_sync_date` *before* the pipeline loses it. `sync.py` writes it as the last step, after pipeline + cleaning have completed:

```sql
INSERT OR REPLACE INTO n_meta (key, value, updated_at)
VALUES ('last_sync_date', '2026-05-04', datetime('now'))
```

### Step 8: Log results

Example summary from the 2026-05-04 run:

```
SYNC COMPLETE
  API calls:           1,484
  Changed facilities:  654
  Campsites refreshed: 15,640 across 453 facilities
  Media records:       3,011
  Total time:          40.5 min
```

## Deployment

- Run as a daily cron: `0 3 * * * cd /path/to/fedcamp && source venv/bin/activate && python sync.py`
- Requires `RIDB_API_KEY` (read from environment or `.env`)
- Safe to run multiple times (upserts + full pipeline rebuild)
- If a run fails mid-pull, `last_sync_date` is unchanged — the next run resumes from the same point

### Pushing fresh data to the live host

`sync.py` operates on the full 362MB working DB. Don't deploy that — the Lightsail nano host is sized for the trimmed app DB. After a sync:

```bash
python purge_for_deploy.py   # ridb.db -> ridb_app.db (~73MB, app-reachable tables only)
./deploy.sh --db             # uploads ridb_app.db, swaps it in atomically as ridb.db
```

`purge_for_deploy.py --check` shows the keep/drop list without writing.

## Database notes

- `sync.py` reads/writes `ridb.db`, which must contain the raw RIDB tables (`facilities`, `campsites`, `campsite_attributes`, `campsite_equipment`, `media`, `facility_addresses`, `facility_activities`). The script asserts these are present at startup.
- A trimmed "app-only" copy may have been deployed in the past; the local working DB must keep the raw tables to allow re-runs of the pipeline.

## Edge cases

- **Deleted facilities**: RIDB doesn't surface deletions. They linger as stale rows. Either tolerate this or do a periodic full pull (`scripts/pull_ridb_data.py`).
- **Bulk-stamp events**: RIDB occasionally re-touches `LastUpdatedDate` on every record (~15K facilities). A sync that crosses such a boundary fans out to all facilities (~12 hours). Mitigate by passing `--since <date-after-the-stamp>`.
- **New facilities**: caught by the `lastupdated` filter (their `LastUpdatedDate` is the creation date).
- **`campsite_attributes` has no `last_updated`**: fine — they're refreshed via the nested arrays in `/facilities/{id}/campsites`.
- **Independently-changed campsites**: not detectable. The `/campsites` endpoint ignores `lastupdated`. Such changes are only picked up if the parent facility was also touched.
