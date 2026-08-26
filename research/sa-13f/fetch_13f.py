# -*- coding: utf-8 -*-
"""
KARST-019: 抓取 Situational Awareness LP(CIK 2045724)全部 13F-HR 申報明細,
產出 research/sa-13f/holdings.csv 與輔助資料。

用法(Windows PowerShell):
    $env:PYTHONUTF8=1; python fetch_13f.py

邏輯:
1. 呼叫 SEC submissions API 取得該 CIK 完整申報清單,篩出 form == '13F-HR'
   (或 '13F-HR/A',如有修訂版會標記但一併保留在 filings_list 供人工核對)。
   注意:本基金目前(2026-08-27 查證)全部 13F-HR 皆為正本,無 /A 修訂版。
2. 對每筆 accession,先抓 EDGAR 目錄索引頁(.../Archives/edgar/data/{cik}/{accession-nodash}/),
   從目錄清單裡挑出「非 primary_doc.xml、非 -index、非 .txt」的 XML 檔,
   該檔即為 information table(SEC 官方標準檔名 form13fInfoTable.xml,
   但各申報代理人常自訂檔名,例如本基金歷史上用過
   SALP_13FQ425.xml / salp13fq1xml.xml / SALP13finfotableQ3.xml /
   Salpform13fq2.xml / SALP13fq1.xml / infotable.xml / form13fInfoTable.xml)。
3. 解析 information table XML(namespace 為 SEC eFTS 13F 標準 schema),
   取出每個 <infoTable> 的 issuer、cusip、value(千美元)、shares、put/call。
4. 匯總全部期別,計算每期加總市值與各持倉占比,並用 CUSIP(找不到 CUSIP 對應時退回用
   issuer 名稱正規化字串)比對上一期,推算 change_vs_prev。
5. 輸出 holdings.csv。

已知限制(詳見 README.md「查不到/有疑點」一節):
- ticker 欄位僅在腳本內建的少量對照表(TICKER_MAP)命中時才填,其餘留空,
  不做無根據的臆測。
- value 單位判斷:SEC 表格說明書規定 <value> 應以千美元為單位,但實測核對
  本基金 7 期申報後確認該欄位實際就是美元金額本身(未乘 1000)——
  詳見 parse_infotable() 內註解與核對依據。本腳本「不」對 value 做 ×1000。
- CUSIP 比對用來判斷「新增/加倉/減倉/清倉/不變」,同一發行人若跨期換過 CUSIP
  (例如公司行動)本腳本无法自動識別,會被誤判為「新增」+「清倉」兩筆,
  人工整理階段已對照 issuer 名稱做二次檢查,結果詳見 README。
"""

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict

HEADERS = {"User-Agent": "Karst Research karsoncheng@casy.hk"}
CIK = "2045724"
SUBMISSIONS_URL = f"https://data.sec.gov/submissions/CIK000{CIK}.json"

OUT_DIR = "C:/projects/Karst/research/sa-13f"

# 期間對應表:reportDate -> period 標籤(YYYYQn)
def period_label(report_date: str) -> str:
    y, m, _ = report_date.split("-")
    m = int(m)
    q = (m - 1) // 3 + 1
    return f"{y}Q{q}"


# 少量已知 ticker 對照(僅在有把握時填,查不到就留空,不臆測)。
# 對照依據為 Karst 自身既有市場知識(非另外查證的官方來源),僅收錄有把握、
# 長期掛牌、名稱不會混淆的公司;新上市/名稱可能對應多檔商品(如 VanEck ETF
# Trust 底下有多檔不同 ETF 共用同一發行人名稱)一律不填,留待人工核對。
TICKER_MAP = {
    "sandisk corp": "SNDK",
    "micron technology inc": "MU",
    "bloom energy corp": "BE",
    "taiwan semiconductor mfg co ltd": "TSM",
    "taiwan semiconductor mfg ltd": "TSM",
    "taiwan semiconductor manufacturing co ltd": "TSM",
    "taiwan semiconductor manufac": "TSM",
    "nebius group n v": "NBIS",
    "nebius group nv": "NBIS",
    "nebius group n.v.": "NBIS",
    "marvell technology inc": "MRVL",
    "vistra corp": "VST",
    "vertiv holdings co": "VRT",
    "talen energy corp": "TLN",
    "constellation energy corp": "CEG",
    "modine mfg co": "MOD",
    "intel corp": "INTC",
    "broadcom inc": "AVGO",
    "onto innovation inc": "ONTO",
    "eqt corp": "EQT",
    "coreweave inc": "CRWV",
    "core scientific inc new": "CORZ",
    "applied digital corp": "APLD",
    "iren limited": "IREN",
    "nvidia corporation": "NVDA",
    "galaxy digital inc.": "GLXY",
    "cipher mining inc": "CIFR",
    "riot platforms inc": "RIOT",
    "lumentum hldgs inc": "LITE",
    "solaris energy infras inc": "SEI",
    "tower semiconductor ltd": "TSEM",
    "hut 8 corp": "HUT",
    "western digital corp": "WDC",
    "coherent corp": "COHR",
    "bitdeer technologies group": "BTDR",
    "seagate technology hldngs pl": "STX",
    "kilroy rlty corp": "KRC",
    "power solutions intl inc": "PSIX",
    "cleanspark inc": "CLSK",
    "bitfarms ltd": "BITF",
    "liberty energy inc": "LBRT",
    "infosys ltd": "INFY",
    "propetro hldg corp": "PUMP",
    "babcock & wilcox enterprises": "BW",
    "oracle corp": "ORCL",
    "advanced micro devices inc": "AMD",
    "asml hldg nv n y registry": "ASML",
    "corning inc": "GLW",
    "hive digital technologies lt": "HIVE",
    "stmicroelectronics": "STM",
    "vishay intertechnology inc": "VSH",
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return r.read()


def get_13f_filings():
    data = json.loads(fetch(SUBMISSIONS_URL).decode("utf-8"))
    recent = data["filings"]["recent"]
    n = len(recent["form"])
    out = []
    for i in range(n):
        form = recent["form"][i]
        if form.startswith("13F-HR"):
            out.append({
                "form": form,
                "accession": recent["accessionNumber"][i],
                "filed_date": recent["filingDate"][i],
                "report_date": recent["reportDate"][i],
            })
    # SEC 回傳由新到舊,反轉成由舊到新方便算 change_vs_prev
    out.sort(key=lambda x: x["report_date"])
    return out


def find_infotable_filename(accession: str) -> str:
    nodash = accession.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{nodash}/"
    html = fetch(url).decode("utf-8", errors="replace")
    files = re.findall(r'href="([^"]+)"', html)
    candidates = [
        f.split("/")[-1] for f in files
        if nodash in f and f.lower().endswith(".xml")
        and "primary_doc" not in f.lower()
    ]
    if not candidates:
        raise RuntimeError(f"找不到 information table XML: {accession}")
    # 通常只有一個候選;若多於一個,挑檔名含 info/table 的
    for c in candidates:
        if "info" in c.lower() or "table" in c.lower():
            return c
    return candidates[0]


def parse_infotable(xml_bytes: bytes):
    root = ET.fromstring(xml_bytes)
    # namespace 可能是 http://www.sec.gov/edgar/document/thirteenf/informationtable
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    rows = []
    for it in root.findall(f"{ns}infoTable"):
        def gt(tag):
            el = it.find(f"{ns}{tag}")
            return el.text.strip() if el is not None and el.text else ""

        issuer = gt("nameOfIssuer")
        cusip = gt("cusip")
        value_raw = gt("value")
        shares_el = it.find(f"{ns}shrsOrPrnAmt/{ns}sshPrnamt")
        shares = shares_el.text.strip() if shares_el is not None and shares_el.text else "0"
        put_call_el = it.find(f"{ns}putCall")
        put_call = put_call_el.text.strip() if put_call_el is not None and put_call_el.text else ""

        # 重要:SEC 13F 表格說明書規定 <value> 應以「千美元」為單位申報,
        # 但實測核對本基金全部 7 期申報後發現:該欄位實際填寫的就是「美元金額本身」
        # (未乘以 1000)。核對依據:
        #   1. 用已知的外部核實數字核對 ——Q2 2026 期總市值加總後得約 202.4 億美元,
        #      與 research/2026-08-27-sa-fund-status.md 記載的第三方轉述數字
        #      (約 202.4 億美元)一致,且首五大持倉占比(SanDisk 28.0%、
        #      Micron 27.5%、Bloom Energy 9.4%、TSM 6.3%、Nebius 6.1%)與該檔
        #      逐一吻合。若依規定把 <value> 當「千美元」再乘以 1000,總市值會
        #      變成約 202.4 億美元的 1000 倍(約 20.24 兆美元),明顯離譜。
        #   2. 逐檔用「value / shares」推算隱含每股價格,結果落在合理股價區間
        #      (例如 2024Q4 Marvell 隱含 $110.45/股、2025Q1 Intel 隱含
        #      $22.71/股),若額外乘以 1000 則變成天文數字,不合理。
        # 因此本腳本刻意「不」把 <value> 乘以 1000,直接視為美元金額。
        # 這代表本基金(或其申報代理人)在 <value> 欄位的填寫方式與 SEC 表格
        # 說明書字面規定不同,已在 README.md「有疑點」一節註明。
        rows.append({
            "issuer": issuer,
            "cusip": cusip,
            "value_usd": int(round(float(value_raw))),
            "shares": int(float(shares)),
            "put_call": put_call,
        })
    return rows


# 已知的 CUSIP 對照問題:同一家公司在不同期別被基金/代理人填成不同 CUSIP
# (多半是把選擇權/權證用的 9 碼 CUSIP 誤填到普通股列,或單純打字有出入)。
# 逐筆比對股數與市值變化幅度後,判斷以下都是「同一持倉、CUSIP 填寫不一致」,
# 而非真的清倉又新開倉,故做別名對照,合併計入同一條時間序列。
# 對照依據:見 README.md「有疑點」一節逐筆列出的股數/金額比對過程。
CUSIP_ALIASES = {
    "093712AH0": "093712107",  # Bloom Energy Corp:2025Q3 誤填 -> 2025Q4 起改為正確普通股 CUSIP
    "55024UAD1": "55024U109",  # Lumentum Holdings Inc:同上
    "17253JAA4": "17253J106",  # Cipher Mining Inc:同上
}


def normalize_issuer(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def main():
    filings = get_13f_filings()
    print(f"共找到 {len(filings)} 筆 13F-HR 申報:")
    for f in filings:
        print(" ", f["form"], f["accession"], "filed", f["filed_date"], "period", f["report_date"])

    all_periods = []  # list of dict: period info + rows
    for f in filings:
        infotable_name = find_infotable_filename(f["accession"])
        nodash = f["accession"].replace("-", "")
        xml_url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{nodash}/{infotable_name}"
        print(f"抓取 {f['accession']} 的 information table: {xml_url}")
        xml_bytes = fetch(xml_url)
        rows = parse_infotable(xml_bytes)
        # 同一 issuer+cusip 可能因 put/call 拆多筆,先按 (cusip, put_call) 分別列,
        # 但股數/市值合計時若同一 cusip 出現多筆(常見於 put/call 分行),
        # change_vs_prev 比對用 cusip 彙總後的股數與市值。
        all_periods.append({
            **f,
            "period": period_label(f["report_date"]),
            "infotable_url": xml_url,
            "rows": rows,
        })

    with open(f"{OUT_DIR}/filings_list.json", "w", encoding="utf-8") as fp:
        json.dump(
            [{k: v for k, v in p.items() if k != "rows"} for p in all_periods],
            fp, ensure_ascii=False, indent=2,
        )

    # 依期別排序(已經是舊到新)
    prev_by_cusip = {}  # cusip -> (shares, issuer)
    csv_lines = ["period,filed_date,issuer,ticker,cusip,shares,value_usd,weight_pct,change_vs_prev"]

    for p in all_periods:
        rows = p["rows"]
        # 按 cusip 彙總(同一 cusip 若有多筆 put/call 分錄,加總 shares/value)
        agg = defaultdict(lambda: {"issuer": "", "shares": 0, "value_usd": 0})
        for r in rows:
            cusip = CUSIP_ALIASES.get(r["cusip"], r["cusip"])
            key = cusip or normalize_issuer(r["issuer"])
            agg[key]["issuer"] = r["issuer"]
            agg[key]["shares"] += r["shares"]
            agg[key]["value_usd"] += r["value_usd"]

        total_value = sum(v["value_usd"] for v in agg.values())

        cur_by_cusip = {}
        for cusip, v in agg.items():
            cur_by_cusip[cusip] = (v["shares"], v["issuer"])

        for cusip, v in sorted(agg.items(), key=lambda kv: -kv[1]["value_usd"]):
            issuer = v["issuer"]
            shares = v["shares"]
            value_usd = v["value_usd"]
            weight_pct = round(value_usd / total_value * 100, 4) if total_value else 0

            ticker = TICKER_MAP.get(normalize_issuer(issuer), "")

            if cusip in prev_by_cusip:
                prev_shares, _ = prev_by_cusip[cusip]
                diff = shares - prev_shares
                if diff == 0:
                    change = "不變"
                elif prev_shares == 0:
                    change = f"加倉(+{diff}股)"
                elif diff > 0:
                    change = f"加倉(+{diff}股)"
                else:
                    change = f"減倉({diff}股)"
            else:
                change = "新增(首次揭露)"

            cusip_disp = cusip if re.match(r"^[A-Z0-9]{6,9}$", cusip) else cusip
            issuer_csv = issuer.replace(",", ";")
            ticker_csv = ticker
            change_csv = change.replace(",", ";")

            csv_lines.append(
                f'{p["period"]},{p["filed_date"]},"{issuer_csv}",{ticker_csv},{cusip_disp},'
                f'{shares},{value_usd},{weight_pct},"{change_csv}"'
            )

        # 找出上一期有、這一期沒有的 cusip -> 清倉
        # (在寫下一期之前處理,故這裡先記錄,實際寫入延後到下一輪期首;
        #  簡化做法:直接在這裡把清倉列也加進本期輸出,標記為「清倉」)
        cleared = set(prev_by_cusip.keys()) - set(cur_by_cusip.keys())
        for cusip in cleared:
            prev_shares, prev_issuer = prev_by_cusip[cusip]
            issuer_csv = prev_issuer.replace(",", ";")
            ticker = TICKER_MAP.get(normalize_issuer(prev_issuer), "")
            csv_lines.append(
                f'{p["period"]},{p["filed_date"]},"{issuer_csv}",{ticker},{cusip},'
                f'0,0,0,"清倉(-{prev_shares}股)"'
            )

        prev_by_cusip = cur_by_cusip

    with open(f"{OUT_DIR}/holdings.csv", "w", encoding="utf-8", newline="\n") as fp:
        fp.write("\n".join(csv_lines) + "\n")

    print(f"寫入 {OUT_DIR}/holdings.csv,共 {len(csv_lines)-1} 列持倉/變動紀錄")


if __name__ == "__main__":
    main()
