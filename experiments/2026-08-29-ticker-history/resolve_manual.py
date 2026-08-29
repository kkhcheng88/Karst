"""把 KARST-082 留低的 32 個人手待辨代號逐個辨明,補入對照表(KARST-083 第一至二步)。

跑法(倉根)::

    python experiments/2026-08-29-ticker-history/resolve_manual.py

**對照規則不變。** ``karst.data.ticker_history.resolve_anchor`` 那五格自動裁決一字不改;
本檔只處理它明文交出來的那一格——判詞 ``人手待辨`` 與 ``佔位錨``,即規則自己講「證據
不足,交人手」的那 32 段成分期。人手裁決落一個新判詞 ``人手辨明``(見
``VERDICT_IDENTIFIED``);查不出的會落 ``未能辨明`` 並留佔位錨,**本次無一落入此格**。

證據三源(每一列的 ``evidence`` 逐條寫明用了哪一源):

  1. **SEC 名稱窗口** —— ``data.sec.gov/submissions/CIK<十位數>.json`` 的 ``formerNames``
     逐條帶 from/to,加申報活躍期的頭尾。這是主證據:名稱窗口與成分期對得上、申報
     活躍期整段覆蓋成分期,才算辨明。
  2. **SEC 名稱→CIK 表** —— ``data/sec/cik-lookup-data.txt``,保留歷史名,由公司名反查 CIK。
  3. **維基百科標普 500 成分變動表** —— ``Historical components of the S&P 500`` 一頁列出
     每次變動的日子、代號與公司名。這是唯一把**代號**連到**公司名**的來源;SEC 兩份
     檔都沒有代號一欄,正是 082 判不出這 32 個的原因。

一段成分期之內上市體真的換過人的(AET、ESRX、TWX),按 SEC 名稱窗口拆成多列,
不把整段算到其中一家頭上。拆點的來歷逐條寫在 ``evidence``。
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from karst.data.ticker_history import (  # noqa: E402
    VERDICT_IDENTIFIED,
    VERDICT_MANUAL,
    VERDICT_PLACEHOLDER,
    TickerAnchor,
    read_anchor_table,
    write_anchor_table,
)

ANCHOR_TABLE = REPO_ROOT / "karst" / "data" / "universes" / "sp500_ticker_anchors.csv"
OUT_DIR = Path(__file__).resolve().parent
RESOLVED_FILE = OUT_DIR / "manual-review-resolved.csv"
CHANGED_FILE = OUT_DIR / "anchor-changes-083.csv"

WIKI = "維基百科《Historical components of the S&P 500》成分變動表(2026-08-30 取)"
SUBM = "SEC submissions"
LOOKUP = "SEC cik-lookup-data.txt"


# 鍵是 (代號, 成分期起, 成分期訖);值是這一段要換上的一列或多列錨。
# 多列即「一段成分期之內上市體換過人」,拆點的來歷寫在 evidence。
RESOLUTIONS: dict[tuple[str, str, str], list[dict[str, str]]] = {
    ("ADT", "2012-10-02", "2016-05-02"): [
        {
            "cik": "0001546640",
            "display_name": "ADT Corp.",
            "evidence": (
                f"{WIKI}:2012-10-01 加入、2016-05-03 剔除,兩次都寫代號 ADT、公司名 ADT。"
                f"{LOOKUP}:ADT CORP → 0001546640。{SUBM} 0001546640:申報 2012-04-10~2016-06-14,"
                "整段覆蓋成分期 2012-10-02~2016-05-02,收購完成後即停止申報。"
                "今日持有 ADT 代號的 0001703056(ADT Inc.)申報由 2017-04-11 才起,是 2018 年重新上市的"
                "另一家公司,不是當年那隻成分股"
            ),
        }
    ],
    ("AET", "1996-01-02", "2018-11-29"): [
        {
            "valid_from": "1996-01-02",
            "valid_to": "2000-12-01",
            "cik": "0001013761",
            "display_name": "Aetna Inc. (1996-2000)",
            "evidence": (
                f"{LOOKUP}:AETNA INC → 0001013761。{SUBM} 0001013761(今名 AETNA INC /CT/):"
                "名稱窗口 AETNA INC 1996-07-16~2000-11-30,申報 1996-06-12 起。"
                "拆點 2000-12-01 取自名稱窗口——同日另一個 CIK 接上同一個名(見下一列)。"
                "本段在快照窗口(2015-01-02 起)之外"
            ),
        },
        {
            "valid_from": "2000-12-01",
            "valid_to": "2018-11-29",
            "cik": "0001122304",
            "display_name": "Aetna Inc.",
            "evidence": (
                f"{WIKI}:2018-12-03 剔除,代號 AET、公司名 Aetna,理由 CVS 收購 Aetna。"
                f"{LOOKUP}:AETNA INC /PA/ → 0001122304。{SUBM} 0001122304:名稱窗口 "
                "AETNA U S HEALTHCARE INC 2000-09-01~2000-12-01,其後即 AETNA INC;"
                "申報 2000-09-01~2019-02-14,覆蓋成分期餘下整段"
            ),
        },
    ],
    ("ANDV", "2007-09-27", "2018-10-01"): [
        {
            "cik": "0000050104",
            "display_name": "Andeavor (前稱 Tesoro)",
            "evidence": (
                f"{WIKI}:2018-10-01 剔除,代號 ANDV、公司名 Andeavor。"
                f"{LOOKUP}:ANDEAVOR → 0000050104。{SUBM} 0000050104:名稱窗口 "
                "TESORO PETROLEUM CORP 1994-11-28~2004-11-05、TESORO CORP 2004-11-09~2017-08-01、"
                "ANDEAVOR 2017-08-08~2018-10-11;申報 1994-01-07 起,整段覆蓋成分期。"
                "同一實體改名兼換代號(TSO→ANDV),不是代號回收"
            ),
        }
    ],
    ("APC", "1997-07-28", "2019-08-09"): [
        {
            "cik": "0000773910",
            "display_name": "Anadarko Petroleum Corp.",
            "evidence": (
                f"{WIKI}:2019-08-09 剔除,代號 APC、公司名 Anadarko Petroleum。"
                f"{LOOKUP}:ANADARKO PETROLEUM CORP → 0000773910。{SUBM} 0000773910:"
                "申報 1994-02-14 起,整段覆蓋成分期(被 Occidental 收購後仍以子公司身分申報)。"
                "今日持有 APC 代號的 0002080921(ARKO Petroleum)申報 2025-09-15 才起,當時並不存在"
            ),
        }
    ],
    ("ATI", "1996-01-02", "2015-07-02"): [
        {
            "cik": "0001018963",
            "display_name": "Allegheny Technologies Inc.",
            "evidence": (
                f"{WIKI}:2015-07-02 剔除,代號 ATI、公司名 Allegheny Technologies——"
                "與今日持有 ATI 代號的 0001018963 是同一家。"
                f"{SUBM} 0001018963:名稱窗口 ALLEGHENY TELEDYNE INC 1996-07-17~1999-08-25、"
                "ALLEGHENY TECHNOLOGIES INC 1999-12-13~2022-06-22、其後 ATI INC。"
                "原錨確認正確:那是同一實體自己改名,不是代號回收。"
                "成分期起點 1996-01-02 是成分歷史來源的第一日,不是真正的加入日;"
                "1996-07 之前的一截在快照窗口之外"
            ),
        }
    ],
    ("BBT", "1997-12-04", "2019-12-09"): [
        {
            "cik": "0000092230",
            "display_name": "BB&T Corp.",
            "evidence": (
                f"{LOOKUP}:BB&T CORP → 0000092230。{SUBM} 0000092230(今名 TRUIST FINANCIAL CORP):"
                "名稱窗口 SOUTHERN NATIONAL CORP 1994-05-19~1997-05-14、"
                "BB&T CORP 1997-06-06~2019-12-06;申報 1994-02-14 起,整段覆蓋成分期。"
                "本倉成分歷史 sp500_historical.csv:BBT 於 2019-12-09 剔除,同日 TFC(Truist Financial)"
                "加入——同一實體改名換代號。原錨 0001108134(Beacon Financial)申報 2000-03-10 才起,"
                "蓋不住 1997 年的成分期,判定為錯"
            ),
        }
    ],
    ("CAM", "2008-01-29", "2016-04-04"): [
        {
            "cik": "0000941548",
            "display_name": "Cameron International Corp.",
            "evidence": (
                f"{WIKI}:2016-04-04 剔除,代號 CAM、公司名 Cameron International。"
                f"{LOOKUP}:CAMERON INTERNATIONAL CORP → 0000941548。{SUBM} 0000941548:"
                "名稱窗口 COOPER CAMERON CORP 1995-08-10~2006-05-17、其後 CAMERON INTERNATIONAL CORP;"
                "申報 1995-08-10~2016-04-14,整段覆蓋成分期,被 Schlumberger 收購後即停止申報"
            ),
        }
    ],
    ("COL", "2001-07-02", "2018-11-27"): [
        {
            "cik": "0001137411",
            "display_name": "Rockwell Collins Inc.",
            "evidence": (
                f"{WIKI}:2018-12-03 剔除,代號 COL、公司名 Rockwell Collins。"
                f"{LOOKUP}:ROCKWELL COLLINS INC → 0001137411。{SUBM} 0001137411:"
                "申報 2001-04-12~2018-12-07,整段覆蓋成分期,被 United Technologies 收購後即停止申報"
            ),
        }
    ],
    ("CSRA", "2015-11-30", "2018-04-04"): [
        {
            "cik": "0001646383",
            "display_name": "CSRA Inc.",
            "evidence": (
                f"{WIKI}:2015-12-01 加入、2018-04-04 剔除,兩次都寫代號 CSRA、公司名 CSRA。"
                f"{LOOKUP}:CSRA INC. → 0001646383。{SUBM} 0001646383:名稱窗口 "
                "Computer Sciences Government Services Inc 2015-07-10~2015-11-06、其後 CSRA Inc.;"
                "申報 2015-07-10~2018-05-10,整段覆蓋成分期"
            ),
        }
    ],
    ("DD", "1996-01-02", "2017-09-01"): [
        {
            "cik": "0000030554",
            "display_name": "E. I. du Pont de Nemours and Co.",
            "evidence": (
                f"{WIKI}:2017-09-01 剔除,代號 DD、公司名 DuPont(與 Dow 合併成 DowDuPont)。"
                f"{LOOKUP}:DUPONT E I DE NEMOURS & CO → 0000030554。{SUBM} 0000030554"
                "(今名 EIDP, Inc.):名稱窗口 DUPONT E I DE NEMOURS & CO 1994-01-06~2022-11-04;"
                "申報 1994-01-06 起,整段覆蓋成分期。原錨 0001666700(DuPont de Nemours, Inc.)"
                "申報 2016-03-01 才起,是 2019 年分拆出來的另一家,只對得上 2019-06-03 起那一段成分期"
            ),
        }
    ],
    ("DOW", "1996-01-02", "2017-09-01"): [
        {
            "cik": "0000029915",
            "display_name": "The Dow Chemical Co.",
            "evidence": (
                f"{WIKI}:2017-09-01 剔除,代號 DOW、公司名 Dow Chemical Company。"
                f"{LOOKUP}:DOW CHEMICAL CO /DE/ → 0000029915。{SUBM} 0000029915:"
                "申報 1994-05-16 起,整段覆蓋成分期(合併後仍以子公司身分申報)。"
                "0001751788(Dow Inc.)申報 2018-09-07 才起,只對得上 2019-04-02 起那一段成分期"
            ),
        }
    ],
    ("DXC", "1996-01-02", "2015-12-01"): [
        {
            "cik": "0000023082",
            "display_name": "Computer Sciences Corp.",
            "evidence": (
                f"{WIKI}:2015-12-01 剔除,代號 CSC、公司名 Computer Sciences Corporation,"
                "理由「CSC 完成分拆 CSRA」——與本段成分期的訖日一字不差,同日 CSRA 加入。"
                f"{LOOKUP}:COMPUTER SCIENCES CORP → 0000023082。{SUBM} 0000023082:"
                "申報 1994-01-25~2018-02-12,整段覆蓋成分期。"
                "成分歷史來源以最終代號 DXC 記述 CSC 這一段;2017-04-04 起那一段才是 "
                "0001688568(DXC Technology,由 CSC 與 HPE 企業服務合併而成)"
            ),
        }
    ],
    ("EA", "2002-07-22", ""): [
        {
            "cik": "0000712515",
            "display_name": "Electronic Arts Inc.",
            "evidence": (
                f"{LOOKUP}:ELECTRONIC ARTS INC → 0000712515。{SUBM} 0000712515:"
                "今日代號欄仍是 EA,申報 1994-08-09 起一路至 2026-08-14,整段覆蓋成分期。"
                f"{WIKI}:2026-08-05 剔除,代號 EA、公司名 Electronic Arts(財團私有化)——"
                "本倉成分歷史仍記它在名單上,兩者的分別已記於 sp500_historical.csv 的註"
            ),
        }
    ],
    ("EMC", "1996-03-28", "2016-09-07"): [
        {
            "cik": "0000790070",
            "display_name": "EMC Corp.",
            "evidence": (
                f"{WIKI}:2016-09-08 剔除,代號 EMC、公司名 EMC Corporation(Dell 收購)。"
                f"{LOOKUP}:EMC CORP → 0000790070。{SUBM} 0000790070:申報 1994-02-14 起,"
                "整段覆蓋成分期(被 Dell 收購後仍以子公司身分申報)"
            ),
        }
    ],
    ("EQR", "2001-12-03", ""): [
        {
            "cik": "0000906107",
            "display_name": "Equity Residential",
            "evidence": (
                f"{LOOKUP}:EQUITY RESIDENTIAL → 0000906107。{SUBM} 0000906107:名稱窗口 "
                "EQUITY RESIDENTIAL PROPERTIES TRUST 1994-02-10~2002-10-30、"
                "EQUITY RESIDENTIAL 2002-11-13~2026-08-12,今名 VIVMARK RESIDENTIAL、代號 VMRK。"
                "「今日對照查無 EQR」的原因就在這裡:同一實體 2026-08 改名換代號,仍在名單上。"
                f"{WIKI}:現役名單載 VMRK/Vivmark Residential"
            ),
        }
    ],
    ("ESRX", "2003-09-26", "2018-12-21"): [
        {
            "valid_from": "2003-09-26",
            "valid_to": "2012-04-03",
            "cik": "0000885721",
            "display_name": "Express Scripts Inc. (2003-2012)",
            "evidence": (
                f"{LOOKUP}:EXPRESS SCRIPTS INC → 0000885721。{SUBM} 0000885721:"
                "申報 1996-05-10~2018-04-20。拆點 2012-04-03 取自 "
                f"{WIKI}:當日因「Express Scripts 收購 Medco」而剔除 MHS,"
                "同時新設的控股公司 0001532063 接手做上市母體。本段在快照窗口之外"
            ),
        },
        {
            "valid_from": "2012-04-03",
            "valid_to": "2018-12-21",
            "cik": "0001532063",
            "display_name": "Express Scripts Holding Co.",
            "evidence": (
                f"{WIKI}:2018-12-24 剔除,代號 ESRX、公司名 Express Scripts,理由 Cigna 收購。"
                f"{SUBM} 0001532063:名稱窗口 Aristotle Holding, Inc. 2011-10-06~2011-11-18、"
                "其後 Express Scripts Holding Co.;申報 2011-10-06~2019-07-26,覆蓋成分期餘下整段"
            ),
        },
    ],
    ("EVHC", "2016-12-02", "2018-10-11"): [
        {
            "cik": "0001678531",
            "display_name": "Envision Healthcare Corp.",
            "evidence": (
                f"{WIKI}:2016-12-02 加入、2018-10-11 剔除,兩次都寫代號 EVHC、"
                "公司名 Envision Healthcare。"
                f"{LOOKUP}:ENVISION HEALTHCARE CORP 有兩個 CIK。{SUBM} 分辨:"
                "0001678531 名稱窗口 New Amethyst Corp. 2016-08-04~2016-11-29、"
                "其後 Envision Healthcare Corp,申報 2016-08-04~2019-02-14,整段覆蓋成分期;"
                "0001344154 申報止於 2014-06-20,蓋不住成分期,排除"
            ),
        }
    ],
    ("FB", "2013-12-23", "2022-06-09"): [
        {
            "cik": "0001326801",
            "display_name": "Facebook Inc.",
            "evidence": (
                f"{WIKI}:2013-12-23 加入,代號 FB、公司名 Facebook。"
                f"{LOOKUP}:FACEBOOK INC → 0001326801。{SUBM} 0001326801:名稱窗口 "
                "Facebook Inc 2005-05-06~2021-10-27,今名 Meta Platforms, Inc.、代號 META。"
                "本倉成分歷史:FB 於 2022-06-09 剔除,同日 META 加入——同一實體改名換代號"
            ),
        }
    ],
    ("HOT", "2000-11-17", "2016-09-23"): [
        {
            "cik": "0000316206",
            "display_name": "Starwood Hotels & Resorts Worldwide, Inc.",
            "evidence": (
                f"{WIKI}:2016-09-22 剔除,代號 HOT、公司名 Starwood Hotels and Resorts"
                "(Marriott 收購)。"
                f"{LOOKUP}:STARWOOD HOTELS & RESORTS WORLDWIDE, LLC → 0000316206。"
                f"{SUBM} 0000316206:名稱窗口 STARWOOD HOTEL & RESORTS WORLDWIDE INC "
                "1998-04-10~2011-12-12 與 2012-01-04~2016-09-23——**窗口訖日與成分期訖日同日**;"
                "申報 1994-05-17 起,整段覆蓋成分期。配對的 REIT 0000048595"
                "(STARWOOD HOTELS & RESORTS)申報止於 2013-03-21,蓋不住成分期,排除"
            ),
        }
    ],
    ("INFO", "2017-06-02", "2022-03-02"): [
        {
            "cik": "0001598014",
            "display_name": "IHS Markit Ltd.",
            "evidence": (
                f"{WIKI}:2017-06-02 加入、2022-03-02 剔除,兩次都寫代號 INFO、公司名 IHS Markit。"
                f"{LOOKUP}:IHS MARKIT LTD. → 0001598014。{SUBM} 0001598014:名稱窗口 "
                "Markit Ltd. 2014-01-27~2016-07-11、其後 IHS Markit Ltd.;"
                "申報 2014-01-27~2022-03-11,整段覆蓋成分期"
            ),
        }
    ],
    ("LB", "1996-01-02", "2021-08-03"): [
        {
            "cik": "0000701985",
            "display_name": "L Brands, Inc. (前稱 The Limited)",
            "evidence": (
                f"{LOOKUP}:LIMITED INC / LIMITED BRANDS INC / L BRANDS, INC. 三個名同錨 0000701985。"
                f"{SUBM} 0000701985:名稱窗口 LIMITED INC 1994-06-13~2002-06-12、"
                "LIMITED BRANDS INC 2002-06-17~2013-03-22、L Brands, Inc. 2013-04-02~2021-07-30,"
                "今名 Bath & Body Works, Inc.、代號 BBWI;申報 1994-03-11 起,整段覆蓋成分期。"
                "本倉成分歷史:LB 於 2021-08-03 剔除,同日 BBWI 加入——同一實體改名換代號。"
                "原錨 0001995807(LandBridge Co LLC)申報 2023-10-11 才起,當時並不存在"
            ),
        }
    ],
    ("NFX", "2010-12-20", "2019-02-15"): [
        {
            "cik": "0000912750",
            "display_name": "Newfield Exploration Co.",
            "evidence": (
                f"{WIKI}:2010-12-17 加入、2019-02-15 剔除,兩次都寫代號 NFX、"
                "公司名 Newfield Exploration。"
                f"{LOOKUP}:NEWFIELD EXPLORATION CO /DE/ → 0000912750。{SUBM} 0000912750:"
                "申報 1995-02-10~2019-02-25,整段覆蓋成分期,被 Encana 收購後即停止申報"
            ),
        }
    ],
    ("PCG", "1996-01-02", "2019-01-18"): [
        {
            "cik": "0001004980",
            "display_name": "PG&E Corp.",
            "evidence": (
                f"{WIKI}:2019-01-18 剔除,代號 PCG、公司名 Pacific Gas & Electric Company。"
                f"{LOOKUP}:PG&E CORP → 0001004980。{SUBM} 0001004980:申報 1996-02-21 起,"
                "今日代號欄仍是 PCG,一路至 2026;原錨確認正確。"
                "成分期起點 1996-01-02 是成分歷史來源的第一日:控股公司 PG&E Corp 成立之前,"
                "上市體是公用事業本身 0000075488(PACIFIC GAS & ELECTRIC Co);"
                "那一截(1997 年之前)在快照窗口(2015-01-02 起)之外,故此本段不拆"
            ),
        }
    ],
    ("PCL", "2002-01-17", "2016-02-22"): [
        {
            "cik": "0000849213",
            "display_name": "Plum Creek Timber Co., Inc.",
            "evidence": (
                f"{WIKI}:2016-02-22 剔除,代號 PCL、公司名 Plum Creek Timber"
                "(與 Weyerhaeuser 合併)。"
                f"{LOOKUP}:PLUM CREEK TIMBER CO INC → 0000849213。{SUBM} 0000849213:"
                "名稱窗口 PLUM CREEK TIMBER CO L P 1994-08-15~1999-04-12、"
                "其後 PLUM CREEK TIMBER CO INC;申報 1994-03-14~2016-03-04,整段覆蓋成分期"
            ),
        }
    ],
    ("POM", "2007-11-09", "2016-03-24"): [
        {
            "cik": "0001135971",
            "display_name": "Pepco Holdings, Inc.",
            "evidence": (
                f"{WIKI}:2016-03-30 剔除,代號 POM、公司名 Pepco Holdings(Exelon 收購)。"
                f"{LOOKUP}:PEPCO HOLDINGS INC → 0001135971。{SUBM} 0001135971:名稱窗口 "
                "NEW RC INC 2001-07-20~2002-01-09、PEPCO HOLDINGS INC 2002-03-27~2016-03-24"
                "——**窗口訖日與成分期訖日同日**;申報 2001-03-14 起,整段覆蓋成分期。"
                "原錨 0001877971(POMDOCTOR Ltd)申報 2021-09-30 才起,當時並不存在"
            ),
        }
    ],
    ("SBNY", "2021-12-20", "2023-03-15"): [
        {
            "cik": "0001288784",
            "display_name": "Signature Bank",
            "evidence": (
                f"{WIKI}:2021-12-20 加入、2023-03-15 剔除,兩次都寫代號 SBNY、"
                "公司名 Signature Bank,剔除理由「FDIC 接管」。"
                f"{LOOKUP}:SIGNATURE BANK CORP → 0001288784。{SUBM} 0001288784:"
                "申報 2004-04-26~2025-02-24,整段覆蓋成分期"
            ),
        }
    ],
    ("SCG", "2009-01-02", "2019-01-02"): [
        {
            "cik": "0000754737",
            "display_name": "SCANA Corp.",
            "evidence": (
                f"{WIKI}:2019-01-02 剔除,代號 SCG、公司名 SCANA(Dominion Energy 收購)。"
                f"{LOOKUP}:SCANA CORP → 0000754737。{SUBM} 0000754737:"
                "申報 1994-01-13~2019-03-01,整段覆蓋成分期"
            ),
        }
    ],
    ("SE", "2007-01-03", "2017-02-27"): [
        {
            "cik": "0001373835",
            "display_name": "Spectra Energy Corp.",
            "evidence": (
                f"{WIKI}:2017-02-28 剔除,代號 SE、公司名 Spectra Energy(與 Enbridge 合併)。"
                f"{LOOKUP}:SPECTRA ENERGY CORP. → 0001373835。{SUBM} 0001373835:名稱窗口 "
                "Gas SpinCo, Inc. 2006-09-07~2006-10-23、其後 Spectra Energy Corp.;"
                "申報 2006-09-07~2018-02-14,整段覆蓋成分期。"
                "今日持有 SE 代號的 0001703399(Sea Limited)申報 2017-04-24 才起——"
                "082 的第三關(原主要先放低該名稱)當時把它擋走,判詞正確,現補回真身"
            ),
        }
    ],
    ("SPLS", "1998-10-07", "2017-09-13"): [
        {
            "cik": "0000791519",
            "display_name": "Staples, Inc.",
            "evidence": (
                f"{WIKI}:2017-09-18 剔除,代號 SPLS、公司名 Staples(Sycamore Partners 私有化)。"
                f"{LOOKUP}:STAPLES INC → 0000791519。{SUBM} 0000791519:"
                "申報 1994-10-07~2021-11-08,整段覆蓋成分期"
            ),
        }
    ],
    ("STI", "1996-01-02", "2019-12-09"): [
        {
            "cik": "0000750556",
            "display_name": "SunTrust Banks, Inc.",
            "evidence": (
                f"{WIKI}:2019-12-09 剔除,代號 STI、公司名 SunTrust Banks,"
                "理由「BB&T 收購 SunTrust 組成 Truist Financial」。"
                f"{LOOKUP}:SUNTRUST BANKS INC → 0000750556。{SUBM} 0000750556:"
                "申報 1995-02-06~2019-12-19,整段覆蓋成分期,合併完成後即停止申報。"
                "原錨 0001881551(Solidion Technology)申報 2021-09-27 才起,當時並不存在"
            ),
        }
    ],
    ("TE", "2001-10-10", "2016-07-01"): [
        {
            "cik": "0000350563",
            "display_name": "TECO Energy, Inc.",
            "evidence": (
                f"{WIKI}:2016-07-01 剔除,代號 TE、公司名 TECO Energy(Emera 收購)。"
                f"{LOOKUP}:TECO ENERGY INC → 0000350563。{SUBM} 0000350563:"
                "申報 1994-01-28~2016-12-16,整段覆蓋成分期。"
                "原錨 0001992243(FREYR Battery / T1 Energy)申報 2023-09-08 才起,當時並不存在"
            ),
        }
    ],
    ("TWX", "1996-01-02", "2018-06-15"): [
        {
            "valid_from": "1996-01-02",
            "valid_to": "1996-10-11",
            "cik": "0000736157",
            "display_name": "Time Warner Inc. (1990-1996)",
            "evidence": (
                f"{LOOKUP}:TIME WARNER INC → 0000736157。{SUBM} 0000736157"
                "(今名 TIME WARNER COMPANIES INC):名稱窗口 TIME WARNER INC 1994-04-13~1996-10-11。"
                "拆點 1996-10-11 就是這個名稱窗口的訖日——同月另一個 CIK 接上同一個名(見下一列)。"
                "本段在快照窗口之外"
            ),
        },
        {
            "valid_from": "1996-10-11",
            "valid_to": "2002-02-11",
            "cik": "0001021387",
            "display_name": "Time Warner Inc. (1996-2002)",
            "evidence": (
                f"{LOOKUP}:TIME WARNER INC/ → 0001021387。{SUBM} 0001021387"
                "(今名 HISTORIC TW INC):名稱窗口 TW INC 1996-10-15~1996-10-11、"
                "TIME WARNER INC/ 1996-10-22~2002-02-11。拆點取自名稱窗口兩端。"
                "註:2001-01 AOL 與 Time Warner 合併之後,上市母體已轉為 0001105705,"
                "本列的訖日按名稱窗口寫,比上市母體易手略遲;兩段都在快照窗口之外,不影響快照"
            ),
        },
        {
            "valid_from": "2002-02-11",
            "valid_to": "2018-06-15",
            "cik": "0001105705",
            "display_name": "Time Warner Inc.",
            "evidence": (
                f"{WIKI}:2018-06-20 剔除,代號 TWX、公司名 Time Warner(AT&T 收購)。"
                f"{LOOKUP}:TIME WARNER INC. → 0001105705。{SUBM} 0001105705"
                "(今名 WARNER MEDIA, LLC):名稱窗口 AOL TIME WARNER INC 2000-04-25~2003-10-14、"
                "TIME WARNER INC 2003-10-01~2007-11-09、TIME WARNER INC. 2007-12-11~2018-06-11、"
                "TIME WARNER LLC 2018-06-15~2018-06-18;申報 2000-02-11~2020-10-23。"
                "快照窗口(2015-01-02 起)之內的 TWX 全屬本列"
            ),
        },
    ],
}


def main() -> int:
    anchors = list(read_anchor_table(ANCHOR_TABLE))
    open_rows = {
        (a.ticker, a.valid_from, a.valid_to)
        for a in anchors
        if a.verdict in (VERDICT_MANUAL, VERDICT_PLACEHOLDER)
    }
    missing = sorted(set(RESOLUTIONS) - open_rows)
    if missing:
        raise SystemExit(f"對照表上找不到這幾段待辨成分期,先核對:{missing}")
    unresolved = sorted(open_rows - set(RESOLUTIONS))
    print(f"對照表 {len(anchors)} 列;待辨成分期 {len(open_rows)} 段,本檔辨明 {len(RESOLUTIONS)} 段")
    if unresolved:
        print(f"仍未辨明 {len(unresolved)} 段:{unresolved}")

    rebuilt: list[TickerAnchor] = []
    resolved_rows: list[dict[str, str]] = []
    changed_rows: list[dict[str, str]] = []
    for anchor in anchors:
        key = (anchor.ticker, anchor.valid_from, anchor.valid_to)
        if key not in RESOLUTIONS:
            rebuilt.append(anchor)
            continue
        was = anchor.cik or "(佔位錨)"
        for spec in RESOLUTIONS[key]:
            row = TickerAnchor(
                ticker=anchor.ticker,
                cik=spec["cik"],
                valid_from=spec.get("valid_from", anchor.valid_from),
                valid_to=spec.get("valid_to", anchor.valid_to),
                display_name=spec["display_name"],
                verdict=VERDICT_IDENTIFIED,
                evidence=spec["evidence"],
            )
            rebuilt.append(row)
            resolved_rows.append(
                {
                    "ticker": anchor.ticker,
                    "membership": f"{anchor.valid_from}~{anchor.valid_to or '仍在名單上'}",
                    "anchor_from": row.valid_from,
                    "anchor_to": row.valid_to,
                    "was_anchor": was,
                    "now_anchor": row.cik,
                    "company": row.display_name,
                    "verdict": row.verdict,
                    "evidence": row.evidence,
                }
            )
            if row.cik != anchor.cik:
                changed_rows.append(
                    {
                        "ticker": anchor.ticker,
                        "membership": f"{row.valid_from}~{row.valid_to or '仍在名單上'}",
                        "from_anchor": was,
                        "to_anchor": row.cik,
                        "verdict": row.verdict,
                        "evidence": row.evidence,
                    }
                )

    write_anchor_table(ANCHOR_TABLE, rebuilt)
    print(f"對照表補成 {len(rebuilt)} 列 → {ANCHOR_TABLE}")

    with RESOLVED_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "ticker",
                "membership",
                "anchor_from",
                "anchor_to",
                "was_anchor",
                "now_anchor",
                "company",
                "verdict",
                "evidence",
            ],
        )
        writer.writeheader()
        writer.writerows(resolved_rows)
    print(f"辨明結果 {len(resolved_rows)} 列 → {RESOLVED_FILE}")

    with CHANGED_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["ticker", "membership", "from_anchor", "to_anchor", "verdict", "evidence"],
        )
        writer.writeheader()
        writer.writerows(changed_rows)
    print(f"錨改變 {len(changed_rows)} 列 → {CHANGED_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
