# -*- coding: utf-8 -*-
"""十宗試跑:機械檢查兩臂的 rows/*.csv 與卡(格式合格率、一致性、漏答、讀了哪些文件)。
不開任何結果、不比較準確度。用法:PYTHONUTF8=1 python check_rows.py [ds|opus|both]
"""
import csv, glob, io, json, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
COLS = ("event_id,ticker,cik,signal_date,improvement_text,n_drivers,top_driver_type,top_driver_share_lo,"
        "top_driver_share_hi,persistence_overall,pred_g2_point,pred_g2_lo,pred_g2_hi,pred_g4_point,pred_g4_lo,"
        "pred_g4_hi,supply_catchup,supply_timing,tags,lifecycle_stage,stop_event_1_date,stop_event_2_date,"
        "premise,falsify_1,biggest_unknown,unknowns_count,contamination_note").split(",")
PERS = {"高", "中", "低", "無法判斷"}
SUPPLY = {"會", "不會", "不適用", "查不到"}
DRV = {"價格", "數量", "組合", "成本", "一次性", "低基期"}

def num(x):
    try:
        return float(x)
    except Exception:
        return None

def g0_from_packet(eid):
    p = os.path.join(BASE, "..", "A2", "packets", f"{eid}.json")
    try:
        d = json.load(open(p, encoding="utf-8"))
        return d["4_財務數列"].get("g0_signal_q_yoy")
    except Exception:
        return None

def check_arm(arm):
    rows_dir = os.path.join(BASE, arm, "rows")
    files = sorted(glob.glob(os.path.join(rows_dir, "*.csv")))
    out = {"arm": arm, "n_files": len(files), "parse_ok": 0, "header_ok": 0, "ncol_ok": 0,
           "field_violations": [], "consistency": [], "persistence": {}, "supply": {},
           "unknowns_total": 0, "cannot_judge": 0, "docs_read": {}, "cards": 0, "card_sections_missing": []}
    for f in files:
        eid = os.path.basename(f)[:-4]
        raw = open(f, encoding="utf-8-sig").read()
        try:
            rd = list(csv.reader(io.StringIO(raw)))
        except Exception as e:
            out["field_violations"].append((eid, "parse", str(e)))
            continue
        if len(rd) < 2:
            out["field_violations"].append((eid, "rows", len(rd)))
            continue
        out["parse_ok"] += 1
        hdr, row = rd[0], rd[1]
        if [h.strip() for h in hdr] == COLS:
            out["header_ok"] += 1
        else:
            out["field_violations"].append((eid, "header", len(hdr)))
        if len(row) == len(COLS):
            out["ncol_ok"] += 1
        else:
            out["field_violations"].append((eid, "ncol", len(row)))
            continue
        d = dict(zip(COLS, row))
        if d["persistence_overall"] not in PERS:
            out["field_violations"].append((eid, "persistence", d["persistence_overall"]))
        if d["supply_catchup"] not in SUPPLY:
            out["field_violations"].append((eid, "supply", d["supply_catchup"]))
        if d["top_driver_type"] not in DRV:
            out["field_violations"].append((eid, "driver", d["top_driver_type"]))
        for k in ("pred_g2_point", "pred_g2_lo", "pred_g2_hi", "pred_g4_point", "pred_g4_lo", "pred_g4_hi"):
            if num(d[k]) is None:
                out["field_violations"].append((eid, k, d[k]))
        lo, pt, hi = num(d["pred_g2_lo"]), num(d["pred_g2_point"]), num(d["pred_g2_hi"])
        if None not in (lo, pt, hi) and not (lo <= pt <= hi):
            out["field_violations"].append((eid, "g2_order", (lo, pt, hi)))
        for k in ("improvement_text", "premise", "falsify_1", "biggest_unknown", "contamination_note"):
            if "," in d[k] or "\n" in d[k]:
                out["field_violations"].append((eid, k + "_comma", None))
        out["persistence"][d["persistence_overall"]] = out["persistence"].get(d["persistence_overall"], 0) + 1
        out["supply"][d["supply_catchup"]] = out["supply"].get(d["supply_catchup"], 0) + 1
        u = num(d["unknowns_count"])
        out["unknowns_total"] += int(u) if u is not None else 0
        if d["persistence_overall"] == "無法判斷":
            out["cannot_judge"] += 1
        g0 = g0_from_packet(eid)
        if g0 is not None and pt is not None:
            if d["persistence_overall"] == "高" and pt < 0.8 * g0:
                out["consistency"].append((eid, "高 but pt<0.8g0", pt, g0))
            if d["persistence_overall"] == "低" and pt >= 0.8 * g0:
                out["consistency"].append((eid, "低 but pt>=0.8g0", pt, g0))
        # card
        cards = glob.glob(os.path.join(BASE, arm, f"卡-{eid}-*.md"))
        if cards:
            out["cards"] += 1
            txt = open(cards[0], encoding="utf-8").read()
            for step in ("第一步", "第二步", "第三步", "第四步", "第五步", "第六步", "第七步", "第八步"):
                if step not in txt:
                    out["card_sections_missing"].append((eid, step))
            acc = set(re.findall(r"\d{10}-\d{2}-\d{6}", txt))
            out["docs_read"][eid] = len(acc)
            if "contamination_note" not in txt and "污染" not in txt:
                out["card_sections_missing"].append((eid, "contamination"))
        else:
            out["card_sections_missing"].append((eid, "no_card"))
    return out

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    arms = ["ds", "opus"] if which == "both" else [which]
    res = {a: check_arm(a) for a in arms}
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
