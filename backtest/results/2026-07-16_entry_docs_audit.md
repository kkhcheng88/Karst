# Agent 入口閱讀鏈一致性審計(2026-07-16)

> **性質**:唯讀審計,無修改任何被審檔案。產出僅本檔。
> **動機**:Codex 即將加入做 adversarial reviewer,會由 `AGENTS.md`(檔頭明文寫
> "for any coding agent (Claude Code / Roo Code / Codex)")入手,照其指示讀
> `STATUS.md` → `ARCHITECTURE.md` → `.agents/KARS_MEMORY.md`。本檔盤點呢條鏈
> 邊度過時/矛盾,令 Codex(或任何新 session)會被誤導成假 findings。
> **執行**:read-only 審計 agent(Opus),2026-07-16。

---

## 1. 方法 + 現行事實基準

### 1.1 方法

1. 先讀「現行事實源頭」建立基準(下 §1.2),唔靠記憶/對話。
2. 逐檔全文讀審計對象:`AGENTS.md`、`STATUS.md`、`ARCHITECTURE.md`、`README.md`、
   `HANDOFF.md`、`.agents/KARS_MEMORY.md`、`docs/INDEX.md`(`.agents/USER.md` **唔存在**,見 F-A2)。
3. 每個指針逐個 `ls` 驗證存唔存在;每個數字claim 對 code/YAML 實跑驗證。
4. 每條 CONTRADICTS 引原文(檔:行)+ 引現行事實出處。冇證據唔寫,唔肯定標「**需人判**」。

### 1.2 現行事實基準(全部經本次驗證)

| 事實 | 出處(已驗) |
|---|---|
| **凍結 confidence 公式**:`confidence_raw = (Σ 4-KPI subscores)/8 × penalty(crowding_band, cycle_stage)`;`confidence = min(raw, 0.30) if len(sources)==1` | `thesis/DESIGN.md:84-102`(§4a,2026-07-15 凍結) |
| **4-KPI rubric 0/1/2 錨點 + 0.5 步進**;penalty = 5×3 凍結查表 | `thesis/DESIGN.md:162-183` |
| **「獨立來源」= 數獨立證據鏈,唔係數訂閱源**;Tier-1 須擊中**承重 claim** 先脫 cap | `thesis/DESIGN.md:104-115` |
| **Red-team 協議**(§4b):FALSIFY 四動作;夜班 Level-1 **永遠唔准向上郁 confidence**;moat/growth 攞 2 分前提 = 經 Level-2 red-team 生還,齋引用最高 1.5 | `thesis/DESIGN.md:117-160` |
| **§4c 三通道分流**(2026-07-16):red-team 殺傷力唔准喺 confidence 數字酌情;通道 1 subscore / 通道 2 cap 資格 / 通道 3 magnitude 加成 | `thesis/DESIGN.md:194-243` |
| **sizing v2 已接線** honour `magnitude_unconfirmed`(`theme_magnitude_mid()` 用 `min(tier, 2.0)` damp) | `thesis/DESIGN.md:223-235`;commit `2833d3b` |
| **lint 機械把關**:P2 formula check(themes.yaml confidence ≠ wiki subscores 套公式輸出,誤差 >0.01 = **error**)+ §4c `magnitude_unconfirmed` 無對應 wiki `red_team` 段 = warning | `thesis/lint.py:24-33, 205-206, 282-328` |
| **新工具全部存在** | `thesis/confidence_formula.py`(5,139B)、`composite_score.py`(7,631B)、`kill_metrics.py`(8,304B)、`magnitude_features.py`(13,590B) |
| **15 個 active theme**,confidence 全部 = 公式輸出,範圍 **0.20–0.47** | `thesis/themes.yaml` 實跑:memory 0.30 / photonics 0.30 / **ai-power-grid 0.47** / adv-pkg 0.30 / space 0.30 / rare-earth 0.30 / tpu 0.30 / oil-gas 0.275 / semicap 0.20 / aero-alloys 0.24 / **euv-litho 0.47** / us-solar 0.30 / gas-compression 0.30 / siding 0.24 / glp1 0.30 |
| **P1-P5 提案全部已實作** | `docs/2026-07-15_quantification_review.md`;commits `3d0ab49`(P1)`285ccc8`+`6c051a2`(P2)`8715f37`(P3)`61fa4ed`(P4)`af77872`(P5) |
| **solvency 條件閘已接線**(weekly valuation + daily pick) | commit `3f1fb33`;`thesis/dashboard_render.py:64-67, 292-300, 744` |
| **校準迴路已閉**:`log_predictions.py` = the ONE writer;`backfill_outcomes.py` 回填 outcome | `thesis/daily_ic.cmd:4-5, 17-18`;`thesis/backfill_outcomes.py:1-20` |
| **IC≥0.05 已程式化** | `thesis/forward_ic.py:43-44`(`PRELIM_MATURED_MIN=60`、`PASS_MEAN_MIN=0.05`)+ `judge():177-182` 狀態機 |
| **insider `conf_eff` 仍未接分**(真.未修) | `backtest/spine/__init__.py:13` 明寫 "Known gap: insider conf_eff computed but NOT fed to score (P0-1)";`spine/expression.py:66` `score = 100.0 * mc.gate * (1 if above else 0) * warm * thesis.unit` — 用 `thesis.unit` 唔係 `conf_eff` |

### 1.3 過時量化(git 客觀證據)

| 檔 | 最後 commit | 距今 | 新框架命中數 |
|---|---|---|---|
| **`AGENTS.md`** | 2026-07-05 `cad034e` | **11 日** | **0** |
| **`README.md`** | 2026-07-05 `cad034e` | **11 日** | **0** |
| `HANDOFF.md` | 2026-07-06 `f1171a8` | 10 日 | 0 |
| `ARCHITECTURE.md` | 2026-07-09 `d617b26` | 7 日 | 0 |
| `docs/INDEX.md` | 2026-07-12 `a706a52` | 4 日 | 0 |
| `STATUS.md` | 2026-07-13 `4c3bb0a` | 3 日 | 0※ |
| `.agents/KARS_MEMORY.md` | 2026-07-13 `904ca62` | 3 日 | 0 |
| — 對照 — | | | |
| `thesis/DESIGN.md` | **2026-07-16** `2833d3b` | 0 日 | 全部 |
| `.claude/skills/thesis/SKILL.md` | 2026-07-15 `2308fcb` | 1 日 | **有**(§4a/§4b/red-team/kill_metrics/cap) |

※ grep `4a|4b|4c|red.?team|confidence_formula|magnitude_unconfirmed|composite_score|kill_metrics|solvency`
唯一 STATUS.md 命中係 `STATUS.md:228` 嘅 "**red**-team" 誤中(實際字串 = "port-back **已修**" 嗰行嘅無關字元),
**非真命中**。即整條入口鏈對新框架 = **零覆蓋**。

> **唯一亮點(重要緩解因素)**:`.claude/skills/thesis/SKILL.md:69-84` **有**覆蓋 §4a rubric、
> §4b red-team 四動作、夜班唔准向上郁、齋引用 cap 1.5、凍結公式 + single-source cap 0.30、
> `kill_metrics.py`。而 `AGENTS.md:28-30` 明確講「other agents: read that SKILL.md as the procedure」。
> **即 Codex 有機會由 SKILL.md 攞到新框架 —— 但前提係佢行到嗰一步而唔係喺 STATUS/ARCHITECTURE/
> DESIGN 檔頭已經被誤導。**

---

## 2. 逐檔審計

### 2.1 `AGENTS.md`(**最高風險 —— Codex 嘅入口**)

#### CONTRADICTS

**A1(最危險)| `AGENTS.md:15`:P0 清單標「未修」,實際 4 個入面 3 個已解決**

原文:
> `- docs/ROADMAP_AGENTIC.md` — 已核准的實施計畫(Phase A-D);`docs/2026-07-03_*` — 全系統審查
>   (P0 接線問題清單,**未修**,動 spine/thesis 前先看)。

逐條對現行事實:

| P0 | AGENTS.md 講 | 現行事實 | 判定 |
|---|---|---|---|
| ① insider `conf_eff` 算了但從未接回分數 | 未修 | `spine/__init__.py:13` + `expression.py:66` 確認仍未接 | **仍真.未修 ✅** |
| ② credit 軸/兩軸背離已驗證卻完全缺席 | 未修 | credit 2026-07-05 測完**判死剔除**、ROADMAP A2 **作廢**(`ARCHITECTURE.md:34`、`STATUS.md:199-202, 284`、`KARS_MEMORY.md:218`) | **已作廢,唔係 gap ❌** |
| ③ 校準迴路是斷的(outcome 回填程式不存在) | 未修 | `thesis/backfill_outcomes.py` **存在**;`daily_ic.cmd:17-18` 已排程;`daily_ic.cmd:4` 明寫 log_predictions = "the ONE writer"(雙 logger 問題亦已解) | **已修 ❌** |
| ④ IC≥0.05 只是文字非程式 | 未修 | `forward_ic.py:44` `PASS_MEAN_MIN = 0.05` + `judge():177` 狀態機 + PRELIMINARY 判定 | **已修 ❌** |

→ **AGENTS.md:15 準確度 = 1/4。** Codex 會攞住呢句去審 ②③④ = 3 個假 finding。

**A2 | `AGENTS.md:18` 指向唔存在嘅檔(失效指針)**

原文:
> `- .agents/USER.md` — who the user is + work preferences (adversarial thinking, evidence-first, NHITL).

驗證:`ls .agents/USER.md` → **No such file or directory**。
現行事實:`.agents/KARS_MEMORY.md:183` 自己記低咗刪除:
> 舊 `.agents/USER.md`(個人被動收入目標)**已刪**——與專案目的無關、會誤導。

→ 2026-07-04 刪咗,`AGENTS.md` 12 日冇跟。Codex 第一步讀 Read-first 清單就撞牆。

#### 缺失關鍵新規則(Codex 唔知就會審錯)

`AGENTS.md` 對以下**全部零提及**:

| 缺失 | 應該喺邊講 | 後果 |
|---|---|---|
| **§4a 凍結 confidence 公式 + rubric + penalty 表 + single-source cap 0.30** | "Core discipline" 節 | Codex 會以為 confidence 仍係自由推導 |
| **`thesis/lint.py` 機械把關**(formula check = error) | "Core discipline" / Phase 3 節 | Codex 會建議「加個 lint check」——已有 |
| **§4b red-team 協議**(INGEST = 審判;夜班唔准向上郁 confidence) | "Core discipline" 節 —— 現行 `AGENTS.md:38-39` 只講「falsifiable kill_condition」,停留喺舊 FALSIFY | Codex 唔知有 Level-1/Level-2 分層 |
| **§4c 三通道 + `magnitude_unconfirmed`** | Phase 3 節 | Codex 會覺得 red-team 判決冇落地 |
| **composite 分(P1)/ solvency 閘 / kill_metrics** | Daily engine / Phase 3 節 | 同上 |
| **`docs/INDEX.md`** | Read-first 節 | `STATUS.md:6` 標佢做「★ 全 workspace 導航地圖」,但 `AGENTS.md` 由頭到尾**冇提過**(已 grep 驗證) |

#### 其他

- `AGENTS.md:31` 指 `thesis/README.md` 做 "Structure" —— 但該檔嘅 confidence 流程已過時(見 §2.8 X2)。
- `AGENTS.md:24` 指 `backtest/results/2026-07-01_*.md` —— ✅ 存在(10 個檔)。
- `AGENTS.md:28` 指 `.claude/skills/thesis/SKILL.md` —— ✅ 存在且**內容最新**。

---

### 2.2 `STATUS.md`(標明 "START HERE")

#### CONTRADICTS

**S1 | `STATUS.md:4`:「最後更新:2026-07-13」—— 缺 07-14~07-16 三日全部新框架**

呢三日 commit 包括(`git log --since=2026-07-14`):P1 composite 分、P2 公式凍結 + rubric + lint、
P3 magnitude features、P4 kill metrics、P5 entry/exit 卡、single-source cap、獨立來源定義、
FALSIFY→red-team 升級、§4c 三通道、red-team wave 1-4(**15 個 active theme 全部已 red-team**)、
15/15 confidence 遷移(`0ac6f3f`)、sizing v2 接線(`2833d3b`)、solvency 閘接線(`3f1fb33`)。
→ **一個「START HERE」檔缺咗系統最近三日嘅全部方法論骨幹。**

**S2(需人判 —— 最尖銳)| `STATUS.md:256`:「confidence 上限 ≤0.40」vs 現行兩個 theme = 0.47**

原文:
> 5. 衛星紀律:校準迴路未通之前,Phase-3 注碼 ≤20%、confidence 上限 ≤0.40。

現行事實:`thesis/themes.yaml` 實跑 → `ai-power-grid 0.47`、`euv-lithography-monopoly 0.47`
(兩者 note 均寫「2026-07-16 P2 遷移(用戶批准)+ red-team 判決:脫 single-source cap」)。
`thesis/DESIGN.md` §4a 凍結公式**只有 single-source cap 0.30,冇 0.40 全域上限**。

**兩種讀法,我唔夠證據判:**
- (a) 呢條 2026-07-06 訂嘅衛星紀律**已被 §4a 公式體制取代**(而且前提「校準迴路未通」本身已唔成立
  —— 見 §1.2 校準迴路已閉)→ STATUS.md 過時,應刪/改寫。
- (b) 呢條 cap **仍然生效**,而 15/15 遷移不慎令兩個 theme 越界 → 係真.違規,要處理。

→ **標「需人判」。呢個係 Codex 最有可能提出、而我哋唔可以一句「假 finding」打發嘅一條。**
   無論邊種讀法,doc 同 impl 唔一致係事實,必須裁決。

**S3 | `STATUS.md:107`:「估值/expectations-gap 全系統缺席(thesis_valuation.py 未起)」—— 內部矛盾 + 過時**

原文(2026-07-12 節):
> ③估值/expectations-gap 全系統缺席(thesis_valuation.py 未起);

現行事實:
- `ls thesis/thesis_valuation.py` → **MISS**(檔名確實唔存在)
- **但** `thesis/valuation.py` **存在**(52,623B),且 `STATUS.md:91` **自己**講:
  > **valuation.py v1 生產化**(週期頂 bias 修正,SUN 09:15 週更已註冊)+ **BT-5 判別力 6/6 全中
  > (判官預先寫死)→ 過閘**
- 再加 solvency 閘已接(commit `3f1fb33`)、P1 composite 分嘅 `dim_expect` 直接食 `P_base@14x`
  (`docs/2026-07-15_quantification_review.md:71`)。

→ **`STATUS.md:107` 同 `STATUS.md:91` 喺同一檔內互相矛盾。** 功能已建,只係唔叫嗰個檔名。

**S4 | `STATUS.md:219`:P0 ③④ 標「未修」,同 `STATUS.md:229-231` 自我矛盾**

原文(2026-07-03 節):
> 抓到 **P0 級接線問題,未修**:① insider `conf_eff` 算了但從未接回分數;② credit 軸/兩軸背離已驗證卻
> 完全缺席;③ 校準迴路是斷的(outcome 回填程式不存在);④ IC≥0.05 只是文字非程式。

但同檔 `STATUS.md:229-231`(2026-07-12 節)已更正:
> **Batch 1(WS1 裁判狀態機 + WS3 生命週期)實測已全套跑緊 live**(`forward_ic.py` judge() 出
> PRELIMINARY、`lint.py` admission gate 0 error、`thesis/migrate_track_record.py` 已 run 過)——
> 07-06 嗰個「未驗證」擔心係多慮,程式碼早已到位,唔止係 design doc。

→ 舊節冇加 strikethrough / 更正註,而 `AGENTS.md:15` 正正叫人去讀嗰個「未修」清單。

**S5 | `STATUS.md:251`:「未修 #1/#2 前,錶行極都冇數」—— 過時**
`#1 統一雙 logger + outcome 回填` 已修(`daily_ic.cmd:4` "the ONE writer" + `backfill_outcomes.py`);
`#2 PASS/FAIL 程式化` 已修(`forward_ic.py:44`)。

**S6 | `STATUS.md:300`:「37 實驗索引」—— 實際 129**
`ls backtest/experiments/exp_*.py | wc -l` → **129**(`backtest/results/*.md` → 122)。
`backtest/experiments/README.md:3` 自己都仲寫「37 個一次性研究實驗(2026-06-30 ~ 07-03)」。

**S7(需人判)| `STATUS.md:91`:「接 sizing 閘嘅執行語意待用戶揀(task #30)」**
commit `3f1fb33` = "solvency conditional gate wired into weekly valuation + daily pick (per probe verdict)"。
→ 唔肯定 task #30(valuation 閘語意)同 solvency 閘係咪同一件事已解。**需人判**。

#### 失效指針

| 行 | 指向 | 狀態 |
|---|---|---|
| `STATUS.md:250` | `docs/2026-07-06_phase3_methodology_review.md` | **MISS** → 實際喺 `docs/_archive/` |
| `STATUS.md:253` | `docs/2026-07-06_dashboard_design.md` | **MISS** → 實際喺 `docs/_archive/` |
| `STATUS.md:254` | `docs/2026-07-06_bottleneck_candidates.md` | **MISS** → 實際喺 `docs/_archive/` |

**部分緩解**:`STATUS.md:7-9` 有預警:
> 本檔下方「下一步」部分段落係 2026-07-06 sandbox 時代殘留(引用已 SUPERSEDED 檔如
> phase3_methodology_review/dashboard_design/bottleneck_candidates)——**以 INDEX.md §3 Phase-3 +
> `docs/2026-07-08_phase3_architecture.md` 為準**。

→ 呢個預警寫得好,但唔改路徑本身,Codex 照樣會報「3 個 broken link」。

#### 缺失
整節「現在在哪」停喺 2026-07-13;冇 07-14~16 節;冇提 §4a/§4b/§4c/lint formula check/
composite 分/kill_metrics/solvency 閘/15 theme 全 red-team 完成。

---

### 2.3 `ARCHITECTURE.md`(自稱 "single source of truth")

#### CONTRADICTS

**R1 | `ARCHITECTURE.md:37, 104`:「Phase 3 ✅ live(9 個 Type-B)」—— 實際 15 個 active**

原文 `:37`:
> | **3 質性 thesis** | 價值鏈→ticker→一手驗證→crowding→confidence(0..1 sizing 乘數)| ✅ live(9 個 Type-B)| `thesis/`, `spine/providers.py` |

原文 `:104`:
> **✅ 已建:** Phase 0/1/4 spine · Phase 3(9 Type-B thesis **+ Insider 家族**)· ...

現行事實:`thesis/themes.yaml` 實跑 = **15 個 active**(2026-07-11 discovery radar 新增 6 個,
見 `STATUS.md:122`)。→ 一份自稱 single-source-of-truth 嘅檔,主要資產數目錯 40%。

**R2(最陰險)| `ARCHITECTURE.md:59, 114`:insider `conf_eff` 講到似已接分 —— code 明寫未接**

原文 `:59`:
> | **Flow: Insider** | **Phase 3**(非價格、知情人行為)| ✅ **已建** — v2 **SEC EDGAR Form 4** ... **bounded ±30% conf 修正** |

原文 `:114`:
> 63d 歸零/126d 轉負(⚠️ 與**現在的長期 ±30% overlay 接線** horizon 不符 → 修法 = 改接細價 12月 portfolio tilt...)

現行事實(直接讀 code):
- `backtest/spine/__init__.py:13` — `Known gap: insider conf_eff computed but NOT fed to score (P0-1).`
- `backtest/spine/expression.py:66` — `score = 100.0 * mc.gate * (1 if above else 0) * warm * thesis.unit`
  (用 `thesis.unit`,**唔係** `conf_eff`)
- `orchestrator.py:48` 計 `conf_eff`,`card.py:22` 只係擺入 card dict = **display-only**
- `KARS_MEMORY.md:223` 亦確認:「conf_eff 仍 display-only」

→ **`ARCHITECTURE.md` 錯,`STATUS.md`/`KARS_MEMORY.md`/code 啱。** 呢個係「doc 講某嘢已接但其實未接」
   —— 同其他 finding 方向**相反**(其餘多數係「講未建但已建」)。Codex 若信 ARCHITECTURE,會**漏報**
   一個真.P0;若信 STATUS,會啱。**呢條係入口鏈入面唯一一個「doc 過度樂觀」嘅方向。**

**R3 | `ARCHITECTURE.md:21`:tier-1 工具箱仍列 PMCC —— 已於 scorecard v3.1 移除**

原文:
> │   LEAP / SHORT_CALL→PMCC / CSP  │   結構資格分 × RSI-2 擇時                   │

現行事實(三處交叉確認佢已移除):
- `README.md:58` — 「`params/` ← 期權/timing 參數(帶 tag;**PMCC 已於 v3.1 移除**)」
- `params/layer1_options.md:8` — 「⚠️ **架構更新(2026-06-30 scorecard v3.1,本檔未全面改寫)**:**PMCC 已從 tier-1 ...**」
- `KARS_MEMORY.md:87` — 「**v3.1:PMCC 拿掉(長腿≡LEAP);改成 `SHORT_CALL = >200SMA × RSI-2 超買`**」
- `STATUS.md:14` — 「SPY/QQQ/SPMO 用期權工具(**LEAP/SHORT_CALL/CSP**)」← 冇 PMCC

→ 內部矛盾:ARCHITECTURE 嘅漏斗圖同 STATUS 嘅 30 秒版**唔一致**。

**R4 | `ARCHITECTURE.md:41`:「102 篇 FTS 語料 + 88 源節點」—— 規模已完全唔同**

原文:
> | **知識層** | 102 篇 FTS 語料(①)+ 88 源節點(②)+ wiki(③)| ✅ live | `thesis/corpus.py`, `build_source_nodes.py` |

現行事實:`thesis/corpus.db` = **11,558,502,400 bytes(~11.5 GB)**;`STATUS.md:41` 講
`Karst-corpus-weekly`「全 universe(~9.9k ticker)transcript 增量抓取 + `corpus.db` incremental build;
~1-2h 跑完」。→ 「102 篇」係 2026-07-01 嘅數,差咗幾個數量級。

**R5 | `ARCHITECTURE.md:142`:排程表只有 2 個任務、時間全錯**

原文:
> | Windows 排程任務 | `Karst-forward-IC-daily`(平日 09:00)· `Karst-insider-weekly`(週日 08:00)—— `schtasks /Query` 查 |

現行事實:`STATUS.md:20-21`:
> 2026-07-08 起全批搬到 **05:30 HKT 檔**(美股收市後、用戶瞓緊、rate limit 閒置...)。週任務用 TUE-SAT

實際 = **~12 個排程**(6 日更 + 6 週更,`STATUS.md:23-51`),forward-IC 係 **05:30 二至六**唔係平日 09:00。

#### 失效指針

**R6 | `ARCHITECTURE.md:138`:`universe.yaml` 唔存在**
> | thesis 登記(機器可讀)| `thesis/themes.yaml` ← **ticker 的單一真相**;`universe.yaml` 用 `thesis:` 自動拉,不重抄 |

驗證:`ls thesis/universe.yaml` → **MISS**(全 repo 冇呢個檔)。

#### 其他

- `ARCHITECTURE.md:5`「最後收斂:2026-07-01」—— 15 日前(雖然檔本身 07-09 有 commit,檔頭冇更新)。
- `ARCHITECTURE.md:38`「3e A 型危機 tail | 🔴 未建」—— 未驗證(超出本次範圍,但 `STATUS.md:31` 提過
  「危機 sleeve 狀態」喺 playbook_readout.py 度)。**需人判**。
- 零 §4a/§4b/§4c/red-team/composite/solvency/lint 覆蓋。

---

### 2.4 `README.md`

#### CONTRADICTS

**M1 | `README.md:56`:「thesis/ ← Phase 3 質性層(9 主題 + forward-IC)」—— 實際 15**
**M2 | `README.md:54`:「experiments/ ← 37 個回測實驗(見其 README.md 索引)」—— 實際 129**

#### 其他

- `README.md:42`「結構(2026-07-03 更新;**新 session 從 `STATUS.md` 開始**)」—— 13 日前;
  指向 STATUS.md 呢點**正確**。
- `README.md:48`「`AGENTS.md / HANDOFF.md` ← agent 入口 / **最近 session 詳細交接**」——
  HANDOFF.md 係 2026-07-03 嘅嘢,叫「最近」誤導(見 §2.5)。
- `README.md:58` PMCC 註記**正確**(反證 `ARCHITECTURE.md:21` 錯)。
- 零新框架覆蓋。**唯一好消息**:README 係定位檔,唔講方法論細節,所以缺失傷害細。

---

### 2.5 `HANDOFF.md`

#### 自標已冗餘

`HANDOFF.md:3`:
> ⚠️ **已被 `STATUS.md` 取代為入口(2026-07-06)。** 本檔僅保留為 2026-07-03 當日詳細記錄。

`STATUS.md:314` 亦講:
> - 2026-07-03 當日研究細節:`HANDOFF.md`(該 session 的詳細交接,已被本檔取代為入口)

#### CONTRADICTS

**H1(高危)| `HANDOFF.md:37-38` body 仍然主張「Credit > VIX」—— 已被判死**

原文 `:37-38`:
> 2. **Credit (HYG/LQD) > VIX** for risk regime (matches KC Fed RORO research). Credit was
>    the only risk gauge with a positive reversion edge.

原文 `:148`(**Open decisions,仲叫人去砌**):
> - [ ] (design) If wanted: rebuild the 大盤 panel as TWO axes (趨勢 gate / 風險情緒) + a
>       divergence read (finding #1). **Risk axis = credit + VIX** + safe-haven + true-breadth...

現行事實:credit 2026-07-05 測完**判死**:
- `ARCHITECTURE.md:34` — 「**credit 測完剔除**(`results/2026-07-05_market_regime_2d.md`)」
- `STATUS.md:199-201` — 「**credit(HYG/LQD)做風險軸 = 失敗**(regime 反覆、對 VIX 無增量)」
- `STATUS.md:284` — 「~~A2 credit 軸+兩軸背離~~(**已作廢** 2026-07-06)」
- `KARS_MEMORY.md:218` — 「①「credit>VIX」(§10)已被 07-05 `market_regime_2d` 推翻——credit 剔除,ROADMAP A2 作廢」

**部分緩解**:`HANDOFF.md:4-5` 檔頭有 retract 標示。**但 body 原文(:37-38)同 open decision(:148)
完全冇改**。一個 skim body 嘅 reviewer(Codex 典型行為:grep "credit" 攞 context)會攞到已判死嘅結論
**加埋一條叫佢去建嘅 open TODO**。

#### 失效指針

**H2 | `HANDOFF.md:6`:`docs/2026-07-06_fable_brief.md` —— MISS**
> 現行入口 = `STATUS.md`;交棒 = `docs/2026-07-06_fable_brief.md`。

驗證:`ls docs/2026-07-06_fable_brief.md` → **MISS**;實際喺 `docs/_archive/2026-07-06_fable_brief.md`
(`INDEX.md:71` 確認 2026-07-12 移入 `_archive/`;`STATUS.md:293` 亦已用新路徑)。

#### 冗餘判斷 → 見 §5

---

### 2.6 `.agents/KARS_MEMORY.md`

#### CONTRADICTS

**K1(最尷尬)| `KARS_MEMORY.md:3` 叫人讀 `USER.md` —— 而同一檔 `:183` 記低咗佢已刪**

原文 `:3`:
> 本檔是 Karst 的長期記憶。每次啟動先讀此檔 + **`USER.md`** + 最新 session,不要再從 conversation summary 重建。

原文 `:183`:
> 舊 `.agents/USER.md`(個人被動收入目標)**已刪**——與專案目的無關、會誤導。

→ **同一個檔自我矛盾**,而且 `AGENTS.md:18` 亦係指住呢個唔存在嘅檔(A2)。
   **兩個入口檔一齊指住同一個 12 日前已刪嘅檔。**

**K2 | `KARS_MEMORY.md:6`:「最後更新:2026-07-06(§12)」—— 實際有 §13/§14/§15 到 2026-07-13**

**K3 | `KARS_MEMORY.md:40-41`(§3 Core Strategy)仍列 PMCC —— 同 `:87`(§7)自我矛盾**

原文 `:40-41`:
> - **Layer 1 — Options Core(只 SPY/QQQ/SPMO)**:CSP(QQQ 20Δ/30DTE/50%PT,98.6% WR)
>   + **PMCC(SPY only,long leg deep ITM 0.70)** + 方向性 deep ITM LEAP。可選 IC(SPY 10Δ)。

原文 `:87`:
> **v3.1:PMCC 拿掉(長腿≡LEAP);改成 `SHORT_CALL = >200SMA × RSI-2 超買`**

→ §3(標題寫「**已確認**」)同 §7 打架。同 `ARCHITECTURE.md:21` 一齊構成 **PMCC 三方混亂**。

**K4 | `KARS_MEMORY.md:166`:「thesis 擴到 9 個 Type-B 主題」+「forward-IC 每日排程(平日 09:00)」**
→ 實際 15 個 / 05:30 二至六。

**K5 | `KARS_MEMORY.md:244, 248, 251`:排程時間全錯 + 數目錯**
- `:244` 「`Karst-gooptions-daily`(schtasks,**每日 09:10**)」→ STATUS:26 = **05:35**
- `:248` 「`Karst-playbook-daily`(平日 **09:15**)」→ STATUS:28 = **05:40**;
        「`Karst-transcripts-daily`(每日 **09:20**)」→ STATUS:29 = **05:45**
- `:251` 「**四個排程**總表喺 STATUS.md」→ 實際 ~12 個

**K6 | `KARS_MEMORY.md:155`:memory-supercycle 「confidence 0.35」—— 現行 0.30**
(`themes.yaml:74` note:「2026-07-15 red-team 修正(0.38→0.30)」;中間仲經歷過 0.38)

#### 缺失

零 §4a/§4b/§4c 覆蓋。§9(Phase 3 設計定稿)`:139` 仍寫舊式 confidence 描述:
> **confidence(不是「信念」!)= f(4-KPI, 佐證數, 距kill, payoff, regime契合)→ 對戰績校準成真機率 → sizing**

→ 呢個係 §1 嘅**概念**描述,而家已有凍結**公式**取代。冇標「已被 §4a 凍結公式取代」。

#### 雙重記憶邊界(用戶 memory 專門記低嘅債務)

**現況:完全冇寫。** 逐項驗證:

| 問題 | 現況 |
|---|---|
| `.agents/KARS_MEMORY.md`(repo 內)vs 用戶 project memory(`~/.claude/projects/<slug>/memory/`)點分工? | **兩邊都冇寫**。KARS_MEMORY.md 檔頭(`:1-6`)只講「本檔是 Karst 的長期記憶」,冇提另一套記憶存在 |
| 有冇矛盾? | **有 overlap 冇明確矛盾**。例:用戶 memory `karst-system-review-2026-07` 記「P0:insider 未接線/credit 軸缺席/校準迴路斷/IC 無程式判定」← 同 `KARS_MEMORY.md:174` 同一份 P0 清單,**兩邊都已過時(3/4 已解)**。即**同一個過時事實喺兩套記憶度各存一份**,更新要兩邊做,而兩邊都冇寫「要兩邊做」 |
| 寫記憶前查重規則 | 用戶全域 CLAUDE.md 有寫(「**寫記憶前兩邊查重**」),但 **repo 內冇任何檔提過呢件事** —— Codex 讀唔到用戶全域 CLAUDE.md,所以對 Codex 嚟講呢條規則**唔存在** |

→ **對 Codex 嘅具體風險**:佢只見到 `.agents/KARS_MEMORY.md`,會當佢係唯一記憶,
   可能建議「將 X 寫入 KARS_MEMORY」而唔知另一套已有/會撞。**建議喺 KARS_MEMORY 檔頭加一段邊界說明。**

---

### 2.7 `docs/INDEX.md`

#### CONTRADICTS

**I1 | `INDEX.md:55`:`weekly_corpus.cmd`「待用戶授權排程」—— 已註冊**
原文:
> | `thesis/weekly_corpus.cmd` | 🟢 週度 prefetch→build(全市場;**待用戶授權排程**)|

現行事實 `STATUS.md:41`:
> | SUN 08:30 | Karst-corpus-weekly(**已註冊 2026-07-12**)| 全 universe(~9.9k ticker)transcript 增量抓取 + `corpus.db` incremental build |

**I2 | `INDEX.md:57`:`thesis/DESIGN.md` 標 📘 DESIGN(規格,待/正實作)—— 應係 🟢 LIVE**
`INDEX.md:5` 定義:「📘DESIGN(規格,待/正實作)」。但 §4a/§4b/§4c 全部**已實作已接線**
(lint.py / confidence_formula.py / sizing.py,commit `2833d3b` 明寫「4c channel 3 wired -- standard complete」)。

**I3 | `INDEX.md:16`:「`.agents/KARS_MEMORY.md` | 🟢 歷史決策/坑(§1-14)」—— 實際到 §15**
(`KARS_MEMORY.md:255` = 「§15 2026-07-13 ——「Karst should be user agnostic」原則確立」)
※ 註:`STATUS.md:303` 另寫「§1-10」→ **三個數:INDEX 講 §1-14、STATUS 講 §1-10、實際 §1-15**。

**I4 | `INDEX.md:45`:LIVE 部件清單缺新工具**
原文:
> | 已 LIVE 部件 | `thesis/{forward_ic,log_predictions,backfill_outcomes,migrate_track_record}.py`(裁判)、`{sizing,concentration,beta_check,lint}.py`(生命週期/注碼)、`themes.yaml`(registry)|

缺:`confidence_formula.py`、`composite_score.py`、`kill_metrics.py`、`magnitude_features.py`、
`valuation.py`、`crowding_composite.py`、`dashboard_render.py`、`paper_ledger.py`、`brier.py`。

#### 其他
- `INDEX.md:6`「更新:2026-07-09」—— 7 日前。
- `INDEX.md:35`「Phase-3 衛星(30%)—— 📘 DESIGN + 部分 🟢 LIVE」—— 而家絕大部分 LIVE。
- `INDEX.md:77-80` 導航規則寫得好(「引數字/結論 → 去 `backtest/results/*.md`(落檔嘅先係真相)」)
  —— 呢條規則本身**係緩解 Codex 誤判嘅最佳單條規則**,但 `AGENTS.md` 冇 mirror 佢。

---

### 2.8 附帶發現(唔喺指定清單,但喺 Codex 必經路徑上)

**X1(最危險嘅單行)| `thesis/DESIGN.md:4`:「Phase 3 尚未實作」**

原文:
> 本檔是 2026-07-01 一整晚設計 session 的收斂記錄(...)。**Phase 3 尚未實作;這是定案的設計藍圖。**

現行事實:Phase 3 = 全 repo 最活躍嘅層。15 theme live、sizing v2 接線、lint 機械把關、
15/15 confidence 遷移完成、全部 theme red-team 完。**呢個檔 2026-07-16 啱啱 commit 過**(`2833d3b`),
即有人改緊 §4c 但冇碰檔頭第 4 行。

**點解最危險**:`AGENTS.md:27` 明寫「**Design:** `thesis/DESIGN.md`(**read before touching the thesis layer**)」。
Codex 一打開就見到第 4 行話「尚未實作」,然後下面 §4a/§4b/§4c 寫到「凍結」「已接線」。
→ Codex 會合理地報:「DESIGN.md 內部矛盾 / 設計文件聲稱未實作但 code 已存在,doc-code drift」。
**呢個係一行字造成嘅最高 ROI 修正。**

**X2 | `thesis/README.md`(`AGENTS.md:31` 指向):confidence 流程仍係手工推導**

原文(「加一個主題(pilot 流程)」步驟 1):
> 算 **cycle_stage**(早/中/晚)+ **confidence**(從 4-KPI + 佐證數 + 距 kill + payoff + regime 契合;
> 標「INITIAL, uncalibrated」直到有 track record)。

同 `DESIGN.md:92-96` 凍結公式直接衝突:
```
confidence_raw = (Σ 4-KPI subscores) / 8 × penalty(crowding_band, cycle_stage)
confidence     = min(confidence_raw, 0.30)   if len(sources) == 1
```
→ README 講「五個輸入自由推導 + 標 INITIAL」;DESIGN 講「兩個輸入套凍結公式 + cap + lint 機械驗證」。
**Codex 讀 thesis/README.md 會以為 confidence 冇公式。**

**X3(需人判)| `.agents/skills/` 未追蹤副本,proper noun 被 sed 污染**

- `git ls-files .agents/skills/` → **空**(untracked;`git status` 亦顯示 `?? .agents/skills/`)
- `diff .agents/skills/thesis/SKILL.md .claude/skills/thesis/SKILL.md` → **DIFFERENT**,差異全部係
  `claude-obsidian` → **`Codex-obsidian`**、`Claude-Code-bound` → `Codex-bound`:
  ```
  61c61
  < ## The thesis thinking loop (NHITL — adapted from Codex-obsidian /think, with FEEL removed)
  ---
  > ## The thesis thinking loop (NHITL — adapted from claude-obsidian /think, with FEEL removed)
  135c135
  < - Do NOT install Codex-obsidian (Codex-bound + external dep); ...
  ---
  > - Do NOT install claude-obsidian (Claude-Code-bound + external dep); ...
  ```
- **問題**:`claude-obsidian` 係**專有名詞**(一個實際存在嘅 repo);`Codex-obsidian` **唔存在**。
  睇落似係為 Codex 做嘅 find/replace 出咗界,把專有名詞一齊換咗。
- **後果**:若 Codex 讀 `.agents/skills/thesis/SKILL.md`,會見到「Do NOT install Codex-obsidian」
  —— 一個唔存在嘅嘢。而 `AGENTS.md:28` 指嘅係 `.claude/skills/thesis/SKILL.md`(正確版本)。
- **需人判**:呢個係 gatekeeper 進行中嘅 staging 定係意外?兩份 SKILL.md 邊份 authoritative?
  **我唔修,只報。**

---

## 3. 「Codex 會審錯乜」—— 假 finding 預測(本節係更新必要性嘅直接證明)

情境:Codex 照 `AGENTS.md` → `STATUS.md` → `ARCHITECTURE.md` → `KARS_MEMORY.md` 做對抗審查。
以下係佢**最可能提出、而且會「正確地」按舊規則論證、但其實已經解決**嘅 findings,按可能性排序:

### 假 finding #1 ★最可能|「校準迴路是斷的 —— outcome 回填程式不存在」

- **Codex 會引**:`AGENTS.md:15`(「P0 接線問題清單,**未修**,動 spine/thesis 前先看」)
  → `STATUS.md:219`(「③ 校準迴路是斷的(outcome 回填程式不存在)」)
  → `HANDOFF.md:135-136`(「**校準迴路是斷的**(log_predictions 從未寫入、outcome 回填程式碼不存在)」)
  → `KARS_MEMORY.md:174`(同一句)
  **四個檔互相印證** —— Codex 會覺得證據極強,信心極高。
- **現行事實**:`thesis/backfill_outcomes.py` **存在**(5,284B,2026-07-08);
  `thesis/daily_ic.cmd:17-18` 每日跑 `log_predictions.py` + `backfill_outcomes.py`;
  `daily_ic.cmd:4` 明寫 log_predictions = "**the ONE writer**"(連帶解咗「兩個唔一致 logger」問題)。
- **浪費**:Codex 會開一個 P0 ticket 叫人寫一個已經寫咗、已經每日跑緊 8 日嘅 script。

### 假 finding #2 ★最可能|「IC≥0.05 只是文字,冇程式判定」

- **Codex 會引**:同上四個檔(`STATUS.md:219` ④、`HANDOFF.md:136`、`KARS_MEMORY.md:174`),
  再加 `AGENTS.md:15` 嘅「未修」authority。
  **用戶 project memory `karst-system-review-2026-07` 都仲係咁寫**(「IC 無程式判定」)。
- **現行事實**:`thesis/forward_ic.py:43-44`:
  ```python
  PRELIM_MATURED_MIN = 60         # below this many matured JUDGE_HORIZON rows -> PRELIMINARY, no verdict
  PASS_MEAN_MIN = 0.05
  ```
  `judge():177-182` 完整狀態機,出 PRELIMINARY / PASS / FAIL。`STATUS.md:229-231` **自己都已經更正咗**
  (「`forward_ic.py` judge() 出 PRELIMINARY ... 07-06 嗰個「未驗證」擔心係多慮,程式碼早已到位」)
  —— 但 Codex 讀嘅係 `:219` 嗰個舊節,`AGENTS.md` 亦係指佢去舊節。

### 假 finding #3 ★最陰險(唔止浪費,仲會推 repo 走回頭路)|「credit 風險軸已驗證卻缺席,應該補返」

- **Codex 會引**:`AGENTS.md:15`(「未修」)→ `STATUS.md:219` ②(「credit 軸/兩軸背離已驗證卻完全缺席」)
  → `HANDOFF.md:37-38`(「**Credit (HYG/LQD) > VIX** for risk regime (matches KC Fed RORO research).
  Credit was the **only** risk gauge with a positive reversion edge.」)
  → `HANDOFF.md:148`(open decision:「Risk axis = **credit** + VIX + safe-haven + true-breadth」)
  **仲有一條未剔嘅 `[ ]` TODO 叫佢去做。**
- **現行事實**:credit 2026-07-05 backtest **判死並剔除**:
  `ARCHITECTURE.md:34`(「credit 測完剔除」)、`STATUS.md:199-201`(「**credit(HYG/LQD)做風險軸 = 失敗**
  ——regime 反覆、對 VIX 無增量」)、`STATUS.md:284`(「~~A2 credit 軸~~ **已作廢**」)、
  `KARS_MEMORY.md:218`。用戶 memory `regime-and-fear-greed-findings` 亦記「credit 軸 07-05 已剔除」。
- **點解最陰險**:呢個唔止係浪費時間 —— 係一個 adversarial reviewer **攞住已被實證推翻嘅結論
  + 一條未剔嘅 TODO,去要求重建一條已判死嘅軸**。而佢會引 KC Fed 論文做外部 authority,睇落好有力。
  否證佢要重跑成個 `results/2026-07-05_market_regime_2d.md`。

### 假 finding #4|「confidence 係手工推導,冇機械驗證 —— 建議加 lint check 確保數字跟到推導」

- **Codex 會引**:`thesis/README.md`(confidence「從 4-KPI + 佐證數 + 距 kill + payoff + regime 契合」
  自由推導、標「INITIAL, uncalibrated」)+ `KARS_MEMORY.md:139`(同款舊描述)
  + `INDEX.md:57`(`thesis/DESIGN.md` 標 📘 **DESIGN**,即「待/正實作」)
  + `thesis/DESIGN.md:4`(「**Phase 3 尚未實作**」)。
  → Codex 合理結論:「呢個係設計藍圖,confidence 公式未落地,冇機械把關」。
- **現行事實**:`thesis/lint.py:24-33` 檔頭明寫:
  > P2 formula lint ... `thesis/confidence_formula.py` ... > 0.01 -> **error** listing wiki subscores,
  > crowding, cycle, formula output, themes.yaml value.
  實作喺 `lint.py:282-320`;§4c check 喺 `:323-328`。15/15 theme confidence 已全部遷移做公式輸出
  (commit `0ac6f3f`)。**呢個正正係 Codex 會「建議」嘅嘢 —— 一日前已經做咗。**

### 假 finding #5|「thesis 層數據完整性問題:doc 講 9 個主題,themes.yaml 有 15 個」

- **Codex 會引**:`ARCHITECTURE.md:37`(「✅ live(**9 個** Type-B)」)+ `ARCHITECTURE.md:104`
  + `README.md:56`(「9 主題」)+ `KARS_MEMORY.md:166`(「thesis 擴到 **9 個** Type-B 主題」)
  —— **三個檔一致講 9**,而 `ARCHITECTURE.md` 仲自稱 "single source of truth"。
- **現行事實**:15 個 active(2026-07-11 discovery radar 新增 6 個,`STATUS.md:122` 有記)。
- **點解仍要修**:呢個技術上係「doc 錯」唔係「code 錯」,但 Codex 報出嚟會包裝成
  「registry 同 architecture doc 唔一致 = 資料完整性風險」,而**佢係啱嘅**(只係修嘅方向係改 doc)。
  同時佢會**繼續用 9 呢個數去做其他推論**(例:「9 個主題點解有 15 個 wiki 頁?」→ 更多假 finding 級聯)。

### 榮譽提名(唔入 top-5 但值得預期)

| 假 finding | Codex 會引 | 現行事實 |
|---|---|---|
| 「估值/expectations-gap 全系統缺席」 | `STATUS.md:107` | `valuation.py` 52KB 已生產化 + BT-5 過閘(`STATUS.md:91`);solvency 閘已接(`3f1fb33`) |
| 「PMCC 結構風險」 | `ARCHITECTURE.md:21`、`KARS_MEMORY.md:40-41` | PMCC 已於 scorecard v3.1 移除(`README.md:58`、`params/layer1_options.md:8`) |
| 「知識層得 102 篇語料,規模不足以支撐 thesis」 | `ARCHITECTURE.md:41` | `corpus.db` 11.5 GB / ~9.9k ticker 週度增量 |
| 「broken links ×4」 | `STATUS.md:250,253,254`、`HANDOFF.md:6` | 真 finding(但 low-severity),`STATUS.md:7-9` 已有預警 |

### ⚠️ 反面:Codex 會**啱**嘅嘢(唔好一竹篙打一船人)

呢兩條 Codex 若提出,**係真 finding,唔准當噪音打發**:

1. **insider `conf_eff` 未接分(P0-1)** —— 真.未修,`spine/__init__.py:13` 自己認。
   **但注意**:若 Codex 信 `ARCHITECTURE.md:59, 114`(講到似已接),佢會**漏報**呢條。
   即 ARCHITECTURE 嘅過度樂觀**幫倒忙**:令 adversarial reviewer 漏咗唯一一個真 P0。
2. **confidence 0.47 越 ≤0.40 上限**(`STATUS.md:256`)—— **需人判**,見 §2.2 S2。

---

## 4. 建議更新清單(按優先排序)

> 我唔改任何嘢 —— 以下係俾 gatekeeper 嘅具體清單,每條指明段落。

### P0 —— Codex 入場前必改(直接決定假 finding 數量)

| # | 檔:段落 | 改乜 |
|---|---|---|
| **P0-1** | **`thesis/DESIGN.md:4`** | 刪/改「Phase 3 尚未實作;這是定案的設計藍圖」→ 改成「**Phase 3 已實作並 live**;本檔 §0-§3/§5-§9 = 2026-07-01 設計收斂記錄,**§4a/§4b/§4c = 2026-07-15/16 凍結嘅執行規則(已接線)**」。**一行字,最高 ROI**(擋假 finding #4) |
| **P0-2** | **`AGENTS.md:15`** | 「P0 接線問題清單,**未修**」→ 逐條標狀態:「① insider conf_eff **仍未接**(`spine/__init__.py:13`);② credit **已作廢**(07-05 判死);③ 校準迴路 **已修**(`backfill_outcomes.py` + `daily_ic.cmd`);④ IC 判定 **已程式化**(`forward_ic.py:44`)」。**擋假 finding #1/#2/#3** |
| **P0-3** | **`AGENTS.md:18`** | 刪 `.agents/USER.md` 一行(檔已刪 12 日),或改指 `docs/2026-07-08_transition_plan.md`(🔒PERSONAL)—— **需人判**用戶偏好邊個 |
| **P0-4** | **`AGENTS.md`「Core discipline」節(:35-40)** | **加**新框架四條硬規則:(a) confidence = **§4a 凍結公式輸出**,唔准手工推導,`lint.py` formula check = **error**;(b) §4b red-team:INGEST 係審判,**夜班永遠唔准向上郁 confidence**,moat/growth 2 分須 Level-2 生還;(c) §4c red-team 判決**只准**入三通道,唔准喺 confidence 數字酌情;(d) single-source cap 0.30,脫 cap 須 Tier-1 擊中**承重** claim |
| **P0-5** | **`AGENTS.md`「Read first」節(:9-19)** | **加** `docs/INDEX.md`(現時完全冇提,而 `STATUS.md:6` 標佢做「★ 全 workspace 導航地圖」);**加** `INDEX.md:77` 嗰條救命規則:「引數字/結論 → 去 `backtest/results/*.md`(**落檔嘅先係真相,對話/記憶會錯**)」 |
| **P0-6** | **`AGENTS.md`「Phase 3」節(:26-33)** | 加 §4c / `magnitude_unconfirmed` / composite 分(P1)/ solvency 閘 / `kill_metrics.py` 一句話指針;明確講「新工具:`confidence_formula.py`/`composite_score.py`/`kill_metrics.py`/`magnitude_features.py`」 |
| **P0-7** | **`STATUS.md:256`** | **裁決** confidence ≤0.40 上限:廢除定保留?(見 §6 需人判 #1)。**唔裁決 = Codex 一定會撞** |
| **P0-8** | **`STATUS.md`「現在在哪」加 2026-07-14~16 節** | P1-P5 全部落地 / 公式凍結 + rubric + penalty 表 / red-team 協議 + 15 theme 全 red-team 完 / §4c 三通道 + sizing v2 接線 / 15/15 confidence 遷移 / solvency 閘接線。**更新檔頭 `:4` 日期** |

### P1 —— 高價值(擋剩餘假 finding + 修真矛盾)

| # | 檔:段落 | 改乜 |
|---|---|---|
| **P1-1** | `ARCHITECTURE.md:37, 104` | 「9 個 Type-B」→ **15 個 active**(擋假 finding #5) |
| **P1-2** | `ARCHITECTURE.md:59, 114` | insider:**明確標 `conf_eff` = display-only,未接分(P0-1 仍未修)**,唔好講到似已接線。**呢條防止 Codex 漏報真 P0** |
| **P1-3** | `ARCHITECTURE.md:21` | 漏斗圖刪 PMCC(v3.1 已移除)→ 對齊 `STATUS.md:14` 嘅 `LEAP/SHORT_CALL/CSP` |
| **P1-4** | `ARCHITECTURE.md:41` | 知識層「102 篇 + 88 源節點」→ 現行規模(corpus.db ~11.5GB / ~9.9k ticker 週度增量) |
| **P1-5** | `ARCHITECTURE.md:142` | 排程表 2 個 → 指返 `STATUS.md` 嘅 ~12 個總表(**唔好喺兩處維護排程表** —— 呢個係 drift 根源) |
| **P1-6** | `ARCHITECTURE.md:138` | 刪 `universe.yaml`(唔存在) |
| **P1-7** | `ARCHITECTURE.md:5` + **加一節** | 檔頭「最後收斂:2026-07-01」→ 2026-07-16;**加 Phase-3 現行方法論指針**(§4a/§4b/§4c 一句話 + 指 DESIGN) |
| **P1-8** | **`thesis/README.md`「加一個主題」步驟 1** | confidence「從 4-KPI + 佐證數 + 距 kill + payoff + regime 契合」自由推導 + 「INITIAL, uncalibrated」→ 改成 **§4a 凍結公式 + cap + lint 機械驗證**(擋假 finding #4) |
| **P1-9** | `STATUS.md:107` | 「估值全系統缺席(thesis_valuation.py 未起)」→ 標已由 `valuation.py` 提供 + BT-5 過閘 + solvency 閘已接 |
| **P1-10** | `STATUS.md:219` + `:251` | 2026-07-03 節嘅 P0 清單加逐條 **strikethrough + 現狀**(同 P0-2 一致);`:251`「未修 #1/#2 前錶行極都冇數」→ 標已修 |
| **P1-11** | `README.md:54, 56` | 「9 主題」→ 15;「37 個回測實驗」→ 129(`backtest/experiments/README.md:3` 一齊改) |

### P2 —— 衛生(唔改唔會死,但係 drift 溫床)

| # | 檔:段落 | 改乜 |
|---|---|---|
| **P2-1** | `.agents/KARS_MEMORY.md:3` | 刪 `USER.md`(自己 `:183` 記低已刪)|
| **P2-2** | `.agents/KARS_MEMORY.md:6` | 「最後更新:2026-07-06(§12)」→ 2026-07-13(§15);**加 §16 = 07-14~16 新框架** |
| **P2-3** | `.agents/KARS_MEMORY.md:40-41` | §3 刪 PMCC 或標「v3.1 已移除,見 §7」 |
| **P2-4** | `.agents/KARS_MEMORY.md:139` | §9 舊 confidence 概念描述加「**已被 §4a 凍結公式取代**」 |
| **P2-5** | `.agents/KARS_MEMORY.md:166, 244, 248, 251` | 9→15;排程時間 09:xx→05:xx;「四個排程」→ 指 STATUS 總表 |
| **P2-6** | **`.agents/KARS_MEMORY.md` 檔頭加「雙重記憶邊界」節** | 寫明:repo 內 KARS_MEMORY = **系統事實/決策/坑**(任何 agent 可讀);用戶 project memory(`~/.claude/projects/<slug>/memory/`)= **用戶偏好/跨專案教訓**;**寫記憶前兩邊查重**。→ 解用戶 memory `workspace-org-debt-pending` 記低嘅債務(見 §6 需人判 #4)|
| **P2-7** | `docs/INDEX.md:55` | `weekly_corpus.cmd`「待用戶授權排程」→ **已註冊 2026-07-12(SUN 08:30)** |
| **P2-8** | `docs/INDEX.md:57` | `thesis/DESIGN.md` 📘 DESIGN → **🟢 LIVE**(§4a/4b/4c 已接線) |
| **P2-9** | `docs/INDEX.md:16` + `STATUS.md:303` | KARS_MEMORY §1-14 / §1-10 → **§1-15**(兩處對齊) |
| **P2-10** | `docs/INDEX.md:45` | LIVE 部件補 `confidence_formula/composite_score/kill_metrics/magnitude_features/valuation/crowding_composite/dashboard_render/paper_ledger/brier` |
| **P2-11** | `docs/INDEX.md:6` | 更新日期 |
| **P2-12** | `STATUS.md:250, 253, 254` | 3 個 `_archive/` 路徑修正(`:7-9` 預警可保留做 belt-and-braces) |
| **P2-13** | `STATUS.md:300` + `backtest/experiments/README.md:3` | 37 → 129 |
| **P2-14** | `README.md:48` | 「HANDOFF.md ← 最近 session 詳細交接」→ 依 §5 裁決改寫 |

---

## 5. `HANDOFF.md` 冗餘判斷

### 判定:**歸檔(移入 `docs/_archive/2026-07-03_handoff.md`),唔好留喺 root**

### 理由(逐條有據)

| 面向 | 證據 |
|---|---|
| **已自標冗餘** | `HANDOFF.md:3`:「⚠️ **已被 `STATUS.md` 取代為入口(2026-07-06)。** 本檔僅保留為 2026-07-03 當日詳細記錄。」 |
| **STATUS 亦已降格佢** | `STATUS.md:314`:「2026-07-03 當日研究細節:`HANDOFF.md`(該 session 的詳細交接,**已被本檔取代為入口**)」 |
| **內容已被吸收** | `HANDOFF.md:5` 自己講:「其餘 findings(資本效率 / alpha=T1+T2 拆解等)**仍有效,已濃縮入 `.agents/KARS_MEMORY.md` §10**」。實測 `KARS_MEMORY.md:173` 確有完整濃縮版。用戶 project memory `regime-and-fear-greed-findings` + `tier1-metrics-decision` 亦各存一份 |
| **主動有害(唯一決定性理由)** | body `:37-38` 仍主張已判死嘅「Credit > VIX」;`:148` 仲有一條**未剔嘅 `[ ]` open decision** 叫人「Risk axis = credit + VIX + ...」。→ **假 finding #3 嘅彈藥庫**。檔頭 retract(`:4-5`)擋唔住 grep-driven 嘅 reviewer |
| **失效指針** | `:6` 指 `docs/2026-07-06_fable_brief.md` → 實際喺 `_archive/` |
| **佔住 root 嘅注意力預算** | root 得 5 個 .md;`AGENTS.md`(:5-19)同 `README.md:48` 都仲當佢係 agent 入口之一。Codex 一定會讀 |

### 具體執行(俾 gatekeeper)

1. `git mv HANDOFF.md docs/_archive/2026-07-03_handoff.md`
2. **移之前**,喺 body `:37-38` 同 `:148` 就地加 retract 標記(唔好齋靠檔頭)——
   即使歸檔咗,`_archive/` 仍然係 grep-able,credit 嗰條仍會咬人。
3. 連帶更新:`README.md:48`(刪 HANDOFF 或改標「已歸檔」)、`AGENTS.md`(冇直接提,但
   `STATUS.md:314` 要改路徑)、`docs/INDEX.md:15`(「`AGENTS.md` / `HANDOFF.md` / `README.md` | 🟢 ...」
   → 移去 §7 SUPERSEDED)、`STATUS.md:314`。

### 反對意見(誠實列出)

- findings #9-#12(top-10-days coverage / relevering / capital-efficiency / **alpha = T1 + T2 精確拆解**)
  嘅**推導細節**比 `KARS_MEMORY.md:173` 嘅濃縮版豐富好多,而 `:114-128`(#12 alpha 拆解)
  係 Karst 架構「點解 RSI-2 唔用嚟 SPY in/out」嘅**根本理據**。刪走會失去可溯源性。
- → **所以係「歸檔」唔係「刪除」**。`_archive/` 保留全文可溯,但唔再喺 root 誤導新 session。
- **需人判**:用戶可能想改為「合併入 STATUS.md」。我唔建議 —— `STATUS.md` 已經 37KB / 322 行,
  再塞 12 個 findings 嘅推導會令「START HERE」更加冇人讀得完。**歸檔 + KARS_MEMORY §10 濃縮版
  已經係啱嘅分層。**

---

## 6. 未解 / 需人判

| # | 議題 | 我知嘅 | 我唔知嘅(要人判) |
|---|---|---|---|
| **1** ★ | **confidence ≤0.40 上限係咪已廢?** | `STATUS.md:256` 寫「校準迴路未通之前,Phase-3 注碼 ≤20%、confidence 上限 ≤0.40」(2026-07-06 訂)。現行 `ai-power-grid` / `euv-lithography-monopoly` = **0.47**,兩者均經用戶批准嘅 15/15 遷移。§4a 凍結公式**只有** single-source cap 0.30,**冇** 0.40 全域上限。前提「校準迴路未通」本身已唔成立(`backfill_outcomes.py` + `daily_ic.cmd` 已跑 8 日) | (a) 0.40 cap 已被 §4a 體制**默示取代** → 改 STATUS;定 (b) cap **仍生效**,15/15 遷移不慎越界 → 要處理兩個 theme。**呢個係 Codex 一定會撞、而我冇證據單方面判嘅一條** |
| **2** | **`.agents/skills/` untracked 副本** | 未被 git 追蹤(`?? .agents/skills/`);同 `.claude/skills/` 差異全部係 `claude-obsidian`→**`Codex-obsidian`**、`Claude-Code-bound`→`Codex-bound` 嘅 find/replace。`claude-obsidian` 係真實存在嘅 repo,`Codex-obsidian` **唔存在** | 係 gatekeeper 進行中嘅 staging 定係意外污染?兩份 SKILL.md 邊份 authoritative?`AGENTS.md:28` 指 `.claude/` 嗰份。要唔要 commit / 刪 / 修返 proper noun? |
| **3** | **`HANDOFF.md` 最終處置** | 我建議歸檔(§5,理由完整) | 用戶可能想合併入 STATUS.md(我不建議,理由見 §5)或原地保留加強 retract |
| **4** | **雙重記憶邊界具體分工** | repo 內 `.agents/KARS_MEMORY.md` vs 用戶 `~/.claude/projects/<slug>/memory/` **兩邊都冇寫邊界**;實測有 overlap(同一份過時 P0 清單各存一份);用戶全域 CLAUDE.md 有「寫記憶前兩邊查重」但 **Codex 讀唔到**。用戶 memory `workspace-org-debt-pending` 已記低呢個係待辦 | 邊界點劃?我提咗一個建議切法(P2-6:系統事實 vs 用戶偏好),但呢個係用戶嘅制度決定,唔係我判 |
| **5** | **`STATUS.md:91` task #30(valuation 閘語意)係咪已被 solvency 閘解決?** | commit `3f1fb33` = "solvency conditional gate wired into weekly valuation + daily pick (per probe verdict)";`dashboard_render.py:744` `pick_ticker(..., solvency=None)` 已接 | task #30 講嘅「接 sizing 閘嘅執行語意」同 solvency 條件閘係咪同一件事?若係 → STATUS 要剔;若唔係 → 仲欠 |
| **6** | **`AGENTS.md` 應唔應該保留 P0-1(insider conf_eff)喺入口?** | 佢係唯一仲真.未修嘅 P0(`spine/__init__.py:13` 自認) | 保留 = Codex 會報(**真 finding,好事**);但要唔要順便決定「修定正式作廢」?`ARCHITECTURE.md:114` 已提修法方向(改接細價 12 月 portfolio tilt),`STATUS.md:42` 講 insider-tilt live snapshot 已跑但「display-only,未接 sizing.py」 |
| **7** | **`ARCHITECTURE.md:38`「3e A 型危機 tail 🔴 未建」係咪仍準確?** | 超出本次審計深度。`STATUS.md:31` 提到 `playbook_readout.py` 有「危機 sleeve 狀態」;`results/2026-07-08_crisis_rescue.md` 存在 | 未驗證。**標需人判**,唔敢寫入 CONTRADICTS |

---

## 7. 附錄:全部失效指針總表(已逐個 `ls` 驗證)

| 檔:行 | 指向 | 實況 |
|---|---|---|
| `AGENTS.md:18` | `.agents/USER.md` | **MISS** — 2026-07-04 已刪(`KARS_MEMORY.md:183`) |
| `KARS_MEMORY.md:3` | `USER.md` | **MISS** — 同上(自我矛盾) |
| `ARCHITECTURE.md:138` | `thesis/universe.yaml` | **MISS** — 全 repo 冇 |
| `STATUS.md:250` | `docs/2026-07-06_phase3_methodology_review.md` | **MISS** — 喺 `docs/_archive/` |
| `STATUS.md:253` | `docs/2026-07-06_dashboard_design.md` | **MISS** — 喺 `docs/_archive/` |
| `STATUS.md:254` | `docs/2026-07-06_bottleneck_candidates.md` | **MISS** — 喺 `docs/_archive/` |
| `HANDOFF.md:6` | `docs/2026-07-06_fable_brief.md` | **MISS** — 喺 `docs/_archive/` |
| `STATUS.md:107` / `:251` | `thesis/thesis_valuation.py` | **MISS** — 功能已由 `thesis/valuation.py` 提供 |

**驗證通過(冇問題,列出以示已查)**:`docs/ROADMAP_AGENTIC.md`、`docs/KARST_WIKI.md`、
`docs/2026-07-08_phase3_architecture.md`、`docs/2026-07-08_phase3_ws3_lifecycle.md`、
`docs/2026-07-09_ima_extraction_prompts.md`、`docs/2026-07-13_dashboard_v4_portable.md`、
`docs/2026-07-05_risk_control_layer_report.md`、`docs/2026-07-04_progress_and_next.md`、
`docs/2026-07-06_core_strategy_v2.md`、`docs/2026-07-06_wiki_verification_v2.md`、
`docs/2026-07-06_gap_conflict_register_v2.md`、`docs/2026-07-12_valuation_expectations_gap_spec.md`、
`docs/2026-07-03_strategy_methodology_review.md`、`docs/2026-07-03_dashboard_decision_experience.md`、
`backtest/scan.py`、`backtest/spine/`、`backtest/experiments/README.md`、`backtest/basket_temp.py`、
`backtest/playbook_readout.py`、`web/README.md`、`invariants/systematic_rules.md`、`thesis/README.md`、
`.claude/skills/thesis/SKILL.md`、`backtest/results/2026-07-01_*.md`(10 個)。

---

## 8. 統計摘要

| 類別 | 數目 |
|---|---|
| **CONTRADICTS(有原文 + 現行事實雙引證)** | **21** |
| — 其中「doc 講未建/未修,實際已建/已修」 | 9(A1×3、S3、S4×2、S5、I1、I2) |
| — 其中「doc 講已建/已接,實際未接」(**反向,更危險**) | 1(R2 — insider conf_eff) |
| — 其中「數字過時」 | 7(R1、R4、R5、M1、M2、K4、K5) |
| — 其中「引用已判死結論」 | 2(H1、A1-②) |
| — 其中「內部矛盾(同檔/跨檔)」 | 6(K1、K3、R3、S3、S4、I3) |
| **失效指針(逐個 ls 驗證)** | **8** |
| **缺失關鍵新規則(整條鏈零覆蓋)** | 7 個 doc × 6 類新規則 |
| **需人判** | **7** |
| 入口鏈對新框架 grep 命中 | **0 / 7 個 doc** |
| 入口鏈最舊檔齡 | **11 日**(`AGENTS.md`、`README.md`,2026-07-05 `cad034e`) |

---

*審計完成 2026-07-16。唯讀執行 —— 無修改任何被審檔案;本檔為唯一產出。*
*所有修改建議交 gatekeeper 執行;§6 七項需用戶裁決。*
