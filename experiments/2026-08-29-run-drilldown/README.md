# 運行詳情鑽取層核對(D-035,KARST-078)

> 跑法(倉根目錄,另開一個背景程序常駐):
> ```
> set PYTHONUTF8=1
> set PYTHONPATH=.
> python experiments/2026-08-29-run-drilldown/serve_temp.py 8768
> ```
> 再用真正的瀏覽器引擎(headless Chrome,`--dump-dom` 取 JS 執行完畢後的
> DOM、`--screenshot` 取畫面)打三頁——不是只讀原始碼推斷行為。`dom/` 底下
> 是逐頁的完整渲染後 DOM,`screenshot-*.png` 是實際畫面截圖。核對完已經
> `TaskStop` 收工那個 server,倉內不留常駐程序。

## 一句話

**三頁頂層導覽都只剩三項(策略總覽/策略詳情/參數掃描),運行詳情頁不再有
自己的運行選擇器,唯一入口是策略詳情頁的歷次運行表(或者直連網址);
`?run=` 不帶 `?id=` 一樣反查得到正確那套策略,麵包屑一樣「策略詳情 ›
<策略名> › 運行」。**

## 核對了什麼、在哪裡看得到

| 核對點 | 憑據 |
|---|---|
| 頂層導覽三項,不見「運行詳情」 | `dom/overview.html` 第 10 行:`<nav class="nav">` 底下 `nav-links` 只有 `/`、`/strategy`、`/sweep` 三個 `<a>`,`screenshot-overview.png` 同一樣 |
| 策略詳情歷次運行表每行連得到運行詳情,帶 `?id=&run=` | `dom/strategy-rotation.html`(策略「因子輪動(ETF 版)」):`href="/run?id=3&run=run-924a54eb843f0988"` |
| 運行詳情頁頂麵包屑「策略詳情 › <策略名> › 運行」,策略名連得回策略頁 | `dom/run.html`:`<nav class="breadcrumb" ...><span>策略詳情</span><span>／</span><a href="/strategy?id=...">因子輪動(ETF 版)</a><span>／</span><span aria-current="page">運行</span></nav>`;`screenshot-run.png` 同一樣 |
| 運行詳情頁不再有運行選擇器(D-035,用戶原話見下) | `dom/run.html` 第 70–75 行只有一段註解交代拆走原因,DOM 內文再搜不到任何運行選擇按鈕;`screenshot-run.png` 頁頂只有「以現版本重跑」一個按鈕 |
| 只帶 `?run=`(不帶 `?id=`)一樣顯示正確那套策略 | `dom/run-runonly.html`:`http://127.0.0.1:8768/run?run=run-924a54eb843f0988` 渲染出同一句麵包屑,身份晶片同樣是「因子輪動(ETF 版)」 |
| D-034/D-040 的「全部運行失敗」邊界情況(附帶驗一次,與 KARST-077 共用同一個 server) | `screenshot-strategy-allfailed.png`(策略「趨勢波段」):歷次運行表顯示「7 條運行全部失敗(年化回報同時低於 SPY 與 QQQ 買入持有)。」,不是「此策略未有正式運行」那句;頁頂身份、圖表、選股快照仍照常畫得出(用最近一次運行的產物,不因為它是失敗運行而整頁空白) |

## D-035 這一票的中途改動(留一句在此,票上留言已另記)

原工作內容第 (2) 項寫「運行選擇器保留在運行頁內但只列同一策略的正式運行」,
中途改為**整個拆走**,不是過濾——用戶原話:「檢視運行 bar is not useful
again if I have thousands of run for this strategy」。上面「運行詳情頁不再
有運行選擇器」那一列核對的就是這件事:策略詳情頁本身仍有頁頂選擇列(見
KARST-067 既有設計),但運行詳情頁(`run-view.js`)那一份已經整份拆走。

## 這個核對法為什麼算數

Headless Chrome 是與用戶實際用的同一個瀏覽器引擎,`--dump-dom` 取的是
JavaScript 全部執行完畢之後的 DOM(不是伺服器吐出的原始 HTML),所以能
驗到 `app.js`/`strategy.js`/`run-view.js` 真的照這樣渲染,不只是原始碼
寫成這樣——與人手在瀏覽器打開這幾頁看到的東西一致。
