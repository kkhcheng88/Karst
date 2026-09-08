"""KARST-188 主線抽核(第二部分):錯價來源標籤的**證據**核實。

merge_labels.py 只核了「標籤有沒有跟規則走」。這一支核的是另一件事:
子隊引的那份 SEC 業績新聞稿是否真的存在、裡面是否真的有它引述的那句指引原文。

做法:
  1. 由五份標籤檔抽出每家引用的 accession number 與連結;
  2. 用 companyfacts 快取查該公司 CIK,直接組 EDGAR 申報索引,
     取回該次申報的**全部**文件(不只子隊引的那一份);
  3. 把子隊引述的英文原句正規化(去掉不換行空格、編輯用方括號、多重空白),
     取一段 40 字元的獨特子串,檢查是否逐字出現在該次申報的任何一份文件內。

抽核家數:20 家(六十家的三分之一),涵蓋排位前十二家全部 + 8 家其他。
輸出:label_evidence_check.csv
"""
import os, re, sys, json, time, html
import urllib.request
import pandas as pd

sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE  # noqa

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
UA = "Karst Research (VANESSALAU@vl-lawyers.com)"

CHECK_20 = ["CRDO", "STRL", "FSLR", "COLL", "CLS", "LULU", "CRUS", "INOD", "FN", "AGX",
            "CRNC", "RMBS", "ADTN", "ENPH", "ON", "ARM", "QCOM", "ORCL", "TDC", "VIAV"]
# 主線抽核的責任範圍是 20 家(六十家的三分之一)。腳本走通之後順手把餘下四十家也核一次,
# 令「零家資料不足」這句話有六十家的文件支撐,而不只是二十家。
_ALL = [ln.split(",")[0] for ln in
        open(os.path.join(D, "screen60_full.csv"), encoding="utf-8").read().splitlines()[1:]]
CHECK = CHECK_20 + [t for t in _ALL if t not in CHECK_20]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def norm(s):
    s = html.unescape(s)
    s = s.replace("\u00a0", " ").replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = re.sub(r"\[[^\]]*\]", " ", s)          # 子隊加的編輯用方括號
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[^A-Za-z0-9\.\,\%\$\-\(\)\' ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_sections():
    out = {}
    for i in range(1, 6):
        p = os.path.join(D, "labels_batch%d.md" % i)
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
        for sec in re.split(r"\n## ", txt)[1:]:
            m = re.match(r"([A-Z]{1,5})\b", sec.strip())
            if m:
                out[m.group(1)] = sec
    return out


def filing_texts(cik, acc):
    """取回該次申報全部文件的正規化全文(串成一條)。"""
    a = acc.replace("-", "")
    base = "https://www.sec.gov/Archives/edgar/data/%d/%s/" % (int(cik), a)
    try:
        idx = get(base + "index.json").decode("utf-8", "ignore")
        items = json.loads(idx)["directory"]["item"]
    except Exception as e:
        return None, "索引取不到: %s" % str(e)[:50]
    blobs = []
    for it in items:
        nm = it["name"]
        if not nm.lower().endswith((".htm", ".html", ".txt")):
            continue
        if nm.lower().endswith("-index.htm"):
            continue
        try:
            blobs.append(norm(get(base + nm).decode("utf-8", "ignore")))
        except Exception:
            pass
        time.sleep(0.1)
    return " ".join(blobs), base


def main():
    secs = parse_sections()
    rows = []
    for t in CHECK:
        sec = secs.get(t)
        rec = dict(ticker=t)
        if not sec:
            rec.update(status="標籤檔無此段"); rows.append(rec); continue
        accs = re.findall(r"accession\s+([0-9]{10}-[0-9]{2}-[0-9]{6})", sec)
        quotes = re.findall(r"[\"\u201c]([A-Za-z][^\"\u201d]{40,})[\"\u201d]", sec)
        rec.update(accession=accs[0] if accs else "", n_quotes=len(quotes))
        if not accs:
            rec.update(status="段落內無 accession(公司無發指引時可以是這樣)")
            rows.append(rec); print(t, rec["status"]); continue
        try:
            cik = int(IE.cik_for(t))
        except Exception as e:
            rec.update(status="CIK 查不到"); rows.append(rec); continue
        text, base = filing_texts(cik, accs[0])
        if text is None:
            rec.update(status=base); rows.append(rec); print(t, base); continue
        rec["doc_chars"] = len(text)
        hit, miss = 0, []
        checked = 0
        for q in quotes[:6]:
            probe = norm(q)
            # 取最長的一段純英文子串作探針,避開數字格式差異
            words = [w for w in probe.split(" ") if w]
            probe40 = ""
            for k in range(len(words)):
                cand = " ".join(words[k:k + 8])
                if sum(c.isalpha() for c in cand) >= 35:
                    probe40 = cand
                    break
            if not probe40:
                continue
            checked += 1
            if probe40.lower() in text.lower():
                hit += 1
            else:
                miss.append(probe40[:60])
        rec.update(quotes_checked=checked, quotes_found=hit,
                   missing="; ".join(miss)[:240],
                   status=("全部引句核實" if checked and hit == checked else
                           "部分引句核實" if hit else
                           "引句對不上" if checked else "無可核英文引句"))
        rows.append(rec)
        print(t, rec["status"], hit, "/", checked, "文件字數", rec["doc_chars"])

    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(D, "label_evidence_check.csv"), index=False, encoding="utf-8")
    print("=" * 66)
    print(d[["ticker", "accession", "status", "quotes_checked", "quotes_found"]].to_string(index=False))
    print()
    print(d["status"].value_counts().to_string())


if __name__ == "__main__":
    main()
