# -*- coding: utf-8 -*-
"""KARST-197:前瞻預測登記表加備註欄。

**既有預測一字不改。** 只做兩件事:
  1. 表加一欄「備註(KARST-197)」——記兩件事:這一項若成真,支不支持買入(D-173
     暫定規則第四件要數的就是這一格);以及數字基礎已經更正。
  2. 表之前加一段說明,講清楚備註欄怎樣讀、由誰判。

支不支持買入是**主 agent 判定**,不是用戶裁決,亦不是子隊原判——原表沒有這一格。
判準:該項預測若成真,是站在「錯價會被糾正」那一邊(指引維持或上調、收入與利潤率
不失守、去槓桿、內部人買入),還是站在「空方論點成立」那一邊(指引下調、利潤率
轉差、稀釋、集中度風險持續、倍數不回歸)。
"""
import io
import os

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"

SUPPORT = {
    "FSLR-P1": (True, "指引不下調 = 經營損害被高估那一邊"),
    "FSLR-P2": (False, "毛利率按季轉差"),
    "FSLR-P3": (False, "收入按年下降"),
    "LINC-1": (False, "招生增速失守"),
    "LINC-2": (False, "指引下調或撤回"),
    "LINC-3": (False, "自由現金流為負"),
    "AGX-1": (False, "在手訂單縮"),
    "AGX-2": (False, "毛利率跌"),
    "AGX-3": (False, "市銷率不回歸,即數三不兌現"),
    "P-CLS-1": (True, "收入達或高於指引上限"),
    "P-CLS-2": (False, "股數上升即稀釋"),
    "P-CLS-3": (False, "股價不重上高位"),
    "P-COLL-1": (False, "舊藥收入按季跌"),
    "P-COLL-2": (True, "指引不再下調"),
    "P-COLL-3": (True, "新藥合計收入達標"),
    "CRDO-P1": (True, "毛利率落在指引之內或以上"),
    "CRDO-P2": (False, "無內部人公開市場買入"),
    "CRDO-P3": (False, "客戶集中度風險持續"),
    "CRNC-1": (True, "自由現金流達指引下限"),
    "CRNC-2": (False, "下一年收入指引按年下降"),
    "CRNC-3": (True, "回購可轉債即去槓桿"),
    "CRUS-1": (True, "收入不跌穿指引下限"),
    "CRUS-2": (True, "毛利率守住指引下限"),
    "CRUS-3": (False, "市銷率不回歸,即數三不兌現"),
    "FN-1": (False, "自由現金流仍為負"),
    "FN-2": (True, "下一季收入指引達標"),
    "FN-3": (True, "營業利潤率不低於上一財年"),
    "INOD-1": (True, "收入增速守住指引"),
    "INOD-2": (False, "動用 ATM 即稀釋"),
    "INOD-3": (False, "客戶預付款下降"),
    "LMB-1": (False, "EDITDA 利潤率達不到全年指引所需節奏"),
    "LMB-2": (False, "有機收入連續第三季為負"),
    "LMB-3": (False, "無內部人公開市場買入"),
    "P-LULU-1": (False, "可比銷售差於或等於 −10%"),
    "P-LULU-2": (True, "指引不第五度下調"),
    "P-LULU-3": (True, "內部人公開市場買入"),
    "RMBS-1": (True, "權利金收入達指引上限"),
    "RMBS-2": (True, "總收入達指引上限,連續第三季超標"),
    "RMBS-3": (True, "大客戶無流失"),
    "STRL-P1": (False, "分部利潤率按年跌幅仍大"),
    "STRL-P2": (True, "全年收入指引不下調"),
    "STRL-P3": (False, "無內部人公開市場買入"),
}
# LMB-1 的說明打錯字,改回正確寫法
SUPPORT["LMB-1"] = (False, "調整後 EBITDA 利潤率達不到全年指引所需節奏")

BASIS = "數字基礎已由 KARST-195/196/197 更正,預測本身不變"


def remark(code: str) -> str:
    sup, why = SUPPORT[code]
    return "%s(%s);%s" % ("支持買入" if sup else "不支持買入", why, BASIS)


def do_csv():
    import csv
    p = os.path.join(D, "前瞻預測登記表.csv")
    with open(p, "r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    head, body = rows[0], rows[1:]
    if "備註(KARST-197)" in head:
        print("CSV 已有備註欄,不重複加")
        return
    head.append("備註(KARST-197)")
    ci = head.index("code")
    for r in body:
        r.append(remark(r[ci]))
    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
        csv.writer(fh).writerows([head] + body)
    print("CSV 加欄完成,%d 列" % len(body))


def do_md():
    """MD 加欄：既有預測一字不改，只在行尾接一格備註。

    注：舊版用 regex 抓代號，抓不到 FSLR-P1 那種帶數字的代號；
    現改為數分隔符定位。
    """
    p = os.path.join(D, "前瞻預測登記表.md")
    lines = io.open(p, encoding="utf-8").read().split(chr(10))
    out, k = [], 0
    for ln in lines:
        s = ln.rstrip()
        if s.startswith("|") and s.count("|") == 8:
            cells = [c.strip() for c in s.split("|")]
            code = cells[3].strip("*")
            if code in SUPPORT:
                out.append(s + " " + remark(code) + " |")
                k += 1
                continue
        out.append(s)
    io.open(p, "w", encoding="utf-8").write(chr(10).join(out))
    print("MD 加欄完成，%d 列帶備註" % k)


if __name__ == "__main__":
    do_csv()
    do_md()
