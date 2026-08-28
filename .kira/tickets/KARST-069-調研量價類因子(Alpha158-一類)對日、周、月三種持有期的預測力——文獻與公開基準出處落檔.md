---
id: KARST-069
title: 調研:量價類因子(Alpha158 一類)對日、周、月三種持有期的預測力——文獻與公開基準出處落檔
type: research
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: null
closed: 2026-08-29
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

用戶 2026-08-29 問(原話「I want to know if this is useful for Day or Weekly or Month trading window. Any research did that?」)。主 agent 已口頭答:Alpha158 設計為日線、預測 1–5 日;短期反轉主導一個月內、動量主導 3–12 個月;美股大型股單因子預測力弱、需合併;月度以上靠基本面與風格因子。本票把出處落檔:(1) qlib Alpha158 原設計的標籤與持有期、公開基準的 IC 量級(A 股);(2) 學術文獻:短期反轉(Jegadeesh 1990、Lehmann 1990)、動量(Jegadeesh & Titman 1993)、成交量與波幅類因子對周度回報的證據、美股 vs A 股的技術因子預測力差異;(3) 任何在美股上跑過 Alpha158/Alpha360 的公開結果;(4) 結語:對 Karst 的意思——哪一段持有期值得先掃、預測力面板應先看哪三個窗口。輸出 research/2026-08-29-factor-horizon-evidence.md,每條有 URL 或 DOI。不動程式、不動庫。

## 驗收條件

- [x] 研究檔落檔,四節各有出處
- [x] 結語給出預測力面板首輪應看的持有期窗口建議
- [x] 不動程式、不動庫

## 結果

1. qlib Alpha158 原設計標籤是次日報酬,官方公開基準(CSI300,A 股)的 IC 落在 0.04–0.05 量級,只驗了次日這一個窗口,沒有官方周度/月度版本。
2. 學術文獻確認四個持有期各有主導因子:1 週反轉最強(Lehmann 1990)、1 個月反轉轉弱但成交量與波幅異常接手(Jegadeesh 1990、Gervais et al. 2001、Ang et al. 2006)、3–12 個月換動量主導(Jegadeesh & Titman 1993),跟量價因子完全是不同時間尺度;A 股市場結構跟美股不同(Liu Stambaugh Yuan 2019),技術因子在 A 股更強有間接證據支持。
3. 沒有機構級論文在美股上跑過 Alpha158/360 並公布 IC,唯一查到的個人部落格覆現(標普 500,PyTorch MLP/LightGBM)測出 IC 僅 0.004–0.005,比 A 股官方基準弱一個數量級,只能當量級參考。
4. 建議預測力面板首輪看 1、5、21 個交易日三個窗口,分別對應 qlib 原設計、周度反轉證據、月度反轉與量波證據疊加的轉折點;動量的 3–12 個月窗口留給日後另一批因子,不併入本輪。

詳見 research/2026-08-29-factor-horizon-evidence.md。

## 留言
