"""Final validation of chat agent — all key scenarios."""
import requests

BASE = "http://localhost:8000/api/chat"
history = []

def chat(msg):
    global history
    r = requests.post(BASE, json={"message": msg, "history": history[-10:]})
    d = r.json()
    events = [f"{e['type']}: {e.get('message','')}" for e in d.get("events", [])]
    print(f"  User: {msg}")
    print(f"  Memora: {d['reply']}")
    if events:
        print(f"  Actions: {events}")
    print()
    # Track history
    history.append({"role": "user", "content": msg})
    history.append({"role": "assistant", "content": d["reply"]})
    return d

print("=" * 60)
print("  CHAT AGENT VALIDATION")
print("=" * 60)
print()

print("--- 1. Greeting ---")
chat("Hello!")

print("--- 2. Ask about tasks ---")
chat("What tasks do I have?")

print("--- 3. Delete specific task ---")
chat("Delete the gym workout task")

print("--- 4. Follow-up with context ---")
chat("What do I have left now?")

print("--- 5. Create a new task ---")
chat("Add a yoga class tomorrow at 8am")

print("--- 6. Casual chitchat ---")
chat("Thanks, you're really helpful!")

print("=" * 60)
print("  VALIDATION COMPLETE")
print("=" * 60)
