# Phase 3 — Thesis 層設計(質性 offense,NHITL)

> 本檔是 2026-07-01 一整晚設計 session 的收斂記錄(20+ backtest commit 的實證 + 逐步壓力測試 +
> 知識層/NHITL 架構討論)。Phase 3 尚未實作;這是定案的設計藍圖。技術識別碼/ticker/檔名/函式名保留英文。

---

## 0. 定位 & 為什麼(實證地基)

本 session 的 20+ 個 backtest(見 `backtest/results/2026-07-01_*.md`)實證釘死:**price/volume 量化
forward IC ≈ 0**(線性 Alpha158 + GBDT/Alpha360 + 板塊輪動,全過多重檢定 + walk-forward)= **風控,
不是報酬 alpha**。逆向工程 oracle 定位出可捕捉的 edge:

- **事件驅動**:top-20 非科技單週 gap **每一週都對得上一個有名有姓的宏觀催化劑**(GFC 銀行紓困、
  俄烏/OPEC 油衝、疫苗重啟、崩盤防禦、911)——見 `results/2026-07-01_gap_forensics.md`。
- **regime 驅動**:逐年主導板塊 = 可辨識宏觀敘事;yearly-hold oracle ≈ 2× SPY。
- **skill-curve**:forward IC 0.05 就淨贏 SPY、0.10 翻倍(報酬對排序技巧極度凸)。

**統一結論:edge 是「價格圖裡沒有的資訊」**(「OPEC 減產」「疫苗成功」「多年不投資」活在新聞/
基本面/供需裡)→ 質性問題 = Phase 3。它填 `spine/providers.thesis_quality` seam,把 tier-2 個股分數
從 0/100 資格變成 **資格 × confidence**。

---

## 1. NHITL 系統:把人拿出迴圈(核心對齊)

原始目標:**執行層全自動、no-human-in-the-loop**(理由:人會 FOMO/報復/悶——POET/RGTI 教訓;系統
存在就是要拿掉人的情緒)。所以「靠人的信念」是系統要**消滅**的失敗模式,不是 edge。四個元素**全可量化**:

| 元素 | 可算? | 進系統的方式 |
|---|---|---|
| **分類** | ✅ | regime(VIX/利率/通膨→cell)、板塊/子板塊、cycle-stage、event-type、A型危機(VIX>40+超賣系統板塊) |
| **夠早 / priced-in** | ✅ | 估值分位(自身歷史+產業)+ 供給回應(capex 轉向)+ 擁擠(新 thematic ETF 上市/資金流) |
| **風控** | ✅ | invariants INV-1..9 + kill condition + sizing 規則(`invariants/systematic_rules.md`) |
| **confidence**(不是「信念」)| 🟡 大半可算+校準 | 見下 |

### confidence(不是 conviction/信念)
換這個字是**紀律不是語意**:信念=人的情緒信仰(黑箱、FOMO 溫床、NHITL 要拿掉);**confidence=從證據
算出、可分解、可稽核的確定度**。
```
confidence = f( 4-KPI 各分數, 佐證獨立來源數, 距 kill condition 多遠,
                payoff 不對稱比, regime 契合度 )
   → 對 track record 校準(說 0.7 就該長期 ~70% 命中)成真機率
   → 部位大小(sizing)
```
- **沒有一格是「我覺得」,每格溯回證據**(跟「每個數字有出處」+ wiki 引用紀律同源)。
- **必須校準**:uncalibrated 只是個數字,calibrated 才是真機率。校準靠 forward-IC / 戰績簿(§6)。
- **知識層(§5)的存在,就是把 confidence 算得可追溯 + 可校準的機器**——這是 NHITL 的實現,不是分心。

### 唯一的人 / 嚴格閘
原始設計已分清:執行層全自動;**採納「新 thesis 類型」進系統**要過驗證閘(deflated Sharpe / walk-forward
/ forward-IC track record——人或嚴格自動)。日常運作(分類→confidence→sizing→risk)全自動;人只在
「要不要納入一個全新玩法」時簽字,且該閘也可嚴格自動化。

---

## 2. 兩型 offense(實證識別)

- **B(主力)— 主題超級週期:** 供給受限 + 需求爆發 + 定價權 + 催化劑(能源 2021-22、Memory 2026、
  GLP-1、AI-電力/銅/鈾)。→ value-chain + bottleneck 的工作。**這型 = 讀供需+定價權。**
- **A(尾部)— 危機救援:** VIX 極端(>40)+ 被打爛的「too-big-to-fail」系統板塊 + 政策 → 均值回歸暴力
  反彈(GFC 金融、COVID)。稀有、半可規則化(見 `results/2026-07-01_gap_forensics.md` 已驗:2020-04-03
  XLE -36% 前值 / VIX 66 / 排名最慘 → 爆)。**這型 = 讀恐懼+政策,VIX+回撤可算。**

---

## 3. B 型生命週期機制
`發現 → 假設 → 偽證 → 估值(priced-in?) → 週期位置 → 表達 → 追蹤`

**週期位置(進/持/出)——到頂 = 三訊號齊發:** 估值極端(頂 PE 分位)+ 供給回應(capex 從紀律轉狂飆)
+ 擁擠(新 thematic ETF 上市——DRAM 訊號雙重意義:確認+晚期——賣方一致、資金湧入)→ PE 均值回歸 →
出。**進 = 鏡像**(便宜/合理 + 供給仍受限 + 尚未成共識)。

---

## 4. 4-KPI(Expectations Investing)
每條 claim **typed + cited**(quote+doc+date),照 `lenses/README.md` 的 Mark Douglas 蒸餾 pipeline:
1. **moat / bottleneck**(無替代 + 產能受限 + 定價權)— 逐字稿受限語言 + margins。
2. **資本配置 / ROIC**(`roic`、`ttm_fcf`、capex 趨勢)— 是創造價值還是軍備競賽(Mag7 CAPEX 恐慌例)。
3. **估值 / 期望值**(`ttm_pe` 分位,自身歷史+產業)— 風格相依(成長股看耐久非便宜;成熟股便宜是 tilt,
   已驗 `results/2026-07-01_valuation.md`)。
4. **成長耐久 / TAM**(additive-mechanism 閘:是否創造全新需求 vs 搶份額)。

---

## 5. 知識層(NHITL 的實現機制)

### 分層(關鍵:規模分層,markdown 不扛原料)
| 層 | 內容 | 技術 | 規模 |
|---|---|---|---|
| **原料語料** | 新聞 / 逐字稿 / 財報 | **SQLite FTS**(法律 MCP 16 萬判例已證)| 百萬級 OK |
| **綜合 wiki** | 概念 / value-chain / 公司 / thesis | **markdown + `[[]]` + git**(Obsidian 模型)| 幾千頁 |
| **介面** | 暴露 wiki/檢索工具 | **MCP server**(agent-agnostic:Claude Code / Roo / Codex)| — |

- wiki **引用進** FTS 語料(指向/查詢 + pin 關鍵引文),**不複製原料**。
- 一份報告是**來源**,不是頁;其論點蒸餾掛到多個概念/鏈頁,backlink 反查(解「一報告連多概念」)。
- 選 **claude-obsidian 的架構/慣例**(本地 markdown + `[[]]` + lint 矛盾偵測),**不綁其 Claude-Code
  skills**;借 llm_wiki 的**確定性圖相關性模型**(連結信號,非 embeddings)。

### 檢索(照法律 MCP `search.py`,確定性非向量)
`research_cases` pattern:**concept_groups(同義詞 OR)→ df 收割 terms-of-art(n≥2 才追,anti-noise)
→ 收斂 → concept-coverage 排序 → receipt**。兩個內建紀律**正好解兩大坑**:
- **df 收割 = anti-noise**(只追跨多事件反覆出現的 pattern,不追一次性巧合 → 防「LLM 幻想相似」);
- **concept-coverage(含 regime 描述子)= regime-conditioning**(regime 也對上的類比排前面);
- **good-law/treatment 機制**(工具給證據、LLM 在脈絡判)= 判斷「這類比對現在 regime 還算不算數」
  (法律叫 distinguished/overruled)——證據源從「treatment 句」換成「計算的 regime 特徵」。

### 事件引擎(唯一值得早做的重基建)
歷史事件類比 → **regime-conditioned base rate**,解「新事件 n=1、驗證太慢」。語料 = **FNSPID
(1999-2023、15.7M 新聞 + 29.7M 價格、已對齊、2025-07 釋出商用)** —— 直接補上 defeatbeta 新聞只有
15 個月的死點。**先做薄版**(一種事件型、FNSPID 一小片、手動 regime-condition)驗證有沒有用,再工業化。

### 原料分級(Tier — 權威等級)
- **Tier 1 一手**:逐字稿 / 財報 / 實際價量 / 財務數據 → 真證據。
- **Tier 2 意見**:分析報告 → 待驗證的 claim,標「analyst view (to verify)」,不是真理。
- **Tier 3 訊號**:新聞 → 事件/時機偵測、廣度、雜。

### 資料源現況
- **defeatbeta**:`news()` 只 2025-03 起(~15 個月,太淺,只當「當前偵測」);`earning_call_transcripts()`
  / `ttm_pe`(長日線)/ financials 可用;無 sector 分類(用 yfinance)。
- **FNSPID**:歷史新聞語料(1999-2023),歷史類比的地基。待驗:全文粒度 + 時間戳 point-in-time。
- 歷史類比也可用**價量異常 + regime 特徵 + 已知宏觀事件**建(不全靠新聞)。

---

## 6. 驗證(不是 backtest)—— 戰績簿 = agent 的自我監控 log,不是人的日記

**戰績簿是 agent 自己的、機器可讀、append-only 的「預測-結果」log,全自動(NHITL);人不用它做日常
決策。** 若人來讀來判「最近做得好不好」= 人回到迴圈 + recency/ego 偏誤 = 違反 NHITL。結構:
```
每個 thesis append:{時間, ticker/theme, thesis_id, confidence, cycle_stage, prediction(方向/幅度),
  kill_condition, entry 脈絡} → 之後自動掛 {實際 forward 報酬, kill 有無觸發, 實際 vs 預測}
```
系統自動從它算:
- **校準 confidence**:「說 0.7 是否真 ~70% 命中」→ 自動調 confidence 函數/校準映射。
- **流程層 forward IC**:連續排序 IC(長期累積,≥0.05 靶,1–2 年)= **背景健檢,不是下注閘**。
- **賭注層期望值 / 命中率 / CAR / kill 紀律**(B 型 payoff 凸:對=大贏、錯守 kill=小虧 → 命中率 40%
  也能大賺;~20–30 個才有話說)。
- **decay 偵測(自我修復)**:live vs 期望 rolling 背離超閾值 → circuit-breaker / 停 sleeve。
  **戰績簿就是 `invariants/systematic_rules.md` §自我修復 那層的實現**(機器檢查,非人)。
- **餵「新 thesis 類型」驗證閘**:新玩法的 track-record 過閘才准上 live-sizing。

**單一新事件當下沒有 IC 可算(n=1)** → 用事前框架 + kill 護欄驗(供需真嗎?priced-in?kill 設了?
Bull/Base/Bear?),不是數字;數字之後從戰績簿累積。**人唯一碰戰績簿的地方 = 「採納新 thesis 類型」
驗證閘上的一份衍生摘要(且該閘也可嚴格自動化)。** 另:**矛盾 lint**(wiki 層)= 新 claim 跟舊的矛盾
→ 偽證/一致性紀律。

---

## 7. 護欄(重新校準)
- 陷阱**不是「建這個系統」**(那是 NHITL 目標)——**是「無限完美化、永不上線、永不部署資本」**
  (Charter 的「方法論救贖」死穴)。
- 守則:**做到能自動跑就上線 → 部署 → 迭代 → 校準**。MVP 精神。
- 目標是「不再需要忍」,不是「建一個完美研究系統」;系統是工具,不是目的。

---

## 8. 接回 spine
輸出 `ThesisVerdict {verdict, confidence, cycle_stage, kill_condition, source}` →
`spine/providers.thesis_quality(ticker)`(取代 neutral stub)。tier-2 個股分數 = 資格 × confidence;
confidence → sizing。tier-1 ETF 期權不變;+ A 型危機 tail sleeve(VIX+回撤規則)。

---

## 9. 建造順序(lean pilot 先,讓需求拉重基建)
1. **精簡先行(幾乎免費):** 4-KPI 檢查清單 + 一個 `[[]]` markdown thesis 頁 + web/LLM 研究 + 風控
   四件套(小注/認賠/贏大輸小/分散)+ 戰績簿。**現在就能開始有紀律地(紙上)下注。**
2. **pilot(端到端):** 一個主題(AI-電力/銅/鈾,或 GLP-1)→ 4-KPI → confidence 分數 → 一個 thesis
   頁 → 餵 `thesis_quality` → 看 tier-2 card 變化。建立模板(像 Memory 之於 spine)。
3. **薄版事件引擎:** FNSPID 一小片 + 一種事件型 + 手動 regime-condition → 驗 base rate 有沒有用。
4. **重基建(FTS 語料 / MCP server / 完整 wiki / 事件引擎工業化)只在精簡版證明「不夠用、漏主題、
   需要歷史 base rate」時才建——讓需求拉,別憑空推,且時間盒。**

---

## 10. 未決 / 待驗
- FNSPID 全文粒度 + 時間戳 point-in-time 品質(下載一小片實測)。
- confidence 各因子的權重 + 校準方法(要跑一段才有戰績可校準)。
- 「新 thesis 類型」驗證閘的嚴格自動化(forward-IC/track-record 閘的具體閾值)。
- MCP server 的工具面(照 VR `server.py` 的 pattern 設計)。
- 分類器(regime/cycle/event-type)的具體實作(規則 vs ML)。
