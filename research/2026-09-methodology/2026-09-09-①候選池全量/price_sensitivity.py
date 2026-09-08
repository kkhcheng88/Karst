"""KARST-188 流程檢討的其中一項:名單對價格雜訊有多敏感。

背景:抽數時美股仍在交易,管線取到的是即市報價而非收市價,並標成「收市」。
同一日抽兩次,六十家之中五十九家的價格不同(中位差 0.39%,最大 1.53%)。
本腳本量化:這個級數的價格差,會令幾多家在回報底線兩邊翻轉、會令正本十二家換幾多人。

數三對價格是接近純倒數的關係(退出市值除以現價),所以價格上升 s,
數三大約由 n3 變成 (1+n3)/(1+s) − 1。本腳本用這條關係做衝擊,不重抽價格。

輸出:price_sensitivity.csv、以及主控台的摘要。
"""
import os
import numpy as np
import pandas as pd

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
BOTTOM = 0.15
SHOCKS = [0.0039, 0.0100, 0.0153]  # 兩次重跑的中位差、一個整數參照、最大差


def n3_after(n3, s):
    return (1.0 + n3) / (1.0 + s) - 1.0


def top12(f):
    # 甲組 = 負債閘過、而且賠率算得出(與 make_ranking.py 的分組同一條件)
    a = f[f["debt_gate"].astype(bool) & f["odds"].notna()].sort_values(
        "odds", ascending=False)
    return list(a[a["pass_bottom_line"]].head(12).index)


def main():
    r = pd.read_csv(os.path.join(D, "ranking_60.csv")).set_index("ticker")
    base12 = top12(r)
    rows = []
    print("基準正本十二家:", base12)
    print()
    for s in SHOCKS:
        for sign in (+1, -1):
            g = r.copy()
            g["n3_ret_1y"] = [n3_after(x, sign * s) if pd.notna(x) else np.nan
                              for x in g["n3_ret_1y"]]
            g["pass_bottom_line"] = g["n3_ret_1y"] >= BOTTOM
            new12 = top12(g)
            flipped = [t for t in r.index
                       if pd.notna(r.loc[t, "n3_ret_1y"])
                       and bool(r.loc[t, "pass_bottom_line"]) != bool(g.loc[t, "pass_bottom_line"])]
            inn = [t for t in new12 if t not in base12]
            out = [t for t in base12 if t not in new12]
            rows.append(dict(shock_pct=sign * s * 100, n_flip=len(flipped),
                             flipped=";".join(flipped), in12=";".join(inn),
                             out12=";".join(out)))
            print("價格 %+.2f%%:底線兩邊翻轉 %d 家 %s;正本十二家 進 %s 出 %s"
                  % (sign * s * 100, len(flipped), flipped or "", inn or "無", out or "無"))

    # 每家距底線多遠(換算成需要幾多百分比的價格變動才會翻轉)
    n3 = r["n3_ret_1y"].dropna()
    need = ((1.0 + n3) / (1.0 + BOTTOM) - 1.0)  # 令 n3 剛好等於底線所需的價格變動
    near = need.abs().sort_values()
    print()
    print("距底線最近的十家(第二欄 = 要多少價格變動才翻轉):")
    for t in near.index[:10]:
        print("  %-6s %+6.2f%%   數三 %+6.2f%%  %s"
              % (t, need[t] * 100, n3[t] * 100,
                 "過" if r.loc[t, "pass_bottom_line"] else "不過"))
    within = near[near < 0.0153]
    print()
    print("在「兩次重跑最大價差」(1.53%%)之內就會翻轉的:%d 家 —— %s"
          % (len(within), list(within.index)))

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(D, "price_sensitivity.csv"), index=False,
               encoding="utf-8-sig")
    nd = pd.DataFrame({"need_price_move_pct": need * 100, "n3": n3 * 100,
                       "pass": r.loc[n3.index, "pass_bottom_line"]})
    nd.sort_values("need_price_move_pct", key=abs).to_csv(
        os.path.join(D, "bottom_line_margin.csv"), encoding="utf-8-sig")
    print()
    print("已寫 price_sensitivity.csv、bottom_line_margin.csv")


if __name__ == "__main__":
    main()
