---
id: KARST-136
title: 前瞻盈利收益率序列建置票(用戶裁決 D-109 全面轉前瞻):由 yfinance 季度 PIT 預估砌九板塊+大市月度前瞻盈利收益率序列(2002 年起),連同由現有正本翻算嘅後顧盈利收益率,兩條同落一個 CSV;建置報告講清覆蓋率、錯改率、限制;唔跑任何訊號
type: task
createdAt: 2026-09-01
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: karst-136-agent
deliverable: KARST-D02
---

## 工作內容

端到端行為:探索地基由「後顧市盈率」升級做「盈利收益率兩條線」。完成後,一個 CSV(建議 experiments/2026-09-02-forward-yield-build/sector_yields.csv)載有月度序列 series×month_end 兩欄指標:ey_lag(後顧盈利收益率=過去十二個月已公布盈利÷市值,由 experiments/2026-09-02-multiples-oracle-scan/ 現有管線同一批成員同一權重翻算,負盈利照計唔斷線)同 ey_fwd(前瞻盈利收益率=未來四季 PIT 預估盈利÷市值,2002 年起)。前瞻分母行 KARST-125 勘察定案嘅路線(裁決 D-093;勘察報告同票喺 .kira/tickets/ 與 research/ 自己搵嚟讀):yfinance get_earnings_dates 每季 EPS 預估,當年當時版本,錯改率約 2.8%;逐公司預估 EPS×股數合計做板塊分子,成員與市值權重同現有月度正本一致;預估缺席嘅公司點處理(跳過/後備)要寫明並統計佔比。序列覆蓋 MKT+九隻 SPDR 板塊,月底頻。建置報告(research/2026-09-02-前瞻收益率序列建置.md)必答:逐板塊逐年覆蓋率(有預估嘅市值佔比)、2002 前點解冇、錯改率喺呢批樣本實measured幾多、同後顧序列嘅相關與分歧期(分歧期正係前瞻有增量資訊嘅位)。誠實限制照錄:只有現存 657 間公司(除牌缺席)、預估係分析員共識唔係真實、yfinance 歷史預估嘅 PIT 性質係勘察結論唔係鐵證。唔跑任何訊號唔落任何判詞——嗰啲係 KARST-137 嘅事。

## 驗收條件

- [ ] sector_yields.csv 落檔:MKT+9 板塊,月底頻,ey_lag 全期(1998-12 起)+ ey_fwd(2002 起),負盈利期唔斷線;砌檔腳本同錄
- [ ] 建置報告成檔:覆蓋率逐板塊逐年、錯改率實測、兩條序列相關與分歧期、限制三條照錄
- [ ] ey_lag 翻算口徑核對:與現有 pe_lag 正本逐月互為倒數(容差內),核對表落檔
- [ ] 生產庫雜湊不變;大檔不入 git;預估數據抓取有快取落 experiments/,唔重複打 API

## 結果

## 留言
