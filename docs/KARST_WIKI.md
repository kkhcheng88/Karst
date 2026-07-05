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

> **價格同成交量嘅訊號(技術分析、動能、均值回歸)= 風控,唔係 alpha。真正嘅超額回報(alpha),
> 唯一可能嘅來源係 Phase 3 嘅「質性 thesis」(基本面/供需/催化劑故事)。**

點解咁講?我哋跑咗 20+ 個嚴謹回測(線性因子、機器學習、板塊輪動,全部過多重檢定 + 時間外驗證),
**價量訊號預測未來回報嘅能力(forward IC)≈ 0**。佢哋幫到手嘅係**防守**(降低回撤、避開跌浪),
唔係**進攻**(跑贏大市)。

**一句比喻**:**「因子家族防你爆煲,thesis 畀你嗰一擊。」**
- 價量層 = 安全氣囊 + 剎車(生存)。
- Phase 3 thesis = 油門(賺錢)。

**全系統嘅可證偽靶心**:Phase 3 嘅 thesis 排序,**forward IC 要 ≥ 0.05**(達到就跑贏大市、0.10 就翻倍
級)。呢個係我哋判成敗嘅硬指標,而佢**要累積幾個月數據先驗到**——即係 **Karst 最大嘅賭注仲未證實**。

**一個重要微調(唔好誤會「價量完全冇用」)**:價量層有一種**真但細**嘅 alpha,叫**擇時技巧(T1)**——
見下一節。佢真、可以量度(+2-6%/年),但要靠組合(portfolio)先兌現到,而且細過 Phase 3 賭嗰注。

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

## 五、訊號家族結算(逐個定生死 + 關鍵數)

**全部照 §3 標準量度跑過。信心:HIGH=方向釘實、MED=有但要打折、negative=紀律性否定(保留為證據)。**

| 家族 | 一句定性 | 關鍵數 | 信心 | 用法 |
|---|---|---|---|---|
| **動能/趨勢** | 買強勢 = **側避跌浪**,唔係處處贏 | 20日突破大盤 1.51/1.64/1.41 vs B&H 0.91;micro 兩半狂贏 | HIGH | Phase 4 timer(風控) |
| **均值回歸 RSI-2** | 高波先 work、micro 落刀 | mid <5 H2 +101%/2.61;H1 低波蝕 | HIGH | Phase 4,配 RS+regime gate |
| **相對強度 RS** | 揸領先股(選股),兩半贏 | Q5 全 horizon 贏宇宙;RS gate 救 RSI-2 | HIGH | Phase 1 選股 + Phase 4 filter |
| **低波** | 唔係 alpha,防守 tilt | 低波籃回撤 −29% vs 高波 −58%(高波 raw 贏但 survivorship) | HIGH(非alpha) | 防守 tilt only |
| **Vol 擇時** | 半 artifact,走漏反彈 | 條件Sharpe 靚但總財富唔贏 | MED(非alpha) | 用 regime gate 唔用 timer |
| **F&G 恐懼貪婪** | 買恐懼賣貪婪,資本有效 | extreme<5 部署/Sharpe 贏 B&H;活躍 1/3-1/2 | HIGH(風控) | 恐懼加曝險/CSP 窗 |
| **VIX** | 恐懼/入場計,逆向 | VIX>30 → +5-6% fwd63 | HIGH | Phase 0 入場計 |
| **Insider(Form4)** | 大型股短期顯著,打折 | 21/63 日顯著,survivorship 折 | MED | Phase 3 |
| **突破(Donchian/Minervini)** | timer 有用、選股冇 alpha | 20日突破最佳;Minervini 選股 ≈ B&H | HIGH | Phase 4 timer;選股唔當 alpha |
| **止蝕/加碼 risk-layer** | 封尾部生存,唔係回報 | RISK 斬贏家、輸 FIXED | HIGH | 風控唔係 alpha |
| **VCP 收縮型態** | 無增量、輕微傷 | 3 次一致,IC≈0 | HIGH(negative) | **唔建** |
| **GEX(aggregate)** | 對 VIX 無增量 | partial ≈ −0.08 | HIGH(negative) | **唔建**;VIX 已夠 |
| **Gamma 牆(strike)** | 支持/阻力 context 工具 | live,無回測 | 理論撐 | tier-1 zone/regime context |

---

## 六、兩引擎 + 一開關 + filter(點砌埋一齊)

幾十個回測,最後收斂成一個好簡潔嘅結構:

| | 角色 | 定性 |
|---|---|---|
| **引擎① 動能/趨勢** | 買強勢揸趨勢 | **穩健**(冇 regime 大輸);價值 = 側避跌浪 |
| **引擎② 均值回歸/RSI-2** | 買弱勢搏反彈 | **regime 條件**(高波先 work) |
| **開關 Vol/VIX regime** | switch 兩個引擎 | 低波→動能;高波→均值回歸。**自己唔係引擎** |
| **RS** | 選股(揸 leaders)+ filter(gate RSI-2 買 dip) | 穩健 |

**兩種可用組合:**
1. **regime 層**:高波開均值回歸、低波開動能。
2. **名股層(★ 最實)**:**RS 揀邊隻(領先股)× RSI-2 揀幾時(回調 dip)**——動能揀 what × 均值回歸揀 when,
   而且**唔使等 regime、仲救返 RSI-2 嘅脆弱**。

**深層原因**:動能同均值回歸唔係對立學派,係**同一個「報酬自相關」喺唔同時間長短、相反符號**——
短(日-週)= 反轉(RSI-2)、中(3-12月)= 動能(趨勢/RS)、長(3-5年)= 反轉(= 價值股)。

---

## 七、決策矩陣(接乜 / 唔接乜)

**✅ 接線落 spine:**
1. Phase 4:**20 日高突破 timer**(當風控 timing 欄,絕不乘結構分)。
2. Phase 4:**RSI-2 × RS-leader filter × 高波 regime gate**(裸奔 RSI-2 低波流血)。
3. Phase 1:RS 領先股 tilt。
4. Phase 0:VIX/credit/RV 做開關(已有);gamma 牆做 tier-1 zone context。

**❌ 唔做(已證無用/redundant):**
低波選股當 alpha · Vol-timer 當 alpha · VCP · Minervini 全套選股當 alpha · GEX aggregate ·
細價/板塊 ETF 趨勢 · 止蝕/trail 當回報引擎(佢係封尾部)。

---

## 八、未完成 + 下一步(Phase 2 & 3)

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

## 九、東西喺邊(檔案地圖)

| 要做乜 | 去邊 |
|---|---|
| 睇全貌(呢份,layman) | `docs/KARST_WIKI.md` |
| 技術版跨 Phase 真相 | `ARCHITECTURE.md` |
| 現況 / 下一步 / 入口 | `STATUS.md` |
| 風控層結算(標準化量度 + 逐訊號 + 決策矩陣) | `docs/2026-07-05_risk_control_layer_report.md` |
| 每個回測明細 | `backtest/results/*.md`(30+ 檔,有日期) |
| 實驗腳本索引 | `backtest/experiments/README.md` |
| gamma 牆工具 + 理論 | `docs/2026-07-05_gamma_walls.md` + `exp_gamma_walls.py` |
| Phase 3 設計 / 操作 | `thesis/DESIGN.md` · `.claude/skills/thesis/SKILL.md` |
| 每日掃描 | `python backtest/scan.py` |
| 歷史決策/坑 | `.agents/KARS_MEMORY.md` |

---

*收官定案:**價量/擇時/風控層 = 防你爆嘅安全網(有真但細嘅 T1 擇時 alpha,靠組合兌現);真正跑贏大市嗰
一擊,靠 Phase 3 質性 thesis,而佢仲未證實。下一站:Phase 3。***
