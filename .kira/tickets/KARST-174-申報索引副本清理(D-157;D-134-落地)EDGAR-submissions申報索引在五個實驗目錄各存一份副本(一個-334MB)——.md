---
id: KARST-174
title: 申報索引副本清理(D-157;D-134 落地):EDGAR submissions/申報索引在五個實驗目錄各存一份副本(一個 334MB)——定一份正本位置(data/sec/submissions/ 或現有最完整那份),其餘逐檔核 sha256 與正本相同才刪,不同者保留並列出差異;所有引用該副本的腳本改指向正本;不動 10-K 文本快取與 companyfacts
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: Claude Opus 5
deliverable: KARST-D02
closed: 2026-09-03
---

## 工作內容

背景:KARST-167 報告(research/2026-09-03-小型股宇宙v0盤點.md)發現申報索引(EDGAR submissions/bulk index)在五個實驗目錄各存一份副本,D-134 單一副本原則在這一格從未落地。先讀:D-134、D-153、D-157;data/sec/10k_text/README.md(單一快取範本);該報告列出的五個位置。做法:①盤點:列出每份副本的路徑、大小、sha256、抓取日期(檔內或 manifest)、被哪些腳本引用(Grep);②定正本:最完整或最新那份搬入 data/sec/submissions/(Move-Item 整檔位元操作,不解碼內容),寫 README.md(來源、抓取日期、格式、更新方法)與 manifest.csv;③其餘副本:sha256 與正本相同者刪除(Remove-Item),不同者保留原位並在 README 列出差異(大小、日期、行數差),不擅自合併;④引用它們的腳本改路徑指向正本(只改路徑常數,不改邏輯),每個改動列在票上留言;⑤刪除前把清單寫進票上留言(路徑、大小、sha256、與正本相同的證據),刪除後再留言確認;⑥不動 10-K 文本快取、companyfacts、價格庫;生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9。禁區:中文檔只經 Read/Write/Edit;絕對路徑;PS 5.1 無 &&;不建目錄連結指向 data/;>5MB 不入 git(README、manifest 用 git add -f)。完成:AC 逐格用 Edit 剔 [x],comment 後 close;要人裁用四格 raise 加 docs 鍵。

## 驗收條件

- [x] 票上留言列齊五份副本的路徑、大小、sha256、引用腳本,刪除前後各一則留言
- [x] data/sec/submissions/ 正本連 README.md 與 manifest.csv(git add -f);與正本相同的副本已刪,不同者保留並在 README 列出差異
- [x] 引用副本的腳本改指向正本,只改路徑常數;10-K 文本快取、companyfacts、價格庫不動
- [x] 生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9;commit 用 git commit --only -F <訊息檔> -- <自己的檔>

## 結果

## 留言

### agent:Claude Opus 5 · 2026-09-03 09:02
\## 刪除前盤點(五份「副本」逐份核完 sha256)

盤點腳本 `experiments/2026-09-03-submissions-dedup/compare_copies.py`(只讀),逐檔結果 `out/inventory.csv`(8,012 正本 + 3,063 副本檔全部算過雜湊)。

\### 一、先更正票面一個前提:五份之中只有兩份是真副本

| # | 位置 | 檔數 | 大小 | 是什麼 |
|---|---|---:|---:|---|
| 1 | `data/sec/submissions/` | 8,013 | 643.1 MB | **正本**(8,012 份 + manifest.jsonl) |
| 2 | `experiments/2026-09-02-fundamentals-panel/data/submissions/` | 110 | 15.4 MB | 真副本,`CIK##########.json` 全本 |
| 3 | `experiments/2026-09-02-silent-revisions/data/submissions/` | 1,655 | 329.6 MB | 真副本 + EDGAR 分頁檔 |
| 4 | `experiments/2026-09-02-lazy-prices/data/submissions/` | 573 | 0.84 MB | **衍生物**,不是副本 |
| 5 | `experiments/2026-09-02-narrative-layers/data/submissions/` | 573 | 0.84 MB | **衍生物**,不是副本 |
| 6 | `experiments/2026-09-02-narrative-layers-v2/data/submissions/` | 152 | 0.09 MB | **衍生物**,不是副本 |

第 4–6 項目錄名叫 `submissions`,但檔名是裸 CIK(`0000001800.json`)、每份約 1.8 KB,內容是 `[[filingDate, reportDate, accession, primaryDoc], …]` 的 10-K 清單,即由申報索引切出來的衍生物。D-134 決策第 2 條明文准許「實驗票目錄只存衍生物」,所以**這 1,298 個檔不是違規,一個都不刪**。KARST-167 報告把它們一併數作副本,是被目錄名誤導。

\### 二、正本定在哪:維持 `data/sec/submissions/`,不搬

理由:KARST-167 已把 8,012 份收進去並寫了 `manifest.jsonl`(逐份 CIK、來源網址、位元組、sha256、抓取時間),是現存最完整、最新(2026-09-03)、唯一有 manifest 的一份。第 2、3 項全部抓於 2026-09-02,較舊。不需要 Move-Item。

\### 三、擬刪清單:514 檔、89.2 MB

| 來源 | 刪 | 釋出 |
|---|---:|---:|
| fundamentals-panel | 32 | 4.1 MB |
| silent-revisions | 482 | 85.1 MB |
| **合計** | **514** | **89.2 MB** |

逐檔清單(路徑、位元組、sha256、正本對應檔)在 `experiments/2026-09-03-submissions-dedup/out/delete_list.csv`,514 行。抽四行示例:

```
fundamentals-panel  ...\CIK0000004281.json  166841  56cf76eb61c178071f2aa78096a28f9fa5dc3a42d110652770c5a9323218a6ea
fundamentals-panel  ...\CIK0000009389.json  168898  ff599307920ccd6201b095890a43825b3e65a6da5ad39b33dd148f6543e7d582
silent-revisions    ...\CIK0000001800.json  155792  bf947fb6b2449cd72db320e57d64ed250ce49188289fef55f809de148d1c48dd
silent-revisions    ...\CIK0000002488.json  162408  8ac9c389acf86e343f4e81054c2e1a56055e22ae8b6b7f0fe18893da37785ca9
```

**與正本相同的證據:** 每一行的 sha256 都在正本 8,012 份的雜湊表內查得到同值的一份(正本 8,012 份雜湊互不重覆,所以是一對一)。刪除腳本 `delete_identical.py` 在真刪那一刻會**再算一次**該檔 sha256,並確認正本仍有同雜湊的一份,三者對得上才 `os.remove`;對不上就跳過並列出。乾跑跳過 0 檔。

\### 四、保留清單:不同的一律不刪(1,254 檔、256.2 MB)

| 類別 | 檔數 | 大小 | 為什麼不同 |
|---|---:|---:|---|
| EDGAR 分頁檔(silent-revisions) | 1,051 | 226.9 MB | **正本完全沒有這種檔**,見下節 |
| 同 CIK 但內容有異 | 101 | 14.5 MB | 抓於 09-02,正本抓於 09-03,期間多了新申報;逐份比正本細約 16 KB |
| 正本沒有的 CIK | 99 | 14.2 MB | 該 CIK 不在 v0 宇宙 8,001 個之內,正本無對應 |
| 衍生物(第 4–6 項目錄) | 1,298 | 1.8 MB | 不是申報索引本體,D-134 准許 |

\### 五、附帶查證:那個 334 MB 目錄大部分不是冗餘,是正本缺的一塊

查證腳本 `check_shard_gap.py`,結果 `out/shard_gap.json`:

- EDGAR 的 `CIK##########.json` 只載**最近約 1,000 份**申報,更早的歷史放在它自己 `filings.files` 欄列出的分頁檔。
- 正本 8,012 份之中 **2,066 份(25.8%)是截短的**,合共聲明了 **2,736 個分頁檔,正本一個都沒有存**。
- silent-revisions 那 1,051 個分頁檔補得回其中 **971 個(35.5%)**,令 **553 家公司**的申報史完整。
- 實例:雅培(CIK 0000001800)正本只有 2018-06-05 至 2026-08-27 那 1,002 份;1994-02-14 至 2018-06-03 的 2,612 份全部住在那兩個分頁檔內。

即:**單一快取在四分之一的公司身上其實不完整,而補得回的那部分現時住在一個實驗目錄。** 若當初照「334 MB 是副本」整個刪掉,會刪走 226.9 MB 無法從正本復原的原料。本票不合併(票面明文「不擅自合併」),只記錄;收編與否已另開 `raise` 請裁。

\### 六、不碰的東西

10-K 文本快取 `data/sec/10k_text/`、`data/sec/companyfacts/`、`data/prices/`、`data/panel/`、`data/universe/` 全部沒有讀寫。生產庫 `karst.sqlite` 只讀,開工核 SHA256 首 16 位 = `b168e9f45b578cf9`,相符。

下一則留言確認刪除結果。

### agent:Claude Opus 5 · 2026-09-03 09:05
**問題**：申報索引單一快取只有近千份的近期申報,四分之一公司(2,066 家)的舊申報史缺失;補得回那部分的原料現時住在一個實驗目錄,要不要收編入 data/sec/submissions/?

**前文後理**：KARST-174 逐檔核 sha256 時查出:EDGAR 的 CIK<十位>.json 只載最近約 1,000 份申報,更早的歷史要另抓它 filings.files 欄列出的分頁檔。正本 8,012 份之中 2,066 份(25.8%)是截短的,合共聲明 2,736 個分頁檔,正本一個都沒有存。KARST-167 建這份快取時沒有察覺這一格。後果:任何用正本算「首次申報日」「上市年份」的票,在那 2,066 家身上會系統性偏遲——看到的最早申報日其實是第 1,000 份那一份。KARST-167 報告 §2.4 的「按首次申報年」分佈表就是這樣算出來的;experiments/2026-09-02-chain-layers/build_v2.py 第 86 行早已獨立踩過同一個坑。實驗目錄 2026-09-02-silent-revisions 存有 1,051 個分頁檔(226.9 MB),補得回 2,736 個之中的 971 個(35.5%),令 553 家公司的申報史完整;另有 99 份正本沒有的 CIK 全本(14.2 MB,那些 CIK 不在 v0 宇宙之內)。本票票面明文「不擅自合併」,所以我只登記不搬,現時原地保留。

**建議**：我押要收編,而且值得補齊,但不是現在做。三點理由:①這不是儲存問題,是正確性問題——四分之一公司的申報史被無聲截短,而快取的名字叫「單一正本」,下一個人不會想到要自己查 filings.files;README 已寫警告,但警告靠人記得讀,結構才靠得住。②收編那 1,051 個分頁檔是純位元搬移加補 manifest,零 EDGAR 請求、零風險;99 份宇宙外 CIK 同理。③但補齊剩下那 1,765 個未抓的分頁檔要打 EDGAR,按 KARST-167 實測每秒 8 個請求算約 4 分鐘,成本近零——只是它應該由一張自己的票做,連同「首次申報日」那一格的重算,而不是塞進這張清副本票。我不建議把它併入現正在跑的 KARST-171/172/173:那三張正在寫 data/,同時改 submissions 的 manifest 會撞。

**選項**：
- 甲（建議）：開一張新票:收編 1,051 個分頁檔與 99 份宇宙外 CIK 入正本、補 manifest、補抓餘下 1,765 個分頁檔,並重算 KARST-167 的首次申報年分佈 —— 把正確性缺口一次補實,而且不與正在跑的三張票爭 data/;成本約 4 分鐘機器時間加一次重算
- 乙：只收編現有的 1,051 個分頁檔與 99 份 CIK,不補抓、不重算,餘下的缺口留在 README 當已知偏差 —— 零 EDGAR 請求、最快收乾淨,但四分之一公司仍有三分之二的分頁缺失,首次申報日照樣偏遲
- 丙：維持現狀:分頁檔留在實驗目錄,只靠 README 第二節的警告 —— 改動最少,但單一快取名不副實,而那 226.9 MB 原料掛在一張已關的票的目錄下,下一次清理很容易被當副本刪走

**要睇邊份稿**：
- data/sec/submissions/README.md
- research/2026-09-03-小型股宇宙v0盤點.md

### agent:Claude Opus 5 · 2026-09-03 09:08
\## 刪除後確認

\### 一、刪除結果:514 檔、89.2 MB,零跳過

腳本 `delete_identical.py --apply`。逐檔在 `os.remove` 那一刻**再算一次** sha256、再確認正本仍有同雜湊的一份,三者對得上才刪。跳過 0 檔,即 514 檔全部通過即場覆核。

| 來源 | 刪 | 釋出 | 刪前 | 刪後 |
|---|---:|---:|---:|---:|
| fundamentals-panel | 32 | 4.1 MB | 110 檔 / 15.4 MB | **78 檔 / 11.3 MB** |
| silent-revisions | 482 | 85.1 MB | 1,655 檔 / 329.6 MB | **1,173 檔 / 244.5 MB** |
| **合計** | **514** | **89.2 MB** | | |

**正本一個檔都沒有改:** `data/sec/submissions/` 刪前刪後同為 8,013 檔 / 643.1 MB(8,012 份 + manifest.jsonl)。`manifest.jsonl` 沒有寫過,仍是 8,012 行,與檔數一致。

**保留的沒有動:** 三個衍生物目錄(lazy-prices 573、narrative-layers 573、narrative-layers-v2 152)檔數與大小分毫不變;silent-revisions 的 1,051 個分頁檔全數在原位。

覆核:刪走的 `CIK0000001800.json` 在正本查得到,而它的分頁檔 `CIK0000001800-submissions-001.json` 正本沒有、實驗目錄仍在——即刪的只有真冗餘,無法復原的一份都沒碰。

\### 二、正本連 README.md 與 manifest.csv

- `data/sec/submissions/README.md` —— 來源、抓取日期與速率、User-Agent、格式、`manifest.jsonl` 欄位、更新規則七條;**第二節是那個不完整警告**;第四節逐項列出保留副本的差異與成因;第五節列出指向本目錄的四支腳本。
- `data/sec/submissions/manifest.csv` —— 目錄層登記,一行一個申報索引位置(正本 + 五個),欄位:位置、角色、檔名式樣、內容、檔數、位元組、抓取日、本票之後狀態、註。

**一個要講明的取捨:** 逐份索引本來就有 `manifest.jsonl`(8,012 行,KARST-167 寫)。再出一份逐份的 `manifest.csv` 等於把同一個索引存兩份——正是本票在清的那件事。所以 `manifest.csv` 做成**目錄層**登記,不重覆 jsonl。README 第一節寫明兩者分工。若判斷這不符驗收條件原意,請講,我改成逐份版。

兩份都是說明不是數據,已按票面用 `git add -f` 越過 `data/` 的 gitignore。

\### 三、腳本改動:兩支,各一處,只改路徑常數

**1. `experiments/2026-09-02-fundamentals-panel/resolve_cik_extra.py` 第 36 行**

```
- CACHE = HERE / "data" / "submissions"
+ CACHE = REPO / "data" / "sec" / "submissions"
```

讀寫都改指單一快取。`submissions()` 的抓取邏輯(先查快取、查不到才打 EDGAR)一字未改。`REPO` 早在第 33 行定義,次序無問題。

**2. `experiments/2026-09-02-silent-revisions/fetch_8k402.py` 第 40 行**

```
- EXISTING = PANEL_DIR / "data" / "submissions"
+ EXISTING = REPO / "data" / "sec" / "submissions"
```

`load_or_fetch()` 的三層退路(本地 → EXISTING → EDGAR)結構不變,只是第二層由 fundamentals-panel 的副本改指正本。**`CACHE` 刻意不改**,理由:它要存 EDGAR 分頁檔,而正本現時不收分頁檔,把 `CACHE` 指過去等於一重跑就把 1,000 多個分頁檔寫進正本 —— 那是票面明文禁止的「擅自合併」。

這一改剛好令刪除安全閉環:silent-revisions 那 482 個被刪的全本,重跑時會由第二層在正本找回,不會多打一次 EDGAR。

兩支都過 `python -m py_compile`。三支本票新腳本(`compare_copies.py`、`check_shard_gap.py`、`delete_identical.py`)同樣通過。

**沒有改但要記一筆:** 三個衍生物目錄的腳本(`fetch_sections.py`、`fetch_item1.py`、`fetch_text.py`)的 `SUBS` 常數**不改**——它們存的是衍生物,指向正本反而會把衍生物寫進原料快取,是製造違規不是修正。但這三支確實有另一個 D-134 第 1 條問題:它們直接打 EDGAR 取申報索引,沒有先查單一快取。修它要改抓取邏輯,超出本票「只改路徑常數」的界,沒有做,在此記低。

\### 四、假設冊與受影響的票

- **A-046 立(`overturned`)**:「單一快取載有完整申報史」查證為假。寫得出的後果:KARST-167 §2.4「按首次申報年」分佈表對老公司系統性偏遲、D-147 迷因硬排除 R5(上市未滿兩年)在那 2,066 家身上會漏判。
- 已在 **KARST-167** 留言記錄影響(票已關,不倒推階段)。

\### 五、禁區覆核

| 項目 | 狀態 |
|---|---|
| `data/sec/10k_text/` | 沒有讀寫 |
| `data/sec/companyfacts/`、`data/prices/`、`data/panel/`、`data/universe/` | 沒有讀寫(另一隊 KARST-171/172/173 在用) |
| 生產庫 `karst.sqlite` | 只讀;開工與收工 SHA256 首 16 位皆 `b168e9f45b578cf9` |
| symlink / junction | 一個都沒有建 |
| >5MB 入 git | 無;只有 README.md 與 manifest.csv 用 `git add -f` |

### agent:Claude Opus 5 · 2026-09-03 09:11
\## 收工:工作做完,票**未關**

驗收條件四格全部剔齊,commit `1ccdead`(14 檔,只有本票的檔;另一隊 KARST-171/172/173 的 `data/universe/RULES.md`、`experiments/2026-09-03-price-library/` 與它的票核過沒有帶走)。

**關不到檔的原因:** 本票舉了手未答,守閘擋住 `close`,這是對的——那條要裁的事(1,051 個分頁檔與 99 份宇宙外 CIK 收不收編入正本)我不會自問自答。

**收口做法:** 有人裁了之後跑 `answer` 清招牌,再跑 `close`。

收工核對:生產庫 `karst.sqlite` SHA256 首 16 位 `b168e9f45b578cf9`,與開工相同。

**留給下一手的三句:**

1. 這張票釋出的 89.2 MB 是次要成果。主要成果是查出**正本在四分之一公司身上不完整**(A-046),而這一格會令任何用「首次申報日」做上市日代理的規則出錯——D-147 的迷因硬排除 R5 首當其衝。
2. 那個 334 MB 目錄**不要當副本刪**。裡面 226.9 MB 是正本沒有的分頁檔,刪了要重新打 EDGAR 才拿得回。
3. 三個名叫 `submissions` 的衍生物目錄**不是違規**。日後開票時衍生物目錄不要再叫這個名,免得下一個人再誤判一次。

### agent:Claude Fable 5.1 · 2026-09-03 11:19
**裁決**：答甲:開票收編 1,051 個歷史分頁與 99 份宇宙外公司入正本,補抓餘下 1,765 個分頁,重算首次申報年分佈,A-046 依結果更新(D-161)。丙否決:警告靠人記得讀,結構才靠得住;227MB 掛在已關票的目錄下,下次清理會再被當副本。

**出處**：D-161
