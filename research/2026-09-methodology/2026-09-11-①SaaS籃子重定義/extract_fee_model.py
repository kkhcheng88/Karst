# -*- coding: utf-8 -*-
"""KARST-209 步驟四(取證半):由各家自己的 10-K 全文抽出「怎樣收費」那幾句。

判準:只用**該公司自己的申報原文**;抽不到就標查不到,不猜。

做法(第一版抽全篇、第二版抽收入確認附註各中招一次,第三版改成排序):
1. 全篇掃高精度收費語(准許清單,不用「number of X」這種泛語——風險因素樣板
   大量出現「number of employees/users」,那是 False Positive 的主要來源)。
2. 每個命中取所在句,句子內若含 BOILER(股份酬金、可轉債、加權平均價一類)即丟。
   第一版中招的正是這一類:「based on the volume weighted average price」是**股價**
   不是收費;ASR、股份單位、匯率都不是。
3. 每句按「在收入確認附註窗口內」+「語句精度等級」排序,每家留最多三句候選。
4. **分桶不自動定**——人讀原句之後在 `收費模式.md` 定;本檔只負責找句與排句。

輸出 `fee_candidates.csv`(代號、候選一至三、取自、申報日、accession)。
"""
import csv
import glob
import gzip
import json
import re

OUT = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①SaaS籃子重定義"
CACHE = "C:/projects/Karst/data/sec/10k_text"

NOTE_HEAD = re.compile(
    r"revenue (?:recognition|from contracts with customers)|"
    r"revenue and (?:deferred|contract) (?:revenue|costs)", re.I)

# 精度等級由小到大,1 最精。每條都是「講怎樣收錢」的語式,不是「講有幾多人」。
PREC = [
    (1, "席位", r"per[\s\-](?:user|seat|subscriber|agent|endpoint|device|employee|"
                r"technician|bed|room|clinician|advisor|unit|location|store|register)"),
    (1, "席位", r"(?:seat|user|subscriber|per[\s\-]user)[\s\-]based"),
    (2, "席位", r"(?:charg|pric|fee|fees|subscription|licen[cs]e|bill)[^.]{0,90}"
                r"based on the number of (?:users|seats|subscribers|employees|"
                r"endpoints|devices|agents|advisors)"),
    (1, "用量或交易", r"usage[\s\-]based|consumption[\s\-]based|transaction[\s\-]based|"
                 r"volume[\s\-]based|capacity[\s\-]based"),
    (1, "用量或交易", r"based on (?:the )?(?:actual )?(?:usage|consumption|"
                 r"transaction volume|volume of|number of transactions|assets under)"),
    (2, "用量或交易", r"per[\s\-](?:transaction|call|query|record|message|"
                 r"API call|gigabyte|terabyte|GB|TB|report|document|claim|"
                 r"covered life|loan|order|shipment|user per)"),
    (2, "用量或交易", r"(?:fees?|revenue|pric\w+|charg\w+)[^.]{0,90}"
                 r"(?:based on|equal to|as a percentage of)[^.]{0,40}"
                 r"(?:transaction|usage|consumption|volume|number of transactions)"),
    (1, "資產或存戶", r"assets under management|based on (?:the )?(?:value|size|balance) of"
                 r" (?:the )?(?:assets|portfolio|deposits|accounts)|"
                 r"average (?:daily )?balance"),
    (2, "資產或存戶", r"per[\s\-]account|based on (?:the )?number of accounts|"
                 r"(?:fees?|pric\w+)[^.]{0,80}(?:account|deposit|asset) balance"),
    (1, "授權或永久", r"perpetual licen[cs]|term licen[cs]|software licen[cs]e fee|"
                 r"licen[cs]e[\s\-]based"),
    (3, "授權或永久", r"sales[\s\-]based or usage[\s\-]based royalt"),
    (2, "訂閱(未標明計量)", r"subscription[\s\-]based (?:model|pricing|business|service|offering)|"
                   r"(?:sold|offer\w*|sold as) (?:as )?(?:a )?subscription"),
]

# 命中句含這些 = 講股價/酬金/租約/債,不是講收費(前一版誤中的主要原因)
BOILER = re.compile(r"volume weighted average|stock units|share price|stock price|"
                    r"exercise price|purchase price allocation|"
                    r"compensation expense|convertible notes|repurchase|"
                    r"attrition rate|diluted|earnings per share|"
                    r"\blease|right-of-use|interest income|interest expense|"
                    r"employee contributions|addressable market|"
                    r"number of employees (?:we|that)|our employees",
                    re.I)

# 命中句必須同時有收費語境,否則只是碰巧出現「per user」一類字(如 ARPU 定義、
# 租約、酬金)。這一條是前一版大量 False Positive 的直接解藥。
CONTEXT = re.compile(r"\b(pric\w+|fee|fees|revenue|subscription\w*|licen[cs]\w*|"
                     r"charg\w+|bill\w+|royalt\w+|pay\w+|rate|rates|invoice\w*|sell\w*|"
                     r"sold|offer\w*)\b", re.I)


def plain(path):
    with gzip.open(path, "rb") as f:
        h = f.read().decode("utf-8", errors="replace")
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&#8217;", "\u2019"),
                 ("&rsquo;", "\u2019"), ("&#39;", "'"), ("&quot;", '"'),
                 ("&#8220;", '"'), ("&#8221;", '"'), ("&#160;", " "),
                 ("&#8226;", " "), ("&#8211;", "-")):
        h = h.replace(a, b)
    # 行內標籤被剝走後會留下「subscription- based」「per- user」這種斷字,
    # 令 `subscription[\s\-]based` 這類樣式失手(前一版有 23 家因此掃不到任何語)。
    h = re.sub(r"-\s+", "-", h)
    return re.sub(r"\s+", " ", h)


def sentence_at(txt, mm):
    s = max(txt.rfind(". ", 0, mm.start()), txt.rfind("; ", 0, mm.start()))
    e = txt.find(". ", mm.end())
    sent = txt[s + 1: (e + 1) if e > 0 else mm.end() + 220].strip()
    if len(sent) < 50:
        sent = txt[max(0, mm.start() - 160): mm.end() + 220].strip()
    return re.sub(r"\s+", " ", sent)[:420]


def candidates(txt):
    """回 [(rank, bucket, sentence, where)],已去重、已按精度排序。"""
    notes = list(NOTE_HEAD.finditer(txt))
    win = (0, len(txt))
    if notes:
        st = notes[-1 if len(notes) > 4 else 0].start()
        win = (st, st + 60000)
    out, seen = [], set()
    for rank, bucket, pat in PREC:
        n_pat = 0
        for mm in re.finditer(pat, txt, re.I):
            sent = sentence_at(txt, mm)
            # 一等語(per-user / usage-based 一類)本身就夠專,不另加語境要求;
            # 二等以下的泛語才要求句內有收費語境(這正是前一版大量誤中的來源)。
            if BOILER.search(sent) or (rank > 1 and not CONTEXT.search(sent)):
                continue
            key = sent[:70]
            if key in seen:
                continue
            seen.add(key)
            where = "收入確認附註" if win[0] <= mm.start() < win[1] else "全文"
            out.append((rank, bucket, sent, where))
            n_pat += 1
            if n_pat >= 8:      # 每條樣式各自封頂,否則首條樣式會霸佔全部額度
                break
    out.sort(key=lambda r: (r[0], r[3] != "收入確認附註"))
    return out


def main():
    man = [json.loads(l) for l in
           open(f"{CACHE}/manifest.jsonl", encoding="utf-8") if l.strip()]
    by_ticker = {}
    for m in man:                       # 同一代號多份:取申報日最新那批
        t = m["ticker"]
        if t not in by_ticker or m["filingDate"] > by_ticker[t]["filingDate"]:
            by_ticker[t] = m

    cons = [r["ticker"] for r in csv.DictReader(open(f"{OUT}/constituents.csv",
                                                     encoding="utf-8-sig"))]
    rows = []
    for t in cons:
        m = by_ticker.get(t)
        path = (glob.glob(f"{CACHE}/{t}_{m['accession'].replace('-','')}.txt.gz")
                if m else [])
        if not path:
            rows.append({"代號": t, "無": "倉內快取與補抓皆無 10-K 全文"
                                          "(多為外國私人發行人交 20-F,或非美國申報人)",
                         "候選一": "", "候選二": "", "候選三": "",
                         "取自": "", "申報日": "", "accession": ""})
            continue
        cands = candidates(plain(path[0]))
        r = {"代號": t, "無": "" if cands else "全文掃不到任何收費語",
             "取自": cands[0][3] if cands else "",
             "申報日": m["filingDate"], "accession": m["accession"]}
        for i in range(3):
            r[f"候選{'一二三'[i]}"] = cands[i][2] if i < len(cands) else ""
        r["自動桶"] = " / ".join(dict.fromkeys(c[1] for c in cands[:3]))
        rows.append(r)

    with open(f"{OUT}/fee_candidates.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["代號", "候選一", "候選二", "候選三",
                                          "取自", "申報日", "accession", "自動桶", "無"])
        w.writeheader()
        w.writerows(rows)

    n_ok = sum(1 for r in rows if r["候選一"])
    lines = [f"{len(rows)} 家;有候選 {n_ok};無 {len(rows)-n_ok}"]
    for r in rows:
        if not r["候選一"]:
            lines.append(f"{r['代號']:6s}└── {r['無'] or '無'}")
            continue
        lines.append(f"{r['代號']:6s}|{r['候選一'][:175]}")
        if r["候選二"] and r["候選二"][:60] != r["候選一"][:60]:
            lines.append(f"      ↳|{r['候選二'][:175]}")
    with open(f"{OUT}/fee_candidates_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(lines[0])


if __name__ == "__main__":
    main()
