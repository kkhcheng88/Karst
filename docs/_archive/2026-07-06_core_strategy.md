# Karst Core 策略 v1 — 策略樹 + Transition 機制 + 執行計畫(Fable 任務 3 交付)【SUPERSEDED】

> ⛔ **本檔已被取代**(2026-07-06 同日):v1 係斷網 sandbox 用 RV-proxy IV / SPY-only 砌嘅;
> 用戶下令用真數據獨立重做。新版 = `docs/2026-07-06_core_strategy_v2.md`(真 ^VIX/^VXN + 真總回報,
> Loop 1-4 + adversarial 覆核 + 獨立重跑驗證)。主要推翻:0.80Δ 全格贏、RSI-2 dip 閘、遲滯出場、
> 年度再平衡足夠 —— 詳見 v2 §8 版本紀錄。本檔留檔可溯,唔好再引用。

> **一句講晒**:底倉揸住唔郁(75%)+ 一條有紀律嘅 LEAP 引擎(10-15%)+ 現金彈藥(15%),
> 用「趨勢 × 恐懼」四象限做 transition;**唔靠估市入出,靠期權結構將真擇時技巧(T1)兌現成 alpha**。
> 回測:對 SPY B&H(總回報、HK 稅後)Jensen alpha **+3.4 ~ +5.9pp/年(t 3~4)**,β≈1.0,MaxDD −44~45%。
> 證據鏈:`backtest/results/2026-07-06_core_portfolio_loops.md`(loop 記錄)+ `_leap_delta_sweep.md`。
> **定位**:core 管 ~80% 資金(衛星 Phase 3 ~20% 另計);core 唔使做英雄——效率 + modest 真 alpha。

---

## 1. 點解係咁砌(每嚿嘢嘅證據)

| 設計 | 點解 | 證據 |
|---|---|---|
| 底倉永不因趨勢賣出 | 指數自我入出 = T2 結構拖累食晒 T1(已證冇 Jensen alpha);F&G 貪婪減倉實測蝕(loop 2 A3)| `topdays_exposure`;loop 2 |
| alpha 由 LEAP 兌現 | 槓桿 + 非 benchmark 工具 = 唯一結構解(finding #12);0.80Δ deep-ITM 贏晒 0.3/0.5/0.7(theta 損耗 8× 冚死槓桿 2.4×)| `leap_delta_sweep`;loop 1-4 |
| LEAP 必須右側閘 | 冇閘 MaxDD −99.9%(爆倉);遲滯版(<200SMA×0.98×5日)churn 減半、+1.0pp α(edge 偏 H2,標明)| `leap_timing`;loop 2-3 |
| 恐懼 dip 先入場 | RSI-2 低位入場先有 Jensen alpha(拉長出場殺 alpha);② 牛+恐懼 = 兩半最好+最安全 | `rsi2_200sma` 附錄;`market_regime_2d` |
| 賣期權 = 配菜唔係支柱 | CSP 利潤大半 beta、cost-sensitive(α+1.2 t1.8);SC 細 skim;兩者同源(相關+0.73)唔可以疊加當兩份 | `csp`;`shortcall_timing`;loop 1 |
| 年度再平衡 + 掃盈利 | 防底倉衰減(loop 2 教訓);+2.3pp 複合但 0 alpha = beta 維護 | loop 3-4 |
| 板塊 ETF 唔入 core | 0/28 因子過 Bonferroni;TAA 輸 SPY;完美年度輪動先 2× SPY 而我哋 IC≈0;EW premium 得 +0.6pp | `skill_curve`;`rotation_challenge` |
| 純期權 core 否決 | 85% 現金拖住,回報跟唔上(loop 2 B);但佢 Sharpe 0.86/DD −18% 可當防守檔案(見 §4 樹)| loop 2 |

## 2. 策略樹(regime 分枝 + 每枝做乜)

**狀態機 = 2D 象限:趨勢(遲滯 200SMA)× 恐懼(VIX zone:<18 平靜 / 18-28 中 / >28 恐慌)**

```
                          ┌──────────────────────────────────────────────┐
                          │  底倉 70-75% SPY:四個象限都揸住,永不趨勢沽  │
                          └──────────────────────────────────────────────┘
   ① 牛 + 平靜(74% 日子)     ② 牛 + 恐慌(6%)          ③ 熊 + 恐慌(12%)        ④ 熊 + 平靜(8%)
   ─────────────────────      ─────────────────────      ─────────────────────    ─────────────────
   · LEAP:持有(若在倉)      · ★ LEAP 入場窗:           · LEAP:閘關(離場後      · LEAP:閘關
     roll@63td,掃盈利返底倉     >200SMA × RSI-2<10          唔開新倉)              · 唔加倉、唔追
   · RSI-2>90 → 賣 covered       → 開/加 LEAP             · 唔接刀:洗盤/breadth    · 現金收息等趨勢
     call(≤25% 底倉,0.30Δ)  · 恐慌部署(揀一):          得「確認尺」地位,        翻身
   · F&G>75:停止賣 put、        a) 10pp 現金買 SPY          唔係開倉訊號           · (可選)防守 tilt:
     只賣 call 嗰邊              b) 10pp 抵押賣 CSP        · 已有恐慌倉:VIX<18       低波/防守板塊 ETF
   · 現金企喺 15% 目標           (20Δ/21DTE/PT50)          先沽返                   —— 未驗證,本機
                                  ——CSP 真數據應更好       · 底倉照揸(唔沽)         補測先用
                               · unwind:VIX<18
```

**Transition 規則(全部 T 日收市判定 → T+1 收市執行)**

| # | 由 → 去 | 訊號 | 動作 |
|---|---|---|---|
| T1 | 任何 → 趨勢向下 | 收市 < 200SMA×0.98 **連續 5 日** | LEAP 全沽(T+1);底倉不動;停開新 LEAP/CSP |
| T2 | 趨勢向下 → 向上 | 收市 > 200SMA(即時,唔使等 5 日)| LEAP 重新合資格,等 RSI-2<10 dip 先入 |
| T3 | 平靜 → 恐慌 | VIX zone 入 >28 | 若趨勢向上 = 象限② → 恐慌部署一次 |
| T4 | 恐慌 → 平靜 | VIX < 18 | 沽返恐慌加碼嗰批;CSP 到期唔續 |
| T5 | 年度 | 每年首個交易日 | LEAP 調返目標 premium %;底倉調返目標 %(補/減用現金)|
| T6 | roll | LEAP 剩 63td | 賣舊買新 1 年 0.80Δ;**超額盈利掃入底倉** |

**象限轉換頻率**:平均 6.4 次/年(遲滯後);最密 20 次(2002)。營運負荷:年均 LEAP 動作 ~2-3 次、
短 call ~10 次、恐慌部署 <1 次 —— 每日睇一次 dashboard 夠用。

## 3. 兩個校準(同一引擎,揀風險胃納)

| | **E1 保守(預設)** | **E2 進取(合用戶「risk/reward 最優+槓桿彈性」)** |
|---|---|---|
| 配置 | 底倉75 / LEAP prem 10 / 現金15 | 底倉70 / LEAP prem 15 / 現金15 |
| CAGR / Sharpe(96-26)| 14.44% / 0.76 | 16.56% / 0.78 |
| Jensen α | +4.42 (t3.7) | +5.92 (t3.4) |
| MaxDD / 最差63日 | −45.1% / −29.6% | −44.1% / −27.4% |
| Delta-notional 中位/p90/max | 128/160/178% | 151/199/218% |
| TE / 最差單月超額 | 6.5% / — | 9.7% / −12.8% |
| 邊個揀 | 想貼市少痛 | 接受單月大偏離換多 2pp/年 |

Sharpe 差 0.02 = 噪音;**呢個係胃納選擇,唔係邊個「更啱」**。兩個都符合「唔做短 DTE OTM」
(LEAP = 1年 deep-ITM;賣嗰邊全部 covered/secured)。
**統計註**(fresh-eyes 驗證):E1 過 Bonferroni×31(p≈0.003-0.007)+ DSR 0.983;E2(t3.4)Bonferroni
邊緣(p≈0.01-0.02)——揀 E2 係揀風險胃納,統計上最穩嗰個係 E1。

## 4. 防守分枝(樹嘅延伸,非必需)

持續 ③/④(熊市確認,例如 <200SMA 超過 1 個月):可選將部分現金/底倉結構轉做 **loop-2 B 檔案**
(15% LEAP-gated + 85% 現金)—— 佢喺回測係 Sharpe 0.86 / MaxDD −18% 嘅低 beta 檔案。
**But**:切換本身 = 指數擇時(T2 拖累風險)→ 只建議做「新資金入場點」選項,唔好成個組合切嚟切去。
防守板塊 tilt(低波/XLP/XLV/XLU)有舊證據(低波 = 防守非 alpha)但**未喺 portfolio 級驗證** → 本機補測先用。

## 5. 點解 core 冇板塊輪動(誠實交代 brief 原題)

Brief 任務 3 原文包括「板塊 ETF 擇時 rebalance 或現金」。測試+舊證據嘅答案:**唔做**。
量化輪動 forward IC≈0(0/28);最強 TAA 輸 SPY 3.8pp;板塊 ETF 動能「唔食」;EW 板塊 ≈ SPY(+0.6pp)。
板塊層真正得返嘅嘢:①防守 tilt(§4,待驗);②年度宏觀敘事(2022 能源嗰種)= **質性判斷 = Phase 3 衛星嘅工作**,
唔係 core 嘅機械規則。夾硬喺 core 加板塊分枝 = 加 turnover 加 noise 冇 alpha —— 違反鐵律 2 唔准砌唔存在嘅 alpha。

## 6. 執行計畫(scenario playbook,每朝 5 分鐘)

**每日讀數(dashboard 順序)**:①SPY vs 200SMA(+遲滯狀態)→ ②VIX zone → ③RSI-2 → ④F&G(>75?)→ ⑤持倉狀態。

| Scenario | 讀數 | 今日 action |
|---|---|---|
| 平常日(最多)| ①牛 ②平靜 ③中性 | 乜都唔使做 |
| 開 LEAP | 牛 + RSI-2<10(5日內)+ 未滿倉 | 買 SPY 1年 0.80Δ call 至 premium 目標(E1=10%/E2=15% NAV)|
| Roll | LEAP 剩 63td | 賣舊買新;盈利超標部分買 SPY |
| 賣 call | RSI-2>90 + 冇短call在倉 | 賣 21DTE 0.30Δ call,名義 ≤25% 底倉 |
| 恐慌窗 | 牛 + VIX>28 | 10pp 買 SPY 或賣 20Δ CSP(一輪一次)|
| 退恐慌 | VIX<18 | 沽恐慌加碼/等 CSP 到期 |
| 轉熊 | <200SMA×0.98 五日 | 沽晒 LEAP;之後唔開新倉;底倉唔郁 |
| 貪婪 | F&G>75 | 唔賣 put;唔加倉;call 嗰邊照舊 |
| 年初 | 首個交易日 | 再平衡返目標 |

**注碼粒度($300k-1M 組合)**:SPY deep-ITM 1年 LEAP premium 一張 ~US$15-25k → E1@10%($500k 組合 = $50k)
≈ 2-3 張;roll 用 limit order,分 1-2 日execute。短 call 名義 25%×$350k底倉 ≈ 1-2 張。粒度 OK,
組合 <$200k 就要將 LEAP 目標調做「1-2 張」規則制。

**HK 稅**:已入晒回測(股息 30% 預扣、無 CGT、國庫券息免預扣)。期權 P&L 無 CGT = 結構性有利。

## 7. 誠實結論 + 可信度分層(鐵律 2)

**答 brief 條題:「core 贏唔贏到 SPY B&H 嘅 Jensen alpha?」——贏到,但要講清楚邊部分幾實:**

| 層 | 結論 | 可信度 |
|---|---|---|
| 機制 | T1 擇時技巧存在(真數據 α 4-6%/yr t2-2.9);LEAP 結構兌現 T1;右側閘必要;0.80Δ 最優 | **HIGH**(多檔真數據 + sweep 排名全格穩)|
| 幅度 | 組合級 α +3.4~5.9pp/yr t3~4(31/31 格、全子窗口正、成本×2/cash0% 都企得住)| **MEDIUM**:RV-proxy IV(無真 VIX)、SPY-only、單一歷史路徑;2021+ 窗 t 得 1.6-1.8 |
| 配菜 | SC +0.9pp 係上限(sandbox 定價偏鬆);CSP 恐慌窗真數據 +1.2 t1.8;恐慌加碼 α≈0(唔蝕,擺明係 discipline 唔係引擎)| MEDIUM-LOW |
| 代價 | β≈1.0;MaxDD −44~45%;肥尾(單月 −12.8%);趨勢反覆年(2004/10/11/15/16 型)輸 2-7pp | **HIGH(certain)** |

**唔准吹嘅位**:再平衡+掃盈利嘅 +2.3pp 係複合/beta 維護,唔係 alpha;回撤唔係「SPY 一半」(嗰個係 loop-2
嘅底倉衰減 artifact,已修正);washout 唔係開倉訊號。

**本機重跑清單(升 magnitude 去 HIGH 嘅路)**:
1. `exp_leap_delta_sweep.py` + loop 3/4 headline 用真 ^VIX(+VIX3M term)重跑(command 喺 sweep results 檔尾);
2. QQQ(+SPMO)LEAP sleeve 版(QQQ RSI-2 期權入場 α 6.5%/yr t2.9 係四檔裡最強嘅真數據 prior);
3. CSP 恐慌窗用真期權鏈/真 VIX 重估(sandbox RV-lag 對佢最不利);
4. 防守板塊 tilt(§4)portfolio 級測試。

**升級路徑(接線)**:2D quadrant 邏輯 + 遲滯閘 + vol regime switch 入 `spine/`(gap register C5/C9);
scan.py 每朝出 §6 嗰張 scenario 表。
