# D1 ASML crowding 污染修正 — A/B 驗證(2026-07-17)

**背景正本**:`backtest/results/2026-07-16_crowding_asml_contamination.md`(污染調查)
**修正**:`thesis/crowding_composite.py` — `NON_ANALYST_CALL_DOCS` 排除 6 份非法說會文件
**接手紀錄**:原修正喺 worktree session `6a8cb3b4`(asml-crowding)寫好但未驗證完就停;
本檔係接手後喺 main 完成嘅驗證,worktree 可退役。

## 修正內容

6 份 ASML/ASMLF 文件被 defeatbeta feed 標成「transcript」,但佢哋自己開場白已表明唔係法說會:

| 文件 | 實際係乜 | 被 parser 當成「分析員」嘅人 |
|---|---|---|
| transcript-ASML-2025-10-15 | 3 人短文件 | Fouquet(ASML CEO 自己) |
| transcript-ASML-2026-01-28 | results **press conference** | Toby Sterling(路透社記者) |
| transcript-ASML-2026-04-15 | Q1 results **video** | Fouquet(CEO)+ Dassen(CFO) |
| transcript-ASMLF-{同上 3 個日期} | ASMLF = 同一間公司 OTC ADR,內文相同 | 同上 |

**點解用明確排除名單而唔用通用規則**:兩個機械式守衛(字數門檻、講者角色推斷)喺 2026-07-16 已被
實證否決(見污染調查檔)——會誤傷 WOLF 呢類真.低覆蓋率困境股嘅真實讀數。呢度修嘅係**數據**,
唔係分類器。

## A/B 驗證(呢個先係原 session 未做完嘅部分)

方法:同一日、同一個 defeatbeta DB、同一份 code,**只差有冇修正**,逐 theme 對比 composite_pctile。

| Theme | 未修正 | 修正後 | 變動 |
|---|---:|---:|---:|
| **euv-lithography-monopoly** | **2.8** | **57.4** | **+54.6** |
| 其餘 16 個 theme(advanced-packaging、ai-power-grid、mag7-hyperscaler、memory-supercycle、semicap-equipment、semiconductor-cycle、space-satellite、tpu-custom-silicon 等) | — | — | **全部 +0.0** |

**判詞**:修正係外科手術式,只掂 ASML/euv,零旁及損害。

### 原 session 嘅「其他 theme 都郁咗」係誤會

原 session 停低前報告「semicap 40.7→81.4、space 59.9→94.7」,懷疑有 bug 或者缺 manifest。
實情:**佢攞緊兩個唔同指標嚟比**——semicap 嘅 composite = 40.7、attendance = 81.4;
space composite = 54.5、attendance = 94.7。即係「舊檔嘅 composite」對「新輸出嘅 attendance」,
apples-to-oranges。A/B 對照證實:冇 bug、冇缺 manifest、亦唔關新 ingest 嘅 transcripts 事。

### 回歸檢查(沿用原 session 已驗嘅三項)

- **ASML**:3 份壞文件剔走 → 最新讀數變返真.2025-07-16 法說會(11 個分析員)
- **WOLF**:維持 1.5 不變 —— 真.低覆蓋困境股嘅讀數冇被誤傷
- **NVDA 2025**:10/6/9/8,同已 commit 嘅回歸檢查一致

## 對 euv confidence 嘅影響:數字冇變,但地基換咗

| | crowding | penalty 帶 | raw | confidence |
|---|---:|---|---:|---:|
| 修正前(污染) | 2.8 | <40 × late = 0.75 | 0.469 | 0.40(uncalibrated cap) |
| **修正後(真值)** | **57.4** | 40-60 × late = 0.65 | **0.406** | **0.40**(cap 仍綁住) |

**confidence 維持 0.40** —— 因為 UNCALIBRATED_CAP 一路都係綁緊嗰個,raw 跌咗但仍然(僅僅)高過 0.40。
即係話:**呢個 0.40 由「上限遮住壞數」變成「上限遮住實數」**,可信度質變,數值不變。

⚠️ **貼邊警告**:57.4 距離 60 呢個帶界只差 2.6 分。一過界 → raw 0.344 → confidence **0.34**。
下次 ASML 法說會嘅分析員人數,足以推佢過界。

敏感度(euv,late cycle,subscores 2/1.5/0/1.5):

| crowding | 39 | 45 | **57.4** | 59 | 61 | 75 | 85 | 92 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| confidence | 0.40 | 0.40 | **0.40** | 0.40 | 0.34 | 0.34 | 0.28 | 0.25 |

## 仲未解:D2(用戶拍板)

D1 修完 crowding = 57.4,但**紅隊原本估 ≥90**。個差距唔係 bug,係**建構效度問題**:
crowding 軸量緊「ASML 自己歷史上嘅覆蓋率分位」(temporal),但 §4a penalty 表想要嘅係
「相對全市場有幾 priced-in」(cross-sectional)。ASML 係全球最多人研究嘅股票之一、PE 98 分位——
橫向睇實係 ≥90。若改 cross-sectional,euv confidence → **0.25**(正正係紅隊嘅估值)。

**呢個決定影響全部 17 個 theme 嘅 penalty,唔止 euv** —— 所以係用戶決定,唔係 gatekeeper 自己改。
