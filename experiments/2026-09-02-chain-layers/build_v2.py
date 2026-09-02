# -*- coding: utf-8 -*-
"""KARST-161 建 chain_membership_v2.csv 與 removed_v2.csv。

做四件事:
1. 讀 chain_membership_v1.csv(utf-8-sig)。**v1 檔一字不改**,只作來源。
2. 按 roster_v2.py 的 CHAINS 重組:承接的成員原欄(valid_from/valid_to/role/note/
   source_url/evidence_10k/added_by/valid_from_basis/filer_type)一字不改搬過來;
   story/position/purity_note 換成 v2 該鏈的。
3. v2 新增成員查 EDGAR(submissions API)拿申報表型與最近一份年報,年報全文只入
   D-134 共用快取 data/sec/10k_text/,抓前先查 manifest.jsonl,已有就不重抓。
4. 對帳:v1 的 309 行必須「有承接」或「在 REMOVED 名單」,兩者皆非即報錯。

EDGAR 規矩:每秒 ≤10 請求,User-Agent = Casy Limited kaho.career@gmail.com。
生產庫 karst.sqlite 全程不碰。
"""
import csv, gzip, hashlib, json, os, re, sys, time
import urllib.request

ROOT = r"C:\projects\Karst"
EXP = os.path.join(ROOT, "experiments", "2026-09-02-chain-layers")
CACHE = os.path.join(ROOT, "data", "sec", "10k_text")
MANIFEST = os.path.join(CACHE, "manifest.jsonl")
SCRATCH = (r"C:\Users\Kaho\AppData\Local\Temp\claude\C--projects-Karst"
           r"\d2e5d32d-fb0a-455e-a4f0-b5414e1a7c69\scratchpad")
SUBDIR = os.path.join(SCRATCH, "subs")
UA = "Casy Limited kaho.career@gmail.com"
TICKET = "chain-purity-161"

sys.path.insert(0, EXP)
from roster_v2 import CHAINS, REMOVED, EXACT

os.makedirs(SUBDIR, exist_ok=True)
_last = [0.0]


def get(url):
    wait = 0.13 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "gzip, deflate"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            import io
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    _last[0] = time.time()
    return raw.decode("utf-8", "replace")


with open(os.path.join(SCRATCH, "company_tickers.json"), encoding="utf-8") as f:
    TMAP = {v["ticker"]: v["cik_str"] for v in json.load(f).values()}


def subs(cik):
    p = os.path.join(SUBDIR, f"{cik}.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    d = json.loads(get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"))
    json.dump(d, open(p, "w", encoding="utf-8"))
    return d


MAN = {}
with open(MANIFEST, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            r = json.loads(line)
            MAN.setdefault(r["ticker"], []).append(r)

FETCHED, MISSING, FOREIGN = [], [], []


def annual_report(tk):
    cik = TMAP.get(tk)
    if not cik:
        return None
    try:
        d = subs(cik)
    except Exception as e:
        print(f"  ! {tk} submissions 失敗 {e}")
        return None
    rec = d["filings"]["recent"]
    first = min(rec["filingDate"]) if rec["filingDate"] else ""
    # v1 的漏洞:submissions 的 recent 只載最近約一千份申報,大型股的 min(filingDate)
    # 會是近年日期,不是真正首次申報日。older pages 的 filingFrom 才是真的。
    for pg in (d["filings"].get("files") or []):
        fr = pg.get("filingFrom") or ""
        if fr and (not first or fr < first):
            first = fr
    best = None
    for i, form in enumerate(rec["form"]):
        if form in ("10-K", "10-K405", "20-F", "40-F"):
            cand = (form, rec["accessionNumber"][i].replace("-", ""),
                    rec["primaryDocument"][i], rec["filingDate"][i], rec["reportDate"][i])
            if best is None or (cand[3] > best[3] and
                                not (best[0] == "10-K" and cand[0] != "10-K")):
                best = cand
    if not best:
        return None
    form, acc, doc, fdate, rdate = best
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"
    return form, acc, url, fdate, rdate, first, int(cik)


def ensure_cached(tk, info):
    form, acc, url, fdate, rdate, first, cik = info
    if tk in MAN and MAN[tk]:
        have = [r for r in sorted(MAN[tk], key=lambda r: r.get("reportDate") or "")
                if os.path.exists(os.path.join(
                    CACHE, r.get("path") or f"{r['ticker']}_{r['accession']}.txt.gz"))]
        if have:
            return have[-1]
    if form != "10-K":
        FOREIGN.append((tk, form))
        return None
    try:
        html = get(url)
    except Exception as e:
        print(f"  ! {tk} 年報下載失敗 {e}")
        MISSING.append((tk, str(e)))
        return None
    text = re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html))
    text = re.sub(r"&nbsp;?", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&#\d+;", " ", text)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    path = f"{tk}_{acc}.txt.gz"
    with gzip.open(os.path.join(CACHE, path), "wb") as g:
        g.write(text.encode("utf-8"))
    rec = {"ticker": tk, "cik": f"{cik:010d}", "accession": acc, "form": form,
           "filingDate": fdate, "reportDate": rdate, "url": url,
           "chars": len(text),
           "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
           "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
           "fetchedBy": TICKET}
    with open(MANIFEST, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    MAN.setdefault(tk, []).append(rec)
    FETCHED.append(tk)
    return rec


WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-\./%$,']*")
JUNK = re.compile(r"(us-gaap:|srt:|dei:|xbrl|iso4217|\b\d{10}\b|\b\d{4}-\d{2}-\d{2}\b)", re.I)


def is_junk(s):
    toks = s.split()
    if not toks or JUNK.search(s):
        return True
    numish = sum(1 for t in toks if not re.search(r"[A-Za-z]{3}", t))
    return numish > len(toks) * 0.3


def evidence(rec, kws):
    if not rec:
        return ""
    p = os.path.join(CACHE, rec.get("path") or f"{rec['ticker']}_{rec['accession']}.txt.gz")
    if not os.path.exists(p):
        return ""
    try:
        with gzip.open(p, "rt", encoding="utf-8", errors="replace") as g:
            txt = g.read()
    except Exception:
        return ""
    low = txt.lower()
    year = (rec.get("reportDate") or rec.get("filingDate") or "")[:4]
    for kw in kws:
        start = 0
        for _ in range(30):
            i = low.find(kw.lower(), start)
            if i < 0:
                break
            start = i + 1
            seg = re.sub(r"\s+", " ", txt[max(0, i - 120): i + 240]).strip()
            if len(WORD.findall(seg)) < 12:
                continue
            toks = seg.split()
            hit = next((n for n, w in enumerate(toks)
                        if kw.split()[0].lower() in w.lower()), None)
            if hit is None:
                continue
            snip = " ".join(toks[max(0, hit - 5): max(0, hit - 5) + 15])
            snip = re.sub(r'^[^A-Za-z0-9]+', '', snip).strip().replace('"', "'")
            if len(snip.split()) >= 8 and not is_junk(snip):
                return f"{year}:{snip}"
    return f"{year}:(快取有卷但關鍵詞未命中)"


# ── 讀 v1(唯讀,不改) ──────────────────────────────────────────────────────
with open(os.path.join(EXP, "chain_membership_v1.csv"), encoding="utf-8-sig",
          newline="") as f:
    v1 = list(csv.DictReader(f))
V1IDX = {}
for r in v1:
    V1IDX.setdefault((r["theme"], r["ticker"]), []).append(r)
print(f"v1 讀入 {len(v1)} 行,{len(set(r['theme'] for r in v1))} 條鏈")

# ── v2 新增成員先查 EDGAR ────────────────────────────────────────────────────
NEW = []
for th, c in CHAINS.items():
    for tk, src, pur in c["members"]:
        if src is None:
            NEW.append((th, tk))
newt = sorted(set(t for _, t in NEW))
print(f"v2 新增成員 {len(NEW)} 行,{len(newt)} 隻代碼要查 EDGAR")

INFO, REC = {}, {}
for n, tk in enumerate(newt, 1):
    info = annual_report(tk)
    INFO[tk] = info
    if info:
        REC[tk] = ensure_cached(tk, info)
    else:
        MISSING.append((tk, "EDGAR 查無年報"))
    if n % 20 == 0:
        print(f"  ...{n}/{len(newt)}")
print(f"新抓年報 {len(FETCHED)} 份;外國申報人 {len(FOREIGN)} 隻;查不到 {len(MISSING)} 隻")


def src_url(tk):
    info = INFO.get(tk)
    if info:
        return info[2]
    return (f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
            f"&company={tk}&type=10-K")


# ── 砌 v2 ────────────────────────────────────────────────────────────────────
OUT = ["theme", "ticker", "valid_from", "valid_to", "role", "note",
       "story", "position", "purity", "purity_note",
       "source_url", "evidence_10k", "added_by", "valid_from_basis",
       "filer_type", "src_theme_v1"]
rows, carried = [], set()
errors = []

for th, c in CHAINS.items():
    for tk, src, pur in c["members"]:
        purity = pur or c["purity_default"]
        if src is not None:
            got = V1IDX.get((src, tk))
            if not got:
                errors.append(f"承接不到 v1 行:{src}/{tk}")
                continue
            for r in got:
                carried.add(id(r))
                rows.append({
                    "theme": th, "ticker": tk,
                    "valid_from": r["valid_from"], "valid_to": r["valid_to"],
                    "role": r["role"], "note": r["note"],
                    "story": c["story"], "position": c["position"],
                    "purity": purity, "purity_note": c["purity_note"],
                    "source_url": r["source_url"], "evidence_10k": r["evidence_10k"],
                    "added_by": r["added_by"], "valid_from_basis": r["valid_from_basis"],
                    "filer_type": r["filer_type"], "src_theme_v1": src,
                })
        else:
            info = INFO.get(tk)
            if tk in EXACT:
                vf, basis = EXACT[tk]
            else:
                first = info[5] if info else ""
                if first and first > "2022-01-01":
                    vf = first
                    basis = "近似(EDGAR 首次申報日代上市日;查不到更早的入位事件)"
                else:
                    vf = "2022-01-01"
                    basis = "近似(2022-01-01 前已上市且業務未變,沿用 v0 走廊起點)"
            rows.append({
                "theme": th, "ticker": tk, "valid_from": vf, "valid_to": "",
                "role": "core", "note": "",
                "story": c["story"], "position": c["position"],
                "purity": purity, "purity_note": c["purity_note"],
                "source_url": src_url(tk),
                "evidence_10k": evidence(REC.get(tk), c["kw"]),
                "added_by": "v2", "valid_from_basis": basis,
                "filer_type": (info[0] if info else "無申報紀錄"),
                "src_theme_v1": "",
            })

# ── 對帳:v1 每一行必須有承接,或在出隊名單 ──────────────────────────────────
RMSET = {(t, k) for t, k, _, _ in REMOVED}
for r in v1:
    if id(r) in carried:
        continue
    if (r["theme"], r["ticker"]) in RMSET:
        continue
    errors.append(f"v1 行既無承接亦不在出隊名單:{r['theme']}/{r['ticker']}")

if errors:
    print("!! 對帳失敗:")
    for e in errors:
        print("   ", e)
    sys.exit(1)
print("對帳通過:v1 每一行不是被承接就是在出隊名單")

out = os.path.join(EXP, "chain_membership_v2.csv")
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=OUT)
    w.writeheader()
    w.writerows(rows)

# ── removed_v2.csv ───────────────────────────────────────────────────────────
RULE = {"a": "位置不同", "b": "定價機制不同", "c": "單一資產主導",
        "d": "主業已轉向(只入其股價主要跟隨的那條)"}
rmrows = []
for th, tk, rule, why in REMOVED:
    src = V1IDX.get((th, tk), [{}])[0]
    rmrows.append({
        "v1_theme": th, "ticker": tk, "rule": rule, "rule_name": RULE[rule],
        "reason": why,
        "v1_valid_from": src.get("valid_from", ""), "v1_valid_to": src.get("valid_to", ""),
        "v1_added_by": src.get("added_by", ""),
    })
with open(os.path.join(EXP, "removed_v2.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["v1_theme", "ticker", "rule", "rule_name",
                                      "reason", "v1_valid_from", "v1_valid_to",
                                      "v1_added_by"])
    w.writeheader()
    w.writerows(rmrows)

# ── 統計 ─────────────────────────────────────────────────────────────────────
stats = {}
for th, c in CHAINS.items():
    rs = [x for x in rows if x["theme"] == th]
    act = [x for x in rs if not x["valid_to"]]
    stats[th] = {
        "new": c["new"], "src": c["src"], "short": c["short"],
        "roster": len(set(x["ticker"] for x in rs)),
        "active": len(set(x["ticker"] for x in act)),
        "v2_added": sum(1 for x in rs if x["added_by"] == "v2"),
        "with_10k": sum(1 for x in rs if x["evidence_10k"]
                        and "快取有卷但關鍵詞未命中" not in x["evidence_10k"]),
        "members": [(x["ticker"], x["added_by"], bool(x["valid_to"]), x["src_theme_v1"])
                    for x in rs],
    }
appr = sum(1 for x in rows if "近似" in x["valid_from_basis"])
summary = {
    "chains_total": len(CHAINS),
    "chains_new_v2": sum(1 for c in CHAINS.values() if c["new"]),
    "chains_v1_retired": sorted(set(r["theme"] for r in v1) - set(CHAINS)),
    "rows": len(rows), "unique_tickers": len(set(x["ticker"] for x in rows)),
    "rows_v0": sum(1 for x in rows if x["added_by"] == "v0"),
    "rows_v1": sum(1 for x in rows if x["added_by"] == "v1"),
    "rows_v2": sum(1 for x in rows if x["added_by"] == "v2"),
    "removed_rows": len(rmrows),
    "valid_from_approx": appr, "valid_from_approx_pct": round(100 * appr / len(rows), 1),
    "evidence_hit": sum(1 for x in rows if x["evidence_10k"]
                        and "快取有卷但關鍵詞未命中" not in x["evidence_10k"]),
    "evidence_none": sorted(set(x["ticker"] for x in rows if not x["evidence_10k"])),
    "fetched": FETCHED, "foreign": FOREIGN, "missing": MISSING,
    "under5_roster": sorted(t for t, s in stats.items() if s["roster"] < 5),
    "under5_active": sorted(t for t, s in stats.items() if s["active"] < 5),
    "stats": stats,
}
json.dump(summary, open(os.path.join(SCRATCH, "v2_summary.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in summary.items() if k != "stats"},
                 ensure_ascii=False, indent=1)[:3000])
