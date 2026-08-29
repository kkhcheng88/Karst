"""KARST-049 驗收:策略總覽頁(真數據)。

四項驗收條件,一項一個測試,只證「行得通」,不掃邊界情況。

測試打的是**本機庫內真實的策略與回測運行**——這正是要驗的那件事(規格 8.7:
頁面上不准有假數據)。庫或策略不在,就跳過,不用捏一組數頂上。
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

import pytest

from karst.metrics import run_metrics
from karst.store import FORMAL_RUN, SWEEP_RUN
from karst.web.api_overview import PAGES, STRATEGY_TYPE_NAMES, _page
from karst.web.data import build_reader
from karst.web.server import STATIC_ROOT, serve_in_background

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def _get_json(url: str):
    return json.loads(_get(url))


def _strip_comments(text: str) -> str:
    """剝走註釋,只留下真正會跑的程式碼——註釋裡提一句不算「吊住假數據」。"""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"^\s*//.*$", " ", text, flags=re.M)
    return text


@pytest.fixture(scope="module")
def reader():
    if not (PROJECT_ROOT / "karst.sqlite").is_file():
        pytest.skip("本機沒有定義庫,策略總覽無從讀起")
    built = build_reader(PROJECT_ROOT)
    if not built.store.list_strategy_names():
        pytest.skip("庫內未有任何策略")
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
    return _get_json(f"{base_url}/api/overview")


def test_開本機網址即見策略總覽而每行來自庫內真實策略(base_url, reader, overview):
    """驗收一:根路徑就是策略總覽,表內每一行是庫內真實策略與其最新運行成績。"""
    page = _get(f"{base_url}/").decode("utf-8")
    assert "<title>策略總覽 — Karst</title>" in page
    assert 'id="grp-body"' in page, "總覽的表身不在根路徑那一頁"
    assert "/static/overview.js" in page

    # 表上那批策略,同定義庫登記的那批逐個對得上,一套不多一套不少
    names = [s["name"] for s in overview["strategies"]]
    assert names == reader.store.list_strategy_names()

    # 有成績那幾行,逐項對得住由 karst.metrics 獨立算一次的結果
    scored = [s for s in overview["strategies"] if s["metrics"]]
    assert scored, "庫內未有任何跑得出成績的策略"
    for row in scored:
        metrics = run_metrics(
            reader.runs,
            row["runId"],
            risk_free_rate=reader.risk_free_rate,
            benchmarks=reader.benchmarks,
            snapshot_root=reader.snapshot_root,
        )
        assert row["metrics"]["annualReturnPct"] == pytest.approx(
            metrics.annual_return * 100
        )
        assert row["metrics"]["maxDrawdownPct"] == pytest.approx(
            metrics.max_drawdown * 100
        )
        assert row["metrics"]["closedTrades"] == metrics.closed_trades
        # 「對基準」那一欄就是累計超額,不是頁面自己減出來的另一個數
        assert row["metrics"]["vsBenchPp"] == pytest.approx(
            metrics.benchmarks["QQQ"].excess_total_return * 100
        )
        # D-039:總覽表新增的 Sortino 一欄,同 karst.metrics 獨立算一次的結果對得上
        if metrics.sortino is None:
            assert row["metrics"]["sortinoRatio"] is None
        else:
            assert row["metrics"]["sortinoRatio"] == pytest.approx(metrics.sortino)
        # 該行報的那次運行,確實是這套策略庫內的其中一次,而且不是掃描格
        record = reader.store.get_run(row["runId"])
        assert record.strategy_name == row["name"]
        assert record.origin == FORMAL_RUN, "門面成績被一格參數掃描頂替了"


def test_總覽只算正式運行掃描格不計不列(reader, overview):
    """總覽的成績與運行數只算正式運行;參數掃描一格都不計、不列。

    (用戶 2026-08-28 追問後由協調者交低:掃描另在參數掃描頁一次掃描一行呈現。)
    """
    records = reader.store.list_runs()
    formal = [r for r in records if r.origin == FORMAL_RUN]
    swept = [r for r in records if r.origin == SWEEP_RUN]
    assert swept, "庫內未有掃描格,這一項驗不到"
    assert len(formal) + len(swept) == len(records), "有運行的來歷兩邊都不屬"

    # KARST-077:總覽的正式運行數與逐套策略的運行數,同 data.py／api_strategy.py
    # 同一條規矩——序列缺失運行(KARST-057)登記在案,但不算「可揀的正式運行」。
    usable = [r for r in formal if not reader.series_missing(r)]

    meta = overview["meta"]
    assert meta["runCount"] == len(usable)
    assert meta["sweepRunCount"] == len(swept)
    assert meta["runCount"] < len(records), "掃描格仍然計進總覽的運行數"

    # 逐套策略的運行數亦只計正式運行(且不計序列缺失那幾條)
    for row in overview["strategies"]:
        mine = [r for r in usable if r.strategy_name == row["name"]]
        assert row["runCount"] == len(mine)

    # 只跑過掃描、未有正式運行那一套:照樣在表上見到,而且講得出為什麼是空的
    only_swept = [
        s for s in overview["strategies"] if s["runCount"] == 0 and s["sweepRunCount"]
    ]
    for row in only_swept:
        assert row["metrics"] is None
        assert "參數掃描" in (row["note"] or "")

    # 靜態頁不掛任何數據檔,亦無內嵌序列;數據只有一條路——/api/
    for name in ("overview.html", "overview.js"):
        source = _strip_comments((STATIC_ROOT / name).read_text(encoding="utf-8"))
        assert not re.search(r"(?:window|global)\s*\.\s*KARST", source)
        assert not re.findall(r"\[\s*(?:-?\d+(?:\.\d+)?\s*,\s*){8,}", source), (
            f"{name} 內有寫死的數列"
        )
    # 原型那個「原型・假數據」徽章不准跟過來(design-system 3.15:正式版移除)
    page_source = (STATIC_ROOT / "overview.html").read_text(encoding="utf-8")
    assert "proto-badge" not in page_source and "proto-stripe" not in page_source


def test_有成績那幾行代表的運行本身不是失敗運行(overview):
    """驗收(KARST-077/D-034):總覽揀來代表一套策略的那次運行,如果有成績
    可看,那次本身就不是失敗運行——門面不首先擺一個已知跑輸大盤的結果。
    """
    from karst.web.data import is_failed_run

    scored = [s for s in overview["strategies"] if s["metrics"]]
    assert scored, "庫內未有任何跑得出成績的策略"
    for row in scored:
        bench = {
            ticker: b["annualReturnPct"] / 100.0
            for ticker, b in row["benchmarks"].items()
            if b["annualReturnPct"] is not None
        }
        judged = is_failed_run(row["metrics"]["annualReturnPct"] / 100.0, bench)
        assert judged is not True, f"{row['name']} 門面代表的運行本身是失敗運行"


def test_全部正式運行失敗的策略仍列一行只留失敗計數(overview):
    """驗收(KARST-077/D-040):一套策略全部正式運行都是失敗運行,那一行仍然
    照列(不是隱藏、不是移除),成績欄留空,只帶一個失敗計數——不是「有一次
    失敗運行」就整行不見。
    """
    all_failed_rows = [s for s in overview["strategies"] if s["isFailed"]]
    if not all_failed_rows:
        pytest.skip("本機庫內未有一套策略全部正式運行都失敗,這一項驗不到")
    for row in all_failed_rows:
        assert row["runCount"] > 0, "全部運行都失敗的前提是真的有運行"
        assert row["failedRunCount"] == row["runCount"]
        assert row["metrics"] is None
        assert str(row["failedRunCount"]) in (row["note"] or "")
        # 這一行仍然是一套「看得見」的策略:名稱、運行編號照舊,開得進策略詳情頁
        assert row["name"]
        assert row["runId"]


def test_類型篩選與搜尋可用且側欄有明細(base_url, reader, overview):
    """驗收二:類型篩選、名稱搜尋照原型可用;側欄明細有成績卡。

    (D-039/KARST-081:迷你走勢欄與其資料整個拿走,這裡不再驗小走勢,
    改驗那批資料真的沒有再送到前端。)
    """
    page = (STATIC_ROOT / "overview.html").read_text(encoding="utf-8")
    script = (STATIC_ROOT / "overview.js").read_text(encoding="utf-8")

    # 篩選列的三件零件同原型一致:類型晶片、搜尋框、篩出幾多的計數
    assert 'id="type-chips"' in page and 'id="q"' in page and 'id="filter-count"' in page
    assert 'id="detail"' in page, "右邊的明細側欄不在"
    assert "picked[s.type]" in script, "類型篩選沒有接上"
    assert "s.name.toLowerCase().indexOf(q)" in script, "名稱搜尋沒有接上"
    assert "renderDetail" in script

    # D-039:迷你走勢連同它的資料一併拿走——畫線的函式不應該再留在腳本裡,
    # 回應裡逐行都不應該再帶 equity/benchEquity 這兩個陣列。
    assert "function sparkline" not in script
    for row in overview["strategies"]:
        assert "equity" not in row and "benchEquity" not in row

    # 篩選要有得篩:每一行的類型都是庫認得那八類之一,而且中文名對得上
    for row in overview["strategies"]:
        assert row["type"] in STRATEGY_TYPE_NAMES
        assert row["typeName"] == STRATEGY_TYPE_NAMES[row["type"]]


def test_載入中空錯誤三態齊全且導航列兩頁連結齊全(base_url):
    """驗收三:三態照設計系統做齊;導航列兩頁(D-036),未建的連去佔位空狀態。"""
    script = (STATIC_ROOT / "overview.js").read_text(encoding="utf-8")

    # 載入中:骨架列(design-system 3.15 第 8 條,早已定義、原型未接上)
    assert "skeleton" in script and "showLoading" in script
    # 空:未有策略時整版換成狀態塊
    assert "state-block" in script and "未有策略" in script
    # 錯誤:拿不到數據講得出原因,而且再試得過
    assert "拿不到數據" in script and "state-retry" in script
    # 收起一塊要改 display:.fit-main 是 display:grid,單靠 hidden 屬性蓋不過它,
    # 蓋不過的話錯誤態出現時骨架表仍然留在上面(實測見過)
    assert "style.display" in script

    # 導航列兩頁齊全(D-035:運行詳情不是頂層頁面,是策略詳情的鑽取層;
    # D-036:參數掃描降為策略詳情的下鑽層,頂層只剩總覽同詳情兩頁),
    # 兩條連結逐條開得到(未建那頁開出佔位空狀態)
    app_js = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    hrefs = re.findall(r"\{\s*href:\s*'([^']+)'\s*,\s*label:\s*'([^']+)'\s*\}", app_js)
    assert len(hrefs) == 2, f"導航列不是兩頁:{hrefs}"
    assert [label for _, label in hrefs] == ["策略總覽", "策略詳情"]
    for href, label in hrefs:
        body = _get(f"{base_url}{href}").decode("utf-8")
        assert "<html" in body.lower(), f"導航列的 {label} 開不出一頁"
    # 未建成的頁連去佔位空狀態,不是死連結;建成之後同一條連結自動出該頁本身
    assert PAGES["/strategy"] == _page("strategy.html")
    assert PAGES["/sweep"] == _page("sweep.html")
    assert _page("這一頁不存在.html") == "pending.html"
    pending = (STATIC_ROOT / "pending.html").read_text(encoding="utf-8")
    assert "state-block" in pending and 'href="/"' in pending


def test_運行詳情頁改為策略詳情鑽取層直連網址仍行得通(base_url):
    """驗收(D-035):運行詳情不再是頂層頁面,但網址、頁面本身、端點照舊
    行得通——是導覽與入口改變,不是這個頁面被拆走。"""
    served = _get(f"{base_url}/run").decode("utf-8")
    on_disk = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    assert served == on_disk, "/run 出的不是原本那一頁"
    assert "/static/run-view.js" in served

    # 運行詳情自己那批端點照舊行得通(server.py 不用改)
    listing = _get_json(f"{base_url}/api/runs?limit=2")
    assert listing["runs"], "運行清單空白"
    detail = _get_json(f"{base_url}/api/runs/{listing['runs'][0]['runId']}")
    assert detail["series"]["strategy"]["values"], "運行詳情的淨值線空白"

    # 導航列不再有「運行詳情」這一項(D-035);這一頁掛的導覽現頁高亮落在
    # 「策略詳情」,回上層改由麵包屑(design-system 3.6a)承擔
    view = (STATIC_ROOT / "run-view.js").read_text(encoding="utf-8")
    assert "KV.mountNav('/strategy'" in view
    assert "bcCrumb" in view, "運行詳情頁沒有掛麵包屑"
    app_js = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    assert "label: '運行詳情'" not in app_js

    # D-035(用戶原話:「檢視運行 bar is not useful again if I have thousands
    # of run for this strategy」):運行詳情頁不再有自己的「檢視運行」選擇器
    assert "mountRunPick" not in view and "RUN_PICK_LIMIT" not in view
