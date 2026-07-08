# Karst 投資框架與方法論審查(2026-07-03)

> 審查方法:三個唯讀 agent 抽取 spine/web/thesis 實作事實(全部 file:line 佐證)+
> 本 session 的四層 refinement(top-10-days → capital efficiency → alpha=T1+T2 分解 →
> tier-1 指標決策)+ 全部 20+ 篇 `backtest/results/`。
> 證據標記沿用 repo 紀律:✅ 已回測/已驗證 · 📄 從程式碼/文件推得 · ⚠️ 假設,待驗。
> 姊妹篇:`2026-07-03_dashboard_decision_experience.md`(決策體驗)、
> `ROADMAP_AGENTIC.md`(全自動化實施計畫)。

---

## 一、值得保留的地基(先說,防止未來 session「修好」它們)

1. **證據優先紀律**:DSR/PSR 多重檢定校正、mirror/increment/horizon 三原則、
   負面結果照樣入檔(VCP、triple confirmation、sector character 全是紀律性否定)。✅
2. **「價格圖裡沒有的資訊」防火牆**(ARCHITECTURE §3):價格訊號歸 Phase 0/1/4,
   質性歸 Phase 3,擇時永不乘進結構分。這是整個系統最重要的架構決策。✅
3. **可證偽靶心唯一**:forward IC ≥ 0.05(質性排序)。20+ 回測已證 price/volume
   排序 IC≈0,不要回頭挖。✅
4. **透明引擎**(純 pandas,不用框架):40 行 engine 人人可審計,DSR 自持。✅

---

## 二、發現(按嚴重度排序)

### P0 — 已驗證的訊號沒接上/程式與文件矛盾(修這些最便宜、最值錢)

**P0-1|Insider 訊號:算了、顯示了、但從未影響任何分數,且 horizon 錯配**
- 事實:`orchestrator.py:46-49` 算出 `conf_eff`(±30% bounded 修正,
  `providers.py:85-89`),但 `expression.py:66` 的分數公式用的是原始 `th.unit`
  ——`conf_eff` 只進卡片顯示(`card.py:18-22`),**對 0/100 分數與 BUY_DIP/WATCH/AVOID
  動作零影響**。📄
- 更深一層:`exp_insider_validate.py` 證明 insider 是 **21d 短期催化**(t=5.12,63d 歸零、
  126d 轉負)✅,但現在的接法是 180 天回看窗(`thesis/insider.py:35`)、無衰減、
  掛在長期 confidence 上——即使接回去,horizon 也是錯的。
- `providers.py:7-9` docstring 聲稱 confidence 會 multiply into sizing——與程式碼矛盾。📄
- ~~**修法**:把 insider 從 confidence 修正改成**擇時側的 21d 戰術 tilt 欄位**~~
  **【修法已更正 2026-07-06(gap register #2):** 21d 版係 regime artifact(07-05
  `insider_rigor` R8:大型股拉長到 2006,21d t1.1 唔顯著)。**正確修法 = 接細價股
  (<$2B)12 個月 portfolio tilt(vs IWM,bounded overlay)**,見 `insider_literature`
  FINAL。`conf_eff` 廢除或明文降級為顯示註記 + 修正 docstring 照舊。驗收:tier-2
  long-only mirror、**12 個月 horizon、size-matched vs IWM** 嘅 A/B 增量回測,過 DSR。
  工作量:M。】

**P0-2|Credit 風險軸與兩軸背離:已驗證卻完全缺席,單一 market_score 主動掩蓋它**
- 事實:Phase 0 閘只有 trend/VIX/term/IWM-breadth/SPMO-RS(`context.py:54-115`),
  **無 credit(HYG/LQD)、無兩軸概念**;全 repo 只有 `regime.py:8` 一行註解承認
  「later add」。📄
- ~~但已驗證:credit > VIX 作為 risk regime 指標~~ **[2026-07-06 更正:此結論已被 07-05
  `results/2026-07-05_market_regime_2d.md` 推翻——credit 軸 H1/H2 反符號、對 VIX 無穩定增量,
  已剔除;風險軸 = VIX,趨勢 = 安全度修正。本 P0-2 修法(加 _credit_stress)作廢。]**
  (原文保留:credit > VIX 作為 risk regime 指標(KC Fed RORO 相符);趨勢軸與風險軸
  corr 僅 0.64,**背離**(bull+risk-off / bear+risk-on)標記 2018/2020 頂、2022 底 ✅
  (memory `regime-and-fear-greed-findings`)。web 的 market_score 把 5 因子壓成單一
  0-100(`market_score.py:20,120`)——正是 finding #1 說「會掩蓋兩軸結構」的做法。
- **修法**(最小改動,agent 已定位):`context.py` 加 `_credit_stress()`
  (HYG/LQD 比值 vs 其 200SMA/63d RS)→ `schemas.py` MarketContext 加
  `credit_rs / risk_axis_label / trend_risk_divergence` → 與現有 `fragile`
  (`context.py:83`)**整併**成單一風險軸,不要疊第三個 ad-hoc 布林。
  market_score 拆成趨勢軸+風險軸兩個子分數+背離徽章(見姊妹篇 §3)。
  第一步:先探測 `data.load("HYG")/("LQD")` 的歷史覆蓋(agent 未驗證)⚠️。
  驗收:渲染面板能重現 2018-Q4 / 2020-02 / 2022-10 三個背離事件。工作量:M。

**P0-3|校準迴路是斷的:outcome 回填程式碼不存在,完整 schema 從未寫入一筆**
- 事實:`track_record.jsonl` 有**兩套 writer、schema 不一致**;含
  `kill_condition/entry_ctx/outcome` 的完整 schema(`log_predictions.py:53-65`)
  **實測 164 筆中 0 筆**——它從未被排程呼叫;outcome 回填程式碼**全庫不存在**
  (只有 `log_predictions.py:64` 初始化 None);confidence 校準映射函式也不存在
  (`DESIGN.md:178` 自認未決)。📄
- 後果:DESIGN §6 的「confidence 對戰績校準」——NHITL 的核心主張(confidence 是
  可算可校準的,不是信念)——**目前只是設計文字**。不修,confidence 就是
  「換了名字的信念」,審查必須直說。
- **修法**:(a) 統一成單一 writer(超集 schema);(b) `log_predictions` 併入
  `daily_ic.cmd` 排程鏈;(c) 實作 outcome 回填 job(掃描到期預測,回填實現報酬
  與 kill_condition 狀態);(d) 校準映射等 ≥20 筆到期後再建(先把資料流通了)。
  驗收:track_record 每日以完整 schema 增長;第一批 +21d 到期自動回填。工作量:M。

**P0-4|IC ≥ 0.05 是文字,不是程式**
- 事實:閾值散落 4 處文字/docstring(`DESIGN.md:17,136`、`forward_ic.py:4,176`、
  `SKILL.md:112`),`compute_ic()` 只印數字,無 PASS/FAIL 判定。📄
- **修法**:`forward_ic.report()` 加狀態機:`PRELIMINARY`(dates<20 或 matured<50)/
  `PASS` / `FAIL`,輸出 JSON 供未來 auditor agent 讀。現況:僅 3 個交易日、0 筆到期
  ——靶心目前無檢定力,這正是要現在就把管線修好的原因。工作量:S。

### P1 — 方法論加固(標準,不是新點子)

**P1-5|Walk-forward/OOS 未成為預設**:多數實驗是全樣本+DSR;閾值(VIX 30/25、
F&G 80、RSI2 10/90)是全樣本挑的(HANDOFF #5 有跨年代 robustness 檢查,部分緩解 ✅)。
修法:寫進回測 checklist——任何新規則必須 IS/OOS 或 walk-forward + DSR;
2b 實驗已示範格式。工作量:每實驗 S。

**P1-6|Survivorship**:tier-2 廣宇宙 +12.5% CAGR 的主張建立在現任 S&P 成員上
(ARCHITECTURE §6 自認)。修法:point-in-time 成分股來源,或至少在所有引用處
標注折減;不修就別把 +12.5% 當 sizing 依據。工作量:M。

**P1-7|無持久化價格庫**:每次回測重新抓網路,不可重現且受 Yahoo 限流
(本 session 已討論)。修法:parquet/DuckDB 快照 + as-of manifest,回測模式
`KARST_DATA_SOURCE=store`;實驗檔記 manifest hash。順帶解 headless 部署痛點。工作量:M。

**P1-8|稅務/成本現實層缺席**:「對標無腦 QQQ 稅後」寫在 Charter 裡但無稅模型。
⚠️ 假設用戶為香港稅務居民(無資本利得稅、美股股息 30% 預扣)——若成立,
B&H 的股息拖累更重、短線進出的稅務成本近零,**對 MR/擇時類策略相對有利**,
這會實質改變 sleeve 比較。修法:jurisdiction 設為 config 參數(HK 預設),
capstone 級比較全部帶稅後欄。**需用戶確認稅務居民地**。工作量:S。

**P1-9|tier-1 擇時重複實作**:`expression.py:11` 自認 scorecard 把 RSI-2 烘在內、
與 timing 欄位重複,Phase 4 未統一。低急迫(能用),但每次改 RSI-2 邏輯要改兩處。工作量:M。

### P2 — 組合層缺席(結構性最大洞)

**P2-10|兩個 sleeve 已上線(tier-1 期權、tier-2 做多),但無資本配置框架**:
無合併淨值、無 sleeve 間正交性量測、無現金/乾火藥帳本。而本 session 的
capital-efficiency 發現 ✅(恐慌部署的 conditional Sharpe 1.0-1.7 > B&H,
deployed-cap 年化 24-74%)說明系統 edge 的正確表達正是「乾火藥 + 部署計時器」
——但系統沒有乾火藥的概念。修法見 `ROADMAP_AGENTIC.md` Phase B(paper ledger +
sleeve registry + 正交性矩陣 + 乾火藥政策);指標按 memory `tier1-metrics-decision`
(不用 Jensen alpha;IC/資本效率/PnL÷曝險/conditional Sharpe/DD/正交性;
基準 SPY vs SPY、QQQ 與 SPMO 各 vs {自己, SPY})。工作量:L。

### P3 — 衛生

- `spine/__init__.py:7-11` docstring 停在 Phase 0(Phase 1/4 實際已建)——過時自述,
  會誤導接手的 agent。⚠️ 順手修。
- 計算了但從未渲染的欄位清單(MarketContext 11 個原始因子、`thesis.kill_condition`、
  rotation drivers/caveats、逐卡 caveats)→ 見姊妹篇 §5,渲染或刪,別留殭屍。
- `lint.py` 健檢無排程——併入每日排程鏈。工作量:S。

---

## 三、不建議做的事(反建議,同樣是審查產出)

1. **不要再挖 price/volume 排序 alpha**——28 因子 0/28 過關(KARS_MEMORY §8)✅。
2. **不要建 11 板塊 trend/chop 性格地圖**——2b 已否定,DSR 未過 ✅。
3. **不要把 VIX 和 F&G 平均/混合**——極性相反會互相抵銷,已驗證 ✅;
   VIX 管進場(恐懼),F&G 管出場(貪婪),各自為政。
4. **不要遷移 vectorbt 或任何回測框架**——透明引擎+自持 DSR 是方法論護城河
   (2026-06-30 已決策,本審查維持)。
5. **不要追查 capstone 的 beta≈0.7**——原始 run 不可恢復,結論已被四層 refinement
   三角驗證(0.12–1.00 全曝險域 relever 不翻正)✅,再挖是沉沒成本。
6. **不要在無用戶明示下改變「決策支援,人執行下單」邊界**——
   `.claude/skills/karst` 的鐵律;全自動化指的是決策管線,不是下單。

---

## 四、優先順序一覽(建議執行序)

| # | 項目 | 為什麼先 | 工作量 |
|---|---|---|---|
| 1 | P0-3 校準迴路(schema 統一+排程+回填) | 每天不修就流失一天不可補的校準資料 | M |
| 2 | P0-2 credit 軸+兩軸背離(compute 端) | 已驗證訊號,閘與面板都在等它 | M |
| 3 | P0-1 insider 改接細價 12月 portfolio tilt(~~21d~~ 已更正,見上) | 已驗證 edge 正在閒置;含 A/B 驗收 | M |
| 4 | P0-4 IC 判定程式化 | S 工作量,auditor agent 的前置 | S |
| 5 | P1-7 價格庫 | 一切回測重現性的地基 | M |
| 6 | P2-10 組合層 v0(ledger+乾火藥) | 兩 sleeve 已備,edge 表達在此 | L |
| 7 | P1-5/6/8 方法論標準+稅務參數 | 寫成 checklist 從此生效 | S-M |

(P3 衛生項順手做,不佔優先級。)
