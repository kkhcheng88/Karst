#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
implied_expectations.py --- 隱含預期計算器原型 (KARST-183)

由現價反推「市場正在假設的經營路徑」,而不是由假設算出一個目標價。
輸出兩件分開的東西:
  (甲) 長期價值範圍 (每股) --- 給定經營假設,公司值多少
  (乙) 一年持有回報情境    --- 一年後市場只部分承認 / 仍保持折讓時的回報
(乙) 不由 (甲) 自動推導:它用公司自己的歷史市銷率分佈當退出倍數。

資料來源:
  data/sec/companyfacts/CIK##########.json.gz  (SEC XBRL 申報帳目)
  yfinance                                     (現價、股數)

不碰 karst/ 引擎。不做回測、不做參數掃描。

用法:
  python strategy/tools/implied_expectations.py SNOW AXTI
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import math
import os
import sys
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FACTS_DIR = os.path.join(REPO, "data", "sec", "companyfacts")
TICKERS_JSON = os.path.join(REPO, "data", "sec", "company_tickers.json")

DAY = dt.timedelta(days=1)


# ----------------------------------------------------------------------------
# 一、SEC companyfacts 讀取
# ----------------------------------------------------------------------------

def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def load_facts(cik: str) -> dict:
    path = os.path.join(FACTS_DIR, "CIK%s.json.gz" % cik)
    if os.path.exists(path):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    path = os.path.join(FACTS_DIR, "CIK%s.json" % cik)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def cik_for(ticker: str) -> str:
    with open(TICKERS_JSON, "r", encoding="utf-8") as fh:
        m = json.load(fh)
    cik = m.get(ticker.upper())
    if not cik:
        raise KeyError("company_tickers.json 沒有 %s" % ticker)
    return cik


def _rows(facts: dict, tag: str, taxonomy: str = "us-gaap") -> List[dict]:
    node = facts.get("facts", {}).get(taxonomy, {}).get(tag)
    if not node:
        return []
    out: List[dict] = []
    for unit, rows in node.get("units", {}).items():
        if unit not in ("USD", "shares", "USD/shares"):
            continue
        out.extend(rows)
    return out


def duration_series(facts: dict, tags: Sequence[str]) -> Dict[Tuple[dt.date, dt.date], float]:
    """期間型事實 (收入、利潤...):回傳 {(start, end): val},同期取最後申報的一份。"""
    best: Dict[Tuple[dt.date, dt.date], Tuple[str, float]] = {}
    for tag in tags:
        for r in _rows(facts, tag):
            if "start" not in r or "end" not in r:
                continue
            k = (_d(r["start"]), _d(r["end"]))
            filed = r.get("filed", "")
            if k not in best or filed >= best[k][0]:
                best[k] = (filed, float(r["val"]))
        if best:
            break  # 用第一個有資料的標籤,不混用不同定義
    return {k: v[1] for k, v in best.items()}


def _tag_series(facts: dict, tag: str) -> Dict[dt.date, float]:
    best: Dict[dt.date, Tuple[str, float]] = {}
    for r in _rows(facts, tag):
        if "start" in r or "end" not in r:
            continue
        k = _d(r["end"])
        filed = r.get("filed", "")
        if k not in best or filed >= best[k][0]:
            best[k] = (filed, float(r["val"]))
    return {k: v[1] for k, v in best.items()}


def instant_series(facts: dict, tags: Sequence[str], asof: Optional[dt.date] = None,
                    tol_days: int = 200, label: str = "", notes: Optional[List[str]] = None
                    ) -> Dict[dt.date, float]:
    """時點型事實 (現金、負債、股數)。有序後備清單:依序試每個標籤,取第一個
    『覆蓋到 asof 附近 tol_days 日內』的標籤 —— 不是第一個有任何資料的標籤(KARST-183
    的舊寫法在公司換標籤時會卡死在舊標籤的過期資料上,見 A-048/lululemon:
    CashAndCashEquivalentsAtCarryingValue 停在 2019 年,舊寫法見它非空即停,
    現金被 _latest 的容差濾成 0,淨負債誇大 15.15 億美元)。

    若沒有任何標籤覆蓋到 asof 附近,退回「合併全部標籤取每個時點最後申報值」的
    盡力結果,並在 notes 印警告 —— 不再靜默當 0。asof=None 時(呼叫端不關心新鮮度)
    沿用「第一個有資料的標籤」這條舊行為。
    """
    if asof is None:
        for tag in tags:
            s = _tag_series(facts, tag)
            if s:
                return s
        return {}

    for tag in tags:
        s = _tag_series(facts, tag)
        if not s:
            continue
        if (asof - max(s)).days <= tol_days:
            return s

    # 有序後備清單全部落空:合併全部標籤,每個時點取最後申報值,盡力給一個答案
    merged: Dict[dt.date, Tuple[str, float]] = {}
    for tag in tags:
        for r in _rows(facts, tag):
            if "start" in r or "end" not in r:
                continue
            k = _d(r["end"])
            filed = r.get("filed", "")
            if k not in merged or filed >= merged[k][0]:
                merged[k] = (filed, float(r["val"]))
    series = {k: v[1] for k, v in merged.items()}
    # 只在「有資料但太舊」時印警告 —— 這才是缺數的風險所在(A-048 那種)。
    # 全部標籤完全沒有資料(series 空)多數是公司真的沒有這一項(例如沒有租賃負債、
    # 沒有少數股東權益),不是抽取缺陷,不印警告以免洗版;_latest 照舊當 0。
    if notes is not None and series:
        notes.append(
            "警告:%s 的候選標籤(%s)全部缺 asof(%s)前後 %d 日內的資料,"
            "最新只到 %s,用這筆舊值代替 —— 可能失真,建議人手核對資產負債表。"
            % (label or "/".join(tags), "/".join(tags), asof, tol_days, max(series)))
    return series


def quarterize(series: Dict[Tuple[dt.date, dt.date], float]) -> Dict[dt.date, float]:
    """把年 / 半年 / 累計期拆成單季,回傳 {季末日: 單季值}。

    做法:對每個長於 100 日的期間 P,若存在同起點的較短期間 Q,
    則 P - Q 就是 (Q.end+1 .. P.end) 這一段;反覆迭代直到收斂。
    """
    per = dict(series)
    changed = True
    while changed:
        changed = False
        by_start: Dict[dt.date, List[Tuple[dt.date, float]]] = {}
        for (s, e), v in per.items():
            by_start.setdefault(s, []).append((e, v))
        for (s, e), v in list(per.items()):
            if (e - s).days <= 100:
                continue
            for (e2, v2) in by_start.get(s, []):
                if e2 >= e:
                    continue
                k = (e2 + DAY, e)
                if k not in per:
                    per[k] = v - v2
                    changed = True
    out: Dict[dt.date, float] = {}
    for (s, e), v in per.items():
        if 80 <= (e - s).days <= 100:
            out[e] = v
    return out


def ttm(quarters: Dict[dt.date, float], asof: Optional[dt.date] = None) -> Tuple[Optional[float], List[dt.date]]:
    """最近四季合計。回傳 (值, 用到的四個季末)。缺季就回 None。"""
    ends = sorted(quarters)
    if asof:
        ends = [e for e in ends if e <= asof]
    if len(ends) < 4:
        return None, []
    use = ends[-4:]
    # 四季必須大致連續 (跨度 330-400 日)
    span = (use[-1] - use[0]).days
    if not (240 <= span <= 300):
        pass  # 仍然用,但由呼叫端自行判斷
    return sum(quarters[e] for e in use), use


def ttm_series(quarters: Dict[dt.date, float]) -> Dict[dt.date, float]:
    ends = sorted(quarters)
    out = {}
    for i in range(3, len(ends)):
        window = ends[i - 3:i + 1]
        if (window[-1] - window[0]).days > 330:
            continue
        out[ends[i]] = sum(quarters[e] for e in window)
    return out


REV_TAGS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
            "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"]
EBIT_TAGS = ["OperatingIncomeLoss"]
SBC_TAGS = ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"]
DA_TAGS = ["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet", "Depreciation"]
CAPEX_TAGS = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"]
TAX_TAGS = ["IncomeTaxExpenseBenefit", "IncomeTaxExpenseBenefitContinuingOperations"]
PRETAX_TAGS = ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
               "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"]
DILUTED_TAGS = ["WeightedAverageNumberOfDilutedSharesOutstanding",
                "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
                "WeightedAverageNumberOfSharesOutstandingBasic"]
CASH_TAGS = ["CashAndCashEquivalentsAtCarryingValue",
             "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
             "CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations"]
STI_TAGS = ["ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
            "MarketableSecuritiesCurrent"]
LTI_TAGS = ["AvailableForSaleSecuritiesDebtSecuritiesNoncurrent", "MarketableSecuritiesNoncurrent",
            "LongTermInvestments"]
DEBT_CUR_TAGS = ["LongTermDebtCurrent", "DebtCurrent"]
DEBT_NC_TAGS = ["LongTermDebtNoncurrent", "ConvertibleDebtNoncurrent", "LongTermDebt"]
LEASE_CUR_TAGS = ["OperatingLeaseLiabilityCurrent"]
LEASE_NC_TAGS = ["OperatingLeaseLiabilityNoncurrent"]
NCI_TAGS = ["MinorityInterest"]


@dataclass
class Financials:
    ticker: str
    cik: str
    name: str
    asof: dt.date                 # 最近一季季末
    rev_ttm: float
    ebit_ttm: float
    sbc_ttm: float
    da_ttm: float
    capex_ttm: float
    tax_rate_hist: Optional[float]
    diluted_shares: float
    cash: float
    investments: float
    debt: float
    lease_debt: float
    nci: float = 0.0
    rev_ttm_hist: Dict[dt.date, float] = field(default_factory=dict)
    rev_q: Dict[dt.date, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    @property
    def net_debt(self) -> float:
        """淨負債口徑:有息負債 + 經營租賃負債 + 少數股東權益帳面值 − 現金 − 投資。
        少數股東權益放這裡,是因為企業價值屬於全體資本提供者,不只母公司股東。"""
        return self.debt + self.lease_debt + self.nci - self.cash - self.investments

    @property
    def op_margin(self) -> float:
        return self.ebit_ttm / self.rev_ttm

    @property
    def rev_growth_yoy(self) -> Optional[float]:
        ends = sorted(self.rev_ttm_hist)
        if len(ends) < 5:
            return None
        return self.rev_ttm_hist[ends[-1]] / self.rev_ttm_hist[ends[-5]] - 1.0


def _latest(series: Dict[dt.date, float], asof: dt.date, tol_days: int = 200) -> float:
    ends = [e for e in series if e <= asof]
    if not ends:
        return 0.0
    e = max(ends)
    if (asof - e).days > tol_days:
        return 0.0
    return series[e]


def build_financials(ticker: str) -> Financials:
    cik = cik_for(ticker)
    facts = load_facts(cik)
    notes: List[str] = []

    rev_q = quarterize(duration_series(facts, REV_TAGS))
    ebit_q = quarterize(duration_series(facts, EBIT_TAGS))
    sbc_q = quarterize(duration_series(facts, SBC_TAGS))
    da_q = quarterize(duration_series(facts, DA_TAGS))
    capex_q = quarterize(duration_series(facts, CAPEX_TAGS))
    tax_q = quarterize(duration_series(facts, TAX_TAGS))
    pretax_q = quarterize(duration_series(facts, PRETAX_TAGS))
    dil_q = quarterize(duration_series(facts, DILUTED_TAGS))

    asof = max(rev_q)
    rev_ttm, used = ttm(rev_q)
    ebit_ttm, _ = ttm(ebit_q, asof)
    sbc_ttm, _ = ttm(sbc_q, asof)
    da_ttm, _ = ttm(da_q, asof)
    capex_ttm, _ = ttm(capex_q, asof)

    if sbc_ttm is None:
        sbc_ttm = 0.0
        notes.append("companyfacts 沒有可用的股權薪酬季度標籤,SBC 當 0 處理 —— 這會高估自由現金流。")
    if da_ttm is None:
        da_ttm = 0.0
        notes.append("缺折舊攤銷標籤。")
    if capex_ttm is None:
        capex_ttm = 0.0
        notes.append("缺資本開支標籤。")
    if ebit_ttm is None:
        raise RuntimeError("%s 缺 OperatingIncomeLoss,無法建模" % ticker)

    # 歷史實際稅率(近四年累計,只在稅前為正時才有意義)
    tax_rate_hist = None
    tt, _ = ttm(tax_q, asof) if tax_q else (None, [])
    pt, _ = ttm(pretax_q, asof) if pretax_q else (None, [])
    if tt is not None and pt is not None and pt > 0:
        tax_rate_hist = tt / pt

    dil_ttm_ends = sorted(dil_q)
    diluted_shares = dil_q[dil_ttm_ends[-1]] if dil_ttm_ends else 0.0

    def _inst(tags: Sequence[str], label: str) -> float:
        return _latest(instant_series(facts, tags, asof=asof, label=label, notes=notes), asof)

    cash = _inst(CASH_TAGS, "現金")
    inv = _inst(STI_TAGS, "短期投資") + _inst(LTI_TAGS, "長期投資")
    debt = _inst(DEBT_CUR_TAGS, "短期有息負債") + _inst(DEBT_NC_TAGS, "長期有息負債")
    lease = _inst(LEASE_CUR_TAGS, "短期經營租賃負債") + _inst(LEASE_NC_TAGS, "長期經營租賃負債")
    nci = _inst(NCI_TAGS, "少數股東權益")

    return Financials(
        ticker=ticker.upper(), cik=cik, name=facts.get("entityName", ticker),
        asof=asof, rev_ttm=rev_ttm, ebit_ttm=ebit_ttm, sbc_ttm=sbc_ttm,
        da_ttm=da_ttm, capex_ttm=capex_ttm, tax_rate_hist=tax_rate_hist,
        diluted_shares=diluted_shares, cash=cash, investments=inv,
        debt=debt, lease_debt=lease, nci=nci,
        rev_ttm_hist=ttm_series(rev_q), rev_q=rev_q, notes=notes,
    )


# ----------------------------------------------------------------------------
# 二、假設 (三組不可省)
# ----------------------------------------------------------------------------

@dataclass
class Assumptions:
    # --- 第一組:經營路徑 ---
    bad_growth: float          # 惡化期年收入增長率(可為負)
    bad_years: int             # 惡化持續幾年
    recovery_growth: float     # 惡化期結束後的年收入增長率
    target_margin: float       # 第 N 年的正常化營業利潤率(GAAP,已含股權薪酬)
    margin_ramp_years: int     # 由現時利潤率線性走到目標利潤率要幾年
    horizon: int = 10          # 明確預測期年數

    # --- 第二組:現金流轉換 ---
    tax_rate: float = 0.23     # 邊際稅率
    sales_to_capital: float = 2.0   # 每 1 元再投資帶來幾元新收入(增長再投資的價格)
    sbc_treatment: str = "expensed"  # 股權薪酬:在營業利潤中已扣,配稀釋後股數

    # --- 第三組:長期估值 ---
    wacc: float = 0.10
    terminal_growth: float = 0.025
    terminal_roic: float = 0.15   # 終值期投入資本回報率,決定終值再投資率


@dataclass
class Valuation:
    per_share: float
    ev: float
    pv_explicit: float
    pv_terminal: float
    terminal_share: float      # 終值佔企業價值比重
    path: List[dict]


def value(fin: Financials, a: Assumptions) -> Valuation:
    rev = fin.rev_ttm
    m0 = fin.op_margin
    pv_fcff = 0.0
    path = []
    prev_rev = rev
    for t in range(1, a.horizon + 1):
        g = a.bad_growth if t <= a.bad_years else a.recovery_growth
        rev = prev_rev * (1.0 + g)
        # 利潤率:由現時水平線性走向目標
        k = min(t / float(max(a.margin_ramp_years, 1)), 1.0)
        margin = m0 + (a.target_margin - m0) * k
        ebit = rev * margin
        nopat = ebit * (1.0 - a.tax_rate) if ebit > 0 else ebit  # 虧損不給稅盾
        dr = rev - prev_rev
        reinvest = max(dr, 0.0) / a.sales_to_capital
        fcff = nopat - reinvest
        df = 1.0 / (1.0 + a.wacc) ** t
        pv_fcff += fcff * df
        path.append(dict(t=t, rev=rev, growth=g, margin=margin, ebit=ebit,
                         nopat=nopat, reinvest=reinvest, fcff=fcff, pv=fcff * df))
        prev_rev = rev

    # 終值:第 N+1 年,再投資率 = g / ROIC
    rev_n1 = prev_rev * (1.0 + a.terminal_growth)
    nopat_n1 = rev_n1 * a.target_margin * (1.0 - a.tax_rate)
    reinv_rate = a.terminal_growth / a.terminal_roic
    fcff_n1 = nopat_n1 * (1.0 - reinv_rate)
    if a.wacc <= a.terminal_growth:
        raise ValueError("折現率必須高於終值增長率")
    tv = fcff_n1 / (a.wacc - a.terminal_growth)
    pv_tv = tv / (1.0 + a.wacc) ** a.horizon

    ev = pv_fcff + pv_tv
    equity = ev - fin.net_debt
    per_share = equity / fin.diluted_shares
    return Valuation(per_share=per_share, ev=ev, pv_explicit=pv_fcff, pv_terminal=pv_tv,
                     terminal_share=(pv_tv / ev if ev else float("nan")), path=path)


# ----------------------------------------------------------------------------
# 三、反推 (由現價解出其中一項假設)
# ----------------------------------------------------------------------------

def solve(fin: Financials, a: Assumptions, field_name: str, price: float,
          lo: float, hi: float, tol: float = 1e-4) -> Optional[float]:
    """二分法解出 field_name,使每股價值 = 現價。單調性由呼叫端保證。"""
    def f(x: float) -> float:
        try:
            return value(fin, replace(a, **{field_name: x})).per_share - price
        except Exception:
            return float("nan")

    flo, fhi = f(lo), f(hi)
    if math.isnan(flo) or math.isnan(fhi) or flo * fhi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2.0
        fm = f(mid)
        if abs(hi - lo) < tol:
            return mid
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2.0


def sensitivity(fin: Financials, a: Assumptions, price: float,
                keys: Sequence[str], solve_field: str,
                lo: float, hi: float) -> List[dict]:
    """關鍵假設各改 +10% (相對),反推值改多少。"""
    base = solve(fin, a, solve_field, price, lo, hi)
    out = []
    for k in keys:
        v0 = getattr(a, k)
        for sign in (+1, -1):
            v1 = v0 * (1.0 + 0.10 * sign) if not isinstance(v0, int) else max(1, int(round(v0 * (1 + 0.10 * sign))))
            got = solve(fin, replace(a, **{k: v1}), solve_field, price, lo, hi)
            out.append(dict(key=k, bump=("+10%" if sign > 0 else "-10%"),
                            value=v1, solved=got, base=base,
                            delta=(None if got is None or base is None else got - base)))
    return out


def value_sensitivity(fin: Financials, a: Assumptions, keys: Sequence[str]) -> List[dict]:
    base = value(fin, a).per_share
    out = []
    for k in keys:
        v0 = getattr(a, k)
        for sign in (+1, -1):
            v1 = v0 * (1.0 + 0.10 * sign) if not isinstance(v0, int) else max(1, int(round(v0 * (1 + 0.10 * sign))))
            ps = value(fin, replace(a, **{k: v1})).per_share
            out.append(dict(key=k, bump=("+10%" if sign > 0 else "-10%"), value=v1,
                            per_share=ps, base=base, pct=(ps / base - 1.0) if base else None))
    return out


# ----------------------------------------------------------------------------
# 四、市場資料與歷史市銷率
# ----------------------------------------------------------------------------

@dataclass
class Market:
    price: float
    price_date: dt.date
    shares_now: Optional[float]
    ps_hist: Dict[str, float]   # 歷史市銷率百分位(長窗)
    ps_now: float
    ps_hist_1y: Dict[str, float] = field(default_factory=dict)  # 近一年


def market_data(fin: Financials, years: int = 4) -> Market:
    import yfinance as yf
    tk = yf.Ticker(fin.ticker)
    hist = tk.history(period="%dy" % (years + 1), auto_adjust=False)
    if hist.empty:
        raise RuntimeError("yfinance 沒有 %s 的價格" % fin.ticker)
    price = float(hist["Close"].iloc[-1])
    pdate = hist.index[-1].date()
    try:
        shares_now = float(tk.fast_info.get("shares"))
    except Exception:
        shares_now = None

    # 歷史市銷率:每個交易日的收市價 / 當時最近一期 TTM 每股收入
    ttm_ends = sorted(fin.rev_ttm_hist)
    ps_all: List[Tuple[dt.date, float]] = []
    shares = fin.diluted_shares
    for tsd, row in hist.iterrows():
        d0 = tsd.date()
        # 假設帳目在季末後 40 日才公開
        avail = [e for e in ttm_ends if e + dt.timedelta(days=40) <= d0]
        if not avail:
            continue
        r = fin.rev_ttm_hist[avail[-1]]
        if r <= 0:
            continue
        ps_all.append((d0, float(row["Close"]) * shares / r))

    def pcts(vals: List[float]) -> Dict[str, float]:
        v = sorted(vals)
        if not v:
            return {"n": 0}
        def q(p):
            return v[min(len(v) - 1, max(0, int(round(p * (len(v) - 1)))))]
        return {"p10": q(0.10), "p25": q(0.25), "p50": q(0.50),
                "p75": q(0.75), "p90": q(0.90), "n": len(v)}

    cutoff = pdate - dt.timedelta(days=365)
    ps_now = price * shares / fin.rev_ttm
    return Market(price=price, price_date=pdate, shares_now=shares_now,
                  ps_hist=pcts([v for _, v in ps_all]),
                  ps_hist_1y=pcts([v for d0, v in ps_all if d0 >= cutoff]),
                  ps_now=ps_now)


# ----------------------------------------------------------------------------
# 五、輸出 (乙):一年持有回報情境 —— 不由 (甲) 推導
# ----------------------------------------------------------------------------

def one_year_scenarios(fin: Financials, mkt: Market, growth_cases: Dict[str, float],
                       multiple_cases: Dict[str, float], dilution: float) -> List[dict]:
    """一年後股價 = 退出市銷率 x 屆時 TTM 收入 / 稀釋後股數。

    退出倍數來自公司自己過去幾年的市銷率分佈,不是 (甲) 的折現值。
    dilution:一年內股數淨增幅(股權薪酬造成)。
    """
    rows = []
    shares1 = fin.diluted_shares * (1.0 + dilution)
    for gname, g in growth_cases.items():
        rev1 = fin.rev_ttm * (1.0 + g)
        for mname, mult in multiple_cases.items():
            px1 = mult * rev1 / shares1
            rows.append(dict(growth_case=gname, growth=g, mult_case=mname, mult=mult,
                             rev1=rev1, price1=px1, ret=px1 / mkt.price - 1.0))
    return rows


# ----------------------------------------------------------------------------
# 六、CLI
# ----------------------------------------------------------------------------

def fmt_m(x: float) -> str:
    return "%.0f" % (x / 1e6)


CASES: Dict[str, dict] = {
    # 每家一組「固定假設」。這些是判斷,不是資料;改動要在報告的假設清單裡寫明理由。
    "SNOW": dict(
        wacc=0.10, terminal_growth=0.025, terminal_roic=0.15, tax_rate=0.23,
        sales_to_capital=3.0, margin_ramp_years=8, horizon=10,
        recovery_growth=0.06,          # 第一階段之後(第 6-10 年)的收入增長
        target_margin=0.20,            # 第 10 年正常化 GAAP 營業利潤率(已扣股權薪酬)
        stage1_growth_ref=0.25,        # 反推利潤率時固定的第一階段增長
        stage1_years_ref=5,
        dilution_1y=0.020,             # 一年淨稀釋
        g1_cases={"惡化(收入 +10%)": 0.10, "減速(+20%)": 0.20, "維持現速(+30%)": 0.30},
    ),
    "AXTI": dict(
        wacc=0.12, terminal_growth=0.025, terminal_roic=0.12, tax_rate=0.23,
        sales_to_capital=1.0, margin_ramp_years=6, horizon=10,
        recovery_growth=0.05,
        target_margin=0.18,
        stage1_growth_ref=0.30,
        stage1_years_ref=5,
        dilution_1y=0.025,
        g1_cases={"訂單見頂(收入 -10%)": -0.10, "增長腰斬(+25%)": 0.25, "維持現速(+55%)": 0.55},
    ),
}

SENS_KEYS = ["wacc", "terminal_growth", "sales_to_capital", "tax_rate", "horizon"]
GBOUND = (-0.50, 3.00)   # 反推收入增長率的搜尋範圍
MBOUND = (-0.20, 1.00)   # 反推營業利潤率的搜尋範圍(超過 100% 即當無解)


def annualise_latest_quarter(fin: Financials) -> Financials:
    """把最近一季 x4 當起步年。用於業績剛剛轉折、TTM 明顯落後的公司。
    只換起步年的收入與營業利潤,資產負債表與股數不變。"""
    e = max(fin.rev_q)
    ebit_q = None
    facts = load_facts(fin.cik)
    eq = quarterize(duration_series(facts, EBIT_TAGS))
    sq = quarterize(duration_series(facts, SBC_TAGS))
    if e not in eq:
        raise RuntimeError("最近一季沒有營業利潤")
    out = replace(fin, rev_ttm=fin.rev_q[e] * 4.0, ebit_ttm=eq[e] * 4.0,
                  sbc_ttm=(sq.get(e, 0.0) * 4.0))
    out.notes = list(fin.notes) + [
        "起步年用最近一季(%s)年化,不是 TTM —— TTM 落後於已轉折的經營水平。" % e]
    return out


def analyse(ticker: str, base_mode: str = "ttm") -> dict:
    fin = build_financials(ticker)
    mkt = market_data(fin)
    if base_mode == "annualized_q":
        fin = annualise_latest_quarter(fin)
    C = CASES[fin.ticker]
    base = Assumptions(
        bad_growth=C["stage1_growth_ref"], bad_years=C["stage1_years_ref"],
        recovery_growth=C["recovery_growth"], target_margin=C["target_margin"],
        margin_ramp_years=C["margin_ramp_years"], horizon=C["horizon"],
        tax_rate=C["tax_rate"], sales_to_capital=C["sales_to_capital"],
        wacc=C["wacc"], terminal_growth=C["terminal_growth"],
        terminal_roic=C["terminal_roic"],
    )
    px = mkt.price

    # ---- 反推表 A:固定利潤率,解「第一階段年均收入增長率」 ----
    tableA = []
    for D in (3, 5, 7):
        a = replace(base, bad_years=D)
        g = solve(fin, a, "bad_growth", px, *GBOUND)
        v = value(fin, replace(a, bad_growth=g)) if g is not None else None
        tableA.append(dict(
            years=D, implied_growth=g,
            gap_vs_current=(None if g is None or fin.rev_growth_yoy is None else g - fin.rev_growth_yoy),
            terminal_share=(v.terminal_share if v else None),
            rev_at_end=(v.path[D - 1]["rev"] if v else None),
            rev_at_horizon=(v.path[-1]["rev"] if v else None),
            sens=sensitivity(fin, a, px, SENS_KEYS + ["target_margin"], "bad_growth", *GBOUND),
        ))

    # ---- 反推表 B:固定收入路徑,解「正常化營業利潤率」 ----
    tableB = []
    for g1 in sorted({C["stage1_growth_ref"], C["stage1_growth_ref"] - 0.10,
                      C["stage1_growth_ref"] + 0.10}):
        a = replace(base, bad_growth=g1)
        m = solve(fin, a, "target_margin", px, *MBOUND)
        v = value(fin, replace(a, target_margin=m)) if m is not None else None
        tableB.append(dict(
            stage1_growth=g1, implied_margin=m,
            terminal_share=(v.terminal_share if v else None),
            ebit_at_horizon=(v.path[-1]["ebit"] if v else None),
            sens=sensitivity(fin, a, px, SENS_KEYS + ["bad_growth"], "target_margin", *MBOUND),
        ))

    # ---- 輸出(甲):長期價值範圍 ----
    scen = {
        "悲觀": replace(base, bad_growth=C["stage1_growth_ref"] - 0.15,
                      target_margin=C["target_margin"] - 0.08, wacc=C["wacc"] + 0.02,
                      recovery_growth=C["recovery_growth"] - 0.02, terminal_growth=0.015),
        "基準": base,
        "樂觀": replace(base, bad_growth=C["stage1_growth_ref"] + 0.15,
                      target_margin=C["target_margin"] + 0.08, wacc=C["wacc"] - 0.01,
                      recovery_growth=C["recovery_growth"] + 0.02, terminal_growth=0.03),
    }
    valA = {}
    for name, a in scen.items():
        v = value(fin, a)
        valA[name] = dict(per_share=v.per_share, ev=v.ev, terminal_share=v.terminal_share,
                          upside=v.per_share / px - 1.0,
                          assum=dict(bad_growth=a.bad_growth, bad_years=a.bad_years,
                                     recovery_growth=a.recovery_growth,
                                     target_margin=a.target_margin, wacc=a.wacc,
                                     terminal_growth=a.terminal_growth))
    valA_sens = value_sensitivity(fin, base, SENS_KEYS + ["bad_growth", "target_margin"])

    # ---- 輸出(乙):一年持有回報情境(退出倍數來自公司自己的歷史市銷率) ----
    # 退出倍數的語意要看現價站在自己歷史區間的哪一邊:
    #  - 現價低於歷史中位數 = 帶折讓 -> 情境是「折讓維持 / 部分修復 / 完全修復」
    #  - 現價高於歷史中位數 = 帶溢價 -> 情境是「溢價維持 / 部分回落 / 回到常態」
    h1, h4 = mkt.ps_hist_1y, mkt.ps_hist
    if mkt.ps_now >= h4.get("p50", mkt.ps_now):
        mult_cases = {
            "溢價維持(現時 %.1fx)" % mkt.ps_now: mkt.ps_now,
            "小幅回落(近一年 50 分位 %.1fx)" % h1["p50"]: h1["p50"],
            "回落至近一年低位(25 分位 %.1fx)" % h1["p25"]: h1["p25"],
            "回到四年常態(中位數 %.1fx)" % h4["p50"]: h4["p50"],
        }
    else:
        mult_cases = {
            "折讓維持(四年 25 分位 %.1fx)" % h4["p25"]: h4["p25"],
            "部分修復(四年中位數 %.1fx)" % h4["p50"]: h4["p50"],
            "倍數不變(現時 %.1fx)" % mkt.ps_now: mkt.ps_now,
            "完全修復(四年 75 分位 %.1fx)" % h4["p75"]: h4["p75"],
        }
    # 一年淨稀釋:用股權薪酬佔市值的比例代替(授出價值 / 市值 = 新增股數 / 總股數),
    # 下限 0.5%。這是「甲」把股權薪酬當費用之後,「乙」這一邊唯一要另計的稀釋。
    dilution = max(0.005, fin.sbc_ttm / (mkt.price * fin.diluted_shares))
    oneyear = one_year_scenarios(fin, mkt, C["g1_cases"], mult_cases, dilution)

    return dict(fin=fin, mkt=mkt, base=base, tableA=tableA, tableB=tableB,
                valA=valA, valA_sens=valA_sens, oneyear=oneyear,
                mult_cases=mult_cases, dilution_1y=dilution, cfg=C)


def _jsonable(o):
    if isinstance(o, (Financials, Assumptions, Market)):
        return {k: _jsonable(v) for k, v in o.__dict__.items()}
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, dt.date):
        return str(o)
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    return o


def main(argv=None):
    ap = argparse.ArgumentParser(description="隱含預期計算器原型")
    ap.add_argument("tickers", nargs="+")
    ap.add_argument("--json", help="把結果寫成 JSON 到這個路徑")
    ap.add_argument("--full", action="store_true", help="跑完整反推 + 敏感度 + 兩個輸出")
    ap.add_argument("--base", default="ttm", choices=["ttm", "annualized_q"],
                    help="起步年:TTM(預設)或最近一季年化")
    args = ap.parse_args(argv)

    if args.full:
        res = {}
        for t in args.tickers:
            r = analyse(t, base_mode=args.base)
            res[t.upper()] = _jsonable(r)
            f, m = r["fin"], r["mkt"]
            print("=" * 72)
            print("%s  price=%.2f (%s)  rev_ttm=%.1fM  margin=%.1f%%  netdebt=%.1fM  shares=%.1fM"
                  % (f.ticker, m.price, m.price_date, f.rev_ttm / 1e6, 100 * f.op_margin,
                     f.net_debt / 1e6, f.diluted_shares / 1e6))
            print("-- A: implied stage-1 revenue CAGR (margin fixed) --")
            for row in r["tableA"]:
                print("   D=%dy  g=%s  vs_now=%s  TVshare=%s"
                      % (row["years"],
                         "%.1f%%" % (100 * row["implied_growth"]) if row["implied_growth"] is not None else "n/s",
                         "%.1fpp" % (100 * row["gap_vs_current"]) if row["gap_vs_current"] is not None else "-",
                         "%.0f%%" % (100 * row["terminal_share"]) if row["terminal_share"] is not None else "-"))
                for s in row["sens"]:
                    if s["delta"] is not None:
                        print("        %-18s %s -> g %+.1fpp" % (s["key"], s["bump"], 100 * s["delta"]))
            print("-- B: implied normalised operating margin (revenue path fixed) --")
            for row in r["tableB"]:
                print("   g1=%.0f%%  margin=%s  TVshare=%s"
                      % (100 * row["stage1_growth"],
                         "%.1f%%" % (100 * row["implied_margin"]) if row["implied_margin"] is not None else "n/s",
                         "%.0f%%" % (100 * row["terminal_share"]) if row["terminal_share"] is not None else "-"))
                for s in row["sens"]:
                    if s["delta"] is not None:
                        print("        %-18s %s -> margin %+.1fpp" % (s["key"], s["bump"], 100 * s["delta"]))
            print("-- (A) long-term value range --")
            for k, v in r["valA"].items():
                print("   %-4s %8.2f/sh  upside %+6.1f%%  TVshare %.0f%%"
                      % (k, v["per_share"], 100 * v["upside"], 100 * v["terminal_share"]))
            for s in r["valA_sens"]:
                print("        %-18s %s -> value %+.1f%%" % (s["key"], s["bump"], 100 * s["pct"]))
            print("-- (B) one-year holding return --")
            for row in r["oneyear"]:
                print("   %-22s x %-26s px1=%8.2f  ret=%+7.1f%%"
                      % (row["growth_case"], row["mult_case"], row["price1"], 100 * row["ret"]))
        if args.json:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(res, fh, indent=2, ensure_ascii=False, default=str)
        return res

    out = {}
    for t in args.tickers:
        fin = build_financials(t)
        mkt = market_data(fin)
        print("=" * 70)
        print("%s (%s) CIK %s  帳目截至 %s" % (fin.ticker, fin.name, fin.cik, fin.asof))
        print("  TTM 收入 %s M / 營業利潤 %s M (利潤率 %.1f%%) / 股權薪酬 %s M"
              % (fmt_m(fin.rev_ttm), fmt_m(fin.ebit_ttm), 100 * fin.op_margin, fmt_m(fin.sbc_ttm)))
        print("  折舊攤銷 %s M / 資本開支 %s M" % (fmt_m(fin.da_ttm), fmt_m(fin.capex_ttm)))
        print("  現金 %s M / 投資 %s M / 有息負債 %s M / 租賃負債 %s M -> 淨負債 %s M"
              % (fmt_m(fin.cash), fmt_m(fin.investments), fmt_m(fin.debt),
                 fmt_m(fin.lease_debt), fmt_m(fin.net_debt)))
        print("  稀釋股數 %.1f M (申報) / yfinance 現時股數 %s"
              % (fin.diluted_shares / 1e6,
                 ("%.1f M" % (mkt.shares_now / 1e6)) if mkt.shares_now else "n/a"))
        print("  現價 %.2f (%s) / 市銷率 %.2f / 歷史 %s" % (mkt.price, mkt.price_date, mkt.ps_now, mkt.ps_hist))
        print("  TTM 收入年增 %s" % (("%.1f%%" % (100 * fin.rev_growth_yoy)) if fin.rev_growth_yoy is not None else "n/a"))
        for n in fin.notes:
            print("  [注意] " + n)
        out[fin.ticker] = dict(
            fin=dict(asof=str(fin.asof), rev_ttm=fin.rev_ttm, ebit_ttm=fin.ebit_ttm,
                     sbc_ttm=fin.sbc_ttm, da_ttm=fin.da_ttm, capex_ttm=fin.capex_ttm,
                     tax_rate_hist=fin.tax_rate_hist, diluted_shares=fin.diluted_shares,
                     cash=fin.cash, investments=fin.investments, debt=fin.debt,
                     lease_debt=fin.lease_debt, net_debt=fin.net_debt,
                     op_margin=fin.op_margin, rev_growth_yoy=fin.rev_growth_yoy,
                     notes=fin.notes),
            mkt=dict(price=mkt.price, date=str(mkt.price_date), ps_now=mkt.ps_now,
                     ps_hist=mkt.ps_hist, shares_now=mkt.shares_now),
        )
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, default=str)
    return out


if __name__ == "__main__":
    main()
