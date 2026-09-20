# Karst 專案守則(2026-09-10 建;每個 session 自動載入,不靠記性)

> 起因:用戶原話「how Claude is managing memory, as i am afraid the project will get lost again like the failure in all the previous Karst project」。本檔用 `@` 匯入把進度正本直接塞進每個 session 的開場 context,主 agent 不用「記得要讀」。

## 開場必讀(自動匯入,勿刪)

@strategy/四類注地圖.md

@strategy/資料來源.md

@strategy/投資委託.md

@strategy/投資決策模型.md

> **現行產品入口(D-181)**:策略正本為 `strategy/投資決策模型.md`(v1.1),委託 v1.4、六層 v1.4,設計與工作包見 `strategy/specs/獨立投研工作台設計與交付計劃-v1.md`。先交通用獨立股票頁;基本面推導當日內在價值,期限目標另有橋接。研究不讀私人或模型帳本,相位服務條件判斷,四類注不強制。原84宗按凍結協議保存。
>
> **開發／生產上下文分開**:本檔的自動匯入只用於開發 session。正式研究 worker 必須由允許清單重新組裝輸入,不繼承本檔、地圖、HANDOFF、.kira、全倉或舊對話,也不開放私人帳戶／交易工具。單靠提示「忽略持倉」不算隔離。

## 派工分層(D-175,用戶 2026-09-12 明令;原研究工作的派工例外保留;現行產品目標依 D-179 為投資工作台,對全域「一律 DeepSeek」與「Fable 不落場」立例外)

| 工作性質 | 誰做 |
|---|---|
| 需判斷:能力卡、模組規格、對外報告、卡片判詞覆核、事件與籃子界定、要下結論的分析 | **Anthropic Opus,effort high 起**(Agent 工具 `model: opus`) |
| 策略思考與探索:四類注定位、主流程結構、模組要多問的問題、與用戶討論後的立場 | **Fable 主腦親自執行,不派工** |
| 回測、大批量填卡、取數、對照表、腳本重跑、格式整理 | DeepSeek Flash(`kira-worker run`,預設 high;純機械 low) |
| 一張票同時含判斷與量產 | 拆票;DeepSeek 產出的判詞交貨後由 Opus 或 Fable 抽查並記票 |

## 硬規則(本專案)

1. **地圖是唯一進度正本。** 任何「這件事做到哪」的答案以 `strategy/四類注地圖.md` 為準;每輪與用戶討論收線前必須更新對應格,否則不算收線。
2. **向用戶提「新想法 / 新形態 / 要你點頭」之前**,先查現行 `strategy/投資決策模型.md` 與委託,再搜三份歷史正本:`strategy/framework.md`、`strategy/principles.md`、`strategy/candidates.md`,再搜 `.kira/decisions.md` 與各對帳單的對齊紀錄。文件已有的不准當新提案。
3. **開票**必掛 Epic `根基重整`(D-177)之下四件交付品之一(D09 資料 / D10 策略正本 / D11 ②收尾與回歸集 / D12 獨立投研工作台);Kira 把關會擋掛錯的。舊 Epic `方法論期(D-166)` 不再開票。
4. **每類收官報四數**(複合年化、最大跌幅、命中率、優勢來源;`principles.md` §三)。
5. 上文被壓縮(compaction)後,第一件事重讀地圖與 HANDOFF §零,不憑摘要行事。
6. **講「某資料拿不到」之前先查 `strategy/資料來源.md`**(已自動匯入);查過才講。倉內已接 DefeatBeta、富途 MCP、Longbridge 三個接口與 EDGAR 本地快取。
7. **②第一次考試目錄是回歸測試集**(D-178):只准追加不准改寫;改資料管線或抽取程式後須對這 84 包重跑越界、錯位、引用三項檢查。
8. **生產與考試取證分開。** 日常使用最新適用公開資料,強模型可補查;凍結②提示詞的「共識一律查不到／禁止補查／首報值」只服務原考試。用戶已表明一月至一年偏好,不重問;1% 只示例,資金停手線未定,不自行補成正式參數。
9. **主 agent 是顧問不是工頭**(用戶 2026-09-13):策略與形態親自思考並帶立場,回覆先講立場與對盤數的意義,不報機械過程。
10. **程式必須通用,倉內不准一次性腳本**(用戶 2026-09-14 明令,D-180):程式只住 `karst/` 套件,代號與日期由參數傳入,生產檔名與碼內不寫死股票身份;參數化測試 fixture 可含代號及可信預期值,不逐股複製腳本;探索與除錯碼放倉外 scratchpad,不 commit;派工指令必須帶這條原文,工人交回的股票專屬檔不收貨。細則 `karst/README.md`。
11. **用戶問問題不等於叫開工**(用戶 2026-09-14:「I am asking you on the phases and stage but not asking you to start」):要用戶講明「開始」才派工或開實作票;討論與清單只答問題。本輪用戶已明確要求「can update into the Repo? And start doing the planning or design?」,依此完成規劃與設計提交;不要再等待同一句授權,也不把設計提交寫成 runtime 已完成。

其餘規矩:`HANDOFF.md`(現況與規矩)、`CONTEXT.md`(詞彙表)、`.kira/decisions.md`(已裁決的事)。

2026-09-14 GPT 審查同步:本次為 D-181 已授權的策略、規劃與設計修訂,不代表股票頁、取證器或 WeKnora 已部署;進度以地圖 D12 與下一步隊列為準。
