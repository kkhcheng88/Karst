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
        server = mcp_server.build(cls.data, auth=mcp_server.bearer_auth(TOKEN))
        cls.thread = threading.Thread(
            target=server.run,
            kwargs={"transport": "http", "host": "127.0.0.1", "port": cls.port,
                    "show_banner": False},
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
                return names, result.data
        names, result = asyncio.run(call())
        self.assertIn("search_evidence", names)
        self.assertIn("refresh_sources", names)
        self.assertEqual(names & {"submit_order", "account_balance", "stock_positions"}, set())
        self.assertEqual(result["method"], "sma")


if __name__ == "__main__":
    unittest.main()
