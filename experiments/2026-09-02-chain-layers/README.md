# 鏈層第一版人手表(承接舊倉 KarstETF)

2026-09-02 由主 agent 自舊倉 `C:\projects\Investment\KarstETF\bt\exp9_full_reader\chain_membership.csv` 原檔複製,未改一字(檔首含 UTF-8 BOM,讀取時用 `encoding="utf-8-sig"`)。

## 這張表是什麼

- 舊倉 KarstETF(2026-08-15 停案)用「主題 / 鏈位 / 敘事」三層模型挑選代表公司;`theme` 欄即鏈位,33 條;`valid_to` 空白者為現役,共 98 個唯一代碼。
- 依舊倉 ADR-0039 分四類:16 條可投注鏈位(42 個代表席位)、10 條純需求型不落注、2 條退役、2 條永久剔除、1 條被部分取代(energy→upstream_oil)、1 條待裁(smr_newbuild)。
- 歸層機制:LLM 讀業務描述與分部收入做窮盡分類並附引文核對,再由分析員依四步規則(純度閘→方向測試→代表性測試→市值排序)定代表,鎖死名單。
- **同層對同一消息反應相似**這一條,舊倉只有質性「方向測試」,**從未做過統計量度**(僅一個退役個案引用過相關係數)。所以這張表是「鏈層」(CONTEXT.md)的**候選人手表**,不是已驗證的分層。

## 在 Karst 的用途

- 用戶 2026-09-02 定義:價值鏈=產業鏈,鏈分「鏈層」,同層=同位置、同故事、消息衝擊相似(D-129)。
- 本表作為鏈層第一版,供 KARST-149/151 提出量法時當作待驗證的標籤;驗證方向=同層公司事件日回報相關性是否顯著高於同 GICS 子行業但不同層的公司。
- 多數鏈位本身即一層(不再分上下游);石油鏈例外,舊倉列出 7 個潛在子層但只覆蓋上游開採與油田服務兩層。

## 出處檔(舊倉,唯讀)

- `docs\adr\0024-three-layer-model-theme-layer-narrative.md`
- `docs\adr\0031-classification-mechanism-and-industry-map.md`
- `docs\adr\0039-representative-rule-and-layer-freeze.md`(最終鎖死版)
- `bt\exp9_full_reader\chain_membership.csv`(唯一真源)
