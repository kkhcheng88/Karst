---
id: KARST-240
title: 通用獨立股票頁——來源版本、隔離研究、內在價值與期限目標、TA及條件計劃
type: task
createdAt: 2026-09-14
risk: medium
model: opus
fits: D-181 設計工作包P1;單股與批次共用核心,第二股只換參數跑完整流程;不逐股開取證腳本票
dependsOn: [KARST-241]
claimedBy: main-agent
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

實作 strategy/specs/獨立投研工作台設計與交付計劃-v1.md 的 P1。輸入任意適用股票代號與截止時間,由通用來源 adapter、固定來源版本、清理後研究委託及六層 v1.2 產生獨立股票頁。首屏可直接讀評級、理由、假設、反證、行動條件和變化,展開見原文、公允價值、目標價、日週月結構與前瞻 R&R。

P1 同時落實最小來源 manifest、研究輸入允許清單、必要索引與不可改寫發布包,不等完整事件引擎或新能力考試。現行判斷模型按配置記實際版本,強模型直讀原文;程式算數列、估值、TA 和 R&R。後續 P2 增量、P3 模型組合、P4 掃描分階段接上,本票留下穩定契約。

首批 AXTI、TTD、BE、INTU、ORCL 只作跨公司驗收配置,不是研究取得用戶持倉的依據。沿用本票 id／路徑維持登記引用;題目已由單一公司改為通用能力。本輪用戶授權開始規劃設計,本次只完成規格和票內容對齊,尚未達成下列功能驗收。

## 驗收條件

- [ ] 任一適用首批股票輸出 HTML 及完整發布包:研究評級、期限、條件狀態、六行、六層、反方與綜合回應、原文定位及來源日期;具體資料不足不以「未量度」或空白代替。
- [ ] 研究執行為新上下文及公開資料工具允許清單;不讀私人／模型帳本、成本、盈虧或交易方法。用合成秘密 fixture 驗證禁止來源不進 prompt／工具結果。
- [ ] 按申報形式取得最新年報、最近適用季報、業績稿及完整逐字稿含 Q&A;共識、公開機構持股／內部人、淡倉與行情按覆蓋取得。每份有不可變版本、完整 hash、公開／取得時間、期間及定位;先查本地快取,缺逐字稿查備援並說明影響,不偽造齊料。
- [ ] 基本面推導今天的基準公允價值與悲觀／樂觀範圍,算式、股數／稀釋、折現率及敏感度可核;另有指定日期目標情境與實現橋接。基準不取兩端平均,內在價值不直接等同六個月價格。資料不足有明確的條件估值或缺口。
- [ ] TA 保留核心 pivot／支撐阻力／200 日 SMA、日週月與通道／突破回踩;所有確認時間可重播。計劃報每股／百分比 R&R、退出、跳空壓力及驗證事件,不以未確認1%輸出正式用戶股數。
- [ ] run 與發布保存研究委託／策略／提示詞／實際模型／計算版本、輸入版本集合、各層必讀與時間、成本耗時。發布中斷無半張卡;相關來源變更不能冒充完整最新;原發布及期限不覆寫。
- [ ] 同一入口第二股只換參數跑至完整頁面,再以同一批次機制驗首批;代號／日期／路徑／公司映射不寫死生產程式,不增加股票專用腳本。固定估值輸入只變現價時,公允價值不被無故改寫,折讓／反推要求／R&R 正確重算。
- [ ] 改取證／抽取路徑按 D-178 跑84包相关越界、錯位、引用檢查並記適用範圍,原包、提示詞與成績不修改;本票不能把未執行驗收標成已通過。

## 結果

## 留言

2026-09-14 GPT 按用戶明確要求更新 repo 並開始規劃設計:對齊 D-181／P1,保留開票狀態,未宣稱已完成股票頁。

### agent:main-agent · 2026-09-15 02:40
依 D-183 三步分工,本票定為**步二**:接真實來源與模型,首批第一隻完整分析,第二隻只換參數驗通用性;依賴步一 KARST-241(樣本包、四份契約、離線核心與可閱讀股票頁);步三為 KARST-242(更新一次)。驗收條件八條不變,第七條「第二股只換參數」與第八條回歸檢查在本票驗。實作等用戶講「開始」。

### agent:main-agent · 2026-09-15 23:37
步二開工(用戶 2026-09-15「yes please do」)。分工照 D-183:

**GPT(分支加合併請求)**:(1) `karst/fetch/registry.py`——把 adapter 產出的 `<raw>` + `.meta.json`(形狀 = `karst/tests/fixtures/README.md` 規矩 4,另加 `status` ok/empty/error 與 `source_url`)映射成 0.2 證據記錄、寫入 `evidence/manifest.jsonl` 與內容定址物件;映射規則照 PR #1 第三輪評語(時間精度、期間只收 ISO、coverage 原樣、8-K 主文與附件各一條、錯誤信封入 diagnostic),對 fixtures 全部 48 份可測。(2) `karst/packet.py` 加 `build_packet(evidence_records, as_of, security)`:requirements(逐字稿 available/partial/missing 按 truncated)、diagnostic_ids、dependencies。(3) `karst/agents/`:六角色提示詞檔(產業與宏觀 L1+L2、公司與財務 L3、估值 L4、技術 L5、反方、綜合 L6)——每份含輸入(bundle 路徑、可讀證據清單、投資委託、六層紀律該層一節、情境模組問題)、輸出格式(research.schema 的 layer 片段 JSON,引用必帶 evidence_id 加 locator)、補查請求格式(packet supplement_requests);加 `assemble.py` 把六個片段合成 research.json 並驗證。反方只讀證據與各層片段,不讀綜合。

**本地**:(1) `karst/fetch/` 四個 adapter(edgar、defeatbeta、prices、broker 落地),輸出 staging 目錄形狀 = fixtures;由 Opus 子代理以倉外 scratch-241 三支草稿為種子重寫成通用模組。(2) 首批第一隻:重抓完整逐字稿與申報四節 → registry → packet → 六角色以 Opus 直讀原文(Agent 工具,角色定義檔限工具,不給券商 MCP)→ assemble → publish;記 run(模型、提示詞版本、費用、耗時)。(3) 第二隻只換參數。(4) 券商 MCP 由取證角色呼叫,`broker.land()` 落地。

接口:兩邊只靠 fixtures 的 raw+meta 形狀與 0.2 契約對接;不改契約版本。

### agent:Fable主腦 · 2026-09-16 03:51
步二本地進度(2026-09-15):取證器四個 + GPT PR #2 + karst/pipeline 管線 CLI 合併,107 測試通過。首隻 AXTI 真實全流程已跑通並發布:cards/releases/pub-18bff4219f2f0109d2d20ee3d5219c607531701c851f26e8b0d7a3593d976f1b(中性/等資料/部分覆蓋;FCFF 基準約 21 對現價 57.5;最強反證為管理層「每季 1.3 億」口徑未定;20 條補查待補)。六角色全部 Opus,harness 計約 1.94M token、約 1 小時 20 分;契約在組裝前擋下五處缺陷(詳 cards/runs/research-AXTI-2026-09-15/紀錄.md §三)。未完:pipeline 補 land 與補查登記子命令、提示詞三句、角色 agent 定義重載、本地日線續抓(止於 09-01)、第二隻參數化重跑、84 包回歸檢查。

### agent:Fable主腦 · 2026-09-16 21:28
2026-09-16 修訂版已發布:cards/releases/pub-57d0ea9befab4a9551993d4d41c8d949080ce9363d995c8e0876eb31d247eb32(指回 pub-18bff42…)。負面/避開/部分覆蓋;內在價值 10/23/37 對 09-15 收市 57.70;目標價全部清空;GPT 四點覆核(目標價未撤、乘四期間錯、RPO 口徑、悲觀溢價)全部處置;取證包 54→90 份(四月增發 424B5/8-K、三份協議 8-K、9 月日線、收市報價)。計算器首次擋住模型算術錯(反方重複扣少數股東,估值層 36.9 正確)。約 1.76M token、關鍵路徑約 95 分鐘。紀錄 cards/runs/research-AXTI-2026-09-16-rev1/紀錄.md。新提案 strategy/specs/資料服務層與研究形態提案-v1(供GPT評論).md 待 GPT 評論後開步二收尾與第二股票。未完:pipeline land/補查登記子命令、EX-10 附件取數、模型呼叫改 API、第二股。

### agent:Fable主腦 · 2026-09-16 22:54
2026-09-16 票務映射(依《主研究Agent與資料服務-執行計劃-v1》角色可互換修訂,PR #4/#5 已合併):本票承接 W1 本地機械核心與單一主研究入口(store/service/mcp_server/fetch/longbridge;protocol/research intake/review 格式/契約 0.3/發布 0.3 路徑),取代原六角色步二收尾中的 land/補查登記子命令——六角色 assemble 路徑保留供舊包讀取,不再新增功能。W2 → 新票(兩客戶端共用 MCP、雙向覆核交接、Zeabur);W3 → 新票(第二股 INTU 頁);W4 → KARST-242。W1 已派兩位 Opus 工人並行實作,不 commit,交回後本地驗收合併。已知缺項:Longbridge OpenAPI 憑證(LONGPORT_APP_KEY/SECRET/ACCESS_TOKEN)本機未設——現有 ~/.longbridge 只是 MCP 的 CLI 授權,SDK 用不到;需用戶到 open.longbridge.com 建應用取得,並核 scope 只有行情。

### agent:Fable主腦 · 2026-09-17 01:10
2026-09-17 W1 本地核心交付並端到端驗收:store/service/mcp_server/fetch/longbridge + protocol/research intake/review 格式/契約 0.3.0/發布 0.3 路徑,160 測試;Longbridge 真憑證(.env)實測四工具 ok(修 pyo3 列舉序列化)。驗收運行:AXTI 單一主研究者(形態 B)以 90 份真實證據建 0.3 packet → 模型交分析 payload → service.save_research(程式補工程欄位、契約驗、計算器重算 28.03/13.88/53.45、SMA200 56.25 同值)→ publish_research → verify_release 通過 → 重開 SQLite 讀回同版。發布 cards/releases/pub-7b6f9f0…;紀錄 cards/runs/research-AXTI-2026-09-17-single/紀錄.md。合流修兩處接縫(role_meta 形狀、subject 型別)。留下:publish_research 未傳臨時日線畫圖;補查登記應入 save_research;registry 加 contract_version 參數;隔離仍靠指令。步二本票餘下:上述三項小修 + 84 包回歸檢查;之後 W2=KARST-243。
