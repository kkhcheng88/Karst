"""KARST-051 參數掃描頁的薄 REST 層。

本檔是參數掃描頁**全部**端點的所在,不碰其他頁的路由。與 ``karst.web.data``
一樣:**只讀不寫**,而且不重跑引擎——畫面上每一個數,都是掃描落檔那一刻寫低
的那個數。

為什麼讀目錄而不是讀庫
----------------------
掃描本身現時**未入庫**:``karst/sweep/runner.py`` 只把逐格的**運行**經
``RunStore`` 落痕(所以掃描表每一列的 ``run_id`` 都在庫內查得到),掃描格與
判讀表則只由 ``karst/sweep/report.py`` 寫成 CSV 落在 ``experiments/`` 之下。
庫裡沒有 sweep 表,亦沒有「列出掃描」的 API。所以本頁以**掃描落檔目錄**為
來源;等掃描入庫那一票落地,只需換掉本檔的 ``discover_sweeps``,頁面與端點
形狀不變。(KARST-051 票上已註明)

一次掃描 = 一對表
-----------------
* ``掃描表.csv``——逐格的成績(參數軸 + 指標 + run_id)。
* ``判讀表.csv`` / ``判讀表-軸型.csv``——逐格的裁決(平原/山脊/孤峰/普通/
  無效/無鄰)與鄰域統計。

KARST-047 的軸型重判把新判讀寫在**另一個實驗目錄**,並在該目錄的
``summary.json`` 以 ``source`` 指回掃描表所在。所以同一個掃描表可能有兩份
判讀:一份舊口徑(全部軸當連續)、一份軸型口徑。**有軸型口徑就用軸型口徑**,
因為只有它分得出層與山脊。
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Callable

import pandas as pd

# 用庫本身的錯誤型別,不用 server.WebError——否則本檔與 server.py 互相 import。
# server.do_GET 已經把 NotFound 映成 404、ContractViolation 映成 400。
from karst.errors import ContractViolation, NotFound

# ---------------- 落檔上的檔名(karst/sweep/report.py 與兩個重判腳本的正本) ----------------

# 本頁的靜態路由:server.py 只需 PAGE_FILES.update(api_sweep.PAGES)
PAGES: dict[str, str] = {"/sweep": "sweep.html"}

GRID_FILENAME = "掃描表.csv"
VERDICT_FILENAMES = ("判讀表-軸型.csv", "判讀表.csv")   # 有軸型口徑就先用軸型口徑
LAYER_FILENAMES = ("分層判讀.csv", "分層判讀表.csv")     # 兩個名字倉內都有,同一個 schema
SUMMARY_FILENAME = "summary.json"
EXPERIMENTS_DIRNAME = "experiments"

# ---------------- 掃描表的欄位分類(karst/sweep/runner.py 的 METRIC_COLUMNS / TRACE_COLUMNS) ----------------

METRIC_COLUMNS = (
    "total_return",
    "annual_return",
    "max_drawdown",
    "win_rate",
    "profit_loss_ratio",
    "sortino",
    "average_holding_days",
    "turnover",
)
TRACE_COLUMNS = (
    "run_id",
    "trades",
    "closed_trades",
    "trading_days",
    "start",
    "end",
    "reused",
    "seconds",
)
EXCESS_PREFIX = "annual_excess_"

# 判讀表的非參數欄(karst/sweep/verdict.py 的 CellVerdict.as_row())
VERDICT_COLUMNS = (
    "value",
    "trades",
    "verdict",
    "neighbours",
    "valid_neighbours",
    "neighbourhood_mean",
    "neighbour_mean",
    "lift",
    "peak_over_neighbourhood",
    "is_local_peak",
    "layer",
    "siblings",
    "weakest_sibling_mean",
    "layer_drop",
)

# ---------------- 軸型與裁決(karst/sweep/grid.py、verdict.py 的正本字串) ----------------

CONTINUOUS = "連續"
CHOICE = "選擇"
NO_CHOICE_LAYER = "全格(沒有選擇軸)"
VERDICTS = ("平原", "山脊", "孤峰", "普通", "無效", "無鄰")
INVALID = "無效"

# ---------------- 顯示單位 ----------------
# 「百分比」那幾格落檔是小數(0.1269 = 12.69%),同 karst/web/data.py 一樣在這一層
# 乘 100 交出去;頁面只負責印,不做換算亦不算指標。

PCT_METRICS = frozenset(
    {"total_return", "annual_return", "max_drawdown", "win_rate", "turnover"}
)
METRIC_LABELS = {
    "total_return": ("總回報", "pct"),
    "annual_return": ("年化回報", "pct"),
    "max_drawdown": ("最大回撤", "pct"),
    "win_rate": ("勝率", "pct"),
    "profit_loss_ratio": ("盈虧比", "num"),
    "sortino": ("Sortino", "num"),
    "average_holding_days": ("平均持倉日數", "days"),
    "turnover": ("換手率", "pct"),
}
# 參數組詳情照設計系統 3.13 定死這四行,不隨掃描而變
DETAIL_METRICS = ("annual_return", "max_drawdown", "sortino")

OBJECTIVE_LABELS = {
    "annual_return": "年化回報",
    "total_return": "總回報",
    "max_drawdown": "最大回撤",
    "sortino": "Sortino",
}


def objective_label(objective: str | None) -> str:
    """判讀的目標指標印成人話。``annual_excess:SPY`` → 「對 SPY 超額年化」。"""
    if not objective:
        return "判讀目標"
    if objective.startswith("annual_excess:"):
        return f"對 {objective.split(':', 1)[1]} 超額年化"
    return OBJECTIVE_LABELS.get(objective, objective)


def objective_unit(objective: str | None) -> str:
    if not objective:
        return "num"
    if objective.startswith("annual_excess:"):
        return "pct"
    if objective in PCT_METRICS:
        return "pct"
    return "num"


# ============================================================
# 小工具
# ============================================================


def _clean(value: Any) -> Any:
    """NaN / NaT / numpy 標量 → JSON 出得到的東西。

    server.py 以 ``allow_nan=False`` 序列化,一個 NaN 漏出去整個回應就爆,
    所以出門前逐格洗一次。
    """
    if value is None:
        return None
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, (bool, int, str)):
        return value
    if pd.isna(value):
        return None
    item = getattr(value, "item", None)
    if callable(item):
        return _clean(item())
    return str(value)


def _scaled(value: Any, unit: str) -> Any:
    """百分比那一族落檔是小數,交出去之前乘 100(同 data.py 的做法)。"""
    cleaned = _clean(value)
    if cleaned is None or unit != "pct":
        return cleaned
    return float(cleaned) * 100.0


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _axis_values(series: pd.Series) -> tuple[list[Any], bool]:
    """一條軸在表上出現過的取值。

    數字軸按大細排(鄰格才會真的相鄰),其餘按首次出現的次序——同
    ``experiments/2026-08-28-axis-aware-verdict/rejudge_axis_aware.py`` 的做法。
    """
    seen: list[Any] = []
    for raw in series.tolist():
        if raw not in seen:
            seen.append(raw)
    numeric = all(_is_number(v) for v in seen) and bool(seen)
    if numeric:
        seen = sorted(seen, key=float)
        seen = [float(v) for v in seen]
    else:
        seen = [_clean(v) for v in seen]
    return seen, numeric


def _cell_key(row: Any, axes: list[str]) -> tuple:
    """兩張表對行用的鍵。數字統一成 float,免得 ``1`` 與 ``1.0`` 對不上。"""
    parts = []
    for name in axes:
        raw = row[name]
        parts.append(float(raw) if _is_number(raw) else str(raw).strip())
    return tuple(parts)


def _param_value(raw: Any) -> Any:
    return float(raw) if _is_number(raw) else _clean(raw)


def _layer_name(params: dict[str, Any], choice_axes: list[str]) -> str:
    """沒有 ``layer`` 欄時,照 grid.layer_label() 同一個格式砌一個出來。"""
    if not choice_axes:
        return NO_CHOICE_LAYER
    return "、".join(f"{name}={_format_value(params[name])}" for name in choice_axes)


def _format_value(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _read_csv(path: Path) -> pd.DataFrame:
    # report.py 一律 utf-8-sig 落檔(有 BOM),讀回要對得上
    return pd.read_csv(path, encoding="utf-8-sig")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# ============================================================
# 找掃描:行檔案系統,因為庫裡沒有 sweep 表
# ============================================================


class SweepSource:
    """一次掃描的來源:一張掃描表,配一張判讀表(可能在另一個目錄)。"""

    def __init__(
        self,
        *,
        root: Path,
        grid_path: Path,
        verdict_path: Path,
        layer_path: Path | None,
        summary_path: Path | None,
    ) -> None:
        self.root = root
        self.grid_path = grid_path
        self.verdict_path = verdict_path
        self.layer_path = layer_path
        self.summary_path = summary_path

    @property
    def id(self) -> str:
        return self.grid_path.parent.relative_to(self.root).as_posix()

    @property
    def label(self) -> str:
        return self.grid_path.parent.name

    @property
    def experiment(self) -> str:
        rel = self.grid_path.parent.relative_to(self.root).parts
        # experiments/<實驗>/... → 取實驗那一格
        return rel[1] if len(rel) > 1 else rel[0]

    @property
    def axis_aware(self) -> bool:
        return self.verdict_path.name == VERDICT_FILENAMES[0]

    def signature(self) -> tuple:
        paths = [self.grid_path, self.verdict_path, self.layer_path, self.summary_path]
        return tuple(
            (str(p), p.stat().st_mtime_ns if p and p.is_file() else 0) for p in paths if p
        )


def _first_existing(directory: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def discover_sweeps(root: Path) -> list[SweepSource]:
    """掃 ``experiments/`` 找掃描落檔,順帶把軸型重判接回它的掃描表。"""
    experiments = root / EXPERIMENTS_DIRNAME
    if not experiments.is_dir():
        return []

    # 1) 逐個掃描表目錄
    grids: dict[Path, Path] = {}
    for grid_path in sorted(experiments.rglob(GRID_FILENAME)):
        grids[grid_path.parent] = grid_path

    # 2) 軸型重判:住在別的目錄,靠自己的 summary.json 的 source 指回來
    rejudged: dict[Path, tuple[Path, Path | None]] = {}
    for summary_path in sorted(experiments.rglob(SUMMARY_FILENAME)):
        source = _read_json(summary_path).get("source")
        if not isinstance(source, str) or not source.strip():
            continue
        source_dir = (root / source.strip()).resolve()
        for child in sorted(summary_path.parent.iterdir()):
            if not child.is_dir():
                continue
            verdict_path = child / VERDICT_FILENAMES[0]
            if not verdict_path.is_file():
                continue
            target = source_dir / child.name
            if target in grids:
                rejudged[target] = (verdict_path, _first_existing(child, LAYER_FILENAMES))

    sweeps: list[SweepSource] = []
    for directory, grid_path in grids.items():
        verdict_path, layer_path = rejudged.get(directory, (None, None))
        if verdict_path is None:
            verdict_path = _first_existing(directory, VERDICT_FILENAMES)
            layer_path = _first_existing(directory, LAYER_FILENAMES)
        if verdict_path is None:
            continue  # 有成績無判讀:畫不出裁決,不上架
        summary_path = _first_existing(directory, (SUMMARY_FILENAME,)) or _first_existing(
            directory.parent, (SUMMARY_FILENAME,)
        )
        sweeps.append(
            SweepSource(
                root=root,
                grid_path=grid_path,
                verdict_path=verdict_path,
                layer_path=layer_path,
                summary_path=summary_path,
            )
        )

    sweeps.sort(key=lambda s: (s.experiment, s.label))
    return sweeps


# ============================================================
# 讀一次掃描,整理成頁面要的形狀
# ============================================================


class SweepView:
    """一次掃描讀出來、整理成頁面要的形狀。"""

    def __init__(self, source: SweepSource) -> None:
        self.source = source
        grid = _read_csv(source.grid_path)
        verdict = _read_csv(source.verdict_path)

        known = set(METRIC_COLUMNS) | set(TRACE_COLUMNS)
        self.axes: list[str] = [
            c for c in grid.columns if c not in known and not c.startswith(EXCESS_PREFIX)
        ]
        if not self.axes:
            raise ContractViolation(f"{source.grid_path.name} 找不到任何參數軸欄")
        self.excess_columns = [c for c in grid.columns if c.startswith(EXCESS_PREFIX)]

        self.summary = _read_json(source.summary_path) if source.summary_path else {}

        # 判讀表逐格的 value 是「判讀當時盯住的那個指標」。summary.json 自報的
        # objective 靠不住——同一個實驗跑過兩次判讀(例如超額一次、最大回撤一次)
        # 而兩次都寫同一個 判讀表.csv 時,留在檔上的是後跑那次,summary 卻仍然
        # 寫住前一次。所以逐欄對回掃描表,認出 value 到底是哪一欄。
        self.judged = {
            _cell_key(row, self.axes): row for _, row in verdict.iterrows()
        }
        self.objective = self._detect_objective(grid) or self._objective_from_summary()
        self.unit = objective_unit(self.objective)

        # 軸型:判讀表有 layer 欄就照它宣告的來;沒有就按取值形態推斷
        self.declared = "layer" in verdict.columns
        self.axis_values: dict[str, list[Any]] = {}
        self.axis_numeric: dict[str, bool] = {}
        for name in self.axes:
            values, numeric = _axis_values(grid[name])
            self.axis_values[name] = values
            self.axis_numeric[name] = numeric

        if self.declared:
            self.choice_axes = self._choice_axes_from_layer(verdict)
        else:
            self.choice_axes = [n for n in self.axes if not self.axis_numeric[n]]
        self.continuous_axes = [n for n in self.axes if n not in self.choice_axes]

        self.cells = self._merge(grid)
        self.layer_rows = self._layer_rows()

    # ---------------- 組裝 ----------------

    def _detect_objective(self, grid: pd.DataFrame) -> str | None:
        """判讀表的 value 對得上掃描表哪一欄,那一欄就是判讀目標。

        兩張表都由同一批 float 寫出,對得上就是一字不差(容差只為食走 CSV
        的最後一兩個位)。對不上任何一欄(例如目標是一條算式)就交白卷,
        由 summary.json 補位。
        """
        candidates = [c for c in METRIC_COLUMNS if c in grid.columns] + self.excess_columns
        if not candidates:
            return None

        pairs: dict[str, list[tuple[float, float]]] = {c: [] for c in candidates}
        for _, row in grid.iterrows():
            judgement = self.judged.get(_cell_key(row, self.axes))
            if judgement is None:
                continue
            judged_value = _clean(judgement.get("value"))
            if judged_value is None:
                continue
            for name in candidates:
                grid_value = _clean(row[name])
                if grid_value is not None:
                    pairs[name].append((float(judged_value), float(grid_value)))

        for name in candidates:
            samples = pairs[name]
            if len(samples) < 2:
                continue
            scale = max(1.0, max(abs(a) for a, _ in samples))
            if max(abs(a - b) for a, b in samples) <= 1e-9 * scale:
                if name.startswith(EXCESS_PREFIX):
                    return "annual_excess:" + name[len(EXCESS_PREFIX) :]
                return name
        return None

    def _objective_from_summary(self) -> str | None:
        objective = self.summary.get("objective")
        if isinstance(objective, str) and objective:
            return objective
        drivers = self.summary.get("drivers")
        if isinstance(drivers, dict):
            for driver in drivers.values():
                if isinstance(driver, dict) and isinstance(driver.get("objective"), str):
                    return driver["objective"]
        return None

    def _choice_axes_from_layer(self, verdict: pd.DataFrame) -> list[str]:
        names: list[str] = []
        for raw in verdict["layer"].tolist():
            text = str(raw or "").strip()
            if not text or text == NO_CHOICE_LAYER:
                continue
            for part in text.split("、"):
                name = part.split("=", 1)[0].strip()
                if name in self.axes and name not in names:
                    names.append(name)
            break
        return [n for n in self.axes if n in names]

    def _merge(self, grid: pd.DataFrame) -> list[dict[str, Any]]:
        """逐格把成績與裁決對起來。對行用參數值,不靠兩表列序相同。"""
        judged = self.judged
        has_layer = self.declared
        cells: list[dict[str, Any]] = []
        for _, row in grid.iterrows():
            key = _cell_key(row, self.axes)
            params = {name: _param_value(row[name]) for name in self.axes}
            judgement = judged.get(key)

            metrics = []
            for name in METRIC_COLUMNS:
                if name not in grid.columns:
                    continue
                label, unit = METRIC_LABELS[name]
                metrics.append(
                    {
                        "key": name,
                        "label": label,
                        "unit": unit,
                        "value": _scaled(row[name], unit),
                    }
                )
            for name in self.excess_columns:
                metrics.append(
                    {
                        "key": name,
                        "label": f"對 {name[len(EXCESS_PREFIX):]} 超額年化",
                        "unit": "pct",
                        "value": _scaled(row[name], "pct"),
                    }
                )

            cell: dict[str, Any] = {
                "params": params,
                "runId": _clean(row.get("run_id")),
                "trades": _clean(row.get("trades")),
                "metrics": metrics,
            }

            if judgement is None:
                # 掃描表有、判讀表無:當作未判,不冒充一個裁決
                cell.update(
                    {
                        "verdict": None,
                        "value": None,
                        "layer": _layer_name(params, self.choice_axes),
                        "invalid": True,
                    }
                )
            else:
                layer = (
                    str(judgement["layer"]).strip()
                    if has_layer and _clean(judgement["layer"]) is not None
                    else _layer_name(params, self.choice_axes)
                )
                verdict_text = _clean(judgement["verdict"])
                cell.update(
                    {
                        "verdict": verdict_text,
                        "invalid": verdict_text == INVALID,
                        "layer": layer or NO_CHOICE_LAYER,
                        "value": _scaled(judgement.get("value"), self.unit),
                        "neighbours": _clean(judgement.get("neighbours")),
                        "validNeighbours": _clean(judgement.get("valid_neighbours")),
                        "neighbourhoodMean": _scaled(
                            judgement.get("neighbourhood_mean"), self.unit
                        ),
                        "neighbourMean": _scaled(judgement.get("neighbour_mean"), self.unit),
                        "lift": _scaled(judgement.get("lift"), self.unit),
                        "peakOverNeighbourhood": _clean(
                            judgement.get("peak_over_neighbourhood")
                        ),
                        "isLocalPeak": bool(_clean(judgement.get("is_local_peak"))),
                        "siblings": _clean(judgement.get("siblings")),
                        "weakestSiblingMean": _scaled(
                            judgement.get("weakest_sibling_mean"), self.unit
                        ),
                        "layerDrop": _scaled(judgement.get("layer_drop"), self.unit),
                    }
                )
            cells.append(cell)
        return cells

    def _layer_rows(self) -> list[dict[str, Any]]:
        """逐層一行:層名、格數、各裁決計數、該層最優。"""
        order: list[str] = []
        buckets: dict[str, list[dict[str, Any]]] = {}
        for cell in self.cells:
            name = cell["layer"]
            if name not in buckets:
                buckets[name] = []
                order.append(name)
            buckets[name].append(cell)

        rows = []
        for name in order:
            members = buckets[name]
            counts = {v: 0 for v in VERDICTS}
            for cell in members:
                if cell["verdict"] in counts:
                    counts[cell["verdict"]] += 1
            scored = [c for c in members if c.get("value") is not None and not c["invalid"]]
            best = max(scored, key=lambda c: c["value"]) if scored else None
            rows.append(
                {
                    "name": name,
                    "cells": len(members),
                    "counts": counts,
                    "best": None
                    if best is None
                    else {
                        "params": best["params"],
                        "value": best["value"],
                        "verdict": best["verdict"],
                    },
                }
            )
        return rows

    # ---------------- 交出去 ----------------

    def counts(self) -> dict[str, int]:
        counts = {v: 0 for v in VERDICTS}
        for cell in self.cells:
            if cell["verdict"] in counts:
                counts[cell["verdict"]] += 1
        return counts

    def best_cell(self) -> dict[str, Any] | None:
        """全掃描最高分那格。單看它會被孤峰騙,所以永遠與代表格並列。"""
        scored = [
            c for c in self.cells if c.get("value") is not None and not c["invalid"]
        ]
        return max(scored, key=lambda c: c["value"]) if scored else None

    def representative_cell(self) -> dict[str, Any] | None:
        """代表格:高地中間那格——鄰域平均最高、而且**不是孤峰**的那一格。

        「高地中間」在判讀表上沒有一欄直接寫住,所以照 KARST-051 票上寫明的
        退路取:先在平原之中揀鄰域平均最高那格;一格平原都沒有,就在非孤峰的
        有效格之中揀鄰域平均最高那格。孤峰一律不做代表——它正是要防的那件事。
        """
        usable = [
            c
            for c in self.cells
            if not c["invalid"]
            and c.get("neighbourhoodMean") is not None
            and c.get("verdict") != "孤峰"
        ]
        if not usable:
            return None
        plateaus = [c for c in usable if c["verdict"] == "平原"]
        pool = plateaus or usable
        return max(pool, key=lambda c: c["neighbourhoodMean"])

    def _cell_brief(self, cell: dict[str, Any] | None) -> dict[str, Any] | None:
        if cell is None:
            return None
        return {
            "params": cell["params"],
            "layer": cell["layer"],
            "value": cell["value"],
            "verdict": cell["verdict"],
            "neighbourhoodMean": cell.get("neighbourhoodMean"),
            "lift": cell.get("lift"),
            "trades": cell.get("trades"),
            "runId": cell.get("runId"),
        }

    def is_reference(self) -> bool:
        """這次掃描是不是「對照」而不是策略本身的掃描(D-029)。

        用戶裁定:因子混合策略的參數是**驅動器設定**(訊號、回望期、換倉節奏、
        退路),四隻 ETF 的比例是驅動器每個換倉日算出來的**輸出**,不是參數。
        所以一個把 ETF 比例本身當軸來掃的格,掃的不是策略的參數,只是拿固定
        比例來做對照。認法:連續軸清一色是 ``weight_*`` 且有兩條以上。
        """
        weights = [n for n in self.continuous_axes if n.startswith("weight_")]
        return len(weights) >= 2 and len(weights) == len(self.continuous_axes)

    def brief(self) -> dict[str, Any]:
        prov = self.summary.get("provenance")
        prov = prov if isinstance(prov, dict) else {}
        best = self.best_cell()
        return {
            "reference": self.is_reference(),
            "id": self.source.id,
            "label": self.source.label,
            "experiment": self.source.experiment,
            "strategy": prov.get("strategy"),
            "cells": len(self.cells),
            "axes": self.axes,
            "continuousAxes": self.continuous_axes,
            "choiceAxes": self.choice_axes,
            "layers": len(self.layer_rows),
            "axisAware": self.declared,
            "objective": self.objective,
            "objectiveLabel": objective_label(self.objective),
            "objectiveUnit": self.unit,
            "counts": self.counts(),
            "best": self._cell_brief(best),
            "representative": self._cell_brief(self.representative_cell()),
        }

    def provenance(self) -> dict[str, Any]:
        prov = self.summary.get("provenance")
        prov = prov if isinstance(prov, dict) else {}
        thresholds = self.summary.get("thresholds")
        return {
            "strategy": prov.get("strategy"),
            "strategyVersionNo": prov.get("strategy_version_no"),
            "snapshotId": prov.get("snapshot_id") or self.summary.get("snapshot_id"),
            "period": prov.get("period") or self.summary.get("period"),
            "engine": prov.get("engine"),
            "costs": self.summary.get("costs")
            if isinstance(self.summary.get("costs"), str)
            else None,
            "thresholds": thresholds if isinstance(thresholds, dict) else {},
            "gridPath": self.source.grid_path.relative_to(self.source.root).as_posix(),
            "verdictPath": self.source.verdict_path.relative_to(self.source.root).as_posix(),
        }

    def layer_cells(self, layer: str) -> list[dict[str, Any]]:
        return [c for c in self.cells if c["layer"] == layer]

    def projections(self, layer: str) -> tuple[str, list[dict[str, Any]]]:
        """小倍數。回 (模式, 卡片)。

        連續軸有三條或以上:每對一張投影圖(其餘連續軸取平均),看哪一對站得住
        ——原型那六張就是這一種。

        只得一兩條連續軸就配不出「主圖以外」的組合(兩條時配出來那張就是主圖
        本身),改為**每層一張**:同一組連續取值,逐層並排。山脊正是這樣看出來
        的——一層之內是高地,換一層就塌。
        """
        if len(self.continuous_axes) >= 3:
            pairs = [
                (a, b)
                for i, a in enumerate(self.continuous_axes)
                for b in self.continuous_axes[i + 1 :]
            ]
            cards = [self._projection(self.layer_cells(layer), a, b, None) for a, b in pairs]
            return "pair", cards

        if not self.continuous_axes:
            return "layer", []

        row_axis = self.continuous_axes[0] if len(self.continuous_axes) >= 2 else None
        col_axis = self.continuous_axes[-1]
        cards = [
            self._projection(self.layer_cells(row["name"]), row_axis, col_axis, row["name"])
            for row in self.layer_rows
        ]
        return "layer", cards

    def _projection(
        self,
        cells: list[dict[str, Any]],
        row_axis: str | None,
        col_axis: str,
        title: str | None,
    ) -> dict[str, Any]:
        row_values = self.axis_values[row_axis] if row_axis else [None]
        col_values = self.axis_values[col_axis]
        row_index = {v: i for i, v in enumerate(row_values)}
        col_index = {v: i for i, v in enumerate(col_values)}

        sums = [[0.0] * len(col_values) for _ in row_values]
        counts = [[0] * len(col_values) for _ in row_values]
        best: dict[str, Any] | None = None
        for cell in cells:
            if cell.get("value") is None or cell["invalid"]:
                continue
            ri = row_index.get(cell["params"][row_axis], -1) if row_axis else 0
            ci = col_index.get(cell["params"][col_axis], -1)
            if ri < 0 or ci < 0:
                continue
            sums[ri][ci] += cell["value"]
            counts[ri][ci] += 1
            if best is None or cell["value"] > best["value"]:
                best = cell

        grid = [
            [
                (sums[r][c] / counts[r][c]) if counts[r][c] else None
                for c in range(len(col_values))
            ]
            for r in range(len(row_values))
        ]

        return {
            "title": title,
            "rowAxis": row_axis,
            "colAxis": col_axis,
            "rows": [None] if row_axis is None else row_values,
            "cols": col_values,
            "grid": grid,
            "verdict": None if best is None else best["verdict"],
            "best": None
            if best is None
            else {"params": best["params"], "value": best["value"], "verdict": best["verdict"]},
        }

    def payload(self, layer: str | None) -> dict[str, Any]:
        names = [row["name"] for row in self.layer_rows]
        if layer and layer not in names:
            raise NotFound(f"這次掃描沒有這一層:{layer}")
        # 沒有指名就開在**代表格那一層**——D-029 要求一開就見到最佳格與代表格
        # 兩個標記,那就要由代表格所在那一層開起。
        representative = self.representative_cell()
        default_layer = representative["layer"] if representative else None
        if default_layer not in names:
            default_layer = names[0] if names else NO_CHOICE_LAYER
        chosen = layer or default_layer
        small_mode, small_cards = self.projections(chosen)

        note = (
            "判讀已按軸型分過層:鄰域只沿連續軸取,選擇軸另計一層。"
            if self.declared
            else "本次判讀落檔時把全部軸當連續軸(舊口徑);畫面上的選擇軸由取值形態認出,"
            "只影響切法,不改已落檔的裁決。"
        )

        return {
            **self.brief(),
            "objectiveUnit": self.unit,
            "judgementNote": note,
            "provenance": self.provenance(),
            "axisList": [
                {
                    "name": name,
                    "kind": CHOICE if name in self.choice_axes else CONTINUOUS,
                    "numeric": self.axis_numeric[name],
                    "values": self.axis_values[name],
                }
                for name in self.axes
            ],
            "layerRows": self.layer_rows,
            "layer": chosen,
            "cells": self.layer_cells(chosen),
            "smallMode": small_mode,
            "projections": small_cards,
            "detailMetrics": list(DETAIL_METRICS),
        }


# ============================================================
# 端點
# ============================================================


def _project_root(reader: Any) -> Path:
    """由 reader 推回專案根。data.py 沒有 root 欄位,靠 runs_root 倒推。"""
    runs_root = getattr(reader, "runs_root", None)
    if runs_root is not None:
        path = Path(runs_root)
        if path.name == "runs" and path.parent.name == "data":
            return path.parent.parent
    return Path.cwd().resolve()


class SweepReader:
    """掃描落檔的唯讀讀取層,按檔案改動時間快取。"""

    def __init__(self, root: Path, reader: Any = None) -> None:
        self.root = root
        self.reader = reader
        self._views: dict[str, tuple[tuple, SweepView]] = {}
        self._sources: list[SweepSource] | None = None
        self._run_strategies: dict[str, str] | None = None

    # ---------------- 策略名倒查 ----------------

    def _strategy_by_run(self) -> dict[str, str]:
        """運行編號 → 策略名。掃描落檔的 summary.json 未必記得住策略名,
        但每一格都寫住運行編號,而運行入了庫——由庫倒查得回,好過在清單上
        印一句「落檔未記」。只讀登記本身,不掂運行結果檔。"""
        if self._run_strategies is None:
            table: dict[str, str] = {}
            try:
                for record in self.reader.runs.list_runs():
                    table[record.run_id] = record.strategy_name
            except Exception:  # noqa: BLE001 - 倒查不到就當沒有,不可拖冧成張清單
                table = {}
            self._run_strategies = table
        return self._run_strategies

    def _with_strategy(self, view: SweepView, data: dict[str, Any]) -> dict[str, Any]:
        if data.get("strategy") or self.reader is None:
            return data
        table = self._strategy_by_run()
        for cell in view.cells:
            name = table.get(cell.get("runId") or "")
            if name:
                data["strategy"] = name
                data["strategyFrom"] = "由格內運行倒查"
                break
        return data

    def sources(self, refresh: bool = False) -> list[SweepSource]:
        if self._sources is None or refresh:
            self._sources = discover_sweeps(self.root)
        return self._sources

    def view(self, sweep_id: str) -> SweepView:
        for source in self.sources():
            if source.id == sweep_id:
                break
        else:
            for source in self.sources(refresh=True):
                if source.id == sweep_id:
                    break
            else:
                raise NotFound(f"沒有這次掃描:{sweep_id}")

        signature = source.signature()
        cached = self._views.get(sweep_id)
        if cached is None or cached[0] != signature:
            self._views[sweep_id] = (signature, SweepView(source))
        return self._views[sweep_id][1]

    def list_sweeps(self) -> dict[str, Any]:
        sweeps = []
        for source in self.sources(refresh=True):
            try:
                view = self.view(source.id)
                sweeps.append(self._with_strategy(view, view.brief()))
            except Exception as exc:  # noqa: BLE001
                # 一次掃描讀不到,不應該令整張清單開不到——列出來並講明原因
                sweeps.append(
                    {
                        "id": source.id,
                        "label": source.label,
                        "experiment": source.experiment,
                        "error": f"{type(exc).__name__}：{exc}",
                    }
                )
        return {"sweeps": sweeps, "total": len(sweeps)}

    def get_sweep(self, query: dict[str, list[str]]) -> dict[str, Any]:
        sweep_id = (query.get("id") or [""])[0].strip()
        if not sweep_id:
            sweeps = self.sources()
            if not sweeps:
                raise NotFound("找不到任何掃描落檔")
            sweep_id = sweeps[0].id
        layer = (query.get("layer") or [""])[0].strip() or None
        view = self.view(sweep_id)
        return self._with_strategy(view, view.payload(layer))


def routes(reader: Any) -> dict[str, Callable[[Any, dict[str, list[str]]], Any]]:
    """本頁的全部端點。server.py 只需把這個 dict 併入它的 routes。"""
    sweeps = SweepReader(_project_root(reader), reader)
    return {
        "/api/sweeps": lambda handler, query: sweeps.list_sweeps(),
        "/api/sweep": lambda handler, query: sweeps.get_sweep(query),
    }
