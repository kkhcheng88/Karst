"""KARST-174 步驟三:刪除 sha256 與正本完全相同的副本。

預設乾跑,只寫 out/delete_list.csv。加 --apply 才真刪。
刪之前逐檔即場重算 sha256,並確認正本那一份存在且雜湊相同;有任何一項對不上就跳過。
只刪實驗目錄內的檔;正本、10-K 文本快取、companyfacts、價格庫、生產庫一律不碰。
"""
import csv
import hashlib
import os
import sys

ROOT = r"C:\projects\Karst"
CANON = os.path.join(ROOT, "data", "sec", "submissions")
BASE = os.path.join(ROOT, "experiments", "2026-09-03-submissions-dedup")
OUT = os.path.join(BASE, "out")

DIRS = {
    "fundamentals-panel": os.path.join(ROOT, "experiments", "2026-09-02-fundamentals-panel", "data", "submissions"),
    "lazy-prices": os.path.join(ROOT, "experiments", "2026-09-02-lazy-prices", "data", "submissions"),
    "narrative-layers": os.path.join(ROOT, "experiments", "2026-09-02-narrative-layers", "data", "submissions"),
    "narrative-layers-v2": os.path.join(ROOT, "experiments", "2026-09-02-narrative-layers-v2", "data", "submissions"),
    "silent-revisions": os.path.join(ROOT, "experiments", "2026-09-02-silent-revisions", "data", "submissions"),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    apply = "--apply" in sys.argv

    canon_hash = {}
    for n in os.listdir(CANON):
        p = os.path.join(CANON, n)
        if os.path.isfile(p) and n.lower().endswith(".json"):
            canon_hash[sha256(p)] = n

    with open(os.path.join(OUT, "inventory.csv"), encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["verdict"] == "identical"]

    plan, skipped, deleted, freed = [], [], 0, 0
    for r in rows:
        src = os.path.join(DIRS[r["copy"]], r["file"])
        if not os.path.isfile(src):
            skipped.append((src, "來源不存在"))
            continue
        now = sha256(src)
        if now != r["sha256"]:
            skipped.append((src, "雜湊自盤點後變過"))
            continue
        twin = canon_hash.get(now)
        if not twin:
            skipped.append((src, "正本查無同雜湊"))
            continue
        size = os.path.getsize(src)
        plan.append({"copy": r["copy"], "path": src, "bytes": size,
                     "sha256": now, "canon_twin": os.path.join(CANON, twin)})
        if apply:
            os.remove(src)
            deleted += 1
            freed += size

    with open(os.path.join(OUT, "delete_list.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["copy", "path", "bytes", "sha256", "canon_twin"])
        w.writeheader()
        w.writerows(plan)

    per = {}
    for p in plan:
        d = per.setdefault(p["copy"], [0, 0])
        d[0] += 1
        d[1] += p["bytes"]
    print("apply" if apply else "dry-run")
    for k, v in sorted(per.items()):
        print(f"  {k}: {v[0]} 檔, {round(v[1]/1048576,1)} MB")
    print(f"合計 {len(plan)} 檔, {round(sum(p['bytes'] for p in plan)/1048576,1)} MB")
    print(f"跳過 {len(skipped)}", skipped[:5])
    if apply:
        print(f"已刪 {deleted} 檔, 釋出 {round(freed/1048576,1)} MB")


if __name__ == "__main__":
    main()
