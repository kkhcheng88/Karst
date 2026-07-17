# thesis/.raw/fomosoc/ — FOMO 研究院(fomosoc.com)ingest 索引

- **來源**: FOMO 研究院,KP@FOMOSoc,https://www.fomosoc.com,約 5 萬訂閱
- **來源評估正本**: `backtest/results/2026-07-17_source_registry.md` §3b
- **本輪 ingest 報告(判詞正本)**: `backtest/results/2026-07-17_fomosoc_ingest.md`
- **首次 ingest**: 2026-07-17
- **抓取範圍**: `/api/v1/archive?sort=new&limit=40` 回傳 23 篇(2026-05-09 → 2026-07-15),其中 **10 篇深入分析/相關筆記已逐篇抓取**;餘 13 篇為 KP 思考筆記(免費 mega-cap 新聞綜合)+ 商周專欄轉載,未逐篇抓(見下「未抓」節)

---

## ⚠️ 三條使用紀律(讀本目錄任何檔之前必讀)

1. **本目錄所有檔都係 WebFetch(小模型)重構,唔係逐字原文。** `.raw` 慣例係「immutable full text for citation」—— **本目錄唔滿足呢個慣例**。引用任何句子/數字前**必須返原 URL 一手核對**。
2. **只用免費/牆前內容。** 用戶已定唔訂閱。牆後內容一律當「未讀」,唔准推測。
3. **單一策展渠道** —— 同 zsxq PDF 同等待遇:**唔准升 `n_sources`、唔准加 `sources:` 條目**。Level-1 red-team 級別,**唔可以升 confidence**。

---

## 逐篇索引

| 期 | 檔案 | 日期 | free/paid | 牆斬喺邊(免費 %) | 對應 theme | 判決 | 一句 |
|---|---|---|---|---|---|---|---|
| **#55**<br>3D封裝 | [`2026-07-15_3dhybrid-bondingbesiasmpt-553d.md`](2026-07-15_3dhybrid-bondingbesiasmpt-553d.md) | 2026-07-15 | only_paid | 第4章「為什麼會這樣?」後(**65-70%**) | `advanced-packaging` | **WEAKEN**(scoped) | 逐字「OSAT 幾乎無法參與」混合鍵合、價值歸晶圓廠+設備商(BESI/ASMPT,**全非美**)→ 獨立命中 07-16 red-team 已判嘅「OSAT proxy 唔捕捉真租金」;但只涵蓋 3D 段 TAM,且零出處 = 佐證非證據 |
| **#54**<br>玻璃基板 | [`2026-07-01_copostgv-54.md`](2026-07-01_copostgv-54.md) | 2026-07-01 | only_paid | 第4章標題後(**60-65%**) | `advanced-packaging`<br>(次 `photonics-optical`) | **WEAKEN(弱)**<br>+ **框架更正** | **CoPoS ≠ 玻璃**(形狀革命 vs 材料升級,**非硬性綁定**)→ 現有 note「CoPoS 坐實 GLW」唔成立,要拆兩軸;第4章標題(免費可見)逐字「上游玻璃材料:重要,但**不是你該下注的地方**」= 對 GLW 點名負面,但理據牆後、且屬循環論證 → 唔足以動 magnitude |
| **#53**<br>NAND 控制器 | [`2026-06-24_hbm-dramnvidia-ssd-53nand-flash-simo.md`](2026-06-24_hbm-dramnvidia-ssd-53nand-flash-simo.md) | 2026-06-24 | only_paid | 4.1 節標題(**65-70%**) | `memory-supercycle` | **NEUTRAL** | 標題主角 SIMO/群聯「**僅標題提及,內文未深入**」→ registry 講「免費段有 SIMO」係過樂觀;全篇零出處。**唯一美股 ADR 機會(SIMO)落空** |
| **#52**<br>功率半導體 | [`2026-06-17_sicgan800v-52.md`](2026-06-17_sicgan800v-52.md) | 2026-06-17 | only_paid | 第4章末(**40-45%**)⚠️**全批最低** | `ai-power-grid` | **NEUTRAL** | 標題問「誰是贏家」,免費段**一個贏家名都冇派**;17%/30% 滲透率無出處**且分母同我哋 kill 軸對唔上**;副產品:佢個「SiC 價值 50% 喺基板/上游咽喉」框架 vs **WOLF(美股唯一純 SiC 垂直整合)已破產** = 咽喉 ≠ 定價權嘅活教材 |
| **#51**<br>利率路徑 | [`2026-06-10_fed-51.md`](2026-06-10_fed-51.md) | 2026-06-10 | only_paid | 2.3 節中(**60-65%**) | **無**<br>(`rates-duration` = RESERVED/unused) | **NEUTRAL**<br>(範圍外) | **全批出處密度最高**(CME FedWatch 70%、FOMC 8-4、NFP +172k、失業率 4.3%)—— **但正因為宏觀數據本身就係公開具名,我哋一手攞得到**。出處密度高 ≠ 作者做咗功課 |
| **#50**<br>HVDC/台達電 | [`2026-06-03_800v-hvdc-50hvdc.md`](2026-06-03_800v-hvdc-50hvdc.md) | 2026-06-03 | only_paid | 3.1 節末(**45-50%**) | `ai-power-grid` | **NEUTRAL**<br>(**且無證據價值**) | ★ **開篇自認「本篇在撰寫時參考 SemiAnalysis 報告」→ 佢唔係獨立來源,係我哋已一手持有嘅 SemiAnalysis PDF 嘅二次轉述。「兩來源一致」係假象** |
| **#49**<br>GlobalFoundries | [`2026-05-27_3-49globalfoundries.md`](2026-05-27_3-49globalfoundries.md) | 2026-05-27 | only_paid | AMD 分拆史前(**65-70%**) | **無**(擦邊) | **NEUTRAL**<br>(範圍外) | GFS 唔喺任何 theme;係**代工平台唔係瓶頸擁有者**(同 CIEN 剔除先例同構);⚠️ 兩個數字(「$70B 營收」「$375B 隱含估值」)表面上差一個數量級,未一手核實,唔用 |
| **#48**<br>DCI | [`2026-05-20_dci-48nokiacisco.md`](2026-05-20_dci-48nokiacisco.md) | 2026-05-20 | only_paid | 第3章末(**~67%**) | `photonics-optical`(弱) | **NEUTRAL** | 一篇專講 DCI 嘅文,由頭到尾冇提 COHR/LITE/CIEN —— **但呢個係 argument from silence + 全篇 99% 無出處 → 零證據價值**;佢捧嘅 Nokia/Cisco 正正係 theme 已判過唔要嗰類「系統整合商非組件擁有者」 |
| **#47**<br>Cloudflare | [`2026-05-13_aiagentic-ai-47cloudflare.md`](2026-05-13_aiagentic-ai-47cloudflare.md) | 2026-05-13 | only_paid | 第5章(**~35-65%**,WebFetch 自相矛盾未核實) | **無** | **NEUTRAL**<br>(範圍外) | NET 已於 2026-07-15 正式判出 Karst 範圍;純軟體;唯一具名數(Dell'Oro Zscaler 34%)同我哋無關 |
| **#55**(撞號)<br>Datadog | [`2026-07-08_ai-ai-55datadog.md`](2026-07-08_ai-ai-55datadog.md) | 2026-07-08 | only_paid | 2.4 節後(**65-70%**) | **無** | **NEUTRAL**<br>(範圍外) | 純軟體/可觀測性;**零具名出處**;⚠️ 同 3D 封裝篇撞「第55期」—— 作者自己編號有錯,**引用用 slug+日期,唔好用期數** |
| **#46**<br>KP 筆記 | [`2026-06-13_800-vdcspacex-ipowwdc-kp46.md`](2026-06-13_800-vdcspacex-ipowwdc-kp46.md) | 2026-06-13 | **everyone**<br>(免費,無牆) | **無牆** | `ai-power-grid` | **NEUTRAL** | ★ **全批對 ai-power-grid 資訊量最高嘅一篇 —— 而佢係免費文**。引 SemiAnalysis(native 800VDC 推遲 2028+)+ **摩根士丹利具名反駁**(供應鏈調查話冇延誤)+ **Google/Meta 傾向 ±400V**(open question) |

---

## 判決分佈

| 判決 | 篇數 | 篇目 |
|---|---|---|
| **WEAKEN** | **2** | #55 3D封裝(scoped)、#54 玻璃基板(弱)+ 框架更正 |
| **NEUTRAL(theme 相關)** | 4 | #53、#52、#50、#48、#46 |
| **NEUTRAL(範圍外)** | 4 | #51、#49、#47、#55 Datadog |
| **STRENGTHEN** | **0** | — |

**零 STRENGTHEN。** 十篇入面冇一篇提供到可以升 confidence 嘅獨立硬證據(而且 Level-1 本身就唔准升)。

---

## 未抓(誠實記錄)

archive 回傳 23 篇,以下 13 篇未逐篇抓,理由如下:

- **KP 思考筆記 #41–#50(免費,週更)** — 已抓 #46(因為佢直接講 800VDC)。其餘(#41 高盛 AI 拐點/CPU、#42 Cerebras 上市、#43 SpaceX IPO、#44 Tesla-SpaceX 合併/Anthropic、#45 AI PC/記憶體需求減半、#47 SpaceX 收購 Cursor/微軟甲骨文、#48 蘋果美光交火/SK 減產 HBM、#49 Meta 算力過剩/Palantir、#50 Nvidia 延期/SK ADR/Meta)= **mega-cap 新聞綜合**,registry §3b 已評估過(1 篇免費全文 + 20 預覽)。
  ⚠️ **未抓 = 未證實。** 當中 **#45「記憶體需求減半」** 同 **#48「SK 海力士減產 HBM」** 標題上同 `memory-supercycle` 嘅 kill 軸(「HBM/advanced-packaging capacity ramps AHEAD of demand → glut」)方向相關 —— **呢兩篇係本輪最明顯嘅未覆蓋缺口,建議下輪優先**(見 ingest 報告「未解/風險」節)。
- **KP 商周專欄(#2002–#2010,3 篇合輯,`only_paid`)** — 報章專欄轉載,非供應鏈研究。

---

## 下輪抓文備忘

- API: `https://www.fomosoc.com/api/v1/archive?sort=new&limit=40` → slug / title / post_date / audience
- 全文: `https://www.fomosoc.com/p/<slug>`
- WebFetch 有 15 分鐘 cache,同一 URL 唔使重抓
- **牆位會隨文變**(實測 40-70%),**唔好假設 70-80%**
