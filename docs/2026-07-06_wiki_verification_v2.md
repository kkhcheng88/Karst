# KARST_WIKI 驗證報告 v2 —— 獨立重驗(取代同日 sandbox 版)

> **性質**:任務 1 交付物(Fable brief §4)。用戶 2026-07-06 下令**棄用斷網 sandbox agent 嘅驗證**、
> 由任務 1 獨立重做。本次由 4 個互相獨立、fresh-context 嘅驗證員(sonnet)分段執行,
> **明令禁讀** `2026-07-06_*` 舊產出以避免錨定;主腦(Fable)合議定案。
> **本檔取代** `docs/2026-07-06_wiki_verification.md`(sandbox 版,留檔可溯但唔好再引用)。
> 詳細逐條核對表(每 claim 一行、file:line 證據):session scratchpad `task1_{A,B,C,D}_findings.md`;
> 重要判定已全部併入本檔。

## 0. 方法

- **A**:§5.1-5.3、§5.8-5.9(動能/RSI-2/RS/突破/VCP)→ 對 `backtest/results/` 逐數字核對(34 條)
- **B**:§5.4-5.6、§5.10-5.11、§六決策樹+XY 象限 8 數(26 條)
- **C**:§二/§三/§4.1-4.2/§八 oracle 全章/§5.7 insider(19 條)
- **D**:全 wiki「live/已接線/未接線/已建」狀態 claim → 用 **spine/scan/thesis code 做真相**(~45 條)
- Ground truth:`backtest/results/2026-06-30 ~ 07-05_*.md` + experiments docstring + **程式碼本身**;
  sandbox agent 對 wiki 嘅未 commit diff 全部重點覆核。

## 1. 總結統計(~124 條 claim)

| 驗證員 | 條數 | VERIFIED | 有問題(MISMATCH/OVERSTATED/STALE/UNTRACEABLE/PARTIAL/NOT-FOUND)|
|---|---|---|---|
| A(訊號家族 I)| 34 | 24 | 9 MISMATCH + 1 OVERSTATED + 1 UNTRACEABLE(歷史敘述)|
| B(訊號家族 II + 決策樹)| 26 | 21 | 1 MISMATCH + 1 OVERSTATED + 2 STALE + 1 UNTRACEABLE |
| C(核心信念 + oracle + insider)| 19 | 18 | 1 OVERSTATED(輕微)+ 1 引用清單有缺 |
| D(code 接線)| ~45 | ~30 | 4 CODE-MISMATCH + 6 PARTIAL + 2 NOT-FOUND |

**大局判定**:wiki 嘅**核心數字鏈全部係實**(T1 +2-6%/年、QQQ RSI-2 α6.53 t2.9、oracle 155%→年度≈2×SPY、
0/28 因子、VIX>28 +9.0/+5.9、XY 象限 8 數、GEX partial −0.08、credit 剔除屬實)。
問題集中喺三個 pattern:**(i) 來源標 ⚠ 但 wiki 升級做 ✅(符號灌水);(ii) wiki 內部唔同章節對同一訊號
講法唔一致;(iii) 文檔 status 講「live」但 code 實際係閹割版/裸奔版**。

## 2. 最重要發現(修正前 wiki 會誤導決策嘅位)

1. **§5.2 Mag7 RSI-2 被錯誤降級**:wiki 原判「🟡 只極端<5」;來源檔(`rsi2_capital_efficiency`)
   entry<10 已 46/1.09 贏 B&H 30.9/0.88,且明文判 Mag7 = "most regime-robust / all-weather"。已改 ✅。
2. **§5.2 mid/large 符號灌水**:來源標 ⚠(H1 <5 = −41/−43/−32 大地雷),wiki 寫 ✅ 同格仲自己寫住「大地雷」。已改 ⚠。
3. **§5.1 vs §5.8 內部矛盾**:「突破兩半都贏」其實只限大盤/Mag7/large/micro;mid/small H2 輸 B&H
   (0.37/0.33 vs 0.86/0.69);兩節符號(❌ vs 🟡)都唔一致。已統一 + 加限定。
4. **§5.6 vol-timer 方向講反**:wiki 話「≈/低過 B&H」;來源話表面 Sharpe 1.4-1.7 **高過** B&H 但係
   半 artifact + 走漏 capitulation(所以先至判中性)。已改正;細價/板塊嗰兩格數從未落檔 → 標「—」。
5. **spine 現行 RSI-2 = 裸奔版**(code 驗出):`timing.py` 只有 RSI-2,RS-leader / 高波 gate 都未接,
   `is_laggard` 只落 notes —— 正正係回測話 H1 會流血嗰個組態。§4.3/§7.1 已披露。
6. **insider P0-1 gap 冇喺 wiki 披露**:`spine/__init__.py:13` code 自認 `conf_eff` 計咗從未回饋落
   score(display-only);且 §4.3 insider 句仲用緊被 `insider_rigor` R7/R8 推翻嘅舊講法(21/63 日顯著)
   —— 同自己 §5.7 修正版矛盾。兩處已修。
7. **Phase 1 RS「已 live」規格錯配**:live 版係 20 日 advisory tilt(`sector.py _WIN=20`,唔入 score),
   唔係回測驗證嘅 126 日 Q5 硬閘。已標明。
8. **§8 引用幽靈檔案**:`factor_sweep.md` 唔存在(數據併喺 `skill_curve.md`);個股 IC 0.017 出處
   `alpha360_ml.md` 反而漏列。已修引用清單。
9. **兩句 STALE**:§5.10「VIX/credit/RV 已夠」漏跟 credit 剔除;§六 LEAP「delta sweep 未做」過時
   (有 sandbox draft,真數據重跑未做)。已修。
10. **§5.4 F&G headline 用最脆弱格**:<5/>75 得 7 次入場、2020 主導;來源建議落地用 <10。已加註。

## 3. 判定 sandbox 版驗證嘅質素(用戶關注)

覆核結論:sandbox agent 嘅 wiki 修改**大方向正確、數字冇捏造**(credit 推翻屬實、XY 象限數全對、
oracle 鏈全對、§5.7 insider 修正版正確)。但佢係 **doc-level 驗證**:(a) 冇做 code-level 核對
(所以走漏發現 5/6/7);(b) 有幾處自己引入/保留咗符號灌水同內部矛盾(發現 1/2/3);
(c) 有句子改咗一半冇同步(發現 9)。呢啲已由本次修正。

## 4. 已套用修正(2026-07-06,共 18 處)

§一~§十:Phase 0 狀態(RV 字眼 + quadrant 未接)· Phase 1 狀態(20日 tilt)· Phase 3(insider 修正
+ P0-1 披露)· Phase 4(裸奔披露)· §5.1 股種/市值/Regime 三行 · §5.2 Mag7 + mid/large · §5.4 headline
註 · §5.6 vol-timer · §5.8 市值行 · §5.10 credit · §六 前言接線提示 + delta sweep 狀態 + 長期反轉學術註
· §3.2 DSR 歸屬註 · §7.1 三行(RSI-2 裸奔/RS 20日/低波未接)· §7.3 規則③未自動化 · §八 引用清單 · 頁首指向本檔。
修改前備份:`~/.claude/backups/KARST_WIKI.md.2026-07-06.bak`。

## 5. 遺留(交任務 2 登記冊跟進)

- `exp_lowvol_family.py` 細價/板塊 vol-timer 數只喺 console,從未落檔(UNTRACEABLE)→ 要補跑落檔
- `exp_family_validate.py`(+12.5pp 來源)係準孤兒:結論散喺 ARCHITECTURE/memory,無獨立 results 檔
- DSR 0.908 係 long-short mirror 檢定,long-only headline 未有直接 DSR → 可補
- §八 155%/196%(1999-2026)vs 151.5%(2002-2026)係唔同窗口嘅獨立研究,讀者易誤會同一組數
- 防守板塊 tilt portfolio 級從未測(§7.1 已標未接線)
