# -*- coding: utf-8 -*-
"""KARST-175 敘事鏈層 v3 甲版補缺重跑 —— 只跑甲版。

嚴格照 CRITERIA_rerun.md(跑數前 commit 9a7add0 凍結)執行。
量法(殘差、三組配對、cluster bootstrap、運氣帶、等效獨立層數、AMI)由 analyze_v3.py
逐字搬過來,一字不改;只換價格來源(單一價格庫 + 自算調整因子)與補齊子行業/板塊。

跑法: set PYTHONUTF8=1 && python analyze_rerun.py
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_mutual_info_score

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
PXLIB = REPO / "data" / "prices" / "daily"
PXLIB_MANIFEST = PXLIB / "manifest.csv"
ETF_PANEL = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
CHAIN = REPO / "experiments" / "2026-09-02-chain-layers" / "chain_membership_v2_2.csv"
CACHE = REPO / "data" / "sec" / "10k_text"
MANIFEST = CACHE / "manifest.jsonl"
FILL = OUT / "industry_fill.csv"

SLICES = ["2015-06-30", "2019-06-30", "2023-06-30", "2025-06-30"]
CONT_WINDOW = ("2022-01-01", "2026-08-31")
B_BOOT = 2000
B_PERM = 2000
MIN_DAYS = 200
MIN_PAIRS = 100
MIN_ROSTER = 5
MAX_STALE_DAYS = 500
SEED = 20260902
SEED_V3 = 20260903
RNG = np.random.default_rng(SEED)
RNG_PERM = np.random.default_rng(SEED_V3)

SECTOR_ETF = {
    "Technology": "XLK", "Financial Services": "XLF", "Energy": "XLE",
    "Healthcare": "XLV", "Industrials": "XLI", "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP", "Utilities": "XLU", "Basic Materials": "XLB",
    "Communication Services": "XLK", "Real Estate": "XLF",
}
ETFS = ["SPY", "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]

ITEM1_START = re.compile(r"item\s*1\s*[.\-:–—]?\s*business", re.I)
ITEM1A_END = re.compile(r"item\s*1a\s*[.\-:–—]?\s*risk\s*factors", re.I)
ITEM2_END = re.compile(r"item\s*2\s*[.\-:–—]?\s*propert", re.I)
MIN_SPAN = 3000
MIN_TEXT = 2000


# ---------------- 載入:meta(補齊子行業與板塊) ----------------

def load_meta() -> tuple[dict, dict]:
    meta = json.loads((V1 / "out" / "ticker_meta.json").read_text(encoding="utf-8"))
    p = V2 / "out" / "ticker_meta_new.json"
    if p.exists():
        for t, v in json.loads(p.read_text(encoding="utf-8")).items():
            meta.setdefault(t, v)
    filled = {}
    if FILL.exists():
        with io.open(FILL, "r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r["industry"]:
                    cur = dict(meta.get(r["ticker"]) or {})
                    cur["industry"] = r["industry"]
                    if r["sector"]:
                        cur["sector"] = r["sector"]
                    cur["longName"] = cur.get("longName") or r.get("longName") or ""
                    cur["_filled_by"] = "KARST-175"
                    cur["_fetchedAt"] = r["fetchedAt"]
                    meta[r["ticker"]] = cur
                    filled[r["ticker"]] = {"industry": r["industry"], "sector": r["sector"]}
    return meta, filled


# ---------------- 載入:單一價格庫 + 自算調整因子 ----------------

def sha16(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def pick_segments(man: pd.DataFrame, tickers: list[str], win_start: str, win_end: str) -> dict:
    """CRITERIA_rerun 3.2:代號 -> 價格段(寫死次序,不看數揀)。"""
    ws, we = pd.Timestamp(win_start), pd.Timestamp(win_end)
    out = {}
    for t in tickers:
        rows = man[man["ticker"] == t]
        if rows.empty:
            continue
        cands = []
        for _, r in rows.iterrows():
            vf = pd.Timestamp(r["valid_from"])
            vt = pd.Timestamp(r["valid_to"]) if isinstance(r["valid_to"], str) and r["valid_to"] else None
            covers = (vf <= ws) and (vt is None or vt >= we)
            lo = max(vf, ws)
            hi = we if vt is None else min(vt, we)
            overlap = max(0, (hi - lo).days)
            cands.append((0 if covers else 1, -overlap,
                          0 if r["series_role"] == "primary" else 1,
                          -int(r["rows"] or 0), str(r["entity_id"]), t))
        cands.sort()
        best = cands[0]
        out[t] = best[4]
    return out


def load_price_library(tickers: list[str]) -> tuple[dict, pd.DataFrame, dict]:
    """回傳 {(ticker, entity_id): 已調整價 Series}、manifest 子集、版本記錄。"""
    man = pd.read_csv(PXLIB_MANIFEST, dtype=str)
    man["rows"] = pd.to_numeric(man["rows"], errors="coerce").fillna(0).astype(int)
    sub = man[man["ticker"].isin(tickers)].copy()
    ents = sorted(set(sub["entity_id"]))
    parts = sorted(PXLIB.glob("part_*.parquet"))
    frames = []
    for p in parts:
        df = pd.read_parquet(p, columns=["entity_id", "ticker", "date", "close", "adj_close"],
                             filters=[("entity_id", "in", ents)])
        if len(df):
            frames.append(df)
    px = pd.concat(frames, ignore_index=True)
    px = px[px["ticker"].isin(tickers)]
    px["date"] = pd.to_datetime(px["date"])

    series: dict[tuple[str, str], pd.Series] = {}
    audit_rows = []
    for (ent, tkr), g in px.groupby(["entity_id", "ticker"], sort=False):
        g = g.sort_values("date")
        close = pd.to_numeric(g["close"], errors="coerce")
        adj = pd.to_numeric(g["adj_close"], errors="coerce")
        f = adj / close.replace(0.0, np.nan)
        p_adj = close * f
        s = pd.Series(p_adj.to_numpy(), index=pd.DatetimeIndex(g["date"].to_numpy()))
        s = s[~s.index.duplicated(keep="last")].dropna()
        if len(s) == 0:
            continue
        series[(tkr, ent)] = s
        fv = f.dropna()
        audit_rows.append({
            "ticker": tkr, "entity_id": ent, "rows": int(len(s)),
            "first_date": str(s.index[0].date()), "last_date": str(s.index[-1].date()),
            "f_first": float(fv.iloc[0]) if len(fv) else float("nan"),
            "f_last": float(fv.iloc[-1]) if len(fv) else float("nan"),
            "f_min": float(fv.min()) if len(fv) else float("nan"),
            "f_max": float(fv.max()) if len(fv) else float("nan"),
        })
    with io.open(OUT / "adj_factor_audit.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["ticker", "entity_id", "rows", "first_date",
                                           "last_date", "f_first", "f_last", "f_min", "f_max"])
        w.writeheader()
        w.writerows(sorted(audit_rows, key=lambda r: r["ticker"]))

    version = {
        "library": "data/prices/daily/",
        "manifest_sha256_16": sha16(PXLIB_MANIFEST),
        "fetchedAt_min": str(sub["fetchedAt"].min()),
        "fetchedAt_max": str(sub["fetchedAt"].max()),
        "segments_for_chain_tickers": int(len(sub)),
        "tickers_found": int(sub["ticker"].nunique()),
        "tickers_requested": int(len(tickers)),
        "tickers_missing": sorted(set(tickers) - set(sub["ticker"])),
        "adjustment": "p = close * (adj_close / close);自算因子,凍結庫版本(CRITERIA_rerun 3.3)",
        "benchmark_panel": str(ETF_PANEL.relative_to(REPO)).replace("\\", "/"),
    }
    (OUT / "price_source_version.json").write_text(
        json.dumps(version, ensure_ascii=False, indent=1), encoding="utf-8")
    return series, sub, version


def build_panel(series: dict, seg: dict, etf: pd.DataFrame) -> pd.DataFrame:
    cols = {}
    for t, ent in seg.items():
        s = series.get((t, ent))
        if s is not None and len(s):
            cols[t] = s
    df = pd.DataFrame(cols)
    keep = [c for c in ETFS if c in etf.columns]
    df = pd.concat([df, etf[keep]], axis=1).sort_index()
    return df


# ---------------- 鏈表 ----------------

def read_chain() -> list[dict]:
    with io.open(CHAIN, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def roster_sizes(rows) -> dict:
    d = {}
    for r in rows:
        d.setdefault(r["theme"], set()).add(r["ticker"])
    return {k: len(v) for k, v in d.items()}


def labels_at(rows, T: str, big: set) -> dict:
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


# ---------------- 事前可得文本(只為甲版對照集,不跑乙版) ----------------

def read_manifest_by_ticker() -> dict:
    out: dict[str, list] = {}
    if not MANIFEST.exists():
        return out
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


def has_exante_text(ticker: str, T: str, man: dict) -> bool:
    for d in (ITEM1_V1, ITEM1_V2, ITEM1_OUT):
        p = d / f"{ticker}_{T}.txt.gz"
        if p.exists():
            txt = gzip.decompress(p.read_bytes()).decode("utf-8")
            return len(txt) >= MIN_TEXT
    cut = pd.Timestamp(T)
    cands = [(f, a) for f, a in man.get(ticker, []) if pd.Timestamp(f) <= cut]
    if not cands:
        return False
    f, acc = max(cands)
    if (cut - pd.Timestamp(f)).days > MAX_STALE_DAYS:
        return False
    p = CACHE / f"{ticker}_{acc}.txt.gz"
    if not p.exists():
        return False
    full = gzip.decompress(p.read_bytes()).decode("utf-8")
    item1 = extract_item1(full)
    if len(item1) < MIN_TEXT:
        return False
    (ITEM1_OUT / f"{ticker}_{T}.txt.gz").write_bytes(gzip.compress(item1.encode("utf-8")))
    return True


# ---------------- 量法(照 analyze_v3.py 逐字) ----------------

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


# ---------------- 主流程 ----------------

def slice_block(T, rows, big, meta, series, seg_man, etf, man, layer_rows, results, filled):
    end = (pd.Timestamp(T) + pd.Timedelta(days=365)).strftime("%Y-%m-%d")
    lmap = labels_at(rows, T, big)
    seg = pick_segments(seg_man, sorted(lmap.keys()), T, end)
    px = build_panel(series, seg, etf)
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
    block["n_with_prices"] = len(stocks)
    block["n_no_price_in_library"] = sorted(set(lmap) - set(stocks))
    block["n_dropped_short_window"] = sorted(set(stocks) - set(resid.columns))
    block["n_dropped_no_industry"] = sorted(t for t in stocks if t in resid.columns
                                            and not (meta.get(t) or {}).get("industry"))
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

    block["n_usable_full"] = len(keep)
    block["n_chains_full"] = int(len(set(lab_names)))
    block["n_filled_in_usable"] = int(sum(1 for t in keep if t in filled))
    block["filled_in_usable"] = sorted(t for t in keep if t in filled)
    block["missing_price_or_industry"] = sorted(set(lmap) - set(keep))
    block["arms"]["manual_v22_full"] = evaluate("manual_v22_full", keep, lab, C, sub,
                                                sub_names, rets, sector_neff)
    a = block["arms"]["manual_v22_full"]
    print(f"[{T}] 甲版(全) usable={len(keep)} chains={block['n_chains_full']} "
          f"G1={a['G1']:.4f} G2={a['G2']:.4f} diff={a['diff']:+.4f} "
          f"CI={a['bootstrap']['diff_ci95']}")

    for c in sorted(set(lab_names)):
        mem = [keep[i] for i in range(len(keep)) if lab_names[i] == c]
        layer_rows.append({"arm": "manual_v22_full", "slice": T, "layer": c, "size": len(mem),
                           "n_subindustries": len({(meta[m] or {}).get("industry") or "" for m in mem}),
                           "members": " ".join(mem)})

    # ---- 附錄:甲版(對照集)。乙版不跑,保留率不定義。 ----
    ctrl = [t for t in keep if has_exante_text(t, T, man)]
    block["n_ctrl"] = len(ctrl)
    block["ctrl_missing_text"] = sorted(set(keep) - set(ctrl))
    if len(ctrl) >= 6:
        ci = [keep.index(t) for t in ctrl]
        C_c = C[np.ix_(ci, ci)]
        sub_c = sub[ci]
        subn_c = sub_names[ci]
        labn_c = lab_names[ci]
        lab_c = codes(labn_c)
        block["n_chains_ctrl"] = int(len(set(labn_c)))
        block["arms"]["manual_v22_ctrl"] = evaluate("manual_v22_ctrl", ctrl, lab_c, C_c, sub_c,
                                                    subn_c, rets, sector_neff)
        b = block["arms"]["manual_v22_ctrl"]
        print(f"[{T}] 甲版(對照集) n={len(ctrl)} G1={b['G1']:.4f} G2={b['G2']:.4f} "
              f"diff={b['diff']:+.4f} CI={b['bootstrap']['diff_ci95']}")
    else:
        block["note_ctrl"] = "對照集少於 6 家"
    block["retention"] = "—(乙版不重跑)"
    results["slices"][T] = block


def main() -> int:
    meta, filled = load_meta()
    rows = read_chain()
    tickers = sorted({r["ticker"] for r in rows})
    series, seg_man, version = load_price_library(tickers)
    etf = pd.read_parquet(ETF_PANEL)
    etf.index = pd.to_datetime(etf.index)
    rs = roster_sizes(rows)
    big = {t for t, n in rs.items() if n >= MIN_ROSTER}
    small = sorted(set(rs) - big)
    man = read_manifest_by_ticker()

    print(f"price library: {len(series)} 段可用 / {len(tickers)} 家;"
          f"庫內取不到 {version['tickers_missing']}")
    print(f"industry 補齊 {len(filled)} 家;chains {len(rs)} (≥5 家: {len(big)}, <5 家: {len(small)})")

    results = {
        "ticket": "KARST-175",
        "criteria": "CRITERIA_rerun.md",
        "criteria_commit": "9a7add0",
        "chain_table": "chain_membership_v2_2.csv",
        "price_source": version,
        "industry_filled_n": len(filled),
        "industry_filled": sorted(filled.keys()),
        "seed_bootstrap": SEED, "seed_v3": SEED_V3,
        "themes_lt5_excluded": small,
        "arms_run": ["manual_v22_full", "manual_v22_ctrl(附錄)"],
        "arms_not_run": ["exante_A_tfidf", "exante_B_semantic"],
        "slices": {}, "continuous": {},
    }
    layer_rows: list[dict] = []

    for T in SLICES:
        slice_block(T, rows, big, meta, series, seg_man, etf, man, layer_rows, results, filled)

    # ---- 對照窗(不入判詞) ----
    ms, me = CONT_WINDOW
    for tag, fn in (("strict", labels_at), ("loose", labels_at_loose)):
        lmap = fn(rows, ms, big)
        seg = pick_segments(seg_man, sorted(lmap.keys()), ms, me)
        px = build_panel(series, seg, etf)
        rets = window_returns(px, ms, me)
        etf_cols = [e for e in ETFS if e != "SPY" and e in rets.columns]
        sector_neff = n_eff(rets[etf_cols].dropna())
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
        print(f"[cont {tag}] usable={len(keep)} layers={res.get('n_layers')} "
              f"diff={res.get('diff'):+.4f} CI={res['bootstrap']['diff_ci95']}")

    (OUT / "results_rerun.json").write_text(json.dumps(results, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    with io.open(OUT / "layers_rerun.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["arm", "slice", "layer", "size",
                                           "n_subindustries", "members"])
        w.writeheader()
        w.writerows(layer_rows)

    lines = ["KARST-175 附錄:逐個名單", ""]
    lines.append(f"價格庫內完全取不到的代號({len(version['tickers_missing'])}):"
                 + " ".join(version["tickers_missing"]))
    lines.append(f"本票補回 industry 的公司({len(filled)}):" + " ".join(sorted(filled)))
    lines.append("")
    lines.append("名冊不足五家、整條不入判準的鏈:" + " ".join(small))
    for T, b in results["slices"].items():
        if "n_usable_full" not in b:
            lines.append(f"\n[{T}] {b.get('note', '無有效行')}")
            continue
        lines.append(f"\n[{T}] 定格 {b['n_rows_in_effect']} 家 → 有價 {b['n_with_prices']} → "
                     f"可入數 {b['n_usable_full']}(其中本票補回子行業 {b['n_filled_in_usable']} 家)")
        lines.append("  庫內無價:" + " ".join(b["n_no_price_in_library"]))
        lines.append("  有價但回報日數不足 200 天而剔:" + " ".join(b["n_dropped_short_window"]))
        lines.append("  有價但仍無子行業:" + " ".join(b["n_dropped_no_industry"]))
        lines.append("  本票補回子行業而入數者:" + " ".join(b["filled_in_usable"]))
        lines.append(f"  有價有子行業但無事前文本(不入對照集,{len(b.get('ctrl_missing_text', []))}):"
                     + " ".join(b.get("ctrl_missing_text", [])))
    (OUT / "appendix_rerun.txt").write_text("\n".join(lines), encoding="utf-8")
    print("written -> out/results_rerun.json, out/layers_rerun.csv, out/appendix_rerun.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
