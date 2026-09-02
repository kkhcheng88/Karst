"""KARST-152 步驟 2:機器分層 + 殘餘相關主判數 + 事後診斷。

嚴格照 CRITERIA.md(已於跑數前 commit 0aa236d 凍結)執行。
Run: PYTHONUTF8=1 python analyze.py
"""
from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics import adjusted_mutual_info_score

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
TEXTS = DATA / "item1"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

PARQUET = Path(r"C:\projects\Karst\experiments\2026-09-02-timing-sweep\data\daily_close.parquet")
CHAIN_CSV = Path(r"C:\projects\Karst\experiments\2026-09-02-chain-layers\chain_membership_v0.csv")

SLICES = ["2015-06-30", "2019-06-30", "2023-06-30"]
KS = [40, 60, 80]
B_BOOT = 2000
MIN_DAYS = 200
RNG = np.random.default_rng(20260902)

SECTOR_ETF = {
    "Technology": "XLK", "Financial Services": "XLF", "Energy": "XLE",
    "Healthcare": "XLV", "Industrials": "XLI", "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP", "Utilities": "XLU", "Basic Materials": "XLB",
    # XLC(2018)與 XLRE(2015)不在日線檔內;用拆分前的歷史歸屬,見 CRITERIA.md 第 1 節
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


def load_meta() -> dict[str, dict]:
    return json.loads((OUT / "ticker_meta.json").read_text(encoding="utf-8"))


def load_prices() -> pd.DataFrame:
    return pd.read_parquet(PARQUET)


def window_returns(px: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    sub = px.loc[(px.index > pd.Timestamp(start)) & (px.index <= pd.Timestamp(end))]
    return sub.pct_change().iloc[1:]


def residualise(rets: pd.DataFrame, meta: dict[str, dict], stocks: list[str]) -> pd.DataFrame:
    """對 SPY 與所屬板塊 ETF 回歸,取殘差。"""
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


def build_corpus(slice_day: str, meta: dict[str, dict]) -> tuple[list[str], list[str]]:
    tickers, docs = [], []
    for p in sorted(TEXTS.glob(f"*_{slice_day}.txt.gz")):
        t = p.name.split("_")[0]
        txt = gzip.decompress(p.read_bytes()).decode("utf-8").lower()
        name = ((meta.get(t) or {}).get("longName") or "") + " " + \
               ((meta.get(t) or {}).get("shortName") or "")
        drop = {w for w in TOKEN_RE.findall(name.lower())} | {t.lower()}
        toks = [w for w in TOKEN_RE.findall(txt) if w not in drop]
        tickers.append(t)
        docs.append(" ".join(toks))
    return tickers, docs


def cluster(docs: list[str], k: int):
    vec = TfidfVectorizer(stop_words=list(STOP), ngram_range=(1, 2), min_df=5,
                          max_df=0.5, sublinear_tf=True, max_features=20000, norm="l2")
    X = vec.fit_transform(docs)
    model = AgglomerativeClustering(n_clusters=k, metric="cosine", linkage="average")
    labels = model.fit_predict(np.asarray(X.todense()))
    return labels, X, vec


def top_terms(X, vec, labels, k: int, n: int = 10) -> dict[int, list[str]]:
    names = np.array(vec.get_feature_names_out())
    Xd = np.asarray(X.todense())
    out = {}
    for c in range(k):
        m = labels == c
        if m.sum() == 0:
            out[c] = []
            continue
        mean = Xd[m].mean(axis=0)
        out[c] = names[np.argsort(mean)[::-1][:n]].tolist()
    return out


def codes(arr: np.ndarray) -> np.ndarray:
    """字串標籤轉整數碼(空字串 -> -1,永不與任何標籤相等)。"""
    uniq = {v: i for i, v in enumerate(sorted(set(arr)))}
    return np.array([-1 if v == "" else uniq[v] for v in arr], dtype=np.int32)


def pair_groups(C: np.ndarray, lab: np.ndarray, sub: np.ndarray) -> dict:
    n = len(lab)
    iu = np.triu_indices(n, 1)
    c = C[iu]
    same_l = (lab[iu[0]] == lab[iu[1]])
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


def bootstrap_diff(C: np.ndarray, lab: np.ndarray, sub: np.ndarray, k: int) -> dict:
    """以敘事層為抽樣單位的 cluster bootstrap(CRITERIA.md 第 7 節)。"""
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
        # 剔走對角線,以及同層不同副本的假配對
        valid = ~np.isnan(sm) & ~np.eye(n, dtype=bool) & ~(same_l & ~same_c)
        m1 = valid & same_l & ~same_s
        m2 = valid & ~same_l & same_s
        if m1.sum() < 20 or m2.sum() < 20:
            continue
        a, b = float(sm[m1].mean()), float(sm[m2].mean())
        g1s.append(a)
        g2s.append(b)
        diffs.append(a - b)
    d = np.array(diffs)
    return {
        "B_used": len(d),
        "diff_mean": float(d.mean()) if len(d) else float("nan"),
        "diff_ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))] if len(d) else None,
        "G1_ci95": [float(np.percentile(g1s, 2.5)), float(np.percentile(g1s, 97.5))] if g1s else None,
        "G2_ci95": [float(np.percentile(g2s, 2.5)), float(np.percentile(g2s, 97.5))] if g2s else None,
    }


def n_eff(returns: pd.DataFrame) -> float:
    """等效獨立數 = N^2 / sum(相關矩陣元素)(D-131,事後診斷)。"""
    R = returns.corr().to_numpy()
    R = np.nan_to_num(R, nan=0.0)
    N = R.shape[0]
    s = R.sum()
    return float(N * N / s) if s > 0 else float("nan")


def main() -> int:
    meta = load_meta()
    px = load_prices()
    results = {"slices": {}, "manual_table": {}, "n_eff": {}}
    layer_dump = []

    for sl in SLICES:
        tickers, docs = build_corpus(sl, meta)
        end = (pd.Timestamp(sl) + pd.Timedelta(days=365)).strftime("%Y-%m-%d")
        rets = window_returns(px, sl, end)
        resid = residualise(rets, meta, tickers)
        keep = [t for t in tickers if t in resid.columns and
                (meta.get(t) or {}).get("industry")]
        docs_k = [docs[tickers.index(t)] for t in keep]
        C = resid[keep].corr(min_periods=150).to_numpy()
        sub_names = np.array([(meta[t] or {}).get("industry") or "" for t in keep])
        sub = codes(sub_names)
        print(f"[{sl}] texts={len(tickers)} usable={len(keep)} days={len(resid)}", flush=True)

        slice_res = {"n_texts": len(tickers), "n_usable": len(keep),
                     "return_window": [sl, end], "n_days": int(len(resid)),
                     "n_subindustries": int(len(set(sub_names)) - (1 if "" in sub_names else 0)),
                     "k": {}}
        for k in KS:
            labels, X, vec = cluster(docs_k, k)
            terms = top_terms(X, vec, labels, k)
            stats = pair_groups(C, labels.astype(np.int32), sub)
            boot = bootstrap_diff(C, labels.astype(np.int32), sub, k)
            ami = float(adjusted_mutual_info_score(sub_names, labels))
            sizes = np.bincount(labels, minlength=k).tolist()
            # 事後診斷:層等權日回報的等效獨立層數
            layer_rets = {}
            for c in range(k):
                mem = [keep[i] for i in range(len(keep)) if labels[i] == c]
                cols = [m for m in mem if m in rets.columns]
                if len(cols) >= 2:
                    layer_rets[f"L{c}"] = rets[cols].mean(axis=1)
            lr = pd.DataFrame(layer_rets).dropna(how="all")
            slice_res["k"][str(k)] = {
                "pair_stats": stats, "bootstrap": boot, "ami_vs_subindustry": ami,
                "layer_sizes": sizes, "singleton_layers": int(sum(1 for s in sizes if s == 1)),
                "largest_layer": int(max(sizes)),
                "n_eff_layers_posthoc": n_eff(lr) if lr.shape[1] >= 2 else None,
                "n_layers_with_returns": int(lr.shape[1]),
            }
            for c in range(k):
                mem = [keep[i] for i in range(len(keep)) if labels[i] == c]
                layer_dump.append({"slice": sl, "k": k, "layer": c, "size": len(mem),
                                   "members": mem, "top_terms": terms[c]})
        results["slices"][sl] = slice_res

        # 板塊層對照(同一窗)
        etf_cols = [e for e in ETFS if e != "SPY" and e in rets.columns]
        results["n_eff"][sl] = {"sector_etf_n_eff": n_eff(rets[etf_cols].dropna()),
                                "n_sector_etfs": len(etf_cols)}

    # ---- 人手表對照 ----
    # 人手表的 note 欄有未加引號的逗號(舊倉手寫),pandas 直讀會炸;
    # 前五欄(theme/ticker/valid_from/valid_to/role)一定無逗號,故按首五個逗號手動切。
    themes: dict[str, str] = {}
    lines = CHAIN_CSV.read_text(encoding="utf-8-sig").splitlines()
    for ln in lines[1:]:
        if not ln.strip():
            continue
        parts = ln.split(",", 5)
        if len(parts) < 5:
            continue
        theme, ticker, _vfrom, vto = parts[0], parts[1], parts[2], parts[3]
        if vto.strip():
            continue          # 已退役代表,不計
        themes.setdefault(ticker.strip(), theme.strip())
    mstart, mend = "2022-01-01", "2026-08-31"
    mrets = window_returns(px, mstart, mend)
    mstocks = [t for t in themes if t in px.columns]
    mres = residualise(mrets, meta, mstocks)
    mkeep = [t for t in mstocks if t in mres.columns and (meta.get(t) or {}).get("industry")]
    MC = mres[mkeep].corr(min_periods=150).to_numpy()
    mlab_names = np.array([themes[t] for t in mkeep])
    msub_names = np.array([(meta[t] or {}).get("industry") or "" for t in mkeep])
    mlab = codes(mlab_names)
    msub = codes(msub_names)
    mstats = pair_groups(MC, mlab, msub)
    mboot = bootstrap_diff(MC, mlab, msub, len(set(mlab)))
    theme_rets = {}
    for th in sorted(set(mlab_names)):
        cols = [mkeep[i] for i in range(len(mkeep))
                if mlab_names[i] == th and mkeep[i] in mrets.columns]
        if len(cols) >= 2:
            theme_rets[th] = mrets[cols].mean(axis=1)
    tr = pd.DataFrame(theme_rets).dropna(how="all")
    etf_cols = [e for e in ETFS if e != "SPY" and e in mrets.columns]
    results["manual_table"] = {
        "window": [mstart, mend],
        "n_reps_in_csv": int(len(themes)), "n_usable": len(mkeep),
        "n_chain_layers": int(len(set(mlab_names))),
        "n_subindustries": int(len(set(msub_names)) - (1 if "" in msub_names else 0)),
        "pair_stats": mstats, "bootstrap": mboot,
        "ami_vs_subindustry": float(adjusted_mutual_info_score(msub_names, mlab_names)),
        "n_eff_chain_posthoc": n_eff(tr) if tr.shape[1] >= 2 else None,
        "n_chain_layers_with_returns": int(tr.shape[1]),
        "sector_etf_n_eff_same_window": n_eff(mrets[etf_cols].dropna()),
        "missing_reps": sorted(set(themes) - set(mkeep)),
    }

    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    (OUT / "layers.json").write_text(json.dumps(layer_dump, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    print("written -> out/results.json, out/layers.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
