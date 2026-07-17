# KP 思考筆記(第46期):800 VDC 延期了?SpaceX IPO 後會如何?WWDC 沒有新意?

- **URL**: https://www.fomosoc.com/p/800-vdcspacex-ipowwdc-kp46
- **日期**: 2026-06-13
- **作者**: KP@FOMOSoc
- **audience**: `everyone`(**免費**,無牆)
- **牆斬喺邊**: **無牆,全文免費**
- **對應 theme**: `ai-power-grid`
- **判決**: **NEUTRAL** —— 但**係全批對 ai-power-grid 資訊量最高嘅一篇**(諷刺:免費文 > 收費文)

> ⚠️ **本檔係 WebFetch(小模型)重構,唔係逐字原文。** 引用前必須返原 URL 核對。
> 只抓咗 800 VDC 一節(SpaceX IPO / WWDC 兩節同任何 theme 無關,略)。

---

## 一、核心內容(800 VDC 節)

**延期主張(來源:SemiAnalysis — 具名)**:

> 「NVIDIA『原生』的 800V 直流電架構,大規模出貨時間已經**推遲到 2028 年或更晚**,比市場先前預期的 **2027 年**放量要慢得多。」

**反駁(來源:摩根士丹利 — 具名)**:

> 摩根士丹利聲稱「**供應鏈調查顯示 800V 直流電根本沒有延誤**」,但**未引用具體 SemiAnalysis 內容**。

**KP 自己嘅結論**:「**兩方都對,只是討論不同『樓層』**」——
- **第一階段:外掛式電源櫃(Sidecar)** — **2026 下半年**
- **第二階段:原生 800V 架構(Native)** — **2028 年或更晚**

**具名公司**:
- **NVIDIA** — 推動純 800V 方案,被指延遲至 2028 後
- **台達電** — 被**摩根士丹利點名**為「台灣電源龍頭」,**第三季準備 800V 電源機櫃量產**(台股,非美)
- **Google、Meta** — 傾向採用**替代方案(±400V)**

## 二、★ 同已 ingest 嘅 SemiAnalysis PDF 對帳

| 項目 | SemiAnalysis PDF(一手,2026-05-26,已 ingest) | FOMO #46(2026-06-13,轉述) | 一致? |
|---|---|---|---|
| 階段框架 | **Phase 1–4** | **兩階段**(Sidecar / Native) | **簡化咗**(4→2) |
| Sidecar 時程 | Phase 1 White-Space Retrofit **late-2026/2027** | 2026 下半年 | **一致** |
| Native 時程 | Phase 2 Turning Point **2027/2028**(800VDC-native compute 物理強制) | **2028 或更晚** | **FOMO 偏悲觀半年** |
| 灰空間集中整流 | Phase 3 **late-2028/2029** | **冇提** | 丟失 |
| SST 終局 | Phase 4,**唔預期 at-scale 直到 early-2029** | **冇提** | 丟失 |
| TAM / ASP | sidecar TAM ~$11B(2028)、SST ~$13B(2030)、HVDC rack ASP $400-500K | **冇提** | 丟失 |
| 可觀測錨 | UL 認證(as of 2026-05 冇 vendor 完成)、NEC 2029 code、3300V+ SiC limited production | **冇提** | 丟失 |

**判**:FOMO #46 = SemiAnalysis 四階段曲線嘅**兩階段簡化版**,方向一致但**丟失晒所有可觀測錨同量化**。→ **引用一律引 PDF 一手。**

## 三、★ FOMO 版**獨有**、PDF ingest record **冇**嘅兩樣嘢

1. **摩根士丹利嘅反駁** —— 「供應鏈調查顯示根本冇延誤」+ 台達電 Q3 量產 800V 電源機櫃。
   - **價值**:呢個係一個**具名嘅對立賣方觀點**。我哋 kill 軸「800V/HVDC native mass-production (SemiAnalysis stages 3-4) slips again」**完全建基喺 SemiAnalysis 一家嘅曲線上**。MS 反駁 = 提醒呢條軸嘅**觀測基準本身有爭議**。
   - ⚠️ **但 FOMO 冇引 MS 報告日期/標題,亦冇引 SemiAnalysis 原文** → 兩邊都係轉述。**唔可以當證據,只可當「呢條軸有 disagreement」嘅提示。**
   - ⚠️ 亦要留意:**MS 講「冇延誤」嘅證據係台達電 Q3 量產 sidecar 機櫃** —— 而 SemiAnalysis 講「延誤」講嘅係 **native**。KP 自己都話咗兩方講緊唔同樓層。**即係 MS 嘅反駁根本冇反駁到 kill 軸講嘅嘢(native)。** → **kill 軸站得住,唔使改。**

2. **Google / Meta 傾向 ±400V** —— ⚠️ **呢個我判唔到,誠實標明。**
   - 業界慣例:「800VDC」好多時**就係**用 ±400V(對地 ±400V = 800V 差動)實作。→ 咁樣嘅話 ±400V **唔係替代方案,佢就係 800VDC**,FOMO 呢句可能係**概念混淆**。
   - 但亦有可能佢指嘅係真正嘅 ±400V 匯流排(800V 總線嘅另一種拓撲),影響逐層含量分配。
   - **免費段解唔到,PDF ingest record 亦冇呢條。→ 記做 open question,唔開新 kill 軸。**(如果係真嘅替代路線,咁 kill 軸「800V native slips **OR** 48V stays good-enough」就漏咗第三條路;但我而家冇證據。)

## 四、★ 作者內部一致性檢查(#46 vs #52,相隔 4 日)

| | #46(2026-06-13,**免費**) | #52(2026-06-17,**收費**) |
|---|---|---|
| 800V framing | **標題就係「800 VDC 延期了?」**;主文引 SemiAnalysis 話 native 推遲到 2028+ | 「**無延遲**」,呈現快速上升曲線;SiC/GaN 資料中心電源滲透率 **2026 = 17% → 2030 = 30%**(**無出處**) |

**判**:**唔算硬矛盾**(#46 講 native 800VDC 機櫃架構;#52 講 SiC/GaN 器件滲透率 —— 唔同嘢),**但係一個 framing 不一致**:同一作者四日內,免費文以「延期」開題,收費文以「無延遲、17% 滲透」開題,而收費文**冇帶返自己四日前引嘅 SemiAnalysis 延期 caveat**。
→ **對來源評估嘅意義**:唔可以淨係讀佢一篇就當攞到佢個 view;佢**兩條線(免費筆記 / 收費深度)之間唔互相 reconcile**。

## 五、US-listed 過濾

| 公司 | 上市地 | 喺 Karst? |
|---|---|---|
| NVIDIA | 美股 | 否(下游需求,theme note 明確 excluded) |
| **台達電** | **台灣 — 非美** | 否 |
| Google / Meta | 美股 | `mag7-hyperscaler`(下游需求) |

**US-listed 新增可表達標的:0。**

## 六、Level-1 red-team

- [x] 觸及承重 claim?**係(輕微)** —— kill 軸「stages 3-4 slips」嘅觀測基準有具名對立觀點(MS)。
- [x] 抵觸 kill 軸?**表面上似,實際否** —— MS 反駁講嘅係 sidecar(台達電 Q3),SemiAnalysis 講嘅係 native。兩者唔衝突,kill 軸完好。
- [x] 平庸解釋:「兩方都對,只係講唔同樓層」本身就係最平庸嗰個解釋,而且**啱**。
- → **入 review queue(±400V open question),唔郁 confidence。**

## 七、判決

**NEUTRAL** — 零 Tier-1、零新公司事實、US-listed 新標的 0。但係本批**對 ai-power-grid 資訊量最高**嘅一篇,而且**佢係免費文**。
兩個有用副產品:(a) MS 具名反駁提醒 kill 軸建基單一曲線 —— 覆核後**軸站得住**(MS 冇反駁到 native);(b) **±400V open question** 記入 review queue。
`ai-power-grid` confidence 0.40 維持。
