---
id: KARST-246
title: 取數與 TA 圖像流程:統一來源接口(小 port)、共用任務目錄建立、CLI 依賴整理、模型可讀的標準圖與條件式計劃
type: task
createdAt: 2026-09-18
risk: medium
model: opus
fits: 一程做得完:fetch / agents / pipeline / page 四處小改加一個繪圖模組;不擴成框架
dependsOn: [KARST-245]
claimedBy: null
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

承 2026-09-18 架構評審與 GPT 覆核(交付二)。(1) 來源接口保持小:每個 adapter(edgar / defeatbeta / longbridge / prices / 手動落地)回明報的落地記錄——來源類別 kind、檔案、公開與取得時間、涵蓋範圍、ok / empty / error 及原因;供應商代號轉換留在 adapter;registry 只登記不反推 kind;service 不再逐來源 if/elif;不建通用插件框架。TradingView 不預設為新來源——只在確定需要其特有資料時才加。(2) 共用 stage_task:六角色、主研究、覆核三處任務目錄落地抽成一份(隔離規則、原子落地、失敗清理)。(3) pipeline 只留 CLI 殼:sections_from_markdown / questions_from_model 搬入 agents/protocol、pair_staging 搬入 fetch/registry;依賴單向 adapter → service → 領域。(4) 由 Longbridge 行情產生模型可讀的標準圖(日 / 週 / 月,含 200 日線與關鍵位)作計算／繪圖能力的衍生輸出,供主研究者讀圖並產出條件式投資計劃;圖不保存陣列,只保存衍生數字與圖檔。順手:ok/empty/error 判定只在 adapter 落地時判一次、schema 內嵌工具一份、repo_root 一份、mcp_server 的 one()/many() 搬回 service。程式只住 karst/,代號由參數傳入(D-180)。

## 驗收條件

- [ ] 換股票不改程式:同一命令換 security 參數即完成取數、登記、建包
- [ ] 來源失敗能說明原因:任一 adapter 失敗或空回傳,search_evidence / get_research_context 回具體 status_reason,且 registry 不再反推 kind
- [ ] 三處任務目錄落地只剩一份實作,三個角色經同一介面測試通過;pipeline 不再被 agents 或 service import
- [ ] 主研究者收到程式生成的日 / 週 / 月圖並在研究中引用其衍生數字,產出含入場 / 失效 / 目標與 R&R 的條件式計劃;圖檔不含價格陣列保存
- [ ] 全套測試通過;生產碼零代號

## 結果

## 留言
