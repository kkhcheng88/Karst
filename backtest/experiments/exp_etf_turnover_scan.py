"""backtest/experiments/exp_etf_turnover_scan.py -- market-wide ETF turnover scan.

TWO PURPOSES (see thesis/DESIGN.md sec1 crowding row + user task 2026-07-17):
  1. DISCOVERY: scan a ~150-220 name US-listed ETF universe (broad/sector/thematic/
     factor/international, hardcoded below with category tags) for tickers with
     material daily-dollar turnover that sit OUTSIDE backtest/spine/universe.yaml
     (currently just SPY/QQQ/SPMO) AND outside every theme's thesis_etf in
     thesis/themes.yaml -- i.e. things we may be blind to.
  2. CROWDING-AXIS INPUT: thesis/DESIGN.md sec1 row 39 lists "擁擠(新 thematic ETF
     上市/資金流)" as a chartered priced-in input -- never implemented. This scan
     produces exactly that reading for each of the 17 active themes' thesis ETF(s)
     (or nearest category-matched candidate where a theme has none): turnover-surge
     ratio (60d/252d $-volume) and listing age. NOTE this is DISTINCT from
     thesis/crowding_composite.py, which already exists but measures a different
     thing entirely (per-ticker analyst-attendance percentile + bull-report ratio,
     BOTH cross-sectional/temporal ATTENTION proxies) -- no existing module reads
     ETF listing dates or ETF-level volume surges. This module is additive, read-only:
     it does not touch crowding_composite.py, themes.yaml, or universe.yaml.

Data: backtest/data.py load() (yfinance-first OHLCV) for price/volume history;
yfinance .info / history(period="max") for AUM and inception date (fetched only for
the smaller "candidates of interest" subset -- theme-tagged tickers + anything
crossing the $20M/day blind-spot bar -- to keep the full-universe pass fast/light).

Liquidity bar: avg daily $-volume (60d) >= $5,000,000 = "enough turnover to matter"
(same order of magnitude as the ai-power-grid UTES/GRID sub-$15M satellite-sizing
precedent in themes.yaml -- below ~$5M, single trades move the tape and sizing
would be constrained regardless of the thesis). Sensitivity noted in the report.

Run: PYTHONUTF8=1 python backtest/experiments/exp_etf_turnover_scan.py
Output: backtest/results/2026-07-17_etf_turnover_scan.md (written by this script)
"""
from __future__ import annotations

import io
import os
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yaml
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data as karst_data  # backtest/data.py

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UNIVERSE_YAML = os.path.join(REPO, "backtest", "spine", "universe.yaml")
THEMES_YAML = os.path.join(REPO, "thesis", "themes.yaml")
OUT_MD = os.path.join(REPO, "backtest", "results", "2026-07-17_etf_turnover_scan.md")

TODAY = datetime.now(timezone.utc).replace(tzinfo=None)
LIQ_BAR = 5_000_000       # $5M/day "enough turnover" bar
BLIND_SPOT_BAR = 20_000_000  # $20M/day bar for table A (blind-spot)
NEW_MONTHS = 24            # <=24 months since inception = "new" (crowding signal)

# ---------------------------------------------------------------------------
# 1. Scan universe -- ~185 US-listed ETFs, hardcoded + category-tagged.
#    Leveraged/inverse products (2x/3x, "Bull"/"Bear"/"Daily") are EXCLUDED on
#    purpose: their volume is a derivatives-trading artifact, not a thematic-
#    capital-flow signal, and including them would contaminate both the
#    blind-spot and crowding reads (noted explicitly here, not silently dropped).
# ---------------------------------------------------------------------------
UNIVERSE: list[tuple[str, str]] = [
    # ticker, category
    # --- broad market ---
    ("SPY", "broad"), ("QQQ", "broad"), ("IWM", "broad"), ("DIA", "broad"),
    ("VTI", "broad"), ("VOO", "broad"), ("MDY", "broad"), ("RSP", "broad"),
    ("IWB", "broad"), ("IWF", "broad"), ("IWD", "broad"), ("SPMO", "broad"),
    # --- sector SPDR + Vanguard alternates ---
    ("XLK", "sector"), ("XLF", "sector"), ("XLV", "sector"), ("XLE", "sector"),
    ("XLI", "sector"), ("XLY", "sector"), ("XLP", "sector"), ("XLU", "sector"),
    ("XLB", "sector"), ("XLRE", "sector"), ("XLC", "sector"),
    ("VGT", "sector"), ("VDE", "sector"), ("VFH", "sector"), ("VHT", "sector"),
    ("VIS", "sector"), ("VCR", "sector"), ("VDC", "sector"), ("VPU", "sector"),
    ("VAW", "sector"), ("VNQ", "sector"), ("VOX", "sector"),
    ("IDU", "sector"), ("FUTY", "sector"),
    # --- semiconductor / AI hardware thematic ---
    ("SMH", "thematic_semi"), ("SOXX", "thematic_semi"), ("XSD", "thematic_semi"),
    ("PSI", "thematic_semi"), ("SOXQ", "thematic_semi"), ("FTXL", "thematic_semi"),
    ("CHPX", "thematic_semi"),
    # --- robotics / AI software ---
    ("BOTZ", "thematic_ai"), ("ROBO", "thematic_ai"), ("ARKQ", "thematic_ai"),
    ("IRBO", "thematic_ai"), ("AIQ", "thematic_ai"), ("WTAI", "thematic_ai"),
    ("ROBT", "thematic_ai"), ("KOMP", "thematic_ai"), ("THNQ", "thematic_ai"),
    ("LOUP", "thematic_ai"),
    # --- space / satellite ---
    ("ARKX", "thematic_space"), ("UFO", "thematic_space"), ("ROKT", "thematic_space"),
    ("NASA", "thematic_space"),
    # --- quantum ---
    ("QTUM", "thematic_quantum"),
    # --- nuclear / uranium / grid power ---
    ("URA", "thematic_power"), ("URNM", "thematic_power"), ("NLR", "thematic_power"),
    ("URNJ", "thematic_power"), ("NUKZ", "thematic_power"), ("GRID", "thematic_power"),
    ("UTES", "thematic_power"),
    # --- rare earth / critical minerals ---
    ("REMX", "thematic_materials"), ("XME", "thematic_materials"),
    ("PICK", "thematic_materials"), ("COPX", "thematic_materials"),
    # --- solar / clean energy ---
    ("ICLN", "thematic_clean"), ("TAN", "thematic_clean"), ("PBW", "thematic_clean"),
    ("QCLN", "thematic_clean"), ("FAN", "thematic_clean"),
    # --- battery / EV / lithium ---
    ("LIT", "thematic_ev"), ("DRIV", "thematic_ev"), ("IDRV", "thematic_ev"),
    ("KARS", "thematic_ev"), ("BATT", "thematic_ev"),
    # --- cybersecurity ---
    ("CIBR", "thematic_cyber"), ("HACK", "thematic_cyber"), ("IHAK", "thematic_cyber"),
    ("BUG", "thematic_cyber"),
    # --- biotech / pharma / GLP1-adjacent ---
    ("XBI", "thematic_biotech"), ("IBB", "thematic_biotech"), ("LABU", "thematic_biotech"),
    ("ARKG", "thematic_biotech"), ("BBH", "thematic_biotech"), ("PPH", "thematic_biotech"),
    ("IHE", "thematic_biotech"), ("XPH", "thematic_biotech"), ("GNOM", "thematic_biotech"),
    # --- infrastructure / defense / building products ---
    ("PAVE", "thematic_infra"), ("IFRA", "thematic_infra"),
    ("ITA", "thematic_defense"), ("PPA", "thematic_defense"), ("XAR", "thematic_defense"),
    ("DFEN", "thematic_defense"), ("SHLD", "thematic_defense"),
    ("ITB", "thematic_housing"), ("XHB", "thematic_housing"),
    ("PHO", "thematic_water"), ("FIW", "thematic_water"),
    # --- metals / mining ---
    ("GDX", "thematic_metals"), ("GDXJ", "thematic_metals"), ("SIL", "thematic_metals"),
    ("SILJ", "thematic_metals"),
    # --- crypto / blockchain ---
    ("BITQ", "thematic_crypto"), ("BLOK", "thematic_crypto"), ("BKCH", "thematic_crypto"),
    ("WGMI", "thematic_crypto"),
    # --- China tech / international / EM ---
    ("KWEB", "international"), ("CQQQ", "international"), ("EEM", "international"),
    ("EFA", "international"), ("VWO", "international"), ("INDA", "international"),
    ("EWJ", "international"),
    # --- factor / style ---
    ("MTUM", "factor"), ("QUAL", "factor"), ("VLUE", "factor"), ("USMV", "factor"),
    ("SPLV", "factor"), ("SPHQ", "factor"),
    # --- commodities / ag ---
    ("DBA", "commodity"), ("MOO", "commodity"), ("DBC", "commodity"),
    # --- energy sub-sector ---
    ("XOP", "thematic_energy"), ("OIH", "thematic_energy"), ("UNG", "thematic_energy"),
    ("FCG", "thematic_energy"),
    # --- financials sub-sector ---
    ("KRE", "sector_sub"), ("KBE", "sector_sub"),
    # --- retail / consumer ---
    ("XRT", "sector_sub"),
    # --- misc thematic ---
    ("PRNT", "thematic_misc"), ("HDRO", "thematic_misc"), ("HJEN", "thematic_misc"),
    ("HERO", "thematic_misc"), ("ESPO", "thematic_misc"), ("FINX", "thematic_misc"),
    ("SKYY", "thematic_misc"), ("WCLD", "thematic_misc"), ("CLOU", "thematic_misc"),
    ("FIVG", "thematic_misc"),
    # --- Karst-relevant thesis ETFs already in themes.yaml (included for
    #     completeness so the "known set" logic below is self-consistent) ---
    ("DRAM", "known_thesis_etf"), ("FOTO", "known_thesis_etf"),
    ("MAGS", "known_thesis_etf"),
]

# ---------------------------------------------------------------------------
# 2. Theme -> candidate ETF map (purpose 2: crowding-axis input).
#    [D] = themes.yaml-designated thesis_etf (already known/tracked).
#    [C] = nearest category-tag candidate identified by THIS scan (not yet a
#          designated thesis_etf -- flagged for user consideration, not auto-added).
# ---------------------------------------------------------------------------
THEME_ETF_MAP: dict[str, list[tuple[str, str]]] = {
    "memory-supercycle":              [("DRAM", "D")],
    "photonics-optical":               [("FOTO", "D")],
    "ai-power-grid":                   [("URA", "D"), ("GRID", "D"), ("UTES", "D"),
                                         ("NLR", "C"), ("URNM", "C"), ("URNJ", "C"),
                                         ("NUKZ", "C"), ("IDU", "C"), ("FUTY", "C")],
    "advanced-packaging":              [("XSD", "C"), ("SOXX", "C"), ("PSI", "C")],
    "space-satellite":                 [("NASA", "D"), ("ARKX", "C"), ("UFO", "C")],
    "rare-earth-materials":            [("REMX", "D"), ("XME", "C"), ("PICK", "C")],
    "tpu-custom-silicon":              [("CHPX", "D"), ("SMH", "C"), ("SOXX", "C"),
                                         ("XSD", "C")],
    "oil-gas-energy":                  [("XLE", "D"), ("XOP", "C"), ("OIH", "C"),
                                         ("FCG", "C")],
    "semicap-equipment":               [("SMH", "C"), ("SOXX", "C"), ("XSD", "C"),
                                         ("PSI", "C")],
    "aerospace-specialty-alloys":      [("ITA", "C"), ("PPA", "C"), ("XAR", "C"),
                                         ("PICK", "C")],
    "euv-lithography-monopoly":        [("SMH", "C"), ("SOXX", "C"), ("XSD", "C")],
    "us-solar-manufacturing":          [("TAN", "C"), ("ICLN", "C"), ("QCLN", "C")],
    "gas-compression-equipment":       [("FCG", "C"), ("XOP", "C"), ("OIH", "C")],
    "specialty-siding-pricing-power":  [("ITB", "C"), ("XHB", "C")],
    "glp1-biologics-packaging":        [("XBI", "C"), ("IHE", "C"), ("PPH", "C"),
                                         ("XPH", "C"), ("IBB", "C")],
    "mag7-hyperscaler":                [("MAGS", "D"), ("QQQ", "D")],
    "semiconductor-cycle":             [("SMH", "D"), ("QQQ", "D")],
}


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_known_sets() -> tuple[set[str], set[str]]:
    """Return (universe_yaml_tickers, all_thesis_etf_tickers)."""
    with open(UNIVERSE_YAML, "r", encoding="utf-8") as f:
        uni = yaml.safe_load(f)
    uni_tickers = {t["ticker"] for t in uni.get("tickers", [])}

    with open(THEMES_YAML, "r", encoding="utf-8") as f:
        themes = yaml.safe_load(f)
    thesis_etfs: set[str] = set()
    for _key, th in themes.get("themes", {}).items():
        for etf in th.get("thesis_etf", []) or []:
            thesis_etfs.add(etf["etf"])
    return uni_tickers, thesis_etfs


def fetch_price_volume(ticker: str) -> pd.DataFrame | None:
    """OHLCV via backtest/data.py load() (yfinance-first)."""
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            df = karst_data.load(ticker, source="yfinance", min_rows=30)
        if df is None or len(df) < 30:
            return None
        return df
    except Exception:
        return None


def compute_turnover_stats(df: pd.DataFrame) -> dict:
    d = df.copy()
    d["dollar_vol"] = d["close"] * d["volume"]
    n = len(d)
    win60 = min(60, n)
    win252 = min(252, n)
    avg60 = float(d["dollar_vol"].tail(win60).mean())
    avg252 = float(d["dollar_vol"].tail(win252).mean())
    surge = avg60 / avg252 if avg252 > 0 else float("nan")
    last_close = float(d["close"].iloc[-1])
    ret63 = float(last_close / d["close"].iloc[-min(64, n)] - 1) if n >= 5 else float("nan")
    ret252 = float(last_close / d["close"].iloc[-min(253, n)] - 1) if n >= 5 else float("nan")
    hi252 = float(d["close"].tail(win252).max())
    dist_from_high = float(last_close / hi252 - 1)
    first_date = d.index[0].date().isoformat()
    return {
        "avg_dollar_vol_60d": avg60,
        "avg_dollar_vol_252d": avg252,
        "surge_ratio": surge,
        "ret_63d": ret63,
        "ret_252d": ret252,
        "dist_from_52w_high": dist_from_high,
        "history_start": first_date,
        "n_rows": n,
    }


def fetch_aum_and_inception(ticker: str, retries: int = 2) -> dict:
    """Best-effort AUM + inception date via yfinance .info (slower / less reliable
    -- only called for the smaller candidates-of-interest subset)."""
    aum = None
    inception = None
    for attempt in range(retries):
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                t = yf.Ticker(ticker)
                info = t.info
            if info:
                aum = info.get("totalAssets")
                incep_ts = info.get("fundInceptionDate")
                if incep_ts:
                    try:
                        inception = datetime.utcfromtimestamp(int(incep_ts)).date().isoformat()
                    except Exception:
                        inception = None
            break
        except Exception:
            time.sleep(1.5)
            continue
    return {"aum": aum, "inception_yf": inception}


def months_since(date_str: str | None) -> float | None:
    if not date_str:
        return None
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return (TODAY - d).days / 30.44
    except Exception:
        return None


def main() -> None:
    log("讀 universe.yaml + themes.yaml 已知集合...")
    uni_tickers, thesis_etfs = load_known_sets()
    known_set = uni_tickers | thesis_etfs
    log(f"已知 universe.yaml tickers = {sorted(uni_tickers)}")
    log(f"已知 thesis_etf tickers = {sorted(thesis_etfs)}")

    all_tickers = sorted({t for t, _cat in UNIVERSE})
    cat_map = dict(UNIVERSE)
    log(f"掃描宇宙 = {len(all_tickers)} 隻 ETF")

    results: dict[str, dict] = {}
    failed: list[str] = []
    for i, tk in enumerate(all_tickers, 1):
        if i % 20 == 0 or i == 1:
            log(f"  ...{i}/{len(all_tickers)}  現處理 {tk}")
        df = fetch_price_volume(tk)
        if df is None:
            failed.append(tk)
            continue
        try:
            stats = compute_turnover_stats(df)
            stats["category"] = cat_map.get(tk, "?")
            results[tk] = stats
        except Exception:
            failed.append(tk)
            log(f"  計算失敗 {tk}: {traceback.format_exc(limit=1)}")
        time.sleep(0.05)

    log(f"價量抓取完成: {len(results)} 成功 / {len(failed)} 失敗")
    if failed:
        log(f"失敗清單: {failed}")

    # candidates of interest -> need AUM + inception:
    #  - theme-tagged tickers (table B/C)
    #  - anything crossing the $20M/day blind-spot bar (table A)
    theme_tickers = {t for lst in THEME_ETF_MAP.values() for t, _tag in lst}
    blind_spot_candidates = {
        tk for tk, s in results.items()
        if s["avg_dollar_vol_60d"] >= BLIND_SPOT_BAR and tk not in known_set
    }
    candidates_of_interest = (theme_tickers | blind_spot_candidates) & set(results.keys())
    log(f"抓 AUM/上市日期 = {len(candidates_of_interest)} 隻(theme-tagged + 盲點候選)")

    extra: dict[str, dict] = {}
    for i, tk in enumerate(sorted(candidates_of_interest), 1):
        log(f"  ...{i}/{len(candidates_of_interest)}  AUM/inception {tk}")
        extra[tk] = fetch_aum_and_inception(tk)
        time.sleep(0.3)

    for tk, ex in extra.items():
        results[tk].update(ex)
        # prefer history_start (from price data, always available) as inception
        # proxy when yfinance .info doesn't carry fundInceptionDate
        incep = ex.get("inception_yf") or results[tk].get("history_start")
        results[tk]["inception_effective"] = incep
        results[tk]["months_listed"] = months_since(incep)

    write_report(results, uni_tickers, thesis_etfs, known_set, failed, cat_map)
    log(f"報告已寫: {OUT_MD}")


def fmt_money(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    if v >= 1e9:
        return f"${v/1e9:.2f}B"
    if v >= 1e6:
        return f"${v/1e6:.1f}M"
    return f"${v:,.0f}"


def fmt_pct(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    return f"{v*100:+.1f}%"


def write_report(results, uni_tickers, thesis_etfs, known_set, failed, cat_map) -> None:
    lines: list[str] = []
    lines.append("# ETF 全市場成交掃描 -- 盲點發現 + 擁擠軸輸入 (2026-07-17)")
    lines.append("")
    lines.append("腳本: `backtest/experiments/exp_etf_turnover_scan.py`｜"
                 "數據源: `backtest/data.py load()`(yfinance-first)+ yfinance `.info`(AUM/上市日)。")
    lines.append("")
    lines.append("## 0. 方法論")
    lines.append("")
    lines.append(f"- 掃描宇宙:{len(cat_map)} 隻美國上市 ETF(hardcode,見腳本 `UNIVERSE`,分 broad/"
                 "sector/thematic_*/factor/international/commodity 等類別)。**刻意排除**槓桿/反向"
                 "產品(2x/3x Bull/Bear/Daily)——呢啲嘅成交量係衍生品交易活動,唔係主題資金流訊號,"
                 "混入會污染盲點表同擁擠表。")
    lines.append(f"- 流動性門檻:60 日平均日成交金額 ≥ **${LIQ_BAR/1e6:.0f}M** 先算「夠 turnover」。"
                 "呢個門檻對齊 themes.yaml 現有 ai-power-grid UTES/GRID 衛星倉位先例(~$11-15M/日已"
                 "夠用戶用 $10-15k 倉位)——低於呢個量級,單一交易已經郁到價,倉位天生受限,同 thesis "
                 "本身好唔好無關。敏感度:若門檻收緊到 $10M,C 表(死場)會多幾隻邊緣名;若放寬到 $2M,"
                 "A 表(盲點)可能多幾隻細價主題 ETF,但雜訊(bid-ask 闊、追蹤誤差大)同步上升。")
    lines.append(f"- 盲點門檻:成交 ≥ **${BLIND_SPOT_BAR/1e6:.0f}M**/日 **且** 唔喺 `universe.yaml`(現時"
                 f"只有 {sorted(uni_tickers)})**亦**唔係 `themes.yaml` 任何 theme 嘅 `thesis_etf`"
                 f"(現有 {len(thesis_etfs)} 隻:{sorted(thesis_etfs)})。")
    lines.append(f"- 新上市定義:成立 ≤ **{NEW_MONTHS} 個月**。上市日優先用 yfinance `.info."
                 "fundInceptionDate`,拎唔到就退而求其次用價量歷史第一個交易日做 proxy(保守;真上市日"
                 "可能更早,唔會令「新」被高估)。")
    lines.append(f"- 失敗誠實列出(yfinance 落唔到數據),唔靜靜跳過:{failed if failed else '(全部成功)'}")
    lines.append("")

    # ---- Table A: blind spot ----
    lines.append("## A. 盲點表 -- 成交夠大但唔喺 universe/thesis_etf 入面")
    lines.append("")
    lines.append(f"門檻:60d 平均日成交 ≥ ${BLIND_SPOT_BAR/1e6:.0f}M,且唔喺已知集合"
                 f"({sorted(known_set)})。")
    lines.append("")
    a_rows = []
    for tk, s in results.items():
        if tk in known_set:
            continue
        if s.get("avg_dollar_vol_60d", 0) >= BLIND_SPOT_BAR:
            a_rows.append((tk, s))
    a_rows.sort(key=lambda x: -x[1]["avg_dollar_vol_60d"])
    if a_rows:
        lines.append("| Ticker | 類別 | 60d 均量$ | 252d 均量$ | 激增比 | 63d 報酬 | 距52週高 | AUM | 上市 |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for tk, s in a_rows:
            ml = s.get("months_listed")
            ml_s = f"{ml:.0f}mo" if ml is not None else "N/A"
            lines.append(
                f"| {tk} | {s['category']} | {fmt_money(s['avg_dollar_vol_60d'])} | "
                f"{fmt_money(s['avg_dollar_vol_252d'])} | {s['surge_ratio']:.2f}x | "
                f"{fmt_pct(s['ret_63d'])} | {fmt_pct(s['dist_from_52w_high'])} | "
                f"{fmt_money(s.get('aum'))} | {ml_s} |"
            )
    else:
        lines.append("(本次掃描宇宙內冇發現符合門檻嘅盲點;注意呢個結果受限於 hardcode 嘅 185 隻"
                     "掃描清單,唔係全市場 3000+ 隻 ETF 嘅完整普查。)")
    lines.append("")

    # ---- Table B: crowding signal ----
    lines.append("## B. 擁擠訊號表 -- 17 個 theme 對口主題 ETF 嘅「新上市/成交激增」讀數")
    lines.append("")
    lines.append("D = themes.yaml 已登記 thesis_etf;C = 本掃描找到嘅同類候選(未登記,僅供參考,"
                 f"唔自動加入 thesis)。中招定義:激增比 > 1.5x **或** 上市 ≤ {NEW_MONTHS} 個月。")
    lines.append("")
    lines.append("| Theme | ETF | D/C | 60d 均量$ | 激增比 | 上市 | AUM | 中招? |")
    lines.append("|---|---|---|---|---|---|---|---|")
    theme_hits: dict[str, list[str]] = {}
    for theme, lst in THEME_ETF_MAP.items():
        for tk, tag in lst:
            s = results.get(tk)
            if s is None:
                lines.append(f"| {theme} | {tk} | {tag} | N/A | N/A | N/A | N/A | 數據缺失 |")
                continue
            ml = s.get("months_listed")
            surge = s.get("surge_ratio", float("nan"))
            is_new = (ml is not None and ml <= NEW_MONTHS)
            is_surge = (not np.isnan(surge) and surge > 1.5)
            hit = is_new or is_surge
            if hit:
                theme_hits.setdefault(theme, []).append(
                    f"{tk}({'新上市' if is_new else ''}{'+' if is_new and is_surge else ''}"
                    f"{'激增' if is_surge else ''})")
            ml_s = f"{ml:.0f}mo" if ml is not None else "N/A"
            lines.append(
                f"| {theme} | {tk} | {tag} | {fmt_money(s['avg_dollar_vol_60d'])} | "
                f"{surge:.2f}x | {ml_s} | {fmt_money(s.get('aum'))} | "
                f"{'**是**' if hit else '否'} |"
            )
    lines.append("")
    lines.append("**中招 theme 清單(擁擠軸若接入呢個輸入,讀數會變嘅):**")
    lines.append("")
    if theme_hits:
        for theme, hits in theme_hits.items():
            lines.append(f"- **{theme}**: {', '.join(hits)}")
    else:
        lines.append("(本次讀數冇 theme 中招 -- 即係話依家 17 個 theme 對口 ETF 都冇出現「新上市/"
                     "資金激增」嘅擁擠訊號,巿況相對平靜。)")
    lines.append("")

    # ---- Table C: dead zone ----
    lines.append("## C. 死場表 -- 主題 ETF 有概念冇資金(60d 均量$ < 門檻)")
    lines.append("")
    c_rows = []
    seen = set()
    for theme, lst in THEME_ETF_MAP.items():
        for tk, tag in lst:
            if tk in seen:
                continue
            seen.add(tk)
            s = results.get(tk)
            if s and s.get("avg_dollar_vol_60d", 1e18) < LIQ_BAR:
                c_rows.append((tk, theme, tag, s))
    c_rows.sort(key=lambda x: x[3]["avg_dollar_vol_60d"])
    if c_rows:
        lines.append("| Ticker | 對應 Theme | D/C | 60d 均量$ | AUM | 上市 |")
        lines.append("|---|---|---|---|---|---|")
        for tk, theme, tag, s in c_rows:
            ml = s.get("months_listed")
            ml_s = f"{ml:.0f}mo" if ml is not None else "N/A"
            lines.append(f"| {tk} | {theme} | {tag} | {fmt_money(s['avg_dollar_vol_60d'])} | "
                         f"{fmt_money(s.get('aum'))} | {ml_s} |")
    else:
        lines.append("(冇主題 ETF 落入死場 -- 全部候選都夠 $5M/日流動性。)")
    lines.append("")

    # ---- judgement ----
    lines.append("## 判詞")
    lines.append("")
    lines.append("### (i) 我哋真係漏咗啲乜")
    lines.append("")
    if a_rows:
        for tk, s in a_rows[:5]:
            lines.append(f"- **{tk}**({s['category']},{fmt_money(s['avg_dollar_vol_60d'])}/日): "
                         "見下段業務判詞,值唔值得跟進見備註。")
    else:
        lines.append("- 本次掃描冇發現盲點——但呢個結論嘅可信度受限於 185 隻嘅 hardcode 清單,"
                     "唔係全市場普查,建議睇下面「未解/風險」。")
    lines.append("")
    lines.append("### (ii) 擁擠軸點讀")
    lines.append("")
    lines.append("見上表 B 中招清單。表 C 死場方向相反——有主題概念但資金未跟,係「太早」而非"
                 "「太擠」嘅訊號,兩者唔應該用同一把尺判斷 timing。")
    lines.append("")
    lines.append("### (iii) 定期跑頻率建議")
    lines.append("")
    lines.append("建議**季度**跑一次(同 discovery radar 40 候選覆核節奏對齊):ETF 上市/資金流係")
    lines.append("低頻結構性事件(對比 daily VIX/RS 呢啲高頻訊號),月度跑太密、年度跑太疏(24 個月")
    lines.append("嘅「新」窗口可能漏一整個上市潮)。")
    lines.append("")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
