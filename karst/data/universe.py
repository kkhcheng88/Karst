"""起步宇宙名單(universe)。

D-026 第 6 條:免費來源不含退市股,故每個快照連同**當時的宇宙名單**一併凍結,
前向累積自家的宇宙歷史;此前的回測期一律在成績報告標明「未含退市股」。

這裡只是起步的小清單(SPY、QQQ 加十隻大型股),不是平台的宇宙定義——
正式宇宙是策略層的事,管線只負責照名單抓、照名單凍。
"""

from __future__ import annotations

from dataclasses import dataclass

# 主日曆以 SPY 的交易日為準(舊倉同制:align_to_calendar 以 SPY 為錨)
CALENDAR_TICKER = "SPY"


@dataclass(frozen=True, slots=True)
class UniverseMember:
    """名單上的一員:代號、實體種類、顯示名。

    代號只是屬性不是主鍵——入庫時按日期解析成實體編號(D-026 第 2 條)。
    """

    ticker: str
    kind: str  # company / etf
    display_name: str


STARTER_UNIVERSE: tuple[UniverseMember, ...] = (
    UniverseMember("SPY", "etf", "SPDR S&P 500 ETF Trust"),
    UniverseMember("QQQ", "etf", "Invesco QQQ Trust, Series 1"),
    UniverseMember("AAPL", "company", "Apple Inc."),
    UniverseMember("MSFT", "company", "Microsoft Corporation"),
    UniverseMember("NVDA", "company", "NVIDIA Corporation"),
    UniverseMember("AMZN", "company", "Amazon.com, Inc."),
    UniverseMember("GOOGL", "company", "Alphabet Inc."),
    UniverseMember("META", "company", "Meta Platforms, Inc."),
    UniverseMember("TSLA", "company", "Tesla, Inc."),
    UniverseMember("JPM", "company", "JPMorgan Chase & Co."),
    UniverseMember("XOM", "company", "Exxon Mobil Corporation"),
    UniverseMember("JNJ", "company", "Johnson & Johnson"),
)

# 因子敞口 ETF(KARST-031 的因子混合策略、KARST-036 的因子輪動用這四隻)。
# 它們不在起步名單——起步名單是「不指定代號時預設抓哪一批」,而這四隻只在
# 因子那幾套策略用得着,不應該混進大型股那份預設批次。但它們一樣要**登記**
# 過:一個代號是公司還是 ETF、顯示名叫什麼,決定了它以什麼為錨(D-026 第 2 條),
# 命令列不猜。KARST-057 之前它們沒有登記,唯一入口抓不到,只能繞路直呼管線。
FACTOR_ETF_UNIVERSE: tuple[UniverseMember, ...] = (
    UniverseMember("QUAL", "etf", "iShares MSCI USA Quality Factor ETF"),
    UniverseMember("VLUE", "etf", "iShares MSCI USA Value Factor ETF"),
    UniverseMember("MTUM", "etf", "iShares MSCI USA Momentum Factor ETF"),
    UniverseMember("USMV", "etf", "iShares MSCI USA Min Vol Factor ETF"),
)

# 登記在案的全部代號。唯一入口按這份查代號,**預設批次仍然是起步名單**——
# 登記與預設是兩件事,這裡分開兩份正是為了不把它們混做一件。
UNIVERSE_REGISTRY: tuple[UniverseMember, ...] = STARTER_UNIVERSE + FACTOR_ETF_UNIVERSE


def tickers_of(universe: tuple[UniverseMember, ...]) -> tuple[str, ...]:
    return tuple(member.ticker for member in universe)
