# 15-theme confidence 最終遷移 diff 表(P2 收尾 + red-team 判決 + §4c 三通道)

> **狀態(2026-07-16 更新):✅ 已批准並已全量落地**(commit `0ac6f3f` "thesis: apply approved
> 15/15 confidence migration (P2 complete)")。本表由「提案」變成「已執行嘅決策記錄」——
> themes.yaml / wiki 15 個 theme 嘅 confidence 全部已切成本表嘅「最終建議」欄,lint P2 formula
> errors 7→0 機械驗收通過。
>
> ⚠️ **但 euv 一行事後被推翻**:`backtest/results/2026-07-16_crowding_asml_contamination.md`
> 證實本表 euv 用嘅 crowding=2.8 係污染讀數(ASML 最後 3 份 corpus「法說會」實為記者會/宣傳片,
> defeatbeta feed 2025-07-16 後轉咗文件類型)。euv 0.47 因此係假讀數;正確值視乎兩個未決:
> D1 淨修 → 0.406,紅隊判斷 → 0.250,而 D2(crowding 軸 temporal vs cross-sectional 建構效度)
> 係 DESIGN 層變更,等用戶拍板。**本表其餘 14 行不受影響。**
> **產出日期**:2026-07-16。**唯一新增檔**:本檔。
> **一句總結**:全部 confidence = `thesis/confidence_formula.py`(§4a 凍結公式)輸出,冇任何心算、冇任何酌情。
> red-team 殺傷力照 §4c 三通道機械分流(subscore / cap 資格 / magnitude 加成),**永不喺 confidence 數字度酌情郁**。

---

## 1. 方法

### 1.1 公式(DESIGN §4a 凍結,`thesis/confidence_formula.py` 唯一實作)
```
confidence_raw = (Σ 4-KPI subscores) / 8 × penalty(crowding_band, cycle_stage)
confidence     = min(confidence_raw, 0.30)   if n_sources == 1   (single-source cap)
               = confidence_raw               otherwise
subscore ∈ {0, 0.5, 1, 1.5, 2}
```
penalty 5×3 查表(crowding pctile 五帶 × cycle 三欄),逐格照 §4a;crowding band 左閉右開
(40→「40-60」、90→「≥90」);`event-driven` 映射到 mid 欄、`mid-late` 映射到 late 欄。
**本表所有 confidence / raw / penalty 均由 `confidence_formula.py` 逐個 `cf.confidence(...)` 計出**
(腳本 + 原始輸出見 §7),無一個係人手估。

### 1.2 subscore 來源(red-team 判決之後嘅最終值)
- **9 個 gooptions-sourced theme**(memory/photonics/ai-power/advanced-packaging/space/rare-earth/
  tpu/oil-gas/semicap):由各自 red-team 報告攞 red-team 後最終 moat/capital/valuation/growth。
  「生還」= 該格不變;「中彈」= 承重腿對應格降;「分岔」= 未證 magnitude 腿對應格降。
- **6 個 discovery-radar theme**(aerospace/euv/us-solar/gas-compression/specialty-siding/glp1):
  以 `2026-07-15_subscore_backfill_draft.md` §6 gatekeeper 裁決值為 baseline
  (gas-compression moat 1.5→1.0、gas capital 保留 1.0、siding 估值保留 0.5),再套各自
  2026-07-16 red-team 報告嘅調整(euv moat 補強 1.5→2.0、gas-compression growth 1.5→1.0 等)。
- **capital / valuation** 兩格全部係機械讀數(pe_pctile / P_base / 財務健康代理),red-team 協議不覆核。

### 1.3 crowding / cycle / n_sources / 現行 confidence 來源
- crowding:`thesis/.raw/crowding_composite.json` 之 `composite_pctile`(2026-07-13 generated)。
- cycle_stage、現行 confidence、n_sources:`thesis/themes.yaml`(theme-level ROLLUP)。
- **n_sources = themes.yaml `sources:` list 長度**。實測:**只有 ai-power-grid = 2**
  (gooptions-trend-core tier2 + `gev-balance-sheet-cash-backed-backlog` tier1,corroborates 承重),
  **其餘 14 個 theme 全部 = 1** → 受 single-source cap 0.30 綁。

### 1.4 已讀檔(read 日期 2026-07-16)
DESIGN.md §4a/§4c;confidence_formula.py;crowding_composite.json;themes.yaml;
15 份 red-team 報告(`2026-07-15_redteam_*` ×7、`2026-07-16_redteam_*` ×8);
`2026-07-15_subscore_backfill_draft.md`;`thesis/lint.py`(§7 對照)。

---

## 2. 15-theme 主表

subscores 欄格式 = moat / capital / valuation / growth。`公式 confidence` = 批准後應寫入 themes.yaml 嘅值。

| # | slug | red-team 判決 | subscores (m/c/v/g) | crowd | cycle | n_src | 公式 raw | cap | 公式 confidence | mag_unconf | 現行 conf | 最終建議 | Δ | 歸因 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | memory-supercycle | 中彈 | 1.5/1/1/1.5 | 24.8 | late | 1 | 0.469 | 綁 | **0.30** | 否 | 0.30 | 0.30 | +0.00 | 已合規 |
| 2 | photonics-optical | 中彈 | 1.5/1/0.5/2 | 57.1 | late | 1 | 0.406 | 綁 | **0.30** | 否 | 0.30 | 0.30 | +0.00 | 已合規 |
| 3 | **ai-power-grid** | 生還+補強 | 1.5/1/0.5/2 | 34.3 | late | **2** | 0.469 | **脫** | **0.47** | 否 | 0.33 | **0.47** | **+0.139** | 脫cap(GEV Tier-1 現金背書承重) |
| 4 | advanced-packaging | 中彈 | 1/1/0.5/2 | 48.1 | late | 1 | 0.366 | 綁 | **0.30** | 否 | 0.32 | 0.30 | −0.02 | cap 修正(0.32>cap 違規) |
| 5 | space-satellite | 中彈 | 1/1/0.5/1.5 | 59.9 | early | 1 | 0.475 | 綁 | **0.30** | **是**(超級週期三支柱) | 0.28 | 0.30 | +0.02 | penalty 標準化;殺傷落 sizing |
| 6 | rare-earth-materials | 分岔 | 1.5/1/1/1 | 97.8 | event-driven | 1 | 0.309 | 綁 | **0.30** | 否* | 0.28 | 0.30 | +0.02 | penalty 標準化 |
| 7 | tpu-custom-silicon | 中彈 | 1.5/1/0.5/1.5 | 46.5 | mid | 1 | 0.478 | 綁 | **0.30** | **是**(結構份額轉移) | 0.25 | 0.30 | **+0.050** | penalty 標準化;殺傷落 sizing |
| 8 | oil-gas-energy | 分岔/部分中彈 | 1/1/1/1 | 67.8 | late | 1 | 0.275 | 不綁 | **0.275** | **是**(SEI $1B 腿) | 0.25 | 0.275 | +0.025 | penalty 標準化 |
| 9 | **semicap-equipment** | 分岔 | 1/0.5/0/1 | 40.7 | late | 1 | 0.203 | 不綁 | **0.203** | **是**(耐久 toll 腿) | 0.20 | 0.20 | +0.003 | red-team growth 1.5→1 中彈,抵銷 formula 上拉 |
| 10 | aerospace-specialty-alloys | 部分中彈 | 1.5/1/0/1 | 78.6 | late | 1 | 0.241 | 不綁 | **0.24** | 否 | 0.24 | 0.24 | +0.001 | 已近合規 |
| 11 | **euv-lithography-monopoly** | 生還+補強 | 2/1.5/0/1.5 | 2.8 | late | 1 | 0.469 | 綁 | **0.30** | 否 | 0.22 | **0.30**(n=1)／**0.47**(n=2 若登記) | **+0.08 / +0.25** | subscore backfill+補強;**脫cap 非 null-op**(報告 crowding 用錯) |
| 12 | us-solar-manufacturing | 分岔 | 1.5/1.5/2/1.5 | 76.0 | mid | 1 | 0.609 | 綁 | **0.30** | **是**(durability 腿) | 0.32 | 0.30 | −0.02 | cap 修正(0.32>cap 違規) |
| 13 | gas-compression-equipment | 部分中彈 | 1/1/2/1 | 88.9 | early | 1 | 0.469 | 綁 | **0.30** | **是**(AI-gas magnitude 腿) | 0.33 | 0.30 | −0.03 | cap 修正 + §6 moat 1.5→1 |
| 14 | specialty-siding-pricing-power | 分岔 | 1/1/0.5/1 | 97.2 | mid | 1 | 0.241 | 不綁 | **0.24** | **是**(2x share-shift 腿) | 0.20 | 0.24 | +0.041 | subscore backfill |
| 15 | glp1-biologics-packaging | 生還 | 1.5/1.5/1/2 | 95.3 | mid | 1 | 0.413 | 綁 | **0.30** | 否 | 0.27 | 0.30 | +0.03 | subscore backfill |

**cap 欄**:`綁` = n=1 且 raw>0.30,cap 實際壓低到 0.30;`不綁` = n=1 但 raw<0.30,cap 無效果(confidence=raw);`脫` = n=2 且 Tier-1 擊中承重,confidence=raw。
**rare-earth `否*`**:red-team 未加 `magnitude_unconfirmed`;事件二元(2026-11-27 休戰到期)風險已由 `magnitude_tier: 5-10x-binary` 承擔,§4a 明令唔准喺 penalty 再折一次。

### 摘要
- **移動 |Δ|≥0.05:3 個** —— ai-power +0.139、euv +0.080、tpu +0.050(euv 若登記 Tier-1 → 潛在 +0.25)。
- **最大移動**:ai-power +0.139(現狀 n=2 已脫 cap);潛在最大 = euv +0.25(需 gatekeeper 決定登記 Tier-1)。
- **脫 cap**:現狀 1 個(ai-power,themes.yaml 已 n=2);euv 資格合格但未登記(潛在第 2 個)。
- **magnitude_unconfirmed:7 個** —— space、tpu、oil-gas、semicap、us-solar、gas-compression、specialty-siding。
- 其餘 8 個(memory/photonics/ai-power/advanced-packaging/rare-earth/aerospace/euv/glp1)無新 magnitude flag。

---

## 3. 大幅移動者(|Δ|≥0.05)逐個歸因

### 3.1 ai-power-grid：0.33 → 0.47(+0.139,**脫 cap**)
- 唯一喺 themes.yaml 已登記第二獨立源(GEV balance-sheet Current Deferred Revenue $18.7B→$31.8B,
  現金背書承重供給腿)→ n_sources=2 → **脫 single-source cap**,confidence = raw = 0.469。
- subscores 未變(red-team 生還:moat 1.5 齋引用升格 Level-2 生還,但商品氣/電網段稀釋 → 唔升 2)。
- 歸因類別:**脫cap**(非 subscore 變、非 penalty 變)。呢個係「補強 → 脫 cap 且 raw>cap」通道真正見效嘅乾淨案例。

### 3.2 euv-lithography-monopoly：0.22 → 0.30(+0.08,n=1);潛在 → 0.47(+0.25,n=2)
- **兩層歸因**:(a) subscore backfill + red-team 補強(moat 1.5→2.0:承重經 Level-2 生還兼雙 Tier-1
  現金背書+16 年約束語言 transcript 獨立擊中);(b) crowding 修正暴露 cap escape 係**實質、非 null-op**。
- **關鍵更正 — red-team 報告 null-op 結論無效**:`2026-07-16_redteam_euv_lithography.md` 判「脫 cap 但
  null-op」,理由係佢**假設 ASML most-consensus crowding ≥90 → penalty ~0.40 → raw ~0.25 < 0.30 cap**。
  但 `crowding_composite.json` 實際 euv **composite_pctile = 2.8**(ASML 單票 analyst-attendance 分位極冷),
  band `<40`、cycle late → **penalty = 0.75**。用真 crowding:raw = 5.0/8 × 0.75 = **0.469**,遠 > 0.30 cap。
  → **cap 對 euv 係綁緊嘅**,脫 cap 會由 0.30 拉到 0.469,**唔係 null-op**。報告自己 line 196-197
  已 flag「crowding penalty 具體檔位應由 crowding_composite.py 讀返」,只係佢冇料到會低到 2.8。
- **landing 決策點(交 gatekeeper)**:euv 現 themes.yaml n=1 → 機械修正 = 0.30(+0.08,同時修 lint、
  升返偏保守嘅 0.22)。**若接受 red-team 建議登記雙 Tier-1**(sources 加 tier1 條目 + corroborates 承重)
  → n=2 → **0.47**。同 ai-power 完全對稱。保守版(若 gatekeeper 唔收 moat 2/cap 1.5/growth 1.5 補強、
  只用 backfill baseline m1.5/c1/v0/g1):n=2 → 0.328。**建議**:與 ai-power 一致處理——red-team 既判雙
  Tier-1 獨立擊中承重,理應登記脫 cap = **0.47**;至少唔可以照報告當 null-op 留喺 0.30。

### 3.3 tpu-custom-silicon：0.25 → 0.30(+0.050,penalty 標準化 + cap)
- 純粹遷移向上:舊手工 0.25 偏保守,公式 raw 0.478(crowding 46.5「40-60」× mid = penalty 0.85)被 cap 綁 0.30。
- red-team **中彈**(結構份額轉移未證)照 §4c **落 subscore 通道**(growth 2→1.5),但 raw 仍 0.478 >> cap
  → confidence 唔動(0.30);殺傷力**唔喺 confidence**,喺 magnitude 通道(share-shift 腿標 magnitude_unconfirmed)。
- 歸因類別:**penalty 標準化**(confidence 升);red-team 殺傷**改道去 sizing**(見 §4.2)。

> 註:specialty-siding +0.041 差少少入唔到 0.05 門檻,但係 subscore backfill 帶動嘅第 4 大真移動,§4.3 一併講。

---

## 4. 特別 flag 案例

### 4.1 ai-power(脫 cap → 應升 0.47)
確認:0.33 → **0.47**。呢個係唯一「本來就有 n=2 登記」嘅 theme,公式直接俾 raw。用戶提出嘅「0.33 應升 0.47?」
答案 = **係**,前提係 GEV 條目已喺 themes.yaml sources(已核實 line 344-350,corroborates 承重腿)。

### 4.2 tpu / space(red-team 向下 vs 公式 cap 向上 —— §4c 解)
- 表面矛盾:red-team 判「向下」(事實唔夠硬),公式遷移判「向上」(舊估太保守)。
- §4c 標準化解法:**confidence 跟公式**(tpu 0.30、space 0.30,penalty 標準化拉上 cap),
  **red-team 殺傷力落 magnitude 通道**——
  - tpu:結構份額轉移腿 → node 標 `magnitude_unconfirmed: true`(toll-booth 已證那半唔標)。
  - space:超級週期三支柱(backlog / Golden Dome / VC)降級為敘事 → 標 `magnitude_unconfirmed: true`
    (§4c 正文明確點名 space 三支柱為 magnitude 未證案例)。
- 淨效果:信心標準化(可審計、唔酌情),但賭注唔會因為標準化就自動放大(sizing v2 對呢兩個 node 收起 magnitude 加成)。

### 4.3 semicap(唯一 red-team 實質壓 confidence 嘅 theme)
- 唯一一個 red-team **subscore 中彈落到 cap 以下**、真正機械帶低 confidence 嘅 case:
  growth 1.5 → 1.0(FY26 營收實跌、兌現全靠 FY27 前瞻指引)→ raw 由 0.244 跌到 **0.203**。
- 對照:若淨做「純 formula 遷移」用現行 wiki 舊 subscores(growth 1.5),lint 報 0.2438 → 會升到 **0.24**;
  但接受 red-team growth 1.5→1.0 後 = **0.20**,即 red-team 中彈**抵銷**咗 formula 上拉,confidence 停喺 0.20。
- 額外殺傷:耐久 toll 腿($130-150M+ 靠前瞻指引)標 `magnitude_unconfirmed: true`(sizing 層再收注)。
- 歸因類別:**red-team 中彈**(唯一 subscore 通道實質見效嘅 theme)。

### 4.4 euv(脫 cap 非 null-op)—— 見 §3.2
最重要一個更正:**唔好照 red-team 報告當 euv 脫 cap = null-op**。真 crowding 2.8 → raw 0.469 > cap,
脫 cap 由 0.30 拉到 0.47。呢個係全表**潛在最大單一移動**,交 gatekeeper 決定登記 Tier-1 與否。

---

## 5. lint 對照(`thesis/lint.py`,2026-07-16 跑)

跑法:`PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python thesis/lint.py`。lint 報:
- **P2 formula lint ERRORS = 7**(wiki subscores 套公式 ≠ themes.yaml confidence,MUST fix)。
- **P2 formula lint warnings = 6**(6 個 discovery-radar theme:wiki「## confidence 推導」段機讀唔到 4 個
  `KPI X/2` subscores,lint 略過 → 唔入 7 error,要 landing 時補機讀格式)。
- **ADMISSION single-source cap warnings = 3**(advanced-packaging / us-solar / gas-compression:sources=1 但
  confidence>0.30 cap)。

lint 嘅 7 個 error 用嘅係**現行 wiki 舊 subscores**(未貼 red-team 判決),**我張表就係修佢哋嘅方案**:

| lint error theme | lint 用 wiki subscores | lint formula conf | 我表最終建議 | 關係 |
|---|---|---|---|---|
| ai-power-grid | 1.5/1/0.5/2 (n=2) | 0.4688 | **0.47** | 一致 ✓ |
| advanced-packaging | 2/1/0.5/2 (n=1) | 0.30 (raw 0.447) | **0.30** | 一致 ✓(我用 red-team moat 2→1,兩者皆 cap 0.30) |
| space-satellite | 1/1/0.5/2 (n=1) | 0.30 (raw 0.534) | **0.30** | 一致 ✓(我用 growth 2→1.5,皆 cap 0.30) |
| rare-earth-materials | 1.5/1/1/1.5 (n=1) | 0.30 (raw 0.344) | **0.30** | 一致 ✓(我用 growth 1.5→1,皆 cap 0.30) |
| tpu-custom-silicon | 1.5/1/0.5/1.5 (n=1) | 0.30 (raw 0.478) | **0.30** | 一致 ✓ |
| oil-gas-energy | 1/1/1/1 (n=1) | 0.2750 | **0.275** | 一致 ✓ |
| semicap-equipment | 1/0.5/0/1.5 (n=1) | 0.2438 | **0.20** | **差異**:我用 red-team growth 1.5→1.0 → 0.203。lint 用舊 growth 1.5 → 0.244 |

**唯一數字差異 = semicap**:lint(舊 wiki subscores)修出 0.24,我(red-team 判決後)修出 0.20。
理由 = §4.3 red-team growth 中彈。landing 時 semicap wiki subscores 要由 growth 1.5 改 1.0,themes.yaml
confidence 由 0.20 維持 0.20(公式 0.203 四捨到 0.20),lint 之後會用新 subscores 過 clean。

**6 個 discovery-radar theme**(aerospace/euv/us-solar/gas-compression/specialty-siding/glp1)唔喺 7 error
入面(lint 因 wiki 未機讀而略過),landing 要:(a) wiki「## confidence 推導」段補 `moat X/2 / capital X/2 /
valuation X/2 / growth X/2` 四行機讀格式;(b) themes.yaml confidence 改成本表值。改完 lint formula error 應歸 0。

---

## 6. 落地清單(gatekeeper 批准後切數字用)

themes.yaml confidence 行號已核實(2026-07-16)。wiki 路徑 = `thesis/wiki/<slug>.md` 之「## confidence 推導」段。

| slug | themes.yaml conf 行 | 現值→新值 | wiki 推導段要改乜 |
|---|---|---|---|
| memory-supercycle | 74 | 0.30→0.30 | 無(已合規);subscores 確認 1.5/1/1/1.5 |
| photonics-optical | 148 | 0.30→0.30 | 無(已合規);subscores 確認 1.5/1/0.5/2 |
| ai-power-grid | 246 | **0.33→0.47** | subscores 1.5/1/0.5/2 已機讀;確認脫 cap(n=2),記 raw=0.469 |
| advanced-packaging | 436 | 0.32→0.30 | moat 2→1(red-team 中彈,可交易 OSAT 唔捕捉租金);raw 0.366、cap 0.30 |
| space-satellite | 551 | 0.28→0.30 | growth 2→1.5(耐久腿侵蝕);node 加 `magnitude_unconfirmed: true`(三支柱)+ red_team 段 |
| rare-earth-materials | 704 | 0.28→0.30 | growth 1.5→1(分岔:兌現未到);raw 0.309、cap 0.30 |
| tpu-custom-silicon | 779 | 0.25→0.30 | growth 2→1.5(份額轉移未證);AVGO node 加 `magnitude_unconfirmed: true` + red_team 段 |
| oil-gas-energy | 888 | 0.25→0.275 | subscores 1/1/1/1;SEI 腿標 `magnitude_unconfirmed`(theme 現 flat,per-node 化時落) |
| semicap-equipment | 972 | 0.20→0.20 | **growth 1.5→1.0**(FY26 實跌);node 加 `magnitude_unconfirmed: true` + red_team 段;raw 0.203 |
| aerospace-specialty-alloys | 1025 | 0.24→0.24 | wiki 補 4 行機讀 subscores 1.5/1/0/1;raw 0.241 |
| euv-lithography-monopoly | 1079 | **0.22→0.30(n=1)/ 0.47(若登記 Tier-1→n=2)** | wiki 補 4 行 subscores 2/1.5/0/1.5;**gatekeeper 決定**係咪 sources 加雙 Tier-1 條目(現金背書 down-payment + 16 年約束語言)+ corroborates 承重;更正報告 null-op 誤判 |
| us-solar-manufacturing | 1125 | 0.32→0.30 | wiki 補 4 行 subscores 1.5/1.5/2/1.5;node 標 `magnitude_unconfirmed`(durability 腿);cap 0.30 |
| gas-compression-equipment | 1178 | 0.33→0.30 | wiki 補 4 行 subscores 1/1/2/1(§6 moat 1.5→1、red-team growth 1.5→1);node 標 `magnitude_unconfirmed`(AI-gas 腿) |
| specialty-siding-pricing-power | 1230 | 0.20→0.24 | wiki 補 4 行 subscores 1/1/0.5/1;node `siding-segment-diluted` 標 `magnitude_unconfirmed`(2x share-shift 腿);raw 0.241 |
| glp1-biologics-packaging | 1270 | 0.27→0.30 | wiki 補 4 行 subscores 1.5/1.5/1/2;raw 0.413、cap 0.30 |

**批准後驗證**:重跑 `thesis/lint.py`,P2 formula ERRORS 應由 7 → 0、single-source cap warnings 由 3 → 0
(advanced-packaging/us-solar/gas-compression 全部落返 ≤0.30);唯一 `magnitude_unconfirmed` 相關檢查要求
每個標記 node 嘅 wiki 有對應 red_team 段(space/tpu/semicap/us-solar/gas-compression/specialty-siding/oil-gas)。

---

## 7. 附錄:計算腳本原始輸出

腳本 `scratchpad/compute_diff.py`(import `confidence_formula as cf`,逐個 `cf.confidence(subscores, crowding, cycle, n_sources)`),
`PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python` 跑出:

```
slug                            m/c/v/g          crowd cyc           n   pen     raw  cap?   conf   cur  delta
memory-supercycle               1.5/1.0/1.0/1.5   24.8 late          1  0.75  0.4688  True  0.300  0.30 +0.000
photonics-optical               1.5/1.0/0.5/2.0   57.1 late          1  0.65  0.4062  True  0.300  0.30 +0.000
ai-power-grid                   1.5/1.0/0.5/2.0   34.3 late          2  0.75  0.4688 False  0.469  0.33 +0.139
advanced-packaging              1.0/1.0/0.5/2.0   48.1 late          1  0.65  0.3656  True  0.300  0.32 -0.020
space-satellite                 1.0/1.0/0.5/1.5   59.9 early         1  0.95  0.4750  True  0.300  0.28 +0.020
rare-earth-materials            1.5/1.0/1.0/1.0   97.8 event-driven  1  0.55  0.3094  True  0.300  0.28 +0.020
tpu-custom-silicon              1.5/1.0/0.5/1.5   46.5 mid           1  0.85  0.4781  True  0.300  0.25 +0.050
oil-gas-energy                  1.0/1.0/1.0/1.0   67.8 late          1  0.55  0.2750  True  0.275  0.25 +0.025
semicap-equipment               1.0/0.5/0.0/1.0   40.7 late          1  0.65  0.2031  True  0.203  0.20 +0.003
aerospace-specialty-alloys      1.5/1.0/0.0/1.0   78.6 late          1  0.55  0.2406  True  0.241  0.24 +0.001
euv-lithography-monopoly        2.0/1.5/0.0/1.5    2.8 late          1  0.75  0.4688  True  0.300  0.22 +0.080
us-solar-manufacturing          1.5/1.5/2.0/1.5   76.0 mid           1  0.75  0.6094  True  0.300  0.32 -0.020
gas-compression-equipment       1.0/1.0/2.0/1.0   88.9 early         1  0.75  0.4688  True  0.300  0.33 -0.030
specialty-siding-pricing-power  1.0/1.0/0.5/1.0   97.2 mid           1  0.55  0.2406  True  0.241  0.20 +0.041
glp1-biologics-packaging        1.5/1.5/1.0/2.0   95.3 mid           1  0.55  0.4125  True  0.300  0.27 +0.030

-- euv IF dual Tier-1 registered (n_sources=2) --
euv n=2: raw=0.4688 cap_applied=False conf=0.4688
euv backfill-baseline (m1.5 c1 v0 g1, n=1): raw=0.3281 conf=0.3000
```
