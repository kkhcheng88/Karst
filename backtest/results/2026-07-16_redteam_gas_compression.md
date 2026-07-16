# Level-2 Red-Team：gas-compression-equipment（天然氣壓縮設備樽頸 / USAC）

- 日期：2026-07-16
- 協議：thesis/DESIGN.md §4b（FALSIFY 升級：INGEST 係審判，唔係歸檔）+ §4c（三通道分流）
- 角色：辯方 red-team。**職責 = 事實補全（搵敘事冇展示嘅重大事實），唔係反對表演。**
  每條反方必須錨喺可引用事實/數據；砌唔到錨定事實 = 標「敘事風險」，唔算 finding。
- Pilot 教訓已納入：反面狩獵只收一手（數據/日期/公告/法說先例）；強制回答
  「Tier-1 佐證掂嘅係承重 claim 定周邊事實？」；balance-sheet 硬性檢查。
- 前置裁決：gatekeeper 已判 moat 咽喉喺 OEM（CAT/Ariel），USAC 係受益者/fleet 持有人
  **非咽喉持有人**（backtest/results/2026-07-15_subscore_backfill_draft.md §6），moat
  subscore 已由 1.5 降至 1.0。現行 confidence 0.33 違反 single-source cap（合規值 0.30）。
- 約束：只新增本檔，冇改 themes.yaml / wiki / 任何現有檔。

---

## 1. 控方主張摘要

天然氣壓縮設備樽頸（B 型，cycle early，confidence 0.33，verdict
`real-structural-bottleneck-deeply-unloved`，單一 ticker USAC）。承重 claim：

> 引擎/壓縮機 lead time 已達 **150 週**（2013 年 4–6 月 → 2018 約 1 年 → 2026 年 150 週，
> 13 年**單向惡化**，跨整個商品週期不縮返），管理層明講「our compression services business
> **does not have direct commodity price exposure**」= 解耦油氣週期；USAC 自家 existing fleet
> 因新機供給緊而**升值**，係樽頸嘅**受益者**；ttm_pe 2nd pctile = 全批 40 候選最平最未被發現。

拆四個子命題逐個審：
- (i) 樽頸係**真**（150 週交期、13 年單向惡化、非商品價掛鈎）
- (ii) USAC 係**直接受益者**（新機稀缺 → 自家 fleet 升值 → USAC 有 pricing power）
- (iii) 樽頸**唔會短期內被 OEM 產能解除**（撞 kill condition 第二軸）
- (iv) 「2nd pctile 最平最 unloved」= **市場錯殺/未發現**（撐起 valuation KPI 2/2 + cycle early 定性）

---

## 2. 四個規定動作

### 動作 1 — 反面事實狩獵

**(a) 系統自己渠道（Tier-1 財務，最鋒利）—— defeatbeta quarterly，9 季至 2026-03-31**

- **balance-sheet 硬檢查：USAC 冇 RPO row；Current Deferred Revenue 細且穩，掂唔到 duration 承重。**
  Deferred Revenue 2024–2025 穩定 ~$64–68M，2026-03 跳至 $81M（隨 J-W Power 併購）——**呢個係
  租賃預收（月結預繳鏡頭），約佔年營收 6%，唔係多年合約鎖單**。同 pilot MU「RPO $100B 唔喺
  balance sheet」/ photonics「order book 到 2028 = 披露 backlog」同一形態：**一手財務入面搵唔到
  「150 週樽頸墊到 USAC 多年收入地板」嘅入帳證據**。註：wiki 引嘅「已下 2027–2029 訂單」係
  **USAC 自己買引擎嘅 capex 承諾（佢係買家鎖上游供應），唔係客戶承諾嘅收入 backlog**——方向相反。

- **毛利無擴張（承重機制喺一手數字唔現形）**：營業利潤率兩年橫行——2024-03 29.7% → 2024-06 33.0%
  → 2025-09 34.1% → 2026-03 **27.4%**（併購後跌）。**若 150 週稀缺真轉化成 USAC pricing power，
  毛利應該擴——但冇。** 直接對照 photonics red-team：嗰邊 COHR 毛利 30.3%→37.7%、LITE 16.2%→44.2%
  九季單調擴張（證實「賣得起價」）；**USAC 呢邊毛利平，連「賣得起價」嘅結果都睇唔到**——受益者
  機制喺一手財數比 photonics 更弱。

- **槓桿確認 + 負權益一年（valuation「最平」嘅結構性解釋）**：Total Debt $2.99B、Net Debt $2.97B；
  TTM EBITDA ≈ **$627M** → **Net Debt/EBITDA 4.73x**（符合已知 4.75）。TTM 利息 $189M vs TTM 營業
  利益 $335M → **利息覆蓋 1.77x**（極薄）。**Total Equity 連續四季為負**（2025-03 −$11.9M →
  2025-12 −$112.5M；分派長期超過留存盈利=典型 MLP 退還資本侵蝕賬面），2026-03 才靠併購增發轉正
  $316.7M。→ **「2nd pctile 最平」有結構性解釋：4.73x 槓桿 + 負賬面權益 + MLP 分派封頂上檔,
  市場畀低 multiple 係 correctly-priced,唔一定係「未被發現」。**

- **分派可持續性（用戶前提一手核實，雙向報告）**：季派息 $0.525/unit 穩定，$66.9M×9 季；
  管理層口徑 **DCF coverage 1.72x**（Q1'26，健康）。**用戶前提「USAC 2020 前曾大砍分派」= 一手
  核實為錯**：USAC 自 IPO（2013）從未削減或漏派，$0.525 自 2015 持平，捱過 2018 Energy Transfer
  併購 + 2020 COVID。按 §4b 校準紀律（事實補全、雙向）**照直報告——呢點令 thesis 更可信,分派
  唔係本次利刀**。惟硬 FCF 口徑較嚴：TTM FCF $303M vs 分派 $267M = **1.13x**（僅覆蓋）,前 4 季
  只 **0.77x**,缺口靠舉債（單季發債 churn $599M）——DCF（回加增長 capex,MLP 標準）覆蓋,
  總 FCF 勉強,兩者都真、睇分母。

- **Insider**：本協議未拉 EDGAR（單一 MLP,insider 訊號稀）——記為未狩獵項,非陰性判決。

**(b) 外部一手（WebSearch，篩走意見文）**

- **150 週樽頸 = 真,但係「CAT 客戶一手轉述」,非 CAT/Ariel 官方週數:** 三家上市壓縮商 Q1'26 法說
  各自一手講出交期——**Kodiak（KGS）「3600 型引擎 >180 週」、Archrock（AROC）「CAT lead time ~160 週」、
  NGS 轉述同業「150–180 週」**,且交期隨季度升級（NGS Q4'25 仲係 110–120 週 → Q1'26 150–180）。
  **多操作商獨立佐證 + 惡化中 = 樽頸真確、機制生還兼強化**。惟 **CAT 官方（Q1'26,2026-04-30）只一手
  證實「大馬力往復式引擎 backlog 自 2024 增長 >3.5x」+ gas compression 需求強,從不以「週」報價**;
  **Ariel（私人公司)一手產能/交期公告搵唔到**,樽頸被一手歸咎於 **CAT 3600 系引擎**而非 Ariel。
  → 「150 週」呢個量化錨係 **CAT 二手(操作商轉述)**,同 photonics「32 個月 Tier-2 自陳」同型缺口。

- **撞 kill condition 第二軸(dated,幫控方睇時點):** CAT 一手(2026-04-30,CEO Creed)明確
  **「將大馬力往復式引擎產能由 2024 水平嘅 2x 提升至接近 3x…主要喺 2027 至 2029 年」**。
  → kill 第二軸「主要 OEM(CAT/Ariel)新產能上線紓緩樽頸」**有咗官方時間表,約 2027 起紓緩**,
  唔再係「有冇」問題,係「2027 定 2029」嘅時點問題(同 photonics 供給回應由「宣言」變「dated 承諾」同型)。

- **USAC「受益者」= 被動 + 收購驅動,pricing power 一手弱過同業(最鋒利一刀):**
  - **USAC(Q1'26,2026-05-05)**:rev per revenue-generating HP/月 = **$22.73(+7.9% YoY)**睇似強,
    **但(a)平均利用率倒跌 94.4%→91.9%,(b)rev-gen HP 由 3.56M 升 4.44M 主要嚟自 J-W Power 併購(外延非有機),
    (c)CEO 一手語言只講「新引擎 lead time 拉長 + 收購時機恰到好處」,零具體有機加租幅度或前瞻 pricing power。**
  - **對照同一個稀缺,可交易同業展示咗「主動 pricing power」係點:** **Kodiak(利用率 98%)一手明言
    「設備定價持續向上、合約續約可 repricing 加價、pricing power 延續到 2027 及之後」;Archrock
    (利用率 95%,contract ops 毛利 72%)一手「2025 加價 + 2026 定價改善」帶動 rev/HP 升。**
  - → **同一個樽頸,USAC 係最弱嘅表達:被動 fleet 稀缺受惠 + 利用率倒跌 + 增長靠併購;真.主動
    pricing power 一手證據喺 KGS/AROC 見到,USAC 自身冇畀。** 子命題 (ii)「USAC 係直接受益者」中彈。

- **AI-gas 需求驅動:一手屬實(發電端)但「傳導到 compression」一手零落數:** GE Vernova(Q1'26,
  2026-04-22)gas turbine backlog **100 GW**(YE25 83 GW)、Q1 data center 訂單 $2.4B、slot 排到
  2030+——**AI→天然氣發電需求一手真確、有規模**,惟屬**發電渦輪,非壓縮**。EIA(2026-07 STEO)電力部門
  gas 需求 2026 +2%/2027 +4%(溫和);反面一手:**2026 新增裝機 51% 太陽能 + 28% 儲能 + gas 僅 6.3 GW**,
  近期電力缺口主要 solar+storage 填。**USAC 全部文件零一手將 AI 量化連到自身 compression volume,
  管理層增長歸因併購 + Permian/LNG,無提 AI。** → AI-gas → compression 仍係 forward 敘事(magnitude 腿)。

**(c) 歷史先例(MLP 退還資本 + 油氣壓縮週期)**

- USAC 自己 2015–2016 曾有一段:油價崩,壓縮利用率跌,單位價格由高位回落——**壓縮利用率並非完全
  無週期**(管理層自認 pricing power「喺 low-90s/high-80s 利用率先 kick-in」,即 91.9% 已貼近臨界,
  再跌就失去定價力)。今輪利用率已由 94.4% 跌 91.9%,方向要留意。呢個係**一手可證偽觀測**,非敘事。

### 動作 2 — Steelman 反方(非 wiki/文章自供,事實錨齊)

**「USAC 係買呢個真樽頸嘅最差載體 + 低估值係槓桿 correctly-priced 而非未發現」:**
1. 同一稀缺,**Kodiak(98% 利用率)/Archrock(95%)有一手主動 pricing power 到 2027;USAC 只有
   被動受惠 + 利用率倒跌 + 靠併購增長**（三家 Q1'26 法說一手對照）;
2. **一手財數:USAC 毛利兩年橫行 27–34%(冇擴張)**,對比 photonics 龍頭毛利九季單調擴——
   「賣得起價」嘅結果喺 USAC 一手都睇唔到;
3. **Net Debt/EBITDA 4.73x + 負賬面權益四季 + 利息覆蓋 1.77x + MLP 分派封上檔**——低 multiple
   有充分結構解釋,「2nd pctile 最平 = 錯殺/未發現」係未證斷言;
4. 增長 YoY 全靠 J-W Power 併購（$860M,含 1,820 萬攤薄新 unit + $430M 舉債）,**有機利用率反而軟**。

呢條 steelman 唔需要否定樽頸係真——**就算 150 週樽頸全真,USAC 都可以係捕捉唔到嗰個真樽頸嘅
最弱可交易載體**(pricing power 一手喺 peer 度,唔喺 USAC 度)。

### 動作 3 — 平庸解釋測試

**悶故事：「油氣/LNG capex 週期上行 + 一間高槓桿 MLP 做咗筆攤薄併購」可以解釋幾多？**
- 解釋到:rev/HP +7.9%、利用率 90%+、營收 YoY 跳升、發債擴張——**全部係併購 + 週期偏緊嘅標準現象**,
  唔需要「13 年結構性樽頸令 USAC 有獨特 pricing power」呢個更強假設。利用率**倒跌**同「賣方沽清、
  出租即滿」嗰種結構緊絀相斥。
- 解釋唔到(結構故事嘅額外證據):(1) lead time **13 年單向惡化、跨商品週期不縮返**(2013 4–6 月 →
  2026 150+ 週,多操作商一手佐證)——呢個係真.結構,非單一週期;(2) 管理層「no direct commodity
  price exposure」+ HAL/PTEN/NOV 對照(嗰啲上升週期先講 sold-out、落週期冇聲)——**樽頸機制本身生還**。
- **可區分觀測(datable):**
  1. **2027–2029 = 天然實驗**:CAT 產能 3x 落地 vs lead time。若交期捱得過新產能 → 結構贏;
     若急縮 → 週期贏。
  2. **USAC 利用率 vs 91.9% 臨界**:續跌穿高-80s = 失去定價力確認(管理層自訂臨界);升返 95%+ = 緊絀確認。
  3. **USAC 毛利率**:若始終唔擴張而 peer(KGS/AROC)擴 → USAC 被動載體確認。
- 結論:**子命題 (i)「樽頸真」= 悶故事解釋唔到,有 13 年單向 + 多操作商一手背書,生還。
  子命題 (ii)「USAC 直接受益」+ (iv)「未發現」= 悶故事(併購 + 週期 + 槓桿)大部分解釋到,中彈。**

### 動作 4 — kill 距離(逐條)

| kill 軸 | 當下事實 | 距離判定 |
|---|---|---|
| **lead time 壓縮返常態(150 週 → <52 週)** | 交期方向仍惡化(多操作商一手 150–180 週、隨季度升級)→ **未觸發** | **未觸發、遠距離**;但量化錨係 CAT 二手(操作商轉述),非 CAT/Ariel 官方 |
| **主要 OEM(CAT/Ariel)新產能上線紓緩樽頸** | **CAT 一手明確擴產至 2024 水平 3x,主要 2027–2029**;backlog +3.5x | **未觸發、dated:約 12–36 個月**(2027 起係第一個可證偽窗口)——由「宣言」變「官方時間表」 |
| **需求驅動(LNG/Permian/AI-gas)停滯/逆轉** | LNG/Permian 一手真;**AI-gas → compression 傳導一手零落數**(GEV backlog 屬發電);2026 新增裝機 gas 僅 6.3 GW | **未觸發**;但 AI-gas 腿係 forward 敘事,唔算已兌現需求 |
| **(新增建議)USAC 利用率跌穿高-80s / 毛利率持續不擴張兼落後 peer** | 利用率 94.4%→91.9%(貼近管理層自訂 91% pricing 臨界);毛利兩年橫行 | **早期警戒(非 kill)**;USAC-specific 被動載體確認器 |

---

## 3. 判決：**部分中彈**（樽頸機制生還、承重「USAC 直接受益」中彈、「未發現」被 balance-sheet 推翻、kill 軸 dated）

按 §4b 校準:判決標準 = 承重 claim 面對補全後嘅事實集企唔企得住。逐子命題:

- **(i)「樽頸真」——生還,且被多操作商一手佐證強化。** 13 年單向惡化、跨商品週期不縮、Kodiak/
  Archrock/NGS 三家獨立一手 150–180 週且升級中、管理層「no direct commodity price exposure」+
  HAL/PTEN/NOV 對照——樽頸機制係全 claim 最硬部分,悶故事解釋唔到。惟「150 週」量化錨係 **CAT 客戶
  二手轉述**,非 CAT/Ariel 官方週數,**Ariel 一手完全缺席**(同 photonics「32 月 Tier-2 自陳」同型)。
- **(ii)「USAC 係直接受益者」——中彈(本次最鋒利)。** 一手財數:**毛利兩年橫行冇擴張、利用率倒跌
  94.4%→91.9%、增長靠 J-W Power 併購(攤薄)、CEO 零具體有機加租**;同一稀缺,**Kodiak(98%)/Archrock
  (95%)展示咗真.主動 pricing power 一手,USAC 冇**。**USAC 係呢個真樽頸嘅最弱可交易載體——被動 fleet
  稀缺受惠,非主動定價權持有人。Tier-1 財務掂到嘅(rev/HP、DCF、槓桿)全部係周邊或反向,唔證承重。**
- **(iv)「2nd pctile 最平最 unloved = 未發現」——被 balance-sheet 推翻/收緊。** Net Debt/EBITDA
  4.73x + 負賬面權益四季 + 利息覆蓋 1.77x + MLP 分派封 equity 上檔 → **低 multiple 係槓桿/攤薄/
  上檔封頂嘅 correctly-priced,唔係「錯殺未發現」**。「supply-tight × unloved 最理想象限」框架被侵蝕:
  係 supply-tight × **structurally-levered-correctly-priced**。
- **(iii)「唔會短期被 OEM 解除」——部分中彈(dated)。** 當下未解除(交期惡化),但 CAT 一手擴產至
  3x(2027–2029)令樽頸解除由「有冇」變「2027 定 2029」嘅時點問題。
- **附:分派可持續性 = 反向補全(令 thesis 更可信)。** 用戶前提「2020 曾大砍」一手核實為錯;USAC
  自 IPO 從未削減、DCF coverage 1.72x。**照 §4b「搵唔到重大遺漏/前提有誤要照報」——分派唔係利刀。**

**Rubric 建議(§4a 掛鈎;§4c 三通道分流):**
- **moat 格:維持 1.0(gatekeeper 已判)。** 咽喉喺 OEM;本次進一步證實 USAC 係**被動受益者**
  (pricing power 一手喺 peer 唔喺 USAC)——1.0 錨「樽頸真但護城河主要喺不可交易實體/被稀釋」坐實,
  甚至 reviewer 可辯 0.5(受益者本身係最弱 peer)。建議記 1.0 + 標爭議。
- **growth 格:1.5 → 1.0。** 三驅動入面 **AI-gas → compression 傳導一手零落數(magnitude 腿未證)**;
  有機增長溫和(~5%/yr)、YoY 兌現靠併購而非需求拉動、「2027–2029 訂單」係 USAC 買引擎 capex 非客戶
  收入 backlog。機制真但兌現部分靠未證下一階段 + 靠外延 → §4a 1 分錨「機制真但兌現中/部分靠未證」。
- **valuation(2)/capital(1)格:機械格,本協議不覆核數字。** 但註明:valuation 2 分係
  pe_pctile 2nd + p_base 0.468 機械映射;**建構喺呢個低 multiple 之上嘅「未發現/unloved」敘事
  已被 balance-sheet 推翻**——敘事修正入 verdict/note,唔郁 valuation KPI 數字(§4c:唔酌情改公式格)。

---

## 4. 建議（不執行；郁數留返日間 confidence 迴路 + §4c 三通道）

- **confidence:0.33 → 0.30(合規修正,cap 綁住)。** 公式重算:growth 1.5→1.0 令 base 6.0→5.0/8=0.625,
  penalty(crowding 88.9 → 80–90 帶 × early = 0.75)→ raw 0.469;single-source cap → **0.30**。
  現行 0.33 本身違規(> cap),向下修返 0.30。**red-team 殺傷力唔喺 confidence 數字(cap 已綁),
  喺通道 2 + 通道 3(見下)。**
- **通道 2(cap 資格,binary):唔脫 cap。** 本次 Tier-1 財務掂到嘅(rev/HP、DCF、槓桿、毛利)全部係
  周邊或**反向**(毛利平、利用率跌 = 同承重相斥),冇任何 Tier-1 獨立擊中承重(150 週 duration /
  USAC 直接 pricing power)。照 §4a 定義**唔足以**當獨立第二源 → 續受 single-source cap 綁 0.30。
- **通道 3(magnitude 加成,sizing 層):node 標 `magnitude_unconfirmed: true`,收起 3-5x-durable 加成。**
  node 現標 magnitude_tier `3-5x-durable`;本次 red-team 證:(a)USAC 係被動受益者非主動定價權持有人
  (pricing power 一手喺 peer),(b)AI-gas magnitude 腿一手零傳導,(c)「最平未發現」= 槓桿 correctly-priced。
  **三支撐「durable magnifier」框架嘅腿全部未證/被推翻 → 收起 magnitude 加成,回落 confidence-only
  基準注碼。** 呢個先係本 thesis red-team 殺傷力真正落腳點(唔喺 confidence 數字,喺注碼)。
- **verdict 建議修正:** `real-structural-bottleneck-deeply-unloved` →
  `real-bottleneck-but-usac-passive-levered-vehicle`(樽頸真、生還;但 USAC 係被動 + 高槓桿 + 最弱
  可交易載體,「deeply-unloved」部分被 balance-sheet 推翻)。
- **wiki 措辭建議:**(1)「150 週」標「操作商一手轉述(KGS 180w/AROC 160w),CAT/Ariel 官方週數未證、
  Ariel 一手缺席」;(2)加「USAC 被動受益,主動 pricing power 一手喺 KGS/AROC 唔喺 USAC(毛利平、
  利用率 94.4%→91.9%)」;(3)加「低 multiple = 4.73x 槓桿 + 負賬面權益四季 + MLP 上檔封頂
  correctly-priced,非未發現」;(4)加「AI-gas → compression 傳導一手零落數 = forward 敘事」;
  (5)**修正待補清單:用戶前提『2020 曾大砍分派』一手核實為錯,USAC 自 IPO 從未削減、DCF cov 1.72x**;
  (6)加「已下 2027–2029 訂單 = USAC 買引擎 capex 承諾,非客戶收入 backlog」;(7)Deferred Revenue
  ≈$64–81M = 租賃預收,非多年鎖單(pilot MU/photonics 同型:披露 backlog ≠ 入帳緩衝)。
- **kill 軸建議:** 第二軸(OEM 產能)由定性改 dated——「CAT 大馬力往復式引擎產能 2027–2029 擴至 3x
  如期落地 + lead time 開始縮」。新增早期警戒(非 kill):USAC 利用率跌穿高-80s、毛利率持續不擴張兼
  落後 KGS/AROC、AI-gas 一手仍零傳導。
- **同業對照建議(超出改數範圍,記入待補):** 若要買呢個真樽頸,**KGS(98% 利用率 + 主動 pricing power
  到 2027)/AROC(95% + 72% 毛利)一手表達強過 USAC**;USAC 唯一相對優勢係 2nd pctile 估值,但該估值
  = 槓桿 correctly-priced。ticker 選擇本身值得覆核(wrong-vehicle 風險)。

---

## 5. Meta-review（一句）

本次 red-team 最有價值嘅唔係否定樽頸——**樽頸係真且生還(多操作商一手佐證強化)**——而係發現
**thesis 揀咗最弱嘅可交易載體**:同一個 150 週稀缺,Kodiak/Archrock 有主動 pricing power 一手 +
95–98% 利用率,USAC 只有被動受惠 + 利用率倒跌 + 靠攤薄併購增長 + 4.73x 槓桿 + 負賬面權益四季,
而佢唯一賣點「2nd pctile 最平」正正係呢啲槓桿/攤薄事實被市場 correctly-priced 嘅結果。pilot 嗰把
「披露 backlog ≠ 入帳緩衝」嘅刀第三次落中(USAC 冇 RPO、deferred revenue 係租賃預收);而新增一把
**「揀啱樽頸、揀錯載體」**嘅刀——建議升格做 INGEST checklist 常設一問:**「呢個承重樽頸,眼前呢隻
ticker 係咪最直接嘅一手受益者,定係同業有更強一手表達?」**
