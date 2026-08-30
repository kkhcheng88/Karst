"""KARST-052 驗收:由畫面發起重跑與重掃,經唯一入口登記參數集並排隊執行。

四項驗收條件,一項一個測試,只證「行得通」,不掃邊界情況。

測試打的是**本機庫內真實的運行與真實的掃描落檔**——這正是要驗的那件事:
重跑改的是真的參數集,重掃跑的是真的格。庫、運行、掃描或價格快照不在,就
跳過,不用捏一組數頂上(做法照 tests/test_web.py)。

有兩個測試要真的動引擎(改一格重跑、重掃)。引擎要價格快照,快照是可重抓的
數據不入 git,所以在一部剛 clone 的機上會跳過——跳過的是**執行**那一半,
「同取值得同一個編號」與「彈窗預填當前值」兩半照跑,不受影響。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from karst.data.snapshots import snapshot_dir
from karst.web.api_jobs import RERUN_RECIPES, JobContext
from karst.web.data import build_reader
from karst.web.server import STATIC_ROOT, serve_in_background

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def 收拾重掃落檔(seeded_project_root):
    """重掃測試會真的落一幅掃描;測完收拾走,不要每跑一次測試就多一幅。

    KARST-093:落點跟住 reader 由倉根搬去臨時專案根。臨時目錄 session 完自己會
    掉,收拾其實已經多餘,但照留——收拾的那幾行本身寫住一課(見下),而且日後
    有人把落點改回倉內時,收拾還在,不用重新想一次。

    KARST-057:數據目錄重建之前,重掃那個測試因為沒有價格快照永遠跳過,
    所以沒有人見到它會在 ``experiments/重掃/`` 留低垃圾。數據回來之後它
    真的會跑,而落下的目錄會被掃描頁當成一幅正經掃描列出來,一跑一幅。

    收拾刻意逐個檔案刪、刪前核對路徑:2026-08-28 的事故正是一條遞迴刪除
    沿住目錄連結刪落主倉去。
    """
    生出來的: list[Path] = []
    yield 生出來的
    根 = (Path(seeded_project_root) / "experiments" / "重掃").resolve()
    for 目錄 in 生出來的:
        目錄 = Path(目錄).resolve()
        if 目錄.parent != 根 or 目錄.is_symlink() or not 目錄.is_dir():
            continue  # 不是我們認得的那個位,不碰
        for 檔 in 目錄.iterdir():
            if 檔.is_file():
                檔.unlink()
        if not any(目錄.iterdir()):
            目錄.rmdir()


def _get(url: str):
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _post(url: str, payload: dict):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _wait(base_url: str, job_id: str, limit_seconds: float = 900.0):
    """輪詢到有結果為止——前端就是這樣等,測試照跟。"""
    import time

    began = time.time()
    while time.time() - began < limit_seconds:
        status, job = _get(f"{base_url}/api/job?id={urllib.parse.quote(job_id)}")
        assert status == 200, job
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.4)
    raise AssertionError(f"工作 {job_id} 等過 {limit_seconds} 秒仍未有結果")


@pytest.fixture(scope="module")
def reader(seeded_project_root):
    """讀取層接**種好數的臨時專案根**,不是倉根那個生產庫(KARST-093)。

    本檔是整批網頁測試裡最要緊接走的一個:它驗的是「畫面按重跑」,而重跑走的正是
    **正式路徑**——經唯一入口登記一版新參數集、跑引擎、落一次 ``origin='formal'``
    的運行。以前 reader 打倉根那個生產庫,於是每跑一次這個檔,生產庫就多一條正式
    運行,而那一條與人手跑出來的一模一樣,分不出來:正式運行由 12 條變 13 條就是
    這樣來的(KARST-087 交低)。接了臨時庫之後,它照樣真的跑、真的寫,只是寫在
    session 完就掉的臨時目錄裡。
    """
    return build_reader(seeded_project_root)


@pytest.fixture(scope="module")
def base_url(reader):
    httpd, url = serve_in_background(reader)
    try:
        yield url
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture(scope="module")
def sample_run(reader):
    """庫內第一個「重跑做得到」的正式運行。"""
    listing = reader.list_runs(None)
    for item in listing["runs"]:
        record = reader.store.get_run(item["runId"])
        if record.strategy_name in RERUN_RECIPES and record.param_values:
            return record
    pytest.skip(f"庫內未有 {'、'.join(sorted(RERUN_RECIPES))} 這幾套策略的運行")


def _has_prices(reader, snapshot_id: str) -> bool:
    """價格快照的檔案還在不在。不在就跑不動引擎,要動引擎那兩個測試會跳過。

    快照是可重抓的數據,不入 git(D-026 第 5 條),所以一部剛 clone 的機上
    本來就沒有——跳過不是失敗。
    """
    try:
        snapshot_dir(reader.store, snapshot_id, root=JobContext(reader).snapshot_root)
    except Exception:  # noqa: BLE001
        return False
    return True


# ----------------------------------------------------------------------
# 驗收一:重跑彈窗——同取值得同一個編號,改一格得新編號
# ----------------------------------------------------------------------


def test_同取值重跑得回同一個運行編號而且不會再跑一次(base_url, sample_run):
    """驗收一(上半):一格不改就按重跑,得回的是原來那個編號,不會多出一次運行。

    運行編號是內容雜湊,不是跑完才派的流水號:同一組輸入本來就有這一次,就
    沒有第二次可言。這一條是整張票的骨——它若不成立,「重跑」就會變成每按
    一次多一筆一模一樣的紀錄。
    """
    status, job = _post(
        f"{base_url}/api/rerun",
        {
            "runId": sample_run.run_id,
            "cadence": sample_run.rebalance_cadence,
            "values": dict(sample_run.param_values),
        },
    )
    assert status == 202, job          # 收單即走,執行在後端
    done = _wait(base_url, job["jobId"])

    assert done["status"] == "done", done.get("error")
    assert done["runId"] == sample_run.run_id, "同一組取值竟然得出另一個運行編號"
    assert done["reused"] is True, "同一組取值應該沿用原來那次,不應該再跑一次"
    # 一格都沒改,定義庫不應該多一版參數集出來
    assert done["paramSetVersionNo"] == sample_run.param_set_version_no


def test_改一格重跑得出另一個運行編號(base_url, reader, sample_run):
    """驗收一(下半):改一格參數,得出的是**另一個**運行編號,舊運行不改寫。"""
    if not _has_prices(reader, sample_run.snapshot_id):
        pytest.skip(f"價格快照 {sample_run.snapshot_id} 的檔案不在,跑不動引擎")

    # 揀一格數字參數來改:加一,足以改身份,又不會把策略推去跑不出東西
    changed = dict(sample_run.param_values)
    key = next(
        (k for k, v in sorted(changed.items()) if str(v).strip().lstrip("-").isdigit()),
        None,
    )
    if key is None:
        pytest.skip("這個運行沒有一格純整數參數可以改")
    changed[key] = str(int(changed[key]) + 1)

    status, job = _post(
        f"{base_url}/api/rerun",
        {
            "runId": sample_run.run_id,
            "cadence": sample_run.rebalance_cadence,
            "values": changed,
        },
    )
    assert status == 202, job
    done = _wait(base_url, job["jobId"])

    assert done["status"] == "done", done.get("error")
    assert done["runId"] != sample_run.run_id, "改了一格參數,不應該還是同一個編號"
    # 舊運行一個字不改:照樣查得回,取值仍然是舊那一組
    old = reader.store.get_run(sample_run.run_id)
    assert dict(old.param_values) == dict(sample_run.param_values)
    # 新運行真的落了痕,而且是**正式運行**,不是掃描格
    fresh = reader.store.get_run(done["runId"])
    assert dict(fresh.param_values)[key] == changed[key]
    assert fresh.sweep_id is None


# ----------------------------------------------------------------------
# 驗收二:重掃彈窗——改得動掃描格,掃得出新的一幅
# ----------------------------------------------------------------------


@pytest.fixture(scope="module")
def sample_sweep(base_url):
    """本機第一幅「重掃做得到」的掃描。"""
    status, listing = _get(f"{base_url}/api/sweeps")
    assert status == 200, listing
    for item in listing.get("sweeps", []):
        if item.get("error"):
            continue
        code, form = _get(
            f"{base_url}/api/rescan-form?id={urllib.parse.quote(item['id'])}"
        )
        if code == 200 and form.get("supported"):
            return form
    pytest.skip("本機未有任何重掃做得到的掃描落檔")


def test_重掃彈窗每格預填的是當前那幅掃描的取值(sample_sweep):
    """驗收二(上半):彈窗開放得改的正是掃描格,而且每格預填**當前值**。

    彈窗不會反問用戶「這幅掃描本來是怎樣跑的」——驅動器、熱身期、成本、
    快照、期間、引擎全部由那幅掃描自己身上讀回。用戶要改的只有掃描格,
    所以只開放那幾格;每格預填當前那一幅的取值,**那是當前值,不是預設值**。
    """
    assert sample_sweep["controls"], "說得出可以重掃,就要講得出改得動哪幾格"
    for control in sample_sweep["controls"]:
        assert control["name"], "每一格都要有鍵名,後端靠它認得出改了哪一格"
        assert control["label"], "每一格都要有一個人看得懂的標籤"
        assert str(control["value"]).strip(), (
            f"「{control['label']}」沒有預填當前值;彈窗每格必須預填當前那幅掃描的取值"
        )
        assert control["kind"] in ("list", "number")

    # 不變的那幾件要講得出,好讓彈窗寫明「這幾件不變,所以不在這裡改」
    assert sample_sweep["snapshotId"]
    assert sample_sweep["objective"]
    assert sample_sweep["cells"] > 0


def test_重掃改了範圍就掃出一幅新的掃描(base_url, reader, sample_sweep, 收拾重掃落檔):
    """驗收二(下半):改掃描範圍,真的掃得出一幅新的掃描,舊那幅一個字不改。"""
    if not _has_prices(reader, sample_sweep["snapshotId"]):
        pytest.skip(f"價格快照 {sample_sweep['snapshotId']} 的檔案不在,跑不動引擎")

    controls = {c["name"]: str(c["value"]) for c in sample_sweep["controls"]}
    # 揀一條列軸縮短一格:格少了,掃得快,而且證明範圍真的改得動
    trimmed = None
    for control in sample_sweep["controls"]:
        if control["kind"] == "list":
            items = [p.strip() for p in str(control["value"]).split("、") if p.strip()]
            if len(items) > 2:
                controls[control["name"]] = "、".join(items[:2])
                trimmed = control["name"]
                break
    if trimmed is None:
        pytest.skip("這幅掃描沒有一條夠長的列軸可以縮短")

    before = {p.name for p in (PROJECT_ROOT / "experiments").rglob("掃描表.csv")}

    status, job = _post(
        f"{base_url}/api/rescan",
        {"sweepId": sample_sweep["sweepId"], "controls": controls},
    )
    assert status == 202, job
    done = _wait(base_url, job["jobId"])

    assert done["status"] == "done", done.get("error")
    assert done["sweepId"] != sample_sweep["sweepId"], "重掃應該另開一幅,不是改寫舊那幅"
    assert done["cells"] > 0

    # 新那幅真的落了檔,而且讀得回
    out_dir = PROJECT_ROOT / done["sweepId"]
    收拾重掃落檔.append(out_dir)  # 斷言照做,做完收拾走(見 fixture)
    assert (out_dir / "掃描表.csv").is_file(), "新掃描要有自己的掃描表"
    assert (out_dir / "summary.json").is_file()
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["rescan_of"] == sample_sweep["sweepId"], "新掃描要指得回它由哪一幅重掃而來"

    # 舊那幅一個字不改
    code, again = _get(
        f"{base_url}/api/rescan-form?id={urllib.parse.quote(sample_sweep['sweepId'])}"
    )
    assert code == 200
    assert again["cells"] == sample_sweep["cells"]
    assert before  # 掃描落檔目錄本來就有東西,不是空跑一場


# ----------------------------------------------------------------------
# 驗收三:全部登記經唯一入口,karst verify 仍然清白
# ----------------------------------------------------------------------


def test_重跑重掃的寫入全部經唯一入口(reader):
    """驗收三:網頁殼寫入之後,全庫核對仍然揪不出繞過唯一入口的寫入。

    ``verify`` 揪的正是「有東西入了庫但沒有經過唯一入口」。重跑與重掃是整個
    網頁殼唯一會寫庫的一層,它若自己開一條路寫進去,這裡就會亮。
    """
    from karst.gateway import Gateway

    with Gateway.open(str(JobContext(reader).db_path)) as gateway:
        findings = gateway.verify()
    assert not findings, "全庫核對揪到繞過唯一入口的寫入:\n" + "\n".join(
        str(f) for f in findings
    )


def test_網頁殼只有這一層寫得到庫():
    """寫入只有一條路:``api_jobs`` 這一層。其餘 api_* 只讀。

    這一條看的是原始碼,不是行為——寫入路徑一多,「經唯一入口」就守不住,
    而且多數是無心加的。
    """
    web = PROJECT_ROOT / "karst" / "web"
    writers = []
    for path in sorted(web.glob("api_*.py")):
        if path.name == "api_jobs.py":
            continue
        text = path.read_text(encoding="utf-8")
        for needle in ("Gateway.open", "register_param_set", "record_simulation"):
            if needle in text:
                writers.append(f"{path.name} 用了 {needle}")
    assert not writers, "只有 api_jobs 可以寫庫,這幾處自己開了路:" + "、".join(writers)


# ----------------------------------------------------------------------
# 規矩:不設預設值、執行在後端排隊
# ----------------------------------------------------------------------


def test_參數交漏一格或留空一律拒收而不會替你補一個數(base_url, sample_run):
    """本平台不設參數預設值(D-008 第 3 條):彈窗預填的是當前值,不是預設值。

    所以交上來那一份必須是完整的一組。少一格、多一格、留空一格,一律當場
    拒收——**不會**替你補一個數再跑,那樣跑出來的成績沒有人講得出是誰的取值。
    """
    full = dict(sample_run.param_values)
    key = sorted(full)[0]

    short = dict(full)
    short.pop(key)
    status, resp = _post(
        f"{base_url}/api/rerun",
        {"runId": sample_run.run_id, "cadence": sample_run.rebalance_cadence,
         "values": short},
    )
    assert status == 400 and key in resp["error"]

    extra = dict(full)
    extra["這格根本不存在"] = "1"
    status, resp = _post(
        f"{base_url}/api/rerun",
        {"runId": sample_run.run_id, "cadence": sample_run.rebalance_cadence,
         "values": extra},
    )
    assert status == 400 and "這格根本不存在" in resp["error"]

    blank = dict(full)
    blank[key] = "   "
    status, resp = _post(
        f"{base_url}/api/rerun",
        {"runId": sample_run.run_id, "cadence": sample_run.rebalance_cadence,
         "values": blank},
    )
    assert status == 400 and key in resp["error"]

    # 換倉節奏一樣是參數集的一部分,一樣無預設值
    status, resp = _post(
        f"{base_url}/api/rerun",
        {"runId": sample_run.run_id, "cadence": "", "values": full},
    )
    assert status == 400

    # 查無此運行是 404,不是伺服器壞
    status, resp = _post(
        f"{base_url}/api/rerun",
        {"runId": "run-沒有這一個", "cadence": "daily", "values": {"a": "1"}},
    )
    assert status == 404


def test_執行在後端排隊前端只輪詢(base_url, sample_run):
    """下單即走(202),執行在後端一條工作執行緒上排隊,前端靠輪詢問進度。

    引擎一跑動輒幾分鐘。若果在 HTTP 請求裡面跑,瀏覽器早就斷線,而且第二個
    人一按就兩個回測搶同一個庫。所以下單只入隊,查進度另開一條。
    """
    body = {
        "runId": sample_run.run_id,
        "cadence": sample_run.rebalance_cadence,
        "values": dict(sample_run.param_values),
    }
    status, first = _post(f"{base_url}/api/rerun", body)
    assert status == 202
    assert first["status"] in ("queued", "running")
    assert first["jobId"]

    done = _wait(base_url, first["jobId"])
    assert done["status"] == "done", done.get("error")
    assert done["submittedAt"] and done["startedAt"] and done["finishedAt"]

    # 工作清單查得到,亦講得出現時忙不忙
    status, listing = _get(f"{base_url}/api/jobs?limit=5")
    assert status == 200
    assert any(j["jobId"] == first["jobId"] for j in listing["jobs"])
    assert "busy" in listing

    # 查一件不存在的工作是 404
    status, _ = _get(f"{base_url}/api/job?id={urllib.parse.quote('job-沒有這一件')}")
    assert status == 404


def test_兩個彈窗照原型的形而且不掛假數據():
    """彈窗照 KARST-015 原型:同一個標題、同一塊血統。頁內不准有寫死的數據。"""
    run_page = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    assert 'id="rerun-modal"' in run_page
    assert "以現版本重跑" in run_page
    assert 'id="rerun-body"' in run_page

    sweep_page = (STATIC_ROOT / "sweep.html").read_text(encoding="utf-8")
    assert 'id="rescan-modal"' in sweep_page
    assert "以現版本重掃" in sweep_page
    assert 'id="rescan-body"' in sweep_page

    # 彈窗內容一律由 /api/ 取,頁內不掛任何數據檔
    for page in (run_page, sweep_page):
        assert "data.js" not in page
        assert "data-ext.js" not in page
        assert "proto-badge" not in page
