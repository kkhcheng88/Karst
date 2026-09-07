# 歷次運行改排名表、因子分布改持股分布 核對(D-037,KARST-080)

> 跑法(倉根目錄,另開一個背景程序常駐):
> ```
> set PYTHONUTF8=1
> set PYTHONPATH=.
> python experiments/2026-08-29-run-ranking-holdings/serve_temp.py 8767
> ```
> 沿用 KARST-079(`experiments/2026-08-29-strategy-page-restructure/README.md`)
> 記低的做法:headless Chrome `--dump-dom --virtual-time-budget=6000
> --user-data-dir=<獨立 profile>` 取 JS 執行完畢後的真實 DOM,不是只讀原始碼
> 推斷行為;另外用 `curl` 直打新端點 `/api/strategy/holdings`、`/api/strategy/runs`
> 逐項核對數值與排序。核對完已經收工那個 server(kill 對應 PID),倉內不留
> 常駐程序。

## 一句話

**六項工作全部落地並核對過:歷次運行表換成排名表(運行編號/版本/年化/
Sortino/最大回撤/勝率,四個成績欄可點欄頭排序、預設按年化由高至低)→
持股分布(原「因子分布」)頁面載入預設顯示排名第一行那次運行,點任一行
即換,榜按持有日數排前十、算出各自累計報酬,行業佔比因無數據源留空並
註明→因子敞口與因子版本搬到運行詳情頁新增的「因子」分頁→策略頁「檢視
中」整段(參數清單/運行編號/快照/視窗)整個拿走→新增持股彙總後端端點
(帶測試)→選股漏斗搬到策略頁最底,最終次序:門面成績→熱力圖帶→歷次
運行表+持股分布→選股漏斗。**

## 核對了什麼、在哪裡看得到

| 核對點 | 憑據 |
|---|---|
| 歷次運行表六欄、預設年化由高至低排序 | `dom/strategy-id3-holdings.html` 的 `<thead>`:六個 `<th>`(運行編號/版本/年化/Sortino/最大回撤/勝率),沒有快照、參數、查看欄;`data-sort="annualReturnPct"` 那格 `aria-sort="descending"`,其餘三格 `aria-sort="none"` |
| 排序改由後端 `?sort=&dir=` 驅動(不是前端整批抓完再排) | `curl "/api/strategy/runs?id=2&all=1&sort=winRatePct&dir=asc"`:回傳的 8 條運行按勝率由低到高排(43.16%→43.22%→……),`sort`/`dir` 兩個欄位原樣回聲 |
| 頁面載入自動選中排名第一行、換到持股分布 | `dom/strategy-id3-holdings.html`:`<tr class="row-clickable is-picked" data-run="run-924a54eb843f0988" aria-pressed="true">`;同一份 DOM 的 `#holdings-body` 已經是該運行的持股分布表,不是空狀態 |
| 運行編號那格是連結、直達運行詳情頁(D-035/D-036 入口不能斷) | `dom/strategy-id3-holdings.html`:`<td class="mono"><a href="/run?id=3&run=run-924a54eb843f0988">run-924a54eb843f0988</a></td>` |
| 持股分布:前十由持有日數排、算對累計報酬、行業佔比留空並註明 | `curl "/api/strategy/holdings?run=run-924a54eb843f0988"`:`rankBasis:"holdingDays"`、四隻持股按 `holdingDays` 由高到低(USMV 1696 日、VLUE 1502 日、QUAL/MTUM 270 日並列)、各自 `cumulativeReturnPct`、`sectorBreakdown: null`、`notes.why` 講明無行業欄;`dom/strategy-id3-holdings.html` 的 `#holdings-body` 表格同一組數字,外加一句「累計報酬＝該股在此運行全部已平倉交易的合計損益÷起始資金 100000」 |
| D-034 全部運行失敗的策略,排名表與持股分布都是清楚的空狀態(不是報錯) | `dom/strategy-id2-all-failed.html`:`#runs-body` 是 `8 條運行全部失敗(年化回報同時低於 SPY 與 QQQ 買入持有)。`,`#holdings-body` 是「此策略未有正式運行,持股分布無從畫起。」;「檢視中」整段、`run-pick`/`config-slim` 兩個舊區塊完全不在 DOM 裡(`grep -c` 為 0) |
| 策略頁段落最終次序 | `dom/strategy-id2-all-failed.html`、`dom/strategy-id3-holdings.html` 的 `<h2>` 依序:淨值走勢/選股快照(門面成績同一排)→參數掃描(熱力圖帶)→歷次運行→持股分布→選股漏斗,選股漏斗是頁面最後一個 `<section>` |
| 因子敞口、因子版本搬到運行詳情頁新分頁,策略頁不再顯示 | `dom/run-id3-factor-tab.html`:`#tab-f`/`#p-f` 分頁內 `#factor-expo` 畫出四條因子敞口棒(價值 100%、其餘 0%,對回這次運行的持倉),`#factor-hist` 畫出四條因子版本鏈(v1 ← v2,現用標籤);同一份策略頁 DOM(`strategy-id2/3`)都搜不到 `factor-expo`/`factor-hist` |
| 新增後端持股彙總端點,有測試覆蓋(至少兩隻股票各一筆交易,累計報酬算對) | `tests/test_web_holdings.py`:`test_兩隻股票各一筆交易累計報酬算對`(AAA 持 4 日、損益 +100、起始資金 100000 → 累計報酬 10%;BBB 持 2 日、損益 -50 → -5%)、`test_沒帶run參數要清楚拒收`;`python -m pytest tests/test_web_holdings.py -q` → `2 passed` |
| 沒有引入新的迴歸 | `python -m pytest tests/test_web_holdings.py tests/test_web_strategy.py tests/test_web_overview.py tests/test_web_series_missing.py -q` → `2 failed, 16 passed`(見下一節,兩項失敗與本票無關、屬本機既有狀態) |

## 兩項既有失敗,與本票無關

跑 `tests/test_web_*.py` 有兩個測試維持失敗,兩個都用 `git stash` 把本票
改動全部退回、單獨重跑同一條測試確認過——退回之後一樣失敗,證明是本機
既有狀態,不是本票引入的迴歸:

1. `tests/test_web_overview.py::test_載入中空錯誤三態齊全且導航列三頁連結齊全`
   ——斷言導覽列有 3 條連結,但 KARST-079(D-036)早已把頂層導覽收成 2 頁,
   這個斷言是舊測試留下未跟住改的殘留,與本票的排序/持股分布改動無關。
2. `tests/test_web_strategy.py::test_五個元件全部由真實運行數據畫出`
   ——本機 ambient DB 裡「最近有運行」的策略(id=2,趨勢波段)8 條正式運行
   全部被 D-034 判定失敗,`/api/strategy/runs`(不帶 `all=1`)因此合法地回
   空清單;測試斷言 `page["items"][0]` 一定有東西,是對本機資料狀態的假
   設,不是本票的排序邏輯有錯。

另外原本 `tests/test_web_strategy.py::test_宏觀驅動器參數區的序列齊全度由
真數據填` 在改動過程中一度變成第三個失敗——這個是本票直接造成的:
「序列齊全度」那一行原本掛在策略頁的 `config-slim` 區塊(已隨「檢視中」
一併拿走),搬去了運行詳情頁的運行身份晶片(`run-view.js`)。這個測試原本
查 `strategy.js` 有沒有相關字串,已經改成查 `run-view.js`(功能本身沒有
少,只是換了檔案),改完之後這條測試恢復 `passed`,不算在上面兩項既有失
敗之列。

## 一個沒有寫在票面、由我判斷落地的地方(已在票上 `raised`)

有四項票面文字沒有直接寫明的判斷,已經在 `.kira/tickets/KARST-080-*.md`
用 `raised` 留言分四格記低,等用戶或者接手的人審:

1. 持股分布的「最常持有」用哪個口徑——揀了持有日數,不是平均持倉權重。
2. 行業佔比確認無數據源(`karst/data/universe.py` 沒有行業欄),只做另外
   兩項,API 回 `sectorBreakdown: null` 並帶解釋。
3. D-036(下鑽運行詳情)與 D-037(點行換持股分布)字面上的牴觸,靠「運行
   編號連結 vs. 點行其他地方」拆開兩個語意來滿足。
4. 「序列齊全度」不在票面明文列出的四項「檢視中」內容之列,選擇保留功能
   並搬去運行詳情頁,而不是直接刪除。

## 這個核對法為什麼算數

Headless Chrome 是與用戶實際用的同一個瀏覽器引擎,`--dump-dom` 取的是
JavaScript 全部執行完畢之後的畫面,不是伺服器吐出的原始 HTML,所以能驗
到 `strategy.js`/`run-view.js` 真的照這樣渲染、真的接得上新端點——與人
手在瀏覽器打開這幾頁看到的東西一致。持股分布的數值另外用 `curl` 直打
`/api/strategy/holdings`、`/api/strategy/runs?sort=`,逐項對過 API 回傳
與畫面顯示一致,雙重核對排序與累計報酬沒有算錯。
