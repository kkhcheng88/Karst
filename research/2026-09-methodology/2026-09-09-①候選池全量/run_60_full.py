"""KARST-188 第一步:六十家過閘名單的機械欄位一次過算齊。

本腳本**不含任何個股質性判斷**。它產生的每一欄都由固定規則算出,規則寫在下面,
在看數字之前定好,六十家同一套,不逐家調。

規則(先寫,後看數字):

A. 截止日與價格日
   截止日 2026-09-09;價格用最近收市(2026-09-08)。窗口回報沿用 KARST-184 的
   起點 2026-06-01,終點改為最近收市。同業歸因用 KARST-184 的 screen_step1_raw.csv
   (窗口至 2026-09-04),候選與同業同一把尺。

B. 折現率規則(KARST-184 定,本票沿用)
   十年期美債收益率(2026-09-08 ^TNX 收 4.792%)+ 股權溢價 5.0% = 9.792%
   → 四捨五入至 0.5% → **10.0%**,六十家同一個數。

C. 不含模型鎖定判斷的四項
   (c1) 第一版篩四道閘:六十家全部已過(KARST-184 screen_step2_gates.csv),
        本票用更新後的 companyfacts 重核淨負債與營運現金流。
   (c2) 負債閘:淨現金,或淨負債 ÷ 近四季營運現金流 ≤ 3。
   (c3) 200 日線形態三格:價 > 200 日線 = 回調;價 < 200 日線且 200 日線 40 日
        斜率 ≤ 0 = 殺;價 < 200 日線但斜率 > 0 = 線附近。
   (c4) 跌幅歸因:同業中位相對 SPY 回報 ≤ −15% = 行業殺;≥ −5% = 個別殺;
        介乎兩者 = 混合。同業 = 同四位 SIC(該 SIC 在宇宙內至少 5 家),
        否則同兩位 SIC。
   (c5) 估值折讓兩把尺(依 KARST-184 總覽 §6.3 第 2 條的建議,本票採納為規則):
        現時市銷率 ≤ 四年中位 × 0.8 且 ≤ 近一年中位 × 0.8 = 兩把尺都過;
        只過一把 = 「重估已完成,不是折讓」;都不過 = 不過。

   鎖定結論三格:
        入選 = 四道閘過 + 負債閘過 + (c5) 兩把尺都過 + (c3) 判「殺」
        不入 = (c3) 判「回調」,或 (c5) 兩把尺都不過
        觀察 = 其餘

D. 三個數(通用機械式假設,六十家同一套,不含個股判斷)
   第一階段 5 年增長率參考值 = 近四年 TTM 收入年增率(夾在 −50%~+100%);
   目標營業利潤率 = 現時 GAAP 營業利潤率(即假設利潤率不變);
   terminal_growth 2.5%、terminal_roic 15%、tax 23%、sales_to_capital 2.0、horizon 10。
   數一 = 固定利潤率下,現價隱含的第一階段(5 年)收入年增率。
   數二 = 上述假設下的基準每股值,及其相對現價的上升幅度。
   數三 = 一年持有回報:收入走平、退出倍數 = **近一年市銷率中位**
          (不用四年中位——KARST-184 已證四年分佈屬於一家不同性質的公司),
          一年淨稀釋 = 股權薪酬 ÷ 市值,下限 0.5%。
   估值不可靠旗:現時營業利潤率 ≤ 0、或終值佔企業價值 > 150%、或每股值 ≤ 0。

E. 壓力情境跌幅(第一版,機械公式;票內指定)
   壓力價 = 近一年市銷率 25 分位 × (TTM 收入 × 0.9) ÷ 稀釋股數。
   下限規則(依 KARST-184 總覽 §6.3 第 6 條建議,本票採納):壓力跌幅的絕對值
   不得小於該股近一年實際最大回撤。兩者取較大的跌幅。

F. 賠率與底線
   賠率 = 數二上升幅度 ÷ |壓力跌幅|(票內定義)。
   回報底線(臨時線,示例):數三 ≥ +15%。
   倉位 = 組合 2%(示例損失預算,未經用戶對齊,D-170)÷ |壓力跌幅|。

輸出:screen60_full.csv、screen60_full.json、yf_analyst_raw.json
"""
import os, sys, json, math, datetime as dt
import pandas as pd
import numpy as np

sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE  # noqa

OUT_DIR = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
SRC_DIR = r"C:\projects\Karst\research\2026-09-methodology\2026-09-08-①候選池走通"

TICKERS = ['ADTN', 'SEDG', 'INOD', 'VPG', 'LINC', 'ARRY', 'UTI', 'MRAM', 'CIEN', 'LASR',
           'ENPH', 'AAON', 'STRL', 'RMBS', 'AIP', 'CLFD', 'CEVA', 'TROX', 'LMB', 'ON',
           'ARM', 'POWL', 'MEC', 'MYRG', 'LUMN', 'ORCL', 'AGX', 'DOCN', 'FN', 'MTZ',
           'AMKR', 'CRNC', 'MOD', 'FSLR', 'CRUS', 'IPGP', 'IREN', 'GNRC', 'CDNS', 'TTMI',
           'CENX', 'CLS', 'VIAV', 'ALB', 'FLEX', 'COLL', 'MRCY', 'SAIA', 'QCOM', 'HLIT',
           'KRMN', 'PUMP', 'SANM', 'CRDO', 'CLVT', 'MTSI', 'TDC', 'LULU', 'DRS', 'ACLS']

WACC = 0.10
WIN_START = dt.date(2026, 6, 1)
LOSS_BUDGET = 0.02          # 示例值,未經用戶對齊(D-170)
BOTTOM_LINE_1Y = 0.15       # 臨時示例底線
OCF_TAGS = ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]


# ---------------------------------------------------------------------------
# 本票的人手更正(A-049):稀釋股數不可以拆季
# ---------------------------------------------------------------------------
# implied_expectations.build_financials 把稀釋股數當成流量,經 quarterize() 拆季
# (第四季 = 全年 − 首九個月)。稀釋股數是**加權平均存量**,不是流量,拆季等於
# 用全年平均減去九個月平均,結果接近零。財政年度在年中結束、最近一份申報是 10-K
# 的公司會全部中招。六十家之中有 6 家(VPG、ORCL、FN、IREN、VIAV、MRCY)的股數
# 被壓到真實值的 0.1%–4%,連帶市銷率、每股值、壓力價、倉位全部作廢。
#
# 本票的處理(照 KARST-184 對 BS_FIX 的做法):**不改共用工具**,在本腳本內更正,
# 並在票上舉手另開票修共用工具。
#
# 更正規則:直接取未拆季的 duration 事實,取結束日最近的一筆;同一結束日有多筆時
# 優先取 60–100 日(季度)的那筆。再與 yfinance 現時股數對照,相差超過 ±25% 時
# 改用 yfinance 並記一筆(股數可以因回購/增發而變,±25% 是容差不是判準)。
# ---------------------------------------------------------------------------
# 本票的第二項人手更正(A-050):有息負債標籤清單太窄
# ---------------------------------------------------------------------------
# implied_expectations 只認四個負債標籤(LongTermDebtCurrent、DebtCurrent、
# LongTermDebtNoncurrent、ConvertibleDebtNoncurrent、LongTermDebt)。很多公司用
# NotesPayable* / LoansPayable* / LongTermDebtAndCapitalLeaseObligations* 申報,
# 完全不在清單內,結果有息負債當零。實測:Oracle 的 1,295 億美元債務只認到 60 億;
# Clarivate 的 43 億債務全部漏掉,淨負債由 +40 億變成 −1.9 億(反而變成淨現金)。
# 這一項會直接推翻第一版篩的「壓力下不依賴短期再融資」那道閘。
#
# 更正規則(保守取大):有息負債 = max(組合標籤的最大值, 流動分項 + 非流動分項)。
# 再與 yfinance 的 Total Debt 對照,相差超過 25% 時記一筆「負債閘存疑」,由人手核。
#
# 三個桶要分清楚,否則會重覆計數:
#   COMBINED —— 一個標籤就代表全部有息負債(含流動部分)的「總額」標籤
#   CUR / NC —— 分項標籤,兩者相加才是總額
# 「總額」標籤只在它的資產負債表日期**不早於**分項的日期時才採用;否則就是上一季的
# 舊總額,加進去會把已經還掉或重分類的部分算兩次(Viavi 就是這樣被多算 1.94 億)。
DEBT_COMBINED = ["DebtLongtermAndShorttermCombinedAmount",
                 "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",
                 "LongTermDebtAndCapitalLeaseObligations",
                 "LongTermDebt", "NotesPayable", "DebtInstrumentCarryingAmount"]
DEBT_CUR_WIDE = ["LongTermDebtCurrent", "DebtCurrent", "NotesPayableCurrent",
                 "LoansPayableCurrent", "ConvertibleNotesPayableCurrent",
                 "LinesOfCreditCurrent", "ShortTermBorrowings",
                 "OtherShortTermBorrowings", "SecuredDebtCurrent",
                 "LongTermDebtAndCapitalLeaseObligationsCurrent"]
DEBT_NC_WIDE = ["LongTermDebtNoncurrent", "LongTermNotesPayable",
                "LongTermLoansPayable", "ConvertibleLongTermNotesPayable",
                "ConvertibleDebtNoncurrent", "LongTermLineOfCredit", "LineOfCredit",
                "SecuredLongTermDebt"]

# 一個桶之內「依序取第一個有值的標籤」會漏數:同一家公司可以同時有定期貸款與可轉債,
# 分別報在兩條不同的標籤上,取了第一條就當第二條不存在。實測 Collegium:
# LongTermLoansPayable 7.978 億 + ConvertibleLongTermNotesPayable 2.387 億,
# 舊寫法只讀到 7.978 億,漏掉可轉債 2.387 億(10-Q 一手核實:有息負債合計 10.915 億)。
#
# 改法:桶內分「總額標籤」與「分項標籤族」。總額標籤本身已包含全部;分項標籤族之間
# 互不重疊,可以相加。**桶值 = max(總額標籤, 各族最大值之和)** ——只取 max,永不把
# 總額與分項相加,所以不會重覆計數。
DEBT_CUR_AGG = ["LongTermDebtCurrent", "DebtCurrent",
                "LongTermDebtAndCapitalLeaseObligationsCurrent"]
DEBT_CUR_FAMILIES = [["NotesPayableCurrent", "LoansPayableCurrent"],
                     ["ConvertibleNotesPayableCurrent"],
                     ["LinesOfCreditCurrent"],
                     ["ShortTermBorrowings", "OtherShortTermBorrowings"],
                     ["SecuredDebtCurrent"]]
DEBT_NC_AGG = ["LongTermDebtNoncurrent"]
DEBT_NC_FAMILIES = [["LongTermNotesPayable", "LongTermLoansPayable"],
                    ["ConvertibleLongTermNotesPayable", "ConvertibleDebtNoncurrent"],
                    ["LongTermLineOfCredit", "LineOfCredit"],
                    ["SecuredLongTermDebt"]]

FRESH_DAYS = 45   # 時點科目距離資產負債表日超過這個日數,當它是上一季的舊數,不採用

# 投資類標籤清單與債務清單犯同一個毛病:太窄。實測 Cirrus Logic 用
# DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent/Noncurrent 申報,
# 三條都不在清單內,3.567 億美元有價證券當零;Argan 的 4.806 億非流動證券同樣漏掉。
# 兩家都因此被少算淨現金。桶內取第一條有值的(避免總額與分項重覆),
# 桶之間相加,再與「總額標籤」取大者。
STI_WIDE = ["ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
            "MarketableSecuritiesCurrent",
            "DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent",
            "AvailableForSaleSecuritiesCurrent", "OtherShortTermInvestments"]
LTI_WIDE = ["AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
            "MarketableSecuritiesNoncurrent", "LongTermInvestments",
            "DebtSecuritiesAvailableForSaleExcludingAccruedInterestNoncurrent",
            "AvailableForSaleSecuritiesNoncurrent"]
# **合計標籤只准住在這一格。** 2026-09-09 由 RMBS 查出:
# AvailableForSaleSecuritiesDebtSecurities 是合計(流動 + 非流動),我原先誤放進 LTI_WIDE,
# 而 RMBS 的證券全部是流動,於是同一筆 6.518 億美元在流動桶與非流動桶各計一次,
# 淨現金被虛報 6.518 億——修正後的現金加投資是 7.86 億,與 10-Q 對得上。
INV_AGG = ["DebtSecuritiesAvailableForSaleExcludingAccruedInterest", "MarketableSecurities",
           "AvailableForSaleSecurities", "AvailableForSaleSecuritiesDebtSecurities"]

# 現金標籤同樣太窄。2026-09-09 由 CRNC 查出:它的現金掛在
# CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAnd
# DiscontinuedOperations,三個標籤一個都對不上,1.276 億美元現金被當成零。
# 改為前綴比對,並按「愈接近純現金愈優先」排序。
CASH_PREFIXES = ["CashAndCashEquivalentsAtCarryingValue",
                 "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
                 "CashAndCashEquivalentsAtFairValue"]


def interest_debt_fixed(fin):
    facts = IE.load_facts(fin.cik)

    def pick(tags):
        """依序試每個標籤,取第一個有新鮮資料的,回傳(金額, 資產負債表日期)。"""
        for tg in tags:
            ser = IE.instant_series(facts, [tg], fin.asof)
            v = IE._latest(ser, fin.asof)
            if v:
                d = max((k for k in ser if abs((k - fin.asof).days) <= 200), default=None)
                return float(v), d
        return 0.0, None

    def bucket(agg_tags, families):
        """桶值 = max(總額標籤, 各分項族最大值之和)。"""
        a_val, a_d = 0.0, None
        for tg in agg_tags:
            v, d = pick([tg])
            if v and (a_d is None or (d and d > a_d) or v > a_val):
                if d is None or a_d is None or d >= a_d:
                    a_val, a_d = max(a_val, v), (d or a_d)
        s_val, s_d = 0.0, None
        for fam in families:
            v, d = pick(fam)
            if v:
                s_val += v
                if d and (s_d is None or d > s_d):
                    s_d = d
        if s_val > a_val:
            return s_val, s_d
        return a_val, a_d

    cur, d_cur = bucket(DEBT_CUR_AGG, DEBT_CUR_FAMILIES)
    nc, d_nc = bucket(DEBT_NC_AGG, DEBT_NC_FAMILIES)
    est_parts = cur + nc
    d_parts = max([d for d in (d_cur, d_nc) if d], default=None)

    # 總額標籤:**先比新鮮度,後比金額**。反過來(先取金額最大)會挑中上一季的舊總額,
    # 再被新鮮度規則整筆丟掉,結果債務當零——Clarivate 與 Tronox 就是這樣一度變成淨現金。
    est_combined, d_comb = 0.0, None
    for tg in DEBT_COMBINED:
        v, d = pick([tg])
        if not v or d is None:
            continue
        if d_comb is None or d > d_comb:
            d_comb, est_combined = d, v
        elif d == d_comb:
            est_combined = max(est_combined, v)
    # 總額標籤比分項舊,代表它是上一季的數,不採用
    if d_comb and d_parts and d_comb < d_parts:
        est_combined, d_comb = 0.0, None

    debt = max(est_combined, est_parts)
    return debt, dict(combined=est_combined, parts=est_parts, cur=cur, nc=nc,
                      d_parts=str(d_parts), d_comb=str(d_comb))


def cash_invest_fixed(fin):
    """A-047 的另一面:投資類科目取到上一季的舊結餘,現金被高估。

    實測 Collegium:2026-06-30 的資產負債表上可供出售證券已經是零(1.554 億在期內
    沽清,用來付 AZSTARYS 收購的現金對價),但 companyfacts 仍留有 2026-03-31 的
    1.573 億,抽取程式當它是最近一筆,淨負債因而少計 1.573 億。

    改法:時點科目的資產負債表日期距離 fin.asof 超過 FRESH_DAYS 日就當它不存在——
    公司在最近一期沒有再報這一格,通常代表那一格已經歸零或改了標籤,不是「維持不變」。
    """
    facts = IE.load_facts(fin.cik)

    def fresh(tags):
        tot, used = 0.0, []
        for tg in tags:
            ser = IE.instant_series(facts, [tg], fin.asof)
            cands = [(d, v) for d, v in ser.items()
                     if abs((d - fin.asof).days) <= FRESH_DAYS and v]
            if cands:
                d, v = max(cands)
                tot += float(v)
                used.append("%s@%s" % (tg, d))
                break            # 同一族只取一條,避免重覆計數
        return tot, used

    # 現金:先用原清單,取不到就退到前綴比對(CRNC 的「含已終止經營」後綴不在清單內)
    cash, u1 = fresh(IE.CASH_TAGS)
    if cash == 0:
        us = facts.get("facts", {}).get("us-gaap", {})
        wide = [t for p in CASH_PREFIXES for t in sorted(us) if t.startswith(p)]
        seen, ordered = set(), []
        for t in wide:
            if t not in seen:
                seen.add(t); ordered.append(t)
        cash, u1 = fresh(ordered)

    sti, u2 = fresh(STI_WIDE)
    lti, u3 = fresh(LTI_WIDE)
    agg, u4 = fresh(INV_AGG)
    # 保險絲:流動桶與非流動桶的金額完全相同,幾乎肯定是同一筆證券的兩個標籤,
    # 不是兩筆錢。RMBS 就是這樣被虛報一倍。
    if sti > 0 and abs(sti - lti) < 1.0:
        lti, u3 = 0.0, [x + "(與流動桶同額,判為同一筆,不重覆計)" for x in u3]
    if agg > sti + lti:
        return cash, agg, "; ".join(u1 + u4)
    return cash, sti + lti, "; ".join(u1 + u2 + u3)


def yf_total_debt(tk):
    try:
        bs = tk.quarterly_balance_sheet
        if bs is None or bs.empty:
            bs = tk.balance_sheet
        if bs is None or bs.empty:
            return None
        col = bs.columns[0]
        for n in ("Total Debt",):
            if n in bs.index and pd.notna(bs.loc[n, col]):
                return float(bs.loc[n, col])
        tot = 0.0
        for n in ("Long Term Debt", "Current Debt"):
            if n in bs.index and pd.notna(bs.loc[n, col]):
                tot += float(bs.loc[n, col])
        return tot or None
    except Exception:
        return None


def diluted_shares_fixed(fin, shares_now):
    facts = IE.load_facts(fin.cik)
    ser = IE.duration_series(facts, IE.DILUTED_TAGS)
    src, val = None, None
    if ser:
        latest_end = max(e for (_s, e) in ser)
        cands = [((s, e), v) for (s, e), v in ser.items() if e == latest_end]
        cands.sort(key=lambda kv: abs((kv[0][1] - kv[0][0]).days - 91))
        (s0, e0), val = cands[0]
        src = "XBRL 未拆季 %s→%s" % (s0, e0)
    if val and shares_now and not (0.75 <= val / shares_now <= 1.25):
        return float(shares_now), "yfinance 現時股數(XBRL %s 與市場股數相差 >25%%)" % (
            "%.1fM" % (val / 1e6))
    if val:
        return float(val), src
    if shares_now:
        return float(shares_now), "yfinance 現時股數(XBRL 無稀釋股數標籤)"
    return None, "無股數"


# ---------------------------------------------------------------- 同業歸因
def peer_table():
    raw = pd.read_csv(os.path.join(SRC_DIR, "screen_step1_raw.csv"))
    raw = raw.dropna(subset=["sic", "rel_spy"])
    raw["sic4"] = raw["sic"].astype(int)
    raw["sic2"] = raw["sic4"] // 100
    return raw


def peer_kill(raw, ticker):
    row = raw[raw["ticker"] == ticker]
    if row.empty:
        return dict(peer_n=0, peer_med=None, peer_basis="無 SIC", kill_type="資料不足",
                    self_rel_0904=None)
    sic4 = int(row["sic4"].iloc[0]); sic2 = int(row["sic2"].iloc[0])
    self_rel = float(row["rel_spy"].iloc[0])
    grp = raw[(raw["sic4"] == sic4) & (raw["ticker"] != ticker)]
    basis = "四位 SIC %d" % sic4
    if len(grp) < 5:
        grp = raw[(raw["sic2"] == sic2) & (raw["ticker"] != ticker)]
        basis = "兩位 SIC %d" % sic2
    if len(grp) < 5:
        return dict(peer_n=len(grp), peer_med=None, peer_basis=basis + "(同業不足 5 家)",
                    kill_type="資料不足", self_rel_0904=self_rel)
    med = float(grp["rel_spy"].median())
    if med <= -0.15:
        k = "行業殺"
    elif med >= -0.05:
        k = "個別殺"
    else:
        k = "混合"
    return dict(peer_n=int(len(grp)), peer_med=med, peer_basis=basis, kill_type=k,
                self_rel_0904=self_rel)


# ---------------------------------------------------------------- 價格
def price_block(ticker, spy_hist):
    import yfinance as yf
    h = yf.Ticker(ticker).history(period="2y", auto_adjust=False)
    if h.empty:
        return None
    h.index = [d.date() for d in h.index]
    close = h["Close"]
    price = float(close.iloc[-1]); pdate = close.index[-1]
    p0_dates = [d for d in close.index if d >= WIN_START]
    if not p0_dates:
        return None
    p0 = float(close.loc[p0_dates[0]])
    ret = price / p0 - 1.0
    spy0 = float(spy_hist.loc[[d for d in spy_hist.index if d >= WIN_START][0]])
    spy1 = float(spy_hist.iloc[-1])
    rel = ret - (spy1 / spy0 - 1.0)
    ma200 = float(close.iloc[-200:].mean()) if len(close) >= 200 else float("nan")
    ma_series = close.rolling(200).mean()
    slope = (float(ma_series.iloc[-1]) / float(ma_series.iloc[-41]) - 1.0) \
        if len(ma_series.dropna()) > 41 else float("nan")
    px_vs = price / ma200 - 1.0
    if px_vs > 0:
        form = "回調"
    elif slope <= 0:
        form = "殺"
    else:
        form = "線附近"
    yr = close.iloc[-252:]
    mdd = float((yr / yr.cummax() - 1.0).min())
    return dict(price=price, price_date=str(pdate), ret_win=ret, rel_spy_win=rel,
                ma200=ma200, px_vs_ma200=px_vs, ma200_slope_40d=slope, ma200_form=form,
                mdd_1y=mdd)


# ---------------------------------------------------------------- 三個數
def generic_assumptions(fin):
    g = fin.rev_growth_yoy
    g = 0.0 if g is None else max(-0.5, min(1.0, g))
    return IE.Assumptions(
        bad_growth=g, bad_years=5, recovery_growth=g * 0.5,
        target_margin=fin.op_margin, margin_ramp_years=1, horizon=10,
        tax_rate=0.23, sales_to_capital=2.0,
        wacc=WACC, terminal_growth=0.025, terminal_roic=0.15,
    )


def ocf_ttm_of(fin):
    facts = IE.load_facts(fin.cik)
    q = IE.quarterize(IE.duration_series(facts, OCF_TAGS))
    if not q:
        return None
    v, _ = IE.ttm(q, fin.asof)
    return v


def main():
    import yfinance as yf
    raw = peer_table()
    spy = yf.Ticker("SPY").history(period="2y", auto_adjust=False)["Close"]
    spy.index = [d.date() for d in spy.index]

    rows, analyst_raw = [], {}
    for t in TICKERS:
        r = dict(ticker=t)
        try:
            fin = IE.build_financials(t)
        except Exception as e:
            r["error"] = "建帳失敗: %s" % e
            rows.append(r); print(t, r["error"]); continue
        pb = price_block(t, spy)
        if pb is None:
            r["error"] = "無價格"; rows.append(r); print(t, "無價格"); continue
        r.update(pb)
        price = pb["price"]

        # 帳目 —— A-050 更正:有息負債改用擴闊後的標籤清單
        ocf = ocf_ttm_of(fin)
        debt_fix, debt_parts = interest_debt_fixed(fin)
        debt_before = fin.debt
        if debt_fix > (fin.debt or 0.0) * 1.02:
            from dataclasses import replace as _rp2
            fin = _rp2(fin, debt=debt_fix)
            r["debt_fixed"] = True
        else:
            r["debt_fixed"] = False
        r.update(debt_before_fix=debt_before, debt_after_fix=fin.debt,
                 debt_est_combined=debt_parts["combined"], debt_est_parts=debt_parts["parts"])

        # 現金與投資:剔走過期的時點結餘(見 cash_invest_fixed 說明)
        cash_new, inv_new, cash_src = cash_invest_fixed(fin)
        r.update(cash_before_fix=fin.cash, invest_before_fix=fin.investments,
                 cash_after_fix=cash_new, invest_after_fix=inv_new, cash_src=cash_src,
                 cash_fixed=bool(abs((cash_new + inv_new) - (fin.cash + fin.investments))
                                 > 0.01 * max(1.0, fin.cash + fin.investments)))
        if cash_new > 0 or fin.cash == 0:
            from dataclasses import replace as _rp3
            fin = _rp3(fin, cash=cash_new, investments=inv_new)
        def _gate(nd):
            if nd < 0:
                return True, "淨現金 %.0f 百萬" % (-nd / 1e6)
            if ocf and ocf > 0:
                return nd / ocf <= 3.0, "淨負債 ÷ 營運現金流 %.2f 倍" % (nd / ocf)
            return False, "營運現金流不正或缺數"

        nd_ocf = (fin.net_debt / ocf) if (ocf and ocf > 0) else None
        debt_gate, debt_note = _gate(fin.net_debt)
        # 與 yfinance 的 Total Debt 對照。旗號只在「換用 yfinance 的債務數會令負債閘
        # 改判」時才舉——金額有差但兩邊同過或同不過那一關的,不算存疑。
        ydebt = yf_total_debt(yf.Ticker(t))
        r["debt_yf"] = ydebt
        r["debt_gap_vs_yf"] = (ydebt / fin.debt - 1.0) if (ydebt and fin.debt) else None
        if ydebt is not None:
            nd_y = fin.net_debt + (ydebt - (fin.debt or 0.0))
            r["debt_doubt"] = bool(_gate(nd_y)[0] != debt_gate)
        else:
            r["debt_doubt"] = None
        r.update(name=fin.name, asof=str(fin.asof), rev_ttm=fin.rev_ttm,
                 op_margin=fin.op_margin, rev_growth_yoy=fin.rev_growth_yoy,
                 net_debt=fin.net_debt, ocf_ttm=ocf, net_debt_to_ocf=nd_ocf,
                 debt_gate=bool(debt_gate), debt_note=debt_note,
                 diluted_shares=fin.diluted_shares, sbc_ttm=fin.sbc_ttm,
                 fin_notes="; ".join(fin.notes) if fin.notes else "")

        # 市銷率
        try:
            mkt = IE.market_data(fin)
        except Exception as e:
            r["error"] = "市價失敗: %s" % e
            rows.append(r); print(t, r["error"]); continue
        # A-049 更正:稀釋股數不可以拆季
        sh_fix, sh_src = diluted_shares_fixed(fin, mkt.shares_now)
        if sh_fix is None:
            r["error"] = "缺稀釋股數且 yfinance 無股數"
            rows.append(r); print(t, r["error"]); continue
        r["shares_src"] = sh_src
        r["shares_before_fix"] = fin.diluted_shares
        if not fin.diluted_shares or abs(sh_fix / fin.diluted_shares - 1.0) > 0.02:
            from dataclasses import replace as _rp
            fin = _rp(fin, diluted_shares=sh_fix)
            r["diluted_shares"] = fin.diluted_shares
            r["shares_fixed"] = True
            mkt = IE.market_data(fin)
        else:
            r["shares_fixed"] = False
        ps_now = price * fin.diluted_shares / fin.rev_ttm
        p50_4y = mkt.ps_hist.get("p50"); p50_1y = mkt.ps_hist_1y.get("p50")
        p25_1y = mkt.ps_hist_1y.get("p25")
        ratio4 = ps_now / p50_4y if p50_4y else None
        ratio1 = ps_now / p50_1y if p50_1y else None
        if ratio4 is None or ratio1 is None:
            grade = "資料不足"
        elif ratio4 <= 0.8 and ratio1 <= 0.8:
            grade = "兩把尺都過"
        elif ratio4 <= 0.8 or ratio1 <= 0.8:
            grade = "只過一把(重估已完成,不是折讓)"
        else:
            grade = "都不過"
        r.update(ps_now=ps_now, ps_p50_4y=p50_4y, ps_p50_1y=p50_1y, ps_p25_1y=p25_1y,
                 ps_ratio_4y=ratio4, ps_ratio_1y=ratio1, discount_grade=grade)

        # 同業歸因
        r.update(peer_kill(raw, t))

        # 三個數
        a = generic_assumptions(fin)
        try:
            g5 = IE.solve(fin, a, "bad_growth", price, *IE.GBOUND)
        except Exception:
            g5 = None
        try:
            v = IE.value(fin, a)
            per_share, tshare = v.per_share, v.terminal_share
        except Exception:
            per_share, tshare = None, None
        upside = (per_share / price - 1.0) if (per_share and per_share > 0) else None
        unreliable = []
        if fin.op_margin is None or fin.op_margin <= 0:
            unreliable.append("現時營業利潤率 ≤ 0")
        if tshare is not None and tshare > 1.5:
            unreliable.append("終值佔比 >150%")
        if per_share is None or per_share <= 0:
            unreliable.append("每股值無解或 ≤ 0")
        dil = max(0.005, (fin.sbc_ttm or 0.0) / (price * fin.diluted_shares))
        ret1 = (p50_1y * fin.rev_ttm / (fin.diluted_shares * (1 + dil)) / price - 1.0) \
            if p50_1y else None
        ret1_p25 = (p25_1y * fin.rev_ttm / (fin.diluted_shares * (1 + dil)) / price - 1.0) \
            if p25_1y else None
        r.update(n1_implied_g5=g5, n2_per_share=per_share, n2_upside=upside,
                 n2_terminal_share=tshare, n2_unreliable="; ".join(unreliable),
                 dilution_1y=dil, n3_ret_1y=ret1, n3_ret_1y_p25=ret1_p25,
                 g_ref_used=a.bad_growth, margin_used=a.target_margin)

        # 壓力情境
        if p25_1y:
            sp = p25_1y * fin.rev_ttm * 0.9 / fin.diluted_shares
            raw_drop = sp / price - 1.0
        else:
            sp, raw_drop = None, None
        floor = pb["mdd_1y"]
        if raw_drop is None:
            drop, applied = floor, True
        elif raw_drop > floor:          # 機械壓力跌幅比實際最大回撤淺
            drop, applied = floor, True
        else:
            drop, applied = raw_drop, False
        drop = min(drop, -0.05)         # 安全下限,避免除以近零
        r.update(stress_price=sp, stress_drop_raw=raw_drop, stress_drop=drop,
                 stress_floor_applied=bool(applied))

        # 賠率、底線、倉位
        odds = (upside / abs(drop)) if (upside is not None and drop) else None
        r.update(odds=odds,
                 pass_bottom_line=(None if ret1 is None else bool(ret1 >= BOTTOM_LINE_1Y)),
                 position_pct=(LOSS_BUDGET / abs(drop)) if drop else None)

        # 鎖定結論。負債閘不過 = 第一版篩的「壓力下不依賴短期再融資」那一關不過,
        # 按 D-169 第 3 條屬淘汰,不是扣分。
        if (not debt_gate) or pb["ma200_form"] == "回調" or grade == "都不過":
            concl = "不入"
        elif grade == "兩把尺都過" and pb["ma200_form"] == "殺" and debt_gate:
            concl = "入選"
        else:
            concl = "觀察"
        r["A_conclusion"] = concl

        # 分析員資料(原始存檔,標籤另行判斷)
        ar = {}
        try:
            tk = yf.Ticker(t)
            info = tk.info or {}
            ar["info"] = {k: info.get(k) for k in
                          ("targetMeanPrice", "targetHighPrice", "targetLowPrice",
                           "numberOfAnalystOpinions", "recommendationKey", "trailingPE",
                           "forwardPE", "revenueGrowth", "earningsGrowth", "sector",
                           "industry", "longBusinessSummary")}
            try:
                ar["price_targets"] = {k: (float(v) if v is not None else None)
                                       for k, v in dict(tk.analyst_price_targets).items()}
            except Exception as e:
                ar["price_targets_err"] = str(e)
            for nm, attr in (("revenue_estimate", "revenue_estimate"),
                             ("earnings_estimate", "earnings_estimate"),
                             ("growth_estimates", "growth_estimates")):
                try:
                    df = getattr(tk, attr)
                    ar[nm] = json.loads(df.to_json(orient="index")) if df is not None else None
                except Exception as e:
                    ar[nm + "_err"] = str(e)
            try:
                cal = tk.calendar
                ar["calendar"] = {k: str(v) for k, v in dict(cal).items()} if cal else None
            except Exception as e:
                ar["calendar_err"] = str(e)
        except Exception as e:
            ar["err"] = str(e)
        analyst_raw[t] = ar

        # 共識收入增長(下一財年)
        cons_g = None
        try:
            re_ = ar.get("revenue_estimate") or {}
            for key in ("+1y", "0y"):
                if key in re_ and re_[key].get("growth") is not None:
                    cons_g = float(re_[key]["growth"])
                    r["consensus_growth_key"] = key
                    break
        except Exception:
            pass
        if cons_g is None:
            cons_g = (ar.get("info", {}) or {}).get("revenueGrowth")
            if cons_g is not None:
                r["consensus_growth_key"] = "info.revenueGrowth(近況,非預測)"
        r["consensus_rev_growth"] = cons_g
        if cons_g is None or g5 is None:
            lab = "資料不足"
        elif g5 <= cons_g - 0.03:
            lab = "市場比指引更悲觀"
        elif g5 >= cons_g + 0.03:
            lab = "市場比指引更樂觀"
        else:
            lab = "與指引重疊"
        r["mispricing_label_auto"] = lab
        r["gap_vs_consensus_pp"] = (None if (cons_g is None or g5 is None)
                                    else (g5 - cons_g) * 100)

        rows.append(r)
        print("%-6s %s 現價 %.2f 數一 %s 數二 %s 數三 %s 壓力 %.0f%% 賠率 %s %s %s"
              % (t, concl,
                 price,
                 "n/a" if g5 is None else "%+.1f%%" % (g5 * 100),
                 "n/a" if upside is None else "%+.0f%%" % (upside * 100),
                 "n/a" if ret1 is None else "%+.0f%%" % (ret1 * 100),
                 drop * 100,
                 "n/a" if odds is None else "%.2f" % odds,
                 lab, r["ma200_form"]))

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT_DIR, "screen60_full.csv"), index=False, encoding="utf-8")
    with open(os.path.join(OUT_DIR, "screen60_full.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1, default=str)
    with open(os.path.join(OUT_DIR, "yf_analyst_raw.json"), "w", encoding="utf-8") as fh:
        json.dump(analyst_raw, fh, ensure_ascii=False, indent=1, default=str)
    print("=" * 70)
    print("完成", len(df), "家;錯誤", int(df["error"].notna().sum()) if "error" in df else 0)
    if "A_conclusion" in df:
        print(df["A_conclusion"].value_counts().to_dict())
        print(df["mispricing_label_auto"].value_counts().to_dict())
        print("過底線", int(df["pass_bottom_line"].fillna(False).sum()))


if __name__ == "__main__":
    main()
