"""Test dashboard and calendar API responses."""
import requests

# Test 1: Dashboard
print("=== Dashboard ===")
r = requests.get("http://localhost:8000/api/dashboard")
print(f"Status: {r.status_code}")
d = r.json()
print(f"Date: {d.get('date')}")
print(f"Tasks count: {len(d.get('tasks', []))}")
for t in d.get("tasks", []):
    print(f"  - {t.get('title')} | start={t.get('scheduled_start')} | status={t.get('status')}")
print(f"Upcoming count: {len(d.get('upcoming', []))}")
for t in d.get("upcoming", []):
    print(f"  - {t.get('title')} | start={t.get('scheduled_start')}")
print(f"Week load: {d.get('week_load')}")
print(f"Completion %: {d.get('completion_percentage')}")
print(f"Inbox: {d.get('inbox_count')}")
print()

# Test 2: Calendar events for this week
print("=== Calendar (Mar 8-15) ===")
r2 = requests.get("http://localhost:8000/api/calendar", params={"start": "2026-03-08", "end": "2026-03-15"})
print(f"Status: {r2.status_code}")
events = r2.json()
print(f"Events count: {len(events)}")
for e in events:
    print(f"  - {e.get('title')} | start={e.get('scheduled_start')} | end={e.get('scheduled_end')}")
print()

# Test 3: Raw tasks
print("=== Tasks ===")
r3 = requests.get("http://localhost:8000/api/tasks")
print(f"Status: {r3.status_code}")
tasks = r3.json()
print(f"Tasks count: {len(tasks)}")
for t in tasks:
    print(f"  - id={t.get('id')} {t.get('title')} | start={t.get('scheduled_start')} | end={t.get('scheduled_end')} | status={t.get('status')}")
