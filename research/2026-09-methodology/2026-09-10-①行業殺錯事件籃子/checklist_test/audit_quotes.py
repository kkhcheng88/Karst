# -*- coding: utf-8 -*-
"""KARST-204:引用抽查——把卡上的英文引句拿回衝擊前申報原文核對。

規格 §四 第 2 條:「引用核對抽查每宗事件 20%(示例值),抽中而出處指不回原文的,
該格作廢並記一次。」本檔把那條抽查機械化:抽查不靠人眼,靠字串比對,
所以可以做到全查而不只是 20%——票另外要求人手抽查十家,那一份另做。

做法:由 `卡-E*.md` 逐家抽出英文引句(至少六個字的連續英文,夾在引號內),
到 `docs/<EVENT>/<TICKER>__*.txt` 找。正規化空白與引號之後做子字串比對;
比對不中再試「引句頭 12 個字」的寬鬆比對(申報正文常有換行與表格雜訊)。

輸出:out/quote_audit.csv(逐句一行)與 out/quote_audit_summary.csv(逐家一行)。
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
SEC_HDR = re.compile(r"^#{2,3}\s*(?:\d+[.、]\s*)?([A-Z][A-Z0-9.\-]{0,5})\b")


def norm(s):
    s = s.replace("\u00a0", " ").replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = re.sub(r"[^A-Za-z0-9%$.,()'\- ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def load_docs(eid):
    d = {}
    for p in glob.glob(f"{BASE}/docs/{eid}/*.txt"):
        tk = os.path.basename(p).split("__")[0]
        with open(p, encoding="utf-8", errors="ignore") as f:
            d.setdefault(tk, []).append(norm(f.read()))
    return d


def main(eids):
    rows = []
    for eid in eids:
        card = f"{BASE}/卡-{eid}.md"
        if not os.path.exists(card):
            print("無卡:", eid)
            continue
        docs = load_docs(eid)
        with open(card, encoding="utf-8") as f:
            lines = f.read().split("\n")
        cur = None
        for ln in lines:
            m = SEC_HDR.match(ln.strip())
            if ln.strip().startswith("#"):
                hit = re.findall(r"\b([A-Z]{1,5})\b", ln)
                for h in hit:
                    if h in docs:
                        cur = h
                        break
            for q in QUOTE.findall(ln):
                if len(re.findall(r"[A-Za-z]{3,}", q)) < 5:
                    continue          # 中文句或太短,不是申報引句
                if not re.search(r"[A-Za-z]", q):
                    continue
                nq = norm(q)
                if not nq:
                    continue
                blobs = docs.get(cur, [])
                status = "找不到公司文件" if not blobs else "指不回原文"
                # 引句常用省略號接駁兩段原文;逐段各自核,全部找得到才算成功
                frags = [f.strip() for f in re.split(r"\.\.\.+|…", nq) if
                         len(re.findall(r"[A-Za-z]{3,}", f)) >= 4]
                if not frags:
                    frags = [nq]
                for b in blobs:
                    if all(f in b for f in frags):
                        status = "核對成功" if len(frags) == 1 else "核對成功(分段)"
                        break
                    head = " ".join(frags[0].split()[:12])
                    if len(head) > 30 and head in b:
                        status = "核對成功(頭段)"
                        break
                rows.append({"event_id": eid, "ticker": cur or "",
                             "quote": q[:200], "status": status})
    if not rows:
        print("無引句")
        return
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/quote_audit.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["event_id", "ticker", "quote", "status"])
        w.writeheader()
        w.writerows(rows)

    agg = {}
    for r in rows:
        k = (r["event_id"], r["ticker"])
        a = agg.setdefault(k, {"n": 0, "ok": 0})
        a["n"] += 1
        a["ok"] += r["status"].startswith("核對成功")
    with open(f"{OUT}/quote_audit_summary.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "ticker", "n_quotes", "n_ok", "rate"])
        for (e, t), a in sorted(agg.items()):
            w.writerow([e, t, a["n"], a["ok"], round(a["ok"] / a["n"], 3)])

    n = len(rows)
    ok = sum(1 for r in rows if r["status"].startswith("核對成功"))
    print(f"引句 {n} 句,核對成功 {ok} 句({ok / n:.1%}),指不回原文 {n - ok} 句")


if __name__ == "__main__":
    main(sys.argv[1:] or ["E03", "E12", "E13"])
