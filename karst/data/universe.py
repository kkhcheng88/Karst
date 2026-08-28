"""宇宙名單(universe)與宇宙名單登記。

D-026 第 6 條:免費來源不含退市股,故每個快照連同**當時的宇宙名單**一併凍結,
前向累積自家的宇宙歷史;此前的回測期一律在成績報告標明「未含退市股」。

登記上有三份名單(見 ``NAMED_UNIVERSES``):起步的小清單、因子敞口 ETF,
以及 KARST-065 加的**標普 500 歷史成分**——後者由免費成分歷史源砌出來,
含已退市與已剔除的代號,每個代號帶加入/剔除日期,是「不靠今日名單回測歷史」
那一步的原料。登記不等於預設批次:不指定代號時抓的仍然是起步名單。

正式宇宙是策略層的事,管線只負責照名單抓、照名單凍。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

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


# ----------------------------------------------------------------------
# 標普 500 歷史成分(KARST-065)
# ----------------------------------------------------------------------

UNIVERSES_DIR = Path(__file__).resolve().parent / "universes"
SP500_MEMBERSHIP_FILE = UNIVERSES_DIR / "sp500_historical.csv"


@dataclass(frozen=True, slots=True)
class MembershipPeriod:
    """一段成分期:這個代號由哪一日起、到哪一日止在名單之內。

    ``left_on`` 留空即來源記它仍在名單上。日期是**來源講的日期**,不是本倉自行
    推斷的——推斷不出來就留空並在 ``note`` 講明,不猜(D-026 第 6 條的同一條理:
    留白比造一個看似完整的名單安全)。
    """

    ticker: str
    display_name: str
    joined_on: str
    left_on: str
    source: str
    note: str


@dataclass(frozen=True, slots=True)
class UniverseSource:
    """一份名單的來源:叫什麼、在哪、覆蓋到哪一日、幾時抓的。"""

    name: str
    url: str
    coverage: str
    fetched_on: str


@dataclass(frozen=True, slots=True)
class UniverseListing:
    """登記上的一份名單。``key`` 是命令列用的名(一律 ASCII)。"""

    key: str
    title: str
    description: str
    members: tuple[UniverseMember, ...]
    membership: tuple[MembershipPeriod, ...]
    sources: tuple[UniverseSource, ...]


SP500_SOURCES: tuple[UniverseSource, ...] = (
    UniverseSource(
        name="fja05680/sp500",
        url="https://github.com/fja05680/sp500",
        coverage="1996-01-02 ~ 2026-06-30(逐次變動的成分歷史;MIT 授權)",
        fetched_on="2026-08-29",
    ),
    UniverseSource(
        name="wikipedia",
        url="https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        coverage="只有現役名單(用來補上一個來源 2026-06-30 之後的尾巴,並提供公司名)",
        fetched_on="2026-08-29",
    ),
)


def _read_membership(path: Path) -> tuple[MembershipPeriod, ...]:
    """讀成分歷史表。表由 ``experiments/2026-08-29-sp500-universe/build_membership.py``
    砌出來,是登記的正本;這裡只讀,不在程式裡另寫一份名單(單一定義)。"""
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return tuple(
        MembershipPeriod(
            ticker=row["ticker"].strip().upper(),
            display_name=row["display_name"].strip(),
            joined_on=row["joined_on"].strip(),
            left_on=row["left_on"].strip(),
            source=row["source"].strip(),
            note=row["note"].strip(),
        )
        for row in rows
    )


def _members_from(periods: tuple[MembershipPeriod, ...]) -> tuple[UniverseMember, ...]:
    """由成分期表取出唯一代號的名單。一個代號可以有幾段成分期(離開又回來),
    但名單上只出現一次。來源沒有公司名的(多數是已退市那批),顯示名用代號本身。"""
    names: dict[str, str] = {}
    for period in periods:
        if period.display_name or period.ticker not in names:
            names[period.ticker] = period.display_name
    return tuple(
        UniverseMember(ticker, "company", names[ticker] or ticker) for ticker in sorted(names)
    )


SP500_MEMBERSHIP: tuple[MembershipPeriod, ...] = _read_membership(SP500_MEMBERSHIP_FILE)

SP500_HISTORICAL_UNIVERSE: tuple[UniverseMember, ...] = _members_from(SP500_MEMBERSHIP)


def _dedupe(*groups: tuple[UniverseMember, ...]) -> tuple[UniverseMember, ...]:
    """按次序併幾份名單,同一個代號只保留**先出現**那一個。

    起步名單與標普 500 歷史成分有十隻股重疊(AAPL 一類)。先出現的贏,所以
    唯一入口查 AAPL 查到的仍是起步名單那一員,顯示名不會因為多登記一份名單而變。
    """
    seen: set[str] = set()
    merged: list[UniverseMember] = []
    for group in groups:
        for member in group:
            if member.ticker in seen:
                continue
            seen.add(member.ticker)
            merged.append(member)
    return tuple(merged)


# 登記在案的全部代號。唯一入口按這份查代號,**預設批次仍然是起步名單**——
# 登記與預設是兩件事,這裡分開幾份正是為了不把它們混做一件。
UNIVERSE_REGISTRY: tuple[UniverseMember, ...] = _dedupe(
    STARTER_UNIVERSE, FACTOR_ETF_UNIVERSE, SP500_HISTORICAL_UNIVERSE
)

NAMED_UNIVERSES: tuple[UniverseListing, ...] = (
    UniverseListing(
        key="starter",
        title="起步名單",
        description="SPY、QQQ 加十隻大型股;不指定代號時抓的就是這一份。",
        members=STARTER_UNIVERSE,
        membership=(),
        sources=(),
    ),
    UniverseListing(
        key="factor-etf",
        title="因子敞口 ETF",
        description="四隻 MSCI 因子 ETF(KARST-031 因子混合、KARST-036 因子輪動用)。",
        members=FACTOR_ETF_UNIVERSE,
        membership=(),
        sources=(),
    ),
    UniverseListing(
        key="sp500-historical",
        title="標普 500 歷史成分",
        description=(
            "1996-01-02 以來曾經入選標普 500 的全部代號,含已退市與已剔除那批,"
            "每個代號帶加入/剔除日期(KARST-065)。這是名單登記,不是「抓得到日線」"
            "的保證——退市代號免費行情源多數抓不到,缺口逐條寫在快照說明檔(D-026 第 6 條)。"
        ),
        members=SP500_HISTORICAL_UNIVERSE,
        membership=SP500_MEMBERSHIP,
        sources=SP500_SOURCES,
    ),
)


def universe_listing(key: str) -> UniverseListing:
    """按名取一份登記名單;查無此名即拒收,不猜。"""
    wanted = str(key).strip().lower()
    for listing in NAMED_UNIVERSES:
        if listing.key == wanted:
            return listing
    raise ValueError(
        f"宇宙名單登記上沒有「{key}」;現有:"
        f"{'、'.join(item.key for item in NAMED_UNIVERSES)}"
    )


def members_in_window(
    listing: UniverseListing, *, start: str, end: str
) -> tuple[UniverseMember, ...]:
    """名單上在 ``start``~``end`` 這段窗口內**曾經入選**的那批代號。

    判準是成分期與窗口有沒有重疊:加入日不遲過窗口尾、剔除日不早過窗口頭。
    沒有成分期的名單(起步、因子 ETF)整份回,它們本來就不帶成分歷史。
    """
    if not listing.membership:
        return listing.members
    wanted = {
        period.ticker
        for period in listing.membership
        if period.joined_on <= end and (not period.left_on or period.left_on >= start)
    }
    return tuple(member for member in listing.members if member.ticker in wanted)


def tickers_of(universe: tuple[UniverseMember, ...]) -> tuple[str, ...]:
    return tuple(member.ticker for member in universe)
