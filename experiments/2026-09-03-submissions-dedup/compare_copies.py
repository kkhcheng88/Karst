"""KARST-174 申報索引副本清理:逐檔核 sha256。

只讀。輸出 out/inventory.csv(逐檔)與 out/summary.json(逐目錄)。
正本:data/sec/submissions/CIK##########.json
"""
import csv
import hashlib
import json
import os
import sys

ROOT = r"C:\projects\Karst"
CANON = os.path.join(ROOT, "data", "sec", "submissions")
COPIES = [
    ("fundamentals-panel", os.path.join(ROOT, "experiments", "2026-09-02-fundamentals-panel", "data", "submissions")),
    ("lazy-prices", os.path.join(ROOT, "experiments", "2026-09-02-lazy-prices", "data", "submissions")),
    ("narrative-layers", os.path.join(ROOT, "experiments", "2026-09-02-narrative-layers", "data", "submissions")),
    ("narrative-layers-v2", os.path.join(ROOT, "experiments", "2026-09-02-narrative-layers-v2", "data", "submissions")),
    ("silent-revisions", os.path.join(ROOT, "experiments", "2026-09-02-silent-revisions", "data", "submissions")),
]
OUT = os.path.join(ROOT, "experiments", "2026-09-03-submissions-dedup", "out")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cik_key(name):
    """把檔名正規化為 10 位 CIK;非申報索引檔回 None。"""
    stem = name[:-5] if name.lower().endswith(".json") else name
    if stem.upper().startswith("CIK"):
        stem = stem[3:]
    if "-submissions-" in stem:          # EDGAR 分頁 shard,正本沒有
        return None
    return stem.zfill(10) if stem.isdigit() else None


def main():
    os.makedirs(OUT, exist_ok=True)

    canon_by_key, canon_hashes = {}, {}
    for name in os.listdir(CANON):
        p = os.path.join(CANON, name)
        if not os.path.isfile(p) or not name.lower().endswith(".json"):
            continue
        k = cik_key(name)
        d = sha256(p)
        canon_by_key[k] = (name, d, os.path.getsize(p))
        canon_hashes.setdefault(d, name)
    print(f"正本 {len(canon_by_key)} 份, 不重覆雜湊 {len(canon_hashes)}", flush=True)

    rows, summary = [], {}
    for label, d in COPIES:
        s = {"dir": d, "files": 0, "bytes": 0,
             "identical": 0, "identical_bytes": 0,
             "differs": 0, "differs_bytes": 0,
             "no_counterpart": 0, "no_counterpart_bytes": 0,
             "shard": 0, "shard_bytes": 0,
             "derivative": 0, "derivative_bytes": 0}
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if not os.path.isfile(p):
                continue
            size = os.path.getsize(p)
            dg = sha256(p)
            k = cik_key(name)
            if k is None:
                verdict = "shard"          # 分頁檔,正本無對應
            elif not name.upper().startswith("CIK"):
                # 裸 CIK 檔名 = 三個敘事目錄的 10-K 清單衍生物,不是申報索引本體
                verdict = "derivative"
            elif k in canon_by_key and canon_by_key[k][1] == dg:
                verdict = "identical"
            elif dg in canon_hashes:
                verdict = "identical"      # 同內容、檔名不同
            elif k in canon_by_key:
                verdict = "differs"
            else:
                verdict = "no_counterpart"
            s["files"] += 1
            s["bytes"] += size
            s[verdict] += 1
            s[verdict + "_bytes"] += size
            rows.append({
                "copy": label, "file": name, "bytes": size, "sha256": dg,
                "cik_key": k or "",
                "canon_file": canon_by_key.get(k, ("", "", ""))[0] if k else "",
                "canon_sha256": canon_by_key.get(k, ("", "", ""))[1] if k else "",
                "canon_bytes": canon_by_key.get(k, ("", "", ""))[2] if k else "",
                "verdict": verdict,
            })
        summary[label] = s
        print(f"{label}: {s}", flush=True)

    with open(os.path.join(OUT, "inventory.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"canon_files": len(canon_by_key), "copies": summary}, f,
                  indent=2, ensure_ascii=False)
    print("done", flush=True)


if __name__ == "__main__":
    sys.exit(main())
