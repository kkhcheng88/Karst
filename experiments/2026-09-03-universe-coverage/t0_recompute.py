# -*- coding: utf-8 -*-
"""KARST-173:用單一價格庫與面板 v3 重算 138 家十倍股在 t0 的市值、指數身份、淨現金。

判準見 CRITERIA.md 第二至七節。零新抓,全部原料唯讀。
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import common as C

FIVE_Y = pd.DateOffset(years=5)


def main() -> None:
    C.OUT.mkdir(exist_ok=True)
    names = pd.read_csv(C.TENBAGGERS)
    names = names[names["horizon"] == "5y"].copy()
    names["t0"] = pd.to_datetime(names["t0"])
    print(f"十倍股名單(5y):{len(names)} 家")

    # 一次過接實體,再一次過讀價格
    matched = []
    for r in names.itertuples():
        eid, why = C.match_entity(r.ticker, r.t0)
        matched.append((eid, why))
    names["entity_id"] = [m[0] for m in matched]
    names["match_note"] = [m[1] for m in matched]
    eids = {e for e in names["entity_id"] if e}
    print(f"接得回實體:{len(names) - names['entity_id'].isna().sum()} 家,涉及 {len(eids)} 個實體")

    px = C.load_prices(entity_ids=eids)
    px_idx = {k: v for k, v in px.groupby(["entity_id", "ticker"], sort=False)}
    panel_all = C.panel()

    rows = []
    for r in names.itertuples():
        row: dict = dict(ticker=r.ticker, t0=r.t0.date().isoformat(),
                         multiple_old=r.multiple, t0_price_old=r.t0_price,
                         entity_id=r.entity_id, match_note=r.match_note,
                         宇宙分段=getattr(r, "宇宙分段", ""))
        if not isinstance(r.entity_id, str) or not r.entity_id:
            row["mcap_missing_reason"] = "entity_unmatched"
            rows.append(row)
            continue

        s = px_idx.get((r.entity_id, r.ticker))
        if s is None:
            cand = px[px["entity_id"] == r.entity_id]
            s = cand if len(cand) else None
        if s is None or not len(s):
            row["mcap_missing_reason"] = "price_absent"
            rows.append(row)
            continue
        s = s.sort_values("date")
        d = s["date"].to_numpy()

        # t0 當日,否則 t0 之前 5 個交易日內最近一日
        i = int(np.searchsorted(d, np.datetime64(r.t0), side="right")) - 1
        if i < 0 or (r.t0 - pd.Timestamp(d[i])).days > 10:
            row["mcap_missing_reason"] = "price_absent_at_t0"
            rows.append(row)
            continue
        px_t0 = float(s["close"].iloc[i])
        adj_t0 = float(s["adj_close"].iloc[i])
        row["price_date"] = pd.Timestamp(d[i]).date().isoformat()
        row["t0_close"] = px_t0
        row["t0_adj_close"] = adj_t0

        # 五年窗內的倍數與回撤(用新價格庫重算,作交叉核對,不改判)
        end = r.t0 + FIVE_Y
        w = s[(s["date"] > r.t0) & (s["date"] <= end)]
        if len(w):
            row["multiple_new"] = float(w["adj_close"].max() / adj_t0)
            row["drawdown_new"] = float(w["adj_close"].min() / adj_t0 - 1)
            row["window_rows"] = int(len(w))
        else:
            row["window_rows"] = 0

        # 市值
        sh_row = panel_all[(panel_all["entity_id"] == r.entity_id)
                           & (panel_all["filed_date"] <= r.t0)
                           & (panel_all["shares_outstanding"].notna())]
        row["has_panel_at_t0"] = bool(len(
            panel_all[(panel_all["entity_id"] == r.entity_id)
                      & (panel_all["filed_date"] <= r.t0)]))
        sf, in_tbl = C.split_factor_after(r.ticker, r.t0)
        row["split_factor"] = sf
        row["split_table_absent"] = not in_tbl
        if r.ticker in C.CONTAMINATED:
            row["mcap_missing_reason"] = "split_table_contaminated"
        elif sh_row.empty:
            row["mcap_missing_reason"] = "shares_absent_at_t0"
        else:
            last = sh_row.iloc[-1]
            row["shares_filed"] = float(last["shares_outstanding"])
            row["shares_filed_date"] = pd.Timestamp(last["filed_date"]).date().isoformat()
            row["shares_period_end"] = pd.Timestamp(last["period_end"]).date().isoformat() \
                if pd.notna(last["period_end"]) else ""
            row["currency"] = last["currency"]
            row["mcap"] = px_t0 * float(last["shares_outstanding"]) * sf
            row["mcap_missing_reason"] = "none"

        # 淨現金(兩個口徑)與指數身份
        prow = C.panel_asof(r.entity_id, r.t0)
        row.update(C.net_cash_flags(prow))
        if prow is not None:
            row["panel_filed_date"] = pd.Timestamp(prow["filed_date"]).date().isoformat()
        row["in_index"] = C.in_index(r.ticker, r.t0)
        row["in_v1"] = None   # 下面統一填
        rows.append(row)

    out = pd.DataFrame(rows)
    v1 = pd.read_csv(C.UNIVERSE / "universe_smallcap_v1.csv", dtype={"entity_id": str})
    v1_ids = set(v1["entity_id"].str.zfill(10))
    out["in_v1"] = out["entity_id"].fillna("").map(lambda e: bool(e) and e in v1_ids)

    m = out["mcap"] if "mcap" in out.columns else pd.Series(dtype=float)
    out["U1"] = (m >= 3e8) & (m < 5e9)
    out["U2"] = m < 5e9
    out["U3"] = (m >= 2e8) & (m <= 1e10)
    out["U0"] = out["in_index"].fillna(False)
    out["U5"] = out["in_v1"]
    out.to_csv(C.OUT / "tenbagger_t0_v3.csv", index=False, encoding="utf-8")

    n = len(out)
    known = int(m.notna().sum())
    summary = {
        "n_names": n,
        "n_entity_matched": int(out["entity_id"].notna().sum()),
        "n_price_at_t0": int(out["t0_close"].notna().sum()) if "t0_close" in out else 0,
        "n_has_panel_at_t0": int(out.get("has_panel_at_t0", pd.Series(dtype=bool)).sum()),
        "n_mcap_known": known,
        "mcap_missing_reason": out["mcap_missing_reason"].value_counts().to_dict(),
        "mcap_quantiles_usd": (m.dropna().describe(percentiles=[.1, .25, .5, .75, .9]).to_dict()
                               if known else {}),
        "coverage": {},
        "n1_known": int(out["n1"].notna().sum()),
        "n1_positive": int(out["n1"].fillna(False).sum()),
        "n2_known": int(out["n2"].notna().sum()),
        "n2_positive": int(out["n2"].fillna(False).sum()),
        "n1_reason": out["n1_reason"].value_counts().to_dict(),
        "n2_reason": out["n2_reason"].value_counts().to_dict(),
        "n_in_index": int(out["in_index"].fillna(False).sum()),
        "drawdown_gt_50pct": (int((out["drawdown_new"] <= -0.5).sum())
                              if "drawdown_new" in out else 0),
        "drawdown_known": (int(out["drawdown_new"].notna().sum())
                           if "drawdown_new" in out else 0),
        "split_table_absent": int(out.get("split_table_absent",
                                          pd.Series(dtype=bool)).fillna(False).sum()),
        "currency_non_usd": int((out.get("currency", pd.Series(dtype=str)).fillna("")
                                 .replace("", np.nan).dropna() != "USD").sum()),
        "by_t0_year": {},
    }
    out["t0_year"] = pd.to_datetime(out["t0"]).dt.year
    for y, g in out.groupby("t0_year"):
        summary["by_t0_year"][int(y)] = {
            "家數": int(len(g)),
            "有面板": int(g["has_panel_at_t0"].fillna(False).sum()),
            "有市值": int(g["mcap"].notna().sum()) if "mcap" in g else 0,
        }
    for u, label in [("U0", "U0 t0 時為標普成分"), ("U1", "U1 羅素2000近似(3億–50億)"),
                     ("U2", "U2 全美小型股(<50億)"), ("U3", "U3 自定義(2億–100億)"),
                     ("U5", "U5 小型股宇宙 v1 成員名單")]:
        hit = int(out[u].fillna(False).sum())
        if u in ("U0", "U5"):
            summary["coverage"][label] = {"命中": hit, "分母": n,
                                          "覆蓋率": round(hit / n, 4)}
        else:
            summary["coverage"][label] = {
                "命中": hit, "有市值家數": known,
                "覆蓋率下限(未知當作不在)": round(hit / n, 4),
                "覆蓋率上限(未知當作在)": round((hit + n - known) / n, 4),
                "有市值者之中的比例": round(hit / known, 4) if known else None}
    (C.OUT / "tenbagger_t0_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
