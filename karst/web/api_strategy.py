"""KARST-050 策略詳情頁的薄 REST 層。

本檔**只讀不寫**,而且與 ``karst.web.data`` 同一條紀律:庫一律經
``karst.store.DefinitionStore`` 讀(D-027),序列經 ``karst.runs.RunStore``
讀回,快照經 ``karst.data.snapshots`` 讀回;自己不碰 sqlite、不碰 parquet
格式,亦不產生任何數值——所有數字都是上面那幾層算出來的。

端點全部掛在 ``/api/strategy`` 之下(查詢字串帶參數,不再拆路徑,
好讓 ``server.py`` 一行就註冊得完):

    /api/strategy?id=<策略編號>                  策略身份、版本沿革、因子、運行總數
    /api/strategy/runs?id=&sort=&dir=&limit=&offset=
                                                  歷次運行(可排序、逐頁,含年化/Sortino/回撤/勝率)
    /api/strategy/picks?run=&date=               某一日的選股快照、漏斗、因子敞口
    /api/strategy/holdings?run=                  一次運行整段期間的持股分布(D-037,KARST-080)

頭兩個亦收 ``?run=``:不帶 ``?id=`` 時由那一次運行反查它自己那套策略
(KARST-067),所以 ``/strategy?run=X`` 與 ``/strategy?id=<X 那套>&run=X``
顯示同一頁,不會出現頁頂身份與正在看的運行對不上。

淨值線、八項指標、成交標記**不在這裡**:那幾樣 ``/api/runs/<run_id>`` 早已
交得出,策略頁直接沿用同一個端點,兩頁不會各算一套。

選股快照與漏斗的數據來自**運行產物**:引擎每次運行把各決策日的候選名單各層
與逐股分數落成兩份 parquet(``candidates`` / ``factor_scores``),與逐日淨值
同一個目錄(KARST-056)。本檔只讀,不算——過了哪一關、幾多分、排第幾,
全部是引擎跑那一趟的副產品,不是這裡另算一套。

未有那兩份痕跡的運行(KARST-056 之前跑的,或者掃描格)照舊只畫得出範圍與
持倉兩層,並在 ``notes`` 講明原因:**拿不到的東西一格都不虛構**
(與 ``data.py`` 檔頭同一句)。
"""

from __future__ import annotations

import math
import re
from typing import Any, Callable
from weakref import WeakKeyDictionary

import pandas as pd

from karst.data.snapshots import read_price_frame, read_universe
from karst.engine.funnel import (
    GATE_STAGES,
    STAGE_HELD,
    STAGE_LABELS,
    STAGE_SCOPE,
    STAGE_SELECTED,
    STATUS_HELD,
    STATUS_OUT,
    STATUS_SELECTED,
    STATUS_WATCH,
    TRACE_STAGES,
)
from karst.errors import ContractViolation, NotFound
from karst.metrics import benchmark_curve, trade_stats
from karst.metrics.ratios import annual_volatility, sortino_ratio
from karst.runs import BASE, window_stats
from karst.store import FORMAL_RUN, SWEEP_RUN

# D-034 的判準(失敗運行)、因子身份與版本鏈的形狀,一份正本住 karst.web.data,
# 這裡照用,不另抄一套(KARST-080:factor_payload 原本這裡也有一份,現併走)。
# D-039「代表運行」的揀法(KARST-081)同一條規矩:與策略總覽共用
# ``pick_representative_run``,不各寫一份。
from karst.web.data import (
    FAILURE_JUDGE_BENCHMARKS,
    factor_payload,
    is_failed_run,
    pick_representative_run,
)

# 一頁歷次運行的預設條數。這張表自 KARST-054 起只列**正式運行**,四千個掃描格
# 由庫身篩走(D-029),所以現實中一頁綽綽有餘。閘照舊留住:每一行的年化/回撤/
# 勝率都要讀一次該運行的 parquet(實測約 15ms 一個),真的有一日跑出幾百次正式
# 運行,無閘就會等足一分鐘。照實回報總數,由頁面講明「共 N 次」。
DEFAULT_RUN_PAGE = 50
MAX_RUN_PAGE = 200

# 歷次運行表四個可排序的成績欄(D-037)。運行編號、版本欄不可排序。
_SORT_FIELDS = {"annualReturnPct", "sortinoRatio", "maxDrawdownPct", "winRatePct"}

# 策略型別的中文名。庫內 strategy_type 是 schema 的 CHECK 取值(英文),
# 畫面要中文;對不上就照原樣顯示,不猜。
TYPE_LABELS = {
    "fundamental": "基本面",
    "technical": "技術",
    "multifactor": "多因子",
    "event": "事件",
    "meanrev": "均值回歸",
    "follow": "跟隨",
    "macro": "宏觀",
    "options": "期權",
}

_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")

# 每個讀取層一份快取。庫是唯讀連線開的,同一個問題答案不會中途變,
# 而 store.list_runs() 要為 3547 個運行逐個砌 RunRecord(實測約 1 秒),
# 每次揀日子都重來一次就太慢。
_CACHES: "WeakKeyDictionary[Any, dict[str, Any]]" = WeakKeyDictionary()


def _cache(reader: Any) -> dict[str, Any]:
    bag = _CACHES.get(reader)
    if bag is None:
        bag = {
            "runs": {},
            "sweepCells": {},
            "universe": {},
            "prices": {},
            "selection": {},
            "strategies": None,
        }
        _CACHES[reader] = bag
    return bag


# ---------------- 出得去的數 ----------------


def _f(value: Any) -> float | None:
    """轉成 JSON 出得去的數:NaN／inf 一律當缺值,不讓它們流到畫面。"""
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def _pct(value: Any) -> float | None:
    """比率轉百分點。0.1138 -> 11.38"""
    out = _f(value)
    return None if out is None else out * 100.0


def _day(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value[:10]
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _one(query: dict[str, list[str]], name: str) -> str | None:
    values = query.get(name) or []
    raw = (values[0] if values else "").strip()
    return raw or None


def _int(query: dict[str, list[str]], name: str, default: int) -> int:
    raw = _one(query, name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ContractViolation(f"{name} 要一個整數,收到 {raw!r}") from None


def _wants_all(query: dict[str, list[str]]) -> bool:
    """網址 ``?all=1`` 要完整名單(連失敗運行一併給),否則預設篩走(D-034)。"""
    raw = _one(query, "all")
    return raw not in (None, "", "0", "false")


# ---------------- 策略身份 ----------------


def _strategies(reader: Any) -> list[Any]:
    """庫內每套策略的最新版本。名字是唯一鍵(schema 的 UNIQUE)。"""
    bag = _cache(reader)
    if bag["strategies"] is None:
        bag["strategies"] = [
            reader.store.get_strategy_version(name)
            for name in reader.store.list_strategy_names()
        ]
    return bag["strategies"]


def _runs_of(reader: Any, name: str) -> list[Any]:
    """該策略的**正式運行**,新的在前(庫內登記由早到遲)。

    只列正式運行,與運行清單、策略總覽同一個口徑(D-029:一次掃描當一件事,
    掃描格不入運行清單)。來歷問庫身那一格(backtest_run.origin,KARST-054),
    不再靠參數集名的前綴猜——所以四千個掃描格由庫身篩走,一格都不用砌出來。

    **序列缺失運行一併篩走**(KARST-057):逐日序列不在磁碟上的運行,
    登記照舊在案,但這張表逐行都要讀一次 parquet 算年化/回撤/勝率,讀不到就
    整頁 404。與運行清單、掃描清單同一條規矩:登記留住,清單不列。
    """
    bag = _cache(reader)
    if name not in bag["runs"]:
        every = reversed(reader.store.list_runs(name, origin=FORMAL_RUN))
        bag["runs"][name] = [r for r in every if not reader.series_missing(r)]
    return bag["runs"][name]


def _sweep_cells_of(reader: Any, name: str) -> int:
    """該策略有幾多格掃描格運行。

    一套策略只跑過掃描時,歷次運行表是空的——空一格而不講,用戶會以為壞了。
    這個數就是那句「掃描結果見參數掃描頁」講得出多少格的憑據。
    """
    bag = _cache(reader)
    if name not in bag["sweepCells"]:
        bag["sweepCells"][name] = int(reader.store.count_runs(name, origin=SWEEP_RUN))
    return bag["sweepCells"][name]


def _resolve(reader: Any, wanted: str | None, run_id: str | None) -> Any:
    """把 ?id= 解成一套策略。收策略編號,亦收策略名(總覽頁連過來時兩者皆可)。

    **不帶 id 而帶 ?run= 時,由那一次運行反查它自己那套策略**(KARST-067)。
    以前這一格退回「最近有運行的那一套」,於是 ``/strategy?run=<因子混合那次>``
    的上半部會掛住趨勢波段的身份與歷次運行——正在看的運行與頁頂那個名對不上,
    而且錯得無聲(KARST-056 順帶發現)。運行編號本身已經指得回一套策略,問它
    就有答案,不必猜。

    兩者都沒有:揀最近有運行的那一套——直接開 /strategy 也有東西看得到。
    """
    versions = _strategies(reader)
    if not versions:
        raise NotFound("定義庫內未有任何策略")

    if not wanted and run_id:
        # 查無此運行即 404(``get_run`` 自己拋),不會靜靜退回預設那一套:
        # 網址指名了一次運行,答不出就要講答不出。
        wanted = reader.runs.get_run(run_id).strategy_name

    if wanted:
        for version in versions:
            if str(version.strategy_id) == wanted or version.name == wanted:
                return version
        raise NotFound(f"定義庫內沒有這一套策略:{wanted}")

    newest, newest_at = versions[0], ""
    for version in versions:
        runs = _runs_of(reader, version.name)
        at = runs[0].created_at if runs else ""
        if at > newest_at:
            newest, newest_at = version, at
    return newest


def _run_perf(reader: Any, record: Any) -> tuple[float | None, bool | None]:
    """該次運行的年化回報,連是不是失敗運行(D-034)——``pick_representative_run``
    揀代表運行要用,不算三個顯示用的數字(那是 ``_row_metrics`` 的事)。
    """
    try:
        equity = reader.runs.equity_curve(record.run_id)
    except Exception:  # noqa: BLE001
        return None, None
    stats = window_stats(equity, None, None, base=BASE)
    bench = _bench_annual_returns(reader, record.snapshot_id, stats.start, stats.end)
    return stats.annual_return, is_failed_run(stats.annual_return, bench)


def _default_run_id(reader: Any, active: Any | None, runs: list[Any]) -> str | None:
    """D-039:門面預設帶去看的那一次運行——與策略總覽共用同一個挑選函數
    (``karst.web.data.pick_representative_run``),不各寫一份。

    有現役設定就優先在那一組裡面揀,組內／全庫都揀年化回報最高的非失敗運行。
    全部都是失敗運行(真有這個情況,例如目前庫內的趨勢波段)就退回登記時間
    最新那一次——照樣有東西可看,不留一個空白給用戶。
    """
    record, _, _ = pick_representative_run(active, runs, lambda r: _run_perf(reader, r))
    return record.run_id if record is not None else None


def overview(reader: Any, query: dict[str, list[str]]) -> dict[str, Any]:
    """策略身份、版本沿革、因子、運行總數,以及預設檢視哪一次運行。"""
    strategy = _resolve(reader, _one(query, "id"), _one(query, "run"))
    runs = _runs_of(reader, strategy.name)

    # 版本沿革:每一版之下跑過幾次,由運行清單自己數
    counts: dict[int, int] = {}
    for record in runs:
        counts[record.strategy_version_no] = counts.get(record.strategy_version_no, 0) + 1
    try:
        chain = reader.store.strategy_version_chain(strategy.name)
    except NotFound:
        chain = [strategy]
    latest_no = max((item.version_no for item in chain), default=strategy.version_no)

    # 現役設定:庫內未指定就是 None——不猜、不頂替(data.py 同一條規矩)
    try:
        active = reader.store.get_active_setup(strategy.name)
    except NotFound:
        active = None

    return {
        "strategy": {
            "id": strategy.strategy_id,
            "name": strategy.name,
            "type": strategy.strategy_type,
            "typeLabel": TYPE_LABELS.get(strategy.strategy_type, strategy.strategy_type),
            "versionNo": strategy.version_no,
            "description": strategy.description,
            "createdAt": strategy.created_at,
        },
        "activeSetup": None
        if active is None
        else {
            "strategyVersionNo": active.strategy_version_no,
            "paramSetName": active.param_set_name,
            "paramSetVersionNo": active.param_set_version_no,
            "designatedAt": active.designated_at,
            "note": active.note,
        },
        "runTotal": len(runs),
        # 只有掃描格、未有正式運行的策略,頁面要講得出「幾多格、去哪裡看」
        "sweepCellTotal": _sweep_cells_of(reader, strategy.name),
        # D-039:預設帶去看的那一次運行,與策略總覽同一個挑選函數——有現役
        # 設定用現役,否則用年化回報最高的非失敗運行。全部運行都失敗(真有
        # 這個情況,例如趨勢波段)就退回登記時間最新那一次,好過帶去一個空白。
        "defaultRunId": _default_run_id(reader, active, runs),
        "versions": [
            {
                "versionNo": item.version_no,
                "description": item.description,
                "createdAt": item.created_at,
                "runCount": counts.get(item.version_no, 0),
                "isLatest": item.version_no == latest_no,
            }
            for item in sorted(chain, key=lambda v: v.version_no, reverse=True)
        ],
        "factors": [factor_payload(reader, f, True) for f in strategy.factors],
    }


# ---------------- 歷次運行 ----------------


def _bench_annual_returns(
    reader: Any, snapshot_id: str, start: str, end: str
) -> dict[str, float | None]:
    """該快照、該段期間,SPY 與 QQQ 買入持有的年化回報——D-034 判失敗運行要用。

    只讀這兩隻(``FAILURE_JUDGE_BENCHMARKS``),不是 ``reader.benchmarks``
    整組:判準本身寫死是這兩隻,與頁面設定了顯示哪幾條基準線無關。
    按(快照、代號、起、迄)快取:同一套策略的歷次運行往往共用同一個快照與
    同一段期間,不必每行各讀一次基準價格。
    """
    bag = _cache(reader)
    cache = bag.setdefault("benchAnnual", {})
    out: dict[str, float | None] = {}
    for ticker in FAILURE_JUDGE_BENCHMARKS:
        key = (snapshot_id, ticker, start, end)
        if key not in cache:
            try:
                curve = benchmark_curve(
                    reader.store, snapshot_id, ticker, start, end, root=reader.snapshot_root
                )
                cache[key] = curve.stats.annual_return
            except (NotFound, KeyError):
                cache[key] = None
        out[ticker] = cache[key]
    return out


def _row_metrics(reader: Any, record: Any) -> dict[str, Any]:
    """一行運行要顯示的幾個數,連 D-034 的失敗運行判定。

    只讀該次運行自己的兩條序列(淨值、成交)算前幾項,不叫 ``run_metrics``——
    後者連基準曲線一併算(要讀整份快照價格),一頁五十行就慢十倍。
    年化與最大回撤照 ``window_stats`` 的全期口徑,勝率照 ``trade_stats``,
    與運行詳情頁同一套算法。判失敗運行另外只讀 SPY／QQQ 兩條基準的年化,
    比 ``run_metrics`` 省一大截。
    """
    run_id = record.run_id
    equity = reader.runs.equity_curve(run_id)
    stats = window_stats(equity, None, None, base=BASE)
    trades = trade_stats(reader.runs.orders(run_id), equity.index)
    bench = _bench_annual_returns(reader, record.snapshot_id, stats.start, stats.end)
    sortino = sortino_ratio(
        stats.equity, annual_return=stats.annual_return, risk_free_rate=reader.risk_free_rate
    )
    return {
        "totalReturnPct": _pct(stats.total_return),
        "annualReturnPct": _pct(stats.annual_return),
        "sortinoRatio": _f(sortino),
        "maxDrawdownPct": _pct(stats.max_drawdown),
        "winRatePct": _pct(trades.win_rate),
        "profitLossRatio": _f(trades.profit_loss_ratio),
        "closedTrades": trades.closed_trades,
        "tradingDays": stats.trading_days,
        "isFailed": bool(is_failed_run(stats.annual_return, bench)),
    }


def runs(reader: Any, query: dict[str, list[str]]) -> dict[str, Any]:
    """該策略的歷次運行(只列正式運行),新的在前,逐頁交。

    自 KARST-054 起這張表只有正式運行,一套策略通常得幾次,所以逐頁那一套實際上
    再用不著;``limit`` / ``offset`` 照舊收,因為端點的形狀是對外的約定,而且庫內
    真的有一日出現幾百次正式運行時,它仍然是那道閘。

    ``?run=`` 與 ``/api/strategy`` 一樣收:不帶 ``?id=`` 時由那一次運行反查它
    自己那套策略(KARST-067),免得頁頂身份與下面那張表各自指住兩套策略。

    D-034(經 D-040 定案):失敗運行(年化同時輸給 SPY 與 QQQ)預設不列,
    亦不設展開行、不另外顯示計數在畫面——``failedCount`` 這個數只供頁面在
    「此策略運行全部失敗」那種空表狀態講一句「N 條運行全部失敗」,不是用來
    畫一條可以展開的行(D-035 起檢視運行選擇器已經拆走,策略詳情頁只剩歷次
    運行表這一個進入運行的入口)。``?all=1`` 要完整名單(供核對用,連失敗運行
    都在)。``offset``/``limit`` 照篩選之後那張表算,翻頁翻的是「看得見」
    那幾條,不是庫內原始那幾條。
    """
    strategy = _resolve(reader, _one(query, "id"), _one(query, "run"))
    every = _runs_of(reader, strategy.name)

    items_all = []
    for record in every:
        reasons = reader.runs.stale_reasons(record.run_id)
        item = {
            "runId": record.run_id,
            "strategyName": record.strategy_name,
            "strategyVersionNo": record.strategy_version_no,
            "paramSetName": record.param_set_name,
            "paramSetVersionNo": record.param_set_version_no,
            "rebalanceCadence": record.rebalance_cadence,
            "paramValues": dict(record.param_values),
            "periodStart": record.period_start,
            "periodEnd": record.period_end,
            "snapshotId": record.snapshot_id,
            "createdAt": record.created_at,
            "isStale": bool(reasons),
            "staleReasons": list(reasons),
        }
        item.update(_row_metrics(reader, record))
        items_all.append(item)

    failed_count = sum(1 for item in items_all if item["isFailed"])
    visible = items_all if _wants_all(query) else [i for i in items_all if not i["isFailed"]]

    # 四個成績欄可點欄頭升降排序,預設按年化由高至低(D-037)。排序要在
    # 分頁之前做——不然「前 50」揀出來的不是真正排名最高那 50 條。
    sort_key = _one(query, "sort") or "annualReturnPct"
    if sort_key not in _SORT_FIELDS:
        raise ContractViolation(
            f"歷次運行表只認得 {sorted(_SORT_FIELDS)} 這幾個排序欄,收到 {sort_key!r}"
        )
    descending = (_one(query, "dir") or "desc") != "asc"
    # None(算不出,例如未曾平倉的 Sortino)一律排到榜尾,不管升降序
    visible = sorted(
        visible,
        key=lambda item: (item[sort_key] is None, item[sort_key] if item[sort_key] is not None else 0.0),
        reverse=descending,
    )
    if descending:
        # reverse=True 連 None 那組(True > False)也一併倒轉,推到榜首——
        # 再排一次,只把「有值」那段倒轉,「無值」那段留在榜尾。
        with_value = [i for i in visible if i[sort_key] is not None]
        without_value = [i for i in visible if i[sort_key] is None]
        visible = with_value + without_value

    offset = max(0, _int(query, "offset", 0))
    limit = _int(query, "limit", DEFAULT_RUN_PAGE)
    if limit <= 0 or limit > MAX_RUN_PAGE:
        limit = MAX_RUN_PAGE
    page = visible[offset : offset + limit]

    return {
        "strategyId": strategy.strategy_id,
        "strategyName": strategy.name,
        "total": len(every),
        # D-034(經 D-040 定案):預設篩走的失敗運行有幾多條——不設展開行,
        # 只供「此策略運行全部失敗」那種空表狀態講一句「N 條運行全部失敗」。
        "failedCount": failed_count,
        # 空表要講得出「不是壞了,是這套策略只跑過掃描」——連幾多格一齊交
        "sweepCellTotal": _sweep_cells_of(reader, strategy.name),
        "sort": sort_key,
        "dir": "asc" if not descending else "desc",
        "offset": offset,
        "shown": len(page),
        "items": page,
    }


# ---------------- 檢視視窗的額外一格 ----------------


def window(reader: Any, query: dict[str, list[str]]) -> dict[str, Any]:
    """策略詳情頁頭條數字比 D-020 八項多出的那一格:波幅。

    D-020 那八項由 ``/api/runs/<run_id>`` 交(兩頁同一個口徑,不重算);
    波幅只有這一頁用得著,所以住在這裡。算法照 ``karst.metrics.ratios``,
    本檔一樣不自己算數。
    """
    run_id = _one(query, "run")
    if not run_id:
        raise ContractViolation("要算哪一次運行的波幅:請帶 ?run=")
    for name in ("start", "end"):
        raw = _one(query, name)
        if raw is not None and not _DAY.fullmatch(raw):
            raise ContractViolation(f"檢視視窗的 {name} 要一個 YYYY-MM-DD 的日子,收到 {raw!r}")

    equity = reader.runs.equity_curve(run_id)
    stats = window_stats(equity, _one(query, "start"), _one(query, "end"), base=BASE)
    return {
        "runId": run_id,
        "start": stats.start,
        "end": stats.end,
        "tradingDays": stats.trading_days,
        "annualVolatilityPct": _pct(annual_volatility(stats.equity)),
    }


# ---------------- 選股快照、漏斗、因子敞口 ----------------


def _universe(reader: Any, snapshot_id: str) -> list[dict[str, Any]]:
    bag = _cache(reader)
    if snapshot_id not in bag["universe"]:
        frame = read_universe(reader.store, snapshot_id, root=reader.snapshot_root)
        bag["universe"][snapshot_id] = [
            {
                "entityId": int(row.entity_id),
                "symbol": str(row.ticker),
                "name": str(row.display_name),
                "kind": str(row.entity_kind),
            }
            for row in frame.itertuples()
        ]
    return bag["universe"][snapshot_id]


def _closes(reader: Any, snapshot_id: str, day: str) -> dict[int, float]:
    """該快照某一日的收市價。停牌／未上市那日照 D-026 留空,不補價。"""
    bag = _cache(reader)
    if snapshot_id not in bag["prices"]:
        frame = read_price_frame(reader.store, snapshot_id, root=reader.snapshot_root)
        table = frame[["entity_id", "date", "close"]].copy()
        table["date"] = table["date"].map(_day)
        bag["prices"][snapshot_id] = table
    table = bag["prices"][snapshot_id]
    rows = table.loc[table["date"] == day]
    out: dict[int, float] = {}
    for row in rows.itertuples():
        price = _f(row.close)
        if price is not None:
            out[int(row.entity_id)] = price
    return out


def _factor_for(symbol: str, factors: Any) -> Any:
    """哪一個因子由這隻可投資對象承載。

    因子名寫成「族·定義(代號)」(例:質素·MSCI USA Sector Neutral Quality(QUAL)),
    所以括號內那個代號就是承載它的 ETF。對不上就回 None——**寧可不標,
    不猜一個出來**。
    """
    tag = "(" + symbol.upper() + ")"
    for factor in factors:
        if tag in (factor.name or "").upper():
            return factor
    return None


# 各層那句提示。「當日過關,或早前過關後仍在場」不是修辭:漏斗的語意是
# 「到達該層」,而一隻早兩個月入場、今日仍在手的股票**已經到達過**每一層,
# 所以它照計。少了這一句,持倉那一層就會比技術關還要闊,漏斗看落像壞了。
_STAGE_HINTS = {
    STAGE_SCOPE: "該策略在這一日看得見的全部標的(已扣除基準)",
    "fundamental": "選股漏斗第一層(D-013):非結構化量化/基本面篩選;當日過關,或早前過關後仍在場",
    "technical": "選股漏斗第二層(D-013):技術量化篩選;當日過關,或早前過關後仍在場",
    "pattern": "選股漏斗第三層(D-013):圖形;當日過關,或早前過關後仍在場",
    "theory": "選股漏斗第四層(D-013):技術分析理論;當日過關,或早前過關後仍在場",
    STAGE_SELECTED: "決策日揀中要落注的名單;早前揀中而仍在場的一併計入",
    STAGE_HELD: "扣除倉位上限與風控後,該日收工時實際持有",
}

# 表由窄到闊排:手上有的擺最前,未過關的墊底。
_STATUS_ORDER = {STATUS_HELD: 0, STATUS_SELECTED: 1, STATUS_WATCH: 2, STATUS_OUT: 3}


def _selection(reader: Any, run_id: str) -> dict[str, Any] | None:
    """讀回這次運行的選股痕跡,整理成「決策日 → 各層名單 / 逐股分數」。

    舊運行(或者掃描格)一張痕跡都沒有,回 ``None``——畫面照舊只畫得出的那
    兩層,不虛構。整份讀回來一次就快取住:趨勢波段一次運行有近三千個決策日,
    每次揀日子都重讀 parquet 就等到人不耐煩。
    """
    bag = _cache(reader)
    if run_id in bag["selection"]:
        return bag["selection"][run_id]

    try:
        kinds = reader.runs.selection_kinds(run_id)
    except (NotFound, ContractViolation):
        kinds = ()
    if not kinds:
        bag["selection"][run_id] = None
        return None

    by_date: dict[str, dict[str, set[int]]] = {}
    stages: list[str] = []
    if "candidates" in kinds:
        frame = reader.runs.candidates(run_id)
        present = set(frame["stage"])
        stages = [stage for stage in TRACE_STAGES if stage in present]
        for row in frame.itertuples():
            day = _day(row.decision_date)
            by_date.setdefault(day, {}).setdefault(str(row.stage), set()).add(
                int(row.entity_id)
            )

    scores: dict[str, dict[int, dict[str, dict[str, Any]]]] = {}
    score_names: list[str] = []
    if "factor_scores" in kinds:
        frame = reader.runs.factor_scores(run_id)
        score_names = sorted(set(str(name) for name in frame["score_name"]))
        for row in frame.itertuples():
            day = _day(row.decision_date)
            scores.setdefault(day, {}).setdefault(int(row.entity_id), {})[
                str(row.score_name)
            ] = {"value": _f(row.score), "rank": int(row.rank)}

    days = sorted(set(by_date) | set(scores))
    bag["selection"][run_id] = {
        "stages": tuple(stages),
        "byDate": by_date,
        "scores": scores,
        "days": days,
        "scoreNames": tuple(score_names),
    }
    return bag["selection"][run_id]


def _decision_day(trace: dict[str, Any], day: str) -> str | None:
    """畫面停在 ``day``,那一刻手上這個組合是哪一個決策日的產物。

    取 ``day`` 或之前**最近**那一個決策日——不會取之後那一個,取了就是偷看
    未來(D-021 知情時間)。
    """
    earlier = [d for d in trace["days"] if d <= day]
    return earlier[-1] if earlier else None


def picks(reader: Any, query: dict[str, list[str]]) -> dict[str, Any]:
    """某一次運行、某一日的選股快照:各層名單、逐股分數、持倉權重,連因子敞口。

    有選股痕跡的運行,漏斗按痕跡畫齊它真有的每一層,逐股分數逐隻寫出來
    (KARST-056);未有痕跡的舊運行照舊只畫範圍與持倉兩層,並在 ``notes``
    講明原因——**拿不到的東西一格都不虛構**。
    """
    run_id = _one(query, "run")
    if not run_id:
        raise ContractViolation("要看哪一次運行的選股快照:請帶 ?run=")

    record = reader.runs.get_run(run_id)
    equity = reader.runs.equity_curve(run_id)
    days = [_day(d) for d in equity.index]

    wanted = _one(query, "date")
    if wanted is not None and not _DAY.fullmatch(wanted):
        raise ContractViolation(f"快照時點要一個 YYYY-MM-DD 的日子,收到 {wanted!r}")
    if wanted is None:
        day = days[-1]
    elif wanted in days:
        day = wanted
    else:
        # 揀了一個不是交易日的日子:退到之前最近一個交易日,不猜一個未來的
        earlier = [d for d in days if d <= wanted]
        if not earlier:
            raise NotFound(f"運行 {run_id} 在 {wanted} 之前沒有交易日")
        day = earlier[-1]

    held = reader.runs.holdings_on(run_id, day)
    closes = _closes(reader, record.snapshot_id, day)
    equity_value = _f(equity.loc[pd.Timestamp(day)])

    # 選股痕跡:這一日的組合出自哪一個決策日,那一日各層揀了誰、逐股幾多分
    trace = _selection(reader, run_id)
    decision_day = None if trace is None else _decision_day(trace, day)
    stage_ids: dict[str, set[int]] = {}
    day_scores: dict[int, dict[str, dict[str, Any]]] = {}
    if trace is not None and decision_day is not None:
        stage_ids = {
            stage: set(ids) for stage, ids in trace["byDate"].get(decision_day, {}).items()
        }
        day_scores = trace["scores"].get(decision_day, {})

    held_ids = {int(entity) for entity, shares in held.items() if shares}
    # 「到達該層」:早前過關而今日仍在場的,一樣算到達過每一層(見 _STAGE_HINTS)
    reached = {
        stage: set(stage_ids.get(stage, set())) | held_ids
        for stage in (trace["stages"] if trace is not None else ())
        if stage != STAGE_SCOPE
    }
    gate_ids: set[int] = set()
    for stage in GATE_STAGES:
        gate_ids |= reached.get(stage, set())
    selected_ids = reached.get(STAGE_SELECTED, set())

    benchmarks = {t.upper() for t in reader.benchmarks}
    rows = []
    for item in _universe(reader, record.snapshot_id):
        # 基準(SPY／QQQ)在名單內,但它們不是這套策略揀得中的標的,
        # 不入「範圍」——否則漏斗第一層會多數兩隻永遠揀不到的東西
        if item["symbol"].upper() in benchmarks:
            continue
        shares = _f(held.get(item["entityId"]))
        price = closes.get(item["entityId"])
        value = None if (shares is None or price is None) else shares * price
        weight = (
            None
            if (value is None or not equity_value)
            else value / equity_value * 100.0
        )
        factor = _factor_for(item["symbol"], record.factors)
        entity_id = item["entityId"]
        is_held = shares is not None and shares > 0

        if trace is None:
            # 未有痕跡的舊運行:只講得出手上有沒有,講不出過了哪一關
            status = "持倉" if is_held else "未持倉"
            stages = [STAGE_SCOPE] + ([STAGE_HELD] if is_held else [])
        else:
            if is_held:
                status = STATUS_HELD
            elif entity_id in selected_ids:
                status = STATUS_SELECTED
            elif entity_id in gate_ids:
                status = STATUS_WATCH
            else:
                status = STATUS_OUT
            stages = [STAGE_SCOPE]
            stages += [s for s in trace["stages"] if s != STAGE_SCOPE and entity_id in reached.get(s, set())]
            if is_held:
                stages.append(STAGE_HELD)

        rows.append(
            {
                "entityId": entity_id,
                "symbol": item["symbol"],
                "name": item["name"],
                "kind": item["kind"],
                "family": None if factor is None else factor.family,
                "factorName": None if factor is None else factor.name,
                "factorVersionNo": None if factor is None else factor.version_no,
                "shares": shares,
                "price": price,
                "value": value,
                "weightPct": weight,
                "held": is_held,
                "status": status,
                "stages": stages,
                "scores": day_scores.get(entity_id, {}),
            }
        )

    primary = trace["scoreNames"][0] if (trace and trace["scoreNames"]) else None

    def _order(row: dict[str, Any]) -> tuple[Any, ...]:
        rank = None if primary is None else (row["scores"].get(primary) or {}).get("rank")
        return (
            _STATUS_ORDER.get(row["status"], 9),
            -(row["weightPct"] or 0.0),
            rank if rank is not None else 10**9,
            row["symbol"],
        )

    rows.sort(key=_order)

    scope = len(rows)
    holding = sum(1 for r in rows if r["held"])
    in_scope = {r["entityId"] for r in rows}

    # 因子敞口:每一格因子由哪一個對象承載、佔多少比重(詞彙表「因子敞口」)。
    # 這次運行引用到的因子全部列出,未持有的照實寫 0,好讓分布看得出空格。
    by_symbol = {r["symbol"].upper(): r for r in rows}
    exposure = []
    for factor in record.factors:
        carrier = None
        for symbol, row in by_symbol.items():
            if "(" + symbol + ")" in (factor.name or "").upper():
                carrier = row
                break
        # 承載不到任何對象的因子(例如趨勢波段那個 boolean 入場訊號)不入分布:
        # 它根本不是一格敞口,擺上去會讀成「這個因子的敞口是 0」。它在右邊的
        # 因子版本一欄仍然看得到。
        if carrier is None:
            continue
        exposure.append(
            {
                "family": factor.family,
                "factorName": factor.name,
                "versionNo": factor.version_no,
                "symbol": carrier["symbol"],
                "name": carrier["name"],
                "weightPct": carrier["weightPct"] or 0.0,
                "shares": carrier["shares"],
            }
        )
    exposure.sort(key=lambda e: -(e["weightPct"] or 0.0))

    # 承載不到任何因子、但實際持有的(例如技術策略買的股票):照樣入分布
    carried = {e["symbol"] for e in exposure if e["symbol"]}
    for row in rows:
        if row["held"] and row["symbol"] not in carried:
            exposure.append(
                {
                    "family": None,
                    "factorName": None,
                    "versionNo": None,
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "weightPct": row["weightPct"] or 0.0,
                    "shares": row["shares"],
                }
            )

    cash = None if equity_value is None else 100.0 - sum(
        (r["weightPct"] or 0.0) for r in rows if r["held"]
    )

    return {
        "runId": run_id,
        "date": day,
        "requestedDate": wanted,
        "snapshotId": record.snapshot_id,
        "firstDay": days[0],
        "lastDay": days[-1],
        "equity": equity_value,
        "cashWeightPct": cash,
        "decisionDate": decision_day,
        "scoreNames": list(trace["scoreNames"]) if trace else [],
        "funnel": _funnel(record, trace, scope, reached, in_scope, holding),
        "rows": rows,
        "exposure": exposure,
        "notes": {
            "scoresAvailable": bool(trace and trace["scoreNames"]),
            "why": ""
            if trace
            else "這一次運行未有留下選股痕跡(候選名單與逐股分數),"
            "所以中間各層與逐股分數欄位一格都不顯示;重跑一次即補得回。",
        },
    }


def _funnel(
    record: Any,
    trace: dict[str, Any] | None,
    scope: int,
    reached: dict[str, set[int]],
    in_scope: set[int],
    holding: int,
) -> list[dict[str, Any]]:
    """漏斗:由闊到窄,只畫**真有數據**的層。

    未有痕跡的運行照舊只得範圍與持倉兩層——一層都不虛構,亦不畫一格空的關口
    扮篩過。有痕跡就把它真有的每一層畫出來:一套策略只用一兩層是常態
    (D-013 明言),兩層畫兩格就是它的真相。
    """
    blocks = [
        {
            "key": STAGE_SCOPE,
            "label": STAGE_LABELS[STAGE_SCOPE],
            "hint": f"數據快照 {record.snapshot_id} 當日可交易的標的(已扣除基準)",
            "count": scope,
        }
    ]
    if trace is not None:
        for stage in trace["stages"]:
            if stage == STAGE_SCOPE:
                continue
            blocks.append(
                {
                    "key": stage,
                    "label": STAGE_LABELS[stage],
                    "hint": _STAGE_HINTS.get(stage, ""),
                    "count": len(reached.get(stage, set()) & in_scope),
                }
            )
    blocks.append(
        {
            "key": STAGE_HELD,
            "label": STAGE_LABELS[STAGE_HELD],
            "hint": _STAGE_HINTS[STAGE_HELD],
            "count": holding,
        }
    )
    return blocks


# ---------------- 持股分布(D-037,KARST-080) ----------------

# 「持股分布」前十名的排名基準:持有日數(該實體在 holdings 長表裡出現的
# 交易日數),不是平均權重——不必逐日回讀收市價、算法簡單直驗,詞彙表
# 「持股分布」條目已寫明用這個口徑。
HOLDINGS_RANK_BASIS = "holdingDays"


def holdings(reader: Any, query: dict[str, list[str]]) -> dict[str, Any]:
    """一次運行整段期間的持股彙總(D-037):最常持有的前十隻股票、
    各股在此運行的累計報酬,連行業佔比(現有資料沒有行業欄,見下)。

    直接讀 ``RunStore.holdings()``(逐日持倉長表)與 ``RunStore.orders()``
    (逐筆成交)現算,不另建快取表——與本檔其餘端點同一條紀律。

    排名:持有日數(``HOLDINGS_RANK_BASIS``)。累計報酬:該股票在此運行
    全部已平倉交易的合計損益(``karst.metrics.trades.trade_stats`` 逐筆
    FIFO 配對的 ``profit``,已扣手續費),除以該次運行的起始資金
    (``equity_curve`` 第一天的淨值,不是檢視視窗用的 ``BASE=100`` 那個
    顯示常數)。

    行業佔比:``karst.data.universe.UniverseMember`` 與快照的宇宙檔都沒有
    行業欄(核過 ``karst/data/universe.py`` 全檔),所以這裡只做前十股票與
    累計報酬,``sectorBreakdown`` 固定回 ``None`` 並在 ``notes`` 講明——
    這一截缺口已經在票上舉手,不是這裡漏做。
    """
    run_id = _one(query, "run")
    if not run_id:
        raise ContractViolation("要看哪一次運行的持股分布:請帶 ?run=")

    record = reader.runs.get_run(run_id)
    equity = reader.runs.equity_curve(run_id)
    if equity.empty:
        raise NotFound(f"運行 {run_id} 沒有淨值序列,算不出持股分布")
    starting_capital = _f(equity.iloc[0])

    held = reader.runs.holdings(run_id)
    top_holdings: list[dict[str, Any]] = []
    if not held.empty:
        by_days = held.groupby("entity_id").size().sort_values(ascending=False)

        trades = trade_stats(reader.runs.orders(run_id), equity.index)
        profit_by_id: dict[int, float] = {}
        for trip in trades.round_trips:
            profit_by_id[trip.entity_id] = profit_by_id.get(trip.entity_id, 0.0) + trip.profit

        universe_by_id = {row["entityId"]: row for row in _universe(reader, record.snapshot_id)}

        for entity_id, days in by_days.head(10).items():
            entity_id = int(entity_id)
            info = universe_by_id.get(entity_id)
            profit = profit_by_id.get(entity_id, 0.0)
            cum_return_pct = None if not starting_capital else profit / starting_capital * 100.0
            top_holdings.append(
                {
                    "entityId": entity_id,
                    "symbol": info["symbol"] if info else f"#{entity_id}",
                    "name": info["name"] if info else "",
                    "holdingDays": int(days),
                    "realizedProfit": _f(profit),
                    "cumulativeReturnPct": _f(cum_return_pct),
                }
            )

    return {
        "runId": run_id,
        "rankBasis": HOLDINGS_RANK_BASIS,
        "startingCapital": starting_capital,
        "topHoldings": top_holdings,
        "sectorBreakdown": None,
        "notes": {
            "sectorAvailable": False,
            "why": "現有實體登記冊／宇宙檔沒有行業欄,行業佔比未做"
            "(KARST-080 留言已舉手,見票)。",
        },
    }


# ---------------- 註冊 ----------------


def routes(reader: Any) -> dict[str, Callable[[Any, dict[str, list[str]]], Any]]:
    """交回本頁的端點表,由 ``server.py`` 一行併入它自己那張。"""
    return {
        "/api/strategy": lambda handler, query: overview(reader, query),
        "/api/strategy/runs": lambda handler, query: runs(reader, query),
        "/api/strategy/window": lambda handler, query: window(reader, query),
        "/api/strategy/picks": lambda handler, query: picks(reader, query),
        "/api/strategy/holdings": lambda handler, query: holdings(reader, query),
    }
