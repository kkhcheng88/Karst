"""影片 id 清單 → 字幕純文字檔。無字幕的影片記入 skipped 清單,不當錯誤中止。

用法:
    PYTHONUTF8=1 python captions.py --ids Ubv1YW_5uPI jOhjFLl0TRs --out-dir research/_captions/某某
    PYTHONUTF8=1 python captions.py --ids-file 已剔選.txt --out-dir research/_captions/某某

--ids-file 每行一個 video id(可用 # 開頭做註解、空行忽略;也可以直接貼
candidates.md 剔選那一行,腳本只取每行第一個欄位當 id,所以貼「video_id」
那一欄的值即可)。

已知限制與處理方式(對應票 KARST-011):
  1. 429 限速 — 每條片之間 sleep(預設 2 秒,--sleep 可調),yt-dlp 本身
     再加 --sleep-requests 2。
  2. 好多片無字幕(只有 live_chat 不算字幕)— 抓不到 .json3 檔的一律
     記入 out-dir/skipped.md,不中止其餘影片。
  3. 自動字幕辨識質素一般 — 本腳本只負責抽取純文字,不做校對;任何
     要入引擎的具體數字,代理抽取筆記時必須標明「回片核對」。

語言優先順序用 --sub-langs 控制(逗號分隔,前面的優先):同一條片若同時
有多種語言字幕,揀清單裡排得最前那一種。預設「zh-Hant,zh-HK,yue,zh-Hans,en」
(中文優先);對象本身講英文的材料(例:英文播客訪談)可以用
--sub-langs "en,zh-Hant,zh-HK,yue,zh-Hans" 反過來揀英文優先。
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

from json3_to_text import json3_to_text

YT_DLP = r"C:\Users\Kaho\AppData\Local\Programs\Python\Python312\Scripts\yt-dlp.exe"
SUB_LANGS = "zh-Hant,zh-HK,yue,zh-Hans,en"


def read_ids_file(path: Path) -> list[str]:
    ids = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 容忍貼進來的是 candidates.md 表格行或逗號分隔——只取第一個 token
        token = line.strip("|").strip().split()[0]
        token = token.split(",")[0].strip()
        if token:
            ids.append(token)
    return ids


def fetch_one(video_id: str, workdir: Path, sub_langs: str) -> Path | None:
    workdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        YT_DLP,
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        sub_langs,
        "--sub-format",
        "json3",
        "--sleep-requests",
        "2",
        "-o",
        str(workdir / "%(id)s.%(ext)s"),
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        print(f"[錯誤] {video_id} yt-dlp 執行失敗:\n{result.stderr[-2000:]}", file=sys.stderr)
    json3_files = sorted(workdir.glob(f"{video_id}*.json3"))
    if not json3_files:
        return None
    # 按 sub_langs 的順序揀語言;冇一個對得上就退而求其次揀第一個
    for lang in sub_langs.split(","):
        lang = lang.strip()
        for p in json3_files:
            if f".{lang}." in p.name:
                return p
    return json3_files[0]


def main():
    ap = argparse.ArgumentParser(
        description="影片 id 清單 → 字幕純文字檔;無字幕者記入 skipped 清單"
    )
    ap.add_argument("--ids", nargs="*", default=[], help="直接列 video id")
    ap.add_argument("--ids-file", default=None, help="每行一個 video id 的檔案")
    ap.add_argument("--out-dir", required=True, help="輸出目錄")
    ap.add_argument(
        "--sleep", type=float, default=2.0, help="每條片之間額外 sleep 秒數(避 429)"
    )
    ap.add_argument(
        "--sub-langs",
        default=SUB_LANGS,
        help="字幕語言優先順序,逗號分隔,前面的優先(預設中文優先)",
    )
    args = ap.parse_args()

    ids = list(args.ids)
    if args.ids_file:
        ids.extend(read_ids_file(Path(args.ids_file)))
    ids = list(dict.fromkeys(ids))  # 去重、保序
    if not ids:
        print("[錯誤] 沒有輸入任何 video id(用 --ids 或 --ids-file)", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir)
    raw_dir = out_dir / "_raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    skipped = []
    done = []
    for i, vid in enumerate(ids):
        print(f"[{i + 1}/{len(ids)}] {vid} ...")
        json3_path = fetch_one(vid, raw_dir, args.sub_langs)
        if json3_path is None:
            print("  無字幕(只有 live_chat 不算字幕),跳過")
            skipped.append(vid)
        else:
            text_path = out_dir / f"{vid}.txt"
            n = json3_to_text(json3_path, text_path)
            print(f"  已轉純文字:{text_path}({n} 字)")
            done.append(vid)
        if i < len(ids) - 1:
            time.sleep(args.sleep)

    skipped_path = out_dir / "skipped.md"
    skipped_lines = ["# 無字幕跳過清單", ""]
    skipped_lines += [f"- {v} https://www.youtube.com/watch?v={v}" for v in skipped]
    skipped_path.write_text("\n".join(skipped_lines) + "\n", encoding="utf-8")

    print(f"完成:{len(done)} 條有字幕,{len(skipped)} 條跳過(見 {skipped_path})")


if __name__ == "__main__":
    main()
