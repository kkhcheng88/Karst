# -*- coding: utf-8 -*-
"""KARST-232 第一步:換位後主清單(最終版)`cache/picks_final.json` + 可直接抄入
`picks_final.md` 的表身(只印,不寫中文檔;md 由 Write 工具落)。

換位三宗:
  E056 → B028(指引人手核不過)
  E070 → B034(指引人手核不過)
  E067 → B033(與十宗試跑重疊,結果已打開)
全部按「同年同桶優先、已有後備次序」;已用過的後備(B028、B034)不再用。
原鎖定檔 `picks_before_results.md` 與 `picks_after_guidance_check.md` 一字不改。

次序照原鎖定檔槽位;檔案名沿用槽位(event_id 欄另記來源事件 id)。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

SWAPS = {
    "E056": dict(src="B028", reason="指引上調人手核不過(稿內為 reiterate 舊指引)"),
    "E070": dict(src="B034", reason="指引上調人手核不過(上調的是經營利潤率)"),
    "E067": dict(src="B033", reason="與十宗試跑重疊(結果已打開)"),
}


def sha(pairs_main, pairs_back) -> str:
    payload = "\n".join("%s|%s" % (y, a) for y, a in pairs_main) + "\n---\n" + \
        "\n".join("%s|%s" % (y, a) for y, a in pairs_back)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    picks = json.loads((CACHE / "picks.json").read_text(encoding="utf-8"))
    main_l = picks["main"]
    back_l = picks["backup"]
    bmap = {b["event_id"]: b for b in back_l}
    used = {v["src"] for v in SWAPS.values()}

    final, swap_recs = [], []
    for p in main_l:
        sw = SWAPS.get(p["event_id"])
        if not sw:
            final.append(dict(slot=p["event_id"], event_id=p["event_id"], year=p["year"],
                              bucket=p["bucket"], acc=p["acc"], swapped=False))
            continue
        b = bmap[sw["src"]]
        if b["year"] != p["year"] or b["bucket"] != p["bucket"]:
            raise SystemExit("換位不按同年同桶:%s → %s" % (p["event_id"], sw["src"]))
        final.append(dict(slot=p["event_id"], event_id=b["event_id"], year=b["year"],
                          bucket=b["bucket"], acc=b["acc"], swapped=True,
                          replaced_event=p["event_id"], replaced_acc=p["acc"],
                          reason=sw["reason"], source="後備清單"))
        swap_recs.append(dict(slot=p["event_id"], out_event=p["event_id"], out_acc=p["acc"],
                              out_year=p["year"], out_bucket=p["bucket"],
                              in_event=b["event_id"], in_acc=b["acc"],
                              in_year=b["year"], in_bucket=b["bucket"],
                              same_year_bucket=True, reason=sw["reason"],
                              backup_rank=[x["event_id"] for x in back_l].index(b["event_id"]) + 1))
    assert len(final) == 84, len(final)
    assert len({f["acc"] for f in final}) == 84, "重複 accession"
    assert not ({f["event_id"] for f in final} & used - {f["event_id"] for f in final if f["swapped"]})

    back_rest = [b for b in back_l if b["event_id"] not in used]
    m_pairs = [(f["year"], f["acc"]) for f in final]
    b_pairs = [(b["year"], b["acc"]) for b in back_l]
    br_pairs = [(b["year"], b["acc"]) for b in back_rest]
    hashes = {
        "main_swapped_plus_backup44": sha(m_pairs, b_pairs),
        "main_swapped_plus_backup41": sha(m_pairs, br_pairs),
        "main_swapped_only": hashlib.sha256(
            "\n".join("%s|%s" % (y, a) for y, a in m_pairs).encode("utf-8")).hexdigest(),
    }

    # ---- 口徑自核:把 E067 還原(只剩 E056/E070 兩宗換位)應再現 KARST-230 的雜湊
    TWO_SWAP = "6443ffc110597f976d370bf462afea5672f11170a7f1249455bad57f4f01920f"
    m2 = [(f["year"], (next(x["acc"] for x in main_l if x["event_id"] == f["slot"])
                       if f["slot"] == "E067" else f["acc"])) for f in final]
    check = sha(m2, b_pairs)
    print("selfcheck_two_swap %s %s" % (check, "OK" if check == TWO_SWAP else "MISMATCH"))

    out = dict(swaps=swap_recs, final=final, hashes=hashes,
               n_main=len(final), n_backup_total=len(back_l),
               n_backup_used=len(used), backups_used=sorted(used),
               backups_left=[b["event_id"] for b in back_rest],
               orig_lock_sha="9ebe5da6d641e728b2f6d4ec7729911f405a8f686a14e086444fa3d9866c572a",
               after_guidance_sha="6443ffc110597f976d370bf462afea5672f11170a7f1249455bad57f4f01920f")
    (CACHE / "picks_final.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (CACHE / "picks_final_ids.txt").write_text(
        "\n".join(f["slot"] for f in final) + "\n", encoding="utf-8")

    # ---- 印表身(ASCII + 中文都直接印,供人手抄入 md)
    print("### 換位紀錄(3 宗)")
    print("| 槽位 | 換出 | 年份 | 行業桶 | 換入 | 換入 accessionNumber | 同年同桶後備候選 | 原因 |")
    print("|---|---|---|---|---|---|---|---|")
    for s in swap_recs:
        print("| %s | %s | %s | %s | **%s** | `%s` | 1(無選擇餘地) | %s |"
              % (s["slot"], s["out_event"], s["out_year"], s["out_bucket"],
                 s["in_event"], s["in_acc"], s["reason"]))
    print()
    print("### 主清單 84 宗")
    print("| # | 槽位(換入者另標) | 年 | 行業桶 | accessionNumber |")
    print("|---|---|---|---|---|")
    for i, f in enumerate(final, 1):
        mark = " ← 換入 %s" % f["event_id"] if f["swapped"] else ""
        print("| %d | %s%s | %s | %s | `%s` |"
              % (i, f["slot"], mark, f["year"], f["bucket"], f["acc"]))
    print()
    print("### SHA-256")
    for k, v in hashes.items():
        print("%s %s" % (k, v))
    print("orig_lock_sha %s" % out["orig_lock_sha"])
    print("backup_left %d" % len(back_rest))
    print("swap_count %d" % len(swap_recs))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
