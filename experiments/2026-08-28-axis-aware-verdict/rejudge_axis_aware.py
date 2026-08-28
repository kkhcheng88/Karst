"""KARST-047:把 KARST-043 兩個驅動器的 60 格**重判**一次(不重跑運行)。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-28-axis-aware-verdict/rejudge_axis_aware.py

KARST-043 收檔時舉了一手:現時的鄰域把三條軸一視同仁——回望期移一個月,與
「持現金改成均分」、「月度改成季度」,同樣算「一步之遙」。前者是連續刻度上的
微調,後者是換一套做法。混在同一個鄰域平均裡,一條真山脊會被判成孤峰。

本檔**一次引擎都不動**:只讀 KARST-043 落下的掃描表(連成本那一份,兩個驅動器
各 60 格),用兩套鄰域各判一次——

* **舊口徑**:三條軸全部當連續,即 KARST-043 用的那一個格。判出來的結果**要與
  當日落檔的判讀表逐格對得上**,否則即是本票改動了不該改的東西——所以這一步是
  本檔的自檢,不是裝飾。(KARST-048 之後 ``rotation_grid`` 自己會宣告軸型,所以
  舊口徑要經 ``all_continuous`` 把它還原,不再是它的原樣。)
* **新口徑**:回望期做連續軸,退路(持現金/均分)與節奏(月度/季度)做選擇軸。
  鄰域只沿回望期取,兩條選擇軸切出四層,每層各出一份判讀,並判得出**山脊**。

落檔:逐驅動器一份新判讀表、一份新舊裁決對照表、一份分層判讀表,加四張投影圖
(新舊各兩張,看得到裁決標記由三角變成等號)。

**本檔不裁定哪一格該用**(D-008),亦不改任何既有結果檔——KARST-043 的
``results/`` 只讀不寫。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:  # 未裝套件也跑得動(倉根就在上兩層)
    sys.path.insert(0, str(REPO))

HERE = Path(__file__).resolve().parent

import pandas as pd  # noqa: E402

from karst.sweep.factor_rotation import rotation_grid  # noqa: E402
from karst.sweep.grid import CHOICE, ProductGrid, SweepAxis, all_continuous, layer_label  # noqa: E402
from karst.sweep.report import draw_heatmap  # noqa: E402
from karst.sweep.verdict import LONELY_PEAK, PLATEAU, RIDGE, CellScore, judge  # noqa: E402

# KARST-043 的落檔。**只讀**。
SOURCE = REPO / "experiments" / "2026-08-28-costs-and-regrid" / "results"

# 判讀門檻:與 KARST-043 完全一樣,一個字都不改——改了就分不出「裁決變了」
# 是因為軸型,還是因為門檻。
OBJECTIVE = "annual_excess:SPY"
MIN_TRADES = 30
MARGIN = 0.005
QUANTILE = 0.90

# 兩個驅動器:回望期是連續軸,另外兩條是選擇軸。
DRIVERS = {
    "relative_strength": {
        "title": "相對強弱對 SPY",
        "continuous": ("lookback_months",),
        "choice": ("fallback", "cadence"),
        "values": {"lookback_months": list(range(1, 16)), "fallback": ["cash", "equal"]},
        "cadences": ["monthly", "quarterly"],
    },
    "factor_momentum": {
        "title": "因子動量排名",
        "continuous": ("lookback_months",),
        "choice": ("mode", "cadence"),
        "values": {"lookback_months": list(range(1, 16)), "mode": ["winner", "rank"]},
        "cadences": ["monthly", "quarterly"],
    },
}

COST_LABEL = "連成本(每股 US$0.005 + 滑點 5 個基點)"
PERIOD = ("2015-01-02", "2026-08-26")
SNAPSHOT = "2026-08-27-91a5d51339d9"


def _plain(value):
    """由 CSV 讀回來的 ``numpy.int64`` 一類還原做 Python 型別。

    不還原一樣掃得出格,但軸的次序、標籤與查表都會靜靜地走樣(numpy 的整數不是
    Python ``int`` 的子類)。
    """
    return value.item() if hasattr(value, "item") else value


def _axis_values(frame: pd.DataFrame, name: str) -> list:
    """一條軸在掃描表上出現過的取值,數字軸按大細排,其餘按首次出現。"""
    seen: list = []
    for value in frame[name]:
        value = _plain(value)
        if value not in seen:
            seen.append(value)
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in seen):
        return sorted(seen)
    return seen


def axis_aware_grid(frame: pd.DataFrame, spec: dict) -> ProductGrid:
    """新口徑的格:連續軸照移一步,選擇軸釘死不動、切層。"""
    axes = []
    for name in (*spec["continuous"], *spec["choice"]):
        values = _axis_values(frame, name)
        if name in spec["choice"]:
            axes.append(SweepAxis(name=name, values=tuple(values), ordered=False, kind=CHOICE))
        else:
            axes.append(SweepAxis(name=name, values=tuple(values)))
    return ProductGrid(axes)


def scores_from(frame: pd.DataFrame, grid) -> list[CellScore]:
    """掃描表逐行變成一格成績。目標指標就是 KARST-043 用的對 SPY 年化超額。"""
    names = list(grid.axis_names)
    table = {}
    for _, row in frame.iterrows():
        key = tuple(_plain(row[name]) for name in names)
        table[key] = (float(row["annual_excess_SPY"]), int(row["trades"]))
    out: list[CellScore] = []
    for point in grid.points():
        key = tuple(point.get(name) for name in names)
        if key not in table:
            raise SystemExit(f"掃描表沒有這一格:{point.label}")
        value, trades = table[key]
        out.append(CellScore(point=point, value=value, trades=trades))
    return out


def rejudge(driver_key: str, spec: dict, out_root: Path) -> dict:
    source = SOURCE / f"dense-{driver_key}"
    frame = pd.read_csv(source / "掃描表.csv")
    old_frame = pd.read_csv(source / "判讀表.csv")
    if len(frame) != 60:
        raise SystemExit(f"{driver_key} 的掃描表不是 60 格,是 {len(frame)} 格")

    # --- 舊口徑:三條軸全部連續,即 KARST-043 當日用的那個格 -----------------
    # KARST-048 起 ``rotation_grid`` 自己宣告軸型(退路/模式/節奏是選擇軸),所以
    # 當日那個格要 ``all_continuous`` 還原一次才對得回落檔的判讀表。
    old_grid = all_continuous(
        rotation_grid(driver_key, values=spec["values"], cadences=spec["cadences"])
    )
    old = judge(
        scores_from(frame, old_grid), old_grid, objective=OBJECTIVE,
        min_trades=MIN_TRADES, lonely_peak_margin=MARGIN, plateau_quantile=QUANTILE,
    )

    # 自檢:重判出來的舊裁決要與 KARST-043 落檔的判讀表逐格對得上。
    names = list(old_grid.axis_names)
    filed = {
        tuple(_plain(row[name]) for name in names): str(row["verdict"])
        for _, row in old_frame.iterrows()
    }
    mismatched = [
        cell.point.label
        for cell in old.cells
        if filed.get(tuple(cell.point.get(n) for n in names)) != cell.verdict
    ]
    if mismatched:
        raise SystemExit(
            f"{driver_key}:舊口徑重判與 KARST-043 落檔的判讀表對不上,"
            f"{len(mismatched)} 格不同(例:{mismatched[0]});本票不應改動舊判讀"
        )

    # --- 新口徑:回望期連續,退路與節奏做選擇軸 -----------------------------
    new_grid = axis_aware_grid(frame, spec)
    new = judge(
        scores_from(frame, new_grid), new_grid, objective=OBJECTIVE,
        min_trades=MIN_TRADES, lonely_peak_margin=MARGIN, plateau_quantile=QUANTILE,
    )

    out = out_root / f"dense-{driver_key}"
    out.mkdir(parents=True, exist_ok=True)
    new.frame().to_csv(out / "判讀表-軸型.csv", index=False, encoding="utf-8-sig")
    new.layer_frame().to_csv(out / "分層判讀.csv", index=False, encoding="utf-8-sig")

    # --- 新舊裁決對照表(60 行) --------------------------------------------
    rows = []
    for cell in new.cells:
        key = tuple(cell.point.get(n) for n in names)
        before = old.cell_for(cell.point)
        rows.append(
            {
                **cell.point.as_dict(),
                "層": cell.layer_name,
                OBJECTIVE: cell.value,
                "舊裁決": filed[key],
                "新裁決": cell.verdict,
                "變了": "是" if filed[key] != cell.verdict else "",
                "舊鄰域格數": len(before.neighbours),
                "舊鄰域平均": before.neighbourhood_mean,
                "舊落差": before.lift,
                "新鄰域格數": len(cell.neighbours),
                "新鄰域平均": cell.neighbourhood_mean,
                "新落差": cell.lift,
                "換層最差鄰域平均": cell.weakest_sibling_mean,
                "換層代價": cell.layer_drop,
                "成交筆數": cell.trades,
            }
        )
    table = pd.DataFrame(rows).sort_values(OBJECTIVE, ascending=False)
    table.to_csv(out / "新舊裁決對照表.csv", index=False, encoding="utf-8-sig")

    # --- 投影圖:新舊各兩張,每一行是一層(色塊剛好蓋一格,沒有沖淡) -------
    choice_axis_name = spec["choice"][0]
    charts: list[str] = []
    for cadence in spec["cadences"]:
        for tag, judgement in (("舊判", old), ("新判", new)):
            path = out / f"{tag}-{cadence}-回望期×{choice_axis_name}.png"
            draw_heatmap(
                judgement.where(cadence=cadence),
                path,
                x_axis="lookback_months",
                y_axis=choice_axis_name,
                title=f"{spec['title']}·{tag}({cadence})",
                subtitle=f"{OBJECTIVE}|{PERIOD[0]} ~ {PERIOD[1]}|{COST_LABEL}",
            )
            charts.append(path.name)

    changed = table[table["變了"] == "是"]
    summary = {
        "driver": driver_key,
        "title": spec["title"],
        "cells": len(new),
        "continuous_axes": list(new_grid.continuous_axes),
        "choice_axes": list(new_grid.choice_axes),
        "layers": [layer_label(k) for k in new.layer_keys()],
        "plateau_threshold": new.plateau_threshold,
        "old": {
            "summary": old.summary(),
            "neighbours_per_cell": len(old.cells[0].neighbours),
            "counts": {v: len(old._by(v)) for v in (PLATEAU, RIDGE, LONELY_PEAK)},
        },
        "new": {
            "summary": new.summary(),
            "counts": {v: len(new._by(v)) for v in (PLATEAU, RIDGE, LONELY_PEAK)},
        },
        "changed_cells": len(changed),
        "ridges": [
            {
                "params": c.point.label,
                "layer": c.layer_name,
                "value": c.value,
                "neighbourhood_mean": c.neighbourhood_mean,
                "weakest_sibling_mean": c.weakest_sibling_mean,
                "layer_drop": c.layer_drop,
                "old_verdict": filed[tuple(c.point.get(n) for n in names)],
            }
            for c in sorted(new.ridges, key=lambda c: c.value or 0.0, reverse=True)
        ],
        "best": {
            "params": new.best.point.label,
            "value": new.best.value,
            "old_verdict": filed[tuple(new.best.point.get(n) for n in names)],
            "new_verdict": new.best.verdict,
            "old_neighbourhood_mean": old.best.neighbourhood_mean,
            "new_neighbourhood_mean": new.best.neighbourhood_mean,
        },
        "charts": charts,
        "files": [
            "判讀表-軸型.csv",
            "新舊裁決對照表.csv",
            "分層判讀.csv",
        ],
    }

    print(f"\n【{spec['title']}】{new_grid.describe()}")
    print(f"  舊口徑:{old.summary()}(每格鄰域 {len(old.cells[0].neighbours)} 個)")
    print(f"  新口徑:{new.summary()}")
    print(f"  高地門檻 {new.plateau_threshold:.6f};裁決有變的格 {len(changed)} 個")
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(
            table.head(10)[
                [*names, OBJECTIVE, "舊裁決", "新裁決", "舊鄰域平均", "新鄰域平均", "換層代價"]
            ].to_string(index=False)
        )
    print("  分層判讀:")
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(new.layer_frame()[["層", "格數", PLATEAU, RIDGE, LONELY_PEAK, "高地格數", "最優", "層平均"]].to_string(index=False))
    return summary


def main() -> None:
    out_root = HERE / "results"
    out_root.mkdir(parents=True, exist_ok=True)
    print(
        "重判(不重跑):讀 KARST-043 的 60 格掃描表,"
        f"門檻與當日一樣(成交 ≥ {MIN_TRADES}、孤峰 {MARGIN}、分位 {QUANTILE})"
    )
    summary = {
        "ticket": "KARST-047",
        "source": str(SOURCE.relative_to(REPO)).replace("\\", "/"),
        "snapshot_id": SNAPSHOT,
        "period": list(PERIOD),
        "costs": COST_LABEL,
        "objective": OBJECTIVE,
        "thresholds": {
            "min_trades": MIN_TRADES,
            "lonely_peak_margin": MARGIN,
            "plateau_quantile": QUANTILE,
        },
        "drivers": {},
    }
    for driver_key, spec in DRIVERS.items():
        summary["drivers"][driver_key] = rejudge(driver_key, spec, out_root)
    (out_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n落檔:{out_root}")


if __name__ == "__main__":
    main()
