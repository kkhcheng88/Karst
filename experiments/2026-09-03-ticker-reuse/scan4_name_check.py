"""KARST-165 唯讀掃描第四輪:代號→CIK 對照表本身是不是接錯了公司。

做法:每個代號有兩個獨立來源的公司名——
  ① yfinance 的 shortName / longName(KARST-152、KARST-157 抓的 ticker_meta)
  ② SEC 的 CIK 名冊(data/sec/cik-lookup-data.txt,一個 CIK 可以有多個曾用名)
把 company_tickers.json 給的 CIK 拿去 SEC 名冊查名,與 yfinance 的名比。
一個字都對不上 = 這個代號現時接到的 CIK 很可能不是價格序列那家公司。
"""
import json
import pathlib
import re

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
OUT = REPO / "experiments" / "2026-09-03-ticker-reuse" / "out"
OUT.mkdir(parents=True, exist_ok=True)

STOP = {"inc", "corp", "corporation", "co", "company", "the", "ltd", "limited",
        "plc", "holdings", "holding", "group", "llc", "lp", "sa", "nv", "ag",
        "class", "common", "stock", "new", "international", "industries",
        "technologies", "technology", "systems", "solutions", "and", "of",
        "&", "-", "l", "p", "a", "b", "c", "trust", "fund", "incorporated"}


def toks(name: str) -> set:
    s = re.sub(r"[^a-z0-9 ]", " ", str(name).lower())
    return {w for w in s.split() if w and w not in STOP and len(w) > 1}


meta = {}
for p in ["experiments/2026-09-02-narrative-layers/out/ticker_meta.json",
          "experiments/2026-09-02-narrative-layers-v2/out/ticker_meta_new.json"]:
    f = REPO / p
    if f.exists():
        meta.update(json.loads(f.read_text(encoding="utf-8")))
print("yfinance 有名的代號:", len(meta))

tick2cik = json.loads((REPO / "data/sec/company_tickers.json").read_text(encoding="utf-8"))
wanted = {str(int(tick2cik[t])) for t in meta if t in tick2cik}

names: dict[str, list[str]] = {}
with (REPO / "data/sec/cik-lookup-data.txt").open(encoding="latin-1") as fh:
    for line in fh:
        parts = [p for p in line.rstrip("\n").split(":") if p != ""]
        if len(parts) >= 2 and parts[-1].isdigit():
            c = str(int(parts[-1]))
            if c in wanted:
                names.setdefault(c, []).append(":".join(parts[:-1]))
print("SEC 名冊查得到名的 CIK:", len(names), "/", len(wanted))

rows = []
for t, m in sorted(meta.items()):
    cik = tick2cik.get(t)
    if not cik:
        rows.append({"ticker": t, "cik": None, "yf_name": m.get("longName") or m.get("shortName"),
                     "sec_names": None, "overlap": None, "flag": "no_cik"})
        continue
    cik = str(int(cik))
    yf = f"{m.get('shortName') or ''} {m.get('longName') or ''}"
    yt = toks(yf)
    secn = names.get(cik, [])
    best, bestname = 0, ""
    for n in secn:
        ov = len(yt & toks(n))
        if ov > best:
            best, bestname = ov, n
    rows.append({
        "ticker": t, "cik": cik,
        "yf_name": (m.get("longName") or m.get("shortName") or "").strip(),
        "sec_names": " | ".join(secn[:4]),
        "best_sec_name": bestname,
        "overlap": best,
        "yf_tokens": len(yt),
        "flag": ("no_sec_name" if not secn else ("MISMATCH" if best == 0 else "ok")),
    })
df = pd.DataFrame(rows)
df.to_csv(OUT / "ticker_cik_name_check.csv", index=False, encoding="utf-8")
print(df["flag"].value_counts().to_string())
print("\n=== 一個字都對不上的代號 ===")
bad = df[df.flag == "MISMATCH"].sort_values("ticker")
pd.set_option("display.width", 250, "display.max_colwidth", 70)
print(bad[["ticker", "cik", "yf_name", "sec_names"]].to_string(index=False))
