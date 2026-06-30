# Lenses — 基本面 / 護城河鏡片

> 定位:**Layer-3 衛星選股 + 防守宇宙篩選**。不是 alpha,是「誰有資格進場」。
> 證據標準與 backtest 不同——lenses 的驗證機制是 Tree 的隨時間 scoring + 前瞻
> track record,不是 41,000 次回測。

---

## 蒸餾原則:可證偽的可檢查 criteria,不是 LLM 人格扮演

對應「method → scriptify,domain → LLM」:

- **可量化部分 → scriptify 成 screen:** ROIC / FCF 趨勢、Piotroski F-score、
  Lynch PEG < 1、owner earnings。
- **護城河耐久性判斷 → LLM overlay:** 輸出一個**餵進 Tree 的 falsifiable verdict**
  (帶 kill condition),不是 vibes。

⚠️ `virattt/ai-hedge-fund` 之類 repo 本質是 LLM 角色扮演——當鷹架可以,當真理
來源不行。**蒸餾真正的書 > 蒸餾現成 persona repo。**

---

## School Mismatch(重要)

Compass 封存的 8 個 value agents(Buffett / Graham / Klarman / Greenblatt …)幾乎全是
**deep value**。但 Karst 的衛星是 **bottleneck 小市值高成長**(idea-02,10x/100x)。
這是相反學派。對「財報日 +44%」那種標的,cigar-butt 框架是錯的工具。

**衛星正確 lens 組合 = 成長動能(進場/RS/trend)+ 護城河耐久性(bottleneck 真偽)
+ 成長分類。**

---

## 蒸餾順序(書都已在 `../../ebooks/`,零採購)

| 順序 | 書 | 用途 | 對應層 |
|---|---|---|---|
| 1 | **Pat Dorsey《The Little Book That Builds Wealth》** | 四種護城河來源 → 驗證 bottleneck 真偽 | 防守 + thesis 驗證 |
| 1 | **Michael Porter《Competitive Advantage》** | 進入障礙(學術地基)| 同上 |
| 2 | **Mark Minervini 股票魔法師 I–IV** | Trend Template / VCP → 編碼成 timing 規則 | Layer-2(非新方法,是規則化)|
| 3 | **Peter Lynch《One Up》《Beating the Street》** | fast grower 分類 | 衛星選股 |

> Dorsey / Porter 不只做防守 lens——idea-02 說「bottleneck 價值取決於替代方案不存在」,
> 這逐字就是 Porter barriers to entry / Dorsey moat。它們是衛星 thesis 的證偽器。

---

## 蒸餾格式:照 Mark Douglas pipeline

`../../ebooks/.../Mark Douglas/` 已有一條完整 book→agent pipeline,照它走,別重發明:

```
01-writings → 02-interviews → tagged-excerpts.md
  → primitives-draft.md → agent-spec-draft.md → validation-report.md
  + specialization.yaml
```

每個 lens 最終輸出:一組 **可檢查 criteria(scriptify)+ LLM 判斷項(domain)**,
每條帶 kill condition,直接接進 Tree。

---

## Open Items

- [ ] 蒸餾 Dorsey → moat criteria(最高槓桿,先做)
- [ ] 蒸餾 Minervini Trend Template → Layer-2 編碼規則
- [ ] 蒸餾 Lynch → 衛星成長分類
- [ ] 升級 Compass `lenses/`(Lynch/Marks/Munger)或遷移到此
