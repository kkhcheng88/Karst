# 樣本索引(KARST-241 步一;首批股票 AXTI / AXT Inc / CIK 0001051627;抓取日 2026-09-14 UTC 18:26–18:57,即香港時間 2026-09-15 凌晨)

每份資料檔旁有同名 `.meta.json`(source / tool / params / fetched_at / published_at 與依據 / period / truncated / known_gaps),本表只是速覽;細節以 meta 為準。**所有抓取腳本都在倉外 scratchpad,倉內只有資料與 meta。** 富途與 Longbridge 的 MCP 回傳由代理人由工具輸出逐字轉錄成檔(MCP 沒有直接寫檔的路徑);兩份超長回傳(富途業績日價格史、Longbridge 事實清單)是由系統保存的原始輸出檔逐位元複製,meta 記有原文 sha256。

## edgar/(7 份;1 份本地索引切片 + 6 份線上申報,每份申報同時留原始 HTML 與衍生純文本)

| 路徑 | 來源 / 工具 | 期間 | 取得時間 (UTC) | 截短 | 已知缺漏 |
|---|---|---|---|---|---|
| `edgar/CIK0001051627.submissions_slice.json` | 本地 `data/sec/submissions/CIK0001051627.json` | 最近 40 筆申報 2026-05-06 至 2026-08-19(本地 1,000 筆之中) | 18:26:44 | 是(40/1,000) | 非 8-K 的 items 為空字串;部分 reportDate 空白;本地快照可能落後 EDGAR 數日;**EDGAR 索引指有 1 個分頁檔(1998–2000 年 36 筆)本地沒有**,meta 記 found_locally=false |
| `edgar/0001437749-26-008612.10-K.{raw.htm.gz,txt}` | EDGAR 線上(本地 10-K 快取 manifest 查無此 CIK,改線上抓) | 年度 2025-12-31;受理 2026-04-24 | 18:26:44 | 文本截前 60,000 字元(原長 514,782);原始 HTML 3.2 MB 完整,以 gzip 存 | 純文本開頭含 inline XBRL 隱藏標頭值(未清);本地 10k_text 無此公司 |
| `edgar/0001437749-26-027677.10-Q.{raw.htm.gz,txt}` | EDGAR 線上 | 季度 2026-06-30;受理 2026-08-13T20:16:33Z | 18:26:44 | 文本截前 60,000 字元(原長 378,737);原始 HTML 2.2 MB 完整 gzip | — |
| `edgar/0001437749-26-025061.8-K.{raw.htm,txt}` | EDGAR 線上(主文件;Item 2.02, 9.01) | 事件日 2026-07-30;受理 2026-07-30T20:15:25Z | 18:26:45 | 否(4,086 字元) | 受理時間不等於稿件首發時間(§四 4);附件清單(含 XBRL)記在 meta |
| `edgar/0001437749-26-025061.8-K.EX-99.1.{raw.htm,txt}` | EDGAR 線上(附件 ex_974537.htm,由 index 頁找到) | 2026 年第二季業績稿,稿頭日期 2026-07-30 | 18:26:45 | 否(14,815 字元) | 稿頭只有日期,無時刻 |
| `edgar/0001437749-26-014204.8-K.{raw.htm,txt}` | EDGAR 線上(主文件;Item 2.02, 9.01) | 事件日 2026-04-30;受理 2026-04-30 | 18:26:46 | 否(4,095 字元) | 同上 |
| `edgar/0001437749-26-014204.8-K.EX-99.1.{raw.htm,txt}` | EDGAR 線上(附件) | 2026 年第一季業績稿,稿頭日期 2026-04-30 | 18:26:46 | 否(15,506 字元) | 同上 |

## defeatbeta/(10 份;`defeatbeta-api` 0.0.60,遠端資料集更新時間 2026-09-14T05:09:09Z)

| 路徑 | 工具 | 期間 | 取得時間 (UTC) | 截短 | 已知缺漏 |
|---|---|---|---|---|---|
| `defeatbeta/earning_call_transcripts.list.json` | `Ticker.earning_call_transcripts().get_transcripts_list()` | 61 場,2007Q4(2008-02-27)至 2026Q2(2026-07-30) | 18:30:02 | 否 | 季度不連續(來源本身缺);只有 report_date,無文字版可取得時刻 |
| `defeatbeta/earning_call_transcript.FY2026Q2.json` | `get_transcript(2026, 2)` | 2026Q2 電話會 2026-07-30;107 段、38,043 字元 | 18:30:02 | 否(上限 40,000 未觸及) | 來源無「準備發言 / 問答」分段標記,只有段號、講者、內容;講者無職銜 |
| `defeatbeta/quarterly_income_statement.json` | `Ticker.quarterly_income_statement().data` | 期末 2022-06-30 至 2026-06-30 共 17 季 + TTM;45 行 | 18:30:03 | 否 | 缺值以 `"*"` 字串表示(照原樣);2022-09-30、2022-12-31、2023-03-31 三季整欄 `*`;表內無幣別單位 |
| `defeatbeta/quarterly_balance_sheet.json` | `Ticker.quarterly_balance_sheet().data` | 同上;81 行 | 18:30:03 | 否 | 同上 |
| `defeatbeta/quarterly_cash_flow.json` | `Ticker.quarterly_cash_flow().data` | 同上;56 行 | 18:30:03 | 否 | 同上 |
| `defeatbeta/quarterly_revenue_by_breakdown.json` | `Ticker.quarterly_revenue_by_breakdown()` | — | 18:30:04 | 否 | **來源回傳空表**(0 列;此公司無分部拆分) |
| `defeatbeta/shares.json` | `Ticker.shares()` | 1998-03-31 至 2026-05-04,222 筆 | 18:30:05 | 否 | 日期為來源報告日,非申報封面日 |
| `defeatbeta/splits.json` | `Ticker.splits()` | — | 18:30:06 | 否 | **空表**(無拆股紀錄) |
| `defeatbeta/calendar.json` | `Ticker.calendar()` | 2023-02-16 至 2026-07-30,15 筆 | 18:30:06 | 否 | `time` 多為 `time-not-supplied`;未來日期屬排程非確認 |
| `defeatbeta/info.json` | `Ticker.info()` | 現時快照 | 18:30:12 | 否 | 無歷史版本 |

## prices/(1 份)

| 路徑 | 來源 / 工具 | 期間 | 取得時間 (UTC) | 截短 | 已知缺漏 |
|---|---|---|---|---|---|
| `prices/AXTI.daily_slice.csv` | 本地 `data/prices/daily/part_11.parquet`(entity_id=0001051627,primary)最後 400 個交易日 + DefeatBeta `Ticker.price()` 續抓 | 2025-01-29 至 2026-09-11,407 列(本地 400 + DefeatBeta 7);`source` 欄分 local / defeatbeta | 18:31:58 | 是(只取最後 400 個本地交易日) | 本地庫此公司最後一日是 2026-09-01(非全庫名義的 09-02),續抓由 09-02 起以免人為留洞;DefeatBeta 列無 `adj_close`;DefeatBeta 最後一列 09-11(09-14 未入);重疊 400 日核對:收市價相對差最大 5.7e-8、成交量全同、日期互無缺 |

## futu/(13 份;MCP 可用,13 個接口全部成功,0 失敗)

| 路徑 | 工具 | 期間 | 取得時間 (UTC) | 截短 | 已知缺漏 |
|---|---|---|---|---|---|
| `futu/quote_research_analyst_consensus.json` | `quote_research_analyst_consensus` | 更新 2026-08-31;5 位分析員 | 18:32 | 否 | 只有聚合,強買/持有/賣為百分比;無歷史版本 |
| `futu/quote_research_rating_summary.json` | `quote_research_rating_summary`(機構維度,limit 20) | 5 家機構、34 條評級,2025-10-29 至 2026-07-31 | 18:32 | 否(has_more=false) | 分析員維度清單為空;多條無目標價;update_time 比 recommendation_date 遲數日至數月,不能當「當日已可見」;來源 TipRanks |
| `futu/quote_research_morningstar_report.json` | `quote_research_morningstar_report` | 報告日 2026-09-11 | 18:32 | 否 | 只有量化評級(無人手分析員報告);fundamentals_content 為空;ai_analysis 是富途生成文字,非晨星 |
| `futu/quote_valuation_detail.json` | `quote_valuation_detail`(PE,1 年) | 2025-09-15 至 2026-09-14,251 個日點;板塊同儕 30 家 | 18:35 | 否 | PE 由虧損負值於 2026-07-30 跳成 +1,564,一年均值與 ±1σ 無意義;plate_stock_item_count 22 對 30 家不符;profit_data 由 2023Q1 跳到 2026Q2 |
| `futu/quote_insider_holder_list.json` | `quote_insider_holder_list`(limit 30) | 現時 8 名內部人 | 18:35 | 否 | 每人買賣次數欄全同(3/3/8),似公司層統計;一人無持股數;職銜中英混雜 |
| `futu/quote_insider_trade_list.json` | `quote_insider_trade_list`(limit 50) | 2025-11-24 至 2026-08-16,50 筆(共 81) | 18:35 | 是(第一頁;next_key "50" 未翻) | Form 144 擬售與其後 Form 4 實售並列,直接加總會重複;日期是交易日非申報日;部分欄缺 |
| `futu/quote_shareholders_institutional.json` | `quote_shareholders_institutional`(limit 10) | 2024/Q2 至 2026/Q3,10 期 | 18:35 | 是(第一頁;next_key 1711900799 未翻) | 期別標籤按季末 +45 日推算(2026/Q3 實為 6 月底持股);最新一期似未完成 |
| `futu/quote_short_interest.json` | `quote_short_interest`(count 30) | 2025-06-13 至 2026-08-31,30 筆(半月一筆) | 18:35 | 是(count 30,最多 90) | 日期是結算日,無公布時刻;days_to_cover 多數被壓成 1 |
| `futu/quote_daily_short_volume.json` | `quote_daily_short_volume`(count 30) | 2026-07-31 至 2026-09-11,30 個交易日 | 18:35 | 是(count 30) | 只拆 Nasdaq / NYSE 兩個場所;09-14 未入 |
| `futu/quote_financials_earnings_price_history.json` | `quote_financials_earnings_price_history` | 2021/Q2 至 2026/Q2 共 20 期,每期 30 列(偏移 −15 至 +14 日),600 列 | 18:35:08 | 否(逐位元複製自系統保存的原始輸出) | 2021–2022 期 pub_type 0 且時刻 00:00:00 = 時刻不明,不能當午夜;每期 30 列重複同一組欄位 |
| `futu/quote_company_profile.json` | `quote_company_profile` | 現時 | 18:32 | 否 | 全部欄位為字串;無 CIK |
| `futu/quote_owner_plate.json` | `quote_owner_plate` | 現時 | 18:32 | 否 | `name` 欄放的是股票名不是板塊名;無成員歷史 |
| `futu/quote_market_snapshot.json` | `quote_market_snapshot(["US.AXTI"])` | 2026-09-14 盤中(美東 14:32) | 18:32 | 否 | **盤中快照,last_price 不是收市價**;listing_date 為 0 與 profile 不符;pe_ratio 負而 pe_ttm 1,954 並存 |

## longbridge/(17 份;MCP 可用,17 個接口 16 成功、1 失敗:`fund_holder` 回 `internal server error`,recoverable none,未重試)

| 路徑 | 工具 | 期間 | 取得時間 (UTC) | 截短 | 已知缺漏 |
|---|---|---|---|---|---|
| `longbridge/quote.json` | `quote(["AXTI.US"])` | 2026-09-14T18:41:34Z 盤中 | 18:41:34 | 否 | **盤中價非收市價**;post_market 屬前一交易日、overnight / pre_market 屬當日,三段不同日;價格為小數字串 |
| `longbridge/consensus.json` | `consensus` | Q3 2024 至 Q1 2027 共 11 期(8 已公布 + 3 前瞻),六項指標 | 18:41 | 否 | **整份沒有任何時間戳**(預測形成時間、公布時間皆無);兩格 estimate 空字串;無分析員數與高低;說明文字為簡體;是公布時的 surprise 資料,不能直接作往後兩季的 C4(§四 7) |
| `longbridge/forecast_eps.json` | `forecast_eps` | 2019-01-14 起 112 個快照窗口,最後一個 end_date "0"(現行) | 18:41 | 否(逐條換行以便比對,值原樣) | 機構數三欄全為 0;未註明各預測對應哪個財年;9 條 end_date 為 2079-06-06 哨兵值;窗口重疊需去重 |
| `longbridge/institution_rating.json` | `institution_rating` | 2026-08-27 起(end_date "0") | 18:41 | 否 | 同一份內兩套評級字彙(buy/over/hold 與 strong_buy/buy/hold);updated_at 是中文日期字串;目標均價 91.6 對富途 90.75 |
| `longbridge/institution_rating_history.json` | `institution_rating_history` | 目標價月史 2021-10-01 至 2026-09-01(60 列);評級分佈窗口 2021-10-28 至今(90 段) | 18:41 | 否 | 全部數字含計數與 epoch 皆字串;首列目標價空;月級快照落後實際評級數週;多段連續相同 |
| `longbridge/institutional_views.json` | `institutional_views` | 評級分佈月表 2018-01-31 至 2026-08-27(104 列);目標價表同上(60 列) | 18:41 | 否 | 此接口回到 2018-01,`institution_rating_history` 只到 2021-10——兩個接口深度不同;tlist 與 target_history 同資料不同欄名,最後一列收市價略有差異 |
| `longbridge/shareholder.json` | `shareholder` | 27 列,report_date 2026-03-20 至 2026-08-17 | 18:45 | 否(`total` 欄為 0,未填) | **13F 機構(6 月底)與內部人 Form 4 混在同一清單**,institution_type 全空無法分;兩列 shareholder_name 空白(2.74%、4.91%);shareholder_id 全為 "0";無持股數只有百分比 |
| `longbridge/fund_holder.json` | `fund_holder` | — | 18:45 | — | **取得失敗**:error_code 2101400 internal server error,recoverable none;檔內存錯誤信封,契約須把「取得失敗」與「確定無基金持有」分開 |
| `longbridge/short_positions.json` | `short_positions(count 40)` | 2025-01-15 至 2026-08-31,40 筆(半月) | 18:45 | 是(count 40,最多 100) | 與富途同一 FINRA 序列,shares 相同但 rate 是小數(0.1402)對富途百分比(14.018),days_to_cover 富途壓成 1 |
| `longbridge/filings.json` | `filings` | 2026-04-21 至 2026-08-19,最新 50 筆 | 18:45 | 是(廠商只回 50 筆) | 實際欄位與工具說明不同(無 type / filing_date;要由 title 解析表格);10-K、10-Q 與五筆 04-24 的 publish_at 只有日期精度且 10-Q 比 EDGAR 受理遲一日;附件 URL 無類型標籤;無 accession 欄 |
| `longbridge/valuation.json` | `valuation` | PE 日序列 2025-09-14 至 2026-09-13,313 點(含週末沿用) | 18:54 | 否 | 只有 PE;desc 是含 HTML 標籤的簡體句子;低/中/高跨越虧轉盈無意義;PE 1,095 對富途 1,954 同日不同口徑 |
| `longbridge/valuation_history.json` | `valuation_history` | PB 日序列 2025-09-14 至 2026-09-13,313 點;同業 36 家市值 | 18:57 | 否 | 只有 PB 且無參數可選指標;時間戳為 epoch 秒字串(與 `valuation` 的 RFC3339 不同);`symbols` 區塊鍵名被壓成 `a_x_t_i._u_s`;含 aichat / ai_summary 等介面負載 |
| `longbridge/industry_valuation.json` | `industry_valuation` | AXTI 月史 2021-10-01 至 2026-09-01(60 列)+ 同業 ASML、LRCX | 18:54 | **是**:AXTI 區塊完整原樣;兩家同業的 history 只留頭 2 尾 2 列,中間 56 列以 `_truncated` 標記物件代替(同業純作結構示範) | 同業是設備巨頭非基板同儕;數字字串最多 22 位小數;AXTI 三個 PE 口徑(−198 / +1,095 / +1,954)分屬兩家廠商;ASML 2024-01-01 原有 pe 2753.99 廠商異常值(已記在 meta) |
| `longbridge/business_segments.json` | `business_segments` | 2026.Q2(2026-03-30 至 2026-06-30) | 18:45 | 否 | 業務只有一個 100% 桶,無產品線拆分(DefeatBeta 同樣為空);rpt_date "2026.04.30" 錯(Q2 業績是 07-30 公布);地區名簡體;三種日期格式並存 |
| `longbridge/finance_calendar.json` | `finance_calendar(report, US, 2026-09-15..2026-09-28)` | 10 個日桶(至 09-29)、45 場業績 | 18:45 | 否 | **全市場清單,AXTI 不在窗內**(只作事件結構樣本);日桶是 UTC 日而事件 local_date 是美東日,盤後事件落在下一桶;LAES 一場未到期已填 actual_revenue;數值為本地化字串,要用 value_raw |
| `longbridge/security_facts.json` | `security_facts(limit 100)` | 2026-01-07 至 2026-08-03,34 條(News 19 / Fundamental 10 / Technical 5) | 18:54:55 | 否(逐位元複製自系統保存的原始輸出,444,511 字元) | nl_info 是廠商生成敘事(每條 1.4k–36k 字元),不是來源資料;anomaly_detection 欄全空;08-03 後無事實雖股價多次 ±10%;新聞 URL 指向廠商頁 |
| `longbridge/history_candlesticks_by_date.json` | `history_candlesticks_by_date(week, 2024-01-01 起)` | 2024-01-01 至 2026-09-14,142 根週線 | 18:57 | 否(逐條換行,值原樣) | **最後一根是進行中的本週(只有 09-14 一個盤中交易日)**;未復權且無企業行動標記;trade_sessions=all 但每根都標 Intraday |

## 補做清單(主 agent 決定是否補)

1. `longbridge/fund_holder`:廠商 500 錯誤,可擇日重試一次。
2. 富途 `quote_insider_trade_list`(next_key "50",餘 31 筆)、`quote_shareholders_institutional`(next_key 1711900799)兩個分頁未翻;`quote_research_rating_summary` 分析員維度(rating_dimension_type 2)未取。
3. Longbridge `consensus` 的半年 / 年度變體(opt_periods saf / af)未取;`valuation` 只回 PE、`valuation_history` 只回 PB,PS 無接口回傳。
4. 本地 10-K 快取無 AXTI(manifest 9,914 份之中沒有此 CIK),10-K 由線上抓;若日後補建快取應以此份 accession 0001437749-26-008612 對照。
