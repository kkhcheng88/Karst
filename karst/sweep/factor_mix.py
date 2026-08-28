"""把因子混合策略接上通用掃描:一格權重 = 一個參數集 = 一次運行。

掃描本身不認得任何一套策略(見 ``karst.sweep.runner``);本檔就是「因子混合怎樣
跑一格」那份接法。做兩件事:

``plan(point)``
    把這一格的權重登記成一個參數集,交回這一格的來歷。**先查再登記**——同名參數集
    再登記一次會出新版(``store.register_param_set`` 的規矩),而版本號是運行編號的
    一部分;不先查的話,同一格重掃會變成一個新編號,於是白白重跑一次。查到內容
    一模一樣就原封不動沿用,一個字都不寫。

``simulate(point)``
    砌 ``FactorMixParams`` 跑一次回測,交回引擎那份結果。

一格一個參數集名(``{前綴}{格的短名}``),不是同一個名不斷出新版——這樣每一格的
來歷各自獨立,查重靠名不靠版本鏈,亦不會在庫裡堆一條幾百版的參數集鏈。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from ..engine.contracts import PricePanel, TradingCosts
from ..errors import ContractViolation
from ..store import ParamSet, StrategyVersion
from ..strategies.factor_mix import (
    FactorMixParams,
    FactorSleeve,
    register_factor_mix,
    run_factor_mix,
)
from .grid import CHOICE, ProductGrid, SimplexGrid, SweepAxis, SweepGrid, SweepPoint, compose
from .runner import CellPlan

# 換倉節奏在掃描格裡的軸名。權重之外多掃一維節奏時用這個名。
CADENCE_AXIS = "cadence"


def weight_grid(
    sleeves: Sequence[FactorSleeve],
    *,
    step: float,
    cadences: Sequence[str] | None = None,
    total: float = 1.0,
) -> SweepGrid:
    """砌因子混合的掃描格:權重單純形格,可另加換倉節奏一維。

    四格權重配 10% 步長是 286 格,5% 是 1771 格。``cadences`` 給了就再乘節奏那一維
    (例如月度與季度,兩個節奏即 572 格)。

    一句要記住:**步長 10% 排不出「各 25%」**——十步分不均四格。要那一格做對照,
    請用 5% 步長,或者把它當**對照格**另外跑一次(見 ``reference_point``)。

    **軸型**(KARST-048):四格權重是**連續軸**(移一步 = 把一步的權重由其中一格
    搬去另一格),換倉節奏是**選擇軸**——月度改季度是換一套做法,不是把某個刻度
    推一格。所以節奏不入鄰域,而是把整個格切成兩層(或者幾層),每層各出一份
    平原判讀,判得出山脊:權重上鋪得平,但換一個節奏就沒有了。
    """
    keys = [sleeve.weight_key for sleeve in sleeves]
    simplex = SimplexGrid(keys, step=step, total=total)
    if not cadences:
        return simplex
    # ``ordered=True`` 對選擇軸沒有作用,照原樣留住只為 ``all_continuous`` 還原得
    # 到軸型之前那個格(舊口徑重判要用)。
    axis = SweepAxis(
        name=CADENCE_AXIS,
        values=tuple(str(c).strip() for c in cadences),
        ordered=True,
        kind=CHOICE,
    )
    return compose(simplex, ProductGrid([axis]))


def reference_point(
    sleeves: Sequence[FactorSleeve],
    weights: Mapping[str, float],
    *,
    cadence: str | None = None,
) -> SweepPoint:
    """砌一個**對照格**:例如四格各 25%。

    對照格不一定在掃描格上(10% 步長就排不出各 25%),但它照樣跑得、照樣落痕、
    照樣有運行編號——報告把它單獨列一行,好讓人見到「掃出來的最優」贏了固定
    比重幾多。
    """
    values: list[tuple[str, Any]] = []
    for sleeve in sleeves:
        if sleeve.weight_key not in weights:
            raise ContractViolation(f"對照格缺「{sleeve.weight_key}」的權重")
        values.append((sleeve.weight_key, float(weights[sleeve.weight_key])))
    if cadence is not None:
        values.append((CADENCE_AXIS, str(cadence).strip()))
    return SweepPoint(values=tuple(values))


def weight_text(value: Any) -> str:
    """權重寫入參數集時的文字。固定寫法,重掃一字不差。

    參數集一律以文字存值(``store`` 會 ``str(value).strip()``),而運行編號正是由
    這串文字算出來的——所以格式一變,同一格就會變成另一個運行。這裡定死:最多四位
    小數,末尾的零剪走(``0.25``、``0.1``、``0``、``1``)。
    """
    number = float(value)
    text = f"{number:.4f}".rstrip("0").rstrip(".")
    return text if text else "0"


def cost_text(value: Any) -> str:
    """成本寫入參數集時的文字。與 ``weight_text`` 同一個道理,但**精細得多**。

    權重那個寫法只留四位小數,而成本細得多:滑點 5 個基點是 ``0.0005``,每股
    US$0.005 是 ``0.005``,再細一級就會被四位小數剪成同一串字——兩組不同的成本
    撞成同一個參數集,即撞成同一個運行編號,靜靜地讀回上一次的成績。這裡留八位。
    """
    number = float(value)
    if number.is_integer():
        return str(int(number))
    text = f"{number:.8f}".rstrip("0").rstrip(".")
    return text if text else "0"


def cost_values(costs: TradingCosts | None) -> dict[str, str]:
    """交易成本在參數集裡的三格。**成本為零就一格都不寫。**

    這一句是驗收條件第 1 條「成本為零時既有運行編號逐位不變」的全部:成本入了
    參數集,運行編號自然跟著變(那正是要的——帶成本的重跑不可以讀回零成本的
    舊成績);但零成本那批舊運行本來就沒有這三格,所以照樣撞得回去。
    """
    if costs is None or costs.is_zero:
        return {}
    return {
        "fee_model": costs.fee_model,
        "fee_rate": cost_text(costs.fee_rate),
        "slippage": cost_text(costs.slippage_fraction),
    }


def cost_slug(costs: TradingCosts | None) -> str:
    """成本在參數集**名**裡的一截。零成本即空字串。

    為什麼成本要入名,不是只入值:參數集一格一個名,同名再登記會出新版,而版本號
    是運行編號的一部分。若帶成本那次沿用同一個名,它會把那個名推上第 2 版;之後
    再零成本重掃一次,又會被推去第 3 版——於是同一格零成本跑兩次,前後兩個運行
    編號不同,「成本為零逐位不變」當場破功。換一個名,兩條路各自獨立,互不相干。
    """
    if costs is None or costs.is_zero:
        return ""
    model = "ps" if costs.fee_model == "per_share" else "pv"
    return f"-fee{model}{cost_text(costs.fee_rate)}-slip{cost_text(costs.slippage_fraction)}"


class CostedEngine:
    """把交易成本注入引擎參數之後,才交給真正的引擎跑。

    因子混合那條策略路徑的參數型別(``strategies.factor_mix.FactorMixParams``)
    暫時只有舊的 ``fees`` 一個數字,載不起「每股手續費」與「滑點」。引擎本身是
    **可換件**(D-007 第 3 條),所以成本由這一件薄薄的替換件補上去:它不改任何
    成績的算法,只在參數交到引擎之前把成本那一格填好。

    ``name`` 照抄被包住那件引擎——引擎名是運行編號的一部分,包一層不可以令它變成
    另一個名(否則同一件引擎會算出兩個編號)。日後 ``FactorMixParams`` 自己接了
    成本合約,這一件就可以整件刪走,呼叫方一個字不用改。
    """

    def __init__(self, costs: TradingCosts, engine: Any | None = None) -> None:
        if not isinstance(costs, TradingCosts):
            raise ContractViolation(
                f"交易成本要是 TradingCosts,收到 {type(costs).__name__}"
            )
        if engine is None:
            from ..engine.vectorbt_engine import VectorbtEngine

            engine = VectorbtEngine()
        self._costs = costs
        self._engine = engine
        self.name = getattr(engine, "name", type(engine).__name__)

    def simulate(self, panel: Any, targets: Any, params: Any) -> Any:
        return self._engine.simulate(panel, targets, replace(params, costs=self._costs))


def ensure_factor_mix_setup(
    gateway: Any,
    *,
    strategy_name: str,
    sleeves: Sequence[FactorSleeve],
    snapshot_id: str,
    setup_param_set_name: str,
    setup_weights: Mapping[str, Any],
    cadence: str,
    description: str | None = None,
) -> StrategyVersion:
    """確保四個因子與策略已經登記,回傳策略版本。**已經有就一個字都不寫。**

    登記走的仍然是唯一入口(D-020 第 4 條)——本檔一句直接寫庫都沒有。這裡本來
    有一道「先查」:因為 ``register_factor_mix`` 每次都登記一個參數集,重跑一次
    掃描就會白白多一個版本。那個理由已經不成立——同名同節奏同取值即沿用舊版,
    這條規矩住在唯一入口(KARST-046),所以先查那一句刪走。

    順帶執正一件事:舊那道先查只認**名**,同名而權重不同一樣會早走,於是改了
    權重的設定參數集寫不入去。現在照直交去入口,取值不同就照樣出新版。
    """
    version, _ = register_factor_mix(
        gateway,
        strategy_name=strategy_name,
        sleeves=sleeves,
        snapshot_id=snapshot_id,
        param_set_name=setup_param_set_name,
        rebalance_cadence=cadence,
        weights={key: weight_text(value) for key, value in setup_weights.items()},
        description=description,
    )
    return version


class FactorMixJob:
    """因子混合策略的掃描跑法(``karst.sweep.runner.CellJob``)。

    ``cadence`` 是固定節奏;掃描格帶 ``cadence`` 軸時,那一軸話事,本欄可以留空。
    """

    def __init__(
        self,
        *,
        gateway: Any,
        panel: PricePanel,
        sleeves: Sequence[FactorSleeve],
        strategy_name: str,
        snapshot_id: str,
        engine_version: str,
        param_set_prefix: str,
        period_start: str,
        period_end: str,
        cadence: str | None = None,
        strategy_version_no: int | None = None,
        initial_cash: float = 100_000.0,
        fees: float = 0.0,
        costs: TradingCosts | None = None,
        engine: Any | None = None,
        engine_name: str = "vectorbt",
    ) -> None:
        if not isinstance(panel, PricePanel):
            raise ContractViolation(f"價格面板要是 PricePanel,收到 {type(panel).__name__}")
        if not sleeves:
            raise ContractViolation("最少要一格因子敞口")
        if not str(param_set_prefix or "").strip():
            raise ContractViolation(
                "參數集名前綴不可留空;一格一個參數集名,沒有前綴會與別的掃描撞名"
            )
        self._gateway = gateway
        self._store = gateway.store
        self._panel = panel
        self._sleeves = tuple(sleeves)
        self._strategy_name = str(strategy_name).strip()
        self._snapshot_id = str(snapshot_id).strip()
        self._engine_version = str(engine_version).strip()
        self._prefix = str(param_set_prefix).strip()
        self._period = (str(period_start).strip(), str(period_end).strip())
        self._cadence = str(cadence).strip() if cadence else None
        self._strategy_version_no = strategy_version_no
        self._initial_cash = float(initial_cash)
        self._fees = float(fees)
        self._costs = costs
        # 成本非零就換上替換件引擎(見 CostedEngine):成本要入的是引擎參數,而
        # 因子混合那個參數型別暫時載不起成本合約。引擎名照舊,運行編號不受影響。
        self._engine = engine if costs is None or costs.is_zero else CostedEngine(costs, engine)
        self._engine_name = str(engine_name).strip()
        self._written = 0

    @property
    def costs(self) -> TradingCosts | None:
        return self._costs

    @property
    def weight_keys(self) -> tuple[str, ...]:
        return tuple(sleeve.weight_key for sleeve in self._sleeves)

    @property
    def param_sets_written(self) -> int:
        """這次掃描真正寫入庫的參數集數目(其餘是查到現成的,沒有寫)。"""
        return self._written

    def _cadence_of(self, point: SweepPoint) -> str:
        if CADENCE_AXIS in point.names:
            return str(point.get(CADENCE_AXIS)).strip()
        if not self._cadence:
            raise ContractViolation(
                "缺換倉節奏:掃描格沒有 cadence 這一軸,而本跑法亦沒有指定固定節奏。"
                "節奏無預設值(D-009 第 7 條),兩者揀一個寫明"
            )
        return self._cadence

    def _weights_of(self, point: SweepPoint) -> dict[str, float]:
        return {key: float(point.get(key)) for key in self.weight_keys}

    def _param_set(self, name: str, cadence: str, values: dict[str, str]) -> ParamSet:
        # 不必先查一句「庫裡有沒有同一組」:同名同節奏同取值即沿用舊版,那條規矩
        # 住在唯一入口(KARST-046)。查到現成的那幾格,收據自己會講 reused。
        param_set, receipt = self._gateway.register_param_set(
            self._strategy_name,
            param_set_name=name,
            rebalance_cadence=cadence,
            values=values,
            strategy_version_no=self._strategy_version_no,
        )
        if not receipt.reused:
            self._written += 1
        return param_set

    def plan(self, point: SweepPoint) -> CellPlan:
        cadence = self._cadence_of(point)
        values = {key: weight_text(value) for key, value in self._weights_of(point).items()}
        values.update(cost_values(self._costs))
        param_set = self._param_set(
            f"{self._prefix}{point.slug}{cost_slug(self._costs)}", cadence, values
        )
        factor_version_ids = tuple(
            self._store.get_factor_version(sleeve.factor_name).factor_version_id
            for sleeve in self._sleeves
        )
        strategy = self._store.get_strategy_version(
            self._strategy_name, self._strategy_version_no
        )
        return CellPlan(
            strategy_name=strategy.name,
            param_set_name=param_set.name,
            snapshot_id=self._snapshot_id,
            engine_name=self._engine_name,
            engine_version=self._engine_version,
            period_start=self._period[0],
            period_end=self._period[1],
            strategy_version_no=strategy.version_no,
            param_set_version_no=param_set.version_no,
            factor_version_ids=factor_version_ids,
        )

    def simulate(self, point: SweepPoint) -> Any:
        params = FactorMixParams(
            cadence=self._cadence_of(point),
            weights=self._weights_of(point),
            initial_cash=self._initial_cash,
            fees=self._fees,
        )
        # 成本不在這個型別裡,它由 CostedEngine 在參數交到引擎之前補上(見上文)。
        result = run_factor_mix(
            store=self._store,
            panel=self._panel,
            sleeves=self._sleeves,
            params=params,
            engine=self._engine,
        )
        if result.engine_name != self._engine_name:
            raise ContractViolation(
                f"這一格由「{result.engine_name}」跑出來,但落痕寫的是「{self._engine_name}」;"
                "引擎名是運行編號的一部分,不可以對不上(D-007 第 3 條)"
            )
        return result
