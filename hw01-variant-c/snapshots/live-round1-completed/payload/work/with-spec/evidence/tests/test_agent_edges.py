"""Supplemental deterministic checks for citation edge cases; STUB-only."""
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))
import agent


class CitationEdgeChecks(unittest.TestCase):
    def test_citation_uses_returned_line_numbers_not_array_positions(self):
        read = {"D01": {2, 4}}
        self.assertIsNone(agent._validate_answer_sources(
            "Text (D01:2).", True, True, read))
        self.assertIn("D01:1", agent._validate_answer_sources(
            "Text [D01:1].", True, True, read))

    def test_sparse_range_and_unclosed_candidate_are_rejected(self):
        read = {"D01": {2, 4}}
        self.assertIn("D01:3", agent._validate_answer_sources(
            "Text [D01:2-4].", True, True, read))
        self.assertIn("не закрыта", agent._validate_answer_sources(
            "Text (D01:2-4", True, True, read))

    def test_non_citation_mentions_are_not_candidates(self):
        text = "Дата (2026-10-20); D01; [D01]; (D01); обычные (скобки)."
        self.assertIsNone(agent._validate_answer_sources(text, True, False, {}))

    def test_successful_empty_search_allows_absence_without_citation(self):
        self.assertIsNone(agent._validate_answer_sources(
            "В корпусе сведения не найдены.", True, False, {}))
        self.assertIn("успешный search_docs", agent._validate_answer_sources(
            "В корпусе сведения не найдены.", False, False, {}))

    def test_successful_empty_read_is_distinct_from_unread_document(self):
        message = agent._validate_answer_sources(
            "Text [D01:1].", True, True, {"D01": set()})
        self.assertIn("не была возвращена", message)
        self.assertNotIn("не был успешно прочитан", message)

    def test_large_range_fails_without_iterating_to_range_end(self):
        message = agent._validate_answer_sources(
            "Text [D01:1-999999999].", True, True, {"D01": {1, 2}})
        self.assertIn("D01:3", message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
