# Dashboard v4:內容升級 + 隨身交付架構【Fable 5,2026-07-13】

> 承接 v3(`docs/2026-07-12_dashboard_design_v3.md`——四行版面/五條設計原則照用,唔重複),
> 兩樣新嘢:①摺入 07-12/13 全部新機制(AA-strict 結構、delta 總帳、expectations-gap、
> 機會階梯、BT-7 ballast 體檢);②**交付架構**(用戶需求:唔常在家,要手機喺美股收市後
> +開市前兩個時段睇晒)。

---

## 1. 交付架構(拍板):Markdown-to-GitHub + Telegram 門鐘

**場景事實**:數據係批次節奏(05:55 港晨 = 美股收市後全批;20:30 港晚 = 開市前 premarket
疊加),用戶純閱讀(NHITL 冇互動掣)→ dashboard 係「出版物」,唔係「服務」。

| 層 | 做法 | 點解 |
|---|---|---|
| **主載體** | `DASHBOARD.md`(repo 根目錄)+ `dashboard_assets/*.png`(圖表),由批次 job 生成後 auto-commit push(重用 track_record 現有 auto-commit 管道)| GitHub 手機 app 原生 render markdown 表格/emoji 燈/`<details>` 摺疊/PNG;**auth = GitHub 登入本身;零新基建零月費** |
| **門鐘** | Telegram bot:05:55 + 20:30 各推一條——全綠推「✅ 今日無動作」,有事推具體行動 + GitHub link;kill 觸發即時加推 | 用戶唔使記得check,有事嚟搵人;bot ~30 行 Python + 一次過攞 token |
| **降級** | `web/` 現有 dashboard 留做屋企 LAN 深挖;**唔上雲** | 上雲要複製數據管道 + 起 auth,批次節奏下零增值 |
| **唔採** | HTML push GitHub(唔 render,得 source);GitHub Pages(頁面公開,組合數據唔出街);雲 web app(供養成本+故障焦慮)| — |

**私隱紀律**:報告只出 %NAV/訊號/紅綠燈,唔出券商帳號/絕對倉位以外嘅個人資料;repo 保持 private。

**兩個版本**:
- **晨版(05:55 後)**:全四行 + 隊列 + 學習迴路(當日決策主餐)
- **晚版(20:30)**:淨刷新 ROW 0/0.5(premarket 價疊加觸發預覽),尾行標「PREMARKET 預覽,
  收市判定為準」

## 2. 版面 v4(v3 四行 + 兩個新元素;手機優先:每表 ≤5 欄,次要嘢入 `<details>`)

```
🏷 市況檔位:平靜市 | 調整市 | 危機市   ← 機會階梯嘅檔位橫額(v4 新)
┌ ROW 0 今日行動條 ────────────────────────────
│ SPY>200SMA 🟢 | QQQ>200SMA 🟢 | Roll T-42 | Top-up T-12
│ KILL: 0 | 危機sleeve: ⚪DISARMED | 裁判: PRELIM 12/60
├ ROW 0.5 機會雷達(v4 新)──────────────────────
│ A閃縮候選: 2隻pending | B washout: ⚪ | C-core: ⚪(VIX 16)
│ D觸發: 1(DRAM合約價+) | 本月機會預算: 已用 1.2%/5%
├ ROW 1 風險條 ────────────────────────────────
│ ★組合delta: 112%(band 105-125 🟢)← AA 第一風險數(v4 新)
│ ai-capex kill情境: −X% | ballast體檢: 上次PASS(季度)
│ beta化: 0 | 數據哨兵: 🟢
├ ROW 2 主題作戰台(按 |target−current| 排)─────
│ theme | conf | mag | exp-gap(P_base/g_impl)← v4 新欄 | Δ行動
│ (15行;watch 摺埋;每行 <details> 收 stage/擁擠/kill距離/新鮮度)
├ ROW 3 學習迴路 ──────────────────────────────
│ IC: matured n/60(首判決~10月)| Brier: — | 隊列: 2/3/1 | IMA: 2/4
└──────────────────────────────────────────────
```

v4 相對 v3 嘅內容增量(數據源全部已存在):
1. **市況檔位橫額**:機會階梯三檔(`opportunity_ladder.md` 規則:VIX+200SMA+washout 判);
   佢決定 ROW 0.5 邊啲雷達係「可執行」狀態。
2. **ROW 0.5 機會雷達**:A(閃縮候選 pending 數)/B(washout 燈)/C-core(VIX 檔)/
   D(第三方序列觸發數)+ 本月機會預算用量。
3. **組合 delta vs band**:AA 結構嘅單一控制變數升做風險條頭位(`sizing.py` %制 +
   beta_check 讀數合成);未遷移 AA 前顯示 core v2 等效 delta,遷移後自動有意義。
4. **exp-gap 欄**:P_base + g_implied(`exp_expectations_gap_v0` 季度刷新;
   「大部分係希望」行標 ⚠,sizing 鎖 watch 級嘅原因直接睇到)。
5. **ballast 體檢**:季度職責排名結果一格(BT-7 機制,`2026-07-13_bt7_ballast_definition.md`)。

## 3. 實作計畫(1-2 個 session,執行 backlog)

1. `thesis/dashboard_render.py`:讀現有輸出(playbook_log / theme_signal / sizing --nav-pct /
   concentration / beta_check / ic_report.json / 三條 queue / expectations_gap 結果 /
   premarket_log)→ 砌 `DASHBOARD.md` + PNG;**唔起新計算,純聚合現有檔**。
2. 接入 05:55 批次尾 + 20:30 job 尾:render → git add/commit/push(重用現有 auto-commit
   模式;夜班 permission boundary 唔適用——寫喺工作目錄內)。
3. Telegram:用戶自行 @BotFather 開 bot 攞 token(5 分鐘,人手一次)→ token 落
   `~/.config/karst/telegram`(gitignored)→ render 尾段 sendMessage。
4. 驗收:手機 GitHub app 實睇一次晨版+晚版;斷網/數據哨兵紅燈情境下推「⚠ 數據不可信」
   而唔係靜默;kill fixture 觸發即時推送測試。

## 4. 唔做清單(v3 §4 照用,加兩條)

- 唔做雲端 web app / 唔開 GitHub Pages(私隱)
- Telegram 唔推任何「一撳落單」深度連結——門鐘只講事實,落單永遠喺券商人手做(NHITL 界線)
