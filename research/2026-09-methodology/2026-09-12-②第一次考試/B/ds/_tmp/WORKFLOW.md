# exam2-B-ds-1 工序備忘(壓縮後照此續做)

## 身份與範圍
- 工人 `exam2-B-ds-1`(DeepSeek 臂第一隊)。票 KARST-233。
- 事件:`A3/picks_final.md` 第二節最終主清單 84 宗,**表序 #11–#42 = E011–E042,共 32 宗**。
- 已落檔、不重判:E001–E010(第一隊上一輪)、E043、E044(更早一輪)。第二隊 `exam2-B-ds-2` 做 #43–#84。
- **禁讀 `B/opus/`**、禁讀 A3 的 controls/population/entry_pool/thresholds/picks_*/cache/執行紀錄/補強紀錄/入口抽查、禁讀 `data/`、禁讀其他事件(含第二隊)的卡。
- 禁 Agent 工具、禁背景執行、禁網絡。含中文檔只用 Write 寫。Python 一律 PYTHONUTF8=1。

## 每個事件四步
1. `PYTHONUTF8=1 python _dump.py <eid> core` — 事件識別/觸發 meta/文件清單/八季數列/同業/價格/共識。
2. `PYTHONUTF8=1 python _dump.py <eid> pr` — EX-99.1 全文(必要時先 `| head -c N`)。
3. 有逐字稿:`_dump.py <eid> trhead 14000` 或 `trgrep <pat>`。本地申報:`_gz.py find <gz> <regex> [max]` / `_gz.py sed <gz> <a> <b>` / `_gz.py ctx <gz> <regex> [n] [mx]`。
4. 寫 `卡-<eid>-<ticker>-<signal_date>.md`(Write 工具)+ 寫 `rows/<eid>.spec.json`(Write 工具)→ 跑 `PYTHONUTF8=1 python _mkcsv.py <eid>`。

## 卡結構(照提示詞 v1.1)
頭五行:event_id/ticker/T0/T1/T2;improvement_type_機械;g0;模型:deepseek-v4.1-flash;effort high;提示詞 v1.1;判斷日期 2026-09-13;一次執行。
然後【第一步:改善是什麼】…【第八步:最大未知、總判與延續機率】+ `contamination_note` 節 + 判不出的事 + 執行紀錄節(**開始與結束各實跑一次 `date -u` 並貼原始輸出**;列出讀了哪些本地檔與行段)。

## 28 欄 csv(次序固定)
event_id,ticker,cik,signal_date,improvement_text,n_drivers,top_driver_type,top_driver_share_lo,top_driver_share_hi,persistence_overall,p_continue,pred_g2_point,pred_g2_lo,pred_g2_hi,pred_g4_point,pred_g4_lo,pred_g4_hi,supply_catchup,supply_timing,tags,lifecycle_stage,stop_event_1_date,stop_event_2_date,premise,falsify_1,biggest_unknown,unknowns_count,contamination_note
- top_driver_type ∈ {價格,數量,組合,成本,一次性,低基期,匯率,收購}
- persistence_overall ∈ {高,中,低,無法判斷};高 p≥0.70;中 0.40–0.69(要寫一句為何既不高也不低);低 <0.40
- 門檻 = 0.8×g0(g0<0 時 = g0);pred_* 小數(0.12=12%),lo ≤ point ≤ hi
- supply_catchup ∈ {會,不會,不適用,查不到};「不適用」必附真正機制
- tags 用「|」連,取自 {快速增長,景氣循環,樽頸}
- lifecycle_stage ∈ {起步,快速擴張,飽和,不適用,查不到}
- 文字欄一句、不含換行;csv 由 csv 模組 QUOTE_ALL 寫(可含逗號)

## 硬規矩
- 訊號季數字只用 EX-99.1 稿內;稿內沒有的標「查不到」。
- 每句判斷附出處(申報類型 + accession + 節名/行號);無出處標「判斷」。
- 不寫市場對錯、不給買賣判詞、不填價格已反映多少。共識一律查不到。
- 記憶污染照樣隔離並在 contamination_note 誠實寫。
- 每事件只判一次,寫完不改;發現錯另寫 `rows/<eid>.note.md`。

## 收工
1. 續寫 `執行紀錄——ds-1.md`(模型、effort、每事件起訖 date -u、讀了哪些檔、失敗與重跑)。
2. `node "C:/projects/Kira/Kira/plugin/tools/kira-ticket-ops/cli.mjs" comment --ticket KARST-233 --as exam2-B-ds-1 --spec <json>`(四格:結論/證據/產物/未解與風險)。
3. 最終訊息:每事件一行 `event_id | persistence_overall | p_continue | pred_g2_point | supply_catchup | 讀了幾份本地文件 | 問題`;加總耗時。
