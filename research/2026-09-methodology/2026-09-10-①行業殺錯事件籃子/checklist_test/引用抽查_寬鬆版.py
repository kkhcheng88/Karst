# -*- coding: utf-8 -*-
"""KARST-204 收尾:引用抽查的寬鬆版,量出機械比對的偽陰性有多大。

`audit_quotes.py` 只把空白收窄,原文若把標點與字隔開(表格抽出常見 `2016 , 2015`)
或把字切斷(PDF 抽出常見 `federal r eserve`),就會誤判「指不回原文」。
本檔改用**去掉全部空白**之後再比對,其餘完全不變。兩個數之差即偽陰性下限。

輸出:out/引用抽查_兩版對比.csv(逐家),另印總數。
"""
import csv
import glob
import os
import re
import sys

BASE = ("C:/projects/Karst/research/2026-09-methodology/"
        "2026-09-10-①行業殺錯事件籃子/checklist_test")
OUT = f"{BASE}/out"
QUOTE = re.compile(r"[\"“”「」]([^\"“”「」\n]{25,400}?)[\"“”「」]")


def norm(s, drop_space=False):
    s = s.replace("\u00a0", " ").replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = re.sub(r"[^A-Za-z0-9%$.,()'\- ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s.replace(" ", "") if drop_space else s


def load(eid, drop_space):
    d = {}
    for p in glob.glob(f"{BASE}/docs/{eid}/*.txt"):
        tk = os.path.basename(p).split("__")[0]
        with open(p, encoding="utf-8", errors="ignore") as f:
            d.setdefault(tk, []).append(norm(f.read(), drop_space))
    return d


def run(eids, drop_space):
    res = {}
    for eid in eids:
        card = f"{BASE}/卡-{eid}.md"
        if not os.path.exists(card):
            continue
        docs = load(eid, drop_space)
        cur = None
        with open(card, encoding="utf-8") as f:
            for ln in f.read().split("\n"):
                if ln.strip().startswith("#"):
                    for h in re.findall(r"\b([A-Z]{1,5})\b", ln):
                        if h in docs:
                            cur = h
                            break
                for q in QUOTE.findall(ln):
                    if len(re.findall(r"[A-Za-z]{3,}", q)) < 5:
                        continue
                    nq = norm(q, drop_space)
                    if not nq:
                        continue
                    blobs = docs.get(cur, [])
                    ok = False
                    frags = [f.strip() for f in re.split(r"\.\.\.+|…", nq) if f.strip()]
                    # 頭段一律由「保留空白」的版本取首 12 個字,才與 audit_quotes.py 同義
                    frags_sp = [f.strip() for f in
                                re.split(r"\.\.\.+|…", norm(q, False)) if f.strip()]
                    head = " ".join(frags_sp[0].split()[:12]) if frags_sp else ""
                    head = norm(head, drop_space)
                    for b in blobs:
                        if frags and all(f in b for f in frags):
                            ok = True
                            break
                        if len(head) > 30 and head in b:
                            ok = True
                            break
                    res.setdefault((eid, cur or ""), [0, 0])
                    res[(eid, cur or "")][0] += 1
                    res[(eid, cur or "")][1] += int(ok)
    return res


def main():
    eids = [f"E{i:02d}" for i in range(1, 15)]
    strict = run(eids, False)
    loose = run(eids, True)
    rows = []
    for k in sorted(set(strict) | set(loose)):
        sn, so = strict.get(k, [0, 0])
        ln, lo = loose.get(k, [0, 0])
        rows.append(dict(event_id=k[0], ticker=k[1], 句數=ln,
                         嚴版成功=so, 嚴版率=round(so / sn, 3) if sn else "",
                         寬版成功=lo, 寬版率=round(lo / ln, 3) if ln else "",
                         差=lo - so))
    with open(f"{OUT}/引用抽查_兩版對比.csv", "w", encoding="utf-8",
              newline="", ) as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    ts = sum(v[0] for v in strict.values()), sum(v[1] for v in strict.values())
    tl = sum(v[0] for v in loose.values()), sum(v[1] for v in loose.values())
    print(f"嚴版 {ts[1]}/{ts[0]} = {ts[1]/ts[0]:.1%};"
          f"寬版 {tl[1]}/{tl[0]} = {tl[1]/tl[0]:.1%};"
          f"偽陰性下限 {tl[1]-ts[1]} 句({(tl[1]-ts[1])/ts[0]:.1%})")
    worst = sorted([r for r in rows if r["寬版率"] != "" and float(r["寬版率"]) < 1],
                   key=lambda r: float(r["寬版率"]))
    print("寬版下仍然不達一的家:", len(worst))
    for r in worst:
        print("  ", r["event_id"], r["ticker"], f"{r['寬版成功']}/{r['句數']}")


if __name__ == "__main__":
    main()
