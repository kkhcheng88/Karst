"""砌代號→實體的帶生效期對照表,並對照現有快照列出錨改變了的代號(KARST-082 第一至三步)。

跑法(倉根)::

    python experiments/2026-08-29-ticker-history/build_anchors.py

四件事,次序寫死:

  1. **備妥三份來源** —— 今日的 ``company_tickers.json``(代號→CIK,只講今日)、
     ``cik-lookup-data.txt``(名稱→CIK,保留歷史名)、逐個 CIK 的 ``submissions``
     (名稱窗口帶 from/to)。全部落 ``data/sec/`` 快取,重跑不再打 SEC。
  2. **逐段成分期裁決** —— 規則住在 ``karst.data.ticker_history.resolve_anchor``,
     這裡只負責備料與落檔。成分期取自宇宙名單登記,只收與快照窗口重疊那幾段。
  3. **落對照表** —— ``karst/data/universes/sp500_ticker_anchors.csv``,每列一段生效期。
  4. **對照現有快照** —— 與 ``2026-08-28-493fd1df1cb9`` 的 manifest 逐個代號比,
     錨改變清單與人手待辨清單分開落檔。

SEC 要求來訪者在 User-Agent 自報身分與聯絡方法,並限每秒十次;本檔兩樣都守。
"""

from __future__ import annotations

import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from karst.data.cik import fetch_cik_map, is_placeholder  # noqa: E402
from karst.data.ticker_history import (  # noqa: E402
    VERDICT_MANUAL,
    VERDICT_PLACEHOLDER,
    VERDICT_RECYCLED,
    AnchorInputs,
    fetch_cik_lookup,
    fetch_entity_history,
    load_name_index,
    names_adopted_after,
    normalise_company_name,
    resolve_anchor,
    write_anchor_table,
)
from karst.data.universe import SP500_MEMBERSHIP  # noqa: E402

USER_AGENT = "Karst backtesting research karsoncheng@casy.hk"
REQUEST_TIMEOUT = 60.0
REQUEST_PAUSE = 0.15  # SEC 限每秒十次;留一截餘裕

BASE_SNAPSHOT = "2026-08-28-493fd1df1cb9"
WINDOW_START = "2015-01-02"
WINDOW_END = "2026-08-28"

SEC_CACHE = REPO_ROOT / "data" / "sec"
LOOKUP_FILE = SEC_CACHE / "cik-lookup-data.txt"
SUBMISSIONS_CACHE = SEC_CACHE / "submissions"
TICKER_MAP_CACHE = SEC_CACHE / "company_tickers.json"

ANCHOR_TABLE = REPO_ROOT / "karst" / "data" / "universes" / "sp500_ticker_anchors.csv"
OUT_DIR = Path(__file__).resolve().parent
CHANGED_FILE = OUT_DIR / "anchor-changes.csv"
MANUAL_FILE = OUT_DIR / "manual-review.csv"

_last_call = [0.0]


def throttled(call, *args, **kwargs):
    """守住 SEC 每秒十次的上限。"""
    gap = time.monotonic() - _last_call[0]
    if gap < REQUEST_PAUSE:
        time.sleep(REQUEST_PAUSE - gap)
    try:
        return call(*args, **kwargs)
    finally:
        _last_call[0] = time.monotonic()


def today_ticker_map() -> dict[str, str]:
    """今日的代號→CIK。抓過即存快取,重跑用同一份,免得對照表隨日子飄。"""
    if TICKER_MAP_CACHE.exists() and TICKER_MAP_CACHE.stat().st_size > 0:
        return json.loads(TICKER_MAP_CACHE.read_text(encoding="utf-8"))
    mapping = throttled(fetch_cik_map, user_agent=USER_AGENT, timeout=REQUEST_TIMEOUT)
    TICKER_MAP_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TICKER_MAP_CACHE.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    return mapping


def snapshot_universe() -> dict[str, dict]:
    path = REPO_ROOT / "data" / "snapshots" / BASE_SNAPSHOT / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return {row["ticker"]: row for row in manifest["universe"]}


def spans_of(ticker: str) -> list[tuple[str, str, str]]:
    """一個代號與快照窗口重疊的成分期,回 ``(加入日, 剔除日, 公司名)``。"""
    out = []
    for period in SP500_MEMBERSHIP:
        if period.ticker != ticker:
            continue
        if period.joined_on > WINDOW_END:
            continue
        if period.left_on and period.left_on < WINDOW_START:
            continue
        out.append((period.joined_on, period.left_on, period.display_name))
    return sorted(out)


def main() -> int:
    universe = snapshot_universe()
    companies = {t: row for t, row in universe.items() if row["entity_kind"] == "company"}
    print(f"快照 {BASE_SNAPSHOT}:{len(universe)} 個實體,其中上市公司 {len(companies)} 個")

    print("備妥名稱→CIK 表(cik-lookup-data.txt)…")
    throttled(fetch_cik_lookup, path=LOOKUP_FILE, user_agent=USER_AGENT, timeout=REQUEST_TIMEOUT)
    name_index = load_name_index(LOOKUP_FILE)
    print(f"  正規化名稱 {len(name_index)} 條")

    ticker_map = today_ticker_map()
    print(f"今日代號→CIK 對照 {len(ticker_map)} 條")

    # 只有成分期已結束那批要查名稱窗口:未結束的代號一路連到今日,沒有易主的空間。
    work: list[tuple[str, str, str, str]] = []
    for ticker in sorted(companies):
        for joined_on, left_on, display_name in spans_of(ticker):
            work.append((ticker, joined_on, left_on, display_name))
    closed = {ticker for ticker, _, left_on, _ in work if left_on}
    need = sorted({ticker_map[t] for t in closed if t in ticker_map})
    print(f"成分期 {len(work)} 段;已結束的代號 {len(closed)} 個,要查名稱窗口的 CIK {len(need)} 個")

    histories: dict[str, object] = {}
    for index, cik in enumerate(need, start=1):
        histories[cik] = throttled(
            fetch_entity_history,
            cik,
            cache_dir=SUBMISSIONS_CACHE,
            user_agent=USER_AGENT,
            timeout=REQUEST_TIMEOUT,
        )
        if index % 25 == 0:
            print(f"  已查 {index}/{len(need)}")

    # 第二輪:凡今日持有人在成分期之後改過名,把同名的其他 CIK 也查一次,
    # 好讓裁決那一步有得比。候選由名稱表反查,不是憑空猜。
    candidates: set[str] = set()
    for ticker, joined_on, left_on, _ in work:
        if not left_on:
            continue
        cik = ticker_map.get(ticker)
        history = histories.get(cik) if cik else None
        if history is None:
            continue
        for adopted in names_adopted_after(history, day=left_on):
            key = normalise_company_name(adopted)
            candidates.update(c for c in name_index.get(key, ()) if c != cik)
    candidates -= set(histories)
    print(f"同名候選 CIK {len(candidates)} 個,逐個查名稱窗口…")
    for index, cik in enumerate(sorted(candidates), start=1):
        try:
            histories[cik] = throttled(
                fetch_entity_history,
                cik,
                cache_dir=SUBMISSIONS_CACHE,
                user_agent=USER_AGENT,
                timeout=REQUEST_TIMEOUT,
            )
        except Exception as error:  # 候選查不到就當它不存在,裁決那邊自然判「人手待辨」
            print(f"  {cik} 查不到:{error}")
        if index % 25 == 0:
            print(f"  已查 {index}/{len(candidates)}")

    anchors = []
    for ticker, joined_on, left_on, display_name in work:
        cik = ticker_map.get(ticker, "")
        anchors.append(
            resolve_anchor(
                AnchorInputs(
                    ticker=ticker,
                    display_name=display_name,
                    joined_on=joined_on,
                    left_on=left_on,
                    today_cik=cik,
                    today_history=histories.get(cik),
                    candidate_histories=histories,
                    name_index=name_index,
                )
            )
        )
    write_anchor_table(ANCHOR_TABLE, anchors)
    print(f"對照表 {len(anchors)} 列 → {ANCHOR_TABLE}")

    # ---- 對照現有快照 ----
    by_ticker: dict[str, list] = defaultdict(list)
    for anchor in anchors:
        by_ticker[anchor.ticker].append(anchor)

    changed, manual = [], []
    for ticker in sorted(companies):
        was = companies[ticker]["anchor"]
        was_label = "佔位錨" if is_placeholder(was) else was
        for anchor in by_ticker.get(ticker, ()):
            now = anchor.cik or "(佔位錨)"
            if anchor.verdict in (VERDICT_MANUAL, VERDICT_PLACEHOLDER):
                manual.append(
                    {
                        "ticker": ticker,
                        "membership": f"{anchor.valid_from}~{anchor.valid_to or '仍在名單上'}",
                        "current_anchor": was_label,
                        "verdict": anchor.verdict,
                        "reason": anchor.evidence,
                    }
                )
            # 兩邊都以「有沒有真 CIK」為準:舊錨是佔位、新錨也判不出,那是原地踏步;
            # 舊錨是真 CIK 而新錨判定它不可能是當時的持有人(改用佔位),那是**改變**——
            # 由一個錯的十位數字退回「未知」,正是本票要做的事,不可以不算數。
            was_real = not is_placeholder(was)
            same = (was_real and anchor.cik == was) or (not was_real and not anchor.cik)
            if not same:
                changed.append(
                    {
                        "ticker": ticker,
                        "membership": f"{anchor.valid_from}~{anchor.valid_to or '仍在名單上'}",
                        "from_anchor": was_label,
                        "to_anchor": now,
                        "verdict": anchor.verdict,
                        "evidence": anchor.evidence,
                    }
                )

    with CHANGED_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["ticker", "membership", "from_anchor", "to_anchor", "verdict", "evidence"],
        )
        writer.writeheader()
        writer.writerows(changed)
    with MANUAL_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["ticker", "membership", "current_anchor", "verdict", "reason"],
        )
        writer.writeheader()
        writer.writerows(manual)

    recycled = [row for row in changed if row["verdict"] == VERDICT_RECYCLED]
    print(f"錨改變 {len(changed)} 個代號(其中判定代號回收 {len(recycled)} 個)→ {CHANGED_FILE}")
    print(f"人手待辨 {len(manual)} 個代號 → {MANUAL_FILE}")
    for row in recycled:
        print(f"  回收 {row['ticker']} {row['membership']}:{row['from_anchor']} → {row['to_anchor']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
