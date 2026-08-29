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
claimedBy: agent:KARST-076-research
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

用戶 2026-08-29 指示(原話「估值模型 especially I want to have a research on market standard and academic based 估值模型. I think this is very valuable for us to have all the 10+ or 100+ 估值模型 in most situation as the quant factor for us. as I think we are doing stock selection. It is either for Swing Trading that based on 1-5, or it is based on fundamentals that is 6-8. … 6-8 is not something I know very well. I just know DCF」)。本票出一份估值模型總目錄,每個模型一行:名稱、一句白話、公式或做法、屬絕對估值 / 相對估值 / 學術錯價訊號 / 財務質素評分哪類、所需輸入(損益表 / 資產負債表 / 現金流量表 / 分析員預測 / 折現率 / 市價)、可否用免費數據算(SEC EDGAR XBRL companyfacts API、yfinance 財務、FRED 利率)、學術或業界預測力證據(出處、樣本期、多空回報或 t 值,OSAP 有對應訊號的註明訊號名)、對 Karst 的適用度(月度橫斷面因子可否直接化)。範圍至少涵蓋:DCF 一族(FCFF、FCFE、DDM 單段 / 多段、APV、剩餘收益 / EVA、實質選擇權)、相對估值一族(P/E、前瞻 P/E、PEG、EV/EBITDA、EV/Sales、P/B、P/S、P/CF、FCF 孳息、股息率、行業特定倍數)、學術錯價與內在價值(Ohlson 1995、Feltham-Ohlson、Frankel-Lee 1998 V/P、Lee-Myers-Swaminathan 1999、Bartram-Grinblatt 2018 agnostic fundamental analysis、Rhodes-Kropf 等 2005 錯價分解、Penman 的會計估值)、財務質素與風險評分(Piotroski F、Mohanram G、Altman Z、Beneish M、Sloan 應計項目、Novy-Marx 毛利率、Fama-French 盈利與投資因子、Greenblatt 魔法公式、Asness QMJ 質素)。另答:(a) 免費財務報表數據源的可行性(EDGAR XBRL companyfacts 覆蓋年份、欄位一致性問題、標普 500 歷史成分含退市公司的覆蓋;Karst 已有 karst/data/cik.py);(b) 分析員預測與折現率輸入的免費替代;(c) 結語:建議首批 10–15 個可用免費數據算的模型、分三期的建置路徑、實測前預期量級。輸出 research/2026-08-29-valuation-models-catalogue.md,總目錄另出 CSV research/2026-08-29-valuation-models-catalogue.csv。不動程式、不動庫。

## 驗收條件

- [ ] 總目錄落檔(md + csv),每個模型一行齊八欄,至少 40 個模型,每行有出處
- [ ] 免費數據源可行性與首批 10–15 個模型建議,分期建置路徑,預期量級
- [ ] 不動程式、不動庫

## 結果

## 留言
