# KARST-240：adapter 到六角色再到股票頁

本次核心版本 0.2.2；四份正本契約仍為 **0.2.0**，沒有新增或改寫契約欄位。角色片段的 `output.schema.json` 由既有 research／packet／evidence schema 動態產生，不另維護第二份研究契約。

本地負責真實來源與 Opus 執行。本套件不呼叫模型、不讀帳戶；首批及第二隻都換參數／bundle，不新增股票專屬程式。

## 1. 登記來源

```python
from pathlib import Path
from karst.fetch.registry import EvidenceRegistry
from karst.packet import build_packet
from karst.schema import canonical

bundle = Path(bundle_path)  # 由執行配置提供
registry = EvidenceRegistry(bundle)
record = registry.register(raw_path, meta_path, entity_ids=resolved_entity_ids)
# adapter 失敗而只落 meta：register(None, meta_path, entity_ids=...)
# raw/text 皆有：分別 register，明確傳同一 meta；兩者是不同 representation。

packet = build_packet(selected_records, as_of, security,
                      created_at=packet_created_at, root=bundle)
(bundle / 'evidence.json').write_bytes(canonical(selected_records))
(bundle / 'packet.json').write_bytes(canonical(packet))
```

`security` 沿用 packet schema 六欄。`selected_records` 是本次明確選定的適用來源與診斷，不是整本歷史 manifest；可包括產業、同業及市場來源。身份由接口／身份表提供，registry 不從代號猜 CIK，也不把全市場日曆硬掛一家公司。`entity_ids` 可在 meta 提供，函式參數優先。

meta 最少維持 fixture README 規矩 4。新 adapter 加 `status: ok|empty|error`、`source_url`；可加明確 `kind`、`entity_ids`、`source_id`、`media_type`、`data_as_of` 及時間精度／時區／依據。broker 工具仍須在 registry 的公開方法允許清單，不能靠填 kind 越過。新增公開方法須明確擴充表與測試。

| 輸入情況 | 登記規則 |
|---|---|
| raw + meta | 原始 bytes 入 objects；`file` hash／bytes 若有會核對 |
| `files.raw` 為 gzip | sidecar 的 hash／bytes 核解壓原文；artifact hash 核實際保存的壓縮檔 |
| `files.text` | 明記衍生方式及 truncated；不冒充未截全文 |
| 8-K 主文與 EX-99.1 | document／URL 各有來源身份，各一條；同 accession 不合併 |
| 逐字稿目錄 | filing_index；不能滿足 transcript requirement |
| date-only | 保留 YYYY-MM-DD、date 精度；時區未知維持 null，沒有假午夜 |
| 舊 meta 的非 EDGAR 日期 | 不當整個版本公開時間；逐字稿 call date 只留 coverage，其他適用日期保守作 data_as_of |
| 新 adapter 明確 `published_at_precision` | 依據要證明本版本可見性；與值矛盾或 datetime 無時區直接拒收 |
| 五種 period 形狀 | coverage 保留原描述；start/end 只收合法 ISO 日期，FY／季度／TTM／盤中狀態不推成日界 |
| empty/error（包括只落 meta） | manifest 保留診斷原件，packet 放 diagnostic_ids，不能引用為事實 |
| 同 bytes／不同供應商 | 可共用物件，但來源身份各自保留 |
| 重複取數 | fetched_at 變而內容／語義不變：沿用證據 ID，在 observations 追加取得紀錄；broker 外層取得時間亦不製造假更新，response 內供應商時間仍參與版本 |
| 同內容但時間／期間／口徑修正 | 新 source_version，supersedes 指向同來源上一版 |

物件位於 `evidence/objects/<sha256 前兩字>/<完整 sha256>.<ext>`。`evidence/manifest.jsonl` 是不可變證據版本事件；`evidence/observations.jsonl` 記本次取得時間、證據 ID、原始 sidecar 與 raw 物件參照。重跑相同 raw/meta 不追加重複事件。單一 writer 鎖、寫入 fsync 後原子換檔；遇到既有物件損壞或鎖佔用會報錯。程序意外退出留下 registry.lock 時，由操作員確認無 writer 後移除；不自動搶鎖。仍是單機檔案核心，SQLite／差異路由留步三。

`build_packet` 預設 requirements 包含 filing、transcript、financials、prices 及其他已提供種類。available 只表示所提供文本未截短，不保證是最新季度或必讀章節齊全，角色仍須核對。任何被選來源截短則該種 partial；沒有可用來源則 missing；診斷不生成證據 dependency。各證據 dependency 固定 source_version；額外的假設／方法依賴由參數傳入。截止後取得／公開資料不會被悄悄篩掉，會拒收，避免誤以為資料完整。

## 2. 每角色輸入與執行

`prepare_inputs` 輸出全新任務目錄，只複製允許的公開證據檔、input.json、prompt.md、output.schema.json；不複製既有 research.json 或其他鄰近檔。

```python
from karst.agents.inputs import prepare_inputs

context = prepare_inputs(
    role, packet, selected_records, bundle_root=bundle, destination=task_directory,
    allowed_evidence_ids=role_evidence_ids,
    mandate={'version': mandate_version, 'research_only': True, 'text': reviewed_mandate},
    discipline_sections=reviewed_sections,
    scenario_questions=reviewed_scenario_questions,
    upstream=required_fragments,
)
```

委託用現行已清理的研究版本；`research_only=true` 是本地已覆核的聲明，不是自動刪除自由文字中的私隱。`discipline_sections` 僅下表 layer 鍵；反方用 counter。輸入不得包含全倉／開發對話。**本地 runner 必須新建模型上下文，只掛載該 task 目錄，工具採公開市場允許清單；檔案複製與提示詞本身不是 OS sandbox。** 最新原始證據可按需讀完整，補查經本地取證角色。

| role／檔名 | 層 | payload | 上游 |
|---|---|---|---|
| industry.json | L1、L2 | phases | 無 |
| company.json | L3 | modules、phases | 無（先獨立读原文） |
| technical.json | L5 | technical、market、phases | 無 |
| valuation.json | L4 | valuation、target_date | industry、company |
| counter_initial.json | 無，反方第一步 | independent_view | 無，只讀證據 |
| counter.json | 無，反方第二步 | independent_view、strongest_counter、challenges | counter_initial、industry、company、valuation、technical |
| synthesis.json | L6 | coverage、rating、execution_state、headline、plan、open_questions、counter_response | industry、company、valuation、technical、counter |

六個角色；counter_initial 是同一反方角色先做的封存紀錄，不是第七個分析角色。前四個角色可先執行各自能獨立完成的部分，valuation 等 industry/company；反方先形成獨立看法，再審 L1–L5；synthesis 最後。每次 input_hashes 對應讀到的上游 JSON canonical SHA256。改動上游後，下游須重評，不能只更新 hash 裝作已讀。

每個角色回傳共同信封：contract_version、role、packet_id、read_evidence_ids、input_hashes、layers、payload、supplement_requests。允許的層與欄位由 output.schema.json 限制；不能把新的財務欄位塞進 layer。策略規格較細的必答內容寫入 conclusion／assumptions／gaps，保留引用。company 必須記錄讀過 packet 所供逐字稿。L1–L5 及估值／技術內容在 assemble 時保持原樣。

補查可先交 `requests.json`（格式見 common.md），不必等產出完整 layer。runner 呼叫既有 add_request／resolve_request 或 build_packet 建立新版本；新證據先登記，再重建 packet 的 requirements／dependencies。最後片段只能保留 packet 中已有的 pending 請求；如果已解決，就從片段待辦移除，解決歷史留 packet。v1 的新 packet 要重新產出匹配 packet_id 的片段，沒有自動跨版本沿用審核。

補查、局部重評、反方退回與沿用的後續規則見 [補查與增量重評路由 v1](../../strategy/specs/補查與增量重評路由-v1.md)。該文是設計，不表示目前已支援跨 packet 沿用。現在不能只重蓋片段的 packet_id、assessed_at 或上游雜湊來通過 assemble；派工原始輸入與模型原始輸出應封存。L6 若接受會推翻 L4 目標依據的挑戰，須退回 L4 修訂並重評下游，不能只清空 plan.target_price 而仍把未採納目標當首頁 KPI。

## 3. 合成及發布

run.json 只含 research_id、created_at、mode、strategy_version、mandate_version、method_version、models。models 六列，role 取上表六個最終角色，記实际 provider、model_id、prompt_version；counter 第一／二步的獨立呼叫時間、費用、推理配置與輸入雜湊另外寫在本地 run log。模型簡稱不代替實際版本。prompt_version 可用 prepare_inputs 回傳的 prompt_sha256，另存委託／紀律版本及 task input hash。

0.2 的 mode 尚沒有 live 枚舉：公開來源實際模型跑的保存／重播使用 offline_replay，在 run log 說明其為 live source capture + actual model run；integration_example 只用於手填整合示例；synthetic_demo 只用合成資料。這些是既有技術模式，不能用來暗示投資能力已驗證。

```bash
python -m karst.agents.assemble --bundle <BUNDLE> --fragments <FRAGMENTS> --run <RUN_JSON>
python -m karst.run --bundle <BUNDLE> --output <RELEASES>
```

assemble 先驗片段擁有權、版本／雜湊、引用、補查、反方及完整 research，再寫 research.json；若已存在則拒絕覆寫，另建 run bundle。綜合必須在 headline 和 L6 保留反方最強反證，counter_response 會附入 L6 conclusion。不得靠更換綜合判詞改掉估值或技術。CLI 不執行模型，不把模型請求文字當 shell/tool 指令。

原有 publish 仍負責重算、封存輸入及來源可追查的 HTML。六個片段、counter_initial、task inputs、run log 由本地保存，不能只留最终頁面；它們不是新增的 publication 契約欄位。actual tool/model run、第二家公司只換參數與本地畫面驗收由本地完成。

目前計算契約只支援 FCFF DCF；適用其他方法但程式尚未支援時，用 unavailable + gap_reason 說明，不能捏造 FCFF。非行號 locator 的語義及引文是否實際支持論據，需本地／研究覆核；程式只驗可登記來源、讀取紀錄與有效行號。

## 4. 驗證與本地合併門檻

```bash
python -m unittest discover -s karst/tests -v
```

涵蓋全 48 份 raw/meta：45 ok、2 empty、1 error；這是登記狀態，並非 45 份都可直接滿足分析。逐字稿目錄不算 transcript；這批全文樣本實際為 107/107 段、未超過截短門檻，另有合成案例驗 partial/missing。另測四個當前 adapter 的離線落地再入 registry、內容／期間／精度、雙重來源、metadata-only error、反方隔離、補查及從 build_packet → 六片段 → publish。

84 宗凍結回歸集不改。本次在 GitHub 可讀的 84 包重新核：日期越界／遮罩、8 行財務期間順序及訊號季對齊、申報參照結構與截止日期。完整原文引用及數字期間重新抽取依賴本地 EDGAR/companyfacts 快取（不在 GitHub）；仍須本地按凍結協議跑「越界／錯位／引用」三項，不把上述包內檢查宣稱為完整 84 宗回歸通過。
