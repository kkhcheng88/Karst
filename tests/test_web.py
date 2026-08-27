"""KARST-032 驗收:本機網頁殼 v0,讀真實運行畫淨值圖與蠟燭圖。

四個測試對住票上四項驗收條件,一項一個,只證「行得通」,不掃邊界情況。

測試打的是**本機庫內真實的回測運行**——這正是要驗的那件事(規格 8.7:
頁面上不准有假數據)。庫或運行不在,就跳過,不用捏一組數頂上。
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

import pytest

from karst.web.data import build_reader
from karst.web.server import STATIC_ROOT, serve_in_background

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# design-system 1.7「圖表專用色」連 1.5 蠟燭圖成交量柱那兩格的全集。
# 圖表庫的選項不吃 CSS 變數,只能傳字面值;能出現在前端 JS 的就只有這一組。
ALLOWED_CHART_COLOURS = {
    "#26a69a",                  # 策略淨值線、買入標記、蠟燭升色(= --up)
    "#b07de0",                  # QQQ 線(= --bench-qqq)
    "#7d869c",                  # SPY 線、圖表軸文字色(= --bench-spy / --text-3)
    "#ef5350",                  # 沽出標記、蠟燭落色(= --down)
    "#8f9bb3",                  # 同日一買一沽的中性圓點
    "#4a5468",                  # 十字線
    "#2b3246",                  # 十字線標籤底(= --bg-4)
    "#262c3b",                  # 價軸與時間軸邊框(= --line)
    "rgba(38,44,59,.55)",       # 圖表格線(= --line 半透明)
    "rgba(18,22,31,.97)",       # 懸停成交浮層底
    "rgba(122,134,156,.4)",     # 成交量柱預設色
    "rgba(38,166,154,.35)",     # 蠟燭圖成交量柱(上日),design-system 1.5
    "rgba(239,83,80,.35)",      # 蠟燭圖成交量柱(落日),design-system 1.5
}


def _strip_comments(text: str) -> str:
    """剝走註釋,只留下真正會跑的程式碼——註釋裡提一句不算「吊住假數據」。"""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)      # JS/CSS 區塊註釋
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)     # HTML 註釋
    text = re.sub(r"^\s*//.*$", " ", text, flags=re.M)      # 整行 // 註釋
    return text


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def _get_json(url: str):
    return json.loads(_get(url))


@pytest.fixture(scope="module")
def reader():
    if not (PROJECT_ROOT / "karst.sqlite").is_file():
        pytest.skip("本機沒有定義庫,網頁殼無從讀起")
    built = build_reader(PROJECT_ROOT)
    if not built.list_runs(1)["total"]:
        pytest.skip("庫內未有任何回測運行")
    return built


@pytest.fixture(scope="module")
def base_url(reader):
    httpd, url = serve_in_background(reader)
    try:
        yield url
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture(scope="module")
def traded_run(reader):
    """庫內第一個有已平倉交易的運行——蠟燭圖上的出入場點要有東西可標。"""
    for item in reader.list_runs(12)["runs"]:
        detail = reader.get_run(item["runId"])
        if detail["trades"]:
            return detail
    pytest.skip("庫內沒有任何帶已平倉交易的運行")


def test_進出場標記落在對應日期的蠟燭上(base_url, traded_run):
    """驗收一:淨值圖與蠟燭圖畫得出,進出場標記落在對應日期的蠟燭上。"""
    run_id = traded_run["run"]["runId"]
    trade = traded_run["trades"][0]

    # 頁面本身載得到圖表庫與兩個圖區(淨值圖與蠟燭圖共用同一個圖區)
    page = _get(f"{base_url}/").decode("utf-8")
    assert 'id="main-chart"' in page
    assert "lightweight-charts.standalone.production.js" in page

    # 淨值圖:有逐日序列,亦有落在交易日上的買賣標記
    detail = _get_json(f"{base_url}/api/runs/{run_id}")
    assert len(detail["series"]["strategy"]["dates"]) > 1
    assert detail["tradeMarks"], "有交易的運行,淨值圖上要有交易日標記"

    # 蠟燭圖:每一個標記的日子都要真的有一根蠟燭
    candles = _get_json(
        f"{base_url}/api/runs/{run_id}/candles?symbol={trade['symbol']}"
    )
    assert candles["candles"], "畫不出蠟燭"
    assert candles["markers"], "該實體在這次運行有交易,蠟燭圖上要有標記"

    candle_days = {candle["time"] for candle in candles["candles"]}
    orphans = [m["time"] for m in candles["markers"] if m["time"] not in candle_days]
    assert not orphans, f"這幾個標記找不到對應日期的蠟燭:{orphans}"

    # 點中那一筆的進場日與出場日,兩日都要標得出
    marker_days = {m["time"] for m in candles["markers"]}
    assert trade["entryDate"] in marker_days
    assert trade["exitDate"] in marker_days
    assert {"buy", "sell"} <= {m["side"] for m in candles["markers"]}


def test_數據來自真實運行而非寫死的假數據(base_url, reader, traded_run):
    """驗收二:圖上數據經薄 REST 層來自一次真實回測運行,頁內查不到寫死的假數據。"""
    run_id = traded_run["run"]["runId"]
    payload = _get_json(f"{base_url}/api/runs/{run_id}")

    # REST 出的淨值,同 RunStore 由 parquet 讀回那一條逐點對得上
    stats = reader.runs.window_stats(run_id)
    values = payload["series"]["strategy"]["values"]
    assert len(values) == len(stats.equity)
    assert values[0] == pytest.approx(float(stats.equity.iloc[0]))
    assert values[-1] == pytest.approx(float(stats.equity.iloc[-1]))

    # 成交日標記的日子,同 orders.parquet 的成交日一模一樣
    orders = reader.runs.orders(run_id)
    assert {m["date"] for m in payload["tradeMarks"]} == set(
        orders["trade_date"].astype(str)
    )

    # 靜態頁不掛任何數據檔,亦沒有內嵌序列;數據只有一條路——/api/
    static_files = {p.name for p in STATIC_ROOT.iterdir() if p.is_file()}
    assert "data.js" not in static_files
    assert "data-ext.js" not in static_files

    # 原型那個「原型・假數據」徽章不准跟過來(design-system 3.15:正式版移除)
    page = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    assert "proto-badge" not in page
    assert "proto-stripe" not in page

    for name in ("index.html", "app.js", "run-view.js"):
        source = _strip_comments((STATIC_ROOT / name).read_text(encoding="utf-8"))
        # 不再吊住原型那份假數據檔(品牌字 KARST 不算,要的是那個全域數據物件)
        assert not re.search(r"(?:window|global)\s*\.\s*KARST", source), (
            f"{name} 仍然吊住原型的 window.KARST 假數據"
        )
        assert not re.search(r"\bKARST\s*\.\s*[a-z]", source), (
            f"{name} 仍然在讀原型假數據物件的欄位"
        )
        # 沒有一段寫死的長數列扮數據
        long_arrays = re.findall(r"\[\s*(?:-?\d+(?:\.\d+)?\s*,\s*){8,}", source)
        assert not long_arrays, f"{name} 內有寫死的數列"


def test_圖用lightweight_charts且色值字級取自設計系統(base_url):
    """驗收三:圖表用 lightweight-charts 畫,顏色與字級取 token,無自定色值。"""
    page = _get(f"{base_url}/").decode("utf-8")

    # 本地載入,不經 CDN(D-019:Apache-2.0,本地載入)
    assert "/static/vendor/lightweight-charts.standalone.production.js" in page
    assert "http://" not in page and "https://" not in page, "頁面不應該向外取任何東西"
    vendor = STATIC_ROOT / "vendor" / "lightweight-charts.standalone.production.js"
    assert vendor.is_file()
    assert "Lightweight Charts" in vendor.read_text(encoding="utf-8", errors="replace")[:400]

    # 前端 JS 內的色值,逐個都要在 design-system 登記過的那一組之內
    for name in ("app.js", "run-view.js"):
        text = (STATIC_ROOT / name).read_text(encoding="utf-8")
        literals = set(re.findall(r"#[0-9a-fA-F]{6}\b", text))
        literals |= {
            "rgba(" + m + ")"
            for m in re.findall(r"rgba\(([^)]*)\)", text)
        }
        stray = {c for c in literals if c.lower() not in ALLOWED_CHART_COLOURS}
        assert not stray, f"{name} 用了 design-system 未登記的色值:{sorted(stray)}"

    # 樣式表的 token 值同 design-system.md 正本一致
    css = (STATIC_ROOT / "style.css").read_text(encoding="utf-8")
    for token, value in (
        ("--bg-1", "#131722"),
        ("--text-1", "#e8eaf0"),
        ("--text-3", "#7d869c"),
        ("--up", "#26a69a"),
        ("--down", "#ef5350"),
        ("--accent", "#4a9eff"),
        ("--bench-qqq", "#b07de0"),
        ("--fs-xs", "11px"),
        ("--fs-md", "15px"),
        ("--nav-h", "52px"),
    ):
        assert re.search(rf"{re.escape(token)}\s*:\s*{re.escape(value)}", css), (
            f"style.css 的 {token} 對不上 design-system.md 的 {value}"
        )

    # 圖表字級用 --fs-xs 那一格(11),不是隨手一個數
    assert "fontSize: 11" in (STATIC_ROOT / "app.js").read_text(encoding="utf-8")


def test_換運行整頁跟住換且運行編號顯示得到(base_url):
    """驗收四:換一次運行,整頁的圖跟住換,該次運行的編號在頁面上顯示得到。"""
    listing = _get_json(f"{base_url}/api/runs?limit=8")
    assert listing["total"] >= 2, "庫內要有至少兩次運行才換得到"
    assert listing["runs"], "運行清單空白"

    # 揀兩次不同的運行,各自拿回自己那一份
    first = listing["runs"][0]["runId"]
    second = next(r["runId"] for r in listing["runs"] if r["runId"] != first)

    one = _get_json(f"{base_url}/api/runs/{first}")
    two = _get_json(f"{base_url}/api/runs/{second}")

    # 每一份都報得出自己是哪一次運行
    assert one["run"]["runId"] == first
    assert two["run"]["runId"] == second

    # 整頁跟住換:圖與指標是兩份不同的東西,不是同一份換個名
    assert (
        one["series"]["strategy"]["values"] != two["series"]["strategy"]["values"]
        or one["metrics"] != two["metrics"]
        or one["trades"] != two["trades"]
    )

    # 八項指標(D-020 第 8 條)兩份都齊
    for payload in (one, two):
        metrics = payload["metrics"]
        for key in (
            "totalReturnPct",
            "annualReturnPct",
            "maxDrawdownPct",
            "winRatePct",
            "profitLossRatio",
            "annualExcessPct",
            "sortino",
            "averageHoldingDays",
            "turnover",
        ):
            assert key in metrics, f"少了指標 {key}"

    # 運行編號在頁面上有落腳位,而且真的由 JS 填上去
    page = _get(f"{base_url}/").decode("utf-8")
    assert 'id="bc-run"' in page
    view = (STATIC_ROOT / "run-view.js").read_text(encoding="utf-8")
    assert "bcRun" in view and "runId" in view
