# -*- coding: utf-8 -*-
"""KARST-226 票 A″ 第九步(執行口徑 v1.2):抽樣並鎖定 picks_before_results.md。

與 `A2/s7_sample_lock.py` 之別:
  ①入口池改用 v1.2 的定義(`entry_pool == 1`:宇宙 ∧ 2015 後 ∧ 過前視窗第 90 百分位 ∧
    同業相對為正 ∧ 稿內有訊號季收入 ∧ 非盤中公開 ∧ 非疑更早公開 ∧ 歷史季度 T1 前已申報
    ∧ 適用性 F 過 ∧ 非金融 SIC);
  ②檔內說明的規格正本指向 v1.2 修訂頁;移除 v1.1 的「經營現金流」等舊閘字眼;
  ③對照清單改為 A2 已作廢的鎖定清單(`A2/cache/picks.json`);
  ④表內不再列公司代號(只留 CIK),並補 `release_timing` 一欄。
抽樣規則、種子、分層法一字不改:2015–2024 每年 8 個主 + 4 個後備,2025 上半年 4 個主 +
4 個後備,合共 84 主 + 44 後備;年內按六個行業桶按入口池比例分層(最大餘數法);
隨機種子 20260912。**本檔在任何 T1 後欄位或結果被計算之前落檔且不再改動。**
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
    entry = df[df["entry_pool"] == 1].copy()
    entry["year"] = entry["year"].astype(str)
    print("入口池(v1.2):%d" % len(entry))
    print("  桶分佈:", entry["bucket"].value_counts().to_dict())
    frame = entry[entry["bucket"].isin(BUCKET_ORDER)]
    print("  六桶內(入抽樣層):%d;其他桶(不入層):%d"
          % (len(frame), len(entry) - len(frame)))

    picks, backups = [], []
    alloc_rows = []
    for y in YEARS:
        sub = frame[frame["year"] == y]
        n_main = 8 if y != "2025" else 4
        n_bk = 4          # v1.2 沿用 v1:後備同規則每年 4 個,2025 亦 4 個 → 11 年 = 44
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
    add("# ②第一次考試 · 票 A″ 抽樣鎖定清單(picks_before_results)")
    add("")
    add("> **本檔在任何 T1 之後的價格、財報、結果欄被計算之前落檔;落檔後不得改動。**")
    add("> 落檔時間(UTC):%s"
        % dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    add("> 隨機種子:%d;抽樣代碼:`s7_sample_lock.py`;桶對應表:`buckets.py`(原樣抄於下)"
        % SEED)
    add("> 單位:公司—事件(同一公司可出現多於一次)。")
    add("")
    add("## 抽樣規則")
    add("")
    add("- 規格正本:`../../執行口徑——②第一次考試-v1.2(修訂頁).md`(第 1–10 項);"
        "原口徑 `../../執行口徑——②第一次考試-v1.md` 第一節。")
    add("- 入口池(v1.2)一字記之:`宇宙 ∧ 2015 後(2014 只作暖身窗口)∧ 反應日相對 SPY "
        "≥ 該事件前視窗第 90 百分位 且 相對同業為正 ∧ 公開改善(加速 ≥2pp 或收入指引上調,"
        "至少一項)∧ 稿內有訊號季收入 ∧ 非盤中公開 ∧ 非疑更早公開(反應日前一日|報酬| ≤ 8%)∧ "
        "**加速所用歷史季度 T1 前已申報** ∧ 適用性 F 過 ∧ 非金融 SIC(60–64、67)∧ 非併購`。")
    add("- 百分位門檻用**該事件反應日之前 252 個交易日窗口**內、宇宙內事件的相對 SPY 反應"
        "第 90 百分位(窗口內不足 300 宗則退 504 日;再不足則標資料不足,不入池)。"
        "門檻為敘述統計,不逐日重算。")
    add("- 主清單:2015–2024 每年 8 個、2025 上半年 4 個,合共 **84**;"
        "後備同規則**每年 4 個,2025 亦 4 個**,合共 **44**。")
    add("- 年內按六個行業桶按入口池比例分層,最大餘數法;桶內以種子 %d 洗牌後取前若干個。"
        % SEED)
    add("- 「其他」桶(未列入下表的 SIC2)不入抽樣層,故不會被抽中;其事件數見執行紀錄。")
    add("- 後備只在主清單事件因 **第 4 步(稿內訊號季收入)、第 6 步(適用性 F)、補三"
        "(歷史季度 T1 前已申報)**任一項事後核不過、以致取證包建不成時,按後備清單次序"
        "(同年同桶優先)補上;**每個補位都要記明原因**。其他任何理由(包括看過公司名字、"
        "看過結果)**不得**換位。")
    add("- **不得看公司名字後換。**")
    add("- **純機械聲明**:本清單由 `s7_sample_lock.py` 以固定種子一次抽出,逐格按入口池"
        "比例分層;抽出之後**沒有任何人手換名、沒有事後挑選**。抽樣只讀 accessionNumber、"
        "年份、行業桶,不讀公司名;本清單亦不列公司代號。")
    add("")
    add("## 六個行業桶對應表(SIC 兩位數)")
    add("")
    add(bucket_table_md())
    add("")

    def tbl(rows, prefix, label):
        add("## %s(%d 個)" % (label, len(rows)))
        add("")
        add("| # | event_id | 年份 | 行業桶 | 公司—事件(CIK) | accessionNumber |"
            " 申報日 | 反應日 | 公開時段 | SIC2 | improvement_type | 稿內g0 | 加速(pp) |"
            " 相對SPY | 相對同業 |")
        add("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for i, (y, b, a) in enumerate(rows, 1):
            m = meta.loc[a]
            eid = "%s%03d" % (prefix, i)
            add("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                % (i, eid, y, b, m["cik"], a, m["filingDate"], m["reaction_date"],
                   m["release_timing"], m["sic2"], m["improvement_type"],
                   "" if pd.isna(m["rev_g0_text"]) else "%.4f" % m["rev_g0_text"],
                   "" if pd.isna(m["accel_pp_text"]) else "%.2f" % m["accel_pp_text"],
                   "" if pd.isna(m["rel_spy"]) else "%.4f" % m["rel_spy"],
                   "" if pd.isna(m["rel_sic2"]) else "%.4f" % m["rel_sic2"]))
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

    # ---- 與 A2 已作廢的鎖定清單對照(執行紀錄用)
    a2p = HERE.parent / "A2" / "cache" / "picks.json"
    cmp: dict = {"hash_v12": sha}
    if a2p.exists():
        a2 = json.loads(a2p.read_text(encoding="utf-8"))
        a2_main = [p["acc"] for p in a2["main"]]
        a2_bk = [p["acc"] for p in a2["backup"]]
        m = [p[2] for p in picks]
        b = [p[2] for p in backups]
        inu = set(df.loc[df["in_universe"] == 1, "accessionNumber"])
        cmp.update({
            "a2_main_n": len(a2_main), "a2_main_still_in_universe": int(sum(a in inu for a in a2_main)),
            "a2_main_in_v12_main": int(len(set(a2_main) & set(m))),
            "a2_main_in_v12_backup": int(len(set(a2_main) & set(b))),
            "a2_backup_in_v12_main": int(len(set(a2_bk) & set(m))),
            "v12_main_not_in_a2_lists": int(len(set(m) - set(a2_main) - set(a2_bk))),
        })
        print("與 A2 主清單重疊 %d / 84" % cmp["a2_main_in_v12_main"])
    (CACHE / "picks_compare_a2.json").write_text(
        json.dumps(cmp, ensure_ascii=False, indent=1), encoding="utf-8")
    print("主 %d,後備 %d,SHA-256 %s" % (len(picks), len(backups), sha))
    print("→", out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
