# STATUS — Karst 現況(新 session 從這裡開始)

> **單一入口檔**。每個 session 結束時更新「現在在哪/下一步」兩節(取代散落交接)。
> 最後更新:2026-07-12。歷史細節不放這裡——放指針。
>
> **★ 全 workspace 導航地圖 = `docs/INDEX.md`**(邊份 doc live/design/superseded/personal、去邊搵嘢)。
> 見同名 v1/v2 一律用 v2;本檔下方「下一步」部分段落係 2026-07-06 sandbox 時代殘留(引用已
> SUPERSEDED 檔如 phase3_methodology_review/dashboard_design/bottleneck_candidates)——**以 INDEX.md
> §3 Phase-3 + `docs/2026-07-08_phase3_architecture.md` 為準**。

## 30 秒版:這是什麼

Karst = 每日 top-down 投資決策支援系統(NHITL 目標,**決策支援,人執行下單**)。
two-tier 輸出:SPY/QQQ/SPMO 用期權工具(LEAP/SHORT_CALL/CSP),其他個股只做多。
實證定位(20+ 回測):**價量訊號 = 風控,不是 alpha;alpha 唯一可能的門 = Phase 3
質性 thesis**。全系統的可證偽靶心:**thesis 排序 forward IC ≥ 0.05**。

## 每日自動化(schtasks;部機開住先跑;新 session 開波先掃一眼呢張表嘅「要做乜」欄)

> 2026-07-08 起全批搬到 **05:30 HKT 檔**(美股收市後、用戶瞓緊、rate limit 閒置;05:30 係為冬令
> DST 留 buffer —— 冬令美股收市 = HKT 05:00 正)。週任務用 TUE-SAT(對應美股 MON-FRI 收市)。

| 時間(HKT)| 任務 | 產物 / session 要做乜 |
|---|---|---|
| 05:30 二至六 | Karst-forward-IC-daily | `thesis/track_record.jsonl` 自動 commit(唔使理)|
| 05:35 每日 | Karst-gooptions-daily | 抓 gooptions.cc 新研究 + wiki stubs 自動 commit |
| 05:40 二至六 | Karst-playbook-daily | `playbook_log.txt`(core v2 每日判定表,用戶觀察用)|
| 05:45 每日 | Karst-transcripts-daily | 新 Backtest-Everything transcript 排入 `../Reference/raw_data/backtest_everything_transcripts/_PENDING_ANALYSIS.md` |
| 05:55 每日 | Karst-nightly-analysis(**已註冊 2026-07-09**;**2026-07-12 加咗第3項 guard**)| Python guard 三選一(transcripts inbox / gooptions manifest delta / **magnifier node 新stale**):全部零就零 quota;有一樣就 headless Claude(全 opus,acceptEdits + python-only bash)蒸餾 transcripts + ingest gooptions + **magnifier重新評分草稿**(寫入queue,唔自動落實),詳 `thesis/nightly_analysis_prompt.md` |
| 20:30 一至五 | Karst-premarket-daily(**已註冊,補記 2026-07-12**)| `premarket_log.txt`:開市前 ~1h live premarket 價疊加返 05:xx post-close 觸發表(dip/covered-call/200SMA),read-only |
| — | **人手 fallback(而家生效)** | 日間 session 見 `_PENDING_ANALYSIS.md` 有未剔 `[ ]` 或 gooptions 有新文 → 蒸餾/INGEST(判「採納/佐證/唔採納」)|

## 每週自動化(schtasks;唔係人手 fallback,係真.排程跑)

| 時間(HKT)| 任務 | 產物 |
|---|---|---|
| SUN 08:00 | Karst-insider-weekly | 重建 `thesis/insider_cache.json`(SEC EDGAR Form 4,gitignored)|
| SUN 08:15 | Karst-risk-check-weekly(**已註冊 2026-07-12**)| WS3 backlog #3-4:`weekly_risk_log.txt` = concentration.py(meta_factor 集中度,cap 50%)+ beta_check.py(逐 theme vs 板塊 ETF beta 化偵測)|
| SUN 08:30 | Karst-corpus-weekly(**已註冊 2026-07-12**)| 全 universe(~9.9k ticker)transcript 增量抓取 + `corpus.db` incremental build;~1-2h 跑完(機器要開住)。log 落 `thesis/.raw/transcripts/cron.log`(gitignored)|
| SUN 08:45 | Karst-insider-tilt-weekly(**已註冊 2026-07-12**)| ROADMAP A3/P0-c:`backtest/results/<date>_insider_tilt_live.md` = 細價股(<$2B)12個月insider群買tilt live snapshot,display-only,未接sizing.py |
| SUN 08:50 | Karst-altdata-twse-weekly(**已註冊 2026-07-12**)| altdata top-5 probe #5/ROADMAP Batch-3 #8:TWSE月度營收(免key)v1 淨追蹤 ASE(3711,advanced-packaging chain confirmation),存 `thesis/.raw/altdata_twse_history.jsonl`(gitignored,dedup)|

> **EIA-930電網探測(2026-07-12 建立又移除)**:曾經接入 PJM 電網逐時需求配 ai-power-grid,但用戶
> 覆核後判斷同 constraint scan(ai-power-grid 自己啲 ticker 嘅 transcript 語言,已經係主管道、更
> 直接、更早)重疊、增加複雜度但邊際價值低 → 2026-07-12 移除(script/排程/STATUS紀錄全部剔走)。
> `~/.config/eia/api_key` 保留(用戶自己攞嘅,冇壞處),但唔再用。crack spread(EIA)/ISM(FRED)/
> Cass Freight/AAR 呢幾條本身都未做,連同呢個一齊確認**唔再追**——altdata top-5 probe 淨係留返
> TWSE 一條。
| SUN 10:30 | Karst-constraint-scan-weekly(**已註冊 2026-07-12**;排喺 corpus-weekly 之後留 2h buffer)| WS4 backlog #1:`backtest/results/<date>_constraint_scan_production.md`(theme×季度熱力表)+ `thesis/.raw/constraint_scan_queue.md`(雙向新警報,持久 checklist,**有追蹤**,唔係gitignored)|

> **Magnifier staleness 已改做每日**(2026-07-12,原本獨立嘅 `Karst-magnifier-staleness-weekly`
> 已刪):理由——文章日日ingest,週度先check會慢成7日先追到。已摺入 05:55 嘅
> `Karst-nightly-analysis`(見上,第3項guard),同一日偵測、同一日 headless Claude 出草稿。
> Magnifier per-node schema 本身見 `docs/2026-07-08_phase3_ws3_lifecycle.md` §1a-node;首個
> worked example = ai-power-grid 5 nodes;草稿queue = `thesis/.raw/magnifier_review_queue.md`
> (持久checklist,**有追蹤**,人手confirm先落實,唔係夜班自動生效)。

## 人手週度任務(IMA;2026-07-12 新增 —— agent 做唔到,一定要用戶自己開 IMA)

> **點解要人手**:IMA 官方 wiki OpenAPI(daymade `ima-skill` 用緊嗰個)實測攞唔到全文,得 IMA 自己
> 個消費端 chat 介面先做到真.RAG——嗰個要用戶自己 login IMA 手動問,agent 冇辦法自動化。**新
> session 開波、或者每逢週一,check 呢張表有冇漏做**。細節/完整 prompt 見
> `docs/2026-07-09_ima_extraction_prompts.md`。

| 頻率 | Prompt | 用戶要做乜 | 落邊 |
|---|---|---|---|
| **每週** | ①資金流/持倉 | IMA 開 **DeepSeek**(2026-07-12 四model對打確認主力),貼 Prompt①,匯出.md,貼返 Karst | `backtest/results/` 或對應 thesis note |
| 主題變動時 | ②記憶體供需(可複製做其他主題) | 有主題新進展先跑,唔定期 | 對應 thesis wiki |
| 每週(可選) | ③供給約束語言全市場掃描 | Karst 最核心嗰條,但耗用大,睇量力而為 | discovery radar 候選池 |
| 每週 | ④板塊 house view/共識 | priced-in 參照,唔係買入訊號 | `backtest/results/2026-07-09_priced_in_gate.md` 類似檔 |

**貼返嚟嗰陣,Karst 會用 `docs/2026-07-09_ima_extraction_prompts.md`「貼返嚟時的驗證清單」逐項核實
先落檔**(單一孤證數字唔會盲信,即使有citation格式)。

## 現在在哪(2026-07-12)

**2026-07-12(Fable 5 獨立 session)—— 投資邏輯總審查完成(任務書 `docs/2026-07-12_fable_investment_strategy_brief.md`):**
- **★ 總審查報告 = `docs/2026-07-12_fable_investment_logic_review.md`**(§5-A/B 答案 + P0-P2 改進清單 + 創新層);
  **dashboard 設計書 = `docs/2026-07-13_dashboard_v4_portable.md`**(交付版,取代 07-03/07-06 舊檔;
  v3`docs/2026-07-12_dashboard_design_v3.md`留做版面骨架底稿,四行版面/五條原則仍生效)。
- 核心發現:①sizing 三重 cap 令注碼排名同信念排名**倒轉**(conf 第1嘅 memory 注碼排第7,$1,184;sizing.py 07-12 實跑),
  MC 四方案對比現行 E[PnL]≈$234 貼零(`results/2026-07-12_sizing_two_axis_decision_analysis.md`);②裁判有效橫截面闊度=主題數唔係 ticker 數
  + 63d IC 判 1-3y thesis 錯配 → 建議加 milestone-Brier 第二把尺;③估值/expectations-gap 全系統缺席(thesis_valuation.py 未起);
  ④「ai-capex 54.9%>50%」係 belief-weight 讀數,實際部署只 39.2%,錢冇爆錶——建議換做 kill-scenario VaR 做決策語言。
- 4 個新探測落檔(全部有 script 可重跑):sizing 兩軸 MC / capex-D&A 供給紀律雷達(**新警號:MP 兩軸齊響 2.19x/2.54x,排人手覆核**)/
  analyst 出席數擁擠 proxy(MU 谷底 20 年最低、USAC 全場最低,方向成立)/ 衛星期權表達(MU 一張最平 $9.1k,集中化係前提)。
- P0 三項:sizing v2(magnitude 軸+top-K 集中,shadow A/B 先行)、milestone-Brier 裁判、crypto 治理(排最先)。
- **第二波(同日,用戶三指令:估值可實施方案 / sizing 改 % NAV 制(系統自己係 portfolio manager,唔鏡射用戶)/ 「全風險組合」挑戰)**:
  ①**估值模組已實跑 v0**:`docs/2026-07-12_valuation_expectations_gap_spec.md` + `results/2026-07-12_expectations_gap_v0.md`(28/28 隻;15 主題 8 個「大部分係希望」、FSLR 唯一 0.83x「白送」;USAC 個平一半係債務槓桿假象;GEV 隱含 155.8%/年×5年)——production 化三步 + BT-5 判別力測試(案例庫六案全中先接 sizing 閘);
  ②**Karst-AA 全風險設計** = `docs/2026-07-12_all_active_design_response.md`(portable-alpha 結構:ballast 防守籃+LEAP 0.50Δ 填 delta+T sleeve 15-30%、delta 總帳做單一控制、% NAV 制);兩條新負重數:LEAP 115% delta 只使 9.55% NAV premium(`results/2026-07-12_leap_rent_delta_ledger.md`)、**防守板塊做偽現金實測輸現金 −1.51%/熊市episode、MaxDD 深 14pp**(`results/2026-07-12_ballast_parking_ab.md`)→ 推薦 AA-pragmatic(策略層零死資本,現金只做閘嘅停車場),strict/pragmatic 雙變體入 BT-2 對照;
  ③**BT-2 已跑完**(`results/2026-07-12_bt2_aa_vs_core.md`,step-0 重現 core v2 過閘、307k 條會計 assert 全過):AA 結構成立——MaxDD 淺 11pp(−44% vs core v2 −54.5%)、保守 α +5.0pp(t3.4)vs core v2 +6.4pp(差距=留俾 T sleeve 真 alpha 填);**AA-strict 反超 AA-pragmatic**(base +15.4%/+7.5pp t5.0,孤立 ballast 測試嗰筆 14pp 稅喺全結構唔成立)→ 推薦改口 strict 行先;AA-strict 係唯一 damp model 都過 Bonferroni×48 嘅格。
  ④**BT-7 ballast 定義測試已跑**(`results/2026-07-13_bt7_ballast_definition.md`):B1 現行 trio 三個 league 職責排名全勝留任;用戶候選 DIA 假設證偽(downside capture 92-98% 近乎 1:1 跟跌 + QQQ 相關全場最高);Mag7 反面對照確認(熊市 delta 地台 109%,冇得減磅);稅漏實測 trio +0.86pp/yr vs USMV +0.63pp(真但非決定性)。ballast 機制 = 季度職責體檢(設計檔 §8c)。
  ⑤**B 測試已跑**(`results/2026-07-13_bt_b_washout_expression.md`):washout 訊號期權 vs 現貨表達——同曝險口徑期權只贏 2-4/9(IV 貴+theta 食突),「期權本質更優」唔成立;定案 B 預設表達 = SPY 現貨細注,期權僅槓桿工具選項(機會階梯已更新)。**Dashboard v4 設計已定**(`docs/2026-07-13_dashboard_v4_portable.md`:DASHBOARD.md auto-commit 上 private GitHub + Telegram 門鐘,唔起雲 app)。**★ 全 session 交接書(俾 Opus 接手)= `docs/2026-07-13_fable_session_handover.md`**(D1-D10 決策 + P0-P2 backlog + 唔准重推名單)。
  ⑥第三輪(用戶追問):新 sleeve 候選 A-D + 機會階梯落檔(`docs/2026-07-12_new_sleeve_candidates.md`、`docs/2026-07-12_opportunity_ladder.md`;C 經用戶修正拆做 C-core=SPY/QQQ LEAP 主力 + C-list=P_base>1 極端錯價配角);實施閘:雷達層四個即裝、A 要完整 backtest、B 要表達層細測、C 冇得測改用簽名紀律、D 逐序列 spot-check。下一步:B 表達層測試 → dashboard v4(摺入 delta 總帳/估值欄/AA sleeve/機會階梯雷達)。

**2026-07-09~07-12(連續多 session)—— Objective A 收檔;Discovery Radar 全審完 + China 披露;4 條 backtest 驗證;magnifier 書蒸餾;IMA automation 解決。90 檔案 backlog 今日理清 commit:**
- **Objective A(宏觀恐慌板塊輪動)正式收檔,結論負面**:category-2(恐慌後板塊反轉)擴到 6 個歷史案例(XLK/XLC 2022-23、XLY/XLK GFC)後 pattern 不穩定 → 呢條線關咗(`results/2026-07-11_category2_sentiment_reversal_v3.md`);「復甦語言」實驗一開始睇似有訊號,spot-check 揭發係「trough」呢隻字污染(`_category2_recovery_language.md` 已明確 retract)。GFC 案例入面 financials(coincident/ground-zero)vs consumer-discretionary/tech(trough 落後數月)嘅時序差異留低做殘餘發現,唔再追。
- **★ Discovery Radar(Objective B 主力)全數 39-40 candidate 審完**:4 組 subagent verbatim 覆核(`results/2026-07-11_discovery_radar_review_group{A,B,C,D}.md`)→ `thesis/themes.yaml` 新增 6 個 theme(aerospace-specialty-alloys / euv-lithography-monopoly / us-solar-manufacturing / gas-compression-equipment / specialty-siding-pricing-power / glp1-biologics-packaging,連 `thesis/wiki/*.md`),KALU/MCHP/AVT/PTEN 4 隻列 WATCH 排下季 re-check。
- **China dependency 全市場 audit**(`results/2026-07-11_china_dependency_audit.md`,68 隻票):訂立 Type A(公司本身中資/國企關聯,capital-cycle 機制失效)/ B(美資但供應鏈/收入依賴中國)/ C(政策反向限制)分類;15 個 theme 入面 12 個補咗呢個披露(memory-supercycle、ai-power-grid、rare-earth-materials 等)。
- **4 條 backtest 驗證跑完並審**:sizing formula(margin-of-safety × convergence-speed)、institutional ownership crowding axis、buyback capital allocation signal、insider breadth/market ratio——結論落 `results/2026-07-11_*.md`,含 look-ahead 檢查 + market-cap tier breakdown。
- **Magnifier model**:`docs/2026-07-09_magnifier_model_plan.md`(supercycle-magnifier 特徵框架:operating leverage/supply discipline/distance-from-trough/moat durability/crowding)+ 3 本書蒸餾(Capital Returns、Expectations Investing、One Up on Wall Street,`docs/2026-07-11_magnifier_book_*.md`)。**scorecard 設計(D/E步)擺低等用戶面談**,唔自己砌。
- **IMA automation 解決**:daymade `ima-copilot` skill 裝咗(官方 wiki OpenAPI 實測攞唔到全文,淨係 IMA 自己個 chat 介面先做到真 RAG,人手操作);2026-07-12 四 model 對打(DeepSeek vs MiniMax-M3×2 vs mimo-v2.5-pro)確認 **DeepSeek 做主力**;4 條 weekly extraction prompt 定咗(`docs/2026-07-09_ima_extraction_prompts.md`,v3,加咗 folder citation + 匯出.md 要求);人手週度任務落咗 STATUS.md 上表,新 session 開波會見到。
- **WS4 基建接線**:`thesis/theme_signal.py`(每主題 buy-zone/wait/kill-watch)+ `backtest/basket_temp.py`(cap-weighted heat vs equal-weighted breadth vs dispersion)兩者已入 `daily_playbook.cmd` 排程。`thesis/prefetch_transcripts.py` resumability 由「檔案存在」改埋「corpus.db 已 index」雙重判斷(避免刪 raw cache 之後重複下載)。
- **夜班 permission boundary 問題浮出並修好一單**:headless run 寫唔到工作目錄外(`../Reference/`)→ 07-11 iron-butterfly 63/64 addendum stage 咗喺 `.agents/nightshift_pending_writes.md`,今日日間 session 過檔完(`Reference/distillations/2026-06-24_backtest-everything-distillation.md` + `_PENDING_ANALYSIS.md` 已更新),stage 檔已刪。
- **90 個檔案 backlog 今日 commit**:scratch/intermediate(`_scratch_group*/`、`_groupA_context_quotes.txt`、`exp_groupC_radar_pull_output.txt`、sizing validation 中間 csv、nightly log、ticker cache)已收入 `.gitignore`,唔再係 untracked noise。
- 未閉:corpus 一個 data-hygiene bug(`transcript-WST-2023-11-10` 錯標做 Westrock Coffee,未重抓/重標);`exp_insider_validate.py` 舊 script 嘅 fat-finger price bug fix 未搬(新 `exp_insider_breadth.py`/`exp_insider_market_ratio.py` 已修);dashboard + magnifier scorecard 繼續擺低等用戶。

## 現在在哪(2026-07-06)

**2026-07-06(Fable 重做 session,真數據)—— 任務 1-3 獨立重做完成;core 策略 v2 定稿:**
- 背景:用戶發現 sandbox Fable run 斷網(proxy-IV/SPY-only)→ 下令棄用其產出、由任務 1 重做。本機
  已證 yfinance 全通(SPY/QQQ/SPMO/^VIX/^VXN)。
- **任務 1**(`docs/2026-07-06_wiki_verification_v2.md`):4 個獨立驗證員追溯 ~124 claim + code 級核對;
  修 18 處(Mag7 誤降級、符號灌水、spine RSI-2「裸奔」披露、insider P0-1 披露、幽靈引用等);驗收 PASS。
- **任務 2**(`docs/2026-07-06_gap_conflict_register_v2.md`):20 項;P0 修咗 3(**ROADMAP A3 insider
  修法方向寫錯 21d→已更正做細價 12月 portfolio**、STATUS 殘留 credit 待辦、ARCHITECTURE 內部矛盾);
  3 個孤兒補跑落檔(rotation 非 duplicate + bonds>cash 發現;minervini PARTIAL 弱;vol-timer 細價 ❌);
  code P0(conf_eff 未接分、校準迴路斷)登記排期 = ROADMAP A1/A3。
- **★ 任務 3 core 策略 v2**(`docs/2026-07-06_core_strategy_v2.md`;證據:`results/2026-07-06_
  leap_real_sweep / core_assembly_real / core_topup / sector_capeff.md`):**底倉 SPY + LEAP 引擎
  (SPY+QQQ 對半、純 200SMA 閘、b15% premium、月度 top-up)+ 現金 ^IRX**。真數據 α:**保守 model
  +6.5pp/yr(t3.1)/ base +12.4pp(t5.4)**,MaxDD ≈ SPY。推翻 v1:0.80Δ 全格贏(RV-proxy artifact)、
  dip 閘(miss V 反彈)、遲滯(無淨值);**月度 top-up 係機制核心**(修 40-60% cash-starved)。
  板塊三假設真數據 control-leg 全滅(恐慌買殘板塊顯著負 t−2.52)。Bonferroni×42:base 過(2.4e-6)、
  保守 model p=0.095(過 0.10 唔過 0.05,如實記)。全部經 adversarial 覆核(opus)+ 獨立重跑驗證 PASS。
- **Phase-3 設計 session 已完成(2026-07-08,Fable)**:五份 WS 規格 + 全局架構 + 執行 backlog 全部落檔
  —— 入口 = `docs/2026-07-08_phase3_architecture.md`(→ ws1 裁判/ws3 生命週期/ws4 早期偵測+儀錶盤/
  ws2 危機sleeve/ws5 表達注碼)。四個實證探測:constraint-language ✅(早敘事17個月)/insider-cluster ❌
  /crisis event-study(右側 ARM→ENTER,n細誠實標)/80 源 altdata 普查(top-5 probe)。
- 下一步:**執行 Batch 1(WS1+WS3 地基)** → Batch 2(儀錶化)→ Batch 3(probes/接線)→ dashboard
  (任務 6,WS5 §5 需求)→ 任務 8 sweep(≥50% 非 AI)。Core 接線 to-do 見策略檔 §7。
  夜班分析任務等用戶授權(見上表)。

**2026-07-06(Fable 5 sandbox session)【產出已全部 SUPERSEDED,留檔可溯】—— 舊記錄:**
- **任務 1 wiki 驗證**(`docs/2026-07-06_wiki_verification.md`):34 份 results 全數追溯;wiki 修 13 處
  (§5.2 誤植 F&G 數、credit 新舊結論並存、VIX>30 untraceable、+12.5% 補 DSR caveat、insider 大型股 2022+-only)。
- **任務 2 gap/衝突**(`docs/2026-07-06_gap_conflict_register.md`):6 份 doc 修 10 處;code 審計 12 條
  (vol-switch「已 live」係假、2D 閘只有 input 無 quadrant 邏輯、雙 logger 寫同一 track_record、params↔code 唔對辦);
  **補跑 LEAP delta sweep**(`results/2026-07-06_leap_delta_sweep.md`):**0.80Δ deep-ITM 全面贏 0.3/0.5/0.7**
  (theta ×8 冚死槓桿 ×2.4;「0.3 最好」記憶 = short-call 條腿)。
- **★ 任務 3 core 策略 v1**(`docs/2026-07-06_core_strategy.md` + `results/2026-07-06_core_portfolio_loops.md`,
  4 輪 loop、30 trials、fresh-eyes 驗證通過):**底倉 70-75% SPY(永不趨勢沽)+ 遲滯閘 LEAP 10-15%(0.80Δ,
  >200SMA×RSI-2 dip 入、<0.98×200SMA 五日出)+ 現金 15% + covered-call skim**;2D 象限 transition 表 +
  每日 playbook。**對 SPY B&H(TR、HK 稅後):α +3.4~5.9pp/yr(E1 t3.7 過 Bonferroni+DSR 0.983;E2 邊緣)、
  β≈1.0、MaxDD −44~45%**。板塊輪動唔入 core(0/28/TAA 輸);washout = 確認尺唔係分枝;
  幅度 MEDIUM(RV-proxy IV、SPY-only)→ 本機真 VIX 重跑清單喺策略檔 §7。
- **任務 5 驗證**:獨立 agent 重跑逐位吻合、look-ahead 全過、benchmark 公平;4 個表述修正已落實。

**2026-07-06(Vanessa session)—— Phase-2 收官 + Trend-Core value-chain 更新 + Fable 交棒:**
- **Phase-2 大市層 flow 收官**(`results/2026-07-05_phase2_flow.md` + `_breadth_reversion.md`):DIX(慢 tilt,配 GEX)
  + **breadth 洗盤 reversion**(底 decile / ≤27% above50 → 21d +2.58% ≈3× baseline、短線 over VIX +2pp、**單邊**——
  洗盤會彈 / 見頂唔會即插、做空頂實證冇值、減 drift 後仍然;對實際股災底 GFC/COVID/2011/2022/2025 核實)。**修正**舊
  「breadth 冇用」(嗰個只對 LEVEL 線性成立)。淨結論:大市層 flow ≈ VIX 冗餘,只 DIX + 洗盤兩個小 tilt 加值 → 收官。
  餘下(板塊/子板塊 breadth + 背離 + 群體行為;大市層背離已證冇用)= Phase-3 rider,需 value-chain 成份定義。
- **Trend-Core(gooptions)re-scrape = Phase-3「3b 發現」loop**(commit `50bcb2e`):抓新 9 篇 #138-146 → 更新 5 個
  value-chain wiki。**AXTI「唯一便宜錨」糾正 3 處**(#141 蝕錢 / fwd PE 72.8× / 峰值盈利假象);新節點:光纖耦合、
  冷卻內化、HBM base-die 代工、tpu interactive;tpu 護城河再定義=「開源模型 GPU-shaped」非 CUDA。9 個 confidence 全部不變。
- **LEAP 擇時 = alpha 機制釐清(用戶點明)**:指數擇時分兩種——SPY 現貨 1:1 入出贏唔到 Jensen alpha(結構拖累中和 T1);
  **但 LEAP call(槓桿 + 非 benchmark 工具)= 唯一結構解**(finding #12),擇時有價值、曝險可低、槓桿放大真 +T1;
  代價 = 尾部風險,必須閘(>200SMA × RSI-2 dip × 恐懼)。→ core 期權層真.alpha 機制。
- **★ 下一步 = Fable 5 交棒**(見「下一步」+ `docs/2026-07-06_fable_brief.md`)。

**2026-07-05(Vanessa session)—— 風控/擇時層全面回測 + ebooks 蒸餾。4 份新結果檔 `results/2026-07-05_*.md`:**
- `fg_timed_capital_efficiency` · `meanrev_family` · `factor_families_momentum_lowvol_rs` · `breakout_momentum`
- **核心定案(高信心)**:
  - **價量/擇時層 = 風控/timing,唔係 alpha**(全面再確認)。**Capital-efficiency 係真但細嘅 T1 擇時 alpha**
    (`exp_alpha_decomp` T1 +2-6%/yr),兌現要靠個股表達/多-sleeve portfolio;大 alpha 仍靠 Phase 3。
  - **Momentum**:粗糙 SMA 誇大咗;正版 TSMOM = **downside protection(H2/跌浪先顯,H1平穩牛≈B&H)**;
    **最佳 timer = 20日高突破 > TSMOM > SMA**(兩半贏、修 H1;修返用戶「月lookback太慢」)。**已測未接線。**
  - **Mean-rev(RSI-2)**:regime-gated(高波)+ cap-gated(**micro dip=落刀**)+ **RS-leader filter 救返 H1 脆弱**。
  - **RS**:選 leaders 穩健(選股)、gate RSI-2(filter);LEVEL 係 edge、TREND 只對 dip-filter 反向有用。
  - **Low-vol/Vol**:低波選股非 alpha(防守);vol = **regime gate** 唔係引擎。
  - **突破 SELECTION(Minervini)/ risk-layer**:price-only 版無 alpha;**止蝕/trail 斬贏家傷回報 → 封尾部生存唔係 alpha**(caveat:無成交量確認未測)。
- **ebooks 蒸餾**:`ebooks/Discretionary Momentum/DISTILLATION-backtestable-rules.md`(O'Neil/Darvas/Livermore/Minervini common core + SPEC A-D;**在 Karst repo 外**)。
- **大市 2D regime 定案**(`results/2026-07-05_market_regime_2d.md`):**credit(HYG/LQD)做風險軸 = 失敗**
  (regime 反覆、對 VIX 無增量);**改用「VIX × 趨勢(200SMA)」2D = 成立**——② 牛市+高VIX 兩半前望最好
  (+5%)+ 回撤最淺,∴ **買恐懼優先喺上升趨勢做**;熊市買恐懼細注(方向 regime-dependent)。VIX 主軸、
  趨勢做安全度修正器。
- **未閉 gap**:突破加成交量確認(救 Minervini selection?);VCP 型態本身未測;GEX(Phase 0 fragility)未建;
  gamma 牆 + BofA Bull&Bear + trend×VIX 大市閘 forward-log。

**2026-07-04(Vanessa session,於 Claude Code 續)—— 詳見 `docs/2026-07-04_progress_and_next.md`:**
- **定位更正**:Karst = 獨立、自足系統(非三大腦執行臂、edge 不外包);`README`/`ARCHITECTURE`/`KARS_MEMORY`/`AGENTS` 已清 framing。
- **Backtest 全盤點完成**;insider + 四大家族重跑並存檔(`results/2026-07-04_insider_family_revalidate.md`,S&P500 離線版:RSI-2 long-only **+12.5%** 重現;insider 大型股 21d t2.30 / 63d t2.91,DSR 0.79)。兩者**未到「高」**(insider 只大型股;family 有 survivorship)。
- **修咗實驗檔 2 bug**:`_DATA` 路徑(reorg 後指錯)+ None 價格快取永不重抓。**weekly cron 冇壞**(寫 `thesis/`,未搬)。
- ⚠️ `px_defeatbeta.pkl` 全 None(死快取);sandbox 上唔到網攞唔到小型股價 → 需**本機 defeatbeta 重抓**(bug 已修,一 run 即補)。

**2026-07-03:**

- **已建**:spine Phase 0/1/4(市場閘/板塊/擇時,`python backtest/scan.py`)、
  thesis 9 主題 + forward-IC 每日排程、web dashboard(`web/`,可部署)、
  insider EDGAR 家族、20+ 回測結論(`backtest/results/`)。
- **剛完成**:全系統審查(`docs/2026-07-03_*.md` 三份)→ 抓到 **P0 級接線問題,
  未修**:① insider `conf_eff` 算了但從未接回分數;② credit 軸/兩軸背離已驗證卻
  完全缺席;③ 校準迴路是斷的(outcome 回填程式不存在);④ IC≥0.05 只是文字非程式。
- **已核准開工**(用戶 2026-07-03):`docs/ROADMAP_AGENTIC.md` 全部。
- **用戶事實**:香港稅務居民(無 CGT、美股股息 30% 預扣)→ 稅後比較用 HK 參數。
- **workspace 已重組**(2026-07-03):37 個實驗檔移入 `backtest/experiments/`
  (含索引),本檔成為唯一入口。

## 下一步(2026-07-12 更新)

Discovery Radar + China audit + 4 條 backtest 驗證 + IMA automation 已完成收尾(見上「現在在哪」)。
2026-07-12 已查證:WST transcript 錯標 + insider fat-finger bug port-back 已修(commit `242f74b`);
**Batch 1(WS1 裁判狀態機 + WS3 生命週期)實測已全套跑緊 live**(`forward_ic.py` judge() 出
PRELIMINARY、`lint.py` admission gate 0 error、`thesis/migrate_track_record.py` 已 run 過)——
07-06 嗰個「未驗證」擔心係多慮,程式碼早已到位,唔止係 design doc。
按優先:

1. **等用戶面談**:magnifier scorecard(D/E步設計)、dashboard 接線——用戶已明確話擺低,唔自己砌。
2. **Batch 2 剩餘缺口(2026-07-12 查到嘅唯一真.gap)**:WS3 #3-4「集中度報表 + beta 化月檢」
   (`thesis/concentration.py`、`thesis/beta_check.py`)兩個工具**已寫好、可以跑**,但**未排入任何
   排程**(唔喺 daily/weekly .cmd 入面,亦冇喺 STATUS.md 自動化表出現)——形同得個藥冇食。建議下一步
   將呢兩個工具接入月度排程(或至少人手每月跑一次 + 落紀錄)。
3. WATCH 4 隻票(KALU/MCHP/AVT/PTEN)——已排低,下季 review。
4. Batch 3(altdata probe/TWSE job/insider P0-c 接線/dashboard)——未動工,排喺 Batch 2 缺口之後。
5. 人手週度 IMA 任務(見上表)持續行。

### (2026-07-06 Fable 完成後更新,部分已執行)

**Fable 交棒任務 1-8 全部完成**(交付檔見「現在在哪」)。下一步按優先:

1. **本機重跑(升 core 策略幅度 MEDIUM→HIGH)**:真 ^VIX + QQQ 重跑 delta sweep + loop3/4 headline
   (command 喺 `results/2026-07-06_leap_delta_sweep.md` 檔尾);之後先郁真錢。
2. **Phase-3 開錶前 5 修**(`docs/2026-07-06_phase3_methodology_review.md` §3):#1 統一雙 logger +
   outcome 回填(M)→ #2 PASS/FAIL 程式化(S)→ #3 裁判 reframe(hit-rate@20-30 outcomes 做近期主裁判,S)
   → #4 conf_eff 接或刪(S)→ #5 thesis_valuation.py 起碼版(M)。**未修 #1/#2 前,錶行極都冇數**。
3. **接線(策略樹要用)**:2D quadrant + 遲滯閘入 spine(gap register C5)→ dashboard P0 面板
   (`docs/2026-07-06_dashboard_design.md`;注意新發現:repo 冇 position tracker,要起 positions.json)。
4. **Phase-3 闊度 pipeline**:由 `docs/2026-07-06_bottleneck_candidates.md` 頭三名(SRM 彈藥/LNG 船/航空 MRO
   ——揀佢哋因為去相關)起 value-chain wiki;目標 ~30 個去相關主題。
5. 衛星紀律:校準迴路未通之前,Phase-3 注碼 ≤20%、confidence 上限 ≤0.40。

**策略主線(研究層,仍有效)**:風控/擇時層特徵已徹底釘死(見上)→ **重心轉 Phase 3 thesis + forward-IC**(唯一 alpha 門)。
**可選接線**(風控層):① 20日高突破 timer 入 `spine/timing.py`;② RSI-2 × RS-leader gating;③ vol/VIX regime 開關。
**可選補測**:突破 + 成交量確認(唯一未閉 gap);VCP 數值代理;GEX(Phase 0)。

---

### (2026-07-04 下一步,仍有效)

**即刻(Vanessa 本機,有 defeatbeta):** 2 bug 已修,run 以下即補小型股價、重現全宇宙:
```
python backtest\experiments\exp_insider_validate.py
python backtest\experiments\exp_family_validate.py
```
完成後更新 `results/2026-07-04_insider_family_revalidate.md`(全宇宙 insider 預期 21d t≈5.12)。

**升級到「高」(rigor):** ① 選股類 point-in-time 除 survivorship;② 期權類 BSM+成本+walk-forward(到中高,無真實期權鏈);③ VCP + 大盤擇時補存檔;④(可選)出總表:測咩｜結果｜可信度｜點升級。

**清理(可選):** `reference/README.md`、`invariants/`、`params/` 殘留的 Compass / 三大腦 framing。

---

### (前 ROADMAP Phase A/B 次序 —— **部分已過時**,以 `docs/ROADMAP_AGENTIC.md` 為準)

1. **A1 校準資料流**(統一 track_record schema + `log_predictions` 進排程 +
   outcome 回填)——每天不修就流失一天不可補的資料【仍有效】
2. **B1 持久化價格庫**(parquet + as-of manifest)——與 A1 並行【仍有效】
3. ~~A2 credit 軸+兩軸背離~~(**已作廢** 2026-07-06:credit 07-05 測完剔除,A2 改為 2D quadrant 接線)
   → A3 insider 接線方向**已更正做細價 12 月 portfolio tilt**(舊「21d 戰術 tilt」regime-fragile,唔採)
   → B2 paper ledger(詳 ROADMAP)

## 東西在哪

| 要做什麼 | 去哪 |
|---|---|
| **懂整個系統(layman 全貌 wiki,由此入)** | **`docs/KARST_WIKI.md`** |
| ~~★ Fable 交棒任務書~~(已完成、已存檔)| `docs/_archive/2026-07-06_fable_brief.md` |
| 懂整個系統(技術版真相) | `ARCHITECTURE.md`(跨 Phase 地圖,single source of truth) |
| 風控/擇時層結算(標準化量度+逐訊號+決策矩陣) | `docs/2026-07-05_risk_control_layer_report.md` |
| 開工 roadmap | `docs/ROADMAP_AGENTIC.md`(A1-D6,含驗收條件) |
| 懂「為什麼要修/為什麼不做」 | `docs/2026-07-03_strategy_methodology_review.md`(P0-P3 + 反建議) |
| 改 dashboard | `docs/2026-07-03_dashboard_decision_experience.md`(逐面板規格+錨點) |
| 跑每日掃描 | `python backtest/scan.py [--json]`;dashboard:`web/README.md` |
| 找/跑/寫回測實驗 | `backtest/experiments/README.md`(37 實驗索引+慣例) |
| 回測結論 | `backtest/results/*.md`(dated;經 experiments 索引反查) |
| thesis 層操作 | `thesis/DESIGN.md` + `.claude/skills/thesis/SKILL.md` |
| 歷史決策/坑 | `.agents/KARS_MEMORY.md`(§1-10) |
| 期權/timing 參數 | `params/`(帶 ✅/📄/⚠️ tag;注意 PMCC 已於 v3.1 移除) |
| 風控鐵律 | `invariants/systematic_rules.md`(INV-5/8/9 已進程式,其餘文件層) |
| agent 工作制度 | `~/.claude/playbooks/`(調度/判斷/模板/維護) |

## 新 session 閱讀順序(按任務)

- **接續開發**:本檔 → `docs/ROADMAP_AGENTIC.md` → 對應程式碼
- **做研究/回測**:本檔 → `backtest/experiments/README.md`(慣例+索引)→
  memory `validation-mirror-and-increment`(鏡子/增量/horizon 三原則)
- **懂系統**:本檔 → `ARCHITECTURE.md` → `.agents/KARS_MEMORY.md`
- 2026-07-03 當日研究細節:`HANDOFF.md`(該 session 的詳細交接,已被本檔取代為入口)

## 維護規則

- session 結束:更新本檔「現在在哪/下一步」;新結論落 `backtest/results/` 或 `docs/`;
  重大決策/坑 append 到 `.agents/KARS_MEMORY.md`。
- `.agents/sessions/` 日誌已停用(2026-07-01 起由 KARS_MEMORY §8-10 + 本檔取代)。
- 別讓兩套入口再分岔:**AGENTS.md 的 Read-first 指向本檔,本檔指向其他一切。**
