"""json3 字幕檔轉純文字。

用法(CLI,與舊版 scratchpad 腳本相容):
    PYTHONUTF8=1 python json3_to_text.py <src.json3> <dst.txt>

亦可當模組用(captions.py 依賴這個函式):
    from json3_to_text import json3_to_text
    n_chars = json3_to_text(src_path, dst_path)
"""
import json
import sys
from pathlib import Path


def json3_to_text(src, dst) -> int:
    """讀一個 yt-dlp 產出的 json3 字幕檔,寫出純文字檔,回傳字數。"""
    src = Path(src)
    dst = Path(dst)
    with src.open(encoding="utf-8") as f:
        data = json.load(f)

    parts = []
    for ev in data.get("events", []):
        for seg in ev.get("segs", []) or []:
            t = seg.get("utf8", "")
            if t and t != "\n":
                parts.append(t)
    text = "".join(parts)

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    return len(text)


def main():
    if len(sys.argv) != 3:
        print("用法: python json3_to_text.py <src.json3> <dst.txt>", file=sys.stderr)
        sys.exit(1)
    n = json3_to_text(sys.argv[1], sys.argv[2])
    print(n, "chars")


if __name__ == "__main__":
    main()
