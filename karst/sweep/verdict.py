"""判讀:平原、山脊、孤峰、無效格。

D-016 第 3 條與規格 6.5 的判準是**參數穩健平原**——最優那一格的鄰域表現皆佳
才算穩健;峰值明顯高於鄰域的當擬合噪音,叫孤峰。KARST-013 那次 144 組示範就是
這樣判的:單點最優夏普 1.61,3×3 鄰域平均只有 1.16,故判孤峰。

**鄰域只沿連續軸取**(KARST-047)。掃描格每條軸自報軸型(見 ``karst.sweep.grid``):
回望期那一類是**連續軸**,鄰格是真的一步之遙;持現金/均分、月度/季度那一類是
**選擇軸**,換一個取值即換一套做法。選擇軸不入鄰域,而是把格切成一層層,每層
各出一份平原判讀。兩者混在同一個鄰域平均裡會出事:KARST-043 的相對強弱驅動器
沿回望期 6 至 9 個月全部在 +2.8% 以上,卻因為鄰域把「均分」與「季度」那幾片
一齊算進去,整條山脊被判成孤峰。

於是多一種裁決:

``山脊``
    沿連續軸站得住(自己與鄰域平均**兩者都在高地**),但**同一格換另一層即跌穿
    平原門檻**。它不是平原(換一套做法就沒有了),亦不是孤峰(回望期揀錯一兩格
    不要緊)。KARST-043 那條 6 至 9 個月的山脊,正是這種形狀。

裁決的先後**不變**:孤峰仍然先判。一格沿連續軸自己都是尖的(高出鄰域平均多過
門檻),那就是孤峰,不會因為它所在的層是高地而改叫山脊——「沿連續軸平順」是
山脊的前提,而那個門檻正是量它平不平順的尺。山脊只從本來會判平原的那批格裡分
出來,所以**沒有選擇軸的格(例如 3×3 規則型)判讀逐位不變**。

本檔把那次一次性的判法寫成規矩,三個門檻**一個預設值都沒有**:

``min_trades``
    成交筆數少過這個數的格判**無效**。無效格不入最優、不入任何鄰域平均——
    一格只成交過兩次,那個回報數字講的是運氣,不是這組參數。

``lonely_peak_margin``
    「明顯高於」高幾多才算。單位就是目標指標自己的單位(年化超額用的是小數,
    0.02 即兩個百分點)。KARST-013 那次的落差是 0.45 個夏普。

``plateau_quantile``
    高地由哪一個分位起計。0.9 即「有效格之中目標值排前一成」。**高地門檻在整個
    格上算一次,不逐層另計**——每一層各有自己的前一成,會令最差那一層都排得出
    「平原」,那就不是高地,只是矮子裡拔將軍。

本檔**不裁定哪一格該用**(D-008):它只把每格貼上一個標籤,最優與最穩健兩格
並列交出,揀哪一格是用戶的事。

一句講清楚方向:**目標指標一律「越大越好」**。最大回撤在本倉一路以負數表示
(-0.23 即跌兩成三),所以「越大」剛好就是「跌得越少」,不用另設一個方向參數。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

import pandas as pd

from ..errors import ContractViolation
from .grid import LayerKey, SweepGrid, SweepPoint, layer_label

# 裁決標籤。無效格永不參與其餘各種判讀。
PLATEAU: Final[str] = "平原"
RIDGE: Final[str] = "山脊"
LONELY_PEAK: Final[str] = "孤峰"
ORDINARY: Final[str] = "普通"
INVALID: Final[str] = "無效"
NO_NEIGHBOUR: Final[str] = "無鄰"

VERDICTS: Final[tuple[str, ...]] = (
    PLATEAU,
    RIDGE,
    LONELY_PEAK,
    ORDINARY,
    INVALID,
    NO_NEIGHBOUR,
)


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

    ``neighbourhood_mean`` **包含自己那一格**(全連續軸的二維格即整個 3×3 九格的
    平均),與規格 6.5、KARST-013 那次的講法一致;``neighbour_mean`` 是**不含自己**
    的鄰居平均,想看純粹的四周有幾好時用它。兩個都列出來,免得下一個人要猜是
    哪一個。**兩個都只沿連續軸算**(KARST-047)。

    ``layer`` 是這一格所在的那一層(選擇軸的一組取值);沒有選擇軸就是空的。
    ``weakest_sibling_mean`` 是**同一組連續軸取值、換去其他每一層**之中最差的那個
    鄰域平均——山脊與平原之分就在這個數:它跌穿高地門檻,即是「換一套做法就沒有
    了」。``layer_drop`` 是自己的鄰域平均減它,即換層要付的代價。
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
    layer: LayerKey = ()
    sibling_means: tuple[float, ...] = ()
    weakest_sibling_mean: float | None = None
    layer_drop: float | None = None

    @property
    def valid(self) -> bool:
        return self.verdict != INVALID

    @property
    def layer_name(self) -> str:
        """這一格所在那一層的人話名。"""
        return layer_label(self.layer)

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
                "layer": self.layer_name,
                "siblings": len(self.sibling_means),
                "weakest_sibling_mean": self.weakest_sibling_mean,
                "layer_drop": self.layer_drop,
            }
        )
        return row


@dataclass(frozen=True, slots=True)
class SweepJudgement:
    """一次掃描判完之後的全部結果。

    ``best`` 是有效格之中目標指標最高那一格(單點最優);``most_robust`` 是鄰域
    平均最高那一格——**穩健平原的中心**。兩格不同,通常就是在講單點最優靠不住。

    ``choice_axes`` 是把這個格切成一層層的那幾條選擇軸;``layers()`` 逐層交出一份
    切片,報告與投影圖按層分開出(KARST-047)。
    """

    objective: str
    min_trades: int
    lonely_peak_margin: float
    plateau_quantile: float
    plateau_threshold: float | None
    cells: tuple[CellVerdict, ...]
    grid_description: str
    choice_axes: tuple[str, ...] = ()
    axes_description: str = ""

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
    def ridges(self) -> tuple[CellVerdict, ...]:
        """山脊:沿連續軸站得住,換一層即跌穿門檻(KARST-047)。"""
        return self._by(RIDGE)

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
            choice_axes=self.choice_axes,
            axes_description=self.axes_description,
        )

    def layer_keys(self) -> tuple[LayerKey, ...]:
        """整個格切出來的層,次序按掃描次序首次出現。沒有選擇軸即只有一層。"""
        seen: list[LayerKey] = []
        for cell in self.cells:
            if cell.layer not in seen:
                seen.append(cell.layer)
        return tuple(seen)

    def layer(self, key: LayerKey) -> "SweepJudgement":
        """揀出一層。

        **裁決不重判**:每一格的標籤與鄰域平均本來就是在自己那一層之內算的(鄰域
        只沿連續軸取),高地門檻則在整個格上算——所以這裡揀出來的,正正是那一層
        的判讀,不是另一套數。
        """
        wanted = tuple(key)
        kept = tuple(cell for cell in self.cells if cell.layer == wanted)
        if not kept:
            raise ContractViolation(
                f"切不出這一層:{layer_label(wanted)};"
                f"有的層是:{'、'.join(layer_label(k) for k in self.layer_keys())}"
            )
        return SweepJudgement(
            objective=self.objective,
            min_trades=self.min_trades,
            lonely_peak_margin=self.lonely_peak_margin,
            plateau_quantile=self.plateau_quantile,
            plateau_threshold=self.plateau_threshold,
            cells=kept,
            grid_description=(
                f"{self.grid_description}(只看「{layer_label(wanted)}」這一層;"
                "鄰域本來就只沿連續軸取,高地門檻在整個格上算)"
            ),
            choice_axes=self.choice_axes,
            axes_description=self.axes_description,
        )

    def layers(self) -> tuple[tuple[LayerKey, "SweepJudgement"], ...]:
        """逐層一份判讀,報告與投影圖分開出的入口。"""
        return tuple((key, self.layer(key)) for key in self.layer_keys())

    def layer_frame(self) -> pd.DataFrame:
        """**分層判讀表**:一層一行,各層的裁決分佈與最好那一格。

        選擇軸的整件事就在這張表上——同一條連續軸,換一層之後高地還在不在。
        """
        rows: list[dict[str, Any]] = []
        for key in self.layer_keys():
            slice_ = self.layer(key)
            valid = [c for c in slice_.valid_cells if c.value is not None]
            best = slice_.best
            robust = slice_.most_robust
            row: dict[str, Any] = {name: value for name, value in key}
            row["層"] = layer_label(key)
            row["格數"] = len(slice_)
            row["有效格"] = len(valid)
            for name in VERDICTS:
                row[name] = len(slice_._by(name))
            row["最優"] = best.value if best is not None else None
            row["最優參數"] = best.point.label if best is not None else None
            row["鄰域平均最高"] = (
                robust.neighbourhood_mean if robust is not None else None
            )
            row["層平均"] = (
                float(sum(c.value for c in valid) / len(valid)) if valid else None
            )
            row["高地格數"] = (
                sum(
                    1
                    for c in valid
                    if self.plateau_threshold is not None
                    and c.value >= self.plateau_threshold
                )
                if self.plateau_threshold is not None
                else 0
            )
            rows.append(row)
        return pd.DataFrame(rows)

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

    def axes_line(self) -> str:
        """報告要印的一句:哪幾條軸是連續、哪幾條是選擇、山脊怎樣判。"""
        if not self.choice_axes:
            return (
                "軸型:全部連續軸,只有一層;鄰域沿全部軸取,判讀與規格 6.5 的 3×3 一樣,"
                "不會出現山脊"
            )
        described = self.axes_description or (
            "選擇軸:" + "、".join(self.choice_axes) + ";鄰域只沿連續軸取,選擇軸逐層分開判"
        )
        return (
            f"{described}(切出 {len(self.layer_keys())} 層);"
            "**山脊** = 沿連續軸自己與鄰域平均都在高地,但同一組連續軸取值換去另一層"
            "即跌穿高地門檻"
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
    """逐格判平原 / 山脊 / 孤峰 / 無效,交回整份裁決。

    判法,按次序:

    1. **無效格**先剔走:成交筆數少於 ``min_trades``,或者目標指標算不出。無效格
       之後一概不用——不入最優,亦不入任何一格的鄰域平均。
    2. **鄰域平均**:由 ``grid.neighbours()`` 取那一格的相鄰格(**只沿連續軸**;
       全連續軸的二維格即 3×3,單純形格是權重移一步的鄰居),只計有效的鄰居,
       連自己一齊平均。選擇軸不入鄰域——鄰居永遠與自己同一層。
    3. **孤峰**:這一格比全部有效鄰居都高(是個峰),而且高出鄰域平均多過
       ``lonely_peak_margin``。當擬合噪音(D-016 第 3 條)。
    4. **山脊**:不是孤峰,自己與鄰域平均兩者都在高地(不低於
       ``plateau_quantile`` 分位),**但同一組連續軸取值換去另一層之後,那一格的
       鄰域平均跌穿高地門檻**。即是話沿連續軸站得住,換一套做法就沒有了。
    5. **平原**:同上,而且換去每一層都站得住(或者根本沒有選擇軸)。四周同樣好、
       換一套做法一樣好,才算平原,這正是穩健的意思。
    6. 其餘是**普通**格;有效但一個有效鄰居都沒有的,標**無鄰**——判不出穩健
       與否,不當它平原,亦不冤枉它是孤峰。

    第 4 步只在有選擇軸時才可能成立,所以**沒有選擇軸的格判讀逐位不變**。換層
    比較時,對不上的層(那一格未掃過、或者判了無效)一律略過:沒有數就是沒有數,
    不當它跌穿。
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

    # 第一轉:逐格算鄰域平均(只沿連續軸)。山脊要拿同一組連續軸取值在**別的層**
    # 的鄰域平均來比,所以一定要先把全部算好,才判得出標籤。
    choice_axes = tuple(grid.choice_axes)
    spine_index: dict[tuple[tuple[str, Any], ...], dict[LayerKey, SweepPoint]] = {}
    means: dict[SweepPoint, float] = {}
    for point in grid.points():
        if point not in table:
            continue
        spine = tuple((n, v) for n, v in point.values if n not in set(choice_axes))
        spine_index.setdefault(spine, {})[grid.layer_of(point)] = point
        if point not in valid:
            continue
        around = [valid[n] for n in grid.neighbours(point) if n in valid]
        if not around:
            continue  # 一個有效鄰居都沒有 = 無鄰,判不出穩健與否,不拿來做比較
        pool = [valid[point], *around]
        means[point] = float(sum(pool) / len(pool))

    cells: list[CellVerdict] = []
    for point in grid.points():
        score = table.get(point)
        if score is None:
            continue  # 這個格未掃過(例如中途停手);報告會講明掃了幾多格
        neighbours = tuple(n for n in grid.neighbours(point) if n in table)
        neighbour_values = tuple(valid[n] for n in neighbours if n in valid)
        layer = grid.layer_of(point)

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
                    layer=layer,
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

        # 同一組連續軸取值,換去其他每一層的那一格:比得了的才算數(未掃過、
        # 判了無效的一律略過——沒有數就是沒有數,不當它跌穿)。
        spine = tuple((n, v) for n, v in point.values if n not in set(choice_axes))
        sibling_means = tuple(
            means[other]
            for other_layer, other in spine_index.get(spine, {}).items()
            if other_layer != layer and other in means
        )
        weakest = min(sibling_means) if sibling_means else None
        layer_drop = (
            float(neighbourhood_mean - weakest)
            if weakest is not None and neighbourhood_mean is not None
            else None
        )
        on_high_ground = (
            plateau_threshold is not None
            and neighbourhood_mean is not None
            and value >= plateau_threshold
            and neighbourhood_mean >= plateau_threshold
        )

        if neighbourhood_mean is None:
            verdict = NO_NEIGHBOUR
        elif is_peak and lift is not None and lift > margin:
            verdict = LONELY_PEAK
        elif on_high_ground:
            # 高地上的格,再問一句:換一層還企唔企得穩。企不穩的是山脊,不是平原。
            falls = (
                plateau_threshold is not None
                and weakest is not None
                and weakest < plateau_threshold
            )
            verdict = RIDGE if falls else PLATEAU
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
                layer=layer,
                sibling_means=sibling_means,
                weakest_sibling_mean=weakest,
                layer_drop=layer_drop,
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
        choice_axes=choice_axes,
        axes_description=grid.axes_line(),
    )
