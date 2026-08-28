"""掃描格(sweep grid):一次參數掃描要走哪些格,以及哪兩格算相鄰。

**相鄰的定義是判讀的地基**。參數穩健平原(D-016 第 3 條、規格 6.5)判的是
「最優那一格的鄰域是不是同樣好」——鄰域一改,平原與孤峰的裁決就跟住改。所以
本檔把每種格的相鄰定義寫死並寫明,報告亦一定要把它印出來(``describe()``)。

**每條軸自報軸型**(KARST-047):

``連續軸``(continuous axis)
    回望期、均線日數那一類:軸上相鄰兩個取值是**真的一步之遙**,「移一步」有
    刻度上的意思。鄰域只沿這種軸取。

``選擇軸``(choice axis)
    持現金/均分、月度/季度那一類:換一個取值是**換一套做法**,不是微調。這種
    軸**不入鄰域**——它把整個格切成幾片(**層**,layer),每一層各自出一份平原
    判讀。把兩種軸混在同一個鄰域平均裡,一條真山脊會被判成孤峰:KARST-043 的
    相對強弱驅動器沿回望期 6 至 9 個月全部在 +2.8% 以上,卻因為鄰域把「均分」與
    「季度」兩片一齊算進去而判了孤峰。

軸型**預設連續**——舊有的格一個字不用改,判讀逐位不變(規格 6.5 的 3×3 仍然是
3×3)。要分層的格請明寫 ``kind=CHOICE``。

三種格:

``ProductGrid``
    逐軸取值的笛卡兒積。相鄰 = **每條連續軸最多移一步、且不可全部不動,選擇軸
    釘死不動**——全部軸皆連續的二維格,即是經典的 3×3 鄰域(自己加八個鄰居,
    規格 6.5)。

``SimplexGrid``
    權重單純形格:一堆權重,每個是步長的整數倍,加總剛好一。相鄰 = **把一步
    的權重由其中一格移去另一格**(``+step`` / ``-step`` 各一個,其餘不動)。
    四格權重最多十二個鄰居。笛卡兒積在這裡用不著:加總必須為一,絕大部分組合
    根本不是有效的權重。

``CompositeGrid``
    幾個格拼起來(例如「權重單純形格 × 換倉節奏一維」)。相鄰 = 每個成分格各自
    「移一步或者不動」,但不可以全部不動。兩個一維 ``ProductGrid`` 拼起來,
    拼出來的鄰域與一個二維 ``ProductGrid`` 的 3×3 一模一樣——三種格的相鄰
    定義是同一套規矩的三個樣子,不是三套。

無效的格不入格(單純形格不會排出加總不等於一的格),但**一格跑出來算不算數**
不在本檔:成交筆數太少那一類判無效,住在 ``karst.sweep.verdict``。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from typing import Any, Final

from ..errors import ContractViolation

# 權重換算成整數步數時容許的浮點尾數。只擋尾數,不當「差不多就當一步」。
_STEP_TOLERANCE = 1e-9

# 兩種軸型。**連續軸**上「移一步」有刻度上的意思(回望期由 6 個月到 7 個月);
# **選擇軸**換一個取值即換一套做法(持現金改成均分),鄰格是另一個世界。
CONTINUOUS: Final[str] = "連續"
CHOICE: Final[str] = "選擇"
AXIS_KINDS: Final[tuple[str, ...]] = (CONTINUOUS, CHOICE)

# 一層(layer)= 選擇軸的一組取值。沒有選擇軸即整個格只有一層,那一層的鍵是空的。
LayerKey = tuple[tuple[str, Any], ...]


def layer_label(key: LayerKey) -> str:
    """一層的人話名:``fallback=cash、cadence=monthly``;沒有選擇軸就是「全格」。"""
    if not key:
        return "全格(沒有選擇軸)"
    return "、".join(f"{name}={_format_value(value)}" for name, value in key)


def layer_slug(key: LayerKey) -> str:
    """一層的機器名(檔名用):``fallback-cash-cadence-monthly``。"""
    if not key:
        return "全格"
    return "-".join(f"{name}-{_slug_value(value)}" for name, value in key)


def _clean_name(name: Any, label: str = "參數名") -> str:
    text = str(name or "").strip()
    if not text:
        raise ContractViolation(f"{label}不可留空")
    return text


def _format_value(value: Any) -> str:
    """把一個取值印成人看得明、機器又對得回的樣子。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        number = float(value)
        if abs(number - round(number)) < _STEP_TOLERANCE:
            return str(int(round(number)))
        return f"{number:g}"
    return str(value)


def _slug_value(value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if 0.0 <= number <= 1.0:
            # 權重那一類:印成百分點,10% 就是 10,看得懂又不會撞名。
            percent = number * 100.0
            if abs(percent - round(percent)) < 1e-6:
                return str(int(round(percent)))
            return f"{percent:g}".replace(".", "p")
        return _format_value(value).replace(".", "p").replace("-", "neg")
    return str(value).strip().replace(" ", "-")


@dataclass(frozen=True, slots=True)
class SweepPoint:
    """掃描格的一格:一組參數取值。

    ``values`` 是 ``(參數名, 取值)`` 的序對串,**次序由掃描格話事**——同一個格
    重掃一次,序對串一字不差,所以它可以直接做字典的鍵、做運行的查重依據。
    """

    values: tuple[tuple[str, Any], ...]

    def __post_init__(self) -> None:
        cleaned: list[tuple[str, Any]] = []
        seen: set[str] = set()
        for name, value in self.values:
            key = _clean_name(name)
            if key in seen:
                raise ContractViolation(f"一格之內參數「{key}」出現兩次")
            seen.add(key)
            cleaned.append((key, value))
        if not cleaned:
            raise ContractViolation("一格最少要有一個參數;空的格掃不出東西")
        object.__setattr__(self, "values", tuple(cleaned))

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.values)

    def get(self, name: str) -> Any:
        key = _clean_name(name)
        for candidate, value in self.values:
            if candidate == key:
                return value
        raise ContractViolation(f"這一格沒有參數「{key}」;有的是:{'、'.join(self.names)}")

    def as_dict(self) -> dict[str, Any]:
        return {name: value for name, value in self.values}

    def merge(self, other: "SweepPoint") -> "SweepPoint":
        return SweepPoint(values=self.values + other.values)

    @property
    def label(self) -> str:
        """人看的一行:``weight_quality=0.25、cadence=quarterly``。"""
        return "、".join(f"{name}={_format_value(value)}" for name, value in self.values)

    @property
    def slug(self) -> str:
        """機器用的短名(參數集命名、檔名):``quality25-value25-cadence-quarterly``。"""
        parts = []
        for name, value in self.values:
            short = name[len("weight_"):] if name.startswith("weight_") else name
            parts.append(f"{short}{_slug_value(value)}")
        return "-".join(parts)

    def __str__(self) -> str:  # pragma: no cover - 只為方便看
        return self.label


@dataclass(frozen=True, slots=True)
class SweepAxis:
    """掃描格的一個軸:一個參數,加它要掃的一串取值。

    ``ordered`` 預設為真——**軸上的取值按給出的次序當作有序**,相鄰即次序相差
    一格。換倉節奏由密到疏(月、季、年)就是這種軸。真正沒有次序的軸(例如三
    隻互不相干的基準)請寫 ``ordered=False``:那時同一軸的任何兩個取值皆相鄰,
    因為「移一步」在一個無序的軸上沒有意思。

    ``kind`` 是**軸型**,預設 ``CONTINUOUS``(連續):鄰域沿住它走。寫
    ``kind=CHOICE``(選擇)那一條軸就**退出鄰域**,改為把格切成幾層,每層各出
    一份判讀(KARST-047)。兩者是兩件事:``ordered`` 講「這條軸上一步是幾遠」,
    ``kind`` 講「這條軸該不該走一步」。選擇軸不走,所以它的 ``ordered`` 沒有作用。
    """

    name: str
    values: tuple[Any, ...]
    ordered: bool = True
    kind: str = CONTINUOUS

    @property
    def is_choice(self) -> bool:
        return self.kind == CHOICE

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _clean_name(self.name))
        kind = str(self.kind or "").strip()
        if kind not in AXIS_KINDS:
            raise ContractViolation(
                f"軸「{self.name}」的軸型只收 {'、'.join(AXIS_KINDS)},收到 {self.kind!r};"
                "連續軸(回望期一類)鄰格是一步之遙,選擇軸(持現金/均分一類)鄰格是另一個世界"
            )
        object.__setattr__(self, "kind", kind)
        items = tuple(self.values)
        if not items:
            raise ContractViolation(
                f"軸「{self.name}」一個取值都沒有;掃描不設預設值,要掃哪幾個一律寫明"
            )
        seen: list[Any] = []
        for item in items:
            if any(item == existing for existing in seen):
                raise ContractViolation(f"軸「{self.name}」的取值有重複:{_format_value(item)}")
            seen.append(item)
        object.__setattr__(self, "values", items)

    def __len__(self) -> int:
        return len(self.values)


class SweepGrid:
    """掃描格的共通門面:排得出全部格,講得出哪幾格與某一格相鄰。

    子類要實作 ``points()``、``neighbours()`` 與 ``describe()``。軸型預設全部連續
    ——**舊有的格不用改一個字**,鄰域與判讀逐位不變;要分層的格覆寫 ``axis_kinds``。
    """

    @property
    def axis_names(self) -> tuple[str, ...]:
        raise NotImplementedError

    @property
    def axis_kinds(self) -> dict[str, str]:
        """逐條軸的軸型。預設全部連續:沒有明寫的格,鄰域行為與從前一模一樣。"""
        return {name: CONTINUOUS for name in self.axis_names}

    @property
    def choice_axes(self) -> tuple[str, ...]:
        """選擇軸:不入鄰域,改為把格切成幾層。"""
        kinds = self.axis_kinds
        return tuple(name for name in self.axis_names if kinds.get(name) == CHOICE)

    @property
    def continuous_axes(self) -> tuple[str, ...]:
        """連續軸:鄰域只沿住這幾條走。"""
        kinds = self.axis_kinds
        return tuple(name for name in self.axis_names if kinds.get(name) != CHOICE)

    def axes_line(self) -> str:
        """報告要印的一句:每條軸是連續還是選擇。"""
        kinds = self.axis_kinds
        parts = "、".join(f"{name}({kinds.get(name, CONTINUOUS)})" for name in self.axis_names)
        tail = (
            f";鄰域只沿連續軸取,選擇軸({'、'.join(self.choice_axes)})逐層分開判"
            if self.choice_axes
            else ";全部是連續軸,只有一層"
        )
        return f"軸型:{parts}{tail}"

    def layer_of(self, point: SweepPoint) -> LayerKey:
        """這一格屬於哪一層(選擇軸的一組取值)。沒有選擇軸就是空的那一層。"""
        return tuple((name, point.get(name)) for name in self.choice_axes)

    def layers(self) -> tuple[LayerKey, ...]:
        """整個格切出來的層,次序按掃描次序首次出現。"""
        seen: list[LayerKey] = []
        for point in self.points():
            key = self.layer_of(point)
            if key not in seen:
                seen.append(key)
        return tuple(seen)

    def points(self) -> tuple[SweepPoint, ...]:
        raise NotImplementedError

    def neighbours(self, point: SweepPoint) -> tuple[SweepPoint, ...]:
        raise NotImplementedError

    def describe(self) -> str:
        """一句講清楚這個格是什麼、相鄰怎樣定義。報告一定要印這一句。"""
        raise NotImplementedError

    def __len__(self) -> int:
        return len(self.points())

    def contains(self, point: SweepPoint) -> bool:
        return point in set(self.points())

    def neighbour_map(self) -> dict[SweepPoint, tuple[SweepPoint, ...]]:
        """整個格的鄰接表。判讀一次過取,不用逐格再算。"""
        return {point: self.neighbours(point) for point in self.points()}


class ProductGrid(SweepGrid):
    """逐軸取值的笛卡兒積。相鄰 = 每條**連續軸**最多移一步,且不可全部不動。

    全部軸皆連續的二維格,鄰域就是規格 6.5 講的 3×3(中心格加八個鄰居);邊角的
    格鄰居少些——那是事實,不補格、不繞回對邊。

    **選擇軸釘死不動**:鄰居永遠與自己同一層。所以一個「回望期(連續)× 退路
    (選擇)× 節奏(選擇)」的格,某一格的鄰居只有回望期前後那兩格,而不是
    七格——這正是 KARST-047 要修的那件事。
    """

    def __init__(self, axes: Sequence[SweepAxis]) -> None:
        items = tuple(axes)
        if not items:
            raise ContractViolation("笛卡兒積格最少要有一個軸")
        names = [axis.name for axis in items]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ContractViolation(f"軸名重複:{'、'.join(duplicates)}")
        self._axes = items

    @property
    def axes(self) -> tuple[SweepAxis, ...]:
        return self._axes

    @property
    def axis_names(self) -> tuple[str, ...]:
        return tuple(axis.name for axis in self._axes)

    @property
    def axis_kinds(self) -> dict[str, str]:
        return {axis.name: axis.kind for axis in self._axes}

    def points(self) -> tuple[SweepPoint, ...]:
        return tuple(
            SweepPoint(
                values=tuple(
                    (axis.name, value) for axis, value in zip(self._axes, combo, strict=True)
                )
            )
            for combo in product(*(axis.values for axis in self._axes))
        )

    def _indices(self, point: SweepPoint) -> tuple[int, ...]:
        out: list[int] = []
        for axis in self._axes:
            value = point.get(axis.name)
            matched = [i for i, candidate in enumerate(axis.values) if candidate == value]
            if not matched:
                raise ContractViolation(
                    f"取值 {_format_value(value)} 不在軸「{axis.name}」的掃描取值裡"
                )
            out.append(matched[0])
        return tuple(out)

    def neighbours(self, point: SweepPoint) -> tuple[SweepPoint, ...]:
        base = self._indices(point)
        choices: list[list[int]] = []
        for axis, index in zip(self._axes, base, strict=True):
            if axis.is_choice:
                # 選擇軸不移動:鄰居永遠與自己同一層(KARST-047)。
                choices.append([index])
            elif axis.ordered:
                choices.append(
                    [i for i in (index - 1, index, index + 1) if 0 <= i < len(axis.values)]
                )
            else:
                choices.append(list(range(len(axis.values))))
        out: list[SweepPoint] = []
        for combo in product(*choices):
            if combo == base:
                continue
            out.append(
                SweepPoint(
                    values=tuple(
                        (axis.name, axis.values[i])
                        for axis, i in zip(self._axes, combo, strict=True)
                    )
                )
            )
        return tuple(out)

    def describe(self) -> str:
        shape = " × ".join(f"{axis.name}({len(axis)})" for axis in self._axes)
        unordered = [axis.name for axis in self._axes if not axis.ordered and not axis.is_choice]
        note = ""
        if unordered:
            note = f";無序軸({'、'.join(unordered)})同軸任意兩個取值皆相鄰"
        choices = self.choice_axes
        if choices:
            spine = len(self._axes) - len(choices)
            rule = (
                f"相鄰 = 每條連續軸最多移一步且不可全部不動,選擇軸釘死不動"
                f"({spine} 條連續軸;選擇軸 {'、'.join(choices)} 切出 {len(self.layers())} 層,"
                "每層各出一份判讀)"
            )
        else:
            rule = (
                f"相鄰 = 每個軸最多移一步且不可全部不動"
                f"({'二維即 3×3 鄰域' if len(self._axes) == 2 else f'{len(self._axes)} 維'})"
            )
        return (
            f"笛卡兒積格 {shape},共 {len(self.points())} 格;{rule}{note};{self.axes_line()}"
        )


class SimplexGrid(SweepGrid):
    """權重單純形格:每個權重是步長的整數倍,加總剛好一。

    步長 10% 配四個權重就是 286 格(把十步分去四格的所有分法),5% 是 1771 格。
    相鄰 = **把一步的權重由其中一格移去另一格**:一個 ``+step``、一個 ``-step``,
    其餘不動。這是單純形上「移一步」的唯一講得通的意思——笛卡兒積式的
    「每格各自 ±一步」會走出加總不等於一的格,那些格根本不是有效的權重。

    ``total`` 可以少於一(餘下的持現金),但每一格的權重加總永遠等於 ``total``。
    """

    def __init__(
        self,
        keys: Sequence[str],
        *,
        step: float,
        total: float = 1.0,
    ) -> None:
        names = tuple(_clean_name(key, "權重參數名") for key in keys)
        if len(names) < 2:
            raise ContractViolation("單純形格最少要兩個權重;一個權重沒有東西可以互相調配")
        if len(set(names)) != len(names):
            raise ContractViolation(f"權重參數名重複:{'、'.join(names)}")

        step_value = float(step)
        if not (0.0 < step_value <= 1.0):
            raise ContractViolation(f"步長要在 0 與 1 之間,收到 {step!r}")
        total_value = float(total)
        if not (0.0 < total_value <= 1.0):
            raise ContractViolation(f"權重加總要在 0 與 1 之間,收到 {total!r}")
        steps = total_value / step_value
        if abs(steps - round(steps)) > 1e-6:
            raise ContractViolation(
                f"步長 {step_value} 除不盡加總 {total_value};"
                "步長要令加總剛好走得完整數步,否則排不出加總等於一的格"
            )

        self._keys = names
        self._step = step_value
        self._total = total_value
        self._steps = int(round(steps))

    @property
    def keys(self) -> tuple[str, ...]:
        return self._keys

    @property
    def step(self) -> float:
        return self._step

    @property
    def total(self) -> float:
        return self._total

    @property
    def total_steps(self) -> int:
        return self._steps

    @property
    def axis_names(self) -> tuple[str, ...]:
        return self._keys

    def _compositions(self) -> tuple[tuple[int, ...], ...]:
        """把 ``total_steps`` 步分去 ``len(keys)`` 格的所有分法,次序固定。"""
        slots = len(self._keys)

        def walk(remaining: int, left: int) -> Iterable[tuple[int, ...]]:
            if left == 1:
                yield (remaining,)
                return
            for take in range(remaining + 1):
                for rest in walk(remaining - take, left - 1):
                    yield (take, *rest)

        return tuple(walk(self._steps, slots))

    def _to_point(self, steps: Sequence[int]) -> SweepPoint:
        return SweepPoint(
            values=tuple(
                (key, round(count * self._step, 10))
                for key, count in zip(self._keys, steps, strict=True)
            )
        )

    def _to_steps(self, point: SweepPoint) -> tuple[int, ...]:
        out: list[int] = []
        for key in self._keys:
            value = float(point.get(key))
            count = value / self._step
            if abs(count - round(count)) > 1e-6:
                raise ContractViolation(
                    f"權重「{key}」= {value} 不是步長 {self._step} 的整數倍,不在這個單純形格上"
                )
            out.append(int(round(count)))
        if sum(out) != self._steps:
            raise ContractViolation(
                f"這一格的權重加總是 {sum(out) * self._step},不是 {self._total};"
                "單純形格每一格的加總都一樣"
            )
        return tuple(out)

    def points(self) -> tuple[SweepPoint, ...]:
        return tuple(self._to_point(steps) for steps in self._compositions())

    def neighbours(self, point: SweepPoint) -> tuple[SweepPoint, ...]:
        base = list(self._to_steps(point))
        out: list[SweepPoint] = []
        for source in range(len(base)):
            if base[source] < 1:
                continue
            for target in range(len(base)):
                if target == source:
                    continue
                moved = list(base)
                moved[source] -= 1
                moved[target] += 1
                out.append(self._to_point(moved))
        return tuple(out)

    def describe(self) -> str:
        return (
            f"權重單純形格:{len(self._keys)} 個權重"
            f"({'、'.join(self._keys)}),步長 {self._step:.0%},加總 {self._total:.0%},"
            f"共 {len(self.points())} 格;"
            "相鄰 = 把一步的權重由其中一格移去另一格(一個 +一步、一個 −一步,其餘不動)"
        )


class CompositeGrid(SweepGrid):
    """幾個格拼起來,例如「權重單純形格 × 換倉節奏一維」。

    相鄰 = **每個成分格各自「移一步或者不動」,但不可以全部不動**。這條規矩把
    另外兩種格接得上:兩個一維 ``ProductGrid`` 拼起來,鄰域就是二維的 3×3。
    """

    def __init__(self, parts: Sequence[SweepGrid]) -> None:
        items = tuple(parts)
        if len(items) < 2:
            raise ContractViolation("拼合格最少要兩個成分格;一個的話直接用那個就好")
        names: list[str] = []
        for part in items:
            names.extend(part.axis_names)
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ContractViolation(f"成分格之間參數名重複:{'、'.join(duplicates)}")
        self._parts = items

    @property
    def parts(self) -> tuple[SweepGrid, ...]:
        return self._parts

    @property
    def axis_names(self) -> tuple[str, ...]:
        out: list[str] = []
        for part in self._parts:
            out.extend(part.axis_names)
        return tuple(out)

    @property
    def axis_kinds(self) -> dict[str, str]:
        """成分格各自報自己那幾條軸的軸型;拼合格不改寫任何一條。"""
        out: dict[str, str] = {}
        for part in self._parts:
            out.update(part.axis_kinds)
        return out

    def points(self) -> tuple[SweepPoint, ...]:
        out: list[SweepPoint] = []
        for combo in product(*(part.points() for part in self._parts)):
            merged = combo[0]
            for extra in combo[1:]:
                merged = merged.merge(extra)
            out.append(merged)
        return tuple(out)

    def _split(self, point: SweepPoint) -> tuple[SweepPoint, ...]:
        table = point.as_dict()
        out: list[SweepPoint] = []
        for part in self._parts:
            missing = [name for name in part.axis_names if name not in table]
            if missing:
                raise ContractViolation(f"這一格缺參數:{'、'.join(missing)}")
            out.append(SweepPoint(values=tuple((name, table[name]) for name in part.axis_names)))
        return tuple(out)

    def neighbours(self, point: SweepPoint) -> tuple[SweepPoint, ...]:
        pieces = self._split(point)
        choices = [
            (piece, *part.neighbours(piece))
            for part, piece in zip(self._parts, pieces, strict=True)
        ]
        out: list[SweepPoint] = []
        for combo in product(*choices):
            if all(chosen == piece for chosen, piece in zip(combo, pieces, strict=True)):
                continue
            merged = combo[0]
            for extra in combo[1:]:
                merged = merged.merge(extra)
            out.append(merged)
        return tuple(out)

    def describe(self) -> str:
        inner = ";".join(part.describe() for part in self._parts)
        return (
            f"拼合格({len(self._parts)} 個成分格,共 {len(self.points())} 格)"
            f"——相鄰 = 每個成分格各自移一步或者不動,但不可全部不動;{self.axes_line()}。"
            f"成分格:{inner}"
        )


class ExplicitGrid(SweepGrid):
    """點名要跑哪幾格,**不設鄰域**——對照格用的。

    「固定各 25%」那一類對照,常常根本不在掃描格上(10% 步長就排不出各 25%)。
    它照樣要跑、要落痕、要有運行編號,好讓報告答得出「掃出來的最優,贏了固定
    比重幾多」;但它沒有四周可比,所以這裡的鄰域一律是空的,判讀會把它標成
    **無鄰**而不是平原——不冤枉它,亦不替它充穩健。
    """

    def __init__(self, points: Sequence[SweepPoint], *, label: str = "對照格") -> None:
        items = tuple(points)
        if not items:
            raise ContractViolation("顯式格最少要一格")
        names = items[0].names
        for point in items[1:]:
            if point.names != names:
                raise ContractViolation(
                    f"顯式格每一格的參數名要一樣:{names} 對 {point.names}"
                )
        if len(set(items)) != len(items):
            raise ContractViolation("顯式格有重複的格")
        self._points = items
        self._label = str(label).strip() or "對照格"

    @property
    def axis_names(self) -> tuple[str, ...]:
        return self._points[0].names

    def points(self) -> tuple[SweepPoint, ...]:
        return self._points

    def neighbours(self, point: SweepPoint) -> tuple[SweepPoint, ...]:
        return ()

    def describe(self) -> str:
        return f"{self._label}:點名的 {len(self._points)} 格,不設鄰域(判不出穩健與否)"


def product_grid(**axes: Sequence[Any]) -> ProductGrid:
    """砌一個笛卡兒積格,**全部軸當連續**:``product_grid(fast=[5,10], slow=[50,100])``。

    有選擇軸的格請用 ``continuous_axis`` / ``choice_axis`` 逐條砌好再交
    ``ProductGrid``——軸型要明寫,不由參數名去猜。
    """
    return ProductGrid([SweepAxis(name=name, values=tuple(values)) for name, values in axes.items()])


def continuous_axis(name: str, values: Sequence[Any], *, ordered: bool = True) -> SweepAxis:
    """砌一條**連續軸**(回望期、均線日數一類):鄰域沿住它走一步。"""
    return SweepAxis(name=name, values=tuple(values), ordered=ordered, kind=CONTINUOUS)


def choice_axis(name: str, values: Sequence[Any]) -> SweepAxis:
    """砌一條**選擇軸**(持現金/均分、月度/季度一類)。

    它不入鄰域,而是把格切成一層層,每層各出一份判讀。``ordered`` 在這裡沒有
    作用(選擇軸不走一步),所以一律記 ``False``,免得下一個人以為它有意思。
    """
    return SweepAxis(name=name, values=tuple(values), ordered=False, kind=CHOICE)


def simplex_grid(keys: Sequence[str], *, step: float, total: float = 1.0) -> SimplexGrid:
    """砌一個權重單純形格。步長無預設值,要掃幾密一律寫明。"""
    return SimplexGrid(keys, step=step, total=total)


def compose(*parts: SweepGrid) -> CompositeGrid:
    """把幾個格拼起來(例如權重單純形格 × 換倉節奏)。"""
    return CompositeGrid(parts)


def points_frame(grid: SweepGrid) -> list[Mapping[str, Any]]:
    """整個格攤成逐格一行的字典串,方便人眼核對格數與次序。"""
    return [point.as_dict() for point in grid.points()]
