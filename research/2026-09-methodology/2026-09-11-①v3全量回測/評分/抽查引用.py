# -*- coding: utf-8 -*-
"""KARST-215 引用抽查:每批抽兩家,把卡上的英文引文拿回衝擊前原文核。

只讀;不改任何既有輸出。來源:
  批1 → 批1/docs/*.txt
  批2 → 批2/docs/*.txt
  批3 → 無本地 docs(落檔清單沒有),改核 199 checklist_test/docs/<E>/*.txt,
        該處正是批3 packets 內 prefiling_docs 欄所指向的原文。

口徑(重要):卡上的「引文」有四種寫法,核逐字比對會把後三種一律判落空,不公平。故三級:
  (1) 逐字命中:去掉 `**`、正規化(彎引號→直引號、`®/™` 與其前後空白刪走、大小寫、
      非英數字符全部忽略)之後,引文是原文的連續子串。
  (2) 拼接命中:引文按 `…`／`...` 切成 ≥20 字元的片段,或(無省略號時)由中間切成前後
      兩半;只要有一個片段命中,或前後兩半**依序**出現在原文、相隔 ≤200 字元,即算命中。
      這一級專收兩種真實寫法:(a) 申報目錄頁／表頭被夾在句子中間(原文是
      「…repackaged Avastin ® 24 Table of Contents in patients with wet AMD presents…」);
      (b) 卡上把兩個申報句子併成一句。
  (3) 落空:以上皆非。
落空逐條印出,由人核是「原文真的沒有」還是「只是改寫」。

用法:PYTHONUTF8=1 python 抽查引用.py
"""
import csv
import glob
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(BASE)
METH = os.path.dirname(V3)
CT = os.path.join(METH, "2026-09-10-①行業殺錯事件籃子", "checklist_test", "docs")

PICKS = [
    ("批1", "E02", "REGN", "卡-E02.md"),
    ("批1", "E04", "FSLY", "卡-E04.md"),
    ("批2", "E10", "CNC", "卡-E10.md"),
    ("批2", "E07", "NVDA", "卡-E07.md"),
    ("批3", "E08", "NKE", "卡-E08.md"),
    ("批3", "E14", "CHGG", "卡-E14.md"),
]

QUOTE_RE = re.compile(r"[「『\"“]([^」』\"”]{25,400})[」』\"”]")
FRAG_SPLIT = re.compile(r"…|\.\.\.|；……|\s\*\*\s")
WS = re.compile(r"\s+")
MIN_FRAG = 20


def norm(s):
    return WS.sub(" ", s.replace("**", "").replace("`", "")).strip()


CURL = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"',
                      "—": "-", "–": "-", " ": " "})
NONALNUM = re.compile(r"[^0-9a-z]")


def key(s):
    """比對用鍵:正規化 + 刪商標符號與其前後空白 + 去大小寫 + 只留英數。"""
    s = norm(s).translate(CURL)
    s = re.sub(r"\s*[®™]\s*", "", s)
    return NONALNUM.sub("", s.lower())


def frags(q):
    """≥20 字元片段;無省略號者,由中間切成前後兩半備用。"""
    out = [f for f in (norm(x) for x in FRAG_SPLIT.split(q)) if len(f) >= MIN_FRAG]
    if len(out) == 1:
        ws = out[0].split(" ")
        if len(ws) >= 6:
            h = len(ws) // 2
            out = [" ".join(ws[:h]), " ".join(ws[h:])]
    return out


def grade(q, docs):
    """回傳 逐字／拼接／落空。"""
    kq = key(q)
    if any(kq in key(body) for _, body in docs):
        return "逐字"
    for f in frags(q):
        kf = key(f)
        if len(kf) >= 15 and any(kf in key(body) for _, body in docs):
            return "拼接"
    fs = frags(q)
    if len(fs) == 2:
        ka, kb = key(fs[0]), key(fs[1])
        for _, body in docs:
            kb_body = key(body)
            i = kb_body.find(ka)
            if i >= 0:
                j = kb_body.find(kb, i + len(ka))
                if j >= 0 and j - (i + len(ka)) <= 200:
                    return "拼接"
    return "落空"


def load_docs(batch, event):
    pats = ([os.path.join(CT, event, "*.txt")] if batch == "批3"
            else [os.path.join(V3, batch, "docs", "*.txt")])
    out = []
    for p in pats:
        for f in glob.glob(p):
            with open(f, encoding="utf-8", errors="replace") as fh:
                out.append((os.path.basename(f), norm(fh.read())))
    return out


def section(text, ticker):
    """卡檔以 `## 一、<名>(<代號>)` 分段;取含該代號那一節。"""
    parts = re.split(r"(?m)^##\s+", text)
    for p in parts[1:]:
        head = p.split("\n", 1)[0]
        if re.search(r"[（(]%s[）)]" % re.escape(ticker), head):
            return p
    return text


def main():
    rows = []
    for batch, event, ticker, card in PICKS:
        with open(os.path.join(V3, batch, card), encoding="utf-8") as fh:
            seg = section(fh.read(), ticker)
        docs = load_docs(batch, event)
        quotes, seen = [], set()
        for q in QUOTE_RE.findall(seg):
            q2 = norm(q)
            asc = sum(1 for ch in q2 if ord(ch) < 128)
            if len(q2) >= MIN_FRAG and asc / max(len(q2), 1) >= 0.8 and q2 not in seen:
                seen.add(q2); quotes.append(q2)
        g = [grade(q, docs) for q in quotes]
        z, p, m = g.count("逐字"), g.count("拼接"), g.count("落空")
        hit = z + p
        rows.append(dict(批次=batch, 事件=event, 代號=ticker, 卡內引文數=len(quotes),
                         逐字=z, 拼接=p, 落空=m, 命中=hit,
                         命中率=round(hit / len(quotes), 3) if quotes else None,
                         原文檔數=len(docs)))
        print("== %s %s %s:引文 %d 條 → 逐字 %d、拼接 %d、落空 %d;原文檔 %d 份"
              % (batch, event, ticker, len(quotes), z, p, m, len(docs)))
        for q, gg in zip(quotes, g):
            if gg == "落空":
                print("   落空:%s" % q[:120])
    tot_q = sum(r["卡內引文數"] for r in rows)
    tot_z = sum(r["逐字"] for r in rows)
    tot_p = sum(r["拼接"] for r in rows)
    tot_h = tot_z + tot_p
    print("\n合計:引文 %d 條 → 逐字 %d、拼接 %d、落空 %d;命中率 %.1f%%"
          % (tot_q, tot_z, tot_p, tot_q - tot_h, 100.0 * tot_h / tot_q))
    with open(os.path.join(BASE, "抽查引用.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
        w.writerow(dict(批次="合計", 事件="", 代號="", 卡內引文數=tot_q, 逐字=tot_z,
                        拼接=tot_p, 落空=tot_q - tot_h, 命中=tot_h,
                        命中率=round(tot_h / tot_q, 3), 原文檔數=""))


if __name__ == "__main__":
    main()
