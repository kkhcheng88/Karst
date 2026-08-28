"""KARST-059:引擎 vs 獨立手算,逐日對淨值、逐筆對成交。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-28-engine-crosscheck/compare.py

本檔是**對照的裁判**,不是任何一邊的計算:引擎那一邊只呼叫 ``karst.engine``,
手算那一邊只呼叫 ``handcalc``(純 pandas),兩邊由同一批 CSV 出發,結果逐日相減。

紀律(票 KARST-059 硬性):不讀不寫 karst.sqlite、不寫 data/、不經唯一入口——
引擎只以記憶體內的面板呼叫。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from karst.engine import (                                    # noqa: E402
    BarPanel,
    BreakoutEntry,
    MeasuredMoveTarget,
    MonthlyLossBreaker,
    PricePanel,
    RankingRebalanceParams,
    RiskFractionSizing,
    RuleStrategyParams,
    SwingLowStop,
    rebalance_schedule,
    run_rule_strategy,
)

import handcalc as hc                                          # noqa: E402

AAPL_ID = 1
SPY_ID = 10
QQQ_ID = 20

TOLERANCE = 1e-9          # 票上的容差:相對誤差 1e-9


# ----------------------------------------------------------------------
# 對照用的小工具
# ----------------------------------------------------------------------
def series_diff(engine: pd.Series, hand: pd.Series, label: str) -> dict:
    """兩條逐日序列相減。判定用**相對**誤差:淨值在百萬量級,絕對 1e-9 等於要求
    float64 最後一個 bit 都一樣,那是在考浮點運算次序,不是在考回測邏輯。"""
    joined = pd.DataFrame({"engine": engine.astype(float), "hand": hand.astype(float)})
    joined["abs_diff"] = (joined["engine"] - joined["hand"]).abs()
    scale = joined["engine"].abs().clip(lower=1.0)
    joined["rel_diff"] = joined["abs_diff"] / scale
    worst = joined["rel_diff"].idxmax()
    return {
        "label": label,
        "days": int(len(joined)),
        "max_abs_diff": float(joined["abs_diff"].max()),
        "max_rel_diff": float(joined["rel_diff"].max()),
        "worst_day": str(pd.Timestamp(worst).date()),
        "days_over_tolerance": int((joined["rel_diff"] > TOLERANCE).sum()),
        "passed": bool(joined["rel_diff"].max() <= TOLERANCE),
        "frame": joined,
    }


def normalise_engine_orders(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["trade_date"] = out["trade_date"].astype(str).str.slice(0, 10)
    return out[["trade_date", "side", "shares", "price", "exit_reason"]].reset_index(drop=True)


def compare_orders(engine_orders: pd.DataFrame, hand_orders: pd.DataFrame) -> dict:
    """逐筆對:日期、方向、股數、成交價、出場原因。行數不同即當場報。"""
    left = normalise_engine_orders(engine_orders)
    right = hand_orders.copy().reset_index(drop=True)
    if len(left) != len(right):
        return {
            "matched": False,
            "reason": f"筆數不同:引擎 {len(left)} 筆,手算 {len(right)} 筆",
            "engine_rows": len(left),
            "hand_rows": len(right),
            "rows": [],
        }
    rows = []
    matched = True
    for position in range(len(left)):
        a, b = left.iloc[position], right.iloc[position]
        price_diff = abs(float(a["price"]) - float(b["price"]))
        share_diff = abs(float(a["shares"]) - float(b["shares"]))
        same = (
            a["trade_date"] == b["trade_date"]
            and a["side"] == b["side"]
            and price_diff <= TOLERANCE * max(1.0, abs(float(a["price"])))
            and share_diff <= TOLERANCE * max(1.0, abs(float(a["shares"])))
            and (a["exit_reason"] if pd.notna(a["exit_reason"]) else None)
            == (b["exit_reason"] if pd.notna(b["exit_reason"]) else None)
        )
        matched = matched and same
        rows.append(
            {
                "n": position + 1,
                "engine_date": a["trade_date"], "hand_date": b["trade_date"],
                "engine_side": a["side"], "hand_side": b["side"],
                "engine_shares": float(a["shares"]), "hand_shares": float(b["shares"]),
                "engine_price": float(a["price"]), "hand_price": float(b["price"]),
                "engine_reason": a["exit_reason"], "hand_reason": b["exit_reason"],
                "share_diff": share_diff, "price_diff": price_diff,
                "same": bool(same),
            }
        )
    return {"matched": bool(matched), "reason": "", "engine_rows": len(left),
            "hand_rows": len(right), "rows": rows}


# ----------------------------------------------------------------------
# 規則路徑
# ----------------------------------------------------------------------
def rule_case(
    name: str,
    bars: pd.DataFrame,
    *,
    breakout: int,
    swing: int,
    min_sf: float,
    max_sf: float,
    max_pos: float,
    risk: float,
    rr_floor: float,
    monthly_cap: float | None,
    cash: float,
) -> dict:
    frame = lambda column: pd.DataFrame({AAPL_ID: bars[column]})   # noqa: E731
    panel = BarPanel.from_frames(
        open=frame("Open"), high=frame("High"), low=frame("Low"), close=frame("Close")
    )
    params = RuleStrategyParams(
        entry=BreakoutEntry(lookback_days=breakout),
        stop=SwingLowStop(
            lookback_days=swing, min_stop_fraction=min_sf, max_stop_fraction=max_sf
        ),
        target=MeasuredMoveTarget(min_reward_risk=rr_floor),
        sizing=RiskFractionSizing(
            risk_per_trade=risk,
            max_position_fraction=max_pos,
            equity_basis="current_equity",
        ),
        breaker=None if monthly_cap is None else MonthlyLossBreaker(max_monthly_drawdown=monthly_cap),
        initial_cash=cash,
        fees=0.0,                       # D-030:基準情境不計交易成本
        tie_break_seed=20260828,
    )
    engine_result = run_rule_strategy(panel=panel, params=params)

    hand = hc.run_rule_handcalc(
        bars,
        hc.HandParams(
            breakout_lookback_days=breakout,
            swing_lookback_days=swing,
            min_stop_fraction=min_sf,
            max_stop_fraction=max_sf,
            max_position_fraction=max_pos,
            per_trade_risk=risk,
            reward_risk_floor=rr_floor,
            monthly_loss_cap=monthly_cap,
            initial_cash=cash,
        ),
    )

    equity = series_diff(engine_result.equity_curve, hand["equity"], "淨值")
    cash_cmp = series_diff(engine_result.cash, hand["cash"], "現金")
    basis_cmp = series_diff(engine_result.sizing_basis, hand["sizing_basis"], "注碼基數")
    blocked_engine = engine_result.breaker_blocked.astype(bool)
    blocked_hand = hand["blocked"].astype(bool)
    blocked_same = bool((blocked_engine.to_numpy() == blocked_hand.to_numpy()).all())
    orders = compare_orders(engine_result.orders_frame(), hand["orders"])

    equity["frame"].to_csv(HERE / f"diff-{name}-equity.csv", encoding="utf-8-sig")
    pd.DataFrame(orders["rows"]).to_csv(HERE / f"diff-{name}-orders.csv", index=False, encoding="utf-8-sig")
    hand["trades"].to_csv(HERE / f"trades-{name}-hand.csv", index=False, encoding="utf-8-sig")

    report = {
        "name": name,
        "path": "規則路徑",
        "bars": int(len(bars)),
        "period": [str(bars.index[0].date()), str(bars.index[-1].date())],
        "params": {
            "breakout_lookback_days": breakout, "swing_lookback_days": swing,
            "min_stop_fraction": min_sf, "max_stop_fraction": max_sf,
            "max_position_fraction": max_pos, "per_trade_risk": risk,
            "reward_risk_floor": rr_floor, "monthly_loss_cap": monthly_cap,
            "initial_cash": cash, "equity_basis": "current_equity", "fees": 0.0,
        },
        "engine": {
            "entry_signals": int(engine_result.entry_signals),
            "orders": int(len(engine_result.orders)),
            "blocked_days": int(engine_result.blocked_days),
            "final_equity": float(engine_result.equity_curve.iloc[-1]),
            "total_return": float(engine_result.total_return),
        },
        "hand": {
            "entry_signals": int(hand["entry_signals"]),
            "orders": int(len(hand["orders"])),
            "blocked_days": int(hand["blocked"].sum()),
            "final_equity": float(hand["equity"].iloc[-1]),
            "trades": int(len(hand["trades"])),
        },
        "equity": {k: v for k, v in equity.items() if k != "frame"},
        "cash": {k: v for k, v in cash_cmp.items() if k != "frame"},
        "sizing_basis": {k: v for k, v in basis_cmp.items() if k != "frame"},
        "breaker_matches": blocked_same,
        "orders_match": orders["matched"],
        "orders_note": orders["reason"],
        "exit_reasons_hand": hand["trades"]["exit_reason"].value_counts().to_dict()
        if len(hand["trades"]) else {},
    }
    report["passed"] = bool(
        equity["passed"] and cash_cmp["passed"] and basis_cmp["passed"]
        and blocked_same and orders["matched"]
    )
    return report


# ----------------------------------------------------------------------
# 排名路徑(adapter A)
# ----------------------------------------------------------------------
def ranking_case(name: str, spy: pd.DataFrame, qqq: pd.DataFrame, cash: float) -> dict:
    opens = pd.DataFrame({SPY_ID: spy["Open"], QQQ_ID: qqq["Open"]}).dropna()
    closes = pd.DataFrame({SPY_ID: spy["Close"], QQQ_ID: qqq["Close"]}).loc[opens.index]
    panel = PricePanel.from_frames(open=opens, close=closes)

    # 節奏:手算自己排一次月度換倉表,再與引擎的排期核對。兩邊排得一樣,
    # 才把同一張目標比重表餵落引擎——這樣對照對的是資金那一層,不是排期。
    execution_bars = hc.monthly_execution_bars(opens.index)
    engine_schedule = rebalance_schedule(panel.dates, "monthly")
    engine_execution = [list(panel.dates).index(execution) for _, execution in engine_schedule]
    schedule_same = bool(execution_bars == engine_execution)

    targets = pd.DataFrame(np.nan, index=opens.index, columns=list(opens.columns), dtype=float)
    for position in execution_bars:
        targets.iloc[position, :] = 0.5          # 兩隻等權

    params = RankingRebalanceParams(
        cadence="monthly", top_n=2, direction="high", initial_cash=cash, fees=0.0
    )
    from karst.engine.vectorbt_engine import VectorbtEngine

    output = VectorbtEngine().simulate(panel, targets, params)
    hand = hc.run_ranking_handcalc(opens, closes, execution_bars, cash)

    equity = series_diff(output.equity_curve, hand["equity"], "淨值")
    holdings_diff = float(
        (output.holdings.astype(float) - hand["holdings"].astype(float)).abs().to_numpy().max()
    )
    engine_orders = pd.DataFrame(
        [
            {"trade_date": str(o.trade_date)[:10], "entity_id": int(o.entity_id),
             "side": o.side, "shares": float(o.shares), "price": float(o.price)}
            for o in output.orders
        ],
        columns=["trade_date", "entity_id", "side", "shares", "price"],
    )
    equity["frame"].to_csv(HERE / f"diff-{name}-equity.csv", encoding="utf-8-sig")
    engine_orders.to_csv(HERE / f"orders-{name}-engine.csv", index=False, encoding="utf-8-sig")
    hand["orders"].to_csv(HERE / f"orders-{name}-hand.csv", index=False, encoding="utf-8-sig")

    orders_same = len(engine_orders) == len(hand["orders"])
    order_price_diff = 0.0
    order_share_diff = 0.0
    if orders_same and len(engine_orders):
        left = engine_orders.sort_values(["trade_date", "entity_id"]).reset_index(drop=True)
        right = hand["orders"].sort_values(["trade_date", "entity_id"]).reset_index(drop=True)
        orders_same = bool(
            (left["trade_date"] == right["trade_date"]).all()
            and (left["entity_id"] == right["entity_id"]).all()
            and (left["side"] == right["side"]).all()
        )
        order_price_diff = float((left["price"] - right["price"]).abs().max())
        order_share_diff = float((left["shares"] - right["shares"]).abs().max())
        orders_same = orders_same and order_share_diff <= 1e-6 and order_price_diff <= 1e-9

    report = {
        "name": name,
        "path": "排名路徑(adapter A)",
        "bars": int(len(opens)),
        "period": [str(opens.index[0].date()), str(opens.index[-1].date())],
        "params": {"cadence": "monthly", "top_n": 2, "direction": "high",
                   "initial_cash": cash, "fees": 0.0, "weights": "等權 1/2"},
        "rebalances": len(execution_bars),
        "execution_dates": [str(opens.index[p].date()) for p in execution_bars],
        "schedule_matches_engine": schedule_same,
        "engine": {"final_equity": float(output.equity_curve.iloc[-1]),
                   "orders": int(len(output.orders))},
        "hand": {"final_equity": float(hand["equity"].iloc[-1]),
                 "orders": int(len(hand["orders"]))},
        "equity": {k: v for k, v in equity.items() if k != "frame"},
        "max_holdings_diff": holdings_diff,
        "orders_match": bool(orders_same),
        "max_order_price_diff": order_price_diff,
        "max_order_share_diff": order_share_diff,
    }
    report["passed"] = bool(
        equity["passed"] and schedule_same and orders_same and holdings_diff <= 1e-6
    )
    return report


def main() -> None:
    aapl_full = hc.load_bars(HERE / "AAPL.csv")
    aapl_window = aapl_full.loc["2023-01-03":"2023-03-31"]
    spy_full = hc.load_bars(HERE / "SPY.csv")
    qqq_full = hc.load_bars(HERE / "QQQ.csv")

    reports = []

    # 示例參數(experiments/2026-08-28-trend-swing-real/run_backtest.py)原封不動
    sample = dict(breakout=50, swing=10, min_sf=0.01, max_sf=0.25, max_pos=0.25,
                  risk=0.02, rr_floor=1.5, monthly_cap=0.06, cash=1_000_000.0)

    reports.append(rule_case("rule-A-票面窗口", aapl_window, **sample))
    reports.append(rule_case("rule-B-含暖身", aapl_full, **sample))

    # 壓力格:短回望令票面那三個月之內真的開得成倉,出場原因才有得對
    stress = dict(sample, breakout=20, swing=5, rr_floor=1.0)
    reports.append(rule_case("rule-C-短回望", aapl_window, **stress))
    reports.append(rule_case("rule-D-短回望無熔斷", aapl_window, **dict(stress, monthly_cap=None)))
    reports.append(rule_case("rule-E-熔斷收緊", aapl_window, **dict(stress, monthly_cap=0.005)))
    reports.append(rule_case("rule-F-短回望含暖身", aapl_full, **stress))

    # 逼出「目標跳空以開價成交」那一格:回望極短,目標貼近,隔晚跳空直接越過。
    # 前面幾格已經行到止蝕跳空,這一格補上目標那一邊。
    gap = dict(sample, breakout=5, swing=3, rr_floor=0.3, min_sf=0.01)
    reports.append(rule_case("rule-G-跳空目標", aapl_full, **gap))

    reports.append(ranking_case("rank-A-票面窗口",
                                spy_full.loc["2023-01-03":"2023-03-31"],
                                qqq_full.loc["2023-01-03":"2023-03-31"], 100_000.0))
    reports.append(ranking_case("rank-B-延長", spy_full, qqq_full, 100_000.0))

    for report in reports:
        mark = "通過" if report["passed"] else "有差異"
        line = (f"[{mark}] {report['name']} ({report['path']}) "
                f"{report['period'][0]}~{report['period'][1]} {report['bars']} 根;"
                f"淨值最大相對差 {report['equity']['max_rel_diff']:.3e}")
        if report["path"] == "規則路徑":
            line += (f";訊號 引擎{report['engine']['entry_signals']}/手算{report['hand']['entry_signals']}"
                     f";成交 引擎{report['engine']['orders']}/手算{report['hand']['orders']}"
                     f";熔斷日 引擎{report['engine']['blocked_days']}/手算{report['hand']['blocked_days']}"
                     f";逐筆{'對得上' if report['orders_match'] else '對不上 ' + report['orders_note']}")
        else:
            line += (f";換倉 {report['rebalances']} 次"
                     f";逐筆{'對得上' if report['orders_match'] else '對不上'}")
        print(line)

    summary = {
        "ticket": "KARST-059",
        "tolerance": TOLERANCE,
        "tolerance_note": "相對誤差;淨值百萬量級,絕對 1e-9 等於考浮點次序而非回測邏輯",
        "data": {
            "source": "yfinance auto_adjust=True",
            "files": ["AAPL.csv", "SPY.csv", "QQQ.csv"],
            "note": "只住實驗目錄;不入定義庫、不寫 data/、不碰 karst.sqlite",
        },
        "all_passed": all(r["passed"] for r in reports),
        "cases": reports,
    }
    (HERE / "results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"\n全部通過:{summary['all_passed']};明細已落 results.json")


if __name__ == "__main__":
    main()
