---
slug: us-solar-manufacturing
type: B
cycle_stage: mid
confidence: 0.32
verdict: real-policy-moat-and-still-cheap
updated: 2026-07-11
tickers: ['FSLR']
---

<!-- frontmatter = valid-YAML scalars only, tickers quoted。wiki-links 一律 INLINE 放內文;每條 claim
     inline 引用來源。切勿把 [[wiki-links]] 放進 YAML frontmatter(會斷 parser)。 -->

# 美國太陽能製造貿易政策護城河(B 型)— 7年連續 sold-out,估值仲未追

> **2026-07-11 discovery radar 全市場逐隻驗證新增**,transcript-only 一手源。未做 capital-allocation/
> ROIC/TAM 深度研究。詳細證據見 `backtest/results/2026-07-11_discovery_radar_review_groupB.md`。

## 一句話(核心張力 = thesis 本身)
[[FSLR]] 連續 7 年一路向後年份延伸嘅 sold-out/fully-allocated 語言(2019年賣晒到2020 -> 2021年賣晒到
2022+訂單到2024 -> 2023年賣晒到2026+backlog到2030 -> 2026年確認"fully allocated position for our
U.S. production",同 2 年前預告吻合)。護城河由美國貿易政策(232/301關稅 + IRA本土成分獎勵)撐住,唔係
純週期性半導體荒。**呢批 discovery radar 40 候選入面 priced-in 狀態最好嘅一個**:ttm_pe 3年滾動分位
22nd(2026-07-11量度,~14.7x)——結構故事真,但市場仲未完全重估,同 [[USAC]] 一齊係少數「supply-tight
× unloved」象限嘅新候選。主要風險係政策 binary(關稅/IRA 可被下屆政府撤銷)。

## ticker 層
| ticker | 角色 | 可交易 | 估值(Tier-1,2026-07-11) | conviction 含義 |
|---|---|---|---|---|
| [[FSLR]] | 美國本土太陽能板製造,關稅/IRA護城河 | ✅ US | ttm_pe ~14.7x,3年滾動 **22nd pctile** | 真結構+仲平,discovery radar呢批priced-in最好 |

## 證據(verbatim,節錄;全文見 group B 報告)
- 2016-04-27(負面對照組,證明唔係常態吹噓):CFO *"I wouldn't say we have pricing power but we have
  that ability to optimize."*
- 2023-10-31:*"Our contracted backlog extends into 2030, and excluding India, we are sold out
  through 2026."*
- 2026-02-24:*"We entered 2026 with a fully allocated position for our U.S. production."*
- 2026-04-30(最新):美國本土產能維持全負荷,只有海外(馬來西亞/越南)產能因關稅政策 demand-side 受限。

## confidence 推導
```
7年連續、量化、持續確認嘅結構故事 + 政策護城河(非純週期性) + ttm_pe 22nd pctile(discovery radar
呢批入面priced-in狀態最好)= 6個新thesis入面confidence較高嗰個
但政策binary風險(關稅/IRA可撤銷)非零,要扣返少少 -> confidence ≈ 0.32
```

## kill_condition(可證偽)
> Section 201/232/301 太陽能關稅或 IRA 本土成分規定被撤銷/豁免,重開美國市場俾中國/東南亞競爭者
> **或** "sold out" backlog 落空(大額訂單取消)**或** 美國太陽能需求增長停滯(聯邦可再生能源政策
> 逆轉)。任何一項觸發 -> confidence 歸零。2016年 FSLR 自己講過「冇pricing power」,證明依家嘅定價權
> 唔係常態,政策逆轉風險係真實嘅。

## 跨主題連結
**2026-07-13**:核心原料(碲)中國出口管制風險已抽到跨主題總覽 [[china-supply-macro-risk]](同
[[rare-earth-materials]]、[[photonics-optical]] 嘅 [[AXTI]] 並列)——同一機制(中國用關鍵原料出口牌照
做地緣槓桿),但唔綁定 rare-earth-materials 嗰個 2026-11 calendar 觸發點(碲管制係 2025-02 已生效嘅
持續狀態,非等待中嘅二元事件),監察時唔應混為一談。

## 待補
- [ ] Capital-allocation/ROIC 分析
- [ ] TAM sizing(美國太陽能裝機未來5年展望 + 政策路徑情境分析)
- [ ] 窄 ETF 搜尋(未搜)
- [ ] 第三方分析師報告交叉驗證

## 來源
Tier-3(transcript-discovery-radar):`thesis/corpus.db` FTS5 全文搜索,`backtest/results/
2026-07-11_discovery_radar_review_groupB.md` 逐隻人手驗證(2007-2026 分層取樣,±220字context)。
