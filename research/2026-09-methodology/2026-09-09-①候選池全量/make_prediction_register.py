"""KARST-188:把各張加模型卡片第七節的預登記預測抽出來,併成一份登記表。

用途:這些預測是日後回頭核對「加了模型的判斷有沒有比機械層準」的唯一憑據。
散在十四份卡片裡等於沒有登記——要一份可以逐項打勾的正本。

輸出:前瞻預測登記表.md、前瞻預測登記表.csv
"""
import os
import re
import glob
import pandas as pd

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
TOP12 = ["CRDO", "STRL", "COLL", "CLS", "LULU", "CRUS",
         "CRNC", "INOD", "FN", "AGX", "RMBS", "LMB"]
EXTRA = ["FSLR", "LINC"]


def strip_md(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    return s.strip()


def parse_card(path):
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    t = re.search(r"B-([A-Z]+)-", os.path.basename(path)).group(1)
    # 找第七節,讀到下一個 "## " 為止
    start = None
    for i, ln in enumerate(lines):
        # 各隊的標題字眼略有出入(「預登記預測」/「預先登記的預測」),只認第七節 + 「預測」
        if ln.startswith("## 七") and "預測" in ln:
            start = i
            break
    if start is None:
        return t, []
    body = []
    for ln in lines[start + 1:]:
        if ln.startswith("## "):
            break
        body.append(ln)
    rows = []
    for ln in body:
        if not ln.strip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        if set("".join(cells)) <= set("-: "):      # 分隔行
            continue
        if "代號" in cells[0] or "預測" in cells[1] and "勝率" in cells[2]:
            continue                                # 表頭
        rows.append([strip_md(c) for c in cells[:5]])
    return t, rows


def main():
    recs = []
    for p in sorted(glob.glob(os.path.join(D, "B-*-加模型判斷.md"))):
        t, rows = parse_card(p)
        for r in rows:
            recs.append(dict(ticker=t, code=r[0], prediction=r[1],
                             win_rate=r[2], check_date=r[3], check_doc=r[4]))
    df = pd.DataFrame(recs)
    have = sorted(df["ticker"].unique()) if len(df) else []
    missing = [t for t in TOP12 + EXTRA if t not in have]

    df["組別"] = df["ticker"].apply(
        lambda x: "正本十二家" if x in TOP12 else "附加")
    df = df.sort_values(["組別", "ticker", "code"],
                        ascending=[False, True, True])

    L = ["# KARST-188 前瞻預測登記表", "",
         "**這一份是日後覆核用的正本。** 每一項都是加了模型之後才寫得出的、可證偽的預測:",
         "有門檻、有核的日期、有核的文件。到期逐項打勾,就能回答「加模型那一層值不值得做」。", "",
         "- 立場日:2026-09-09。價格參照 2026-09-08(**注意:抽數時美股仍在交易,",
         "  那是即市報價不是收市價,見總覽第六節**)。",
         "- 勝率一律寫成區間,**只作評分用,不作倉位輸入**",
         "  (依 2026-09-07 錯殺注材料梳理 §11 第 23 項)。",
         "- 覆核時「核的文件」必須是一手申報文件;",
         "  查不到那份文件就記「未能核」,不准用新聞或第二手轉述代替。", ""]
    if missing:
        L += ["> 尚未交回卡片、因而未有預測的:" + "、".join(missing), ""]
    L += ["共 %d 項,涵蓋 %d 家。" % (len(df), len(have)), "",
          "| 家 | 組別 | 代號 | 可證偽的預測 | 勝率區間 | 核的日期 | 核的文件 |",
          "|---|---|---|---|---|---|---|"]
    for _, r in df.iterrows():
        L.append("| %s | %s | %s | %s | %s | %s | %s |"
                 % (r["ticker"], r["組別"], r["code"], r["prediction"],
                    r["win_rate"], r["check_date"], r["check_doc"]))
    L += ["", "## 覆核時要一併記下的兩件事", "",
          "1. **這項預測有沒有影響過當時的進場動作。** 有影響而落空的,",
          "   比沒有影響而落空的嚴重得多——前者代表判斷鏈斷了,後者只代表多寫了一句。",
          "2. **核的日期有沒有如期出現。** 本批有五家的業績日是推算的",
          "   (COLL、CRNC、FN、RMBS 明寫,見各卡最後一節),日期改變就順延,不算落空。"]

    with open(os.path.join(D, "前瞻預測登記表.md"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    df.to_csv(os.path.join(D, "前瞻預測登記表.csv"), index=False,
              encoding="utf-8-sig")
    print("已寫前瞻預測登記表:%d 項,涵蓋 %d 家" % (len(df), len(have)))
    print("每家項數:")
    print(df.groupby("ticker").size().to_string())
    if missing:
        print("未交回卡片:", missing)


if __name__ == "__main__":
    main()
