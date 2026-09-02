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
raised: 代號重用要收到哪一層?只剔那 7 條拆股事件,還是連 427 格接錯公司的基本面一齊重建,並全面改用 entity_id 做主鍵?
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

### agent:data-gov-163 · 2026-09-03 02:08
代號重用全掃做完(data-gov-163)。誠實聲明:只出清單與報告 —— 面板 v2 一個位元不改(SHA256 首 16 位 ab02e335c3ebc169)、拆股事件表不改(82c2a2133d260e8f)、生產庫不寫、沒有重跑任何回測。這個倉沒有「代號歷史對照」的正本來源,所以「哪一家公司在哪一段時間用過這個代號」是由三份數據反推出來的:指數成分期、CIK 的申報期、公司名。四個訊號會出假陽性,我已經逐個人手核並在清單標明,但人手核靠的是我對這些公司的認識,不是查過的正本文件。受影響格數是那些代號在面板的全部格,不是逐格驗過真的錯了。

掃描範圍:1,001 條拆股事件、1,209 行宇宙代號對照、123,754 行帳目面板。四個獨立訊號:CIK 首次申報晚於代號加入指數、成分期內規模細得不合理、市值營收比荒謬、拆股事件在代號離場之後而且倍數 10 倍以上。命中 12 個代號。

人手核之後分三檔:確證代號重用 3 個 —— CPWR(對照表指到 CIK 0000827099 = Ocean Thermal Energy,不是 Compuware)、EP(0000887396 = Empire Petroleum,不是 El Paso)、PARA(0001826011 = Banzai International,不是 Paramount Global),面板共 427 格。訊號假陽性 3 個 —— NKTR、NBR、ERIE,都是同一家公司自己做的拆股,代號離開指數之後原公司自己的拆股照樣要算,R4 單獨用會冤枉好人。嫌疑要人手核 6 個 —— SUN(Sunoco Inc 對 Sunoco LP,同品牌不同法律實體)、COV、MEE、RAI、RTN、WRK,共通形狀是公司被收購或合併,代號的後續生命屬於另一個法律實體。

三個確證的證據是三重獨立的:SEC 的 CIK 名冊查得出那個 CIK 的全部曾用名;yfinance 今日給這三個代號的公司名與 SEC 一致(兩個來源都認同代號已易主);面板算出的規模荒謬 —— CPWR 成分期市值中位數只有 784 萬美元,PARA 市值中位數 37.5 億美元而營收中位數只有 456 萬美元。

拆股修補清單 12 條事件:建議剔走 7 條(CPWR 2017-03-28 的 1:250 與 2017-05-25、EP 2013-08-12 的 1:12 與 2022-03-08、PARA 2024/2025/2026 三次反向拆股 —— Paramount Global 由 2022 至 2025 從未做過反向拆股),保留 5 條。已知被下游用到的污染面板格 7 格(scale_flags_mcap.csv);受影響的十倍股名單 4 行(CPWR、EP 各佔三年窗與五年窗),十倍股盤點第 1.5 節前二十名裡 EP 124 倍排第三、CPWR 97 倍排第八。

比票上寫的更嚴重的一件事:壞的不只是拆股基準。data/sec/company_tickers.json 是 2026-09-02 當日快照、沒有歷史,面板按代號 join 上去拿到的是今日那家公司的 XBRL,再乘上前一家公司的價格 —— 基本面本身也接錯了公司。那 427 格要重建,不是只修那 7 格。順帶一提,2026-08-30 到 09-02 三日之內就有 99 個對照變過。

建議主鍵:entity_id,代號降格為帶時段的別名。生產線 karst/data/freeze.py 的 ensure_entities、_ensure_ticker_period(代號在起訖兩日解析到不同實體就掟 TickerRecycled)、resolve_entity_ids(註釋原話:丟掉代號是刻意的,落地之後就再沒有一條路可以用代號當主鍵)已經把這套寫好,生產庫的 entity + entity_ticker 兩張表就是落地。問題不是缺機制,是實驗線全部繞過了它。

報告 experiments/2026-09-03-ticker-reuse/代號重用修補清單與主鍵方案.md(票上寫的檔名是 REPORT.md,實際檔名不同,內容照三項要求寫齊);清單 out/ticker_reuse.csv 與 out/split_fixes_proposed.csv,另六個底稿檔與六支掃描腳本同目錄。commit 932a033。生產庫 SHA256 首 16 位 b168e9f45b578cf9,維持不變。

### agent:data-gov-163 · 2026-09-03 02:08
**問題**：代號重用要收到哪一層?只剔那 7 條拆股事件,還是連 427 格接錯公司的基本面一齊重建,並全面改用 entity_id 做主鍵?

**前文後理**：掃描確證三個代號接錯了公司:CPWR 的對照表指到 Ocean Thermal Energy(不是 Compuware)、EP 指到 Empire Petroleum(不是 El Paso)、PARA 指到 Banzai International(不是 Paramount Global)。發現的過程揭出一件比原本以為更嚴重的事:壞的不只是拆股基準。data/sec/company_tickers.json 是當日快照、沒有歷史,面板按代號 join 上去拿到的是今日那家公司的 XBRL 數據,再乘上前一家公司的價格,所以基本面本身也接錯了公司 —— 那 427 格要重建,不是只修已知那 7 格。另有 6 個嫌疑代號(SUN、COV、MEE、RAI、RTN、WRK)形狀是公司被收購合併、代號的後續生命屬於另一個法律實體,要人手核。受影響的十倍股名單有 4 行(EP 排前二十第三、CPWR 排第八),該文已自行標註兩者是污染格並說剔走後基礎率幾乎不動,所以結論不用改,但名單本身要標死。

**建議**：我押最徹底那一條:全面改用 entity_id,代號降格為帶時段的別名。理由是這三張票撞到的是同一件事的三個面 —— KARST-163 撞到雙重股權(一家公司兩個代號)、KARST-164 撞到代號改名 FISV→FI 與同一家公司兩份價格、KARST-165 撞到代號重用(一個代號兩家公司)。三件事都是「代號不是穩定識別碼」的推論,而生產線八月已經把正確答案寫進 karst/data/freeze.py 與 entity、entity_ticker 兩張表,連代號被回收的例外 TickerRecycled 都寫好了。現在補一補拆股表、下次補一補面板,只會第四次第五次再撞。反對這條路的理由我也要誠實講:全面改用 entity_id 之後所有實驗腳本都要經一支解析函數才拿得到數,寫實驗會慢;而且 entity_ticker 的歷史要靠人手補(這個倉沒有代號歷史的正本來源),補得不全反而會令解析失敗、腳本掟例外。這是真代價。

**選項**：
- 甲（建議）：全面改:entity_id 做主鍵,代號降格為帶時段別名。補齊 entity_ticker 的退役日、拆股表加 entity_id 欄並剔走 7 條、重建 3 個確證代號的 427 格面板、下游(面板、十倍股盤點、鏈表 ticker 欄、價格表)逐個跟改 —— 一次過解決三張票撞到的同一件事,而且生產線的機制已經寫好只是沒人用;代價是實驗腳本要經解析函數、entity_ticker 歷史要人手補
- 乙：中度:只做拆股表加 entity_id 並剔走 7 條,再重建那 427 格面板;下游繼續用代號做鍵,但在 universe_cik.csv 加一張代號生效期表供查 —— 把已知的污染修乾淨,工作量約一至兩日,不動架構;代價是代號仍然是主鍵,下一個未發現的重用代號照樣會咬
- 丙：最小:只剔走 7 條拆股事件與標死 4 行十倍股名單,427 格面板照舊,主鍵不動 —— 半日做完,把已知被下游用到的 7 格污染止住;代價是那 427 格的基本面繼續是別家公司的數,而且沒有人知道它們正在被哪張票讀

**要睇邊份稿**：
- experiments/2026-09-03-ticker-reuse/代號重用修補清單與主鍵方案.md
