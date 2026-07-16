# Karst-AA 全風險組合設計【Fable 5 應戰書,2026-07-12】

> ## 🛑 提案,唔係指令 — 唔准照本檔行動(2026-07-16 加註)
>
> **本檔用祈使語氣寫(例 §8「即刻 → 賣 SPY 底倉,砌 AA-strict 殼」),但佢係一份未獲批准嘅設計提案。
> 照字面執行會用真錢做一個從未拍板嘅遷移。**
>
> 逐條核實(2026-07-16):
> - **AA-strict 遷移未批准,而且係 blocked。** `thesis/aa_strict_paper_tracker.py:1-3` 明文
>   「daily **PAPER (no real capital)** … before any real-money migration decision」,並引用用戶
>   2026-07-13 嘅明確指示;`STATUS.md:97` 記住「AA 遷移(**#25 blocked**)…等用戶拍板」。
>   → **「賣 SPY 底倉」係提案內容,唔係已批准嘅行動。**
> - **本檔聲稱 `sizing.py` 已行 `--nav-pct` % NAV 制 — 實測唔存在**(`grep nav-pct thesis/sizing.py`
>   = 0 命中)。sizing 現行仍係 $ 制 + `paper_ledger.py` 層做 %-of-sleeve 轉換。
> - 本檔嘅 magnifier「永久人手判斷」立場亦已被 `thesis/magnitude_features.py`(P3,F2/F3/F5 已機械化)
>   部分推翻。
>
> **保留理由**:呢份係「全風險組合」設計探索嘅完整論證同真數,有參考價值。
> **但任何 agent/讀者:本檔嘅祈使句一律當「提案」讀,唔係當「待辦」讀。真錢動作一律要用戶明確拍板。**

> **背景**:用戶挑戰——移除「持有 SPY 現貨 / 任何零 beta 資產」嘅選項,只准用五類非零 beta 工具
> (①SPY/QQQ LEAP call 或 PMCC ②11 GICS 板塊輪動 ③thesis ETF ④thesis 個股長倉 ⑤magnifiers),
> 問:點樣做到最佳 risk/reward?timing 點調整?
> **同場指令**:sizing 一律 **% NAV**——系統係自己嘅 portfolio manager,唔鏡射任何人嘅個人組合;
> 邊個跑個系統都應該攞到同一個建議;forward IC 量度嘅係系統自己。Crypto 剔出討論。
> **本檔三條負重數全部今日真數**:
> `results/2026-07-12_leap_rent_delta_ledger.md`(LEAP 租金,真期權鏈)
> `results/2026-07-12_ballast_parking_ab.md`(防守板塊做偽現金,1999-2026 實測)
> `results/2026-07-12_expectations_gap_v0.md`(估值 v0,姊妹檔 spec 另見)

---

## 0. 先直接答你:而家個組合係咪 well formed?

**係——喺佢自己兩條公理之下。** 公理一:被動底倉不可掂(70% SPY 永不賣);公理二:未經證實
嘅 alpha 只配細錢。喺呢兩條公理下,core v2 嘅每一嚿嘢都有證據支撐,我冇嘢好挑。

**但你條挑戰拆嘅,正正係最貴嗰條公理。** 70% 資本喺度做緊一件事:倉庫 beta。而你哋自己
最重要嘅發現(LEAP = 唯一結構性 alpha 出口)已經證明咗:**index beta 可以用期權好平咁買returns**
——今日真鏈實測:組合 delta 去到 115%,行 0.50Δ 路線只使 **9.55% NAV premium**。即係話
理論上 ~90% 資本可以釋放出嚟做 idiosyncratic alpha,而唔犧牲 index 曝險。呢個結構喺機構界
有名有姓:**portable alpha / return stacking**——beta 用衍生工具攞,實體資本疊 alpha 策略。

所以我嘅判詞:**現組合 well formed,但你嘅挑戰方向正確**——佢逼個系統由「70% 資本瞓覺」
走向「每一蚊都要有工作」。下面係點樣做,以及(誠實)呢條路今日實測出嚟嘅兩個代價。

---

## 1. 三條負重數(設計之前,先睇證據)

### 1a. LEAP 租金(真鏈 2026-07-12)——倉庫可以搬,但要交租

| | SPY 0.80Δ | SPY 0.50Δ | QQQ 0.80Δ | QQQ 0.50Δ |
|---|---|---|---|---|
| 租金(時間值/notional,年化)| 4.56% | 5.77% | 5.95% | 7.53% |
| **每 $1 delta 嘅租金** | **5.70%** | 11.64% | 7.45% | 15.17% |
| 槓桿(delta-notional per $ premium)| 3.09× | **7.27×** | 2.80× | 5.57× |
| 目標 delta 115% 所需 premium | 20.51% NAV | **9.55% NAV** | — | — |

（註:最後一行係 **SPY+QQQ 兩腳合計**(對半分)嘅全組合 premium 需求,唔係 SPY 單腳——
所以 QQQ 兩格冇獨立數。頭三行先係逐腳讀數。）

兩個 lens 各有贏家:**每蚊 delta 嘅碳租 0.80Δ 平一半;每蚊資本嘅曝險 0.50Δ 多一倍**。
Skew 今日重新確認(0.80Δ IV 貴 11.5-13.8pp,同 07-09 spotcheck 一致)→ 0.50Δ 仍然係
model 定價最準嗰點。**設計採用 0.50Δ 單軌(同 core v2 旗艦一致),0.80Δ 雙軌做 BT-6 敏感度。**

### 1b. 「偽現金」實測(1999-2026,HK 稅後)——挑戰約束有真.代價

四個倉庫方案,同一條 200SMA 閘(192 次切換,成本 10bps/邊):

| | CAGR | Sharpe | MaxDD | 關鍵讀數 |
|---|---|---|---|---|
| W1 SPY 長持 | 8.1% | 0.50 | −55.6% | benchmark |
| W2 閘出→現金 | 4.9% | 0.48 | **−28.4%** | 傳統做法 |
| W3 閘出→XLP/XLU/XLV | 6.6% | 0.47 | −42.2% | **bear episode 平均輸現金 −1.51%/次(n=14)** |
| W4 防守籃長持 | 7.3% | **0.55** | −39.5% | 牛市租金:全期 −1.03pp/yr,**H2(2012+)−2.66pp/yr** |

**誠實結論:防守板塊唔係好嘅現金替代品**——2008 嗰次閘外 259 日,籃子 −20.7% vs 現金 +0.7%。
禁零 beta 資產嘅代價 ≈ **MaxDD 深 14pp + 每個熊市 episode −1.5%**。呢個唔係設計失敗,
係約束嘅真實價錢,要擺喺枱面俾決策者揀(→ §2 兩個變體)。
但同時注意 W4:防守籃長持 Sharpe 0.55 **贏** SPY 0.50——防守股做**常設 ballast**(唔係臨時
避難所)係有 risk-adjusted 根據嘅,佢嘅牛市落後可以用 LEAP delta 補。

### 1c. 估值 v0(15 主題 expectations-gap)

見 `docs/2026-07-12_valuation_expectations_gap_spec.md` + `results/2026-07-12_expectations_gap_v0.md`
——AA 嘅 T sleeve 用「P_base coverage + 隱含增長」做入場紀律(gap 負 → watch 級)。

---

## 2. Karst-AA 設計(全部 % NAV;NAV=100%,邊個跑都係同一個答案)

### 2.0 約束詮釋(要明寫,唔准將來搬龍門)

- 「零 beta 資產」= 現金/T-bills/貨幣基金,**硬禁**(strict 變體)。
- 「SPY 現貨」禁——但 11 GICS ETF 加權可以合成 SPY,所以呢條禁令嘅真正含義只可以係:
  **唔准有「唔使解釋嘅被動持倉」**。每個 ballast 組合必須係 regime 規則嘅輸出,預先註冊,
  唔係 cap-weight 靜態複製。板塊輪動嘅角色 = **beta 變速箱**,唔係進攻(0/28 + 恐慌買殘板塊
  顯著負,兩個結論企硬)。

### 2.1 四個 sleeve(% NAV,PRELIMINARY 期讀數)

| Sleeve | 內容 | 牛市配置 | 熊市配置 | 角色 |
|---|---|---|---|---|
| **B|Ballast** | 防守/quality 板塊籃(XLP/XLU/XLV 起步;規則見 2.3)| 40-50% | 55-70% | beta 倉庫 + 資金水塘(W4 Sharpe 0.55 嘅根據)|
| **L|Index 引擎** | SPY+QQQ 0.50Δ LEAP,**per-leg 200SMA 閘**(core v2 引擎原封不動搬過嚟)| premium 10-15% NAV | 0%(閘出)| 補 delta 去 target band + 已證 +6.5pp 保守 α 嘅嗰部機器 |
| **T|Thesis/Magnifier** | top-K(5-7)theme,conf×magnitude 排位,expectations-gap 閘;binary 名微注 option-framing | 15-30%(earn-in:PRELIM 15 → PASS 25 → PASS+兩季 30)| kill/crowding 規則自然縮 | idiosyncratic alpha——**呢度先係 AA 對 core v2 嘅真.升級**(alpha 資本由 ~4% 變 15-30%)|
| **C|Crisis sleeve** | WS2 ARM/ENTER 原規則 | 0%(平時)| ≤5% | 危機右側買入,funding 由 B 轉出 |

單一 theme 倉位:1.5%–6% NAV,下限 1.5%(低過就唔開倉,留 watch);binary 名每注 ≤0.5%。
**Sizing 全部 % 制**:`sizing.py` 嘅 $41k/$20k/$15k 參數作廢,改 `--nav-pct` 模式
(per-theme raw cap = min(conf × 10% NAV, 6% NAV) 級距,實際常數由 BT-2 定案)。

### 2.2 Delta 總帳(成個設計嘅單一控制變數)

**portfolio_delta = Σ(sleeve 權重 × β)+ LEAP delta-notional**,每月首交易日核數
(thesis sleeve 嘅 β 用 `beta_check.py` 現成讀數;佢由風控工具升級做總帳輸入)。
2D regime(200SMA × VIX,原有)決定 target band,**LEAP 係填縫劑**:
`LEAP 目標 delta = band 中位 − B 貢獻 − T 貢獻`——T sleeve 愈大,L 自動愈細,
**防止「同一注押兩次」**(portable alpha 喺 2008 死因 = alpha sleeve 其實係 beta;
Karst T sleeve 係 AI 重倉長倉,必須入帳,唔准當佢中性)。

| Regime(現有 2D)| Target delta band | 講人話 |
|---|---|---|
| 牛 + 平靜(兩 leg >200SMA,VIX<20)| 105–125% | 全速,輕槓桿 |
| **牛 + 恐懼(>200SMA,VIX>28)** | 115–140% | 你哋已證嘅最佳象限——B 轉 L/T 加注 |
| 一 leg 閘出 | 80–105% | 半速 |
| 熊(兩 leg <200SMA)| **strict:50-65% / pragmatic:35-50%** | 見 2.4 兩變體 |

對照:core v2 熊市 delta ≈ 70-72%(SPY 底倉揸到尾)。**AA 兩個變體喺熊市都低過 core v2**
——呢個係 AA 嘅第二個賣點:牛市曝險相若、熊市曝險更淺、alpha 資本大一個數量級。

### 2.3 Ballast 組成規則(預先註冊,免變 discretion)

- 熊市 / 一 leg 閘出:XLP/XLU/XLV 等權(defensive trio)。
- 牛市:trio 佔 ballast ≥60%,其餘 ≤40% 可按季輪入「quality carry」板塊(規則:唔准持有
  三個月內 priced-in 讀數 top-decile 嘅板塊;輪動唯一目的係咪 beta 微調,唔係 alpha 主張)。
- 恐慌窗(牛 + VIX>28):B → L/T 轉移上限每次 10% NAV,T+1 執行,唔接刀(買 SPY delta
  唔買殘板塊——「恐慌買殘板塊 −2.45%/次 t−2.52」結論企硬)。

### 2.4 五類指定工具逐一對號(每類喺邊、點解咁擺)

| 你指定嘅工具 | 喺 AA 嘅位置 | 理由 |
|---|---|---|
| ①**LEAP call** | L sleeve 主體(0.50Δ,per-leg 200SMA 閘)| 已證引擎;skew 最細 model 最準;9.55% NAV 填到 115% delta |
| ①**PMCC** | **以拆件形態存在**(v3.1 已定案:long leg ≡ LEAP,short call 獨立計時機)——貪婪窗(F&G>75 / B&B≥9 / RSI-2>90)先沽 30-45d 0.20-0.30Δ call 疊喺 LEAP 上面,即「條件性 PMCC」 | 唔做常設 PMCC 因為 short call 喺趨勢市斬贏家(shortcall timing 研究);但佢係 AA 入面**唯一唔沽貨都拉得低 delta 嘅工具**——喺 strict 變體(冇現金)入面角色更重:貪婪窗 + 熊市過渡期用短 call 收租兼壓 delta 落 band 下半 |
| ②**11 GICS 板塊輪動** | B sleeve 嘅 beta 變速箱(2.3 規則)| 進攻已判死(0/28);defensive trio 做熊市地台、牛市 ≤40% 輪 quality carry |
| ③**Thesis ETF** | T sleeve 嘅**預設表達層**——WS5 表達次序原封保留:主題 ETF 籃(DRAM/FOTO/URA+GRID+UTES/NASA…)行先,大型純 play 次之,細價純 play 殿後 ≤1/3 | ETF 攞 theme beta 兼分散單票風險;佢哋嘅 β 照入 delta 總帳(purity/liquidity 已逐隻評,themes.yaml 現成)|
| ④**Thesis 個股長倉** | T sleeve top-K 嘅集中表達(1.5-6% NAV/注,expectations-gap 閘)| 冇乾淨 ETF 嘅主題(advanced-packaging/USAC/FSLR 呢類)唯一表達;gap 正 + early 先俾大注 |
| ⑤**Magnifiers** | T sleeve 入面嘅獨立注碼邏輯:per-node magnitude_tier 驅動 conf×magnitude 排位;rubric F1/F3/F4 做早篩(唔等 constraint 語言確認);binary 名(SMR/pre-earnings)固定微注 ≤0.5% NAV option-framing | Magnifier 係 T sleeve 嘅「刺刀」——佢哋唔係另一個 sleeve,係 top-K 排位入面 magnitude 軸權重最大嗰批;10x 數學 = 唔對稱 payoff × 重複落場,唔係注碼大 |

### 2.5 兩個變體(關鍵決策點,證據已擺齊)

| | **AA-strict**(字面遵守挑戰)| **AA-pragmatic**(我嘅推薦)|
|---|---|---|
| 閘出後 LEAP premium 現金 | 唔准現金 → 轉入 B(防守籃)| **准短暫現金停泊**(佢係閘嘅停車場,唔係策略配置)|
| 熊市 delta 地台 | ~50-65%(B+T 冇得再低)| 35-50% |
| 實測代價 | **MaxDD 深 ~14pp、每熊市 episode −1.5%**(1b)| 冇呢筆稅 |
| 哲學 | 每一蚊任何時候都喺風險資產 | **每一蚊嘅「策略」位置都係主動決定;現金只可以係「閘關咗」嘅暫存態,策略權重永遠 = 0** |

我嘅立場:**挑戰嘅真.洞見係「殺死永久死資本」,唔係「連停車場都拆埋」。** 1b 嘅 14pp MaxDD
係純代價,冇補償回報——一個以最佳結果為目標嘅 portfolio manager 唔應該交呢筆稅。
AA-pragmatic 保留咗挑戰嘅全部精神(策略層 100% active、冇被動底倉),只係將
「閘出→邊度等」呢個戰術問題交返俾證據(W2 贏 W3)。**但兩個變體都會入 BT-2 對照跑**,
如果 strict 喺 capital efficiency 上反超(例如防守籃嘅 recovery beta 幫佢追返),照數據改口。

---

## 3. Timing 點變(直接答你第二條問題)

**訊號一條都冇變——變嘅係訊號嘅「輸出端」。** Core v2 嘅訊號輸出係「入/出」;
AA 嘅訊號輸出係「delta band + 資金去邊個 sleeve」。逐條:

1. **200SMA cross(每日,1 分鐘)**:照舊 T+1,但動作由「沽 LEAP→現金」變「沽 LEAP→
   (strict)入 B /(pragmatic)停車場」;cross 返上去,B/停車場 → 重建 LEAP。
2. **月度儀式升級**:「月度 top-up」(core v2 機制核心)升級做「**月度 delta 核數**」——
   首交易日:①計 Σβw ②對 band ③調 LEAP 張數 ④T sleeve target vs actual 對齊。
   top-up 嘅精神(補彈藥防 cash-starved)完整保留,只係彈藥庫由 SPY 底倉變咗 B。
3. **恐懼窗(牛 + VIX>28)**:由「可選人手 M1」升級做**機械規則**:B→L 轉 5-10% NAV
   (你哋 2D 回測:呢個象限兩半前望最好 +5%)。AA 冇咗「底倉永遠唔郁」嘅顧慮,呢個訊號
   終於有錢可用——**呢個係 AA 對 timing 嘅最大解放**。
4. **Breadth washout(bottom decile,已證 21d +2.58% ≈3× baseline,單邊)**:新增一次性
   boost:+5% NAV delta(經 LEAP),21 個交易日後歸位。單邊訊號單邊用(頂部唔做嘢)。
5. **Roll 梯**:LEAP book 大咗,R4 由單點 roll 改做**季度 1/4 梯**——四個到期批次輪流,
   免單日 term-structure/IV 事件食成本機器。
6. **T sleeve timing 唔用 TA(企硬)**:入場 = cycle_stage + expectations gap(early+gap正
   = 爽快建倉;late+gap負 = watch);離場 = kill / 過期 / beta化 / **新增 crowding-extreme
   trim**(擁擠複合讀數 top decile 且倉位 ≥2× 成本 → 機械 trim 1/3,資金回 B 或 early theme)。
7. **危機 sleeve(VIX>40 ARM → <30 ENTER)**:照 WS2,funding 表預先寫死(由 B 轉,
   唔係新錢),期權表達可用。

---

## 4. 點解 AA 嘅 risk/reward 應該更好(機制,唔係願望)

1. **Alpha 資本 ×6**:core v2 實際 alpha 資本 = LEAP premium(15% × 70% 機器)+ 衛星 ~4%;
   AA = LEAP premium 10-15% + T sleeve 15-30%,全部有 thesis/引擎級證據排位。
2. **熊市更淺**(2.2 對照表):core v2 揸 SPY 底倉食盡 −54%;AA 熊市 delta 35-65%。
3. **恐懼窗終於有彈藥**:core v2 最佳象限訊號得個 M1 人手可選;AA 有機械 B→L 通道。
4. **每蚊曝險嘅租金透明**:1a 表令「倉庫成本」第一次變成可核數嘅 line item。
5. **代價都透明**:LEAP 租金 ~5-7% NAV/年(全牛市配置)、QQQ 0.50Δ spread 6%、
   strict 變體嘅 14pp MaxDD 稅、model 風險原封繼承(30d→1y IV 映射仍係最大假設,
   damped 版做 operative)。

---

## 5. 回測計畫(全部可以喺現有 harness 做;trial registry 預先註冊)

| # | 測乜 | 設計 | 判官 | 狀態 |
|---|---|---|---|---|
| BT-1 | 偽現金(閘外停泊)| W1-W4,1999-2026,HK 稅 | DD + episode 超額 | ✅ 今日完成(1b)|
| BT-2 | **AA 全組合 vs core v2 vs SPY** | 重用 `leap_real_sweep` 機器:ballast 序列 + delta 總帳 + 0.50Δ 引擎;strict/pragmatic 雙變體;base/damped 雙 model;兩半期 + 2008/2020/2022 | capital-efficiency 套餐 + MaxDD ≤ SPY + 保守 model t≥2.5;**入 trial registry 計 Bonferroni** | 下一步,1-2 session |
| BT-3 | Regime delta band 嘅增量 | 固定 115% vs 2.2 band 表(增量原則:淨測嗰一扭)| 同上 | BT-2 之後 |
| BT-4 | Washout boost 增量 | AA ± 第 3 節第 4 條 | 同上 | 同上 |
| BT-5 | Expectations-gap 判別力 | 案例庫 ex-ante(MU16/23、FSLR/STP、WOLF/SMCI 負對照)| gap 符號 vs 結局 | 見估值 spec 檔 |
| BT-6 | 0.80Δ 倉庫軌 vs 0.50Δ 單軌 | 雙 tranche 敏感度 + QQQ spread 壓力 | 同 BT-2 | 敏感度級 |

**誠實預告**:BT-2 嘅 α 唔會係 core v2 α + T sleeve α 嘅簡單相加——T sleeve 喺回測入面
只可以用 proxy(theme basket 歷史),佢嘅真.判官係 forward IC/Brier,唔係歷史模擬。
BT-2 能證明嘅係:**結構層面**(ballast+LEAP+band)唔輸 core v2;T sleeve 嘅增量係
forward 問題。呢一點唔會用回測包裝過去。

---

## 6. 判詞

- 現組合:**well formed,公理內無可挑剔;公理本身(70% 死資本)係你哋最貴嘅選擇。**
- 挑戰方向:**啱**——portable-alpha 化係現有 LEAP 發現嘅自然延伸,唔係推倒重來。
- 挑戰字面:**有一條實測代價**(禁現金 = 14pp MaxDD 稅)→ 推薦 AA-pragmatic
  (策略層零死資本,現金只做閘嘅停車場),strict 做對照組一齊回測,俾數據講最後一句。
- 落地次序:BT-2/3(結構)→ % 制 sizing.py 改造 + expectations-gap 閘(T sleeve)→
  paper 三個月(delta 總帳月度核數行起上嚟)→ 先郁真錢。

---

## 7. ★ BT-2 已跑(同日 addendum)——結構成立,而且推翻咗 §2.5 嘅推薦

**結果檔:`backtest/results/2026-07-12_bt2_aa_vs_core.md`**(2001-2026,step-0 重現 core v2
先過閘:base +12.38pp/damp +6.44pp 全落 pre-registered band;12 組會計 run、307,056 條
bar 級 assert 全過)。三個判決:

1. **結構層成立**:AA 用原始回報換返 ~11pp 淺啲嘅 MaxDD(strict −44.2% / prag −43.7%
   vs core v2 −54.5% / SPY −55.6%),最差 12 個月 −36% vs core v2 −46%,β 0.85-0.91。
   保守 model α:AA-strict +5.0pp(t3.4)vs core v2 +6.4pp(t3.0)——差 1.4pp,
   而呢 1.4pp+ 正正係 live T sleeve 要用真.揀股功力填返嘅位(本測試 T=零 alpha QQQ 代理)。
2. **§2.5 推薦被證據推翻:AA-strict 贏 AA-pragmatic**——回報同 α 都贏(base +15.4%/+7.5pp
   t5.0 vs +12.8%/+5.4pp t4.1),MaxDD 基本一樣(−44.2 vs −43.7)。機制:strict 泊喺 trio
   嘅閘外資金唔入 delta 對沖帳,開緊嗰條 leg re-lever 更多,且 trio 喺復原期贏過瞓覺現金;
   孤立 ballast 測試嗰筆「14pp 稅」喺全結構入面唔成立(兩個變體 ballast 都係主導 sleeve,
   閘外路由嗰橛太細,搬唔郁 MaxDD)。**推薦改口:strict 行先**(用戶原挑戰嘅字面版勝出)。
3. **統計紀律**:Bonferroni×48 —— 6 個新 trial base IV 全過;damp IV 得 AA-strict @115
   (p=0.000794)同 @130 過;**AA-strict 係唯一連保守 model 都過 Bonferroni 嘅格**
   (core v2 自己個勝出格 damp p=0.095 都唔過呢把尺)。DSR 兩個 headline ≥0.999。
   Caveat 不變:LEAP model 風險原封繼承(30d→1y IV proxy);T sleeve 真 edge 係 forward
   IC/Brier 問題,歷史模擬冇資格答。

## 8. 而家個 model 應該點行(2026-07-13 定稿:三步遷移)

**原則:結構先行、主題錢賺返嚟(trust is earned 原封不動)。HK 冇 CGT,換結構零稅務成本。**

1. **即刻 → 裁判首讀數(~10 月)**:賣 SPY 底倉,砌 AA-strict 殼(ballast trio + delta
   總帳 + 0.50Δ LEAP 引擎,band 115 起步)。T sleeve(25% NAV)**大部分揸市場代理**
   (QQQ——即 BT-2 已證嘅零功力版),真主題只佔 PRELIMINARY 紀律容許嗰橛(top-K 集中
   + expectations-gap 閘 + % NAV sizing v2)。結構著數即刻兌現:MaxDD 淺 ~11pp,
   且係唯一 damp model 過 Bonferroni×48 嘅配置。
2. **裁判 PASS 後**:T sleeve 代理 → 真 top-K 主題(earn-in 階梯照 §2 表)。
3. **跑順一季後**:檢討 band 115 → 130(strict@130 damp +5.8pp t3.5 亦過 Bonferroni,
   MaxDD −45.0%——貼近 core v2 回報、坑淺 10pp;先 paper 一季 delta 總帳操作零甩漏
   先升檔)。

**反面條件(寫低先算誠實)**:如果最終判斷主題層永冇 alpha(裁判持續 FAIL / T sleeve
歸因長期 ≈0),core v2 先係正確機器(純大市盡曝險攞 +6.4pp)——AA 嘅上限靠主題兌現,
結構只保證佢唔輸喺風險調整層面。遷移執行細節(委託單次序、LEAP 換月銜接、ballast
建倉分段)屬執行 backlog,唔喺本檔 scope。

### 8a. 放寬約束後重審(2026-07-13,用戶問「准揸 cash / 准揸 cash+SPY 之後仲揀唔揀 AA?」)

**兩個放寬其實都已被今次測試覆蓋,結論不變:**
- **准現金**:BT-2 兩變體唯一分別就係呢樣——pragmatic(閘外泊現金)damp +3.8pp
  vs strict(照入 trio)+5.0pp,MaxDD 相同;現金停泊實測蝕章,唔採。
- **准 SPY(輪動用法)**:ballast 測試 W3(牛揸 SPY/熊轉 trio)CAGR 6.6% 輸 W4
  (trio 長揸)7.3%,Sharpe 0.47 vs 0.55——切換摩擦食突,唔採。
- **准 SPY(長揸壓艙用法)= core v2 本人**:純歷史結構數同 AA-strict 接近打和
  (core v2 Sharpe base 0.98 vs 0.89、damp 0.73 vs 0.74;α/MaxDD 比率 core v2
  6.4/54.5 vs AA@130 5.8/45.0——比率 AA@130 佔優)。決勝三點屬向前望:
  ①ratio(130 檔性價比高);②主題層資本容量(4% vs 25%,成套 Phase-3 嘅賭注要屋住);
  ③swing/機會主義風格需要 drawdown headroom(機會階梯 C-core/B 要 spare 油門)。
  **最終定案:維持 §8 三步遷移(AA-strict 殼 → PASS 入真主題 → 升 130),
  回頭條件照舊。**

### 8c 前置(2026-07-13 用戶追問):「防守」點定義?要唔要機制/擇時?

1. **職責定義(唔係標籤)**:ballast 五條職責——非零 beta 股票 / downside capture 明顯
   <1(2008 實測 trio −15~−29% vs SPY −37%)/ **同 T sleeve 正交**(AI 重倉嘅對立面,
   ballast 價值一半在於「唔係你嗰注」)/ 流動性 / 冇期權租兼有息。
2. **機制 = 季度「防守體檢表」**:候選(XLP/XLU/XLV/USMV/quality/div 系)每季量
   downside capture(3y 滾動)、對 QQQ 相關性、**HK 稅後淨息(30% 預扣——XLU 高息
   年蝕近 1pp 稅,USMV 低息係結構著數,香港獨有角度)**、流動性;按職責排名揸頭 3-4。
   成份可換,理由只可以係「體檢唔合格」,唔准係「估下季邊個贏」。
3. **防守股之間擇時:唔做**(三條 in-house 證據:板塊進攻 0/28;W3 切換輸 W4 長揸;
   預測冧市型態 = 系統唔玩嘅遊戲)→ 用「分散頂替預測」(消費+公用+醫療+可選 min-vol,
   唔同冧市型態各有一隻)。唯一可預註冊再測嘅例外:利率急升期減 XLU(公用似債)。
4. **內部咬合**:ballast β 愈低,冧市墊愈厚但 LEAP 租愈貴(β0.55 trio vs β0.7 min-vol
   係一個可測嘅錶盤)。
5. **→ BT-7 立項**:trio vs trio+USMV vs 五隻分散版 vs 純 min-vol,HK 稅後,判官 =
   downside capture + 三壓力窗 DD + 對 QQQ 相關 + 淨回報;預先註冊,唔准鬥靚回報擇優。
   (USMV 2011+ 數據限制要如實標。)

### 8b. 追問三條(2026-07-13):交易成本 / 「現金搏時機」/ B-A-D 裝落 core v2

1. **交易多寡唔係決勝點**:BT-2 全部係扣成本淨數(ETF 10bps/邊、期權 0.5%/邊,HK 冇
   CGT),AA-strict +5.0pp 係畀晒手續費先贏;core v2 真.優勢係心力(每日 4 個數),
   唔係成本。
2. **「留現金搏時機」嘅正確講法係「留可調動資本」**:瞓覺彈藥(現金停泊)已測蝕章
   (pragmatic +3.8 vs strict +5.0,DD 同);返工彈藥(ballast trio ~60%)先係機會階梯
   嘅 funding 來源;**core v2 先係彈藥最少嗰個**(70% 鎖死永不賣)。
3. **B/A/D 裝落 core v2 嘅相容性**:B 結構中立(邊個殼都加分,細注指數層);A 勉強得
   但會食晒現金袋、實質上係喺旁邊重建 AA;D 價值同主題資本成正比(core v2 主題 ~4%,
   D 冇肉食)。→ 兩個完整套餐:**「簡單機器」= core v2+B+C-core**(指數層世界觀最優解,
   −55% DD、主題餓死)vs **「全動員」= AA-strict+B/A/D+機會階梯**(維持推薦——用戶
   自述風格 modern value/swing/隱藏敘事,正正係主題層遊戲)。
