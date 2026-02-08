"""Part 3: Sections 8-11 — Organizations, Rec Areas, Links, Activities"""
import sqlite3

DB_PATH = "ridb.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

out = []
def p(s=""):
    out.append(s)
    print(s)

EQ80 = "=" * 80
def section(n, title):
    p(f"\n{EQ80}")
    p(f"  {n}. {title}")
    p(f"{EQ80}")

def query(sql, params=None):
    if params:
        c.execute(sql, params)
    else:
        c.execute(sql)
    return c.fetchall()
