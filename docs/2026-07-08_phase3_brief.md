# Phase-3 全面深化任務書 —— 交 Fable 行設計 loop(architecture + mechanism)

> **交俾 Fable 執行。你係大腦/orchestrator:想、派、審、決 —— backtest/research/coding 派俾平價
> sub-agent(sonnet 分析、haiku 機械),你只 review + synthesize + decide。溝通用香港白話中文
> (ticker/程式/技術名詞英文)。**運作模式 = 設計 loop**:每個 workstream 行
> Purpose → Research/Test → Enhancement → **Self-Review(adversarial:呢個機制頂唔頂得住反駁?
> 有冇 overfit?有冇量度唔到嘅嘢扮量度得到?)** → 收貨/再迭代。
> **產出 = 可執行規格**(schema/演算法/觸發條件/驗收條件),交返俾日常 session 執行。
> 每個結論落檔;只喺對話裡 = 未完成。設計期唔准直接改 production code(spine/scan)——
> 規格檔 + 原型 script 得。

---

## 0. 定位(一段講晒)

Phase 3 = 衛星資金(組合 30%,~$41k 起步、crypto 階梯觸發會增大)嘅大腦。NHITL:confidence
係證據推導 + 校準嘅數,唔係人嘅信念;全系統可證偽靶心 = **thesis 排序 forward IC ≥ 0.05**。
本 brief 嘅任務:把 Phase 3 由「9 個未校準主題 + 斷咗嘅裁判」深化成一部**發現得早、收編得嚴、
計分得真、退場得果斷**嘅機器。

## 0.5 現況快照(2026-07-08,唔使自己重建)

- **已有**:9 個 Type-B 主題(`thesis/themes.yaml` + wiki 頁,4-KPI cited);corpus.db(FTS,115 篇
  gooptions 研究);source-node 圖層;insider EDGAR 管線(**display-only**);forward-IC 每日
  05:30 log(schtasks);gooptions 每日 05:35 自動抓 + 05:45 transcript 抓 + `_PENDING_ANALYSIS.md`
  隊列;`ai-capex-macro-risk.md` 宏觀監察頁(五盞燈)。
- **斷/缺(code 已核實,gap register v2)**:
  - **P0-d 校準迴路斷**:兩個 schema 唔一致嘅 logger 寫同一 `track_record.jsonl`;outcome 回填
    程式全 repo 不存在(`log_predictions.py:64` 永遠 None);`forward_ic.report()` 無 PASS/FAIL
    程式判定(IC≥0.05 只喺 docstring)。
  - **P0-c insider 接線斷**:`conf_eff` 計咗從未入 score(`spine/expression.py:66` 只用
    `thesis.unit`;`spine/__init__.py:13` code 自認)。**修法方向已更正(07-06):細價 <$2B
    12 個月 portfolio tilt vs IWM,舊 21d 版 regime-fragile 唔採。**
  - **A 型危機 sleeve 未建**(🔴)。
  - **發現單源**:9 個主題基本上全部由 gooptions 語料生出。
- **結構性弱點(用戶 07-08 點名)**:
  1. 9 個主題冇一個喺 early 階段捕獲(8 late/mid;「發表咗嘅研究」天生滯後)。
  2. 6/9 主題掛喺同一注 AI capex(集中度炸彈;BIS 情境一發生齊死)。
- **用戶取態**:core/衛星 70/30;新錢跟新制度;偏好 ETF 表達多過個股;真實 NAV ~$346k
  (crypto 61% 獨立倉,詳 `2026-07-08_transition_plan.md`)。

## 1. 鐵律(不可違反;全部沿用 repo 現行)

1. **誠實結論授權**:證據話唔得就照直講;唔准為交貨砌唔存在嘅機制。「量度唔到」係合法答案,
   但要講埋 fallback。
2. **Cited everything**:每個 claim 有來源;Tier 1/2/3 分級;報告 bullish 本身 = 擁擠訊號。
3. **Multiple-testing 紀律**:任何掃描/回測報 trial 數;Bonferroni/DSR;n 細嘅嘢(A 型)用
   事前框架+kill 驗,唔准扮有 t-stat。
4. **NHITL**:設計每個機制時問「呢度有冇一步要人喺迴圈入面?」有就要嗎自動化、要嗎明文標成
   人工閘(愈少愈好)。
5. **MVP 護欄(DESIGN §7)**:做到能自動跑就上線→部署→迭代;無限完美化 = 死穴。每個 WS 要
   時間盒。
6. **落檔 + 白話**;驗證不自驗(做的 agent ≠ 驗的 agent)。

## 2. 必須尊重嘅已定案(唔好重推;可用新證據挑戰)

- Forward IC ≥ 0.05 做判官(oracle 獎勵曲線凸:0.05 贏 SPY、0.10 ≈ 2×);量化因子排板塊 0/28
  —— 質性係唯一未測源。
- Insider 修法 = 細價 12 個月 portfolio tilt(唔係 21d);大型股 21d edge 係 2022+ regime artifact。
- 恐慌買殘板塊 @VIX>28 = 顯著負(`sector_capeff` H2 t−2.52);A 型嘅門檻/定義必須同呢個
  結果劃清界線。
- 板塊層價量輪動判死;年度敘事 = Phase 3 嘅工作。
- Core v2 唔郁(佢係另一個世界;本 brief 只管衛星)。
- 用戶鐵律:唔做短 DTE OTM;tier-2 只 long-only。

## 3. 五個 Workstream(每個行設計 loop;WS1 最急)

### WS1|裁判修復(校準迴路 = ROADMAP A1)★ 最優先
設計:單一 writer 超集 schema(遷移舊 jsonl 點做?);outcome 回填 job(21/63/126d 實際回報 +
kill 有冇觸發,由價格歷史補;point-in-time 紀律);`forward_ic.report()` 狀態機
(PRELIMINARY/PASS/FAIL,JSON 機讀,樣本量門檻);confidence 校準映射方法(講 0.7 應該 ~70% 中
—— 用乜方法?幾多樣本先開始?);decay 偵測/circuit-breaker(rolling 背離 → 停 sleeve 嘅具體
規則)。**驗收:設計通過後由執行 session 實作,每日 log 完整 schema、首批 21d 到期自動回填、
report 機讀。**

### WS2|A 型危機救援 sleeve(日級時鐘)
設計:觸發三元組操作化 —— VIX 門檻(>40 定分級?收市定盤中?)× 「系統性板塊」定義(邊啲板塊
算 too-big-to-fail?「被打爛」= 幾深回撤/乜嘢排名口徑?)× **政策訊號點量度**(呢個係最難嘅
設計位:聯儲/財政部行動點變成機器讀得到嘅訊號?定係承認要人工確認 = 明文人工閘?)。
用 ~8-10 個歷史案例(1998/2001/2008-09/2011/2015/2018/2020/2024-08/2025-04)event-study 驗證;
sizing 上限 + kill + 唔對稱 payoff 檢查;dashboard 警報規格(餵任務 6)。
**同 M1(VIX>28 買 SPY,α≈0 discipline)同 H2 陰性結果嘅分界要白紙黑字。**

### WS3|主題增量機制(發現→收編→退場)
設計:admission gate checklist(4-KPI cited + kill + priced-in/週期閘 + 可交易表達 + INITIAL
confidence 即日入戰績簿)—— 寫成機器可檢查嘅 lint 規則幾多、人工判斷幾多?退場規則(kill 除牌
/ THIN 主題 N 月冇新證據降級 / 退化成 beta 除牌 —— N 同「beta 化」點定義?);單一來源 flag →
confidence 上限(幾多?);主題間集中度量度(共同因子曝險點計?AI-capex 呢類 meta-factor 點
tag?)+ 發現配額傾斜非 AI;注碼預算固定下嘅競爭上崗規則(confidence 排名 → sizing 映射)。

### WS4|早期偵測(B 型要早唔係要快;月級時鐘)
設計:(a) **insider 群買 → 主題發現輸入**(cluster 定義:幾多個 insider/幾長窗口/邊啲行業樣本
夠?同 P0-c 修理嘅關係);(b) **constraint-language 掃描**:corpus FTS 跨板塊掃「lead time/
allocation/提價/sold out」語言 —— 詞表點建?雜訊點濾(df 收割 anti-noise 原則)?定期 job 規格;
(c) value-chain 成員地圖基建(先邊幾條鏈?格式?)→ 細板塊群體行為偵測(方向已認可未測);
(d) FNSPID 事件引擎薄版 —— **時間盒,驗證「有冇用」先,唔准工業化**。
每個子項要答:訊號提早幾多?誤報率點控?去邊度接入 admission gate?

### WS5|表達與接線
審 `ThesisVerdict → spine thesis_quality` 現況(score 公式);cold-start 期 confidence → sizing
映射(cap 細注幾細?);ETF vs 個股表達規則(用戶偏好 ETF —— power-basket 研究係範本:
`2026-07-08_power_etf_basket.md`);dashboard 需求清單(A 型警報/主題面板/pending 隊列/裁判
成績表)→ 餵任務 6。

## 4. 交付物

1. **每 WS 一份機制設計檔**(`docs/2026-07-XX_phase3_ws<N>_<topic>.md`):可執行規格級 ——
   schema/演算法/觸發條件/參數/驗收條件/時間盒;含 Self-Review 段(反駁過乜、點頂住/點讓步)。
2. **全局架構檔**:數據流圖(發現源 → admission → registry → 表達 → 戰績簿 → 校準 → sizing
   → dashboard),邊嚿係已有 code、邊嚿新建、依賴次序。
3. **執行 backlog**:逐項帶驗收條件同優先次序,交返俾日常 session 執行(執行時照
   playbooks/10-dispatch 派工 + 驗證不自驗)。
4. 若設計途中發現「呢樣要真數據先答到」—— 派 sub-agent 即場跑(本機 yfinance/EDGAR/corpus
   全通),結論落 `backtest/results/`。

## 5. 唔喺 scope 入面

Core v2(已定稿)、dashboard 實作(任務 6 用你嘅需求清單另做)、任務 8 第一輪 sweep 執行
(用你設計嘅機制去行,但行係執行 session 嘅事)、修 production spine code(執行階段先動)。
