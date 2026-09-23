# karst/ —— 通用工作台程式(D-180／D-181)

所有生產程式從第一天可跨公司重用。代號、公司映射、日期、路徑、來源和模型由參數／配置傳入,不建立股票專用抓取或分析腳本。一次性探索與除錯碼放倉外 scratch,不 commit。

本分支落實 D-183／KARST-241 的離線部分：四份契約、檔案式取證包、補查版本、確定性計算與股票頁發布。下表仍是完整計劃，不代表每個模組都已存在。契約與驗收見 [契約說明](contracts/README.md) 及 [設計計劃](../strategy/specs/獨立投研工作台設計與交付計劃-v1.md)。

## 公開閱讀頁（GitHub Pages）

`python -m karst.reader --content cards/reader --output <新目錄>` 生成總覽、個股／主題、固定最新頁、歷史版與更新紀錄；僅 Python 標準庫，無服務或模型呼叫。Agent 程序、公開邊界與部署狀態見 [`cards/reader/README.md`](../cards/reader/README.md)。此模組不替代現有研究資料室或正式研究版本。

## 手動增量更新（核心 0.2.4）

1. `get_research_context(subject)` 同時回目前版本、觀察項目及 `update_plan`。這個讀取不取新資料、不執行模型；`refresh_status` 列實際取得範圍和時間，不能把目錄沒有新增說成全市場沒有新聞。
2. 按觀察項目用 `refresh_sources` 取需要的來源；刷新結果也回更新計劃。`plan_update(subject)` 可單獨重查。逐份來源對照原版本，包括新發現而未被引用的文件；只改取得時間不視為新研究。來源恢復舊內容時查看 observations，不只比 manifest 的首次取得時間。
3. 讀計劃及必要原文，判斷實際影響。`affected_layers` 是分流範圍，`reuse_candidates` 是待研究者核可的沿用候選，均不是投資結論。價格日檢查 L4 的現價要求、L5 與 L6；舊經營假設、估值日及目標日不自動滾動。任何舊分析錯誤均可修訂，不以「沒有新文件」拒絕重評。
4. 無需修改分析時，以 `record_update_check(subject, plan_id, outcome, reason)` 留查核紀錄，不新建研究。outcome 為 `unchanged`／`needs_reassessment`／`incomplete`；取數失敗或空白覆蓋不能登記為 unchanged。紀錄會再核資料與版本；重試不重複新增。
5. 需要改建議時，讀指定 `as_of_version` 的完整研究，準備新 packet，交完整更新分析到 `save_research`。API 任務亦帶上一版實際假設／日期，清楚標為 previous analysis，不冒充新閱讀。完全未變的層保留 assessed_at；`headline.change_since_last` 寫變化理由。相同分析、輸入及前版的保存重試取回同一研究版本；並發的不同更新仍須核前版。
6. 指定版本的 context 回 `changes_since_previous`：數字／欄位的前後差異、各層沿用狀態及研究者理由。Agent 據此整理既有五段閱讀頁，前面先說改了甚麼、為甚麼、現在怎樣做；完整識別碼和原始差異只留 Agent 紀錄。新資料在研究期間到達時，context 仍列待重評，舊快照不冒稱最新。

`set_watch` 需基於最新研究版本；修改用 expected_version 防覆蓋。觀察內容為 waiting_for、conditions、validation_deadline、subscriptions、dependencies；`get_watchlist` 讀全部，版本附加保存。價格條件明列 gte／lte、value、currency，只比較未復權的最近日線，並標完成狀態與日期；未完成只報未知，達價不等於執行交易。事件條件由 Agent 判讀；到期即使沒有新文件仍須檢查事件缺席。

依賴明列 input_kind（source／entity／relation／assumption）、input_id、input_version、assumption_id、assumption_version、layers、exposure。來源／實體訂閱可發現其他公司資料倉的新報告，各公司保留自己的暴露說明。明示關係或假設修訂可用 `plan_update` 的 input_changes（kind、id、version、reason）分流，記錄查核時傳回相同 input_changes。這是依賴查詢，**不是完整關係圖資料庫或自動判斷傳導**；外部資料要用於正式研究引用仍需登記入本次取證包。

首版保留缺口：未接排程／通知、未自動執行研究或覆核、未把 DB 自動同步到 Pages；舊六角色跨 packet runner 不在此改造。Claude 不可用時獨立覆核繼續待辦，主研究沿用或自查不視為獨立覆核。來源與股票頁不因本功能而擴充指標。

## 現在可跑

Python 3.11+，在倉根目錄建立虛擬環境後：

```bash
python -m pip install -e .
python -m unittest discover -s karst/tests -v
python -m karst.run --bundle karst/examples/synthetic --output /tmp/karst-releases
```

最後一行輸出 `index.html` 的絕對路徑，瀏覽器直接開啟。頁面不依賴網絡、前端伺服器或外部資源。`--validate-only` 可單獨驗證輸入；`--previous-publication-id <ID>` 可連結上版。換股票只換 bundle，不新增程式。

五個來源適配器（edgar／defeatbeta／longbridge／prices／broker）把原始回傳落到 `<out>/<source>/…`，每份旁邊一份同名 `.meta.json`（形狀 = `tests/fixtures`，另加 `status` ok/empty/error、`status_reason` 與 `source_url`）；代號、CIK、日期一律由參數傳入。CLI 照舊（longbridge 那條見〈服務層〉）：

```bash
set KARST_EDGAR_USER_AGENT=<name email>   # EDGAR 要求；先查本地 submissions 與 10-K 快取，其餘線上抓
python -m karst.fetch.edgar --ticker <代號> --out <DIR>            # 或 --cik；10-K/10-Q/8-K(+EX-99.1)，失敗寫 status error 不捏造
python -m karst.fetch.defeatbeta --ticker <代號> --out <DIR>       # 逐字稿清單與最新全文（預設不截短）、三張季表、拆分、股數、拆股、日曆、info
python -m karst.fetch.prices --ticker <代號> --out <DIR>           # 本地 parquet 最近 400 日 + DefeatBeta 續抓，重疊日核收市價；--no-continue 只用本地
python -m karst.fetch.broker --out <DIR> --source futu --tool <工具> --symbol <代號> --params '{}' --response-file <F>  # 只落地代理人已拿到的 MCP 回傳；不呼叫 MCP，帳戶／持倉／下單類鍵一律拒收
```

### 來源接口(source port,KARST-246)

每個 adapter 對外只有兩樣東西:`KINDS`(它負責哪幾種證據)與

```python
fetch(security, out_dir, *, since=None, client=None) -> list[LandedRecord]
```

`LandedRecord` = `{kind, path, meta_path, published_at, fetched_at, period, coverage, status, status_reason}`。
**種類由 adapter 明報**,登記器照用不反推;ok／empty／error 也只在落地時判一次,
登記器認結果(舊 sidecar 沒有 status 時才走舊推斷)。供應商代號轉換留在 adapter 內
(`longbridge.symbol_for`),CIK／代號由 `port.cik_for`／`ticker_for` 由 security 推。
`client` 是該 adapter 要呼叫的東西(HTTP getter、SDK client、Ticker factory),或者一個
選項 mapping(測試與重播用:fixture 目錄、注入的列)。`fetch` 不是插件框架,沒有註冊表掃描。

**加一個來源要改幾處:一處。** 寫一個 `karst/fetch/<來源>.py`(`KINDS`、`kind_for`、`fetch`),
在 `service.ADAPTERS` 加一行;`KIND_ADAPTERS` 由各 adapter 宣告的 `KINDS` 組成,
`service._run_adapters` 對同一張表迭代,沒有 if/elif。讀多個 feed 的 adapter 回 `port.Landing`(記錄＋逐 feed 的 `FeedOutcome`),單一來源的回普通 list,由 `port.cover` 從記錄推出覆蓋。(改動前要動的是:adapter、
`service.KIND_ADAPTERS` 手寫表、`service._run_adapters` 的分支、`registry.PUBLIC_KINDS`
或 `evidence_kind` 的推斷規則,共四處。)

`fetch/broker.py` 是手動落地:它不呼叫 MCP,`KINDS` 是空的(`refresh_sources` 不會路由到它),
`client` 是代理人已經拿到的回傳清單。`fetch/prices.py` 同樣不接 `refresh_sources`
路由(日線由 longbridge 供),保留作 CLI 與重播入口。

`examples/synthetic/` **全部是合成資料**，含虛構公司、日期、預測與價格；不屬於真實接口樣本，也不是投資建議。本地已提供的真實回傳在 [tests/fixtures/](tests/fixtures/README.md)，新增測試引用其期間形狀，未把轉錄數值當估值真值。本核心讀取已保存的 `research.json`，不會自行呼叫模型、生成評級或讀券商帳戶。

契約目前為 **0.4.0**（估值方法分派，KARST-247），保留 0.3.0、0.2.0、0.1.0 讀取，舊 bundle 與舊發布不變；收件預設出 0.4，0.3 的 packet 照它自己的版本收。第二輪接線要看 [契約的遷移表](contracts/README.md)：日期精度與時區、原始 coverage、error/empty 取得紀錄，以及手填判斷的 `integration_example` 模式。Windows 缺符號連結權限時只略過該項測試，路徑逃逸檢查照跑。

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

**任務目錄只有一份落地實作**(`agents/staging.py` 的 `stage_task`,KARST-246):六角色
(`agents.inputs.prepare_inputs`)、主研究(`research.export_task`)、覆核
(`review.build_review_task`)三處只負責組自己的 context,隔離規則(目的地不得是 bundle
或其上層、`mkdir(exist_ok=False)`、只複製允許的 artifact、`input.json` /
`output.schema.json` / 提示詞、中途失敗整個刪掉)住在一處。`extra_files` 讓呼叫者多帶
幾個檔(例如 `charts/`),提示詞檔名由呼叫者給(主研究 `prompt.md`、覆核 `review.md`)。

**證券價格序列**(`karst/bars.py`,KARST-254):讀已登記 K 線只經 `bars.series_for(bundle, security, as_of, records=None)`,回 `Series`(`daily`、`views`、`source`、`basis`、`gaps`、`last_complete`)。身份核對、交易時段、口徑與選源規則都在裏面;歷史夠不夠問 `series.enough("chart" | "daily_check" | "publication")`,門檻只在 bars 模組定義一次。呼叫方不再自己推 `Session` 或讀 `_basis`。

**日更規模化**(KARST-256):
- `karst/fetch/limits.py` 是每個外部來源的呼叫上限(速率、並行、逾時、重試退避),adapter 的每次網路呼叫都經 `limits.call(來源, 函式)`;逾時／429 在覆蓋回報記 timeout／rate_limited。
- `daily.refresh_scope` 以 `WORKERS`(預設 8)個成員並行,每條工作線程自開 SQLite 連線;檢查點只追加(`<run_id>.json` 表頭加 `<run_id>.members.jsonl` 每股一行)。`daily.start` 在背景跑並回表頭,`daily.wait`／`run_summary` 回摘要,重啟後以 `resume_run_id` 續跑。
- 每股的價格序列存在公司證據倉(`CompanyBundle.daily_series`),K 線只由最後一根已收市起取,新快照接駁等同全量重建(有測試),口徑或身份不同就全量重建。
- `karst/daily_snapshot.py` 產生日更快照(`CompanyBundle.save_daily_snapshot`):計劃價距離、觸發狀態、收市 R&R、公允價值位置、價格事件與重評排隊;事件門檻集中在該檔頂部。它不改研究版本、不寫查核、不發布。
- **增量分流**(`karst/triage.py`,KARST-257):`updates.plan` 仍是純函式;`triage.inputs(store, bundle, subject, data_dir=…)` 收集它讀的一切(本公司證據、觀察項訂閱／依賴帶進的他公司來源、只取本證券自己的收市價、取源狀態、方法版本、已存關係／假設修訂),`triage.plan`／`triage.record_check` 是 `service.plan_update`／`record_update_check` 的實作。新聞窗口規則只在此處:`news_since` 定日更由何時讀新聞(只有 `unchanged` 查核才推進,重疊一日),`check_outcome` 擋覆蓋不完整或無研究基準的 `unchanged`(store 收件時呼叫),`unread_queue`／`news_pending` 定重評排隊何時算已讀。
- 量度:`python -m karst.daily_bench --members 200 --workers 8 --price-delay 0.5 --article-delay 0.455`(假 client,預設先跑一次「前一日」再量穩態)。

**模型可讀的標準圖**(`karst/charts.py` 0.3.1,matplotlib Agg):
`service.render_charts(bundle, out_dir, store=…)` 由**已登記的日線證據**組本次陣列,畫
**四張 PNG**——月(長期位置)、週(主要趨勢)、日線全貌、近期放大(最後 90 根,足以看
K 棒實體與影線)。每張都是 **OHLC 蠟燭 + 成交量**(另畫 20 根平均量),均線是**曲線**:
200／50 日 SMA 與 20 日 EMA **先用完整歷史計算,再裁到該視窗**,所以放大圖照樣看得出
200 日線的真實斜率;週／月圖映射的是同一條**日線**均線,圖例明寫 `200-day SMA`,不會
變成 200 週／月。未收定的 K 棒加斜紋與虛線,且不移動均線(副題已明寫 `last bar
unconfirmed`,圖內不另加標示——它落在右邊每句說明的位置上);價格軸按窗內高低比自動選
線性或對數(`scale="log"/"linear"` 可指定),標題與說明帶標的(由參數傳入,碼內沒有代號)、
週期、日期範圍、資料截止,以及**來源供應商名與取得日期**。圖是公開檔,像素抹不走,所以
`evidence_id` 只留在 `derived.json` 與 artifact 紀錄,不印在圖上。

支撐阻力畫成**有錨點的區域**:已確認 pivot 按容差歸成一條 band。**容差是價格的比例**
(0.25×ATR14÷收市價與 0.4% 取大者),不是金額——金額容差在對數長圖上會把幾年前的低位併
成一塊無意義的巨帶。每個錨點分開記**形成日**與較後的**確認日**,圖上用圓點與豎線分別標出;
區域是支撐還是阻力按它與現價的相對位置定,band 由高點還是低點造(`pivots`)另記,圖上那
句說明兩樣都寫(例:`support … (2 pivot highs, now below price)`)。

圖上的文字說明按左右兩邊各自排開,不會疊在一起:全歷史的日線圖與週／月圖只寫最靠近現價
的兩個區域與最近一次 BOS／CHoCH,其餘只畫線與區域;放大圖才逐項寫。圖例移到圖框之外(上方
一行),不再蓋住 K 棒。數字一律以 `derived.json` 為準。

**結構事件**(`karst/structure.py`,定義版本 `karst.structure/1`,KARST-251):沿用**同一套已確認
pivot**(左右對稱窗口、嚴格比較、以右邊那根收市確認;**與 LuxAlgo 的 `leg(size)` 不同**,不聲稱
逐點一致),標出 HH／HL／LH／LL 與趨勢狀態,再判**收線突破**最近一個已確認 swing level:順勢
是 BOS,逆着已成立趨勢的第一次是 CHoCH;趨勢未明或結構尚未建立時只記 BOS,不硬標 CHoCH。
另有前高／前低(已被突破那條,連同其後有沒有被回踩)、**等高等低**(相鄰同側 swing 相距在
`atr_multiple`×ATR 之內)與 **liquidity sweep**(影線越過已確認 level、收市回到原側;突破後在
`reclaim_window` 根之內收回原側則另記一次跨 bar 的 sweep,並把該次突破標為失效)。每個事件記
`anchor_time`(價格極值形成)、`confirmed_at`(令它可知的那根收市)、方向、價位／區域、
`definition` 與參數、`refs` 與失效條件,狀態只准向前走(provisional → confirmed → touched →
invalidated)。**未收定的 bar 只出 provisional,不改任何狀態**;每根 bar 先對之前已可知的 level
判突破與 sweep,再收下它自己確認的 pivot,所以同一根 bar 不會既確認一條 level 又突破它——
逐根重播同一序列會重現同一段歷史,而不是事後重建的版本(`test_structure.py` 的 prefix replay)。
日／週視圖在 `derived.json` 的 `views.<view>.structure` 帶 `state` 與最近 12 個事件
(`render(..., events_kept=…)` 可調);圖上只疊最近一次 BOS／CHoCH、現時 swing 與前高低、最近
三次 sweep,圖例與支阻區分開,月線不疊。`charts.structure(bars, "W")` 是同一套套在週線 bar 上。

`derived.json` 保留畫圖用的同一批數字:各均線精確值、與現價距離、**MA200 對前 20 個
交易日的方向**(變動、百分比、rising／falling／flat)、**ATR(14,Wilder,算法與期間寫
在 JSON 內)**、**量比**(尾根對前 20 根)、每個區域的錨點與確認時點、每個視圖的 bar 數
／已收定數／窗口／座標,以及 `parameters` 與 `params_digest`。**圖檔與 JSON 都不含價格
陣列**——陣列只活在這次呼叫的記憶體裡,JSON 亦不含本機路徑。

每張圖同時回一個 **artifact**:`artifact_id`(= `cha-` + PNG 的 sha256)、view、period、
hash、bytes、`bars_as_of`、`drawn_from`／`drawn_to`、來源 `evidence_id` 與參數指紋;同一
批 bar、同一組參數畫出同一張圖,id 就是同一個。**檔名帶內容指紋**
(`daily_recent-<12位>.png`,`derived-<12位>.json` 同理),所以明天再畫是落在旁邊而不是
蓋住今天那張——承諾「當時看過那張圖仍取得回」就不能與下一版共用一個路徑;
`derived.json` 本身是最新一次的指針。給了 `store=` 就登記到 `chart_artifacts`
(見〈服務層〉),這是遠端能讀圖的前提。`service.without_local_paths(result)` 是回給遠端
客戶端的形態(去掉本機路徑),`service.chart_artifact(store, artifact_id)` 取回圖檔並**先
核 hash 才交**。`export_task(..., charts=…)` 把四張圖、`derived.json` 與 artifact 清單
(`path` 換成任務目錄內的相對路徑)放進任務的 `charts/`。MCP 工具
`render_charts(subject, output_dir=None, as_of=None)` 回 artifact 清單(不回路徑),
`read_chart(artifact_id)` 回**真正的 ImageContent**(base64 PNG)加一段身份 JSON。

覆核由 `agents.review` 處理：`build_review_task` 匯出針對指定 `research_id` 與指定爭議的任務，`REVIEW_RESULT_SCHEMA` 與 `validate_review` 收挑戰（針對層、主張、引用、嚴重程度）、對爭議的裁決與新補查請求；覆核者不給第二個評級、不覆蓋主研究。`agents/adapters/` 已接 Anthropic Messages 與 OpenAI Responses 兩條實際呼叫路徑（回合迴圈、本地工具 list_evidence／read_evidence／calculate／有圖時 read_chart、圖像以真正 image content 送出並記錄、預算與用量），見下面〈覆核入口〉；缺憑證或缺 transport 一律明確報錯，不假裝已接通。

發布時當次的價格陣列由參數傳入（`publish(..., bars=...)`），只用來畫圖與量度，**不寫入保存的 research.json**；發布包只複製被引用的證據原文，`evidence.json` 仍是完整索引。沒有陣列時頁面顯示衍生數字與資料截止，不畫空圖。`service.publish_research` 不必逐次傳：沒給 `bars` 時它先由**已登記的日線證據**（`karst/bars.py`）組陣列，再退到 `bars_provider` 臨時取數（不登記、不保存）；晚於資料截止的 K 線一律拒收。**重組出來的日線比該版自己記下的技術基礎（`technical.derived.bars_count.D`）短一成以上就報錯,不靜靜出一張少了轉折點與 200 日線的圖**；錯誤會講明原因（被時點守則擋走的快照，或該版證據內根本沒有日線序列），要麼傳 `bars=`，要麼改用證據當時存在的截止時點。契約對照見 [契約說明](contracts/README.md)。

頁面只顯示來源登記與原始檔連結，原文不再內嵌。移動或分享頁面請保留整個發布目錄；只取走 `index.html` 會失去本地來源連結。renderer 版本 0.3.0、calculator 0.2.0。

## 服務層(W1 本地核心、W2 傳輸與公司證據倉)

CLI、MCP 與日後的排程共用同一組函式:`service.py` 是操作入口,`store.py` 是持久狀態,
`mcp_server.py` 只是薄包裝(每個工具一行呼叫 service)。服務層本身不呼叫任何模型;研究方法
的正本住在 `agents/protocol.py`,`service.get_research_protocol` 只作轉介,不自己寫規則。

| 入口 | 做什麼 |
|---|---|
| `store.init(<path>)` | SQLite(WAL):`entities` 公司／證券／產業節點、`evidence_text` FTS5 全文索引(隨時可由 manifest 重建)、`research_versions` 版本化研究(連它當時的 packet 與證據索引)與計算回執、`jobs` 覆核／研究／取數任務、`chart_artifacts` 已登記的圖(id→檔案、hash、週期、來源;圖在任何研究版本存在之前就畫好,所以不掛在版本或任務行上,`read_chart` 只認這張表)。**證據登記本身不進 SQLite**:身份住在各公司證據倉的 manifest,倉內不留第二份 |
| `service.get_research_context` | 已有研究版本(帶前一版與各自發布編號)、來源、待補請求、待處理覆核;原文不內嵌。`as_of_version=` 切換兩種讀口(見下) |
| `service.company_paths`／`ensure_company` | 每家公司一個證據倉(`<data>/companies/<證券ID>/bundle`)與發布目錄;同時 upsert 證券與公司節點 |
| `service.refresh_sources` | 按 `KIND_ADAPTERS` 經**來源接口**呼叫對應 adapter(`clients[<adapter 名>]` 可注入 client)**落入該公司的證據倉**,暫存去 `<data>/tmp/<run>/`;只登記 adapter 報回的 LandedRecord;回新增／變更／無變／失敗／未覆蓋,變與不變按內容指紋,不按取得時間;`coverage` 是逐 adapter 的**取源覆蓋回報**(`port.cover` 唯一判定 ok／partial／failed,`feeds` 逐來源列 cause:error／timeout／rate_limited／empty 與原因),同一份寫入 `refresh_status`;某個來源爆掉只成為該 adapter 的 failed 回報,不拖垮其餘。`daily` 的取源是否完整只看 `port.complete(coverage)`;舊版新聞 `coverage.json` 側檔已不再寫也不再讀 |
| `service.search_evidence`／`read_evidence` | 索引查詢與按行分頁讀原文(回 `L<起>-L<迄>` 定位);`text=` 走 SQLite FTS5 全文(回 snippet 與行號估計),無 FTS5 明確報錯不靜默退化;`as_of_version=` 改問某版當時用了什麼,回傳的 `scope` 明寫答了哪一條;查不到只代表本地未登記 |
| `service.ingest_source` | 登記用戶提供的報告、連結或實際讀到的摘錄;摘錄標 truncated,作者立場與本系統判斷分開記。**`kind=industry_report` 必須帶 `entity_ids`(`NASDAQ:XXX`／`cik:…`／`industry:<slug>`)、`author`、`published_at`、`source_type`**(broker_report／independent_research／news／user_note／other),缺哪一項就報哪一項 |
| `service.render_charts` | 由已登記日線組本次陣列,出月／週／日／近期四張蠟燭圖、`derived.json` 與 artifact 清單(見上);`store=` 登記 artifact,陣列不保存,沒有已登記日線就明報,不畫空圖 |
| `service.chart_artifact`／`without_local_paths` | 按 `artifact_id` 取回已登記的圖(先核 hash 才交,未登記或檔案不符一律拒);回遠端時去掉本機路徑,只留 artifact |
| `service.bundle_for`／`bundles_for` | 「這個 subject 該寫哪個證據倉、該搜哪幾個」的單一規則;MCP 只把它的 `--bundle` 傳進來問 |
| `service.save_research`／`publish_research` | 轉交研究收件 `agents.research.save`:讀一次 packet、驗證一次後保存,撞版本回衝突不覆寫;payload 的補查請求登記入新 packet(同 as_of／created_at),版本存入後才寫回證據倉;**保存時連當時的 packet 與證據索引一起凍結**,發布只用該版凍結的輸入、指回前一次發布、畫本次臨時日線,再記錄頁面位置並更新公司資料室 |
| `service.request_review`／`claim_review`／`submit_review`／`get_job` | 覆核任務的開票、領取與交回;`execution='api'` 直接呼叫 adapter 並寫回結果(見〈覆核入口〉) |

憑證放**倉根 `.env`,不 commit**(已在 `.gitignore`);系統環境變數已設的一律優先,`.env` 不覆蓋。
Longbridge 公開行情用 `LONGPORT_APP_KEY`、`LONGPORT_APP_SECRET`、`LONGPORT_ACCESS_TOKEN`;
EDGAR 用 `KARST_EDGAR_USER_AGENT`。缺憑證時 `fetch/longbridge.py` 每個輸出寫 `status: error`、
`status_reason: credentials missing`,不拋例外也不捏造回傳。本地啟動:

```bash
python -m karst.fetch.longbridge --symbol <代號.US> --out <STAGING> --start <ISO> --end <ISO>
python -m karst.mcp_server --data-dir <DATA>                  # stdio,本地開發
KARST_AUTH_MODE=token KARST_MCP_TOKEN=<token> python -m karst.mcp_server --http --port 8080 --data-dir <DATA>
```

`--data-dir`(或環境變數 `KARST_DATA_DIR`,預設 `./karst-data`)是唯一持久根:

```
<data>/karst.sqlite                       研究版本(連當時的 packet 與證據索引)、任務、FTS5 全文索引
<data>/companies/<證券ID 安全化>/bundle/   該公司唯一證據倉(evidence/objects、manifest.jsonl、evidence.json、packet.json、security.json);只經 karst/company_bundle.py 讀寫
<data>/companies/<證券ID 安全化>/releases/ 發布頁
<data>/tmp/                               取數暫存與任務目錄,可清
<data>/oauth-proxy/                       github 模式的授權狀態(客戶端註冊、加密後的上游 token)
```

`--http` 用 fastmcp 的 streamable-http,驗證由 `karst/auth.py` 的 `build_auth()` 按環境變數決定,
**兩個模式都未設就拒絕起動 http**(stdio 不需要驗證):

| 模式 | 怎樣開 | 用在哪 |
|---|---|---|
| `github` | `KARST_AUTH_MODE=github` 加 `KARST_GITHUB_CLIENT_ID`／`KARST_GITHUB_CLIENT_SECRET`／`KARST_BASE_URL`／`KARST_ALLOWED_GITHUB_USERS` | 遠端部署。fastmcp `OAuthProxy` 代理 GitHub 的授權碼 + PKCE,客戶端動態註冊、自己拿 token;ChatGPT 的自訂連接器沒有固定 token 欄位,只能行這條 |
| `token` | `KARST_AUTH_MODE=token` 加 `KARST_MCP_TOKEN` | 本機或過渡;客戶端自己帶 `Authorization: Bearer` |

`github` 模式的**允許清單是硬閘**:`KARST_ALLOWED_GITHUB_USERS` 以外的登入名,即使 GitHub 授權成功,
每個請求一律 401(檢查住在 token 驗證器,不只擋工具呼叫);清單為空拒絕起動。回呼路徑是 fastmcp 的
預設 `/auth/callback`,GitHub OAuth App 要填 `KARST_BASE_URL` 加這個路徑。授權狀態存在
`<data>/oauth-proxy/`(加密,鑰匙由 client secret 推導),重啟之後兩端不用重新註冊。
`GET /healthz` 兩個模式都免驗證,回 `{status, version, data_dir}`。舊的 `--bundle`／`--staging`
保留為相容選項(固定單一證據倉)。`--env-file` 可指定另一個憑證檔。備份:
`python -m karst.store backup --data-dir <DATA> --out <ZIP>`(SQLite 一致快照 + 證據檔,`tmp/` 不備份)。

**部署到 Zeabur、環境變數清單、GitHub OAuth App 建法,以及 ChatGPT 自訂連接器與
`claude mcp add --transport http` 兩端連接步驟:見倉根 [zeabur.md](../zeabur.md)。**

服務層只開公開市場方法,倉內沒有帳戶／持倉／下單類入口,manual 落地入口 `fetch/broker.py` 不變。

## 版本綁定、兩種讀口與重用憑證(KARST-245)

**一個研究版本擁有它自己的輸入。** `save_research` 把當時的 packet 與證據索引(該 packet 選中的
記錄,packet 次序)一併存入 `research_versions`;`publish_research` 只用這份凍結輸入建發布,不讀
公司證據倉當下的 `packet.json`。公司之後再登記新證據、packet 換號,舊版本照樣發布得到,而且
**與首次發布逐位元相同**(同一 `input_hash` → 同一 `pub-…` 目錄)。證據**原文**仍住在公司證據倉:
內容定址,指紋不變就是同一份檔;發布複製時逐個重算 hash,這一關沒有省掉。舊 DB 沒有這兩欄的
版本讀回 `None`,發布退回讀當下 bundle 並在結果寫明 `inputs_from: "bundle"`,不假裝當時已釘住。

**發布鏈在 service 這條路成立。** `previous_publication_id` 由 store 沿 `previous_version_id` 找最近
一個已發布的前版取得(中間未發布的版本跳過),寫進 `publication.json`;`get_research_context` 每
行版本另帶 `previous_version_id` 與自己的 `publication_id`,資料室頁因此印得出「指回 pub-…」。

**兩種問法分開,不合成「永遠讀最新」。** `get_research_context` / `search_evidence` 不給
`as_of_version` 就是**目前可用資料**(公司證據倉現況);給了就是**該版研究當時使用的資料**(版本
自己的凍結索引)。回傳的 `sources_view` / `scope` 明寫答了哪一條;沒有凍結輸入的舊版本會明確
報錯,不會用今日的登記冒充當時。

**研究收件是一個 module(KARST-259)。** `agents.research.save(store, bundle, payload, *, subject,
role_meta, previous_version_id=None, clock)` 是保存研究版本的唯一入口,`service.save_research`
(MCP `save_research`)只是轉交。呼叫方只交分析 payload、前版引用與角色紀錄;收件在內部
**讀一次** packet(舊路徑一次保存讀四次、中途改寫一次)、把 payload 的補查請求登記在那份拷貝上、
按收件規則 `_build` 補齊工程欄位並**驗證一次**(`check_packet`／`check_research`)、跑計算器,
再由 store 在一個交易內追加版本;只有請求有增加而且版本已存入,才把新 packet 寫回證據倉,
衝突或拒收一律不留痕。舊的「驗證指紋憑證」(`Verified`/`fingerprint`)、`ImportError` 退路與
注入 `intake=` 參數均已移除——驗證不再跨 seam 重複,憑證就沒有存在理由。`intake(...)` 保留為
只驗證不保存的同一套規則。更新時哪些層沿用前版(今日:與前版逐字相同的層保留 `assessed_at`)
只寫在 `_build`,增量範圍控制(KARST-262)亦落在這裏。同一 payload、同一輸入與時鐘所得版本
編號與計算回執與重構前逐字相同(`test_version_inputs.SameVersionsTests`)。

## 覆核入口(W2)

覆核有兩條路,同一份任務、同一份結果格式:

| 模式 | 做法 |
|---|---|
| `execution='interactive'` | `request_review` 只開票;另一個客戶端 `claim_review` 領取、`submit_review` 交回 |
| `execution='api'` | `request_review` 同時建任務目錄(`agents.review.build_review_task`)、呼叫 adapter、驗證結果並寫回同一張票 |

```python
job = service.request_review(store, subject=<SUBJECT>, version_id=<VERSION>,
                             dispute="改善是否一次性？", evidence_ids=[...],
                             reviewer={"execution": "api", "provider": "anthropic",
                                       "model": <MODEL_ID>},
                             bundle=<BUNDLE>, task_dir=<TASK_DIR>)   # transport 可注入
```

adapter(`agents/adapters/anthropic_adapter.py` 走 SDK Messages、`openai_adapter.py` 走 httpx
對 Responses)只管線路格式;回合迴圈、預算、工具與結果驗證住在 `agents/adapters/__init__.py`。
模型**只有兩個工具**:`list_evidence()` 與 `read_evidence(evidence_id, offset, limit)`,由 adapter
在本機執行,**只讀該任務目錄**——沒有 bundle、沒有倉、沒有網絡、沒有帳戶入口。輸出必須是一個
符合任務 `output.schema.json`(覆核即 `REVIEW_RESULT_SCHEMA`)的 JSON 物件,不符即拒收。

預設預算 12 回合 / 400k 累計 input token / 16k output;`budget` 參數逐項覆寫。用量記
input、cached、output 與起訖時間;**`cost_usd` 留 null**——沒有價目表就不估價。憑證只由環境
變數名稱引用(`ANTHROPIC_API_KEY`、`OPENAI_API_KEY`,倉根 `.env` 或環境),缺即明確報錯,不
嘗試呼叫。

票的收尾三態:結果通過 `validate_review` = `done`;結果不符或未送出即失敗 = `failed`;**已送出
而結果不明(連線中斷、逾時)= `needs_check`**,由人對帳,程式不自動重發以免重複付費。三態都是
終態。**狀態轉換只有一處**:`store.JOB_TRANSITIONS` 列明每個目標可以由哪些狀態到達,service 一律
經 `store.transition(job_id, to, **欄位)`(單句條件 UPDATE,所以第二個領取者搶不到),非法轉換拋
`ContractError` 並講出該票現在的狀態;`to=None` 只記欄位(例如補用量),不算轉換。同一
(`version_id`, 爭議)已有非 failed 的票時,`request_review` 回舊票,不再付一次。
`get_research_context` 另回 `latest_review`:裁決、最強挑戰(層、主張、嚴重程度)與新補查數目。

## 資料室頁

`page/render_company_index(store, bundle, security, releases)` 出一頁公司資料室:該公司的證據
清單(**目前可用資料**:來源、種類、公開／取得時間、狀態、被哪幾個研究版本引用)、研究版本
清單(資料截止、評級、執行狀態、與上次相比一句、頁面連結、本版發布編號與它指回哪一個)、
待補請求與最新覆核摘要。`publish_research` 成功後自動寫入 `<releases>/index.html`;無框架、無外部
資源、明文可讀,與研究頁同一套 CSS。

資料室只索引已保存的東西,不重算任何判斷;查不到只代表本地未登記。證據清單答的是「公司證據倉
現在有什麼」;「某一版當時用了什麼」要按版本問(`as_of_version`),兩條問法不合成一條。

## 此步邊界與本地接線

- 程式已提供：契約與來源 hash／引用／時間檢查、增量補查的 packet 版本、五種估值方法與敏感度／反推（見下節）、每股與百分比 R&R、壓力價損失、SMA200、帶確認時間的局部轉折、日週月圖、不可變發布。
- 六層結論、情境假設、評級、目標價橋接、支撐阻力區域與相位，由已保存的研究輸出提供。程式不把這些當作已驗證的投資能力，也不聲稱已執行六個角色。引用檢查只證明存在及定位有效，不能證明論證成立。
- 銀行、保險、資產重估、FCFE 等仍未有對應方法，不應硬套現有五種；填 `valuation.status=unavailable` 並交代缺口，或用有依據的方法算再在 `alternative_view` 講分歧。

## 估值計算（契約 0.4，KARST-247）

`calculations.calculate_valuation(calculation)` 按輸入宣告的 `method` 分派，回一份回執
`{calculator_version, method, inputs_digest, outputs}`。**同一個計算器同時服務主模型、
替代視角、敏感度與反推**，所以頁上任何一個數字都追得回產生它的那份輸入。

| method | 算什麼 | 橋接 |
|---|---|---|
| `fcff_dcf` | 年度期末 FCFF 折現（0.2／0.3 原意，一字不改） | 舊欄位 cash／nonoperating_assets／debt／other_claims |
| `fcff_dcf_dated` | 估值日、各期現金流日期、期中／期末、首期 stub、擴張末期 FCFF 與正常化終值 FCFF 分開、終值有自己的日期 | 共用橋接 |
| `forward_pe` | 前瞻 P/E：每股盈利口徑、期間、倍數、適用日，可按折現率折回估值日 | **股權倍數，禁接企業橋接** |
| `ev_multiple` | EV/EBIT 或 EV/EBITDA | 共用橋接 |
| `sotp` | 各分部企業價值 × 持股比例加總 | 全公司只做一次共用橋接 |

共用橋接：現金、非經營資產、債務、少數股東、可贖回權益、可轉債／認股權（**要留空就必須在
`unsupported_claims` 寫明缺口，不准靜靜當零**）、攤薄股數、SBC 處理（哪一邊入帳加一句說明，
不重複扣）。`scale`（absolute／thousands／millions）同時套在金額與股數上，所以每股值不因尺度改
變，而回傳的金額一律絕對單位；0.2／0.3 沒有 `scale` 的輸入照舊當 absolute。

- `sensitivity(calculation, changes)`：`changes` 用 `model.flows.2.amount` 這種點路徑指到
  **已存在的數值**輸入；路徑打錯或指到整個物件會拋錯，不會靜靜無效。回執的 `inputs_digest`
  是**未改動**那份計算的指紋，所以查得到它屬於哪個情境。
- `solve_implied(calculation, target_price, solve_for, bounds)`：先在範圍內取樣再二分，
  回 `solved`／`no_solution`／`multiple_solutions`／`undefined`，不會把多解硬報成一個答案。
- 研究可在 `valuation.sensitivities[]` 與 `valuation.implied` 保存模型當時的回執；發布時程式
  一律重算，回執對不上原情境的會在頁上標明並只採用重算值。
- **方法目錄只有一處**：`calculations.CATALOG`（每個方法答什麼、必填參數、單位；估值類連函式），
  `METHODS` 由它導出。`calculations.run(method, params)` 按目錄執行，`calculations.TOOL`
  （名稱、描述、method enum）與 `run_tool({"method", "params"})` 是 MCP `calculate` 工具與兩個
  API adapter 共用的同一個工具；adapter 不 import service。加方法只加一列目錄（非估值類另在
  `run` 加一個分支）。不准另寫第二份算式或第二份名單。
- 首屏以依據與缺口幫助閱讀；沒有「已量度／未量度」格。只有合成／歷史重播的來源狀態提示，避免把舊包當即時分析。
- 目前沒有部位配置或百分之一風險預算。R&R 是條件價格下的算術，退出參考不是最大可保證損失，壓力情境另列。
- 本地 adapter 保留原始回傳和 `.meta.json`，再正規化成四份契約；未知時間、單位、缺頁不可補成已知。補查登記新來源版本後，用 `resolve_request` 產生新 packet，再重新產生對應的 research。
- SQLite、快取、事件訂閱、依賴路由、並行 worker、真實模型 context 隔離與允許清單留待接線及 KARST-242。當前私密欄位守衛只檢查部分 selector；它不能代替 adapter 的工具權限限制或原始回傳清理。
- 84 包考試原始目錄及抽取程式均未改。本測試集沒有重跑它，也不取代其回歸用途。

## 模組分工

| 模組 | 責任 |
|---|---|
| config、schema | 配置、身份／證券映射、版本化契約;憑證只讀環境,不寫入研究包 |
| fetch/ | **已實作(本地 adapter)**:按來源分 edgar、defeatbeta、longbridge、prices、broker,共用 `port.py` 的來源接口(`LandedRecord`、`fetch(security, out_dir, *, since, client)`、一次過的 ok／empty／error 判定、`pair_staging`);`common.py` 共用 meta 寫入(固定欄序、UTC Z、sha256)、時間轉換(帶偏移轉 Z、只有日期原樣、無偏移回 None)、限速、HTML 轉文本、代號→CIK。edgar 先查本地 submissions 與 10-K 快取(D-134)再上 EDGAR;prices 本地 parquet 接 DefeatBeta 並核重疊;broker 只落地公開市場方法的回傳,帳戶／持倉／下單鍵拒收。正規化成契約與快取／SQLite 仍待接 |
| manifest | 來源版本、原始內容 hash、解析衍生物及定位;同內容去重但保留來源關係 |
| store | **已實作**:SQLite schema、全文索引與持久狀態;單一提交者、交易與版本檢查(撞版本回衝突不覆寫);研究版本連它當時的 packet 與證據索引一起存;任務狀態轉換表只此一份。證據登記不在此,身份住 manifest |
| service、mcp_server | **已實作(W1)**:CLI／MCP／排程共用的操作函式與薄包裝;不呼叫模型,研究方法轉介 agents/protocol |
| packet | 建允許清單中的研究輸入包、必讀與缺口;不載入私人／模型帳本或開發上下文 |
| agents/ | 六角色任務、結構化輸出、有限補查、引用檢查;記實際模型與提示詞版本 |
| ta/、charts、structure | 關鍵區域、200 日 SMA、日週月、通道與突破回踩,確認時點不前視;`charts.py` **已實作**月／週／日／近期四張蠟燭 PNG(成交量、歷史均線曲線、有錨點的支撐阻力區)與衍生數字(均線方向、ATR、量比、形成／確認時點),不保存陣列;圖經 artifact 登記,`read_chart` 送真正圖像。`structure.py` **已實作**已確認 swing／BOS／CHoCH／前高低／等高等低／sweep 的事件層(見上) |
| calculations | **已實作**:五種估值方法分派、共用股權橋接、敏感度與反推,全部留同一份回執;有期限的目標價橋接仍由研究輸出提供 |
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


### 2026-09-19：雲端首次研究與讀回（0.2.3）

- 正常 `refresh_sources` 登記後建立可驗證 working packet，回 `research_input`；失敗回 `packet_error`，不假裝研究已保存。已保存版本的輸入不變。
- 新 `prepare_research(security, as_of?, evidence_ids?)` 可在補查入庫後明確建立選定快照；未知／重複 ID、截止後資料或身份不符會拒絕。`save_research` 沿用現有嚴格收件檢查。
- `get_research_context(subject, as_of_version=...)` 回該版完整 `research` 與 `calculation_receipt`；平常目錄查詢仍簡短。跨 subject 版本會拒絕。
- 更新保存會指回前次 research_id；逐層完整內容未變者保留原 assessed_at，有變者重新標時。目標日期不由程式自動延後。這不等於自動更新路由／排程已交付。
- EDGAR 正常取數會讀最新 SEC submissions，沒有本機快取亦可工作。明傳 submissions_dir 的重播／fixture 預設維持離線；可用 refresh_index 改設定。線上失敗有可用快取時明記錯誤和快取時間；兩者皆無則回來源錯誤。申報全文的抽取與 10-K 本地副本優先規則未改。
