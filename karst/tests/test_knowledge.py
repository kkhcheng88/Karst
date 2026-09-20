import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from karst import knowledge as k
from karst.schema import ContractError
from karst.store import Store

SOURCE = [{"url": "https://example.com/report", "title": "Results"}]


def universe():
    return {"name": "Compute", "summary": "Demand and supply", "sources": SOURCE,
            "members": [{"entity_id": x, "name": x, "kind": "company", "roles": ["compute"],
                         "comparison_groups": ["operators"]} for x in ("A", "B", "C")]}


def relation(a="A", b="B"):
    return {"from_entity": a, "to_entity": b, "relation_type": "supplies", "mechanism": "capacity",
            "status": "active", "valid_from": None, "valid_to": None, "basis": "documented", "sources": SOURCE}


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name)/"state.sqlite")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_versions_are_append_only_and_stale_writes_fail(self):
        first = k.save(self.store, "universe", "compute", universe())
        self.assertEqual(first, k.save(self.store, "universe", "compute", universe()))
        edited = universe() | {"summary": "Changed"}
        with self.assertRaises(ContractError):
            k.save(self.store, "universe", "compute", edited)
        second = k.save(self.store, "universe", "compute", edited, expected_version=first["version"])
        self.assertEqual(k.get(self.store, "universe", "compute", version=first["version"])["payload"], universe())
        reverted = k.save(self.store, "universe", "compute", universe(), expected_version=second["version"])
        self.assertNotEqual(first["version"], reverted["version"])

    def test_historical_graph_never_uses_later_discovery_and_traversal_is_bounded(self):
        with patch("karst.store.now", return_value="2026-01-01T00:00:00Z"):
            k.save(self.store, "universe", "compute", universe())
            edge = k.save(self.store, "relation", "ab", relation())
        with patch("karst.store.now", return_value="2026-01-03T00:00:00Z"):
            k.save(self.store, "relation", "bc", relation("B", "C") | {"valid_from": "2025-01-01"})
        old = k.value_chain(self.store, "compute", as_of="2026-01-02T00:00:00Z")
        self.assertEqual([r["object_id"] for r in old["relations"]], ["ab"])
        one = k.value_chain(self.store, "compute", focus="A", depth=1, as_of="2026-01-04T00:00:00Z")
        self.assertEqual([m["entity_id"] for m in one["members"]], ["A", "B"])
        self.assertEqual(len(k.value_chain(self.store, "compute", focus="A", depth=2)["members"]), 3)
        k.save(self.store, "relation", "ab", relation() | {"status": "withdrawn"}, expected_version=edge["version"])
        self.assertEqual(len(k.value_chain(self.store, "compute")["relations"]), 1)
        self.assertEqual(len(k.value_chain(self.store, "compute", as_of="2026-01-02T00:00:00Z")["relations"]), 1)

    def test_revised_assumption_finds_adopted_dependency(self):
        payload = {"subject": "A", "driver": "delivery", "statement": "Deliveries grow", "expected": 20,
                   "unit": "%", "period": "FY2027", "next_check": "Next results", "change_effect": "Recalculate revenue",
                   "layers": ["L3", "L4", "L6"], "status": "active", "sources": SOURCE}
        first = k.save(self.store, "assumption", "growth", payload)
        watch = {"payload": {"dependencies": [{"input_kind": "assumption", "input_id": "growth", "input_version": first["version"]}]}}
        self.assertEqual(k.dependency_changes(self.store, watch, as_of="2099-01-01T00:00:00Z"), [])
        second = k.save(self.store, "assumption", "growth", payload | {"expected": 10}, expected_version=first["version"])
        changes = k.dependency_changes(self.store, watch, as_of="2099-01-01T00:00:00Z")
        self.assertEqual(changes[0]["version"], second["version"])

    def test_no_dangling_relation_or_unattributed_input(self):
        with self.assertRaises(ContractError):
            k.save(self.store, "relation", "ab", relation())
        with self.assertRaises(ContractError):
            k.save(self.store, "universe", "compute", universe() | {"sources": []})
        bad = copy.deepcopy(universe())
        bad["members"].append(bad["members"][0])
        with self.assertRaises(ContractError):
            k.save(self.store, "universe", "compute", bad)

    def test_seed_restart_preserves_live_revision_and_period_basis(self):
        manifest = [{"kind": "universe", "object_id": "compute", "payload": universe()}]
        self.assertEqual(len(k.bootstrap(self.store, manifest)), 1)
        first = k.get(self.store, "universe", "compute")
        changed = k.save(self.store, "universe", "compute", universe() | {"summary": "Live edit"}, expected_version=first["version"])
        self.assertEqual(k.bootstrap(self.store, manifest), [])
        self.assertEqual(k.get(self.store, "universe", "compute")["version"], changed["version"])
        metric = {"key": "pe", "value": None, "unit": "x", "period": "FY2027", "basis": "adjusted",
                  "status": "missing", "source_index": 0}
        p = {"subject": "A", "as_of": "2026-01-01", "metrics": [metric], "sources": SOURCE}
        row = k.save(self.store, "comparison", "a-current", p)
        self.assertIsNone(k.value_chain(self.store, "compute")["comparisons"][0]["payload"]["metrics"][0]["value"])
        with self.assertRaises(ContractError):
            k.validate("comparison", p | {"metrics": [metric | {"value": 0}]})
        with self.assertRaises(ContractError):
            k.latest(self.store, "unknown")

    def test_actual_relation_revision_routes_through_service(self):
        from karst import service
        from karst.tests.test_updates import baseline, watch
        k.save(self.store, "universe", "compute", universe())
        first = k.save(self.store, "relation", "power-capacity", relation())
        w = watch()
        w["validation_deadline"] = None
        w["dependencies"][0]["input_version"] = first["version"]
        second = k.save(self.store, "relation", "power-capacity", relation() | {"mechanism": "Delayed"}, expected_version=first["version"])
        with patch.object(self.store, "latest_research", return_value=baseline([]) | {"created_at":"2020-01-01T00:00:00Z"}), patch.object(self.store, "get_watch", return_value={"payload":w}), patch("karst.service.get_research_protocol", return_value={"version":{"declared":"test","digest":"a"*64}}):
            result = service.plan_update(self.store, self.tmp.name, "A")
        reason = next(r for r in result["reasons"] if r["kind"] == "dependency_changed")
        self.assertEqual(reason["event"]["version"], second["version"])
        self.assertTrue({"L2", "L3", "L4", "L6"} <= set(result["affected_layers"]))
        self.assertNotIn("rating", result)

    def test_cross_matrix_preserves_mixed_cases_and_negative_eps_is_not_pe(self):
        result = k.valuation_matrix([{"label": "base", "eps": 4}, {"label": "up", "eps": 6},
                                     {"label": "loss", "eps": -1}], [40, 60],
                                     period="FY2027", earnings_basis="adjusted diluted", currency="USD")
        self.assertEqual(result["result"]["rows"][1]["prices"], [240, 360])
        self.assertEqual(result["result"]["rows"][2]["prices"], [None, None])
        for invalid in (True, float("nan"), -1, 1e308):
            with self.assertRaises(ContractError):
                k.valuation_matrix([{"label": "base", "eps": 4}], [invalid],
                                   period="FY2027", earnings_basis="GAAP", currency="USD")


if __name__ == "__main__":
    unittest.main()
