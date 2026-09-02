# -*- coding: utf-8 -*-
"""KARST-159 建 chain_membership_v1.csv。

做三件事:
1. 讀 chain_membership_v0.csv(utf-8-sig),v0 原行一字不改,只補新欄。
2. 對每個代碼查 EDGAR(submissions API)拿:申報表型(10-K / 20-F / 40-F)、最近一份年報的
   accession 與網址、首次申報日(作 valid_from 的機械退路)。
3. 年報全文只入 D-134 共用快取 data/sec/10k_text/,逐行 append manifest.jsonl;
   由快取抽一句佐證片段填 evidence_10k。

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
TICKET = "KARST-159"

sys.path.insert(0, EXP)
from roster_v1 import CHAINS, EXACT

os.makedirs(SUBDIR, exist_ok=True)
_last = [0.0]


def get(url, binary=False):
    """EDGAR 取檔,節流到每秒 ≤8 請求。"""
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
    return raw if binary else raw.decode("utf-8", "replace")


# ── ticker → cik ─────────────────────────────────────────────────────────────
with open(os.path.join(SCRATCH, "company_tickers.json"), encoding="utf-8") as f:
    TMAP = {v["ticker"]: v["cik_str"] for v in json.load(f).values()}
# v0 表內幾隻已除牌 / 改名的,手工補回 CIK(EDGAR 現役代碼表已無)
TMAP.setdefault("PXD", 1038357)   # Pioneer Natural Resources,2024 被 XOM 收購
TMAP.setdefault("GTBIF", 1690012)  # Green Thumb Industries(場外)
TMAP.setdefault("HUT", 1964789)    # Hut 8
TMAP.setdefault("SNDK", 2001348)   # Sandisk(2025 由 WDC 分拆)
# EDGAR 現役代碼表把 XOM 指向重組後的新控股 CIK(未有年報),年報仍在舊 CIK 名下
TMAP["XOM"] = 34088                # Exxon Mobil Corp


def subs(cik):
    """submissions JSON,存 scratchpad 避免重覆打 EDGAR。"""
    p = os.path.join(SUBDIR, f"{cik}.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    d = json.loads(get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"))
    json.dump(d, open(p, "w", encoding="utf-8"))
    return d


# ── manifest 索引 ────────────────────────────────────────────────────────────
MAN = {}          # ticker -> list of records
MAN_ACC = set()   # (ticker, accession)
with open(MANIFEST, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        MAN.setdefault(r["ticker"], []).append(r)
        MAN_ACC.add((r["ticker"], r["accession"]))

FETCHED, MISSING, FOREIGN = [], [], []


def annual_report(tk):
    """回傳 (form, accession, url, filingDate, reportDate, firstFilingDate)。"""
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
    best = None
    for i, form in enumerate(rec["form"]):
        if form in ("10-K", "10-K405", "20-F", "40-F"):
            cand = (form, rec["accessionNumber"][i].replace("-", ""),
                    rec["primaryDocument"][i], rec["filingDate"][i], rec["reportDate"][i])
            # 取最近一份;10-K 優先於 20-F/40-F
            if best is None or (cand[3] > best[3] and
                                not (best[0] == "10-K" and cand[0] != "10-K")):
                best = cand
    if not best:
        return None
    form, acc, doc, fdate, rdate = best
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"
    return form, acc, url, fdate, rdate, first, int(cik)


def ensure_cached(tk, info):
    """10-K 申報人:快取無就抓 EDGAR 並 append manifest。回傳 manifest 記錄。"""
    form, acc, url, fdate, rdate, first, cik = info
    if tk in MAN and MAN[tk]:
        # 取快取真的存在該檔、而且報告期最近的一份
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
    # 欄位照 manifest 現有主流那一套(fetchedBy,無 path;檔名 = <TICKER>_<accession>.txt.gz)
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
# 內聯 XBRL 的 context 區塊會夾雜大量標籤與日期,抽到就是垃圾,要擋
JUNK = re.compile(r"(us-gaap:|srt:|dei:|xbrl|iso4217|\b\d{10}\b|\b\d{4}-\d{2}-\d{2}\b)", re.I)


def is_junk(s):
    toks = s.split()
    if not toks or JUNK.search(s):
        return True
    numish = sum(1 for t in toks if not re.search(r"[A-Za-z]{3}", t))
    return numish > len(toks) * 0.3


def evidence(rec, kws):
    """由快取年報抽一句 ≤15 字(英文以詞計)的原文片段。"""
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
            # 由關鍵詞所在位置往前取 5 個詞,合共 15 個詞
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


# ── 讀 v0(原行一字不改) ────────────────────────────────────────────────────
with open(os.path.join(EXP, "chain_membership_v0.csv"), encoding="utf-8-sig", newline="") as f:
    v0 = list(csv.DictReader(f))
print(f"v0 原行 {len(v0)} 行,{len(set(r['theme'] for r in v0))} 條鏈")

# ── 收集所有要查 EDGAR 的代碼 ───────────────────────────────────────────────
tickers = set(r["ticker"] for r in v0)
for th, c in CHAINS.items():
    for a in c["add"]:
        tickers.add(a[0])
print(f"要查 EDGAR 的代碼共 {len(tickers)} 隻")

INFO, REC = {}, {}
for n, tk in enumerate(sorted(tickers), 1):
    info = annual_report(tk)
    INFO[tk] = info
    if info:
        REC[tk] = ensure_cached(tk, info)
    else:
        MISSING.append((tk, "EDGAR 查無年報"))
    if n % 40 == 0:
        print(f"  ...{n}/{len(tickers)}")

print(f"新抓年報 {len(FETCHED)} 份;外國申報人(20-F/40-F,無 10-K 快取){len(FOREIGN)} 隻;"
      f"查不到 {len(MISSING)} 隻")

# ── 砌 v1 ────────────────────────────────────────────────────────────────────
OUT = ["theme", "ticker", "valid_from", "valid_to", "role", "note",
       "story", "position", "source_url", "evidence_10k", "added_by",
       "valid_from_basis", "filer_type"]
rows = []


def src_url(tk):
    info = INFO.get(tk)
    if info:
        return info[2]
    return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={tk}&type=10-K"


def filer(tk):
    info = INFO.get(tk)
    return info[0] if info else "無申報紀錄"


for r in v0:
    th = r["theme"]
    c = CHAINS.get(th)
    tk = r["ticker"]
    rows.append({
        # ↓ v0 五欄原樣搬,一字不改
        "theme": r["theme"], "ticker": r["ticker"], "valid_from": r["valid_from"],
        "valid_to": r["valid_to"], "role": r["role"], "note": r["note"],
        # ↓ v1 新增欄
        "story": c["story"] if c else "", "position": c["position"] if c else "",
        "source_url": src_url(tk),
        "evidence_10k": evidence(REC.get(tk), c["kw"] if c else ["business"]),
        "added_by": "v0",
        "valid_from_basis": "沿用 v0(舊倉 ADR-0039 鎖死名單,未改)",
        "filer_type": filer(tk),
    })

for th, c in CHAINS.items():
    for tk, vf, basis, role, note in c["add"]:
        info = INFO.get(tk)
        if vf is None:
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
            "role": role, "note": note,
            "story": c["story"], "position": c["position"],
            "source_url": src_url(tk),
            "evidence_10k": evidence(REC.get(tk), c["kw"]),
            "added_by": "v1", "valid_from_basis": basis, "filer_type": filer(tk),
        })

out = os.path.join(EXP, "chain_membership_v1.csv")
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=OUT)
    w.writeheader()
    w.writerows(rows)

# ── 統計,供 chain_stories_v1.md 與 README 引用 ─────────────────────────────
stats = {}
for th, c in CHAINS.items():
    rs = [x for x in rows if x["theme"] == th]
    act = [x for x in rs if not x["valid_to"]]
    stats[th] = {
        "new": c["new"], "roster": len(set(x["ticker"] for x in rs)),
        "active": len(set(x["ticker"] for x in act)),
        "v1_added": len(c["add"]), "short": c["short"],
        "with_10k": sum(1 for x in rs if x["evidence_10k"]
                        and "快取有卷但關鍵詞未命中" not in x["evidence_10k"]),
        "members": [(x["ticker"], x["added_by"], bool(x["valid_to"])) for x in rs],
    }
appr = sum(1 for x in rows if "近似" in x["valid_from_basis"])
summary = {
    "chains_total": len(CHAINS), "chains_v0": sum(1 for c in CHAINS.values() if not c["new"]),
    "chains_v1": sum(1 for c in CHAINS.values() if c["new"]),
    "rows": len(rows), "unique_tickers": len(set(x["ticker"] for x in rows)),
    "v0_rows": sum(1 for x in rows if x["added_by"] == "v0"),
    "v1_rows": sum(1 for x in rows if x["added_by"] == "v1"),
    "valid_from_approx": appr, "valid_from_approx_pct": round(100 * appr / len(rows), 1),
    "evidence_hit": sum(1 for x in rows if x["evidence_10k"]
                        and "快取有卷但關鍵詞未命中" not in x["evidence_10k"]),
    "evidence_none": sum(1 for x in rows if not x["evidence_10k"]),
    "fetched": FETCHED, "foreign": FOREIGN, "missing": MISSING,
    "under5_roster": [t for t, s in stats.items() if s["roster"] < 5],
    "under5_active": [t for t, s in stats.items() if s["active"] < 5],
    "stats": stats,
}
json.dump(summary, open(os.path.join(SCRATCH, "v1_summary.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in summary.items() if k != "stats"},
                 ensure_ascii=False, indent=1)[:2500])
