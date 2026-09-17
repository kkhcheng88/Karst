"""The allowlist verifier remembers a decision per token briefly, so a research run's
hundreds of tool calls do not turn into hundreds of GitHub API calls."""
import asyncio
import unittest

from karst.auth import AllowedGitHubUsers


class FakeUpstream:
    """Stands in for GitHubTokenVerifier.verify_token: counts calls, answers by token."""

    def __init__(self, answers):
        self.answers, self.calls = answers, 0

    async def __call__(self, token):
        self.calls += 1
        return self.answers.get(token)


class Verified:
    def __init__(self, login):
        self.claims = {"login": login}


class AllowlistCacheTests(unittest.TestCase):
    def build(self, ttl, answers):
        clock = {"now": 1000.0}
        verifier = AllowedGitHubUsers(["owner"], cache_ttl_seconds=ttl, clock=lambda: clock["now"])
        upstream = FakeUpstream(answers)
        # Bypass the real GitHub lookup; only the allowlist + cache are under test.
        AllowedGitHubUsers.__mro__[1].verify_token = lambda self, token: upstream(token)
        return verifier, upstream, clock

    def test_repeated_calls_within_ttl_hit_upstream_once(self):
        verifier, upstream, clock = self.build(60, {"good": Verified("owner"), "bad": Verified("stranger")})
        run = asyncio.run
        self.assertIsNotNone(run(verifier.verify_token("good")))
        self.assertIsNotNone(run(verifier.verify_token("good")))
        self.assertIsNone(run(verifier.verify_token("bad")))
        self.assertIsNone(run(verifier.verify_token("bad")))
        self.assertEqual(upstream.calls, 2)
        clock["now"] += 61
        self.assertIsNotNone(run(verifier.verify_token("good")))
        self.assertEqual(upstream.calls, 3)

    def test_zero_ttl_disables_the_cache(self):
        verifier, upstream, _ = self.build(0, {"good": Verified("owner")})
        asyncio.run(verifier.verify_token("good"))
        asyncio.run(verifier.verify_token("good"))
        self.assertEqual(upstream.calls, 2)


if __name__ == "__main__":
    unittest.main()
