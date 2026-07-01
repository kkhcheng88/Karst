# Finance / Investment Method Distillation — Requirement Profile + Skill Instruction

**Type:** Requirement Profile(對齊 VLOS [`distillation-core-spec.md`](../../VLOS/docs/distillation-core-spec.md) §12)
**Core Methodology:** VLOS `distillation-core-spec.md`(DS0-DS5 共用工作流、TDD gates、state machine、
workbench structure、incremental merge —— 全部沿用,本檔只定義 finance-specific 差異,不複製)
**Status:** v1.0 — for a reusable "finance method distillation" skill
**Scope:** 把交易/投資的**方法論**(SEPA/VCP、CAN SLIM、Wyckoff、mean-reversion 系統…)與**概念/框架**
(VRP、factor、regime…)蒸餾成**結構化、有引用、可回測**的知識產物。

---

## 0. 為什麼金融版跟法律版不同(讀這段就懂全部)

法律知識蒸餾的產物是**可引用的散文** `{topic}.md`。金融方法**不能停在散文**,因為:

> **一個交易方法的價值 = 它有沒有 edge = 只能用回測回答,不能用「作者說有效」回答。**

所以金融 Profile 在 VLOS 工作流上加**兩個硬性差異**:

1. **產物是「機器可讀的 spec」+ 散文**,不是只有散文。spec = 每條規則 → **predicate + 具名參數 +
   作者原值 + 待測範圍**。目的是能直接編碼回測。
2. **「作者宣稱有效」= Tier-2 待驗假設,不是 Tier-1 事實。** 書對「**方法是什麼**」是一手(忠實抽取);
   對「**它賺錢**」是意見(作者戰績多半是倖存者偏誤)。→ **多一個 stage:方法在 backtest 通過前,
   status 不能是 `validated`。**

因此 finance state machine 在 VLOS 的 `raw→verified→tagged→synthesized→reviewed→published` 之間插入:

```
... → synthesized → backtested → (validated | killed | partial) → published
```

**未回測的方法,只能標 `synthesized`,不得當「可用/有效」使用。** 這是金融版的核心紀律,對應本專案
已建立的 CIO-Phase-0 原則(`ARCHITECTURE.md §5`:勝率是騙子、發表即衰減、long-only ≠ long-short 鏡子)。

---

## 1. Domains(金融的三個 domain,類比法律的 client/tactics/drafting)

| Domain | 用途 | 產物 | 是否須回測 |
|---|---|---|---|
| **`method`**(主) | 系統化的交易/選股技術(SEPA/VCP、RSI-2 系統…) | **機器 spec + 散文 + 回測結果** | ✅ **必須** |
| **`concept`** | 框架/理論(VRP、factor、估值、regime 分類) | 知識 synthesis(近法律版) | 🟡 若可量化則測 |
| **`playbook`** | 情境戰術(危機劇本、財報前後、sizing 紀律) | 條件式規則 + 觸發 | 🟡 事件研究 |

> 使用者聚焦「投資**方法**」→ 預設走 `method`。同一本書可跨 domain 重蒸(用不同 tag set),同 VLOS。

---

## 2. Workbench 結構(沿用 VLOS §10,path 換成 finance)

```
knowledge/{domain}/{method}/            # e.g. method/minervini_sepa_vcp/
├── sources/                            # DS0-DS1:每個來源一個 .md + front matter
│   └── {source_slug}.md
├── excerpts/                           # DS2:每個來源一個 tagged excerpt file
│   └── {source_slug}_excerpts.md
├── runs/{date}/                        # DS3-DS4:不可變 synthesis 記錄
│   ├── {method}_draft.md
│   └── review.md
├── {method}.md                         # 散文 synthesis(引用 excerpt IDs)
├── {method}.spec.yaml                  # ★ 機器 spec(predicate + 參數 + 待測範圍)
└── {method}.backtest.md                # ★ DS-BT 回測結果 + 判決(validated/killed/partial)
```

在 Karst 內建議 `knowledge/` = `thesis/`(既有知識層):`thesis/.raw/<source>` 放原文、
`thesis/specs/<method>.spec.yaml` 放 spec、`thesis/wiki/<method>.md` 放散文。worker agent 可自選,
但**三件產物(散文 / spec / 回測)缺一不可**。

---

## 3. DS0-DS1 — Source Intake & Verification(finance front matter)

沿用 core-spec §3-§4。source front matter 的 finance 差異:

```yaml
---
title: "{Book / Course / Paper / KOL thread}"
author: "{Author}"
type: book | course | paper | kol | filing | transcript      # source medium
tier: 1 | 2 | 3          # 1=一手(逐字稿/filing/價格);2=方法書/分析報告/KOL(意見);3=新聞
claim_status: unverified # 作者對「有效」的宣稱一律 unverified,直到 DS-BT
edition: "{2nd ed 2016}" # 版本(方法書常改版,see core-spec §8.1)
ingested_at: YYYY-MM-DD
verified: true | false
reliability: primary | secondary | inferred | questionable
notes: "..."
---
```

**finance rule:** 方法書 `type: book, tier: 2`(方法本身可信=一手技術,但「賺錢」是 Tier-2 待驗)。
**不得**因為作者名氣把 `claim_status` 靜默升級。

---

## 4. DS2 — Tagged Excerpts(finance tag set)

沿用 core-spec §5 的 excerpt contract(canonical quote + supported assertion + scope + boundary +
failure conditions + audit)。**tag set 換成 finance-method 的 8 個(不得自創,不 fit 就 flag)**:

| Tag | 用途 | → 對應 spec 維度 |
|---|---|---|
| `[進場規則]` | 何時買/觸發(pivot 突破、oversold…) | entry |
| `[出場/停損]` | 何時賣/停損/移動停利 | exit |
| `[選股/過濾]` | 哪些標的合格(趨勢模板、RS-rating、流動性) | filter |
| `[部位管理]` | sizing、加減碼、風險上限、集中度 | sizing |
| `[市場前提/regime]` | 大盤/regime 條件(多頭才做、VIX 閾值) | regime |
| `[量化參數]` | **具體數字**(8% pivot、25%→12%→6% 收縮、量縮 %) | params |
| `[作者宣稱-未證]` | 作者聲稱的績效/勝率/報酬 —— **標記為待驗,不採信** | claim(Tier-2) |
| `[反面教材]` | 不要做的事、常見錯誤、失效條件 | anti |

**每條 `[量化參數]` 必須照錄原文數字**(canonical),DS3 才轉成「參數 + 待測範圍」。
作者含糊處(「量要明顯縮」)→ 標 `[量化參數]` 並在 assertion 註明「vague → 待參數化」。

---

## 5. DS3 — Consolidation:**按維度合併 → 機器 spec + 散文**

這就是你要的「**merge with proper dimensions**」。**維度 = tag 對應的 spec section**
(entry / exit / filter / sizing / regime / params / claim / anti)。DS3 讀**全部** excerpt files,
按維度歸併,每條 assertion 引用 excerpt IDs。

### 5a. 機器 spec 模板 `{method}.spec.yaml`(★ finance 核心)

```yaml
method: minervini_sepa_vcp
version: "1.0"
sources: [minervini_wizard_2013, minervini_champion_2016]
claim_status: unverified           # 直到 backtest
dimensions:
  filter:                          # 選股過濾(SEPA 趨勢模板)
    - id: trend_template_1
      rule: "close > SMA150 and close > SMA200"
      author_value: "股價在 150 與 200 日均線之上"
      params: {}
      source: [minervini_wizard_2013-EX-012]
    - id: rs_rating
      rule: "rs_rating >= P"
      author_value: "RS rating >= 70(理想 80-90)"
      params: {P: {author: 70, test_range: [60, 70, 80, 90]}}   # 測範圍,非單一值
      source: [minervini_wizard_2013-EX-018]
  entry:
    - id: vcp_pivot_breakout
      rule: "breakout above pivot on volume expansion"
      author_value: "突破最後收縮的高點(pivot),量增"
      params:
        contractions_min: {author: 2, test_range: [2, 3, 4]}
        depth_decay: {author: 0.5, test_range: [0.4, 0.5, 0.6]}   # 每次收縮深度 < 前次 × ratio
        vol_dryup_pct: {author: null, test_range: [0.5, 0.7]}     # vague in book -> parameterize
        breakout_vol_mult: {author: 1.5, test_range: [1.2, 1.5, 2.0]}
      source: [minervini_champion_2016-EX-031, ...-EX-034]
  exit: [...]
  sizing: [...]
  regime: [...]
claims:                            # Tier-2,DS-BT 要驗的假設,不是事實
  - "作者稱 SEPA 年化遠超大盤"     # source: ...-EX-002 ; status: to_backtest
anti:
  - "追已延伸(breakout 後追高)"    # source: ...-EX-040
open_questions:                    # 書裡含糊、需靠 test_range 解決的
  - "量縮的精確定義書中未給 -> 用 test_range 掃"
```

### 5b. 散文 `{method}.md`(引用 + 誠實邊界,近法律版模板)

```markdown
# {Method} — 蒸餾
## 1. 一句話核心
## 2. 適用前提(regime / 市場條件)
## 3. 選股過濾(filter)         — 每條 [來源: excerpt_ids]
## 4. 進場規則(entry)
## 5. 出場/停損(exit)
## 6. 部位/風險(sizing)
## 7. 反面教材(anti)
## 8. 作者宣稱 vs 待驗(claims)   — 全部標 Tier-2 / to_backtest
## 9. 含糊處與參數化決定(open_questions)
## 10. 誠實邊界
- spec 為忠實抽取;「有效」未證,見 {method}.backtest.md
- 參數用「待測範圍」非作者單一值,避免擬合其後見之明
```

### 5c. Merge 規則(維度合併,沿用 core-spec §11.2 + finance 加強)

| 情況 | 處理 |
|---|---|
| 兩來源同維度、不矛盾 | 合入同 dimension,追加 source |
| 兩來源同參數、不同值 | **保留兩者為 test_range 的端點**(不選一個) |
| 矛盾規則 | 保留在 `open_questions` / `anti`,不抹平 |
| 新來源揭新維度 | DS5 提請新增 section |
| 作者宣稱績效 | 一律進 `claims`(Tier-2),永不進 rule |

---

## 6. DS4 — Internal Quality Gate(finance 專屬 adversarial 檢查)

沿用 core-spec §7,加金融檢查(fail 就回 DS2/DS3):

| Check | Fail 條件 |
|---|---|
| **可證偽性** | 有 rule 無法轉成機器 predicate(仍是散文) |
| **參數化** | `[量化參數]` 未成 `params` + `test_range`(硬寫死作者單值) |
| **Tier 分離** | 「作者說有效」被寫進 rule / 被當事實 |
| **無倖存者盲信** | synthesis 用作者績效當證據(而非標 to_backtest) |
| **含糊已顯性** | 書中含糊處未進 `open_questions` |
| **引用完整** | 有 assertion 無 excerpt ID(orphan) |

DS4 用**獨立 context**(不與 DS3 共享對話),產出 `runs/{date}/review.md`。Max 3 loop → escalate。

---

## 7. DS-BT — Backtest & Validate(★ 金融版新增 stage,法律版沒有)

**spec 通過 DS4 後,不直接 publish,先回測。** 這對應 Karst 既有工具:

1. 從 `{method}.spec.yaml` 編碼偵測器(filter/entry/exit predicate)。
2. 事件研究鏡子(像 `backtest/exp_insider_validate.py`)+ **long-only 頂層 vs 指數鏡子**
   (像 `exp_family_validate.py` —— 記住 IC/long-short 對 long-only 方法是錯鏡子)。
3. **掃 `test_range`(非作者單值)+ walk-forward + deflated Sharpe**(`backtest/metrics.py`),
   look-ahead-safe(進場用可得時點,如突破當日收盤/次日開盤)。
4. 誠實 caveat:成本/換手/survivorship。
5. 產出 `{method}.backtest.md` + 判決:

| 判決 | 條件 | status |
|---|---|---|
| **validated** | 過 deflated Sharpe(或 long-only 顯著贏指數,穩健於 test_range + 期間)| `validated` |
| **partial** | 某些參數/期間有、某些沒 | `partial`(標明條件)|
| **killed** | 掃遍 range 仍無 edge | `killed`(記錄,別再用)|

> **這一步把「Minervini 說 VCP 賺錢」變成「VCP 在 X 參數、Y 期間、Z 成本下,edge 是/不是真的」。**

---

## 8. DS5 — Storage & Publish

沿用 core-spec §8。finance 加:**publish 前 status 必須反映回測**(`validated`/`partial`/`killed`);
`killed` 的方法**保留作 audit**(記錄「測過、沒 edge」比刪掉有價值 —— 防未來重複踩)。
三件產物齊(散文 / spec / backtest)才算 `published`。

---

## 9. 如何把這變成「可重用的 skill」(給 worker agent 的打包指令)

做一個 Claude Code / Roo skill(`.claude/skills/finance-distill/SKILL.md`),內容 =:

1. **description**:蒸餾任何金融/投資**方法或概念**成「引用散文 + 機器 spec + 回測判決」。觸發:
   「distill this trading method / book / strategy」「把 X 方法變成可回測 spec」。
2. **procedure** = 本檔 DS0 → DS1 → DS2(finance tag set)→ DS3(維度合併 → spec + 散文)→ DS4
   (可證偽/參數化/Tier 分離檢查)→ **DS-BT(回測 test_range + walk-forward + deflated Sharpe)** →
   DS5(依判決 publish)。
3. **鐵律(寫進 skill 頂端)**:
   - 未 tagged 不得 synthesis;未 backtest 不得標 validated。
   - `[量化參數]` → 一律「參數 + 待測範圍」,不硬寫作者單值。
   - 作者宣稱績效 = Tier-2 假設,永不進 rule、永不當證據。
   - long-only 方法用 long-only 鏡子(hold 頂層 vs 指數),不要用 long-short IC 誤判。
   - 勝率是騙子;看期望值 + 尾部 + deflated Sharpe;誠實標 survivorship/成本 caveat。
4. **references**:本檔 + VLOS core-spec(工作流)+ Karst `ARCHITECTURE.md §5`(家族評分/鏡子教訓)+
   `backtest/exp_insider_validate.py`、`exp_family_validate.py`、`metrics.py`(回測工具)。
5. **產物路徑**:`thesis/.raw/`、`thesis/specs/`、`thesis/wiki/`(或 skill 自定 workbench)。

---

## 10. 第一個任務(worker agent 的 Minervini kickoff)

> Domain=`method`,method_slug=`minervini_sepa_vcp`。來源 = Minervini《Trade Like a Stock Market
> Wizard》+《Think & Trade Like a Champion》的 **Trend Template 章 + VCP 章**。走 DS0→DS5:
> 逐條 tagged excerpt(用 §4 的 8 tag)→ 按維度合併成 `minervini_sepa_vcp.spec.yaml`(entry/exit/
> filter/sizing/regime/params/claims/anti,參數帶 test_range)+ 散文 → DS4 檢查 → **DS-BT 用
> Karst 回測(掃 test_range + walk-forward + deflated Sharpe,long-only 鏡子)** → 依判決 publish。
> **不預設 VCP 有效;spec 存在的目的就是誠實地測它到底有沒有 edge。**

---

## 11. 對應原則

| VLOS 原則 | finance 體現 |
|---|---|
| P7 Generic Core | 沿用 VLOS DS0-DS5;本檔只加 finance tag/spec/DS-BT |
| P8 Define Before Execute | DS2 gate → spec → DS4 → **DS-BT** → DS5 |
| P12 Grounded | 每條 rule 連 excerpt ID;每個 param 連來源 + test_range |
| Karst CIO Phase-0 | 方法未過 deflated Sharpe = 未 validated;鏡子要選對(long-only) |
| Karst NHITL | 「有效」由回測數據判,不由作者名氣或人的信念判 |
```
