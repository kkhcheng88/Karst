# -*- coding: utf-8 -*-
"""KARST-158 step 1: diagnose and repair the share-count scale errors in the
KARST-146 accounts panel, then write panel v2.

Detection is NOT invented here: it is CRITERIA 3.3' (訂正一) of KARST-156
(experiments/2026-09-02-share-shrink/CRITERIA.md), frozen before that ticket saw
any return number. Constants copied verbatim.

What this file adds -- and the reason it adds it: run on the panel column alone,
the anchor rule repairs cells it should not. CPWR is the proof: its raw share
count (22.3m) already matches the cover page to within 3%, but the split-event
table holds a 1:115 reverse split filed by a LATER user of the same ticker, so
the split-aligned series shows a three-magnitude step that the anchor reads as a
unit error. Repairing it would multiply a correct number by a thousand. So a
candidate is only acted on when a SECOND, independent channel speaks:

  cover page confirms the multiplier  -> repair by 10^k
  cover page says the raw is already right (within 5x) -> leave the cell alone
  anything else, cover page missing included -> set missing, never guess

That is 票 KARST-158 rule (2): 只以 10 的整數次方校正、判不出的格設缺值不猜.

Reads (all read-only, nothing copied -- D-134):
  fundamentals-panel/out/panel_monthly.parquet   KARST-146 panel v1  (never written)
  fundamentals-panel/data/secfacts/CIK*.json     raw companyfacts (cover-page channel)
  fourpiece-test/data/splits.parquet             KARST-148 split-event table
  stock-oracle-curve/data/stock_monthly.parquet  month-end close (mcap channel)

Writes:
  out/panel_monthly_v2.parquet   panel v1 + repaired diluted_shares (gitignored, big)
  out/scale_fixes.csv            every candidate cell: orig / fixed / multiplier / basis
  out/scale_flags_mcap.csv       cells the price*shares channel still flags in v2
  out/meta_v2.json               counts + v2 hash
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

PANEL = REPO / "experiments" / "2026-09-02-fundamentals-panel" / "out" / "panel_monthly.parquet"
SECFACTS = REPO / "experiments" / "2026-09-02-fundamentals-panel" / "data" / "secfacts"
SPLITS = REPO / "experiments" / "2026-09-02-fourpiece-test" / "data" / "splits.parquet"
MONTHLY = REPO / "experiments" / "2026-09-01-stock-oracle-curve" / "data" / "stock_monthly.parquet"

V2 = OUT / "panel_monthly_v2.parquet"

# --- KARST-156 CRITERIA 3.3' constants, copied verbatim, not re-tuned ---------
SCALE_DEV_TOL = 0.7        # under 5x from the anchor: never a candidate
SCALE_REPAIR_MIN = 1.5     # protects real corporate actions (KDP 2018 = 0.88)
SCALE_MIN_OBS = 6
POW10_TOL = 0.35           # how close to a whole power of ten counts as one
JUNK_FLOOR = 100.0
BAND = (1e5, 1e11)

# mcap outlier channel (diagnostic only, never mutates)
MCAP_BAND = (1e7, 2e13)

FORMS = {"10-K", "10-Q", "20-F", "40-F"}
COLS = ("diluted_shares", "diluted_shares_restated")


# ------------------------------------------------------------------- splits
def split_factor_fn(splits: pd.DataFrame):
    sp = {s: g[["report_date", "ratio"]].to_numpy() for s, g in splits.groupby("symbol")}

    def f(sym: str, filed) -> float:
        arr = sp.get(sym)
        if arr is None or pd.isna(filed):
            return 1.0
        out = 1.0
        for d, r in arr:
            if d > filed:
                out *= float(r)
        return out

    return f, sp


# ------------------------------------------------------- channel 1: anchor
def anchor_candidates(vals: np.ndarray):
    """CRITERIA 3.3' detection, unchanged. Returns (kind, k, dev, anchor).

    kind: '' not a candidate | 'junk' | 'pow10' | 'deviant'
    'pow10' means the deviation is 30x or more AND lands on a whole power of ten
    (the only shape this ticket is allowed to rescale); 'deviant' means it moved
    5x or more on no clean power of ten -- CRITERIA 3.3' rule 6 keeps those, they
    are real corporate actions or splits the event table is missing.
    """
    n = len(vals)
    kind = np.array([""] * n, dtype=object)
    kk = np.full(n, np.nan)
    dv = np.full(n, np.nan)
    ok = np.isfinite(vals) & (vals > 0)
    if ok.sum() < SCALE_MIN_OBS:
        return kind, kk, dv, np.nan
    anchor = float(np.median(np.log10(vals[ok])))
    for i, v in enumerate(vals):
        if not np.isfinite(v) or v <= 0:
            continue
        dev = np.log10(v) - anchor
        dv[i] = dev
        if abs(dev) < SCALE_DEV_TOL:
            continue
        if v < JUNK_FLOOR:
            kind[i] = "junk"
            continue
        k = int(round(dev))
        if k != 0 and abs(dev) >= SCALE_REPAIR_MIN and abs(dev - k) <= POW10_TOL:
            kind[i] = "pow10"
            kk[i] = k
        else:
            kind[i] = "deviant"
    return kind, kk, dv, anchor


# --------------------------------------------------- channel 2: cover page
def load_dei(cik: str) -> pd.DataFrame | None:
    p = SECFACTS / f"CIK{cik}.json"
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as fh:
        d = json.load(fh)
    node = d.get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding")
    if not node:
        return None
    units = node.get("units", {}).get("shares")
    if not units:
        return None
    rows = []
    for r in units:
        form = r.get("form", "")
        base = form[:-2] if form.endswith("/A") else form
        if base not in FORMS:
            continue
        val = r.get("val")
        if val is None or val <= 0:
            continue
        rows.append((r["end"], r["filed"], float(val), form.endswith("/A")))
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["end", "filed", "val", "amended"])
    df["end"] = pd.to_datetime(df["end"])
    df["filed"] = pd.to_datetime(df["filed"])
    df = df.sort_values(["end", "amended", "filed"]).groupby("end", as_index=False).first()
    return df[["end", "filed", "val"]].sort_values("filed").reset_index(drop=True)


def dei_at(dei: pd.DataFrame, m: pd.Timestamp) -> float:
    """Point-in-time cover-page shares: latest period end among filed <= m."""
    w = dei[dei["filed"] <= m]
    if w.empty:
        return np.nan
    return float(w.loc[w["end"].idxmax(), "val"])


# ------------------------------------------------------------------- main
def fix_column(panel: pd.DataFrame, col: str, filed_col: str, sf, dei_cache,
               cik_of) -> tuple[np.ndarray, pd.DataFrame]:
    filed = pd.to_datetime(panel[filed_col], errors="coerce")
    factor = np.array([sf(t, f) for t, f in zip(panel["ticker"], filed)])
    raw = panel[col].to_numpy(dtype=float)
    adj = raw * factor

    n = len(panel)
    kind = np.array([""] * n, dtype=object)
    kk = np.full(n, np.nan)
    dv = np.full(n, np.nan)
    an = np.full(n, np.nan)
    for _, g in panel.groupby("ticker", sort=False):
        idx = g.index.to_numpy()
        k_, kv, d_, a_ = anchor_candidates(adj[idx])
        kind[idx] = k_
        kk[idx] = kv
        dv[idx] = d_
        an[idx] = a_

    cand = np.flatnonzero(kind != "")
    cover = np.full(n, np.nan)
    for i in cand:
        t = panel["ticker"].iat[i]
        if t not in dei_cache:
            dei_cache[t] = load_dei(cik_of[t])
        d = dei_cache[t]
        if d is not None and not d.empty:
            cover[i] = dei_at(d, panel["month_end"].iat[i])
    with np.errstate(divide="ignore", invalid="ignore"):
        cratio = np.log10(raw / cover)

    # ---- adjudication ------------------------------------------------------
    action = np.array([""] * n, dtype=object)
    new = raw.copy()
    for i in cand:
        if kind[i] == "junk":                        # 3.3' rule 3
            new[i] = np.nan
            action[i] = "drop_junk"
            continue
        if kind[i] == "deviant":                     # 3.3' rule 6: hands off
            action[i] = "keep_deviant"
            continue
        c = cratio[i]
        if np.isfinite(c) and abs(c - kk[i]) <= POW10_TOL:
            new[i] = raw[i] / (10.0 ** kk[i])        # two channels, same 10^k
            action[i] = "repair"
        elif np.isfinite(c) and abs(c) < SCALE_DEV_TOL:
            action[i] = "keep_cover_agrees_raw"      # cover page says raw is fine
        else:
            new[i] = np.nan                          # 票 rule 2: 判不出,不猜
            action[i] = "drop_unresolved"

    # ---- band check on the value actually kept (3.3' rule 5) ---------------
    final_adj = new * factor
    nonpos = np.isfinite(new) & (new <= 0)
    bad = np.isfinite(final_adj) & (final_adj > 0) & ((final_adj < BAND[0])
                                                     | (final_adj > BAND[1]))
    for i in np.flatnonzero(nonpos):
        new[i] = np.nan
        action[i] = "drop_nonpositive"
    for i in np.flatnonzero(bad):
        new[i] = np.nan
        if action[i] in ("", "keep_cover_agrees_raw", "keep_deviant"):
            action[i] = "drop_band"
    touched_mask = action != ""

    def basis(i) -> str:
        a = action[i]
        if a == "drop_junk":
            return f"原值 {raw[i]:.6g} 低於 100 股,判為垃圾值,設缺值"
        if a == "drop_nonpositive":
            return f"原值 {raw[i]:.6g} 不是正數,設缺值"
        if a == "drop_band":
            return "保留值換算到今日拆股基準後不在 [1e5, 1e11] 股之內,設缺值"
        if a == "keep_deviant":
            return (f"偏離自身量級錨 {dv[i]:+.2f} 個量級,但不落在任何 10 的整數次方上——"
                    f"判為真實公司行動或事件表欠缺的拆股,照 3.3′ 第六條保留")
        if a == "keep_cover_agrees_raw":
            return (f"偏離自身量級錨 {dv[i]:+.2f} 個量級,但封面頁股數與原值相差只有 "
                    f"{cratio[i]:+.2f} 個量級——原值本身沒有刻度錯,不動")
        if a == "repair":
            return (f"偏離自身量級錨 {dv[i]:+.2f} 個量級,落在整數 {int(kk[i])} 的 "
                    f"±0.35 之內;封面頁股數比值 {cratio[i]:+.2f} 獨立印證同一個倍數")
        if np.isfinite(cratio[i]):
            return (f"偏離自身量級錨 {dv[i]:+.2f} 個量級,封面頁比值 {cratio[i]:+.2f} "
                    f"指向另一個倍數,兩條線不合,判不出,設缺值")
        return (f"偏離自身量級錨 {dv[i]:+.2f} 個量級,同期無封面頁股數可對,"
                f"只得一條線,判不出,設缺值")

    rows = pd.DataFrame({
        "column": col,
        "ticker": panel["ticker"][touched_mask].to_numpy(),
        "cik": panel["cik"][touched_mask].to_numpy(),
        "month_end": panel["month_end"][touched_mask].to_numpy(),
        "period_end": panel[col.replace("_restated", "") + "_end"][touched_mask].to_numpy(),
        "filed": filed[touched_mask].to_numpy(),
        "orig": raw[touched_mask],
        "fixed": new[touched_mask],
        "multiplier": kk[touched_mask],
        "action": action[touched_mask],
        "dev_log10": np.round(dv[touched_mask], 4),
        "anchor_log10": np.round(an[touched_mask], 4),
        "split_factor": factor[touched_mask],
        "cover_shares": cover[touched_mask],
        "cover_log10_ratio": np.round(cratio[touched_mask], 4),
        "basis": [basis(i) for i in np.flatnonzero(touched_mask)],
    })
    return new, factor, action, rows


def main() -> None:
    panel = pd.read_parquet(PANEL)
    panel["month_end"] = pd.to_datetime(panel["month_end"])
    panel = panel.sort_values(["ticker", "month_end"]).reset_index(drop=True)
    print(f"panel v1: {len(panel)} rows, {panel['ticker'].nunique()} tickers")
    src_hash = hashlib.sha256(PANEL.read_bytes()).hexdigest()

    splits = pd.read_parquet(SPLITS)
    splits["report_date"] = pd.to_datetime(splits["report_date"])
    sf, sp = split_factor_fn(splits)
    print(f"split events {len(splits)} on {splits['symbol'].nunique()} tickers")

    cik_of = panel.groupby("ticker")["cik"].first().to_dict()
    dei_cache: dict = {}

    out_cols, all_rows, counts, factors = {}, [], {}, {}
    for col in COLS:
        # the panel carries no separate filing date for the restated sibling
        # (RULES.md sec.2 promised one; the build did not emit it), so the main
        # column's filing date is used for the split basis. Stated in RULES v2.
        new, factor, action, rows = fix_column(panel, col, "diluted_shares_filed",
                                               sf, dei_cache, cik_of)
        out_cols[col] = new
        factors[col] = factor
        all_rows.append(rows)
        c = {a: int((action == a).sum()) for a in
             ("repair", "drop_junk", "drop_unresolved", "drop_band",
              "drop_nonpositive", "keep_cover_agrees_raw", "keep_deviant")}
        c["candidates"] = int((action != "").sum())
        c["nonnull_v1"] = int(np.isfinite(panel[col].to_numpy(dtype=float)).sum())
        c["nonnull_v2"] = int(np.isfinite(new).sum())
        counts[col] = c
        print(col, c)

    fixes = pd.concat(all_rows, ignore_index=True)
    fixes.to_csv(OUT / "scale_fixes.csv", index=False, encoding="utf-8-sig")

    # ---- channel 3 (diagnostic): price x shares = market cap ---------------
    monthly = pd.read_parquet(MONTHLY, columns=["symbol", "month_end", "close"])
    monthly["month_end"] = pd.to_datetime(monthly["month_end"])
    monthly = monthly.drop_duplicates(["symbol", "month_end"]).rename(
        columns={"symbol": "ticker", "close": "_px"})
    px = panel[["ticker", "month_end"]].merge(monthly, on=["ticker", "month_end"],
                                              how="left")["_px"].to_numpy(dtype=float)
    fac = factors["diluted_shares"]
    cap1 = panel["diluted_shares"].to_numpy(dtype=float) * fac * px
    cap2 = out_cols["diluted_shares"] * fac * px
    bad1 = np.isfinite(cap1) & ((cap1 < MCAP_BAND[0]) | (cap1 > MCAP_BAND[1]))
    bad2 = np.isfinite(cap2) & ((cap2 < MCAP_BAND[0]) | (cap2 > MCAP_BAND[1]))
    print(f"mcap channel outside [{MCAP_BAND[0]:.0e},{MCAP_BAND[1]:.0e}]: "
          f"v1 {int(bad1.sum())} -> v2 {int(bad2.sum())}")
    resid = panel.loc[bad2, ["ticker", "month_end", "diluted_shares"]].copy()
    resid["diluted_shares_v2"] = cap2[bad2] / (fac[bad2] * px[bad2])
    resid["mcap_v1"] = cap1[bad2]
    resid["mcap_v2"] = cap2[bad2]
    resid["split_factor"] = fac[bad2]
    resid.to_csv(OUT / "scale_flags_mcap.csv", index=False, encoding="utf-8-sig")

    # ---- write v2 ----------------------------------------------------------
    v2 = panel.copy()
    for col in COLS:
        v2[col + "_v1_raw"] = panel[col]
        v2[col] = out_cols[col]
    v2.to_parquet(V2, index=False)
    h = hashlib.sha256(V2.read_bytes()).hexdigest()

    meta = {
        "ticket": "KARST-158",
        "source_panel": "experiments/2026-09-02-fundamentals-panel/out/panel_monthly.parquet",
        "source_panel_sha256_16": src_hash[:16],
        "detection_rule": "KARST-156 CRITERIA 3.3' (訂正一),常數一字不改",
        "adjudication_rule": "封面頁 dei:EntityCommonStockSharesOutstanding 第二條線印證才校正;"
                             "封面頁反證原值正確則不動;其餘一律設缺值(不猜)",
        "constants": {"SCALE_DEV_TOL": SCALE_DEV_TOL,
                      "SCALE_REPAIR_MIN": SCALE_REPAIR_MIN,
                      "SCALE_MIN_OBS": SCALE_MIN_OBS, "POW10_TOL": POW10_TOL,
                      "JUNK_FLOOR": JUNK_FLOOR, "BAND": list(BAND)},
        "rows": int(len(v2)), "tickers": int(v2["ticker"].nunique()),
        "columns": counts,
        "mcap_channel": {"band": list(MCAP_BAND), "outside_v1": int(bad1.sum()),
                         "outside_v2": int(bad2.sum())},
        "v2_file": "experiments/2026-09-02-panel-scale-fix/out/panel_monthly_v2.parquet",
        "v2_sha256": h, "v2_sha256_16": h[:16], "v2_bytes": V2.stat().st_size,
    }
    (OUT / "meta_v2.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))

    m = fixes[fixes["column"] == "diluted_shares"]
    print("\ncandidate cells by ticker and action (top 20):")
    print(m.groupby(["ticker", "action"]).size().sort_values(ascending=False)
          .head(20).to_string())


if __name__ == "__main__":
    main()
