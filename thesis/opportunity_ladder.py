"""thesis/opportunity_ladder.py — 機會階梯檔位判定 + A/B/C/D 雷達燈(read-only,唔落單)

動機(docs/2026-07-12_opportunity_ladder.md 一直只係設計文件,冇實作;dashboard v4
`docs/2026-07-13_dashboard_v4_portable.md` ROW 0 / ROW 0.5 兩格依賴呢個模組嘅輸出,
之前顯示「未接線」——見 thesis/dashboard_render.py 的 BACKLOG_NOTE)。

規則來源(全部照抄以下兩份設計文件,唔自創規則):
  - 主文件 = docs/2026-07-12_opportunity_ladder.md(檔位三分法 + 撞期優先序)
  - 候選文件 = docs/2026-07-12_new_sleeve_candidates.md(A/B/C/D 四個候選嘅原始定義,
    主文件開首第 3 行明講「承接」呢份)

凡文件冇講清楚嘅位,下面用「【文件未定義,採用保守解讀】」標明,唔靜雞雞自己發明規則
(呢個係使用者對本次任務嘅明確要求)。

輸出:thesis/.raw/opportunity_ladder.json
用法:
    python thesis/opportunity_ladder.py --verbose
    python thesis/opportunity_ladder.py --vix-override 90 --verbose --out-path thesis/.raw/_test.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))            # thesis/
REPO_ROOT = os.path.dirname(ROOT)                              # Karst/
sys.path.insert(0, REPO_ROOT)
from backtest.data import load  # noqa: E402  (yfinance-first price loader, 參考 thesis/beta_check.py 用法)

OUT_PATH = os.path.join(ROOT, ".raw", "opportunity_ladder.json")

# ============================================================================
# 檔位門檻常數 —— 逐個數字對應主文件邊一行
# ============================================================================

# 主文件 line 30:「平靜市(VIX<20,趨勢向上)——「日常獵季」」
CALM_VIX_MAX = 20.0

# 主文件 line 36:「調整市(washout 亮燈,VIX 25-35,長期趨勢未破)——「快手窗」」
ADJUST_VIX_LO = 25.0
ADJUST_VIX_HI = 35.0

# 主文件 line 43:「危機市(VIX>40 → ARM;回落<30 → ENTER)——「十年一遇窗」」。
# 呢兩個數同 backtest/playbook_readout.py 現成嘅 CRISIS_ARM_VIX / CRISIS_ENTER_VIX 完全一致
# (WS2 crisis-rescue 現成規則;主文件危機市 point1 本身都寫「ENTER 右側訊號照現成引擎規則
# 入」),所以呢度直接復用嗰套 ARM/ENTER hysteresis 邏輯,唔重新發明一套。
CRISIS_ARM_VIX = 40.0
CRISIS_ENTER_VIX = 30.0
CRISIS_ARM_WINDOW_TD = 60      # 同 playbook_readout.py 一致:trailing 60 個交易日內有冇 breach

# washout proxy 門檻 —— 主文件淨係講「washout 亮燈」呢個狀態名(line 36),冇俾實際計算式。
# 真正已回測嘅 washout 定義住喺另一份研究(backtest/results/2026-07-05_phase2_flow.md
# addendum + exp_breadth_reversion.py):市場 breadth(%股票喺自己 50SMA 之上)跌穿底 decile
# (實測 ≈ ≤27%)。嗰個定義要全市場 breadth 數據(大批股票收市價 pickle 快取),唔喺本次任務
# 畀嘅「現成數據源」清單入面(清單只列 VIX/SPY)。
# 【文件未定義,採用保守解讀】按使用者指示的 fallback:SPY 距 52 週(252 交易日)高位回撤 %
# 做 washout proxy。門檻本身文件都冇講——呢度採用傳統「correction」門檻(回撤 ≥10%)當
# 「washout 亮燈」:比日常小回調保守(唔會日日閃燈),又比危機門檻(VIX>40)寬鬆,同主文件
# 調整市 VIX 25-35 嗰個「未到危機但唔平靜」嘅語意大致對齊。呢個係 PROXY,唔係已回測驗證嘅
# 原始 breadth 訊號——如果第日要接返真 breadth washout,呢個門檻同計算式應該整個換走。
WASHOUT_DRAWDOWN_PCT = 10.0
WASHOUT_LOOKBACK_TD = 252

# 主文件「一條凌駕規則」段(line 62-65)嘅建議值——文件自己講明「具體數等 BT-2 + A 回測返嚟
# 先釘」,即呢啲數字係 PROVISIONAL,唔係定案。
BUDGET_SUGGESTED_PCT_NAV = {"平靜市": 5.0, "調整市": 10.0, "危機市": 20.0}


# ============================================================================
# 訊號計算
# ============================================================================

def crisis_state(vix_series, vix_override=None):
    """復用 backtest/playbook_readout.py crisis_sleeve_line() 嘅 ARM/ENTER/DISARMED 判斷
    (同一門檻、同一 60 個交易日 trailing window),但只回傳狀態,唔做 sector targeting——
    嗰個係執行細節,唔喺呢個 read-only 檔位雷達嘅範圍。"""
    vix = vix_series.copy()
    if vix_override is not None:
        vix.iloc[-1] = float(vix_override)   # 測試用:假裝今日 VIX 收市 = override 值
    vix_now = float(vix.iloc[-1])
    window = vix.tail(CRISIS_ARM_WINDOW_TD)
    breach = window[window > CRISIS_ARM_VIX]
    if breach.empty:
        return "DISARMED", vix_now, None
    arm_date = breach.index[0]   # 同 playbook_readout.py 一致:ARM 由 window 內第一次 breach 起計
    state = "ENTER-SIGNAL" if vix_now < CRISIS_ENTER_VIX else "ARMED"
    return state, vix_now, arm_date


def compute_trend_gate(spy_close, override=None):
    """趨勢閘 = SPY 收市 vs 200SMA(同 backtest/playbook_readout.py 嘅 LEAP gate 定義一致)。
    【文件未定義,採用保守解讀】主文件講「趨勢向上」/「長期趨勢未破」冇話明係唔係just呢個
    200SMA gate,定係要睇 200SMA 斜率之類更嚴格嘅嘢。呢度沿用系統其他地方(playbook_readout.py
    嘅 LEAP gate)一致嘅定義,保持同一套「趨勢」語意,唔另起爐灶。"""
    sma200 = spy_close.rolling(200).mean()
    last = float(spy_close.iloc[-1])
    last_sma = float(sma200.iloc[-1])
    pct = (last / last_sma - 1.0) * 100.0
    gate_on = last > last_sma
    if override is not None:
        gate_on = bool(override)
    return gate_on, pct


def compute_washout(spy_close, override=None):
    if override is not None:
        return bool(override), None
    window = spy_close.tail(WASHOUT_LOOKBACK_TD)
    high = float(window.max())
    last = float(spy_close.iloc[-1])
    drawdown_pct = (last / high - 1.0) * 100.0   # 負數
    lit = drawdown_pct <= -WASHOUT_DRAWDOWN_PCT
    return lit, drawdown_pct


def classify_tier(vix_now, crisis_state_str, trend_gate_on, washout_lit):
    """三檔判定,優先序 = 危機 > 調整 > 平靜。

    危機凌駕一切:主文件危機市一節本身就係一組凌駕規則(A 暫停新倉、B 唔加大、C-core 做
    主力),同「撞期優先序」呼應。

    【文件未定義,採用保守解讀】主文件三個小節嘅門檻之間有幾段罅隙冇覆蓋:
      - VIX 20-25(平靜市門檻 <20,調整市門檻 25-35,中間漏咗一段)
      - VIX 35-40 但未觸發危機 ARM(調整市門檻上限 35,危機門檻要 >40)
      - washout 冇亮燈但 VIX 已經 >=20(調整市文字要求「washout 亮燈」先算)
      - trend 已破(gate OFF)但未觸發 VIX>40 ARM 嘅慢熊市情況(文件三檔都冇講呢種組合)
    呢度嘅保守解讀:呢啲罅隙一律唔當「平靜市」處理(平靜市門檻寫死 VIX<20 且趨勢向上,
    一步都唔讓),寧可預設落去「調整市」——調整市本質上就係「唔平靜又未到危機」嘅中間檔,
    寧緊唔寬,防止市況剛轉差嗰陣 dashboard 仍然掛住「平靜市」誤導使用者。
    """
    if crisis_state_str in ("ARMED", "ENTER-SIGNAL"):
        return "危機市"
    if not trend_gate_on:
        # trend 已破但未觸發 VIX>40 ARM —— 主文件冇呢個組合,保守落去調整市(見上面 docstring)
        return "調整市"
    if vix_now < CALM_VIX_MAX and not washout_lit:
        return "平靜市"
    # 主文件字面「調整市」定義(washout 亮燈 + VIX 25-35)+ 上面列出嘅全部罅隙情況,
    # 一律歸類做調整市。
    return "調整市"


# ============================================================================
# A/B/C/D 四個雷達
# ============================================================================

def radar_a():
    # 候選文件 §候選A「Karst 點驗證」四步(事件庫 / transcript 過性-結構過濾器 /
    # insider 確認訊號 / 判官)一步都未做;主文件「Backtest 先至郁」表格 A 欄寫明
    # 「完整 backtest 必須...冇藉口跳過」,即係「未做」而唔係「唔使做」。
    # 使用者指示:事件庫未起 -> not_wired,誠實標示,唔准造數——原封不動跟。
    return {
        "status": "not_wired",
        "note": ("事件庫未起(候選文件 candidate-A『Karst點驗證』1-4 步未動工;"
                 "主文件『Backtest 先至郁』表格 A 欄:①裝雷達=事件掃描器=平,"
                 "但③真錢閘要完整 backtest,尚未立項)"),
    }


def radar_b(washout_lit, drawdown_pct, tier):
    # 主文件對 B 喺唔同檔位嘅動作原句(逐檔對應主文件邊一行):
    #   平靜市 line 33 point3:「B/C 雷達待機,零動作」
    #   調整市 line 37 point1:「B 先行(訊號最證實、時窗最短:21-42 日,固定 2-3% NAV
    #                            premium,機械離場)」
    #   危機市 line 56 point3:「B 照計但唔加大(佢嘅 edge 係反彈頭三週,固定注碼照舊)」
    action_by_tier = {
        "平靜市": "待機,零動作",
        "調整市": "先行(21-42日,固定2-3% NAV premium,機械離場)",
        "危機市": "照計但唔加大(反彈頭三週,固定注碼)",
    }
    return {
        "lit": bool(washout_lit),
        "spy_drawdown_from_52w_high_pct": None if drawdown_pct is None else round(drawdown_pct, 2),
        "washout_threshold_pct": -WASHOUT_DRAWDOWN_PCT,
        "tier_action": action_by_tier.get(tier, "未定義檔位(不應發生)"),
        "note": ("washout = proxy(SPY 52週高回撤 >= "
                 f"{WASHOUT_DRAWDOWN_PCT:.0f}%);主文件冇俾原始 breadth 計算式,"
                 "見檔頭常數區塊註解"),
    }


def radar_c(crisis_state_str, vix_now, arm_date):
    # 主文件危機市 point1(line 50):「C-core(危機預算 70-80%)= SPY/QQQ LEAP,ENTER 右側
    # 訊號照現成引擎規則入」——「現成引擎規則」= backtest/playbook_readout.py 嘅 crisis
    # ARM/ENTER(docs/2026-07-08_phase3_ws2_crisis.md),上面 crisis_state() 已直接復用。
    # C-list(高門檻配角,主文件危機市 point2,line 52-55)要 expectations-gap 嘅
    # P_base>1.0 讀數 + solvency gate,呢兩個模組唔喺本次任務畀嘅現成數據源清單入面
    # -> 誠實標 not_wired,同 A/D 一致做法(唔擴大範圍自己去接)。
    return {
        "state": crisis_state_str,          # DISARMED / ARMED / ENTER-SIGNAL
        "vix": round(vix_now, 2),
        "arm_vix_threshold": CRISIS_ARM_VIX,
        "enter_vix_threshold": CRISIS_ENTER_VIX,
        "armed_since": arm_date.date().isoformat() if arm_date is not None else None,
        "note": "C-core:復用 backtest/playbook_readout.py 嘅 crisis ARM/ENTER(WS2 現成引擎)",
        "c_list": {
            "status": "not_wired",
            "note": ("高門檻配角(P_base>1.0 + solvency gate,主文件危機市 point2)未接"
                     "expectations-gap 模組讀數,唔喺本次任務嘅現成數據源清單內"),
        },
    }


def radar_d():
    # 候選文件 §候選D + 主文件「Backtest 先至郁」表格 D 欄:管道(UBS Memory/TWSE)已開頭,
    # 但「逐主題 spot-check」——DRAM 合約價喺 MU 2016/2023 兩輪拐點校對——未做;
    # 表格原句:「每條序列性質唔同,冇得一鑊熟」,即依然逐條驗先信,唔可以跳。
    return {
        "status": "not_wired",
        "note": ("DRAM 合約價序列未 spot-check(主文件表格 D 欄:『每條序列性質唔同,"
                 "冇得一鑊熟』;MU 2016/2023 兩輪拐點校對未做)"),
    }


def monthly_budget_note(tier):
    # 主文件「一條凌駕規則」段(line 62-65):「平靜月 5% NAV / 調整月 10% / 危機月 20%,
    # 具體數等 BT-2 + A 回測返嚟先釘」——即呢啲數字係建議值,文件自己都話未定案。
    # 「已用」百分比要一個 position ledger(已部署幾多 NAV)嗰類數據源,唔喺任務畀嘅
    # 現成數據源清單入面(清單只列 VIX/SPY)-> not_wired,唔擬造數字。
    return {
        "tier": tier,
        "suggested_cap_pct_nav": BUDGET_SUGGESTED_PCT_NAV.get(tier),
        "status": "provisional(主文件:『具體數等 BT-2 + A 回測返嚟先釘』,未定案)",
        "used_pct_nav": {
            "status": "not_wired",
            "note": "需要 position ledger 數據源,呢次任務畀嘅現成數據源清單未包含",
        },
    }


# ============================================================================
# 組裝 + 主流程
# ============================================================================

def build_report(vix_override=None, washout_override=None, trend_gate_override=None):
    spy = load("SPY")["close"]
    vix_series = load("^VIX")["close"]

    crisis_state_str, vix_now, arm_date = crisis_state(vix_series, vix_override)
    trend_gate_on, spy_vs_200sma_pct = compute_trend_gate(spy, trend_gate_override)
    washout_lit, drawdown_pct = compute_washout(spy, washout_override)

    tier = classify_tier(vix_now, crisis_state_str, trend_gate_on, washout_lit)

    radar = {
        "A": radar_a(),
        "B": radar_b(washout_lit, drawdown_pct, tier),
        "C": radar_c(crisis_state_str, vix_now, arm_date),
        "D": radar_d(),
    }

    overrides_used = {}
    if vix_override is not None:
        overrides_used["vix_override"] = vix_override
    if washout_override is not None:
        overrides_used["washout_override"] = washout_override
    if trend_gate_override is not None:
        overrides_used["trend_gate_override"] = trend_gate_override

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tier": tier,
        "tier_inputs": {
            "vix": round(vix_now, 2),
            "spy_vs_200sma_pct": round(spy_vs_200sma_pct, 2),
            "trend_gate": "ON" if trend_gate_on else "OFF",
            "washout": bool(washout_lit),
            "spy_drawdown_from_52w_high_pct": None if drawdown_pct is None else round(drawdown_pct, 2),
            "crisis_state": crisis_state_str,
        },
        "radar": radar,
        "monthly_budget_note": monthly_budget_note(tier),
        "test_overrides_applied": overrides_used or None,
    }
    return report


def main():
    ap = argparse.ArgumentParser(
        description="Karst 機會階梯檔位判定 + A/B/C/D 雷達燈(read-only,唔落單)。")
    ap.add_argument("--verbose", action="store_true", help="印出檔位 + 四個雷達狀態")
    ap.add_argument("--vix-override", type=float, default=None,
                     help="測試用:假裝今日 VIX 收市 = 呢個值(例:--vix-override 90 驗證危機檔)")
    ap.add_argument("--washout-override", choices=["on", "off"], default=None,
                     help="測試用:強制 washout 亮燈狀態,跳過真實回撤計算")
    ap.add_argument("--trend-gate-override", choices=["on", "off"], default=None,
                     help="測試用:強制趨勢閘 ON/OFF,跳過真實 200SMA 比較")
    ap.add_argument("--out-path", default=OUT_PATH, help="輸出 json 路徑(測試時可指向別處,唔覆蓋正式檔)")
    args = ap.parse_args()

    washout_override = None if args.washout_override is None else (args.washout_override == "on")
    trend_gate_override = None if args.trend_gate_override is None else (args.trend_gate_override == "on")

    report = build_report(vix_override=args.vix_override,
                           washout_override=washout_override,
                           trend_gate_override=trend_gate_override)

    out_dir = os.path.dirname(args.out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    if args.verbose:
        ti = report["tier_inputs"]
        print(f"==== opportunity_ladder {report['generated_at']} ====")
        print(f"檔位: {report['tier']}")
        print(f"  VIX={ti['vix']}  SPY vs 200SMA={ti['spy_vs_200sma_pct']:+.2f}%"
              f"(gate {ti['trend_gate']})  washout={ti['washout']}"
              f"(SPY52週高回撤={ti['spy_drawdown_from_52w_high_pct']}%)"
              f"  crisis_state={ti['crisis_state']}")
        for k in ["A", "B", "C", "D"]:
            r = report["radar"][k]
            if "status" in r:
                print(f"  雷達{k}: {r['status']} — {r['note']}")
            else:
                summary = {kk: vv for kk, vv in r.items() if kk not in ("note", "c_list")}
                print(f"  雷達{k}: {summary}")
        mb = report["monthly_budget_note"]
        print(f"月機會預算: {mb['tier']} 建議上限 {mb['suggested_cap_pct_nav']}% NAV"
              f"({mb['status']});已用={mb['used_pct_nav']['status']}")
        if report["test_overrides_applied"]:
            print(f"(已套用測試 override: {report['test_overrides_applied']})")
    print(f"opportunity_ladder: tier={report['tier']} -> wrote {args.out_path}")


if __name__ == "__main__":
    main()
