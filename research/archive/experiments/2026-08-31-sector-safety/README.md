# KARST-119:板塊安全判準與債券中間級

- **票**:KARST-119(D-064 / D-065 / D-070 / D-071)
- **報告**:`research/2026-08-31-板塊安全判準與債券中間級.md`
- **紀律**:判準文本連全部參數在提交 **`0a6ac10`** 已寫死,該提交**沒有**下載過任何數據、沒有跑過任何計算。本目錄全部檔案在該提交之後才產生。

## 次序(照跑一次可重現)

```
set PYTHONUTF8=1
python experiments/2026-08-31-sector-safety/fetch_prices.py   # 板塊 ETF + SPY + IEF 日線含息價
python experiments/2026-08-31-sector-safety/fetch_cftc.py     # CFTC 金融版(TFF)E-mini 標普 500 週報
python experiments/2026-08-31-sector-safety/measure.py        # 三條判準 × 五次熊 + 階梯回測
python experiments/2026-08-31-sector-safety/report_tables.py  # 報告用表
python experiments/2026-08-31-sector-safety/extras.py         # 補充數字(債券濾網、真值副口徑等)
```

`probe_cftc.py` 只用來探 CFTC 的欄名,不參與量度。

## 檔案

| 檔 | 內容 |
|---|---|
| `prices_daily.parquet` | 九隻 SPDR 板塊 ETF、SPY、IEF 的日線開市/收市**已調整價(含息)**,1998-12-01~2026-08-27。**不入本倉**(照 KARST-113 先例,探索性價格數據不落 git),跑 `fetch_prices.py` 即重新生成 |
| `cftc_tff_es.parquet` | CFTC TFF FutOnly 週報,合約代碼 `13874A`,1,055 週,2006-06-13~2026-08-25 |
| `monthly_panel.csv` | 月度面板:331 個持有月 × 回報、三條判準訊號、持倉百分位、債券濾網 |
| `results.json` | 全部量度結果(基礎率與打和線、逐判準逐熊統計、階梯回測、五次熊基礎事實) |

## 口徑要點

- **探索性數據,不入生產庫**(與 KARST-113 同一個做法);沒有改動任何引擎程式。
- 成交:上月最後一個交易日收市決策,下一個交易日**開市價**成交(D-021 第 3 條)。
- 現金:**USD,恆一、零息**(D-060)——與 KARST-113 用國庫券不同。
- 換馬成本主數字 10 個基點,另跑 0 與 25。
- CFTC 知情時點:**截數日 + 10 個曆日**(保守;官方公佈時間表未入庫,KARST-112 明文不可寫死三日)。

## 一句話結果

**三條判準(趨勢線族單腳、持倉族單腳、雙腳正形)全部不及格**——三條都過不到「轉守之後防守那邊真的跑贏」那一關。**債券中間級有條件通過**:必須帶自身 10 個月線濾網,否則 2022 年那段多蝕 5.87 個百分點。
