# 全範圍日更與恢復 v1（Agent 可直接接手）

用途：一次完整日更；可由互動或排程 Agent 執行。不依賴之前對話。公開投研與發布已獲授權，不包含交易、私人持倉或對外訊息。

## 起手與唯一正本

讀 master 的 HANDOFF.md、strategy/四類注地圖.md、此檔、get_research_protocol(mode="workflow")。進度以地圖最新紀錄為準。Repo kkhcheng88/Karst；正式站 https://kkhcheng88.github.io/Karst/；MCP服務 https://karst.zeabur.app。確認雲端工具版本；不得把程式存在當部署成功。身份用交易所前綴；SPY為NYSEARCA:SPY。

## 一次執行

1. `get_daily_scope(universe_id="daily-monitoring")` 讀版本化名單；公司、雷達、價值鏈及市场參照全部納入，不用正式研究清單替代。比對上次回執，新增／移除要記錄。
2. `get_daily_runs(limit=10)` 查中斷。相同觀察窗口未完成才 `resume_daily_scope(run_id)`；只補失敗及未執行成員，成功來源日期保留。新一天必須 `refresh_daily_scope(universe_id="daily-monitoring")`，不能沿用昨日成功結果冒充今天。名單版本變動拒續跑，重新開本日批次並保留舊回執。
   - **背景分段（0.2.14 起）**：`refresh_daily_scope` 與 `resume_daily_scope` 在背景執行，每次呼叫最多等 40 秒，只回摘要與 `run_id`（`state`＝running／finished／interrupted、`counts`、`incomplete_subjects`、`pending_subjects`、`reassessment_queue`），不回每股全文。`state=running` 就用 `get_daily_runs(run_id=..., wait_seconds=40)` 再查，直至 finished；要某股詳情用 `get_daily_runs(run_id=..., subject=...)`。同一名單有批次仍在跑時，新開批次會被拒，應改為查該批次。
   - 容器重啟後，未完成批次讀作 `interrupted`：以同一 `run_id` 呼叫 `resume_daily_scope`，已完成成員不重做。`finished` 但有 `incomplete_subjects` 時同樣可續跑，只重試那些成員。
   - 每股每日有日更快照：機械更新計劃價距離、觸發狀態、現價 R&R 及對公允價值範圍的位置，不改研究版本、不寫查核、不發布。`reassessment_queue` 列出需要 Agent 重評的層：價格事件→L5／L6；新新聞→L2／L3／L4／L6。來源覆蓋不完整不排隊，新聞窗口亦不推進。重評完成並 `record_update_check` 後，該股的排隊才清除。
3. 若 session 尚未列新工具，依名單逐股 `refresh_sources(subject, kinds=["prices","news"])`，保存每股結果與失敗、新聞窗口及來源日期。先核工具現有參數，不猜未暴露介面；可用 `refresh_daily` 時優先該入口。成功取源不等於研究完成。失敗成員本輪補跑一次，持續失敗保留incomplete及錯誤，不寫無新聞。
4. 宏觀與共同產業事件只取一次。讀新聞標題去重，原文核對新事件、舊聞轉載與事件日期；受影響股票各自評估。正常日更新位置、RS／動能與行動；業績、訂單、融資、監管、競爭變化才重評相關經營與倍數。休市仍掃新聞，價格保留最近完整收市，不能製造新K線。
5. SPY六因素各保留證據期別、上次判斷及缺口；只改受影響項，合成一句市場立場。不能用升跌倒推宏觀原因。比較先對齊期間、幣別、會計和資本口徑；ARR不是全年收入，融資額不是現金，新增債務與所得現金雙邊處理。研究假設明示，不能標成公司指引。
6. 兩種觀望分開：研究足夠但機會不合適／缺關鍵研究無法建議。有合格方案才列方向、觸發、入場區、失效、目標、保守端成本後風報比、催化劑。否則列最關鍵等待條件及成立後重評甚麼。機會比較回答偏好、溢價依據、不值得追者。
7. 新來源 `ingest_source` 後 `read_evidence`；主研究按update protocol沿用未變層，`save_research(expected_previous_version_id=...)`，讀回計算與目標，再 `publish_research` 和 `set_watch`。衝突重讀合併判斷，禁止強蓋。無公司契約的指數／價值鏈存來源、計算及閱讀provenance，不假稱正式公司研究。完成原文判斷才 `record_update_check` 推進已審查窗口；不完整不得推進。
8. 閱讀版新增revision，價格／圖表／正文日期一致，經營模型日期單列；檢查過時目標在最新摘要與計劃全部撤回。生成 manifest：`editions:[{report,provenance}]`，必要時 `desk`；格式參照 cards/reader/README.md。暫存manifest及stage於scratch。
9. 執行 `python -m karst.reader.release stage --content cards/reader --manifest MANIFEST --out STAGE`；閱讀四類頁、計算與stage回執，歷史HTML不得變；通過後 `python -m karst.reader.release apply --content cards/reader --staged STAGE`。純編輯無需重跑整套抽取回歸；程式變更跑對應功能測試。
10. GitHub取最新master及tree，以其為base提交已審核差異；不可推本機不同歷史或force。若遠端改動，重讀、重做stage。已有相同研究／閱讀版則沿用，避免重複。公開repo不放憑證、帳戶資料或第三方全文。
11. 等Pages Actions成功，執行 `python -m karst.reader.release verify --staged STAGE --base-url https://kkhcheng88.github.io/Karst --edition COMMIT --receipt RECEIPT.json`。必須HTTP讀回首頁、新版頁、歷史新版入口及圖表bytes一致；Actions成功不等於讀回成功。程式更新另核healthz版本。發布失敗只補發布，不重做研究。
12. 保存回執至 `cards/runs/daily/YYYY-MM-DD/status.json`，更新地圖及HANDOFF；每日輸出市場變化→鏈冷暖→個股行動→缺口。允許各股部分完成，不允許整批incomplete稱全完成。只在任務結果回報，不另發郵件／Slack。

## 回執最少欄位

`run_id, parent_run_id, universe_id, universe_version, started_at, source_cutoffs, members, shared_events, research_versions, reader_editions, publication, gaps`。

members逐股存：`subject, intake_status, evidence_ids, news_window, review_status, changed_layers, failure, retry_count`。publication存：`status, commit, pages_run, stage_fingerprint, readback_receipt`。階段區分 intake_ready、reviewed、analysis_saved、reader_staged、committed、deployed、verified；independent_review_done另欄，不能由主研究自查替代。

## 恢復與退出

- 取數中斷：讀雲端checkpoint，同窗口resume；repo回執不替代雲端實際來源。
- 研究已存、頁面未發：讀版本，不重存相同研究；從stage繼續。
- 已提交、讀回失敗：讀Actions／master與實際頁面，重試讀回；確有錯才新修訂，不改歷史。
- 外部來源失敗、模型不可用：明示受影響判斷及待辦；覆核job pending不是覆核完成。
- 驗收要求：每個名單成員有結果；失敗可續跑；舊成功不被重新標日期；六因素與前瞻比較可追到來源／假設；新版公開bytes可核對。

主研究Agent與排程Agent使用相同標準。排程建立只證明已登記；首次獨立排程執行、成功發布與讀回另需實際回執，未有回執不得宣稱每天已成功自動運作。
