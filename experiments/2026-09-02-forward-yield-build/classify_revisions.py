"""KARST-136:把 Wayback 今昔對照的逐格結果重新分類,量度真‧事後改寫率。

為什麼要重分類:`verify_yahoo_estimate_vintage.py` 判「拆股換算」用的是
「預估比率 ≈ 實際比率」,容差 2%。但 Yahoo 把拆過重股的公司舊季度每股數字
還原到今日基準之後**只保留兩位小數**(KARST-125 §4.1「精度已毀」),0.005 的
進位誤差落在 0.05 上就是 ±10%,遠超 2% 容差,於是一大批純粹是拆股+進位的格
被誤判成「被改寫」。本腳本照 KARST-125 的五分類重判,並把量化誤差傳導進容差。

分類(與 KARST-125 §4.1 表對齊):
  unchanged      今昔逐位相同(容差 0.011)
  split_rescaled 預估與實際同時按同一倍數搬動——單位變了,不是改寫
  precision_lost 今日值已被進位到兩位小數,量化誤差大到判不出——不計入分母
  not_joined     存檔那一列在今日的表裡找不到對應
  rewritten      實際盈利不動(或量化誤差解釋不到),預估卻動了

輸出:revision_cells.csv(逐格)、revision_summary.csv(合計)
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "out" / "vintage_results.json"

EQ_TOL = 0.011      # 逐位相同的容差(兩位小數的一個進位步)
QUANT = 0.005       # 兩位小數的半步
PREC_FLOOR = 0.05   # 相對量化誤差超過此值即判「精度已毀」


def rel_quant(x: float | None) -> float:
    if x is None or x != x or x == 0:
        return 1.0
    return QUANT / abs(x)


def classify(p: dict) -> str:
    if not p.get("joined"):
        return "not_joined"
    te, ne = p.get("then_est"), p.get("now_est")
    ta, na = p.get("then_act"), p.get("now_act")
    if te is None or ne is None:
        return "not_joined"
    if abs(te - ne) < EQ_TOL:
        return "unchanged"
    # 今日值已被進位到兩位小數,量化誤差大到任何比率檢定都失效
    if rel_quant(ne) > PREC_FLOOR or (na is not None and rel_quant(na) > PREC_FLOOR):
        return "precision_lost"
    if ta and na and ne and na != 0 and ne != 0:
        r_est, r_act = te / ne, ta / na
        # 容差要把兩邊的量化誤差一齊傳導進去
        tol = max(0.02, rel_quant(ne) + rel_quant(na)) * max(1.0, abs(r_act))
        if abs(r_est - r_act) < tol:
            return "split_rescaled"
    return "rewritten"


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"未見 {SRC},先跑 revise_probe.py")
    data = json.loads(SRC.read_text(encoding="utf-8"))
    rows = []
    for tk, tres in data.items():
        for chk in tres.get("checked", []):
            for p in chk.get("pairs", []):
                rows.append({
                    "symbol": tk, "snapshot": chk["timestamp"],
                    "quarter": p.get("date"),
                    "then_est": p.get("then_est"), "now_est": p.get("now_est"),
                    "then_act": p.get("then_act"), "now_act": p.get("now_act"),
                    "verdict": classify(p),
                })
    if not rows:
        raise SystemExit("對照結果空白")
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "revision_cells.csv", index=False, encoding="utf-8")

    vc = df["verdict"].value_counts()
    judgeable = int(vc.get("unchanged", 0) + vc.get("split_rescaled", 0)
                    + vc.get("rewritten", 0))
    rate = (vc.get("rewritten", 0) / judgeable) if judgeable else float("nan")
    summ = vc.rename_axis("verdict").reset_index(name="cells")
    summ["share"] = summ["cells"] / len(df)
    summ.to_csv(HERE / "revision_summary.csv", index=False, encoding="utf-8")

    print(f"樣本 {df['symbol'].nunique()} 隻,存檔 {df['snapshot'].nunique()} 份,"
          f"逐格對照 {len(df)} 格")
    print(summ.to_string(index=False))
    print(f"\n判得出結論 {judgeable} 格,其中真‧被改寫 {int(vc.get('rewritten', 0))} 格,"
          f"改寫率 {rate:.1%}")
    print("\n真‧被改寫逐格:")
    r = df[df["verdict"] == "rewritten"]
    if len(r):
        print(r[["symbol", "snapshot", "quarter", "then_est", "now_est",
                 "then_act", "now_act"]].to_string(index=False))


if __name__ == "__main__":
    main()
