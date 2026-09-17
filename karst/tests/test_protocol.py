"""The method has one versioned source; each mode returns the same content on retry."""
import unittest

from jsonschema import Draft202012Validator

from karst.agents.protocol import (DECLARED, DISCIPLINE_FILE, DISCIPLINE_PREFIXES, MODEL_FILE,
                                   MODES, get_research_protocol, questions_from_model,
                                   sections_from_markdown)
from karst.schema import ContractError


class SourceReadingTests(unittest.TestCase):
    """The method reads the strategy sources itself; the CLI is not in the way."""

    def test_discipline_sections_cover_six_layers_and_the_counter(self):
        sections = sections_from_markdown(DISCIPLINE_FILE.read_text(encoding='utf-8'), DISCIPLINE_PREFIXES)
        self.assertEqual(sorted(sections), sorted(DISCIPLINE_PREFIXES))
        for key, body in sections.items():
            self.assertTrue(body.strip(), key)

    def test_scenario_questions_carry_the_modules_and_the_five_checks(self):
        questions = questions_from_model(MODEL_FILE.read_text(encoding='utf-8'))
        self.assertEqual(len(questions), 8)  # three module focuses + the five narrative checks
        self.assertTrue(all(q.strip() and '|' not in q for q in questions))


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
