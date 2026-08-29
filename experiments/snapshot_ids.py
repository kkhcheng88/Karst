"""現役數據快照編號——**全部成績腳本共用這一份**(KARST-057)。

2026-08-28 倉根 ``data/`` 被誤清空(436 MB:運行序列與價格快照),``karst.sqlite``
完好。無檔案系統層面的備份,用戶裁決當作**重建**而不是還原(見 KARST-057)。

重抓只生得出**新的**快照編號:編號是抓取日加內容雜湊前 12 位,而
``find_equivalent_snapshot`` 認等價靠掃描磁碟上已有的快照目錄——目錄清空之後
零候選,管線直接落一個新編號(假設 A-007 已推翻)。所以舊編號一個都撞不回,
每一支腳本都要改。

**為什麼集中在這裡。** 舊做法是七支腳本各自寫死一次快照編號,散落十幾處;
下次再要換數據,漏改一處就會出一批對不上血統的成績,而且不會報錯——它只會
靜靜跑出另一批數字。改在這裡一處,七支腳本一齊跟住走。

三份快照全部經唯一入口重抓、有抓取登記::

    python -m karst.gateway data snapshot --start 2015-01-02 --end 2026-08-26
    python -m karst.gateway data snapshot --start 2015-01-02 --end 2026-08-26 \\
        --ticker SPY --ticker QQQ --ticker QUAL --ticker VLUE --ticker MTUM --ticker USMV
    python -m karst.gateway data macro-snapshot --price-snapshot <大型股那個編號>

(第二句的四隻因子 ETF 在 KARST-057 之前不在宇宙名單登記上,唯一入口抓不到;
本票已把它們登記入 ``karst/data/universe.py`` 的 ``FACTOR_ETF_UNIVERSE``,
**起步名單那份預設批次不變**——登記與預設是兩件事。)
"""

from __future__ import annotations

# SPY、QQQ 加十隻大型股;2015-01-02~2026-08-26,2,929 個交易日、35,148 列日線。
# 用者:趨勢波段(KARST-028)。
PRICE_LARGE_CAP = "2026-08-28-a508d635a5fa"

# 六隻因子敞口 ETF(SPY、QQQ、QUAL、VLUE、MTUM、USMV);同一個窗口,17,574 列。
# 用者:因子混合、權重掃描、因子輪動、成本重掃、宏觀驅動器。
PRICE_FACTOR_ETF = "2026-08-28-000b4820a23a"

# 十一隻 SPDR 行業 ETF(XLK 一族)連 SPY 作主日曆錨(宇宙名單登記 sector-etf),
# 2015-01-02~2026-08-28,2,930 個交易日、12 個實體、35,160 列。XLRE(2015-10-07
# 上市)、XLC(2018-06-18 上市)在窗口前段有起始缺口,不補假數據,缺口寫入快照
# 說明檔的註記(D-026 第 6 條)。用者:KARST-072 文獻結論交代後開的實測票。
# (KARST-073)
PRICE_SECTOR_ETF = "2026-08-29-d5c393e65534"

# 標普 500 歷史成分(宇宙名單登記 sp500-historical),2015-01-02~2026-08-28,
# 2,931 個交易日、625 個實體、1,831,875 列。**含已被剔出指數的代號**,不是今日名單。
# 窗口內曾入選 772 個代號,抓得到 629 個;缺口 147 個(19.0%)逐條列在快照說明檔
# 與 experiments/2026-08-29-sp500-universe/缺口.csv。存活者偏差**只除得一半**,
# 用之前先讀那個目錄的 README 第五節。(KARST-065)
PRICE_SP500_HISTORICAL = "2026-08-28-493fd1df1cb9"

# 宏觀十四序列,對齊 PRICE_LARGE_CAP 那條主日曆;41,006 列讀數。
# KARST-058 換來源之後重抓:VIX 與 VIX_3M 改由 Cboe 官方免費歷史檔直取
# (來源名 cboe+yfinance-macro),VIX_3M 自此 2,929 個交易日**全部有真讀數、
# 零留空**——舊那一份的尾段由 2026-07-18 起停數,期限結構驅動器每日判「數據不足」。
MACRO = "2026-08-28-dc2d9f1a1778"

# 舊編號 → 新編號。留在這裡是為了讀得懂舊落檔:倉內的舊報告、舊 summary.json
# 仍然寫住左邊那幾個編號,它們指向的快照已經不在磁碟上。
PREVIOUS: dict[str, str] = {
    "2026-08-27-61e284eaa998": PRICE_LARGE_CAP,
    "2026-08-27-91a5d51339d9": PRICE_FACTOR_ETF,
    "2026-08-28-3b2de5c59740": "2026-08-28-810facb50382",   # KARST-057 重建
    # KARST-058 換來源(VIX 那兩條 yfinance → Cboe 官方檔)。舊那一份**沒有刪**,
    # 仍在 data/macro_snapshots/ 與登記表上:換來源之前落的成績引用的是它,
    # 刪掉就等於把那批成績的血統斬斷。
    "2026-08-28-810facb50382": MACRO,
}

__all__ = [
    "PRICE_LARGE_CAP",
    "PRICE_FACTOR_ETF",
    "PRICE_SECTOR_ETF",
    "PRICE_SP500_HISTORICAL",
    "MACRO",
    "PREVIOUS",
]
