"""KARST-089 對照腳本:vectorbt_engine.py 兩處注碼/比重算術是否逐位相同。

只讀不寫:定義庫用 sqlite3 唯讀模式(``mode=ro``)開,只行 SELECT;
karst/ 一個檔都不改,兩處算術都是**原地執行真碼**,不是抄一份出來重寫:

- 甲處 ``_order_rules_nb``(njit,逐格純量)——用 numba 的 ``.py_func`` 取回
  未編譯的原函式,配一個假的逐格情境物件直接呼叫。
- 乙處 ``VectorbtSignalMatrixEngine.simulate_rules``(numpy,整張矩陣)——把
  ``vbt.Portfolio.from_signals`` 暫時換成一個攔截器,接住它算好交出來的
  ``size`` 矩陣即中止,所以 319–328 行那段算術是真的行了一次。

用法:PYTHONUTF8=1 python compare.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import vectorbt as vbt  # noqa: E402

from karst.engine import vectorbt_engine as ve  # noqa: E402
from karst.engine.rules import BarPanel, ExitPlan, RuleSignals  # noqa: E402
from karst.store import DefinitionStore  # noqa: E402
from karst.strategies.trend_swing import read_setup  # noqa: E402

DB = REPO / "karst.sqlite"
OUT = Path(__file__).resolve().parent / "result.json"

# 兩處算術在源碼裡的位置。行號會飄,所以另外把該幾行原文抄入結果檔,好等下一個
# 人核對「腳本行的到底是不是這兩段」。
SITE_A = ("karst/engine/vectorbt_engine.py", "_order_rules_nb", (207, 219))
SITE_B = ("karst/engine/vectorbt_engine.py", "VectorbtSignalMatrixEngine.simulate_rules", (319, 328))


# ----------------------------------------------------------------------
# 定義庫:唯讀開啟,只取參數集
# ----------------------------------------------------------------------
def read_only_store() -> tuple[DefinitionStore, sqlite3.Connection]:
    """唯讀開庫。**不行 schema.connect**——那條路會建表兼寫 schema_meta。"""
    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return DefinitionStore(conn), conn


def rule_path_param_sets(store: DefinitionStore, conn: sqlite3.Connection) -> list[Any]:
    """庫內全部規則類(有注碼/風控參數)的參數集,經 store 的查詢介面取回。"""
    names = [
        r["name"]
        for r in conn.execute(
            "SELECT DISTINCT s.name AS name FROM strategy s"
            " JOIN strategy_version sv ON sv.strategy_id = s.strategy_id"
        )
    ]
    found: list[Any] = []
    for name in names:
        versions = [
            int(r["version_no"])
            for r in conn.execute(
                "SELECT sv.version_no FROM strategy_version sv"
                " JOIN strategy s ON s.strategy_id = sv.strategy_id WHERE s.name = ?",
                (name,),
            )
        ]
        for version_no in versions:
            # list_param_sets 同名只交回最新一版;參數集的**每一版**都要對照,
            # 所以逐版點名再經 get_param_set 取回。
            heads = {ps.name for ps in store.list_param_sets(name, strategy_version_no=version_no)}
            for set_name in sorted(heads):
                set_versions = [
                    int(r["version_no"])
                    for r in conn.execute(
                        "SELECT ps.version_no FROM param_set ps"
                        " JOIN strategy_version sv ON sv.strategy_version_id = ps.strategy_version_id"
                        " JOIN strategy s ON s.strategy_id = sv.strategy_id"
                        " WHERE s.name = ? AND sv.version_no = ? AND ps.name = ?"
                        " ORDER BY ps.version_no",
                        (name, version_no, set_name),
                    )
                ]
                for set_version_no in set_versions:
                    ps = store.get_param_set(
                        name, set_name,
                        strategy_version_no=version_no,
                        set_version_no=set_version_no,
                    )
                    if any(k.startswith("sizing.") for k in ps.values):
                        found.append((name, version_no, ps))
    return found


def runs_of(conn: sqlite3.Connection, param_set_id: int) -> list[dict[str, Any]]:
    return [
        dict(r)
        for r in conn.execute(
            "SELECT run_id, origin, engine_name FROM backtest_run WHERE param_set_id = ?"
            " ORDER BY created_at",
            (int(param_set_id),),
        )
    ]


# ----------------------------------------------------------------------
# 甲處:真碼,經 numba 的 py_func 逐格呼叫
# ----------------------------------------------------------------------
class _Context:
    """``_order_rules_nb`` 用到的四格情境。其餘欄位那條路行不到,不用造。"""

    def __init__(self, i: int, col: int, position_now: float, value_now: float) -> None:
        self.i = i
        self.col = col
        self.position_now = position_now
        self.value_now = value_now


def site_a_shares(
    *,
    price: float,
    stop_level: float,
    value_now: float,
    risk_per_trade: float,
    max_position_fraction: float,
    fixed_equity_basis: float,
) -> float:
    """行一次甲處真碼,交回它落單的股數;不落單即 NaN。"""
    rows, cols = 1, 1
    open_ = np.array([[price]], dtype=float)
    entries = np.array([[True]])
    stop = np.array([[stop_level]], dtype=float)
    exit_bar = np.full((rows, cols), -1, dtype=np.int64)
    exit_price = np.zeros((rows, cols))
    exit_code = np.full((rows, cols), ve.EXIT_CODE_NONE, dtype=np.int8)
    exit_mark = np.full((rows, cols), ve.EXIT_CODE_NONE, dtype=np.int8)
    position_entry = np.full(cols, ve._NO_ENTRY, dtype=np.int64)
    blocked = np.zeros(rows)

    order = ve._order_rules_nb.py_func(
        _Context(0, 0, 0.0, value_now),
        open_, entries, stop,
        exit_bar, exit_price, exit_code, exit_mark,
        position_entry, blocked,
        risk_per_trade, max_position_fraction, fixed_equity_basis,
        0.0, 0.0, 0.0,
    )
    size = float(getattr(order, "size", np.nan))
    return size


# ----------------------------------------------------------------------
# 乙處:真碼,攔截 from_signals 接住它算好的 size 矩陣
# ----------------------------------------------------------------------
class _Captured(Exception):
    def __init__(self, size: np.ndarray) -> None:
        super().__init__("captured")
        self.size = np.asarray(size, dtype=float)


def site_b_shares(
    *, prices: np.ndarray, stop_levels: np.ndarray, params: Any
) -> np.ndarray:
    """行一次乙處真碼,交回它交去 from_signals 的 ``size`` 矩陣。"""
    rows = len(prices)
    columns = [1]
    dates = pd.date_range("2020-01-02", periods=rows, freq="D")

    def frame(values: np.ndarray) -> pd.DataFrame:
        return pd.DataFrame(np.asarray(values, dtype=float).reshape(rows, 1),
                            index=dates, columns=columns)

    opens = np.asarray(prices, dtype=float)
    # 高低收只是為了砌一份形狀正確的面板;乙處那段算術只讀 open 與 stop_level,
    # 而攔截器在 from_signals 那一刻就中止,所以這三張表不會影響結果。
    panel = BarPanel(
        open=frame(opens),
        high=frame(np.nan_to_num(opens, nan=1.0) * 1.01),
        low=frame(np.nan_to_num(opens, nan=1.0) * 0.99),
        close=frame(opens),
    )
    stop = np.asarray(stop_levels, dtype=float).reshape(rows, 1)
    zeros = np.zeros((rows, 1))
    signals = RuleSignals(
        entries=np.ones((rows, 1), dtype=bool),
        stop_level=stop,
        target_level=zeros,
        stop_fraction=np.full((rows, 1), 0.05),
        target_fraction=np.full((rows, 1), 0.10),
        month_id=np.zeros(rows, dtype=np.int64),
        exits=ExitPlan(
            exit_bar=np.full((rows, 1), -1, dtype=np.int64),
            exit_price=zeros,
            exit_code=np.full((rows, 1), ve.EXIT_CODE_NONE, dtype=np.int8),
        ),
        breakout=np.ones((rows, 1), dtype=bool),
        plan_ready=np.ones((rows, 1), dtype=bool),
        breakout_margin=zeros,
        plan_reward_risk=np.full((rows, 1), 2.0),
    )

    original = vbt.Portfolio.from_signals

    def intercept(*args: Any, **kwargs: Any):
        raise _Captured(kwargs["size"])

    vbt.Portfolio.from_signals = staticmethod(intercept)
    try:
        ve.VectorbtSignalMatrixEngine().simulate_rules(panel, signals, params)
    except _Captured as captured:
        return captured.size.reshape(rows)
    finally:
        vbt.Portfolio.from_signals = original
    raise AssertionError("乙處沒有行到 from_signals")


# ----------------------------------------------------------------------
# 逐位比較
# ----------------------------------------------------------------------
def bits(value: float) -> str:
    """一個 float64 的位模式。NaN 與 -0.0 都分得出,所以「逐位相同」名副其實。"""
    return np.float64(value).tobytes().hex()


def identical(left: float, right: float) -> bool:
    return bits(left) == bits(right)


def case_grid(initial_cash: float) -> list[dict[str, Any]]:
    """輸入格:一半是尋常價位,一半是邊界。價位刻意用非整數,好逼出浮點差異。"""
    # 標籤裡的「封頂/未封頂」按 0.02 / 0.25 這組取值算:止蝕距離窄過成交價的
    # 8%(= risk / maxfrac)就會踩到單一持倉市值上限。
    normal = [
        ("尋常:止蝕闊、上限未封頂", 100.0, 88.0),
        ("尋常:止蝕窄、上限封頂", 100.0, 96.0),
        ("尋常:非整數價位(上限封頂)", 37.43, 35.11),
        ("尋常:低價股(上限未封頂)", 1.07, 0.93),
        ("尋常:高價股(上限封頂)", 12345.678, 11987.5),
        ("尋常:止蝕貼身(上限封頂)", 250.0, 249.5),
    ]
    edge = [
        ("邊界:止蝕距離剛好為零", 100.0, 100.0),
        ("邊界:止蝕高於成交價(負距離)", 100.0, 104.0),
        ("邊界:止蝕距離極細(股數溢出)", 100.0, 100.0 - 5e-324),
        ("邊界:成交價缺值(NaN)", np.nan, 96.0),
        ("邊界:止蝕價缺值(NaN)", 100.0, np.nan),
        ("邊界:兩格皆缺值", np.nan, np.nan),
        ("邊界:成交價為零", 0.0, -4.0),
        ("邊界:成交價為負", -100.0, -104.0),
        ("邊界:止蝕價為零", 100.0, 0.0),
        # 成交價細到次正規:股數與上限同時是 +inf。甲處的 ``if shares > cap`` 封不到
        # (inf > inf 不成立),乙處的 ``isfinite`` 封得到——兩處唯一封不同的一格。
        ("邊界:成交價次正規(股數與上限同為 +inf)", 5e-324, 0.0),
        # 上限為 +inf 而股數有限:兩處都應該照落單。
        ("邊界:上限為 +inf、股數有限", 5e-324, -1000000.0),
        ("邊界:恰好踩正上限(股數 == cap)", 100.0, np.nan),  # 下面按參數改寫
    ]
    cases = [
        {"label": label, "price": price, "stop_level": stop}
        for label, price, stop in normal + edge
    ]
    return cases


def tie_case(price: float, risk_per_trade: float, max_position_fraction: float) -> float:
    """令 shares 恰好等於 cap 的止蝕價:stop_distance = risk/maxfrac × price。"""
    return price - risk_per_trade * price / max_position_fraction


def main() -> int:
    store, conn = read_only_store()
    report: dict[str, Any] = {
        "票": "KARST-089",
        "日期": "2026-08-30",
        "定義庫": {"路徑": str(DB), "開法": "sqlite3 mode=ro(唯讀),只行 SELECT"},
        "兩處": {
            "甲": {"檔": SITE_A[0], "函式": SITE_A[1], "行": list(SITE_A[2])},
            "乙": {"檔": SITE_B[0], "函式": SITE_B[1], "行": list(SITE_B[2])},
        },
        "源碼原文": {},
        "參數集": [],
    }

    source = (REPO / "karst" / "engine" / "vectorbt_engine.py").read_text(encoding="utf-8")
    lines = source.splitlines()
    for key, (_, _, (start, end)) in (("甲", SITE_A), ("乙", SITE_B)):
        report["源碼原文"][key] = lines[start - 1 : end]

    param_sets = rule_path_param_sets(store, conn)
    total_cases = 0
    total_same = 0
    runnable_as_stored = 0

    for strategy_name, strategy_version_no, ps in param_sets:
        strategy_params, risk = read_setup(ps)
        params = strategy_params.rule_params(risk)

        # 乙處**收貨門檻**:熔斷開住、或者基數取當下權益,它一律當場拒收。
        refusals = []
        if params.breaker_on:
            refusals.append("熔斷開住(monthly_loss_cap 有值)")
        if params.sizing.uses_current_equity:
            refusals.append("注碼基數 = 當下權益(current_equity)")
        if not refusals:
            runnable_as_stored += 1

        # 要兩處都行得到,唯有把參數改成乙處收得到的形態:關熔斷、基數改起始本金。
        # 這一步本身就是結論的一部分——庫內沒有一個參數集可以原封不動走乙處。
        comparable = replace(
            params,
            breaker=None,
            sizing=replace(params.sizing, equity_basis="initial_cash"),
        )
        # 甲處在引擎裡收到的固定基數(vectorbt_engine.py 第 248 行同一條式)
        fixed_basis = 0.0 if comparable.sizing.uses_current_equity else comparable.initial_cash
        equity = comparable.initial_cash

        cases = case_grid(equity)
        cases[-1]["stop_level"] = tie_case(
            cases[-1]["price"],
            comparable.sizing.risk_per_trade,
            comparable.sizing.max_position_fraction,
        )

        prices = np.array([c["price"] for c in cases], dtype=float)
        stops = np.array([c["stop_level"] for c in cases], dtype=float)

        b_values = site_b_shares(prices=prices, stop_levels=stops, params=comparable)

        rows = []
        for index, case in enumerate(cases):
            a_value = site_a_shares(
                price=case["price"],
                stop_level=case["stop_level"],
                value_now=equity,
                risk_per_trade=comparable.sizing.risk_per_trade,
                max_position_fraction=comparable.sizing.max_position_fraction,
                fixed_equity_basis=fixed_basis,
            )
            b_value = float(b_values[index])
            same = identical(a_value, b_value)
            total_cases += 1
            total_same += int(same)
            rows.append(
                {
                    "情況": case["label"],
                    "成交價": case["price"],
                    "止蝕價": case["stop_level"],
                    "甲_股數": a_value,
                    "乙_股數": b_value,
                    "甲_位": bits(a_value),
                    "乙_位": bits(b_value),
                    "逐位相同": same,
                    "甲_落單": bool(np.isfinite(a_value)),
                    "乙_落單": bool(np.isfinite(b_value)),
                }
            )

        report["參數集"].append(
            {
                "策略": strategy_name,
                "策略版本": strategy_version_no,
                "參數集": ps.name,
                "參數集版本": ps.version_no,
                "param_set_id": ps.param_set_id,
                "單筆風險上限": params.sizing.risk_per_trade,
                "單一持倉市值上限": params.sizing.max_position_fraction,
                "注碼基數": params.sizing.equity_basis,
                "月度虧損熔斷": None if params.breaker is None else params.breaker.max_monthly_drawdown,
                "起始本金": params.initial_cash,
                "乙處可否原封不動行": not refusals,
                "乙處拒收理由": refusals,
                "已登記運行": runs_of(conn, ps.param_set_id),
                "逐格對照": rows,
                "本組全數逐位相同": all(r["逐位相同"] for r in rows),
            }
        )

    conn.close()

    report["總結"] = {
        "參數集數": len(param_sets),
        "可原封不動走乙處的參數集數": runnable_as_stored,
        "對照格數": total_cases,
        "逐位相同格數": total_same,
        "全數逐位相同": total_cases == total_same,
        "不同的格": [
            {"參數集": entry["參數集"], "參數集版本": entry["參數集版本"], "情況": row["情況"],
             "甲": row["甲_股數"], "乙": row["乙_股數"]}
            for entry in report["參數集"]
            for row in entry["逐格對照"]
            if not row["逐位相同"]
        ],
    }

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = report["總結"]
    print(f"參數集 {summary['參數集數']} 個;對照 {summary['對照格數']} 格;"
          f"逐位相同 {summary['逐位相同格數']} 格")
    print(f"可原封不動走乙處的參數集:{summary['可原封不動走乙處的參數集數']} 個")
    for row in summary["不同的格"]:
        print(f"  不同:{row['參數集']} v{row['參數集版本']} / {row['情況']}:"
              f"甲={row['甲']} 乙={row['乙']}")
    print(f"結果已落 {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
