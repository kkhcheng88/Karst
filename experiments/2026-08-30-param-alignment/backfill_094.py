"""KARST-094 補記:現有正式運行所用的參數集,一律補記「示例」並留痕(D-038)。

為什麼要補:D-038 講明現有那批「示例-…」取值只是通鏈用的示例值,未經與用戶對齊,
不視為現役設定;而在 KARST-094 之前,這句話只住在登記那一刻的記憶體裡,庫內查不到。
補記之後,庫身自己講得出哪個參數集是示例——看報告的人分得出。

**只補正式運行所用的那幾個參數集。** 掃描格的參數集有 8000 幾個,它們本來就是掃描
展開出來的取值,不是拿去做現役設定的候選;補它們只會令這張表被雜訊淹沒,而真正
要分辨的那十幾個反而被埋。

依據句一律寫「D-038:未經用戶對齊」——這不是逐個參數集判出來的結論,而是 D-038
已經替全部未對齊的取值講了的那一句,所以逐列寫同一句是誠實的,不是偷懶。

**一切經唯一入口,逐列蓋簽章。** 不直接寫庫:繞過那道門塞一列標記,正正是
``karst verify`` 要揪的那件事。

跑法:``PYTHONUTF8=1 python experiments/2026-08-30-param-alignment/backfill_094.py``
加 ``--dry-run`` 只看不寫。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(r"C:\projects\Karst")
sys.path.insert(0, str(REPO))

from karst.gateway import Gateway  # noqa: E402
from karst.store import SAMPLE  # noqa: E402

SCRATCH = Path(__file__).resolve().parent
STORE = REPO / "karst.sqlite"
BASIS = "D-038:未經用戶對齊"
WRITER = "KARST-094-backfill"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只列出要補記什麼,一個字都不寫")
    args = parser.parse_args()

    report: dict = {"basis": BASIS, "writer": WRITER, "param_sets": [], "dry_run": args.dry_run}

    with Gateway.open(str(STORE), writer=WRITER) as gateway:
        rows = gateway.store.connection.execute(
            "SELECT DISTINCT r.param_set_id, p.name, p.version_no, s.name AS strategy"
            " FROM backtest_run AS r"
            " JOIN param_set AS p ON p.param_set_id = r.param_set_id"
            " JOIN strategy_version AS sv"
            "   ON sv.strategy_version_id = p.strategy_version_id"
            " JOIN strategy AS s ON s.strategy_id = sv.strategy_id"
            " WHERE r.origin = 'formal'"
            " ORDER BY r.param_set_id"
        ).fetchall()
        print(f"正式運行所用的參數集:{len(rows)} 個")

        for row in rows:
            param_set_id = int(row["param_set_id"])
            existing = gateway.store.param_set_alignment(param_set_id)
            entry = {
                "param_set_id": param_set_id,
                "strategy": row["strategy"],
                "param_set": f"{row['name']}@{row['version_no']}",
                "already_declared": existing is not None,
            }
            if existing is not None:
                entry["mark"] = existing.mark
                entry["seq_no"] = existing.seq_no
                print(f"  {param_set_id:>5} 已有標記({existing.label}),略過")
            elif args.dry_run:
                print(f"  {param_set_id:>5} 會補記「示例」 {row['strategy']} / {row['name']}")
            else:
                alignment, receipt = gateway.mark_param_set_alignment(
                    param_set_id, mark=SAMPLE, basis=BASIS
                )
                entry["mark"] = alignment.mark
                entry["seq_no"] = alignment.seq_no
                entry["recorded_at"] = alignment.recorded_at
                entry["signed"] = list(receipt.signed_rows)
                print(
                    f"  {param_set_id:>5} 已補記「{alignment.label}」 "
                    f"{row['strategy']} / {row['name']}"
                )
            report["param_sets"].append(entry)

        if not args.dry_run:
            verdicts = gateway.verify_report()
            report["verify"] = [verdict.describe() for verdict in verdicts]
            print("\n核對報告:")
            for verdict in verdicts:
                print(f"  {verdict.describe()}")
                for finding in verdict.findings:
                    print(f"    - {finding}")

    out = SCRATCH / "backfill_094.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n落檔:{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
