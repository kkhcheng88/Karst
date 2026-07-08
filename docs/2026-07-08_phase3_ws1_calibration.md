# Phase-3 WS1 規格 —— 裁判修復(校準迴路)【設計定稿,待執行】

> 設計:Fable(2026-07-08);事實底:scratchpad `ws1_forensics.md`(forensics agent,code+實跑核實)。
> 現況:276 行戰績簿、**2 種 schema 並存**(A=272 行,`forward_ic.py:62-81` 寫,有排程;
> B=4 行超集,`log_predictions.py:39-69` 寫,**冇排程**);0 matured(時間未到);
> 58 ticker 入面 57 隻可回填價格(SIVE 兩源都攞唔到);`backtest/spine/providers.py:40-51`
> 讀 themes.yaml 5 個 field。

## 1. 定案

### D1|單一寫入者 = schema B(超集),A 退役
- `log_predictions.py` 成為唯一 writer;`forward_ic.py` 內嘅 `log_predictions()` 函數**刪除**
  (唔係留住唔叫 —— 留住 = 第日又俾人叫返)。
- `daily_ic.cmd`(05:30)改為:`log_predictions.py` → `backfill_outcomes.py`(新)→
  `forward_ic.py report` → git commit。
- **遷移(一次性 script `thesis/migrate_track_record.py`)**:272 行 A 格式正規化做 B 超集
  (補 `outcome: null`、`legacy: true`);07-07 嗰 4 個 A/B 重疊 (ts,ticker,thesis_id) 保留 B 行;
  遷移前備份原檔;遷移後 `forward_ic.py ic` 要跑得通並輸出同遷移前一致嘅 pending 數。

### D2|Outcome 回填(新 `thesis/backfill_outcomes.py`)
- 對每行 `outcome==null` 且 `asof_date + horizon` 已到期:填
  `{fwd_ret: {21,63,126}, excess_vs_spy: {…}, filled_at}`;價格口徑跟 `forward_ic.py` 現行
  (adjusted=True;SPY 同口徑)。
- 攞唔到價(SIVE 類):填 `outcome: {error: "no_price_source"}`,IC 計算排除並喺 report 披露
  排除數。
- `kill_fired` **唔自動判**(kill 係文字條件,機器判唔到)—— 留 null,由夜班分析/日間 session
  按 lint 提示人手回填;呢個係明文人工位,唔扮自動。

### D3|裁判狀態機(`forward_ic.py report` 改造,輸出 JSON + 人讀兩版)
- **PRELIMINARY**:matured < 60 或 weekly 橫截面 < 8 → 唔出判決,淨報進度。
- **PASS**:rolling 26 週內,63d **excess** IC(Spearman,週度非重疊,ticker 級橫截面)均值 ≥ 0.05
  且 IR(mean/std)≥ 0.5。
- **FAIL**:rolling 26 週均值 ≤ 0 且 matured ≥ 150 → JSON 帶 `circuit_breaker: true`。
- 副指標(報唔判):theme 級 IC(n=9,橫截面薄,參考用)、21d/126d IC、raw IC。
- **熔斷有牙**:`circuit_breaker: true` 時,WS5 嘅衛星部署上限自動減半(sizing 規則讀呢個 JSON;
  接線屬執行階段)。

### D4|Confidence 校準映射 —— **押後**(MVP 護欄)
matured ≥ 100 先開始做「講 0.7 中唔中 70%」嘅映射;而家淨係保證數據齊(D1/D2 已保證)。
唔准而家發明校準公式 —— 冇數據嘅校準 = 假嘢。

## 2. Self-Review(反駁過乜)

| 挑戰 | 裁定 |
|---|---|
| 「58 ticker 橫截面,但同主題 ticker 高度相關,有效 n 細好多」| 成立 → 所以 theme 級 IC 做副指標並列;PASS 門檻用 26 週 rolling(時間軸補橫截面嘅薄)|
| 「IC 用 raw 定 excess?」| Excess-vs-SPY 做判決口徑(repo 標準:唔好俾 beta 冒充技巧);raw 併報 |
| 「kill_fired 可以自動化?」| 唔可以(文字條件)→ 明文人工欄,lint 提示;扮自動 = 自欺 |
| 「校準映射點解唔即刻做?」| 0 matured 下做映射 = 純理論;MVP 護欄:管道先行,映射等數 |
| 「forward_ic.py 兩用(写+判)點解要拆?」| 單一寫入者係防再爛嘅結構保證,唔係潔癖 |

## 3. 執行 backlog(交日常 session;每項帶驗收)

| # | 項 | 驗收 |
|---|---|---|
| 1 | `migrate_track_record.py` + 跑一次 | 276→統一 schema;重疊 4 行去重;備份存在;`ic` 跑通 pending 數不變 |
| 2 | 刪 `forward_ic.log_predictions()`;`daily_ic.cmd` 改叫新鏈 | 05:30 run 後 jsonl 尾行係 B schema;cmd ASCII-only |
| 3 | `backfill_outcomes.py` | 人工做舊一行測試(改 asof 做 90 日前)→ 回填正確;SIVE 行標 error |
| 4 | `forward_ic.py report` 狀態機 + JSON | PRELIMINARY 輸出正確;fixture 測 PASS/FAIL 分支 |
| 5 | lint.py 加:themes.yaml 每主題必有 kill/tickers/cycle_stage/confidence + 單源 flag 欄(WS3 接手)| lint 0 error |
| 6 | 驗證不自驗:獨立 agent 讀規格逐條核對實作 | PASS |

**時間盒:全部 ≤ 1 個執行 session。第一個真判決預計:首批 21d 預測 7 月底到期,63d 判決 ~10 月。**
