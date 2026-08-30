"""KARST-117 驗收:因子混合標封存之後,不可刪的登記一列未動、參數集與運行照查得到。

`tests/test_strategy_status.py` 只證得到「在一個乾淨的小庫裡,封存留得低痕、清單過濾得到」。
真庫那 8,318 次運行、7,096 個參數集、50,829 列既有簽章有沒有被這次封存動過,小庫證不到
——那要對住 `karst.sqlite` 本身核,就是這一支(做法照 KARST-116 的 `verify_116.py`)。

**四項證據,全部逐格對,不靠雜湊。**

1. **運行逐位不變**:`backtest_run` 全部欄位,逐條逐格與動庫之前那份備份比。
   狀態走旁表、不進參數集內容,所以運行編號按理一位都不應該變——這一項是那句話的證明。
2. **既有簽章一個不動**:備份庫與現庫的 `gateway_write` 全表逐列比。要證的是一列都沒有
   消失、沒有改過,而新增的那一列屬 `strategy_status`。
3. **封存那條線的家當照留**:因子混合的策略登記、版本、參數集(連逐格取值)與歷次運行,
   逐條逐格與備份比,一格都不應該變——「封存不是刪除」這句話的證明。
4. **狀態讀得回、清單過濾對**:封存那一筆的依據指得出 D-055;預設清單不列它、加旗標列到它。

跑法:``PYTHONUTF8=1 python experiments/2026-08-31-strategy-status/verify_117.py``
全程唯讀:兩個庫都以 ``mode=ro`` 開,一個字都不寫回去。
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(r"C:\projects\Karst")
EXP = REPO / "experiments" / "2026-08-31-strategy-status"
LIVE = REPO / "karst.sqlite"
BACKUP = Path(r"C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-31.bak")

ARCHIVED = "因子混合(ETF 版)"
ACTIVE = ("趨勢波段", "因子輪動(ETF 版)")


def rows(path: Path, sql: str, args: tuple = ()) -> list[dict]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(sql, args)]
    finally:
        conn.close()


def diff(before: dict, after: dict, label: str) -> list[str]:
    """兩份「鍵→整列」逐格比,回一份人讀得明的出入清單。"""
    out = [
        f"{label} {key}.{col}:{before[key][col]!r}→{after[key][col]!r}"
        for key in sorted(set(before) & set(after), key=str)
        for col in before[key]
        if before[key][col] != after[key][col]
    ]
    out += [f"{label} 不見了 {key}" for key in sorted(set(before) - set(after), key=str)]
    out += [f"{label} 多了 {key}" for key in sorted(set(after) - set(before), key=str)]
    return out


def main() -> int:
    if not BACKUP.exists():
        print(f"找不到動庫之前的備份 {BACKUP};無得比,不出結論")
        return 1

    report: dict = {}
    failures: list[str] = []

    # 1. 運行逐位不變 -----------------------------------------------------
    sql_runs = "SELECT * FROM backtest_run ORDER BY run_id"
    before = {row["run_id"]: row for row in rows(BACKUP, sql_runs)}
    after = {row["run_id"]: row for row in rows(LIVE, sql_runs)}
    run_diff = diff(before, after, "運行")
    report["runs"] = {
        "before": len(before), "after": len(after), "差": run_diff[:10],
    }
    if run_diff:
        failures.append("運行有出入")

    # 2. 既有簽章一個不動 --------------------------------------------------
    sql_signed = "SELECT table_name, row_key, writer, content_digest FROM gateway_write"
    sign_before = {(r["table_name"], r["row_key"]): r for r in rows(BACKUP, sql_signed)}
    sign_after = {(r["table_name"], r["row_key"]): r for r in rows(LIVE, sql_signed)}
    dropped = sorted(f"{t}[{k}]" for t, k in set(sign_before) - set(sign_after))
    altered = sorted(
        f"{t}[{k}]" for t, k in set(sign_before) & set(sign_after)
        if sign_before[(t, k)]["content_digest"] != sign_after[(t, k)]["content_digest"]
    )
    fresh = sorted(set(sign_after) - set(sign_before))
    report["signatures"] = {
        "before": len(sign_before), "after": len(sign_after),
        "dropped": dropped[:10], "altered": altered[:10],
        "added": [f"{t}[{k}]" for t, k in fresh],
    }
    if dropped or altered:
        failures.append("既有簽章有出入")
    if [t for t, _ in fresh] != ["strategy_status"]:
        failures.append(f"新增簽章不是剛好一列 strategy_status:{fresh}")

    # 3. 封存那條線的家當照留 ----------------------------------------------
    #    策略登記、版本、參數集連逐格取值、歷次運行,全部逐格對備份。
    sql_strategy = "SELECT * FROM strategy WHERE name = ?"
    sql_versions = (
        "SELECT v.* FROM strategy_version v JOIN strategy s USING (strategy_id)"
        " WHERE s.name = ? ORDER BY v.strategy_version_id"
    )
    sql_param_sets = (
        "SELECT p.* FROM param_set p JOIN strategy_version v USING (strategy_version_id)"
        " JOIN strategy s USING (strategy_id) WHERE s.name = ? ORDER BY p.param_set_id"
    )
    sql_param_values = (
        "SELECT pv.* FROM param_value pv JOIN param_set p USING (param_set_id)"
        " JOIN strategy_version v USING (strategy_version_id)"
        " JOIN strategy s USING (strategy_id) WHERE s.name = ?"
        " ORDER BY pv.param_set_id, pv.param_key"
    )
    sql_own_runs = (
        "SELECT r.* FROM backtest_run r JOIN strategy_version v USING (strategy_version_id)"
        " JOIN strategy s USING (strategy_id) WHERE s.name = ? ORDER BY r.run_id"
    )

    kept: dict = {}
    for label, sql, key in (
        ("策略登記", sql_strategy, lambda r: r["strategy_id"]),
        ("策略版本", sql_versions, lambda r: r["strategy_version_id"]),
        ("參數集", sql_param_sets, lambda r: r["param_set_id"]),
        ("參數取值", sql_param_values, lambda r: (r["param_set_id"], r["param_key"])),
        ("該線運行", sql_own_runs, lambda r: r["run_id"]),
    ):
        b = {key(r): r for r in rows(BACKUP, sql, (ARCHIVED,))}
        a = {key(r): r for r in rows(LIVE, sql, (ARCHIVED,))}
        d = diff(b, a, label)
        kept[label] = {"before": len(b), "after": len(a), "差": d[:10]}
        if d:
            failures.append(f"{label}有出入")
        if not a:
            failures.append(f"{label}查唔到嘢——封存不應該令它查不到")
    report["封存那條線的家當"] = kept

    # 4. 狀態讀得回、清單過濾對 --------------------------------------------
    status = rows(
        LIVE,
        "SELECT s.name, t.seq_no, t.status, t.basis, t.recorded_at"
        " FROM strategy_status t JOIN strategy s USING (strategy_id)"
        " ORDER BY s.name, t.seq_no",
    )
    report["狀態紀錄"] = status
    if [r["name"] for r in status] != [ARCHIVED]:
        failures.append(f"標了狀態的不是只得因子混合一條:{[r['name'] for r in status]}")
    elif status[0]["status"] != "archived":
        failures.append("因子混合不是 archived")
    elif "D-055" not in str(status[0]["basis"]):
        failures.append("封存依據沒有指明 D-055")

    sys.path.insert(0, str(REPO))
    from karst.store import DefinitionStore  # noqa: E402  (要先有 REPO 在 path 上)

    with DefinitionStore.open(str(LIVE)) as store:
        default_list = store.list_strategy_names()
        full_list = store.list_strategy_names(include_archived=True)
    report["清單"] = {"預設": default_list, "加旗標": full_list}
    if default_list != list(ACTIVE):
        failures.append(f"預設清單不是只得兩條現役:{default_list}")
    if ARCHIVED not in full_list:
        failures.append("加旗標仍然列不到封存那條")

    report["verdict"] = "全部對得上" if not failures else failures
    out = EXP / "verify_117.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n落檔:{out}")
    return 0 if not failures else 3


if __name__ == "__main__":
    sys.exit(main())
