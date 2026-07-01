# Finance Method Distillation — Skill Specification

把任何金融/投資的**方法**(交易/選股系統:突破、mean-reversion、factor 過濾…)或**概念/框架**
(VRP、regime、factor 理論、估值…)從來源材料(書、課程、論文、KOL、逐字稿)蒸餾成:

1. **可審計的 tagged excerpts**(每條主張都有原文引用),
2. **引用完整的散文 synthesis**,
3. **ready-to-backtest 的機器 spec**(規則 → predicate + 具名參數 + 待測範圍)。

**這個 skill 是純蒸餾(Maker)。它不做回測、不判斷方法是否有效** —— 它交出一個乾淨、量化、可回測的
spec 就完成任務。是否有 edge,由後續獨立的回測回答。

---

## 1. 核心紀律(不可妥協)

1. **未 tagged 不得 synthesis;未記理由不得例外。** 防止「跳過原文直接寫結論」「用 summary 代替 tagging」
   「把單一 excerpt 過度泛化成通則」。
2. **方法 spec 忠實於來源(一手:「方法是什麼」);「它賺錢」是待驗假設(Tier-2:unverified)** ——
   永不採信、永不寫進 rule。作者的績效/勝率一律進 `claims`,標 `to_backtest`。
3. **量化參數一律「參數 + 待測範圍」,不硬寫作者單一值**(避免擬合他的後見之明)。作者含糊處
   → 顯性化成 `open_questions` + test_range。
4. **每條主張連 excerpt ID;保留矛盾;標明適用範圍與邊界。**
5. **勝率是騙子** —— 蒸餾時不因「作者說勝率 90%」而升級 confidence;那只是待驗的 claim。

---

## 2. 產物(三件,缺一不可)

| 產物 | 內容 | status |
|---|---|---|
| `excerpts/{source_slug}_excerpts.md` | 每份來源的 tagged excerpts | — |
| `{method}.spec.yaml` | 機器 spec:predicate + 參數 + test_range | `synthesized`,`claim_status: unverified` |
| `{method}.md` | 散文 synthesis(引用 excerpt IDs)| — |

`runs/{date}/` 保留 synthesis/self-check 記錄作 audit(不可變)。

---

## 3. 工作流(DS0 → DS4 → 存檔)

```
DS0 收料 → DS1 驗證 → DS2 逐份 tagged excerpt → DS3 按維度合併成 spec + 散文 → DS4 自檢 → 存檔
```

skill 到「存檔」結束。回測是另一步(見 §10),不在此 skill 內。

---

## 4. Domains

| Domain | 用途 | 主要產物 |
|---|---|---|
| **`method`** | 系統化交易/選股技術 | 機器 spec + 散文(可回測)|
| **`concept`** | 框架/理論(非直接可交易)| 散文 synthesis(可量化部分才進 spec)|
| **`playbook`** | 情境戰術(危機劇本、財報前後、sizing 紀律)| 條件式規則 + 觸發 |

同一本書可跨 domain 重蒸(用不同 tag set,產出不同 synthesis)。

---

## 5. Workbench 結構

```
knowledge/{domain}/{method}/
├── sources/{source_slug}.md              # DS0-DS1:來源 + front matter
├── excerpts/{source_slug}_excerpts.md    # DS2:每份來源一個 excerpt file
├── runs/{date}/                          # DS3-DS4:不可變記錄
│   ├── {method}_draft.md
│   └── review.md
├── {method}.md                           # 散文 synthesis
└── {method}.spec.yaml                    # 機器 spec(ready-to-backtest)
```

實作可自定 workbench 路徑,但**三件產物 + audit 記錄**的結構不變。

---

## 6. DS0-DS1 — 收料與驗證

每份來源建一個 `sources/{source_slug}.md`,front matter:

```yaml
---
title: "{Book / Course / Paper / KOL thread}"
author: "{Author}"
type: book | course | paper | kol | filing | transcript   # 媒介
tier: 1 | 2 | 3            # 1=一手(逐字稿/filing/價格);2=方法書/報告/KOL(意見);3=新聞
claim_status: unverified   # 作者對「有效」的宣稱,恆為 unverified
edition: "{2nd ed 2016}"
ingested_at: YYYY-MM-DD
verified: true | false
reliability: primary | secondary | inferred | questionable
notes: "..."
---
```

**DS0**:定義來源範圍——哪些材料納入、由誰提供、哪些缺失/排除(排除須記理由)。
**DS1**:確認 authenticity / relevance / completeness / temporal-validity;`verified: true` 才能進 DS2。
方法書通常 `type: book, tier: 2`(方法可信=一手技術,但「賺錢」是 Tier-2 待驗)。

---

## 7. DS2 — Tagged Excerpts

**每份 verified source 產生一個 excerpt file,含 ≥1 個 tagged excerpt。** 無相關內容時記 exception
(`duplicate` / `irrelevant_with_reason` / `unreadable` / `not_obtainable`)。

### Excerpt 格式

```markdown
### 🏷️ [Tag] — ID: {source_slug}-EX-{NNN}
- **原文摘錄 (Canonical Quote):** 照錄,不 paraphrase
  > "..."
- **支持的主張 (Assertion):** 此摘錄支持什麼可重用命題
- **適用場景 (Scope):**
- **不支持什麼 (Boundary):** 不可如何延伸
- **失效條件 (Failure Conditions):** 何時不適用 / 有無矛盾
- **審計:** Source / Confidence(High|Med|Low)/ Date
```

> Low-confidence 或單一 insight 可用 Light 模式(只 Quote + Assertion + Tag),標 `[Light]`。

### Tag Set(8 個,不得自創;不 fit 就 flag)

| Tag | 用途 | → spec 維度 |
|---|---|---|
| `[進場規則]` | 何時買/觸發 | entry |
| `[出場/停損]` | 何時賣/停損/移動停利 | exit |
| `[選股/過濾]` | 哪些標的合格(趨勢模板、RS、流動性) | filter |
| `[部位管理]` | sizing、加減碼、風險上限、集中度 | sizing |
| `[市場前提/regime]` | 大盤/regime 條件 | regime |
| `[量化參數]` | 具體數字(照錄原值) | params |
| `[作者宣稱-未證]` | 作者聲稱的績效/勝率 —— 待驗,不採信 | claims(Tier-2)|
| `[反面教材]` | 不要做的事、常見錯誤、失效條件 | anti |

規則:quotes 照錄;`[量化參數]` 必照錄原文數字;含糊處(「量要明顯縮」)標 assertion「vague → 待參數化」。

---

## 8. DS3 — 按維度合併 → spec + 散文

**維度 = tag 對應的 spec section**(entry / exit / filter / sizing / regime / params / claims / anti)。
DS3 讀**全部** excerpt files,按維度歸併,每條 assertion 引用 excerpt IDs。

### 8a. 機器 spec `{method}.spec.yaml`

```yaml
method: "{method_slug}"
version: "1.0"
sources: ["{source_slug}", ...]
claim_status: unverified
dimensions:
  filter:
    - id: "{rule_id}"
      rule: "close > SMA150 and SMA150 > SMA200"   # 可機器檢查的 predicate
      author_value: "股價在 150/200 日均線之上"       # 原文描述
      params: {}
      source: ["{source_slug}-EX-012"]
  entry:
    - id: "{rule_id}"
      rule: "breakout above pivot on volume expansion"
      author_value: "突破最後收縮高點,量增"
      params:
        contractions_min: {author: 2, test_range: [2, 3, 4]}      # 掃範圍,非單一值
        vol_dryup_pct:    {author: null, test_range: [0.5, 0.7]}  # 書中含糊 -> 參數化
        breakout_vol_mult:{author: 1.5, test_range: [1.2, 1.5, 2.0]}
      source: ["{source_slug}-EX-031"]
  exit: [...]
  sizing: [...]
  regime: [...]
claims:                       # Tier-2,待回測驗;不是事實
  - {text: "作者稱年化遠超大盤", source: ["...-EX-002"], status: to_backtest}
anti:
  - {text: "追已延伸(突破後追高)", source: ["...-EX-040"]}
open_questions:               # 含糊/需靠 test_range 解決
  - "量縮精確定義書中未給 -> test_range 掃"
```

### 8b. 散文 `{method}.md`

```markdown
# {Method} — 蒸餾
## 1. 一句話核心
## 2. 適用前提(regime / 市場條件)
## 3. 選股過濾(filter)        — 每條 [來源: excerpt_ids]
## 4. 進場規則(entry)
## 5. 出場/停損(exit)
## 6. 部位/風險(sizing)
## 7. 反面教材(anti)
## 8. 作者宣稱 vs 待驗(claims) — 全部 Tier-2 / to_backtest
## 9. 含糊處與參數化決定(open_questions)
## 10. 誠實邊界
- spec 為忠實抽取;「有效」未證(claim_status: unverified)
- 參數用「待測範圍」非作者單一值
```

### 8c. 合併規則

| 情況 | 處理 |
|---|---|
| 兩來源同維度、不矛盾 | 合入同 dimension,追加 source |
| 兩來源同參數、不同值 | **保留兩值為 test_range 端點**(不選一個) |
| 矛盾規則 | 保留在 `open_questions` / `anti`,不抹平 |
| 新來源揭新維度 | 新增 section,標明來源 |
| 作者宣稱績效 | 一律進 `claims`(Tier-2),永不進 rule |

---

## 9. DS4 — 自檢 Gate(通過才存檔;fail 回 DS2/DS3,max 3 loop)

| 檢查 | Fail 條件 |
|---|---|
| 覆蓋 | 有 verified source 無 excerpt 也無 exception |
| Quote 照錄 | 有 paraphrase 冒充原文 |
| Tag 合規 | 用了 8 個以外的 tag |
| 可證偽性 | 有 rule 無法轉成機器 predicate(仍是散文) |
| 參數化 | `[量化參數]` 未成 `params` + `test_range`(硬寫死作者單值) |
| Tier 分離 | 「作者說有效」被寫進 rule / 當事實 |
| 含糊顯性 | 書中含糊處未進 `open_questions` |
| 引用完整 | 有 assertion 無 excerpt ID(orphan) |
| 邊界 | excerpt 未記 boundary / failure conditions |

DS4 用獨立 context(不與 DS3 共享對話),產出 `runs/{date}/review.md`。

---

## 10. 存檔 + 交棒

- 存三件產物 + `runs/{date}/`;spec 標 `status: synthesized`、`claim_status: unverified`。
- **skill 到此結束。**
- **交棒:回測是另一步(不在此 skill)。** spec 交出時已 ready-to-backtest(規則 predicate 化、參數帶
  range),由回測系統接手:編碼偵測器 → 掃 `test_range` + walk-forward + deflated Sharpe →
  誠實 caveat(成本/換手/survivorship)→ 判 validated / partial / killed → 寫回 `claim_status`。
- **鏡子要選對:long-only 方法(如突破/選股)用「持有頂層 vs 指數」的 long-only 鏡子,不要用
  long-short IC 誤判。** 回測完成前,方法恆為 `synthesized`,不得當「有效」使用。

---

## 11. 參考範例(僅示意 spec 產出長相,非任務)

以 Minervini SEPA/VCP(突破選股法)為例,DS3 產出的 `spec.yaml` 片段會像:

```yaml
method: "minervini_sepa_vcp"
dimensions:
  filter:                                   # SEPA 趨勢模板
    - id: trend_stack
      rule: "close>SMA50 and SMA50>SMA150 and SMA150>SMA200 and slope(SMA200,20)>0"
      author_value: "股價 > 50/150/200MA 且 200MA 上升"
      source: ["wizard_2013-EX-012"]
    - id: rs_rating
      rule: "rs_rating >= P"
      params: {P: {author: 70, test_range: [60,70,80,90]}}
      source: ["wizard_2013-EX-018"]
  entry:                                    # VCP pivot 突破
    - id: vcp_breakout
      rule: "breakout(pivot) and volume > breakout_vol_mult * avg_vol(50)"
      params:
        contractions_min: {author: 2, test_range: [2,3]}
        depth_decay:      {author: 0.5, test_range: [0.4,0.5,0.6]}
        breakout_vol_mult:{author: 1.5, test_range: [1.2,1.5,2.0]}
      source: ["champion_2016-EX-031","champion_2016-EX-034"]
claims:
  - {text: "SEPA 年化遠超大盤", source: ["wizard_2013-EX-002"], status: to_backtest}
anti:
  - {text: "追已延伸的突破", source: ["champion_2016-EX-040"]}
open_questions:
  - "量縮的精確門檻書中未給 -> 用 vol_dryup test_range 掃"
```

重點示意:趨勢模板 → `filter`;VCP → `entry`;作者績效 → `claims`(待驗);含糊 → `open_questions` +
test_range。**交出這樣一個 spec 就完成 skill 的任務。**
