"""KARST-060:把「山脊」計數補回 KARST-036 那份 ``results/summary.json``。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-28-factor-rotation-drivers/backfill_ridge_counts.py

為什麼要補:``run_rotation_sweep.py`` 逐個驅動器報的裁決分佈當日只寫了平原、孤峰、
無效三項,漏了 KARST-047 新增的**山脊**。少一欄不等於「零格」——README 那張判讀表
因此有一欄長期填「填不到」,而各驅動器目錄下那份 ``判讀表.csv`` 裝的是**最大回撤**
那一軸,答不到年化超額軸上有幾多格判山脊。

**一次引擎都不動**:山脊格數由當日落檔的 ``掃描表.csv`` 逐格重判出來(與重判腳本
同一個做法,KARST-047、048),門檻與軸型全部照 ``summary.json`` 那一份,一個字不改。

**自檢是這一支的重點**:重判出來的平原 / 孤峰 / 無效三項,要與 ``summary.json``
本來就有的那三個數逐個對得上,才准把山脊那一欄寫回去。對不上即代表這一次重判與
當日那一次不是同一個口徑,寧可停手,也不可以塞一個來歷不明的數入落檔。

產生程式那邊(``run_rotation_sweep.py``)同時已經補上這一欄,所以下次重跑會直接
帶住山脊,不用再走這一支。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:  # 未裝套件也跑得動(倉根就在上兩層)
    sys.path.insert(0, str(REPO))

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

import pandas as pd  # noqa: E402

from karst.strategies.factor_rotation import DRIVER_PARAMETERS  # noqa: E402
from karst.sweep import CADENCE_AXIS, CellScore, judge  # noqa: E402
from karst.sweep.factor_rotation import rotation_grid  # noqa: E402

# 目標指標的名 → 掃描表上那一欄。判讀那一層只認「越大越好」,欄名的對法住在這裡。
OBJECTIVE_COLUMNS = {
    "annual_excess:SPY": "annual_excess_SPY",
    "max_drawdown": "max_drawdown",
}


def _plain(value):
    """由 CSV 讀回來的 ``numpy.int64`` 一類還原做 Python 型別。

    不還原一樣掃得出格,但軸的次序、標籤與查表都會靜靜地走樣(numpy 的整數不是
    Python ``int`` 的子類)。
    """
    return value.item() if hasattr(value, "item") else value


def _axis_values(frame: pd.DataFrame, name: str) -> list:
    """一條軸在掃描表上出現過的取值,數字軸按大細排,其餘按首次出現。

    取值由**當日那張掃描表**讀回來,不在本檔另抄一份 KARST-036 的取值清單——手抄
    的清單遲早會與落檔不一致,而一旦不一致,重判就會靜靜地判了另一個格。
    """
    seen: list = []
    for value in frame[name]:
        value = _plain(value)
        if value not in seen:
            seen.append(value)
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in seen):
        return sorted(seen)
    return seen


def _judge_axis(frame: pd.DataFrame, grid, objective: str, thresholds: dict):
    column = OBJECTIVE_COLUMNS[objective]
    names = list(grid.axis_names)
    table = {
        tuple(_plain(row[name]) for name in names): (float(row[column]), int(row["trades"]))
        for _, row in frame.iterrows()
    }
    scores = []
    for point in grid.points():
        key = tuple(point.get(name) for name in names)
        if key not in table:
            raise SystemExit(f"掃描表沒有這一格:{point.label}")
        value, trades = table[key]
        scores.append(CellScore(point=point, value=value, trades=trades))
    return judge(
        scores,
        grid,
        objective=objective,
        min_trades=thresholds["min_trades"],
        lonely_peak_margin=thresholds["lonely_peak_margin"],
        plateau_quantile=thresholds["plateau_quantile"],
    )


def _with_ridge(counts: dict, judgement, where: str) -> dict:
    """把山脊那一欄插回原有次序(平原 → 山脊 → 孤峰 → 無效),先驗其餘三欄。

    三欄之中有一欄對不上,即代表這一次重判與當日那一次不是同一個口徑。
    """
    recomputed = {
        "plateau": len(judgement.plateaus),
        "lonely_peak": len(judgement.lonely_peaks),
        "invalid": len(judgement.invalid_cells),
    }
    for key, value in recomputed.items():
        if int(counts[key]) != value:
            raise SystemExit(
                f"{where}:重判出來的「{key}」是 {value},落檔那份寫住 {counts[key]}"
                "——口徑對不上,不補這一欄"
            )
    return {
        "plateau": counts["plateau"],
        "ridge": len(judgement.ridges),
        "lonely_peak": counts["lonely_peak"],
        "invalid": counts["invalid"],
    }


def main() -> None:
    path = RESULTS / "summary.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    thresholds = summary["thresholds"]
    objective = summary["objective"]
    cadences = list(summary["cadences"])

    print(
        f"補山脊計數(不重跑引擎):讀 {len(summary['drivers'])} 份掃描表,"
        f"門檻與當日一樣(成交 ≥ {thresholds['min_trades']}、"
        f"孤峰 {thresholds['lonely_peak_margin']}、分位 {thresholds['plateau_quantile']})"
    )

    for driver_key, item in summary["drivers"].items():
        frame = pd.read_csv(RESULTS / driver_key / "掃描表.csv")
        if len(frame) != item["cells"]:
            raise SystemExit(
                f"{driver_key} 的掃描表是 {len(frame)} 格,落檔寫住 {item['cells']} 格"
            )
        grid = rotation_grid(
            driver_key,
            values={name: _axis_values(frame, name) for name in DRIVER_PARAMETERS[driver_key]},
            cadences=_axis_values(frame, CADENCE_AXIS) or cadences,
        )
        main_axis = _judge_axis(frame, grid, objective, thresholds)
        drawdown_axis = _judge_axis(frame, grid, "max_drawdown", thresholds)

        item["counts"] = _with_ridge(item["counts"], main_axis, f"{driver_key}·{objective}")
        item["max_drawdown_axis"]["counts"] = _with_ridge(
            item["max_drawdown_axis"]["counts"], drawdown_axis, f"{driver_key}·max_drawdown"
        )
        print(
            f"  {item['title']}:{objective} 山脊 {item['counts']['ridge']} 格"
            f"(平原 {item['counts']['plateau']}、孤峰 {item['counts']['lonely_peak']});"
            f"最大回撤軸 山脊 {item['max_drawdown_axis']['counts']['ridge']} 格"
        )

    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n落檔:{path}")


if __name__ == "__main__":
    main()
