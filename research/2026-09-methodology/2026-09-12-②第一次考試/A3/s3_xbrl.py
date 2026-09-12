# -*- coding: utf-8 -*-
"""KARST-226 票 A″(v1.2)第三步:由 companyfacts 取訊號季按年收入增速 g0、上一季增速,
並判**分析口徑適用性 F**(執行口徑 v1.2 第 5 項 (b))。

與 `A/s3_xbrl.py` 之別:
  ①標準收入標籤收窄為 v1.2 明文那三個:`Revenues`、
    `RevenueFromContractWithCustomerExcludingAssessedTax`、`SalesRevenueNet`
    (`RevenuesNetOfInterestExpense` 明文不算);其他標籤不再當作收入來源。
  ②新增適用性三類原因 `applicability_reason`:
      真無披露      —— 無 companyfacts 快取 / 無 us-gaap 科目 / 無 USD 單位
      標籤缺        —— 三個標準標籤一個都沒有
      季度轉換失敗  —— 有標籤但取不到 80–100 日單季值,或訊號季之前湊不到連續 8 季
  ③新增 `n_consec_q`(以訊號季結尾的連續季度數)與 `rev_tag_used`。

輸出 `cache/xbrl_metrics.parquet`。
"""
from __future__ import annotations

import gzip
import json
import multiprocessing as mp
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
CF = ROOT / "data" / "sec" / "companyfacts"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

# v1.2 明文的三個標準收入標籤(次序 = 取值優先)
STD_REV_TAGS = ["Revenues",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet"]
MIN_CONSEC_Q = 8


def quarter_rev(cik: str):
    """回傳 (期末日 → 首報單季收入, 期末日 → 該值首報申報日, 狀態, 用到的標籤, 標籤數,
    其中由「全年 − 九個月」補回的年結季數)。

    「首報申報日」= 該期末日各標籤之中 `filed` 最早者(v1.2 補三要用它核 T1 可得性)。
    """
    p = CF / ("CIK%s.json.gz" % cik)
    if not p.exists():
        return {}, {}, "真無披露", "", 0, 0
    try:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            facts = json.load(f)
    except (OSError, json.JSONDecodeError, EOFError):
        return {}, {}, "真無披露", "", 0, 0
    gaap = facts.get("facts", {}).get("us-gaap", {})
    if not gaap:
        return {}, {}, "真無披露", "", 0, 0

    have_any_tag = any(t in gaap for t in STD_REV_TAGS)
    if not have_any_tag:
        return {}, {}, "標籤缺", "", 0, 0

    used = ""
    by_end: dict[str, tuple[float, str]] = {}
    ytd9: dict[str, tuple[float, str, str]] = {}   # 起日 → (值, 申報日, 訖日);九個月累計
    fy: dict[str, tuple[float, str, str]] = {}     # 起日 → (值, 申報日, 訖日);全年
    n_tags_with_q = 0
    for tag in STD_REV_TAGS:
        node = gaap.get(tag)
        if not node:
            continue
        got = False
        for unit, rows in node.get("units", {}).items():
            if unit != "USD":
                continue
            for r in rows:
                st, en, v = r.get("start"), r.get("end"), r.get("val")
                if st is None or en is None or v is None:
                    continue
                try:
                    d = (date.fromisoformat(en) - date.fromisoformat(st)).days
                except ValueError:
                    continue
                fl = r.get("filed", "")
                if 80 <= d <= 100:
                    got = True
                    prev = by_end.get(en)
                    if prev is None or fl < prev[1]:
                        by_end[en] = (float(v), fl)
                elif 255 <= d <= 285:
                    # 以「起日」為鍵:同一年度的全年與九個月由同一日起
                    prev = ytd9.get(st)
                    if prev is None or fl < prev[1]:
                        ytd9[st] = (float(v), fl, en)
                elif 340 <= d <= 380:
                    prev = fy.get(st)
                    if prev is None or fl < prev[1]:
                        fy[st] = (float(v), fl, en)
        if got:
            n_tags_with_q += 1
            if not used:
                used = tag
    # 年結那一季沒有三月期值(申報慣例:10-K 只標全年與九個月累計)→ 用 全年 − 九個月 補回,
    #   兩者同一「起日」,九個月訖日須為全年訖日之前一季;可得時點 = 兩者之中較晚申報者。
    #   只用三個標準標籤,不引入新標籤。
    n_derived = 0
    for st_day, (v_fy, f_fy, end_fy) in fy.items():
        if end_fy in by_end:
            continue
        hit = ytd9.get(st_day)
        if hit is None:
            continue
        v9, f9, end9 = hit
        try:
            gap = (date.fromisoformat(end_fy) - date.fromisoformat(end9)).days
        except ValueError:
            continue
        if not (60 <= gap <= 130) or v_fy - v9 <= 0:
            continue
        by_end[end_fy] = (v_fy - v9, max(f_fy, f9))
        n_derived += 1
    if not by_end:
        return {}, {}, "季度轉換失敗", used, 0, 0
    return ({k: v[0] for k, v in by_end.items()},
            {k: v[1] for k, v in by_end.items()}, "", used, n_tags_with_q, n_derived)


def yoy_end(series: dict[str, float], end: str) -> str | None:
    """回傳去年同季的期末日(取最接近 365 日前者)。"""
    e = date.fromisoformat(end)
    cands = []
    for k in series:
        d = (e - date.fromisoformat(k)).days
        if 340 <= d <= 390:
            cands.append((abs(d - 365), k))
    if not cands:
        return None
    cands.sort()
    return cands[0][1]


def yoy(series: dict[str, float], end: str) -> float | None:
    base_k = yoy_end(series, end)
    if base_k is None:
        return None
    base = series[base_k]
    if base == 0:
        return None
    return series[end] / base - 1.0


def n_consecutive(ends: list[str], q: str) -> int:
    """由 q 往前數連續季度(相鄰兩個期末相距 60–130 日),回傳連續季數。"""
    if q not in ends:
        return 0
    i = ends.index(q)
    n = 1
    j = i
    while j - 1 >= 0:
        gap = (date.fromisoformat(ends[j]) - date.fromisoformat(ends[j - 1])).days
        if 60 <= gap <= 130:
            n += 1
            j -= 1
        else:
            break
    return n


def _one(cik: str):
    s, filed, st, tag, n, nd = quarter_rev(cik)
    return cik, (s, st, tag, n, nd), filed


def main() -> None:
    ev = pd.read_parquet(CACHE / "events_raw.parquet")
    ev = ev.drop_duplicates(subset=["accessionNumber"]).reset_index(drop=True)
    ciks = sorted(ev["cik"].unique())
    print("要取 XBRL 的公司數:%d" % len(ciks), flush=True)

    series_by_cik: dict[str, dict[str, float]] = {}
    filed_by_cik: dict[str, dict[str, str]] = {}
    status_by_cik: dict[str, str] = {}
    tag_by_cik: dict[str, str] = {}
    n_done = 0
    n_derived_tot = 0
    with mp.Pool(processes=8) as pool:
        for cik, (s, st, tag, _n, nd), filed in pool.imap_unordered(_one, ciks, chunksize=20):
            series_by_cik[cik] = s
            filed_by_cik[cik] = filed
            status_by_cik[cik] = st
            tag_by_cik[cik] = tag
            n_derived_tot += nd
            n_done += 1
            if n_done % 1000 == 0:
                print("  ...%d/%d" % (n_done, len(ciks)), flush=True)

    rows = []
    for r in ev.itertuples(index=False):
        s = series_by_cik.get(r.cik, {})
        st = status_by_cik.get(r.cik, "真無披露")
        fdd = date.fromisoformat(r.filingDate)
        rec = dict(accessionNumber=r.accessionNumber, cik=r.cik,
                   signal_q_end="", signal_q_days_before_filing=None,
                   fiscal_quarter="", rev_g0=None, rev_prev_q_yoy=None,
                   accel_pp=None, accel_hit=None, xbrl_status=st or "",
                   rev_tag_used=tag_by_cik.get(r.cik, ""), n_consec_q=0,
                   applicability_reason="",
                   q_filed_signal="", q_filed_yago="", q_filed_prev="",
                   q_filed_prev_yago="", hist_src_latest_filed="",
                   rev_signal_xbrl=None, rev_yago_xbrl=None,
                   rev_prev_xbrl=None, rev_prev_yago_xbrl=None,
                   rev_ttm_xbrl=None, prev4_yoy_mean=None)
        if s:
            ends = sorted(s)
            cands = [e for e in ends if date.fromisoformat(e) <= fdd
                     and (fdd - date.fromisoformat(e)).days <= 120]
            if not cands:
                rec["applicability_reason"] = "季度轉換失敗"
                rec["xbrl_status"] = "filingDate 前 120 日內無單季收入期末"
            else:
                q = cands[-1]
                rec["signal_q_end"] = q
                rec["signal_q_days_before_filing"] = (fdd - date.fromisoformat(q)).days
                qm = date.fromisoformat(q).month
                rec["fiscal_quarter"] = "%dQ%d" % (
                    date.fromisoformat(q).year, (qm - 1) // 3 + 1)
                nq = n_consecutive(ends, q)
                rec["n_consec_q"] = nq
                if nq < MIN_CONSEC_Q:
                    rec["applicability_reason"] = "季度轉換失敗"
                fmap = filed_by_cik.get(r.cik, {})
                g0 = yoy(s, q)
                rec["rev_g0"] = g0
                qy = yoy_end(s, q)
                rec["q_filed_signal"] = fmap.get(q, "")
                rec["q_filed_yago"] = fmap.get(qy, "") if qy else ""
                rec["rev_signal_xbrl"] = s.get(q)
                rec["rev_yago_xbrl"] = s.get(qy) if qy else None
                idx = ends.index(q)
                if idx >= 1:
                    pq = ends[idx - 1]
                    pg = yoy(s, pq)
                    rec["rev_prev_q_yoy"] = pg
                    pqy = yoy_end(s, pq)
                    rec["q_filed_prev"] = fmap.get(pq, "")
                    rec["q_filed_prev_yago"] = fmap.get(pqy, "") if pqy else ""
                    rec["rev_prev_xbrl"] = s.get(pq)
                    rec["rev_prev_yago_xbrl"] = s.get(pqy) if pqy else None
                    if g0 is not None and pg is not None:
                        rec["accel_pp"] = (g0 - pg) * 100.0
                        rec["accel_hit"] = int(rec["accel_pp"] >= 2.0)
                # 補三:加速所用的「歷史季度」(去年同季、上一季、去年上一季)最晚來源申報日
                hist = [rec["q_filed_yago"], rec["q_filed_prev"], rec["q_filed_prev_yago"]]
                hist = [h for h in hist if h]
                rec["hist_src_latest_filed"] = max(hist) if hist else ""
                # 最近四季收入(TTM)與「訊號前四季按年增速平均」(控制 C2 用)
                if idx >= 3 and nq >= 4:
                    last4 = ends[idx - 3:idx + 1]
                    rec["rev_ttm_xbrl"] = float(sum(s[e] for e in last4))
                pgs = []
                for j in range(1, 5):
                    if idx - j < 0:
                        break
                    e = ends[idx - j]
                    gg = yoy(s, e)
                    if gg is not None:
                        pgs.append(gg)
                if len(pgs) == 4:
                    rec["prev4_yoy_mean"] = float(sum(pgs) / 4.0)
                if g0 is None and not rec["applicability_reason"]:
                    rec["xbrl_status"] = "算不出 g0(缺去年同季)"
        else:
            # 公司層已判:真無披露 / 標籤缺 / 季度轉換失敗
            rec["applicability_reason"] = st or "真無披露"
        rows.append(rec)

    out = pd.DataFrame(rows)
    out.to_parquet(CACHE / "xbrl_metrics.parquet", index=False)
    print("有 g0:%d / %d" % (out["rev_g0"].notna().sum(), len(out)))
    print("有上一季增速:%d;加速命中(≥2pp):%d" % (
        out["rev_prev_q_yoy"].notna().sum(), (out["accel_hit"] == 1).sum()))
    print("由「全年−九個月」補回的年結季數:%d(公司層合計)" % n_derived_tot)
    print("適用性三類:", out["applicability_reason"].value_counts(dropna=False).to_dict())
    print("連續季數分位:", out["n_consec_q"].quantile([.1, .5, .9]).round(1).to_dict())
    print("用到的標籤:", out["rev_tag_used"].value_counts().to_dict())
    print("→", CACHE / "xbrl_metrics.parquet")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
