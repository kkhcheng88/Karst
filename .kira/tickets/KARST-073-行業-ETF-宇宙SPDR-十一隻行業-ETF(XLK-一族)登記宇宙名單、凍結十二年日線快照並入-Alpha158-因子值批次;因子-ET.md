---
id: KARST-073
title: 行業 ETF 宇宙:SPDR 十一隻行業 ETF(XLK 一族)登記宇宙名單、凍結十二年日線快照並入 Alpha158 因子值批次;因子 ETF 快照亦入批次
type: task
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-068]
claimedBy: null
closed: 2026-08-29
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

用戶 2026-08-29 裁決要測「XLK and related series of industrial ETF, and the 4 S&P factor ETF」。本票只做數據準備,不做實測(實測票等 KARST-072 文獻結論向用戶交代後才開)。範圍:(1) 宇宙名單登記新增「SPDR 行業 ETF」:XLK、XLF、XLE、XLV、XLI、XLY、XLP、XLU、XLB、XLRE(2015-10 起)、XLC(2018-06 起),連 SPY 作主日曆錨,成立日期照登記;(2) 經唯一入口凍結 2015 年起日線快照,較遲成立的兩隻照 D-026 標示起始缺口;(3) 以 karst factor ingest-alpha158 把該快照與既有因子 ETF 快照 2026-08-28-000b4820a23a(SPY、QQQ、QUAL、VLUE、MTUM、USMV)各入一批 Alpha158 因子值;(4) experiments/snapshot_ids.py 加編號;結果落 experiments/2026-08-29-sector-etf-universe/(README、行數、缺值比例)。karst verify 清白。不加參數預設值;只跑所涉測試檔。

## 驗收條件

- [x] 宇宙名單登記有「SPDR 行業 ETF」,唯一入口列得出;快照凍結,兩隻較遲成立的起始缺口照 D-026 標示
- [x] 行業 ETF 快照與因子 ETF 快照各有 Alpha158 因子值批次,行數與缺值比例落檔;karst verify 清白
- [x] snapshot_ids.py 已加編號;只跑所涉測試檔

## 結果

**宇宙名單登記。** `karst/data/universe.py` 新增 `SECTOR_ETF_UNIVERSE`(十一隻:
XLK、XLF、XLE、XLV、XLI、XLY、XLP、XLU、XLB、XLRE、XLC)與登記名單
`sector-etf`(連 SPY 主日曆錨共十二隻),唯一入口 `karst data universe --name
sector-etf` 列得出;成立日期九隻 1998-12-16、XLRE 2015-10-07、XLC 2018-06-18。

**快照凍結。** 經唯一入口 `karst data snapshot` 凍結 2015-01-02~2026-08-28
窗口,編號 **`2026-08-29-d5c393e65534`**(2,930 個交易日、12 個實體、
**35,160 列**)。XLRE、XLC 上市前那段窗口留白、不補假數據,原因逐條寫入快照
說明檔的 `--note` 註記(D-026 第 6 條)。整份快照缺值 1,064 列(3.03%),
全部集中在 XLRE(193 列,6.59%)與 XLC(871 列,29.73%)的上市前段,其餘
九隻分類 ETF 與 SPY 全窗口零缺值。

**Alpha158 因子值批次。** `karst factor ingest-alpha158` 各入一批:
行業 ETF 快照(`2026-08-29-d5c393e65534`)158 條因子、5,400,668 個值、
缺值比例 2.7832%;既有因子 ETF 快照(`2026-08-28-000b4820a23a`)158 條因子、
2,775,447 個值、缺值比例 0.0448%。`karst verify` 清白。

**編號登記與落檔。** `experiments/snapshot_ids.py` 加 `PRICE_SECTOR_ETF`;
結果落 `experiments/2026-08-29-sector-etf-universe/`(README.md、summary.json)。

**測試。** 只跑所涉測試檔:`tests/test_gateway_data.py`(加一句斷言覆蓋
`sector-etf` 名單,6 條全過)、`tests/test_alpha158_ingest.py`(未改動因子
入庫程式碼,覆核既有行為不受影響,10 條全過)。

## 留言
