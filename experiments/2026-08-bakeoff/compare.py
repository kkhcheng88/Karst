"""把兩邊在同一批參數上的結果併起來,看兩個引擎是否真的在跑同一條策略。

若兩邊差距細,代表「快」的那一邊不是靠偷工減料快;差距大就要在報告裡如實講。
"""

from __future__ import annotations

import json
import os

import pandas as pd

import karst_spec as spec

R = spec.RESULT_DIR


def main() -> None:
    vbt = pd.read_csv(os.path.join(R, "vbt_sweep_returns.csv"))
    pb = pd.read_csv(os.path.join(R, "pb_sweep_returns.csv"))
    keys = ["top_n", "interval", "smooth"]
    m = pb.merge(vbt, on=keys, suffixes=("_pb", "_vbt"))
    m["diff_pct"] = (m["total_return_pb"] - m["total_return_vbt"]) / (1 + m["total_return_vbt"]) * 100
    m = m[keys + ["total_return_vbt", "total_return_pb", "diff_pct", "sec"]]
    m.to_csv(os.path.join(R, "agreement.csv"), index=False)

    summary = {
        "n_compared": int(len(m)),
        "abs_diff_pct_median": float(m["diff_pct"].abs().median()),
        "abs_diff_pct_max": float(m["diff_pct"].abs().max()),
        "corr": float(m["total_return_vbt"].corr(m["total_return_pb"])),
    }
    print(m.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    with open(os.path.join(R, "agreement.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
