"""KARST-051 驗收:參數掃描頁讀真實掃描表與判讀表。

一項驗收條件一個測試,只證「行得通」,不掃邊界情況。

測試打的是**落在實驗目錄的真實掃描**——掃描結果未入庫(只有每格的運行編號
入了庫),所以頁面以掃描落檔目錄為來源,測試亦照同一條路核對。找不到掃描
落檔就跳過,不用捏一張表頂上(規格 8.7:頁面上不准有假數據)。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd
import pytest

from karst.web.data import build_reader
from karst.web.server import STATIC_ROOT, serve_in_background

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def _get_json(url: str):
    return json.loads(_get(url))


def _status(url: str) -> int:
    """只要狀態碼——用來驗錯誤態,所以錯誤本身不算測試失敗。"""
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def _sweep_url(base_url: str, sweep_id: str, layer: str | None = None) -> str:
    query = {"id": sweep_id}
    if layer is not None:
        query["layer"] = layer
    return f"{base_url}/api/sweep?" + urllib.parse.urlencode(query)


@pytest.fixture(scope="module")
def reader():
    if not (PROJECT_ROOT / "karst.sqlite").is_file():
        pytest.skip("本機沒有定義庫,網頁殼無從讀起")
    return build_reader(PROJECT_ROOT)


@pytest.fixture(scope="module")
def base_url(reader):
    httpd, url = serve_in_background(reader)
    try:
        yield url
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture(scope="module")
def sweeps(base_url):
    listing = _get_json(f"{base_url}/api/sweeps")
    usable = [s for s in listing["sweeps"] if not s.get("error")]
    if not usable:
        pytest.skip("本機沒有任何掃描落檔")
    return usable


@pytest.fixture(scope="module")
def layered(sweeps):
    """一次帶選擇軸、而且判讀已按軸型分層的掃描——切層要驗的就是它。"""
    for sweep in sweeps:
        if sweep["axisAware"] and sweep["layers"] > 1 and sweep["continuousAxes"]:
            return sweep
    pytest.skip("本機沒有已按軸型分層判讀的掃描")


def test_四個元件由真實掃描表與判讀表畫出(base_url, sweeps, layered):
    """驗收一:四個元件由真實掃描表與判讀表畫出,孤峰/山脊/平原標記可見。"""
    page = _get(f"{base_url}/sweep").decode("utf-8")
    for anchor in ('id="heat"', 'id="small"', 'id="nbhd"', 'id="slices"'):
        assert anchor in page, f"畫面缺了這個元件:{anchor}"
    assert "lightweight-charts.standalone.production.js" in page

    payload = _get_json(_sweep_url(base_url, layered["id"]))
    assert payload["cells"], "熱力圖一格都沒有"
    assert payload["projections"], "小倍數一張圖都沒有"

    # 格內的數,同掃描表 CSV 那一行逐點對得上——不是頁面自己算出來的
    grid = pd.read_csv(PROJECT_ROOT / payload["provenance"]["gridPath"], encoding="utf-8-sig")
    assert sum(row["cells"] for row in payload["layerRows"]) == len(grid)

    cell = next(c for c in payload["cells"] if c["runId"])
    mask = pd.Series(True, index=grid.index)
    for axis, value in cell["params"].items():
        column = grid[axis]
        if pd.api.types.is_numeric_dtype(column) and isinstance(value, (int, float)):
            mask &= (column.astype(float) - float(value)).abs() < 1e-9
        else:
            mask &= column.astype(str).str.strip() == str(value)
    matched = grid[mask]
    assert len(matched) == 1, "一組參數對不回掃描表的一行"
    assert str(matched.iloc[0]["run_id"]) == cell["runId"]
    for metric in cell["metrics"]:
        if metric["key"] in grid.columns and metric["value"] is not None:
            raw = float(matched.iloc[0][metric["key"]])
            scale = 100.0 if metric["unit"] == "pct" else 1.0
            assert metric["value"] == pytest.approx(raw * scale, rel=1e-9, abs=1e-9)

    # 三個裁決標記都真的有格拿得到——標記畫得出,不是死碼
    total = {"平原": 0, "山脊": 0, "孤峰": 0}
    for sweep in sweeps:
        for name in total:
            total[name] += sweep["counts"].get(name, 0)
    missing = [name for name, count in total.items() if count == 0]
    assert not missing, f"這幾個裁決在全部掃描裡一格都沒有,標記無從驗起:{missing}"


def test_選擇軸可切層而熱力圖只沿連續軸畫(base_url, layered):
    """驗收二:選擇軸可切層,熱力圖只沿連續軸畫。"""
    payload = _get_json(_sweep_url(base_url, layered["id"]))
    kinds = {axis["name"]: axis["kind"] for axis in payload["axisList"]}
    choice = [name for name, kind in kinds.items() if kind == "選擇"]
    assert choice, "這次掃描應該有選擇軸"
    assert set(payload["continuousAxes"]).isdisjoint(choice)

    # 一層 = 選擇軸取定一組值:同一層之內,選擇軸不再變
    names = [row["name"] for row in payload["layerRows"]]
    assert len(names) > 1
    for axis in choice:
        assert len({str(c["params"][axis]) for c in payload["cells"]}) == 1, (
            f"同一層之內選擇軸 {axis} 仍在變,熱力圖就不止沿連續軸畫"
        )

    # 切去另一層:層換到、格亦換到
    other = next(n for n in names if n != payload["layer"])
    switched = _get_json(_sweep_url(base_url, layered["id"], other))
    assert switched["layer"] == other
    assert switched["cells"]
    assert [c["params"] for c in switched["cells"]] != [c["params"] for c in payload["cells"]]

    # 連續軸的取值兩層一模一樣——換的只是層,不是那幅圖的骨架
    for axis in payload["continuousAxes"]:
        assert {str(c["params"][axis]) for c in switched["cells"]} == {
            str(c["params"][axis]) for c in payload["cells"]
        }


def test_載入中空錯誤三態齊全(base_url, sweeps):
    """驗收三:載入中/空/錯誤三態齊全。"""
    page = _get(f"{base_url}/sweep").decode("utf-8")
    assert 'id="page-state"' in page and 'id="detail-state"' in page
    assert 'id="cell-empty"' in page, "未點格之前要有一格空態"

    script = (STATIC_ROOT / "sweep.js").read_text(encoding="utf-8")
    for state in ("skeleton", "state-block", "function loading", "function empty", "function fail"):
        assert state in script, f"三態少了這一截:{state}"
    assert ".catch(" in script, "抓不到錯誤就出不到錯誤態"

    # 錯誤態有東西可出:掃描不存在、層不存在,兩樣都要 404 而不是 500
    assert _status(f"{base_url}/api/sweep?id=experiments/no-such-sweep") == 404
    assert _status(_sweep_url(base_url, sweeps[0]["id"], "沒有這一層")) == 404


def test_既有頁面行為不變(base_url):
    """驗收四:既有頁面行為不變(既有測試另由 tests/test_web.py 全套跑過)。"""
    assert _status(f"{base_url}/") == 200
    assert _status(f"{base_url}/run") == 200
    assert _status(f"{base_url}/static/app.js") == 200
    assert _get_json(f"{base_url}/api/runs?limit=1")["runs"], "運行清單應該照舊出得到"


def test_掃描清單一次掃描一行且最佳格與代表格並列(base_url, sweeps):
    """驗收五(2026-08-28 留言補):掃描清單一次掃描一行,最佳格與代表格並列、裁決可見。"""
    page = _get(f"{base_url}/sweep").decode("utf-8")
    assert 'id="sweep-table"' in page, "沒有掃描清單"

    for sweep in sweeps:
        for key in ("label", "cells", "objectiveLabel", "best", "representative", "reference"):
            assert key in sweep, f"掃描清單那一行缺了 {key}"

    paired = [s for s in sweeps if s["best"] and s["representative"]]
    assert paired, "沒有一次掃描同時報得出最佳格與代表格"
    for sweep in paired:
        assert sweep["best"]["verdict"], "最佳格的裁決要可見"
        assert sweep["representative"]["verdict"], "代表格的裁決要可見"
        # 代表格一定不是孤峰——防孤峰誤導正是它存在的理由
        assert sweep["representative"]["verdict"] != "孤峰"
        assert sweep["representative"]["neighbourhoodMean"] is not None

    # D-029:固定比例權重那種掃描要標「對照」
    weight_only = [
        s for s in sweeps
        if s["continuousAxes"] and all(a.startswith("weight_") for a in s["continuousAxes"])
    ]
    if weight_only:
        assert all(s["reference"] for s in weight_only), "固定比例權重掃描要標對照"
    assert not any(
        s["reference"] for s in sweeps if not s["continuousAxes"]
        or not all(a.startswith("weight_") for a in s["continuousAxes"])
    ), "驅動器參數掃描不應該標對照"

    # 點一格才開曲線(D-029):清單頁與熱圖都要指得出那一格的運行編號
    detail = _get_json(_sweep_url(base_url, paired[0]["id"]))
    assert any(c["runId"] for c in detail["cells"]), "一格都沒有運行編號,點格就開不到曲線"
