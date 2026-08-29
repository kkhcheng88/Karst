"""KARST-078 瀏覽器核對用:在臨時 port 起一個唯讀 server,前景常駐到被中斷為止。

跑法(倉根目錄,另開一個背景程序):
    set PYTHONUTF8=1
    python experiments/2026-08-29-run-drilldown/serve_temp.py 8768
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from karst.web.data import build_reader
from karst.web.server import make_server

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8768
    reader = build_reader(ROOT)
    httpd = make_server(reader, "127.0.0.1", port)
    print(f"READY http://127.0.0.1:{port}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
