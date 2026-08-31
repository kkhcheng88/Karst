"""KARST-121 樣本驗證:SPDR 行業 ETF 的歷史持股,在 SEC 拿不拿得到、拿得到幾遠。

要答的一條事實:自己砌行業層倍數,分子(市值)靠本倉價格快照,分母(盈利)靠 EDGAR,
中間欠的是「當日這個行業由哪些股票組成」。State Street 官網那個每日持股檔只有今日一份
(本票查過 Wayback,無任何歷史存檔),所以歷史成分要另找——答案是 SEC 的申報。

十一隻 SPDR 行業 ETF 全部屬同一個信託:SELECT SECTOR SPDR TRUST,CIK 1064641。
它的持股申報一路有:早年 N-Q(季度)、N-CSR/N-CSRS(半年/全年),2019 年起 NPORT-P。
每一份都有申報日期,所以是天然的 point-in-time——不存在事後重述。

跑法(Windows PowerShell):
    $env:PYTHONUTF8 = "1"; python probe_edgar_sector_holdings.py

輸出:edgar_sector_holdings_coverage.json(小檔,入 git)
"""

from __future__ import annotations

import json
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# SEC 要求每個請求帶可辨識的聯絡方式(官方免費、不需鑰匙、每秒不超過十次請求,D-041)
USER_AGENT = "Karst research kaho.career@gmail.com"

SECTOR_SPDR_TRUST_CIK = "0001064641"

# 帶持股明細的申報型別
HOLDINGS_FORMS = ("NPORT-P", "NPORT-EX", "N-Q", "N-Q/A", "N-CSR", "N-CSRS", "N-30D")


def fetch_submissions(cik: str) -> dict:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def summarise(payload: dict) -> dict:
    recent = payload["filings"]["recent"]
    forms = recent["form"]
    dates = recent["filingDate"]

    by_form = {}
    for form in HOLDINGS_FORMS:
        idx = [i for i, f in enumerate(forms) if f == form]
        if not idx:
            continue
        by_form[form] = {
            "count": len(idx),
            "newest_filing_date": dates[idx[0]],
            "oldest_filing_date": dates[idx[-1]],
        }

    return {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "entity_name": payload.get("name"),
        "cik": SECTOR_SPDR_TRUST_CIK,
        "note": (
            "每一份申報都帶申報日期(filingDate),知情時點由它決定,不用重述後數字——"
            "這正是 point-in-time 的定義。本摘要只數申報份數與日期範圍,未解析持股明細。"
        ),
        "holdings_filings_in_recent_index": by_form,
        "all_forms_in_recent_index": dict(Counter(forms).most_common()),
        "older_index_files": payload["filings"].get("files", []),
    }


def main() -> None:
    payload = fetch_submissions(SECTOR_SPDR_TRUST_CIK)
    result = summarise(payload)
    out_path = Path(__file__).parent / "edgar_sector_holdings_coverage.json"
    out_path.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"實體:{result['entity_name']}(CIK {result['cik']})")
    for form, info in result["holdings_filings_in_recent_index"].items():
        print(
            f"  {form:<10} {info['count']:>4} 份　"
            f"{info['oldest_filing_date']} ~ {info['newest_filing_date']}"
        )
    for older in result["older_index_files"]:
        print(f"  更早的索引檔:{older['filingFrom']} ~ {older['filingTo']}(共 {older['filingCount']} 份)")
    print(f"落檔:{out_path}")


if __name__ == "__main__":
    main()
