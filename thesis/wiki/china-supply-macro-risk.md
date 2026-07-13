---
slug: china-supply-macro-risk
type: macro-risk
updated: 2026-07-13
---

<!-- frontmatter = valid-YAML scalars only. Put wiki-links INLINE in the body; cite sources inline
     per claim. Never put double-bracket links in YAML frontmatter (breaks the parser). -->

# 中國供應鏈曝險宏觀風險(跨主題)— 供給側嘅集中度風險,唔係「睇淡中國」

> 概念頁,跨 [[rare-earth-materials]] / [[us-solar-manufacturing]](兩個正式標 `china-supply`
> meta_factor 嘅 theme)+ [[photonics-optical]](AXTI 節點,標 `ai-capex` 但中國曝險全審查最高危)。
> 蒸餾自 `backtest/results/2026-07-11_china_dependency_audit.md`(68 隻票全審查)+
> `backtest/results/2026-07-13_mp_capex_da_review.md` / `2026-07-13_mp_capex_da_history.md`(MP
> capex 警號對抗式覆核,已裁決)。呢頁**不進 themes.yaml、不接 thesis_quality**(同
> [[ai-capex-macro-risk]] 一樣,係跨主題校準輸入,唔係某隻 ticker 嘅 thesis)。
>
> 起因:Fable 交接書 P2-13;`thesis/themes.yaml` 43-46 行 header 一直寫呢個 hub MISSING,
> `thesis/lint.py` 亦持續 warning(WS3 §1a hub-page-coverage check)。

## 一句話

`china-supply` meta_factor 量度嘅**唔係**「呢隻股睇淡中國」,而係**供給側直接曝險**——公司自己嘅
製造、關鍵原料供應鏈,定係收入結構,實質依賴中國(生產設施喺境內、原料出口受中國牌照管制、或收入
集中喺中國客戶),令一次中國政策衝擊(出口管制收緊/放寬、關稅、反傾銷調查)可以**直接打斷或改寫**
呢隻票嘅供給或需求,唔係間接嘅總經 sentiment。正式標呢個 meta_factor 嘅得 2 個 theme([[rare-earth-materials]]
/ [[us-solar-manufacturing]]),但下面會見到,曝險實際散落喺更多 theme(尤其 `ai-capex` 底下嘅
[[photonics-optical]]、ai-power-grid、advanced-packaging)——呢個係本頁第 4 節要單獨處理嘅結構性缺口。

## 四條線

### 線一:稀土/關鍵金屬咽喉主題([[rare-earth-materials]],meta_factor: china-supply)

**現況:** cycle_stage `event-driven`、confidence **0.28**(全批最低)、verdict
`real-chokepoint-thin-evidence-event-binary`(`thesis/themes.yaml:571-573`)。

**曝險機制:** 中國官方(USGS)數據掐住嘅真金屬咽喉——銦 70%、鎵 98–99% 全球產量在中國,對美重稀土
(釔)出口管制後只剩管制前約 5%(`thesis/wiki/rare-earth-materials.md:63-65`)。[[MP]] 歷史上 >90%
營收靠賣稀土精礦俾 Shenghe Resources(MP 少數股東)喺中國分離提煉,因為 MP 自己冇分離產能——2025 年 7
月起靠 DoD/DoW $400M 夥伴關係迅速切到零,但重稀土(鏑/鋱)本土分離要等新產線 2026 年中先投產,即
「營收依賴」已脫鈎、「產能依賴」未完全脫鈎;中國仲反過嚟將 MP 列入設備/技術進口黑名單(反向風險)
(`thesis/themes.yaml:605-613`)。

**最新讀數/裁決:** kill_condition 綁定單點二元事件——**2026-11 中美正式協議全面解除銦/鎵/重稀土出口
管制**(或陝西銦杰 250 噸 InP 良率達標 / MP 的 DoD $110/kg 保底或 Project Vault 撥款生變 / 休戰無限期
延長市場 price-out)任一觸發 → confidence 歸零(`thesis/themes.yaml:574-579`;`thesis/wiki/rare-earth-materials.md:116-119`)。
[[MP]] ttm_pe 119.6(自身史 92 分位)已入政策溢價,「別追高」;[[AXTI]] 曾係「唯一便宜咽喉」但已下修
(見線四)。

**詳細檔案:** `thesis/wiki/rare-earth-materials.md`。

### 線二:美國太陽能製造嘅碲(tellurium)依賴([[us-solar-manufacturing]],meta_factor: trade-policy + china-supply)

**現況:** cycle_stage `mid`、confidence **0.32**、verdict `real-policy-moat-and-still-cheap`
(`thesis/themes.yaml:854-856`)——discovery radar 呢批入面 priced-in 狀態最好嘅一個(ttm_pe 3 年滾動
22nd 分位)。

**曝險機制:** [[FSLR]] 嘅「反中國」定位喺製造地(美國/印度/越南/馬來西亞,非中國)同避開中國主導嘅
多晶矽供應鏈(CdTe 技術路線,唔使多晶矽)兩方面都啱,但**唔完全等於零依賴**——CdTe 技術嘅核心原料
碲,中國控制全球約 75–76% 產量,2025 年 2 月已對碲/CdTe 實施出口許可管制。FSLR 自己 10-K 披露緊主動
應對(替代供應商、申請許可證、回收率最多 95%)——呢種語言本身已顯示公司當呢個係真實而非假設性嘅風險
(`thesis/themes.yaml:883-888`;audit `backtest/results/2026-07-11_china_dependency_audit.md:119,252-261`)。
呢個係 **Type C(出口限制/供應鏈輸入)**,唔係 Type A/B 製造依賴——FSLR 本身冇喺中國設廠。

**最新讀數/裁決:** kill_condition 2026-07-11 已補上呢條腿——「中國進一步收緊碲/CdTe 出口管制,打斷
FSLR 核心原料供應」與關稅/IRA 政策撤銷並列為觸發條件之一(`thesis/themes.yaml:857-862`)。**呢個風險
機制同線一(rare-earth-materials)一樣——中國用關鍵原料出口牌照做地緣槓桿**,但**唔綁定同一個 2026-11
calendar 觸發點**(FSLR 嘅碲管制係 2025-02 已生效嘅持續狀態,唔係等待中嘅二元事件),兩者唔應被當成
同一個觸發時鐘(見第 4 節)。

**詳細檔案:** `thesis/wiki/us-solar-manufacturing.md`。

### 線三:MP capex/D&A 雙警號(已覆核,2026-07-13 裁決)

**現況:** Fable 交接書 P2-16 標記「兩軸齊響 2.192x(capex/D&A TTM 水平)/2.540x(capex YoY 加速度),
P2 死亡劇本前兆,未有人跟」。呢個唔係獨立主題,係 [[rare-earth-materials]] theme 入面 [[MP]] 呢隻票
嘅一條額外訊號軸,同中國供應鏈曝險嘅關聯在於:呢個警號本身係咪「供給紀律崩壞」訊號,直接決定緊 MP
呢個中國依賴過渡期(見線一)嘅風險讀法。

**曝險機制:** N/A——本身唔係中國曝險訊號,而係資本開支/折舊比率嘅供給紀律訊號,本頁收錄係因為佢
直接影響線一嘅風險判讀(MP 正正處於「擺脫中國營收依賴、未完全擺脫中國產能依賴」嘅視窗期,capex 建緊
嘅正正係呢條未驗證嘅新產線)。

**最新讀數/裁決(2026-07-13,對抗式覆核已裁決,駁回 P2 前兆說):** 兩軸門檻本身無統計基礎(probe
自己承認 loosely-anchored、n=2、mirror 錯配),而 MP 自身歷史時序(2026-07-13 補算)顯示現讀數
2.192x 喺自身歷史屬**低至中位**(季度粒度 55.6 分位、年度粒度 16.7 分位),遠低於自身 FY2022 建置
高峰 17.792x,且係谷底(1.747x,2025Q3)後第 2 季溫和反彈——形態同 RKLB(持續假象型,現處自身歷史
新高)、MU(真週期頂型,谷底後 9 季連升未見頂)都唔同類,支持「build-out 正常波動」讀法
(`backtest/results/2026-07-13_mp_capex_da_history.md:149-159`)。擴產本身由 **DoD 15% 股權注資
(equity,非債務)+ $110/kg 保底 + Apple 預付 + Project Vault 政府背書**撐住,結構上唔符合 P2「由
紀律轉狂擴嘅債務融資超建」定義要件(`backtest/results/2026-07-13_mp_capex_da_review.md:52-63`)。
**裁決:capex 兩軸唔構成 P2 供給紀律崩壞訊號,駁回。** 但 MP 仍有獨立、非 capex 嘅殘餘風險——ttm_pe
92 分位已入政策溢價、2026-11 二元事件、純 play 無多元化緩衝——呢啲風險真實存在,只係唔應該用 capex
警號嚟論證(`backtest/results/2026-07-13_mp_capex_da_review.md:109-131`)。維持觀察(hold/watch),
不 kill、不因 capex 警號加倉,confidence: 中。

**詳細檔案:** `backtest/results/2026-07-13_mp_capex_da_review.md`(對抗式覆核全文)+
`backtest/results/2026-07-13_mp_capex_da_history.md`(自身歷史時序數據)。

### 線四:AXTI 中國製造風險([[photonics-optical]],meta_factor: ai-capex——**未標 china-supply**)

**現況:** [[photonics-optical]] theme 整體 cycle_stage `late`、confidence 0.30;AXTI 作為 InP 基板
節點(`inp-substrate-chokehold`)cycle_stage 標 `event-driven`(`thesis/themes.yaml:159-163`)。

**曝險機制:** AXTI 是全審查 68 隻票入面**最高危一隻**——10-K 逐字「全部 substrate 產品喺中國生產」
(北京通美 Tongmei 廠,1,049/1,075 員工喺中國),已經俾中國出口許可證直接掐停收入兩次(2023 鎵鍺、
2025 磷化銦)(`backtest/results/2026-07-11_china_dependency_audit.md:61`;`thesis/themes.yaml:213-216`)。
呢個係**雙重曝險**:AXTI 唔止有現有 kill_condition 講嘅 InP 供給樽頸曝險(交期 32 個月),仲有**生產
地本身喺中國**嘅曝險——中國進一步收緊 InP 出口,可以**同時**打生產同批次放行兩條線
(`thesis/themes.yaml:213-218`)。AXTI 同時出現喺 [[rare-earth-materials]] 嘅 ticker 表(唯一便宜咽喉
候選)同 [[photonics-optical]] 嘅節點表——兩個 theme 共用同一隻高風險票。

**最新讀數/裁決:** AXTI 曾被兩個 theme 都當「便宜錨」(ttm_pe 16.2、26 分位),但 **#141 修正咗呢個
判讀**——AXTI 當季轉虧(−14.7%)、預估 PE 72.8×、P/S 61×→38.6×(−41% vs 50 日均),原本嘅低 ttm_pe
係**盈利觸頂尾隨假象,唔係真.便宜**(`thesis/wiki/photonics-optical.md:52,83-85`;MP/AXTI 便宜咽喉框架
原文見 `thesis/wiki/rare-earth-materials.md:53-55` 表格,已被 #141 修正)。**呢隻票未標 `china-supply`
meta_factor**(theme 標籤係 `ai-capex`)——呢個係一個
標籤缺口:concentration.py 嘅 china-supply 集中度計算會漏計 AXTI 呢個全審查最高危嘅曝險(詳見第 4 節)。

**詳細檔案:** `thesis/wiki/photonics-optical.md`(AXTI 節點全文)+ `thesis/wiki/rare-earth-materials.md`
(AXTI 作為便宜咽喉候選嘅原始框架,已被 #141 修正)。

## Type A/B/C 分類表(from `backtest/results/2026-07-11_china_dependency_audit.md`,15 個 active theme 全覆蓋)

分類定義(audit `:35-42`):`TYPE_A` = 公司本身中國註冊/國家關聯(全審查未發現);`TYPE_B_MANUFACTURING`
= 境內設廠;`TYPE_B_SUPPLY_CHAIN` = 關鍵工序依賴中國;`TYPE_B_REVENUE` = 收入集中中國到政策衝擊會係
實質打擊;`TYPE_C_EXPORT_RESTRICTED` = 反向——俾政策(美國或中國)限制對中國銷售/採購。

### Table 1 — 15 個 theme 逐一 rollup

| Theme | meta_factor(s) | 審查票數 | headline 發現 | 出處(audit 行號) |
|---|---|---|---|---|
| memory-supercycle | ai-capex | MU/SNDK/WDC/SKHY(4) | 全部 4 隻均有實質 Type B 曝險;SKHY 最嚴重(無錫≈全球 40% DRAM) | `:128-136` |
| photonics-optical | ai-capex | COHR/LITE/AXTI/MRVL/AAOI/SIVE/LWLG/GLW/FN(9) | **AXTI 全審查最高危**(雙重曝險);AAOI/GLW 亦有實質中國製造;SIVE/LWLG/FN 乾淨 | `:138-146` |
| ai-power-grid | ai-capex | GEV/BE/VRT/ETN/PWR/MPWR/VICR/NVTS/WOLF/ON/TXN/GNRC/SPXC/CAT(14) | **全審查最大最重叢**——GEV 供應鏈斷點(CEO 親口確認)、MPWR 全審查最高依賴度(55.3% 中國營收+成都廠)、NVTS 最大營收集中(47-62%);PWR 乾淨 | `:148-167` |
| advanced-packaging | ai-capex | AMKR/ASX/TTMI/INTC/MKSI/KLAC/GLW/STX/WDC/KLIC/TER/FORM/LRCX(13) | KLIC 全審查**最清晰**中國營收披露(53.5% 10-K 逐字);ASX/AMKR/TTMI/STX 有實質製造;KLAC/TER/FORM/LRCX 係美國出口政策**削減緊**中國營收(反向) | `:169-178` |
| space-satellite | policy-defense | RKLB/ASTS/KTOS/HEI/LOAR/RDW/LUNR/BKSY/PL/GSAT(10) | **9/10 乾淨**,唯一例外 KTOS 係反向(俾中國 MOFCOM 拉黑名單)——確認呢叢真正與中國隔絕 | `:180-185` |
| rare-earth-materials | **china-supply** | MP/USAR(2) | MP 係教科書級 Type B(歷史 >90% 營收靠中國分離,已切零但產能依賴未完全脫鈎);USAR 乾淨 | `:187-200` |
| tpu-custom-silicon | ai-capex | AVGO/TSM/CLS(3) | TSM 中國故事係台海風險,唔係大陸依賴,唔應與其他名混為一談;AVGO ship-to 誇大;CLS 有蘇州/東莞製造 | `:202-211` |
| oil-gas-energy | energy-macro, ai-capex | XOM/CVX/COP/EQT/LNG/SEI/KMI(7) | 大致乾淨;LNG 有實質中美 SPA 合約曝險但物理交付已被貿易緊張打斷 | `:213-223` |
| semicap-equipment | ai-capex | AEHR(1) | 未證實間接曝險(經 onsemi 客戶集中,onsemi 自己有中國 JV) | `:225-232` |
| aerospace-specialty-alloys | aerospace-capex | ATI/CRS(2) | ATI 有已披露、具名嘅關鍵原料(鋯/鉿/鉬)中國依賴;CRS 只係製造/分銷層面,原料披露唔提中國 | `:234-242` |
| euv-lithography-monopoly | ai-capex | ASML(1) | Type C——中國曾係最大單一市場(33%→guided 降至~20%),MATCH Act 待審會全面禁 DUV 賣中國 | `:244-250` |
| **us-solar-manufacturing** | **trade-policy, china-supply** | FSLR(1) | Type C/B——製造非中國,但核心原料碲(中國控制 75-76% 產量)2025-02 已受出口許可管制 | `:252-261` |
| gas-compression-equipment | energy-macro, ai-capex | USAC(1) | 乾淨,交期由 Caterpillar 引擎供應主導,非中國 | `:263-265` |
| specialty-siding-pricing-power | building-products | LPX(1) | 乾淨,20+ 廠全在南北美洲 | `:263-265` |
| glp1-biologics-packaging | pharma-manufacturing | WST(1) | 有實質上海青浦兩廠(注塑/壓縮成型),但服務 APAC 區域市場,對主 thesis(Annex-1)低關聯 | `:267-275` |

### Table 2 — 全審查最高嚴重度票(cross-theme leaderboard,evidence confidence 按 audit 原文標)

| Ticker | Theme | 標籤 | 一手證據 | Evidence confidence | 出處 |
|---|---|---|---|---|---|
| **AXTI** | photonics-optical | TYPE_B_MANUFACTURING(HIGH)+ TYPE_B_SUPPLY_CHAIN(HIGH) | 10-K 逐字「全部 substrate 產品喺中國生產」;已被中國出口許可證掐停收入兩次(2023/2025) | **HIGH——全審查最高危一隻** | `:61` |
| **MPWR** | ai-power-grid | TYPE_B_MANUFACTURING + SUPPLY_CHAIN + REVENUE | 成都廠;10-K 自己列明中國供應商集中做 top risk;中國營收佔比 55.3%(升緊) | **HIGH——全審查最高依賴度一隻** | `:73` |
| **GEV** | ai-power-grid | TYPE_B_SUPPLY_CHAIN(HIGH)+ TYPE_C + MANUFACTURING | CEO Strazik(Reuters 2025-12)親口確認中國釔出口管制威脅 GEV 全球 H-class 燃氣渦輪機隊(葉片熱塗層) | **HIGH——全審查最尖銳供應鏈發現** | `:68` |
| **KLIC** | advanced-packaging | TYPE_B_MANUFACTURING + REVENUE | 蘇州廠;10-K 逐字「約 53.5% FY2025 營收嚟自中國總部客戶」 | **HIGH——全審查最清晰中國營收披露** | `:89` |
| **NVTS** | ai-power-grid | TYPE_B_REVENUE(severe) | 無廠(fabless);中國 47%(2025,降自 60-62%)——全審查最大營收集中度 | HIGH | `:75` |
| **MP** | rare-earth-materials | TYPE_B_SUPPLY_CHAIN(historical)+ REVENUE(ceased) | 歷史 >90% 營收靠賣精礦俾中國分離;已切零但重稀土分離產能依賴至 2026 中 | HIGH | `:103` |
| **TXN** | ai-power-grid | TYPE_B_MANUFACTURING + SUPPLY_CHAIN + REVENUE | 成都廠+晶圓凸塊;21% 客戶總部/約 50% ship-to;正被中國商務部反傾銷調查 | HIGH | `:78` |
| **CAT** | ai-power-grid | TYPE_B_MANUFACTURING(extensive)+ TYPE_C | 全審查製造足跡最深:6 個中國城市、4 個業務線、30 年歷史 | HIGH(mfg) | `:81` |
| **ASML** | euv-lithography-monopoly | TYPE_C(HIGH)+ REVENUE(reversing) | 中國曾係最大單一市場(33% FY25,Q3 一度衝 42%),政策guided降至~20%(2026);MATCH Act 待審 | HIGH | `:118` |
| **FSLR** | us-solar-manufacturing | TYPE_C + TYPE_B_SUPPLY_CHAIN(input) | 製造非中國,但核心原料碲(中國~75-76%產量)2025-02 已受出口管制;10-K 披露主動應對 | HIGH(管制)/MEDIUM(成本佔比) | `:119` |

**未證實/有爭議(唔可以當已確認事實讀):** LITE(製造地衝突未解決)、ON/GEV/VRT(中國營收 % 因披露口徑
被模糊)、CAT(冇披露稀土依賴,但未搜到唔等於冇)、BE(scandium 供應指控,公司自己否認,未解決)
(`backtest/results/2026-07-11_china_dependency_audit.md:279-295`)。

## 共同觸發事件:2026-11 中美協議

**單點:** 2026-11 美國期中選舉同月撞中國休戰到期——[[rare-earth-materials]] 嘅 kill_condition **明文
綁定**呢個calendar 日期:「2026-11 US-China formal deal fully lifts indium/gallium/heavy-REE export
controls」任一觸發即 confidence 歸零(`thesis/themes.yaml:574-579`)。[[ai-power-grid]] 嘅
kill_condition 亦已包含中國稀土/釔管制條款(「China tightens rare-earth/yttrium export controls
further, hitting GEV turbine-coating supply directly or MPWR/NVTS/TXN China revenue concentration」,
`thesis/themes.yaml:227-235`),雖然呢個 theme 本身**未標 `china-supply` meta_factor**(標嘅係
`ai-capex`)。

**相關性警示(meta_factor cap 存在嘅原因):** 一次中國政策衝擊(管制收緊或解除)**唔會只打正式標
`china-supply` 嘅 2 個 theme**——佢會同時觸及:
1. [[rare-earth-materials]](MP/USAR,直接綁定 2026-11)
2. [[us-solar-manufacturing]](FSLR,同一機制、但唔同 calendar——持續狀態非二元事件)
3. [[ai-power-grid]](GEV/MPWR/NVTS/TXN,kill_condition 已寫入但 meta_factor 未標)
4. [[photonics-optical]](AXTI,全審查最高危但 meta_factor 未標)
5. [[memory-supercycle]](MU/SNDK/WDC/SKHY 全部有實質曝險,`thesis/themes.yaml:133-137`)
6. [[advanced-packaging]] 部分(KLIC/ASX/AMKR/TTMI/STX)

**呢個係本頁要點名嘅結構性缺口:** `thesis/themes.yaml` 嘅 `meta_factor` 標籤目前只反映「thesis 敘事
主軸係咪中國供應鏈」,唔反映「呢個 theme 有冇實質中國曝險票」——[[ai-power-grid]] 同 [[photonics-optical]]
嘅敘事主軸係 AI capex(標 `ai-capex` 正確),但佢哋各自嘅個別票(MPWR/GEV/AXTI)喺中國依賴嚴重度上
**高過**兩個正式標 `china-supply` 嘅 theme 入面嘅大部分票。結果:`concentration.py` 現時計嘅
`china-supply` meta_factor 集中度(2 個 theme)**低估**咗真實嘅跨 theme 中國政策相關性尾部風險——一次
2026-11 級別嘅政策衝擊,實際同步曝險嘅 theme 數目遠多於 2 個。呢點供未來覆核參考,本頁**唔擅自改
meta_factor 標籤**(改標籤要喺 themes.yaml 同 lint.py 嘅 VALID_META_FACTORS 同一 commit 一齊改,
需要人手/agent 對每個 theme 逐一重跑「一句話因果測試」,超出本次聚合任務範圍)。

## 監察清單(全部引用現有 kill_condition/監察條件,無新增)

| 線 | 監察乜 | 出處 |
|---|---|---|
| 線一(rare-earth-materials) | **主單點:2026-11 中美是否達成正式協議解除管制**;陝西銦杰 250 噸 InP 良率進度;MP 的 DoD $110/kg 保底/Project Vault 撥款狀態;休戰是否無限期延長 | `thesis/wiki/rare-earth-materials.md:116-119` |
| 線二(us-solar-manufacturing) | 232/301 關稅或 IRA 本土成分規定會否被撤銷/豁免;「sold out」backlog 會否落空;**中國會否進一步收緊碲/CdTe 出口管制** | `thesis/wiki/us-solar-manufacturing.md:47-51`;`thesis/themes.yaml:857-862` |
| 線三(MP capex) | capex 融資結構會否轉債務型(現係 equity/政府背書型,轉型即真 P2 marker);$110/kg 保底/Project Vault 撥款狀態(同線一共用);2026-11 事件解決方向;產能會否 ramp AHEAD of 已鎖定需求(DoD/Apple/Vault) | `backtest/results/2026-07-13_mp_capex_da_review.md:115-121` |
| 線四(AXTI) | InP 短缺會否解除(交期壓縮/中國全面放行/新產能上線);**中國會否進一步收緊 InP 出口**(同時打生產同批次放行兩條線,dual-exposure) | `thesis/wiki/photonics-optical.md:110-116`;`thesis/themes.yaml:213-218` |
| 相鄰(ai-power-grid,未標 china-supply 但已入 kill_condition) | 中國會否進一步收緊稀土/釔出口管制,直接打 GEV 渦輪供應或 MPWR/NVTS/TXN 中國營收集中度 | `thesis/themes.yaml:227-235` |

## 來源

`backtest/results/2026-07-11_china_dependency_audit.md`(68 隻票全審查,6 個平行 subagent + WebSearch/
SEC EDGAR)、`backtest/results/2026-07-13_mp_capex_da_review.md` + `2026-07-13_mp_capex_da_history.md`
(MP capex/D&A 對抗式覆核,`backtest/experiments/exp_mp_capex_history.py` 可重跑)、`thesis/themes.yaml`
(rare-earth-materials/us-solar-manufacturing/photonics-optical/ai-power-grid theme 記錄)、
`thesis/wiki/rare-earth-materials.md`、`thesis/wiki/us-solar-manufacturing.md`、
`thesis/wiki/photonics-optical.md`(Tier-2 #078/#105/#115/#141 轉引,見各自「來源」段)。
