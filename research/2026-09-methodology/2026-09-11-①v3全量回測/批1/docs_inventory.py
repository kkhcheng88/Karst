# -*- coding: utf-8 -*-
"""列出本批選定公司在衝擊起日前最後一份 10-K / 10-Q 的申報日、accession、本地全文有無。"""
import json
import os

ROOT = "C:/projects/Karst"
SUB = ROOT + "/data/sec/submissions/CIK{cik}.json"
TXT = ROOT + "/data/sec/10k_text"

# (事件, ticker, CIK, 衝擊起日)
PICKS = [
    ("E01", "T", "0000732717", "2013-05-21"),
    ("E01", "SPG", "0001063761", "2013-05-21"),
    ("E01", "NLY", "0001043219", "2013-05-21"),
    ("E01", "ED", "0001047862", "2013-05-21"),
    ("E02", "BIIB", "0000875045", "2015-09-18"),
    ("E02", "REGN", "0000872589", "2015-09-18"),
    ("E02", "GILD", "0000882095", "2015-09-18"),
    ("E02", "JNJ", "0000200406", "2015-09-18"),
    ("E03", "UNFI", "0001020859", "2017-06-15"),
    ("E03", "KR", "0000056873", "2017-06-15"),
    ("E03", "SFM", "0001575515", "2017-06-15"),
    ("E03", "GIS", "0000040704", "2017-06-15"),
    ("E04", "ZM", "0001585521", "2021-02-12"),
    ("E04", "PTON", "0001639825", "2021-02-12"),
    ("E04", "TDOC", "0001477449", "2021-02-12"),
    ("E04", "FSLY", "0001517413", "2021-02-12"),
    ("E09", "OXY", "0000797468", "2014-11-26"),
    ("E09", "RIG", "0001451505", "2014-11-26"),
    ("E09", "HAL", "0000045012", "2014-11-26"),
    ("E09", "CVX", "0000093410", "2014-11-26"),
]


def main():
    for eid, tk, cik, cutoff in PICKS:
        p = SUB.format(cik=cik)
        if not os.path.exists(p):
            print(f"{eid} {tk} 無 submissions 快取")
            continue
        d = json.load(open(p, encoding="utf-8"))
        r = d.get("filings", {}).get("recent", {})
        got = []
        for i in range(len(r.get("form", []))):
            if r["form"][i] in ("10-K", "10-Q") and r["filingDate"][i] < cutoff:
                acc = r["accessionNumber"][i]
                loc = os.path.exists(f"{TXT}/{tk}_{acc.replace('-', '')}.txt.gz")
                got.append((r["form"][i], r["filingDate"][i], r["reportDate"][i], acc, loc))
        got.sort(key=lambda x: x[1], reverse=True)
        print(f"== {eid} {tk} cutoff {cutoff}")
        for g in got[:4]:
            print("   ", g[0], "filed", g[1], "period", g[2], g[3], "LOCAL" if g[4] else "need-fetch")


if __name__ == "__main__":
    main()
