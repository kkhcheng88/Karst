"""KARST-087 驗收:數據快照登記收入治理清單,凍結一律經唯一入口簽章。

票上四項:
  1. 治理清單含數據快照登記與抓取登記;繞過那道門直接寫一列快照登記,``verify`` 點名。
  2. 定義庫本身不再受理無簽章的快照登記——裸的 ``DefinitionStore`` 凍不入,一列都不寫。
  3. 收窄之前落庫那批舊列由補簽命令補回,逐列留痕(誰、幾時、為什麼)。
  4. ``verify`` 報告分**定義、因子批次、快照**三類,各自講清白與否。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_snapshot_governance.py -q``
"""

from __future__ import annotations

import io
import sqlite3

import pytest

from karst.errors import ContractViolation
from karst.gateway import Gateway
from karst.gateway import ledger
from karst.gateway.cli import main
from karst.store import DefinitionStore

FETCH = {
    "fetched_at": "2026-08-30T09:00:00",
    "window_start": "2026-01-02",
    "window_end": "2026-08-28",
    "entity_count": 3,
    "row_count": 120,
    "trading_days": 40,
    "alert_count": None,
    "alert_summary": None,
}


@pytest.fixture()
def gateway(tmp_path, monkeypatch):
    monkeypatch.delenv("KARST_GATEWAY_KEY", raising=False)
    with Gateway.open(str(tmp_path / "karst.sqlite"), writer="KARST-087-test") as opened:
        yield opened


def _freeze(gateway: Gateway, digest: str) -> str:
    """經唯一入口登記一個快照連它的抓取登記,回傳快照編號。

    刻意不經凍結管線:本檔核的是**登記那一列有沒有簽章**,不是管線算得對不對。
    """
    snapshot_id = gateway.store.register_snapshot(
        source="csv", taken_on="2026-08-30", content_hash=digest
    )
    gateway.store.record_snapshot_fetch(snapshot_id, **FETCH)
    return snapshot_id


# ----------------------------------------------------------------------
# 一、治理清單
# ----------------------------------------------------------------------


def test_governed_tables_cover_snapshot_registration():
    """數據快照登記與抓取登記在治理清單內——以前只有「除名」在,「登記」不在。"""
    assert "data_snapshot" in ledger.GOVERNED_TABLES
    assert "data_snapshot_fetch" in ledger.GOVERNED_TABLES
    assert ledger.GOVERNED_TABLES["data_snapshot"] == ("snapshot_id",)
    assert ledger.GOVERNED_TABLES["data_snapshot_fetch"] == ("snapshot_id",)


def test_every_governed_table_has_a_category():
    """兩份清單逐張表對得上:治理清單加一張表而忘記講它屬報告哪一類,這裡就會紅。"""
    assert set(ledger.TABLE_CATEGORIES) == set(ledger.GOVERNED_TABLES)
    assert set(ledger.TABLE_CATEGORIES.values()) == set(ledger.CATEGORIES)


def test_snapshot_registration_written_behind_the_gate_is_signed(gateway):
    snapshot_id = _freeze(gateway, "aaaaaaaaaaaa")
    signed = {
        (row["table_name"], row["row_key"]): row["writer"]
        for row in gateway.store.connection.execute(
            "SELECT table_name, row_key, writer FROM gateway_write"
        )
    }
    assert signed[("data_snapshot", snapshot_id)] == "KARST-087-test"
    assert signed[("data_snapshot_fetch", snapshot_id)] == "KARST-087-test"
    assert gateway.verify() == []


def test_direct_write_of_a_snapshot_row_is_named_by_verify(gateway):
    """驗收條件原句:直接寫庫的快照登記被 verify 點名。"""
    _freeze(gateway, "aaaaaaaaaaaa")
    with gateway.store.connection:
        gateway.store.connection.execute(
            "INSERT INTO data_snapshot (snapshot_id, source, taken_on, content_hash, path,"
            " universe, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("2026-08-30-bbbbbbbbbbbb", "csv", "2026-08-30", "bbbbbbbbbbbb", None, "[]",
             "2026-08-30T00:00:00"),
        )
    findings = gateway.verify()
    named = [
        finding for finding in findings
        if finding.table == "data_snapshot" and finding.row_key == "2026-08-30-bbbbbbbbbbbb"
    ]
    assert len(named) == 1
    assert named[0].problem == ledger.UNSIGNED
    assert named[0].category == ledger.CATEGORY_SNAPSHOT


# ----------------------------------------------------------------------
# 二、定義庫不再受理無簽章的快照登記
# ----------------------------------------------------------------------


def test_bare_store_cannot_register_a_snapshot(tmp_path):
    """拎一個裸庫身來凍,當場拒收,而且庫內一列都不寫。"""
    with DefinitionStore.open(str(tmp_path / "bare.sqlite")) as bare:
        with pytest.raises(ContractViolation) as error:
            bare.register_snapshot(
                source="csv", taken_on="2026-08-30", content_hash="cccccccccccc"
            )
        assert "唯一入口" in str(error.value)
        left = bare.connection.execute("SELECT COUNT(*) AS n FROM data_snapshot").fetchone()["n"]
        assert left == 0


def test_bare_store_cannot_record_a_snapshot_fetch(gateway, tmp_path):
    """抓取登記同制:快照編號刻意不含抓取時間,那幾格只此一份,一樣要經那道門。"""
    snapshot_id = gateway.store.register_snapshot(
        source="csv", taken_on="2026-08-30", content_hash="dddddddddddd"
    )
    with DefinitionStore.open(gateway.path) as bare:
        with pytest.raises(ContractViolation) as error:
            bare.record_snapshot_fetch(snapshot_id, **FETCH)
        assert "唯一入口" in str(error.value)
        left = bare.connection.execute(
            "SELECT COUNT(*) AS n FROM data_snapshot_fetch"
        ).fetchone()["n"]
        assert left == 0


def test_a_signer_that_does_not_sign_writes_nothing(tmp_path):
    """簽章手不做事 = 寫不入。寧可寫不入,不要寫入一列無憑無據的快照登記。"""
    with DefinitionStore.open(str(tmp_path / "lazy.sqlite")) as store:
        store.attach_snapshot_signer(lambda table, primary_key: None)
        with pytest.raises(ContractViolation) as error:
            store.register_snapshot(
                source="csv", taken_on="2026-08-30", content_hash="eeeeeeeeeeee"
            )
        assert "沒有留下簽章" in str(error.value)
        left = store.connection.execute("SELECT COUNT(*) AS n FROM data_snapshot").fetchone()["n"]
        assert left == 0


# ----------------------------------------------------------------------
# 三、補簽
# ----------------------------------------------------------------------


def test_countersign_signs_the_legacy_rows_and_leaves_a_trace(gateway):
    """補簽把收窄之前那批無簽章的舊列補回,並逐列留痕:誰、幾時、為什麼。"""
    _freeze(gateway, "aaaaaaaaaaaa")
    with gateway.store.connection:  # 造一列「收窄之前落庫」的舊帳
        gateway.store.connection.execute(
            "INSERT INTO data_snapshot (snapshot_id, source, taken_on, content_hash, path,"
            " universe, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("2026-08-30-bbbbbbbbbbbb", "csv", "2026-08-30", "bbbbbbbbbbbb", None, "[]",
             "2026-08-30T00:00:00"),
        )
    assert gateway.verify() != []

    done = gateway.countersign_snapshots(reason="治理清單收窄之前落庫的舊列")
    assert [(item.table, item.row_key) for item in done] == [
        ("data_snapshot", "2026-08-30-bbbbbbbbbbbb")
    ]
    assert done[0].writer == "KARST-087-test"
    assert gateway.verify() == []

    trace = ledger.countersigned_rows(gateway.store.connection)
    assert len(trace) == 1
    assert trace[0]["table_name"] == "data_snapshot"
    assert trace[0]["row_key"] == "2026-08-30-bbbbbbbbbbbb"
    assert trace[0]["countersigned_by"] == "KARST-087-test"
    assert trace[0]["reason"] == "治理清單收窄之前落庫的舊列"
    assert trace[0]["countersigned_at"]


def test_countersign_leaves_already_signed_rows_alone(gateway):
    """補簽是補「無」,不是覆蓋「有」:全部有簽章時,一列都不補、不多留一行痕跡。"""
    _freeze(gateway, "aaaaaaaaaaaa")
    assert gateway.countersign_snapshots(reason="無事可做") == ()
    assert ledger.countersigned_rows(gateway.store.connection) == []


def test_countersigning_a_signed_row_is_refused(gateway):
    snapshot_id = _freeze(gateway, "aaaaaaaaaaaa")
    with pytest.raises(ContractViolation) as error:
        ledger.countersign(
            gateway.store.connection,
            b"key",
            "data_snapshot",
            snapshot_id,
            writer="偷雞者",
            reason="想蓋過去",
        )
    assert "已經有簽章" in str(error.value)


def test_countersign_needs_a_reason(gateway):
    _freeze(gateway, "aaaaaaaaaaaa")
    with pytest.raises(ContractViolation):
        gateway.countersign_snapshots(reason="   ")


def test_countersign_stops_when_a_signature_does_not_check_out(tmp_path, monkeypatch):
    """簽章對不上就整道停手,一列都不補——那種情況補簽解決不了,亦不應由補簽蓋走痕跡。"""
    path = str(tmp_path / "karst.sqlite")
    monkeypatch.setenv("KARST_GATEWAY_KEY", "第一把鑰匙")
    with Gateway.open(path, writer="KARST-087-test") as gateway:
        _freeze(gateway, "aaaaaaaaaaaa")

    monkeypatch.setenv("KARST_GATEWAY_KEY", "另一把鑰匙")
    with Gateway.open(path, writer="KARST-087-test") as other:
        assert any(
            finding.problem == ledger.FORGED and finding.category == ledger.CATEGORY_SNAPSHOT
            for finding in other.verify()
        )
        with pytest.raises(ContractViolation) as error:
            other.countersign_snapshots(reason="想補簽")
        assert "簽章對不上" in str(error.value)
        assert ledger.countersigned_rows(other.store.connection) == []


def test_countersign_trace_cannot_be_changed_or_deleted(gateway):
    """補簽留痕只加不改不刪:補簽的理由是一件已經發生的事。"""
    with gateway.store.connection:
        gateway.store.connection.execute(
            "INSERT INTO data_snapshot (snapshot_id, source, taken_on, content_hash, path,"
            " universe, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("2026-08-30-bbbbbbbbbbbb", "csv", "2026-08-30", "bbbbbbbbbbbb", None, "[]",
             "2026-08-30T00:00:00"),
        )
    gateway.countersign_snapshots(reason="舊列")
    with pytest.raises(sqlite3.IntegrityError):
        with gateway.store.connection:
            gateway.store.connection.execute(
                "UPDATE gateway_countersign SET reason = ?", ("改個講法",)
            )
    with pytest.raises(sqlite3.IntegrityError):
        with gateway.store.connection:
            gateway.store.connection.execute("DELETE FROM gateway_countersign")


# ----------------------------------------------------------------------
# 四、verify 報告分三類
# ----------------------------------------------------------------------


def test_verify_report_has_three_categories(gateway):
    _freeze(gateway, "aaaaaaaaaaaa")
    verdicts = gateway.verify_report()
    assert [verdict.category for verdict in verdicts] == list(ledger.CATEGORIES)
    assert [verdict.category for verdict in verdicts] == ["定義", "因子批次", "快照"]
    assert all(verdict.clean for verdict in verdicts)
    by_category = {verdict.category: verdict for verdict in verdicts}
    assert by_category["快照"].row_count == 2  # 登記 + 抓取登記
    assert by_category["定義"].row_count == 0


def test_a_dirty_snapshot_does_not_dirty_the_other_two_categories(gateway):
    """快照髒了是取數的源頭被人動過,與定義、因子批次是三件事,報告要分得開。"""
    _freeze(gateway, "aaaaaaaaaaaa")
    with gateway.store.connection:
        gateway.store.connection.execute(
            "INSERT INTO data_snapshot (snapshot_id, source, taken_on, content_hash, path,"
            " universe, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("2026-08-30-bbbbbbbbbbbb", "csv", "2026-08-30", "bbbbbbbbbbbb", None, "[]",
             "2026-08-30T00:00:00"),
        )
    by_category = {verdict.category: verdict for verdict in gateway.verify_report()}
    assert not by_category["快照"].clean
    assert by_category["定義"].clean
    assert by_category["因子批次"].clean
    assert "揪到 1 處" in by_category["快照"].describe()


# ----------------------------------------------------------------------
# 五、命令列同一道門
# ----------------------------------------------------------------------


def test_cli_verify_prints_three_categories(tmp_path, monkeypatch):
    monkeypatch.delenv("KARST_GATEWAY_KEY", raising=False)
    monkeypatch.setenv("KARST_WRITER", "KARST-087-cli")
    path = str(tmp_path / "karst.sqlite")
    with Gateway.open(path) as gateway:
        _freeze(gateway, "aaaaaaaaaaaa")

    buffer = io.StringIO()
    assert main(["--store", path, "verify"], out=buffer) == 0
    printed = buffer.getvalue()
    assert "定義:清白" in printed
    assert "因子批次:清白" in printed
    assert "快照:清白" in printed


def test_cli_countersigns_and_turns_the_snapshot_category_clean(tmp_path, monkeypatch):
    monkeypatch.delenv("KARST_GATEWAY_KEY", raising=False)
    monkeypatch.setenv("KARST_WRITER", "KARST-087-cli")
    path = str(tmp_path / "karst.sqlite")
    with Gateway.open(path) as gateway:
        _freeze(gateway, "aaaaaaaaaaaa")
        with gateway.store.connection:
            gateway.store.connection.execute(
                "INSERT INTO data_snapshot (snapshot_id, source, taken_on, content_hash, path,"
                " universe, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("2026-08-30-bbbbbbbbbbbb", "csv", "2026-08-30", "bbbbbbbbbbbb", None, "[]",
                 "2026-08-30T00:00:00"),
            )

    dirty = io.StringIO()
    assert main(["--store", path, "verify"], out=dirty) == 3
    assert "快照:揪到 1 處不合格" in dirty.getvalue()

    signing = io.StringIO()
    assert main(
        ["--store", path, "data", "countersign-snapshots",
         "--reason", "治理清單收窄之前落庫的舊列"],
        out=signing,
    ) == 0
    assert "已補簽 1 列快照登記" in signing.getvalue()

    clean = io.StringIO()
    assert main(["--store", path, "verify"], out=clean) == 0
    assert "快照:清白" in clean.getvalue()
