# 2026-07-04 Session — 進度與下一步

> Vanessa session(Cowork);於 Claude Code 續。技術識別碼/ticker/檔名保留英文。
> 入口:`STATUS.md` 已更新並指向本檔。

---

## 一、本 session 做咗咩

### 1. 定位更正(重要,已改 repo)
- **Karst = 獨立、自足的全自動 agentic 投資決策系統。自己找 edge(自建 Phase 3)、自己跑決策管線。edge 就在 Karst。**
- 廢除舊 framing:「三大腦(Compass=WHY / Tree=WHAT / Karst=WHEN-HOW)、Karst=執行臂、edge 不在 Karst」——**錯的**。Compass / Tree / Reference / ebooks 只是**外部參考素材,非功能依賴**。
- 已清:`README.md`(定位節)、`ARCHITECTURE.md`(Phase 2 行)、`.agents/KARS_MEMORY.md`(§1)、`AGENTS.md`(第 3 行)。
- **未清(下個 session 可選):** `reference/README.md`(表)、`invariants/systematic_rules.md`、`params/layer2_timing.md` 裡 Compass `regime_matrix` 的營運引用。歷史 `results/`、`.agents/sessions/` **不動**(是證據記錄)。

### 2. 「未證明」的精確界線(與 Vanessa 對齊)
- **已證:** 市場層擇時(RSI-2 / 200SMA / VIX / F&G = 資本效率 + 風控);輪動獎品巨大且**事件驅動**(供需瓶頸 / 危機解決),非 quant alpha。
- **未證:** 用**可實現、因果、前瞻**訊號**捕捉**那個獎品 = Phase 3,靶心 forward IC ≥ 0.05,**0 戰績**。
- **關鍵:** Phase 3 本質前瞻,不可能「等統計驗證才用」(那叫後追,edge 已消失)。驗證模式 = 事前框架 + 可證偽 kill + 凸 payoff 的 EV(~20-30 注);forward-IC 是背景健檢,**不是部署閘**。

### 3. Backtest 全盤點(catalog)
- 19 份存檔結論 + 幾個 orphan,已分類:市場擇時 / 期權 / 輪動 / 選股 / 內部人 / 資本效率 / 型態 / spine。
- 誠實結論:多數假設在自己嚴謹門檻(DSR / walk-forward / Bonferroni)下**被殺**(disciplined negative);少數正 edge 窄而小(RSI-2 dip、short-call、部署計時器、家族 long-only)。
- 三個「off-book」結論(family +12.5%、insider 21d、VCP 否定)原本只在文件引用、**未存 `results/`**。

### 4. 重跑 + 存檔(off-book → 存檔)→ `backtest/results/2026-07-04_insider_family_revalidate.md`
離線重現(S&P500 universe,因為只有 `sp500_px.pkl` 有真價):
- **Insider**(大型股子集 189 宗):21d 超額 **+2.32%(t2.30)**、63d **+4.29%(t2.91)**、126d 中位轉負;DSR(63d)0.791。
- **四大家族**(1995-2026):RSI-2 long-only 頂五分位 **+12.5%** 重現;momentum +9.9%、RS +8.6~10.2%、low-vol −1.5%。IC:只有 RSI-2 mean-rev 顯著(t≈6)。RSI-2 long-short DSR 0.908。
- **兩者都未到「高」:** insider 只大型股 + DSR<0.95 + costless;family 有 **current-S&P survivorship**。

### 5. 修咗嘅 bug(實驗檔,已改 repo)
- `exp_insider_validate.py` / `exp_family_validate.py`:
  - ① `_DATA` 路徑(reorg 後指向不存在的 `experiments/.insider_data`,會誤觸 SEC 下載)→ 改指 `backtest/.insider_data`。
  - ② 價格快取 None 值**永不重抓**(`t not in cache` 當已快取)→ 改成 `cache.get(t) is None` 重試,令死快取可自癒。
- **weekly cron 冇壞**:`thesis/insider_edgar.py` 寫入 `thesis/`(未搬),路徑正常。
- **未修(需價格源):** `backtest/.insider_data/px_defeatbeta.pkl`(136MB,1743 keys)**全 None** = 死快取。

### 6. 環境限制(記住)
- Sandbox:Python 3.10 + scipy 1.15.3。**上唔到網**(SEC 403;defeatbeta / yfinance 裝唔起)→ 攞唔到小型股價。
- 唯一可用離線價格源:`sp500_px.pkl`(505 S&P 名 + SPY,1995-2026)。

---

## 二、下一步(優先序)

### A. 即刻可做 —— 喺 Vanessa 本機(有 defeatbeta + 網)
Bug 已修,run 以下即補小型股價、重現**全宇宙**(從 repo 根):
```
python backtest\experiments\exp_insider_validate.py
python backtest\experiments\exp_family_validate.py
```
- 會重抓約 1700 隻名(要時間)並重寫 `px_defeatbeta.pkl`。
- 完成後更新 `results/2026-07-04_insider_family_revalidate.md`:全宇宙 insider(預期 21d **t≈5.12**,小型股先夠強)+ 小型股家族。

### B. 升級到「高」(對應 session task list)
1. **選股類 point-in-time 除 survivorship**:用**當時真實 S&P 成員名單**重跑 family + Alpha360,睇 +12.5% / IC 0.017 除偏差後仲企唔企得住。需歷史成員數據。
2. **期權類 BSM + 成本 + walk-forward**:LEAP / CSP / short-call / 市場狀態。無真實期權鏈 → 用 Black-Scholes;數字須標明「理論估算」。目標「中高」。
3. **補存檔:VCP + 大盤擇時**:VCP A/B vs 普通突破;RSI-2 / 200SMA / scorecard 加 walk-forward + 真實成本。
4. (可選)出一份**總表**:測咩 ｜ 結果數字 ｜ 可信度 ｜ 點樣先到「高」(合併 catalog + 這次數字)。

### C. 清理(可選)
5. 清 `reference/README.md`、`invariants/`、`params/` 殘留的 Compass / 三大腦 framing。

---

## 三、東西喺邊
| 主題 | 位置 |
|---|---|
| 本次重跑證據 | `backtest/results/2026-07-04_insider_family_revalidate.md` |
| 系統定位(已更正) | `README.md` / `ARCHITECTURE.md` / `.agents/KARS_MEMORY.md` §1 |
| 全盤點 verdict | 本檔 §一.3 + `backtest/experiments/README.md` + `results/*.md` |
| 實驗檔 bug 修正 | `exp_insider_validate.py` / `exp_family_validate.py`(`_DATA` + None 重試) |
