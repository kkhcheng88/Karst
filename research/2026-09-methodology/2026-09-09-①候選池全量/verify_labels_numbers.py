"""KARST-188 證據核實(補充):十一家「整句對不上」的改核數字。

verify_labels_sec.py 用整句探針核了六十家,49 家整句逐字命中。對不上的那些,
成因全部是章節標題、子隊自己加的省略號、括號內的子隊註解,或者指引本身是
表格摘錄(AIP、IREN、CLVT)——不是造假,是我的探針太死板。
這一支改核**指引數字本身**:把子隊引述裡的每一個金額 / 百分比抽出來,
逐個查是否出現在該次申報的原文,數字才是標籤所依據的東西。
輸出:label_number_check.csv
"""
import os, re, sys, json, time, html
import urllib.request
import pandas as pd

sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE  # noqa

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
UA = "Karst Research (VANESSALAU@vl-lawyers.com)"
CHECK = ["CRDO", "LULU", "FN", "CRNC", "ON", "ARM",
         # 全六十家核完之後補上的:整句對不上、或者根本沒有可核英文整句的另外五家
         "POWL", "MEC", "AIP", "IREN", "CLVT"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def norm(s):
    s = html.unescape(s)
    for a, b in [("\u00a0", " "), ("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'),
                 ("\u201d", '"'), ("\u2013", "-"), ("\u2014", "-")]:
        s = s.replace(a, b)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_sections():
    out = {}
    for i in range(1, 6):
        with open(os.path.join(D, "labels_batch%d.md" % i), encoding="utf-8") as fh:
            txt = fh.read()
        for sec in re.split(r"\n## ", txt)[1:]:
            m = re.match(r"([A-Z]{1,5})\b", sec.strip())
            if m:
                out[m.group(1)] = sec
    return out


def filing_text(cik, acc):
    a = acc.replace("-", "")
    base = "https://www.sec.gov/Archives/edgar/data/%d/%s/" % (int(cik), a)
    items = json.loads(get(base + "index.json").decode("utf-8", "ignore"))["directory"]["item"]
    blobs = []
    for it in items:
        nm = it["name"]
        if nm.lower().endswith((".htm", ".html", ".txt")) and not nm.lower().endswith("-index.htm"):
            try:
                blobs.append(norm(get(base + nm).decode("utf-8", "ignore")))
            except Exception:
                pass
            time.sleep(0.1)
    return " ".join(blobs)


NUM = re.compile(r"\$?\s?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)\s?(billion|million|bn|m|%)?",
                 re.I)


def variants(num, unit):
    """一個數字在新聞稿裡可能出現的寫法。"""
    v = num.replace(",", "")
    out = {num, v}
    try:
        f = float(v)
    except ValueError:
        return out
    u = (unit or "").lower()
    if u in ("billion", "bn"):
        out |= {format(f * 1000, ",.0f"), format(f * 1000, ",.1f"), format(f, ".3f"),
                format(f, ".2f"), format(f, ".1f")}
    if u in ("million", "m"):
        out |= {format(f, ",.0f"), format(f, ",.1f"),
                format(f / 1000, ".3f"), format(f / 1000, ".2f")}
    if f == int(f):
        out.add(str(int(f)))
        out.add(format(int(f), ","))
    return {x for x in out if len(x) >= 2}


def main():
    secs = parse_sections()
    rows = []
    for t in CHECK:
        sec = secs[t]
        acc = re.search(r"accession\s+([0-9]{10}-[0-9]{2}-[0-9]{6})", sec).group(1)
        text = filing_text(int(IE.cik_for(t)), acc)
        # \u5f15\u865f\u653e\u5bec\u5230 10 \u5b57\u5143\u8d77,\u4e26\u4e14\u4e0d\u9650\u958b\u982d\u5fc5\u9808\u662f\u82f1\u6587\u5b57\u6bcd\u2014\u2014AIP / IREN / CLVT \u7684\u6307\u5f15
        # \u662f\u8868\u683c\u6458\u9304,\u5b50\u968a\u7528\u4e2d\u6587\u9023\u63a5\u8a5e\u4e32\u8d77\u4f86,\u56b4\u683c\u7684\u6574\u53e5\u898f\u5247\u62bd\u4e0d\u5230\u4efb\u4f55\u4e00\u689d\u3002
        quotes = re.findall(r"[\"\u201c]([^\"\u201d]{10,})[\"\u201d]", sec)
        if not quotes:
            quotes = [sec]      # \u9023\u5f15\u865f\u90fd\u6c92\u6709\u7684,\u6574\u6bb5\u62ff\u53bb\u62bd\u6578\u5b57
        found, missing, seen = [], [], set()
        for q in quotes:
            for num, unit in NUM.findall(norm(q)):
                if num in seen or len(num.replace(",", "").replace(".", "")) < 2:
                    continue
                seen.add(num)
                lbl = "%s%s" % (num, (" " + unit) if unit else "")
                if any(v in text for v in variants(num, unit)):
                    found.append(lbl)
                else:
                    missing.append(lbl)
        rows.append(dict(ticker=t, accession=acc, n_numbers=len(found) + len(missing),
                         n_found=len(found), found="; ".join(found)[:200],
                         missing="; ".join(missing)[:200]))
        print("%-5s 指引數字 %d 個,查得到 %d 個" % (t, len(found) + len(missing), len(found)))
        if missing:
            print("      查不到:", "; ".join(missing))
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(D, "label_number_check.csv"), index=False, encoding="utf-8")
    print("=" * 60)
    print(d[["ticker", "n_numbers", "n_found"]].to_string(index=False))


if __name__ == "__main__":
    main()
