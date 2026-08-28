"""KARST-067 驗收二:抓取登記加齊全度警報兩格,``karst data list`` 看得到。

KARST-061 把齊全度核對做在凍結那一刻,但結論只寫在**已凍結快照自己**的
manifest 與說明檔——庫身那一邊 ``karst data list`` 仍然看不到某份快照當日
有沒有序列停止講話,要開目錄才知道(見該票留言)。本檔證四件事:

  1. **舊庫原地補欄,既有登記一列不動** —— 第 9 版補的兩格都可以留空,所以
     ``ALTER TABLE ADD COLUMN`` 補得到,不必重建表。連 ``fetched_at`` 那個
     「第一次凍結是哪一刻」都不會在搬運途中被碰過。
  2. **留空 ≠ 零警報** —— 舊列與價格快照兩格都是空的,即「沒有核對過齊全度」;
     核對過而零警報是另一句話,正面寫出來。把前者記成 0,就是把一件沒有發生過
     的核對記成合格,與 ^VIX3M 停更 28 日仍然看似正常(假設 A-008)同一種錯。
  3. **凍結宏觀快照時寫入** —— 有序列尾段落後,警報條數與一句摘要落入登記。
  4. **``karst data list`` 看得到** —— 不必開快照目錄。

全部離線:價格由 csv 來源、宏觀讀數砌出來,一次都不連網。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_snapshot_fetch_alerts.py -q``
"""

from __future__ import annotations

import inspect
import io
import re
import sqlite3

import pandas as pd
import pytest

from karst import schema
from karst.data import CompletenessThresholds, StaticMacroSource
from karst.errors import ContractViolation
from karst.gateway import Gateway
from karst.gateway.cli import EXIT_OK, main
from karst.store import DefinitionStore

WINDOW = ("2024-01-02", "2024-01-31")
TICKERS = ("SPY", "QQQ")          # 起步名單上的 ETF 不掛 SEC CIK,整條管線一次網都不用出
CODES = ("VIX", "VIX_3M", "UST_10Y", "HY_ETF")
LEVEL = {"VIX": 16.0, "VIX_3M": 18.0, "UST_10Y": 4.0, "HY_ETF": 77.0}
STRICT = CompletenessThresholds(max_stale_days=0, max_missing_ratio=0.0)


# ----------------------------------------------------------------------
# 場景搭建(離線)
# ----------------------------------------------------------------------


@pytest.fixture()
def bars_file(tmp_path) -> str:
    """一份離線日線檔:兩隻 ETF、2024 年 1 月的營業日,價格照公式生成。"""
    rows = []
    for index, day in enumerate(pd.bdate_range(*WINDOW)):
        for ticker, base in zip(TICKERS, (470.0, 400.0)):
            close = base + index * 0.5
            rows.append(
                {
                    "date": day.date().isoformat(),
                    "ticker": ticker,
                    "open": close - 0.4,
                    "high": close + 0.6,
                    "low": close - 0.8,
                    "close": close,
                    "volume": 1_000_000 + index,
                }
            )
    path = tmp_path / "bars.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8")
    return str(path)


@pytest.fixture()
def karst(tmp_path, monkeypatch):
    """回傳一個「跑一句 karst 命令」的函數:(回傳碼, 螢幕輸出)。"""
    monkeypatch.delenv("KARST_GATEWAY_KEY", raising=False)
    monkeypatch.setenv("KARST_WRITER", "KARST-067-strategy-ledger-tidyup")
    path = str(tmp_path / "karst.sqlite")

    def run(*argv: str) -> tuple[int, str]:
        buffer = io.StringIO()
        code = main(["--store", path, *argv], out=buffer)
        return code, buffer.getvalue()

    run.path = path                                    # type: ignore[attr-defined]
    run.price_root = str(tmp_path / "snapshots")       # type: ignore[attr-defined]
    run.macro_root = str(tmp_path / "macro_snapshots")  # type: ignore[attr-defined]
    return run


def _price_snapshot(karst, bars_file: str) -> str:
    code, output = karst(
        "data", "snapshot",
        *[argument for ticker in TICKERS for argument in ("--ticker", ticker)],
        "--start", WINDOW[0], "--end", WINDOW[1],
        "--source", "csv", "--bars", bars_file,
        "--root", karst.price_root,
    )
    assert code == EXIT_OK, output
    match = re.search(r"已凍結數據快照 (\S+)", output)
    assert match, output
    return match.group(1)


def _macro_values(calendar, drop: dict[str, tuple[str, ...]] | None = None) -> pd.DataFrame:
    """砌一批合成宏觀讀數;``drop`` 指明哪一條序列在哪幾日沒有讀數。"""
    holes = drop or {}
    rows = []
    for index, day in enumerate(calendar):
        for code in CODES:
            if day in holes.get(code, ()):
                continue
            rows.append({"date": day, "series": code, "value": LEVEL[code] + 0.01 * index})
    return pd.DataFrame(rows)


def _freeze_macro(karst, price_snapshot_id: str, *, thresholds, drop=None):
    """經唯一入口凍一份宏觀快照(離線讀數),回傳(快照成果單, 抓取登記)。"""
    from karst.data import read_calendar

    with Gateway.open(karst.path) as gateway:
        calendar = read_calendar(
            gateway.store, price_snapshot_id, root=karst.price_root
        )
        return gateway.take_macro_snapshot(
            price_snapshot_id=price_snapshot_id,
            thresholds=thresholds,
            source=StaticMacroSource(_macro_values(calendar, drop)),
            root=karst.macro_root,
            price_root=karst.price_root,
            codes=CODES,
            taken_on="2026-08-29",
        )


# ----------------------------------------------------------------------
# 一、舊庫原地補欄,既有登記一列不動
# ----------------------------------------------------------------------


def _eighth_version_ddl() -> str:
    """第 9 版之前那份建表 DDL:同一份正本,剪走新加那兩欄。

    不另抄一份舊 DDL——抄一份就會與正本各走各路,而這個測試要驗的正正是
    「舊庫」與「新庫」兩邊對得上。
    """
    text = schema.ddl()
    for column in schema._ALERT_COLUMNS:
        text = re.sub(rf"^\s*{column}\s+.*\n", "", text, flags=re.M)
    statement = re.search(
        r"CREATE TABLE IF NOT EXISTS data_snapshot_fetch \(.*?\n\);", text, re.DOTALL
    )
    assert statement is not None
    for column in schema._ALERT_COLUMNS:
        assert column not in statement.group(0)
    return text


OLD_ROW = {
    "snapshot_id": "2026-08-28-000000000000",
    "fetched_at": "2026-08-28T15:00:12+00:00",
    "window_start": "2015-01-02",
    "window_end": "2026-08-26",
    "entity_count": 6,
    "row_count": 17574,
    "trading_days": 2929,
    "recorded_at": "2026-08-28T15:00:16+00:00",
}


def test_ninth_version_adds_the_cells_in_place_and_keeps_the_old_rows(tmp_path):
    """舊庫重開即補得到兩格,而原有那筆抓取登記逐格一字不變。"""
    path = str(tmp_path / "old.sqlite")
    old = sqlite3.connect(path)
    old.row_factory = sqlite3.Row
    old.executescript(_eighth_version_ddl())
    old.execute(
        "INSERT INTO data_snapshot (snapshot_id, source, taken_on, content_hash,"
        " path, universe, created_at) VALUES (?, 'yfinance', '2026-08-28', 'abc',"
        " NULL, '[]', '2026-08-28T15:00:00+00:00')",
        (OLD_ROW["snapshot_id"],),
    )
    old.execute(
        "INSERT INTO data_snapshot_fetch (snapshot_id, fetched_at, window_start,"
        " window_end, entity_count, row_count, trading_days, recorded_at)"
        " VALUES (:snapshot_id, :fetched_at, :window_start, :window_end,"
        " :entity_count, :row_count, :trading_days, :recorded_at)",
        OLD_ROW,
    )
    old.commit()
    columns_before = [r["name"] for r in old.execute("PRAGMA table_info(data_snapshot_fetch)")]
    assert "alert_count" not in columns_before
    old.close()

    # 重開一次 = 遷移一次
    with DefinitionStore.open(path) as store:
        conn = store.connection
        columns = [r["name"] for r in conn.execute("PRAGMA table_info(data_snapshot_fetch)")]
        assert columns == columns_before + ["alert_count", "alert_summary"]

        kept = dict(
            conn.execute(
                "SELECT * FROM data_snapshot_fetch WHERE snapshot_id = ?",
                (OLD_ROW["snapshot_id"],),
            ).fetchone()
        )
        # 既有登記逐格一字不變——連「第一次凍結是哪一刻」都沒有被碰過
        for key, value in OLD_ROW.items():
            assert kept[key] == value, key
        # 補出來是留空,不是零:第 9 版之前沒有人核對過這份快照的齊全度
        assert kept["alert_count"] is None and kept["alert_summary"] is None

        fetch = store.snapshot_fetch(OLD_ROW["snapshot_id"])
        assert fetch is not None and not fetch.audited

        # 遷移做過什麼,寫在庫身自己那張 schema_meta,不寫在別處的筆記
        note = conn.execute(
            "SELECT value FROM schema_meta WHERE key = ?",
            (schema.SNAPSHOT_FETCH_ALERTS_MIGRATION_KEY,),
        ).fetchone()
        assert note is not None and "1 筆抓取登記" in note["value"]
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        version = conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        ).fetchone()
        assert int(version["value"]) == schema.SCHEMA_VERSION
        assert schema.SCHEMA_VERSION >= 9   # 這兩格由第 9 版起在庫身

    # 補過一次就是新版,重開不會再補一次(欄不會多出第二份)
    with DefinitionStore.open(path) as store:
        columns = [
            r["name"]
            for r in store.connection.execute("PRAGMA table_info(data_snapshot_fetch)")
        ]
        assert columns.count("alert_count") == 1


# ----------------------------------------------------------------------
# 二、兩格是必給的,而且同生共死
# ----------------------------------------------------------------------


def test_the_two_cells_are_required_with_no_default():
    """「這份快照有沒有核對過齊全度」是呼叫方才答得出的事,補不出預設值。"""
    parameters = inspect.signature(DefinitionStore.record_snapshot_fetch).parameters
    for name in ("alert_count", "alert_summary"):
        assert parameters[name].default is inspect.Parameter.empty, name
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY, name


def test_one_cell_alone_is_refused(karst, bars_file):
    """留一格空補不出另一格:核對過就兩格都有,沒有核對過就兩格都留空。"""
    snapshot_id = _price_snapshot(karst, bars_file)
    with DefinitionStore.open(karst.path) as store:
        with pytest.raises(ContractViolation):
            store.record_snapshot_fetch(
                snapshot_id,
                fetched_at="2026-08-29T00:00:00+00:00",
                window_start=WINDOW[0],
                window_end=WINDOW[1],
                entity_count=2,
                row_count=44,
                trading_days=22,
                alert_count=1,
                alert_summary=None,
            )


# ----------------------------------------------------------------------
# 三、凍結宏觀快照時寫入;四、karst data list 看得到
# ----------------------------------------------------------------------


def test_a_stale_series_lands_in_the_registry_and_shows_in_data_list(karst, bars_file):
    """尾段落後的序列,凍結那一刻連條數帶摘要寫入抓取登記,清單上一眼看得到。"""
    price_id = _price_snapshot(karst, bars_file)
    from karst.data import read_calendar

    with DefinitionStore.open(karst.path) as store:
        calendar = read_calendar(store, price_id, root=karst.price_root)

    snapshot, fetch = _freeze_macro(
        karst, price_id, thresholds=STRICT, drop={"VIX_3M": tuple(calendar[-6:])}
    )
    assert [alert.series for alert in snapshot.alerts] == ["VIX_3M"]
    assert fetch.alert_count == 1 and fetch.audited
    # 摘要要答得出「哪一條、短了幾多日」,連當時用的是哪一把尺
    assert "VIX_3M" in fetch.alert_summary
    assert "門檻" in fetch.alert_summary

    with DefinitionStore.open(karst.path) as store:
        stored = store.snapshot_fetch(snapshot.snapshot_id)
        assert stored is not None
        assert (stored.alert_count, stored.alert_summary) == (
            fetch.alert_count,
            fetch.alert_summary,
        )

    code, output = karst("data", "list")
    assert code == EXIT_OK
    listed = [line for line in output.splitlines() if "齊全度" in line]
    assert len(listed) == 1, output          # 只有宏觀那一份核對過
    assert "警報 1 條" in listed[0]
    assert "VIX_3M" in listed[0]
    # 價格快照那一份沒有核對過齊全度,清單上不會多出一行講它「零警報」
    assert output.count("齊全度") == 1


def test_a_clean_freeze_is_recorded_as_checked_not_as_blank(karst, bars_file):
    """齊全的一份寫的是「核對過、零警報」,而不是留白——留白是另一句話。"""
    price_id = _price_snapshot(karst, bars_file)
    snapshot, fetch = _freeze_macro(karst, price_id, thresholds=STRICT)

    assert snapshot.alerts == ()
    assert fetch.alert_count == 0 and fetch.audited
    assert f"{len(CODES)} 條序列全部合格" in fetch.alert_summary

    code, output = karst("data", "list")
    assert code == EXIT_OK
    assert "警報 0 條" in output
    assert f"{len(CODES)} 條序列全部合格" in output


def test_a_price_snapshot_is_recorded_as_never_audited(karst, bars_file):
    """價格快照沒有第二把尺可以核它的尾段:兩格留空,清單上一行都不多。"""
    snapshot_id = _price_snapshot(karst, bars_file)
    with DefinitionStore.open(karst.path) as store:
        fetch = store.snapshot_fetch(snapshot_id)
        assert fetch is not None
        assert (fetch.alert_count, fetch.alert_summary) == (None, None)
        assert not fetch.audited
        assert store.list_snapshots()[0].alert_count is None

    code, output = karst("data", "list")
    assert code == EXIT_OK
    assert snapshot_id in output
    assert "齊全度" not in output
