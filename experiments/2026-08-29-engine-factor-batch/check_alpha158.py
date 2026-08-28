"""KARST-071:證明選股引擎取得到住在因子值批次(Parquet)裡的 Alpha158 值。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-29-engine-factor-batch/check_alpha158.py

做四件事,全部**只讀**——不登記策略、不落運行、一列都不寫入庫:

1. 揀一條 Alpha158 因子、一個決策日,把引擎那條路取回來的「最新已知值」與直接開
   Parquet 自己挑一次的結果**逐格對數**。
2. 證明知情時間閘沒有鬆:取回來的每一個值,知情時點都在該日收工之前;檔裡知情時點
   在該日之後的那些值,一個都沒有混進來。
3. 用同一條因子經 ``run_ranking_rebalance`` 跑一次完整回測——策略經現有介面
   (簽名一格沒有改)真的用得着這批值。
4. 數字落 ``summary.json``。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:      # 未裝套件也跑得動(倉根就在上兩層)
    sys.path.insert(0, str(REPO))
_EXPERIMENTS = REPO / "experiments"
if str(_EXPERIMENTS) not in sys.path:   # 現役快照編號共用一份(KARST-057)
    sys.path.insert(0, str(_EXPERIMENTS))

from snapshot_ids import PRICE_LARGE_CAP  # noqa: E402
from karst.data.snapshots import read_price_panel  # noqa: E402
from karst.engine import PricePanel, read_factor_panel, run_ranking_rebalance  # noqa: E402
from karst.engine.factorvalues import FactorValueSource  # noqa: E402
from karst.factorstore import DEFAULT_FACTOR_ROOT, FactorValueStore  # noqa: E402
from karst.store import DefinitionStore  # noqa: E402

HERE = Path(__file__).resolve().parent

STORE_PATH = REPO / "karst.sqlite"
SNAPSHOT_ROOT = REPO / "data" / "snapshots"
SNAPSHOT_ID = PRICE_LARGE_CAP

# 對數用的一條因子與一個決策日。取值是示例,不是現役設定。
FACTOR = "Alpha158·KMID"
DECISION_DAY = "2020-06-30"

# **版本號要明寫。** 每條 Alpha158 因子現時有兩版:第 1 版對住十二隻那份快照
# (2026-08-28-a508d635a5fa),值就在 alpha158 那個批次檔裡;第 2 版對住標普 500
# 那份快照(2026-08-28-493fd1df1cb9),KARST-064 那次入庫只登記了因子,**一個值
# 都未落**。留空版本號即取最新版,取回來的會是一張空表——不是取值那一路壞了,
# 是那一版根本未算過(缺失=不參與,D-021 第 4 條)。
FACTOR_VERSION_NO = 1

# 第 3 步那次回測的示例參數(可掃描,不是現役設定)。
CADENCE = "monthly"
TOP_N = 3
DIRECTION = "high"


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)

    with DefinitionStore.open(str(STORE_PATH)) as store:
        files = FactorValueStore(store, REPO / DEFAULT_FACTOR_ROOT)
        version = store.get_factor_version(FACTOR, FACTOR_VERSION_NO)
        reference = f"{FACTOR}@{FACTOR_VERSION_NO}"

        # ---- 1. 引擎那條路 vs 直接開檔 ---------------------------------
        source = FactorValueSource(store)
        taken = source.latest_known_values(
            FACTOR, DECISION_DAY, version_no=FACTOR_VERSION_NO
        )

        gate = pd.Timestamp(f"{DECISION_DAY}T23:59:59.999999")
        whole = files.read_long([reference], snapshot_id=SNAPSHOT_ID)
        expected = (
            whole[whole["knowledge_time"] <= gate]
            .sort_values(
                ["entity_id", "event_time", "knowledge_time"],
                ascending=[True, False, False],
                kind="mergesort",
            )
            .drop_duplicates("entity_id", keep="first")
            .set_index("entity_id")["value"]
        )
        got = taken.set_index("entity_id")["value"].astype(float)
        same = list(got.index) == list(expected.index) and bool((got == expected).all())
        print(
            f"[1] 因子「{FACTOR}」第 {version.version_no} 版,決策日 {DECISION_DAY}:"
            f"引擎取回 {len(got)} 隻,直接開檔挑出 {len(expected)} 隻;"
            f"逐格{'一致' if same else '對不上'}"
        )
        if not same:
            raise AssertionError("引擎取回的最新已知值與 Parquet 內的挑法對不上")

        # ---- 2. 知情時間閘(D-021 第 3 條)------------------------------
        taken_knowledge = pd.to_datetime(taken["knowledge_time"])
        after_gate = whole[whole["knowledge_time"] > gate]
        leaked = pd.merge(
            taken[["entity_id", "event_time", "knowledge_time"]].assign(
                event_time=pd.to_datetime(taken["event_time"]),
                knowledge_time=taken_knowledge,
            ),
            after_gate[["entity_id", "event_time", "knowledge_time"]],
            on=["entity_id", "event_time", "knowledge_time"],
        )
        print(
            f"[2] 取回的值知情時點最遲 {taken_knowledge.max()};檔裡知情時點在該日之後"
            f"還有 {len(after_gate)} 個值,混進來的有 {len(leaked)} 個"
        )
        if bool((taken_knowledge > gate).any()) or len(leaked):
            raise AssertionError("取到了知情時點之後才知道的值(前視)")

        # ---- 3. 策略經現有介面跑一次完整回測 ----------------------------
        opens = read_price_panel(
            store, SNAPSHOT_ID, field="open", root=SNAPSHOT_ROOT
        ).dropna(how="any")
        closes = read_price_panel(
            store, SNAPSHOT_ID, field="close", root=SNAPSHOT_ROOT
        ).dropna(how="any")
        common = opens.index.intersection(closes.index)
        panel = PricePanel.from_frames(open=opens.loc[common], close=closes.loc[common])

        result = run_ranking_rebalance(
            store=store,
            panel=panel,
            factor_name=FACTOR,
            cadence=CADENCE,
            top_n=TOP_N,
            direction=DIRECTION,
            version_no=FACTOR_VERSION_NO,
        )
        factor_panel = read_factor_panel(
            store,
            FACTOR,
            [pd.Timestamp(r.decision_date) for r in result.rebalances],
            version_no=FACTOR_VERSION_NO,
            entity_ids=panel.entity_ids,
        )
        filled = int(factor_panel.notna().to_numpy().sum())
        print(
            f"[3] 經 run_ranking_rebalance 跑 {len(panel.dates)} 根 K 線 × "
            f"{len(panel.entity_ids)} 隻:換倉 {len(result.rebalances)} 次、"
            f"成交 {len(result.orders)} 筆、累計回報 {result.total_return:.4f};"
            f"因子面板 {factor_panel.shape[0]} × {factor_panel.shape[1]} 有值 {filled} 格"
        )
        if filled == 0 or not result.orders:
            raise AssertionError("策略經現有介面仍然取不到因子值批次裡的值")

        summary = {
            "ticket": "KARST-071",
            "snapshot_id": SNAPSHOT_ID,
            "factor": {"name": version.name, "version_no": version.version_no,
                       "factor_version_id": version.factor_version_id,
                       "head_version_no": store.get_factor_version(FACTOR).version_no,
                       "note": "第 2 版對住標普 500 快照,登記了但一個值都未落;"
                               "留空版本號即取最新版,會取回一張空表"},
            "batch": {"batch_key": "alpha158", "rows_in_file": int(len(whole))},
            "cross_check": {
                "decision_day": DECISION_DAY,
                "entities_from_engine": int(len(got)),
                "entities_from_file": int(len(expected)),
                "values_identical": same,
                "latest_knowledge_time_taken": str(taken_knowledge.max()),
                "values_known_after_the_gate_in_file": int(len(after_gate)),
                "values_known_after_the_gate_taken": int(len(leaked)),
            },
            "backtest": {
                "cadence": CADENCE, "top_n": TOP_N, "direction": DIRECTION,
                "note": "示例參數,不是現役設定",
                "trading_days": int(len(panel.dates)),
                "entities": int(len(panel.entity_ids)),
                "rebalances": len(result.rebalances),
                "orders": len(result.orders),
                "total_return": float(result.total_return),
                "factor_panel_shape": list(factor_panel.shape),
                "factor_panel_filled_cells": filled,
            },
        }

    (HERE / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("[4] 摘要已落 summary.json")


if __name__ == "__main__":
    main()
