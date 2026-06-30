# Systematic Invariants — 系統性風控(無人味版)

> Karst 是 no-human-in-the-loop 的執行層。一個沒有 discretionary entry 的系統,
> **結構上不會犯** operator 心理錯誤(FOMO / 報復 / 悶)。所以這裡只留
> **可機器檢查的系統性 invariant**,不抄 Charter 的人類心理教訓。

---

## 切一刀:Charter 兩堆

| 堆 A:operator 心理(🗑️ 丟) | 堆 B:系統性 invariant(✅ 留,改寫成機器約束) |
|---|---|
| FOMO / 報復 / 悶 / 日日 check P/L | (系統免疫,無對應) |
| 心理安全閘 | (無 discretionary entry,不需要) |
| IPO 首日「感覺」 | → INV-7:上市 < N 天不進場 |
| TTD 越跌越買 | → INV-3:禁止 averaging down 超閾值 |
| POET 揀 laggard | → INV-5:Warm sector 只取 RS top-2 |
| POET 長 option 折磨 | → INV-6:LEAP 只右側 + hold-to-exp |
| GOOGL 裸賣 | → INV-2:只賣 covered |

**教訓的「價值」保留,「以人為中心的形式」丟掉。**

---

## INV — 機器可檢查約束

| ID | 規則 | 來源 |
|---|---|---|
| **INV-1** | 單筆 CSP assignment 風險 ≤ 可投入資金 **20%** | idea-07 §6.2 |
| **INV-2** | 總 CSP assignment 風險 ≤ **50%**(確保 crash 時不被迫平倉) | idea-07 §5 |
| **INV-3** | 禁止 averaging down(martingale 防呆);單名上限固定 | TTD 教訓 |
| **INV-4a** | **IC / short-vol** 賣方:只在 **medium VIX(15–25)** | dist §4.3 |
| **INV-4b** | **CSP / bull put**(directional):在 **low IV rank(0–25%)** 賣;避開 IV rank 25–75 死區 | 56/57 `AJ3hFgKUptE` |
| **INV-5** | Warm sector 內按 RS 排名,只取 **top-2**,永不 laggard | POET 教訓 + sector_filter |
| **INV-6** | LEAP 只在 **price > 200 SMA(右側)** + hold-to-expiration | POET 教訓 + dist §1.5 |
| **INV-7** | 上市 **< N 天**(待定)的標的不進場 | FIGMA 教訓 |
| **INV-8** | PMCC / CSP **ETF only**,不碰個股 | dist §1.6 / §2 |
| **INV-9** | 只賣 covered(PMCC 結構),禁裸賣 | GOOGL 教訓 |

---

## REGIME — 風控閘(動態)

| 觸發 | 動作 | 來源 |
|---|---|---|
| **VIX > 30 / GEX 翻負** | 減倉 PMCC、暫停 CSP(vega 風險最大化) | idea-06 GEX |
| FOMC 週 | 賣方暫停 / 減倉(⚠️ open,待複核) | idea-07 §6.2 |
| 宏觀 regime ≤ 防守級 | 依 Compass `regime_matrix` 降 beta 暴露 | Compass |

---

## 自我修復:三層,且有一道閘

> 「策略會自我修復」是整個設計唯一危險處。誠實版:

1. **Decay 偵測** ✅ 全自動 — live 表現 vs backtest 期望的滾動背離
   (rolling Sharpe / WR / PF;credit spread 的 POP gap 式監控)。
2. **自動降風險 / 停 sleeve** ✅ 全自動 — 背離超閾值 → 系統性 circuit-breaker
   (非人為 discretion)。也含 black-swan 閘(資料異常 / 跳空 > X% / VIX 超界 → halt)。
3. **丟回研究迴圈重新 hypothesize→kill** ⚠️ **需驗證閘** — 偵測到衰減 → 交給
   Compass / Tree / LLM 重新推導。**新參數上線前必須過 deflated Sharpe + walk-forward
   閘(人或嚴格自動 gate)**,否則系統會自我過擬合餵真錢。

**結論:執行層可 zero human-in-loop;策略演化層必須有閘。** 別讓系統自己改參數
直接跑。

---

## Open Items

- [ ] INV-7 的 N(上市天數門檻)——定值
- [ ] INV-3 的 averaging-down 閾值與單名上限——定值
- [ ] decay 偵測的背離閾值與 lookback——定值
- [ ] FOMC 賣方暫停——回 transcript 複核是否成立
