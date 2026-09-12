# -*- coding: utf-8 -*-
"""KARST-228 格式與一致性檢查:兩臂各 10 張 csv 與 10 張卡。
輸出 _audit_format.txt(逐臂逐項)。
"""
import csv, io, os, re, glob

BASE = r"C:/projects/Karst/research/2026-09-methodology/2026-09-12-②第一次考試"
PAO = os.path.join(BASE, "試跑")

PERSIST = {"高", "中", "低", "無法判斷"}
SUPPLY = {"會", "不會", "不適用", "查不到"}
# 六類驅動型(top_driver_type)——以卡內實際用語為準,列於執行口徑
DRIVERS = {"數量", "價格", "成本", "組合", "一次性", "低基期"}

STEPS = ["第一步", "第二步", "第三步", "第四步", "第五步", "第六步", "第七步", "第八步"]

out = []


def check_arm(arm):
    rowsdir = os.path.join(PAO, arm, "rows")
    carddir = os.path.join(PAO, arm)
    csvs = sorted(glob.glob(os.path.join(rowsdir, "E*.csv")))
    out.append("=" * 70)
    out.append("ARM=%s  csv=%d" % (arm, len(csvs)))
    n_pass = 0
    viol = []
    cons = []
    miss = []
    for p in csvs:
        ev = os.path.basename(p)[:-4]
        raw = io.open(p, encoding="utf-8-sig").read()
        try:
            rr = list(csv.reader(io.StringIO(raw)))
        except Exception as ex:
            out.append("  [PARSE-FAIL] %s : %s" % (ev, ex))
            continue
        hdr, body = rr[0], rr[1:]
        ok = (len(hdr) == 27 and len(body) == 1 and len(body[0]) == 27)
        if ok:
            n_pass += 1
        out.append("  %s cols=%d rows(data)=%d -> %s" % (ev, len(hdr), len(body), "PASS" if ok else "FAIL"))
        if not ok:
            continue
        d = dict(zip(hdr, body[0]))
        if d.get("persistence_overall") not in PERSIST:
            viol.append("%s persistence_overall=%r" % (ev, d.get("persistence_overall")))
        if d.get("supply_catchup") not in SUPPLY:
            viol.append("%s supply_catchup=%r" % (ev, d.get("supply_catchup")))
        if d.get("top_driver_type") not in DRIVERS:
            viol.append("%s top_driver_type=%r" % (ev, d.get("top_driver_type")))
        cards = glob.glob(os.path.join(carddir, "卡-%s-*.md" % ev))
        if not cards:
            miss.append("%s 缺卡" % ev)
            continue
        ct = io.open(cards[0], encoding="utf-8").read()
        lack = [s for s in STEPS if s not in ct]
        if lack:
            miss.append("%s 缺節:%s" % (ev, ",".join(lack)))
        if "contamination_note" not in ct:
            miss.append("%s 缺 contamination_note" % ev)
        # step-8 總判 vs csv persistence_overall
        m8 = re.search(r"persistence_overall[^\n]{0,20}?[:：]\s*\*{0,2}(高|中|低|無法判斷)", ct)
        if m8 and m8.group(1) != d.get("persistence_overall"):
            cons.append("%s persistence_overall csv=%s / card=%s" % (ev, d.get("persistence_overall"), m8.group(1)))
        # step-3 點值 vs csv pred_g2_point
        m3 = re.search(r"(?:兩季|其後兩季|2Q|G2)[^\n]{0,40}?點值\s*\*{0,2}([0-9]+\.[0-9]+)", ct)
        if m3:
            try:
                cv = float(d.get("pred_g2_point") or "nan")
                kv = float(m3.group(1))
                if abs(cv - kv) > 0.005:
                    cons.append("%s pred_g2_point csv=%s / card 點值=%s" % (ev, d.get("pred_g2_point"), m3.group(1)))
            except ValueError:
                pass
    out.append("  --- csv 解析合格數 = %d / %d" % (n_pass, len(csvs)))
    out.append("  --- 取值違規 = %d" % len(viol))
    for v in viol:
        out.append("      " + v)
    out.append("  --- 一致性違規 = %d" % len(cons))
    for v in cons:
        out.append("      " + v)
    out.append("  --- 缺節 = %d" % len(miss))
    for v in miss:
        out.append("      " + v)
    return n_pass, len(viol), len(cons), len(miss)


for arm in ("ds", "opus"):
    check_arm(arm)

io.open(os.path.join(PAO, "_audit_format.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
