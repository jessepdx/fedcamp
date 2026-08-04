"""Rebuild n_state_cache in place so it matches what search returns.

The counts sit next to the state picker, so they are a promise: choosing a
state must return that many campgrounds. Keeping them honest means deriving
them from the same rules search uses — the preferred-address join, the
facility_name filter, and the default camping types.

Safe to re-run: the table is dropped and rebuilt from the facility data, and
it is a ~50-row derived cache with no independent state of its own.

Usage:
    python rebuild_state_cache.py [path-to-db]     # defaults to ridb.db
"""
import sqlite3
import sys

import db

SQL = """
    SELECT fa.state_code, COUNT(*)
    FROM n_facility_rollup r
    {addr_join}
    WHERE r.facility_name IS NOT NULL AND r.facility_name <> ''
      AND r.camping_type IN ({types})
      AND fa.state_code IS NOT NULL AND fa.state_code <> ''
    GROUP BY fa.state_code
    ORDER BY fa.state_code
""".format(addr_join=db.PREFERRED_ADDRESS_JOIN,
           types=",".join("'%s'" % t for t in db.DEFAULT_CAMPING_TYPES))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else db.DB_PATH
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    try:
        before = cur.execute(
            "SELECT COUNT(*), SUM(facility_count) FROM n_state_cache").fetchone()
    except sqlite3.OperationalError:
        before = (0, 0)

    rows = cur.execute(SQL).fetchall()
    if not rows:
        print("ERROR: rebuild produced no rows — refusing to write", file=sys.stderr)
        conn.close()
        return 1

    cur.execute("DROP TABLE IF EXISTS n_state_cache")
    cur.execute("""
        CREATE TABLE n_state_cache (
            state_code      TEXT PRIMARY KEY,
            facility_count  INTEGER NOT NULL
        )
    """)
    cur.executemany(
        "INSERT INTO n_state_cache (state_code, facility_count) VALUES (?, ?)",
        rows)
    conn.commit()

    after = cur.execute(
        "SELECT COUNT(*), SUM(facility_count) FROM n_state_cache").fetchone()
    conn.close()

    removed = (before[1] or 0) - after[1]
    print(f"  before: {before[0]} states, {before[1] or 0:,} facilities")
    print(f"  after:  {after[0]} states, {after[1]:,} facilities"
          + (f" ({removed:,} phantom entries removed)" if removed > 0
             else " (already correct)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
