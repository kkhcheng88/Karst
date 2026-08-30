"""判 KARST-096 那三道閘(``replay.py`` 只凍不判,判在這裡)。

跑法(倉根,要先跑過 before 與 after 兩次 replay)::

    python experiments/2026-08-30-freeze-module/compare.py --out <目錄>

三道閘,任何一道不過即回非零:

  **甲、對生產逐位。** 重凍出來的快照編號與內容雜湊,要與已凍結那兩份**逐位相同**。
  這一道證的是「新模組凍出來的,還是同一份東西」。

  **乙、改動前後逐位。** ``before/`` 與 ``after/`` 兩個目錄逐檔逐位比,包括 parquet。
  只有三格明列的東西容許不同,其餘一位都不准差:

    · ``fetched_at`` —— 牆上的鐘,刻意不入內容雜湊(D-026 第 3 條)。
    · ``*.gateway-key`` —— 每複製一次庫身就新開一把簽章匙,與凍結無關。
    · ``summary.json`` 的 ``label`` —— 就是 before / after 這兩個字本身。

  容許清單是**逐條寫死**的,不是一條「差得少就當過」的容差:清單以外多差一行,
  這道閘就當場不過。

  **丙、說明檔對已凍結那份。** 重凍出來的說明檔與快照目錄裡那份逐行比。差異分兩類,
  兩類都要成立才算過:

    · 抓取時間那一行 —— 甲閘已經講了它不入雜湊,必然不同。
    · 其餘全部要是**純新增**:已凍結那份的每一行都要在重凍那份裡找得到,一行不缺。
      多出來的是快照凍結之後才加的欄目(三數等式、別名閘那一節、齊全度那一節),
      它們在那兩份快照凍結的日子還未存在。

  而且 **before 與 after 的差異要逐行相同** —— 這一句才是本票的重點:那些多出來的
  欄目在改動之前已經多出來,不是這次改動改出來的。
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN = {
    "price": REPO_ROOT / "data" / "snapshots" / "2026-08-28-3bf7ab0a522a",
    "macro": REPO_ROOT / "data" / "macro_snapshots" / "2026-08-28-dc2d9f1a1778",
}
CLOCK_MARKERS = ('"fetched_at":', "| 抓取時間(UTC) |")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files_under(root: Path) -> dict[str, Path]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): path
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _is_clock(line: str) -> bool:
    return any(marker in line for marker in CLOCK_MARKERS)


def _allowed_difference(relative: str, before: Path, after: Path) -> tuple[bool, list[str]]:
    """這兩份檔差的那幾行,在不在乙閘那張容許清單上。"""
    if relative.endswith(".gateway-key"):
        return True, ["整檔:每複製一次庫身就新開一把簽章匙"]
    if not relative.endswith((".json", ".md", ".csv")):
        return False, ["二進位檔逐位不同(parquet 之類不容許有分別)"]

    changed = [
        line
        for line in difflib.unified_diff(
            before.read_text(encoding="utf-8").splitlines(),
            after.read_text(encoding="utf-8").splitlines(),
            n=0,
            lineterm="",
        )
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]
    offenders = [
        line
        for line in changed
        if not _is_clock(line) and not (relative == "summary.json" and '"label":' in line)
    ]
    return not offenders, offenders or changed


def gate_b(out: Path) -> dict[str, Any]:
    """改動前後逐位。"""
    before_root, after_root = out / "before", out / "after"
    before, after = files_under(before_root), files_under(after_root)
    only_before = sorted(set(before) - set(after))
    only_after = sorted(set(after) - set(before))

    identical: list[str] = []
    excused: list[dict[str, Any]] = []
    offending: list[dict[str, Any]] = []
    for relative in sorted(set(before) & set(after)):
        if sha256(before[relative]) == sha256(after[relative]):
            identical.append(relative)
            continue
        ok, lines = _allowed_difference(relative, before[relative], after[relative])
        (excused if ok else offending).append({"file": relative, "lines": lines})

    return {
        "files_compared": len(set(before) & set(after)),
        "byte_identical": len(identical),
        "excused": excused,
        "offending": offending,
        "only_in_before": only_before,
        "only_in_after": only_after,
        "passed": not offending and not only_before and not only_after,
    }


def gate_a(out: Path) -> dict[str, Any]:
    """對生產逐位:兩次重凍的編號與內容雜湊都要對得住已凍結那份。"""
    rows: list[dict[str, Any]] = []
    for label in ("before", "after"):
        summary = json.loads((out / label / "summary.json").read_text(encoding="utf-8"))
        for kind in ("price", "macro"):
            item = summary[kind]
            rows.append(
                {
                    "label": label,
                    "kind": kind,
                    "frozen_snapshot_id": item["frozen_snapshot_id"],
                    "replayed_snapshot_id": item["replayed_snapshot_id"],
                    "frozen_content_hash": item["frozen_content_hash"],
                    "replayed_content_hash": item["replayed_content_hash"],
                    "identical": (
                        item["frozen_snapshot_id"] == item["replayed_snapshot_id"]
                        and item["frozen_content_hash"] == item["replayed_content_hash"]
                    ),
                }
            )
    return {"rows": rows, "passed": all(row["identical"] for row in rows)}


def _readme_delta(replayed: Path, frozen: Path) -> dict[str, Any]:
    """重凍那份與已凍結那份的說明檔差在哪。"""
    frozen_lines = frozen.read_text(encoding="utf-8").splitlines()
    replayed_lines = replayed.read_text(encoding="utf-8").splitlines()
    diff = [
        line
        for line in difflib.unified_diff(frozen_lines, replayed_lines, n=0, lineterm="")
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]
    removed = [line for line in diff if line.startswith("-") and not _is_clock(line)]
    added = [line for line in diff if line.startswith("+") and not _is_clock(line)]
    clock = [line for line in diff if _is_clock(line)]
    return {
        "frozen_lines": len(frozen_lines),
        "replayed_lines": len(replayed_lines),
        "diff_lines": len(diff),
        "clock_lines": len(clock),
        "added_lines": len(added),
        "removed_lines": len(removed),
        # 純新增即「已凍結那份一行不缺」。有東西被刪走就是真的改了行為。
        "additions_only": not removed,
        "added": added,
        "removed": removed,
        "diff": diff,
        # 改動前後拿來比的就是這一格:抓取時間那一行本身在兩次之間必然不同(牆上的鐘),
        # 把它剔走之後仍然逐行相同,才證得到「多出來那些欄目不是這次改動改出來的」。
        "diff_without_clock": [line for line in diff if not _is_clock(line)],
    }


def gate_c(out: Path) -> dict[str, Any]:
    """說明檔:對已凍結那份純新增,而且改動前後的差異逐行相同。"""
    deltas: dict[str, dict[str, Any]] = {}
    for label in ("before", "after"):
        for kind, frozen_dir in FROZEN.items():
            deltas[f"{label}/{kind}"] = _readme_delta(
                out / label / f"{kind}-說明.md", frozen_dir / "說明.md"
            )

    same_across_runs = {
        kind: (
            deltas[f"before/{kind}"]["diff_without_clock"]
            == deltas[f"after/{kind}"]["diff_without_clock"]
        )
        for kind in FROZEN
    }
    return {
        "deltas": deltas,
        "same_before_after": same_across_runs,
        "passed": all(same_across_runs.values())
        and all(item["additions_only"] for item in deltas.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="判 KARST-096 那三道閘")
    parser.add_argument("--out", required=True, help="兩次 replay 的輸出根目錄")
    args = parser.parse_args()
    out = Path(args.out)

    result = {"甲_對生產逐位": gate_a(out), "乙_改動前後逐位": gate_b(out), "丙_說明檔": gate_c(out)}
    result["passed"] = all(gate["passed"] for gate in result.values() if isinstance(gate, dict))

    target = Path(__file__).resolve().parent / "結果.json"
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    a, b, c = result["甲_對生產逐位"], result["乙_改動前後逐位"], result["丙_說明檔"]
    print("甲、對生產逐位:" + ("過" if a["passed"] else "不過"))
    for row in a["rows"]:
        mark = "=" if row["identical"] else "≠"
        print(
            f"    {row['label']:6s} {row['kind']:5s} "
            f"{row['replayed_snapshot_id']} {mark} {row['frozen_snapshot_id']}"
        )
    print("乙、改動前後逐位:" + ("過" if b["passed"] else "不過"))
    print(f"    比了 {b['files_compared']} 個檔,逐位相同 {b['byte_identical']} 個")
    for item in b["excused"]:
        print(f"    容許不同:{item['file']}({len(item['lines'])} 行)")
    for item in b["offending"]:
        print(f"    **不容許**:{item['file']} → {item['lines'][:4]}")
    print("丙、說明檔:" + ("過" if c["passed"] else "不過"))
    for key, delta in c["deltas"].items():
        print(
            f"    {key:14s} 差 {delta['diff_lines']:3d} 行"
            f"(鐘 {delta['clock_lines']}、新增 {delta['added_lines']}、"
            f"刪走 {delta['removed_lines']})"
        )
    for kind, same in c["same_before_after"].items():
        print(f"    {kind} 改動前後的差異逐行相同:{'是' if same else '否'}")
    print(f"\n總判:{'三道閘全過' if result['passed'] else '有閘不過'} → {target}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
