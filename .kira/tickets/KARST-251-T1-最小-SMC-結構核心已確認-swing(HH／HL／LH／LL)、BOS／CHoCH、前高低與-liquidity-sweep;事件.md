---
id: KARST-251
title: T1 最小 SMC 結構核心:已確認 swing(HH／HL／LH／LL)、BOS／CHoCH、前高低與 liquidity sweep;事件帶形成／確認／失效時間;prefix replay 防前視;與現有支阻及圖表整合
type: task
createdAt: 2026-09-19
risk: high
model: opus
fits: 一程做得完:一個新模組(結構事件)、charts 疊加與 derived 輸出、一份 replay 測試;不做 internal／OB／FVG
dependsOn: []
claimedBy: Fable主腦
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依 strategy/specs/SMC與TA工具箱-ClaudeCode執行計劃-v1.md §4.2 表首三行。新模組 karst/structure.py(名稱可依既有慣例):以既有 confirmed pivot(charts.pivot_zones 的左右對稱窗口)為 swing 定義並明示與 LuxAlgo leg 不同;每個 swing 標 HH／HL／LH／LL 與趨勢狀態;BOS／CHoCH 以已確認 swing level 的收線突破判定,首次建立結構或方向不明不標 CHoCH;前高／前低與等高等低(容差按 ATR 比例可配置)及 liquidity sweep(收線 bar wick 越界、close 回原側;跨 bar reclaim 另有窗口);每個事件保存 anchor_time、confirmed_at、timeframe、方向、價位／區域、定義與參數版本、狀態轉換與失效條件;provisional 與 confirmed 分開。整合:charts.render 在日／週圖疊加影響判斷的結構(最近的 BOS／CHoCH、前高低、sweep),與現有支阻聚類分清圖例;事件列表入 derived.json;不畫全部歷史事件。驗收用逐步增加 bar 的 prefix replay:截至某時已確認的事件不因後來 bar 改寫,只追加狀態;涵蓋趨勢、箱體、假突破、缺口、最後一根未收線。每項能力在模組 docstring 一句寫明補了現有 pivot／支阻的哪個缺口(觸發、失效、等待或漏看)。不加 internal structure、Order Block、FVG、AVWAP、Volume Profile、Squeeze、自動形態、RS 引擎。程式只住 karst/,不含股票身份;測試 fixture 用合成序列。

## 驗收條件

- [ ] structure 模組對合成日線序列輸出 swing 序列(HH／HL／LH／LL)、BOS／CHoCH、前高低、sweep 事件,每個事件含 anchor_time、confirmed_at、timeframe、方向、價位、參數版本、狀態;首次建立結構不標 CHoCH
- [ ] prefix replay 測試:對序列逐根增加 bar,任何在 t 已 confirmed 的事件在 t+k 的輸出中 anchor／confirmed_at／價位不變,只可追加狀態(touched／invalidated);最後一根未收線的候選只標 provisional
- [ ] 假突破案例:wick 越過前高、收回原側者標 sweep 而非 BOS;收線越過者標 BOS;箱體案例不產生 CHoCH
- [ ] charts.render 日／週圖疊加最近結構事件並與支阻聚類圖例分清;derived.json 帶事件列表;現有 charts／chart_images／publish_bars 測試全部通過
- [ ] 模組 docstring 寫明每項能力補足的既有缺口;PYTHONUTF8=1 全套測試通過

## 結果

## 留言
