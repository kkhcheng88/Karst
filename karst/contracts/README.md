# 四份契約 · 0.2.0（現行 0.4.0）

D-183 的現行程式正本是 `v0_2/*.schema.json`，使用 JSON Schema Draft 2020-12。Python 與本地 adapter 共用同一份定義；不要另抄一份欄位清單作第二正本。`v0_1/` 保留原樣，舊 bundle 仍可讀，schema hash 按實際版本記錄。此次按 PR #1 第二輪真實样本回饋擴充，完整真實 bundle 仍待本地驗收。

| 格式 | 正本 | 責任 |
|---|---|---|
| 證據登記 | evidence.schema.json | 一個來源版本：身份、公開／取得時間、所述期間、工具與公開參數、原始檔 hash、缺漏 |
| 取證包 | packet.schema.json | 一次研究可讀的精確證據 ID、截止時間、必讀來源狀態、補查、依賴版本 |
| 研究輸出 | research.schema.json | 已保存的六層判斷與引用、情境輸入、評級、相位、技術與條件計劃 |
| 發布包 | publication.schema.json | 固定輸入、計算器／頁面／契約版本、來源及輸出檔 hash、上版 ID |

共用的身份、時間、定位與資產定義在 evidence 的 `$defs`；研究內重複結構在 research 的 `$defs`。所有引用從內建 registry 解析，不去網絡下載 schema。完整時刻需带時區，adapter 建議統一 UTC；只有日期時保留日期，依下節精度規則處理。拒絕重複 JSON key、非有限數值、未知版本與未定義欄位。

## 0.3.0：單主研究路徑的必要變更

`v0_3/` 由 `v0_2/` 複製，只改下表列出的欄位，其餘四份契約一字不動；`v0_2/`、`v0_1/` 原樣保留，舊 bundle 與舊發布照讀照驗。同一 bundle 的 evidence、packet、research 仍必須同版，`karst/schema.py` 按每份物件自己的 `contract_version` 選對應目錄。

| 物件 | 0.2.0 | 0.3.0 | 為什麼 |
|---|---|---|---|
| research / publication | `mode` 三值：synthetic_demo、offline_replay、integration_example | 加 `interactive_research`、`api_research` | 分開「互動客戶端的真實研究」與「API 執行器的真實研究」；手填示例仍叫 integration_example，不冒充真實執行 |
| research | `models[]` 為六角色紀錄，`role` 是任意字串，可為空陣列 | `models[]` 是角色清單，每項 `{role: researcher｜reviewer, execution: interactive｜api, provider, model_id, prompt_version}`，至少一項 | 角色（責任）與執行方式（誰啟動維持）分開，長度不再固定六；角色與輸出不含固定供應商 |
| research | `technical.views` 必填，D／W／M 三個陣列必填 | `technical.views` 可省略，內含的 D／W／M 亦可逐個省略 | 本次取得的價格陣列是臨時輸入，只用來畫圖與量度，不隨研究永久保存 |
| research | 衍生數字散在計算結果，沒有保存位置 | 新增必填 `technical.derived`：`sma200`（不足 200 根為 null）、`bars_count` D／W／M、`data_as_of` | 沒有陣列時，頁與歷史版本仍答得出「用了多少 K 線、截至何時、SMA200 是多少」 |
| research | 沒有上版關係欄位 | 新增必填 `previous_research_id`（可為 null） | 單主研究由程式補上版關係；舊 0.2 沿用 publication 的 `previous_publication_id` |

其餘規則不變：引用仍要 `evidence_id` 加非空 `locator`，行號範圍照核；`derived.data_as_of` 與 K 線一樣不得晚於 packet cutoff；發布時傳入的臨時陣列同樣受 cutoff 檢查，**不能把較新的價格靜靜混進較舊的計劃**。0.3 發布只複製被引用（各層 `read_evidence_ids` 及所有引用）的原始 bytes，`evidence.json` 仍保留全部登記作索引；未複製原文的來源在頁上照列版本與 SHA256，但不給死連結。0.2 發布路徑照舊複製全部原始檔。

Renderer 升至 0.3.0、calculator 升至 0.2.0（行為已改：無陣列時不畫空圖、只在有陣列時計 SMA200／轉折）。同一份舊 bundle 重新發布會因此得到新的 publication ID，這是版本規則要求的結果，已發布目錄本身不受影響。

## 0.4.0：估值方法分派（KARST-247）

`v0_4/` 由 `v0_3/` 複製，**只改 research 的 `valuation` 一段**，evidence、packet、publication 三份除版本字串外一字不動；`v0_3/`、`v0_2/`、`v0_1/` 原樣保留，舊 bundle 與舊發布照讀照驗。`karst/schema.py` 仍按每份物件自己的 `contract_version` 選目錄；`agents.research.intake` 預設出 0.4，遇 0.3 的 packet 就按 0.3 收件（`SUPPORTED`）。

| 物件 | 0.3.0 | 0.4.0 | 為什麼 |
|---|---|---|---|
| research | `scenarios[].calculation` 固定是年度期末 `fcff_dcf` 一種形狀 | `$defs/calculation` 是帶 `method` 判別的 oneOf：`fcff_dcf`（**原意不變**）、`fcff_dcf_dated`、`forward_pe`、`ev_multiple`、`sotp` | 生意的經濟結構決定方法；把倍數或不規則時點塞進 `fcff_dcf` 只會令同一個欄位有兩種意思 |
| research | 無 | 每個 calculation 帶 `scale`（absolute／thousands／millions） | 尺度由輸入宣告；金額與股數同一尺度，每股值不因尺度改變，回傳金額一律絕對單位。0.3 沒有這個欄位＝absolute |
| research | 資本項散在 `cash`／`debt`／`other_claims` 三格 | `$defs/bridge`：現金、非經營資產、債務、少數股東、可贖回權益、`convertibles_dilution`（可為 null 但必須在 `unsupported_claims` 寫明缺口）、攤薄股數、`sbc_treatment{basis, note}` | 「其他索償」把少數股東、可轉債與贖回權壓成一格，看不出漏了哪一樣；SBC 要講明在哪一邊入帳才知道有沒有雙扣 |
| research | 無 | `forward_pe` 只有 `equity{diluted_shares, sbc_treatment}`，**schema 不容許它帶 bridge**；`ev_multiple` 反之 | 股權倍數的現金與債務已在盈利與股數之內，再加企業橋接就是雙計；兩邊各自宣告 `multiple_basis` |
| research | 無 | `scenarios[].drivers[]`：名稱、期間、單位、值、`input_path`、引用 | 經營假設要指得出它餵哪一個計算輸入，改一項才追得到每股結果 |
| research | `alternative_view` 是 statement | statement ＋ 可為 null 的 `calculation` | 替代視角可以真的算一次，不只是一句話 |
| research | 無 | `sensitivities[]`（情境、改哪些 `input_path`、回執）與 `implied`（情境、目標價、求解變數、邊界、固定假設、`outcome`、值、回執），兩者皆可為空／null | 敏感度與反推要對得到它所屬的情境；`status != calculated` 時兩格必須是空與 null |

回執欄 `receipt{calculator_version, method, inputs_digest, outputs}` 存的是模型當時呼叫計算工具所得。**發布時程式一律重算**，並比對 `inputs_digest` 與每股值；對不上的在頁上標明並只採用重算值。`packet.check_research` 另外擋「敏感度或反推指向一個沒有 calculation 的情境」。

Renderer 升至 0.4.0（估值段按方法分別展示計算依據、driver、敏感度表與反推）、calculator 升至 0.3.0（方法分派、尺度、敏感度與反推）。舊 bundle 重新發布因此得到新的 publication ID；已發布目錄不受影響，`verify_release` 結果不變。0.2／0.3 的 `fcff_dcf` 算式與數值一字未改——五個既有發布用新計算器重算，每股值與原紀錄完全相同。

## 0.2 接線與迁移

同一 bundle 的 evidence、packet、research 必須同版；publication 沿用該版本，不以新版 schema 冒充舊發布。0.1 讀取沒有自動補欄。升到 0.2 要另存 bundle，新增以下欄位並重評其實際含義：

| 物件 | 新欄位／取值 | 接口責任 |
|---|---|---|
| evidence | `coverage: object|null` | 原樣保留來源的期間／涵蓋描述；正規化區間仍放 `period` |
| evidence | `published_at_precision`、`data_as_of_precision` | `datetime` / `date` / `unknown`，分別配帶時區時刻、純日期、null |
| evidence | `published_at_timezone`、`data_as_of_timezone` | 純日期已知的 IANA 時區；未知為 null。完整時刻已帶偏移時亦填 null |
| evidence | `data_as_of_basis` | 資料截至時點的依据；未知需明講，不能拿 fetched_at 代替 |
| evidence | `status`、`status_reason` | `ok` / `empty` / `error`；後兩種必填非空原因，原始回傳照存 |
| packet | `diagnostic_ids: []` | 選入發布的空回傳／失敗登記 ID；與可引用的 evidence_ids 分開 |
| research / publication | `mode: integration_example` | 真實資料配手填測試判斷的接線示例，頁面不冒充正式模型研究 |

`period` 仍只含 `start`、`end`（date 或 null）。單一 **reportDate** 可存兩端相同日期，但不能因此聲稱它是整季的開始。財年季度缺已核會計日曆、TTM 缺期間、未完窗口或多組異質序列時，可以保持 null；不能從電話會日期反推財季。

多期報表的最早／最晚期末只可作涵蓋端點索引，不表示完整期間或中間每季有值；`coverage` 保留所有期末、TTM 標記、缺列等來源描述。盤中快照保留 session_date/state；只有 `as_of: fetch time`、無來源時點的資料，不能把取得日宣稱成資料日。未來事件日曆與預測期間可超過 cutoff，其公布／取得版本須在 cutoff 內。

只有日期時，**直接存 `YYYY-MM-DD`，不存假造的 `T00:00:00Z`**。機器用日期的可能時間區間做檢查，不把區間邊界回寫為公開時刻：

- 日常 `system_observed`：實際已在 cutoff 前取得，而且日期不是確定在未來，即可使用；精度仍保留為 date／unknown。
- 歷史 `public_as_of_replay`：若截止前已實際取得，可使用該觀測；否則 date 必須整個可能區間都在 cutoff 前。同日盤前／盤中不能靠稿頭日期過關。
- 已知 IANA 時區時，按該地日期起訖（含夏令時間）判斷；未知時區時，保守涵蓋 UTC 偏移 ±14 小時。這不是假設原文屬 UTC。`tzdata` 隨安裝提供 Windows 的時區資料。
- `published_at=null` 不可作歷史公開可用的證明。逐字稿只有 call/report_date 時，該日期留在 coverage，published_at 仍應為 null，直到有文字版本可取得的證據。EDGAR 受理時刻能支持该申報版本已公開，不能自動聲稱是更早的新聞稿首發。
- 未帶時區的日期加時刻不可自行加 `Z`。保留原始回傳及 meta；確認時區後才能正規化，否則 published_at 為 null 並交代 basis。日期精度、來源日期的含義、版本的歷史真實性仍需接口核查，schema 不會替它猜。
- 券商「現時快照」的 update_time 不自動證明同一份內容在過去已可取得。若無歷史版本依據，published_at 應保持 unknown；有依據的更新日可記在 data_as_of，原時間描述保留在來源。不能僅因日期格式合法就讓現時共識通過歷史重播。

來源 ID 維持原識別字規則，描述名稱留在 `source`／原始 meta。`entity_ids` 由接口以已核映射補齊；全市場日曆用 `market:US` 等實體，不可把不在清單裡的公司硬掛上去。新增 kind：`ownership`、`short_interest`、`calendar`、`profile`、`valuation`、`filing_index`；不要把估值、持股與申報清單都塞進 financials。

`error`／`empty` 登記仍有原文 hash、取得時間和本來要抓的 kind，放 packet.diagnostic_ids 後會隨發布保留。它們不能作 statement 引用、read_evidence_ids、available/partial requirement 或 fulfilled supplement；拿不到的必讀來源仍標 missing。空表只證明這次查詢回空，不能推出沒有持股、沒有收入或沒有更新。歷史包也不能帶入 cutoff 後才發生的失敗紀錄。

原始 JSON 檔若含 NaN，照 bytes 保留供追溯，但正規化的契約仍拒絕 NaN。adapter 需按來源意義把缺值轉成 null 並記轉換，不可改成零。樣本中的 `*`、空字串、哨兵日期、三家不同 PE 與盤中狀態亦須保留原口徑；本版沒有替它們建立共同數值真值。

## 原始檔、時點與缺漏

輸入 bundle 必須有 `evidence.json`（登記陣列）、`packet.json`、`research.json` 及登記所指的檔案。`artifact.path` 是乾淨的相對路徑，不能越出 bundle；不可使用 packet/research/evidence JSON 檔名作來源路徑。hash 對**原始 bytes**計算，UTF-8 文本換行亦算內容。

`evidence_id` 固定一版內容；更新要給新 ID，用 `supersedes` 指前版。`source_id` 連結同一來源，`source_version` 由 adapter 提供不可變版本，不能填會隨日變動的「latest」。主體以 `issuer_id`／`security_id` 區分公司與上市證券；ticker 只作顯示／查詢參數。

- `published_at` 是**這個版本**公開的時間，不能把事後修訂掛回原報告日期。未知可為 null，但必須解釋 `published_at_basis`。
- `fetched_at` 是本系統實際取得時間；`data_as_of` 是來源聲稱的資訊時點；`period` 是資料描述的會計／預測期間。預測可談未來期間，不能用未來公布的資料。
- `system_observed` 要求取得時間不晚於 cutoff，公開／資料時點不得確定在 cutoff 後；date／unknown 按上節規則保留不確定性。
- `public_as_of_replay` 允許今天取得的已知歷史版本，公開精度與可能區間按上節檢查。這不證明供應商提供了真正的歷史版本。
- requirement 的 `available` 不接受截短文件；`partial` 保留可讀部分與缺口；`missing` 或 `not_applicable` 要明講原因。逐字稿狀態不可省略；有逐字稿時第三層必須登記讀過的 ID。讀取紀錄本身並非讀懂的證明。
- 公開 market selector 可以留；帳戶、持倉、成本、盈虧與憑證不得進包。程式只防部分已知欄位；本地 adapter 仍需在來源與上下文邊界執行允許清單、清理原文。

## 補查是核心的一部分

```python
from karst.packet import add_request, resolve_request, check_packet

# request 的完整欄位見 packet schema。
pending = add_request(packet, request)
# adapter 先抓取並登記來源；此核心不執行網絡請求。
revised = resolve_request(
    pending, request["request_id"], new_evidence_ids,
    resolution="已取得補充來源", created_at=created_at, as_of=new_cutoff,
)
check_packet(revised, registered_records, bundle_root)
```

兩個操作都回傳新物件及新 packet ID，原 packet 不變。既有來源也可用來解決補查，但必須已登記。拿不到用 `unavailable=True`、空 evidence IDs 和原因；不能假裝 fulfilled。當日研究可前移 cutoff，歷史重播則保持原 cutoff，後知資訊會被拒絕。呼叫方负责將各版 packet 落檔；這裡尚未提供持久任務隊列。

research 必須引用補查完成後的精確 packet ID，不能拿上一包的判斷冒充新包完成。未解的補查／更新、缺漏 requirement 與 `coverage=complete` 不相容。每個 statement 可引用多份證據，也可無引用地提出假設；`L12-L18` 定位會檢查實際 UTF-8 行數，其他 PDF 頁／JSON 定位目前只保存文字，尚未驗證其語義或位置。

## 計算、技術與輸出模式

`research.mode` 支援 `synthetic_demo`、`integration_example` 和 `offline_replay`；前兩者分別是合成資料與真實資料接線示例。後者代表傳入已保存的研究，實際 provider/model/prompt 由 `models` 留存。真實即時執行記錄及模式在 KARST-240 與本地一起接入，不能先填假的模型執行紀錄。

FCFF DCF 的 cashflows 是自 valuation_date 起每個**完整年度年末**的企業自由現金流，以同一幣別的絕對金額輸入；不是已折現值、不是 equity cashflow、不是「百萬」而未乘單位。股數為絕對攤薄股數；cash 及各種索償為同一估值日金額。年中折現、短首期、多幣別與不同會計模型不在這版。折現率須高於永續增長，終年 FCFF 須可正值正常化；不能以永續模型掩蓋缺少可終值的生意。**0.4 起**：期中折現、首期 stub、前瞻 P/E、EV 倍數與 SOTP 各有自己的 method（見上節），`fcff_dcf` 的意義不變；多幣別仍不在這版。

三情境分別計算，沒有先驗勝率；基準內在價值不是上下界平均。`target_prices` 是到 `target_date` 的獨立價格假設，需要解釋估值到市場定價的橋接。`plan.target_price` 是該計劃採用的退出目標，未必等於基準估值；必須在 execution_rule 解釋。R&R 按每股成本、預期分派、條件入場與退出價計算，沒有風險預算或私人淨值。

日／週／月 bars 各自由 adapter 提供有序、口徑一致的資料；`at` 指已知該 bar 狀態的時間，`complete` 表示已收定。核心不擅自推斷交易所日曆、週月收盤或復權。`quote_to_bar_factor` 明示報價與 K 線口徑的換算；raw 必須為 1。SMA200 需 200 根已收定日線；局部轉折需左右各兩根已收定 K 線，確認時間記在右邊第二根。支撐阻力區域、通道、突破回測與相位判斷仍由研究輸入，不宣稱能由價格證明機構行為。

## 發布與演進

發布把選定的來源 bytes、輸入、計算與 HTML 放在同一目錄。publication ID 由正規化輸入、schema hash、renderer/calculator 版本及上版 ID 計算；同輸入重跑不覆寫。新目標或假設產生新版，當時 target 與引用可保留。

Renderer 0.2.1 起，股票頁的來源區只呈現登記欄位、hash、路徑、大小及連結，不內嵌原始檔全文。`provenance` 決定「公開市場來源／合成資料來源」，有沒有外部 URL 不改變來源性質。下載連結以相對路徑指向發布包 `inputs/` 的原始檔；來源網站 URL 有則另列。文字欄位仍做 HTML 跳脫，本頁不執行原始檔中的 HTML。移動或分享時保留整個發布目錄，才能繼續開啟相對連結。此修訂沒有改 0.2.0 契約或來源 bytes。

此步使用本地單一發布者、排他 lock、同檔案系統暫存目錄再 rename。一般例外會清理；進程被強制終止可能留下 lock／staging，須確認沒有程序後手動清理。這不是分散式交易或防惡意篡改的簽章，manifest 不對自身簽名；不保證斷電 durability。沒有自動 latest 別名，避免另加跨檔案狀態交易。

契約與程式需一同升版；已發布版本不能靜默改含義。修改 renderer/calculator 行為亦必須升其版本，否則同輸入仍指向旧發布。未有真實樣本支持前保留 0.x 狀態；擴充金融模型或資料口徑應附對應 fixture 及遷移說明。SQLite／事件依賴表在步三加入，沿用 ID、版本與發布內容，不需要丟掉這批來源與研究。
