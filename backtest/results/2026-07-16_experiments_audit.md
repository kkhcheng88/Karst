# backtest/experiments + backtest/results 盤點審計(2026-07-16)

> **性質**:唯讀盤點,冇刪改任何檔案。目的:回應用戶 memory 記低嘅「experiments 104檔冇歸檔」整理債務,
> 畀 gatekeeper 一張證據齊全嘅清理判斷清單。**結論:實際狀況比 memory 描述好——README 自己記錄嘅孤兒
> 清單同宜家嘅檔案系統狀態一致(冇 drift),真正新發現係一條「結論已被推翻但冇標註」嘅個案(§4)同
> 一條 stale 副 worktree。**

---

## 1. 清點數字

| 項目 | 數量 |
|---|---|
| `backtest/experiments/exp_*.py`(git tracked) | 129 |
| `backtest/experiments/_*.py`(底線開頭,gitignore scratch helper,唔算實驗) | 1 |
| `backtest/results/*.md`(現行,git tracked) | 122 |
| `backtest/results/_archive/*.md`(已歸檔) | 2 |
| `backtest/results/_scratch_groupB/`、`_scratch_groupD/`(gitignored 中間檔) | 8+11 個 .txt,untracked |
| **配對率** | 129 個腳本中 124 個有結果文件覆蓋(直接或透過共用 addendum 檔)、**3 個確認孤兒 + 2 個準孤兒**(全部 README 自己已記錄,非新發現) |

**方法論註**:唔係每個 `exp_*.py` 都一定有獨立同名 `results/*.md`——本 repo 兩個合法慣例都存在:
(a) 多個腳本共寫一個 result 檔(例:`exp_rsi2_filter/_exit/_alpha` 三個腳本 → 同一個
`2026-06-30_rsi2_200sma.md` 用 Addendum 段落累加);(b) 部分 result 係**質性 thesis 研究**(冇對應
python 腳本,例如全部 15 個 `redteam_*.md`、`china_dependency_audit.md`、`crypto_thesis_research.md`、
`dram_series_spotcheck.md`、`demand_side_scan.md`)——呢啲用 grep/filing 閱讀做,唔係回測,「冇腳本」係
正常,唔係孤兒。

**README 自身已過期**:`backtest/experiments/README.md` 開首寫「37 個一次性研究實驗(06-30~07-03)」,
但索引表實際延伸覆蓋到 07-13(bt_b_washout_expr);07-13 尾段到 07-16 新增嘅約 20 個腳本
(`exp_earnings_expectation_probe`/`exp_solvency_gate_probe`/`exp_trim_rule_backtest`/`exp_clist_v1`/
`exp_mp_capex_history` 等)完全冇入索引表,亦冇更新開首嘅腳本總數。**呢個係文件落後,唔係孤兒**——
逐一核實後全部都搵到對應 result(見附表),只係 README 冇跟到手。建議 gatekeeper 更新 README 索引表
延伸到 07-16。

---

## 2. 孤兒腳本清單(冇對應 result)

全部 3 個確認孤兒 + 2 個準孤兒都係 **README 第 118-124 行自己已經記錄**嘅舊清單,今次逐一重新核實
(`grep -rl` 搜全部 results/*.md 內容)**結果不變,冇新孤兒**:

| 腳本 | README 自述狀態 | 本次核實 |
|---|---|---|
| `exp_pmcc.py` | 孤兒(PMCC 已於 v3.1 移除,歷史) | 確認,results/ 全庫 zero mention |
| `exp_sector_timeframe.py` | 孤兒 | 確認,zero mention |
| `exp_rescue_forensics.py` | 孤兒 | 確認,zero mention |
| `exp_memory_cycle.py` | 準孤兒(結論在 KARS_MEMORY,餵 thesis) | 確認,只喺 `2026-07-08_altdata_census.md` 順帶提及,冇專屬 result |
| `exp_rsi2_capeff_detailed.py` | 準孤兒(餵 mean-rev 家族) | 確認,zero 專屬 result |

README 第 124 行已明文:「**不刪**(負面結果是證據、repo 哲學)。要引用其結論前,先重跑一次補 results
文件。」—— 本次審計同意呢個處置,冇新增建議。

**額外核實過、一開始睇似孤兒但其實有結果嘅個案**(避免 gatekeeper 誤刪):
- `exp_clist_v1.py` → 結果檔喺 `docs/2026-07-13_clist_v1.md`(唔喺 `backtest/results/`,係跨目錄慣例——
  腳本自己 docstring 第 2 行明寫)。已確認 `docs/2026-07-13_clist_v1.md` 存在。
- `exp_core_portfolio_loop2/3/4.py` → 同 `exp_core_portfolio_lab.py` 共用一個已歸檔結果檔
  `backtest/results/_archive/2026-07-06_core_portfolio_loops.md`(檔內第 5 行明寫 4 個腳本名)。
- `_extract_expectations_investing.py`(底線開頭)→ 一次性 PDF 文字擷取工具(硬編碼個人電腦路徑
  讀 ebook),符合 `.gitignore` 第 55 行 `backtest/experiments/_*.py` 慣例,本身唔算「實驗」,
  唔算孤兒。

---

## 3. 取代鏈表

| 主題 | 版本鏈 | 現行 | 舊版有冇標註取代 |
|---|---|---|---|
| LEAP delta 掃描 | `2026-07-06_leap_delta_sweep.md`(sandbox/RV-proxy)→ `2026-07-06_leap_real_sweep.md`(真數據) | leap_real_sweep | **有**——README 明文「superseded → leap_real_sweep」,舊檔**已移入** `results/_archive/`,檔內自帶「DRAFT — sandbox run」橫幅。處理乾淨,無需再動。 |
| Core Portfolio Loop 1-4 | `exp_core_portfolio_lab/_loop2/3/4.py`(sandbox,SPY-only RV-proxy)→ `exp_core_assembly_real.py` 系(真 VIX/QQQ 數據) | core_assembly_real → core_topup → topup_timing_ab → base_mix → bt2_aa_structure → bt7_ballast_def | **有**——loops 檔已移入 `_archive/`,檔內第 6-8 行自帶「數據限制...未 bankable,要本機真 VIX 重跑」警示 + 指向 `docs/2026-07-06_core_strategy.md`。處理乾淨。 |
| 估值(own-history PE) | `exp_valuation.py` → `exp_valuation_broad.py` | valuation_broad | 兩者結果**同寫一個檔**(`2026-07-01_valuation.md` 內用「Broad update」段落累加,非兩個獨立檔)—— README 話「superseded」但實際係 in-place addendum,唔係兩檔並存,**無風險**,只係 README 用詞誤導(叫法應該係「延伸」唔係「取代」)。 |
| Category-2 情緒反轉(sentiment reversal) | v1(07-11)→ v2(07-11,修窗口 bug)→ v3(07-11,改用 peak-vs-trough 法) | **v3 為終判** | **冇**——v1 檔本身完全冇任何指向 v2/v3 嘅標註,見 §4 詳述,**本審計最重要發現**。 |
| Expectations-Gap 估值(生產快照) | `2026-07-12_expectations_gap_v0.md`(一次性)→ `2026-07-13_expectations_gap_v1.md` → `2026-07-15_expectations_gap_v1.md`(同名,重跑刷新數) | 07-15 最新 | v0 檔自述「kept as historical record」(有標註,乾淨)。**但 07-13/07-15 兩個「v1」同名唔同日**——呢個唔係取代鏈,而係「生產腳本定期重跑、每次落一個新日期快照」嘅慣例(`.gitignore` 第 127 行有註明此慣例),**兩檔都保留係設計原意**,非重複。已 diff 確認內容非 byte-identical(數字小幅刷新 + 07-15 版多咗 Solvency 閘一節)。 |
| Constraint-language production scan | `2026-07-12_constraint_scan_production.md` → `2026-07-15_constraint_scan_production.md` | 07-15 最新 | 同上,**同一生產腳本嘅定期快照**,非取代鏈,兩檔都應該保留(季度時序趨勢要睇多點)。 |
| Confidence 公式遷移 diff | `2026-07-15_confidence_formula_diff.md`(P2 凍結公式 preview diff)→ `2026-07-16_final_confidence_diff.md`(P2 收尾+red-team+§4c) | 07-16 為終稿(仍係草稿待批,見 commit 7750691/0ac6f3f) | 07-16 檔自述「**唯一新增檔**」,冇宣告 07-15 檔作廢,兩者是流程階段記錄(preview→final),非重複,合理保留。 |
| MP Materials capex/D&A | `exp_capex_da_probe.py`(2026-07-12,cross-sectional 快照)→ `2026-07-13_mp_capex_da_review.md`(人手覆核)→ `exp_mp_capex_history.py`(補建 MP 自己時序) | 三檔遞進,非取代 | 每一步都明文 cross-reference 上一步(review 檔開首列出覆核材料;history 腳本 docstring 引用 review 檔「監察條件#5」),**證據鏈完整**,無風險。 |

---

## 4. 結論已被推翻但冇標註(最重要一節)

### `2026-07-11_category2_sentiment_reversal.md`(v1)—— 讀者單獨睇呢個檔會得出錯誤結論

**v1 檔本身內容**:對 XLF(GFC)/XLK(covid)/XLF(covid)三個案例都做「net(pos-neg)」時序表,結尾只有
一句程式化描述:「First-half avg neg_ratio: X% | Second-half avg neg_ratio: Y% | **WORSENING (neg ratio
rising into the episode start)**」。**呢句「WORSENING」讀落好似係一個有方向性嘅發現**(語氣轉差 →
危機開始),但 v1 完全冇檢查呢個轉差時點相對股價底部係「早」定「遲」——冇 lead/lag 分析。

**v2 檔(同日 07-11)引入 real lead-time check**,直接推翻咗呢個「訊號有用」嘅隱含印象:
> 「Real lead time: signal fully available (last transcript published) 2009-12-15 vs price trough
> 2009-03-06 = **-284 days** (signal LAGGED price -- not actionable, price already moved first)」
> (GFC-XLF 案例);covid-XLF 案例更差,-349 日。

**v3 檔(同日)做 6 案例總表 + 明文終判**:
> 「**結論:呢個 pattern 唔穩定,冇通用交易 edge。** 6 個案例入面淨係 2 個...有真.搶先...3 個落後
> ...多數情況下,語氣訊號比股價更遲轉向...」
> 「呢條研究線暫時擱置,唔再擴大案例數...類別2呢條研究線正式擱置,唔再投入。」
> v3 亦交代咗手足檔 `2026-07-11_category2_recovery_language.md`(復甦專屬詞彙變體)嘅初步「搶先」
> 讀數係假陽性(「trough」呢個詞絕大多數係業務週期慣用語,同危機復甦無關,**結果已撤回**)。

**問題**:v1 檔案名(`2026-07-11_category2_sentiment_reversal.md`,冇 `_v2`/`_v3` 後綴)喺目錄裡排喺
最前、睇落最「正規」,但**內容完全冇提及自己已被 v2/v3 取代同最終否決**。任何 agent 或人類單獨開
v1(例如 grep 命中呢個檔名、或者按日期排序睇 07-11 批次)都會停喺「WORSENING」呢句,誤以為搵到一個
有方向性嘅訊號,完全唔知道:(a) 呢個轉差冇 actionable timing(lag 唔係 lead)、(b) 6 案例擴大後
pattern 唔穩定、(c) 呢條研究線已經正式擱置。

**建議**(唯讀審計,交 gatekeeper 執行):喺 `2026-07-11_category2_sentiment_reversal.md` 同 `_v2.md`
開首各加一行指標,例如:「**→ 已被 `_v3.md` 取代,v3 終判:pattern 不穩定、研究線已擱置,勿單獨引用
本檔結論**」。呢個係加一行 pointer,唔係刪除或改動原有數據/結論本身,符合「決策記錄唔應刪」嘅鐵律。

### 其他曾懷疑、核實後排除嘅個案
- expectations_gap / constraint_scan_production 兩組「同名唔同日」檔——核實為生產快照定期重跑慣例
  (非取代鏈),v0→v1 的方法變更本身已在 v1 檔開首用「v1's ONLY change vs v0」講清楚。冇推翻風險。
- valuation.md 嘅「superseded」字眼——核實實際係同檔 Addendum,非兩檔並存,冇風險。

---

## 5. Gitignore 洩漏檢查

**結果:乾淨,冇洩漏。**
- `git ls-files backtest/experiments/` 入面 **冇**任何底線開頭檔案(`_*.py`/`_*.csv`/`_*.json`/`_*.txt`
  全部正確被 `.gitignore` 第 53-57 行擋住,包括睇落似正常 source code 嘅 `_extract_expectations_investing.py`
  ——核實內容後確認佢真係一次性 scratch 工具,唔係被誤傷嘅正式腳本)。
- `git ls-files backtest/results/` 入面 **冇**任何非 `.md` 檔案(`_*.csv` 同 `_scratch_*/` 全部正確被
  `.gitignore` 第 58-59 行擋住)。
- `backtest/results/2026-07-15_constraint_scan_production.md`(session 開始時 git status 顯示 `??`
  untracked)現時已經 committed、`git status --porcelain` 對呢個檔案乾淨——判斷係之前 nightshift commit
  (`3a09236`/`2833d3b`)已經收咗,唔算洩漏,亦唔算孤兒檔案。
- 冇發現任何應該被 ignore 但實際被 track 咗嘅檔案(反向洩漏)。

---

## 6. 歸檔建議

1. **`backtest/experiments/README.md` 索引表過期**——建議延伸索引到 07-16(新增約 20 個腳本行),
   同修正開首「37 個實驗」嘅過時總數。呢個係文件維護,唔係刪檔。
2. **`2026-07-11_category2_sentiment_reversal.md` + `_v2.md`**——加一行「已被 v3 取代」指標(見 §4),
   不刪除。
3. **`_archive/` 慣例值得延續但目前只用咗 2 次**(leap_delta_sweep、core_portfolio_loops)——
   兩者都係「整個檔案被另一個獨立檔案取代」嘅乾淨案例。目前**冇**其他 result 檔符合呢個「完全被
   另一獨立檔取代」嘅條件(valuation 係同檔 addendum、expectations_gap/constraint_scan 係快照序列、
   confidence_diff 係流程階段)——**暫時毋須再搬其他檔入 `_archive/`**。
4. **`.claude/worktrees/asml-crowding/`(獨立 git worktree,分支 `wt-asml-crowding`)**——
   內含自己嘅 `backtest/experiments/exp_category2_recovery_language.py`、
   `exp_category2_sentiment_reversal.py` 同對應 result 複本,`STATUS.md` 話「最後更新:2026-07-13」。
   呢個唔喺本次审计範圍(backtest/experiments 同 backtest/results)之內,但同用戶 memory 提到嘅
   「workspace 整理債務」有關——建議另外起一個 session 用 `git worktree list` 核實呢個 worktree
   仲用唔用緊,唔用就 `git worktree remove`(用戶 memory 有寫「雙重記憶系統邊界要寫明」,呢個
   worktree 副本可能加劇緊嗰個問題)。
5. **`backtest/results/_scratch_groupB/`、`_scratch_groupD/`**——兩個目錄入面總共 19 個 `.txt`
   (逐 ticker 檔),已經被 `.gitignore` 正確排除(untracked),留喺磁碟冇 git 負擔,毋須處理。

---

## 7. 未解/需人判

1. **`.claude/worktrees/asml-crowding` 是否仍在用**——本審計冇檢查佢嘅 commit 歷史/分支狀態,
   淨係發現佢存在同載有重複嘅 category2 實驗複本;是否刪除要 gatekeeper/用戶確認呢條分支嘅工作
   狀態。
2. **`2026-07-13_pernode_batch1/2/3_draft.md` + `2026-07-15_subscore_backfill_draft.md` +
   `2026-07-15_confidence_formula_diff.md`**——全部自稱「草稿,待用戶/gatekeeper 覆核」,但 git log
   顯示 `0ac6f3f thesis: apply approved 15/15 confidence migration (P2 complete)` 已經係之後嘅
   commit(遷移已批准並套用)。呢啲「草稿」標籤有機會已經 stale(應該話「已套用」)——但呢個屬於
   `thesis/` 層嘅狀態同步問題,超出 `backtest/experiments`/`backtest/results` 範圍,建議 gatekeeper
   另核 `thesis/DESIGN.md`/`themes.yaml` 對應段落嚟確認。
3. **README 索引表延伸(建議1)同 category2 取代標註(建議2)—— 呢兩項係本審計認為風險最高、
   值得優先處理嘅寫入動作,但兩者都需要 gatekeeper(或用戶)批准先落筆,本審計本身唔改任何檔案。**
