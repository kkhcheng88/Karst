# 4-KPI subscore 補寫草稿 — discovery-radar 6 theme(P2 收尾第一步)

> **狀態(2026-07-16 更新):✅ 已覆核並已落地。** 本檔由「草稿」變成「已執行嘅決策記錄」——
> gatekeeper 裁決見 §6(gas moat 1.5→1.0、gas capital 保持 1.0 因 solvency 已有獨立閘唔雙重罰、
> siding 估值 0.5 定性為 blended-PE 數據質量降級);6 個 theme 嘅 subscores + confidence 已經連同
> 其餘 9 個一齊喺 commit `0ac6f3f` 全量切入 themes.yaml / wiki,lint 機械驗收通過。
> 最終整合表見 `backtest/results/2026-07-16_final_confidence_diff.md`。
> 目的:6 個 discovery-radar theme 現行 confidence 係純敘事推導(冇 4-KPI 逐格分數),套唔到
> `thesis/DESIGN.md` §4a 凍結公式。呢度按 §4a 錨點逐格補分,供遷移用。gatekeeper 覆核後,把
> 「建議 wiki 推導 block」(§4)貼入各 wiki、把 capped 值寫入 themes.yaml,再跑 `thesis/lint.py`
> 驗證(公式輸出 = themes.yaml 記錄,誤差 ±0.01)。

---

## 1. 方法

### 1.1 Rubric 引用(全部凍結於 DESIGN §4a,2026-07-15)
- **subscore ∈ {0, 0.5, 1, 1.5, 2}**,每格至少一條 cited 證據;半分要書面理由。
- **公式**:`confidence_raw = (Σ 4-KPI) / 8 × penalty(crowding_band, cycle_stage)`;
  `confidence = min(confidence_raw, 0.30)` 當 `len(sources) == 1`,否則 = raw。
- **moat / growth 硬上限 1.5**(§4b rubric 掛鈎):攞 2 分嘅前提 = 該格承重 claim 經 Level-2
  red-team 且生還(wiki 有 `red_team:` 記錄)。**呢 6 個 theme 全部未經 Level-2 red-team**
  (wiki 全部標「未做 capital-allocation/ROIC/TAM 深度研究」、只有 transcript-only 一手源),
  故 moat / growth 一律**封頂 1.5**,表內標「pending red-team,生還先可升 2」。
- **valuation 係機械格**(§4a 註):直接由 `pe_pctile`(wiki 記錄,自身歷史 3 年滾動分位)
  + `p_base`(valuation_report.json,取 theme 最佳表達 ticker)映射錨點,零自由裁量:
  - `pe_pctile < 50` **且** `p_base ≥ 0.4` → **2**
  - `pe_pctile 50–90`;**或** `p_base < 0.4` 但有資產/合約類緩衝 → **1**
  - `pe_pctile ≥ 90`;或夢想定價 → **0**
  - 插值可用 0.5 步(見 specialty-siding 嘅衝突處理,§2.5 + §5)。
- **penalty 查表**(crowding composite pctile × cycle_stage,§4a 凍結):

  | crowding \ cycle | early | mid | late |
  |---|---|---|---|
  | < 40 | 1.00 | 0.90 | 0.75 |
  | 40–60 | 0.95 | 0.85 | 0.65 |
  | 60–80 | 0.85 | 0.75 | 0.55 |
  | 80–90 | 0.75 | 0.65 | 0.45 |
  | ≥ 90 | 0.65 | 0.55 | 0.40 |

- **single-source cap**:6 個 theme `sources:` list 長度全部 = 1(`transcript-discovery-radar`,
  tier 3),**全部觸發 cap 0.30**。呢個係設計意圖:單一敘事來源(discovery-radar transcript
  掃描)嘅 thesis,注碼上限被獨立佐證數綁住;公式嘅精細分辨力主要喺 cap 以下發揮。要脫離 cap
  須 Tier-1 渠道獨立擊中**承重 claim**(constraint-language scanner / insider cluster /
  財務直證核心機制),並喺 `sources:` 登記 `corroborates:`。

### 1.2 數據讀數日期(全部落實數,唔靠估)
| 數據 | 來源檔 | 讀數日期 |
|---|---|---|
| pe_pctile(自身 3 年滾動) | 各 wiki / themes.yaml note | 2026-07-11 量度 |
| p_base(per ticker,取 theme 最佳表達) | `thesis/.raw/valuation_report.json` | as_of 2026-07-15 |
| crowding composite pctile | `thesis/.raw/crowding_composite.json` | generated 2026-07-13 |
| cycle_stage | `thesis/themes.yaml`(各 theme frontmatter) | 現行 |
| sources list 長度 | `thesis/themes.yaml`(各 theme `sources:`) | 現行(全部 = 1) |

**證據紀律**:wiki/note 冇證據支持嘅格,寧願低分 + 標「證據缺失」。以下 capital/ROIC 格全部
受「未做 ROIC/capex 深度研究」限制——用 valuation_report.json 嘅一手財務讀數(EBIT margin /
interest coverage / net_debt / solvency_flag)做**下限錨**(有盈利就唔俾 0),但因缺正式 ROIC
趨勢 + capex 紀律證據,**一律封喺 ≤1.5** 並標缺口;呢批 capital 格係全草稿最軟嘅判斷(見 §5)。

---

## 2. 逐 theme 評分

### 2.1 aerospace-specialty-alloys(現行 0.24)
- **最佳表達 ticker**:ATI(rollup best;p_base 0.237)。pe_pctile 98th(ATI/CRS 均 98th)。
- **crowding** 78.6(60–80 帶);**cycle** late。**penalty = 0.55**。

| KPI | 分 | Justification(引證據) |
|---|---|---|
| moat/樽頸 | **1.5** | ATI「supply 6/7 of the 7 most advanced jet engine nickel alloys」(2026-04-30 transcript)+ CRS re-qualification 換供應鎖客(2018-10-24)+ 19/15 年一致 LTA/capacity-constrained 第一人稱語言(wiki 證據段)。一手約束語言 + 可交易名直接持有咽喉 → 本質係 2 分料,但**未經 Level-2 red-team,封頂 1.5**(pending red-team,生還先可升 2)。 |
| 資本/ROIC | **1.0** | wiki/themes.yaml note 明文「未做 capital-allocation/ROIC/TAM 深度研究」。一手財務(valuation_report):ATI EBIT margin 中位 0.132、interest coverage 5.82、solvency_flag false → 有盈利、非燒錢,唔俾 0;但**冇 ROIC 趨勢 / capex 紀律證據** → 混合,1.0。⚠證據缺失(ROIC/capex)。 |
| 估值/priced-in | **0** | 機械格:pe_pctile 98th(≥90)→ 0;p_base 0.237(<0.4)亦指向 0。全批最貴之二。 |
| 成長/TAM | **1.0** | 需求 = 噴射引擎 build-rate(build-rate 掛鈎、非 additive 創造全新需求);LTA backlog 真但 TAM 未 sizing(wiki 待補)。機制真、兌現中但耐久靠 build-rate 週期 → 1.0(未觸 1.5 頂)。 |

base = (1.5+1.0+0+1.0)/8 = **3.5/8 = 0.4375**
penalty(78.6 → 60–80 × late)= **× 0.55** → raw = **0.241**
single-source cap → min(0.241, 0.30) = **0.241**(cap 未綁住)
**capped = 0.24 | 現行 = 0.24 | delta = 0.00**

---

### 2.2 euv-lithography-monopoly(現行 0.22)
- **最佳表達 ticker**:ASML(p_base 0.184)。pe_pctile 98th。
- **crowding** 2.8(<40 帶,全批最冷);**cycle** late。**penalty = 0.75**。

| KPI | 分 | Justification(引證據) |
|---|---|---|
| moat/樽頸 | **1.5** | 全球唯一 EUV/High-NA 微影供應商、零替代;16 年橫跨 4 週期「always constraining the business」(2010)、「12–18 月 lead time」(2019)、「sold out for 2026」(2026-04-15)。全批單股最強護城河(themes.yaml note F4/F2 全批最高)→ 本質 2 分料,**封頂 1.5**(pending red-team)。 |
| 資本/ROIC | **1.0** | 「未做 ROIC 深度研究」。一手財務:ASML EBIT margin 中位 0.328(極高)、coverage 104、net cash(net_debt −6.5B)→ 有盈利、財務極穩,唔俾 0;但**無正式 ROIC 趨勢 / capex 紀律 writeup** → 1.0。⚠證據缺失(ROIC/capex);財務質地強,reviewer 可辯 1.5。 |
| 估值/priced-in | **0** | 機械格:pe_pctile 98th(≥90)→ 0;p_base 0.184(<0.4)。全市場最人盡皆知嘅壟斷,「未被發現」溢價不存在。 |
| 成長/TAM | **1.0** | AI 驅動先進製程 capex 拉動,需求真但 ASML 經 fab capex 週期捕捉(兌現中);TAM 未 sizing(wiki 待補)。機制真、部分靠未證下一階段 → 1.0。 |

base = (1.5+1.0+0+1.0)/8 = **3.5/8 = 0.4375**
penalty(2.8 → <40 × late)= **× 0.75** → raw = **0.328**
single-source cap → min(0.328, 0.30) = **0.30**(**cap 綁住** — 因 crowding 極冷,penalty 高)
**capped = 0.30 | 現行 = 0.22 | delta = +0.08**(全批最大正 delta;主因 crowding 2.8 令 penalty 只 0.75)

---

### 2.3 us-solar-manufacturing(現行 0.32)
- **最佳表達 ticker**:FSLR(p_base 0.655)。pe_pctile 22nd。
- **crowding** 76.0(60–80 帶);**cycle** mid。**penalty = 0.75**。

| KPI | 分 | Justification(引證據) |
|---|---|---|
| moat/樽頸 | **1.5** | 232/301 關稅 + IRA 本土成分政策護城河 + CdTe 唔使多晶矽(結構性成本護城河);連續 7 年 sold-out(2019→2020 … 2023 backlog 到 2030、2026「fully allocated」);2016 自認「no pricing power」→ 今日係真 regime change(wiki 負面對照組)。可交易名(FSLR)直接持有 → 本質 2 分,**封頂 1.5**(pending red-team;政策 binary 亦係扣分理由)。 |
| 資本/ROIC | **1.5** | 「未做 ROIC 深度研究」但一手財務最強之一:FSLR EBIT margin 中位 0.315、coverage 41.7、net cash(net_debt −1.84B)。早/中週期產能建設有 backlog 到 2030 一手支持(§4a 2 分錨:「早週期買建 capex 有一手訂單/backlog 支持」)→ 給 1.5;差 formal ROIC 計算先唔到 2。⚠ROIC 趨勢未正式計。 |
| 估值/priced-in | **2** | 機械格:pe_pctile 22nd(<50)**且** p_base 0.655(≥0.4)→ 2。discovery-radar 批 priced-in 狀態最好。 |
| 成長/TAM | **1.5** | 美國本土製造 additive 需求(reshoring + 政策)已被財報兌現(sold-out through 2030、有實收入);供給結構性慢(政策護城河 + CdTe)。本質近 2,**封頂 1.5**(pending red-team;TAM 未 sizing、政策 binary)。 |

base = (1.5+1.5+2.0+1.5)/8 = **6.5/8 = 0.8125**
penalty(76.0 → 60–80 × mid)= **× 0.75** → raw = **0.609**
single-source cap → min(0.609, 0.30) = **0.30**(**cap 硬綁** — raw 遠高於 cap)
**capped = 0.30 | 現行 = 0.32 | delta = −0.02**
⚠**現行 0.32 > cap 0.30 = 現正違規 single-source cap**;合規值 = 0.30(向下修返合規,DESIGN
§4a addendum 預期嘅情況)。

---

### 2.4 gas-compression-equipment(現行 0.33)
- **最佳表達 ticker**:USAC(p_base 0.468)。pe_pctile 2nd。
- **crowding** 88.9(80–90 帶);**cycle** early。**penalty = 0.75**。

| KPI | 分 | Justification(引證據) |
|---|---|---|
| moat/樽頸 | **1.5** | 引擎/壓縮機 lead time 13 年單向惡化(2013 4–6 月→2018 約 1 年→2026 150 週),管理層「does not have direct commodity price exposure」(2022-08-02)= 解耦油氣週期;證據最乾淨。**但咽喉喺 OEM(CAT/Ariel)、USAC 係受益者/fleet 持有人非咽喉本身**(themes.yaml node 明標)→ 拉低至 1.5 而非 2;紅隊前亦封 1.5。⚠reviewer 若重「咽喉非可交易名直接持有」可判 1.0。 |
| 資本/ROIC | **1.0** | 「未做 ROIC 深度研究」。一手財務:USAC EBIT margin 中位 0.301(高)**但** interest coverage 1.72(低)、net_debt/EBITDA 4.75(高槓桿)、**solvency_flag = true**;node 標「MLP 結構封 equity 上檔(分派重)」→ 有盈利唔俾 0,但槓桿 + solvency flag 拖低 → 1.0。⚠solvency_flag=true + coverage 1.7x,reviewer 可判 0.5。 |
| 估值/priced-in | **2** | 機械格:pe_pctile 2nd(<50)**且** p_base 0.468(≥0.4)→ 2。全批 40 候選估值最平。 |
| 成長/TAM | **1.5** | LNG 出口 + Permian associated gas + AI 天然氣發電三驅動,多年結構性;已下 2027–2029 訂單(兌現中)。供給結構性慢(150 週)。本質近 2,**封頂 1.5**(pending red-team;TAM 未 sizing)。 |

base = (1.5+1.0+2.0+1.5)/8 = **6.0/8 = 0.75**
penalty(88.9 → 80–90 × early)= **× 0.75** → raw = **0.563**
single-source cap → min(0.563, 0.30) = **0.30**(**cap 硬綁**)
**capped = 0.30 | 現行 = 0.33 | delta = −0.03**
⚠**現行 0.33 > cap 0.30 = 現正違規**;合規值 = 0.30(向下修返合規)。

---

### 2.5 specialty-siding-pricing-power(現行 0.20)
- **最佳表達 ticker**:LPX(p_base 0.729)。pe_pctile 95th(**whole-company blended**,wiki 明標分唔開弱 OSB / 強 Siding)。
- **crowding** 97.2(≥90 帶);**cycle** mid。**penalty = 0.55**。

| KPI | 分 | Justification(引證據) |
|---|---|---|
| moat/樽頸 | **1.0** | SmartSide/ExpertFinish 近 9 季 7 季講 pricing power(2024 起)+ 2026-05-06 真 managed-allocation 到 2026-02(實質事件非講字)。**但只係公司一個 segment,commodity OSB 另一盤而家蝕錢(§4a 1 分錨:護城河被非核心業務稀釋)** → 1.0(封頂 1.5 未觸及,本質係 1)。 |
| 資本/ROIC | **1.0** | 「未做 ROIC 深度研究」。一手財務:LPX EBIT margin 中位 0.141、coverage 8.67、net_debt/EBITDA 0.77、solvency false → 尚健康;但 OSB segment 現跌破 EBITDA 損益兩平拖累(§4a 1 分錨:核心 ROIC 好但被拖累)→ 1.0。 |
| 估值/priced-in | **0.5** ⚠ | 機械格衝突:pe_pctile 95th(≥90)→ 錨指 0;**但** p_base 0.729(≥0.4,常態化盈利下便宜)+ wiki 明標 pe 係 blended、不可靠 → 有緩衝。插值 **0.5**(0 與 1 之間)。**呢格係判斷插值,gatekeeper 須裁**(見 §5)。 |
| 成長/TAM | **1.0** | vinyl→engineered-wood 轉換 + share gain(收縮市場仍增長),機制真;**但公司只佔一角 + TAM 未 sizing + OSB 拖累**(§4a 1 分錨:TAM 真但公司只佔一角)→ 1.0。 |

base = (1.0+1.0+0.5+1.0)/8 = **3.5/8 = 0.4375**
penalty(97.2 → ≥90 × mid)= **× 0.55** → raw = **0.241**
single-source cap → min(0.241, 0.30) = **0.241**(cap 未綁住)
**capped = 0.24 | 現行 = 0.20 | delta = +0.04**

---

### 2.6 glp1-biologics-packaging(現行 0.27)
- **最佳表達 ticker**:WST(p_base 0.293)。pe_pctile 71st。
- **crowding** 95.3(≥90 帶);**cycle** mid。**penalty = 0.55**。

| KPI | 分 | Justification(引證據) |
|---|---|---|
| moat/樽頸 | **1.5** | HVP regulatory-lock:>一半 HVP 元件已 spec-ed 入藥廠 FDA filing,換供應要重新報批(換供應鎖客、非純物理稀缺);4 季一致 demand-outstripping-supply(2025Q2–2026Q1)+ 雙驅動(GLP-1 量 + Annex-1 強制升級 370 項,較上季 340 升)。regulatory-lock 係耐久護城河 → 本質近 2,**封頂 1.5**(pending red-team;track record 僅 4 季)。 |
| 資本/ROIC | **1.5** | 「未做 ROIC 深度研究」但一手財務強:WST EBIT margin 中位 0.222、coverage 336、net cash(net_debt −0.205B);HVP 毛利 60%+ vs Standard 20–30% = mix-shift 改善盈利能力(§4a 2 分錨部分命中:有盈利 + 改善)。差 formal ROIC/capex 紀律證據先唔到 2 → 1.5。⚠ROIC 未正式計。 |
| 估值/priced-in | **1** | 機械格:pe_pctile 71st(50–90)→ 1;p_base 0.293(<0.4,無強資產緩衝但 regulatory-lock/backlog 屬軟緩衝)。落 1 分區,一致。 |
| 成長/TAM | **1.5** | Annex-1 強制升級 = additive 新需求,已被財報兌現(4 季 demand>supply);GLP-1 量長期增長。**但供給非結構性慢(管理層 ramping、kill=追上就完)+ 史短 + TAM 未 sizing** → 本質介乎 1–2,取 1.5(additive 機制強,封頂 1.5,pending red-team)。⚠reviewer 若重「短缺唔耐久」可判 1.0。 |

base = (1.5+1.5+1.0+1.5)/8 = **5.5/8 = 0.6875**
penalty(95.3 → ≥90 × mid)= **× 0.55** → raw = **0.378**
single-source cap → min(0.378, 0.30) = **0.30**(**cap 綁住**)
**capped = 0.30 | 現行 = 0.27 | delta = +0.03**

---

## 3. 總表(6 行)

| theme | moat | 資本 | 估值 | 成長 | base(Σ/8) | crowding(2026-07-13) | cycle | penalty | raw | **capped** | 現行 | **delta** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| aerospace-specialty-alloys | 1.5△ | 1.0 | 0 | 1.0△ | 0.4375 | 78.6 (60–80) | late | 0.55 | 0.241 | **0.24** | 0.24 | **0.00** |
| euv-lithography-monopoly | 1.5△ | 1.0 | 0 | 1.0△ | 0.4375 | 2.8 (<40) | late | 0.75 | 0.328 | **0.30**◆ | 0.22 | **+0.08** |
| us-solar-manufacturing | 1.5△ | 1.5 | 2 | 1.5△ | 0.8125 | 76.0 (60–80) | mid | 0.75 | 0.609 | **0.30**◆ | 0.32 | **−0.02**✗ |
| gas-compression-equipment | 1.5△ | 1.0 | 2 | 1.5△ | 0.75 | 88.9 (80–90) | early | 0.75 | 0.563 | **0.30**◆ | 0.33 | **−0.03**✗ |
| specialty-siding-pricing-power | 1.0 | 1.0 | 0.5⚠ | 1.0 | 0.4375 | 97.2 (≥90) | mid | 0.55 | 0.241 | **0.24** | 0.20 | **+0.04** |
| glp1-biologics-packaging | 1.5△ | 1.5 | 1 | 1.5△ | 0.6875 | 95.3 (≥90) | mid | 0.55 | 0.378 | **0.30**◆ | 0.27 | **+0.03** |

圖例:△ = moat/growth 封頂 1.5(pending red-team);◆ = single-source cap 0.30 綁住;
✗ = 現行值 > cap、現正違規、向下修返合規;⚠ = 判斷插值待裁。
**全部 6 個 delta 落喺 ±0.08 內**,與 DESIGN §4a addendum「有 cap 後 delta 壓縮到 ±0.08」一致。

估值格數據錨(實數):

| theme | best ticker | pe_pctile(2026-07-11) | p_base(2026-07-15) | → 估值分 |
|---|---|---|---|---|
| aerospace | ATI | 98th | 0.237 | 0(≥90) |
| euv | ASML | 98th | 0.184 | 0(≥90) |
| us-solar | FSLR | 22nd | 0.655 | 2(<50 且 ≥0.4) |
| gas-compression | USAC | 2nd | 0.468 | 2(<50 且 ≥0.4) |
| specialty-siding | LPX | 95th(blended) | 0.729 | 0.5(衝突插值⚠) |
| glp1 | WST | 71st | 0.293 | 1(50–90) |

---

## 4. 建議 wiki 推導 block(每 theme 一段,照 memory-supercycle 2026-07-15 格式,方便 gatekeeper 直接貼)

> 每段建議取代對應 wiki 現行「## confidence 推導」嘅純敘事 code block。

### aerospace-specialty-alloys
```
## confidence 推導(可追溯;2026-07-15 subscore 補寫)
KPI: moat 1.5/2(ATI「6/7 most advanced jet engine nickel alloys」+ CRS re-qual 鎖客、
       19/15 年一致;一手約束語言但未經 Level-2 red-team → 封頂 1.5)
     · capital 1/2(EBIT margin 0.132/coverage 5.82,有盈利;ROIC/capex 未研究,證據缺失)
     · valuation 0/2(pe_pctile 98th ≥90 + p_base 0.237 <0.4,機械格)
     · growth 1/2(build-rate 掛鈎、非 additive;TAM 未 sizing)          = 3.5/8 = 0.4375 base
penalty(§4a 表:crowding 78.6 → 60–80 帶 × late)                        × 0.55  → 0.241
single-source cap(sources len=1,transcript-discovery-radar)             → min(0.241, 0.30)
→ confidence = 0.24  (INITIAL, uncalibrated)
```

### euv-lithography-monopoly
```
## confidence 推導(可追溯;2026-07-15 subscore 補寫)
KPI: moat 1.5/2(全球唯一 EUV 供應商、16 年 4 週期「always constraining」「sold out 2026」;
       全批單股最強護城河但未經 Level-2 red-team → 封頂 1.5)
     · capital 1/2(EBIT margin 0.328/coverage 104/net cash,有盈利;ROIC/capex 未研究)
     · valuation 0/2(pe_pctile 98th ≥90 + p_base 0.184 <0.4;最人盡皆知、無「未被發現」溢價)
     · growth 1/2(AI 製程 capex 拉動、經 fab 週期兌現中;TAM 未 sizing)  = 3.5/8 = 0.4375 base
penalty(§4a 表:crowding 2.8 → <40 帶 × late)                          × 0.75  → 0.328
single-source cap(sources len=1)                                        → min(0.328, 0.30)
→ confidence = 0.30  (INITIAL, uncalibrated;↑ from 0.22,主因 crowding 極冷 penalty 只 0.75)
```

### us-solar-manufacturing
```
## confidence 推導(可追溯;2026-07-15 subscore 補寫)
KPI: moat 1.5/2(232/301 關稅+IRA+CdTe 成本護城河、7 年 sold-out、2016 自認無 pricing power
       →今日真 regime change;可交易名直接持有但未經 Level-2 red-team → 封頂 1.5)
     · capital 1.5/2(EBIT margin 0.315/coverage 41.7/net cash + backlog 到 2030 支持產能建設;
       formal ROIC 未計故未到 2)
     · valuation 2/2(pe_pctile 22nd <50 且 p_base 0.655 ≥0.4,機械格,批內 priced-in 最好)
     · growth 1.5/2(reshoring additive 已兌現、供給政策性慢;TAM 未 sizing、政策 binary → 封頂 1.5)
                                                                          = 6.5/8 = 0.8125 base
penalty(§4a 表:crowding 76.0 → 60–80 帶 × mid)                         × 0.75  → 0.609
single-source cap(sources len=1)                                        → min(0.609, 0.30)
→ confidence = 0.30  (INITIAL, uncalibrated;↓ from 0.32,現行違規 cap,向下修返合規)
```

### gas-compression-equipment
```
## confidence 推導(可追溯;2026-07-15 subscore 補寫)
KPI: moat 1.5/2(150 週 lead time、13 年單向惡化、「no direct commodity price exposure」解耦;
       但咽喉喺 OEM(CAT/Ariel)、USAC 係受益者非咽喉持有人 → 拉低 1.5;未經 red-team)
     · capital 1/2(EBIT margin 0.301 高 但 coverage 1.72 低/net_debt-EBITDA 4.75/solvency_flag=true
       + MLP 分派重 → 有盈利唔俾 0 但槓桿拖低)
     · valuation 2/2(pe_pctile 2nd <50 且 p_base 0.468 ≥0.4,機械格,全批最平)
     · growth 1.5/2(LNG/Permian/AI-gas 三驅動、2027–29 訂單兌現中、供給結構性慢;TAM 未 sizing → 封頂 1.5)
                                                                          = 6.0/8 = 0.75 base
penalty(§4a 表:crowding 88.9 → 80–90 帶 × early)                       × 0.75  → 0.563
single-source cap(sources len=1)                                        → min(0.563, 0.30)
→ confidence = 0.30  (INITIAL, uncalibrated;↓ from 0.33,現行違規 cap,向下修返合規)
```

### specialty-siding-pricing-power
```
## confidence 推導(可追溯;2026-07-15 subscore 補寫)
KPI: moat 1/2(SmartSide/ExpertFinish 7/9 季 pricing power + 真 managed-allocation 事件;
       但只覆蓋一個 segment、被虧損 OSB 稀釋 → 1 分,非封頂)
     · capital 1/2(EBIT margin 0.141/coverage 8.67 尚健康 但 OSB 跌破 EBITDA 損益平衡拖累)
     · valuation 0.5/2(⚠機械格衝突:pe_pctile 95th ≥90 指 0,但 p_base 0.729 ≥0.4 + pe 係 blended
       不可靠有緩衝 → 插值 0.5;待 gatekeeper 裁)
     · growth 1/2(轉換/share-gain 機制真 但公司只佔一角、TAM 未 sizing)  = 3.5/8 = 0.4375 base
penalty(§4a 表:crowding 97.2 → ≥90 帶 × mid)                          × 0.55  → 0.241
single-source cap(sources len=1)                                        → min(0.241, 0.30)
→ confidence = 0.24  (INITIAL, uncalibrated)
```

### glp1-biologics-packaging
```
## confidence 推導(可追溯;2026-07-15 subscore 補寫)
KPI: moat 1.5/2(HVP >半數 spec-ed 入 FDA filing=換供應要重新報批 regulatory-lock、4 季一致
       demand>supply、Annex-1 370 項雙驅動;耐久護城河但史短 + 未經 red-team → 封頂 1.5)
     · capital 1.5/2(EBIT margin 0.222/coverage 336/net cash + HVP 60% 毛利 mix-shift 改善;
       formal ROIC 未計故未到 2)
     · valuation 1/2(pe_pctile 71st 50–90 + p_base 0.293 <0.4,機械格,適中)
     · growth 1.5/2(Annex-1 additive 已兌現;但短缺非結構性慢(ramping)+史短 → 封頂 1.5)
                                                                          = 5.5/8 = 0.6875 base
penalty(§4a 表:crowding 95.3 → ≥90 帶 × mid)                          × 0.55  → 0.378
single-source cap(sources len=1)                                        → min(0.378, 0.30)
→ confidence = 0.30  (INITIAL, uncalibrated)
```

---

## 5. 未解 / 證據不足 / 唔肯定嘅判斷(誠實列,供 gatekeeper 覆核)

1. **capital/ROIC 格全批係最軟判斷**。6 個 theme wiki 全部明文「未做 capital-allocation/ROIC/
   TAM 深度研究」。我用 valuation_report.json 嘅一手財務讀數(EBIT margin / coverage /
   net_debt / solvency_flag)做下限錨(有盈利就唔俾 0),但**冇一個 theme 有正式 ROIC 趨勢或
   capex 紀律 writeup**。呢批 capital 分(aerospace/gas 1.0;euv 1.0;us-solar/glp1 1.5)本質係
   「財務健康度代理」,唔係真 ROIC 判斷。gatekeeper 若要嚴,可全部下調 0.5 級。

2. **specialty-siding 估值格 0.5 係判斷插值,唔係機械輸出**。pe_pctile 95th(≥90 → 錨 0)
   vs p_base 0.729(≥0.4 → 支持高分),兩者衝突,加上 wiki 明標 pe 係 whole-company blended
   不可靠。我取 0.5。**呢格 gatekeeper 必須裁**:若嚴守「pe_pctile≥90 → 0」機械規則則為 0
   (base 降到 3.0/8=0.375,raw=0.206,capped=0.21,delta +0.01);若信 p_base buffer 取 1 則
   base 4.0/8=0.5,raw=0.275,capped=0.28,delta +0.08。三種取值 capped 分別 0.21/0.24/0.28。

3. **gas-compression moat 1.5 有爭議**。咽喉實際喺 OEM(CAT/Ariel),USAC 係受益者/fleet 持有人
   而非咽喉本身(themes.yaml node 自己標)。嚴格按「可交易名直接持有咽喉」錨,呢格可判 1.0
   (base 降 5.5/8=0.6875,raw=0.516,capped 仍 0.30 因 cap 綁住 → delta 不變)。因 cap 綁住,
   呢個爭議唔影響 capped 值,但影響 wiki 記錄嘅 subscore(lint 會逐格對),須揀定。

4. **gas-compression capital 1.0 vs 0.5**:solvency_flag=true + interest coverage 1.72x 係實在
   隱憂,reviewer 可判 0.5(同上,因 cap 綁住,唔影響 capped 0.30,但影響 lint 對數)。

5. **euv / us-solar / gas / glp1 四個因 cap 綁住,subscore 微調唔影響 capped 0.30**,但
   **lint.py 會逐格核對 wiki 記錄嘅 subscores 套公式 = themes.yaml 值**。所以就算 capped 相同,
   gatekeeper 都要 sign-off 每格分數本身(上面爭議 3–4),因為 lint 對嘅係公式全鏈,唔淨係終值。

6. **moat/growth 封頂 1.5 係硬套 §4b**:6 個 theme 全部未經 Level-2 red-team。若 gatekeeper 決定
   對某 theme(例:us-solar CdTe 護城河、euv 壟斷)行 Level-2 red-team 且生還,對應格可升 2,
   raw 上升,但**只有現行未觸 cap 嘅 theme(aerospace 0.241、siding 0.241)先會反映到 capped**;
   已觸 cap 嘅四個要同時脫離 single-source cap(Tier-1 獨立擊中承重 claim)先郁得到 0.30 以上。

7. **crowding 讀數 2026-07-13、pe 讀數 2026-07-11、p_base 2026-07-15,三者非同日**。跨度 4 日,
   對分位級判斷影響應可忽略,但 gatekeeper 落 themes.yaml 前宜確認毋須 refresh。

8. **本草稿一律用 INITIAL / uncalibrated**;confidence 校準要等戰績簿(DESIGN §6)累積,
   現階段所有數都係「證據推導值」非「校準機率」。

---

## 6. Gatekeeper 裁決(Opus 主 session,2026-07-16)

算術逐 theme 抽驗通過(base×penalty→cap 全對)。三個待裁位判決如下,**capped 值全部維持草稿數(0.24/0.30/0.30/0.30/0.24/0.30)**——因所有爭議格唔係喺 cap 下面(siding)就係被 cap 綁住(gas):

1. **gas-compression moat 1.5 → 1.0(改)**:§4a moat 2 分錨要求「可交易名直接持有咽喉」;USAC 係 fleet 持有人/受益者,咽喉實際喺 OEM(CAT/Ariel),正中 1 分錨「樽頸真但護城河主要喺不可交易實體」。改 1.0。base 6.0→5.5/8,raw 0.563→0.516,**cap 綁住 capped 仍 0.30**,但 wiki 記 1.0(lint 逐格對)。

2. **gas-compression capital 1.0(保留,但補理由)**:solvency_flag=true + coverage 1.72x 係實在紅旗,但**唔喺 capital KPI 度罰**——solvency 已由獨立條件閘處理(pick_ticker demote + 日報警示),capital 又罰 = 雙重計算,違反公式「唔好雙重折」原則(同 memory red-team「表達層風險唔喺 penalty 再折」同源)。USAC 有高 EBIT margin(0.301)+ 真分派,係 MLP 結構槓桿唔係燒錢軍備競賽 → capital 1.0 反映「創造價值」。wiki 註明 solvency 由獨立閘負責。

3. **specialty-siding 估值 0.5(保留,重新定性)**:唔係「自由插值」,係 **documented 數據質量降級**——pe_pctile 95th 係 whole-company blended(OSB+Siding 溝埋,wiki 明標不可靠),唯一乾淨信號 p_base 0.729 指向便宜,但單一 input 唔夠支持滿分 → 0.5 反映「一 input 污染、一 input 便宜、淨結果模糊」。capped 0.24。**待補:Siding segment 單獨 PE**(有咗先計得準)。

4. **capital 格全批定性**:6 個 theme 嘅 capital 分本質係「財務健康度代理」(EBIT margin/coverage/net_debt/solvency),**唔係正式 ROIC 判斷**——全部 wiki 已標「未做 ROIC 深度研究」。落 wiki 時每格註明呢個限制,列入待補。呢批係全套 confidence 最軟嘅輸入,校準時要記住。

**落筆安排**:本 6 theme 嘅 themes.yaml confidence 數字 + wiki 推導 block **併入 task #6 最終 15/15 diff**,同其餘 red-team 判決一次過俾用戶批准後切,唔零散切(us-solar 0.32→0.30、gas 0.33→0.30 係違規修正;euv +0.08、siding +0.04、glp1 +0.03、aerospace 0.00)。
