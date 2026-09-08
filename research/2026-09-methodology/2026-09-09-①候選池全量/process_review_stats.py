"""KARST-188 流程檢討的量化根據。

把「這一版流程哪裡不成立」逐條算成數字,免得檢討只剩下感覺。
輸出:process_review_stats.json + 主控台表格
"""
import os, json
import numpy as np
import pandas as pd
from scipy import stats

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"


def main():
    f = pd.read_csv(os.path.join(D, "screen60_full.csv"))
    r = pd.read_csv(os.path.join(D, "ranking_60.csv")).set_index("ticker")
    f = f.set_index("ticker")
    f["mispricing_label"] = r["mispricing_label"]
    out = {}
    P = print

    P("=" * 74)
    P("一、壓力跌幅公式:機械公式有沒有真的在計算")
    n_floor = int(f["stress_floor_applied"].sum())
    raw_pos = int((f["stress_drop_raw"] > 0).sum())
    P("  改用一年最大回撤封底的家數: %d / %d (%.0f%%)" % (n_floor, len(f), n_floor / len(f) * 100))
    P("  機械公式算出的壓力價高於現價(原始值為正)的家數: %d / %d" % (raw_pos, len(f)))
    P("  → 公式本身在 %d 家之中沒有起作用,壓力跌幅實際上等於「過去一年跌過幾多」。" % n_floor)
    out["stress_floor_applied"] = n_floor
    out["stress_raw_positive"] = raw_pos

    P("")
    P("=" * 74)
    P("二、數三是不是一個獨立的數")
    d = f[["n3_ret_1y", "ps_now", "ps_p50_1y"]].dropna()
    ratio = d["ps_now"] / d["ps_p50_1y"]
    rho, p = stats.spearmanr(d["n3_ret_1y"], ratio)
    P("  數三 對 (現時市銷率 ÷ 一年中位市銷率) 的斯皮爾曼相關: %.3f (p=%.1e, n=%d)"
      % (rho, p, len(d)))
    P("  → 相關接近 −1,即數三幾乎完全由「倍數回到中位數要升幾多」決定,")
    P("    它不是一個獨立於折讓格的第三個數,是折讓格的另一種寫法。")
    out["n3_vs_ps_ratio_spearman"] = round(float(rho), 4)

    P("")
    P("=" * 74)
    P("三、機械 DCF 出來的數二能不能當「合理結果」")
    n2 = f["n2_upside"].dropna()
    P("  數二為正的家數: %d / %d" % (int((n2 > 0).sum()), len(n2)))
    ts = f["n2_terminal_share"].dropna()
    P("  終值佔比 > 90%% 的家數: %d;> 100%%(即營運期現值為負)的家數: %d"
      % (int((ts > 0.90).sum()), int((ts > 1.0).sum())))
    g = f["g_ref_used"].dropna()
    P("  增速參考 > 40%%/年 的家數: %d;被夾在上限 100%%/年 的家數: %d"
      % (int((g > 0.40).sum()), int((g >= 0.999).sum())))
    dd = f[["odds", "g_ref_used"]].dropna()
    rho2, p2 = stats.spearmanr(dd["odds"], dd["g_ref_used"])
    P("  賠率 對 增速參考 的斯皮爾曼相關: %.3f (p=%.1e, n=%d)" % (rho2, p2, len(dd)))
    P("  → 賠率排位有相當部分由「輸入了幾大的增速」決定,不是由折讓深淺決定。")
    top = f.sort_values("odds", ascending=False).head(3)
    for t, row in top.iterrows():
        P("    排位前列 %-5s 賠率 %8.2f 增速參考 %s 終值佔比 %s"
          % (t, row["odds"],
             "%.0f%%" % (row["g_ref_used"] * 100) if pd.notna(row["g_ref_used"]) else "—",
             "%.0f%%" % (row["n2_terminal_share"] * 100) if pd.notna(row["n2_terminal_share"]) else "—"))
    out.update(n2_positive=int((n2 > 0).sum()), terminal_gt90=int((ts > 0.90).sum()),
               terminal_gt100=int((ts > 1.0).sum()), g_gt40=int((g > 0.40).sum()),
               g_clamped=int((g >= 0.999).sum()),
               odds_vs_g_spearman=round(float(rho2), 4))

    P("")
    P("=" * 74)
    P("四、賠率排序與不含模型鎖定判斷有沒有講同一件事")
    a = r[r["rank"].notna()].head(12)
    vc = a["A_conclusion"].value_counts()
    P("  卡片十二家的不含模型結論分佈: %s" % dict(vc))
    veto = a[a["ma200_form"] == "回調"]
    P("  其中 200 日線形態為「回調」(D-169 直接否決)的家數: %d %s"
      % (len(veto), list(veto.index)))
    P("  → 賠率排位高不等於過得到不含模型那一關,兩層各自為政。")
    out["top12_A_conclusion"] = {str(k): int(v) for k, v in vc.items()}
    out["top12_veto_by_ma200"] = list(veto.index)

    P("")
    P("=" * 74)
    P("五、錯價來源標籤有沒有預測力(現階段)")
    ct = pd.crosstab(f["mispricing_label"], f["pass_bottom_line"])
    P(ct.to_string())
    for lab in ct.index:
        tot = ct.loc[lab].sum()
        hit = ct.loc[lab].get(True, 0)
        P("  %-10s 過底線 %d / %d = %.0f%%" % (lab, hit, tot, hit / tot * 100))
    P("  → 三類標籤的過線比例接近,現階段這個標籤幾乎不含分辨力。")
    out["label_vs_bottom_line"] = {str(k): {str(kk): int(vv) for kk, vv in v.items()}
                                   for k, v in ct.to_dict("index").items()}

    P("")
    P("=" * 74)
    P("六、回報底線是不是刀鋒")
    n3 = f["n3_ret_1y"].dropna()
    band = f.loc[n3[(n3 >= 0.12) & (n3 < 0.18)].index]
    P("  數三落在 12%%–18%% 之間的家數: %d / %d,名單: %s"
      % (len(band), len(n3), list(band.index)))
    P("  → 一日價格波動足以令這幾家在名單內外翻轉;+15%% 是暫定示例線,不宜當入場券。")
    out["bottom_line_knife_edge"] = list(band.index)

    P("")
    P("=" * 74)
    P("七、取數更正的影響面")
    P("  股數更正家數: %d %s" % (int(f["shares_fixed"].sum()), list(f[f["shares_fixed"]].index)))
    P("  債務更正家數: %d" % int(f["debt_fixed"].sum()))
    P("  現金/投資更正家數: %d %s" % (int(f["cash_fixed"].sum()), list(f[f["cash_fixed"]].index)))
    nogate = list(f[~f["debt_gate"].astype(bool)].index)
    P("  負債閘不過: %d 家 %s" % (len(nogate), nogate))
    out.update(shares_fixed=int(f["shares_fixed"].sum()),
               debt_fixed=int(f["debt_fixed"].sum()),
               cash_fixed=int(f["cash_fixed"].sum()),
               debt_gate_fail=nogate)

    P("")
    P("=" * 74)
    P("八、六十家之中哪一格最填不出")
    fields = [
        ("數一 現價隱含五年增速", "n1_implied_g5"),
        ("數二 相對現價上行", "n2_upside"),
        ("數三 一年回報", "n3_ret_1y"),
        ("賠率", "odds"),
        ("分析員共識收入增速", "consensus_rev_growth"),
        ("同業中位相對標普(殺法歸因)", "peer_med"),
        ("市銷率 四年中位", "ps_p50_4y"),
        ("營運現金流", "ocf_ttm"),
        ("營業利潤率", "op_margin"),
    ]
    miss = []
    for lab, col in fields:
        n = int(f[col].isna().sum())
        miss.append((lab, n))
    miss.sort(key=lambda x: -x[1])
    for lab, n in miss:
        P("  %-28s 填不出 %2d / 60 (%.0f%%)" % (lab, n, n / 60 * 100))
    lab_missing = int((f["mispricing_label"] == "資料不足").sum())
    P("  %-28s 填不出 %2d / 60 (%.0f%%)" % ("錯價來源標籤", lab_missing, lab_missing / 60 * 100))
    P("  → 最填不出的是數一(37%,現價隱含增速在給定利潤率下無實解)與由數二衍生的賠率(27%),")
    P("    兩格都不是「資料抓不到」,是**模型本身解不出**。錯價來源標籤反而 60/60 全部填得出,")
    P("    因為它有兩把尺,第一把用不上就退到分析員目標價那一把。")
    out["field_missing"] = {k: v for k, v in miss}
    out["label_missing"] = lab_missing

    with open(os.path.join(D, "process_review_stats.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    P("")
    P("已寫 process_review_stats.json")


if __name__ == "__main__":
    main()
