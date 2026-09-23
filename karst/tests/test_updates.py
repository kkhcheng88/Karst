"""Incremental routing, lost-response retries and immutable judgment reuse."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from karst import service, updates
from karst.schema import ContractError, canonical
from karst.store import Store
from karst.tests.v03_fixture import ROLE_META, SECURITY, build_bundle, citable, payload

DAY = "2026-09-19T20:00:00Z"
EARLY = "2026-09-18T20:00:00Z"


def evidence(kind="prices", version="one", source="source", **extra):
    return {"source_id": source, "evidence_id": "ev-" + version,
            "source_version": version, "kind": kind, "status": "ok",
            "fetched_at": EARLY, "entity_ids": ["industry:power"], **extra}


def baseline(records):
    return {"version_id": "rv-one", "evidence": records,
            "payload": {"target_date": "2027-03-01", "valuation": {"valuation_date": "2026-09-18"},
                        "layers": {k: {"assessed_at": EARLY} for k in updates.LAYERS}}}


def watch(exposure="Supplier pricing power"):
    return {"waiting_for": "Capacity commissioning", "conditions": [],
            "validation_deadline": "2026-10-01T20:00:00Z",
            "subscriptions": [{"entity_id": "industry:power", "kinds": ["industry_report"]}],
            "dependencies": [{"input_kind": "relation", "input_id": "power-capacity",
                              "input_version": "one", "assumption_id": "margin",
                              "assumption_version": "one", "layers": ["L2"], "exposure": exposure}]}


class RoutingTests(unittest.TestCase):
    def test_report_filters_distinguish_author_source_and_real_url_boundary(self):
        w=watch();w['dependencies']=[]
        w['subscriptions'][0].update(authors=['Analyst A'], source_types=['broker_report'],
                                     url_prefixes=['https://example.com/research/power'])
        updates.validate_watch(w)
        report=evidence('industry_report', params={'author':' analyst a ', 'source_type':'broker_report'},
                        source_url='https://example.com/research/power/new-note')
        self.assertTrue(updates.subscribed(report,w))
        for url in ('https://example.com.evil.test/research/power/new-note',
                    'https://example.com/research/powerful', 'http://example.com/research/power/new-note'):
            self.assertFalse(updates.subscribed(report | {'source_url':url},w))
        self.assertFalse(updates.subscribed(report | {'params':{'author':'Other','source_type':'broker_report'}},w))
        self.assertFalse(updates.subscribed(report | {'params':{}},w))
        w['subscriptions'][0]['source_ids']=['different-report']
        self.assertFalse(updates.subscribed(report,w))
        for bad in ([], ['https://user:password@example.com/research'], ['https://example.com/research?token=secret']):
            w['subscriptions'][0]['url_prefixes']=bad
            with self.assertRaises(ContractError):updates.validate_watch(w)

    def test_reviewed_report_revision_does_not_repeat_alert_or_mask_next_revision(self):
        old=evidence('industry_report', 'one')
        new=evidence('industry_report', 'two', fetched_at=DAY)
        w=watch();w['dependencies'][0].update(input_kind='source', input_id='source',input_version='two')
        w['dependencies'].append(w['dependencies'][0] | {'input_kind':'entity','input_id':'industry:power'})
        row={'payload':w,'version':'watch-one','based_on_version_id':'rv-one'}
        self.assertEqual(updates.plan('X:A',baseline([old]),[old,new],as_of=DAY,watch=row)['status'],'no_change')
        stale=updates.plan('X:A',baseline([old]),[old,new],as_of=DAY,watch=row | {'based_on_version_id':'older-research'})
        self.assertIn('L2',stale['affected_layers'])
        revised=evidence('industry_report','three',fetched_at=DAY,supersedes='ev-two')
        result=updates.plan('X:A',baseline([old]),[old,new,revised],as_of=DAY,watch=row)
        self.assertEqual(result['affected_layers'],['L2','L3','L4','L6'])
        self.assertNotIn('rating',result)

    def test_acquisition_clock_is_not_news_and_source_period_correction_is(self):
        old = evidence()
        r = updates.plan("X:A", baseline([old]), [dict(old, fetched_at=DAY)], as_of=DAY)
        self.assertEqual(r["status"], "no_change")
        corrected = evidence(version="corrected-period", period={"end": "2026-06-30"}, fetched_at=DAY)
        r = updates.plan("X:A", baseline([old]), [old, corrected], as_of=DAY)
        self.assertEqual(len(r["source_changes"]), 1)
        self.assertEqual(r["source_changes"][0]["change"], "changed")
        self.assertTrue(r["price_only"])
        self.assertEqual(r["reuse_candidates"], ["L1", "L2", "L3"])
        self.assertEqual(r["preserve"]["valuation_date"], "2026-09-18")
        self.assertEqual(r["preserve"]["target_date"], "2027-03-01")

    def test_uncited_transcript_and_unknown_kind_are_not_ignored(self):
        old = evidence()
        for kind in ("transcript", "other_public"):
            r = updates.plan("X:A", baseline([old]), [old, evidence(kind, "new", "new-doc")], as_of=DAY)
            self.assertIn("L3", r["affected_layers"])
            self.assertIn("L4", r["affected_layers"])
            self.assertIn("L6", r["affected_layers"])

    def test_shared_input_has_distinct_exposure_and_no_automatic_rating(self):
        event = {"kind": "relation", "id": "power-capacity", "version": "two", "reason": "Capacity delay"}
        outcomes = []
        for subject, exposure in (("X:SUPPLIER", "Scarce supply supports equipment pricing"),
                                  ("X:BUYER", "Delayed delivery slows data centre revenue")):
            w = {"payload": watch(exposure), "version": "watch-one", "based_on_version_id": "rv-one"}
            r = updates.plan(subject, baseline([]), [], as_of=DAY, watch=w, input_changes=[event])
            self.assertEqual(r["affected_layers"], ["L2", "L3", "L4", "L6"])
            self.assertNotIn("rating", r)
            outcomes.append(r["reasons"][0]["dependency"]["exposure"])
        self.assertNotEqual(*outcomes)
        self.assertTrue(updates.subscribed(evidence("industry_report"), watch()))
        self.assertFalse(updates.subscribed(evidence("industry_report", entity_ids=["unrelated"]), watch()))

    def test_deadline_absence_and_unconfirmed_price_remain_questions(self):
        w = watch()
        w["validation_deadline"] = EARLY
        w["conditions"] = [{"kind": "price", "description": "Confirm a daily breakout", "operator": "gte", "value": 100, "currency": "USD"}]
        row = {"payload": w, "version": "watch-one", "based_on_version_id": "rv-one"}
        r = updates.plan("X:A", baseline([]), [], as_of=DAY, watch=row,
                         market={"price": 110, "currency": "USD", "adjustment": "raw", "complete": False})
        self.assertIn("validation_due", [x["kind"] for x in r["reasons"]])
        self.assertEqual(r["conditions"][0]["status"], "unknown")
        self.assertNotIn("L5", r["affected_layers"])
        r = updates.plan("X:A", baseline([]), [], as_of=DAY, watch=row,
                         market={"price": 110, "currency": "USD", "adjustment": "raw", "complete": True})
        self.assertEqual(r["conditions"][0]["status"], "threshold_met")
        self.assertIn("L5", r["affected_layers"])
        r = updates.plan("X:A", baseline([]), [], as_of=DAY, watch=row,
                         market={"price": 110, "currency": "USD", "adjustment": "ForwardAdjust", "complete": True})
        self.assertEqual(r["conditions"][0]["status"], "unknown")

    def test_failure_does_not_become_no_change_or_erase_successful_old_sources(self):
        old = evidence()
        failed = evidence(version="failure", status="error", status_reason="Connection failed", fetched_at=DAY)
        r = updates.plan("X:A", baseline([old]), [old, failed], as_of=DAY)
        self.assertEqual(r["status"], "incomplete")
        self.assertEqual(r["source_changes"], [])
        self.assertEqual(r["diagnostics"][0]["status"], "error")
        future = evidence(version="future", fetched_at="2026-09-20T20:00:00Z")
        r = updates.plan("X:A", baseline([old]), [old, future], as_of=DAY)
        self.assertEqual(r["status"], "no_change")

    def test_same_observation_inputs_have_same_plan_and_missing_snapshot_escalates(self):
        old = evidence()
        a = updates.plan("X:A", baseline([old]), [old], as_of=DAY,
                         refresh_status=[{"status": "ok", "adapter": "prices", "checked_at": EARLY}])
        b = updates.plan("X:A", baseline([old]), [old], as_of=DAY,
                         refresh_status=[{"status": "ok", "adapter": "prices", "checked_at": DAY}])
        self.assertEqual(a["plan_id"], b["plan_id"])
        missing = baseline(None)
        r = updates.plan("X:A", missing, [], as_of=DAY)
        self.assertEqual(r["status"], "needs_reassessment")

    def test_return_to_an_older_source_version_uses_observation_journal(self):
        a = evidence(version="a")
        b = evidence(version="b", fetched_at="2026-09-19T10:00:00Z", supersedes="ev-a")
        old = baseline([a, b]) | {"as_of": "2026-09-19T12:00:00Z"}
        receipts = [{"evidence_id": "ev-a", "fetched_at": DAY}]
        r = updates.plan("X:A", old, [a, b], as_of=DAY, observations=receipts)
        self.assertEqual(r["source_changes"][0]["previous_evidence_id"], "ev-b")
        self.assertEqual(r["source_changes"][0]["evidence_id"], "ev-a")

    def test_same_second_revisions_do_not_depend_on_frozen_list_order(self):
        a = evidence(version="z")
        b = evidence(version="a", supersedes="ev-z")
        self.assertEqual(updates.latest_sources([b, a], DAY)["source"]["evidence_id"], "ev-a")


class PersistenceTests(unittest.TestCase):
    def test_ingested_author_report_revision_routes_but_unselected_author_does_not(self):
        source_bundle=service.company_paths(self.root,'industry:power')['bundle']
        def ingest(author,excerpt):
            return service.ingest_source(source_bundle,url='https://example.com/research/power/note',
                excerpt=excerpt,author=author,published_at='2026-09-19',kind='industry_report',
                entity_ids=['industry:power'],title='Capacity outlook',source_type='broker_report',store=self.store)
        rejected=ingest('Other Analyst','Higher capacity forecast')
        selected=ingest('Selected Analyst','Margin forecast 20 percent')
        self.assertEqual(selected['document']['author'],'Selected Analyst')
        self.assertTrue(selected['source_version'])
        protocol=service.get_research_protocol('research')['version']
        prior=baseline([])['payload'] | {'method_version':protocol['declared']+'+'+protocol['digest'][:12]}
        first=self.store.save_research_version('reader',prior,evidence=[],as_of=EARLY)
        w=watch();w['dependencies']=[]
        w['subscriptions'][0].update(authors=['Selected Analyst'],source_types=['broker_report'])
        self.store.save_watch('reader',w,first['version_id'])
        first_plan=service.plan_update(self.store,self.root/'empty','reader',data_dir=self.root)
        self.assertEqual([x['evidence_id'] for x in first_plan['source_changes']],[selected['evidence_id']])
        retry=ingest('Selected Analyst','Margin forecast 20 percent')
        self.assertEqual(retry['evidence_id'],selected['evidence_id'])
        revised=ingest('Selected Analyst','Margin forecast 15 percent')
        latest=service.plan_update(self.store,self.root/'empty','reader',data_dir=self.root)
        self.assertEqual([x['evidence_id'] for x in latest['source_changes']],[revised['evidence_id']])
        self.assertEqual(latest['source_changes'][0]['source_version'],revised['source_version'])
        self.assertEqual(latest['affected_layers'],['L2','L3','L4','L6'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(self.root)
        self.store = Store(self.root / "state.sqlite")
        self.addCleanup(self.store.close)
        self.analysis = payload(self.packet, citable(self.bundle, self.records))
        self.analysis["plan"]["next_review_at"] = self.analysis["target_date"] + "T20:00:00Z"
        self.subject = SECURITY["security_id"]

    def save(self, analysis=None, previous=None):
        return service.save_research(self.store, self.bundle, analysis or self.analysis,
                                     subject=self.subject, role_meta=ROLE_META,
                                     expected_previous_version_id=previous)

    def test_lost_save_response_retry_returns_exact_version_after_restart(self):
        first = self.save()
        with Store(self.store.path) as restarted:
            retry = service.save_research(restarted, self.bundle, self.analysis,
                                           subject=self.subject, role_meta=ROLE_META)
        self.assertTrue(retry["idempotent_replay"])
        self.assertEqual(retry["version_id"], first["version_id"])
        self.assertEqual(retry["payload"], first["payload"])
        self.assertEqual(len(self.store.list_research(self.subject)), 1)
        changed = copy.deepcopy(self.analysis)
        changed["headline"]["change_since_last"]["text"] = "Corrected wording"
        conflict = self.save(changed)
        self.assertTrue(conflict["conflict"])

    def test_price_update_retains_economics_dates_and_exposes_real_differences(self):
        first = self.save()
        before = canonical(first["payload"])
        p = copy.deepcopy(self.analysis)
        p["market"]["price"] += 1
        p["headline"]["change_since_last"]["text"] = "Price changed; operating assumptions and target horizon unchanged."
        p["layers"]["L5"]["conclusion"]["text"] += " Price changed."
        second = self.save(p, first["version_id"])
        self.assertEqual(second["payload"]["target_date"], first["payload"]["target_date"])
        self.assertEqual(second["payload"]["valuation"], first["payload"]["valuation"])
        for layer in ("L1", "L2", "L3", "L4"):
            self.assertEqual(second["payload"]["layers"][layer], first["payload"]["layers"][layer])
        context = service.get_research_context(self.store, self.bundle, self.subject,
                                              as_of_version=second["version_id"])
        diff = context["changes_since_previous"]
        self.assertEqual(diff["layers"]["L3"]["mode"], "reused")
        self.assertEqual(diff["layers"]["L5"]["mode"], "reassessed")
        self.assertIn("market", [c["field"] for c in diff["changes"]])
        self.assertEqual(canonical(self.store.get_research(first["version_id"])["payload"]), before)

    def test_watch_revalidation_check_dedupe_and_failure_disclosure(self):
        first = self.save()
        w = self.store.save_watch(self.subject, watch(), first["version_id"])
        with self.assertRaises(ContractError):
            self.store.save_watch("OTHER:COMPANY", watch(), first["version_id"])
        revised = watch("Different exposure")
        with self.assertRaises(ContractError):
            self.store.save_watch(self.subject, revised, first["version_id"])
        plan = service.plan_update(self.store, self.bundle, self.subject)
        check = service.record_update_check(self.store, self.bundle, self.subject,
                                             plan["plan_id"], "unchanged", "No new company evidence; existing conclusion retained.")
        retry = service.record_update_check(self.store, self.bundle, self.subject,
                                             plan["plan_id"], "unchanged", "No new company evidence; existing conclusion retained.")
        self.assertEqual(check["check_id"], retry["check_id"])
        self.assertEqual(len(self.store.list_research(self.subject)), 1)
        self.store.record_refresh(self.subject, "provider", {"adapter": "provider", "status": "error", "error": "network"})
        with self.assertRaisesRegex(ContractError, "changed"):
            service.record_update_check(self.store, self.bundle, self.subject, plan["plan_id"], "unchanged", "Stale")
        failed = service.plan_update(self.store, self.bundle, self.subject)
        with self.assertRaisesRegex(ContractError, "Incomplete"):
            self.store.record_update_check(failed, "unchanged", "Cannot hide retrieval failure")
        saved = self.store.record_update_check(failed, "incomplete", "Retry provider before confirming no changes")
        self.assertEqual(saved["payload"]["outcome"], "incomplete")

    def test_refresh_failure_survives_context_and_other_adapter_success(self):
        self.save()
        broken = {"longbridge": {"adapter": "longbridge", "status": "failed", "scope": None, "feeds": [
            {"feed": "longbridge", "status": "failed", "cause": "error", "reason": "connection failed"}]}}
        with patch("karst.service._run_adapters", return_value=([], broken)):
            result = service.refresh_sources(self.root, SECURITY, ["prices"], store=self.store,
                                             bundle=self.bundle, staging=self.root / "new-stage")
        self.assertEqual(result["update_plan"]["status"], "incomplete")
        self.store.record_refresh(self.subject, "edgar", {"adapter": "edgar", "status": "ok"})
        context = service.get_research_context(self.store, self.bundle, self.subject)
        self.assertEqual(context["update_plan"]["status"], "incomplete")

    def test_new_industry_source_routes_across_two_subscribed_company_bundles(self):
        report = evidence("industry_report", "new-report", "shared-report")
        protocol = service.get_research_protocol("research")["version"]
        sources = {"supplier": [], "buyer": [], "industry": [report]}
        with patch("karst.service.company_bundles", return_value=list(sources)), patch(
                "karst.triage._records", side_effect=lambda p: sources[str(p)]):
            for subject, exposure in (("supplier", "Pricing power rises"), ("buyer", "Input costs rise")):
                p = baseline([])["payload"] | {"method_version": protocol["declared"] + "+" + protocol["digest"][:12]}
                first = self.store.save_research_version(subject, p, evidence=[], as_of=EARLY)
                w = watch(exposure)
                w["dependencies"][0].update(input_kind="entity", input_id="industry:power")
                self.store.save_watch(subject, w, first["version_id"])
                result = service.plan_update(self.store, subject, subject, data_dir=self.root)
                self.assertEqual(result["affected_layers"], ["L2", "L3", "L4", "L6"])
                self.assertEqual(result["source_changes"][0]["dependencies"][0]["exposure"], exposure)
                self.assertEqual(result["source_changes"][0]["evidence_id"], "ev-new-report")


if __name__ == "__main__":
    unittest.main()
