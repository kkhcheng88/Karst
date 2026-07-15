"""thesis/magnitude_features.py -- P3(docs/2026-07-15_quantification_review.md 提案3):
magnifier 五特徵入面三個轉機械。

WHY:themes.yaml 每個 theme 嘅 nodes(magnitude_tier: 2x/2-3x/3-5x-durable/5-10x-binary)係 magnifier
五特徵人手判。五個特徵入面三個可以機械計:
  F2 估值 headroom -- node tickers 嘅 ttm_pe 自身歷史分位(reuse thesis/theme_signal.py 嘅
                       ticker_metrics(),唔重寫佢嘅邏輯)
  F3 距底部        -- 現價喺自己 trailing 5 年(或可用歷史)close 範圍嘅分位
  F5 擁擠          -- theme 級 crowding composite pctile(thesis/.raw/crowding_composite.json),
                       node 繼承 theme 讀數
F1(新事實強度)、F4(樽頸位置)保留判斷,唔喺呢個腳本入面(rubric 錨定,人/貴模型判)。

計咗機械讀數之後,一致性 flag(v1 只有兩條規則,刻意唔加多)提供夜班客觀對照——「計算特徵有變
先值得人手覆核」,唔使平模型自己作判「證據薄唔薄」。flag 永遠只係「建議覆核」,唔會自動改
magnitude_tier(判斷保留畀人/貴模型,同 kill_metrics.py 嘅「唔自動 kill」原則一致)。

F2 設計選擇:用 ticker_metrics() 嘅 pe_pctile_verdict(而非原始 pe_pctile)-- 排除 stale/
peak-earnings artifact 讀數(見 theme_signal.py PE_STALE_DAYS 註解),同 theme_signal 嘅 verdict
邏輯口徑一致,避免一隻已轉虧損嘅名嘅舊 PE 讀數扮「現時仲平」。

F3 效率設計:唔重新 data.load() 一次 -- 直接攞 ticker_metrics() 內部已經經 backtest/data.py load()
攞返嚟嘅完整 adjusted close 序列(row["price"]),喺呢個序列上面取 trailing 窗口計 percentile。
同一隻 ticker 唔使攞兩次價,数据來源仍然係 backtest/data.py 嘅 load()。

已知圖裂縫,graceful N/A(唔 crash):SKHY 冇價格數據、SIVE 可能載入失敗;逐 ticker try/except,
一隻死唔會炸成個 report(標 error 繼續)。

CLI:
  PYTHONUTF8=1 python thesis/magnitude_features.py --report
      計全部 active theme 嘅 node,print 逐 theme 逐 node 表(node/tier/F2/F3/F5/flags)+ 寫
      thesis/.raw/magnitude_features_report.json(gitignored,regenerable,同 kill_metrics_report.json/
      crowding_composite.json 一致嘅慣例)。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402
import yaml  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
THEMES_PATH = os.path.join(ROOT, "themes.yaml")
CROWDING_JSON = os.path.join(ROOT, ".raw", "crowding_composite.json")
OUT_JSON = os.path.join(ROOT, ".raw", "magnitude_features_report.json")

# sibling import -- reuse thesis/theme_signal.py 嘅 ticker_metrics(),唔重寫佢嘅估值/價格邏輯。
sys.path.insert(0, ROOT)
import theme_signal  # noqa: E402

STALE_DAYS = 60          # last_scored 距今 > 呢個日數 -> 標「已過期,值得夜班覆核」
F3_WINDOW_DAYS = 5 * 252  # trailing 5 年(交易日近似);可用歷史唔夠 5 年就用全部(pandas tail 自動處理)
VALID_TIERS = {"2x", "2-3x", "3-5x-durable", "5-10x-binary"}


def load_active_themes() -> dict:
    with open(THEMES_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    themes = data.get("themes", {}) or {}
    return {slug: t for slug, t in themes.items() if t.get("status", "active") == "active"}


def load_crowding() -> dict:
    try:
        with open(CROWDING_JSON, encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("themes", {}) or {}
    except Exception:
        return {}


def _staleness(last_scored, today: date):
    """last_scored(YAML 通常已解析做 date;容錯 str/None)-> (距今日數 or None, 是否 stale)。"""
    if last_scored is None:
        return None, False
    d = last_scored
    if isinstance(d, datetime):
        d = d.date()
    if isinstance(d, str):
        try:
            d = datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            return None, False
    if not isinstance(d, date):
        return None, False
    days = (today - d).days
    return days, days > STALE_DAYS


def safe_ticker_metrics(sym: str) -> dict:
    """theme_signal.ticker_metrics() 本身已經逐段 try/except、聲稱 never raise,但呢度再包一層
    防禦(任務要求逐 ticker try/except),一隻 ticker 死唔好炸成個 report。"""
    try:
        return theme_signal.ticker_metrics(sym)
    except Exception as e:
        return {"symbol": sym, "price": None, "pe_pctile_verdict": None,
                "pe_pctile": None, "error": str(e)[:160]}


def f2_valuation_pctile(ticker_rows: list[dict]):
    """F2 估值 headroom:median(pe_pctile_verdict),排除 stale/None。多 ticker 取 median;
    冇一隻有現行 PE 讀數 -> None(N/A)。"""
    vals = [r.get("pe_pctile_verdict") for r in ticker_rows if r.get("pe_pctile_verdict") is not None]
    if not vals:
        return None
    return float(np.median(vals))


def f3_bottom_pctile(ticker_rows: list[dict]):
    """F3 距底部:每 ticker 用 ticker_metrics() 已載入嘅完整 adjusted close 序列(row["price"],
    backtest/data.py load() 攞返嚟),取 trailing 5 年(或全部可用歷史)嘅 [lo, hi] 位置,
    0=貼 5 年低點(有利),100=貼 5 年高點(不利)。多 ticker 取 median;冇任何 ticker 有足夠
    價格歷史(<20 行)-> None(N/A)。"""
    vals = []
    for r in ticker_rows:
        px = r.get("price")
        if px is None or len(px) < 20:
            continue
        tail = px.tail(F3_WINDOW_DAYS)
        lo, hi = float(tail.min()), float(tail.max())
        if hi <= lo:
            continue
        vals.append(float((tail.iloc[-1] - lo) / (hi - lo) * 100.0))
    if not vals:
        return None
    return float(np.median(vals))


def consistency_flags(tier, f2, f3, f5) -> list[str]:
    """v1 兩條規則(刻意唔加多)。永遠只係「建議覆核」,唔改 magnitude_tier。"""
    flags = []
    if tier in {"3-5x-durable", "5-10x-binary"} and f5 is not None and f5 >= 90:
        flags.append("高 magnitude 檔+極端擁擠,建議覆核")
    if (tier == "2x" and f2 is not None and f2 < 30 and f3 is not None and f3 < 40
            and f5 is not None and f5 < 50):
        flags.append("低檔位但三個計算特徵齊指 magnifier-genuine setup,建議覆核")
    return flags


def compute_node(slug: str, node: dict, f5, f5_status: str, today: date) -> dict:
    name = node.get("name")
    tickers = node.get("tickers") or []
    tier = node.get("magnitude_tier")
    last_scored = node.get("last_scored")
    stale_days, is_stale = _staleness(last_scored, today)
    last_scored_s = last_scored.isoformat() if hasattr(last_scored, "isoformat") else (
        str(last_scored) if last_scored is not None else None)

    base = {
        "theme": slug, "name": name, "tickers": tickers, "magnitude_tier": tier,
        "tier_recognized": tier in VALID_TIERS,
        "last_scored": last_scored_s, "stale_days": stale_days, "stale": bool(is_stale),
        "f5_crowding_pctile": f5, "f5_status": f5_status,
    }

    if not tickers:
        base.update({
            "status": "skip_etf_only_leg",
            "f2_valuation_pctile": None, "f3_bottom_pctile": None,
            "flags": [], "ticker_detail": [],
        })
        return base

    ticker_rows = [safe_ticker_metrics(sym) for sym in tickers]
    f2 = f2_valuation_pctile(ticker_rows)
    f3 = f3_bottom_pctile(ticker_rows)
    flags = consistency_flags(tier, f2, f3, f5)
    ticker_detail = [{
        "symbol": r.get("symbol"),
        "pe_pctile_verdict": r.get("pe_pctile_verdict"),
        "pe_pctile_stale_days": r.get("pe_stale_days"),
        "has_price": r.get("price") is not None,
        "error": r.get("error"),
    } for r in ticker_rows]

    base.update({
        "status": "ok",
        "f2_valuation_pctile": f2, "f3_bottom_pctile": f3,
        "flags": flags, "ticker_detail": ticker_detail,
    })
    return base


def run(write: bool = True) -> dict:
    themes = load_active_themes()
    crowding = load_crowding()
    today = date.today()

    theme_reports: dict[str, dict] = {}
    themes_without_nodes: list[str] = []
    n_nodes_total = n_nodes_skipped = n_nodes_flagged = n_nodes_stale = 0

    for slug, t in sorted(themes.items()):
        nodes = t.get("nodes") or []
        if not nodes:
            themes_without_nodes.append(slug)
            continue

        crowd_entry = crowding.get(slug)
        if crowd_entry and crowd_entry.get("composite_status") == "ok" \
                and crowd_entry.get("composite_pctile") is not None:
            f5 = float(crowd_entry["composite_pctile"])
            f5_status = "ok"
        else:
            f5 = None
            f5_status = (crowd_entry.get("composite_status") if crowd_entry
                         else "not_in_crowding_composite_json")

        node_rows = []
        for node in nodes:
            row = compute_node(slug, node, f5, f5_status, today)
            n_nodes_total += 1
            if row["status"] == "skip_etf_only_leg":
                n_nodes_skipped += 1
            if row["flags"]:
                n_nodes_flagged += 1
            if row["stale"]:
                n_nodes_stale += 1
            node_rows.append(row)

        theme_reports[slug] = {"f5_crowding_pctile": f5, "f5_status": f5_status, "nodes": node_rows}

    # ---------- print ----------
    print(f"=== magnitude_features report ({today.isoformat()}): "
          f"{len(theme_reports)}/{len(themes)} active themes 有 nodes, "
          f"{n_nodes_total} nodes 總計({n_nodes_skipped} ETF-only skip, "
          f"{n_nodes_stale} stale>{STALE_DAYS}日), {n_nodes_flagged} 觸一致性 flag ===\n")

    header = f"{'node':<30}{'tier':<16}{'F2(val)':>9}{'F3(bot)':>9}{'F5(crowd)':>10}  flags"
    for slug in sorted(theme_reports):
        rep = theme_reports[slug]
        f5_s = f"{rep['f5_crowding_pctile']:.1f}" if rep["f5_crowding_pctile"] is not None else "n/a"
        print(f"[{slug}]  (F5 theme-level={f5_s}, status={rep['f5_status']})")
        print("  " + header)
        for row in rep["nodes"]:
            if row["status"] == "skip_etf_only_leg":
                print(f"  {row['name']:<30}{str(row['magnitude_tier']):<16}"
                      f"{'skip':>9}{'skip':>9}{'skip':>10}  (ETF-only leg, 冇 ticker 可計)")
                continue
            f2_s = f"{row['f2_valuation_pctile']:.0f}" if row["f2_valuation_pctile"] is not None else "n/a"
            f3_s = f"{row['f3_bottom_pctile']:.0f}" if row["f3_bottom_pctile"] is not None else "n/a"
            f5r_s = f"{row['f5_crowding_pctile']:.0f}" if row["f5_crowding_pctile"] is not None else "n/a"
            stale_tag = f" [STALE {row['stale_days']}d]" if row["stale"] else ""
            flag_s = "; ".join(row["flags"]) if row["flags"] else ""
            print(f"  {row['name']:<30}{str(row['magnitude_tier']):<16}"
                  f"{f2_s:>9}{f3_s:>9}{f5r_s:>10}  {flag_s}{stale_tag}")
        print()

    if themes_without_nodes:
        print("冇 nodes 定義(仍係 theme-level 舊格式,未跑 per-node schema batch):")
        print("  " + ", ".join(themes_without_nodes) + "\n")

    flagged_lines = []
    for slug in sorted(theme_reports):
        for row in theme_reports[slug]["nodes"]:
            for f in row["flags"]:
                flagged_lines.append(f"{slug}/{row['name']} ({row['magnitude_tier']}): {f}")
    if flagged_lines:
        print(f"=== {len(flagged_lines)} 個 node 觸 flag(建議夜班放入 magnifier_review_queue.md) ===")
        for line in flagged_lines:
            print("  " + line)
    else:
        print("0 個 node 觸 flag")

    stale_lines = [f"{slug}/{row['name']}({row['stale_days']}日)"
                   for slug in sorted(theme_reports) for row in theme_reports[slug]["nodes"]
                   if row["stale"]]
    if stale_lines:
        print(f"\n{len(stale_lines)} 個 node last_scored 已過期(>{STALE_DAYS}日):")
        print("  " + ", ".join(stale_lines))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of_date": today.isoformat(),
        "stale_threshold_days": STALE_DAYS,
        "f3_window_trading_days": F3_WINDOW_DAYS,
        "n_active_themes": len(themes),
        "n_themes_with_nodes": len(theme_reports),
        "themes_without_nodes": themes_without_nodes,
        "n_nodes_total": n_nodes_total,
        "n_nodes_skipped_etf_only": n_nodes_skipped,
        "n_nodes_stale": n_nodes_stale,
        "n_nodes_flagged": n_nodes_flagged,
        "flagged": flagged_lines,
        "themes": theme_reports,
    }
    if write:
        os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
        with open(OUT_JSON, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"\nWrote {OUT_JSON}")
    return payload


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true",
                     help="計全部 active theme 嘅 node magnitude features,print 表 + 寫 "
                          "thesis/.raw/magnitude_features_report.json")
    args = ap.parse_args()
    if args.report or len(sys.argv) == 1:
        run(write=True)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
