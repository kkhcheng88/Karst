# Karst 詞彙表(CONTEXT.md)

> 只寫「它是什麼」,不寫實作。新詞誕生或舊詞收窄意思,當場落此表。英文名同時是程式裡的名。

| 中文 | English | 是什麼 |
|---|---|---|
| 因子 | factor | 可餵入策略的量化數值序列。一切信號的歸一形態——不論來源是結構化行情還是非結構化材料,入引擎前都是因子。 |
| 非結構化因子 | unstructured factor | 由非結構化材料(逐字稿、分析員報告、agent 研究)轉換而成的因子。轉換過程必須有清晰定義(2026-08-25 用戶明令「this unstructure factor need to form with a clear definition」)。 |
| 信號 | signal | 策略基於因子計算出的行動指示(買/不買/沽)。生產中系統出信號,用戶只揀執行與否,無其他要拍板的事。 |
| 策略 | strategy | 引擎的租戶:一套由因子到信號的規則,含自己的換倉節奏參數。「跟隨 SA」本身是一個策略,不是基準。 |
| 基準 | benchmark | 純對照尺,不是策略。例:QQQ 買入持有。 |
| 樽頸策略 | bottleneck strategy | 首個正式策略:供需故事(demand-supply story),承繼舊項目「主題→鏈位→敘事」框架,以非結構化因子為主要輸入,定義須比舊項目嚴格。 |
| 換倉節奏 | rebalance cadence | 策略參數,不是平台常數。揀節奏的原則是配合該策略的基本面擺動、防過擬合(依用戶 2026-08-25 語推出)。 |
| 紙上交易 | paper trading | 不落真金的持續運行,目的是隨時看到各策略的實際表現。 |
| 單一定義 | single definition | 每項定義(規則、名單、參數)全庫只有一個正本、無第二影像(2026-08-25 用戶明令「All database should have only 1 definition, no second image」)。 |
