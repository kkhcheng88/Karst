# -*- coding: utf-8 -*-
"""KARST-230 第二部:84 包取證包機械品質核六項。
P1 4_財務數列 八季連續(季末單調、間隔 80-100 日、無重複)
P2 訊號季一行標明來源 = EX-99.1 稿內文字
P3 3_截止前文件 各本地檔存在、行數 >= 500、含 MD&A / Item 7 / Item 2
P4 5_同業 同業 SIC 四位數與本公司同(並同一行業桶)、兩大摘錄非空
P5 2_觸發資料 非初步業績(preliminary 不與 results/revenue 同句)
P6 masking_check.latest_data_date <= T1
只讀;輸出 audit_out/part2.json + part2.txt。全檔不列公司名或代號。
"""
import datetime, glob, gzip, json, os, re, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_common as C

ROOT = r"C:\projects\Karst"
GAP_LO, GAP_HI = 80, 100
MIN_LINES = 500
MD_RE = re.compile(r"Management.{0,3}s Discussion|Item\s*7\b|Item\s*2\b", re.I)
PRE_RE = re.compile(r"preliminar", re.I)
RES_RE = re.compile(r"result|revenue|sales|financial", re.I)
# 初步業績語境:preliminary 與 results/revenue 字眼相距不遠
NEAR = 160


def _ent_sic():
    """entity_id -> sic 四位字串(只取兩欄;不取 name)。"""
    d = pd.read_parquet(os.path.join(ROOT, "data", "universe", "entities.parquet"),
                        columns=["entity_id", "sic"])
    d["sic"] = d["sic"].astype(str).str.strip()
    return dict(zip(d["entity_id"], d["sic"]))


def _lines_text(local_gz):
    p = os.path.join(C.EDGAR, local_gz)
    if not os.path.exists(p):
        return None, None
    with gzip.open(p, "rt", encoding="utf-8", errors="replace") as f:
        t = f.read()
    return t, t.count("\n") + 1


def check_packet(path, ents):
    eid = os.path.basename(path)[:-5]
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    r = {"event_id": eid, "fail": [], "detail": {}}

    # ---------- P1 八季連續
    q = d["4_財務數列"]
    rows = q.get("quarters", [])
    pe = []
    for x in rows:
        try:
            pe.append(datetime.date.fromisoformat(str(x.get("period_end"))[:10]))
        except ValueError:
            pe.append(None)
    p1 = {"n_rows": len(rows), "period_end": [str(x) for x in pe]}
    if len(rows) != 8:
        r["fail"].append("P1:季數=%d(應 8)" % len(rows))
    if any(x is None for x in pe):
        r["fail"].append("P1:季末日期無法解讀")
    else:
        if len(set(pe)) != len(pe):
            r["fail"].append("P1:季末日期有重複")
        inc = all(pe[i] > pe[i - 1] for i in range(1, len(pe)))
        p1["monotonic"] = inc
        if not inc:
            r["fail"].append("P1:季末日期非單調上升")
        gaps = [(pe[i] - pe[i - 1]).days for i in range(1, len(pe))]
        p1["gaps"] = gaps
        bad = [g for g in gaps if not (GAP_LO <= g <= GAP_HI)]
        p1["gap_out_of_range"] = bad
        if bad:
            r["fail"].append("P1:季距越界 %s" % bad)
        # 訊號季 = 最後一季
        p1["signal_q_end"] = str(q.get("signal_q_end"))[:10]
        p1["last_q_end"] = str(pe[-1])
        if p1["signal_q_end"] != p1["last_q_end"]:
            r["fail"].append("P1:signal_q_end(%s)≠序列末季(%s)" % (p1["signal_q_end"], p1["last_q_end"]))
    r["detail"]["P1"] = p1

    # ---------- P2 訊號季來源
    src = {str(x.get("period_end"))[:10]: str(x.get("revenue_source", "")) for x in rows}
    sig_q = str(q.get("signal_q_end"))[:10]
    p2 = {"row_source": src.get(sig_q, "(查無此季)"),
          "source_by_row": str(q.get("source_by_row"))[:120],
          "n_rows_marked_ex991": sum(1 for v in src.values() if "EX-99.1" in v)}
    p2["sig_marked"] = "EX-99.1" in p2["row_source"]
    if not p2["sig_marked"]:
        r["fail"].append("P2:訊號季行未標來源=EX-99.1(現值:%s)" % p2["row_source"][:60])
    r["detail"]["P2"] = p2

    # ---------- P3 截止前文件
    s3 = d.get("3_截止前文件", {})
    p3 = []
    for k in sorted(s3):
        v = s3[k]
        if not isinstance(v, dict):
            p3.append({"slot": k, "ok": False, "why": "包內標示「%s」(無本地檔)" % str(v)[:20]})
            r["fail"].append("P3:%s 無檔(%s)" % (k, str(v)[:20]))
            continue
        gz = v.get("local_gz", "")
        t, n = _lines_text(gz)
        e = {"slot": k, "local_gz": gz, "form": v.get("form"),
             "filingDate": v.get("filingDate"), "exists": t is not None,
             "lines": n, "accn": v.get("accession")}
        if t is None:
            e["ok"] = False
            e["why"] = "本地檔不存在"
            r["fail"].append("P3:%s 本地檔不存在" % k)
        else:
            hit = MD_RE.search(t)
            e["mda_hit"] = None if not hit else hit.group(0)[:40]
            e["ok"] = (n >= MIN_LINES and hit is not None)
            if n < MIN_LINES:
                e["why"] = "行數 %d < %d" % (n, MIN_LINES)
                r["fail"].append("P3:%s 行數 %d<%d" % (k, n, MIN_LINES))
            elif hit is None:
                e["why"] = "無 MD&A / Item 7 / Item 2 字樣"
                r["fail"].append("P3:%s 無 MD&A/Item7/Item2 字樣" % k)
        p3.append(e)
    r["detail"]["P3"] = p3

    # ---------- P4 同業
    # 票面兩問:摘錄非空、同業 SIC 四位數與本公司同桶(即不跨行業)。另加記 SIC4 全等
    # (補充四正本:「同 SIC 四位數且同行業桶,不足 5 家退三位數;仍不足標同業資料不足」)。
    s5 = d.get("5_同業與行業", {})
    csic = str(d.get("sic", "")).strip()
    c4 = csic.zfill(4)[:4]
    cbucket = d.get("bucket", "")
    p4 = {"own_sic": csic, "own_sic4": c4, "own_bucket": cbucket,
          "n_listed_peers_same_sic2": s5.get("n_listed_peers_same_sic2"),
          "peer_rule_impl": str(s5.get("peer_rule"))[:110],
          "has_sic4_field": False, "peers": []}
    peers = s5.get("peer_annual_reports_2_largest", [])
    if len(peers) != 2:
        r["fail"].append("P4:同業數=%d(應 2)" % len(peers))
    n_exc_empty = n_sic4_diff = n_bucket_diff = 0
    for i, pr in enumerate(peers):
        pid = str(pr.get("entity_id", ""))
        psic = ents.get(pid, "")
        exc = pr.get("capex_excerpt")
        nexc = len(exc) if isinstance(exc, list) else (1 if exc else 0)
        e = {"idx": i, "entity_id": pid, "packet_sic2": str(pr.get("sic2")),
             "ent_sic": psic, "ent_sic4": (psic.zfill(4)[:4] if psic else ""),
             "bucket_of_sic2": C.bucket_of_sic2(str(pr.get("sic2")).zfill(2)),
             "excerpt_n": nexc, "form": pr.get("form"),
             "annual_found": bool(pr.get("local_gz") or pr.get("accn"))}
        e["sic4_same_as_own"] = bool(psic) and e["ent_sic4"] == c4
        e["bucket_same"] = e["bucket_of_sic2"] == cbucket
        e["packet_sic2_same"] = str(pr.get("sic2")).zfill(2) == c4[:2]
        e["excerpt_ok"] = nexc > 0
        if not e["excerpt_ok"]:
            n_exc_empty += 1
            r["fail"].append("P4:同業%d 年報摘錄空(資本開支摘錄=空)" % (i + 1))
        if not e["bucket_same"]:
            n_bucket_diff += 1
            r["fail"].append("P4:同業%d 桶 %s≠本公司 %s(跨行業)" % (i + 1, e["bucket_of_sic2"], cbucket))
        if not e["sic4_same_as_own"]:
            n_sic4_diff += 1
        p4["peers"].append(e)
    p4["n_excerpt_empty"] = n_exc_empty
    p4["n_sic4_not_equal"] = n_sic4_diff
    p4["n_bucket_diff"] = n_bucket_diff
    p4["rule_sic4_implemented"] = False   # 包內只有 sic2 欄,無 SIC4/三位數退階/「同業資料不足」標籤
    r["detail"]["P4"] = p4

    # ---------- P5 非初步業績
    txt = str(d.get("2_觸發資料", {}).get("ex991_full_text", ""))
    hits, head_hit = [], None
    for m in PRE_RE.finditer(txt):
        seg = txt[max(0, m.start() - NEAR): m.start() + NEAR]
        if RES_RE.search(seg):
            if head_hit is None:
                head_hit = txt[max(0, m.start() - 60): m.start() + 90]
            hits.append(C.mask_text(re.sub(r"\s+", " ", txt[max(0, m.start() - 60): m.start() + 90]).strip())[:150])
    # 甲級:preliminary 出現在稿頭(首 800 字元)且與業績字眼同句 → 頭條式初步業績
    head = txt[:800]
    p5 = {"n_preliminary": len(PRE_RE.findall(txt)), "n_prelim_near_results": len(hits),
          "chars": len(txt),
          "headline_hit": bool(PRE_RE.search(head) and RES_RE.search(head)),
          "samples": hits[:3]}
    r["detail"]["P5"] = p5
    if p5["headline_hit"]:
        r["fail"].append("P5:觸發稿頭條即初步業績(preliminary results)x%d" % len(hits))
    elif hits:
        r["fail"].append("P5:觸發稿含 preliminary 字眼 x%d(免責句/表頭)" % len(hits))

    # ---------- P6 masking
    mc = d.get("masking_check", {})
    t1 = str(d.get("1_事件識別", {}).get("T1_分析截止", ""))[:10]
    ldd = str(mc.get("latest_data_date", ""))[:10]
    p6 = {"latest_data_date": ldd, "T1": t1, "verified": mc.get("verified"),
          "cutoff": str(mc.get("cutoff"))[:30]}
    p6["ok"] = bool(ldd) and bool(t1) and ldd <= t1
    if not p6["ok"]:
        r["fail"].append("P6:latest_data_date(%s) > T1(%s)" % (ldd, t1))
    r["detail"]["P6"] = p6

    r["n_fail"] = len(r["fail"])
    r["pass"] = r["n_fail"] == 0
    return r


def main():
    ents = _ent_sic()
    fs = sorted(glob.glob(os.path.join(C.HERE, "packets", "E*.json")))
    res = [check_packet(f, ents) for f in fs]
    npass = sum(1 for r in res if r["pass"])
    by_item = {}
    for r in res:
        for it in sorted({f.split(":")[0] for f in r["fail"]}):
            by_item.setdefault(it, []).append(r["event_id"])
    sub = {
        "P4_摘錄空": [r["event_id"] for r in res if r["detail"]["P4"]["n_excerpt_empty"]],
        "P4_跨行業桶": [r["event_id"] for r in res if r["detail"]["P4"]["n_bucket_diff"]],
        "P4_SIC4 不全等": [r["event_id"] for r in res if r["detail"]["P4"]["n_sic4_not_equal"]],
        "P5_頭條式初步業績": [r["event_id"] for r in res if r["detail"]["P5"]["headline_hit"]],
    }
    outf = {"n_packets": len(res), "n_pass": npass, "n_fail": len(res) - npass,
            "by_item": {k: {"n": len(v), "event_ids": v} for k, v in sorted(by_item.items())},
            "sub": {k: {"n": len(v), "event_ids": v} for k, v in sub.items()},
            "packets": res}
    with open(os.path.join(C.OUT, "part2.json"), "w", encoding="utf-8") as f:
        json.dump(outf, f, ensure_ascii=False, indent=1)
    L = []
    L.append("84 包機械品質核:共 %d 包,六項全過 %d 包,至少一項未過 %d 包" % (len(res), npass, len(res) - npass))
    L.append("逐項未過(每包只計一次):")
    for k, v in sorted(by_item.items()):
        L.append("  %s:未過 %d 包 — %s" % (k, len(v), ", ".join(v)))
    L.append("逐項全過包數:P1 %d、P2 %d、P3 %d、P4 %d、P5 %d、P6 %d" % (
        sum(1 for r in res if not any(f.startswith("P1") for f in r["fail"])),
        sum(1 for r in res if not any(f.startswith("P2") for f in r["fail"])),
        sum(1 for r in res if not any(f.startswith("P3") for f in r["fail"])),
        sum(1 for r in res if not any(f.startswith("P4") for f in r["fail"])),
        sum(1 for r in res if not any(f.startswith("P5") for f in r["fail"])),
        sum(1 for r in res if not any(f.startswith("P6") for f in r["fail"])),
    ))
    L.append("P4 細分:")
    for k, v in sub.items():
        L.append("  %s:%d 包 %s" % (k, len(v), ", ".join(v)))
    L.append("")
    for r in res:
        if r["pass"]:
            continue
        L.append("-" * 70)
        L.append("[%s] 不合格 %d 項" % (r["event_id"], r["n_fail"]))
        for f in r["fail"]:
            L.append("    × " + f)
        L.append("    P1 " + json.dumps(r["detail"]["P1"], ensure_ascii=False))
        L.append("    P2 " + json.dumps(r["detail"]["P2"], ensure_ascii=False))
        L.append("    P3 " + json.dumps(r["detail"]["P3"], ensure_ascii=False))
        L.append("    P4 " + json.dumps(r["detail"]["P4"], ensure_ascii=False))
        L.append("    P5 " + json.dumps(r["detail"]["P5"], ensure_ascii=False)[:400])
    with open(os.path.join(C.OUT, "part2.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L.split("\n") if isinstance(L, str) else L[:24]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
