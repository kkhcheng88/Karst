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

## 四、五個 Phase(系統骨架)

Karst 分 **Phase 0 至 4** 五層,由上而下。每層標準化寫:**做乜 / 點運作 / 驗證咗乜 / 狀態 / 點用**。

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

## 五、訊號家族結算(逐個定生死 + 關鍵數 + 適用範圍)

**全部照 §3 標準量度跑過(資本效率 / 兩半 / 4 股種 + 市值層)。信心:HIGH=方向釘實、MED=有但打折、
negative=紀律性否定(保留為證據)。數字讀法:部署CAGR% / 條件Sharpe(vs B&H);FULL/H1/H2 = 全期 /
2016-20 平穩牛 / 2021+ 震盪。**

### 5.1 動能 / 趨勢(Momentum)—— HIGH
- **定性**:買強勢揸趨勢 = **側避跌浪(downside protection)**;唔係處處贏,但**冇一個 regime 會大輸**。
- **關鍵發現**:三種做法排序 **20 日高突破 > TSMOM(過去 12 月報酬正負)> 單一 SMA**(SMA 我一度誇大咗,
  已收);價值喺**跌浪 regime(H2)先顯,平穩牛(H1)≈ B&H**(冇跌浪好避)。
- **適用股種/市值(條件Sharpe FULL/H1/H2)**:
  - **大盤指數**:突破 **1.51/1.64/1.41** vs B&H 0.91(兩半贏、修 H1);TSMOM 1.07/0.82/1.28(偏 H2)。
  - **Mag7**:突破 **1.74/1.73/1.75** vs 1.17/1.48/0.91(兩半贏)。
  - **個股市值層全部食,micro 最勁**:TSMOM micro **1.32/1.66/1.03** vs B&H 0.78/1.40/0.27;small/mid/large 溫和贏。
  - **細價 ETF / 板塊 ETF 唔食**(Sharpe 僅僅到 B&H)。
- **信心 HIGH**;**Caveat**:資本效率≠財富(靠 portfolio);市值層 survivorship;20 日突破**已測未接線**。
- **用法**:Phase 4 timer(20 日突破)+ Phase 1 選股偏向強勢。

### 5.2 均值回歸 RSI-2(Mean Reversion)—— HIGH
- **定性**:2 日超賣搏反彈;**regime-gated + cap-gated**——唔係隨時 work。
- **關鍵發現 / 適用**:
  - **Regime**:**高波(2021+)先 work,低波(2016-19)裸奔會蝕**(大盤 <5 入場 H1 = −17%/−0.32)。
  - **市值(決定生死)**:**micro = 落刀**(兩半都負 −13~−34%,永遠唔好 dip-buy);**mid/large = 高波怪獸**
    (mid <5 H2 **+101%/2.61**、large **+73%/2.55**),但 **H1 緊入場係地雷**(small −41 / mid −43 / large −32)。
  - **股種**:大盤 <5/>75 = 32/1.21;細價 24/0.94;板塊 24/0.98;**Mag7 48/1.30 但只喺極端 <5**(動能股,逆向擇時相沖)。
- **★ RS-leader filter 救返佢**:買「回調緊嘅領先股」兩半都正(補 H1 脆弱)。
- **信心 HIGH**(特徵);**用法**:Phase 4,**RSI-2 × RS-leader × 高波 gate**;鬆入場(<10-20)做主,<5 極端加碼。

### 5.3 相對強度 RS(Relative Strength)—— HIGH
- **定性**:**選股(揀邊隻)+ filter(gate 擇時)**,唔係 timer。
- **關鍵發現**:
  - **選股**:按 126 日相對強度排,**最強 Q5 全 horizon 贏宇宙**(前望年化 17.5/17.8/16.3/12.5% vs 宇宙
    14.4/12.1/10.3/9.2%,21/63/126/252 日),**兩半都成立**,最勁 21-63 日。最弱 Q1 只短期反彈、H2 負。
  - **LEVEL(強唔強)先係 edge;TREND(加速/褪色)對選股幾乎無用**(「褪色=陷阱」證錯)。
  - **Filter on RSI-2**:買「回調緊嘅領先股」(RS 高 + 短期回調)> 加速中領先股,兩半穩健。
- **信心 HIGH**;**用法**:Phase 1 選股 tilt + Phase 4 入場 filter。

### 5.4 恐懼貪婪 F&G / VIX —— HIGH(風控 / 開關)
- **F&G**:買恐懼(<20/15/10/5)賣貪婪(>75/80/85/90),**資本有效**。適用:大盤 <5/>75 部署 **32/1.21** vs
  B&H 15.3/0.87;細價 24/0.94;板塊 24/0.98;**Mag7 48/1.30 但只極端**(動能相沖);large 層 37/1.29。
  **甜區極端 <5;活躍 1/3-1/2 時間(唔罕見)**。Caveat:<5 只 7 次、靠 2020;資本效率≠財富。
- **VIX**:**恐懼/入場計、逆向**(VIX>30 → 未來 63 日 +5-6%;>28-40 = capitulation jackpot)。**VIX = 均值回歸
  嘅開關**(高波先開 RSI-2)。credit > VIX 做 regime。
- **用法**:Phase 0——恐懼加曝險 / tier-1 賣 put(CSP)窗;VIX 做引擎開關。

### 5.5 低波 / Vol 擇時 —— HIGH(非 alpha)
- **低波選股**:低波籃 CAGR 7.1/Sharpe 0.56/回撤 **−29%** vs 高波 14.5/0.62/**−58%**(高波 raw 贏但**嚴重
  survivorship**)。**低波唯一實嘢 = 防守(低回撤、逆市企穩),唔係 return。**
- **Vol 擇時**:條件Sharpe 靚一半係 artifact + 走漏 capitulation 反彈 → **非 alpha**。
- **用法**:低波 = 防守 tilt;**Vol 嘅真正角色 = regime 開關,唔係引擎**。

### 5.6 Insider(SEC Form 4 群買)—— MED(Phase 3)
- 大型股 21/63 日顯著(t≈2.3/2.9,DSR 0.79);細價股文獻 edge(Lakonishok-Lee ~7-12%/12 月)但 survivorship
  灌大;**符號隨市值變**(細價 12 個月 +12%、大型短期有但長期反轉)。**信心 MED**,survivorship 打折。

### 5.7 突破 / 型態(Breakout / Minervini / VCP)
- **20 日高突破 = 最佳 timer**(見 5.1)。
- **Minervini 趨勢範本 + 突破 SELECTION = 冇 alpha**:部署效率 large +16 / mid +20 ≈ B&H;細價以下更低。
- **止蝕 + 50MA trail(risk-layer)= 封尾部生存,唔係回報**(RISK 斬贏家、per-trade 輸 FIXED 持有)。
- **VCP 收縮型態 = negative**:3 次一致,VCP 突破每個 horizon 都輸 not-VCP,IC≈0 → **唔建**。

### 5.8 GEX / Gamma 牆(期權定位)
- **GEX aggregate = negative**:對 VIX 控制後 partial ≈ −0.08(無增量)→ **唔建**;VIX 已 subsume。
- **Gamma 牆(strike-level)= live context 工具**:tier-1 支持/阻力區 + 強度 + 企穩線;**無歷史→回測唔到,
  理論 + 研究撐,forward-log 驗證**。當 zone/regime context,**唔當 alpha**。

---

## 六、決策樹 —— 每日、每個候選點行(兩引擎 + 開關 + filter)

**骨架:大市閘 → vol 開關揀引擎 → 選股 → 擇時 → 表達 → 風控 overlay。**

```
【1. Phase 0 大市閘】VIX / credit / 實現波動
   ├─ 極端恐懼(VIX>28-40 / F&G<5)………… 逆向入場窗:tier-1 加曝險 / 賣 put(CSP);膽敢買恐懼
   ├─ 脆弱(credit 擴 / 負 gamma / 高實現波動)… 減曝險、唔開新倉、只做防守 tilt(低波)
   └─ 正常 …………………………………………… 繼續落去

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
   ├─ micro 股永不 dip-buy(落刀);Mag7/個股財報窗避
   ├─ 止蝕 / sizing = 封尾部(唔當回報引擎);集中 + 漸進加碼
   └─ 擇時分永不乘入結構分;capital-efficiency 靠 portfolio 兌現(部署閒錢入唔相關 sleeve)
```

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
| **F&G / VIX 恐懼窗** | 0 | VIX>28-40 或 F&G<5-10 → 加曝險 / tier-1 賣 put | HIGH | <5 樣本少(靠 2020) |
| **credit / vol regime 開關** | 0 | credit 擴 / 高實現波動 → 減曝險;決定用邊個引擎 | HIGH | 已 live |
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
| **止蝕/trail** 當回報引擎 | 佢係封尾部(生存),RISK 斬贏家輸 FIXED |
| **細價/板塊 ETF 趨勢** | Sharpe 僅到 B&H,唔食動能 |
| **micro 股 dip-buy** | 兩半都負 = 落刀 |
| **單一 SMA** 做動能 | 誇大;20 日突破/TSMOM 更好 |

### 7.3 硬規則 / 覆蓋規則
1. **擇時分永不乘入結構分**(獨立欄)——避免用時機呃自己個資格分。
2. **tier-2 個股只 long-only**;期權只喺 tier-1(SPY/QQQ/SPMO)。
3. **micro 永不 dip-buy;個股/Mag7 財報窗避。**
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
| **Phase 2 資金流/敘事** | flow/narrative;insider + DIX 可餵 | 🔴 未建 |
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
