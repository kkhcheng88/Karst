# Result — Breadth REVERSION(尾巴/thrust/背離):洗盤→反彈係真、短線 over VIX 有增量

**Date:** 2026-07-05  **Script:** `exp_breadth_reversion.py`  **Tag:** active ✅(修正前結論)
**背景:** 之前 `2026-07-05_phase2_flow.md` 判 breadth「弱/逆向/VIX 冗餘」——但嗰個係測 **LEVEL 的線性 forward IC**。
用戶 push:reversion 應該有意義。而 reversion 經典上住喺**非線性尾巴 / thrust / 背離**,線性 IC 睇唔到。本檔用
**條件報酬**(非 IC)重測,發現**之前結論對尾巴係錯的**。

**數據:** breadth 由 `px_defeatbeta.pkl`(3101 股,1994-2026,median 1557 names/day;**survivorship-biased →
用相對 decile/percentile,唔用絕對 %**);另做**乾淨版**板塊參與度(11 SPDR above 50SMA,1999-2026,無
survivorship)。SPY/VIX/SPDR = yfinance。兩半:median date 2012-09-28。**BASELINE:21d +0.80% / 63d +2.37%。**

## ① 洗盤 → 反彈 = 真、強、兩半穩(非線性,線性 IC 睇唔到)
| %above50 | 21d mean(win) | 63d mean(win) |
|---|---|---|
| **D0 底格(≤27%,殘)** | **+2.58%(69%)** | **+5.23%(73%)** |
| 中間 D3-D8 | ~0.0–0.7% | +0.8–1.9% |
| D9 頂格(≥73%,過熱) | +0.96%(70%) | +3.88%(76%) |

- D0 = **~3× baseline**(21d)、~2.2×(63d)。%above200 D0 同款(21d +2.35% / 63d +4.26%)。
- **兩半都成立**:H1 洗盤 21d +2.51% / H2 21d +2.66%(H2 63d +8.20%,win 84%);過熱格兩半亦正(見 ③)。
- **乾淨版佐證(板塊參與度,無 survivorship)**:板塊洗盤(≤20% 板塊上 50)FULL 21d +1.98%/63d +3.75%;
  H2 21d +3.56%/63d +7.03%(win 83%)→ **同號、確認,唔係 survivorship artifact**。

## ② 喺 VIX 之上有增量 —— 但只喺短 horizon(21d)
| 雙排序 | 21d mean | 63d mean |
|---|---|---|
| 洗盤 & VIX 高 | **+2.95%** | +4.78% |
| 非洗盤 & VIX 高 | +0.90% | +4.72% |
| 洗盤 & VIX 低 | +0.84% | +3.44% |
| 非洗盤 & VIX 低(≈baseline) | +0.47% | +1.52% |

- **21d:洗盤&VIX高(+2.95%) − 非洗盤&VIX高(+0.90%)= +2.05pp = breadth 喺 VIX 之上有增量** ✅。
- **63d:+4.78% ≈ +4.72% = 增量消失**,VIX 捉晒。
- **∴ breadth 洗盤 = 短線(~1 個月)「買恐慌」增強器;長線被 VIX 吸收。** 且洗盤 × VIX-高會**疊加**(最強格)。
- 乾淨版一致:板塊洗盤&VIX高 H2 21d +4.34% / 63d +7.80%。

## ③ reversion 係單邊(downside 真,upside 唔成立)
- 頂格/過熱(≥73% above50):21d +0.96% / 63d +3.88% = **仍正、高過 baseline → 動能延續,唔係轉頭插**。
- **即:洗盤→彈真;過熱→回唔成立。高 breadth = 續升(momentum),唔係 mean-revert down。**

## ④ 大市層 價/breadth 背離 = 冇 edge
| | 21d | 63d |
|---|---|---|
| 背離(SPY 貼高 + 參與↓20d) | +0.44% | +2.28% |
| 確認(SPY 貼高 + 參與↑) | +0.58% | +2.04% |
- **背離 ≈ 確認(兩半一致)→ 市場層 price/breadth 背離冇預測力。** 正符合「背離要落 sub-sector 先有意義」。

## ⑤ Thrust(由洗盤急彈 >10pp)= modest,被 level 吸收
- FULL 21d +1.57%(win 73%)/ 63d +2.59%;H2 較好(+2.18/+4.47)。raw 洗盤 **LEVEL** 比 thrust 定義更乾淨更強。

## Conclusions
1. **修正**:「breadth 冇效」= 只對**線性 LEVEL** 成立;**尾巴洗盤嘅 downside reversion 係真**(兩半 + 乾淨版佐證)、
   **短線(21d)喺 VIX 之上加 +2pp**、洗盤×VIX-高疊加最強。
2. **限定**:(a) 只 downside(洗盤→彈),upside 過熱 = 動能唔係 fade;(b) 只短 horizon(63d 被 VIX 吸);
   (c) 大市層背離冇用;(d) thrust 被 level 吸。
3. **性質**:同 VIX/RSI-2「買恐慌」複合體重疊 → 多一把尺、非全新獨立 alpha。

## Caveat(重要)
- **洗盤事件高度叢集/自相關**:D0 個 n≈692 係**重疊交易日**,實際 ~8-12 次獨立事件(2008/2011/2015-16/2018/
  2020/2022)→ **有效樣本細、誤差遠大過 n**。當「方向一致的 stylized fact」讀,唔好當 t-stat 級證據。
- survivorship 令 LEVEL 偏高 → 已用相對 decile 化解;乾淨板塊版同號 = 較放心。

## Implication + 下一步(用戶 point:sector/sub-sector 應更實)
- 市場層洗盤 reversion **已係正**(唔係 null)→ 提高「**子板塊/value-chain 層會更實**」嘅 prior(群體更同質、
  一齊由弱側轉 = 你講嘅群體行為)。
- **未測 = within-sector breadth**(板塊成份 % above 50 → 預測該板塊 ETF 反彈)——需要**板塊成份 map**
  (= Phase 3 value-chain/主題成份基建)。**呢個正正係 breadth idea × Phase 3 交匯點。** 待建 member map 再跑。

## 驗證(2026-07-06,`exp_breadth_reversion_verify.py`)
**① 日期核實 —— 「洗盤&VIX高」= 真.股災底(無誤)**:抽返事件,一一對上 GFC(2008-09→2009-03,VIX 峰 80.9 /
breadth 谷 **1.6%**)、COVID(2020-02→04,VIX 82.7 / **2.5%**)、dot-com 底(2002,6.9%)、2011(5.4%)、2015、
2018-12(6.4%)、2022 三段、2025-03(VIX 52 / 5.6%)。**修正**:「VIX 高但冇洗盤」嗰批 **唔係孤立驚嚇**,而係
**崩完之後嘅復原/反彈期(VIX 未落股已彈)+ 高波動陰跌 grind**(2009 復原、2020 復原、dot-com grind)→ 正解釋
點解嗰批彈得弱(彈簧已放 / 冇真洗清)。
**② 不對稱係真、唔係 drift(減 drift 重驗)**:用 excess(= 條件平均 − 無條件 baseline)+ 下行風險重跑 ——
- 洗盤 D0:21d excess **+1.78pp** / 63d **+2.86pp**(真 excess,非 drift)。
- 頂格 D9:21d excess **+0.16** / 63d **+1.52**(仍正)、左尾 worst5% −6.3%(**冇更肥**、下插機率冇升)→
  **做空頂實證冇值**;單邊反彈係真.市場性質(「上樓梯落�'」)。
- **新形狀 = U 形微笑**:最差係**中間 ~50% breadth(D4 excess −0.81)= 猶豫區**,兩極端都好過中間 → 亦解釋
  點解線性 IC 微負(直線 fit 一個 U 形嘅假象)。

## Confidence
- 洗盤→彈(downside、短線、over VIX @21d)= **MED**(兩半 + 乾淨版一致,但事件叢集、與 VIX/RSI-2 重疊)。
- upside 過熱=動能、大市層背離冇用 = **MED-HIGH**(清晰、兩半一致)。
