---
id: KARST-165
title: 拆股事件表代號重用污染修補(KARST-158 遺留):CPWR/EP/PARA 等代號被不同公司先後使用,拆股事件表按代號索引令舊公司的拆股套到新公司(共 7 格已知);改以 CIK 為主鍵,列出全部受影響代號與格,重跑受影響面板格核對,面板 v2 不改只出修補清單
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: data-gov-163
deliverable: KARST-D02
---

## 工作內容

背景:A-041 修補紀錄(KARST-158)指出「拆股事件表按代號索引而代號會被重用(CPWR/EP/PARA 共 7 格),屬拆股基準層,建議另開票」;KARST-160 又發現 CPWR 與 EP 是十倍股名單裡的污染格(代號重用令兩家公司的價格序列被接成一條)。先讀 experiments/2026-09-02-panel-scale-fix/(RULES、scale_fixes.csv、README 提到拆股事件表的位置)、research/2026-09-02-十倍股盤點.md 第 1.5 節與 RULES v2 第九節、data/sec/company_tickers.json 與 cik-lookup-data.txt。做法:①找出拆股事件表與價格序列的主鍵現況;②用 SEC 的 CIK 對照(company_tickers.json、submissions/)逐個代號查是否曾屬多於一個 CIK,列全部重用代號連時段;③對每個重用代號,判定拆股事件與價格段各屬哪個 CIK,寫出修補清單(代號、日期段、正確 CIK、受影響面板格數、受影響的十倍股名單行);④不改 panel_monthly_v2.parquet、不改生產庫;修補清單與建議主鍵方案(CIK+代號+時段)落 experiments/2026-09-03-ticker-reuse/out/ 與 REPORT.md;⑤估算若採 CIK 主鍵,哪些下游(面板、十倍股盤點、鏈表 v1/v2 的 ticker 欄)要跟着改,在票上 raise。

## 驗收條件

- [ ] 全部代號重用清單(代號、各 CIK、時段)落 out/ticker_reuse.csv;已知的 CPWR/EP/PARA 必須在內
- [ ] 修補清單 out/split_fixes_proposed.csv:每格附正確 CIK 與理由;受影響的十倍股名單行標出
- [ ] REPORT.md 建議主鍵方案與下游影響;票上 raise;面板 v2、生產庫一個位元不改,SHA256 首 16 位維持 b168e9f45b578cf9
- [ ] commit 用 git commit --only -F <訊息檔> -- <自己的檔>

## 結果

· 2026-09-03 03:00 代號重用全掃 + 修補清單 + 主鍵方案寫完(data-gov-163)

**做了什麼**:掃 1,001 條拆股事件、1,209 行宇宙代號對照、123,754 行帳目面板,用四個獨立
訊號找接錯公司的格,逐個人手核;出代號重用清單、拆股修補清單、主鍵方案與下游影響表。
報告落 `experiments/2026-09-03-ticker-reuse/代號重用修補清單與主鍵方案.md`(票上寫的檔名是
`REPORT.md`,實際檔名不同,內容照三項要求寫齊),六支掃描腳本與八個結果檔同目錄。

**沒有做**:面板 v2 一個位元不改(SHA256 首 16 位 `ab02e335c3ebc169`)、拆股事件表不改
(`82c2a2133d260e8f`)、生產庫不寫、沒有重跑回測。

數字:

- 命中至少一個訊號的代號 12 個。人手核後:**確證代號重用 3 個**(CPWR、EP、PARA,
  面板共 **427 格**)、訊號假陽性同一家公司 3 個(NKTR、NBR、ERIE)、嫌疑要人手核 6 個
  (SUN、COV、MEE、RAI、RTN、WRK)。
- 三個確證的證據是三重獨立的:SEC 名冊查得出 CIK 0000827099 是 Ocean Thermal Energy
  (不是 Compuware)、0000887396 是 Empire Petroleum(不是 El Paso)、0001826011 是
  Banzai International(不是 Paramount Global);yfinance 今日的公司名與 SEC 一致;
  面板算出的規模荒謬(CPWR 成分期市值中位數 784 萬美元;PARA 市值 37.5 億美元配營收 456 萬)。
- 拆股修補清單 12 條事件:**建議剔走 7 條**(CPWR 2、EP 2、PARA 3),保留 5 條
  (同一家公司自己的拆股)。
- 已知被污染的面板格 7 格(scale_flags_mcap.csv);受影響的十倍股名單行 4 行
  (CPWR、EP 各佔三年窗與五年窗),十倍股盤點第 1.5 節前二十名裡 EP 排第三、CPWR 排第八。
- **比票上寫的更嚴重的一件事**:壞的不只是拆股基準。`data/sec/company_tickers.json` 是
  2026-09-02 當日快照、沒有歷史,面板按代號 join 上去拿到的是今日那家公司的 XBRL,
  再乘前一家公司的價格——**基本面本身也接錯了公司**。那 427 格要重建,不是只修 7 格。
- 生產庫 SHA256 首 16 位:`b168e9f45b578cf9`(維持不變)。

建議主鍵:`entity_id`,代號降格為帶時段的別名。生產線 `karst/data/freeze.py` 的
`ensure_entities` / `_ensure_ticker_period` / `resolve_entity_ids` 已經把這套寫好,
`entity` + `entity_ticker` 兩張表就是落地——問題不是缺機制,是實驗線全部繞過了它。
已在票上 raise 交裁。

## 留言
