#!/usr/bin/env python3
"""
Tests for geo_readiness.py
==========================
Validates the GEO Readiness Score composite calculation.

Run with:
    python3 -m pytest tests/test_geo_readiness.py -v
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

from geo_readiness import compute_geo_readiness_score, CATEGORY_WEIGHTS


class TestGeoReadinessScore(unittest.TestCase):

    def test_perfect_scores_yield_100(self):
        scores = {k: 100 for k in CATEGORY_WEIGHTS}
        result = compute_geo_readiness_score(scores)
        self.assertEqual(result["total"], 100)
        self.assertEqual(result["rating"], "Excellent")

    def test_zero_scores_yield_0(self):
        scores = {k: 0 for k in CATEGORY_WEIGHTS}
        result = compute_geo_readiness_score(scores)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["rating"], "Critical")

    def test_known_composite(self):
        """Verify hand-calculated composite score."""
        scores = {
            "ai_citability": 60,       # 60 * 0.25 = 15.0
            "brand_authority": 40,     # 40 * 0.20 = 8.0
            "content_eeat": 50,        # 50 * 0.20 = 10.0
            "technical": 80,           # 80 * 0.15 = 12.0
            "schema": 30,             # 30 * 0.10 = 3.0
            "platform_optimization": 20,  # 20 * 0.10 = 2.0
        }
        # Expected: 15 + 8 + 10 + 12 + 3 + 2 = 50
        result = compute_geo_readiness_score(scores)
        self.assertEqual(result["total"], 50)
        self.assertEqual(result["rating"], "Poor")

    def test_missing_keys_default_to_50(self):
        result = compute_geo_readiness_score({})
        # All default to 50: 50 * (0.25+0.20+0.20+0.15+0.10+0.10) = 50 * 1.0 = 50
        self.assertEqual(result["total"], 50)

    def test_partial_keys_fill_defaults(self):
        result = compute_geo_readiness_score({"ai_citability": 100})
        # ai_citability: 100*0.25=25, rest: 50*0.75=37.5, total=62.5 -> 62
        self.assertEqual(result["total"], 62)

    def test_categories_in_output(self):
        scores = {k: 70 for k in CATEGORY_WEIGHTS}
        result = compute_geo_readiness_score(scores)
        self.assertIn("categories", result)
        for key in CATEGORY_WEIGHTS:
            self.assertIn(key, result["categories"])
            self.assertEqual(result["categories"][key]["score"], 70)

    def test_weights_sum_to_1(self):
        total_weight = sum(CATEGORY_WEIGHTS.values())
        self.assertAlmostEqual(total_weight, 1.0, places=5)

    def test_rating_bands(self):
        cases = [
            (95, "Excellent"),
            (80, "Good"),
            (65, "Fair"),
            (45, "Poor"),
            (20, "Critical"),
        ]
        for score_val, expected_rating in cases:
            scores = {k: score_val for k in CATEGORY_WEIGHTS}
            result = compute_geo_readiness_score(scores)
            self.assertEqual(result["rating"], expected_rating,
                f"Score {score_val} should be '{expected_rating}', got '{result['rating']}'")

    def test_clamped_to_0_100(self):
        # Scores above 100 should be clamped
        scores = {k: 150 for k in CATEGORY_WEIGHTS}
        result = compute_geo_readiness_score(scores)
        self.assertEqual(result["total"], 100)

        # Negative scores should be clamped
        scores = {k: -10 for k in CATEGORY_WEIGHTS}
        result = compute_geo_readiness_score(scores)
        self.assertEqual(result["total"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
