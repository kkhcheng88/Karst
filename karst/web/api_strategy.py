"""KARST-050 策略詳情頁的薄 REST 層。

本檔**只讀不寫**,而且與 ``karst.web.data`` 同一條紀律:庫一律經
``karst.store.DefinitionStore`` 讀(D-027),序列經 ``karst.runs.RunStore``
讀回,快照經 ``karst.data.snapshots`` 讀回;自己不碰 sqlite、不碰 parquet
格式,亦不產生任何數值——所有數字都是上面那幾層算出來的。

端點三個,全部掛在 ``/api/strategy`` 之下(查詢字串帶參數,不再拆路徑,
好讓 ``server.py`` 一行就註冊得完):

    /api/strategy?id=<策略編號>            策略身份、版本沿革、因子、運行總數
    /api/strategy/runs?id=&limit=&offset=  歷次運行(逐頁,含年化/回撤/勝率)
    /api/strategy/picks?run=&date=         某一日的選股快照、漏斗、因子敞口

淨值線、八項指標、成交標記**不在這裡**:那幾樣 ``/api/runs/<run_id>`` 早已
交得出,策略頁直接沿用同一個端點,兩頁不會各算一套。

一件事要講明白:庫內 ``factor_value`` 現時一列都沒有,即**逐日逐股的因子
分數並未落檔**。所以選股快照只交得出落了檔的那幾樣(範圍、持倉、股數、
權重),分數與過關格一格都不虛構——拿不到的東西前端就不顯示那一格
(與 ``data.py`` 檔頭同一句)。
"""

from __future__ import annotations

import math
import re
from typing import Any, Callable
from weakref import WeakKeyDictionary

import pandas as pd

from karst.data.snapshots import read_price_frame, read_universe
from karst.errors import ContractViolation, NotFound
from karst.metrics import trade_stats
from karst.metrics.ratios import annual_volatility
from karst.runs import BASE, window_stats
from karst.store import FORMAL_RUN, SWEEP_RUN

# 一頁歷次運行的預設條數。這張表自 KARST-054 起只列**正式運行**,四千個掃描格
# 由庫身篩走(D-029),所以現實中一頁綽綽有餘。閘照舊留住:每一行的年化/回撤/
# 勝率都要讀一次該運行的 parquet(實測約 15ms 一個),真的有一日跑出幾百次正式
# 運行,無閘就會等足一分鐘。照實回報總數,由頁面講明「共 N 次」。
DEFAULT_RUN_PAGE = 50
MAX_RUN_PAGE = 200

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


def _resolve(reader: Any, wanted: str | None) -> Any:
    """把 ?id= 解成一套策略。收策略編號,亦收策略名(總覽頁連過來時兩者皆可)。

    不帶 id:揀最近有運行的那一套——直接開 /strategy 也有東西看得到。
    """
    versions = _strategies(reader)
    if not versions:
        raise NotFound("定義庫內未有任何策略")

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


def _factor_payload(reader: Any, version: Any, used: bool) -> dict[str, Any]:
    """一個因子的身份與版本鏈。鏈由庫讀回,不是這裡數出來的。"""
    try:
        chain = reader.store.factor_version_chain(version.name)
    except NotFound:
        chain = [version]
    return {
        "factorId": version.factor_id,
        "name": version.name,
        "family": version.family,
        "versionNo": version.version_no,
        "scaleKind": version.scale_kind,
        "description": version.description,
        "createdAt": version.created_at,
        "used": used,
        "chain": [
            {
                "versionNo": item.version_no,
                "createdAt": item.created_at,
                "description": item.description,
            }
            for item in reversed(chain)
        ],
    }


def overview(reader: Any, query: dict[str, list[str]]) -> dict[str, Any]:
    """策略身份、版本沿革、因子、運行總數,以及預設檢視哪一次運行。"""
    strategy = _resolve(reader, _one(query, "id"))
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
        "defaultRunId": runs[0].run_id if runs else None,
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
        "factors": [_factor_payload(reader, f, True) for f in strategy.factors],
    }


# ---------------- 歷次運行 ----------------


def _row_metrics(reader: Any, run_id: str) -> dict[str, Any]:
    """一行運行要顯示的三個數。

    只讀該次運行自己的兩條序列(淨值、成交),不叫 ``run_metrics``——
    後者連基準曲線一併算(要讀整份快照價格),一頁五十行就慢十倍。
    年化與最大回撤照 ``window_stats`` 的全期口徑,勝率照 ``trade_stats``,
    與運行詳情頁同一套算法。
    """
    equity = reader.runs.equity_curve(run_id)
    stats = window_stats(equity, None, None, base=BASE)
    trades = trade_stats(reader.runs.orders(run_id), equity.index)
    return {
        "totalReturnPct": _pct(stats.total_return),
        "annualReturnPct": _pct(stats.annual_return),
        "maxDrawdownPct": _pct(stats.max_drawdown),
        "winRatePct": _pct(trades.win_rate),
        "profitLossRatio": _f(trades.profit_loss_ratio),
        "closedTrades": trades.closed_trades,
        "tradingDays": stats.trading_days,
    }


def runs(reader: Any, query: dict[str, list[str]]) -> dict[str, Any]:
    """該策略的歷次運行(只列正式運行),新的在前,逐頁交。

    自 KARST-054 起這張表只有正式運行,一套策略通常得幾次,所以逐頁那一套實際上
    再用不著;``limit`` / ``offset`` 照舊收,因為端點的形狀是對外的約定,而且庫內
    真的有一日出現幾百次正式運行時,它仍然是那道閘。
    """
    strategy = _resolve(reader, _one(query, "id"))
    every = _runs_of(reader, strategy.name)

    offset = max(0, _int(query, "offset", 0))
    limit = _int(query, "limit", DEFAULT_RUN_PAGE)
    if limit <= 0 or limit > MAX_RUN_PAGE:
        limit = MAX_RUN_PAGE
    page = every[offset : offset + limit]

    items = []
    for record in page:
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
        item.update(_row_metrics(reader, record.run_id))
        items.append(item)

    return {
        "strategyId": strategy.strategy_id,
        "strategyName": strategy.name,
        "total": len(every),
        # 空表要講得出「不是壞了,是這套策略只跑過掃描」——連幾多格一齊交
        "sweepCellTotal": _sweep_cells_of(reader, strategy.name),
        "offset": offset,
        "shown": len(items),
        "items": items,
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


def picks(reader: Any, query: dict[str, list[str]]) -> dict[str, Any]:
    """某一次運行、某一日的選股快照:範圍、持倉、權重,連因子敞口。

    畫面上的漏斗只列**落了檔**的層。庫內 ``factor_value`` 一列都沒有,
    基本面關與技術關那兩層現時無從算起,所以不畫——不是畫一個空格,
    是連那一層都不出現,並在 ``notes`` 講明原因。
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
        rows.append(
            {
                "entityId": item["entityId"],
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
                "held": shares is not None and shares > 0,
                "status": "持倉" if (shares is not None and shares > 0) else "未持倉",
            }
        )
    rows.sort(key=lambda r: (-(r["weightPct"] or 0.0), r["symbol"]))

    scope = len(rows)
    holding = sum(1 for r in rows if r["held"])

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
        "funnel": [
            {
                "key": "scope",
                "label": "範圍",
                "hint": f"數據快照 {record.snapshot_id} 當日可交易的標的(已扣除基準)",
                "count": scope,
            },
            {
                "key": "held",
                "label": "持倉",
                "hint": "扣除倉位上限與風控後,該日收工時實際持有",
                "count": holding,
            },
        ],
        "rows": rows,
        "exposure": exposure,
        "notes": {
            "scoresAvailable": False,
            "why": "定義庫未有逐日因子分數(factor_value 尚未落檔),"
            "所以基本面關與技術關兩層、以及逐股分數欄位一格都不顯示。",
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
    }
