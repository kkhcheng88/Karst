# -*- coding: utf-8 -*-
"""KARST-231 交付品:把 A3/transcripts/*.json 的電話會逐字稿注入對應取證包。

**本腳本只寫不跑。** 未加 --apply 時只印它會做什麼,不動任何檔。
跑之前會先把 A3/packets/ 整份複製到 A3/cache/packets_before_transcripts/(只做一次)。

做什麼(逐個 event_id):
  1. 讀 A3/transcripts/<event_id>.json(只處理 report_date <= T1 的檔,檔內已保證)。
  2. 該宗的包 A3/packets/<event_id>.json 的 2_觸發資料.earnings_call_transcript
     由「查不到」改為逐字稿本文:
       - 注入後整包 <= 300 KB -> 直接放 segments(segments_inline)
       - 超過 300 KB      -> 只放路徑 + 段數 + 頭 50 段(head_50)
  3. masking_check 加 transcript_date(= report_date)與
     transcript_within_T1: true,以及 transcript_source。

規矩:不改 A3/packets/ 以外的既有檔;後備 44 沒有包,自動略過;不列公司名或代號。
"""
import argparse
import datetime as dt
import glob
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # .../A3
TR_DIR = os.path.join(HERE, "transcripts")
PK_DIR = os.path.join(HERE, "packets")
BACKUP_DIR = os.path.join(HERE, "cache", "packets_before_transcripts")
LIMIT_BYTES = 300 * 1024
HEAD_N = 50

FIELD = "earnings_call_transcript"


def build_value(doc, packet):
    """回傳 (值, 模式)。先試 inline,超 300 KB 就退回路徑 + 頭 50 段。"""
    segs = doc["segments"]
    inline = dict(
        mode="segments_inline",
        source=doc["source"],
        report_date=doc["report_date"],
        fiscal_year=doc["fiscal_year"],
        fiscal_quarter=doc["fiscal_quarter"],
        n_segments=doc["n_segments"],
        n_chars=doc["n_chars"],
        segments=[dict(speaker=s["speaker"], content=s["content"]) for s in segs],
    )
    probe = json.loads(json.dumps(packet))
    probe["2_觸發資料"][FIELD] = inline
    if len(json.dumps(probe, ensure_ascii=False).encode("utf-8")) <= LIMIT_BYTES:
        return inline, "inline"
    ref = dict(
        mode="segments_by_path",
        source=doc["source"],
        report_date=doc["report_date"],
        fiscal_year=doc["fiscal_year"],
        fiscal_quarter=doc["fiscal_quarter"],
        n_segments=doc["n_segments"],
        n_chars=doc["n_chars"],
        path="A3/transcripts/%s.json" % doc["event_id"],
        head_50=[dict(speaker=s["speaker"], content=s["content"]) for s in segs[:HEAD_N]],
    )
    return ref, "path"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="真的寫入;不加就只印報告不動檔")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(TR_DIR, "E*.json"))
                   + glob.glob(os.path.join(TR_DIR, "B*.json")))
    plan = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            doc = json.load(fh)
        eid = doc["event_id"]
        pk = os.path.join(PK_DIR, eid + ".json")
        if not os.path.exists(pk):
            plan.append((eid, "skip_no_packet", ""))
            continue
        with open(pk, encoding="utf-8") as fh:
            packet = json.load(fh)
        cur = packet.get("2_觸發資料", {}).get(FIELD)
        if isinstance(cur, dict):
            plan.append((eid, "skip_already_injected", ""))
            continue
        # 保險:檔內日期必須 <= T1
        if doc["report_date"] > doc["T1"]:
            plan.append((eid, "skip_report_date_after_T1", doc["report_date"]))
            continue
        _val, mode = build_value(doc, packet)
        plan.append((eid, "inject_" + mode, doc["report_date"]))

    n_inj = sum(1 for _e, s, _d in plan if s.startswith("inject_"))
    print(json.dumps({
        "transcript_files": len(files),
        "to_inject": n_inj,
        "inline": sum(1 for _e, s, _d in plan if s == "inject_inline"),
        "by_path": sum(1 for _e, s, _d in plan if s == "inject_path"),
        "skip_no_packet": sum(1 for _e, s, _d in plan if s == "skip_no_packet"),
        "skip_already_injected": sum(1 for _e, s, _d in plan if s == "skip_already_injected"),
        "skip_after_T1": sum(1 for _e, s, _d in plan if s == "skip_report_date_after_T1"),
        "backup_dir": os.path.relpath(BACKUP_DIR, os.path.dirname(HERE)).replace("\\", "/"),
        "applied": bool(args.apply),
    }, ensure_ascii=False, indent=2))

    if not args.apply:
        for eid, st, d in plan:
            print("  ", eid, st, d)
        print("(dry run — 未改任何檔;要寫入請加 --apply)")
        return

    # --- 先備份 packets/
    if os.path.exists(BACKUP_DIR):
        print("備份目錄已存在,不改動:", BACKUP_DIR, file=sys.stderr)
    else:
        os.makedirs(os.path.dirname(BACKUP_DIR), exist_ok=True)
        shutil.copytree(PK_DIR, BACKUP_DIR)
        print("已備份 packets/ ->", BACKUP_DIR)

    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    for eid, st, _d in plan:
        if not st.startswith("inject_"):
            continue
        with open(os.path.join(TR_DIR, eid + ".json"), encoding="utf-8") as fh:
            doc = json.load(fh)
        pk = os.path.join(PK_DIR, eid + ".json")
        with open(pk, encoding="utf-8") as fh:
            packet = json.load(fh)
        val, _mode = build_value(doc, packet)
        packet["2_觸發資料"][FIELD] = val
        mc = packet.setdefault("masking_check", {})
        mc["transcript_date"] = doc["report_date"]
        mc["transcript_within_T1"] = bool(doc["report_date"] <= doc["T1"])
        mc["transcript_source"] = doc["source"]
        mc["transcript_injected_utc"] = now
        with open(pk, "w", encoding="utf-8") as fh:
            json.dump(packet, fh, ensure_ascii=False, indent=2)
    print("注入完成:", n_inj, "宗")


if __name__ == "__main__":
    main()
