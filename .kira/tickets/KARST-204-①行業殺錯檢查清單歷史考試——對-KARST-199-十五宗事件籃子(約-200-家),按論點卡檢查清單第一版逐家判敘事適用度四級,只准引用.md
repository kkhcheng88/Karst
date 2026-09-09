---
id: KARST-204
title: ①行業殺錯檢查清單歷史考試——對 KARST-199 十五宗事件籃子(約 200 家),按論點卡檢查清單第一版逐家判敘事適用度四級,只准引用衝擊前文件段落並附出處,另設只憑記憶對照臂,由分開的評分隊對照十二個月結果,答「清單判出來的適用度分不分得開贏輸、有文件比無文件好多少」
type: research
createdAt: 2026-09-10
risk: low
model: opus
fits: 用戶 2026-09-10 原話:「If you based on this mean LLM based assessment are not even a way or not needed to backtest as it must be faked … what should be the checklist to be validated」;KARST-199 舉手「敘事適用度住在年報文字裡,本票沒有去拿」;D-168 分類器時點考核正是此用途,污染由協議防而非不考
dependsOn: [KARST-203]
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D05
---

## 工作內容

前置:KARST-203(檢查清單第一版)收檔,照它的清單與防污染協議做。資料:KARST-199 的 events_spec.json 與籃子成員 csv;每家取衝擊起日之前最近一份 10-K 與 10-Q(data/sec 本地快取,缺則打 EDGAR)、衝擊前最近一次業績會逐字稿(有則用,無則標)。判斷臂 A(有文件):對每家逐格填檢查清單,敘事適用度四級,每個判斷附文件名、節、段落原句;判斷臂 B(記憶對照):同一家同一問題,明令不得查任何文件、只憑一般知識答,分開的子代理做,兩臂互不見。評分:另一子代理只拿兩臂的四級結果與 199 的十二個月超額,出每臂「適用度四級 × 十二個月中位/平均/勝率」表、A 對 B 的分辨力差(例如四級與結果的秩相關、最高級與最低級的成績差)、引用抽查十家核對段落真確。結論業務語言:清單分不分得開;文件比記憶多做了多少功;哪幾格最有分辨力、哪幾格答不到;對 KARST-200 活個案的清單要改什麼。落檔 research/2026-09-methodology/2026-09-10-①行業殺錯事件籃子/checklist_test/。倖存者與 D-168 污染兩點明寫;不改 199 既有輸出、不改 karst/ strategy/ library/;含中文檔案只用 Read/Write/Edit;Python 一律 PYTHONUTF8=1;不 commit。

## 驗收條件

- [ ] 每家兩臂四級判斷落檔,A 臂每判斷附衝擊前文件出處與段落;引用抽查十家結果落檔
- [ ] 評分表落檔:兩臂各自的四級 × 十二個月結果、A 對 B 分辨力差、最有分辨力的格
- [ ] 業務語言結論與對 KARST-200 清單的修改建議
- [ ] 判斷臂與評分隊分開的子代理做、B 臂不得查文件;不改 199 既有輸出、karst/ strategy/ library/;含中文檔案只用 Read/Write/Edit;Python 一律 PYTHONUTF8=1;不 commit

## 結果

## 留言

### agent:main-fable · 2026-09-10 03:09
口徑補充(用戶 2026-09-10 原話:「if you afraid on cheating, we can even redact and ask anothing agent to independently assess. But it is actually no point of doing that, until we can got the correct way in assessing it from a economic point of view」):本票主產出是「經濟學上的清單分不分得開贏輸」;記憶對照臂(B 臂)降為選做,做不做由接票者按成本判;引用出處與判斷/評分分隊仍要。等 KARST-203 收檔才派。
