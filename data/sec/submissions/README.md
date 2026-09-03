# 申報索引單一快取(EDGAR submissions)

倉內唯一一份 SEC 申報索引(submissions index)副本。D-134 用戶定的黃金原則:同一份原料
只准有一份副本,有 manifest、有校驗。任何票要查一家公司交過什麼、幾時交、表格類型、
掛牌代號、SIC、entityType,一律讀這裡,**不要另存一份**。

- 位置:`C:\projects\Karst\data\sec\submissions\`
- 檔案:`CIK<十位補零>.json`(EDGAR 原檔位元,不曾解碼、不曾改寫)
- 逐份索引:`manifest.jsonl`(每份一行,**只准 append,不准整檔重寫**)
- 目錄層索引:`manifest.csv`(本倉每一個申報索引位置的登記,見第四節)
- 現況(2026-09-03 KARST-174 核算):**8,012 份、643.1 MB**;manifest.jsonl 8,012 行,
  與檔數一致

倉根的 `data/` 已被 `.gitignore` 擋住,所以 `.json` 與 `manifest.jsonl` 不入 git;
本 README 與 `manifest.csv` 是說明與登記,不是數據,已用 `git add -f` 納入版本控制。

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

## 二、⚠ 這份快取有一塊是不完整的(必讀)

**EDGAR 的 `CIK##########.json` 只載最近約 1,000 份申報。** 更早的歷史不在檔內,
而是由檔內 `filings.files` 欄列出一批**分頁檔**(`CIK##########-submissions-00N.json`),
要另行抓取。

**本快取一個分頁檔都沒有存。** 2026-09-03 逐份查證的結果
(`experiments/2026-09-03-submissions-dedup/check_shard_gap.py`,
結果 `out/shard_gap.json`):

| 項目 | 數 |
|---|---:|
| 快取檔數 | 8,012 |
| **其中 `filings.files` 非空(即申報史被截短)** | **2,066(25.8%)** |
| 這 2,066 份合共聲明的分頁檔 | 2,736 |
| **本快取存有的分頁檔** | **0** |

**實例:** 雅培 CIK 0000001800,本快取那份只有 2018-06-05 至 2026-08-27 的 1,002 份申報;
1994-02-14 至 2018-06-03 的 2,612 份住在它聲明的兩個分頁檔內,本快取沒有。

**後果:** 任何用這份快取算「首次申報日」「上市年份」「歷史申報密度」的票,
**在那 2,066 家(四分之一)身上會系統性偏遲**——看到的最早申報日其實是第 1,000 份那一份,
不是真正第一份。KARST-167 的「按首次申報年」分佈表(報告 §2.4)受這一格影響;
`experiments/2026-09-02-chain-layers/build_v2.py` 第 86 行早已獨立踩過同一個坑並記下。

**用之前要做的事:** 讀 `filings.recent` 之前先看 `filings.files` 是否非空;
非空即代表手上這份是截短的,要按需另抓分頁檔(見第三節第 3 條)。

---

## 三、新增與更新的規則

1. **抓之前先查這裡。** 用 `CIK<十位補零>.json` 查;檔存在就直接讀,不要再打 EDGAR。
   這是單一副本原則落地的那一步。
2. **速率上限每秒 10 次**,並帶 SEC 要求的 `User-Agent`(真實聯絡電郵)。超速會被封 IP。
3. **要完整申報史就要連分頁檔一齊抓**:讀 `filings.files`,逐個抓
   `https://data.sec.gov/submissions/<name>`。分頁檔**目前不入本快取**——
   收編與否已在 KARST-174 舉手待裁(見第四節註),未有裁決之前放回票目錄作衍生物。
4. **manifest.jsonl 只 append,不整檔重寫。** 隨時可能有另一隊同時在寫。
   真的要改既有行,先讀最新版、只改自己那些行、其餘原樣寫回。
5. **`fetchedBy` 填票號或隊名**,不要留空、不要填人名。
6. **衍生物不放這裡。** 由申報索引切出來的東西(10-K 清單、申報窗、8-K 4.02 索引之類)
   放回各自的票目錄,靠 CIK 指回這裡的正本。這是 D-134 決策第 2 條明文准許的。
7. **內容一律當位元處理**:複製搬移用 `Copy-Item`/`Move-Item`,不要用 shell 解碼讀寫。

---

## 四、本倉其他申報索引位置(KARST-174 盤點)

`manifest.csv` 是這一節的機讀版。KARST-174 逐檔核過 sha256(11,075 個檔),
把與正本完全相同的 **514 份、89.2 MB** 刪走,其餘按 D-157「不同者一律保留」留在原位。

### 4.1 真副本目錄(刪完之後餘下的都是與正本不同的)

| 位置 | 現存 | 大小 | 留下的是什麼 |
|---|---:|---:|---|
| `experiments/2026-09-02-fundamentals-panel/data/submissions/` | 78 | 11.3 MB | 2 份同 CIK 但內容有異 + 76 份正本沒有的 CIK |
| `experiments/2026-09-02-silent-revisions/data/submissions/` | 1,173 | 244.5 MB | 1,051 個**分頁檔**(226.9 MB)+ 99 份內容有異 + 23 份正本沒有的 CIK |

**差異的成因逐項:**

- **分頁檔(1,051 個,226.9 MB)** —— 正本**完全沒有這一類檔**,不是冗餘,是正本缺的一塊
  (見第二節)。它補得回 2,736 個聲明分頁之中的 971 個(35.5%),
  令 **553 家公司**的申報史完整。**這一批若當副本刪掉,是刪走無法從正本復原的原料。**
- **同 CIK 但內容有異(101 份,14.5 MB)** —— 副本抓於 2026-09-02,正本抓於 2026-09-03,
  期間 EDGAR 多了新申報。逐份比正本細約 16 KB,即副本是正本的**較舊子集**,
  沒有正本沒有的資料。保留只為守「不同者一律保留」,不是因為有獨立價值。
- **正本沒有的 CIK(99 份,14.2 MB)** —— 那些 CIK 不在 v0 宇宙的 8,001 個之內
  (KARST-167 只抓宇宙內的),所以正本無對應檔可比。**這 99 份是正本真正欠缺的原料。**

> **註(待裁):** 上面兩類正本沒有的東西——1,051 個分頁檔與 99 份宇宙外 CIK——
> 按 D-134 單一快取原則本應收編入本目錄並補寫 manifest,但 KARST-174 票面明文
> 「不擅自合併」,故只登記不搬。已在 KARST-174 舉手請裁。
> **在裁決之前,本目錄不是「全部申報索引原料」的唯一位置,只是「v0 宇宙最新一版」的唯一位置。**

### 4.2 衍生物目錄(不是副本,不受單一快取原則管)

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
| `experiments/2026-09-03-smallcap-universe-build/build_universe.py` | `CACHE` | 讀本快取建宇宙表 |
| `experiments/2026-09-02-fundamentals-panel/resolve_cik_extra.py` | `CACHE` | KARST-174 由票目錄改指本快取 |
| `experiments/2026-09-02-silent-revisions/fetch_8k402.py` | `EXISTING` | KARST-174 由票目錄改指本快取(`CACHE` 仍在票目錄,因為它要存正本不收的分頁檔) |

上表三、四兩支的抓取邏輯**沒有改動**,只改了路徑常數。兩支都仍然是「先查快取、
查不到才打 EDGAR」;寫入時**不會補寫 `manifest.jsonl`**,所以它們若真的重跑並新抓,
會在本目錄產生未登記檔——重跑之前要先補登記步驟。
