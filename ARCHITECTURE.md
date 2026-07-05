# Karst — 系統架構(single source of truth)

> 每日 top-down、NHITL(no-human-in-the-loop)投資決策支援系統。這份是**跨 Phase 的架構真相**;
> Phase 3 的方法論細節見 `thesis/DESIGN.md`,操作程序見 `.claude/skills/thesis/SKILL.md`。
> 最後收斂:2026-07-01。

---

## 1. 是什麼:top-down 漏斗 + 雙層輸出

```
Phase 0 市場閘 ── Phase 1 板塊+RS ── Phase 2 資金流/敘事(未建) ── Phase 3 質性 thesis ── Phase 4 擇時
   (regime)         (價格選股)          (capital-flow)              (信念,非價格)          (何時扣扳機)
                                                                                              │
                                     ┌────────────────────────────────────────────────────────┘
                                     ▼
                        雙層輸出(two-tier expression)
       ┌────────────────────────────────┬─────────────────────────────────────────┐
       │ tier-1 = SPY / QQQ / SPMO       │ tier-2 = 其他所有個股                      │
       │ → 選擇權工具箱                   │ → 只做多(Long only,個股不做選擇權)        │
       │   LEAP / SHORT_CALL→PMCC / CSP  │   結構資格分 × RSI-2 擇時                   │
       └────────────────────────────────┴─────────────────────────────────────────┘
```

輸出單位 = **card**(每檔每日一張)。tier-2 card = 一檔只做多個股「該不該進、多少信念、是不是好時機」的
完整決策卡(結構分 + thesis conf/cycle + RSI-2)。前門:`python backtest/scan.py`。

---

## 2. Phase 地圖 + 狀態

| Phase | 做什麼 | 狀態 | 程式 |
|---|---|---|---|
| **0 市場閘** | 指數 regime + fragility → gate(能不能開新倉)| ✅ live | `spine/context.py` |
| **1 板塊 + RS** | 板塊溫度(市值加權 + cap-equal 背離)+ 兩層 RS + GICS 11 輪動 | ✅ live | `spine/sector.py`, `rotation.py` |
| **2 資金流/敘事** | 資金流 / 敘事 / macro overlays(自建;可參考外部素材) | 🔴 **未建(刻意延後)** | — |
| **3 質性 thesis** | 價值鏈→ticker→一手驗證→crowding→confidence(0..1 sizing 乘數)| ✅ live(9 個 Type-B)| `thesis/`, `spine/providers.py` |
| **3e A 型危機 tail** | VIX>40 + 被打爛系統板塊救援 sleeve | 🔴 未建 | — |
| **4 擇時** | 對已通過結構的名字,何時扣扳機(獨立欄,**絕不乘進結構分**)| ✅ live(RSI-2)| `spine/timing.py` |
| **forward-IC 評估** | Phase 3 的裁判:confidence 是否 rank-order 未來報酬 | ✅ live(累積中,數月才有判)| `thesis/forward_ic.py` |
| **知識層** | 102 篇 FTS 語料(①)+ 88 源節點(②)+ wiki(③)| ✅ live | `thesis/corpus.py`, `build_source_nodes.py` |

---

## 3. Signal-family → Phase 地圖(settle 版)

**決定歸屬的鐵律 —— 「在不在價格圖裡」防火牆:**
- **在價格圖裡**(RS、動能、RSI-2、突破、VCP)→ 量化/價格層 **Phase 0 / 1 / 4**。
- **不在價格圖裡**(thesis、insider、催化劑、敘事)→ **Phase 3**。混價格訊號進 Phase 3 =
  破壞其立論(edge 來自圖裡沒有的資訊),**禁止**。
- **regime / 定位**(VIX、GEX)→ **Phase 0**。

| 家族 | 歸屬 Phase | 現況 |
|---|---|---|
| **Trend/Momentum** | Phase 1(VCP 趨勢模板=選股)+ **Phase 4(突破觸發)** | 🟡 SPMO 動能在閘;**突破已回測(2026-07-05:20日高突破>TSMOM>SMA,兩半贏B&H、修H1)未接線**;**VCP 型態已測=無增量/輕微傷**(3次一致,`results/2026-07-05_vcp_pattern.md`);動能=downside protection 非 alpha(`results/2026-07-05_breakout_momentum.md`)|
| **Mean Reversion(RSI-2)** | **Phase 4** | ✅ 純價格股權進場(不拿去買選擇權)|
| **Volatility / VRP** | Phase 0 / 選擇權側(IV-rank)| ✅ tier-1 CSP/SHORT_CALL |
| **Relative Strength** | **Phase 1**(Sector RS + Stock-RS-in-sector,**兩層都在此**)| ✅ `rs_vs_market` + `member_rank.rs_vs_parent` |
| **Flow: Insider** | **Phase 3**(非價格、知情人行為)| ✅ **已建** — v2 **SEC EDGAR Form 4**(`insider_edgar.py`,真交易碼:只留 P 買/S 賣、剔除 A/M/F/G/10b5-1 機械交易;離線快取 `insider_cache.json`)+ yfinance fallback(`insider.py`)。bounded ±30% conf 修正。**v3 待補:routine/opportunistic 分類(Cohen 2012,需多年逐人歷史)** |
| **Flow: GEX(aggregate)** | **Phase 0**(SPY/QQQ fragility)| ⚫ **測完唔建**(2026-07-05:免費 SqueezeMetrics GEX 對 VIX partial≈−0.08 無增量,`results/2026-07-05_gex_test.md`);VIX/credit/RV 已 subsume;DIX 免費細 flow 訊號可選 |
| **Gamma Walls(strike-level)** | tier-1 期權側 level/zone context | 🟢 **live 工具建咗**(`exp_gamma_walls.py`:SPY/QQQ/板塊/Mag7 支持/阻力區+強度+企穩線,0DTE/1W/1M;yfinance 免費 live,無歷史→forward-log 驗證;`docs/2026-07-05_gamma_walls.md`)。當 zone/regime context 唔當 alpha |
| **Flow: Dark-pool/UOA** | (存疑,暫不排)| 🔴 我判定多為噪音,先不做 |

---

## 4. Phase 編號對照(避免混淆)

**兩套編號不同,別搞混:**

| | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|---|---|---|---|---|---|
| **Karst spine(本檔)** | 市場閘 | 板塊+RS | 資金流/敘事 | 質性 thesis | 擇時 |
| **CIO_IDEAS.md** | 證明 1 家族 edge(deflated Sharpe>0.5)| 擴到 4 家族 ensemble | top-down 層疊 | 部署 CLI/Web | — |

⚠️ **CIO Phase 0 的「per-family 正式驗證」我們跳過了** —— 直接建了 spine,沒逐家族 walk-forward /
deflated Sharpe。這是已知的嚴謹度缺口(見 §6)。

---

## 5. 5 家族的誠實評估(objective,不護航)

實證地基(本專案 ~20 backtest):**天真價量因子一鍋煮 forward IC ≈ 0**(風控,非 alpha)。但**個別、
有紀律、regime-gated、表達正確的異象家族有真(溫和、低容量、衰減)的 edge**。兩者不矛盾。

| 家族 | 誠實評分 | 關鍵實話 |
|---|---|---|
| Momentum | 因子真(Jegadeesh-Titman)但**會崩 + 擁擠**;VCP/SEPA 品牌方法**無獨立驗證、被高估** |
| Mean Reversion | 真但**邊際/衰減(HFT 套光)/regime 脆**;只配當 gated 擇時 overlay,非獨立 alpha |
| VRP | **最扎實的溢價**,但**負偏賣保險**;98% 勝率是風險不是 edge;sizing+尾避才是全部 |
| Relative Strength | **不獨立(就是動能)**;輪動擇時前瞻上多是幻覺;當廣度/regime 讀比當 alpha 有用 |
| **Insider** | **最真、最耐、最難套利** —— 整批的寶石 |
| GEX / Dark-pool | GEX 當 fragility 真、當方向 alpha 錯;**dark-pool 多為噪音+行銷** |

**三句 bottom line:**
1. **「勝率」在這裡一律是騙子**(RSI-2 84% / CSP 98.6% / insider 93% = 負偏,小賺大賠)。看期望值與尾部。
2. 全部已發表、已擁擠(發表後衰減 30-50%);散戶拿得到的版本(RSI-2/VCP/UOA/GEX)是**衰減最兇**的。
3. **這 5 家族最好的定位是「被風控過、不會爆的更好 beta 底座」,不是 alpha 來源。** 差異化 alpha 在
   **Phase 3 質性 thesis**(讀因子湯裡沒有的供需/regime/催化劑)。**家族防你爆,thesis 給你那一擊。**

---

## 6. 已建 / stub / 延後 + open items

**✅ 已建:** Phase 0/1/4 spine · Phase 3(9 Type-B thesis **+ Insider 家族**)· 知識層(FTS+源節點+wiki)· forward-IC + 每日排程 · scan 全 9 叢覆蓋(市值加權 + 背離)。

**🔴 未建 / 缺口(依價值):**
1. **突破觸發 → Phase 4**(補 RSI-2 覆蓋盲區,帶量確認)。
2. **GEX → Phase 0**(SPY/QQQ fragility)。
3. **per-family 正式驗證(CIO Phase 0)—— 第一輪已跑**(`backtest/experiments/exp_insider_validate.py` +
   `exp_family_validate.py`,SEC bulk Form345 + defeatbeta 價格,look-ahead-safe,forward IC + deflated
   Sharpe)。發現:**Insider 有真「21d」edge(t=5.12)但 63d 歸零/126d 轉負 → 短期催化非長期**(⚠️ 與
   現在的長期 ±30% overlay 接線 **horizon 不符,待改成短期 tilt**);**RSI-2 mean-rev 最強**(IC t=6-12
   兩宇宙皆穩、DSR 0.91,驗證 Phase-4)。
   **⚠️ 方法學修正:IC/long-short 對 long-only 系統是錯的鏡子。** 用「long-only 持有頂五分位 vs SPY
   買入持有」(S&P 1995-2026)測:**momentum +9.9% / RS-126d +10.2% / RS-63d +8.6% / RSI-2 +12.5%
   CAGR 超額**(low-vol 輸)。→ **RS/動能「持有領頭羊」強勝指數;先前用 IC/LS 判它們無 edge 是測錯了
   (空方弱股反彈拖垮 LS)。Karst tier-2 是 long-only → 這才是對的鏡子。** caveat:現 S&P 成員 =
   survivorship,超額被高估;+成本/換手打折。`exp_family_validate.py` 兩種鏡子都有。
4. 背離 → confidence 自動 temper;個股 >200SMA 才認 RSI-2 dip。
5. **Phase 2(資金流/敘事)**、**A 型危機 tail** —— 較大,待決策。
6. 14 篇未歸類分流(軟體/網通種子);各 thesis 頁 `待補`(LTA 記分卡追蹤/逐字稿/FNSPID)。
   內部人 cluster-buy(USAR/LOAR/TSM)可反饋強化對應 thesis 的 confidence(手動或自動)。

**紀律不變量(INV-*):** 見 spine 程式碼註解;INV-5(板塊內落後者只在 US 名判)、INV-8/9(個股不做選擇權)等。

---

## 7. 東西在哪

| 主題 | 位置 |
|---|---|
| 每日掃描前門 | `python backtest/scan.py [--json]` |
| spine(0/1/4 + 路由)| `backtest/spine/` (context, sector, rotation, universe, timing, expression, providers, orchestrator) |
| Phase 3 設計 / 操作 | `thesis/DESIGN.md` · `.claude/skills/thesis/SKILL.md` |
| thesis 登記(機器可讀)| `thesis/themes.yaml` ← **ticker 的單一真相**;`universe.yaml` 用 `thesis:` 自動拉,不重抄 |
| 知識層 | `thesis/corpus.py`(FTS)· `wiki/`(源節點+綜合頁)· `.raw/`(原文,gitignore)|
| forward-IC 裁判 | `thesis/forward_ic.py` + `daily_ic.cmd`(Windows 排程 **每日** log)|
| insider 快取 | `thesis/insider_edgar.py build` + `weekly_insider.cmd`(Windows 排程 **每週日** 重建 EDGAR 快取)|
| Windows 排程任務 | `Karst-forward-IC-daily`(平日 09:00)· `Karst-insider-weekly`(週日 08:00)—— `schtasks /Query` 查 |
| 外部 idea 索引 | `../Reference/CIO_IDEAS.md`(注意編號與本檔不同,見 §4)|
| agent 續傳入口 | `AGENTS.md` · `.agents/KARS_MEMORY.md` |
