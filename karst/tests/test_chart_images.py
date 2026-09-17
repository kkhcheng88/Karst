"""The picture actually reaching the model: MCP image content and API image blocks.

A PNG in a directory proves nothing. What is under test here is that a chart leaves
this machine as an image — base64 bytes with a media type, over MCP as ImageContent
and over the two APIs as a tool-result image / an ``input_image`` — that only
registered artifacts can be read, and that a payload carrying nothing but a file
name is caught rather than mistaken for a reading. No network, no key, no SDK: every
transport is a fake and the MCP client is in-memory.
"""
import asyncio
import base64
import json
import tempfile
import unittest
from pathlib import Path

from fastmcp import Client

from karst import mcp_server, service, store as store_module
from karst.agents.adapters import TaskEvidence, anthropic_adapter, openai_adapter
from karst.agents.protocol import get_research_protocol
from karst.agents.research import export_task
from karst.schema import ContractError, digest
from karst.tests.test_charts import PNG_MAGIC
from karst.tests.test_publish_bars import candles, stage_prices
from karst.tests.v03_fixture import build_bundle, citable, payload

SUBJECT = "FIXTURE:FIXTURE"  # parameterized identity: the fixture security
BUDGET = {"max_turns": 5, "max_output_tokens": 4000}


def anthropic_reply(blocks):
    return {"id": "msg-fake", "content": blocks,
            "usage": {"input_tokens": 900, "cache_read_input_tokens": 0, "output_tokens": 200}}


def openai_reply(items):
    return {"id": "resp-fake", "output": items,
            "usage": {"input_tokens": 900, "output_tokens": 200}}


def image_blocks(payloads):
    """Every real image block in everything that was put on the wire, both wire formats."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "image" and isinstance(node.get("source"), dict):
                found.append({"media_type": node["source"].get("media_type"),
                              "data": node["source"].get("data")})
            elif node.get("type") == "input_image" and isinstance(node.get("image_url"), str):
                header, _, data = node["image_url"].partition(",")
                found.append({"media_type": header.removeprefix("data:").removesuffix(";base64"),
                              "data": data})
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payloads)
    return found


class ChartArtifactTests(unittest.TestCase):
    """render_charts hands out artifacts; the store is what makes one readable later."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(
            self.root, stage=stage_prices(candles(days=40)))
        self.store = store_module.init(self.root / "karst.sqlite3")
        self.addCleanup(self.store.close)

    def test_registered_artifacts_can_be_read_back_and_others_cannot(self):
        result = service.render_charts(self.bundle, self.root / "charts", store=self.store)
        for artifact in result["artifacts"]:
            found = service.chart_artifact(self.store, artifact["artifact_id"])
            with self.subTest(view=artifact["view"]):
                self.assertEqual(found["sha256"], artifact["sha256"])
                self.assertEqual(digest(found["data"]), artifact["sha256"])
                self.assertEqual(found["data"][:8], PNG_MAGIC)
                self.assertEqual(found["meta"]["period"], artifact["period"])
        with self.assertRaisesRegex(ContractError, "Unknown chart artifact"):
            service.chart_artifact(self.store, "cha-" + "0" * 64)

    def test_a_chart_whose_file_changed_is_refused_instead_of_served(self):
        artifact = service.render_charts(self.bundle, self.root / "charts",
                                         store=self.store)["artifacts"][0]
        Path(artifact["path"]).write_bytes(PNG_MAGIC + b"not the chart that was registered")
        with self.assertRaisesRegex(ContractError, "registered hash"):
            service.chart_artifact(self.store, artifact["artifact_id"])

    def test_the_remote_reply_carries_artifacts_instead_of_this_machines_paths(self):
        result = service.render_charts(self.bundle, self.root / "charts", store=self.store)
        remote = service.without_local_paths(result)
        self.assertNotIn("files", remote)
        self.assertNotIn(str(self.root), json.dumps(remote, default=str))
        self.assertEqual({a["view"] for a in remote["artifacts"]}, {"M", "W", "D", "DR"})
        self.assertTrue(all("path" not in a for a in remote["artifacts"]))
        self.assertTrue(all(a["artifact_id"] and a["sha256"] and a["bars_as_of"]
                            for a in remote["artifacts"]))


class McpChartTests(unittest.TestCase):
    """The MCP surface, in memory: render_charts then read_chart, as a client sees them."""

    def setUp(self):
        # The server holds its SQLite file open past teardown on Windows.
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(
            self.root, stage=stage_prices(candles(days=40)))
        self.server = mcp_server.build(self.root / "data", store_path=self.root / "state.sqlite",
                                       bundle=self.bundle)

    def call(self, name, arguments):
        async def run():
            async with Client(self.server) as client:
                return await client.call_tool(name, arguments)
        return asyncio.run(run())

    def test_a_chart_comes_back_as_image_content_not_a_path(self):
        rendered = self.call("render_charts", {"subject": SUBJECT}).data
        self.assertTrue(rendered["artifacts"])
        self.assertTrue(all("path" not in artifact for artifact in rendered["artifacts"]))
        artifact = next(a for a in rendered["artifacts"] if a["view"] == "DR")
        result = self.call("read_chart", {"artifact_id": artifact["artifact_id"]})
        images = [block for block in result.content if block.type == "image"]
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].mimeType, "image/png")
        data = base64.b64decode(images[0].data)
        self.assertEqual(data[:8], PNG_MAGIC)
        self.assertEqual(digest(data), artifact["sha256"])
        self.assertEqual(len(data), artifact["bytes"])
        said = json.loads(next(block.text for block in result.content if block.type == "text"))
        self.assertEqual(said["artifact_id"], artifact["artifact_id"])
        self.assertEqual(said["view"], "DR")
        self.assertEqual(said["bars_as_of"], rendered["data_as_of"])
        self.assertNotIn("path", said)

    def test_an_artifact_nobody_registered_cannot_be_read(self):
        async def run():
            async with Client(self.server) as client:
                return await client.call_tool("read_chart", {"artifact_id": "cha-" + "9" * 64},
                                              raise_on_error=False)
        result = asyncio.run(run())
        self.assertTrue(result.is_error)
        self.assertIn("Unknown chart artifact", str(result.content[0].text))

    def test_the_tool_list_offers_reading_a_chart_and_no_account_tools(self):
        async def run():
            async with Client(self.server) as client:
                return {tool.name for tool in await client.list_tools()}
        names = asyncio.run(run())
        self.assertIn("read_chart", names)
        self.assertIn("render_charts", names)
        self.assertEqual(names & {"submit_order", "account_balance", "read_file"}, set())


class AdapterImageTests(unittest.TestCase):
    """The API path: a staged chart goes out as real image content, and is recorded."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.packet, self.records = build_bundle(
            self.root, stage=stage_prices(candles(days=40)))
        self.evidence_id = citable(self.bundle, self.records)
        self.charts = service.render_charts(self.bundle, self.root / "charts")
        self.task = self.root / "task"
        self.context = export_task(self.bundle, {"security": self.packet["security"]},
                                   self.task, get_research_protocol("research"),
                                   charts=self.charts)
        self.artifact = next(a for a in self.context["charts"]["artifacts"] if a["view"] == "DR")
        self.result = payload(self.packet, self.evidence_id)

    def wants_chart(self, replies, artifact_id=None):
        """A fake model that reads one chart, then returns the analysis payload."""
        sent = []
        chart_call, final = replies

        def transport(request):
            sent.append(request)
            if len(sent) == 1:
                return chart_call(artifact_id or self.artifact["artifact_id"])
            return final(json.dumps(self.result))

        return sent, transport

    ANTHROPIC = (lambda artifact_id: anthropic_reply(
        [{"type": "tool_use", "id": "tu-1", "name": "read_chart",
          "input": {"artifact_id": artifact_id}}]),
        lambda text: anthropic_reply([{"type": "text", "text": text}]))
    OPENAI = (lambda artifact_id: openai_reply(
        [{"type": "function_call", "call_id": "call-1", "name": "read_chart",
          "arguments": json.dumps({"artifact_id": artifact_id})}]),
        lambda text: openai_reply([{"type": "message",
                                    "content": [{"type": "output_text", "text": text}]}]))

    def test_both_wires_send_the_image_itself_and_record_what_was_sent(self):
        staged = (self.task / self.artifact["path"]).read_bytes()
        for module, replies in ((anthropic_adapter, self.ANTHROPIC),
                                (openai_adapter, self.OPENAI)):
            sent, transport = self.wants_chart(replies)
            run = module.run(self.task, "model-under-test", BUDGET, transport=transport)
            images = image_blocks(sent)
            with self.subTest(provider=module.PROVIDER):
                self.assertEqual(run["result"], self.result)
                self.assertEqual(len(images), 1, "the chart must travel as image content")
                self.assertEqual(images[0]["media_type"], "image/png")
                self.assertEqual(base64.b64decode(images[0]["data"]), staged)
                # ...and the run says which chart, which version, which period.
                self.assertEqual(len(run["images_sent"]), 1)
                record = run["images_sent"][0]
                self.assertEqual(record["artifact_id"], self.artifact["artifact_id"])
                self.assertEqual(record["view"], "DR")
                self.assertEqual(record["sha256"], digest(staged))
                self.assertEqual(record["bars_as_of"], self.charts["data_as_of"])
                self.assertEqual(record["period"], "D")
                self.assertEqual(record["turn"], 1)
                # ...and the task keeps that record beside itself.
                kept = json.loads((self.task / "images_sent.json").read_text(encoding="utf-8"))
                self.assertEqual(kept["provider"], module.PROVIDER)
                self.assertEqual([image["artifact_id"] for image in kept["images"]],
                                 [self.artifact["artifact_id"]])

    def test_a_result_that_names_the_file_without_the_bytes_does_not_count(self):
        """The guard behind the test above: strip the image and nothing image-shaped
        is left on the wire, so a filename-only payload could never pass it."""
        original = TaskEvidence.chart
        try:
            TaskEvidence.chart = lambda self, artifact_id: {  # noqa: ARG005
                "artifact_id": artifact_id, "file": "daily_recent.png"}
            for module, replies in ((anthropic_adapter, self.ANTHROPIC),
                                    (openai_adapter, self.OPENAI)):
                sent, transport = self.wants_chart(replies)
                run = module.run(self.task, "model-under-test", BUDGET, transport=transport)
                with self.subTest(provider=module.PROVIDER):
                    self.assertEqual(image_blocks(sent), [])
                    self.assertEqual(run["images_sent"], [])
                    self.assertIn("daily_recent.png", json.dumps(sent, default=str))
        finally:
            TaskEvidence.chart = original

    def test_an_unstaged_chart_is_refused_and_the_error_lists_what_is_staged(self):
        sent, transport = self.wants_chart(self.ANTHROPIC, artifact_id="cha-" + "0" * 64)
        run = anthropic_adapter.run(self.task, "m", BUDGET, transport=transport)
        errors = [block for message in sent[-1]["messages"]
                  for block in (message["content"] if isinstance(message["content"], list) else [])
                  if isinstance(block, dict) and block.get("is_error")]
        self.assertEqual(len(errors), 1)
        self.assertIn("not staged with this task", json.dumps(errors[0], default=str))
        self.assertEqual(run["images_sent"], [])

    def test_the_calculator_is_a_tool_and_the_adapter_does_not_redo_the_arithmetic(self):
        evidence = TaskEvidence(self.task)
        done = evidence.call("calculate", {"method": "sma", "params": {
            "bars": [{"close": 10.0, "complete": True}, {"close": 12.0, "complete": True}],
            "window": 2}})
        self.assertEqual(done["result"]["sma"], 11.0)
        self.assertEqual(done["method"], "sma")

    def test_a_task_without_charts_does_not_advertise_reading_one(self):
        plain = self.root / "plain-task"
        export_task(self.bundle, {"security": self.packet["security"]}, plain,
                    get_research_protocol("research"))
        for module in (anthropic_adapter, openai_adapter):
            with self.subTest(provider=module.PROVIDER):
                offered = {tool["name"] for tool in
                           module.api_tools({"input": {"evidence": [], "charts": None}})}
                self.assertNotIn("read_chart", offered)
                self.assertIn("calculate", offered)
                with_charts = {tool["name"] for tool in module.api_tools(
                    {"input": {"charts": {"artifacts": [self.artifact]}}})}
                self.assertIn("read_chart", with_charts)
        evidence = TaskEvidence(plain)
        with self.assertRaisesRegex(ContractError, "not staged"):
            evidence.call("read_chart", {"artifact_id": self.artifact["artifact_id"]})


if __name__ == "__main__":
    unittest.main()
