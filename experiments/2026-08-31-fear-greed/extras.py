"""KARST-120 補充口徑:訊號命中/誤報計數、超額的噪音尺度、2020 疫市為何黃金撈底無響。

不新增任何判準、不改任何參數——只是把 results.json 已有的東西攤開,
再加兩格解釋性診斷(標準誤、2020-03 的實際讀數)。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]


def wilder_rsi(close: np.ndarray, n: int) -> np.ndarray:
    m = len(close)
    out = np.full(m, np.nan)
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_g, avg_l = gain[:n].mean(), loss[:n].mean()
    out[n] = 100.0 if avg_l == 0 else 100.0 - 100.0 / (1.0 + avg_g / avg_l)
    for i in range(n, m - 1):
        avg_g = (avg_g * (n - 1) + gain[i]) / n
        avg_l = (avg_l * (n - 1) + loss[i]) / n
        out[i + 1] = 100.0 if avg_l == 0 else (0.0 if avg_g == 0 else 100.0 - 100.0 / (1.0 + avg_g / avg_l))
    return out


def main() -> None:
    res = json.load(open(HERE / "results.json", encoding="utf-8"))
    sig = pd.read_csv(HERE / "signals.csv")
    out: dict = {"counts": {}, "noise": {}, "diagnostics": {}}

    for key, col, direction in (
        ("G1", "fwd21_spy_pct", "down"),
        ("G2", "fwd21_spy_pct", "down"),
        ("F1", "fwd21_leader_pct", "up"),
        ("F2", "fwd21_spy_pct", "up"),
    ):
        s = sig[sig["signal"] == key][col].dropna().to_numpy()
        hit = int((s < 0).sum()) if direction == "down" else int((s > 0).sum())
        out["counts"][key] = {"fired": len(s), "hit": hit, "false": len(s) - hit,
                              "precision": round(hit / len(s), 4)}
        out["noise"][key] = {
            "mean_pct": round(float(s.mean()), 4),
            "sd_pct": round(float(s.std(ddof=1)), 4),
            "stderr_pct": round(float(s.std(ddof=1) / np.sqrt(len(s))), 4),
            "note": "重疊窗令有效樣本遠少於響的次數,此標準誤是樂觀下限",
        }

    px = pd.read_parquet(HERE / "prices_daily.parquet")
    close = px.pivot(index="date", columns="ticker", values="close")[SECTORS + ["SPY"]].dropna()
    r2 = pd.DataFrame({t: wilder_rsi(close[t].to_numpy(), 2) for t in close.columns}, index=close.index)
    mar = r2.loc["2020-03-01":"2020-04-03"]
    ncold = (mar[SECTORS] <= 10).sum(axis=1)
    out["diagnostics"]["2020_03"] = {
        "spy_rsi2_min": round(float(mar["SPY"].min()), 2),
        "days_spy_rsi2_le5": int((mar["SPY"] <= 5).sum()),
        "max_sectors_rsi2_le10": int(ncold.max()),
        "days_both": int(((mar["SPY"] <= 5) & (ncold >= 7)).sum()),
    }
    # 2008 的恐半:撈底撈到刀,量一量最深那幾次
    f1 = sig[(sig["signal"] == "F1") & (sig["date"] >= "2008-01-01") & (sig["date"] <= "2009-03-31")]
    out["diagnostics"]["2008_F1"] = f1[["date", "leader", "fwd21_leader_pct"]].to_dict("records")

    (HERE / "extras.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
