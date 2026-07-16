# Level-2 Red-Team：us-solar-manufacturing（FSLR / 美國太陽能製造貿易政策護城河）

- 日期：2026-07-16
- 協議：thesis/DESIGN.md §4b（FALSIFY 升級：INGEST 係審判，唔係歸檔）+ §4c（三通道分流）
- 角色：辯方 red-team。**職責 = 事實補全（搵敘事冇展示嘅重大事實），唔係反對表演。**
  每條反方必須錨喺可引用事實/數據；砌唔到錨定事實 = 標「敘事風險」，唔算 finding。
- Pilot 教訓已納入（memory / photonics 兩單）：反面狩獵只收一手（數據/日期/公告/法律先例）；
  強制回答「Tier-1 佐證掂嘅係承重 claim 定周邊事實？」；強制做 balance-sheet 檢查。
- 約束：只新增本檔，冇改 themes.yaml / wiki / 任何現有檔。

---

## 1. 控方主張摘要

FSLR CdTe 薄膜唔使多晶矽（**結構性成本護城河**）+ 232/301/AD-CVD 關稅牆 + IRA 45X 本土成分
政策護城河 + **連續 7 年一路向後年份延伸嘅 sold-out/fully-allocated 語言**（backlog 到 2030、
2026 fully allocated）。現行 `confidence 0.32`（**違反 single-source cap 0.30**，sources 只登記
`transcript-discovery-radar` tier-3 一條）、`cycle mid`、`verdict real-policy-moat-and-still-cheap`、
`magnitude_tier 3-5x-durable`（案例庫贏家 26.44x realized、Pattern-1「護城河獨立於商品價」PASS）。

承重 claim 拆四條腿逐個審：
- **(i) CdTe「結構性成本護城河」**（唔使多晶矽 → 成本上獨立於 c-Si 商品鏈）
- **(ii) 關稅護城河**（232/301/AD-CVD 擋住中國/東南亞 c-Si）
- **(iii) IRA 45X 本土成分護城河**（補貼 + domestic-content adder）
- **(iv) 7 年連續 sold-out / backlog 到 2030**（訂單能見度 = 地板）

**本次同前兩單 pilot 嘅結構分野（先講最重要）：** photonics 一手逐字稿覆蓋 = 零、MU 嘅 RPO
唔喺 balance sheet；**FSLR 兩樣都反過來**——corpus 有齊 **30 篇一手逐字稿（2019Q1→2026Q1）**、
balance sheet 有 **~$1.79B 真.deferred revenue**。所以 pilot 嗰把「披露 backlog ≠ 入帳緩衝」嘅刀，
喺 FSLR **斬唔落**（見動作 1d）。呢單嘅致命傷唔喺「backlog 係咪真」，喺「護城河係咪成本、
盈利係咪自己賺嘅」。

---

## 2. 四個規定動作

### 動作 1 — 反面事實狩獵

**(a) 系統自己渠道（Tier-1，最鋒利）**

- **一手覆蓋 = 滿分（罕見）。** `corpus.py ticker FSLR` 返 30 篇，全部係一手 earnings-call
  逐字稿，2019Q1 連續到 2026Q1。「7 年連續 sold-out」呢個承重語言**可以逐年一手核實**，
  唔似 photonics「32 個月交期」係 Tier-2 自陳零掛源。2023-10-31 一手實錄：total backlog
  **81.8 GW**、YTD net bookings 27.8 GW（`corpus get transcript-FSLR-2023-10-31`）。
- **但「backlog 到 2030」係「峰值後下坡」而唔係「逐年延伸」——一手數打臉敘事。** 一手
  backlog 軌跡：**81.8 GW（2023-10）→ 50.1 GW / $15.0B（2025 年底）→ 47.9 GW / $14.4B（2026-03-31）**。
  wiki 講「連續 7 年一路向後年份延伸」，但一手數係 backlog 自 2023 見頂後**近乎腰斬**——
  交付快過新單補充 + debooking。「sold-out 語言逐年向後延」呢個動能敘事，一手上 2024 起已停。
- **8.3 GW debooking = kill_condition 第二條觸發器已部分點着（一手）。** FY2025 錄得
  **8.3 GW debooking，主因客戶合約違約，包括 BP 系affiliates**（Q4'25 電話會，2026-02-24）；
  全年 **淨 debooking −0.9 GW**（gross 7.4 − 終止）。wiki 嘅 kill_condition 明寫「『sold out』
  backlog 落空（大額訂單取消）→ confidence 歸零」——8.3 GW 客戶違約字面上就係「大額訂單取消」。
  **緩解（幫控方）：** Q1'26 debooking 急降至 0.1 GW、backlog 仍 47.9 GW ≈ 3 年能見度、
  且終止觸發 liquidated-damages（見 1d，違約客戶要留低訂金）。距離 = 近而未觸發。
- **Insider（EDGAR 180 日，剔機械交易後）**：net **−$9.9M**、**0 P-buyer、無 cluster**、
  score −0.17 neutral（`insider.py FSLR`）。弱陰性：冇任何 insider 獨立追認承重 claim
  （同 photonics COHR/LITE 同型）。

**(b) 承重 (iii) — 45X 補貼量級 = 本次最鋒利一刀（一手財數自證）**

- FSLR 係全美最大 45X 受益人。一手量級：2024 年賣咗 **$857.2M 稅額換 $818.6M 現金**
  （8-K，2025-02-20）；**FY2025 全年確認 ~$1.6B 45X 效益**（Q4'25 電話會 + FY2025 10-K）。
- **對照自己拉嘅一手財數（defeatbeta quarterly_income_statement）：FY2025 淨利
  = 209.5 + 341.9 + 455.9 + 520.9 = $1,528M。即 45X（~$1.6B）> 全年淨利（$1.53B）。**
  45X 走 COGS（生產抵免）：FY2025 毛利 $2,120M，剝走 $1.6B 45X ≈ $520M 毛利 / $5,219M 營收
  = **~10% GM，vs 帳面 41%**；剝 45X 後淨利大約 **breakeven 至微蝕**。
- **殺傷力：** wiki 用「FSLR 有盈利、7 年 sold-out → 呢個 downside kill 唔係彩票理由」嚟證成
  3-5x-durable。但一手財數顯示**盈利本身就係政策補貼**——「有盈利所以唔係彩票」係循環論證：
  盈利 = 政策。同時污染估值格：`ttm_pe 22 分位（~14.7x）平` 係建喺**補貼 E** 之上，
  剝補貼後「平」嘅前提消失。政策 binary 唔係「downside tail」，係**盈利本體**嘅存廢問題。

**(c) 承重 (i) — 「結構性成本護城河」被多晶矽崩盤蝕穿（一手價格）**

- FSLR 美國 utility bookings ASP **~$0.34–0.37/W**（含 adjuster；Q4'25 $0.364、Q1'26 ~$0.35，
  一手電話會）。中國 c-Si 現貨：全球 **$0.08–0.28/W**、中國 TOPCon 600W 低見 **~$0.087/W**；
  **多晶矽崩到 ~$6.2/kg，只為 TOPCon 模組加 ~$0.012/W**（NREL Spring-2025 Solar Industry
  Update, fy25osti/95135）。
- **殺傷力：** CdTe 「結構性成本護城河」嘅歷史 PASS（案例庫週期 8：2011-12 多晶矽泡沫爆，
  CdTe 捱過殺死 STP/YGE/Q-Cells/LDK）係「護城河獨立於商品價」。但**今日因果反轉**——
  平多晶矽令 c-Si 變成低成本方，FSLR 唔食平 poly 嘅便宜。ex-tariff 計，FSLR $0.35/W
  貴過中國 c-Si $0.09–0.13/W。**成本護城河已冇；撐住 FSLR 嘅係政策（關稅 + 45X），唔係成本。**
  案例庫 Pattern-1 而家反方向咬——「護城河獨立於商品價」呢次係對 FSLR 不利。
  （Gap：FSLR 不披露 all-in cost/W，只俾 component + margin；上述係 ASP vs 對手現貨嘅一手對照。）

**(d) 強制 balance-sheet 檢查 — 反轉方向：FSLR 係 GEV 型，backlog 有真金現金背書**

- **`quarterly_balance_sheet`（defeatbeta，9 季至 2026-03-31）：**
  - **Current Deferred Revenue $1,203.2M + Non-Current Deferred Revenue $582.4M = ~$1,785.6M
    真.客戶預付。** 軌跡：$2,005M（2023-12）→ $2,040M（2024-12）→ $2,218M（2025-09）
    → $1,786M（2026-03）。Current 一路升（$414M → $1,203M）= 合約近交付時由 non-current
    重分類，係**轉化中、唔係取消**嘅健康簽名。
  - **判定 = 承重 (iv) 補強。** 呢個同 MU（聲稱 RPO $100B 但 balance sheet 得 $1.02B deferred）、
    photonics（COHR ~$62M / LITE ~$7M deferred 可忽略）**決定性唔同**：FSLR 客戶真金白銀落訂
    （多年 PPA 訂金 + termination security）。「披露式 backlog ≠ 入帳緩衝」嗰把兩連勝嘅刀，
    喺 FSLR **斬唔落**——backlog 有 ~$1.8B 現金背書，違約客戶留低訂金（呼應 8.3 GW debooking
    但 deferred revenue 未崩，見 1a）。
  - **但要量級校準（唔為交貨誇大）：** $1.8B deferred 對 $14.4B contracted backlog ≈ **12%**——
    係實質訂金/security，唔係全額預付。佢證「backlog 真、違約有成本」，證唔到「鎖到 2030」。

**(e) 承重 (iv) 副線 — 碲（Te）供給 kill 軸比 wiki 描繪嘅弱（一手對沖，幫控方）**

- 中國控 **76.5% 精煉碲**、2025-02-04 對碲/CdTe 出口許可管制、碲價 ~$121→$243/kg（+67%，
  商業 tracker，非 USGS）。**但 FSLR 一手已對沖**：5N Plus 長約供碲、料源含 Rio Tinto
  Kennecott（Utah，非中國銅精煉副產碲）+ 自營回收（2005 起、Cd/Te 回收率 ~90%）。
  10-K 迄今**無披露任何實際碲供給中斷**。kill_condition 第 4 條（中國碲管制打斷核心原料）
  嘅供給側**大幅中性化**——剩返係碲價 cost-creep，唔係斷供。事實補全令呢條 kill 軸縮窄。

### 動作 2 — Steelman 反方（非 wiki/文章自供，事實錨齊）

**「FSLR 唔係『結構成本護城河 + 平』，係『政策租值冠軍 + 補貼 E 上嘅平』——一個
repealable 補貼就係盈利本體」：**
1. 一手：FY2025 45X ~$1.6B **> 全年淨利 $1.53B**；剝 45X 後 ~10% GM、淨利 ≈ breakeven（動作 1b）。
2. 一手：FSLR ASP $0.35/W vs 中國 c-Si $0.09–0.13/W（ex-tariff），成本護城河已冇（動作 1c）；
   撐價嘅係關稅 + 45X，**兩者皆屬 2025-2026 政治配置嘅函數**。
3. 一手：backlog 由 81.8 GW（2023）腰斬到 47.9 GW（2026Q1）、FY2025 8.3 GW 客戶違約（動作 1a）——
   「逐年向後延嘅 sold-out」動能已停。
4. 先例：太陽能史一貫係「政策一變、經濟即翻」（Section 201/ITC step-down 週期、
   歐洲 FiT 撤銷後 2012-13 產能崩）——政策租值唔係結構護城河。

呢條 steelman 唔需要「美國太陽能需求係假」——就算裝機需求全真，FSLR 嘅**超額利潤**
仍係政策製造，一個立法週期可以抹走。

### 動作 3 — 平庸解釋測試

**悶故事：「受保護市場入面嘅補貼本土冠軍」可以解釋幾多？**
- 解釋到：41% GM、22 分位平 PE、7 年 backlog 語言、96% 美國稼動——**全部可由「關稅牆內收政策租」
  解釋**，唔需要「結構性成本護城河」呢個更強假設（成本護城河一手已證冇，見 1c）。補貼冠軍
  自然錄高帳面 margin（因為 $1.6B 補貼入 COGS）+ 低 PE（市場知道 E 有補貼成分，折返）。
- 解釋唔到（結構故事嘅額外證據，真）：(1) **$1.8B deferred revenue 現金背書**——受保護但無需求
  嘅公司唔會有客戶落 $1.8B 訂金（動作 1d）；(2) **碲供給非中國對沖 + 自營回收**（動作 1e）=
  真.供應鏈韌性；(3) 關稅牆係**四機制分散**（201/232/301/AD-CVD），唔係單一 executive 開關，
  比純政策 binary 難一鋪清（見動作 4）。
- **可區分觀測（datable）**：
  1. **2028 大選後政策配置** = 45X/AD-CVD 存廢嘅天然實驗（呢個先係真.kill window）。
  2. **Section 232 多晶矽調查（2025-07-01 啟動、未裁）** 若落地 → c-Si feedstock 加稅，幫控方；
     若無疾而終 → 關稅牆封頂。
  3. **bookings vs debookings QoQ**：Q1'26 已回穩（0.1 GW）；若重返 2025 型大額違約 → (iv) 中彈。
- 結論：**(i) 成本護城河 = 悶故事完勝（結構解釋唔成立，一手證冇）；(iii) 補貼 = 悶故事解釋晒
  且更誠實；(ii)(iv) 有結構證據額外背書（deferred revenue + 關稅分散），悶故事解釋唔全。**

### 動作 4 — kill 距離（逐條）

| kill 軸 | 當下事實 | 距離判定 |
|---|---|---|
| **關稅撤銷 / 豁免**（201/232/301/AD-CVD） | 方向**反而收緊**：AD-CVD 終令 2025-06-24 生效（柬 125%、越 120–813%、泰 111–375%、馬 8.6–81%）；301 中國模組 50%（2024-09）、poly/wafer 50%（2025-01）；232 poly 調查 2025-07-01 啟動未裁。201 已 2026-02-06 到期但本身無牙（bifacial 早豁免）。 | **未觸發、方向逆（幫控方）**；且**四機制分散**降低「一鋪清」風險。真.window = 2028 大選後 |
| **IRA 45X 撤銷** | OBBBA（2025-07-04 簽署）**保留** 45X 到 ~2030（風電 2027 殺、太陽能/儲能相位不變）+ 加 FEOC 限制 | **未觸發、statutory 到 2030**；但**曝險 = 存亡級**（45X $1.6B > 淨利 $1.53B）——kill 一觸即由「有盈利」變「breakeven」。呢個係全 thesis 最深、最非線性嘅單點 |
| **「sold out」backlog 落空（大額取消）** | FY2025 **8.3 GW 客戶違約 debooking（含 BP 系）**、backlog 81.8→47.9 GW 腰斬；但 Q1'26 回穩 0.1 GW、deferred revenue $1.8B 未崩、違約留訂金 | **部分點着後回穩**；基準應校正：唔係「逐年延伸」，係「峰後下坡、~3 年能見度」。監察 bookings−debookings 淨值 QoQ |
| **中國碲/CdTe 管制斷供** | 管制 2025-02 生效、碲價 +67%；但 FSLR 5N Plus/Rio Tinto 非中國料源 + 自營回收 90%、**無披露中斷** | **供給側大幅中性化**（幫控方）；剩碲價 cost-creep。wiki 把此列平權 kill 軸 = **高估**，建議降權 |
| **成本護城河解除**（對手追上） | c-Si 因平 poly 已平過 FSLR（ex-tariff），**成本護城河其實已冇** | **軸 mis-specified**：FSLR 從來（今日）唔靠成本贏，靠政策贏——呢條應改寫成「政策一走、暴露已失嘅成本競爭力」，見 §4 |

---

## 3. 判決：**分岔（承重 (iv) backlog 補強、(ii) 生還、(i) 成本護城河中彈、(iii) 補貼腿存亡曝險）**

按 §4b 校準：判決標準 = 承重 claim 面對補全後嘅事實集企唔企得住。逐子命題：

- **(iv)「7 年 sold-out / backlog」——補強（現金背書），但動能敘事中彈。** balance-sheet 檢查
  反轉方向：$1.8B deferred revenue = 真現金，pilot 嗰把「披露 backlog」刀斬唔落，一手逐字稿覆蓋
  滿分。**但**「逐年向後延」係假象（81.8→47.9 GW 腰斬、8.3 GW 違約）——backlog 真、有現金、
  但係**峰後下坡嘅 ~3 年能見度**，唔係「延伸到 2030 嘅擴張」。
- **(ii) 關稅護城河——生還兼方向逆（幫控方）。** c-Si 牆 2025-26 反而更高（AD-CVD 新令、301 50%、
  232 待裁），全部針對 FSLR 唔用嘅 c-Si 鏈；四機制分散降 binary 風險。呢條係承重最硬嘅一截。
- **(i)「CdTe 結構性成本護城河」——中彈（一手價格證偽）。** 多晶矽崩盤令 c-Si 變低成本方，
  FSLR $0.35 vs 中國 $0.09–0.13。成本護城河已冇；撐住嘅係政策唔係成本。案例庫 Pattern-1
  今次反咬。**moat 格嘅「結構性成本」半截唔成立。**
- **(iii) 45X 補貼腿——生還（到 2030）但揭出存亡級曝險。** 45X $1.6B > 淨利 $1.53B：盈利本體
  = 政策。「有盈利所以非彩票」循環論證破；「22 分位平」係補貼 E 上嘅平。政策 binary 由
  「downside tail」升級為「盈利存廢」。
- 附：碲 kill 軸（1e）供給側被一手對沖中性化，wiki 高估咗呢條。insider 弱陰性、無追認。

**§4c 三通道分流（承重殺傷力唔准喺 confidence 數字酌情，機械入通道）：**

| red-team 結果 | 落點 |
|---|---|
| **(iv) backlog 現金背書** | Tier-1 擊中，但擊中嘅係**已-priced / 市場已知**嘅需求能見度（周邊），唔係承重 magnitude 腿 → **通道 2：唔脫 cap**（分岔定義，同 tpu toll-booth 已 priced 同型） |
| **(i) 成本護城河中彈** | **通道 1**：moat 格「結構成本」半截降格；入公式但被 single-source cap 吸收 |
| **(iii) 補貼腿存亡曝險 + magnitude 動能停** | **通道 3**：3-5x-durable 嘅 durability 腿未證（靠 repealable 政策 + 已失成本競爭力）→ 標 `magnitude_unconfirmed`，sizing v2 收起 magnitude 加成 |

**點解唔脫 cap（關鍵判斷）：** Tier-1（逐字稿 + $1.8B deferred + Federal Register 關稅 + 8-K 45X）
獨立硬證嘅係「backlog 真、關稅現時高、45X 現時係法律」——全部係**市場已知 / 已-priced** 嘅事實。
但 thesis 真正押注嘅承重 magnitude 腿 = 「政策捱得過多個政治週期 + 一間盈利=補貼嘅公司 durable
複合 3-5x」——呢條係**政治**問題，Tier-1 財數證唔到（且成本腿一手證偽）。此乃 §4c 標準**分岔**
（tpu 型：硬證 toll-booth 已 priced，唔證 share-shift 承重腿）→ **唔脫 cap，confidence 受 0.30 綁**。

**Rubric 建議（§4a 掛鈎；judgment 放設計、算術放執行）:**
- **moat 格：2 → 1.5。** 政策 + $1.8B 現金背書 backlog + 非中國碲對沖（皆 Tier-1）撐住真.demand
  韌性，但「結構性成本護城河」半截一手證偽（1c）、政策 binary 存亡曝險（1b）——2 分前提
  「承重經 Level-2 且生還」喺成本腿唔滿足。
- **資本配置/ROIC 格：2 → 1.5。** 盈利/ROIC 帳面靚但 ~100% 補貼製造（剝 45X 後 breakeven）——
  現金真收到但係政策衍生，唔俾滿分。
- **估值格：維持 2（機械讀數，pe_pctile 22 < 50）**，但 prose 註記 E 受 $1.6B 45X 污染
  （呢個係俾 valuation.py/分析員嘅旗，唔准喺 subscore 度酌情覆寫，§4c 反酌情）。
- **成長耐久/TAM 格：2 → 1.5。** 美國裝機 additive 需求真，但兌現靠政策 + backlog（2025 有
  8.3 GW 違約）；durability 腿政策依賴。

---

## 4. 建議（不執行；郁數留返日間 confidence 迴路）

- **confidence：0.32 → 0.30。** 現行 0.32 本身就係 **cap 違規**（sources 只登記一條 tier-3，
  arithmetic cap = 0.30）。red-team 判 **唔脫 cap**（Tier-1 擊中已-priced/周邊，唔係承重 magnitude
  腿）→ 應機械回落到 0.30。淨效果：數字微降，但**性質決定性改變**（見 verdict 措辭）。
  註：若日間迴路認為逐字稿滿覆蓋 + $1.8B deferred 足以登記 tier-1 源脫 cap，則按 §4a 公式
  重算（rubric Σ=6.5/8 × penalty(<40,mid=0.90) ≈ 0.73 raw）——但本 red-team **不建議脫 cap**，
  因承重 magnitude 腿（政策 durability + 已失成本競爭力）Tier-1 證唔到；脫 cap 前呢個 0.73 係
  「已 priced 事實被當成承重佐證」嘅假高。
- **magnitude_tier：3-5x-durable → 標 `magnitude_unconfirmed`（實質收窄至 2-3x）。** wiki 自己
  已留伏筆「reviewer 若重政策 binary 可判 2-3x」——本次一手證據（45X > 淨利、成本護城河已冇、
  backlog 腰斬）正正支持收窄。sizing v2 對此 node 停 magnitude 加成，回落 confidence-only 基準注碼。
- **verdict：`real-policy-moat-and-still-cheap` → 措辭必改。** 建議
  `policy-RENT-champion-not-cost-moat, cheap-on-subsidized-E, policy-binary-is-earnings-body`。
  wiki 應改：(1)「結構性成本護城河」標「一手價格證偽——多晶矽崩盤後 c-Si 已平過 FSLR，
  護城河係政策唔係成本」；(2) 加註「45X $1.6B > FY2025 淨利 $1.53B，盈利=補貼」；
  (3)「連續 7 年逐年延伸」改為「backlog 81.8→47.9 GW 峰後下坡、FY2025 8.3 GW 客戶違約、
  ~3 年能見度」；(4) 記 balance-sheet **正面** finding：$1.8B deferred revenue = 真現金背書，
  「披露 backlog ≠ 入帳緩衝」嘅刀喺 FSLR 斬唔落（同 MU/photonics 決定性分野）；
  (5) 碲 kill 軸降權（供給側一手對沖，剩 cost-creep）。
- **kill 軸改寫：** 「成本護城河解除」mis-specified（成本護城河已冇）——改為「**政策保護
  移除，暴露已失嘅成本競爭力（FSLR ASP $0.35 vs 中國 c-Si $0.09–0.13）**」。新增可量化早警：
  bookings−debookings 淨值連兩季轉負、Section 232 poly 裁決、2028 政策配置、Te 價穿閾值。
  （us-solar 現於 `kill_metrics` = 純 prose、無可量化軸，夜班判唔到距離——上述軸應接線。）
- **sources cap 註記：** 本次 Tier-1 佐證掂到嘅（deferred revenue、關稅存在、45X 存在）全部係
  **已-priced/周邊**事實，照 §4a/§4c 定義**唔足以**當獨立第二源解 cap（承重 magnitude 腿 =
  政策 durability，Tier-1 證唔到）。

---

## 5. Meta-review（一句）

呢次 red-team 三單 pilot 首次**balance-sheet 檢查回正**（FSLR 真有 $1.8B deferred，pilot 嗰把
「披露 backlog」刀斬唔落），證明呢把刀有辨別力、唔係逢 backlog 必斬；但同一輪狩獵搵到更深一層:
**護城河被錯標**——「結構性成本」一手證偽（多晶矽崩盤令 c-Si 反超），真護城河係政策租值，
而**盈利本身就係補貼**（45X $1.6B > 淨利 $1.53B）。最有價值嘅發現係:一個「有盈利、7 年 sold-out、
22 分位平」睇落最穩陣嘅候選,拆開係「補貼 E 上嘅平 + 一個立法週期可抹走嘅超額利潤」——
**「有盈利所以唔係彩票」呢類 claim 應升格做 INGEST checklist 常設一問:盈利剝走政策補貼後仲剩幾多?**
