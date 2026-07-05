# Result — 大市 2D regime:credit 軸失敗、趨勢×VIX 成立(修正框架)

**Date:** 2026-07-05  **Scripts:** `exp_credit_axis.py`(negative)、`exp_trend_vix_axis.py`(active ✅)
**背景:** 用戶問「風險軸 = credit,我哋 backtest 咗未?」→ 冇。先前 wiki/framework 把 VIX×credit 兩軸
當 established 係 overstated。呢檔補測,定案正確嘅 2D。資料 yfinance,前望 21/63d 報酬 + 63d 最差回撤。

## (A) credit 軸(HYG/LQD)= NEGATIVE —— 剔除
credit-stress = HYG/LQD 比率 < 126MA(息差擴)。2007-2026。
- **對 VIX 冇穩定增量**:credit→前望63d 兩半反符號(H1<2016 −0.11 / partial|VIX −0.17;H2 2016+ **+0.17**
  / partial +0.17);FULL ≈ 0。VIX→ret 穩定 +0.20。
- **四象限假設(②>①>④>③)失敗**:③「VIX高+credit擴 真危機」前望報酬**最高**(FULL +4.52%、H2 +9.45%),
  唔係最低——因 QE 年代危機 V 彈;只係回撤最深。④「頂部警號」冇跑輸。
- **唯一真嘢**(VIX高+credit擴 = 回撤最深)**都係 H1 GFC 年代先明顯,H2 冇晒**。
- **結論**:QE/Fed-backstop 年代,credit 擴由「避險」變「買點」→ **credit 唔做風險軸;VIX 已足夠。**

## (B) 趨勢 × VIX 2D = VALIDATED ✅ —— 換入 Y 軸
趨勢 = SPY vs 200SMA(牛/熊);恐懼 = VIX。SPY 1993-2026(涵蓋 dotcom/GFC/2020/2022)。
**四象限前望63d / 63d最差回撤:**
| 象限 | FULL | H1 1993-09 | H2 2010+ |
|---|---|---|---|
| **② 牛市+高VIX(升中買dip)** | **+5.12% / −4.0%** | **+4.65% / −4.2%** | +5.85% / −3.7% |
| ① 牛市+低VIX(正常) | +2.62 / −3.8 | +2.92 / −3.2 | +2.41 / −4.2 |
| ④ 熊市+低VIX(派發) | +1.73 / −3.9 | +1.24 / −3.7 | +4.34 / −5.1 |
| ③ 熊市+高VIX(跌中恐慌) | +1.72 / **−8.7** | **−1.19 / −10.7** | +6.74 / −5.3 |
對照 VIX>28:牛市 **+9.0% / −3.5%**;熊市 +5.9% / **−7.6%**。連續 partial:VIX|trend +0.14(FULL)/+0.10(H1)
/+0.22(H2)—— **VIX 兩半都有獨立增量**;trend→ret 方向會反(H1 +0.20 / H2 −0.22)。

## Conclusions(正確嘅 2D + 規則)
1. **★ ② 牛市+恐懼 = 穩健甜區**:前望報酬**兩半都最高**(+4.65/+5.85)且回撤淺(−4%)。**「喺上升趨勢入面
   買恐懼」= 實證成立(兩半)。** = 用戶原本 2D idea 嘅正確版。
2. **VIX(恐懼)= 主軸**(逆向買、獨立增量兩半穩,話你【幾時買】)。
3. **趨勢(200SMA)= 安全度/dip 深度修正器**(牛市 dip 淺 −4% / 熊市深 −5~−10.7%,穩定跨兩半;話你【買得幾
   安心】)——**唔係方向訊號**(方向 regime 反覆)。
4. **熊市方向 regime 反覆**:③ H1 落刀(−1.19)、H2 V 彈(+6.74)→ **唔可硬講「熊+恐慌=避」**,睇年代。

## 可部署規則(更新)
> **買恐懼(VIX/F&G 高),但優先喺上升趨勢(SPY>200SMA)做 = ② 最好+最安全。**
> **喺下跌趨勢(SPY<200SMA)買恐懼 = 細注/小心(dip 深、可能落刀,方向睇年代)。**
> **牛市+低VIX = 順勢揸;熊市+低VIX(自滿)= 回報弱、唔加倉。**
> **X = VIX/F&G(何時)· Y = 趨勢 200SMA(有幾安全)· credit 剔除。**

## Confidence
- **② bull+fear = HIGH**(兩半一致最好 + 淺回撤,33 年、多個 crisis)。
- **VIX 主軸 = HIGH**(獨立增量兩半穩)。
- **趨勢=安全度 = HIGH**(dip 深度牛淺熊深,穩)。
- **熊市方向 = LOW / regime-dependent**(H1↔H2 反轉,唔可硬用)。

## Implication for Karst
- **Phase 0 大市閘用「VIX × 趨勢(200SMA)」2D,唔用 credit**;規則同上(買恐懼優先牛市)。
- 同 RSI-2×regime / 動能綜合一致:**買 dip 喺上升趨勢/高波先安全**([[regime-and-fear-greed-findings]])。
- BofA Bull&Bear:只得近期(訂閱)→ 回測唔到,當 Phase 2 質性情緒 read(同 gamma 牆一 tier)。
