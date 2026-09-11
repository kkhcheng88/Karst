# -*- coding: utf-8 -*-
"""KARST-213 批 2:衝擊前文件節錄器。

用法:
  python 節錄.py <E??> <TICKER> [組名] [每條命中數]
逐條關鍵詞掃該家公司衝擊前的 10-K 與 10-Q,每個命中印
  命中位置 ±窗 的文字 + 最近一個「Item X」標題。

組名:battery(預設,步四八條通用)/ bank / food / device / semi / power / solar
      / hospital / social
"""
import json
import os
import re
import sys

B2 = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①v3全量回測/批2"
DOCS = B2 + "/docs"

KW = {
    "客戶集中": [r"one customer", r"largest customer", r"customer accounted for",
               r"no customer", r"customers accounted for"],
    "合約與取消": [r"[Cc]ontract termination", r"terminate (?:the|this|for) [A-Za-z]* ?[Aa]greement",
                r"without cause", r"remaining performance obligation",
                r"annual recurring", r"backlog", r"order book"],
    "定價": [r"price increase", r"pricing", r"list price", r"discount", r"rebate"],
    "競爭": [r"[Cc]ompetition", r"competitors", r"compete "],
    "收入重複": [r"subscription", r"recurring revenue", r"renewal rate",
              r"retention rate", r"same-store", r"organic (?:net )?(?:sales|revenue) growth"],
    "管理層應對": [r"cost (?:reduction|savings|efficiencies)", r"restructuring",
                r"efficienc(?:y|ies) (?:program|initiative|plan)", r"headcount"],
    # 銀行
    "存款": [r"uninsured deposits", r"deposit(?:s)? (?:decreased|increased|outflow)", r"deposit beta",
           r"brokered deposits"],
    "證券帳面": [r"available-for-sale", r"held-to-maturity", r"accumulated other comprehensive",
              r"unrealized loss"],
    "貸款組合": [r"commercial real estate", r"multi-family", r"CRE concentration",
              r"loan-to-value", r"office portfolio"],
    "資本比率": [r"Tier 1", r"capital ratio", r"leverage ratio"],
    "利率風險": [r"interest rate risk", r"net interest margin", r"asset sensitivity"],
    "帳面值": [r"book value per (?:common )?share", r"tangible book value", r"total stockholders.? equity",
             r"total shareholders.? equity"],
    # 食品飲料
    "銷量": [r"volume (?:decline|declined|decrease|growth)", r"organic volume",
           r"price/mix", r"elasticity"],
    "減肥藥": [r"GLP-1", r"weight loss", r"obesity", r"semaglutide", r"Wegovy", r"Ozempic"],
    # 醫療器械
    "報銷": [r"reimbursement", r"coverage (?:policy|decision)", r"Medicare", r"payer"],
    "產品": [r"continuous glucose", r"sensor", r"apnea", r"mask", r"patient"],
    # 半導體
    "超大規模": [r"hyperscale", r"customers? (?:in|such as) (?:cloud|data center)",
             r"data center (?:revenue|demand)", r"accelerated computing"],
    "出口管制": [r"export control", r"U\.S\. government", r"licens(?:e|ing) requirement"],
    "存貨": [r"inventor(?:y|ies) (?:write|level|reserve)", r"supply (?:constraint|commitment)",
           r"purchase commitment"],
    # 電力/數據中心設備
    "訂單": [r"orders", r"backlog", r"pipeline", r"capacity expansion"],
    # 太陽能
    "政策補貼": [r"investment tax credit", r"production tax credit", r"ITC", r"Section 48",
              r"net metering", r"net energy metering"],
    "關稅": [r"tariff", r"trade case", r"anti-dumping", r"countervailing"],
    "稅務股本": [r"tax equity", r"investment fund", r"third-party (?:owner|financing)"],
    # 醫院與保險
    "覆蓋與補貼": [r"exchange (?:subsid|coverage)", r"Affordable Care Act", r"ACA",
                r"Medicaid", r"uncompensated care", r"disproportionate share"],
    "病人量": [r"admissions", r"adjusted admissions", r"same-hospital", r"patient days",
            r"health plan membership"],
    # 社交平台
    "用戶": [r"daily active users", r"monthly active users", r"DAU", r"MAU", r"engagement"],
    "廣告": [r"average price per ad", r"ad impressions", r"advertisers", r"ad pricing"],
    "監管": [r"regulat(?:ion|ory)", r"privacy", r"data protection", r"FTC", r"consent decree"],
}

GROUPS = {
    "battery": ["客戶集中", "合約與取消", "定價", "競爭", "收入重複", "管理層應對"],
    "bank": ["存款", "證券帳面", "貸款組合", "資本比率", "利率風險"],
    "food": ["減肥藥", "銷量", "定價", "競爭", "收入重複"],
    "device": ["減肥藥", "報銷", "產品", "定價", "客戶集中", "競爭"],
    "semi": ["超大規模", "客戶集中", "存貨", "定價", "出口管制", "競爭"],
    "power": ["訂單", "客戶集中", "超大規模", "定價", "競爭"],
    "solar": ["政策補貼", "關稅", "稅務股本", "客戶集中", "定價"],
    "hospital": ["覆蓋與補貼", "病人量", "定價", "關稅", "競爭"],
    "social": ["用戶", "廣告", "監管", "競爭", "定價"],
    "mgmt": ["管理層應對", "定價", "競爭"],
}


def snippet(text, pos, win=420):
    a = max(0, pos - win // 3)
    b = min(len(text), pos + win)
    seg = re.sub(r"\s+", " ", text[a:b]).strip()
    head = ""
    m = None
    for m2 in re.finditer(r"(?i)\bItem\s+\d+[A-Z]?\b", text[:pos]):
        m = m2
    if m:
        head = re.sub(r"\s+", " ", text[m.start():m.start() + 70]).strip()
    return head, seg


def scan(path, cats, per=2, win=420):
    if not path or not os.path.exists(path):
        return [("(檔案缺)", "")]
    text = open(path, encoding="utf-8", errors="ignore").read()
    out = []
    for cat in cats:
        for k in KW[cat]:
            n = 0
            for m in re.finditer(k, text):
                head, seg = snippet(text, m.start(), win)
                out.append((cat, "%s ⟦%s⟧" % (seg, head)))
                n += 1
                if n >= per:
                    break
    return out


def main():
    eid, tk = sys.argv[1], sys.argv[2]
    grp = sys.argv[3] if len(sys.argv) > 3 else "battery"
    per = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    spec = json.load(open("%s/%s_%s_docs.json" % (DOCS, eid, tk), encoding="utf-8"))
    cats = GROUPS.get(grp, GROUPS["battery"])
    print("=== %s %s cutoff=%s group=%s ===" % (eid, tk, spec["cutoff"], grp))
    for d in spec["docs"]:
        if not d.get("path"):
            print("[%s %s] %s" % (d["form"], d.get("filingDate", ""), d.get("status")))
            continue
        print("\n----- %s %s %s -----" % (d["form"], d.get("filingDate"), d["accession"]))
        for cat, seg in scan(d["path"], cats, per):
            print("  <#%s> %s" % (cat, seg))


if __name__ == "__main__":
    main()
