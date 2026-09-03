# -*- coding: utf-8 -*-
"""KARST-170 敘事鏈層存在性 v3 —— 甲版(事後表)與乙版(受控表)並量。

嚴格照 CRITERIA.md(跑數前 commit ef08ef0 凍結)執行。
量法(殘差、三組配對、cluster bootstrap、等效獨立層數、AMI)照 KARST-157 analyze.py 逐字搬過來。

跑法: set PYTHONUTF8=1 && python analyze_v3.py
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics import adjusted_mutual_info_score
from sklearn.preprocessing import normalize

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
DATA = HERE / "data"
ITEM1_OUT = DATA / "item1"
for d in (OUT, ITEM1_OUT):
    d.mkdir(parents=True, exist_ok=True)

V1 = REPO / "experiments" / "2026-09-02-narrative-layers"
V2 = REPO / "experiments" / "2026-09-02-narrative-layers-v2"
ITEM1_V1 = V1 / "data" / "item1"
ITEM1_V2 = V2 / "data" / "item1"
PX_OLD = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
PX_NEW = V2 / "data" / "new_close.parquet"
CHAIN = REPO / "experiments" / "2026-09-02-chain-layers" / "chain_membership_v2_2.csv"
CACHE = REPO / "data" / "sec" / "10k_text"
MANIFEST = CACHE / "manifest.jsonl"

SLICES = ["2015-06-30", "2019-06-30", "2023-06-30", "2025-06-30"]
MAIN_SLICES = ["2023-06-30", "2025-06-30"]
CONT_WINDOW = ("2022-01-01", "2026-08-31")
B_BOOT = 2000
B_PERM = 2000
MIN_DAYS = 200
MIN_PAIRS = 100
MIN_ROSTER = 5
MAX_STALE_DAYS = 500
SEED = 20260902          # cluster bootstrap 照 v2 一字不改
SEED_V3 = 20260903       # 本票新增部分(SVD、隨機重貼標籤)
RNG = np.random.default_rng(SEED)
RNG_PERM = np.random.default_rng(SEED_V3)

EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_WORDS = 200
MAX_CHUNKS = 40

SECTOR_ETF = {
    "Technology": "XLK", "Financial Services": "XLF", "Energy": "XLE",
    "Healthcare": "XLV", "Industrials": "XLI", "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP", "Utilities": "XLU", "Basic Materials": "XLB",
    "Communication Services": "XLK", "Real Estate": "XLF",
}
ETFS = ["SPY", "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]

BOILER = """item items business company companies fiscal annual report reports form
sec securities exchange commission common stock shares shareholders shareholder
subsidiaries subsidiary approximately including include included includes may will
million billion thousand year years ended december january february march april june
july august september october november inc corp corporation llc ltd plc lp co
also based including addition addition new use used using united states u.s us
our we their its it he she they operations operating operate operates products
services service customers customer markets market business segment segments
information additional certain such other others including well within under over
per net total end first second third fourth quarter""".split()
STOP = set(ENGLISH_STOP_WORDS) | set(BOILER)
TOKEN_RE = re.compile(r"[a-z][a-z\-]{2,}")

ITEM1_START = re.compile(r"item\s*1\s*[.\-:–—]?\s*business", re.I)
ITEM1A_END = re.compile(r"item\s*1a\s*[.\-:–—]?\s*risk\s*factors", re.I)
ITEM2_END = re.compile(r"item\s*2\s*[.\-:–—]?\s*propert", re.I)
MIN_SPAN = 3000
MIN_TEXT = 2000


# ---------------- 載入 ----------------

def load_meta() -> dict:
    meta = json.loads((V1 / "out" / "ticker_meta.json").read_text(encoding="utf-8"))
    p = V2 / "out" / "ticker_meta_new.json"
    if p.exists():
        for t, v in json.loads(p.read_text(encoding="utf-8")).items():
            meta.setdefault(t, v)
    return meta


def load_prices() -> pd.DataFrame:
    px = pd.read_parquet(PX_OLD)
    new = pd.read_parquet(PX_NEW)
    new = new.loc[:, [c for c in new.columns if c not in px.columns]]
    return pd.concat([px, new], axis=1).sort_index()


def read_chain() -> list[dict]:
    with io.open(CHAIN, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def roster_sizes(rows) -> dict:
    d = {}
    for r in rows:
        d.setdefault(r["theme"], set()).add(r["ticker"])
    return {k: len(v) for k, v in d.items()}


def labels_at(rows, T: str, big: set) -> dict:
    """CRITERIA 1.2/1.3:定格 + 近似規則 + 名冊 ≥5。同代碼多層取 valid_from 最早、再 theme 字母序。"""
    cut = pd.Timestamp(T)
    cand: dict[str, list] = {}
    for r in rows:
        if r["theme"] not in big:
            continue
        vf, vt = r["valid_from"].strip(), r["valid_to"].strip()
        if not vf:
            continue
        vfd = pd.Timestamp(vf)
        if vt:
            vtd = pd.Timestamp(vt)
            if vtd < vfd or vtd < cut:
                continue
        if vfd > cut:
            continue
        if ("近似" in (r.get("valid_from_basis") or "")) and cut < pd.Timestamp("2023-01-01"):
            continue
        cand.setdefault(r["ticker"], []).append((vf, r["theme"]))
    return {t: sorted(v)[0][1] for t, v in cand.items()}


def labels_at_loose(rows, T: str, big: set) -> dict:
    """對照窗寬鬆版:同上但不套用近似規則。"""
    cut = pd.Timestamp(T)
    cand: dict[str, list] = {}
    for r in rows:
        if r["theme"] not in big:
            continue
        vf, vt = r["valid_from"].strip(), r["valid_to"].strip()
        if not vf:
            continue
        vfd = pd.Timestamp(vf)
        if vt:
            vtd = pd.Timestamp(vt)
            if vtd < vfd or vtd < cut:
                continue
        if vfd > cut:
            continue
        cand.setdefault(r["ticker"], []).append((vf, r["theme"]))
    return {t: sorted(v)[0][1] for t, v in cand.items()}


# ---------------- 事前可得文本 ----------------

def read_manifest_by_ticker() -> dict:
    out: dict[str, list] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        out.setdefault(rec["ticker"], []).append((rec["filingDate"], rec["accession"]))
    return out


def extract_item1(text: str) -> str:
    starts = [m.start() for m in ITEM1_START.finditer(text)]
    if not starts:
        return ""
    for end_re in (ITEM1A_END, ITEM2_END):
        ends = [m.start() for m in end_re.finditer(text)]
        spans = []
        for s in starts:
            e = [x for x in ends if x > s + MIN_SPAN]
            if e:
                spans.append((s, e[0]))
        ok = [sp for sp in spans if sp[1] - sp[0] >= MIN_SPAN]
        if ok:
            s, e = min(ok, key=lambda sp: sp[1] - sp[0])
            return text[s:e]
    return ""


def exante_text(ticker: str, T: str, man: dict) -> str | None:
    """切片日之前最新一份 10-K 的 Item 1;先讀已有的切節衍生物,再由共用快取切。"""
    for d in (ITEM1_V1, ITEM1_V2, ITEM1_OUT):
        p = d / f"{ticker}_{T}.txt.gz"
        if p.exists():
            txt = gzip.decompress(p.read_bytes()).decode("utf-8")
            return txt if len(txt) >= MIN_TEXT else None
    cut = pd.Timestamp(T)
    cands = [(f, a) for f, a in man.get(ticker, []) if pd.Timestamp(f) <= cut]
    if not cands:
        return None
    f, acc = max(cands)
    if (cut - pd.Timestamp(f)).days > MAX_STALE_DAYS:
        return None
    p = CACHE / f"{ticker}_{acc}.txt.gz"
    if not p.exists():
        return None
    full = gzip.decompress(p.read_bytes()).decode("utf-8")
    item1 = extract_item1(full)
    if len(item1) < MIN_TEXT:
        return None
    (ITEM1_OUT / f"{ticker}_{T}.txt.gz").write_bytes(gzip.compress(item1.encode("utf-8")))
    return item1


# ---------------- 量法(照 KARST-157 逐字) ----------------

def window_returns(px: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    sub = px.loc[(px.index > pd.Timestamp(start)) & (px.index <= pd.Timestamp(end))]
    return sub.pct_change().iloc[1:]


def residualise(rets: pd.DataFrame, meta: dict, stocks: list[str]) -> pd.DataFrame:
    out = {}
    spy = rets["SPY"]
    for t in stocks:
        if t not in rets.columns:
            continue
        y = rets[t]
        etf = SECTOR_ETF.get((meta.get(t) or {}).get("sector") or "", None)
        cols = [spy] if (etf is None or etf not in rets.columns) else [spy, rets[etf]]
        X = pd.concat(cols, axis=1)
        d = pd.concat([y, X], axis=1).dropna()
        if len(d) < MIN_DAYS:
            continue
        yv = d.iloc[:, 0].to_numpy()
        Xv = np.column_stack([np.ones(len(d)), d.iloc[:, 1:].to_numpy()])
        beta, *_ = np.linalg.lstsq(Xv, yv, rcond=None)
        out[t] = pd.Series(yv - Xv @ beta, index=d.index)
    return pd.DataFrame(out)


def codes(arr: np.ndarray) -> np.ndarray:
    uniq = {v: i for i, v in enumerate(sorted(set(arr)))}
    return np.array([-1 if v == "" else uniq[v] for v in arr], dtype=np.int32)


def pair_groups(C, lab, sub) -> dict:
    n = len(lab)
    iu = np.triu_indices(n, 1)
    c = C[iu]
    same_l = lab[iu[0]] == lab[iu[1]]
    same_s = (sub[iu[0]] == sub[iu[1]]) & (sub[iu[0]] >= 0)
    ok = ~np.isnan(c)
    res = {}
    for name, m in (("G1_same_layer_diff_subind", same_l & ~same_s),
                    ("G2_same_subind_diff_layer", ~same_l & same_s),
                    ("G3_same_layer_same_subind", same_l & same_s),
                    ("G0_neither", ~same_l & ~same_s)):
        mm = m & ok
        res[name] = {"n_pairs": int(mm.sum()),
                     "mean": float(np.nanmean(c[mm])) if mm.sum() else float("nan")}
    return res


def bootstrap_diff(C, lab, sub) -> dict:
    layers = np.unique(lab)
    idx_by_layer = {L: np.where(lab == L)[0] for L in layers}
    diffs, g1s, g2s = [], [], []
    for _ in range(B_BOOT):
        drawn = RNG.choice(layers, size=len(layers), replace=True)
        idx, copy = [], []
        for ci, L in enumerate(drawn):
            members = idx_by_layer[L]
            idx.append(members)
            copy.append(np.full(len(members), ci))
        idx = np.concatenate(idx)
        copy = np.concatenate(copy).astype(np.int32)
        sm = C[np.ix_(idx, idx)]
        n = len(idx)
        li, si = lab[idx], sub[idx]
        same_l = li[:, None] == li[None, :]
        same_c = copy[:, None] == copy[None, :]
        same_s = (si[:, None] == si[None, :]) & (si[:, None] >= 0)
        valid = ~np.isnan(sm) & ~np.eye(n, dtype=bool) & ~(same_l & ~same_c)
        m1 = valid & same_l & ~same_s
        m2 = valid & ~same_l & same_s
        if m1.sum() < 20 or m2.sum() < 20:
            continue
        a, b = float(sm[m1].mean()), float(sm[m2].mean())
        g1s.append(a); g2s.append(b); diffs.append(a - b)
    d = np.array(diffs)
    return {
        "B_used": len(d),
        "diff_mean": float(d.mean()) if len(d) else float("nan"),
        "diff_ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))] if len(d) else None,
        "G1_ci95": [float(np.percentile(g1s, 2.5)), float(np.percentile(g1s, 97.5))] if g1s else None,
        "G2_ci95": [float(np.percentile(g2s, 2.5)), float(np.percentile(g2s, 97.5))] if g2s else None,
    }


def permutation_band(C, lab, sub, observed) -> dict:
    """CRITERIA 5.2:同一批公司、同一個相關矩陣,只打亂邊家屬邊層(層大小分佈不變)。"""
    vals = []
    lab = np.asarray(lab)
    for _ in range(B_PERM):
        p = RNG_PERM.permutation(len(lab))
        st = pair_groups(C, lab[p], sub)
        g1 = st["G1_same_layer_diff_subind"]["mean"]
        g2 = st["G2_same_subind_diff_layer"]["mean"]
        if math.isnan(g1) or math.isnan(g2):
            continue
        vals.append(g1 - g2)
    v = np.array(vals)
    if not len(v):
        return {"B_used": 0}
    return {"B_used": int(len(v)),
            "null_mean": float(v.mean()),
            "band95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))],
            "observed_percentile": float((v < observed).mean() * 100.0)}


def n_eff(returns: pd.DataFrame) -> float:
    R = np.nan_to_num(returns.corr().to_numpy(), nan=0.0)
    N = R.shape[0]
    s = R.sum()
    return float(N * N / s) if s > 0 else float("nan")


def layer_n_eff(rets, members, labels):
    lr = {}
    for c in sorted(set(int(x) for x in labels)):
        if c < 0:
            continue
        cols = [members[i] for i in range(len(members)) if labels[i] == c and members[i] in rets.columns]
        if len(cols) >= 2:
            lr[f"L{c}"] = rets[cols].mean(axis=1)
    df = pd.DataFrame(lr).dropna(how="all")
    return (n_eff(df) if df.shape[1] >= 2 else None), int(df.shape[1])


def evaluate(name, members, labels, C, sub, sub_names, rets, sector_neff) -> dict:
    m = labels >= 0
    idx = np.where(m)[0]
    if len(idx) < 6 or len(set(labels[m])) < 2:
        return {"arm": name, "verdict_cell": "量不出", "why": "層數或成員太少",
                "n_labelled": int(m.sum()), "n_layers": int(len(set(labels[m])))}
    lab2 = labels[idx].astype(np.int32)
    sub2 = sub[idx]
    C2 = C[np.ix_(idx, idx)]
    mem2 = [members[i] for i in idx]
    stats = pair_groups(C2, lab2, sub2)
    boot = bootstrap_diff(C2, lab2, sub2)
    g1 = stats["G1_same_layer_diff_subind"]["mean"]
    g2 = stats["G2_same_subind_diff_layer"]["mean"]
    perm = permutation_band(C2, lab2, sub2, g1 - g2)
    ne, nl = layer_n_eff(rets, mem2, lab2)
    sizes = [int((lab2 == c).sum()) for c in sorted(set(lab2))]
    ami = float(adjusted_mutual_info_score(sub_names[idx], lab2))
    thin = (stats["G1_same_layer_diff_subind"]["n_pairs"] < MIN_PAIRS or
            stats["G2_same_subind_diff_layer"]["n_pairs"] < MIN_PAIRS)
    return {
        "arm": name,
        "n_labelled": int(m.sum()), "n_unlabelled": int((~m).sum()),
        "coverage": float(m.mean()),
        "n_layers": len(sizes), "layer_sizes": sizes,
        "largest_layer": max(sizes), "median_layer": float(np.median(sizes)),
        "pair_stats": stats,
        "G1": g1, "G2": g2, "diff": g1 - g2,
        "resolution_multiple": (g1 / g2) if (g2 and not math.isnan(g2) and g2 != 0) else None,
        "bootstrap": boot, "permutation": perm,
        "ami_vs_subindustry": ami,
        "n_eff_layers": ne, "n_layers_with_returns": nl,
        "sector_etf_n_eff": sector_neff,
        "n_eff_gap": (ne - sector_neff) if (ne is not None and not math.isnan(sector_neff)) else None,
        "below_pair_threshold": bool(thin),
    }


# ---------------- 乙版分組 ----------------

def tfidf_labels(docs: list[str], meta: dict, tickers: list[str], k: int) -> np.ndarray:
    toks = []
    for t, txt in zip(tickers, docs):
        name = ((meta.get(t) or {}).get("longName") or "") + " " + ((meta.get(t) or {}).get("shortName") or "")
        drop = {w for w in TOKEN_RE.findall(name.lower())} | {t.lower()}
        toks.append(" ".join(w for w in TOKEN_RE.findall(txt.lower()) if w not in drop))
    vec = TfidfVectorizer(stop_words=list(STOP), ngram_range=(1, 2), min_df=5,
                          max_df=0.5, sublinear_tf=True, max_features=20000, norm="l2")
    X = vec.fit_transform(toks)
    n = min(100, X.shape[1] - 1, max(X.shape[0] - 1, 2))
    Z = normalize(TruncatedSVD(n_components=n, random_state=SEED_V3).fit_transform(X))
    lab = AgglomerativeClustering(n_clusters=k, metric="cosine", linkage="average").fit_predict(Z)
    return lab.astype(np.int32), X, vec


def embed(docs: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMB_MODEL)
    chunks, owner = [], []
    for i, d in enumerate(docs):
        w = d.split()
        got = 0
        for s in range(0, len(w), CHUNK_WORDS):
            chunks.append(" ".join(w[s:s + CHUNK_WORDS])); owner.append(i); got += 1
            if got >= MAX_CHUNKS:
                break
        if got == 0:
            chunks.append(""); owner.append(i)
    E = model.encode(chunks, batch_size=128, show_progress_bar=False,
                     convert_to_numpy=True, normalize_embeddings=False)
    owner = np.asarray(owner)
    out = np.zeros((len(docs), E.shape[1]), dtype=np.float32)
    for i in range(len(docs)):
        out[i] = E[owner == i].mean(axis=0)
    return normalize(out)


def semantic_labels(docs: list[str], k: int) -> np.ndarray:
    Z = embed(docs)
    return AgglomerativeClustering(n_clusters=k, metric="cosine", linkage="average").fit_predict(Z).astype(np.int32)


def top_terms_for(X, vec, labels, n=10) -> dict:
    names = np.array(vec.get_feature_names_out())
    Xd = np.asarray(X.todense())
    out = {}
    for c in sorted(set(int(x) for x in labels)):
        if c < 0:
            continue
        out[c] = names[np.argsort(Xd[labels == c].mean(axis=0))[::-1][:n]].tolist()
    return out


# ---------------- 主流程 ----------------

def slice_block(T, rows, big, meta, px, man, layer_rows, results):
    end = (pd.Timestamp(T) + pd.Timedelta(days=365)).strftime("%Y-%m-%d")
    lmap = labels_at(rows, T, big)
    rets = window_returns(px, T, end)
    etf_cols = [e for e in ETFS if e != "SPY" and e in rets.columns]
    sector_neff = n_eff(rets[etf_cols].dropna()) if len(rets) else float("nan")

    block = {"return_window": [T, end], "n_rows_in_effect": len(lmap),
             "sector_etf_n_eff": sector_neff, "arms": {}}
    if not lmap:
        block["note"] = "無有效行"
        results["slices"][T] = block
        print(f"[{T}] 無有效行")
        return

    stocks = [t for t in lmap if t in px.columns]
    resid = residualise(rets, meta, stocks)
    keep = [t for t in stocks if t in resid.columns and (meta.get(t) or {}).get("industry")]
    if len(keep) < 6:
        block["note"] = "可入數成員少於 6 家"
        results["slices"][T] = block
        print(f"[{T}] 可入數 {len(keep)} 家,太少")
        return
    C = resid[keep].corr(min_periods=150).to_numpy()
    sub_names = np.array([(meta[t] or {}).get("industry") or "" for t in keep])
    sub = codes(sub_names)
    lab_names = np.array([lmap[t] for t in keep])
    lab = codes(lab_names)

    block["n_with_prices"] = len(stocks)
    block["n_usable_full"] = len(keep)
    block["n_chains_full"] = int(len(set(lab_names)))
    block["missing_price_or_industry"] = sorted(set(lmap) - set(keep))
    block["arms"]["manual_v22_full"] = evaluate("manual_v22_full", keep, lab, C, sub,
                                                sub_names, rets, sector_neff)
    print(f"[{T}] 甲版(全) usable={len(keep)} chains={block['n_chains_full']} "
          f"G1={block['arms']['manual_v22_full']['G1']:.3f} G2={block['arms']['manual_v22_full']['G2']:.3f}")

    for c in sorted(set(lab_names)):
        mem = [keep[i] for i in range(len(keep)) if lab_names[i] == c]
        layer_rows.append({"arm": "manual_v22_full", "slice": T, "layer": c, "size": len(mem),
                           "n_subindustries": len({(meta[m] or {}).get("industry") or "" for m in mem}),
                           "members": " ".join(mem), "top_terms": ""})

    # ---- 對照集:再交叉「有事前可得年報文本」 ----
    texts = {}
    for t in keep:
        tx = exante_text(t, T, man)
        if tx:
            texts[t] = tx
    ctrl = [t for t in keep if t in texts]
    block["n_ctrl"] = len(ctrl)
    block["ctrl_missing_text"] = sorted(set(keep) - set(ctrl))
    if len(ctrl) < 6:
        block["note_ctrl"] = "對照集少於 6 家,乙版跳過"
        results["slices"][T] = block
        return

    ci = [keep.index(t) for t in ctrl]
    C_c = C[np.ix_(ci, ci)]
    sub_c = sub[ci]
    subn_c = sub_names[ci]
    labn_c = lab_names[ci]
    lab_c = codes(labn_c)
    K = int(len(set(labn_c)))
    block["n_chains_ctrl"] = K
    block["arms"]["manual_v22_ctrl"] = evaluate("manual_v22_ctrl", ctrl, lab_c, C_c, sub_c,
                                                subn_c, rets, sector_neff)
    print(f"[{T}] 甲版(對照集) n={len(ctrl)} K={K} "
          f"G1={block['arms']['manual_v22_ctrl']['G1']:.3f} G2={block['arms']['manual_v22_ctrl']['G2']:.3f}")

    docs = [texts[t] for t in ctrl]
    lab_a, Xtf, vec = tfidf_labels(docs, meta, ctrl, K)
    block["arms"]["exante_A_tfidf"] = evaluate("exante_A_tfidf", ctrl, lab_a, C_c, sub_c,
                                               subn_c, rets, sector_neff)
    lab_b = semantic_labels(docs, K)
    block["arms"]["exante_B_semantic"] = evaluate("exante_B_semantic", ctrl, lab_b, C_c, sub_c,
                                                  subn_c, rets, sector_neff)
    print(f"[{T}] 乙-A diff={block['arms']['exante_A_tfidf']['diff']:+.3f} "
          f"乙-B diff={block['arms']['exante_B_semantic']['diff']:+.3f}")

    terms_a = top_terms_for(Xtf, vec, lab_a)
    for name, lb in (("exante_A_tfidf", lab_a), ("exante_B_semantic", lab_b)):
        for c in sorted(set(int(x) for x in lb)):
            mem = [ctrl[i] for i in range(len(ctrl)) if lb[i] == c]
            layer_rows.append({"arm": name, "slice": T, "layer": c, "size": len(mem),
                               "n_subindustries": len({(meta[m] or {}).get("industry") or "" for m in mem}),
                               "members": " ".join(mem),
                               "top_terms": " ".join(terms_a.get(c, [])) if name.startswith("exante_A") else ""})

    base = block["arms"]["manual_v22_ctrl"]["diff"]
    ret = {}
    for k2, arm in (("exante_A_tfidf", "exante_A_tfidf"), ("exante_B_semantic", "exante_B_semantic")):
        d = block["arms"][arm]["diff"]
        ret[k2] = (d / base) if (base and base > 0) else None
    ret["primary"] = max([v for v in ret.values() if v is not None], default=None)
    ret["base_diff"] = base
    block["retention"] = ret
    print(f"[{T}] 保留率 A={ret['exante_A_tfidf']} B={ret['exante_B_semantic']} 主={ret['primary']}")

    results["slices"][T] = block


def main() -> int:
    meta = load_meta()
    px = load_prices()
    rows = read_chain()
    rs = roster_sizes(rows)
    big = {t for t, n in rs.items() if n >= MIN_ROSTER}
    small = sorted(set(rs) - big)
    man = read_manifest_by_ticker()

    print(f"price panel: {px.shape[1]} cols; chains {len(rs)} (≥5 家: {len(big)}, <5 家: {len(small)})")

    results = {"criteria_commit": "ef08ef0", "chain_table": "chain_membership_v2_2.csv",
               "embedding_model": EMB_MODEL, "seed_bootstrap": SEED, "seed_v3": SEED_V3,
               "themes_lt5_excluded": small, "slices": {}, "continuous": {}}
    layer_rows: list[dict] = []

    for T in SLICES:
        slice_block(T, rows, big, meta, px, man, layer_rows, results)

    # ---- 對照窗(不入判詞) ----
    ms, me = CONT_WINDOW
    rets = window_returns(px, ms, me)
    etf_cols = [e for e in ETFS if e != "SPY" and e in rets.columns]
    sector_neff = n_eff(rets[etf_cols].dropna())
    for tag, fn in (("strict", labels_at), ("loose", labels_at_loose)):
        lmap = fn(rows, ms, big)
        stocks = [t for t in lmap if t in px.columns]
        if len(stocks) < 6:
            results["continuous"][tag] = {"note": "有效成員太少", "n_rows_in_effect": len(lmap)}
            continue
        resid = residualise(rets, meta, stocks)
        keep = [t for t in stocks if t in resid.columns and (meta.get(t) or {}).get("industry")]
        if len(keep) < 6:
            results["continuous"][tag] = {"note": "可入數太少", "n_usable": len(keep)}
            continue
        C = resid[keep].corr(min_periods=150).to_numpy()
        subn = np.array([(meta[t] or {}).get("industry") or "" for t in keep])
        labn = np.array([lmap[t] for t in keep])
        res = evaluate(f"manual_v22_cont_{tag}", keep, codes(labn), C, codes(subn),
                       subn, rets, sector_neff)
        res.update({"window": [ms, me], "n_rows_in_effect": len(lmap), "n_usable": len(keep)})
        results["continuous"][tag] = res
        print(f"[cont {tag}] usable={len(keep)} layers={res.get('n_layers')} diff={res.get('diff')}")

    (OUT / "results_v3.json").write_text(json.dumps(results, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    with io.open(OUT / "layers_v3.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["arm", "slice", "layer", "size", "n_subindustries",
                                           "members", "top_terms"])
        w.writeheader()
        w.writerows(layer_rows)
    print("written -> out/results_v3.json, out/layers_v3.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
