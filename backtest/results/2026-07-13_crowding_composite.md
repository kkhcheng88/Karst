# Feature-5 擁擠複合(crowding composite)—— analyst 出席數 + GS flow + bull-ratio 三輸入合成

**日期**: 2026-07-13
**腳本**: `thesis/crowding_composite.py`(可重跑,PYTHONUTF8=1)
**產出**: `thesis/.raw/crowding_composite.json`(機讀,已 gitignore)
**背景**: Fable 交接書 P2-17 / `docs/2026-07-12_dashboard_design_v3.md` backlog #17——magnifier rubric
feature-5(sentiment/crowding)一直冇量化 proxy。2026-07-12 可行性探測
(`backtest/experiments/exp_analyst_attendance.py`,`backtest/results/2026-07-12_analyst_attendance_crowding_probe.md`)
已驗證方向成立(analyst 出席人數 = 免費、Karst 自家 corpus 已有嘅歷史時序,MU 20年谷底出席數同價格谷底
吻合,USAC「未被發現」對照組出席數全場最低),但留低一個已知 bug(NVDA 2025 四季解析全失敗)同兩個
未驗證輸入(GS flow Z、bull-ratio)。本次:(1) 修 NVDA 2025 bug,(2) 三輸入現實檢查,(3) 落地做 15 個
active theme 嘅複合讀數。

---

## [結論]

1. **NVDA 2025 parser bug 已修正**——4 季由 0(全失敗)修到 10/6/9/8 人(見證據段)。根因:呢 4 季轉會 operator
   用自己個名(「Christa」「Sarah」)做 speaker tag,唔係原腳本要求嘅字面 "Operator"。修法:generalize 做
   「冇字面 Operator tag 先 fallback 用第一個發言者自己個 tag」,對其餘 ~95% 已成功解析嘅 transcript 行為
   完全不變(NVDA 本身唔喺任何 active theme 嘅 ticker 名單入面,呢個修正純粹係方法論驗證,唔直接餵落複合)。
2. **三輸入現實檢查**:analyst 出席數✔️(corpus.db 有,79-82 季/隻覆蓋好)、bull-ratio✔️(`thesis/.raw/gooptions/
   research-manifest.json` 嘅 `thesisType` 欄位,只有 `bull`/`neutral` 兩值,冇 `bear`)、**GS flow Z ✗ ——repo
   內搵唔到任何 Goldman Sachs prime-brokerage/flow 數據源**(`docs/2026-07-12_dashboard_design_v3.md` 只係前瞻
   prose,話「P1-2 落地前先顯示 bull-ratio」,證實呢個輸入本身就係已知延後項),誠實標 `not_available`,冇造數。
3. **最擠 3 個 theme**(composite pctile,高=擠):`rare-earth-materials` 97.8、`specialty-siding-pricing-power`
   97.2、`glp1-biologics-packaging` 95.3。**最唔擠 3 個**:`ai-power-grid` 34.3、`memory-supercycle` 24.8、
   `euv-lithography-monopoly` 2.8(⚠️呢個讀數失真,見 [未解/風險] #1——校正後應該係 ~57-59)。
4. **15 個 active theme 全部有 composite 讀數**,冇一個要標「ticker 覆蓋不足」——雖然個別 ticker(SKHY/SIVE 無
   transcript、SNDK/LWLG/USAR/LOAR 歷史太短)喺 ticker 層被跳過,但每個 theme 都至少有一隻覆蓋足夠嘅 ticker
   撐住 attendance 讀數。
5. **輸入覆蓋率**:attendance 15/15 theme 有讀數;bull-ratio 9/15(冇讀數嗰 6 個——aerospace-specialty-alloys/
   euv-lithography-monopoly/gas-compression-equipment/glp1-biologics-packaging/specialty-siding-pricing-power/
   us-solar-manufacturing——全部係 2026-07-11 discovery radar 批次、`sources: transcript-discovery-radar tier:3`,
   本身就冇 gooptions Tier-2 覆蓋,唔係 bug);gs_flow 0/15(全部 `not_available`)。

---

## [證據]

### NVDA 2025 出席數:修正前後對比

| 財季 | 修正前(原腳本邏輯,字面 "Operator" tag) | 修正後(本腳本,operator-tag generalize) |
|---|---|---|
| 2025-02-26 | 0(`failed`) | **10**(`speakertag`) |
| 2025-05-28 | 0(`failed`) | **6**(`speakertag`) |
| 2025-08-27 | 0(`failed`) | **9**(`speakertag`) |
| 2025-11-19 | 0(`failed`) | **8**(`speakertag`) |

修正後 2025 全年平均 8.25 人,同 NVDA 2024 全年(10.0-11.0 人)、2026 已知兩季(9-12 人)同一量級,方向
合理(呢個係方法論驗證,NVDA 本身不在任何 active theme 嘅 tickers 名單——ai-power-grid/tpu-custom-silicon
兩個 theme 嘅 note 都明文將 NVDA 列為「下游需求/incumbent,排除」)。

### 兩個 theme 逐項數(抽樣)

**memory-supercycle**(composite=24.8,2 輸入)
- attendance = 39.5(median of MU/WDC own-history pctile;`SNDK` 跳過因為得 3 季歷史唔夠 `MIN_QUARTERS=8`,
  `SKHY` 跳過因為 corpus 冇 transcript——2026-07-10 先掛牌)
- bull_ratio = 10.0%(1/10 篇 gooptions 報告 bull;`n=10` 唔算薄,呢個真係「共識未算太熱」嘅讀數)
- 解讀:同 themes.yaml 現有 note「late but LTA-cushioned」相容——出席數同 bull 覆蓋都唔算極端擠迫,並非
  「谷底」但都未到 photonics/rare-earth 嗰種擠迫。

**rare-earth-materials**(composite=97.8,2 輸入,但要睇清楚樣本量)
- attendance = 95.5(僅 MP 一隻;USAR 得 2 季歷史,跳過)—— MP 出席人數接近其自身 22 季歷史嘅頂
- bull_ratio = 100%(1/1 篇 gooptions 報告)——**⚠️薄樣本,n=1,唔可以讀成「業界一致睇好」,只係「唯一一篇
  提及嘅報告係 bull」**,composite json 已明文列 `n_bull`/`n_total` 避免呢個誤讀
- 解讀:同 themes.yaml 現有 note(稀土地緣政治敘事 2026-07 昇溫)方向一致,但複合分數嘅極端值主要由「樣本
  量細」放大,唔應該過度解讀做「全市場最擠」

---

## [產物]

- `C:\projects\Investment\Karst\thesis\crowding_composite.py` —— 主腳本(NVDA fix + 三輸入複合 + JSON/報告)
- `C:\projects\Investment\Karst\thesis\.raw\crowding_composite.json` —— 機讀輸出(已加入 `.gitignore`)
- `C:\projects\Investment\Karst\backtest\results\2026-07-13_crowding_composite.md` —— 本報告
- `.gitignore` 新增一行 `thesis/.raw/crowding_composite.json`(跟 `beta_check_report.json`/
  `opportunity_ladder.json`/`valuation_report.json` 同一 convention:derived/regenerable JSON 自己一行)

### 完整 15 theme 表(composite pctile,高=擠;bull_ratio 格式 `%(n_bull/n_total)`)

| theme | composite | attendance | bull_ratio | gs_flow | 輸入數 |
|---|---:|---:|---:|---:|---:|
| rare-earth-materials | **97.8** | 95.5 | 100.0(1/1) | n/a | 2 |
| specialty-siding-pricing-power | **97.2** | 97.2 | n/a(0/0) | n/a | 1 |
| glp1-biologics-packaging | **95.3** | 95.3 | n/a(0/0) | n/a | 1 |
| gas-compression-equipment | 88.9 | 88.9 | n/a(0/0) | n/a | 1 |
| aerospace-specialty-alloys | 78.6 | 78.6 | n/a(0/0) | n/a | 1 |
| us-solar-manufacturing | 76.0 | 76.0 | n/a(0/0) | n/a | 1 |
| oil-gas-energy | 67.8 | 85.5 | 50.0(2/4) | n/a | 2 |
| space-satellite | 59.9 | 94.7 | 25.0(1/4) | n/a | 2 |
| photonics-optical | 57.1 | 62.3 | 51.9(14/27) | n/a | 2 |
| advanced-packaging | 48.1 | 76.3 | 20.0(2/10) | n/a | 2 |
| tpu-custom-silicon | 46.5 | 59.8 | 33.3(3/9) | n/a | 2 |
| semicap-equipment | 40.7 | 81.4 | 0.0(0/2) | n/a | 2 |
| ai-power-grid | **34.3** | 54.3 | 14.3(2/14) | n/a | 2 |
| memory-supercycle | **24.8** | 39.5 | 10.0(1/10) | n/a | 2 |
| euv-lithography-monopoly | **2.8**⚠️ | 2.8⚠️ | n/a(0/0) | n/a | 1 |

---

## [未解/風險]

1. **euv-lithography-monopoly(ASML)讀數失真,已查明根因,未算法修正(刻意)**:ASML 最近 3 季
   (2025-10-15/2026-01-28/2026-04-15)喺 corpus.db 入面 body 只有 8.5K-9.3K 字(正常季報 transcript
   45-55K 字),逐字睇內容確認呢 3 份唔係標準法人電話會議全文——2026-01-28 嗰份出現「Toby Sterling」呢類
   記者名、「Jim Kavanagh」做主持而非「Operator」,睇落係 Capital Markets Day/投資者日嘅節錄,唔係季度
   Q&A。用「最後一季」計 percentile 就攞咗 1-3 人嘅假讀數,拖到 2.8th pctile。**剔除呢 3 季、用最後一份
   乾淨 transcript(2025-07-16,n=11)重算,percentile 應該係 ~57-59th(近乎歷史中位,而非谷底)**——即係
   話 euv-lithography-monopoly 嘅真實 attendance 讀數大概率係「中性」,唔係「最唔擠」。冇喺腳本入面加
   長度過濾(檢查發現全 corpus 有 53 份 <20000 字嘅 theme-ticker transcript,大部分係 2008-2018 年細公司
   (AEHR/GSAT 果類)真係短嘅正常季報,唔係壞數據——冇足夠信心分辨「真係短」vs「truncate」就落一刀切
   長度 filter,寧願留低呢個已知 caveat 誠實揭露,好過用一個未驗證嘅 heuristic 引入新嘅靜默錯誤)。
2. **bull_ratio 6/15 theme `not_available` 全部有解釋、非隨機缺失**:全部係 2026-07-11 discovery radar
   批次(`sources: transcript-discovery-radar tier:3`),呢批 thesis 嘅證據源本身就係逐字 transcript
   一手引句,唔係 gooptions Tier-2 第三方報告,所以 manifest 入面搵唔到相關 `primary_ticker` 好合理。
3. **薄樣本 bull_ratio 唔應該同厚樣本嘅同一把尺量**:`MIN_REPORTS=1`(跟隨 themes.yaml 現有慣例,semicap-
   equipment 都係用 1 篇報告嘅 0% bull)令 rare-earth-materials(1/1)、oil-gas-energy(2/4)、
   space-satellite(1/4)、semicap-equipment(0/2)呢類讀數對單一新報告極度敏感。JSON/報告已經逐個都印
   `n_bull/n_total`,唔會淨顯示個 ratio 呃人,但複合分數嘅排序(尤其最擠 top 3)入面 3 個都係 `n_inputs=1`
   (只有 attendance,無 bull_ratio),同 memory-supercycle/photonics-optical 呢類 `n_inputs=2` 嘅唔完全係
   同一把尺——2-輸入平均會較溫和(向中間拉),1-輸入唔會,呢個結構性差異會令 1-輸入 theme 天然較易出現喺
   極端值,解讀 top/bottom 3 時要意識到呢點。
4. **GS flow Z 完全冇數據源**——搜過 `backtest/data.py`、`thesis/*.py`、`backtest/experiments/*.py`、
   `docs/*.md`,repo 入面得返 `docs/2026-07-12_dashboard_design_v3.md`(前瞻 prose,話明 P1-2 落地前只顯示
   bull-ratio)同 `docs/2026-07-13_fable_session_handover.md`(即本任務嘅 backlog item 本身)兩個提及,
   冇任何實際擷取管道。要真正補呢個輸入,需要外部訂閱(Goldman prime brokerage flow 唔係公開數據),超出
   本次任務範圍。
5. **殘留自舊探測繼承嘅已知雜訊(非本次新增,冇喺本次修正範圍)**:CEO/CFO 只喺 Q&A 應答、冇喺 prepared
   remarks 出現嗰啲 quarter(NVDA 好多季都係呢個模式,Jensen Huang 一直被計做「analyst」——`exp_analyst_
   attendance.py` docstring 原本已知呢個限制,2008 年 MU S. Appleton 案例),因為 own-history percentile
   係跟自己歷史比,呢個系統性高估對每個 ticker 都一致存在,對「相對於自己歷史係咪反常咁多人」嘅判斷影響
   有限,但絕對人數本身唔應該當真.分析師出席人數讀。
6. `MIN_QUARTERS=8` 令 SKHY(0 季)、SIVE(0 季)、SNDK(3 季)、LWLG(2 季)、USAR(2 季)、LOAR(6 季)呢 6 隻
   ticker 喺 attendance 輸入被跳過(theme 層用返其他 ticker 補到,冇任何 theme 因此變 `insufficient_data`)。
