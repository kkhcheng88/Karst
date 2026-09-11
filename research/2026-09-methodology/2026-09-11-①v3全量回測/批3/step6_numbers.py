# -*- coding: utf-8 -*-
"""KARST-214(批 3):步六算術落檔(結果檔 = 步六計算——批3.csv)。

只讀 `packets/*.json`(已遮蔽),不讀 `out/` 任何檔案。兩個模型,按事件性質分開:

  A. 現金流受損模型(E08 關稅、E12 實體清單、E14 生成式 AI)
     情境 Δ 的兩個輸入 —— 收入變動 % 與 毛利率變動 pp —— 由步三暴露表與步四證據導出
     (假設值寫在本檔 ASSUMPTIONS,逐條可在卡上檢查)。
     Δ毛利 = 收入 × Δ毛利率(pp)
     Δ稅後現金流 = Δ毛利 × (1 − 21%)
     損害後現金流 = 基準經營現金流 + Δ稅後現金流
     價值 = 損害後現金流 ÷ 折現率(永續、零增長)
     折現率 = 衝擊日十年期美債 + 5 個百分點(口徑第二節)

  B. 久期模型(E13 利率衝擊)
     這宗打的是折現率不是現金流,故改用「現價隱含的永續增長」作錨:
         成熟期現金流 CF = 現時收入 × 假設成熟轉換率 m
         現價隱含永續增長 g* = r − CF ÷ 市值(Gordon 反解)
         折現率升 dr 而 g 不變 ⇒ 價值倍數 = (r − g*) ÷ (r + dr − g*)
     情境 = 折現率 +100bp / +200bp,以及「現價要求」。
     **為何不用當前經營現金流**:ASAN 與 BILL 的當前經營現金流為負,且逐年虧損,
     以現時現金流做兩段式折現會得出負價值或荒謬低值;改用「成熟期轉換率」把價值
     重心放回遠期,正是本宗要考的久期。m 是假設值(MARGIN),逐家在卡上交代理由。
     **本模型不報「每股價值」的絕對水平**,只報利率變動下的**價值倍數**——因為
     絕對水平受 m 假設支配,而倍數只受 (r − g*) 支配,後者由市值與現時收入決定,
     是市場自己給的數,不是我們假設的數。

**明文縮減(列入舉手)**:取證包內沒有資本開支與營運資金兩欄,故 Δ 的三個輸入之中
資本開支與營運資金兩項標`查不到`,不以 0 冒充;經營現金流作自由現金流的代理。
基準現金流用滾動四季經營現金流(OCF),不用淨利——因 QCOM FY2018 與 CHGG FY2022
的淨利各被一次性稅項扭曲。

**面板缺口與補數(PATCH)**:四家取證包面板缺市值或缺整行,補數一律取自**衝擊前**
申報(10-K 封面股數、10-K 財務報表),逐條來源寫在 PATCH 內;此補數列入舉手。

用法:PYTHONUTF8=1 python step6_numbers.py
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TAX = 0.21

TICKERS = {"E08": ["NKE", "RH", "BBY", "AAPL"],
           "E12": ["QCOM", "SWKS", "MU", "LITE"],
           "E13": ["ASAN", "BILL", "DOCU", "MSFT"],
           "E14": ["CHGG", "DUOL"]}

# 情境假設:(Δ收入 %, Δ毛利率 pp)。全真／部分真／大致不成立。
# 每格來源寫在卡上「步五情境表」;此處只放數,不動判斷。
ASSUMPTIONS = {
    "NKE":  [(-0.06, -4.0), (-0.03, -1.5), (-0.01, -0.3)],
    "RH":   [(-0.12, -5.0), (-0.06, -2.0), (-0.02, -0.5)],
    "BBY":  [(-0.08, -3.0), (-0.04, -1.2), (-0.01, -0.3)],
    "AAPL": [(-0.06, -2.0), (-0.03, -0.8), (-0.01, -0.2)],
    "QCOM": [(-0.08, -2.0), (-0.04, -1.0), (-0.01, -0.2)],
    "SWKS": [(-0.08, -3.0), (-0.04, -1.2), (-0.01, -0.3)],
    "MU":   [(-0.10, -4.0), (-0.05, -1.5), (-0.02, -0.4)],
    "LITE": [(-0.11, -3.0), (-0.05, -1.2), (-0.02, -0.3)],
    "CHGG": [(-0.20, -2.0), (-0.10, -1.0), (-0.02, 0.0)],
    "DUOL": [(-0.05, -1.0), (-0.02, -0.5), (0.00, 0.0)],
}

# E13 久期模型:m = 假設的成熟期經營現金流轉換率(佔收入)。理由寫在卡上:
# ASAN/BILL 屬訂閱制軟件、尚未成熟,取 25%(行業成熟軟件經營現金流利潤率常見區間);
# DOCU 現時已達 25.2%,即取其實際水平;MSFT 現時 46.5%,保守取 35%。
MARGIN = {"ASAN": 0.25, "BILL": 0.25, "DOCU": 0.25, "MSFT": 0.35}
RATE_SHOCKS = [0.01, 0.02]

# 面板缺口補數。來源全部為**衝擊前**申報,逐條寫明。
PATCH = {
    # NKE FY2024 10-K(2024-07-25)封面:2024-07-10 Class A 297,897,252 + Class B 1,201,461,692
    # ⇒ 14.994 億股。面板期末 2024-11-30,其間持續回購,故本數略高估,已在卡上標明。
    "NKE": {"shares_m": 1499.358944},
    # SWKS FY2018 10-K(2018-11-15):封面 177.4 百萬股(2018-09-28);損益表收入 3,868.0 百萬;
    # 現金流量表經營現金流 1,260.6 百萬。面板整行缺(feat_status=最近季度過期)。
    "SWKS": {"shares_m": 177.4, "rev": 3868.0e6, "ocf": 1260.6e6},
    # ASAN FY2021 10-K(2021-03-30)封面:2021-03-22 Class A 91,266,753 + Class B 71,785,101
    # ⇒ 1.6305 億股(早於衝擊 2022-01-03 約 9 個月,其間有增發,故本數略低,已在卡上標明)。
    "ASAN": {"shares_m": 163.051854},
    # DUOL FY2022 10-K(2023-03-01)封面:2023-02-27 Class A 32,201,681 + Class B 8,434,238
    # ⇒ 4,063.6 萬股。
    "DUOL": {"shares_m": 40.635919},
}


def load(eid):
    p = json.load(open(f"{HERE}/packets/{eid}.json", encoding="utf-8"))
    return {c["ticker"]: c for c in p["companies"]}, p


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def base(c):
    """回傳 (收入, 經營現金流, 股數, 衝擊前收市價, 市值);缺者依 PATCH 補,補不到回 None。"""
    tk = c["ticker"]
    p = PATCH.get(tk, {})
    rev = f(c.get("ttm_revenue")) or p.get("rev")
    ocf = f(c.get("ttm_ocf")) or p.get("ocf")
    px = f(c.get("price_shock_start_close"))
    mcap = f(c.get("mcap_usd"))
    shares = mcap / px if (mcap and px) else p.get("shares_m", 0) * 1e6 or None
    return rev, ocf, shares, px, (mcap if mcap else (shares * px if (shares and px) else None))


def value_cf_model(rev, ocf, shares, r, scen):
    """現金流受損模型。回傳 (每股價值, 損害後現金流, Δ稅後現金流)。"""
    drev, dgm = scen
    dgp = rev * (1 + drev) * (dgm / 100.0)      # 收入變動後的收入 × 毛利率變動
    dcf = dgp * (1 - TAX)
    cf2 = ocf + dcf
    return max(cf2, 0.0) / r / shares, cf2, dcf


def mature_cf(tk, rev):
    """成熟期現金流 = 現時收入 × 假設成熟轉換率 m。"""
    return rev * MARGIN[tk]


def implied_g(tk, rev, mcap, r):
    """現價隱含的永續增長 g* = r − 成熟現金流 ÷ 市值(Gordon 反解)。"""
    cf = mature_cf(tk, rev)
    return r - cf / mcap, cf


def rate_mult(k, dr):
    """折現率升 dr 而增長不變時的價值倍數(相對基準 r0)。"""
    r0, g = k["r"], k["g"]
    return (r0 - g) / (r0 + dr - g)


def main():
    rows = []
    for eid, tks in TICKERS.items():
        comp, pack = load(eid)
        r0 = pack["treasury_10y_pct_on_shock_start"] / 100.0 + 0.05
        for tk in tks:
            c = comp[tk]
            rev, ocf, shares, px, mcap = base(c)
            tag = "" if not PATCH.get(tk) else "(補數)"
            if eid == "E13":
                g0, cf = implied_g(tk, rev, mcap, r0)
                k = {"r": r0, "g": g0}
                basis = "折現率 r=%.2f%%、成熟期現金流 %.3f 億(收入 %.3f 億 × 假設轉換率 %.0f%%);" \
                       "現價隱含永續增長 g*=%.2f%%(r−CF/市值)" % (
                           r0 * 100, cf / 1e8, rev / 1e8, MARGIN[tk] * 100, g0 * 100)
                for i, dr in enumerate(RATE_SHOCKS):
                    mult = rate_mult(k, dr)
                    rows.append(dict(event_id=eid, ticker=tk, model="久期",
                                     scenario=["折現率+100bp", "折現率+200bp"][i],
                                     price=round(px, 2), value_per_share=round(px * mult, 2),
                                     pct_vs_price=round(mult - 1, 4),
                                     note="利率升 %dbp、增長不變 ⇒ 價值 ×%.3f。%s%s" % (
                                         dr * 10000, mult, basis, tag)))
                rows.append(dict(event_id=eid, ticker=tk, model="久期", scenario="現價要求",
                                 price=round(px, 2), value_per_share="", pct_vs_price="",
                                 note="要令利率升 100bp 後價值仍等於現價,隱含永續增長須由 %.2f%% "
                                      "同步升至 %.2f%%(即價值毫髮無傷);若增長不變,該情境下現價須跌 %.1f%%。%s%s" % (
                                          g0 * 100, (g0 + 0.01) * 100,
                                          (1 - rate_mult(k, 0.01)) * 100, basis, tag)))
                continue
            for i, scen in enumerate(ASSUMPTIONS[tk]):
                if None in (rev, ocf, shares, px):
                    rows.append(dict(event_id=eid, ticker=tk, model="現金流",
                                     scenario=["全真", "部分真", "不成立"][i],
                                     price=round(px, 2) if px else "", value_per_share="查不到",
                                     pct_vs_price="", note="面板缺收入或現金流或股數"))
                    continue
                v, cf2, dcf = value_cf_model(rev, ocf, shares, r0, scen)
                rows.append(dict(event_id=eid, ticker=tk, model="現金流",
                                 scenario=["全真", "部分真", "不成立"][i],
                                 price=round(px, 2), value_per_share=round(v, 2),
                                 pct_vs_price=round(v / px - 1, 4),
                                 note="Δ收入%+.0f%% Δ毛利%+.1fpp ⇒ Δ稅後現金流 %.3e、損害後 %.3e;"
                                      "為維持現價,市場須付的無增長倍數升至 %.2f 倍%s" % (
                                          scen[0] * 100, scen[1], dcf, cf2,
                                          (px * shares * r0 / cf2) if cf2 > 0 else float("inf"), tag)))
            if ocf and shares and px:
                x = px * shares * r0 / ocf      # 現價隱含的「無增長現金流倍數」
                rows.append(dict(event_id=eid, ticker=tk, model="現金流", scenario="現價要求",
                                 price=round(px, 2), value_per_share="", pct_vs_price="",
                                 note="現價隱含的無增長現金流倍數 %.2f 倍(1.00 = 市場只按無增長定價;"
                                      ">1 = 現價已要求現金流高於現時,<1 = 現價低於無增長價值)%s" % (
                                          x, tag)))

    with open(f"{HERE}/步六計算——批3.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["event_id", "ticker", "model", "scenario", "price",
                                           "value_per_share", "pct_vs_price", "note"])
        w.writeheader()
        for r_ in rows:
            w.writerow(r_)
    print("寫出 %d 行 → 步六計算——批3.csv" % len(rows))


if __name__ == "__main__":
    main()
