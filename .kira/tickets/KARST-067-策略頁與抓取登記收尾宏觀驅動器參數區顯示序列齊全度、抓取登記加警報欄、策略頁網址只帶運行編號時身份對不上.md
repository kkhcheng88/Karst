---
id: KARST-067
title: 策略頁與抓取登記收尾:宏觀驅動器參數區顯示序列齊全度、抓取登記加警報欄、策略頁網址只帶運行編號時身份對不上
type: task
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-056, KARST-061]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

三件細小收尾,全部源自 KARST-056 與 061 同時在改同一批檔而留下。(1) KARST-061 已備好齊全度端點(GET /api/macro/completeness),策略詳情頁宏觀驅動器參數區補「序列齊全度」一行(strategy.js 取數掛上,照 061 票上寫法,不改設計);(2) 抓取登記表加兩格:齊全度警報條數、警報摘要(KARST-061 留言建議),原地遷移保留既有編號,schema 版本加一,karst data list 可見;(3) 策略詳情頁網址只帶 ?run= 不帶 ?id= 時,上半部策略身份與歷次運行取了預設策略,與正在看的運行對不上(KARST-056 順帶發現)——由運行反查策略,令兩種寫法一致。不加參數預設值;只跑所涉測試檔。

## 驗收條件

- [ ] 策略詳情頁宏觀驅動器參數區顯示序列齊全度一行,真數據
- [ ] 抓取登記新增警報兩格,karst data list 可見,既有登記保留;karst verify 清白
- [ ] 只帶 ?run= 的網址與帶齊 ?id=&run= 的顯示一致(測試證明);只跑所涉測試檔

## 結果

## 留言
