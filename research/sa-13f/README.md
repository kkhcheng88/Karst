# Situational Awareness LP —— 13F 持倉逐季事實表(KARST-019)

> 用途:給 D-022(人物判官)當答案紙。純事實整理,不含「應否跟隨」之類的投資判斷。
> CIK:2045724(SEC EDGAR)。查證日期:2026-08-27。
> 對應票:KARST-019。相關背景檔:`research/2026-08-27-sa-fund-status.md`。

## 一、總覽

本次直接向 SEC EDGAR submissions API(`https://data.sec.gov/submissions/CIK0002045724.json`)
核對該基金全部申報紀錄,共找到 **7 期 13F-HR**,涵蓋 **2024Q4 至 2026Q2**(即申報所涵蓋的
持倉期間,不是申報日)。

**重要:比原先已知的三期(2025Q4、2026Q1、2026Q2)多出四期更早的申報**——基金首次申報
其實是 **2024Q4(截至 2024-12-31 的持倉,2025-02-12 公開)**,不是原先認為的 2025Q4。
本表已全部核對並收錄,以下每期均查得到 information table 原始 XML,沒有缺口。

## 二、逐季彙總

| 申報期(period) | 申報日(filed_date) | 持倉數(去重後) | 總市值(美元) | 前五大持倉(占比) | Information Table 原始連結 |
|---|---|---|---|---|---|
| 2024Q4(截至 2024-12-31) | 2025-02-12 | 6 | $254,813,765 | Marvell Technology(34.1%)、Vistra(23.2%)、Vertiv Holdings(20.3%)、Talen Energy(11.0%)、Constellation Energy(8.5%) | [infotable.xml](https://www.sec.gov/Archives/edgar/data/2045724/000093583625000120/infotable.xml) |
| 2025Q1(截至 2025-03-31) | 2025-05-14 | 12 | $1,005,567,727 | Intel(45.7%)、Broadcom(11.7%)、Onto Innovation(7.1%)、Vistra(6.1%)、Modine Mfg(5.5%) | [SALP13fq1.xml](https://www.sec.gov/Archives/edgar/data/2045724/000204572425000002/SALP13fq1.xml) |
| 2025Q2(截至 2025-06-30) | 2025-08-14 | 9 | $2,123,023,762 | VanEck ETF Trust(26.9%,詳見第五節疑點)、Intel(21.4%)、Broadcom(15.5%)、Vistra(11.6%)、Core Scientific(6.4%) | [Salpform13fq2.xml](https://www.sec.gov/Archives/edgar/data/2045724/000204572425000006/Salpform13fq2.xml) |
| 2025Q3(截至 2025-09-30) | 2025-11-14 | 25 | $4,138,368,748 | CoreWeave(25.9%)、Intel(16.4%)、Core Scientific(8.7%)、IREN(8.2%)、Nvidia(7.2%) | [SALP13FinfotableQ3.xml](https://www.sec.gov/Archives/edgar/data/2045724/000204572425000008/SALP13FinfotableQ3.xml) |
| 2025Q4(截至 2025-12-31) | 2026-02-11 | 25 | $5,516,758,345 | CoreWeave(22.0%)、Bloom Energy(16.5%)、Intel(13.5%)、Lumentum Holdings(8.7%)、Core Scientific(7.6%) | [SALP_13FQ425.xml](https://www.sec.gov/Archives/edgar/data/2045724/000204572426000002/SALP_13FQ425.xml) |
| 2026Q1(截至 2026-03-31) | 2026-05-18 | 29 | $13,676,657,577 | VanEck ETF Trust(15.0%,詳見第五節疑點)、Nvidia(11.5%)、SanDisk(8.1%)、Oracle(7.8%)、Micron(7.4%) | [salp13fq1xml.xml](https://www.sec.gov/Archives/edgar/data/2045724/000204572426000008/salp13fq1xml.xml) |
| 2026Q2(截至 2026-06-30,**最新一期**) | 2026-08-14 | 24 | $20,242,292,228 | SanDisk(28.0%)、Micron(27.5%)、Bloom Energy(9.6%)、台積電 ADR(6.4%)、Nebius Group(6.1%) | [form13fInfoTable.xml](https://www.sec.gov/Archives/edgar/data/2045724/000093583626000418/form13fInfoTable.xml) |

**與既有背景檔核對一致:** `research/2026-08-27-sa-fund-status.md` 記載的 2026Q1(約 136.8 億美元)
與 2026Q2(約 202.4 億美元、前五大占比約 77%)兩項第三方轉述數字,與本次直接核對 SEC 原始
XML 算出的結果**完全吻合**(2026Q1 總市值 $13,676,657,577;2026Q2 前五大合計占比
28.03%+27.54%+9.60%+6.37%+6.09%=約77.6%)。2026Q2 持倉數第三方轉述為「25 個」,
本表逐 CUSIP 去重後為 24 個——差異來自原始 XML 有 2 個 CUSIP 各拆成兩行(可能是投票權
分列或代理人重複填寫),本表已依 CUSIP 彙總為單一持倉,判斷 24 為正確去重後數字。

**持倉數逐季暴增,反映基金規模快速膨脹:** 從首期(2024Q4)僅 6 檔、總市值 2.5 億美元,
一路增加到 2026Q2 的 20 多檔、200 億美元以上,與外部報導的基金爆炸性成長軌跡一致
(參見 `2026-08-27-sa-fund-status.md` 記載的高峰資產規模約 450 億美元)。

## 三、逐季持倉明細(CSV)

完整持倉/變動明細見同目錄 `holdings.csv`,共 165 列(不含表頭),欄位:

`period, filed_date, issuer, ticker, cusip, shares, value_usd, weight_pct, change_vs_prev`

- `period`:持倉所涵蓋的季度(依 `periodOfReport` 換算,不是申報日)
- `value_usd`:美元金額(單位換算說明見第四節)
- `weight_pct`:該持倉占當期申報總市值百分比(已剔除已清倉的 0 元列)
- `change_vs_prev`:依 CUSIP 比對上一期(找不到對應 CUSIP 時退回用發行人名稱),
  標示「新增(首次揭露)」「加倉(+N股)」「減倉(-N股)」「清倉(-N股)」「不變」——
  已知的三筆 CUSIP 填寫不一致案例(見第五節)已人工修正為連續持倉的加倉,不計入
  誤判的「清倉+新增」配對。

## 四、value 欄位單位換算說明(重要)

SEC 13F 表格說明書規定 `<value>` 欄位應以「千美元」(thousands of dollars)為單位申報,
但**實測核對本基金全部 7 期申報後確認,該欄位實際填寫的就是美元金額本身,未依規定
換算成千美元**。核對依據:

1. 用已知的外部核實數字核對——2026Q2 期用原始 `<value>` 直接加總得總市值約 202.4 億
   美元,且逐檔占比(SanDisk 28.0%、Micron 27.5%、Bloom Energy 9.6%、台積電 6.4%、
   Nebius 6.1%)與 `research/2026-08-27-sa-fund-status.md` 記載的第三方轉述數字完全吻合。
   若依規定把 `<value>` 當千美元再乘 1000,總市值會變成約 20.24 兆美元,明顯離譜。
2. 逐檔用「value ÷ shares」推算隱含每股價格,結果落在合理股價區間(例如 2024Q4
   Marvell 隱含每股約 110.45 美元、2025Q1 Intel 隱含每股約 22.71 美元),若額外乘
   1000 則變成不合理的天文數字。

因此本表 `value_usd` 一律**直接採用原始 XML 的 `<value>` 數字,不做 ×1000 換算**。
這代表本基金(或其申報代理人)在該欄位的填法本身就與 SEC 表格說明書字面規定不同,
記此存疑,供日後若有官方更正版本時重新核對。

## 五、有疑點/查不到的地方(逐項列明,不隱瞞)

1. **VanEck ETF Trust 的 ticker 無法對應具體 ETF。** 「VANECK ETF TRUST」是共同註冊
   實體,底下有多檔不同 ETF(各有各的 CUSIP)。本表查到至少兩個不同 CUSIP 都掛在
   同一發行人名稱下(`92189F676` 於 2025Q2、2026Q1 出現;`92189F106` 於 2025Q3、
   2025Q4 出現),兩者股數與隱含每股價格都不同,判斷是**兩檔不同的 ETF**,不是同一
   持倉的 CUSIP 打字誤差,故未合併計算、也未強行對應 ticker(避免瞎猜)。
2. **三筆 CUSIP 前後不一致、判斷為同一持倉的人工修正**(已反映在 `holdings.csv`,
   `change_vs_prev` 欄位有註明):
   - Bloom Energy Corp:2025Q3 用 `093712AH0`,2025Q4 起改用 `093712107`(常見的
     普通股 CUSIP 格式)。判斷依據:發行人名稱相同、股數變化幅度(3,193,802 →
     10,484,522 股)與基金當期大幅加碼能源持倉的整體行為一致。
   - Lumentum Holdings Inc:2025Q3 用 `55024UAD1`,2025Q4 起改用 `55024U109`。
   - Cipher Mining Inc:2025Q3 用 `17253JAA4`,2025Q4 起改用 `17253J106`。
   - 以上三筆的舊 CUSIP 格式(字母+9 碼含字母尾碼)較像選擇權/權證/私募憑證常見
     格式,推測是申報代理人早期誤填,後期改回標準普通股 CUSIP。**這是本表基於
     股數與市值合理性做出的判斷,不是 SEC 官方勘誤,若日後要用於精確會計核對,
     建議另行向 SEC 查證。**
3. **ticker 對應完整度。** 165 列持倉明細中,約半數欄位有把握地填上 ticker(依
   Karst 自身既有市場知識做對照,非另查證的官方交叉比對來源);其餘留空,包括:
   `T1 ENERGY INC`、`WHITEFIBER INC`、`SHARONAI HOLDINGS INC`(注意:此發行人的
   ticker 其實在 Form 3/4 申報中查到是 **SHAZ**,詳見第六節,但因不是從 13F 本身
   查到,`holdings.csv` 內仍留空,避免混用資料源)、`KEEL INFRASTRUCTURE CORP`、
   `CEREBRAS SYSTEMS INC`、以及全部 `VANECK ETF TRUST` 列。這些留空是因為公司較新
   上市、或名稱可能對應多個商品,沒有把握,寧可留空不臆測。
4. **2025Q4「INTEL CORP」股數從 20,237,400 變成 20,237,401(僅 +1 股)。** 已在
   `change_vs_prev` 標為「加倉(+1股)」,推測是四捨五入或代理人填寫誤差,金額變化
   極小(占比影響可忽略),故如實記錄,不做主觀修正。
5. **本表未追加抓取「以美元計價的期權/put/call 部位」細節。** 原始 XML 有
   `putCall` 欄位,本次抓取程式有解析但發現全部 7 期本基金均未申報任何 put/call
   分錄(欄位皆為空),故 `holdings.csv` 不含 put/call 欄。若日後基金開始申報選擇權
   部位,`fetch_13f.py` 的 `parse_infotable()` 函式已預留解析邏輯,只需擴充輸出欄位。
6. **未查到任何 13F-HR/A(修正版)。** 全部 7 期均為正本申報,無修正版,故不存在
   「同一期有多個版本互相取代」的問題。

## 六、13F 以外的已知揭露(13D/13G/Form 3/Form 4)

除 13F 之外,本次核對 SEC submissions API 完整申報紀錄,查到以下非 13F 的受益權/
內部人揭露(全部一手,來源 SEC EDGAR),比原先背景檔(`2026-08-27-sa-fund-status.md`)
只記載的一筆(2026-08-04 Core Scientific 13D/A)**多出七筆**:

| # | 表格 | 申報日 | 標的公司 | 揭露內容 | EDGAR 連結 |
|---|---|---|---|---|---|
| 1 | Schedule 13D(首次) | 2025-08-19 | Core Scientific, Inc. | 17,682,918 股,占已發行股份 5.8%;附逐筆買入明細(2025-07-18 至 2025-08-13,每股約 13.19~14.90 美元) | [primary_doc.xml](https://www.sec.gov/Archives/edgar/data/1839341/000093583625000543/primary_doc.xml) |
| 2 | Schedule 13D/A(修正 No.1) | 2025-10-14 | Core Scientific, Inc. | 28,756,478 股,占 9.4% | [primary_doc.xml](https://www.sec.gov/Archives/edgar/data/2045724/000093583625000638/primary_doc.xml) |
| 3 | Schedule 13G | 2026-05-27 | Nebius Group N.V.(Class A Ordinary Shares) | 12,410,060 股,占 5.6%(以 2026-03-31 已發行股數 220,406,311 股計算) | [primary_doc.xml](https://www.sec.gov/Archives/edgar/data/2045724/000093583626000303/primary_doc.xml) |
| 4 | Schedule 13G | 2026-06-29 | SharonAI Holdings Inc. | 5,404,540 股,占 19.9% | [primary_doc.xml](https://www.sec.gov/Archives/edgar/data/2045724/000093583626000334/primary_doc.xml) |
| 5 | Form 3(內部人首次申報) | 2026-06-29(生效日 2026-06-22) | SharonAI Holdings Inc. | 因持股超過 10% 成為須申報內部人,首次揭露 | [ownership.xml](https://www.sec.gov/Archives/edgar/data/2045724/000093583626000333/ownership.xml) |
| 6 | Form 4(內部人交易) | 2026-07-02(交易日 2026-06-30) | SharonAI Holdings Inc. | 行使認股權證(transaction code X)取得 3,700,000 股,行使價每股 0.0001 美元;行使後直接持有 5,396,127 股(另有 2,674,823 股透過預付認股權證間接持有) | [ownership.xml](https://www.sec.gov/Archives/edgar/data/2045724/000093583626000339/ownership.xml) |
| 7 | Schedule 13D/A(修正 No.2) | 2026-08-04 | Core Scientific, Inc. | 14,089,395 股,占 4.4%(較 7/15 時披露的 25,608,473 股/8.1% 大幅減少)——此筆為背景檔已記載的既有事實 | [primary_doc.xml](https://www.sec.gov/Archives/edgar/data/1839341/000091957426004796/primary_doc.xml) |
| 8 | Schedule 13G/A | 2026-08-14 | SharonAI Holdings Inc. | 7,563,029 股,占 19.9% | [primary_doc.xml](https://www.sec.gov/Archives/edgar/data/2045724/000093583626000416/primary_doc.xml) |

**與 13F 交叉核對:** 第 6 筆 Form 4 揭露的「行使後直接持有 5,396,127 股」,與
`holdings.csv` 中 2026Q2 13F 記載的 SharonAI Holdings 持股數(5,396,127 股)完全一致,
互相印證資料可信。

**除以上 8 筆外,本次查證未再查到其他 13D/13G/Form 3/4 申報**(已完整核對 submissions
API 回傳的全部申報紀錄,非抽樣)。SharonAI Holdings 的 ticker 經 Form 3 XML 核對為
**SHAZ**(注意:此為從 13D/13G/Form3/4 文件查到,不是從 13F information table 本身
查到,`holdings.csv` 中該持倉的 ticker 欄位仍依規則留空)。

**期權倉位:** 未另外查到 13F 以外的期權倉位揭露(13F information table 本身的
put/call 欄位全部為空,見第五節第 5 點)。`research/2026-08-27-sa-fund-status.md`
提到 2026Q1 有「$8.46B 名義 put 空頭部位」的第三方轉述,但本次直接核對 2026Q1 原始
XML(`salp13fq1xml.xml`)後,29 筆 infoTable 的 `putCall` 欄位全部為空,**未查到任何
put/call 分錄**——與該第三方轉述數字不符,列為待查疑點,不採信第三方數字。

## 七、腳本

`fetch_13f.py`——可重跑的抓取/整理腳本,邏輯:呼叫 submissions API 取得申報清單、
逐期到 EDGAR 目錄索引頁找出 information table 實際檔名(各期檔名不一致,已處理)、
解析 XML、彙總、輸出 `holdings.csv`。內含完整中文註解,包含 value 單位判斷依據、
CUSIP 別名對照表(對應第五節第 2 點的三筆人工修正)、ticker 對照表來源說明。

執行方式(Windows PowerShell):

```powershell
$env:PYTHONUTF8=1
python research/sa-13f/fetch_13f.py
```

`filings_list.json`——腳本執行後的副產品,記錄每期 accession/申報日/期間/
information table 連結,供人工核對用。
