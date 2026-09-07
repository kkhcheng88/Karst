# knowledge/ —— 成功交易者與投資書的蒸餾知識庫

> 2026-09-07 建(D-165 暫停期研究線;D-166 四類注為對照骨架)。這個目錄放**別人的心得經我們對照過的版本**,不放原書、不放原始貼文(原件留在 `C:\projects\Investment\`,這裡只放連結與頁碼)。用戶 2026-09-07 原話:「all voice can be a good reference it is only a matter of how we manage ourselves, but all the expert voice should be weighted」「Properly manage these distilled knowledge in our repo to be reusable」。

## 一、目錄

```
knowledge/
  README.md            本檔:結構、權重規矩、檔案格式
  INDEX.md             全部來源一覽表(來源、類型、權重四格、對應類注、狀態),由蒸餾檔頭部欄位彙整
  reference-list.md    待蒸餾名單(擴充版),含往績可查度、材料位置、優先次序、狀態
  books/<slug>.md      一本書一檔
  traders/<slug>.md    一位交易者一檔(跨書、跨訪談、跨貼文合併;書中某位受訪者若獨立成檔亦放此)
  communities/<slug>.md 社群存檔(如 royalflush Discord)一檔
  social/<handle>.md   社交帳號一檔
  insights/<topic>.md  跨來源合成的主題結論,按四類注的問題分檔(見 §四);每條結論列出支持與反對的來源
```

**規矩**:`books/`、`traders/`、`communities/`、`social/` 是**來源層**,只記那個來源講了什麼、我們怎樣對照;`insights/` 是**結論層**,只由來源層引用而來,不准出現沒有來源的主張。策略票引用知識庫時引 `insights/`,追溯時才落到來源層。

## 二、來源權重四格(每個來源檔頭部必填)

用戶 2026-09-07 定「all the expert voice should be weighted」。四格各給 高/中/低,並一句理由:

| 格 | 問的是 | 高 | 低 |
|---|---|---|---|
| `era` 時代 | 樣本年代與今日市場結構是否相近 | 2010 年後、有未盈利敘事股的年代 | 1990 年前 |
| `horizon` 持有期 | 與用戶「數週至數季」是否對得上 | 波段、事件驅動 | 以年計的長持,或即日 |
| `practised` 親身做過 | 對所講的那類注,他是做過還是旁觀 | 有對帳單/審計往績做過該類 | 旁觀者判斷、拒收該類 |
| `capital` 資本規模 | 約束是否與散戶相似 | 散戶起家、小型集中基金 | 大型基金、有交易台與期權工具 |

**用法**:同一條問題有多個來源意見相左時,先看四格再定信誰;四格皆低的來源只作背景,不入 `insights/` 的結論句。大資本來源(Soros、Druckenmiller、Buffett 一類)的**框架**(定價、護城河、週期)不受 `capital` 格折減,**戰術**(注碼、進出、對沖)受折減。

## 三、來源檔格式

```markdown
---
name: <slug>
type: book | trader | community | social
title: <書名 / 人名 / 社群名>
source_path: <原件位置或 URL>
era: <年代範圍>
market: US | HK | 多市場
weights: {era: 高|中|低, horizon: 高|中|低, practised: 高|中|低, capital: 高|中|低}
weights_note: <一句理由>
categories: [①, ②, ③, ④, 事件窗, 治理]   # 對哪幾類注有話講
verified_record: <往績可查度:審計/對帳單/13F/無>
status: distilled | partial | pending
distilled_on: YYYY-MM-DD
distilled_by: <模型>
---

## 一、一句核心主張
## 二、心得逐條(引述 + 頁碼或日期 + 對應類注/問題 + 一句歸類)
## 三、與用戶框架衝突處(直說,附理由)
## 四、可入候選登記表的項目(五格:聲稱/服務哪類/文獻/延遲成本/證偽條件)
## 五、蒸餾員一句判斷
```

## 四、insights/ 的分檔(按四類注要答的問題,見 `research/2026-09-06-方法論候選登記表.md` §零)

- `sizing-and-exit.md` 注碼與離場治理(所有來源最一致的一半;D-166 框架未寫的一半)
- `consensus-gauge.md` 敘事共識度量:市場知不知道、飽和了沒有
- `pricing-position.md` 定價位置:市場已為故事付了多少
- `moat-durability.md` 護城河能否持續、敘事會否成真
- `forced-selling.md` 錯殺成因:誰在非因生意而賣
- `event-window-price-action.md` 事件窗價格行為:機構怎樣吸貨與派貨
- `category-transitions.md` 換類:④→③→②→① 的觸發與標記
- `where-the-money-lands.md` 敘事成真時錢落在主角還是瓶頸(Porter/Aschenbrenner 對④的挑戰)
- `conflicts-with-framework.md` 所有來源對 D-166 框架的反對意見彙整,連我們的回應

每條結論格式:`結論句 —— 支持:[來源A p.x][來源B]; 反對:[來源C]; 權重判定:一句`。

## 五、與其他檔的關係

- 原件與前人蒸餾:`C:\projects\Investment\ebooks\`(內有動能派可回測規則蒸餾 `Discretionary Momentum/DISTILLATION-backtestable-rules.md` 與 Mark Douglas/Tom Hougaard 六維整理,**不重做,只引用**;該檔第零節記有書庫檔案錯置,引用前先看)。
- 候選登記表:`research/2026-09-06-方法論候選登記表.md`,來源檔第四節的項目最終要併進去。
- 框架正本:`research/2026-09-06-用戶投資框架四類注.md`(D-166)。
- 詞彙:`CONTEXT.md`「四類注 / 敘事 / 事件窗價格行為 / 來源權重四格」。
