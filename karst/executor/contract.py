"""策略合約(strategy contract):一條策略要交出的那幾件東西的宣告。

線畫在「只有這條策略知道的東西」與「每條策略做法一模一樣的東西」之間
(架構審視候選一,D-043)。線的策略那一邊只剩四件:

1. 有哪幾格參數、每格的值域與文字寫法(**參數規格**);
2. 要登記哪幾條因子(**因子規格**);
3. 由面板與已驗參數算出**目標比重表**或**規則參數**,連同選股痕跡(策略本體);
4. 用**選股漏斗**哪幾層。

線的另一邊全部住在 ``karst.executor.executor``(策略執行台)。

本檔另外收住兩件全倉正本:

``ParamField`` 的**值域檢查**
    取代五套並存的純量驗證(``trend_swing._as_int`` / ``._as_float``、
    ``factor_rotation._check_tilt`` / ``._check_lookback_days``、
    ``engine.rules._fraction`` / ``._positive``)。

``value_text`` / ``field_slug`` 的**參數文字化**
    取代四份並存的文字化(``sweep.factor_mix.weight_text``、
    ``sweep.factor_rotation.param_text`` 與 ``point_slug``、``SweepPoint.slug``)。
    文字化不是排版:參數集一律以文字存值,而**運行編號正是由那串文字算出來的**
    ——格式一變,同一組參數就會變成另一次運行。所以四份收成一份,口徑逐位不變。

紀律三條:

* **一格預設值都沒有**(D-009 第 7 條)。規格只講值域,不講取值;缺一格拒收、
  多一格拒收。換倉節奏尤其明文不可有預設。
* **一格都要掃得到**(D-008 第 3 條)。寫死在碼裡的數值不是參數。
* ``plan`` 是**純函數**:不開庫、不讀檔、不寫檔、不 import 任何第三方引擎
  (D-007 第 3 條)。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final, Protocol, runtime_checkable

import numpy as np

from ..errors import ContractViolation
from ..store import EXIT_GOVERNANCES as _STORE_EXIT_GOVERNANCES
from ..store import LAYERS as _STORE_LAYERS

# ----------------------------------------------------------------------
# 錯誤模式:全部是 ContractViolation 的子型別,執行台在跑引擎**之前**擲出
# ----------------------------------------------------------------------


class MissingParameter(ContractViolation):
    """規格有這一格、取值沒有。不補預設——補了就是替用戶決定(D-008 第 2 條)。"""


class UnknownParameter(ContractViolation):
    """取值有這一格、規格沒有。多一格照收即等於規格不是正本。"""


class ParameterOutOfRange(ContractViolation):
    """取值在規格宣告的值域之外。"""


class UnresolvedTicker(ContractViolation):
    """交易代號在那一日解析不到實體(D-026 第 2 條)。"""


class EntityNotInPanel(ContractViolation):
    """解析到實體,但面板沒有它的價格。不猜、不當零。"""


class DuplicateExposureEntity(ContractViolation):
    """兩格敞口撞同一個實體。"""


class MissingRequiredInput(ContractViolation):
    """策略要一份輸入(宏觀面板一類)而呼叫方沒有給。"""


class PlanShapeViolation(ContractViolation):
    """計劃的形狀不合:比重寫在非執行日、痕跡層名不在宣告之內一類。"""


class EngineNameMismatch(ContractViolation):
    """結果自報的引擎名與落痕寫的不同;引擎名是運行編號的一部分。"""


# ----------------------------------------------------------------------
# 參數文字化:全倉正本
# ----------------------------------------------------------------------

# 值寫入參數集時的寫法。
TEXT_FOUR_PLACES: Final[str] = "four_places"
"""最多四位小數,末尾的零剪走(``0.25``、``0.1``、``0``、``1``)。權重用這個。"""

TEXT_EIGHT_PLACES: Final[str] = "eight_places"
"""整數照寫,否則最多八位小數剪零。交易成本用這個——滑點 5 個基點是 ``0.0005``,
四位小數會把兩組不同的成本剪成同一串字,即撞成同一個運行編號。"""

TEXT_AUTO: Final[str] = "auto"
"""按型別揀:是非寫 ``true``/``false``、整數寫整數、小數走四位小數那一套、
其餘照原文剪空白。"""

TEXT_VERBATIM: Final[str] = "verbatim"
"""照原文剪空白。換倉節奏、模式一類文字取值用這個。"""

TEXT_STYLES: Final[frozenset[str]] = frozenset(
    {TEXT_FOUR_PLACES, TEXT_EIGHT_PLACES, TEXT_AUTO, TEXT_VERBATIM}
)

# 一格在**參數集名**裡的短名寫法。
SLUG_PERCENT: Final[str] = "percent"
"""0 至 1 之間的數印成百分點(``0.25`` → ``25``),``weight_`` 前綴剪走。
權重格用這個——十步一格的權重印成百分點看得懂又不會撞名。"""

SLUG_VERBATIM: Final[str] = "verbatim"
"""數字就是數字(``6`` 就是 ``6``)。回望期一類用這個:印成百分點會把
一個月印成 100,對讀庫的人是誤導。"""

SLUG_STYLES: Final[frozenset[str]] = frozenset({SLUG_PERCENT, SLUG_VERBATIM})

# 「印成整數」的容差。只擋浮點尾數。
_STEP_TOLERANCE: Final[float] = 1e-9

_WEIGHT_PREFIX: Final[str] = "weight_"


def value_text(value: Any, style: str = TEXT_AUTO) -> str:
    """一個取值寫入參數集時的文字。**這是全倉唯一一份寫法。**

    參數集一律以文字存值(``store`` 會 ``str(value).strip()``),運行編號由那串
    文字算出來,所以這裡改一個字,全庫的運行編號就會換一批。
    """
    if style not in TEXT_STYLES:
        raise ContractViolation(f"參數文字化寫法只收 {sorted(TEXT_STYLES)},收到 {style!r}")

    if style == TEXT_VERBATIM:
        return str(value).strip()

    if style == TEXT_FOUR_PLACES:
        number = float(value)
        text = f"{number:.4f}".rstrip("0").rstrip(".")
        return text if text else "0"

    if style == TEXT_EIGHT_PLACES:
        number = float(value)
        if number.is_integer():
            return str(int(number))
        text = f"{number:.8f}".rstrip("0").rstrip(".")
        return text if text else "0"

    # TEXT_AUTO
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(int(value))
    if isinstance(value, float):
        if float(value).is_integer():
            return str(int(value))
        return value_text(value, TEXT_FOUR_PLACES)
    return str(value).strip()


def display_text(value: Any) -> str:
    """把一個取值印成人看得明、機器又對得回的樣子(掃描格的標籤用)。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        number = float(value)
        if abs(number - round(number)) < _STEP_TOLERANCE:
            return str(int(round(number)))
        return f"{number:g}"
    return str(value)


def value_slug(value: Any) -> str:
    """一個取值印成短名的一截(不帶參數名)。權重印成百分點。"""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if 0.0 <= number <= 1.0:
            # 權重那一類:印成百分點,10% 就是 10,看得懂又不會撞名。
            percent = number * 100.0
            if abs(percent - round(percent)) < 1e-6:
                return str(int(round(percent)))
            return f"{percent:g}".replace(".", "p")
        return display_text(value).replace(".", "p").replace("-", "neg")
    return str(value).strip().replace(" ", "-")


def field_slug(name: str, value: Any, style: str = SLUG_PERCENT) -> str:
    """一格在**參數集名**裡的短名。**這是全倉唯一一份寫法。**

    參數集一格一個名,而版本號是運行編號的原料之一;短名一變,同一格重掃就會
    寫成另一個參數集,於是白白重跑一次。
    """
    if style not in SLUG_STYLES:
        raise ContractViolation(f"短名寫法只收 {sorted(SLUG_STYLES)},收到 {style!r}")
    key = str(name).strip()
    if style == SLUG_PERCENT:
        short = key[len(_WEIGHT_PREFIX):] if key.startswith(_WEIGHT_PREFIX) else key
        return f"{short}{value_slug(value)}"
    return f"{key}{value_text(value, TEXT_AUTO)}"


def point_slug(values: Sequence[tuple[str, Any]], style: str = SLUG_PERCENT) -> str:
    """一組取值的短名:逐格短名以 ``-`` 串起。"""
    return "-".join(field_slug(name, value, style) for name, value in values)


# 交易成本在參數集裡的三格。名寫死在這裡,因為它們同時是**運行編號的原料**:
# 三個名任何一個改一個字,全部帶成本的運行當場換編號。
COST_FEE_MODEL: Final[str] = "fee_model"
COST_FEE_RATE: Final[str] = "fee_rate"
COST_SLIPPAGE: Final[str] = "slippage"
COST_FIELD_NAMES: Final[tuple[str, ...]] = (COST_FEE_MODEL, COST_FEE_RATE, COST_SLIPPAGE)


# ----------------------------------------------------------------------
# 參數規格:一格的值域檢查
# ----------------------------------------------------------------------

KIND_INTEGER: Final[str] = "integer"
KIND_NUMBER: Final[str] = "number"
KIND_TEXT: Final[str] = "text"
PARAM_KINDS: Final[frozenset[str]] = frozenset({KIND_INTEGER, KIND_NUMBER, KIND_TEXT})

# 一格取值寫在參數集的哪一邊。
SLOT_VALUE: Final[str] = "value"
"""寫入 ``param_value`` 那張表(絕大多數格)。"""

SLOT_CADENCE: Final[str] = "cadence"
"""寫入參數集的 ``rebalance_cadence`` 那一欄。換倉節奏在庫裡有自己一格,
但它照樣是一格**可掃軸**、照樣無預設(D-009 第 7 條),所以照樣入規格。"""

PARAM_SLOTS: Final[frozenset[str]] = frozenset({SLOT_VALUE, SLOT_CADENCE})


@dataclass(frozen=True, slots=True)
class ParamField:
    """一格參數的規格:名、型別、值域、文字寫法。**沒有取值,亦沒有預設值。**

    值域兩邊各自講明含不含端點:``_fraction`` 是兩邊都不含的 0 與 1 之間、
    ``_positive`` 是下限 0 不含而無上限、``_check_tilt`` 是下限 0 不含而上限 1 含、
    ``_check_lookback_days`` 是下限 1 含而無上限——五套並存的純量驗證,收成
    這四個欄位講得完。
    """

    name: str
    kind: str
    what: str
    lower: float | None = None
    upper: float | None = None
    lower_inclusive: bool = False
    upper_inclusive: bool = False
    choices: tuple[str, ...] = ()
    text_style: str = TEXT_AUTO
    slug_style: str = SLUG_PERCENT
    slot: str = SLOT_VALUE
    label: str | None = None

    def __post_init__(self) -> None:
        if not str(self.name or "").strip():
            raise ContractViolation("參數格的名不可留空")
        if self.kind not in PARAM_KINDS:
            raise ContractViolation(
                f"參數格「{self.name}」的型別只收 {sorted(PARAM_KINDS)},收到 {self.kind!r}"
            )
        if self.text_style not in TEXT_STYLES:
            raise ContractViolation(
                f"參數格「{self.name}」的文字寫法只收 {sorted(TEXT_STYLES)},收到 {self.text_style!r}"
            )
        if self.slug_style not in SLUG_STYLES:
            raise ContractViolation(
                f"參數格「{self.name}」的短名寫法只收 {sorted(SLUG_STYLES)},收到 {self.slug_style!r}"
            )
        if self.slot not in PARAM_SLOTS:
            raise ContractViolation(
                f"參數格「{self.name}」的落點只收 {sorted(PARAM_SLOTS)},收到 {self.slot!r}"
            )
        if not str(self.what or "").strip():
            raise ContractViolation(f"參數格「{self.name}」要一句說明:它是什麼")
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "choices", tuple(str(c).strip() for c in self.choices))
        if self.kind == KIND_TEXT and not self.choices:
            raise ContractViolation(
                f"參數格「{self.name}」是文字格,要寫明收哪幾個取值;"
                "「什麼都收」不是值域,掃描格亦排不出來"
            )

    @property
    def title(self) -> str:
        """錯誤訊息裡怎樣叫這一格:有中文名就「中文名(程式名)」,否則程式名。"""
        return f"{self.label}({self.name})" if self.label else self.name

    @property
    def range_text(self) -> str:
        """值域寫成一句人話。判讀報告與錯誤訊息共用。"""
        if self.kind == KIND_TEXT:
            return "、".join(self.choices)
        low = "無下限" if self.lower is None else (
            f"≥{self.lower}" if self.lower_inclusive else f">{self.lower}"
        )
        high = "無上限" if self.upper is None else (
            f"≤{self.upper}" if self.upper_inclusive else f"<{self.upper}"
        )
        return f"{low} 且 {high}"

    def check(self, value: Any) -> Any:
        """驗一個取值,回**已轉型**的值。過不到即拋 ``ParameterOutOfRange``。"""
        if self.kind == KIND_TEXT:
            text = str(value).strip()
            if text not in self.choices:
                raise ParameterOutOfRange(
                    f"{self.title}只收「{self.range_text}」,收到 {value!r}"
                )
            return text

        if self.kind == KIND_INTEGER:
            text = str(value).strip()
            try:
                number: Any = int(text)
            except (TypeError, ValueError):
                # ``6.0`` 一類寫法照收(參數集以文字存值,來源不一);
                # 但 ``6.5`` 不是整數,照拒。
                try:
                    as_float = float(text)
                except (TypeError, ValueError) as exc:
                    raise ParameterOutOfRange(
                        f"{self.title}要是整數,收到 {value!r}"
                    ) from exc
                if not np.isfinite(as_float) or not float(as_float).is_integer():
                    raise ParameterOutOfRange(f"{self.title}要是整數,收到 {value!r}")
                number = int(as_float)
        else:
            try:
                number = float(str(value).strip())
            except (TypeError, ValueError) as exc:
                raise ParameterOutOfRange(
                    f"{self.title}要是一個數,收到 {value!r}"
                ) from exc
            if not np.isfinite(number):
                raise ParameterOutOfRange(
                    f"{self.title}要是有限數,收到 {value!r}"
                )

        if self.lower is not None:
            if number < self.lower or (not self.lower_inclusive and number == self.lower):
                raise ParameterOutOfRange(
                    f"{self.title}要 {self.range_text},收到 {value!r}"
                )
        if self.upper is not None:
            if number > self.upper or (not self.upper_inclusive and number == self.upper):
                raise ParameterOutOfRange(
                    f"{self.title}要 {self.range_text},收到 {value!r}"
                )
        return number

    def text(self, value: Any) -> str:
        """這一格寫入參數集時的文字。"""
        return value_text(value, self.text_style)

    def slug(self, value: Any) -> str:
        """這一格在參數集名裡的短名。"""
        return field_slug(self.name, value, self.slug_style)


# ----------------------------------------------------------------------
# 純量驗證:全倉正本
#
# 以前五套並存,各自寫一遍「是不是有限數、在不在範圍內」——``trend_swing._as_int``
# 與 ``._as_float``、``factor_rotation._check_tilt`` 與 ``._check_lookback_days``、
# ``engine.rules._fraction`` 與 ``._positive``。五套一旦飄開,同一個取值會在一處
# 收得、另一處拒收。以下四句是同一份 ``ParamField.check`` 的四種值域,連錯誤訊息
# 都只有一份。
# ----------------------------------------------------------------------


def _adhoc(name: str, kind: str, **bounds: Any) -> ParamField:
    return ParamField(name=name, kind=kind, what="(即場驗一個取值)", **bounds)


def check_positive(value: Any, label: str) -> float:
    """正數:下限 0 不含,無上限。注碼、價位、本金一類。"""
    return _adhoc(label, KIND_NUMBER, lower=0.0).check(value)


def check_fraction(value: Any, label: str) -> float:
    """比例:0 與 1 之間,**兩邊都不含**。單筆風險上限、月度熔斷一類。"""
    return _adhoc(label, KIND_NUMBER, lower=0.0, upper=1.0).check(value)


def check_ratio(value: Any, label: str) -> float:
    """押注比重:大於 0、**上限 1 含**。輪動驅動器押幾多注用這個。"""
    return _adhoc(label, KIND_NUMBER, lower=0.0, upper=1.0, upper_inclusive=True).check(value)


def check_count(value: Any, label: str) -> int:
    """日數 / 個數:整數,**下限 1 含**,無上限。回望期一類。"""
    return _adhoc(label, KIND_INTEGER, lower=1, lower_inclusive=True).check(value)


def check_integer(value: Any, label: str) -> int:
    """整數,不設值域。"""
    return _adhoc(label, KIND_INTEGER).check(value)


def check_number(value: Any, label: str) -> float:
    """有限數,不設值域。"""
    return _adhoc(label, KIND_NUMBER).check(value)


# ----------------------------------------------------------------------
# 風控三格:**普通可掃軸,不是特權**
#
# 乙份設計把風控做成 ``RunRequest`` 的一格獨立輸入。裁決不取(design-judge 第三
# 節):風控取值與別的參數一樣要掃得到、要入參數集、要入運行編號——開一格獨立
# 輸入即是把它抬出參數規格之外,於是「單筆風險由 2% 改做 1.5%」不會換一個運行
# 編號,兩次成績會靜靜地撞成同一次。所以它們是三個普通 ``ParamField``。
# ----------------------------------------------------------------------

RISK_PER_TRADE: Final[str] = "risk.per_trade_risk"
RISK_MAX_POSITION: Final[str] = "sizing.max_position_fraction"
RISK_MONTHLY_CAP: Final[str] = "risk.monthly_loss_cap"


def risk_fields() -> tuple[ParamField, ...]:
    """風控那三格的規格。**無取值、無預設**,每格自報值域。"""
    return (
        ParamField(
            name=RISK_PER_TRADE,
            kind=KIND_NUMBER,
            what="單筆願意輸的本金比例;注碼由它與止蝕距離倒算出來",
            label="單筆風險比例",
            lower=0.0,
            upper=1.0,
            slug_style=SLUG_VERBATIM,
        ),
        ParamField(
            name=RISK_MAX_POSITION,
            kind=KIND_NUMBER,
            what="一隻股票最多佔組合市值幾多;注碼算出來大過它就削到它",
            label="單一持倉市值上限",
            lower=0.0,
            upper=1.0,
            slug_style=SLUG_VERBATIM,
        ),
        ParamField(
            name=RISK_MONTHLY_CAP,
            kind=KIND_NUMBER,
            what="一個月輸到幾多就停止開新倉(月度熔斷)",
            label="月度虧損熔斷門檻",
            lower=0.0,
            upper=1.0,
            slug_style=SLUG_VERBATIM,
        ),
    )


@dataclass(frozen=True, slots=True)
class ParamSpec:
    """一條策略全部參數格的宣告。**一格預設值都沒有,一格都要掃得到。**

    它同時是「一格掃描格怎樣變成一個參數集」的依據:``as_param_set`` 把一組取值
    收成庫收得的兩件(``rebalance_cadence`` 與 ``values``),``slug`` 收成參數集名
    那一截。
    """

    fields: tuple[ParamField, ...]

    def __post_init__(self) -> None:
        fields = tuple(self.fields)
        if not fields:
            raise ContractViolation("參數規格一格都沒有;沒有參數的策略掃不出東西")
        seen: set[str] = set()
        for item in fields:
            if not isinstance(item, ParamField):
                raise ContractViolation(
                    f"參數規格只收 ParamField,收到 {type(item).__name__}"
                )
            if item.name in seen:
                raise ContractViolation(f"參數規格內「{item.name}」出現兩次")
            seen.add(item.name)
        cadence = [item for item in fields if item.slot == SLOT_CADENCE]
        if len(cadence) > 1:
            raise ContractViolation("參數規格只可以有一格換倉節奏")
        object.__setattr__(self, "fields", fields)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.fields)

    @property
    def value_names(self) -> tuple[str, ...]:
        """落 ``param_value`` 那張表的那幾格。"""
        return tuple(item.name for item in self.fields if item.slot == SLOT_VALUE)

    @property
    def cadence_field(self) -> ParamField | None:
        for item in self.fields:
            if item.slot == SLOT_CADENCE:
                return item
        return None

    def field(self, name: str) -> ParamField:
        key = str(name).strip()
        for item in self.fields:
            if item.name == key:
                return item
        raise UnknownParameter(
            f"參數規格沒有「{key}」這一格;有的是:{'、'.join(self.names)}"
        )

    def validate(self, values: Mapping[str, Any]) -> dict[str, Any]:
        """驗一整組取值,回**已轉型**的一份。缺一格拒收、多一格拒收、值域不合拒收。"""
        given = {str(key).strip(): value for key, value in dict(values or {}).items()}
        missing = [name for name in self.names if name not in given]
        if missing:
            raise MissingParameter(
                f"缺參數:{'、'.join(missing)};參數無預設值,要用的一律寫明"
                "(D-008 第 3 條、D-009 第 7 條)"
            )
        extra = sorted(set(given) - set(self.names))
        if extra:
            raise UnknownParameter(
                f"這條策略沒有這幾格參數:{'、'.join(extra)};"
                f"規格宣告的是:{'、'.join(self.names)}"
            )
        return {item.name: item.check(given[item.name]) for item in self.fields}

    def as_param_set(self, values: Mapping[str, Any]) -> tuple[str | None, dict[str, str]]:
        """一組取值收成庫收得的兩件:``(換倉節奏, 逐格文字)``。

        取值先過一次值域,再逐格按自己那一格的寫法文字化——所以參數集內那串字
        全倉只有這一條路寫得出,運行編號因此穩定。
        """
        checked = self.validate(values)
        cadence: str | None = None
        texts: dict[str, str] = {}
        for item in self.fields:
            text = item.text(checked[item.name])
            if item.slot == SLOT_CADENCE:
                cadence = text
            else:
                texts[item.name] = text
        return cadence, texts

    def slug(self, values: Mapping[str, Any]) -> str:
        """一組取值的參數集名短名。次序照規格宣告的次序,重掃一字不差。"""
        checked = self.validate(values)
        return "-".join(item.slug(checked[item.name]) for item in self.fields)

    def read(self, param_set: Any) -> dict[str, Any]:
        """由一個已登記的參數集讀回一整組取值(節奏那一格由 ``rebalance_cadence`` 來)。"""
        raw: dict[str, Any] = dict(getattr(param_set, "values", {}) or {})
        cadence_field = self.cadence_field
        if cadence_field is not None:
            raw[cadence_field.name] = getattr(param_set, "rebalance_cadence", None)
        return self.validate(raw)


# ----------------------------------------------------------------------
# 交易成本那三格:全倉唯一一份
# ----------------------------------------------------------------------


def cost_fields(costs: Any) -> tuple[ParamField, ...]:
    """交易成本在參數規格裡的三格。**成本為零就一格都不出。**

    這一句是「成本為零時既有運行編號逐位不變」的全部:成本入了參數集,運行編號
    自然跟著變(那正是要的——帶成本的重跑不可以讀回零成本的舊成績);但零成本
    那批舊運行本來就沒有這三格,所以照樣撞得回去。
    """
    if costs is None or bool(getattr(costs, "is_zero", False)):
        return ()
    return (
        ParamField(
            name=COST_FEE_MODEL,
            kind=KIND_TEXT,
            what="手續費按每股收還是按成交金額比例收",
            label="手續費型別",
            choices=("per_share", "fraction_of_value"),
            text_style=TEXT_VERBATIM,
            slug_style=SLUG_VERBATIM,
        ),
        ParamField(
            name=COST_FEE_RATE,
            kind=KIND_NUMBER,
            what="手續費率(每股銀碼,或者成交金額的比例)",
            label="手續費率",
            lower=0.0,
            lower_inclusive=True,
            # 滑點 5 個基點是 0.0005;四位小數會把兩組不同的成本剪成同一串字,
            # 即撞成同一個運行編號,靜靜地讀回上一次的成績。這裡留八位。
            text_style=TEXT_EIGHT_PLACES,
            slug_style=SLUG_VERBATIM,
        ),
        ParamField(
            name=COST_SLIPPAGE,
            kind=KIND_NUMBER,
            what="滑點:成交價相對參考價偏走的比例",
            label="滑點",
            lower=0.0,
            upper=1.0,
            lower_inclusive=True,
            text_style=TEXT_EIGHT_PLACES,
            slug_style=SLUG_VERBATIM,
        ),
    )


def cost_inputs(costs: Any) -> dict[str, Any]:
    """交易成本那三格的取值(未文字化),零成本即空的。交去 ``sweep`` 的起步取值。"""
    if costs is None or bool(getattr(costs, "is_zero", False)):
        return {}
    return {
        COST_FEE_MODEL: costs.fee_model,
        COST_FEE_RATE: costs.fee_rate,
        COST_SLIPPAGE: costs.slippage_fraction,
    }


def cost_slug(costs: Any) -> str:
    """成本在參數集**名**裡的一截。零成本即空字串。

    為什麼成本要入名,不是只入值:參數集一格一個名,同名再登記會出新版,而版本號
    是運行編號的一部分。若帶成本那次沿用同一個名,它會把那個名推上第 2 版;之後
    再零成本重掃一次,又會被推去第 3 版——於是同一格零成本跑兩次,前後兩個運行
    編號不同,「成本為零逐位不變」當場破功。換一個名,兩條路各自獨立,互不相干。
    """
    if costs is None or bool(getattr(costs, "is_zero", False)):
        return ""
    model = "ps" if costs.fee_model == "per_share" else "pv"
    rate = value_text(costs.fee_rate, TEXT_EIGHT_PLACES)
    slip = value_text(costs.slippage_fraction, TEXT_EIGHT_PLACES)
    return f"-fee{model}{rate}-slip{slip}"


# ----------------------------------------------------------------------
# 因子規格、實體解析、一次運行的輸入
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FactorSpec:
    """這條策略要登記的一條因子:名、刻度型、產生程序、說明。

    產生程序的輸入數據版本由策略填入執行台交來的**快照編號**——同名因子改用另一個
    快照即自動出新版(版本鏈,D-021 第 6、8、9 條)。
    """

    name: str
    scale_kind: str
    procedure: Any
    description: str | None = None

    def __post_init__(self) -> None:
        for label, value in (("因子名", self.name), ("刻度型", self.scale_kind)):
            if not str(value or "").strip():
                raise ContractViolation(f"因子規格的{label}不可留空")
        if self.procedure is None:
            raise ContractViolation(
                f"因子「{self.name}」缺產生程序;追溯三件之一,不可留空(D-021 第 8 條)"
            )


@dataclass(frozen=True, slots=True)
class EntityRequest:
    """這一組參數要解析哪些交易代號。

    ``exposures`` 持得到的(會出現在目標比重表);``signals`` 只做訊號的(大市那條線,
    在目標比重表裡永遠是 0 或者根本沒有那一欄);``series`` 宏觀序列代號(非可投資,
    不入實體表)。
    """

    exposures: tuple[str, ...] = ()
    signals: tuple[str, ...] = ()
    series: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("exposures", "signals", "series"):
            object.__setattr__(
                self, name, tuple(str(t).strip() for t in getattr(self, name))
            )
        overlap = set(self.exposures) & set(self.signals)
        if overlap:
            raise ContractViolation(
                f"代號 {sorted(overlap)} 同時報成持倉與只做訊號;一個代號只可以是其中一邊"
            )

    @property
    def tickers(self) -> tuple[str, ...]:
        """要經定義庫按日解析的那批(宏觀序列不在內)。"""
        return self.exposures + self.signals


@dataclass(frozen=True, slots=True)
class ResolvedEntity:
    """一個代號在那一日解析出來的樣子。"""

    ticker: str
    entity_id: int
    entity_kind: str
    tradable: bool


@dataclass(frozen=True, slots=True)
class FactorVersionRef:
    """一條因子現行那一版的身份。運行編號蓋住的就是它。"""

    name: str
    factor_version_id: int
    version_no: int


@dataclass(frozen=True, slots=True)
class RunRequest:
    """跑一格所需的全部輸入。**不帶定義庫、不帶唯一入口、不帶引擎。**

    ``params`` 是**已驗、已轉型**的一組取值(含換倉節奏那一格);``entities`` 是
    代號 → 已解析實體的唯讀對照;``factors`` 是因子名 → 現行版本;``extras`` 是
    第二種輸入(宏觀面板一類)。
    """

    panel: Any
    params: Mapping[str, Any]
    entities: Mapping[str, ResolvedEntity]
    factors: Mapping[str, FactorVersionRef]
    snapshot_id: str
    extras: Mapping[str, Any] = field(default_factory=dict)

    def entity(self, ticker: str) -> ResolvedEntity:
        key = str(ticker).strip()
        try:
            return self.entities[key]
        except KeyError as exc:
            raise UnresolvedTicker(
                f"代號 {key} 未經解析;要用的代號一律先在 needs_entities 宣告"
            ) from exc

    def factor(self, name: str) -> FactorVersionRef:
        key = str(name).strip()
        try:
            return self.factors[key]
        except KeyError as exc:
            raise ContractViolation(
                f"因子「{key}」未經登記;要用的因子一律先在 factor_specs 宣告"
            ) from exc

    def require(self, key: str) -> Any:
        value = self.extras.get(key)
        if value is None:
            raise MissingRequiredInput(
                f"這條策略要一份「{key}」才跑得動,但呼叫方沒有給"
            )
        return value


# ----------------------------------------------------------------------
# 引擎計劃:目標比重路徑與規則路徑二擇其一
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TargetPlan:
    """目標比重路徑的計劃:一張「日期 × 實體編號 → 目標比重」的表。

    空白 = 這根 K 線不下單,0 = 清倉到零,兩者不可混(CONTEXT.md「目標比重表」)。
    """

    targets: Any
    cadence: str
    initial_cash: float
    fees: float
    rebalances: tuple[Any, ...] = ()
    selection: Any | None = None
    extras: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RulePlan:
    """規則路徑的計劃:一份事件規則參數。"""

    rule_params: Any
    selection: Any | None = None
    extras: Mapping[str, Any] = field(default_factory=dict)


EnginePlan = TargetPlan | RulePlan

# 這條策略走引擎的哪一條路。**在跑之前就要講得出**:落痕寫的引擎名是運行編號的
# 一部分,所以執行台要先知道自己會叫哪一件引擎,才算得出編號來查重。
ENGINE_TARGETS: Final[str] = "targets"
"""目標比重路徑(規格 6.3):砌一張「日期 × 實體 → 目標比重」的表。"""

ENGINE_RULES: Final[str] = "rules"
"""規則路徑(規格 6.2):砌一份事件規則參數。"""

ENGINE_PATHS: Final[frozenset[str]] = frozenset({ENGINE_TARGETS, ENGINE_RULES})


# ----------------------------------------------------------------------
# 三層與離場治理:合約兩格必填(D-054、D-056、D-058;KARST-116)
#
# 取值的正本住在庫身的 CHECK 約束,``karst.store`` 給程式一個名字用;這裡只是轉引,
# 不另寫一份——庫、入口、執行台、策略四邊必須認同一套字(與對齊標記同制)。
# ----------------------------------------------------------------------

LAYERS: Final[dict[str, str]] = _STORE_LAYERS
"""由上而下三層:``regime`` 市況 → ``sector`` 板塊 → ``stock`` 個股(D-054)。"""

EXIT_GOVERNANCES: Final[dict[str, str]] = _STORE_EXIT_GOVERNANCES
"""離場治理三型:``continuation`` 延續型注、``reversion`` 回歸型注、
``rule_based`` 規則型(D-056)。"""


# ----------------------------------------------------------------------
# 合約本身
# ----------------------------------------------------------------------


@runtime_checkable
class StrategyContract(Protocol):
    """一條策略要交出的那八件。用 ``Protocol`` 不用基類:基類會誘使策略去繼承
    編排,而編排正是要拆走的東西。

    其中 ``layer`` 與 ``exit_governance`` 是 D-058 第 1 條加的兩格必填(KARST-116):
    它們不影響怎樣跑,只答「這條策略站在三層的哪一層、它的注幾時走」——而正因為未答
    就登記不到、登記不到就跑不動,它是全倉唯一一道逼人在寫策略之前先答的閘。
    """

    #: 這條策略在 ``store.STRATEGY_TYPES`` 八個之中屬哪一類。執行台不猜。
    strategy_type: str

    #: 這條策略屬**由上而下三層**的哪一層:``regime`` 市況(防守階梯)、``sector``
    #: 板塊、``stock`` 個股(``LAYERS`` 三揀一)。**必填,執行台不猜、庫身不收空白**
    #: (D-054、D-058 第 1 條)。平台重心是由上而下三層,任何策略按此次序收窄、不准
    #: 跳層由個股起步——一條策略講不出自己站在哪一層,就無從判它有沒有跳層。
    layer: str

    #: 這條策略的**離場治理**屬哪一型:``continuation`` 延續型注(價格止蝕增值、不准
    #: 溝貨、賠率門檻有意義)、``reversion`` 回歸型注(價格止蝕有害,靠入場前寫死的
    #: 論點失效條件加注碼上限)、``rule_based`` 規則型(離場由預先寫死的規則逐期重算,
    #: 無價格止蝕亦無論點條件)。**必填**(D-056 第 2 條、D-058 第 1 條):治理配置
    #: 必須在入場之前寫死,是策略合約的一部分,不准臨場決定。
    exit_governance: str

    #: 用選股漏斗哪幾層,由上而下。空的即這條策略交不出選股痕跡(D-013)。
    funnel_stages: tuple[str, ...]

    #: 走引擎的哪一條路:``ENGINE_TARGETS`` 或 ``ENGINE_RULES``。
    engine_path: str

    def param_spec(self) -> ParamSpec:
        """全部參數格的規格。一格預設值都沒有,一格都要掃得到。"""
        ...

    def factor_specs(self, snapshot_id: str) -> tuple[FactorSpec, ...]:
        """要登記哪幾條因子。快照編號由執行台交來,填入產生程序的輸入數據版本。"""
        ...

    def needs_entities(self, params: Mapping[str, Any]) -> EntityRequest:
        """這一組參數要解析哪些交易代號。策略不碰定義庫。"""
        ...

    def plan(self, request: RunRequest) -> EnginePlan:
        """策略本體:收面板與已驗參數,回一份引擎收得的計劃。**純函數。**"""
        ...
