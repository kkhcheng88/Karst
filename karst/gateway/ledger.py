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

from ..errors import ContractViolation, ImmutabilityViolation

# 鑰匙:環境變數優先,其次庫檔旁的鑰匙檔
GATEWAY_KEY_ENV = "KARST_GATEWAY_KEY"
KEY_SUFFIX = ".gateway-key"

IN_MEMORY = ":memory:"

# 受治理的表 → 主鍵欄位。定義類的表全部在此;因子值(factor_value)不在——
# 它已由 trigger 鎖死不可改不可刪,且掛在已簽章的因子版本之下,逐值簽章代價
# 與它的行數不相稱(KARST-022 範圍註明)。大批因子值連表都不入了(D-032:改存
# Parquet),它們的**登記**在下面兩張表,逐列有簽章。
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
    # KARST-068 補上的兩張:因子值批次的登記。值本身住 Parquet(D-032),庫內
    # 就只剩這兩列——落點、內容雜湊、行數、載住哪幾個因子版本。**那一列雜湊就是
    # 整批值的唯一憑證**:它若果可以被人手改一個字,檔案核對就核了個寂寞
    # (改檔的人順手改埋雜湊,重算出來一樣對得上)。所以它與定義同一道門、
    # 同一種簽章。檔案本身的核對另有一段(見 ``Gateway.verify``)。
    "factor_value_batch": ("batch_key", "snapshot_id"),
    "factor_value_batch_member": ("batch_key", "snapshot_id", "factor_version_id"),
    # KARST-084 補上的一張:快照除名登記。「這個快照不再算可回測」是一個定義級動作
    # ——它決定了日後所有回測拿得到哪幾個快照——所以與策略定義同一道門、同一種簽章。
    # 沒有簽章的除名列即是有人繞過唯一入口靜靜除掉一個快照,verify 一掃就見到。
    "data_snapshot_retraction": ("snapshot_id",),
    # KARST-087 補上的兩張:數據快照登記本身,連它的抓取登記。
    #
    # 以前清單裡只有「除名」而沒有「登記」,於是治理只管得住「哪個快照不算數」,管不住
    # 「哪個快照算數」——價格線、宏觀線、重凍腳本三處各自拎住定義庫直接寫一列快照登記,
    # 一列簽章都沒有,而 verify 照樣報全庫清白。清白報告不覆蓋的地方,正正是每一次回測
    # 取數的源頭:一個快照的來源、日期、內容雜湊、落點、當時的宇宙名單,全部住在這一列。
    # 有人改一個字(例如把落點指去另一份 parquet),整條追溯鏈就斷了而無人知。
    #
    # 抓取登記一併入清單:它答的是「幾時抓、抓哪段窗口、幾多實體幾多列、當日齊全度核對
    # 出什麼」。快照編號刻意不含抓取時間,所以那幾格只此一份,改了就沒有第二處對得回。
    "data_snapshot": ("snapshot_id",),
    "data_snapshot_fetch": ("snapshot_id",),
    # KARST-093 補上的一張:運行除名登記。「這一次運行不算數」與「指定現役設定」
    # 同級——兩者都是決定門面八個數字、歷次運行表、運行選單取哪幾次運行的定義級
    # 動作,所以同一道門、同一種簽章。沒有簽章的除名列即是有人繞過唯一入口靜靜
    # 抹走一次運行的成績,verify 一掃就見到。
    "backtest_run_retraction": ("run_id",),
    # KARST-091 補上的一張:批次登記。一次參數掃描收工寫的那一列,載住門面左半那四個
    # 數(達標幾條/共幾條、中位年化、中位 Sortino、中位最大回撤)與判讀口徑。D-042 用
    # 「達標運行的中位數年化最高」排批次名次,即那一列直接決定用戶見到哪一批成績——
    # 與指定現役設定同級的定義級動作。它以前只住在 experiments/ 的 CSV 裡,任何人改得到
    # 而無人知;收入清單之後,繞過那道門塞一批看似達標的成績,verify 一掃就見到。
    "sweep_batch": ("sweep_id",),
    # KARST-094 補上的一張:參數集對齊標記。D-038 講明示例取值未經與用戶對齊、不是現役
    # 設定,而「畫面與紀錄須能分辨」——這張表就是那個分辨。一個參數集由「示例」變成
    # 「已對齊」,即是說它可以拿去做現役設定、它那次運行的成績可以當真;那與指定現役設定
    # 同級,是決定門面數字代表什麼的定義級動作。沒有簽章的標記即是有人繞過那道門,把一組
    # 從未與用戶對齊的取值標成已對齊送上門面——正正是 D-038 要防的那件事。
    "param_set_alignment": ("param_set_id", "seq_no"),
    # KARST-116 補上的一張:策略治理宣告。D-058 第 1 條要求每條策略講得出自己屬由上而下
    # 三層的哪一層、離場治理屬哪一型,兩格必填。這兩句話決定這條策略在三層次序裡站哪一格
    # (即它應不應該先過板塊層才落個股),以及一注落了下去幾時走(價格止蝕、論點失效,
    # 還是逐期按規則重算)——與指定現役設定同級的定義級動作。沒有簽章的宣告即是有人繞過
    # 唯一入口靜靜替一條策略改層別或改離場分型,而那正是 D-057/D-058 要防的漂移。
    "strategy_governance": ("strategy_id", "seq_no"),
    # KARST-117 補上的一張:策略登記狀態。D-058 第 1 條把 D-057 的「封存以搬走或刪除
    # 落實」修正為狀態格——定義庫按設計不可刪任何登記,所以封存不用刪、用狀態。而狀態
    # 一旦決定「這條線還算不算現役」,它就與指定現役設定同級:一條線由現役變封存,即是
    # 說它不再出現在「現在有哪幾條線」的答案裡。沒有簽章的狀態即是有人繞過唯一入口靜靜
    # 封存一條線(或者把一條已封存的線靜靜復活),而那正是 D-057/D-058 要防的漂移。
    "strategy_status": ("strategy_id", "seq_no"),
}

# 核對報告的三類(KARST-087)。一份「全庫清白/揪到 N 處」的總帳讀不出**哪一邊**不清白,
# 而三邊的意思差很遠:定義髒了是策略講法被人改過,因子批次髒了是值檔與登記對不上,
# 快照髒了是取數的源頭被人動過。分三類列,才答得到「現在清白的是什麼」。
CATEGORY_DEFINITION = "定義"
CATEGORY_FACTOR_BATCH = "因子批次"
CATEGORY_SNAPSHOT = "快照"

CATEGORIES: tuple[str, ...] = (CATEGORY_DEFINITION, CATEGORY_FACTOR_BATCH, CATEGORY_SNAPSHOT)

TABLE_CATEGORIES: dict[str, str] = {
    "factor": CATEGORY_DEFINITION,
    "factor_version": CATEGORY_DEFINITION,
    "strategy": CATEGORY_DEFINITION,
    "strategy_version": CATEGORY_DEFINITION,
    "strategy_factor_ref": CATEGORY_DEFINITION,
    "param_set": CATEGORY_DEFINITION,
    "param_value": CATEGORY_DEFINITION,
    "active_setup": CATEGORY_DEFINITION,
    # 運行除名歸「定義」而不是自立一類:它與 active_setup 是同一種東西——不是數據
    # 來源出了事(那是「快照」),而是一句「門面數字該取哪幾次運行」的講法。
    "backtest_run_retraction": CATEGORY_DEFINITION,
    # 批次登記同樣歸「定義」:它不是數據來源出了事(那是「快照」),而是一句
    # 「門面數字取哪一批運行、按哪一套判讀口徑」的講法(KARST-091)。
    "sweep_batch": CATEGORY_DEFINITION,
    # 參數集對齊標記**併入「定義」,不自立第四類**(KARST-094)。理由:分類的用處是答
    # 「現在清白的是什麼」,而三類之別在於**髒了代表什麼事**——定義髒了是策略的講法被人
    # 改過,因子批次髒了是值檔與登記對不上,快照髒了是取數的源頭被人動過。對齊標記髒了
    # 屬第一種:它與 active_setup 是同一句話的兩半(一個講「跟隨哪一個參數集」,一個講
    # 「那個參數集算不算數」),兩者分開兩類反而讀不出它們是連在一起的。自立一類亦會令
    # 報告多一行長期「1 類、13 列、清白」的雜音,把真正要分辨的三邊沖淡。
    "param_set_alignment": CATEGORY_DEFINITION,
    # 策略治理宣告同樣歸「定義」:它不是數據來源出了事(那是「快照」),而是一句
    # 「這條策略是什麼、它的注怎樣走」的講法,與策略定義本身同一類(KARST-116)。
    "strategy_governance": CATEGORY_DEFINITION,
    # 策略登記狀態同樣歸「定義」:「這條線還算不算現役」與 active_setup 的
    # 「跟隨哪一個參數集」是同一族講法,不是數據來源出了事(KARST-117)。
    "strategy_status": CATEGORY_DEFINITION,
    "risk_rule": CATEGORY_DEFINITION,
    "strategy_risk_ref": CATEGORY_DEFINITION,
    "factor_value_batch": CATEGORY_FACTOR_BATCH,
    "factor_value_batch_member": CATEGORY_FACTOR_BATCH,
    "data_snapshot": CATEGORY_SNAPSHOT,
    "data_snapshot_fetch": CATEGORY_SNAPSHOT,
    "data_snapshot_retraction": CATEGORY_SNAPSHOT,
}


def category_of(table: str) -> str:
    """一張受治理的表屬於報告的哪一類。認不出的表當場拋錯,不歸去某一類了事——
    治理清單加了一張表而忘記講它屬哪一類,應該在加的那一刻就撞板,不是靜靜歸錯類。
    """
    try:
        return TABLE_CATEGORIES[table]
    except KeyError:  # pragma: no cover - 兩份清單同步時不會走到
        raise KeyError(
            f"{table} 在治理清單內但沒有講明屬核對報告哪一類;"
            f"請在 TABLE_CATEGORIES 補上(現有:{'、'.join(CATEGORIES)})"
        ) from None

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

    @property
    def category(self) -> str:
        """這一處不合格屬核對報告哪一類:定義、因子批次,還是快照(KARST-087)。"""
        return category_of(self.table)

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


def unsigned_rows(conn: sqlite3.Connection, tables: Sequence[str]) -> list[tuple[str, str]]:
    """這幾張表裡,哪幾列一個簽章都沒有。回傳 ``(表名, row key)``,按表名與 row key 排。

    「沒有簽章」與「簽章對不上」是兩回事,本函式只答前者:後者代表庫內那一列落庫之後
    被人改過,補簽解決不了,亦不應該由補簽把痕跡蓋走。
    """
    missing: list[tuple[str, str]] = []
    for table in tables:
        pk_columns = GOVERNED_TABLES[table]
        for row in conn.execute(f'SELECT * FROM "{table}"').fetchall():
            key_text = row_key_of(pk_columns, row)
            found = conn.execute(
                "SELECT 1 FROM gateway_write WHERE table_name = ? AND row_key = ?",
                (table, key_text),
            ).fetchone()
            if found is None:
                missing.append((table, key_text))
    return sorted(missing)


def countersign(
    conn: sqlite3.Connection,
    key: bytes,
    table: str,
    row_key: str,
    *,
    writer: str,
    reason: str,
) -> str:
    """替一列本來沒有簽章的舊列補簽,並在補簽冊留一行(誰、幾時、為什麼)。

    補簽只證明「由補簽那一刻起,這一列沒有再被改過」;它證明不了這一列當初是經唯一入口
    寫的——那件事已經過去了,今日蓋一個章擔保不了。所以簽章與留痕**同一次寫入落地**:
    日後查一個簽章的來歷,查得出它是原簽還是補簽、補的人給的理由是什麼。

    已經有簽章的列一律拒收:補簽是補「無」,不是覆蓋「有」。
    """
    note = str(reason).strip()
    if not note:
        raise ContractViolation("補簽必須講明為什麼;無理由的補簽等於把一列來歷不明的舊帳洗白")
    existing = conn.execute(
        "SELECT 1 FROM gateway_write WHERE table_name = ? AND row_key = ?",
        (table, row_key),
    ).fetchone()
    if existing is not None:
        raise ContractViolation(
            f"{table}[{row_key}] 已經有簽章,不必亦不可補簽;"
            "簽章對不上的列請按版本鏈重新經唯一入口登記,不要用補簽蓋過去"
        )
    pk_columns = GOVERNED_TABLES[table]
    where = " AND ".join(f'"{column}" = ?' for column in pk_columns)
    row = conn.execute(
        f'SELECT * FROM "{table}" WHERE {where}', tuple(row_key.split("|"))
    ).fetchone()
    if row is None:
        raise LookupError(f"{table} 查無 row key {row_key!r},簽不到章")
    digest = content_digest(table, row)
    moment = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        conn.execute(
            "INSERT INTO gateway_write (table_name, row_key, content_digest, signature,"
            " writer, written_at) VALUES (?, ?, ?, ?, ?, ?)",
            (table, row_key, digest, sign(key, digest), writer, moment),
        )
        conn.execute(
            "INSERT INTO gateway_countersign (table_name, row_key, reason,"
            " countersigned_by, countersigned_at) VALUES (?, ?, ?, ?, ?)",
            (table, row_key, note, writer, moment),
        )
    return row_key


def countersigned_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """補簽冊全份,新的在前。查一個簽章是原簽還是補簽就看這裡。"""
    return conn.execute(
        "SELECT table_name, row_key, reason, countersigned_by, countersigned_at"
        " FROM gateway_countersign ORDER BY countersigned_at DESC, table_name, row_key"
    ).fetchall()


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
