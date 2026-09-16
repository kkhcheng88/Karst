---
id: KARST-243
title: W2 兩個客戶端共用連接及雙向覆核交接:Karst 資料服務部署 Zeabur、ChatGPT 與 Claude Code 同一 MCP endpoint、reviewer 任務互評
type: task
createdAt: 2026-09-16
risk: high
model: opus
fits: 一程做得完:部署配置、MCP HTTP 包裝、reviewer 任務互評三件,前提 W1 已合併
dependsOn: [KARST-240]
claimedBy: null
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依《主研究Agent與資料服務-執行計劃-v1》(角色可互換修訂)W2:把 W1 的資料／計算／研究讀寫服務以官方 MCP Python SDK Streamable HTTP 部署到 Zeabur 單一實例加持久目錄;部署目錄、啟動命令、環境變數名稱與兩端連接／驗證步驟寫入 README,不提交憑證;遠端入口用兩個客戶端支援的驗證方式,研究寫入與付費覆核 API 不裸露公網。先接通共用 reviewer 任務與互動提交(A 寫研究、B 寫覆核、A 讀回,再交換角色);自動覆核用可配置 provider adapter,先接有現成憑證的一家,啟用的 adapter 必須實測;API job 記模型、起訖、用量與費用上限,同一 job 去重。券商 token scope 與服務工具清單分開核實(只行情、無交易)。程式只住 karst/,代號由參數傳入,不建股票專屬腳本(D-180)。

## 驗收條件

- [ ] ChatGPT 與 Claude Code 均能從同一 endpoint 取得同版研究指引(get_research_protocol)、讀研究、取數及計算
- [ ] 用一份小型公開樣本完成 A 寫研究、B 寫覆核、A 讀回,再交換角色;只完成一端時如實列另一端未驗
- [ ] 遠端服務重啟後仍可讀原研究與任務狀態
- [ ] 服務工具清單只含公開市場資料與研究讀寫;帳戶／持倉／下單類工具在程式中不存在;Longbridge token 已核為只有行情權限;README 含部署與驗證步驟,倉內無憑證

## 結果

## 留言
