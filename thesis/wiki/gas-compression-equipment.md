---
slug: gas-compression-equipment
type: B
cycle_stage: early
confidence: 0.33
verdict: real-structural-bottleneck-deeply-unloved
updated: 2026-07-11
tickers: ['USAC']
---

<!-- frontmatter = valid-YAML scalars only, tickers quoted。wiki-links 一律 INLINE 放內文;每條 claim
     inline 引用來源。切勿把 [[wiki-links]] 放進 YAML frontmatter(會斷 parser)。 -->

# 天然氣壓縮設備樽頸(B 型)— discovery radar 全批最乾淨 + 最平

> **2026-07-11 discovery radar 全市場逐隻驗證新增**,transcript-only 一手源。未做 capital-allocation/
> ROIC/TAM 深度研究。詳細證據見 `backtest/results/2026-07-11_discovery_radar_review_groupC.md`。

## 一句話(核心張力 = thesis 本身)
[[USAC]] 嘅引擎/壓縮機 lead time 喺整個商品週期入面**單向惡化**(2013年4-6個月 -> 2018年約1年 -> 2026年
150週/約3年),管理層明確講 *"our compression services business does not have direct commodity price
exposure"*——即係話唔跟油氣價格周期升跌,同 HAL/PTEN/NOV 呢類「上升週期先講sold out、落週期就冇聲」
嘅 oilfield-services 週期性完全唔同,係 discovery radar 40 候選入面**證據最乾淨**嘅一個。加上 ttm_pe
3年滾動分位**2nd**(2026-07-11量度,~27.1x)——全批估值最平,幾乎完全未被市場發現/reprice,同
priced_in_gate 框架講嘅「supply-tight × unloved」最理想象限吻合。**6個新thesis入面confidence最高。**

## ticker 層
| ticker | 角色 | 可交易 | 估值(Tier-1,2026-07-11) | conviction 含義 |
|---|---|---|---|---|
| [[USAC]] | 天然氣壓縮設備服務,大型馬力機隊自有者 | ✅ US | ttm_pe ~27.1x,3年滾動 **2nd pctile** | 故事最乾淨+估值最平,discovery radar呢批最佳組合 |

## 證據(verbatim,節錄;全文見 group C 報告)
- 2018-11-06:*"we're effectively sold out of the larger horsepower assets... Lead times for the large
  horsepower equipment...are still right around a year."*
- 2022-08-02:管理層明確講 *"our compression services business does not have direct commodity price
  exposure."*
- 2026-05-05(最新):*"Certain new engine lead times have recently tripled from 50 weeks to
  approximately 150 weeks... we have already placed orders for engines and packaged components for
  2027 and engines for 2028 and a portion of 2029."*

需求驅動:LNG出口 + Permian associated gas + AI天然氣發電拉動,多年期結構性故事,唔係單一價格 spike。
2026年 J-W Power 併購令 USAC 有 in-house 製造能力可以打尖(moat-widening)。

## confidence 推導
```
全批證據最乾淨(明確非商品價掛鈎,13年單向惡化) + ttm_pe 2nd pctile(全批最平)
= priced_in_gate框架嘅「supply-tight × unloved」最理想象限,discovery radar呢批入面confidence最高
但單一ticker(冇thesis_etf分散),集中風險要留意 -> confidence ≈ 0.33
```

## kill_condition(可證偽)
> 引擎/壓縮機 lead time 開始壓縮返歷史常態(150週 -> 少於52週)**或** 主要OEM(Caterpillar/Ariel)
> 新產能上線紓緩樽頸 **或** 需求驅動力(LNG出口+Permian associated gas+AI天然氣發電拉動)增長停滯/
> 逆轉。觸發 -> confidence 歸零。

## 待補
- [ ] Capital-allocation/ROIC 分析
- [ ] TAM sizing(LNG出口+AI天然氣發電需求未來5年展望)
- [ ] 窄 ETF 搜尋(未搜)
- [ ] 第三方分析師報告交叉驗證
- [ ] 單一ticker集中風險評估(考慮同業 CSI Compressco/Archrock 做對照)

## 來源
Tier-3(transcript-discovery-radar):`thesis/corpus.db` FTS5 全文搜索,`backtest/results/
2026-07-11_discovery_radar_review_groupC.md` 逐隻人手驗證(2013-2026 分層取樣,±250字context)。
