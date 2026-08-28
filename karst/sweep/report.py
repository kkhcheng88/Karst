"""報告:熱力圖、投影圖,以及一份指得回運行設定的說明。

兩種圖是同一件事的兩個樣子:

* **熱力圖**(heat map)——二維格畫一張,一格一個色塊。
* **投影圖**(projection map)——高維格每一對參數畫一張,其餘維度取平均。四個
  權重就是六張(質素×價值、質素×動能……)。投影圖的一個色塊蓋住很多格,所以
  它旁邊一定要寫住蓋了幾多格、其中幾多格無效——不然「平均」兩個字會騙人。

兩種圖都由同一個函式畫:二維格的投影圖,每一個色塊剛好只蓋一格,即是熱力圖。

**無效格在圖上分得出**(驗收條件三):整個色塊全部無效就填成灰,不參與色階;
半數無效的會在格上打一個星。孤峰打三角、山脊打等號、平原打點——圖例逐個寫明。

**選擇軸的格逐層出圖**(KARST-047)。持現金/均分、月度/季度那一類選擇軸不入
鄰域,而是把格切成一層層;把幾層壓成同一張圖,一條山脊就會被別層的爛成績沖淡。
所以有選擇軸的判讀請用 ``draw_layer_projections``:**每一層自己一套投影圖**,
只投影連續軸。真的要跨層看,``draw_heatmap`` 照畫得出,但圖上會明寫「此圖跨越
選擇軸,色塊是幾層的平均」——不讓那句沖淡靜靜地發生。

報告本身(``write_report``)頂頭那一行永遠是來歷:**策略版本 × 期間 × 數據快照
× 引擎版本**(規格 7.4)。掃描表與判讀表同時落 CSV,所以就算一張圖都畫不出
(沒裝繪圖庫),數字仍然齊全、仍然指得回每一格是哪一次運行。
"""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ..errors import ContractViolation
from .grid import LayerKey, layer_label, layer_slug
from .runner import SweepCell, SweepRun
from .verdict import INVALID, LONELY_PEAK, PLATEAU, RIDGE, SweepJudgement

# 圖上想用的中文字型,由上而下試。一個都沒有就退回英文標題,不畫豆腐方塊。
_CJK_FONTS = (
    "Microsoft JhengHei",
    "Microsoft YaHei",
    "Noto Sans CJK TC",
    "Noto Sans CJK SC",
    "SimHei",
    "PingFang TC",
)


@dataclass(frozen=True, slots=True)
class ProjectionCell:
    """投影圖的一個色塊:蓋住哪些格、平均幾多、其中幾多格無效。"""

    x: Any
    y: Any
    mean: float | None
    best: float | None
    cells: int
    invalid: int
    plateaus: int
    lonely_peaks: int
    ridges: int = 0
    layers: int = 1

    @property
    def all_invalid(self) -> bool:
        return self.cells > 0 and self.invalid == self.cells


def projection(judgement: SweepJudgement, x_axis: str, y_axis: str) -> pd.DataFrame:
    """把整個格投影去 ``x_axis`` × ``y_axis`` 兩個維度。

    其餘維度取**有效格的平均**;一個有效格都沒有的色塊,平均是 ``None`` 而不是
    零——沒有數就是沒有數,填零會被讀成「回報是零」。

    ``layers`` 一欄講這個色塊蓋住幾多**層**(選擇軸的幾組取值)。大過一,即是這
    張圖把幾層壓在一齊,色塊的平均會被別層沖淡——逐層出圖見
    ``draw_layer_projections``。
    """
    if x_axis == y_axis:
        raise ContractViolation(f"投影的兩個軸不可以是同一個:{x_axis}")

    buckets: dict[tuple[Any, Any], list] = {}
    for cell in judgement.cells:
        key = (cell.point.get(x_axis), cell.point.get(y_axis))
        buckets.setdefault(key, []).append(cell)

    rows: list[dict[str, Any]] = []
    for (x_value, y_value), group in buckets.items():
        values = [c.value for c in group if c.verdict != INVALID and c.value is not None]
        rows.append(
            {
                x_axis: x_value,
                y_axis: y_value,
                "mean": float(sum(values) / len(values)) if values else None,
                "best": max(values) if values else None,
                "cells": len(group),
                "invalid": sum(1 for c in group if c.verdict == INVALID),
                "plateaus": sum(1 for c in group if c.verdict == PLATEAU),
                "ridges": sum(1 for c in group if c.verdict == RIDGE),
                "lonely_peaks": sum(1 for c in group if c.verdict == LONELY_PEAK),
                "layers": len({c.layer for c in group}),
            }
        )
    frame = pd.DataFrame(rows)
    return frame.sort_values([y_axis, x_axis]).reset_index(drop=True)


def projection_cells(judgement: SweepJudgement, x_axis: str, y_axis: str) -> tuple[ProjectionCell, ...]:
    frame = projection(judgement, x_axis, y_axis)
    return tuple(
        ProjectionCell(
            x=row[x_axis],
            y=row[y_axis],
            mean=None if pd.isna(row["mean"]) else float(row["mean"]),
            best=None if pd.isna(row["best"]) else float(row["best"]),
            cells=int(row["cells"]),
            invalid=int(row["invalid"]),
            plateaus=int(row["plateaus"]),
            lonely_peaks=int(row["lonely_peaks"]),
            ridges=int(row["ridges"]),
            layers=int(row["layers"]),
        )
        for _, row in frame.iterrows()
    )


def _pyplot():
    """遲到這一刻才 import 繪圖庫:沒裝的人一樣讀得到 CSV 與報告文字。"""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - 視乎有沒有裝
        raise ContractViolation(
            "畫熱力圖要 matplotlib,這部機沒有裝(它不是 karst 的必要依賴)。"
            "掃描表與判讀表照樣落了 CSV,數字一個不缺"
        ) from exc
    return plt


def _apply_cjk_font(plt) -> bool:
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in _CJK_FONTS:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name, *plt.rcParams.get("font.sans-serif", [])]
            plt.rcParams["axes.unicode_minus"] = False
            return True
    return False


def draw_heatmap(
    judgement: SweepJudgement,
    path: str | Path,
    *,
    x_axis: str,
    y_axis: str,
    title: str,
    subtitle: str = "",
    statistic: str = "mean",
) -> Path:
    """畫一張熱力圖 / 投影圖並落檔,回傳檔案路徑。

    ``statistic`` 揀 ``mean``(其餘維度取平均)或者 ``best``(取最好那一格)。
    二維格兩者一樣,因為一個色塊只蓋一格。

    圖若然跨越選擇軸(x/y 是選擇軸,或者其餘維度裡有選擇軸),副標題會自動加一句
    講明色塊是幾層的平均——**不讓沖淡靜靜地發生**(KARST-047)。
    """
    if statistic not in {"mean", "best"}:
        raise ContractViolation(f"統計只收 mean 或 best,收到 {statistic!r}")

    plt = _pyplot()
    has_cjk = _apply_cjk_font(plt)
    frame = projection(judgement, x_axis, y_axis)
    subtitle = _layer_note(judgement, x_axis, y_axis, subtitle, frame)
    xs = sorted(frame[x_axis].unique(), key=_sort_key)
    ys = sorted(frame[y_axis].unique(), key=_sort_key)

    table = frame.pivot(index=y_axis, columns=x_axis, values=statistic).reindex(
        index=ys, columns=xs
    )
    marks = {
        (row[x_axis], row[y_axis]): (
            int(row["cells"]),
            int(row["invalid"]),
            int(row["plateaus"]),
            int(row["lonely_peaks"]),
            int(row["ridges"]),
        )
        for _, row in frame.iterrows()
    }

    width = max(5.0, 0.75 * len(xs) + 3.0)
    height = max(4.0, 0.6 * len(ys) + 2.4)
    figure, axes = plt.subplots(figsize=(width, height), dpi=140)
    axes.set_facecolor("#d9d9d9")  # 無數的色塊留灰底
    image = axes.imshow(
        table.to_numpy(dtype=float),
        cmap="RdYlGn",
        aspect="auto",
        origin="lower",
        interpolation="nearest",
    )
    axes.set_xticks(range(len(xs)), _ticks(xs))
    axes.set_yticks(range(len(ys)), _ticks(ys))
    axes.set_xlabel(x_axis)
    axes.set_ylabel(y_axis)

    for yi, y_value in enumerate(ys):
        for xi, x_value in enumerate(xs):
            cells, invalid, plateaus, peaks, ridges = marks.get(
                (x_value, y_value), (0, 0, 0, 0, 0)
            )
            if cells == 0:
                continue
            if invalid == cells:
                axes.add_patch(
                    plt.Rectangle(
                        (xi - 0.5, yi - 0.5), 1, 1,
                        facecolor="#b0b0b0", edgecolor="white", hatch="//", linewidth=0.5,
                    )
                )
                continue
            label = ""
            if peaks:
                label = "▲"
            elif ridges:
                label = "="
            elif plateaus:
                label = "·"
            if invalid:
                label += "*"
            if label:
                axes.text(xi, yi, label, ha="center", va="center", fontsize=8, color="#202020")

    bar = figure.colorbar(image, ax=axes)
    bar.set_label(judgement.objective if has_cjk else judgement.objective)

    heading = title if has_cjk else _ascii_fallback(title)
    note = subtitle if has_cjk else _ascii_fallback(subtitle)
    axes.set_title(heading + (f"\n{note}" if note else ""), fontsize=10)
    legend = (
        "▲ 孤峰   = 山脊(沿連續軸平順,換一層即掉)   · 平原   * 部分無效   "
        "斜線格 = 整格無效(成交太少)   "
        "淨灰格 = 這個組合根本不存在(例如兩個權重加起來已經超過一)"
        if has_cjk
        else (
            "^ lonely peak   = ridge   . plateau   * partly invalid   "
            "hatched = all invalid   plain grey = combination does not exist"
        )
    )
    figure.text(0.01, 0.01, legend, fontsize=7, color="#404040")
    figure.tight_layout()

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out, bbox_inches="tight")
    plt.close(figure)
    return out


def _layer_note(
    judgement: SweepJudgement,
    x_axis: str,
    y_axis: str,
    subtitle: str,
    frame: pd.DataFrame,
) -> str:
    """跨層的圖,副標題自動加一句;只有一層的圖只講明它是哪一層。

    兩件事分開講,因為它們是兩件事:一是**圖上有一條軸是選擇軸**(那一軸上左右
    相鄰兩格不是一步之遙,是另一套做法);二是**一個色塊真的壓住幾層**(那時
    平均會被別層沖淡)。第一件不一定引致第二件。
    """
    if not judgement.choice_axes:
        return subtitle
    notes: list[str] = []
    if len(judgement.layer_keys()) <= 1:
        notes.append(f"只看「{layer_label(judgement.layer_keys()[0])}」這一層")
    else:
        crossed = [name for name in (x_axis, y_axis) if name in judgement.choice_axes]
        if crossed:
            notes.append(
                f"{'、'.join(crossed)} 是選擇軸:那一軸上相鄰兩格不是一步之遙,是另一層"
            )
        stacked = int(frame["layers"].max()) if len(frame) else 1
        if stacked > 1:
            # 不用 ⚠ 那個符號:中文字型多數沒有它,印出來是一個豆腐方塊。
            notes.append(
                f"注意——每個色塊壓住 {stacked} 層的平均,一條山脊會被別層沖淡"
                "(逐層的圖見 draw_layer_projections)"
            )
    note = ";".join(notes)
    if not note:
        return subtitle
    return f"{subtitle}|{note}" if subtitle else note


def draw_projection_set(
    judgement: SweepJudgement,
    directory: str | Path,
    *,
    axes: Sequence[str],
    title: str,
    subtitle: str = "",
    statistic: str = "mean",
    prefix: str = "projection",
) -> tuple[Path, ...]:
    """高維格:每一對參數畫一張投影圖。四個權重就是六張。

    有選擇軸的判讀,這個函式仍然照畫(每張圖會自報跨了幾層),但**逐層的圖請用**
    ``draw_layer_projections``。
    """
    names = [str(a).strip() for a in axes]
    if len(names) < 2:
        raise ContractViolation("投影圖最少要兩個軸")
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            x_axis, y_axis = names[i], names[j]
            path = out / f"{prefix}-{_slug(x_axis)}-{_slug(y_axis)}.png"
            paths.append(
                draw_heatmap(
                    judgement,
                    path,
                    x_axis=x_axis,
                    y_axis=y_axis,
                    title=f"{title}:{x_axis} × {y_axis}",
                    subtitle=subtitle,
                    statistic=statistic,
                )
            )
    return tuple(paths)


def draw_layer_projections(
    judgement: SweepJudgement,
    directory: str | Path,
    *,
    axes: Sequence[str] | None = None,
    title: str,
    subtitle: str = "",
    statistic: str = "mean",
    prefix: str = "projection",
) -> dict[LayerKey, tuple[Path, ...]]:
    """**逐層各出一套投影圖**(KARST-047):選擇軸切出幾層,就有幾套圖。

    ``axes`` 預設取判讀的**連續軸**——選擇軸已經是分層的依據,再把它畫上去只會
    畫出一條單格的線。一層之內只得一條連續軸的話(例如「回望期 × 退路 × 節奏」
    分層之後只剩回望期),投影圖需要兩條軸才畫得成,那時本函式**不畫圖**,只回
    一個空的清單——數字在判讀表與分層判讀表上,一格不缺。

    沒有選擇軸的判讀,行為與 ``draw_projection_set`` 一樣:整個格一套圖。
    """
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    names = (
        [str(a).strip() for a in axes]
        if axes is not None
        else [n for n in _judgement_axes(judgement) if n not in judgement.choice_axes]
    )

    result: dict[LayerKey, tuple[Path, ...]] = {}
    for key in judgement.layer_keys():
        slice_ = judgement.layer(key) if judgement.choice_axes else judgement
        if len(names) < 2:
            result[key] = ()
            continue
        tag = layer_slug(key)
        heading = f"{title}({layer_label(key)})" if key else title
        result[key] = draw_projection_set(
            slice_,
            out,
            axes=names,
            title=heading,
            subtitle=subtitle,
            statistic=statistic,
            prefix=f"{prefix}-{tag}" if key else prefix,
        )
    return result


def _judgement_axes(judgement: SweepJudgement) -> tuple[str, ...]:
    """判讀本身有哪幾條軸(逐格的參數名;整份判讀的每一格參數名相同)。"""
    if not judgement.cells:
        return ()
    return judgement.cells[0].point.names


def write_report(
    sweep: SweepRun,
    judgement: SweepJudgement,
    directory: str | Path,
    *,
    title: str,
    charts: Sequence[Path] = (),
    references: Sequence[SweepCell] = (),
    notes: str = "",
    top: int = 5,
    filename: str = "報告.md",
) -> Path:
    """把掃描表、判讀表與報告文字一齊落檔,回傳報告檔的路徑。

    落三樣:``掃描表.csv``(逐格八項指標 + 運行編號)、``判讀表.csv``(逐格裁決
    與鄰域平均)、以及一份 Markdown 報告。報告頂頭那一行就是來歷——**策略版本 ×
    期間 × 數據快照 × 引擎版本**,規格 7.4 要的正是這一句。
    """
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)

    sweep_csv = out / "掃描表.csv"
    verdict_csv = out / "判讀表.csv"
    sweep.frame().to_csv(sweep_csv, index=False, encoding="utf-8-sig")
    judgement.frame().to_csv(verdict_csv, index=False, encoding="utf-8-sig")

    best = judgement.best
    robust = judgement.most_robust
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"產出於 {datetime.now():%Y-%m-%d %H:%M}。")
    lines.append("")
    lines.append("## 這次掃的是哪一套設定")
    lines.append("")
    lines.append(f"- 來歷:{sweep.provenance.line()}")
    if not sweep.provenance.consistent:
        lines.append(
            "- ⚠ 這次掃描之內來歷不一致(見上一行列出的多個值);格與格之間的差異"
            "不只來自參數,判讀請小心"
        )
    lines.append(f"- 掃描格:{judgement.grid_description}")
    lines.append(
        f"- 跑法:共 {len(sweep)} 格,其中 {sweep.executed} 格今次真的動過引擎、"
        f"{sweep.reused} 格是讀回已有的運行(同一格不重跑);耗時 {sweep.seconds:.1f} 秒"
    )
    lines.append(
        f"- 無風險利率 {sweep.risk_free_rate:.2%}(Sortino 用);"
        f"基準 {'、'.join(sweep.benchmark_tickers) or '(這次沒有算超額)'}"
    )
    lines.append(f"- 逐格的運行編號在 `{sweep_csv.name}` 的 `run_id` 欄,一格一個。")
    lines.append("")
    lines.append("## 判讀門檻")
    lines.append("")
    lines.append(f"- {judgement.thresholds_line()}")
    lines.append(f"- {judgement.axes_line()}")
    if judgement.choice_axes:
        lines.append(
            "- 鄰域平均**包含自己那一格**,而且**只沿連續軸取**——選擇軸不入鄰域"
            "(KARST-047)。不含自己的那個數在判讀表的 `neighbour_mean` 欄;"
            "換一層的代價在 `weakest_sibling_mean` 與 `layer_drop` 兩欄。"
        )
    else:
        lines.append(
            "- 鄰域平均**包含自己那一格**(二維即整個 3×3 九格);不含自己的那個數在"
            "判讀表的 `neighbour_mean` 欄。"
        )
    lines.append("")
    lines.append("## 結果")
    lines.append("")
    lines.append(f"- {judgement.summary()}")
    if best is not None:
        lines.append(
            f"- **單點最優**:{best.point.label};{judgement.objective} = "
            f"{_num(best.value)},鄰域平均 {_num(best.neighbourhood_mean)}"
            f"(落差 {_num(best.lift)},{best.verdict}),成交 {best.trades} 筆,"
            f"運行編號 {sweep.cell_for(best.point).run_id}"
        )
    if robust is not None:
        lines.append(
            f"- **鄰域平均最高**:{robust.point.label};鄰域平均 "
            f"{_num(robust.neighbourhood_mean)},本格 {_num(robust.value)}"
            f"({robust.verdict}),運行編號 {sweep.cell_for(robust.point).run_id}"
        )
    if best is not None and robust is not None and best.point != robust.point:
        lines.append(
            "- 單點最優與鄰域平均最高**不是同一格**——這正是規格 6.5 要人看住的那件事:"
            "單點最高不等於穩健。"
        )
    lines.append("")
    lines.append(f"### 頭 {top} 格(按 {judgement.objective},只計有效格)")
    lines.append("")
    lines.append(f"| # | 參數 | {judgement.objective} | 鄰域平均 | 落差 | 裁決 | 成交筆數 | 運行編號 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for rank, cell in enumerate(judgement.top(top), start=1):
        lines.append(
            f"| {rank} | {cell.point.label} | {_num(cell.value)} | "
            f"{_num(cell.neighbourhood_mean)} | {_num(cell.lift)} | {cell.verdict} | "
            f"{cell.trades} | {sweep.cell_for(cell.point).run_id} |"
        )
    lines.append("")

    if references:
        lines.append("### 對照格")
        lines.append("")
        lines.append(f"| 參數 | {judgement.objective} | 全格排名 | 運行編號 |")
        lines.append("|---|---|---|---|")
        ranked = [c for c in judgement.top(len(judgement)) ]
        order = {cell.point: index for index, cell in enumerate(ranked, start=1)}
        for cell in references:
            value = cell.value_of(judgement.objective)
            place = order.get(cell.point)
            lines.append(
                f"| {cell.point.label} | {_num(value)} | "
                f"{place if place else '不在這個格上'} | {cell.run_id} |"
            )
        lines.append("")

    if judgement.choice_axes:
        layer_csv = out / "分層判讀表.csv"
        layer_table = judgement.layer_frame()
        layer_table.to_csv(layer_csv, index=False, encoding="utf-8-sig")
        lines.append(
            f"### 分層判讀(選擇軸 {'、'.join(judgement.choice_axes)} 切出"
            f" {len(judgement.layer_keys())} 層)"
        )
        lines.append("")
        lines.append(
            "選擇軸換一個取值即換一套做法,不是微調——所以它不入鄰域,而是逐層各出"
            "一份判讀。同一條連續軸在哪一層站得住、在哪一層沒有,就在這張表上。"
        )
        lines.append("")
        columns = ["層", "格數", "有效格", "高地格數", PLATEAU, RIDGE, LONELY_PEAK, "最優", "層平均"]
        lines.append("| " + " | ".join(columns) + " |")
        lines.append("|" + "---|" * len(columns))
        for _, row in layer_table.iterrows():
            lines.append(
                "| "
                + " | ".join(
                    (
                        _num(row[name])
                        if name in {"最優", "層平均"}
                        else str(row[name])
                    )
                    for name in columns
                )
                + " |"
            )
        lines.append("")
        lines.append(f"逐層的完整數字在 `{layer_csv.name}`。")
        lines.append("")

    if judgement.ridges:
        lines.append("### 山脊(沿連續軸平順,換一層即掉;KARST-047)")
        lines.append("")
        lines.append(
            "這幾格自己與連續軸鄰域平均都在高地,但同一組連續軸取值換去另一層之後,"
            "那一層的鄰域平均跌穿高地門檻。**不是平原**(換一套做法就沒有了),"
            "**亦不是孤峰**(連續軸上揀錯一兩格不要緊)。"
        )
        lines.append("")
        for cell in sorted(judgement.ridges, key=lambda c: c.value or 0.0, reverse=True)[:20]:
            lines.append(
                f"- {cell.point.label}:{_num(cell.value)},連續軸鄰域平均 "
                f"{_num(cell.neighbourhood_mean)};換去最差那一層只有 "
                f"{_num(cell.weakest_sibling_mean)}(跌 {_num(cell.layer_drop)})"
            )
        if len(judgement.ridges) > 20:
            lines.append(f"- (其餘 {len(judgement.ridges) - 20} 格見判讀表)")
        lines.append("")

    if judgement.lonely_peaks:
        lines.append("### 孤峰(判為擬合噪音,D-016 第 3 條)")
        lines.append("")
        for cell in sorted(judgement.lonely_peaks, key=lambda c: c.value or 0.0, reverse=True)[:20]:
            lines.append(
                f"- {cell.point.label}:{_num(cell.value)},鄰域平均 "
                f"{_num(cell.neighbourhood_mean)},高出 {_num(cell.lift)}"
            )
        if len(judgement.lonely_peaks) > 20:
            lines.append(f"- (其餘 {len(judgement.lonely_peaks) - 20} 格見判讀表)")
        lines.append("")

    if judgement.invalid_cells:
        lines.append("### 無效格(成交太少,數字講的是運氣不是參數)")
        lines.append("")
        lines.append(
            f"- 共 {len(judgement.invalid_cells)} 格成交少於 {judgement.min_trades} 筆;"
            "它們不入最優,亦不入任何一格的鄰域平均。"
        )
        for cell in judgement.invalid_cells[:10]:
            lines.append(f"  - {cell.point.label}:成交 {cell.trades} 筆")
        if len(judgement.invalid_cells) > 10:
            lines.append(f"  - (其餘 {len(judgement.invalid_cells) - 10} 格見判讀表)")
        lines.append("")

    if charts:
        lines.append("## 圖")
        lines.append("")
        for chart in charts:
            name = Path(chart).name
            lines.append(f"![{name}]({name})")
            lines.append("")

    if notes:
        lines.append("## 備註")
        lines.append("")
        lines.append(notes)
        lines.append("")

    lines.append("## 檔")
    lines.append("")
    lines.append(f"- `{sweep_csv.name}`:逐格八項指標、成交筆數、運行編號")
    lines.append(f"- `{verdict_csv.name}`:逐格裁決、鄰域平均、落差、所在層、換層代價")
    if judgement.choice_axes:
        lines.append("- `分層判讀表.csv`:逐層的裁決分佈、最優格、層平均")
    lines.append("")
    lines.append(
        "本報告只交表與判讀,**不裁定哪一組參數該用**——那是用戶的領域(D-008)。"
    )
    lines.append("")

    path = out / filename
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def copy_chart(source: str | Path, directory: str | Path) -> Path:
    out = Path(directory) / Path(source).name
    if Path(source).resolve() != out.resolve():
        shutil.copyfile(source, out)
    return out


def _num(value: float | None) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    return f"{float(value):.4f}"


def _as_number(value: Any) -> float | None:
    """數字就交回它的浮點值,不是數字就交回 ``None``。

    **不可以只靠 ``isinstance(value, (int, float))``**:掃描表由 CSV 或者 parquet
    讀回來時,取值是 ``numpy.int64`` 一類,它不是 Python 的 ``int`` 子類。當日
    只認 Python 型別,回望期就會由 1、10、11…… 這樣按字排,圖上的軸次序整條錯,
    而且錯得靜——色塊照樣畫得出。
    """
    if isinstance(value, bool) or isinstance(value, str):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None  # NaN 不當數字排


def _ticks(values: Sequence[Any]) -> list[str]:
    """一條軸的刻度標籤。**百分比與否由整條軸一齊決定,不是逐格猜。**

    權重軸(0.05、0.1、…)印成百分點才看得懂;但回望期那條軸的第一格是 ``1``,
    逐格猜的話它會落在 0 至 1 之間而被印成「100%」——同一條軸上「100%」旁邊
    企住「2」、「3」,讀圖的人只會以為圖壞了。所以規矩是:**整條軸的取值全部
    在 0 與 1 之間、而且至少有一個不是整數**,才當它是比例軸。
    """
    numbers = [_as_number(v) for v in values]
    percent = (
        all(n is not None and 0.0 <= n <= 1.0 for n in numbers)
        and any(n is not None and abs(n - round(n)) > 1e-9 for n in numbers)
    )
    return [_tick(value, percent=percent) for value in values]


def _tick(value: Any, *, percent: bool = False) -> str:
    if isinstance(value, bool):
        return str(value)
    number = _as_number(value)
    if number is not None:
        if percent and abs(number * 100 - round(number * 100)) < 1e-6:
            return f"{number:.0%}"
        return f"{number:g}"
    return str(value)


def _sort_key(value: Any) -> tuple[int, Any]:
    number = _as_number(value)
    if number is not None:
        return (0, number)
    return (1, str(value))


def _slug(text: str) -> str:
    return str(text).strip().replace("_", "-").replace(" ", "-")


def _ascii_fallback(text: str) -> str:
    """沒有中文字型時,寧可印得出的英文,不印一行豆腐方塊。"""
    return "".join(ch if ord(ch) < 128 else "?" for ch in text)
