"""KARST-082 驗收:代號歷史對照(A-011 善後)。

不連網。SEC 那兩份檔的形態用小樣本重現,證五件事:

  1. 名稱正規化令 ``BED BATH & BEYOND INC`` 與 ``BED BATH & BEYOND, INC.`` 撞成同一個鍵
     ——它們是兩個不同的 CIK,撞成一鍵正是為了讓它浮出來,不靠標點靜靜分開。
  2. 申報摘要讀得出**帶日期的名稱窗口**,現名的生效起接在最後一個舊名之後。
  3. 裁決五種判詞各行其路,尤其:BBBY 在成分期內解到 Bed Bath & Beyond(CIK 886158),
     不是今日掛住 BBBY 那家公司;而只是自己改名的(ATI)不判成代號回收。
  4. 一個代號在同一個窗口內錨到兩個實體即拒收,不靜靜挑一個。
  5. 撤回錯配的代號映射之後,同一個代號可以重新掛到正確的實體上。
"""

from __future__ import annotations

import pytest

from karst import DefinitionStore
from karst.data.ticker_history import (
    VERDICT_CURRENT,
    VERDICT_MANUAL,
    VERDICT_PLACEHOLDER,
    VERDICT_RECYCLED,
    VERDICT_RENAMED,
    VERDICT_VERIFIED,
    AnchorInputs,
    TickerAnchor,
    anchor_map_for_window,
    anchors_for_range,
    distinct_ciks,
    filings_cover,
    load_name_index,
    names_adopted_after,
    names_at,
    normalise_company_name,
    parse_entity_history,
    read_anchor_table,
    resolve_anchor,
    write_anchor_table,
)
from karst.errors import ContractViolation, NotFound

LOOKUP_SAMPLE = "\n".join(
    [
        "BED BATH & BEYOND INC:0000886158:",
        "BED BATH & BEYOND, INC.:0001130713:",
        "BEYOND, INC.:0001130713:",
        "OVERSTOCK.COM, INC:0001130713:",
        "KEYCORP:0000036208:",
        "KEYCORP /NEW/:0000091576:",
        "ATI INC:0000929245:",
        "ATI INC:0001018963:",
        "ALLEGHENY TECHNOLOGIES INC:0001018963:",
        "",
        ":0001003197:",
    ]
)


def _submissions(cik, name, former, first, last, tickers=()):
    """砌一份 ``submissions/CIK….json`` 的最小形態。"""
    return {
        "cik": cik,
        "name": name,
        "tickers": list(tickers),
        "formerNames": [
            {"name": n, "from": f"{f}T00:00:00.000Z", "to": f"{t}T00:00:00.000Z"}
            for n, f, t in former
        ],
        "filings": {
            "recent": {"filingDate": [last]},
            "files": [{"filingFrom": first, "filingTo": last}],
        },
    }


# 今日掛住 BBBY 的那家公司:成分期內叫 Overstock,2025 年才改名頂上 Bed Bath & Beyond
OVERSTOCK = parse_entity_history(
    _submissions(
        1130713,
        "NEIGHBORHOOD INTELLIGENCE, INC.",
        [
            ("OVERSTOCK.COM, INC", "2006-02-07", "2023-11-03"),
            ("BEYOND, INC.", "2023-09-19", "2025-08-22"),
            ("BED BATH & BEYOND, INC.", "2025-09-17", "2026-08-13"),
        ],
        "2002-03-05",
        "2026-08-19",
        tickers=("BBBY",),
    )
)
# 當年那家 Bed Bath & Beyond
BED_BATH = parse_entity_history(
    _submissions(
        886158,
        "20230930-DK-Butterfly-1, Inc.",
        [("BED BATH & BEYOND INC", "1995-03-08", "2023-09-20")],
        "1995-02-03",
        "2023-12-04",
    )
)
# 只是自己改名:Allegheny Technologies → ATI Inc,申報一路貫穿成分期
ALLEGHENY = parse_entity_history(
    _submissions(
        1018963,
        "ATI INC",
        [("ALLEGHENY TECHNOLOGIES INC", "1999-12-13", "2022-06-22")],
        "1996-07-17",
        "2026-08-26",
        tickers=("ATI",),
    )
)
# 同名的空殼:1994 年申報過四個月就沒有下文,不可能是 1996–2015 的成分股
ATI_SHELL = parse_entity_history(
    _submissions(929245, "ATI INC /OK", [], "1994-09-02", "1994-12-12")
)


@pytest.fixture()
def name_index(tmp_path):
    path = tmp_path / "cik-lookup-data.txt"
    path.write_text(LOOKUP_SAMPLE, encoding="utf-8")
    return load_name_index(path)


# ----------------------------------------------------------------------
# 1. 名稱正規化與名稱表
# ----------------------------------------------------------------------


def test_標點不同的兩個名字收成同一個鍵():
    """A-011 的核心:兩家不同公司的名字只差標點,不可以靠標點分開。"""
    assert normalise_company_name("BED BATH & BEYOND INC") == "BED BATH BEYOND INC"
    assert normalise_company_name("BED BATH & BEYOND, INC.") == "BED BATH BEYOND INC"


def test_州別尾註剝走():
    assert normalise_company_name("KEYCORP /NEW/") == "KEYCORP"
    assert normalise_company_name("FREYR Battery, Inc. /DE/") == "FREYR BATTERY INC"


def test_名稱表把同名的幾個CIK一齊收起(name_index):
    assert name_index["BED BATH BEYOND INC"] == ("0000886158", "0001130713")
    assert name_index["KEYCORP"] == ("0000036208", "0000091576")
    assert "" not in name_index


# ----------------------------------------------------------------------
# 2. 名稱窗口
# ----------------------------------------------------------------------


def test_申報摘要讀得出帶日期的名稱窗口():
    assert BED_BATH.first_filing == "1995-02-03"
    assert BED_BATH.last_filing == "2023-12-04"
    assert names_at(BED_BATH, start="2015-01-02", end="2017-07-26") == (
        "BED BATH & BEYOND INC",
    )
    # 現名的生效起接在最後一個舊名之後,不會回頭蓋住成分期
    assert names_at(OVERSTOCK, start="2015-01-02", end="2017-07-26") == (
        "OVERSTOCK.COM, INC",
    )


def test_後來才取得的名稱認得出():
    later = names_adopted_after(OVERSTOCK, day="2017-07-26")
    assert "BED BATH & BEYOND, INC." in later
    assert "OVERSTOCK.COM, INC" not in later


def test_申報活躍期要整段蓋住成分期():
    assert filings_cover(BED_BATH, start="1999-10-01", end="2017-07-26")
    # 只在 1994 年申報過四個月的空殼蓋不住 1996–2015
    assert not filings_cover(ATI_SHELL, start="1996-01-02", end="2015-07-02")


# ----------------------------------------------------------------------
# 3. 裁決
# ----------------------------------------------------------------------


def _inputs(ticker, joined, left, today_cik, today_history, candidates, index, name=""):
    return AnchorInputs(
        ticker=ticker,
        display_name=name,
        joined_on=joined,
        left_on=left,
        today_cik=today_cik,
        today_history=today_history,
        candidate_histories=candidates,
        name_index=index,
    )


def test_成分期未結束即取今日對照(name_index):
    anchor = resolve_anchor(
        _inputs("AAPL", "2015-01-02", "", "0000320193", None, {}, name_index)
    )
    assert anchor.verdict == VERDICT_CURRENT
    assert anchor.cik == "0000320193"
    assert anchor.valid_to == ""


def test_BBBY在成分期內解到BedBathBeyond(name_index):
    """驗收條件那一條:BBBY 不可以錨到今日掛住這個代號的另一家公司。"""
    anchor = resolve_anchor(
        _inputs(
            "BBBY",
            "1999-10-01",
            "2017-07-26",
            "0001130713",
            OVERSTOCK,
            {"0000886158": BED_BATH},
            name_index,
        )
    )
    assert anchor.verdict == VERDICT_RECYCLED
    assert anchor.cik == "0000886158"
    # 生效訖順延到原主放低那個名稱那一日,不是被剔出指數那一日——
    # 2017–2023 那幾年 BBBY 仍然是 Bed Bath & Beyond 的代號
    assert anchor.valid_to == "2023-09-20"


def test_自己改名不判成代號回收(name_index):
    """ATI:今日持有人的申報一路貫穿成分期,那是它自己改名,同名空殼不可以頂上。"""
    anchor = resolve_anchor(
        _inputs(
            "ATI",
            "2000-01-03",
            "2015-07-02",
            "0001018963",
            ALLEGHENY,
            {"0000929245": ATI_SHELL},
            name_index,
        )
    )
    assert anchor.verdict == VERDICT_RENAMED
    assert anchor.cik == "0001018963"


def test_同名空殼撐不起整段成分期即不改錨(name_index):
    """成分期由 1996-01-02 起(那是成分歷史來源的第一日,不是真正的加入日),
    今日持有人的第一份申報比它晚了半年,蓋不住整段;但唯一的同名候選只在 1994 年
    申報過四個月,一樣撐不起。兩邊都不足以定案,即交人手辨,**原錨照留**——
    留一個「可能對」的錨,好過改去一個明顯是空殼的。"""
    anchor = resolve_anchor(
        _inputs(
            "ATI",
            "1996-01-02",
            "2015-07-02",
            "0001018963",
            ALLEGHENY,
            {"0000929245": ATI_SHELL},
            name_index,
        )
    )
    assert anchor.verdict == VERDICT_MANUAL
    assert anchor.cik == "0001018963"


def test_成分期後沒改過名即當作一路持有(name_index):
    steady = parse_entity_history(
        _submissions(1000180, "SANDISK CORP", [], "1996-05-29", "2019-05-07")
    )
    anchor = resolve_anchor(
        _inputs("SNDK", "2006-04-20", "2016-05-12", "0001000180", steady, {}, name_index)
    )
    assert anchor.verdict == VERDICT_VERIFIED
    assert anchor.cik == "0001000180"


def test_今日持有人當時未存在而又認不出原主即改用佔位錨(name_index):
    """認不出就寫認不出:留一個已知是錯的十位數字,正是 A-011 那個錯法。

    SE 的成分期 2007–2017 是 Spectra Energy 的;今日掛住 SE 的 Sea Limited 要到
    2017-04 才第一次申報,絕不可能是當時的持有人。名稱表認不出當年是誰,
    於是這一段改用佔位錨,並列入人手待辨清單。"""
    sea = parse_entity_history(
        _submissions(1703399, "Sea Ltd", [], "2017-04-24", "2026-08-27", tickers=("SE",))
    )
    anchor = resolve_anchor(
        _inputs("SE", "2007-01-03", "2017-02-27", "0001703399", sea, {}, name_index)
    )
    assert anchor.verdict == VERDICT_MANUAL
    assert anchor.cik == ""
    assert "佔位錨" in anchor.evidence


def test_今日對照查無此代號即佔位錨(name_index):
    anchor = resolve_anchor(
        _inputs("AET", "1996-01-02", "2018-11-29", "", None, {}, name_index)
    )
    assert anchor.verdict == VERDICT_PLACEHOLDER
    assert anchor.cik == ""


# ----------------------------------------------------------------------
# 4. 對照表的取用
# ----------------------------------------------------------------------


def _anchor(ticker, cik, valid_from, valid_to):
    return TickerAnchor(
        ticker=ticker,
        cik=cik,
        valid_from=valid_from,
        valid_to=valid_to,
        display_name="",
        verdict=VERDICT_CURRENT,
        evidence="",
    )


def test_窗口內錨到兩個實體即拒收():
    anchors = [
        _anchor("SNDK", "0001000180", "2006-04-20", "2019-05-07"),
        _anchor("SNDK", "0002023554", "2025-11-28", ""),
    ]
    with pytest.raises(ContractViolation, match="錨到兩個實體"):
        anchor_map_for_window(anchors, start="2015-01-02", end="2026-08-28")
    # 窗口收窄到只碰得到一段,就解得出
    assert anchor_map_for_window(anchors, start="2015-01-02", end="2016-12-30") == {
        "SNDK": "0001000180"
    }


def test_佔位錨不入對照():
    anchors = [_anchor("AET", "", "1996-01-02", "2018-11-29")]
    assert anchor_map_for_window(anchors, start="2015-01-02", end="2026-08-28") == {}


def test_行情落在成分期之外即無錨可取():
    anchors = [_anchor("BBBY", "0000886158", "1999-10-01", "2023-09-20")]
    assert anchors_for_range(anchors, ticker="BBBY", start="2015-01-02", end="2017-01-01")
    # 2026 年那批日線屬後來的持有人,不是當年那隻成分股
    assert not anchors_for_range(
        anchors, ticker="BBBY", start="2026-07-17", end="2026-08-27"
    )


def test_同一家公司離開又回來不算易主():
    anchors = [
        _anchor("EQT", "0000033213", "2008-12-19", "2018-11-13"),
        _anchor("EQT", "0000033213", "2022-10-03", ""),
    ]
    assert distinct_ciks(anchors) == ("0000033213",)


def test_對照表落檔再讀回一字不差(tmp_path):
    anchors = [
        _anchor("BBBY", "0000886158", "1999-10-01", "2023-09-20"),
        _anchor("AET", "", "1996-01-02", "2018-11-29"),
    ]
    path = write_anchor_table(tmp_path / "anchors.csv", anchors)
    # 落檔按代號與生效起排序,讀回來一字不差
    assert read_anchor_table(path) == tuple(
        sorted(anchors, key=lambda item: (item.ticker, item.valid_from))
    )


# ----------------------------------------------------------------------
# 5. 撤回錯配
# ----------------------------------------------------------------------


def test_撤回錯配之後代號可以重掛到正確的實體():
    with DefinitionStore.open() as store:
        wrong = store.register_entity(
            kind="company", display_name="Neighborhood Intelligence", cik="0001130713"
        )
        store.register_ticker(wrong, "BBBY", valid_from="2015-01-02")
        assert store.resolve_ticker("BBBY", "2016-06-01") == wrong

        right = store.register_entity(
            kind="company", display_name="Bed Bath & Beyond", cik="0000886158"
        )
        # 未撤回之前,日子重疊那一關會擋住正確那一段寫不進去
        with pytest.raises(Exception):
            store.register_ticker(right, "BBBY", valid_from="2015-01-02")

        store.retract_ticker("BBBY", entity_id=wrong, valid_from="2015-01-02")
        store.register_ticker(right, "BBBY", valid_from="2015-01-02")
        assert store.resolve_ticker("BBBY", "2016-06-01") == right
        # 舊實體本身不刪:舊快照仍然引用得到它的實體編號
        assert store.get_entity(wrong).cik == "0001130713"


def test_撤回查無此段即拋錯():
    with DefinitionStore.open() as store:
        entity = store.register_entity(kind="company", display_name="X", cik="0000000123")
        with pytest.raises(NotFound):
            store.retract_ticker("XXX", entity_id=entity, valid_from="2015-01-02")
