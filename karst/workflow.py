"""Read-only production intake: resolve scope, expose existing state, sequence tools.

This is a work plan, never a recommendation or a claim of completed research.
No extra task database: knowledge, evidence, research and watches own their state.
"""
from __future__ import annotations

from . import knowledge, service
from .schema import ContractError, canonical, digest

INTENTS = ("add", "compare", "analyze", "update")
KINDS = ("stock", "fund", "value_chain", "market")
RESULT_SCHEMA = {
    "type": "object", "required": ["request", "existing", "steps", "completion"],
    "properties": {key: {"type": kind} for key, kind in
                   (("request", "object"), ("existing", "object"),
                    ("steps", "array"), ("completion", "object"))},
}


def plan(store, data_dir, *, subject, kind, intent, question, universe_id=None,
         benchmark=None):
    if kind not in KINDS or intent not in INTENTS:
        raise ContractError("Unknown workflow kind or intent")
    if not all(isinstance(x, str) and x.strip() for x in (subject, question)):
        raise ContractError("Resolved subject and investment question required")
    if kind == "value_chain" and not universe_id:
        raise ContractError("Value-chain requests require an explicit universe_id")
    for value in (universe_id, benchmark):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ContractError("Optional identifiers must be nonempty strings")
    request = dict(subject=subject, kind=kind, intent=intent, question=question,
                   universe_id=universe_id, benchmark=benchmark)
    universe = knowledge.get(store, "universe", universe_id) if universe_id else None
    existing = {"entity": store.get_entity(subject),
                "universe_version": universe["version"] if universe else None,
                "members": universe["payload"]["members"] if universe else [],
                "research_version": None, "watch": store.get_watch(subject),
                "sources": [], "update_plan": None}
    if kind in ("stock", "fund"):
        bundle = service.company_paths(data_dir, subject)["bundle"]
        # Do not create a bundle or packet just to answer an intake request.
        if bundle.exists():
            context = service.get_research_context(store, bundle, subject, data_dir=data_dir)
            existing.update(research_version=context["latest_version_id"],
                            sources=context["sources"], update_plan=context["update_plan"])
            if existing['update_plan']:
                existing['update_plan'].pop('checked_at', None)
    steps = []

    def step(key, tool, purpose):
        steps.append({"key": key, "tool": tool, "purpose": purpose})

    step("scope", "get_knowledge", "核對身份、現有版本、價值鏈位置、同業組及實際問題；不把同層視為交易關係。")
    if universe_id:
        step("universe", "save_knowledge", "讀取後以 expected_version 追加名單；來源支持角色及每條有方向關係。相同請求不重建名單。")
    step("evidence", "refresh_sources / ingest_source / read_evidence",
         "取最新適用來源，分開資料期、公布日與取得日；失敗另列，沿用仍有效的舊證據。")
    step("comparison", "compare_registered_momentum / save_knowledge",
         "同收線日計算日／週／月相對表現、廣度及風險；盈利比率需同期間、同口徑，無意義倍數留空。")
    full = intent == "analyze" or (intent == "update" and existing["research_version"] is not None)
    if full:
        if kind == "stock":
            step("analysis", "get_research_protocol / read_evidence / calculate / render_charts / read_chart",
                 "首次分析讀完整業績及逐字稿；更新依受影響層重讀，同時挑戰舊假設及倍數。形成有期限的估值、實讀圖及可執行計劃。")
            step("save", "save_research / publish_research",
                 "保存主研究及計算回執；明示覆蓋缺口，舊版本與目標日不改写。")
            step("review", "request_review",
                 "按重要爭議安排獨立覆核；排隊與自查不等於獨立覆核完成。")
        elif kind == "fund":
            step("analysis", "read_evidence / calculate / render_charts / read_chart",
                 "研究指數盈利／估值、集中度、成分與產業驅動、費用、跟蹤、折溢價及分派；不向 ETF 索取公司營收或硬套公司 DCF。")
        else:
            step("analysis", "get_value_chain / get_research_context / read_evidence",
                 "比較現況與資金方向、敘事假設與風險、主要公司及機會排序；區分已深讀公司與僅機械比較。")
    elif intent == "update" and existing["research_version"] is None:
        step("radar_update", "get_knowledge / save_knowledge",
             "尚無正式研究，只更新比較與雷達；不稱評級維持或完成完整重評。")
    step("reader", "python -m karst.reader.release",
         "追加人類摘要及獨立 provenance，先預覽驗證再推送；保留既有歷史，讀回 Pages 與雲端版本。")
    step("follow_up", "set_watch / plan_update / record_update_check",
         "有正式研究才綁定 watch；記下一事件、假設與倍數失效條件。無變只記查核，未完成資料不當無變。")
    gaps = []
    if not benchmark:
        gaps.append("comparison_benchmark_required")
    if full and kind in ("fund", "market", "value_chain"):
        gaps.append("non_company_formal_research_contract_not_yet_supported")
    completion = {
        "deliverable": "investment_analysis" if full else "comparison_and_radar",
        "status": "planned", "blockers": gaps,
        "done_when": ["requested_scope_answered", "inputs_and_calculations_saved",
                      "human_summary_published_and_read_back", "next_checks_recorded"],
        "independent_review": "report_actual_status_separately",
        "schedule": "manual_on_request; no scheduler created by this plan",
    }
    result = {"request": request, "existing": existing, "steps": steps, "completion": completion}
    return {"plan_id": "workflow-" + digest(canonical(result)), **result}


def compare_registered(store, data_dir, *, weights, benchmark, cutoff, selected_on,
                       as_of, currency, history_sessions=200):
    """Calculate against actual registered candles, with a replayable input receipt.

Only explicit NoAdjust daily prices currently qualify. Adjusted prices are not
silently relabelled total returns. Evidence acquisition cutoff != price cutoff.
"""
    from .bars import series_from_evidence, _basis, Session
    from .momentum import compare
    from .packet import read_json, instant

    if not isinstance(weights, dict) or not weights or benchmark in weights:
        raise ContractError("Distinct benchmark and a nonempty member-weight mapping required")
    if type(history_sessions) is not int or not 2 <= history_sessions <= 5000:
        raise ContractError('history_sessions must be between 2 and 5000')
    if (not isinstance(as_of, str) or instant(as_of).tzinfo is None
            or instant(as_of).date().isoformat() < cutoff):
        raise ContractError("Evidence cutoff precedes price cutoff")
    series, sources = {}, {}
    session_bases = set()
    for subject in [benchmark, *weights]:
        bundle = service.company_paths(data_dir, subject)["bundle"]
        packet_path = bundle / "packet.json"
        if not packet_path.exists():
            raise ContractError(f"No registered price packet: {subject}")
        security = read_json(packet_path)["security"]
        if security["security_id"] != subject or security.get("currency") != currency:
            raise ContractError(f"Identity or currency mismatch: {subject}")
        records = service._registry(bundle).records()
        if not records and (bundle / "evidence.json").exists():
            records = read_json(bundle / "evidence.json")
        # Filter identity before source selection; never choose another security.
        records = [r for r in records if subject in r.get("entity_ids", [])]
        result = series_from_evidence(bundle, records, as_of,
                    session=Session.for_exchange(security.get("exchange")))
        if not result:
            raise ContractError(f"No eligible candles: {subject}")
        record = next(r for r in records if r["evidence_id"] == result["source"]["evidence_id"])
        basis = _basis(record)
        if basis["adjust"].lower() != "noadjust" or basis["period"].lower() != "day":
            raise ContractError(f"Explicit NoAdjust daily prices required: {subject}")
        session_bases.add(basis["session"].lower())
        series[subject] = [{"date": b["at"][:10], "close": b["close"], "complete": b["complete"]}
                           for b in result["bars"]["D"] if b["at"][:10] <= cutoff][-history_sessions:]
        sources[subject] = result["source"]
    if len(session_bases) != 1:
        raise ContractError("Trading-session bases differ")
    inputs = dict(series=series, weights=weights, benchmark=benchmark, cutoff=cutoff,
                  selected_on=selected_on, basis="unadjusted_price", currency=currency)
    output = compare(**inputs)
    receipt = {"schema_version": 1, "as_of": as_of, "history_sessions": history_sessions, "sources": sources,
               "input": inputs, "output": output}
    return {"receipt_id": "receipt-" + digest(canonical(receipt)), **receipt}
