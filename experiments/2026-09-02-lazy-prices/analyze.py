"""KARST-153 步驟 2:年報文字改動 -> 五分位 -> 三臂 -> 四基準。

一切照 CRITERIA.md(commit d4b8ad2,跑數前凍結)。本檔不改判準,只執行。

Run: PYTHONUTF8=1 python analyze.py
"""
from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SEC_DIR = DATA / "sections"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

PARQUET = Path(r"C:\projects\Karst\experiments\2026-09-02-timing-sweep\data\daily_close.parquet")
ETFS = {"SPY", "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"}

# ---- CRITERIA 凍結參數 ----
PAIR_MIN_DAYS, PAIR_MAX_DAYS = 270, 500
STALE_DAYS = 366
N_QUANTILES = 5
MIN_POOL = 25            # 不足 25 家的月份跳過
COSTS_BP = [0, 15, 25, 50]
SAMPLE_FROM = pd.Timestamp("2009-01-01")
SAMPLE_TO = pd.Timestamp("2026-08-31")
SEG1 = (pd.Timestamp("2009-01-01"), pd.Timestamp("2016-12-31"))
SEG2 = (pd.Timestamp("2017-01-01"), pd.Timestamp("2026-08-31"))
LUCK_DRAWS = 1000
SEED = 20260902
# 量不出門檻
MIN_COVERAGE_FRAC = 0.40
MIN_MONTHS = 60
MIN_MEDIAN_POOL = 50

TOKEN_RE = re.compile(r"[a-z]{2,}")
STOP = frozenset(ENGLISH_STOP_WORDS)


def tokenize(text: str) -> list[str]:
    return [w for w in TOKEN_RE.findall(text.lower()) if w not in STOP]


def load_tokens(ticker: str, acc: str, sec: str) -> list[str] | None:
    p = SEC_DIR / f"{ticker}_{acc}_{sec}.txt.gz"
    if not p.exists():
        return None
    return tokenize(gzip.decompress(p.read_bytes()).decode("utf-8", "replace"))


def cosine_tfidf(a: list[str], b: list[str]) -> float:
    v = TfidfVectorizer(analyzer=lambda x: x, lowercase=False)
    m = v.fit_transform([a, b])
    return float((m[0] @ m[1].T).toarray()[0, 0])


def jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    u = len(sa | sb)
    return float(len(sa & sb) / u) if u else float("nan")


# ---------------------------------------------------------------- 第一步:改動分數
def build_changes() -> pd.DataFrame:
    man = json.loads((OUT / "filing_manifest.json").read_text(encoding="utf-8"))
    rows = [v for v in man.values() if v.get("ok")]
    df = pd.DataFrame(rows)
    df["filingDate"] = pd.to_datetime(df["filingDate"])
    df = df.sort_values(["ticker", "filingDate"]).reset_index(drop=True)

    recs = []
    for ticker, g in df.groupby("ticker", sort=True):
        g = g.reset_index(drop=True)
        cache: dict[tuple[str, str], list[str] | None] = {}

        def tok(acc: str, sec: str):
            k = (acc, sec)
            if k not in cache:
                cache[k] = load_tokens(ticker, acc, sec)
            return cache[k]

        for i in range(1, len(g)):
            cur, prv = g.loc[i], g.loc[i - 1]
            gap = (cur["filingDate"] - prv["filingDate"]).days
            if not (PAIR_MIN_DAYS <= gap <= PAIR_MAX_DAYS):
                continue
            rec = {"ticker": ticker, "filingDate": cur["filingDate"], "gap": gap,
                   "acc": cur["acc"], "prev_acc": prv["acc"]}
            any_sec = False
            for sec in ("mdna", "risk"):
                ta, tb = tok(cur["acc"], sec), tok(prv["acc"], sec)
                if ta is None or tb is None or not ta or not tb:
                    continue
                any_sec = True
                rec[f"cos_{sec}"] = 1.0 - cosine_tfidf(ta, tb)
                rec[f"jac_{sec}"] = 1.0 - jaccard(ta, tb)
            if any_sec:
                recs.append(rec)

    ch = pd.DataFrame(recs)
    for m in ("cos", "jac"):
        cols = [c for c in (f"{m}_mdna", f"{m}_risk") if c in ch.columns]
        ch[f"chg_{m}"] = ch[cols].mean(axis=1, skipna=True)
    return ch


# ---------------------------------------------------------------- 第二步:月度面板
def month_grid(px: pd.DataFrame):
    """回傳 [(rank_date, trade_date)],rank=月最後交易日,trade=下一個交易日。"""
    idx = px.index
    last = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).last()
    pos = {d: i for i, d in enumerate(idx)}
    out = []
    for rd in last:
        i = pos[rd]
        if i + 1 < len(idx):
            out.append((rd, idx[i + 1]))
    return out


def eligible(ch: pd.DataFrame, rd: pd.Timestamp) -> pd.DataFrame:
    sub = ch[(ch["filingDate"] <= rd) &
             ((rd - ch["filingDate"]).dt.days <= STALE_DAYS)]
    if sub.empty:
        return sub
    # 用 tail(1) 而不是 last():last() 逐欄取最後一個非空值,會把兩份不同年報的
    # 分數混在同一行。
    return sub.sort_values("filingDate").groupby("ticker", as_index=False).tail(1)


def leg_return(names, r_map) -> tuple[float, list[str]]:
    vals, keep = [], []
    for n in names:
        v = r_map.get(n)
        if v is not None and np.isfinite(v):
            vals.append(v)
            keep.append(n)
    if not vals:
        return float("nan"), []
    return float(np.mean(vals)), keep


def turnover(prev_w: dict, new_names: list[str]) -> tuple[float, dict]:
    new_w = {n: 1.0 / len(new_names) for n in new_names} if new_names else {}
    keys = set(prev_w) | set(new_w)
    tau = 0.5 * sum(abs(new_w.get(k, 0.0) - prev_w.get(k, 0.0)) for k in keys)
    return tau, new_w


def drift(w: dict, r_map: dict) -> dict:
    if not w:
        return {}
    g = {k: v * (1.0 + r_map.get(k, 0.0)) for k, v in w.items()
         if np.isfinite(r_map.get(k, np.nan))}
    s = sum(g.values())
    return {k: v / s for k, v in g.items()} if s > 0 else {}


def run_backtest(ch: pd.DataFrame, px: pd.DataFrame, metric: str, tag: str):
    grid = month_grid(px)
    rng = np.random.default_rng(SEED)
    rows, luck_rows = [], []
    w_q1: dict = {}
    w_q5: dict = {}
    w_pool: dict = {}

    for k in range(len(grid) - 1):
        rd, td = grid[k]
        td_next = grid[k + 1][1]
        if rd < SAMPLE_FROM or rd > SAMPLE_TO:
            continue
        el = eligible(ch, rd)
        el = el[el[metric].notna()]
        el = el[el["ticker"].isin(px.columns)]
        if len(el) < MIN_POOL:
            continue
        p0, p1 = px.loc[td], px.loc[td_next]
        r = (p1 / p0 - 1.0)
        r_map = {t: r[t] for t in el["ticker"] if np.isfinite(r.get(t, np.nan))}
        el = el[el["ticker"].isin(r_map)]
        if len(el) < MIN_POOL:
            continue

        q = pd.qcut(el[metric].rank(method="first"), N_QUANTILES, labels=False) + 1
        el = el.assign(q=q.values)
        q1 = el.loc[el["q"] == 1, "ticker"].tolist()
        q5 = el.loc[el["q"] == N_QUANTILES, "ticker"].tolist()
        pool = el["ticker"].tolist()

        r_q1, _ = leg_return(q1, r_map)
        r_q5, _ = leg_return(q5, r_map)
        r_pool, _ = leg_return(pool, r_map)

        t_q1, w_q1_new = turnover(w_q1, q1)
        t_q5, w_q5_new = turnover(w_q5, q5)
        t_pool, w_pool_new = turnover(w_pool, pool)
        w_q1 = drift(w_q1_new, r_map)
        w_q5 = drift(w_q5_new, r_map)
        w_pool = drift(w_pool_new, r_map)

        # 運氣帶:同池、同隻數、同月換
        pool_r = np.array([r_map[t] for t in pool])
        n1 = len(q1)
        draws = np.array([pool_r[rng.choice(len(pool_r), n1, replace=False)].mean()
                          for _ in range(LUCK_DRAWS)])
        luck_rows.append(draws)

        rows.append({
            "rank_date": rd, "trade_date": td, "n_pool": len(pool), "n_q1": n1,
            "n_q5": len(q5), "r_q1": r_q1, "r_q5": r_q5, "r_pool": r_pool,
            "ls": r_q1 - r_q5, "to_q1": t_q1, "to_q5": t_q5, "to_pool": t_pool,
            "spy": float(px.loc[td_next, "SPY"] / px.loc[td, "SPY"] - 1),
            "xlk": float(px.loc[td_next, "XLK"] / px.loc[td, "XLK"] - 1),
        })

    res = pd.DataFrame(rows)
    luck = np.array(luck_rows) if luck_rows else np.zeros((0, LUCK_DRAWS))
    res.to_csv(OUT / f"monthly_{tag}.csv", index=False)
    np.save(OUT / f"luck_{tag}.npy", luck)
    return res, luck


# ---------------------------------------------------------------- 第三步:統計
def stats(x: pd.Series) -> dict:
    x = x.dropna()
    n = len(x)
    if n < 2:
        return {"n": n, "mean_m": float("nan"), "t": float("nan"), "ann": float("nan")}
    m, s = float(x.mean()), float(x.std(ddof=1))
    return {"n": n, "mean_m": m, "t": m / (s / np.sqrt(n)) if s > 0 else float("nan"),
            "ann": (1 + m) ** 12 - 1}


def net(res: pd.DataFrame, col: str, to_col: str, bp: float) -> pd.Series:
    return res[col] - 2.0 * (bp / 10000.0) * res[to_col]


def summarize(res: pd.DataFrame, luck: np.ndarray, tag: str) -> dict:
    out: dict = {"tag": tag, "months": len(res),
                 "pool_median": float(res["n_pool"].median()),
                 "first": str(res["rank_date"].min().date()),
                 "last": str(res["rank_date"].max().date())}
    seg = {"full": res,
           "seg1": res[(res.rank_date >= SEG1[0]) & (res.rank_date <= SEG1[1])],
           "seg2": res[(res.rank_date >= SEG2[0]) & (res.rank_date <= SEG2[1])]}
    for sname, sdf in seg.items():
        for bp in COSTS_BP:
            ls = net(sdf, "r_q1", "to_q1", bp) - net(sdf, "r_q5", "to_q5", bp)
            out[f"{sname}|ls|{bp}bp"] = stats(ls)
            out[f"{sname}|q1|{bp}bp"] = stats(net(sdf, "r_q1", "to_q1", bp))
            out[f"{sname}|q5|{bp}bp"] = stats(net(sdf, "r_q5", "to_q5", bp))
            out[f"{sname}|pool|{bp}bp"] = stats(net(sdf, "r_pool", "to_pool", bp))
        out[f"{sname}|spy|0bp"] = stats(sdf["spy"])
        out[f"{sname}|xlk|0bp"] = stats(sdf["xlk"])
        # 只做多 Q1 對基準的差額(15bp 淨,基準零成本)
        q1n = net(sdf, "r_q1", "to_q1", 15)
        out[f"{sname}|q1_vs_spy|15bp"] = stats(q1n - sdf["spy"])
        out[f"{sname}|q1_vs_xlk|15bp"] = stats(q1n - sdf["xlk"])
        out[f"{sname}|q1_vs_pool|15bp"] = stats(q1n - net(sdf, "r_pool", "to_pool", 15))
    if luck.size:
        mask = ((res.rank_date >= SAMPLE_FROM) & (res.rank_date <= SAMPLE_TO)).values
        lm = luck[mask].mean(axis=0)
        out["luck_band_5_95_monthly"] = [float(np.percentile(lm, 5)),
                                         float(np.percentile(lm, 95))]
        out["luck_median_monthly"] = float(np.median(lm))
        out["q1_mean_monthly_0bp"] = float(res["r_q1"].mean())
        out["q1_pctile_in_luck"] = float((lm < res["r_q1"].mean()).mean() * 100)
    return out


def main() -> int:
    px = pd.read_parquet(PARQUET)

    cache = OUT / "changes.parquet"
    if cache.exists():
        ch = pd.read_parquet(cache)
    else:
        ch = build_changes()
        ch.to_parquet(cache)
    print(f"pairs: {len(ch)}; tickers with >=1 pair: {ch.ticker.nunique()}", flush=True)

    universe = sorted(c for c in px.columns if c not in ETFS)
    man = json.loads((OUT / "filing_manifest.json").read_text(encoding="utf-8"))
    covered = sorted({v["ticker"] for v in man.values() if v.get("ok")})
    missing = json.loads((OUT / "missing_tickers.json").read_text(encoding="utf-8"))
    meta = {
        "universe_n": len(universe),
        "tickers_with_any_filing_text": len(covered),
        "tickers_with_any_pair": int(ch.ticker.nunique()),
        "coverage_frac": len(covered) / len(universe),
        "filings_fetched": len(man),
        "filings_with_section": sum(1 for v in man.values() if v.get("ok")),
        "filings_mdna_ok": sum(1 for v in man.values() if v.get("mdna_chars", 0) > 0),
        "filings_risk_ok": sum(1 for v in man.values() if v.get("risk_chars", 0) > 0),
        "pairs": len(ch),
        "pairs_both_sections": int(ch[["cos_mdna", "cos_risk"]].notna().all(axis=1).sum()),
        "missing_tickers": missing,
        "tickers_no_pair": sorted(set(universe) - set(ch.ticker.unique())),
    }
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    print(json.dumps({k: v for k, v in meta.items()
                      if k not in ("missing_tickers", "tickers_no_pair")}, indent=1))

    summaries = {}
    for metric, tag in (("chg_cos", "cos"), ("chg_jac", "jac"),
                        ("cos_mdna", "cos_mdna"), ("cos_risk", "cos_risk"),
                        ("jac_mdna", "jac_mdna"), ("jac_risk", "jac_risk")):
        if metric not in ch.columns:
            continue
        res, luck = run_backtest(ch, px, metric, tag)
        if res.empty:
            print(f"{tag}: no months", flush=True)
            continue
        summaries[tag] = summarize(res, luck, tag)
        s = summaries[tag]
        f = s["full|ls|0bp"]
        print(f"{tag}: months={s['months']} pool_med={s['pool_median']:.0f} "
              f"LS0bp mean={f['mean_m']*100:.3f}%/m t={f['t']:.2f} ann={f['ann']*100:.2f}%",
              flush=True)

    (OUT / "summary.json").write_text(
        json.dumps({"meta": meta | {"missing_tickers": len(missing)},
                    "summaries": summaries}, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
