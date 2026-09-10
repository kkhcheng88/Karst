# -*- coding: utf-8 -*-
"""KARST-209 步驟四(判桶半):人讀原句之後落桶。

`extract_fee_model.py` 找句、`probe_fee.py` 補漏,**判桶由人做**——本檔只是把
人的判斷寫成表,並由**原檔原文**取回那句證據(不靠人手轉抄,免抄錯)。

桶:席位 / 用量或交易 / 資產或存戶 / 混合 / 授權或永久 / 其他 / 查不到。
證據句只在 `fee_candidates.csv`(准許語式命中)與 `fee_probe.csv`(闊網)兩份原文
裡找;**找不到就標查不到,不猜**——判桶不准靠「我知這家公司怎樣收錢」。

每一格寫法:(桶, 搜尋鍵, 備註)。搜尋鍵在原文句內出現即取該句。
"""
import csv
import io

OUT = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①SaaS籃子重定義"

# (代號: 桶, 搜尋鍵, 備註)
PICK = {
    "PANW": ("混合", "per-user, per-endpoint, or capacity-based", "席位與用量並列(防火牆訂閱)"),
    "CRWD": ("用量或交易", "priced on a per-endpoint and per-module basis", "按端點數與模組數"),
    "FTNT": ("混合", "hardware products and software licensing", "硬件、授權與訂閱並行"),
    "MSFT": ("混合", "number of users licensed and applications consumed", "按授權用戶數與消耗"),
    "PLTR": ("混合", "subscription-based or usage-based pricing structures", "訂閱與用量兩種並存"),
    "CSCO": ("混合", "perpetual licenses and subscription arrangements, as well as hardware", "授權、訂閱與硬件"),
    "CRM": ("訂閱(未標明計量)", "paying subscriptions at each of our customers", "原文只說訂閱,未講按什麼計"),
    "ORCL": ("用量或交易", "consumption-based pricing in order to help organizations", "按資源消耗"),
    "AVGO": ("混合", "upfront license revenue", "硬件(半導體)加授權"),
    "NET": ("混合", "a base subscription and a smaller portion based on usage or per seat", "底價訂閱加席位或用量"),
    "NOW": ("混合", "consumption-based pricing component", "訂閱為主,超額部分按消耗"),
    "OKTA": ("訂閱(未標明計量)", "subscription-based business model, which constituted", "未講計量"),
    "DDOG": ("用量或交易", "Usage is measured on a per-unit basis", "按自訂單位用量"),
    "ZS": ("席位", "primarily calculated on a per-user basis", "按用戶"),
    "ADBE": ("混合", "renew monthly on-premise term-based licenses", "訂閱與定期授權並存"),
    "RBRK": ("混合", "perpetual licenses with associated maintenance contracts", "永久授權轉訂閱中"),
    "FFIV": ("混合", "perpetual, subscription, and usage-based consumption models", "三種模式並列"),
    "INTU": ("查不到", None, "10-K 全文掃不到任何收費語"),
    "GEN": ("用量或交易", "optional Turbo Fee", "按每筆墊款收費"),
    "DT": ("用量或交易", "consumes that commitment based on actual usage", "承諾額內按實際用量"),   # noqa: E501
    "CDNS": ("混合", "we collect royalties as our customers ship their product", "定期授權加出貨抽成"),
    "APP": ("其他", "variability in the pricing of advertising", "廣告競價,非軟件收費"),
    "SNPS": ("混合", "network licenses that allow a number of individual users", "授權加按使用人數"),
    "AKAM": ("用量或交易", "usage-based contracts with no committed contract", "按用量"),
    "ANET": ("查不到", None, "10-K 只講運費入收入,掃不到收費模式語"),
    "CHKP": ("查不到", None, "倉內無 10-K 全文(外國私人發行人交 20-F)"),
    "NTAP": ("混合", "subscription arrangements, ratably over the subscription period", "訂閱加消費制"),
    "FROG": ("混合", "usage-based fees in excess of the minimum usage commitment", "底價訂閱加超額用量"),
    "LDOS": ("其他", "The price for a FFP contract is often determined", "政府服務合約計價,非軟件收費"),
    "ACN": ("混合", "fee-per-transaction contracts", "顧問合約按期、按件、按成交"),
    "HO.FP": ("查不到", None, "倉內無 10-K 全文(法國申報)"),
    "ESTC": ("用量或交易", "consumption-based arrangements for our Elastic Cloud offerings", "按消耗"),
    "GOOGL": ("用量或交易", "average amount we charge advertisers for each engagement", "按點擊與曝光收費"),
    "INFY": ("查不到", None, "倉內無 10-K 全文(外國私人發行人交 20-F)"),
    "MSTR": ("混合", "Sales and usage-based royalties", "授權加按銷量抽成"),
    "ADSK": ("混合", "transition from developing and selling perpetual licenses", "永久授權轉訂閱"),
    "IBM": ("查不到", None, "快取的 10-K 全文為 XBRL 標籤,掃不到自然語句"),
    "S": ("用量或交易", "per agent basis, and each agent generally corresponds", "按 agent(對應端點)"),
    "ROP": ("用量或交易", "transactional and volume-based fees", "按件與按量"),
    "WDAY": ("席位", "based on the size of our customers’ employee headcount", "按員工人數"),
    "BAH": ("其他", "We generate revenue through various fixed price and multi-year government contracts",
            "政府服務合約計價,非軟件收費"),
    "TTWO": ("其他", "the method by which we charge our customers", "遊戲銷售與內購,非軟件訂閱"),
    "QLYS": ("查不到", None, "10-K 全文掃不到任何收費語"),
    "VRNS": ("混合", "Maintenance and support associated with a term license subscription", "定期授權加訂閱"),
    "CVLT": ("查不到", None, "10-K 只講按件付給第三方的專利費,未講自己怎樣收費"),
    "BB": ("混合", "sales-based or usage-based royalty promised in exchange for a license", "授權加抽成"),
    "TEAM": ("混合", "on-premises term license agreements", "雲訂閱加數據中心授權"),
    "4704.JP": ("查不到", None, "倉內無 10-K 全文(日本申報)"),
    "SAIC": ("其他", "reimbursable costs, award and incentive fees, usage-based fees", "政府服務合約計價"),
    "ZM": ("訂閱(未標明計量)", "Our business is subscription based", "原文只說訂閱,未講計量"),
    # OTEX.CN 是多倫多報價場,本身無 10-K 快取;同一家公司,證據取 OTEX 那份
    "OTEX.CN": ("混合", "perpetual license sales to subscription-based business model",
                "永久授權轉訂閱(同一家公司,證據取 OTEX 的 10-K)", "OTEX"),
    "FICO": ("用量或交易", "plus estimates of future usage-based fees", "按用量(評分次數)"),
    "TENB": ("混合", "to a lesser extent, perpetual licenses",
             "訂閱與永久授權並存"),
    "NTNX": ("訂閱(未標明計量)", "transition to a subscription-based business model", "轉訂閱中,未講計量"),
    "FSLY": ("用量或交易", "The majority of our revenue is usage based", "按用量"),
    "PTC": ("混合", "Compared to a perpetual license model, our subscription model", "永久授權轉訂閱"),
    "U": ("混合", "based on a fixed fee or consumption-based model", "固定費加用量"),
    "IOT": ("訂閱(未標明計量)", "We offer subscriptions to access our Connected Operations Platform",
            "原文只說訂閱,未講計量"),
    "TYL": ("混合", "Transaction-based fees", "SaaS 訂閱加按件收費"),
    "BMNR": ("查不到", None, "快取的 10-K 是賣股與挖礦年代的舊申報,掃不到收費模式語"),
    "TRMB": ("混合", "Software including perpetual licenses is recognized upon delivery",
             "永久授權加訂閱"),
    "GWRE": ("資產或存戶", "based on the amount of Direct Written Premium", "按平台上保單保額"),
    "DOCU": ("混合", "transaction-based add-ons", "按用戶訂閱加按件附加"),
    "HUBS": ("混合", "seats-based and consumption-based pricing model changes", "席位與用量並存"),
    "MANH": ("查不到", None, "10-K 掃不到收費語"),
    "NTCT": ("查不到", None, "10-K 掃不到收費語"),
    "ATEN": ("混合", "as well as pay-as-y", "硬件加授權與訂閱加按用量"),
    "HUT": ("用量或交易", "overage and consumption-based services", "按用量"),
    "IDCC": ("用量或交易", "the per-unit structure of the related license agreements", "專利授權按件"),
    "ZD": ("用量或交易", "usage-based fees", "按用量"),
    "AUR": ("查不到", None, "10-K 掃不到收費語"),
    "RIOT": ("查不到", None, "10-K 掃不到收費語"),
    "WULF": ("查不到", None, "10-K 掃不到收費語"),
    "GTLB": ("查不到", None, "10-K 掃不到收費語"),
    "PCOR": ("其他", "we do not charge a per-seat or per-user fee",
             "原文只明言**不**按席位/用戶,未講按什麼計"),
    "DSGX": ("查不到", None, "倉內無 10-K 全文(加拿大申報)"),
    "QBTS": ("查不到", None, "10-K 只有 ASC 606 通用語,未講收費模式"),
    "ZETA": ("用量或交易", "A substantial portion of our revenue is derived from usage-based pricing",
             "按用量"),
    "PATH": ("混合", "term license portion of Flex Offerings", "定期授權加 SaaS"),
    "CORZ": ("用量或交易", "consumption-based contracts for its digital asset hosted mining",
             "按消耗(託管算力)"),
    "SNAP": ("其他", "average revenue per user, or ARPU, as quarterly revenue divided",
             "原文只給每人平均收入(廣告),未講收費模式"),
    "OTEX": ("混合", "perpetual license sales to subscription-based business model", "永久授權轉訂閱"),
    "CIFR": ("查不到", None, "10-K 掃不到收費語"),
    "CRCL": ("用量或交易", "usage-based, volume-based, or event-driven transactions", "按用量與成交量"),   # noqa: E501
    "ACIW": ("用量或交易", "capacity overages that are accounted for as a usage-based royalty", "按超量"),
    "RNG": ("混合", "recurring fixed plan subscription fees, variable usage-based fees", "定額加用量"),
    "DBX": ("訂閱(未標明計量)", "derives its revenue from subscription fees", "原文只說訂閱費,未講計量"),
    "APPF": ("用量或交易", "usage-based services", "按用量"),
    "BSY": ("混合", "standard offerings are usage based with monetization", "按用量計費"),
    "TTAN": ("用量或交易", "per unit basis which may vary by product", "按件(每技師每月)"),
    "BOX": ("席位", "including the number of users", "按用戶數"),
    "MARA": ("查不到", None, "10-K 掃不到收費語(加密貨幣挖礦)"),
    "BILL": ("混合", "fixed monthly rate per user for subscriptions as well as transaction fees",
             "按用戶定額加按件"),
    "YOU": ("混合", "transaction fees (charged per use or per user)", "按次或按用戶"),
    "RDWR": ("查不到", None, "倉內無 10-K 全文(以色列申報)"),
    "WK": ("查不到", None, "10-K 掃不到收費語"),
    "CCC": ("用量或交易", "fees are solely based on transaction volume", "按成交量"),
    "NCNO": ("訂閱(未標明計量)", "fees from customers for accessing our solutions",
             "原文只說使用費,未講計量"),
    "QTWO": ("席位", "contractual price per user", "按用戶"),
    "DLB": ("用量或交易", "per unit royalty arrangement whereby they pay us for each unit they sell",
            "按件抽成"),
    "LIF": ("混合", "monthly subscription to access location tracking services", "硬件加月度訂閱"),
    "CLSK": ("查不到", None, "10-K 掃不到收費語(加密貨幣挖礦)"),
    "PEGA": ("訂閱(未標明計量)", "Our clients largely prefer subscription-based offerings",
             "原文只說訂閱,未講計量"),
    "ATO.FP": ("查不到", None, "倉內無 10-K 全文(法國申報)"),
    "ADEA": ("席位", "monthly per-subscriber fee", "按訂戶"),
    "BRZE": ("查不到", None, "10-K 掃不到收費語"),
    "SPSC": ("訂閱(未標明計量)", "Revenue for subscription-based services is recognized on a ratable basis",
             "原文只說訂閱,未講計量"),
    "ALRM": ("席位", "per subscriber basis for access to our non-hosted software platform", "按訂戶"),
    "AGYS": ("用量或交易", "rates per location, including rates per points of sale and per room",
             "按場點/房間數"),
    "SOUN": ("混合", "fixed fees, usage-based revenue, revenue per query or revenue per user",
             "定額加用量與席位"),
    "TDC": ("用量或交易", "ranging from capacity-based to consumption-based pricing", "按容量與消耗"),
    "FRSH": ("訂閱(未標明計量)", "from our subscription and professional services arrangements",
             "原文只說訂閱加服務,未講計量"),
    "KVYO": ("查不到", None,
             "10-K 只講按交易量付給信用卡處理商的**成本**,未講自己按什麼收費(前半版誤判,已改)"),
    "FIVN": ("混合", "fixed fee per agent seat", "按席位定額加用量"),
    "RAMP": ("用量或交易", "transactional usage-based arrangements", "按用量"),
    "INTA": ("席位", "based on the number of users adopting our solution", "按使用人數"),
    "AVPT": ("混合", "SaaS, term license and support and maintenance", "SaaS 加定期授權"),
    "PRGS": ("混合", "sold as perpetual licenses, but certain products also use term licensing",
             "永久授權加定期授權加訂閱"),
    "BLKB": ("用量或交易", "transaction-based payment processing fees", "按交易"),
    "ALKT": ("席位", "per-registered-user pricing model", "按登記用戶"),
    "BL": ("用量或交易", "capture additional revenue as our customers", "按用量"),
    "NN": ("用量或交易", "based on the quantity of usage", "按用量與出貨件數"),
    "APPN": ("席位", "sell our software on a per-user basis", "按用戶"),
    "AI": ("用量或交易", "customers either pay a monthly fee and consumption charges", "按用量"),
    "LSPD": ("查不到", None, "倉內無 10-K 全文(加拿大申報)"),
    "VYX": ("混合", "term-based software license arrangements", "定期授權加服務"),
    "PD": ("席位", "offered on a per-user basis", "按用戶"),
    "VERX": ("用量或交易", "tiered transaction-based pricing model", "按交易"),
    "ASAN": ("席位", "tiered, seat-based model", "按席位"),
    "AIP": ("用量或交易", "Royalties are calculated either as a percentage of the revenues", "按件抽成"),
    "CXM": ("混合", "licensed on a per-user basis as well as products that are licensed based on different tiers of volume",
            "席位加用量分級"),
}


def load():
    """回 {代號: [(出處, 句)]};候選在前、闊網在後。"""
    idx = {}
    for r in csv.DictReader(open(f"{OUT}/fee_candidates.csv", encoding="utf-8-sig")):
        for k in ("候選一", "候選二", "候選三"):
            if r[k]:
                idx.setdefault(r["代號"], []).append(("10-K 收費語式命中", r[k]))
    for r in csv.DictReader(open(f"{OUT}/fee_probe.csv", encoding="utf-8-sig")):
        idx.setdefault(r["代號"], []).append(("10-K 收入確認附註", r["句"]))
    return idx


def main():
    idx = load()
    man = {}
    for r in csv.DictReader(open(f"{OUT}/fee_candidates.csv", encoding="utf-8-sig")):
        if r["申報日"]:
            man[r["代號"]] = (r["申報日"], r["accession"])

    rows, bad = [], []
    for t, spec in PICK.items():
        bucket, key, note = spec[0], spec[1], spec[2]
        src = spec[3] if len(spec) > 3 else t       # 證據來源代號(預設自己)
        sent = ""
        if key:
            for where, s in idx.get(src, []):
                if key.lower() in s.lower():
                    sent = s
                    break
            if not sent:
                bad.append(t)
        fd, acc = man.get(src, ("", ""))
        rows.append({"代號": t, "收費模式": bucket, "證據句": sent, "備註": note,
                     "申報日": fd, "accession": acc})

    order = [r["ticker"] for r in
             csv.DictReader(open(f"{OUT}/constituents.csv", encoding="utf-8-sig"))]
    rank = {t: i for i, t in enumerate(order)}
    rows.sort(key=lambda r: rank.get(r["代號"], 999))

    with open(f"{OUT}/收費模式.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["代號", "收費模式", "證據句", "備註",
                                          "申報日", "accession"])
        w.writeheader()
        w.writerows(rows)

    # 人看的版本
    from collections import Counter
    dist = Counter(r["收費模式"] for r in rows)
    with open(f"{OUT}/收費模式.md", "w", encoding="utf-8") as f:
        f.write("# KARST-209 新籃子收費模式(逐家一句證據)\n\n")
        f.write("判準(票面第四步):**只用該公司自己的申報原文**,每家一句;"
                "判不到就標查不到,不猜。桶:席位 / 用量或交易 / 資產或存戶 / 混合 / "
                "授權或永久 / 其他 / 查不到。\n\n")
        f.write("證據句取原文**照抄**(由 `fee_candidates.csv` 與 `fee_probe.csv` 取回,"
                "不經人手轉抄),出處為該家 10-K 的申報日與 accession。\n\n")
        f.write("## 分佈\n\n| 桶 | 家數 |\n|---|---|\n")
        for k, v in dist.most_common():
            f.write(f"| {k} | {v} |\n")
        f.write(f"\n合計 **{len(rows)}** 家。\n\n")
        f.write("## 逐家\n\n")
        for b in ["席位", "用量或交易", "資產或存戶", "混合", "授權或永久", "其他", "查不到"]:
            grp = [r for r in rows if r["收費模式"] == b]
            if not grp:
                continue
            f.write(f"### {b}({len(grp)} 家)\n\n")
            for r in grp:
                f.write(f"- **{r['代號']}**")
                if r["備註"]:
                    f.write(f" —— {r['備註']}")
                f.write("\n")
                if r["證據句"]:
                    f.write(f"  > {r['證據句']}\n")
                    f.write(f"  > 出處:10-K 申報日 {r['申報日']},`{r['accession']}`\n")
            f.write("\n")
    print("分佈:", dict(dist))
    if bad:
        print("!! 有桶但找不回證據句,要修搜尋鍵:", bad)
    else:
        print("全部有桶者都取回證據句")


if __name__ == "__main__":
    main()
