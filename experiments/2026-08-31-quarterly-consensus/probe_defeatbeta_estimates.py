"""KARST-125: does defeatbeta-api carry any earnings-estimate / analyst-consensus table?

Pure reconnaissance. Lists every table the library exposes, then tries every
estimate-looking accessor on a couple of tickers and dumps the schema + depth.

Run:  set PYTHONUTF8=1 && python probe_defeatbeta_estimates.py
Output: out/defeatbeta_inventory.txt  (+ any sample CSVs)
"""
import os
import sys
import traceback

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

log_lines = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log_lines.append(s)


def main():
    import defeatbeta_api
    from defeatbeta_api.data.ticker import Ticker

    log("defeatbeta_api version:", getattr(defeatbeta_api, "__version__", "?"))
    log("module path:", defeatbeta_api.__file__)

    # 1. What tables does the package know about?
    try:
        from defeatbeta_api.data import huggingface_client as hc
        log("\n--- huggingface_client symbols ---")
        log([n for n in dir(hc) if not n.startswith("_")])
    except Exception as e:
        log("huggingface_client import failed:", e)

    try:
        from defeatbeta_api.client.duckdb_conf import Configuration  # noqa
    except Exception:
        pass

    # Table name constants
    try:
        from defeatbeta_api.util import util  # noqa
    except Exception:
        pass
    try:
        import defeatbeta_api.data.ticker as tmod
        log("\n--- Ticker public methods ---")
        methods = [n for n in dir(Ticker) if not n.startswith("_")]
        for m in methods:
            log("  ", m)
        log("\n--- module-level names in ticker.py ---")
        log([n for n in dir(tmod) if not n.startswith("_")][:80])
    except Exception as e:
        log("introspection failed:", e)

    # Table constants live in defeatbeta_api.data.const usually
    for modname in ("defeatbeta_api.data.const", "defeatbeta_api.util.const",
                    "defeatbeta_api.client.const", "defeatbeta_api.const"):
        try:
            m = __import__(modname, fromlist=["*"])
            consts = {n: getattr(m, n) for n in dir(m)
                      if not n.startswith("_") and isinstance(getattr(m, n), str)}
            if consts:
                log(f"\n--- string constants in {modname} ---")
                for k, v in sorted(consts.items()):
                    log(f"  {k} = {v}")
        except Exception:
            pass

    # 2. Try estimate-looking accessors on real tickers
    tickers = ["AAPL", "AXTI"]
    estimate_like = [m for m in dir(Ticker)
                     if not m.startswith("_")
                     and any(k in m.lower() for k in
                             ("estimat", "analyst", "forecast", "consensus",
                              "eps", "earning", "target", "revision", "guidance"))]
    log("\n--- estimate-looking accessors ---")
    log(estimate_like)

    for t in tickers:
        log(f"\n================ {t} ================")
        try:
            tk = Ticker(t)
        except Exception as e:
            log("Ticker() failed:", e)
            continue
        for m in estimate_like:
            try:
                fn = getattr(tk, m)
                if not callable(fn):
                    continue
                res = fn()
                df = getattr(res, "get_data", None)
                obj = df() if callable(df) else res
                import pandas as pd
                if isinstance(obj, pd.DataFrame):
                    log(f"\n[{m}] DataFrame shape={obj.shape}")
                    log("  columns:", list(obj.columns))
                    log(obj.head(8).to_string())
                    fn_out = os.path.join(OUT, f"defeatbeta_{t}_{m}.csv")
                    obj.to_csv(fn_out, index=False, encoding="utf-8")
                    log("  saved ->", fn_out)
                else:
                    log(f"\n[{m}] -> {type(obj)} {str(obj)[:400]}")
            except Exception as e:
                log(f"\n[{m}] FAILED: {type(e).__name__}: {str(e)[:200]}")

    # 3. Raw table listing straight off the DuckDB/HF layer
    try:
        from defeatbeta_api.data.ticker import Ticker as T2
        tk = T2("AAPL")
        conn = None
        for attr in ("conn", "_conn", "duckdb_client", "client"):
            if hasattr(tk, attr):
                conn = getattr(tk, attr)
                break
        log("\n--- duckdb handle:", type(conn))
        if conn is not None and hasattr(conn, "query"):
            try:
                r = conn.query("SHOW TABLES")
                log(r)
            except Exception as e:
                log("SHOW TABLES failed:", e)
    except Exception as e:
        log("raw layer probe failed:", e)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log(traceback.format_exc())
    with open(os.path.join(OUT, "defeatbeta_inventory.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    print("\nlog ->", os.path.join(OUT, "defeatbeta_inventory.txt"))
