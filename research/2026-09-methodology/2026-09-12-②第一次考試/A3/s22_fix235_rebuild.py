# -*- coding: utf-8 -*-
"""KARST-236 第 1–3 步:重建 E017/E022/E024 的 `4_財務數列`,並修 5 包訊號季行。

口徑(KARST-235 核查的處置):
  1. 四欄(收入、毛利、營業利潤、經營現金流)改用 `finlib_fixed` —— **同一期末跨 tag
     取 `filed` 最早那一份**,同日再按 tag 次序;財年末季推算照舊但與直接事實同一把尺比;
     另有累計差分補缺格那一層(與核查真值同一條)。
  2. 十項加數同樣改為跨 tag 最早申報(原本即時項是 tag 次序優先)。
  3. **訊號季那一行只放 EX-99.1 稿內對得上的數**(數字匹配千/百萬/十億,容差 0.5%,
     附近要有該項關鍵字;同一期末的 6/9/12 個月累計值回聲剔除);稿內對不上者留 null
     (該欄來源標「查不到」),不拿 XBRL 值補。收入另備「各 tag 直接值 / 年報期末推算值」
     作候選(同一期末可以有幾個收入概念,取稿內真的有而且最接近的那一個)。
  4. 重算 `g0_signal_q_yoy` / `prev_q_yoy` / `accel_pp` / `hist_src_latest_filed` /
     `hist_quarters_public_by_T1`;`accel_pp < 2` 且無收入指引上調者加
     `entry_status: 入口不成立(修正後)`。
改前九包備份在 `A3/cache/packets_before_fix235/`;只寫這 8 包,其餘 76 包不動。
不列公司名或代號。用法:`PYTHONUTF8=1 python s22_fix235_rebuild.py [--apply]`
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import finlib_fixed as FF  # noqa: E402
import s15_lib as L  # noqa: E402
from s16_build import HIST_KW, find_plain, find_usd  # noqa: E402

PKT = HERE / "packets"
REBUILD = ["E017", "E022", "E024"]
SIGFIX = ["E021", "E025", "E047", "E057", "E073"]

NUM_RX = re.compile(r"(?<![\w.])(-?\s?\(?\$?\s?\d[\d,]*(?:\.\d+)?\s?\)?)\s*"
                    r"(thousand|thousands|million|millions|billion|billions|mn|bn|[MBK])?\b")
MULT = {"thousand": 1e3, "thousands": 1e3, "k": 1e3,
        "million": 1e6, "millions": 1e6, "mn": 1e6, "m": 1e6,
        "billion": 1e9, "billions": 1e9, "bn": 1e9, "b": 1e9}
KW = {
    "revenue": re.compile(r"(?i)\b(revenue|revenues|net sales|total sales|sales)\b"),
    "gross_profit": re.compile(r"(?i)(gross profit|gross margin)"),
    "operating_income": re.compile(
        r"(?i)(operating income|operating profit|income from operations|"
        r"loss from operations|income \(loss\) from operations)"),
    "ocf": re.compile(r"(?i)(operating activities|cash flow|net cash provided)"),
}
FIELDS = {"revenue": "REV_TAGS", "gross_profit": "GP_TAGS",
          "operating_income": "OI_TAGS", "ocf": "OCF_TAGS"}
TOL = 0.005


def _num(s: str):
    """稿內數字的正負:前置 `-` 或括號(含 `(2,998 )` 這種有空格的)皆為負。"""
    t = re.sub(r"\s+", "", s)
    neg = t.startswith("(") or t.startswith("-")
    t = t.strip("()").replace("$", "").replace(",", "").lstrip("-")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def text_matches(text: str, v: float, name: str):
    """稿內有沒有一個數(含千/百萬/十億縮放)等於 |v|(容差 0.5%),附近有該項字眼。

    回 [{value(照稿內正負), rel, pos, snippet}]。比對用絕對值:稿內同一個數可能寫成
    `(2,998 )`(負)或 `5,575`(正),正負照稿內所印。
    """
    if not text or v in (None, 0):
        return []
    out = []
    for m in NUM_RX.finditer(text):
        raw = _num(m.group(1))
        if raw is None or raw == 0:
            continue
        unit = (m.group(2) or "").lower()
        cands = ([raw * MULT[unit]] if unit in MULT else []) + \
                [raw * s for s in (1.0, 1e3, 1e6, 1e9)]
        for c in cands:
            if c and abs(abs(c) / abs(v) - 1.0) <= TOL:
                ctx = text[max(0, m.start() - 200):m.end() + 40]
                if KW[name].search(ctx):
                    out.append({"value": c,
                                "rel": abs(abs(c) / abs(v) - 1.0),
                                "pos": m.start(),
                                "snippet": re.sub(
                                    r"\s+", " ", text[max(0, m.start() - 110):
                                                     m.end() + 20])})
                break
    return out


def ytd_values(facts: dict, tags: list, end: str) -> list:
    """同一期末的 6/9/12 個月累計值 —— 命中等於把累計值當單季,剔除。"""
    out = []
    for t in tags:
        for (_st, en), (v, _f) in FF._first_report(
                FF.unit_rows(facts, t), 150, 400).items():
            if en == end:
                out.append(v)
    return out


def sig_targets(facts: dict, tags: list, end: str, base) -> list:
    """候選值:修正後真值 → 各 tag 該期末直接值 → 各 tag 年報期末推算值。"""
    out = [base]
    for t in tags:
        for (_s, e), (v, _f) in FF._first_report(FF.unit_rows(facts, t),
                                                 80, 100).items():
            if e == end:
                out.append(v)
    for t in tags:
        y = FF._year_end_quarters(facts, [t])
        if end in y:
            out.append(y[end][0])
    seen, uniq = set(), []
    for v in out:
        if v is not None and v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq


def pick_text(text: str, targets: list, name: str, ytd: list):
    """挑稿內真有、且不是累計值回聲的那一個;先比相對差,再比候選次序、位置。"""
    best = None
    for rank, v in enumerate(targets):
        if v in (None, 0):
            continue
        for m in text_matches(text, v, name):
            if any(y not in (None, 0)
                   and abs(abs(m["value"]) / abs(y) - 1.0) <= TOL for y in ytd):
                continue
            key = (round(m["rel"], 6), rank, m["pos"])
            if best is None or key < best[0]:
                best = (key, m, v)
    if best is None:
        return None
    return {"value": best[1]["value"], "rel": round(best[1]["rel"], 6),
            "matched_target": best[2], "snippet": best[1]["snippet"]}


# ---------------------------------------------------------------- 加十項(修正版)

def _merge_fx(best: dict, en: str, v: float, f: str, idx: int, tag: str) -> None:
    key = (f or "", idx)
    if en not in best or key < best[en][3]:
        best[en] = (v, f, tag, key)


def _tags_earliest(facts: dict, tags: list, unit: str, dur) -> dict:
    """跨 tag 取 `filed` 最早那一份(同日再按 tags 次序)。`dur` = (lo,hi) 或 None。"""
    out: dict = {}
    for idx, t in enumerate(tags):
        for en, (v, f) in L._first_filed(L.tag_rows(facts, t, unit), dur).items():
            _merge_fx(out, en, v, f, idx, t)
    return out


def fixed_extra(facts: dict, name: str) -> dict:
    """{期末日: (值, 最早 filed, 贏的 tag, 排序鍵)}。

    即時項與長短期借款合計原本按 tag 次序取先者 → 改為跨 tag 取最早申報;期長項
    (`s15_lib.duration_series`)本來就是跨 tag 最早申報,回空字典 = 該項原樣保留。
    """
    cfg = L.EXTRA_ITEMS[name]
    if cfg["kind"] not in ("instant", "instant_sum"):
        return {}
    if cfg["kind"] == "instant":
        return _tags_earliest(facts, cfg["tags"], cfg["unit"], None)
    if cfg["kind"] == "instant_sum":
        for idx, (ta, tb) in enumerate([(L.DEBT_CURRENT, L.DEBT_NONCURRENT),
                                        (L.DEBT_TOTAL, []),
                                        (L.DEBT_NONCURRENT, [])]):
            out: dict = {}
            sa = _tags_earliest(facts, ta, cfg["unit"], None)
            sb = _tags_earliest(facts, tb, cfg["unit"], None) if tb else {}
            for en in (set(sa) & set(sb)) if tb else set(sa):
                v = sa[en][0] + sb[en][0] if tb else sa[en][0]
                f = max(sa[en][1], sb[en][1]) if tb else sa[en][1]
                _merge_fx(out, en, v, f, idx, "derived")
            if out:
                return out
        return {}


def guide_rev_raise() -> dict:
    """收入指引上調:沿用建池口徑(`entry_pool.csv` 的 guide_rev_raise)。"""
    p = HERE / "entry_pool.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p, usecols=["accessionNumber", "guide_rev_raise"])
    return {str(a): bool(v) for a, v in zip(df["accessionNumber"],
                                            df["guide_rev_raise"])}


def diff_obj(a, b, path: str = "") -> list:
    """兩個 JSON 物件逐格比對,回「路徑 舊 → 新」清單。"""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            p = "%s.%s" % (path, k)
            if k not in a:
                out.append("%s +新增 %r" % (p, b[k]))
            elif k not in b:
                out.append("%s -刪除 %r" % (p, a[k]))
            else:
                out += diff_obj(a[k], b[k], p)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append("%s 長度 %d → %d" % (path, len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff_obj(x, y, "%s[%d]" % (path, i))
    elif a != b:
        out.append("%s %r → %r" % (path, a, b))
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    apply = "--apply" in sys.argv
    g_raise = guide_rev_raise()
    log = []
    for eid in REBUILD + SIGFIX:
        pf = PKT / ("%s.json" % eid)
        p = json.load(open(pf, encoding="utf-8"))
        before = json.loads(json.dumps({"1_事件識別": p["1_事件識別"],
                                        "4_財務數列": p["4_財務數列"]}))
        idn = p["1_事件識別"]
        cik = str(idn["cik"]).zfill(10)
        t1 = str(idn["T1_分析截止"])[:10]
        fin = p["4_財務數列"]
        qs = fin["quarters"]
        sig = fin["signal_q_end"]
        text = (p["2_觸發資料"] or {}).get("ex991_full_text") or ""
        facts = FF.load_facts(cik)

        rec = {"revenue": FF.rec_full(facts, FF.REV_TAGS),
               "gross_profit": FF.rec_full(facts, FF.GP_TAGS),
               "operating_income": FF.rec_full(facts, FF.OI_TAGS)}
        rev_v = {k: v["value"] for k, v in rec["revenue"].items()}
        ocf = FF.ocf_series(facts)
        ends = sorted(rev_v)
        yago = FF.yoy_end(rev_v, sig)
        prev_q = (ends[ends.index(sig) - 1]
                  if (sig in ends and ends.index(sig) >= 1) else None)
        prev_yago = FF.yoy_end(rev_v, prev_q) if prev_q else None

        if eid in REBUILD:
            extras = {n: fixed_extra(facts, n) for n in L.EXTRA_ITEMS}
            for q in qs:
                e = q["period_end"]
                for fld in ("revenue", "gross_profit", "operating_income"):
                    r = rec[fld].get(e)
                    q[fld] = r["value"] if r else None
                q["ocf"] = ocf.get(e)
                if e != sig:
                    r = rec["revenue"].get(e)
                    q["revenue_xbrl_first_filed_after_T1"] = bool(
                        r and r["first_filed"] and r["first_filed"] > t1)
                    q["revenue_year_end_derived"] = bool(r and r["fy_derived"])
                ex = {}
                for name in L.EXTRA_ITEMS:
                    cfg = L.EXTRA_ITEMS[name]
                    if cfg["kind"] not in ("instant", "instant_sum"):
                        continue        # 期長項本來已是跨 tag 最早申報,原樣保留
                    hit = extras[name].get(e)
                    if e == sig:
                        ok = (hit is not None and
                              (find_usd(text, hit[0], HIST_KW[name])
                               if cfg["unit"] == "USD"
                               else find_plain(text, hit[0], HIST_KW[name])))
                        ex[name] = ({"value": hit[0], "source": "EX-99.1 稿內文字"}
                                    if ok else "查不到")
                    elif hit is None or not hit[1] or hit[1] > t1:
                        ex[name] = "查不到"
                    else:
                        ex[name] = {"value": hit[0], "filed": hit[1],
                                    "source": "XBRL 首報值", "tag": hit[2]}
                for name in ex:
                    q["extra"][name] = ex[name]
            fin["source"] = (
                "訊號季收入 = EX-99.1 稿內文字(v1.2 第 4 項);其餘各季 = "
                "data/sec/companyfacts XBRL 首報值(KARST-236:同一期末跨 tag 取"
                "最早申報,累計差分補缺格)")
            fin["extra_items_rule"] = (
                "加十項(XBRL 首報值,每一格的來源申報日 ≤ T1,晚於 T1 者一律「查不到」;"
                "KARST-236:同一期末跨 tag 取最早申報)。**訊號季那一行只認 EX-99.1 "
                "稿內有的數字**(數字匹配 + 附近要有該項的關鍵字),稿內沒有者標「查不到」。"
                "非訊號季者附 `filed` = 該值最早申報日(必 ≤ T1)。")

        # ---- 訊號季行:四欄改成稿內對得上的數
        sigrow = next(q for q in qs if q["period_end"] == sig)
        srcs, picks = {}, {}
        for name, attr in FIELDS.items():
            tags = getattr(FF, attr)
            if name == "ocf":
                base = ocf.get(sig)
            elif name == "revenue":
                base = rev_v.get(sig)
            else:
                base = rec[name].get(sig, {}).get("value")
            tg = sig_targets(facts, tags, sig, base)
            hit = pick_text(text, tg, name, ytd_values(facts, tags, sig))
            v = hit["value"] if hit else None
            picks[name] = hit
            srcs[name] = "EX-99.1 稿內文字" if v is not None else "查不到"
            sigrow[name] = v
            if name == "revenue":
                sigrow["revenue_source"] = srcs[name]
                sigrow["revenue_ex991"] = v
        sigrow["signal_row_sources"] = srcs
        sigrow["revenue_xbrl_for_reference"] = rev_v.get(sig)
        r = rec["revenue"].get(sig)
        sigrow["revenue_year_end_derived"] = bool(r and r["fy_derived"])
        sigrow["revenue_xbrl_first_filed_after_T1"] = False
        fin["n_rows_first_filed_after_T1"] = sum(
            1 for q in qs if q.get("revenue_xbrl_first_filed_after_T1"))

        # ---- 量化欄重算
        if sig in rev_v and yago and rev_v.get(yago):
            if sigrow.get("revenue") is not None:
                fin["g0_signal_q_yoy"] = round(
                    sigrow["revenue"] / rev_v[yago] - 1.0, 6)
            fin["g0_xbrl_for_reference"] = round(
                rev_v[sig] / rev_v[yago] - 1.0, 6)
        if prev_q and prev_yago and rev_v.get(prev_yago):
            fin["prev_q_yoy"] = round(rev_v[prev_q] / rev_v[prev_yago] - 1.0, 6)
        if fin.get("g0_signal_q_yoy") is not None and fin.get("prev_q_yoy") is not None:
            fin["accel_pp"] = round(
                (fin["g0_signal_q_yoy"] - fin["prev_q_yoy"]) * 100.0, 4)
        hf = [rec["revenue"][x]["first_filed"] for x in (yago, prev_q, prev_yago)
              if x and x in rec["revenue"] and rec["revenue"][x]["first_filed"]]
        fin["hist_src_latest_filed"] = max(hf) if hf else ""
        fin["hist_quarters_public_by_T1"] = bool(hf and max(hf) <= t1)

        entry = None
        if fin.get("accel_pp") is not None and fin["accel_pp"] < 2.0 \
                and not g_raise.get(str(idn.get("accessionNumber", "")), False):
            entry = "入口不成立(修正後)"
            idn["entry_status"] = entry
        idn["修正後(KARST-236)"] = {
            "g0_signal_q_yoy": fin.get("g0_signal_q_yoy"),
            "prev_q_yoy": fin.get("prev_q_yoy"),
            "accel_pp": fin.get("accel_pp"),
            "entry_status": entry,
            "note": "訊號季那一行以 EX-99.1 稿內數字為準、其餘各季改為同一期末跨 tag "
                    "最早申報值後重算;逐格前後值見 A3/修正紀錄——235.md"}

        changes = diff_obj(before["4_財務數列"], fin, "4_財務數列")
        changes += diff_obj(before["1_事件識別"], idn, "1_事件識別")
        if apply:
            pf.write_text(json.dumps(p, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        log.append({"event_id": eid, "rebuild": eid in REBUILD,
                    "n_changes": len(changes), "changes": changes,
                    "g0": fin.get("g0_signal_q_yoy"),
                    "g0_xbrl": fin.get("g0_xbrl_for_reference"),
                    "prev_q_yoy": fin.get("prev_q_yoy"),
                    "accel_pp": fin.get("accel_pp"), "entry_status": entry,
                    "sig_row_sources": srcs,
                    "sig_row_picks": {k: v for k, v in picks.items()},
                    "t1": t1, "signal_q_end": sig})
        print("%s rebuild=%s changes=%d g0=%s prev=%s accel=%s entry=%s" % (
            eid, eid in REBUILD, len(changes), fin.get("g0_signal_q_yoy"),
            fin.get("prev_q_yoy"), fin.get("accel_pp"), entry))
        for c in changes:
            print("     ", c)

    out = HERE / "cache" / "fix235_rebuild_log.json"
    out.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    print("apply=%s log=%s" % (apply, out))


if __name__ == "__main__":
    main()
