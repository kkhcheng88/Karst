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
closed: 2026-09-18
---

## 工作內容

依 strategy/specs/估值與視覺TA升級-ClaudeCode執行指令-v1.md §4.3–4.4:用 BE(run 2026-09-16 packet,前版 rv-f9347224…／pub-8fc7e6c5…)與 AXTI(run 2026-09-16 packet,前版 rv-0fc78d55…／pub-7b6f9f0…)的原凍結 packet 與證據,以 update 模式各出一個新研究版本。不取新證據(價格只為畫圖重登記並裁至 9/16 截止);估值必用契約 0.4 的方法判別(按生意選主模型與替代,敏感度／反推經 calculate 帶 receipt);研究者必實際讀月／週／日／近期四張圖並在 technical.reading 記圖識別;change_attribution 明分「算術／時點修正」「經營／風險假設改變」「方法改變」;BE 核比較優勢延續與供給正常化,AXTI 核 stub 與子公司權益(執行指令 §4.4)。舊發布不改;新版指回前版。程式只住 karst/;運行紀錄與發布落 cards/。

## 驗收條件

- [x] BE 與 AXTI 各一個 update 版本收件成功,expected_previous_version_id 對上前版,發布目錄指回前版發布;原兩份發布未改
- [x] 兩版 valuation.status=calculated 且 scenarios 的 calculation 帶 method(至少一個非年度期末 fcff_dcf 的主模型或替代視角);sensitivities／implied 附 receipt,計算器重算同值
- [x] technical.reading.text 記實讀的四張圖(識別、週期、範圍、截止);plan 形成 setup→觸發→失效→目標／不做;不預設 1H／TP1／固定 R／風險預算
- [x] valuation.change_attribution 分開算術／時點修正、經營／風險假設、方法改變三類,並在 headline.change_since_last 交代;紀錄寫明各類對每股價值的影響
- [x] cards/runs/<run>/紀錄.md 記流程、結論、成本(token)、未做;地圖 D12 格更新;若改動 karst/ 程式則全套測試通過

## 結果

AXTI 新版 `pub-d714886c…`(13.48 / 24.96 / 41.38 對 57.70)、BE 新版 `pub-0a5cd242…`(12.24 / 44.32 / 93.04 對 265.29);兩者評級負面／避開不變,主模型皆日期化 FCFF,替代與敏感度／反推帶回執;紀錄在 `cards/runs/research-{AXTI,BE}-2026-09-18-rev04/`。收件三次被拒的 runner 教訓見留言。

## 留言

### agent:Fable主腦 · 2026-09-18 04:15
2026-09-18 完成:兩隻股各一個 update 版本,固定 9/16 取證包(證據、來源版本、截止不變;契約由 0.3 重述為 0.4,登記器本身支援、證據身份不變),一位 Opus 主研究者,無覆核回合。**AXTI**:rv-583a6bc3… / 發布 `cards/releases/pub-d714886c…`(指回 pub-7b6f9f0…);負面／避開不變;內在價值 13.48 / 24.96 / 41.38(前 13.88 / 28.03 / 53.45)對 57.70;主模型 fcff_dcf_dated(106 天 stub、期中折現、終值再投資率推導),替代 forward_pe 27.92;三項敏感度與反推(現價要求終值正常化 FCFF 4.77 億,基準的 3.7 倍)全部帶回執;更正上一版「9% 折現率 → 55–60」的講法(實為 34.43);新見通美科創板撤回觸發贖回權、AXT 自購通美 0.58% 隱含 10.3 億對現價隱含 31.7 億;setup 不做;約 36 萬 token。**BE**:rv-fbd89374… / 發布 `cards/releases/pub-0a5cd242…`(指回 pub-8fc7e6c5…);負面／避開不變;內在價值 12.24 / 44.32 / 93.04(前 15.65 / 50.37 / 98.64)對 265.29;主模型 fcff_dcf_dated,替代 ev_multiple 48.73(15 倍為自設假設,包內無同業倍數);反推兩次(隱含年回報 4.5%,或終值 FCFF 要 115.9 億=基準 8 倍);更正上一版 Oracle 認股權證由「4 億現金流入」變「3.065 億客戶代價資產攤銷為收入減項」;setup 不做;約 44 萬 token。三類歸因兩版都寫清(算術／時點:BE 期中對期末只值 +0.66;經營假設:AXTI 樂觀由 53 → 41 主因統一 12% 折現率,BE 收入上調但首次逐年列 capex／營運資金／現金稅;方法:年度 → 日期化)。runner 三次收件被拒的教訓:L3 讀取紀錄在 update 模式仍須含全部逐字稿(無沿用機制)、圖表截止必須等於取證包截止、未復權 K 線的報價係數必為 1。程式改動:Longbridge 時區修正(656efb3)與圖標題(05e9800),316 測試通過。紀錄:`cards/runs/research-AXTI-2026-09-18-rev04/紀錄.md`、`cards/runs/research-BE-2026-09-18-rev04/紀錄.md`。未做:ChatGPT 端讀圖驗收;覆核回合;補查 21 條全部 pending。
