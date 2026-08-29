"""KARST-081 核對用:起一個背景 server,常駐直到手動 TaskStop。

跑法(倉根目錄):
    set PYTHONUTF8=1
    set PYTHONPATH=.
    python experiments/2026-08-29-overview-align/serve_temp.py 8767

只可以用 8767／8768 這兩個暫用埠;8765 是主局在用,不准碰。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from karst.web.data import build_reader
from karst.web.server import serve_in_background


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8767
    reader = build_reader(PROJECT_ROOT)
    httpd, url = serve_in_background(reader, port=port)
    print(f"serving at {url}", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    main()
