"""Who gets in: token mode, GitHub OAuth discovery, and the login allowlist. No network calls out."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.server.auth.providers.github import GitHubTokenVerifier
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from starlette.testclient import TestClient

from karst import auth as auth_module, mcp_server

TOKEN = "test-token-not-a-credential"  # test literal; deployments read KARST_MCP_TOKEN
BASE_URL = "https://karst.example.invalid"
GITHUB_ENV = {
    auth_module.MODE_VARIABLE: "github",
    auth_module.CLIENT_ID_VARIABLE: "Ov23liNOTAREALCLIENT",
    auth_module.CLIENT_SECRET_VARIABLE: "not-a-real-client-secret-0123456789",
    auth_module.BASE_URL_VARIABLE: BASE_URL,
    auth_module.ALLOWED_USERS_VARIABLE: "the-owner, Second-Owner",
}
INITIALIZE = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                         "clientInfo": {"name": "test", "version": "0"}}}
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def github_token(login):
    """What GitHubTokenVerifier returns for a valid upstream token."""
    return AccessToken(token="upstream", client_id="42", scopes=["user"],
                       claims={"sub": "42", "login": login})


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.data = Path(self.directory.name)
        self.addCleanup(self.directory.cleanup)

    def test_token_mode_builds_a_static_verifier(self):
        auth = auth_module.build_auth(self.data, {auth_module.TOKEN_VARIABLE: TOKEN})
        self.assertIsInstance(auth, StaticTokenVerifier)

    def test_no_token_and_no_github_credentials_refuses_to_start(self):
        with self.assertRaises(auth_module.AuthConfigError) as caught:
            auth_module.build_auth(self.data, {})
        self.assertIn(auth_module.TOKEN_VARIABLE, str(caught.exception))

    def test_github_mode_without_client_credentials_refuses_to_start(self):
        environment = dict(GITHUB_ENV)
        environment.pop(auth_module.CLIENT_SECRET_VARIABLE)
        with self.assertRaises(auth_module.AuthConfigError) as caught:
            auth_module.build_auth(self.data, environment)
        self.assertIn(auth_module.CLIENT_SECRET_VARIABLE, str(caught.exception))

    def test_github_mode_without_an_allowlist_refuses_to_start(self):
        environment = dict(GITHUB_ENV, **{auth_module.ALLOWED_USERS_VARIABLE: "  , "})
        with self.assertRaises(auth_module.AuthConfigError) as caught:
            auth_module.build_auth(self.data, environment)
        self.assertIn(auth_module.ALLOWED_USERS_VARIABLE, str(caught.exception))

    def test_github_mode_without_a_base_url_refuses_to_start(self):
        environment = dict(GITHUB_ENV)
        environment.pop(auth_module.BASE_URL_VARIABLE)
        with self.assertRaises(auth_module.AuthConfigError) as caught:
            auth_module.build_auth(self.data, environment)
        self.assertIn(auth_module.BASE_URL_VARIABLE, str(caught.exception))

    def test_an_unknown_mode_is_refused(self):
        with self.assertRaises(auth_module.AuthConfigError):
            auth_module.build_auth(self.data, {auth_module.MODE_VARIABLE: "basic",
                                               auth_module.TOKEN_VARIABLE: TOKEN})

    def test_github_credentials_alone_select_github_mode(self):
        environment = dict(GITHUB_ENV)
        environment.pop(auth_module.MODE_VARIABLE)
        auth = auth_module.build_auth(self.data, environment)
        self.assertIsInstance(auth, OAuthProxy)
        self.assertEqual(auth._redirect_path, auth_module.CALLBACK_PATH)
        self.assertTrue((self.data / "oauth-proxy").is_dir())  # survives a container restart


class AllowlistTests(unittest.TestCase):
    """The allowlist is asked after GitHub has spoken, so GitHub is never called here."""

    def verify(self, login, allowed=("the-owner", "Second-Owner")):
        verifier = auth_module.AllowedGitHubUsers(allowed, required_scopes=["user"])
        with mock.patch.object(GitHubTokenVerifier, "verify_token",
                               new=mock.AsyncMock(return_value=github_token(login))):
            return asyncio.run(verifier.verify_token("upstream"))

    def test_a_listed_login_is_accepted(self):
        self.assertIsNotNone(self.verify("the-owner"))

    def test_the_list_ignores_case_and_spacing(self):
        self.assertIsNotNone(self.verify("SECOND-OWNER", allowed=(" second-owner ",)))

    def test_a_login_outside_the_list_is_refused(self):
        self.assertIsNone(self.verify("a-stranger"))

    def test_a_token_github_itself_rejects_stays_rejected(self):
        verifier = auth_module.AllowedGitHubUsers(["the-owner"])
        with mock.patch.object(GitHubTokenVerifier, "verify_token",
                               new=mock.AsyncMock(return_value=None)):
            self.assertIsNone(asyncio.run(verifier.verify_token("expired")))

    def test_an_empty_allowlist_is_refused_at_construction(self):
        with self.assertRaises(auth_module.AuthConfigError):
            auth_module.AllowedGitHubUsers([])


class HttpSurfaceTests(unittest.TestCase):
    """The routes a connector needs, served by the app itself - no port, no network."""

    def app(self, auth):
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        server = mcp_server.build(Path(directory.name) / "karst-data", auth=auth)
        return TestClient(server.http_app(path="/mcp"))

    def github_app(self):
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        return self.app(auth_module.build_auth(Path(directory.name), GITHUB_ENV))

    def test_token_mode_refuses_a_call_without_a_token(self):
        with self.app(auth_module.token_auth(TOKEN)) as client:
            response = client.post("/mcp", json=INITIALIZE, headers=MCP_HEADERS)
        self.assertEqual(response.status_code, 401)

    def test_token_mode_lets_the_right_token_through(self):
        with self.app(auth_module.token_auth(TOKEN)) as client:
            response = client.post("/mcp", json=INITIALIZE,
                                   headers={**MCP_HEADERS, "Authorization": f"Bearer {TOKEN}"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("protocolVersion", response.text)

    def test_github_mode_refuses_a_call_without_a_token(self):
        with self.github_app() as client:
            response = client.post("/mcp", json=INITIALIZE, headers=MCP_HEADERS)
        self.assertEqual(response.status_code, 401)
        self.assertIn("resource_metadata", response.headers.get("www-authenticate", ""))

    def test_github_mode_publishes_protected_resource_metadata(self):
        with self.github_app() as client:
            response = client.get("/.well-known/oauth-protected-resource/mcp")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["resource"].rstrip("/"), f"{BASE_URL}/mcp")
        self.assertEqual([str(server).rstrip("/") for server in body["authorization_servers"]],
                         [BASE_URL])

    def test_github_mode_publishes_authorization_server_metadata(self):
        with self.github_app() as client:
            response = client.get("/.well-known/oauth-authorization-server")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["authorization_endpoint"], f"{BASE_URL}/authorize")
        self.assertEqual(body["registration_endpoint"], f"{BASE_URL}/register")  # ChatGPT registers itself
        self.assertIn("S256", body["code_challenge_methods_supported"])

    def test_healthz_stays_open_in_github_mode(self):
        with self.github_app() as client:
            response = client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
