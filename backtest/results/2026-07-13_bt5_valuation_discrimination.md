# BT-5 — Expectations-Gap 估值模組判別力測試(ex-ante,判官預先寫死)

**Date:** 2026-07-13
**Script:** `backtest/experiments/exp_bt5_valuation_test.py`(可重跑)
**測試對象:** `thesis/valuation.py` v1 嘅 E_norm / P_base@14x 口徑
**Spec:** `docs/2026-07-12_valuation_expectations_gap_spec.md` Sec 3c(BT-5)
**Case library:** `backtest/results/2026-07-09_magnifier_case_library.md`

> **House 規則(硬性):判官預先寫死,唔准事後搬龍門。** 本檔結構上**判官表(§2)喺結果(§5)之前**,
> 判官表連同「預期分類方向」喺**任何 P_base 計算之前**已經 commit(見 §2 時間戳)。§5 結果只係對答案,
> 唔准回頭改判官。

---

## 1. 動機 + 測試設計

`thesis/valuation.py` v1 啱啱生產化(`backtest/results/2026-07-13_expectations_gap_v1.md`),但而家淨係
**display-only**。Spec 3b 想接 **sizing 閘**(分類「大部分係希望」P_base<0.4 且 g_implied > thesis 聲稱增長
→ 該 theme 注碼鎖 watch 級,無論 confidence 幾高)。接閘之前,BT-5 要證明呢把尺喺**已知結局**嘅歷史案例
上判得啱。

**判別力嘅定義(pre-registered):**
- **谷底/可入案例**(事後知道係大贏家嘅入場點,或最終存活嘅低位)→ 估值應該顯示「**非危險**」
  = 現價有相當比例俾正常化盈利冚得住(classification ∈ {`買緊部分希望`, `supercycle 白送`},即 P_base ≥ 0.4)。
- **頂部/爆煲案例**(事後知道係高位崩 / 破產)→ 估值應該顯示「**危險/貴**」
  = 現價大部分係希望、正常化盈利冚唔住(classification ∈ {`大部分係希望`, `N/A-binary (option framing)`},
  即 P_base < 0.4 或 E_norm ≤ 0)。

**單案 PASS 準則(pre-registered):** 谷底案判「非危險」= PASS;頂部案判「危險」= PASS。相反 = FAIL。
**閘準則:** **6/6 全中 → 過閘(可接 sizing);< 6 → 唔過(留 display-only)。**

### 1a. 案例選取 + 誠實邊界(數據約束,揀案發生喺計算之前)

Spec 3c 原本建議嘅六案(MU 2016 / MU 2023 / FSLR IPO / STP IPO / WOLF / SMCI)有一半**無法用
point-in-time 數據測**,原因係硬數據約束,已於揀案階段(計算之前)查明:

| Spec 原建議案 | 可測? | 原因 |
|---|---|---|
| MU 2023 谷底 | ✅ 可測 | defeatbeta 年度回溯到 FY2019,2023 谷底當時有 FY2019-2022 可用 |
| WOLF(頂 / 爆煲) | ✅ 可測 | 2021-11 頂,當時有 FY2019-2021 |
| SMCI(頂) | ✅ 可測 | 2024-03 頂,當時有 FY2020-2023 |
| MU 2016 / MU 2018 頂 | ❌ 無法測 | defeatbeta 年度損益表只回溯到 **FY2019**;2016/2018 數據源冇 |
| FSLR IPO(2006)/ STP IPO(2005)| ❌ 無法測 | 同上(年度 FY2019 地板);STP 已下市,defeatbeta 完全無數據 |
| COHR 2021 高位 | ❌ 無法測 | defeatbeta COHR = II-VI/Coherent Corp 世系(FY2020 起),同 2021 高位嘅舊 Coherent Inc 係**實體錯配**(併購改名污染) |

**代替原則(唔係遷就分數,係遷就數據可得性):** 深歷史 / 已下市案用**同方向**、defeatbeta 有 point-in-time
數據嘅案頂替,且**喺計算之前**寫死。谷底方向補 WDC 2022-12(記憶體同週期存活者)、FSLR 2022-07(IRA 前低點,
太陽能存活者);頂部方向補 NVO 2024-06(GLP-1 贏家變輸家,-56% 乾淨崩,case library 明列)。**唔會**喺睇到
P_base 之後再換案。已下市中國太陽能純商品爆煲組(STP/LDK/YGE/Q-Cells)= case library 最典型爆煲教材,但
**全部已下市、defeatbeta 零數據 → 誠實標「無法測」,由 WOLF(現代 SiC 爆煲、2025 Chapter 11、defeatbeta 有數)
做同方向代表**。

---

## 2. 判官表 —— 先寫死(pre-registered @ 2026-07-13,計算之前)

> **以下六案嘅「測試日 + 預期方向 + 單案 PASS 準則」喺任何 P_base 數值計出嚟之前已經 commit。**
> 預期方向由 case library 記錄嘅**已知結局**決定,同財務數據無關(谷底股事後 23x = 可入;頂部股事後崩 = 危險)。

| # | 案名 | 測試日 | 類型 | 已知結局(case library) | **預期方向** | 單案 PASS = |
|---|---|---|---|---|---|---|
| 1 | **MU**(Micron)| 2022-12-30 | 谷底 | $49.98 谷底 → 2026-06 $1,154.29(**23.1x**),存活者 | 非危險 / 可入 | P_base ≥ 0.4(`買緊部分希望`/`白送`)|
| 2 | **WDC**(Western Digital)| 2022-12-30 | 谷底 | $23.85 谷底 → 2026-06 $638.72(**26.78x**),存活者 | 非危險 / 可入 | P_base ≥ 0.4 |
| 3 | **FSLR**(First Solar)| 2022-07-01 | 谷底 | IRA(2022-08-16)前低點,其後 CdTe 護城河存活者、post-IRA 大升 | 非危險 / 可入 | P_base ≥ 0.4 |
| 4 | **WOLF**(Wolfspeed)| 2021-11-16 | 頂部 / 爆煲 | ATH $141.87 → **2025-06 Chapter 11**,舊股東實質全損 | 危險 / 貴 | P_base < 0.4 或 N/A-binary |
| 5 | **SMCI**(Super Micro)| 2024-03-13 | 頂部 | $118.807 頂 → 2024-11 $18.01(**-85%**),會計醜聞 | 危險 / 貴 | P_base < 0.4 或 N/A-binary |
| 6 | **NVO**(Novo Nordisk)| 2024-06-25 | 頂部 | 頂 $142.74(ATH $146.91)→ **-56%**,CagriSema 失望、贏家變輸家 | 危險 / 貴 | P_base < 0.4 或 N/A-binary |

**平衡:** 3 谷底(全部應顯示正覆蓋)+ 3 頂部(WOLF 蝕錢 → 預期 N/A-binary 觸發;SMCI/NVO 有盈利但貴
→ 真正考 P_base<0.4 門檻,唔係 trivial 蝕錢旗)。板塊分散:記憶體(MU/WDC)、太陽能(FSLR)、SiC(WOLF)、
AI-server(SMCI)、GLP-1(NVO)。

---

## 3. 方法 —— valuation.py 口徑(照抄),年度數據 point-in-time 版

valuation.py v1 用 defeatbeta **季度**數據,但季度只回溯 ~2022-06(見 §1a),深度不足以做歷史 point-in-time。
本測試**照抄 valuation.py 嘅公式口徑**,但把「季度中位數」換成「**年度中位數**」,因為 defeatbeta 年度數據
回溯到 FY2019(足以覆蓋六案測試日)。呢個係唯一嘅適配,明寫如下:

```
# valuation.py 原口徑(季度)                    # 本測試(年度 point-in-time)
margin_median = median(季度 OI/Rev, 全部季)  →  median(年度 OI/Rev, 全部「已申報」財年)
ttm_rev       = 最近 TTM 收入                 →  最近一個「已申報」財年收入
rev_3y_median = median(最近 12 季收入)×4      →  median(最近 3 個「已申報」財年收入)
revenue_used  = min(ttm_rev, rev_3y_median)   →  min(最近財年收入, 3 年財年中位收入)   [同 v1 保守項]
E_norm        = margin_median × revenue_used
NOPAT_norm    = E_norm × (1 − 0.21)
net_debt      = Total Debt − Cash&STI(最近「已申報」財年資產負債表)
EV            = market_cap(測試日 point-in-time)+ net_debt
P_base@14x    = NOPAT_norm × 14 / EV
classification: ≥0.8「supercycle 白送」/ 0.4-0.8「買緊部分希望」/ <0.4「大部分係希望」/ E_norm≤0「N/A-binary」
```

**market_cap 係真 point-in-time:** 用 defeatbeta `market_capitalization()` 時序(每日 close_price ×
歷史 shares_outstanding,回溯到 1994),取測試日當日 / 之前最近一筆。已核對:MU @2022-12-30 = $54.54B
= $49.98 × ~1.09B 股,吻合。

**FX(僅 NVO):** NVO 報表幣別 = DKK。DKK 財務數據 × **測試日 point-in-time** DKK/USD 匯率(yfinance
`DKKUSD=X`,2024-06-25 收 = 0.143895)轉 USD;market_cap 本身已係 USD(ADR)。**唔用今日 spot**(避免
look-ahead)。其餘五案全部 USD 報表,無 FX。

---

## 4. No-look-ahead 聲明(逐案:用咗邊啲截止日期嘅數據)

**紀律:** 一個財年只有喺佢嘅 10-K **會喺測試日之前申報**先納入 → 規則:FYE + 90 日 ≤ 測試日(大型
加速申報者 60-90 日內申報,90 日係保守安全線)。market_cap 只取測試日當日 / 之前。**唔用測試日之後
任何數據。** 逐案納入財年:

| 案 | 測試日 | 報表 FYE | 納入財年(10-K 截 90 日內已申報)| 用嘅資產負債表 | market_cap 日 |
|---|---|---|---|---|---|
| MU | 2022-12-30 | 8/31 | FY2019, FY2020, FY2021, FY2022(FY2022 FYE 2022-08-31 +90d = 2022-11-29 ≤ 測試日)| FY2022(2022-08-31)| 2022-12-30 |
| WDC | 2022-12-30 | 6/30 | FY2019, FY2020, FY2021, FY2022(+90d = 2022-09-28 ≤ 測試日)| FY2022(2022-06-30)| 2022-12-30 |
| FSLR | 2022-07-01 | 12/31 | FY2019, FY2020, FY2021(FY2021 +90d = 2022-03-31 ≤ 測試日;FY2022 未 FYE,排除)| FY2021(2021-12-31)| 2022-07-01 |
| WOLF | 2021-11-16 | 6/30 | FY2019, FY2020, FY2021(+90d = 2021-09-28 ≤ 測試日)| FY2021(2021-06-30)| 2021-11-16 |
| SMCI | 2024-03-13 | 6/30 | FY2020, FY2021, FY2022, FY2023(+90d = 2023-09-28 ≤ 測試日;年度損益表 FY2020 起)| FY2023(2023-06-30)| 2024-03-13 |
| NVO | 2024-06-25 | 12/31 | FY2019-FY2023(FY2023 +90d = 2024-03-31 ≤ 測試日)| FY2023(2023-12-31)| 2024-06-25 |

**共同排除:** 每案測試日之後嘅任何財年 / 季度 / 價格一律唔用。DKK/USD 用測試日匯率(NVO)。

---

<!-- ===== 以下 §5 結果 section:計算之後填,判官表已於上方 §2 寫死 ===== -->

## 5. 結果(對答案)

判官表(§2)寫死之後,`exp_bt5_valuation_test.py` 逐案 point-in-time 計出 P_base@14x。

### 5.1 每案計算過程 + 當時數據

| 案 | 測試日 | 納入財年 | margin 中位 | revenue_used(口徑)| E_norm(USD)| NOPAT | net_debt | market_cap(PIT)| EV | **P_base@14x** | 分類 |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| MU | 2022-12-30 | FY2019-22 | 28.0% | $29.23B(3yr 中位,damped)| $8.17B | $6.46B | −$1.81B(淨現金)| $54.54B | $52.72B | **1.715x** | supercycle 白送 |
| WDC | 2022-12-30 | FY2019-22 | 9.9% | $17.86B(3yr 中位,damped)| $1.78B | $1.40B | +$4.70B | $7.61B | $12.30B | **1.596x** | supercycle 白送 |
| FSLR | 2022-07-01 | FY2019-21 | 13.5% | $2.82B(3yr 中位,damped)| $379.8M | $300.1M | −$1.43B(淨現金)| $7.26B | $5.84B | **0.720x** | 買緊部分希望 |
| WOLF | 2021-11-16 | FY2019-21 | **−39.8%** | $525.6M(最近財年)| **−$209.3M** | −$165.3M | −$315.5M | $16.49B | $16.17B | **−0.143x** | N/A-binary(option framing)|
| SMCI | 2024-03-13 | FY2020-23 | 5.0% | $5.20B(3yr 中位,damped)| $258.1M | $203.9M | −$150.2M | $67.19B | $67.04B | **0.043x** | 大部分係希望 |
| NVO | 2024-06-25 | FY2019-23 | 42.6% | $25.34B(3yr 中位,damped;DKK×0.14319 PIT FX)| $10.80B | $8.53B | −$461.6M | $654.30B | $653.84B | **0.183x** | 大部分係希望 |

**計算讀法:**
- **MU / WDC 谷底 = 白送**:記憶體谷底,價格被殺($49.98 / $23.85)令 EV 細,而 median margin 抽自
  含 FY2021-22 好景嘅正常化盈利 → 正常化 NOPAT × 14 反而**大過 EV**(P_base > 1)。呢個正正係谷底應該
  顯示嘅「現價深度被正常化盈利冚住」。WDC 帶 $4.70B 淨債(EV > 市值)都仍然 1.60x,證明 EV 口徑有捉到
  槓桿(市值單睇會更平)。
- **FSLR 谷底 = 買緊部分希望(0.72x)**:IRA 前公允估值嘅存活者入場點,唔係 MU/WDC 式深谷底大平賣,
  但 ≥0.4 = 非危險,方向正確。
- **WOLF 頂 = N/A-binary**:SiC ramp 常年蝕錢(median margin −39.8%)→ E_norm ≤ 0 → 冇正常化盈利可錨,
  $141.87 ATH 嘅價 100% 係希望冇盈利地板 → 危險。其後 **2025-06 Chapter 11**、舊股東實質全損,兌現。
- **SMCI 頂 = 大部分係希望(0.043x)——強測**:SMCI **有盈利**(margin 5%),但 $67B 市值下正常化盈利只
  冚住 4.3% EV → 唔係 trivial 蝕錢旗,係 P_base<0.4 門檻真捉到「有盈利但貴到大部分係希望」。其後 -85%
  (會計醜聞)——貴估值本身就係脆弱性。
- **NVO 頂 = 大部分係希望(0.183x)——強測**:NVO 勁賺(margin **42.6%**、真 GLP-1 利潤),但 $654B 市值
  下正常化盈利只冚 18.3% → 連怪獸級 margin 嘅質優股喺頂位都被判「大部分係希望」。其後 -56%(CagriSema 失望)。

### 5.2 對答案表(pre-registered 判官 vs 實計)

| # | 案 | 測試日 | 類型 | 預期方向 | 實計 P_base | 實計分類 | **判定** |
|---|---|---|---|---|---:|---|---|
| 1 | MU | 2022-12-30 | 谷底 | 非危險(≥0.4)| 1.715x | supercycle 白送 | ✅ **PASS** |
| 2 | WDC | 2022-12-30 | 谷底 | 非危險(≥0.4)| 1.596x | supercycle 白送 | ✅ **PASS** |
| 3 | FSLR | 2022-07-01 | 谷底 | 非危險(≥0.4)| 0.720x | 買緊部分希望 | ✅ **PASS** |
| 4 | WOLF | 2021-11-16 | 頂部 | 危險(<0.4/N/A)| −0.143x | N/A-binary | ✅ **PASS** |
| 5 | SMCI | 2024-03-13 | 頂部 | 危險(<0.4/N/A)| 0.043x | 大部分係希望 | ✅ **PASS** |
| 6 | NVO | 2024-06-25 | 頂部 | 危險(<0.4/N/A)| 0.183x | 大部分係希望 | ✅ **PASS** |

### 5.3 結論 —— 過閘

**6/6 全中 → 按 §2 pre-registered 準則,過閘:valuation.py 嘅 P_base@14x 可以接 sizing 閘**
(Spec 3b:分類「大部分係希望」P_base<0.4 → 該 theme 注碼鎖 watch 級)。三個谷底 / 存活者入場點全部
顯示正覆蓋(2 白送 + 1 部分希望),三個頂部 / 爆煲名全部顯示危險(2 大部分係希望 + 1 N/A-binary);
最有資訊量嘅係 SMCI / NVO —— **有盈利、甚至怪獸級 margin,但喺頂位仍被 P_base<0.4 門檻正確判危險**,
證明呢把尺唔係淨靠「蝕錢 = 危險」嘅 trivial 訊號。冇 fail 案。

### 5.4 殘留風險(過閘唔等於無限制,誠實列明,唔搬龍門)

1. **判別力有機械成分**:P_base = 正常化盈利 ÷ EV,價低(谷底)自動高、價高(頂)自動低。谷底 3 案某程度
   係「價殺咗自然覆蓋高」。真正加值(超越裸 P/E)喺:(a)normalized(median margin × 保守 revenue)平滑週期;
   (b)EV 口徑捉槓桿(WDC 淨債、MU 淨現金);(c)SMCI/NVO 兩個**有盈利貴頂**被門檻捉到 —— 呢三點先係測試
   真正證到嘅嘢。
2. **谷底案集中 2022**:MU/WDC/FSLR 三谷底同屬 2022 宏觀底,MU/WDC 更同屬記憶體週期。板塊分散(記憶體/太陽能)
   但時點集中;未涵蓋非-2022 谷底。
3. **年度數據 ≠ valuation.py 季度口徑**:因 defeatbeta 深度限制(季度 ~2022-06、年度 FY2019),本測試用年度
   中位數代季度中位數(§3 明寫)。分類門檻相同,但六案結果全部**遠離 0.4/0.8 邊界**(最近係 FSLR 0.72 vs 0.8、
   SMCI 0.043 vs 0.4,均有充足餘量),故適配對判定穩健;若某案卡邊界,季度/年度差異可能翻轉,要逐案覆核。
4. **Spec 原案有一半無法測**(MU 2016/2018、FSLR IPO、STP/LDK):defeatbeta 年度 FY2019 地板 + 已下市 →
   已於 §1a 誠實標明並用同方向代案。**已下市中國太陽能純商品爆煲組(最典型爆煲教材)實際上冇被直接測到**,
   由 WOLF(現代 SiC 爆煲)做同方向代表 —— 想覆蓋 2005-08 太陽能爆煲需付費歷史數據庫(Bloomberg/CRSP),
   defeatbeta 做唔到。
5. **look-ahead 防線靠 FYE+90 日規則**:保守(多數大型加速申報 60 日內),但若某案剛好卡申報邊界,納入財年
   集合可能差一年。六案已逐案列納入財年(§4),MU/WDC/SMCI/NVO 有 4-5 財年,FSLR/WOLF 僅 3 財年(margin
   中位數樣本較薄)。

---

## 附:重跑

```
PYTHONUTF8=1 python backtest/experiments/exp_bt5_valuation_test.py
```
判官(6 案 / 測試日 / 預期方向 / PASS 準則)硬編碼喺 script 頂部 `CASES`,同 §2 判官表一致;改判官要同時改兩處
(故意設計成唔方便事後搬龍門)。
