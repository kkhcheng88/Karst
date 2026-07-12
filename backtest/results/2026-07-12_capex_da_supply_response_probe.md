# Result — Capex/D&A 比率作為 magnifier P2「供給紀律逆轉」機械化 tracker 探測

**Date:** 2026-07-12
**Script:** `backtest/experiments/exp_capex_da_probe.py`
**Tag:** 探測(probe)——**非接線決策**。目標:capex/D&A 比率夠唔夠 reproducible、夠唔夠歷史深度、
訊噪比夠唔夠好,值唔值得由「人手/敘事判斷」升級做排程機械化讀數(仿 `thesis/magnifier_staleness.py`
「機械化觸發、唔機械化判斷」嘅精神)。

> **本檔非訊號回測。** P2(`docs/2026-07-09_magnifier_model_plan.md` §3c:「輸家喺週期頂前做槓桿式
> 產能擴張」)而家淨係人手睇 case(例如 `thesis/wiki/memory-supercycle.md` 引 MU capex「2.66x」),
> 冇一個排程機制去計。呢個 probe 測嘅係:capex/D&A 呢個會計指標,做唔做得到嗰個機械化角色。

---

## 方法

1. 讀 `docs/2026-07-09_magnifier_model_plan.md` §3c + `backtest/results/2026-07-09_magnifier_case_library.md`
   (9 個超級週期 case 庫),搞清 P2 pattern 同 case list。
2. 數據源:defeatbeta 優先(repo 既有 Tier-1),yfinance 做 fallback。兩邊都探測深度,落一個誠實
   coverage table。
3. 核心測試:(a) MU 兩個週期(2016-18、2022-24)capex/D&A 喺週期頂點嘅表現,「2.66x」喺歷史分布邊度;
   (b) 15 個現存 themes 主 ticker 嘅 capex/D&A 今日快照,邊個 theme 供給側已經响閃 P2 警號;
   (c) 對文獻(asset growth anomaly、capital cycle 文獻)嘅方向/量級核對。
4. Mirror / increment / horizon(memory `validation-mirror-and-increment`):**呢個係描述性/水平
   快照 probe,唔係遠期回報回測**——mirror 唔係 cross-sectional IC(P2 而家用法係單一股票喺具名
   週期頂做質化死亡訊號,唔係排名全市場嘅 factor),所以冇做 IC/quintile 測試;increment = N/A(第一次
   喺呢個 repo 度計呢個指標,冇舊機械化版本好 increment);horizon = N/A(早期警號讀數,唔係遠期回報
   窗口測試)。**呢個 mirror 錯配本身就係下面判斷嘅其中一個重點警示**——文獻(asset growth anomaly)
   驗證嘅係 cross-sectional 排名 factor,唔係單一股票週期頂 timing 工具,兩者唔係同一件事。
5. 產物:`backtest/experiments/exp_capex_da_probe.py`(可重跑腳本)+ 本檔。

**兩個唔同指標,唔好混為一談**:
- **(1) capex/D&A 水平比率**——capex ÷ D&A(同期)。呢個先係任務原字面問嘅「capex-to-D&A 比率」。
  >1 = 淨產能擴張超過替換需要;≈1 = 只做維護性 capex。標準 capital cycle 指標。
- **(2) capex YoY 增長倍數**——`memory-supercycle.md` 引嘅「2.66x」其實係呢個(TTM 季度 2025-05-31
  $2.938B → 2026-05-31 $7.826B)。本檔已獨立用 defeatbeta 直接 API call 重現,**結果 2.664x,同
  wiki 一致**。

---

## 數據 coverage(誠實表)

| 來源 | 粒度 | MU 覆蓋窗 | 備註 |
|---|---|---|---|
| defeatbeta `quarterly_cash_flow()` | 季度 | 2022-05-31 ~ 2026-05-31(名義16季,實有13季——2022-08~2023-05 四季 D&A 被 `*` 遮蔽) | Tier-1,repo 既有主力源 |
| defeatbeta `annual_cash_flow()` | 年度 | 名義 FY2019-08-31~FY2025-08-31(7欄),但 FY2019/FY2020 兩欄 capex/D&A 全部 `*` 遮蔽,**實有 FY2021-FY2025(5年)** | Tier-1;呢個係本次 probe 新發現——之前 repo 冇腳本用過呢個 method |
| yfinance `quarterly_cashflow` | 季度 | 2025-02-28 ~ 2026-05-31(6季) | 比 defeatbeta 淺好多 |
| yfinance `cashflow`(annual) | 年度 | FY2021-08-31 ~ FY2025-08-31(5年) | 同 defeatbeta annual 實際覆蓋一致 |
| SEC 10-K MD&A(WebSearch 摘要,Tier-2) | 年度 | FY2016/17/18(手動補) | **唔係 live API 拉**,係 WebSearch 對 FY2018 10-K 原文嘅摘要,信度次於上面四個 |

**結論:MU 2016-18 週期喺 defeatbeta 同 yfinance 兩個 vendor、季度同年度兩種粒度,一律拉唔到。**
呢個係硬 data wall,唔係偷懶漏查——四種組合(defeatbeta-Q / defeatbeta-A / yfinance-Q / yfinance-A)
窗口起點全部卡喺 2019-2025 之間,冇一個穿透到 2016-18。用咗一次 WebSearch 對 SEC 10-K MD&A 段落嘅
摘要補呢三年,**明確標 Tier-2**(唔係本 agent 直接 parse XBRL/財表,係二手摘要,置信度較低但仍係
SEC 一手文件嘅內容)。

15-theme 快照:15/15 tickers 全部經 defeatbeta 成功拉到(**100% 覆蓋**,詳見下面表)。

---

## MU 兩週期讀數

### 2022-24 週期(Tier-1,defeatbeta 季度+年度)

季度(TTM as of 2026-05-31):capex=$25.260B,D&A=$9.011B,**capex/D&A(TTM)= 2.803x**。
單季最新讀數(2026-05-31 quarter alone,非 TTM):capex/D&A = **3.310x**——比 TTM 更極端。

| 期別 | capex($B) | D&A($B) | capex/D&A | capex YoY |
|---|---|---|---|---|
| 2022-05-31 | 2.578 | 1.821 | 1.416 | — |
| 2023-08-31 | 1.461 | 1.937 | 0.754 | — |
| 2023-11-30 | 1.796 | 1.915 | 0.938 | — |
| 2024-02-29 | 1.384 | 1.924 | 0.719 | — |
| 2024-05-31 | 2.086 | 1.955 | 1.067 | 0.809x |
| 2024-08-31 | 3.120 | 1.986 | 1.571 | 2.136x |
| 2024-11-30 | 3.206 | 2.030 | 1.579 | 1.785x |
| 2025-02-28 | 4.055 | 2.079 | 1.950 | 2.930x |
| 2025-05-31 | 2.938 | 2.094 | 1.403 | 1.408x |
| 2025-08-31 | 5.658 | 2.149 | 2.633 | 1.813x |
| 2025-11-30 | 5.389 | 2.212 | 2.436 | 1.681x |
| 2026-02-28 | 6.387 | 2.286 | 2.794 | 1.575x |
| **2026-05-31** | **7.826** | 2.364 | **3.310** | **2.664x**(=wiki「2.66x」) |

年度(FY2021-FY2025,defeatbeta annual,實有數):

| FY end | capex($B) | D&A($B) | capex/D&A |
|---|---|---|---|
| 2021-08-31 | 10.030 | 6.214 | 1.614 |
| 2022-08-31 | 12.067 | 7.116 | 1.696(週期頂,先於 2022-23 記憶體下行崩落) |
| 2023-08-31 | 7.676 | 7.756 | **0.990**(谷底——capex 跌到低過 D&A,教科書式資本紀律) |
| 2024-08-31 | 8.386 | 7.780 | 1.078 |
| 2025-08-31 | 15.857 | 8.352 | 1.899 |

**行為模式清楚而且乾淨**:FY2022 週期頂(1.696x)→ FY2023 資本紀律谷底(0.990x,capex 主動收縮到低過
折舊,經典下行週期底部特徵)→ FY2024 開始回升(1.078x)→ FY2025 AI 驅動急升(1.899x)→ **TTM
2026-05-31 進一步上衝到 2.803x、單季 3.310x**。呢條路徑(discipline at trough → re-acceleration
beyond prior peak)正正係文獻(capital cycle)講嘅供給紀律逆轉標準劇本,亦係 memory-supercycle.md
講嘅「教科書供給回應頂訊號」嘅量化底。

**分布/percentile 嘅誠實限制**:年度 8 點合併排序(FY16-18 Tier-2 + FY21-25 Tier-1):
0.990, 1.078, 1.225, 1.614, 1.679, 1.696, 1.899, 1.930——**FY2025 嘅 1.899x 唔係 8 年最高**,
FY2016 已經去到 1.930x。真正歷史性極端嘅唔係「年度水平」,而係**季度/TTM 嘅加速度**
(TTM 2.803x、單季 3.310x)——但因為冇 2016-18 嘅季度數據可比,呢個「加速度史無前例」嘅講法**冇同基準
可比較**,只能講「相對於 defeatbeta/yfinance 覆蓋到嘅 2022-2026 呢個窗口,係窗口內最高」,唔係「有記錄
以嚟最高」。呢個 caveat 必須明寫,唔可以誇大講「歷史性」。

### 2016-18 週期(Tier-2,SEC 10-K MD&A 摘要)

| FY end | capex($B,net of partner contrib.) | D&A($B) | capex/D&A |
|---|---|---|---|
| 2016-08-31 | 5.750 | 2.980 | 1.930 |
| 2017-08-31 | 4.730 | 3.861 | 1.225 |
| 2018-08-31 | 7.990 | 4.759 | 1.679 |

FY2018(供給端頂,隨後 2018Q4-2019 記憶體價崩)嘅 capex/D&A = 1.679x,同 FY2022 週期頂(1.696x)幾乎
一致——兩個週期喺「頂點」嘅年度水平比率驚人地相近(~1.7x),支持呢個指標喺 MU 身上有結構性重現性,
但亦提示**單純「絕對水平」門檻設得太低會兩個週期都唔會提早響——兩個週期嘅頂都係事後先睇到。**
呢個 caveat 對「值唔值得機械化」判斷好關鍵,下面詳談。

**caveat**:FY2016-18 嘅 capex 數字係「net of partner contributions」(10-K 原文口徑),defeatbeta
嘅口徑未必完全一致(冇獨立核實兩個口徑係咪同一basis)——呢三年數字用嚟做方向性參照(圖形形狀、大致
量級)冇問題,但唔應該同 Tier-1 defeatbeta 數字做逐位小數點嘅直接比較。

---

## 15-Theme 供給側快照

`thesis/themes.yaml` 15 個 theme,each 揀主 ticker,經 defeatbeta `quarterly_cash_flow()` TTM 拉
capex/D&A + capex YoY(以最新季 vs 4 季前比)。**覆蓋率 15/15 = 100%**(全部 defeatbeta,冇一個要
fallback 去 yfinance)。

| theme | ticker | capex/D&A(TTM) | capex YoY |
|---|---|---|---|
| space-satellite | RKLB | 3.080x | 0.944x |
| **memory-supercycle** | **MU** | **2.803x** | **2.664x** |
| **rare-earth-materials** | **MP** | **2.192x** | **2.540x** |
| specialty-siding-pricing-power | LPX | 1.946x | 0.953x |
| aerospace-specialty-alloys | ATI | 1.640x | 1.036x |
| advanced-packaging | AMKR | 1.592x | **2.811x** |
| euv-lithography-monopoly | ASML | 1.568x | 1.014x |
| ai-power-grid | GEV | 1.503x | 2.134x |
| glp1-biologics-packaging | WST | 1.457x | 0.599x |
| us-solar-manufacturing | FSLR | 1.418x | 0.575x |
| photonics-optical | COHR | 1.315x | 2.591x |
| semicap-equipment | AEHR | 1.293x | 0.045x |
| oil-gas-energy | EQT | 0.906x | 1.198x |
| gas-compression-equipment | USAC | 0.408x | 1.320x |
| tpu-custom-silicon | AVGO | 0.098x | 1.604x |

**Flag 規則**(粗略錨定 MU 自己而家嘅讀數:capex/D&A>2.0x 或 capex YoY>1.5x):7/15 theme 中招
(RKLB, MU, MP, AMKR, GEV, COHR, AVGO)。

**3 個最警號嘅 theme**(唔淨係揀單一指標最高嗰個,兩軸都極端 + 敘事吻合先算):
1. **MU(memory-supercycle)**——兩軸都極端(2.803x / 2.664x),而且已經有獨立 wiki 記錄同 LTA/SCA
   反敘事可以對照,係唯一一個「已知、已驗證」嘅 case。
2. **MP(rare-earth-materials)**——兩軸都極端(2.192x / 2.540x),之前冇被特別標記過,呢個 probe
   先發現。值得盡快人手覆核(稀土加工產能擴張,同中國供給/政策敘事高度相關,亦係
   `thesis/themes.yaml` header 講嘅「中國關聯名減信度」caveat 要留意嘅方向,雖然 MP 本身唔係
   中國實體)。
3. **AMKR(advanced-packaging)**——capex YoY **2.811x 係全表最高**(比 MU 仲高!),但水平比率
   只有 1.592x(未算極端)——呢個係「加速度先行、水平仲未追上」嘅早期形態,同 AI/CoWoS 先進封裝
   產能競賽敘事吻合,值得留意但未必即時係頂部訊號(可能仲喺爬升早段)。

**RKLB 嘅重要反例**:水平比率全表最高(3.080x)但 YoY<1(0.944x,即輕微倒退),呢個組合**唔係**典型
P2「加速惡化」訊號,反而似係年輕公司(仲喺建產能早期、折舊基數細)嘅結構性高比率——呢個突顯**純水平
門檻對年輕/高成長公司會誤報**,下面判斷會再講。

**AVGO 嘅重要反例**:capex/D&A 淨係 0.098x,近乎零。AVGO 喺 tpu-custom-silicon theme 係 fabless
設計商,真正嘅產能擴張發生喺代工夥伴(TSM 等)嘅資產負債表,唔喺 AVGO 自己度。呢個證明**呢個指標
淨係對「重資產、自己起廠」嘅價值鏈節點有意義,對 fabless/輕資產節點會讀出誤導性嘅低讀數**,揀 ticker
嗰步本身就要人手判斷邊個係「真正嘅供給側」。

---

## 文獻對照

已有文獻(`docs/2026-07-09_magnifier_literature.md`)本身就係 repo 之前做嘅 review,方向一致、量級
唔可靠(repo 政策已明寫):

- **Cooper, Gulen, Schill (2008)**,*JF* 63(4):asset growth = 最強嘅負向 cross-sectional return
  predictor(強過 B/M、size、momentum)。低 asset growth decile ~26%/yr vs 高 asset growth
  decile ~6%/yr(二手源,量級信度🟡;方向🟢)。
- **Titman, Wei, Xie (2004)**,*JFQA* 39(4):capex 大幅增加 → 顯著負向後續 benchmark-adjusted
  return,喺高 discretion(management 自由裁量大、無外部監督)公司更強。量級**明確不可靠**
  (二手源互相矛盾,2.65%~16.8%~(-4%~-7.5%)/yr 都有人引),repo 政策:只引方向,唔引具體 bps。
- **Fama-French (2015) 五因子模型**:CMA 因子將「低投資贏高投資」正式化做定價因子,CMA-HML 相關性
  ~0.7。
- **Novy-Marx (2011) 營運槓桿**:OL=(COGS+SG&A)/Total Assets,高 OL 贏低 OL 44bp/mo(VW)、
  51bp/mo(EW),對應 model plan feature #1。
- **Gu, Hackbarth, Johnson (2018)**:OL 只喺產能**唔靈活**(fab 呢類)公司先放大風險/回報——
  直接對應 MU 呢類重 capex 名。

**方向完全支持**:capex 加速(相對 D&A/資產基數)= 未來回報負向訊號,呢點文獻同呢個 probe 嘅 MU
case 吻合(FY2023 資本紀律谷底 → 隨後 MU 股價其實喺 2023-2024 反彈,但 memory-supercycle.md 嘅
敘事係「而家喺 2025-26 頂部區間再現同一形態」,即係話**指標本身喺歷史上冇被獨立驗證做「單一股票
週期頂 timing」工具,佢驗證嘅係「跨股票排名」用法**。

**mirror 錯配(最重要嘅誠實提醒)**:呢批文獻嘅驗證方法係:大型 cross-sectional 宇宙(數百至數千隻
股)、~1年遠期回報、equal/value-weight quintile spread。P2 而家嘅實際用法係:**單一具名股票、喺
具名週期頂點、質化死亡訊號**。兩者係唔同嘅任務——文獻證明「加速 capex 嘅股票平均嚟講跑輸」,唔等於
證明「capex/D&A 穿過某門檻就係嗰隻股嘅週期頂」。冇獨立文獻驗證過後者(single-name peak-timing)
呢個具體用法。

---

## 判斷:值唔值得升級做排程機械化 tracker?

**建議:唔升級做自動判斷/自動 kill trigger,但值得加做一個輕量「排程讀數 + 人手覆核」嘅
mechanized WATCH(唔係 mechanized JUDGE)。**

支持機械化(讀數層面)嘅理由:
- 數據可重現性好——defeatbeta 15/15 theme tickers 100% 命中,MU 「2.66x」獨立重現 exact match,
  腳本已存(`exp_capex_da_probe.py`),隨時可以排程重跑。
- MU 兩個週期(2022 頂 1.696x、2018 頂 1.679x)喺年度水平比率上高度一致,顯示指標喺呢隻股身上
  有真實結構性訊號,唔係雜訊。
- 15-theme 快照一次過揪出 MP、AMKR 兩個之前冇被特別點名嘅警號 theme——證明呢個指標有「掃描效率」
  價值,值得定期(例如月度)重跑做 radar,唔使逐個 theme 人手翻 10-K。

反對做**全自動判斷/kill 觸發**嘅理由(呢個先係真正 blocker):
1. **False-positive 結構性風險**——AVGO(fabless)讀數近零唔係因為冇風險,而係揀錯節點;RKLB
   (年輕、折舊基數細)讀數極高唔係因為週期頂,而係公司生命週期階段。呢兩個反例證明**揀邊個 ticker
   做「theme 代表」呢一步本身要人手判斷**,機械化唔到呢一步,而呢一步錯咗,後面個數就冇意義。
2. **Mirror 錯配**——文獻驗證嘅係 cross-sectional 排名,而家用法係單一股票 timing,兩者冇被同一
   份文獻驗證過;「門檻」(2.0x?1.5x YoY?)冇統計基礎,純粹係本 probe 用 MU 自己個讀數倒推嘅
   loosely-anchored 門檻,唔係外部驗證嘅 cutoff。
3. **年度水平比率喺兩個 MU 週期頂驚人咁接近(1.68-1.70x)**——如果將來拎呢個做「>X 就係頂」嘅硬
   門檻,兩次都要事後先知道啱唔啱(因為冇一個獨立、ex-ante 驗證過嘅門檻可以喺頂部發生**嗰刻**分辨
   出嚟同「仲會再升」)。單一 case 重現一致唔等於有效 timing 訊號——n=2 週期嘅樣本太細,唔可以
   宣稱呢個門檻有預測力。
4. **LTA/SCA 反敘事**(`memory-supercycle.md` 已記)——MU 而家嘅 capex 部分由 RPO ~$100B 嘅長約
   鎖定需求撐住,唔純粹係投機式超建。純比率指標睇唔到呢層,會對「有鎖定需求」嘅名產生假陽性死亡
   訊號。
5. **2016-18 週期數據本身要靠 Tier-2 WebSearch 補**——如果將來想做第三、第四個歷史 case 嘅同類
   驗證,好可能一樣撞到 vendor coverage 牆,擴充樣本嘅成本唔低。

**具體建議**(如果之後真係要落地):
- 將 `exp_capex_da_probe.py` 嘅 15-theme 快照部分,月度排程重跑,輸出淨係做**radar/watchlist**
  (邊個 theme 嘅比率/YoY 顯著上升),唔自動落 kill_condition 或改任何評分。
  呢個完全符合 `docs/2026-07-12_magnifier_scorecard_rubric.md` §11「評分留人手」嘅既定決定
  ——依個做法只係加多一個機械化「幾時要人再睇」嘅 trigger,唔取代人手判斷,同
  `thesis/magnifier_staleness.py` 嘅設計精神一致。
- 每次 radar 命中,人手必須額外檢查:(a) 呢隻股係咪真正嘅價值鏈重資產節點(唔係 fabless/輕資產
  代理),(b) 有冇 LTA/長約/政府補貼呢類「鎖定需求」反敘事,(c) 對比返自己公司歷史(唔淨係
  cross-name 比較)。
- 唔建議單獨用呢個指標做「加/減倉」嘅 quantitative gate;keep 佢做人手 case review 嘅其中一個
  排程輸入。

---

## 產物

- `backtest/experiments/exp_capex_da_probe.py`(可重跑;disk-cache 喺 `backtest/.insider_data/capex_da_probe.pkl`)
- 本檔:`backtest/results/2026-07-12_capex_da_supply_response_probe.md`
