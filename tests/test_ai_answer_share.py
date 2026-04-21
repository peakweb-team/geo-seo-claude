#!/usr/bin/env python3
"""
Tests for ai_answer_share.py
=============================
Validates the AI Answer Share Score calculation including position-adjusted
impression weighting.

Run with:
    python3 -m pytest tests/test_ai_answer_share.py -v
"""

import json
import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

from ai_answer_share import (
    compute_query_answer_share,
    compute_answer_share_score,
    compare_answer_share,
    _extract_citation_sequence,
    _domain_matches,
)


class TestCitationSequenceExtraction(unittest.TestCase):

    def test_basic_markers(self):
        text = "According to [1], the market is growing [2]."
        self.assertEqual(_extract_citation_sequence(text), [1, 2])

    def test_repeated_markers(self):
        text = "Source [1] says X, and [2] agrees. But [1] also notes Y."
        self.assertEqual(_extract_citation_sequence(text), [1, 2, 1])

    def test_no_markers(self):
        text = "No citations here, just plain text."
        self.assertEqual(_extract_citation_sequence(text), [])

    def test_adjacent_markers(self):
        text = "Multiple sources agree [1][2][3]."
        self.assertEqual(_extract_citation_sequence(text), [1, 2, 3])

    def test_high_numbers(self):
        text = "Source [12] and [3]."
        self.assertEqual(_extract_citation_sequence(text), [12, 3])


class TestDomainMatching(unittest.TestCase):

    def test_exact_match(self):
        self.assertTrue(_domain_matches("example.com", "https://example.com/page"))

    def test_www_stripped(self):
        self.assertTrue(_domain_matches("example.com", "https://www.example.com/page"))

    def test_no_match(self):
        self.assertFalse(_domain_matches("example.com", "https://other.com/page"))

    def test_subdomain_match(self):
        self.assertTrue(_domain_matches("example.com", "https://blog.example.com/post"))

    def test_case_insensitive(self):
        self.assertTrue(_domain_matches("Example.COM", "https://EXAMPLE.com/page"))


class TestQueryAnswerShare(unittest.TestCase):

    def test_single_citation_client_only(self):
        """Client is the only cited source — share should be 1.0."""
        result = compute_query_answer_share(
            target_domain="example.com",
            citations=["https://example.com/page1"],
            answer_text="According to [1], the product is excellent.",
        )
        self.assertAlmostEqual(result["share"], 1.0)
        self.assertEqual(result["client_citation_count"], 1)

    def test_two_citations_one_client(self):
        """Client is one of two cited sources, cited first."""
        result = compute_query_answer_share(
            target_domain="example.com",
            citations=[
                "https://example.com/page1",
                "https://competitor.com/page2",
            ],
            answer_text="According to [1], the product is excellent. However [2] disagrees.",
        )
        # Marker [1] at rank 1: weight 1/1 = 1.0 (client)
        # Marker [2] at rank 2: weight 1/2 = 0.5 (competitor)
        # Client share: 1.0 / 1.5 ≈ 0.6667
        self.assertAlmostEqual(result["share"], 0.6667, places=3)

    def test_two_citations_client_second(self):
        """Client cited second — lower share due to position weighting."""
        result = compute_query_answer_share(
            target_domain="example.com",
            citations=[
                "https://competitor.com/page1",
                "https://example.com/page2",
            ],
            answer_text="According to [1], something. Also [2] notes this.",
        )
        # Marker [1] at rank 1: weight 1.0 (competitor)
        # Marker [2] at rank 2: weight 0.5 (client)
        # Client share: 0.5 / 1.5 ≈ 0.3333
        self.assertAlmostEqual(result["share"], 0.3333, places=3)

    def test_no_citations_no_mention(self):
        """No citations and no domain mention — share is 0."""
        result = compute_query_answer_share(
            target_domain="example.com",
            citations=[],
            answer_text="Some answer without any citations.",
            domain_mentioned_in_text=False,
        )
        self.assertEqual(result["share"], 0.0)

    def test_no_citations_with_mention(self):
        """No citation markers but domain mentioned in text — small bonus."""
        result = compute_query_answer_share(
            target_domain="example.com",
            citations=[],
            answer_text="Example.com is a well-known provider in this space.",
            domain_mentioned_in_text=True,
        )
        self.assertAlmostEqual(result["share"], 0.05)

    def test_mention_bonus_not_added_when_already_cited(self):
        """Mention bonus should NOT apply when already cited via markers."""
        result = compute_query_answer_share(
            target_domain="example.com",
            citations=["https://example.com/page"],
            answer_text="According to [1], the product works.",
            domain_mentioned_in_text=True,
        )
        self.assertEqual(result["mention_bonus"], 0.0)
        self.assertAlmostEqual(result["share"], 1.0)

    def test_client_repeated_citation(self):
        """Client source cited multiple times — gets cumulative weight."""
        result = compute_query_answer_share(
            target_domain="example.com",
            citations=[
                "https://example.com/page1",
                "https://competitor.com/page2",
            ],
            answer_text="Source [1] says X. Also [2] agrees. But [1] adds more detail.",
        )
        # [1] at rank 1: weight 1.0 (client)
        # [2] at rank 2: weight 0.5 (competitor)
        # [1] at rank 3: weight 1/3 ≈ 0.333 (client)
        # Client: 1.0 + 0.333 = 1.333
        # Total: 1.0 + 0.5 + 0.333 = 1.833
        # Share: 1.333 / 1.833 ≈ 0.727
        self.assertAlmostEqual(result["share"], 0.7273, places=3)

    def test_out_of_range_citation_index(self):
        """Citation marker references index beyond citations list."""
        result = compute_query_answer_share(
            target_domain="example.com",
            citations=["https://example.com/page1"],
            answer_text="Source [1] and [5] say things.",
        )
        # [1] at rank 1: weight 1.0 (client)
        # [5] at rank 2: weight 0.5 (no URL — not counted for client)
        # Client: 1.0, Total: 1.5
        # Share: 1.0/1.5 ≈ 0.667
        self.assertAlmostEqual(result["share"], 0.6667, places=3)


class TestBasketScore(unittest.TestCase):

    def _make_query_result(self, query, citations, answer_text, domain="example.com"):
        from ai_answer_share import _domain_matches
        matching = [u for u in citations if _domain_matches(domain, u)]
        return {
            "query": query,
            "cited": len(matching) > 0,
            "matching_urls": matching,
            "total_citations": len(citations),
            "all_citations": citations,
            "answer_text": answer_text,
            "answer_preview": answer_text[:500],
            "domain_mentioned_in_text": domain.lower() in answer_text.lower(),
        }

    def test_all_cited_high_share(self):
        """All queries cite client as sole source — score should be 100."""
        results = [
            self._make_query_result(
                f"query {i}",
                ["https://example.com/page"],
                f"According to [1], answer {i}.",
            )
            for i in range(5)
        ]
        score = compute_answer_share_score("example.com", results)
        self.assertEqual(score["score"], 100)
        self.assertEqual(score["rating"], "Strong")
        self.assertEqual(score["queries_cited"], 5)

    def test_none_cited(self):
        """No queries cite client — score should be 0."""
        results = [
            self._make_query_result(
                f"query {i}",
                ["https://other.com/page"],
                f"According to [1], answer {i}.",
            )
            for i in range(5)
        ]
        score = compute_answer_share_score("example.com", results)
        self.assertEqual(score["score"], 0)
        self.assertEqual(score["rating"], "Not Visible")

    def test_mixed_basket(self):
        """Mix of cited and not cited queries."""
        results = [
            self._make_query_result(
                "cited query",
                ["https://example.com/page", "https://other.com/page"],
                "According to [1], good. Also [2] says more.",
            ),
            self._make_query_result(
                "not cited query",
                ["https://other.com/page"],
                "According to [1], answer.",
            ),
        ]
        score = compute_answer_share_score("example.com", results)
        # Query 1: client share ≈ 0.667
        # Query 2: client share = 0
        # Average: 0.333 → score 33
        self.assertEqual(score["score"], 33)
        self.assertEqual(score["queries_cited"], 1)
        self.assertAlmostEqual(score["citation_rate"], 0.5)

    def test_error_queries_excluded_from_average(self):
        """Queries with errors should not pull down the average."""
        results = [
            self._make_query_result(
                "good query",
                ["https://example.com/page"],
                "According to [1], great.",
            ),
            {"query": "bad query", "error": "timeout"},
        ]
        score = compute_answer_share_score("example.com", results)
        # Only 1 valid query with share 1.0 → score 100
        self.assertEqual(score["score"], 100)

    def test_empty_basket(self):
        score = compute_answer_share_score("example.com", [])
        self.assertEqual(score["score"], 0)
        self.assertEqual(score["query_count"], 0)


class TestAnswerShareComparison(unittest.TestCase):

    def test_improvement_detected(self):
        baseline = {
            "score": 20,
            "rating": "Weak",
            "per_query": [
                {"query": "q1", "share": 0.0, "cited": False},
                {"query": "q2", "share": 0.5, "cited": True},
            ],
        }
        current = {
            "score": 40,
            "rating": "Moderate",
            "per_query": [
                {"query": "q1", "share": 0.3, "cited": True},
                {"query": "q2", "share": 0.5, "cited": True},
            ],
        }
        result = compare_answer_share(baseline, current)
        self.assertEqual(result["score_change"], 20)
        self.assertEqual(len(result["improvements"]), 1)
        self.assertEqual(result["improvements"][0]["query"], "q1")
        self.assertEqual(len(result["unchanged"]), 1)

    def test_regression_detected(self):
        baseline = {
            "score": 50,
            "rating": "Moderate",
            "per_query": [{"query": "q1", "share": 0.8, "cited": True}],
        }
        current = {
            "score": 20,
            "rating": "Weak",
            "per_query": [{"query": "q1", "share": 0.1, "cited": True}],
        }
        result = compare_answer_share(baseline, current)
        self.assertEqual(result["score_change"], -30)
        self.assertEqual(len(result["regressions"]), 1)


class TestAnswerShareRating(unittest.TestCase):

    def test_rating_bands(self):
        from ai_answer_share import _get_answer_share_rating
        cases = [
            (75, "Strong"),
            (60, "Strong"),
            (50, "Moderate"),
            (40, "Moderate"),
            (30, "Weak"),
            (10, "Minimal"),
            (3, "Not Visible"),
            (0, "Not Visible"),
        ]
        for score_val, expected in cases:
            self.assertEqual(_get_answer_share_rating(score_val), expected,
                f"Score {score_val} should be '{expected}'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
