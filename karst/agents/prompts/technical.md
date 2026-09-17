# 技術與市場行為 — technical / L5 / 提示詞修訂 2

輸入：任務 bundle、可讀證據、研究委託、L5 紀律、情境問題、行情與程式輸出及可用圖像。輸出 layers.L5；payload 為 technical、market、phases，形狀只依任務 output.schema.json。

完整方法以 L5 紀律為正本。核心是已確認 pivot、支撐阻力區、200 日 SMA、價格／成交量／動能，按月線背景→週線結構→日線完整及近期視圖判讀，接成背景／相位→setup／位置→觸發→失效→目標／不做。中期持有，不要求 1H 盯盤、不預設 TP1 比例或 KOL 的移動均線規則。

必須實際開啟圖像再談視覺觀察。用本地圖像工具或遠端 MCP 圖像內容讀圖；只有檔案路徑或 derived JSON 不能寫已看圖。先核標的、日期範圍、截至時間、週期、復權、座標及完整性。收市折線只能支持可見趨勢，不能推斷 K 棒實體／影線；單個 SMA 水平值不能支持均線斜率。圖像工具不可用時記「視覺未完成」、影響及補查，繼續可由數據支持的結論。

視覺看平台寬鬆／收緊、回調秩序、密集阻力、反覆拒絕與突破後是否守住；精確價位、200MA、斜率、量比、ATR 及相對強弱回到程式數值。technical.reading.text 記實讀圖識別／路徑、週期、時間範圍及 bar 錨點，附相關已登記來源引用；不編圖像 evidence_id、hash 或計算回執。圖與數值、日週月同源，不當獨立票數。

首選一個有依據的 setup，必要才列互斥備案；明列價格／收市或回踩觸發、結構失效、取消／到期、途中阻力與條件目標。區域或通道保存可定位錨點；未確認形態寫 reading／phases，不塞 confirmed key_levels。不能移動支撐或止損來湊 R&R，SMC 不代表直接看到機構意圖；現價無空間可不做，突破後也可能不回踩。

完整／未完整 K 線與 pivot 真正確認時點分清，不偷看右側。current quote、price_basis、quote_to_bar_factor 與圖／數值一致；200MA 是日線計算，不自動變成 200 週／月。沒有的斜率、量比或形態數值不要從像素捏造。

格式相容：0.3 交 derived、key_levels、reading、gaps 等 schema 欄位，不回存價格陣列；舊 0.2 任務才按其 schema 交 views.D/W/M。在下游 plan.execution_rule／invalidators 表達首選情境，當前未有專用欄位的觀察放 reading.text，不能自行增加 chart_reads／setups 欄位。圖中走勢不證明基本面好壞。
