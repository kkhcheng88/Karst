# -*- coding: utf-8 -*-
"""KARST-231 附件:stock_news 表覆蓋核查。

只計數、不存文本、不列公司名或代號。只讀 T1 當日或之前的新聞日期(不看 T1 之後)。
輸出:A3/transcripts/news_coverage.json 與逐事件 count 併入 coverage.csv 的 n_news_30d 欄。
"""
import csv
import datetime as dt
import json
import os
import re
import time

import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
A3 = os.path.dirname(HERE)
URL = ("https://huggingface.co/datasets/defeatbeta/yahoo-finance-data/"
       "resolve/main/data/stock_news.parquet")
OUT = os.path.join(HERE, "news_coverage.json")


def load_events():
    ev = []
    pkdir = os.path.join(A3, "packets")
    for fn in sorted(os.listdir(pkdir)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(pkdir, fn), encoding="utf-8") as fh:
            p = json.load(fh)
        ev.append(dict(event_id=p["event_id"], cohort="main", ticker=p["ticker"],
                       t1=re.search(r"(\d{4}-\d{2}-\d{2})", p["1_事件識別"]["T1_分析截止"]).group(1)))
    txt = open(os.path.join(A3, "picks_before_results.md"), encoding="utf-8").read()
    bak = re.findall(r"^\s*\d+\.\s*(\S+?)\((B\d{3}),(\d{4}),", txt, re.M)
    ep = {}
    with open(os.path.join(A3, "entry_pool.csv"), encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            ep[r["accessionNumber"]] = r
    for acc, eid, _yr in bak:
        r = ep[acc]
        ev.append(dict(event_id=eid, cohort="backup", ticker=r["ticker"],
                       t1=str(r["reaction_date"])[:10]))
    return ev


def main():
    c = duckdb.connect()
    c.execute("SET enable_progress_bar=false")
    res = {}

    t = time.time()
    fm = c.execute(f"SELECT num_rows, num_row_groups FROM parquet_file_metadata('{URL}')").fetchdf()
    res["total_rows"] = int(fm.num_rows[0])
    res["num_row_groups"] = int(fm.num_row_groups[0])
    md = c.execute(
        f"SELECT stats_min_value mn, stats_max_value mx FROM parquet_metadata('{URL}') "
        "WHERE path_in_schema='report_date'").fetchdf()
    res["min_report_date"] = str(md.mn.min())
    res["max_report_date"] = str(md.mx.max())
    res["footer_secs"] = round(time.time() - t, 1)
    print("footer:", res, flush=True)

    # 全表非空比例(掃 link 與 report_date 兩欄)
    t = time.time()
    try:
        q = c.execute(
            f"SELECT count(*) n, "
            f"count(link) n_link, count(report_date) n_date, "
            f"sum(CASE WHEN link IS NOT NULL AND trim(link) <> '' THEN 1 ELSE 0 END) n_link_ne, "
            f"sum(CASE WHEN report_date IS NOT NULL AND trim(report_date) <> '' THEN 1 ELSE 0 END) n_date_ne "
            f"FROM '{URL}'").fetchdf()
        res["n_rows_scanned"] = int(q.n[0])
        res["prop_has_link"] = round(int(q.n_link[0]) / max(int(q.n[0]), 1), 4)
        res["prop_has_link_nonempty"] = round(int(q.n_link_ne[0]) / max(int(q.n[0]), 1), 4)
        res["prop_has_report_date"] = round(int(q.n_date[0]) / max(int(q.n[0]), 1), 4)
        res["prop_has_report_date_nonempty"] = round(int(q.n_date_ne[0]) / max(int(q.n[0]), 1), 4)
    except Exception as ex:
        res["scan_error"] = f"{type(ex).__name__}: {str(ex)[:200]}"
    res["scan_secs"] = round(time.time() - t, 1)
    print("scan:", {k: v for k, v in res.items() if k.startswith("prop")}, res["scan_secs"], flush=True)

    # 逐事件:窗口 (T1-30d, T1] 內的新聞宗數
    ev = load_events()
    counts = {}
    t = time.time()
    for i, e in enumerate(ev, 1):
        hi = dt.date.fromisoformat(e["t1"])
        lo = hi - dt.timedelta(days=30)
        try:
            r = c.execute(
                f"SELECT count(*) n FROM '{URL}' WHERE symbol = ? "
                "AND report_date >= ? AND report_date <= ?",
                [e["ticker"], str(lo), str(hi)]).fetchdf()
            counts[e["event_id"]] = int(r.n[0])
        except Exception as ex:
            counts[e["event_id"]] = -1
            print("err", e["event_id"], type(ex).__name__, flush=True)
        if i % 20 == 0:
            print(f"  news {i}/{len(ev)} ({round(time.time()-t,1)}s)", flush=True)
    res["news_query_secs"] = round(time.time() - t, 1)
    res["n_events"] = len(ev)
    res["n_events_with_news_30d"] = sum(1 for v in counts.values() if v > 0)
    res["n_events_zero_news_30d"] = sum(1 for v in counts.values() if v == 0)
    res["events_before_coverage_floor"] = sum(
        1 for e in ev if e["t1"] < res["min_report_date"])
    res["events_on_or_after_coverage_floor"] = len(ev) - res["events_before_coverage_floor"]
    cw = [counts[e["event_id"]] for e in ev if e["t1"] >= res["min_report_date"]]
    res["n_events_with_news_30d_within_coverage"] = sum(1 for v in cw if v > 0)
    res["n_events_in_coverage_window"] = len(cw)
    res["max_news_30d"] = max(counts.values())
    res["median_news_30d_nonzero"] = (
        sorted(v for v in counts.values() if v > 0)[len([v for v in counts.values() if v > 0]) // 2]
        if res["n_events_with_news_30d"] else 0)

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)

    # 併入 coverage.csv
    cp = os.path.join(HERE, "coverage.csv")
    with open(cp, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    FIELDS = list(rows[0].keys())
    if "n_news_30d" not in FIELDS:
        FIELDS.append("n_news_30d")
    for r in rows:
        r["n_news_30d"] = counts.get(r["event_id"], "")
    with open(cp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("news result:", json.dumps({k: v for k, v in res.items()
                                      if not k.startswith("prop")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
