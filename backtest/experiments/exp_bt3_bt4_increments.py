"""BT-3 / BT-4: single-mechanism increments inside the Karst-AA structure.

Motivation (Fable handover P2-11)
----------------------------------
BT-2 (`exp_bt2_aa_structure.py` / `backtest/results/2026-07-12_bt2_aa_vs_core.md`)
already proved the AA-strict all-active STRUCTURE matches-or-beats core-v2 and SPY
B&H on a risk-adjusted basis. But BT-2's delta-ledger bundles TWO mechanisms into
one number:
  (1) the regime->band table: LEAP delta-notional target = 1.15 (0 legs gated
      off) / 0.925 (1 off) / 0.0 (both off) -- design doc section 2.2.
  (2) a breadth-washout one-time +5% NAV-delta LEAP boost, 21 trading days,
      reverting after -- design doc section 3 point 4
      (`docs/2026-07-12_all_active_design_response.md` line 164-165).
Neither component's OWN increment was ever isolated. This script does exactly
that, one mechanism at a time (increment-testing discipline -- see memory
`validation-mirror-and-increment`: test the A/B increment, nothing else).

Machine-check result on (2): grepping `exp_bt2_aa_structure.py` for "washout"
finds exactly ONE hit -- the "Next" pointer at the very end of the file. The
washout boost was NEVER implemented in BT-2's `simulate_aa`. So BT-4 below is a
genuinely NEW mechanism added on top of BT-2's engine (not a toggle on existing
code), while BT-3 ablates something that already exists (the regime band).

BT-3  AA-strict FULL (regime band) vs AA-strict with the band LOCKED at 1.15
      always (regime determination stripped out, "其他一切不變").
BT-4  AA-strict FULL (as BT-2 built it -- NO washout boost, confirmed above) vs
      AA-strict WITH the design doc's washout boost added.

Scope: STRICT variant only, band=1.15 headline (BT-2's own recommended cell --
see its Conclusion #2 "Prefer AA-strict over AA-pragmatic"). This is the cell a
migration decision would actually use; re-running the full pragmatic x3-band
grid is BT-2's job, already done. FULL window only (no H1/H2 split) plus a
compact stress-year check -- a narrower ablation than BT-2's own structural
test, disclosed under Caveats.

Import discipline (what is REUSED vs NEW)
------------------------------------------
REUSED VERBATIM (imported, not reimplemented):
  - the data pipeline: `exp_core_topup` (M) for `load`/`build_underlying`/
    `build_gates`/`simulate_unit_path`/`damp_iv`/`month_start_mask`/
    `two_sided_p_from_t`; `exp_ballast_parking.build_core_only`/`DEFENSIVE`/
    `COST_SIDE` for the XLP/XLU/XLV trio -- the SAME imports BT-2 itself uses.
  - `exp_bt2_aa_structure` (BT2): `rolling_beta`, `nav_metrics`,
    `worst_roll_return`, `_p`/`_a` formatters, and its CONSTANTS (CAPITAL,
    IV_MULT, DAMP, COST_OPT, COST_ETF, TD, DELTA, T_NOM, LEAP_CAP, BAND_1,
    BAND_2, BAND_OPEN_BASE). `rolling_beta` is called with BT2's own default
    window/min_periods (252/60) -- not re-declared as local constants here.
  - **BT2.simulate_aa itself, UNMODIFIED, called directly** -- this IS the
    "AA-strict full version" arm in both BT-3 and BT-4 (zero duplication risk
    for the baseline any ablation is measured against).
  - `metrics` module (`jensen_alpha`, `deflated_sharpe_ratio` not used here --
    see Caveats) for the paired-increment significance test.
  - `exp_breadth_reversion.build_breadth` + `exp_breadth_reversion_verify.
    episodes` for the washout signal (the SAME functions BT-B
    `exp_bt_b_washout_expr.py` used for its FINE granularity -- not re-derived).
  - `exp_bt2_aa_structure.py` is NOT modified.

NEW code (the only new logic in this file):
  1. `simulate_aa_ext` -- a documented copy of BT2.simulate_aa with exactly TWO
     seams added: `band_mode` ("regime"=BT-2 original table / "locked"=always
     band_open) and `washout_active`/`washout_boost` (adds a flat NAV-delta
     boost to `leap_dn` on ledger bars where the signal is active). This copy
     is UNAVOIDABLE -- Python has no clean way to inject a one-line change into
     an existing function without copying it -- so its fidelity is PROVEN, not
     assumed: with band_mode="regime" and washout_active=None it is asserted to
     reproduce BT2.simulate_aa's NAV path bit-for-bit on identical inputs
     (see "Equivalence self-check" below) before any ablation number is trusted.
  2. the washout-signal builder (episode -> 21-trading-day active window).
  3. `build_common()` -- re-assembles the SAME data pipeline BT2.main() builds
     (same functions, same order) so betas/gates/unit-paths are IDENTICAL to
     BT-2's own run; this is orchestration glue, not new financial logic.

Run:  PYTHONUTF8=1 python backtest/experiments/exp_bt3_bt4_increments.py
Writes: backtest/results/2026-07-13_bt3_bt4_increments.md
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import metrics                                              # noqa: E402
import exp_core_topup as M                                  # noqa: E402
from exp_ballast_parking import build_core_only, DEFENSIVE   # noqa: E402
import exp_bt2_aa_structure as BT2                           # noqa: E402
from exp_breadth_reversion import build_breadth              # noqa: E402
from exp_breadth_reversion_verify import episodes            # noqa: E402

# ---- constants reused verbatim from BT-2 -----------------------------------
CAPITAL = BT2.CAPITAL
IV_MULT = BT2.IV_MULT
DAMP = BT2.DAMP
COST_OPT = BT2.COST_OPT
COST_ETF = BT2.COST_ETF
TD = BT2.TD
DELTA = BT2.DELTA
T_NOM = BT2.T_NOM
LEAP_CAP = BT2.LEAP_CAP
BAND_1 = BT2.BAND_1
BAND_2 = BT2.BAND_2
BAND_OPEN_BASE = BT2.BAND_OPEN_BASE
VARIANT = "strict"          # BT-2's recommended winner -- see its Conclusion #2

# ---- NEW constants for this study -------------------------------------------
WASHOUT_QUANTILE = 0.10      # bottom-decile %above50 -- design doc's own threshold
WASHOUT_GAP_TD = 20          # episode-dedup gap (matches BT-B FINE / source doc episodes())
WASHOUT_HOLD_TD = 21         # "21 個交易日後歸位" -- design doc section 3 point 4
WASHOUT_BOOST = 0.05         # "+5% NAV delta" -- design doc section 3 point 4

BONF_N_PRIOR = 48            # BT-2's own registry (42 prior + its 6 new trials)
BONF_N = BONF_N_PRIOR + 2    # + this study's 2 new candidate arms (locked-band, boosted)
BONF_ALPHA = 0.05 / BONF_N   # = 0.0010

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "2026-07-13_bt3_bt4_increments.md")

ASSERT_COUNT = {"n": 0, "runs": 0}


# ---------------------------------------------------------------------------
# simulate_aa_ext -- BT2.simulate_aa PLUS two ablation seams (band_mode,
# washout_active/washout_boost). Everything else below is a byte-for-byte copy
# of exp_bt2_aa_structure.simulate_aa (lines ~178-403 as of 2026-07-12); the
# two diffs are marked "# >>> BT-3" and "# >>> BT-4" inline.
# ---------------------------------------------------------------------------

def simulate_aa_ext(variant, band_open, u_spy, u_qqq, spy_close, qqq_close,
                    r_cash, r_basket, r_qqq, spy_gate, qqq_gate,
                    beta_B, beta_T, ledger_mask, capital=CAPITAL,
                    band_mode="regime", washout_active=None,
                    washout_boost=0.0):
    """AA structure sim -- copy of BT2.simulate_aa with 2 ablation seams.

    band_mode: "regime" = BT-2's original 3-way band table (byte-identical
        behavior to BT2.simulate_aa when washout_active is None -- see the
        equivalence self-check in main()). "locked" = BT-3 ablation: band is
        ALWAYS band_open, regime-based shrink to 0.925/0.0 disabled.
    washout_active: BT-4 -- optional bool array (len n). On ledger bars where
        True, `leap_dn` gets += washout_boost (flat NAV-delta add) before the
        50/50 split / leverage conversion / 15%-premium cap -- i.e. the boost
        is subject to the SAME downstream cap as everything else (disclosed).
    """
    n = len(r_cash)
    units = [u_spy, u_qqq]
    gates = [spy_gate, qqq_gate]
    closes = [spy_close, qqq_close]
    strict = (variant == "strict")

    tval = 0.0
    bval = 0.0
    parked = 0.0
    cash = capital
    opt = [0.0, 0.0]
    c = [0.0, 0.0]
    prev_mark = [np.nan, np.nan]
    tgt_frac = [0.0, 0.0]

    nav = np.empty(n)
    dn_series, premfrac_series = [], []
    bailout = underfund = park_events = warmup_bars = boost_bars = 0
    prev_nav = capital

    for i in range(n):
        costs = 0.0

        # ---- accruals + LEAP mark-to-market -------------------------------
        interest = cash * r_cash[i]
        cash += interest
        b_pnl = bval * r_basket[i]
        bval += b_pnl
        t_pnl = tval * r_qqq[i]
        tval += t_pnl
        parked_pnl = parked * r_basket[i]
        parked += parked_pnl
        l_pnl = 0.0
        for L in range(2):
            u = units[L]
            if c[L] > 0.0:
                pnl = c[L] * (u["mark_pre"][i] - prev_mark[L]) * 100.0
                opt[L] += pnl
                l_pnl += pnl

        # ---- intramonth unit-path SELL events ------------------------------
        for L in range(2):
            u = units[L]
            if bool(u["sell"][i]) and c[L] > 0.0:
                gross = c[L] * u["sell_mark"][i] * 100.0
                proceeds = gross * (1.0 - COST_OPT)
                costs += gross * COST_OPT
                opt[L] = 0.0
                c[L] = 0.0
                is_roll = bool(u["rolled"][i])
                if is_roll:
                    cash += proceeds
                elif strict and not gates[L][i]:
                    parked += proceeds * (1.0 - COST_ETF)
                    costs += proceeds * COST_ETF
                    park_events += 1
                else:
                    cash += proceeds

        # ---- intramonth unit-path BUY events (carried tgt_frac) ------------
        for L in range(2):
            u = units[L]
            if bool(u["buy"][i]):
                nav_now = tval + bval + opt[0] + opt[1] + parked + cash
                target_prem = tgt_frac[L] * nav_now
                if target_prem > 1e-9 and u["buy_mark"][i] > 1e-12:
                    is_roll = bool(u["rolled"][i])
                    parked_first = strict and (not is_roll)
                    need = target_prem * (1.0 + COST_OPT)
                    if parked_first and parked > 1e-12 and need > 1e-12:
                        net_avail = parked * (1.0 - COST_ETF)
                        take = min(net_avail, need)
                        s = take / (1.0 - COST_ETF)
                        parked -= s
                        costs += s * COST_ETF
                        need -= take
                    if need > 1e-12:
                        take = min(max(cash, 0.0), need)
                        cash -= take
                        need -= take
                    if need > 1e-9:
                        avail = max(bval, 0.0) * (1.0 - COST_ETF)
                        take = min(avail, need)
                        if take > 0.0:
                            s = take / (1.0 - COST_ETF)
                            bval -= s
                            costs += s * COST_ETF
                            need -= take
                            bailout += 1
                    if need > 1e-9 and parked > 0.0:
                        avail = parked * (1.0 - COST_ETF)
                        take = min(avail, need)
                        s = take / (1.0 - COST_ETF)
                        parked -= s
                        costs += s * COST_ETF
                        need -= take
                    opt[L] = target_prem
                    costs += target_prem * COST_OPT
                    c[L] = target_prem / (u["buy_mark"][i] * 100.0)

        # ---- delta ledger at month-start (+ forced day-1) ------------------
        if ledger_mask[i]:
            nav_now = tval + bval + opt[0] + opt[1] + parked + cash
            b_actual_w = bval / nav_now if nav_now > 0 else 0.0
            t_actual_w = tval / nav_now if nav_now > 0 else 0.0
            n_off = (0 if spy_gate[i] else 1) + (0 if qqq_gate[i] else 1)
            # >>> BT-3 ablation seam (ONLY new line vs BT2.simulate_aa here):
            if band_mode == "locked":
                band = band_open
            else:
                band = (band_open, BAND_1, BAND_2)[n_off]
            if np.isfinite(beta_B[i]) and np.isfinite(beta_T[i]):
                leap_dn = max(0.0, band - b_actual_w * beta_B[i] - t_actual_w * beta_T[i])
            else:
                leap_dn = 0.0
                warmup_bars += 1
            # >>> BT-4 ablation seam (ONLY new lines vs BT2.simulate_aa here):
            if washout_active is not None and bool(washout_active[i]):
                leap_dn += washout_boost
                boost_bars += 1
            if spy_gate[i] and qqq_gate[i]:
                share = [0.5 * leap_dn, 0.5 * leap_dn]
            elif spy_gate[i]:
                share = [leap_dn, 0.0]
            elif qqq_gate[i]:
                share = [0.0, leap_dn]
            else:
                share = [0.0, 0.0]
            prem = [0.0, 0.0]
            for L in range(2):
                u = units[L]
                if share[L] > 0.0 and bool(u["hold"][i]) and u["mark"][i] > 1e-12:
                    lev = (u["delta"][i] * closes[L][i]) / u["mark"][i]
                    prem[L] = share[L] / lev if lev > 1e-12 else 0.0
            total_prem = prem[0] + prem[1]
            if total_prem > LEAP_CAP and total_prem > 1e-12:
                sc = LEAP_CAP / total_prem
                prem = [prem[0] * sc, prem[1] * sc]
                total_prem = LEAP_CAP
            tgt_frac = [prem[0], prem[1]]
            dn_series.append(leap_dn)
            premfrac_series.append(min(total_prem, LEAP_CAP))

            new_t = T_NOM * nav_now
            dT = new_t - tval
            costs += abs(dT) * COST_ETF
            tval = new_t
            cash -= dT + abs(dT) * COST_ETF

            for L in range(2):
                u = units[L]
                if bool(u["hold"][i]) and u["mark"][i] > 1e-12:
                    target_val = tgt_frac[L] * nav_now
                    dL = target_val - opt[L]
                    costs += abs(dL) * COST_OPT
                    opt[L] = target_val
                    c[L] = target_val / (u["mark"][i] * 100.0)
                    cash -= dL + abs(dL) * COST_OPT
                else:
                    tgt_frac[L] = 0.0

            if cash > 1e-12:
                x = cash / (1.0 + COST_ETF)
                bval += x
                costs += x * COST_ETF
                cash -= x + x * COST_ETF
            elif cash < -1e-12:
                need = -cash
                avail = max(bval, 0.0) * (1.0 - COST_ETF)
                take = min(avail, need)
                if take > 0.0:
                    s = take / (1.0 - COST_ETF)
                    bval -= s
                    costs += s * COST_ETF
                    cash += take
                    need -= take
                if need > 1e-9 and parked > 0.0:
                    avail = parked * (1.0 - COST_ETF)
                    take = min(avail, need)
                    s = take / (1.0 - COST_ETF)
                    parked -= s
                    costs += s * COST_ETF
                    cash += take
                    need -= take
                    underfund += 1

        for L in range(2):
            prev_mark[L] = units[L]["mark"][i] if c[L] > 0.0 else np.nan

        v = tval + bval + opt[0] + opt[1] + parked + cash
        expected = prev_nav + interest + b_pnl + t_pnl + parked_pnl + l_pnl - costs
        if abs(v - expected) > 1e-6 * max(1.0, abs(expected)):
            raise AssertionError(f"[{variant} band{band_open} mode{band_mode}] cross-foot fail "
                                 f"bar {i}: nav={v!r} expected={expected!r}")
        if v <= 0:
            raise AssertionError(f"[{variant}] non-positive NAV bar {i}: {v!r}")
        if cash < -1e-6:
            raise AssertionError(f"[{variant}] negative cash bar {i}: {cash!r}")
        if parked < -1e-6:
            raise AssertionError(f"[{variant}] negative parked bar {i}: {parked!r}")
        ASSERT_COUNT["n"] += 4

        nav[i] = v
        prev_nav = v

    ASSERT_COUNT["runs"] += 1
    return {"nav": nav, "dn_series": np.array(dn_series),
            "premfrac_series": np.array(premfrac_series),
            "bailout": bailout, "underfund": underfund,
            "park_events": park_events, "warmup_bars": warmup_bars,
            "boost_bars": boost_bars}


# ---------------------------------------------------------------------------
# data assembly -- mirrors exp_bt2_aa_structure.main()'s data section verbatim
# (same imported functions, same order) so the ablations run on IDENTICAL
# inputs to BT-2's own run.
# ---------------------------------------------------------------------------

def build_common():
    prov_all = []
    irx_df = M.load("^IRX")
    irx = irx_df["close"]
    prov_all.append(("^IRX", irx_df.attrs.get("source", "?"), len(irx_df),
                     str(irx_df.index.min().date()), str(irx_df.index.max().date())))
    data = {}
    for under, volsym in [("SPY", "^VIX"), ("QQQ", "^VXN")]:
        df, prov, _ = M.build_underlying(under, volsym, irx)
        data[under] = {"df": df}
        prov_all += prov
        print(f"{under} joined: {df.index[0].date()} -> {df.index[-1].date()}, "
              f"{len(df)} days", flush=True)
    spy_df, qqq_df = data["SPY"]["df"], data["QQQ"]["df"]
    for under, df in [("SPY", spy_df), ("QQQ", qqq_df)]:
        d = data[under]
        d["close"] = df["close"].values
        d["iv_raw"] = df["vol"].values / 100.0 * IV_MULT
        d["r_arr"] = df["irx"].values / 100.0
        d["q_arr"] = df["q"].values
        d["r_cash"] = d["r_arr"] / TD
        d["gate"] = M.build_gates(df)["GATED"]
        d["r_net"] = df["r_net"].values

    def_dfs = {}
    for sym in DEFENSIVE:
        dfx, prov = build_core_only(sym)
        def_dfs[sym] = dfx
        prov_all += prov
    def_idx = def_dfs[DEFENSIVE[0]].index
    for sym in DEFENSIVE[1:]:
        def_idx = def_idx.intersection(def_dfs[sym].index)
    basket_r = pd.concat([def_dfs[s]["r_net"].reindex(def_idx) for s in DEFENSIVE],
                         axis=1).mean(axis=1)
    basket_r.name = "basket_r_net"

    common_idx = spy_df.index.intersection(qqq_df.index)
    common_idx = common_idx.intersection(def_idx)
    common_idx = common_idx.intersection(irx_df.index)
    print(f"AA common (8-way) window: {common_idx[0].date()} -> {common_idx[-1].date()}, "
          f"{len(common_idx)} days", flush=True)

    qqq_full_df, _ = build_core_only("QQQ")
    spy_r_s = pd.Series(data["SPY"]["r_net"], index=spy_df.index)
    qqq_r_s = qqq_full_df["r_net"]
    beta_idx = spy_r_s.index.intersection(qqq_r_s.index).intersection(basket_r.index)
    beta_df = pd.DataFrame({
        "spy": spy_r_s.reindex(beta_idx).values,
        "qqq": qqq_r_s.reindex(beta_idx).values,
        "bskt": basket_r.reindex(beta_idx).values}, index=beta_idx)
    beta_B_full = pd.Series(BT2.rolling_beta(beta_df["bskt"].values, beta_df["spy"].values),
                            index=beta_idx)
    beta_T_full = pd.Series(BT2.rolling_beta(beta_df["qqq"].values, beta_df["spy"].values),
                            index=beta_idx)
    beta_B = beta_B_full.reindex(common_idx).values
    beta_T = beta_T_full.reindex(common_idx).values
    warm_nan = int(np.sum(~np.isfinite(beta_B) | ~np.isfinite(beta_T)))
    print(f"beta_B[0]={beta_B[0]:.3f} beta_T[0]={beta_T[0]:.3f}; NaN-in-window bars="
          f"{warm_nan}", flush=True)

    base_paths, damped_paths = {}, {}
    for under in ("SPY", "QQQ"):
        d = data[under]
        iv_damped = M.damp_iv(d["iv_raw"], DAMP)
        base_paths[(under, DELTA)] = M.simulate_unit_path(
            d["close"], d["iv_raw"], d["r_arr"], d["q_arr"], d["gate"], DELTA)
        damped_paths[(under, DELTA)] = M.simulate_unit_path(
            d["close"], iv_damped, d["r_arr"], d["q_arr"], d["gate"], DELTA)

    def onc(series_vals, native_index):
        return pd.Series(series_vals, index=native_index).reindex(common_idx).values

    r_cash_c = onc(data["SPY"]["r_cash"], spy_df.index)
    r_qqq_c = onc(data["QQQ"]["r_net"], qqq_df.index)
    r_basket_c = basket_r.reindex(common_idx).values
    spy_rnet_c = onc(data["SPY"]["r_net"], spy_df.index)
    spy_close_c = onc(data["SPY"]["close"], spy_df.index)
    qqq_close_c = onc(data["QQQ"]["close"], qqq_df.index)
    spy_gate_c = onc(data["SPY"]["gate"], spy_df.index).astype(bool)
    qqq_gate_c = onc(data["QQQ"]["gate"], qqq_df.index).astype(bool)
    for name, arr in [("r_cash", r_cash_c), ("r_qqq", r_qqq_c), ("r_basket", r_basket_c),
                      ("spy_rnet", spy_rnet_c)]:
        assert not np.isnan(arr[1:]).any(), f"NaN in {name} on common window"

    def unit_on_common(under, paths_dict):
        native_index = data[under]["df"].index
        udf = pd.DataFrame(paths_dict[(under, DELTA)], index=native_index)
        sl = udf.reindex(common_idx)
        return {k: sl[k].values for k in udf.columns}

    ledger_mask = M.month_start_mask(common_idx)
    ledger_mask[0] = True

    u_spy_b = unit_on_common("SPY", base_paths)
    u_qqq_b = unit_on_common("QQQ", base_paths)
    u_spy_d = unit_on_common("SPY", damped_paths)
    u_qqq_d = unit_on_common("QQQ", damped_paths)

    return dict(prov_all=prov_all, common_idx=common_idx, beta_B=beta_B, beta_T=beta_T,
               warm_nan=warm_nan, r_cash_c=r_cash_c, r_qqq_c=r_qqq_c, r_basket_c=r_basket_c,
               spy_rnet_c=spy_rnet_c, spy_close_c=spy_close_c, qqq_close_c=qqq_close_c,
               spy_gate_c=spy_gate_c, qqq_gate_c=qqq_gate_c, ledger_mask=ledger_mask,
               u_spy_b=u_spy_b, u_qqq_b=u_qqq_b, u_spy_d=u_spy_d, u_qqq_d=u_qqq_d)


# ---------------------------------------------------------------------------
# washout signal -- reuses build_breadth()/episodes() verbatim
# ---------------------------------------------------------------------------

def build_washout_active(common_idx):
    adv, a50, a200 = build_breadth()
    a50c = a50.dropna()
    wash_mask = a50c <= a50c.quantile(WASHOUT_QUANTILE)
    eps = episodes(wash_mask, gap=WASHOUT_GAP_TD)
    a50_idx = a50c.index
    active = np.zeros(len(a50_idx), dtype=bool)
    entries = []
    for (a, b, ndays) in eps:
        pos = a50_idx.get_loc(a)
        entry_pos = pos + 1                       # T+1 execution, no lookahead
        if entry_pos >= len(a50_idx):
            continue
        entries.append(a50_idx[entry_pos])
        end_pos = min(entry_pos + WASHOUT_HOLD_TD, len(a50_idx))
        active[entry_pos:end_pos] = True
    active_s = pd.Series(active, index=a50_idx)
    active_c = active_s.reindex(common_idx).fillna(False).values.astype(bool)

    # telemetry: episodes whose entry falls inside the AA window, and how many
    # are actually "seen" by a ledger bar (monthly cadence caveat)
    w0, w1 = common_idx[0], common_idx[-1]
    entries_in_window = [e for e in entries if w0 <= e <= w1]
    return active_c, {"n_episodes_total": len(eps), "n_entries_in_window": len(entries_in_window),
                      "p10_threshold": float(a50c.quantile(WASHOUT_QUANTILE)),
                      "a50_span": (str(a50_idx[0].date()), str(a50_idx[-1].date()))}


# ---------------------------------------------------------------------------
# significance helper: paired long/short spread of daily returns, Jensen-alpha
# vs SPY (nets out any beta the mechanism itself reintroduces), same t/p
# convention as BT-2.
# ---------------------------------------------------------------------------

def paired_spread_alpha(nav_a, nav_b, bench_ret):
    ret_a = nav_a[1:] / nav_a[:-1] - 1.0
    ret_b = nav_b[1:] / nav_b[:-1] - 1.0
    spread = ret_a - ret_b
    a, beta, t = metrics.jensen_alpha(spread, bench_ret[1:])
    return a, beta, t


def slice_of(mask):
    idx = np.where(mask)[0]
    return (int(idx[0]), int(idx[-1]) + 1) if len(idx) else (0, 0)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    C = build_common()
    common_idx = C["common_idx"]
    NW = len(common_idx)
    beta_B, beta_T = C["beta_B"], C["beta_T"]
    ledger_mask = C["ledger_mask"]
    spy_close_c, qqq_close_c = C["spy_close_c"], C["qqq_close_c"]
    r_cash_c, r_basket_c, r_qqq_c = C["r_cash_c"], C["r_basket_c"], C["r_qqq_c"]
    spy_gate_c, qqq_gate_c = C["spy_gate_c"], C["qqq_gate_c"]
    spy_rnet_c = C["spy_rnet_c"]

    paths_by_iv = {"base": (C["u_spy_b"], C["u_qqq_b"]), "damp": (C["u_spy_d"], C["u_qqq_d"])}

    washout_active_c, wtel = build_washout_active(common_idx)
    print(f"washout signal: {wtel['n_episodes_total']} FINE episodes total; "
          f"{wtel['n_entries_in_window']} entries inside AA window; "
          f"p10 threshold={wtel['p10_threshold']:.1f}%; a50 span "
          f"{wtel['a50_span'][0]}..{wtel['a50_span'][1]}", flush=True)

    def args_for(iv):
        us, uq = paths_by_iv[iv]
        return (VARIANT, BAND_OPEN_BASE, us, uq, spy_close_c, qqq_close_c,
                r_cash_c, r_basket_c, r_qqq_c, spy_gate_c, qqq_gate_c,
                beta_B, beta_T, ledger_mask)

    # ---- BASELINE arm: AA-strict FULL version, BT2.simulate_aa UNMODIFIED ---
    BASE = {}
    for iv in ("base", "damp"):
        BASE[iv] = BT2.simulate_aa(*args_for(iv))
    print(f"baseline (BT2.simulate_aa unmodified) done ({time.time()-t0:.0f}s)", flush=True)

    # ---- equivalence self-check: simulate_aa_ext(regime, no boost) must ----
    # ---- reproduce BT2.simulate_aa's NAV path bit-for-bit ------------------
    eq_run = simulate_aa_ext(*args_for("base"), band_mode="regime", washout_active=None)
    eq_ok = np.allclose(eq_run["nav"], BASE["base"]["nav"], rtol=0, atol=1e-6)
    eq_maxdiff = float(np.max(np.abs(eq_run["nav"] - BASE["base"]["nav"])))
    print(f"equivalence self-check (simulate_aa_ext vs BT2.simulate_aa, base IV): "
          f"{'PASS' if eq_ok else 'FAIL'} (max abs NAV diff = {eq_maxdiff:.6g})", flush=True)
    assert eq_ok, (f"simulate_aa_ext does NOT reproduce BT2.simulate_aa on identical inputs "
                   f"(max diff {eq_maxdiff}) -- ablation numbers below would be untrustworthy; "
                   f"aborting.")

    # ---- BT-3: locked-band arm ----------------------------------------------
    BT3 = {}
    for iv in ("base", "damp"):
        BT3[iv] = simulate_aa_ext(*args_for(iv), band_mode="locked", washout_active=None)
    print(f"BT-3 locked-band arm done ({time.time()-t0:.0f}s)", flush=True)

    # ---- BT-4: washout-boosted arm ------------------------------------------
    BT4 = {}
    for iv in ("base", "damp"):
        BT4[iv] = simulate_aa_ext(*args_for(iv), band_mode="regime",
                                  washout_active=washout_active_c,
                                  washout_boost=WASHOUT_BOOST)
    print(f"BT-4 washout-boost arm done ({time.time()-t0:.0f}s)", flush=True)

    # ---- headline metrics -----------------------------------------------
    def hm(sim, iv):
        return BT2.nav_metrics(sim[iv]["nav"], spy_rnet_c, 0, NW)

    m_base_b, m_base_d = hm(BASE, "base"), hm(BASE, "damp")
    m_bt3_b, m_bt3_d = hm(BT3, "base"), hm(BT3, "damp")
    m_bt4_b, m_bt4_d = hm(BT4, "base"), hm(BT4, "damp")

    # ---- paired-spread significance (base IV headline, damp IV shown too) --
    a3b, beta3b, t3b = paired_spread_alpha(BASE["base"]["nav"], BT3["base"]["nav"], spy_rnet_c)
    a3d, beta3d, t3d = paired_spread_alpha(BASE["damp"]["nav"], BT3["damp"]["nav"], spy_rnet_c)
    a4b, beta4b, t4b = paired_spread_alpha(BT4["base"]["nav"], BASE["base"]["nav"], spy_rnet_c)
    a4d, beta4d, t4d = paired_spread_alpha(BT4["damp"]["nav"], BASE["damp"]["nav"], spy_rnet_c)
    p3b, p3d = M.two_sided_p_from_t(t3b), M.two_sided_p_from_t(t3d)
    p4b, p4d = M.two_sided_p_from_t(t4b), M.two_sided_p_from_t(t4d)

    # ---- arms' own alpha-vs-SPY significance (for the registry) ------------
    pb3b, pb3d = M.two_sided_p_from_t(m_bt3_b["t"]), M.two_sided_p_from_t(m_bt3_d["t"])
    pb4b, pb4d = M.two_sided_p_from_t(m_bt4_b["t"]), M.two_sided_p_from_t(m_bt4_d["t"])

    # ---- capital-efficiency readouts ----------------------------------------
    def cap_eff(sim):
        pf = sim["premfrac_series"]
        dn = sim["dn_series"]
        acs = 0.25 + (float(np.mean(pf)) if len(pf) else 0.0)
        return dict(dn_med=np.median(dn) * 100 if len(dn) else float("nan"),
                    dn_p90=np.percentile(dn, 90) * 100 if len(dn) else float("nan"),
                    acs=acs * 100, bailout=sim["bailout"], underfund=sim["underfund"],
                    park=sim["park_events"], warmup=sim["warmup_bars"],
                    boost=sim.get("boost_bars", 0))

    ce_base, ce_bt3, ce_bt4 = cap_eff(BASE["base"]), cap_eff(BT3["base"]), cap_eff(BT4["base"])

    # ---- stress-year compact check (base IV) --------------------------------
    yrs = common_idx.year.values
    stress_windows = [("FULL", np.ones(NW, dtype=bool)), ("2008", yrs == 2008),
                      ("2020", yrs == 2020), ("2022", yrs == 2022)]

    def stress_row(sim):
        cells = []
        for _, mask in stress_windows:
            lo, hi = slice_of(mask)
            if hi - lo < 30:
                cells.append("n/a")
                continue
            mm = BT2.nav_metrics(sim["base"]["nav"], spy_rnet_c, lo, hi)
            cells.append(BT2._p(mm["CAGR"]))
        return cells

    stress_base = stress_row(BASE)
    stress_bt3 = stress_row(BT3)
    stress_bt4 = stress_row(BT4)

    # ======================================================================
    # write report
    # ======================================================================
    L = []
    add = L.append
    add("# 結果 — BT-3/BT-4:AA-strict 結構內嘅單一機制增量(regime band / washout boost)")
    add("")
    add("**日期:** 2026-07-13  **腳本:** `backtest/experiments/exp_bt3_bt4_increments.py`  "
        "**狀態:** active")
    add("")
    add("## 動機同範圍")
    add("")
    add("BT-2(`2026-07-12_bt2_aa_vs_core.md`)已證明 AA-strict 全主動「結構」喺風險調整後"
        "唔輸 core-v2 / SPY B&H,但佢個 delta-ledger 將兩個機制捆埋一齊計:(1) regime→band 表"
        "(按閘門狀態 1.15/0.925/0.0);(2) 設計文件第 3 節第 4 點嘅 breadth-washout 一次性 "
        "+5% NAV-delta LEAP boost。**機器覆核:grep `exp_bt2_aa_structure.py` 揾 \"washout\" "
        "只有一個 hit — 檔案結尾嘅「Next」指針。washout boost 喺 BT-2 從未實作過。**"
        "本腳本逐個機制隔離其自身增量,AA-strict 機器其他一切鎖定不變。範圍:**只測 strict "
        "變體、band=1.15 headline**(BT-2 自己推薦嘅格 — 其結論 #2);FULL 窗 + 壓力年份速查"
        "(冇 H1/H2 拆分 — 比 BT-2 本身嘅結構測試窄,見 Caveats)。`exp_bt2_aa_structure.py` "
        "冇改過;下面嘅基線臂直接調用佢嘅 `simulate_aa`,未經修改。")
    add("")

    add("## 方法(mirror / increment / horizon)")
    add("")
    add("**Mirror(鏡像)**:同 BT-2 一模一樣嘅 AA-strict %-NAV 程序(防守 ballast + QQQ-beta "
        "thesis 替身 + 閘控 SPY/QQQ 0.50Δ LEAP overlay,由月度 delta ledger 定大細),對標 "
        "SPY B&H net-TR — 沿用 BT-2 嘅範圍限制(T sleeve = 零 alpha 嘅 QQQ-beta 替身;下面"
        "每個數都係「結構」結果)。")
    add("**Increment(增量)**:BT-3 只改 delta ledger 用嘅 `band` 值(regime 表 vs 鎖死 "
        "1.15)— 相對 `simulate_aa` 只有一行之差。BT-4 只改 ledger bar 上 breadth-washout "
        "信號會唔會令 `leap_dn` 加 +5% — 只加新行,冇拆嘢。兩者都用 `simulate_aa_ext`(有"
        "文檔記錄嘅 BT2.simulate_aa 複製本);其忠實度由下面嘅等價自檢「證明」而非假設。")
    add("**Horizon(期限)**:同 BT-2 不變 — 月度 delta-ledger 節奏(每月首個交易日 + 強制 "
        "day-1),LEAP 63td roll,月中只有閘門自身嘅 T+1 出/入/roll 會觸發。")
    add("")
    add(f"**Washout 信號(只用於 BT-4)**:原封不動重用 `exp_breadth_reversion.py` / "
        f"`exp_breadth_reversion_verify.py` 嘅 `build_breadth()`/`episodes()` — 即 BT-B "
        f"(`exp_bt_b_washout_expr.py`)用過嘅同一批函數。Mask = %above50 <= 自身歷史底 decile"
        f"(p10={wtel['p10_threshold']:.1f}%,a50 歷史 {wtel['a50_span'][0]}..{wtel['a50_span'][1]});"
        f"episode 以 gap={WASHOUT_GAP_TD}td 去重(FINE 粒度,冇危機敘事式去重 — 機械觸發,"
        f"唔係人手數件);入場 = episode 開始後 T+1(無前視);活躍窗 = {WASHOUT_HOLD_TD} 個"
        f"交易日,之後歸位(階梯函數,唔係漸退)— **共 {wtel['n_episodes_total']} 個 FINE "
        f"episode,{wtel['n_entries_in_window']} 個入場點落喺 AA 窗內**"
        f"({common_idx[0].date()}->{common_idx[-1].date()})。")
    add("")

    add("## 等價自檢(證明 `simulate_aa_ext` 係忠實複製)")
    add("")
    add(f"`simulate_aa_ext(band_mode=\"regime\", washout_active=None)` vs `BT2.simulate_aa`,"
        f"完全相同輸入(base IV、strict、band=1.15):**{'PASS' if eq_ok else 'FAIL'}**"
        f"({NW} 個 bar 嘅最大 NAV 絕對差 = {eq_maxdiff:.3g},容差 1e-6)。"
        + ("下面所有 ablation 數字都係對照「已驗證忠實」嘅 BT-2 引擎複製本量度。" if eq_ok else
           "**已中止 — 複製本唔忠實,下面結果無效。**"))
    add("")

    add("## BT-3 — regime→band 增量(AA-strict,base/damp 並列)")
    add("")
    add("| 臂 | IV | CAGR | Sharpe | MaxDD | β | Worst 12m | α vs SPY (t) |")
    add("|---|---|---|---|---|---|---|---|")

    add(f"| AA-strict 完整版(regime band,BT-2 原機)| base m0.85 | {BT2._p(m_base_b['CAGR'])} "
        f"| {m_base_b['Sharpe']:.2f} | {BT2._p(m_base_b['MaxDD'])} | {m_base_b['Beta']:.2f} | "
        f"{BT2._p(m_base_b['Worst12m'])} | {BT2._a(m_base_b)} |")
    add(f"| AA-strict 完整版(regime band,BT-2 原機)| damp 0.4 | {BT2._p(m_base_d['CAGR'])} "
        f"| {m_base_d['Sharpe']:.2f} | {BT2._p(m_base_d['MaxDD'])} | {m_base_d['Beta']:.2f} | "
        f"{BT2._p(m_base_d['Worst12m'])} | {BT2._a(m_base_d)} |")
    add(f"| AA-strict band 鎖死 @1.15(拆走 regime)| base m0.85 | {BT2._p(m_bt3_b['CAGR'])} "
        f"| {m_bt3_b['Sharpe']:.2f} | {BT2._p(m_bt3_b['MaxDD'])} | {m_bt3_b['Beta']:.2f} | "
        f"{BT2._p(m_bt3_b['Worst12m'])} | {BT2._a(m_bt3_b)} |")
    add(f"| AA-strict band 鎖死 @1.15(拆走 regime)| damp 0.4 | {BT2._p(m_bt3_d['CAGR'])} "
        f"| {m_bt3_d['Sharpe']:.2f} | {BT2._p(m_bt3_d['MaxDD'])} | {m_bt3_d['Beta']:.2f} | "
        f"{BT2._p(m_bt3_d['Worst12m'])} | {BT2._a(m_bt3_d)} |")
    add("")
    add("**BT-3 增量(完整版 − 鎖死版,算術差)**:")
    add("")
    add("| IV | ΔCAGR | ΔSharpe | ΔMaxDD | Δα (pp) | Δ 平均 alpha-capital share (pp) |")
    add("|---|---|---|---|---|---|")
    add(f"| base | {(m_base_b['CAGR']-m_bt3_b['CAGR'])*100:+.1f}pp | "
        f"{m_base_b['Sharpe']-m_bt3_b['Sharpe']:+.2f} | "
        f"{(m_base_b['MaxDD']-m_bt3_b['MaxDD'])*100:+.1f}pp | "
        f"{(m_base_b['Alpha']-m_bt3_b['Alpha'])*100:+.1f}pp | "
        f"{ce_base['acs']-ce_bt3['acs']:+.1f}pp |")
    add(f"| damp | {(m_base_d['CAGR']-m_bt3_d['CAGR'])*100:+.1f}pp | "
        f"{m_base_d['Sharpe']-m_bt3_d['Sharpe']:+.2f} | "
        f"{(m_base_d['MaxDD']-m_bt3_d['MaxDD'])*100:+.1f}pp | "
        f"{(m_base_d['Alpha']-m_bt3_d['Alpha'])*100:+.1f}pp | n/a |")
    add("")
    add(f"**配對價差顯著性**(long 完整版 / short 鎖死版嘅日報酬差,對 SPY 做 Jensen-alpha "
        f"以扣走 band 重新引入嘅任何 beta):base IV spread-α "
        f"**{a3b*100:+.2f}pp (t{t3b:+.2f}, p={p3b:.3g}, {'Bonf-PASS' if np.isfinite(p3b) and p3b<=BONF_ALPHA else 'Bonf-FAIL'})**;"
        f"damp IV spread-α {a3d*100:+.2f}pp (t{t3d:+.2f}, p={p3d:.3g}, "
        f"{'Bonf-PASS' if np.isfinite(p3d) and p3d<=BONF_ALPHA else 'Bonf-FAIL'})— spread 對 SPY "
        f"嘅 beta:base {beta3b:.2f}、damp {beta3d:.2f}(Bonferroni×{BONF_N},α<={BONF_ALPHA:.5f},"
        f"保守沿用 BT-2 registry 嘅門檻,唔另計 N)。")
    add("")

    add("## BT-4 — washout boost 增量(AA-strict,base/damp 並列)")
    add("")
    add("| 臂 | IV | CAGR | Sharpe | MaxDD | β | Worst 12m | α vs SPY (t) |")
    add("|---|---|---|---|---|---|---|---|")
    add(f"| AA-strict 完整版(無 boost,BT-2 原機)| base m0.85 | {BT2._p(m_base_b['CAGR'])} "
        f"| {m_base_b['Sharpe']:.2f} | {BT2._p(m_base_b['MaxDD'])} | {m_base_b['Beta']:.2f} | "
        f"{BT2._p(m_base_b['Worst12m'])} | {BT2._a(m_base_b)} |")
    add(f"| AA-strict 完整版(無 boost,BT-2 原機)| damp 0.4 | {BT2._p(m_base_d['CAGR'])} "
        f"| {m_base_d['Sharpe']:.2f} | {BT2._p(m_base_d['MaxDD'])} | {m_base_d['Beta']:.2f} | "
        f"{BT2._p(m_base_d['Worst12m'])} | {BT2._a(m_base_d)} |")
    add(f"| AA-strict + washout boost(+5% NAV delta,21td)| base m0.85 | {BT2._p(m_bt4_b['CAGR'])} "
        f"| {m_bt4_b['Sharpe']:.2f} | {BT2._p(m_bt4_b['MaxDD'])} | {m_bt4_b['Beta']:.2f} | "
        f"{BT2._p(m_bt4_b['Worst12m'])} | {BT2._a(m_bt4_b)} |")
    add(f"| AA-strict + washout boost(+5% NAV delta,21td)| damp 0.4 | {BT2._p(m_bt4_d['CAGR'])} "
        f"| {m_bt4_d['Sharpe']:.2f} | {BT2._p(m_bt4_d['MaxDD'])} | {m_bt4_d['Beta']:.2f} | "
        f"{BT2._p(m_bt4_d['Worst12m'])} | {BT2._a(m_bt4_d)} |")
    add("")
    add("**BT-4 增量(加 boost 版 − 完整版,算術差)**:")
    add("")
    add("| IV | ΔCAGR | ΔSharpe | ΔMaxDD | Δα (pp) | Δ 平均 alpha-capital share (pp) | boost 觸發(ledger bars)|")
    add("|---|---|---|---|---|---|---|")
    add(f"| base | {(m_bt4_b['CAGR']-m_base_b['CAGR'])*100:+.1f}pp | "
        f"{m_bt4_b['Sharpe']-m_base_b['Sharpe']:+.2f} | "
        f"{(m_bt4_b['MaxDD']-m_base_b['MaxDD'])*100:+.1f}pp | "
        f"{(m_bt4_b['Alpha']-m_base_b['Alpha'])*100:+.1f}pp | "
        f"{ce_bt4['acs']-ce_base['acs']:+.1f}pp | {ce_bt4['boost']} |")
    add(f"| damp | {(m_bt4_d['CAGR']-m_base_d['CAGR'])*100:+.1f}pp | "
        f"{m_bt4_d['Sharpe']-m_base_d['Sharpe']:+.2f} | "
        f"{(m_bt4_d['MaxDD']-m_base_d['MaxDD'])*100:+.1f}pp | "
        f"{(m_bt4_d['Alpha']-m_base_d['Alpha'])*100:+.1f}pp | n/a | n/a |")
    add("")
    add(f"**配對價差顯著性**(long 加 boost 版 / short 完整版):base IV spread-α "
        f"**{a4b*100:+.2f}pp (t{t4b:+.2f}, p={p4b:.3g}, {'Bonf-PASS' if np.isfinite(p4b) and p4b<=BONF_ALPHA else 'Bonf-FAIL'})**;"
        f"damp IV spread-α {a4d*100:+.2f}pp (t{t4d:+.2f}, p={p4d:.3g}, "
        f"{'Bonf-PASS' if np.isfinite(p4d) and p4d<=BONF_ALPHA else 'Bonf-FAIL'})— spread 對 SPY "
        f"嘅 beta:base {beta4b:.2f}、damp {beta4d:.2f}(同 BT-3 一樣嘅 Bonferroni×{BONF_N} 門檻)。")
    add("")

    add("## 資本效率讀數(base IV,FULL 窗)")
    add("")
    add("| 臂 | Dn 中位 | Dn p90 | 平均 alpha-capital share | bailout | underfund | park (strict) | warm-up-zero | boost 觸發 |")
    add("|---|---|---|---|---|---|---|---|---|")
    add(f"| 完整版(regime band,無 boost)| {ce_base['dn_med']:.0f}% | {ce_base['dn_p90']:.0f}% | "
        f"{ce_base['acs']:.1f}% | {ce_base['bailout']} | {ce_base['underfund']} | {ce_base['park']} | "
        f"{ce_base['warmup']} | {ce_base['boost']} |")
    add(f"| BT-3 band 鎖死 | {ce_bt3['dn_med']:.0f}% | {ce_bt3['dn_p90']:.0f}% | {ce_bt3['acs']:.1f}% | "
        f"{ce_bt3['bailout']} | {ce_bt3['underfund']} | {ce_bt3['park']} | {ce_bt3['warmup']} | "
        f"{ce_bt3['boost']} |")
    add(f"| BT-4 加 washout boost | {ce_bt4['dn_med']:.0f}% | {ce_bt4['dn_p90']:.0f}% | {ce_bt4['acs']:.1f}% | "
        f"{ce_bt4['bailout']} | {ce_bt4['underfund']} | {ce_bt4['park']} | {ce_bt4['warmup']} | "
        f"{ce_bt4['boost']} |")
    add("")

    add("## 壓力年份速查(CAGR,base IV)")
    add("")
    add("| 臂 | " + " | ".join(w for w, _ in stress_windows) + " |")
    add("|---|" + "---|" * len(stress_windows))
    add(f"| 完整版(regime band,無 boost)| " + " | ".join(stress_base) + " |")
    add(f"| BT-3 band 鎖死 | " + " | ".join(stress_bt3) + " |")
    add(f"| BT-4 加 washout boost | " + " | ".join(stress_bt4) + " |")
    add("")

    add("## 數據來源")
    add("")
    add("| 序列 | 來源 | 行數 | 起 | 迄 |")
    add("|---|---|---|---|---|")
    for name, src, rows, dfrom, dto in C["prov_all"]:
        add(f"| {name} | {src} | {rows} | {dfrom} | {dto} |")
    add("")
    add(f"AA 共同窗:**{common_idx[0].date()} -> {common_idx[-1].date()}({NW} 日)** — "
        f"同 BT-2 一樣嘅構造;beta_B[0]={beta_B[0]:.2f}、beta_T[0]={beta_T[0]:.2f},"
        f"窗內 NaN-beta bar 數:{C['warm_nan']}。")
    add("")

    add("## Caveats")
    add("")
    add("- **(範圍)只測 strict、band=1.15 headline**:BT-2 嘅完整 pragmatic×3-band 網格冇"
        "重跑;呢度係對贏家格嘅窄範圍針對性 ablation。方向「預期」對 pragmatic 都成立,但未驗證。")
    add("- **(a) washout boost 嘅月度節奏錯配**:AA ledger 只喺月初 bar resize(BT-2 自身 "
        "caveat (a),原樣繼承)。washout 信號每日計,但只喺 ledger bar 檢查 — 如果一個 episode "
        f"嘅整個 21 交易日活躍窗完全落喺兩個月初之間,佢就永遠唔會觸發。AA 窗內有 "
        f"{wtel['n_entries_in_window']} 個 washout 入場點;boost 實際喺 {ce_bt4['boost']} 個 "
        "ledger bar 觸發(base IV)— 兩個數之間嘅差就係呢個節奏錯配效應,如實披露,冇抹平。")
    add("- **(b) 兩個新臂冇計 DSR**:BT-2 將佢 6 個新 trial + 42 個舊 trial 餵入 "
        "`deflated_sharpe_ratio` 對照 48 格 Sharpe universe。為呢個窄增量測試重算嗰個 universe "
        "超出範圍;呢度用 Bonferroni×50(0.05/50≈0.00104)做多重檢驗閘,同時應用於每臂自身 "
        "alpha-vs-SPY 以及(保守起見,沿用同一門檻而非另行推導)配對價差測試。")
    add("- **(c) washout boost 同現有 15% premium cap 相互作用**:+5% NAV-delta 加項同 "
        "`leap_dn` 其餘部分一樣受 `LEAP_CAP=0.15` premium 上限約束 — 如果 regime band 已經令 "
        "ledger 貼近上限,boost 會被部分或全部吸收、冇任何作用。呢點喺上面 Dn p90 / 平均 "
        "alpha-capital share 讀數度睇得到,冇隱藏。")
    add("- **(d) washout boost 觸發粒度**:用 FINE episode(gap=20td,冇危機級去重)做觸發 — "
        "機械、非揀櫻桃嘅定義,同 BT-B 自身嘅 FINE 粒度一致,而唔係 BT-B headline 用嘅危機敘事 "
        "8-12 件事件數(嗰個對賬係俾人讀嘅顯示慣例,唔係「乜嘢先算有效一次性觸發」嘅實質要求)。")
    add("- **(e) LEAP/BSM 模型風險原樣繼承自 BT-2/core-v2**:^VIX/^VXN 30d→1y IV-proxy 不變,"
        "base(m0.85)/damp(0.4) 並列展示,冇揀櫻桃。")
    add("- **(f) 單一歷史路徑**、單一數據供應商(yfinance-first);冇 bootstrap。")
    add("")

    add("## Cross-foot 驗證")
    add("")
    add(f"- {ASSERT_COUNT['runs']} 次 `simulate_aa_ext` 會計運行(5 = 1 等價自檢 + 2 BT-3 + "
        f"2 BT-4),{ASSERT_COUNT['n']:,} 個 bar 級 assert 全部通過(同 BT-2 一樣:NAV="
        "T+B+L+Parked+Cash / NAV>0 / Cash>=0 / Parked>=0 / 滾動恆等式,相對容差 1e-6)。"
        "2 次基線運行直接用 BT2.simulate_aa,帶 BT-2 自身嘅 assert(唔重複計入本檔 "
        "ASSERT_COUNT)。")
    add("")

    add("## 結論")
    add("")
    bt3_verdict = ("正(顯著)" if np.isfinite(p3b) and p3b <= BONF_ALPHA and a3b > 0 else
                   "負(顯著)" if np.isfinite(p3b) and p3b <= BONF_ALPHA and a3b < 0 else
                   "不顯著(噪音級,≈零)")
    bt4_verdict = ("正(顯著)" if np.isfinite(p4b) and p4b <= BONF_ALPHA and a4b > 0 else
                   "負(顯著)" if np.isfinite(p4b) and p4b <= BONF_ALPHA and a4b < 0 else
                   "不顯著(噪音級,≈零)")
    add(f"1. **BT-3(regime band)嘅 α 增量:{bt3_verdict}**:完整版−鎖死版 base-IV CAGR "
        f"{(m_base_b['CAGR']-m_bt3_b['CAGR'])*100:+.1f}pp、α 差 "
        f"{(m_base_b['Alpha']-m_bt3_b['Alpha'])*100:+.1f}pp、MaxDD 差 "
        f"{(m_base_b['MaxDD']-m_bt3_b['MaxDD'])*100:+.1f}pp;配對價差 base-IV α "
        f"{a3b*100:+.2f}pp(t{t3b:+.2f}, p={p3b:.3g},"
        f"{'過咗' if np.isfinite(p3b) and p3b<=BONF_ALPHA else '未過'} Bonferroni×{BONF_N})。"
        f"風險側讀數(唔入 α 檢驗,但係 regime band 存在嘅本意):MaxDD 差 "
        f"{(m_base_b['MaxDD']-m_bt3_b['MaxDD'])*100:+.1f}pp、underfund "
        f"{ce_base['underfund']} vs {ce_bt3['underfund']} 次、Dn 中位 "
        f"{ce_base['dn_med']:.0f}% vs {ce_bt3['dn_med']:.0f}% — regime band 嘅實際作用係"
        f"風險旋鈕(降槓桿/降尾部壓力),唔係 α 來源。")
    add(f"2. **BT-4(washout boost)嘅 α 增量:{bt4_verdict}**:加 boost 版−完整版 base-IV "
        f"CAGR {(m_bt4_b['CAGR']-m_base_b['CAGR'])*100:+.1f}pp、α 差 "
        f"{(m_bt4_b['Alpha']-m_base_b['Alpha'])*100:+.1f}pp、MaxDD 差 "
        f"{(m_bt4_b['MaxDD']-m_base_b['MaxDD'])*100:+.1f}pp;配對價差 base-IV α "
        f"{a4b*100:+.2f}pp(t{t4b:+.2f}, p={p4b:.3g},"
        f"{'過咗' if np.isfinite(p4b) and p4b<=BONF_ALPHA else '未過'} Bonferroni×{BONF_N});"
        f"boost 喺窗內 {int(np.sum(ledger_mask))} 個 ledger bar 之中觸發咗 {ce_bt4['boost']} 個"
        f"(窗內有 {wtel['n_entries_in_window']} 個 washout 入場點 — 差額係月度節奏漏接率,"
        "caveat (a))。")
    add("3. **遷移解讀**:上面判「正(顯著)」嘅組件先值得原樣帶入 live 設計;判「不顯著/負」"
        "即係嗰件複雜度喺呢條歷史路徑上冇賺到自己嘅位,冇進一步證據前唔應假設佢加值(佢仍可能"
        "因為呢個 sim 睇唔到嘅理由值得保留 — 例如 Jensen alpha 捕捉唔到嘅尾部風險框架 — 但嗰個"
        "係另一個論證,唔係回測增量)。")
    add("")

    with open(RESULTS, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nWrote {RESULTS} ({time.time()-t0:.0f}s)", flush=True)

    print("\n=== KEY NUMBERS ===", flush=True)
    print(f"BT-3 base spread-alpha {a3b*100:+.2f}pp t{t3b:+.2f} p{p3b:.3g} -> {bt3_verdict}", flush=True)
    print(f"BT-4 base spread-alpha {a4b*100:+.2f}pp t{t4b:+.2f} p{p4b:.3g} -> {bt4_verdict}", flush=True)
    print(f"boost fired {ce_bt4['boost']}/{int(np.sum(ledger_mask))} ledger bars "
          f"({wtel['n_entries_in_window']} washout entries in-window)", flush=True)


if __name__ == "__main__":
    main()
