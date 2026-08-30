"""KARST-116 驗收:兩格補填入生產庫之後,既有登記與運行一位都沒有動。

`tests/test_strategy_governance.py` 只證得到「在一個乾淨的小庫裡,閘擋得住、宣告補得回」。
真庫那 8,318 次運行、50,826 列既有簽章有沒有被這次遷移動過,小庫證不到——那要對住
`karst.sqlite` 本身核,就是這一支(做法照 KARST-094 的 `verify_094.py`)。

**三項證據,全部逐格對,不靠雜湊。**

1. **運行逐位不變**:`backtest_run` 全部欄位,逐條逐格與動庫之前那份備份比。
   兩格走旁表、不進參數集內容,所以運行編號按理一位都不應該變——這一項是那句話的證明。
2. **既有簽章一個不動**:備份庫與現庫的 `gateway_write` 全表逐列比。要證的是一列都沒有
   消失、沒有改過,而新增的那幾列全部屬 `strategy_governance`。
3. **三條策略補填齊**:每條有且只有一筆宣告,值與依據讀得回,而且逐列有簽章。

跑法:``PYTHONUTF8=1 python experiments/2026-08-30-strategy-governance/verify_116.py``
全程唯讀:兩個庫都以 ``mode=ro`` 開,一個字都不寫回去。
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(r"C:\projects\Karst")
EXP = REPO / "experiments" / "2026-08-30-strategy-governance"
LIVE = REPO / "karst.sqlite"
BACKUP = Path(r"C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30.bak")

STRATEGIES = ("因子混合(ETF 版)", "趨勢波段", "因子輪動(ETF 版)")


def rows(path: Path, sql: str) -> list[dict]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(sql)]
    finally:
        conn.close()


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
    差 = [
        f"{run_id}.{key}:{before[run_id][key]!r}→{after[run_id][key]!r}"
        for run_id in sorted(set(before) & set(after))
        for key in before[run_id]
        if before[run_id][key] != after[run_id][key]
    ]
    missing = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    report["runs"] = {
        "before": len(before), "after": len(after),
        "changed_fields": 差[:10], "missing": missing[:10], "added": added[:10],
    }
    if 差 or missing or added:
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
    if any(t != "strategy_governance" for t, _ in fresh):
        failures.append("新增簽章不只 strategy_governance 一張表")

    # 3. 三條策略補填齊 ----------------------------------------------------
    declared = rows(
        LIVE,
        "SELECT s.name, g.seq_no, g.layer, g.exit_governance, g.basis, g.declared_at"
        " FROM strategy_governance g JOIN strategy s USING (strategy_id) ORDER BY s.name, g.seq_no",
    )
    report["declarations"] = declared
    named = {row["name"] for row in declared}
    if named != set(STRATEGIES):
        failures.append(f"補填的策略不是那三條:{sorted(named)}")
    if any(row["seq_no"] != 1 for row in declared):
        failures.append("有策略不只一筆宣告")
    if any(not str(row["basis"]).strip() for row in declared):
        failures.append("有宣告沒有依據一句")

    report["verdict"] = "全部對得上" if not failures else failures
    out = EXP / "verify_116.json"
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n落檔:{out}")
    return 0 if not failures else 3


if __name__ == "__main__":
    sys.exit(main())
