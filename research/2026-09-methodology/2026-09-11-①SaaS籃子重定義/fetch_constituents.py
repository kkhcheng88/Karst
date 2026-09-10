# -*- coding: utf-8 -*-
"""KARST-209 步驟一:IGV + CIBR 成分股。

來源次序(依票面):
1. 倉內 data/ 與 library/ —— 已 Glob 查過,無 IGV/CIBR 持股檔。
2. 發行商網站:
   - IGV(iShares Expanded Tech-Software Sector ETF)
     舊 `.ajax?fileType=csv` 端點已失效(回 HTML,非 CSV)。
     現行端點是產品頁自己的 `<product-path>/latest-holdings.csv`,頁內連結為憑。
   - CIBR(First Trust NASDAQ Cybersecurity ETF)
     `EtfHoldings.aspx?Ticker=CIBR` 的持股表在頁內 HTML;匯出 Excel 走 __doPostBack,不用。
3. web.archive.org —— 試一次得 HTTP 429,依票面放棄。
4. 兩個來源都只有**今日**持股(iShares 自報 as of 2026-09-08、First Trust as of 2026-09-09),
   取不到衝擊日(2026-01)快照,故本表是「今日成分」,偏差方向寫在總覽。

輸出:
- `sources/IGV_holdings.csv` / `sources/CIBR_holdings.html`(原始檔,連抓取時間與網址)
- `constituents.csv`(去重合併後的名單:每家屬哪隻 ETF、權重)
"""
import csv
import re
import subprocess
import sys
from datetime import datetime, timezone

OUT = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①SaaS籃子重定義"
SRC = f"{OUT}/sources"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

IGV_URL = ("https://www.ishares.com/us/products/239771/"
           "ishares-north-american-techsoftware-etf/latest-holdings.csv")
CIBR_URL = "https://www.ftportfolios.com/Retail/Etf/EtfHoldings.aspx?Ticker=CIBR"


def curl(url, dest):
    """抓一個 URL 落檔;回傳 (http_code, size)。"""
    r = subprocess.run(
        ["curl", "-sL", "-A", UA, "-m", "60", url, "-o", dest,
         "-w", "%{http_code} %{size_download}"],
        capture_output=True, text=True)
    parts = r.stdout.strip().split()
    return (parts[0] if parts else "?", parts[1] if len(parts) > 1 else "0")


def parse_igv(path):
    """iShares csv:頭幾行是基金資料,之後才是 'Ticker,Name,...,Weight (%)' 長表。"""
    rows = []
    asof = None
    with open(path, encoding="utf-8-sig", newline="") as f:
        lines = f.read().splitlines()
    header_i = None
    for i, ln in enumerate(lines):
        if ln.startswith("Fund Holdings as of"):
            asof = ln.split(",", 1)[1].strip().strip('"')
        if ln.startswith("Ticker,"):
            header_i = i
            break
    if header_i is None:
        return rows, asof
    for rec in csv.DictReader(lines[header_i:]):
        tk = (rec.get("Ticker") or "").strip().strip('"')
        if not tk or tk == "-":
            continue
        if (rec.get("Asset Class") or "").strip('"') != "Equity":
            continue
        rows.append({
            "ticker": tk,
            "name": (rec.get("Name") or "").strip().strip('"'),
            "weight": float((rec.get("Weight (%)") or "0").strip('"') or 0),
        })
    return rows, asof


def parse_cibr(path):
    """First Trust:持股表是頁內第 6 個 <table>(前五個是導覽與摘要)。"""
    h = open(path, encoding="utf-8", errors="replace").read()
    asof = None
    m = re.search(r"as of\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})", h, re.I)
    if m:
        asof = m.group(1)
    tabs = re.findall(r"<table.*?</table>", h, re.S | re.I)
    tbl = None
    for t in tabs:
        if "Security Name" in t and "Weighting" in t:
            tbl = t
            break
    if tbl is None:
        return [], asof
    rows = []
    for r in re.findall(r"<tr.*?</tr>", tbl, re.S | re.I):
        cells = [re.sub(r"\s+", " ", re.sub("<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<t[hd].*?</t[hd]>", r, re.S | re.I)]
        if len(cells) < 7 or cells[0] == "Security Name":
            continue
        tk = cells[1]
        # 非股票列:匯率/現金/其他(Classification = Other,或無代號)
        if not tk or tk.startswith("$") or cells[3] == "Other":
            continue
        rows.append({
            "ticker": tk,
            "name": cells[0],
            "weight": float(cells[6].rstrip("%") or 0),
        })
    return rows, asof


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    igv_path, cibr_path = f"{SRC}/IGV_holdings.csv", f"{SRC}/CIBR_holdings.html"
    print("IGV ", curl(IGV_URL, igv_path))
    print("CIBR", curl(CIBR_URL, cibr_path))

    igv, igv_asof = parse_igv(igv_path)
    cibr, cibr_asof = parse_cibr(cibr_path)
    print(f"IGV {len(igv)} 家 (as of {igv_asof});CIBR {len(cibr)} 家 (as of {cibr_asof})")

    merged = {}
    for r in igv:
        m = merged.setdefault(r["ticker"], {"ticker": r["ticker"], "name": r["name"],
                                            "in_igv": 0, "in_cibr": 0,
                                            "igv_weight": 0.0, "cibr_weight": 0.0})
        m["in_igv"], m["igv_weight"] = 1, r["weight"]
    for r in cibr:
        m = merged.setdefault(r["ticker"], {"ticker": r["ticker"], "name": r["name"],
                                            "in_igv": 0, "in_cibr": 0,
                                            "igv_weight": 0.0, "cibr_weight": 0.0})
        m["in_cibr"], m["cibr_weight"] = 1, r["weight"]
        if not m["name"]:
            m["name"] = r["name"]

    rows = sorted(merged.values(), key=lambda x: -(x["igv_weight"] + x["cibr_weight"]))
    for r in rows:
        r["etf"] = ("IGV+CIBR" if r["in_igv"] and r["in_cibr"]
                    else ("IGV" if r["in_igv"] else "CIBR"))
        r["weight_sum"] = round(r["igv_weight"] + r["cibr_weight"], 2)

    with open(f"{OUT}/constituents.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "name", "etf", "in_igv", "in_cibr",
                                          "igv_weight", "cibr_weight", "weight_sum"])
        w.writeheader()
        w.writerows(rows)

    with open(f"{OUT}/sources/來源.md", "w", encoding="utf-8") as f:
        f.write("# 成分股來源(KARST-209)\n\n")
        f.write(f"抓取時間(UTC):**{now}**\n\n")
        f.write("| ETF | 網址 | 自報 as of | 原始檔 | 家數(股票) |\n|---|---|---|---|---|\n")
        f.write(f"| IGV | {IGV_URL} | {igv_asof} | `sources/IGV_holdings.csv` | {len(igv)} |\n")
        f.write(f"| CIBR | {CIBR_URL} | {cibr_asof} | `sources/CIBR_holdings.html` | {len(cibr)} |\n\n")
        f.write("**兩隻都只有今日持股,取不到 2026-01 衝擊日快照。** 依票面第 4 條,"
                "本籃是「今日成分」;web.archive.org 試一次得 HTTP 429,依票面放棄。\n\n")
        f.write("iShares 舊 `.ajax?fileType=csv&fileName=<T>_holdings&dataType=fund` 端點"
                "今日回 HTML 不是 CSV(已試三種參數組合並帶 cookie 與 XHR 標頭),"
                "現行端點是產品頁內的 `<product-path>/latest-holdings.csv`。\n")
    print("合併後", len(rows), "家")
    print("ETF 分佈:", {k: sum(1 for r in rows if r["etf"] == k)
                       for k in ("IGV+CIBR", "IGV", "CIBR")})


if __name__ == "__main__":
    main()
