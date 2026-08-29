"""KARST-077(D-034)驗證:用本機真實定義庫,逐條正式運行判一次「失敗運行」。

不寫庫、不改任何運行紀錄——只讀,把結果落成 ``summary.json`` 供票核對。
判準本身住 ``karst.web.data.is_failed_run``,這裡不另抄一套:一次運行的年化回報
(全期,``window_stats`` 口徑)若同時低於 SPY 與 QQQ 買入持有的年化回報(同一快照、
同一段期間),即為失敗運行;任一基準缺值就不判(照列)。

跑法(倉根目錄):
    set PYTHONUTF8=1
    python experiments/2026-08-29-failed-runs/audit_failed_runs.py
"""

from __future__ import annotations

import json
from pathlib import Path

from karst.metrics import benchmark_curve
from karst.runs import BASE, window_stats
from karst.store import FORMAL_RUN
from karst.web.data import FAILURE_JUDGE_BENCHMARKS, build_reader, is_failed_run

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    reader = build_reader(ROOT)
    strategies = []
    for name in reader.store.list_strategy_names():
        all_formal = reader.store.list_runs(name, origin=FORMAL_RUN)
        usable = [r for r in all_formal if not reader.series_missing(r)]
        series_missing = len(all_formal) - len(usable)

        runs = []
        for record in usable:
            equity = reader.runs.equity_curve(record.run_id)
            stats = window_stats(equity, None, None, base=BASE)
            bench: dict[str, float | None] = {}
            for ticker in FAILURE_JUDGE_BENCHMARKS:
                try:
                    curve = benchmark_curve(
                        reader.store,
                        record.snapshot_id,
                        ticker,
                        stats.start,
                        stats.end,
                        root=reader.snapshot_root,
                    )
                    bench[ticker] = curve.stats.annual_return
                except Exception:
                    bench[ticker] = None
            judged = is_failed_run(stats.annual_return, bench)
            runs.append(
                {
                    "runId": record.run_id,
                    "period": [stats.start, stats.end],
                    "annualReturn": stats.annual_return,
                    "benchmarks": bench,
                    "isFailed": judged,
                }
            )

        strategies.append(
            {
                "strategy": name,
                "usableRuns": len(usable),
                "seriesMissingRuns": series_missing,
                "failedRuns": sum(1 for r in runs if r["isFailed"] is True),
                "runs": runs,
            }
        )

    out = {"strategies": strategies}
    out_path = Path(__file__).resolve().parent / "summary.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"寫入 {out_path}")
    for row in strategies:
        print(
            f"{row['strategy']}: 可判 {row['usableRuns']} 次"
            f"(序列缺失另 {row['seriesMissingRuns']} 次,不判),"
            f"失敗 {row['failedRuns']} 次"
        )


if __name__ == "__main__":
    main()
