# -*- coding: utf-8 -*-
"""KARST-228 核查工具:在某一事件的「包內文件」與「包列本地文件」中定位字串。

用法: PYTHONUTF8=1 python audit_lookup.py E001 "查詢字串" [--ctx 1]
搜尋範圍(全部都是該事件取證包所指向的東西):
  1. 包內 EX-99.1 全文(packet `2_觸發資料.ex991_full_text`)
  2. 包內其他文字欄位(1_事件識別、4_財務數列、5_同業與行業、6_價格狀態、7_共識、masking_check)
  3. packet `3_截止前文件` 各項的 local_gz、`2_觸發資料.local_8k`、`5_同業與行業.peer_annual_reports_2_largest[].local_gz`
     —— 全部在 A/edgar_cache/(gzip 純文字)
輸出:檔名 + 行號 + 該行片段。找不到就寫 NOT FOUND。
"""
import gzip, io, json, os, re, sys

BASE = r"C:/projects/Karst/research/2026-09-methodology/2026-09-12-②第一次考試"
CACHE = os.path.join(BASE, "A", "edgar_cache")
TXT = os.path.join(BASE, r"試跑", "_audit_txt")


def packet_txt_path(e):
    """把 packet 的文字欄位攤成可供 grep 的純文字檔(只做一次,存 _audit_txt/)。"""
    os.makedirs(TXT, exist_ok=True)
    p = os.path.join(TXT, e + ".packet.txt")
    if not os.path.exists(p):
        d = json.load(io.open(os.path.join(BASE, "A2", "packets", e + ".json"), encoding="utf-8"))
        lines = []
        for sec in ("1_事件識別", "2_觸發資料", "4_財務數列", "5_同業與行業", "6_價格狀態", "7_共識", "masking_check"):
            v = d.get(sec)
            if isinstance(v, dict):
                for k, vv in v.items():
                    if isinstance(vv, (dict, list)):
                        vv = json.dumps(vv, ensure_ascii=False)
                    lines.append("[%s.%s] %s" % (sec, k, str(vv)))
            else:
                lines.append("[%s] %s" % (sec, str(v)))
        io.open(p, "w", encoding="utf-8").write("\n".join(lines))
    return p


def local_files(e):
    d = json.load(io.open(os.path.join(BASE, "A2", "packets", e + ".json"), encoding="utf-8"))
    out = []
    for k, v in (d.get("3_截止前文件") or {}).items():
        if isinstance(v, dict) and v.get("local_gz"):
            out.append((v["local_gz"], "%s / %s / filingDate=%s" % (k, v.get("form"), v.get("filingDate"))))
    l8 = (d.get("2_觸發資料") or {}).get("local_8k")
    if l8:
        out.append((l8, "2_觸發資料.local_8k"))
    for x in (d.get("5_同業與行業") or {}).get("peer_annual_reports_2_largest", []) or []:
        if isinstance(x, dict) and x.get("local_gz"):
            out.append((x["local_gz"], "同業年報 %s" % x.get("ticker")))
    return out


def search(e, q, ctx=0):
    res = []
    for path, label in [(packet_txt_path(e), "包內文字欄位(packet)")]:
        L = io.open(path, encoding="utf-8").read().split("\n")
        offs = [i for i, l in enumerate(L, 1) if l.startswith("[2_觸發資料.ex991_full_text]")]
        off = offs[0] if offs else 10 ** 9
        for i, ln in enumerate(L, 1):
            if q.lower() in ln.lower():
                tag = "包內 EX-99.1 全文第 %d 行(packet.txt:%d)" % (i - off + 1, i) if i > off else "%s :%d [%s]" % (os.path.basename(path), i, label)
                res.append((tag, ln.strip()[:300]))
    for fn, label in local_files(e):
        fp = os.path.join(CACHE, fn)
        if not os.path.exists(fp):
            res.append(("MISSING %s" % fn, label))
            continue
        data = gzip.open(fp, "rt", encoding="utf-8", errors="replace").read().split("\n")
        for i, ln in enumerate(data, 1):
            if q.lower() in ln.lower():
                res.append(("%s :%d [%s]" % (fn, i, label), ln.strip()[:300]))
    return res


if __name__ == "__main__":
    e = sys.argv[1]
    q = sys.argv[2]
    r = search(e, q)
    print("### %s <<%s>>  hits=%d" % (e, q, len(r)))
    for a, b in r[:12]:
        print("  @", a)
        print("     ", b)
    if not r:
        print("   NOT FOUND")
