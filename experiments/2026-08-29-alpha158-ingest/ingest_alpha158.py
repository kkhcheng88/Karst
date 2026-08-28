"""KARST-064:把 Alpha158 全部 158 條在起步宇宙十二隻上入庫一次(真數據)。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-29-alpha158-ingest/ingest_alpha158.py ^
        --store karst.sqlite --snapshot 2026-08-28-a508d635a5fa

本檔**不另寫一套入庫邏輯**:它只是叫唯一入口那道子命令
(``karst factor ingest-alpha158``)行一次,再把成果單落檔。要重跑,直接打那句
命令一樣得——這裡多一個檔,只為留住「這一次跑的是哪個快照、跑出什麼數」。

落檔的是 ``summary.json``:入庫行數、因子數、缺值比例、用時,連逐條因子的行數。
沒有預設值:``--store`` 與 ``--snapshot`` 兩個都要給——用哪個庫、算哪一批數據,
是跑的人才答得出的事。

**一個因子值都不會覆寫**:``factor_value`` 落庫後不可改不可刪(D-021 第 9 條),
同一個快照重跑第二次會被主鍵擋住而拒收,不會靜靜寫多一份。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:  # 未裝套件也跑得動(倉根就在上兩層)
    sys.path.insert(0, str(REPO))

from karst.factors import ALPHA158_NAMES  # noqa: E402
from karst.gateway.alpha158 import (  # noqa: E402
    ALPHA158_FORMULA_SOURCE,
    ALPHA158_PROCEDURE_VERSION,
    factor_name,
)
from karst.gateway.service import Gateway  # noqa: E402

HERE = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Alpha158 因子入庫一次(KARST-064)")
    parser.add_argument("--store", required=True, help="單一定義庫路徑(無預設)")
    parser.add_argument("--snapshot", required=True, help="價格快照編號(無預設)")
    parser.add_argument("--root", default=None, help="快照快取根;留空即用登記的落點")
    parser.add_argument("--writer", default=None, help="寫入者署名")
    args = parser.parse_args(argv)

    with Gateway.open(args.store, writer=args.writer) as gateway:
        report = gateway.ingest_alpha158(snapshot_id=args.snapshot, root=args.root)
        per_factor = _rows_per_factor(gateway)
        findings = gateway.verify()

    summary = report.as_dict()
    summary["procedure_version"] = ALPHA158_PROCEDURE_VERSION
    summary["formula_source"] = ALPHA158_FORMULA_SOURCE
    summary["verify_findings"] = [str(finding) for finding in findings]
    summary["rows_per_factor"] = per_factor
    summary["least_covered"] = sorted(per_factor.items(), key=lambda item: item[1])[:5]

    (HERE / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"入庫行數  {report.written_rows}")
    print(f"因子數    {report.factor_count}")
    print(f"缺值比例  {report.missing_ratio:.6%}")
    print(f"用時      {report.seconds:.1f} 秒")
    print(f"核對      {'清白' if not findings else findings}")
    return 0 if not findings else 3


def _rows_per_factor(gateway: Gateway) -> dict[str, int]:
    """逐條因子在庫內有幾多列。覆蓋率最低那幾條,就是暖身期最長那幾條。"""
    counted: dict[str, int] = {}
    for name in ALPHA158_NAMES:
        version = gateway.store.get_factor_version(factor_name(name))
        counted[name] = int(
            gateway.store.connection.execute(
                "SELECT COUNT(*) FROM factor_value WHERE factor_version_id = ?",
                (version.factor_version_id,),
            ).fetchone()[0]
        )
    return counted


if __name__ == "__main__":
    raise SystemExit(main())
