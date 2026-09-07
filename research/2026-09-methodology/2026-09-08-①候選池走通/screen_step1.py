"""KARST-184 第一步:相對 SPY 大跌候選初篩。

宇宙:data/universe/entities.parquet(KARST-167 建,5,257 家 SEC 申報實體,含股數/市值/SIC)。
價格:yfinance,2025-10-01 至 2026-09-05(200 日線需要約一年)。
窗口:2026-06-01(或之後第一個交易日)至 2026-09-04。

輸出:screen_step1_raw.csv(全部有價股票的窗口表現)
      screen_step1_shortlist.csv(相對 SPY 跌逾 25% 且過流動性/市值閘)
"""
import sys, time, math
import pandas as pd
import numpy as np
import yfinance as yf

ROOT = r"C:\projects\Karst"
OUT = r"C:\projects\Karst\research\2026-09-methodology\2026-09-08-①候選池走通"

START = "2025-10-01"
END = "2026-09-06"
WIN_START = pd.Timestamp("2026-06-01")
WIN_END = pd.Timestamp("2026-09-04")

ent = pd.read_parquet(ROOT + r"\data\universe\entities.parquet")
ent = ent[ent["primary_ticker"].notna() & (ent["filing_status"] == "active")]
# 排除明顯的 ETP / 市值不合理
ent = ent[~ent["etp_suspect"].fillna(False) & ~ent["mcap_implausible"].fillna(False)]
tickers = sorted(set(t for t in ent["primary_ticker"] if isinstance(t, str) and t.isalpha() and len(t) <= 5))
print(f"universe tickers: {len(tickers)}", flush=True)

# --- SPY 基準 ---
spy = yf.download("SPY", start=START, end=END, auto_adjust=True, progress=False)
spy_close = spy["Close"]["SPY"] if isinstance(spy.columns, pd.MultiIndex) else spy["Close"]


def window_ret(s: pd.Series):
    s = s.dropna()
    if s.empty:
        return None, None, None
    a = s[s.index >= WIN_START]
    b = s[s.index <= WIN_END]
    if a.empty or b.empty:
        return None, None, None
    p0 = a.iloc[0]
    p1 = b.iloc[-1]
    if not (p0 > 0):
        return None, None, None
    return p0, p1, p1 / p0 - 1.0


spy_p0, spy_p1, spy_ret = window_ret(spy_close)
print(f"SPY {spy_p0:.2f} -> {spy_p1:.2f} = {spy_ret:+.2%}", flush=True)

rows = []
CH = 150
for i in range(0, len(tickers), CH):
    chunk = tickers[i:i + CH]
    for attempt in range(3):
        try:
            df = yf.download(chunk, start=START, end=END, auto_adjust=True,
                             progress=False, threads=True, group_by="column")
            break
        except Exception as e:  # noqa
            print(f"  retry {attempt} {e}", flush=True)
            time.sleep(5)
    else:
        continue
    if df is None or df.empty:
        continue
    close = df["Close"]
    vol = df["Volume"] if "Volume" in df.columns.get_level_values(0) else None
    for t in chunk:
        if t not in close.columns:
            continue
        s = close[t].dropna()
        if len(s) < 120:
            continue
        p0, p1, r = window_ret(s)
        if r is None:
            continue
        ma200 = s.rolling(200, min_periods=150).mean()
        ma200_last = ma200.iloc[-1] if not math.isnan(ma200.iloc[-1]) else np.nan
        # 200 日線斜率:對比 40 個交易日前
        ma200_prev = ma200.iloc[-41] if len(ma200) > 41 else np.nan
        dv = np.nan
        if vol is not None and t in vol.columns:
            v = vol[t].dropna()
            j = s.reindex(v.index).ffill()
            dvs = (v * j).dropna().tail(60)
            if len(dvs) > 20:
                dv = float(dvs.median())
        rows.append(dict(
            ticker=t, p0=float(p0), p1=float(p1), ret=float(r),
            rel_spy=float(r - spy_ret),
            ma200=float(ma200_last) if ma200_last == ma200_last else np.nan,
            px_vs_ma200=float(p1 / ma200_last - 1) if ma200_last == ma200_last and ma200_last > 0 else np.nan,
            ma200_slope_40d=float(ma200_last / ma200_prev - 1) if (ma200_prev == ma200_prev and ma200_prev > 0) else np.nan,
            med_dollar_vol_60d=dv,
        ))
    print(f"  {i + len(chunk)}/{len(tickers)} done, rows={len(rows)}", flush=True)

raw = pd.DataFrame(rows)
meta = ent[["primary_ticker", "name", "entity_id", "sic", "sic_description",
            "approx_mcap_usd", "shares_outstanding"]].rename(columns={"primary_ticker": "ticker"})
raw = raw.merge(meta.drop_duplicates("ticker"), on="ticker", how="left")
raw["mcap_now_usd"] = raw["shares_outstanding"] * raw["p1"]
raw.to_csv(OUT + r"\screen_step1_raw.csv", index=False, encoding="utf-8")
print(f"raw rows: {len(raw)}", flush=True)

short = raw[(raw["rel_spy"] <= -0.25)
            & (raw["mcap_now_usd"] >= 3e8)
            & (raw["med_dollar_vol_60d"] >= 3e6)].copy()
short = short.sort_values("rel_spy")
short.to_csv(OUT + r"\screen_step1_shortlist.csv", index=False, encoding="utf-8")
print(f"shortlist rows: {len(short)}", flush=True)
print(short.head(40)[["ticker", "name", "rel_spy", "mcap_now_usd", "med_dollar_vol_60d", "px_vs_ma200"]].to_string(), flush=True)
