# -*- coding: utf-8 -*-
"""KARST-191:負債閘資料不足後備計算。

面板 v3 的 `total_debt` 欄空白時(那一期沒有出過我們標籤表上的任何一條債務標籤),
不可以當「不過閘」(A 版原做法)也不可以當「零負債」(A2 版原做法)——這兩個都是
機械假設,不是查出來的事實。

本模組改用 companyfacts 快照(data/sec/companyfacts/CIK##########.json.gz),
套用 strategy/tools/implied_expectations.py(甲,KARST-183/184 候選池走通用的那一套)
的「有序後備標籤清單 + asof 容差」演算法(`instant_series` / `_latest`)重算
短期有息負債 + 長期有息負債。**只讀取匯入該檔案,不修改它**——KARST-190 另一隊
正在改 implied_expectations.py 本身。

知情時點:companyfacts 每一筆事實帶 `filed`(申報日)。套用甲那套演算法之前,
先把 `filed` 晚於觸發日的列全部砍走(`clip_facts_by_filed`),所以甲的演算法
自始至終只看得到觸發日當時已經公布的事實,回算出來的數字必然符合
「申報日 <= 觸發日」——`fallback_total_debt` 內再顯式斷言一次,違反即拋錯。

三態輸出(不是二選一):
  "panel"                —— 面板本身有值,不必後備(呼叫端自行判斷,本模組不處理這格)
  "companyfacts_fallback" —— 面板空白,但 companyfacts 用甲那套邏輯撈到至少一個標籤,
                             回算出一個數字(可能是 0,例如公司確實沒有短期負債但有
                             長期負債,兩者分開判斷)
  "資料不足"              —— companyfacts 對這家公司,知情時點內,DEBT_CUR_TAGS 與
                             DEBT_NC_TAGS 五條標籤一條都沒出現過(或者連 companyfacts
                             快照檔都沒有)。這一格必須單獨報告,不可以併入過閘或不過閘。
"""
from __future__ import annotations

import datetime as dt
import functools
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(r"C:\projects\Karst")
sys.path.insert(0, str(ROOT / "strategy" / "tools"))
import implied_expectations as IE  # noqa: E402  # 只讀取匯入,不修改該檔

DEBT_TAGS_ALL = list(IE.DEBT_CUR_TAGS) + list(IE.DEBT_NC_TAGS)


def _iso(s: str) -> Optional[dt.date]:
    try:
        return dt.date.fromisoformat(s)
    except Exception:
        return None


def clip_facts_by_filed(facts: dict, cutoff: dt.date) -> dict:
    """複製一份 facts,只保留 filed <= cutoff 的列(知情時點過濾)。

    之後餵給 IE.instant_series / IE._latest,兩個函式的演算法完全不改一個字,
    只是它們現在只看得到「觸發日當時已經公布」的事實。
    """
    out_taxes: dict = {}
    for taxonomy, tags in facts.get("facts", {}).items():
        out_tags: dict = {}
        for tag, node in tags.items():
            out_units: dict = {}
            for unit, rows in node.get("units", {}).items():
                kept = []
                for r in rows:
                    fd = _iso(r.get("filed", ""))
                    if fd is not None and fd <= cutoff:
                        kept.append(r)
                if kept:
                    out_units[unit] = kept
            if out_units:
                out_tags[tag] = {"units": out_units}
        if out_tags:
            out_taxes[taxonomy] = out_tags
    return {"facts": out_taxes}


@functools.lru_cache(maxsize=None)
def _load_facts_cached(cik: str) -> Optional[dict]:
    try:
        return IE.load_facts(cik)
    except FileNotFoundError:
        return None


def _has_any_debt_tag_before(facts: dict, cutoff: dt.date) -> bool:
    """DEBT_CUR_TAGS+DEBT_NC_TAGS 五條標籤,知情時點內(filed<=cutoff)有沒有出過
    任何一筆——用來分辨「真的沒有任何債務標籤」(→ 資料不足)和「有標籤,只是甲那套
    後備邏輯挑出來的值剛好是 0」(→ 有值,值為 0)。"""
    for tag in DEBT_TAGS_ALL:
        for r in IE._rows(facts, tag):
            fd = _iso(r.get("filed", ""))
            if fd is not None and fd <= cutoff:
                return True
    return False


def fallback_total_debt(entity_id: str, panel_period_end: dt.date, trigger_date: dt.date,
                        tol_days: int = 200) -> dict:
    """回傳:
      status      "companyfacts_fallback" | "資料不足"
      total_debt  float | None(companyfacts_fallback 時才有)
      debt_cur    float | None
      debt_nc     float | None
      reason      資料不足時的原因;有值時是用到哪組標籤
    """
    facts = _load_facts_cached(entity_id)
    if facts is None:
        return dict(status="資料不足", total_debt=None, debt_cur=None, debt_nc=None,
                   reason="無 companyfacts 快照檔")

    if not _has_any_debt_tag_before(facts, trigger_date):
        return dict(status="資料不足", total_debt=None, debt_cur=None, debt_nc=None,
                   reason="知情時點內,DEBT_CUR_TAGS+DEBT_NC_TAGS 五條標籤全部沒出現過")

    clipped = clip_facts_by_filed(facts, trigger_date)
    notes: list = []
    cur_series = IE.instant_series(clipped, IE.DEBT_CUR_TAGS, asof=panel_period_end,
                                   tol_days=tol_days, label="短期有息負債(後備)", notes=notes)
    nc_series = IE.instant_series(clipped, IE.DEBT_NC_TAGS, asof=panel_period_end,
                                  tol_days=tol_days, label="長期有息負債(後備)", notes=notes)
    debt_cur = IE._latest(cur_series, panel_period_end, tol_days=tol_days)
    debt_nc = IE._latest(nc_series, panel_period_end, tol_days=tol_days)
    total = debt_cur + debt_nc

    # 知情時點再斷言一次(防禦性):series 裡真正被 _latest 選中的那個 end 日期,
    # 回頭在 clipped facts(已經砍走 filed>trigger_date 的列)裡找它的 filed 日期,
    # 必須 <= 觸發日——clip 已經保證這件事,這裡是二次核對,不是重覆過濾。
    for series, tags in ((cur_series, IE.DEBT_CUR_TAGS), (nc_series, IE.DEBT_NC_TAGS)):
        ends = [e for e in series if e <= panel_period_end]
        if not ends:
            continue
        e = max(ends)
        if (panel_period_end - e).days > tol_days:
            continue
        best_filed = None
        for tag in tags:
            for r in IE._rows(clipped, tag):
                if r.get("end") == str(e):
                    fd = _iso(r.get("filed", ""))
                    if fd is not None and (best_filed is None or fd > best_filed):
                        best_filed = fd
        if best_filed is not None and best_filed > trigger_date:
            raise AssertionError(
                "知情時點違規(後備債務標籤):entity=%s end=%s filed=%s > 觸發日 %s"
                % (entity_id, e, best_filed, trigger_date))

    return dict(status="companyfacts_fallback", total_debt=total,
               debt_cur=debt_cur, debt_nc=debt_nc,
               reason="DEBT_CUR_TAGS+DEBT_NC_TAGS(甲有序後備清單,asof=面板季末)")
