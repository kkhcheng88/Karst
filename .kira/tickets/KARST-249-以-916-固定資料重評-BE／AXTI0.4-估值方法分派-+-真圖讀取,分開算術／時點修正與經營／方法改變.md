---
id: KARST-249
title: 以 9/16 固定資料重評 BE／AXTI:0.4 估值方法分派 + 真圖讀取,分開算術／時點修正與經營／方法改變
type: task
createdAt: 2026-09-18
risk: medium
model: opus
fits: 一程做得完:兩隻股各一次 Opus 單主研究者 update 派工(固定 packet、不取新證據),收件、發布、寫紀錄
dependsOn: []
claimedBy: Fable主腦
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依 strategy/specs/估值與視覺TA升級-ClaudeCode執行指令-v1.md §4.3–4.4:用 BE(run 2026-09-16 packet,前版 rv-f9347224…／pub-8fc7e6c5…)與 AXTI(run 2026-09-16 packet,前版 rv-0fc78d55…／pub-7b6f9f0…)的原凍結 packet 與證據,以 update 模式各出一個新研究版本。不取新證據(價格只為畫圖重登記並裁至 9/16 截止);估值必用契約 0.4 的方法判別(按生意選主模型與替代,敏感度／反推經 calculate 帶 receipt);研究者必實際讀月／週／日／近期四張圖並在 technical.reading 記圖識別;change_attribution 明分「算術／時點修正」「經營／風險假設改變」「方法改變」;BE 核比較優勢延續與供給正常化,AXTI 核 stub 與子公司權益(執行指令 §4.4)。舊發布不改;新版指回前版。程式只住 karst/;運行紀錄與發布落 cards/。

## 驗收條件

- [ ] BE 與 AXTI 各一個 update 版本收件成功,expected_previous_version_id 對上前版,發布目錄指回前版發布;原兩份發布未改
- [ ] 兩版 valuation.status=calculated 且 scenarios 的 calculation 帶 method(至少一個非年度期末 fcff_dcf 的主模型或替代視角);sensitivities／implied 附 receipt,計算器重算同值
- [ ] technical.reading.text 記實讀的四張圖(識別、週期、範圍、截止);plan 形成 setup→觸發→失效→目標／不做;不預設 1H／TP1／固定 R／風險預算
- [ ] valuation.change_attribution 分開算術／時點修正、經營／風險假設、方法改變三類,並在 headline.change_since_last 交代;紀錄寫明各類對每股價值的影響
- [ ] cards/runs/<run>/紀錄.md 記流程、結論、成本(token)、未做;地圖 D12 格更新;若改動 karst/ 程式則全套測試通過

## 結果

## 留言
