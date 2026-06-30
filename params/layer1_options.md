# Layer 1 — 期權結構參數

> 標的層已決定「該有 exposure」之後,本檔決定「用什麼期權結構表達」。
> 全部 **ETF only(SPY / QQQ / SPMO)**——backtest 鐵律:期權策略在個股上死得很慘。

Tag:✅ verified(對過 transcript) / 📄 distilled(待複核) / ⚠️ open(待解決)

數據源根目錄:`../../Reference/raw_data/backtest_everything_transcripts/`
蒸餾:`../../Reference/distillations/2026-06-24_backtest-everything-distillation.md`

---

## 0. Universal Options Principles(所有結構通用)

| 原則 | 數據 | Tag | 來源 |
|---|---|---|---|
| 賣保費 > 買保費 | 每個系統性買 option 策略都虧;long strangle −$31,521 | 📄 | dist §6.4 `OiTIRvCzw8g` |
| 30 DTE >> 1 DTE | iron condor 差距 $28,660 | 📄 | dist §4.1 `W_2y4SLVBs0` |
| 10Δ > 16Δ > 20Δ(賣方) | IC 差距 $17,000 | 📄 | dist §4.2 `ozPuGv0IkWI` |
| 50% profit target | IC beat hold ~$4K | 📄 | dist §4.5 `w8VcWe6cG80` |
| **stop loss 傷害賣方策略** | 移除 0DTE SL:−$6K → +$14K | 📄 | dist §9.1 `FvWWkKuSyps` |
| 只在 medium VIX(15–25)賣 | low VIX −$6,396(陷阱) | 📄 | dist §4.3 `DJyMPW2tQc0` |
| ticker 選擇 > 策略選擇 | 同策略 NVDA 賺 / TSLA 虧 | 📄 | dist §4.7 |

---

## 1. CSP(Cash Secured Put)— Core Layer-1 主力

| 參數 | 值 | Tag |
|---|---|---|
| 標的 | **QQQ** | 📄 |
| delta | **20Δ** | 📄 |
| DTE | 30 | 📄 |
| 出場 | 50% PT,no SL | 📄 |
| 結果 | **+$8,656,98.6% WR,PF 5.94,max DD 2%** | 📄 |

來源:dist §2.2 / §2.6 `BXZZC3S-A68`。QQQ 20Δ 賺超過 SPY 最佳值 2 倍以上;98.6% WR
維持到 20Δ。

⚠️ **尾部:** 單筆 COVID(2020-03)虧 ~$8,000 = 吃掉整年保費。Position sizing 必須
熬過單筆災難 → 見 `invariants`(單筆 CSP ≤ 20%、總 assignment ≤ 50%)。

---

## 2. PMCC(Poor Man's Covered Call)— SPY only

| 腿 | 參數 | Tag |
|---|---|---|
| **Long leg** | **deep ITM 0.70Δ**(可接受 0.70–0.80),≥365 DTE,90 DTE roll | 📄 |
| **Short leg** | **0.30Δ,30 DTE,50% PT** | 📄 ⚠️ |
| 結果(SPY) | +$9,698,short call 78.5% WR,144 trades | 📄 |

來源:dist §1.6 `ojwJu-Fz1zg`。

🔴 **只跑 SPY。** TSLA −$28,479、AAPL −$2,332——高波動把 short call 在 rally 中
壓垮。PMCC 不碰個股。

🔴 **Long leg 為何必須 deep ITM(結構,非偏好):** 要 short strike 永遠在 long strike
之上才有 defined risk。若 long leg 用 0.30Δ(價外),short strike 可能落在 long strike
下方 → 無上限虧損區間。**這就是 idea-07 §6.2 的錯**(見 §5)。

⚠️ **open — short leg delta:** Covered call 600-config 回測(dist §3.3)說 SPY/QQQ
低波標的用 **0.2Δ + hold-to-expiration**(不 roll)最佳;PMCC 慣例是 0.30Δ + 50% PT。
兩者有張力,待回測在 PMCC 結構下重測。

🔴 **隱藏 vega(idea-07 風險 2):** LEAP 的 vega 遠高於持股,vol spike 可在標的沒
大跌時重創 LEAP。→ `invariants`:VIX > 30 / GEX 翻負 = 減倉 PMCC。

---

## 3. 方向性 LEAP(裸買 long call,非 PMCC)

> ✅ **這是 transcript 01 實際測的東西**——裸買方向性 long call、無 short call、
> 持 6–12 個月。與 PMCC long leg 是**不同策略**,參數不可互換。

兩種風險取向:

### (a) Deep ITM 0.70–0.90 —— Karson 目前實際做法

| 特性 | 值 | Tag |
|---|---|---|
| WR | 高(0.90Δ ≈ 78% WR) | ✅ |
| 報酬 | 較低(用 6× 報酬換勝率 + 抗回撤) | ✅ |
| 適用 | 資金效率版的正股替身 |  |

成長股偏 0.90Δ(TSLA 0.90Δ +$126,970、AAPL 0.90Δ 85.7% WR PF 6.66);
穩定標的(SPY / NVDA)偏 0.70Δ。來源:dist §1.4 `8MjtHJ6i9_k`。

### (b) Low delta 0.30–0.50 —— 高報酬高勝率代價

| 特性 | 值 | Tag |
|---|---|---|
| 最佳 | **QQQ 0.30Δ hold-to-exp = 169%,PF 5.22,57% WR** | ✅ verified `-aQCEO_MPU8` |
| 條件 | **必須 hold-to-exp、不可設 stop loss、只在上升趨勢** |  |
| 風險 | 6× 報酬 vs deep ITM,但 57% WR |  |

🔴 **致命前提:** dist §1.5 `0DLMKE6HpFE` 證明——一旦加 stop loss,deep OTM LEAP 會在
回調(2018/2020/2022)被洗掉,deep ITM 反而因有內在價值存活。**(b) 與 stop loss
互斥。** 這跟 Charter「LEAP 只右側 + hold-to-exp」的 invariant 一致。

> **決策:** (a) vs (b) 是自覺的「報酬 vs 勝率 vs 抗回撤」取捨。Karson 現用 (a)。
> Karst 兩者都記錄,依 use case 選。

---

## 4. Iron Condor(可選補充 — regime 互補)

| 參數 | 值 | Tag |
|---|---|---|
| 標的 | **SPY**(❌ 不要 QQQ:太波動 −$9,017) | 📄 |
| 結構 | 10Δ short,30 DTE,50% PT | 📄 |
| Gate | **VIX 15–25,no stop loss** | 📄 |
| 結果 | **+$18,186,77% WR,43% max DD(全場最低)** | 📄 |

來源:dist §4.14 `BlvQLYEz3JY`。定位:long-vol regime 的互補(IC 是 short vol,
與 calendar 之類 long vol 反相關)。

---

## 5. idea-07 修正記錄(別重蹈)

`../../Reference/ideas/2026-06-24_idea-07-pmcc-csp-core.md` 內部自相矛盾:

- §2 寫 `LEAP delta ≈ 0.8`(✅ 對,PMCC 標準)
- §6.2 寫 `PMCC LEAP 0.30-0.50 delta`(🔴 錯,把 standalone LEAP 參數誤植)

**根因:** transcript 01 測的是 §3 的「方向性 LEAP」,不是 PMCC long leg。0.30Δ 對
裸買做多有效,對 PMCC long leg 會破壞 defined-risk 結構。Karst 把這拆成 §2 與 §3
兩條獨立 line-item,不再混用。

---

## 6. Open Items(待回測 / 待複核)

- [ ] PMCC short leg delta:0.30Δ(慣例)vs 0.20Δ hold-to-exp(CC 回測)——重測
- [ ] FOMC 週是否暫停賣方(idea-07 提到 FOMC 賣保費虧 $3,337)——複核 transcript
- [ ] 所有 📄 tag 回 transcript 複核(目前只有 transcript 01 完成 ✅)
- [ ] CSP / PMCC 在 SPMO 上的行為(distillation 未涵蓋 SPMO)
