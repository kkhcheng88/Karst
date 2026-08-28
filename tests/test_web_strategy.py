"""KARST-050 驗收:策略詳情頁,五個元件全部由庫內真實運行畫出。

四項驗收條件,一項一個測試,只證「行得通」,不掃邊界情況(照 test_web.py 同一套)。

測試打的是**本機庫內真實的回測運行**——這正是要驗的那件事(規格 8.7:
頁面上不准有假數據)。庫或運行不在,就跳過,不用捏一組數頂上。
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from karst.metrics import trade_stats
from karst.metrics.ratios import annual_volatility
from karst.runs import BASE, window_stats
from karst.store import FORMAL_RUN
from karst.web.data import build_reader
from karst.web.server import STATIC_ROOT, serve_in_background

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _strip_comments(text: str) -> str:
    """剝走註釋,只留下真正會跑的程式碼——註釋裡提一句不算「吊住假數據」。"""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"^\s*//.*$", " ", text, flags=re.M)
    return text


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def _get_json(url: str):
    return json.loads(_get(url))


def _status_of(url: str) -> int:
    """拿 HTTP 狀態碼,錯誤碼一樣要拿得到(錯誤態是要驗的東西之一)。"""
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


@pytest.fixture(scope="module")
def reader():
    if not (PROJECT_ROOT / "karst.sqlite").is_file():
        pytest.skip("本機沒有定義庫,策略詳情頁無從讀起")
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
def overview(base_url):
    """不帶 id 就是「最近有運行的那一套」——直接開 /strategy 也有東西看。"""
    payload = _get_json(base_url + "/api/strategy")
    if not payload["runTotal"]:
        pytest.skip("庫內那套策略未有任何運行")
    return payload


# ---------------------------------------------------------------- 驗收一


def test_五個元件全部由真實運行數據畫出(reader, base_url, overview):
    """淨值對基準、選股快照、漏斗、歷次運行、因子分布,逐個對回 Python 層真值。"""
    run_id = overview["defaultRunId"]
    record = reader.runs.get_run(run_id)

    # 一、淨值對基準:策略線與基準線同一段日期,基期一致(沿用 /api/runs 那個端點)
    detail = _get_json(base_url + "/api/runs/" + run_id)
    series = detail["series"]
    assert series["strategy"]["values"], "策略淨值線是空的"
    assert series["strategy"]["values"][0] == pytest.approx(series["base"])
    assert series["benchmarks"], "一條基準線都畫不出"
    for ticker, curve in series["benchmarks"].items():
        assert len(curve["dates"]) == len(curve["values"])
        assert curve["values"][0] == pytest.approx(series["base"]), ticker

    # 二、頭條數字多出的那一格(波幅)照 karst.metrics 算,不是頁面自己算
    equity = reader.runs.equity_curve(run_id)
    stats = window_stats(equity, None, None, base=BASE)
    win = _get_json(base_url + "/api/strategy/window?run=" + run_id)
    assert win["annualVolatilityPct"] == pytest.approx(annual_volatility(stats.equity) * 100.0)

    # 三、選股快照與漏斗:範圍與持倉逐個對回庫內持倉
    picks = _get_json(base_url + "/api/strategy/picks?run=" + run_id)
    held = reader.runs.holdings_on(run_id, picks["date"])
    holding_rows = [row for row in picks["rows"] if row["held"]]
    assert {row["entityId"] for row in holding_rows} == {
        eid for eid, shares in held.items() if shares > 0
    }
    labels = [layer["label"] for layer in picks["funnel"]]
    assert labels[0] == "範圍" and labels[-1] == "持倉"
    assert picks["funnel"][0]["count"] == len(picks["rows"])
    assert picks["funnel"][-1]["count"] == len(holding_rows)
    # 漏斗是「到達該層」的語意(design-system 5.1):後一層永不多過前一層
    counts = [layer["count"] for layer in picks["funnel"]]
    assert counts == sorted(counts, reverse=True)
    # 股數照實出,不是頁面砌出來的
    for row in holding_rows:
        assert row["shares"] == pytest.approx(held[row["entityId"]])

    # 四、因子分布:每一格敞口都指得回這次運行真正引用的因子
    families = {factor.family for factor in record.factors}
    carried = {row["symbol"] for row in holding_rows}
    for item in picks["exposure"]:
        assert item["family"] is None or item["family"] in families
        assert item["symbol"] in carried or item["weightPct"] == 0.0

    # 五、歷次運行:那三個數照 karst.metrics 算
    page = _get_json(base_url + "/api/strategy/runs?id=" + str(overview["strategy"]["id"]) + "&limit=3")
    first = page["items"][0]
    truth_equity = reader.runs.equity_curve(first["runId"])
    truth = window_stats(truth_equity, None, None, base=BASE)
    trades = trade_stats(reader.runs.orders(first["runId"]), truth_equity.index)
    assert first["annualReturnPct"] == pytest.approx(truth.annual_return * 100.0)
    assert first["maxDrawdownPct"] == pytest.approx(truth.max_drawdown * 100.0)
    assert first["winRatePct"] == pytest.approx(trades.win_rate * 100.0)

    # 六、頁內不准吊住假數據:五個元件的掛點在,數字一個都不寫死
    page_html = (STATIC_ROOT / "strategy.html").read_text(encoding="utf-8")
    for host in ("equity-chart", "picks-table", "funnel", "runs-body", "factor-expo"):
        assert 'id="' + host + '"' in page_html, host
    script = _strip_comments((STATIC_ROOT / "strategy.js").read_text(encoding="utf-8"))
    assert "window.KARST" not in script and "KARST." not in script


# ---------------------------------------------------------------- 驗收二


def test_歷次運行表列出該策略全部運行並跳得到運行詳情(reader, base_url, overview):
    name = overview["strategy"]["name"]
    sid = str(overview["strategy"]["id"])

    # 這張表的口徑要與端點一樣,兩件事都要扣起:
    #   一、掃描格不入運行清單(D-029、KARST-054 起問 backtest_run.origin);
    #   二、序列缺失運行不入清單(KARST-057)——逐日序列不在磁碟上,
    #       這張表逐行要讀的年化/回撤/勝率根本算不出來。
    # 兩樣都是登記照舊在案、清單不列,所以這裡數的是「列得出的那幾次」。
    every = [
        record
        for record in reader.store.list_runs(name, origin=FORMAL_RUN)
        if not reader.series_missing(record)
    ]

    page = _get_json(base_url + "/api/strategy/runs?id=" + sid + "&limit=5")
    assert page["total"] == len(every), "報稱的總數與庫內對不上"
    assert page["shown"] == min(5, len(every))

    # 逐頁取得完:第二頁接得上第一頁,不重複亦不跳號
    if page["total"] > 5:
        second = _get_json(base_url + "/api/strategy/runs?id=" + sid + "&limit=5&offset=5")
        ids = [r["runId"] for r in page["items"]] + [r["runId"] for r in second["items"]]
        assert len(set(ids)) == len(ids)
        newest_first = [r.run_id for r in reversed(every)][: len(ids)]
        assert ids == newest_first

    # 點一行跳到運行詳情:那一頁在、而且該運行編號真的開得到
    from karst.web.server import PAGE_FILES

    assert "/run" in PAGE_FILES, "運行詳情頁的路徑不見了,歷次運行表跳不過去"
    assert (STATIC_ROOT / PAGE_FILES["/run"]).is_file()
    target = page["items"][0]["runId"]
    assert _status_of(base_url + "/api/runs/" + target) == 200
    assert 'href="/run?run=' in (STATIC_ROOT / "strategy.js").read_text(encoding="utf-8")


# ---------------------------------------------------------------- 驗收三


def test_載入中空錯誤三態齊全(base_url, overview):
    script = (STATIC_ROOT / "strategy.js").read_text(encoding="utf-8")
    # 三態各有自己的出口,而且用的是 design-system 已定義的狀態塊與骨架列
    assert "function showLoading" in script and "skeleton" in script
    assert "function showEmpty" in script
    assert "function showFail" in script and "state-block" in script

    # 錯誤態:揀了一套庫內沒有的策略,是 404 不是伺服器壞
    missing = urllib.parse.quote("這套策略不存在")
    assert _status_of(base_url + "/api/strategy?id=" + missing) == 404
    # 揀了一次不存在的運行:一樣是 404
    assert _status_of(base_url + "/api/strategy/picks?run=run-0000000000000000") == 404
    # 沒講要看哪一次運行、或者揀了一個不是日子的日子:是揀錯,400
    assert _status_of(base_url + "/api/strategy/picks") == 400
    run_id = overview["defaultRunId"]
    bad_day = urllib.parse.quote("舊年")
    assert _status_of(base_url + "/api/strategy/picks?run=" + run_id + "&date=" + bad_day) == 400


# ---------------------------------------------------------------- 驗收四


def test_既有頁面行為不變(reader, base_url):
    """新端點只加不改:舊端點與舊頁面照舊。"""
    assert _status_of(base_url + "/api/meta") == 200
    assert _status_of(base_url + "/api/runs?limit=3") == 200
    listing = _get_json(base_url + "/api/runs?limit=3")
    assert listing["runs"], "舊的運行清單端點空了"
    run_id = listing["runs"][0]["runId"]
    assert _status_of(base_url + "/api/runs/" + run_id) == 200

    # 舊頁面(運行詳情)照舊出得到,策略詳情頁自己那一頁亦在
    assert _status_of(base_url + "/run") == 200
    assert _status_of(base_url + "/strategy") == 200

    # 一條 sqlite 連線,幾個頁面同時查庫也不會互相搞亂(策略頁一開就三個請求並行)
    from concurrent.futures import ThreadPoolExecutor

    paths = [
        "/api/meta",
        "/api/runs?limit=3",
        "/api/runs/" + run_id,
        "/api/strategy",
        "/api/strategy/picks?run=" + run_id,
    ]
    with ThreadPoolExecutor(max_workers=len(paths)) as pool:
        codes = list(pool.map(lambda p: _status_of(base_url + p), paths))
    assert codes == [200] * len(paths), dict(zip(paths, codes))


# ------------------------------------------------- KARST-067 收尾兩件


def test_只帶運行編號的網址與帶齊策略編號時顯示一致(reader, base_url):
    """``?run=`` 不帶 ``?id=``:由運行反查它自己那套策略,不再退回預設那一套。

    以前這一格答「最近有運行的那一套」,於是 ``/strategy?run=<因子混合那次>``
    的頁頂身份與歷次運行表掛住趨勢波段,而正在看的運行屬於另一套——兩種寫法
    看同一次運行,顯示不一樣,而且錯得無聲(KARST-056 順帶發現)。
    """
    default = _get_json(base_url + "/api/strategy")

    # 要驗得出分別,那次運行必須**不屬於**預設那一套策略
    picked = None
    for name in reader.store.list_strategy_names():
        if name == default["strategy"]["name"]:
            continue
        runs = [
            record
            for record in reader.store.list_runs(name, origin=FORMAL_RUN)
            if not reader.series_missing(record)
        ]
        if runs:
            picked = (name, runs[-1].run_id)
            break
    if picked is None:
        pytest.skip("庫內只有一套策略有正式運行,兩種寫法的分別驗不出來")
    name, run_id = picked

    by_run = _get_json(base_url + "/api/strategy?run=" + run_id)
    assert by_run["strategy"]["name"] == name, "只帶運行編號時仍然取了別套策略"

    sid = str(by_run["strategy"]["id"])
    assert by_run == _get_json(base_url + "/api/strategy?id=" + sid + "&run=" + run_id)

    # 下面那張歷次運行表同一個口徑,而且真的列得出正在看的那一次
    runs_by_run = _get_json(base_url + "/api/strategy/runs?run=" + run_id + "&limit=50")
    assert runs_by_run == _get_json(
        base_url + "/api/strategy/runs?id=" + sid + "&run=" + run_id + "&limit=50"
    )
    assert run_id in [item["runId"] for item in runs_by_run["items"]]

    # 網址指名了一次庫內沒有的運行:答不出就講答不出,不會靜靜退回預設那一套
    assert _status_of(base_url + "/api/strategy?run=run-0000000000000000") == 404

    # 頁面那一邊要把 run 帶去問,否則端點永遠收不到它
    script = _strip_comments((STATIC_ROOT / "strategy.js").read_text(encoding="utf-8"))
    assert "'run=' + encodeURIComponent(wantedRun)" in script


def test_宏觀驅動器參數區的序列齊全度由真數據填(reader, base_url):
    """參數區那一行掛的是 KARST-061 那個小端點,數由已凍結快照當場重算。"""
    from karst.data.macro import read_macro_completeness

    script = _strip_comments((STATIC_ROOT / "strategy.js").read_text(encoding="utf-8"))
    assert "序列齊全度" in script
    assert "/api/macro/completeness?snapshot=" in script
    # 跟住的是這次運行參數集記住的那份宏觀快照,不是頁面自己揀一份
    assert "run.paramValues.macro_snapshot" in script

    macro_root = Path(reader.snapshot_root).parent / "macro_snapshots"
    picked = next(
        (
            listing.snapshot_id
            for listing in reader.store.list_snapshots()
            if (macro_root / listing.snapshot_id).is_dir()
        ),
        None,
    )
    if picked is None:
        pytest.skip("本機沒有已凍結的宏觀快照,那一行的真數據無從對")

    payload = _get_json(base_url + "/api/macro/completeness?snapshot=" + picked)
    truth = read_macro_completeness(reader.store, picked, root=macro_root)
    assert payload["seriesCount"] == len(truth)
    assert payload["worstStaleDays"] == int(truth["stale_days"].max())
    assert payload["staleSeries"] == [
        str(row["series"])
        for row in truth.to_dict("records")
        if int(row["stale_days"]) > 0
    ]
    # 沒有給門檻 = 沒有裁決:頁面那一行講「落後幾多日」,不會自己揀一套門檻判合格
    assert payload["thresholds"] is None and payload["alerts"] == []
