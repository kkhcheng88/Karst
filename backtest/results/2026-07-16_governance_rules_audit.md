# 治理規則全系統盤點 —— 「寫咗但冇 encode」審計(2026-07-16)

> **動機**:`thesis/DESIGN.md` §4a 凍結公式由零寫起,冇審計系統本身已有嘅治理規則,結果漏規則兩次
> (single-source cap 0.30 → 07-15 補;≤0.40 未校準上限 → 07-16 補)。**假設仲有第三條。**
> 本檔係唯讀盤點:掃晒全系統寫低嘅硬規則,同現行公式/code 對照,搵出仲有邊啲寫咗但冇 encode。
>
> **唯讀**:本次審計冇修改任何檔(本報告除外)。

---

## 1. 方法

**掃描範圍**(逐個讀):`STATUS.md`、`invariants/systematic_rules.md`、`ARCHITECTURE.md`、
`.agents/KARS_MEMORY.md`、`thesis/DESIGN.md`、WS1-WS5 五份規格檔
(`docs/2026-07-08_phase3_ws{1,2,3,4,5}_*.md`)。

**對照對象**(現行實作):`thesis/confidence_formula.py`、`thesis/sizing.py`、`thesis/lint.py`、
`thesis/themes.yaml`、`thesis/forward_ic.py`(ic_report.json)、`thesis/nightly_analysis_prompt.md`。

**實測**(唔靠估;script:`scratchpad/audit.py`,PYTHONUTF8=1):
逐條規則寫 python 對 `themes.yaml` 現行值量度越界;跑 `thesis/lint.py --no-ticker-check`
同 `thesis/sizing.py` 攞真實讀數;`ic_report.json` 驗校準前提。

### ⚠️ 併發警告(影響本報告時效)

審計期間(21:13→21:51)**另一個 session 正在併發修 0.40 cap**,working tree 未 commit:
`git diff --stat` 顯示 `AGENTS.md / ARCHITECTURE.md / HANDOFF.md / STATUS.md / thesis/DESIGN.md /
thesis/confidence_formula.py` 六個檔改緊。`DESIGN.md` 由 25,357→26,909 bytes、行號整體下移 16 行。
**本報告所有行號 = 2026-07-16 21:51 working tree 嘅現行行號**(唔係 session 開始時嘅快照)。
`STATUS.md:256` 因為頭部插入 5 行,現行係 **`STATUS.md:261`**。

---

## 2. 規則登記冊

圖例:✅ = 有 encode 且有機械檢查;🟡 = 有 encode 冇機械檢查(或只印 footnote);❌ = 冇 encode。

| # | 規則 | 出處(檔:行) | 現行 encode | lint 機械檢查 | 實測越界? | 風險 |
|---|---|---|---|---|---|---|
| R1 | single-source cap **0.30** | `ws3_lifecycle.md:162`、`DESIGN.md:100-104` | ✅ `confidence_formula.py:SINGLE_SOURCE_CAP` | ✅ warn `lint.py:276` + formula lint | **0/15 越界** | 低(已補) |
| R2 | confidence ∈ **(0, 0.6]** | `ws3_lifecycle.md:137` | ✅ `lint.py:243` | ✅ ERROR | 0/15 | 低 |
| R3 | **confidence 上限 ≤0.40**(校準未通) | `STATUS.md:261` | 🟡 **修緊(未 commit)**:`confidence_formula.py:UNCALIBRATED_CAP` | ✅(修完後)formula lint | **遷移做咗一半**(見下) | **高** |
| R4 | **Phase-3 注碼 ≤20%**(校準未通) | `STATUS.md:261`(**同一句!**) | ❌ **冇** | ❌ | 讀法而定 → **需人判** | **高** |
| R5 | **`corroborates:` 標記**(≥2 sources 要至少一條) | `DESIGN.md:137-138`(原文寫明「執行檢查:lint…」) | ❌ **冇** | ❌ `grep -c corroborates lint.py` = **0** | 0/2(兩個都有,靠人手自律) | **最高** |
| R6 | 證據過期 **120d** → conf×0.8 + status→watch;再 120d → delisted | `ws3_lifecycle.md:171` | ❌ **冇** | ❌ 只檢查日期合法(`lint.py:266`) | 0/15(max age **8d**) | 中 |
| R7 | Beta 化 → delisted(126d corr>0.9 持續 6 個月) | `ws3_lifecycle.md:172` | 🟡 `thesis/beta_check.py` 存在 | ❌ 唔喺 lint | 未測 | 中 |
| R8 | 同一 meta_factor 合計 ≤ **50%** | `ws3_lifecycle.md:176`、`ws5:30` | ✅ `sizing.py:50 MF_CAP_PCT` | ❌(sizing 層執行) | 已 cut:ai-capex raw $58.3k → $10,250 | 低 |
| R9 | 衛星總部署 ≤ **50%**(PRELIMINARY) | `ws5:26,38` | ✅ `sizing.py:51 PRELIM_TOTAL_CAP_PCT` | ❌ | 實跑 $16,302 < $20,500 ✅ | 低 |
| R10 | FAIL 熔斷 → **25%**、新倉凍結 | `ws5:40` | 🟡 `sizing.py:52 FAIL_TOTAL_CAP_PCT`(cap 有;「新倉凍結」冇) | ❌ | N/A(status=PRELIMINARY) | 中 |
| R11 | 單主題上限 min(conf×$20k, $15k) | `ws5:24` | ✅ `sizing.py:122` | ❌ | ✅ 合規 | 低 |
| R12 | **A 型 sleeve ≤ 衛星 10%**(獨立預算) | `ws5:32`、`ws2_crisis.md:29` | ❌ **只印 footnote**(`sizing.py:497-498`) | ❌ | N/A(registry 冇 A 型) | 中(潛伏) |
| R13 | **細價純 play ≤ 該主題 1/3 + 要有自己 kill** | `ws5:29` | ❌ **只印 footnote**(`sizing.py:499-500`) | ❌ | **未量度**(ticker 層冇 itemize) | 中 |
| R14 | **moat/growth 攞 2 分 = 要 Level-2 red-team 生還;齋引用最高 1.5** | `DESIGN.md:161-162` | ❌ **冇** | ❌ | 5 格攞 2 分,全部有 red-team 報告 → **實質合規** | 中 |
| R15 | **夜班永遠唔准向上郁 confidence**(硬規則) | `DESIGN.md:157` | ❌ 冇機械閘 | ❌ | 只靠 prompt 自律(`nightly_analysis_prompt.md:15`) | 中 |
| R16 | Kill 觸發 → **T+1 收市全部離場,冇裁量** | `ws5:44` | ❌ 冇機械 | ❌ | N/A | 需人判 |
| R17 | source id **按機構計**(N 篇 = 1 源) | `ws3_lifecycle.md:190` | ❌ 冇 | ❌(lint 淨數 list 長度) | 冇重覆 id | 低 |
| R18 | WS4:每主題 **3-7 個錶封頂** | `ws4_early_detection.md:37` | ❌ 冇 | ❌ | **0 個越頂**(最多 4) | 低 |
| R19 | 裁判狀態機門檻(matured 60/150、IC 0.05、IR 0.5) | `ws1_calibration.md:30-33` | ✅ `forward_ic.py` → `ic_report.json:thresholds` | — | 規格↔實作**逐個對得上** | 低 |
| R20 | 估值閘 P_base<0.20 → 注碼 ×0.5 | **只喺 code comment**(`sizing.py:88-97`) | ✅ `sizing.py:95-96` | ❌ | 4 個 theme 入閘(表內「½」) | 中(**無 doc 家**) |
| R21 | INV-1..INV-9(CSP 20%/50%、禁裸賣、LEAP 右側…) | `invariants/systematic_rules.md:29-38` | 🟡 spine 層 | ❌ | 未測(Phase-3 範圍外) | 需人判 |

---

## 3. 「寫咗但冇 encode」清單(最重要一節)

### 🔴 #1 — `corroborates:` 執行檢查缺席 **(最危險:守住 cap 出口嘅門冇上鎖)**

**規則原文**(`thesis/DESIGN.md:137-138`):
> - 執行檢查:lint 對 `sources:` 有 ≥2 條時,要求至少一條標明 corroborates: <claim>,
>   防止「加個 newsletter 就解 cap」嘅假獨立。

**code 對照**:**冇**。`grep -c "corroborates" thesis/lint.py` = **0**。規則原文**直接點名 lint 做執行者**,
但 lint.py 完全冇呢個檢查。

**實測現行值**:15 個 theme 得 **2 個**係 multi-source(`ai-power-grid`、`euv-lithography-monopoly`),
兩個都**確實有** `corroborates:` 標記 → **今日 0 越界**(靠人手自律,唔係靠機器)。

**點解最危險 —— 睇實測數字就明**:

```
conf 全表(2026-07-16 實測):
  0.47  ai-power-grid            (sources=2)  ← 唯一兩個脫咗 cap 嘅
  0.47  euv-lithography-monopoly (sources=2)  ←
  0.30  memory-supercycle        (sources=1)  ┐
  0.30  photonics-optical        (sources=1)  │
  0.30  advanced-packaging       (sources=1)  │ 13/15 全部俾
  0.30  space-satellite          (sources=1)  │ single-source cap
  0.30  rare-earth-materials     (sources=1)  │ 釘死喺 ≤0.30
  ... (下略)                                   ┘
```

**13/15 個 theme 嘅 confidence 係俾 single-source cap 釘住嘅** —— 即係話 R1 個 cap 幾乎係
**唯一實際綁緊嘢嘅約束**。而「脫 cap」係一個 **binary 開關**:一脫,confidence 即刻由 0.30 跳到公式
raw(0.469,**+56%**),直接乘落注碼。

**而呢個開關嘅防偽機制(corroborates)冇上鎖。** 更加要留意:**唯一兩個脫咗 cap 嘅 theme,
正正就係唯一兩個越咗 0.40 界嘅 theme** —— 同一個出口,兩條規則(R5 假獨立防偽 + R3 未校準上限)
一條冇 encode、一條啱啱先補。呢個唔係巧合,係結構:**cap 出口就係全系統風險最集中嗰一點。**

**建議點補**(lint.py,~10 行):
```python
# admission gate ERROR(唔係 warning——呢條係防 gaming,唔應該靠自律)
if len(sources) >= 2:
    if not any(isinstance(s, dict) and str(s.get("corroborates", "")).strip() for s in sources):
        errs.append("sources >= 2 但冇任何一條標明 corroborates: <claim> "
                    "(DESIGN §4a:137 假獨立防偽)—— 脫唔到 single-source cap")
```
**兼要諗**:脫 cap 嘅判定應該**由 corroborates 標記驅動**,而唔係由 `len(sources)` 驅動。
現行 `confidence_formula.py` 嘅 cap 條件係 `int(n_sources) <= 1` —— 即係**加多一個
冇 corroborates 嘅 source entry 就即刻脫 cap**,正正就係 DESIGN 原文話要防嗰個「加個 newsletter
就解 cap」。建議 `confidence()` 收 `n_corroborating_sources` 而唔係 `n_sources`。

---

### 🔴 #2 — `STATUS.md:261` **同一句嘅另一半**:「Phase-3 注碼 ≤20%」

**規則原文**(`STATUS.md:261`,一句兩條規則):
> 5. 衛星紀律:校準迴路未通之前,**Phase-3 注碼 ≤20%**、**confidence 上限 ≤0.40**。

**今日嘅併發修復只攞咗後半句(≤0.40),前半句(注碼 ≤20%)一樣冇 encode。**
兩條規則同一個前提、同一句、同一行 —— 呢個正正示範咗「由零寫起、唔審計既有規則」點樣漏嘢:
即使今次專登去攞呢條 line 嘅規則,都仲係只攞咗一半。

**code 對照**:`sizing.py` 完全**冇 20% 呢個概念**,亦**冇「組合」呢個變數**
(`DEFAULT_BUDGET = 41_000.0` 淨係衛星預算)。最接近係 `PRELIM_TOTAL_CAP_PCT = 0.50`(衛星嘅 50%)。

**實測**(`python thesis/sizing.py`,2026-07-16):
```
judge status: PRELIMINARY   satellite budget: $41,000
TOTAL final_$ = $16,302
total deployment cap for status=PRELIMINARY: $20,500 (50% of budget)
```
**兩個讀法,結論相反 → 需人判**:
- **讀法 A(20% = 組合)**:`ws5:5` 衛星 = 組合 30% → 組合 ≈ $136.7k。
  實際部署 $16,302 = 組合 **11.9%** ✅;結構 cap $20,500 = 組合 **15%** ✅ 合規。
  (`ws2_crisis.md:39`「≤10% 衛星(≈ 組合 3%)」印證 10%×30%=3% → 衛星 ≈ 組合 30% 呢個換算。)
- **讀法 B(20% = 衛星)**:20% × $41k = $8,200。實際部署 $16,302 → **越界 ~2 倍** ❌。

**我傾向讀法 A**(「Phase-3 注碼 ≤20% of Phase-3」自我指涉,唔通;「未校準時衛星只准去到組合 20%
而唔係全額 30%」語意通),**但呢個係我嘅推測,唔係文件寫明,要用戶拍板。**

**⚠️ 就算讀法 A 成立,合規係「數字啱撞」出嚟,唔係「有嘢守住」**:0.50 × 30% = 15% ≤ 20% 純粹係
兩個獨立常數乘出嚟啱好喺界內。冇任何 code 知道「20%」呢條線存在;`DEFAULT_BUDGET` 一升、
或者 `PRELIM_TOTAL_CAP_PCT` 一改(例如裁判 PASS 後跳 100% → 組合 30% > 20%),**冇嘢會叫**。

**建議點補**:①用戶先裁定分母;②裁定後喺 `sizing.py` 加 `PORTFOLIO_SIZE` + assert,
或者最低限度加一個 `total_cap_for_status()` 層嘅 doc-cited 上限常數(**唔准無主 magic number**,
同今日 `confidence_formula.py` 補 cap 時定嘅紀律一致)。

---

### 🟠 #3 — 證據過期 120d 降級(WS3 退場三途之一)

**規則原文**(`docs/2026-07-08_phase3_ws3_lifecycle.md:171`):
> | 證據過期 | `today - last_evidence > 120d` | confidence ×0.8、status→watch;再 120d → delisted |

**code 對照**:**冇**。`lint.py:266` 淨係檢查 `last_evidence` 係**合法 ISO 日期**,
**唔檢查佢幾舊**。(`kill_metrics.py:44 STALE_DAYS = 120` 係另一回事 —— 佢管 kill 讀數嘅
`current_as_of`,唔係 theme 嘅 `last_evidence`。同一個數字、唔同用途,容易睇漏當咗已 encode。)

**實測**:15/15 theme 嘅 `last_evidence` **最舊得 8 日**(max age = 8d)→ **0 越界**。
呢條規則**今日 dormant** —— 但正因為 dormant,冇人會發現佢冇 encode。系統一慢落嚟
(例如過時嘅慢主題、或者 ingest 停咗),第一個過 120d 嘅 theme 唔會有任何嘢自動降佢。

**建議點補**:lint.py admission 檢查加 age 計算 → >120d 出 WARNING(標明應 ×0.8 + watch)、
>240d 出 ERROR(應 delisted)。**唔好自動改 themes.yaml**(同夜班紀律一致:機器偵測、人手落實)。

---

### 🟠 #4 — WS5 兩條注碼細則:只印 footnote,冇執行

**規則原文**(`docs/2026-07-08_phase3_ws5_expression.md:29`、`:32`):
> ③每主題最多一隻細價純 play(10x 位),佔該主題注碼 **≤ 1/3**,必須有自己嘅 kill。
> **A 型危機 sleeve 另設獨立預算 ≤ 衛星 10%**,平時 100% 現金。

**code 對照**:`sizing.py:497-500` **淨係 print 兩行 footnote 提你**,冇任何計算:
```
  - Type-A crisis sleeve <=10% of satellite budget is a SEPARATE budget (WS5 Sec1.5),
    not shown in this table (no Type-A themes currently in registry -- all 9 are Type B).
  - Small-cap pure-play position inside a theme <= 1/3 of that theme's final $
    (WS5 Sec1.3), and must carry its own kill_condition. Not itemized per-ticker here.
```
**公道講**:呢個係**誠實嘅自我披露**(明寫「Not itemized per-ticker here」),唔係扮咗做。
但「誠實咁講咗冇做」≠ 有規則守住 —— 呢兩條規則實質**淨係活喺 print statement 入面**。

**實測**:
- A 型 ≤10%:registry **冇 A 型 theme**(15/15 都係 B 型)→ N/A,**潛伏**。(注意 footnote 寫住
  「all 9 are Type B」—— **過時**,而家 15 個。)
- 細價純 play ≤1/3:**量度唔到** —— sizing 只出到 theme 層 `final_$`,冇 ticker 層分配,
  所以「邊隻係細價純 play、佔幾多」**系統根本唔知**。呢條規則今日**冇可能檢查**(唔係「冇違反」)。

**建議點補**:①A 型 sleeve:等有 A 型 theme 先做,但而家就要喺 `raw_cap()` 加 `type == "A"` 分支
(而家 `raw_cap` 對 A/B 一視同仁 —— 一個 A 型 theme 今日 admit 落去會直接攞 B 型嘅
`min(conf×20k, 15k)`,**靜靜咁越咗 10% 獨立預算**);②細價純 play:要 ticker 層分配先檢查得到,
屬 sizing v3 範圍,**而家最低限度應該喺 lint 檢查「細價純 play 有冇自己嘅 kill」**(呢個 part
唔使 ticker 層注碼都做得到)。

---

### 🟡 #5 — `moat`/`growth` 攞 2 分要 red-team 生還(§4b rubric 掛鈎)

**規則原文**(`thesis/DESIGN.md:161-162`):
> **Rubric 掛鈎(§4a 補充):**moat / growth 格攞 2 分嘅前提 = 該格承重 claim 經過
> Level-2 red-team 且生還(wiki 有記錄);齋引用(未經抗辯)最高 1.5。

**code 對照**:**冇**。lint 嘅 formula lint 只驗「wiki subscores 套公式 = themes.yaml confidence」,
**唔驗 subscores 本身合唔合 rubric 前提**。即係話:一個未經 red-team 嘅 theme 自己俾自己 moat 2/2,
只要 themes.yaml 個數同公式對得上,**lint 全綠**。

**實測**:5 格攞 2 分(photonics moat+growth、ai-power-grid growth、advanced-packaging growth、
euv moat),**全部都有對應 red-team 報告**(`backtest/results/2026-07-1{5,6}_redteam_*.md`)
→ **實質合規**(15/15 theme 已完成 Level-2 red-team,commit `6fd6689`)。

**建議點補**:lint 加 —— subscore ≥2 嘅 moat/growth 格,wiki 必須有 red_team 記錄,否則 ERROR。
**順帶提一個 regex 脆弱點**:`lint.py:78 RED_TEAM_RE = r"red_team|##\s*red.?team"` 認唔到
`advanced-packaging.md` / `euv-lithography-monopoly.md` 嗰種散文式記法(「red-team 詳見 …」)。
今日冇害(嗰兩個 theme 冇 `magnitude_unconfirmed` node,§4c 檢查撞唔到),但如果照上面建議
擴大 red-team 檢查範圍,**要先修呢個 regex**,否則會出一堆假 ERROR。

---

### 🟡 #6 — 「夜班永遠唔准向上郁 confidence」(明文標住「硬規則」)

**規則原文**(`thesis/DESIGN.md:157`):
> **夜班永遠唔准向上郁 confidence**(硬規則)。

**code 對照**:**冇機械閘**。純粹靠 prompt 自律(`nightly_analysis_prompt.md:15`:
「confidence/cycle_stage 一律預設『維持』,冇 Tier-1 財報級新事實唔准郁」)。

**實測**:**無法機械驗證**(要 diff 夜班前後 themes.yaml + 歸因)。

**評語**:呢條係**規則原文自己叫自己做「硬規則」,但實作係軟嘅**。夜班寫嘅係草稿、
唔准剔 `[x]`、唔准改 `nodes:` —— 呢啲紀律寫得好清楚,但全部靠 LLM 跟 prompt。
**建議**:git pre-commit hook 或夜班 wrapper 加 assert:夜班 session 產生嘅 themes.yaml diff,
任何 `confidence:` 向上 = 拒絕 commit。呢個係少數**真係做得到機械化**嘅 NHITL 紀律。

---

## 4. 矛盾規則 / 前提失效規則

### 4.1 🔴 矛盾:`≤0.40`(STATUS:261)vs `∈ (0, 0.6]`(WS3:137)

| | 出處 | 日期 | 數字 | encode 狀態 |
|---|---|---|---|---|
| 規則 X | `STATUS.md:261` | 2026-**07-06** | confidence 上限 **≤0.40**(校準未通之前) | 今日先補入公式 |
| 規則 Y | `ws3_lifecycle.md:137` | 2026-**07-08** | confidence ∈ **(0, 0.6]** | 一直係 lint admission ERROR |

**兩條都係「校準前」適用,數字唔同(0.40 vs 0.6),而且互相冇引用對方。**
WS3(07-08)**晚過** STATUS:261(07-06),而且 WS3 先係被 encode 嗰個 —— 所以過去 10 日,
**lint 一直合法放行 0.47**(≤0.6 過關),冇報過任何錯。呢個就係 0.47 可以靜靜咁存在嘅機制。

**需人判**:邊條 governing?可能性 ——(a)0.40 係 0.6 之上再加嘅一層時限性緊縮(兩條並存,取最緊)
—— 今日併發修復採取咗呢個解讀;(b)WS3 嘅 0.6 已經 supersede 咗 07-06 嗰句。
**我傾向 (a)**(0.6 = 結構上限,0.40 = 校準前臨時上限,語意唔衝突),**但要用戶確認**,
因為呢個決定緊 euv 應該係 0.40 定 0.47。

### 4.2 🟡 前提測試:「校準迴路未通」—— **前提仍然成立,規則 active**

實測 `thesis/ic_report.json`(2026-07-16 05:33 生成):
```json
"status": "PRELIMINARY",  "circuit_breaker": false,
"thresholds": { "preliminary_matured_min": 60, "pass_mean_min": 0.05,
                "pass_ir_min": 0.5, "fail_matured_min": 150 },
"coverage": { "predictions": 618, "tickers": 64, "dates": 11 },
"horizons": { "21": { "matured": 0, "pending": 612, "raw_ic_daily": null, ... } }
```
**matured = 0 / pending = 612,裁判一個讀數都未出過**,門檻要 60 → **前提 100% 成立**。
→ R3(≤0.40)同 R4(注碼 ≤20%)**兩條都仲生效**,唔係過期規則。
(對照 `KARS_MEMORY` / `fable_session_handover.md:65`:「裁判 matured=0,首判決 ~10 月」—— 一致。)

### 4.3 🟡 前提失效(文件過時,非規則衝突)

| 出處 | 過時內容 | 現況 |
|---|---|---|
| `ws5:16,19` | 「現時 **9 主題全部 late**」→ 全部細注 | 而家 **15 個**,cycle_stage 有 `early`(space-satellite) |
| `ws5:24` | 例:「AI-電力 0.33 → $6.6k;記憶體 0.38 → $7.6k」 | 現值 0.40 / 0.30(例子過時,**非規則**) |
| `sizing.py:498` | footnote:「no Type-A themes… **all 9 are Type B**」 | 而家 15 個(數字過時) |
| `STATUS.md:235-238` | 「concentration.py / beta_check.py **未排入任何排程**」 | 對照 `STATUS.md:40`(**已註冊 2026-07-12**)+ `thesis/weekly_risk_check.cmd` 存在 → **235 段 stale**,低風險 |

### 4.4 🟡 「encode 咗但 doc 冇寫」:估值閘 0.20 / ×0.5(R20)

`sizing.py:95-96` 嘅 `VAL_GATE_PBASE_MAX = 0.20` / `VAL_GATE_FACTOR = 0.50` **喺任何 spec doc 都搵唔到**
—— 理據淨係活喺 `sizing.py:88-97` 個 code comment(「brain ruling, 2026-07-13, user delegated」,
引 BT-5 三個 known-top 案例 P_base ≤ 0.183)。**理據其實好紮實**(有 backtest、有案例),
但佢**冇 doc 家** —— 而 `STATUS.md:91` 仲寫住「接 sizing 閘嘅執行語意**待用戶揀**(task #30)」,
即係 **STATUS 話待裁決、code 已經接咗**。今日 4 個 theme 實際食緊呢個 ½ 閘。
**需人判**:呢個 gate 係咪已經 approved?**建議**:寫返入 WS5 §8 或估值 spec,補 doc 出處。

---

## 5. 建議

### 5.1 公式(`confidence_formula.py`)應該加咩

| 加咩 | 理由 | 出處 |
|---|---|---|
| **cap 條件由 `corroborates` 數驅動,唔好由 `len(sources)` 驅動** | 而家加個冇 corroborates 嘅 source entry 就脫到 cap = DESIGN 原文明文要防嗰個 gaming | `DESIGN.md:137-138` |
| (已做,確認)`UNCALIBRATED_CAP = 0.40` + `caps_binding` | 併發 session 今日已補 | `STATUS.md:261` |

### 5.2 lint(`lint.py`)應該檢查咩(**按 ROI 排序**)

| 優先 | 檢查 | 級別 | 對應規則 |
|---|---|---|---|
| **P0** | `len(sources)>=2` → 至少一條有 `corroborates:` | **ERROR** | R5(`DESIGN.md:137`) |
| **P0** | `today - last_evidence > 120d` → 應 ×0.8+watch;>240d → 應 delisted | WARN / ERROR | R6(`ws3:171`) |
| **P1** | moat/growth subscore ≥2 → wiki 要有 red_team 記錄(**先修 `RED_TEAM_RE` regex**) | ERROR | R14(`DESIGN.md:161`) |
| **P1** | 細價純 play 要有自己嘅 kill_condition | WARN | R13(`ws5:29`) |
| **P2** | A 型 theme 唔准用 B 型 `raw_cap()`(`sizing.py` 層 assert) | ERROR | R12(`ws5:32`) |
| **P2** | 夜班 diff 守衛:confidence 向上 = 拒絕(pre-commit hook,唔係 lint) | ERROR | R15(`DESIGN.md:157`) |

### 5.3 制度建議(**根因,唔係逐條補窿**)

呢個係**第三次**同類 bug(0.30 → 0.40 → 而家搵到 6 條)。逐條補窿補唔完,根因係:
**規則散落喺 7 個檔(STATUS / DESIGN / WS1-5 / invariants),冇單一登記冊,冇「規則 → encode 位置」嘅映射。**

建議:
1. **本檔 §2 個登記冊入 repo 做常設檔**(例如 `invariants/RULES_REGISTRY.md`),
   每條規則一行:規則 / 出處(檔:行)/ encode 位置 / 機械檢查 / 前提。
2. **紀律(已寫入今日 `DESIGN.md` §4a,建議升格做全系統規則)**:
   - 任何 doc 寫低嘅硬規則 → 必須 encode 或者 lint 檢查,**唔可以靠人記得**;
   - 任何 code 嘅 cap/閘 → 必須有 doc 出處(檔:行),**唔准無主 magic number**(R20 就係反例)。
3. **加一個 meta-lint**:掃 `sizing.py` / `confidence_formula.py` 嘅常數,冇 doc 引用嘅出 WARN。
4. **改公式/rubric 嗰陣,強制跑一次規則登記冊審計**(今次 §4a 由零寫起 = 根因)。

---

## 6. 附:實測命令(可重跑)

```powershell
$env:PYTHONUTF8=1; $env:PYTHONIOENCODING="utf-8"
python thesis/lint.py --no-ticker-check    # admission + formula lint
python thesis/sizing.py                    # 真實注碼 / cap / 集中度 cut
python -c "import json;print(json.load(open('thesis/ic_report.json'))['horizons']['21']['matured'])"  # 校準前提
```
盤點 script:`scratchpad/audit.py`(themes.yaml 逐條規則越界量度;唯讀)。

**本次審計狀態**:唯讀完成,冇改任何檔(本報告除外)。
**時效**:2026-07-16 21:51 working tree(有未 commit 嘅併發修改,見 §1 併發警告)。
