"""KARST-094 驗收:正式運行逐位不變、既有簽章一個不動(對住倉裡那個真庫核)。

`tests/test_param_alignment.py` 那條 `test_marks_touch_neither_the_param_set_nor_its_signature`
只證得到「在一個乾淨的小庫裡,寫標記碰不到參數集那幾列」。真庫那 13 列正式運行、
51832 列既有簽章有沒有動,小庫證不到——那要對住 `karst.sqlite` 本身核,就是這一支。

**兩項證據,兩項都逐格對,不靠雜湊。**

1. 正式運行:`backtest_run` 全部 13 個欄位,逐條逐格與動庫之前那份 `baseline_runs.json`
   比。`baseline_runs.json` 裡那個 `sha256` 欄的計法上一手沒有寫低,接手時試過 50 幾種
   序列化組合都砌不回同一個值——所以這裡**不再引那個雜湊當證據**,改為逐格比。
   逐格比本來就比雜湊強:雜湊只答「一不一樣」,逐格比答得出「哪一條哪一格不一樣」。

2. 既有簽章:動庫之前的備份庫 `karst.sqlite.2026-08-30-094.bak` 與現庫的
   `gateway_write` 全表逐列比。要證的是**一列都沒有消失、沒有改過**,而新增的那些
   全部屬 `param_set_alignment`。

跑法:``PYTHONUTF8=1 python experiments/2026-08-30-param-alignment/verify_094.py``
全程唯讀:兩個庫都以 `mode=ro` 開,一個字都不寫回去。
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(r"C:\projects\Karst")
EXP = REPO / "experiments" / "2026-08-30-param-alignment"
LIVE = REPO / "karst.sqlite"
BACKUP = Path(r"C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-094.bak")

# `backtest_run` 現時的全部欄位。寫死在這裡是有意的:日後有人加一欄而忘記更新這支,
# 下面那句 assert 會當場叫停,而不是靜靜地少比一格。
RUN_FIELDS = [
    "created_at", "engine_name", "engine_version", "fingerprint", "origin",
    "param_set_id", "period_end", "period_start", "run_id", "snapshot_id",
    "strategy_version_id", "sweep_id", "trading_days",
]


def _open(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _formal_runs(conn: sqlite3.Connection) -> dict[str, dict]:
    columns = [row[1] for row in conn.execute("PRAGMA table_info(backtest_run)")]
    assert sorted(columns) == sorted(RUN_FIELDS), (
        f"backtest_run 的欄位變了({columns});逐格比要連新欄一齊比,請更新 RUN_FIELDS"
    )
    rows = conn.execute(
        "SELECT " + ", ".join(RUN_FIELDS) + " FROM backtest_run WHERE origin = 'formal'"
    ).fetchall()
    return {str(row["run_id"]): {name: row[name] for name in RUN_FIELDS} for row in rows}


def _signatures(conn: sqlite3.Connection) -> tuple[list[str], set[tuple[str, ...]]]:
    columns = [row[1] for row in conn.execute("PRAGMA table_info(gateway_write)")]
    rows = {
        tuple("" if row[name] is None else str(row[name]) for name in columns)
        for row in conn.execute("SELECT * FROM gateway_write")
    }
    return columns, rows


def main() -> int:
    report: dict = {}
    problems: list[str] = []

    live = _open(LIVE)
    backup = _open(BACKUP)

    # ---- 一、正式運行逐格比 --------------------------------------------
    baseline = json.loads((EXP / "baseline_runs.json").read_text(encoding="utf-8"))
    before = baseline["runs"]
    after = _formal_runs(live)

    report["formal_run_rows_before"] = len(before)
    report["formal_run_rows_after"] = len(after)

    differences: list[dict] = []
    if sorted(before) != sorted(after):
        problems.append(
            f"正式運行的編號清單變了:動庫前 {sorted(before)},動庫後 {sorted(after)}"
        )
    for run_id in sorted(set(before) & set(after)):
        for name in RUN_FIELDS:
            if before[run_id][name] != after[run_id][name]:
                differences.append({
                    "run_id": run_id, "field": name,
                    "before": before[run_id][name], "after": after[run_id][name],
                })
    report["field_differences"] = differences
    if differences:
        problems.append(f"正式運行有 {len(differences)} 格對不上")

    # 除名那一條(KARST-093):它的列照舊留在庫內,所以逐格比是 13 列;
    # 而「算數的正式運行」是 12 條。兩個數要分開講,否則下一個人會以為有人數錯。
    retracted = [str(row["run_id"]) for row in
                 live.execute("SELECT run_id FROM backtest_run_retraction")]
    report["retracted_runs"] = retracted
    report["counted_formal_runs"] = len(after) - len(retracted)

    # ---- 二、既有簽章一列不動 ------------------------------------------
    columns_before, sigs_before = _signatures(backup)
    columns_after, sigs_after = _signatures(live)
    if columns_before != columns_after:
        problems.append(f"gateway_write 的欄位變了:{columns_before} → {columns_after}")

    removed = sigs_before - sigs_after
    added = sigs_after - sigs_before
    table_index = columns_after.index("table_name")

    report["signatures_before"] = len(sigs_before)
    report["signatures_after"] = len(sigs_after)
    report["signatures_removed"] = len(removed)
    report["signatures_added"] = len(added)
    report["added_tables"] = sorted({row[table_index] for row in added})

    if removed:
        problems.append(
            f"有 {len(removed)} 列既有簽章消失或者被改過:{sorted(removed)[:3]}"
        )
    if report["added_tables"] not in ([], ["param_set_alignment"]):
        problems.append(f"新增的簽章不只對齊標記那張表:{report['added_tables']}")

    # ---- 三、庫身版本 ----------------------------------------------------
    def _version(conn: sqlite3.Connection) -> str:
        return str(conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'").fetchone()[0])

    report["schema_version_before"] = _version(backup)
    report["schema_version_after"] = _version(live)
    report["alignment_rows"] = live.execute(
        "SELECT COUNT(*) FROM param_set_alignment").fetchone()[0]

    live.close()
    backup.close()

    report["problems"] = problems
    report["verdict"] = "全部逐格相同" if not problems else f"揪到 {len(problems)} 處"

    print(f"正式運行:動庫前 {report['formal_run_rows_before']} 列、"
          f"動庫後 {report['formal_run_rows_after']} 列;"
          f"其中已除名 {len(retracted)} 條,算數的是 {report['counted_formal_runs']} 條")
    print(f"  逐格對不上的:{len(differences)} 格")
    print(f"既有簽章:{report['signatures_before']} 列 → {report['signatures_after']} 列;"
          f"消失或被改 {report['signatures_removed']} 列、"
          f"新增 {report['signatures_added']} 列({report['added_tables']})")
    print(f"庫身版本:第 {report['schema_version_before']} 版 → 第 {report['schema_version_after']} 版;"
          f"對齊標記 {report['alignment_rows']} 列")
    for problem in problems:
        print(f"  - {problem}")
    print(f"結論:{report['verdict']}")

    out = EXP / "verify_094.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str),
                   encoding="utf-8")
    print(f"落檔:{out}")
    return 0 if not problems else 3


if __name__ == "__main__":
    raise SystemExit(main())
