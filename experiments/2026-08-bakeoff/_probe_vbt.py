import inspect
import vectorbt as vbt

print("VERSION", vbt.__version__)
pf = vbt.Portfolio
print("PF_METHODS", sorted(m for m in dir(pf) if m.startswith("from_")))
for name in ("from_orders", "from_signals", "from_order_func"):
    fn = getattr(pf, name, None)
    if fn is None:
        print(name, "MISSING")
        continue
    try:
        sig = inspect.signature(fn)
        print("---", name, "---")
        print([p for p in sig.parameters])
    except Exception as e:  # pragma: no cover
        print(name, "SIGERR", e)
print("TOPLEVEL", sorted(x for x in dir(vbt) if not x.startswith("_"))[:60])
