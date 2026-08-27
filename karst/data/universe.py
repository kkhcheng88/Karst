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


def tickers_of(universe: tuple[UniverseMember, ...]) -> tuple[str, ...]:
    return tuple(member.ticker for member in universe)
