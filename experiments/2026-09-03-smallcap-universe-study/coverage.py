"""KARST-162 §1:候選宇宙定義對 KARST-160 五年窗 138 家十倍股名單的 t0 覆蓋率。

規則見同目錄 RULES.md(跑數之前寫好)。只讀既有位置的原料,不另存副本(D-134),不寫入 data/。
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

NAMES = os.path.join(ROOT, "experiments/2026-09-02-tenbagger-scan/out/tenbagger_names.csv")
CELLS = os.path.join(ROOT, "experiments/2026-09-02-tenbagger-scan/out/t0_cells.parquet")
DAILY = os.path.join(ROOT, "experiments/2026-09-02-timing-sweep/data/daily_close.parquet")
NEW = os.path.join(ROOT, "experiments/2026-09-02-narrative-layers-v2/data/new_close.parquet")
SPLITS = os.path.join(ROOT, "experiments/2026-09-02-fourpiece-test/data/splits.parquet")
PANEL = os.path.join(ROOT, "experiments/2026-09-02-panel-scale-fix/out/panel_monthly_v2.parquet")
TICKERS = os.path.join(ROOT, "data/sec/company_tickers.json")
FRAMES = os.path.join(OUT, "sec_cover_shares.json")

# --- RULES.md 第三節,跑數前凍結 -------------------------------------------------
UNIVERSES = {
    "U1 羅素2000近似(3億–50億)": (3e8, 5e9),
    "U2 全美小型股(<50億)": (0.0, 5e9),
    "U3 自定義(2億–100億)": (2e8, 1e10),
}


def load_prices():
    a = pd.read_parquet(DAILY)
    b = pd.read_parquet(NEW)
    return a, b


def price_on(a, b, ticker, day):
    for df in (a, b):
        if ticker in df.columns:
            s = df[ticker].dropna()
            s = s[s.index <= day]
            if len(s):
                return float(s.iloc[-1])
    return np.nan


def main():
    names = pd.read_csv(NAMES, encoding="utf-8-sig")
    five = names[names.horizon == "5y"].copy()
    five["t0"] = pd.to_datetime(five["t0"])
    assert len(five) == 138, len(five)

    cells = pd.read_parquet(CELLS)
    cells["t0"] = pd.to_datetime(cells["t0"])

    daily, new = load_prices()

    # --- 層一:面板直接有 mcap --------------------------------------------------
    key = cells.set_index(["ticker", "t0"])
    five["mcap"] = np.nan
    five["mcap_src"] = "未知"
    for i, r in five.iterrows():
        try:
            v = key.loc[(r.ticker, r.t0), "mcap"]
        except KeyError:
            continue
        v = float(v) if np.ndim(v) == 0 else float(np.ravel(v)[0])
        if np.isfinite(v):
            five.at[i, "mcap"] = v
            five.at[i, "mcap_src"] = "panel"

    # --- 層二:同一家 t0 之前最近一格的 shares_adj × t0 價格(向前補,上限 24 個月) --
    sh = cells[["ticker", "t0", "shares_adj"]].dropna().sort_values("t0")
    for i, r in five[five.mcap_src == "未知"].iterrows():
        g = sh[(sh.ticker == r.ticker) & (sh.t0 <= r.t0)]
        if not len(g):
            continue
        last = g.iloc[-1]
        if (r.t0 - last.t0).days > 730:
            continue
        px = price_on(daily, new, r.ticker, r.t0)
        if np.isfinite(px):
            five.at[i, "mcap"] = float(last.shares_adj) * px
            five.at[i, "mcap_src"] = "panel_ffill"

    # --- 層三:證監會 frames 封面頁股數(未還原拆股)× t0 未還原價格 ---------------
    # 未還原價格 = 還原價 × (t0 之後所有拆股比例的連乘)
    splits = pd.read_parquet(SPLITS)
    if "symbol" not in splits.columns:
        splits = splits.reset_index()
    scol = "symbol" if "symbol" in splits.columns else splits.columns[0]
    dcol = "date" if "date" in splits.columns else splits.columns[1]
    rcol = "ratio" if "ratio" in splits.columns else splits.columns[2]
    splits[dcol] = pd.to_datetime(splits[dcol], utc=True).dt.tz_localize(None)

    t2c = {}
    if os.path.exists(TICKERS):
        with open(TICKERS, encoding="utf-8") as f:
            j = json.load(f)
        # 倉內這一份已預處理成 {ticker: "0001045810"};原始證監會格式是 {idx: {...}}
        for k, v in (j.items() if isinstance(j, dict) else []):
            if isinstance(v, str):
                t2c[str(k).upper()] = int(v)
            elif isinstance(v, dict):
                t2c[str(v["ticker"]).upper()] = int(v["cik_str"])
    panel = pd.read_parquet(PANEL, columns=["ticker", "cik"]).drop_duplicates()
    for _, r in panel.iterrows():
        t2c.setdefault(str(r.ticker).upper(), int(r.cik))

    frames = {}
    if os.path.exists(FRAMES):
        with open(FRAMES, encoding="utf-8") as f:
            frames = {int(k): v for k, v in json.load(f).items()}
    # A-041 同一種病:證監會封面頁股數本身有以千/百萬為單位的錯格
    # (實例:ALK 2010 報 35,831,543,000,翌年 35,453,202)。
    # 照 panel v2 的量級錨規則修:偏離自身 log10 中位數 ≥30 倍、且落在某個 10^k 的 ±0.35 之內,除以 10^k。
    n_fixed = 0
    for cik, ys in frames.items():
        vals = {y: v for y, v in ys.items() if v and v > 0}
        if len(vals) < 3:
            continue
        anchor = float(np.median([np.log10(v) for v in vals.values()]))
        for y, v in list(vals.items()):
            dev = np.log10(v) - anchor
            if abs(dev) >= np.log10(30):
                k = round(dev)
                if k != 0 and abs(dev - k) <= 0.35:
                    frames[cik][y] = v / (10.0**k)
                    n_fixed += 1
    # 第二道:量級錨會被拆股拉歪(實例:ALK 兩次一拆二,錨被抬高,2010 那格逃過第一道)。
    # 補一條鄰年比對——與時間上最接近的另一年相差 1,000 倍或以上(且落在 10^k 的 ±0.35),
    # 即除以 10^k。門檻設在 |k| ≥ 3 是刻意的:一千倍以上的跳動只可能是「以千為單位」的
    # 申報錯誤,不可能是真的公司行動(一拆一千的反向拆股不存在)。
    n_fixed2 = 0
    for cik, ys in frames.items():
        yy = sorted((int(y), v) for y, v in ys.items() if v and v > 0)
        if len(yy) < 2:
            continue
        for idx, (y, v) in enumerate(yy):
            nb = yy[idx + 1][1] if idx == 0 else yy[idx - 1][1]
            dev = np.log10(v) - np.log10(nb)
            k = round(dev)
            if abs(k) >= 3 and abs(dev - k) <= 0.35:
                frames[cik][str(y)] = v / (10.0**k)
                frames[cik][y] = v / (10.0**k)
                n_fixed2 += 1
    print(f"封面頁股數量級修正格數:量級錨 {n_fixed}、鄰年比對 {n_fixed2}")

    for i, r in five[five.mcap_src == "未知"].iterrows():
        cik = t2c.get(str(r.ticker).upper())
        if cik is None or cik not in frames:
            continue
        yrs = {int(y): v for y, v in frames[cik].items()}
        if not yrs:
            continue
        past = [y for y in yrs if y <= r.t0.year]
        if past:
            yr, tag = max(past), "sec_frames"
        else:
            yr, tag = min(yrs), "sec_frames(含事後)"
        if abs(r.t0.year - yr) > 3:
            continue
        px_adj = price_on(daily, new, r.ticker, r.t0)
        if not np.isfinite(px_adj):
            continue
        fut = splits[(splits[scol] == r.ticker) & (splits[dcol] > r.t0)]
        factor = float(np.prod(fut[rcol].values)) if len(fut) else 1.0
        five.at[i, "mcap"] = float(yrs[yr]) * px_adj * factor
        five.at[i, "mcap_src"] = f"{tag}({yr})"

    # --- 層四:時間上最接近的股數(可以在 t0 之後,含事後資訊)---------------------
    # 只用於「這家公司在 t0 那刻有多大」這個描述性問題,不可用於任何訊號。
    pshare = pd.read_parquet(PANEL, columns=["ticker", "month_end", "diluted_shares"]).dropna()
    pshare["month_end"] = pd.to_datetime(pshare["month_end"])
    sf_map = cells.dropna(subset=["sf"]).groupby("ticker")["sf"].median()
    pool = pd.concat(
        [
            sh.rename(columns={"t0": "d", "shares_adj": "s"})[["ticker", "d", "s"]],
            pshare.assign(
                s=lambda x: x.diluted_shares
                * x.ticker.map(sf_map).fillna(1.0)
            ).rename(columns={"month_end": "d"})[["ticker", "d", "s"]],
        ]
    )
    for i, r in five[five.mcap_src == "未知"].iterrows():
        g = pool[pool.ticker == r.ticker]
        if not len(g):
            continue
        gap = (g.d - r.t0).abs()
        if gap.min() > pd.Timedelta(days=1460):
            continue
        s = float(g.loc[gap.idxmin(), "s"])
        px = price_on(daily, new, r.ticker, r.t0)
        if np.isfinite(px) and s > 0:
            five.at[i, "mcap"] = s * px
            five.at[i, "mcap_src"] = "nearest(含事後)"

    # --- 覆蓋率 ------------------------------------------------------------------
    known = five.mcap.notna()
    res = []
    for label, (lo, hi) in UNIVERSES.items():
        inside = known & (five.mcap >= lo) & (five.mcap < hi)
        res.append(
            {
                "宇宙": label,
                "市值下限": lo,
                "市值上限": hi,
                "命中家數": int(inside.sum()),
                "有市值家數": int(known.sum()),
                "覆蓋率下限(未知當作不在)": round(inside.sum() / 138, 4),
                "覆蓋率上限(未知當作在)": round((inside.sum() + (~known).sum()) / 138, 4),
                "有市值者之中的比例": round(inside.sum() / max(known.sum(), 1), 4),
            }
        )

    # U0 對照:t0 已經是標普成分的比例(現役宇宙的骨幹)
    in_idx = five.merge(
        cells[["ticker", "t0", "in_index"]], on=["ticker", "t0"], how="left"
    )["in_index"]
    res.insert(
        0,
        {
            "宇宙": "U0 現役骨幹:t0 時已是標普成分",
            "市值下限": None,
            "市值上限": None,
            "命中家數": int((in_idx == True).sum()),  # noqa: E712
            "有市值家數": int(in_idx.notna().sum()),
            "覆蓋率下限(未知當作不在)": round((in_idx == True).sum() / 138, 4),  # noqa: E712
            "覆蓋率上限(未知當作在)": None,
            "有市值者之中的比例": None,
        },
    )

    rdf = pd.DataFrame(res)
    rdf.to_csv(os.path.join(OUT, "universe_coverage.csv"), index=False, encoding="utf-8-sig")

    five_out = five[
        ["ticker", "t0", "t0_price", "multiple", "mcap", "mcap_src", "宇宙分段", "t0_year"]
    ].sort_values("mcap")
    for label, (lo, hi) in UNIVERSES.items():
        five_out[label] = ((five.mcap >= lo) & (five.mcap < hi)).values
    five_out.to_csv(os.path.join(OUT, "tenbagger_t0_mcap.csv"), index=False, encoding="utf-8-sig")

    q = five.loc[known, "mcap"].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9])
    summary = {
        "n_names": 138,
        "n_mcap_known": int(known.sum()),
        "src_mix": five.mcap_src.value_counts().to_dict(),
        "mcap_quantiles_usd": {k: (None if pd.isna(v) else float(v)) for k, v in q.items()},
        "unknown_tickers": sorted(five.loc[~known, "ticker"].tolist()),
    }
    with open(os.path.join(OUT, "coverage_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(rdf.to_string(index=False))
    print()
    print("市值來源分佈:", summary["src_mix"])
    print("有市值:", summary["n_mcap_known"], "/138")
    print("市值分位(百萬美元):", {k: (None if v is None else round(v / 1e6)) for k, v in summary["mcap_quantiles_usd"].items()})
    print("未知:", summary["unknown_tickers"])


if __name__ == "__main__":
    main()
