# 深入分析第55期:3D封裝 — 混合鍵合被推遲了?BESI、ASMPT 與韓美的設備大鬥法

- **URL**: https://www.fomosoc.com/p/3dhybrid-bondingbesiasmpt-553d
- **日期**: 2026-07-15
- **作者**: KP@FOMOSoc
- **audience**: `only_paid`(收費文)
- **牆斬喺邊**: 第四章「第二個戰場:高頻寬記憶體」最後一問「為什麼會這樣?」之後即斬。**約 65-70% 免費**
- **對應 theme**: `advanced-packaging`
- **判決**: **WEAKEN**(scoped — 見下)

> ⚠️ **本檔係 WebFetch(小模型)重構,唔係逐字原文。** 引用任何句子前必須返原 URL 核對。
> ⚠️ **牆後內容(「邊個贏」/BESI vs ASMPT vs 韓美設備商鬥法)冇讀過** —— 標題主打嘅設備大鬥法正正喺牆後。

---

## 一、硬規格(可驗證,但**全部冇具名出處**)

⚠️ **重要修正 source registry §3b**:registry 話「#55 規格紮實」。規格**存在且對得上公開常識**,但**逐條零出處**——冇 filing、冇業績會、冇具名報告。屬「**可獨立驗證但未引用**」,同 §3 講嘅「專家話」型偽證據**唔同級**(嗰啲驗都驗唔到),但**仍然唔可以直接當可引用證據**。要用要自己去 TSMC/ECTC 一手驗。

| 規格 | 數值 | 出處 |
|---|---|---|
| 傳統 micro-bump 間距 | 30–40 μm | 無 |
| TSMC 混合鍵合現行間距 | **6 μm** | 無(「台積電的混合鍵合技術已經能做到」) |
| TSMC 2029 目標間距 | **4.5 μm** | 無(「根據最新規劃」) |
| TSMC 實驗室原型 | **3 μm** | 無 |
| 表面粗糙度要求 | **< 1 nm** | 無 |
| 對準精度要求 | **< 100 nm** | 無 |
| Intel Foveros Direct 3D 鍵合間距 | **9 μm** | 無(2026 Clearwater Forest Xeon 導入) |
| Broadcom 2nm AI 晶片 face-to-face | 通道 **+7x**、功耗 **-90%** | 無 |
| HBM 層數 | 8 → 12 → 16(HBM4 原預期) | 無 |

## 二、事實性敘述(冇出處,但屬業界公開史實)

- **Sony 2015** 首個混合鍵合大規模量產(手機 CIS,畫素+邏輯直接導通);技術源頭 = 向美國 **Ziptronix** 授權嘅 **DBI** 製程。
- **AMD 2022** 3D V-Cache = 首個把混合鍵合用喺邏輯產品(SRAM 疊 CPU 上)。成功關鍵 = 記憶體發熱量低。
- **Apple M5(2026)** 首次用 TSMC SoIC 把 CPU/GPU 拆 chiplet 上下疊。原文:「**根據分析**,這是 Hybrid bonding 技術首次應用在消費級運算產品上」——「根據分析」=**冇講邊個分析**。
- **Intel** Foveros → Foveros Direct 3D;因堅持自主製造 + 先進製程受挫 → **商業化延遲**,2026 先喺 Clearwater Forest 導入。

## 三、★ 承重段落:第 3.5 節「價值被誰賺走了?」——本檔最重要嘅嘢

原文(重構):

> 「在這個領域,**傳統獨立封測代工廠(OSAT)幾乎無法參與**。混合鍵合對潔淨度與精度的要求極高,製程步驟與前段晶圓製造高度重合,因此這項技術基本上**被鎖在晶圓代工巨頭(如台積電)與整合元件製造商(如 Intel)的體系之內**。
>
> 價值的最大受益者主要有兩類:
> - 掌握先進製程與封裝平台的晶圓廠(例如提供 SoIC 的台積電)
> - 提供關鍵設備的製造商(高精度混合鍵合機台、超平整化 CMP 設備等)」

**對 Karst 嘅意義**:`advanced-packaging` 現行 `osat-arms-dealers` node(AMKR/ASX,theme note 逐字「Prefer arms-dealers AMKR/ASX (whoever wins gets paid)」,magnitude 2-3x,叢中最乾淨護城河)——**呢句直接講 OSAT 喺呢條線收唔到錢**。

**但要 scope 清楚,唔可以overclaim**:
- 命中嘅係 **3D / 混合鍵合** 呢一段。**2.5D CoWoS 級封裝、format-war 軍火商論點冇被呢篇否定**(#131 嘅原論點係封裝格式戰邊個贏都收單,主要講緊 2.5D/中介層層面)。
- 即係話:**「whoever wins gets paid」呢個 claim 有一個佢冇涵蓋嘅缺口 —— 當贏家係「3D 混合鍵合」嗰陣,收錢嘅唔係 OSAT。**

## 四、★ TCB / KLIC 雙向影響(本篇最 nuanced 嘅發現)

- **長線逆風**:原文明講 TCB(熱壓鍵合)係中間世代 ——「只要接點裡還有錫存在,在極度微小的空間裡加熱擠壓,錫就會像果醬一樣往外溢出,導致短路」→ 所以先要行去混合鍵合(無焊料)。`advanced-packaging` 把 **KLIC** 收入 `process-equipment-test` node 嘅理由逐字係「**TCB 熱壓鍵合直接受惠**」(#150)。**混合鍵合成功 = TCB 被取代 = KLIC 呢條理由到期。**
- **近端順風**:本篇標題本身就係「混合鍵合**被推遲了**?」,第四章講 HBM「已經蓋了好幾年大樓、層數從 8 層一路飆到 16 層,**卻遲遲不肯換上這項新技術**」→ HBM 未轉混合鍵合 = **TCB 壽命延長** = KLIC 近端受惠。
- **淨判**:KLIC 嘅 TCB 論點係一個**有到期日嘅論點**,到期日 = HBM 幾時轉混合鍵合。→ **kill_metric 候選**(見 ingest 報告)。
- ⚠️ 「HBM 點解唔轉」嘅答案**喺牆後**,我讀唔到。

## 五、US-listed 過濾

| 公司 | 上市地 | 可表達? | 喺 Karst? |
|---|---|---|---|
| **BESI**(Be Semiconductor) | 阿姆斯特丹 Euronext | **非美 → 只做證據** | 否(advanced-packaging note 已記錄唔入 tickers) |
| **ASMPT** | 香港 | **非美 → 只做證據** | 否(同上) |
| **Ziptronix** | 已被 Xperi/Adeia 收購(歷史主體) | 非直接 | 否 |
| **Sony** | 東京(有 ADR SONY) | 邊緣 | 否 |
| **TSMC** | 台灣(ADR **TSM**) | **US-listed(ADR)** | theme note 逐字「TSM is the eroded incumbent (not a long)」 |
| **Intel (INTC)** | 美股 | **US-listed** | ✅ 已喺 tickers(`emib-optionality` node) |
| **AMD** | 美股 | US-listed | 否(下游設計) |
| **Broadcom (AVGO)** | 美股 | US-listed | 否 |
| **Apple (AAPL)** | 美股 | US-listed | 否 |

**US-listed 覆蓋率(本篇點名嘅價值捕獲者)**:原文話價值歸「晶圓廠 + 設備商」。晶圓廠 = TSMC(theme 明確唔做多頭)/ Intel(已有,但係 option 框架)。設備商 = **BESI / ASMPT,兩個都非美**。→ **本篇點名嘅贏家,美股可乾淨表達嘅係零。**

## 六、Level-1 red-team 檢查(nightly 級,唔可升 confidence)

- [x] 觸及承重 claim?**係** —— `osat-arms-dealers` 嘅「whoever wins gets paid」+ KLIC 嘅 TCB 理由。
- [x] 抵觸 kill 軸?**部分** —— kill 有一條「the packaging format war resolves to a single winner, draining the AMKR/ASX arms-dealer premium」。本篇冇話格式戰解決咗,但話**有一個格式(3D 混合鍵合)由頭到尾都唔經 OSAT** → 係 kill 軸嘅**一個未被涵蓋嘅變體**。
- [x] 平庸解釋測試:混合鍵合鎖喺 foundry/IDM 體系,係咪只係「新技術初期都咁,成熟咗會外流去 OSAT」?**有可能**,歷史上覆晶/TCB 都係由 foundry 行先再外流。本篇冇處理呢個反駁,我亦冇證據判。**記低做 open question,唔當定論。**
- → **入 review queue,唔郁 confidence。**

## 七、判決

**WEAKEN(scoped)** — 獨立命中 `advanced-packaging` 2026-07-16 red-team 已判嘅「OSAT 交易 proxy 唔捕捉真正租金(moat 2→1)」,但只涵蓋 3D/混合鍵合段 TAM,唔係全 theme;且本篇零具名出處 → **係佐證,唔係證據**。confidence 維持 0.30(已受 single-source cap 綁)。
