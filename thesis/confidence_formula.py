# -*- coding: utf-8 -*-
"""confidence 公式(純函數)—— thesis/DESIGN.md §4a 凍結公式的唯一實作。

供 thesis/lint.py 嘅公式檢查、同未來 sizing v2 共用。原則(§4a 開場語):
「判斷放設計時,算術放執行時」—— 呢個模組只做「套公式」呢步,penalty 查表逐格
照 DESIGN.md §4a 抄,唔准呢個模組自己發明或調整數字(改表 = 季度設計審查,唔係
改呢份 code)。

公式(DESIGN §4a,凍結;2026-07-15 補 source-cap;2026-07-16 補 uncalibrated ceiling):
    confidence_raw = (Σ 4-KPI subscores) / 8 × penalty(crowding_band, cycle_stage)
    confidence     = min(confidence_raw, *適用嘅 cap)
    subscore ∈ {0, 0.5, 1, 1.5, 2}(每格 0-2,半分步進)

兩個 cap,**同時適用取最緊**(唔係二選一):
    SINGLE_SOURCE_CAP = 0.30   當 len(sources) == 1(§4a「獨立來源」定義)
    UNCALIBRATED_CAP  = 0.40   當校準迴路未通(STATUS.md:256 衛星紀律)

**UNCALIBRATED_CAP 嘅由來(2026-07-16,誠實記低點解會漏)**:§4a 公式當初由零寫起,冇審計
散落喺其他檔嘅既有治理規則,結果漏規則兩次——
  1. single-source cap 0.30(WS3 admission,lint 一直 warn 緊)→ 2026-07-15 補
  2. **≤0.40 未校準上限**(STATUS.md:256「衛星紀律:校準迴路未通之前,Phase-3 注碼 ≤20%、
     confidence 上限 ≤0.40」)→ 2026-07-16 補。漏咗嘅後果:ai-power-grid / euv 合法脫咗
     single-source cap 之後,公式輸出 0.469,**冇任何嘢攔住**,兩個都越咗界。
兩次都係同一類 bug:**規則寫咗喺 doc,但公式冇 encode → 可以靜靜越界**。
教訓 = 公式必須 encode 晒所有已寫低嘅硬規則,唔可以靠人記得。

**呢個 cap 唔係酌情,係規則**:cap 嘅前提「校準迴路未通」有客觀判準——
`thesis/forward_ic.py ic` 嘅 matured predictions 數。2026-07-16 實測 matured=0
(pending=613),即係裁判一個讀數都未出過 → 前提成立 → cap 生效。
機器起咗 ≠ 迴路通咗;要 forward IC 真係出到讀數先算。

純函數、無 IO、無副作用 —— 可獨立 import 測試。
"""

# --- caps(DESIGN §4a;每個 cap 都要有 doc 出處,唔准無主 magic number)---
SINGLE_SOURCE_CAP = 0.30   # §4a「獨立來源」定義:單一來源 thesis 嘅注碼上限
UNCALIBRATED_CAP = 0.40    # STATUS.md:256 衛星紀律:校準迴路未通之前 confidence 上限

# penalty 查表(DESIGN.md §4a「penalty 查表」,5×3,凍結,逐格照抄):
#   crowding \ cycle | early | mid / event-driven | late / mid-late
#   ---------------- | ----- | ------------------- | ----------------
#   < 40(冷)         | 1.00  | 0.90                | 0.75
#   40-60             | 0.95  | 0.85                | 0.65
#   60-80             | 0.85  | 0.75                | 0.55
#   80-90             | 0.75  | 0.65                | 0.45
#   >= 90(極擠)      | 0.65  | 0.55                | 0.40
_PENALTY_TABLE = {
    "<40":   {"early": 1.00, "mid": 0.90, "late": 0.75},
    "40-60": {"early": 0.95, "mid": 0.85, "late": 0.65},
    "60-80": {"early": 0.85, "mid": 0.75, "late": 0.55},
    "80-90": {"early": 0.75, "mid": 0.65, "late": 0.45},
    ">=90":  {"early": 0.65, "mid": 0.55, "late": 0.40},
}

# DESIGN §4a 表頭寫「mid / event-driven」同「late / mid-late」係同一欄——theme-level
# cycle_stage(thesis/lint.py VALID_CYCLE_STAGES = early/mid/late/event-driven)以外,
# node-level 偶有 "mid-late"(例:memory-supercycle 的 hdd-nearline-storage node)出現,
# 呢度一併映射,唔會因為多咗個 node-level 字串就炸。
_CYCLE_COLUMN = {
    "early": "early",
    "mid": "mid",
    "event-driven": "mid",
    "late": "late",
    "mid-late": "late",
}

REQUIRED_KPIS = ("moat", "capital", "valuation", "growth")


def _crowding_band(crowding_pctile):
    """crowding percentile(0-100)-> DESIGN §4a 五帶之一(對應 _PENALTY_TABLE 嘅 key)。
    邊界依表面文字("< 40" / "40-60" / ... / ">= 90")做左閉右開分段:
    40 落入 "40-60" 帶(唔係 "<40"),90 落入 ">=90" 帶(唔係 "80-90")。
    """
    c = float(crowding_pctile)
    if c < 40:
        return "<40"
    if c < 60:
        return "40-60"
    if c < 80:
        return "60-80"
    if c < 90:
        return "80-90"
    return ">=90"


def penalty(crowding_pctile, cycle_stage):
    """DESIGN §4a 5x3 查表(crowding pctile 五帶 x cycle 三欄)。逐格照抄,唔准發明。

    crowding_pctile: 0-100 嘅擁擠複合分位(thesis/.raw/crowding_composite.json 嘅
        composite_pctile)。
    cycle_stage: theme-level 四值之一(early/mid/event-driven/late),或 node-level
        額外見過嘅 mid-late(視為同 late 同欄,見 _CYCLE_COLUMN)。

    Raises ValueError if cycle_stage 唔喺已知集合(例如 typo)—— 唔靜默估值。
    """
    band = _crowding_band(crowding_pctile)
    col = _CYCLE_COLUMN.get(str(cycle_stage))
    if col is None:
        raise ValueError(
            f"cycle_stage {cycle_stage!r} not recognised "
            f"(expected one of {sorted(_CYCLE_COLUMN)})"
        )
    return _PENALTY_TABLE[band][col]


def confidence(subscores, crowding_pctile, cycle_stage, n_sources, calibrated=False):
    """DESIGN §4a 凍結公式的完整計算(含兩個 cap)。

    subscores: dict,必須含 {moat, capital, valuation, growth} 四鍵,各 0-2
        (半分步進,例如 1.5)。
    crowding_pctile: 0-100(見 penalty() 的說明)。
    cycle_stage: 見 penalty() 的說明。
    n_sources: len(themes.yaml 該 theme 的 `sources:` list)。
    calibrated: 校準迴路通咗未(預設 False = 現況)。判準唔係「機器起咗未」,
        而係 `thesis/forward_ic.py ic` 有冇 matured predictions —— 2026-07-16
        實測 matured=0,所以現行全系統一律 False。**唔准淨係因為 code 存在
        就傳 True**;要 forward IC 真係出到讀數先算通(見模組 docstring)。

    回傳 {"raw", "capped", "cap_applied", "caps_binding"}:
        caps_binding = 實際綁住嗰(啲)cap 嘅名,方便 lint / 報告講清楚
        邊條規則喺度發功(空 list = 冇 cap 綁,capped == raw)。
        cap_applied 保留做向後兼容(= 有冇任何 cap 綁住)。

    single-source cap 觸發條件依 §4a 原文字面(`len(sources) == 1`)。呢度用 `<= 1`
    (保守擴展,涵蓋 0-source 嘅退化情況;0-source theme 本身已被 lint.py 嘅
    admission gate("sources empty")擋,實務唔會出現,呢度純粹防禦性寫法,
    唔改變任何現行合規 theme 的計算結果)。

    **兩個 cap 同時適用時取最緊**(min),唔係二選一 —— 例:單一來源 + 未校準
    → min(raw, 0.30, 0.40) = min(raw, 0.30)。
    """
    missing = [k for k in REQUIRED_KPIS if k not in subscores]
    if missing:
        raise ValueError(f"subscores missing required keys: {missing}")

    total = sum(float(subscores[k]) for k in REQUIRED_KPIS)
    raw = total / 8.0 * penalty(crowding_pctile, cycle_stage)

    caps = []
    if int(n_sources) <= 1:
        caps.append(("single_source", SINGLE_SOURCE_CAP))
    if not calibrated:
        caps.append(("uncalibrated", UNCALIBRATED_CAP))

    capped = raw
    caps_binding = []
    for name, cap_value in caps:
        if cap_value < capped:
            capped = cap_value
    # 邊條 cap 真係綁住(= 佢個值等於最終 capped 而且低過 raw)—— 可能兩條同時等值
    caps_binding = [name for name, cap_value in caps
                    if capped < raw and cap_value == capped]

    return {"raw": raw, "capped": capped,
            "cap_applied": bool(caps_binding), "caps_binding": caps_binding}


if __name__ == "__main__":
    # 手動快速自測(非 pytest;py_compile + 呢段跑得過 = 基本健全)。
    demo = confidence(
        {"moat": 1.5, "capital": 1, "valuation": 1, "growth": 1.5},
        crowding_pctile=24.8,
        cycle_stage="late",
        n_sources=1,
    )
    print(demo)
