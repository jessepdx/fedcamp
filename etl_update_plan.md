# ETL Incremental Update Plan

## Overview

The RIDB API supports a `lastupdated` query parameter (`MM-DD-YYYY` format) that returns records modified since a given date. This enables incremental syncs instead of full re-pulls (which take hours due to the 50 req/min rate limit).

## Current Data Profile

| Table | Rows | Has `last_updated` |
|-------|------|--------------------|
| facilities | 15,061 | Yes |
| campsites | 132,974 | Yes |
| campsite_attributes | 2,423,061 | No (child of campsites) |
| campsite_equipment | 431,992 | No (child of campsites) |
| rec_areas | 3,671 | Yes |
| media | 32,500 | No |
| facility_activities | 48,795 | No |
| permit_entrances | 857 | Yes |

## Typical Monthly Change Volume

Based on `last_updated` distribution in the current dataset:

- **Facilities**: 50–200 per month (spikes to ~4K in bulk update months)
- **Campsites**: 1K–3K per month (one-time bulk of 128K in Dec 2025)
- **API calls needed**: ~200–500 per sync (vs ~5,000+ for full pull)
- **Time estimate**: 5–15 minutes (vs 3–5 hours for full pull)

## Implementation: `sync.py`

### Step 1: Read Last Sync Timestamp

```python
last_sync = conn.execute(
    "SELECT value FROM n_meta WHERE key = 'last_sync_date'"
).fetchone()
# Default to 30 days ago if never synced
```

### Step 2: Fetch Changed Facilities

```
GET /api/v1/facilities?lastupdated=MM-DD-YYYY&limit=50&offset=0
```

Paginate through all results. Collect facility IDs and upsert facility rows:

```python
INSERT OR REPLACE INTO facilities (...) VALUES (...)
```

### Step 3: Re-pull Campsites for Changed Facilities

For each changed facility ID:

```
GET /api/v1/facilities/{id}/campsites?limit=50&offset=0
```

Each campsite response includes nested `attributes` and `equipment` arrays. For each changed facility:

1. `DELETE FROM campsites WHERE facility_id = ?`
2. `DELETE FROM campsite_attributes WHERE campsite_id IN (SELECT campsite_id FROM ...)`
3. `DELETE FROM campsite_equipment WHERE campsite_id IN (SELECT campsite_id FROM ...)`
4. Insert fresh campsite + attribute + equipment rows

### Step 4: Re-pull Related Data for Changed Facilities

For each changed facility:

```
GET /api/v1/facilities/{id}/media
GET /api/v1/facilities/{id}/activities
```

Delete and re-insert for each facility.

### Step 5: Check for Changed Campsites Independently

Campsites can change without their parent facility changing. Check:

```
GET /api/v1/campsites?lastupdated=MM-DD-YYYY&limit=50&offset=0
```

Pull any campsites not already covered by Step 3. Re-pull their attributes and equipment.

### Step 6: Re-run Full Pipeline

The pipeline is fast enough to re-run fully (~12 seconds total):

```bash
python normalize.py   # 11s — pivots EAV, parses descriptions
python rollup.py      # 0.6s — aggregates to facility level
python classify.py    # 0.2s — conditions + tags
python prepare_db.py  # 0.1s — indexes, photos, state cache
```

No need for per-facility pipeline logic. The scripts do full DELETE + re-INSERT on normalized tables, so they rebuild cleanly from whatever is in the raw tables.

### Step 7: Update Sync Timestamp

```python
INSERT OR REPLACE INTO n_meta (key, value, updated_at)
VALUES ('last_sync_date', '2026-02-07', datetime('now'))
```

### Step 8: Log Results

Print a summary:

```
Sync complete — 2026-02-07
  Facilities updated: 47
  Campsites updated: 312
  API calls: 198
  Duration: 6m 32s
  Pipeline re-run: 11.8s
```

## Deployment

- Run as a daily cron job: `0 3 * * * cd /path/to/fedcamp && source venv/bin/activate && python sync.py`
- Requires `RIDB_API_KEY` environment variable
- Safe to run multiple times (idempotent — upserts + full pipeline rebuild)
- If sync fails mid-run, next run picks up where it left off (unchanged `last_sync_date`)

## Edge Cases

- **Deleted facilities**: RIDB API doesn't surface deletions. Periodic full pulls (monthly?) can catch these, or just accept stale entries.
- **Bulk update months**: Occasionally RIDB does mass updates (e.g., 4K facilities in Feb 2026). The sync will take longer but still work — just more API calls.
- **New facilities**: The `lastupdated` filter catches new records too (their `LastUpdatedDate` is their creation date).
- **campsite_attributes has no `last_updated`**: This is fine — we re-pull all attributes for any campsite that changed, via the nested response from `/facilities/{id}/campsites`.
