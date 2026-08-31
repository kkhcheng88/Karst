---
id: KARST-130
title: 每日在外股數存檔件(SSGA 十二隻 ETF):富途反推線 2020 前係凍結分母(KARST-128/D-094),真流歷史只六年半,自儲遲一日蝕一日——與 D-086 倍數存檔同型,先查已存原始頁有冇現成欄位可回填
type: task
createdAt: 2026-09-01
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: karst-130-agent
deliverable: KARST-D02
---

## 工作內容

完成之後做到而家做唔到嘅事:平台每日儲低 SPY + 十一隻 SPDR 板塊 ETF 嘅在外股數(基金單位數)一格 vintage 正本,由今日起逐日累積,將來申贖流線重考就有一條唔靠富途反推嘅乾淨流數據。背景:KARST-128 考出富途反推線 2020-01 之前係凍結分母,真流歷史只六年半唔夠次數關,申贖流判「量不出」(D-094),自儲遲一日蝕一日。行為要求:與現有板塊倍數存檔件同型——原始頁面先落檔後解析、抓取時間與發行商自報截數日兩欄齊、同日重跑冪等(同日不變唔寫新列)、日課一句話跑得起。第一步先查現有倍數存檔已儲低嘅原始頁面入面係咪已經有在外股數/單位數欄位:有就擴解析兼由既有原始頁回填;冇先另抓發行商基金頁(禮貌節奏,勿觸發封鎖)。純存檔件,不落任何策略結論。

## 驗收條件

- [x] 命令跑得,十二隻齊,同日重跑冪等;原始頁面先落檔後解析;抓取時間與截數日兩欄齊
- [x] 已存 raw 頁若有此欄位,由 2026-08-31 起回填;冇就明寫查過乜、點解冇
- [x] HANDOFF 日課句更新;生產庫雜湊不變;大檔不入 git

## 結果

由今日起,平台每日儲低 SPY 連十一隻 SPDR 板塊 ETF 的在外股數(發行商自報的基金單位數),
落 `vintage/fund-shares/` 一格追加式版本存檔。單位數的每日變化就是申贖流,所以這條線一年之後
就是一條不用靠富途成交量÷換手率反推、亦沒有 2020 前凍結分母問題(D-094)的乾淨流數據。

**日課兩句命令**(先設 `PYTHONUTF8=1`,在倉根順序跑;已寫入 HANDOFF 第三節第 6 項):

```
python -m karst.gateway multiples capture   # 板塊前瞻倍數 → vintage/sector-multiples/
python -m karst.gateway shares capture      # 十二隻在外股數 → vintage/fund-shares/
```

另有 `shares list`(讀回存檔;加 `--symbol XLK` 看該隻逐次讀數,兩列之差即淨申贖)與
`shares backfill`(由已落檔原始頁面補,一個網都不出)。逐隻之間停一秒是禮貌節奏,全條約十幾秒。

**首日存檔證據**:正本 `vintage/fund-shares/readings.csv` 在 2026-08-31(UTC)有十二列、
十二隻齊,每列抓取時間 `captured_at_utc` 與發行商自報截數日 `nav_as_of`(2026-08-28)兩欄齊。
每隻存三格:`shares_outstanding_m`(百萬股,主角)、`nav_usd`、`aum_musd`——三格一齊存是因為
「單位數 × NAV ≈ 資產淨值」本身就是一條免費自檢。SPY 1058.53、XLB 164.40、XLC 200.80、
XLE 648.50、XLF 944.45、XLI 183.18、XLK 651.66、XLP 171.02、XLRE 187.95、XLU 515.30、
XLV 258.17、XLY 195.56(百萬股)。原始頁面**先落檔後解析**:`raw/20260831T174513Z/` 十二個
`.html.gz`,即使解析當場斷了,那一日的頁面仍然留得住;raw 目錄由 `.gitignore` 第 15 行
`/vintage/*/raw/` 擋走不入 git,正本 CSV 與說明檔入 git。**同日重跑冪等已在真存檔上驗過**:
回填寫入十二列之後即時真抓一次(20260831T174513Z),十二隻全報「同日不變」、新寫零列——
跨命令都不會重覆寫。

**回填:做到了。** 第一步查已存的 SSGA 原始頁面,發現**本來就有現成欄位**:
`vintage/sector-multiples/raw/` 由 2026-08-31 起存低的三次原始頁面,每張都有
「Fund Net Asset Value」一節,載 `NAV` / `Shares Outstanding` / `Assets Under Management`
連自報截數日。所以不用另抓發行商頁,直接擴解析並回填:`shares backfill` 由那三次原始頁面
補回十二列(第二三次同日數字一樣,冪等擋住)。回填列的 `captured_at_utc` 是**當日真正抓那張
頁面那一刻**,不是回填那一刻;`raw_file` 指回 `../sector-multiples/raw/...` 原證據本身,
不再複製一份頁面。**但要講清楚一件事**:那三次原始頁面的截數日全部是 2026-08-28,
即回填得回的是**一個**時點,不是三個。真正的逐日序列由今日起才開始累積。

**落檔**:`karst/data/fund_shares.py`(新,存檔件本體:解析、追加、冪等、回填,重用
`multiples.py` 的抓取與版式零件)、`karst/gateway/cli.py`(加 `shares` 三句命令)、
`karst/data/__init__.py`(匯出)、`tests/test_fund_shares_vintage.py`(驗收測試 17 條)、
`tests/frozen/karst-130-ssga-xlk-nav-2026-08-31.html`(凍結樣本,由實抓頁面逐字抽出,不是手砌)、
`vintage/fund-shares/readings.csv` 與 `說明.md`(存檔正本與說明)。

**驗證**:`tests/test_fund_shares_vintage.py` 十七條全過、零 skipped(含真連網實抓那條)。
全套 `pytest` 429 passed、7 skipped,那七條 skip 全部是本票以外的舊有 skip。`ruff check`
三個新改檔零警告(倉內另有 26 條 F401 屬不相關舊檔,不在本票範圍)。**生產庫雜湊不變**:
`shares` 與 `multiples` 一樣攔在 `Gateway.open` **之前**,連庫都不開,
`karst.sqlite` 仍然是 `b168e9f4…75fa8`(與 KARST-124 收檔時記的同一個);
`test_cli_shares_never_opens_the_definition_store` 一條專測這件事。

**一個判斷,寫明是誰做的**:不把新欄加落板塊倍數那份 CSV,另開一份存檔——**主 agent 定案**
(不是用戶裁決)。理由兩條:一,追加式存檔的規矩是「舊列一個字都不動」,而加欄就要改寫已經
寫下去的歷史列;二,兩節解析各自獨立,一邊斷了另一邊照樣儲得到。代價是同一張頁面一日抓兩次
(共 24 個請求),已加禮貌節奏逐隻停一秒。

**詞彙表已加一條**:「在外股數 / shares outstanding」(`CONTEXT.md`)。倉內原本有兩個中文
叫法——「在外股數」與 `申贖流` 條目寫的「在外單位數」——指同一樣東西,當場對齊,
新文件一律寫「在外股數」。

## 留言
