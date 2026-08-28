"""KARST-049 策略總覽頁的讀取層與端點。

打開本機網址第一眼見到的是**策略總覽**:庫內每一套策略一行,連住它最新
一次運行的成績。本檔只讀不寫,而且與 ``karst.web.data`` 同一條規矩:

* 庫一律經 ``karst.store.DefinitionStore``(D-027 第 4 條第二條護欄),
  本檔自己不開 sqlite、不寫 SQL;
* 序列經 ``karst.runs.RunStore`` 讀回,指標經 ``karst.metrics`` 算,
  本檔一個數字都不自己算;
* 頁面上一個寫死的數字都沒有:這裡拿不到的東西,前端就不顯示那一格
  (該策略的成績一律出「—」,不補假數據)。

端點只有一個:``GET /api/overview``——總覽一次過要的全部東西。分成幾個
端點的話,前端要等幾轉才畫得出第一行;這一頁本來就是一次過畫完的。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from karst.errors import NotFound
from karst.metrics import benchmark_curve, run_metrics
from karst.runs import BASE, window_stats
from karst.store import FORMAL_RUN, rebalance_cadences

# 數值的出口口徑(NaN／inf 當缺值、比率轉百分點、日期一律 ISO)只有一份,
# 住在 karst.web.data;這裡照用,不另抄一套——兩套口徑遲早會各走各路。
from karst.web.data import _day, _f, _pct

# 策略總覽八類。取值那一面是 schema.py 的 CHECK 約束(單一正本),中文名
# 這一面照原型第十版 prototype/assets/data-ext.js 逐字搬過來。
STRATEGY_TYPE_NAMES: dict[str, str] = {
    "fundamental": "基本面選股",
    "technical": "技術趨勢",
    "multifactor": "多因子",
    "event": "事件驅動",
    "meanrev": "均值回歸",
    "follow": "組合跟隨",
    "macro": "宏觀配置",
    "options": "期權策略",
}

# 迷你走勢只有 92px 闊,一千幾百點畫出來是同一條線,但 JSON 會脹幾十倍。
# 均勻抽 120 點,頭尾兩點必取——線的起點與終點正是用戶在看那兩個數。
SPARK_POINTS = 120

# 表上「對基準」那一欄比的是它。QQQ 是原型定下的主基準,SPY 只在詳情卡列數。
PRIMARY_BENCHMARK = "QQQ"

# 總覽只算**正式運行**(示例運行、用戶自行重跑);參數掃描一格一次運行,庫內
# 動輒幾千個,一律不計亦不列——掃描在參數掃描頁以「一次掃描一行」呈現。
#
# 判準:**庫身那一格**(backtest_run.origin,KARST-054)。以前這裡靠參數集名的
# 前綴猜,前綴一改掃描格就會扮成一套策略的門面成績,而且錯得無聲(假設 A-006)。
# 現在來歷由落庫那一刻寫死,問庫要就有答案,這一層一個字都不用猜。

_STATIC_ROOT = Path(__file__).resolve().parent / "static"

# 導航列四頁未建成的那幾頁,一律出這一頁:佔位空狀態,不是死連結。
PENDING_PAGE = "pending.html"


def _page(filename: str) -> str:
    """那一頁建成了就出它自己,未建成就出佔位空狀態。

    導航列四頁的關係要一開始就看得見,但四頁不是同一日建成的。這裡按檔在不在
    決定出哪一頁,好過在一張表上寫死「這頁未建」——寫死那張表會過時,而過時的
    後果是頁明明已經建成,導航列仍然帶用戶去一版佔位。
    """
    return filename if (_STATIC_ROOT / filename).is_file() else PENDING_PAGE


# 網址 → static/ 下的檔名。根路徑自 KARST-049 起指向策略總覽,原本住在根
# 路徑的運行詳情頁搬去 /run(頁本身一個字沒有改)。
PAGES: dict[str, str] = {
    "/": "overview.html",
    "/index.html": "overview.html",
    "/run": "index.html",
    "/strategy": _page("strategy.html"),  # KARST-050
    "/sweep": _page("sweep.html"),  # KARST-051
}


def _no_run_note(sweep_runs: int) -> str:
    """一套策略在總覽上是空的,講得出為什麼——空一格而不講,用戶會以為壞了。"""
    if sweep_runs:
        return (
            f"這套策略至今只跑過參數掃描({sweep_runs} 格),未有正式運行。"
            "掃描結果請看參數掃描頁。"
        )
    return "這套策略未跑過任何一次運行。"


def _sample_positions(total: int, count: int = SPARK_POINTS) -> list[int]:
    """在 ``total`` 個點之中均勻抽 ``count`` 個位置,頭尾必取。"""
    if total <= 0:
        return []
    if total <= count or count < 2:
        return list(range(total))
    return [round(i * (total - 1) / (count - 1)) for i in range(count)]


class OverviewReader:
    """庫內全部策略,連同各自最新一次運行的成績。

    一次讀出來之後就記住:這一頁是一部唯讀檢視器,而讀全庫四千個運行登記
    要兩秒,每次開頁都重讀一次是白等。庫有新運行時重開伺服器即可。
    """

    def __init__(self, reader: Any) -> None:
        self._reader = reader
        self._cache: dict[str, Any] | None = None
        self._bench_cache: dict[tuple[str, str, str, str], Any] = {}

    def overview(self) -> dict[str, Any]:
        if self._cache is None:
            self._cache = self._build()
        return self._cache

    # ---------------- 砌 payload ----------------

    def _build(self) -> dict[str, Any]:
        reader = self._reader
        store = reader.store

        records = store.list_runs()  # 由早到遲
        formal: list[Any] = []
        sweep_count = 0
        by_strategy: dict[str, list[Any]] = {}
        swept: dict[str, int] = {}
        for record in records:
            if record.origin != FORMAL_RUN:
                # 掃描格不入總覽,只記一個數,好讓「為什麼這套策略是空的」講得出
                sweep_count += 1
                swept[record.strategy_name] = swept.get(record.strategy_name, 0) + 1
                continue
            formal.append(record)
            by_strategy.setdefault(record.strategy_name, []).append(record)

        rows: list[dict[str, Any]] = []
        for index, name in enumerate(store.list_strategy_names(), start=1):
            rows.append(
                self._strategy_row(
                    index, name, by_strategy.get(name, []), swept.get(name, 0)
                )
            )

        newest = formal[-1] if formal else None
        return {
            "strategyTypes": [
                {"id": key, "name": label} for key, label in STRATEGY_TYPE_NAMES.items()
            ],
            "strategies": rows,
            "primaryBenchmark": PRIMARY_BENCHMARK,
            "meta": {
                "strategyCount": len(rows),
                # 正式運行數。掃描格另計,總覽一格都不列。
                "runCount": len(formal),
                "sweepRunCount": sweep_count,
                "snapshot": newest.snapshot_id if newest else None,
                "asOf": newest.period_end if newest else None,
                "periodFrom": newest.period_start if newest else None,
                "periodTo": newest.period_end if newest else None,
            },
        }

    def _pick_run(self, name: str, runs: list[Any]):
        """代表這套策略的那一次運行。

        有現役設定(用戶指定紙上交易跟隨哪一個參數集)就用它那一組的最新一次
        ——門面數字不應該被一次參數掃描的最後一格頂走。未指定就用最新一次,
        不猜「哪一格最靚」:總覽報的是最近跑出什麼,不是最好跑出什麼。
        """
        if not runs:
            return None, False
        try:
            active = self._reader.store.get_active_setup(name)
        except NotFound:
            active = None
        if active is not None:
            matched = [
                r
                for r in runs
                if r.param_set_id == active.param_set_id
                and r.strategy_version_id == active.strategy_version_id
            ]
            if matched:
                return matched[-1], True
        return runs[-1], False

    def _strategy_row(
        self, index: int, name: str, runs: list[Any], sweep_runs: int = 0
    ) -> dict[str, Any]:
        store = self._reader.store
        record, is_active = self._pick_run(name, runs)

        if record is not None:
            strategy_type = record.strategy_type
            version_no = record.strategy_version_no
        else:
            # 未跑過的策略照樣要在表上見到,否則用戶會以為它不見了
            version = store.get_strategy_version(name)
            strategy_type = version.strategy_type
            version_no = version.version_no

        row: dict[str, Any] = {
            "id": f"s{index}",
            "name": name,
            "type": strategy_type,
            "typeName": STRATEGY_TYPE_NAMES.get(strategy_type, strategy_type),
            "versionLabel": f"v{version_no}",
            "runCount": len(runs),
            "sweepRunCount": sweep_runs,
            "runId": None,
            "paramSummary": None,
            "lastRunAt": None,
            "periodStart": None,
            "periodEnd": None,
            "snapshotId": None,
            "isActiveSetup": is_active,
            "isStale": False,
            "metrics": None,
            "benchmarks": {},
            "equity": [],
            "benchEquity": [],
            "note": None if record is not None else _no_run_note(sweep_runs),
        }
        if record is None:
            return row

        cadence = rebalance_cadences().get(
            record.rebalance_cadence, record.rebalance_cadence
        )
        reasons = self._reader.runs.stale_reasons(record.run_id)
        row.update(
            {
                "runId": record.run_id,
                "paramSummary": (
                    f"{record.param_set_name} v{record.param_set_version_no}・{cadence}"
                ),
                "lastRunAt": _day(record.created_at),
                "periodStart": record.period_start,
                "periodEnd": record.period_end,
                "snapshotId": record.snapshot_id,
                "isStale": bool(reasons),
                "staleReasons": list(reasons),
            }
        )

        try:
            self._fill_results(row, record)
        except Exception as exc:  # noqa: BLE001
            # 一次運行的序列讀不回(檔搬走了、快照缺基準),只影響這一行:
            # 照實講這一行為什麼是空,不要整頁塌下來。
            row["note"] = f"讀不到這次運行的結果:{type(exc).__name__}：{exc}"
        return row

    def _fill_results(self, row: dict[str, Any], record: Any) -> None:
        reader = self._reader
        equity = reader.runs.equity_curve(record.run_id)
        stats = window_stats(equity, None, None, base=BASE)
        series = stats.equity

        metrics = run_metrics(
            reader.runs,
            record.run_id,
            risk_free_rate=reader.risk_free_rate,
            benchmarks=reader.benchmarks,
            snapshot_root=reader.snapshot_root,
        )

        primary = metrics.benchmarks.get(PRIMARY_BENCHMARK)
        row["metrics"] = {
            "totalReturnPct": _pct(metrics.total_return),
            "annualReturnPct": _pct(metrics.annual_return),
            "maxDrawdownPct": _pct(metrics.max_drawdown),
            "winRatePct": _pct(metrics.win_rate),
            "profitLossRatio": _f(metrics.profit_loss_ratio),
            "closedTrades": metrics.closed_trades,
            "tradingDays": metrics.trading_days,
            # 對基準:累計超額(百分點)。表上「對基準」那一欄就是它。
            "vsBenchPp": _pct(primary.excess_total_return) if primary else None,
            "annualExcessPp": _pct(primary.annual_excess) if primary else None,
        }
        row["benchmarks"] = {
            ticker: {
                "totalReturnPct": _pct(cmp.total_return),
                "annualReturnPct": _pct(cmp.annual_return),
                "maxDrawdownPct": _pct(cmp.max_drawdown),
            }
            for ticker, cmp in metrics.benchmarks.items()
        }

        positions = _sample_positions(len(series))
        row["equity"] = [_f(series.iloc[i]) for i in positions]
        row["benchEquity"] = self._bench_points(record, stats, series, positions)

    def _bench_points(
        self, record: Any, stats: Any, series: Any, positions: list[int]
    ) -> list[float | None]:
        """主基準在同一段、同一批日子上的線,與策略同基期 100。

        基準走自己的交易日,所以先貼到策略那條時間軸上再抽點——兩條線的第 i
        點必須是同一日,否則迷你圖上兩條線會對不上。
        """
        key = (record.snapshot_id, PRIMARY_BENCHMARK, stats.start, stats.end)
        if key not in self._bench_cache:
            try:
                curve = benchmark_curve(
                    self._reader.store,
                    record.snapshot_id,
                    PRIMARY_BENCHMARK,
                    stats.start,
                    stats.end,
                    root=self._reader.snapshot_root,
                    base=stats.base,
                )
                self._bench_cache[key] = curve.equity
            except (NotFound, KeyError):
                # 該快照的名單沒有這隻基準:那條虛線就不畫,不補假數據
                self._bench_cache[key] = None
        curve_equity = self._bench_cache[key]
        if curve_equity is None:
            return []
        aligned = curve_equity.reindex(series.index).ffill().bfill()
        return [_f(aligned.iloc[i]) for i in positions]


def register(
    routes: dict[str, Callable[[Any, dict[str, list[str]]], Any]], reader: Any
) -> None:
    """把策略總覽的端點掛上網頁殼的路由表(server.py 只加這一句)。"""
    overview = OverviewReader(reader)
    routes["/api/overview"] = lambda handler, query: overview.overview()
