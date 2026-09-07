# 策略詳情頁重組核對(D-036,KARST-079)

> 跑法(倉根目錄,另開一個背景程序常駐):
> ```
> set PYTHONUTF8=1
> set PYTHONPATH=.
> python experiments/2026-08-29-strategy-page-restructure/serve_temp.py 8767
> ```
> 再用真正的瀏覽器引擎(headless Chrome,`--dump-dom` 取 JS 執行完畢後的
> DOM、`--screenshot` 取畫面)打幾頁——不是只讀原始碼推斷行為。核對完已經
> 收工那個 server(kill 對應 PID),倉內不留常駐程序。
>
> 一個技術細節記在這裡免得下一個人再撞一次:`--dump-dom` 只等到 `load`
> 事件,頁面的資料是 `fetch()` 之後才填,所以要加
> `--virtual-time-budget=6000` 才等得到非同步內容落地;另外本機常駐有多個
> 已開的 Chrome,預設 profile 會鎖檔造成 headless 卡死,要另外指
> `--user-data-dir` 開一個獨立 profile。

## 一句話

**策略詳情頁四段固定次序落地:門面成績(含選股快照/漏斗,原位不動)→
熱力圖帶(每個掃描一條,最佳格與代表格並排,無掃描顯示「尚無參數掃描」)→
歷次運行表(照 D-034 隱藏失敗運行)→ 因子分布(暫留原位待 080)。點熱力圖
一格直達參數掃描頁的單格曲線,帶正確的 `?id=&sweep=&layer=&cell=`,麵包屑
「策略詳情 › <策略名> › 掃描 <名> › 格」。頂層導覽剩兩項(策略總覽/策略
詳情),參數掃描與運行詳情仍是直連得到的頁面,只是不再上頂列。**

## 核對了什麼、在哪裡看得到

| 核對點 | 憑據 |
|---|---|
| 策略詳情頁四段次序(門面成績→熱力圖帶→歷次運行→因子分布) | `screenshot-strategy-s3.png`(策略「因子輪動(ETF 版)」,id=3):由上而下依次是頭條數字/淨值圖+選股快照、「參數掃描」熱力圖帶(20 個掃描)、「歷次運行」表、「因子分布」;`dom/strategy-3.html` 同一個次序 |
| 熱力圖帶標最佳格與代表格 | `dom/strategy-3.html` 的 `id="heatband-body"`:每條掃描帶內 `<i class="cell-mark best">最佳</i>` 與 `<i class="cell-mark rep">代表</i>` 並列,例如 dense-factor_momentum 帶第 8 格(`data-i="7"`)標「最佳」、第 4 格標「代表」 |
| 無參數掃描的策略顯示「尚無參數掃描」 | `screenshot-strategy-empty.png`(策略「趨勢波段」,id=2,同時也是 D-034 全部運行失敗的邊界情況):「參數掃描」段落只有一行「尚無參數掃描」;`dom/strategy-2-nosweeps.html` 的 `id="heatband-body"` 內文正是 `<div class="sp-empty">尚無參數掃描</div>` |
| 點熱力圖一格直達單格曲線,帶正確 URL | 由策略頁「最佳格」那格(`data-sweep="experiments/2026-08-28-costs-and-regrid/results/dense-factor_momentum"`、`data-layer="mode=winner、cadence=monthly"`、`data-i="7"`)反推點擊會導向的 URL `/sweep?id=因子輪動(ETF 版)&sweep=...&layer=...&cell=7`,直接打開後核對:`dom/sweep-cell.html` 的熱力圖第 8 格(`data-r="0" data-c="7"`)`aria-pressed="true"`,右欄「參數組詳情」顯示 `lookback_months 8、mode winner、cadence monthly`,與策略頁那一格的參數完全對得上;`screenshot-sweep-cell.png` 同一樣(該格描邊、右欄曲線與數字對齊) |
| 麵包屑「策略詳情 › <策略名> › 掃描 <名> › 格」 | `dom/sweep-cell.html`:`<nav id="bc-crumb">` 內文「策略詳情／因子輪動(ETF 版)／掃描 dense-factor_momentum／格」,策略名連得回 `/strategy?id=...`;截圖同一樣 |
| 頂層導覽剩兩項,不見「參數掃描」「運行詳情」 | `dom/overview.html`、`dom/strategy-3.html`、`dom/sweep-cell.html`、`dom/run-direct.html`、`dom/sweep-list.html` 的 `id="nav-host"` 底下 `nav-links` 全部只有 `/`(策略總覽)、`/strategy`(策略詳情)兩個 `<a>` |
| 參數掃描頁、運行詳情頁都把「策略詳情」點亮為目前導覽項 | 同上幾個 DOM:`/sweep` 與 `/run` 頁面裡 `<a class="nav-link" href="/strategy" aria-current="page">` |
| 直連網址仍然行得通,不靠策略頁才到得了 | `dom/sweep-list.html`:直連 `/sweep`(不帶任何參數)照樣顯示掃描清單(22 次掃描・4708 格),麵包屑退回兩段式「策略總覽／參數掃描」;`dom/run-direct.html`:直連 `/run?id=3&run=run-924a54eb843f0988` 照樣顯示運行詳情,麵包屑「策略詳情／因子輪動(ETF 版)／運行」——這兩頁的行為都是 KARST-077/078 已落地的,本票沒有動它,這裡只是確認重組導覽之後沒有連帶弄壞 |
| D-034/D-040 全部運行失敗的邊界情況(附帶再驗一次) | `screenshot-strategy-empty.png`:「歷次運行」段落只有一行「7 條運行全部失敗(年化回報同時低於 SPY 與 QQQ 買入持有)。」,頁頂身績、圖表、選股快照仍照常畫得出(用最近一次運行的產物) |

## 這一票裡一個沒有寫在票面、由我判斷落地的地方

票面工作內容 (1) 按抽象次序列出四段:門面成績→熱力圖帶→正式運行表→選股
漏斗,字面上像是要把「選股漏斗」搬到全頁最後、與現有淨值圖拆開。但
`.kira/decisions.md` D-037(本票明文列為不做、留給 KARST-080)寫的次序是
「門面成績 → 熱力圖帶 → 歷次運行(排名)+ 持股分布 → 選股漏斗(補充
D-036)」,「補充 D-036」四個字讀成:選股漏斗真正搬到最後、與新的「持股
分布」配對,是 D-037/KARST-080 那一步要做的事,不是本票。加上票面自己提
醒「你改頁面結構時不要把它做不了」與「因子分布段暫留原位不動(080 會
改)」——兩句合起來看,像是要我只加熱力圖帶這一段,不要動選股漏斗現在的
位置(它現在跟淨值圖並排,是「選股快照」面板的一部分)。

所以這一票只在「淨值圖+選股快照」與「歷次運行」之間插入新的熱力圖帶,
選股漏斗維持原位,沒有搬到頁尾。這是我自己的判斷,不是用戶確認過的決
定,已經在票上用 `raised` 留言分四格記低,讓用戶或者接手 080 的人審。

## 這個核對法為什麼算數

Headless Chrome 是與用戶實際用的同一個瀏覽器引擎,`--dump-dom`/
`--screenshot` 取的都是 JavaScript 全部執行完畢之後的畫面,不是伺服器吐
出的原始 HTML,所以能驗到 `app.js`/`strategy.js`/`sweep.js`/`run-view.js`
真的照這樣渲染、真的接得上——與人手在瀏覽器打開這幾頁看到的東西一致。
