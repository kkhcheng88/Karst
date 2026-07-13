# Per-node magnifier 評估 — Batch 1(photonics-optical + advanced-packaging)【草稿,待大腦逐 node 覆核】

**Date:** 2026-07-13
**任務:** Fable 交接書 P2-12 指定推廣次序頭兩個 theme,各起 `nodes:` 塊(per-node magnifier tier),
照 ai-power-grid 現有 nodes schema。
**方法:** magnifier 五特徵框架(`docs/2026-07-09_magnifier_model_plan.md` §1 + `docs/2026-07-12_
magnifier_scorecard_rubric.md` §1),校準錨 = MU 2023 / MU 2016-18 / FSLR-vs-STP。**唔係估值篩**——
tier 反映「呢個 node 被供需超級週期非線性放大嘅潛在倍數檔 + 性質(durable / binary)」。
**打分維持人手/agent 質性判斷**(rubric §11 拍板,唔起自動 scoring script)。confidence 逐 node 故意 OMIT。

## Tier 語意(照 ai-power-grid 五個現有 node 校準)
- `2x` = 成熟/已 priced/大型稀釋,倍數有限(對應 ai-power-grid ipp-utilities)
- `2-3x` = late/priced-ahead 但有真護城河(對應 grid-hardware / power-semis-mature)
- `3-5x-durable` = mid-cycle 但耐久(供給結構性慢,對應 uranium-fuel)
- `5-10x-binary` = 高 magnitude 但 binary(pre-profit / event / turnaround;對應 pre-earnings-optionality,
  WOLF 已 ex-post 破產驗證「binary」標籤真)

## 跨兩 theme 的結構發現(重要,寫入 themes.yaml node comment)
§3b:「10x 通常住上游樽頸 / 供給最慢端」。但呢兩個 theme **冇一個乾淨可交易的 `3-5x-durable`
上游 node**——因為兩者嘅耐久上游咽喉本體都唔係乾淨美股:
- photonics:耐久上游 = InP 基板,但唯一美股純玩家 AXTI **生產喺中國**(北京 Tongmei),帶 China 出口
  管制 + CPO 時程雙 binary → 變 event-shaped,唔係 durable。
- advanced-packaging:耐久上游 = T-glass(日東紡~90%)/ HVLP 銅箔(三井)/ Hoya 雙壟斷,**全非美股**,
  買唔到護城河本體;可交易美股全部係中游 proxy,已 90-100 分位 priced → `2-3x`。
- 所以兩 theme 嘅 magnitude 分佈都偏 `2-3x`(priced 中游)+ 少數 `5-10x-binary`(pre-profit/event 端),
  **呢個係主題本質(真咽喉但可交易表達已 priced / 二手),唔係打分偷懶。**

---

# THEME 1 — photonics-optical(6 nodes;theme-level: late / confidence 0.30 / real-bottleneck-but-crowded)

價值鏈分層依 `thesis/wiki/photonics-optical.md` 6 層 mermaid(① 基板 →② 雷射 IDM →③ 調變器 →④ 模組 →
⑤ DSP/架構 →⑥ 系統/光纖 + ④.5 耦合)。theme 9 隻 ticker 全部覆蓋,無遺漏。

## Node 1 — inp-substrate-chokehold:[AXTI] · event-driven · **5-10x-binary**
- **F1 營運槓桿 = 高**:小市值基數 + fab 固定成本;wiki #141「當季轉虧 −14.7%、預估 PE 72.8×」= 盈利
  擺動巨大(轉虧本身證槓桿)。
- **F2 定價權捱擺動 = 中(打折)**:持有真稀缺 InP 基板(path a),COHR 預付 $22.28M 鎖 3 年 6 吋、
  「連自擴 6 吋嘅 Coherent 都要向 AXT 排隊」(wiki #139)= 定價權真;**但** themes.yaml note 逐字
  「AXTI 係全審查最高危一隻…10-K 逐字『全部 substrate 產品喺中國生產』…已俾中國出口許可證直接掐停
  收入兩次(2023 鎵鍺、2025 磷化銦)」→ 供給紀律訊號被 China 機制打折(magnifier_model_plan §4 尾條
  China caveat)。
- **F3 距底部 = 遠(但屬 trough 非乾淨便宜)**:wiki「ttm_pe 16 係盈利觸頂尾隨假象…P/S 61×→38.6×、
  −41% vs 50 日均」——現正處 CPO-延後驅動嘅 trough,距正常化遠。
- **F4 樽頸位置 = 高**:wiki「唯一美股純玩家、32 月交期咽喉」;6 吋良率僅 15-20% = 供給最慢端。
- **F5 情緒/擁擠 = 開始消風(利好)**:wiki #143「CPO 延後單日殺 AXTI −13% = 擁擠端首度回修」。
- **判 5-10x-binary**:framework「10x 住上游樽頸」+ 案例庫一手 AXTI **51.84x realized(2023-10→2026-05)**
  = magnitude 確實極高;但 China 出口 binary + CPO 時程 binary 令性質 event-shaped(唔係 durable)。
  cycle=event-driven(催化 = CPO 採用時程 + China 出口政策)。**張力誠實記低**:結構咽喉耐久,但唯一
  美股 proxy 帶 China-domicile 製造 binary → 用 binary 檔而非 durable 檔。

## Node 2 — laser-idm-moat:[COHR, LITE] · late · **2-3x**
- **F1 營運槓桿 = 高**:無代工 IDM fab 固定成本;wiki「COHR capex 0.11→0.29B(2.6x)」。
- **F2 定價權 = 高(最乾淨 path a)**:wiki「無代工、產能不可共享的 EML/CW 雷射 IDM」+ NVDA $6B 三張
  支票鎖產能;#143「CPO 延後對龍頭唔痛…Lumentum $808M +90% YoY」= 定價權捱得過架構轉移。
- **F3 距底部 = 近(不利)**:wiki「COHR ttm_pe 188(98%!)、LITE 159(75%)」——已 run(案例庫 COHR
  13.33x / LITE 23.01x realized),接近頂,唔係 trough。
- **F4 樽頸位置 = 高**:最深護城河、雷射軍火商。
- **F5 情緒/擁擠 = 高(不利)**:全批最擠(58% bull)+ 75-98 分位。
- **判 2-3x**:深護城河但已 run + 估值極端 + 高擁擠 → 剩餘 upside 有限,對應 ai-power-grid
  power-semis-mature（深護城河但估值極端 = 2-3x）。late。

## Node 3 — silicon-photonics-dsp:[MRVL] · late · **2-3x**(⚠ 薄 magnifier 證據)
- **F1 營運槓桿 = 中**:fabless,固定成本槓桿低過 IDM;靠 design win。
- **F2 定價權 = 中**:架構定義者(1.6T DSP + 自研 ASIC + 光子 fabric),但 wiki #107/#149「CPO/LPO
  取代 DSP…網路扁平化壓收發器層」= 佢個 DSP 層正被替代(headwind,唔係樽頸)。
- **F3 距底部 = 近(不利)**:wiki「ttm_pe 102(86%)」,已 run。
- **F4 樽頸位置 = 中**:跨鏈(部分兩邊贏),但 DSP 層被 CPO/LPO 替代 → 非純樽頸持有者。
- **F5 情緒/擁擠 = 高**:86 分位、most-consensus AI 名。
- **判 2-3x + 薄證據旗**:性質偏 secular-growth(fabless 大型設計商)多過供給樽頸 magnifier;
  magnifier-specific 證據僅 ttm_pe + 質性層角色,**建議大腦當 WATCH 級,若判佢係 secular-growth
  可考慮唔當 magnifier node**。late。

## Node 4 — modules-transceivers:[AAOI, FN] · late · **2-3x**
- **F1 營運槓桿 = 中高**:wiki「AAOI capex 0.03→0.06B(2.1x)、喊 9x 擴產」;FN 係代工(薄利鏟子)。
- **F2 定價權 = 低中**:模組比雷射 IDM 商品化;wiki #149「B. Riley 以網路扁平化為由把 AAOI 降評至
  中性、目標 $129」= 呢層具名承壓;FN = 純組裝軍火商無定價權。
- **F3 距底部 = 中**:wiki「AAOI ttm_pe 25(48%)」,唔極端。
- **F4 樽頸位置 = 中(承壓)**:wiki #149「網路扁平化砍收發器層需求…價值往上游遷移」= 呢層被結構性
  壓縮(headwind,唔係樽頸);FN 係組裝軍火商但低毛利。
- **F5 情緒/擁擠 = 中**:AAOI 波動大、投機-中。
- **判 2-3x**:層被結構性壓縮(網路扁平化)封住 magnitude 上限;AAOI 9x 擴產賭注 + FN 軍火商性質俾
  少少 optionality。late。出處:wiki 2026-07-08 #149 段。

## Node 5 — cpo-speculative-preprofit:[SIVE, LWLG] · early · **5-10x-binary**
- **F1 營運槓桿 = N/A**:wiki「SIVE/LWLG 無盈利」,pre-revenue,理論上巨大但未兌現。
- **F2 定價權 = 未證**:LWLG「IP 授權」optionality;SIVE「營收年減、P/S ~190×」無護城河證明。
- **F3 距底部 = 冇法用盈利量**:P/S ~190× = 極端,非「trough 便宜」,係押未來。
- **F4 樽頸位置 = 低/未證**:wiki「SIVE 100% CPO 純玩家…CPO 延後最曝險端」;LWLG「純選擇權」。
- **F5 情緒/擁擠 = froth 端**:wiki「報告本身喊 6-8x/9x = froth…純押注 SIVE/LWLG 最曝險」。
- **判 5-10x-binary**:wiki 逐字「純選擇權」(LWLG)/「純投機」(SIVE)= binary/option 性質明確;
  magnitude 潛在高但 pre-revenue 無證護城河 = magnifier_model_plan §3f/§4 警告嘅彩票/option profile。
  tier `5-10x-binary` 正確 flag 做 option/event 框架、極細注。early(pre-profit,押 CPO 未來)。
  **magnitude 數字本質不可量(option),證據薄但「option 性質」證據強。**

## Node 6 — glass-fiber-coupling:[GLW] · mid-late · **2x**
- **F1 營運槓桿 = 低中**:大型多元化,光通訊只係一分部,槓桿被規模稀釋。
- **F2 定價權 = 中高但慢**:wiki「玻璃橋 <2dB/24ch、離子交換波導、被動對位」+ 三雲鎖單(Meta $6B/
  NVDA 認股權證/Amazon);但「玻璃橋尚未變現、發表≠量產」= 慢變數。
- **F3 距底部 = 近(不利)**:wiki #138「46× FY27 PE / 36× FY28、Truist 維持 Hold = 非便宜防守」。
- **F4 樽頸位置 = 中**:④.5 耦合係真.新樽頸節點(vs Teramount/Molex),GLW 領跑;但被大型多元化基數稀釋。
- **F5 情緒/擁擠 = 中**:估值已反映。
- **判 2x**:大型多元化 + 光學只佔一小塊 + 估值已反映 + 慢 2027 變數 → magnitude 被大型稀釋封頂,
  對應 ipp-utilities（mid/mature、2x）。呢個係 theme 嘅耐久-但-被稀釋防守腿。mid-late。

**Photonics 最薄證據 node = silicon-photonics-dsp (MRVL)**(magnifier 框架適配性最弱,偏 secular-growth,
建議 WATCH);次薄 = cpo-speculative(magnitude 不可量,但 option 性質證據強)。

---

# THEME 2 — advanced-packaging(6 nodes;theme-level: late / confidence 0.32 / real-chokepoint-but-proxies-priced)

價值鏈分層依 `thesis/wiki/advanced-packaging.md` mermaid(OSAT 軍火商 / PCB 收費站 / EMIB 選擇權 /
製程設備 / 玻璃基板 / Hoya HDD 下游)。theme 13 隻 ticker 全部覆蓋,無遺漏。

## Node 1 — osat-arms-dealers:[AMKR, ASX] · late · **2-3x**
- **F1 營運槓桿 = 高**:OSAT 資本密集 fab 工序,高固定成本。
- **F2 定價權 = 高(乾淨 path a)**:wiki「封裝格式戰(CoWoS-L vs EMIB-T)無論誰贏封測都要有人做 →
  AMKR/ASX 兩邊通吃、誰贏都收錢(#131)…本叢最乾淨嘅可交易護城河邏輯」。
- **F3 距底部 = 近(不利)**:wiki「AMKR ttm_pe 49(91%)、ASX 67(90%)」,已 run,非 trough;
  供給回應形成中(AMKR ~1.5x、ASX +34%)。
- **F4 樽頸位置 = 高**:封裝軍火商,叢中最乾淨護城河。
- **F5 情緒/擁擠 = 混合**:敘事低(11% bull)但估值 90-91 分位(已 priced)。
- **判 2-3x**:深軍火商護城河但已 90-91 分位 + 供給回應形成中 → priced-ahead,對應 grid-hardware/
  power-semis(深護城河但估值極端 = 2-3x)。核心可交易表達。late。

## Node 2 — pcb-substrate-tollbooth:[TTMI] · late · **2-3x**
- **F1 營運槓桿 = 中**:PCB 有槓桿但 TTMI capex 小基數(1.9x)。
- **F2 定價權 = 中**:PCB/基板收費站,中國配額轉移反向受益(wiki #112/#117);但 PCB 比 OSAT 商品化。
- **F3 距底部 = 近(全叢最極端)**:wiki「TTMI ttm_pe 102(96%!最貴)」= 全 thesis 最貴,完全非 trough。
- **F4 樽頸位置 = 中**:收費站但唔似 OSAT 咁乾淨軍火商;基板被競爭。
- **F5 情緒/擁擠 = 全叢最 priced**:96 分位。
- **判 2-3x(但明記係全叢最 priced)**:收費站位置給 2-3x,但 wiki 明確 TTMI 係最貴、least preferred
  (vs AMKR/ASX)。late。

## Node 3 — process-equipment-test:[MKSI, KLAC, KLIC, TER, FORM, LRCX] · late · **2-3x**
- **F1 營運槓桿 = 中**:設備商,order-driven 中度槓桿。
- **F2 定價權 = 中**:KLAC「零容錯光學檢測」近壟斷、KLIC「TCB 熱壓鍵合直接受惠、目標 $4 億」(#150)較強;
  TER/FORM/LRCX 喺競爭性 test/etch 市場較弱。
- **F3 距底部 = 近(已 re-rate)**:wiki「KLAC/MKSI 94 分位」;#150「設備股 2026 上半已先反映一段…出稿
  當日盤中同步回檔約 6-10%,前瞻世代近期營收含量低」。
- **F4 樽頸位置 = 中**:製程鏟子,KLAC/KLIC 較強、其餘較競爭。
- **F5 情緒/擁擠 = 已 re-rate(priced)**:#150。
- **判 2-3x**:設備鏟子、已 re-rate、龍頭 94 分位 → 中度、priced。late。出處:wiki 2026-07-08 #150 段。
  **註**:China 曝險兩組唔同(KLIC 53.5% China 營收 = 供給側 a 組;KLAC/TER/FORM/LRCX/MKSI 正被美國
  出口管制削 China 營收 = b 組 de-risk 中),但 magnifier tier 同檔,合一 node,tier 唔受影響。

## Node 4 — emib-optionality:[INTC] · event-driven · **5-10x-binary**
- **F1 營運槓桿 = N/A**:wiki「ttm_pe 3519(無意義·近零盈利)…代工季虧 $2.4B」。
- **F2 定價權 = 未證**:EMIB-T 係可信第二供應,但外部代工營收僅 $174M(~1%),護城河未 at-scale 證明。
- **F3 距底部 = turnaround(非乾淨 trough)**:代工蝕錢,係 turnaround 非 cyclical trough;
  magnifier_model_plan §4「唔好把 turnaround(INTC 型)同 cyclical-supercycle 混」。
- **F4 樽頸位置 = 中-未證**:EMIB-T 可能係第二封裝源(格式戰誰贏);#152「Google 2028 下單 INTC 封裝
  AI 晶片 >300 萬顆」= 真 datapoint。optionality。
- **F5 情緒/擁擠 = 事件/政治**:wiki「6/18 +10.64% 買嘅係政治選擇權溢價」。
- **判 5-10x-binary**:wiki 逐字「用事件/選擇權框架、非 PE」;turnaround + event,high binary magnitude
  if EMIB-T + 代工轉身成功但未證。對應 pre-earnings-optionality(event/option、binary)。event-driven。

## Node 5 — glass-substrate-nextgen:[GLW] · mid-late · **2x**
- **F1 營運槓桿 = 低中**:大型多元化,玻璃分部。
- **F2 定價權 = 中**:玻璃領跑但 wiki #138「韓廠 KCC/LX Glass/SKC 亦入局(競爭、非獨家)」。
- **F3 距底部 = 近**:已 priced(46x FY27,見 photonics wiki),非 trough。
- **F4 樽頸位置 = 中**:2027 玻璃基板接棒領跑但競爭者入局 + 慢變數(2027);wiki #138「瘋傳巨型玻璃
  基板 TAM 其實係 CPO TAM 誤植…真實約 $31B by 2030(Yole),遠細過病毒推文 → 唔好用誤植 TAM 撐估值」。
- **F5 情緒/擁擠 = 中**。
- **判 2x**:大型 + 慢 2027 變數 + 競爭者入局 + TAM 細過吹噓 → 中度、durable-but-slow 防守,同 photonics
  GLW node 一致(2x)。mid-late。**(GLW 兩 theme 都有:photonics = 光纖/耦合腿,advanced-packaging =
  玻璃基板腿;兩 node 各自 2x,一致。)**

## Node 6 — hdd-storage-hoya-downstream:[STX, WDC] · mid-late · **2-3x**(⚠ Tier-2 未一手驗)
- **F1 營運槓桿 = 高**:HDD 高固定成本,完售 + 漲價~50% 環境大幅落盈利底。
- **F2 定價權 = 高(當下)**:wiki「硬碟完售 + 漲價~50%(#083/#085)」+ Hoya HDD 玻璃碟 100% 上游壟斷
  封住供給 = 真.供給受限定價力時刻(oligopoly STX/WDC/Toshiba)。
- **F3 距底部 = 顯著**:HDD 曾係「結構性衰退」被當死,現靠 AI-儲存需求 + 完售 inflect;案例庫 WDC
  26.78x realized(2022-12→2026-06)。
- **F4 樽頸位置 = 中高**:oligopoly HDD 商受惠 Hoya 100% 玻璃碟壟斷封供給;nearline HDD 完售。
- **F5 情緒/擁擠 = 較低**:HDD 曾 under-loved(結構衰退敘事),現 inflect,擁擠低過封裝 proxy。
- **判 2-3x + 薄證據旗**:結構 setup 係叢中最 magnifier-genuine(Hoya 鎖 + oligopoly + 完售,近 memory
  型供需超級週期,WDC 本身亦在 memory-supercycle theme)。**但三重折扣壓返 2-3x**:(1)wiki 待補項
  「STX/WDC 完售 + 漲價~50% 一手查證」= 證據仍 Tier-2 未一手驗;(2)儲存/記憶體週期 late(memory
  theme confidence 0.38、capex 頂訊號);(3)大型股稀釋。**升級路徑明寫**:若完售 / 50%-漲價 / Hoya-鎖
  耐久一手驗證成立,可升 `3-5x-durable`。mid-late。

**Advanced-packaging 最薄證據 node = hdd-storage-hoya-downstream**(Tier-2 未一手驗,建議 WATCH +
標升級路徑);次薄 = glass-substrate-nextgen(2027 慢變數 + 競爭者入局 + TAM 誤植,時程投機)。

---

## 校準對照(確保唔係亂標)
- 對 MU 2023 錨(rubric §3):MU 當時 F1 高/F3 遠底/F4 高 → 真 magnifier;本 batch 冇一個 tradeable
  node 同時 F1 高 + F3 遠底 + F4 高(最接近係 hdd-storage,但 F3 受 late 週期打折)→ 冇亂標高檔。
- 對 FSLR-vs-STP(rubric §6):F4(樽頸位置)+ P1(護城河獨立於商品)最有分辨力。本 batch 用 F4 拉開:
  osat/laser/inp = F4 高;modules/dsp/pcb = F4 中;cpo-speculative = F4 低/未證。
- 對 ai-power-grid 五 node:tier 檔分佈一致(mostly 2-3x + 一個 5-10x-binary + 2x 防守腿),兩 theme
  都無乾淨 3-5x-durable(理由見上「跨 theme 結構發現」)。
