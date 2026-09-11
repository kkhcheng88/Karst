# -*- coding: utf-8 -*-
"""KARST-217 ①→②候選交接接口回測(四臂 A/B/C/D)。

口徑正本:同目錄 執行口徑——接口回測.md(先寫死後跑;本腳本不自行改口徑)。
只讀既有輸出;不改任何既有檔。Python 一律 PYTHONUTF8=1。

用法:  set PYTHONUTF8=1 && python iface_backtest.py
"""
import os
import re
import numpy as np
import pandas as pd

ROOT = r"C:\projects\Karst"
BASE = os.path.join(ROOT, r"research\2026-09-methodology")
BASKET = os.path.join(BASE, r"2026-09-10-①行業殺錯事件籃子")
SCORE = os.path.join(BASE, r"2026-09-11-①v3全量回測\評分\評分明細.csv")
PRICES = os.path.join(ROOT, r"data\prices\daily")
SPYF = os.path.join(ROOT, r"data\prices\spy_daily.csv")
OUT = os.path.join(BASE, r"2026-09-11-①v3全量回測\接口回測")

EV = ["E01", "E06", "E07", "E08", "E12", "E13", "E14"]
CAND = [("E01", "SPG"), ("E01", "T"), ("E01", "ED"),
        ("E06", "RMD"), ("E06", "KO"), ("E06", "MDLZ"),
        ("E07", "MU"), ("E08", "AAPL"), ("E12", "SWKS"),
        ("E13", "MSFT"), ("E14", "DUOL")]
COST = 0.001        # 每邊 10 個基點
VALID_BARS = 180    # 候選資格有效期(交易日)
YEAR_BARS = 252     # 一年期限(交易日)
BELOW_RUN = 10      # 線下連續日數

# ---------------------------------------------------------------- 讀資料
spec = pd.read_json(os.path.join(BASKET, "events_spec.json"))
SHOCK = {e["event_id"]: pd.Timestamp(e["shock_start"]) for e in spec["events"]}

bm = pd.read_csv(os.path.join(BASKET, "out", "basket_members.csv"), dtype={"entity_id": str})
bm = bm[bm["basket_kind"] == "新聞點名"][["event_id", "entity_id", "ticker", "name"]].drop_duplicates()
bm = bm[bm["event_id"].isin(EV)].copy()

sc = pd.read_csv(SCORE, dtype={"event_id": str})


def parse_date(s):
    """由 q3_date 自由文字抽出首個日期;只寫到月者取該月 1 日。"""
    if not isinstance(s, str):
        return pd.NaT
    m = re.match(r"\s*(\d{4})-(\d{2})(?:-(\d{2}))?", s)
    if not m:
        return pd.NaT
    return pd.Timestamp("%s-%s-%s" % (m.group(1), m.group(2), m.group(3) or "01"))


PREM = {}   # (event_id, ticker) -> (premise_verdict, 覆核日)
for _, r in sc.iterrows():
    PREM[(r["event_id"], r["ticker"])] = (r["premise_verdict"], parse_date(r["q3_date"]))

need = set(bm["entity_id"])
for e, t in CAND:
    need |= set(bm[(bm["event_id"] == e) & (bm["ticker"] == t)]["entity_id"])
print("需要的實體數:", len(need), flush=True)

shards = sorted({int(x[-2:]) % 16 for x in need})
px = pd.concat([pd.read_parquet(os.path.join(PRICES, "part_%02d.parquet" % s),
                                columns=["entity_id", "ticker", "date", "open", "close",
                                         "adj_close", "series_role"])
                for s in shards], ignore_index=True)
px["entity_id"] = px["entity_id"].astype(str)
px["date"] = pd.to_datetime(px["date"])
px = px[(px["series_role"] == "primary") & (px["entity_id"].isin(need))].copy()
px["adj_open"] = px["open"] * (px["adj_close"] / px["close"])

P = {}
for eid, g in px.groupby("entity_id"):
    g = g.sort_values("date").reset_index(drop=True)
    g["ma200"] = g["adj_close"].rolling(200, min_periods=200).mean()
    g["ma50"] = g["adj_close"].rolling(50, min_periods=50).mean()
    P[eid] = g

sp = pd.read_csv(SPYF, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
sp["adj_open"] = sp["open"] * (sp["adj_close"] / sp["close"])
SPD = sp["date"].values


def spy_i(d):
    i = int(np.searchsorted(SPD, np.datetime64(pd.Timestamp(d)), side="left"))
    return None if i >= len(SPD) else i


def spy_px(d, kind):
    i = spy_i(d)
    return np.nan if i is None else float(sp["adj_close"].iloc[i] if kind == "close"
                                          else sp["adj_open"].iloc[i])


ANCH = {}
for e in EV:
    i0 = spy_i(SHOCK[e])
    ANCH[e] = {"shock": SHOCK[e], "cutoff": pd.Timestamp(SPD[i0 + 5]),
               "a_entry": pd.Timestamp(SPD[i0 + 6]),
               "valid180": pd.Timestamp(SPD[min(i0 + 5 + VALID_BARS, len(SPD) - 1)]),
               "valid90": pd.Timestamp(SPD[min(i0 + 5 + 90, len(SPD) - 1)])}


def year_end(entry_date):
    i = spy_i(entry_date)
    return pd.Timestamp(SPD[min(i + YEAR_BARS, len(SPD) - 1)])


# ---------------------------------------------------------------- 單注模擬
def simulate(eid, event_id, ticker, line_col="ma200", entry_kind="A",
             exit_mode="cross", valid_end=None, use_premise=True):
    a = ANCH[event_id]
    d = P.get(eid)
    if d is None or len(d) == 0:
        return {"status": "無價格", "exit_reason": "無價格"}
    dates = d["date"].values
    vend = valid_end if valid_end is not None else a["valid180"]

    if entry_kind == "A":
        i = int(np.searchsorted(dates, np.datetime64(a["a_entry"]), side="left"))
        if i >= len(d):
            return {"status": "無價格", "exit_reason": "無價格"}
        ent_i, flag = i, "直接進場"
    else:
        j0 = int(np.searchsorted(dates, np.datetime64(a["cutoff"]), side="left"))
        ent_i, flag = None, None
        for j in range(j0, len(d)):
            if pd.Timestamp(dates[j]) > vend:
                break
            c, m = float(d["adj_close"].iloc[j]), d[line_col].iloc[j]
            if np.isnan(m):
                continue
            if j == j0:
                if c > m:
                    ent_i, flag = j + 1, "即日確認"
                    break
                continue
            pc, pm = float(d["adj_close"].iloc[j - 1]), d[line_col].iloc[j - 1]
            if not np.isnan(pm) and pc <= pm and c > m:
                ent_i, flag = j + 1, "升穿確認"
                break
        if ent_i is None or ent_i >= len(d):
            return {"status": "未成交", "exit_reason": "期內未確認"}

    ent_date = pd.Timestamp(dates[ent_i])
    ent_px = float(d["adj_open"].iloc[ent_i])
    if not np.isfinite(ent_px) or ent_px <= 0:
        return {"status": "無價格", "exit_reason": "無價格"}
    y_end = year_end(ent_date)

    # ①必要前提(事後欄)
    exit_i, reason = None, None
    verdict, chk = PREM.get((event_id, ticker), (None, pd.NaT))
    if use_premise and verdict == "被推翻" and isinstance(chk, pd.Timestamp) and not pd.isna(chk):
        pi = int(np.searchsorted(dates, np.datetime64(chk), side="left"))
        if pi <= ent_i:
            r0 = (1 - COST) ** 2 - 1
            s0, s1 = spy_px(ent_date, "open"), spy_px(year_end(ent_date), "close")
            sr = np.nan if (np.isnan(s0) or np.isnan(s1) or s0 <= 0) else s1 / s0 - 1
            return {"status": "成交", "ticker": ticker, "entry_date": ent_date, "entry_px": ent_px,
                    "exit_date": ent_date, "exit_px": ent_px, "bars": 0,
                    "exit_reason": "進場即失效(前提覆核日不遲於進場日)", "flag": flag or "",
                    "ret": r0, "premise": verdict, "spy_ret": sr,
                    "excess": (np.nan if np.isnan(sr) else r0 - sr)}
        exit_i, reason = min(pi, len(d) - 1), "①前提被推翻(事後欄)"

    # 逐日掃線下
    run, seen_above = 0, False
    for j in range(ent_i + 1, len(d)):
        if pd.Timestamp(dates[j]) > y_end:
            break
        c, m = float(d["adj_close"].iloc[j]), d[line_col].iloc[j]
        if not np.isnan(m) and c > m:
            seen_above = True
        if exit_mode == "cross" and not seen_above:
            run = 0
        else:
            run = run + 1 if (not np.isnan(m) and c < m) else 0
        if run >= BELOW_RUN:
            cand_i = min(j + 1, len(d) - 1)
            if exit_i is None or cand_i < exit_i:
                exit_i = cand_i
                reason = "跌回%d日線下連續%d日" % (200 if line_col == "ma200" else 50, BELOW_RUN)
            break

    if exit_i is None:
        ie = int(np.searchsorted(dates, np.datetime64(y_end), side="right")) - 1
        exit_i, reason = max(ie, ent_i), "期末未平"

    ex_date = pd.Timestamp(dates[exit_i])
    ex_px = float(d["adj_close"].iloc[exit_i]) if reason == "期末未平" else float(d["adj_open"].iloc[exit_i])
    kind = "close" if reason == "期末未平" else "open"
    s0, s1 = spy_px(ent_date, "open"), spy_px(ex_date, kind)
    spy_ret = np.nan if (np.isnan(s0) or np.isnan(s1) or s0 <= 0) else s1 / s0 - 1
    ret = (1 - COST) ** 2 * (ex_px / ent_px) - 1
    return {"status": "成交", "ticker": ticker, "entry_date": ent_date, "entry_px": round(ent_px, 6),
            "exit_date": ex_date, "exit_px": round(ex_px, 6), "bars": int(exit_i - ent_i),
            "exit_reason": reason, "flag": flag or "", "ret": ret, "spy_ret": spy_ret,
            "excess": (np.nan if np.isnan(spy_ret) else ret - spy_ret), "premise": verdict}


def idle_excess(event_id):
    a = ANCH[event_id]
    s0, s1 = spy_px(a["a_entry"], "open"), spy_px(year_end(a["a_entry"]), "close")
    return np.nan if (np.isnan(s0) or np.isnan(s1)) else -1.0 * (s1 / s0 - 1)


# ---------------------------------------------------------------- 跑四臂
def run_all(line_col="ma200", valid="valid180", exit_mode="cross", use_premise=True, tag="主口徑"):
    rows = []
    for e, t in CAND:
        eid = bm[(bm["event_id"] == e) & (bm["ticker"] == t)]["entity_id"].iloc[0]
        vend = ANCH[e][valid]
        a = simulate(eid, e, t, line_col, "A", exit_mode, vend, use_premise)
        b = simulate(eid, e, t, line_col, "B", exit_mode, vend, use_premise)
        for nm, dd in (("A", a), ("B", b)):
            r = dict(dd); r.update({"event_id": e, "entity_id": eid, "arm": nm, "tag": tag}); rows.append(r)
        ar = a["ret"] if a["status"] == "成交" else 0.0
        br = b["ret"] if b["status"] == "成交" else 0.0
        ae = a.get("excess", np.nan) if a["status"] == "成交" else idle_excess(e)
        be = b.get("excess", np.nan) if b["status"] == "成交" else idle_excess(e)
        rows.append({"event_id": e, "entity_id": eid, "ticker": t, "arm": "C", "tag": tag,
                     "status": "成交", "entry_date": a.get("entry_date"), "entry_px": np.nan,
                     "exit_date": a.get("exit_date"), "exit_px": np.nan, "bars": a.get("bars"),
                     "flag": "A半+B半",
                     "exit_reason": "A半:%s / B半:%s" % (a.get("exit_reason", "未成交"),
                                                         b.get("exit_reason", "未成交")),
                     "ret": 0.5 * ar + 0.5 * br, "spy_ret": np.nan,
                     "excess": 0.5 * (0 if np.isnan(ae) else ae) + 0.5 * (0 if np.isnan(be) else be),
                     "premise": a.get("premise")})
    for e in EV:
        for _, r in bm[bm["event_id"] == e].iterrows():
            dd = simulate(r["entity_id"], e, r["ticker"], line_col, "B", exit_mode,
                          ANCH[e][valid], use_premise)
            if dd["status"] != "成交":
                dd["ret"] = 0.0
                dd["excess"] = idle_excess(e)
            dd.update({"event_id": e, "entity_id": r["entity_id"], "ticker": r["ticker"],
                       "arm": "D", "tag": tag})
            rows.append(dd)
    return pd.DataFrame(rows)


def agg(df, arm):
    """回一行匯總。單位:①②③臂 = 候選;D 臂 = 成員(未成交比例按成員計),
    另加事件層(七宗等權)的中位/勝率,供四臂直接比。"""
    sub = df[df["arm"] == arm].copy()
    sub["ret"] = sub["ret"].fillna(0.0)
    sub["excess"] = sub["excess"].fillna(0.0)
    sub["traded"] = sub["status"] == "成交"
    ev = sub.groupby("event_id").agg(ret=("ret", "mean"), excess=("excess", "mean")).reset_index()
    lvl = "候選" if arm != "D" else "成員"
    return {"arm": arm, "單位": lvl,
            "單位數": int(len(sub)), "事件數": int(len(ev)),
            "未成交單位": int((~sub["traded"]).sum()),
            "未成交比例": float((~sub["traded"]).mean()),
            "單位_中位絕對": sub["ret"].median(), "單位_平均絕對": sub["ret"].mean(),
            "單位_中位超額": sub["excess"].median(), "單位_最差": sub["ret"].min(),
            "事件_中位絕對": ev["ret"].median(), "事件_平均絕對": ev["ret"].mean(),
            "事件_中位超額": ev["excess"].median(), "事件_勝率絕對": (ev["ret"] > 0).mean(),
            "事件_勝率超額": (ev["excess"] > 0).mean()}


print("\n=== 主口徑 ===", flush=True)
TR = run_all()
S = pd.DataFrame([agg(TR, a) for a in ("A", "B", "C", "D")])
print(S.round(4).to_string(index=False), flush=True)

print("\n=== 逐宗 ===", flush=True)
per_ev = TR.groupby(["event_id", "arm"]).apply(
    lambda g: pd.Series({"n": len(g), "未成交": int((g["status"] != "成交").sum()),
                         "平均絕對": g["ret"].fillna(0).mean(),
                         "中位絕對": g["ret"].fillna(0).median()}), include_groups=False).reset_index()
print(per_ev.pivot(index="event_id", columns="arm", values=["n", "未成交", "平均絕對"]).round(3).to_string(), flush=True)

print("\n=== 敏感度 ===", flush=True)
TR50 = run_all(line_col="ma50", tag="確認線50日")
TR90 = run_all(valid="valid90", tag="有效期90日")
SENS = []
for tag, df in (("確認線改 50 日", TR50), ("有效期改 90 交易日", TR90)):
    for a in ("A", "B", "C", "D"):
        r = agg(df, a); r["敏感度"] = tag; SENS.append(r)
SENS = pd.DataFrame(SENS)
print(SENS[["敏感度", "arm", "單位", "單位數", "未成交單位",
            "單位_中位絕對", "單位_中位超額", "事件_中位絕對", "事件_勝率絕對"]].round(4).to_string(index=False), flush=True)

print("\n=== 離場讀法:狀態讀法(對照) ===", flush=True)
TRC = run_all(exit_mode="state", tag="狀態讀法")
SC = pd.DataFrame([agg(TRC, a) for a in ("A", "B", "C", "D")])
print(SC.round(4).to_string(index=False), flush=True)

print("\n=== 不用①前提離場 ===", flush=True)
TRN = run_all(use_premise=False, tag="無前提離場")
SN = pd.DataFrame([agg(TRN, a) for a in ("A", "B", "C", "D")])
print(SN.round(4).to_string(index=False), flush=True)

print("\n=== 等待成本:B 對 A ===", flush=True)
wc = []
for e, t in CAND:
    a = TR[(TR.arm == "A") & (TR.ticker == t) & (TR.event_id == e)].iloc[0]
    b = TR[(TR.arm == "B") & (TR.ticker == t) & (TR.event_id == e)].iloc[0]
    if b["status"] != "成交":
        wc.append({"event_id": e, "ticker": t, "A進場日": a["entry_date"].date(),
                   "A進場價": a["entry_px"], "B進場日": None, "B進場價": None, "等待交易日": None,
                   "進場價差%": None, "等待期內最低收市相對A%": None,
                   "A全年報酬%": round(100 * a["ret"], 2), "B全年報酬%": None,
                   "判": "期內未確認,資金閒置"})
        continue
    d = P[b["entity_id"]]
    seg = d[(d["date"] >= a["entry_date"]) & (d["date"] <= b["entry_date"])]
    wt = int(len(seg) - 1)
    wc.append({"event_id": e, "ticker": t, "A進場日": a["entry_date"].date(), "A進場價": a["entry_px"],
               "B進場日": b["entry_date"].date(), "B進場價": b["entry_px"], "等待交易日": wt,
               "進場價差%": round(100 * (b["entry_px"] / a["entry_px"] - 1), 3),
               "等待期內最低收市相對A%": round(100 * (seg["adj_close"].min() / a["entry_px"] - 1), 3),
               "A全年報酬%": round(100 * a["ret"], 2), "B全年報酬%": round(100 * b["ret"], 2),
               "判": "追高" if b["entry_px"] > a["entry_px"] else "等便宜"})
WC = pd.DataFrame(wc)
print(WC.to_string(index=False), flush=True)

# ---------------------------------------------------------------- 落檔
TR.to_csv(os.path.join(OUT, "交易表——四臂.csv"), index=False, encoding="utf-8-sig")
S.to_csv(os.path.join(OUT, "匯總——四臂.csv"), index=False, encoding="utf-8-sig")
per_ev.to_csv(os.path.join(OUT, "匯總——逐宗.csv"), index=False, encoding="utf-8-sig")
SENS.to_csv(os.path.join(OUT, "敏感度——50日線與90日.csv"), index=False, encoding="utf-8-sig")
WC.to_csv(os.path.join(OUT, "等待成本——B對A.csv"), index=False, encoding="utf-8-sig")
SC.to_csv(os.path.join(OUT, "_離場讀法對照.csv"), index=False, encoding="utf-8-sig")
SN.to_csv(os.path.join(OUT, "_無前提離場對照.csv"), index=False, encoding="utf-8-sig")
print("\n已落檔:", OUT, flush=True)
