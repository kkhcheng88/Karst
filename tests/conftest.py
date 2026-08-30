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
            SEED_STRATEGY, strategy_type="technical", factor_refs=[SEED_FACTOR]
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
