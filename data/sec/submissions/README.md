# 申報索引單一快取(EDGAR submissions)

倉內唯一一份 SEC 申報索引(submissions index)副本。D-134 用戶定的黃金原則:同一份原料
只准有一份副本,有 manifest、有校驗。任何票要查一家公司交過什麼、幾時交、表格類型、
掛牌代號、SIC、entityType,一律讀這裡,**不要另存一份**。

- 位置:`C:\projects\Karst\data\sec\submissions\`
- 主檔:`CIK<十位補零>.json`(EDGAR 原檔位元,不曾解碼、不曾改寫)。**8,012 份屬 v0
  宇宙**(KARST-167 抓);另有 **99 份屬宇宙外公司**(KARST-177 收編,manifest 標
  `outside_universe_v0`,不計入任何宇宙統計)
- 歷史分頁:`pages/CIK<十位補零>-submissions-NNN.json`(主檔 `filings.files` 欄列出的
  分頁,EDGAR 原檔位元;KARST-177 建的結構,見第二、三節)
- 逐份索引:`manifest.jsonl`(每份一行,主檔與分頁檔都在同一份,**只准 append,不准
  整檔重寫**)
- 完整性登記:`completeness.csv`(每個 v0 宇宙 CIK 一行,見第二節)
- 目錄層索引:`manifest.csv`(本倉每一個申報索引位置的登記,見第四節)
- 現況(2026-09-03 KARST-177 核算):主檔 **8,111 份**(8,012 v0 宇宙 + 99 宇宙外)、
  分頁 **2,816 份**(1,051 收編 + 1,765 補抓),合共約 **1.08 GB**;manifest.jsonl
  **10,927 行**,與檔數(8,111 + 2,816)一致

倉根的 `data/` 已被 `.gitignore` 擋住,所以 `.json`、`pages/` 與 `manifest.jsonl` 不入
git;本 README、`manifest.csv` 與 `completeness.csv` 是說明與登記,不是數據,已用
`git add -f` 納入版本控制。

---

## 一、來源與抓取

| 項目 | 內容 |
|---|---|
| 來源 | `https://data.sec.gov/submissions/CIK<十位補零>.json` |
| 抓取者 | KARST-167(`fetchedBy` 全部是 `KARST-167 universe-167`) |
| 抓取日期 | 2026-09-02 共 1,617 份、2026-09-03 共 6,395 份 |
| 速率 | 每秒 8 個請求(SEC 上限 10) |
| User-Agent | `Casy Limited kaho.career@gmail.com`(SEC 公平取用要求真實聯絡電郵) |
| 涵蓋範圍 | 證監會代號對照表 2026-09-02 快照的 **8,001 個 CIK**,另加 11 份早期收入的 |

`manifest.jsonl` 逐行欄位:`cik`、`file`、`name`、`entityType`、`sic`、`tickers`、
`exchanges`、`url`、`bytes`、`sha256`、`fetchedAt`、`fetchedBy`、`source`。

---

## 二、~~這份快取有一塊是不完整的~~ 已修復(KARST-177,2026-09-03)

**EDGAR 的 `CIK##########.json` 只載最近約 1,000 份申報。** 更早的歷史不在主檔內,
而是由主檔 `filings.files` 欄列出一批**分頁檔**(`CIK##########-submissions-00N.json`)。
KARST-174(2026-09-03 上午)查出本快取當時一個分頁檔都沒有存,8,012 份主檔之中
2,066 份(25.8%)被截短,合共聲明 2,736 個分頁檔;A-046 記錄此事並推翻「單一快取載有
完整申報史」的假設。

**KARST-177(2026-09-03 下午)已補齊。** 分頁檔現在全部住 `pages/`:1,051 個由
`experiments/2026-09-02-silent-revisions` 收編(整檔位元搬移、逐檔 sha256 核對),
餘下 1,765 個向 EDGAR 補抓(零失敗)。逐 CIK 核對 `completeness.csv`:**2,066/2,066
家 complete,完整性 100%**。

**實例:** 雅培 CIK 0000001800,主檔只有 2018-06-05 至 2026-08-27 的 1,002 份申報;
1994-02-14 至 2018-06-03 的 2,612 份住在它聲明的兩個分頁檔內,`pages/` 現在兩個都有。

**一個附帶查證,寫給下一個讀者:** 分頁檔缺失本身是真的,但它從未實際污染 KARST-167
報告 §2.4「按首次申報年」分佈表——建表腳本一早就有讀主檔 `filings.files[].filingFrom`
(截短之後的主檔本身仍帶著的邊界日期,不用抓分頁內容),逐 CIK 核對分頁檔實際內容
之後,全部 8,012 家的首次申報日與這個做法算出來的一模一樣,零家有差。詳見
`research/2026-09-03-小型股宇宙v0盤點.md` §2.4a 與 A-046 的 `verifiedEvidence`。
**真正受過影響的**是任何只讀 `filings.recent` 而沒有連 `filingFrom` 一併取最小值的
舊程式碼(`experiments/2026-09-02-chain-layers/build_v2.py` 第 86 行原始踩坑處),以及
需要分頁**內容**而不只是邊界日期的工作(申報密度、申報中斷偵測一類)——這些現在
都有完整分頁檔可用。

**用之前要做的事:** 讀 `filings.recent` 之前先看 `filings.files` 是否非空;
非空即代表主檔是截短的,完整申報史要連 `pages/` 一併讀(見第三節第 3 條)。

---

## 三、新增與更新的規則

1. **抓之前先查這裡。** 用 `CIK<十位補零>.json` 查;檔存在就直接讀,不要再打 EDGAR。
   這是單一副本原則落地的那一步。
2. **速率上限每秒 10 次**,並帶 SEC 要求的 `User-Agent`(真實聯絡電郵)。超速會被封 IP。
3. **要完整申報史就連 `pages/` 一齊讀**:讀主檔 `filings.files`,逐個查
   `pages/<name>` 是否存在;v0 宇宙 2,066 家截短公司的分頁檔(KARST-177)已經
   **100% 收齊**,查不到再打 `https://data.sec.gov/submissions/<name>`,抓完寫入
   `pages/` 並補一行 `manifest.jsonl`(`source` 填 `fetched`)。
4. **manifest.jsonl 只 append,不整檔重寫。** 隨時可能有另一隊同時在寫。
   真的要改既有行,先讀最新版、只改自己那些行、其餘原樣寫回。
5. **`fetchedBy` 填票號或隊名**,不要留空、不要填人名。
6. **衍生物不放這裡。** 由申報索引切出來的東西(10-K 清單、申報窗、8-K 4.02 索引之類)
   放回各自的票目錄,靠 CIK 指回這裡的正本。這是 D-134 決策第 2 條明文准許的。
7. **內容一律當位元處理**:複製搬移用 `Copy-Item`/`Move-Item`,不要用 shell 解碼讀寫。

---

## 四、本倉其他申報索引位置(KARST-174 盤點,KARST-177 收編)

`manifest.csv` 是這一節的機讀版。KARST-174 逐檔核過 sha256(11,075 個檔),
把與正本完全相同的 **514 份、89.2 MB** 刪走,其餘按 D-157「不同者一律保留」留在原位。
KARST-174 舉手請裁「1,051 個分頁檔與 99 份宇宙外 CIK 收不收編入正本」,主 agent
2026-09-03 裁答甲(D-161):收編加補抓。KARST-177 已執行,見下。

### 4.1 已收編(KARST-177,原地不留副本)

| 曾經在 | 內容 | 現在 |
|---|---|---|
| `experiments/2026-09-02-silent-revisions/data/submissions/` 的 1,051 個分頁檔 | `CIK<10>-submissions-NNN.json` | 已 Move-Item 入本目錄 `pages/`,零失敗 |
| `experiments/2026-09-02-fundamentals-panel/` 76 份 + `experiments/2026-09-02-silent-revisions/` 23 份宇宙外 CIK | `CIK<10>.json`,共 99 份 | 已 Move-Item 入本目錄頂層,manifest 標 `outside_universe_v0` |

逐檔搬移紀錄(路徑、sha256、搬移前後核對)在
`experiments/2026-09-03-submissions-backfill/out/move_log.csv`。

### 4.2 仍在原處的真副本(與正本內容有異,按 D-157「不同者一律保留」)

| 位置 | 現存 | 大小 | 留下的是什麼 |
|---|---:|---:|---|
| `experiments/2026-09-02-fundamentals-panel/data/submissions/` | 2 | 約 0.3 MB | 同 CIK 但內容有異(抓於 2026-09-02,較正本舊) |
| `experiments/2026-09-02-silent-revisions/data/submissions/` | 99 | 約 14.1 MB | 同 CIK 但內容有異(抓於 2026-09-02,較正本舊) |

這 101 份是正本較舊的子集(EDGAR 09-02 至 09-03 之間多了新申報,逐份比正本細
約 16 KB),沒有正本沒有的資料,保留只為守「不同者一律保留」,不搬不刪。

### 4.3 衍生物目錄(不是副本,不受單一快取原則管)

下面三個目錄名叫 `submissions`,但存的**不是申報索引本體**,是由它切出來的 10-K 清單
(`[[filingDate, reportDate, accession, primaryDoc], …]`,每份約 1.8 KB,
檔名是裸 CIK 沒有 `CIK` 前綴)。D-134 決策第 2 條明文准許實驗票目錄存衍生物,
所以**一個都不刪**。

| 位置 | 檔數 | 大小 | 寫它的腳本 |
|---|---:|---:|---|
| `experiments/2026-09-02-lazy-prices/data/submissions/` | 573 | 0.84 MB | `fetch_sections.py` 的 `SUBS` |
| `experiments/2026-09-02-narrative-layers/data/submissions/` | 573 | 0.84 MB | `fetch_item1.py` 的 `SUBS` |
| `experiments/2026-09-02-narrative-layers-v2/data/submissions/` | 152 | 0.09 MB | `fetch_text.py` 的 `SUBS` |

**目錄名是個陷阱:** KARST-167 報告把這三個目錄一併數作「副本」,正是被目錄名誤導。
日後開新票時衍生物目錄不要再叫 `submissions`。

---

## 五、指向本目錄的腳本

| 腳本 | 常數 | 說明 |
|---|---|---|
| `experiments/2026-09-03-smallcap-universe-build/collect_submissions.py` | `CACHE` | KARST-167 寫入本快取的那一支 |
| `experiments/2026-09-03-smallcap-universe-build/build_universe.py` | `CACHE` | 讀本快取建宇宙表;`first_filing_date` 已計 `filings.files[].filingFrom`(見第二節) |
| `experiments/2026-09-02-fundamentals-panel/resolve_cik_extra.py` | `CACHE` | KARST-174 由票目錄改指本快取 |
| `experiments/2026-09-02-silent-revisions/fetch_8k402.py` | `EXISTING`、`PAGES_CACHE` | KARST-174 主檔改指本快取;**KARST-177** 分頁檔寫入路徑再改指本快取的 `pages/`(原本仍留在票目錄,因為當時正本不收分頁檔;現在收了) |
| `experiments/2026-09-03-submissions-backfill/collect.py` | `SRC_DIRS`、`PAGES` | KARST-177 一次性收編腳本(Move-Item 1,051 分頁 + 99 宇宙外主檔) |
| `experiments/2026-09-03-submissions-backfill/find_missing.py`、`fetch_shards.py` | `CANON`、`PAGES` | KARST-177 一次性補抓腳本(餘 1,765 個分頁) |
| `experiments/2026-09-03-submissions-backfill/completeness.py` | `CANON`、`PAGES` | KARST-177 寫 `completeness.csv` |

上表三、四兩支的抓取邏輯**沒有改動**,只改了路徑常數。三支都仍然是「先查快取、
查不到才打 EDGAR」;寫入時**不會補寫 `manifest.jsonl`**,所以它們若真的重跑並新抓,
會在本目錄產生未登記檔——重跑之前要先補登記步驟。
