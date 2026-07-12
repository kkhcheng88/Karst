# Phase-3 主題:母板塊參照 vs 可買 chain-expression ETF(兩個分開問題)【2026-07-10,修正版】

> ⚠️ **概念修正(用戶 2026-07-10 點出)**:本檔第一版把兩個唔同問題撞埋一齊 ——
> ①「呢條 value chain 同母板塊/其他 sub-sector 點相關」(`parent_proxy` 本來嘅角色)
> ②「想買啲乜嚟表達呢條 chain 本身」(交易用,要「純」)。
> 第一版用「thesis 個股喺 parent_proxy 入面嘅權重」評「純度」,即係將 ①②混做一件事嚟評分 ——
> 評分前提本身就錯。`parent_proxy`(SOXX/SMH/XLI/ITA/XLB)從來冇打算表達 chain 本身,佢哋故意
> 代表**母板塊**,拎嚟同 thesis basket 做 correlation/relative-strength 先有意義(用戶明言:呢啲
> sub-sector/value-chain 一定係某板塊嘅子集甚至跨板塊,將來要分析唔同 sub-sector 之間、以及同
> 母板塊之間嘅相關性 —— 母板塊 ETF 本身就唔應該代表到條 chain 嘅全貌,呢個係設計原意唔係缺陷)。

## 問題①:parent_proxy(母板塊參照,分析用,唔使「純」)—— 維持不變

`thesis/themes.yaml` 現狀正確,唔需要改:

| 主題 | parent_proxy | 角色 |
|---|---|---|
| photonics-optical / advanced-packaging / tpu-custom-silicon | SOXX, SMH | SEMI 母板塊溫度計 + 相關性參照 |
| ai-power-grid | XLI | INDUSTRIALS 母板塊參照 |
| space-satellite | ITA | AERO_DEF 母板塊參照 |
| rare-earth-materials | XLB | MATERIALS 母板塊參照 |
| oil-gas-energy | XLE | 兼做 benchmark_etf(乾淨對照,見下) |

**用途**:量 sub-sector vs 母板塊嘅相對強弱/相關性(例如「semis 整體熱唔熱、photonics 跑贏定跑輸個母板塊」),
唔係交易表達工具。SOXX/SMH 入面右 COHR/LITE 唔係缺陷 —— 佢哋本來就唔應該喺度。

## 問題②:chain-expression ETF(想買嚟表達條 chain 本身,要「純」)—— 呢個先係原本想答嘅問題

呢個係獨立於 `parent_proxy` 嘅新問題(用戶原問:「主題 ACCUMULATE 時,買 ETF 得唔得」)。答法:
逐條 chain 各自搵**有冇一隻相對窄嘅 ETF**,用真實持倉權重量「thesis 個股喺入面佔幾多」。
**呢張表唔取代 parent_proxy,係加多一層畀想用 ETF(而非個股)入場嘅人用。**

| 主題/候選 | Chain-expression ETF | thesis 個股喺 top10 權重 | 判 |
|---|---|---|---|
| memory-supercycle | **DRAM**(Roundhill) | SK Hynix 15.9%+Samsung 14.4%+Kioxia 4.4%=**35%** | ✅ 純(全球記憶體寡頭本身) |
| oil-gas-energy | **XLE** | 設計時已核實純能源板塊 | ✅ 純 |
| space-satellite | **NASA**(Tema Space Exploration,用戶自選清單發現)| RKLB 9.5%+ASTS 5.3%+LUNR 3.8%=**18.6%**,+MDA/Firefly/EchoStar/Viasat | 🟡 中(遠優於用 ITA 嚟做呢個角色 —— 但 ITA 本來就唔係為呢個用途存在) |
| 鈾/核電(新候選,見 `2026-07-09_priced_in_gate.md`) | **NLR**(VanEck Uranium & Nuclear,用戶自選清單發現)| UEC 5.0%+SMR 4.8%+BWXT 6.5%=**16.4%**,+CCJ姊妹股Cameco 8.5%/NexGen/Denison/Oklo | 🟡 中 |
| ai-power-grid | **GRID**(Clean Edge Smart Grid,用戶自選清單發現)| ETN+PWR=**16.7%**(仍摻 Schneider/ABB/National Grid 電網設備老牌股)| 🟡 中 |
| ai-power-grid(次選) | PAVE(US Infra) | 僅 7.4%,主力鐵路/建築機械 | 🔴 弱,關係較遠 |
| tpu-custom-silicon | 未搵到窄 ETF(SOXX/SMH 只係母板塊)| AVGO+TSM 喺 SOXX/SMH ≈10-15%,但嗰係母板塊唔係 chain-expression | 🔴 冇窄 ETF,買個股(AVGO/TSM) |
| photonics-optical | 未搵到窄 ETF | COHR/LITE 喺 SOXX/SMH 缺席(母板塊本來就唔含佢哋)| 🔴 冇窄 ETF,買個股(COHR/LITE) |
| advanced-packaging | 未搵到窄 ETF | — | 🔴 冇窄 ETF,買個股 |
| rare-earth-materials(MP/USAR,indium/gallium)| 未搵到窄 ETF(NLR 係鈾,唔係稀土,唔啱)| — | 🔴 冇窄 ETF,買個股 |

**結論**:memory/oil-gas 已有純 chain-expression ETF;space/鈾/ai-power 靠用戶自選清單搵到中純度選擇
(NASA/NLR/GRID);tpu/photonics/packaging/rare-earth 現時**冇窄 ETF,想入場只有個股一條路**
(呢個判斷唔變,但理由更正:唔係「SOXX/SMH 唔夠純」,係「呢啲 chain 本身冇專屬 ETF 存在」)。

## 原始持倉數據(供覆核,兩層都用得到)

**母板塊 proxy**:
SOXX: MU 8.54 / AMD 8.09 / NVDA 6.81 / INTC 6.33 / AVGO 6.08 / AMAT 5.77 / KLAC 5.64 / LRCX 4.89 / MRVL 4.88 / TSM 4.26
SMH: NVDA 17.75 / TSM 9.19 / MU 5.84 / AMAT 5.73 / AMD 5.43 / AVGO 5.41 / KLAC 5.34 / LRCX 5.23 / INTC 5.04 / ASML 4.95
ITA: GE 22.62 / RTX 14.82 / BA 8.90 / TDG 4.59 / HWM 4.50 / GD 4.33 / LMT 4.05 / NOC 3.92 / LHX 3.80 / RKLB 3.63
XLB: LIN 14.04 / NEM 5.84 / FCX 5.29 / CTVA 4.95 / SHW 4.93 / ECL 4.72 / VMC 4.71 / CRH 4.66 / APD 4.62 / MLM 4.54
XLI: CAT 8.51 / GE 6.76 / GEV 5.48 / RTX 4.43 / BA 2.96 / ETN 2.87 / UNP 2.80 / DE 2.76 / UBER 2.55 / VRT 2.23

**Chain-expression 候選**:
DRAM: SK Hynix 15.89 / Samsung 14.37 / FGXXX(cash) 14.17 / SNDK 5.21 / Kioxia 4.36
NASA: RKLB 9.54 / ECHO 9.00 / ASTS 5.29 / VSAT 5.14 / MDA.TO 4.01 / LUNR 3.82 / VNP.TO 3.81 / FLY 3.78 / FTC.L 3.14
NLR: CCO.TO 8.46 / CEG 8.31 / PEG 7.13 / BWXT 6.53 / FORTUM.HE 5.62 / OKLO 5.21 / NXE.TO 5.08 / UEC 5.02 / SMR 4.82 / DML.TO 4.82
GRID: ETN 8.54 / SU.PA 8.31 / ABBN.SW 8.13 / PWR 8.12 / JCI 8.00 / NG.L 4.12 / EOAN.DE 3.89 / PRY.MI 3.88 / NVT 2.88 / HUBB 2.61
PAVE: PWR 4.04 / CSX 3.49 / ETN 3.35 / TT 3.31 / HWM 3.25 / DE 3.19 / URI 3.11 / UNP 3.08 / ROK 3.06 / NSC 2.86

## 用戶自選清單其他 ETF(唔對應現有供給約束主題,記錄但不評分)

SLV(實物白銀,結構不同,冇「稀釋」概念)、USO(期貨滾動,結構同 XLE 唔同,XLE 已夠用)、
EWY(南韓,可做 memory thesis 嘅總體確認指標,唔係替代)、CHAT/MAGS/BOTZ/IGV/SKYY/BUG/CIBR
(AI/科技廣義 beta,需求端/敘事端,唔喺 magnifier 供給約束範圍)。

## 下一步(design 決定,未落地 —— 用戶話事先落手)

- [ ] **唔動 `parent_proxy`**(問題①已經啱)。
- [ ] 考慮喺 themes.yaml 加**新獨立欄**(命名待定,如 `chain_etf`)記錄問題②嘅答案,同 `parent_proxy`
  明確分開,避免將來再撞埋。
- [ ] 鈾/核電新候選正式評估入 themes.yaml(NLR 做其 `chain_etf`)。
- [ ] space-satellite 可喺 thesis doc 註明 NASA 做 chain-expression 選項(**唔動 parent_proxy=ITA**)。

## 邊界(誠實)
兩層都係**持倉快照**,唔係歷史回測。想再驗證「chain-expression ETF 歷史上實際跑贏/跑輸個股籃幾多」,
或者「sub-sector vs 母板塊嘅相關性/相對強弱歷史模式」,兩者都可以另開回測,分開設計唔混。
