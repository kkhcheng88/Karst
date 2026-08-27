"""``python -m karst.web`` —— 起本機網頁殼。

唯一入口 ``karst`` 的子命令是寫死的 if-chain(``karst/gateway/cli.py``),
外面掛不到新子命令,所以本頁殼照 ``karst/gateway/__main__.py`` 同一個模式
自成一道門,完全不動 cli.py。
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from karst.errors import KarstError
from karst.web.data import DEFAULT_RISK_FREE_RATE, build_reader
from karst.web.server import make_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m karst.web",
        description="Karst 本機網頁殼:讀庫內真實運行,畫淨值圖與蠟燭圖。",
    )
    parser.add_argument("--host", default="127.0.0.1", help="監聽位址(預設只開本機)")
    parser.add_argument("--port", type=int, default=8765, help="監聽埠(預設 8765)")
    parser.add_argument(
        "--project-root",
        default=None,
        help="專案根;庫與 data/ 由它推算(預設:現時工作目錄)",
    )
    parser.add_argument("--store", default=None, help="定義庫檔路徑(預設 <根>/karst.sqlite)")
    parser.add_argument("--runs-root", default=None, help="運行序列根(預設 <根>/data/runs)")
    parser.add_argument(
        "--snapshot-root", default=None, help="數據快照根(預設 <根>/data/snapshots)"
    )
    parser.add_argument(
        "--risk-free-rate",
        type=float,
        default=DEFAULT_RISK_FREE_RATE,
        help=f"無風險利率,Sortino 用(預設 {DEFAULT_RISK_FREE_RATE})",
    )
    parser.add_argument("--open", action="store_true", help="起好之後自動開瀏覽器")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    root = Path(args.project_root or Path.cwd()).resolve()
    try:
        reader = build_reader(
            root,
            db_path=args.store,
            runs_root=args.runs_root,
            snapshot_root=args.snapshot_root,
            risk_free_rate=args.risk_free_rate,
        )
        meta = reader.get_meta()
    except KarstError as exc:
        print(f"起不到服務:{exc}", file=sys.stderr)
        return 1

    httpd = make_server(reader, args.host, args.port)
    host, port = httpd.server_address[0], httpd.server_address[1]
    url = f"http://{host}:{port}/"

    print(f"Karst 本機網頁殼　{url}")
    print(f"　專案根　{root}")
    print(f"　庫內運行　{meta['runCount']} 次・策略 {'、'.join(meta['strategies']) or '(無)'}")
    print("　Ctrl+C 收工")

    if args.open:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n收工。")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
