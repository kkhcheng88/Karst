import inspect
import pybroker as pb
from pybroker.context import ExecContext

print("ANNOT", list(getattr(ExecContext, "__annotations__", {}).keys()))
print("SLOTS", getattr(ExecContext, "__slots__", None))
src = inspect.getsource(ExecContext.__init__)
print("INIT_SRC_LEN", len(src))
for kw in ("score", "long_score", "short_score"):
    obj = getattr(ExecContext, kw, "ABSENT")
    print(kw, "->", type(obj).__name__, (getattr(obj, "__doc__", "") or "")[:220].replace("\n", " "))
print("---- calc_target_shares ----")
print(list(inspect.signature(ExecContext.calc_target_shares).parameters))
print((ExecContext.calc_target_shares.__doc__ or "")[:400])
print("---- set_target_shares ----")
print(list(inspect.signature(ExecContext.set_target_shares).parameters))
print((ExecContext.set_target_shares.__doc__ or "")[:500])
print("---- FeeMode ----", [m.name for m in pb.FeeMode])
print("---- hyperparam ----", list(inspect.signature(pb.hyperparam).parameters))
print((pb.hyperparam.__doc__ or "")[:600])
