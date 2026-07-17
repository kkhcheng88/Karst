# 外部來源登記冊 — 邊個入管道、邊個做讀物、憑咩(2026-07-17)

> **一個正本**:呢份係「我哋用邊啲外部來源、佢哋憑咩資格」嘅唯一記錄。
> 新來源評估先睇 §1 三條篩,再入 §2 表。舊評估如果冇落檔 = 冇做過(2026-07-14 嗰次
> substack 評估就係咁蒸發咗,今日重做)。

## §1 三條篩 —— **按來源類型用,唔係一刀切**(2026-07-17 定;§1a 修正同日)

| # | 問題 | 唔過嘅後果 |
|---|---|---|
| 1 | 有冇**有日期、可證偽**嘅判斷(ticker + 方向 + 時限)? | **評唔到分 → 入唔到 radar** |
| 2 | 佢寫嘅嘢**未反映喺價格**未?(SKILL 紀律 4) | 寫緊人盡皆知嘅嘢 → 係背景唔係 edge |
| 3 | 有冇**硬數據**(filing / 合約 / 實地 / 一手 **+ 出處**)? | 淨係框架觀點 → Tier-2,升唔到 confidence |

### §1a 修正(用戶 2026-07-17 指出,原框架有邏輯漏洞)

**原本嘅寫法暗示篩 1 係所有來源嘅硬閘——錯。gooptions 自己都冇 dated call,佢一樣係 ingest 管道。**
用戶原話:「it doesn't have entry or exit point. But similar to GOOPTIONS whether it worth as it
mentioned as observation to the market as Thesis part?」——正確,篩要按**來源類型**用:

| 來源類型 | 佢嘅職能 | 關鍵篩 | 例 |
|---|---|---|---|
| **判斷源** | 喊買賣,可以記分 | **篩 1**(冇 = 永遠評唔到分) | 順哥 Discord |
| **論述源** | 揪出新名 / 供 thesis 素材 | **篩 2 + 3**(**篩 1 唔適用**) | gooptions |

**論述源嘅真正判準(= gooptions 實際交付嘅兩樣嘢):**
1. **揪唔揪到我哋冇睇過嘅名?**(二階/供應鏈/瓶頸,唔係 mega-cap)
2. **啲數字有冇出處?**(filing / 電話會原話 —— 冇出處嘅數字**比冇數字更差**,佢望落似證據但驗唔到)

**點解第 1 條係硬閘**:2026-07-17 順哥評分卡示範咗「讀落好有道理」有幾唔可靠——佢啲分析寫得
好好、自稱個股 75% 勝率,實測命中 56.2%、對 SPY 打和。**冇得評分嘅來源,永遠只能靠「睇落幾
啱」入場,而呢個標準已經證實會出錯。**

## §2 來源現狀

| 來源 | 類型 | 過篩? | 現狀 | 正本 |
|---|---|---|---|---|
| **gooptions** | thesis 文章 | 1✗ 2✓ 3◐ | **ingest 管道**(theme 發現) | `thesis/.raw/gooptions/` |
| **zsxq「社会观察从业者」** | dated calls + 投行 PDF 策展 | 1✓ 2◐ 3✓(PDF) | **PDF 已 ingest**(6 份,全 NEUTRAL);calls 記帳中(3 條待判) | `thesis/.raw/zsxq/INDEX.md`、`PDF_TRIAGE.md` |
| **Discord 順哥(皇者顺)** | dated calls | 1✓ 2✗ 3✗ | **已評分 → 唔接**(round trip 對 SPY 打和;自稱 75% 否證) | `2026-07-17_kol_shunge_roundtrip.md` |
| **substack 美股送分題**<br>(openbookandeasypoint) | 論述/教育 | 2✗ 3✗ | **讀物,唔入管道**(見 §3) | 本檔 §3 |
| **substack FOMO 研究院**<br>(fomosoc.com,KP@FOMOSoc,5萬訂閱) | 論述(供應鏈深度) | 2**◐-✓** 3**◐** | **候選——待實測**(見 §3b) | 本檔 §3b |
| substack acidinvestments | 論述 | 1✗ 2◐ 3◐ | 一次性引用過(memory 長約 red-team) | `2026-07-15_redteam_memory_supercycle.md` |

## §3 substack 美股送分題(openbookandeasypoint)— 2026-07-17 評估

**基本**:1.3 萬訂閱;作者自稱在職美股分析師;約每週 2 篇;**2026-07-05 起收費**(持續讀需訂閱)。
**內容**(2026-05-25 → 07-13 共 15 篇):「CSP 真正的拐點不是 AI,而是 Token 定價權…市場即將
re-rate」、「AMD:CPU 是 AI 下一個戰場,但市場是不是已經把終局價格提前買完了?」、「為什麼
Anthropic 值 1 兆美元?」、加一批方法論教育文(持有贏家 vs 賣出贏家、注碼心理、集中度風險)。

**判決:唔入 ingest 管道。** ⚠️ 判準已按 §1a 修正 —— **唔係因為佢冇 entry/exit**(gooptions 都冇,
呢個唔係論述源嘅判準);係因為佢**做唔到 gooptions 嘅兩樣核心功能**。實讀主打文
(《宋分分析師備忘錄 #7》CSP 拐點係 Token 定價權)逐項對照:

**讀咗兩篇全文**(#7 CSP Token 定價權;#10 油價/AI/Robotaxi —— 後者係全刊唯一聲稱有一手接觸嘅,
即佢嘅 best case)+ 25 篇 API 預覽(`/api/v1/profile/posts?profile_user_id=291548189`;
**23/25 免費**,只有 2 篇收費)。

| gooptions 交付嘅嘢 | 呢個 substack |
|---|---|
| **揪出我哋冇睇過嘅名** | **有,但稀** —— #10 有 Ford / GM / Traton(傳統車廠轉軟件/robotaxi,Traton 夠冷門);#7 零個(全篇 MSFT/GOOG/AAPL/META)。25 篇預覽出現嘅 ticker 全部 mega-cap(MSFT/TSLA/GOOG/NVDA/AMD) |
| **有出處嘅硬數據** | **零**。#7:7 個數字零出處(「MS 做了一個很關鍵嘅模型」冇連結)。#10:5 個數字零出處(「**資深的機構專家**」冇名、「**商品專家跟石油交易員**都說」冇名、「**高盛用他們的模型**算出來」冇報告冇日期、Ford $1B / GM $3B+ 冇出處) |
| **可餵 kill metric 嘅門檻** | **零**。#7:「2026 年底進入正式上線」冇數量門檻。#10:「接下來 4-6 週」供應轉緊,冇價位 |

### 定性:**問題產生器,唔係證據來源**
- **俾到**:值得問嘅角度(「Token 定價權係咪 CSP 拐點?」「傳統車廠軟件轉型算唔算一條線?」)
- **俾唔到**:任何可引用嘅嘢。**連揾到名嗰陣,背後啲數都係「專家話」/「高盛個模型」→ 要用就 100% 重做一手研究。**
- **點解決定性**:問題本身係最平嘅嘢(已有 discovery radar / constraint-language / gooptions)。
  缺嘅係**可追溯嘅答案**,而佢一個都冇。**冇出處嘅數字比冇數字更差** —— 望落似證據,
  留低印象但唔留低責任。Karst tier 制度存在就係擋呢樣。
- **判決**:免費讀物(23/25 免費,RSS 即可),**永遠唔入 ingest**。一年或者俾到一兩個角度,
  追嗰下要自己由零做起。

⚠️ **記錄一個過度推論**:2026-07-17 我先由 #7 一篇推「零個二階名」,再讀 #10 就見到 Ford/GM/Traton
—— **樣本太窄就落通則,同日第三次同類錯誤**(mirror / 順哥結構 / 本項)。結論唔變,措辭已修。

**但有一個具體、有界嘅用途,值得做一次(唔建管道):**
佢主打「**Token 定價權先係 CSP 拐點**」呢個角度,啱啱好戳中我哋一個真缺口——
2026-07-17 ingest 嘅 MS MSFT 報告顯示:**容量 5GW→20GW,但每 MW 營收 $27.5M→$17.2M 逐年跌**。
呢個「起貨快過收錢」缺口,mag7-hyperscaler 而家用 RPO 現金比 + AI run-rate 監察,
**但「定價權」先係決定嗰條線會唔會拉返上嘅機制,而我哋冇任何指標量緊佢。**
→ **行動:一次性讀佢嘅 token 定價權文章,唯一目的 = 提煉一條可量度嘅 kill metric 補俾 mag7。**
提到就用,提唔到就算,唔建立追蹤管道。(需用戶訂閱。)

**教育文嘅價值**:方法論參考(唔係數據來源)。同 Karst 已驗證嘅嘢對得上先信——
例:「持有贏家 vs 賣出贏家」呢個題目,我哋自己嘅數據已經有答案(順哥切走右尾:
avg_win +18.4% / avg_loss -15.3%,資本效率排第 1 百分位)。

## §3b substack FOMO 研究院(fomosoc.com)— 2026-07-17 初評:**候選,待實測**

**基本**:KP@FOMSoc,**5 萬訂閱**,兩條線——「**KP 思考筆記**」(週更,**免費**,mega-cap 新聞綜合)
+「**深入分析**」(週更,**收費**,供應鏈深度)。評估依據:1 篇免費全文(#50)+ 20 篇 API 預覽
(`/api/v1/archive?sort=new&limit=30`)。**收費層零覆蓋——最有價值嗰半我讀唔到,呢個係本評估最大限制。**

### 同 openbookandeasypoint 嘅決定性分別:出處密度

| | 美股送分題 | **FOMO 研究院(免費層)** |
|---|---|---|
| 數字有名有姓出處 | **0%**(「資深機構專家」「高盛個模型」) | **~45%** —— **Micron capex guidance / Meta 官方公告 / SEMI 預測 / Jefferies 6-22 報告 / SemiAnalysis / Reuters** |
| 可證偽預測 | 一句,冇門檻 | Kyber 延至 2028、SEMI 設備 $520B(2026)/$570B(2027)、Meta 14GW(2027) —— **有日期有數,驗得到** |

45% vs 0% 唔係程度差,係**種類**差。附加價值:**佢點名具體報告(SemiAnalysis / Jefferies)= 一張通往真報告嘅地圖。**
弱點:**冇 hyperlink**;關鍵技術規格(Kyber 78 層 midplane)同 SKHY ADR 溢價敘事仍然 unattributed(~55%)。

### 收費層先係 gooptions-like 嗰半(題目 × 現有 theme 直接對撞)

| 期 | 題目 | 二階名 | 對應 theme |
|---|---|---|---|
| #55 | 3D 封裝 / 混合鍵合 | **BESI、ASMPT** | advanced-packaging |
| #54 | 玻璃基板(CoPoS、TGV) | 材料/載板鏈 | advanced-packaging |
| #53 | NAND Flash 控制器 | **慧榮 SIMO、群聯** | memory-supercycle |
| #52 | 功率半導體(SiC/GaN/800V) | 供應鏈贏家 | ai-power-grid |
| #50 | HVDC 與台達電 | **台達電**、重電/散熱 | ai-power-grid(**同 2026-07-17 ingest 嘅「Inside the 800VDC Revolution」PDF 同一條軸 = 獨立覆蓋**) |
| #48 | 資料中心互連 DCI | Nokia、Cisco | photonics-optical |

**呢啲正正係 gooptions 交付嗰種標的**(二階、供應鏈、瓶頸層,冇一個 mega-cap)。

### 實測方案(唔好靠感覺,亦唔好靠標題)
**如果用戶訂閱:攞 #55(混合鍵合 BESI/ASMPT,直接對 advanced-packaging)行一次完整 INGEST 流程。**
- 出到 STRENGTHEN,或者餵到 kill_metric / magnitude 推導 → **gooptions 級,入管道**
- 同 2026-07-17 六份投行 PDF 一樣全 NEUTRAL → 好睇嘅嘢,唔係來源

⚠️ **本評估限制**:1 篇免費全文 + 20 預覽;收費層(即高價值層)未讀。「45% 有出處」係**免費層**嘅數,
收費層可能更高(深度分析通常出處更密)亦可能更低。**唔由一篇推及全刊**(同日已犯三次同類錯,見 §3 尾)。

## §4 未評估 / 待辦

- `C:\TradingView\Discord\ElliottWave_90d.json` —— 另一個 Discord 頻道,未評估。過篩 1 就可以用
  同一條生產線跑(`exp_kol_shunge_roundtrip.py` 直接改 input 路徑)。
- zsxq 3 條 dated calls(2026-07-16 發出)—— 21/63d 成熟後填結果。
