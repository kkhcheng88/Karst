# 雙軸 Sizing 決策分析:confidence 單軸 vs. 加入 magnitude 軸

**日期**: 2026-07-12
**產物**: `backtest/experiments/exp_sizing_two_axis.py`(可執行,50,000 條路徑)、
`backtest/results/_sizing_two_axis_metrics.csv`(逐 scheme 指標快照)
**狀態**: 決策分析,**not a backtest**(見下方「這不是甚麼」)

---

## 這不是甚麼(讀之前必看)

**這份文件不是回測。** Karst 目前沒有任何已到期的 track record 可供回測——
`thesis/ic_report.json`(2026-07-11 產出)顯示 439 筆預測、59 檔股票、8 個日期,
但三個 horizon(21/63/126 交易日)的 `matured` 全部是 0,`raw_ic_daily` /
`weekly_theme_rolling26` 全部是 `null`。沒有已實現的報酬可拿來檢驗任何 sizing 方案孰優孰劣。

本文件做的事:對 15 個 active theme,**人手指派**一組 magnitude(上行倍數)與
downside(kill-trigger 損失)假設,再用 Monte Carlo(50,000 條路徑)模擬「如果這些假設大致
正確,四種不同的 sizing 方案分出來的 $ 配置,長期期望值/尾端風險長怎樣」。這是一個
**假設驅動的決策分析(decision analysis on assumed payoffs)**,結論的可信度上限
被「magnitude/downside 假設本身有多準」卡住——這些假設是粗略的、基於 cycle_stage
與 theme 筆記的**判斷**,不是量測值。詳見文末「限制與注意事項」。

---

## 方法

1. **來源**:15 個 `status: active` 的 theme,confidence/meta_factors/cycle_stage 全部讀自
   `thesis/themes.yaml`(現貨,未修改)。judge 狀態讀自 `thesis/ic_report.json`
   (現貨:`PRELIMINARY`,`circuit_breaker: false`)。
2. **共用資源**:四個方案全部使用同一個 $41,000 satellite budget、同一個 $20,500 總部署
   上限(= 現行 PRELIMINARY 狀態 50% cap,`thesis/sizing.py` 原本就有的規則)。
3. **Magnitude/downside 假設**:見下方全表。粗略規則(任務指定):
   late/priced-in → 1.5–2x / -50%;mid → 2–3x / -35%;early/cheap(USAC、FSLR 明確指名)
   → 3–5x / -35%;event-binary → 5–10x / -80%,且成功機率減半。
4. **三態 Monte Carlo 報酬模型**:每個 theme 每條路徑抽一個 uniform draw,分三態——
   kill(機率 = 1 − p_success,報酬 = downside)、half-win(機率 = 0.5×p_success,
   報酬 = 0.5×(magnitude_mid − 1))、full-win(機率 = 0.5×p_success,
   報酬 = magnitude_mid − 1)。binary theme 用 p_success = 0.5×confidence;
   其餘用 p_success = confidence。
5. **Common random numbers**:baseline(confidence×1.0)與敏感度情境
   (confidence×0.8)共用同一組 uniform 亂數,只有機率門檻隨 conf_mult 改變——
   讓「排名是否改變」的比較不受抽樣雜訊干擾。
6. **ai-power-grid 特殊處理**:此 theme 在 themes.yaml 有 5 個 node 各自的
   `magnitude_tier`(2026-07-12 新增的 additive schema,`sizing.py` 本身仍是
   theme-granular、未使用這欄)。B/C/D 的**配置**數學仍在 theme 層級運作(與
   sizing.py 一致),用一個以 ticker 數加權平均出來的 blended magnitude_mid≈3.5;
   但**報酬模擬**額外做了 node-mixture:每條路徑先抽哪個 node「主導」,再套用該
   node 自己的 magnitude/downside/binary 規則,保留節點層級的資訊豐富度。
7. **N_PATHS = 50,000**(達標 ≥10,000 的要求),seed = 20260712。

---

## 四個方案定義

| 方案 | 定義 |
|---|---|
| **A. status quo** | 直接呼叫 `thesis/sizing.py` 的 `build_table()`(用 `importlib` 載入原始檔,非手動重寫)——PRELIMINARY 狀態:per-theme raw cap = min(confidence×$20k, $15k),再過 meta_factor 50% 集中度 cut,再縮到總部署 50%×$41k = $20,500。 |
| **B. confidence × magnitude** | score = confidence × log2(magnitude_mid),非 binary 的 13 個 theme 按 score 比例分掉 $20,500 − 2×$1,000;binary theme(space-satellite、rare-earth-materials)各拿固定 $1,000「選擇權型」倉位。 |
| **C. Top-5 集中** | 按 confidence × magnitude_mid(原始乘積,非 log)排序,只有前 5 名有錢,按 score 比例分掉全部 $20,500,其餘 10 個 theme = $0。 |
| **D. Kelly-lite** | f\* = (p·b − q)/b,p = 成功機率(binary 減半)、b = magnitude_mid − 1、q = 1−p;負 Kelly → $0;每個 theme 上限 $5,125(= 25%×$20,500);若加總超過 $20,500 才整體等比例縮小(不足則不強制打滿)。 |

---

## 15 個 theme 的 magnitude/downside 假設表(全部標示為 ASSUMPTION,非量測)

| theme | confidence | 分類 | magnitude_mid | downside | binary | 理由(摘要) |
|---|---|---|---|---|---|---|
| memory-supercycle | 0.38 | late_priced | 2.0x | -45% | 否 | late(MU capex 2.66x top signal)但 LTA/SCA take-or-pay 合約明確緩衝下行——落在 late/priced 區間高端,downside 因同一理由由 -50% 放寬到 -45% |
| photonics-optical | 0.30 | late_priced | 1.5x | -50% | 否 | 全登記表中最擁擠的 cluster(58% bull)+ moat 名字(COHR/LITE/FN)ttm_pe 75-98th percentile——落 late/priced 低端,全額 -50% |
| ai-power-grid | 0.33 | late_priced(node mixture) | 3.5x(blended) | -53.75%(blended,僅供參考) | 否(理論層級) | Theme 層級數字是 5 個 node 按 ticker 數加權平均;報酬模擬改用逐路徑抽 node,見下方 node 表 |
| advanced-packaging | 0.32 | late_priced | 1.5x | -50% | 否 | 5 個 discovery-radar proxy(TTMI/MKSI/KLAC/AMKR/ASX)全部 90-100th ttm_pe percentile |
| space-satellite | 0.28 | event_binary | 7.5x | -80% | 是 | Theme 自己的 verdict 明講用 option/event 框架表達、小倉位、嚴格止損;ASTS 377x/RKLB 94x P/S,多是 pre-revenue |
| rare-earth-materials | 0.28 | event_binary | 7.5x | -80% | 是 | Verdict 字面就是「real-chokepoint-thin-evidence-event-binary」;2026-11 中美停火到期binary催化劑;MP 已在 92nd percentile |
| tpu-custom-silicon | 0.25 | mid | 2.5x | -35% | 否 | mid cycle_stage,產業鏈 75-87th ttm_pe percentile,只有單一 Tier-2 來源 |
| oil-gas-energy | 0.25 | late_priced | 1.5x | -40% | 否 | Verdict「thin-split-watch」——明確異質(oil-macro 中性 + gas-power 偏多,「不是同一個 thesis」),downside 由 -50% 略為放寬到 -40% |
| semicap-equipment | 0.20 | late_priced | 1.5x | -50% | 否 | 全表證據最薄弱(1 份中性報告,0% bull);AEHR fwd PE ~615x,一年 +856% |
| aerospace-specialty-alloys | 0.24 | late_priced | 1.5x | -50% | 否 | ATI/CRS 都在 98th ttm_pe percentile,只有 tier-3 來源,未做深度 ROIC/TAM 研究 |
| euv-lithography-monopoly | 0.22 | late_priced | 1.5x | -50% | 否 | ASML 98th ttm_pe percentile——「全表最 priced-in」 |
| us-solar-manufacturing (FSLR) | 0.32 | early_cheap | 4.0x | -35% | 否 | 任務指定明確點名;ttm_pe 只在 22nd percentile,是 6 個新 discovery-radar theme 中最便宜的 |
| gas-compression-equipment (USAC) | 0.33 | early_cheap | 4.5x | -35% | 否 | 任務指定明確點名;ttm_pe 2nd percentile——全部 15 個 active theme 中最極端的便宜 |
| specialty-siding-pricing-power (LPX) | 0.20 | mid | 2.0x | -35% | 否 | 全表最低 confidence;ttm_pe 95th percentile 是混合/不乾淨讀數(OSB 弱 + Siding 強混在一起) |
| glp1-biologics-packaging (WST) | 0.27 | mid | 2.5x | -35% | 否 | ttm_pe 71st percentile(中等);track record 最短(4 季) |

### ai-power-grid node 拆解(僅供報酬模擬使用,配置數學仍用 blended 3.5x)

| node | ticker 數(權重) | magnitude_mid | downside | binary |
|---|---|---|---|---|
| grid-hardware | 7 | 2.5x | -50% | 否 |
| power-semis-mature | 4 | 2.5x | -50% | 否 |
| pre-earnings-optionality | 3 | 7.5x | -80% | 是(WOLF 已真實申請 Chapter 11,事後驗證 binary 標籤成立) |
| uranium-fuel | 1(ETF-only,URA) | 4.0x | -35% | 否 |
| ipp-utilities | 1(ETF-only,UTES) | 2.0x | -35% | 否 |

Blended magnitude_mid = (7×2.5+4×2.5+3×7.5+1×4.0+1×2.0)/16 = **3.5x**(程式計算,非手打)。

---

## 結果:baseline 情境(confidence 原始值)

| scheme | 部署 $ | 有錢的 theme 數 | 最大單一 theme 佔比 | E[PnL] | median | P5 | P95 | P(虧損>30%部署額) | 資本效率(E[PnL]÷部署) |
|---|---|---|---|---|---|---|---|---|---|
| A. status quo | $20,500 | 15 | 12.2% | **$234** | -$1,628 | -$8,819 | $15,306 | 21.5% | 1.1% |
| B. conf×magnitude | $20,500 | 15 | 15.7% | **$2,547** | $1,563 | -$8,027 | $16,601 | 13.2% | 12.4% |
| C. Top-5 集中 | $20,500 | 5 | 25.9% | **$4,033** | -$1,558 | -$13,259 | $39,878 | 37.4% | 19.7% |
| D. Kelly-lite | $12,124(未打滿 cap) | 5 | 42.3% | **$5,248** | $3,448 | -$5,671 | $23,648 | 24.6% | 43.3% |

Scheme A 的 $20,500 部署總額**與 `thesis/sizing.py` 現行邏輯直接呼叫得出的結果完全一致**
(誤差 0%,優於驗收標準的 <1%)——因為 Scheme A 不是重新實作,而是用 `importlib`
直接載入並呼叫 `thesis/sizing.py` 本身的 `build_table()` 函式。

Scheme C 的 Top-5 名單:`space-satellite, rare-earth-materials,
gas-compression-equipment, us-solar-manufacturing, ai-power-grid`。

### 15 個 theme 在四個方案下各自拿到多少錢(baseline)

| theme | conf | mag | A ($) | B ($) | C ($) | D ($) |
|---|---|---|---|---|---|---|
| memory-supercycle | 0.38 | 2.0 | 1,184 | 1,708 | 0 | 0 |
| ai-power-grid | 0.33 | 3.5 | 1,028 | 2,681 | 2,916 | 2,542 |
| gas-compression-equipment | 0.33 | 4.5 | 1,028 | 3,219 | 3,749 | 5,125 |
| advanced-packaging | 0.32 | 1.5 | 997 | 842 | 0 | 0 |
| us-solar-manufacturing | 0.32 | 4.0 | 2,509 | 2,877 | 3,232 | 3,827 |
| photonics-optical | 0.30 | 1.5 | 934 | 789 | 0 | 0 |
| rare-earth-materials | 0.28 | 7.5 | 2,195 | 1,000 | 5,302 | 315 |
| space-satellite | 0.28 | 7.5 | 2,195 | 1,000 | 5,302 | 315 |
| glp1-biologics-packaging | 0.27 | 2.5 | 2,117 | 1,605 | 0 | 0 |
| oil-gas-energy | 0.25 | 1.5 | 779 | 657 | 0 | 0 |
| tpu-custom-silicon | 0.25 | 2.5 | 779 | 1,486 | 0 | 0 |
| aerospace-specialty-alloys | 0.24 | 1.5 | 1,881 | 631 | 0 | 0 |
| euv-lithography-monopoly | 0.22 | 1.5 | 685 | 579 | 0 | 0 |
| semicap-equipment | 0.20 | 1.5 | 623 | 526 | 0 | 0 |
| specialty-siding-pricing-power | 0.20 | 2.0 | 1,568 | 899 | 0 | 0 |

**最大的單一發現**:Scheme C(naive Top-5 by confidence×magnitude)讓 `space-satellite`
和 `rare-earth-materials`——兩個 confidence 最低區間(0.28)、event-binary、
「thin-evidence」的主題——各拿 $5,302,合計吃掉 51.7% 的總部署,**超過**全表 confidence
最高(0.38)、證據最紮實(有 LTA/SCA 合約支撐)的 `memory-supercycle` 拿到的
$0。單純用 conf×magnitude 排序、不對 confidence 設任何門檻,magnitude 的指數級數字
(7.5x vs 1.5-2x)會直接輾壓 confidence 的線性差距——這是「純粹追 magnitude 集中度」
的典型風險示範,不是這次分析刻意做出來的巧合。

第二個值得注意的發現:Scheme D(literal Kelly-lite)在 baseline 情境下**只有 5 個
theme 有正 Kelly edge**,總部署只有 $12,124(約 41,000×0.30,遠低於 $20,500 的
cap),即約 **$8,376(41% 的部署上限額度)完全沒有配置**。這不是 bug,是 Kelly
公式本身「寧可不下注也不要負期望值下注」的忠實反映——但要注意這是**簡化版**公式
(見下方限制),對「失敗有部分回收」的 theme 系統性偏保守。

---

## 結果:敏感度情境(confidence 全體打 8 折,模擬 cold-start 高估)

| scheme | 部署 $ | 有錢的 theme 數 | 最大單一 theme 佔比 | E[PnL] | median | P5 | P95 | P(虧損>30%部署額) | 資本效率 |
|---|---|---|---|---|---|---|---|---|---|
| A. status quo | $20,500 | 15 | 11.1% | -$1,911 | -$3,644 | -$9,355 | $11,200 | 30.8% | -9.3% |
| B. conf×magnitude | $20,500 | 15 | 15.7% | $188 | -$1,027 | -$8,759 | $13,637 | 22.4% | 0.9% |
| C. Top-5 集中 | $20,500 | 5 | 25.9% | $745 | -$4,511 | -$13,259 | $34,192 | 46.9% | 3.6% |
| D. Kelly-lite | $2,530 | 2 | 87.0% | $1,076 | -$886 | -$886 | $7,593 | 55.1% | 42.5% |

Scheme C 的 Top-5 名單在 haircut 情境下**不變**(仍是同一 5 個 theme)。

### 排名穩定性檢查

- 按 E[PnL] 排名,baseline 與 haircut **完全一致**:D > C > B > A。
- 按資本效率排名,baseline 與 haircut **完全一致**:D > C > B > A。
- **A(status quo)在 haircut 情境下 E[PnL] 由正轉負**($234 → -$1,911),
  資本效率由 +1.1% 惡化到 -9.3%——四個方案中對 confidence 高估最敏感的是現行方案本身。

### 結構性發現:B、C 對統一 confidence 折扣「免疫」,A、D 不是

Scheme B 與 C 在 baseline 與 haircut 兩個情境下,**最大單一 theme 佔比(max_share)
與部署總額完全相同**(B: 15.7% / $20,500 兩邊一致;C: 25.9% / $20,500 兩邊一致,
且 Top-5 成員名單不變)。這是因為 B、C 的 $ 配置公式都是「confidence 的某個比例式」
(B 是 log2(magnitude) 加權比例分配、binary 是固定額;C 是排序後比例分配)——把全體
confidence 乘上同一個常數(0.8),既不改變相對排序,也不改變比例分配的結果,**只有
每個 theme 底下的報酬抽樣機率變了**(所以 E[PnL] 會變,但 $ 配置不變)。

反觀 Scheme A(受 $15k per-theme 絕對上限 + meta_factor 集中度 cut 的非線性結構影響)
與 Scheme D(Kelly 公式本身是仿射但非齊次,confidence 打折會直接把邊際為正的 theme
推過門檻變成 $0),兩者的 $ 配置在 haircut 下**都會實質改變**——D 尤其劇烈,
funded theme 數從 5 個降到 2 個,部署總額腰斬又腰斬($12,124 → $2,530)。

**意涵**:如果 Karst 的目標是「confidence 校準之前,先讓 sizing 規則本身對
confidence 系統性高估有一定韌性」,B/C 這種比例式配置在數學結構上天生比 A/D
更穩定——但這個穩定性不代表 B/C 的**絕對**配置就是對的(只是對 uniform 折扣不敏感,
不代表對個別 theme 的高估也免疫)。

---

## 限制與注意事項(務必閱讀)

1. **這不是回測。** 所有 magnitude_mid / downside 數字都是根據 `cycle_stage` +
   themes.yaml 筆記的**人工判斷**,不是從任何歷史價格或已實現報酬量測出來的。
   Karst 目前零已到期預測(`ic_report.json` 三個 horizon 的 `matured` 全部是 0),
   沒有東西可以拿來驗證這些假設對不對。這份分析回答的問題是「如果假設大致合理,
   四種配置規則長期表現的相對排序長怎樣」,不是「哪個規則歷史上比較賺」。
2. **Meta_factor 集中度 cut 只套用在 Scheme A。** 現行 `sizing.py` 有「同一
   meta_factor 底下所有 theme 合計不能超過 50% budget」的規則(例如 9 個
   `ai-capex` theme 會被聯合砍到 $20,500 上限)。B/C/D 三個候選方案**沒有**套用
   這條規則——任務指定的共用約束只有 $41k budget 與 $20.5k 總部署上限,沒有要求
   複製 meta_factor 機制。這代表 B/C/D 的實際部署結果**低估**了它們若真要上線、
   套上同一條集中度規則後會受到的額外限制(尤其 Scheme C 集中在 5 個 theme,若
   其中多個共享同一個 meta_factor,實際部署會被砍更多)。
3. **Scheme D 用的是簡化版 Kelly 公式**,f\* = (p·b − q)/b 隱含「失敗 = 全損」的
   假設,並未使用本分析自己指派的 -35%~-80% 部分回收 downside。這會讓 D 系統性
   偏保守——尤其是那些 magnitude 不算特別高、但 downside 相對溫和的 theme(例如
   memory-supercycle 的 -45%,不是 -100%),用完整版非齊次 Kelly
   f\*=(p·b−q·L)/(b·L)(L=損失幅度)重新計算,預期會有更多 theme 出現正 edge、
   總部署額會更接近 $20,500 上限。本分析選用簡化公式是照任務原文字面規格
   (`f* = (p·b − q)/b`),結果解讀時請把 D 的部署不足(baseline 只用了 59% 的
   cap)視為「這個特定公式的保守性」,不要直接讀成「Kelly 精神本身建議少配置」。
4. **Binary 分類與 $1,000 固定倉位、25% Kelly 單一上限,都是本分析自訂的假設**,
   不是既有系統規則。$1,000(Scheme B)與 $5,125 = 25%×$20,500(Scheme D)的
   具體數字沒有特別的理論基礎,只是為了讓四個方案在「有沒有上限機制」這件事上
   保持某種程度的可比性而選的合理數字。
5. **ai-power-grid 的 node-mixture 報酬模擬是本分析新加的**,`thesis/sizing.py`
   與其餘四支既有腳本(lint.py/concentration.py/beta_check.py/theme_signal.py)
   目前仍是純 theme-granular,不讀取 node 資訊。若之後要把 node 級 magnitude
   真的落地到配置邏輯(而不只是報酬模擬),需要另外設計。
6. **相關但不同的既有分析**:`backtest/results/2026-07-11_sizing_formula_validation.md`
   針對另一個候選第二軸(margin-of-safety 折價 × convergence speed)做過歷史案例庫
   驗證,發現折價半邊有弱但真實的訊號(n=20-21,Spearman rho=0.56,p=0.0098),
   convergence speed 幾乎無訊號,且折成約 11 個獨立宏觀週期後顯著性消失
   (p=0.083–0.69)。該文件明確建議任何第二軸都應該保持保守、不要與 confidence
   並駕齊驅,並點出 WOLF(Wolfspeed)聲請 Chapter 11 的「solvency gate」風險——
   一個表面上「折價」的名字,其實是在為真實的破產風險定價。本分析的
   magnitude 假設同樣完全沒有對「便宜是否等於有償付能力風險」做任何篩選,是同一類
   風險的延伸,尤其 gas-compression-equipment(USAC)與 us-solar-manufacturing
   (FSLR)這兩個「early_cheap」分類的 theme 值得額外注意有沒有類似的 solvency
   gate 問題。
7. **N_PATHS=50,000、單一 seed(20260712)**。沒有做多 seed 重複驗證變異數,
   但 common random numbers 設計已經讓 baseline vs. haircut 的排名比較不受抽樣
   雜訊干擾——排名結論(D > C > B > A,兩個指標都一致)在這個 seed 下相當穩健,
   但沒有做正式的統計顯著性檢定。

---

## 給主審查 agent 的結論摘要

四個方案在 baseline 與 haircut 情境下,E[PnL] 與資本效率排名**完全一致**:
**D(Kelly-lite)> C(Top-5 集中)> B(conf×magnitude)> A(現行 status quo)**。

但排名不能直接讀成「應該換成 D」——D 的高效率主要來自於它把 90% 資金押在
gas-compression-equipment 與 us-solar-manufacturing(兩個「early_cheap」假設,
本分析完全沒有做 solvency 篩選)這類少數幾個高 assumed-magnitude 名字上,
且用的是偏保守的簡化 Kelly 公式,實際上線行為可能與這裡模擬的不同。C 則直接示範了
「不設 confidence 門檻的 magnitude 加權」會讓 event-binary、thin-evidence 的
theme(space-satellite、rare-earth-materials)吃掉一半以上部署額,超過全表
confidence 最高的 memory-supercycle——這是本分析認為最值得主審查 agent 注意的
結構性風險,不是「該用哪個方案」的答案,而是「任何magnitude 軸都需要一個
confidence 門檻或上限,否則會被 magnitude 的指數差距輾壓」的證據。

---
