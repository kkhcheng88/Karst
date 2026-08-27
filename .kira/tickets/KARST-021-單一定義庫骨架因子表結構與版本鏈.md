---
id: KARST-021
title: 單一定義庫骨架:因子表結構與版本鏈
type: task
createdAt: 2026-08-27
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
closed: 2026-08-27
---

## 工作內容

因子(factor)自此有一個正式落腳處:寫得入一個因子定義,查得回任何一個日期 × 股票的值,而且一切查詢以知情時間(knowledge time)為閘,不會用到當日還未知道的資訊。範圍只是這張表的形態與存取——日期 × 股票 → 一個數值,每個值帶事件時間與知情時間雙時間戳,每個因子登記時自報刻度型(scale kind)與產生程序,定義一經落庫不可改、只可出新版並記父版本。缺失值當「該股該日不參與該因子的篩選與排名」,不填補、不當零(D-021 第 4 條)。依 D-021 第 1 至 9 條;本票不做因子計算,亦不做寫入通道的治理(那是唯一入口)。

## 驗收條件

- [x] 寫得入一個因子定義並讀得回:任一「日期 × 股票」的值查得出,且值帶事件時間與知情時間兩個時間戳(D-021 第 1、3 條)
- [x] 同一因子出第二版時舊版內容一字不變,新版記得住父版本,由任一版本追得回上一版(D-021 第 9 條)
- [x] 缺失值的查詢結果是「不參與」而非 0,調用方分辨得到「不參與」與「值真的是零」兩種情況(D-021 第 4 條)
- [x] 因子登記時缺刻度型(基數/序數/是非)或缺產生程序(公式+輸入數據版本,或材料+判官版本)即寫不入(D-021 第 2、6 條)

## 結果

· 2026-08-27 23:29 起了本倉第一個 Python 套件骨架,單一定義庫可用。

**做了什麼**

一個 sqlite 檔裝住全庫正本定義,分四組表:實體(`entity`,上市公司以 CIK 為錨、ETF 與籃子另編內部代碼)與代號歷史映射(`entity_ticker`,代號有生效起訖、同一代號日子不准重疊);因子定義(`factor`,名稱「族名·具體定義」全庫唯一)與版本鏈(`factor_version`,每版記刻度型、產生程序、父版本);因子值(`factor_value`,日期 × 實體 → 一個數值,帶事件時間與知情時間,缺失=沒有那一列);數據快照登記(`data_snapshot`,編號=日期+內容雜湊前 12 位)。

不可改是資料庫層擋的,不是靠自律:因子定義、因子值、快照三張表的 UPDATE 與 DELETE 由 sqlite trigger 一律拒收,要改只可出新版。寫入時另有三道合約閘——缺刻度型、缺產生程序任何一格、知情時間早於事件時間(前視)、值是 NaN 或 ±inf,全部當場拒收。

Python API 一層過(`karst.DefinitionStore`):`register_entity` / `register_ticker` / `resolve_ticker`(按日期解析代號)/ `register_factor` / `new_factor_version`(父版本自動接上當前最新版)/ `factor_version_chain` / `write_factor_values` / `read_factor_values`(可按知情時間截止)/ `latest_known_values` / `value_for` / `register_snapshot`;另有 `freeze_batch` 把一批數據寫成 parquet 再登記快照,接上 D-026 的「數據住 parquet、定義住 sqlite」。

缺失值以一個唯一標記 `NOT_APPLICABLE` 回覆,而且它刻意不可當真假值使用(`if value:` 會即場拋錯),逼調用方寫明 `value is NOT_APPLICABLE`——0.0 與「不參與」在真假判斷裡混為一談,正是這條驗收條件要防的事。

**檔案路徑**

- `pyproject.toml`(Python 3.11+,依賴只有 pandas 與 pyarrow)
- `karst/__init__.py`、`karst/store.py`(API)、`karst/schema.py`(表結構與 trigger)、`karst/models.py`(值型別、時間戳規範化、缺失標記)、`karst/errors.py`、`karst/batches.py`(parquet 批次凍結)
- `tests/test_definition_store.py`

**測試命令與結果**

於倉根跑 `PYTHONUTF8=1 python -m pytest tests -q` — 6 passed。四項驗收條件各一個測試,另加代號按日期解析(GOLD 代號回收情境)與快照登記兩個。另在倉外做過一次落檔重開的煙霧測試:關庫再開,代號、因子值、知情時間閘全部照舊。

**逐項驗收**

1. 寫得入讀得回、雙時間戳:`test_value_round_trips_with_both_timestamps` — 值寫入後讀得回,事件時間 8-25、知情時間 8-27 13:30 兩個都在;以 8-26 為知情截止查同一個值,結果是空——當日還未知道。
2. 第二版不改舊版、父版可追:`test_second_version_keeps_first_intact_and_records_parent` — 出第二版後重讀第一版與原物件完全相同,第二版的父版本指住第一版,版本鏈追回 [2, 1];直接改庫改舊版會被 trigger 擋。
3. 缺失=不參與而非 0:`test_missing_value_is_not_applicable_not_zero` — 一隻股票的值真的是 0.0、另一隻沒有值,兩者分辨得到;沒有值的那隻根本不在結果列內。
4. 缺刻度型或缺產生程序即寫不入:`test_registration_rejects_missing_scale_kind_or_procedure` — 四種缺件(缺刻度型、缺產生程序、公式派缺輸入數據版本、數值派缺判官版本)全部拒收,拒收後庫裡一個因子都沒有。

**一個要留意的取態**

D-026 第 2 條的「以 CIK 為錨」,這裡做成:實體編號是內部流水號,CIK 是它的唯一錨與去重鍵(同一 CIK 重複登記回同一個編號),而不是把 CIK 本身當編號。理由是 ETF 與籃子沒有 CIK,兩套編號同住一張表才不會撞。日後若要編號本身等於 CIK,現階段庫是空的,改動成本仍然很低。

## 留言
