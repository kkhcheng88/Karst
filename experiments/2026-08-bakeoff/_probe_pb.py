import dataclasses
import inspect
import pybroker as pb

print("VERSION", getattr(pb, "__version__", "?"))
print("TOPLEVEL", sorted(x for x in dir(pb) if not x.startswith("_")))
cfg = pb.StrategyConfig
try:
    print("CONFIG_FIELDS", [f.name for f in dataclasses.fields(cfg)])
except Exception as e:
    print("CONFIG_ERR", e)
print("STRATEGY_SIG", list(inspect.signature(pb.Strategy.__init__).parameters))
for m in ("add_execution", "backtest", "walkforward"):
    fn = getattr(pb.Strategy, m, None)
    print(m, list(inspect.signature(fn).parameters) if fn else "MISSING")
ctx = pb.ExecContext
print("CTX", sorted(x for x in dir(ctx) if not x.startswith("_")))
