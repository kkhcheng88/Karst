"""KARST-125 follow-up: defeatbeta exposes a `stock_earning_calendar` table and a
Ticker.calendar() accessor. Does either carry an analyst EPS estimate?

Also enumerates every table the Hugging Face / DuckDB layer actually holds, so
the report can state the inventory as fact rather than inference.

Run: set PYTHONUTF8=1 && python probe_defeatbeta_calendar.py
"""
import os
import traceback

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
log_lines = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log_lines.append(s)


def show(obj, label):
    import pandas as pd
    df = obj
    if hasattr(obj, "get_data"):
        try:
            df = obj.get_data()
        except Exception:
            pass
    if isinstance(df, pd.DataFrame):
        log(f"\n[{label}] shape={df.shape}")
        log("  columns:", list(df.columns))
        log(df.head(12).to_string())
        p = os.path.join(OUT, f"defeatbeta_{label}.csv")
        df.to_csv(p, index=False, encoding="utf-8")
        log("  saved ->", p)
        return df
    log(f"\n[{label}] -> {type(df)}: {str(df)[:600]}")
    return None


def main():
    from defeatbeta_api.data.ticker import Ticker
    from defeatbeta_api.client.duckdb_client import get_duckdb_client

    # 1. Full table inventory straight off the DuckDB/HF layer
    try:
        cli = get_duckdb_client()
        log("duckdb client:", type(cli))
        for meth in ("query", "execute", "sql"):
            if hasattr(cli, meth):
                log("  has method:", meth)
        try:
            r = cli.query("SELECT 1")
            log("  query() works:", r)
        except Exception as e:
            log("  query(SELECT 1) failed:", str(e)[:200])
    except Exception as e:
        log("duckdb client failed:", str(e)[:300])

    # 2. The table-name constants the package ships (these ARE the inventory)
    try:
        from defeatbeta_api.util import util
        log("\n--- util names ---")
        log([n for n in dir(util) if not n.startswith("_")])
    except Exception as e:
        log("util import failed:", str(e)[:200])

    try:
        import defeatbeta_api.data.ticker as tm
        tables = [getattr(tm, n) for n in dir(tm)
                  if n.startswith("stock_") or n in ("sp500_cagr_returns_rolling",
                                                     "exchange_rate")]
        log("\n--- table constants declared in ticker.py ---")
        for n in sorted(dir(tm)):
            v = getattr(tm, n)
            if isinstance(v, str) and not n.startswith("_") and "_" in v:
                log(f"  {n} = {v}")
    except Exception as e:
        log("table const scan failed:", str(e)[:200])

    # 3. The calendar accessor on real tickers
    for t in ("AAPL", "AXTI", "CROX"):
        log(f"\n================ {t} ================")
        tk = Ticker(t)
        for meth in ("calendar", "earning_calendar"):
            if hasattr(tk, meth):
                try:
                    show(getattr(tk, meth)(), f"{t}_{meth}")
                except Exception as e:
                    log(f"[{t}.{meth}] FAILED: {type(e).__name__}: {str(e)[:250]}")
        # trailing EPS depth, for the record
        try:
            df = show(tk.ttm_eps(), f"{t}_ttm_eps")
        except Exception as e:
            log(f"[{t}.ttm_eps] FAILED: {str(e)[:200]}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log(traceback.format_exc())
    with open(os.path.join(OUT, "defeatbeta_calendar.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    print("\nlog -> out/defeatbeta_calendar.txt")
