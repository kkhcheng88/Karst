# -*- coding: utf-8 -*-
"""KARST-231 逐字稿取數:對 A3 主 84 + 後備 44 事件,逐宗查 DefeatBeta
(HuggingFace dataet defeatbeta/yahoo-finance-data / stock_earning_call_transcripts)
的訊號季電話會逐字稿。

規則(見票面):
  - report_date 必須 > signal_q_end 且 <= T1(反應日);> T1 者記「越界」不存。
  - 輸出 A3/transcripts/<event_id>.json(不含 ticker/公司名)。
  - 逐宗寫一行到 coverage.csv(不含 ticker/公司名),log 只記 event_id。

只用於取數,不改 A3/packets/ 或 A3 其他既有檔。
"""
import csv
import datetime as dt
import json
import os
import re
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))          # .../A3/transcripts
A3 = os.path.dirname(HERE)                                  # .../A3
ROOT = os.path.dirname(A3)                                  # .../②第一次考試

SOURCE = "defeatbeta stock_earning_call_transcripts"
DATASET = "defeatbeta/yahoo-finance-data"
OUT_LOG = os.path.join(HERE, "_fetch_log.jsonl")
OUT_CSV = os.path.join(HERE, "coverage.csv")

QNA_PAT = re.compile(
    r"question[\s\-–]*and[\s\-–]*answer|question[\s\-–]*&\s*answer|\bq\s*&\s*a\b",
    re.IGNORECASE,
)
QNA_SPEAKERS = {"analysts", "analyst", "operator"}


# ---------------------------------------------------------------- universe
def load_events():
    """回傳 [{event_id, cohort, year, ticker, cik, fq_a3, signal_q_end, t1, t0_date}]"""
    ev = []
    # --- 主 84:packets
    pkdir = os.path.join(A3, "packets")
    for fn in sorted(os.listdir(pkdir)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(pkdir, fn), encoding="utf-8") as fh:
            p = json.load(fh)
        e1 = p["1_事件識別"]
        f4 = p["4_財務數列"]
        ev.append(
            dict(
                event_id=p["event_id"],
                cohort="main",
                year=None,  # 由 picks 檔補
                ticker=p["ticker"],
                cik=p["cik"],
                fq_a3=e1["fiscal_quarter"],
                signal_q_end=str(f4.get("signal_q_end") or "")[:10],
                t1=parse_t1(e1["T1_分析截止"]),
                t0_date=str(e1["T0_公布時間_美東"])[:10],
            )
        )
    # --- 後備 44:由 picks 檔的 accession 對 entry_pool
    txt = open(os.path.join(A3, "picks_before_results.md"), encoding="utf-8").read()
    bak = re.findall(r"^\s*(\d+)\.\s*(\S+?)\((B\d{3}),(\d{4}),", txt, re.M)
    ep = {}
    with open(os.path.join(A3, "entry_pool.csv"), encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            ep[r["accessionNumber"]] = r
    for _n, acc, eid, yr in bak:
        r = ep[acc]
        ev.append(
            dict(
                event_id=eid,
                cohort="backup",
                year=int(yr),
                ticker=r["ticker"],
                cik=r["cik"].zfill(10),
                fq_a3=r["fiscal_quarter"],
                signal_q_end=str(r["signal_q_end"])[:10],
                t1=str(r["reaction_date"])[:10],
                t0_date=str(r["reaction_date"])[:10],  # 後備無 T0,以反應日代
            )
        )
    # 主清單年份由 picks 檔補齊
    mainyr = dict(re.findall(r"^\|\s*\d+\s*\|\s*(E\d{3})\s*\|\s*(\d{4})\s*\|", txt, re.M))
    for e in ev:
        if e["cohort"] == "main":
            e["year"] = int(mainyr[e["event_id"]])
    return ev


def parse_t1(s):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", str(s))
    return m.group(1) if m else None


def d(s):
    return dt.date.fromisoformat(s[:10])


def _parse_ok(s):
    try:
        d(s)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- selection
def pick_row(rows, signal_q_end, t1, t0_date):
    """rows: [(fy, fq, report_date_str)] → (status, reason, chosen_row, days_late)

    窗口 = (signal_q_end, T1];窗內多於一列時取最接近 T0(8-K 公布日)那列。
    """
    win_lo = d(signal_q_end)
    win_hi = d(t1)
    if not rows:
        return "缺", "公司整體無逐字稿", None, None
    parsed = []
    for fy, fq, rd in rows:
        try:
            parsed.append((fy, fq, rd, d(rd)))
        except Exception:
            continue
    inside = [r for r in parsed if win_lo < r[3] <= win_hi]
    if inside:
        anchor = d(t0_date) if t0_date else win_hi
        chosen = min(inside, key=lambda r: (abs((r[3] - anchor).days), r[3]))
        return "有", "", chosen, 0
    # 越界窗取 45 日:電話會本身在 T0 開,但 Yahoo 的 report_date 是收錄日,
    # 可以遲幾日到幾星期;45 日仍遠短於一季(91 日),不會撈到下一季的會。
    late = [r for r in parsed if win_hi < r[3] <= win_hi + dt.timedelta(days=45)]
    if late:
        n = min(late, key=lambda r: r[3])
        return "越界", "有稿但 report_date 在 T1 之後", n, (n[3] - win_hi).days
    return "缺", "窗口 (signal_q_end, T1+45d] 內無稿", None, None


# ---------------------------------------------------------------- main
def main():
    from defeatbeta_api.data.ticker import Ticker

    events = load_events()
    tc = {}  # ticker -> Transcripts 物件(同一公司多宗事件時省一次查詢)
    print(f"events: {len(events)} (main {sum(1 for e in events if e['cohort']=='main')}, "
          f"backup {sum(1 for e in events if e['cohort']=='backup')})", flush=True)

    # 可續跑:已完成(狀態非「錯誤」)的事件跳過;--max N 限本次處理數
    done = {}
    if os.path.exists(OUT_LOG):
        with open(OUT_LOG, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                done[r["event_id"]] = r
    FIELDS = ["event_id", "cohort", "year", "fq_a3", "signal_q_end", "T1", "status",
              "reason", "def_fiscal_year", "def_fiscal_quarter", "report_date",
              "days_from_T0", "n_segments", "n_chars", "has_qna",
              "prev_tr_date", "next_tr_date", "err"]
    for r in done.values():          # 舊行補齊新欄位
        for k in FIELDS:
            r.setdefault(k, "")
    prior = [r for r in done.values() if r["status"] != "錯誤"]
    maxn = None
    if "--max" in sys.argv:
        maxn = int(sys.argv[sys.argv.index("--max") + 1])
    force = set()
    if "--only" in sys.argv:
        force = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    if force:
        prior = [r for r in prior if r["event_id"] not in force]

    log = open(OUT_LOG, "a", encoding="utf-8")
    rows_out = list(prior)
    seen = {r["event_id"] for r in prior}
    todo = [e for e in events if e["event_id"] not in seen]
    if maxn:
        todo = todo[:maxn]
    print(f"resume: done {len(prior)}, todo {len(todo)}", flush=True)
    t_start = time.time()
    for i, e in enumerate(todo, 1):
        t0 = time.time()
        rec = dict(
            event_id=e["event_id"], cohort=e["cohort"], year=e["year"],
            fq_a3=e["fq_a3"], signal_q_end=e["signal_q_end"], T1=e["t1"],
            status="", reason="", def_fiscal_year="", def_fiscal_quarter="",
            report_date="", days_from_T0="", n_segments="", n_chars="", has_qna="",
            prev_tr_date="", next_tr_date="", err="",
        )
        try:
            if e["ticker"] not in tc:
                tc[e["ticker"]] = Ticker(e["ticker"]).earning_call_transcripts()
            tl = tc[e["ticker"]]
            try:
                lst = tl.get_transcripts_list()
                rows = [(int(r.fiscal_year), int(r.fiscal_quarter), str(r.report_date))
                        for r in lst.itertuples()]
            except Exception:
                rows = []
            status, reason, chosen, days_late = pick_row(
                rows, e["signal_q_end"], e["t1"], e["t0_date"])
            rec["status"], rec["reason"] = status, reason
            if status == "有":
                fy, fq, rd, _dd = chosen
                rec["def_fiscal_year"], rec["def_fiscal_quarter"] = fy, fq
                rec["report_date"] = rd
                rec["days_from_T0"] = (_dd - d(e["t0_date"])).days
                df = tl.get_transcript(fy, fq)
                segs = [
                    dict(paragraph_number=int(r.paragraph_number),
                         speaker="" if r.speaker is None else str(r.speaker),
                         content="" if r.content is None else str(r.content))
                    for r in df.itertuples()
                ]
                n_chars = sum(len(s["content"]) for s in segs)
                has_qna = bool(QNA_PAT.search(" ".join(s["content"] for s in segs))) or any(
                    s["speaker"].strip().lower() in QNA_SPEAKERS for s in segs
                )
                rec["n_segments"], rec["n_chars"], rec["has_qna"] = len(segs), n_chars, has_qna
                doc = dict(
                    event_id=e["event_id"],
                    cik=e["cik"],
                    fiscal_year=fy,
                    fiscal_quarter=fq,
                    a3_signal_quarter=e["fq_a3"],
                    signal_q_end=e["signal_q_end"],
                    report_date=rd,
                    T0_date=e["t0_date"],
                    T1=e["t1"],
                    days_from_T0=rec["days_from_T0"],
                    n_segments=len(segs),
                    n_chars=n_chars,
                    has_qna=has_qna,
                    source=SOURCE,
                    dataset=DATASET,
                    dataset_update_time=DATASET_UPDATE,
                    client="defeatbeta-api",
                    fetch_time_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    segments=segs,
                )
                with open(os.path.join(HERE, e["event_id"] + ".json"), "w", encoding="utf-8") as fh:
                    json.dump(doc, fh, ensure_ascii=False)
            elif status == "越界":
                rec["def_fiscal_year"], rec["def_fiscal_quarter"] = chosen[0], chosen[1]
                rec["report_date"] = chosen[2]
                rec["days_from_T0"] = days_late
            else:  # 缺 —— 記最近的前後一稿,用來看是整段無稿還是單季漏洞
                ds = sorted(d(rd) for _f, _q, rd in rows if _parse_ok(rd))
                lo, hi = d(e["signal_q_end"]), d(e["t1"])
                prevs = [x for x in ds if x <= lo]
                nexts = [x for x in ds if x > hi]
                rec["prev_tr_date"] = str(prevs[-1]) if prevs else ""
                rec["next_tr_date"] = str(nexts[0]) if nexts else ""
        except Exception as ex:
            rec["status"] = "錯誤"
            rec["reason"] = type(ex).__name__
            rec["err"] = str(ex)[:200]
        rows_out.append(rec)
        log.write(json.dumps(rec, ensure_ascii=False) + "\n")
        log.flush()
        print(f"[{i}/{len(todo)}] {rec['event_id']} {rec['cohort']} {rec['status']} "
              f"{rec['reason']} seg={rec['n_segments']} ch={rec['n_chars']} "
              f"({round(time.time()-t0,1)}s)", flush=True)

    rows_out.sort(key=lambda r: r["event_id"])
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows_out)
    log.close()
    print(f"done in {round(time.time()-t_start,1)}s -> {OUT_CSV}", flush=True)


DATASET_UPDATE = ""

if __name__ == "__main__":
    from defeatbeta_api.client.hugging_face_client import HuggingFaceClient

    DATASET_UPDATE = HuggingFaceClient().get_data_update_time()
    main()
