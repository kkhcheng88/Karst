---
id: KARST-124
title: 板塊倍數每日存檔件:一句命令抓九隻 SPDR + SPY 前瞻市盈率落 append-only 版本存檔,即日起每日累積(D-084)
type: task
createdAt: 2026-08-31
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: agent-karst-124
deliverable: KARST-D02
closed: 2026-08-31
---

## 工作內容

落實 D-084 第 1 項。完成之後有咩係之前做唔到:平台從此每日留得低「今日市場肯畀邊個板塊幾多倍」的當日紀錄,日積月累成為自家 point-in-time 前瞻倍數序列——呢樣嘢冇任何免費來源肯畀歷史,唯有自己由今日起儲(KARST-121 勘察結論,來源與欄位細節見 research/2026-08-31-倍數數據勘察.md 的 SPDR 發行商一節)。行為:唯一入口 CLI 新增一句命令,抓九隻 SPDR 板塊 ETF + SPY 發行商公布的前瞻市盈率(及同頁順手可得的後顧市盈率、市淨率一類估值欄位,有幾多攞幾多但不強求),連抓取時間戳與來源網址寫入 append-only 存檔(形態跟倉內既有快照/vintage 慣例,詞彙表「數據版本存檔/vintage」);同日重跑冪等(同日第二次抓到不同數字就兩條都留,以時間戳分辨,不覆蓋);來源改版抓唔到欄位時要響亮失敗並講明邊個欄位斷咗,不准靜靜寫空值。存檔可由 CLI 讀返出嚟列成表。首次實抓一次做冒煙證據,結果與過程落 experiments/2026-08-31-multiple-capture/README.md。排程本票不做(人手/日後接現有排程另計),但 README 要寫明「每日跑一次」的操作句。

## 驗收條件

- [x] 唯一入口一句命令抓齊十隻 ETF 的前瞻市盈率落 append-only 存檔,連時間戳與來源網址;同日重跑冪等有測試
- [x] 欄位斷纜響亮失敗有測試(模擬來源缺欄位);不寫空值
- [x] CLI 讀得返存檔列成表;首次實抓證據落 experiments/2026-08-31-multiple-capture/README.md,含每日操作一句
- [x] 只跑所涉測試檔;生產庫雜湊不變(存檔屬新檔,不動既有庫)

## 結果

**一句命令**:`python -m karst.gateway multiples capture`(每日跑一次;同日重跑安全)。
讀回:`python -m karst.gateway multiples list`,或 `... list --symbol XLK` 看某一隻的逐次讀數。

**首次實抓**(2026-08-31 14:38 UTC,十二隻全過零失敗,發行商自報截數日 2026-08-28):
SPY 21.36、XLB 18.29、XLC 12.88、XLE 12.53、XLF 16.21、XLI 25.37、XLK 26.03、
XLP 20.16、XLRE 36.05、XLU 17.74、XLV 20.41、XLY 23.42(前瞻市盈率 FY1)。
同日第二次跑,十二隻全報「同日不變」、零新列——冪等在真存檔上驗過。

**來源**:State Street 官網基金頁面(`https://www.ssga.com/us/en/intermediary/etfs/<基金名連代號>`),
伺服器直出 HTML、免費、不用鑰匙。每隻取八格:前瞻市盈率 FY1、後顧市盈率、市現率、市帳率、
三至五年每股盈利增長預估、指數與基金兩個成分數、加權平均市值,連兩節各自的發行商自報截數日。
截數日通常是抓取日前一個交易日(知情滯後 T+1);**日後回測對齊用截數日,不是抓取日。**

**落點**:`vintage/sector-multiples/readings.csv`(存檔正本,17 欄,**入 git**)、
同目錄 `說明.md`、`raw/<抓取編號>/<代號>.html.gz`(原始頁面,不入 git)。
正本刻意不放 `data/`:倉根 `/data/` 被 `.gitignore` 擋走的理由是「可重抓的數據」,
而這一份性質相反——今日不抄以後補不回,只住在一部機上等於隨時歸零。

**四條規矩**:追加式(舊列一字不動);同日冪等(數字全同不寫,數字變了兩列都留,以時間戳分辨);
不寫空值(任何一格抓不到即整隻不收、講明斷了哪一節哪一欄、回傳碼非零,其餘代號照寫);
原始頁面先落檔後解析(解析失敗那一日的頁面仍在,修好解析器由存檔重跑補得回)。

**與票面不同的一項**:票與 D-084 寫「九隻 + SPY」共十隻,實作抓十二隻——多了 XLRE 與 XLC,
即倉內 `SECTOR_ETF_UNIVERSE` 本來就有的十一隻連 SPY。理由:漏了這兩隻,日後板塊計分要用全套
倍數時那兩格會永遠空白,而多抓的成本是零;票點名那十隻全部在內,是超集不是替換。
若日後裁定只要十隻,由存檔剔走兩隻隨時做得到;反過來補不回。

**測試**:`tests/test_multiples_vintage.py` 15 條(含一條真實抓取,離線即 skip);
連受影響的 `tests/test_gateway.py`、`test_gateway_data.py`、`test_gateway_governance.py`,
合共 33 條全過。`karst.sqlite` 雜湊由頭到尾 `b168e9f4…75fa8` 不變——這句命令按設計連定義庫
都不開(攔在 `Gateway.open` 之前),有一條測試專門守住。

**落檔**:`karst/data/multiples.py`(新)、`karst/gateway/cli.py`(加 `multiples` 兩句)、
`tests/test_multiples_vintage.py`、`tests/frozen/karst-124-ssga-xlk-2026-08-31.html`(實抓證據,
逐字不改)、`experiments/2026-08-31-multiple-capture/README.md`、`.gitignore`(擋 raw)。

**新記一條假設 A-021**:發行商 FY1 的計算口徑不會靜靜改。今日頁面浮框明文「離群值全部計入」
(即不像 iShares 那樣把市盈率壓到 60),但發行商無口徑變更紀錄、無官方版本存檔可對數。
若為假,自儲序列會在事後查不出的日子出現口徑斷點,一切倍數基判準要重做。
查證途徑已內建:原始頁面逐日留底,浮框原文比對得到。

**未做**:排程(本票明文不做,接的時候接上面那一句);月度對照發行商季度 PDF 概覽的驗證
(勘察建議的第二重驗證,要做另開票);EDGAR 自砌後顧倍數(D-084 第 2 項,另有票)。

## 留言

### agent:agent-karst-124 · 2026-08-31 22:43
做完:`python -m karst.gateway multiples capture` 一句抓齊十二隻(票點名那十隻全在內,多了 XLRE 與 XLC,理由見結果一節),首次實抓 2026-08-31 全過零失敗、同日重跑報「同日不變」零新列,存檔正本 `vintage/sector-multiples/readings.csv` 追加式入 git,原始頁面留底不入 git;斷纜響亮失敗、不寫空值;測試 15 條連受影響的 gateway 三檔共 33 條全過,生產庫雜湊不變(這句命令按設計連定義庫都不開)。另記假設 A-021(發行商 FY1 口徑不會靜靜改)。
