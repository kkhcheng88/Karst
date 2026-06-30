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
- **首個回測結論(✅ 自驗,已解 200SMA 未決項):** 指數上 RSI-2/200SMA **贏不了 B&H 報酬**,只能砍回撤 → **標的層 TA timing = 回撤 overlay,非 alpha;真 edge 在期權結構(VRP)**。重現不了 distillation §11.5。見 `backtest/results/2026-06-30_rsi2_200sma.md`。
- 下一步候選:Phase-2 option overlay(BSM + VIX/VXN,測 CSP/PMCC/LEAP P&L 含 vega)、或 Dorsey/Minervini 蒸餾、或定義 INV 數值。
