"""KARST-052 由畫面發起的重跑與重掃:下單、排隊、查進度。

本檔是網頁殼**唯一**會寫庫的一層,與 ``api_overview`` / ``api_strategy`` /
``api_sweep`` 那三個只讀的相反。寫入一律經**唯一入口** ``karst.gateway``:
參數集由 ``Gateway.register_param_set`` 登記(同名同節奏同取值自動沿用舊版),
運行由 ``karst.runs.RunStore`` 落痕。本檔一句 SQL 都不寫,亦不碰 parquet。

三條規矩,寫在這裡免得日後有人「順手」破例
------------------------------------------
1. **不繞過唯一入口。** 畫面交上來的取值只做形狀檢查(有沒有缺格、是不是這個
   運行本來就有的那幾格),然後原封交去入口;取值合不合法由入口與庫層講。
2. **不設參數預設值。** 彈窗每一格預填的是**當前運行的取值**,那是「當前值」,
   不是預設值(D-008 第 3 條:碼裡不留任何一個取值)。所以下單時每一格都要
   明文帶齊——少一格即拒收,本檔不會替用戶補一個數。
3. **不在請求裡跑引擎。** 一次回測動輒十幾秒,一次重掃幾分鐘;HTTP 請求只負責
   下單並即刻交回工作編號,真正的執行在**一條**背景工作執行緒上排隊。前端輪詢
   ``/api/job`` 看進度,做完了自己跳去新的運行編號。

為什麼只有一條工作執行緒
------------------------
兩次重跑同時動同一個庫就會撞寫入鎖,而且引擎本身吃滿 CPU,並行沒有好處。
本機檢視器一次只服務一個人,先入先出排隊即可(D-020 第 2 條:重計算全留在後端)。
"""

from __future__ import annotations

import json
import os
import queue
import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from karst.errors import ContractViolation, KarstError, NotFound

# 下單那一刻寫在留痕上的「寫入者」:一眼看得出這一次是由畫面發起,不是腳本跑的。
WRITER = "karst-web"

# 請求體上限。畫面交上來的只是幾十格取值,一兆位元組都用不著。
MAX_BODY_BYTES = 256 * 1024

# 記得住的工作數目(做完的照留,用戶回頭看得到上一次跑出什麼)
JOB_HISTORY = 24

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"


class JobError(ContractViolation):
    """下單本身不合格(缺一格取值、沒有講明由哪一個運行重跑)。

    承 ``ContractViolation``,所以無論走 GET 還是 POST,``server.py`` 那一套
    既有的錯誤映射都會把它答成 400——不用在兩處各寫一次。
    """


# ----------------------------------------------------------------------
# 一件工作
# ----------------------------------------------------------------------


class Job:
    """一次重跑或一次重掃。狀態由工作執行緒改,讀的人隨時取得到快照。"""

    def __init__(self, job_id: str, kind: str, label: str, payload: dict[str, Any]) -> None:
        self.id = job_id
        self.kind = kind                    # "rerun" | "rescan"
        self.label = label                  # 一句人話,講這次在跑什麼
        self.payload = payload
        self.status = QUEUED
        self.note = "排隊中"                # 進行中那句話,前端照樣顯示
        self.error: str | None = None
        self.result: dict[str, Any] = {}
        self.submitted_at = _now()
        self.started_at: str | None = None
        self.finished_at: str | None = None
        self._lock = threading.Lock()

    def say(self, note: str) -> None:
        """報一句進度。工作執行緒叫,讀的人下一次輪詢就見到。"""
        with self._lock:
            self.note = note

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "jobId": self.id,
                "kind": self.kind,
                "label": self.label,
                "status": self.status,
                "note": self.note,
                "error": self.error,
                "submittedAt": self.submitted_at,
                "startedAt": self.started_at,
                "finishedAt": self.finished_at,
                **self.result,
            }


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ----------------------------------------------------------------------
# 佇列:一條工作執行緒,先入先出
# ----------------------------------------------------------------------


class JobQueue:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._order: list[str] = []
        self._pending: "queue.Queue[str]" = queue.Queue()
        self._worker: threading.Thread | None = None
        self._seq = 0

    # ---------- 下單 ----------
    def submit(
        self,
        kind: str,
        label: str,
        payload: dict[str, Any],
        runner: Callable[[Job], dict[str, Any]],
    ) -> Job:
        with self._lock:
            self._seq += 1
            job = Job(f"job-{self._seq}", kind, label, payload)
            job.payload["_runner"] = runner
            self._jobs[job.id] = job
            self._order.append(job.id)
            # 舊工作只留最近幾件,做完的先走
            while len(self._order) > JOB_HISTORY:
                stale = self._order.pop(0)
                self._jobs.pop(stale, None)
            self._ensure_worker()
        self._pending.put(job.id)
        return job

    def get(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise NotFound(f"沒有這件工作:{job_id}(只記得最近 {JOB_HISTORY} 件)")
        return job

    def recent(self, limit: int = JOB_HISTORY) -> list[dict[str, Any]]:
        with self._lock:
            ids = list(reversed(self._order))[:limit]
            jobs = [self._jobs[i] for i in ids if i in self._jobs]
        return [job.snapshot() for job in jobs]

    def busy(self) -> bool:
        with self._lock:
            return any(
                self._jobs[i].status in (QUEUED, RUNNING) for i in self._order if i in self._jobs
            )

    # ---------- 執行 ----------
    def _ensure_worker(self) -> None:
        """第一次下單才起工作執行緒:沒有人重跑就不佔一條執行緒。"""
        if self._worker is not None and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._work, name="karst-jobs", daemon=True)
        self._worker.start()

    def _work(self) -> None:
        while True:
            job_id = self._pending.get()
            job = self._jobs.get(job_id)
            if job is None:
                continue
            runner = job.payload.pop("_runner", None)
            if runner is None:
                continue
            job.status = RUNNING
            job.started_at = _now()
            job.say("開始")
            try:
                job.result = runner(job) or {}
                job.status = DONE
                job.say(job.result.get("note") or "做完")
            except Exception as exc:  # noqa: BLE001
                job.status = FAILED
                # 引擎那一層的錯經常一大段 traceback;人看的那句留在 error,
                # 詳細的印在伺服器主控台,不塞進瀏覽器。
                job.error = f"{type(exc).__name__}：{exc}"
                job.say("跑不完")
                print("  [重跑/重掃] 出錯\n" + traceback.format_exc())
            finally:
                job.finished_at = _now()


_QUEUE = JobQueue()


# ----------------------------------------------------------------------
# 專案路徑:全部由 reader 推回來,本檔不自己猜 cwd
# ----------------------------------------------------------------------


def _db_path_of(reader: Any) -> Path:
    """讀取層那個庫檔在哪。

    讀取層只讀,寫入要另開一條讀寫連線(經唯一入口),所以要知道庫檔路徑。
    ``RunReader`` 現時把路徑收在連線來源裡(KARST-055 逐執行緒一條連線),
    早前是直接掛在 reader 上——兩種都認,兩種都沒有就照倉根推。
    """
    for holder in (reader, getattr(reader, "_source", None)):
        found = getattr(holder, "db_path", None)
        if found:
            return Path(found)
    runs_root = Path(getattr(reader, "runs_root", "."))
    root = runs_root.parent.parent if runs_root.name == "runs" else Path.cwd()
    return root / "karst.sqlite"


class JobContext:
    def __init__(self, reader: Any) -> None:
        self.reader = reader
        self.db_path = _db_path_of(reader)
        self.runs_root = Path(reader.runs_root)
        self.snapshot_root = Path(reader.snapshot_root)
        self.risk_free_rate = float(getattr(reader, "risk_free_rate", 0.0) or 0.0)

    @property
    def project_root(self) -> Path:
        # data/runs → 倉根。與 api_sweep._project_root 同一套推法。
        path = self.runs_root
        if path.name == "runs" and path.parent.name == "data":
            return path.parent.parent
        return self.db_path.parent


def _open_gateway(ctx: JobContext):
    """開唯一入口。寫入者一眼看得出這一次由畫面發起。"""
    from karst.gateway import Gateway

    return Gateway.open(str(ctx.db_path), writer=os.environ.get("KARST_WRITER") or WRITER)


def _clean_values(raw: Any, expected: dict[str, str]) -> dict[str, str]:
    """畫面交上來的取值:一格不多、一格不少,而且全部收成字串。

    **不補預設值**——少交一格即拒收。彈窗每格預填的是當前運行的取值,用戶改哪
    一格是他的事,但交上來那一份必須是完整的一組(D-008 第 3 條)。
    """
    if not isinstance(raw, dict):
        raise JobError("要一份參數取值(values),形如 {\"參數名\": \"取值\"}")
    values = {str(key).strip(): str(value).strip() for key, value in raw.items()}
    missing = sorted(set(expected) - set(values))
    extra = sorted(set(values) - set(expected))
    if missing:
        raise JobError(
            f"少交了 {len(missing)} 格參數:{'、'.join(missing)};"
            "每一格都要明文帶齊,本層不會替你補一個數"
        )
    if extra:
        raise JobError(f"這個運行沒有這幾格參數:{'、'.join(extra)}")
    blank = sorted(key for key, value in values.items() if not value)
    if blank:
        raise JobError(f"這幾格留了空:{'、'.join(blank)};參數沒有預設值,要明文寫一個")
    return values


# ----------------------------------------------------------------------
# 重跑:同一段期間、同一個數據快照,改幾格參數,以**現行版本**再走一遍
# ----------------------------------------------------------------------


def _trend_swing_simulation(gateway: Any, ctx: JobContext, record: Any, param_set: Any) -> Any:
    """趨勢波段(規則路徑)。做法照 experiments/2026-08-28-trend-swing-real。"""
    from karst.data import read_universe
    from karst.metrics import DEFAULT_BENCHMARK_TICKERS
    from karst.strategies.trend_swing import build_bar_panel, read_setup, run_trend_swing

    store = gateway.store
    universe = read_universe(store, record.snapshot_id, root=ctx.snapshot_root)
    benchmarks = {t.upper() for t in DEFAULT_BENCHMARK_TICKERS}
    # 基準只做對照尺,不落注(D-010 第 4 條)
    traded = sorted(
        int(entity_id)
        for ticker, entity_id in zip(universe["ticker"], universe["entity_id"])
        if str(ticker).upper() not in benchmarks
    )
    panel = build_bar_panel(
        store,
        record.snapshot_id,
        entity_ids=traded,
        start=record.period_start,
        end=record.period_end,
        root=ctx.snapshot_root,
    )
    # 取值一律由參數集讀回來再跑,不用畫面交上來那一份——證明跑的真是入庫那一組
    params, risk = read_setup(param_set)
    return run_trend_swing(panel=panel, params=params, risk=risk)


def _factor_mix_simulation(gateway: Any, ctx: JobContext, record: Any, param_set: Any) -> Any:
    """因子混合(ETF 版,排名再平衡路徑)。"""
    from karst.strategies.factor_mix import FACTOR_ETF_SLEEVES, FactorMixParams, run_factor_mix

    params = FactorMixParams.from_param_set(param_set, FACTOR_ETF_SLEEVES)
    return run_factor_mix(
        store=gateway.store,
        panel=_price_panel(gateway.store, ctx, record.snapshot_id),
        sleeves=FACTOR_ETF_SLEEVES,
        params=params,
    )


# 策略名 → 怎樣跑一次。加一套策略只加一行,本檔其餘部分不用改。
RERUN_RECIPES: dict[str, Callable[[Any, JobContext, Any, Any], Any]] = {
    "趨勢波段": _trend_swing_simulation,
    "因子混合(ETF 版)": _factor_mix_simulation,
}


def _recipe_for(record: Any) -> Callable[[Any, JobContext, Any, Any], Any]:
    recipe = RERUN_RECIPES.get(record.strategy_name)
    if recipe is None:
        raise JobError(
            f"「{record.strategy_name}」這套策略未有由畫面重跑的做法;"
            f"現時支援:{'、'.join(sorted(RERUN_RECIPES)) or '(無)'}"
        )
    return recipe


def _rerun(job: Job, ctx: JobContext) -> dict[str, Any]:
    from karst.runs import RunStore
    from karst.store import FORMAL_RUN

    run_id = str(job.payload.get("runId") or "").strip()
    if not run_id:
        raise JobError("要講明由哪一個運行重跑(runId)")

    with _open_gateway(ctx) as gateway:
        store = gateway.store
        record = store.get_run(run_id)          # 查無此人 → NotFound → 404
        recipe = _recipe_for(record)
        values = _clean_values(job.payload.get("values"), record.param_values)
        cadence = str(job.payload.get("cadence") or "").strip()
        if not cadence:
            raise JobError("要講明換倉節奏(cadence);節奏是參數集的一部分,無預設值")

        # 1. 取值有無真的改動過?先同**這次運行自己蓋住那一版**參數集對一對。
        #    一格都沒改就一個字都不用寫:重跑不是改動,不應該在定義庫留下新一版。
        #
        #    這一格不能交給唯一入口自己認:它的沿用規矩只認**最新版**,所以若果
        #    這個參數集後來被改過(例如上一次重跑改了一格),再登記同一組舊取值
        #    會開多一版。版本號是運行編號的原料之一,編號就會跟住變,同取值重跑
        #    就得不回同一個編號。「有無改動」本來就是本層才答得到的事——畫面上
        #    每格預填的是當前運行的取值,對照的正本也就是當前運行那一版。
        version = store.get_strategy_version(record.strategy_name)  # 現行版本
        pinned = store.get_param_set(
            record.strategy_name,
            record.param_set_name,
            strategy_version_no=record.strategy_version_no,
            set_version_no=record.param_set_version_no,
        )
        unchanged = (
            version.version_no == record.strategy_version_no
            and cadence == pinned.rebalance_cadence
            and values == dict(pinned.values)
        )
        if unchanged:
            # 策略版本、節奏、每一格取值都無變 → 這次重跑講的就是原來那一次
            job.say("取值與原運行一模一樣,不用登記")
            param_set, param_set_reused = pinned, True
        else:
            # 2. 登記參數集(唯一入口)。策略版本留空即**現行版本**——「以現版本
            #    重跑」正是這個意思:舊運行不改寫,新運行接上現行版本的血統。
            job.say("經唯一入口登記參數集")
            param_set, receipt = gateway.register_param_set(
                record.strategy_name,
                param_set_name=record.param_set_name,
                rebalance_cadence=cadence,
                values=values,
            )
            param_set_reused = bool(receipt.reused)
        factor_ids = tuple(factor.factor_version_id for factor in version.factors)

        # 3. 跑之前先算運行編號:同一組輸入本來就有這一次,就不用再動引擎
        #    (karst/sweep/runner.py 逐格查重同一套做法)
        fingerprint = store.run_fingerprint(
            strategy_name=record.strategy_name,
            param_set_name=param_set.name,
            period_start=record.period_start,
            period_end=record.period_end,
            snapshot_id=record.snapshot_id,
            engine_name=record.engine_name,
            engine_version=record.engine_version,
            strategy_version_no=version.version_no,
            param_set_version_no=param_set.version_no,
            factor_version_ids=factor_ids or None,
        )
        expected = store.run_id_for(fingerprint)
        runs = RunStore(store, root=ctx.runs_root)
        try:
            existing = runs.get_run(expected)
        except NotFound:
            existing = None
        if existing is not None:
            return {
                "runId": existing.run_id,
                "reused": True,
                "paramSetReused": param_set_reused,
                "paramSetVersionNo": param_set.version_no,
                "note": f"同一組取值,沿用原來那個運行編號 {existing.run_id}(沒有再跑一次)",
            }

        # 4. 真的要跑。編號跑之前已經算得出(它是內容雜湊,不是跑完先派的流水號),
        #    所以即刻講出來:等的人見到自己等緊哪一個,萬一跑不完也知道是哪一個。
        job.say(f"新的運行編號是 {expected},跑緊回測(這一步要等一陣)")
        result = recipe(gateway, ctx, record, param_set)
        engine_name = getattr(result, "engine_name", None) or record.engine_name
        if engine_name != record.engine_name:
            raise ContractViolation(
                f"重跑用的引擎是 {engine_name},與本運行的 {record.engine_name} 不同;"
                "引擎是運行編號的原料之一,不同即不是同一條血統,請先查明"
            )

        job.say("落痕")
        fresh = runs.record_simulation(
            result,
            strategy_name=record.strategy_name,
            param_set_name=param_set.name,
            snapshot_id=record.snapshot_id,
            engine_version=record.engine_version,
            engine_name=engine_name,
            origin=FORMAL_RUN,
            period_start=record.period_start,
            period_end=record.period_end,
            strategy_version_no=version.version_no,
            param_set_version_no=param_set.version_no,
            factor_version_ids=factor_ids or None,
        )
        if fresh.run_id != expected:
            raise ContractViolation(
                f"落痕之後的運行編號 {fresh.run_id} 與跑之前算出來的 {expected} 對不上;"
                "查重靠的正是這個編號,對不上即代表登記與落痕不是同一套來歷,請先查明"
            )
        return {
            "runId": fresh.run_id,
            "reused": False,
            "paramSetReused": param_set_reused,
            "paramSetVersionNo": param_set.version_no,
            "note": f"跑完了,新的運行編號 {fresh.run_id}",
        }


# ----------------------------------------------------------------------
# 重掃:同一套來歷(策略版本 × 期間 × 數據快照 × 引擎 × 成本),換一個掃描格
# ----------------------------------------------------------------------
#
# 掃描現時不在庫裡:一次掃描 = ``experiments/`` 之下一個目錄,裡面一張掃描表加
# 一張判讀表(見 api_sweep.py 檔頭)。所以重掃做三件事:砌新格 → 經
# ``Executor.sweep`` 逐格落痕(同一格查得回舊運行就不重跑)→ 判讀並把兩張表
# 寫入一個新目錄,收尾多寫一列批次登記。舊掃描一個字不改。
#
# 重掃**不會**問用戶「這幅掃描本來是怎樣跑的」——那些全部由掃描自己身上讀回:
# 驅動器、熱身期、成本、快照、期間、引擎,一律取自格內那次運行的參數集與留痕。
# 用戶要改的只有掃描格本身,所以彈窗只開放那幾格。

RESCAN_DIRNAME = "重掃"
MACRO_DIRNAME = "macro_snapshots"

# 帳戶設定:重掃沿用原來那批掃描用的那一套。**它不入參數集,亦不入運行編號**
# ——所以它不是「一個沒有寫明的預設參數」,而是一件不影響身份的環境設定;寫在
# 這裡是為了兩條重掃路走同一個數,不是為了讓人調它。
RESCAN_INITIAL_CASH = 100_000.0
RESCAN_FEES = 0.0


@dataclass(frozen=True, slots=True)
class RescanPlan:
    """重掃要砌的東西:一幅新格 + 一份策略合約 + 起步取值 + 命名的兩截。

    以前這裡交的是一個「跑法」物件(``FactorMixJob`` / ``FactorRotationJob``),
    而那兩件各自抄了一次登記、查重、跑引擎、落痕。現在逐格怎樣跑住在執行台,
    本層只需要講「掃哪一幅格、用哪一份合約」。
    """

    grid: Any
    contract: Any
    base_values: dict[str, Any]
    param_set_prefix: str
    param_set_suffix: str
    engine: Any
    title: str
    extras: dict[str, Any] = field(default_factory=dict)


def _costed_engine(costs: Any) -> Any:
    """成本非零就換上替換件引擎;零成本就用預設那件(交回 ``None``)。

    成本要入的是**引擎參數**,而策略計劃載不起它(見 ``karst.engine.costed``)。
    引擎名照舊,所以運行編號不受這一層影響。
    """
    if costs is None or costs.is_zero:
        return None
    from karst.engine.costed import CostedEngine

    return CostedEngine(costs)


def _sweep_view(ctx: JobContext, sweep_id: str) -> Any:
    from karst.web import api_sweep

    return api_sweep.SweepReader(ctx.project_root, ctx.reader).view(sweep_id)


def _typed_like(sample_text: Any, text: Any) -> Any:
    """照參數集記住那一格的寫法決定型別:記住的沒有小數點,就當整數。

    型別要對得住——``50`` 與 ``50.0`` 砌出來的參數集名不同,一不同就當成另一格,
    本來查得回、不用重跑的舊運行會白跑一次。
    """
    raw = str(text).strip()
    sample = str(sample_text).strip()
    try:
        number = float(raw)
    except ValueError:
        return raw
    integral = "." not in sample and "e" not in sample.lower()
    if integral and number.is_integer():
        return int(number)
    return number


def _num_text(value: Any) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else repr(round(number, 10))


def _split_list(text: Any, name: str) -> list[str]:
    parts = [p.strip() for p in str(text or "").replace("、", ",").split(",")]
    parts = [p for p in parts if p]
    if not parts:
        raise JobError(f"軸「{name}」一個取值都沒有;掃描格無預設值,要明文寫幾個取值")
    return parts


def _axis_text(view: Any, name: str, sample_values: dict[str, str]) -> str:
    values = view.axis_values.get(name)
    if not values:
        raise JobError(f"這幅掃描沒有「{name}」這條軸,重掃不出同一套格")
    sample = sample_values.get(name, "")
    return "、".join(str(_typed_like(sample, v)) for v in values)


def _costs_of(values: dict[str, str]) -> Any:
    """由參數集取值還原交易成本。三格齊全才算有成本,一格都沒有就是零成本。"""
    from karst.engine.contracts import TradingCosts

    keys = ("fee_model", "fee_rate", "slippage")
    present = [key for key in keys if key in values]
    if not present:
        return None
    if len(present) != len(keys):
        raise JobError(
            f"這幅掃描的成本只記了 {'、'.join(present)},三格不齊;"
            "成本是運行編號的原料,湊不回原來那一套就重掃不出可比較的格"
        )
    return TradingCosts(
        fee_model=str(values["fee_model"]).strip(),
        fee_rate=float(values["fee_rate"]),
        slippage_fraction=float(values["slippage"]),
    )


def _price_panel(store: Any, ctx: JobContext, snapshot_id: str) -> Any:
    from karst.data import read_price_panel
    from karst.engine.contracts import PricePanel

    opens = read_price_panel(store, snapshot_id, field="open", root=ctx.snapshot_root).dropna(
        how="any"
    )
    closes = read_price_panel(store, snapshot_id, field="close", root=ctx.snapshot_root).dropna(
        how="any"
    )
    common = opens.index.intersection(closes.index)
    return PricePanel.from_frames(open=opens.loc[common], close=closes.loc[common])


def _prefix_of(param_set_name: str, suffix: str) -> str:
    """由「前綴 + 一格的短名」倒推前綴。

    前綴一定要與原來那幅掃描一模一樣,否則同一格會登記成另一個參數集名,
    於是算出另一個運行編號——本來查得回的格會全部重跑一次。倒推不中即當場
    拒收,不猜:猜錯的代價是白跑幾百格。
    """
    if suffix and param_set_name.endswith(suffix):
        return param_set_name[: len(param_set_name) - len(suffix)]
    raise JobError(
        f"認不出這幅掃描的參數集命名:「{param_set_name}」不是以「{suffix}」收尾;"
        "重掃要沿用同一套命名才查得回已經跑過的格,請先查明"
    )


# ---------------- 因子輪動 ----------------


def _rotation_axes(sample: Any) -> tuple[str, tuple[str, ...], str]:
    from karst.sweep.factor_mix import CADENCE_AXIS
    from karst.strategies.factor_rotation import DRIVER_PARAMETERS

    driver = str(sample.param_values.get("driver") or "").strip()
    if not driver:
        raise JobError("這幅掃描的格沒有記住是哪一個驅動器(參數集少了 driver 那一格),重掃不出來")
    names = DRIVER_PARAMETERS.get(driver)
    if not names:
        raise JobError(f"認不得這個驅動器:{driver}")
    return driver, tuple(names), CADENCE_AXIS


def _rotation_form(view: Any, sample: Any) -> list[dict[str, Any]]:
    driver, names, cadence_axis = _rotation_axes(sample)
    seen = dict(sample.param_values)
    seen[cadence_axis] = sample.rebalance_cadence
    controls = [
        {
            "name": name,
            "label": name,
            "kind": "list",
            "value": _axis_text(view, name, seen),
            "hint": "選擇軸" if name in view.choice_axes else "連續軸",
        }
        for name in names
    ]
    controls.append(
        {
            "name": cadence_axis,
            "label": "換倉節奏",
            "kind": "list",
            "value": _axis_text(view, cadence_axis, seen),
            "hint": "選擇軸",
        }
    )
    return controls


def _rotation_build(gateway: Any, ctx: JobContext, view: Any, sample: Any,
                    controls: dict[str, str]) -> "RescanPlan":
    from karst.data import read_macro_panel
    from karst.executor.contract import cost_inputs, cost_slug
    from karst.sweep.factor_rotation import point_slug, rotation_grid
    from karst.sweep.grid import SweepPoint
    from karst.strategies.factor_mix import FACTOR_ETF_SLEEVES
    from karst.strategies.factor_rotation import (
        DRIVER_KEY,
        MACRO_INPUT,
        MACRO_SERIES_KEY,
        MACRO_SERIES_SEPARATOR,
        MACRO_SNAPSHOT_KEY,
        WARMUP_BARS_KEY,
        WARMUP_PREFIX,
        FactorRotationContract,
        macro_series_needed,
    )

    driver, names, cadence_axis = _rotation_axes(sample)
    values = sample.param_values
    seen = dict(values)
    seen[cadence_axis] = sample.rebalance_cadence

    grid_values = {
        name: [_typed_like(seen.get(name, ""), t) for t in _split_list(controls.get(name), name)]
        for name in names
    }
    cadences = _split_list(controls.get(cadence_axis), cadence_axis)
    grid = rotation_grid(driver, values=grid_values, cadences=cadences)

    if "warmup_bars" not in values:
        raise JobError("這幅掃描的格沒有記住熱身期(warmup_bars),重掃不出同一套格")
    warmup_bars = int(float(values["warmup_bars"]))
    warmup_weights = {
        key[len("warmup_"):]: float(text)
        for key, text in values.items()
        if key.startswith("warmup_weight_")
    }
    if not warmup_weights:
        raise JobError("這幅掃描的格沒有記住熱身期的權重(warmup_weight_*),重掃不出同一套格")

    costs = _costs_of(values)
    # 前綴由樣本那一格倒推,不寫死任何命名規矩
    own = SweepPoint(
        tuple([(name, _typed_like(seen.get(name, ""), values[name])) for name in names]
              + [(cadence_axis, sample.rebalance_cadence)])
    )
    prefix = _prefix_of(sample.param_set_name, point_slug(own) + cost_slug(costs))

    macro = None
    macro_id = str(values.get("macro_snapshot") or "").strip() or None
    if macro_series_needed(driver):
        if not macro_id:
            raise JobError(
                f"「{driver}」要宏觀數據,而這幅掃描的格沒有記住宏觀快照編號(macro_snapshot)"
            )
        macro = read_macro_panel(
            gateway.store, macro_id, root=ctx.project_root / "data" / MACRO_DIRNAME
        )

    contract = FactorRotationContract(
        driver_key=driver,
        sleeves=FACTOR_ETF_SLEEVES,
        warmup_bars=warmup_bars,
        warmup_weights=warmup_weights,
        market_ticker=view.summary.get("market_ticker"),
        initial_cash=RESCAN_INITIAL_CASH,
        fees=RESCAN_FEES,
        costs=costs,
        macro_snapshot_id=macro_id,
    )
    # 起步取值 = 整幅格共用那幾格(不是軸,所以不入參數集的名,但照樣入值——
    # 換一個熱身期重掃就是另一次運行)。
    base_values: dict[str, Any] = {
        DRIVER_KEY: driver,
        WARMUP_BARS_KEY: warmup_bars,
        **{f"{WARMUP_PREFIX}{key}": value for key, value in warmup_weights.items()},
        **cost_inputs(costs),
    }
    if macro_id:
        base_values[MACRO_SNAPSHOT_KEY] = macro_id
        base_values[MACRO_SERIES_KEY] = MACRO_SERIES_SEPARATOR.join(
            macro_series_needed(driver)
        )
    return RescanPlan(
        grid=grid,
        contract=contract,
        base_values=base_values,
        param_set_prefix=prefix,
        param_set_suffix=cost_slug(costs),
        engine=_costed_engine(costs),
        extras={} if macro is None else {MACRO_INPUT: macro},
        title=f"因子輪動·{driver}·重掃",
    )


# ---------------- 因子混合(權重單純形格) ----------------


def _weight_step(view: Any, keys: tuple[str, ...]) -> float:
    """由格上的取值倒推步長:相鄰兩個取值之間最細那一格。"""
    for key in keys:
        values = sorted(float(v) for v in (view.axis_values.get(key) or []))
        gaps = [b - a for a, b in zip(values, values[1:]) if b > a]
        if gaps:
            return round(min(gaps), 10)
    raise JobError("認不出這幅權重格的步長,重掃不出同一套格")


def _mix_keys() -> tuple[str, ...]:
    from karst.strategies.factor_mix import FACTOR_ETF_SLEEVES

    return tuple(sleeve.weight_key for sleeve in FACTOR_ETF_SLEEVES)


def _mix_form(view: Any, sample: Any) -> list[dict[str, Any]]:
    from karst.sweep.factor_mix import CADENCE_AXIS

    keys = _mix_keys()
    controls = [
        {
            "name": "step",
            "label": "權重步長",
            "kind": "number",
            "value": _num_text(_weight_step(view, keys)),
            "hint": "四格權重的單純形格:步長越細,格越密(10% 是 286 格,5% 是 1771 格)",
        }
    ]
    if CADENCE_AXIS in view.axes:
        seen = {CADENCE_AXIS: sample.rebalance_cadence}
        controls.append(
            {
                "name": CADENCE_AXIS,
                "label": "換倉節奏",
                "kind": "list",
                "value": _axis_text(view, CADENCE_AXIS, seen),
                "hint": "選擇軸",
            }
        )
    return controls


def _mix_build(gateway: Any, ctx: JobContext, view: Any, sample: Any,
               controls: dict[str, str]) -> "RescanPlan":
    from karst.executor.contract import cost_inputs, cost_slug
    from karst.strategies.factor_mix import FACTOR_ETF_SLEEVES, FactorMixContract
    from karst.sweep.factor_mix import CADENCE_AXIS, weight_grid
    from karst.sweep.grid import SweepPoint

    keys = _mix_keys()
    raw_step = str(controls.get("step") or "").strip()
    try:
        step = float(raw_step)
    except ValueError:
        raise JobError(f"權重步長要一個數字,收到 {raw_step!r}") from None

    cadences = (
        _split_list(controls.get(CADENCE_AXIS), CADENCE_AXIS)
        if CADENCE_AXIS in view.axes
        else None
    )
    grid = weight_grid(FACTOR_ETF_SLEEVES, step=step, cadences=cadences)

    values = sample.param_values
    missing = [key for key in keys if key not in values]
    if missing:
        raise JobError(f"這幅掃描的格沒有記住權重 {'、'.join(missing)},重掃不出同一套格")
    costs = _costs_of(values)
    own_values = [(key, float(values[key])) for key in keys]
    if CADENCE_AXIS in view.axes:
        own_values.append((CADENCE_AXIS, sample.rebalance_cadence))
    prefix = _prefix_of(sample.param_set_name, SweepPoint(tuple(own_values)).slug + cost_slug(costs))

    contract = FactorMixContract(
        sleeves=FACTOR_ETF_SLEEVES,
        initial_cash=RESCAN_INITIAL_CASH,
        fees=RESCAN_FEES,
        costs=costs,
    )
    base_values: dict[str, Any] = dict(cost_inputs(costs))
    if CADENCE_AXIS not in view.axes:
        # 節奏不是這幅格的軸,即整幅格共用一個節奏:由樣本那一格讀回。
        base_values[CADENCE_AXIS] = sample.rebalance_cadence
    return RescanPlan(
        grid=grid,
        contract=contract,
        base_values=base_values,
        param_set_prefix=prefix,
        param_set_suffix=cost_slug(costs),
        engine=_costed_engine(costs),
        extras={},
        title="因子混合權重格·重掃",
    )


# 策略名 → (彈窗開放改哪幾格, 怎樣砌新格與跑法)
RESCAN_FAMILIES: dict[str, tuple[Callable[..., Any], Callable[..., Any]]] = {
    "因子輪動(ETF 版)": (_rotation_form, _rotation_build),
    "因子混合(ETF 版)": (_mix_form, _mix_build),
}


def _rescan_sample(ctx: JobContext, store: Any, view: Any) -> Any:
    """由格內任何一次運行倒查這幅掃描的來歷。掃描表自己不記來歷,運行記。"""
    if not view.cells:
        raise JobError("這幅掃描一格都沒有,重掃不出東西")
    return store.get_run(str(view.cells[0]["runId"]))


def _rescan_thresholds(view: Any) -> dict[str, Any]:
    thresholds = view.summary.get("thresholds")
    thresholds = thresholds if isinstance(thresholds, dict) else {}
    wanted = ("min_trades", "lonely_peak_margin", "plateau_quantile")
    missing = [key for key in wanted if key not in thresholds]
    if missing:
        raise JobError(
            f"這幅掃描沒有記住判讀門檻({'、'.join(missing)});"
            "門檻無預設值,湊不回原來那一套就判不出可比較的裁決"
        )
    if not view.objective:
        raise JobError("這幅掃描沒有記住判讀目標(objective),重掃之後判不出裁決")
    return thresholds


def rescan_form(ctx: JobContext, sweep_id: str) -> dict[str, Any]:
    """彈窗要顯示什麼:這幅掃描改得動哪幾格,每格預填**當前那一幅的取值**。"""
    view = _sweep_view(ctx, sweep_id)
    # 只是問「改得動什麼」,不寫任何東西:借讀取層那條唯讀連線就夠
    sample = _rescan_sample(ctx, ctx.reader.store, view)
    family = RESCAN_FAMILIES.get(sample.strategy_name)
    facts = {
        "sweepId": sweep_id,
        "strategy": sample.strategy_name,
        "snapshotId": sample.snapshot_id,
        "period": [sample.period_start, sample.period_end],
        "engine": f"{sample.engine_name} {sample.engine_version}",
        "objective": view.objective,
        "cells": len(view.cells),
    }
    if family is None:
        return {
            **facts,
            "supported": False,
            "reason": f"「{sample.strategy_name}」這套策略未有由畫面重掃的做法",
            "controls": [],
        }
    try:
        controls = family[0](view, sample)
        _rescan_thresholds(view)
    except JobError as exc:
        return {**facts, "supported": False, "reason": str(exc), "controls": []}
    return {**facts, "supported": True, "reason": "", "controls": controls}


def _rescan(job: Job, ctx: JobContext) -> dict[str, Any]:
    from karst.executor import SAMPLE, BatchReport, Executor
    from karst.runs import RunStore

    sweep_id = str(job.payload.get("sweepId") or "").strip()
    controls = job.payload.get("controls")
    if not isinstance(controls, dict) or not controls:
        raise JobError("要講明新的掃描格(controls),每一格都要明文帶齊")

    with _open_gateway(ctx) as gateway:
        store = gateway.store
        view = _sweep_view(ctx, sweep_id)
        sample = _rescan_sample(ctx, store, view)
        family = RESCAN_FAMILIES.get(sample.strategy_name)
        if family is None:
            raise JobError(
                f"「{sample.strategy_name}」這套策略未有由畫面重掃的做法;"
                f"現時支援:{'、'.join(sorted(RESCAN_FAMILIES))}"
            )
        thresholds = _rescan_thresholds(view)
        objective = view.objective

        job.say("砌新的掃描格")
        plan = family[1](gateway, ctx, view, sample, controls)

        stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        out_dir = ctx.project_root / "experiments" / RESCAN_DIRNAME / stamp
        new_id = out_dir.relative_to(ctx.project_root).as_posix()
        total = len(plan.grid)

        def progress(index: int, count: int, _cell: Any) -> None:
            job.say(f"跑緊第 {index}/{count} 格")

        job.say(f"共 {total} 格,開始跑")
        executor = Executor(
            gateway, RunStore(store, root=ctx.runs_root), snapshot_root=ctx.snapshot_root
        )
        # 重掃接住的是一次**已經發生過**的登記,所以只讀不寫:再登記一次會把版本鏈
        # 無故推前一格,而版本號是運行編號的原料——本來查得回、不用重跑的格會白跑。
        setup = executor.setup_from(
            plan.contract,
            strategy_name=sample.strategy_name,
            snapshot_id=sample.snapshot_id,
            param_set_name=sample.param_set_name,
            alignment=SAMPLE,
            strategy_version_no=sample.strategy_version_no,
            param_set_version_no=sample.param_set_version_no,
        )
        outcome = executor.sweep(
            plan.contract,
            setup=setup,
            grid=plan.grid,
            panel=_price_panel(store, ctx, sample.snapshot_id),
            period=(sample.period_start, sample.period_end),
            engine_version=sample.engine_version,
            risk_free_rate=ctx.risk_free_rate,
            sweep_id=new_id,
            param_set_prefix=plan.param_set_prefix,
            param_set_suffix=plan.param_set_suffix,
            base_values=plan.base_values,
            objective=objective,
            min_trades=int(thresholds["min_trades"]),
            lonely_peak_margin=float(thresholds["lonely_peak_margin"]),
            plateau_quantile=float(thresholds["plateau_quantile"]),
            report=BatchReport(
                directory=out_dir,
                title=f"{plan.title}(由畫面發起)",
                notes=(
                    f"由 `{sweep_id}` 重掃而來:同一個策略版本、同一段期間、同一個數據快照、"
                    "同一套成本,分別只在掃描格本身。舊那幅掃描一個字不改。\n\n"
                    f"判讀目標與門檻沿用原來那一幅({objective};"
                    f"min_trades={thresholds['min_trades']}、"
                    f"lonely_peak_margin={thresholds['lonely_peak_margin']}、"
                    f"plateau_quantile={thresholds['plateau_quantile']})。"
                ),
            ),
            engine=plan.engine,
            engine_name=sample.engine_name,
            extras=plan.extras,
            progress=progress,
        )
        sweep = outcome.sweep
        # 頁面靠這一份讀回判讀門檻與來歷。**不可以有 source 這一格**——
        # api_sweep 見到 source 就當這個目錄是「別處那幅掃描的重判」。
        summary = {
            "rescan_of": sweep_id,
            "snapshot_id": sample.snapshot_id,
            "period": [sample.period_start, sample.period_end],
            "objective": objective,
            "thresholds": dict(thresholds),
            "market_ticker": view.summary.get("market_ticker"),
            "cells": len(sweep),
            "executed": sweep.executed,
            "reused": sweep.reused,
            "provenance": {
                "strategy": sample.strategy_name,
                "strategy_version_no": sample.strategy_version_no,
                "snapshot_id": sample.snapshot_id,
                "period": [sample.period_start, sample.period_end],
                "engine": f"{sample.engine_name} {sample.engine_version}",
            },
        }
        (out_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        failed = len(outcome.failures)
        return {
            "sweepId": new_id,
            "cells": len(sweep),
            "executed": sweep.executed,
            "reusedCells": sweep.reused,
            "errorCells": failed,
            "note": (
                f"重掃完成:{len(sweep)} 格,其中 {sweep.executed} 格今次真的跑過、"
                f"{sweep.reused} 格讀回已有的運行"
                + (f";另有 {failed} 格拋錯,已按無效格入判讀" if failed else "")
            ),
        }


# ----------------------------------------------------------------------
# 下單:HTTP 那一層
# ----------------------------------------------------------------------


def _submit_rerun(ctx: JobContext, body: dict[str, Any]) -> dict[str, Any]:
    run_id = str(body.get("runId") or "").strip()
    if not run_id:
        raise JobError("要講明由哪一個運行重跑(runId)")
    # 收得下單之前先驗一次(讀取層那條唯讀連線就夠):交漏一格、查無此運行、
    # 未支援的策略,全部即刻答 400/404。排完隊才講,用戶等一場空。
    record = ctx.reader.store.get_run(run_id)
    _recipe_for(record)
    _clean_values(body.get("values"), record.param_values)
    if not str(body.get("cadence") or "").strip():
        raise JobError("要講明換倉節奏(cadence);節奏是參數集的一部分,無預設值")
    job = _QUEUE.submit(
        "rerun",
        f"重跑 {run_id}",
        dict(body),
        lambda j: _rerun(j, ctx),
    )
    return job.snapshot()


def _submit_rescan(ctx: JobContext, body: dict[str, Any]) -> dict[str, Any]:
    sweep_id = str(body.get("sweepId") or "").strip()
    if not sweep_id:
        raise JobError("要講明由哪一幅掃描重掃(sweepId)")
    controls = body.get("controls")
    if not isinstance(controls, dict) or not controls:
        raise JobError("要講明新的掃描格(controls),每一格都要明文帶齊")
    # 同上:未支援的策略、湊不回門檻的掃描,收單那一刻就講
    form = rescan_form(ctx, sweep_id)
    if not form.get("supported"):
        raise JobError(form.get("reason") or "這幅掃描重掃不出來")
    missing = [c["name"] for c in form["controls"] if not str(controls.get(c["name"]) or "").strip()]
    if missing:
        raise JobError(f"這幾格留了空:{'、'.join(missing)};掃描格無預設值,要明文寫")
    job = _QUEUE.submit(
        "rescan",
        f"重掃 {sweep_id}",
        dict(body),
        lambda j: _rescan(j, ctx),
    )
    return job.snapshot()


_POST_ROUTES: dict[str, Callable[[JobContext, dict[str, Any]], dict[str, Any]]] = {
    "/api/rerun": _submit_rerun,
    "/api/rescan": _submit_rescan,
}


def _read_body(handler: Any) -> dict[str, Any]:
    """讀請求體。HTTP/1.1 是長連線,body 一定要讀完,否則下一個請求會錯位。"""
    raw = handler.headers.get("Content-Length")
    try:
        length = int(raw or 0)
    except ValueError:
        raise JobError(f"Content-Length 要一個整數,收到 {raw!r}") from None
    if length <= 0:
        raise JobError("下單要一份 JSON 請求體")
    if length > MAX_BODY_BYTES:
        raise JobError(f"請求體太大({length} 位元組),上限 {MAX_BODY_BYTES}")
    body = handler.rfile.read(length)
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JobError(f"請求體不是 UTF-8 的 JSON:{exc}") from None
    if not isinstance(payload, dict):
        raise JobError("請求體要是一個 JSON 物件")
    return payload


def handle_post(handler: Any, reader: Any) -> None:
    """server.py 的 ``do_POST`` 只需轉呼這一句;寫入端點全部住在本檔。

    回應與錯誤映射照 ``do_GET`` 那一套:下單本身不合格是 400,運行/掃描查無此人
    是 404,收得下單即 202 加一個工作編號(真正的執行在背景排隊)。
    """
    path = urlparse(handler.path).path
    try:
        if path not in _POST_ROUTES:
            # 未讀的請求體照樣要清走,否則長連線會錯位
            _drain(handler)
            handler._send_json(HTTPStatus.NOT_FOUND, {"error": f"沒有這個端點:{path}"})
            return
        body = _read_body(handler)
        handler._send_json(HTTPStatus.ACCEPTED, _POST_ROUTES[path](JobContext(reader), body))
    except JobError as exc:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
    except NotFound as exc:
        handler._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
    except (ContractViolation, KarstError) as exc:
        handler._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
    except BrokenPipeError:
        pass
    except Exception as exc:  # noqa: BLE001
        print("  [下單] 出錯\n" + traceback.format_exc())
        handler._send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"{type(exc).__name__}：{exc}"}
        )


def _drain(handler: Any) -> None:
    try:
        length = int(handler.headers.get("Content-Length") or 0)
    except ValueError:
        return
    if 0 < length <= MAX_BODY_BYTES:
        handler.rfile.read(length)


def routes(reader: Any) -> dict[str, Callable[[Any, dict[str, list[str]]], Any]]:
    """查進度那兩條(GET)。下單那兩條是 POST,見 ``handle_post``。"""

    def one(_handler: Any, query: dict[str, list[str]]) -> Any:
        job_id = (query.get("id") or [""])[0].strip()
        if not job_id:
            raise JobError("要講明查哪一件工作(id)")
        return _QUEUE.get(job_id).snapshot()

    def many(_handler: Any, query: dict[str, list[str]]) -> Any:
        raw = (query.get("limit") or [str(JOB_HISTORY)])[0]
        try:
            limit = max(1, min(JOB_HISTORY, int(raw)))
        except ValueError:
            raise JobError(f"limit 要一個整數,收到 {raw!r}") from None
        return {"jobs": _QUEUE.recent(limit), "busy": _QUEUE.busy()}

    def form(_handler: Any, query: dict[str, list[str]]) -> Any:
        sweep_id = (query.get("id") or [""])[0].strip()
        if not sweep_id:
            raise JobError("要講明看哪一幅掃描(id)")
        return rescan_form(JobContext(reader), sweep_id)

    return {"/api/job": one, "/api/jobs": many, "/api/rescan-form": form}
