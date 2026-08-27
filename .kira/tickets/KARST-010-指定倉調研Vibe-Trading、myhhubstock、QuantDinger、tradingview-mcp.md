---
id: KARST-010
title: 指定倉調研:Vibe-Trading、myhhub/stock、QuantDinger、tradingview-mcp
type: research
createdAt: 2026-08-25
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: KARST-010-researcher
epic: V1 藍圖
deliverable: KARST-D01
closed: 2026-08-25
---

## 工作內容

要答的事實問題:用戶點名四個 GitHub 倉——HKUDS/Vibe-Trading、myhhub/stock、OpenByteInc/QuantDinger、atilaahmettaner/tradingview-mcp——各自是什麼、做到什麼程度、對 Karst 有什麼可借(整件借用、抽零件、還是只借思路),以及有沒有任何發現需要修訂 KARST-001 的「混合路線」建議。逐倉按 Karst 準則評:授權(對照 D-007 自用先行)、維護活躍度、與 D-002(應用+蠟燭圖+高性能引擎)/D-003(非結構化轉因子)/D-006(選股不擇時、組合層)的契合度、代碼質素與可信度(KARST-001 曾對 QuantDinger 標記「前端非開源、回測引擎未披露」,要重查證實或推翻)。這條問題現正影響「借用哪些零件」的架構決定。

## 驗收條件

- [x] 四個倉逐個有:定位一句、架構與核心零件、授權、活躍度、可借清單(或明寫無可借連理由)
- [x] 與 KARST-001 建議的關係有明文交代(維持、補充、或需修訂邊一項)
- [x] 每個結論附出處(repo 檔案/文件連結)
- [x] 報告落檔於倉內 research/ 目錄並在票的結果引用路徑

## 結果

四個倉逐個查透,結論:**KARST-001 的混合路線核心建議維持,補充三項,修訂一項。**四個倉沒有一個提供向量化引擎(Vibe-Trading 與 QuantDinger 都是逐根事件驅動迴圈、tradingview-mcp 是連 numpy 都沒有的純 Python 迴圈、myhhub 根本沒有引擎),所以 D-002「矩陣式、一秒模擬大量交易」那一格,vectorbt 與 PyBroker 仍是唯二答案。**要修訂的是 KARST-001 §六對 QuantDinger 的第 (3) 條指控「回測引擎未披露」——經查不成立,須撤回**:引擎在開源後端內 `backend_api_python/app/services/strategy_v2/runtime.py`(111,314 bytes),含完整逐根模擬迴圈、多標的持倉、權重再平衡、佣金滑點與績效指標;KARST-001 誤判成因已查明(同倉另有一個 1,027 bytes 的 `backtest_execution.py`,只是手續費正規化小工具)。同條的「前端非開源」則證實,前端與流動版皆為禁商用的 source-available 授權,直接踩 D-007 的 SaaS 留門。QuantDinger 的最終判斷不變(仍不建議當地基),但理由換成準確的那幾條。最大的新發現是 **Vibe-Trading(MIT、近一年 1,762 commit)是 KARST-001 漏掉的真候選**,其因子契約 `dict[str, pd.DataFrame] → pd.DataFrame` 連三條註冊表紀律(禁前視、禁 inf、NaN 必須傳遞)建議交 KARST-003 當藍本。myhhub/stock 是綁死 A 股市場結構的工具(數據源、籌碼分佈/龍虎榜/漲跌停概念、OCR 落單三層皆綁),用戶交易美股,只能借思路不能抽零件。最終路線選擇仍由用戶裁決(D-005)。

報告:`research/2026-08-25-named-repos.md`

## 留言

### human:Kaho · 2026-08-27 23:09
交付品「Karst v1 規格」（KARST-D01）已簽收。

**簽收人留言**：用戶 2026-08-27 於原生多選介面勾選簽收
