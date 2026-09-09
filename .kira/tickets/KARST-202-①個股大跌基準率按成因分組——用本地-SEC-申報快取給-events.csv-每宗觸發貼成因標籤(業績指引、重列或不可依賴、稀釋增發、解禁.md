---
id: KARST-202
title: ①個股大跌基準率按成因分組——用本地 SEC 申報快取給 events.csv 每宗觸發貼成因標籤(業績/指引、重列或不可依賴、稀釋增發、解禁、退市通知、破產、高管離任、收購處置、指數剔除、行業共跌、無申報),按成因分組重出一至十二個月結果分佈,答「哪些成因之後回歸、哪些繼續跌」
type: research
createdAt: 2026-09-10
risk: low
model: opus
fits: 用戶 2026-09-10 原話:「candidates.md … mentioned a lot of reason of 個股大跌?? This won't hints more on the filter of the return difference of different root cause?」;strategy/candidates.md 丙族「錯殺的成因分類(①的核心):賣家賣的理由與生意無關」列六種可辨事件;KARST-187/194 的基準率表 23,883 宗觸發全部無成因標籤,池平均接近零是各成因的平均;D-168 歷史資料作基準率屬允許範圍,不屬 D-174 凍結的工具建設
dependsOn: []
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D05
---

## 工作內容

資料:research/2026-09-methodology/2026-09-09-①基準率表/out/events.csv 正本(不改)與 _gatefix 版;本地 SEC 申報快取(data/sec submissions 索引,KARST-177 補齊)。第一步成因標籤:對每宗觸發,取觸發日前 30 個交易日至後 5 個交易日窗內該公司的申報,按規則貼一個主成因與零至多個副成因:8-K Item 2.02(業績)、Item 7.01/8.01 含 guidance 字眼(指引)、Item 4.02(不可依賴/重列)、Item 3.01(退市通知)、Item 1.03(破產)、Item 5.02(高管離任)、Item 2.01(收購處置)、Item 1.01/2.03(重大合約/舉債);S-3/S-1/424B(稀釋增發);Form 144 或鎖定期屆滿(解禁,能判多少判多少);10-12B/Form 10(分拆孤兒);指數剔除(若有免費名單則用,無則標「未判」寫明);行業共跌沿用 events.csv 既有 industry_kill 欄;窗內無任何申報標「無申報」。規則清單與每條的判定次序寫成檔,主成因取窗內最接近觸發日者。第二步:按主成因分組,出每組樣本、勝率(簇 bootstrap 區間)、中位與平均超額、平均與中位盈虧比、剔前 1% 後平均、觸及 −33%/−80% 比例,1/3/6/12 個月,建表與驗證年份分開;另出「行業共跌 × 個股成因」交叉表。第三步結論業務語言:哪些成因之後回歸(可作①候選來源)、哪些繼續跌(反對票)、哪些量不出;與 candidates.md 丙族六種逐一對照,標文獻方向是否重現。落檔同目錄 out/*_cause.* 與 對照——按成因分組.md;總覽檔尾加更正紀錄節,原條文不改;倖存者口徑與「申報快取覆蓋不全」的偏差方向明寫。

## 驗收條件

- [ ] 成因標籤規則檔落檔;events.csv 每宗觸發有主成因與副成因欄(另存 *_cause.csv,不改正本),各成因宗數與「無申報」比例列出
- [ ] 按成因分組表落檔,含勝率區間、兩種盈虧比、剔前 1% 後平均、−33%/−80% 觸及率,1/3/6/12 個月,建表與驗證年份分開;行業共跌 × 個股成因交叉表落檔
- [ ] 業務語言結論:哪些成因回歸、哪些繼續跌、哪些量不出;與 candidates.md 丙族六種逐一對照
- [ ] 不改 events.csv 正本與既有輸出、不改 karst/ strategy/ library/;含中文檔案只用 Read/Write/Edit;Python 一律 PYTHONUTF8=1;不 commit

## 結果

## 留言
