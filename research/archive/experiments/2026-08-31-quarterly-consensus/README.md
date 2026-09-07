# KARST-125:逐季「公布前共識」勘察的樣本與腳本

配合報告 `research/2026-08-31-季度共識來源勘察.md`。純數據勘察,不落策略結論、不改策略碼。

## 腳本

| 腳本 | 驗什麼 |
|---|---|
| `probe_yfinance_estimates.py` | yfinance 逐季「預測 vs 實際」有幾深、有哪些欄位 |
| `probe_yf_coverage.py` | 覆蓋有幾闊:大中小微型股、房地產信託、行業 ETF 各有沒有貨 |
| `check_estimate_is_live_consensus.py` | 記在**未公布**季度上的預測值,是不是等於今日的即時共識(自足檢查,不靠外部存檔) |
| `verify_yahoo_estimate_vintage.py` | **核心證據**:拿 Wayback 的舊版頁面,對同一季度的預測值,今昔逐格對數,看數字有沒有被改寫 |
| `probe_defeatbeta_estimates.py` | defeatbeta-api 有沒有任何預測/共識類的表 |
| `probe_defeatbeta_calendar.py` | 它的業績日曆表逐欄看清楚,連整份表清單 |

跑法(Windows,中文輸出要先設 UTF-8):

```
set PYTHONUTF8=1
python probe_yfinance_estimates.py
```

## 產出放哪

- `out/` —— 小樣本 CSV 與逐次執行的紀錄,**入 git**,它們就是報告的證據。
- `data/` —— 抓回來的原始存檔頁面,一份約 0.5–1.5 MB,**不入 git**(倉根 `.gitignore` 已擋 `experiments/*/data/`),重跑腳本即可再抓。

## 一個踩過的坑,寫低免得下一個人再踩

Yahoo 那份 `earningsHistory` JSON,每筆紀錄裡的欄位次序是 `epsActual` → `epsEstimate` → `quarter`,即是**季度標籤排在預測值後面**。用「先找 quarter、再往後找 epsEstimate」的正則去抽,會把第 N 個季度標籤配上第 N+1 筆的預測值,於是每一格都差整整一個季度——結果看上去就跟「Yahoo 事後改寫了預測值」一模一樣,而且錯得很整齊,很容易當成真發現。

所以 `verify_yahoo_estimate_vintage.py` 改為括號配對抽出整個 JSON 陣列再逐筆解,並且加了一道自檢:**已公布的實際盈利是不改的事實**,如果舊版頁面的實際值同今日對得上,就證明季度確實對準了,那時預測值若有差異才算真差異。
