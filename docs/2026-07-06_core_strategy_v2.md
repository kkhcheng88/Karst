# Karst Core 策略 v2 —— 真數據版(取代同日 sandbox v1)

> **一句講晒**:底倉 SPY 揸住唔郁 + 一條 **SPY+QQQ 對半、純 200SMA 閘、月度補彈藥**嘅 LEAP 引擎
> + 現金 buffer 收息。冇板塊輪動、冇 dip 等入場、冇貪婪減倉 —— 全部真數據測死咗先剔走。
> **對 SPY B&H(總回報、HK 稅後)Jensen α:保守 model +6.5pp/年(t3.1)/ base model +12.4pp(t5.4)**,
> β≈1、MaxDD ≈ SPY(−54~56%)。
> **地位**:v1(`2026-07-06_core_strategy.md`)係斷網 sandbox 用 proxy-IV 砌嘅,已 superseded;
> 本檔每個數都嚟自真 ^VIX/^VXN + 真總回報,經獨立 adversarial 覆核 + 獨立重跑驗證。
> 證據鏈:`results/2026-07-06_leap_real_sweep.md`(引擎)→ `_core_assembly_real.md`(總裝)→
> `_core_topup.md`(機制修正+勝出格)→ `_sector_capeff.md`(板塊判死)。
> 用戶約束(2026-07-06 親答):MaxDD 貼 SPY 可接受、槓桿無硬上限、$500k-1M、core/衛星 70/30。

---

## 1. 點解係咁砌(每嚿嘢嘅證據,全部真數據)

| 設計 | 點解 | 證據 |
|---|---|---|
| 底倉永不因趨勢賣出 | 指數現貨入/出 = T2 結構拖累食晒 T1(真數據恒等式拆解);防守 tilt portfolio 級都測埋 = 冇 alpha | `alpha_decomp`;`sector_capeff` H3 |
| alpha 由 LEAP 兌現 | 槓桿+非 benchmark 工具 = 唯一結構解;真數據引擎級 α:0.80Δ GATED +5.7pp t5.5(最 model-免疫格)| `leap_real_sweep` |
| **純 200SMA 閘(冇 dip、冇遲滯)** | GATED 贏 GATED+DIP(dip 過濾=純曝險削減,miss V 型反彈;71 個 episode 攤開,adversarial 覆核 SURVIVES);HYST 無淨增值 | `leap_real_sweep` + 覆核 |
| **SPY+QQQ 對半** | mix 喺 9/9 對比全勝 SPY-only(QQQ 真數據 prior 兌現)| `core_assembly_real` |
| **月度 top-up(機制核心)** | 年度先補彈藥 → sleeve 有 40-60% 合資格日冇錢開倉;月度補錢令 cash-starved 跌到 10%/7%,保守 model 下 α 由 t1.8(邊緣)升到 **t3.1(穩)**;on-roll 版反而更差(負面照報)。**挑戰測試(2026-07-07)**:RSI-2<10 觸發補錢 = α 打平但 cash-starved 更差(15%/14%);月度補錢+dip 先入場 = 全窗輸(保守 α +5.6 vs +6.5)—— 月曆版維持 | `core_assembly_real` + `core_topup` + `topup_timing_ab` |
| 板塊 ETF 唔入 core | 三個未測角度真數據 control-leg 全滅:dip 輪動 12 格 0 顯著;**恐慌窗買殘板塊顯著輸畀買 SPY(−2.45%/次 t−2.52)**;防守 tilt 冇 alpha。板塊年度敘事 = Phase-3 衛星工作 | `sector_capeff` H1-H3 |
| 現金 buffer = T-bills 預設 | cash vs IEF 冇顯著格;債贏 2008/2020 輸 2022(regime-conditional)→ 債係宏觀判斷唔係系統規則 | `sector_capeff` H4;`portfolio_rotation` |
| **底倉 = SPY(唔係 QQQ/SPMO)** | A/B 實測(同一 LEAP 引擎):QQQ 底倉 = **beta 賭注** —— β 1.14→1.25 而 α-t 反而跌(base 5.4→4.5 / damp 3.1→2.7)、MaxDD 更深(−61.6%,仲未計 2000 年 3 月頂);50/50 長史同 SPY 打平;SPMO 得 9.7 年單一動能牛 regime,damp 下有 α 改善旗但**未見過熊市** → 唔夠證據換底倉,列 watchlist(觸發:撐過一次真熊市,或長史動量因子 proxy 喺同一 harness 覆核)| `2026-07-07_base_mix.md` |
| 恐慌加碼唔入機械規則 | 板塊版顯著負;SPY 版舊證據 α≈0(discipline 唔係引擎)| `sector_capeff` H2 |
| 賣保費(covered call / CSP)= 可選人手 skim | 真數據 priors 細而正(06-30 檔);**唔計入本檔 α**,免疊加水分 | `shortcall_timing`;`csp` |

## 2. 策略規格(機械規則,每條有時序)

**組合 = 底倉 SPY(目標 70%)+ LEAP premium 預算 b% NAV + 現金(^IRX)**;LEAP = 1 年期 call,
SPY leg 用 ^VIX、QQQ leg 用 ^VXN 定價參考,premium 預算對半分兩 leg。

| # | 規則 | 訊號(T 收市)| 動作(T+1 收市)|
|---|---|---|---|
| R1 | 趨勢出場 | 該 leg 標的收市 < 200SMA | 沽晒該 leg LEAP;底倉不動;premium 現金留倉收息 |
| R2 | 趨勢入場 | 該 leg 標的收市 > 200SMA | 買返該 leg 到 premium 目標(有幾多錢買幾多)|
| R3 | **月度 top-up** | 每月首交易日 | 把 sleeve premium 現金池補返到 b% NAV(由底倉轉;超過唔郁、唔強制沽)|
| R4 | Roll | LEAP 剩 63 個交易日 | 賣舊買新 1 年;**超額盈利掃返底倉**(beta 維護,唔當 alpha)|
| R5 | 年度再平衡 | 每年首交易日 | 全組合調返目標比例 |
| M1(可選人手)| 恐慌部署 | 牛 + VIX>28 | 細注買 **SPY**(唔好買殘板塊——已證輸);α≈0,係 discipline 唔係引擎 |
| M2(可選人手)| 貪婪收油 | F&G>75 | 唔加倉(舊證據:>75 後 63d 回報衰減)|
| M3(可選人手)| 賣保費 skim | RSI-2>90 / 恐慌窗 | covered call ≤25% 底倉 / CSP 一輪一次;參數見 `params/`+`options_engine.py`(以 code 為準)|

**冇嘅嘢(同 v1 嘅分別)**:冇 RSI-2 dip 入場閘(降級)、冇遲滯出場(無淨值)、冇板塊分枝(判死)、
冇 2D 象限機械規則(quadrant 留做 dashboard context + 衛星參考;core 機械層得 200SMA 閘一個訊號)。

**風控架構(分層,回應用戶「exit rule 保護」)**:①sizing 預算(b% premium cap = 第一道,免費)
→ ②入場閘(牛市先開槓桿)→ ③exit rule 只落槓桿腿(R1;長 option 最多輸 premium)→ ④底倉唔設
exit(佢嘅風險由「冇槓桿」本身管理;加 exit = T2 拖累燒 alpha)。第三方佐證(Tier-2,2026-07-08):
Backtest Everything 頻道 married-put 掃描 —— SPY/QQQ 保護性認沽 **0/32 配置贏 B&H**、回撤減幅極微,
「揸 SPY 就唔好買你唔需要嘅保險」(詳 Reference distillation Addendum 2026-07-08)。

## 3. 兩個校準檔(同一引擎,揀 model-risk 胃納)

| | **E-穩(Δ0.70)** | **E-旗艦(Δ0.50,勝出格)** |
|---|---|---|
| 規格 | C-monthly / b15 / Δ0.70 / mix | C-monthly / b15 / Δ0.50 / mix |
| α base(m0.85)| +7.8pp(t4.8)| **+12.4pp(t5.4)** |
| **α 保守(damp0.4)** | **+4.6pp(t3.0)** | **+6.5pp(t3.1)** |
| CAGR base/damp | 17.1% / 13.8% | 22.3% / 16.1% |
| MaxDD | −53.5~53.9% | −54.5~55.6% |
| 最差滾動月 | −37.5~38.1% | −39.8~41.6% |
| Delta-notional 中位/p90 | 86-90% / 118-144% | ~120% / 172-216% |
| 邊個揀 | 想 model 風險細(deep-ITM vega 細,IV 假設影響低)| 用戶 profile(MaxDD 貼 SPY、槓桿無上限)嘅 risk/reward 最優 |

再保守:b10 版(Δ0.70:damp +3.2pp t3.0 / Δ0.50:damp +4.4pp t3.0)—— 全部 C-monthly 格喺保守
model 都顯著(t2.8-3.1),**引擎唔靠 model 假設食糊,靠嘅係注碼同補彈藥機制**。

## 4. 統計紀律(唔准吹嘅位)

- **Trial registry**:總裝 18 格 + top-up 24 格 = 42;勝出格 Bonferroni×42:**base p=2.4e-6 過**;
  **保守 model p=0.095 —— 過 0.10 唔過 0.05**;DSR 1.000 過。誠實讀法:「大概率係真,
  用最嚴格鏡未到決定性」。
- **子窗誠實**:α 集中 H2 2011-26 + 2016-20;**2021+ 子窗 t 得 0.8-1.6(弱)**;H1(SPY-only 代理)弱。
  單一歷史路徑,冇 bootstrap。
- **Model 風險邊界**:30d VIX→1y IV 映射係本回測最大假設;damp=0.4 係 first-order 保守近似
  (adversarial 覆核指定);真 crash term-structure 倒掛更複雜。**接線前要用真期權鏈 spot-check roll 日**。
- **無 smile/skew、European BSM、QQQ 窗 2001+ 起(miss dot-com 頂)、成本 0.5%/邊假設**(1%/邊
  sensitivity α 只跌 0.3pp —— 成本唔係 swing 變量)。
- **月度 top-up 嘅結構效果**:全期平均底倉曝險 ~72%(唔係名義 70+);MaxDD 變淺一部分嚟自呢個
  beta 縮水(驗證員 V3 已 forensics,唔係 bug);最差滾動月 −40% 級(2020 型急跌,閘未切走前)——
  肥尾照舊,冇「回撤減半」童話。

## 5. 執行 playbook(摘要;**完整獨立操作手冊見 `docs/2026-07-07_core_playbook.md`**)

**每日(1 分鐘)**:①SPY vs 200SMA ②QQQ vs 200SMA —— 有 cross 就 T+1 執行 R1/R2。完。
(VIX/F&G/RSI-2 係 M1-M3 可選項同 dashboard context,唔係必要動作。)

**每月首交易日(5 分鐘)**:R3 top-up —— sleeve 現金補返到 15% NAV。

**每季/roll 時**:R4 —— LEAP 剩 63td 就 roll,盈利掃返底倉。

**每年首交易日**:R5 全組合再平衡。

**$500k 粒度(勝出格)**:SPY leg ~$37.5k premium ≈ 5 張(近期 ~$7k/張);QQQ leg ≈ 8 張(~$4.7k/張);
rounding drag 實測 +0.01pp 可忽略。$200k 以下先要轉「按張數」規則。

**HK 稅**:benchmark 已扣股息 30% 預扣;期權 P&L 無 CGT;LEAP 唔收息(冇預扣)= 結構性著數,已入數。

## 6. 同 70/30 大格局嘅關係

Core(本檔)管 70% 資金 —— 佢唔使做英雄:保守讀法 +4.6~6.5pp/年真 α 已經超額完成「效率 + modest
alpha」嘅任務。衛星 30% = Phase-3 質性 thesis(年度板塊/主題敘事嗰種 alpha 住喺嗰度,唔喺 core 機械層)。

## 7. 升級路徑(接線 to-do)

1. **真期權鏈 spot-check**(接線前必做):揀 5-10 個歷史 roll 日對真 LEAP 報價,驗 30d→1y 映射同 skew
2. spine 接線:200SMA 閘 + 月度 top-up 日曆 + roll 倒數入 `scan.py` 每朝輸出(§5 表);2D quadrant 做 context 欄
3. Forward tracking:每月記實際 vs model premium,damp 版 α 做保守追蹤基準
4. 衛星層(Phase 3)照 ROADMAP A1(校準迴路)先行 —— 佢係而家全系統最大單一 P0

## 8. 版本紀錄

- **v2(本檔,2026-07-06)**:真數據全鏈(Loop 1-4)+ adversarial 覆核 + 獨立重跑驗證。核心改動:
  0.80Δ 全格贏(draft)→ Δ 係注碼選擇且 Δ0.50 勝出格;RSI-2 dip 閘 → 降級;遲滯 → 移除;
  年度再平衡 → 月度 top-up(機制核心);板塊三假設 → 判死;α +3.4~5.9(proxy)→ 保守 +6.5(t3.1)/
  base +12.4(t5.4)。
- v1(sandbox,RV-proxy IV,SPY-only):`2026-07-06_core_strategy.md`【SUPERSEDED】
