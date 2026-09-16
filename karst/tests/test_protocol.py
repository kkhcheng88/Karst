"""The method has one versioned source; each mode returns the same content on retry."""
import unittest

from jsonschema import Draft202012Validator

from karst.agents.protocol import DECLARED, MODES, get_research_protocol
from karst.schema import ContractError


class ProtocolTests(unittest.TestCase):
    def test_every_mode_returns_the_same_pinned_content_twice(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                first = get_research_protocol(mode)
                self.assertEqual(first['mode'], mode)
                self.assertEqual(first['version']['declared'], DECLARED)
                self.assertTrue(first['steps'])
                Draft202012Validator.check_schema(first['output_schema'])
                again = get_research_protocol(mode, version=first['version']['digest'])
                self.assertEqual(first, again)
                self.assertEqual(get_research_protocol(mode, version=DECLARED), first)

    def test_content_comes_from_the_strategy_sources_not_a_second_copy(self):
        text = get_research_protocol('research')['text']
        self.assertIn('研究委託（正本）', text)
        self.assertIn('六層分析紀律', text)
        for layer in ('L1', 'L2', 'L3', 'L4', 'L5', 'L6'):
            self.assertIn(f'## {layer}', text)
        self.assertIn('情境問題', text)
        self.assertIn('已量度', text)  # the prompt forbids the label explicitly

    def test_modes_differ_and_unknown_mode_or_version_is_refused(self):
        digests = {mode: get_research_protocol(mode)['version']['digest'] for mode in MODES}
        self.assertEqual(len(set(digests.values())), len(MODES))
        self.assertNotEqual(get_research_protocol('review')['output_schema'],
                            get_research_protocol('research')['output_schema'])
        with self.assertRaises(ContractError):
            get_research_protocol('freestyle')
        with self.assertRaises(ContractError):
            get_research_protocol('research', version='research-protocol-v0')


if __name__ == '__main__':
    unittest.main()
