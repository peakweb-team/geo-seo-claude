#!/usr/bin/env python3
"""
AI Answer Share Score
=====================
Computes a single 0-100 score measuring how much of AI-generated answers
is attributable to a client's domain across a basket of test prompts.

This is the second of two topline scores in the revised GEO scoring system:
  1. GEO Readiness Score  — "How prepared is the site to be cited by AI systems?"
  2. AI Answer Share Score — "How much of AI's answers does this business actually own?"

Design is inspired by the Princeton GEO paper's key insight: measure *visibility
inside generated answers*, not just citation presence. The paper introduces
position-adjusted impression, where citations appearing earlier in the answer
are weighted more heavily.

Scoring method
--------------
For each query in the prompt basket, we compute a per-query answer share:

  1. Parse the answer text for inline citation markers (e.g. [1], [2]).
  2. Map each marker to its source URL via the citations list.
  3. For each citation occurrence, compute a position weight:
         weight_i = 1 / rank_i
     where rank_i is the 1-based position of the citation marker in the
     sequence of all citation markers in the answer (first marker = rank 1).
  4. Sum the position-weighted impressions for the client domain and divide
     by the total position-weighted impressions across all sources:
         query_share = sum(client_weights) / sum(all_weights)
  5. Also check for domain mentions in the answer text (unlinked mentions),
     which contribute a small bonus.

The final AI Answer Share Score is the average query_share across all queries
in the basket, scaled to 0-100.

Input format
------------
This module expects the JSON output from geo_validate.py (the Perplexity
validation results), which contains per-query results with:
  - query: str
  - cited: bool
  - all_citations: list[str]   (ordered list of source URLs)
  - answer_preview: str        (the answer text, may contain [1], [2] markers)
  - domain_mentioned_in_text: bool

Usage:
    from ai_answer_share import compute_answer_share_score

    with open("perplexity-baseline.json") as f:
        results = json.load(f)
    score = compute_answer_share_score("example.com", results["query_results"])
"""

import json
import re
import sys
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Position-adjusted impression calculation
# ---------------------------------------------------------------------------

def _normalise_domain(domain: str) -> str:
    """Strip www. and lowercase."""
    return domain.lower().replace("www.", "")


def _domain_matches(target: str, url: str) -> bool:
    """Check if a URL belongs to the target domain."""
    target = _normalise_domain(target)
    try:
        parsed = urlparse(url)
        host = _normalise_domain(parsed.netloc)
        return target in host or host in target
    except Exception:
        return False


def _extract_citation_sequence(answer_text: str) -> list[int]:
    """
    Extract the ordered sequence of citation markers from answer text.

    Perplexity answers use [1], [2], etc. to reference sources.
    Returns a list of 1-based citation indices in the order they appear.

    Example:
        "According to [1], the market is growing [2][1]."
        => [1, 2, 1]
    """
    return [int(m) for m in re.findall(r"\[(\d+)\]", answer_text)]


def compute_query_answer_share(
    target_domain: str,
    citations: list[str],
    answer_text: str,
    domain_mentioned_in_text: bool = False,
) -> dict:
    """
    Compute the position-adjusted answer share for a single query.

    Args:
        target_domain: The client domain (e.g. "example.com")
        citations: Ordered list of source URLs from the API response.
                   Index 0 = citation [1], index 1 = citation [2], etc.
        answer_text: The generated answer text with [N] citation markers.
        domain_mentioned_in_text: Whether the domain name appears in the text.

    Returns:
        Dict with:
            share:              float 0.0-1.0, the position-adjusted answer share
            total_impressions:   float, sum of all position weights
            client_impressions:  float, sum of client's position weights
            citation_count:      int, total citation markers in answer
            client_citation_count: int, client domain citation markers
            mention_bonus:       float, small bonus for unlinked domain mention
    """
    marker_sequence = _extract_citation_sequence(answer_text)

    if not marker_sequence:
        # No citation markers found — check for domain mention only
        mention_bonus = 0.05 if domain_mentioned_in_text else 0.0
        return {
            "share": mention_bonus,
            "total_impressions": 0.0,
            "client_impressions": 0.0,
            "citation_count": 0,
            "client_citation_count": 0,
            "mention_bonus": mention_bonus,
        }

    total_impressions = 0.0
    client_impressions = 0.0
    client_citation_count = 0

    for rank, citation_index in enumerate(marker_sequence, start=1):
        # Position weight: earlier citations get more weight
        weight = 1.0 / rank

        total_impressions += weight

        # Map citation marker to URL (markers are 1-based, list is 0-based)
        url_index = citation_index - 1
        if 0 <= url_index < len(citations):
            url = citations[url_index]
            if _domain_matches(target_domain, url):
                client_impressions += weight
                client_citation_count += 1

    # Mention bonus: small credit for being named in the answer even
    # beyond citation markers (e.g. "Company X is known for...")
    mention_bonus = 0.0
    if domain_mentioned_in_text and client_citation_count == 0:
        mention_bonus = 0.05

    share = 0.0
    if total_impressions > 0:
        share = client_impressions / total_impressions

    share = min(1.0, share + mention_bonus)

    return {
        "share": round(share, 4),
        "total_impressions": round(total_impressions, 4),
        "client_impressions": round(client_impressions, 4),
        "citation_count": len(marker_sequence),
        "client_citation_count": client_citation_count,
        "mention_bonus": mention_bonus,
    }


# ---------------------------------------------------------------------------
# Basket-level score
# ---------------------------------------------------------------------------

def compute_answer_share_score(
    target_domain: str,
    query_results: list[dict],
) -> dict:
    """
    Compute the AI Answer Share Score across a basket of query results.

    Args:
        target_domain: The client domain.
        query_results: List of per-query result dicts from geo_validate.py.

    Returns:
        Dict with:
            score:           int 0-100, the final AI Answer Share Score
            rating:          str label
            query_count:     int, number of queries in basket
            queries_cited:   int, number of queries where domain was cited
            citation_rate:   float 0.0-1.0, fraction of queries with any citation
            avg_share:       float 0.0-1.0, average position-adjusted share
            per_query:       list of per-query detail dicts
    """
    per_query = []

    for qr in query_results:
        if "error" in qr:
            per_query.append({
                "query": qr.get("query", ""),
                "share": 0.0,
                "error": qr["error"],
            })
            continue

        # Prefer full answer_text (new runs) over truncated answer_preview (old baselines)
        answer = qr.get("answer_text") or qr.get("answer_preview", "")

        detail = compute_query_answer_share(
            target_domain=target_domain,
            citations=qr.get("all_citations", []),
            answer_text=answer,
            domain_mentioned_in_text=qr.get("domain_mentioned_in_text", False),
        )
        detail["query"] = qr.get("query", "")
        detail["cited"] = qr.get("cited", False)
        per_query.append(detail)

    # Average share across all queries
    valid_shares = [pq["share"] for pq in per_query if "error" not in pq]
    avg_share = sum(valid_shares) / len(valid_shares) if valid_shares else 0.0

    # Scale to 0-100
    score = round(avg_share * 100)
    score = max(0, min(100, score))

    queries_cited = sum(1 for pq in per_query if pq.get("cited", False))
    query_count = len(query_results)
    citation_rate = queries_cited / query_count if query_count > 0 else 0.0

    return {
        "score": score,
        "rating": _get_answer_share_rating(score),
        "query_count": query_count,
        "queries_cited": queries_cited,
        "citation_rate": round(citation_rate, 4),
        "avg_share": round(avg_share, 4),
        "per_query": per_query,
    }


def _get_answer_share_rating(score: int) -> str:
    """Rating label for the AI Answer Share Score."""
    if score >= 60:
        return "Strong"
    elif score >= 40:
        return "Moderate"
    elif score >= 20:
        return "Weak"
    elif score >= 5:
        return "Minimal"
    else:
        return "Not Visible"


# ---------------------------------------------------------------------------
# Comparison between two runs
# ---------------------------------------------------------------------------

def compare_answer_share(baseline: dict, current: dict) -> dict:
    """
    Compare two AI Answer Share Score results.

    Args:
        baseline: Result dict from a previous compute_answer_share_score() call.
        current: Result dict from the current run.

    Returns:
        Dict with score change, per-query improvements/regressions.
    """
    score_change = current["score"] - baseline["score"]

    baseline_by_query = {pq["query"]: pq for pq in baseline.get("per_query", [])}
    improvements = []
    regressions = []
    unchanged = []

    for pq in current.get("per_query", []):
        query = pq["query"]
        bp = baseline_by_query.get(query)
        if bp is None:
            continue

        old_share = bp.get("share", 0.0)
        new_share = pq.get("share", 0.0)
        delta = new_share - old_share

        entry = {"query": query, "old_share": old_share, "new_share": new_share, "delta": round(delta, 4)}

        if delta > 0.01:
            improvements.append(entry)
        elif delta < -0.01:
            regressions.append(entry)
        else:
            unchanged.append(entry)

    return {
        "baseline_score": baseline["score"],
        "current_score": current["score"],
        "score_change": score_change,
        "baseline_rating": baseline["rating"],
        "current_rating": current["rating"],
        "improvements": sorted(improvements, key=lambda x: -x["delta"]),
        "regressions": sorted(regressions, key=lambda x: x["delta"]),
        "unchanged": unchanged,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ai_answer_share.py <domain> <perplexity-results.json>")
        print("Reads the output of geo_validate.py and computes the AI Answer Share Score.")
        sys.exit(1)

    domain = sys.argv[1]
    with open(sys.argv[2], "r") as f:
        data = json.load(f)

    result = compute_answer_share_score(domain, data.get("query_results", []))
    print(json.dumps(result, indent=2))
