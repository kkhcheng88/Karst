"""thesis/composite_score.py — tier-2 個股 0-100 綜合分(P1,docs/2026-07-15_quantification_review.md)。

PURE COMPOSITION,零新訊號:五個維度全部係現有已回測/已驗證管道嘅輸出
(theme_signal 嘅 pe_pctile/vs_200sma、valuation.py 嘅 P_base、crowding_composite、
themes.yaml 嘅 confidence/cycle_stage),本模組唯一新增嘅嘢係「組合」——
band 映射 + 加權平均。權重凍結喺 thesis/composite_weights.yaml(設計時旋鈕,
執行時只讀;等權起步,理由見該檔)。

用途邊界(鐵律,同 repo 其他訊號一致):
  1. pick_ticker 排序 + 日報/同儕對比顯示 —— 即刻用(sizing-neutral)。
  2. 入 sizing 前必須過 A/B 增量回測(vs expression.py:66 現行 gate score,
     long-only mirror、4 股種、2016+ 前後半)。
  3. pre-profit/binary 名(冇 pe_pctile 又冇正 P_base)行 N/A 車道 ——
     score=None + na_reason,唔造假分(同 valuation.py N/A-binary 桶同一誠實原則)。

Forward log:dashboard_render 每個交易日 append 全部計到分嘅 ticker 落
thesis/composite_log.jsonl(COMMITTED,同 track_record.jsonl 同款)——composite 係
point-in-time 讀數,事後砌唔返(crowding/valuation 檔會被覆寫),要驗證權重就只能
而家開始儲。呢個 log 就係第 2 點嗰個回測嘅未來數據源。

呼叫方:thesis/dashboard_render.py(日常路徑,免重複拉數);本檔冇 CLI——
數據拉取係 theme_signal/valuation/crowding 嘅工,唔喺度重做。
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))          # thesis/
WEIGHTS_PATH = os.path.join(ROOT, "composite_weights.yaml")
LOG_PATH = os.path.join(ROOT, "composite_log.jsonl")

LATE_STAGES = {"late", "mid-late"}
THESIS_LATE_HAIRCUT = 0.8   # late-cycle theme 嘅 confidence 維度打 8 折(cycle 語境,唔係新判斷)


def load_weights(path: str = WEIGHTS_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    return {"weights": cfg.get("weights") or {}, "min_dims": int(cfg.get("min_dims", 3))}


# ============================================================================
# band 映射(邏輯住喺 code,權重住喺 YAML——band 唔係 tuning 旋鈕,係讀數語義)
# ============================================================================


def _f(x):
    """Robust float: theme_signal rows carry strings ('87.3', '+43.9%', 'n/a', '—')."""
    if x is None:
        return None
    try:
        return float(str(x).replace("%", "").replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def dim_trend(vs200sma) -> float | None:
    """vs 200SMA % -> 0-100。帶狀而非線性:200SMA 閘本身係二元(上/落),帶狀保留
    「離線幾遠」嘅資訊但唔扮連續精確。破位=0 對齊 verdict 狀態機嘅 KILL-WATCH。"""
    v = _f(vs200sma)
    if v is None:
        return None
    if v >= 15:
        return 100.0
    if v >= 5:
        return 80.0
    if v >= 0:
        return 60.0
    if v >= -5:
        return 30.0
    return 0.0


def dim_value(pe_pctile) -> float | None:
    """自身歷史 PE 分位反轉:平(低分位)= 高分。"""
    p = _f(pe_pctile)
    if p is None:
        return None
    return round(max(0.0, min(100.0, 100.0 - p)), 1)


def dim_expect(p_base) -> float | None:
    """P_base@14x 帶狀(valuation.py 分類閾值 0.4/0.8 嘅分數化,唔另設新閾值)。
    負 P_base = N/A-binary placeholder,唔係真讀數 -> None。"""
    pb = _f(p_base)
    if pb is None or pb < 0:
        return None
    if pb >= 0.8:
        return 100.0
    if pb >= 0.4:
        return 60.0
    return 25.0


def dim_crowd(crowding_pctile) -> float | None:
    """theme 擁擠分位反轉(買入視角:少人迫=高分)。theme-level 讀數,同 theme
    內逐隻 ticker 共用——crowding_composite 冇個股粒度,唔扮有。"""
    c = _f(crowding_pctile)
    if c is None:
        return None
    return round(max(0.0, min(100.0, 100.0 - c)), 1)


def dim_thesis(confidence, cycle_stage) -> float | None:
    conf = _f(confidence)
    if conf is None:
        return None
    base = max(0.0, min(1.0, conf)) * 100.0
    if str(cycle_stage) in LATE_STAGES:
        base *= THESIS_LATE_HAIRCUT
    return round(base, 1)


# ============================================================================
# 組合
# ============================================================================


def score_ticker(row: dict, theme_ctx: dict, cfg: dict | None = None) -> dict:
    """row: theme_signal 風格 ticker dict(pe_pctile / vs200sma,字串亦可)。
    theme_ctx: {confidence, cycle_stage, crowding_pctile, p_base}(theme/valuation 層語境)。
    回傳 {score, dims, n_dims, na_reason}——score=None 即 N/A 車道。"""
    cfg = cfg or load_weights()
    dims = {
        "trend": dim_trend(row.get("vs200sma")),
        "value": dim_value(row.get("pe_pctile")),
        "expect": dim_expect(theme_ctx.get("p_base")),
        "crowd": dim_crowd(theme_ctx.get("crowding_pctile")),
        "thesis": dim_thesis(theme_ctx.get("confidence"), theme_ctx.get("cycle_stage")),
    }
    # pre-profit/binary 車道:估值同預期兩個維度都冇 -> 綜合分對呢類名冇意義
    # (剩返 trend/crowd/thesis 全部係 theme 層或純技術,冇個股基本面錨)。
    if dims["value"] is None and dims["expect"] is None:
        return {"score": None, "dims": dims, "n_dims": 0,
                "na_reason": "pre-profit/option-framing(冇 PE 分位亦冇正 P_base)——用事件/選擇權框架另評,綜合分不適用"}
    avail = {k: v for k, v in dims.items() if v is not None}
    if len(avail) < cfg["min_dims"]:
        return {"score": None, "dims": dims, "n_dims": len(avail),
                "na_reason": f"可用維度僅 {len(avail)} 個(<{cfg['min_dims']}),唔出分"}
    w = cfg["weights"]
    total_w = sum(w.get(k, 0.0) for k in avail)
    if total_w <= 0:
        return {"score": None, "dims": dims, "n_dims": len(avail), "na_reason": "權重和為 0"}
    score = sum(v * w.get(k, 0.0) for k, v in avail.items()) / total_w
    return {"score": round(score, 1), "dims": dims, "n_dims": len(avail), "na_reason": None}


# ============================================================================
# forward log(committed;point-in-time,事後砌唔返——權重驗證嘅未來數據源)
# ============================================================================


def append_log(scored_rows: list, as_of: str) -> int:
    """scored_rows: [{ticker, theme, score, dims}]。同日已 log 過就 skip(idempotent,
    morning+evening 兩次 run 只記一次)。"""
    seen = set()
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        seen.add(json.loads(line).get("as_of"))
                    except json.JSONDecodeError:
                        continue
    if as_of in seen:
        return 0
    n = 0
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        for r in scored_rows:
            if r.get("score") is None:
                continue
            fh.write(json.dumps({
                "as_of": as_of, "ticker": r["ticker"], "theme": r.get("theme"),
                "score": r["score"], "dims": r.get("dims"),
                "logged_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False) + "\n")
            n += 1
    return n
