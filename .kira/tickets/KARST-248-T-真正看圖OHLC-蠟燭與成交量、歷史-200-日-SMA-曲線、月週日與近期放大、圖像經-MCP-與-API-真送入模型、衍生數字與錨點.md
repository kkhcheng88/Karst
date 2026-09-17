---
id: KARST-248
title: T 真正看圖:OHLC 蠟燭與成交量、歷史 200 日 SMA 曲線、月/週/日與近期放大、圖像經 MCP 與 API 真送入模型、衍生數字與錨點
type: task
createdAt: 2026-09-18
risk: medium
model: opus
fits: 一程做得完:charts 重繪 + MCP 圖像工具 + adapter image content;契約新欄位待 V 的 0.4 一併
dependsOn: []
claimedBy: null
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依 strategy/specs/估值與視覺TA升級-ClaudeCode執行指令-v1.md §2(T1/T2)實作。T1:charts._draw 改為 OHLC 蠟燭 + 成交量 + 由完整歷史先計再裁窗的 200 日 SMA 曲線(50MA/20EMA 按需),月/週背景、日線全貌、近期日線放大三種視圖;週/月映射日 MA 時圖例明標 200 日;軸、座標、來源、價格基準、截止、未完整 bar 清晰;支撐阻力為具錨點區域,pivot 形成與確認時點分開;derived 保留精確 MA、MA200 對前 20 交易日方向、重要 pivot、量比、ATR。圖像與衍生物永久保存(來源版本/參數/hash),不建第二個行情庫。T2:render_charts 回 artifact 清單(服務端路徑只作內部定位);MCP 加按 chart/artifact ID 讀圖的工具,回 ImageContent(文字路徑不算);OpenAI/Anthropic adapter 以真正 image input / tool-result content 送同一圖檔;記送入的圖像身份/版本/週期;現行 schema 先在 reading.text 記實讀圖;失敗/無 vision 只限制視覺判斷。程式只住 karst/,代號由參數傳入(D-180)。

## 驗收條件

- [ ] 參數化數列(非水平 SMA、長影線、跳空)生成三張圖,人工/模型檢視與原始數值一致,不只測檔案存在
- [ ] 假突破、週線趨勢中的日線回調、未收週/月棒三種情況,模型能列錨點、觸發與失效,可說無法判斷,不從外觀捏勝率
- [ ] Claude Code 與 GPT 端實際讀到同版本圖片(MCP 工具回 ImageContent);API payload 真含 image content,只有檔名不得通過
- [ ] 研究輸出形成 setup → 觸發 → 取消/失效 → 目標/不做,數字核 R&R,不預設 1H/TP1/固定 R/風險預算
- [ ] 換 security/as_of 不改程式;全套測試通過;生產碼零代號

## 結果

## 留言

### agent:Fable主腦 · 2026-09-18 02:46
2026-09-18 交付並合併:charts 0.2.0——月/週/日/近期四視圖,OHLC 蠟燭+成交量(20 根均量),200/50 日 SMA 與 20 日 EMA 由完整歷史先計再裁窗成曲線(週月映射日線 MA、圖例標 200-day SMA),未收定 K 棒斜紋標示,線性/對數自選,標的/週期/範圍/截止/來源/價格基準齊;支撐阻力為有錨點區域(容差 0.25×ATR14 或 0.4% 取大),形成日與確認日分開;derived 含精確 MA 與距離、MA200 對前 20 交易日方向、ATR(14 Wilder)、量比、區域錨點、參數指紋;圖與 JSON 不含價格陣列、不含本機路徑。T2:render_charts 回 artifact 清單(cha-<sha256>);store 加 chart_artifacts 表;MCP 新工具 read_chart 回真正 ImageContent(hash 先核),只讀已登記 artifact;Anthropic adapter 以 tool_result image block、OpenAI adapter 以 input_image 送同一圖檔,並掛 calculate 工具;送出的圖像身份記入 run 與任務目錄。28 個測試。驗收:(1) 圖上 MA 序列與獨立計算一致,通過;(2) 三組合成數列 derived 標錨點與確認日,**模型列觸發/失效待實跑**;(3) 離線 ImageContent 與 adapter payload 通過,**兩端真讀圖待部署實跑**;(4) setup→觸發→失效→目標待實跑;(5) 換 security/as_of 不改程式、零代號。未做:page/render 技術段未顯示新衍生數字(待 0.4 欄位);區域參數未經真實個案校準;兩條 image 線路未經真 API 驗證(首跑先最小預算試 read_chart)。
