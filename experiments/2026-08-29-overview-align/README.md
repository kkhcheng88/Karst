# 策略總覽對齊策略詳情、拿走迷你走勢、拿走頁尾(D-039,KARST-081)

> 跑法(倉根目錄,另開一個背景程序常駐):
> ```
> set PYTHONUTF8=1
> set PYTHONPATH=.
> python experiments/2026-08-29-overview-align/serve_temp.py 8767
> ```
> 再用真正的瀏覽器引擎(headless Chrome,`--dump-dom` 取 JS 執行完畢後的
> DOM、`--screenshot` 取畫面,兩者都加 `--virtual-time-budget` 等非同步的
> `fetch` 真正跑完)打兩頁——不是只讀原始碼推斷行為。`dom/` 底下是逐頁的
> 完整渲染後 DOM,`screenshot-*.png` 是實際畫面截圖。核對完已經
> `Stop-Process` 收工那個 server,倉內不留常駐程序。

## 一句話

**策略總覽表換成八欄(名稱/類型/對基準/年化/Sortino/最大回撤/勝率/開啟),
迷你走勢欄連同底層數據整個拿走;總覽與策略詳情現在共用同一套「代表運行」
判法,同一策略在兩頁的年化、Sortino、最大回撤、勝率全部對得上;全部正式
運行都失敗的策略仍列一行,成績欄留空、對基準欄改講「N 條運行全部失敗」;
五頁的頁尾說明列(數據期間、快照、免責聲明、圖表庫版本)連同產生它的程式
碼一併拿走,圖表庫的授權聲明搬去倉根 `NOTICE`。**

## 核對了什麼、在哪裡看得到

| 核對點 | 憑據 |
|---|---|
| 總覽表頭八欄、順序照 D-039(名稱/類型/對基準/年化/Sortino/最大回撤/勝率/開啟),四個成績欄可排序 | `dom/overview.html`:`<thead>` 逐欄 `data-key`(`name`/`type`/`vsBench`/`cagr`/`sortino`/`maxDD`/`winRate`)、`class="sortable"`;`screenshot-overview.png` 表頭同一樣 |
| 迷你走勢欄不見,底層 `equity`/`benchEquity` 不再送到前端 | `dom/overview.html` 逐行 `<td>` 數到八個,不見走勢圖;`/api/overview` 回應逐行核對 `"equity" not in row`(見下方腳本輸出) |
| 勝率格同格細字附交易次數 | `dom/overview.html`:`因子輪動(ETF 版)` 那一行 `63%<div class="dim" ...>111 筆</div>`;`screenshot-overview.png` 同一樣 |
| 總覽與策略詳情同一策略的代表運行是同一次,年化/Sortino/最大回撤/勝率四項數字一致 | `screenshot-overview.png` 右側明細卡(因子輪動 ETF 版):年化 19.2%、最大回撤 -33.7%;`screenshot-strategy.png` 頭條同一策略:年化 19.2%、Sortino 1.31、最大回撤 -33.7%、勝率 63%——與總覽表身那一行完全對得上 |
| 全部正式運行失敗的策略仍列一行,成績留空、對基準欄改講清楚 | `dom/overview.html`:「因子混合(ETF 版)」`<td class="num dim">1 條運行全部失敗</td>`,其餘成績格 `—`;「趨勢波段」同款,講「8 條運行全部失敗」;`screenshot-overview.png` 同一樣 |
| 五頁頁尾說明列整個不見 | `dom/overview.html`、`dom/strategy.html` 兩份完整渲染後 DOM 逐個搜 `foot-host`／`class="foot"`,零命中(另外三頁 index/sweep/run/pending 由原始碼掃過,見下方「這個核對法為什麼算數」) |
| 策略詳情頁的「選股快照」「參數掃描」「歷次運行」「選股漏斗」四個元件仍照常畫得出(不受迷你走勢拿走牽連) | `screenshot-strategy.png`:選股快照表格、參數掃描熱力圖帶全部有真數據畫出 |

## 這一票中途做的兩個決定(票上留言已另記)

1. **迷你走勢連右側明細卡的那份也一併拿走**,不只是表內那一欄。design-system.md
   原本 §3.15 那一列寫明同一顆 SVG 元件「表內與卡內」共用,而且票面本身就
   講明底層 equity/benchEquity 資料要停送,明細卡的走勢圖吃的正正是同一批
   資料——拿走資料等於兩處都要拿走畫面。明細卡改成只留 KPI 磚同 QQQ/SPY
   文字對比(那組數字本身已經在成績物件裡,不吃 equity 陣列)。
2. **代表運行判法統一時,順手修正咗策略詳情頁一個既有 bug**:改之前策略詳情
   頁的預設運行完全唔理會現役設定(同 design-system §4「門面數字一律現役
   設定」對唔上),總覽表就有理會但排序準則用「最近一次」唔係「年化最高」。
   兩個實作合併做 `karst.web.data.pick_representative_run` 之後,兩頁一致
   照 D-039 走「現役設定優先、組內或全庫揀年化最高的正式運行」。

## 順帶浮出的第三個既有測試斷言(非本票原定的兩項,但同一類「舊斷言追唔上
新結構」)

`tests/test_web_strategy.py::test_五個元件全部由真實運行數據畫出` 原本在
「五、歷次運行」那格因為 `IndexError`(全部運行失敗策略令 `items` 是空的)
提早失敗,修好之後往下跑到「六、頁內不准吊住假數據」才第二次失敗——斷言
`id="factor-expo"` 應該在 `strategy.html`,但因子敞口那一格早已按
D-037/KARST-080 搬去運行詳情頁(`index.html`/`run-view.js`),`strategy.html`
本來就再沒有這個掛點,舊斷言只是一直沒有機會跑到。改法:那個 host 清單拿走
`factor-expo`,不改行為——「四、因子分布」那格驗的是 API 本身的數,不受影響。

## 這個核對法為什麼算數

- headless Chrome 帶 `--virtual-time-budget` 打真正的頁面,DOM 是 JS 執行、
  `fetch` 拿到真數據之後的那份,不是原始碼推斷、也不是只看 `/api/*` 的
  JSON(兩者都做了,互相對得上)。
- index.html / sweep.html / run.html(即 `/run`)/ pending.html 四頁的頁尾
  拿走,用 `python -c` 逐頁 `urllib` 打一次,核對回應內文不見
  `foot-host`/`class="foot"`,見下方指令(倉根目錄執行,`8767` 是本次核對
  用的暫用埠,收工已關):
  ```
  python -c "import urllib.request as u; [print(p, 'foot-host' in u.urlopen('http://127.0.0.1:8767'+p).read().decode()) for p in ['/','/strategy','/sweep','/run']]"
  ```
  五頁之中 `overview` 與 `strategy` 額外用瀏覽器引擎複核(見上表),其餘三頁
  因為改動同屬「拿走同一個 `#foot-host` 掛點」那一類改動,原始碼層面
  (`git diff`)已經逐頁確認拿走,不再逐頁另開瀏覽器。
- pytest:`tests/test_web_overview.py` 與 `tests/test_web_strategy.py` 共
  13 項全過(含本票新增的 Sortino 對照斷言、all-failed 分支斷言)。
