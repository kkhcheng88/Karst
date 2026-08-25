import inspect
import pybroker as pb

print("STRATEGY_METHODS", sorted(m for m in dir(pb.Strategy) if not m.startswith("_")))
for m in ("add_rotation", "set_before_exec", "set_after_exec"):
    fn = getattr(pb.Strategy, m, None)
    if fn:
        print(m, list(inspect.signature(fn).parameters))
        d = (fn.__doc__ or "").strip().splitlines()
        print("   doc:", " | ".join(x.strip() for x in d[:6]))
print("ROTCTX", sorted(x for x in dir(pb.RotationContext) if not x.startswith("_")))
print("SYMSEL", sorted(x for x in dir(pb.SymbolSelector) if not x.startswith("_")))
print("optimize", list(inspect.signature(pb.optimize).parameters))
print("register_columns", list(inspect.signature(pb.register_columns).parameters))
print("set_parallel", list(inspect.signature(pb.set_parallel).parameters))
d = (pb.Strategy.add_execution.__doc__ or "").strip().splitlines()
print("ADD_EXEC_DOC:", " | ".join(x.strip() for x in d[:12]))
