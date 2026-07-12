# KARS_MEMORY — 專案記憶(系統的記)

> 本檔是 Karst 的長期記憶。每次啟動先讀此檔 + `USER.md` + 最新 session,
> 不要再從 conversation summary 重建。

最後更新:2026-07-06(§12)。**入口已改:新 session 先讀 repo 根的 `STATUS.md`,再讀本檔。**

---

## 1. 系統定位 + 外部參考(同層 `C:/projects/Investment/`)

**Karst = 獨立、自足的全自動 agentic 投資決策系統。自己找 edge(自建 Phase 3 質性層)、
自己跑決策管線。edge 就在 Karst。**
(2026-07-04 更正:舊版把 Karst 寫成 Compass+Tree 的「執行臂 / WHEN-HOW」、edge 在
Compass+Tree——那是錯的 framing,已廢除。)

同層 repo 一律**只是外部參考素材,非功能依賴**:

| repo | 一句話 |
|---|---|
| **Compass** | 舊質性/紀律筆記(部分由較弱 agent 建、可能有錯;只當素材) |
| **Tree**(drawtree) | 可證偽假設樹協定 github.com/Draw-Tree/drawtree-protocol(參考) |
| **Reference**(原 Quant)| 原料倉:distillation + transcripts + 抓取 script + ideas |
| **ebooks**(原 Investors)| 書庫:蒸餾原料(Dorsey/Porter/Minervini/Lynch/O'Neil…) |
| **Indicators** | 指標數據 Python crawler(用途待評估) |

> **2026-06-30 reorg:** Quant→`Reference`;書→`ebooks`;`.agents`(session memory)→已移入 Karst。

---

## 2. 終極目標(用戶 2026-06-24 定義)

Daily stock scanning system:底層可腳本化 TA 訊號,上層 LLM agent 分析不可程式化的東西;
top-down(SPY/SPMO/QQQ 市場 → 價值鏈輪動 → 個股);最終可為網站/工具;**edge + backtested 最重要**。

---

## 3. Core Strategy(已確認,idea-07)

- **Layer 1 — Options Core(只 SPY/QQQ/SPMO)**:CSP(QQQ 20Δ/30DTE/50%PT,98.6% WR)
  + PMCC(SPY only,long leg deep ITM 0.70)+ 方向性 deep ITM LEAP。可選 IC(SPY 10Δ)。
- **Layer 2 — Long Stock**:RSI(2)<5 + price>200SMA;持股賣 covered call。
- **Layer 3 — Bottleneck 衛星**:小市值高成長(idea-02),高風險高報酬,satellite only。

賣保費 > 買保費(鐵律)。詳見 Karst `params/`。

---

## 4. 關鍵決策 / 已知坑

- 🔴 **idea-07 LEAP delta 錯**:0.30 是 standalone 方向性 LEAP(transcript 01),**不是**
  PMCC long leg(必須 deep ITM 0.70-0.80,否則 defined risk 結構壞)。Karst 已拆開。
- ✅ **複核紀律**:參數帶 tag(✅ verified / 📄 distilled / ⚠️ open)。只信對過 transcript 的數字。
- 🔴 **別盡信 Compass**:部分由較弱 agent 建,可能有錯。以 backtest distillation 為地基。
- 🔴 **不寫人類心理教訓進系統**:no-human-in-loop,只留系統性 invariant(Karst `invariants/`)。
- ⚠️ **self-fixing 危險處**:執行層可全自動;策略演化層必須有 deflated Sharpe + walk-forward 驗證閘。
- 🔴 **School mismatch**:Compass 封存的 deep-value agents(Buffett/Graham/Klarman…)≠ bottleneck
  高成長衛星的正確學派。衛星 lens = 成長動能 + 護城河耐久性(Dorsey/Porter)+ Lynch 分類。

---

## 5. TA 訊號(idea-05/06,門已關)

4 price 家族 + 1 flow:Trend / Mean-reversion / Volatility regime / Relative strength / Flow(insider+GEX)。
已 kill:SMC、Elliott Wave、Fibonacci、KDJ/LWR/BBI(冗餘)。不再探索新 TA 方法。

---

## 6. 參考 repo

- `github.com/xbtlin/ai-berkshire` — 投資決策 copilot 架構參考(用戶 2026-06-28 分享;當鷹架,非真理來源)
- `github.com/Draw-Tree/drawtree-protocol` — Tree 協定
- `yan-labs/serenity-aleabitoreddit` — bottleneck 方法論(methodology.md 可用;theses/track-record 不可)

---

## 7. 當前狀態(2026-06-30)

- Karst spec 完成(Layer-1/2 + invariants + lenses 規劃);git 多個 commit on main。
- reorg 完成:Quant→Reference、books→ebooks、.agents→Karst。
- **backtest harness 已建**(`backtest/`,純 pandas,**不用 vectorbt**;data = defeatbeta≥0.0.60 + yfinance fallback,banner 已在 loader 吞掉)。
- **回測結論(✅ 自驗,已解 200SMA 未決項):** 200SMA 濾網不穩健;RSI-2 raw CAGR 贏不了 B&H,**但 Jensen alpha 顯著正**(QQQ 6.5%/yr t2.9、SPY 4.3% t2.4,集中在 entry<5–10 / exit>70,拉長出場殺死 alpha;AvgDD 僅 ~−2~4%)→ **RSI-2 = modest 低容量進場 alpha,可疊加 VRP(賣 CSP / 進 LEAP 的超賣時機)**,不是純回撤 overlay。LEAP 需右側閘防破產(provisional)。見 `backtest/results/`。
- **CSP 自驗(provisional):** 引擎重現 94–97% WR,**但 alpha 不顯著——CSP 利潤大半是 beta(短 put ≈ +0.2 delta),不是免費 VRP alpha**(且對成本假設敏感);唯一亮點 = RSI-2<10 dip 進場(PF↑、AvgDD↓、可疊進場 alpha)。見 `backtest/results/2026-06-30_csp.md`。
- **Scorecard + skill 已建**(`backtest/scorecard.py` + `.claude/skills/karst/`):每日 0–100 per-tool 適合度,agent 可 `/karst` 呼叫。
- **Scorecard 驗證(✅ `results/2026-06-30_scorecard_validation.md`):** 分數**不預測報酬**(LEAP/PMCC 高分均值回歸=反指標),但**預測風險/regime**(高分→回撤小);**CSP 那格如設計運作**(高分→未來回撤小,boundary ~25)。→ scorecard 是風險儀表板,非 alpha 神諭。
- **Scorecard v2 已建 + 驗(`results/2026-06-30_scorecard_validation.md`):** 百分位尺度修好範圍(0–100);CSP/CASH 驗證有效。**但 LEAP 仍不預測報酬——因為把 RSI-2 dip 混進分數會稀釋 edge(dip alpha 只在隔離時顯現)。架構結論:scorecard = regime/風險適合度(非報酬預測);RSI-2 dip = 分開的純進場 trigger,別混進分數。** PMCC degenerate(百分位灌水、假霸榜),待重做或拿掉。
- **Scorecard v3 已建 + 驗(定稿):** 用戶的乾淨規則模型——`LEAP = >200SMA × RSI-2 dip`(純 gate×dip);`PMCC = >200SMA × 高IV`;`CSP = IV-rank U 型`(低IV=平靜收租安全 / 高IV=capitulation 危險,看 csp_mode);`CASH = <200SMA × 高IV`。raw 0–100(丟掉 v2 百分位,稀疏訊號會壞)。**驗證:LEAP gate×dip 在 5d 重現 dip alpha(dip +0.85% vs 無dip +0.16%);CSP U 型有效(高IV端較險);PMCC 不再 degenerate;CASH 危險旗標有效。** scorecard = regime/風險適合度 + RSI-2 trigger。**v3.1:PMCC 拿掉(長腿≡LEAP);改成 `SHORT_CALL = >200SMA × RSI-2 超買`——驗證 SPY 短 call PF 1.53→2.26(RSI2>90),QQQ 動能極端超買會反噬。對稱:LEAP 買在 RSI-2 dip / SHORT_CALL 賣在 RSI-2 超買。** 見 `results/2026-06-30_shortcall_timing.md`。
- **下一步(可選):** CSP cost-sweep、harden LEAP magnitudes、wheel 變體、Dorsey 蒸餾(衛星層)、定義 INV 數值、macro regime_matrix(殖利率/信用)接 CASH。核心 timing+scorecard 線已收尾。

---

## 8. Spine — top-down 掃描系統(2026-07-01 起,終极目標的脊椎)

> 校正:整套系統**對所有標的評分**(two-tier);只有 SPY/QQQ/SPMO 用期權工具(LEAP/Covered Call→PMCC/CSP),其餘個股**只做多**。Karst 原本只是 3-ETF 期權 widget;spine 把它變成 universe-driven 掃描器。`backtest/spine/`,`python backtest/scan.py`(--json)。

**終局 = 6 段漏斗**(每 Card = 一個 ticker):0 市場閘 → 1 板塊溫度(階層)→ 2 個股結構分 → 3 兩層表達 → 4 風控;**TA 擇时另成 Phase 4**。

**鎖定的設計決策(見 `backtest/results/2026-07-01_spine_phase0.md`):**
1. **擇时 = Phase 4 + 獨立欄位,絕不乘進分數**(重申:結構分=regime/資格 ≠ 進場 trigger=RSI-2)。Phase 0 無擇时,故 MU(+165% 乖離)只 ELIGIBLE 不喊買。
2. **SPMO = momentum 因子**(非 market、非 sector);仍是 tier-1 期權標的,`RS(SPMO/SPY)` 餵市場閘。
3. **市場閘** = SPY>200SMA + ^VIX 分檔/iv_rank + IWM 廣度背離 + ^VIX/^VIX3M term + SPMO-RS。**否決 QQQ/DIA 進閘**(與 SPY 太相關)。**價格/RS 用 ETF,只有波動用 index**。
4. **板塊先做 Memory**(小、週期強、新聞密)。`DRAM` ETF 太新(2026-04 上市,61d 無 200SMA)→ 溫度用 **cap-weight 籃 {MU,WDC,STX}**;逼出 `etf:` OR `basket:` 抽象。
5. **subsector 階層**(schema 先留,Phase 1 填 Memory→SEMI):兩層 RS(子vs母 / 母vs市)+ **coherence/breadth**(抓「只有 MU 在撐」)→ 餵 INV-5。
6. **Flow 訊號隔離**:gamma wall/GEX、CTA、Fear&Greed = 付費/不可免費回測 → overlay 層、標未驗證、永不進核心。免費可回測的正交維度只有 **breadth + VIX term**(後者已進閘)。
7. **資料新鮮度修正**:defeatbeta 價格**慢 ~1 交易日** → `data.py` `load()` 翻成 **yfinance 優先、defeatbeta fallback**(價格);defeatbeta 專供 fundamentals/transcripts/news(Phase 3)。`source=` 可 pin 回供應商重現 backtest。

**MVP1 = Phase 0 + 1 + 4**(v2 = Phase 2 overlay + Phase 3 thesis seam)。用戶定:Phase 1 是 key,先做。

**狀態:**
- **Phase 0 完成**(market gate + 兩層 router)。順手修資料新鮮度:`data.py` yfinance 優先(defeatbeta 慢 1 天)。commit `afc1c8b`。
- **Phase 1 完成**(`results/2026-07-01_spine_phase1.md`):板塊溫度從 **ETF 真實持股(option B)** 算。關鍵發現:DRAM(Roundhill Memory)持股是**全球**的——SK Hynix 24.7% / Samsung 16.3% / Kioxia / + 現金 sleeve 14.9%(濾掉);US 三名只佔 ~14%,WDC 不在內。決策:溫度用全持股(幣別在 RS/ROC 比值中自動消掉,只剩時段差,微小);ETF 權重加權;tier-2 可下單 = US 持股自動衍生(SNDK/MU/STX)+ DRAM 本身當板塊級 long;外國名 = context。兩層 RS(vs SPY / vs SEMI=SOXX)+ breadth/coherence + INV-5(laggard 只在 US 可交易成員裡判)。驗證讀數有洞見:Memory Hot 但 vs SEMI 0.99(半導體在熱、記憶體只跟上),US RS 龍頭 SNDK,STX 落後。
- **Phase 4 完成 → MVP1 收口**(`results/2026-07-01_spine_phase4_mvp1.md`):RSI-2 擇时做成**獨立 card 欄位**(DIP<10 / overbought>90 / elevated / neutral),**不乘進結構分**。tier-2 long 的 `action` = 結構資格 × 擇时 → **BUY_DIP / WATCH / AVOID**。tier-1 保留已驗證 scorecard(擇时已烘在內),RSI-2 只 surface 不 decompose。驗證讀數:記憶體名字全 WATCH(合格但無 dip、極度延伸 → 等回調,不喊買)——正是設計要的兩層誠實輸出。
- **MVP1 = Phase 0+1+4 完成**:可用的每日 top-down 掃描(market gate → sector temp[ETF 持股] → 兩層表達 → RSI-2 action)。入口 `python backtest/scan.py [--json]` / `/karst` skill。
- **Phase 2a 完成**(`results/2026-07-01_spine_phase2a_rotation.md`):GICS 板塊輪動地圖(`rotation.py`,11 SPDR,RS vs SPY 63/21d,ETF-only)= **防禦/regime 鏡片**。讀數:tilt risk-on(勉強)、**breadth narrow(2/11 贏 SPY → fragile/late-cycle 警示)**、tech leading 但 RS21 在退、Indus/Health/Fin RS21 加速(輪動跡象)。
- **關鍵策略決策(用戶定,2026-07-01):**
  - **進攻 = tech value-chain(跨 GICS:Tech→Energy→Materials/InP→Indus),個股深做 + bottleneck 過濾(Serenity/Dorsey/Porter)= Phase 3**;**防禦 = 非 tech GICS 板塊,ETF-only、mean-revert/分散**(非對稱深度 = 控 overfitting)。
  - **value-chain ≠ GICS 板塊**:兩個鏡片分開拿(GICS=防禦/輪動;value-chain=進攻)。別把鏈塞進板塊盒。
  - **「tech 才有 true bull」要可證偽**:給機器可檢查的「tech 領導已壞」條件(XLK RS<1 持續 → 轉防禦),別變成不可證偽信仰(POET 死法)。
  - **板塊性格藏在趨勢尺度(%>200),不在日線(Hurst/ADX 全部 ~隨機)**;且全在 bull 上 fit → 2b 要跨多 regime 量測 + 對標 B&H + 過 deflated-Sharpe/walk-forward 閘 + total-return。
  - **bottleneck = 讓 value-chain 廣度不變 FOMO 的紀律**(無替代品+定價權+可證偽 kill);最深 bottleneck 常不可交易(InP/SK Hynix)→ 用下游/ETF 表達,別獵奇找 ticker。
  - **順序:把 Phase 3 以外的先收齊**(A)——2a 完成 → 2b 性格 → 2c 輪動動態 → **最後 Phase 3(thesis = value-chain + bottleneck = alpha)**。
- **Phase 2b 完成——紀律性負面結果**(`results/2026-07-01_sector_character_2b.md`,`exp_sector_character.py`):量測(非硬編)板塊性格。結論:**假設大致不成立**。TE 全部 0.21–0.24(板塊分不出趨勢性);只 3/11 tag 跨 IS/OOS 穩定;CAGR 上幾乎所有主動變體輸 B&H **但 MaxDD 砍半** → **dip 進場 = 風控,非報酬(再次印證地基鐵律)**。唯一可信差異:**Fin(弱 Health)偏 mean-revert(MR 贏 B&H Sharpe+CAGR、IS/OOS 穩),但 DSR 0.71<0.95 未過多重檢定閘 → suggestive 未確認**。**決策:不建 11 板塊 trend/chop EXIT 地圖(過擬合);改用一條通用 EXIT「dip 進場 + 跌破 200SMA 出場」當風控覆蓋餵 Phase 4;Fin/Health 只當低信心提示。** 驗證閘擋下一個會過擬合的功能 = 高價值。data.py 加 `adjusted=` total-return(只給 backtest)。
- **估值 backtest 完成(Phase 3 前奏,`results/2026-07-01_valuation.md`,`exp_valuation.py`)**:系統原本零估值維度。測「PE 相對自身歷史分位,便宜時買」是否有 edge(用 defeatbeta `ttm_pe`,唯一長日線歷史;PS/EV-EBITDA/ROIC 只 2022+ 太短)。結果:**Test1 U 型**(Q0 便宜 8.4% 勝 Q2/Q3 中間 4.9–5.7%,但 **Q4 最貴 9.1% 最高**——高 PE 成長股續奔;拖累 value 的正是 NVDA/META/CSCO/MSFT;value 有效在成熟股 AAPL/KO/PG/JNJ)。**Test2 機械策略不成立**(只 AAPL DSR 0.97=倖存者代言,其餘輸 B&H)。**結論:估值非機械 alpha,但(1)當 context 量尺 modestly useful;(2)從估值角度驗證 offense/defense 分野——成長/offense 名字 value 是陷阱(貴≠賣,盯成長耐久),成熟/defense 名字便宜是 tilt。** 回答「priced in?」:分位=期望值坐標,非決策;要配 moat/ROIC/成長耐久(Expectations Investing)。**決策:不建機械估值策略;把估值分位(自身歷史+產業相對)當 Phase-3 thesis 的「估值/期望值」KPI,風格相依用。**
- **Phase 3 refine(用戶 4 點,尚未定稿):**(1)scope = 主題發現漏斗(RS群聚/新thematic ETF/敘事頻率/人工)+ 生命週期維護 + additive-mechanism 閘,非靜態全圖;(2)thesis KPI 四家族 = **moat/bottleneck + 資本配置/ROIC + 估值/期望值 + 成長耐久**(統一框架 Expectations Investing);(3)顛覆創新跨板塊(禮來/GLP-1 = offense,非 Healthcare 防禦)——offense = 有 additive mechanism 的新興主題 value-chain,不限 tech;(4)value-chain 建構 = A 人工 seed + B 揭露抽取(逐字稿/營收拆分/10-K,每邊引用)、**拒絕 C 價格共動**;加工管線 6 步 collect→extract(typed+cited claim)→assemble(知識圖非 GNN)→filter(materiality)→formulate(Tree 可證偽假設)→track。pilot = AI/Data-Center 或 GLP-1。
- **組成/輪動/技巧曲線大調查(2026-07-01,`results/2026-07-01_portfolio_oracle.md` / `_rotation_challenge.md` / `_skill_curve.md`):** 用戶挑戰「單標的擇時 vs 現金」是錯框架——真問題是**投組組成**(有限資本配去哪個候選)。做了完整調查:
  - **Oracle 天花板**:週度完美輪動 top-3 = 155% net、top-1 = 327%(vs SPY 8.6%)——離散度巨大。
  - **因果輪動失敗**:動能(週/月)、雙動能+債券,全部淨輸 SPY/EW;只砍回撤(又是風控)。
  - **用戶反駁「頻率 mirage」成立→我收回**:payoff by rank 顯示**第 2 名 141%、第 3 名 76%(16x/9x SPY)——不用完美**;reward-vs-skill 曲線**極度凸:forward IC 0.05 就淨贏 SPY、0.10 翻倍**。
  - **但量化排序技巧 ≈ 0**:28 個 Alpha158 家族因子 forward IC sweep(+ Bonferroni + composite + SVD)= **0/28 過關**,最強 mom52 IC 0.033(過不了)。**Qlib=更多同源 price/volume,SVD 找變異非預測(PC1 IC≈0)。price/volume 這扇門關死。**
  - **🎯 整個系統重構成一個可證偽靶**:**找一個 forward IC ≥ 0.05 的排序訊號**;唯一未測、合理可能有增量的來源 = **質性資訊(新聞/催化劑/財報/bottleneck)= Phase 3**。**Phase 3 的成功標準 = thesis 排序的 forward IC ≥ 0.05(可前瞻量測、可證偽)。** breadth 小、IC 0.05–0.1 是硬門檻(專業量化才 0.02–0.05),零證據任何可及訊號能過,但報酬凸性 justifies 去找。
- **agent 對用戶的提醒(Charter 角色)**:持續加結構層可能是「方法論救贖」的高級拖延;edge 在 Phase 3,別無限延後;每個 sleeve 要對標「無腦抱 QQQ」淨成本/稅後。

---

## 9. Phase 3 設計定稿(2026-07-01 session,詳見 `thesis/DESIGN.md`)

**edge 實證定位**:20+ backtest 證 price/volume 量化 = 風控非 alpha;逆向工程 oracle → **可捕捉 edge = 讀 regime + 催化劑 + 供需**(top-20 事件週全對得上有名有姓的宏觀事件;yearly-hold oracle ≈2×SPY;skill-curve:forward IC 0.05 就贏 SPY)。**「價格圖裡沒有 OPEC 減產/疫苗成功/underinvestment 這些資訊」→ 質性 = Phase 3。**

**NHITL 對齊(關鍵)**:原始目標「執行層全自動、拿掉人的情緒」。四元素**全可量化**:分類(regime/板塊/cycle/event/A型危機)、夠早(估值分位+供給回應+擁擠=priced-in 閘)、風控(invariants+kill+sizing)、**confidence(不是「信念」!)= f(4-KPI, 佐證數, 距kill, payoff, regime契合)→ 對戰績校準成真機率 → sizing**。**「信念」是系統要消滅的 FOMO,換成可算+可校準的 confidence。** 唯一人/嚴格閘 = 採納「新 thesis 類型」的驗證閘(原始設計已有)。**基建(FTS 語料+wiki+MCP+LLM 抽 KPI)= NHITL 的實現機制,不是分心。**

**兩型 offense**:B 主題超級週期(供給受限+需求+定價權+催化劑;能源2021/Memory2026/GLP-1/AI-電力-銅-鈾;讀供需);A 危機救援(VIX>40+最慘系統板塊+政策;讀恐懼,VIX+回撤可算,已驗 COVID/GFC)。

**知識層(規模分層)**:原料語料→**SQLite FTS**(百萬級,法律 MCP 16萬判例已證);綜合→**markdown+`[[]]`+git wiki**(幾千頁,引用進語料不複製);介面→**MCP server(agent-agnostic:Claude Code/Roo/Codex)**。檢索照法律 MCP `search.py` 的 `research_cases`(**df 收割=anti-noise + concept-coverage=regime-conditioning + good-law=判類比對現在 regime 算不算數**,確定性非向量)。原料分級:逐字稿/財報/價量=一手 Tier1;分析報告=待驗意見 Tier2;新聞=事件訊號 Tier3。

**事件引擎(唯一值得早做的重基建)**:歷史類比 → regime-conditioned base rate,解「新事件 n=1 驗證太慢」。語料 = **FNSPID(1999-2023、15.7M 新聞+價格、已對齊、已釋商用)**——補 defeatbeta 新聞只 15 個月的死點。**做薄版先驗。**

**驗證(非 backtest)**:新事件當下用「事前框架+kill 護欄」(非數字);流程層 forward-IC(1-2年,背景健檢非閘);賭注層期望值/命中率/CAR/kill 紀律(凸 payoff,~20-30 個才有話說);confidence 對這些校準。

**護欄(重新校準)**:陷阱不是「建系統」(那是 NHITL 目標),是「無限完美化、永不部署」。**做到能自動跑就上線→部署→迭代→校準。**

**選型**:知識層採 **claude-obsidian 架構/慣例(不綁其 skills)** + 借 llm_wiki 圖相關性;拒絕 WeKnora/PandaWiki(向量/server 重,違確定性哲學)。**agent 可攜靠 MCP server(照 VR pattern),不綁 Claude Code。**

**建造順序**:精簡先行(4-KPI 清單 + 一個 `[[]]` thesis 頁 + web 研究 + 風控四件套 + 戰績簿,現在就紙上下注)→ pilot 端到端 → 薄版事件引擎 → 重基建只在需求拉時才建、且時間盒。

**Phase 3 pilot 已建(2026-07-01,可跑):** `thesis/` 骨架 + memory-supercycle thesis(4-KPI cited、真 capex/PE 證據、cycle=late、confidence 0.35)→ `spine/providers.thesis_quality` 讀 `thesis/themes.yaml` → tier-2 分數 = 資格 × confidence(memory 100→35)。`thesis/log_predictions.py` 系統自動寫 track_record;`backtest/experiments/exp_memory_cycle.py` 價量版事件 base rate(極端延伸中位 -6.1%=別追)。

**維護/延續層(讓「下一個 session / 任何 agent」都會維護):** **不裝 claude-obsidian**(綁 Claude Code + 外部依賴);改**原生**:`thesis` skill(`.claude/skills/thesis/SKILL.md`,可被自動發現;借 claude-obsidian 的 `/wiki`·`/autoresearch`·`/think` pattern,但**拿掉 `/think` 的「FEEL」**——違反 NHITL,換成 NHITL 紀律迴圈)+ `AGENTS.md`(repo 根,給 Roo/Codex 跨 agent)+ `thesis/lint.py`(斷連結/孤兒/pending)+ `thesis/.raw/`(餵進的原文,可溯源)。**Obsidian(app)可直接開 `thesis/` 看 `[[]]` 圖,零安裝那 repo。**
- **v2 其他**:Phase 2 Compass overlay(資金流/敘事/macro)、flow 訊號(gamma/CTA/F&G)當未驗證 overlay;選做:RSI-2 從 tier-1 scorecard 真拆出、issuer-CSV 完整持股、marketcap.py 現為 dead fallback。

---

## 10. 2026-07-01 晚 ~ 2026-07-03(本節補上 §7-9 之後的全部進度)

**07-01 晚 → 07-02:**
- **Insider 家族已建**(SEC EDGAR Form 4,`thesis/insider_edgar.py` + 每週日排程重建快取);驗證:**21d 真 edge(t=5.12),63d 歸零/126d 轉負 → 短期催化,非長期**。
- **thesis 擴到 9 個 Type-B 主題**(`thesis/themes.yaml`);forward-IC 每日排程上線(`Karst-forward-IC-daily`,平日 09:00)。
- **Family validation 方法學修正**:IC/long-short 對 long-only 系統是錯的鏡子;long-only「持頂五分位 vs SPY」下 momentum/RS/RSI-2 全部顯著贏(RSI-2 +12.5% CAGR 超額)→ 反轉舊判決。⚠️ 現任成員 = survivorship,超額被高估。
- **VCP 三輪回測 = 無增量 edge**(pattern/sharpely/SEPA;A/B + swing horizon)→ 不編碼進 Layer-2(negative,結論在 ARCHITECTURE §3 與 git log;⚠️ verdict 未存 results 檔)。
- `docs/finance-method-distillation-spec.md`(蒸餾 skill 規格)。

**07-03:**
- **Web dashboard 上線**(`web/`,compute/serve 分離,Zeabur/Docker headless 路徑;`KARST_DATA_SOURCE=defeatbeta` toggle)。
- **Regime/fear-greed 研究(12 findings,詳 `HANDOFF.md`)**:牛熊≠風險 regime(兩軸,背離=頂/底標記)、credit>VIX、VIX=恐懼進場計/F&G=貪婪出場計(別平均)、triple-confirmation 失敗、fear/greed MR ≈ B&H(α≈0)→ **資本效率視角反轉詮釋**:部署期 conditional Sharpe 1.0-1.7 > B&H → 乾火藥部署計時器,非 SPY 替代;**alpha = T1 擇時技巧(全正)+ T2 結構拖累(指數自我擇時必負)** → tier-1 評估不用 Jensen alpha(用 IC/資本效率/PnL÷曝險/conditional Sharpe/DD/正交性)。
- **全系統審查(3 份 `docs/2026-07-03_*.md`)→ P0 級接線問題,未修**:① insider `conf_eff` 算了從未接回分數(`expression.py:66` 用原始 `th.unit`);② credit 軸/兩軸背離缺席;③ 校準迴路斷(log_predictions 從未寫入、outcome 回填程式不存在);④ IC≥0.05 只是文字。**`docs/ROADMAP_AGENTIC.md` 用戶已全部核准**,下一步 = A1(校準資料流)+ B1(價格庫)並行。
- **用戶確認:香港稅務居民**(無 CGT、美股股息 30% 預扣)→ 稅後比較用 HK 參數。
- **Workspace 重組**:37 個 exp_*.py → `backtest/experiments/`(含索引 README);**`STATUS.md` 成為唯一入口**;`.agents/sessions/` 日誌正式停用(由 KARS_MEMORY §8-10 + STATUS.md 取代);params/lenses 的過時內容已加更正註記(PMCC 移除、VCP 否定)。
- Agent 工作制度立檔:`~/.claude/playbooks/`(調度/判斷/模板/維護)+ 重寫的全域 CLAUDE.md。

---

## 11. 2026-07-04(Vanessa session)—— 詳見 `docs/2026-07-04_progress_and_next.md`

- **定位更正(用戶明示):** Karst = **獨立、自足系統,自己找 edge(自建 Phase 3)**。廢除「三大腦 / Karst=執行臂 / edge 不在 Karst」framing(已清 `README`/`ARCHITECTURE`/§1/`AGENTS`)。Compass/Tree 只是外部參考。舊 `.agents/USER.md`(個人被動收入目標)**已刪**——與專案目的無關、會誤導。
- **「未證明」精確界線:** 已證=市場擇時(資本效率)+ 輪動獎品事件驅動;**未證=前瞻捕捉那獎品(Phase 3,IC≥0.05,0 戰績)**。Phase 3 前瞻本質**不可能等統計驗證才用**(後追=edge 已消失);forward-IC 是健檢非部署閘。
- **Backtest 全盤點完成** + **off-book 重跑存檔**(`results/2026-07-04_insider_family_revalidate.md`,S&P500 離線版):insider 大型股 21d t2.30/63d t2.91;四大家族 RSI-2 long-only **+12.5% 重現**(momentum +9.9%/RS +8.6~10.2%/low-vol −1.5%)。兩者**未到「高」**(insider 只大型股;family survivorship)。
- **Bug 修正(實驗檔):** `exp_insider_validate`/`exp_family_validate` 的 `_DATA` 路徑(reorg 後指錯)+ 死快取 None 永不重抓(改 `cache.get(t) is None`)。**weekly cron 冇壞**(`thesis/insider_edgar.py` 未搬)。`px_defeatbeta.pkl` 全 None,需本機 defeatbeta 重抓(bug 已修,一 run 即補全宇宙 → 預期 insider 21d t≈5.12)。
- **升級到「高」的做法(通用):** 分設計/考試期(walk-forward)+ 真實成本 + 除 survivorship(point-in-time 成員)+ 多重檢定校正;期權類只能 Black-Scholes 理論定價(無真實期權鏈)→ 上限「中高」。
- **用戶溝通偏好:** 香港白話中文、少術語/縮寫、個人投資者(不提「容量」caveat)。「乾火藥部署計時器」改叫「**入市時機訊號**」。

---

## 12. 2026-07-05/06(Vanessa session)—— Phase-2 收官 + Trend-Core value-chain 更新 + Fable 交棒

- **Trend-Core(gooptions)re-scrape = Phase-3「3b 發現」loop**:`thesis/download_gooptions.py` 抓新 9 篇(#138-146)→
  更新 5 個 value-chain wiki(commit `50bcb2e`)。**AXTI「唯一便宜錨」糾正(3 處)**:#141 顯示 AXTI 蝕錢 / fwd PE 72.8× /
  峰值盈利假象,唔再係乾淨便宜入口。新結構節點:photonics 光纖↔PIC 耦合(#138)、adv-pkg 冷卻內化+HBM base-die 代工
  (#140/#142)、tpu interactive 端(#145)。tpu 護城河再定義 =「開源模型 GPU-shaped」非 CUDA(#146),領先指標 = Gemma。
  **9 個 confidence 全部不變**(佐證/糾正,非 re-score)。
- **Phase-2 市場層 flow 收官**(`results/2026-07-05_phase2_flow.md` + `_breadth_reversion.md`):
  - **breadth 洗盤 reversion 真**(修正舊「breadth 冇用」——嗰個只對 LEVEL 線性成立):底 decile / ≤27% above50 →
    21d +2.58%(≈3× baseline)、**短線(21d)喺 VIX 之上加 +2pp**、**單邊**(頂唔會插、做空頂實證冇值、減 drift 後仍然)、
    真形狀 = U 形(中間 ~50% breadth 最差)。對實際股災底核實無誤(GFC VIX80/breadth1.6%、COVID VIX82/2.5%、2011/2022/2025)。
    但短命(63d 被 VIX 吸)、同 VIX/RSI-2「買恐慌」重疊 → 確認尺、非新獨立 alpha。
  - **淨結論**:大市層 flow ≈ VIX 冗餘,只有 DIX(慢 tilt)+ breadth-washout(短線執底)兩個小 tilt 加值 → **收官**。
    餘下價值(板塊/子板塊 breadth + 背離 + 群體行為;大市層背離已證冇用)= **Phase-3 rider**,需 value-chain 成份定義。
- **下一步 = Fable 5 交棒(用戶定,2026-07-06)**:Fable 做 adversarial reviewer + orchestrator(大腦、rate-limited →
  spawn 平價 sub-agent 做 backtest/research);brief 見 `docs/2026-07-06_fable_brief.md`。任務 1-5 優先(驗 wiki/找 gap →
  砌 core 投資策略 = SPY/QQQ/SPMO 期權 + Sector ETF 擇時/現金,portfolio concept,**誠實用 Jensen alpha 對 SPY B&H**、
  ~3 approach + 明確 transition、scenario 執行計畫 + backtest),6 dashboard 設計、7 Phase-3 方法論審查、8 emerging bottleneck。
  **用戶關鍵 framing:core(大盤+板塊 ETF)= 大部分資金;Phase 3 = 衛星(高風險高回報)。core 唔使做英雄,要有效率 +
  期權 overlay 加少少真 alpha。**

---

## 13. 2026-07-06(Fable 任務 1-2:全庫 adversarial 驗證修正)

- **舊結論正式撤銷/降級(檔已修,詳 `docs/2026-07-06_wiki_verification.md` + `_gap_conflict_register.md`)**:
  ① 「credit>VIX」(§10)已被 07-05 `market_regime_2d` 推翻——credit 剔除,ROADMAP A2 作廢;
  ② insider「t=5.12」= 全宇宙 micro-cap tail;大型股 21d 拉長到 2006 得 t1.1(只 2022+ 有);可靠版 = 細價 12月 portfolio vs IWM;
  ③ RSI-2 top-quintile「+12.5%」補 DSR 0.908<0.95 caveat(方向可信、幅度打折);
  ④ wiki §5.2 曾誤植 F&G 數做 RSI-2 數(已正);「VIX>30→+5-6%」untraceable,換 VIX>28 牛+9.0%/熊+5.9%;
  ⑤ **code 真相**:vol regime 開關「已 live」係假(spine 冇,研究版 only);VIX×趨勢 2D 閘只有 input、無 quadrant 邏輯;
  DIX/washout 未接;RSI-2 裸奔(無 RS-leader/vol gate);conf_eff 仍 display-only;outcome 回填仍不存在;
  **兩個唔一致 logger 寫同一個 track_record.jsonl**(forward_ic.py log_predictions vs log_predictions.py run);
  params 文檔 vs code:CSP DTE 30↔21、LEAP roll 90↔63。
- **新回測(補 gap)**:`results/2026-07-06_leap_delta_sweep.md`(DRAFT,SPY 1996-2026,RV-proxy IV):
  **LEAP delta 0.80 深 ITM 全面贏 0.3/0.5/0.7**(每 gate/每半/每敏感度 Sharpe 第一;0.3Δ 槓桿×2.4 但 theta ×8,
  sleeve 級爆倉)→ 用戶「0.3 最好」記憶 = short-call 條腿(0.30Δ 21DTE),唔係 LEAP。真 VIX/QQQ 本機重跑先 bankable。

## §14 2026-07-07/08 — 真數據重做定案(sandbox 產出全部 superseded)+ 營運新件

- **上面 §13 引用嘅三份 07-06 檔已全部【SUPERSEDED】**:wiki 驗證 / gap 登記 / core 策略一律睇 **v2**
  (`docs/2026-07-06_wiki_verification_v2.md`、`_gap_conflict_register_v2.md`、`_core_strategy_v2.md`)。
  Draft delta sweep 嘅「0.80Δ 全格贏」**喺真 ^VIX 數據唔成立**(RV-proxy 冇 crash-vega);但 0.30Δ 嘅
  +15.7pp headline 一半以上又係 constant-m 誤映射 artifact(兩個 model 錯法相反)——終審:hostable =
  0.70-0.80Δ,勝出格 = **C-monthly top-up / b15 / Δ0.50 / SPY+QQQ mix**(保守 α +6.5pp t3.1 / base +12.4 t5.4),
  詳 `results/2026-07-06_leap_real_sweep.md`(+終審 Addendum)/ `_core_assembly_real.md` / `_core_topup.md`。
- **Core v2 鐵律**:引用 α 必 base/damped 並列;純 200SMA GATED(RSI-2 dip 閘已降級——miss V 反彈);
  月度 top-up 係 alpha 命脈(cash-starved 53%→10%);板塊三假設 + crash-switch 換底倉全部真數據判死
  (`_sector_capeff.md`、`2026-07-08_crash_switch.md`);底倉標的 A/B:QQQ 底倉=beta 賭注,SPMO watchlist
  (`2026-07-07_base_mix.md`);操作手冊 `docs/2026-07-07_core_playbook.md`。
- **YAML 坑(themes.yaml)**:`note:` plain scalar 含「空格+#」(如引用 #150)會被當 YAML comment 截斷
  → **note 一律雙引號包住**。lint.py 會爆 parser error 提示。
- **新排程**:`Karst-gooptions-daily`(schtasks,每日 09:10)行 `thesis/daily_gooptions.cmd`:抓 gooptions.cc
  新報告(resumable)→ 重建 source stubs(覆寫式=設計內,stubs 必須薄)→ 自動 commit。log:
  `thesis/.raw/gooptions/cron.log`。首跑抓咗 #147-150 並已 ingest(macro-risk 頁 + 4 主題 evidence 更新,
  confidence 全部維持;SKHY 掛牌後先入 universe)。
- **再加兩個排程(07-08)**:`Karst-playbook-daily`(平日 09:15,core v2 判定表 → `playbook_log.txt`)、
  `Karst-transcripts-daily`(每日 09:20,Backtest-Everything 增量抓 → 新片排入 Reference
  `_PENDING_ANALYSIS.md` 等 session 蒸餾;首批 59-62 已蒸餾:married-put 佐證 core v2「底倉唔買保護」、
  0DTE「100% win」判唔採納 multiple-testing)。四個排程總表喺 STATUS.md「每日自動化」節。
- **cmd 檔坑**:`.cmd` 註解一律 ASCII——cmd.exe 用 cp950 讀 UTF-8 中文字節,撞正 0x26(&)字節會
  把 REM 行斬開當指令執行(daily_transcripts.cmd 首版中招,已修)。中文註解放 .py docstring。

## §15 2026-07-13 —— 「Karst should be user agnostic」原則確立(crypto governance 撤回事件)

- **事發**:Fable review(P0-3)寫「crypto 治理缺口」係系統缺陷,建議加 ETH/SOL 監察 ladder +
  下行/時間出口。Karst 照做咗一個 `thesis/crypto_governance.py`(硬編碼用戶個人 ETH/SOL 成本價,
  排入 05:43 daily automation),**用戶即日撤回**:①「唔賣就唔算realise loss」係經過深思嘅立場
  (`docs/2026-07-08_transition_plan.md` §8 已記低 2026-07-08 知情拒絕下行/時間出口,「唔再重提」)——
  加監察/alert 本質上都係推佢去諗「幾時應該賣」,同呢個立場方向相反,唔止係「加咗個功能」咁簡單;
  ②**用戶明確原則**:「Karst should be user agnostic」——**個人持倉/成本價/具體資產呢類數字,
  唔應該硬編碼落 Karst 系統層嘅自動化 pipeline**。
- **確立嘅通用原則**:Karst 嘅「大腦」(spine/scan、Phase-3 thesis 邏輯、sizing 公式、dashboard)
  要**邊個攞去跑都出到同一個建議**,唔應該綁死某一個用戶嘅具體持倉/成本/現金流狀況。個人化嘅嘢
  (crypto 持倉、稅務身份之外嘅個人現金流、具體訂單簿)住喺 `docs/2026-07-08_transition_plan.md`
  呢類 **🔒PERSONAL** 文件層,**唔進系統自動化 code**。呢個同 `docs/2026-07-12_all_active_design_
  response.md` 已經確立嘅「sizing 一律 %NAV,唔係 $」原則同一脈——兩者都係「系統邏輯同個人現況
  分層」嘅具體案例。
- **執行**:script/cmd/schtask 已刪、`.gitignore`/`STATUS.md`/architecture doc §5 已改返映呢個判定
  (由「已修缺陷」改做「非缺陷,已撤回」)。**下次 Fable/agent 建議「加個人化監察」呢類功能之前,
  應該先問:呢個屬於系統層(user-agnostic)定係個人層(PERSONAL doc)?**
