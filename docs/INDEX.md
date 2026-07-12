# Karst Workspace 導航地圖(任何 agent / 新 session 由此入)

> **呢份係咩**:成個 workspace 嘅單一導航索引 —— 邊份 doc 係咩、live 定 design 定作廢、去邊搵嘢。
> **落嚟次序**:`STATUS.md`(現況+每日排程)→ 本檔(全圖)→ 各專檔。
> **標籤**:🟢LIVE(運作中)· 📘DESIGN(規格,待/正實作)· ⛔SUPERSEDED(留檔勿引)· 🔒PERSONAL(含用戶持倉,勿公開)
> 更新:2026-07-09。

## 0. 頂層入口(root)
| 檔 | 用途 |
|---|---|
| `STATUS.md` | 🟢 現況 + 每日自動化排程表 + 下一步(每 session 先讀)|
| `docs/INDEX.md` | 🟢 本檔,全 workspace 導航 |
| `docs/KARST_WIKI.md` | 🟢 layman 全貌 wiki(v2 已驗證,`docs/2026-07-06_wiki_verification_v2.md`)|
| `ARCHITECTURE.md` | 🟢 技術版跨 Phase 真相 |
| `AGENTS.md` / `HANDOFF.md` / `README.md` | 🟢 agent 協作 / 交接 / repo 說明 |
| `.agents/KARS_MEMORY.md` | 🟢 歷史決策/坑(§1-14)|
| `docs/ROADMAP_AGENTIC.md` | 🟢 接線 roadmap(A1-D6)|

## 1. Core 策略(70% 資金)—— 🟢 LIVE
| 檔 | |
|---|---|
| `docs/2026-07-06_core_strategy_v2.md` | 🟢 **定稿**:SPY 底倉 + SPY/QQQ LEAP(純200SMA閘+月度top-up,Δ0.50)+ 現金。保守 α +6.5pp t3.1 |
| `docs/2026-07-07_core_playbook.md` | 🟢 獨立操作手冊(每日判定/開倉SOP/邊界情況)|
| `docs/2026-07-06_core_strategy.md` | ⛔ v1(sandbox proxy),SUPERSEDED |
| 證據 | `results/2026-07-06_{leap_real_sweep,core_assembly_real,core_topup}.md`、`2026-07-07_{base_mix,topup_timing_ab}.md`、`2026-07-09_options_chain_spotcheck.md` |
| 已判死(留證) | `results/2026-07-06_sector_capeff.md`(板塊三假設)、`2026-07-08_{crash_switch,crypto_decorr}.md`、`2026-07-06_portfolio_rotation.md` |

## 2. 每日運作工具 —— 🟢 LIVE(排程見 STATUS)
| 工具 | 輸出 |
|---|---|
| `backtest/playbook_readout.py` | core 每日判定 + **觸發價**(200SMA cross / RSI-2<10 / >90) + 危機 sleeve 狀態 |
| `thesis/theme_signal.py` | 衛星每主題 verdict(BUY-ZONE/WAIT/KILL-WATCH)+ HARD/SOFT target |
| → log | `playbook_log.txt`(root,gitignored)|

## 3. Phase-3 衛星(30%)—— 📘 DESIGN + 部分 🟢 LIVE
| 檔 | |
|---|---|
| `docs/2026-07-08_phase3_architecture.md` | 📘 **Phase-3 入口**:數據流圖 + 部件清單 + 執行 backlog + 系統 top-3 缺陷 |
| `docs/2026-07-08_phase3_ws{1..5}_*.md` | 📘 五 WS 規格:ws1 裁判 / ws2 危機 / ws3 生命週期 / ws4 早期偵測+儀錶盤 / ws5 表達注碼 |
| `docs/2026-07-09_magnifier_model_plan.md` | 📘 **★ supercycle magnifier 模型**(用戶最新方向;含 case 庫 patterns + discovery reframe;**model 設計待用戶深談**)|
| `docs/2026-07-09_magnifier_literature.md` | 🟢 21 篇學術地基(回報偏態/資本週期/營運槓桿/彩票)|
| `docs/2026-07-09_text_and_smartmoney_methodology.md` | 🟢 11 篇:文本訊號方法論(Lazy Prices/LM 詞典/Theile 供應鏈 NLP)+ 13F smart-money probe 評估 |
| 已 LIVE 部件 | `thesis/{forward_ic,log_predictions,backfill_outcomes,migrate_track_record}.py`(裁判)、`{sizing,concentration,beta_check,lint}.py`(生命週期/注碼)、`themes.yaml`(registry)|
| Phase-3 研究 | `results/2026-07-08_{constraint_language_probe,altdata_census,insider_cluster_probe,crisis_rescue,power_etf_basket}.md`、`2026-07-09_magnifier_case_library.md` |

## 4. 知識層(discovery 原料)—— 🟢 LIVE
| 件 | |
|---|---|
| `thesis/corpus.py` | 🟢 SQLite FTS5 全文庫(`build/search/get/ticker/verify`);收 gooptions + transcript;**MCP-ready,MCP 本身 defer** |
| `thesis/.raw/transcripts/` | 🟢 defeatbeta 電話會 transcript(gitignored;full-market prefetch 進行中)|
| `thesis/.raw/gooptions/` | 🟢 gooptions 研究(gitignored)|
| `thesis/prefetch_transcripts.py` / `download_gooptions.py` | 🟢 抓取(resumable)|
| `thesis/weekly_corpus.cmd` | 🟢 週度 prefetch→build(全市場;待用戶授權排程)|
| `docs/2026-07-09_ima_extraction_prompts.md` | 📘 IMA 知識庫 agent 抽取管道(4 條 prompt:資金流/記憶體/約束語言掃描/共識;取代人手上載研報)|
| `thesis/DESIGN.md` | 📘 Phase-3 完整設計藍圖 |

## 5. Session 產出:驗證/審查(this session)
| 檔 | |
|---|---|
| `docs/2026-07-06_wiki_verification_v2.md` | 🟢 wiki 逐條驗證(v1 ⛔)|
| `docs/2026-07-06_gap_conflict_register_v2.md` | 🟢 gap/衝突登記(v1 ⛔)|

## 6. 🔒 PERSONAL(含用戶真實持倉,勿公開/push 前 scrub)
| 檔 | |
|---|---|
| `docs/2026-07-08_transition_plan.md` | 🔒 過渡計畫 + 實際持倉 + recovery ladder + AXTI/量子/crypto 決定 |

## 7. ⛔ SUPERSEDED(留檔勿引)
`docs/2026-07-06_{core_strategy,wiki_verification,gap_conflict_register,phase3_methodology_review,dashboard_design,bottleneck_candidates}.md`(sandbox Fable 產出)· `results/2026-07-06_{leap_delta_sweep,core_portfolio_loops}.md`(proxy draft)· `docs/2026-07-06_fable_brief.md`(交棒書,任務已重做)

## 8. 較早期參考(pre-session,仍有效)
`docs/2026-07-05_{risk_control_layer_report,gamma_walls}.md`、`2026-07-03_strategy_methodology_review.md`、`backtest/results/2026-06-30~07-05_*.md`(訊號家族結算)、`backtest/experiments/README.md`(實驗腳本索引)

## 導航規則(俾 agent)
1. 引數字/結論 → 去 `backtest/results/*.md`(落檔嘅先係真相,對話/記憶會錯)。
2. 見同名 v1/v2 → **一律用 v2**;v1 已標 SUPERSEDED。
3. 改重要檔前備份 `~/.claude/backups/`;.cmd 註解 ASCII-only;themes.yaml note 含 `#` 要雙引號。
4. Magnifier 模型設計(step D)**待用戶深談**,唔好 solo 砌。
