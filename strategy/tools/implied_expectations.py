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
#
# KARST-196:193 那條規則的股權成本**不隨槓桿變**,於是債務權重越高 WACC 越低 ——
# 方向與公司金融的基本結論相反(加槓桿會令股權風險上升,WACC 大致持平,只差稅盾)。
# 實測 TROX / CLVT / LUMN / COLL 四家債務補上之後,WACC 由 10.0% 機械地跌到
# 6.0–7.0%,估值被推高;規則本身沒有下限,一家槓桿高、又剛好過得到負債閘的公司,
# 會同時拿到便宜的折現率與通行證。
#
# 改法(Hamada 重槓桿):把 5.0 個百分點視為**無槓桿(零負債)股權溢價**,按 D/E 與
# 稅率重槓桿 —— 重槓桿後溢價 = 無槓桿溢價 × (1 + (1 − t) × D/E),
# 出自 Hamada (1972) 的 βL = βU × (1 + (1 − t) × D/E)(債務 beta 當 0);
# 股權成本 Ke = 美債 + 重槓桿後溢價,再照舊按市值 / 有息負債權重加權。
# 代入之後有一條封閉式(w = 債務權重、Ke_u = 無槓桿股權成本、s = 信用差價):
#
#     WACC(w) = Ke_u − w × [ t × Ke_u − (1 − t) × s ]
#
# 即 WACC 對槓桿是一條線,w = 0 時等於無槓桿股權成本,w = 1 時等於 (1 − t)(Ke_u + s)。
# 兩個端點取細那個就是**這條規則本身算得出的最低 WACC**,寫成 wacc_floor;它不是
# 外加的任意下限,是同一條公式的極限值,只用來擋住下面 D/E 上限造成的越界。
# 稅率 t = 0 時全條線變成水平(WACC ≡ Ke_u),與直覺一致:沒有稅盾就沒有槓桿好處。
#
# D/E 上限:重槓桿後溢價對 D/E 是線性的,D/E 爆大(TROX 4.21 倍、CLVT 3.58 倍)時
# 溢價會爆到二十幾個百分點,那個股權成本已經沒有意義 —— 這種公司的股權其實是一張
# 期權,不是可以用單一折現率描述的東西。所以 D/E 截頂至 DE_CAP 並印警告。截頂只
# 壓住**報出來的股權成本**;WACC 那一邊由 wacc_floor 兜住,兩者合起來令 WACC 對
# 任何槓桿都落在 [wacc_floor, Ke_u] 之內。

EQUITY_PREMIUM = 0.05      # **無槓桿**股權溢價(D/E = 0 時的溢價),加在十年期美債
                           # 收益率之上;有槓桿的公司按 Hamada 式重槓桿,見
                           # cost_of_capital()。KARST-196 之前它是固定溢價。
RATE_ROUND_STEP = 0.005    # 資本成本四捨五入到最近 0.5 個百分點
CREDIT_SPREAD = 0.02       # 信用差價(債務成本 = 十年期美債 + 這一格)。
                           # 第一版全批共用 2.0 個百分點 —— 這是**示例值,待對齊**,
                           # 不是任何一家公司的實際信用評級推算,見 README 限制第 10 條。
DE_CAP = 3.0               # 重槓桿用的 D/E 上限(市值口徑),超過就截頂並印警告。
                           # 3.0 = 債務佔資本 75%,非金融公司到這一級已是信貸故事;
                           # 這是判斷不是市場觀察,見 README 限制第 19 條。


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


def rule_discount_rate(credit_spread: float = CREDIT_SPREAD,
                       de_cap: float = DE_CAP) -> dict:
    """規則資本成本的**批次共用輸入**:十年期美債收益率 + 5.0 個百分點 =
    **無槓桿**股權成本(D/E = 0 那一家的股權成本)。

    `rate` 一格是無槓桿股權成本四捨五入至 0.5% 後的值 —— KARST-190 直接把它當折現率
    用,KARST-193 之後它只是「淨現金公司的折現率」與舊行為的對照值;實際折現率由
    cost_of_capital() 逐家算(無槓桿股權成本用 `raw_rate` 這個未四捨五入的原值,
    再按該公司的 D/E 重槓桿)。回傳完整記錄(供寫入輸出 JSON `_meta` 與印說明用)。"""
    info = fetch_treasury_10y()
    raw = info["treasury_yield"] + EQUITY_PREMIUM
    rate = _round_half_up(raw, RATE_ROUND_STEP)
    info.update(equity_premium=EQUITY_PREMIUM, raw_rate=raw,
                rounded_to=RATE_ROUND_STEP, rate=rate, manual_override=False,
                credit_spread=credit_spread,
                cost_of_equity_raw=raw,
                cost_of_debt_pretax=info["treasury_yield"] + credit_spread,
                # KARST-196 新增欄(只加不刪):無槓桿溢價與 D/E 上限是本批共用的輸入,
                # 重槓桿後溢價逐家不同,記在 cost_of_capital() 的回傳裡。
                equity_premium_unlevered=EQUITY_PREMIUM,
                cost_of_equity_unlevered=raw,
                de_cap=de_cap, relever="hamada",
                basis="WACC(KARST-193 定口徑,KARST-196 補槓桿調整):無槓桿股權溢價 "
                      "= 5.0 個百分點,按 Hamada 式 × (1 + (1 − 稅率) × D/E) 重槓桿 "
                      "→ 股權成本 = 美債 + 重槓桿後溢價;債務成本 = 美債 + 信用差價,"
                      "再乘 (1 − 稅率);權重用市值與有息負債帳面值;D/E 截頂 %.1f 倍;"
                      "WACC 不低於同一條公式的極限值 wacc_floor;"
                      "四捨五入至 0.5%% 在 WACC 層做" % de_cap)
    return info


def cost_of_capital(fin: "Financials", market_cap: float, tax_rate: float,
                    treasury_yield: float, equity_premium: float = EQUITY_PREMIUM,
                    credit_spread: float = CREDIT_SPREAD,
                    round_step: float = RATE_ROUND_STEP,
                    net_cash_include_investments: bool = False,
                    de_cap: float = DE_CAP,
                    relever: bool = True) -> dict:
    """逐家加權資本成本(KARST-193 定口徑,KARST-196 補槓桿調整)。
    回傳的 dict 就是輸出 JSON `_meta` 那一格。

      D/E        = 有息負債帳面值 ÷ 市值(與下面權重同一口徑,含融資租賃),截頂 de_cap
      重槓桿溢價 = 無槓桿溢價 × (1 + (1 − 稅率) × D/E)      ← Hamada (1972)
      股權成本   Ke = 十年期美債 + 重槓桿後溢價(四捨五入前的原值)
      債務成本   Kd = (十年期美債 + 信用差價) × (1 − 稅率)
      權重       市值 E = 現價 × 稀釋後股數;債務 D = 有息負債帳面值
      WACC       = max(Ke × E/(D+E) + Kd × D/(D+E), wacc_floor),四捨五入至 round_step

    **為什麼要重槓桿。** KARST-193 的 Ke 不隨槓桿變,而 Kd 恆低於 Ke,於是債務權重
    越高 WACC 越低 —— 高槓桿公司反而拿到便宜折現率、估值被推高,方向與公司金融的
    基本結論相反。重槓桿之後代入,WACC 對債務權重 w 是一條線:

        WACC(w) = Ke_u − w × [ 稅率 × Ke_u − (1 − 稅率) × 信用差價 ]

    Ke_u = 無槓桿股權成本。w = 0 時 WACC = Ke_u(淨現金公司,值與 KARST-190/193
    完全相同);w = 1 時 WACC = (1 − 稅率) × (Ke_u + 信用差價)。**兩個端點取細那個
    就是 wacc_floor** —— 它是同一條公式的極限值,不是外加的任意數字下限;只在 D/E
    被 de_cap 截頂、算出來的 WACC 越過這條線時才生效(`wacc_floor_binding`)。

    **D/E 上限。** 重槓桿後溢價對 D/E 線性,D/E 爆大時溢價會爆到二十幾個百分點,
    那個股權成本已經沒有意義(這種公司的股權其實是一張期權)。所以截頂並在
    `warnings` 留一句;截頂只壓住報出來的股權成本,WACC 那一邊由 wacc_floor 兜住。

    淨現金公司(有息負債 ≤ 現金,對齊 D-162 釘死的 N2 口徑「現金 − 總債務」)
    當作沒有槓桿:D/E = 0、溢價 = 無槓桿溢價、WACC = Ke_u,值與 KARST-190/193 相同。

    經營租賃負債**不入權重**(仍然留在淨負債裡,口徑不變)—— 本票只按「有息負債
    帳面值」定權重,租賃債務化的資本成本處理是另一個議題,見 README 限制第 11 條。
    net_cash_include_investments=True 時,判定淨現金那一步把短期及長期投資也當現金
    (SNOW、ENPH 這種「現金少於債務、但現金加證券遠多於債務」的公司會因此翻邊)。

    relever=False 還原 KARST-193 的舊算法(固定溢價、無下限),**只供前後對照與
    回歸測試用**(KARST-196 的六十家差異表就是這樣出「前」那一欄),不是給正常路徑
    用的開關 —— 走這條路等於把本票修好的方向缺陷放回去。
    """
    ke_unlevered = treasury_yield + equity_premium
    kd_pre = treasury_yield + credit_spread
    kd_post = kd_pre * (1.0 - tax_rate)
    cash_base = fin.cash + (fin.investments if net_cash_include_investments else 0.0)
    debt = fin.debt
    net_cash = debt <= cash_base
    warnings: List[str] = []
    # WACC 對槓桿是一條線,極小值必在 w = 0 或 w = 1 其中一端(見上方推導)
    wacc_floor = min(ke_unlevered, (1.0 - tax_rate) * (ke_unlevered + credit_spread))
    de_raw = 0.0
    de_used = 0.0
    de_capped = False
    if net_cash or market_cap <= 0 or (debt + market_cap) <= 0:
        w_debt, w_equity = 0.0, 1.0
        premium_levered = equity_premium
        ke = ke_unlevered
        wacc_pre_floor = ke_unlevered
    else:
        w_debt = debt / (debt + market_cap)
        w_equity = 1.0 - w_debt
        de_raw = debt / market_cap
        de_used = min(de_raw, de_cap) if relever else 0.0
        de_capped = bool(relever and de_raw > de_cap)
        if de_capped:
            warnings.append(
                "D/E %.2f 倍超過上限 %.1f 倍,重槓桿時截頂 —— 槓桿到這一級,單一股權"
                "折現率已經描述不了這家公司(股權接近一張期權),數字要人手核。"
                % (de_raw, de_cap))
        premium_levered = equity_premium * (1.0 + (1.0 - tax_rate) * de_used)
        ke = treasury_yield + premium_levered
        wacc_pre_floor = ke * w_equity + kd_post * w_debt
    wacc_floor_binding = bool(relever and wacc_pre_floor < wacc_floor - 1e-12)
    wacc_raw = max(wacc_pre_floor, wacc_floor) if relever else wacc_pre_floor
    if wacc_floor_binding:
        warnings.append(
            "WACC 原值 %.3f%% 低於本規則的極限值 %.3f%%(D/E 截頂所致),已抬到極限值。"
            % (100 * wacc_pre_floor, 100 * wacc_floor))
    wacc = _round_half_up(wacc_raw, round_step)
    return dict(
        wacc=wacc, wacc_raw=wacc_raw, rounded_to=round_step,
        cost_of_equity=ke, cost_of_debt_pretax=kd_pre, cost_of_debt_after_tax=kd_post,
        tax_rate=tax_rate, treasury_yield=treasury_yield, equity_premium=equity_premium,
        credit_spread=credit_spread,
        market_cap=market_cap, debt_book=debt, cash=fin.cash, investments=fin.investments,
        lease_debt=fin.lease_debt, weight_equity=w_equity, weight_debt=w_debt,
        net_cash=net_cash, net_cash_include_investments=net_cash_include_investments,
        # ---- KARST-196 新增欄(只加不刪)----
        relever=("hamada" if relever else "none"),
        equity_premium_unlevered=equity_premium,
        equity_premium_levered=premium_levered,
        cost_of_equity_unlevered=ke_unlevered,
        de_ratio=de_raw, de_ratio_used=de_used, de_cap=de_cap, de_capped=de_capped,
        wacc_floor=wacc_floor, wacc_pre_floor=wacc_pre_floor,
        wacc_floor_binding=wacc_floor_binding,
        warnings=warnings,
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


# ============================================================================
# 一之二、資產負債表取數修復 (KARST-195)
# ============================================================================
# 六處缺陷的一手證據與本地修法全部來自 KARST-188:
#   research/2026-09-methodology/2026-09-09-①候選池全量/
#     run_60_full.py(interest_debt_fixed / cash_invest_fixed / diluted_shares_fixed)
#     check_finance_lease.py、finance_lease_gap.csv、bs_staleness.csv、facts-*.md
# 本節把那批本地修法搬進共用工具,不是另外發明一套。舊的 *_TAGS 常數一格不刪
# (KARST-188 的腳本直接引用 IE.CASH_TAGS / IE.DILUTED_TAGS),新表另立。

BS_FRESH_DAYS = 45       # 時點科目距結算日超過這個日數 = 上一季的舊結餘,不採用
PRICE_STALE_DAYS = 200   # 結算日距價格日超過這個日數 = 「過期」,印警告

# --- (二) 有息負債:三桶,合計標籤與分項標籤互斥 ---------------------------
# 舊清單只認五個窄式標籤,信貸額度 / 可轉債 / 有抵押債 / 其他短期借款 / 把租賃併在
# 一起報的合計標籤全部不在內,取不到值就當「沒有負債」(A-053)。實測後果:ORCL 的
# 1,295 億債務讀成 72 億;CLVT 的 43 億債務全部漏掉,淨負債由 +41 億變成淨現金 −1.9 億。
#
# 三桶分清楚,否則會重覆計數:
#   COMBINED   一個標籤就代表全部有息負債(含流動部分)的「總額」標籤
#   CUR / NC   分項標籤,兩者相加才是總額
# 桶值 = max(總額標籤, 各分項族最大值之和) —— 只取 max,**永不把總額與分項相加**,
# 這就是缺陷(四)「合計標籤同時入流動與非流動兩桶」的根治法。
# 總額標籤先比新鮮度、後比金額;總額標籤的日期早於分項桶就是上一季的舊總額,棄用
# (反過來先取金額最大,會挑中舊總額再被新鮮度規則整筆丟掉,債務當零——CLVT、TROX
# 一度因此變成淨現金)。
DEBT_COMBINED = ["DebtLongtermAndShorttermCombinedAmount",
                 "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities"]
# **含糊標籤**:`LongTermDebt` 與 `NotesPayable` 兩條,不同申報人用法相反 —— 有人用來
# 報「全部有息負債的總額」,有人用來報「資產負債表上非流動那一行」。當成總額而它其實
# 只是非流動,就會漏掉流動部分(QCOM 2026-06-28:LongTermDebt 127.81 億被當成總額,
# 流動的 24.89 億整筆漏掉,低估 16%);當成非流動而它其實是總額,則會重覆計數。
# 六十家之中 15 家的債務取自這兩條標籤,所以不能靠猜,要逐家用申報歷史判。
DEBT_AMBIGUOUS = ["LongTermDebt", "NotesPayable"]
# 判斷用的對照標籤:找一個「含糊標籤與非流動標籤同日並存」的申報日,看它等於非流動
# 那一行,還是等於非流動 + 流動。QCOM 2025-09-28 兩者都是 148.11 億 → 非流動那一行。
_AMB_NC_PROBE = ["LongTermDebtNoncurrent", "NotesPayableNoncurrent"]
_AMB_NC_FAMILY = ["LongTermNotesPayable", "LongTermLoansPayable",
                  "ConvertibleLongTermNotesPayable", "ConvertibleDebtNoncurrent",
                  "LongTermLineOfCredit", "SecuredLongTermDebt"]
_AMB_CUR_PROBE = ["DebtCurrent", "LongTermDebtCurrent", "NotesPayableCurrent",
                  "LoansPayableCurrent", "ConvertibleNotesPayableCurrent",
                  "LinesOfCreditCurrent", "SecuredDebtCurrent", "ShortTermBorrowings"]
# 債務**附註**口徑:本金總額,不是資產負債表帳面值(帳面值 = 本金 − 未攤銷折價與
# 發行成本)。KARST-188 的本地版把 DebtInstrumentCarryingAmount 放進總額桶,於是
# ORCL 取到 1,301.05 億(本金)而不是資產負債表的 1,295.41 億,CRNC 取到 1.80 億
# 而不是 10-Q 帳面的 1.7346 億 —— 後者與本票驗收條件「對得上一手 10-Q」直接相撞。
# 本工具改為:**只在資產負債表口徑完全取不到值時**才退到這一格,並印警告。
DEBT_NOTE_PRINCIPAL = ["DebtInstrumentCarryingAmount", "DebtInstrumentFaceAmount"]
DEBT_CUR_AGG = ["LongTermDebtCurrent", "DebtCurrent",
                "LongTermDebtAndCapitalLeaseObligationsCurrent"]
# 一個桶之內「依序取第一個有值的標籤」會漏數:同一家公司可以同時有定期貸款與可轉債,
# 分別報在兩條標籤上,取了第一條就當第二條不存在(COLL:LongTermLoansPayable 7.978 億
# + ConvertibleLongTermNotesPayable 2.387 億,舊寫法只讀到 7.978 億)。族之間互不重疊,
# 可以相加;族之內只取第一條。
DEBT_CUR_FAMILIES = [["NotesPayableCurrent", "LoansPayableCurrent"],
                     ["ConvertibleNotesPayableCurrent"],
                     ["LinesOfCreditCurrent"],
                     ["ShortTermBorrowings", "OtherShortTermBorrowings"],
                     ["SecuredDebtCurrent"]]
# LongTermDebtAndCapitalLeaseObligations 按 US-GAAP 定義就是「非流動」那一行
# (含流動到期部分的是 ...IncludingCurrentMaturities 那一條),所以住在非流動桶,
# 不進總額桶。放錯桶會令 LMB / GNRC / SAIA / DRS 漏掉流動到期部分。
DEBT_NC_AGG = ["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations"]
DEBT_NC_FAMILIES = [["LongTermNotesPayable", "LongTermLoansPayable"],
                    ["ConvertibleLongTermNotesPayable", "ConvertibleDebtNoncurrent"],
                    ["LongTermLineOfCredit", "LineOfCredit"],
                    ["SecuredLongTermDebt"]]

# --- (五) 融資租賃:整筆漏計 (A-059) ---------------------------------------
# 舊工具的租賃清單只有經營租賃,債務清單亦不含融資租賃,於是 FinanceLeaseLiability*
# 整筆消失。全批 29/60 家受影響、合共 97.1 億美元;DOCN 的負債閘因此判錯
# (淨負債 6.331 億 → 10.429 億,由「過」變「不過」)。融資租賃是有息負債,計入
# `debt`;經營租賃照舊留在 `lease_debt` 分開列。
FIN_LEASE_CUR = ["FinanceLeaseLiabilityCurrent", "CapitalLeaseObligationsCurrent"]
FIN_LEASE_NC = ["FinanceLeaseLiabilityNoncurrent", "CapitalLeaseObligationsNoncurrent"]
FIN_LEASE_TOT = ["FinanceLeaseLiability", "CapitalLeaseObligations"]

# --- (三)(四) 現金與投資:標籤過窄、不核申報日、合計標籤雙計 ----------------
# 舊清單漏掉 DebtSecuritiesAvailableForSale* 一系(CRUS 漏 3.567 億、AGX 漏 4.806 億),
# 又不核申報日期(COLL 的 1.573 億證券在結算日之前已變現用於收購,工具仍當它在手)。
STI_WIDE = ["ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
            "MarketableSecuritiesCurrent",
            "DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent",
            "AvailableForSaleSecuritiesCurrent", "OtherShortTermInvestments"]
LTI_WIDE = ["AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
            "MarketableSecuritiesNoncurrent", "LongTermInvestments",
            "DebtSecuritiesAvailableForSaleExcludingAccruedInterestNoncurrent",
            "AvailableForSaleSecuritiesNoncurrent"]
# **合計標籤只准住在這一格。** AvailableForSaleSecuritiesDebtSecurities 是合計
# (流動 + 非流動);把它放進非流動桶,而公司的證券全部是流動,同一筆錢就會在兩個桶
# 各計一次 —— RMBS 因此虛報 6.518 億淨現金(A-054 同族)。
INV_AGG = ["DebtSecuritiesAvailableForSaleExcludingAccruedInterest", "MarketableSecurities",
           "AvailableForSaleSecurities", "AvailableForSaleSecuritiesDebtSecurities"]
# 現金標籤同樣太窄:CRNC 的現金掛在
# CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAnd
# DiscontinuedOperations,三個標籤一個都對不上,1.276 億現金被當成零。改為前綴比對,
# 按「愈接近純現金愈優先」排序。
CASH_PREFIXES = ["CashAndCashEquivalentsAtCarryingValue",
                 "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
                 "CashAndCashEquivalentsAtFairValue"]


def _bs_pick(facts: dict, tags: Sequence[str], asof: dt.date,
             fresh_days: int = BS_FRESH_DAYS) -> Tuple[float, Optional[dt.date], Optional[str]]:
    """時點科目:依序試每個標籤,取第一個**結算日在 asof 前後 fresh_days 日內**
    且有值的標籤,回傳 (金額, 結算日, 標籤名)。

    容差用 fresh_days(45 日)而不是 instant_series() 的 200 日:200 日容得下上一季,
    而「公司在最近一期沒有再報這一格」通常代表那一格已經歸零或改了標籤,不是維持不變
    (COLL 的可供出售證券就是這樣被當成仍在手,淨負債少計 1.573 億)。
    """
    for tg in tags:
        node = facts.get("facts", {}).get("us-gaap", {}).get(tg)
        if not node:
            continue
        best: Dict[dt.date, Tuple[str, float]] = {}
        for unit, rows in node.get("units", {}).items():
            if not unit.startswith("USD"):
                continue
            for r in rows:
                if "start" in r or "end" not in r or r.get("val") is None:
                    continue
                k = _d(r["end"])
                filed = r.get("filed", "")
                if k not in best or filed >= best[k][0]:
                    best[k] = (filed, float(r["val"]))
        cands = [(k, v[1]) for k, v in best.items()
                 if abs((k - asof).days) <= fresh_days and v[1]]
        if cands:
            k, v = max(cands)
            return float(v), k, tg
    return 0.0, None, None


def classify_ambiguous_debt_tag(facts: dict, tag: str) -> Tuple[str, str]:
    """判斷 `LongTermDebt` / `NotesPayable` 在這一家公司是「總額」還是「非流動那一行」。

    做法:在申報歷史裡由新到舊找一個「該標籤與非流動標籤同日並存」的結算日,比對
      - 標籤值 ≈ 非流動值              → 它是資產負債表非流動那一行(`noncurrent`)
      - 標籤值 ≈ 非流動值 + 流動值      → 它是全部有息負債的總額(`total`)
    兩者都對不上就繼續向前找;全無證據回 `unknown`(呼叫方當作總額並印警告)。

    回傳 (判斷, 證據字串)。容差 1%,遷就四捨五入與少量其他長期負債。
    """
    amb = instant_series(facts, [tag], asof=dt.date(2100, 1, 1))
    if not amb:
        return "unknown", ""
    nc_agg = instant_series(facts, _AMB_NC_PROBE, asof=dt.date(2100, 1, 1))
    nc_fam = {}
    for g in _AMB_NC_FAMILY:
        for k, v in instant_series(facts, [g], asof=dt.date(2100, 1, 1)).items():
            nc_fam[k] = nc_fam.get(k, 0.0) + v
    cur = instant_series(facts, _AMB_CUR_PROBE, asof=dt.date(2100, 1, 1))
    for d in sorted(amb, reverse=True):
        a = amb[d]
        n = nc_agg.get(d) or nc_fam.get(d) or 0.0
        c = cur.get(d) or 0.0
        if not a or not n:
            continue
        tol = 0.01 * abs(a)
        if abs(a - n) <= tol:
            return "noncurrent", "%s:%s=%.0fM,非流動=%.0fM" % (d, tag, a / 1e6, n / 1e6)
        if c and abs(a - (n + c)) <= tol:
            return "total", "%s:%s=%.0fM,非流動+流動=%.0fM" % (
                d, tag, a / 1e6, (n + c) / 1e6)
    return "unknown", ""


def interest_bearing_debt(facts: dict, asof: dt.date,
                          notes: Optional[List[str]] = None) -> Tuple[float, dict]:
    """有息負債 = max(總額標籤, 流動分項 + 非流動分項) + 融資租賃負債。

    回傳 (金額, 明細)。明細記齊用了哪個標籤、哪一個結算日,供輸出逐家印出來
    ——本票要求「印出每家用了哪個標籤」,因為這一格出錯時輸出表面上完全看不出來。
    """
    def bucket(agg_tags, families):
        a_val, a_d, a_tag = 0.0, None, None
        for tg in agg_tags:
            v, d, t = _bs_pick(facts, [tg], asof)
            if not v:
                continue
            if a_d is None or (d and d > a_d) or (d == a_d and v > a_val):
                a_val, a_d, a_tag = v, d, t
        s_val, s_d, s_tags = 0.0, None, []
        for fam in families:
            v, d, t = _bs_pick(facts, fam, asof)
            if v:
                s_val += v
                s_tags.append("%s@%s %.0fM" % (t, d, v / 1e6))
                if d and (s_d is None or d > s_d):
                    s_d = d
        if s_val > a_val:
            return s_val, s_d, "+".join(s_tags)
        return a_val, a_d, ("%s@%s %.0fM" % (a_tag, a_d, a_val / 1e6) if a_tag else "")

    # 含糊標籤先逐家歸位:是「非流動那一行」就進非流動桶(流動部分照樣另外加),
    # 是「總額」才進總額桶。判不出的當總額(保守沿用舊行為)並印警告。
    amb_cls = {}
    nc_agg_tags, comb_tags = list(DEBT_NC_AGG), list(DEBT_COMBINED)
    for tg in DEBT_AMBIGUOUS:
        verdict, ev = classify_ambiguous_debt_tag(facts, tg)
        amb_cls[tg] = dict(verdict=verdict, evidence=ev)
        if verdict == "noncurrent":
            nc_agg_tags.append(tg)
        else:
            comb_tags.append(tg)

    cur, d_cur, src_cur = bucket(DEBT_CUR_AGG, DEBT_CUR_FAMILIES)
    nc, d_nc, src_nc = bucket(nc_agg_tags, DEBT_NC_FAMILIES)
    parts = cur + nc
    d_parts = max([d for d in (d_cur, d_nc) if d], default=None)

    combined, d_comb, tag_comb = 0.0, None, None
    for tg in comb_tags:
        v, d, t = _bs_pick(facts, [tg], asof)
        if not v or d is None:
            continue
        if d_comb is None or d > d_comb:
            combined, d_comb, tag_comb = v, d, t
        elif d == d_comb and v > combined:
            combined, tag_comb = v, t
    if d_comb and d_parts and d_comb < d_parts:
        combined, d_comb, tag_comb = 0.0, None, None   # 舊總額,不採用

    if combined >= parts and tag_comb:
        debt_bs, src = combined, "%s@%s %.0fM" % (tag_comb, d_comb, combined / 1e6)
        if amb_cls.get(tag_comb, {}).get("verdict") == "unknown" and notes is not None:
            notes.append(
                "警告:有息負債取自 %s = %.0fM,但申報歷史裡沒有一個結算日可以判斷它是"
                "「全部有息負債的總額」還是「資產負債表非流動那一行」。當成總額處理;"
                "若實為非流動,流動到期部分會漏計。" % (tag_comb, combined / 1e6))
    else:
        debt_bs, src = parts, "; ".join(x for x in (src_cur, src_nc) if x)

    # 資產負債表口徑完全取不到 → 退到債務附註的本金總額,並印警告
    principal, d_pri, tag_pri = 0.0, None, None
    if debt_bs <= 0:
        principal, d_pri, tag_pri = _bs_pick(facts, DEBT_NOTE_PRINCIPAL, asof)
        if principal:
            debt_bs, src = principal, "%s@%s %.0fM(債務附註本金)" % (
                tag_pri, d_pri, principal / 1e6)
            if notes is not None:
                notes.append(
                    "警告:有息負債取不到任何資產負債表口徑的標籤,退用債務附註的本金總額 "
                    "%s = %.0fM —— 本金不等於帳面值(未扣未攤銷折價與發行成本),可能高估。"
                    % (tag_pri, principal / 1e6))
    else:
        principal, d_pri, tag_pri = _bs_pick(facts, DEBT_NOTE_PRINCIPAL, asof)

    fl_cur, d_fc, t_fc = _bs_pick(facts, FIN_LEASE_CUR, asof)
    fl_nc, d_fn, t_fn = _bs_pick(facts, FIN_LEASE_NC, asof)
    fl_tot, d_ft, t_ft = _bs_pick(facts, FIN_LEASE_TOT, asof)
    if fl_tot > fl_cur + fl_nc:
        fin_lease, fl_src = fl_tot, "%s@%s %.0fM" % (t_ft, d_ft, fl_tot / 1e6)
    else:
        fin_lease = fl_cur + fl_nc
        fl_src = "+".join(x for x in (
            ("%s@%s %.0fM" % (t_fc, d_fc, fl_cur / 1e6)) if t_fc else "",
            ("%s@%s %.0fM" % (t_fn, d_fn, fl_nc / 1e6)) if t_fn else "") if x)

    # 融資租賃已經併在總額標籤裡的情形:*AndCapitalLeaseObligations* 一族按定義
    # 包含資本(融資)租賃,再加一次就是重覆計數。金額多數很小(CLVT 佔淨負債 0.7%),
    # 但要講出來,不靜靜調整 —— 靜靜扣掉會令「這個數怎樣來」更難查。
    if fin_lease and tag_comb and "CapitalLeaseObligations" in (tag_comb or "") \
            and debt_bs == combined and notes is not None:
        notes.append(
            "注意:有息負債取自合計標籤 %s(按定義已含資本 / 融資租賃),而融資租賃 "
            "%.0fM 另外再加了一次,可能重覆計數 %.1f%%。"
            % (tag_comb, fin_lease / 1e6, 100.0 * fin_lease / max(debt_bs, 1.0)))

    detail = dict(debt_total=debt_bs + fin_lease, debt_balance_sheet=debt_bs,
                  finance_lease=fin_lease, combined=combined, parts=parts,
                  cur=cur, nc=nc, note_principal=principal,
                  tag_combined=tag_comb, date_combined=str(d_comb),
                  date_parts=str(d_parts), src=src, src_finance_lease=fl_src,
                  ambiguous_tags=amb_cls)
    return debt_bs + fin_lease, detail


def cash_and_investments(facts: dict, asof: dt.date,
                         notes: Optional[List[str]] = None) -> Tuple[float, float, dict]:
    """現金與短 / 長期投資。回傳 (現金, 投資, 明細)。

    (三) 現金標籤取不到就退到前綴比對;(四) 合計標籤只准住 INV_AGG,而且與分項
    互斥(取較大者,永不相加);另加一條保險絲:流動桶與非流動桶金額完全相同,
    幾乎肯定是同一筆證券的兩個標籤,不是兩筆錢。
    """
    cash, d_cash, t_cash = _bs_pick(facts, CASH_TAGS, asof)
    if not cash:
        us = facts.get("facts", {}).get("us-gaap", {})
        wide, seen = [], set()
        for p in CASH_PREFIXES:
            for t in sorted(us):
                if t.startswith(p) and t not in seen:
                    seen.add(t)
                    wide.append(t)
        cash, d_cash, t_cash = _bs_pick(facts, wide, asof)
        if cash and notes is not None:
            notes.append("現金標籤退用前綴比對:%s@%s = %.0fM(三個標準標籤都對不上)."
                         % (t_cash, d_cash, cash / 1e6))

    sti, d_sti, t_sti = _bs_pick(facts, STI_WIDE, asof)
    lti, d_lti, t_lti = _bs_pick(facts, LTI_WIDE, asof)
    agg, d_agg, t_agg = _bs_pick(facts, INV_AGG, asof)

    fuse = None
    if sti > 0 and abs(sti - lti) < 1.0:
        fuse = ("流動桶 %s 與非流動桶 %s 金額完全相同(%.0fM),判為同一筆證券的兩個標籤,"
                "非流動那一筆不重覆計。" % (t_sti, t_lti, sti / 1e6))
        lti, t_lti = 0.0, None
        if notes is not None:
            notes.append(fuse)

    if agg > sti + lti:
        inv = agg
        src_inv = "%s@%s %.0fM(合計標籤)" % (t_agg, d_agg, agg / 1e6)
    else:
        inv = sti + lti
        src_inv = "+".join(x for x in (
            ("%s@%s %.0fM" % (t_sti, d_sti, sti / 1e6)) if t_sti else "",
            ("%s@%s %.0fM" % (t_lti, d_lti, lti / 1e6)) if t_lti else "") if x)

    detail = dict(cash=cash, investments=inv, src_cash=(
        "%s@%s %.0fM" % (t_cash, d_cash, cash / 1e6) if t_cash else "(無)"),
        src_investments=src_inv or "(無)", sti=sti, lti=lti, agg=agg, fuse=fuse,
        date_cash=str(d_cash))
    return cash, inv, detail


def latest_diluted_shares(facts: dict) -> Tuple[float, str]:
    """(一) 稀釋股數:**不可以拆季**。

    稀釋後加權平均股數是加權平均**存量**,不是流量;quarterize() 用「全年 − 首九個月」
    去拆它,等於用全年平均減九個月平均,數學上沒有意義,結果接近零(A-049:六十家
    之中 VPG / ORCL / FN / VIAV / MRCY / IREN 六家被壓到真實值的 0.1%–4.4%,
    FN 的基準每股值因此變成現價的 +99,660%)。

    改法:直接取未拆季的 duration 事實中結束日最近的一筆;同一結束日有多筆時優先取
    60–100 日的那筆(季度期)。回傳 (股數, 來源說明)。
    """
    ser = duration_series(facts, DILUTED_TAGS)
    if not ser:
        return 0.0, "無稀釋股數標籤"
    latest_end = max(e for (_s, e) in ser)
    cands = [((s, e), v) for (s, e), v in ser.items() if e == latest_end]
    cands.sort(key=lambda kv: abs((kv[0][1] - kv[0][0]).days - 91))
    (s0, e0), val = cands[0]
    return float(val), "XBRL 未拆季 %s→%s" % (s0, e0)


def reconcile_diluted_shares(fin: "Financials", shares_now: Optional[float]
                             ) -> "Financials":
    """與 yfinance 現時股數對照:相差超過 ±25% 就改用市場股數並記一筆。
    股數可以因回購 / 增發而變,±25% 是容差不是判準 —— 這一步是為了接住
    「XBRL 那一格本身有問題」的情形,不是為了追平兩個來源。"""
    if not shares_now or shares_now <= 0:
        if not fin.diluted_shares:
            fin.notes.append("警告:XBRL 與 yfinance 都取不到稀釋股數。")
        return fin
    v = fin.diluted_shares
    if v and 0.75 <= v / shares_now <= 1.25:
        return fin
    out = replace(fin, diluted_shares=float(shares_now))
    out.notes = list(fin.notes) + [
        "稀釋股數改用 yfinance 現時股數 %.1fM(XBRL %s 相差超過 25%%,來源:%s)。"
        % (shares_now / 1e6, ("%.1fM" % (v / 1e6)) if v else "0",
           fin.shares_src or "n/a")]
    out.extraction = dict(fin.extraction or {})
    out.extraction["shares_src"] = "yfinance 現時股數(XBRL %s 與市場股數相差 >25%%)" % (
        ("%.1fM" % (v / 1e6)) if v else "0")
    out.shares_src = out.extraction["shares_src"]
    return out


# --- (六) 報表新鮮度:companyfacts 會靜靜地落後一季 (A-055) ------------------

SUBMISSIONS_DIR = os.path.join(REPO, "data", "sec", "submissions")


_SUB_NET_CACHE: Dict[str, Optional[dict]] = {}


def _fetch_submissions(cik: str) -> Optional[dict]:
    if cik in _SUB_NET_CACHE:
        return _SUB_NET_CACHE[cik]
    out = None
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://data.sec.gov/submissions/CIK%s.json" % cik,
            headers={"User-Agent": "Karst research karsoncheng@casy.hk"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except Exception:
        out = None
    _SUB_NET_CACHE[cik] = out
    return out


def load_submissions(cik: str, prefer_local: bool = True) -> Tuple[Optional[dict], str]:
    """SEC 申報清單。先讀本地 data/sec/submissions 快取,沒有才打 SEC 端點。
    回傳 (資料, 來源說明)。"""
    path = os.path.join(SUBMISSIONS_DIR, "CIK%s.json" % cik)
    if prefer_local and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh), "data/sec/submissions(本地快取)"
        except Exception:
            pass
    got = _fetch_submissions(cik)
    return got, ("data.sec.gov(即時)" if got else "無 submissions 資料")


def filing_freshness(cik: str, asof: dt.date, price_date: Optional[dt.date] = None
                     ) -> dict:
    """companyfacts 的最新資產負債表期末日,對 EDGAR 申報清單交叉核對。

    A-055:2026-09-09 當日重新下載六十家 companyfacts,仍有 5 家(ENPH、RMBS、
    AMKR、CDNS、CLVT)的最新一張資產負債表停在 2026-03-31,而公司早已申報了
    2026-06-30 那一季 —— 表照樣填得滿,不會報錯。所以要對申報清單核一次:
    最近一份 10-Q / 10-K 所涵蓋的期末日若晚於 companyfacts 的結算日,即「資料落後」。
    """
    out = dict(facts_asof=str(asof), stale=None, expired=False, index_behind=False,
               latest_form=None, latest_filing_date=None, latest_report_date=None,
               lag_days=None, days_asof_to_price=None, source=None, note=None,
               expired_note=None)
    if price_date is not None:
        gap = (price_date - asof).days
        out["days_asof_to_price"] = gap
        out["expired"] = gap > PRICE_STALE_DAYS
        if out["expired"]:
            out["expired_note"] = (
                "過期:結算日 %s 距價格日 %s 已 %d 日,超過 %d 日。"
                % (asof, price_date, gap, PRICE_STALE_DAYS))

    def _latest_periodic(sub):
        rec = (sub or {}).get("filings", {}).get("recent", {})
        forms = rec.get("form", [])
        rpt = rec.get("reportDate", [""] * len(forms))
        rows = [(rec["filingDate"][i], rpt[i], forms[i]) for i in range(len(forms))
                if forms[i] in ("10-Q", "10-K") and rpt[i]]
        rows.sort()
        return rows[-1] if rows else None

    sub, src = load_submissions(cik)
    out["source"] = src
    row = _latest_periodic(sub)
    # 本地快取自己落後(它的最近一期比 companyfacts 還舊)→ 打一次 SEC 端點確認,
    # 否則會漏報「資料落後」:一個過期的對照表只會給出假的安心。
    if row and _d(row[1]) < asof:
        live = _fetch_submissions(cik)
        row2 = _latest_periodic(live)
        if row2 and _d(row2[1]) >= _d(row[1]):
            row, out["source"], out["index_behind"] = row2, "data.sec.gov(本地快取落後,已即時重取)", True
        else:
            out["index_behind"] = True
    if not row:
        out["note"] = "申報清單取不到 10-Q / 10-K,新鮮度無法核對"
        return out
    fdate, rdate, form = row
    out.update(latest_form=form, latest_filing_date=fdate, latest_report_date=rdate)
    stale = _d(rdate) > asof
    out["stale"] = bool(stale)
    out["lag_days"] = (_d(rdate) - asof).days
    notes = []
    if stale:
        notes.append(
            "資料落後:companyfacts 最新資產負債表期末日 %s,但 EDGAR 顯示公司已於 %s "
            "申報涵蓋 %s 的 %s(落後 %d 日)—— 淨負債、現金、股數全部是上一季的數。"
            % (asof, fdate, rdate, form, out["lag_days"]))
    if out["expired_note"]:
        notes.append(out["expired_note"])
    if notes:
        out["note"] = "".join(notes)
    return out


# --- (七) 收市價核對:最後一根日線是不是已收市 (A-056) ----------------------

US_EASTERN = "America/New_York"


def _now_eastern() -> dt.datetime:
    from zoneinfo import ZoneInfo
    return dt.datetime.now(ZoneInfo(US_EASTERN))


def us_market_state(now_et: dt.datetime) -> str:
    """美股正常交易時段狀態:'pre'(未開市)/ 'open'(交易中)/ 'closed'(已收市)。
    週末一律 'closed'。假期不另判 —— 假期當日 yfinance 根本不會有那一根日線,
    退回上一根本身就是退回上一個真交易日。"""
    if now_et.weekday() >= 5:
        return "closed"
    t = now_et.time()
    if t < dt.time(9, 30):
        return "pre"
    if t < dt.time(16, 0):
        return "open"
    return "closed"


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
    # --- KARST-195 新增欄位(只加不改舊欄)---------------------------------
    finance_lease: float = 0.0        # 融資租賃負債。已經**包含在 debt 之內**,
                                      # 這一格只為了拆解得出來,不要再加一次。
    shares_src: str = ""              # 稀釋股數的來源(XBRL 期間 / yfinance)
    extraction: dict = field(default_factory=dict)   # 逐格用了哪個標籤、哪一日

    @property
    def net_debt(self) -> float:
        """淨負債口徑:有息負債 + 經營租賃負債 + 少數股東權益帳面值 − 現金 − 投資。
        少數股東權益放這裡,是因為企業價值屬於全體資本提供者,不只母公司股東。
        KARST-195 之後,`debt` 已含融資租賃(A-059);經營租賃仍然分開放 lease_debt。"""
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

    # (一) 稀釋股數:不拆季(A-049)。dil_q 那條舊路只留作對照,不再用來取值。
    dil_ttm_ends = sorted(dil_q)
    shares_quarterized = dil_q[dil_ttm_ends[-1]] if dil_ttm_ends else 0.0
    diluted_shares, shares_src = latest_diluted_shares(facts)

    def _inst(tags: Sequence[str], label: str) -> float:
        return _latest(instant_series(facts, tags, asof=asof, label=label, notes=notes), asof)

    # (二)(四)(五) 有息負債:三桶互斥 + 融資租賃
    debt, debt_detail = interest_bearing_debt(facts, asof, notes)
    # (三)(四) 現金與投資:前綴變體 + 申報日核對 + 合計標籤互斥
    cash, inv, cash_detail = cash_and_investments(facts, asof, notes)
    lease = _inst(LEASE_CUR_TAGS, "短期經營租賃負債") + _inst(LEASE_NC_TAGS, "長期經營租賃負債")
    nci = _inst(NCI_TAGS, "少數股東權益")

    extraction = dict(
        asof=str(asof),
        debt=debt_detail, cash=cash_detail,
        shares=diluted_shares, shares_src=shares_src,
        shares_quarterized_old=shares_quarterized,
        operating_lease=lease, nci=nci,
    )
    notes.append(
        "取數標籤:有息負債 %.0fM = %s(其中融資租賃 %.0fM = %s);現金 %.0fM = %s;"
        "投資 %.0fM = %s;經營租賃 %.0fM;稀釋股數 %.1fM(%s)。"
        % (debt / 1e6, debt_detail["src"] or "(無)",
           debt_detail["finance_lease"] / 1e6, debt_detail["src_finance_lease"] or "(無)",
           cash / 1e6, cash_detail["src_cash"], inv / 1e6, cash_detail["src_investments"],
           lease / 1e6, diluted_shares / 1e6, shares_src))

    return Financials(
        ticker=ticker.upper(), cik=cik, name=facts.get("entityName", ticker),
        asof=asof, rev_ttm=rev_ttm, ebit_ttm=ebit_ttm, sbc_ttm=sbc_ttm,
        da_ttm=da_ttm, capex_ttm=capex_ttm, tax_rate_hist=tax_rate_hist,
        diluted_shares=diluted_shares, cash=cash, investments=inv,
        debt=debt, lease_debt=lease, nci=nci,
        rev_ttm_hist=ttm_series(rev_q), rev_q=rev_q, notes=notes,
        finance_lease=debt_detail["finance_lease"], shares_src=shares_src,
        extraction=extraction,
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
    # --- KARST-195 新增(只加不改舊欄)------------------------------------
    is_closing_price: bool = True          # 用的是不是已完成的收市價
    price_check: dict = field(default_factory=dict)


def market_data(fin: Financials, years: int = 4,
                now_et: Optional[dt.datetime] = None) -> Market:
    """(七) 收市價核對(A-056)。

    yfinance 在交易時段回的最後一根日線是**未完成的當日線**,不是收市價。KARST-188
    整份六十家名單因此不可重現:同一日相隔一小時抽兩次,五十九家價格不同,中位差
    0.39%,而 STRL 只需 +0.13% 就跨過回報底線、擠走 LINC。

    做法:按**美東時間**判交易時段。最後一根日線的日期若等於美東今日、而當刻仍在
    09:30–16:00 之內(或未開市),就丟掉那一根,退回上一個已完成的交易日 ——
    寧可用兩日前的真收市價,不要用今日的假收市價。now_et 可傳入,供測試注入時點。
    """
    import yfinance as yf
    tk = yf.Ticker(fin.ticker)
    hist = tk.history(period="%dy" % (years + 1), auto_adjust=False)
    if hist.empty:
        raise RuntimeError("yfinance 沒有 %s 的價格" % fin.ticker)

    now_et = now_et or _now_eastern()
    state = us_market_state(now_et)
    last_bar = hist.index[-1].date()
    check = dict(now_eastern=now_et.strftime("%Y-%m-%d %H:%M:%S %Z"),
                 market_state=state, last_bar_date=str(last_bar),
                 dropped_bar_date=None, fell_back=False, volume_note=None)
    if last_bar == now_et.date() and state in ("open", "pre"):
        check["dropped_bar_date"] = str(last_bar)
        check["fell_back"] = True
        hist = hist.iloc[:-1]
        if hist.empty:
            raise RuntimeError("%s 丟掉未收市那一根之後沒有價格" % fin.ticker)
        check["note"] = (
            "美股仍在%s(美東 %s),yfinance 最後一根日線 %s 是未完成的當日線,已丟棄,"
            "退回上一交易日 %s 的收市價。"
            % ("交易時段" if state == "open" else "開市前", check["now_eastern"],
               last_bar, hist.index[-1].date()))
    else:
        check["note"] = ("美東 %s,市場狀態「%s」,最後一根日線 %s 為已完成的收市價。"
                         % (check["now_eastern"], state, last_bar))

    price = float(hist["Close"].iloc[-1])
    pdate = hist.index[-1].date()
    # 成交量完整度:只發警告,不改價。時鐘說已收市而成交量明顯不足全日,多數代表
    # 那一根仍在結算(收市後幾分鐘),值得知道,但不足以推翻時鐘。
    try:
        if "Volume" in hist and len(hist) > 21:
            v_last = float(hist["Volume"].iloc[-1])
            v_med = float(hist["Volume"].iloc[-21:-1].median())
            if v_med > 0 and v_last < 0.5 * v_med:
                check["volume_note"] = (
                    "注意:%s 那一根的成交量只有近 20 日中位的 %.0f%%,可能仍未足全日。"
                    % (pdate, 100.0 * v_last / v_med))
    except Exception:
        pass
    check["price_date"] = str(pdate)
    check["price"] = price
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
                  ps_now=ps_now,
                  is_closing_price=True, price_check=check)


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
            rerating_reasons: Optional[Dict] = None,
            allow_stale: bool = False,
            now_et: Optional[dt.datetime] = None) -> dict:
    """折現率四條路,由上而下先中先用(呼叫方式一句沒改;走了哪一條記在回傳的
    `rate_path`,取值見每條後面的括號):

    1. manual_override=True + discount_rate  → 直接用傳入值,標明「人手覆寫」。
       (`rate_path="manual_override"`)
    2. rate_inputs(KARST-193 新增,`rule_discount_rate()` 的回傳)→ 逐家算 WACC
       (見 cost_of_capital();KARST-196 起股權溢價按 D/E 重槓桿),CASES 內的
       手填 wacc 忽略並在 notes 說明。(`rate_path="rule_wacc"`)
    3. discount_rate(KARST-190 的批次規則值)→ 全批共用這個數,不算 WACC。
       舊腳本傳這一個參數的行為完全不變。(`rate_path="batch_discount_rate"`)
    4. 兩個都不傳 → 舊行為:讀 CASES[ticker]["wacc"](供 KARST-184/186 那種
       直接呼叫 analyse() 的舊重跑腳本重現當日結果)。(`rate_path="cases_legacy"`)

    rerating_reasons:一年回報表四情境的「重估理由」,{情境編號: '理由'};不傳
    就讀 RERATING_REASONS[代號],仍然沒有就留空並印警告。

    allow_stale(KARST-195):companyfacts 落後於 EDGAR 申報清單時,預設**拒絕給
    基準值**(valA 的 per_share 置 None,原值移到 per_share_withheld),只給警告;
    傳 True 就照樣輸出數字,並在 `data_freshness` 內留下記錄。
    now_et:注入「現在的美東時間」,供收市價核對的測試用。"""
    fin = build_financials(ticker)
    mkt = market_data(fin, now_et=now_et)
    # (一) 稀釋股數與市場股數對照 —— 差得太遠就換市場股數,再重算市銷率
    fin2 = reconcile_diluted_shares(fin, mkt.shares_now)
    if fin2 is not fin:
        fin = fin2
        mkt = market_data(fin, now_et=now_et)
    # (六) 報表新鮮度:對 EDGAR 申報清單交叉核對
    freshness = filing_freshness(fin.cik, fin.asof, mkt.price_date)
    if freshness.get("note"):
        fin.notes.append(freshness["note"])
    baseline_withheld = bool(freshness.get("stale")) and not allow_stale
    if baseline_withheld:
        fin.notes.append(
            "【拒絕輸出基準值】資料落後於公司已申報的最新一期,基準每股值不予輸出"
            "(要照樣看數字,加 --allow-stale 並自行承擔口徑落後一季的後果)。")
    if base_mode == "annualized_q":
        fin = annualise_latest_quarter(fin)
    C = CASES[fin.ticker]
    wacc_detail: Optional[dict] = None
    rate_path: str
    if rate_inputs is not None and not (manual_override and discount_rate is not None):
        rate_path = "rule_wacc"
        wacc_detail = cost_of_capital(
            fin, market_cap=mkt.price * fin.diluted_shares, tax_rate=C["tax_rate"],
            treasury_yield=rate_inputs["treasury_yield"],
            equity_premium=rate_inputs.get("equity_premium", EQUITY_PREMIUM),
            credit_spread=rate_inputs.get("credit_spread", CREDIT_SPREAD),
            round_step=rate_inputs.get("rounded_to", RATE_ROUND_STEP),
            net_cash_include_investments=rate_inputs.get(
                "net_cash_include_investments", False),
            de_cap=rate_inputs.get("de_cap", DE_CAP))
        wacc = wacc_detail["wacc"]
        if wacc_detail["net_cash"]:
            fin.notes.append(
                "折現率:淨現金公司(有息負債 %.0fM ≤ 現金 %.0fM),沒有實質槓桿,D/E = 0,"
                "股權溢價維持無槓桿值 %.1f 個百分點,WACC = 股權成本 %.2f%% → %.1f%%;"
                "CASES 內的舊手填值 %.1f%% 已忽略。"
                % (fin.debt / 1e6, fin.cash / 1e6,
                   100 * wacc_detail["equity_premium_unlevered"],
                   100 * wacc_detail["cost_of_equity"],
                   100 * wacc, 100 * C.get("wacc", float("nan"))))
        else:
            fin.notes.append(
                "折現率:D/E %.2f 倍%s → 股權溢價由無槓桿 %.1f 個百分點重槓桿至 %.2f 個"
                "百分點(Hamada:× (1 + (1 − %.0f%% 稅率) × D/E));"
                "WACC = 股權成本 %.2f%% × %.1f%% + 稅後債務成本 %.2f%% × %.1f%% "
                "= %.2f%% → 四捨五入至 %.1f%%(有息負債 %.0fM、市值 %.0fM;"
                "信用差價 %.1f 個百分點是示例值,待對齊)。CASES 內的舊手填值 %.1f%% 已忽略。"
                % (wacc_detail["de_ratio"],
                   ("(已截頂至 %.1f 倍)" % wacc_detail["de_cap"]) if wacc_detail["de_capped"] else "",
                   100 * wacc_detail["equity_premium_unlevered"],
                   100 * wacc_detail["equity_premium_levered"],
                   100 * wacc_detail["tax_rate"],
                   100 * wacc_detail["cost_of_equity"], 100 * wacc_detail["weight_equity"],
                   100 * wacc_detail["cost_of_debt_after_tax"], 100 * wacc_detail["weight_debt"],
                   100 * wacc_detail["wacc_pre_floor"], 100 * wacc,
                   wacc_detail["debt_book"] / 1e6, wacc_detail["market_cap"] / 1e6,
                   100 * wacc_detail["credit_spread"], 100 * C.get("wacc", float("nan"))))
        for w in wacc_detail["warnings"]:
            fin.notes.append("[注意] 折現率:" + w)
    elif discount_rate is not None:
        rate_path = "manual_override" if manual_override else "batch_discount_rate"
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
        rate_path = "cases_legacy"
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

    # (六) 資料落後時拒絕給基準值 —— 欄位一格不刪,原值改放 *_withheld
    if baseline_withheld:
        for v in valA.values():
            v["per_share_withheld"] = v["per_share"]
            v["upside_withheld"] = v["upside"]
            v["per_share"] = None
            v["upside"] = None
            v["withheld"] = True

    return dict(fin=fin, mkt=mkt, base=base, tableA=tableA, tableB=tableB,
                valA=valA, valA_sens=valA_sens, oneyear=oneyear,
                mult_cases=mult_cases, dilution_1y=dilution, cfg=C,
                rate_sensitivity=rate_sens,
                rate_path=rate_path,
                wacc_detail=wacc_detail, valA_joint=valA_joint,
                oneyear_four=oneyear_four, rerating_warnings=rerating_warnings,
                data_freshness=freshness, price_check=mkt.price_check,
                extraction=fin.extraction, baseline_withheld=baseline_withheld)


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
    ap.add_argument("--de-cap", type=float, default=DE_CAP,
                    # 注意:這句 help 先被 % DE_CAP 格式化一次,argparse 印說明時再
                    # 格式化一次,所以字面上的百分號要寫四個 %,兩輪之後才剩一個。
                    help="重槓桿用的 D/E 上限(市值口徑,預設 %.1f 倍 = 債務佔資本 75%%%%)。"
                         "股權溢價按 Hamada 式 × (1 + (1 − 稅率) × D/E) 重槓桿,D/E 超過"
                         "這一格就截頂並印警告;WACC 另有本規則自身的極限值兜底。"
                         % DE_CAP)
    ap.add_argument("--net-cash-include-investments", action="store_true",
                    help="判定「淨現金公司」時把短期及長期投資也當現金(預設只看現金,"
                         "對齊 D-162 的 N2 口徑)。翻邊的公司 WACC 會由加權值變回股權成本。")
    ap.add_argument("--allow-stale", action="store_true",
                    help="companyfacts 落後於 EDGAR 申報清單時,照樣輸出基準每股值"
                         "(預設拒絕輸出,只給警告)。用了就要自行承擔口徑落後一季。")
    args = ap.parse_args(argv)

    if args.full:
        if args.override_discount_rate is not None:
            rate_info = dict(rate=args.override_discount_rate, manual_override=True,
                             treasury_yield=None, treasury_source=None, treasury_date=None)
            print("折現率:人手覆寫 = %.2f%%(--override-discount-rate;不經規則計算,"
                  "本批 %d 家共用此數,輸出標明「手動覆寫」)"
                  % (100 * rate_info["rate"], len(args.tickers)))
        else:
            rate_info = rule_discount_rate(credit_spread=args.credit_spread,
                                           de_cap=args.de_cap)
            rate_info["net_cash_include_investments"] = args.net_cash_include_investments
            print("資本成本規則(KARST-193 口徑,KARST-196 補槓桿調整):十年期美債 "
                  "%.3f%%(來源 %s,取數日 %s) + **無槓桿**股權溢價 %.1f 個百分點 "
                  "= 無槓桿股權成本 %.3f%%;逐家按 D/E(市值口徑,截頂 %.1f 倍)"
                  "以 Hamada 式 × (1 + (1 − 稅率) × D/E) 重槓桿;"
                  "債務成本 = 美債 + 信用差價 %.1f 個百分點(示例值,待對齊)× (1 − 稅率);"
                  "WACC 逐家按市值與有息負債權重計,不低於本規則的極限值,"
                  "四捨五入至最近 0.5%%。淨現金公司 D/E = 0,WACC = 無槓桿股權成本 "
                  "= %.2f%%。本批 %d 家。"
                  % (100 * rate_info["treasury_yield"], rate_info["treasury_source"],
                     rate_info["treasury_date"], 100 * rate_info["equity_premium"],
                     100 * rate_info["raw_rate"], rate_info["de_cap"],
                     100 * rate_info["credit_spread"],
                     100 * rate_info["rate"], len(args.tickers)))
        res = {"_meta": dict(discount_rate=rate_info, cost_of_capital={},
                             data_freshness={}, price_check={}, extraction={},
                             rate_path={},
                             allow_stale=bool(args.allow_stale))}
        for t in args.tickers:
            if rate_info["manual_override"]:
                r = analyse(t, base_mode=args.base, discount_rate=rate_info["rate"],
                            manual_override=True, allow_stale=args.allow_stale)
            else:
                r = analyse(t, base_mode=args.base, rate_inputs=rate_info,
                            allow_stale=args.allow_stale)
            res[t.upper()] = _jsonable(r)
            if r.get("wacc_detail"):
                res["_meta"]["cost_of_capital"][t.upper()] = _jsonable(r["wacc_detail"])
            res["_meta"]["data_freshness"][t.upper()] = _jsonable(r["data_freshness"])
            res["_meta"]["price_check"][t.upper()] = _jsonable(r["price_check"])
            res["_meta"]["extraction"][t.upper()] = _jsonable(r["extraction"])
            res["_meta"]["rate_path"][t.upper()] = r["rate_path"]
            f, m = r["fin"], r["mkt"]
            print("=" * 72)
            print("%s  price=%.2f (%s)  rev_ttm=%.1fM  margin=%.1f%%  netdebt=%.1fM  shares=%.1fM"
                  % (f.ticker, m.price, m.price_date, f.rev_ttm / 1e6, 100 * f.op_margin,
                     f.net_debt / 1e6, f.diluted_shares / 1e6))
            print("  [價格] %s" % r["price_check"].get("note", ""))
            if r["price_check"].get("volume_note"):
                print("  [價格] " + r["price_check"]["volume_note"])
            print("  [新鮮度] %s" % (r["data_freshness"].get("note")
                                or "companyfacts 結算日 %s = EDGAR 最近一份 %s(%s)所涵蓋的期末,無落後"
                                   % (r["data_freshness"].get("facts_asof"),
                                      r["data_freshness"].get("latest_form"),
                                      r["data_freshness"].get("latest_filing_date"))))
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
            if r["baseline_withheld"]:
                print("   【拒絕輸出基準值】%s" % r["data_freshness"].get("note", ""))
                print("   (要照樣看數字,重跑時加 --allow-stale)")
            for k, v in r["valA"].items():
                if v.get("per_share") is None:
                    print("   %-4s 不予輸出(資料落後;內部計算值 %s/sh)"
                          % (k, ("%.2f" % v["per_share_withheld"])
                             if v.get("per_share_withheld") is not None else "n/a"))
                    continue
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
        fin = reconcile_diluted_shares(fin, mkt.shares_now)
        fresh = filing_freshness(fin.cik, fin.asof, mkt.price_date)
        print("=" * 70)
        print("%s (%s) CIK %s  帳目截至 %s" % (fin.ticker, fin.name, fin.cik, fin.asof))
        print("  TTM 收入 %s M / 營業利潤 %s M (利潤率 %.1f%%) / 股權薪酬 %s M"
              % (fmt_m(fin.rev_ttm), fmt_m(fin.ebit_ttm), 100 * fin.op_margin, fmt_m(fin.sbc_ttm)))
        print("  折舊攤銷 %s M / 資本開支 %s M" % (fmt_m(fin.da_ttm), fmt_m(fin.capex_ttm)))
        print("  現金 %s M / 投資 %s M / 有息負債 %s M(其中融資租賃 %s M)/ 經營租賃 %s M -> 淨負債 %s M"
              % (fmt_m(fin.cash), fmt_m(fin.investments), fmt_m(fin.debt),
                 fmt_m(fin.finance_lease), fmt_m(fin.lease_debt), fmt_m(fin.net_debt)))
        print("  稀釋股數 %.1f M (申報) / yfinance 現時股數 %s"
              % (fin.diluted_shares / 1e6,
                 ("%.1f M" % (mkt.shares_now / 1e6)) if mkt.shares_now else "n/a"))
        print("  現價 %.2f (%s) / 市銷率 %.2f / 歷史 %s" % (mkt.price, mkt.price_date, mkt.ps_now, mkt.ps_hist))
        print("  TTM 收入年增 %s" % (("%.1f%%" % (100 * fin.rev_growth_yoy)) if fin.rev_growth_yoy is not None else "n/a"))
        print("  [價格] %s" % mkt.price_check.get("note", ""))
        if mkt.price_check.get("volume_note"):
            print("  [價格] " + mkt.price_check["volume_note"])
        print("  [新鮮度] %s" % (fresh.get("note") or "無落後(EDGAR 最近一份 %s 涵蓋 %s)"
                             % (fresh.get("latest_form"), fresh.get("latest_report_date"))))
        for n in fin.notes:
            print("  [注意] " + n)
        out[fin.ticker] = dict(
            fin=dict(asof=str(fin.asof), rev_ttm=fin.rev_ttm, ebit_ttm=fin.ebit_ttm,
                     sbc_ttm=fin.sbc_ttm, da_ttm=fin.da_ttm, capex_ttm=fin.capex_ttm,
                     tax_rate_hist=fin.tax_rate_hist, diluted_shares=fin.diluted_shares,
                     cash=fin.cash, investments=fin.investments, debt=fin.debt,
                     finance_lease=fin.finance_lease, shares_src=fin.shares_src,
                     lease_debt=fin.lease_debt, net_debt=fin.net_debt,
                     op_margin=fin.op_margin, rev_growth_yoy=fin.rev_growth_yoy,
                     notes=fin.notes, extraction=fin.extraction),
            mkt=dict(price=mkt.price, date=str(mkt.price_date), ps_now=mkt.ps_now,
                     ps_hist=mkt.ps_hist, shares_now=mkt.shares_now,
                     price_check=mkt.price_check),
            data_freshness=fresh,
        )
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, default=str)
    return out


if __name__ == "__main__":
    main()
