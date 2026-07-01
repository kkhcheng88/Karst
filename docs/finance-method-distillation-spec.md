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

**清楚的分工(重要):蒸餾 skill 只負責到「產出 spec」,回測是 Karst 另一步(不在 skill 內)。**

```
[蒸餾 skill = Maker]                      [Karst 回測 = Checker,分開做]
raw → verified → tagged → synthesized  ─交棒→  backtested → (validated | killed | partial)
```

- **skill 擁有 `raw → synthesized`**:產出一個乾淨、引用完整、參數化(帶 test_range)、**ready-to-
  backtest** 的 spec,`claim_status: unverified`,**到此結束、交棒**。
- **Karst(我)擁有 `synthesized → validated`**:拿 spec 去回測(§7 是交棒說明,非 skill 的 stage)。
- **未回測的方法,永遠只是 `synthesized`,不得當「有效」使用。** 這對應 `ARCHITECTURE.md §5`
  (勝率是騙子、發表即衰減、long-only ≠ long-short 鏡子)。這是 VLOS Maker/Checker 分離的金融版。

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

## 7. 交棒:回測(★ 不在 skill 內 —— 由 Karst 做)

**skill 到 §6 就結束(產出 `synthesized` 的 spec)。回測是分開的一步,由 Karst(主系統)執行**,
用既有工具,不用 worker agent 重造:

1. 從 `{method}.spec.yaml` 編碼偵測器(filter/entry/exit predicate)。
2. 事件研究鏡子(`backtest/exp_insider_validate.py`)+ **long-only 頂層 vs 指數鏡子**
   (`exp_family_validate.py` —— IC/long-short 對 long-only 方法是錯鏡子)。
3. 掃 `test_range`(非作者單值)+ walk-forward + deflated Sharpe(`backtest/metrics.py`),look-ahead-safe。
4. 誠實 caveat(成本/換手/survivorship),判決 validated / partial / killed,寫回 spec 的 `claim_status`。

> skill 交出的 spec **已經是 ready-to-backtest**(參數帶 range、規則已 predicate 化),所以這步是 Karst
> 直接接手,不需要 worker agent 參與。

---

## 8. Skill 收尾 —— 存檔就好(**沒有 VLOS 那套 publish 機制**)

我們**沒有** domain-master 再生、HITL-2 approval、agent 消費規則那套(VLOS 專屬 infra)。所以 skill 的
收尾很簡單:**把三個 working 產物存好、標 status,結束**:

| 產物 | 路徑 | status |
|---|---|---|
| tagged excerpts | `excerpts/{source_slug}_excerpts.md` | — |
| 機器 spec | `{method}.spec.yaml` | `synthesized`(claim_status: unverified)|
| 散文 | `{method}.md` | — |

`runs/{date}/` 保留 DS3/DS4 記錄作 audit。**就這樣** —— 不 publish、不 regenerate master、不 HITL。
回測後 Karst 才把 `claim_status` 改成 validated/killed(那不是 skill 的事)。

---

## 9. 如何把這變成「可重用的 skill」(給 worker agent 的打包指令)

做一個 Claude Code / Roo skill(`.claude/skills/finance-distill/SKILL.md`),內容 =:

1. **description**:蒸餾任何金融/投資**方法或概念**成「引用散文 + ready-to-backtest 機器 spec」。觸發:
   「distill this trading method / book / strategy」「把 X 方法變成可回測 spec」。
2. **procedure(就這 4 步,不含回測/publish)** = 本檔 **DS0 → DS1 → DS2(finance tag set)→ DS3
   (維度合併 → spec + 散文)→ DS4(可證偽/參數化/Tier 分離自檢)→ 存檔(§8)**。**結束。**
   回測與 validated 判定**不是這個 skill 的事**(見 §7,Karst 做)。
3. **鐵律(寫進 skill 頂端)**:
   - 未 tagged 不得 synthesis。
   - `[量化參數]` → 一律「參數 + 待測範圍」,不硬寫作者單值。
   - 作者宣稱績效 = Tier-2 假設,永不進 rule、永不當證據;spec 一律 `claim_status: unverified`。
   - spec 交出去時就是 ready-to-backtest(規則已 predicate 化、參數帶 range);**不預設方法有效。**
4. **references**:本檔 + VLOS core-spec(通用 DS0-DS5 工作流,直接沿用)。
5. **產物路徑**:`thesis/.raw/`、`thesis/specs/`、`thesis/wiki/`(或 skill 自定 workbench)。

> **範圍界線:skill = 純蒸餾(Maker)。它交出乾淨、量化、可回測的 spec 就完成任務,不證明它有效。**

---

## 10. 第一個任務(worker agent 的 Minervini kickoff)

> Domain=`method`,method_slug=`minervini_sepa_vcp`。來源 = Minervini《Trade Like a Stock Market
> Wizard》+《Think & Trade Like a Champion》的 **Trend Template 章 + VCP 章**。走 **DS0→DS4 + 存檔**:
> 逐條 tagged excerpt(用 §4 的 8 tag)→ 按維度合併成 `minervini_sepa_vcp.spec.yaml`(entry/exit/
> filter/sizing/regime/params/claims/anti,**參數帶 test_range**)+ 散文 → DS4 自檢 → 存檔,
> status=`synthesized`。**交棒。** 回測由 Karst 另跑(§7)。
> **不預設 VCP 有效;你的任務是交出一個乾淨、可回測的 spec,不是證明它賺錢。**

---

## 11. 對應原則

| VLOS 原則 | finance 體現 |
|---|---|
| P7 Generic Core | 沿用 VLOS DS0-DS5;本檔只加 finance tag set + 機器 spec 產物 |
| P8 Define Before Execute | DS2 tagged gate → DS3 spec → DS4 自檢 → 存檔(skill 到此) |
| P9 Maker/Checker 分離 | **distiller skill = Maker(產 spec);Karst 回測 = Checker(驗 edge)** |
| P12 Grounded | 每條 rule 連 excerpt ID;每個 param 連來源 + test_range |
| Karst CIO Phase-0 | spec 交出=`synthesized`;過 deflated Sharpe 才 `validated`(Karst 判,鏡子選對)|
| Karst NHITL | 「有效」由回測數據判,不由作者名氣或人的信念判 |
```
