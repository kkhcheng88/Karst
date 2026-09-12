# -*- coding: utf-8 -*-
"""KARST-226 票 A″(執行口徑 v1.2)第十一步:經營對照預測 C1/C2/C3 → `controls_operating.csv`。

口徑(執行口徑 v1.2 修訂頁第 8 項):
  - **C2 = 全樣本主要對照** —— 訊號季之前連續四季的按年收入增速平均(XBRL 首報值),
    每宗都算;四季中最早申報日晚於 T1 的,計入 `C2_n_hist_after_T1` 供核查。
  - **C1 只在有可比收入指引的子樣本比** —— 由該份 EX-99.1 的財年收入指引中值,
    用**固定季節性法**分配到季度(去年同季佔去年餘下期間的比例),標「估算」。
    在比例分配下「下一季增速」與「餘下期間整體增速」是同一條數(權重約掉),
    故只報一條 `C1_implied_yoy`,並附分配後的下一季隱含收入與去年同季收入供核。
  - **C3 = g0**(訊號季按年收入增速),與取證包一致用**稿內文字**版,另列 XBRL 版對照。

本檔輸出**不入任何取證包**。與 A2 版之別:(a) 季末季由年報 − 9 個月累計補回(finlib);
(b) C1 改用 v1.2 解析器的指引紀錄 + 單位判讀;(c) C3 用稿內文字版。
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

import finlib as F

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

SCALES = [1.0, 1e3, 1e6, 1e9]
UNIT_WORDS = {"billion": 1e9, "bn": 1e9, "b": 1e9, "million": 1e6, "mn": 1e6,
              "m": 1e6, "thousand": 1e3, "k": 1e3}
NUM_UNIT_RX = re.compile(
    r"\$?\s*(\d[\d,]*(?:\.\d+)?)\s*(billion|million|bn|mn|thousand|b|m|k)\b", re.I)


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def pick_scale(mid: float, sentence: str, refs: list[float]) -> tuple[float | None, str]:
    """定出指引數字的單位倍率。先認句中的單位字,再用往年收入量級核。"""
    refs = [r for r in refs if r and r > 0]
    for m in NUM_UNIT_RX.finditer(sentence or ""):
        u = UNIT_WORDS.get(m.group(2).lower())
        if not u:
            continue
        try:
            v = float(m.group(1).replace(",", "")) * u
        except ValueError:
            continue
        for s in SCALES:
            if v > 0 and abs(v - mid * s) / v < 0.005:
                return s, "句中單位字"
    if not refs:
        return None, "無往年收入可核單位"
    best, besterr = None, None
    for s in SCALES:
        for r in refs:
            ratio = mid * s / r
            if 0.3 <= ratio <= 3.0:
                err = abs(ratio - 1.0)
                if besterr is None or err < besterr:
                    best, besterr = s, err
    if best is None:
        return None, "指引值與往年收入量級不合(疑單位誤判)"
    return best, "往年收入量級"


def c1_for(recs: list[dict], b: dict, q_end: str) -> dict:
    """由指引紀錄算 C1。回傳 dict(欄位見 `COLS`)。"""
    out = {"C1_implied_yoy": "", "C1_basis": "", "C1_estimated": "",
           "C1_guidance_mid_usd": "", "C1_guidance_scale": "", "C1_note": "",
           "C1_snippet": "", "C1_next_q_implied_rev": "", "C1_next_q_prior_rev": ""}
    cands = [r for r in recs if r.get("metric") == "revenue" and r.get("period") == "FY"
             and r.get("new_mid") is not None]
    if not cands:
        out["C1_note"] = "無可比財年收入指引(解析器未抽到)"
        return out
    if not b.get("ok"):
        out["C1_note"] = b.get("note", "無財務快取")
        return out
    q = date.fromisoformat(q_end)
    ends = sorted(e for e in b["rev_q"] if e <= q_end)
    if q_end not in ends:
        out["C1_note"] = "無訊號季 XBRL"
        return out
    ann = sorted({e for _s, e, _v in b["rev_annual"]})
    fye_cur_l = [e for e in ann if e >= q_end]
    fye_cur = fye_cur_l[0] if fye_cur_l else None
    py_end_l = [e for e in ann if e < q_end]
    py_end = py_end_l[-1] if py_end_l else None
    if fye_cur is None or py_end is None:
        out["C1_note"] = "無財年期末可定位(年報數列不足)"
        return out
    fy_tot = None
    for _s, e, v in b["rev_annual"]:
        if e == fye_cur:
            fy_tot = v
    py_tot = None
    for _s, e, v in b["rev_annual"]:
        if e == py_end:
            py_tot = v
    ytds = [(s, e, v) for s, e, v in b["rev_cum"] if e == q_end]
    ytd = max(ytds, key=lambda x: _days(x[0], x[1]))[2] if ytds else None
    n_done = sum(1 for e in ends if _days(py_end, e) > 0)
    # 財年最後四個季末:首尾相距約 9 個月(四個季末＝三段季距),不是 12 個月
    py_qs = sorted(e for e in b["rev_q"] if e <= py_end)[-4:]
    if len(py_qs) == 4 and not (240 <= _days(py_qs[0], py_qs[-1]) <= 320):
        py_qs = []          # 最後四季不構成連續一年(申報期改過等)→ 不強行分配

    refs = [x for x in (fy_tot, py_tot, ytd) if x]
    rec = cands[0]
    scale, how = pick_scale(float(rec["new_mid"]), rec.get("sentence", ""), refs)
    if scale is None:
        out["C1_note"] = how
        return out
    mid = float(rec["new_mid"]) * scale
    out["C1_guidance_mid_usd"] = round(mid, 2)
    out["C1_guidance_scale"] = how
    out["C1_snippet"] = (rec.get("sentence") or "")[:300]
    if ytd is None or not py_tot or len(py_qs) != 4:
        out["C1_note"] = "財年定位不足(累計收入/去年財年/去年四季有缺,得 %d 季)" % len(py_qs)
        return out
    # 指引屬哪一個財年:句中有財年數字認那個;否則訊號季即財年末或中值低於累計 →
    # 當下一財年,其餘當本財年
    yr = _fy_year(rec.get("sentence", ""))
    if yr is not None and any(date.fromisoformat(e).year == yr for e in ann):
        g_end = min(e for e in ann if date.fromisoformat(e).year == yr)
        next_fy = g_end > fye_cur
    else:
        next_fy = (n_done >= 4) or (mid <= ytd)
    share_prior = sum(b["rev_q"][e] for e in py_qs[:n_done] if b["rev_q"].get(e)) / py_tot
    if next_fy:
        if share_prior <= 0:
            out["C1_note"] = "去年首 %d 季無收入,無法以季節性推當財年" % n_done
            return out
        denom = ytd / share_prior
        tag = "下一財年(分母=以去年同季佔比推當財年總額)"
    else:
        rest = mid - ytd
        py_rest = py_qs[n_done:]
        if not py_rest:
            out["C1_note"] = "本財年已無餘下季度"
            return out
        if any(b["rev_q"].get(e) is None for e in py_rest):
            out["C1_note"] = "去年餘下季度有缺值"
            return out
        denom = sum(b["rev_q"][e] for e in py_rest)
        if rest <= 0:
            out["C1_note"] = "指引中值不高於已報累計收入"
            return out
        tag = "本財年餘下季度(去年同季佔比分配;比例分配下與下一季增速同值)"
        nxt = py_rest[0]
        out["C1_next_q_prior_rev"] = round(b["rev_q"][nxt], 2)
        out["C1_next_q_implied_rev"] = round(rest * b["rev_q"][nxt] / denom, 2)
    if denom <= 0:
        out["C1_note"] = "對照分母非正"
        return out
    out["C1_implied_yoy"] = round(mid / denom - 1.0, 6)
    out["C1_basis"] = tag
    out["C1_estimated"] = "真"
    out["C1_note"] = "本財年已完成 %d 季;指引 %s + 單位判讀(%s)%s" % (
        n_done, "%.4g" % float(rec["new_mid"]), how,
        "" if yr is None else ";句中年份 %d" % yr)
    if abs(out["C1_implied_yoy"]) > 2.0:
        out["C1_note"] += ";極端值(|隱含增速|>200%),指引數字疑誤抽"
    return out


def _fy_year(sentence: str) -> int | None:
    m = re.search(r"(?i)(?:fiscal|full[- ]year|fy)[^\d\n]{0,12}(20\d\d)", sentence or "")
    return int(m.group(1)) if m else None


def _add_year(d: str, n: int) -> str:
    from datetime import timedelta
    return (date.fromisoformat(d) + timedelta(days=365 * n)).isoformat()


def c2_for(b: dict, q_end: str, t1: str) -> dict:
    out = {"C2_prev4_avg_yoy": "", "C2_n_quarters": "", "C2_n_hist_after_T1": "",
           "C2_note": ""}
    if not b.get("ok") or not q_end:
        out["C2_note"] = "無財務快取" if not b.get("ok") else "無訊號季"
        return out
    ser = b["rev_q"]
    filed = b.get("rev_q_filed", {})
    ends = sorted(ser)
    if q_end not in ends:
        out["C2_note"] = "訊號季不在 XBRL 數列"
        return out
    i = ends.index(q_end)
    hist = ends[max(0, i - 4):i]
    ys = [y for y in (F.yoy(ser, e) for e in hist) if y is not None]
    out["C2_n_quarters"] = len(ys)
    out["C2_n_hist_after_T1"] = sum(
        1 for e in hist if filed.get(e, (None, ""))[1] and filed[e][1] > t1)
    if len(ys) != 4:
        out["C2_note"] = "可用歷史季不足 4(得 %d)" % len(ys)
        return out
    c2 = sum(ys) / 4.0
    out["C2_prev4_avg_yoy"] = round(c2, 6)
    notes = []
    if out["C2_n_hist_after_T1"]:
        notes.append("其中 %d 季的首報日晚於 T1" % out["C2_n_hist_after_T1"])
    if abs(c2) > 2.0:
        notes.append("基數效應(去年同季接近零),數值不可直接比")
    out["C2_note"] = ";".join(notes)
    return out


COLS = ["event_id", "kind", "year", "bucket", "accessionNumber", "cik", "ticker",
        "reaction_date", "signal_q_end", "fiscal_quarter", "improvement_type",
        "C1_implied_yoy", "C1_basis", "C1_estimated", "C1_guidance_mid_usd",
        "C1_guidance_scale", "C1_next_q_implied_rev", "C1_next_q_prior_rev",
        "C1_note", "C1_snippet",
        "C2_prev4_avg_yoy", "C2_n_quarters", "C2_n_hist_after_T1", "C2_note",
        "C3_g0_text", "C3_g0_xbrl"]


def main() -> None:
    picks = json.loads((CACHE / "picks.json").read_text(encoding="utf-8"))
    pop = pd.read_parquet(CACHE / "population_improvement.parquet")
    meta = pop.set_index("accessionNumber")
    guide: dict[str, list[dict]] = {}
    for line in (CACHE / "guidance_parsed.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        guide.setdefault(r["accessionNumber"], []).append(r)
    rows = []
    bundles: dict[str, dict] = {}
    for kind in ("main", "backup"):
        for p in picks[kind]:
            m = meta.loc[p["acc"]]
            cik = m["cik"]
            if cik not in bundles:
                bundles[cik] = F.bundle(cik)
            b = bundles[cik]
            q_end = m["signal_q_end"]
            t1 = str(m["reaction_date"])[:10]
            c1 = c1_for(guide.get(p["acc"], []), b, q_end) if q_end else {
                "C1_note": "無訊號季", "C1_implied_yoy": "", "C1_basis": "",
                "C1_estimated": "", "C1_guidance_mid_usd": "", "C1_guidance_scale": "",
                "C1_snippet": "", "C1_next_q_implied_rev": "", "C1_next_q_prior_rev": ""}
            c2 = c2_for(b, q_end, t1)
            row = dict(
                event_id=p["event_id"], kind=kind, year=p["year"], bucket=p["bucket"],
                accessionNumber=p["acc"], cik=cik, ticker=m["ticker"],
                reaction_date=t1, signal_q_end=q_end,
                fiscal_quarter=m["fiscal_quarter"], improvement_type=m["improvement_type"],
                C3_g0_text="" if pd.isna(m["rev_g0_text"]) else round(float(m["rev_g0_text"]), 6),
                C3_g0_xbrl="" if pd.isna(m["rev_g0"]) else round(float(m["rev_g0"]), 6),
                **c1, **c2)
            rows.append(row)
            print("  %s %s %s C1=%s(%s) C2=%s(%s) C3=%s" % (
                p["event_id"], kind, m["ticker"], row["C1_implied_yoy"],
                row["C1_note"][:24], row["C2_prev4_avg_yoy"], row["C2_note"][:20],
                row["C3_g0_text"]), flush=True)
    out = pd.DataFrame(rows, columns=COLS)
    out.to_csv(HERE / "controls_operating.csv", index=False, encoding="utf-8-sig")
    print("共 %d 列(主 %d、後備 %d)" % (
        len(out), (out["kind"] == "main").sum(), (out["kind"] == "backup").sum()))
    print("C1 有值 %d;C2 有值 %d;C3 有值 %d" % (
        (out["C1_implied_yoy"] != "").sum(), (out["C2_prev4_avg_yoy"] != "").sum(),
        (out["C3_g0_text"] != "").sum()))
    print("C1 註解分佈:", out["C1_note"].str.slice(0, 22).value_counts().to_dict())
    print("C2 註解分佈:", out["C2_note"].str.slice(0, 22).value_counts().to_dict())
    print("→", HERE / "controls_operating.csv")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
