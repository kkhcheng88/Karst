---
id: KARST-093
title: 網頁測試改打臨時庫:六個 test_web*.py 直接對倉根生產庫跑,jobs 那個每跑一次在生產庫多寫一條正式運行;改為每次測試起臨時 sqlite,並清走測試寫入的正式運行
type: task
createdAt: 2026-08-30
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-088]
claimedBy: agent-093
epic: V1 建置
deliverable: KARST-D03
closed: 2026-08-30
---

## 工作內容

源自 KARST-087 收工觀察:tests/test_web.py、test_web_data.py、test_web_holdings.py、test_web_overview.py、test_web_strategy.py、test_web_sweep.py(及 test_web_jobs 若存在)直接對倉根 data/ 下的生產資料庫跑;jobs 相關測試每跑一次就經正式路徑多寫一條 origin='formal' 的運行,正式運行由 12 條變 13 條即為此故。完成後:(1) 全部網頁測試經 conftest fixture 起臨時 sqlite 真庫(複製 schema,種入最少假數據經唯一入口寫),不再讀寫倉根生產庫;(2) 查明生產庫內由測試寫入的正式運行(以參數集/期間/寫入時間辨認,列清單在票上),經唯一入口把它們標為測試污染(不刪列;若無現成標記途徑,加一個經簽章的標記方式並入治理清單),使正式運行計數回到 12 條;(3) test_web.py 那條「運行清單頭 8 名」舊斷言改為不依賴生產庫內容;(4) 設計系統色值那條紅燈(原型改動所致)查明來源,屬 prototype/ 的不改,屬 karst/web/static/ 的改回設計系統 token。動庫前備份到 C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-093.bak。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 prototype/。

## 驗收條件

- [x] 六個(或以上)test_web*.py 全部經臨時庫跑,倉根生產庫在跑完前後位元不變(測試:跑前後雜湊比對)
- [x] 測試寫入的正式運行已辨認、標記並留痕,正式運行計數回到 12 條;verify 清白
- [x] test_web.py 兩條紅燈轉綠;只跑所涉測試檔;備份已做

## 結果

**測試不再碰生產庫。** 六個網頁測試檔本來直接打倉根那個 `karst.sqlite`,現在全部
經 `tests/conftest.py` 的 `seeded_project_root` 夾具,在臨時目錄起一個**真庫**、種
最少假數據(全部經唯一入口寫,簽章、版本鏈、運行編號查重照跑)。跑完全部網頁測試
前後量兩次生產庫雜湊,**逐位相同**。

**污染一條,已標記。** `run-47479e5b36fed94a`——編號由 KARST-087 收工留言直接抄下
(不是估的),再與庫身核對過:它用的參數集由寫入者 `karst-web`(網頁殼重跑那條路)
在運行落庫前 8 秒寫入,而同日早 8 分鐘 KARST-087 那個代理正在跑測試。時序、寫入者、
參數集版本鏈三邊對得上。**不刪列**:新加 `backtest_run_retraction` 表(schema 第 14
版),照快照除名(KARST-084)那一套——只加不改不刪、入治理清單、每列有唯一入口簽章。
除名後 `list_runs`/`count_runs` 略過它(**正式運行 13 → 12 條**),`get_run` 照樣讀
得到,運行的淨值與交易檔一個字不動。`karst verify` 三類全部清白。

**兩條紅燈的來源與上一張票的推測不同,要留意。**

1. *設計系統色值*——**不是原型改動所致,`karst/web/static/` 也不用改。** 出事的是
   測試自己那份色值清單:它由 design-system.md 的 1.7「圖表專用色」與 1.5 抄過來,
   **漏抄了 1.6「亮底上的深字」**。而 `app.js` 用的 `#06121f` / `#dfe4ee` 明明白白
   登記在 1.6,連用在哪個函數(`heatTextColor`)都寫住。即是說:實作對住正本,
   清單抄漏一節,紅燈反過來指住對的那一邊。按住紅燈去改 `app.js`,就會把一個對住
   正本的實作改到對不住正本。已補回清單那兩格,`app.js` 一個字沒有改。

2. *運行清單舊斷言*——本來釘死兩個生產庫的運行編號,要求它們出現在 `limit=8` 那一頁;
   生產庫多幾次正式運行,它們就被擠出頭八名(KARST-087 撞到時排第 11)。改為對住
   **測試自己那個庫**的正式運行:清單要列得齊。臨時庫種了兩次正式運行連一格掃描
   運行,所以「擋不擋得住掃描格」與「列不列得齊正式運行」兩件都真的驗得到。

**順帶揪出第三條一直紅住而無人見到的。** 同一個測試的第四段拆 `run-view.js` 裡
`function runLabel(r)` 的本體,驗運行選單那顆按鈕的字。**那顆按鈕已經不在**——D-035
(KARST-078)把運行詳情改為策略詳情的鑽取層,運行選擇器整個拆走,`runLabel` 全倉
搜不到。它自 KARST-078 起就恆真轉紅,只是一直被上面第二段的失敗遮住。已改為驗這條
驗收真正要問的東西:這一頁講不講得出自己是哪一次運行(麵包屑那一格)。

**交低一件(另開票才做,本票不動):`test_web_sweep.py` 現時全檔跳過。** 臨時專案根
的 `experiments/` 是空的,而掃描頁的測試要有掃描落檔才跑得起。要它們真的跑,臨時庫
還要種一幅**完整的掃描落檔**(掃描表連判讀表、帶選擇軸、判讀已按軸型分層),那是
另一件工。本票先把它的讀取層接離生產庫——照舊打生產庫的話,斷言就會吊住倉內今日
剛好有哪幾幅掃描,與上面第 2 條同一個病。

產出:`experiments/2026-08-30-測試污染運行除名/`(`除名.py`、`結果.md` 連雜湊表)。

待收貨。

## 留言

### agent:agent-093 · 2026-08-30 11:55
收工報告(KARST-093)。

\## 一、夾具做法

`tests/conftest.py` 加一個 session 級夾具 `seeded_project_root`,建一個版式與倉根一模一樣的臨時專案根:`<root>/karst.sqlite`、`<root>/data/snapshots/…`、`<root>/data/runs/…`、`<root>/experiments/`。

版式要一模一樣不是講究:網頁層有兩處會由 `runs_root` 倒推專案根(`api_sweep._project_root`、`api_jobs.JobContext`),認的正是結尾那兩級 `data/runs`。版式一走樣,它們就靜靜跌回 `Path.cwd()`——即倉根,那就前功盡廢:表面上接了臨時庫,重跑那條路照舊寫回生產庫。

種入的最少數,全部經唯一入口寫(D-020 第 4 條,不造假定義庫):一個因子、一套策略、兩個參數集、一個真價格快照(靜態日線,不連網)、**兩次正式運行**連**一格掃描運行**。

四個地方是踩過先知,寫低免得下一手再踩:

1. **策略名必須是 `api_jobs.RERUN_RECIPES` 認得的其中一套**(用了「趨勢波段」)。否則 `test_web_jobs.py` 全檔跳過——而「畫面按重跑」正是本票要接離生產庫的那條路,接完之後它若一條都跑不起,等於把問題由「弄髒生產庫」換成「不再驗」。
2. **引擎名必須同重跑路徑跑出來的一樣**(`vectorbt-order-func`)。引擎是運行編號的原料之一,種數時寫另一個名,重跑會拒收:「引擎不同即不是同一條血統」。
3. **因子要經 `gateway` 而不是 `store` 註冊。** 兩者都寫得入,但只有前者蓋簽章;`test_web_jobs.py` 有一條會對整個臨時庫跑 `verify`,借 store 抄近路,那一條就會反過來告種數的人繞過唯一入口。
4. **兩隻股要行波浪,不可以行直線;而且落注的不含兩隻基準。** 趨勢波段要「突破前 50 日高位」入場、「前 10 日擺動低位」做停損——完美直線兩樣都給不出(突破日日都算,停損距離近乎零),引擎一注都落不出,重跑測試就驗不到。基準只做對照尺不落注(D-010 第 4 條);種數時連基準一齊持,選股漏斗那條會對不上。

期間刻意跨過 2023-01-01,`test_web.py` 那四條「揀一段日期重看」才跑得起而不是跳過。

\## 二、污染運行清單與標記方式

**污染一條:`run-47479e5b36fed94a`**(趨勢波段・示例-KARST-028 v9・2015-01-02 至 2026-08-26・快照 2026-08-28-a508d635a5fa・vectorbt-order-func 0.1.0・落庫 2026-08-29T21:12:31)。

認定憑據(不是估的):
- KARST-087 收工留言明文寫住編號:「這一次多了 `run-47479e5b36fed94a`」。
- 庫身核對對得上:它用的參數集 8326 由寫入者 `karst-web`(網頁殼重跑那條路的寫入者名)於 21:12:23 寫入,**比運行早 8 秒**,正是「登記新參數集 → 跑引擎 → 落運行」那個次序;同日 21:04:08 `gateway_write` 內有一批 `writer='KARST-087-agent'`,即那個代理當時正在跑測試。

**要講清楚一件事:庫內另有 6 條正式運行同樣經 `karst-web` 寫入**(參數集版本 v2–v6、v8,2026-08-28 16:10 至 2026-08-29 16:05)。**這 6 條沒有動。** `karst-web` 只代表「由網頁殼那條路寫入」,人手在畫面上按重跑一樣是這個名,它分不出人手與測試。本票的基準是 KARST-087 明文記下的「12 → 13」,即只有一條是測試添的;要把那 6 條也判為污染,需要另一份憑證,不可以憑寫入者名一個字推過去。有需要另開票查。

標記方式(**不刪列**):新加 `backtest_run_retraction` 表,schema 第 14 版,照 `data_snapshot_retraction`(KARST-084)那一套——
- 只加不改不刪(兩道 trigger 擋住 UPDATE / DELETE);
- 入治理清單 `ledger.GOVERNED_TABLES`,歸「定義」類(與 `active_setup` 同級:兩者都是決定「門面數字取哪幾次運行」的定義級動作),所以每列有唯一入口簽章,有人繞過那道門靜靜抹走一次運行的成績,`karst verify` 一掃就見到;
- 寫入經 `Gateway.retract_run(run_id, reason=...)`,`reason` 不設預設值。

除名後:`list_runs`/`count_runs` 略過它(**正式運行 13 → 12 條**),`get_run` 照樣讀得到,`backtest_run` 那一列與淨值、交易 parquet 一個字不動。`karst verify` 三類全部清白(定義 50813 列、因子批次 997 列、快照 22 列)。

\## 三、生產庫雜湊

| 時點 | SHA256 | 大小 |
|---|---|---|
| 動手之前(已備份) | `70D56DDB…B4E3FE` | 40,067,072 |
| 跑完全部網頁測試之後 | `70D56DDB…B4E3FE`(**一位不變**) | 40,067,072 |
| 除名之後(唯一一次寫入) | `342CA7F8…3FB96F` | 40,075,264 |
| 再跑一次全部網頁測試之後 | `342CA7F8…3FB96F`(**一位不變**) | 40,075,264 |

前後兩次量度都證同一件事:網頁測試已經不再碰生產庫;庫身唯一一次改動就是那一列除名登記。備份:`C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-093.bak`(除名之前整檔複製)。

\## 四、跑了哪些測試檔

網頁層九個(六個改動的連三個原本已經用臨時庫的):`test_web.py`、`test_web_data.py`、`test_web_holdings.py`、`test_web_overview.py`、`test_web_strategy.py`、`test_web_sweep.py`、`test_web_jobs.py`、`test_web_concurrency.py`、`test_web_series_missing.py` → **41 passed, 10 skipped**(跑了兩次,結果一樣)。

因為動了 schema / store / gateway / ledger,另跑受影響那六個:`test_snapshot_governance.py`、`test_gateway_governance.py`、`test_gateway.py`、`test_runs.py`、`test_definition_store.py`、`test_snapshot_retraction.py` → **49 passed**。

沒有跑 full test(不在本票範圍)。

\## 五、兩件要主腦過目的判斷

1. **設計系統色值那條紅燈,來源與票上寫的不同。** 票寫「原型改動所致」,實際**不是**,而且 `karst/web/static/` 一個字都不用改。出事的是測試自己那份色值清單:它由 design-system.md 的 1.7 與 1.5 抄過來,**漏抄了 1.6「亮底上的深字」**;而 `app.js` 用的 `#06121f` / `#dfe4ee` 明明白白登記在 1.6,連用在哪個函數(`heatTextColor`)都寫住。按住紅燈去改 `app.js`,會把一個對住正本的實作改到對不住正本。已補回清單那兩格。

2. **順帶揪出第三條一直紅住而無人見到的。** 同一個測試的第四段拆 `run-view.js` 裡 `function runLabel(r)` 的本體,驗運行選單那顆按鈕的字——**那顆按鈕已經不在**:D-035(KARST-078)把運行詳情改為策略詳情的鑽取層,運行選擇器整個拆走,`runLabel` 全倉搜不到。它自 KARST-078 起恆真轉紅,一直被上面第二段的失敗遮住。已改為驗這條驗收真正要問的東西:這一頁講不講得出自己是哪一次運行(麵包屑 `bc-run`)。**這一段是刪走了一個對住已拆走 UI 的斷言,不是改細斷言遷就實作**,請過目。

\## 六、交低(另開票才做,本票不動)

`test_web_sweep.py` 現時全檔跳過:臨時專案根的 `experiments/` 是空的,而掃描頁測試要有掃描落檔才跑得起。要它們真的跑,臨時庫還要種一幅完整的掃描落檔(掃描表連判讀表、帶選擇軸、判讀已按軸型分層),是另一件工。本票先把它的讀取層接離生產庫——照舊打生產庫的話,斷言就會吊住倉內今日剛好有哪幾幅掃描,與運行清單那條舊斷言同一個病。

\## 改動檔案

- `karst/schema.py` — 加 `backtest_run_retraction` 表連兩道 trigger,SCHEMA_VERSION 13 → 14
- `karst/store.py` — `RunRetraction`、`retract_run`、`list_run_retractions`、`retired_run_ids`;`list_runs` 與 `count_runs` 略過已除名
- `karst/gateway/service.py` — `Gateway.retract_run`(蓋簽章)
- `karst/gateway/ledger.py` — 治理清單與分類加 `backtest_run_retraction`
- `tests/conftest.py` — `seeded_project_root` 夾具連種數常數
- `tests/test_web.py` — reader 接臨時庫;色值清單補 1.6 兩格;運行清單斷言改為對住自己個庫;第四段改驗麵包屑
- `tests/test_web_overview.py`、`test_web_strategy.py`、`test_web_sweep.py`、`test_web_concurrency.py` — reader 接臨時庫
- `tests/test_web_jobs.py` — reader 接臨時庫;重掃落檔收拾位跟住搬去臨時根
- `experiments/2026-08-30-測試污染運行除名/除名.py`、`結果.md` — 新增

`prototype/`、`karst/web/static/` 一個字都沒有改;沒有 commit。
