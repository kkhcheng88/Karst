# Crowding composite 污染 — ASML 文件類型錯誤令 euv confidence 0.47 變成假讀數

- 日期:2026-07-16
- 觸發:用戶問「we should be on the sizing v2 and euv corroborates?」→ 覆核 euv `corroborates:` 登記時發現
- 狀態:**發現已證實(逐格核到一手文件本體)。修法未定 —— D2 係 DESIGN 變更,等用戶拍板。**
- 相關:commit `0ac6f3f`(已核准 15/15 confidence migration)、`thesis/crowding_composite.py`、
  `thesis/confidence_formula.py`、`backtest/results/2026-07-16_redteam_euv_lithography.md`

---

## 1. 摘要

`euv-lithography-monopoly` 嘅 confidence **0.47**(用戶已核准、已 commit、已餵落 sizing v2)
**建基於一個壞咗嘅輸入**。

crowding composite 俾 euv 打 **2.8**(= 全書 15 個 theme 入面**最唔擠**),原因係 **ASML 最近三份
corpus「transcript」根本唔係分析員法說會**:一份係**記者會**、兩份係**IR 宣傳片**。parser 於是
將 **ASML 自己嘅 CEO / CFO** 同埋 **一個路透社記者** 當咗做「分析員」,數出 1 / 3 / 2 個人,
對比 ASML 自己 71 個季度穩定嘅 **9–20 個分析員** → 自身歷史分位 = 2.8(近乎歷史最低關注度)。

**紅隊當初係啱嘅。Gatekeeper 用咗一個由記者會同宣傳片推導出嚟嘅數字去推翻紅隊**,
並且將呢個推翻**當成事實寫咗入 `themes.yaml` 嘅 `corroborates:` 段**:

> 「報告自身『脫 cap 但 null-op』結論係誤判——用錯 crowding pctile 假設 ≥90,真 composite_pctile=2.8,
> 故本次登記後脫 cap 有效拉升 confidence 至 raw=0.469。」

呢句嘅 `真 composite_pctile=2.8` 就係假讀數本身。

> **要留意嘅荒謬性**:ASML —— theme 自己份 note 都寫明係「全市場最多人討論嘅半導體壟斷故事之一,
> 『未被發現』呢個溢價完全唔存在」、ttm_pe 98 分位 —— 喺系統入面讀成**全書最唔擠嘅標的**,
> 比 memory(24.8)、tpu(46.5)仲要冷門。而 specialty-siding(97.2)同 glp1-packaging(95.3)
> 就讀成全書最擁擠。**呢個排名本身就係 D2 嘅證據**(見 §5)。

---

## 2. 證據鏈(逐格已核)

### 2a. ASML 出席數序列 — 71 季穩定,最後 3 季插水

```
2006-2025:  9 – 20 個分析員,中位數 11,71 個季度無斷層
2025-07-16: 11   <- 最後一份真.分析員法說會
2025-10-15:  1   <- 插水
2026-01-28:  3   <- 插水
2026-04-15:  2   <- 插水(= 最新,驅動 pctile 2.8)
```

ASML 冇喺 2026 年失去 85% 賣方覆蓋 —— 佢係全球覆蓋最厚嘅 semicap 名。紅隊自己都引用咗
2026-07-15 Q2 業績會嘅大量分析員互動。**呢個插水唔可能係真。**

### 2b. 文件本體自報身分(決定性證據)

| 日期 | 開頭原文 | 字數 | 實際係乜 | parser 數到嘅「分析員」 |
|---|---|---|---|---|
| 2025-07-16 | "ASML 2025 Second Quarter Financial Results **Conference Call**" | 51,582 | ✅ 真.分析員法說會 | 11 個真分析員 |
| 2025-10-15 | (3 個 speaker,18 turns) | 8,566 | ❌ 短片 | `Christophe Fouquet` = **CEO** |
| 2026-01-28 | "Q4 full year 2025 financial results **press conference**" | 51,635 | ❌ **記者會** | `Toby Sterling` = **路透社記者**、`Sarah Jacob` |
| 2026-04-15 | "Hello, and welcome to ASML's Q1 2026 **results video**" | 9,263 | ❌ **IR 宣傳片** | `Christophe Fouquet`(CEO)、`R.J.M. Dassen`(CFO) |

- 2026-01-28 嘅「operator」= **`Monique Mols` = ASML 傳媒關係主管**(唔係法說會 operator)。
- 2026-04-15 嘅「operator」= **`Jim Kavanagh` = ASML IR 副總裁**,佢喺片入面訪問自己間公司嘅 CEO/CFO。
- **即係 defeatbeta 嘅 ASML 供稿喺 2025-07 之後轉咗文件類型** —— 由分析員法說會轉成記者會 / 宣傳片。
  日期係啱嘅(每季一份),但**文件種類係錯嘅**。

### 2c. parser 冇壞 —— 佢係喺唔啱嘅文件上盡咗力

反例(證明 parser 本身正常):

- **MPWR 2021-02-04**(fallback 路徑):數到 `Quinn Bolton`(Needham)、`Ross Seymore`(Deutsche)、
  `Tore Svanberg`(Stifel)、`Rick Schafer`(Oppenheimer)、`William Stein`(Truist)
  —— **全部真.賣方分析員**。✅
- **WOLF 2026-05-05**:`method=Operator`、Q&A 正常解析、2 個真分析員(Rolland / Dorsheimer)。
  Wolfspeed 財困,**真.覆蓋崩塌** → pctile 1.5 係**真讀數**,唔係 bug。
  (而且 WOLF 係 ai-power-grid 14 隻票之一,theme 用 median → 被稀釋,無害。)

**euv 之所以爆,係因為佢係單一 ticker theme —— ASML 嘅假數冇任何嘢稀釋,直接變成 theme 分數。**

---

## 3. 數字影響(frozen 公式,逐格算)

subscores(紅隊 §4c 通道 1 判定):moat 2.0 / capital 1.5 / valuation 0.0 / growth 1.5 → **Σ = 5.0/8 = 0.625**
cycle_stage = `late`

| 情境 | crowding pctile | penalty(查表) | confidence |
|---|---|---|---|
| **現時已 commit(污染)** | 2.8 → 帶 `<40` | **0.75** | **0.469** ← themes.yaml 現值 |
| **只修 D1**(剔走 3 份非法說會文件) | 57.4 → 帶 `40-60` | 0.65 | **0.406** |
| **紅隊嘅判斷**(most-consensus) | ~92 → 帶 `>=90` | 0.40 | **0.250** |

**關鍵:淨係修 D1 只收復咗約三分一嘅落差(0.469 → 0.406),距離紅隊嘅 0.25 仲好遠。**
即係話呢度有**兩個獨立缺陷**,而 data bug 係**細嗰半**。

---

## 4. D1 — 資料層缺陷(已證實,但**冇乾淨嘅機械修法**)

**缺陷**:非分析員法說會文件(記者會 / 宣傳片)進入 attendance series → 公司高管同記者被當成分析員。

**試過兩個 guard,兩個都經實測否決 —— 記錄低,免得下次有人再行同一條死路:**

### ❌ Guard A:「fallback operator + 冇 handoff 語句 → 判 failed」
- 保住咗 NVDA 2025 回歸測試(10/6/9/8 全對)✅
- 但**誤殺 11 個 MPWR 季度**(嗰啲 fallback 抽取其實**完全正確**,見 §2c)
- 而且**捉唔到 ASML 2025-10-15**(嗰份有 literal `Operator` tag)→ 修完 pctile 一樣爛

### ❌ Guard B:關鍵字閘(開頭有 "press conference" / "results video" → 剔走)
實測**過闊,會剷走真嘢**:
- **CHKP** "Financial Results **Video** Conference" → **真.分析員法說會**(Gray Powell / Gregg Moskowitz /
  Joel Fishbein 全部真分析員)
- **BMW(BAMXF)** "Annual **Press Conference**" → **一樣有真分析員出席**
  (Jose Asumendi/JPM、Horst Schneider/BofA、Michael Tyndall/HSBC)

> **教訓:文件嘅「標籤」決定唔到佢有冇效 —— 決定性嘅係「邊個出席」。BMW 開記者會分析員照嚟;
> ASML 開記者會嚟嘅係路透社。要機械分辨,就要一個「分析員 vs 記者」嘅名冊分類器 —— Karst 冇。**

### Blast radius(全 corpus 掃過)

- corpus 共 **195,957** 份 transcript;自報 `press conference` 39 份、`results video` 51 份(~90 份,極窄)。
  (`media call` 780 份係**假陽性** —— 多數係法說會入面順口提到「稍後有 media call」,唔好用呢個關鍵字。)
- 全書 **69 隻 active theme ticker 入面,得 2 隻**中招:**ASML**(bug)同 **WOLF**(真讀數,無害)。
- **即係污染極窄 —— 但精準命中 euv 唯一嗰隻票。**

---

## 5. D2 — 建構效度缺陷(**DESIGN 層,唔喺我權限,等用戶拍板**)

`crowding_composite.py` 嘅 attendance input 係 **temporal own-history percentile**:
> 「per-ticker **temporal own-history** percentile of latest successfully-parsed quarter's
> distinct-analyst Q&A count。Higher = more crowded.」

即係佢答緊:**「今季嚟嘅分析員,相對 ASML 自己嘅歷史,係咪特別少?」**

但 `confidence_formula.py` 個 penalty 查表要嘅係 **cross-sectional「呢個故事係咪已經人盡皆知 / priced-in」**
嘅折扣。**兩個係唔同嘅建構。**

**證據 = 全書排名根本反轉:**

```
   2.8  euv-lithography-monopoly    <- ASML,98 分位 PE,全市場最多人講 = 「最唔擠」???
  24.8  memory-supercycle
  34.3  ai-power-grid
  ...
  95.3  glp1-biologics-packaging    <- 冷門包裝細分 = 「最擠」???
  97.2  specialty-siding-pricing-power
  97.8  rare-earth-materials
```

一個覆蓋厚而穩定嘅巨型股(ASML)輕微低於自己常態 → 讀成 2.8;一隻冷門股覆蓋喺自己歷史高位
→ 讀成 97。**temporal 讀數用喺一個要 cross-sectional 答案嘅格,方向可以完全相反。**

補充:模組 docstring 自己攞嚟做驗證嘅兩個個案,其實**唔同型**:
- **MU**「20 年最低出席 = 週期底」= temporal ✅(支持現行實作)
- **USAC**「全場 comparator 入面平均出席最低」= **cross-sectional** ❌(**唔支持**現行實作)

→ 即係話當初 probe 嘅其中一半驗證,同最後實作嘅建構對唔上。

---

## 6. 建議

### 即刻(機械、無酌情、我可以做)
1. **唔好靜靜哋改 euv 個數。** P2 已經立咗「confidence = frozen 公式輸出、零酌情、lint 強制」。
   正路 = **修輸入 → 重跑 frozen 公式 → 出咩就係咩**,唔係人手撥去 0.25。
2. **euv 嘅 crowding input 應該標 `insufficient_data` / `suspect`**,唔好靜靜哋繼續驅動 confidence
   同 sizing。ASML 最後一份可信法說會係 **2025-07-16**(3 季前)。

### 要用戶拍板(design)
3. **D2:crowding 軸究竟要量度乜?** temporal(現行)定 cross-sectional(penalty 表嘅原意)?
   呢個係 DESIGN §4a frozen 公式嘅變更 → 唔喺 agent 權限。
4. **euv 0.47 係用戶核准嘅數。** 而家證實佢建基於記者會 + 宣傳片。要唔要 revert?revert 去邊個數?
   (0.406 = 淨修 D1;0.250 = 紅隊判斷。)

### 資料層(可跟進)
5. ASML 真.分析員法說會**係存在嘅**(ASML 同一日開兩場:分析員 call + 記者會)。
   應該查 defeatbeta 有冇正確嗰份、可唔可以重抓 —— 修好資料就唔使砌脆弱嘅分類器。

---

## 7. 誠實報告 / 未解

- **`corroborates:` 段本身冇問題。** ASML 客戶預付訂金(合約負債 $19.4B ≈ 59% 營收)嘅現金背書
  證據係紮實嘅,脫 single-source cap 嘅資格**成立**。壞嘅淨係 **crowding penalty 呢一格**,
  以及 gatekeeper 用嗰個假數去推翻紅隊嘅**推理**。**兩件事要分開睇 —— 唔好因為呢單而撤銷現金背書登記。**
- **紅隊份報告自己嗰句「脫 cap 但 null-op」**:佢個結論(0.25)啱,但**理由部分錯**——
  佢估 crowding ≥90 係**判斷**唔係量度,佢自己都標明咗「若實際落 80-90 檔,penalty 0.45、raw ~0.28」。
  即係話紅隊係**估啱咗**,gatekeeper 就係**量錯咗**。呢個唔係「紅隊全對」,係「兩邊都冇拎到啱嘅尺」。
- **未查**:呢個文件類型污染有冇影響 **constraint-language scanner**(Karst 主 alpha 管道,同樣讀
  corpus transcript)。ASML 嘅記者會/宣傳片入面 CEO 一樣會講約束語言,所以未必有害,但
  **「16 年第一人稱約束語言 = Tier-1」嘅 provenance 主張,有部分可能其實踩住記者會**。值得跟進。
- **未查**:其餘 ~90 份自報非法說會文件(BMW / CHKP / DDL 等)大部分其實有真分析員出席,
  即係話呢個問題喺 ASML 特別嚴重,可能同「ASML 同日開兩場」呢個特殊安排有關。

---

## 8. 重現

```powershell
# 注意:corpus.db 唔喺 git(gitignored),要喺主 checkout 跑
$env:PYTHONUTF8=1
cd C:\projects\Investment\Karst
python -c "import sqlite3,sys; sys.path.insert(0,'thesis'); import crowding_composite as cc; con=sqlite3.connect('thesis/corpus.db'); print(cc.attendance_series(con,'ASML').tail(6).to_string()); print(cc.ticker_attendance_pctile(con,'ASML'))"
```
