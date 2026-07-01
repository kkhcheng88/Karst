---
slug: memory-supercycle
type: B
cycle_stage: late
confidence: 0.35
verdict: real-but-late
updated: 2026-07-01
tickers: [MU, SNDK, STX, DRAM]
links: [[AI-demand]] [[HBM]] [[advanced-packaging]] [[pricing-power]] [[underinvestment]]
sources: [defeatbeta:ttm_pe, defeatbeta:holdings(DRAM), price:MU/SNDK/STX, web:HBM-demand]
---

# Memory 超級週期(B 型)— real but LATE

> pilot thesis 頁。confidence = INITIAL, uncalibrated(冷啟無 track record)。當「有紀律的相對強弱 +
> 週期溫度」讀,別當精確機率。

## 一句話
記憶體(DRAM/HBM/NAND)是**真的供給受限 + AI 需求爆發 + 三寡頭定價權**的 B 型超級週期——**但已晚期**
(估值極度延伸 + DRAM ETF 剛上市=擁擠 + HBM 產能開始回應)→ **不追高,盯頂訊號。**

## 4-KPI(每條 cited)

### 1. moat / bottleneck — 強(2/2)
- **三寡頭**:DRAM ETF 持股顯示 SK Hynix (~25%) + Samsung (~16%) + Micron/SNDK/Kioxia 主導 → 高集中度
  寡頭(來源:`defeatbeta holdings(DRAM)`,session 開場已驗)。
- **瓶頸 = HBM / 先進封裝(CoWoS)**:AI GPU 要 HBM,HBM 產能受先進封裝限制 → 真 bottleneck(來源:
  web:HBM-demand;需再從逐字稿抽管理層受限語言補強)。
- **定價權**:短缺期三寡頭有定價權,margin 擴張。→ 強,但**是週期性定價權**(供給回來就消失),非永久。

### 2. 資本配置 / ROIC — 中偏弱(1/2)+ 頂訊號 ✅ 已確認
- **MU capex 一年內狂飆 ~2.7x**:$2.94B(2025-05)→ 4.05 → 5.66 → 5.39 → 6.39 → **7.83B(2026-05)**
  (來源:`defeatbeta quarterly_cash_flow`,2026-07-01 拉)。**這是「供給回應」頂訊號的教科書確認**——
  多年 underinvestment 正在反轉、產能在加速 → 超級週期末段特徵。同時 capex 吃 FCF → 資本配置近期偏弱。
- STX capex 也升($0.04→0.16B);SNDK 平($0.04B,較 asset-light)。

### 3. 估值 / 期望值 — 中(1/2)⚠️ 修正我的初估錯誤
- **修正**:我原寫「估值極端 0/2」**講太滿**。實際 `defeatbeta ttm_pe`(2026-07-01 拉):
  **MU ttm_pe 26,自身 5y 分位僅 53%(中段!)**;STX 92(74%);SNDK 79(27%,史短不可靠)。
- **為什麼價格 +165% 但 PE 中段?因為 supercycle 讓盈利也爆** → **這正是週期股的經典頂陷阱:
  peak earnings 讓 PE 看似正常,週期一轉盈利崩、PE 飆、股價崩**(估值研究:「低 PE 在盈利峰 = value trap」)。
- 所以估值 KPI 不是「明著貴」,而是「**peak-earnings 讓它看似不貴,但那就是頂**」。→ 中,仍壓 confidence。

### 4. 成長耐久 / TAM — 中強(1.5/2)
- AI/HBM 需求是**真且 additive**(HBM 是新 TAM,不是搶份額)→ 強。
- **但記憶體是週期性,不是軟體那種 secular**;需求耐久性受 AI capex 週期牽制 → 打折。→ 中強。

## cycle_stage = LATE(三頂訊號,現在有真資料)
| 訊號 | 現況 |
|---|---|
| 供給回應 ✅ **最強、已確認** | **MU capex 一年 2.7x($2.94→7.83B)** = 產能加速上線 = 教科書頂訊號 |
| 擁擠 ✅ | **DRAM(Roundhill Memory)ETF 2026-04 剛上市** = 主題被市場確認 + 晚期擁擠訊號 |
| 估值 🟡(修正)| PE **中段**(MU 53%),但 **peak-earnings 讓 PE 看似不貴 = 週期頂陷阱**;價格延伸 +114~232% |

→ **供給回應(capex 狂飆)是最硬的頂訊號,已用真資料確認 → LATE 站得住。** 進場的鏡像條件
(便宜 + 供給仍緊 + 未成共識)**全不成立**(供給正在回應、ETF 已上市)。

## confidence 推導(可追溯,已用真資料修正)
```
KPI:  moat 2/2 · capital 1/2(capex 吃FCF+頂訊號)· valuation 1/2(PE中段但peak-earnings陷阱)
      · growth 1.5/2                                    = 5.5/8 = 0.69 base
cycle penalty (LATE, capex頂訊號已確認 → 更該壓): × ~0.5   → 0.34
佐證: capex ✅ + ttm_pe ✅ 已拉(修正了初估);逐字稿受限語言 + FNSPID 頂類比仍待補 → 不加分
→ confidence ≈ 0.35  (INITIAL, uncalibrated — 冷啟無 track record)
```
**讀法:真主題(moat/需求強)但晚期已確認(capex 頂訊號)+ peak-earnings 估值陷阱 → 壓到 0.35。
相對強弱有、但別追高;要吃就 DRAM ETF 小注,盯 kill(capex 超前需求轉過剩)。**
**⚠️ 紀律示範:拉真資料修正了我「估值極端」的初估錯誤(PE 其實中段),同時 capex 確認了晚期。**

## 歷史 base rate(薄版事件引擎,價量版)
`backtest/exp_memory_cycle.py`(2026-07-01):記憶體股(MU/STX/WDC 長史)按「距 200SMA」分桶的 fwd-126d:
| dist band | 中位 fwd% | % 為正 | n |
|---|---|---|---|
| 無條件 | +8.6% | 56% | 27,563 |
| +50~100%(適度延伸)| **+14%** | **61%** | 2,019 |
| **+100%..(像現在:MU +165%/STX +115%/WDC +124%)** | **-6.1%** | **44%** | 158 |

→ **極端延伸的歷史 base rate:中位虧、不到一半贏**(vs 適度延伸的中位 +14%/61%)。**實證支持「晚期、別追高」。**
高均值(+53%)是肥尾(偶爾續噴)= 凸 payoff,但**中位說別追**。⚠️ 小 n(158)、價量版、倖存者偏差;
乾淨版需 FNSPID + regime-conditioning(見 DESIGN §5)。

## kill_condition
> HBM / 先進封裝(CoWoS)產能 ramp **超前** AI 需求(轉過剩)**或** 三寡頭定價紀律破裂。
> 觸發 → 出場 / confidence 歸零。

## 表達
- **可交易**:MU / SNDK / STX(US),DRAM ETF(板塊級,含買不到的 SK Hynix/Samsung)。
- **晚期 → 小注 + 盯頂**;若要吃這主題,DRAM ETF 比追單一延伸個股穩(分散)。

## 待補(降低「未確認」扣分)
- [x] ✅ `defeatbeta` MU capex 趨勢(2.7x = 供給回應頂訊號)— 2026-07-01 拉。
- [x] ✅ `ttm_pe` 分位(MU 53% 中段 = peak-earnings 陷阱,修正了初估)— 2026-07-01 拉。
- [ ] 逐字稿抽管理層 HBM 受限/定價語言(moat 證據補強)。
- [x] ✅ 「過去記憶體週期頂」價量 base rate — 見 `backtest/exp_memory_cycle.py`(價量版,不需 FNSPID)。
- [ ] FNSPID 撈同期新聞全文接地(深化)。
