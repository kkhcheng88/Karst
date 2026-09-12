# -*- coding: utf-8 -*-
"""KARST-222 票 A:抽三列人手覆核(收貨條件之一)。

做法**不重用 s2/s3 的推導碼**,直接用原件重算一遍:
  - T0 → 反應日:由該宗 8-K 的 acceptanceDateTime 換美東時間,同一個美東日若是交易日
    且不遲於 16:00 就當日,否則順延到 SPY 日曆上的下一個交易日。
  - 反應報酬:反應日 adj_close ÷ 反應日前最後一個交易日 adj_close − 1,再減 SPY 同日報酬。
  - g0 與前一季按年:直接讀 `data/sec/companyfacts/CIK*.json.gz`,揀 80–100 日的
    revenue 事實,同一 (start,end) 取 filed 最早者,再找 340–390 天前的同季做基期。

三列以固定種子 20260912 由 **入口池** 抽出(不是人手挑)。輸出 cache/verify3.json
與 cache/verify3.md。

KARST-225(v1.1)另加一項:同一列由日線原件**另寫一份**推導,覆核
`turnover_mean_60d`(門檻所用,算術平均)與 `turnover_median_60d`。
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
PRICES = ROOT / "data" / "prices" / "daily"
CF = ROOT / "data" / "sec" / "companyfacts"
SUB = ROOT / "data" / "sec" / "submissions"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
ET = ZoneInfo("America/New_York")
TAGS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
        "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueGoodsNet", "RegulatedAndUnregulatedOperatingRevenue"]


def spy_calendar() -> list[str]:
    s = pd.read_csv(ROOT / "data" / "prices" / "spy_daily.csv", parse_dates=["date"])
    return sorted(s["date"].dt.strftime("%Y-%m-%d").tolist())


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


def turnover_indep(cik10: str, react: str) -> tuple | None:
    """另寫一份:由日線原件直接取反應日前 60 列的 close×volume 平均與中位。"""
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

    pxmap: dict[str, pd.DataFrame] = {}
    rep = []
    for i in idx:
        r = ep.iloc[i]
        cik10 = str(r["cik"]).zfill(10)
        # --- 由原件重推 T0 → 反應日
        acc = r["accessionNumber"]
        raw = json.loads((SUB / ("CIK%s.json" % cik10)).read_text(encoding="utf-8"))
        rec = raw["filings"]["recent"]
        j = rec["accessionNumber"].index(acc)
        acc_dt = rec["acceptanceDateTime"][j]
        t = dt.datetime.fromisoformat(acc_dt.replace("Z", "+00:00")).astimezone(ET)
        day = t.strftime("%Y-%m-%d")
        if day in calset and (t.hour, t.minute, t.second) <= (16, 0, 0):
            react = day
            rule = "T0 在美東 %s 且不遲於 16:00 → 同一日" % t.strftime("%H:%M:%S")
        else:
            react = next((d for d in cal if d > day), "NaT")
            rule = "T0 在美東 %s(%s)→ 順延至下一個交易日" % (
                t.strftime("%H:%M:%S"),
                "非交易日" if day not in calset else "遲於 16:00")
        # --- 由日線重推反應報酬
        if cik10 not in pxmap:                       # 只取原件的日線,不重用 s2 的推導
            arr = pxlib.price_arrays({cik10}).get(cik10)
            pxmap[cik10] = ([], None) if arr is None else ([str(x) for x in arr[0]], arr[1])
        gd, adj = pxmap[cik10]
        k = gd.index(react) if react in gd else None
        ret = None
        prev = ""
        if k is not None and k > 0:
            prev = gd[k - 1]
            ret = adj[k] / adj[k - 1] - 1
        # --- 由 companyfacts 重推 g0 與前一季
        q = single_quarter(cik10)
        ends = sorted(q)
        sig_end = r["signal_q_end"]
        g0 = None
        if sig_end in q:
            e = dt.date.fromisoformat(sig_end)
            base = [x for x in ends
                    if 340 <= (e - dt.date.fromisoformat(x)).days <= 390]
            if base:
                b = min(base, key=lambda x: abs((e - dt.date.fromisoformat(x)).days - 365))
                g0 = q[sig_end] / q[b] - 1 if q[b] else None
        tv = turnover_indep(cik10, react)
        rep.append(dict(
            turnover_mean_recomputed=None if tv is None else round(tv[0], 2),
            turnover_median_recomputed=None if tv is None else round(tv[1], 2),
            turnover_window_n=None if tv is None else tv[2],
            turnover_mean_csv=(None if pd.isna(r["turnover_mean_60d"])
                               else round(float(r["turnover_mean_60d"]), 2)),
            turnover_median_csv=(None if pd.isna(r["turnover_median_60d"])
                                 else round(float(r["turnover_median_60d"]), 2)),
            accessionNumber=acc, cik=cik10, ticker=r["ticker"], sic2=str(r["sic2"]),
            acceptanceDateTime=acc_dt, t0_et=t.strftime("%Y-%m-%dT%H:%M:%S"),
            rule=rule, reaction_date_recomputed=react, reaction_date_csv=r["reaction_date"],
            t1_close_csv=float(r["t1_close_adj"]), t1_close_recomputed=(
                None if k is None else round(float(adj[k]), 6)),
            prev_date_recomputed=prev, ret_recomputed=(None if ret is None else round(ret, 6)),
            ret_csv=float(r["ret_reaction"]),
            spy_ret_recomputed=round(float(spy_ret.get(react, float("nan"))), 6),
            rel_spy_csv=float(r["rel_spy"]),
            signal_q_end=sig_end, g0_recomputed=(None if g0 is None else round(g0, 6)),
            g0_csv=(None if pd.isna(r["rev_g0"]) else round(float(r["rev_g0"]), 6)),
            rev_q_used=len(q)))
    (CACHE / "verify3.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    L = ["# 三列人手覆核(種子 20260912 由入口池抽)", ""]
    for m in rep:
        L.append("## %s %s(%s)" % (m["accessionNumber"], m["ticker"], m["cik"]))
        L.append("")
        L.append("- T0 原文 `%s` → 美東 `%s`;規則:%s" % (m["acceptanceDateTime"], m["t0_et"], m["rule"]))
        L.append("- 反應日:重推 `%s` 對 population.csv `%s` → %s"
                 % (m["reaction_date_recomputed"], m["reaction_date_csv"],
                    "相符" if m["reaction_date_recomputed"] == m["reaction_date_csv"] else "**不符**"))
        L.append("- T1 收市(還原):重推 %s 對表 %s" % (m["t1_close_recomputed"], m["t1_close_csv"]))
        L.append("- 反應報酬:重推 %s(前一日 %s)對表 %s;同日 SPY 報酬 %s"
                 % (m["ret_recomputed"], m["prev_date_recomputed"], m["ret_csv"], m["spy_ret_recomputed"]))
        L.append("- 相對 SPY:%s(表 %s)" % (
            None if m["ret_recomputed"] is None else round(m["ret_recomputed"] - m["spy_ret_recomputed"], 6),
            m["rel_spy_csv"]))
        L.append("- 訊號季 `%s`:g0 重推 %s 對表 %s(該家可用單季事實 %d 個)"
                 % (m["signal_q_end"], m["g0_recomputed"], m["g0_csv"], m["rev_q_used"]))
        L.append("- 60 日成交額(反應日前 60 列):平均重推 %s 對表 %s;中位重推 %s 對表 %s"
                 "(%s 列)"
                 % (m["turnover_mean_recomputed"], m["turnover_mean_csv"],
                    m["turnover_median_recomputed"], m["turnover_median_csv"],
                    m["turnover_window_n"]))
        L.append("")
    (CACHE / "verify3.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    for m in rep:
        print("%s %s 反應日 %s(表 %s)%s;g0 重推 %s / 表 %s" % (
            m["ticker"], m["cik"], m["reaction_date_recomputed"], m["reaction_date_csv"],
            "相符" if m["reaction_date_recomputed"] == m["reaction_date_csv"] else "不符",
            m["g0_recomputed"], m["g0_csv"]))
    print("→", CACHE / "verify3.md")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
