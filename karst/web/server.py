"""KARST-032 本機網頁殼:薄 REST 層 + 靜態頁。

用 Python 標準庫的 ``ThreadingHTTPServer``,不引入 fastapi/uvicorn——
這一層只有四個 GET 端點,標準庫夠用,而且不必為一個本機檢視器把
starlette/pydantic 塞進正式依賴,令只想用引擎的人也要一併安裝。

這一層**只讀不寫**:庫由 ``karst.store`` 開(D-027),parquet 由
``karst.runs`` 讀回,本檔自己不碰 sqlite 亦不碰檔案格式。
"""

from __future__ import annotations

import json
import mimetypes
import posixpath
import re
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse, parse_qs

from karst.errors import ContractViolation, NotFound
from karst.web import api_sweep
from karst.web import api_strategy
from karst.web import api_overview
from karst.web import api_jobs  # KARST-052 重跑/重掃(唯一會寫庫的一層)
from karst.web import api_macro  # KARST-061 宏觀序列齊全度

STATIC_ROOT = Path(__file__).resolve().parent / "static"

# 網址 → static/ 下的頁檔。每一頁在自己那個模組登記自己那一行,本檔不逐頁寫死。
PAGE_FILES: dict[str, str] = {"/": "index.html", "/index.html": "index.html"}
PAGE_FILES.update(api_overview.PAGES)  # KARST-049 策略總覽(連根路徑)
PAGE_FILES.update(api_sweep.PAGES)  # KARST-051 參數掃描頁

# 檢視視窗的起訖日:一律 YYYY-MM-DD。日子本身合不合理由下游那層講(揀了一段
# 只得一日、結束早過開始),這裡只擋明顯不是日子的東西。
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")

# .js 在部分 Windows 機器上被登記成 text/plain,瀏覽器會拒絕執行;明文釘死。
_MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


class WebError(Exception):
    """回得出 HTTP 狀態碼的錯,例如揀了一個庫裡沒有的運行編號。"""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _guess_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _MIME:
        return _MIME[suffix]
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _safe_static_path(url_path: str) -> Path | None:
    """把網址路徑解成 static/ 之下的實體檔;越界一律回 None。"""
    rel = posixpath.normpath(unquote(url_path)).lstrip("/")
    if not rel or rel in (".", ".."):
        return None
    candidate = (STATIC_ROOT / rel).resolve()
    try:
        candidate.relative_to(STATIC_ROOT.resolve())
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


def _window_args(query: dict[str, list[str]]) -> tuple[str | None, str | None]:
    """?start=&end= 兩個日子。兩個都留空即全期——留空與不帶,兩者同義。"""

    def one(name: str) -> str | None:
        values = query.get(name) or []
        raw = (values[0] if values else "").strip()
        if not raw:
            return None
        if not _DAY.fullmatch(raw):
            raise WebError(
                HTTPStatus.BAD_REQUEST,
                f"檢視視窗的 {name} 要一個 YYYY-MM-DD 的日子,收到 {raw!r}",
            )
        return raw

    return one("start"), one("end")


def build_handler(reader: Any) -> type[BaseHTTPRequestHandler]:
    """造一個綁定了 ``reader`` 的 handler 類。

    ``reader`` 要有 list_runs() / get_run(run_id) / get_candles(run_id, symbol)
    三個方法,見 ``karst.web.data.RunReader``。
    """

    def _list_runs(_handler: Any, query: dict[str, list[str]]) -> Any:
        raw = (query.get("limit") or ["24"])[0]
        try:
            limit = None if raw in ("", "0", "all") else int(raw)
        except ValueError:
            raise WebError(HTTPStatus.BAD_REQUEST, f"limit 要一個整數,收到 {raw!r}") from None
        return reader.list_runs(limit)

    routes: dict[str, Callable[[Any, dict[str, list[str]]], Any]] = {
        "/api/runs": _list_runs,
        "/api/meta": lambda r, q: reader.get_meta(),
    }
    routes.update(api_sweep.routes(reader))  # 參數掃描頁(KARST-051),端點全部住在 api_sweep.py
    routes.update(api_strategy.routes(reader))  # KARST-050 策略詳情頁的端點
    api_overview.register(routes, reader)  # KARST-049 策略總覽的端點
    routes.update(api_jobs.routes(reader))  # KARST-052 查重跑/重掃進度(下單是 POST)
    routes.update(api_macro.routes(reader))  # KARST-061 宏觀序列齊全度(自成一個小端點)

    class Handler(BaseHTTPRequestHandler):
        server_version = "KarstWeb/0.1"
        protocol_version = "HTTP/1.1"

        # 預設會對每個請求做反查 DNS,本機開發時純粹拖慢
        def address_string(self) -> str:  # noqa: D102
            return self.client_address[0]

        def log_message(self, fmt: str, *args: Any) -> None:
            # 每個請求一行,夠用來知道頁面有無真的打到 REST
            print("  %s - %s" % (self.address_string(), fmt % args))

        # ---------- 回應小工具 ----------
        def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _send_json(self, status: int, payload: Any) -> None:
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self._send_bytes(status, body, "application/json; charset=utf-8")

        def _send_error_json(self, status: int, message: str) -> None:
            self._send_json(status, {"error": message})

        # ---------- 路由 ----------
        def do_HEAD(self) -> None:  # noqa: N802
            self.do_GET()

        def do_POST(self) -> None:  # noqa: N802
            # 全站唯一的寫入路徑,連錯誤映射一併住在 api_jobs(KARST-052)
            api_jobs.handle_post(self, reader)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)

            try:
                if path.startswith("/api/"):
                    # 查庫不再排隊:讀取層已改為逐執行緒各自一條唯讀連線
                    # (KARST-055,data.py 的 _ThreadStore),兩個請求同時查庫
                    # 各用各的游標,不會互相搞亂。KARST-050 臨時加的那道鎖已移除。
                    self._handle_api(path, query)
                    return
                self._handle_static(path)
            except WebError as exc:
                self._send_error_json(exc.status, exc.message)
            except BrokenPipeError:
                # 瀏覽器換頁時常見,不是錯
                pass
            except NotFound as exc:
                # 揀了一個庫裡沒有的運行 / 快照名單沒有的代號:是 404,不是伺服器壞
                self._send_error_json(HTTPStatus.NOT_FOUND, str(exc))
            except ContractViolation as exc:
                # 揀了一段只得一日、或者結束日早過開始日:是揀錯,不是伺服器壞
                self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            except Exception as exc:  # noqa: BLE001
                self._send_error_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    f"{type(exc).__name__}：{exc}",
                )

        def _handle_api(self, path: str, query: dict[str, list[str]]) -> None:
            if path in routes:
                self._send_json(HTTPStatus.OK, routes[path](self, query))
                return

            # /api/runs/<run_id>            一次運行的全部畫圖資料
            # /api/runs/<run_id>/candles    某實體在該次運行內的 K 線與買賣標記
            parts = [p for p in path.strip("/").split("/") if p]
            if len(parts) >= 3 and parts[0] == "api" and parts[1] == "runs":
                run_id = unquote(parts[2])
                # 兩個端點共用同一段檢視視窗:圖與數不會各看各的一段
                start, end = _window_args(query)
                if len(parts) == 3:
                    self._send_json(HTTPStatus.OK, reader.get_run(run_id, start, end))
                    return
                if len(parts) == 4 and parts[3] == "candles":
                    symbols = query.get("symbol") or []
                    if not symbols:
                        raise WebError(
                            HTTPStatus.BAD_REQUEST, "要畫哪一隻的蠟燭圖:請帶 ?symbol="
                        )
                    self._send_json(
                        HTTPStatus.OK,
                        reader.get_candles(run_id, symbols[0], start, end),
                    )
                    return

            raise WebError(HTTPStatus.NOT_FOUND, f"沒有這個端點:{path}")

        def _handle_static(self, path: str) -> None:
            if path in PAGE_FILES:
                target = STATIC_ROOT / PAGE_FILES[path]
            elif path.startswith("/static/"):
                target = _safe_static_path(path[len("/static/") :])
            else:
                target = None

            if target is None or not target.is_file():
                self._send_bytes(
                    HTTPStatus.NOT_FOUND,
                    "找不到這一頁。".encode("utf-8"),
                    "text/plain; charset=utf-8",
                )
                return

            self._send_bytes(HTTPStatus.OK, target.read_bytes(), _guess_type(target))

    return Handler


def make_server(reader: Any, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """起一個未開始服務的 server,port 給 0 即由系統派一個(測試用)。"""
    httpd = ThreadingHTTPServer((host, port), build_handler(reader))
    httpd.daemon_threads = True
    return httpd


def serve_in_background(reader: Any, host: str = "127.0.0.1", port: int = 0):
    """起一個背景 server,回傳 (server, url)。測試用,收工記得 shutdown()。"""
    httpd = make_server(reader, host, port)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    actual_host, actual_port = httpd.server_address[0], httpd.server_address[1]
    return httpd, f"http://{actual_host}:{actual_port}"
