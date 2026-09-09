# -*- coding: utf-8 -*-
"""KARST-202 第一步:給 out/events_gatefix.csv 每宗觸發貼「成因」標籤。

原料:
  * 觸發表 out/events_gatefix.csv(正本 events.csv 不改;gatefix 版只多了負債閘補算欄)
  * 本地 SEC 申報索引快取 data/sec/submissions/(KARST-177 補齊,主檔 + pages/ 歷史分頁)

窗:觸發日前 30 個交易日至後 5 個交易日(交易日曆用 data/prices/spy_daily.csv 的日期)。
主成因:窗內「帶成因」的申報之中,申報日最接近觸發日者;同日多份按嚴重次序 CAUSE_ORDER。
副成因:窗內出現過的其他成因(去重,按 CAUSE_ORDER 排)。

讀申報的做法照 research/2026-09-methodology/2026-09-10-①被迫賣每月掃描/scan_forced_selling.py:
CIK 檔名去掉 "CIK"/".json" 就是 entity_id;filings.recent 只載最近約 1,000 份,
filings.files 非空即代表主檔截短,歷史要連 pages/ 一併讀(submissions/README.md 第二節)。

輸出:out/events_cause.csv(逐宗觸發一行,不改任何既有檔)
      out/cause_counts.csv(各成因宗數與佔比)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SUB = ROOT / "data" / "sec" / "submissions"
PAGES = SUB / "pages"
SPY_CSV = ROOT / "data" / "prices" / "spy_daily.csv"

DAYS_BEFORE = 30   # 交易日
DAYS_AFTER = 5     # 交易日

# ---------------------------------------------------------------- 成因字典
# 次序 = 同日多份申報時的嚴重次序(愈前愈嚴重,先取)
CAUSE_ORDER = [
    "破產(8-K 1.03)",
    "重列或不可依賴(8-K 4.02)",
    "退市或不合規通知(8-K 3.01)",
    "稀釋增發(S-1/S-3/424B)",
    "業績(8-K 2.02)",
    "收購或處置(8-K 2.01)",
    "高管離任(8-K 5.02)",
    "指引或其他重大訊息(8-K 7.01/8.01)",
    "重大合約或舉債(8-K 1.01/2.03)",
    "內部人擬售(Form 144)",
    "分拆孤兒(Form 10)",
    # 以下兩格是「窗內有申報但不帶上述成因」的退路,永遠排最後
    "定期報告(10-K/10-Q)",
    "其他申報",
]
CAUSE_RANK = {c: i for i, c in enumerate(CAUSE_ORDER)}
# 帶成因者 = 退路兩格以外
SUBSTANTIVE = set(CAUSE_ORDER[:-2])

DILUTION_PREFIX = ("S-1", "S-3", "424B")
FORM10_FORMS = {"10-12B", "10-12B/A", "10-12G", "10-12G/A"}
PERIODIC = {"10-K", "10-K/A", "10-Q", "10-Q/A", "10-KT", "10-QT",
            "20-F", "20-F/A", "40-F", "40-F/A"}
# 純持股/內部人交易表:數量壓倒性,不當「申報」計(Form 144 例外,見票面「解禁」一項)
OWNERSHIP_NOISE = {"3", "3/A", "4", "4/A", "5", "5/A"}

ITEM_MAP = {
    "1.03": "破產(8-K 1.03)",
    "4.02": "重列或不可依賴(8-K 4.02)",
    "3.01": "退市或不合規通知(8-K 3.01)",
    "2.02": "業績(8-K 2.02)",
    "2.01": "收購或處置(8-K 2.01)",
    "5.02": "高管離任(8-K 5.02)",
    "7.01": "指引或其他重大訊息(8-K 7.01/8.01)",
    "8.01": "指引或其他重大訊息(8-K 7.01/8.01)",
    "1.01": "重大合約或舉債(8-K 1.01/2.03)",
    "2.03": "重大合約或舉債(8-K 1.01/2.03)",
}


def classify(form: str, items: str) -> list[str]:
    """一份申報 -> 零至多個成因。"""
    out: list[str] = []
    f = (form or "").strip().upper()
    if f in OWNERSHIP_NOISE:
        return out
    if f.startswith("8-K"):
        for x in (items or "").split(","):
            c = ITEM_MAP.get(x.strip())
            if c and c not in out:
                out.append(c)
    if f.startswith(DILUTION_PREFIX):
        out.append("稀釋增發(S-1/S-3/424B)")
    if f in ("144", "144/A"):
        out.append("內部人擬售(Form 144)")
    if f in FORM10_FORMS:
        out.append("分拆孤兒(Form 10)")
    if not out:
        out.append("定期報告(10-K/10-Q)" if f in PERIODIC else "其他申報")
    return out


# ---------------------------------------------------------------- 申報快取
def load_filings(entity_id: str) -> list[tuple[str, str, str]]:
    """回傳 [(filingDate, form, items), ...],主檔 recent + 全部歷史分頁。"""
    rows: list[tuple[str, str, str]] = []
    main = SUB / f"CIK{entity_id}.json"
    if not main.exists():
        return rows
    try:
        d = json.load(open(main, encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return rows

    def take(block: dict) -> None:
        forms = block.get("form", []) or []
        dates = block.get("filingDate", []) or []
        items = block.get("items", []) or []
        for i in range(len(forms)):
            rows.append((dates[i] if i < len(dates) else "",
                         forms[i] if i < len(forms) else "",
                         items[i] if i < len(items) else ""))

    filings = d.get("filings", {})
    take(filings.get("recent", {}))
    for pg in filings.get("files", []) or []:
        fp = PAGES / pg.get("name", "")
        if not fp.exists():
            continue
        try:
            take(json.load(open(fp, encoding="utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue
    rows.sort(key=lambda r: r[0])
    return rows


def main() -> None:
    ev = pd.read_csv(OUT / "events_gatefix.csv", encoding="utf-8-sig",
                     parse_dates=["trigger_date"], dtype={"entity_id": "string"},
                     usecols=["entity_id", "trigger_date", "primary_ticker", "name",
                              "industry_kill", "trigger_year"])
    ev["entity_id"] = ev["entity_id"].str.zfill(10)
    print("觸發宗數 %d,公司數 %d" % (len(ev), ev["entity_id"].nunique()))

    cal = pd.read_csv(SPY_CSV, parse_dates=["date"])["date"].sort_values().to_numpy()
    print("交易日曆 %s ~ %s(%d 日)" % (pd.Timestamp(cal[0]).date(),
                                        pd.Timestamp(cal[-1]).date(), len(cal)))

    # 逐宗算窗(用同一條 SPY 交易日曆,不逐家用自己的價格序列,避免停牌令窗長度不一)
    pos = np.searchsorted(cal, ev["trigger_date"].to_numpy(), side="left")
    lo = np.clip(pos - DAYS_BEFORE, 0, len(cal) - 1)
    hi = np.clip(pos + DAYS_AFTER, 0, len(cal) - 1)
    ev["win_start"] = pd.to_datetime(cal[lo])
    ev["win_end"] = pd.to_datetime(cal[hi])

    recs = []
    n_done = 0
    for eid, grp in ev.groupby("entity_id", sort=False):
        filings = load_filings(eid)
        fdates = [r[0] for r in filings]
        for _, r in grp.iterrows():
            ws = r["win_start"].strftime("%Y-%m-%d")
            we = r["win_end"].strftime("%Y-%m-%d")
            i0 = np.searchsorted(fdates, ws, side="left")
            i1 = np.searchsorted(fdates, we, side="right")
            win = filings[i0:i1]

            n_all = len(win)
            n_noise = sum(1 for _, f, _ in win if (f or "").strip().upper() in OWNERSHIP_NOISE)
            best = None          # (rank, |日差|, 成因, 申報日, 表格)
            seen: set[str] = set()
            td = r["trigger_date"]
            for fd, form, items in win:
                for c in classify(form, items):
                    seen.add(c)
                    if c not in SUBSTANTIVE:
                        continue
                    gap = abs((pd.Timestamp(fd) - td).days)
                    key = (gap, CAUSE_RANK[c])
                    if best is None or key < best[0]:
                        best = (key, c, fd, form)

            if best is not None:
                primary, pdate, pform = best[1], best[2], best[3]
            elif "定期報告(10-K/10-Q)" in seen:
                primary, pdate, pform = "定期報告(10-K/10-Q)", "", ""
            elif "其他申報" in seen:
                primary, pdate, pform = "其他申報", "", ""
            else:
                primary, pdate, pform = "無申報", "", ""

            sec = sorted((c for c in seen if c != primary), key=lambda c: CAUSE_RANK[c])
            recs.append({
                "entity_id": eid,
                "trigger_date": td,
                "primary_ticker": r["primary_ticker"],
                "name": r["name"],
                "trigger_year": r["trigger_year"],
                "industry_kill": r["industry_kill"],
                "win_start": ws, "win_end": we,
                "主成因": primary,
                "主成因申報日": pdate,
                "主成因表格": pform,
                "副成因": "|".join(sec),
                "副成因數": len(sec),
                "窗內申報份數": n_all,
                "窗內持股表份數": n_noise,
                "窗內實質申報份數": n_all - n_noise,
            })
        n_done += 1
        if n_done % 500 == 0:
            print("  ...已處理 %d/%d 家" % (n_done, ev["entity_id"].nunique()))

    out = pd.DataFrame(recs)
    out.to_csv(OUT / "events_cause.csv", index=False, encoding="utf-8-sig")
    print("已寫 out/events_cause.csv,%d 行" % len(out))

    cnt = out["主成因"].value_counts().rename_axis("主成因").reset_index(name="宗數")
    cnt["佔比"] = cnt["宗數"] / len(out)
    cnt["公司數"] = [out[out["主成因"] == c]["entity_id"].nunique() for c in cnt["主成因"]]
    cnt.to_csv(OUT / "cause_counts.csv", index=False, encoding="utf-8-sig")
    print(cnt.to_string(index=False))
    print("\n窗內完全無申報(不計持股表)比例:%.4f" %
          float((out["窗內實質申報份數"] == 0).mean()))
    print("窗內連持股表都無比例:%.4f" % float((out["窗內申報份數"] == 0).mean()))


if __name__ == "__main__":
    main()
