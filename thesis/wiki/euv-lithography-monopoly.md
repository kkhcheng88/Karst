---
slug: euv-lithography-monopoly
type: B
cycle_stage: late
confidence: 0.40
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

## confidence 推導(可追溯;2026-07-16 P2 遷移 + red-team 判決)
```
KPI: moat 2/2(全球唯一 EUV/High-NA 微影供應商、16 年橫跨 4 週期第一人稱約束語言;red-team
       2026-07-16 判「生還+補強」——雙 Tier-1 獨立擊中承重:現金背書 down-payment[合約負債
       ≈$19.4B≈FY2025營收59.3%] + 16年約束語言 transcript → 生還升格 2/2)
     · capital 1.5/2(EBIT margin 0.328/coverage 104/net cash 極穩;現金背書佐證資本配置紀律)
     · valuation 0/2(pe_pctile 98th ≥90 + p_base 0.184 <0.4,機械格;全市場最人盡皆知嘅壟斷)
     · growth 1.5/2(AI 驅動先進製程 capex 拉動,兌現中;TAM 未 sizing)   = 5.0/8 = 0.625 base
penalty(§4a 表:crowding 57.4 → 40-60 帶 × late)                          × 0.65  → raw 0.406
登記雙 Tier-1 source(asml-cash-backed-downpayments,corroborates 供給半截)→ n_sources=2
→ 脫 single-source cap 0.30:成立(現金背書證據紮實,呢部分冇問題)
→ UNCALIBRATED_CAP 0.40:**適用、綁住**(STATUS.md:256;forward_ic matured=0)
→ confidence = min(0.406, 0.40) = **0.40**  (uncalibrated;D1 已修,D2 待拍板)
```

> ## D1 已修(2026-07-17),D2 仍未決
> 正本:`backtest/results/2026-07-16_crowding_asml_contamination.md`(調查)
> + `backtest/results/2026-07-17_crowding_d1_fix_verification.md`(A/B 驗證)
> - **D1 資料污染 — 已修**:6 份 ASML/ASMLF 非法說會文件(記者會/IR 宣傳片,「分析員」= 路透社記者
>   或 ASML 自己 CEO/CFO)已由 `crowding_composite.py` 嘅 `NON_ANALYST_CALL_DOCS` 排除。
>   A/B 驗證(同日同 DB,只差修正):**只有 euv 郁(2.8 → 57.4),其餘 16 個 theme 全部 +0.0**
>   —— 外科手術式,無旁及損害。crowding 由假讀數 2.8 還原至 **57.4**;raw 0.469 → **0.406**;
>   confidence 維持 0.40(uncalibrated cap 仍然綁住)。⚠️ 57.4 距 60 帶界只差 2.6 分,一過界 → 0.34。
> - **D2 建構效度 — 未決(用戶拍板)**:crowding 軸量緊 **temporal 自身歷史分位**,但 penalty 表要嘅係
>   **cross-sectional priced-in 折扣**。證據 = 全書排名反轉(ASML 98 分位 PE、全市場最多人講 → 讀成
>   「唔擠」;冷門包裝/護牆板 → 讀成「最擠 95-97」)。**呢個影響全部 17 個 theme 嘅 penalty,唔止 euv。**
>   若改 cross-sectional,ASML 應 ≥90 → euv confidence 0.25(= 紅隊原本估值)。
> - **紅隊原本估 crowding ≥90 → 0.25。佢個直覺啱**,係 gatekeeper 攞污染數推翻咗佢(已認)。
>   D1 修完得 57.4,仍未到紅隊估嘅 ≥90 —— 差距正正就係 D2 嗰個 temporal-vs-cross-sectional 問題。

red-team 詳見 `backtest/results/2026-07-16_redteam_euv_lithography.md`。

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
