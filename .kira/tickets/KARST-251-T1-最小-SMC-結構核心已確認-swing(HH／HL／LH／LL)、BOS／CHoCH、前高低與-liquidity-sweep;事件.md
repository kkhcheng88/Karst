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
closed: 2026-09-19
---

## 工作內容

依 strategy/specs/SMC與TA工具箱-ClaudeCode執行計劃-v1.md §4.2 表首三行。新模組 karst/structure.py(名稱可依既有慣例):以既有 confirmed pivot(charts.pivot_zones 的左右對稱窗口)為 swing 定義並明示與 LuxAlgo leg 不同;每個 swing 標 HH／HL／LH／LL 與趨勢狀態;BOS／CHoCH 以已確認 swing level 的收線突破判定,首次建立結構或方向不明不標 CHoCH;前高／前低與等高等低(容差按 ATR 比例可配置)及 liquidity sweep(收線 bar wick 越界、close 回原側;跨 bar reclaim 另有窗口);每個事件保存 anchor_time、confirmed_at、timeframe、方向、價位／區域、定義與參數版本、狀態轉換與失效條件;provisional 與 confirmed 分開。整合:charts.render 在日／週圖疊加影響判斷的結構(最近的 BOS／CHoCH、前高低、sweep),與現有支阻聚類分清圖例;事件列表入 derived.json;不畫全部歷史事件。驗收用逐步增加 bar 的 prefix replay:截至某時已確認的事件不因後來 bar 改寫,只追加狀態;涵蓋趨勢、箱體、假突破、缺口、最後一根未收線。每項能力在模組 docstring 一句寫明補了現有 pivot／支阻的哪個缺口(觸發、失效、等待或漏看)。不加 internal structure、Order Block、FVG、AVWAP、Volume Profile、Squeeze、自動形態、RS 引擎。程式只住 karst/,不含股票身份;測試 fixture 用合成序列。

## 驗收條件

- [x] structure 模組對合成日線序列輸出 swing 序列(HH／HL／LH／LL)、BOS／CHoCH、前高低、sweep 事件,每個事件含 anchor_time、confirmed_at、timeframe、方向、價位、參數版本、狀態;首次建立結構不標 CHoCH
- [x] prefix replay 測試:對序列逐根增加 bar,任何在 t 已 confirmed 的事件在 t+k 的輸出中 anchor／confirmed_at／價位不變,只可追加狀態(touched／invalidated);最後一根未收線的候選只標 provisional
- [x] 假突破案例:wick 越過前高、收回原側者標 sweep 而非 BOS;收線越過者標 BOS;箱體案例不產生 CHoCH
- [x] charts.render 日／週圖疊加最近結構事件並與支阻聚類圖例分清;derived.json 帶事件列表;現有 charts／chart_images／publish_bars 測試全部通過
- [x] 模組 docstring 寫明每項能力補足的既有缺口;PYTHONUTF8=1 全套測試通過

## 結果

karst/structure.py 結構事件引擎(swing HH／HL／LH／LL、BOS／CHoCH、前高低、equal levels、sweep;形成／確認／狀態時間分開,定義 karst.structure/1)+ 日／週／近期圖疊加與 derived.json 輸出;prefix replay 證無前視。23 個新測試,全套 359 通過;commit b2ef423。internal／OB／FVG 依規格押後。詳見留言。

## 留言

### agent:Fable主腦 · 2026-09-19 02:43
2026-09-19 完成(Opus 實作、Fable 覆核合併,commit b2ef423)。新模組 karst/structure.py:swing 沿用既有左右對稱 confirmed pivot(docstring 明寫與 LuxAlgo leg 不同)標 HH／HL／LH／LL;趨勢只由已確認突破推動;BOS = 收線越過最近已確認 swing 位且順趨勢;CHoCH = 逆已成立趨勢的第一次收線突破,趨勢未明永不標;sweep 分 same_bar(影線越過收回、level 轉 touched)與 cross_bar_reclaim(窗口內收回、原突破轉 invalidated);equal_levels 容差 = atr_multiple × ATR(預設 0.25);前高低帶 broken_at／retested_at 令突破、回踩、sweep 分得清。每事件帶 event_id、anchor_time、confirmed_at、status／status_at、invalidation、definition karst.structure/1、refs、zone_ref。引擎每根 bar 先對「之前已可知」的 level 判突破,再收該根確認的 pivot,故無前視;ReplayTests 對五條合成序列逐根重播,已確認事件各格不變、status 只准向前、confirmed_at 不晚於輸入最後一根;另有週線逐日重播證明週未收不出要收回的判斷。charts.render 在日／週／近期圖疊加最近結構(events_kept 預設 12),圖例與支阻帶分開,derived.json 各 view 帶 structure;charts.atr 改為呼叫 structure.atr_series(ATR 定義只剩一份)。reclaim_window 預設 2(看實際圖後由 5 改,免把回踩蓋成失效);突破被收回不回滾趨勢(回滾等於改寫歷史)。23 個新測試,全套 359 通過。未做(規格押後):internal structure、Order Block、FVG、AVWAP、Volume Profile、Squeeze、自動形態、RS 引擎。名詞 結構事件 已入 CONTEXT.md。
