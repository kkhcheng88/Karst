# Result — BREAKOUT MOMENTUM(SPEC D Donchian timer + SPEC A/B Minervini 個股 + risk-layer)

**Date:** 2026-07-05  **Scripts:** `exp_breakout_timer.py`、`exp_minervini_breakout.py`  **Tag:** active ✅
—— 完成「補風控層」(path a);源自 `ebooks/Discretionary Momentum/DISTILLATION-backtestable-rules.md`
(O'Neil/Darvas/Livermore/Minervini 蒸餾)。資本效率 + 4 類別/市值層 + two-halves,2016+,10bps。
**Caveat 全檔通用:cache 只有 close → price-only,practitioner 嘅 VOLUME≥1.5× 突破確認未套用。**

## Question
用戶指出 SMA/月-lookback 太粗糙/太慢。測公認+實戰嘅**突破式(短 horizon)動能**:(D)Donchian 新N日高
timer;(A/B)Minervini 趨勢範本+突破個股選股 + 風控層 overlay。答:突破加唔加到 TSMOM 之上?edge 喺
入場定出場?

## SPEC D — Donchian 突破 timer(新N日高入/新M日低出),條件Sharpe(high20 入場行,穩健唔係單格)
| 籃 | B&H F/H1/H2 | 突破 high20/low10 F/H1/H2 | vs TSMOM composite |
|---|---|---|---|
| **micro** | 0.78/1.40/0.27 | **2.31/3.34/1.29** | ≫(TSMOM 1.32/1.66/1.03) |
| **Mag7** | 1.17/1.48/0.91 | **1.74/1.73/1.75** | >(1.30/1.42/1.19) |
| **大盤** | 0.91/0.91/0.92 | **1.51/1.64/1.41** | >(1.07/**0.82**/1.28)—**修 H1** |
| large | 1.01/0.97/1.06 | 1.36/1.65/1.07 | >(1.06/1.09/1.03) |
| mid | 0.90/0.95/0.86 | 0.98/1.61/**0.37** | H1 勁 H2 弱 |
| small | 0.79/0.89/0.69 | 0.93/1.59/**0.33** | H1 勁 H2 弱 |
| 板塊ETF | 0.67/0.58/0.80 | 0.68/0.76/0.60 | ≈ B&H |
| 細價ETF | 0.53/0.57/0.48 | 0.55/1.04/**0.11** | H1 勁 H2 弱 |
→ **快 20 日高突破 = 目前最佳 momentum timer > TSMOM > SMA**;大盤/Mag7/large/micro **兩半贏 B&H,而且
修返 TSMOM 嘅 H1 弱點**(印證用戶「月 lookback 對日 K 太慢」)。曝險低啲(56% vs 80%)= 更選擇性。
mid/small/ETF-板塊/細價 H2 whipsaw 弱。

## SPEC A/B — Minervini 趨勢範本 + 突破個股 · RISK vs FIXED(每筆%/勝%/效率%/yr)
| tier | RISK F/H1/H2 (eff) | FIXED F/H1/H2 (eff) |
|---|---|---|
| micro | −0.5/+1.9/−2.4 (−6/+22/−35) | +1.6/+8.4/−4.2 (+6/+34/−17) |
| small | +1.5/+3.8/−0.0 (+16/+35/−0) | +3.9/+8.0/+1.1 (+16/+32/+5) |
| mid | +1.7/+3.2/+0.8 (+17/+27/+9) | **+4.9/+5.6/+4.4** (+20/+22/+18) |
| large | +1.3/+1.7/+1.0 (+12/+14/+10) | +4.0/+4.4/+3.7 (+16/+18/+15) |
1. **❌ 「edge 喺 risk layer」不成立(作回報)**:FIXED 全面贏 RISK。8% 止蝕 + 50MA trail **斬贏家 +
   whipsaw 細蝕**(持 19-28d vs 62d,勝率 31% vs 56%)→ **止蝕/trail = 封尾部損失(生存),唔係 boost
   回報**。per-trade return 量度唔到佢真正價值。
2. **⚠ Minervini SELECTION 冇加 alpha**:FIXED 效率 large +16 / mid +20 ≈ B&H(18.9/19.8);small +16
   < 17.9;**micro +6 << 14.4**。堆疊 MA + RS≥80 + 突破嘅選股 **唔 beat 揸個 tier** → 同「選股 IC ≈ 0」一致。
3. **⚠ H1 >> H2**:FIXED micro H1 +8.4 → H2 −4.2;small +8.0 → +1.1。突破選股一樣 H1 勁、H2 whipsaw。

## Conclusions(path a 完成)
1. **唯一乾淨改良 = 20 日高突破 timer**(SPEC D)> TSMOM > SMA:大盤/Mag7/large/micro 兩半贏 B&H、修 H1。
   **值得接線做 Phase-1/4 momentum timer。**
2. **突破 SELECTION(Minervini)冇 alpha**(≈/低過 B&H;price-only caveat)。
3. **Risk layer(止蝕/trail)斬贏家、傷回報** → 佢係尾部封頂(生存),唔係 alpha。
4. **大局再確認**:**價量/動能層 = 風控/timing,唔係 alpha。** 真 alpha 仍靠 Phase 3。

## Caveats
- **price-only,無成交量確認** —— practitioner 最強調嘅突破質量 filter 缺席;加量可能改善(未測=真 gap)。
- Minervini RS≥80 用月度橫截面百分位 ffill(point-in-time);63 日固定持有係武斷 baseline。
- 個股 survivorship 偏高(micro 最甚);資本效率階段(總財富待 portfolio)。

## Confidence: **HIGH(方向)**
- SPEC D 20 日高突破 > TSMOM 跨多籃 + 兩半一致;Minervini 冇 alpha + risk-layer 傷回報跨 4 tier 一致。
- 唯一未證 = 加成交量確認會唔會令突破 selection 由「無 alpha」變「有」。

## Implication for Karst
- **Phase-1/4 momentum timer 用 20 日高突破**(取代/補 SMA;比 TSMOM 更快、修 H1),但仍當**風控/timing**
  ([[regime-and-fear-greed-findings]] 一致:動能 = downside protection,唔係 alpha)。
- **唔使**砌 Minervini 全套選股當 alpha(price-only 版無增量);止蝕/trail 定位為**風控(封尾部)**唔係回報引擎。
- **策略下一步 = Phase 3 thesis + forward-IC**(唯一 alpha 門);風控層特徵已徹底釘死。
- (可選)若要救 Minervini selection:**加成交量確認**重測 —— 唯一未閉嘅 gap。
