"""KOL 交易員名字 → 候選影片清單(CSV + MD)。

只出候選清單,不代選、不下載。用戶要在 MD 檔的「選」欄剔選之後,
才把揀中的 video id 交給 captions.py 抽字幕。

用法:
    PYTHONUTF8=1 python search.py "施傅"
    PYTHONUTF8=1 python search.py "張智威" --limit 30 --out-dir research/_candidates/張智威
    PYTHONUTF8=1 python search.py "某某" --queries "交易 訪談" "交易系統" "投資 心法"

輸出(預設 research/_candidates/<name>/):
    candidates.csv  — 供程式/試算表用,含空白「選取」欄
    candidates.md   — 供人手在對話/編輯器裡剔選,含空白「選」欄
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

YT_DLP = r"C:\Users\Kaho\AppData\Local\Programs\Python\Python312\Scripts\yt-dlp.exe"

# 預設三條查詢後綴:訪談/系統披露類優先於行情評論類,篩選準則見 README.md。
DEFAULT_QUERIES = ["交易 訪談", "交易系統", "投資 心法"]

PRINT_FMT = "%(id)s|%(title)s|%(duration)s|%(upload_date)s|%(channel)s"


def run_search(name: str, query_suffix: str, limit: int) -> list[dict]:
    query = f"ytsearch{limit}:{name} {query_suffix}"
    cmd = [YT_DLP, "--flat-playlist", "--print", PRINT_FMT, query]
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        print(f"[警告] 查詢失敗:{query}\n{result.stderr}", file=sys.stderr)
        return []
    rows = []
    for line in result.stdout.splitlines():
        parts = line.split("|", 4)
        if len(parts) != 5:
            continue
        vid, title, duration, upload_date, channel = parts
        rows.append(
            {
                "video_id": vid,
                "title": title,
                "duration_sec": duration,
                "upload_date": upload_date,
                "channel": channel,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "query": query,
            }
        )
    return rows


def dedupe(rows: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for r in rows:
        if r["video_id"] in seen:
            continue
        seen.add(r["video_id"])
        out.append(r)
    return out


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "選取",
        "video_id",
        "title",
        "duration_sec",
        "upload_date",
        "channel",
        "url",
        "query",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            row = {"選取": "", **r}
            writer.writerow(row)


def write_md(rows: list[dict], path: Path, name: str) -> None:
    lines = [
        f"# {name} — 候選影片清單(待用戶剔選)",
        "",
        "> 本清單由 tools/video-to-skill/search.py 自動產生,只作候選,不代選。",
        "> 請在「選」欄用 x 剔選要抽字幕的影片,篩選準則(訪談/系統披露類優先、行情評論類跳過)見 README.md。",
        "",
        "| 選 | 影片 ID | 標題 | 時長(秒) | 上傳日期 | 頻道 | 連結 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| | {r['video_id']} | {r['title']} | {r['duration_sec']} | "
            f"{r['upload_date']} | {r['channel']} | {r['url']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="KOL 交易員名字 → 候選影片清單(不代選)")
    ap.add_argument("name", help="KOL 名字")
    ap.add_argument(
        "--queries",
        nargs="*",
        default=None,
        help="自訂查詢後綴清單(空白分隔多個),預設用內建三條",
    )
    ap.add_argument("--limit", type=int, default=30, help="每條查詢取幾多筆(ytsearchN)")
    ap.add_argument(
        "--out-dir",
        default=None,
        help="輸出目錄,預設 research/_candidates/<name>",
    )
    args = ap.parse_args()

    queries = args.queries if args.queries else DEFAULT_QUERIES
    out_dir = (
        Path(args.out_dir) if args.out_dir else Path("research/_candidates") / args.name
    )

    all_rows = []
    for q in queries:
        rows = run_search(args.name, q, args.limit)
        print(f"查詢「{args.name} {q}」取得 {len(rows)} 筆")
        all_rows.extend(rows)

    rows = dedupe(all_rows)
    print(f"去重後共 {len(rows)} 筆候選")

    csv_path = out_dir / "candidates.csv"
    md_path = out_dir / "candidates.md"
    write_csv(rows, csv_path)
    write_md(rows, md_path, args.name)
    print(f"已寫:{csv_path}")
    print(f"已寫:{md_path}")


if __name__ == "__main__":
    main()
