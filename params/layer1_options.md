# Layer 1 — 期權結構參數

> 標的層已決定「該有 exposure」之後,本檔決定「用什麼期權結構表達」。
> 全部 **ETF only(SPY / QQQ / SPMO)**——backtest 鐵律:期權策略在個股上死得很慘。

Tag:✅ verified(對過 transcript) / 📄 distilled(待複核) / ⚠️ open(待解決)

> ⚠️ **架構更新(2026-06-30 scorecard v3.1,本檔未全面改寫)**:**PMCC 已從 tier-1
> 工具箱移除**(long leg ≡ LEAP,兩腿拆開:LEAP 買在 RSI-2 dip / SHORT_CALL 賣在
> RSI-2 超買)。本檔的 PMCC 章節保留為歷史推導與參數出處;現行工具 =
> LEAP / SHORT_CALL / CSP / CASH,見 `backtest/scorecard.py` docstring 與
> `backtest/results/2026-06-30_shortcall_timing.md`。

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
| 賣方擇時**分結構**(別一概而論) | IC → medium VIX(§4);CSP/bull put → **low IV rank**(§1) | ✅/📄 | 56/57 + dist §4.3 |
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

✅ **擇時(IV rank)— video 56/57 `AJ3hFgKUptE`/`FO2Yq7to0lc`,2,865 trades:**

| IV rank | 結果 |
|---|---|
| **Low(0–25%)** | **91.2% WR,+$24,556,PF 1.58** — 最佳 |
| Medium(25–50)| −$8,885 ❌ |
| High(50–75)| −$7,986 ❌ |
| Very high(75–100)| +$4,720,PF 1.69(樣本僅 193,小)|

U 型,low IV rank 大幅最佳。原因:CSP/bull put 是**方向性看多**,在平靜上升趨勢(low IV)
最賺,不是靠高 IV 收大保費。**規則:在 low IV rank 賣,避開 25–75 死區(INV-4b)。**

🔴 **推翻**:(a) guru「只在高 IV 賣」;(b) 本助手早期口頭講的「CSP 在 high IV rank 賣」——
backtest 證明相反。
⚠️ **別與 §4 IC 的「medium VIX」混淆**:IC 是 short-vol/range(用 absolute VIX level);
CSP 是 directional(用 IV rank),結論相反。不同 metric、不同結構。
⚠️ 影片測的是 bull put **spread**;CSP(naked secured)同族,合理外推,但 tail 無下方保護。
⚠️ 殘留尾部:low IV rank 偶爾出現在 crash 前(2020 初)→ 靠 sizing(INV-1/2)兜底。

🟡 **2026-06-30 自驗(`backtest/results/2026-06-30_csp.md`,provisional/cost-sensitive):**
引擎重現 94–97% WR(對齊 distillation)。**但 CSP 的 alpha 不顯著(t<1.8)——94% WR 與
$76k 利潤大半是 beta(短 put ≈ +0.2 delta),不是免費 VRP alpha**;net of cost 的 VRP 很薄。
**唯一亮點:RSI-2<10 dip 進場**(PF 2.9–3.4、AvgDD −0.8%、SPY alpha t1.8)→ **在超賣 dip 賣
CSP**,進場 alpha 可疊。⚠️ low-IV-rank(56/57)在裸 CSP 沒穩定重現(幫 QQQ、傷 SPY),
且結論對成本假設(1.5%/側)敏感——待 cost sweep。

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

🟡 **2026-06-30 自驗(`backtest/results/2026-06-30_leap_timing.md`,provisional):**
LEAP **需要擇時**,但只需「右側閘」:`price > 200SMA` 才開槓桿(= INV-6)。always-in
LEAP = **破產(MaxDD −99.9%)**;加 200SMA 閘把 MaxDD 拉回 ~−70% 且報酬 ~翻倍。
**機制確認(槓桿部位的擇時 = 防破產);但 CAGR 數字是樂觀 artifact(VIX 當 1yr IV、
成本過低、單一路徑),且即使有閘 MaxDD 仍 ~−70% → 小倉位。** 待 harden 後才釘死數字。

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
