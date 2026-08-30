"""KARST-055 驗收:網頁殼讀取層逐執行緒一條資料庫連線。

兩項驗收條件,一項一個測試,只證「行得通」,不掃邊界情況(照 test_web.py 同一套)。

要驗的是一件很具體的事:一條 sqlite 連線不是多執行緒安全的,幾個請求同時
在同一條連線上查庫會互相搞亂對方的游標,答出「沒有因子版本 N」這種明明存在
卻查不到的錯(KARST-050 實測 8 次全錯)。當時只在伺服器加一道鎖令查庫排隊;
現在改成逐執行緒各自一條連線,鎖已移除,所以這裡要證同時打也答得對。

測試打的是**本機庫內真實的回測運行**;庫或運行不在,就跳過。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from karst.web import server as server_module
from karst.web.data import build_reader
from karst.web.server import PAGE_FILES, serve_in_background

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 對撞用的端點。四個都真的要查庫,而且住在不同模組(server.py / api_overview.py /
# api_strategy.py)——同一條連線上撞的正是這種各自為政的查詢。
ENDPOINTS = (
    "/api/meta",
    "/api/runs?limit=4",
    "/api/overview",
    "/api/strategy/runs",
)
HITS_EACH = 10


def _fetch(url: str):
    """回 (payload, 出錯講咩)。答得成即 error 是 None。"""
    try:
        with urllib.request.urlopen(url, timeout=180) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        return None, f"HTTP {exc.code}:{detail}"
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}:{exc}"
    try:
        payload = json.loads(body)
    except ValueError as exc:
        return None, f"答的不是 JSON:{exc}"
    if isinstance(payload, dict) and "error" in payload:
        return None, f"payload 帶錯:{payload['error']}"
    return payload, None


@pytest.fixture(scope="module")
def reader(seeded_project_root):
    """讀取層接**種好數的臨時專案根**,不是倉根那個生產庫(KARST-093)。"""
    return build_reader(seeded_project_root)


@pytest.fixture(scope="module")
def base_url(reader):
    httpd, url = serve_in_background(reader)
    try:
        yield url
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture(scope="module")
def baseline(base_url):
    """逐個端點獨自打一次,做對撞的比對底本。

    順帶把伺服器內幾個「開頁一次過讀全庫」的快取先行填好——不然十個請求同時
    到齊,每一個都由零砌一次同一份總覽,對撞測試會被那筆重複工夫拖到幾分鐘,
    而那筆工夫與要驗的事無關。查庫本身照舊逐個請求真的查,對撞照撞。
    """
    out = {}
    for endpoint in ENDPOINTS:
        payload, error = _fetch(base_url + endpoint)
        assert error is None, f"{endpoint} 獨自打都答不到:{error}"
        out[endpoint] = payload
    return out


@pytest.fixture(scope="module")
def collision(base_url, baseline):
    """四個端點各打十次,全部同時發出。跑一次,兩個測試共用這一次的結果。"""
    jobs = [endpoint for endpoint in ENDPOINTS for _ in range(HITS_EACH)]
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        results = list(pool.map(lambda path: _fetch(base_url + path), jobs))
    return list(zip(jobs, results))


def test_並發對撞零錯(collision):
    """驗收一:三個以上端點同時各打十次,零錯。"""
    failures = [(job, error) for job, (_, error) in collision if error]
    assert not failures, f"{len(failures)}/{len(collision)} 個請求出錯:{failures[:5]}"


def test_同時打與獨自打答同一個答案(collision, baseline):
    """並發不只要「不出錯」,還要答得**啱**。

    舊缺陷答得出 404,亦答得出一份被搞亂的內容;所以同時打那十次的答案,
    要與獨自打那一次逐字相同。
    """
    for endpoint in ENDPOINTS:
        alone = baseline[endpoint]
        together = [payload for job, (payload, _) in collision if job == endpoint]
        assert len(together) == HITS_EACH
        for payload in together:
            assert payload == alone, f"{endpoint} 同時打答出另一個答案"


def test_臨時鎖已移除(base_url):
    """驗收一(下半):KARST-050 那道令查庫排隊的臨時鎖不再存在。"""
    assert not hasattr(server_module, "_API_LOCK"), "server.py 仍然吊住那道臨時鎖"
    source = Path(server_module.__file__).read_text(encoding="utf-8")
    assert "_API_LOCK" not in source


def test_逐執行緒各自一條連線(reader):
    """連線逐執行緒一條:同一條執行緒之內共用,跨執行緒各有各的。"""

    def probe(_):
        store = reader.store
        # 同一條執行緒之內問兩次,拿到的要是同一條連線,不是每次重開
        assert reader.store is store
        # RunStore 綁住的亦是本執行緒那一條
        assert reader.runs.store is store
        # 真的查得到嘢,不是只得個空殼
        assert store.list_strategy_names() is not None
        return store

    with ThreadPoolExecutor(max_workers=3) as pool:
        stores = list(pool.map(probe, range(3)))

    assert len({id(store) for store in stores}) == 3, "幾條執行緒仍然共用同一條連線"


def test_四頁照舊開得到(base_url):
    """驗收二:頁面行為不變——登記在案的每一頁照舊出 200。"""
    for path in sorted(PAGE_FILES):
        with urllib.request.urlopen(base_url + path, timeout=60) as response:
            assert response.status == 200, path
            assert response.read(), path
