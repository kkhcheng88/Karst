# -*- coding: utf-8 -*-
"""KARST-228 核查輔助:列出十個取證包的關鍵欄位(T1、文件清單、local_gz、申報日)。只讀不寫。"""
import io, json, os, sys

BASE = r"C:/projects/Karst/research/2026-09-methodology/2026-09-12-②第一次考試"
EVENTS = ["E001", "E009", "E017", "E025", "E033", "E041", "E049", "E057", "E065", "E073"]
OUT = os.path.join(BASE, r"試跑\_audit_packet_fields.txt")

lines = []
for e in EVENTS:
    p = os.path.join(BASE, "A2", "packets", e + ".json")
    d = json.load(io.open(p, encoding="utf-8"))
    ident = d["1_事件識別"]
    lines.append("=" * 70)
    lines.append("%s %s  T1=%s  T0=%s" % (e, d.get("ticker"), ident.get("T1_分析截止"), ident.get("T0_公布時間_美東")))
    lines.append("  acceptance_cutoff_packet=%s  signal_q=%s  8K_items=%s  acc=%s" % (
        d.get("evidence_cutoff"), ident.get("fiscal_quarter"), ident.get("8-K_items"), ident.get("accessionNumber")))
    trig = d.get("2_觸發資料", {})
    lines.append("  觸發: local_8k=%s  ex991_chars=%s  transcript=%s" % (
        trig.get("local_8k"), trig.get("ex991_chars"), trig.get("earnings_call_transcript")))
    tf = d.get("3_截止前文件", {})
    for k, v in tf.items():
        if isinstance(v, dict):
            lines.append("  3_截止前文件[%s] form=%s filingDate=%s reportDate=%s accessions=%s local=%s" % (
                k, v.get("form"), v.get("filingDate"), v.get("reportDate"), v.get("accession"), v.get("local_gz")))
        else:
            lines.append("  3_截止前文件[%s]=%s" % (k, str(v)[:200]))
    fin = d.get("4_財務數列", {})
    lines.append("  4_財務數列: source=%s signal_q_end=%s g0=%s prev_q=%s accel=%s nq=%s" % (
        fin.get("source"), fin.get("signal_q_end"), fin.get("g0_signal_q_yoy"),
        fin.get("prev_q_yoy"), fin.get("accel_pp"), len(fin.get("quarters", []))))
    pe = d.get("5_同業與行業", {})
    pl = pe.get("peer_annual_reports_2_largest", [])
    lines.append("  5_同業: n_peers=%s peers2=%s" % (
        pe.get("n_listed_peers_same_sic2"),
        [(x.get("ticker"), x.get("accession"), x.get("local_gz"), x.get("form")) for x in pl] if isinstance(pl, list) else str(pl)[:200]))
    lines.append("  6_價格狀態: %s" % json.dumps(d.get("6_價格狀態", {}), ensure_ascii=False)[:400])
    lines.append("  7_共識: %s | %s" % (d.get("7_共識", {}).get("analyst_consensus"), str(d.get("7_共識", {}).get("note"))[:120]))
    lines.append("  masking: %s" % json.dumps(d.get("masking_check", {}), ensure_ascii=False)[:400])

io.open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("wrote", OUT, len(lines), "lines")
