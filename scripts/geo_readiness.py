#!/usr/bin/env python3
"""
GEO Readiness Score
===================
Computes a single 0-100 site-level readiness score from six audit categories.

This is the first of two topline scores in the revised GEO scoring system:
  1. GEO Readiness Score  — "How prepared is the site to be cited by AI systems?"
  2. AI Answer Share Score — "How much of AI's answers does this business actually own?"

The GEO Readiness Score preserves the existing Peakweb audit framework. It is a
weighted composite of six category scores, each 0-100, rolled up into a single
number that is easy to explain to customers.

Usage:
    from geo_readiness import compute_geo_readiness_score

    score = compute_geo_readiness_score({
        "ai_citability": 65,
        "brand_authority": 40,
        "content_eeat": 55,
        "technical": 72,
        "schema": 30,
        "platform_optimization": 45,
    })
    # score => {"total": 52, "rating": "Poor", "categories": {...}}
"""

import json
import sys

# ---------------------------------------------------------------------------
# Category weights — these define the composite formula
# ---------------------------------------------------------------------------

CATEGORY_WEIGHTS = {
    "ai_citability":        0.25,
    "brand_authority":      0.20,
    "content_eeat":         0.20,
    "technical":            0.15,
    "schema":               0.10,
    "platform_optimization": 0.10,
}

# ---------------------------------------------------------------------------
# Rating bands
# ---------------------------------------------------------------------------

RATING_BANDS = [
    (90, 100, "Excellent"),
    (75, 89,  "Good"),
    (60, 74,  "Fair"),
    (40, 59,  "Poor"),
    (0,  39,  "Critical"),
]


def _get_rating(score: int) -> str:
    for lo, hi, label in RATING_BANDS:
        if lo <= score <= hi:
            return label
    return "Unknown"


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def compute_geo_readiness_score(category_scores: dict) -> dict:
    """
    Compute the GEO Readiness Score from six category scores.

    Args:
        category_scores: Dict with keys matching CATEGORY_WEIGHTS.
            Each value should be 0-100. Missing keys default to 50.

    Returns:
        Dict with:
            total:      int 0-100 composite score
            rating:     str label (Excellent / Good / Fair / Poor / Critical)
            categories: dict of {category: {score, weight, weighted}} for each category
    """
    categories = {}
    weighted_sum = 0.0

    for category, weight in CATEGORY_WEIGHTS.items():
        raw = category_scores.get(category, 50)
        raw = max(0, min(100, int(raw)))
        weighted = round(raw * weight, 2)
        weighted_sum += weighted
        categories[category] = {
            "score": raw,
            "weight": weight,
            "weighted": weighted,
        }

    total = round(weighted_sum)
    total = max(0, min(100, total))

    return {
        "total": total,
        "rating": _get_rating(total),
        "categories": categories,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python geo_readiness.py '<json category scores>'")
        print('Example: python geo_readiness.py \'{"ai_citability":65,"brand_authority":40,"content_eeat":55,"technical":72,"schema":30,"platform_optimization":45}\'')
        sys.exit(1)

    scores = json.loads(sys.argv[1])
    result = compute_geo_readiness_score(scores)
    print(json.dumps(result, indent=2))
