"""KARST-032 / KARST-042 驗收:本機網頁殼,讀真實運行畫圖,並可揀一段日期重看。

每張票四項驗收條件,一項一個測試,只證「行得通」,不掃邊界情況。

測試打的是**本機庫內真實的回測運行**——這正是要驗的那件事(規格 8.7:
頁面上不准有假數據)。庫或運行不在,就跳過,不用捏一組數頂上。
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

import pytest

from karst.errors import NotFound
from karst.metrics import run_metrics, trade_stats
from karst.web.data import DEFAULT_RISK_FREE_RATE, build_reader
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
    page = _get(f"{base_url}/run").decode("utf-8")
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
    # 根路徑自 KARST-049 起是策略總覽,運行詳情頁搬去 /run(頁本身一個字沒有改)
    page = _get(f"{base_url}/run").decode("utf-8")

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
    page = _get(f"{base_url}/run").decode("utf-8")
    assert 'id="bc-run"' in page
    view = (STATIC_ROOT / "run-view.js").read_text(encoding="utf-8")
    assert "bcRun" in view and "runId" in view


# ============================================================
# KARST-042 檢視視窗:揀一段日期,八項指標與淨值圖按該段重看
# ============================================================

# 票上指名那次真實運行(趨勢波段);2023 起那一段有期初存貨要承接。
# 數據目錄重建(KARST-057)後快照重抓、編號跟住換:舊 run-728a01087531258f。
WINDOW_RUN_ID = "run-7e3b498e086bdb88"
WINDOW_START = "2023-01-01"

# 八項指標(D-020 第 8 條)在 REST 出的名
EIGHT = (
    "totalReturnPct",
    "annualReturnPct",
    "maxDrawdownPct",
    "winRatePct",
    "profitLossRatio",
    "annualExcessPct",
    "sortino",
    "averageHoldingDays",
    "turnover",
)


@pytest.fixture(scope="module")
def windowed(reader):
    """一次跨過 2023 的真實運行——切得出視窗,才驗得到「重看」。"""
    try:
        return reader.runs.get_run(WINDOW_RUN_ID).run_id
    except NotFound:
        pass
    for item in reader.list_runs(12)["runs"]:
        if item["periodStart"] < WINDOW_START < item["periodEnd"]:
            return item["runId"]
    pytest.skip("庫內沒有一次跨過 2023 的運行,切不出檢視視窗")


def test_揀一段日期八項與淨值圖按該段重看而運行編號不變(base_url, windowed):
    """驗收一:頁面可揀起訖日期,八項指標與淨值圖隨之按該段重算,運行編號不變。"""
    page = _get(f"{base_url}/run").decode("utf-8")
    for anchor in ('id="win-pick"', 'id="win-from"', 'id="win-to"', "檢視視窗"):
        assert anchor in page, f"頁面上沒有檢視視窗控制:{anchor}"

    view = (STATIC_ROOT / "run-view.js").read_text(encoding="utf-8")
    for anchor in ("win-pick", "win-from", "win-to"):
        assert anchor in view, f"run-view.js 未接上 {anchor}"

    full = _get_json(f"{base_url}/api/runs/{windowed}")
    win = _get_json(f"{base_url}/api/runs/{windowed}?start={WINDOW_START}")

    # 是重看不是重跑:運行編號一個字不變
    assert win["run"]["runId"] == full["run"]["runId"] == windowed
    assert win["run"]["periodStart"] == full["run"]["periodStart"]

    # 淨值圖由視窗起始日重設基準(與 window_stats 一致),基準線同一把尺
    series = win["series"]
    first = series["strategy"]["dates"][0]
    assert first >= WINDOW_START
    assert first > full["series"]["strategy"]["dates"][0]
    assert series["strategy"]["values"][0] == pytest.approx(series["base"])
    for ticker, bench in series["benchmarks"].items():
        assert bench["dates"][0] == first, f"{ticker} 那條線不是由視窗起始日起"
        assert bench["values"][0] == pytest.approx(series["base"])

    # 八項按該段重算,不是全期那一份
    assert win["metrics"]["start"] == first
    assert win["metrics"] != full["metrics"]
    assert win["window"]["isFull"] is False and full["window"]["isFull"] is True


def test_起訖日期經薄REST層取數頁面不自行算指標(base_url, reader, windowed):
    """驗收二:薄 REST 層以起訖日期取數,頁面內無自行計算指標。"""
    payload = _get_json(f"{base_url}/api/runs/{windowed}?start={WINDOW_START}")
    truth = run_metrics(
        reader.runs,
        windowed,
        risk_free_rate=DEFAULT_RISK_FREE_RATE,
        start=WINDOW_START,
        snapshot_root=reader.snapshot_root,
    )
    m = payload["metrics"]
    assert (m["start"], m["end"], m["tradingDays"]) == (
        truth.start, truth.end, truth.trading_days
    )
    assert m["totalReturnPct"] == pytest.approx(truth.total_return * 100.0)
    assert m["annualReturnPct"] == pytest.approx(truth.annual_return * 100.0)
    assert m["maxDrawdownPct"] == pytest.approx(truth.max_drawdown * 100.0)
    assert m["winRatePct"] == pytest.approx(truth.win_rate * 100.0)
    assert m["profitLossRatio"] == pytest.approx(truth.profit_loss_ratio)
    assert m["sortino"] == pytest.approx(truth.sortino)
    assert m["averageHoldingDays"] == pytest.approx(truth.average_holding_days)
    assert m["turnover"] == pytest.approx(truth.turnover)
    for ticker, value in truth.annual_excess.items():
        assert m["annualExcessPct"][ticker] == pytest.approx(value * 100.0)

    # 蠟燭圖與買賣標記同樣經 REST 按這一段取數
    symbol = payload["trades"][0]["symbol"]
    stem = f"{base_url}/api/runs/{windowed}/candles?symbol={symbol}"
    inside = _get_json(f"{stem}&start={WINDOW_START}")
    whole = _get_json(stem)
    assert inside["candles"], "視窗內畫不出蠟燭"
    assert len(inside["candles"]) < len(whole["candles"])
    for candle in inside["candles"]:
        assert m["start"] <= candle["time"] <= m["end"]
    for mark in inside["markers"]:
        assert m["start"] <= mark["time"] <= m["end"]

    # 頁面只負責把日子交出去、把數字擺上畫面:沒有一條算指標的算式
    view = (STATIC_ROOT / "run-view.js").read_text(encoding="utf-8")
    assert "start=" in view and "end=" in view and "/api/runs/" in view
    for banned in ("Math.pow", "Math.sqrt", "Math.log", "cummax", "annualise"):
        assert banned not in view, f"run-view.js 自己算起指標來了:{banned}"


def test_不揀日期時全期的顯示與現行逐位相同(base_url, reader, windowed):
    """驗收三:全期(不揀日期)的顯示與現行逐位相同。"""
    payload = _get_json(f"{base_url}/api/runs/{windowed}")

    # 未有檢視視窗那一層之前,頁面就是這樣取數的
    equity = reader.runs.equity_curve(windowed)
    stats = reader.runs.window_stats(windowed)
    orders = reader.runs.orders(windowed)
    trades = trade_stats(orders, equity.index)
    truth = run_metrics(
        reader.runs,
        windowed,
        risk_free_rate=DEFAULT_RISK_FREE_RATE,
        snapshot_root=reader.snapshot_root,
    )

    assert payload["window"]["isFull"] is True
    assert payload["window"]["openingLots"] == 0, "全期沒有『之前』,期初存貨必然是空"

    series = payload["series"]["strategy"]
    assert len(series["values"]) == len(stats.equity)
    assert series["dates"][0] == str(stats.equity.index[0].date())
    assert series["values"][0] == pytest.approx(float(stats.equity.iloc[0]))
    assert series["values"][-1] == pytest.approx(float(stats.equity.iloc[-1]))

    assert len(payload["trades"]) == trades.closed_trades
    assert {mk["date"] for mk in payload["tradeMarks"]} == set(
        orders["trade_date"].astype(str)
    )

    m = payload["metrics"]
    assert m["totalReturnPct"] == pytest.approx(truth.total_return * 100.0)
    assert m["annualReturnPct"] == pytest.approx(truth.annual_return * 100.0)
    assert m["maxDrawdownPct"] == pytest.approx(truth.max_drawdown * 100.0)
    assert m["winRatePct"] == pytest.approx(truth.win_rate * 100.0)
    assert m["turnover"] == pytest.approx(truth.turnover)

    # 留空的起訖日與不帶起訖日同義
    assert _get_json(f"{base_url}/api/runs/{windowed}?start=&end=") == payload


def test_視窗前已有持倉的運行照樣顯示得出八項指標(base_url, reader):
    """驗收四:趨勢波段那次運行取 2023-01-01 起,八項顯示得出不報錯。"""
    try:
        reader.runs.get_run(WINDOW_RUN_ID)
    except NotFound:
        pytest.skip(f"本機庫內沒有 {WINDOW_RUN_ID}")

    payload = _get_json(f"{base_url}/api/runs/{WINDOW_RUN_ID}?start={WINDOW_START}")

    # 視窗開波之前已經在手上那幾注,承接得到才算得出來回類三項(KARST-039)
    assert payload["window"]["openingLots"] == 4
    assert payload["window"]["start"] == "2023-01-03"

    m = payload["metrics"]
    for key in EIGHT:
        assert key in m, f"少了指標 {key}"
        assert m[key] is not None, f"指標 {key} 算不出"

    assert m["totalReturnPct"] == pytest.approx(81.66, abs=0.01)
    assert m["annualReturnPct"] == pytest.approx(17.89, abs=0.01)
    assert m["maxDrawdownPct"] == pytest.approx(-18.14, abs=0.01)
    assert m["winRatePct"] == pytest.approx(48.19, abs=0.01)


# ============================================================
# KARST-053 運行選單認得出是哪一次、圖例可點、說明句已刪
# ============================================================

# 庫內兩次正式運行(示例運行)。掃描格一律不入運行清單(D-029)。
# 舊編號 run-728a01087531258f / run-f4c162e5aac34347 在數據目錄重建(KARST-057)
# 之後成為過時運行(序列缺失):登記照舊在案,但逐日序列已經不在,畫不出圖。
FORMAL_RUNS = ("run-7e3b498e086bdb88", "run-024df83fb4891c89")


def test_運行選單只列正式運行且認得出是哪一次(base_url, reader):
    """驗收一:選單顯示策略・參數集・期間・日期,不顯示編號;掃描格不在列。"""
    listing = _get_json(f"{base_url}/api/runs?limit=8")

    # 一、掃描格不入清單:庫內幾千次運行,清單上只剩正式那幾次
    在庫 = len(reader.runs.list_runs())
    assert listing["total"] < 在庫, "運行清單沒有把掃描格擋走"
    for item in listing["runs"]:
        assert not item["paramSetName"].startswith("掃描"), (
            f"掃描格 {item['runId']} 走進了運行清單"
        )

    # 二、兩個示例運行必須在列
    在列 = {item["runId"] for item in listing["runs"]}
    for run_id in FORMAL_RUNS:
        try:
            reader.runs.get_run(run_id)
        except NotFound:
            continue  # 本機庫內沒有這一次,不能怪清單
        assert run_id in 在列, f"示例運行 {run_id} 不在運行選單"

    # 三、選單那四樣東西,端點逐項交得出(頁面才有得顯示)
    for item in listing["runs"]:
        for key in ("strategyName", "paramSetName", "paramSetVersionNo",
                    "periodStart", "periodEnd", "createdAt"):
            assert item.get(key), f"{item['runId']} 少了選單要顯示的 {key}"

    # 四、按鈕的字是那四樣,不是運行編號;編號退到明細(頁頭小字與身分卡)
    view = _strip_comments((STATIC_ROOT / "run-view.js").read_text(encoding="utf-8"))
    標籤 = re.search(r"function runLabel\(r\)\s*\{.*?\n  \}", view, flags=re.S)
    assert 標籤, "run-view.js 找不到運行選單的標籤"
    標籤文 = 標籤.group(0)
    for key in ("strategyName", "paramSetName", "paramSetVersionNo",
                "periodStart", "periodEnd", "createdAt"):
        assert key in 標籤文, f"運行選單沒有顯示 {key}"
    assert "runId" not in 標籤文, "運行選單仍然把運行編號當招牌"
    assert 'id="bc-run"' in _get(f"{base_url}/run").decode("utf-8")


def test_圖表下的說明句已刪(base_url):
    """驗收二:「N 條線同以 X 為基期・曲線上的箭嘴……」那一句不再出現。"""
    view = _strip_comments((STATIC_ROOT / "run-view.js").read_text(encoding="utf-8"))
    for 字 in ("為基期", "曲線上的箭嘴"):
        assert 字 not in view, f"圖表下的說明句還在:{字}"


def test_圖例每項可點收起該條線(base_url):
    """驗收三:QQQ、SPY 與策略淨值三條線,圖例上逐條收得起、放得回。"""
    view = _strip_comments((STATIC_ROOT / "run-view.js").read_text(encoding="utf-8"))

    # 圖例是真按鈕,鍵盤到得了;aria-pressed 講出這一刻是開還是關
    assert "legendButton" in view and "data-line" in view
    assert "aria-pressed" in view
    # 收起是叫圖表不畫那一條,不是把它由數據裡刪走
    assert "applyOptions({ visible: on })" in view
    # 三條線都掛得上鍵:策略一個、基準逐個用自己的代號
    assert "STRATEGY_LINE" in view
    assert "state.lines[name] = line" in view

    # 基準真的有 QQQ 同 SPY 兩條,收得起的就是它們
    listing = _get_json(f"{base_url}/api/runs?limit=1")
    detail = _get_json(f"{base_url}/api/runs/{listing['runs'][0]['runId']}")
    assert set(detail["series"]["benchmarks"]) >= {"QQQ", "SPY"}

    # 點來點去只關畫面的事:八項指標由 /api/ 交,頁面沒有一條算式(同 KARST-042)
    for banned in ("Math.pow", "Math.sqrt", "Math.log"):
        assert banned not in view
