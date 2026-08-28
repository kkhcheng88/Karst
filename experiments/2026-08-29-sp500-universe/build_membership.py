"""砌「標普 500 歷史成分」的成分歷史表(KARST-065 第一步與第二步)。

輸入兩個免費來源,輸出一份 CSV 落 ``karst/data/universes/sp500_historical.csv``,
即宇宙名單登記那一份正本:

  1. **fja05680/sp500**(MIT 授權)——逐次變動的成分歷史,覆蓋 1996-01-02 ~ 2026-06-30。
     用它的 ``sp500_ticker_start_end.csv``:一列一段成分期(代號、加入日、剔除日)。
  2. **維基百科 List of S&P 500 companies**——只有**現役**名單,用來補第一個來源
     2026-06-30 之後那兩個月的尾巴,並提供公司名。

研究檔 research/2026-08-29-alpha158-feasibility.md 第四節列的是 teddykoker/
survivorship-free-spy;核實結果是它的 constituents.csv 止於 2019-04-29(見
README.md 第一節),補不到本倉要的窗口,故改用上面第一個來源。

跑法(倉根)::

    python experiments/2026-08-29-sp500-universe/build_membership.py

原始檔下載到 scratchpad(暫存,不入倉);出來的 CSV 才是正本。
"""

from __future__ import annotations

import csv
import html as html_module
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = REPO_ROOT / "karst" / "data" / "universes" / "sp500_historical.csv"

FJA_BASE = "https://raw.githubusercontent.com/fja05680/sp500/master/"
FJA_START_END = "sp500_ticker_start_end.csv"
WIKI_API = (
    "https://en.wikipedia.org/w/api.php?action=parse"
    "&page=List_of_S%26P_500_companies&prop=text&format=json&formatversion=2"
)
USER_AGENT = "Karst-research/1.0 (karsoncheng@casy.hk)"

# 代號寫法:兩個來源用 BRK.B / BF.B,行情來源(yfinance)用 BRK-B / BF-B。
# 本倉一律收行情來源那個寫法——登記上的代號要與抓得到日線的那個字串同一個。
TICKER_REWRITES = {"BRK.B": "BRK-B", "BF.B": "BF-B"}

SOURCE_FJA = "fja05680/sp500"
SOURCE_WIKI = "wikipedia"

NOTE_WIKI_ADD = (
    "fja05680 的成分歷史止於 2026-06-30,本行由維基百科現役名單(2026-08-29 抓)補回;"
    "加入日期取維基百科的 Date added"
)
NOTE_WIKI_DROP = (
    "維基百科 2026-08-29 的現役名單已無此代號,但 fja05680 止於 2026-06-30 記它仍在;"
    "剔除日期落在 2026-07-01 與 2026-08-29 之間,確實日子不詳"
)


def fetch(url: str, timeout: float = 180.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def cache_path(scratch: Path, name: str) -> Path:
    scratch.mkdir(parents=True, exist_ok=True)
    return scratch / name


def load_fja(scratch: Path) -> list[dict[str, str]]:
    path = cache_path(scratch, "fja_start_end.csv")
    if not path.exists():
        path.write_bytes(fetch(FJA_BASE + urllib.parse.quote(FJA_START_END)))
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_wikipedia(scratch: Path) -> list[dict[str, str]]:
    """維基百科現役名單:代號、公司名、加入日期。"""
    path = cache_path(scratch, "wiki_sp500.html")
    if not path.exists():
        payload = json.loads(fetch(WIKI_API, timeout=60).decode("utf-8"))
        path.write_text(payload["parse"]["text"], encoding="utf-8")
    html = path.read_text(encoding="utf-8")
    table = re.search(r"id=.constituents.*?</table>", html, re.S)
    if table is None:
        raise SystemExit("維基百科那一頁找不到成分表(id=constituents),頁面結構改了")
    rows: list[dict[str, str]] = []
    for chunk in re.findall(r"<tr>(.*?)</tr>", table.group(0), re.S):
        # 只收資料列(``<td>``);表頭那一列是 ``<th>``,一齊收就會多出一個叫
        # 「Symbol」的假代號——第一版正是這樣多出一個成分。
        cells = re.findall(r"<td[^>]*>(.*?)\n?</td>", chunk, re.S)
        if len(cells) < 7:
            continue
        plain = [html_module.unescape(re.sub(r"<[^>]+>", "", cell)).strip() for cell in cells]
        rows.append({"ticker": plain[0], "name": plain[1], "date_added": plain[5]})
    if not 480 <= len(rows) <= 520:
        raise SystemExit(f"維基百科解析到 {len(rows)} 行,不像一份完整的標普 500 名單")
    return rows


def rewrite(ticker: str) -> str:
    ticker = ticker.strip().upper()
    return TICKER_REWRITES.get(ticker, ticker)


def build() -> list[dict[str, str]]:
    scratch = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else Path.home()
        / "AppData/Local/Temp/claude/C--projects-Karst"
        / "d2e5d32d-fb0a-455e-a4f0-b5414e1a7c69/scratchpad"
    )
    fja = load_fja(scratch)
    wiki = load_wikipedia(scratch)

    names = {rewrite(row["ticker"]): row["name"] for row in wiki}
    wiki_now = set(names)
    fja_now = {rewrite(row["ticker"]) for row in fja if not row["end_date"].strip()}

    rows: list[dict[str, str]] = []
    for row in fja:
        ticker = rewrite(row["ticker"])
        note = ""
        if not row["end_date"].strip() and ticker not in wiki_now:
            note = NOTE_WIKI_DROP
        rows.append(
            {
                "ticker": ticker,
                "display_name": names.get(ticker, ""),
                "joined_on": row["start_date"].strip(),
                "left_on": row["end_date"].strip(),
                "source": SOURCE_FJA,
                "note": note,
            }
        )

    for ticker in sorted(wiki_now - fja_now):
        joined = next(row["date_added"] for row in wiki if rewrite(row["ticker"]) == ticker)
        rows.append(
            {
                "ticker": ticker,
                "display_name": names[ticker],
                "joined_on": joined,
                "left_on": "",
                "source": SOURCE_WIKI,
                "note": NOTE_WIKI_ADD,
            }
        )

    rows.sort(key=lambda row: (row["ticker"], row["joined_on"]))
    return rows


def main() -> int:
    rows = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["ticker", "display_name", "joined_on", "left_on", "source", "note"]
        )
        writer.writeheader()
        writer.writerows(rows)

    tickers = {row["ticker"] for row in rows}
    still_in = [row for row in rows if not row["left_on"]]
    print(f"成分期 {len(rows)} 段、唯一代號 {len(tickers)} 個")
    print(f"  仍在市(來源記為未剔除)  {len(still_in)} 個")
    print(f"  最早加入日期            {min(row['joined_on'] for row in rows)}")
    print(f"  最後剔除日期            {max(row['left_on'] for row in rows if row['left_on'])}")
    print(f"  有公司名                {sum(1 for row in rows if row['display_name'])} 段")
    print(f"落點 {OUT_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
