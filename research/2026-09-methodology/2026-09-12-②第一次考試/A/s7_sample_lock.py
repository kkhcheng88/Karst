# -*- coding: utf-8 -*-
"""KARST-222 票 A 第七步:抽樣並鎖定 picks_before_results.md。

執行口徑 v1 第一節:單位「公司—事件」;2015–2024 每年 8 個、2025 上半年 4 個 = 主 84;
後備同規則每年 4 個(2025 兩個)= 44;年內按六個行業桶(桶對應表見 buckets.py,原樣
抄入檔)按入口池比例分層;隨機種子 20260912。

分層用最大餘數法(Hare quota)。抽樣層只含六個具名桶;「其他」桶(未列入六桶的
SIC2)不入抽樣層,原因寫入檔內。**本檔在任何 T1 後欄位或結果被計算之前落檔且不再改動**。
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import random
import sys
from pathlib import Path

import pandas as pd

from buckets import BUCKET_ORDER, bucket_table_md

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
SEED = 20260912
YEARS = [str(y) for y in range(2015, 2026)]


def largest_remainder(shares: dict[str, int], total: int) -> dict[str, int]:
    denom = sum(shares.values())
    if denom == 0:
        return {k: 0 for k in shares}
    exact = {k: v * total / denom for k, v in shares.items()}
    base = {k: int(v) for k, v in exact.items()}
    rem = total - sum(base.values())
    order = sorted(exact, key=lambda k: (-(exact[k] - base[k]), k))
    for k in order[:rem]:
        base[k] += 1
    return base


def main() -> None:
    df = pd.read_parquet(CACHE / "population_improvement.parquet")
    entry = df[(df["pass_p90"] == 1)
               & (df["improvement_type"].isin(["加速", "指引", "兩者"]))
               & (df["excl_going_concern"] != "有")].copy()
    entry["year"] = entry["year"].astype(str)
    print("90 版入口池:%d" % len(entry))
    print("  桶分佈:", entry["bucket"].value_counts().to_dict())
    frame = entry[entry["bucket"].isin(BUCKET_ORDER)]

    picks, backups = [], []
    alloc_rows = []
    for y in YEARS:
        sub = frame[frame["year"] == y]
        n_main = 8 if y != "2025" else 4
        n_bk = 4          # 執行口徑 v1:「另抽同規則後備清單每年 4 個」→ 11 年 = 44
        shares = {b: int((sub["bucket"] == b).sum()) for b in BUCKET_ORDER}
        if sum(shares.values()) < n_main + n_bk:
            raise SystemExit("%s 年入口池不足(%d),抽不出 %d 主 + %d 備"
                             % (y, sum(shares.values()), n_main, n_bk))
        a_main = largest_remainder(shares, n_main)
        a_bk = largest_remainder(shares, n_bk)
        rng = random.Random(SEED * 1000 + int(y))
        for b in BUCKET_ORDER:
            ids = sorted(sub[sub["bucket"] == b]["accessionNumber"].tolist())
            rng.shuffle(ids)
            take_main = ids[: a_main[b]]
            take_bk = ids[a_main[b]: a_main[b] + a_bk[b]]
            for a in take_main:
                picks.append((y, b, a))
            for a in take_bk:
                backups.append((y, b, a))
            alloc_rows.append({"year": y, "bucket": b, "pool": shares[b],
                               "main": a_main[b], "backup": a_bk[b]})
        print("  %s:入口池 %d,主 %d,備 %d" % (y, sum(shares.values()), n_main, n_bk))

    meta = df.set_index("accessionNumber")
    lines = []
    add = lines.append
    add("# ②第一次考試 · 票 A 抽樣鎖定清單(picks_before_results)")
    add("")
    add("> **本檔在任何 T1 之後的價格、財報、結果欄被計算之前落檔;落檔後不得改動。**")
    add("> 落檔時間(UTC):%s" % dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    add("> 隨機種子:%d;抽樣代碼:%s;桶對應表:%s`buckets.py`(原樣抄於下)"
        % (SEED, "`s7_sample_lock.py`", ""))
    add("> 單位:公司—事件(同一公司可出現多於一次);同日同業叢集欄見清單。")
    add("")
    add("## 抽樣規則")
    add("")
    add("- 入口池 = 宇宙門檻 ∧ 當年第 90 百分位(相對 SPY,且相對同業 > 0)∧ "
        "improvement_type ≠ 無。")
    add("- 主清單:2015–2024 每年 8 個、2025 上半年 4 個,合共 **84**;"
        "後備同規則每年 4 個(2025 兩個),合共 **44**。")
    add("- 年內按六個行業桶按入口池比例分層,最大餘數法;桶內以種子 %d 洗牌後取前若干個。"
        % SEED)
    add("- 「其他」桶(未列入下表的 SIC2)不入抽樣層,故不會被抽中;其事件數見執行紀錄。")
    add("- 後備只在主清單事件「取證包建不成」時,按後備清單次序(同年同桶優先)補上。")
    add("- **不得看公司名字後換。**")
    add("")
    add("## 六個行業桶對應表(SIC 兩位數)")
    add("")
    add(bucket_table_md())
    add("")

    def tbl(rows, prefix, label):
        add("## %s(%d 個)" % (label, len(rows)))
        add("")
        add("| # | event_id | 年份 | 行業桶 | 公司—事件(CIK) | 代號 | 申報日 | 反應日 |"
            " SIC2 | improvement_type | g0 | 加速(pp) | 相對SPY | 相對同業 |"
            " 同業叢集 cluster_id |")
        add("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for i, (y, b, a) in enumerate(rows, 1):
            m = meta.loc[a]
            eid = "%s%03d" % (prefix, i)
            add("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                % (i, eid, y, b, a, m["ticker"], m["filingDate"], m["reaction_date"],
                   m["sic2"], m["improvement_type"],
                   "" if pd.isna(m["rev_g0"]) else "%.4f" % m["rev_g0"],
                   "" if pd.isna(m["accel_pp"]) else "%.2f" % m["accel_pp"],
                   "" if pd.isna(m["rel_spy"]) else "%.4f" % m["rel_spy"],
                   "" if pd.isna(m["rel_sic2"]) else "%.4f" % m["rel_sic2"],
                   m["cluster_id"]))
        add("")

    tbl(picks, "E", "主清單")
    tbl(backups, "B", "後備清單")

    add("## 每年每桶數量")
    add("")
    add("| 年 | 桶 | 入口池 | 主取 | 後備取 |")
    add("|---|---|---|---|---|")
    for r in alloc_rows:
        add("| %s | %s | %d | %d | %d |" % (r["year"], r["bucket"], r["pool"],
                                            r["main"], r["backup"]))
    add("")

    payload = "\n".join("%s|%s" % (p[0], p[2]) for p in picks) + "\n---\n" + \
        "\n".join("%s|%s" % (p[0], p[2]) for p in backups)
    sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    add("## 雜湊與清單")
    add("")
    add("- 主清單 84 條 accession(次序即鎖定次序,票 B 分兩批各 42 個:第 1–42、第 43–84):")
    add("")
    for i, (y, b, a) in enumerate(picks, 1):
        add("%d. %s(E%03d,%s,%s)" % (i, a, i, y, b))
    add("")
    add("- 後備清單 44 條 accession(次序即補位次序):")
    add("")
    for i, (y, b, a) in enumerate(backups, 1):
        add("%d. %s(B%03d,%s,%s)" % (i, a, i, y, b))
    add("")
    add("- 清單 SHA-256(上述主+後備 accession 與年份,以換行相接):`%s`" % sha)
    add("")

    out = HERE / "picks_before_results.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (CACHE / "picks.json").write_text(json.dumps(
        {"seed": SEED, "hash": sha,
         "main": [{"event_id": "E%03d" % i, "year": y, "bucket": b, "acc": a}
                  for i, (y, b, a) in enumerate(picks, 1)],
         "backup": [{"event_id": "B%03d" % i, "year": y, "bucket": b, "acc": a}
                    for i, (y, b, a) in enumerate(backups, 1)]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("主 %d,後備 %d,SHA-256 %s" % (len(picks), len(backups), sha))
    print("→", out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
