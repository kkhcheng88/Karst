# Phase-3 方法論 Adversarial 審查(Fable 任務 7)

> **審乜**:Phase-3(質性 thesis)機制夠唔夠好去「開始累積 forward 戰績」。審 in-repo 實物
> (thesis/DESIGN.md、themes.yaml、forward_ic.py、log_predictions.py、insider.py、corpus、wiki 樣本)。
> 外部 plan 檔(valiant-questing-horizon)喺 repo 外,拎唔到——但方法論內容 brief §7 已列全,
> 且「審實際建咗嘅嘢」正正係 adversarial 審查應該做嘅。
> **審查現況**:9 個 Type-B、0 個 Type-A;track_record 164 條(**0 條有 outcome**);corpus 102 篇
> (單一來源 gooptions、全 Tier-2 意見、僅 2 個月);thesis_valuation.py / cycle_position.py 不存在。

## 1. 總判:仲未 FIT 開錶。三個 blocker(依殺傷力):

### ★ Blocker 1 — 校準迴路係「斷咗」,唔係「慢」
164/164 條記錄用**薄 schema**(ts/thesis_id/ticker/confidence/cycle_stage)——冇 `outcome`、冇
`prediction`、冇 `kill_condition` 欄位。原因:**得 `forward_ic.py` 嘅薄 logger 行過**(06-30/07-01/07-02
三次);有 outcome 欄位嘅 `log_predictions.py run()` **從未執行過**(`grep -c '"prediction"'
track_record.jsonl` = 0)。回填 job 不存在。**∴ 時間過幾耐都唔會有數據累積——而家每日 log 嘅嘢,
遲早要重錄。** 9 個 confidence(0.20-0.38,全部手 set、標明 uncalibrated)冇任何機制會喺數月內修正,
就算 9 個全部錯晒。

### ★ Blocker 2 — 闊度唔夠:n=9 統計上解唔開自己個成功標準
單期 rank-IC 噪音 ≈ 1/√(n−1) = **0.354**(係 0.05 目標嘅 7 倍)。週度非重疊累積,t≥2 需時:

| 真 IC | 需要週數 | 日曆時間 |
|---|---|---|
| 0.05(設計目標「贏 SPY」)| ~200 | **~3.8 年** |
| 0.10(「翻倍級」)| ~50 | ~1 年 |
| 0.15 / 0.20 | ~22 / ~12 | ~5 / ~2.5 個月 |

仲衰:9 個主題有 4-6 個同揸 AI-capex 因子(memory/photonics/packaging/TPU-silicon)→ **有效獨立闊度
可能只 4-6**。要 1 年內解到 IC=0.05,需 **n≈32** 個去相關主題;半年內要 n≈63。
**∴ 依家開錶 = 每一週買到嘅統計 power 接近零,除非系統真係好過自己目標 2-3 倍(IC≥0.10-0.15)。**

### Blocker 3 — 防「追已爆共識」嘅兩道閘 = prose-only
priced-in 閘、週期位置閘:每個 wiki 頁一次過手拉數(MU ttm_pe 26/67% 分位、capex 2.66×,全部釘死喺
2026-07-01)——冇 code 重算、冇排程、冇 threshold 判定。**呢兩道閘正正係「ideas = 共識非 novel
foresight」誠實邊界嘅執行機制**,而家係裝飾。insider `conf_eff`(唯一算緊嘅 corroboration)又冇接入分數。

## 2. 生命週期逐格判定

| 階段 | 判定 | 證據 |
|---|---|---|
| 發現 | PARTIAL | corpus.py FTS5 真;但單源(gooptions)、全 Tier-2、102 篇/2 個月;Tier-1(filing/逐字稿)未接 |
| 4-KPI 假設 | 模板 OPERATIONAL / 打分 PROSE | 冇 four_kpi.py;X/8 × 週期 penalty 全部係 markdown 手算 |
| 偽證 kill | PARTIAL | schema 迫每主題有 kill_condition(lint.py:84)但**冇 code 讀佢判 true/false**;質素混雜——space-satellite 有 ticker+日期+二元事件(好);oil-gas 有價位冇日期冇定義(「decisively」= ?);semicap「continues / at scale」不可量度 |
| priced-in 閘 | **PROSE-ONLY** | thesis_valuation.py 全 repo 不存在 |
| 週期位置閘 | **PROSE-ONLY** | cycle_stage 手 set free-text;冇 capex 加速比/ETF 發行數/擁擠度計算 |
| 表達 ThesisVerdict | ✅ OPERATIONAL | providers.py:40-51 → expression.py:65-66 真接線(唯一全通嘅一格)|
| 追蹤 forward IC | PARTIAL | compute_ic() 真 Spearman;**「≥0.05」只係 docstring,冇 PASS/FAIL code**(= ROADMAP A4 未做)|
| Type-A 危機 sleeve | **零 artifact** | 0 個 type:A 主題;冇 crisis 程式;VIX 66 聽日出現唔會有任何嘢 fire(gap_forensics 嘅 2020-04 XLE 例子係回測發現,唔係 forward 規則)|

## 3. 改進計畫(排序;每項有驗收)

| # | 修乜 | 點解 | 驗收 | 工作量 |
|---|---|---|---|---|
| 1 | **統一雙 logger 落 rich schema + 起 outcome 回填 job** | 唔修,時間唔會變數據 | 63 日後 `grep -c '"outcome": {'` > 0 | M |
| 2 | **forward_ic PASS/FAIL 程式化(JSON)** | 成功標準而家問唔到機器 | verdict() 出 {status, ic_mean, n_dates, threshold} | S |
| 3 | **改裁判(即刻做 S 版)**:近期主裁判 = **每主題 hit-rate/expectancy @ 20-30 個到期 outcome**(DESIGN §6 自己都有寫);cross-sectional IC 降做慢速輔證;寫入 docstring/report 免半年後誤判「PRELIMINARY = 失敗」 | n=9 解唔開 0.05,呢個係數學唔係意見 | forward_ic 文檔+report 反映雙層裁判 | S(reframe)/ L(真擴闊度到 ~30 主題,持續做——任務 8 起步)|
| 4 | **conf_eff:接入或者刪** | 假接線比冇接線更誤導(卡面睇落已 temper,實際冇)| expression.py grep conf_eff 有 hit,或卡面刪欄 | S(方向按 A/B 測)|
| 5 | **起碼版 thesis_valuation.py**:ttm_pe 分位 + capex YoY 排程重算(數據管道 defeatbeta 已證行得通,只係而家靠人手拉)| 冇校準迴路之前,呢啲 snapshot 係 confidence 同現實嘅唯一連繫,而佢哋緊釘死喺 07-01 | 隔月跑兩次,asof+數值真係識變 | M |

**開錶條件**:#1 + #2 落地 → 先開錶;#3 S 版同步;#5 儘快;#4 決定咗方向就做。

## 4. 對用戶 framing 嘅落地含義

- Phase 3 = 衛星(~20%)呢個 sizing 決定**同 audit 結論互相支持**:喺校準存在之前,confidence 係
  未經驗證嘅手寫數 → 衛星注碼 + confidence 上限(例如 ≤0.40)係啱嘅紀律,唔好因為某主題「感覺好勁」加注。
- **闊度即係 pipeline**:去到 ~30 個去相關主題先有統計出路 → 任務 8(bottleneck 掃描)唔係錦上添花,
  係 Phase-3 可測性嘅必要條件。發現引擎(3b loop)要由單源 gooptions 擴到 Tier-1 + 多源。
- 誠實講:Phase-3 嘅「大 alpha」故事而家係**一個結構良好但未接電嘅實驗設計**。修完 #1-#5(S+M 為主,
  唔難),佢先變成一個真係喺度累積證據嘅系統。
