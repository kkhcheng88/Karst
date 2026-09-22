---
id: KARST-254
title: S2 證券價格序列 module(架構候選一):身份核對、口徑、交易時段、歷史門檻與增量接駁單一入口
type: task
createdAt: 2026-09-23
risk: high
model: opus
fits: 一程:bars 模組加深及六個呼叫點改接,測試改經新 interface
dependsOn: []
claimedBy: Opus-S2
epic: 根基重整
deliverable: KARST-D12
closed: 2026-09-23
---

## 工作內容

依執行計劃 §三 2 及 2026-09-23 架構評審候選一。現況:service.plan_update／render_charts／_publication_bars、daily 兩處、workflow 各自拼裝日曆與口徑,並讀取私有 bars._basis;身份過濾只在 workflow;歷史門檻三套(daily 200 根、出圖 2 根、發布 0.9)。把這些收進 bars 模組的一個入口,呼叫方只問「給我某證券截至某時的序列及其是否足夠某用途」。門檻按用途命名、單一出處。不改現有序列數值與完成狀態語義(KARST-250 規則保持)。程式只住 karst/,不寫一次性腳本。

## 驗收條件

- [x] karst/ 內不再有 bars 模組以外的地方呼叫 _basis 或自行拼裝交易時段
- [x] 證券身份核對由序列入口統一執行,六個呼叫點全部經它
- [x] 歷史足夠門檻按用途命名並只有一處定義
- [x] 既有 bars／charts／daily／publish 測試全部通過,新 interface 有定向測試覆蓋身份不符、歷史不足、增量接駁
- [x] 已發布研究重建序列的數值與重構前逐值相同(以既有 fixture 驗)

## 結果

新入口 `bars.series_for(bundle, security, as_of, records=None)` 回 `Series`(daily、views、source、basis、gaps、last_complete),`Series.enough(use)` 答三種用途;門檻 CHART_MIN_BARS=2、DAILY_CHECK_MIN_COMPLETE=200、PUBLICATION_MIN_SHARE=0.9 只在 bars.py 定義。六個呼叫點全部改接,`series_from_evidence`／`from_evidence`／`refused_prices` 併入模組內部。七份已發布研究以其 inputs 重建序列(兩個截止時點)重構前後逐 bytes 相同。全套 440 通過、1 跳過,唯一失敗是既有 test_reader symlink(WinError 1314)。

## 留言

### agent:Opus-S2 · 2026-09-23 10:30

實作要點:(1) 身份核對:只讀登記在 security_id(無則 issuer_id,cik 拼法歸一)名下的價格,另一證券的快照寫入 gaps;證券無任何 id 時無從核對,照舊讀取(render_charts 在無 packet 的公司倉)。plan_update 無 packet 時以 subject 作 security_id。(2) 交易時段由 security.exchange 推出,`session=` 只留作配置半日市／假期的旋鈕。(3) 口徑以結構化 `basis` 回傳,workflow 與 plan_update 不再回頭找來源記錄讀 `_basis`。(4) 行為差異一處:daily 的補取觸發原以全部根數 <200 判斷、history_ready 以已確認根數 ≥200 判斷,現統一為已確認根數(daily_check);只在「總數 ≥200 但已確認 <200」的邊界多補取一次。(5) 七份發布的逐值比對用倉外 scratchpad 腳本,未 commit;既有 test_publish_bars 與 charts 測試同樣經新入口通過。新詞「證券價格序列」「歷史足夠門檻」已入 CONTEXT.md。對 KARST-256:增量快照只要以同口徑登記,`series_for` 會自動以最新快照為主、舊快照補早段(segments 記兩段),`enough('daily_check')` 判是否仍需全量補取。
