"""全倉第一個 ``conftest.py``(KARST-090)。

放在這裡的東西只有一個資格:**每個測試檔都會用到,而各自抄一份就會飄開。**
現時只有兩件——寫入者名字,與一個臨時真庫。

**不造假定義庫。** 每個要庫的測試照舊起一個臨時 sqlite **真庫**,照舊經唯一入口
寫(D-020 第 4 條):版本鏈、寫入者簽章、同名同值即沿用舊版、運行編號查重——
這些正是要驗的東西,造一個假的出來就等於不驗。臨時庫住在 ``tmp_path``,
**一句都不會寫到倉裡那個 ``karst.sqlite``**。

假引擎住在 ``tests/doubles/``,不住這裡:替身要明寫才拿得到,不應該由夾具悄悄
塞給每個測試。

KARST-093 補上第三件:一個**種好數的臨時專案根** ``seeded_project_root``。六個
``test_web*.py`` 本來一律 ``build_reader(PROJECT_ROOT)``——即是直接打倉根那個生產庫
``karst.sqlite``。讀那邊已經不好(測試斷言吊住生產庫當日有幾多條運行,庫一長大就
無故轉紅),寫那邊更加不可以:``test_web_jobs.py`` 驗的是「網頁上按重跑」,而重跑
走的正是**正式路徑**,於是每跑一次測試,生產庫就多一條 ``origin='formal'`` 的運行
——正式運行由 12 條變 13 條就是這樣來的(KARST-087 交低,KARST-093 收拾)。

夾具是 session 級的:種一次數要凍一個真價格快照、寫幾份 parquet,六個檔各種一次
太慢;而它只在 ``tmp_path_factory`` 開出來的目錄內寫,session 完就整個掉。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pytest

from karst import FormulaProcedure
from karst.data import StaticSource, UniverseMember, build_price_snapshot, read_universe
from karst.gateway import Gateway
from karst.runs import RunStore, synthetic_simulation
from karst.store import FORMAL_RUN, SWEEP_RUN

# KARST-095 補上的第二批 import:種一幅完整掃描要用的執行台、掃描格與假引擎。
# 獨立成一組,不併入上面那組——上面那組是 KARST-090/093 的正本,這裡只加不改。
from types import SimpleNamespace
from typing import Any

import numpy as np

from doubles.engines import RecordingEngine
from karst.engine.contracts import CADENCES, PricePanel, SimulationOutput
from karst.executor import SAMPLE, BatchReport, Executor
from karst.executor.contract import (
    ENGINE_TARGETS,
    KIND_INTEGER,
    KIND_TEXT,
    SLOT_CADENCE,
    SLUG_VERBATIM,
    TEXT_VERBATIM,
    EntityRequest,
    FactorSpec,
    ParamField,
    ParamSpec,
    RunRequest,
    TargetPlan,
)
from karst.sweep import ProductGrid, choice_axis, continuous_axis

#: 寫入者名字。唯一入口每寫一列都蓋一個簽章,而簽章要有名字;測試沒有人手輸入,
#: 所以在這裡給一個一看就知道是測試的預設。**測試自己設了就不覆蓋**——有些測試
#: 正是要驗「換一個寫入者會怎樣」。
DEFAULT_TEST_WRITER = "karst-tests"


@pytest.fixture()
def writer_name(monkeypatch: pytest.MonkeyPatch) -> str:
    """給這個測試一個固定的寫入者名,回傳它。

    **刻意不是 autouse**:設了它就換走全部簽章的署名,而有些測試正是要驗
    「換一個寫入者會怎樣」。要用就明寫,不要由夾具悄悄改全倉的行為。
    """
    monkeypatch.setenv("KARST_WRITER", DEFAULT_TEST_WRITER)
    return DEFAULT_TEST_WRITER


@pytest.fixture()
def gateway(tmp_path, writer_name) -> Iterator[Gateway]:
    """一個開在 ``tmp_path`` 的**真庫**唯一入口。用完自動關。"""
    with Gateway.open(str(tmp_path / "karst.sqlite")) as opened:
        yield opened


@pytest.fixture()
def store(gateway: Gateway):
    """上面那個真庫的定義庫。只讀定義時用它,寫入請經 ``gateway``。"""
    return gateway.store


# ----------------------------------------------------------------------
# 種好數的臨時專案根(KARST-093):網頁層那六個測試檔的地基
# ----------------------------------------------------------------------

#: 種數用的策略、參數集與引擎。名字刻意與生產庫內那幾套**不同**,一眼看得出
#: 畫面上那幾行是種出來的,不是誰的真成績。
SEED_FACTOR = "動量·12-1 月"
SEED_FACTOR_PROCEDURE = FormulaProcedure(
    formula="close[-21] / close[-252] - 1",
    input_data_version="2026-08-30-000000000000",
)
#: 策略名**必須**是 ``api_jobs.RERUN_RECIPES`` 認得的其中一套,否則
#: ``test_web_jobs.py`` 全檔跳過——「畫面按重跑」那條路正是本票要接離生產庫的
#: 那一條,接完之後它若果一條都跑不起,等於把問題由「弄髒生產庫」換成「不再驗」。
SEED_STRATEGY = "趨勢波段"
SEED_PARAM_SET = "現役"

#: 趨勢波段那套規則引擎要的十二格取值。**逐格明寫,不設預設值**:引擎那邊沒有
#: 預設,參數集也不應該有——一格取值背後是一個決定,預設值會令那個決定變成
#: 「無人揀過但照跑」。這一組由庫內示例參數集抄過來當**測試種數**,不是誰對齊
#: 過的現役參數,亦不代表任何策略的現役設定(D-038)。
SEED_PARAM_VALUES = {
    "account.fees": "0.0",
    "account.initial_cash": "1000000.0",
    "entry.breakout_lookback_days": "50",
    "execution.tie_break_seed": "20260828",
    "risk.monthly_loss_cap": "0.06",
    "risk.per_trade_risk": "0.02",
    "risk.reward_risk_floor": "1.5",
    "sizing.equity_basis": "current_equity",
    "sizing.max_position_fraction": "0.25",
    "stop.max_stop_fraction": "0.25",
    "stop.min_stop_fraction": "0.01",
    "stop.swing_lookback_days": "10",
}
#: 掃描格那一格的參數集。名字**故意**用「掃描」開頭:運行清單有一條斷言正是
#: 「清單上不可以有參數集名以掃描開頭的項目」,種一個進去,那條斷言才驗得到
#: 它真的擋得住,而不是因為庫內根本沒有掃描格而空手過關(D-029)。
SEED_SWEEP_PARAM_SET = "掃描-測試格"
#: 引擎名**必須**同趨勢波段那條重跑路徑跑出來的一樣。引擎是運行編號的原料之一
#: (規格 7.4),種數時寫另一個名,重跑就會拒收:「引擎不同即不是同一條血統」。
SEED_ENGINE = ("vectorbt-order-func", "0.1.0")

#: 快照與運行的期間。**刻意跨過 2023-01-01**:``test_web.py`` 有四條測試要揀一段
#: 由 2023 年頭切開的視窗重看,期間不跨過那一日,它們就只會跳過,驗不到東西。
SEED_PERIOD_START = "2022-06-01"
SEED_PERIOD_END = "2023-06-30"
#: 第二次運行收早三個月。期間是運行身份的五件之一(規格 7.4),所以期間一不同
#: 就是另一個運行編號——運行清單要有兩次**不同**的運行,才換得到、比得出。
SEED_SHORT_PERIOD_END = "2023-03-31"

#: 宇宙名單三隻:SPY 是日曆基準(``build_price_snapshot`` 沒有它就不肯凍),
#: QQQ 是另一隻成績基準(``run_metrics`` 兩隻都要,缺一隻整份運行讀不出來),
#: TESTCO 是唯一一隻「拿來買賣」的股。
SEED_UNIVERSE = (
    UniverseMember("SPY", "etf", "SPDR S&P 500 ETF Trust"),
    UniverseMember("QQQ", "etf", "Invesco QQQ Trust"),
    UniverseMember("TESTCO", "company", "Test Company, Inc."),
    UniverseMember("WAVECO", "company", "Wave Company, Inc."),
)
SEED_CIK_MAP = {"TESTCO": "0000000042", "WAVECO": "0000000043"}


def _seed_bars() -> pd.DataFrame:
    """一份靜態日線,只為造得出一個真的價格快照目錄——全程不連網。

    兩隻基準(SPY、QQQ)行直線就夠:它們只做對照尺,不落注(D-010 第 4 條)。

    兩隻股**刻意行波浪**,不是直線。趨勢波段那套規則要「突破前 50 日高位」才入場、
    要「前 10 日擺動低位」做停損位——一條完美直線兩樣都給不出:突破日日都算突破,
    而擺動低位緊貼現價,停損距離近乎零,於是引擎一注都落不出。臨時庫的重跑測試
    正是要驗「改一格參數會跑出另一次運行」,跑不出交易就驗不到,所以這裡要的是
    一份**真的會出訊號**的行情,不是一份好看的行情。

    做法:上升趨勢 + 一條週期約四十日的正弦波,兩隻相位相差半個週期——兩隻同時
    見頂見底的話,揀股那一步就沒有東西可揀。
    """
    import math

    days = tuple(
        day.strftime("%Y-%m-%d")
        for day in pd.bdate_range(SEED_PERIOD_START, SEED_PERIOD_END)
    )
    rows: list[dict[str, object]] = []
    for index, day in enumerate(days):
        for ticker, base, slope, amplitude, phase in (
            ("SPY", 400.0, 0.20, 0.0, 0.0),
            ("QQQ", 300.0, 0.30, 0.0, 0.0),
            ("TESTCO", 50.0, 0.06, 6.0, 0.0),
            ("WAVECO", 80.0, 0.05, 9.0, math.pi),
        ):
            close = base + slope * index + amplitude * math.sin(index / 6.4 + phase)
            rows.append(
                {
                    "date": day,
                    "ticker": ticker,
                    "open": close - 0.10,
                    "high": close + 0.50,
                    "low": close - 0.50,
                    "close": close,
                    "volume": 1_000_000.0 + index,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def seeded_project_root(tmp_path_factory) -> Path:
    """一個**種好數的臨時專案根**,版式與倉根一模一樣,回傳它的路徑。

    版式要一模一樣,是因為網頁層有兩處會由 ``runs_root`` 倒推專案根
    (``api_sweep._project_root``、``api_jobs.JobContext``),認的正是結尾那兩級
    ``data/runs``。版式一走樣,它們就靜靜跌回 ``Path.cwd()``——即是倉根,
    那就前功盡廢:表面上接了臨時庫,重跑那條路照舊寫回生產庫。

        <root>/karst.sqlite          定義庫(唯一入口開出來,連簽章鑰匙)
        <root>/data/snapshots/…      一個真的價格快照(靜態日線,不連網)
        <root>/data/runs/…           逐次運行的淨值、持倉、交易 parquet
        <root>/experiments/          掃描落檔的地方,種數階段刻意留空

    種入的最少數:一個因子、一套策略、兩個參數集、一個價格快照、**兩次正式運行**
    (期間不同,所以是兩個編號)連**一格掃描運行**。兩次正式運行是因為「換一次
    運行整頁跟住換」要有得換;那一格掃描運行是因為「掃描格不入運行清單」要有
    東西可擋。

    全部經唯一入口寫(D-020 第 4 條):版本鏈、寫入者簽章、運行編號查重照跑一次,
    那些正是要驗的東西,造一個假的出來就等於不驗。
    """
    root = tmp_path_factory.mktemp("karst-project")
    snapshot_root = root / "data" / "snapshots"
    runs_root = root / "data" / "runs"
    for folder in (snapshot_root, runs_root, root / "experiments"):
        folder.mkdir(parents=True, exist_ok=True)

    with Gateway.open(
        str(root / "karst.sqlite"), writer=DEFAULT_TEST_WRITER
    ) as gateway:
        store = gateway.store

        snapshot = build_price_snapshot(
            store,
            start=SEED_PERIOD_START,
            end=SEED_PERIOD_END,
            universe=SEED_UNIVERSE,
            source=StaticSource(_seed_bars(), name="static-seed"),
            root=snapshot_root,
            cik_map=SEED_CIK_MAP,
            taken_on="2026-08-30",
        )
        # 落注的只有兩隻股,**不含**兩隻基準:基準只做對照尺,不落注
        # (D-010 第 4 條)。種數時連基準一齊持,選股漏斗那一條就會對不上——
        # 漏斗只數候選股,而持倉裡卻有兩隻從來不在候選名單的 ETF。
        宇宙 = read_universe(store, snapshot.snapshot_id, root=snapshot_root)
        基準 = {"SPY", "QQQ"}
        entities = tuple(
            int(entity_id)
            for ticker, entity_id in zip(宇宙["ticker"], 宇宙["entity_id"])
            if str(ticker).upper() not in 基準
        )

        # 經 ``gateway`` 而不是 ``store``:兩者都寫得入,但只有前者蓋簽章。
        # ``test_web_jobs.py`` 有一條測試會對整個臨時庫跑 ``verify``,種數階段
        # 借 store 抄近路,那一條就會反過來告種數的人繞過唯一入口。
        gateway.register_factor(
            SEED_FACTOR, scale_kind="cardinal", procedure=SEED_FACTOR_PROCEDURE
        )
        gateway.register_strategy(
            SEED_STRATEGY,
            strategy_type="technical",
            layer="stock",
            exit_governance="continuation",
            factor_refs=[SEED_FACTOR],
        )
        for name in (SEED_PARAM_SET, SEED_SWEEP_PARAM_SET):
            gateway.register_param_set(
                SEED_STRATEGY,
                param_set_name=name,
                rebalance_cadence="daily",
                values=SEED_PARAM_VALUES,
            )
        gateway.designate_active_setup(SEED_STRATEGY, param_set_name=SEED_PARAM_SET)

        runs = RunStore(store, root=runs_root)

        def record(*, period_end: str, seed: int, origin: str, **extra: object) -> None:
            runs.record_simulation(
                synthetic_simulation(
                    start=SEED_PERIOD_START,
                    end=period_end,
                    entity_ids=entities,
                    seed=seed,
                ),
                strategy_name=SEED_STRATEGY,
                snapshot_id=snapshot.snapshot_id,
                engine_name=SEED_ENGINE[0],
                engine_version=SEED_ENGINE[1],
                origin=origin,
                period_start=SEED_PERIOD_START,
                period_end=period_end,
                **extra,
            )

        record(
            period_end=SEED_PERIOD_END,
            seed=7,
            origin=FORMAL_RUN,
            param_set_name=SEED_PARAM_SET,
        )
        record(
            period_end=SEED_SHORT_PERIOD_END,
            seed=11,
            origin=FORMAL_RUN,
            param_set_name=SEED_PARAM_SET,
        )
        record(
            period_end=SEED_PERIOD_END,
            seed=23,
            origin=SWEEP_RUN,
            sweep_id="sweep-種數-001",
            param_set_name=SEED_SWEEP_PARAM_SET,
        )

    return root


# ----------------------------------------------------------------------
# 種一幅完整掃描(KARST-095):test_web_sweep.py 要的真實掃描落檔
# ----------------------------------------------------------------------
#
# KARST-093 只把 ``seeded_project_root`` 的 ``experiments/`` 留空(見上面那個
# 夾具的說明),``test_web_sweep.py`` 因此整檔跳過。這裡補上那一幅:經**策略
# 執行台的 sweep 入口**(KARST-091,``Executor.sweep``)在同一個臨時專案根種
# 一幅小型完整掃描——批次登記、逐格運行、判讀一次過經唯一入口落檔,與生產
# 掃描走的是同一條路,分別只在策略本體與引擎換了替身。

#: 掃描夾具的因子、策略、參數集名。名字刻意帶 KARST-095,一眼看得出是這張票
#: 種的掃描,不是任何人的真策略、亦不是上面 KARST-093 那組正式運行種數。
SWEEP_FACTOR = "KARST-095·掃描判讀因子"
SWEEP_STRATEGY = "KARST-095·掃描夾具策略"
SWEEP_PARAM_SET = "KARST-095·掃描起步"
SWEEP_ENGINE_VERSION = "0.1.0"
SWEEP_TICKERS = ("KRSWEEPA", "KRSWEEPB")
SWEEP_DAYS = pd.bdate_range("2021-01-04", "2022-12-30")
SWEEP_PERIOD = (str(SWEEP_DAYS[0].date()), str(SWEEP_DAYS[-1].date()))
SWEEP_ID = "KARST-095-掃描夾具"

#: 逐格的目標年化回報(判讀的輸入)。鋪成三種形狀,一格都不靠運氣:
#: mode=A、mode=B 在 x=1、x=2 同樣高(候選平原);mode=A 的 x=2、x=3 換去
#: mode=B/C 就跌穿高地門檻(山脊——沿 x 軸自己站得住,換一套 mode 就沒有了);
#: mode=C 的 x=2 獨高、四周低(孤峰)。三個判讀門檻(``SWEEP_MIN_TRADES`` /
#: ``SWEEP_LONELY_PEAK_MARGIN`` / ``SWEEP_PLATEAU_QUANTILE``)配這組數精挑
#: 出來,換一個數就要重新推導判讀結果,不要當隨手改。
SWEEP_RATES: dict[tuple[str, int], float] = {
    ("A", 1): 0.20, ("A", 2): 0.20, ("A", 3): 0.20,
    ("B", 1): 0.20, ("B", 2): 0.20, ("B", 3): 0.03,
    ("C", 1): 0.03, ("C", 2): 0.60, ("C", 3): 0.03,
}
SWEEP_MODES = ("A", "B", "C")
SWEEP_XVALUES = (1, 2, 3)
SWEEP_OBJECTIVE = "annual_return"
#: ``_SweepFixtureEngine``(``RecordingEngine`` 之上加一味)從不交訂單,成交
#: 筆數恆為零;無效格門檻因此定 0,不然九格會全部因「零成交」被判無效。
SWEEP_MIN_TRADES = 0
SWEEP_LONELY_PEAK_MARGIN = 0.05
SWEEP_PLATEAU_QUANTILE = 0.5


class _SweepFixtureContract:
    """種掃描夾具專用的玩具策略合約(見 ``karst.executor.contract.StrategyContract``)。

    只有兩格參數是掃描軸:``mode``(選擇軸,對應 ``karst.sweep`` 的「層」)與
    ``x``(連續軸)。``cadence`` 是換倉節奏那格,釘死不掃。目標比重表把
    ``mode``、``x`` 編碼進兩隻代號各自的比重,好讓 ``_SweepFixtureEngine`` 由
    比重表反推返呢一格是邊一格——同 ``tests/test_sweep.py`` 的 ``_ToyContract``
    同一手法,分別只在這裡用嘅底是 ``tests/doubles/engines.py`` 嗰個
    ``RecordingEngine``(KARST-095 票明文要求)。
    """

    strategy_type = "multifactor"
    # 兩格必填(D-058;KARST-116)。夾具策略是玩具,但它照樣要答——閘不分真假策略。
    layer = "stock"
    exit_governance = "rule_based"
    funnel_stages: tuple[str, ...] = ()
    engine_path = ENGINE_TARGETS

    def param_spec(self) -> ParamSpec:
        return ParamSpec(
            fields=(
                ParamField(
                    name="mode", kind=KIND_TEXT, what="選擇軸(掃描格的層)",
                    label="模式", choices=SWEEP_MODES,
                    text_style=TEXT_VERBATIM, slug_style=SLUG_VERBATIM,
                ),
                ParamField(
                    name="x", kind=KIND_INTEGER, what="連續軸(掃描格的鄰域)",
                    label="X", lower=1, upper=3,
                    lower_inclusive=True, upper_inclusive=True, slug_style=SLUG_VERBATIM,
                ),
                ParamField(
                    name="cadence", kind=KIND_TEXT, what="幾耐拉一次倉回目標比重",
                    label="換倉節奏", choices=tuple(sorted(CADENCES)),
                    text_style=TEXT_VERBATIM, slug_style=SLUG_VERBATIM, slot=SLOT_CADENCE,
                ),
            )
        )

    def factor_specs(self, snapshot_id: str) -> tuple[FactorSpec, ...]:
        return (
            FactorSpec(
                name=SWEEP_FACTOR,
                scale_kind="cardinal",
                procedure=FormulaProcedure(
                    formula="close[-21] / close[-252] - 1",
                    input_data_version=str(snapshot_id),
                ),
            ),
        )

    def needs_entities(self, params) -> EntityRequest:
        return EntityRequest(exposures=SWEEP_TICKERS)

    def plan(self, request: RunRequest) -> TargetPlan:
        """一張目標比重表:比重**只寫在執行日那一行**(D-021 第 3 條)。"""
        panel = request.panel
        held = sorted(request.entity(ticker).entity_id for ticker in SWEEP_TICKERS)
        execution_day = panel.dates[1]
        targets = pd.DataFrame(
            np.nan, index=panel.dates, columns=[int(e) for e in panel.entity_ids], dtype=float
        )
        targets.loc[execution_day, :] = 0.0
        mode_index = SWEEP_MODES.index(str(request.params["mode"]))
        x_value = int(request.params["x"])
        targets.loc[execution_day, held[0]] = mode_index / 1000.0
        targets.loc[execution_day, held[1]] = x_value / 1000.0
        return TargetPlan(
            targets=targets,
            cadence=str(request.params["cadence"]),
            initial_cash=100_000.0,
            fees=0.0,
            rebalances=(
                SimpleNamespace(
                    decision_date=str(panel.dates[0].date()),
                    execution_date=str(execution_day.date()),
                ),
            ),
        )


class _SweepFixtureEngine(RecordingEngine):
    """``RecordingEngine``(``tests/doubles/engines.py``)之上加一味:淨值曲線
    的年化回報由目標比重表反推的那一格話事,不是全期一條斜率。

    ``RecordingEngine`` 本身的 ``drift`` 是全批一條線,砌不出「呢格高嗰格低」
    ——判讀要驗的三種形狀(平原/山脊/孤峰)正正靠逐格不同的成績鋪出來。呼叫
    記錄(``calls``/``seen_params``)一律照舊由父類的字段接住,只有
    ``simulate`` 本身要換一條淨值線的算法,所以整個方法要覆寫,不是加一味。
    """

    def __init__(self) -> None:
        super().__init__(name="karst-095-sweep-recorder", drift=0.0)

    def simulate(self, panel: Any, targets: pd.DataFrame, params: Any) -> SimulationOutput:
        self.calls.append(targets.copy())
        self.seen_params.append(params)
        written = targets.index[targets.notna().any(axis=1)]
        row = targets.loc[written[0]]
        columns = sorted(int(column) for column in targets.columns)
        mode_index = int(round(float(row[columns[0]]) * 1000.0))
        x_value = int(round(float(row[columns[1]]) * 1000.0))
        mode = SWEEP_MODES[mode_index]
        annual_return = SWEEP_RATES[(mode, x_value)]
        daily_rate = (1.0 + annual_return) ** (1.0 / 252.0) - 1.0
        base = float(params.initial_cash)
        equity = pd.Series(
            base * np.power(1.0 + daily_rate, np.arange(len(panel.dates), dtype=float)),
            index=panel.dates, name="equity",
        )
        # 持倉一定要有非零數:落庫那關(karst/runs/registry.py 的
        # _normalise_holdings)會把全零的倉篩剩一列都不留,當成「一日都沒持過倉」
        # 拒收——同 tests/test_sweep.py 的 _ToyEngine 一樣,要交一個持過倉的形狀。
        holdings = pd.DataFrame(10.0, index=panel.dates, columns=list(panel.entity_ids))
        return SimulationOutput(equity_curve=equity, holdings=holdings, orders=())


def _sweep_fixture_panel(entity_ids: list[int]) -> PricePanel:
    """一張最細的價格面板:兩隻代號 × ``SWEEP_DAYS`` 那段日子,價格一律 100。

    ``_SweepFixtureEngine`` 不看價格,這裡只求形狀正確:代號解析得回實體、
    實體在面板裡、日子與掃描期間對得上(同 ``tests/test_sweep.py`` 的 ``_panel``)。
    """
    frame = pd.DataFrame(100.0, index=SWEEP_DAYS, columns=[int(e) for e in entity_ids])
    return PricePanel.from_frames(open=frame, close=frame)


@pytest.fixture(scope="session")
def seeded_sweep(seeded_project_root: Path) -> dict[str, Any]:
    """KARST-095:在 ``seeded_project_root`` 之上,經**策略執行台的 sweep 入口**
    (KARST-091,``Executor.sweep``)種一幅 3×3 格以內的完整掃描——批次登記、
    逐格運行、判讀一次過經唯一入口落檔,``test_web_sweep.py`` 讀的正是這一幅。

    掃描格:``mode``(選擇軸,3 個取值)× ``x``(連續軸,3 個取值)= 9 格,在
    「3×3 格以內」那句票文的字面範圍內。九格逐格的目標年化回報寫在
    ``SWEEP_RATES``,精挑到令平原、山脊、孤峰三種裁決在這一幅之內全部出現
    ——``test_四個元件由真實掃描表與判讀表畫出`` 要驗的「三個裁決標記都真的
    有格拿得到」正是靠這一點,不是隨便九個數就驗得到。
    """
    with Gateway.open(
        str(seeded_project_root / "karst.sqlite"), writer=DEFAULT_TEST_WRITER
    ) as gateway:
        store = gateway.store
        snapshot_id = store.list_snapshots()[0].snapshot_id

        entity_ids: list[int] = []
        for ticker in SWEEP_TICKERS:
            entity_id = store.register_entity(
                kind="etf", display_name=f"KARST-095 掃描夾具標的 {ticker}",
                local_code=f"ETF-{ticker}",
            )
            store.register_ticker(entity_id, ticker, valid_from="2020-01-01")
            entity_ids.append(entity_id)
        panel = _sweep_fixture_panel(entity_ids)

        runs = RunStore(store, root=seeded_project_root / "data" / "runs")
        executor = Executor(
            gateway, runs, snapshot_root=seeded_project_root / "data" / "snapshots"
        )
        contract = _SweepFixtureContract()
        engine = _SweepFixtureEngine()
        grid = ProductGrid(
            [
                choice_axis("mode", SWEEP_MODES),
                continuous_axis("x", SWEEP_XVALUES),
            ]
        )

        setup = executor.register(
            contract,
            strategy_name=SWEEP_STRATEGY,
            snapshot_id=snapshot_id,
            param_set_name=SWEEP_PARAM_SET,
            values={"mode": "A", "x": 1, "cadence": "quarterly"},
            alignment=SAMPLE,
        )

        directory = seeded_project_root / "experiments" / "KARST-095-掃描夾具"
        outcome = executor.sweep(
            contract,
            setup=setup,
            grid=grid,
            panel=panel,
            period=SWEEP_PERIOD,
            engine_version=SWEEP_ENGINE_VERSION,
            risk_free_rate=0.04,
            sweep_id=SWEEP_ID,
            param_set_prefix="KARST-095-掃描-",
            param_set_suffix="",
            base_values={"cadence": "quarterly"},
            objective=SWEEP_OBJECTIVE,
            min_trades=SWEEP_MIN_TRADES,
            lonely_peak_margin=SWEEP_LONELY_PEAK_MARGIN,
            plateau_quantile=SWEEP_PLATEAU_QUANTILE,
            report=BatchReport(directory=directory, title="KARST-095 掃描頁測試夾具"),
            engine=engine,
            benchmarks=(),
        )

    return {
        "root": seeded_project_root,
        "sweep_id": SWEEP_ID,
        "directory": directory,
        "outcome": outcome,
    }
