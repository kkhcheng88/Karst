# -*- coding: utf-8 -*-
"""KARST-226 票 A″(執行口徑 v1.2)第十二步:抽三列人手覆核(收貨條件之一)。

做法**不重用 s2/s3/s6 的推導碼**,直接用原件重算一遍(種子 20260912 由 `entry_pool.csv` 抽三列):
  - **T0(v1.2 第 2 項)**:min(8-K 受理時間, EX-99.1 稿頭日期)。稿頭日期從 EX-99.1 原文
    第一段的日期重抓;稿頭日早於申報日 → 視作稿頭日收市後公開,反應日 = 稿頭日次一交易日;
    否則用受理時間美東鐘點(≤16:00 同一日,遲於 16:00 順延)。
  - `release_timing`:由 T0 美東鐘點分盤前 / 盤中 / 盤後;沿用稿頭日者記「稿頭日(收市後)」。
  - 反應報酬:反應日 adj_close ÷ 反應日前最後一個交易日 adj_close − 1,再減 SPY 同日報酬;
    另算反應日前一交易日絕對報酬(> 8% 者應標疑更早公開)。
  - g0 兩條:**XBRL 版**由 companyfacts 原件重算;**稿內版**由人口檔的稿內收入除以前一年
    同季 XBRL 值重算。
  - 訊號季收入是否真的在稿內:另寫一份數字匹配(千/百萬/十億、逗號、容差 0.5%)。
  - 60 日成交額(算術平均與中位)由日線原件另寫一份。

輸出 `cache/verify3.json` 與 `cache/verify3.md`。
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import random
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import pxlib

ROOT = Path(r"C:\projects\Karst")
CF = ROOT / "data" / "sec" / "companyfacts"
SUB = ROOT / "data" / "sec" / "submissions"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE.parent / "A" / "edgar_cache"
ET = ZoneInfo("America/New_York")
TAGS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
        "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueGoodsNet", "RegulatedAndUnregulatedOperatingRevenue"]
MONTH_NUM = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
             "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
             "december": 12, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
             "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
DATE_RX = re.compile(r"\b(" + "|".join(sorted(MONTH_NUM, key=len, reverse=True))
                     + r")\.?\s+(\d{1,2}),?\s+(\d{4})\b", re.I)
PRE_930 = (9, 30)
AT_1600 = (16, 0)


def spy_calendar() -> list[str]:
    s = pd.read_csv(ROOT / "data" / "prices" / "spy_daily.csv", parse_dates=["date"])
    return sorted(s["date"].dt.strftime("%Y-%m-%d").tolist())


def dateline_of(text: str, filing_date: str) -> str:
    """EX-99.1 稿頭日期(另寫一份):首 2,500 字內、與申報日相距 0–45 日的**第一個**日期。

    與 `s2b_dateline.parse_dateline` 同一條口徑,但獨立實作(含簡寫月份與「Feb. 12, 2018」
    這類寫法),用來覆核交付檔的 `dateline` 欄。
    """
    try:
        fd = dt.date.fromisoformat(filing_date)
    except ValueError:
        return ""
    for m in DATE_RX.finditer(text[:2500]):
        try:
            d = dt.date(int(m.group(3)), MONTH_NUM[m.group(1).lower()], int(m.group(2)))
        except (ValueError, KeyError):
            continue
        if 0 <= (fd - d).days <= 45:
            return d.isoformat()
    return ""


def single_quarter(cik10: str) -> dict[str, float]:
    p = CF / ("CIK%s.json.gz" % cik10)
    if not p.exists():
        return {}
    with gzip.open(p, "rt", encoding="utf-8") as f:
        d = json.load(f)
    out: dict[str, float] = {}
    for t in TAGS:
        node = d.get("facts", {}).get("us-gaap", {}).get(t)
        if not node:
            continue
        best: dict[tuple, tuple] = {}
        for unit, rows in node.get("units", {}).items():
            if unit != "USD":
                continue
            for r in rows:
                st, en, v, fd = r.get("start"), r.get("end"), r.get("val"), r.get("filed", "")
                if not st or not en or v is None:
                    continue
                days = (dt.date.fromisoformat(en) - dt.date.fromisoformat(st)).days
                if not (80 <= days <= 100):
                    continue
                k = (st, en)
                if k not in best or fd < best[k][1]:
                    best[k] = (float(v), fd)
        for (_st, en), (v, _fd) in best.items():
            out.setdefault(en, v)
    return out


def num_in_text(text: str, value: float) -> tuple[bool, str]:
    """另寫一份數字匹配:值 × {1, 千, 百萬, 十億} 是否在稿內出現(容差 0.5%)。"""
    if not value:
        return False, ""
    for unit, mult in (("", 1.0), ("thousand", 1e3), ("million", 1e6), ("billion", 1e9),
                       ("k", 1e3), ("m", 1e6), ("bn", 1e9)):
        v = value / mult
        for pat in (r"\$\s*%s\b" % re.escape("%.2f" % v),
                    r"\$\s*%s\b" % re.escape("%.1f" % v),
                    r"\$\s*%s\b" % re.escape("{:,.0f}".format(v)),
                    r"\$\s*%s\b" % re.escape("%.0f" % v)):
            m = re.search(pat, text)
            if m:
                return True, m.group(0)[:24]
    # 逗號與小數的通用比對:抽所有金額,換算後比
    for m in re.finditer(r"\$\s*([\d,]+(?:\.\d+)?)\s*(thousand|million|billion|bn|mn|[kmb])?\b",
                         text, re.I):
        try:
            raw = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        u = (m.group(2) or "").lower()
        sc = {"thousand": 1e3, "k": 1e3, "million": 1e6, "m": 1e6, "mn": 1e6,
              "billion": 1e9, "b": 1e9, "bn": 1e9}.get(u, 1.0)
        if abs(raw * sc - value) <= 0.005 * value:
            return True, m.group(0)[:24]
    return False, ""


def turnover_indep(cik10: str, react: str) -> tuple | None:
    for p in pxlib.parts():
        d = pd.read_parquet(p, columns=["entity_id", "date", "adj_close", "close",
                                        "volume", "series_role"])
        d = d[d["entity_id"] == cik10]
        if not len(d):
            continue
        d = d[(d["series_role"] == "primary")]
        d["date"] = pd.to_datetime(d["date"])
        d = d[d["date"] >= pd.Timestamp("2013-06-01")].dropna(subset=["adj_close"])
        d = d.sort_values("date")
        gd = d["date"].dt.strftime("%Y-%m-%d").tolist()
        if react not in gd:
            return None
        i = gd.index(react)
        if i < 60:
            return None
        w = (d["close"] * d["volume"]).to_numpy(dtype="float64")[i - 60:i]
        return float(np.mean(w)), float(np.median(w)), len(w)
    return None


def main() -> None:
    rng = random.Random(20260912)
    ep = pd.read_csv(HERE / "entry_pool.csv", encoding="utf-8-sig")
    idx = sorted(rng.sample(range(len(ep)), 3))
    cal = spy_calendar()
    calset = set(cal)
    spy = pd.read_csv(ROOT / "data" / "prices" / "spy_daily.csv", parse_dates=["date"])
    spy["d"] = spy["date"].dt.strftime("%Y-%m-%d")
    spy["r"] = spy["adj_close"].pct_change()
    spy_ret = dict(zip(spy["d"], spy["r"]))
    spy_adj = dict(zip(spy["d"], spy["adj_close"]))
    spy_prev = {cal[i]: cal[i - 1] for i in range(1, len(cal))}

    pxmap: dict[str, tuple] = {}
    rep = []
    for i in idx:
        r = ep.iloc[i]
        cik10 = str(r["cik"]).zfill(10)
        acc = r["accessionNumber"]
        raw = json.loads((SUB / ("CIK%s.json" % cik10)).read_text(encoding="utf-8"))
        rec = raw["filings"]["recent"]
        j = rec["accessionNumber"].index(acc)
        acc_dt = rec["acceptanceDateTime"][j]
        t = dt.datetime.fromisoformat(acc_dt.replace("Z", "+00:00")).astimezone(ET)
        acc_day = t.strftime("%Y-%m-%d")
        # --- 稿頭日期(v1.2)
        exp = DOCS / ("%s__EX991.txt.gz" % acc.replace("-", ""))
        txt = gzip.open(exp, "rt", encoding="utf-8").read() if exp.exists() else ""
        dl = dateline_of(txt, r["filingDate"])
        # --- 價格原件(另讀一份,供開市跳空判)
        if cik10 not in pxmap:
            arr = pxlib.price_arrays({cik10}).get(cik10)
            pxmap[cik10] = ([], None, None, None) if arr is None else (
                [str(x) for x in arr[0]], arr[1], arr[2], arr[3])
        gd, adj, cl, op = pxmap[cik10]
        tm = (t.hour, t.minute)
        react8 = next((d for d in cal if d > acc_day), "NaT")
        same_day = acc_day in calset
        if dl and dl < acc_day:
            t0_day, rule = dl, "稿頭日 %s 早於申報日 → 視作稿頭日收市後公開" % dl
            timing = "prior_day_after_close"
            react = next((d for d in cal if d > dl), "NaT")
        elif dl and dl == acc_day:
            t0_day, rule = dl, "稿頭日 %s 與申報日同日 → 用受理時間美東 %s 判時段" % (
                dl, t.strftime("%H:%M:%S"))
            if tm < PRE_930:
                timing, react = "pre_market", (acc_day if same_day else react8)
            elif tm >= AT_1600:
                timing, react = "after_close", react8
            else:
                # 開市跳空判:未還原開市價對上一交易日未還原收市價
                gap = dayret = None
                if acc_day in gd:
                    jd = gd.index(acc_day)
                    if jd >= 1 and cl is not None and cl[jd - 1] > 0:
                        gap = op[jd] / cl[jd - 1] - 1.0
                        dayret = cl[jd] / cl[jd - 1] - 1.0
                if (gap is not None and dayret not in (None, 0.0)
                        and abs(gap) >= 0.5 * abs(dayret) and (gap > 0) == (dayret > 0)):
                    timing, react = "pre_market_inferred", acc_day
                else:
                    timing, react = "intraday", acc_day
        else:
            t0_day = acc_day
            if tm < PRE_930:
                timing, react = "pre_market_8k", (acc_day if same_day else react8)
            elif tm >= AT_1600:
                timing, react = "after_close_8k", react8
            else:
                timing, react = "undetermined", react8
            rule = "無稿頭日期 → 用 8-K 受理時間美東 %s" % t.strftime("%H:%M:%S")
        k = gd.index(react) if react in gd else None
        ret = np.nan
        prev = ""
        if k is not None and k > 0:
            prev = gd[k - 1]
            ret = adj[k] / adj[k - 1] - 1
        prior_abs = (abs(adj[k - 1] / adj[k - 2] - 1)
                     if k is not None and k > 1 else None)
        # --- g0(XBRL 版與稿內版)
        q = single_quarter(cik10)
        ends = sorted(q)
        sig_end = r["signal_q_end"]
        g0x = None
        yago_end, yago = None, None
        if sig_end in q:
            e = dt.date.fromisoformat(sig_end)
            base = [x for x in ends if 340 <= (e - dt.date.fromisoformat(x)).days <= 390]
            if base:
                b = min(base, key=lambda x: abs((e - dt.date.fromisoformat(x)).days - 365))
                yago_end, yago = b, q[b]
                g0x = q[sig_end] / q[b] - 1 if q[b] else None
        rev_text = None if pd.isna(r["rev_signal_text"]) else float(r["rev_signal_text"])
        g0t = (rev_text / yago - 1) if (rev_text and yago) else None
        found, hit = num_in_text(txt, rev_text) if rev_text else (False, "")
        tv = turnover_indep(cik10, react)
        rep.append(dict(
            accessionNumber=acc, cik=cik10, ticker=r["ticker"], sic2=str(r["sic2"]),
            acceptanceDateTime=acc_dt, acceptance_day_et=acc_day,
            dateline_recomputed=dl, dateline_csv=r["dateline"],
            t0_day_recomputed=t0_day, t0_rule=rule, release_timing_recomputed=timing,
            release_timing_csv=r["release_timing"], t0_source_csv=r["t0_source"],
            t0_source_recomputed=("稿頭" if (dl and dl <= acc_day) else "8-K"),
            reaction_date_recomputed=react, reaction_date_csv=r["reaction_date"],
            t1_close_csv=float(r["t1_close_adj"]),
            t1_close_recomputed=(None if k is None else round(float(adj[k]), 6)),
            prev_date_recomputed=prev,
            ret_recomputed=(None if np.isnan(ret) else round(float(ret), 6)),
            ret_csv=float(r["ret_reaction"]),
            spy_ret_recomputed=round(float(spy_ret.get(react, float("nan"))), 6),
            rel_spy_csv=float(r["rel_spy"]),
            prior_day_abs_ret_recomputed=(None if prior_abs is None else round(float(prior_abs), 6)),
            prior_day_abs_ret_csv=float(r["prior_day_abs_ret"]),
            signal_q_end=sig_end, yago_q_end=yago_end,
            rev_signal_xbrl_csv=(None if pd.isna(r["rev_signal_xbrl"])
                                 else float(r["rev_signal_xbrl"])),
            rev_signal_text_csv=rev_text, rev_text_hit_in_ex991=bool(found),
            rev_text_hit_token=hit,
            g0_xbrl_recomputed=(None if g0x is None else round(g0x, 6)),
            g0_xbrl_csv=(None if pd.isna(r["rev_g0"]) else round(float(r["rev_g0"]), 6)),
            g0_text_recomputed=(None if g0t is None else round(g0t, 6)),
            g0_text_csv=(None if pd.isna(r["rev_g0_text"]) else round(float(r["rev_g0_text"]), 6)),
            turnover_mean_recomputed=None if tv is None else round(tv[0], 2),
            turnover_median_recomputed=None if tv is None else round(tv[1], 2),
            turnover_window_n=None if tv is None else tv[2],
            turnover_mean_csv=(None if pd.isna(r["turnover_mean_60d"])
                               else round(float(r["turnover_mean_60d"]), 2)),
            turnover_median_csv=(None if pd.isna(r["turnover_median_60d"])
                                 else round(float(r["turnover_median_60d"]), 2)),
            rev_q_used=len(q)))
    (CACHE / "verify3.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    L = ["# 三列人手覆核(種子 20260912 由入口池抽;執行口徑 v1.2)", ""]
    same = lambda a, b: "相符" if a == b else "**不符**"    # noqa: E731
    for m in rep:
        L.append("## %s %s(%s)" % (m["accessionNumber"], m["ticker"], m["cik"]))
        L.append("")
        L.append("- 8-K 受理 `%s`(美東日 %s);EX-99.1 稿頭日期(重抓)`%s`(表 `%s`)"
                 % (m["acceptanceDateTime"], m["acceptance_day_et"],
                    m["dateline_recomputed"], m["dateline_csv"]))
        L.append("- T0 規則:%s;T0 日 `%s`;來源重推 `%s` 對表 `%s` → %s"
                 % (m["t0_rule"], m["t0_day_recomputed"], m["t0_source_recomputed"],
                    m["t0_source_csv"],
                    same(m["t0_source_recomputed"], m["t0_source_csv"])))
        L.append("- 公開時段:重推 `%s` 對表 `%s` → %s"
                 % (m["release_timing_recomputed"], m["release_timing_csv"],
                    same(m["release_timing_recomputed"], m["release_timing_csv"])))
        L.append("- 反應日:重推 `%s` 對表 `%s` → %s"
                 % (m["reaction_date_recomputed"], m["reaction_date_csv"],
                    same(m["reaction_date_recomputed"], m["reaction_date_csv"])))
        L.append("- T1 收市(還原):重推 %s 對表 %s"
                 % (m["t1_close_recomputed"], m["t1_close_csv"]))
        L.append("- 反應報酬:重推 %s(前一日 %s)對表 %s;同日 SPY %s;相對 SPY 表 %s"
                 % (m["ret_recomputed"], m["prev_date_recomputed"], m["ret_csv"],
                    m["spy_ret_recomputed"], m["rel_spy_csv"]))
        L.append("- 反應日前一交易日絕對報酬:重推 %s 對表 %s(> 0.08 應標疑更早公開)"
                 % (m["prior_day_abs_ret_recomputed"], m["prior_day_abs_ret_csv"]))
        L.append("- 訊號季 `%s`(去年同季 `%s`):稿內收入 %s **在稿內找到=%s**(命中 `%s`);"
                 "XBRL 值 %s(該家可用單季事實 %d 個)"
                 % (m["signal_q_end"], m["yago_q_end"], m["rev_signal_text_csv"],
                    m["rev_text_hit_in_ex991"], m["rev_text_hit_token"],
                    m["rev_signal_xbrl_csv"], m["rev_q_used"]))
        L.append("- g0:XBRL 版重推 %s 對表 %s;稿內版重推 %s 對表 %s"
                 % (m["g0_xbrl_recomputed"], m["g0_xbrl_csv"],
                    m["g0_text_recomputed"], m["g0_text_csv"]))
        L.append("- 60 日成交額(反應日前 60 列):平均重推 %s 對表 %s;中位重推 %s 對表 %s"
                 "(%s 列)"
                 % (m["turnover_mean_recomputed"], m["turnover_mean_csv"],
                    m["turnover_median_recomputed"], m["turnover_median_csv"],
                    m["turnover_window_n"]))
        L.append("")
    (CACHE / "verify3.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    for m in rep:
        print("%s 反應日 %s(表 %s)%s;時段 %s(%s);稿內收入命中 %s;g0 稿內 %s / 表 %s"
              % (m["accessionNumber"], m["reaction_date_recomputed"],
                 m["reaction_date_csv"],
                 same(m["reaction_date_recomputed"], m["reaction_date_csv"]),
                 m["release_timing_recomputed"], m["release_timing_csv"],
                 m["rev_text_hit_in_ex991"], m["g0_text_recomputed"], m["g0_text_csv"]))
    print("→", CACHE / "verify3.md")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
