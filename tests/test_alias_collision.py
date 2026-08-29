"""KARST-084 驗收:同一個實體收到多過一條代號序列,凍結時有明文結果。

`anchor_map_for_window` 一直只擋「一個代號錨到兩個實體」;反方向那一格
——兩個代號錨到同一個實體——直到 KARST-083 的 BBT/TFC、EQR/VMRK 才浮出來,
之前是由**後寫覆蓋先寫**靜靜決定留哪條。本檔證三件事:

  1. 規則本身(生效期未結束優先 → 日線較多優先 → 分不出兩條都剔)逐格算得對。
  2. 凍結時真的會觸發,而且每次觸發逐條寫入快照說明檔。
  3. 三數等式(宇宙表代號數 = 實體數 + 剔除數)在快照上核得到。
"""

from __future__ import annotations

import pandas as pd
import pytest

from karst import DefinitionStore
from karst.data import (
    StaticSource,
    UniverseMember,
    build_price_snapshot,
    read_manifest,
    read_universe,
    universe_balance,
)
from karst.data.snapshots import README_FILE, UniverseBalance, snapshot_dir
from karst.data.ticker_history import (
    AliasCandidate,
    TickerAnchor,
    anchor_map_for_window,
    resolve_alias_collisions,
    valid_to_for_window,
)

CALENDAR_DAYS = tuple(
    day.strftime("%Y-%m-%d") for day in pd.bdate_range("2024-01-02", "2024-02-29")
)

# 同一個實體(0000000042)收到兩條代號序列:OLDCO 已經退役,NEWCO 仍然在用。
SHARED_CIK = "0000000042"

UNIVERSE = (
    UniverseMember("SPY", "etf", "SPDR S&P 500 ETF Trust"),
    UniverseMember("OLDCO", "company", "Old Co, Inc."),
    UniverseMember("NEWCO", "company", "New Co, Inc."),
)
CIK_MAP = {"OLDCO": SHARED_CIK, "NEWCO": SHARED_CIK}


@pytest.fixture()
def store():
    with DefinitionStore.open(":memory:") as opened:
        yield opened


def _bars(*, oldco_days: int) -> pd.DataFrame:
    """SPY 全期有成交;OLDCO 只有頭 ``oldco_days`` 日;NEWCO 全期都有。"""
    rows: list[dict[str, object]] = []
    for index, day in enumerate(CALENDAR_DAYS):
        rows.append(
            {
                "date": day,
                "ticker": "SPY",
                "open": 400.0 + index,
                "high": 401.0 + index,
                "low": 399.0 + index,
                "close": 400.5 + index,
                "volume": 1_000_000.0 + index,
            }
        )
        rows.append(
            {
                "date": day,
                "ticker": "NEWCO",
                "open": 50.0 + index,
                "high": 51.0 + index,
                "low": 49.0 + index,
                "close": 50.5 + index,
                "volume": 2_000.0 + index,
            }
        )
        if index < oldco_days:
            rows.append(
                {
                    "date": day,
                    "ticker": "OLDCO",
                    "open": 18.0 + index,
                    "high": 19.0 + index,
                    "low": 17.0 + index,
                    "close": 18.5 + index,
                    "volume": 3_000.0 + index,
                }
            )
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# 一、規則本身
# ----------------------------------------------------------------------


def test_live_ticker_wins():
    """兩個代號同一實體、其中一條生效期未結束:留未結束那條,即使它日線較少。"""
    verdicts = resolve_alias_collisions(
        [
            AliasCandidate(ticker="BBT", cik=SHARED_CIK, valid_to="2019-12-06", bar_count=1_700),
            AliasCandidate(ticker="TFC", cik=SHARED_CIK, valid_to="", bar_count=1_200),
        ]
    )
    assert len(verdicts) == 1
    assert verdicts[0].kept == "TFC"
    assert verdicts[0].dropped == ("BBT",)
    assert "生效期未結束" in verdicts[0].reason


def test_more_bars_wins_when_both_retired():
    """兩條生效期都結束了:取真實日線較多的那條。"""
    verdicts = resolve_alias_collisions(
        [
            AliasCandidate(ticker="AAA", cik=SHARED_CIK, valid_to="2020-01-01", bar_count=40),
            AliasCandidate(ticker="BBB", cik=SHARED_CIK, valid_to="2021-01-01", bar_count=900),
        ]
    )
    assert verdicts[0].kept == "BBB"
    assert verdicts[0].dropped == ("AAA",)
    assert "日線較多" in verdicts[0].reason


def test_more_bars_wins_when_both_live():
    """兩條生效期都未結束(EQR/VMRK 那一格):同樣取日線較多的那條。"""
    verdicts = resolve_alias_collisions(
        [
            AliasCandidate(ticker="EQR", cik=SHARED_CIK, valid_to="", bar_count=2_900),
            AliasCandidate(ticker="VMRK", cik=SHARED_CIK, valid_to="", bar_count=120),
        ]
    )
    assert verdicts[0].kept == "EQR"
    assert verdicts[0].dropped == ("VMRK",)


def test_tie_drops_both():
    """生效期同樣結束、日線又一樣多:分不出高下,兩條都剔,不猜。"""
    verdicts = resolve_alias_collisions(
        [
            AliasCandidate(ticker="AAA", cik=SHARED_CIK, valid_to="2020-01-01", bar_count=500),
            AliasCandidate(ticker="BBB", cik=SHARED_CIK, valid_to="2020-06-30", bar_count=500),
        ]
    )
    assert verdicts[0].kept == ""
    assert verdicts[0].dropped == ("AAA", "BBB")
    assert "分不出高下" in verdicts[0].reason


def test_no_collision_is_silent():
    """每個實體只收到一條序列,以及佔位錨:一格都不觸發。"""
    assert (
        resolve_alias_collisions(
            [
                AliasCandidate(ticker="AAA", cik="0000000001", valid_to="", bar_count=10),
                AliasCandidate(ticker="BBB", cik="0000000002", valid_to="", bar_count=10),
                AliasCandidate(ticker="CCC", cik="PLACEHOLDER-CCC", valid_to="", bar_count=10),
                AliasCandidate(ticker="DDD", cik="PLACEHOLDER-DDD", valid_to="", bar_count=10),
            ]
        )
        == ()
    )


# ----------------------------------------------------------------------
# 二、凍結時真的觸發,而且逐條寫入說明檔
# ----------------------------------------------------------------------


def test_freeze_drops_alias_and_writes_it_down(store, tmp_path):
    snapshot = build_price_snapshot(
        store,
        start=CALENDAR_DAYS[0],
        end=CALENDAR_DAYS[-1],
        universe=UNIVERSE,
        source=StaticSource(_bars(oldco_days=12), name="static-test"),
        root=tmp_path,
        cik_map=CIK_MAP,
        anchor_valid_to={"OLDCO": "2023-06-30", "NEWCO": ""},
        taken_on="2026-08-30",
    )

    universe = read_universe(store, snapshot.snapshot_id)
    assert sorted(universe["ticker"]) == ["NEWCO", "SPY"]

    manifest = read_manifest(store, snapshot.snapshot_id)
    assert manifest["universe_tickers"] == 3
    assert manifest["entities"] == 2
    assert manifest["alias_dropped"] == 1
    assert manifest["universe_tickers"] == manifest["entities"] + manifest["alias_dropped"]

    verdicts = manifest["alias_verdicts"]
    assert len(verdicts) == 1
    assert verdicts[0]["cik"] == SHARED_CIK
    assert verdicts[0]["kept"] == "NEWCO"
    assert verdicts[0]["dropped"] == ["OLDCO"]

    readme = (snapshot_dir(store, snapshot.snapshot_id) / README_FILE).read_text(
        encoding="utf-8"
    )
    assert "同實體別名裁決" in readme
    assert "OLDCO" in readme
    assert "3 代號 = 2 實體 + 1 剔除;對得上" in readme


def test_freeze_without_collision_says_so(store, tmp_path):
    """沒有撞的快照,說明檔一樣要講明「一次都沒有觸發」——沉默不等於核過。"""
    snapshot = build_price_snapshot(
        store,
        start=CALENDAR_DAYS[0],
        end=CALENDAR_DAYS[-1],
        universe=UNIVERSE,
        source=StaticSource(_bars(oldco_days=12), name="static-test"),
        root=tmp_path,
        cik_map={"OLDCO": "0000000041", "NEWCO": SHARED_CIK},
        anchor_valid_to={"OLDCO": "", "NEWCO": ""},
        taken_on="2026-08-30",
    )
    manifest = read_manifest(store, snapshot.snapshot_id)
    assert manifest["alias_dropped"] == 0
    assert manifest["universe_tickers"] == manifest["entities"] == 3
    readme = (snapshot_dir(store, snapshot.snapshot_id) / README_FILE).read_text(
        encoding="utf-8"
    )
    assert "一次都沒有觸發" in readme


# ----------------------------------------------------------------------
# 三、三數等式
# ----------------------------------------------------------------------


def test_universe_balance_holds_after_gate(store, tmp_path):
    snapshot = build_price_snapshot(
        store,
        start=CALENDAR_DAYS[0],
        end=CALENDAR_DAYS[-1],
        universe=UNIVERSE,
        source=StaticSource(_bars(oldco_days=12), name="static-test"),
        root=tmp_path,
        cik_map=CIK_MAP,
        anchor_valid_to={"OLDCO": "2023-06-30", "NEWCO": ""},
        taken_on="2026-08-30",
    )
    balance = universe_balance(store, snapshot.snapshot_id)
    assert balance.universe_tickers == 3
    assert balance.entities == 2
    assert balance.alias_dropped == 1
    assert balance.declared is True
    assert balance.balances is True
    assert "對得上" in balance.describe()


def test_universe_balance_catches_a_swallowed_series():
    """凍結於這道閘之前的快照:三個代號只剩兩個實體,等式即當場對不上。"""
    balance = UniverseBalance(
        snapshot_id="2026-08-28-000000000000",
        universe_tickers=3,
        entities=2,
        rows=3,
        alias_dropped=0,
        declared=False,
    )
    assert balance.balances is False
    assert "對不上" in balance.describe()
    assert "以 0 核" in balance.describe()


# ----------------------------------------------------------------------
# 四、生效訖由對照表挑出來,與挑錨用同一條規矩
# ----------------------------------------------------------------------


def test_valid_to_matches_the_anchor_map():
    anchors = (
        TickerAnchor("TFC", SHARED_CIK, "2019-12-09", "", "Truist", "今日對照", ""),
        TickerAnchor("BBT", SHARED_CIK, "1996-01-02", "2019-12-06", "BB&T", "今日對照·已核實", ""),
    )
    window = {"start": "2015-01-02", "end": "2026-08-28"}
    assert anchor_map_for_window(anchors, **window) == {"TFC": SHARED_CIK, "BBT": SHARED_CIK}
    assert valid_to_for_window(anchors, **window) == {"TFC": "", "BBT": "2019-12-06"}
