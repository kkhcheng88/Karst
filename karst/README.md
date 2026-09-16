# karst/ —— 通用工作台程式(D-180／D-181)

所有生產程式從第一天可跨公司重用。代號、公司映射、日期、路徑、來源和模型由參數／配置傳入,不建立股票專用抓取或分析腳本。一次性探索與除錯碼放倉外 scratch,不 commit。

本分支落實 D-183／KARST-241 的離線部分：四份契約、檔案式取證包、補查版本、確定性計算與股票頁發布。下表仍是完整計劃，不代表每個模組都已存在。契約與驗收見 [契約說明](contracts/README.md) 及 [設計計劃](../strategy/specs/獨立投研工作台設計與交付計劃-v1.md)。

## 現在可跑

Python 3.11+，在倉根目錄建立虛擬環境後：

```bash
python -m pip install -e .
python -m unittest discover -s karst/tests -v
python -m karst.run --bundle karst/examples/synthetic --output /tmp/karst-releases
```

最後一行輸出 `index.html` 的絕對路徑，瀏覽器直接開啟。頁面不依賴網絡、前端伺服器或外部資源。`--validate-only` 可單獨驗證輸入；`--previous-publication-id <ID>` 可連結上版。換股票只換 bundle，不新增程式。

四個來源適配器（KARST-240 本地部分）把原始回傳落到 `<out>/<source>/…`，每份旁邊一份同名 `.meta.json`（形狀 = `tests/fixtures`，另加 `status` ok/empty/error 與 `source_url`）；代號、CIK、日期一律由參數傳入：

```bash
set KARST_EDGAR_USER_AGENT=<name email>   # EDGAR 要求；先查本地 submissions 與 10-K 快取，其餘線上抓
python -m karst.fetch.edgar --ticker <代號> --out <DIR>            # 或 --cik；10-K/10-Q/8-K(+EX-99.1)，失敗寫 status error 不捏造
python -m karst.fetch.defeatbeta --ticker <代號> --out <DIR>       # 逐字稿清單與最新全文（預設不截短）、三張季表、拆分、股數、拆股、日曆、info
python -m karst.fetch.prices --ticker <代號> --out <DIR>           # 本地 parquet 最近 400 日 + DefeatBeta 續抓，重疊日核收市價；--no-continue 只用本地
python -m karst.fetch.broker --out <DIR> --source futu --tool <工具> --symbol <代號> --params '{}' --response-file <F>  # 只落地代理人已拿到的 MCP 回傳；不呼叫 MCP，帳戶／持倉／下單類鍵一律拒收
```

`examples/synthetic/` **全部是合成資料**，含虛構公司、日期、預測與價格；不屬於真實接口樣本，也不是投資建議。本地已提供的真實回傳在 [tests/fixtures/](tests/fixtures/README.md)，新增測試引用其期間形狀，未把轉錄數值當估值真值。本核心讀取已保存的 `research.json`，不會自行呼叫模型、生成評級或讀券商帳戶。

契約目前為 **0.3.0**（單主研究路徑），保留 0.2.0、0.1.0 讀取，舊 bundle 與舊發布不變。第二輪接線要看 [契約的遷移表](contracts/README.md)：日期精度與時區、原始 coverage、error/empty 取得紀錄，以及手填判斷的 `integration_example` 模式。Windows 缺符號連結權限時只略過該項測試，路徑逃逸檢查照跑。

步二新增 `fetch.registry.EvidenceRegistry`、`packet.build_packet`、六角色提示詞／輸入允許清單與 `agents.assemble`；核心版本 0.2.2。接線、片段欄位、補查與本地驗收見 [agents/README.md](agents/README.md)。**六份片段只是 0.2 那條路徑的做法，不是發布的前提**——現行單主研究路徑（0.3）一份 payload 就可以出頁，見下節；舊 bundle 仍由 `agents.assemble` 讀。

發布目錄包括 `publication.json`、`index.html`、`calculations.json` 及 `inputs/`。後者保留該版 packet、research、evidence 登記與原始 bytes，可以再次交給同一入口重播。不要把產生的發布包或大批原始來源 commit。

## 單主研究路徑（0.3）

一名主研究者持有完整論點，六層全部由他作答；**沒有六份片段，也沒有反方初判**，針對性覆核另開任務。方法只有一份版本化正本：`agents.protocol.get_research_protocol(mode)`（mode 為 research／update／review）把研究委託全文、六層紀律各節、策略正本的情境問題與該模式的模板組成一份內容，回 `{version, mode, text, output_schema, steps}`；`version` 同時帶宣告字串與內容 digest，重試或接手時可以固定同一版。角色與輸出不含固定供應商，GPT、Claude 或其他已接模型都可以做主研究或覆核。

```python
from karst.agents.protocol import get_research_protocol
from karst.agents.research import export_task, intake

protocol = get_research_protocol('research')          # 或 'update'
export_task(bundle, subject, task_dir, protocol)      # input.json / prompt.md / output.schema.json ＋ 允許讀的原始檔
research = intake(payload, bundle=bundle, clock=now,  # 模型只交分析 payload
                  role_meta=[{'role': 'researcher', 'execution': 'interactive',
                              'provider': ..., 'model_id': ..., 'prompt_version': ...}])
```

模型交回的 payload **只有分析**：六層的 conclusion／assumptions／strongest_counter／gaps／實讀來源、估值、技術衍生數字（不交 K 線陣列）、計劃、首屏六句、相位、模組、覆蓋、評級、執行狀態、待答問題、補查請求。`research_id`、`packet_id`、`created_at`、各層 `assessed_at`、mode、策略／委託／方法版本、models 與上版關係一律由程式補；payload 內出現這些欄位會被拒收。收件時照樣跑 packet 版本、引用、實讀紀錄與行號檢查，不通過就拋 `ContractError`，不寫任何檔。

覆核由 `agents.review` 處理：`build_review_task` 匯出針對指定 `research_id` 與指定爭議的任務，`REVIEW_RESULT_SCHEMA` 與 `validate_review` 收挑戰（針對層、主張、引用、嚴重程度）、對爭議的裁決與新補查請求；覆核者不給第二個評級、不覆蓋主研究。`agents/adapters/` 只寫介面、預算與用量紀錄形狀：沒有 transport 就明確拒絕，不會假裝 API 已接通。

發布時當次的價格陣列由參數傳入（`publish(..., bars=...)`），只用來畫圖與量度，**不寫入保存的 research.json**；發布包只複製被引用的證據原文，`evidence.json` 仍是完整索引。沒有陣列時頁面顯示衍生數字與資料截止，不畫空圖。契約對照見 [契約說明](contracts/README.md)。

頁面只顯示來源登記與原始檔連結，原文不再內嵌。移動或分享頁面請保留整個發布目錄；只取走 `index.html` 會失去本地來源連結。renderer 版本 0.3.0、calculator 0.2.0。

## 服務層(W1)

CLI、MCP 與日後的排程共用同一組函式:`service.py` 是操作入口,`store.py` 是持久狀態,
`mcp_server.py` 只是薄包裝(每個工具一行呼叫 service)。服務層本身不呼叫任何模型;研究方法
的正本住在 `agents/protocol.py`,`service.get_research_protocol` 只作轉介,不自己寫規則。

| 入口 | 做什麼 |
|---|---|
| `store.init(<path>)` | SQLite(WAL):`entities` 公司／證券／產業節點、`sources` 證據索引(身份沿用 registry manifest)、`research_versions` 版本化研究與計算回執、`jobs` 覆核／研究／取數任務 |
| `service.get_research_context` | 已有研究版本、來源索引、待補請求、待處理覆核;原文不內嵌 |
| `service.refresh_sources` | 呼叫 edgar／defeatbeta／longbridge,登記後回新增／變更／無變／失敗／未覆蓋;變與不變按內容指紋,不按取得時間 |
| `service.search_evidence`／`read_evidence` | 索引查詢與按行分頁讀原文(回 `L<起>-L<迄>` 定位);查不到只代表本地未登記 |
| `service.ingest_source` | 登記用戶提供的報告、連結或實際讀到的摘錄;摘錄標 truncated,作者立場與本系統判斷分開記 |
| `service.calculate` | 包 `calculations`,回結果、單位、輸入回執與計算器版本;未知方法拒絕 |
| `service.save_research`／`publish_research` | 先驗證後保存,撞版本回衝突不覆寫;發布先寫檔再記錄頁面位置 |
| `service.request_review`／`claim_review`／`submit_review`／`get_job` | 覆核任務的開票、領取與交回;API 模式的實際呼叫留 W2 |

憑證放**倉根 `.env`,不 commit**(已在 `.gitignore`);系統環境變數已設的一律優先,`.env` 不覆蓋。
Longbridge 公開行情用 `LONGPORT_APP_KEY`、`LONGPORT_APP_SECRET`、`LONGPORT_ACCESS_TOKEN`;
EDGAR 用 `KARST_EDGAR_USER_AGENT`。缺憑證時 `fetch/longbridge.py` 每個輸出寫 `status: error`、
`status_reason: credentials missing`,不拋例外也不捏造回傳。本地啟動:

```bash
python -m karst.fetch.longbridge --symbol <代號.US> --out <STAGING> --start <ISO> --end <ISO>
python -m karst.mcp_server --store <DIR>/karst.sqlite3 --bundle <BUNDLE> --staging <STAGING>
```

MCP 預設 stdio;`--http` 是 W2 的遠端部署,現時明文拒絕。`--env-file` 可指定另一個憑證檔。
服務層只開公開市場方法,倉內沒有帳戶／持倉／下單類入口,manual 落地入口 `fetch/broker.py` 不變。

## 此步邊界與本地接線

- 程式已提供：契約與來源 hash／引用／時間檢查、增量補查的 packet 版本、年末 FCFF DCF、每股與百分比 R&R、壓力價損失、SMA200、帶確認時間的局部轉折、日週月圖、不可變發布。
- 六層結論、情境假設、評級、目標價橋接、支撐阻力區域與相位，由已保存的研究輸出提供。程式不把這些當作已驗證的投資能力，也不聲稱已執行六個角色。引用檢查只證明存在及定位有效，不能證明論證成立。
- 自動估值目前只算 FCFF DCF。銀行、資產重估、商業化前公司等不應硬套；填 `valuation.status=unavailable` 並交代缺口。方法選擇與替代估值可先呈現文字，增加新計算方法時擴充版本化契約及測試。反向 DCF、估值敏感度矩陣、通道與突破回測偵測尚待實作。
- 首屏以依據與缺口幫助閱讀；沒有「已量度／未量度」格。只有合成／歷史重播的來源狀態提示，避免把舊包當即時分析。
- 目前沒有部位配置或百分之一風險預算。R&R 是條件價格下的算術，退出參考不是最大可保證損失，壓力情境另列。
- 本地 adapter 保留原始回傳和 `.meta.json`，再正規化成四份契約；未知時間、單位、缺頁不可補成已知。補查登記新來源版本後，用 `resolve_request` 產生新 packet，再重新產生對應的 research。
- SQLite、快取、事件訂閱、依賴路由、並行 worker、真實模型 context 隔離與允許清單留待接線及 KARST-242。當前私密欄位守衛只檢查部分 selector；它不能代替 adapter 的工具權限限制或原始回傳清理。
- 84 包考試原始目錄及抽取程式均未改。本測試集沒有重跑它，也不取代其回歸用途。

## 模組分工

| 模組 | 責任 |
|---|---|
| config、schema | 配置、身份／證券映射、版本化契約;憑證只讀環境,不寫入研究包 |
| fetch/ | **已實作(本地 adapter)**:按來源分 edgar、defeatbeta、prices、broker;`common.py` 共用 meta 寫入(固定欄序、UTC Z、sha256)、時間轉換(帶偏移轉 Z、只有日期原樣、無偏移回 None)、限速、HTML 轉文本、代號→CIK。edgar 先查本地 submissions 與 10-K 快取(D-134)再上 EDGAR;prices 本地 parquet 接 DefeatBeta 並核重疊;broker 只落地公開市場方法的回傳,帳戶／持倉／下單鍵拒收。正規化成契約與快取／SQLite 仍待接 |
| manifest | 來源版本、原始內容 hash、解析衍生物及定位;同內容去重但保留來源關係 |
| store | **已實作**:SQLite schema、索引與持久狀態;單一提交者、交易與版本檢查(撞版本回衝突不覆寫) |
| service、mcp_server | **已實作(W1)**:CLI／MCP／排程共用的操作函式與薄包裝;不呼叫模型,研究方法轉介 agents/protocol |
| packet | 建允許清單中的研究輸入包、必讀與缺口;不載入私人／模型帳本或開發上下文 |
| agents/ | 六角色任務、結構化輸出、有限補查、引用檢查;記實際模型與提示詞版本 |
| ta/ | 關鍵區域、200 日 SMA、日週月、通道與突破回踩,確認時點不前視 |
| valuation/ | 基本面情境到當日內在價值、估值敏感度、反向要求與有期限的目標價橋接 |
| plan | 每股／百分比 R&R、條件執行與壓力情境;不讀私人淨值 |
| publish、page/ | 不可變發布包、latest 視圖、HTML;發布前檢查依賴版本 |
| events、jobs | 來源訂閱、新事件、依賴路由、去重、重試與期限覆核 |
| model_portfolio/ | 自有模型委託、配置、紙上訂單與帳本;與研究輸入隔離 |
| evaluate/ | 固定期限、發布後成交、總回報／成本／基準與錯誤歸因 |
| run | 單股與批次共用協調入口、輸入 pinning、成本及執行紀錄 |
| tests/ | 通用契約、隔離、時間、計算與失敗恢復的參數化測試 |

未來即時入口可再加入 `--ticker`、`--as-of` 與 `--universe`；目前只支援上述 `--bundle`，避免把尚未接通的來源當作已可用。

## 通用性及隔離規矩

1. 生產程式不寫死任何股票識別或公司特例;不同申報形式／會計口徑用明確資料與適用規則配置。來源 adapter 按來源,不按股票複製。
2. 測試只在 karst/tests/。參數化 fixture 可以有代號、日期與可信預期數字;這是在驗證通用處理,不是以「不准股票專用腳本」禁止有效測試。大型84包保留原位置,測試以引用讀取。
3. 正式研究 worker 的 context 和可用工具由 packet／執行器允許清單決定;不是把整個 repo 交給模型再要求忽略私人資料。MCP 全 server 可用不代表其所有方法可給研究角色。
4. 強模型讀原文並判斷,程式計算;便宜模型轉換結果不能遮住原文。策略不依賴特定框架或無限 agent 辯論。
5. 新模組先在本表登記;工作票按通用能力開,換第二股不新增一支程式。P1 只落實必要模組,P2/P3/P4 按設計漸進增加。
