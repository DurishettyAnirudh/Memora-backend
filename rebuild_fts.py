"""Rebuild FTS index."""
from app.database import SessionLocal
from app.models.task import Task
from sqlalchemy import text

db = SessionLocal()

# Check schema
r = db.execute(text("SELECT sql FROM sqlite_master WHERE name='tasks_fts'")).fetchone()
print("FTS schema:", r[0] if r else "NOT FOUND")

# Clear and repopulate
db.execute(text("DELETE FROM tasks_fts"))
rows = db.query(Task).all()
for t in rows:
    db.execute(text("INSERT INTO tasks_fts(rowid, title) VALUES (:id, :title)"),
               {"id": t.id, "title": t.title})
db.commit()
print(f"FTS rebuilt with {len(rows)} rows")
db.close()
