import inspect
from memori import Memori

print("=== Constructor Signature ===")
print(inspect.signature(Memori.__init__))

print("\n=== Public Methods ===")
for name in sorted(dir(Memori)):
    if not name.startswith('_'):
        attr = getattr(Memori, name)
        if callable(attr):
            try:
                sig = inspect.signature(attr)
                print(f"  {name}{sig}")
            except (ValueError, TypeError):
                print(f"  {name}(...)")
        else:
            print(f"  {name} = {type(attr).__name__}")
