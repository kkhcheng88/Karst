# Karst Dashboard 設計書 v3【Fable 5,2026-07-12】

> 交付物 5(任務書 §7)。取代 `docs/2026-07-03_dashboard_decision_experience.md` 同
> `docs/2026-07-06_dashboard_design.md`(兩份都係 Phase-3 新機制上線前寫,已過時)。
> WS5 §5 嘅「一頁四格」需求係本檔嘅子集——本檔按 2026-07-12 現況(15 主題、per-node、
> 裁判 live、magnifier queue)+ 投資邏輯總審查(`2026-07-12_fable_investment_logic_review.md`)
> 嘅建議重新設計。**設計對象:一個傳奇交易員每朝早 90 秒內答到「今日使唔使做嘢」。**

---

## 0. 五條設計原則(邊樣先上主版嘅裁決標準)

1. **每個格仔必須答一條「今日使唔使郁手」嘅問題**。答唔到嘅資訊(歷史曲線、裝飾圖表、
   per-ticker 價格圖)一律落 drill-down 或者唔要(broker app 有嘅嘢唔重複)。
2. **排序按 action gap,唔係按 confidence**。個 dashboard 係行動清單,唔係榮譽榜——
   「目標注碼 vs 實際持倉」差距最大嗰行排最頂。
3. **Core 只配四個數**。Core playbook 設計上係每日 1 分鐘(§5 core v2),dashboard 唔應該
   俾佢多過一條橫條;衛星先係需要版面嘅嗰個。
4. **風險讀數講錢,唔講百分比**。「ai-capex 集中度 54.9%」冇人知點反應;
   「ai-capex kill 齊 fire = −$X」先係決策語言。
5. **狀態燈只有三色,而且「灰」係一種成就**。大部分日子所有格應該係灰(冇嘢做)——
   個 dashboard 嘅成功指標係「平日 90 秒關掉,異常日 10 秒內見到邊度出事」。

---

## 1. 版面(一頁四行 + drill-down)

```
┌─ ROW 0 今日行動條 ──────────────────────────────────────────────────────┐
│ CORE: SPY>200SMA ✓ | QQQ>200SMA ✓ | Roll T-42d | Top-up T-12d          │
│ KILL 觸發: 0 | 危機sleeve: DISARMED(VIX 16.2) | 裁判: PRELIM 0/60     │
├─ ROW 1 風險條 ─────────────────────────────────────────────────────────┤
│ ai-capex kill情境: −$7.2k(部署35%) | 部署 $20.5k/上限$20.5k          │
│ beta化警戒: 0 theme | 數據哨兵: OK | crypto ladder: ⚠未接管(61%資產) │
├─ ROW 2 主題作戰台(按 |target−current| 排)───────────────────────────┤
│ theme | conf | mag | stage | 擁擠 | exp-gap | target$→current$ | Δ | kill距離 | 新鮮度 │
│ (15 行,部署中嘅行加粗;watch-only 行摺埋預設唔展開)                  │
├─ ROW 3 學習迴路 + 隊列 ────────────────────────────────────────────────┤
│ IC進度: matured 0/60(首判決 ~10月) | Brier: −(未接) |               │
│ 隊列: PENDING 2 | magnifier 3 | constraint 警報 1 | IMA週任務 2/4      │
└────────────────────────────────────────────────────────────────────────┘
每行 theme 名 = link → drill-down(wiki 頁 + node 表 + 最新證據 + kill 全文)
```

## 2. 逐格規格(數據源全部係現有碎片,冇一個要新起)

### ROW 0 今日行動條(開波 10 秒)

| 元素 | 內容 | 數據源 | 變色規則 |
|---|---|---|---|
| Core 閘 ×2 | SPY/QQQ 收市 vs 200SMA + 距離 % | `playbook_log.txt`(05:40 job 已出)| cross 發生 → 紅(T+1 要執行 R1/R2);距 200SMA <1% → 黃(聽日可能 cross)|
| Roll 倒數 | LEAP 剩餘交易日(兩 leg 取小)| 同上 | ≤63td → 黃 + 「R4 今週」|
| Top-up 倒數 | 距下個月首交易日 | 日曆 | 當日 → 黃(R3,5 分鐘)|
| Kill 觸發 | 昨夜/今晨有冇 kill 事實成立 | `theme_signal.py` verdict + 夜班 queue | ≥1 → 紅(全版最高優先;T+1 全離場冇裁量)|
| 危機 sleeve | ARM/ENTER 狀態機 | VIX 讀數(05:30 批次)| VIX>40 → ARM 黃;回落<30 → ENTER 綠(WS2 規則)|
| 裁判 | 狀態 + matured 進度 | `thesis/ic_report.json` | FAIL → 紅(熔斷:部署上限自動砍 25%)|

**premarket 疊加**:20:30 HKT `premarket_log.txt` 已有——開市前睇嘅係同一條 ROW 0,
數字換 premarket 版(dip/covered-call/200SMA 觸發預覽),唔另開版面。

### ROW 1 風險條(每週認真睇一次,平日掃一眼)

| 元素 | 內容 | 數據源 | 變色 |
|---|---|---|---|
| **Kill-scenario VaR** | 每個 ≥2 主題嘅 meta_factor:「kill 齊 fire 蝕幾多 $」(用審查檔嘅 downside 表:late/priced −50%、binary −80%、其他 −35% × 實際持倉)| `concentration.py` 群組 × ledger 持倉 | 單一 meta_factor 情境損失 > 部署額 60% → 黃;>75% → 紅 |
| 部署 vs 上限 | $ 部署 / 現行狀態上限(PRELIM 50%)| `sizing.py` | 超 → 紅(唔應該發生,發生 = 有嘢冇跟規矩)|
| Beta 化警戒 | 126d rolling corr>0.9 嘅 theme 數 | `beta_check.py`(SUN 08:15 已排程)| ≥1 → 黃(除牌候選)|
| 數據哨兵 | yfinance 新鮮度/跨源抽查(architecture §5 #3)| 05:30 批次頂行 | 異常 → 紅(當日所有訊號唔可信——呢個燈紅,其他燈全部作廢)|
| Crypto ladder | 階梯狀態/距下個觸發價 | 手動 config(P0-3 落地前顯示「未接管」警告)| 未接管 → 常駐 ⚠(專登乞人憎——佢係全組合最大無掩護風險)|

### ROW 2 主題作戰台(核心版面,月度 sizing 日先逐行睇)

一行一 theme,欄位同來源:

| 欄 | 來源 | 備註 |
|---|---|---|
| conf | `themes.yaml` | 靜態 |
| mag tier | `themes.yaml` nodes(冇 node 嘅 theme 顯示 theme 級估)| P2-1 推廣後齊 |
| stage | `themes.yaml` | early 行有 ⚡ 標記(早=買得爽,WS5 §0)|
| 擁擠 | 三輸入複合(analyst 出席數 pctile / GS flow Z / bull-ratio)| P1-2 落地前先顯示 bull-ratio |
| exp-gap | 正/中/負 三值 | P1-1 落地前顯示「—」,唔好用 PE 分位濫竽充數 |
| target→current | `sizing.py` final$ vs ledger 實倉 | **排序鍵 = |差|**;ledger 未起前 current 手填 |
| Δ 行動 | BUY $x / TRIM $x / — | 差 <$500 顯示 —(唔好為執粒數 churn)|
| kill 距離 | 質性三檔:遠/近/⚠(夜班 draft 判)| 來自 magnifier/constraint queue 判讀 |
| 新鮮度 | 距 last_evidence 日數 | >90d → 黃(120d 過期降級規則嘅前哨)|

Watch-only 主題(WATCH 4 隻 + confidence 除名者)預設摺埋一行「watchlist (4)」。

### ROW 3 學習迴路 + 隊列(信任係賺返嚟——進度要見得到)

- **IC 進度條**:matured n/60 + 預計首判決月份(而家 0/60、~10 月)——呢條進度條存在嘅
  意義係提醒「而家所有 confidence 都係未經校準嘅排名分」,直到佢行完。
- **Brier 讀數**(P0-2 落地後):滾動 20 個已判 milestone 嘅 Brier + 「講 0.7 中幾多」表。
- **隊列深度**:`_PENDING_ANALYSIS.md` 未剔數 / `magnifier_review_queue.md` 未 confirm 數 /
  `constraint_scan_queue.md` 新警報數——三個數字,唔展開內容;>5 累積 → 黃(自動化在產出
  但人手 confirm 塞緊車,NHITL 嘅「H」嗰粒卡咗)。
- **IMA 週任務**:4 條 prompt 本週完成 tick(STATUS 表搬上屏)。

### Drill-down(點 theme 名先開)

wiki 頁 + node 表 + 最近 3 條 cited 證據 + kill_condition 全文 + 該 theme 嘅 prediction
track(講過乜、中過乜)。**Drill-down 先係擺曲線圖嘅地方**(theme basket vs 板塊 ETF
相對走勢——beta_check 數據現成)。

---

## 3. 使用儀式(邊個頻率睇邊行)

| 頻率 | 睇乜 | 時間 |
|---|---|---|
| 每朝(必)| ROW 0 五粒燈。全灰 = 熄機。 | 10-90 秒 |
| 開市前(可選)| ROW 0 premarket 版 | 30 秒 |
| 每週日(SUN 08:xx 批次跑完後)| ROW 1 全行 + ROW 3 隊列;清 queue | 15-30 分鐘 |
| 每月首交易日 | ROW 2 逐行;執行 R3 top-up + 衛星 target/current 對齊 | 30-60 分鐘 |
| 每季 | 全版 + adversarial bear-case sweep + WATCH 覆核 | 半日 |

---

## 4. 實作註記(俾執行 session,唔係本檔 scope)

- `web/` 已有 read-only dashboard 殼(run_scan/app/render,可部署)——本設計係換內容
  唔係重起爐灶。所有數據源都係現有檔案/script 輸出,接線工作 = 每格一個 parser + 一版
  template,估 1-2 個 session。
- 落地次序建議:ROW 0(全部數據今日已有,即接)→ ROW 3(隊列數 file 現成)→ ROW 1
  (VaR 計算要 P0-1 嘅 downside 表,但可以先用粗表)→ ROW 2(等 ledger + P1 模組,
  最遲但最肥)。
- **Ledger 係 ROW 1/2 嘅前置**:冇 position tracker(07-06 已發現 repo 冇),
  target vs current 同 VaR 都係盲嘅。極簡 CSV 台帳(architecture §5 #3 嘅同一個修項)
  要排先。
- 唔好做嘅嘢(明文,防手多):唔好加 per-ticker 報價流(broker 有)、唔好加任何
  可以「一撳就落單」嘅嘢(NHITL 界線:落單永遠喺 broker 人手做)、唔好加大市新聞 feed
  (noise)、唔好將 IC 曲線放主版(佢係季度話題,唔係每日行動)。
