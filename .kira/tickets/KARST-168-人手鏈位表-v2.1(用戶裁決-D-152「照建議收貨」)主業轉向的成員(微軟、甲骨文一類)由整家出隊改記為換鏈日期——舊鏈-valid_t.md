---
id: KARST-168
title: 人手鏈位表 v2.1(用戶裁決 D-152「照建議收貨」):主業轉向的成員(微軟、甲骨文一類)由整家出隊改記為換鏈日期——舊鏈 valid_to、新鏈 valid_from 各填轉向日並附年報或公告佐證,令切片日期前的樣本仍可用;逐一覆核 removed_v2.csv 的 23 行哪些屬「主業轉向」哪些屬真出隊;其餘 v2 內容一字不改;交主 agent 收貨後作 v3 量度的正本
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: chain-v21-168
deliverable: KARST-D02
closed: 2026-09-03
---

## 工作內容

背景:KARST-161 交付 v2(experiments/2026-09-02-chain-layers/chain_membership_v2.csv、chain_stories_v2.md、removed_v2.csv),用戶已裁照建議收貨(D-152),其中一項建議是主業轉向不整家出隊、改記換鏈日期(D-151 ③)。先讀 D-147、D-151、D-152,chain_stories_v2.md 的誠實聲明與出隊規則,removed_v2.csv 全部 23 行。做法:①逐行判 23 行出隊理由:規則 d「主業已轉向」的(至少 MSFT、ORCL,可能還有其他)改為兩行——舊鏈一行 valid_to=轉向日、新鏈一行 valid_from=同日,轉向日以年報或公告可查的事件為準(例如微軟 2023 年 1 月宣布 OpenAI 追加投資、甲骨文 2023 年 9 月 OCI 收入首次單獨披露),查不到填近似並標記;②其他規則(位置不同、單一資產主導、無可比公司)維持出隊;③v2 檔不改,另出 chain_membership_v2_1.csv、chain_stories_v2_1.md(只加一節「v2.1 變更」列每一行改動與佐證)、removed_v2_1.csv;④年報佐證從 data/sec/10k_text 快取讀,缺才抓(每秒 ≤10、User-Agent `Casy Limited kaho.career@gmail.com`、抓前查 manifest,fetchedBy 填票號);⑤誠實聲明沿用 v2 四項;⑥收工在票上 comment 結果並 close,不需用戶審(用戶已裁方向)。

## 驗收條件

- [x] chain_membership_v2_1.csv:主業轉向成員以換鏈日期呈現(舊鏈 valid_to + 新鏈 valid_from 同日),每行附佐證來源;v2 檔一字不改
- [x] chain_stories_v2_1.md 有「v2.1 變更」一節逐行列改動;removed_v2_1.csv 只剩真出隊
- [x] 新抓年報只入單一快取連 manifest;生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9
- [x] commit 用 git commit --only -F <訊息檔> -- <自己的檔>;票上 comment 後 close

## 結果

**逐行覆核 removed_v2.csv 23 行**:改記換鏈日期 2 行(MSFT、ORCL),維持出隊 21 行。

| 公司 | 舊鏈 → 新鏈 | 轉向日 | 準確度 | 佐證 |
|---|---|---|---|---|
| MSFT | `software_cloud` → `hyperscalers` | 2023-01-23 | 月準確 | FY2023 10-K(0000950170-23-035122)明文「In January 2023 we announced the third phase of our OpenAI strategic partnership」;OpenAI 一詞在 FY2022 年報 0 次、FY2023 年報 7 次 |
| ORCL | `software_cloud` → `hyperscalers` | 2023-06-01 | 近似 | FY2024 10-K(0000950170-24-075605)業務描述開首首次以「用 OCI 訓練生成式 AI 模型的 AI 公司」作代表客戶;FY2022/FY2023 同一段只有通用 AI 字眼。取該財年首日 |

維持出隊的 21 行,其中 4 行掛規則 d 名下但不是「某一日轉向」:BHP / RIO(全期鐵礦石主導、沒有轉向日,v2 亦沒有鐵礦石那一層可換)、COP(轉向日 2012-04-30 完成 Phillips 66 分拆,有 FY2012 10-K 明文,但在表的起點 2022-01-01 之前,補回舊鏈只得空區間;順帶更正 v0 那一行的 `valid_to=2026-07-22` 是舊倉表務日期,不是業務轉向日)、HOOD(v1 同一家公司出現兩次的去重,不是轉向;`fintech` 在 v2 已拆散,沒有舊鏈可寫)。其餘 17 行是規則 a / b / c。

| | v2 | v2.1 |
|---|---:|---:|
| 鏈數 | 65 | 65 |
| 成員行數 | 347 | 349 |
| 不重覆公司數 | 343 | 343 |
| 出隊行數 | 23 | 21 |
| 本票新抓年報 | — | 0 份 |

**正本**:`experiments/2026-09-02-chain-layers/chain_membership_v2_1.csv`(UTF-8 BOM)、`chain_stories_v2_1.md`、`removed_v2_1.csv`(UTF-8 BOM);腳本 `build_v2_1.py`;README 加 v2.1 一節;CONTEXT.md 詞彙表新增「換鏈日期 / chain switch date」。commit `efc8335`。生產庫 SHA256 首 16 位 `b168e9f45b578cf9`,未變。

**唯一一處連帶改動**:`software_cloud` 的逐鏈純度句(`purity_note`,該鏈 8 行共用)在 v2 寫住「v2 剔走四家:MSFT 與 ORCL 按規則 d……」,在 v2.1 不成立,已改寫並在文件明列。carried 過來的 347 行合共只有 14 格有改動。

## 留言

### agent:chain-v21-168 · 2026-09-03 08:03
KARST-168 收檔。

**誠實聲明**(沿用 v2 四項,加本票兩點):這張表仍然是事後編的,量到的解析度一定偏高;來源品質未經核數;valid_from 六成是近似;純度判斷全屬人手、沒有統計量度背書。本票額外要講兩點:①ORCL 的轉向日是由 2024-06-20 才公開的年報倒推,本身帶前視成分,不是事前可得;②本票只改了兩家、四行,同一類前視問題在 v2 其他地方仍然存在。

**逐行覆核 removed_v2.csv 全部 23 行**,問一條:這一行是不是「某一日主業轉了向」?

改記換鏈日期:2 家、4 行。
- MSFT:software_cloud 2022-01-01 → 2023-01-23,hyperscalers 2023-01-23 起現役。佐證=FY2023 10-K(accession 0000950170-23-035122,申報日 2023-07-27)明文「In January 2023 we announced the third phase of our OpenAI strategic partnership」;邊界佐證=OpenAI 一詞在 FY2022 年報 0 次、FY2023 年報 7 次。日期月準確(日取微軟公告日,快取內核實不到日)。
- ORCL:software_cloud 2022-01-01 → 2023-06-01,hyperscalers 2023-06-01 起現役。佐證=FY2024 10-K(0000950170-24-075605,申報日 2024-06-20)業務描述開首首次以「用 OCI 訓練生成式 AI 模型的 AI 公司」作代表客戶;FY2022(0001564590-22-023675)與 FY2023(0000950170-23-028914)同一段只有 SaaS 功能式與風險因素式的通用 AI 字眼。取該財年首日,標記近似。票面建議的「2023 年 9 月 OCI 收入首次單獨披露」在年報快取內核實不到,故不採;removed_v2.csv 原判詞寫「自 2024 年起」,年報證據指向再早一個財年,本票採年報證據。

維持出隊:21 行。其中 4 行掛規則 d 名下,但逐行看過都不是「某一日轉了向」。
- BHP、RIO:全期都是鐵礦石(與鋁)主導的多元化礦商,沒有轉向日;舊倉 2026-07-21 手術已把出隊日追溯到 2021-11-30(走廊首個決策日之前),量度窗內沒有一日屬 copper;而且 v2 的 65 條鏈沒有鐵礦石那一層,沒有新鏈可換。兩家都是 20-F 外國申報人,10-K 快取沒有它們的年報。
- COP:轉向日查得到而且很早——2012-04-30 完成下游分拆(Phillips 66),FY2012 10-K(0001193125-13-065426)有明文。但表的起點是 2022-01-01,補回舊鏈那一行只會得出一段空區間,對切片沒有用,所以維持出隊。順帶更正一件事:v0 那一行的 valid_to=2026-07-22 是舊倉的表務日期(energy 主題退役日),不是業務轉向日。COP 本來已在 upstream_oil 現役,沒有樣本損失。
- HOOD:這一行本來處理的是同一家公司在 v1 出現兩次(fintech 與 web3_crypto)的去重,不是轉向;而且 fintech 在 v2 已拆成 alt_lending 與 payments,券商這個位置在 v2 沒有對應層,沒有舊鏈可以寫 valid_to。
其餘 17 行分別是規則 a(位置不同)、b(定價機制不同)、c(單一資產主導),按票面 ② 維持出隊,判詞逐行寫在 removed_v2_1.csv 的 v21_review 欄。

**數**:鏈數 65(不變)、成員行數 349(v2 347)、不重覆公司數 343(不變)、出隊 21 行(v2 23)。本票新抓年報 0 份——MSFT / ORCL / COP 的佐證全部在 data/sec/10k_text 快取內,沒有打過 EDGAR,manifest 沒有新行。生產庫只讀,SHA256 首 16 位仍是 b168e9f45b578cf9。

**v0 / v1 / v2 檔一字不改**,已用逐格比對確認(git status 顯示三個 v2 檔沒有改動)。carried 過來的 347 行合共只有 14 格有改:MSFT / ORCL 在 hyperscalers 那兩行的 valid_from、note、valid_from_basis 共 6 格,加上 software_cloud 的逐鏈純度句 purity_note(該鏈 8 行共用)。那一句在 v2 寫住「v2 剔走四家:MSFT 與 ORCL 按規則 d……」,在 v2.1 已經不成立,所以改寫了——這是本票唯一一處超出「兩家、四行」的連帶改動,已在 chain_stories_v2_1.md 與 README 明列。

**新檔**:chain_membership_v2_1.csv(UTF-8 BOM,多 v21_change / switch_date_basis / switch_evidence 三欄)、chain_stories_v2_1.md(v2 全文只加「v2.1 變更」一節,並在該節聲明凡與 v2 原文衝突以該節為準)、removed_v2_1.csv(UTF-8 BOM,多 v21_review / switch_date / switch_evidence 三欄)、build_v2_1.py。README 加 v2.1 一節;CONTEXT.md 詞彙表新增「換鏈日期 / chain switch date」。commit efc8335。

**本票沒有做的**:①同一類前視問題在 v2 其他地方仍在——ai_hpc_hosting 四家(CORZ / IREN / WULF / CIFR)2024 年才由 crypto_mining 轉去 AI 託管,valid_from 仍是 2022 年初;HOOD 在 crypto_exchange 的 valid_from 仍是 2022-01-01。按票面「其餘 v2 內容一字不改」本票沒有動,要一併按換鏈日期處理是另一張票。②純度判斷仍然全屬人手,沒有統計量度背書;本票是改表票,不出成績。③valid_from 近似比例沒有改善,本票只精確化了兩行,其中一行還是近似。
