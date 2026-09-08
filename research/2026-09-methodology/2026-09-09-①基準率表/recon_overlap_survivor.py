# -*- coding: utf-8 -*-
"""KARST-192 第(四)(六)步:同公司單注版對照 + 倖存者翻轉 m 表 + 兩個歷史季度實測點。

(四) 同公司單注版
  正本的冷卻期是 120 個交易日,但持有期是 252 個交易日 —— 同一家公司的第二次觸發
  可以落在第一次的持有期之內,等於同時持有同一家公司兩注。本步出一版
  「觸發後 365 個曆日內不再計同一家公司的新觸發」的總表,與正本並列。

(六) 倖存者翻轉
  m 表:缺失事件的平均超額為 -50 / -75 / -100 個百分點時,
        令「完整樣本」的平均超額降到零所需的缺失比例 m。
        (1-m) x 觀察平均 + m x 缺失平均 = 0  =>  m = 觀察平均 / (觀察平均 - 缺失平均)
  實測點:2015Q1 與 2019Q1 兩個固定歷史季度,數當時有申報、市值 >= 5 億美元、
        其後 24 個月內停止申報的公司數。**這是一個點,不是估計。**

輸出:out/recon_one_position_recon.csv、out/recon_one_position_summary_recon.csv、
      out/recon_survivor_m_recon.csv、out/recon_survivor_probe_recon.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_tables as MT            # noqa: E402
import make_tables_gatefix as MTG   # noqa: E402
from recon_caliber import cell_recon, VERSIONS_BASE, VERSIONS_GF, PERIODS  # noqa: E402

OUT = HERE / "out"
PRICES = ROOT / "data" / "prices" / "daily"
PANEL = ROOT / "data" / "panel" / "quarterly_v3.parquet"
SUBS = ROOT / "data" / "sec" / "submissions"
ENTITIES = ROOT / "data" / "universe" / "entities.parquet"

HOLD_DAYS = 365   # 「同公司同時只持一注」的封鎖期(曆日)
MIN_MCAP = 500e6


# ------------------------------------------------------------------ (四)
def one_position_mask(ev: pd.DataFrame) -> pd.Series:
    """在給定的合格事件集內,同一家公司 365 曆日之內只留首次觸發。"""
    keep = np.zeros(len(ev), dtype=bool)
    order = ev.sort_values(["entity_id", "trigger_date"]).index
    last_end: dict[str, pd.Timestamp] = {}
    for i in order:
        e = ev.at[i, "entity_id"]
        t = ev.at[i, "trigger_date"]
        prev = last_end.get(e)
        if prev is None or t > prev:
            keep[ev.index.get_loc(i)] = True
            last_end[e] = t + pd.Timedelta(days=HOLD_DAYS)
    return pd.Series(keep, index=ev.index)


def overlap_tables(long: pd.DataFrame, versions, tag: str) -> tuple[pd.DataFrame, list]:
    rows, drops = [], []
    for ver, flag in versions:
        q = long[long[flag] & long["資料可信"]].copy()
        # 單注遮罩只需按事件層(entity_id, trigger_date)算一次
        uniq = (q[["entity_id", "trigger_date"]].drop_duplicates()
                 .reset_index(drop=True))
        m = one_position_mask(uniq)
        keepset = set(map(tuple, uniq[m][["entity_id", "trigger_date"]].to_numpy()))
        q["單注"] = [tuple(x) in keepset for x in
                     q[["entity_id", "trigger_date"]].to_numpy()]
        drops.append({"事件表": tag, "版本": ver,
                      "合格事件(事件層)": int(len(uniq)),
                      "單注版保留": int(m.sum()),
                      "被重疊剔走": int(len(uniq) - m.sum()),
                      "剔走比例": float(1 - m.sum() / len(uniq)) if len(uniq) else np.nan})
        for plabel, pf in PERIODS:
            if pf == "le2021":
                s0 = q[q["trigger_year"] <= 2021]
            elif pf == "ge2022":
                s0 = q[q["trigger_year"] >= 2022]
            else:
                s0 = q
            for entry in MT.ENTRIES.values():
                for h in MT.HORIZONS:
                    s = s0[(s0["進場格"] == entry) & (s0["期"] == h)]
                    base = {"事件表": tag, "版本": ver, "年份段": plabel,
                            "進場格": entry, "期": h}
                    rows.append({**base, "口徑": "正本(120 日冷卻)",
                                 **cell_recon(s)})
                    rows.append({**base, "口徑": "同公司單注(365 曆日)",
                                 **cell_recon(s[s["單注"]])})
    return pd.DataFrame(rows), drops


# ------------------------------------------------------------------ (六) m 表
def m_table(grids: pd.DataFrame) -> pd.DataFrame:
    g = grids[(grids["表"] == "總表(三格進場)") & (grids["格"] == "全部")].copy()
    rows = []
    for r in g.itertuples(index=False):
        mu = getattr(r, "平均超額", np.nan)
        if not np.isfinite(mu):
            continue
        rec = {"事件表": r.事件表, "版本": r.版本, "年份段": r.年份段,
               "進場格": r.進場格, "期": r.期, "樣本N": r.樣本N,
               "觀察平均超額": mu, "觀察勝率": getattr(r, "勝率", np.nan)}
        for miss in (-0.50, -0.75, -1.00):
            key = f"缺失平均 {int(miss*100)} 個百分點時,平均歸零所需缺失比例 m"
            rec[key] = float(mu / (mu - miss)) if mu > 0 else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ (六) 實測點
LAST_RE = re.compile(rb'"filingDate":\s*\[\s*"(\d{4}-\d{2}-\d{2})"')
FROM_RE = re.compile(rb'"filingFrom":\s*"(\d{4}-\d{2}-\d{2})"')


def scan_submissions() -> pd.DataFrame:
    """由申報索引主檔取每個 CIK 的最後申報日與最早申報日(含分頁邊界)。

    最後申報日 = filings.recent.filingDate 的第一個(EDGAR 由新到舊排)。
    最早申報日 = min(filings.files[].filingFrom, recent 內最舊者);
                 README 第二節已核:用 filingFrom 邊界日期與逐筆讀分頁內容結果一致。
    """
    rows = []
    for p in sorted(SUBS.glob("CIK*.json")):
        b = p.read_bytes()
        m = LAST_RE.search(b)
        if not m:
            continue
        last = m.group(1).decode()
        froms = [x.decode() for x in FROM_RE.findall(b)]
        dates = re.findall(rb'"(\d{4}-\d{2}-\d{2})"', b[m.start():m.start() + 40000])
        recent_min = min(d.decode() for d in dates) if dates else last
        first = min(froms + [recent_min]) if froms else recent_min
        rows.append({"entity_id": p.stem.replace("CIK", ""),
                     "最早申報日": first, "最後申報日": last,
                     "有分頁": bool(froms)})
    df = pd.DataFrame(rows)
    df["最早申報日"] = pd.to_datetime(df["最早申報日"])
    df["最後申報日"] = pd.to_datetime(df["最後申報日"])
    return df


def mcap_on(date: pd.Timestamp, ids: list[str]) -> pd.DataFrame:
    """某日的近似市值:該日(或之前最近交易日)收市價 x 該日前最近一次已公布封面頁股數。"""
    frames = []
    lo = date - pd.Timedelta(days=10)
    for p in sorted(PRICES.glob("part_*.parquet")):
        t = pq.read_table(p, columns=["entity_id", "date", "close", "series_role"])
        t = t.filter(pc.and_(pc.equal(t["series_role"], "primary"),
                             pc.and_(pc.greater_equal(t["date"], lo.date()),
                                     pc.less_equal(t["date"], date.date()))))
        if t.num_rows:
            frames.append(t.to_pandas())
    px = pd.concat(frames, ignore_index=True)
    px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values(["entity_id", "date"]).groupby("entity_id").tail(1)

    pan = pd.read_parquet(PANEL, columns=["entity_id", "period_end", "filed_date",
                                          "shares_outstanding"])
    pan = pan.dropna(subset=["shares_outstanding", "filed_date"])
    pan["filed_date"] = pd.to_datetime(pan["filed_date"])
    pan = pan[(pan["filed_date"] <= date) &
              (pan["filed_date"] >= date - pd.Timedelta(days=400))]
    pan = pan.sort_values(["entity_id", "filed_date"]).groupby("entity_id").tail(1)

    d = px.merge(pan[["entity_id", "shares_outstanding"]], on="entity_id", how="inner")
    d["mcap"] = d["close"] * d["shares_outstanding"]
    return d[["entity_id", "date", "close", "shares_outstanding", "mcap"]]


def survivor_probe(subs: pd.DataFrame) -> dict:
    res = {}
    for label, qend in (("2015Q1", pd.Timestamp("2015-03-31")),
                        ("2019Q1", pd.Timestamp("2019-03-29"))):
        mc = mcap_on(qend, [])
        big = mc[mc["mcap"] >= MIN_MCAP]
        j = big.merge(subs, on="entity_id", how="left")
        active = j[(j["最早申報日"] <= qend) & (j["最後申報日"] >= qend)]
        cut = qend + pd.DateOffset(months=24)
        stopped = active[active["最後申報日"] < cut]
        res[label] = {
            "季末日": str(qend.date()),
            "有價格且有股數的公司": int(len(mc)),
            "其中市值 >= 5 億美元": int(len(big)),
            "其中當時有申報(申報期涵蓋該日)": int(len(active)),
            "其後 24 個月內停止申報": int(len(stopped)),
            "停止申報比例": float(len(stopped) / len(active)) if len(active) else np.nan,
            "停止申報者代號": sorted(stopped["entity_id"].tolist())[:50],
        }
    return res


def main() -> None:
    long_b, _ = MT.load_long()
    long_g, _ = MTG.load_long_gatefix()

    tb, db = overlap_tables(long_b, VERSIONS_BASE, "events.csv(正本)")
    tg, dg = overlap_tables(long_g, VERSIONS_GF, "events_gatefix.csv")
    op = pd.concat([tb, tg], ignore_index=True)
    op.to_csv(OUT / "recon_one_position_recon.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(db + dg).to_csv(OUT / "recon_one_position_summary_recon.csv",
                                 index=False, encoding="utf-8-sig")
    print(pd.DataFrame(db + dg).to_string(index=False))

    grids = pd.read_csv(OUT / "recon_caliber_recon.csv", encoding="utf-8-sig")
    mt = m_table(grids)
    mt.to_csv(OUT / "recon_survivor_m_recon.csv", index=False, encoding="utf-8-sig")

    print("\n[申報索引掃描]")
    subs = scan_submissions()
    print(f"  掃到 {len(subs):,} 個 CIK 主檔;有分頁的 {int(subs['有分頁'].sum()):,}")
    ent = pd.read_parquet(ENTITIES, columns=["entity_id", "filing_status",
                                             "first_filing_date", "last_filing_date"])
    probe = survivor_probe(subs)
    probe["申報索引主檔數"] = int(len(subs))
    probe["最後申報日 < 2026-01-01 的 CIK 數"] = int((subs["最後申報日"] < "2026-01-01").sum())
    probe["最後申報日 < 2024-01-01 的 CIK 數"] = int((subs["最後申報日"] < "2024-01-01").sum())
    probe["最後申報日 < 2020-01-01 的 CIK 數"] = int((subs["最後申報日"] < "2020-01-01").sum())
    probe["宇宙表 filing_status=ceased 的實體數"] = int((ent["filing_status"] == "ceased").sum())
    probe["宇宙表實體數"] = int(len(ent))
    with open(OUT / "recon_survivor_probe_recon.json", "w", encoding="utf-8") as f:
        json.dump(probe, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in probe.items() if k not in ("2015Q1", "2019Q1")},
                     ensure_ascii=False, indent=2))
    for k in ("2015Q1", "2019Q1"):
        v = dict(probe[k]); v.pop("停止申報者代號", None)
        print(k, json.dumps(v, ensure_ascii=False))

    m12 = mt[(mt["年份段"] == "全期 2010-2026") & (mt["進場格"] == "觸發日即買")]
    print("\n[m 表 全期 觸發日即買]")
    with pd.option_context("display.width", 220, "display.max_columns", 20):
        print(m12.to_string(index=False))


if __name__ == "__main__":
    main()
