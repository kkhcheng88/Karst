# -*- coding: utf-8 -*-
"""KARST-141 case-control pair definitions.

Each pair: a winner that (claimed) rose ~10x or more, matched against a loser in
the same industry whose investment thesis in the same year was materially similar.

`base_year` = the year BEFORE the winner's take-off. All "ex-ante observable"
measurements are taken as of the END of base_year, so nothing after take-off
leaks in.

`window` = (start, end) used to measure the actual multiple from the trough.
"""

PAIRS = [
    dict(
        pid="P01", cause="new_product_cycle",
        winner="BE", loser="PLUG",
        industry="Fuel cell / distributed power",
        base_year=2023, window=("2023-06-01", "2026-09-01"),
        thesis="Both sold the same story going into 2024: clean on-site power / "
               "hydrogen demand inflecting on policy support (IRA credits) and "
               "data-centre power scarcity; both were loss-making with negative "
               "gross margin history.",
    ),
    dict(
        pid="P02", cause="turnaround",
        winner="AMD", loser="INTC",
        industry="x86 / general-purpose processors",
        base_year=2015, window=("2015-06-01", "2022-01-01"),
        thesis="Both were pitching an architecture/process turnaround into 2016: "
               "AMD on Zen, Intel on 10nm plus its own accelerator push. Same end "
               "markets (PC, server CPU), same year, same 'next node wins' thesis.",
    ),
    dict(
        pid="P03", cause="turnaround",
        winner="ANF", loser="GAP",
        industry="US mall apparel retail",
        base_year=2020, window=("2020-12-01", "2026-09-01"),
        thesis="Both were post-COVID mall-apparel turnarounds: shrink the store "
               "fleet, push digital, restore merchandise margin. Same channel, "
               "same year, same 'the brand still has equity' argument. (First "
               "choice of loser was Express/EXPR, which filed for bankruptcy in "
               "2024 and has been delisted - yfinance returns NO_DATA for it, so "
               "Gap was substituted as a surviving same-thesis comparator. Note "
               "this substitution itself softens the contrast: Gap survived.)",
    ),
    dict(
        pid="P04", cause="cycle_reversal",
        winner="AR", loser="CRK",
        industry="Appalachia / Haynesville natural gas E&P",
        base_year=2020, window=("2020-12-01", "2026-09-01"),
        thesis="Both were levered US natural-gas producers selling the identical "
               "2021 thesis: gas price reversal plus LNG export pull, with "
               "deleveraging as the equity kicker.",
    ),
    dict(
        pid="P05", cause="cycle_reversal",
        winner="BLDR", loser="BZH",
        industry="US residential construction chain",
        base_year=2011, window=("2011-06-01", "2022-01-01"),
        thesis="Both were leveraged plays on the same US housing recovery from the "
               "2011 trough; both had been near-death in 2009-2011.",
    ),
    dict(
        pid="P06", cause="operating_leverage",
        winner="FTNT", loser="CHKP",
        industry="Enterprise cyber security",
        base_year=2016, window=("2016-12-01", "2022-06-01"),
        thesis="Both sold the same secular story - enterprise security budgets "
               "compounding double digits, firewall/appliance refresh cycle - to "
               "the same buyers in 2017. (First choice of loser was SecureWorks/"
               "SCWX, acquired by Sophos in 2025 and delisted; yfinance returns "
               "NO_DATA. Check Point is the surviving same-thesis comparator and "
               "was in fact the more profitable company in 2016.)",
    ),
    dict(
        pid="P07", cause="unit_economics",
        winner="WING", loser="LOCO",
        industry="US fast-casual restaurant franchising",
        base_year=2015, window=("2015-12-01", "2025-06-01"),
        thesis="Both 2014-2015 IPO-era fast-casual chains pitching national unit "
               "growth off a small regional base with a franchise/company hybrid "
               "model. (First choice of loser was Potbelly/PBPB - yfinance returns "
               "NO_DATA - so El Pollo Loco, the other 2014-15 fast-casual IPO with "
               "the same national-expansion pitch, was used.)",
    ),
    dict(
        pid="P08", cause="new_product_cycle",
        winner="DXCM", loser="SENS",
        industry="Continuous glucose monitoring devices",
        base_year=2016, window=("2016-01-01", "2022-01-01"),
        thesis="Both were CGM pure-plays pitching the same TAM: diabetics moving "
               "off fingersticks onto continuous sensors, with reimbursement as "
               "the unlock.",
    ),
    dict(
        pid="P09", cause="bottleneck",
        winner="CLS", loser="BHE",
        industry="Electronics manufacturing services / data-centre hardware",
        base_year=2022, window=("2022-06-01", "2026-09-01"),
        thesis="Both mid-cap EMS providers pitching the same AI/data-centre "
               "hardware build-out as the growth driver into 2023.",
    ),
    dict(
        pid="P10", cause="bottleneck",
        winner="ACLS", loser="ASYS",
        industry="Semiconductor capital equipment",
        base_year=2019, window=("2019-06-01", "2024-06-01"),
        thesis="Both small-cap semi-equipment names levered to the same power / "
               "silicon-carbide and mature-node capex cycle into 2020-2021.",
    ),
    dict(
        pid="P11", cause="cycle_reversal",
        winner="WFRD", loser="NBR",
        industry="Oilfield services",
        base_year=2021, window=("2021-01-01", "2026-09-01"),
        thesis="Both levered oilfield-service names pitching the identical 2021-22 "
               "shale-activity recovery. Weatherford had just exited Chapter 11 "
               "with debt written down; Nabors carried its debt through. KEPT "
               "DELIBERATELY AS A NEGATIVE CONTROL: the winner's pre-take-off "
               "price history does not exist (post-reorg equity starts 2021-01), "
               "so no ex-ante comparison is possible. Excluded from checklist "
               "induction; retained to show what an unresearchable case looks "
               "like.",
    ),
]

CAUSE_LABEL = {
    "bottleneck": "樽頸(供給受限)",
    "new_product_cycle": "新產品週期",
    "turnaround": "轉身",
    "cycle_reversal": "週期反轉",
    "operating_leverage": "經營槓桿",
    "unit_economics": "單位經濟複製",
}
