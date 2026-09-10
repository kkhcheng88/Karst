# -*- coding: utf-8 -*-
"""KARST-204:A7 前置否決閘,兩個門檻各跑一次(0 與 10 個百分點)。

規格出處:`strategy/specs/論點卡與敘事衝擊檢查清單-v1.md` §3.3 A7 ——
「現價隱含收入增速 > 分析員共識收入增速 → 一律判『不買』。
  守門條件:至少三位分析員、更新於最近一季之內。」

**照字面跑不動,而且要寫明為什麼。**
倉內沒有任何時點分析員共識資料(已查:data/ 之下無估值共識來源;
strategy/tools/implied_expectations.py 的隱含預期要逐家手填假設並取即時價,
無法在十四宗歷史事件、二百家公司身上重跑)。守門條件「至少三位分析員」
在歷史考試上一家都滿足不到,照字面 A7 對全樣本一律不觸發,
兩個門檻的結果會完全一樣——那不是結論,是量不到。

所以本檔跑兩版:

  甲 嚴格版(照規格字面):守門條件不成立 → A7 不觸發,零家被剔。
  乙 代理版(明標`推算`,口徑寫死在這裡,列入舉手):
      - 共識收入增速  ← 衝擊前最後一期面板的 TTM 收入按年增速 f_rev_growth_yoy
        (理由:沒有共識就用市場當時看得見的實際增速當錨;它系統性偏低於
         真共識,故代理版偏向多切,方向要記住)
      - 隱含收入增速  ← 令本股市銷率在五年內收斂到同宗事件同 SIC 同業當期
        市銷率中位所需的年化收入增速 = (PS_i / PS_median)^(1/5) − 1
        (理由:規格要的是「現價寫了什麼進去」,在只有機械輸入的情況下,
         市銷率相對同業就是唯一機械算得出的那一項)
      - 觸發:隱含 − 共識 > 門檻(0 或 0.10)→ 判「不買」,不入判斷層
      - 規格的例外閘(最近一季營業利潤率 ÷ 近四季 > 1.3 轉人手覆核)未實作,
        面板無單季營業利潤率;逐家標明。

輸出:out/a7_gate.csv,每家一行,兩個門檻各一欄 True/False。
"""
import csv
import os
from statistics import median

BASE = ("C:/projects/Karst/research/2026-09-methodology/"
        "2026-09-10-①行業殺錯事件籃子")
OUT = f"{BASE}/checklist_test/out"
HORIZON = 5.0


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(f"{BASE}/out/basket_members.csv", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    # 同業市銷率中位:同一宗事件的「同SIC全體」籃子,只取正值
    peer = {}
    for r in rows:
        if r["basket_kind"] != "同SIC全體":
            continue
        v = f(r["f_ps"])
        if v is not None and v > 0:
            peer.setdefault(r["event_id"], []).append(v)
    peer_med = {k: median(v) for k, v in peer.items() if len(v) >= 5}

    out = []
    for r in rows:
        if r["basket_kind"] != "新聞點名":
            continue
        eid = r["event_id"]
        ps = f(r["f_ps"])
        g_con = f(r["f_rev_growth_yoy"])
        pm = peer_med.get(eid)
        g_imp = None
        note = ""
        if ps is None or ps <= 0:
            note = "市銷率缺(收入或市值缺)"
        elif pm is None:
            note = "同業市銷率中位不足五家"
        else:
            g_imp = (ps / pm) ** (1.0 / HORIZON) - 1.0
        gap = (g_imp - g_con) if (g_imp is not None and g_con is not None) else None
        if gap is None and not note:
            note = "衝擊前收入增速缺"
        out.append({
            "event_id": eid, "ticker": r["ticker"], "name": r["name"],
            "f_ps": ps, "peer_ps_median": pm,
            "g_implied_proxy": g_imp, "g_consensus_proxy": g_con, "gap": gap,
            # 甲 嚴格版:守門條件(三位分析員)全樣本不成立 → 永不觸發
            "a7_strict_cut": False,
            "a7_proxy_cut_0pp": (gap is not None and gap > 0.0),
            "a7_proxy_cut_10pp": (gap is not None and gap > 0.10),
            "note": note,
            "margin_exception_checked": False,
        })

    with open(f"{OUT}/a7_gate.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    n = len(out)
    c0 = sum(1 for x in out if x["a7_proxy_cut_0pp"])
    c10 = sum(1 for x in out if x["a7_proxy_cut_10pp"])
    na = sum(1 for x in out if x["gap"] is None)
    print(f"新聞點名 {n} 家;算不出 gap {na} 家")
    print(f"甲 嚴格版:剔 0 家(守門條件無分析員資料,A7 不觸發)")
    print(f"乙 代理版 0 個百分點:剔 {c0} 家,餘 {n - c0}")
    print(f"乙 代理版 10 個百分點:剔 {c10} 家,餘 {n - c10}")


if __name__ == "__main__":
    main()
