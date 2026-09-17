"""Who may reach the tools: one static Bearer token, or GitHub OAuth with a login allowlist.

``KARST_AUTH_MODE=github`` puts fastmcp's OAuth proxy in front of GitHub, so a
connector that only speaks OAuth (ChatGPT's custom MCP connector) can register
itself and obtain its own token; ``KARST_AUTH_MODE=token`` keeps the single fixed
token for local or transitional use. Either way HTTP mode refuses to start
unconfigured — an unauthenticated port would be a research *write* surface.

Authorising with GitHub only proves who you are; ``KARST_ALLOWED_GITHUB_USERS``
decides whether that person gets in at all. The check sits in the token verifier,
so it covers every request, not only tool calls.

Only environment variable *names* appear here; no value is ever written into the repo.
"""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

from cryptography.fernet import Fernet
from fastmcp.server.auth.jwt_issuer import derive_jwt_key
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.server.auth.providers.github import GitHubTokenVerifier
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from key_value.aio.stores.disk import DiskStore
from fastmcp.utilities.logging import get_logger
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

logger = get_logger(__name__)

MODE_VARIABLE = "KARST_AUTH_MODE"
TOKEN_VARIABLE = "KARST_MCP_TOKEN"
CLIENT_ID_VARIABLE = "KARST_GITHUB_CLIENT_ID"
CLIENT_SECRET_VARIABLE = "KARST_GITHUB_CLIENT_SECRET"
BASE_URL_VARIABLE = "KARST_BASE_URL"
ALLOWED_USERS_VARIABLE = "KARST_ALLOWED_GITHUB_USERS"

AUTHORIZE_ENDPOINT = "https://github.com/login/oauth/authorize"
TOKEN_ENDPOINT = "https://github.com/login/oauth/access_token"
# fastmcp's OAuthProxy default; the GitHub OAuth App's callback URL must be <base_url> + this.
CALLBACK_PATH = "/auth/callback"


class AuthConfigError(RuntimeError):
    """The requested mode cannot be configured from the environment."""


class AllowedGitHubUsers(GitHubTokenVerifier):
    """GitHub token verification, then one more question: is this login on the list?

    Returning ``None`` is how a verifier says no, so a stranger's token fails the
    same way an expired one does — 401 on every route, tools included.
    """

    # Every MCP request re-verifies the bearer token, and the upstream verifier asks
    # GitHub twice per call. A research run is hundreds of tool calls, so without a
    # cache that is hundreds of GitHub requests against a 5,000/hour budget — and the
    # failure mode is a silent 401 mid-run. Decisions are remembered briefly per token.
    CACHE_TTL_SECONDS = 60

    def __init__(self, allowed_logins, *, cache_ttl_seconds=None, clock=None, **kwargs):
        super().__init__(**kwargs)
        self.allowed_logins = {str(login).strip().lower() for login in allowed_logins
                               if str(login).strip()}
        if not self.allowed_logins:
            raise AuthConfigError("An empty allowlist would admit nobody; refusing to build it")
        self._ttl = self.CACHE_TTL_SECONDS if cache_ttl_seconds is None else cache_ttl_seconds
        self._clock = clock or time.monotonic
        self._cache = {}  # sha256(token) -> (expires_at, decision or None)

    async def verify_token(self, token: str):
        key = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = self._clock()
        cached = self._cache.get(key)
        if cached is not None and cached[0] > now:
            return cached[1]
        decision = await self._decide(token)
        if self._ttl > 0:
            if len(self._cache) > 1024:  # ponytail: bounded by wholesale reset, not LRU
                self._cache.clear()
            self._cache[key] = (now + self._ttl, decision)
        return decision

    async def _decide(self, token: str):
        verified = await super().verify_token(token)
        if verified is None:
            return None
        login = (verified.claims or {}).get("login")
        if not login or str(login).lower() not in self.allowed_logins:
            logger.warning("Refused GitHub login %r: not in %s", login, ALLOWED_USERS_VARIABLE)
            return None
        return verified


def token_auth(token):
    """One static Bearer token. Rotation is a deployment action, not a code change."""
    return StaticTokenVerifier({token: {"client_id": "karst-client", "scopes": []}})


def github_auth(*, client_id, client_secret, base_url, allowed_logins, data_dir):
    """GitHub OAuth (authorization code + PKCE) proxied by fastmcp; DCR handled locally."""
    return OAuthProxy(
        upstream_authorization_endpoint=AUTHORIZE_ENDPOINT,
        upstream_token_endpoint=TOKEN_ENDPOINT,
        upstream_client_id=client_id,
        upstream_client_secret=client_secret,
        token_verifier=AllowedGitHubUsers(allowed_logins, required_scopes=["user"]),
        base_url=base_url,
        redirect_path=CALLBACK_PATH,
        client_storage=_client_storage(data_dir, client_secret),
    )


def _client_storage(data_dir, client_secret):
    """OAuth state on the persistent volume, encrypted the way fastmcp's own default is.

    Left to itself fastmcp writes client registrations, transactions and upstream
    tokens under the per-user data directory, which a container loses on restart —
    and with them every registration a connector made. The keys derive from the
    upstream client secret, so they are the same after a restart as before.
    """
    signing_key = derive_jwt_key(high_entropy_material=client_secret, salt="fastmcp-jwt-signing-key")
    storage_key = derive_jwt_key(high_entropy_material=signing_key.decode(),
                                 salt="fastmcp-storage-encryption-key")
    directory = Path(data_dir) / "oauth-proxy"
    directory.mkdir(parents=True, exist_ok=True)
    return FernetEncryptionWrapper(key_value=DiskStore(directory=directory),
                                   fernet=Fernet(key=storage_key))


def build_auth(data_dir, environ=None):
    """The auth provider for HTTP mode, or ``AuthConfigError`` saying what is missing."""
    env = os.environ if environ is None else environ
    mode = (env.get(MODE_VARIABLE) or "").strip().lower()
    if not mode:
        mode = "github" if env.get(CLIENT_ID_VARIABLE) and env.get(CLIENT_SECRET_VARIABLE) else "token"
    if mode == "token":
        token = env.get(TOKEN_VARIABLE)
        if not token:
            raise AuthConfigError(
                f"--http in token mode needs a Bearer token in {TOKEN_VARIABLE}; refusing to "
                "serve research writes on an unauthenticated port")
        return token_auth(token)
    if mode != "github":
        raise AuthConfigError(f"{MODE_VARIABLE}={mode!r} is neither 'github' nor 'token'")

    missing = [name for name in (CLIENT_ID_VARIABLE, CLIENT_SECRET_VARIABLE)
               if not env.get(name)]
    if missing:
        raise AuthConfigError(
            f"{MODE_VARIABLE}=github needs the GitHub OAuth App credentials in "
            f"{' and '.join(missing)} (create the app first; see zeabur.md)")
    allowed_logins = [part.strip() for part in (env.get(ALLOWED_USERS_VARIABLE) or "").split(",")
                      if part.strip()]
    if not allowed_logins:
        raise AuthConfigError(
            f"{MODE_VARIABLE}=github needs {ALLOWED_USERS_VARIABLE} (comma-separated GitHub "
            "logins); without it any GitHub account on earth could write research")
    base_url = (env.get(BASE_URL_VARIABLE) or "").strip()
    if not base_url:
        raise AuthConfigError(
            f"{MODE_VARIABLE}=github needs the public address in {BASE_URL_VARIABLE} "
            f"(e.g. https://<your domain>); the OAuth callback is {BASE_URL_VARIABLE} + "
            f"{CALLBACK_PATH}")
    return github_auth(client_id=env[CLIENT_ID_VARIABLE], client_secret=env[CLIENT_SECRET_VARIABLE],
                       base_url=base_url, allowed_logins=allowed_logins, data_dir=data_dir)
