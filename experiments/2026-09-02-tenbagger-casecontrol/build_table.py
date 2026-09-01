# -*- coding: utf-8 -*-
"""Join price + fundamental measures into a per-pair comparison, then score each
candidate discriminator by how often the winner and loser actually differ in the
same direction.

A discriminator only earns a line in the checklist if it separates the two sides
in most of the pairs where BOTH sides have data. Pairs where either side is
missing the field are counted as `n_missing`, never imputed.

P11 (WFRD/NBR) is excluded from scoring by design - the winner has no
pre-take-off history, so it cannot inform an ex-ante checklist.

Run:  PYTHONUTF8=1 python build_table.py
"""
import pathlib
import sys

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pairs import PAIRS, CAUSE_LABEL  # noqa: E402

OUT = HERE / "out"
EXCLUDE_FROM_SCORING = {"P11"}

# metric -> (higher value expected in winner?, human label)
# `None` means we have no prior and just report which side is higher.
METRICS = [
    ("mult_hold_from_base_year_end_to_peak", None, "outcome: multiple if bought at base-year end"),
    ("revenue_growth_yoy", True, "revenue growth, latest readable FY"),
    ("revenue_accel", True, "revenue growth minus prior-year growth (acceleration)"),
    ("gross_margin", True, "gross margin level"),
    ("gross_margin_direction", True, "gross margin direction YoY"),
    ("net_income_positive", True, "profitable on net income"),
    ("cfo_positive", True, "operating cash flow positive"),
    ("dilution_yoy", False, "share count growth (lower is better)"),
    ("net_debt_over_equity", False, "net debt / equity (lower is better)"),
    ("liabilities_over_assets", False, "liabilities / assets (lower is better)"),
    ("ps_ratio", False, "price / sales at base-year end (lower is cheaper)"),
    ("market_cap_at_base_year_end", False, "market cap at base-year end (smaller base)"),
    ("revenue_latest", False, "revenue scale at base-year end (smaller base)"),
    ("rs12_vs_spy_at_base_year_end", None, "12m relative strength vs SPY"),
    ("maxdd_24m_to_base_year_end", None, "worst drawdown over prior 24m"),
]


def load():
    px = pd.read_csv(OUT / "price_measures.csv")
    fx = pd.read_csv(OUT / "fundamentals_exante.csv")
    df = px.merge(fx, on=["pid", "role", "symbol", "base_year"], how="outer",
                  suffixes=("", "_f"))
    meta = pd.DataFrame([{**p, "cause_zh": CAUSE_LABEL[p["cause"]]} for p in PAIRS])
    return df.merge(meta[["pid", "cause", "cause_zh", "industry", "base_year", "thesis"]],
                    on=["pid", "base_year"], how="left")


def add_derived(df):
    df = df.copy()
    df["revenue_accel"] = df["revenue_growth_yoy"] - df["revenue_growth_prior_yoy"]
    return df


def per_pair(df):
    rows = []
    for pid, g in df.groupby("pid"):
        w = g[g.role == "winner"].iloc[0]
        l = g[g.role == "loser"].iloc[0]
        rec = dict(pid=pid, cause=w["cause"], cause_zh=w["cause_zh"],
                   industry=w["industry"], base_year=int(w["base_year"]),
                   winner=w["symbol"], loser=l["symbol"],
                   winner_basis=w.get("data_basis"), loser_basis=l.get("data_basis"))
        for m, _, _ in METRICS:
            rec[f"W_{m}"] = w.get(m)
            rec[f"L_{m}"] = l.get(m)
        rows.append(rec)
    return pd.DataFrame(rows).sort_values("pid")


def as_num(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, str):
        if v.lower() in ("true", "false"):
            return 1.0 if v.lower() == "true" else 0.0
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(f) else f


def score(pairs_df):
    rows = []
    scored = pairs_df[~pairs_df.pid.isin(EXCLUDE_FROM_SCORING)]
    for m, expect_higher, label in METRICS:
        n_ok = n_missing = n_winner_higher = n_tie = 0
        detail = []
        for _, r in scored.iterrows():
            wv, lv = as_num(r[f"W_{m}"]), as_num(r[f"L_{m}"])
            if wv is None or lv is None:
                n_missing += 1
                detail.append(f"{r.pid}:missing")
                continue
            n_ok += 1
            if wv == lv:
                n_tie += 1
                detail.append(f"{r.pid}:tie")
            elif wv > lv:
                n_winner_higher += 1
                detail.append(f"{r.pid}:W>L")
            else:
                detail.append(f"{r.pid}:W<L")
        if expect_higher is None:
            agree = None
        else:
            agree = n_winner_higher if expect_higher else (n_ok - n_winner_higher - n_tie)
        rows.append(dict(
            metric=m, label=label,
            direction_expected=("winner higher" if expect_higher is True else
                                "winner lower" if expect_higher is False else "no prior"),
            n_pairs_with_both=n_ok, n_pairs_missing=n_missing,
            n_winner_higher=n_winner_higher, n_ties=n_tie,
            n_agreeing_with_prior=agree,
            hit_rate=None if agree is None or n_ok == 0 else round(agree / n_ok, 2),
            detail="; ".join(detail),
        ))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = add_derived(load())
    pairs_df = per_pair(df)
    pairs_df.to_csv(OUT / "comparison_by_pair.csv", index=False, encoding="utf-8")
    sc = score(pairs_df)
    sc.to_csv(OUT / "discriminator_scorecard.csv", index=False, encoding="utf-8")

    print("=== pairs (10 scored + 1 negative control) ===")
    print(pairs_df[["pid", "cause", "winner", "loser", "base_year",
                    "W_mult_hold_from_base_year_end_to_peak",
                    "L_mult_hold_from_base_year_end_to_peak"]].to_string(index=False))
    print("\n=== cause mix ===")
    print(pairs_df.cause.value_counts().to_string())
    print("\n=== discriminator scorecard (P11 excluded) ===")
    print(sc[["metric", "n_pairs_with_both", "n_pairs_missing", "n_winner_higher",
              "n_agreeing_with_prior", "hit_rate"]].to_string(index=False))
    print("\n=== detail ===")
    for _, r in sc.iterrows():
        print(f"{r.metric}: {r.detail}")
