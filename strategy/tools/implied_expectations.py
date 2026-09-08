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
# 零、資本成本規則 (KARST-190 定折現率規則,KARST-193 改為 WACC 口徑)
# ----------------------------------------------------------------------------
# KARST-190:折現率 = 十年期美債收益率 + 股權溢價,四捨五入至最近 0.5%,同一批
# 候選公司共用同一個數 —— 取消逐家在 CASES 手填折現率的做法(SNOW 10%、AXTI 12%
# 就是舊做法的產物,現在只當歷史記錄留在 CASES 裡,計算時預設忽略,見 analyse())。
#
# KARST-193:上面那個數是**股權成本**,但 value() 折現的是**企業自由現金流**
# (FCFF,付利息之前的現金流,得出企業價值再減淨負債)。兩者不配對 —— FCFF 要配
# 加權資本成本(WACC)。改法:股權成本沿用 190 的規則值(四捨五入前的原值),
# 債務成本 = 十年期美債 + 信用差價,再乘 (1 − 稅率);權重用市值與有息負債帳面值;
# 四捨五入至 0.5% 改在 WACC 這一層做。淨現金公司(有息負債 ≤ 現金)沒有實質槓桿,
# WACC 直接等於股權成本,值不變。

EQUITY_PREMIUM = 0.05      # 股權溢價,加在十年期美債收益率之上
RATE_ROUND_STEP = 0.005    # 資本成本四捨五入到最近 0.5 個百分點
CREDIT_SPREAD = 0.02       # 信用差價(債務成本 = 十年期美債 + 這一格)。
                           # 第一版全批共用 2.0 個百分點 —— 這是**示例值,待對齊**,
                           # 不是任何一家公司的實際信用評級推算,見 README 限制第 10 條。


def _round_half_up(x: float, step: float) -> float:
    """四捨五入到 step 的倍數 —— 明確用四捨五入(非 Python round() 的銀行家捨入),
    因為折現率的取整規則是「四捨五入」,兩者在 .x5 邊界會給出不同答案。"""
    import decimal
    q = decimal.Decimal(str(x)) / decimal.Decimal(str(step))
    q = q.quantize(decimal.Decimal("1"), rounding=decimal.ROUND_HALF_UP)
    return float(q * decimal.Decimal(str(step)))


def fetch_treasury_10y() -> dict:
    """十年期美債收益率。FRED DGS10 與 yfinance ^TNX 兩個來源都試,取日期較新
    的那個(FRED 常常慢幾日才更新,^TNX 是即市代碼,新鮮度更可靠)。回傳的
    dict 連同兩個來源各自的嘗試結果一併記錄,方便事後查來源與日期。
    兩個來源都失敗就拋錯 —— 折現率是全套裡最強的槓桿,寧願報錯也不要
    靜默套一個假數字。"""
    attempts: List[dict] = []

    try:
        import urllib.request
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
        with urllib.request.urlopen(url, timeout=15) as resp:
            text = resp.read().decode("utf-8")
        rows = [r.split(",") for r in text.strip().splitlines()[1:]]
        rows = [(d, v) for d, v in rows if v not in (".", "")]
        if rows:
            d, v = rows[-1]
            attempts.append(dict(source="FRED DGS10", date=d, yield_pct=float(v)))
        else:
            attempts.append(dict(source="FRED DGS10", error="回傳空表"))
    except Exception as e:
        attempts.append(dict(source="FRED DGS10", error=str(e)))

    try:
        import yfinance as yf
        tk = yf.Ticker("^TNX")
        hist = tk.history(period="7d")
        if not hist.empty:
            d = str(hist.index[-1].date())
            v = float(hist["Close"].iloc[-1])
            attempts.append(dict(source="yfinance ^TNX", date=d, yield_pct=v))
        else:
            attempts.append(dict(source="yfinance ^TNX", error="沒有歷史價"))
    except Exception as e:
        attempts.append(dict(source="yfinance ^TNX", error=str(e)))

    ok = [a for a in attempts if "yield_pct" in a]
    if not ok:
        raise RuntimeError(
            "十年期美債收益率取數失敗:FRED DGS10 與 yfinance ^TNX 都不可用 -- %r" % attempts)
    ok.sort(key=lambda a: a["date"], reverse=True)
    chosen = ok[0]
    return dict(treasury_yield=chosen["yield_pct"] / 100.0, treasury_source=chosen["source"],
                treasury_date=chosen["date"], attempts=attempts)


def rule_discount_rate(credit_spread: float = CREDIT_SPREAD) -> dict:
    """規則資本成本的**批次共用輸入**:十年期美債收益率 + 5.0 個百分點 = 股權成本。

    `rate` 一格是股權成本四捨五入至 0.5% 後的值 —— KARST-190 直接把它當折現率用,
    KARST-193 之後它只是「淨現金公司的折現率」與舊行為的對照值;實際折現率由
    cost_of_capital() 逐家算(股權成本用 `raw_rate` 這個未四捨五入的原值)。
    回傳完整記錄(供寫入輸出 JSON `_meta` 與印說明用)。"""
    info = fetch_treasury_10y()
    raw = info["treasury_yield"] + EQUITY_PREMIUM
    rate = _round_half_up(raw, RATE_ROUND_STEP)
    info.update(equity_premium=EQUITY_PREMIUM, raw_rate=raw,
                rounded_to=RATE_ROUND_STEP, rate=rate, manual_override=False,
                credit_spread=credit_spread,
                cost_of_equity_raw=raw,
                cost_of_debt_pretax=info["treasury_yield"] + credit_spread,
                basis="WACC(KARST-193):股權成本 = 美債 + 股權溢價;債務成本 = "
                      "美債 + 信用差價,再乘 (1 − 稅率);權重用市值與有息負債帳面值;"
                      "四捨五入至 0.5% 在 WACC 層做")
    return info


def cost_of_capital(fin: "Financials", market_cap: float, tax_rate: float,
                    treasury_yield: float, equity_premium: float = EQUITY_PREMIUM,
                    credit_spread: float = CREDIT_SPREAD,
                    round_step: float = RATE_ROUND_STEP,
                    net_cash_include_investments: bool = False) -> dict:
    """逐家加權資本成本(KARST-193)。回傳的 dict 就是輸出 JSON `_meta` 那一格。

      股權成本   Ke = 十年期美債 + 股權溢價(四捨五入前的原值)
      債務成本   Kd = (十年期美債 + 信用差價) × (1 − 稅率)
      權重       市值 E = 現價 × 稀釋後股數;債務 D = 有息負債帳面值
      WACC       = Ke × E/(D+E) + Kd × D/(D+E),四捨五入至最近 round_step

    淨現金公司(有息負債 ≤ 現金,對齊 D-162 釘死的 N2 口徑「現金 − 總債務」)
    當作沒有槓桿:WACC = Ke,值與 KARST-190 的舊折現率完全相同。

    經營租賃負債**不入權重**(仍然留在淨負債裡,口徑不變)—— 本票只按「有息負債
    帳面值」定權重,租賃債務化的資本成本處理是另一個議題,見 README 限制第 11 條。
    net_cash_include_investments=True 時,判定淨現金那一步把短期及長期投資也當現金
    (SNOW、ENPH 這種「現金少於債務、但現金加證券遠多於債務」的公司會因此翻邊)。
    """
    ke = treasury_yield + equity_premium
    kd_pre = treasury_yield + credit_spread
    kd_post = kd_pre * (1.0 - tax_rate)
    cash_base = fin.cash + (fin.investments if net_cash_include_investments else 0.0)
    debt = fin.debt
    net_cash = debt <= cash_base
    if net_cash or market_cap <= 0 or (debt + market_cap) <= 0:
        w_debt, w_equity = 0.0, 1.0
        wacc_raw = ke
    else:
        w_debt = debt / (debt + market_cap)
        w_equity = 1.0 - w_debt
        wacc_raw = ke * w_equity + kd_post * w_debt
    wacc = _round_half_up(wacc_raw, round_step)
    return dict(
        wacc=wacc, wacc_raw=wacc_raw, rounded_to=round_step,
        cost_of_equity=ke, cost_of_debt_pretax=kd_pre, cost_of_debt_after_tax=kd_post,
        tax_rate=tax_rate, treasury_yield=treasury_yield, equity_premium=equity_premium,
        credit_spread=credit_spread,
        market_cap=market_cap, debt_book=debt, cash=fin.cash, investments=fin.investments,
        lease_debt=fin.lease_debt, weight_equity=w_equity, weight_debt=w_debt,
        net_cash=net_cash, net_cash_include_investments=net_cash_include_investments,
    )


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
    wacc: float = 0.10        # 折現率。經 --full 批次跑時由規則自動算出(見
                               # rule_discount_rate()),不再逐家手填 —— 見 analyse()
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


# --- 四情境固定次序 (KARST-193) ---------------------------------------------
# 一年回報表的正表。固定四行、固定次序,第一行永遠是「倍數不變」——
# 先看「市場什麼都不改變主意,單靠經營賺不賺得到錢」,再看倍數變化的情境。
# 規則:倍數一改動,就必須寫得出接到盈利能力 / 增長 / 風險 / 資本配置的哪一項
# 具體變化(「重估理由」欄),空白只印警告、不阻止跑。

FOUR_SCENARIOS = (
    (1, "經營按基準路徑、倍數不變", "基準", "現時", False),
    (2, "經營改善、倍數收縮至近一年 25 分位", "樂觀", "p25", True),
    (3, "具體反證出現、倍數回到近一年中位", "基準", "p50", True),
    (4, "論點失效、倍數近一年 25 分位", "悲觀", "p25", True),
)


def _label_growth_cases(growth_cases: Dict[str, float]) -> Dict[str, Tuple[str, float]]:
    """把 CASES 裡的 g1_cases 按收入增速排序,配到悲觀 / 基準 / 樂觀三格。
    最低的一格 = 悲觀,最高的一格 = 樂觀,中間 = 基準(只有兩格時基準取較低那格)。"""
    items = sorted(growth_cases.items(), key=lambda kv: kv[1])
    if not items:
        return {}
    lo, hi = items[0], items[-1]
    mid = items[len(items) // 2] if len(items) >= 3 else items[0]
    return {"悲觀": lo, "基準": mid, "樂觀": hi}


def one_year_four_scenarios(fin: Financials, mkt: Market, growth_cases: Dict[str, float],
                            dilution: float,
                            rerating_reasons: Optional[Dict] = None) -> Tuple[List[dict], List[str]]:
    """一年回報表正表:四情境、固定次序。回傳 (rows, warnings)。

    退出倍數用**近一年**市銷率分位(近一年才是同一盤生意的定價區間;四年那套留在
    附錄的原有情境表)。近一年樣本不足就退回四年分位並在 warnings 說明。
    rerating_reasons:{情境編號或情境名: '重估理由'},由使用者填;空白印警告。
    """
    warnings: List[str] = []
    h1 = mkt.ps_hist_1y if mkt.ps_hist_1y.get("n") else {}
    src = "近一年"
    if not h1:
        h1 = mkt.ps_hist
        src = "四年(近一年樣本不足)"
        warnings.append("近一年市銷率樣本不足,四情境的退出倍數改用四年分位數。")
    gmap = _label_growth_cases(growth_cases)
    mults = {"現時": mkt.ps_now, "p25": h1.get("p25"), "p50": h1.get("p50")}
    mlabel = {"現時": "現時 %.1fx" % mkt.ps_now,
              "p25": "%s 25 分位 %.1fx" % (src, h1["p25"]) if h1.get("p25") is not None else "n/a",
              "p50": "%s 中位 %.1fx" % (src, h1["p50"]) if h1.get("p50") is not None else "n/a"}
    reasons = dict(rerating_reasons or {})
    shares1 = fin.diluted_shares * (1.0 + dilution)
    rows: List[dict] = []
    for seq, name, gkey, mkey, needs in FOUR_SCENARIOS:
        if gkey not in gmap or mults.get(mkey) is None:
            rows.append(dict(seq=seq, scenario=name, growth_case=None, growth=None,
                             mult_case=mlabel.get(mkey), mult=None, rev1=None,
                             price1=None, ret=None, rerating_reason=None,
                             needs_rerating_reason=needs, note="缺退出倍數或增速格,無法計算"))
            continue
        gname, g = gmap[gkey]
        mult = mults[mkey]
        rev1 = fin.rev_ttm * (1.0 + g)
        px1 = mult * rev1 / shares1
        reason = reasons.get(seq, reasons.get(name))
        reason = reason.strip() if isinstance(reason, str) else None
        if not needs:
            reason = reason or "不適用(倍數不變,沒有重估)"
        elif not reason:
            warnings.append(
                "情境 %d「%s」的**重估理由**欄空白 —— 倍數由 %.1fx 變成 %.1fx 是一個判斷,"
                "必須寫得出接到盈利能力 / 增長 / 風險 / 資本配置的哪一項具體變化,"
                "否則這一行只是把倍數當自變數亂撥。"
                % (seq, name, mkt.ps_now, mult))
        rows.append(dict(seq=seq, scenario=name, growth_case=gname, growth=g,
                         mult_case=mlabel[mkey], mult=mult, rev1=rev1, price1=px1,
                         ret=px1 / mkt.price - 1.0, rerating_reason=reason,
                         needs_rerating_reason=needs, note=None))
    # 四情境的名字假設了現價的倍數站在自己近一年區間的上半 —— 現價已經低於 25 分位時,
    # 「倍數收縮至 25 分位」其實是倍數**上調**,情境 2 與 4 會變成正回報,名不副實。
    if mults.get("p25") is not None and mkt.ps_now < mults["p25"]:
        warnings.append(
            "現價市銷率 %.1fx 已經低於%s 25 分位 %.1fx —— 情境 2 與 4 的「倍數收縮至 25 分位」"
            "實際上是倍數**上調**,那兩行的正回報來自倍數修復,不是經營變差之下仍然賺錢。"
            "讀表時要把名字反過來看,或者改用更低的退出倍數。"
            % (mkt.ps_now, src, mults["p25"]))
    return rows, warnings


# ----------------------------------------------------------------------------
# 六、CLI
# ----------------------------------------------------------------------------

def fmt_m(x: float) -> str:
    return "%.0f" % (x / 1e6)


CASES: Dict[str, dict] = {
    # 每家一組「固定假設」。這些是判斷,不是資料;改動要在報告的假設清單裡寫明理由。
    #
    # KARST-190:wacc 這一格現在只是歷史記錄 —— --full 批次跑時折現率一律由
    # rule_discount_rate() 自動算出、全批共用,檔內這個手填數會被忽略並印警告
    # (除非命令列明確傳 --override-discount-rate)。SNOW 的 10%、AXTI 的 12% 正是
    # 舊「逐家手填」做法的產物,留著只為了對照;直接呼叫 analyse() 不傳
    # discount_rate 的舊腳本(如 KARST-184/186 的重跑腳本)仍會讀到這個值,行為不變。
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
    # LULU 的固定假設沿用 KARST-184 候選卡(research/2026-09-methodology/
    # 2026-09-08-①候選池走通/run_three_numbers.py)已核過的一組,原本用 monkeypatch
    # 注入、不在共用工具內 —— 現搬進 CASES 供本票三家重跑直接使用。該票另外對現金
    # 做了人手更正(BS_FIX,A-048),但 KARST-186 已把同一個修復做進
    # instant_series() 的候選標籤後備清單,build_financials("LULU") 現在會自動
    # 取到新標籤的現金(實測 asof 2026-08-02 現金 13.90 億),不用再另外套 BS_FIX。
    "LULU": dict(
        wacc=0.10, terminal_growth=0.025, terminal_roic=0.18, tax_rate=0.23,
        sales_to_capital=3.0, margin_ramp_years=3, horizon=10,
        recovery_growth=0.03,
        target_margin=0.17,
        stage1_growth_ref=0.03,
        stage1_years_ref=5,
        dilution_1y=0.005,
        g1_cases={"北美續跌(-5%)": -0.05, "走平(0%)": 0.0, "低單位數增長(+4%)": 0.04},
    ),
    # KARST-193:TDC / ON / ENPH / ARM 四家的固定假設原本只存在於 KARST-184 的
    # research/2026-09-methodology/2026-09-08-①候選池走通/run_three_numbers.py
    # (monkeypatch 注入),照搬進來供本票七家一次過重跑,一格未改;理由見該票總覽檔的
    # 假設清單。舊 wacc 欄同樣只是歷史記錄,計算時忽略(見 analyse())。
    "TDC": dict(
        wacc=0.10, terminal_growth=0.025, terminal_roic=0.15, tax_rate=0.23,
        sales_to_capital=3.0, margin_ramp_years=5, horizon=10,
        recovery_growth=0.02, target_margin=0.18,
        stage1_growth_ref=-0.03, stage1_years_ref=5, dilution_1y=0.020,
        g1_cases={"加速流失(收入 -10%)": -0.10, "緩慢流失(-3%)": -0.03, "企穩(+2%)": 0.02},
    ),
    "ON": dict(
        wacc=0.10, terminal_growth=0.025, terminal_roic=0.12, tax_rate=0.23,
        sales_to_capital=1.2, margin_ramp_years=4, horizon=10,
        recovery_growth=0.04, target_margin=0.25,
        stage1_growth_ref=0.05, stage1_years_ref=5, dilution_1y=0.010,
        g1_cases={"再跌一年(-8%)": -0.08, "見底走平(0%)": 0.0, "週期回升(+12%)": 0.12},
    ),
    "ENPH": dict(
        wacc=0.10, terminal_growth=0.025, terminal_roic=0.15, tax_rate=0.23,
        sales_to_capital=4.0, margin_ramp_years=4, horizon=10,
        recovery_growth=0.05, target_margin=0.20,
        stage1_growth_ref=0.05, stage1_years_ref=5, dilution_1y=0.020,
        g1_cases={"補貼退場(-20%)": -0.20, "走平(0%)": 0.0, "回升(+15%)": 0.15},
    ),
    "ARM": dict(
        wacc=0.10, terminal_growth=0.025, terminal_roic=0.25, tax_rate=0.23,
        sales_to_capital=4.0, margin_ramp_years=6, horizon=10,
        recovery_growth=0.08, target_margin=0.40,
        stage1_growth_ref=0.25, stage1_years_ref=5, dilution_1y=0.020,
        g1_cases={"授權見頂(+5%)": 0.05, "減速(+15%)": 0.15, "維持現速(+25%)": 0.25},
    ),
}

# 一年回報表四情境的「重估理由」:{代號: {情境編號: '理由'}} —— **由使用者填**,
# 空白時輸出印警告但不阻止跑(KARST-193)。倍數一改動就要寫得出它接到盈利能力 /
# 增長 / 風險 / 資本配置的哪一項具體變化;寫不出,那一行就只是把倍數當自變數亂撥。
RERATING_REASONS: Dict[str, Dict[int, str]] = {}

# 聯合情境的三項同時偏移(KARST-193):增長 ∓10 個百分點、目標利潤率 ∓5 個百分點、
# 折現率 ±1 個百分點。與逐項 ±10% 的敏感度表不同 —— 那個答「一項錯一成」,
# 這個答「三項一齊錯向同一邊」,後者才是真正的下行情形。
JOINT_GROWTH_SHIFT = 0.10
JOINT_MARGIN_SHIFT = 0.05
JOINT_RATE_SHIFT = 0.01

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


def analyse(ticker: str, base_mode: str = "ttm",
            discount_rate: Optional[float] = None, manual_override: bool = False,
            rate_inputs: Optional[dict] = None,
            rerating_reasons: Optional[Dict] = None) -> dict:
    """折現率四條路,由上而下先中先用(前三條是舊有行為,一句沒改):

    1. manual_override=True + discount_rate  → 直接用傳入值,標明「人手覆寫」。
    2. rate_inputs(KARST-193 新增,`rule_discount_rate()` 的回傳)→ 逐家算 WACC
       (見 cost_of_capital()),CASES 內的手填 wacc 忽略並在 notes 說明。
    3. discount_rate(KARST-190 的批次規則值)→ 全批共用這個數,不算 WACC。
       舊腳本傳這一個參數的行為完全不變。
    4. 兩個都不傳 → 舊行為:讀 CASES[ticker]["wacc"](供 KARST-184/186 那種
       直接呼叫 analyse() 的舊重跑腳本重現當日結果)。

    rerating_reasons:一年回報表四情境的「重估理由」,{情境編號: '理由'};不傳
    就讀 RERATING_REASONS[代號],仍然沒有就留空並印警告。"""
    fin = build_financials(ticker)
    mkt = market_data(fin)
    if base_mode == "annualized_q":
        fin = annualise_latest_quarter(fin)
    C = CASES[fin.ticker]
    wacc_detail: Optional[dict] = None
    if rate_inputs is not None and not (manual_override and discount_rate is not None):
        wacc_detail = cost_of_capital(
            fin, market_cap=mkt.price * fin.diluted_shares, tax_rate=C["tax_rate"],
            treasury_yield=rate_inputs["treasury_yield"],
            equity_premium=rate_inputs.get("equity_premium", EQUITY_PREMIUM),
            credit_spread=rate_inputs.get("credit_spread", CREDIT_SPREAD),
            round_step=rate_inputs.get("rounded_to", RATE_ROUND_STEP),
            net_cash_include_investments=rate_inputs.get(
                "net_cash_include_investments", False))
        wacc = wacc_detail["wacc"]
        if wacc_detail["net_cash"]:
            fin.notes.append(
                "折現率:淨現金公司(有息負債 %.0fM ≤ 現金 %.0fM),沒有實質槓桿,"
                "WACC = 股權成本 %.2f%% → %.1f%%;CASES 內的舊手填值 %.1f%% 已忽略。"
                % (fin.debt / 1e6, fin.cash / 1e6, 100 * wacc_detail["cost_of_equity"],
                   100 * wacc, 100 * C.get("wacc", float("nan"))))
        else:
            fin.notes.append(
                "折現率:WACC = 股權成本 %.2f%% × %.1f%% + 稅後債務成本 %.2f%% × %.1f%% "
                "= %.2f%% → 四捨五入至 %.1f%%(有息負債 %.0fM、市值 %.0fM;"
                "信用差價 %.1f 個百分點是示例值,待對齊)。CASES 內的舊手填值 %.1f%% 已忽略。"
                % (100 * wacc_detail["cost_of_equity"], 100 * wacc_detail["weight_equity"],
                   100 * wacc_detail["cost_of_debt_after_tax"], 100 * wacc_detail["weight_debt"],
                   100 * wacc_detail["wacc_raw"], 100 * wacc,
                   wacc_detail["debt_book"] / 1e6, wacc_detail["market_cap"] / 1e6,
                   100 * wacc_detail["credit_spread"], 100 * C.get("wacc", float("nan"))))
    elif discount_rate is not None:
        wacc = discount_rate
        if "wacc" in C:
            if manual_override:
                fin.notes.append(
                    "折現率:人手覆寫 %.1f%%(--override-discount-rate);"
                    "CASES 內的舊手填值 %.1f%% 不採用。"
                    % (100 * wacc, 100 * C["wacc"]))
            else:
                fin.notes.append(
                    "折現率:CASES 內的舊手填值 %.1f%% 已忽略,改用批次規則值 %.1f%%"
                    "(十年期美債收益率 + 5%% 股權溢價,四捨五入至 0.5%%;"
                    "如要採用手填值,重跑時加 --override-discount-rate 明確覆寫)。"
                    % (100 * C["wacc"], 100 * wacc))
    else:
        wacc = C["wacc"]   # 舊行為:向後相容,供不傳 discount_rate 的舊腳本使用
    base = Assumptions(
        bad_growth=C["stage1_growth_ref"], bad_years=C["stage1_years_ref"],
        recovery_growth=C["recovery_growth"], target_margin=C["target_margin"],
        margin_ramp_years=C["margin_ramp_years"], horizon=C["horizon"],
        tax_rate=C["tax_rate"], sales_to_capital=C["sales_to_capital"],
        wacc=wacc, terminal_growth=C["terminal_growth"],
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
                      target_margin=C["target_margin"] - 0.08, wacc=base.wacc + 0.02,
                      recovery_growth=C["recovery_growth"] - 0.02, terminal_growth=0.015),
        "基準": base,
        "樂觀": replace(base, bad_growth=C["stage1_growth_ref"] + 0.15,
                      target_margin=C["target_margin"] + 0.08, wacc=base.wacc - 0.01,
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

    # ---- 聯合情境(KARST-193):三項一齊偏向同一邊,不是逐項各自 ±10% ----
    joint_defs = {
        "悲觀(增長 -10pp、目標利潤率 -5pp、折現率 +1pp)": replace(
            base, bad_growth=base.bad_growth - JOINT_GROWTH_SHIFT,
            target_margin=base.target_margin - JOINT_MARGIN_SHIFT,
            wacc=base.wacc + JOINT_RATE_SHIFT),
        "中性(全部基準)": base,
        "樂觀(增長 +10pp、目標利潤率 +5pp、折現率 -1pp)": replace(
            base, bad_growth=base.bad_growth + JOINT_GROWTH_SHIFT,
            target_margin=base.target_margin + JOINT_MARGIN_SHIFT,
            wacc=base.wacc - JOINT_RATE_SHIFT),
    }
    valA_joint = {}
    for name, a in joint_defs.items():
        try:
            v = value(fin, a)
            valA_joint[name] = dict(per_share=v.per_share, ev=v.ev,
                                    terminal_share=v.terminal_share,
                                    upside=v.per_share / px - 1.0,
                                    assum=dict(bad_growth=a.bad_growth, bad_years=a.bad_years,
                                               recovery_growth=a.recovery_growth,
                                               target_margin=a.target_margin, wacc=a.wacc,
                                               terminal_growth=a.terminal_growth))
        except Exception as e:
            valA_joint[name] = dict(per_share=None, error=str(e))

    # ---- 折現率敏感度:±1 個百分點(絕對值),KARST-190 規定的自動輸出 ----
    # 跟上面 valA_sens 的 wacc 那一行不同 —— 那個是「相對 ±10%」(舊有全項統一規則),
    # 這裡是折現率規則本身要求的「絕對 ±1 個百分點」,基準情境(scen["基準"] = base)
    # 之外另外印,不覆蓋 valA_sens。
    base_ps = valA["基準"]["per_share"]
    rate_sens = []
    for dpp, label in ((-0.01, "-1pp"), (0.01, "+1pp")):
        a2 = replace(base, wacc=base.wacc + dpp)
        try:
            ps2 = value(fin, a2).per_share
        except Exception:
            ps2 = None
        rate_sens.append(dict(
            wacc=a2.wacc, bump=label, per_share=ps2, base=base_ps,
            delta=(None if ps2 is None or base_ps is None else ps2 - base_ps),
            pct=(None if not ps2 or not base_ps else ps2 / base_ps - 1.0),
        ))

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

    # 四情境正表(KARST-193):固定次序,「倍數不變」永遠第一;上面那個 3×4 網格
    # (oneyear)保留為附錄,一行沒刪。
    reasons = rerating_reasons if rerating_reasons is not None else \
        RERATING_REASONS.get(fin.ticker) or C.get("rerating_reasons")
    oneyear_four, rerating_warnings = one_year_four_scenarios(
        fin, mkt, C["g1_cases"], dilution, reasons)

    return dict(fin=fin, mkt=mkt, base=base, tableA=tableA, tableB=tableB,
                valA=valA, valA_sens=valA_sens, oneyear=oneyear,
                mult_cases=mult_cases, dilution_1y=dilution, cfg=C,
                rate_sensitivity=rate_sens,
                wacc_detail=wacc_detail, valA_joint=valA_joint,
                oneyear_four=oneyear_four, rerating_warnings=rerating_warnings)


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
    ap.add_argument("--override-discount-rate", type=float, default=None,
                    help="人手指定折現率(小數,如 0.12 = 12%%),整批共用,取代規則值;"
                         "輸出會標明「手動覆寫」。不傳就用規則值(十年期美債收益率 "
                         "+ 5%% 股權溢價,四捨五入至 0.5%%),CASES 內任何舊手填值一律忽略。")
    ap.add_argument("--credit-spread", type=float, default=CREDIT_SPREAD,
                    help="信用差價(小數,預設 %.3f = %.1f 個百分點)。債務成本 = 十年期美債 "
                         "+ 這一格,再乘 (1 − 稅率)。預設值是示例,待對齊。"
                         % (CREDIT_SPREAD, 100 * CREDIT_SPREAD))
    ap.add_argument("--net-cash-include-investments", action="store_true",
                    help="判定「淨現金公司」時把短期及長期投資也當現金(預設只看現金,"
                         "對齊 D-162 的 N2 口徑)。翻邊的公司 WACC 會由加權值變回股權成本。")
    args = ap.parse_args(argv)

    if args.full:
        if args.override_discount_rate is not None:
            rate_info = dict(rate=args.override_discount_rate, manual_override=True,
                             treasury_yield=None, treasury_source=None, treasury_date=None)
            print("折現率:人手覆寫 = %.2f%%(--override-discount-rate;不經規則計算,"
                  "本批 %d 家共用此數,輸出標明「手動覆寫」)"
                  % (100 * rate_info["rate"], len(args.tickers)))
        else:
            rate_info = rule_discount_rate(credit_spread=args.credit_spread)
            rate_info["net_cash_include_investments"] = args.net_cash_include_investments
            print("資本成本規則(KARST-193):十年期美債 %.3f%%(來源 %s,取數日 %s)"
                  " + 股權溢價 %.1f 個百分點 = 股權成本 %.3f%%;"
                  "債務成本 = 美債 + 信用差價 %.1f 個百分點(示例值,待對齊)× (1 − 稅率);"
                  "WACC 逐家按市值與有息負債權重計,四捨五入至最近 0.5%%。"
                  "淨現金公司 WACC = 股權成本 = %.2f%%。本批 %d 家。"
                  % (100 * rate_info["treasury_yield"], rate_info["treasury_source"],
                     rate_info["treasury_date"], 100 * rate_info["equity_premium"],
                     100 * rate_info["raw_rate"], 100 * rate_info["credit_spread"],
                     100 * rate_info["rate"], len(args.tickers)))
        res = {"_meta": dict(discount_rate=rate_info, cost_of_capital={})}
        for t in args.tickers:
            if rate_info["manual_override"]:
                r = analyse(t, base_mode=args.base, discount_rate=rate_info["rate"],
                            manual_override=True)
            else:
                r = analyse(t, base_mode=args.base, rate_inputs=rate_info)
            res[t.upper()] = _jsonable(r)
            if r.get("wacc_detail"):
                res["_meta"]["cost_of_capital"][t.upper()] = _jsonable(r["wacc_detail"])
            f, m = r["fin"], r["mkt"]
            print("=" * 72)
            print("%s  price=%.2f (%s)  rev_ttm=%.1fM  margin=%.1f%%  netdebt=%.1fM  shares=%.1fM"
                  % (f.ticker, m.price, m.price_date, f.rev_ttm / 1e6, 100 * f.op_margin,
                     f.net_debt / 1e6, f.diluted_shares / 1e6))
            for n in f.notes:
                print("  [注意] " + n)
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
            print("-- 折現率敏感度(絕對 ±1 個百分點,KARST-190) --")
            for s in r["rate_sensitivity"]:
                if s["per_share"] is None:
                    print("        wacc=%.1f%% (%s) -> 無解" % (100 * s["wacc"], s["bump"]))
                else:
                    print("        wacc=%.1f%% (%s) -> %8.2f/sh  %+.1f%%"
                          % (100 * s["wacc"], s["bump"], s["per_share"], 100 * (s["pct"] or 0.0)))
            print("-- (A2) 聯合情境(三項一齊偏,KARST-193) --")
            for k, v in r["valA_joint"].items():
                if v.get("per_share") is None:
                    print("   %-40s 無解(%s)" % (k, v.get("error", "")))
                else:
                    print("   %-40s %8.2f/sh  upside %+6.1f%%  TVshare %.0f%%  wacc %.1f%%"
                          % (k, v["per_share"], 100 * v["upside"], 100 * v["terminal_share"],
                             100 * v["assum"]["wacc"]))
            print("-- (B) 一年回報表 · 四情境正表(KARST-193;第 1 行永遠是倍數不變) --")
            for row in r["oneyear_four"]:
                if row["price1"] is None:
                    print("   %d %-34s %s" % (row["seq"], row["scenario"], row["note"]))
                    continue
                print("   %d %-34s %-22s 倍數 %-22s px1=%8.2f  ret=%+7.1f%%"
                      % (row["seq"], row["scenario"], row["growth_case"], row["mult_case"],
                         row["price1"], 100 * row["ret"]))
                print("       重估理由:%s" % (row["rerating_reason"] or "(空白 —— 未填)"))
            for w in r["rerating_warnings"]:
                print("   [注意] " + w)
            print("-- (B 附錄) 原有情境網格(收入格 × 歷史市銷率格) --")
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
