# Result — VCP PATTERN:收縮結構加唔加到純突破?(NO edge,slightly HURTS)

**Date:** 2026-07-05  **Scripts:** `exp_vcp_pattern.py`(重跑,修 `_DATA` reorg 路徑後);
`exp_vcp_sharpely.py`(sharpely.in 規則版,git log `beec6bc` 佐證,同路徑 bug 未重跑)  **Tag:** negative
—— close 咗孤兒(結論本來只喺 git log `f8b9b67`/`beec6bc`,今補 results 檔;第 3 次一致確認)。

## Question
Minervini VCP(volatility contraction pattern)嘅**收縮結構**——連續愈嚟愈淺嘅回調 + 量縮——係咪喺
純趨勢範本突破之上**加價值**?(用戶問 VCP 未測 → 其實測過,今正式落檔。)

## Method
3273 股;趨勢範本(price>50>150>200、200 上升、距 52wk 高/低)+ pivot 突破 → 172,309 個突破候選。
忠實 operationalise VCP:zigzag swing 抽收縮序列(每段 H→L 回調 ≥2%)+ 單調收窄(每段淺過上段)+
末段夠緊(≤15%)+ 量縮(base 尾三分一 vs 頭三分一)。**A/B**:VCP 突破 vs not-VCP 突破;**連續 IC**:
VCP-similarity score vs forward excess。SWING horizons 5/10/21/42/63d,excess vs SPY,look-ahead-safe
(base+swing 只用 ≤突破日,次棒進場)。62% 突破被判 is_vcp。

## Results — excess vs SPY(%,t;n)
| horizon | A 全部突破 | B VCP 突破 | not-VCP 突破 | IC(score) |
|---|---|---|---|---|
| 5d | +0.10 (7.0) | +0.06 (3.8) | **+0.16 (6.3)** | +0.001 |
| 10d | +0.24 (11.4) | +0.17 (7.2) | **+0.35 (8.9)** | +0.001 |
| 21d | +0.42 (13.3) | +0.32 (9.1) | **+0.59 (9.7)** | −0.001 |
| 42d | +0.75 (17.0) | +0.62 (12.1) | **+0.96 (11.9)** | +0.002 |
| 63d | +1.08 (7.8) | +0.82 (11.7) | **+1.53 (4.3)** | +0.001 |

## Conclusions
1. **VCP 突破喺每個 swing horizon 都輸畀 not-VCP 突破**(not-VCP +0.16~1.53 vs VCP +0.06~0.82)。
2. **連續 VCP-similarity IC ≈ 0**(+0.001~−0.001,全 horizon)—— VCP-ness 唔預測 forward。
3. **∴ VCP 收縮結構加唔到值,仲輕微傷**:較鬆/闊嘅底突破反而爆得大(pent-up range expansion)。
4. 純突破本身有細正 follow-through(A +0.10~1.08% excess,t 顯著)—— 但 **VCP shape = discretionary
   dressing**,唔係 edge。

## Caveats
- Costless;survivorship(cache 生還者)。
- **Selection 偏差**:VCP 傾向揀低波名,not-VCP 較高波 → not-VCP excess 大部分係波動而非 alpha
  (但 IC≈0 已足證 VCP 唔預測)。
- **量縮 under-tested**:px cache 多數只有 close 無 volume → 量縮 default 0.5,VCP 嘅「量」維度冇真正測。
- base=65d、swing w=3/2%、is_vcp 門檻皆選擇;但三次不同 operationalisation 一致 → 穩健。

## Confidence: **HIGH(negative)** —— 三次(pattern×2 + sharpely)一致「VCP 唔加值/輕微傷」。

## Implication for Karst
- **唔好建 VCP 做 Phase-1 選股 edge** —— 收縮結構冇增量。純趨勢範本突破嘅細正 follow-through 先係實際
  存在嘅嘢(而佢一樣係 timing/風控,唔係 alpha,見 [[breakout_momentum]] / `2026-07-05_breakout_momentum.md`)。
- 唯一未閉:VCP 嘅**成交量**維度(cache 無量)—— 若日後接真 volume,可補測量縮 filter,但先驗預期低。
- 同大局一致:**價格型態/突破 = 風控/timing 非 alpha;真 alpha 靠 Phase 3。**
