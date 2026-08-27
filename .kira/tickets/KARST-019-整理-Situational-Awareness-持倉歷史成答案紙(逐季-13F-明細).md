---
id: KARST-019
title: 整理 Situational Awareness 持倉歷史成答案紙(逐季 13F 明細)
type: task
createdAt: 2026-08-27
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: null
epic: V1 藍圖
deliverable: KARST-D01
closed: 2026-08-27
---

## 工作內容

人物判官(D-022)要有答案紙才能評分。把 Situational Awareness LP 自首次申報起至最新一期的每份 13F 明細整理成一張表:申報期、申報日(知情時間)、持倉名稱、代號、股數、市值、佔比、對上一期的增減;來源用 SEC EDGAR 原始申報,每期附連結。同時列出已知的非 13F 披露(13D/13G、期權倉位)如有。只整理事實,不做推論。

## 驗收條件

- [x] research/ 下有逐季持倉表(CSV + 說明 md),每期附 EDGAR 出處與申報日
- [x] 增減欄可對出每期進出的股票
- [x] 查不到的期或欄位明講缺口

## 結果

· 2026-08-27 03:00 直接向 SEC EDGAR submissions API 核對 CIK 2045724 全部申報紀錄,
查得 **7 期 13F-HR**(2024Q4 至 2026Q2),比原先背景檔已知的三期多出四期更早的申報——
基金首次 13F 其實是 2024Q4(2025-02-12 公開),不是原先認為的 2025Q4。全部 7 期皆抓到
information table 原始 XML,無缺漏期別。產物:
- `research/sa-13f/holdings.csv`——165 列持倉/變動明細,含 period、filed_date、issuer、
  ticker(部分留空,詳 README)、cusip、shares、value_usd、weight_pct、change_vs_prev
- `research/sa-13f/README.md`——逐季彙總表(前五大持倉、EDGAR 原始連結)、value 單位
  換算依據、CUSIP 前後不一致的三筆人工修正說明、非 13F 揭露清單(查到 8 筆 13D/13G/
  Form3/4,比原先已知的一筆多 7 筆)、逐項列明的疑點與缺口
- `research/sa-13f/fetch_13f.py`——可重跑抓取腳本
- 關鍵疑點(README 第四、五節已詳列):value 欄位實際是美元金額本身,未依 SEC 表格
  說明書規定換算成千美元(已用外部已知數字核對確認);三筆持倉(Bloom Energy、
  Lumentum、Cipher Mining)在 2025Q3→2025Q4 之間 CUSIP 填法不一致,已人工判斷為同一
  持倉並修正 change_vs_prev;VanEck ETF Trust 底下至少兩檔不同 ETF 共用發行人名稱,
  未強行合併

## 留言

### human:Kaho · 2026-08-27 23:09
交付品「Karst v1 規格」（KARST-D01）已簽收。

**簽收人留言**：用戶 2026-08-27 於原生多選介面勾選簽收
