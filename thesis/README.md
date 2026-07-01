# thesis/ — Phase 3 質性 offense 層(NHITL)

設計藍圖見 `DESIGN.md`。本層產出 **confidence**(可算+可校準,不是「信念」)餵 `spine/providers.thesis_quality`。

## 結構
```
thesis/
  DESIGN.md            ← 定案設計(讀這個先)
  themes.yaml          ← 機器可讀 registry:ticker -> theme verdict(spine 讀這個)
  wiki/                ← markdown + [[]] 綜合頁(4-KPI 證據 + 引用),幾千頁級
    <slug>.md          ← 一個主題/概念/公司的頁
  track_record.md      ← agent 自我監控 log 的 schema(§DESIGN 6;不是人的日記)
  track_record.jsonl   ← 實際 log(append-only,系統寫,冷啟為空)
```
原料語料(新聞/逐字稿/財報)**不在此**——在 SQLite FTS(百萬級);wiki **引用進**語料,不複製。

## 加一個主題(pilot 流程)
1. 建 `wiki/<slug>.md`:4-KPI(moat/bottleneck、ROIC/資本配置、估值/priced-in、成長耐久),每條 **cited**;
   算 **cycle_stage**(早/中/晚)+ **confidence**(從 4-KPI + 佐證數 + 距 kill + payoff + regime 契合;
   標「INITIAL, uncalibrated」直到有 track record)。
2. 在 `themes.yaml` 登記:ticker -> {confidence, cycle_stage, verdict, kill, wiki}。
3. `spine/providers.thesis_quality` 自動讀到 → tier-2 分數 = 資格 × confidence → `python backtest/scan.py` 看變化。

## confidence 是 INITIAL 直到校準
冷啟沒有 track record,confidence 是**有出處的初估**,不是真機率。**跑一段、戰績簿累積後,系統自動校準**
(DESIGN §6)。所以 pilot 的 confidence 數字**別當精確**,當「有紀律的相對強弱 + 週期溫度」。
