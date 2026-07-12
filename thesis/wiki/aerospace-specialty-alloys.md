---
slug: aerospace-specialty-alloys
type: B
cycle_stage: late
confidence: 0.24
verdict: real-moat-but-fully-priced
updated: 2026-07-11
tickers: ['ATI', 'CRS']
---

<!-- frontmatter = valid-YAML scalars only, tickers quoted。wiki-links 一律 INLINE 放內文;每條 claim
     inline 引用來源。切勿把 [[wiki-links]] 放進 YAML frontmatter(會斷 parser)。 -->

# 航太噴射引擎特種合金(B 型)— 真.LTA 鎖客護城河,但已極度 priced-in

> **2026-07-11 discovery radar 全市場逐隻驗證新增**,同原有 9 個 thesis 唔同來源結構:呢個純粹係
> [[ATI]]/[[CRS]] 自己 earnings call transcript 一手逐字引句(`thesis/corpus.db`),唔係 gooptions/IMA
> 第三方報告篩選出嚟。**未做完整 capital-allocation/ROIC/TAM 深度研究(同原有 9 個 thesis 唔同深度)**,
> confidence 相應保守。詳細證據 + 覆核紀錄見 `backtest/results/2026-07-11_discovery_radar_review_groupA.md`。

## 一句話(核心張力 = thesis 本身)
[[ATI]](19年)同 [[CRS]](15年)嘅 earnings call 一路第一人稱講緊噴射引擎鎳基高溫合金/鈦合金**產能約束
+ 客戶認證鎖客(qualification lock-in)+ 多年期 LTA 合約結構**——ATI 自己講「供應 6/7 款最先進噴射引擎
鎳合金」,CRS 客戶要重新認證先可以轉供應商。2026 年最新一季雙雙確認故事仲 live。**但呢個結構已經被市場
發現**:ttm_pe 3年滾動分位兩隻都係 98th(2026-07-11 量度),discovery radar 40 候選入面估值最貴嘅之一。
真.護城河,但買入時機唔平。

## ticker 層
| ticker | 角色 | 可交易 | 估值(Tier-1,2026-07-11) | conviction 含義 |
|---|---|---|---|---|
| [[ATI]] | 鈦/鎳超合金,供應 6/7 款最先進噴射引擎鎳合金 | ✅ US | ttm_pe ~61.7x,3年滾動 **98th pctile** | 真結構性樽頸,但已極貴 |
| [[CRS]] | 特種合金,客戶認證鎖定 + LTA 議價 | ✅ US | ttm_pe ~60.9x,3年滾動 **98th pctile** | 同 ATI 同一機制,合併做一個 thesis |

## 證據(verbatim,節錄;全文見 group A 報告)
- ATI 2026-04-30:*"lead times are extending for our most differentiated products, super alloy nickels...
  This is not short-cycle demand. It is tied to long-term contracts..."* / *"We supply 6 of the 7 most
  advanced jet engine nickel alloys."*
- ATI 2023-08-02:*"we've secured over $1.2 billion in new commitments"*(LTA)。
- CRS 2026-04-29:*"customers are prioritizing security of supply, and we are continuing to realize
  pricing that reflects the value we deliver"* / *"you guys are kind of 24/7 full out."*
- CRS 2018-10-24:*"Our customers recognize the urgency to qualify additional capacity..."*(認證鎖客)。

## confidence 推導
```
真結構性樽頸(LTA鎖客+具名產品護城河,19/15年一致) 但 ttm_pe 98th pctile(全批最貴之二)
= 類近 photonics-optical(0.30,真瓶頸但最擠)/ advanced-packaging(0.32) 嘅處境,
  但呢批係 transcript-only 一手源、未做 capital-allocation/ROIC/TAM 深度研究 -> 額外保守
-> confidence ≈ 0.24
```

## kill_condition(可證偽)
> 噴射引擎 OEM(Boeing/Airbus/GE/RTX/Safran)build-rate guidance 回落,或 LTA 新簽/backlog 成長停滯
> (ATI 式 $1.2bn 新承諾唔再出現)**或** 有競爭者(PCC/Special Metals/VDM Metals/Aperam)帶新產能上線,
> 削弱「6/7 most advanced」稀缺性 **或** 估值喺基本因素冇進一步確認下持續擴張(純 multiple 驅動)。
> 觸發 -> confidence 歸零。

## 待補
- [ ] Capital-allocation/ROIC 分析(呢個 thesis 未做,同原有 9 個 thesis 深度唔同)
- [ ] TAM sizing(噴射引擎 build-rate 未來5年展望)
- [ ] 窄 ETF 搜尋(未搜)
- [ ] 第三方分析師報告交叉驗證(現時純 transcript 一手源)

## 來源
Tier-3(transcript-discovery-radar):`thesis/corpus.db` FTS5 全文搜索,`backtest/results/
2026-07-11_discovery_radar_review_groupA.md` 逐隻人手驗證(2007-2026 分層取樣,±260字context)。
