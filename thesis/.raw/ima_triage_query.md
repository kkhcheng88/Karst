# IMA 外資研報 —— 標準檢索查詢(每日貼一次)

> **用途**:一日 100+ 份研報,唔可能全讀。呢條查詢做**分流**——只搵出掂到 Karst 17 個 active
> theme 嘅嗰幾份,人手導出 PDF 之後先做 INGEST。
>
> **紀律(2026-07-17 定)**:
> - **AI 攞嚟「搵」= 可以**(檢索任務,開返個檔就驗到)
> - **AI 攞嚟「答」= 唔可以**(摘要當證據 = 驗唔到、追唔到源頭,同「高盛個模型話」冇分別)
> - 所以**只問「邊幾份提到 X」,唔問「呢啲報告話乜」**。
> - 來源紀律照 zsxq PDF:單一策展渠道,**唔升 n_sources**;投行報告 = Tier-2 觀點 + 內含可升格
>   Tier-1 硬數據(佢引嘅 filing / 管理層原話先算)。
>
> 產物路徑慣例:導出 PDF 放 `thesis/.raw/ima/pdf/`,檔名加日期 prefix(同 `thesis/.raw/zsxq/pdf/` 一樣)。

---

## 貼落 IMA 嘅查詢(檢索,唔係分析)

```
列出今日(或指定日期)研報入面,標題或內文提及以下任何一個 ticker / 公司嘅報告。
只需要:報告標題、投行、日期、提及嘅 ticker。
唔需要總結內容,唔需要分析,唔需要你嘅睇法。

AAOI, AEHR, AMKR, AMZN, ASML, ASTS, ASX, ATI, AVGO, AXTI, BE, BKSY, CAT, CHPX,
CLS, COHR, COP, CRS, CVX, DRAM, EQT, ETN, FN, FORM, FOTO, FSLR, GEV, GLW, GNRC,
GOOGL, GRID, GSAT, HEI, INTC, KLAC, KLIC, KMI, KTOS, LITE, LNG, LOAR, LPX, LRCX,
LUNR, LWLG, MAGS, META, MKSI, MP, MPWR, MRVL, MSFT, MU, NASA, NVTS, ON, PL, PWR,
QQQ, RDW, REMX, RKLB, SEI, SIVE, SKHY, SMH, SNDK, SPCX, SPXC, STX, TER, TSM,
TTMI, TXN, URA, USAC, USAR, UTES, VICR, VRT, WDC, WOLF, WST, XLE, XOM

另外,以下主題關鍵詞命中都要列出(唔限於上面 ticker):
半導體資本開支 / 先進封裝 / 混合鍵合 / 玻璃基板 / CoWoS / CoPoS / HBM / DRAM 合約價 /
NAND / EUV / High-NA / 800V HVDC / 資料中心供電 / SiC / GaN / 光通訊 / CPO / 矽光子 /
稀土 / 太空發射 / 衛星 / GLP-1 / 天然氣壓縮 / LNG
```

---

## 逐 theme ticker(如果要窄查)

| theme | tickers |
|---|---|
| advanced-packaging | AMKR, ASX, FORM, GLW, INTC, KLAC, KLIC, LRCX, MKSI, STX, TER, TTMI, WDC |
| aerospace-specialty-alloys | ATI, CRS |
| ai-power-grid | BE, CAT, ETN, GEV, GNRC, GRID, MPWR, NVTS, ON, PWR, SPXC, TXN, URA, UTES, VICR, VRT, WOLF |
| euv-lithography-monopoly | ASML |
| gas-compression-equipment | USAC |
| glp1-biologics-packaging | WST |
| mag7-hyperscaler | AMZN, GOOGL, MAGS, META, MSFT, QQQ |
| memory-supercycle | DRAM, MU, SKHY, SNDK, WDC |
| oil-gas-energy | COP, CVX, EQT, KMI, LNG, SEI, XLE, XOM |
| photonics-optical | AAOI, AXTI, COHR, FN, FOTO, GLW, LITE, LWLG, MRVL, SIVE |
| rare-earth-materials | MP, REMX, USAR |
| semicap-equipment | AEHR |
| semiconductor-cycle | AVGO, MU, QQQ, SMH, TSM |
| space-satellite | ASTS, BKSY, GSAT, HEI, KTOS, LOAR, LUNR, NASA, PL, RDW, RKLB, SPCX |
| specialty-siding-pricing-power | LPX |
| tpu-custom-silicon | AVGO, CHPX, CLS, TSM |
| us-solar-manufacturing | FSLR |

---

## 之後點做(同 zsxq 27 份 PDF 完全一樣嘅流程)

1. IMA 出名單 → 用戶揀 2-5 份最相關嘅,導出 PDF 落 `thesis/.raw/ima/pdf/`
2. Claude 分流(A/B/C 類,同 `thesis/.raw/zsxq/PDF_TRIAGE.md` 一樣格式)
3. A 類先行完整 INGEST:硬數據 vs 觀點分開 → Level-1 red-team → STRENGTHEN/NEUTRAL/WEAKEN
4. lint 零 ERROR 先 commit

**基準參考(2026-07-17)**:六份真.投行 PDF(MS/JPM/HSBC)行完 INGEST **全部 NEUTRAL,零 confidence 變動**
—— 呢個閘唔易過,連 sell-side 一手報告都過唔到。所以「一日 100 份」入面真正有增量嘅,
現實估計係**每星期 0-2 份**。分流嘅價值就係唔使為咗嗰 0-2 份去讀 700 份。
