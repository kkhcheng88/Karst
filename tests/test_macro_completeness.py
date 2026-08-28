"""KARST-061 驗收:宏觀序列的齊全度在**凍結那一刻**核對,不再靠人翻說明檔。

本檔對住票上三條驗收條件的頭兩條,證五件事:

  1. **停止講話的序列會被指名道姓講出來** —— 尾段短過主日曆、或者留空超出比例,
     凍結那一刻逐條列出,而且寫入已凍結快照的說明檔與 manifest。
  2. **齊全的序列一條都不誤報** —— 供到主日曆尾日、零留空的序列,連最嚴的門檻
     (0 日、0%)都不會報。報一堆狼來了,下一個人就會學會不看警告。
  3. **前值填補遮不住停更** —— 尾段停數兩日仍在填補上限之內,舊那張齊全度表
     (只數真有讀數／填補／留空)看上去一格留空都沒有,而尾段落後那一格照樣長大。
     ^VIX3M 那件事之所以無人察覺,正正就是因為沒有人在數這一格。
  4. **門檻是參數、沒有預設值** —— 不給門檻就凍不到快照(連函式簽名都取不到
     預設值),唯一入口那兩個旗亦是必給。
  5. **門檻不入內容雜湊** —— 同一批讀數換一套門檻,仍然是同一個快照編號。

全部離線:讀數是砌出來的,一次都不連網。
"""

from __future__ import annotations

import argparse
import inspect
import io
import json

import pandas as pd
import pytest

from karst import DefinitionStore
from karst.data import (
    ALERT_MISSING_RATIO,
    ALERT_STALE_TAIL,
    FFILL_LIMIT,
    CompletenessThresholds,
    StaticMacroSource,
    audit_macro_completeness,
    build_macro_snapshot,
    macro_completeness,
    macro_coverage,
    read_macro_completeness,
    read_macro_frame,
    read_macro_manifest,
)
from karst.data.macro import README_FILE, macro_snapshot_dir
from karst.errors import ContractViolation
from karst.gateway.cli import EXIT_OK, _data_macro, build_parser
from karst.web import api_macro

CALENDAR = tuple(
    day.strftime("%Y-%m-%d") for day in pd.bdate_range("2024-01-02", "2024-03-29")
)
CODES = ("VIX", "VIX_3M", "UST_10Y", "HY_ETF")
LEVEL = {"VIX": 16.0, "VIX_3M": 18.0, "UST_10Y": 4.0, "HY_ETF": 77.0}

# 最嚴的一套:必須供到主日曆尾日、一日都不准留空。齊全的序列在這一套下面都不報,
# 才算得上「不誤報」。
STRICT = CompletenessThresholds(max_stale_days=0, max_missing_ratio=0.0)


def _values(drop: dict[str, tuple[str, ...]] | None = None) -> pd.DataFrame:
    """砌一批合成讀數;``drop`` 指明哪一條序列在哪幾日沒有讀數。"""
    holes = drop or {}
    rows: list[dict[str, object]] = []
    for index, day in enumerate(CALENDAR):
        for code in CODES:
            if day in holes.get(code, ()):
                continue
            rows.append({"date": day, "series": code, "value": LEVEL[code] + 0.01 * index})
    return pd.DataFrame(rows)


def _build(store, root, *, thresholds, drop=None, taken_on="2026-08-29"):
    return build_macro_snapshot(
        store,
        start=CALENDAR[0],
        end=CALENDAR[-1],
        calendar=CALENDAR,
        calendar_ticker="SPY",
        thresholds=thresholds,
        codes=CODES,
        source=StaticMacroSource(_values(drop)),
        root=root,
        taken_on=taken_on,
    )


# ----------------------------------------------------------------------
# 驗收條件(一):凍結那一刻逐條列出,並寫入已凍結的快照
# ----------------------------------------------------------------------


def test_stale_tail_is_named_at_freeze_time(tmp_path):
    """尾段停數的序列,凍結那一刻就被指名道姓講出來,不必等人翻說明檔。"""
    stale_tail = CALENDAR[-10:]
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(
            store,
            tmp_path,
            thresholds=CompletenessThresholds(max_stale_days=3, max_missing_ratio=1.0),
            drop={"VIX_3M": stale_tail},
        )

        assert [alert.series for alert in snapshot.alerts] == ["VIX_3M"]
        alert = snapshot.alerts[0]
        assert alert.kind == ALERT_STALE_TAIL
        assert alert.stale_days == 10
        assert alert.last_actual == CALENDAR[-11]
        assert alert.calendar_end == CALENDAR[-1]
        # 訊息本身要講得出「短了幾多日」與「門檻是幾多」,不是一句「有問題」
        assert "VIX_3M" in alert.message
        assert "10 個交易日" in alert.message
        assert "門檻 3 日" in alert.message


def test_alert_lands_in_the_frozen_snapshot(tmp_path):
    """警報與這次用的門檻,一齊寫入已凍結快照的說明檔與 manifest,事後查得回。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(
            store,
            tmp_path,
            thresholds=CompletenessThresholds(max_stale_days=3, max_missing_ratio=1.0),
            drop={"VIX_3M": CALENDAR[-10:]},
        )
        manifest = read_macro_manifest(store, snapshot.snapshot_id, root=tmp_path)

        assert manifest["completeness_thresholds"] == {
            "max_stale_days": 3,
            "max_missing_ratio": 1.0,
        }
        assert [row["series"] for row in manifest["completeness_alerts"]] == ["VIX_3M"]
        by_code = {row["series"]: row for row in manifest["completeness"]}
        assert by_code["VIX_3M"]["stale_days"] == 10
        assert by_code["UST_10Y"]["stale_days"] == 0
        # manifest 一定要是機讀得回的(中文照原文,不轉義成 \u)
        assert json.loads(json.dumps(manifest, ensure_ascii=False))

        readme = (
            macro_snapshot_dir(store, snapshot.snapshot_id, root=tmp_path) / README_FILE
        ).read_text(encoding="utf-8")
        assert "## 七之一、齊全度核對" in readme
        assert "1 條序列超出門檻" in readme
        assert "VIX_3M" in readme
        assert "尾段落後" in readme


def test_clean_snapshot_says_so_in_the_readme(tmp_path):
    """齊全的一份,說明檔要正面寫「全部合格」——沒有警報不等於沒有核對過。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(store, tmp_path, thresholds=STRICT)
        readme = (
            macro_snapshot_dir(store, snapshot.snapshot_id, root=tmp_path) / README_FILE
        ).read_text(encoding="utf-8")
        assert f"{len(CODES)} 條序列全部合格" in readme


# ----------------------------------------------------------------------
# 驗收條件(二):齊全的序列不誤報
# ----------------------------------------------------------------------


def test_complete_series_never_fire_even_at_the_strictest_thresholds(tmp_path):
    """四條都供到主日曆尾日、零留空:連 0 日 / 0% 這一套都一條都不報。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(store, tmp_path, thresholds=STRICT)
        assert snapshot.alerts == ()

        completeness = read_macro_completeness(store, snapshot.snapshot_id, root=tmp_path)
        assert list(completeness["series"]) == sorted(CODES)
        assert set(completeness["stale_days"]) == {0}
        assert set(completeness["missing"]) == {0}
        assert set(completeness["missing_ratio"]) == {0.0}
        assert set(completeness["last_actual"]) == {CALENDAR[-1]}


def test_only_the_offending_series_is_flagged(tmp_path):
    """一條停更,不會連累其餘三條:名單上只有它一個。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(
            store,
            tmp_path,
            thresholds=STRICT,
            drop={"VIX_3M": CALENDAR[-10:]},
        )
        flagged = {alert.series for alert in snapshot.alerts}
        assert flagged == {"VIX_3M"}
        assert {"VIX", "UST_10Y", "HY_ETF"} & flagged == set()


# ----------------------------------------------------------------------
# 兩項核對各自獨立;前值填補遮不住停更
# ----------------------------------------------------------------------


def test_filled_days_do_not_hide_a_stale_tail(tmp_path):
    """尾段只停兩日,仍在填補上限之內——舊那張表一格留空都沒有,尾段落後照樣報。

    這一條正是 ^VIX3M 那件事的縮影:前值填補會把停更的頭幾日填得無影無蹤,
    只數「真有讀數／填補／留空」那三格的話,看上去完全正常。
    """
    tail = CALENDAR[-2:]
    assert len(tail) <= FFILL_LIMIT
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(
            store,
            tmp_path,
            thresholds=CompletenessThresholds(max_stale_days=1, max_missing_ratio=0.0),
            drop={"VIX_3M": tail},
        )
        completeness = read_macro_completeness(store, snapshot.snapshot_id, root=tmp_path)
        row = completeness.set_index("series").loc["VIX_3M"]

        assert int(row["missing"]) == 0          # 舊那張表看不出任何異樣
        assert int(row["filled"]) == len(tail)
        assert int(row["stale_days"]) == len(tail)   # 新那一格看得出
        assert [alert.kind for alert in snapshot.alerts] == [ALERT_STALE_TAIL]


def test_mid_window_holes_fire_on_ratio_not_on_tail(tmp_path):
    """中段有洞、尾段照供:報的是留空比例,不是尾段落後。兩項核對各自獨立。"""
    hole = CALENDAR[20:32]
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(
            store,
            tmp_path,
            thresholds=CompletenessThresholds(max_stale_days=0, max_missing_ratio=0.01),
            drop={"VIX_3M": hole},
        )
        assert [alert.series for alert in snapshot.alerts] == ["VIX_3M"]
        alert = snapshot.alerts[0]
        assert alert.kind == ALERT_MISSING_RATIO
        assert alert.stale_days == 0                       # 尾段照供,不算落後
        assert alert.missing == len(hole) - FFILL_LIMIT    # 頭三日由前值填補接住
        assert alert.last_actual == CALENDAR[-1]
        assert "留空" in alert.message


def test_both_kinds_are_reported_on_one_line(tmp_path):
    """兩項都超,一條序列仍然只出一筆,兩個理由寫在同一筆裡。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(
            store,
            tmp_path,
            thresholds=STRICT,
            drop={"VIX_3M": CALENDAR[-10:]},
        )
        assert len(snapshot.alerts) == 1
        assert snapshot.alerts[0].kind == f"{ALERT_STALE_TAIL}、{ALERT_MISSING_RATIO}"


def test_a_series_with_no_reading_at_all_is_stale_for_the_whole_calendar():
    """一個真讀數都沒有,不是「落後零日」,是由第一日起就在落後。"""
    coverage = pd.DataFrame(
        [
            {
                "series": "DEAD",
                "actual": 0,
                "filled": 0,
                "missing": len(CALENDAR),
                "first_actual": "",
                "last_actual": "",
            }
        ]
    )
    completeness = macro_completeness(coverage, CALENDAR)
    assert int(completeness.loc[0, "stale_days"]) == len(CALENDAR)
    assert float(completeness.loc[0, "missing_ratio"]) == 1.0

    alerts = audit_macro_completeness(completeness, CALENDAR, thresholds=STRICT)
    assert [alert.series for alert in alerts] == ["DEAD"]
    assert "沒有" in alerts[0].message


def test_recomputed_from_disk_matches_what_was_frozen(tmp_path):
    """由磁碟上的讀數重算,與凍結當日那一張逐格對得上——核對的是數據,不是別人的結論。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(
            store, tmp_path, thresholds=STRICT, drop={"VIX_3M": CALENDAR[-10:]}
        )
        frame = read_macro_frame(store, snapshot.snapshot_id, root=tmp_path)
        expected = macro_completeness(macro_coverage(frame), CALENDAR)
        recomputed = read_macro_completeness(store, snapshot.snapshot_id, root=tmp_path)
        pd.testing.assert_frame_equal(recomputed, expected)


# ----------------------------------------------------------------------
# 門檻是參數、無預設值;門檻不入內容雜湊
# ----------------------------------------------------------------------


def test_thresholds_are_a_required_parameter_with_no_default():
    """凍結一份沒有人核對過的宏觀快照,在簽名上就表達不出來。"""
    param = inspect.signature(build_macro_snapshot).parameters["thresholds"]
    assert param.default is inspect.Parameter.empty
    assert param.kind is inspect.Parameter.KEYWORD_ONLY


@pytest.mark.parametrize(
    "days, ratio",
    [(-1, 0.0), (0, -0.1), (0, 1.5), ("三", 0.0), (0, "一成")],
)
def test_nonsense_thresholds_are_rejected_on_the_spot(days, ratio):
    with pytest.raises(ContractViolation):
        CompletenessThresholds(max_stale_days=days, max_missing_ratio=ratio)


def test_thresholds_do_not_change_the_snapshot_id(tmp_path):
    """同一批讀數換一套門檻,仍然是同一個快照編號:門檻不是數據的一部分。"""
    lenient = CompletenessThresholds(max_stale_days=90, max_missing_ratio=1.0)
    ids = []
    for index, thresholds in enumerate((STRICT, lenient)):
        root = tmp_path / f"root{index}"
        with DefinitionStore.open(":memory:") as store:
            ids.append(
                _build(
                    store, root, thresholds=thresholds, drop={"VIX_3M": CALENDAR[-10:]}
                ).snapshot_id
            )
    assert ids[0] == ids[1]


# ----------------------------------------------------------------------
# 唯一入口:兩個旗必給,警告印得出來
# ----------------------------------------------------------------------


def _macro_argv(*extra: str) -> list[str]:
    return ["data", "macro-snapshot", "--price-snapshot", "2026-08-28-a508d635a5fa", *extra]


def test_gateway_refuses_to_freeze_without_thresholds():
    """唯一入口的兩個門檻旗是必給的:漏給即當場停低,不會靜靜用一個沒有人揀過的數。"""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(_macro_argv())
    with pytest.raises(SystemExit):
        parser.parse_args(_macro_argv("--max-stale-days", "3"))

    args = parser.parse_args(
        _macro_argv("--max-stale-days", "3", "--max-missing-ratio", "0.01")
    )
    assert args.max_stale_days == 3
    assert args.max_missing_ratio == 0.01


class _StubFetch:
    fetched_at = "2026-08-29T01:02:03+00:00"
    window = "2015-01-02~2026-08-26"
    trading_days = 2929
    row_count = 41006


class _StubGateway:
    """只接住 take_macro_snapshot 那一下,好讓輸出那一段離線驗得到。"""

    def __init__(self, snapshot) -> None:
        self._snapshot = snapshot
        self.seen: dict = {}

    def take_macro_snapshot(self, **kwargs):
        self.seen = kwargs
        return self._snapshot, _StubFetch()


def _run_cli(snapshot, *, max_stale_days=3, max_missing_ratio=0.01):
    gateway = _StubGateway(snapshot)
    args = argparse.Namespace(
        price_snapshot="2026-08-28-a508d635a5fa",
        root=None,
        price_root=None,
        series=[],
        taken_on=None,
        max_stale_days=max_stale_days,
        max_missing_ratio=max_missing_ratio,
    )
    buffer = io.StringIO()
    assert _data_macro(args, gateway, buffer) == EXIT_OK
    return gateway, buffer.getvalue()


def test_gateway_prints_the_alert_block(tmp_path):
    """超出門檻,唯一入口自己印出來——不再要人去翻說明檔第七節。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(
            store,
            tmp_path,
            thresholds=CompletenessThresholds(max_stale_days=3, max_missing_ratio=0.01),
            drop={"VIX_3M": CALENDAR[-10:]},
        )
    gateway, text = _run_cli(snapshot)

    assert "齊全度" in text
    assert "警報:1 條序列超出門檻" in text
    assert "VIX_3M" in text
    assert "停止講話" in text
    # 門檻由命令列原封不動傳到管線,不是在中間被人改過
    passed = gateway.seen["thresholds"]
    assert (passed.max_stale_days, passed.max_missing_ratio) == (3, 0.01)


def test_gateway_says_all_clear_when_nothing_is_stale(tmp_path):
    """齊全的一份,唯一入口正面講一句「全部合格」,不是靜靜不出聲。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(store, tmp_path, thresholds=STRICT)
    _, text = _run_cli(snapshot, max_stale_days=0, max_missing_ratio=0.0)

    assert f"{len(CODES)} 條序列全部合格" in text
    assert "警報" not in text


# ----------------------------------------------------------------------
# 策略詳情頁那一行:自成一個小端點
# ----------------------------------------------------------------------


class _StubReader:
    def __init__(self, store, macro_root) -> None:
        self.store = store
        self.macro_root = macro_root


def test_completeness_endpoint_serves_the_numbers_without_any_threshold(tmp_path):
    """逐條的數算得出來不必門檻;沒有給門檻就只交數,不交裁決。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(
            store, tmp_path, thresholds=STRICT, drop={"VIX_3M": CALENDAR[-10:]}
        )
        payload = api_macro.completeness(
            _StubReader(store, tmp_path), {"snapshot": [snapshot.snapshot_id]}
        )

    assert payload["snapshotId"] == snapshot.snapshot_id
    assert payload["calendarEnd"] == CALENDAR[-1]
    assert payload["tradingDays"] == len(CALENDAR)
    assert payload["seriesCount"] == len(CODES)
    assert payload["staleSeries"] == ["VIX_3M"]
    assert payload["worstStaleDays"] == 10
    # 沒有門檻 = 沒有裁決,而不是「門檻是零」——兩者在頁面上要分得開
    assert payload["thresholds"] is None
    assert payload["alerts"] == []


def test_completeness_endpoint_judges_only_when_both_thresholds_are_given(tmp_path):
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(
            store, tmp_path, thresholds=STRICT, drop={"VIX_3M": CALENDAR[-10:]}
        )
        reader = _StubReader(store, tmp_path)
        payload = api_macro.completeness(
            reader,
            {
                "snapshot": [snapshot.snapshot_id],
                "maxStaleDays": ["3"],
                "maxMissingRatio": ["1.0"],
            },
        )
        assert payload["thresholds"] == {"max_stale_days": 3, "max_missing_ratio": 1.0}
        assert [alert["series"] for alert in payload["alerts"]] == ["VIX_3M"]

        # 給一半當錯:門檻沒有預設值,補不出另一半
        with pytest.raises(ContractViolation):
            api_macro.completeness(
                reader, {"snapshot": [snapshot.snapshot_id], "maxStaleDays": ["3"]}
            )
        with pytest.raises(ContractViolation):
            api_macro.completeness(reader, {})


def test_completeness_endpoint_is_registered_on_its_own_path():
    """自成一個小端點:策略詳情那一堆壞了,這一行照樣答得出。"""
    assert "/api/macro/completeness" in api_macro.routes(object())
