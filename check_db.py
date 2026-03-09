import sqlite3
conn = sqlite3.connect("memora.db")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
for t in tables:
    count = conn.execute(f"SELECT count(*) FROM [{t[0]}]").fetchone()[0]
    print(f"{t[0]}: {count} rows")
conn.close()
