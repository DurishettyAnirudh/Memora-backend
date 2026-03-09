import inspect, sqlite3
from memori import Memori

print("=== MEMORI CONSTRUCTOR ===")
print(inspect.signature(Memori.__init__))

print("\n=== MEMORI PUBLIC METHODS ===")
for name in sorted(dir(Memori)):
    if not name.startswith('_'):
        attr = getattr(Memori, name)
        if callable(attr):
            try:
                sig = inspect.signature(attr)
                print(f"  {name}{sig}")
            except:
                print(f"  {name}(...)")
        else:
            print(f"  {name} = {type(attr).__name__}")

print("\n=== TRYING TO INSTANTIATE ===")
try:
    m = Memori(conn=lambda: sqlite3.connect("memora.db"))
    print(f"Memori created, type: {type(m)}")
    print(f"Has .llm: {hasattr(m, 'llm')}")
    print(f"Has .config: {hasattr(m, 'config')}")
    if hasattr(m, 'llm'):
        print(f"  llm type: {type(m.llm)}")
        print(f"  llm dir: {[x for x in dir(m.llm) if not x.startswith('_')]}")
except Exception as e:
    print(f"Error: {e}")
