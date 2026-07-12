---
slug: euv-lithography-monopoly
type: B
cycle_stage: late
confidence: 0.22
verdict: real-monopoly-but-most-priced-in
updated: 2026-07-11
tickers: ['ASML']
---

<!-- frontmatter = valid-YAML scalars only, tickers quoted。wiki-links 一律 INLINE 放內文;每條 claim
     inline 引用來源。切勿把 [[wiki-links]] 放進 YAML frontmatter(會斷 parser)。 -->

# EUV 微影全球唯一供應商(B 型)— 最乾淨嘅結構故事,但最人盡皆知

> **2026-07-11 discovery radar 全市場逐隻驗證新增**,transcript-only 一手源(唔係 gooptions/IMA)。
> 未做 capital-allocation/ROIC/TAM 深度研究。詳細證據見
> `backtest/results/2026-07-11_discovery_radar_review_groupB.md`。

## 一句話(核心張力 = thesis 本身)
[[ASML]] 係全球唯一 EUV 微影設備供應商,零替代品。16 年橫跨 4 個景氣週期(2010 DRAM 榮景/2017記憶體
上升期/2021晶片荒/2026 AI驅動記憶體+邏輯建設)一致用第一人稱講「我哋刻意 constrain 個生意」「12-24個月
訂單lead time」「客戶 sold out」。**呢個係全批 discovery radar 40 候選入面最長、最一致嘅結構故事**,
但同時亦係全市場最多人討論嘅半導體壟斷故事——「未被發現」嘅溢價完全唔存在,ttm_pe 3年滾動分位 98th
(2026-07-11量度)。真.壟斷,但買入時機唔平,而且冇「未被發現」加分(對比 aerospace-specialty-alloys
起碼仲係相對冷門嘅利基)。

## ticker 層
| ticker | 角色 | 可交易 | 估值(Tier-1,2026-07-11) | conviction 含義 |
|---|---|---|---|---|
| [[ASML]] | 全球唯一 EUV 微影設備供應商 | ✅ US(Nasdaq) | ttm_pe ~59.9x,3年滾動 **98th pctile** | 最乾淨結構故事,但最擠 |
| ASMLF | 同一間公司,OTC ADR | 唔用(流動性差過ASML) | — | thesis 只用 ASML 一個 ticker |

## 證據(verbatim,節錄;全文見 group B 報告)
- 2010-01-20(CEO Eric Meurice):*"we are always constraining the business because our lead times are
  so enormous."*
- 2019-07-17:*"there is an order lead time which we give our customers about 18 months."*
- 2026-01-28(CFO Dassen):*"long lead time items...longer than 12, 18 months to realize."*
- 2026-04-15(最新):*"what our customers tell us is that they are sold out for 2026 and their supply
  constraint will last beyond 2026."*

## confidence 推導
```
全批最長最一致嘅結構故事(16年、4個週期、零替代品) 但 ttm_pe 98th pctile + 全市場最人盡皆知嘅
半導體壟斷故事之一(「未被發現」溢價完全唔存在)
= 同 aerospace-specialty-alloys 近似級別,但少咗「相對冷門利基」嘅加分 -> 略低
-> confidence ≈ 0.22
```

## kill_condition(可證偽)
> 有可行 EUV/High-NA EUV 競爭者出現(中國本土突破如 SMEE、或 Canon/Nikon 重返 High-NA)打破唯一供應商
> 結構 **或** AI驅動先進製程資本開支增長停滯/逆轉(TSMC/三星/Intel capex guidance回落) **或** 訂單
> backlog/lead time 回復返 2019 年前水平(12-24個月縮到 <6個月)。觸發 -> confidence 歸零。

## 2026-07-12 update:補接 [[ai-capex-macro-risk]] cross-link(原文遺漏)
- [[ai-capex-macro-risk]]:本頁 kill_condition 第二腳「AI驅動先進製程資本開支增長停滯/逆轉」應對照該頁
  五盞燈——ASML 客戶係 TSMC/三星/Intel 等晶圓廠,唔係雲端四大本身,故傳導有一層延遲:雲端 capex 打嗝要
  先傳到晶圓代工 capex guidance,先輪到 ASML 訂單。最直接相關嘅兩盞燈係「四大 FCF 軌跡」(領先指標)
  同「承諾-run-rate 缺口」(擴散速度);若兩盞燈持續轉偏空兩季以上,應提前重新評估本頁 confidence,
  唔使等 TSMC/三星自己 capex guidance 落實先反應。

## 待補
- [ ] Capital-allocation/ROIC 分析
- [ ] TAM sizing(先進製程 capex 未來5年展望)
- [ ] 窄 ETF 搜尋(未搜,ASML 本身已係大部分半導體設備 ETF 最大持股,窄化意義存疑)
- [ ] 第三方分析師報告交叉驗證

## 來源
Tier-3(transcript-discovery-radar):`thesis/corpus.db` FTS5 全文搜索,`backtest/results/
2026-07-11_discovery_radar_review_groupB.md` 逐隻人手驗證(2006-2026 分層取樣,±220字context)。
