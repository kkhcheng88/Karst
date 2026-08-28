"""KARST-061:以現有的宏觀快照,逐條序列重新核對一次齊全度。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-29-macro-completeness/audit_macro_snapshots.py ^
        --max-stale-days 3 --max-missing-ratio 0.01

答兩條問題:

1. **新做的這道關,會不會抓到 ^VIX3M 那件事?** 換來源之前那份宏觀快照
   (``2026-08-28-810facb50382``)的 VIX_3M 尾段停了 28 個交易日,當日一個錯都
   沒有報。把它拿來重新核一次:抓得到,這道關才算真的做得到事;抓不到,它就只是
   一段沒有用的程式。
2. **會不會誤報?** 現役那份(``2026-08-28-dc2d9f1a1778``)十四條全部供到主日曆
   尾日。齊全的序列在任何一套門檻下都不應該出現在警報名單裡——報一堆狼來了,
   下一個人就會學會不看警告,那樣這件事等於沒有做。

**本檔不寫庫、不凍快照、不抓數、不跑回測**:只由磁碟上已凍結的讀數重算、只落檔。
重算而不是讀回 manifest 那一份,是刻意的:manifest 那份是凍結當日寫下的結論,
重算這一份用的是讀數本身——要核對的是數據,不是別人寫下的結論。

**門檻是命令列參數,沒有預設值。** 「幾多日算停更」不是數據的性質,是對這條訊號
的容忍度;程式代揀一個數,就等於把一個沒有人裁決過的判斷寫進了每一次核對。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:  # 未裝套件也跑得動(倉根就在上兩層)
    sys.path.insert(0, str(REPO))

import pandas as pd  # noqa: E402

from karst import DefinitionStore  # noqa: E402
from karst.data import (  # noqa: E402
    CompletenessThresholds,
    audit_macro_completeness,
    read_macro_calendar,
    read_macro_completeness,
)
from experiments.snapshot_ids import MACRO, PREVIOUS  # noqa: E402

HERE = Path(__file__).resolve().parent
STORE_PATH = REPO / "karst.sqlite"
MACRO_ROOT = REPO / "data" / "macro_snapshots"

# 現役那份,加換來源之前那份。後者留在磁碟上是刻意的(KARST-058):換來源之前落的
# 成績引用的是它,刪掉就等於把那批成績的血統斬斷——而對本票來說,它正好是一份
# **已知有一條序列靜靜停更**的真數據,是這道關唯一一次驗得到「真的抓得到」的機會。
LEGACY_MACRO = next(
    (old for old, new in PREVIOUS.items() if new == MACRO), "2026-08-28-810facb50382"
)
SNAPSHOTS = (
    (MACRO, "現役(KARST-058 換來源之後)"),
    (LEGACY_MACRO, "換來源之前(已知 VIX_3M 停更)"),
)


def audit_one(
    store: DefinitionStore, snapshot_id: str, thresholds: CompletenessThresholds
) -> tuple[pd.DataFrame, tuple, tuple[str, ...]]:
    calendar = read_macro_calendar(store, snapshot_id, root=MACRO_ROOT)
    completeness = read_macro_completeness(store, snapshot_id, root=MACRO_ROOT)
    alerts = audit_macro_completeness(completeness, calendar, thresholds=thresholds)
    return completeness, alerts, calendar


def main() -> int:
    parser = argparse.ArgumentParser(description="宏觀快照齊全度重新核對(KARST-061)")
    parser.add_argument(
        "--max-stale-days", type=int, required=True,
        help="門檻:一條序列的尾段容許落後主日曆幾多個交易日(無預設值)",
    )
    parser.add_argument(
        "--max-missing-ratio", type=float, required=True,
        help="門檻:留空日數佔主日曆的比例上限,0.01 即 1%%(無預設值)",
    )
    parser.add_argument("--out", default=None, help="落檔目錄,預設本目錄")
    args = parser.parse_args()

    thresholds = CompletenessThresholds(
        max_stale_days=args.max_stale_days, max_missing_ratio=args.max_missing_ratio
    )
    out = Path(args.out) if args.out else HERE
    out.mkdir(parents=True, exist_ok=True)
    print(f"齊全度{thresholds.describe()}", flush=True)

    summary: dict[str, object] = {
        "ticket": "KARST-061",
        "thresholds": thresholds.as_dict(),
        "snapshots": [],
    }

    with DefinitionStore.open(str(STORE_PATH)) as store:
        for snapshot_id, label in SNAPSHOTS:
            completeness, alerts, calendar = audit_one(store, snapshot_id, thresholds)
            path = out / f"齊全度-{snapshot_id}.csv"
            completeness.to_csv(path, index=False, encoding="utf-8-sig")

            print(
                f"\n{snapshot_id}  {label}\n"
                f"  主日曆 {calendar[0]} ~ {calendar[-1]}({len(calendar)} 個交易日)、"
                f"{len(completeness)} 條序列",
                flush=True,
            )
            if alerts:
                print(f"  警報:{len(alerts)} 條序列超出門檻", flush=True)
                for alert in alerts:
                    print(f"    {alert.message}", flush=True)
            else:
                print("  警報:一條都沒有(全部合格)", flush=True)

            summary["snapshots"].append(
                {
                    "snapshot_id": snapshot_id,
                    "label": label,
                    "calendar_start": calendar[0],
                    "calendar_end": calendar[-1],
                    "trading_days": len(calendar),
                    "series_count": int(len(completeness)),
                    "alert_count": len(alerts),
                    "alerts": [alert.as_dict() for alert in alerts],
                    "worst_stale_days": int(completeness["stale_days"].max()),
                    "worst_missing_ratio": float(completeness["missing_ratio"].max()),
                    "completeness_csv": path.name,
                }
            )

    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n落檔:{out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
