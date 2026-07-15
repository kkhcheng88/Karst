# 框架可量化度審查:更好嘅評分/刻度,令平模型都執行到【2026-07-15】

> **觸發**:用戶指令「make the system more quantifiable with better scoring and scale,
> help stock selection and entry/exit, especially when execution is under cheaper model」,
> 參考 TradingKey 個股分析頁(6 維度、34 指標、統一 10 分制、綜合分+peer 對比+支撐阻力)。
> **本檔 = 現狀盤點 + 差距分析 + 五個按價值排序嘅提案。全部提案跟返 repo 鐵律:
> display-first,未經回測唔接 sizing。**

---

## 0. 核心設計原則(成份檔嘅一句版)

**判斷放喺設計時(貴模型、季度),算術放喺執行時(平模型、每日)。**
平模型執行退化嘅唔係算術,係 judgment。所以量化嘅目標唔係「消滅判斷」,
係**把判斷凍結成 rubric/公式/查表**,令夜班平模型淨係做三件事:計數、對表、
發現對唔上就掉入 review queue(唔係自己作判斷)。呢個同現有裁判/夜班架構一致。

---

## 1. 現狀盤點:邊啲已經係機械、邊啲仲靠判斷

### 1a. 已機械化(平模型安全)✅

| 讀數 | 邊度計 | 性質 |
|---|---|---|
| tier-2 card score | `spine/expression.py:66` | `100 × mcap_gate × trend(0/1) × sector_warm × confidence` |
| pe_pctile / vs_200sma / w52_pos | `thesis/theme_signal.py` | 自身歷史分位 + 趨勢,全公式 |
| verdict 狀態機 | `theme_signal.py:257` | KILL-WATCH/BUY-ZONE/ACCUMULATE/WAIT,機械規則 |
| P_base@14x / g_implied | `thesis/valuation.py`(週) | Mauboussin 公式 |
| crowding composite pctile | `thesis/crowding_composite.py`(週) | 公式 |
| insider 佐證 | `spine/providers.py:86` | bounded ±30% nudge,公式 |
| sizing v1/v2 | `thesis/sizing.py` | 公式(輸入=confidence×magnitude) |
| kill VaR / paper NAV | `paper_ledger.py` / `paper_league.py` | 公式 |
| tier-1 期權 0-100 scorecard | karst skill | 已係統一刻度嘅先例 |

### 1b. 仍靠判斷(平模型執行會退化)⚠️

| 判斷面 | 而家點做 | 退化風險 |
|---|---|---|
| **confidence** | 半公式:`(4-KPI 總分)/8 × penalty(~0.5)`,但 4-KPI 逐格同 penalty 倍數係 agent 推理 | **高**——同一證據,平模型俾出唔同 subscore |
| **magnitude_tier** | magnifier 5 特徵人手判(2x/2-3x/3-5x-durable/5-10x-binary) | **高**——檔位錯直接影響 sizing v2 |
| **cycle_stage** | 逐 theme/node 人手判 | 中——有慣性,但升降級時刻靠判斷 |
| **kill 距離** | news_watch flag 方向,但「有冇實質靠近」人手判 | 中——夜班已出現「待日間覆核」隊列 |
| **INGEST admit/更新** | 逐篇判(4-KPI/priced-in/crowding) | 中——有 SKILL 紀律,但無 rubric 對照表 |

### 1c. 結構性差距(對比 TradingKey 模式)

現有 tier-2 score 係**乘法閘**:唔合資格=0,合資格=confidence 縮放。後果:

1. **同 theme 內兩隻合資格股分數幾乎一樣**(只差 mcap gate)——估值/預期/擁擠/insider
   全部**已經計咗**但唔入分,揀股靠 `pick_ticker()` 嘅 ad-hoc 排序(magnitude→pe_pctile)。
2. **冇統一刻度**:tier-1 有 0-100,tier-2 個股冇真綜合分;用戶問「AVGO 定 LITE」時,
   系統俾唔到一個「AVGO 62 分 vs LITE 48 分,差喺估值+擁擠」嘅答案。
3. **冇 peer 對比呈現**:數據齊(同 theme 內逐隻 pe_pctile/crowding/P_base)但冇並排。

TradingKey 嗰種「6 維度 34 指標」嘅啟示唔係抄佢指標(佢嘅預測力未知),
係**呈現架構**:統一刻度 + 維度分解 + 同儕對比 + 明確價位。Karst 嘅底層數據
已經夠砌呢個架構,差嘅係「組合」一步——而組合係純算術,正正係平模型執行到嘅嘢。

---

## 2. 五個提案(按 價值÷工作量 排序)

### P1|Tier-2 個股 0-100 綜合分(純組合現有讀數,零新訊號)★首推

```
composite = Σ wᵢ × dimᵢ    (每 dim 0-100,權重凍結喺 YAML)

dim_trend   : vs_200sma 帶狀映射(>+15%=100 … 破位=0)          [theme_signal 已有]
dim_value   : 100 − pe_pctile(自身歷史,平=高分)               [theme_signal 已有]
dim_expect  : P_base@14x 帶狀映射(≥0.8=100 / 0.4-0.8=60 / <0.4=25) [valuation 已有]
dim_crowd   : 100 − crowding_pctile(買入視角)                  [crowding 已有]
dim_thesis  : confidence × 100,late-cycle 打 8 折               [themes.yaml 已有]
dim_insider : 50 + insider.score × 50                            [providers 已有]
```

- **冇一個新訊號**,全部係 1a 表入面已回測/已驗證管道嘅輸出;新嘢只係權重向量。
- **權重凍結喺 `backtest/spine/composite_weights.yaml`**,起步用等權(冇證據支持
  任何非等權),日後由 forward log 校準——權重調整=設計時決策,唔係執行時。
- **pre-profit/binary 名行「N/A 車道」**:pe_pctile/P_base 缺 → 唔扮有分,card 標
  「option-framing,綜合分不適用」(同 N/A-binary 桶一致,唔造假分)。
- **用途排序**:①即刻做 `pick_ticker()` 嘅排序依據(sizing-neutral,今日就可以);
  ②日報/dashboard 顯示 + 同 theme peer 並排;③**入 sizing 前必須過 A/B 增量回測**
  (vs 現行 gate score,mirror=long-only,4 股種,前後半)。
- 工作量:~1 日(一個 pure function + YAML + card 欄位 + 日報一行)。

### P2|confidence 推導凍結成公式 + rubric 錨定 subscore

```
confidence = (Σ 4-KPI)/8 × penalty_lookup(crowding_band, cycle_stage)
penalty_lookup = 5×3 查表(凍結,例:late+crowd>80 → 0.40;early+crowd<40 → 0.90)
```

- 4-KPI 每格 0/1/2 **保留判斷**,但每格配書面判準(rubric):平模型做嘅係「證據
  對判準」嘅匹配,唔係自由心證。rubric 住喺 `thesis/DESIGN.md` 新章節。
- **算術搬入 lint**:`thesis/lint.py` 加檢查——themes.yaml 記錄嘅 confidence 必須
  等於公式輸出(subscore 記錄喺 wiki 推導段),對唔上=lint error。呢個把「數字係咪
  跟到自己聲稱嘅推導」由自律變成機械檢查。
- 順手修正 fable-logic-review 指出嘅「sizing 反排序」根因之一:confidence 數字
  嘅可比性(而家逐個 theme 推導口徑微妙唔同)。
- 工作量:~1 日(rubric 寫作佔大半;lint 檢查 ~50 行)。

### P3|magnitude_tier:5 特徵入面 3 個轉機械

| Magnifier 特徵 | 轉機械? | 來源 |
|---|---|---|
| F2 估值 headroom | ✅ pe_pctile 帶狀 | theme_signal |
| F3 距底部 | ✅ price vs 多年低點分位 | data.py 一行 |
| F5 情緒/擁擠 | ✅ crowding composite | crowding_composite |
| F1 新事實強度 | ❌ 保留判斷(rubric 錨定) | INGEST 流程 |
| F4 樽頸位置 | ❌ 保留判斷(呢個先係 thesis 本體) | 人手/貴模型 |

- 檔位 = (3 個計算特徵 + 2 個 rubric 判斷)查表;lint 加一致性檢查
  (例:F3 貼底 + F5 低擁擠但判 2x → flag 落 review queue)。
- 夜班 staleness 覆核(magnifier_review_queue)從此有客觀對照:計算特徵有變
  先值得覆核,唔使平模型自由判「證據薄唔薄」。
- 工作量:~1.5 日。

### P4|kill 距離分數(逐條軸機械化,可以嘅先做)

themes.yaml 每條有數字閾值嘅 kill 軸,加機器可讀欄位:

```yaml
kill_metrics:
  - metric: starlink_rev_yoy      # SPCX
    current: 0.498                 # 最近讀數(季更)
    trigger: 0.30                  # 跌穿即 kill
    direction: below
```

- → `kill_proximity = (current − trigger) / trigger` 每 theme 一個 0-100 距離分,
  入日報(「kill 距離:仲有 66% 緩衝」)。news_watch 嘅方向 flag 從此有錨。
- 誠實邊界:好多軸本質係質性(「約束語言消失」),呢啲**保留 prose**,唔硬塞數字。
  預計 15 theme 入面約半數有至少一條可量化軸。
- 工作量:~1 日 code + 逐 theme 補 current/trigger(可以夜班分批)。

### P5|Entry/Exit 卡(呈現已驗證規則,唔發明新閾值)

每隻 opportunity 名出一張機械卡:

```
入場區:200SMA($X)至現價($Y)之間分批;RSI-2<10 嘅回調日加注   [已驗證:RSI-2 dip×質優]
加碼:回落至 200SMA 附近                                        [現行 briefing 已有]
離場:收市跌穿 200SMA(theme composite 同款)                    [core-v2 已驗證嘅鏡像]
注碼:sizing 表 %(衛星 sleeve)                                  [sizing v1/v2]
```

- **全部係已回測規則嘅參數化呈現**(RSI-2 dip-buy、200SMA 閘、20 日高突破 timer
  喺 KARST_WIKI §5 有格仔);**唔加任何未驗證嘅新價位邏輯**(07-13 trim-rule
  驗證前後半唔一致嘅教訓)。
- 個股層面 200SMA 破位規則證據唔及 ETF 層硬——卡上照標「系統規則,非已驗證訊號」
  (同 07-14 新觸發通知同一句)。
- 工作量:~0.5 日(數據全喺 theme_signal row 度)。

---

## 3. 唔做乜(同點解)

1. **唔抄 TradingKey 嘅指標集**——佢 34 指標嘅預測力未知;Karst 嘅 edge 係
   「入 sizing 前必須回測」呢條紀律,唔係指標數量。抄呈現架構,唔抄內容。
2. **綜合分唔即刻接 sizing**——權重未經驗證;先 display + pick_ticker 排序
   (sizing-neutral),累積 forward log 先講。
3. **唔為 binary/pre-profit 名造假分**——N/A 車道係誠實設計,唔係缺陷。
4. **唔加分析師目標價/共識維度**——07-14 已判(earnings-expectation-ratio-rejected):
   共識類數據冇免費歷史、同現有估值軸冗餘。TradingKey 嘅「機構認同度」維度
   正正係嗰類,唔跟。

## 4. 建議次序

**P1 → P2 → P5**(合共 ~2.5 日)係一組:P1 俾統一刻度,P2 令刻度嘅最大輸入
(confidence)可比可審計,P5 令「跟住點做」機械化。P3/P4 係第二波
(magnifier 推廣同 kill 軸補數,可以夜班分批做)。

做完之後平模型執行面貌:夜班每日=計分+對表+diff+發 queue;
貴模型季度=審 rubric、校權重、判 queue 入面嘅邊界 case。
