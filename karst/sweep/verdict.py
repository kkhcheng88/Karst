"""判讀:平原、孤峰、無效格。

D-016 第 3 條與規格 6.5 的判準是**參數穩健平原**——最優那一格的鄰域表現皆佳
才算穩健;峰值明顯高於鄰域的當擬合噪音,叫孤峰。KARST-013 那次 144 組示範就是
這樣判的:單點最優夏普 1.61,3×3 鄰域平均只有 1.16,故判孤峰。

本檔把那次一次性的判法寫成規矩,三個門檻**一個預設值都沒有**:

``min_trades``
    成交筆數少過這個數的格判**無效**。無效格不入最優、不入任何鄰域平均——
    一格只成交過兩次,那個回報數字講的是運氣,不是這組參數。

``lonely_peak_margin``
    「明顯高於」高幾多才算。單位就是目標指標自己的單位(年化超額用的是小數,
    0.02 即兩個百分點)。KARST-013 那次的落差是 0.45 個夏普。

``plateau_quantile``
    高地由哪一個分位起計。0.9 即「有效格之中目標值排前一成」。

本檔**不裁定哪一格該用**(D-008):它只把每格貼上四個標籤之一,最優與最穩健
兩格並列交出,揀哪一格是用戶的事。

一句講清楚方向:**目標指標一律「越大越好」**。最大回撤在本倉一路以負數表示
(-0.23 即跌兩成三),所以「越大」剛好就是「跌得越少」,不用另設一個方向參數。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

import pandas as pd

from ..errors import ContractViolation
from .grid import SweepGrid, SweepPoint

# 四個裁決標籤。無效格永不參與其他三種判讀。
PLATEAU: Final[str] = "平原"
LONELY_PEAK: Final[str] = "孤峰"
ORDINARY: Final[str] = "普通"
INVALID: Final[str] = "無效"
NO_NEIGHBOUR: Final[str] = "無鄰"

VERDICTS: Final[tuple[str, ...]] = (PLATEAU, LONELY_PEAK, ORDINARY, INVALID, NO_NEIGHBOUR)


@dataclass(frozen=True, slots=True)
class CellScore:
    """判讀的輸入:一格的參數、它的目標指標讀數、它成交過幾多筆。

    ``value`` 是 ``None`` 即這一格算不出目標指標(例如一次都未平倉就沒有勝率)
    ——當無效處理,不當零。
    """

    point: SweepPoint
    value: float | None
    trades: int


@dataclass(frozen=True, slots=True)
class CellVerdict:
    """一格的裁決,連同判它的那幾個數。

    ``neighbourhood_mean`` **包含自己那一格**(二維即整個 3×3 九格的平均),與
    規格 6.5、KARST-013 那次的講法一致;``neighbour_mean`` 是**不含自己**的鄰居
    平均,想看純粹的四周有幾好時用它。兩個都列出來,免得下一個人要猜是哪一個。
    """

    point: SweepPoint
    value: float | None
    trades: int
    verdict: str
    neighbours: tuple[SweepPoint, ...]
    neighbour_values: tuple[float, ...]
    neighbourhood_mean: float | None
    neighbour_mean: float | None
    lift: float | None
    ratio: float | None
    is_local_peak: bool

    @property
    def valid(self) -> bool:
        return self.verdict != INVALID

    def as_row(self) -> dict[str, Any]:
        row: dict[str, Any] = dict(self.point.as_dict())
        row.update(
            {
                "value": self.value,
                "trades": self.trades,
                "verdict": self.verdict,
                "neighbours": len(self.neighbours),
                "valid_neighbours": len(self.neighbour_values),
                "neighbourhood_mean": self.neighbourhood_mean,
                "neighbour_mean": self.neighbour_mean,
                "lift": self.lift,
                "peak_over_neighbourhood": self.ratio,
                "is_local_peak": self.is_local_peak,
            }
        )
        return row


@dataclass(frozen=True, slots=True)
class SweepJudgement:
    """一次掃描判完之後的全部結果。

    ``best`` 是有效格之中目標指標最高那一格(單點最優);``most_robust`` 是鄰域
    平均最高那一格——**穩健平原的中心**。兩格不同,通常就是在講單點最優靠不住。
    """

    objective: str
    min_trades: int
    lonely_peak_margin: float
    plateau_quantile: float
    plateau_threshold: float | None
    cells: tuple[CellVerdict, ...]
    grid_description: str

    def __len__(self) -> int:
        return len(self.cells)

    def frame(self) -> pd.DataFrame:
        """逐格一行的判讀表,次序與掃描次序一致。"""
        return pd.DataFrame([cell.as_row() for cell in self.cells])

    def _by(self, verdict: str) -> tuple[CellVerdict, ...]:
        return tuple(cell for cell in self.cells if cell.verdict == verdict)

    @property
    def plateaus(self) -> tuple[CellVerdict, ...]:
        return self._by(PLATEAU)

    @property
    def lonely_peaks(self) -> tuple[CellVerdict, ...]:
        return self._by(LONELY_PEAK)

    @property
    def invalid_cells(self) -> tuple[CellVerdict, ...]:
        return self._by(INVALID)

    @property
    def valid_cells(self) -> tuple[CellVerdict, ...]:
        return tuple(cell for cell in self.cells if cell.verdict != INVALID)

    @property
    def best(self) -> CellVerdict | None:
        """單點最優:有效格之中目標指標最高那一格。"""
        return _pick(
            [c for c in self.valid_cells if c.value is not None], lambda c: float(c.value)
        )

    @property
    def most_robust(self) -> CellVerdict | None:
        """鄰域平均最高那一格(含自己那一格的平均)。"""
        return _pick(
            [c for c in self.valid_cells if c.neighbourhood_mean is not None],
            lambda c: float(c.neighbourhood_mean),
        )

    def where(self, **fixed: Any) -> "SweepJudgement":
        """切一片出來:某幾個參數釘死,只留符合的格。

        用來分開畫圖——例如節奏也在掃描格之內時,月度與季度各畫一套投影圖,
        免得兩個節奏的成績在同一個色塊裡互相沖淡。

        **裁決不重判**:每一格的標籤與鄰域平均仍然是在整個格上算出來的那一個,
        這裡只是揀出來看。要重判請對切出來的成績重新叫 ``judge``。
        """
        if not fixed:
            return self
        kept = tuple(
            cell
            for cell in self.cells
            if all(cell.point.get(name) == value for name, value in fixed.items())
        )
        if not kept:
            raise ContractViolation(
                f"切不出格:沒有一格符合 {fixed};請核對參數名與取值"
            )
        note = "、".join(f"{name}={value}" for name, value in fixed.items())
        return SweepJudgement(
            objective=self.objective,
            min_trades=self.min_trades,
            lonely_peak_margin=self.lonely_peak_margin,
            plateau_quantile=self.plateau_quantile,
            plateau_threshold=self.plateau_threshold,
            cells=kept,
            grid_description=f"{self.grid_description}(只看 {note} 這一片,裁決在整個格上算)",
        )

    def cell_for(self, point: SweepPoint) -> CellVerdict:
        for cell in self.cells:
            if cell.point == point:
                return cell
        raise ContractViolation(f"這次掃描沒有 {point.label} 這一格")

    def top(self, count: int = 5) -> tuple[CellVerdict, ...]:
        """目標指標排頭幾格(只計有效格)。"""
        ranked = sorted(
            (c for c in self.valid_cells if c.value is not None),
            key=lambda c: c.value,
            reverse=True,
        )
        return tuple(ranked[: max(int(count), 0)])

    def thresholds_line(self) -> str:
        """把三個門檻印成一行——報告一定要印,否則裁決講不出根據。"""
        plateau = (
            f"{self.plateau_threshold:.6g}" if self.plateau_threshold is not None else "算不出"
        )
        return (
            f"目標指標 {self.objective}(越大越好);"
            f"無效格門檻 = 成交少於 {self.min_trades} 筆;"
            f"孤峰門檻 = 高出鄰域平均 {self.lonely_peak_margin:.6g} 以上;"
            f"平原高地 = 目標值排前 {(1.0 - self.plateau_quantile):.0%}"
            f"(分位 {self.plateau_quantile:.2f},即 {plateau} 以上)"
        )

    def summary(self) -> str:
        counts = {verdict: len(self._by(verdict)) for verdict in VERDICTS}
        parts = "、".join(f"{name} {counts[name]} 格" for name in VERDICTS if counts[name])
        return f"共 {len(self.cells)} 格:{parts}"


def _pick(cells: Sequence[CellVerdict], score) -> CellVerdict | None:
    """取分數最高那一格。**打和時取參數標籤排最前那一格**。

    這一句不是小事:兩格分數一模一樣時若然靠 ``hash`` 或者字典次序決定,同一份
    數據重跑兩次可以指向不同的格——「同一輸入得同一結果」那句話就不成立了。
    """
    if not cells:
        return None
    top = max(score(cell) for cell in cells)
    tied = [cell for cell in cells if score(cell) == top]
    return min(tied, key=lambda cell: cell.point.label)


def judge(
    scores: Sequence[CellScore] | Mapping[SweepPoint, CellScore],
    grid: SweepGrid,
    *,
    objective: str,
    min_trades: int,
    lonely_peak_margin: float,
    plateau_quantile: float,
) -> SweepJudgement:
    """逐格判平原 / 孤峰 / 無效,交回整份裁決。

    判法,按次序:

    1. **無效格**先剔走:成交筆數少於 ``min_trades``,或者目標指標算不出。無效格
       之後一概不用——不入最優,亦不入任何一格的鄰域平均。
    2. **鄰域平均**:由 ``grid.neighbours()`` 取那一格的相鄰格(二維 3×3、單純形
       格是權重移一步的鄰居),只計有效的鄰居,連自己一齊平均。
    3. **孤峰**:這一格比全部有效鄰居都高(是個峰),而且高出鄰域平均多過
       ``lonely_peak_margin``。當擬合噪音(D-016 第 3 條)。
    4. **平原**:不是孤峰,而且**自己與鄰域平均兩者都在高地**(目標值不低於
       ``plateau_quantile`` 分位)。四周同樣好才算平原,這正是穩健的意思。
    5. 其餘是**普通**格;有效但一個有效鄰居都沒有的,標**無鄰**——判不出穩健
       與否,不當它平原,亦不冤枉它是孤峰。
    """
    items = list(scores.values()) if isinstance(scores, Mapping) else list(scores)
    if not items:
        raise ContractViolation("一格成績都沒有,判不出東西")

    name = str(objective or "").strip()
    if not name:
        raise ContractViolation("目標指標要寫明;判讀不設預設指標")
    floor = int(min_trades)
    if floor < 0:
        raise ContractViolation(f"成交筆數門檻不可為負,收到 {min_trades!r}")
    margin = float(lonely_peak_margin)
    if margin < 0.0:
        raise ContractViolation(
            f"孤峰門檻不可為負,收到 {lonely_peak_margin!r};負門檻會把整個高地都判成孤峰"
        )
    quantile = float(plateau_quantile)
    if not (0.0 <= quantile <= 1.0):
        raise ContractViolation(f"平原分位要在 0 與 1 之間,收到 {plateau_quantile!r}")

    table: dict[SweepPoint, CellScore] = {}
    for score in items:
        if score.point in table:
            raise ContractViolation(f"同一格出現兩次:{score.point.label}")
        table[score.point] = score

    valid: dict[SweepPoint, float] = {}
    for point, score in table.items():
        if score.trades < floor or score.value is None:
            continue
        valid[point] = float(score.value)

    plateau_threshold: float | None = None
    if valid:
        plateau_threshold = float(pd.Series(list(valid.values())).quantile(quantile))

    cells: list[CellVerdict] = []
    for point in grid.points():
        score = table.get(point)
        if score is None:
            continue  # 這個格未掃過(例如中途停手);報告會講明掃了幾多格
        neighbours = tuple(n for n in grid.neighbours(point) if n in table)
        neighbour_values = tuple(valid[n] for n in neighbours if n in valid)

        if point not in valid:
            cells.append(
                CellVerdict(
                    point=point,
                    value=score.value,
                    trades=score.trades,
                    verdict=INVALID,
                    neighbours=neighbours,
                    neighbour_values=neighbour_values,
                    neighbourhood_mean=None,
                    neighbour_mean=None,
                    lift=None,
                    ratio=None,
                    is_local_peak=False,
                )
            )
            continue

        value = valid[point]
        if neighbour_values:
            neighbour_mean = float(sum(neighbour_values) / len(neighbour_values))
            pool = (value, *neighbour_values)
            neighbourhood_mean = float(sum(pool) / len(pool))
            lift = float(value - neighbourhood_mean)
            # 「峰值為鄰域幾多倍」是 KARST-013 那次的講法(規格 6.5 引的 1.39 倍)。
            # 鄰域平均是零或負數時,倍數會失真甚至變號——那時寧可不給,只看落差。
            ratio = float(value / neighbourhood_mean) if neighbourhood_mean > 0.0 else None
            is_peak = all(value > other for other in neighbour_values)
        else:
            neighbour_mean = None
            neighbourhood_mean = None
            lift = None
            ratio = None
            is_peak = False

        if neighbourhood_mean is None:
            verdict = NO_NEIGHBOUR
        elif is_peak and lift is not None and lift > margin:
            verdict = LONELY_PEAK
        elif (
            plateau_threshold is not None
            and value >= plateau_threshold
            and neighbourhood_mean >= plateau_threshold
        ):
            verdict = PLATEAU
        else:
            verdict = ORDINARY

        cells.append(
            CellVerdict(
                point=point,
                value=value,
                trades=score.trades,
                verdict=verdict,
                neighbours=neighbours,
                neighbour_values=neighbour_values,
                neighbourhood_mean=neighbourhood_mean,
                neighbour_mean=neighbour_mean,
                lift=lift,
                ratio=ratio,
                is_local_peak=is_peak,
            )
        )

    return SweepJudgement(
        objective=name,
        min_trades=floor,
        lonely_peak_margin=margin,
        plateau_quantile=quantile,
        plateau_threshold=plateau_threshold,
        cells=tuple(cells),
        grid_description=grid.describe(),
    )
