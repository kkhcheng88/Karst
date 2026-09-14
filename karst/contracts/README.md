# 四份契約 · 0.1.0

D-183 的程式正本是 `v0_1/*.schema.json`，使用 JSON Schema Draft 2020-12。Python 與本地 adapter 共用同一份定義；不要另抄一份欄位清單作第二正本。此版先供離線整合，真實样本映射仍待本地驗收。

| 格式 | 正本 | 責任 |
|---|---|---|
| 證據登記 | evidence.schema.json | 一個來源版本：身份、公開／取得時間、所述期間、工具與公開參數、原始檔 hash、缺漏 |
| 取證包 | packet.schema.json | 一次研究可讀的精確證據 ID、截止時間、必讀來源狀態、補查、依賴版本 |
| 研究輸出 | research.schema.json | 已保存的六層判斷與引用、情境輸入、評級、相位、技術與條件計劃 |
| 發布包 | publication.schema.json | 固定輸入、計算器／頁面／契約版本、來源及輸出檔 hash、上版 ID |

共用的身份、時間、定位與資產定義在 evidence 的 `$defs`；研究內重複結構在 research 的 `$defs`。所有引用從內建 registry 解析，不去網絡下載 schema。所有時間需帶時區，adapter 建議統一 UTC。拒絕重複 JSON key、非有限數值、未知版本與未定義欄位。

## 原始檔、時點與缺漏

輸入 bundle 必須有 `evidence.json`（登記陣列）、`packet.json`、`research.json` 及登記所指的檔案。`artifact.path` 是乾淨的相對路徑，不能越出 bundle；不可使用 packet/research/evidence JSON 檔名作來源路徑。hash 對**原始 bytes**計算，UTF-8 文本換行亦算內容。

`evidence_id` 固定一版內容；更新要給新 ID，用 `supersedes` 指前版。`source_id` 連結同一來源，`source_version` 由 adapter 提供不可變版本，不能填會隨日變動的「latest」。主體以 `issuer_id`／`security_id` 區分公司與上市證券；ticker 只作顯示／查詢參數。

- `published_at` 是**這個版本**公開的時間，不能把事後修訂掛回原報告日期。未知可為 null，但必須解釋 `published_at_basis`。
- `fetched_at` 是本系統實際取得時間；`data_as_of` 是來源聲稱的資訊時點；`period` 是資料描述的會計／預測期間。預測可談未來期間，不能用未來公布的資料。
- `system_observed` 要求公開／資料／取得時間都不晚於 cutoff；未知公開時間仍可按實際取得時間留存，但不能宣稱具備歷史公開時間證明。
- `public_as_of_replay` 允許今天取得的已知歷史版本，但該版本公開時間必須已知且不晚於 cutoff。這只驗查登記時間，不證明供應商提供了真正的歷史版本。
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

`research.mode` 暫限 `synthetic_demo` 和 `offline_replay`。後者代表傳入已保存的模型研究，不代表使用了弱模型；實際 provider/model/prompt 由 `models` 留存。真實即時執行記錄及模式在 KARST-240 與本地一起接入，不能先填假的模型執行紀錄。

FCFF DCF 的 cashflows 是自 valuation_date 起每個**完整年度年末**的企業自由現金流，以同一幣別的絕對金額輸入；不是已折現值、不是 equity cashflow、不是「百萬」而未乘單位。股數為絕對攤薄股數；cash 及各種索償為同一估值日金額。年中折現、短首期、多幣別與不同會計模型不在這版。折現率須高於永續增長，終年 FCFF 須可正值正常化；不能以永續模型掩蓋缺少可終值的生意。

三情境分別計算，沒有先驗勝率；基準內在價值不是上下界平均。`target_prices` 是到 `target_date` 的獨立價格假設，需要解釋估值到市場定價的橋接。`plan.target_price` 是該計劃採用的退出目標，未必等於基準估值；必須在 execution_rule 解釋。R&R 按每股成本、預期分派、條件入場與退出價計算，沒有風險預算或私人淨值。

日／週／月 bars 各自由 adapter 提供有序、口徑一致的資料；`at` 指已知該 bar 狀態的時間，`complete` 表示已收定。核心不擅自推斷交易所日曆、週月收盤或復權。`quote_to_bar_factor` 明示報價與 K 線口徑的換算；raw 必須為 1。SMA200 需 200 根已收定日線；局部轉折需左右各兩根已收定 K 線，確認時間記在右邊第二根。支撐阻力區域、通道、突破回測與相位判斷仍由研究輸入，不宣稱能由價格證明機構行為。

## 發布與演進

發布把選定的來源 bytes、輸入、計算與 HTML 放在同一目錄。publication ID 由正規化輸入、schema hash、renderer/calculator 版本及上版 ID 計算；同輸入重跑不覆寫。新目標或假設產生新版，當時 target 與引用可保留。公開頁面只把來源當 escaped text，不執行報告或模型輸入中的 HTML。

此步使用本地單一發布者、排他 lock、同檔案系統暫存目錄再 rename。一般例外會清理；進程被強制終止可能留下 lock／staging，須確認沒有程序後手動清理。這不是分散式交易或防惡意篡改的簽章，manifest 不對自身簽名；不保證斷電 durability。沒有自動 latest 別名，避免另加跨檔案狀態交易。

契約與程式需一同升版；已發布版本不能靜默改含義。修改 renderer/calculator 行為亦必須升其版本，否則同輸入仍指向旧發布。未有真實樣本支持前保留 0.x 狀態；擴充金融模型或資料口徑應附對應 fixture 及遷移說明。SQLite／事件依賴表在步三加入，沿用 ID、版本與發布內容，不需要丟掉這批來源與研究。
