---
slug: gas-compression-equipment
type: B
cycle_stage: early
confidence: 0.3
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

## confidence 推導(可追溯;2026-07-16 P2 遷移 + red-team 判決)
```
KPI: moat 1/2(gatekeeper §6 裁決 + red-team 2026-07-16 確認:150 週 lead time、13年單向惡化、
       「no direct commodity price exposure」解耦真;但咽喉喺 OEM(CAT/Ariel),USAC 係受益者/fleet
       持有人非咽喉持有人,一手財數證實 USAC 係被動受益者[毛利兩年橫行冇擴張、利用率94.4%→91.9%
       倒跌]、pricing power一手喺同業KGS/AROC唔喺USAC → 由 1.5 降至 1)
     · capital 1/2(EBIT margin 0.301 高 但 coverage 1.72 低/net_debt-EBITDA 4.75/solvency_flag=true
       + MLP 分派重 → 有盈利唔俾 0 但槓桿拖低;solvency 由獨立條件閘處理,唔重複折)
     · valuation 2/2(pe_pctile 2nd <50 且 p_base 0.468 ≥0.4,機械格,全批最平;但低multiple有結構
       解釋[4.73x槓桿+負賬面權益四季],唔一定係「未發現」)
     · growth 1/2(red-team 中彈:AI-gas magnitude 腿一手零傳導[GEV backlog屬發電非壓縮],有機增長
       靠併購非需求拉動,「2027-2029訂單」係USAC買引擎capex承諾非客戶收入backlog → 由 1.5 降至 1)
                                                                          = 5.0/8 = 0.625 base
penalty(§4a 表:crowding 88.9 → 80–90 帶 × early)                       × 0.75  → 0.469
single-source cap(sources len=1)                                        → min(0.469, 0.30)
→ confidence = 0.30  (現行 0.33 已違反 cap,屬修正;AI-gas magnitude 腿已 flag
   magnitude_unconfirmed,見 compression-shortage-unloved node。INITIAL, uncalibrated)
```
red-team 詳見 `backtest/results/2026-07-16_redteam_gas_compression.md`。

## red_team(Level-2,2026-07-16;詳 backtest/results/2026-07-16_redteam_gas_compression.md)
- **判決:部分中彈**——樽頸機制(150週交期)生還兼被多操作商一手佐證強化(Kodiak/Archrock/NGS
  獨立確認150-180週且升級中);但承重「USAC 直接受益者」中彈(本次最鋒利一刀)。
- **一手財數證實 USAC 係最弱可交易載體**:毛利兩年橫行27-34%(冇擴張,對照 photonics 龍頭毛利九季
  單調擴張);利用率倒跌94.4%→91.9%;增長靠J-W Power併購(攤薄)非有機;CEO零具體有機加租幅度。
  同一稀缺,Kodiak(98%利用率)/Archrock(95%)展示咗真.主動pricing power一手,USAC冇。
- **「2nd pctile 最平未發現」被balance-sheet推翻**:Net Debt/EBITDA 4.73x + 負賬面權益四季 + 利息
  覆蓋1.77x + MLP分派封equity上檔 → 低multiple係槓桿/攤薄correctly-priced,非「錯殺未發現」。
- **已 flag `magnitude_unconfirmed: true`**(compression-shortage-unloved node)——AI-gas magnitude
  腿一手零傳導 + USAC被動受益者(非主動定價權持有人),sizing v2 對此 node 收起 3-5x-durable 加成。

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
