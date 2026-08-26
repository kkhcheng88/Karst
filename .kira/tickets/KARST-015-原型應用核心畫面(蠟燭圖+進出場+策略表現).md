---
id: KARST-015
title: 原型:應用核心畫面(蠟燭圖+進出場+策略表現)
type: prototype
createdAt: 2026-08-26
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-007, KARST-014]
claimedBy: null
epic: V1 藍圖
deliverable: KARST-D01
---

## 工作內容

要用具體東西回答的問題:應用核心畫面實際長什麼樣——蠟燭圖上的進出場標記、虛擬籃子的合成淨值圖、各策略表現一覽呢三個畫面,按 KARST-007 傾掂的形態同 KARST-014 揀的圖表庫,砌一個粗原型(假數據即可)俾用戶反應。原型定案的配色、版面骨架、元件選擇,落 design-system.md 做正本——設計系統由此誕生,不先於原型。

## 驗收條件

- [x] 三個核心畫面有可打開的粗原型(假數據)
- [x] 用戶對原型的反應有記錄,採納與否逐項有裁決
- [x] 定案的 token 與元件落 design-system.md

## 結果

· 2026-08-27 02:40 原型十版迭代收版。prototype/ 四頁(策略總覽、策略詳情、運行詳情、參數掃描)以 lightweight-charts 假數據砌成,第十版定為 v1 基線(D-023:畫面不再是阻塞項,日後可改)。用戶逐版反應與裁決已入 D-020 精神與詞彙表(現役設定、選股快照、檢視運行、檢視視窗、因子族);未裁小項(漏斗篩選語意、圖下留白)照現狀落檔。設計系統正本 .kira/design-system.md(token、版面骨架、14 個元件狀態、六條畫面原則、十項待統一)由第十版抽出,值未改動。

closed: 2026-08-27

## 留言

· 2026-08-26 03:05 fable-main 圖表庫已定:用戶拍板 lightweight-charts(D-019),本票原型以此為基砌;Plotly/Dash 只作後備。留言完放回未認領。

· 2026-08-27 01:10 fable-main 用戶對第八版(策略頁改單一捲軸)的反應轉成第九版要求,並帶出三項落規格的裁決:(1) 策略頁可揀「檢視運行」,整頁隨之切換,預設現役設定並標明非現役;(2) 「檢視視窗」——同一次運行的逐日結果可由任意起始日重看,不需重跑(用戶原話:「if I just want to focus on the performance since 2023 then I don't need a rerun?」)→ 引擎規格要求運行結果必須保存逐日淨值與持倉序列;(3) 因子命名落在「族名·具體定義」一級,族名不是因子(用戶原話:「動量, or 質素 are really can be single definition?」)。詞彙表已加 因子族、檢視視窗。另:策略頁淨值圖加買賣標記與滑過見成交;漏斗層可點作篩選。
