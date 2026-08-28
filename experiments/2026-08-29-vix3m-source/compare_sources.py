"""KARST-058:VIX 與 VIX_3M 兩個來源的重疊期逐日對照。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-29-vix3m-source/compare_sources.py

答一條問題:**把 VIX 與 VIX_3M 由 yfinance 換去 Cboe 官方歷史檔,換到的是不是
同一條數?** 換來源的風險不在「新來源有沒有數」——那看一眼就知;風險在「新來源
的數與舊來源對不上,而我們照舊拿舊成績與新成績比」。所以這裡逐日逐格對,把差異
攤出來,不做平均掩蓋。

做四件:

1. 兩邊各自抓 2015-01-02 ~ 窗口尾:yfinance 抓 ``^VIX`` / ``^VIX3M``,
   Cboe 抓官方免費歷史檔 ``VIX_History.csv`` / ``VIX3M_History.csv``。
2. 逐日內連接,算絕對差與相對差,落 ``逐日對照-<序列>.csv``。
3. 逐條序列出差異摘要(重疊日數、最大絕對差、逐日完全相同的日數、各自的首尾日)。
4. 另出一張 ``尾段補回.csv``:舊來源停更之後、新來源仍有數的那一段逐日讀數——
   這一段就是這張票要補回來的東西。

**本檔不寫庫、不凍快照、不跑回測**:只抓數、只對數、只落檔。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:  # 未裝套件也跑得動(倉根就在上兩層)
    sys.path.insert(0, str(REPO))

import pandas as pd  # noqa: E402

from karst.data.macro import (  # noqa: E402
    MACRO_SOURCE_NAME,
    CboeMacroSource,
    MacroSeries,
    YFinanceMacroSource,
    series_of,
)

HERE = Path(__file__).resolve().parent

WINDOW_START = "2015-01-02"
WINDOW_END = "2026-08-27"

# 舊來源代號:名冊上這兩條已經改成 Cboe(KARST-058),所以舊那一邊在這裡就地重建。
# 這正是「序列代號不變、只換來源代號」的另一面:同一個 VIX_3M,兩個 symbol 對得住。
LEGACY = {
    "VIX": MacroSeries(
        code="VIX",
        symbol="^VIX",
        source=MACRO_SOURCE_NAME,
        tier="第一層",
        family="波動率",
        label="CBOE 波動率指數(30 日)",
        unit="年化波動率點數",
        note="KARST-058 之前的來源代號",
    ),
    "VIX_3M": MacroSeries(
        code="VIX_3M",
        symbol="^VIX3M",
        source=MACRO_SOURCE_NAME,
        tier="第一層",
        family="波動率",
        label="CBOE 波動率指數(3 個月)",
        unit="年化波動率點數",
        note="KARST-058 之前的來源代號",
    ),
}

CODES = ("VIX", "VIX_3M")


def _pull(source, items, label: str) -> pd.DataFrame:
    frame = source.fetch_daily_series(items, WINDOW_START, WINDOW_END)
    print(
        f"  {label}:{len(frame)} 列,"
        + "、".join(
            f"{code} {block['date'].min()}~{block['date'].max()}({len(block)} 日)"
            for code, block in frame.groupby("series", sort=True)
        ),
        flush=True,
    )
    return frame


def main() -> int:
    print(f"窗口 {WINDOW_START} ~ {WINDOW_END}", flush=True)
    print("抓數(兩邊各自抓,不共用任何一步)……", flush=True)

    old = _pull(
        YFinanceMacroSource(), [LEGACY[code] for code in CODES], "yfinance(舊來源)"
    )
    new = _pull(CboeMacroSource(), series_of(CODES), "Cboe 官方歷史檔(新來源)")

    summary: dict[str, object] = {
        "ticket": "KARST-058",
        "window": [WINDOW_START, WINDOW_END],
        "old_source": {
            "name": "yfinance-macro",
            "symbols": {code: LEGACY[code].symbol for code in CODES},
        },
        "new_source": {
            "name": "cboe-macro",
            "symbols": {item.code: item.symbol for item in series_of(CODES)},
            "url": "https://cdn.cboe.com/api/global/us_indices/daily_prices/<代號>_History.csv",
        },
        "series": {},
    }

    rows: list[dict[str, object]] = []
    for code in CODES:
        left = (
            old.loc[old["series"] == code, ["date", "value"]]
            .rename(columns={"value": "yfinance"})
            .set_index("date")
        )
        right = (
            new.loc[new["series"] == code, ["date", "value"]]
            .rename(columns={"value": "cboe"})
            .set_index("date")
        )
        joined = left.join(right, how="inner").sort_index()
        joined["絕對差"] = (joined["cboe"] - joined["yfinance"]).abs()
        joined["相對差"] = joined["絕對差"] / joined["yfinance"].abs()
        out = joined.reset_index().rename(
            columns={"date": "日期", "yfinance": "舊來源(yfinance)", "cboe": "新來源(Cboe)"}
        )
        out.to_csv(HERE / f"逐日對照-{code}.csv", index=False, encoding="utf-8-sig")

        # 舊來源停更之後、新來源仍有數的那一段
        last_old = str(left.index.max())
        tail = right.loc[right.index > last_old].reset_index()
        tail.columns = ["日期", "新來源(Cboe)"]
        if not tail.empty:
            tail.to_csv(HERE / f"尾段補回-{code}.csv", index=False, encoding="utf-8-sig")

        identical = int((joined["絕對差"] == 0.0).sum())
        stat = {
            "overlap_days": int(len(joined)),
            "identical_days": identical,
            "identical_share": round(identical / len(joined), 6) if len(joined) else None,
            "max_abs_diff": float(joined["絕對差"].max()) if len(joined) else None,
            "mean_abs_diff": float(joined["絕對差"].mean()) if len(joined) else None,
            "max_rel_diff": float(joined["相對差"].max()) if len(joined) else None,
            "old_first": str(left.index.min()),
            "old_last": last_old,
            "new_first": str(right.index.min()),
            "new_last": str(right.index.max()),
            "tail_days_recovered": int(len(tail)),
            "tail_first": str(tail["日期"].iloc[0]) if not tail.empty else None,
            "tail_last": str(tail["日期"].iloc[-1]) if not tail.empty else None,
        }
        summary["series"][code] = stat  # type: ignore[index]
        rows.append(
            {
                "序列代號": code,
                "舊來源代號": LEGACY[code].symbol,
                "新來源代號": next(i.symbol for i in series_of([code])),
                "重疊日數": stat["overlap_days"],
                "逐日完全相同": stat["identical_days"],
                "完全相同佔比": stat["identical_share"],
                "最大絕對差": stat["max_abs_diff"],
                "平均絕對差": stat["mean_abs_diff"],
                "最大相對差": stat["max_rel_diff"],
                "舊來源尾日": stat["old_last"],
                "新來源尾日": stat["new_last"],
                "尾段補回日數": stat["tail_days_recovered"],
            }
        )

    table = pd.DataFrame(rows)
    table.to_csv(HERE / "差異摘要.csv", index=False, encoding="utf-8-sig")

    # 期限結構比率本身:換來源之後那個比率有沒有走樣
    ratio_rows = []
    for label, frame in (("舊來源(yfinance)", old), ("新來源(Cboe)", new)):
        panel = frame.pivot(index="date", columns="series", values="value").dropna()
        ratio = panel["VIX"] / panel["VIX_3M"]
        ratio_rows.append(
            {
                "來源": label,
                "有比率的日數": int(len(ratio)),
                "首日": str(ratio.index.min()),
                "尾日": str(ratio.index.max()),
                "比率平均": float(ratio.mean()),
                "倒掛日數(比率>1)": int((ratio > 1.0).sum()),
                "倒掛佔比": float((ratio > 1.0).mean()),
            }
        )
    ratio_table = pd.DataFrame(ratio_rows)
    ratio_table.to_csv(HERE / "期限結構比率對照.csv", index=False, encoding="utf-8-sig")
    summary["term_structure"] = json.loads(ratio_table.to_json(orient="records"))

    (HERE / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with pd.option_context("display.width", 220, "display.max_columns", 40):
        print("\n=== 兩來源差異摘要 ===", flush=True)
        print(table.to_string(index=False), flush=True)
        print("\n=== 期限結構比率(VIX ÷ VIX_3M) ===", flush=True)
        print(ratio_table.to_string(index=False), flush=True)
    print(f"\n落檔:{HERE}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
