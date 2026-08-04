"""
Produce a slimmed app-only DB for deployment.

The Flask app only reads ~10 tables. The rest (raw EAV tables, intermediate
normalized tables, rec areas, etc.) are pipeline-only and add hundreds of MB
to the SQLite file. This script copies ridb.db -> ridb_app.db, drops the
unused tables, VACUUMs, and reports the size.

Usage:
    python purge_for_deploy.py            # ridb.db -> ridb_app.db
    python purge_for_deploy.py --check    # just report what would be dropped
"""
import argparse
import os
import shutil
import sqlite3
import sys
import time

SRC = "ridb.db"
DST = "ridb_app.db"

# Tables the Flask app actually reads (verified via grep over db.py/app.py/stats.py)
KEEP = {
    "facilities",
    "campsites",
    "facility_addresses",
    "facility_activities",
    "media",
    "n_facility_rollup",
    "n_facility_conditions",
    "n_facility_tags",
    "n_facility_photo",
    "n_state_cache",
    "n_meta",
}


def list_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def table_sizes(conn):
    """Approximate row count per table."""
    sizes = {}
    for t in list_tables(conn):
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        sizes[t] = n
    return sizes


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true",
                   help="Report what would be dropped, don't write ridb_app.db")
    args = p.parse_args()

    if not os.path.exists(SRC):
        sys.exit(f"ERROR: {SRC} not found")

    # Inspect source
    src_conn = sqlite3.connect(SRC)
    src_size_mb = os.path.getsize(SRC) / 1024 / 1024
    sizes = table_sizes(src_conn)
    src_conn.close()

    keep_present = sorted(t for t in sizes if t in KEEP)
    drop_present = sorted(t for t in sizes if t not in KEEP)
    keep_missing = sorted(KEEP - set(sizes))

    print(f"Source: {SRC} ({src_size_mb:.1f} MB)")
    print(f"\nKeep ({len(keep_present)} tables — app-reachable):")
    for t in keep_present:
        print(f"  {t:<28} {sizes[t]:>12,} rows")

    print(f"\nDrop ({len(drop_present)} tables — pipeline-only):")
    for t in drop_present:
        print(f"  {t:<28} {sizes[t]:>12,} rows")

    if keep_missing:
        print(f"\nWARNING: app expects but source is missing: {keep_missing}")

    if args.check:
        print("\n--check: no files written.")
        return

    # Copy then drop
    if os.path.exists(DST):
        os.remove(DST)
    print(f"\nCopying {SRC} -> {DST}...")
    t0 = time.time()
    shutil.copyfile(SRC, DST)
    print(f"  done in {time.time() - t0:.1f}s")

    print("Dropping unused tables...")
    dst_conn = sqlite3.connect(DST)
    cur = dst_conn.cursor()
    for t in drop_present:
        cur.execute(f"DROP TABLE IF EXISTS {t}")
    dst_conn.commit()

    # Build query planner statistics. Without sqlite_stat1 the planner guesses,
    # and it guesses wrong: the facility-page photos query was picking
    # idx_media_type and scanning all ~35K image rows (34.7ms) instead of
    # idx_campsites_facility -> idx_media_preview (0.006ms). VACUUM preserves
    # sqlite_stat1, so this has to run before it, not after.
    print("ANALYZE...")
    t0 = time.time()
    cur.execute("ANALYZE")
    dst_conn.commit()
    print(f"  done in {time.time() - t0:.1f}s")

    print("VACUUM...")
    t0 = time.time()
    cur.execute("VACUUM")
    dst_conn.commit()
    print(f"  done in {time.time() - t0:.1f}s")

    dst_conn.close()
    dst_size_mb = os.path.getsize(DST) / 1024 / 1024
    print(f"\nResult: {DST} ({dst_size_mb:.1f} MB, "
          f"{(1 - dst_size_mb / src_size_mb) * 100:.0f}% smaller)")


if __name__ == "__main__":
    main()
