# -*- coding: utf-8 -*-
"""接口回測前置:查價量可用性(不落結論,只查覆蓋)。
輸出:_probe_data.csv / 主控台摘要。"""
import os
import pandas as pd

ROOT = r"C:\projects\Karst"
BASKET = os.path.join(ROOT, r"research\2026-09-methodology\2026-09-10-①行業殺錯事件籃子")
SCORE = os.path.join(ROOT, r"research\2026-09-methodology\2026-09-11-①v3全量回測\評分\評分明細.csv")
PRICES = os.path.join(ROOT, r"data\prices\daily")
OUT = os.path.join(ROOT, r"research\2026-09-methodology\2026-09-11-①v3全量回測\接口回測")

EV = ["E01", "E06", "E07", "E08", "E12", "E13", "E14"]
CAND = [("E01", "SPG"), ("E01", "T"), ("E01", "ED"),
        ("E06", "RMD"), ("E06", "KO"), ("E06", "MDLZ"),
        ("E07", "MU"), ("E08", "AAPL"), ("E12", "SWKS"),
        ("E13", "MSFT"), ("E14", "DUOL")]

m = pd.read_csv(os.path.join(BASKET, "out", "basket_members.csv"), dtype={"entity_id": str})
m = m[m["basket_kind"] == "新聞點名"]
sc = pd.read_csv(SCORE, dtype={"event_id": str})

rows = []
for e in EV:
    g = m[m["event_id"] == e]
    rows.append((e, "basket", len(g), g["entity_id"].nunique()))
for e, t in CAND:
    g = sc[(sc["event_id"] == e) & (sc["ticker"] == t)]
    rows.append((e, "cand:" + t, len(g), g["premise_verdict"].iloc[0] if len(g) else None))
print(pd.DataFrame(rows, columns=["event", "kind", "rows", "n"]).to_string())

# 讀價格:只讀需要的 entity
need = set(m[m["event_id"].isin(EV)]["entity_id"].astype(str))
shards = sorted({int(e[-2:]) % 16 for e in need})
files = [os.path.join(PRICES, "part_%02d.parquet" % s) for s in shards]
print("shards:", shards, "files:", len(files))
px = pd.concat([pd.read_parquet(f, columns=["entity_id", "ticker", "date", "open", "close", "adj_close", "series_role"])
                for f in files], ignore_index=True)
px["entity_id"] = px["entity_id"].astype(str)
px["date"] = pd.to_datetime(px["date"])
px = px[(px["series_role"] == "primary") & (px["entity_id"].isin(need))]
print("price cols loaded; total rows", len(px))
sub = px[px["entity_id"].isin(need)]
print("needed entities:", len(need), "found:", sub["entity_id"].nunique())

# 逐宗查:衝擊起日前有幾多交易日
spec = pd.read_json(os.path.join(BASKET, "events_spec.json"))
shock = {e["event_id"]: e["shock_start"] for e in spec["events"]}
res = []
for e in EV:
    ids = set(m[m["event_id"] == e]["entity_id"].astype(str))
    s = pd.Timestamp(shock[e])
    for eid in sorted(ids):
        d = sub[sub["entity_id"] == eid].sort_values("date")
        if len(d) == 0:
            res.append((e, eid, None, 0, 0, None)); continue
        res.append((e, eid, d["ticker"].iloc[0],
                    int((d["date"] < s).sum()), int(len(d)),
                    str(d["date"].min().date()) + "/" + str(d["date"].max().date())))
r = pd.DataFrame(res, columns=["event", "entity_id", "ticker", "bars_before_shock", "bars_total", "span"])
r.to_csv(os.path.join(OUT, "_probe_data.csv"), index=False, encoding="utf-8-sig")
print("\n每宗 basket 成員 衝擊前交易日數 分佈:")
print(r.groupby("event")["bars_before_shock"].describe()[["count", "min", "25%", "50%"]].to_string())
print("\n不足 250 根的(basket 內):", int((r["bars_before_shock"] < 250).sum()), "/", len(r))
print("\n11 家候選:")
cands = r[r.apply(lambda x: (x["event"], x["ticker"]) in CAND, axis=1)]
print(cands.to_string())
