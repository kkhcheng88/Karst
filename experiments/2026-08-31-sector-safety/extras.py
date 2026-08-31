import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
p = pd.read_csv(HERE / "monthly_panel.csv", index_col=0)
p.index = pd.PeriodIndex(p.index, freq="M")
r = json.loads((HERE / "results.json").read_text(encoding="utf-8"))

print("=== IEF 自身 10 個月線濾網:五次熊逐月 ===")
for name, (a, b) in {
    "2008": ("2007-11", "2009-03"),
    "2018Q4": ("2018-10", "2018-12"),
    "2020": ("2020-03", "2020-03"),
    "2022": ("2022-02", "2022-10"),
}.items():
    seg = p.loc[(p.index >= pd.Period(a)) & (p.index <= pd.Period(b))]
    ok = seg["ief_safe"]
    print(f"{name}: 通過濾網的月數 {int(ok.sum())}/{len(ok)} -> {list(ok.astype('object'))}")

print()
print("=== IEF 濾網全樣本(2003-08 起有得算)===")
sub = p["ief_safe"].dropna()
print(f"月數 {len(sub)},通過 {int(sub.sum())} ({100*sub.mean():.1f}%),由 {sub.index[0]} 起")

print()
print("=== 真值乙(D-053 原文口徑:九隻最好那隻回報 < 0)全樣本 ===")
for label in ("A", "A1", "B", "C"):
    s = r["criteria"][label]["full_truthB"]
    print(
        f"判準 {label}: 響 {s['fires']} | 命中 {s['hit']} 誤報 {s['false_alarm']} "
        f"走漏 {s['miss']} | 精確度 {s['precision_pct']:.1f}% 捕捉率 {s['recall_pct']:.1f}%"
    )
print(
    f"基礎率 {r['base']['bestsec_down_rate_pct']:.1f}%,"
    f"打和精確度 {r['base']['bestsec_breakeven_precision_pct']:.1f}%"
)

print()
print("=== 判準甲響的那 20 個月,SPY 之後的表現 ===")
fires = [pd.Period(m) for m in r["criteria"]["A"]["fire_months"]]
seg = p.loc[fires, ["spy_ret"]]
print(f"平均 {100*seg['spy_ret'].mean():.2f}% 中位 {100*seg['spy_ret'].median():.2f}% "
      f"上升月 {int((seg['spy_ret']>0).sum())}/{len(seg)}")

print()
print("=== 判準丙那 5 次逐次 ===")
for m in r["criteria"]["C"]["fire_months"]:
    per = pd.Period(m)
    row = p.loc[per]
    print(f"  {m}: SPY {100*row['spy_ret']:+.2f}%  IEF {100*row['ief_ret']:+.2f}%  "
          f"安全板塊數 {row['safe_count']:.0f}  持倉百分位 {row['d_np_pctile']:.1f}")

print()
print("=== 判準乙覆蓋:首個訊號月與熊市覆蓋 ===")
b = p["d_np_pctile"].dropna()
print(f"首個有數據的持有月 {b.index[0]},最後 {b.index[-1]},共 {len(b)} 月;"
      f"全樣本 331 月之中無數據 {331-len(b)} 月")
