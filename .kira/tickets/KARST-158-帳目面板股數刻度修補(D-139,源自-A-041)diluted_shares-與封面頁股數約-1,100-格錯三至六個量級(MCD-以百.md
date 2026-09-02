---
id: KARST-158
title: 帳目面板股數刻度修補(D-139,源自 A-041):diluted_shares 與封面頁股數約 1,100 格錯三至六個量級(MCD 以百萬、COP/GRMN 以千、FTI 為 1.0),逐格校正出面板 v2(保留 v1 正本與變更紀錄,不改 companyfacts 原檔),然後只重跑 KARST-148 的「行內價值」一件作核對,結果留言於 148 票不重開
type: task
createdAt: 2026-09-02
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: panel-fix-158
deliverable: KARST-D02
---

## 工作內容

背景:KARST-156 發現面板 experiments/2026-09-02-fundamentals-panel/out/panel_monthly.parquet 的 diluted_shares 有單位刻度錯(A-041,見 .kira/assumptions.jsonl 與 research/2026-09-02-股數收縮.md 相關一節、experiments/2026-09-02-share-shrink/out/flagged_big_moves.csv);凡市值、每股數字、股數變化率都受影響,而 KARST-148 四件套的「行內價值」用市值(research/2026-09-02-四件套實測.md),其「無效」結論可信度待核。做法:①**診斷**:對每家公司每格 diluted_shares 與封面頁股數(dei:EntityCommonStockSharesOutstanding,原檔快取位置見面板建置報告),按公司自身時間序列找跳三個量級以上且非拆股(對照倉內拆股事件表)的格;另用「股價 × 股數 = 市值」對照倉內已知市值合理範圍(例如與同期 SPY 成份權重或既有市值快照粗對)標出離群格;列出錯格清單、疑似刻度倍數(10^3、10^6)與來源(companyfacts 該格的 unit/scale 欄或申報本身寫法)入 out/scale_fixes.csv。②**修補規則寫死**:只以 10 的整數次方校正、每格記錄原值/校正值/依據;判不出倍數的格設缺值不猜;拆股格不動。③**出 v2**:寫 out/panel_monthly_v2.parquet(v1 不動,gitignore 已覆蓋大檔),RULES.md 加「v2 變更紀錄」一節(錯格數、校正數、缺值數、規則),meta.json 加 v2 雜湊;所有下游票日後讀 v2,v1 只留追溯。④**核對重跑**:只重跑 148 的行內價值一件(照 experiments/2026-09-02-fourpiece-test/CRITERIA.md 原判準、原窗、原成本,不改一字),在 v1 與 v2 各跑一次,報兩版的年化/對基準差額/運氣帶位置差異;結論以 kira-ticket-ops comment 留言於 KARST-148(--as panel-fix-158),票不重開;若 v2 令價值一件由「無效」變「有量」,在留言首行寫明並通知主 agent,不自行改 D-129 判詞。⑤誠實聲明:校正依據是規則推斷不是原始申報核對;缺值格數;封面頁股數與攤薄股數口徑不同(在外 vs 加權攤薄)不可互替,只互相作刻度參照。

## 驗收條件

- [ ] out/scale_fixes.csv(每格原值/校正值/倍數/依據)與錯格統計齊;校正規則只用 10 的整數次方、判不出設缺值,寫入 RULES.md v2 變更紀錄
- [ ] panel_monthly_v2.parquet 出檔,v1 不動;meta.json 記 v2 雜湊與行數;RULES.md 註明下游改讀 v2
- [ ] 148 行內價值一件 v1/v2 各跑一次(原判準一字不改),差異表齊,結論留言於 KARST-148 票;若結論改變首行標明並回報主 agent
- [ ] 報告落 research/2026-09-02-面板股數刻度修補.md;腳本落 experiments/2026-09-02-panel-scale-fix/;原料不另存副本(D-134);commit 用 git commit --only -- <自己的檔>,不用私有 index;生產庫(倉根 C:\projects\Karst\karst.sqlite)只讀,SHA256 首 16 位維持 b168e9f45b578cf9

## 結果

## 留言
