---
id: KARST-031
title: 因子混合策略(ETF 版):四類因子敞口混權重跑回測
type: task
createdAt: 2026-08-27
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-023, KARST-027]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
closed: 2026-08-28
---

## 工作內容

因子混合策略(factor-mix strategy)自此跑得出回測:質素、價值、動能、低波四類因子 ETF 按權重混成一個組合,而 ETF 與股票走同一條可投資對象路徑,平台不為 ETF 另開一條。範圍是 v1 那個直接買現成因子 ETF 混權重的版本;自算因子分數選股列日後版本,不入本票(D-012 第 2 條)。因子命名照因子族(factor family)規矩落在「族名·具體定義」一級——族名只是分類,不是因子,版本鏈與單一定義都落在具體定義那一級(規格 1.8)。

## 驗收條件

- [x] 四類因子 ETF 按指定權重混成一個組合,跑得出一次完整回測並交得出逐日淨值(D-012)
- [x] ETF 與股票走同一條可投資對象路徑,適配層無為 ETF 另設的分支(D-012)
- [x] 落庫的因子名全部在「族名·具體定義」一級,查不到單以族名登記的因子(規格 1.8)
- [x] 四類的權重是可掃描參數,不寫死在碼裡(D-008)

## 結果

· 2026-08-28 00:28 —— 因子混合策略(ETF 版)跑得出回測。新增 `karst/strategies/factor_mix.py`(策略層,不碰引擎、數據、留痕、唯一入口四層),四格因子敞口按參數集指定的權重砌成一張目標比重表,交去引擎適配層 A 的目標比重路徑(`PortfolioEngine.simulate`)跑,逐日淨值、逐日持倉、逐筆交易三件經 `karst/runs` 落痕。

**示例運行(示例參數,不是現役設定)**:數據快照 `2026-08-27-91a5d51339d9`(yfinance,已調整價,2015-01-02 ~ 2026-08-26,2929 個交易日,宇宙為六隻 ETF:SPY、QQQ 加下列四隻);四格因子敞口為 QUAL(質素)、VLUE(價值)、MTUM(動能)、USMV(低波),各佔 25%,換倉節奏季度(quarterly),起始本金 100,000、手續費率 0。運行編號 `run-f4c162e5aac34347`,期內換倉 47 次,首次執行日 2015-01-05。

- 累計回報 **+321.9%**
- 年化回報 **13.2%**
- 最大回撤 **-34.9%**

再講一次:上面那組權重與節奏只是為驗收而揀的示例,不是現役設定;權重與節奏兩者都住在參數集,改參數不用改碼。

**逐項剔驗收條件**

1. **四類因子 ETF 按指定權重混成一個組合,跑得出一次完整回測並交得出逐日淨值** —— `run_factor_mix` 一句跑完,逐日淨值每一根 K 線一個數、無缺口、由起始本金起步;四隻 ETF 全部真的持有,同一個面板裡的 SPY、QQQ 一股不持;混出來的走勢落在四隻成份之間(是「混」不是「揀一隻」)。運行經 `record_factor_mix_run` 落痕,引用得到快照編號與四個因子版本,落痕之後讀得回逐日淨值不用重跑。測試:`test_four_factor_etfs_mix_into_one_portfolio_with_a_daily_equity_curve`(用真實抓取的 2024 全年六隻 ETF 快照;離線即 skip,做法沿用 `test_data_yfinance.py`)。

2. **ETF 與股票走同一條可投資對象路徑,適配層無為 ETF 另設的分支** —— 掃 `karst/engine/` 全部原始碼的語法樹(識別字與真正用到的字串,不計說明文字),`etf` 與 `entity_kind` 零命中:適配層由頭到尾只認得實體編號。另外把四格之中一格由 ETF 換成一隻上市公司,同一個 `run_factor_mix` 照跑,兩格都由同一個 `store.resolve_ticker` 按日解析、同屬一張價格面板的一欄、都落到注。測試:`test_etfs_and_stocks_share_one_investable_path`。

3. **落庫的因子名全部在「族名·具體定義」一級,查不到單以族名登記的因子** —— 查庫證明(經 `karst/store.py` 的連線,只用通用 SQL,D-027):`factor` 表四列,每一列的 `name` 都含分隔符「·」且兩邊不空、`name` 的前半等於 `family`、`name != family`;`SELECT COUNT(*) FROM factor WHERE name = family` 為 0;四個族名(質素、價值、動能、低波)一個都不是因子名。連寫都寫不入——用族名單獨登記或查詢一律當場拒收。四個因子各自全庫只有一處正本(無第二影像),策略引用的亦是具體定義那一級。測試:`test_no_factor_is_registered_under_a_family_name_alone`。

4. **四類的權重是可掃描參數,不寫死在碼裡** —— 五組權重/節奏各登記一個參數集,同一個函式跑出五條不同的淨值曲線,一行碼都沒有改;參數集缺一格權重即拒收(無預設值);`FactorMixParams` 的 `weights` 與 `cadence` 兩格簽名都沒有預設值;掃 `karst/strategies/` 的語法樹,查不到任何綁在權重那一格的數值。測試:`test_the_four_weights_are_scannable_parameters`。

**測試** —— 本票 `tests/test_factor_mix.py` 4 passed(離線 3、真實抓取 1);全倉 `python -m pytest -q` 48 passed,無紅燈。唯一入口核對 `karst verify` 全庫清白:四個因子、策略與參數集全部有寫入者簽章,無一列繞過唯一入口。

**產物** —— `karst/strategies/__init__.py`、`karst/strategies/factor_mix.py`、`tests/test_factor_mix.py`;`pyproject.toml` 的 packages 加 `karst.strategies`。快照 `2026-08-27-91a5d51339d9` 與運行 `run-f4c162e5aac34347` 落在 `data/`(不入 git,可由管線重抓)。

## 留言

· 2026-08-28 KARST-031-factormix —— **三件交低給下一手,本票內自行繞過,沒有改別人的層。**

1. **適配層 A 欠一個「與排名無關」的組合參數型別。** `PortfolioEngine.simulate` 的參數型別是 `RankingRebalanceParams`,但模擬器實際只讀其中兩格(起始本金、手續費率),另外兩格(選幾隻、排名方向)是排名策略專有。目標比重路徑上這兩格用不著,本票唯有填 `top_n=敞口格數`、`direction="high"` 兩個空值進去。建議日後把兩格共用的抽成一個 `PortfolioParams`,由 `RankingRebalanceParams` 繼承——`karst/engine/` 是 KARST-024 的地盤,本票不動。

2. **單一定義庫欠一個「列出全部因子」的 API。** 驗收條件 3 要查庫證明「無單以族名登記的因子」,`karst/store.py` 現有的 `locate_definition` / `find_name_occurrences` 都要先知道名字,列不出全表。本票改為經 `store.connection` 下通用 SQL 查 `factor` 表(沒有另開 sqlite 連線,守住 D-027 兩條護欄),但這件事應該有個正式 API。

3. **D-012 的 ETF 舉例與族系對不上,請用戶過目。** D-012 第 1 條寫「以**標普**四隻風格指數對應的因子敞口」,第 2 條舉例卻是「SPMO、QUAL」——SPMO 是標普系,QUAL 是 MSCI 系。本票按派工指令用齊 MSCI 系四隻(QUAL / VLUE / MTUM / USMV),四隻同出一個指數供應商,混起來族系一致。若用戶原意是標普系,對應的四隻是 SPHQ / SPVU / SPMO / SPLV——**換一套只需另砌一份敞口名單傳入,`factor_mix.py` 一個字不用改**,但四個因子名要另行登記。

4. **一個策略層的判斷,寫在這裡以免日後有人當它是 bug。** 換倉節奏排出來的第一次換倉,最早也在第一個週期的尾(季度即第一季完)。排名策略要等第一個因子讀數,等得有道理;混權重策略的權重在回測開始之前已經由參數集寫定,沒有東西要等,所以 `factor_mix_schedule` 在節奏排期之外補一次「第一根 K 線決策、第二根按開價建倉」。少了這一次,季度節奏會白白持三個月現金,交出來的淨值不是這套策略的成績。可執行時點照舊不變:永不同根成交(D-021 第 3 條)。
