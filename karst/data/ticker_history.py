"""代號歷史對照:一個交易代號在**哪一段日子**屬於哪一個實體(KARST-082)。

D-026 第 2 條講明交易代號只是**有生效期的屬性**,實體編號才是主鍵。但直到本票之前,
代號→CIK 的錨定用的是 SEC ``company_tickers.json``——那份檔只講**代號今日屬誰**,
一個字都沒有講過它昨日屬誰。假設 A-011 就是這樣崩塌的:``BBBY`` 在今日那份對照解到
NEIGHBORHOOD INTELLIGENCE(CIK 1130713),而 1996 年以來的標普 500 成分股 ``BBBY``
是 Bed Bath & Beyond(CIK 886158)。用今日的對照去錨歷史成分,會**靜靜**把一家公司的
價格掛到另一家公司身上。

本檔改用兩份帶時間的 SEC 公開檔:

* ``cik-lookup-data.txt``——一百零五萬行的**名稱→CIK**表,保留歷史名稱(內含
  ``BED BATH & BEYOND INC:0000886158``)。它沒有代號、沒有日期,只回答「這個名稱
  曾經屬於哪個 CIK」。
* ``data.sec.gov/submissions/CIK<十位數>.json``——每個 CIK 的**名稱窗口**
  (``formerNames`` 逐條帶 from/to)與申報活躍期。它回答「這個 CIK 在那一日叫什麼名」。

兩份合起來才夠判代號回收:今日持有人若在成分期**結束之後**才改成現名,而該名稱在
名稱表上另有一個唯一的、成分期內活躍的更早持有者,即判定代號被回收,錨改回更早那個。

**判不到就列出來,不猜。** 名稱表有一百零五萬行,同名撞車與字尾雜訊(``KEYCORP`` 對
``KEYCORP /NEW/``、``BED BATH & BEYOND INC`` 對 ``BED BATH & BEYOND, INC.``)俯拾皆是;
拿市場簡稱去撞名,撞出來的多數是同名的舊實體或子公司。本檔的規矩是:**證據不足就
交人手辨**,``VERDICT_MANUAL`` 那一格永遠寫得出「為什麼判不到」。
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from ..errors import ContractViolation
from .errors import DataFetchFailed

SEC_CIK_LOOKUP_URL = "https://www.sec.gov/Archives/edgar/cik-lookup-data.txt"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

# 下載檔的落點:快取根之下自己一個目錄,與價格快照、宏觀快照並排(D-026 第 5 條)。
DEFAULT_SEC_CACHE = Path("data/sec")

# ----------------------------------------------------------------------
# 判詞:一個代號的錨是怎樣定出來的。落檔的每一列都帶住其中一個。
# ----------------------------------------------------------------------

VERDICT_CURRENT = "今日對照"
"""成分期一路連到今日,代號中途沒有易主的空間,錨取今日對照。"""

VERDICT_VERIFIED = "今日對照·已核實"
"""成分期已結束,但今日持有人在成分期之後沒有改過名,視為同一個實體一路持有。"""

VERDICT_RENAMED = "同一實體改名·非回收"
"""今日持有人成分期之後改過名,但它自己的申報一路貫穿成分期——是它自己改名
(ALLEGHENY TECHNOLOGIES INC → ATI INC),不是別人接收了這個代號。"""

VERDICT_RECYCLED = "代號回收·改錨"
"""今日持有人是在成分期之後才取得這個名稱與代號的;錨改回成分期內的持有人。"""

VERDICT_MANUAL = "人手待辨"
"""證據不足以判定。列出候選與理由,交人手裁決,**不猜**。"""

VERDICT_PLACEHOLDER = "佔位錨"
"""兩份來源都認不出這個代號當時屬誰,維持佔位錨(見 ``cik.placeholder_cik``)。"""

VERDICT_IDENTIFIED = "人手辨明"
"""``人手待辨`` / ``佔位錨`` 那一格經人手查證之後定了案,錨換上查實的 CIK。

自動裁決那五格一字不改;這個判詞只出現在人手裁決過的列上,並且**必須**在
``evidence`` 逐條寫明用了哪一份公開來源(SEC 名稱窗口、SEC 名稱→CIK 表、
維基百科標普 500 成分變動表)。查不出的不落這個判詞——維持 ``人手待辨`` 與佔位錨,
判不出就寫判不出(KARST-083)。"""

ANCHOR_COLUMNS = (
    "ticker",
    "cik",
    "valid_from",
    "valid_to",
    "display_name",
    "verdict",
    "evidence",
)


# ----------------------------------------------------------------------
# 名稱正規化
# ----------------------------------------------------------------------

_STATE_SUFFIX = re.compile(r"\s*/[A-Z][A-Z0-9]*/?\s*$")
_NON_ALNUM = re.compile(r"[^A-Z0-9]+")


def normalise_company_name(name: str) -> str:
    """把公司名收成可比對的形態:大寫、去掉 EDGAR 的州別尾註、只留字母數字與單空格。

    去州別尾註是必須的:EDGAR 同一家公司會有 ``KEYCORP`` 與 ``KEYCORP /NEW/`` 兩條,
    後者才是現存實體。只留字母數字則令 ``BED BATH & BEYOND INC`` 與
    ``BED BATH & BEYOND, INC.`` 收成同一個鍵——**它們是兩個不同的 CIK**,收成同一個鍵
    正是為了讓這種撞車浮出來被看見,而不是靠標點的有無靜靜分開。
    """
    text = str(name).strip().upper()
    previous = None
    while previous != text:
        previous = text
        text = _STATE_SUFFIX.sub("", text).strip()
    return " ".join(_NON_ALNUM.sub(" ", text).split())


def load_name_index(path: str | Path) -> dict[str, tuple[str, ...]]:
    """讀 ``cik-lookup-data.txt``,回傳「正規化名稱 → 該名稱用過的全部 CIK」。

    檔的每一行是 ``公司名:十位數CIK:``。公司名本身可以有冒號(極少數),故此
    **由右邊拆**:尾兩格是 CIK 與空字串,其餘全部是名字。
    """
    index: dict[str, set[str]] = {}
    with Path(path).open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split(":")
            if len(parts) < 3:
                continue
            cik = parts[-2].strip()
            name = ":".join(parts[:-2]).strip()
            if not name or not cik.isdigit():
                continue
            key = normalise_company_name(name)
            if key:
                index.setdefault(key, set()).add(cik.zfill(10))
    if not index:
        raise DataFetchFailed(f"名稱→CIK 表 {path} 讀出來是空的,當抓取失敗處理")
    return {key: tuple(sorted(value)) for key, value in index.items()}


# ----------------------------------------------------------------------
# 一個 CIK 的名稱窗口
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NameWindow:
    """一個 CIK 在 ``valid_from``~``valid_to`` 這段日子登記的名稱。

    ``valid_to`` 留空即「直到今日仍然是這個名」。日期取自 SEC ``formerNames``,
    不是本倉推斷出來的。
    """

    cik: str
    name: str
    valid_from: str
    valid_to: str


@dataclass(frozen=True, slots=True)
class EntityHistory:
    """一個 CIK 的身分史:現名、名稱窗口、今日掛住的代號、申報活躍期。"""

    cik: str
    current_name: str
    windows: tuple[NameWindow, ...]
    tickers: tuple[str, ...]
    first_filing: str
    last_filing: str


def _iso_day(value: object) -> str:
    """SEC 的時間戳寫成 ``2023-09-20T00:00:00.000Z``,只取日子那一截。"""
    text = str(value or "").strip()
    return text[:10] if len(text) >= 10 else ""


def parse_entity_history(payload: Mapping[str, object]) -> EntityHistory:
    """把 ``submissions/CIK….json`` 讀成身分史。

    ``formerNames`` 逐條帶 from/to;現名的生效起 = 全部舊名之中最晚那個 ``to``
    (沒有舊名即由第一次申報起),訖留空表示至今。SEC 的窗口偶有交疊
    (同一日換名的兩條記錄),照原文收下,不代它修——``names_at`` 因此回一個
    **集合**而不是單一個名。
    """
    cik = str(payload.get("cik", "")).strip().zfill(10)
    current_name = str(payload.get("name", "")).strip()

    windows: list[NameWindow] = []
    latest_end = ""
    for entry in payload.get("formerNames") or ():
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name", "")).strip()
        start, end = _iso_day(entry.get("from")), _iso_day(entry.get("to"))
        if not name:
            continue
        windows.append(NameWindow(cik=cik, name=name, valid_from=start, valid_to=end))
        latest_end = max(latest_end, end)

    filings = payload.get("filings") or {}
    recent = filings.get("recent") or {} if isinstance(filings, Mapping) else {}
    dates = [str(day) for day in (recent.get("filingDate") or ()) if str(day).strip()]
    older = filings.get("files") or () if isinstance(filings, Mapping) else ()
    starts = [str(item.get("filingFrom", "")) for item in older if isinstance(item, Mapping)]
    ends = [str(item.get("filingTo", "")) for item in older if isinstance(item, Mapping)]
    first_filing = min([day for day in [*dates, *starts] if day] or [""])
    last_filing = max([day for day in [*dates, *ends] if day] or [""])

    if current_name:
        windows.append(
            NameWindow(
                cik=cik,
                name=current_name,
                valid_from=latest_end or first_filing,
                valid_to="",
            )
        )

    tickers = tuple(
        str(item).strip().upper() for item in (payload.get("tickers") or ()) if str(item).strip()
    )
    return EntityHistory(
        cik=cik,
        current_name=current_name,
        windows=tuple(windows),
        tickers=tickers,
        first_filing=first_filing,
        last_filing=last_filing,
    )


def _covers(window: NameWindow, *, start: str, end: str) -> bool:
    """名稱窗口與 ``start``~``end`` 有沒有重疊。窗口兩端留空即當作無界。"""
    if window.valid_from and window.valid_from > end:
        return False
    if window.valid_to and window.valid_to < start:
        return False
    return True


def names_at(history: EntityHistory, *, start: str, end: str) -> tuple[str, ...]:
    """這個 CIK 在 ``start``~``end`` 之內登記過的名稱(可能不止一個)。"""
    return tuple(
        sorted({window.name for window in history.windows if _covers(window, start=start, end=end)})
    )


def filings_cover(history: EntityHistory, *, start: str, end: str) -> bool:
    """這個 CIK 的申報活躍期有沒有**整段**蓋住 ``start``~``end``。

    標普 500 成分股在成分期之內必然持續向 SEC 申報。一個只在 1994 年申報過四個月的
    空殼(``ATI INC /OK``)不可能是 1996–2015 的成分股,這一格就是用來把它擋走的。
    """
    if not history.first_filing or not history.last_filing:
        return False
    return history.first_filing <= start and history.last_filing >= end


def window_released_before(history: EntityHistory, *, name: str, day: str) -> bool:
    """這個 CIK 在 ``day`` 之前有沒有**放低**過 ``name`` 這個名稱。

    「接收一個已死品牌」的指紋:原主先停用那個名稱(或索性停止申報),之後才有人
    取而用之。兩家公司**同時**掛住同一個名稱(``SEA LTD`` 那一格),那不是接收,
    只是撞名——撞名不可以拿來當代號易主的證據。
    """
    key = normalise_company_name(name)
    for window in history.windows:
        if normalise_company_name(window.name) != key:
            continue
        if window.valid_to and window.valid_to < day:
            return True
        if history.last_filing and history.last_filing < day:
            return True
    return False


def names_adopted_after(history: EntityHistory, *, day: str) -> tuple[str, ...]:
    """這個 CIK 在 ``day`` **之後**才取得的名稱。

    代號回收的指紋:一家公司買下一個已死品牌之後改名,順帶把那個代號也接過來。
    """
    return tuple(
        sorted(
            {
                window.name
                for window in history.windows
                if window.valid_from and window.valid_from > day
            }
        )
    )


# ----------------------------------------------------------------------
# 錨的裁決
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TickerAnchor:
    """一個代號在一段生效期內錨到哪個實體,連判詞與證據。

    ``cik`` 可以是佔位錨(``PLACEHOLDER-…``)——判不到就寫判不到,不留一個看似
    可信的十位數字在表上。
    """

    ticker: str
    cik: str
    valid_from: str
    valid_to: str
    display_name: str
    verdict: str
    evidence: str


@dataclass(frozen=True, slots=True)
class AnchorInputs:
    """裁決一個代號所需的全部材料。全部由呼叫方備妥,本層不自己上網。"""

    ticker: str
    display_name: str
    joined_on: str
    left_on: str
    today_cik: str
    today_history: EntityHistory | None
    candidate_histories: Mapping[str, EntityHistory]
    name_index: Mapping[str, tuple[str, ...]]


def resolve_anchor(inputs: AnchorInputs) -> TickerAnchor:
    """按下列次序裁決一個代號在它那段成分期內的錨。

    1. **成分期未結束**(``left_on`` 留空):代號一路連到今日仍屬同一個成分股,
       中途沒有易主的空間,錨取今日對照(``VERDICT_CURRENT``)。
    2. **成分期已結束、今日對照無此代號**:兩份來源都認不出當時屬誰,維持佔位錨
       (``VERDICT_PLACEHOLDER``)。
    3. **成分期已結束、今日持有人在成分期之後沒有改過名**:視為同一個實體一路持有
       (``VERDICT_VERIFIED``)。
    4. **成分期已結束、今日持有人在成分期之後改過名、但它自己的申報一路貫穿成分期**:
       是它自己改名,不是別人接收了這個代號(``VERDICT_RENAMED``)。
    5. **成分期已結束、今日持有人在成分期之後改過名、而它自己當時根本未在申報**:
       它不可能是當時的持有人。逐個「後來才取得的名稱」反查名稱表,候選要同時過三關——
       (甲)不是今日持有人自己;(乙)申報活躍期**整段**覆蓋成分期(成分股在成分期內
       必然持續申報);(丙)在今日持有人取用該名稱**之前**已經放低它(名稱窗口已結束,
       或已停止申報)。**恰好一個**候選過關即判定代號回收,錨改回它(``VERDICT_RECYCLED``);
       零個或多於一個,一律交人手辨(``VERDICT_MANUAL``)——名稱表有一百零五萬行,
       撞名俯拾皆是,證據不足時列出來比猜一個安全。
    """
    ticker = inputs.ticker.strip().upper()
    span_start, span_end = inputs.joined_on, inputs.left_on

    if not span_end:
        if not inputs.today_cik:
            return TickerAnchor(
                ticker=ticker,
                cik="",
                valid_from=span_start,
                valid_to="",
                display_name=inputs.display_name,
                verdict=VERDICT_PLACEHOLDER,
                evidence="成分期仍未結束,但今日的代號→CIK 對照查無此代號",
            )
        return TickerAnchor(
            ticker=ticker,
            cik=inputs.today_cik,
            valid_from=span_start,
            valid_to="",
            display_name=inputs.display_name,
            verdict=VERDICT_CURRENT,
            evidence=f"成分期由 {span_start} 起一路未結束,代號今日仍屬 {inputs.today_cik}",
        )

    if not inputs.today_cik or inputs.today_history is None:
        return TickerAnchor(
            ticker=ticker,
            cik="",
            valid_from=span_start,
            valid_to=span_end,
            display_name=inputs.display_name,
            verdict=VERDICT_PLACEHOLDER,
            evidence=(
                f"成分期 {span_start}~{span_end} 已結束,今日的代號→CIK 對照查無此代號;"
                "名稱表沒有代號一欄,單憑代號認不出當時屬誰"
            ),
        )

    later = names_adopted_after(inputs.today_history, day=span_end)
    if not later:
        return TickerAnchor(
            ticker=ticker,
            cik=inputs.today_cik,
            valid_from=span_start,
            valid_to=span_end,
            display_name=inputs.display_name,
            verdict=VERDICT_VERIFIED,
            evidence=(
                f"成分期 {span_start}~{span_end} 結束後,{inputs.today_cik} 未改過名"
                f"(現名 {inputs.today_history.current_name});視為同一實體一路持有"
            ),
        )

    if filings_cover(inputs.today_history, start=span_start, end=span_end):
        return TickerAnchor(
            ticker=ticker,
            cik=inputs.today_cik,
            valid_from=span_start,
            valid_to=span_end,
            display_name=inputs.display_name,
            verdict=VERDICT_RENAMED,
            evidence=(
                f"{inputs.today_cik} 的申報由 {inputs.today_history.first_filing} 至 "
                f"{inputs.today_history.last_filing},一路貫穿成分期 {span_start}~{span_end}"
                f"(期內名稱:{'、'.join(names_at(inputs.today_history, start=span_start, end=span_end)) or '(無)'});"
                f"成分期後改名為「{'、'.join(later)}」是它自己改名,不是代號易主"
            ),
        )

    span_names = {normalise_company_name(name) for name in names_at(
        inputs.today_history, start=span_start, end=span_end
    )}
    found: dict[str, str] = {}
    for adopted in later:
        key = normalise_company_name(adopted)
        if not key or key in span_names:
            # 只是標點或州別尾註改動,不是易主
            continue
        adopted_on = min(
            [
                window.valid_from
                for window in inputs.today_history.windows
                if normalise_company_name(window.name) == key and window.valid_from
            ]
            or [""]
        )
        others = [
            cik for cik in inputs.name_index.get(key, ()) if cik != inputs.today_cik
        ]
        for cik in others:
            history = inputs.candidate_histories.get(cik)
            if history is None:
                continue
            if not filings_cover(history, start=span_start, end=span_end):
                continue
            if not adopted_on or not window_released_before(history, name=adopted, day=adopted_on):
                continue
            found[cik] = (adopted, adopted_on)

    if len(found) == 1:
        cik, (adopted, adopted_on) = next(iter(found.items()))
        # 生效訖不是成分期那一日:代號屬於原主的日子由它上市起,到它**放低這個名稱**
        # (或停止申報)為止,與它幾時被剔出指數無關。Bed Bath & Beyond 2017 年就
        # 離開了標普 500,但 BBBY 這個代號一直是它的,直到 2023 年它清盤為止。
        # 兩者混為一談,2017–2023 那幾年就會變成一段沒有主人的空白。
        released = min(
            [
                day
                for day in (
                    *(
                        window.valid_to
                        for window in inputs.candidate_histories[cik].windows
                        if normalise_company_name(window.name)
                        == normalise_company_name(adopted)
                        and window.valid_to
                    ),
                    inputs.candidate_histories[cik].last_filing,
                    adopted_on,
                )
                if day
            ]
            or [span_end]
        )
        return TickerAnchor(
            ticker=ticker,
            cik=cik,
            valid_from=span_start,
            valid_to=max(released, span_end),
            display_name=inputs.display_name,
            verdict=VERDICT_RECYCLED,
            evidence=(
                f"今日持有人 {inputs.today_cik} 的申報由 "
                f"{inputs.today_history.first_filing} 起,蓋不住成分期 {span_start}~{span_end},"
                f"它不可能是當時的持有人;它在成分期結束後才取得名稱「{adopted}」,"
                f"而同一名稱在 SEC 名稱表上另有唯一一個候選 {cik} 同時滿足:申報由 "
                f"{inputs.candidate_histories[cik].first_filing} 至 "
                f"{inputs.candidate_histories[cik].last_filing} 整段覆蓋成分期,"
                f"且已在 {inputs.today_cik} 取用該名稱之前放低它;判定代號回收,錨改回 {cik};"
                f"生效訖順延至 {max(released, span_end)}——代號屬原主的日子到它放低該名稱"
                "(或停止申報)為止,不是到它被剔出指數為止"
            ),
        )

    reason = (
        f"今日持有人 {inputs.today_cik} 的申報由 {inputs.today_history.first_filing} 起,"
        f"蓋不住成分期 {span_start}~{span_end},它不可能是當時的持有人;"
        f"它在成分期後才取得名稱({'、'.join(later)});"
    )
    if not found:
        reason += (
            "但名稱表上找不到一個同名、申報整段覆蓋成分期、"
            "而又在它取用該名稱之前已放低該名稱的候選,認不出當時屬誰"
        )
    else:
        reason += f"而同名的合資格候選不止一個({'、'.join(sorted(found))}),無法斷定是哪一個"

    # 認不出當時屬誰,還要決定「這段期間的錨寫什麼」。分兩格:
    #
    #   * 今日持有人的第一份申報**晚過成分期結束**——它當時根本未存在,絕不可能持有
    #     這個代號。留住它就是 A-011 那個錯法(把 SunTrust 2015–2019 的價格掛到
    #     Solidion Technology 身上)。改用佔位錨:「知道不是它,但未知是誰」是真話,
    #     一個看似可信的十位數字不是。
    #   * 今日持有人在成分期**之內**開始申報——它可能是期中成立的繼承實體(控股公司
    #     重組那一類),亦可能是代號回收。分不開就保留原錨,連同理由入人手待辨清單。
    impossible = bool(
        inputs.today_history.first_filing and inputs.today_history.first_filing > span_end
    )
    if impossible:
        reason += (
            f";其第一份申報 {inputs.today_history.first_filing} 晚過成分期結束 {span_end},"
            "當時它並不存在,故此不留它作錨,改用佔位錨"
        )
    else:
        reason += (
            f";其第一份申報 {inputs.today_history.first_filing} 落在成分期之內,"
            "可能是期中成立的繼承實體,排除不了,暫時保留原錨"
        )
    return TickerAnchor(
        ticker=ticker,
        cik="" if impossible else inputs.today_cik,
        valid_from=span_start,
        valid_to=span_end,
        display_name=inputs.display_name,
        verdict=VERDICT_MANUAL,
        evidence=reason,
    )


# ----------------------------------------------------------------------
# 對照表的讀寫與取用
# ----------------------------------------------------------------------


def write_anchor_table(path: str | Path, anchors: Sequence[TickerAnchor]) -> Path:
    """把對照表落檔。表是登記的正本,程式裡不另寫一份名單(單一定義)。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ANCHOR_COLUMNS))
        writer.writeheader()
        for anchor in sorted(anchors, key=lambda item: (item.ticker, item.valid_from)):
            writer.writerow(
                {
                    "ticker": anchor.ticker,
                    "cik": anchor.cik,
                    "valid_from": anchor.valid_from,
                    "valid_to": anchor.valid_to,
                    "display_name": anchor.display_name,
                    "verdict": anchor.verdict,
                    "evidence": anchor.evidence,
                }
            )
    return target


def read_anchor_table(path: str | Path) -> tuple[TickerAnchor, ...]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return tuple(
        TickerAnchor(
            ticker=row["ticker"].strip().upper(),
            cik=row["cik"].strip(),
            valid_from=row["valid_from"].strip(),
            valid_to=row["valid_to"].strip(),
            display_name=row["display_name"].strip(),
            verdict=row["verdict"].strip(),
            evidence=row["evidence"].strip(),
        )
        for row in rows
    )


def anchors_for_range(
    anchors: Iterable[TickerAnchor], *, ticker: str, start: str, end: str
) -> tuple[TickerAnchor, ...]:
    """一個代號在 ``start``~``end`` 這段**實際有成交的日子**之內,對照表講得出的錨。

    這一格與 ``anchor_map_for_window`` 的分別很要緊:窗口是「我們想要哪一段」,
    這裡問的是「這批價格本身落在哪一段」。免費行情源給的永遠是**代號今日持有人**
    的歷史;若一個代號的成分期在 2017 年已經結束,而抓回來的日線由 2026 年起,
    那批價格根本不是當年那隻成分股的,回一個空 tuple 讓呼叫方把它剔走。
    """
    symbol = str(ticker).strip().upper()
    return tuple(
        anchor
        for anchor in anchors
        if anchor.ticker == symbol
        and (not anchor.valid_from or anchor.valid_from <= end)
        and (not anchor.valid_to or anchor.valid_to >= start)
    )


def distinct_ciks(anchors: Iterable[TickerAnchor]) -> tuple[str, ...]:
    """一批錨之中不同的真 CIK(佔位與空白不算)。

    同一家公司離開名單又回來,兩段成分期錨到同一個 CIK,那不是易主;
    兩個不同的 CIK 才是。
    """
    return tuple(sorted({a.cik for a in anchors if a.cik and a.cik.isdigit()}))


def anchors_for_window(
    anchors: Iterable[TickerAnchor], *, start: str, end: str
) -> dict[str, TickerAnchor]:
    """取出 ``start``~``end`` 這段窗口用得着的「代號→錨」對照(挑錨那條規矩的正本)。

    ``anchor_map_for_window`` 與凍結時的生效期都由這一格生出來,挑法只有一份。
    """
    picked: dict[str, TickerAnchor] = {}
    for anchor in anchors:
        if anchor.valid_from and anchor.valid_from > end:
            continue
        if anchor.valid_to and anchor.valid_to < start:
            continue
        if not anchor.cik or not anchor.cik.isdigit():
            continue
        existing = picked.get(anchor.ticker)
        if existing is not None and existing.cik != anchor.cik:
            raise ContractViolation(
                f"代號 {anchor.ticker} 在窗口 {start}~{end} 之內錨到兩個實體"
                f"({existing.cik} 與 {anchor.cik});代號中途易主,這個窗口不可凍成一個快照,"
                "請按易主日期把窗口斬開"
            )
        picked[anchor.ticker] = anchor
    return picked


def anchor_map_for_window(
    anchors: Iterable[TickerAnchor], *, start: str, end: str
) -> dict[str, str]:
    """取出 ``start``~``end`` 這段窗口用得着的「代號→CIK」對照。

    一個代號在窗口之內**只可以有一個錨**。若對照表講明它在窗口中途易主,
    這裡即拒收——一個快照的價格表用代號當鍵,窗口跨了易主就無法分開兩家公司的
    價格,只能把窗口斬開再凍兩個快照。寧可拒收,不可靜靜挑一個。

    佔位錨與空白的 CIK 不入對照:管線見不到某個代號就自己補佔位錨,
    這裡重覆一次只會令兩處各有一份說法。
    """
    return {
        ticker: anchor.cik
        for ticker, anchor in anchors_for_window(anchors, start=start, end=end).items()
    }


def valid_to_for_window(
    anchors: Iterable[TickerAnchor], *, start: str, end: str
) -> dict[str, str]:
    """同一批窗口內的錨,取出「代號→生效訖」(留空即生效期未結束)。

    這是同實體別名那道閘(``resolve_alias_collisions``)規則第一關要的那一格:
    退了役的代號拿回來的日線是今日持有人的歷史,信不過。
    """
    return {
        ticker: anchor.valid_to
        for ticker, anchor in anchors_for_window(anchors, start=start, end=end).items()
    }


# ----------------------------------------------------------------------
# 同一個實體收到多過一條代號序列(KARST-084)
# ----------------------------------------------------------------------
#
# ``anchor_map_for_window`` 擋的是「一個代號錨到兩個實體」。反方向那一格
# ——**兩個代號錨到同一個實體**——直到 KARST-083 才浮出來:``BBT`` 與 ``TFC``
# 都錨到 0000092230(BB&T 改名做 Truist),``EQR`` 與 ``VMRK`` 都錨到 0000906107。
# 兩個代號一齊入表會撞同一個實體編號,管線那一層不會出聲,靜靜只留其中一條價格
# 序列——而兩條序列**不是同一批數字**:BBT 的日線由 18.55 行到 31.50,TFC 的由
# 24.43 行到 50.21,即免費行情源給的 ``BBT`` 根本是今日持有那三個字母的另一家公司。
#
# 留邊條要講得出理由,不可以靠登記次序決定。規則寫在下面,**全倉只有這一份**:
# 凍結管線與 KARST-083 的重凍腳本同呼叫 ``resolve_alias_collisions``。


ALIAS_RULE = (
    "同一個實體收到多過一條代號序列時,按次序裁決:"
    "(一)生效期未結束的優先——退了役的代號,免費行情源給的是**今日持有人**的歷史,"
    "信不過;仍然在用的那個代號才拿得到這家公司自己的序列。"
    "(二)生效期同樣未結束(或同樣已結束)——取真實日線較多的那條。"
    "(三)仍然分不出高下——兩條都剔走,不猜。"
)
"""這道閘的明文規則。說明檔逐字照錄,規則只有這一份正本。"""


@dataclass(frozen=True, slots=True)
class AliasCandidate:
    """凍結那一刻,一個代號帶住的三格材料。

    ``valid_to`` 留空即生效期未結束。``bar_count`` 是這個代號在這批數據裡的日線根數
    ——它是規則第二關那把尺,由呼叫方數,本層不去碰數據。
    """

    ticker: str
    cik: str
    valid_to: str
    bar_count: int


@dataclass(frozen=True, slots=True)
class AliasVerdict:
    """一次觸發的裁決:哪個實體、哪幾個代號、留了誰、為什麼。

    ``kept`` 留空即「分不出高下,兩條都剔」——那一格不是失敗,是規則第三關寫明的結果。
    ``reason`` 是給人讀的整句,說明檔逐條照抄。
    """

    cik: str
    tickers: tuple[str, ...]
    kept: str
    dropped: tuple[str, ...]
    reason: str


def _describe_candidate(candidate: AliasCandidate) -> str:
    span = "生效期未結束" if not candidate.valid_to else f"生效期訖 {candidate.valid_to}"
    return f"{candidate.ticker}({span};日線 {int(candidate.bar_count)} 根)"


def resolve_alias_collisions(
    candidates: Sequence[AliasCandidate],
) -> tuple[AliasVerdict, ...]:
    """按 ``ALIAS_RULE`` 裁決「兩個代號錨到同一個實體」,逐條回一個判詞。

    沒有撞的實體不會出現在結果裡——這個函數只講觸發了的那幾格。錨不是真 CIK 的
    (佔位錨、空白)一律不入這道閘:佔位錨本身就是逐個代號各自一個,撞不起來。
    """
    by_cik: dict[str, list[AliasCandidate]] = {}
    for candidate in candidates:
        cik = str(candidate.cik).strip()
        if not cik or not cik.isdigit():
            continue
        by_cik.setdefault(cik, []).append(candidate)

    verdicts: list[AliasVerdict] = []
    for cik, found in sorted(by_cik.items()):
        if len(found) < 2:
            continue
        group = sorted(found, key=lambda item: item.ticker)
        live = [item for item in group if not item.valid_to]

        if len(live) == 1:
            kept: AliasCandidate | None = live[0]
            why = (
                f"留低 {kept.ticker}:全組只有它生效期未結束,是這個實體仍然在用的代號;"
                "其餘那幾個已經退役,免費行情源給的是代號今日持有人的歷史,不是這家公司自己的"
            )
        else:
            pool = live if live else group
            ranked = sorted(pool, key=lambda item: (-int(item.bar_count), item.ticker))
            same = "同樣未結束" if live else "同樣已結束"
            if len(ranked) > 1 and int(ranked[0].bar_count) == int(ranked[1].bar_count):
                kept = None
                why = (
                    f"生效期{same},真實日線又同樣是 {int(ranked[0].bar_count)} 根,"
                    "分不出高下;按規則第三關兩條都剔走,不猜"
                )
            else:
                kept = ranked[0]
                why = (
                    f"留低 {kept.ticker}:生效期{same},取真實日線較多的那條"
                    f"({int(kept.bar_count)} 根,次名 {ranked[1].ticker} 只有 "
                    f"{int(ranked[1].bar_count)} 根)"
                )

        dropped = tuple(
            item.ticker for item in group if kept is None or item.ticker != kept.ticker
        )
        reason = (
            f"實體 {cik} 收到 {len(group)} 條代號序列("
            + "、".join(_describe_candidate(item) for item in group)
            + ");兩個代號一齊入表會撞同一個實體編號,管線只會留低其中一條價格序列而不出聲,"
            f"故此在此明剔。{why}。剔走:{'、'.join(dropped)}"
        )
        verdicts.append(
            AliasVerdict(
                cik=cik,
                tickers=tuple(item.ticker for item in group),
                kept=kept.ticker if kept is not None else "",
                dropped=dropped,
                reason=reason,
            )
        )
    return tuple(verdicts)


def dropped_by_alias(verdicts: Sequence[AliasVerdict]) -> tuple[str, ...]:
    """一批判詞合共剔走了哪些代號(排序、去重)。"""
    return tuple(sorted({ticker for verdict in verdicts for ticker in verdict.dropped}))


# ----------------------------------------------------------------------
# 抓取(SEC 要求 User-Agent 自報身分與聯絡方法)
# ----------------------------------------------------------------------


def _get(url: str, *, user_agent: str, timeout: float) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json,text/plain,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            if response.headers.get("Content-Encoding") == "gzip":
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    except (urllib.error.URLError, OSError) as exc:
        raise DataFetchFailed(f"{url} 抓不到({type(exc).__name__}: {exc})") from exc
    return raw


def fetch_cik_lookup(*, path: str | Path, user_agent: str, timeout: float) -> Path:
    """下載 ``cik-lookup-data.txt`` 到快取根;已在就原檔沿用,不重抓。"""
    target = Path(path)
    if target.exists() and target.stat().st_size > 0:
        return target
    raw = _get(SEC_CIK_LOOKUP_URL, user_agent=user_agent, timeout=timeout)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return target


def fetch_entity_history(
    cik: str, *, cache_dir: str | Path, user_agent: str, timeout: float
) -> EntityHistory:
    """抓一個 CIK 的申報摘要並讀成身分史;抓過的存快取,重跑不再打 SEC。"""
    padded = str(cik).strip().zfill(10)
    cache = Path(cache_dir) / f"CIK{padded}.json"
    if cache.exists() and cache.stat().st_size > 0:
        payload = json.loads(cache.read_text(encoding="utf-8"))
    else:
        raw = _get(
            SEC_SUBMISSIONS_URL.format(cik=padded), user_agent=user_agent, timeout=timeout
        )
        payload = json.loads(raw.decode("utf-8"))
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return parse_entity_history(payload)
