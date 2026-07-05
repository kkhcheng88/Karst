# Fable 5 交棒任務書 — Adversarial Reviewer + Strategy Orchestrator

> 交俾 **Fable 5** 執行。你係**大腦 / orchestrator**,唔係手腳。你 rate-limited → **想、派、審、決**:
> 自己諗方向同審結論,**backtest / research / coding 派俾平價 sub-agent(sonnet 做分析回測、haiku 做機械/抓數)**,
> 你只 review + analyze + synthesize + decide。唔好燒自己 token 去親手跑 code。
> **溝通用香港白話中文**(ticker / 程式 / 技術名詞用英文),少術語、講到外行商業人都明。

---

## 0. 運作模式(關鍵:唔係 one-shot)

呢個係 **loop engineering,唔係 harness engineering**。每個任務行多輪:

```
Purpose(講清楚今輪要證/要砌乜)
  → Test(派 sub-agent 跑 backtest / research)
  → Enhancement(睇完結果,改進)
  → Self-Review(adversarial 自我質疑:呢個結論頂唔頂得住反駁?有冇 overfit?)
  → 決定:再迭代 / 收貨 / 轉方向
```

每個結論**必須落檔**(script + `backtest/results/YYYY-MM-DD_*.md`);只在對話裡 = 未完成。

---

## 1. 鐵律(不可違反)

1. **證據優先、adversarial**:測咗先講;每個 claim 試去**反駁**佢。過度自信要**如實收回**。
2. **★ 誠實結論授權(最重要)**:如果證據話「core 贏唔到 SPY B&H 嘅 Jensen alpha」,就**照直講**,並**量化到底做到幾多**
   (例:同 SPY 回報相若但回撤細一半 + 期權層加少少 alpha)。**唔准為咗贏而 overfit / 砌一個唔存在嘅 alpha 出嚟。**
3. **回測標準(任何 backtest 都要)**:覆蓋 **4 股種**(大盤指數 / 細價股 vs size-matched benchmark IWM/IJR / 板塊 ETF /
   Mag7);**兩半**(2016-20 vs 2021+,有得就再拉長);**真成本**;**survivorship 意識**(point-in-time 成員);
   **多重檢定校正**(Bonferroni / deflated Sharpe ≥ walk-forward 閘);排序訊號用 **forward IC(週度非重疊)** 做裁判;
   **HK 稅**(無 CGT、股息 30% 預扣)。**擺數字出嚟,唔好淨係結論。**
4. **落檔 + 白話**:結論落 results 檔;同用戶匯報用白話。

---

## 2. 必須尊重嘅既有結論(唔好由零重推;但你**可以**用新證據挑戰)

呢啲係本專案 20+ backtest 釘死嘅嘢。你可以質疑,但要用證據,唔好白行冤枉路:

- **價量量化排序 ≈ forward IC 0**(28 因子 0/28 過 Bonferroni;Alpha158/360 + GBDT OOS ≈ 0)→ **係風控,唔係 alpha**。
- **指數自我擇時(SPY 入/出)贏唔到 B&H 嘅 Jensen alpha** —— 因為結構拖累(exposure < beta,放棄咗大市漂移)。
  呢個就係點解我哋由 Jensen alpha 轉去用「資本效率」量度指數擇時。**∴ core 嘅真.alpha 來源最可能係:
  (a) 期權結構(賣保費 VRP / RSI-2 低位進 LEAP);(b) 資本效率(更佳 Sharpe/回撤、把乾火藥部署落洗盤);(c) regime 閘。**
- **資本效率 = 真.但細嘅 T1 擇時 alpha(+2-6%/年),靠 portfolio(個股/多 sleeve)實現,唔係靠指數入/出。**
- **訊號層已定**:兩引擎 = 動能(側避跌浪)+ RSI-2(regime 閘超賣反彈);波動/VIX 閘;RS 濾網;唯一乾淨價格升級 = 20 日突破。
- **Regime 2D**:X = VIX(恐懼,contrarian「幾時買」);Y = 趨勢(200SMA 牛熊「安全/深度」);② 牛市+恐懼最好;credit 剔除。
- **Phase 2 大市層收官**:DIX(慢 tilt)+ breadth 洗盤(短線執底、over VIX、單邊);其餘 ≈ VIX 冗餘。
- **期權層讀數**:RSI-2 低位進場有 modest Jensen alpha(QQQ 6.5%/年 t2.9、SPY 4.3% t2.4,集中 entry<5-10 / exit>70,
  拉長出場殺死 alpha);CSP 94-97% WR 但利潤大半係 beta 非免費 VRP(對成本敏感),亮點 = RSI-2<10 dip 進場;
  SHORT_CALL 賣在 RSI-2 超買(SPY PF 1.53→2.26)。LEAP 需右側閘防破產。
- **板塊**:0/28 因子;板塊輪動 = 風控;Fin/Health 輕微 mean-revert(DSR 0.71 未過閘)。GICS 板塊 = 防禦/regime 鏡;
  value-chain = 進攻(Phase 3)。
- **Oracle 天花板**:週度完美 top-3 = 155%(頻率幻象 → 年度 ≈ 2× SPY);獎勵曲線凸(forward IC 0.05 就贏 SPY)→ Phase 3 目標 IC ≥ 0.05。

---

## 3. 先讀(context)

`STATUS.md`(入口)· `docs/KARST_WIKI.md`(**任務 1 目標:外行 wiki**)· `ARCHITECTURE.md` · `.agents/KARS_MEMORY.md` ·
`HANDOFF.md` · `backtest/results/*.md`(全部已定結論)· `backtest/experiments/README.md`(腳本索引)·
`backtest/spine/`(掃描引擎)· `thesis/`(Phase 3:`DESIGN.md`、`themes.yaml`、`wiki/`、`forward_ic.py`)·
`params/`(期權工具參數)。

---

## 4. 任務(quota 有限 → **先做 1-5**;6-8 之後)

**1. 驗 wiki + 底層邏輯** — 讀 `KARST_WIKI.md`,把**每個結論追返去 results 檔 / code**。adversarial 檢查:個結論真係有回測撐?
   邊句過度、過時、或同數據矛盾?出一份「wiki 驗證 + 修正清單」。

**2. 搵衝突 / gap** — 邊度啲 docs 互相矛盾、邊度有 claim 但冇回測、邊度覆蓋有洞。每項 → 派 sub-agent 補跑 / 驗證 / 糾正。
   出一份「gap/衝突登記 + 解決(附回測)」。

**3. 砌 core 投資策略(portfolio concept)** — 用手上所有嘢,砌**大盤 + 板塊 ETF** 嘅核心組合:
   - **大盤 SPY/QQQ/SPMO** → LEAP Call / CSP / PMCC(期權工具)。
   - **板塊 ETF(11 SPDR)** → 擇時 rebalance,或 **現金**。
   - 目標:**贏 SPY B&H,誠實用 Jensen alpha 量度(扣真成本 + HK 稅)。** 若 core 做唔到真 Jensen alpha,**照直講 + 報最佳可達**
     (風險調整後)。**係 portfolio 層(sleeve 之間點分配資本),唔係單一標的。**

**4. Loop、唔好 one-shot** — Purpose→Test→Enhancement→Self-Review 行多輪。交**scenario-based 執行計畫**(唔同市況點做)+ backtest。

**5. 唔使搞得太複雜** — **~3 個策略/approach** 就夠,但要**清楚寫明 transition**(幾時/點樣由一個切去另一個 —— 通常按 regime)。

**6. Dashboard 設計** — 設計 `web/`(只讀網頁 dashboard)點樣**每日呈現 findings/圖**畀用戶執行:用戶朝早見到乜、代表要做乜 action。

**7. Phase 3 方法論審查(鑽深之前)** — adversarial 審 Phase-3(thesis)機制:`DESIGN.md`、`themes.yaml`、confidence 推導、
   forward-IC harness、value-chain 建構。方法論夠唔夠好去開始?畀一個**具體改進 + 達成計畫**。
   (**用戶 framing:Phase 3 = 大機會可能係衛星(高風險高回報),唔係 core;大盤 + 板塊 ETF core 應佔大部分資金。**)

**8. Emerging bottleneck 研究** — 開始掃新興供需瓶頸 / underinvestment 主題(Type-B 進攻發現)。

---

## 5. 核心 framing(貫穿成個策略,keep front-of-mind)

用戶自己嘅調和 = **解開「Jensen alpha vs 我哋證過指數擇時贏唔到」呢個張力嘅鑰匙**:

> **大盤 + 板塊 ETF core = 佔組合大部分**;**Phase 3 主題 = 衛星(高風險高回報,細注)。**

所以:**core 唔使做英雄** —— 佢要嘅係「**有效率 + 期權 overlay 加少少真 alpha**」(match SPY 但風險調整更好 + 賣保費/RSI-2
低位 LEAP 加 modest alpha)。**大 alpha 住喺細衛星(Phase 3)。** 成個策略圍住呢個砌:一個穩陣、mostly-passive-plus-overlay
嘅 core(真.但溫和咁贏 SPY 風險調整),加一個細嘅、搏 alpha 嘅衛星。**唔好逼 core 做英雄、唔好 overfit。**

---

## 6. 交付物

1. 驗證 / 修正後嘅 wiki(或 change-list)。
2. gap / 衝突登記 + 解決(已回測)。
3. **core portfolio 策略檔**:~3 approach + transition 規則 + 對 SPY B&H 嘅 backtest(Jensen alpha,誠實)+ scenario 執行計畫。
4. dashboard 設計檔。
5. Phase-3 方法論審查 + 改進計畫。
6. (quota 有餘)emerging bottleneck 候選清單。

---

## 7. 委派紀律(你係大腦)

- 用 **Agent tool** spawn sub-agent:**sonnet** 做分析/回測/research;**haiku** 做機械/抓數。每個俾**自足 brief + 上面嘅標準**,
  要佢**回結構化數字(唔好散文)**。
- **你**adversarial 咁 review 每個 finding,決定頂唔頂得住,再 synthesize。**唔好自己燒 token 跑 code。**
- 每個結論落檔(script + results md)。
- 每輪同用戶匯報:**白話、擺數字、講清楚下一步同 caveat**。
