import inspect, sqlite3, sys

with open("memori_api.txt", "w") as f:
    from memori import Memori

    f.write("=== CONSTRUCTOR ===\n")
    f.write(str(inspect.signature(Memori.__init__)) + "\n\n")

    f.write("=== PUBLIC METHODS ===\n")
    for name in sorted(dir(Memori)):
        if not name.startswith('_'):
            attr = getattr(Memori, name)
            if callable(attr):
                try:
                    sig = inspect.signature(attr)
                    f.write(f"  {name}{sig}\n")
                except:
                    f.write(f"  {name}(...)\n")
            else:
                f.write(f"  {name} = {type(attr).__name__}\n")

    f.write("\n=== INSTANTIATION TEST ===\n")
    try:
        m = Memori(conn=lambda: sqlite3.connect("memora.db"))
        f.write(f"Created OK, type: {type(m)}\n")
        f.write(f"Has .llm: {hasattr(m, 'llm')}\n")
        f.write(f"Has .config: {hasattr(m, 'config')}\n")
        if hasattr(m, 'llm'):
            f.write(f"  llm type: {type(m.llm)}\n")
            llm_attrs = [x for x in dir(m.llm) if not x.startswith('_')]
            f.write(f"  llm attrs: {llm_attrs}\n")
            if hasattr(m.llm, 'register'):
                f.write(f"  register sig: {inspect.signature(m.llm.register)}\n")
        if hasattr(m, 'config'):
            f.write(f"  config type: {type(m.config)}\n")
            cfg_attrs = [x for x in dir(m.config) if not x.startswith('_')]
            f.write(f"  config attrs: {cfg_attrs}\n")
    except Exception as e:
        f.write(f"Error: {e}\n")

print("Written to memori_api.txt")
