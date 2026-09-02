"""KARST-157 步驟 3:三種分層 × 三組配對殘餘相關 + 等效獨立層數 + 與 GICS 重疊度。

嚴格照 CRITERIA.md(跑數前 commit 1c4a7b5 凍結)執行,量法照 KARST-152 凍結版。
Run: PYTHONUTF8=1 python analyze.py
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics import adjusted_mutual_info_score
from sklearn.preprocessing import normalize

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

V1 = REPO / "experiments" / "2026-09-02-narrative-layers"
ITEM1_V1 = V1 / "data" / "item1"
ITEM1_V2 = HERE / "data" / "item1"
PARQUET_OLD = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
PARQUET_NEW = HERE / "data" / "new_close.parquet"
CHAIN_CSV = REPO / "experiments" / "2026-09-02-chain-layers" / "chain_membership_v0.csv"

SLICES = ["2015-06-30", "2019-06-30", "2023-06-30"]
MANUAL_SLICES = ["2015-06-30", "2019-06-30", "2023-06-30", "2025-06-30"]
MANUAL_WINDOW = ("2022-01-01", "2026-08-31")   # KARST-152 對照窗
B_BOOT = 2000
MIN_DAYS = 200
MIN_PAIRS = 100
SEED = 20260902
RNG = np.random.default_rng(SEED)

EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_WORDS = 200
MAX_CHUNKS = 40

HDB = dict(min_cluster_size=3, max_cluster_size=25, metric="euclidean",
           cluster_selection_method="eom")

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


# ---------------- 載入 ----------------

def load_meta() -> dict[str, dict]:
    meta = json.loads((V1 / "out" / "ticker_meta.json").read_text(encoding="utf-8"))
    new_path = OUT / "ticker_meta_new.json"
    if new_path.exists():
        for t, v in json.loads(new_path.read_text(encoding="utf-8")).items():
            meta.setdefault(t, v)
    return meta


def load_prices() -> pd.DataFrame:
    px = pd.read_parquet(PARQUET_OLD)
    if PARQUET_NEW.exists():
        new = pd.read_parquet(PARQUET_NEW)
        new = new.loc[:, [c for c in new.columns if c not in px.columns]]
        px = pd.concat([px, new], axis=1).sort_index()
    return px


def window_returns(px: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    sub = px.loc[(px.index > pd.Timestamp(start)) & (px.index <= pd.Timestamp(end))]
    return sub.pct_change().iloc[1:]


def residualise(rets: pd.DataFrame, meta: dict[str, dict], stocks: list[str]) -> pd.DataFrame:
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


def build_corpus(slice_day: str, meta: dict[str, dict]) -> tuple[list[str], list[str], list[str]]:
    """回傳 (tickers, tfidf_docs, raw_docs)。兩個 item1 目錄合併,v2 優先。"""
    files: dict[str, Path] = {}
    for d in (ITEM1_V1, ITEM1_V2):
        if not d.exists():
            continue
        for p in sorted(d.glob(f"*_{slice_day}.txt.gz")):
            files[p.name.split("_")[0]] = p
    tickers, tfdocs, rawdocs = [], [], []
    for t in sorted(files):
        txt = gzip.decompress(files[t].read_bytes()).decode("utf-8").lower()
        name = ((meta.get(t) or {}).get("longName") or "") + " " + \
               ((meta.get(t) or {}).get("shortName") or "")
        drop = {w for w in TOKEN_RE.findall(name.lower())} | {t.lower()}
        toks = [w for w in TOKEN_RE.findall(txt) if w not in drop]
        tickers.append(t)
        tfdocs.append(" ".join(toks))
        rawdocs.append(txt)
    return tickers, tfdocs, rawdocs


# ---------------- 分層 ----------------

def tfidf_matrix(docs: list[str]):
    vec = TfidfVectorizer(stop_words=list(STOP), ngram_range=(1, 2), min_df=5,
                          max_df=0.5, sublinear_tf=True, max_features=20000, norm="l2")
    return vec.fit_transform(docs), vec


def reduce_svd(X, n=100):
    n = min(n, X.shape[1] - 1, max(X.shape[0] - 1, 2))
    svd = TruncatedSVD(n_components=n, random_state=SEED)
    return normalize(svd.fit_transform(X))


def hdbscan_labels(Z: np.ndarray) -> np.ndarray:
    return HDBSCAN(**HDB).fit_predict(Z)


def capped_kmeans_labels(Z: np.ndarray) -> np.ndarray:
    """預先登記的穩健性檢查:k-means 起步 + 遞迴切至 ≤25 家,<3 家丟棄(視作無層)。"""
    n = Z.shape[0]
    k0 = max(2, math.ceil(n / 12))
    base = KMeans(n_clusters=min(k0, n), random_state=SEED, n_init=10).fit_predict(Z)
    groups = [np.where(base == c)[0] for c in np.unique(base)]
    final: list[np.ndarray] = []
    queue = list(groups)
    while queue:
        g = queue.pop()
        if len(g) <= 25:
            final.append(g)
            continue
        sub = KMeans(n_clusters=2, random_state=SEED, n_init=10).fit_predict(Z[g])
        for c in (0, 1):
            part = g[sub == c]
            if len(part) == 0:          # 退化:直接硬切
                queue.append(g[:len(g) // 2]); queue.append(g[len(g) // 2:])
                break
            queue.append(part)
    labels = np.full(n, -1, dtype=np.int32)
    lid = 0
    for g in final:
        if len(g) < 3:
            continue
        labels[g] = lid
        lid += 1
    return labels


def embed(docs: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMB_MODEL)
    chunks: list[str] = []
    owner: list[int] = []
    for i, d in enumerate(docs):
        w = d.split()
        got = 0
        for s in range(0, len(w), CHUNK_WORDS):
            chunks.append(" ".join(w[s:s + CHUNK_WORDS]))
            owner.append(i)
            got += 1
            if got >= MAX_CHUNKS:
                break
        if got == 0:
            chunks.append("")
            owner.append(i)
    E = model.encode(chunks, batch_size=128, show_progress_bar=False,
                     convert_to_numpy=True, normalize_embeddings=False)
    owner = np.asarray(owner)
    out = np.zeros((len(docs), E.shape[1]), dtype=np.float32)
    for i in range(len(docs)):
        out[i] = E[owner == i].mean(axis=0)
    return normalize(out)


def top_terms_for(Xtf, vec, labels, n=10) -> dict[int, list[str]]:
    names = np.array(vec.get_feature_names_out())
    Xd = np.asarray(Xtf.todense())
    out = {}
    for c in sorted(set(int(x) for x in labels)):
        if c < 0:
            continue
        m = labels == c
        out[c] = names[np.argsort(Xd[m].mean(axis=0))[::-1][:n]].tolist()
    return out


# ---------------- 量法(照 KARST-152 凍結版) ----------------

def codes(arr: np.ndarray) -> np.ndarray:
    uniq = {v: i for i, v in enumerate(sorted(set(arr)))}
    return np.array([-1 if v == "" else uniq[v] for v in arr], dtype=np.int32)


def pair_groups(C: np.ndarray, lab: np.ndarray, sub: np.ndarray) -> dict:
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


def bootstrap_diff(C: np.ndarray, lab: np.ndarray, sub: np.ndarray) -> dict:
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


def n_eff(returns: pd.DataFrame) -> float:
    R = np.nan_to_num(returns.corr().to_numpy(), nan=0.0)
    N = R.shape[0]
    s = R.sum()
    return float(N * N / s) if s > 0 else float("nan")


def layer_n_eff(rets: pd.DataFrame, members: list[str], labels: np.ndarray) -> tuple[float | None, int]:
    lr = {}
    for c in sorted(set(int(x) for x in labels)):
        if c < 0:
            continue
        cols = [members[i] for i in range(len(members))
                if labels[i] == c and members[i] in rets.columns]
        if len(cols) >= 2:
            lr[f"L{c}"] = rets[cols].mean(axis=1)
    df = pd.DataFrame(lr).dropna(how="all")
    return (n_eff(df) if df.shape[1] >= 2 else None), int(df.shape[1])


def evaluate(name: str, members: list[str], labels: np.ndarray, C: np.ndarray,
             sub: np.ndarray, sub_names: np.ndarray, rets: pd.DataFrame,
             sector_neff: float) -> dict:
    """labels 含 -1(無層)者先剔走,再量。"""
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
        "pair_stats": stats, "bootstrap": boot,
        "ami_vs_subindustry": ami,
        "n_eff_layers": ne, "n_layers_with_returns": nl,
        "sector_etf_n_eff": sector_neff,
        "n_eff_gap": (ne - sector_neff) if (ne is not None and not math.isnan(sector_neff)) else None,
        "below_pair_threshold": bool(thin),
    }


# ---------------- 人手表 ----------------

def read_manual_rows() -> list[dict]:
    rows = []
    with open(CHAIN_CSV, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        next(reader)
        for rec in reader:
            if not rec or not rec[0].strip():
                continue
            rows.append({"theme": rec[0].strip(), "ticker": rec[1].strip().upper(),
                         "valid_from": rec[2].strip(), "valid_to": rec[3].strip()})
    return rows


def manual_labels_at(T: str) -> dict[str, str]:
    """CRITERIA 4(a):valid_from ≤ T 且 (valid_to 空白 或 valid_to ≥ T);
    valid_to < valid_from 的行永不生效。同代碼多層取 valid_from 最早、再取 theme 字母序。"""
    cut = pd.Timestamp(T)
    cand: dict[str, list[tuple[str, str]]] = {}
    for r in read_manual_rows():
        vf, vt = r["valid_from"], r["valid_to"]
        if not vf:
            continue
        vfd = pd.Timestamp(vf)
        if vt:
            vtd = pd.Timestamp(vt)
            if vtd < vfd:
                continue
            if vtd < cut:
                continue
        if vfd > cut:
            continue
        cand.setdefault(r["ticker"], []).append((vf, r["theme"]))
    return {t: sorted(v)[0][1] for t, v in cand.items()}


# ---------------- 主流程 ----------------

def main() -> int:
    meta = load_meta()
    px = load_prices()
    print(f"price panel: {px.shape[1]} cols, {px.shape[0]} rows "
          f"({px.index.min().date()}..{px.index.max().date()})", flush=True)

    results = {"criteria_commit": "1c4a7b5", "embedding_model": EMB_MODEL,
               "hdbscan_params": HDB, "slices": {}, "manual": {}, "robustness": {}}
    layer_rows: list[dict] = []

    for sl in SLICES:
        end = (pd.Timestamp(sl) + pd.Timedelta(days=365)).strftime("%Y-%m-%d")
        rets = window_returns(px, sl, end)
        etf_cols = [e for e in ETFS if e != "SPY" and e in rets.columns]
        sector_neff = n_eff(rets[etf_cols].dropna())

        tickers, tfdocs, rawdocs = build_corpus(sl, meta)
        resid = residualise(rets, meta, tickers)
        keep = [t for t in tickers if t in resid.columns and (meta.get(t) or {}).get("industry")]
        ki = [tickers.index(t) for t in keep]
        C = resid[keep].corr(min_periods=150).to_numpy()
        sub_names = np.array([(meta[t] or {}).get("industry") or "" for t in keep])
        sub = codes(sub_names)
        print(f"[{sl}] texts={len(tickers)} usable={len(keep)} days={len(resid)} "
              f"sectorNeff={sector_neff:.2f}", flush=True)

        Xtf, vec = tfidf_matrix([tfdocs[i] for i in ki])
        Z_tf = reduce_svd(Xtf)
        lab_m = hdbscan_labels(Z_tf)
        Z_em = embed([rawdocs[i] for i in ki])
        lab_s = hdbscan_labels(Z_em)

        slice_res = {
            "return_window": [sl, end], "n_days": int(len(resid)),
            "n_texts": len(tickers), "n_usable": len(keep),
            "n_subindustries": int(len(set(sub_names)) - (1 if "" in sub_names else 0)),
            "sector_etf_n_eff": sector_neff,
            "arms": {},
        }
        for name, lab in (("machine_v2", lab_m), ("semantic", lab_s)):
            slice_res["arms"][name] = evaluate(name, keep, lab, C, sub, sub_names, rets, sector_neff)
            terms = top_terms_for(Xtf, vec, lab)
            for c in sorted(terms):
                mem = [keep[i] for i in range(len(keep)) if lab[i] == c]
                sub_of = sorted({(meta[m] or {}).get("industry") or "" for m in mem})
                layer_rows.append({"arm": name, "slice": sl, "layer": c, "size": len(mem),
                                   "n_subindustries": len(sub_of),
                                   "members": " ".join(mem),
                                   "top_terms": " ".join(terms[c])})

        # 預先登記的穩健性檢查(不參與判詞)
        rob = {}
        for name, Z in (("machine_v2_kmeans", Z_tf), ("semantic_kmeans", Z_em)):
            lab = capped_kmeans_labels(Z)
            rob[name] = evaluate(name, keep, lab, C, sub, sub_names, rets, sector_neff)
        results["robustness"][sl] = rob

        results["slices"][sl] = slice_res

    # ---------------- 人手表 ----------------
    for sl in MANUAL_SLICES:
        end = (pd.Timestamp(sl) + pd.Timedelta(days=365)).strftime("%Y-%m-%d")
        labels_map = manual_labels_at(sl)
        rets = window_returns(px, sl, end)
        etf_cols = [e for e in ETFS if e != "SPY" and e in rets.columns]
        sector_neff = n_eff(rets[etf_cols].dropna()) if len(rets) else float("nan")
        if not labels_map:
            results["manual"][sl] = {"arm": "manual", "verdict_cell": "無有效行",
                                     "n_rows_in_effect": 0,
                                     "return_window": [sl, end],
                                     "sector_etf_n_eff": sector_neff}
            print(f"[manual {sl}] no rows in effect", flush=True)
            continue
        stocks = [t for t in labels_map if t in px.columns]
        resid = residualise(rets, meta, stocks)
        keep = [t for t in stocks if t in resid.columns and (meta.get(t) or {}).get("industry")]
        C = resid[keep].corr(min_periods=150).to_numpy()
        sub_names = np.array([(meta[t] or {}).get("industry") or "" for t in keep])
        sub = codes(sub_names)
        lab_names = np.array([labels_map[t] for t in keep])
        lab = codes(lab_names)
        res = evaluate("manual", keep, lab, C, sub, sub_names, rets, sector_neff)
        res.update({"return_window": [sl, end], "n_days": int(len(resid)),
                    "n_rows_in_effect": len(labels_map),
                    "n_with_prices": len(stocks), "n_usable": len(keep),
                    "missing": sorted(set(labels_map) - set(keep)),
                    "n_chain_layers_in_effect": len(set(labels_map.values()))})
        results["manual"][sl] = res
        print(f"[manual {sl}] rows={len(labels_map)} usable={len(keep)} "
              f"layers={res.get('n_layers')} G1={res['pair_stats']['G1_same_layer_diff_subind']['mean']:.3f} "
              f"G2={res['pair_stats']['G2_same_subind_diff_layer']['mean']:.3f}", flush=True)
        for c in sorted(set(int(x) for x in lab if x >= 0)):
            mem = [keep[i] for i in range(len(keep)) if lab[i] == c]
            nm = [lab_names[i] for i in range(len(keep)) if lab[i] == c][0]
            layer_rows.append({"arm": "manual", "slice": sl, "layer": nm, "size": len(mem),
                               "n_subindustries": len({(meta[m] or {}).get("industry") or "" for m in mem}),
                               "members": " ".join(mem), "top_terms": ""})

    # KARST-152 對照窗(連續窗,直接可比 A-038 那組數)
    ms, me = MANUAL_WINDOW
    labels_map = manual_labels_at(ms)
    rets = window_returns(px, ms, me)
    etf_cols = [e for e in ETFS if e != "SPY" and e in rets.columns]
    sector_neff = n_eff(rets[etf_cols].dropna())
    stocks = [t for t in labels_map if t in px.columns]
    resid = residualise(rets, meta, stocks)
    keep = [t for t in stocks if t in resid.columns and (meta.get(t) or {}).get("industry")]
    C = resid[keep].corr(min_periods=150).to_numpy()
    sub_names = np.array([(meta[t] or {}).get("industry") or "" for t in keep])
    lab_names = np.array([labels_map[t] for t in keep])
    res = evaluate("manual_continuous", keep, codes(lab_names), C, codes(sub_names),
                   sub_names, rets, sector_neff)
    res.update({"window": [ms, me], "n_rows_in_effect": len(labels_map),
                "n_with_prices": len(stocks), "n_usable": len(keep),
                "missing": sorted(set(labels_map) - set(keep))})
    results["manual"]["continuous_2022_2026"] = res
    print(f"[manual continuous] usable={len(keep)} layers={res.get('n_layers')}", flush=True)

    (OUT / "results_v2.json").write_text(json.dumps(results, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    with open(OUT / "layers_v2.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["arm", "slice", "layer", "size",
                                           "n_subindustries", "members", "top_terms"])
        w.writeheader()
        w.writerows(layer_rows)
    print("written -> out/results_v2.json, out/layers_v2.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
