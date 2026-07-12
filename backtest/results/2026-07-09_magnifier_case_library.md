# Result — 5x/10x 美股歷史 case 庫(Phase-3 magnifier 模型逆向工程樣本)

**Date:** 2026-07-09
**Script:** `backtest/experiments/exp_magnifier_case_library.py`(Leg B 價格篩)
**Tag:** raw sample library — **非最終模型**,係後續 case study 深挖嘅原始樣本;唔係訊號回測、冇 IC/alpha 判定

> **本檔非訊號回測。** 目標:建一個歷史 5x/10x 美股 case 庫,做 Phase-3「supercycle magnifier」
> 模型(邊啲股喺一個供需超級週期入面被非線性放大 5-10 倍)逆向工程嘅樣本。兩條腿:**腿 A** 人手/
> WebSearch 重建嘅超級週期地圖(贏家 + 輸家,避 survivorship);**腿 B** 程式化價格篩(補 breadth,
> 明寫 survivorship 限制)。

## Question

Phase-3 想學識分辨「邊個 setup 會被供需失衡非線性放大 5-10 倍」。要學呢件事,需要**兩邊嘅例子**——
淨睇贏家(FSLR/MU/NVDA)會令模型以為「supercycle敘事」本身就係訊號,睇唔到大部分「一樣睇落有supercycle
敘事」嘅 case 其實爆煲(LDK/Evergreen/DryShips/VeraSun/SPAC-EV)。所以呢個 case 庫刻意做 5-8 個週期
× 贏家+輸家對照,再用價格篩補完 breadth。

## Method

**腿 A(主,避 survivorship)**:人手 + WebSearch 重建 2000-2026 主要供需超級週期,每個週期列
**贏家(5x+)同輸家/爆煲(睇落似但死咗)**。覆蓋:dotcom 基建(1999)、中國商品+乾散貨航運
(2003-08)、油/乙醇(2004-08)、太陽能(2005-08 爆煲)、頁岩/壓裂砂(2010s)、記憶體(2017 & 2023-)、
EV/鋰(2020-21)、GLP-1(2023-)、鈾(2023-)、AI-compute/光通訊/電力(2023-)。三個委派 subagent
(WebSearch,無 code 執行權)分別覆蓋 3 個週期組;倍數/日期本 agent 用 `backtest/data.py` 同款
yfinance `download(period="max")` 直接算,唔靠估(方法見下)。

**腿 B(輔,補 breadth)**:掃 `backtest/.insider_data/sp500_px.pkl`(505 隻**現任** S&P 成份,
1994-2026)+ `px_defeatbeta.pkl`(6,769 隻 insider-Form4-active 廣度宇宙,2010-2026,細價股 tilt)。
方法:月底收盤,對每隻股逐月找「任何 24-42 個月窗(≈3 年,留少少彈性)入面 end/start ≥5x」,
起點限 2010-01~2024-12(見 `screen_5x.py`,已存入 `exp_magnifier_case_library.py`)。**明寫
survivorship 限制**:`sp500_px` = 現任成份,已經係「生還者」;`px_defeatbeta` 廣度好多但都係
insider-active(有 SEC Form 4)先入池,一樣有選擇偏誤,唔係完整歷史含已下市股嘅宇宙。

**倍數核實**:凡本 agent 引用嘅數字,一律用 yfinance `period="max"` 直接下載算(方法已存成
`exp_magnifier_case_library_verify.py`,可重現);少數 ticker(NKLA/LCID/CHPT/QS/SPCE/WKHS 部分
歷史段)出現**明顯 ticker-reuse / SPAC 合併前殼公司歷史污染**(舊代號被回收、reverse-split 或壞
tick),已於下面逐項標註,唔用受污染嘅原始數字、改用可核實嘅公開事實。subagent 純文字研究
(WebSearch)嘅數字保留「約/unverified」標記,未經本 agent 二次核實。

---

## 腿 A:超級週期地圖(贏家 + 輸家)

### 週期 1 — Dotcom 電信/互聯網基建(1998-2000 起漲,2000-02 爆煲)
主導樽頸敘事:「頻寬短缺」「fiber is the new oil」、互聯網流量每 100 日翻倍。

| ticker | 週期/主題 | 倍數(約) | 起漲期 | 類型 | 起漲前財務狀態 | ex-ante 可見特徵 | 結局 |
|---|---|---|---|---|---|---|---|
| QCOM | dotcom 基建/CDMA IP 授權 | ~28x | 1995-1998→2000-01-03 | secular-growth | 已盈利、細規模 | 按手機出貨量抽版稅,唔直接曝露資本開支;CDMA 採用未證實 | 爆煲期 -80%,未歸零;CDMA 後成真 3G 標準,長期仍係實業 |
| GLW(康寧) | 光纖電纜 | ~11x | 1999→2000 底 | cyclical-supercycle(被錯配當 dotcom) | 1997 盈利($462M)實高過 2000 頂($422M)—盈利冇撐住估值 | 「光纖=實體樽頸」敘事 | 見底 ~-99%(intraday-to-trough)、134年來首次停息、裁員 28%;未破產,十年後先部分收復 |
| JDSU | 光學元件(激光/放大器) | 約 15-20x+ | 1999-10→2000-07-26 | speculative-momentum/picks-and-shovels | 有真實收入增長但估值脫離可實現盈利 | 「唔理邊個贏網絡層都要用我哋嘅光學晶片」 | 崩至 <$2(>99%),未破產,後改名 Viavi Solutions 存活 |
| CIEN | 光網絡系統 | 約 15x+ | 1999→2000-10-20(高 $1,057 未拆股) | secular-growth | 客戶集中度薄(重度依賴 Qwest/WorldCom 等少數電信商) | DWDM 技術領先、電信商資本開支超級週期 | 2001-02 崩 >95%;存活至今,少數捱過嘅電信設備純play |
| JNPR | 核心互聯網路由器 | 約 7x | IPO 1999-06-25($34)→2000-10-16($243) | secular-growth/挑戰 Cisco | 收入細($673M by 2000)但估值巨 | 真技術差異化(專用路由矽 vs Cisco 通用架構),2001 前奪 Cisco 37% 核心路由器份額 | 崩 >90% 但存活,長年係 Cisco 真對手——「敘事方向啱、只係價貴」案例 |
| Foundry Networks(FDRY) | 以太網交換 | 約 8x | IPO 1999-09-28($25,首日+525%)→2000 初高 $212 | small-cap-story | IPO 時收入極細 | 以太網交換速度領先,互聯網骨幹擴容 | 崩至 $10.25(-95%)但存活,2008-12 被 Brocade 收購 ~$2.6B——體面退場,非爆煲 |
| Redback Networks | 邊緣路由/訂戶管理 | 約 8-9x | IPO 1999-05($23,首日+266%)→2000 高 $198 | speculative-meme/secular-growth 混合 | 未達規模收入嘅故事股 | 「寬頻用戶增長嘅網絡邊緣樽頸」 | **近全損**——2002-10 跌至 $0.27(>99.8%),2007 被 Ericsson 賤價收購——「殭屍生還者」實質係爆煲 |
| Sycamore Networks | 光交換(SONET) | 約 5-8x(拆股調整版本不一) | 1999-10→2000-02 初 | speculative-meme | **近乎零收入level嘅估值錯配之最**——$20B+ 市值 vs 1999 財年僅 $11.3M 銷售 | 除「下一代光交換」敘事外冇 | 未技術性破產,但業務從未跑通;2013 賤賣光帶寬業務僅 $18.75M,其後正式清盤 |

**輸家/爆煲(同期同敘事,實際歸零/破產)**

| ticker | 週期/主題 | 贏家期倍數 | 高點 | 類型 | ex-ante 睇落同贏家一樣嘅信號 | 死因/結局 |
|---|---|---|---|---|---|---|
| Nortel Networks | 電信設備 —— **同一 ticker 兩面嘅關鍵案例** | 見頂 $124.50(拆股後,市值 $400B,佔多倫多交易所 38%) | 2000-07-26 | cyclical-supercycle | 「電信商資本開支超級週期、市佔龍頭」——同 Ciena/JNPR 一樣嘅敘事 | 其後查出會計違規+無力適應競爭,2009-01-14 申請 Chapter 11,2009-12-30 見底 $0.23 —— **破產/歸零** |
| Global Crossing | 全球光纖骨幹 | 見頂 $61(市值 $47B) | 2000-02 | cyclical-supercycle | 「fiber is the new oil」全球產能圈地 | **從未有盈利年份**;2002-01-28 申請 Chapter 11($22.4B 資產 vs $12.4B 債),junk debt 融資嘅過度建設經典案例 |
| WorldCom | 電信骨幹/carrier | 見頂 $61.98-64.50(市值 $115B) | 1999-06 | cyclical-supercycle | 增長全靠併購(MCI 等)、毛利率不合理地穩定 | 1999-2002 造假 $38億+資產負債表、$110億虛構利潤;跌至 $0.08,2002-07-21 申請史上最大 Chapter 11(當時) |
| Lucent Technologies | 電信設備(AT&T 分拆) | 拆股前見頂 ~$84(市值 $258B) | 1999 尾 | cyclical-supercycle | 用「供應商融資」(借錢俾客戶買自己嘅設備)撐銷售數字 | 2000-02 失 ~95%,見底 $0.55;未破產但 2006 賤價併入 Alcatel(兩間傷兵合併) |
| Rhythms NetConnections | DSL 寬頻運營商(CLEC) | 峰值估值 ~$8.9B | 2000 | cyclical-supercycle | 「最後一哩寬頻短缺」樽頸敘事 | 資本密集、全靠持續 VC/債務輸血;2001-08-02 申請 Chapter 11(資產 $698.5M vs 負債 $847.2M) |
| Exodus Communications | 網絡代管/數據中心 | 峰值市值 ~$32B | 2000-03 | cyclical-supercycle | 「互聯網需要數據中心產能」 | 客戶主要係其他 dotcom(自身亦爆煲)= 二階過度建設;2001-09-26 申請 Chapter 11,股東**分毫不獲** |
| CMGI | 互聯網「孵化器」/風投控股 | 見頂 $160(市值 $41B,持 70+ 間互聯網公司股權) | 2000-01 | speculative-meme | 純粹「押注生態系統」嘅 meta-bet,零直接產品護城河 | 持股價值 3 個月內跌 96%($8B→$297M);未完全破產但淪為殼公司(後改名 ModusLink) |
| NorthPoint Communications | DSL CLEC | IPO 1999-05-05 $24 | 1999 | cyclical-supercycle | 同 Rhythms 一樣嘅「最後一哩」敘事 | 財報重列炸咗 Verizon $8億併購案,2001-01-16 申請 Chapter 11、其後轉 Chapter 7 全面清盤,資產賤賣俾 AT&T $135M |
| PMC-Sierra | 網絡/電信晶片 | ~$53 區間(約) | 1999-2000 | cyclical-supercycle | 同 JDSU 一樣嘅「picks-and-shovels」敘事 | 隨晶片設備業崩盤,存活但長期低迷,2016 被 Microsemi 收購——中度爆煲(非歸零) |

**Pattern(dotcom 組)**:敘事方向大致啱(頻寬需求確實增長),分野唔喺敘事,喺 **(1) 週期頂附近做
債務融資嘅產能/併購**(Global Crossing/WorldCom/Lucent vendor financing)、**(2) 多年物理供應回應
lag 喺當時已可見**(新路由器/光纖產能公告)、**(3) 護城河真假**(JNPR/CIEN 有真技術差異化 vs
Sycamore/Redback 純敘事、零規模收入)。「未正式破產」≠「未爆煲」——Redback/Sycamore/Lucent 都係
>90-99% 資本蒸發、包裝成收購/清盤嘅殭屍案例。

### 週期 2 — 中國商品超級週期(2003-2008):金屬/採礦/乾散貨航運/煤炭
主導樽頸敘事:中國城鎮化/基建需求跑贏全球礦山同航運產能;ex-ante 可見警號 = 新船訂單簿、
波羅的海乾散貨指數(BDI)、礦山資本開支公告。

| ticker | 週期/主題 | 倍數(約,一手 yfinance 核實) | 起漲期 | 類型 | 起漲前財務狀態 | ex-ante 可見特徵 | 結局 |
|---|---|---|---|---|---|---|---|
| FCX(Freeport-McMoRan) | 銅/金礦 | **7.86x**(一手:$8.005→$62.93) | 2003-03→2008-05-20 | cyclical-supercycle | 2001-02 銅價多年低位、財務近困境水平 | 中國電網/建築用銅需求 vs 全球礦山供給持平;新礦許可-建成滯後 7-10 年、公開可見 | 隨銅價崩(LME 銅 $3.61→$1.63/lb)跌 ~-70%,但存活至今、非爆煲 |
| SCCO(Southern Copper) | 銅礦 | 約 10.6x(2003-2008,subagent WebSearch,未經本 agent 二次核實) | 2003-2008 | cyclical-supercycle | 已盈利、低成本分位資產 | 同 FCX 需求敘事,但秘魯/墨西哥低成本資產給落後保護 | 2008-09 崩但存活,耐久贏家 |
| X(US Steel) | 整合型鋼鐵 | **19.53x**(一手:$9.83→$191.96,含 2008 高點) | 2003-03→2008-06-25 | cyclical-supercycle | 2003 前:亞洲金融危機後鋼鐵過剩、估值低殘 | 中國鋼鐵消費增速跑贏已公告新產能、進口替代建設 | 2008 年底崩 ~-69%,存活但十年未重返高點(2025 被日本製鐵收購,已非現任 S&P 成份) |
| CLF(Cliffs Natural Resources) | 鐵礦 | 約 6-8x+(subagent) | 2003-04→2008-06-30(高 $121.95) | cyclical-supercycle | 2003 前鐵礦係低估值商品業務 | 中國鋼廠鐵礦進口增速遠超海運供給,基準礦石合約價逐年大漲 | 隨 2008 GFC 崩,2014-15 鐵礦石二次崩盤(中國需求減速+力拓/淡水河谷擴產產能滯後兌現);存活(改名 Cleveland-Cliffs),**14.28x** 一手核實(2003-05→2006-01,$1.888→$26.962,較短窗) |
| NUE(Nucor) | 迷你鋼廠 | **5.72x**(一手:2003-04→2006-10,$10.212→$58.41) | 2003-2008 | cyclical-supercycle | 起漲前已盈利——本組「故事股」成分最低 | 內需鋼材產能利用率收緊、迷你鋼廠利潤率擴張 | 2009 急跌但從未近財務困境——本組「品質週期股」對照案例(vs 下面嘅船公司) |

**輸家/爆煲(乾散貨航運 = 供應回應超調嘅教科書案例)**

| ticker | 週期/主題 | 起漲倍數 | 高點 | 類型 | ex-ante 已可見嘅警號 | 死因/結局 |
|---|---|---|---|---|---|---|
| DryShips(DRYS) | 乾散貨航運 | 約 7x(IPO-to-peak)、對絕對高點計 50x+ | IPO 2005-01($18)→2007-10 收盤高 $123.50 | cyclical-supercycle/small-cap-story | 造船廠新船訂單簿 2005-08 持續膨脹(多年建造 lag 早已公開披露,市場照樣追價) | BDI 崩 94%(11,793→663,2008-05→12);其後連串攤薄增發 + 2016-17 八次合股(11.76M 股→1 股),股東損失 99.99% ——實質全損(非正式 Chapter 11,靠攤薄清零) |
| Genco Shipping(GNK) | 乾散貨航運 | 大倍數(峰值價未核實) | 2005-2008 | cyclical-supercycle | 自身 SEC 文件公開披露嘅新船訂造承諾——喺週期頂附近公開可見 | 「2008 衰退前買太多船」= 官方定調死因;2014-04-21 申請 Chapter 11(資產近 $3B vs 債 $1.5B),同年 7 月以削債 $1.2B 重組出關 |
| Eagle Bulk Shipping(EGLE) | 乾散貨航運 | 峰值 2008-05-16(價格數據不可靠) | 2008 | cyclical-supercycle | 2007 公告 35 艘新船訂造計劃(2012 先完工——供給喺爆煲後幾年先兌現,方向錯晒嘅完美案例) | debt-funded 新船計劃($1,188M 債);申請 Chapter 11(pre-packaged),債務由 $1,188M 重組至 $225M |
| Massey Energy(MEE) | 煤炭(冶金煤,中國鋼鐵驅動)—— 雙面案例 | 贏家期 ~5.7x(2003-05,$9.72→$34.95→高 $55+);2007 再漲 +54% 到 2008-08 收 $63.38 | 2003-2008 兩波 | cyclical-supercycle | 中國鋼鐵驅動嘅冶金煤需求 | 2008 單年 -61.4%;本身未破產——2011 被 Alpha Natural Resources 以 $8.5B 收購(近第二次冶金煤小高峰),**把債務炸彈轉交下家** |
| Alpha Natural Resources | 煤炭 | 見頂 ~$104.44 | 2008 | cyclical-supercycle | 2011 用槓桿收購 Massey——正值中國鋼鐵需求增速已見放緩、美國頁岩氣正取代國內動力煤 | 2015-07-16 單日跌 86% 至 $0.0344,2015-08-03 申請 Chapter 11 —— **破產** |
| Peabody Energy(BTU) | 煤炭 —— 雙面案例 | 市值峰值 ~$20B(2011,GFC 後第二波中國冶金煤小週期) | 2011 | cyclical-supercycle | 同 Alpha 一樣 2011 槓桿收購煤炭儲量,押注中國需求未兌現 | 2016-04-13 申請 Chapter 11 時市值僅 $34M(**-99.8%**);2017 削債 $5.2B 出關 |

**Pattern(中國商品組)**:同 dotcom 組一致——**債務融資嘅產能/併購時機卡喺週期頂附近**
(Genco/Eagle Bulk 新船訂造、Alpha 收購 Massey、Peabody 2011 儲量收購)係贏家變輸家嘅關鍵分野,
唔係需求敘事本身錯(中國確實工業化)。**多年物理供應回應 lag 喺當時已公開可見**(新船訂單簿、
BDI、礦山資本開支公告)但市場照樣追價到頂。低成本/多元化資產(SCCO 低成本銅礦、NUE 起漲前已
盈利、ADM 多元化——見週期 3)提供落後保護,純play/高槓桿(DryShips/VeraSun 類)冇。

### 週期 3 — 油價衝 $147/桶(2004-08)+ 玉米乙醇熱潮爆煲(平行案例)
主導樽頸敘事——油:OPEC 剩餘產能薄、「peak oil」、深水鑽探係邊際桶;乙醇:RFS(可再生燃料標準)
強制配額創造玉米乙醇嘅政府擔保需求底。

| ticker | 週期/主題 | 倍數(約) | 起漲期 | 類型 | 起漲前財務狀態 | ex-ante 可見特徵 | 結局 |
|---|---|---|---|---|---|---|---|
| RIG(Transocean) | 深水鑽探平台 | 約多倍(2003 基準未核實,峰值價格來源不一 $128-163) | 2003-2008-05-19 | cyclical-supercycle | 2000 年代初深水平台日租金低殘 | 深水平台供給實體受限(新船 3-5 年建造 lag),$100+/桶令原本不划算嘅深水項目變可行、結構性推高日租金 | 隨 2008-09 GFC 崩,2011 收復並創第二高峰;RIG 2014 後頁岩/油價戰進入*另一*長期衰退週期 |
| DO(Diamond Offshore) | 深水鑽探 | 盈利確認增長(2007 淨利 $846.5M vs 2006 $706.8M),股價倍數未核實 | 2003-2008 | cyclical-supercycle | 同 RIG 一樣嘅深水日租金動態 | 同 RIG | 2008-09 急跌,存活 |
| ADM(Archer-Daniels-Midland) | 農業/玉米加工,乙醇受益嘅大型多元化股 | 股價倍數未核實;基本面確認:2008 財年營運利潤紀錄 $3.4B(+$280M YoY),截至 2008-09-30 季度淨利 $1.05B(+138% YoY) | 2003-2008 | cyclical-supercycle/多元化大盤股(**非純play,呢個正正係佢存活嘅原因**) | 起漲前已係大型盈利企業 | RFS 強制配額創造政府擔保嘅玉米需求底——同殺死下面純play 嘅需求向量一樣,但 ADM 橫跨玉米加工/油籽/穀物貿易全鏈,唔淨係押乙醇價差 | 2008 Q4 乙醇分部利潤急跌(玉米成本飆+需求端價格轉弱)但整體仍穩健盈利——**同 VeraSun 嘅關鍵對照組:同一需求敘事,靠多元化+非槓桿单一商品價差存活** |
| CLR(Continental Resources) | Bakken 頁岩油 | IPO 2007-05-14 $15/股(市值 $2.5B)→2022 私有化價 $74.28/股(約 5x,忽略中間巨幅波動) | 2007-2022(長窗) | small-cap-story/secular-growth(早期頁岩技術敘事) | IPO 時細規模 | 真技術/地質優勢(2004 首度證明水平壓裂喺 Bakken 商業可行)而非純押油價 | **非爆煲**——長期贏家,2022 私有化收購 |

**輸家/爆煲(玉米乙醇 = 「輸入成本飆升 + 產能同步超建」雙重夾擊教科書案例)**

| ticker | 週期/主題 | 起漲特徵 | 類型 | ex-ante 睇落同贏家一樣嘅信號 | 死因/結局 |
|---|---|---|---|---|---|
| VeraSun Energy(VSE) | 玉米乙醇「純 play」產能龍頭 | IPO 2006-06-14,2007-08 連環併購(ASA Opco $405.6M、2008-04 US BioEnergy $756.9M,新增債 $525.1M)——**週期頂前最後、槓桿最重嘅一筆收購** | speculative small-cap-story | RFS 強制配額嘅需求敘事(同 ADM 一樣) | 用 OTC「accumulator」衍生品對沖玉米——結構性放大落後風險;2008 玉米價跌 63% 令對沖倒戈;2008-10-31 申請 Chapter 11(24 間子公司牽連),距 IPO 僅約 2 年 |
| Pacific Ethanol(PEIX) | 玉米乙醇(加州為主) | Bill Gates/Cascade Investment $84M 背書,股價一度近乎翻四倍,峰值約 $61.22(日期未完全核實) | small-cap-story | 同 RFS 需求敘事 + 「名人背書」誤當品質訊號 | 2008 Q1 淨虧 $35.2M(2007 同期 +$3.0M)、Q3 淨虧 $54.9M;現金耗盡、$250M 貸款違約,關閉 5 間廠中 3 間,2008-11 近乎破產(未正式 Chapter 11 但其後大幅攤薄重組,2021 改名 Alto Ingredients)——原股東近全損 |
| Aventine Renewable Energy(AVR) | 玉米乙醇 | IPO 2006-06-28 $43/股,籌 $389.5M;**IPO 首日已跌 11% 至 $38.37**——週期頂附近已有 ex-ante 紅旗 | speculative/small-cap-story | 同 RFS 需求敘事 | 2007 能源法案(EISA)幾乎令乙醇強制用量翻倍(2007/08 作物年度玉米消耗約 24% 流向乙醇)、2006 年底在建產能足以令全國產量翻倍——需求+產能同步超建;2009-04-08 申請 Chapter 11,2010-03-16 出關,IPO 後不足 3 年 |
| Chesapeake Energy(CHK) | 天然氣/頁岩 —— **同一公司兩個超級週期兩種結局嘅最佳案例** | 贏家期:2000-01 近乎零基數 → 2008-07 高位 $70+(未拆股口徑,約 50-70x+,本組最大倍數之一) | secular-growth/頁岩先驅(水平壓裂+圈地先於同業) | 真.前瞻嘅頁岩地塊圈地(同 CLR 一樣嘅技術浪潮) | 2008 氣價崩潰重挫、部分收復,其後 2010 年代第二輪槓桿式頁岩鑽探,2020 年油氣價崩盤下**2020-06 申請 Chapter 11**——同 Alpha Natural Resources、乾散貨船公司一模一樣嘅「週期頂加槓桿」劇本,十二年後、換咗商品,重演一次 |

**Pattern(油/乙醇組)**:同前兩組一致收斂——**需求敘事(RFS 配額、$147 油價)喺三個 case 都方向啱**,
死因始終係 **(1) 週期頂前嘅槓桿式併購/擴產**(VeraSun 收購 US BioEnergy、CHK 第二輪頁岩槓桿)、
**(2) 純 play 冇多元化緩衝**(VeraSun/Pacific Ethanol/Aventine 對比 ADM 全鏈多元化)、**(3) 對沖
結構反而放大落後風險**(VeraSun accumulator)。CLR/CHK(首輪)證明「真技術優勢先於同業」可以係
持久贏家嘅 ex-ante 分野,但 CHK 自己十二年後用同一劇本(槓桿頂部加倉)證明呢個優勢唔係永久保護傘。

### 週期 4 — EV/鋰超級週期見頂回落(2020-21 高峰、2022-24 崩)+ SPAC-EV 泡沫(平行、可對照)
主導樽頸敘事:鋰/電池金屬供給短缺 vs EV 滲透率 S 曲線;同期一整浪 pre-revenue SPAC EV 殼股。

| ticker | 週期/主題 | 倍數(一手核實/約) | 起漲期 | 類型 | 起漲前財務狀態 | ex-ante 可見特徵 | 結局 |
|---|---|---|---|---|---|---|---|
| ALB(Albemarle) | 鋰生產商 —— **雙面案例** | **4.99x 一手**(2020-03→2023-01,$56.37→$281.45);subagent:ATH $313-335(2022-11) | 2020-03→2022-11 | cyclical-supercycle | 已盈利特化化工商,鋰僅其中一個分部,起漲前產能利用率低 | 碳酸鋰合約/現貨價 2022 年 YoY +225-250%,可觀察嘅輸入價訊號 | 隨中國鋰現貨崩(2023 H2 ~$25/kg→2024 $12-15/kg→2025-06 $8,259/噸)跌 -7.8%(2022)/-32.1%(2023)/-40.5%(2024);2026 部分收復,52週 $64.95-$221 |
| LTHM(Livent) | 鋰生產商 | **8.4x**(subagent 核實:$4.19 2020-03-23→$35.05 2022-09-14) | 2020-03→2022-09 | cyclical-supercycle | 細型鋰生產商,起漲前薄利潤 | 同 ALB 合約價訊號 | 2024-01 同 Allkem 合併做 Arcadium Lithium(2024-02-12 LTHM 除牌),2025 被 Rio Tinto 現金收購 $5.85/股(較 2024-10 收盤 $3.08 溢價 90%,但**較 2022 峰值 $35.05 仍跌 ~83%**)——併購退場,非破產,但泡沫估值從未收復 |
| SGML(Sigma Lithium) | 鋰開發/生產商(巴西) | **38.02x 一手窗**(2020-04→2023-06,$1.06→$40.30);ATH **$43.18** 核實(2023-06-13) | 2020-04→2023-06 | cyclical-supercycle/small-cap-story | 早期階段生產商,**喺鋰價已過頂後先上市**(TSXV→Nasdaq 2023 uplisting)——時機本身係紅旗 | 同鋰價訊號,但上市時機接近週期頂 | 現價約 $12.80(較 ATH -70%);未爆煲、2025-26 仍有盈利(61% 毛利率)——「大幅回吐但存活」對照案例 |
| SLI(Standard Lithium) | 鋰開發商(阿肯色鹵水,pre-revenue) | **38.7x**(subagent:$0.32 2020-03-18→$12.37 2021-10-27) | 2020-03→2021-10 | cyclical-supercycle/small-cap-story | pre-revenue、細價股基數(2020-12 增發價 $2.20) | 同鋰價敘事 + DoE 貸款猜測;極端倍數主要反映起點太細而非基本面 | 大幅回吐,52週 $2.18-$6.40(較 2021 峰值 -50~80%) |
| PLL(Piedmont Lithium) | 鋰開發商 | 約 13x(subagent,未完全核實:ADS $6.30 2020-06→約 $83-88 2022) | 2020-06→2022 | small-cap-story | pre-revenue 鋰開發商(Carolina/Ghana/Quebec 項目) | 鋰合約價 + 項目許可期權敘事 | 崩 -85~90%,2025-08 同 Sayona Mining 合併做 Elevra Lithium、PLL 除牌(**存續但近全損**,一手核實:除牌前確認) |

**輸家/爆煲(SPAC-EV 群 —— speculative-meme,非供給樽頸案例,明確標註同「真週期股」機制唔同)**

| ticker | 週期/主題 | 起漲特徵 | 類型 | 死因/結局 |
|---|---|---|---|---|
| NKLA(Nikola) | EV/氫能貨車 | SPAC 合併(VectorIQ)2020-06-03 完成,數日內衝 $93.99(較 $10 信託淨值約 9.4x),一度市值超福特 | **speculative-meme**(零收入、零產車) | Hindenburg Research 2020-09 指「氫能貨車下坡示範片係假」;股價崩 >99%,2025-02-19 申請 Chapter 11、2025-02-26 除牌,法院監督清盤,資產賣俾 Lucid |
| QS(QuantumScape) | 固態電池技術(pre-revenue) | SPAC 合併(Kensington)2020-11-25 完成,ATH **$132.73**(2020-12-22,約 13.3x 較 $10 信託淨值)——**一手核實為真實數字,非污染數據** | **speculative-meme**(技術承諾,2026 仍未有商業化產品) | 崩 -97%,ATL $3.40(2025-04-08);未破產,現價約 $6.90——「殭屍生還者」5 年後仍 pre-commercial |
| RIDE(Lordstown Motors) | EV 皮卡(Endurance) | SPAC 合併(DiamondPeak)2020-10 完成,峰值市值 ~$5B(零產量) | speculative-meme | Hindenburg 報告(2021-03-12)指預訂單造假,距峰值僅 2 個月;2023-06-27 申請 Chapter 11,轉殼「Nu Ride」訴訟載體 |
| GOEV(Canoo) | EV 多用途送貨車 | SPAC 合併(Hennessy IV)2020-12 完成 | speculative-meme | 多次反向合股(1:25、1:400)後仍近零;2025-01-17 申請 **Chapter 7 全面清盤**(非重組) |
| FSR(Fisker Inc.) | EV(Ocean SUV) | SPAC 合併(Spartan Energy)2020-10 完成,峰值 ~$28.50(2021-02) | speculative-meme(有出貨但品質/軟件問題嚴重) | 2023-24 連環召回/NHTSA 調查已係 ex-ante 紅旗;2024-06-17 申請 Chapter 11,法院確認清盤方案、股權清零 |
| CHPT(ChargePoint) | EV 充電基建 | SPAC 合併(Switchback)2021-02-26 完成,峰值高 $40 區間(2021 初) | speculative-meme/small-cap-story(有真實但持續蝕錢嘅收入) | 2024 年 1:25 反向合股避退市;現價換算前峰值 -99%+——另一「殭屍生還者」 |
| Romeo Power(→併入 NKLA) | EV 電池包 | SPAC 合併 2020-12/2021-01 完成 | speculative-meme | 2022 Q1 已現「持續經營」警示;2022-08-01 以 Nikola SPAC 估值嘅 11% 被收購(收盤價 $0.55)——賤賣、非清潔破產,買家 Nikola 本身 2025 亦破產 |
| Lion Electric(LEV) | EV 貨車/校巴(加拿大) | SPAC 合併(Northern Genesis)2021-05 完成 | speculative-meme(依賴補貼車隊訂單) | 2024-12-18 因信貸協議違約申請破產保護(CCAA),NYSE/TSX 停牌 |

**Pattern(EV/鋰組)**:**鋰生產商(ALB/LTHM/SGML/SLI/PLL)係真.供給樽頸案例**——合約/現貨價係
可觀察嘅 ex-ante 訊號,贏家輸家分野喺「上市/擴產時機是否貼近週期頂」(SGML 喺鋰價已過頂先
uplist、PLL 2022 高追);**SPAC-EV 群(NKLA/QS/RIDE/GOEV/FSR/Romeo/CHPT/LEV)完全唔同機制**——
零收入、零綁定供給約束,純粹 SPAC 上市溢價 + 敘事投機,ex-ante 已有可見紅旗(Hindenburg 報告、
NHTSA 調查、信貸違約)但集資容易掩蓋。「未正式破產」(QS/CHPT)= 殭屍生還者,同樣要當輸家計。

### 週期 5 — GLP-1 減肥藥熱潮(2023-2025)
主導樽頸敘事:GLP-1 需求跑贏製造產能(注射筆、灌裝、API 合成);另一條平行線係細價股單一
binary 臨床數據投機。

| ticker | 週期/主題 | 倍數(一手核實/約) | 起漲期 | 類型 | ex-ante 可見特徵 | 結局 |
|---|---|---|---|---|---|---|
| LLY(Eli Lilly) | GLP-1 製造產能超級週期 | **5.99x 一手**(2020-10→2024-04,$130.46→$781.10) | 2020-10→2024-04(仍未見頂) | cyclical-supercycle(真製造樽頸:注射筆/灌裝/API) | 公開披露嘅產能擴建資本開支、FDA 藥物短缺清單上 Mounjaro/Zepbound 缺貨通知——可觀察樽頸 | **仍在創新高**——ATH $972(2024-08)→新 ATH $1,229.93(2026-06-29,subagent);大型股「supercycle 都未必單次乾淨 5x」假說**部分成立**(呢個 case 反而清晰過 5x 但持續數年、非單次爆) |
| NVO(Novo Nordisk) | GLP-1 製造產能超級週期 —— **雙面案例** | **4.23x 一手**(2021-03→2024-06,$33.71→$142.74,ATH $146.91) | 2021-03→2024-06-25 | cyclical-supercycle,同 LLY 機制 | 同缺貨訊號,但**同時已可見輸俾禮來 tirzepatide 上市嘅市佔風險** | 見頂即崩:2024-12-20 CagriSema 數據不及預期單日 -20%,2026-02-23 REDEFINE 4 失敗再 -16%,較 ATH **-56%**;高盛下修 CagriSema 峰值銷售估計 ~65%;現價 $35-72 區間——**贏家變輸家嘅乾淨案例,同 ALB 手法一致** |
| VKTX(Viking Therapeutics) | GLP-1 肥胖症、細價股單一數據事件 | 約 4x(單一催化劑,非多年趨勢) | 2024-02→2024-03-06(峰值 $96.96) | **small-cap-story/speculative**(binary Phase 2 讀數,明確唔同於 LLY/NVO 嘅製造樽頸機制) | 單一 Phase 2 VENTURE 數據(最多 14.7% 體重下降)——除持貨等數據外無法 front-run | 由 2024-03 峰值回吐,但 2025-26 仍有後續 Phase 2/3 進展、未清零 |
| GPCR(Structure Therapeutics) | 口服 GLP-1、細價股數據事件 | 約 4x(未完全核實) | IPO 2023-02($23)→52週高 $94.90(日期未確認) | small-cap-story/speculative | 同 VKTX 機制,單一候選藥(GSBR-1290)binary 讀數 | 回吐至約 $39,未維持峰值 |
| HIMS(Hims & Hers) | GLP-1 代配藥電訊醫療套利 | **16.38x 一手**(insider_broad 篩,2022-05→2025-07,$4.04→$66.18);subagent ATL-ATH 口徑 26.8x($2.72→$72.98) | 2022-05→2025-07 | **應歸類 speculative/regulatory-arbitrage,唔係真供給樽頸——商業模式建基於 FDA 藥物短缺觸發嘅「配藥」豁免,規管上明擺住可逆轉** | ex-ante 紅旗清晰可見:豁免條款本身有時限、可逆 | 2025-06-23 Novo Nordisk 終止合作 + 指控違規推廣配藥 Wegovy,單日 -34%;2026-02 三連擊(FDA「非法仿製」警告 2-07、Novo 專利訴訟 2-09、FDA GLP-1 API 限制通知 2-18);2026 年初至今 -50%+——**「監管套利爆煲扮成供給樽頸贏家」教科書案例,排除喺 magnifier 核心分類外並註明原因** |

**Pattern(GLP-1 組)**:大型股(LLY/NVO)= 真製造樽頸,但**分野唔喺樽頸真假**(兩者都真)、
**喺第二階段競爭動態**——NVO 輸俾禮來上市節奏 = 贏家變輸家;細價股(VKTX/GPCR)= 單一 binary
臨床事件投機,同「供給樽頸」機制完全唔同、不應同一個籃子讀;HIMS 睇落好似「供給緊張受益者」
但實質係監管套利(豁免可逆),同真樽頸案例分開處理。

### 週期 6 — 鈾牛市(2023-2025,2026 仍在延續;歷史上其實已係第三次鈾週期)
主導樽頸敘事:福島後十年礦業投資不足、電力公司補庫存合約週期、AI 用電需求帶動核電復興、
Sprott Physical Uranium Trust(2021-07 上市)持續喺現貨市場買物理鈾——**呢個係少數 ex-ante
真.可觀察樽頸訊號**(Sprott 持倉/買入活動公開即時披露,唔似 SPAC 純敘事)。

| ticker | 週期/主題 | 倍數(一手核實) | 起漲期 | 類型 | 結局 |
|---|---|---|---|---|---|
| CCJ(Cameco) | 鈾生產商 —— **首次鈾週期(2003-07)一手核實** | **13.73x**(2002-09→2006-01,$2.88→$39.54) | 2002-09→2006-01 | cyclical-supercycle | **鈾係重覆出現嘅週期,非一次性**——同一 ticker 2020-2026 第二輪(subagent:累計約 5-7x,2020 COVID 底→2026-01-28 新 ATH $134.09)仍未見頂,「已喺 2024 見頂」讀法**錯**(mid-2026 仍破頂) |
| NXE(NexGen Energy) | 鈾開發商(Rook I,Athabasca) | **12.13x 一手**(2014-01→2017-02,$0.237→$2.874,Arrow 礦床發現驅動) | 2014-01→2017-02 | cyclical-supercycle | 呢個窗係**公司特定發現驅動**,非板塊性訊號;2020-2026 第二輪(subagent:base~$1.30→ATH $13.92,2026-01-28)約 10x+,兩種 ex-ante 訊號類型(發現 vs 板塊補庫存)要分開讀 |
| UEC(Uranium Energy Corp) | 鈾生產/開發商(美國 ISR) | **25.93x 一手**(2008-11→2010-11,$0.27→$7.00,GFC 後迷你復甦) | 2008-11→2010-11 | cyclical-supercycle | 呢個係 2011 福島事故**前**嘅迷你週期(其後十年鈾價陰乾);2020-2026(subagent 累計 10x+)係第三輪 |
| DNN(Denison Mines) | 鈾開發商(Wheeler River) | **6.6x 一手**(2020-03→2023-09,$0.25→$1.65)——本輪(2023-)清晰命中 5x 門檻 | 2020-03→2023-09 | cyclical-supercycle | 仍屬 developer 階段,subagent:2022 曾回吐 -23.8% | 
| LEU(Centrus Energy) | 鈾濃縮(HALEU,美國本土) | **33.53x 一手**(2018-12→2021-10,$1.69→$56.67) | 2018-12→2021-10 | cyclical-supercycle(角度獨特:濃縮產能/HALEU,非採礦) | 2014 曾破產重組出關嘅公司,起漲前細價股/薄成交量;政策驅動(俄羅斯濃縮鈾制裁後嘅美國本土供給安全)係獨立於採礦供給嘅樽頸類型 |
| URG(Ur-Energy) | 鈾生產商(懷俄明 ISR) | **6.37x 一手**(2008-11→2011-01,$0.51→$3.25)——**呢個亦係 2008-11 舊週期,2023- 本輪 subagent 只錄得約 2x(未達 5x 門檻)** | 2008-11→2011-01 | cyclical-supercycle | **負面對照**:唔係每隻鈾股本輪都命中 5x,URG 本輪較溫和 |
| UUUU(Energy Fuels) | 鈾生產商 | **11.73x 一手**(2008-11→2011-01,$5.50→$64.50,同上舊週期) | 2008-11→2011-01 | cyclical-supercycle | 本輪(2023-)倍數未核實,待補 |
| UROY(Uranium Royalty Corp) | 鈾版稅/streaming | **2.53x 一手(未達 5x)** | 2023-05→2025-10 | cyclical-supercycle | ATH $5.78(2021-10-20)→ATL $1.47(2025-04-08);版稅模式理論上減開發風險,但**未減價格波動**——負面對照,「安全結構」唔自動帶嚟 outperformance |
| MP(MP Materials) | 稀土(非鈾但同源政策驅動) | **4.62x 一手**(2024-03→2026-04,$14.30→$66.04),生涯 10.1x(2020 IPO 底起) | 2024-03→2026-04 | cyclical-supercycle,event-driven(見 `thesis/wiki/rare-earth-materials.md`,confidence 0.28) | 未清晰命中 5x 門檻(接近);已入 thesis 追蹤 |

**Pattern(鈾組)**:**鈾唔係一次性 2023 主題,係第三次歷史週期**(2003-07 / 2008-11 / 2020-26 至今
仍未見頂)——每次都有真.可觀察樽頸訊號(合約補庫存、Sprott 物理買盤),但**個股表現分化大**
(CCJ/NXE/UEC/DNN/LEU 本輪或前一輪清晰 5x+,URG/UUUU 本輪較溫、UROY 版稅結構完全冇跑贏)。
公司特定催化劑(NXE 發現、LEU 政策)vs 板塊性補庫存訊號係兩種唔同嘅 ex-ante 訊號類型,唔應該
混為一談。

### 週期 7 — AI-compute / 記憶體(2023-)/ 光通訊 / AI 電力基建(2023-,本 repo thesis 層已有深度研究)
主導樽頸敘事:AI 訓練/推論算力需求 vs 記憶體(HBM/DRAM/NAND)、光互連(InP 雷射交期 32 個月)、
資料中心電力(變壓器/發電/SiC 功率半導體)三條實體樽頸鏈同時繃緊。本週期 repo 已有一手估值/資本
開支驗證(`thesis/wiki/memory-supercycle.md`、`photonics-optical.md`、`ai-power-grid.md`、
`advanced-packaging.md`,2026-07-01/08 defeatbeta 一手拉),下表只補**價格倍數 + 贏輸對照**,唔重複
KPI 推導。

| ticker | 鏈 | 倍數(一手核實) | 起漲期 | 類型 | 一手佐證(見對應 wiki) | 結局(截至 2026-07) |
|---|---|---|---|---|---|---|
| MU(Micron) | 記憶體核心(DRAM+HBM+NAND) | **23.1x**(2022-12→2026-06,$49.98→$1,154.29) | 2022-12→2026-06(仍在頂) | cyclical-supercycle | capex 一年 **2.66x**($2.94B→$7.83B)= 教科書供給回應頂訊號;ttm_pe 67 分位(memory-supercycle.md) | 仍在高位,晚期但 LTA/RPO(~$1,000億)墊高地板;SK 海力士 ADR $294億上市(2026-07-10)本身係擁擠訊號 |
| SNDK(SanDisk,WDC 分拆) | NAND-CMX 純押 | **78.8x 生涯**(2025-04-22→2026-06-25,$29.62→$2,335;<2 年,唔喺 24-42 月窗口內、更極端) | 2025-02 分拆起→2026-06 | cyclical-supercycle | RPO $41.6B、ttm_pe 97 分位(史短不可靠) | 本 case 庫**單一最極端倍數**——分拆後 14 個月 78.8x,佐證記憶體週期非線性放大嘅上限有幾誇張 |
| WDC(Western Digital) | NAND/HDD 鄰接 | **26.78x**(2022-12→2026-06,$23.85→$638.72) | 2022-12→2026-06 | cyclical-supercycle | ttm_pe 82 分位 | 仍在高位 |
| LITE(Lumentum) | 光通訊雷射 IDM | **23.01x**(2023-10→2026-04,$39.21→$902.32) | 2023-10→2026-04 | cyclical-supercycle | ttm_pe 75 分位、NVDA $2B 首押鎖產能(photonics-optical.md) | 仍在高位;CPO 延後對龍頭「唔痛」(可插拔+EML 訂單撐住) |
| COHR(Coherent) | 光通訊雷射 IDM 最深護城河 | **13.33x**(2023-10→2026-06,$29.60→$394.47) | 2023-10→2026-06 | cyclical-supercycle | **ttm_pe 98 分位(全批最貴)**、capex 2.6x、預付 $22.28M 鎖 3 年 6 吋 InP | 仍在高位但估值極端 |
| AXTI(AXT Inc) | 光通訊上游 InP 基板咽喉 | **51.84x**(2023-10→2026-05,$1.99→$103.16) | 2023-10→2026-05 | small-cap-story(咽喉真,但 wiki #141 已修正:「唯一便宜」係盈利觸頂尾隨假象) | 6 吋良率僅 15-20%,COHR 排隊都要靠佢 | wiki 已提示 CPO 延後單日殺 -13%,擁擠開始消風 |
| CRDO(Credo) | 機架內銅/retimer(CPO 延後受惠) | **33.53x**(2023-04→2026-06,$8.11→$271.95) | 2023-04→2026-06 | cyclical-supercycle | CPO 延後多活一年、反受惠(photonics-optical.md #143) | 仍在高位 |
| CLS(Celestica) | AI 伺服器組裝代工 | **40.96x**(2022-09→2025-10,$8.41→$344.48) | 2022-09→2025-10 | cyclical-supercycle(代工/鏟子型) | — | 未入 thesis universe,值得補 |
| VRT(Vertiv) | 資料中心冷卻/電力管理 | **26.22x**(2022-09→2026-02,$9.72→$254.89) | 2022-09→2026-02 | cyclical-supercycle | ai-power-grid.md 追蹤名單 | 仍在高位 |
| GEV(GE Vernova) | 發電/電網設備(2024 分拆) | **7.64x**(2024-04→2026-06,$153.71→$1,174.86) | 2024-04→2026-06 | cyclical-supercycle | Homer City 級詢價、GEV CEO 訂單步伐訊號(ai-power-grid.md) | 仍在高位 |
| BE(Bloom Energy) | 燃料電池(behind-the-meter 電力) | **34.52x**(2024-02→2026-06,$8.77→$302.70) | 2024-02→2026-06 | cyclical-supercycle,pre-earnings(ai-power-grid.md kill_condition 已點名) | ttm_pe 91 分位 | 仍在高位但估值極端、屬 wiki 明確警告嘅「pre-earnings 名字」 |
| KLAC / LRCX | 半導體設備(先進封裝/HBM 供應鏈) | KLAC **8.0x**、LRCX **10.31x**(均 2022-12→2026-06) | 2022-12→2026-06 | cyclical-supercycle | advanced-packaging.md:ttm_pe 90-96 分位 | 仍在高位、估值已反映 |
| SMCI(Super Micro) | AI 伺服器 —— **同一 ticker 贏輸兩面案例** | 見頂 **44.46x**(2020-10→2024-03,$2.27→$101.00 monthly 口徑;daily 口徑 2024-03-13 高 $118.807) | 2020-10→2024-03 | cyclical-supercycle → **會計醜聞爆煲** | AI 伺服器需求真實(同 CLS/VRT 同鏈) | **一手核實崩 -85%**($118.807→$18.01,2024-03-13→2024-11-14)——會計違規/延交 10-K/退市威脅(Hindenburg 2024-08);需求敘事無錯,治理/造假係死因,同 dotcom 組 WorldCom 手法一致 |
| WOLF(Wolfspeed,前稱 Cree) | SiC 功率半導體(AI/EV 電力鏈,ai-power-grid.md 追蹤名單)—— **輸家案例,驗證 wiki kill_condition** | ATH **$141.87**(2021-11-16,WebSearch 核實,由 SiC/EV 電力敘事驅動) | 2021 尾見頂 | cyclical-supercycle → 破產重組 | 2021:「SiC 純 play」敘事同 BE/NVTS 一樣嘅 pre-earnings 估值溢價 | 2025-06-30 申請 **Chapter 11**,2025-09 底出關:**舊股東按 0.008352 比例換新股**(即 1,000 股舊股換 8.35 股新股,實質全損),舊股東喺重組後公司僅持 3-5% 股權;新股 2025-09-29 掛牌起 $22.10、現價 ~$35-44——**同 wiki ai-power-grid.md 2026-07-01 寫低嘅 kill_condition「pre-earnings 名字(BE/NVTS/WOLF)崩」完全兌現** |
| QBTS/RGTI/IONQ/SOUN/BBAI | 量子運算/AI 軟件投機群 | QBTS 74.57x、**RGTI 94.19x**、IONQ 20.89x、SOUN 15.5x、BBAI 10.27x(全部一手核實) | 2022-2023→2025-2026 | **speculative-meme/small-cap-story**(binary 敘事,非供給樽頸) | 冇對應 wiki(未入 thesis universe) | 全部已由高位回吐 **-45% 至 -74%**(RGTI -70%、QBTS 仍需核實、IONQ -45%、SOUN -72%、BBAI -74%)——同 GLP-1 組 VKTX/GPCR 手法一致嘅「binary/敘事投機」類別,唔屬 cyclical-supercycle |
| WULF/CIFR/IREN/APLD | 比特幣礦工 → AI/HPC 主機代管轉型 | WULF 39.94x、CIFR 43.75x、IREN 50.83x、APLD 33.01x(全部一手核實) | 2022-2023→2025-2026 | cyclical-supercycle(電力/散熱基建同 AI-power-grid 樽頸同源,「第二人生」轉型故事) | — | IREN/CIFR 已由高位回吐 -25~44%,WULF/APLD 未核實回吐幅度;基建轉型敘事真,但估值已反映轉型預期 |
| PLTR(Palantir) | AI 軟件平台 | 31.23x(2022-12→2025-10,$6.42→$200.47) | 2022-12→2025-10 | **secular-growth,非供給樽頸——排除喺 magnifier 核心分類外**(政府合約/平台網絡效應,唔係實體供給約束) | — | 仍在高位,note only |
| NVDA | AI 算力需求錨 | 16.68x(2022-09→2025-10) | 2022-09→2025-10 | **secular-growth,排除**(下游需求方,非供給樽頸表達) | 全部 wiki 明確排除 NVDA 做 thesis 表達 | 仍在高位,note only |

**Pattern(AI-compute 組)**:呢個週期**同時有全部四種模式**——(1)真.供給樽頸(MU/SNDK/LITE/COHR/AXTI,
一手 capex/ttm_pe 已證);(2)贏家變輸家(SMCI 會計醜聞、WOLF 破產——**兩個都直接驗證咗 repo thesis
wiki 寫低嘅 kill_condition**,唔係事後孔明);(3)speculative-meme 投機群(QBTS/RGTI/IONQ/SOUN/BBAI,
binary/敘事、非樽頸);(4)secular-growth 排除項(NVDA/PLTR,下游需求方或平台效應,非供給約束
表達)。SMCI 同 WOLF 兩個 case 特別有價值——證明 repo 而家寫緊嘅 thesis wiki(memory-supercycle/
photonics-optical/ai-power-grid confidence 0.30-0.38、kill_condition 已預先寫低)**本身就係一個
可驗證嘅 ex-ante 框架**,唔止事後解釋。

### 週期 7a — 記憶體歷史先例:2016 DRAM/NAND 上升週期 + 2018-19 崩(MU 而家嘅劇本 8 年前已演過一次)
主導樽頸敘事:三寡頭(三星/SK 海力士/美光)2015 下行週期後嘅 capex 紀律 + 智能手機/雲/早期挖礦
需求。呢個係週期 7(2023- AI/HBM)嘅**直接歷史先例**,同一隻股(MU)8 年前已經跑過一次幾乎一樣嘅
劇本,值得對照讀。

| ticker | 週期/主題 | 倍數(核實) | 起漲期 | 類型 | 起漲前財務狀態 | ex-ante 可見特徵 | 結局 |
|---|---|---|---|---|---|---|---|
| MU(Micron) | DRAM/NAND —— 記憶體週期首輪 | **6.5x 一手核實**($9.56→$64.66) | 2016-02/05→2018-05 | cyclical-supercycle | **蝕錢/近打平**:FY16 收入 $12.4B(較 $16.2B 倒退)、營業利潤率 1.4%、淨虧 $276M;股價已由 2014 的 ~$37 跌 ~70% 至 <$10 | 三寡頭 2015 下行後 capex 紀律、TrendForce 顯示 2016-09/10 PC DRAM 合約價 2 個月內 +20%、渠道存貨跌至 3-4 週(正常 8 週)、3D-NAND 轉換擠壓 DRAM 供給 + 2017 挖礦需求拉動 | **關鍵對照:「週期性回吐,唔係爆煲」**——見頂後跌至 ~$28-30(2018-12,-55~57%)、2019 中再跌至 ~$32(貿易戰/華為禁令);**全程維持盈利、無破產風險**,2020-21 收復,2025-26 AI/HBM 週期再創新高 |
| SK Hynix(000660.KS) | DRAM/NAND 寡頭 | 數倍(未核實精確數字,韓股) | 2016→2018 | cyclical-supercycle | 同樣受 2015 下行拖累 | 同 MU 一樣嘅產業訊號 | 2018 Q3 單季營業利潤 6.47 兆韓元見頂,隨即隨產業崩;2020s AI/HBM 週期再創新高(2026-07 US ADR SKHY 上市,見 memory-supercycle.md) |
| WDC(Western Digital) | NAND(經 SanDisk)+ 傳統 HDD | 約 3.5-4x(約 $28-31→$100-107) | 2016-01/02→2018 中 | cyclical-supercycle(疊加 HDD 結構性衰退底) | 2016-05 完成 SanDisk 併購(~$15.6B,2015-10 announce $86.50、CFIUS 阻中資少數股權後減至 $78.50)——**正正喺低谷簽約垂直整合 NAND** | 同 MU 一樣嘅 DRAM/NAND 訊號,經 SanDisk NAND 傳導 | 2018 全年 -51.3%(同業組 -22.7%);NAND 崩疊加 HDD 結構性衰退,回吐比 MU 更深(約 -62~67%);2025 SanDisk 重新分拆做獨立記憶體標的(見週期 7 SNDK) |
| AMAT / LRCX / KLAC | 半導體設備(記憶體 capex 受益) | AMAT 約 4x、LRCX/KLAC 方向一致(精確數字未核實,LRCX 2021 拆股干擾歷史價) | 2016-01/02→2018 Q1(**比 MU 5 月峰值早幾個月見頂**) | cyclical-supercycle | 2015-16 週期性低殘但維持盈利 | 對記憶體 capex 回升嘅直接讀透 | 2018-05-18 AMAT「9 年最差單日」;BofA 2018-08 因記憶體 capex 減速下調 AMAT/LRCX;跌 ~-50~55%;2020s AI-capex 週期再創新高(AMAT 2026 高見 $723) |

**Pattern(記憶體 7a 對照)**:**半導體設備股(AMAT/LRCX/KLAC)喺 2018 Q1 已經見頂,比 MU 本身
2018-05 嘅頂早幾個月**——capex 減速訊號喺記憶體廠盈利仍在頂峰時已經可見,呢個係一個**可執行嘅
領先指標**(而家 2026 memory-supercycle.md 都用緊 MU capex 2.66x 做「供給回應頂訊號」,同一套
邏輯)。MU 本身喺呢一輪冇破產、只係 -55~67% 週期性回吐,證明「寡頭 + 理性玩家數目少」可以令
supercycle 贏家喺爆煲後存活(對照週期 1/2/3/8 嘅商品純 play 破產潮)。

### 週期 8 — 太陽能/多晶矽爆煲(2005-08 起漲,2008-12+ 爆煲)——**本案例庫嘅典型爆煲教材**
主導樽頸敘事:全球多晶矽短缺(2004-08 現貨由 ~$30/kg 飆至 $400+/kg),鎖定供應合約嘅廠商大賺;
其後一波新產能(大量中國新進場者)+ 2008 金融危機同時令需求同價格崩(多晶矽 2011-12 崩至
~$15-20/kg),幾乎全行業破產。

| ticker | 週期/主題 | 倍數(核實/約) | 起漲期 | 類型 | 起漲前財務狀態 | ex-ante 分野特徵(存活 vs 破產嘅關鍵) | 結局 |
|---|---|---|---|---|---|---|---|
| FSLR(First Solar) | CdTe 薄膜(多晶矽短缺嘅「正對照組」) | **26.44x 一手核實**($11.77 2012 ↔ $311.14 2008,IPO $20→峰值 ~15.5x) | IPO 2006-11-17→2008-05-16 | cyclical-supercycle **疊加真.結構性護城河** | 2004-05 蝕錢,2006 首次盈利($4M/$135M 收入) | **CdTe 薄膜完全唔使多晶矽**+長期公用事業 PPA 鎖定——護城河獨立於多晶矽週期本身,呢個係本案例庫**最清晰嘅「贏家 vs 輸家」分野信號** | 2008-2012 跌 ~96%(未破產、存活),2020s 再創新高——罕見全週期生還者 |
| SPWR(SunPower,舊實體) | 高效單晶矽 | 約 8.3x(IPO$18→峰值 $149.56) | IPO 2005-11-17→2007-11-06 | cyclical-supercycle,效能差異化但仍係晶矽/多晶矽依賴 | Cypress 分拆、IPO 時蝕錢細價股 | 中度:效能差異化但**冇成本護城河**、仍依賴多晶矽投入 | 2008-12 未即爆但長年未真正復原;**2024-08-05 申請 Chapter 11、除牌**——遲咗近 20 年嘅爆煲(ticker 其後被 Complete Solaria 回收改名,唔係同一實體,見下方數據污染註) |
| Trina Solar(TSL) | 垂直整合晶矽 | 未核實精確倍數(IPO $18.50/ADS) | IPO 2006-12-19 | cyclical-supercycle | 1997 創立、2004 轉型太陽能,起漲前溫和盈利 | 垂直整合緩衝輸入成本波動,但冇獨特科技/成本護城河——**靠執行力贏,非護城河** | 罕見生還者:未破產,2017 私有化(~$1.1B,末位 NYSE $11.54),其後上海科創板(688599.SS)重新上市,現仍係一線廠 |

**輸家/爆煲(commodity 晶矽純 play,幾乎全滅)**

| ticker | 週期/主題 | 起漲特徵 | 類型 | 死因(ex-ante 同贏家睇落一樣、實質分野) | 結局 |
|---|---|---|---|---|---|
| Suntech Power(STP) | 中國晶矽組件龍頭(純商品) | IPO 2005-12-14 $15→約 $90(2008,約) | cyclical-supercycle,純商品 | **零護城河**:純晶矽組件廠,純押低成本多晶矽+中國廉價人工;2011 自行終止同 MEMC 嘅多晶矽合約(付 $120M 解約費)——訊號早已可見 | 2013-03 首間在美違約嘅中國發行人($5.41億可轉債),武錫尚德中國破產(2013-03-20),2014-02 Chapter 15,NYSE 除牌——**約 100% 損失** |
| LDK Solar(LDK) | 多晶矽/晶圓生產商 —— **反向整合入新增產能嘅教材** | 創立 2005-07 專為呢個週期而設 → IPO 2007-06-01 $27 | cyclical-supercycle | **零護城河、甚至負面**:反向整合入多晶矽生產本身(同 Fluor 合資廠 2009-07 投產)——**變成引發崩盤嘅新增產能來源之一**,「追價格訊號追到訊號剛好反轉」嘅最尖銳教材 | Chapter 11(2014-10)、中國破產程序(2015)、2016 清盤;$27 IPO/~$70 峰值 → $0 |
| Yingli Green Energy(YGE) | 垂直整合晶矽 | IPO 2007-06,2007-12-10 ADS $33.60 | cyclical-supercycle | 純商品,純靠中國最低成本廠身份競爭;**竟然喺爆煲後仲逆勢擴產**(2012 全球出貨量#1、2011 收入 $2.4B,靠爆煲後更平嘅多晶矽再殺價)——證明「擴產」本身唔係反指標,「零護城河」先係 | 技術性破產 2018(赤字 $1.9B),2018-06-28 起 NYSE 除牌轉 OTC Pink,開曼清盤——11 年慢動作崩盤 |
| Q-Cells(Frankfurt QCE) | 德國電池廠 | IPO 2005-10-05→2008 前峰值 >€80 | cyclical-supercycle+德國 EEG 補貼週期 | 非垂直整合(買晶圓賣電池),全球電池出貨量#1 純靠產能而非成本/科技護城河 | 2012-04 破產,資產 2012-08 售予 Hanwha——品牌延續(Hanwha Qcells)但原股東清零 |
| SolarWorld AG | 德國垂直整合廠 | 創立 1998 | cyclical-supercycle+德國補貼週期 | 垂直整合意在對沖多晶矽波動,但集中喺高成本德國產能——**冇抵銷中國成本劣勢** | **兩度破產**:德國子公司 2017-05 破產、重組實體 2018-03 再破產;美國業務 2018-04 售予 SunPower |
| Energy Conversion Devices(ENER) | 非晶矽薄膜(老牌公司疊加多晶矽短缺敘事) | 約 4.2x($17.25 2005-02→$72.00 2008-06) | cyclical-supercycle,敘事型護城河 | **「敘事護城河冇兌現」**:三接面非晶矽薄膜唔使多晶矽,但效率僅 11-13%(遠低過 FSLR CdTe),集團式燒錢 | 2012-02-14 申請 Chapter 11,申請當日由 $72 跌至 $0.288(約 -99.6%),其後解散 |
| Evergreen Solar(ESLR) | 「String Ribbon」低耗晶矽 | IPO 2000-11 $14,聲稱 2007 峰值 >$113(未核實) | cyclical-supercycle,細價股帶真.局部科技優勢 | **中度:真優勢但不持久**——String Ribbon 確實減少晶矽切割損耗(對多晶矽短缺敘事係真優勢),但效率仍落後 FSLR 同中國晶矽,優勢冇夠深 | 2011-03 關閉僅兩年新廠(Devens, MA),2011-08-15 申請 Chapter 11,2012 歸零,2013-10 解散 |
| Solyndra(私人,提供背景對照) | 非多晶矽依賴嘅圓柱形 CIGS(專為避開短缺而設計) | 私人公司,不適用股價倍數 | speculative/政策驅動 VC 故事 | **敘事護城河係假嘅**:賣點正正係「唔使多晶矽」,但成本/瓦特喺多晶矽**同**組件價格同步崩盤後從未有競爭力,整個論述基礎被雙重擊穿 | $535M DOE 貸款(2009-03,首宗)→2011-09-06 破產→2011-09-08 FBI 搜查,全損+政治醜聞 |
| SunEdison(SUNE,前稱 MEMC,不同輩份對照) | 多晶矽生產商(短缺嘅供給方贏家)→ 後轉型 YieldCo | MEMC 時期受惠短缺(生產商本身持有稀缺資源);2013 改名 SunEdison 轉型太陽能開發/YieldCo,峰值 $33.44(2015-07) | 供給方贏家 → 財務工程型槓桿崩盤(唔同機制) | 前身(WFR/MEMC)握有樽頸資源本身冇破產;**改名轉型後**用 >$11B 槓桿疊 YieldCo 併購(觸發點:告吹嘅 Vivint 併購) | 2016-04-21 申請 Chapter 11(同一實體、兩種完全唔同機制嘅爆煲——先係商品週期贏家,後係財務工程輸家) |

**Pattern(太陽能組 —— 本案例庫嘅核心教材)**:**FSLR vs 幾乎全部同業**係最乾淨嘅單一分野實驗——
同一個多晶矽短缺敘事、同一個時間窗、**只有真正獨立於多晶矽價格本身嘅護城河(CdTe 唔使多晶矽 +
長期 PPA)先至捱過爆煲**。純商品晶矽 play(STP/YGE/Q-Cells)全部破產;LDK 仲**反向整合做新增
產能本身**,係「追供給訊號追到訊號剛好反轉」嘅最尖銳案例;敘事型護城河(ENER 嘅「非晶矽薄膜」、
Solyndra 嘅「唔使多晶矽 CIGS」)聽落同 FSLR 一樣,但效率/成本從未兌現,一樣破產——**證明淨係
「技術唔一樣」唔夠,護城河要真係轉化成成本或鎖價優勢**。呢個係 Phase-3 模型要學嘅核心分野:
唔係「有冇差異化敘事」,而係「差異化係咪真係令你獨立於樽頸本身嘅價格週期」。

### 週期 9 — 頁岩/壓裂砂供給熱潮(2010s)—— 及 2018-20 壓裂砂爆煲
主導樽頸敘事:水平鑽探+壓裂技術令頁岩油氣商業化,同時製造咗壓裂砂(支撐劑)短缺(「Northern White」
威斯康辛砂寡頭因鐵路物流+砂質稀缺賺取溢價)。

| ticker | 週期/主題 | 倍數(約) | 起漲期 | 類型 | ex-ante 可見特徵 | 結局 |
|---|---|---|---|---|---|---|
| PXD(Pioneer Natural Resources) | 二疊紀盆地頁岩油 | 約 14-15x(約,$14.59→$221.46) | 2009-02→2014-07 | cyclical-supercycle | 「二疊紀文藝復興」/Wolfcamp 疊層敘事喺 2012-14 投資者日大力推銷 | 未破產;2016-02 見底 -46%,2020 covid 再急跌;**2024-05 被 ExxonMobil 以 ~$59.5B 收購**——體面退場 |
| FANG(Diamondback Energy) | 二疊紀頁岩油 + 後期整合者 | 約 6-9x(約,2018 峰值未核實) | IPO 2012-10→2018 | cyclical-supercycle+secular 整合者 | Wolfcamp/Spraberry 疊層 + 2013-17 完井成本下降 | 2020-03 一度 -85%,未破產,強力復原,2024 收購 Endeavor 成為超大型整合者 |
| CLR(Continental Resources) | Bakken 頁岩油 | 約 4-5x(約,~2009 低點→$80.64,2014-08) | 2009→2014-08 | cyclical-supercycle | 早期 Bakken 純 play、2010-13 水平鑽探生產力數據已公開 | 未破產,2020-03 單月 -59.7%;2022-11 Hamm 私有化 $74.28/股 |
| EOG(EOG Resources) | Eagle Ford 頁岩(較大盤) | 約 2.1x(較細倍數——大盤股「supercycle 都未必單次乾淨 5x」再一佐證) | 2009-03→2014-06 | secular-growth/cyclical 混合 | 2010 起主導 Eagle Ford 地塊、率先由氣轉油 | 未破產,隨板塊 2014-16/2020 回吐但復原,仍係 S&P500 大盤 E&P |

**輸家/爆煲(壓裂砂 = 「in-basin 砂供給回應」教科書案例,2018 年前已喺行業媒體公開示警)**

| ticker | 週期/主題 | 起漲特徵 | 類型 | ex-ante 已可見嘅警號 | 死因/結局 |
|---|---|---|---|---|---|
| SLCA(US Silica Holdings) | 壓裂砂(Northern White 寡頭) | 約 4-5x(IPO ~$17→峰值 $71.95,2014-09-03) | IPO 2012-02→2014-09 | cyclical-supercycle | **Northern White 溢價定價權本身就係整個牛市論述**,其瓦解(in-basin 砂)喺行業媒體提前 12-18 個月示警 | 未破產但 -99%($71.95→$0.85,2020-03-18);後同 Covia 合併,2024-07 被 Apollo 私有化除牌 |
| Hi-Crush(HCLP→HCR) | 壓裂砂 —— 雙面案例 | 約 2.9x(IPO ~$19.49→峰值 $56.16,2014-08-29) | IPO 2012-08→2014-08 | cyclical-supercycle | 同 SLCA 一樣嘅稀缺/物流敘事;2018 由 MLP 轉普通股架構——爆煲前嘅防守動作本身係訊號 | -99%+;**2020-07 申請 Chapter 11**,2020-10 出關(削債 ~$450M) |
| Covia Holdings(CVIA) | 壓裂砂(Unimin+Fairmount Santrol 合併) | **幾乎冇起漲**——喺週期已過頂先合併上市 | 「零起漲直接爆煲」案例 | 合併本身(2018-06-01)已係防守性削成本動作,**非增長動作**——上市當日已反映 in-basin 砂供給過剩 | **2020-06-29 申請 Chapter 11**,2020-06-30 除牌(OTC CVIAQ),2020-12 見 $0.01;後同 SLCA 一齊被 Apollo 收編 |
| Fairmount Santrol(FMSA,Covia 前身) | 壓裂砂 | IPO 2014(定價由計劃 $21-24 下修至 $16,已反映週期近頂)→2016-01 見底 $1.23 | 冇真正起漲嘅「上市即近頂」案例 | IPO 定價下修本身已係 ex-ante 紅旗——**喺敘事仍熾熱時,一手認購市場已率先降溫** | IPO 至 2016-01 -93%;2018-06-01 併入 Covia(每股 $0.73 現金 + 0.2 股 CVIA),Covia 兩年後亦破產 |
| SandRidge Energy(SD) | 商品超級週期(2008 油價)→ Mississippian Lime 頁岩故事股爆煲 | 約 2.5x(2007-11→2008-06,$26→$65.46)其後 -90%+ | IPO 2007-11→2008-06 | cyclical-commodity→speculative 頁岩故事股 | 2012-13 力推 Mississippian Lime「下一個大局」,地質表現令人失望——當時已有質疑聲音 | 2008 GFC -90%+,2014-16 進一步侵蝕;**2016-05-16 申請 Chapter 11**,2016-10 出關(削債 ~$3.7B、股權近清零) |
| Halcon Resources(HK) | 多盆地頁岩地塊擴張(兩度爆煲) | 峰值未核實 | 2012-02(由殼公司 RAM Energy 借殼、$500M 資本重組)起 | speculative-leasehold-story | 前 Petrohawk 創辦人 Floyd Wilson 主導嘅槓桿式多盆地圈地,2012-13 已有「出價過高」嘅同期質疑 | 2016 單年 -99.4%;**首次 Chapter 11 約 2016-05**(約 2 個月出關),**二次 prepackaged Chapter 11 2019-08-08**(2019-09-24 確認),其後清盤 |

**Pattern(頁岩/壓裂砂組)**:**跨週期一致嘅結論再現**——in-basin 砂供給過剩喺 2017-18 行業媒體
(Rystad、Infill Thinking、OilPrice)已提前 12-18 個月示警(Permian 在建產能追蹤、砂價已喺 2018-08
跌 33%),但 SLCA/HCLP/FMSA/CVIA 全部照樣喺敘事仍熾熱時追價;**大型多元化 E&P(PXD/FANG/CLR/EOG)
未破產、部分體面被收購退場,細價股純 play(壓裂砂公司、SandRidge、Halcon)全滅**——同太陽能組
(FSLR vs 純晶矽 play)、中國商品組(ADM vs VeraSun)一致嘅「多元化/低成本分位 vs 純 play/純敘事」
分野。

---

## 腿 B:價格篩(補 breadth,程式化)

**方法** 見 `exp_magnifier_case_library.py`(逐月收盤、任何 24-42 個月窗 ≥5x、起點限 2010-2024)。
**原始結果**:`sp500_px`(505 隻現任成份)命中 **73** 隻;`px_defeatbeta`(6,769 隻 insider-active
廣度宇宙)命中 **810** 隻;合計 **883** 隻(去重前),存於 `_magnifier_case_library_hits.json`。

**倍數分佈**:≥100x 有 23 隻、20-100x 有 134 隻、10-20x 有 225 隻、5-10x 有 501 隻——**低倍數帶
(5-10x)佔多數,越高倍數帶越稀薄**,同「非線性放大係尾部現象」嘅直覺一致。

**Breadth 篩本身嘅發現(獨立於 Leg A 主觀選材)**:

1. **大部分高倍數 hit 係雜訊,非主題**——>100x 嗰組多數係細價/低流動性殼股(AURX/CHEV/MYCB/CATC/
   PFHO/IVFH/CANN/NIHK 等),同任何可辨識供需週期冇明顯關聯,亦可能含拆股/data artifact(見下面
   caveat)。純價格篩**冇能力分辨「真主題」vs「雜訊」**——腿 A 嘅人手週期地圖唔可以被腿 B 取代,
   兩條腿互補、非其中一條更「客觀」。
2. **腿 A 週期喺腿 B 全部搵到獨立佐證**——MU/SNDK/WDC/LITE/COHR/AXTI/CRDO/VRT/GEV/BE/CLS(AI-compute
   +記憶體+電力+光通訊)、SGML/ALB(鋰)、CCJ 系(鈾,舊窗)、FCX/X(中國商品)、FSLR(太陽能)、
   PXD 系(頁岩)全部獨立喺腿 B 嘅純程式化篩選中出現,證明腿 A 揀嘅唔係倖存者偏誤下嘅事後孔明。
3. **腿 B 補充嘅新 pattern 類型(腿 A 冇覆蓋)**——
   - **CVNA(Carvana)89.03x**(2022-12→2025-12,$0.948→$84.404):**turnaround 型**,非供需樽頸——
     近乎破產(2022-23 財困傳聞、股價跌穿 $4)後靠削成本/GPU 轉正現金流翻生,機制同前面所有
     cyclical-supercycle case 完全唔同,應獨立分類做「turnaround」。
   - **AMD 17.96x**(2015-09→2018-09,$1.72→$30.89):**turnaround 型**——Zen 架構由瀕臨邊緣化
     翻身奪 Intel 市佔,非外部供需樽頸驅動,同 MU 同期嘅記憶體週期(週期 7a)機制唔同、但時間高度
     重疊,值得對照(同一時間窗,一個係供給樽頸週期股、一個係公司特定turnaround)。
   - **ENPH(Enphase Energy)201.69x**(2017-06→2020-12,$0.87→$175.47)、SEDG(SolarEdge)15.96x
     (2017-04→2020-10):**「太陽能 2.0」—— 住宅光伏微逆變器/優化器週期**,同週期 8(2005-08 多晶矽
     短缺)機制完全唔同(呢個係設備/軟件公司,唔直接曝露多晶矽商品價格),但一樣屬太陽能主題下嘅
     非線性放大——值得後續深挖做獨立子週期。
   - **GME(GameStop)54.97x**(2019-08→2021-08)、AMC 7.8x(2020-03→2022-03):**speculative-meme,
     明確排除**——軋空驅動、零供需樽頸敘事,同 SPAC-EV 群一樣屬「敘事/資金流投機」類別,唔屬
     magnifier 核心分類。
   - **MARA(Marathon Digital)62.11x**(2020-03→2022-03)、比特幣礦工首輪牛市——同週期 7 嘅
     WULF/CIFR/IREN(礦工轉 AI 主機代管)係同一批公司嘅**前一次生命週期**,證明「電力/散熱基建」
     本身可以跨多個需求敘事(挖礦→AI)重複被 supercycle 放大,基建資產嘅樽頸屬性比單一終端需求
     更持久。
   - **MPWR(Monolithic Power)5.18x**(2011-09→2015-02,$10.18→$52.73):電源管理/類比半導體,
     同記憶體週期 7a 時間唔重疊、更似獨立嘅類比半導體份額擴張故事(turnaround/secular-growth
     混合),未深究。

**Survivorship 限制(明寫)**:`sp500_px` = 現任 S&P 成份,結構性只含生還者(冇任何已被剔出指數
嘅名字,例如 US Steel 2025 私有化後已經唔喺呢個宇宙,要靠 `px_defeatbeta` 或獨立 yfinance 拉先搵
到)。`px_defeatbeta` 雖然廣度大好多(6,769 隻),但入池條件係「有 SEC Form 4 內部人申報」——
一樣有選擇偏誤(細價殼股/已下市多年嘅公司唔一定留喺呢個 cache),**唔係完整歷史含已下市股嘅
宇宙**。腿 A 嘅破產/爆煲名字(WorldCom/LDK/Suntech/DryShips/Genco/NKLA/GOEV 等)大部分**兩個
universe 都搵唔到**(已下市太耐、或者從未係 insider-active 名單),證明淨用價格篩做 magnifier
case 庫會系統性漏晒輸家——**呢個正正係委派任務原本要求「腿 A 為主」嘅原因**。

---

## 跨週期 pattern 觀察(初步,唔係最終模型)

9 個週期(+1 個記憶體歷史先例對照)、約 90 個 ticker(贏家 + 輸家),橫跨 26 年,收斂出幾個一致
到誇張程度嘅 pattern:

1. **需求敘事幾乎永遠方向啱,分野唔喺敘事真假,喺三件事**:
   - **(a) 有冇喺週期頂附近做槓桿式產能/併購**——Global Crossing/WorldCom(dotcom)、Genco/Eagle
     Bulk/Alpha Natural Resources(中國商品)、VeraSun/CHK 第二輪(油/乙醇)、Q-Cells/SolarWorld
     隱含嘅高成本擴產(太陽能)、Covia 合併(頁岩砂)—— 全部係「贏家變輸家」嘅第一原因,而且
     **呢個動作本身喺當時已經係公開可見嘅 SEC 文件/新聞**,唔係事後先知道。
   - **(b) 護城河係咪真係獨立於樽頸商品價格本身**——FSLR(CdTe 唔使多晶矽)vs 幾乎全部太陽能同業
     (純押多晶矽短缺)係本案例庫**最乾淨嘅單一分野實驗**;JNPR/CIEN(真技術差異化)vs Sycamore/
     Redback(純敘事、零規模收入)係 dotcom 組嘅對應版本。**敘事型「差異化」唔夠**——ENER(非晶矽
     薄膜)、Solyndra(CIGS)都聲稱「唔使多晶矽」,一樣破產,因為效率/成本從未追上。
   - **(c) 多元化/低成本分位嘅緩衝**——ADM(全鏈多元化)vs VeraSun(純 play)、SCCO/NUE(低成本
     分位)vs 高成本同業、三寡頭(MU/SK 海力士/三星)嘅「理性玩家數目少」令記憶體週期(7a)只係
     週期性回吐(-55~67%)而非破產——呢個係跨 9 個週期入面**少數輸家最終冇破產嘅子群**。
2. **多年物理供應回應 lag 幾乎每次都喺當時已公開可見**(新船訂單簿/BDI、in-basin 砂礦公告、
   新產能公告、記憶體/半導體設備 capex),但市場照樣追價到頂——**呢個唔係「有冇訊號」嘅問題,
   係「訊號被追價行為淹沒」**。呢個對 Phase-3 模型嘅含義:訊號存在唔夠,仲要問「市場而家有冇
   定價呢個訊號」(對照 repo 而家 thesis wiki 用緊嘅「crowding 壓 confidence」框架——已喺光通訊
   頁驗證,見週期 7)。
3. **「未正式破產」≠「未爆煲」**——殭屍生還者(Redback→Ericsson 賤賣、Sycamore→清盤、Lucent→
   合併、QS/CHPT -97~99% 但技術上未破產)一樣係 >90-99% 資本蒸發,建模時要當輸家計,唔可以用
   「有冇 file Chapter 11」做二元標籤。
4. **同一 ticker/同一基建可以跨越多個唔同需求敘事重複被放大**——CHK(天然氣 2008→頁岩 2020,
   兩次破產)、CCJ/NXE/UEC(鈾三次歷史週期)、WFR→SUNE(多晶矽生產商→YieldCo,兩種完全唔同機制
   嘅爆煲)、比特幣礦工→AI 主機代管(MARA 2020-22 vs WULF/CIFR/IREN 2023-26)。**基建/資產本身
   嘅樽頸屬性,比單一終端需求敘事更持久**——呢個係太陽能組 ENPH/SEDG(太陽能 2.0,微逆變器/軟件
   非商品組件)、AI-compute 組礦工轉型都佐證嘅同一個現象。
5. **大盤股嘅「supercycle」通常唔會乾淨 5x**——NVO(4.23x)、EOG(2.1x)、ETN(3.07x,未達門檻)、
   NVDA/PLTR(secular-growth,排除)—— 非線性放大集中喺**細/中價股嘅小基數**(SGML 由 $1.06 起、
   SNDK 78.8x 生涯係本庫最極端單例);LLY 係例外(5.99x 仍破格,且持續數年未回落)。**呢個對
   Phase-3 選材有直接含義:magnifier 效應主要喺 small-cap-story + cyclical-supercycle 交界,
   唔係 secular-growth 大盤股**(同委派要求「重點係 cyclical-supercycle + small-cap-story」
   吻合)。
6. **speculative-meme/regulatory-arbitrage 睇落同真樽頸案例好似,但機制完全唔同**——SPAC-EV 群
   (零收入零樽頸)、量子運算/AI 軟件投機群(binary 敘事)、HIMS(監管套利可逆)、GME/AMC(軋空)
   全部有巨大倍數,但冇一個有 ex-ante 可觀察嘅供給約束——分類時要明確拆出嚟,唔可以同 FCX/FSLR/
   MU 呢啲真.供給樽頸案例混為一談。

## Caveats

- **本檔非最終模型**,係 raw 樣本庫;下一步(未做)= 逐個 case 深挖做 case study,先至逼近
  Phase-3 magnifier 模型嘅特徵工程。
- **倍數核實深淺不一**:AI-compute/EV/GLP-1/鈾(2020 年後)大部分經本 agent 用 `yfinance
  period="max"` 一手核實;dotcom/中國商品/油乙醇/太陽能/頁岩(2000s)大部分嚟自 subagent
  WebSearch,佢哋自己標註咗「約/unverified」嘅數字**未經本 agent 二次核實**,落地用前應該對
  Bloomberg/CRSP 等付費歷史數據庫再核一次(subagent 原話)。
- **Ticker-reuse / 拆股污染**:NKLA、LCID、CHPT(部分)、SPCE(部分)、WKHS 喺兩個 pickle
  universe 或 yfinance 直接下載入面出現明顯唔合理嘅歷史高低點(例如 LCID 顯示 2021 年 $580、
  CHPT 顯示 $922——呢啲極可能係殼公司/SPAC 合併前歷史被同一 ticker 回收污染,或者反向合股
  調整錯配)。呢啲 case 本檔已改用 subagent WebSearch 核實嘅公開事實數字,原始受污染數字**冇
  採用**。
- **腿 B 價格篩方法論限制**:月度重採樣會低估真實日內峰值(例如 SLI 日線 subagent 報 38.7x,
  月度篩本 agent 只搵到 21.67x);24-42 個月固定窗口會漏晒 <24 個月嘅極端案例(SNDK 78.8x 喺
  14 個月內發生,完全喺窗口外,靠人手另外核實先搵到)——**呢個係方法論已知限制,唔係疏忽**。
- **未做**:太陽能 2.0(ENPH/SEDG)、比特幣礦工首輪牛市(MARA/RIOT/GME/AMC 軋空機制)、
  turnaround 類(CVNA/AMD)呢幾條腿 B 意外搵到嘅子線,腿 A 冇深入重建佢哋嘅供需/敘事脈絡——
  下次深挖可以揀 2-3 條做獨立 case study。

## Implication(初步,唔係定論)

呢個 case 庫初步支持委派任務嘅假說:**cyclical-supercycle + small-cap-story 兩類先係
magnifier(細基數 + 真.供給樽頸)**,secular-growth(NVDA/PLTR)同 speculative-meme(SPAC-EV/
量子/GME)雖然倍數一樣誇張但機制唔同、應該分開建模。贏家/輸家最強嘅單一 ex-ante 分野唔係
「敘事真假」(通常兩者都真),而係**護城河獨立於商品價格本身嘅程度** + **週期頂前有冇做槓桿式
產能/併購**——呢兩條後續 case study 深挖時應該優先量化做特徵。
