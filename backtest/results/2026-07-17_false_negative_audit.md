# 假陰性審查:17 個「用咗 alpha + 落咗負面結論」嘅嫌疑檔(2026-07-17)

> **性質**:唯讀審查,無修改任何被審檔案,產出只有本檔。全部係文件審查 + 判斷,冇重跑任何回測。
> **動機**:用戶指控「You keep on catching the wrong direction and I afraid you will false negative
> on every single test」。2026-07-17 一日之內 gatekeeper 喺同一個模式上錯咗六次,每次都係攞一把
> 唔啱嘅尺判一樣嘢死。偏差有方向性:只產生假陰性,殺錯咗嘅嘢唔會有人嚟投訴。
> **審查員**:gatekeeper 自己。審自己嘅工作 —— 唔護短,亦唔為咗顯得嚴謹而亂殺。

---

## [結論]

1. **分類:A=0 · B=2 · C=11 · D=3 · 誤列=1**(17 檔)。
2. **用戶嘅指控成立,但假陰性唔喺呢 17 檔度。** 呢六次錯全部落喺 07-16/07-17 嗰批,而嗰批**已經自己
   掛咗撤回橫額**(3 個 D 類)。**07-05 嗰批反而係紀律最好嘅一批** —— 佢哋一致用資本效率 + two-halves
   + A/B 增量,而且 `2026-07-05_rsi2_capital_efficiency.md` 開篇逐字寫住「measured by CAPITAL
   EFFICIENCY (**not Jensen alpha, which under-states a mostly-flat sleeve**)」。
3. **產生呢 17 個嫌疑犯嘅篩選本身就係一次同類錯誤。** 個篩用關鍵詞 grep「alpha」,但呢個字喺 11 個檔
   入面出現嘅型態係「**呢樣嘢係風控/timing,唔係 alpha**」—— 一個**正確**嘅用法。攞把 grep 尺去度
   「有冇攞錯尺」,收咗 11 個假陽性。**同一種病,相反方向。**
4. **最嚴重嗰個唔喺清單入面,而且方向相反 —— 係假陽性:**
   `2026-07-05_rsi2_capital_efficiency.md` Result 1「capital efficient across the board」
   (大盤部署回報 32% vs B&H 17.1%)**從來冇跑過「隨機同曝險」對照**。今日 15:52 落檔嘅
   `2026-07-17_rsi2_be_replication.md` 補咗呢個對照:CapEff **229 vs 隨機同曝險 219**,
   MC 百分位 55.9,折算相關性後 **p = 0.69**。**呢個 repo 而家有兩份未和解嘅 RSI2 正本。**
5. **另一個現行錯誤**:兩份撤回橫額(`leader_dip_reversion` / `dip_capital_efficiency`)寫住
   「07-05 Result 2:**鬆出場捕捉更多回歸**」—— **misquote**。Result 2 原文係「**tight exit (>70)
   dominates there**(highest deployed return + Sharpe + lowest DD)」。橫額嗌錯咗自己嘅罪。

---

## [總表] 17 行

| # | 檔 | 類別 | 一句理由 | 要改咩 |
|---|---|---|---|---|
| 1 | `2026-07-05_breadth_reversion.md` | **C** | 尺啱到係反面教材嘅反面:用條件報酬 + 減 drift excess + 兩半 + 無 survivorship 乾淨版;而且**明確分開上落兩邊**(洗盤→彈真、過熱→回唔成立),正正冇犯「一句蓋兩邊」 | — |
| 2 | `2026-07-05_breakout_momentum.md` | **B** | Minervini selection「冇 alpha」個判詞其實靠**資本效率 vs B&H**(eff large+16/mid+20 vs B&H 18.9/19.8)撐,證據獨立、方向由 VCP 檔獨立印證;但個「alpha」字係多餘嘅判詞包裝 | 理由改寫成「部署效率 ≈ B&H」。真.未閉缺口係檔案自己講嗰個:**加成交量確認**(cache 只有 close)。「risk layer 傷回報」要註明:**從未量度過佢真正嘅工作(封尾部/生存)**,檔案自己都寫「per-trade return 量度唔到佢真正價值」 |
| 3 | `2026-07-05_gex_test.md` | **C** | 「唔建 GEX」靠 **partial\|VIX ≈ −0.08 跨兩半一致** + 文獻(JFE/FlashAlpha)吻合,同 alpha 無關;「唔係 alpha」四個字係修辭唔係判詞 | — (旁註:DIX 喺本檔被「但唔係 alpha」順手降級,但 `phase2_flow` 反而**收咗** DIX(IC 0.137/t3.9/兩半);兩檔對 DIX 嘅語氣唔一致,唔影響 GEX 結論) |
| 4 | `2026-07-05_meanrev_family.md` | **C** | A/B/C 三個增量「唔 pay」全部用**資本效率(部署CAGR/條件Sharpe/曝險)+ two-halves** 判,冇用 alpha;結論全部有範圍限定(細價唔用 vs-SPY、細/中型股避財報有用)冇一句蓋死 | — |
| 5 | `2026-07-05_phase2_flow.md` | **D** | 本檔嘅「breadth 弱/逆向」正正係**用線性 forward IC 度一個非線性尾巴** = 同一種錯尺病;但 2026-07-06 addendum 已自我修正並指去 `breadth_reversion` | 已處理。**病史價值**:呢單係 07-05 就已經發作過同一種病,而且係**用戶 push 先捉到**(「用戶 push:reversion 應該有意義」),唔係 gatekeeper 自己捉到 |
| 6 | `2026-07-05_rsi2_capital_efficiency.md` | **C** ⚠ | **尺嘅選擇啱**(明文拒用 Jensen alpha、誠實報 total PnL 落後 B&H、做齊 two-halves + VIX 分區 + 自我修正兩次)→ 判 C。**但佢唔再係正本** | ⚠ **Result 1 冇對照組**:「部署回報 32% vs B&H 17.1%」係攞 ~30% 曝險嘅每部署日回報 對 100% 曝險嘅每日曆日回報 —— 即 `capital-efficiency-two-traps` 陷阱 1 本身。`2026-07-17_rsi2_be_replication.md` 補咗隨機同曝險對照 → 優勢基本消失。**兩份檔而家打交,repo 冇和解。見 A 優先 #1** |
| 7 | `2026-07-05_vcp_pattern.md` | **C** | 判死靠 **A/B 增量**(VCP 突破 vs not-VCP 突破,VCP 每個 horizon 都輸)+ **連續 IC ≈ 0**,兩條獨立線;horizon 用 5/10/21/42/63d swing = 對得住方法本身;三次不同 operationalisation 一致 | — |
| 8 | `2026-07-06_core_topup.md` | **C** | **全組合層**(SPY 底倉 + LEAP 疊加 vs SPY net-TR),alpha 喺呢層係啱嘅尺,檔案自己講明「alpha isolates the LEAP-sleeve MACHINERY, not stock selection」;唯一負面結論(Rule D on-roll)有 **starved% 62% vs 對照 53%** + **MaxDD 破 -56% 上限**兩條獨立證據 | — (本審查最易犯嘅反向錯誤,冇犯) |
| 9 | `2026-07-06_sector_capeff.md` | **C** | H1/H2/H4 根本冇用 alpha,用 **paired t-test 增量 + 對照臂(同日買 SPY)**;H3 用 alpha 但係**組合變體 vs 組合變體**(75/25 殼,帶 beta 對照)= 啱層;H2 仲特登將象限②(顯著負)同③(噪音)分開判,冇外推 | — |
| 10 | `2026-07-08_altdata_census.md` | **C** | **唔係回測** —— 係數據源普查 + 5 個未來 probe 規格書,自己開篇聲明「本文件不含任何 IC/Sharpe 實測結果」;兩處「alpha」都係口語;冇對任何新訊號落新負面結論 | — |
| 11 | `2026-07-11_sizing_formula_validation.md` | **C** | 完全冇用 Jensen alpha(唯一 hit 係文獻回顧引 Grinold & Kahn「alpha decay」);判詞工具係 Spearman + partial correlation @ 個案層;而且**主動自揭兩個 mirror 落差**(收斂速度 proxy 係 ex-post 唔係 entry-time 可觀察 → 自己將佢踢出 entry sizing)並相應收窄結論 | — |
| 12 | `2026-07-13_bt3_bt4_increments.md` | **C** | **全組合層**(AA-strict vs SPY net-TR),alpha 啱層;而且係全 repo **處理得最好**嘅一份:BT-3 判 α 增量 ≈ 零之後,**冇殺 regime band**,反而另開風險側讀數(MaxDD +0.8pp、underfund 1 vs 6、Dn 中位 61% vs 71%)並判「regime band 嘅實際作用係**風險旋鈕**,唔係 α 來源」。結論 3 仲主動寫明「佢仍可能因為 Jensen alpha 捕捉唔到嘅尾部風險框架而值得保留」 | — (**呢份係全 repo 應該抄嘅先例**,見 A 優先 #3) |
| 13 | `2026-07-15_solvency_gate_probe.md` | **C** | 冇用 alpha;用 **forward excess vs size-matched universe + 條件 Sharpe**;做齊 A/B 增量(對 pe_pctile 軸)、文獻對照(Dichev 1998 / CHS 2008 / Piotroski 2000)、ticker 集中度、ZIRP/高息 era 穩健性;結論係**有條件 GO** 唔係一刀切殺 | — |
| 14 | `2026-07-16_entry_docs_audit.md` | **誤列** | **呢個檔唔係回測。** 佢係 `AGENTS.md → STATUS.md → ARCHITECTURE.md → ...` 嘅入口閱讀鏈一致性審計。RSI2 hit = **0**;3 個 alpha hit 全部係引述「alpha = T1 + T2 拆解」呢條**已存檔嘅 memory**,唔係判詞 | 由嫌疑名單剔走。(疑似同 `2026-07-16_docs_audit.md` / `2026-07-16_experiments_audit.md` 撈亂) |
| 15 | `2026-07-16_leader_dip_reversion.md` | **D** | 已掛 🛑 橫額;`2026-07-17_rsi2_be_replication.md` §7 已逐條列明撤回乜、保留乜 | 已處理。**但橫額本身有兩個錯要修**:(a) 「07-05 Result 2:鬆出場捕捉更多回歸」係 **misquote**,Result 2 原文講「tight exit (>70) dominates」;(b) 橫額最擔心嗰個罪(200SMA 濾網)**經重跑證實喺資本效率上無害**(CapEff 229→265),真殺手係出場改動(各 −48pp)。**另:本檔個 mirror 其實係啱嘅** —— 佢用「同一隻股、同長度、隨機進場」做基準,明文拒用 B&H CAGR(「會將曝險時間差誤判做訊號嘅回報」)。**錯嘅係配置,唔係尺** |
| 16 | `2026-07-17_kol_shunge_scorecard.md` | **D** | 已掛 🛑 橫額,兩條核心結論撤回,正本移去 `kol_shunge_roundtrip.md`;橫額自己認咗「gatekeeper 失職,唔係 subagent 嘅錯」 | 已處理 |
| 17 | `2026-07-17_xle_xlk_rotation.md` | **B** | 判詞**冇用 alpha**,用 CapEff **同時**並列逐日 increment t-test,而且自己揭發咗 CapEff 陷阱 1(分母細谷高比率)、自己講「呢個係『**未能證實**』而非『證偽』」—— 紀律好。**但個判詞有一條風險側讀數從未入數** | 唔使重跑 t-test。要補:**1a 切換(63d)喺四個窗口 MaxDD -31.2% vs 50/50 嘅 -45.1%、Sharpe 0.92 vs 0.85、CapEff 全窗口贏** —— 呢個一致嘅風險側優勢完全冇入判詞,而 `bt3_bt4` 對 regime band 就俾咗**正正呢個 credit**(同一 repo,兩把尺)。**但落判前必須先驗一件事**:5 個臂嘅 MaxDD 全部一模一樣 -31.2%,強烈暗示係**單一 episode**(似 2020 XLE 崩)造成,唔係穩健嘅風控性質。**要跑嘅係 episode 拆解,唔係成個實驗** |

---

## [A 類優先] 冇一個檔係 A —— 但有四件真.要跑嘅嘢

**先講白**:按用戶自己俾嘅 A 定義(結論靠 alpha 撐 / mirror 錯 / 同既有結論打交),**17 檔冇一個中**。
我唔會為咗交數砌 8 個 A 出嚟。但審查過程翻出咗四個真.未解,按價值排:

### #1 —— RSI2 兩份正本打交,而且冇人和解(**最高優先,唯一會影響落注嘅**)

| | `2026-07-05_rsi2_capital_efficiency.md` | `2026-07-17_rsi2_be_replication.md` |
|---|---|---|
| 標籤 | `active — mechanism HIGH confidence` | 今日 15:52 落檔,無標籤 |
| 對照組 | **冇隨機對照**;基準 = B&H(100% 曝險) | 隨機**同曝險同交易次數**,1000 次/隻/臂 |
| 大盤讀數 | 部署回報 **32% vs B&H 17.1%**、條件 Sharpe 1.16 vs 0.88 | CapEff **229 vs 隨機 219**、MC 百分位 55.9、n_eff 折算後 **p=0.69** |
| 判詞 | 「capital efficient across the board」 | 「同擲毫子分唔開」 |

**要跑咩**:07-05 **Result 4/5(VIX 三區 × 鬆出場 = +4-5%/筆、88% 命中、2-3 星期持有)從未經過
隨機同曝險對照**。07-17 只測咗**無條件** RSI2,冇掂過 VIX 條件化。**呢個係 RSI2 唯一仲企緊嘅主張,
而且係承重嘅** —— `2026-06-30_shortcall_timing.md`(✅ verified)嘅對稱模型「LEAP entry = RSI-2 DIP /
SHORT_CALL = RSI-2 OVERBOUGHT」已經寫入 scorecard v3.1。**如果 VIX 條件化嗰半都過唔到隨機對照,
scorecard v3.1 個 LEAP 入場閘就冇咗依據。**
配置:07-05 Result 4 原配置(entry<10、exit>90/95、**冇 200SMA 濾網**、**冇時間上限**、按入場日 VIX 分區)
+ 07-17 嘅隨機同曝險對照臂 + n_eff 折算。07-05 自己個 caveat 已經預告咗答案可能係「驗唔出」:
極端 VIX 區「112–285 trades 但叢集喺 ~5–8 次 capitulation episode → 有效獨立 N 好細」。

### #2 —— 兩份撤回橫額本身要修(**成本最低,即刻做得**)

橫額嗌錯咗自己嘅罪:(a) misquote 07-05 Result 2(原文講 tight exit dominates,唔係鬆出場好);
(b) 重跑證實 200SMA 濾網喺 CapEff 上**無害**(+5pp),真殺手係「早出場」同「10 日封頂」各 −48pp。
**橫額應該指去 `rsi2_be_replication.md` 做正本,而唔係指去 07-05**(07-05 個 Result 1 本身已經被同一份
重跑削弱咗)。

### #3 —— 將 `bt3_bt4` 嘅「風險旋鈕」先例寫成通則

BT-3 判 regime band 嘅 α 增量 ≈ 零,但**冇殺佢**,反而另開一條風險側判詞。呢個處理係啱嘅,但係
**一次性**嘅 —— `xle_xlk_rotation` 就冇享受到同一個待遇(MaxDD -31.2% vs -45.1% 從未入判詞)。
同一個 repo 對兩個機制用緊兩把尺。要做:寫入紀律 —— **判一個機制之前,先問佢係為咗回報定為咗風控;
如果係風控,回報中性 ≠ 冇用。**(xle_xlk 嗰個要先做 episode 拆解排除單一 2020 artifact,見總表 #17。)

### #4 —— `breakout_momentum` 嘅成交量缺口(檔案自己已經標咗)

「Minervini selection 冇 alpha」係 price-only 跑出嚟嘅,而 practitioner 最強調嘅 **VOLUME≥1.5× 突破確認
缺席**。檔案自己寫「唯一未閉 = 加成交量確認會唔會令突破 selection 由『無 alpha』變『有』」。優先度低
(先驗預期低,而且 VCP 檔獨立印證咗突破 follow-through 本身好細),但佢係一個**掛住未閉嘅真缺口**,
唔係一個假陰性。

---

## [防再犯] Lint / checklist 草稿

### 先講:「問呢把尺啱唔啱」機械化唔到,但佢下面嗰層可以

用戶版嘅一句總結(memory `metric-and-direction-discipline` §3)——「**落判詞前必問:呢把尺,量緊嘅
係咪我要答嗰樣嘢?**」——係啱嘅,但佢係一個 vibe check,冇可證偽性,答「係」零成本。要機械化,要跌落
一層。

### 六次錯 + 本審查翻出嘅兩單,共通結構唔係「尺」,係**冇對照臂**

逐單睇「當初點解錯」同「後來點翻案」:

| 錯 | 翻案靠咩 |
|---|---|
| 順哥 mirror(長揸尺量短炒) | 加一條「換 mirror」A/B 臂 → 證實 **7pp 純粹係 mirror 造成** |
| 抽取爛(關鍵詞漏 22% 收 32% 假) | 加一條「LLM 抽取」對照臂 → MC 百分位 **0.17 → 0.94,結論反轉** |
| RSI2 三處配置相反 | 加四條「逐個改動」A/B 臂 → **殺走 82% PnL**,而且揭穿真殺手唔係大家以為嗰個 |
| 07-05 Result 1 過度樂觀(假陽性) | 加一條「隨機同曝險」對照臂 → 優勢 **32% vs 17.1% → 229 vs 219** |
| `phase2_flow` breadth 判死 | 加一條「條件報酬(非線性)」對照讀法 → 洗盤 **21d +2.58% = 3× baseline** |

**五次翻案,五次都係靠加一條「同一部機器、只改一個嘢」嘅臂。** 而五次錯,全部係
**單臂測試 + 一個現成基準**。呢個係可以機械檢查嘅。

### 落負面判詞前嘅七道閘(答唔到任何一條 = 唔准落負面判詞)

1. **對照臂**:有冇至少一條「同一部機器、只改一個變數」嘅臂?
   *單臂 + 一個現成基準(B&H / SPY)= 唔可以判死。*
2. **同曝險隨機對照**:個結論係咪「贏/輸咗 B&H」或者「CapEff 高/低」?
   如果係 → 有冇跑「**同曝險、同交易次數、同持倉長度分佈、隨機擺位**」對照?
   *冇 = 你量緊曝險結構,唔係量緊訊號。(07-05 Result 1 就係死喺呢條)*
3. **repo 查重(可以真係寫成 script)**:`grep -ril "<訊號名>" backtest/results/ thesis/ docs/ Reference/`
   有 hit 而我未讀 → **停,先讀**。
   *07-16/17 兩份 RSI2 報告就係死喺呢條 —— 十二日前已經有份 `active — mechanism HIGH confidence`
   嘅檔,冇人 grep 過。呢條唔係方法論分歧,係冇做功課。*
4. **方向閘**:我講緊買方定賣方?`grep -ril "<訊號名>" | xargs grep -l "verified"` 睇另一邊有冇已驗證用法。
   *RSI2:買方 = dip;賣方 = `2026-06-30_shortcall_timing.md` RSI2>90 賣 call PF 2.26 ✅。
   短 DTE:買方死;賣方 = playbook M3 賣 21 DTE ✅。一句蓋兩邊 = 同 repo 自己打交。*
5. **配置對源**:如果係複製外部來源嘅測試 → 逐行對過佢原配置未?每一處分別我 justify 咗未?
6. **風控 vs 回報**:呢個機制係為咗賺錢定為咗唔死?
   *如果係後者 → 回報中性 ≠ 冇用,要另開風險側判詞(`bt3_bt4` regime band 先例)。*
7. **「驗唔出」定「證偽」**:p > 0.05 + 低 power = 前者,唔准寫「死咗」。
   有冇報 **n_eff**(跨股/跨期相關性折算)?
   *`rsi2_be_replication` 做啱咗:naive p≈0.07 → n_eff=3.8 → p=0.69,而且明文寫「naive p 值係過度
   聲稱嘅樣本,唔好引用」。`leader_dip` 就寫咗「基本上已經死咗」而證據只支持「驗唔出」。*

### 可以即刻機械化嘅兩條

- **閘 3(查重)** → pre-flight script:開任何 `exp_*.py` 之前跑 `grep -ril "<訊號名>" backtest/results/`,
  有 hit 就喺 docstring 列明「已讀過邊幾份 + 我嘅配置同佢哋差喺邊」。
- **閘 1/2(對照臂)** → 仿 `thesis/lint.py` 加一條 `backtest/results/` lint:
  一個檔如果**含負面判詞關鍵詞**(判死 / 冇料 / 冇 edge / negative / 唔建 / 不成立 / 冇 alpha)
  但**冇「對照臂 / control / A/B / 隨機對照」段** → **error**。
  呢條係純文字檢查,唔使跑數,而且捉得到今次全部六單。

---

## [產物]

- 本檔:`backtest/results/2026-07-17_false_negative_audit.md`(唯一新增)
- 無修改任何現有檔。上面所有「要改咩」全部係**建議**,未執行。

---

## [你唔肯定嘅位] 誠實節

**我自己有冇過度更正嘅風險?** 有,但今次係**相反方向**:我交咗 **A=0**,對一個「你成日判假陰性」
嘅指控嚟講,「我審完自己,發現冇嘢要改」係一個**可疑到極**嘅答案。我嘅反證係:我照樣捉咗自己兩單
—— (a) 07-05 個 canonical 有假**陽**性(呢個對我不利,因為佢係我自己攞嚟做「正面例子」嗰份);
(b) 撤回橫額 misquote 咗 Result 2(即係話我連認錯都認錯咗)。如果我護短,呢兩單唔會寫。
但呢個唔等於 A=0 就啱。

**六個我唔肯定嘅判斷:**

1. **07-05 Result 1 同 07-17 §3 到底係咪真.打交(我最唔肯定嘅一條,而且佢係我 A 優先 #1 嘅地基)。**
   兩者**量度定義唔同**(部署 CAGR 年化 vs 累計 log PnL ÷ 平均曝險)、**宇宙唔同**(23 隻含板塊/細價/
   Mag7 vs 77 隻 theme 名單 + SPY/QQQ,後者有嚴重生存者偏差)、**出場唔同**(>80 vs >90)。
   我**冇重跑去核實佢哋量緊同一樣嘢**。我嘅講法係「07-05 未經同曝險對照」——**呢個係事實**(佢個
   Method 冇列隨機臂);但「所以佢會過唔到」係**推論,唔係已被推翻**。呢個分別好重要,我上面盡量
   守住咗,但如果有人引我呢份去講「07-05 已被推翻」,咁就係我寫得唔夠緊。
2. **用戶叫我判 07-05 做 C 兼「佢先係 RSI2 嘅正本」,我判咗 C 但唔認佢係正本。** 如果用戶對 07-05 嘅
   讀法啱而我錯,咁我成個 A 優先 #1 就係錯嘅,而且我就係喺度**製造**緊一個假陰性(去殺一個好嘅結論)
   —— 即係我審緊嗰種病。
3. **`xle_xlk` 判 B 定 A,我來回反覆咗兩次。** 判 B 嘅理由(5 個臂 MaxDD 全部一模一樣 -31.2% = 單一
   episode 嫌疑)係我自己臨尾先諗到,冇驗證過。如果 -31.2% 真係跨多個 episode 穩健,佢應該係 A。
4. **`breakout_momentum` 判 B 定 C,我兩邊都講得出理由。** Minervini 用 63 日固定持有度一個突破訊號
   —— 按 repo 自己嘅 mirror 紀律(swing → 5-21d),呢個係 horizon 錯配,而檔案自己都認「63 日固定
   持有係武斷 baseline」。我最後判 B 唔判 A,靠嘅係「VCP 檔獨立印證咗突破 follow-through 本身好細」
   —— 但 VCP 檔顯示 excess 係**隨 horizon 上升**嘅(21d +0.42% → 63d +1.08%),呢個其實**削弱**咗我
   「63d 唔緊要」嘅論證。我知道呢度唔企得好穩。
5. **17 檔入面有 6 檔我冇親自全文讀**(`core_topup` / `sector_capeff` / `altdata_census` /
   `sizing_formula_validation` / `solvency_gate_probe` / `entry_docs_audit`)—— 我派咗 subagent 讀,
   自己只 grep 驗證咗關鍵 claim。呢 6 檔全部判 C。**如果 subagent 漏咗嘢,我個 C 就係假嘅** ——
   而呢個正正係「攞一份二手報告當一手證據」,同「讀一篇 substack 就推及全刊」係同一家族嘅錯。
   我做咗嘅緩解:`entry_docs_audit` 個 subagent 話同 brief 對唔上,我自己 grep 覆核咗(RSI2 hit=0、
   alpha hit=3 全部係引述)—— 佢啱。其餘 5 檔我冇獨立覆核。
6. **「A=0」可能係因為個 17 檔清單本身揀錯咗人。** 我判咗個篩選(grep "alpha")係假陽性機器 —— 如果
   真係咁,咁**真.假陰性可能喺呢 17 檔以外**,而我冇去搵。一個更好嘅篩應該係
   grep「單臂測試 + 冇對照臂 + 有負面判詞」(即上面閘 1/2 嗰條 lint),而唔係 grep 一個字。
   **我冇跑過嗰個篩。**
