# track_record — agent 自我監控 log 的 schema(不是人的日記)

見 `DESIGN.md` §6。這是 **agent 自己的、機器可讀、append-only** log,系統**自動**寫入 + 讀取,用來
校準 confidence / 算 forward-IC / 期望值 / decay 偵測(自我修復)/ 餵新-thesis 驗證閘。**人不用它做
日常決策**;人唯一碰它 = 「採納新 thesis 類型」窄閘上的衍生摘要(且該閘可嚴格自動)。

## 檔案
`thesis/track_record.jsonl` — 每行一筆 JSON(append-only)。冷啟為空;系統每次吐 thesis 時 append,
之後結果窗到期時自動回填 outcome。

## 每筆 schema
```json
{
  "ts": "2026-07-01",             // 預測發出時間
  "thesis_id": "memory-supercycle",
  "ticker": "MU",
  "confidence": 0.35,             // 發出時的 confidence
  "cycle_stage": "late",
  "prediction": {"horizon_days": 63, "direction": "long", "note": "late-cycle, small size"},
  "kill_condition": "HBM capacity ramps ahead of demand OR pricing discipline breaks",
  "entry_ctx": {"px": 1154.3, "vs_200sma": 1.65, "regime": "risk_on"},
  "outcome": null                 // 之後自動回填:
  // "outcome": {"fwd_return": 0.08, "kill_fired": false, "realized_vs_pred": "hit"}
}
```

## 系統自動從它算(全機器,NHITL)
- **校準**:分桶 confidence → 實際命中率,「說 0.7 是否真 ~70%」→ 調 confidence 函數/校準映射。
- **forward-IC**:連續排序 vs 實際報酬(≥0.05 靶,背景健檢非閘)。
- **期望值 / 命中率 / CAR / kill 紀律**:凸 payoff(對=大贏、錯守 kill=小虧)。
- **decay 偵測**:live vs 期望 rolling 背離 → circuit-breaker / 停 sleeve(= `invariants` §自我修復)。
- **新-thesis 驗證閘**:新玩法的 track-record 過閘才准 live-sizing。

## 冷啟
現在 track_record 為空 → confidence 全是 INITIAL/uncalibrated。跑一段(數月、~20–30 筆)才有東西可校準。
