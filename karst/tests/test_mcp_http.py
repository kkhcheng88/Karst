"""Remote transport: the Bearer token gates the tools, /healthz stays open. No network calls out."""
import asyncio
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from karst import __version__, mcp_server

TOKEN = "test-token-not-a-credential"  # test literal; deployments read KARST_MCP_TOKEN


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class HttpTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The daemon server thread keeps the SQLite file open past teardown on Windows.
        cls.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.data = Path(cls.directory.name) / "karst-data"
        cls.port = free_port()
        cls.url = f"http://127.0.0.1:{cls.port}/mcp"
        def serve():
            from karst.store import Store
            from karst.tests.test_workflow import seed
            with Store(cls.data / 'karst.sqlite') as state:
                for subject in ('NYSE:DEMO', 'NYSE:INDEX'):
                    seed(cls.data, state, subject)
            # Like production, create and use the SQLite connection on the server
            # thread. Earlier transport tests called only the stateless calculator.
            server = mcp_server.build(cls.data, auth=mcp_server.bearer_auth(TOKEN))
            server.run(transport="http", host="127.0.0.1", port=cls.port, show_banner=False)
        cls.thread = threading.Thread(
            target=serve,
            daemon=True)
        cls.thread.start()
        cls.health = f"http://127.0.0.1:{cls.port}/healthz"
        for _ in range(100):
            try:
                httpx.get(cls.health, timeout=1.0)
                break
            except httpx.HTTPError:
                time.sleep(0.1)
        else:
            raise RuntimeError("HTTP server did not come up")

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_healthz_needs_no_token(self):
        response = httpx.get(self.health, timeout=5.0)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["version"], __version__)
        self.assertEqual(Path(body["data_dir"]), self.data)

    def test_no_token_is_refused(self):
        async def attempt():
            async with Client(StreamableHttpTransport(self.url)) as client:
                await client.list_tools()
        with self.assertRaises(Exception) as caught:  # noqa: B017 - transport-specific error type
            asyncio.run(attempt())
        self.assertIn("401", str(caught.exception))

    def test_a_valid_token_reaches_the_tools(self):
        async def call():
            headers = {"Authorization": f"Bearer {TOKEN}"}
            async with Client(StreamableHttpTransport(self.url, headers=headers)) as client:
                names = {tool.name for tool in await client.list_tools()}
                result = await client.call_tool(
                    "calculate", {"method": "sma", "params": {"bars": [], "window": 3}})
                watches = await client.call_tool("get_watchlist", {})
                update = await client.call_tool("plan_update", {"subject": "FIXTURE:NEW"})
                workflow = await client.call_tool('plan_workflow', {'subject': 'FIXTURE:NEW',
                    'kind': 'stock', 'intent': 'analyze', 'question': 'Can growth support the valuation?'})
                self.assertEqual(workflow.data['completion']['deliverable'], 'investment_analysis')
                report_plan = await client.call_tool('plan_workflow', {'subject': 'industry:fixture',
                    'kind': 'report', 'intent': 'add', 'question': 'What does the analyst report change?'})
                self.assertEqual(report_plan.data['completion']['deliverable'], 'report_impact_assessment')
                self.assertIn('compare_registered_momentum', names)
                self.assertIn('refresh_daily', names)
                compact = await client.call_tool('get_research_protocol', {'mode': 'workflow', 'include_schema': False})
                self.assertNotIn('output_schema', compact.data)
                source_schema = await client.call_tool('get_knowledge', {'kind':'schema'})
                self.assertIn('evidence_id', source_schema.data['source_reference'])
                comparison = await client.call_tool('compare_registered_momentum', {
                    'weights': {'NYSE:DEMO': 1.0}, 'benchmark': 'NYSE:INDEX', 'cutoff': '2026-04-10',
                    'selected_on': '2026-04-11', 'as_of': '2099-01-01T00:00:00Z', 'currency': 'USD'})
                self.assertAlmostEqual(comparison.data['output']['members']['NYSE:DEMO']['beta63'], 1)
                protocol = await client.call_tool('get_research_protocol', {'mode': 'workflow'})
                self.assertIn('沿用證據不等於沿用立場', protocol.data['text'])
                return names, result.data, watches.data, update.data
        names, result, watches, update = asyncio.run(call())
        self.assertIn("search_evidence", names)
        self.assertIn("refresh_sources", names)
        self.assertTrue({"get_watchlist", "set_watch", "plan_update", "record_update_check"} <= names)
        self.assertEqual(watches, {"watches": []})
        self.assertEqual(update["status"], "needs_reassessment")
        self.assertIsNone(update["base_version_id"])
        self.assertEqual(names & {"submit_order", "account_balance", "stock_positions"}, set())
        self.assertEqual(result["method"], "sma")

    def test_versioned_inputs_cross_authenticated_transport(self):
        from karst.tests.test_knowledge import universe, relation
        async def call():
            async with Client(StreamableHttpTransport(self.url, headers={"Authorization": f"Bearer {TOKEN}"})) as client:
                await client.call_tool("save_knowledge", {"kind":"universe", "object_id":"compute", "payload":universe()})
                scope = await client.call_tool('get_daily_scope', {'universe_id':'compute'})
                self.assertTrue(scope.data['members'])
                intake = await client.call_tool('refresh_daily_scope', {'universe_id':'compute'})
                self.assertFalse(intake.data['analysis_complete'])
                self.assertEqual(intake.data['intake_status'], 'incomplete')
                self.assertEqual(len(intake.data['results']), len(scope.data['members']))
                edge = await client.call_tool("save_knowledge", {"kind":"relation", "object_id":"ab", "payload":relation()})
                graph = await client.call_tool("get_value_chain", {"universe_id":"compute", "focus":"A"})
                context = await client.call_tool("get_research_context", {"subject":"A"})
                return edge.data, graph.data, context.data
        edge, graph, context = asyncio.run(call())
        self.assertEqual(graph["relations"][0]["version"], edge["record"]["version"])
        self.assertEqual(context["knowledge"]["relation"][0]["version"], edge["record"]["version"])


if __name__ == "__main__":
    unittest.main()
