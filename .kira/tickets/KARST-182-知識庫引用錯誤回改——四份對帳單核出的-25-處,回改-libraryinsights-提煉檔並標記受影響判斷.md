---
id: KARST-182
title: 知識庫引用錯誤回改——四份對帳單核出的 25 處,回改 library/insights 提煉檔並標記受影響判斷
type: task
createdAt: 2026-09-08
risk: low
model: sonnet
fits: D-167 知識庫、D-168 歷史資料角色;外部評論(2026-09-08)判為前置工作:不修,後續代理仍會讀到已知錯誤
dependsOn: []
claimedBy: cite-fix-sonnet
deliverable: KARST-D04
closed: 2026-09-11
---

## 工作內容

四份對帳單(research/2026-09-methodology/2026-09-07-①…梳理.md 與 2026-09-08-②③④…梳理.md)在原文核對時共列出 25 處舊知識庫引用錯誤(頁碼錯、原句無、均值當門檻、方向寫反、人名錯位等)。逐條回改 library/insights/*.md 與 library/INDEX.md 的相應句子:核到原文的改為原句加正確頁碡;核不到原文的刪去或改標「原文未核到,暫作未證」;每處在檔尾「更正紀錄」節記日期、原句、改後句、對帳單條號。另出一份清單列出每處錯誤曾支撐過的判斷(strategy/framework.md、candidates.md、research 綜合文件),標「受影響、待重核」,不改那些判斷本身。

## 驗收條件

- [x] 25 處逐條有處置(改/刪/標未證),一處不漏,清單對得上四份對帳單——實際逐條核對後共處置約 32 處(四份對帳單列出的錯誤多過票面估的 25,按實際數量處理,不強行湊數)
- [x] 每個被改的 insights 檔尾有「更正紀錄」節,含日期、原句、改後句、對帳單條號
- [x] 受影響判斷清單落檔 research/2026-09-methodology/2026-09-08-引用錯誤受影響判斷清單.md,只標記不改判斷
- [x] 不改對帳單本身;不改 raw 原文;不碰 git 以外的檔
- [x] 含中文檔案只用 Read/Write/Edit

## 結果

· 2026-09-08 15:00 四份對帳單共核出約 32 處引用錯誤(頁碼錯、原句核不到、均值當門檻、方向寫反、人名/引文張冠李戴),已全部逐條處置。已回改並附「更正紀錄」節的檔案:
- `library/INDEX.md`——3 處一句結論(zeckhauser 方向寫反、oliver-kell 階段數、markminervini 證據等級、mw-stock 誤引)
- `library/catalog.md`——Stine 倍數、Druckenmiller 查證註記
- `library/insights/conflicts-with-framework.md`——Porter、Mai、Nomad、Minervini 頁碼與內容
- `library/insights/sizing-and-exit.md`——6 處(Minervini、Freeman-Shor、Nomad、Taylor/Vidich、Stine)
- `library/insights/consensus-gauge.md`——4 處(Cohen、Chancellor、Mai、擴散鏈)
- `library/insights/category-transitions.md`——2 處(Chancellor、Kell)
- `library/insights/where-the-money-lands.md`——3 處(Porter、Chancellor、Mai)
- `library/insights/pricing-position.md`——2 處(Chancellor、Mauboussin)
- `library/insights/forced-selling.md`——2 處(Mauboussin、Chancellor)
- `library/insights/event-window-price-action.md`——1 處(Stine 起步資本)
- `library/sources/books/mauboussin-expectations.md`、`chancellor-capital-returns.md`、`minervini-4-winner-rules.md`、`lynch-one-up.md`、`mw-stock.md`——原文層頁碼與內容修正
- `library/sources/traders/oliver-kell.md`——加碼止蝕範例(48/53 標錯)、階段數(五階段→六形態)、選股閘(收入增長25%誤植為 Kell 自設閘)
- `library/sources/traders/nomad-partnership.md`——Bezos 頁碼、「頭五年零回報」錯誤解讀

  `library/insights/moat-durability.md` 經核對後確認無需改動(對帳單列的相關項目未在此檔出現)。

  受影響判斷清單:`research/2026-09-methodology/2026-09-08-引用錯誤受影響判斷清單.md`——發現 `research/2026-09-methodology/2026-09-07-成功交易者心得對照四類注.md` 直接複述了 6 處錯誤內容(不只是透過提煉檔轉引),是本輪影響面最大的下游文件;另 KARST-178、KARST-179 兩張規格書票的機制草稿引用了受影響來源,但尚未落成正式 spec 檔案。全部標記「受影響、待重核」,未改動任何判斷本身。

  無法核實/保留不動的項目:doc②所列 O'Neil RS/EPS 均值當門檻、"trend is your friend" 誤植、200 日均線誤讀、O'Neil 高潮頂賣出規則等 4 項,經 Grep 全庫確認**未曾進入知識庫**(`mw-market-wizards.md` 本身已正確區分均值與門檻),故無需回改,已在受影響清單第四節註明查證過程。

## 留言

· 2026-09-08 15:00 收工留言:library 層 25 處對帳單錯誤已全數處置(實際約 32 處),受影響判斷清單已落檔。最需要用戶注意的一點:`2026-09-07-成功交易者心得對照四類注.md` 這份研究文件直接複述了 6 處錯誤內容(不只是透過提煉檔轉引),影響面比 library 內部大——是否要為這份文件另開一張回改票,舉手待用戶裁決。KARST-178/179 兩張規格書票的機制草稿都引用了受影響來源,但兩份 spec 都仍未落成正式檔案,建議動筆時直接採用回改後的引文,不需要再開更正票。
