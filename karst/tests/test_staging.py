"""One task-directory implementation for all three roles (KARST-246).

The six-role path, the single main researcher and a targeted review differ in what
they assemble, not in how it lands. Their end-to-end runs live in test_pipeline,
test_research_intake and test_review; this file pins the landing itself.
"""
import tempfile
import unittest
from pathlib import Path

from karst.agents import inputs as inputs_module, research as research_module, review as review_module
from karst.agents.staging import stage_task
from karst.packet import read_json
from karst.schema import ContractError

ARTIFACT = "evidence/objects/ab/abc.txt"
SCHEMA = {"type": "object", "additionalProperties": False, "properties": {}}


class StageTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle"
        (self.bundle / "evidence/objects/ab").mkdir(parents=True)
        (self.bundle / ARTIFACT).write_text("source text", encoding="utf-8")
        (self.bundle / "private-ledger.json").write_text("PRIVATE_SENTINEL", encoding="utf-8")
        self.evidence = [{"artifact": {"path": ARTIFACT}}]

    def stage(self, destination, **kwargs):
        return stage_task(self.bundle, self.evidence, destination=destination,
                          input_context={"allowed_evidence_ids": ["ev-1"]},
                          prompt_text="讀 input.json", output_schema=SCHEMA, **kwargs)

    def test_it_stages_the_allowed_sources_the_input_the_schema_and_the_prompt(self):
        task = self.stage(self.root / "task", prompt_name="review.md",
                          extra_files={"charts/derived.json": b'{"a": 1}',
                                       "charts/daily.png": self.bundle / ARTIFACT})
        self.assertEqual((task / ARTIFACT).read_text(encoding="utf-8"), "source text")
        self.assertEqual(read_json(task / "output.schema.json"), SCHEMA)
        self.assertEqual((task / "review.md").read_text(encoding="utf-8"), "讀 input.json")
        self.assertEqual(read_json(task / "input.json")["allowed_evidence_ids"], ["ev-1"])
        self.assertEqual(read_json(task / "charts/derived.json"), {"a": 1})
        self.assertTrue((task / "charts/daily.png").is_file())
        blob = b"".join(p.read_bytes() for p in task.rglob("*") if p.is_file())
        self.assertNotIn(b"PRIVATE_SENTINEL", blob, "only allowed artifacts are staged")

    def test_the_task_directory_is_new_and_never_the_bundle(self):
        with self.assertRaises(ContractError):
            self.stage(self.bundle)
        with self.assertRaises(ContractError):
            self.stage(self.root)  # a parent of the bundle would expose the whole store
        self.stage(self.root / "task")
        with self.assertRaises(FileExistsError):
            self.stage(self.root / "task")

    def test_a_failed_staging_leaves_nothing_behind(self):
        task = self.root / "task"
        with self.assertRaises(OSError):
            stage_task(self.bundle, [{"artifact": {"path": "evidence/objects/ab/missing.txt"}}],
                       destination=task, input_context={}, prompt_text="x", output_schema=SCHEMA)
        self.assertFalse(task.exists())

    def test_all_three_callers_go_through_it(self):
        for module in (inputs_module, research_module, review_module):
            with self.subTest(module=module.__name__):
                source = Path(module.__file__).read_text(encoding="utf-8")
                self.assertIn("stage_task(", source)
                self.assertNotIn("shutil.copyfile", source,
                                 "artifact copying lives in staging.py, once")


if __name__ == "__main__":
    unittest.main()
