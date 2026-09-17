"""End-to-end CLI wiring, offline: fixtures and the synthetic example are the only inputs."""
import shutil
import tempfile
import unittest
from pathlib import Path

from karst.agents.assemble import LAYERS, UPSTREAM
from karst.fetch.port import pair_staging
from karst.packet import check_packet, read_json
from karst.pipeline import main
from karst.schema import canonical
from karst.tests import test_agents  # imported as a module so its cases are not re-collected

FIXTURES = Path(__file__).resolve().parent / 'fixtures'
SECURITY = {'security_id': 'FIXTURE:FIXTURE', 'issuer_id': 'cik:0000000000', 'ticker': 'FIXTURE',
            'name': 'Fixture issuer', 'currency': 'USD', 'exchange': 'FIXTURE'}


class RegisterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'bundle'
        self.staging = self.root / 'staging'
        shutil.copytree(FIXTURES / 'edgar', self.staging / 'edgar')
        (self.root / 'security.json').write_bytes(canonical(SECURITY))

    def run_cli(self, *args):
        self.assertEqual(main([args[0], '--bundle', str(self.bundle), *args[1:]]), 0)

    def test_exhibit_is_not_swallowed_by_its_parent_filing(self):
        pairs = dict(pair_staging(self.staging))
        stems = {meta: meta.name[: -len('.meta.json')] for meta in pairs}
        owned = [raw for raws in pairs.values() for raw in raws]
        self.assertEqual(len(owned), 13)
        self.assertEqual(len(set(owned)), 13)
        for meta, raws in pairs.items():
            self.assertTrue(raws, meta.name)
            for raw in raws:
                self.assertTrue(raw.name.startswith(stems[meta] + '.'))
                stolen = [stem for other, stem in stems.items()
                          if other != meta and raw.name.startswith(stem + '.')
                          and len(stem) > len(stems[meta])]
                self.assertEqual(stolen, [], f'{raw.name} belongs to {stolen}, not {stems[meta]}')

    def test_register_is_idempotent_then_packet_validates(self):
        security = ['--security-json', str(self.root / 'security.json')]
        for _ in range(2):
            self.run_cli('register', '--staging', str(self.staging), *security)
        manifest = (self.bundle / 'evidence' / 'manifest.jsonl').read_bytes().splitlines()
        self.assertEqual(len(manifest), 13)
        self.run_cli('packet', *security)
        packet = read_json(self.bundle / 'packet.json')
        records = read_json(self.bundle / 'evidence.json')
        selected = check_packet(packet, records, self.bundle)
        self.assertEqual(len(selected), 13)
        self.assertEqual(packet['diagnostic_ids'], [])
        self.run_cli('status')


class BundleCommandTests(unittest.TestCase):
    """Reuses the agent tests' hand-built fragments; the CLI must accept them unchanged."""

    rehash = test_agents.AgentTests.rehash

    def setUp(self):
        test_agents.AgentTests.setUp(self)
        self.fragment_dir = self.root / 'fragments'
        self.fragment_dir.mkdir()
        for role, fragment in self.fragments.items():
            (self.fragment_dir / f'{role}.json').write_bytes(canonical(fragment))
        (self.bundle / 'packet.json').write_bytes(canonical(self.packet))
        (self.bundle / 'evidence.json').write_bytes(canonical(self.records))
        (self.root / 'run.json').write_bytes(canonical(self.run))

    def run_cli(self, *args):
        self.assertEqual(main([args[0], '--bundle', str(self.bundle), *args[1:]]), 0)

    def test_prepare_builds_a_valid_task_directory_for_every_role(self):
        for role in LAYERS:
            self.run_cli('prepare', '--role', role, '--tasks', str(self.root / 'tasks'),
                         '--fragments', str(self.fragment_dir))
            task = self.root / 'tasks' / role
            context = read_json(task / 'input.json')
            canonical(context)
            self.assertEqual(context['role'], role)
            self.assertEqual(set(context['upstream']), set(UPSTREAM[role]))
            self.assertEqual(set(context['discipline_sections']), set(LAYERS[role]) or {'counter'})
            self.assertTrue(context['scenario_questions'])
            self.assertTrue((task / 'output.schema.json').is_file())

    def test_assemble_then_publish(self):
        (self.bundle / 'research.json').unlink()
        self.run_cli('assemble', '--fragments', str(self.fragment_dir), '--run', str(self.root / 'run.json'),
                     '--out', str(self.bundle / 'research.json'))
        self.run_cli('publish', '--output', str(self.root / 'releases'))
        releases = [p for p in (self.root / 'releases').iterdir() if p.is_dir()]
        self.assertEqual(len(releases), 1)
        self.assertTrue((releases[0] / 'index.html').is_file())
        self.run_cli('status', '--fragments', str(self.fragment_dir))


if __name__ == '__main__':
    unittest.main()
