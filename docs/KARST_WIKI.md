# Karst 系統 Wiki — 全貌與實證結算

> **呢份係咩**:用商業門外漢都睇得明嘅話,由頭到尾講清楚成個 Karst 系統——佢想做乜、點運作、我哋幾十個
> 回測驗證咗乜、而家去到邊、下一步做乜。串連晒所有策略發現,砌成 5 個 Phase。
> **技術版真相**見 `ARCHITECTURE.md`;**每個回測明細**見 `backtest/results/*.md`;**風控層結算**見
> `docs/2026-07-05_risk_control_layer_report.md`。呢份 = 單一入口、全貌、layman。
> **更新**:2026-07-05(風控層全部回測完之後嘅收官版)。

---

## 一、Karst 係咩(一頁睇明)

Karst 係一個**每日運作嘅美股投資決策支援系統**。目標係 **NHITL(no-human-in-the-loop)**——即系統自己
由上而下(top-down)分析,**畀決策建議,人負責落單**。

**兩層輸出(two-tier):**
| | 標的 | 做法 |
|---|---|---|
| **tier-1** | SPY / QQQ / SPMO(大盤指數 ETF) | 用**期權工具**(LEAP 長期認購 / 賣 call / 賣 put 收租) |
| **tier-2** | 其他所有個股 | **只做多**(long-only),唔掂期權 |

**每日輸出單位 = 一張「卡」(card)**:每隻股每日一張,答三條問題——**應唔應該入?幾大信念?係咪好時機?**

**一句總綱**:Karst 由上而下睇——**大市 → 板塊 → 資金流 → 個股基本面故事 → 入場時機**——層層過濾,最後畀
一個有理有據嘅建議。

---

## 二、核心信念(幾十個回測換返嚟嘅一句)

> **價量訊號(技術分析、動能、均值回歸)嘅本質 = 「擇時技巧 / 資本效率」,唔係「揀邊隻股」嘅選股 alpha。
> 呢種擇時 alpha 係真嘅、但細,要靠組合(portfolio)先兌現成財富;真正大幅跑贏大市嗰一擊,靠 Phase 3。**

拆開講(呢個係成個 session 反覆釐清嘅重點,唔好簡化成「價量冇用」):
- **選股面 = 冇 alpha**:價量因子預唔預到「邊隻股會跑贏」(forward IC)≈ 0(20+ 回測:線性因子 /
  機器學習 / 板塊輪動,全部過多重檢定 + 時間外驗證)。
- **擇時面 = 有真但細嘅 alpha**:佢真係捉到「高於平均」嘅日子(**T1 擇時技巧,量度到 +2-6%/年**,見 §3.2)。
- **但天真咁用會被打回「風控」**:例如成個指數「入/出」(SPY 揸/走),T1 會被結構拖累(T2)食走 → 淨返
  只降回撤 = 風控。**要換個表達先兌現到財富:個股 long-only(實證 RSI-2 top-quintile 贏 SPY +12.5%),
  或多條唔相關 sleeve 一齊部署閒錢 = portfolio。**
- **大 alpha 靠 Phase 3**:真正可能大幅跑贏,靠質性 thesis(基本面/供需/催化劑)。

**一句比喻**:**「因子家族防你爆煲(兼一個細馬達),thesis 畀你嗰一擊。」**
- 價量層 = 安全網 + **細擇時馬達**(capital efficiency,靠 portfolio 放大)。
- Phase 3 thesis = 大引擎。

**全系統嘅可證偽靶心**:Phase 3 嘅 thesis 排序,**forward IC 要 ≥ 0.05**(達到就跑贏大市、0.10 就翻倍
級)。要累積幾個月數據先驗到——即係 **Karst 最大嘅賭注仲未證實**。**注意兩件事都真:capital efficiency
係真擇時 alpha(細,靠 portfolio);Phase 3 係大 alpha(未證)——唔係非此即彼。**

---

## 三、標準化量度(我哋點衡量一個訊號好唔好)

**所有訊號回測一律照呢套,唔准偷雞。**

### 3.1 主量度 = 資本效率(capital efficiency),唔用 Jensen alpha
一個「有時入場、有時揸現金」嘅策略,唔可以淨睇總回報(因為揸現金嗰陣拖低咗)。要睇**錢落場嗰陣賺得
幾好**:
| 指標 | 人話 |
|---|---|
| **部署CAGR%** | 錢真係落咗場嗰啲日子,年化賺幾多 |
| **條件Sharpe** | 落場嗰陣,每單位風險賺幾多(愈高愈抵) |
| **曝險%** | 幾多時間有貨(其餘揸現金) |
一律**同 Buy & Hold(B&H,買入持有)比**。

**點解唔用 Jensen alpha**:買跌入場會踩中高波動日,令 CAPM 計出嚟嘅 β 虛高,錯誤扣減咗真技巧。

### 3.2 alpha 拆兩橛:T1 擇時技巧 + T2 結構拖累
數學上:**α = 擇時技巧(T1) + 結構拖累(T2)**。
- **T1(正,+2-6%/年)**:擇時真係捉到「高於平均」嘅日子 = **真技巧 = capital efficiency 嘅來源**。
- **T2(負)**:買跌踩高波動日,推高 β,一邊揸現金一邊畀大市升走。
- **結論**:**capital efficiency = 真但細嘅 alpha**;**指數自己入出(SPY 揸/走)會被 T2 食晒 → 淨返係
  風控**;但**換個表達(個股 long-only / 多 sleeve 組合)T2 唔適用 → T1 兌現到**(實證:RSI-2 個股
  top-quintile 贏 SPY +12.5%)。

### 3.3 覆蓋要求(唔准漏)
- **4 個股種**:大盤指數(SPY/QQQ/SPMO)、細價股(IWM/IJR)、板塊 ETF(11 隻 SPDR)、Mag7。
- **4 個市值層**:micro(<$3億)/ small($3億-20億)/ mid($20億-100億)/ large(>$100億)個股籃。
- **兩半驗證(two-halves)**:2016-2020(平穩牛)vs 2021 至今(震盪/熊)——**兩半都成立先叫穩健,
  得一半 = regime 運氣。**
- 細價股用 **size-matched benchmark**(同 IWM 比,唔同 SPY);下負面結論前**對學術文獻**。

### 3.4 Phase 3 嘅量度(唔同):forward IC
Phase 3 係質性 thesis,冇乾淨 Sharpe。量度 = **forward IC ≥ 0.05**(信念排序預唔預到未來回報),
外加命中事件/regime 窗口。慢,要累積。

---

## 四、系統骨架:先分「三個層面」,再行「五個 Phase」

**呢兩樣係唔同維度,唔好撈埋:**
- **層面** = 睇邊個尺度(大市 / 板塊 / 個股)。
- **Phase** = 喺嗰個尺度入面,由上而下嘅處理次序(0→4)。

### 4.1 三個層面(由大到細)—— 好似「先睇天氣、再揀區、最後揀舖」
| 層面 | 問嘅問題 | 用嘅嘢 | 角色 |
|---|---|---|---|
| **① 大市**(SPY/QQQ) | 而家應唔應該落場?(risk-on / off) | VIX×趨勢 2D · 市場 breadth · DIX/情緒 | **主要風控** |
| **② 板塊**(11 大行業) | 落場買邊個行業? | 板塊相對強度 · 輪動 · 年度宏觀敘事(能源2022/AI2024) | **搵 alpha** |
| **③ 個股/主題** | 揀邊隻、幾時入? | 個股 thesis(故事)· insider 腳印 · RSI-2/突破擇時 | **搵 alpha** |

**Edge 喺邊?** oracle 研究(§8)證咗:**真正跑贏嘅空間喺「板塊(年度 regime)+ 個股/主題」,唔喺大市
週度擇時。** 所以**大市層 = 唔好爆煲(風控);板塊 + 個股層 = 搵嗰一擊(alpha)。**

### 4.2 資金流(Phase 2)點樣貼落三層
insider、DIX、breadth 呢啲「資金流腳印」**唔係一個獨立層面,係貼喺每層做「第二意見」**:
- **大市 flow**(DIX / 情緒 / 市場 breadth)→ 確認大市 risk-on/off(多數同 VIX/F&G 冗餘)。
- **板塊 flow**(板塊資金流 / breadth)→ 確認買邊個板塊。
- **個股 flow**(insider 逐公司)→ 確認個股 thesis;**一批同行業 insider 一齊買 = 板塊訊號**。
- **∴ Phase 2 最有價值嗰忽 = 板塊 + 個股 level 嘅 flow 確認 thesis**(edge 喺嗰度),唔係大市 flow。

### 4.3 五個 Phase(每層由上而下嘅處理次序)
每層標準化寫:**做乜 / 點運作 / 驗證咗乜 / 狀態 / 點用**。

### Phase 0 — 市場閘(能唔能夠開新倉)
- **做乜**:睇大市 regime + 脆弱度,決定「而家使唔使避險」。
- **點運作**:VIX(恐慌)+ credit(信用息差)+ 實現波動;高風險就收緊。
- **驗證咗**:
  - **VIX = 恐懼/入場計**:VIX>30 → 未來 63 日 +5-6%(跨所有時期穩);VIX 係**逆向**(高 VIX 喺熊市 →
    反彈)。VIX 係「均值回歸」嘅開關。
  - **credit > VIX** 做 regime(同 KC Fed RORO 研究一致);混合相反極性嘅計(F&G 式)會**互相抵消**。
  - **GEX(莊家 gamma 曝險)測完唔建**:免費 aggregate GEX 對 VIX 控制後**幾乎零增量**(partial ≈ −0.08)——
    VIX 已經 subsume 咗。DIX(暗池)有輕微 flow 訊號可選。
  - **Gamma 牆(strike-level)= live 工具建咗**:tier-1 期權側嘅**支持/阻力區 + 強度 + 企穩線**(見 §5)。
- **狀態**:✅ 已 live(VIX/regime)。GEX 唔建;gamma 牆工具建咗當 context。
- **點用**:大市脆弱 → 唔開新倉 / 減曝險;VIX 極端恐懼 → 反而係入場窗。

### Phase 1 — 板塊 + 相對強度(RS)
- **做乜**:睇邊個板塊強、邊隻股喺板塊入面領先。
- **點運作**:11 個 GICS 板塊溫度(市值加權 + 背離)+ 兩層 RS(股 vs 大市、股 vs 板塊)+ 輪動。
- **驗證咗**:
  - **RS 選股(揸領先股)= 真.穩健**:按 126 日相對強度排,**最強一組(Q5)喺所有時間框都贏宇宙平均、
    兩半都成立**,最勁喺 21-63 日。
  - **RS 係 selection/filter,唔係 timer**(用戶更正):佢揀「邊隻」，唔係「幾時」。
  - **RS 嘅 LEVEL(強唔強)先係 edge;TREND(加速定褪色)幾乎無用**——「褪色 leader 係陷阱」個假設**證實
    錯咗**(褪色 leader 一樣贏)。
- **狀態**:✅ 已 live。
- **點用**:tier-2 選股偏向領先股;RS 亦用嚟 gate 入場時機(見 Phase 4)。

### Phase 2 — 資金流 / 敘事
- **做乜**:讀「因子湯裡冇嘅資訊」嘅資金流同市場敘事。
- **狀態**:🔴 **未建。**
- **點用(將來)**:insider(而家喺 Phase 3)、DIX(免費暗池)可以餵入;同 Phase 3 嘅擁擠度/催化劑扣。

### Phase 3 — 質性 thesis(★ 唯一 alpha 門)
- **做乜**:讀價格圖裡冇嘅嘢——**供需失衡、underinvestment、產能瓶頸、定價權、催化劑**——形成投資
  論點,再打分數做 sizing 乘數。
- **點運作**:價值鏈 → ticker → 一手驗證(逐字稿/披露)→ 擁擠度(crowding)→ 信念分(0..1)。
  裁判 = forward IC。
- **驗證咗**:9 個 Type-B thesis 已建;**但未證**(forward IC 要累積幾個月)。insider 家族(SEC Form 4
  群買)喺呢層:大型股 21/63 日顯著,但 survivorship 打折 → 中信心。
- **狀態**:✅ 已建 / ⏳ **未證**(全系統嘅賭注)。
- **點用**:tier-2 個股分數 = 結構資格 × thesis 信念;tier-1 主題 sleeve。

### Phase 4 — 擇時(幾時扣扳機)
- **做乜**:對已經通過結構嘅名,決定**幾時入場**。獨立一欄,**絕不乘入結構分**。
- **點運作**:RSI-2(2 日超賣反彈)做純價格股權進場;突破觸發(未接線)。
- **驗證咗**:
  - **RSI-2 = regime-gated + cap-gated**:高波先 work(2021+),低波(2016-19)會蝕;**micro 股 dip =
    落刀**(兩半都負);mid/large 高波係怪獸(<5 入場 +101%/Sharpe 2.61)。
  - **RS-leader filter 救返 RSI-2**:買「回調緊嘅領先股」(RS 高但短期回調),兩半都 work,補返 regime 脆弱。
  - **最佳 momentum timer = 20 日高突破 > TSMOM > SMA**:兩半贏 B&H、修返 H1 弱點(用戶「月 lookback 對
    日 K 太慢」直覺獲證)。
- **狀態**:✅ RSI-2 live;20 日突破 timer **已測未接線**。
- **點用**:結構過關後,RSI-2 × RS-leader × 高波 gate 揀時機;絕不乘結構分。

### Phase 編號對照(避免混淆)
| Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|---|---|---|---|---|
| 市場閘 | 板塊+RS | 資金流/敘事 | 質性 thesis | 擇時 |

---

## 五、訊號家族結算(標準化:每個家族同一 7 欄)

**每個家族一律用同一模板:係咩 / 結果 / 股種 / 市值 / Regime / Caveat / 用法。**
- **量度**:資本效率——部署CAGR% / 條件Sharpe(vs B&H);**FULL / H1(2016-20 平穩牛)/ H2(2021+ 震盪)**。
- **符號**:✅ 有 edge(贏 B&H) · 🟡 中性(≈ B&H) · ❌ 輸/無 edge · — 未測或不適用(市場層/全宇宙)。
- **信心**:HIGH=方向釘實 · MED=有但打折 · negative=紀律性否定(保留為證據)。

### 5.1 動能 / 趨勢(Momentum)— HIGH
- **係咩**:買強勢揸趨勢 = 側避跌浪;唔係處處贏,但**冇一個 regime 大輸**(20日突破 > TSMOM > 單一 SMA)。
- **結果**:條件Sharpe(20日突破 FULL/H1/H2):大盤 **1.51/1.64/1.41** vs B&H 0.91;Mag7 **1.74/1.73/1.75** vs 1.17。
- **股種**:大盤 ✅ · 細價 ❌ · 板塊 ❌ · Mag7 ✅
- **市值**:micro ✅(最強 1.32/1.66/1.03 vs 0.78/1.40/0.27) · small ✅ · mid ✅ · large ✅
- **Regime**:H1 平穩牛 ≈ B&H(冇跌浪好避) · H2 跌浪先顯優勢(突破兩半都贏、修 H1)。
- **Caveat**:資本效率≠財富(靠 portfolio);市值層 survivorship;20日突破**已測未接線**。
- **用法**:Phase 4 timer(20日突破) + Phase 1 選股偏強勢。

### 5.2 均值回歸 RSI-2(Mean Reversion)— HIGH
- **係咩**:2 日超賣搏反彈;**regime-gated + cap-gated**,唔係隨時 work。
- **結果**:部署CAGR/條件Sharpe(<5/>75):大盤 32/1.21 · 細價 24/0.94 · 板塊 24/0.98 · Mag7 48/1.30。
- **股種**:大盤 ✅ · 細價 ✅ · 板塊 ✅ · Mag7 🟡(只極端 <5,動能相沖)
- **市值**:micro ❌(落刀,兩半負) · small 🟡 · mid ✅(高波怪獸 +101%/2.61) · large ✅(+73%/2.55)
- **Regime**:H1 低波裸奔蝕(大盤 <5 = −17%/−0.32,緊入場地雷) · H2 高波先 work。
- **Caveat**:micro 永不 dip-buy;H1 緊入場地雷;要 RS-leader + 高波 gate 先穩。
- **用法**:Phase 4 —— RSI-2 × RS-leader × 高波 gate;鬆入場(<10-20)做主、<5 極端加碼。

### 5.3 相對強度 RS(Relative Strength)— HIGH
- **係咩**:**選股(揀邊隻)+ filter(gate 擇時)**,唔係 timer。
- **結果**:最強 Q5 前望年化 **17.5/17.8/16.3/12.5%** vs 宇宙 14.4/12.1/10.3/9.2%(21/63/126/252 日),兩半成立。
- **股種**:— 全宇宙橫截面排名(唔按 4 類分)
- **市值**:— quintile 涵蓋各市值(領先股 across caps)
- **Regime**:兩半都贏;最弱 Q1 只短期反彈、H2 負。
- **Caveat**:**LEVEL(強唔強)係 edge、TREND(加速/褪色)對選股無用**;個股 survivorship。
- **用法**:Phase 1 選股 tilt + Phase 4 入場 filter(買回調中領先股)。

### 5.4 恐懼貪婪 F&G(Fear & Greed)— HIGH(風控)
- **係咩**:買恐懼(<20/15/10/5)賣貪婪(>75/80/85/90);資本有效嘅**逆向部署計時器**。
- **結果**:部署CAGR/條件Sharpe(<5/>75):大盤 32/1.21 · 細價 24/0.94 · 板塊 24/0.98 · Mag7 48/1.30。
- **股種**:大盤 ✅ · 細價 ✅ · 板塊 ✅ · Mag7 🟡(只極端,動能相沖)
- **市值**:micro —(壞數) · small 🟡 · mid 🟡 · large ✅(37/1.29;細/中 survivorship)
- **Regime**:甜區極端 <5;活躍 1/3-1/2 時間(唔罕見)。
- **Caveat**:<5 只 7 次入場、靠 2020;資本效率≠財富。
- **用法**:Phase 0 —— 恐懼加曝險 / tier-1 賣 put(CSP)窗。

### 5.5 VIX × 趨勢 2D(恐懼 × 牛熊)— HIGH(Phase 0 主軸)
- **係咩**:恐懼 / 入場計,**逆向**(高 VIX → 反彈);配趨勢(200SMA)成 **2D 大市閘**(見 §6 XY 圖)。
- **結果**:VIX>30 → 未來 63 日 +5-6%(兩半穩);**牛市+高VIX 前望 +5.1%/回撤淺 −4%(兩半最好+最安全)**;
  熊市+高VIX +1.7%/回撤深 −8.7%(可能落刀)。VIX 對趨勢有獨立增量(partial 兩半 +0.1~0.22)。
- **股種**:— 市場層(SPY),套落全部
- **市值**:— 市場層,不分市值
- **Regime**:VIX 主軸兩半穩;**趨勢(200SMA)= 安全度修正器**(牛淺熊深,穩)。**credit 測完剔除**(regime 反覆、對 VIX 無增量)。
- **Caveat**:熊市方向 regime 反覆(H1 落刀/H2 急彈);極端罕見。
- **用法**:Phase 0 —— **買恐懼優先喺上升趨勢做(② 牛市+高VIX 最安全)**;熊市買恐懼細注;VIX 亦做均值回歸引擎開關。

### 5.6 低波 / Vol(Low-Volatility)— HIGH(非 alpha)
- **係咩**:低波股 / 低波時 = 防守,唔係 return。
- **結果**:低波籃 CAGR 7.1 / Sharpe 0.56 / 回撤 **−29%** vs 高波 14.5/0.62/**−58%**(高波 raw 贏係 survivorship)。
- **股種**:大盤 🟡 · 細價 🟡 · 板塊 🟡 · Mag7 🟡(vol-timer 測 4 類,≈/低過 B&H)
- **市值**:低波籃 vs 高波籃(個股);低波 = 低回撤
- **Regime**:低波 H2 逆市企穩(+5.5% vs 高波 −1.0%)。
- **Caveat**:選股非 alpha(survivorship);vol-timer 半 artifact + 走漏 capitulation。
- **用法**:防守 tilt;**Vol 真正角色 = regime 開關,唔係引擎**。

### 5.7 Insider(SEC Form 4 群買)— MED
- **係咩**:公司內部人集體買入(知情人行為),非價格訊號。
- **結果**:大型股 21/63 日顯著(t≈2.3/2.9,DSR 0.79);細價文獻 edge(Lakonishok-Lee ~7-12%/12 月)。
- **股種**:— 個股(唔按 4 類分)
- **市值**:large ✅(短期) · mid — · small 🟡(文獻 +12%/12月,survivorship) · micro —
- **Regime**:大型短期有、長期反轉;符號隨市值變。
- **Caveat**:survivorship 嚴重灌大;打折。
- **用法**:Phase 3(資金流/知情人)。

### 5.8 突破 / Minervini(Breakout)— HIGH(timer)/ negative(選股)
- **係咩**:新高突破入場(timer)+ Minervini 趨勢範本選股 + 止蝕/trail 風控層。
- **結果**:20日突破 timer = 最佳(見 5.1);Minervini 選股部署效率 ≈ B&H(large +16/mid +20 vs 18.9/19.8)。
- **股種**:timer 大盤/Mag7 ✅ · 細價/板塊 🟡;selection 全部 🟡(≈ B&H)
- **市值**:timer micro ✅ · small/mid/large ✅;selection micro ❌(+6 << 14.4)其餘 ≈ B&H
- **Regime**:突破 timer 兩半(mid/small H2 弱);selection H1 ≫ H2。
- **Caveat**:選股冇 alpha;**止蝕/50MA trail = 限住最大單筆損失(封極端虧損),唔係谷回報**(RISK 斬贏家輸 FIXED);price-only 無量確認。
- **用法**:Phase 4 timer(接 5.1);選股同 risk-layer **唔當 alpha**。

### 5.9 VCP 收縮型態(Volatility Contraction)— negative
- **係咩**:突破前愈嚟愈緊(收縮)嘅底部型態。
- **結果**:VCP 突破**每個 horizon 都輸 not-VCP**(5-63日),連續 IC ≈ 0(3 次不同做法一致)。
- **股種**:— 個股宇宙(3273 股)
- **市值**:— 全宇宙(未細分)
- **Regime**:5-63 日 swing 全 horizon 一致。
- **Caveat**:cache 無量,量維度未測;但 3 次一致穩。
- **用法**:**唔建**(收縮結構無增量、輕微傷)。

### 5.10 GEX aggregate(莊家 gamma 曝險)— negative
- **係咩**:全市場莊家 gamma 淨曝險,做市場脆弱度計。
- **結果**:對 VIX 控制後 **partial ≈ −0.08**(無增量);raw −0.31 但被 VIX(+0.63)subsume。
- **股種**:— 市場層(SPX)
- **市值**:— 市場層
- **Regime**:兩半一致無增量。
- **Caveat**:0DTE 令 EOD-OI 失真;免費版只 aggregate(無 gamma flip)。
- **用法**:**唔建**;VIX/credit/RV 已夠(DIX 免費 flow 可選)。

### 5.11 Gamma 牆 strike-level(支持/阻力)— 工具(理論撐,未回測)
- **係咩**:逐 strike 支持/阻力**區** + **強度** + 企穩線(gamma flip)。
- **結果**:live 快照;pin/flip 有同儕論文撐、牆命中 vendor ~70-78%(自己無回測)。
- **股種**:SPY/QQQ ✅(最可信) · 板塊 🟡 · Mag7 ❌(個股 sign 易破,業績前後更唔準)
- **市值**:— tier-1 為主
- **Regime**:企穩線之上 = 牆較實(區間上落) · 之下 = 跌穿支持急跌(唔係反彈)。
- **Caveat**:無免費歷史 → 回測唔到,靠 forward-log 驗;0DTE 令日內失真;個股避開業績公布日。
- **用法**:tier-1 期權側 zone/regime **context**(揀 strike / 恐懼窗),**唔當 alpha**。

---

## 六、決策樹 —— 每日、每個候選點行(兩引擎 + 開關 + filter)

**骨架:大市閘 → vol 開關揀引擎 → 選股 → 擇時 → 表達 → 風控 overlay。**

```
【1. Phase 0 大市閘 — 2D:恐懼(VIX)× 趨勢(200SMA)】(實證版;credit 測完剔除,見 `results/2026-07-05_market_regime_2d.md`)
   X 恐懼軸(VIX / F&G)= 主軸,逆向 → 話你【幾時買】(高 VIX → 反彈,兩半穩)
   Y 趨勢軸(SPY vs 200SMA 牛熊)= 安全度 → 話你個 dip【有幾深、買得幾安心】(牛淺 −4% / 熊深 −9%,穩)
   ├─ ② 牛市 + 高VIX(升中恐懼)… ★ 最好+最安全 → 買 dip / tier-1 賣 put(前望+5%、回撤淺,兩半穩)
   ├─ ① 牛市 + 低VIX(正常)  … 順勢揸
   ├─ ③ 熊市 + 高VIX(跌中恐慌)… 會彈但 dip 深(−9%)、可能落刀 → 細注/小心(方向睇年代,H1落刀/H2急彈)
   └─ ④ 熊市 + 低VIX(自滿/派發)… 回報弱 → 唔加倉

【2. vol regime 開關】決定用邊個引擎(唔係兩個一齊用)
   ├─ 高波 / 震盪 ……… 開【均值回歸引擎】:RSI-2 買 dip
   └─ 低波 / 順勢 ……… 開【動能引擎】:趨勢 / 20 日突破

【3. Phase 1+3 選股】揀「邊隻」
   ├─ RS 領先股(Q5,LEVEL 高)………………… 必要條件
   ├─ 板塊溫度過濾(強板塊)…………………… tilt
   └─ tier-2 個股:再乘【Phase 3 thesis 信念】… 結構資格 × 信念(alpha 來源)

【4. Phase 4 擇時】揀「幾時入」(獨立欄,絕不乘結構分)
   ├─ 動能 regime …… 20 日高突破觸發
   ├─ 均值回歸 regime … RSI-2 < 門檻(鬆<10-20 做主/<5 加碼)【× RS-leader filter:只買回調中領先股】
   └─ 恐懼窗 ………… F&G/VIX 逆向加碼

【5. 表達】點落
   ├─ tier-1(SPY/QQQ/SPMO)… 期權(gamma 牆揀 strike / 恐懼窗賣 put / 趨勢用 LEAP)
   └─ tier-2 個股 ……………… long-only(結構分 × thesis 信念,擇時用 RSI-2/突破)

【6. 風控 overlay(硬規則)】
   ├─ micro 股永不 dip-buy(跌落去多數繼續插 = 接刀);個股/Mag7 避開業績公布前後幾日(業績大跳空破壞訊號)
   ├─ 止蝕 / sizing = 限住最大單筆損失(封住極端虧損,唔係用嚟谷回報);集中持股 + 贏先漸進加碼
   └─ 擇時分永不乘入結構分;capital-efficiency 靠 portfolio 兌現(部署閒錢入唔相關 sleeve)
```

**Phase 0 大市閘 XY 圖(2D,實證版;數字=前望63d報酬/最差回撤,兩半驗證)**:
```
  熊市    │ ④ 自滿/派發              │ ③ 跌中恐慌
 (SPY<   │   +1.7% / −3.9%          │   +1.7% / −8.7%(dip深、可能落刀)
  200SMA)│   → 回報弱、唔加倉        │   → 細注/小心(方向睇年代:H1落刀/H2急彈)
 ────────┼─────────────────────────┼─────────────────────────────
  牛市    │ ① 正常上升              │ ② ★ 升中買 dip
 (SPY>   │   +2.6% / −3.8%          │   +5.1% / −4.0%(兩半最好+最安全)
  200SMA)│   → 順勢揸                │   → 買!tier-1 賣 put
         │ 低 VIX(平靜/貪婪)        │ 高 VIX(恐懼 >20;>28 更強 牛市+9%)
```
**讀法**:X = VIX(恐懼)話你【幾時買】(逆向,主軸);Y = 趨勢(200SMA)話你個 dip【有幾深/幾安全】。
**★ ② 牛市+恐懼 = 甜區**(兩半實證最好 + 回撤最淺)。**credit 測完剔除**(regime 反覆、對 VIX 無增量)。

**深層原因(點解兩引擎互補)**:動能同均值回歸唔係對立學派,係**同一個「報酬自相關」喺唔同時間長短、
相反符號**——短(日-週)= 反轉(RSI-2)、中(3-12 月)= 動能(趨勢/RS)、長(3-5 年)= 反轉(= 價值股)。
所以「RS 揀領先股(中期動能)× RSI-2 揀回調入場(短期反轉)」係**用唔同 horizon,唔衝突,仲互相加強**。

---

## 七、決策矩陣(接乜 / 唔接乜 / 硬規則)

### 7.1 ✅ 接線落 spine(項目 | Phase | 點做 + 參數 | 信心 | Caveat)
| 項目 | Phase | 點做 / 參數 | 信心 | Caveat |
|---|---|---|---|---|
| **20 日高突破 timer** | 4 | 收市新 20 日高入、新 10-20 日低出;獨立 timing 欄 | HIGH | 已測**未接線**;資本效率非財富 |
| **RSI-2 × RS-leader × 高波 gate** | 4 | RSI-2<10-20(<5 加碼)只喺 RS-Q5 領先股 + 高波 regime | HIGH | micro 排除;裸奔低波流血 |
| **RS 領先股選股** | 1 | 126 日 RS 排 Q5;LEVEL 為主(TREND 唔使) | HIGH | 選股面;個股 survivorship |
| **VIX × 趨勢 2D 大市閘** | 0 | 買恐懼(VIX/F&G 高)**優先喺上升趨勢**(② 牛市+高VIX 最安全);熊市買恐懼細注 | HIGH | credit 剔除;熊市方向 regime-dependent |
| **vol regime 開關** | 0 | 高波開均值回歸引擎、低波開動能引擎 | HIGH | 已 live |
| **Gamma 牆 context** | 0/tier-1 | live 支持/阻力區 + 強度 + 企穩線,揀期權 strike | 理論撐 | 無回測→forward-log;個股 sign 易破 |
| **低波 defensive tilt** | 1 | 脆弱期偏低波(降回撤) | HIGH | 防守用,非 return |
| **DIX flow(可選)** | 0/2 | 免費暗池,高 DIX 偏好 | 低 | 細訊號 |

### 7.2 ❌ 唔做(已證無用 / redundant | 點解)
| 唔做 | 點解 |
|---|---|
| 低波**選股**當 alpha | 高波 raw 贏(survivorship);低波只係防守 |
| **Vol-timer** 當 alpha | 條件Sharpe 半 artifact + 走漏 capitulation |
| **VCP** 型態 filter | 3 次一致無增量、輕微傷,IC≈0 |
| **Minervini 全套選股**當 alpha | 部署效率 ≈ B&H(price-only 版無增量) |
| **GEX aggregate** 做脆弱閘 | 對 VIX partial≈−0.08,VIX 已 subsume |
| **credit(HYG/LQD)做風險軸** | regime 反覆(H1↔H2 反符號)、對 VIX 無穩定增量;QE 年代 credit 擴變買點 |
| **止蝕/trail** 當回報引擎 | 佢係限最大單筆損失(封極端虧損),唔係谷回報;RISK 斬贏家輸 FIXED |
| **細價/板塊 ETF 趨勢** | Sharpe 僅到 B&H,唔食動能 |
| **micro 股 dip-buy** | 兩半都負 = 落刀 |
| **單一 SMA** 做動能 | 誇大;20 日突破/TSMOM 更好 |

### 7.3 硬規則 / 覆蓋規則
1. **擇時分永不乘入結構分**(獨立欄)——避免用時機呃自己個資格分。
2. **tier-2 個股只 long-only**;期權只喺 tier-1(SPY/QQQ/SPMO)。
3. **micro 永不 dip-buy;個股/Mag7 避開業績公布前後幾日(業績跳空破壞訊號)。**
4. **capital-efficiency 靠 portfolio 兌現**(部署閒錢入唔相關 sleeve),唔好裸 lever(vol drag)。
5. **細價股用 size-matched benchmark**(vs IWM 唔係 SPY);任何新訊號要過 4 股種 + 兩半 + 對文獻。
6. **價量層當風控(+ 細 T1 馬達);alpha 靠 Phase 3。**

---

## 八、Phase 3 嘅實證起點 —— 輪動 / Oracle 逆向工程(11 板塊 ETF)

> **Phase 3 唔係憑空覺得「基本面重要」,係由一連串板塊輪動回測「逆向工程」出嚟嘅結論。** 呢節解釋點解
> alpha 一定喺 Phase 3、點解個靶係 forward IC ≥ 0.05、同 Phase 3 應該長咩樣。
> (明細:`results/2026-07-01_portfolio_oracle / rotation_challenge / oracle_forensics / skill_curve /
> gap_forensics / factor_sweep.md`。)

**問題重新框**:唔係「一個訊號贏唔贏自己」,係 **composition**——9-11 個板塊嘅錢點分配。

### 一步步逆向工程(關鍵數)
1. **完美預知上限(oracle)巨大**:每週揀當週最好板塊,top-3 = **155% CAGR**、top-3+現金 = 196%(0% 回撤);
   但**冇技巧嘅平均分(EW 9 板塊)≈ SPY**(免費 composition premium 得 **+0.6pp/年**)。→ 上限全靠預測技巧。
2. **週頻上限係頻率幻象**:持有期一長就崩——**週 151% → 月 66% → 季 38% → 年 23.5%**。真正有意義嘅上限 =
   完美**年度**板塊選擇 ≈ **2× SPY**;週嗰 151% 係 noise-timing。最強量化 TAA(dual momentum + 債避險)
   =7.4% < SPY 11.2%,只降回撤(又係風控)。
3. **獎勵曲線陡凸(唔使揀第一)**:第 2 名 = 16× SPY、第 3 名 = 9× SPY;degrade 到目標 IC 揀 top-3 →
   **IC 0.05 → 10.3%(贏 SPY)、IC 0.10 → 15.6%(~2× SPY)**。排名技巧回報巨大而凸。
4. **但所有量化因子 forward IC ≈ 0**:28 個 Alpha158 因子掃描 + Bonferroni → **0/28 過關**(最強 12 月動能
   IC 0.033、sub-threshold;composite/SVD 都 ~0)。→ **量化門 definitively 關咗:唔係因子唔夠多,係源頭
   一樣(全部價量)。**
5. **★ Oracle 逆向工程 → 兩層 alpha**:
   - **週頻切換 = 不可預測 noise**(散喺所有年份,IC~0,捉唔到)。
   - **年度板塊 regime = 認得出嘅宏觀敘事**:1999-03 科技(dotcom)、2004-07 能源(油超級週期到 $147)、
     2008-10 金融(GFC 震央)、2020-23 能源(COVID+通脹)、2024 科技(AI)。**每年主導板塊當時就知**
     (2022 能源狂升、2008 金融爆煲人人皆知)——**靠宏觀/質性判斷,唔喺價格圖。**
   - **事件層(gap_forensics)**:非科技板塊最大單週跳空,**每一個都對得上一個有名有姓嘅宏觀催化劑**
     (GFC 銀行紓困、俄烏/OPEC 油衝、疫苗重啟)——事件驅動,唔喺 OHLCV。

### 結論 = Phase 3 嘅定義 + 靶
成個系統化約成**一條可證偽問題**:
> **有冇任何訊號(量化或質性),排板塊/主題嘅 forward IC ≥ 0.05?**
- **量化 = 0(門關咗)。**
- **唯一未測嘅源 = 質性資訊(新聞 / 催化劑 / 基本面 / 供需 / 瓶頸)**——正正驅動嗰個年度 regime + 事件跳空,
  **唔喺價格圖 → 就係 Phase 3。**
- **可捕捉目標 = 年度/多月 regime(~2× SPY 上限)**;而**股/主題層 dispersion 仲大過 9 板塊** → tier-2 個股
  + 主題 sleeve 空間更大。
- **Phase 3 天生回測唔到**(冇歷史 thesis 標籤)→ **forward-track**,硬指標 **forward IC ≥ 0.05**。

### 誠實 temper(唔好過度樂觀)
IC 0.05-0.10 係 **HARD bar**——專業 quant 有龐大 breadth + infra 都得 0.02-0.05;一個 operator 週度排 9 板塊
到 IC 0.1 好進取。**我哋而家零證據任何 accessible 訊號過到 0.05。** 但(a)凸獎勵值得追、(b)質性係唯一未測
源、(c)低頻(月度)令 modest IC 抵得住成本 → **Phase 3 值得認真行,但係「開放假設」唔係「已知會贏」。**

---

## 九、未完成 + 下一步(Phase 2 & 3)

**風控/擇時層(Phase 0/1/4)特徵已徹底釘死,冇乜好再挖。** 真正推進 Karst 目標(可證偽 alpha)嘅係:

| | 內容 | 狀態 |
|---|---|---|
| **Phase 3 質性 thesis(主線)** | pilot 端到端行一個主題 → forward IC 累積(數月) | ✅ 建 / ⏳ 未證 → **下一步** |
| **Phase 2 資金流/敘事**(flow overlay,貼三層) | **重點做板塊+個股 level flow 確認 thesis**(insider 已測=MED、DIX 已測)+ **測 breadth 背離見頂**;大市 flow 多數冗餘 | 🔴 未建(平嘢:A 搬 insider 歸類 / B 接 DIX / C 測 breadth) |
| **Phase 3e 危機 tail** | VIX>40 + 被打爛系統板塊救援 sleeve | 🔴 未建 |
| **接線** | 20日突破 timer + RSI-2×RS-leader + gamma 牆 入 spine | 已測未接 |
| **細 gap** | 突破 + 成交量確認;gamma 牆 forward-log 驗證 | 可選 |

**下一個階段重心 = Phase 3 pilot 落地 + forward-IC 累積(alpha 靶心)。**

---

## 十、東西喺邊(檔案地圖)

| 要做乜 | 去邊 |
|---|---|
| 睇全貌(呢份,layman) | `docs/KARST_WIKI.md` |
| 技術版跨 Phase 真相 | `ARCHITECTURE.md` |
| 現況 / 下一步 / 入口 | `STATUS.md` |
| 風控層結算(標準化量度 + 逐訊號 + 決策矩陣) | `docs/2026-07-05_risk_control_layer_report.md` |
| Phase 3 實證起點(輪動/Oracle 逆向工程) | `results/2026-07-01_portfolio_oracle · rotation_challenge · oracle_forensics · skill_curve · gap_forensics.md` |
| 每個回測明細 | `backtest/results/*.md`(30+ 檔,有日期) |
| 實驗腳本索引 | `backtest/experiments/README.md` |
| gamma 牆工具 + 理論 | `docs/2026-07-05_gamma_walls.md` + `exp_gamma_walls.py` |
| Phase 3 設計 / 操作 | `thesis/DESIGN.md` · `.claude/skills/thesis/SKILL.md` |
| 每日掃描 | `python backtest/scan.py` |
| 歷史決策/坑 | `.agents/KARS_MEMORY.md` |

---

*收官定案:**價量/擇時/風控層 = 防你爆嘅安全網(有真但細嘅 T1 擇時 alpha,靠組合兌現);真正跑贏大市嗰
一擊,靠 Phase 3 質性 thesis,而佢仲未證實。下一站:Phase 3。***
