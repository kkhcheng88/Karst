"""KARST-068:Alpha158 的值搬出定義庫,改存壓縮檔案(D-032),庫檔回到 40 MB 量級。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-29-factor-parquet/migrate_factor_values.py ^
        --store karst.sqlite --snapshot 2026-08-28-a508d635a5fa ^
        --writer KARST-068-factor-parquet

本檔**不另寫一套入庫或遷移邏輯**,四步都是叫現成那幾道門:

1. 經唯一入口重新入庫一次(``gateway.ingest_alpha158``)——值今次落
   ``data/factors/<快照編號>/alpha158.parquet``,定義庫只留登記與雜湊。
2. 關庫再開一次:第 11 版遷移在這一刻行(``karst.schema``),它逐個因子版本核對
   「檔案登記的行數 = 表內的行數」而且檔案真的在落點上,三項齊備才把
   ``factor_value`` 清空重建。對不上就一列都不動——那時這個腳本會照實報出來。
3. ``VACUUM``:清空只是把頁面標成可再用,庫檔要重寫一次先縮得返。
4. ``karst verify``:定義逐列核簽章,連每個因子值批次檔重讀再算一次雜湊。

落檔的是 ``summary.json``:遷移前後庫檔大小、Parquet 大小、行數與缺值比例,連同
**逐條因子的行數與 KARST-064 那次的對照**——搬完之後每一條因子有幾多個值,一個
都不可以少。沒有預設值:``--store`` 與 ``--snapshot`` 都要給。

重跑安全:同一批值原封不動重寫當沿用(內容雜湊一樣就一個字都不寫),遷移那一步
跑過即在 ``schema_meta`` 留一筆,不會再數第二次。
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:  # 未裝套件也跑得動(倉根就在上兩層)
    sys.path.insert(0, str(REPO))

from karst.factors import ALPHA158_NAMES  # noqa: E402
from karst.gateway.alpha158 import (  # noqa: E402
    ALPHA158_BATCH,
    ALPHA158_PROCEDURE_VERSION,
    factor_name,
)
from karst.gateway.service import Gateway  # noqa: E402
from karst.schema import FACTOR_VALUES_TO_FILES_MIGRATION_KEY  # noqa: E402

HERE = Path(__file__).resolve().parent
BASELINE = REPO / "experiments" / "2026-08-29-alpha158-ingest" / "summary.json"
MB = 1024 * 1024


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="因子值搬去 Parquet 並縮庫(KARST-068)")
    parser.add_argument("--store", required=True, help="單一定義庫路徑(無預設)")
    parser.add_argument("--snapshot", required=True, help="價格快照編號(無預設)")
    parser.add_argument("--root", default=None, help="快照快取根;留空即用登記的落點")
    parser.add_argument("--factor-root", dest="factor_root", default=None,
                        help="因子值批次檔的根(留空即 data/factors)")
    parser.add_argument("--writer", default=None, help="寫入者署名")
    args = parser.parse_args(argv)

    store_path = Path(args.store)
    size_before = store_path.stat().st_size

    # 一、經唯一入口重新入庫:值落 Parquet,庫內只留登記與雜湊
    with Gateway.open(args.store, writer=args.writer) as gateway:
        legacy_rows = _count(gateway, "SELECT COUNT(*) FROM factor_value")
        report = gateway.ingest_alpha158(
            snapshot_id=args.snapshot, root=args.root, factor_root=args.factor_root
        )
        batch = gateway.store.get_factor_value_batch(ALPHA158_BATCH, args.snapshot)
        rows_per_factor = {
            name: batch.rows_of(
                gateway.store.get_factor_version(factor_name(name)).factor_version_id
            )
            for name in ALPHA158_NAMES
        }

    # 二、關庫再開:第 11 版遷移在這一刻行
    with Gateway.open(args.store, writer=args.writer) as gateway:
        remaining = _count(gateway, "SELECT COUNT(*) FROM factor_value")
        note = gateway.store.connection.execute(
            "SELECT value FROM schema_meta WHERE key = ?",
            (FACTOR_VALUES_TO_FILES_MIGRATION_KEY,),
        ).fetchone()

    # 三、VACUUM:清空只是把頁面標成可再用,庫檔要重寫一次先縮得返
    vacuumed = sqlite3.connect(str(store_path))
    vacuumed.execute("VACUUM")
    vacuumed.close()
    size_after = store_path.stat().st_size

    # 四、全庫核對:定義逐列核簽章,連因子值檔重讀再算一次雜湊
    with Gateway.open(args.store, writer=args.writer) as gateway:
        findings = gateway.verify(factor_root=args.factor_root)

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    differing = {
        name: (count, baseline["rows_per_factor"][name])
        for name, count in rows_per_factor.items()
        if count != baseline["rows_per_factor"][name]
    }

    parquet_bytes = Path(batch.path).stat().st_size
    summary = report.as_dict()
    summary.update(
        {
            "procedure_version": ALPHA158_PROCEDURE_VERSION,
            "legacy_rows_in_table_before": legacy_rows,
            "rows_left_in_table_after": remaining,
            "migration_note": None if note is None else note[0],
            "store_bytes_before": size_before,
            "store_bytes_after": size_after,
            "store_mb_before": round(size_before / MB, 1),
            "store_mb_after": round(size_after / MB, 1),
            "parquet_bytes": parquet_bytes,
            "parquet_mb": round(parquet_bytes / MB, 1),
            "baseline_written_rows": baseline["written_rows"],
            "baseline_missing_ratio": baseline["missing_ratio"],
            "rows_match_baseline": report.written_rows == baseline["written_rows"],
            "missing_ratio_matches_baseline": (
                abs(report.missing_ratio - baseline["missing_ratio"]) < 1e-12
            ),
            "factors_differing_from_baseline": differing,
            "verify_findings": [str(finding) for finding in findings],
            "rows_per_factor": rows_per_factor,
        }
    )
    (HERE / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"入庫行數    {report.written_rows}(KARST-064:{baseline['written_rows']})")
    print(f"缺值比例    {report.missing_ratio:.6%}(KARST-064:{baseline['missing_ratio']:.6%})")
    print(f"逐條對照    {'158 條全部一樣' if not differing else differing}")
    print(f"值的落點    {batch.path}({parquet_bytes / MB:.1f} MB)")
    print(f"表內舊值    {legacy_rows} → {remaining}")
    print(f"庫檔大小    {size_before / MB:.1f} MB → {size_after / MB:.1f} MB")
    print(f"核對        {'清白' if not findings else findings}")
    ok = not findings and remaining == 0 and not differing
    return 0 if ok else 3


def _count(gateway: Gateway, sql: str) -> int:
    return int(gateway.store.connection.execute(sql).fetchone()[0])


if __name__ == "__main__":
    raise SystemExit(main())
