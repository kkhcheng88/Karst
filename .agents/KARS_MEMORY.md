# KARS_MEMORY — 專案記憶(系統的記)

> 本檔是 Karst 的長期記憶。每次啟動先讀此檔 + `USER.md` + 最新 session,
> 不要再從 conversation summary 重建。

最後更新:2026-06-30

---

## 1. 系統地圖(同層 `C:/projects/Investment/`)

| repo | 角色 | 一句話 |
|---|---|---|
| **Compass** | WHY | 質性大腦 + 紀律 + Charter + regime_matrix + sector 溫度 + lenses |
| **Tree**(drawtree) | WHAT | 可證偽假設樹 + risk/reward(Bull/Base/Bear),跑在 MCP。github.com/Draw-Tree/drawtree-protocol |
| **Karst** | WHEN / HOW | 釘死的參數 + timing + 系統性風控(本 repo,cwd)|
| **Reference**(原 Quant)| 原料倉 | backtest distillation + transcripts + 抓取 script + ideas |
| **ebooks**(原 Investors)| 書庫 | 蒸餾原料(Dorsey/Porter/Minervini/Lynch/O'Neil…) |
| **Indicators** | 指標數據 | Python crawler(用途待評估) |

**edge 不在 Karst**。Karst 是執行臂。edge 在 Compass + Tree 的「假設選擇 + 殘酷證偽」。

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
