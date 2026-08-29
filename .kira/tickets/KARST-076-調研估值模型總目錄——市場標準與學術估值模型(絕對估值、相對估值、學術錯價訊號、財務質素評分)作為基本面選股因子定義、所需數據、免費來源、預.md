---
id: KARST-076
title: 調研:估值模型總目錄——市場標準與學術估值模型(絕對估值、相對估值、學術錯價訊號、財務質素評分)作為基本面選股因子:定義、所需數據、免費來源、預測力證據
type: research
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-075]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
closed: 2026-08-29
---

## 工作內容

用戶 2026-08-29 指示(原話「估值模型 especially I want to have a research on market standard and academic based 估值模型. I think this is very valuable for us to have all the 10+ or 100+ 估值模型 in most situation as the quant factor for us. as I think we are doing stock selection. It is either for Swing Trading that based on 1-5, or it is based on fundamentals that is 6-8. … 6-8 is not something I know very well. I just know DCF」)。本票出一份估值模型總目錄,每個模型一行:名稱、一句白話、公式或做法、屬絕對估值 / 相對估值 / 學術錯價訊號 / 財務質素評分哪類、所需輸入(損益表 / 資產負債表 / 現金流量表 / 分析員預測 / 折現率 / 市價)、可否用免費數據算(SEC EDGAR XBRL companyfacts API、yfinance 財務、FRED 利率)、學術或業界預測力證據(出處、樣本期、多空回報或 t 值,OSAP 有對應訊號的註明訊號名)、對 Karst 的適用度(月度橫斷面因子可否直接化)。範圍至少涵蓋:DCF 一族(FCFF、FCFE、DDM 單段 / 多段、APV、剩餘收益 / EVA、實質選擇權)、相對估值一族(P/E、前瞻 P/E、PEG、EV/EBITDA、EV/Sales、P/B、P/S、P/CF、FCF 孳息、股息率、行業特定倍數)、學術錯價與內在價值(Ohlson 1995、Feltham-Ohlson、Frankel-Lee 1998 V/P、Lee-Myers-Swaminathan 1999、Bartram-Grinblatt 2018 agnostic fundamental analysis、Rhodes-Kropf 等 2005 錯價分解、Penman 的會計估值)、財務質素與風險評分(Piotroski F、Mohanram G、Altman Z、Beneish M、Sloan 應計項目、Novy-Marx 毛利率、Fama-French 盈利與投資因子、Greenblatt 魔法公式、Asness QMJ 質素)。另答:(a) 免費財務報表數據源的可行性(EDGAR XBRL companyfacts 覆蓋年份、欄位一致性問題、標普 500 歷史成分含退市公司的覆蓋;Karst 已有 karst/data/cik.py);(b) 分析員預測與折現率輸入的免費替代;(c) 結語:建議首批 10–15 個可用免費數據算的模型、分三期的建置路徑、實測前預期量級。輸出 research/2026-08-29-valuation-models-catalogue.md,總目錄另出 CSV research/2026-08-29-valuation-models-catalogue.csv。不動程式、不動庫。

## 驗收條件

- [x] 總目錄落檔(md + csv),每個模型一行齊八欄,至少 40 個模型,每行有出處
- [x] 免費數據源可行性與首批 10–15 個模型建議,分期建置路徑,預期量級
- [x] 不動程式、不動庫

## 結果

**總目錄 100 個模型**,落 `research/2026-08-29-valuation-models-catalogue.md` 與同名 `.csv`(100 行 × 10 欄,UTF-8 連 BOM)。分類:**絕對估值 18、相對估值 22、學術錯價訊號 32、財務質素評分 28**。每行齊十欄:編號、名稱、類別、白話一句、公式或做法、所需輸入、免費可算、預測力證據出處(附期刊卷期頁碼與 DOI、樣本期、多空回報或 t 值)、OSAP 訊號名、Karst 適用度。

**首批建議 13 個**(準則:只用三張報表加價格、歷史需求不超過四年、有現代複製證據、在大型股沒有已知失效證據):B04 帳面市值比、B01 盈利價格比、B06 銷售價格比、B09 EV/EBITDA、B13 淨派付孳息、C15 資產增長、C12/C13 淨營運資產與其變動、C18 存貨增長、C19 淨外部融資、C20 淨股份發行、C22/C23 盈利意外與收入意外、D16 毛利率、D17 現金基礎營運獲利。

**分三期**:①EDGAR XBRL 數據線(知情時點視圖、代號歷史映射、標籤回退、財報公布日期);②上述 13 個因子加評估管線(**須先補 `karst/factorpredict.py` 缺少的十分位多空組合回報函數**,否則無法與文獻對照);③C04 Bartram-Grinblatt、C05 錯價三分解、C27 Stambaugh-Yuan 綜合分、D22 QMJ、A10 剩餘收益。

**預期量級**:公開數字要連打三重折扣(現代複製、市值加權、公布後衰減),加上標普 500 沒有微型股這一重。合理預期單條因子月度多空毛回報 **0.15%–0.40%**、月度資訊系數 **0.02–0.04**,13 條合成後年化資訊比率 **0.3–0.6**(未計成本)。**任何接近論文原文那種年化 20% 的回測結果,應當作程式有錯來查。**

**三個要拍板或另開票的發現**(本票不自行推翻裁決、不動其他票):
1. **D-026 的基本面分工要重議**:實測 defeatbeta 年度報表由 2019 年起、典型只有 7 期、抽驗 44 個已除牌成分股無一有歷史;yfinance 硬上限 4 期年度、已除牌代號連價格都取不到。兩者都不足以支撐回測。**SEC EDGAR XBRL 才是唯一可行主線**(2009 財年起、按申報日期可還原真正知情時點、保留 2009 年後除牌公司)。誠實範圍是 **2009–2026**,不是 1996–2026。
2. **A-011(代號回收)已由 unverified 改 overturned**,實例:`BBBY` 在 SEC 現行代號表解析到 NEIGHBORHOOD INTELLIGENCE(CIK 1130713)而非 Bed Bath & Beyond(CIK 886158),而 BBBY 是範圍內的歷史成分股。補救來源 `cik-lookup-data.txt`,**修補要另開票**。
3. **A-012 新增(狀態 overturned)**:「DefeatBeta 與 yfinance 的免費財報足以支撐標普 500 歷史成分回測」不成立,附實測數字。

**詞彙表**已加四個詞(絕對估值 / 相對估值 / 學術錯價訊號 / 財務質素評分)。**24 項未核實事項**在文件第九節逐項列明,其中兩個實作陷阱要特別留意:Dechow 錯報 F 分與 Piotroski F 分同名但方向相反;前者有兩套係數在流通,照免費 SSRN 稿實作會靜靜砌錯模型。

## 留言
