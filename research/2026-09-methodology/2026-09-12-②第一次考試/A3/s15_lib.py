# -*- coding: utf-8 -*-
"""KARST-232 補強票共用工具:申報索引、抓取、XBRL 加十項、同業規則、歷史稿指引句。

只讀既有資料;抓回來的原文一律寫 `A/edgar_cache/`(票面許可「只新增,不改既有」)。
"""
from __future__ import annotations

import gzip
import html
import json
import re
import threading
import time
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE.parent / "A" / "edgar_cache"
CF = ROOT / "data" / "sec" / "companyfacts"
SUB = ROOT / "data" / "sec" / "submissions"
UA = {"User-Agent": "Karst research kaho@example.com"}
RATE_PER_SEC = 3.0

# ---------------------------------------------------------------- 抓取(單線程)

_last = [0.0]
_lock = threading.Lock()


def _throttle() -> None:
    with _lock:
        now = time.time()
        wait = _last[0] + 1.0 / RATE_PER_SEC - now
        if wait > 0:
            time.sleep(wait)
            now = _last[0] + 1.0 / RATE_PER_SEC
        _last[0] = now


def http_get(url: str, timeout: int = 45) -> bytes:
    """短重試、快放棄(與 s5 同一支口徑);單線程,3 請求/秒。"""
    import urllib.error
    import urllib.request
    t0 = time.time()
    for attempt in range(4):
        _throttle()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 503) and time.time() - t0 < 60:
                time.sleep(0.6 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if time.time() - t0 < 60:
                time.sleep(0.6 * (attempt + 1))
                continue
            raise
    raise RuntimeError("retries exhausted: %s" % url)


def strip_html(raw: bytes) -> str:
    t = raw.decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"(?is)<br\s*/?>", "\n", t)
    t = re.sub(r"(?is)</(p|div|tr|h[1-6]|li)>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t


def doc_url(cik: str, accn: str, doc: str) -> str:
    return "https://www.sec.gov/Archives/edgar/data/%s/%s/%s" % (
        int(cik), accn.replace("-", ""), doc)


def cached(cik: str, accn: str, doc: str, tag: str, fetch: bool = True) -> tuple[str, str]:
    """回傳 (本地檔名 或 '', 狀態)。已快取者不重抓。"""
    p = DOCS / ("%s__%s.txt.gz" % (accn.replace("-", ""), tag))
    if p.exists():
        return p.name, "已快取"
    if not fetch:
        return "", "未抓"
    try:
        txt = strip_html(http_get(doc_url(cik, accn, doc), timeout=90))
    except Exception as e:  # noqa: BLE001
        return "", "抓取失敗:%s" % type(e).__name__
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write(txt)
    return p.name, "ok"


def read_doc(fn: str) -> str:
    if not fn or fn.startswith("FAIL"):
        return ""
    try:
        return gzip.open(DOCS / fn, "rt", encoding="utf-8").read()
    except OSError:
        return ""


# ---------------------------------------------------------------- 申報索引

_ROW_CACHE: dict[str, list[dict]] = {}


SUB_EXTRA = CACHE / "peer_submissions"


def _blob_rows(blob: dict) -> list[dict]:
    # 主檔是 {"filings": {"recent": {...}}};更舊分片本身就是那個欄式物件
    r = blob.get("filings", {}).get("recent", blob) if "filings" in blob else blob
    n = len(r.get("form", []))
    return [dict(form=r["form"][i], filingDate=r["filingDate"][i],
                 reportDate=r["reportDate"][i],
                 accn=r["accessionNumber"][i], doc=r["primaryDocument"][i],
                 items=(r.get("items", [""] * n)[i] or "")) for i in range(n)]


def filing_rows(cik: str) -> list[dict]:
    """本地 submissions 的 filings.recent,新到舊;併入 s18 補抓的更舊分片(如有)。

    本地快照只存 `filings.recent`(上限約 1000 筆),申報量大的發行人窗口短,
    年報/前兩份季報會落到未下載的 `filings.files` 分片裡;分片抓到
    `cache/peer_submissions/` 後由本函式一併讀入(按 accessionNumber 去重)。
    """
    if cik in _ROW_CACHE:
        return _ROW_CACHE[cik]
    p = SUB / ("CIK%s.json" % cik)
    out: list[dict] = []
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            d = {}
        out.extend(_blob_rows(d.get("filings", {}).get("recent", {})))
        for f in d.get("filings", {}).get("files", []):
            q = SUB_EXTRA / f["name"]
            if not q.exists():
                continue
            try:
                e = json.loads(q.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            out.extend(_blob_rows(e))
    seen = set()
    uniq = []
    for x in out:
        if x["accn"] in seen:
            continue
        seen.add(x["accn"])
        uniq.append(x)
    uniq.sort(key=lambda x: x["filingDate"], reverse=True)
    _ROW_CACHE[cik] = uniq
    return uniq


def pick_filings(rows: list[dict], cutoff: str) -> dict:
    rows = [x for x in rows if x["filingDate"] <= cutoff]
    out = {}
    k = [x for x in rows if x["form"] in ("10-K", "20-F", "40-F")]
    if k:
        out["annual"] = k[0]
    for j, x in enumerate([x for x in rows if x["form"] in ("10-Q", "6-K")][:2]):
        out["q%d" % j] = x
    return out


def prior_release(rows: list[dict], cutoff: str, signal_filed: str) -> dict | None:
    """訊號季之前最近一份帶 Item 2.02 的 8-K(= 上一季業績稿)。"""
    cand = [x for x in rows if x["form"] == "8-K" and x["filingDate"] <= cutoff
            and x["filingDate"] < signal_filed and "2.02" in x["items"]]
    return cand[0] if cand else None


EPS_RX = re.compile(r"(?i)(\.htm|\.html|\.txt)$")
EX_RX = re.compile(r"(?is)<tr.*?</tr>")


def ex991_name_from_index(page: str) -> tuple[str, str]:
    """由 filing index 頁找出 EX-99.1 附件(沿用 s5_fetch_text.py 的同一條)。"""
    cands: list[tuple[str, str]] = []
    for tr in EX_RX.findall(page):
        href = re.search(r'href="([^"]+)"', tr)
        if not href:
            continue
        tds = re.findall(r"(?is)<td[^>]*>\s*([^<]*?)\s*</td>", tr)
        types = [t for t in tds if re.match(r"(?i)^EX-?9", t)]
        if types:
            cands.append((types[0].upper().replace(" ", ""), href.group(1).rsplit("/", 1)[-1]))
    ex1 = [c for c in cands if c[0] == "EX-99.1"]
    pick = ex1[0] if ex1 else (cands[0] if cands else None)
    if not pick:
        return "", ""
    return pick[1], pick[0]


def fetch_ex991(cik: str, acc: str) -> tuple[str, str]:
    """回傳 (本地檔名 或 '', 狀態)。"""
    fn = "%s__EX991.txt.gz" % acc.replace("-", "")
    p = DOCS / fn
    if p.exists():
        return fn, "已快取"
    base = "https://www.sec.gov/Archives/edgar/data/%d/%s" % (int(cik), acc.replace("-", ""))
    try:
        page = http_get(base + "/" + acc + "-index.html").decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001
        return "", "索引抓取失敗:%s" % type(e).__name__
    doc, typ = ex991_name_from_index(page)
    if not doc or not EPS_RX.search(doc):
        return "", "該申報無 EX-99 附件"
    try:
        txt = strip_html(http_get(base + "/" + doc, timeout=120))
    except Exception as e:  # noqa: BLE001
        return "", "附件抓取失敗:%s" % type(e).__name__
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write(txt)
    return fn, "ok"


# ---------------------------------------------------------------- 公司facts

_TAG_UNITS: dict[str, str] = {}


def load_facts(cik: str) -> dict | None:
    p = CF / ("CIK%s.json.gz" % cik)
    if not p.exists():
        return None
    try:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, EOFError):
        return None


def tag_rows(facts: dict, tag: str, unit: str) -> list[dict]:
    node = facts.get("facts", {}).get("us-gaap", {}).get(tag)
    if not node:
        return []
    return list(node.get("units", {}).get(unit, []))


def _first_filed(rows: list[dict], need_days: tuple | None) -> dict:
    """key → (val, filed);key 為 end(instant)或 (start,end)(duration)。"""
    best: dict = {}
    for r in rows:
        st, en, v = r.get("start"), r.get("end"), r.get("val")
        if en is None or v is None:
            continue
        if need_days is None:
            if st is not None:
                continue
            k = en
        else:
            if st is None:
                continue
            try:
                d = (date.fromisoformat(en) - date.fromisoformat(st)).days
            except ValueError:
                continue
            if not (need_days[0] <= d <= need_days[1]):
                continue
            k = (st, en)
        f = r.get("filed", "")
        if k not in best or (f and f < best[k][1]):
            best[k] = (float(v), f)
    return best


def instant_series(facts: dict, tags: list[str], unit: str = "USD") -> dict:
    """期末日 → (值, 最早申報日);同一期末多個 tag 按次序取先者。"""
    out: dict[str, tuple[float, str]] = {}
    for t in tags:
        for en, (v, f) in _first_filed(tag_rows(facts, t, unit), None).items():
            out.setdefault(en, (v, f))
    return out


def _sum_instant(facts: dict, tags_a: list[str], tags_b: list[str],
                 unit: str = "USD") -> dict:
    """兩個即時項相加(長短期借款合計);兩個都要有才算。"""
    va = instant_series(facts, tags_a, unit)
    vb = instant_series(facts, tags_b, unit)
    out = {}
    for en in set(va) & set(vb):
        out[en] = (va[en][0] + vb[en][0], max(va[en][1], vb[en][1]))
    return out


def _quarterize(facts: dict, tags: list[str], unit: str) -> dict:
    """累計值(現金流量表只報累計)→ 單季;filed 取兩個累計的較晚者。"""
    rows: dict[tuple[str, str], tuple[float, str]] = {}
    for t in tags:
        for k, (v, f) in _first_filed(tag_rows(facts, t, unit), (80, 400)).items():
            if k not in rows or (f and f < rows[k][1]):
                rows[k] = (v, f)
    by_start: dict[str, list] = {}
    for (st, en), (v, f) in rows.items():
        by_start.setdefault(st, []).append((en, v, f))
    out: dict[str, tuple[float, str]] = {}
    for _st, lst in by_start.items():
        lst.sort()
        prev = None
        for en, v, f in lst:
            if prev is None:
                out.setdefault(en, (v, f))
            else:
                out.setdefault(en, (v - prev[0], max(f, prev[1])))
            prev = (v, f)
    return out


def duration_series(facts: dict, tags: list[str], unit: str = "USD",
                    cumulative: bool = False) -> dict:
    """期末日 → (單季值, 最早申報日)。`cumulative=True` 者由累計相減。"""
    out: dict[str, tuple[float, str]] = {}
    for t in tags:
        for (_st, en), (v, f) in _first_filed(tag_rows(facts, t, unit), (80, 100)).items():
            if en not in out or (f and f < out[en][1]):
                out[en] = (v, f)
    if cumulative:
        for en, (v, f) in _quarterize(facts, tags, unit).items():
            if en not in out or (f and f < out[en][1]):
                out[en] = (v, f)
    else:                       # 損益表項目:年報期末季由「年報 − 9 個月累計」補回
        for en, (v, f) in _derive_fy(facts, tags, unit).items():
            out.setdefault(en, (v, f))
    return out


def _derive_fy(facts: dict, tags: list[str], unit: str) -> dict:
    out: dict[str, tuple[float, str]] = {}
    for t in tags:
        r9 = _first_filed(tag_rows(facts, t, unit), (255, 285))
        ytd9: dict[str, tuple] = {}
        for (st, en), (v, f) in r9.items():
            ytd9.setdefault(st, (v, f, en))
        for (st, en), (v, f) in _first_filed(tag_rows(facts, t, unit), (340, 380)).items():
            if en in out:
                continue
            hit = ytd9.get(st)
            if hit is None:
                continue
            v9, f9, end9 = hit
            try:
                gap = (date.fromisoformat(en) - date.fromisoformat(end9)).days
            except ValueError:
                continue
            if not (60 <= gap <= 130) or v - v9 <= 0:
                continue
            out[en] = (v - v9, max(f, f9))
    return out


# 十項加數:標籤、單位、形態
EXTRA_ITEMS: dict[str, dict] = {
    "inventory": dict(label="存貨", unit="USD", kind="instant", cumulative=False,
                      tags=["InventoryNet", "InventoryGross"]),
    "accounts_receivable": dict(label="應收帳", unit="USD", kind="instant", cumulative=False,
                                tags=["AccountsReceivableNetCurrent", "ReceivablesNetCurrent",
                                      "AccountsReceivableGrossCurrent"]),
    "deferred_revenue": dict(label="遞延收入(合約負債)", unit="USD", kind="instant",
                             cumulative=False,
                             tags=["ContractWithCustomerLiabilityCurrent",
                                   "ContractWithCustomerLiability",
                                   "DeferredRevenueCurrent", "DeferredRevenue"]),
    "cash_and_equivalents": dict(label="現金及等價物", unit="USD", kind="instant",
                                 cumulative=False,
                                 tags=["CashAndCashEquivalentsAtCarryingValue",
                                       "CashCashEquivalentsRestrictedCashAndRestrictedCash"
                                       "Equivalents"]),
    "total_debt": dict(label="總債務(長短期借款合計)", unit="USD", kind="instant_sum",
                       cumulative=False, tags=[]),
    "capex": dict(label="資本開支", unit="USD", kind="duration", cumulative=True,
                  tags=["PaymentsToAcquirePropertyPlantAndEquipment",
                        "PaymentsToAcquireProductiveAssets"]),
    "depreciation_amortization": dict(label="折舊攤銷", unit="USD", kind="duration",
                                      cumulative=True,
                                      tags=["DepreciationDepletionAndAmortization",
                                            "DepreciationAndAmortization",
                                            "DepreciationAmortizationAndAccretionNet"]),
    "net_income": dict(label="淨利潤", unit="USD", kind="duration", cumulative=False,
                       tags=["NetIncomeLoss", "ProfitLoss"]),
    "diluted_eps": dict(label="攤薄 EPS", unit="USD/shares", kind="duration",
                        cumulative=False, tags=["EarningsPerShareDiluted"]),
    "diluted_shares": dict(label="攤薄股數", unit="shares", kind="duration",
                           cumulative=False,
                           tags=["WeightedAverageNumberOfDilutedSharesOutstanding"]),
}

DEBT_CURRENT = ["LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent"]
DEBT_NONCURRENT = ["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations"]
DEBT_TOTAL = ["LongTermDebt"]


def extra_series(facts: dict) -> dict:
    """回傳 {item: {期末日: (值, 最早申報日)}}。"""
    out = {}
    for name, cfg in EXTRA_ITEMS.items():
        if cfg["kind"] == "instant":
            out[name] = instant_series(facts, cfg["tags"], cfg["unit"])
        elif cfg["kind"] == "instant_sum":
            s = _sum_instant(facts, DEBT_CURRENT, DEBT_NONCURRENT, cfg["unit"])
            if not s:
                s = instant_series(facts, DEBT_TOTAL, cfg["unit"])
            if not s:
                s = instant_series(facts, DEBT_NONCURRENT, cfg["unit"])
            out[name] = s
        else:
            out[name] = duration_series(facts, cfg["tags"], cfg["unit"],
                                        cumulative=cfg["cumulative"])
    return out


# ---------------------------------------------------------------- 稿內數字匹配

def _fmt_variants(v: float) -> list[str]:
    out = []
    for s in ("%.4f" % v, "%.3f" % v, "%.2f" % v, "%.1f" % v, "%.0f" % v):
        s = s.rstrip("0").rstrip(".") if "." in s else s
        if s and s not in out:
            out.append(s)
    return out


def find_num_in_text(text: str, v: float, kw: re.Pattern | None = None,
                     tol: float = 0.005) -> bool:
    """在稿內找一個等於 v(相對容差 tol)的數;`kw` 給了就要求該字眼在附近。"""
    if v is None or v == 0:
        return False
    if not text:
        return False
    for s in _fmt_variants(abs(v)):
        esc = re.escape(s)
        pat = re.compile(r"(?<![\d.,])\(?\$?\s*" + esc + r"(?![\d])")
        for m in pat.finditer(text):
            if kw is None:
                return True
            ctx = text[max(0, m.start() - 150):m.end() + 150]
            if kw.search(ctx):
                return True
    return False


EPS_CTX = re.compile(r"(?i)(per share|eps|diluted)")
SHARE_CTX = re.compile(r"(?i)(diluted|shares outstanding|weighted average)")


# ---------------------------------------------------------------- 同業

GUIDE_RX = re.compile(
    r"(?i)\b(guidance|outlook|we expect|we anticipate|we forecast|we project|"
    r"(?:financial |long-term )?targets?|full[- ]year (?:revenue|earnings|eps)|"
    r"fiscal (?:year )?20\d\d (?:revenue|earnings|eps))")
GUIDE_NOISE = re.compile(
    r"(?i)(will (?:host|hold|report|release|webcast)|expects? to (?:report|release|host)|"
    r"conference call|webcast|replay|dial[- ]in|safe harbor|forward[- ]looking|"
    r"about [A-Z][A-Za-z]+ [A-Z]|\(NYSE|\(NASDAQ|\(Nasdaq)")
"""指引句後備掃描:只在 A3 的 parse_guidance 交白卷時用,所以刻意保守 ——
要同時(一)有指引字眼、(二)句內有數字、(三)不是「幾時開業績會」一類公告句。"""


def guidance_fallback(txt: str, limit: int = 20) -> list[str]:
    sents = re.split(r"(?<=[.!?])\s+|\n(?=[A-Z])", txt)
    out, seen = [], set()
    for s in sents:
        s = re.sub(r"\s+", " ", s).strip()
        if not (12 <= len(s) <= 600) or not re.search(r"\d", s):
            continue
        if not GUIDE_RX.search(s) or GUIDE_NOISE.search(s):
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= limit:
            break
    return out


CAPEX_RX = re.compile(
    r"(?i)capital expenditure"
    r"|purchases? of property"
    r"|payments? for (?:the )?acquisition[s]? of property"
    r"|acquisition of property, plant"
    r"|additions? to property"
    r"|investment in property, plant")
"""資本開支的標準寫法。刻意不收「property and equipment, at cost」一類資產負債表字眼,
免生「摘錄到的是資產總額、不是資本開支」的假陽性。"""


def capex_excerpt(txt: str, n: int = 3) -> list[str]:
    hits = []
    for m in CAPEX_RX.finditer(txt):
        a, b = max(0, m.start() - 500), min(len(txt), m.end() + 500)
        w = re.sub(r"\s+", " ", txt[a:b]).strip()
        if re.search(r"\d", w):
            hits.append(w[:700])
        if len(hits) >= n:
            break
    return hits


def peer_universe(ent: pd.DataFrame, sic_col: str, sic_val: str, cik: str,
                  first_px: dict, t1d: pd.Timestamp) -> pd.DataFrame:
    return ent[(ent[sic_col] == sic_val) & (ent["entity_id"] != cik)
               & (ent["entity_id"].map(first_px) <= t1d)].copy()


def choose_peers(ent: pd.DataFrame, m, first_px: dict, dv_by_date, t1d) -> tuple[str, pd.DataFrame]:
    """回傳 (規則名, 同業池)。規則:同 SIC4 ≥5 → sic4;否則同 SIC3 ≥5 → sic3;否則不足。"""
    sic4 = str(m["sic"]).zfill(4)
    for col, val, name in (("sic4", sic4, "sic4"), ("sic3", sic4[:3], "sic3")):
        u = peer_universe(ent, col, val, m["cik"], first_px, t1d)
        if len(u) >= 5:
            return name, u
    return "insufficient", ent.iloc[0:0]


def top2_peers(pu: pd.DataFrame, dv_by_date, t1d) -> pd.DataFrame:
    try:
        dv_t1 = dv_by_date.loc[t1d]
    except KeyError:
        dv_t1 = pd.Series(dtype="float64")
    return pu.assign(dv=pu["entity_id"].map(dv_t1).astype("float64")
                     ).dropna(subset=["dv"]).sort_values("dv", ascending=False).head(2)
