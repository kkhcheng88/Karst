"""KARST-066:Alpha158 對兩個宇宙 × 三個持有期窗口的因子預測力實測。

依票上留言(2026-08-29 main)擴大的範圍:

  * 兩個宇宙——起步宇宙十二隻(快照 2026-08-28-a508d635a5fa)、
    標普 500 歷史成分(快照 2026-08-28-493fd1df1cb9,625 實體)。
  * 三個持有期窗口——1、5、21 個交易日(research/2026-08-29-factor-horizon-evidence.md
    結語建議)。
  * 每個(宇宙 × 窗口)對全部 158 條 Alpha158 因子逐條算 IC 均值、標準差、ICIR、
    樣本日數(``karst.factorpredict``,KARST-066 本票新寫的對齊 + IC/ICIR 算法)。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-29-factor-ic/run_factor_ic.py --store karst.sqlite

逐條因子逐個宇宙逐個窗口分開處理(不是一次過拼成一張幾億列的表)——標普 500
625 實體 × 158 條因子 × 約 2,900 個交易日,一次拼全部因子會撐爆記憶體;逐條處理
把單次常駐記憶體壓在一條因子的量級(數百萬列),算完即棄。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:  # 未裝套件也跑得動(倉根就在上兩層)
    sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from karst.data import read_price_frame  # noqa: E402
from karst.factorpredict import align_factor_to_forward_returns, daily_ic, summarize_ic  # noqa: E402
from karst.factorvalues import FactorValueReader  # noqa: E402
from karst.factors import ALPHA158_NAMES  # noqa: E402
from karst.gateway.alpha158 import factor_name  # noqa: E402
from karst.gateway.service import Gateway  # noqa: E402

HERE = Path(__file__).resolve().parent
HORIZONS = (1, 5, 21)
UNIVERSES = (
    {"key": "起步十二隻", "snapshot_id": "2026-08-28-a508d635a5fa"},
    {"key": "標普500歷史成分", "snapshot_id": "2026-08-28-493fd1df1cb9"},
)

#: 對照量級,出處見 research/2026-08-29-factor-horizon-evidence.md 結語第一、三節。
A_SHARE_BENCHMARK_IC = "0.04–0.05(qlib 官方 CSI300 基準,Alpha158,次日持有,DoubleEnsemble/XGBoost/CatBoost)"
US_PERSONAL_REPRO_IC = "約 0.005(個人部落格業餘覆現,qlib sp500,Alpha360/LightGBM,非機構級)"
#: 「有訊號」的門檻,結語一句業務結語要答「有幾多條因子 |IC| ≥ 0.02」時用。
SIGNAL_THRESHOLD = 0.02


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True, help="單一定義庫路徑(無預設)")
    parser.add_argument("--factor-root", default=None, help="因子值批次檔根(預設 data/factors)")
    parser.add_argument("--price-root", default=None, help="價格快照快取根(預設 data/snapshots)")
    return parser.parse_args()


def _resolve_names_for_snapshot(gateway: Gateway, names: list[str], snapshot_id: str) -> list[str]:
    """把「因子名稱」逐條解成「因子名稱@版本號」,版本號揀**這個快照那一版**。

    不能用「留空即最新版」——KARST-066 排查時(見 README「未解」一節)踩過一次:
    一次入庫因記憶體不足半途死掉,登記那步(逐版本先落庫,寫值那步才失敗)已經
    把全部 158 條推上新版、且新版的 procedure.input_data_version 指向另一個快照,
    令「最新版」不再對應這個快照的值。走版本鏈找 procedure.input_data_version
    等於這個快照編號的那一版,不猜「最新=這份」。
    """
    resolved: list[str] = []
    for name in names:
        chain = gateway.store.factor_version_chain(name)
        match = next(
            (
                version
                for version in chain
                if version.procedure.kind == "formula"
                and version.procedure.input_data_version == snapshot_id
            ),
            None,
        )
        if match is None:
            raise SystemExit(
                f"因子「{name}」在版本鏈裡找不到 input_data_version={snapshot_id} 的那一版"
            )
        resolved.append(f"{name}@{match.version_no}")
    return resolved


def run(args: argparse.Namespace) -> dict:
    started = time.perf_counter()
    base_names = [factor_name(name) for name in ALPHA158_NAMES]

    results: list[dict] = []
    with Gateway.open(args.store, writer="KARST-066-factor-ic") as gateway:
        store = gateway.factor_values(args.factor_root)
        # 取值經全平台唯一那條路(KARST-088):表與因子值批次兩個住處一齊看。
        reader = FactorValueReader(gateway.store, store.root)
        for universe in UNIVERSES:
            snapshot_id = universe["snapshot_id"]
            print(f"== 宇宙 {universe['key']}({snapshot_id}) ==", file=sys.stderr)
            price_frame = read_price_frame(gateway.store, snapshot_id, root=args.price_root)
            entity_count = price_frame["entity_id"].nunique()

            names = _resolve_names_for_snapshot(gateway, base_names, snapshot_id)
            base_of = dict(zip(names, base_names))

            # 一次過讀全部 158 條因子的長表(同一個批次檔,一次 I/O),之後逐條因子
            # 在記憶體裡切片——切片不必再讀檔,只有 align/daily_ic 逐條因子重算。
            factor_long_all = reader.history(
                names, snapshot_id=snapshot_id, as_of=None, start=None, end=None,
                entity_ids=None,
            )
            version_of = {name: store.resolve(name) for name in names}

            for horizon in HORIZONS:
                t0 = time.perf_counter()
                for name in names:
                    version = version_of[name]
                    base_name = base_of[name]
                    one = factor_long_all[
                        factor_long_all["factor_version_id"] == version.factor_version_id
                    ]
                    if one.empty:
                        continue
                    aligned = align_factor_to_forward_returns(one, price_frame, horizon=horizon)
                    if aligned.empty:
                        results.append(
                            {
                                "universe": universe["key"],
                                "snapshot_id": snapshot_id,
                                "entity_count": int(entity_count),
                                "horizon": horizon,
                                "factor": base_name,
                                "factor_version_no": version.version_no,
                                "ic_mean": None,
                                "ic_std": None,
                                "icir": None,
                                "n_days": 0,
                            }
                        )
                        continue
                    daily = daily_ic(aligned)
                    summary = summarize_ic(daily)
                    if summary.empty:
                        row = {"ic_mean": None, "ic_std": None, "icir": None, "n_days": 0}
                    else:
                        s = summary.iloc[0]
                        row = {
                            "ic_mean": None if pd.isna(s["ic_mean"]) else float(s["ic_mean"]),
                            "ic_std": None if pd.isna(s["ic_std"]) else float(s["ic_std"]),
                            "icir": None if pd.isna(s["icir"]) else float(s["icir"]),
                            "n_days": int(s["n_days"]),
                        }
                    results.append(
                        {
                            "universe": universe["key"],
                            "snapshot_id": snapshot_id,
                            "entity_count": int(entity_count),
                            "horizon": horizon,
                            "factor": base_name,
                            "factor_version_no": version.version_no,
                            **row,
                        }
                    )
                elapsed = time.perf_counter() - t0
                print(f"  持有期 {horizon} 個交易日:158 條算完,用時 {elapsed:.1f} 秒", file=sys.stderr)

    ranked = sorted(
        (row for row in results if row["ic_mean"] is not None),
        key=lambda row: abs(row["ic_mean"]),
        reverse=True,
    )
    top20 = ranked[:20]
    signal_count = sum(
        1 for row in results if row["ic_mean"] is not None and abs(row["ic_mean"]) >= SIGNAL_THRESHOLD
    )

    return {
        "ticket": "KARST-066",
        "horizons": list(HORIZONS),
        "universes": UNIVERSES,
        "benchmark": {
            "a_share_csi300_ic": A_SHARE_BENCHMARK_IC,
            "us_personal_repro_ic": US_PERSONAL_REPRO_IC,
            "signal_threshold": SIGNAL_THRESHOLD,
            "source": "research/2026-08-29-factor-horizon-evidence.md",
        },
        "holding_period_convention": (
            "第 1 個交易日(可執行時點那根 K 線)開價買入,持有到第 N 個交易日"
            "(含首日在內)收價賣出(karst/factorpredict.py 文首說明)"
        ),
        "results": results,
        "top20_by_abs_ic_mean": top20,
        "signal_count_abs_ic_ge_threshold": signal_count,
        "total_factor_horizon_universe_rows": len(results),
        "seconds": time.perf_counter() - started,
    }


def main() -> int:
    args = parse_args()
    summary = run(args)
    (HERE / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print(f"落檔:{HERE / 'summary.json'}", file=sys.stderr)
    print(f"總用時 {summary['seconds']:.1f} 秒", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
