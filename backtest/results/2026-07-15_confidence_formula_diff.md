# Confidence 公式遷移 diff 表(P2 凍結公式 vs 現行 themes.yaml)

> 產出日期:2026-07-15。目的:thesis/DESIGN.md §4a(2026-07-15 凍結,docs/2026-07-15_quantification_review.md
> 提案2)把 `confidence = (Σ 4-KPI subscores) / 8 × penalty(crowding_band, cycle_stage)` 定案為機械公式。
> 遷移前用凍結公式重算 15 個 active theme,睇邊啲 theme 郁得多、郁嘅方向係咪合理、係咪要逐個人手覆核先落
> themes.yaml。**本檔只做 diff,唔改任何現有檔**(themes.yaml/wiki 一隻字冇郁)。

## 1. 方法

- **Subscore 來源**:每個 active theme 嘅 `thesis/wiki/<slug>.md` 內「## confidence 推導」code block,
  用 regex 抽 `moat X/2 · capital X/2 · valuation X/2 · growth X/2 = Y/8` 格式(容許 0.5 步進)。
  **9/15 theme 有呢個格式**(全部係 2026-07-01 admit 批,type B 原始四隻:memory-supercycle/
  photonics-optical/ai-power-grid/advanced-packaging,加 2026-07-11 discovery radar 批:
  rare-earth-materials/tpu-custom-silicon/oil-gas-energy/semicap-equipment/space-satellite)。
  **6/15 theme 冇呢個格式**(2026-07-12 discovery radar 第二批:aerospace-specialty-alloys/
  euv-lithography-monopoly/us-solar-manufacturing/gas-compression-equipment/
  specialty-siding-pricing-power/glp1-biologics-packaging——呢 6 個嘅「confidence 推導」段係純敘事
  比較式,冇 4-KPI 逐格分數,見 §4 未解)。
- **Crowding pctile**:`thesis/.raw/crowding_composite.json`,`generated_at = 2026-07-13T10:05:06Z`。
  **15 個 active theme 全部有 `composite_status: ok` 讀數,冇一個要用 40-60 保守假設**(比 SOP 預期好——
  抽任務時假設嘅「缺讀數要假設 40-60 帶」情況本次冇出現)。讀數比部分 wiki 最新 ingest(2026-07-15 夜班)
  舊 2 日,見 §4 staleness 註記。
- **Cycle_stage + 現行 confidence**:`thesis/themes.yaml` 每個 active theme 嘅 theme-level 欄位(逐字讀取,
  唔用 node 級)。
- **Penalty 表**:`thesis/DESIGN.md` §4a 原表,逐格照搬:

  | crowding \ cycle | early | mid / event-driven | late / mid-late |
  |---|---|---|---|
  | < 40(冷) | 1.00 | 0.90 | 0.75 |
  | 40–60 | 0.95 | 0.85 | 0.65 |
  | 60–80 | 0.85 | 0.75 | 0.55 |
  | 80–90 | 0.75 | 0.65 | 0.45 |
  | ≥ 90(極擠) | 0.65 | 0.55 | 0.40 |

- 公式:`公式confidence = base(Σsubscore/8) × penalty(crowding_band, cycle_stage)`,四捨五入至小數後兩位
  顯示(內部用全精度計算 delta)。

### 語境(DESIGN §4a 關鍵分工決定,寫喺呢度因為直接解釋本表大部分正 delta)

公式 confidence 量嘅係「thesis 為真嘅機率」——**表達層風險(pre-revenue binary/夢想定價/代理二手/
唯一護城河名不可乾淨買)唔再折入 confidence**,呢類風險改由 magnitude_tier + sizing v2(binary micro-
position)同 4-KPI 嘅估值格自己承擔。舊手工推導(2026-07-01/07-11 兩批)嘅「cycle/crowding penalty」
段落普遍**bundle 咗至少三種唔同性質嘅折扣**:(a) 真正嘅 crowding/cycle(合法,公式仍然計)、(b) 估值
分位(已經喺 4-KPI 嘅 valuation 格計過一次——手工 penalty 再罰一次 = 雙重計算)、(c) 表達層/證據品質
風險(SpaceX 唔可以乾淨買、代理二手、薄證據 n=1 來源、投機 froth)——呢類 (c) 正正係凍結公式話唔准再
喺 penalty 度罰嘅嘢。9 個可計 theme 全部正 delta,原因主要係 (b)(c) 被拆走。

## 2. 15-theme 主表

### 2a. 可計 theme(9 個,有 4-KPI 逐格分數)—— 按 |delta| 由大到小排序

| slug | moat | capital | valuation | growth | base(Σ/8) | crowding pctile | cycle | penalty | 公式confidence | 現行confidence | delta | 大幅移動歸因 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| space-satellite | 1/2 | 1/2 | 0.5/2 | 2/2 | 0.5625 | 59.9(40-60) | early | 0.95 | **0.53** | 0.28 | **+0.25** | 幾乎全數來自表達層折扣被移除:舊手工 penalty(~0.50)明文寫「最深護城河 SpaceX 不可乾淨買」+ 夢想定價二次折算;新表只睇 crowding(40-60,由高 attendance/低 bull_ratio 組成)× early cycle → 罰極輕(0.95)。 |
| tpu-custom-silicon | 1.5/2 | 1/2 | 0.5/2 | 1.5/2 | 0.5625 | 46.5(40-60) | mid | 0.85 | **0.48** | 0.25 | **+0.23** | 主因 penalty 標準化:舊 penalty(~0.50)把「薄證據(單一 Tier-2 報告 n=1)」乘埋落罰——呢個係公式完全冇嘅輸入(見 §4 邊界個案);同時估值分位(75-87%)喺 valuation 格已計過,舊 penalty 再罰一次(雙重計算)。新表拆走呢兩個非公式因子後只剩 crowding×cycle。 |
| photonics-optical | 2/2 | 1/2 | 0.5/2 | 2/2 | 0.6875 | 57.1(40-60) | late | 0.65 | **0.45** | 0.30 | **+0.15** | 混合:舊 penalty(~0.43)bundle 咗 58% bull(合法 crowding)+ 估值 75-98 分位(valuation 格已計、雙重計算)+「小型投機 froth」(SIVE/LWLG 表達層風險)。新表拆走後兩者。 |
| ai-power-grid | 1.5/2 | 1/2 | 0.5/2 | 2/2 | 0.625 | 34.3(<40) | late | 0.75 | **0.47** | 0.33 | **+0.14** | 主因 penalty 標準化揭發舊數錯配:舊 penalty(~0.53)理由寫「quality 名 90%+ 分位 + 內部人賣」——但 crowding composite 讀數其實低(34.3,14.3% bull_ratio),舊手工把「個別名貴」當「全 theme 擠」罰,新表用真實 composite 罰得輕好多。 |
| memory-supercycle | 2/2 | 1/2 | 1/2 | 1.5/2 | 0.6875 | 24.8(<40) | late | 0.75 | **0.52** | 0.38 | **+0.14** | 較乾淨嘅純機械標準化案例:舊推導本身冇明顯 bundle 表達層風險或雙重計算估值,只係手工估「LTA 墊地板、罰輕於純晚期 → ~0.55」;新表用實際低 crowding(24.8)算出 0.75,單純係新舊兩套 late-cycle 罰法唔同。 |
| advanced-packaging | 2/2 | 1/2 | 0.5/2 | 2/2 | 0.6875 | 48.1(40-60) | late | 0.65 | **0.45** | 0.32 | **+0.13** | 混合:舊 penalty(~0.46)bundle 咗 11% bull(合法、低擠)+ 估值 90-100 分位(雙重計算)+「表達缺口:真瓶頸非美股、代理二手」(表達層風險)。新表拆走後兩者。 |
| rare-earth-materials | 1.5/2 | 1/2 | 1/2 | 1.5/2 | 0.625 | 97.8(≥90) | event-driven | 0.55 | **0.34** | 0.28 | **+0.06** | 混合但幅度細:舊 penalty(~0.45)bundle 咗事件二元風險 + 薄證據(2 篇)+ 估值 92 分位(雙重計算)+ 100% bull(合法)。新表 ≥90 crowding 帶本身已經好重(0.55),同舊手工數較接近,所以 delta 細過其他大幅移動者。 |
| semicap-equipment | 1/2 | 0.5/2 | 0/2 | 1.5/2 | 0.375 | 40.7(40-60) | late | 0.65 | 0.24 | 0.20 | +0.04(< 0.05 門檻) | 未達大幅移動門檻,不作歸因;方向仍係正(表達層/薄證據混合折扣拆走,但 base 分本身低,絕對值變化細)。 |
| oil-gas-energy | 1/2 | 1/2 | 1/2 | 1/2 | 0.50 | 67.8(60-80) | late | 0.55 | 0.28 | 0.25 | +0.03(< 0.05 門檻) | 未達大幅移動門檻;舊 penalty 本身已經接近機械值(~0.50 vs 0.55),呢個 theme 嘅舊推導冇明顯雙重計算或表達層折扣。 |

### 2b. 推導段缺 / 冇 4-KPI 逐格分數(6 個)—— 無法用公式重算

| slug | crowding pctile | cycle | 現行confidence | 狀態 |
|---|---|---|---|---|
| aerospace-specialty-alloys | 78.6(60-80) | late | 0.24 | 推導段係純敘事比較(「類近 photonics/advanced-packaging,但 transcript-only 源額外保守 → 0.24」),冇 moat/capital/valuation/growth 逐格分數,唔可以套公式。 |
| euv-lithography-monopoly | 2.8(<40) | late | 0.22 | 同上,純敘事(「同 aerospace-specialty-alloys 近似級別,但少咗冷門利基加分 → 0.22」)。 |
| us-solar-manufacturing | 76.0(60-80) | mid | 0.32 | 同上,純敘事(「7年結構故事+估值仍平,但政策binary風險扣減 → 0.32」)。 |
| gas-compression-equipment | 88.9(80-90) | early | 0.33 | 同上,純敘事(「證據最乾淨+估值最平,但單一ticker集中風險 → 0.33」)。 |
| specialty-siding-pricing-power | 97.2(≥90) | mid | 0.20 | 同上,純敘事(「segment層面真訊號但whole-company估值混雜 → 0.20」)。 |
| glp1-biologics-packaging | 95.3(≥90) | mid | 0.27 | 同上,純敘事(「regulatory-lock護城河乾淨但track record最短(4季) → 0.27」)。 |

**呢 6 個全部係 2026-07-12 discovery radar 第二批**(themes.yaml note 逐個提及「6個新thesis」比較框架),
寫法風格同第一批(2026-07-01+07-11)明顯唔同——冇逐格 4-KPI 分數,只有一段跨 theme 相對排序敘事。
呢個唔係抽取失敗,而係呢 6 份 wiki 本身未寫成 4-KPI 打分格式,見 §4。

## 3. 採用影響(如果直接切換,sizing 會點變)

`thesis/sizing.py` 兩套機制都對 confidence 單調遞增:
- **v1(PRELIMINARY/PASS 現行機制)**:`raw_cap = min(confidence × $20k, $15k)`(PRELIMINARY)或
  `confidence × budget / Σconfidence`(PASS)——注碼線性隨 confidence 升跌,confidence 升的 theme 注碼
  必升(PRELIMINARY 個別 cap $15k 前);PASS 模式仲會擠壓其他 theme 嘅相對佔比(分母 Σconfidence 一齊升,
  但升得少嘅 theme 相對佔比反而縮)。
- **v2(shadow,`score = confidence × log2(magnitude_mid)`,低於 `V2_MAGNITUDE_CONF_GATE=0.25` 時
  magnitude 加成關閉、score = confidence)**:排名 by score,top-K 先派錢,confidence 升會直接推高
  排名同注碼;**部分 theme 會跨過 0.25 閘**(例如 tpu-custom-silicon 現行 0.25 貼閘、公式後 0.48,
  magnitude 加成由「關閉」變「開啟」,呢個唔止線性移動,係質變——加成一開,score 額外乘
  `log2(magnitude_mid)`,排名可以跳幾級)。

**注碼升幅最大嘅 theme(照公式 confidence 排序)**:space-satellite(0.28→0.53,幾乎兩倍)、
tpu-custom-silicon(0.25→0.48,近兩倍,仲會跨 v2 magnitude 閘)、photonics-optical(0.30→0.45)、
ai-power-grid(0.33→0.47)、memory-supercycle(0.38→0.52)、advanced-packaging(0.32→0.45)。呢 6 個
theme 喺 v1/v2 都會明顯搶錢(佔 Σconfidence 比重上升);冇一個 theme 喺可計 9 個入面係跌嘅,所以**唔會
有邊個 theme 注碼縮**——純粹「升得多 vs 升得少」嘅相對排序變化,而非誰要被剔除。

## 4. 未解

1. **6/15(40%)active theme 冇 4-KPI 逐格分數,完全無法套公式**(aerospace-specialty-alloys/
   euv-lithography-monopoly/us-solar-manufacturing/gas-compression-equipment/
   specialty-siding-pricing-power/glp1-biologics-packaging,全部 2026-07-12 discovery radar 第二批)。
   要遷移呢 6 個,必須先幫佢哋補寫 4-KPI 逐格打分(照 §4a rubric 錨點),先可以套公式——呢個係遷移嘅
   前置工作量,唔係一次過可以切晒 15 個。
2. **「薄證據/獨立來源數」喺凍結公式冇對應輸入**:DESIGN §1 概念草稿(line 41)原本有「佐證獨立來源數」
   做 confidence 輸入之一,但 §4a 凍結公式(line 91)只剩 4-KPI + crowding/cycle penalty,冇單一來源
   n=1 嘅懲罰位。舊手工推導(tpu-custom-silicon/rare-earth-materials)明文用「薄證據」乘落 penalty——
   公式遷移後呢個訊號會完全消失(唔係被拆走去別處,係無處安放)。建議:遷移時要決定「單一來源」係咪
   應該壓低某個 4-KPI 格分數(例如 moat/growth 格判準本身要求「一手/cited 證據」,理論上薄證據應該反映
   喺低分,但現行 9 個推導入面薄證據係額外乘因子,同 KPI 格分開),定係接受呢個訊號喺遷移後消失。
3. **Crowding 讀數 staleness**:`crowding_composite.json` 產生於 2026-07-13,ai-power-grid 等 theme
   喺 2026-07-14/07-15 有夜班 ingest(但全部標「confidence/cycle 維持」,冇財報級新事實),暫唔影響
   本表結論,但正式遷移前應該重跑一次 crowding composite 攞最新讀數。
4. **`thesis/lint.py` 現時未實作 DESIGN §4a 講嘅「themes.yaml confidence 必須等於公式輸出 ±0.01」機械
   檢查**(已用 grep 確認 lint.py 冇 `penalty`/`crowding_band`/`subscore` 相關邏輯)。即係話而家冇任何
   程式擋住 themes.yaml 同公式脫鈎——呢個檢查要喺遷移落實前一齊補,否則今日切一次之後又會慢慢漂走。
5. **space-satellite 嘅 2026-07-14 SPCX-IPO 重估未反映喺 subscore 本身**:wiki 已經寫低「moat 1/2
   嘅damping理由(SpaceX 不可乾淨買)而家部分解除,但被新利淡(SPCX 本身極貴 IPO + 併入 xAI 稀釋)
   大致抵消,故 subscore 冇改」——本表沿用呢個 4.5/8 unchanged 嘅判斷,但呢個係人手覆核過嘅結論,唔係
   本次抽取自動產生,值得留意呢個 theme 嘅 base 分本身已經處於「下次 ingest 可能要重判」嘅邊界。

## 5. 建議

**採用但逐個覆核大幅移動者(不建議直接全量採用,也不建議完全不採用)。**

理由:
- 9 個可計 theme 全部正 delta、方向一致可解釋(表達層折扣/雙重計算被拆走,同 DESIGN §4a 分工決定完全
  吻合)——公式本身冇跑出奇怪或反直覺嘅數,不是「唔採用」嘅理由。
- 但 7 個 |delta| ≥ 0.05(space-satellite/tpu-custom-silicon/photonics-optical/ai-power-grid/
  memory-supercycle/advanced-packaging/rare-earth-materials)當中,move 幅度最大兩個
  (space-satellite +0.25、tpu-custom-silicon +0.23)本質上係「舊人手判斷刻意把表達層/證據品質風險
  折落 confidence」——呢個折扣消失後,呢兩個 theme 嘅新 confidence(0.53、0.48)已經逼近或超過
  memory-supercycle 舊嘅龍頭數(0.38)。呢個排序變化(乜嘢 theme 應該係全 book 最高 confidence)值得
  人手覆核先落實,尤其 tpu-custom-silicon 會跨過 v2 sizing 嘅 magnitude 閘(0.25),呢個係質變唔係
  線性移動。
- 40% theme(6/15)根本冇法用公式重算,直接全量切換會令呢 6 個 theme 嘅 confidence 同其餘 9 個處於
  兩套唔同方法論(一套機械公式、一套仍然係舊手工敘事數字)——呢個不一致本身就係「唔可以一次過全部切」
  嘅理由。
- 建議路徑:(a) 先幫 6 個推導段缺嘅 theme 補 4-KPI 逐格分數;(b) 7 個大幅移動者逐個由人過目公式輸出
  合理後先寫落 themes.yaml;(c) 2 個 <0.05 移動者(semicap-equipment/oil-gas-energy)風險低,可以隨 (b)
  一併直接切;(d) 同步把 §4a 講嘅 lint.py 機械檢查建好,防止切完之後又漂走。

---

## Gatekeeper addendum(Fable 主 session,2026-07-15)

本表算術抽驗通過(space 0.5625×0.95=0.53 ✓、memory 0.6875×0.75=0.52 ✓)。但「未解 #2」
(公式冇「獨立來源數」輸入位)係一個真設計漏洞,已同日修正:**DESIGN §4a 公式補返
single-source cap 0.30**——呢個唔係新發明,係 WS3 admission 規則本身有、lint 一直 warn 緊
(5 個 theme 現正違規)嘅既有規則,公式必須內建。

**有 cap 之後,本表個 picture 完全改觀**(15 個 active theme 嘅 sources: 登記絕大多數係
單一來源 gooptions-trend-core):

| slug | 公式(無cap) | 公式(有cap) | 現行 | 有cap delta |
|---|---|---|---|---|
| space-satellite | 0.53 | **0.30** | 0.28 | +0.02 |
| tpu-custom-silicon | 0.48 | **0.30** | 0.25 | +0.05 |
| photonics-optical | 0.45 | **0.30** | 0.30 | 0.00 |
| ai-power-grid | 0.47 | **0.30** | 0.33 | −0.03 |
| memory-supercycle | 0.52 | **0.30** | 0.38 | **−0.08**(現正違規,修返合規) |
| advanced-packaging | 0.45 | **0.30** | 0.32 | −0.02 |
| rare-earth-materials | 0.34 | **0.30** | 0.28 | +0.02 |
| semicap-equipment | 0.24 | 0.24 | 0.20 | +0.04 |
| oil-gas-energy | 0.28 | 0.28 | 0.25 | +0.03 |

無 cap:7 個 theme 齊升(最大 +0.25)= 系統性加風險,唔安全。
有 cap:delta 壓縮到 ±0.08,唯一大移動係 memory 向下修返合規——遷移風險大幅下降,
且公式嘅分辨力誠實反映咗「單一來源 thesis 唔應該憑來源內部質素攞高注碼」。

**採用路徑(維持 agent 建議嘅「採用但覆核」,加埋 cap 版本):**
1. 先補 6 個缺 subscores 嘅 theme(discovery-radar 批,wiki 推導係純敘事)——判斷工作,
   照 rubric 錨點逐格補寫,主 session/貴模型做,唔外判。
2. 實作 lint 機械檢查(themes.yaml confidence == 公式輸出 ±0.01,含 cap)。
3. 15/15 齊全後出最終 diff,用戶過目先改 themes.yaml 數字。
