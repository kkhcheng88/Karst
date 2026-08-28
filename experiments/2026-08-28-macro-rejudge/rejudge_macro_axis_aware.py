"""KARST-048:KARST-040 六個宏觀驅動器 180 格**重判**一次(不重跑運行)。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-28-macro-rejudge/rejudge_macro_axis_aware.py

KARST-040 那次掃描,鄰域把三條軸一視同仁——門檻(或者回望期)推一格、押注比重
推一格,與「月度改成季度」,同樣算「一步之遙」。前兩者是連續刻度上的微調,後者
是換一套做法。混在同一個鄰域平均裡,一條真山脊會被判成孤峰:一格的七個鄰居之中
有三四個根本是另一個節奏的成績。

本檔**一次引擎都不動**:只讀 KARST-040 落下的六份掃描表(每個驅動器 30 格,合共
180 格),用兩套鄰域各判一次——

* **舊口徑**:三條軸全部當連續(即 KARST-040 當日那個格,經
  ``karst.sweep.grid.all_continuous`` 由今日的格還原出來)。留住它是為了看得到兩套
  鄰域判出來的分別。
* **新口徑**:門檻 / 回望日數與押注比重做連續軸,換倉節奏做選擇軸(KARST-048 之後
  ``rotation_grid`` 自己就是這樣宣告的,所以這裡直接用生產路徑那個格,不另砌一個)。
  鄰域只沿兩條連續軸取,節奏切出月度、季度兩層,每層各出一份判讀,並判得出**山脊**。
  **新口徑判出來的結果要與來源目錄落檔的判讀表逐格對得上**——這是本檔的自檢,
  不是裝飾:它守住「重判腳本與生產掃描路徑判得出同一批裁決」,180 格全對才繼續。

  自檢本來對的是舊口徑那一臂,因為本檔最初寫成時,來源那張判讀表裝住的是 KARST-040
  當日節奏當連續軸的裁決。KARST-048 令生產掃描路徑自己宣告軸型,來源腳本重跑一次
  就會用新口徑覆寫那張表;數據目錄重建(KARST-057)正正重跑過,所以對得上的一方
  換了邊(實測:新口徑六個驅動器全部 0/30 格不同,舊口徑 1、4、5、1、3、2 格不同)。

落檔:逐驅動器一份新判讀表、一份新舊裁決對照表、一份分層判讀表,加投影圖(舊判
與新判逐層各一張,看得到裁決標記由三角變成等號);另有一份六個驅動器的總表。

**本檔不裁定哪一個驅動器該用**(D-008),亦不改任何既有結果檔——KARST-040 的
``results/`` 只讀不寫。門檻一個字不改(由 KARST-040 的 ``summary.json`` 讀回),
所以每一格裁決有變都只可能來自軸型。
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

from karst.strategies.factor_rotation import DRIVER_PARAMETERS  # noqa: E402
from karst.sweep import (  # noqa: E402
    CADENCE_AXIS,
    LONELY_PEAK,
    ORDINARY,
    PLATEAU,
    RIDGE,
    CellScore,
    all_continuous,
    draw_heatmap,
    draw_layer_projections,
    judge,
    layer_label,
)
from karst.sweep.factor_rotation import rotation_grid  # noqa: E402

# KARST-040 的落檔。**只讀**。
SOURCE = REPO / "experiments" / "2026-08-28-macro-drivers" / "results"

OBJECTIVE_COLUMN = "annual_excess_SPY"

DRIVER_TITLES = {
    "vix_level": "VIX 水平開關",
    "vix_term": "VIX 期限結構開關",
    "credit_trend": "信用利差變化方向",
    "curve_trend": "曲線斜度變化方向",
    "rate_trend": "10 年息率趨勢",
    "fed_expectation": "聯邦基金利率預期方向",
}

CELLS_PER_DRIVER = 30


def _plain(value):
    """由 CSV 讀回來的 ``numpy.int64`` 一類還原做 Python 型別。

    不還原一樣掃得出格,但軸的次序、標籤與查表都會靜靜地走樣(numpy 的整數不是
    Python ``int`` 的子類)。
    """
    return value.item() if hasattr(value, "item") else value


def _axis_values(frame: pd.DataFrame, name: str) -> list:
    """一條軸在掃描表上出現過的取值,數字軸按大細排,其餘按首次出現。

    取值由**當日那張掃描表**讀回來,不在本檔另抄一份 KARST-040 的取值清單——
    手抄的清單遲早會與落檔不一致,而一旦不一致,重判就會靜靜地判了另一個格。
    """
    seen: list = []
    for value in frame[name]:
        value = _plain(value)
        if value not in seen:
            seen.append(value)
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in seen):
        return sorted(seen)
    return seen


def scores_from(frame: pd.DataFrame, grid) -> list[CellScore]:
    """掃描表逐行變成一格成績。目標指標就是 KARST-040 用的對 SPY 年化超額。"""
    names = list(grid.axis_names)
    table = {}
    for _, row in frame.iterrows():
        key = tuple(_plain(row[name]) for name in names)
        table[key] = (float(row[OBJECTIVE_COLUMN]), int(row["trades"]))
    out: list[CellScore] = []
    for point in grid.points():
        key = tuple(point.get(name) for name in names)
        if key not in table:
            raise SystemExit(f"掃描表沒有這一格:{point.label}")
        value, trades = table[key]
        out.append(CellScore(point=point, value=value, trades=trades))
    return out


def rejudge(
    driver_key: str,
    thresholds: dict,
    objective: str,
    subtitle: str,
    out_root: Path,
) -> dict:
    title = DRIVER_TITLES[driver_key]
    source = SOURCE / driver_key
    frame = pd.read_csv(source / "掃描表.csv")
    old_frame = pd.read_csv(source / "判讀表.csv")
    if len(frame) != CELLS_PER_DRIVER:
        raise SystemExit(
            f"{driver_key} 的掃描表不是 {CELLS_PER_DRIVER} 格,是 {len(frame)} 格"
        )

    # --- 新口徑:生產路徑那個格(節奏是選擇軸,KARST-048)---------------------
    params = DRIVER_PARAMETERS[driver_key]
    new_grid = rotation_grid(
        driver_key,
        values={name: _axis_values(frame, name) for name in params},
        cadences=_axis_values(frame, CADENCE_AXIS),
    )
    # --- 舊口徑:同一個格,軸型全部還原做連續(即 KARST-040 當日那一個)------
    old_grid = all_continuous(new_grid)

    def _judge(grid):
        return judge(
            scores_from(frame, grid),
            grid,
            objective=objective,
            min_trades=thresholds["min_trades"],
            lonely_peak_margin=thresholds["lonely_peak_margin"],
            plateau_quantile=thresholds["plateau_quantile"],
        )

    old = _judge(old_grid)
    new = _judge(new_grid)

    # 自檢:重判出來的裁決要與來源目錄落檔的判讀表逐格對得上。
    #
    # 這道閘本來對的是**舊口徑**——本檔最初寫成時,來源那張判讀表是 KARST-040 當日
    # 落檔的,裡面裝住節奏當連續軸判出來的裁決。KARST-048 之後,生產掃描路徑自己
    # 宣告軸型,來源腳本重跑一次就會用**新口徑**覆寫那張判讀表;數據目錄重建
    # (KARST-057)正正重跑過,所以現時落檔那張表裝住的是新口徑的裁決。
    #
    # 於是對得上的一方換了邊:實測六個驅動器,新口徑全部 0/30 格不同,舊口徑分別
    # 1、4、5、1、3、2 格不同。閘照樣要有——它守的是「重判腳本與生產掃描路徑判得出
    # 同一批裁決」,只是現在要對新口徑。舊口徑那一臂留住做歷史對照,但已經沒有落檔
    # 的表可以核對它。
    names = list(old_grid.axis_names)
    filed = {
        tuple(_plain(row[name]) for name in names): str(row["verdict"])
        for _, row in old_frame.iterrows()
    }
    mismatched = [
        cell.point.label
        for cell in new.cells
        if filed.get(tuple(cell.point.get(n) for n in names)) != cell.verdict
    ]
    if mismatched:
        raise SystemExit(
            f"{driver_key}:軸型重判與來源目錄落檔的判讀表對不上,"
            f"{len(mismatched)} 格不同(例:{mismatched[0]});"
            "重判腳本與生產掃描路徑應該判得出同一批裁決"
        )

    out = out_root / driver_key
    out.mkdir(parents=True, exist_ok=True)
    new.frame().to_csv(out / "判讀表-軸型.csv", index=False, encoding="utf-8-sig")
    new.layer_frame().to_csv(out / "分層判讀.csv", index=False, encoding="utf-8-sig")

    # --- 新舊裁決對照表(30 行) --------------------------------------------
    spine = params[0]  # 門檻 或者 回望日數
    rows = []
    for cell in new.cells:
        before = old.cell_for(cell.point)
        rows.append(
            {
                **cell.point.as_dict(),
                "層": cell.layer_name,
                objective: cell.value,
                # 舊裁決取**舊口徑重判**出來那一個,不是落檔判讀表那一欄。
                # 兩者本來一樣(當日那張表就是舊口徑判的),KARST-048 之後生產掃描
                # 路徑改判新口徑,來源腳本一重跑就會覆寫那張表;再讀 filed 的話,
                # 這一欄會變成新裁決自己,整張對照表就永遠報「沒有變」。
                "舊裁決": before.verdict,
                "新裁決": cell.verdict,
                "變了": "是" if before.verdict != cell.verdict else "",
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
    table = pd.DataFrame(rows).sort_values(objective, ascending=False)
    table.to_csv(out / "新舊裁決對照表.csv", index=False, encoding="utf-8-sig")

    # --- 投影圖:舊判整個格一張,新判逐層各一張 -----------------------------
    charts: list[str] = []
    for cadence in _axis_values(frame, CADENCE_AXIS):
        path = out / f"舊判-{cadence}-{spine}×tilt.png"
        draw_heatmap(
            old.where(cadence=cadence),
            path,
            x_axis=spine,
            y_axis="tilt",
            title=f"{title}·舊判({cadence})",
            subtitle=subtitle,
        )
        charts.append(path.name)
    layer_charts = draw_layer_projections(
        new,
        out,
        title=f"{title}·新判",
        subtitle=subtitle,
        prefix="新判",
    )
    for paths in layer_charts.values():
        charts.extend(path.name for path in paths)

    changed = table[table["變了"] == "是"]

    def _counts(judgement):
        tally = {v: 0 for v in (PLATEAU, RIDGE, LONELY_PEAK, ORDINARY)}
        for cell in judgement.cells:
            if cell.verdict in tally:
                tally[cell.verdict] += 1
        return tally

    summary = {
        "driver": driver_key,
        "title": title,
        "cells": len(new),
        "continuous_axes": list(new_grid.continuous_axes),
        "choice_axes": list(new_grid.choice_axes),
        "layers": [layer_label(k) for k in new.layer_keys()],
        "plateau_threshold": new.plateau_threshold,
        "old": {
            "summary": old.summary(),
            "neighbours_per_cell_max": max(len(c.neighbours) for c in old.cells),
            "counts": _counts(old),
        },
        "new": {
            "summary": new.summary(),
            "neighbours_per_cell_max": max(len(c.neighbours) for c in new.cells),
            "counts": _counts(new),
        },
        "changed_cells": len(changed),
        "changes": [
            {
                spine: _plain(row[spine]),
                "tilt": _plain(row["tilt"]),
                "layer": row["層"],
                "value": float(row[objective]),
                "old": row["舊裁決"],
                "new": row["新裁決"],
            }
            for _, row in changed.iterrows()
        ],
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
        "plateaus": [
            {
                "params": c.point.label,
                "layer": c.layer_name,
                "value": c.value,
                "neighbourhood_mean": c.neighbourhood_mean,
                "old_verdict": filed[tuple(c.point.get(n) for n in names)],
            }
            for c in sorted(new.plateaus, key=lambda c: c.value or 0.0, reverse=True)
        ],
        "best": {
            "params": new.best.point.label,
            "layer": new.best.layer_name,
            "value": new.best.value,
            "old_verdict": filed[tuple(new.best.point.get(n) for n in names)],
            "new_verdict": new.best.verdict,
            "old_neighbourhood_mean": old.best.neighbourhood_mean,
            "new_neighbourhood_mean": new.best.neighbourhood_mean,
            "layer_drop": new.best.layer_drop,
        },
        "layer_table": json.loads(new.layer_frame().to_json(orient="records")),
        "charts": charts,
        "files": ["判讀表-軸型.csv", "新舊裁決對照表.csv", "分層判讀.csv"],
    }

    print(f"\n【{title}】{new_grid.describe()}")
    print(
        f"  舊口徑:{old.summary()}"
        f"(每格鄰域最多 {summary['old']['neighbours_per_cell_max']} 個)"
    )
    print(
        f"  新口徑:{new.summary()}"
        f"(每格鄰域最多 {summary['new']['neighbours_per_cell_max']} 個)"
    )
    print(f"  高地門檻 {new.plateau_threshold:+.6f};裁決有變的格 {len(changed)} 個")
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(
            table.head(6)[
                [*names, objective, "舊裁決", "新裁決", "舊鄰域平均", "新鄰域平均", "換層代價"]
            ].to_string(index=False)
        )
        print("  分層判讀:")
        print(
            new.layer_frame()[
                ["層", "格數", PLATEAU, RIDGE, LONELY_PEAK, "高地格數", "最優", "層平均"]
            ].to_string(index=False)
        )
    return summary


def main() -> None:
    # 來歷與門檻一律由 KARST-040 的 summary.json 讀回,不在本檔另抄一份:抄漏一個
    # 數,「裁決有變只可能來自軸型」那句話就不成立。
    filed = json.loads((SOURCE / "summary.json").read_text(encoding="utf-8"))
    thresholds = filed["thresholds"]
    objective = filed["objective"]
    period = (filed["period"][0], filed["period"][1])
    costs_label = filed["costs_label"]
    subtitle = f"{objective}|{period[0]} ~ {period[1]}|{costs_label}"
    drivers = list(filed["drivers"])

    out_root = HERE / "results"
    out_root.mkdir(parents=True, exist_ok=True)
    print(
        f"重判(不重跑):讀 KARST-040 的 {len(drivers)} 份掃描表"
        f"(每份 {CELLS_PER_DRIVER} 格,合共 {len(drivers) * CELLS_PER_DRIVER} 格),"
        f"門檻與當日一樣(成交 ≥ {thresholds['min_trades']}、"
        f"孤峰 {thresholds['lonely_peak_margin']}、分位 {thresholds['plateau_quantile']})"
    )

    summary = {
        "ticket": "KARST-048",
        "source": str(SOURCE.relative_to(REPO)).replace("\\", "/"),
        "price_snapshot_id": filed["price_snapshot_id"],
        "macro_snapshot_id": filed["macro_snapshot_id"],
        "period": list(period),
        "costs": costs_label,
        "objective": objective,
        "thresholds": thresholds,
        "drivers": {},
    }
    for driver_key in drivers:
        summary["drivers"][driver_key] = rejudge(
            driver_key, thresholds, objective, subtitle, out_root
        )

    # --- 六個驅動器一張總表 --------------------------------------------------
    rows = []
    for key, item in summary["drivers"].items():
        rows.append(
            {
                "驅動器": item["title"],
                "代號": key,
                "格數": item["cells"],
                "連續軸": "、".join(item["continuous_axes"]),
                "選擇軸": "、".join(item["choice_axes"]),
                "層數": len(item["layers"]),
                f"舊{PLATEAU}": item["old"]["counts"][PLATEAU],
                f"舊{LONELY_PEAK}": item["old"]["counts"][LONELY_PEAK],
                f"新{PLATEAU}": item["new"]["counts"][PLATEAU],
                f"新{RIDGE}": item["new"]["counts"][RIDGE],
                f"新{LONELY_PEAK}": item["new"]["counts"][LONELY_PEAK],
                "改判格數": item["changed_cells"],
                "最優格": item["best"]["params"],
                "最優格年化超額": item["best"]["value"],
                "最優格舊裁決": item["best"]["old_verdict"],
                "最優格新裁決": item["best"]["new_verdict"],
                "最優格舊鄰域平均": item["best"]["old_neighbourhood_mean"],
                "最優格新鄰域平均": item["best"]["new_neighbourhood_mean"],
                "高地門檻": item["plateau_threshold"],
            }
        )
    overall = pd.DataFrame(rows)
    overall.to_csv(out_root / "六驅動器新舊裁決總表.csv", index=False, encoding="utf-8-sig")
    summary["overall"] = json.loads(overall.to_json(orient="records"))

    (out_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with pd.option_context("display.width", 260, "display.max_columns", 40):
        print("\n=== 六個驅動器:新舊裁決總表 ===")
        print(
            overall[
                [
                    "驅動器",
                    f"舊{PLATEAU}",
                    f"舊{LONELY_PEAK}",
                    f"新{PLATEAU}",
                    f"新{RIDGE}",
                    f"新{LONELY_PEAK}",
                    "改判格數",
                    "最優格",
                    "最優格年化超額",
                    "最優格舊裁決",
                    "最優格新裁決",
                ]
            ].to_string(index=False)
        )
    print(f"\n落檔:{out_root}")


if __name__ == "__main__":
    main()
