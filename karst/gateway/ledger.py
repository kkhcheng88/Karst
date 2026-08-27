"""寫入者簽章(writer signature):證明一列是經唯一入口寫入的。

D-020 第 4 條要求「任何人或 agent 都不可繞過直接寫庫」。庫檔本身的 sqlite
trigger 已擋住**改寫與刪除**,但擋不住有人直接 ``INSERT`` 一行新定義進去。
這一層補上餘下那半:

* 凡經唯一入口寫入的列,都在 ``gateway_write`` 留一筆——內容雜湊 + 簽章。
* 簽章的鑰匙**住在庫檔以外**(環境變數,或庫檔旁的鑰匙檔),所以拿得到庫檔
  不等於簽得出章。
* ``karst verify`` 逐列核對:無簽章 = 繞過唯一入口寫入;簽章對不上 = 落庫後被改。

鑰匙檔遺失只會令核對報「簽章對不上」,不會令庫檔讀不到——治理是揪得出,不是加密。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..errors import ImmutabilityViolation

# 鑰匙:環境變數優先,其次庫檔旁的鑰匙檔
GATEWAY_KEY_ENV = "KARST_GATEWAY_KEY"
KEY_SUFFIX = ".gateway-key"

IN_MEMORY = ":memory:"

# 受治理的表 → 主鍵欄位。定義類的表全部在此;因子值(factor_value)不在——
# 它已由 trigger 鎖死不可改不可刪,且掛在已簽章的因子版本之下,逐值簽章代價
# 與它的行數不相稱(KARST-022 範圍註明)。
GOVERNED_TABLES: dict[str, tuple[str, ...]] = {
    "factor": ("factor_id",),
    "factor_version": ("factor_version_id",),
    "strategy": ("strategy_id",),
    "strategy_version": ("strategy_version_id",),
    "strategy_factor_ref": ("strategy_version_id", "factor_version_id"),
    "param_set": ("param_set_id",),
    "param_value": ("param_set_id", "param_key"),
    # KARST-035 補上的三張:指定現役設定、登記共用風控規則、記策略引用了哪幾條。
    # 三者都是「決定跑什麼」的定義級動作——現役設定決定門面八個數字取哪一次運行,
    # 風控規則是全平台唯一那份正本——故與策略定義同一道門、同一種簽章。
    "active_setup": ("strategy_id", "seq_no"),
    "risk_rule": ("risk_rule_id",),
    "strategy_risk_ref": ("strategy_version_id", "risk_rule_id"),
}

UNSIGNED = "未經唯一入口寫入"
TAMPERED = "落庫後被改動"
FORGED = "簽章對不上"
ORPHANED = "簽章在案但庫內查無此列"


@dataclass(frozen=True, slots=True)
class Finding:
    """核對揪到的一處不合格。"""

    table: str
    row_key: str
    problem: str
    detail: str

    def __str__(self) -> str:
        return f"{self.problem}:{self.table}[{self.row_key}] — {self.detail}"


def key_file_for(store_path: str) -> Path:
    return Path(str(store_path) + KEY_SUFFIX)


def load_or_create_key(store_path: str) -> bytes:
    """取簽章鑰匙:環境變數 > 庫檔旁的鑰匙檔 > 新造一把。

    ``:memory:`` 的庫沒有落腳處,鑰匙只存活於本程序之內。
    """
    from_env = os.environ.get(GATEWAY_KEY_ENV)
    if from_env and from_env.strip():
        return from_env.strip().encode("utf-8")
    if store_path == IN_MEMORY:
        return secrets.token_bytes(32)

    path = key_file_for(store_path)
    if path.exists():
        return path.read_text(encoding="ascii").strip().encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32)
    path.write_text(key, encoding="ascii")
    try:  # POSIX 才有意思;Windows 上不成功也不影響
        path.chmod(0o600)
    except OSError:  # pragma: no cover - 平台差異
        pass
    return key.encode("utf-8")


def row_key_of(pk_columns: Sequence[str], row: sqlite3.Row) -> str:
    return "|".join(str(row[column]) for column in pk_columns)


def content_digest(table: str, row: sqlite3.Row) -> str:
    """一列的內容雜湊:欄名排序後整列入雜湊,改動任何一欄都變。"""
    fields = {key: row[key] for key in row.keys()}
    payload = json.dumps(
        {"table": table, "fields": fields},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sign(key: bytes, digest: str) -> str:
    return hmac.new(key, digest.encode("ascii"), hashlib.sha256).hexdigest()


def _row_fingerprint(
    conn: sqlite3.Connection, table: str, primary_key: Sequence[object]
) -> tuple[str, str]:
    """取一列的 row key 與內容雜湊。查無此列即拋錯——簽不到不存在的東西。"""
    pk_columns = GOVERNED_TABLES[table]
    where = " AND ".join(f'"{column}" = ?' for column in pk_columns)
    row = conn.execute(
        f'SELECT * FROM "{table}" WHERE {where}', tuple(primary_key)
    ).fetchone()
    if row is None:  # pragma: no cover - 寫入後即讀,理應必中
        raise LookupError(f"{table} 查無主鍵 {tuple(primary_key)},簽不到章")
    return row_key_of(pk_columns, row), content_digest(table, row)


def record_write_once(
    conn: sqlite3.Connection,
    key: bytes,
    table: str,
    primary_key: Sequence[object],
    *,
    writer: str,
) -> str:
    """為一列蓋簽章;已經蓋過就原封不動回它的 row key。

    治理清單裡有幾件登記是**重覆呼叫回同一批列**的:三條風控規則的正本、
    策略引用了哪幾條、指同一個現役設定兩次。那些列一經落庫即不可改(trigger
    擋住),所以同一列第二次經入口走過,原本那個簽章照舊有效,不必再蓋一次。

    若庫內那一列的內容與當初簽的對不上,即是有人繞過 trigger 改過它——當場拋錯,
    不會用新內容蓋一個新簽章把痕跡蓋走。
    """
    key_text, digest = _row_fingerprint(conn, table, primary_key)
    existing = conn.execute(
        "SELECT content_digest FROM gateway_write WHERE table_name = ? AND row_key = ?",
        (table, key_text),
    ).fetchone()
    if existing is not None:
        if existing["content_digest"] != digest:
            raise ImmutabilityViolation(
                f"{table}[{key_text}] 已有簽章,但庫內的內容與當初登記的對不上;"
                "落庫後被改過的列不會重新簽章,請按版本鏈重新經唯一入口登記"
            )
        return key_text
    return _insert_signature(conn, key, table, key_text, digest, writer=writer)


def record_write(
    conn: sqlite3.Connection,
    key: bytes,
    table: str,
    primary_key: Sequence[object],
    *,
    writer: str,
) -> str:
    """為剛寫入的一列蓋簽章,回傳它的 row key。"""
    key_text, digest = _row_fingerprint(conn, table, primary_key)
    return _insert_signature(conn, key, table, key_text, digest, writer=writer)


def _insert_signature(
    conn: sqlite3.Connection,
    key: bytes,
    table: str,
    key_text: str,
    digest: str,
    *,
    writer: str,
) -> str:
    with conn:
        conn.execute(
            "INSERT INTO gateway_write (table_name, row_key, content_digest, signature,"
            " writer, written_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                table,
                key_text,
                digest,
                sign(key, digest),
                writer,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
    return key_text


def verify(conn: sqlite3.Connection, key: bytes) -> list[Finding]:
    """逐列核對受治理的表,回傳全部不合格之處(空 list = 全庫清白)。"""
    signed = {
        (row["table_name"], row["row_key"]): row
        for row in conn.execute(
            "SELECT table_name, row_key, content_digest, signature, writer, written_at "
            "FROM gateway_write"
        ).fetchall()
    }
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()

    for table, pk_columns in GOVERNED_TABLES.items():
        for row in conn.execute(f'SELECT * FROM "{table}"').fetchall():
            key_text = row_key_of(pk_columns, row)
            seen.add((table, key_text))
            entry = signed.get((table, key_text))
            digest = content_digest(table, row)
            if entry is None:
                findings.append(
                    Finding(
                        table,
                        key_text,
                        UNSIGNED,
                        "這一列沒有寫入者簽章,即是有人繞過唯一入口直接寫庫",
                    )
                )
            elif entry["content_digest"] != digest:
                findings.append(
                    Finding(
                        table,
                        key_text,
                        TAMPERED,
                        f"內容雜湊與登記時不符(登記於 {entry['written_at']},"
                        f"寫入者 {entry['writer']})",
                    )
                )
            elif not hmac.compare_digest(entry["signature"], sign(key, digest)):
                findings.append(
                    Finding(
                        table,
                        key_text,
                        FORGED,
                        "簽章核不過:不是本庫的鑰匙簽的,或簽章被改過",
                    )
                )

    for (table, key_text), entry in signed.items():
        if (table, key_text) not in seen:
            findings.append(
                Finding(
                    table,
                    key_text,
                    ORPHANED,
                    f"簽章登記在案(寫入者 {entry['writer']}),但庫內已無這一列",
                )
            )
    return findings
