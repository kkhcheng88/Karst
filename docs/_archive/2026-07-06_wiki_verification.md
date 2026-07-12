# Wiki 驗證 + 修正清單(Fable 任務 1)【SUPERSEDED】

> ⛔ **本檔已被取代**(2026-07-06 同日):用戶下令棄用斷網 sandbox run 嘅產出、獨立重驗。
> 新版 = `docs/2026-07-06_wiki_verification_v2.md`(4 個獨立驗證員 + code-level 核對,~124 條)。
> 本檔留檔可溯,唔好再引用。

> **做咗乜**:KARST_WIKI.md 每個實證 claim 追返去 `backtest/results/*.md`(34 份全數庫存)+ 針對疑點
> grep 核實原檔。判定分三級:❌ A = 事實錯 / untraceable / 內部矛盾(即改);⚠️ B = 過度 / 漏 caveat
>(補注);➕ C = 覆蓋洞(要加)。**已直接修改 wiki 嘅項會標 [已修]**。
> 驗證人:Fable 5(adversarial pass)。日期:2026-07-06。

## 總判

Wiki 骨架同大部分數字**可靠**——§5.1/5.3/5.5/5.6/5.8/5.9/5.10、§6 XY 圖、§8 oracle 全鏈(155%/196%/
+0.6pp/週151→年23.5/IC 0.05→10.3%/0/28 Bonferroni/rank2=16×)逐個數對過源檔,全部核實無誤。
問題集中喺:**一條撞數、一條新舊結論並存嘅內部矛盾、一條 untraceable 舊數、幾條漏咗 regime/survivorship
caveat 嘅招牌 claim**。以下逐項。

## ❌ A 級(事實錯 / untraceable / 矛盾)

| # | 位置 | 問題 | 證據 | 修正 |
|---|---|---|---|---|
| A1 | §5.2 RSI-2「結果」行 | **撞數**:32/1.21 · 24/0.94 · 24/0.98 · 48/1.30 係 **F&G 檔**(`fg_timed_capital_efficiency`)best cells,同 §5.4 一模一樣。RSI-2 自己嘅數(`rsi2_capital_efficiency` Result 1,entry<10/exit>80)= **32/1.16 · 21/0.83 · 14/0.63 · 46/1.09** | 兩檔 grep 對確認 | [已修] 換返 RSI-2 own numbers + 標 entry/exit |
| A2 | §Phase 0「驗證咗」L130 | **內部矛盾**:「credit > VIX 做 regime(KC Fed RORO)」係 07-03 前舊結論;07-05 `market_regime_2d` 已推翻(credit regime 反覆 H1 corr −0.11/H2 +0.17、對 VIX 無穩定增量)→ 同一份 wiki §5.5/§6/§7.2 講「credit 剔除」 | `market_regime_2d` REJECTED | [已修] L126+L130 改為 VIX×趨勢 2D,註明 credit 已剔除 |
| A3 | §Phase 0 L128 + §5.5 L228 | **untraceable**:「VIX>30 → 63日 +5-6%(跨所有時期穩)」全 repo 冇呢個回測;源頭係 `topdays_exposure` 明文講「不可重現」嘅舊 capstone(findings #5-8)。可追溯嘅數 = `market_regime_2d`:**VIX>28 牛市 +9.0%/熊市 +5.9%**(63日,兩半穩) | grep 全 repo + topdays L92/L141 | [已修] 換可追溯數字 |
| A4 | §4.3 Phase 2 status | 「🔴 未建」同 §4.2/§9 自相矛盾(大市層已測收官:DIX + 洗盤) | `phase2_flow` 收官段 | [已修] 改「🟡 大市層測完收官;細板塊層跟 Phase 3;overlay 接線未做」 |
| A5 | §5.4 F&G 用法 + §6 樹「恐懼窗 F&G/VIX」 | 同 `fg_vs_vix` 收官結論矛盾:**VIX 恐懼/入場側嚴格更好**(head-to-head VIX>28 每筆 +1.0-5.2% vs F&G<25 +0.1-2.4%);**F&G 獨特價值只喺貪婪/出場側**(>75 → 63d +0.2%、>80 → −1.6%,單調衰減,VIX 低位冇呢個訊號);F&G 恐懼側 H1(2016-20)仲要係**負** | `fg_vs_vix` PART 1-3;KARS_MEMORY L173 同一講法 | [已修] F&G 角色改「貪婪/出場計」;恐懼窗改 VIX 主 |

## ⚠️ B 級(過度 / 漏 caveat)

| # | 位置 | 問題 | 修正 |
|---|---|---|---|
| B1 | §2 + §3.2「實證 RSI-2 top-quintile 贏 SPY +12.5%」 | 招牌數冇 caveat:costless、equal-weight、**現任 S&P 成份 survivorship**(死股預先剔走)、**DSR 0.908 < 0.95 未過多重檢定**(`insider_family_revalidate`)。方向可信、幅度要打折 | [已修] 兩處補「survivorship 灌大、DSR 未過,幅度打折」 |
| B2 | §5.2 市值行「mid ✅ 高波怪獸 +101%/2.61」 | 嗰格係 **H2-only**;同一檔寫明「H1 大地雷(<5 −43)」。引怪獸唔引地雷 = 揀靚數 | [已修] 補 H1 −43 |
| B3 | §5.7 insider「大型股 21/63 日顯著」 | `insider_rigor` Result 8:拉長到 2006 後 large-cap 21d **冧到唔顯著**(t 1.1),edge 只喺 2009/2022/2024/2025 → 係 regime-fragile 唔係穩定短期 edge;文獻-aligned 嘅正結論係**細價 12 個月 portfolio vs IWM**(+10-12% net,對比文獻 ~7.4% → survivorship 灌大) | [已修] 補 2006-21 冇 + 細價先係主 claim |
| B4 | §8.4「量化門 definitively 關咗」 | 板塊層(9-11 ETF)成立(0/28);但個股層 `alpha360_ml` 有 **IC 0.017(t 3.5)真.弱訊號**,<0.05 兼 survivorship-suspect,**point-in-time 重測(make-or-break)未做** | [已修] 補一句 nuance |
| B5 | §5.1 市值行 micro 數字 | 引咗 TSMOM 數(1.32/1.66/1.03)但家族headline係 20日突破(突破 micro = 2.31/3.34/1.29,更強)——兩個 timer 撈埋 | [已修] 標明邊個 timer |
| B6 | §4.2 洗盤/breadth | 數字啱(21d +2.58% ≈3×、over VIX +2pp、單邊),但漏獨立樣本 caveat:**~8-12 個獨立股災事件**(D0 n≈692 係重疊日),方向穩、唔係 t-stat 級證據 | [已修] 補一句 |

## ➕ C 級(覆蓋洞——wiki 應有而未有)

| # | 洞 | 內容 |
|---|---|---|
| C1 | **期權層冇自己嘅 §5 家族段** | core 真.alpha 機制(07-06 用戶點明 + STATUS 已載)完全唔喺 wiki:LEAP = 唯一結構解(finding #12:traded instrument ≠ benchmark 先兌現 T1)、CSP 利潤大半 beta、short call 賣超買 SPY PF 1.53→2.26、RSI-2 低位進場 Jensen alpha QQQ 6.53%/yr t2.9 / SPY 4.26% t2.4(拉長出場殺 alpha)。wiki 得 §6 一句「趨勢用 LEAP」 | [已修:§6 表達行加濃縮版;完整家族段留任務 3 產出後補] |
| C2 | **LEAP 參數證據狀態** | 所有 LEAP 回測 = **0.80Δ deep-ITM、63td roll**,且 magnitude「NOT bankable」(VIX 當 1yr IV、7bps 成本太平、單一路徑);**0.3/0.5/0.8 delta 對比 = 明文未做 gap**(`regime_and_iv` Next 段)。用戶記憶「0.3 最好」實為 **short call 條腿嘅 0.30Δ**(`shortcall_timing`),唔係 LEAP | → 排任務 2 補跑 delta sweep(BSM + 真成本 + theta) |
| C3 | 兩半定義唔一致 | §3.3 定義 two-halves = 2016-20 vs 2021+,但多份檔用自己嘅半(market_regime_2d 用 1993-2009/2010+;gex 用 <2019/2019+;alpha360 冇分半)。唔算錯,但「兩半穩」字眼跨檔含義唔同 | 記錄在案,新回測跟 §3.3 |
| C4 | 未接線清單散落 | 「已測未接線」項(20日突破 timer、RSI-2×RS-leader gate、insider conf_eff 斷線、校準迴路斷)喺 wiki 冇集中一格 | → 任務 2 統一登記 |

## ✅ 抽查核實無誤(重點 claim)

- §5.1 動能:突破大盤 1.51/1.64/1.41 vs 0.91、Mag7 1.74/1.73/1.75 vs 1.17 ✓(`breakout_momentum` SPEC D)
- §5.3 RS:Q5 17.5/17.8/16.3/12.5 vs 宇宙 14.4/12.1/10.3/9.2,兩半成立;LEVEL 係 edge、TREND 無用 ✓(`factor_families`)
- §5.5 2D 閘:② +5.1%/−4.0、③ +1.7%/−8.7、VIX partial +0.1~0.22 兩半 ✓(`market_regime_2d`)
- §5.6 低波:7.1/0.56/−29 vs 14.5/0.62/−58 ✓;§5.9 VCP IC≈0 三法一致 ✓;§5.10 GEX partial −0.077 ✓
- §8 oracle 全鏈:top-3 155%(net)、+cash 196%、EW premium +0.6pp、週151→月66→季38→年23.5、
  IC 0.05→10.3%/0.10→15.6%、0/28 Bonferroni、rank2≈16×/rank3≈9× ✓(4 檔互相咬合)
- §5.8 止蝕/trail「封尾部唔係 alpha」:RISK 31% win/19-28日 vs FIXED 56%/62日 ✓
- 決策樹「micro 永不 dip-buy」「業績避開」「擇時唔乘結構分」全部有檔可依 ✓

## 對任務 2/3 嘅移交

1. **補跑**:LEAP delta sweep(0.3/0.5/0.8)+ 真成本(0.5-2%/RT)+ IV 期限 haircut + theta 拆解(C2)→ 任務 3 直接要用
2. **登記**:risk_control_layer_report L51 仲寫「VIX/credit/RV」——credit 剔除未清到嗰份(cross-doc 版 A2)
3. **登記**:P0 接線 gap(insider conf_eff、校準迴路)fable brief 已知,任務 2 核實 code 現狀
4. **考慮**:F&G 恐懼側訊號喺 spine 嘅角色要對齊 A5(VIX 主、F&G 得返出場側)
