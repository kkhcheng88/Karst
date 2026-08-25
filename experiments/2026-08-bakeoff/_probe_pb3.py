import inspect
import pybroker as pb
from pybroker.context import RotationContext
from pybroker.strategy import Strategy

for m in ("enable_rotation", "optimize", "set_max_long_positions"):
    fn = getattr(Strategy, m)
    print("==", m, list(inspect.signature(fn).parameters))
    print((fn.__doc__ or "").strip()[:1200])
    print()
print("ROTCTX_FIELDS", [f for f in getattr(RotationContext, "__dataclass_fields__", {})])
print("ROTCTX_ANNOT", list(getattr(RotationContext, "__annotations__", {}).items())[:20])
print("SYMSEL_ANNOT", list(getattr(pb.SymbolSelector, "__annotations__", {}).items())[:20])
print("SYMSEL_DOC", (pb.SymbolSelector.__doc__ or "")[:600])
