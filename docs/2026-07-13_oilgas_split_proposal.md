# oil-gas-energy 拆成兩個獨立 thesis — 方案【待用戶拍板先執行,現階段唔郁 themes.yaml】

**Date:** 2026-07-13
**狀態:** ⚠️ **方案(PROPOSAL ONLY)。本文件唔改任何 registry/wiki;themes.yaml 完全唔郁。** 待大腦轉交
用戶、用戶拍板後先由另一個任務執行遷移。
**動機:** magnifier per-node batch 2 期間,Fable 交接書明示:oil-gas-energy **直接拆兩個獨立 thesis
(oil leg / gas leg),唔好 node 化**。因為呢個 theme 唔係「一條價值鏈嘅唔同節點」(嗰種先適合 node 塊),
而係**兩條方向/週期/驅動都唔同嘅子鏈被硬綁埋**——node 塊解決唔到,拆 thesis 先啱。

## 0. 點解係拆 thesis 而唔係起 nodes(判斷依據)
`thesis/wiki/oil-gas-energy.md` 自己一句話已經寫明:「**這叢不是一個 thesis、是兩個被硬綁在一起的能源
子鏈**」。themes.yaml 現有 note 逐字:「THIN (2 reports) + heterogeneous ... Not one thesis -> WATCH split
by track」。兩腿嘅本質差異:

| | 原油腿(oil leg) | 天然氣→電力腿(gas leg) |
|---|---|---|
| 驅動 | 布蘭特/原油價格(價格接受者) | LNG 外銷 + Permian/Appalachian gas + **AI 表後電力(BTM)** |
| 週期方向 | 近端**偏空/超級過剩**(OPEC+ 瓦解、中國需求十年低) | 結構**成長**(AI capex >$700B 拉表後電力) |
| 報告立場 | #116 **neutral**(供給恢復三力先贏) | #058 **bull**(SEI 3.1 GW BTM buildout) |
| 護城河 | 無(油商係價格接受者,OPEC+ 護城河崩) | 有(SEI 表後全包咽喉 + EQT 便宜氣源) |
| meta_factor 因果 | 油價(energy-macro) | LNG/Permian(energy-macro)+ **AI 表後(ai-capex)** |

**node 塊會強迫佢哋共享 theme-level confidence / cycle_stage / kill_condition,但佢哋根本冇共同方向**——
呢個正正係 Fable 話「拆 thesis 唔好 node 化」嘅原因。(對比 memory/space:嗰兩個係**單一方向主題**內部嘅
價值鏈節點成熟度差異 → 適合 node 塊;oil-gas-energy 係**兩個方向相反嘅主題** → 適合拆 thesis。)

---

## 1. 兩個新 thesis 嘅 slug / tickers 分配

現有 7 隻 ticker(themes.yaml):`XOM, CVX, COP, EQT, LNG, SEI, KMI`

### 1a. 原油腿 → 新 thesis(建議 slug:`oil-majors`)
- **tickers:** `XOM, CVX, COP`(整合油商 XOM/CVX + E&P 純上游 COP)
- 角色:全部布蘭特/原油價格 beta;油商紀律佳但供給頂訊號喺體制外(OPEC+/UAE 增產,美股 capex 讀唔到)。
- alt slug 候選:`crude-oil-majors` / `oil-beta`。(揀 `oil-majors` 最直白。)

### 1b. 天然氣→電力腿 → 新 thesis(建議 slug:`natgas-ai-power`)
- **tickers:** `EQT, LNG, KMI, SEI`
  - `EQT` — 阿帕拉契天然氣 E&P、全叢唯一便宜(ttm_pe 10/35%)、BTM 氣源、資本紀律最健康
  - `LNG` — Cheniere 天然氣出口(⚠中國買家合約曝險,見下 §5 caveat)
  - `KMI` — Kinder Morgan gas gathering/processing、LNG 外銷帶動產能緊(2023-10 transcript datapoint)
  - `SEI` — Solaris 表後電力全包、氣→電、3.1 GW 已簽約、AI 拉動(**唯一 bull 名但最貴 + 治理二元**)
- alt slug 候選:`gas-lng-power` / `natgas-btm` / `gas-to-electron`。(揀 `natgas-ai-power` 因為佢同時
  captures LNG 外銷 + BTM AI 電力兩條氣需求腿,同 ai-capex meta_factor 呼應。)

**驗算覆蓋:** 3 + 4 = 7 = 現有全部 ticker,無遺漏、無重複。XLE/XOP(ETF)歸原油腿(見 §4)。

---

## 2. 各自嘅 kill_condition 草稿

### 2a. `oil-majors` kill_condition(草稿)
> WATCH-grade,near-term 偏空框架。可證偽升/降級:布蘭特**決定性收復 > $90**(Hormuz 暗航油輪遭攻擊
> → 保險暴漲 → 實質中斷,**或** OPEC+ 重拾配額紀律)→ 推翻「超級過剩/近端偏空」框架、需改寫成多頭;
> **反之布蘭特跌破 $60**(中國需求續崩)→ 能源類股長多腿(Pies 長腿)亦破。若布蘭特喺 $60-90 靜靜
> range、無新催化 → 原油退化成純 beta → **下架、無 thesis**(呢個係本腿最可能結局,要老實寫)。
> 觸發 → confidence 歸零。

### 2b. `natgas-ai-power` kill_condition(草稿)
> **氣電 BTM 腿:** SEI **治理二元惡化**(Morpheus 空報告指控坐實 / KTR 續拋 / 主要長約被解約,#049)
> **或** AI 表後 capex 停滯(hyperscaler 砍單)→ 氣電多頭腿(#058)歸零。
> **LNG 外銷腿:** 中國買家永久退出約 25 mmtpa 美國 LNG 合約(2026-02 已報導實際停止提貨、轉賣第三方,
> 見 §5)**或** Permian/Appalachian gas gathering 產能 ramp 超前 LNG 外銷 + AI 電力需求 → 天然氣過剩。
> **氣源腿:** EQT 資本紀律逆轉(capex 由平轉狂擴)或阿帕拉契氣價結構性轉跌。
> 任一腿觸發 → 該腿 confidence 歸零;全腿失 edge → 下架。

---

## 3. confidence 建議(INITIAL/uncalibrated,待用戶拍板;拆完各自獨立校準)

現有合併 confidence = **0.25**(base 4/8=0.50 × ~0.50 penalty)。拆後兩腿唔應該都係 0.25——合併嗰個係
兩腿溝出嚟嘅平均,拆開後要各自反映腿本身強弱:

| 新 thesis | 建議 confidence | 理據(相對合併 0.25) |
|---|---|---|
| `oil-majors` | **~0.18-0.20** | **弱腿**:報告 neutral(#116)、near-term 偏空、油商無定價權、OPEC+ 護城河崩、油需求結構衰退、最可能結局 = degrade-to-beta。低過合併 0.25 合理。 |
| `natgas-ai-power` | **~0.25-0.28** | **強腿**:有 bull 名(SEI #058)、EQT 便宜+紀律+AI 拉、真 BTM 咽喉 + 新 TAM(AI 電力)。**但**仍 THIN(每腿得 1-2 篇)+ SEI 貴(97 分位)+ 治理二元 → 唔應該高過 memory 0.38 / 光通訊 0.30 太多。維持 WATCH-grade。 |

**兩腿都仍係 THIN 證據**(oil 1 篇 neutral、gas 1 篇 bull + 1 篇 cross-cluster #049 + KMI transcript
datapoint)→ 建議兩個新 thesis 開頭都標 `verdict: thin-watch-*`,唔即刻當方向 thesis,同現狀一致。
拆嘅目的係**畀兩腿各自獨立追蹤/校準/sizing**(唔再被對方溝淡),唔係即刻升級信心。

---

## 4. meta_factors 分配 + concentration.py 影響(重要)

現有:`oil-gas-energy: meta_factors: [energy-macro, ai-capex]`(2026-07-12 補標 ai-capex 因 gas-power leg
= AI 表後 capex)。拆後:

| 新 thesis | meta_factors | 因果句測試(WS3 §1a 規則0) |
|---|---|---|
| `oil-majors` | `[energy-macro]` | 「油價冧 → XOM/CVX/COP 全部盈利縮」= PASS。**drop ai-capex**(油商同 AI capex 冇因果)。 |
| `natgas-ai-power` | `[energy-macro, ai-capex]` | energy-macro:「LNG 外銷/氣價冧 → EQT/LNG/KMI 傷」;ai-capex:「AI 表後 capex 停 → SEI/EQT-BTM 腿歸零(kill_condition 自己嘅觸發器)」= 兩個都 PASS。 |

**concentration.py 影響(要喺遷移時一齊核對):**
- **energy-macro:** 現有 2 member(oil-gas-energy + gas-compression-equipment)→ 拆後 **3 member**
  (oil-majors + natgas-ai-power + gas-compression-equipment)。仍 ≥2 → hub page 仍需要(現時 MISSING/backlog,
  `thesis/wiki/` 冇 energy-macro hub)。**拆完 energy-macro 反而更應該寫 hub**(3 個成員)。
- **ai-capex:** 現有 9 member(含 oil-gas-energy,54.9% > 50% cap 已在 WARNING)。拆後:oil-majors **甩走**
  ai-capex,natgas-ai-power **接上** ai-capex → member 數 **淨不變(9)**,但 **confidence-weight 輕微下降**
  (原本 oil-gas-energy 全 0.25 計入 ai-capex,拆後只有 natgas-ai-power 嗰~0.25-0.28 計入,oil 腿嗰份唔再
  計)。**方向係好嘅**:略為紓緩 ai-capex 54.9% 超標。**建議遷移後重跑 concentration.py 確認新 %。**

---

## 5. 邊個 wiki 頁要拆 / 點拆

現有:`thesis/wiki/oil-gas-energy.md`(一頁,兩腿混寫)。建議拆成兩頁:

| 新 wiki | 由現頁邊部分搬過去 | frontmatter tickers |
|---|---|---|
| `thesis/wiki/oil-majors.md` | 原油 mermaid 上半(GEO/OPEC/SANC → CRUDE → MAJ/EP/ETF)、XOM/CVX/COP/XLE/XOP ticker 行、KPI 嘅原油部分、cycle_stage 原油部分、#116 來源、kill 原油腿 | `[XOM, CVX, COP, XLE, XOP]` |
| `thesis/wiki/natgas-ai-power.md` | 氣鏈 mermaid 下半(GAS/EQT/LNG/SEI/AICAP/SALP/BTM/GOV)、EQT/LNG/KMI/SEI ticker 行、KPI 嘅氣電部分、cycle_stage 氣電部分、#058 + #049 來源、kill 氣電腿 | `[EQT, LNG, KMI, SEI]` |

**跨頁 cross-link 要處理:**
- **#049(SEI 治理二元)** 係 cross-cluster 來源(同 ai-power-grid 叢共享)→ 跟 gas leg(`natgas-ai-power`),
  並喺 ai-power-grid wiki 保留 cross-link。
- **SEI/EQT 嘅 BTM 重疊**:`natgas-ai-power` 同 `ai-power-grid` 都掂 BTM(SEI 一度同屬兩叢)——喺兩頁互相
  cross-link,講清邊條腿主管 SEI(建議 SEI 主歸 `natgas-ai-power`,ai-power-grid 保留 BTM 提及做 cross-link)。
- **energy-macro hub(MISSING)**:拆完應該順手寫 `thesis/wiki/ai-capex-macro-risk.md` 同款嘅
  `thesis/wiki/energy-macro-hub.md`,覆蓋 oil-majors + natgas-ai-power + gas-compression-equipment 三個
  成員(呢個係 backlog,拆 thesis 係好時機一齊補)。

---

## 6. 遷移步驟(執行清單,待用戶拍板;唔好未拍板就跑)

1. **Backup** `thesis/themes.yaml` → `~/.claude/backups/themes.yaml.<date>.oilgas-split.bak`(硬規則6)。
2. **themes.yaml:** 移除 `oil-gas-energy` theme 塊;新增 `oil-majors`(XOM/CVX/COP,meta_factors [energy-macro])
   + `natgas-ai-power`(EQT/LNG/KMI/SEI,meta_factors [energy-macro, ai-capex])兩個新塊,各帶 §2 kill_condition
   草稿、§3 confidence、`verdict: thin-watch-*`、`admitted: <date>`、sources(oil→#116;gas→#058/#049)。
3. **meta_factor registry header comment**(themes.yaml 頂):更新 energy-macro 成員(2→3)+ ai-capex 註記
   (oil-gas-energy 拆走、natgas-ai-power 接上);移除 header 入面「oil-gas-energy(oil-price leg only after
   the 2026-07-12 split)」嗰句改成反映實際已拆。
4. **wiki:** 依 §5 拆 `oil-gas-energy.md` → `oil-majors.md` + `natgas-ai-power.md`(中文內容用 Read/Write
   工具,硬規則2);處理 cross-link;考慮補 energy-macro hub。
5. **universe.yaml:** 現時 XLE 同時掛 parent_proxy + thesis_etf 指向 oil-gas-energy(themes.yaml note 有記)
   → 改指 `oil-majors`(XOM/CVX/COP 本身就係 XLE 最大持股);XOP 同樣歸 oil-majors。**gas leg 冇乾淨 ETF**
   (FCG only 4% EQT,見 ai-power-grid note)→ 單名表達或 skip。核對 universe.yaml 有冇其他 oil-gas-energy
   grouping 引用要改。
6. **cross-references 全掃:** grep repo 搵 `oil-gas-energy` 字串(ai-power-grid wiki/note 提及 EQT/SEI BTM、
   SALP 換邊、STATUS.md、INDEX.md、KARS_MEMORY.md 等)→ 逐個更新指向新 slug。
7. **驗證:** `python -c "yaml.safe_load(themes.yaml)"` 成功;`python thesis/lint.py`(meta_factor 值合法 +
   hub 警告);`python thesis/concentration.py`(確認 energy-macro 3 member + ai-capex 新 %);
   `python thesis/sizing.py`(兩個新 theme 出現、無 KeyError)。
8. **track_record:** log 拆分做一條 agent prediction/事件(何時拆、點解、兩腿各自 confidence),方便日後
   forward-IC 分腿評估。

---

## 7. 一句總結
**oil-gas-energy(THIN 2-report WATCH、油+氣混合)拆成 `oil-majors`(XOM/CVX/COP,弱腿、near-term 偏空、
建議 conf ~0.18-0.20、meta [energy-macro])+ `natgas-ai-power`(EQT/LNG/KMI/SEI,強腿、AI-BTM 結構成長、
建議 conf ~0.25-0.28、meta [energy-macro, ai-capex]);兩腿各自 kill_condition 草稿 + wiki 拆頁 + universe
XLE/XOP 歸油腿;副作用:energy-macro 升 3 member(更該寫 hub)、ai-capex weight 輕微紓緩。**

> ⚠️ **再強調:本文件係方案。未經用戶拍板,唔好郁 themes.yaml / wiki / universe.yaml。**
