---
id: KARST-060
title: 重建收尾三件小事:序列缺失運行改名、出場規約補「賣出當日不可再入場」、重判總表舊裁決欄修正
type: task
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-057, KARST-059]
claimedBy: null
closed: 2026-08-29
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

三件互不相干但都細小的收尾。(1) KARST-057 把序列檔案不在的運行標成「過時運行(序列缺失)」,與詞彙表「過時運行」(版本過時)撞名;網頁殼標籤與程式名一律改為「序列缺失運行 / series-missing run」(CONTEXT.md 已入冊)。(2) KARST-059 發現出場規約沒有寫「賣出當日不可再入場;新入場最早在下一個交易日開市」——引擎行為已如此,只補規約文字並加一個把行為釘死的測試,不改引擎邏輯、不加參數。(3) 兩支重判腳本(axis-aware-verdict、macro-rejudge)的總表與 summary.json「最優格舊裁決」欄在最優格本身改判時填成新裁決(逐格對照表才對),修正產生程式並重出總表;因子輪動 summary.json 補「山脊」計數欄(KARST-047 漏補),README 該格由「填不到」改為實數。不重跑引擎。

## 驗收條件

- [x] 網頁殼與程式內不再出現「過時運行(序列缺失)」,改為「序列缺失運行」,既有測試過
- [x] 出場規約文字補該句,新增測試證明賣出當日再發訊號只能在下一交易日開市入場
- [x] 兩份重判總表「最優格舊裁決」與逐格對照表一致;因子輪動 summary.json 有山脊計數,README 該格填實數

## 結果

· 2026-08-29 00:52

三件收尾全部做完,**引擎邏輯一個字沒有改,一次都沒有重跑引擎**;`karst.sqlite` 與
`data/` 只讀。

### 一、序列缺失運行改名

「過時運行(序列缺失)」這個名與詞彙表的「過時運行 stale run」撞名——前者講序列檔案
不在,後者講版本已不是最新,兩件事無關。名一律改為**序列缺失運行 / series-missing
run**(CONTEXT.md 早已入冊,本票不動該檔):

- 讀取層那個方法 `RunReader.series_gap()` → **`series_missing()`**,四個呼叫點一併改
  (`karst/web/data.py`、`karst/web/api_strategy.py`、`tests/test_web_strategy.py`)。
- 頁面收到的錯誤訊息由「運行 … 是過時運行(序列缺失)」改為「運行 … 是序列缺失運行」;
  `karst/web/api_sweep.py`、`karst/runs/registry.py` 的規約文字一併改。
- 測試檔 `tests/test_web_stale_series.py` → **`tests/test_web_series_missing.py`**,
  並加一句反向斷言:訊息裡不准再出現「過時運行」。
- 網頁殼**沒有**這個標籤要改:那個數(`missingSeries`)後端交得出,前端現時未有畫面
  用它,所以一個字都不用動。
- 舊名只餘三處刻意留低的註腳(講明「本來寫作什麼、為什麼改」),方便日後有人 grep 舊名
  時撞到解釋而不是死胡同。已關的 KARST-057 是歷史紀錄,不倒改。

### 二、出場規約補「賣出當日不可再入場」

KARST-059 的外部對照發現:引擎的行為本來就對(賣出當日不會再入場),但**規約文字沒有
明寫**,那一句只活在落單那一層的實作裡。本票只補文字與測試:

- `karst/engine/rules.py` 全倉唯一一份出場規約(`resolve_exits` 的 docstring 與檔頭
  那段)補上:**賣出當日不可再入場;同一隻的新入場最早在下一個交易日開市**,連同理由
  (入場成交取開價,離場是開市之後的事,開市那一刻舊倉仍然在手)。
- `karst/engine/vectorbt_engine.py` 那句「手上有貨就只看離場」加一行,指回規約那一句。
- 新測試 **`tests/test_engine_exit_reentry.py`** 把行為釘死:一條每日 +1 的斜坡,突破
  訊號根根成立,所以「賣出當日沒有買入」只可能來自規約那一句,不可能是「那日剛好無
  訊號」。跑出七買六賣,逐個賣出日核三件事——當日確實有入場訊號、當日一張買單都沒有、
  下一個交易日以開價入得回場。

### 三、重判總表「最優格舊裁決」修正

**缺陷**:兩支重判腳本 `summary.json` 的 `best.old_verdict` / `ridges[].old_verdict`
(宏觀那支還有 `plateaus[]`)讀的是來源目錄落檔那張判讀表——但 KARST-048 之後生產掃描
路徑已經改判新口徑,來源腳本一重跑就會覆寫那張表。於是「舊裁決」會填成**新裁決自己**,
最優格一改判就報「沒有變」。KARST-057 當日修好了逐格對照表,這幾格漏了,總表那一欄
「最優格舊裁決」正是由這裡抄過去的。

- 兩處一律改讀**舊口徑重判**那一個(`old.cell_for(...)`),與逐格對照表同一個來源。
- 兩支腳本各加一道閘:summary 那幾格「舊裁決」要與逐格對照表逐格對得上,對不上當場停手。
- 兩支腳本已重跑(只讀落檔 CSV,不碰引擎、不碰庫),總表與 summary.json 重出。
  **看得到的分別**:六驅動器總表本來六行全部「舊裁決 = 新裁決」,現在 VIX 期限結構
  (孤峰→普通)與信用利差(孤峰→山脊)兩行的改判終於顯示得出;軸型重判那邊,六條山脊
  的舊裁決由「山脊」還原成真正的舊裁決(普通 ×5、孤峰 ×1)。
- 兩份 README 加了修正說明。宏觀 README 正文那張表本來就是對的(它抄逐格對照表),
  現在與 CSV 總表一致。

### 四、因子輪動 summary.json 補山脊計數

產生程式 `run_rotation_sweep.py` 的裁決分佈當日只寫平原/孤峰/無效,漏了 KARST-047 新增
的山脊,已補上(下次重跑直接帶住)。既有落檔由新腳本 **`backfill_ridge_counts.py`**
補回——由當日落檔的 `掃描表.csv` 逐格重判一次(不重跑引擎,門檻與軸型一個字不改),
**先核對平原/孤峰/無效三欄與落檔完全相同**,才准把山脊寫回去。

結果:年化超額軸四個驅動器**山脊全部 0 格**;最大回撤軸因子動量有 1 格山脊,與該目錄
那份 `報告-最大回撤.md` 對得上。README 那格由「填不到」改成實數。

### 動過的檔

| 檔 | 改了什麼 |
|---|---|
| `karst/web/data.py` | `series_gap` → `series_missing`;錯誤訊息與註釋改名 |
| `karst/web/api_strategy.py`、`karst/web/api_sweep.py`、`karst/runs/registry.py` | 同一個改名 |
| `karst/engine/rules.py`、`karst/engine/vectorbt_engine.py` | 出場規約補一句(**只有文字**) |
| `tests/test_web_series_missing.py` | 由 `test_web_stale_series.py` 改名,加反向斷言 |
| `tests/test_engine_exit_reentry.py` | 新增:釘死「賣出當日不可再入場」 |
| `tests/test_web.py`、`tests/test_web_strategy.py` | 跟住改名 |
| `experiments/2026-08-28-axis-aware-verdict/rejudge_axis_aware.py` + README | 舊裁決欄修正 + 一致性閘 |
| `experiments/2026-08-28-macro-rejudge/rejudge_macro_axis_aware.py` + README | 同上;總表已重出 |
| `experiments/2026-08-28-factor-rotation-drivers/run_rotation_sweep.py` | 裁決分佈補山脊那一欄 |
| `experiments/2026-08-28-factor-rotation-drivers/backfill_ridge_counts.py` | 新增:補回既有落檔的山脊計數 |
| `experiments/2026-08-28-factor-rotation-drivers/README.md` | 判讀表加山脊欄,「填不到」改實數 |

重出的結果檔:兩份 `results/summary.json`、`六驅動器新舊裁決總表.csv`、各驅動器的
`新舊裁決對照表.csv` / `判讀表-軸型.csv` / `分層判讀.csv` 與投影圖;因子輪動那份
`results/summary.json`(只加山脊一欄,其餘一個字沒動;改前備份在
`~/.claude/backups/factor-rotation-summary.json.2026-08-29.bak`)。

### 收工核對

1. 九個測試檔 42 項全綠:`test_web_series_missing.py`、`test_web.py`、
   `test_web_strategy.py`、`test_web_overview.py`、`test_web_sweep.py`、
   `test_engine_rules.py`、`test_engine_audit.py`、`test_engine_exit_reentry.py`、
   `test_runs.py`。全庫 `pytest tests` 亦跑過。
2. 獨立核對(不經腳本自己那道閘):六驅動器總表的「最優格舊裁決」逐行對回各自的
   `新舊裁決對照表.csv`,軸型重判那邊最優格與三條山脊亦逐格對回——全部一致,零個對不上。
3. 因子輪動那四個驅動器的平原/孤峰/無效三欄,重判出來與落檔完全相同(這是補山脊那一欄
   的准入條件)。

**沒有做的幾件**:沒有 commit(派工明令);沒有改 `CONTEXT.md`;沒有重跑引擎、沒有動
`karst.sqlite` 與 `data/`;沒有開 worktree、沒有建目錄連結。

## 留言
