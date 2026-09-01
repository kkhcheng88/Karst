"""KARST-140 診斷:主判口徑那六隻到底揀咗啲乜。純描述,不改口徑、不改判準。"""
from __future__ import annotations
import pathlib
import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
FWD = HERE.parent / "2026-09-02-forward-yield-build"
OUT = HERE / "out"

fwd = pd.read_parquet(FWD / "data" / "member_forward.parquet")
fwd = fwd[(fwd["month_end"] >= fwd["joined_on"]) & (fwd["month_end"] < fwd["left_on"])]
fwd = fwd[fwd["mcap"] > 0].copy()
fwd["ey_fwd1"] = fwd["earn_fwd1"] / fwd["mcap"]
fwd["ey_fwd4"] = fwd["earn_fwd4"] / fwd["mcap"]

lines = []
for col in ("ey_fwd1", "ey_fwd4"):
    s = fwd[col].dropna()
    q = s.quantile([0.5, 0.9, 0.99, 0.999, 1.0])
    lines.append(f"{col}: n={len(s)} 中位={q[0.5]:.4f} p90={q[0.9]:.4f} "
                 f"p99={q[0.99]:.4f} p999={q[0.999]:.4f} 最大={q[1.0]:.4f}")

for col in ("ey_fwd1", "ey_fwd4"):
    m = pd.read_csv(OUT / f"monthly_{col}.csv")
    syms = pd.Series(",".join(m["hold"]).split(","))
    lines.append(f"\n=== {col} 持倉 ===")
    lines.append(f"不同股票數={syms.nunique()} 總格數={len(syms)}")
    lines.append("最常持有 15 隻: " + ", ".join(
        f"{s}({c})" for s, c in syms.value_counts().head(15).items()))
    # 持倉當月的分數水平
    hold = []
    for _, r in m.iterrows():
        me = pd.Timestamp(r["month_end"])
        for s in str(r["hold"]).split(","):
            hold.append((me, s))
    h = pd.DataFrame(hold, columns=["month_end", "symbol"])
    h = h.merge(fwd[["month_end", "symbol", col, "mcap", "close", "fwd_eps1",
                     "fwd_eps4", "lowprec"]], on=["month_end", "symbol"])
    lines.append(f"持倉分數 中位={h[col].median():.4f} p90={h[col].quantile(0.9):.4f} "
                 f"最大={h[col].max():.4f}")
    lines.append(f"持倉分數 >100%(即前瞻收益率超過一倍)佔比: "
                 f"{(h[col] > 1.0).mean()*100:.1f}%")
    lines.append(f"持倉分數 >50% 佔比: {(h[col] > 0.5).mean()*100:.1f}%")
    lines.append(f"持倉市值中位(億美元)={h['mcap'].median()/1e8:.1f}  "
                 f"全體中位={fwd['mcap'].median()/1e8:.1f}")
    lines.append(f"持倉低精度標記佔比: {h['lowprec'].astype(bool).mean()*100:.1f}%  "
                 f"全體={fwd['lowprec'].astype(bool).mean()*100:.1f}%")
    lines.append(f"持倉股價中位={h['close'].median():.2f}  全體中位={fwd['close'].median():.2f}")

txt = "\n".join(lines)
(OUT / "diag.txt").write_text(txt, encoding="utf-8")
print(txt)
