---
slug: specialty-siding-pricing-power
type: B
cycle_stage: mid
confidence: 0.20
verdict: real-segment-mix-shift-but-diluted-and-priced
updated: 2026-07-11
tickers: ['LPX']
---

<!-- frontmatter = valid-YAML scalars only, tickers quoted。wiki-links 一律 INLINE 放內文;每條 claim
     inline 引用來源。切勿把 [[wiki-links]] 放進 YAML frontmatter(會斷 parser)。 -->

# LP SmartSide/ExpertFinish 特種護牆板(B 型)— 真但薄:segment故事 vs whole-company估值

> **2026-07-11 discovery radar 全市場逐隻驗證新增**,transcript-only 一手源。未做 capital-allocation/
> ROIC/TAM 深度研究。詳細證據見 `backtest/results/2026-07-11_discovery_radar_review_groupD.md`。

## 一句話(核心張力 = thesis 本身)
[[LPX]] 有兩盤生意方向相反——commodity OSB 而家疲弱(2026年最新季度 EBITDA 蝕錢),但 SmartSide/
ExpertFinish 特種護牆板持續講 pricing power(近9季有7季提及,2024年開始),而且 2026-05-06 嗰季確認
ExpertFinish 實際喺 managed-allocation order file 到 2026年2月先落單(真.實質 allocation 事件,唔係
得個講字)。**但 ttm_pe 係 whole-company 分位(3年滾動95th,~62.5x)——只反映咗混合咗弱OSB同強Siding
兩盤生意嘅 blended 估值,而唔係 specialty-siding segment 本身嘅估值**,解讀要格外小心:有可能 market
已經為咗 Siding 呢條線俾咗溢價,亦有可能貴淨係因為 OSB 歷史高峰殘留嘅 multiple,兩者分唔開。呢個
不確定性 + thesis 只覆蓋公司一部分業務令 confidence 係 6個新thesis入面最保守。

## ticker 層
| ticker | 角色 | 可交易 | 估值(Tier-1,2026-07-11,whole-company) | conviction 含義 |
|---|---|---|---|---|
| [[LPX]] | 建材,SmartSide/ExpertFinish特種護牆板(強)+ 商品OSB(弱) | ✅ US | ttm_pe ~62.5x,3年滾動 **95th pctile**(混合estimate) | Segment故事真,但whole-company估值點解讀有不確定性 |

## 證據(verbatim,節錄;全文見 group D 報告)
- 2024-05-08:*"Nearly 30% cumulative Siding revenue growth over a period [in] which the underlying
  market contracted clearly demonstrates pricing power and share gains."*
- 2026-05-06(最新):*"The pricing power of SmartSide helped offset lower sales volume, moderating
  revenue declines"*(喺OSB崩盤期間)。
- 2026-05-06(關鍵):analyst 問 ExpertFinish 產量係咪產能問題,管理層確認 *"We are still dealing with
  a little bit of the ExpertFinish allocation hangover... We came off allocation... in
  February-ish."*——真.曾經 managed-allocation order file,唔係得個講字。
- 對照(commodity OSB,唔屬於呢個thesis):2026年最新季度 *"OSB price softness accounted for a $66
  million reduction in net sales and EBITDA...fell below EBITDA break even."*

## confidence 推導
```
Segment層面真訊號(7/9季pricing power語言 + 實質allocation事件) 但 whole-company ttm_pe 95th
(blended估值,分唔清邊部分反映Siding邊部分係OSB歷史殘留) + thesis只覆蓋部分業務
= 6個新thesis入面最保守 -> confidence ≈ 0.20
```

## kill_condition(可證偽)
> SmartSide/ExpertFinish「pricing power」語言喺未來一季transcript消失 **或** ExpertFinish allocation
> 狀態喺下個上升週期冇再出現(即係2026年呢次係一次性,唔係結構性)**或** OSB商品業務疲弱拖累到成間
> 公司盈利,令Siding segment嘅強度冇辦法喺股價層面反映出嚟 **或** vinyl siding競爭者收窄價格/性能
> 差距,侵蝕share-gain敘事。觸發 -> confidence歸零。

## 待補
- [ ] Capital-allocation/ROIC 分析
- [ ] Segment-level 估值拆解(嘗試分離Siding vs OSB嘅估值貢獻,而唔係用whole-company blended PE)
- [ ] TAM sizing(vinyl siding轉換率、新屋建築 vs 翻新市場佔比)
- [ ] 窄 ETF 搜尋(未搜)
- [ ] 第三方分析師報告交叉驗證

## 來源
Tier-3(transcript-discovery-radar):`thesis/corpus.db` FTS5 全文搜索,`backtest/results/
2026-07-11_discovery_radar_review_groupD.md` 逐隻人手驗證(2007-2026 分層取樣 + 2024-2026 全季覆核,
±220字context)。
