#!/usr/bin/env python3
"""
GEO Validation Script - Automated AI visibility testing via Perplexity API

Tests a set of queries against Perplexity and checks if the target domain
appears in the cited sources. Run before and after GEO fixes to measure impact.

Usage:
    python geo_validate.py --domain example.com --queries queries.txt --output baseline.json
    python geo_validate.py --domain example.com --queries queries.txt --baseline baseline.json --output validation.json

Environment:
    PERPLEXITY_API_KEY - Your Perplexity API key (get from https://www.perplexity.ai/settings/api)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)


PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


def query_perplexity(query: str, api_key: str) -> dict:
    """Query Perplexity API and return response with citations."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "sonar",  # sonar model includes web search + citations
        "messages": [
            {"role": "user", "content": query}
        ],
        "return_citations": True,
        "return_related_questions": False,
    }

    response = requests.post(PERPLEXITY_API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def extract_citations(response: dict) -> list[str]:
    """Extract citation URLs from Perplexity response."""
    citations = []

    # Citations are in the response under 'citations' key
    if "citations" in response:
        citations.extend(response["citations"])

    # Also check in choices[0].message if present
    choices = response.get("choices", [])
    if choices:
        message = choices[0].get("message", {})
        if "citations" in message:
            citations.extend(message["citations"])

    return citations


def domain_in_citations(domain: str, citations: list[str]) -> tuple[bool, list[str]]:
    """Check if target domain appears in any citation URLs."""
    domain = domain.lower().replace("www.", "")
    matching_urls = []

    for url in citations:
        try:
            parsed = urlparse(url)
            citation_domain = parsed.netloc.lower().replace("www.", "")
            if domain in citation_domain or citation_domain in domain:
                matching_urls.append(url)
        except Exception:
            continue

    return len(matching_urls) > 0, matching_urls


def run_validation(domain: str, queries: list[str], api_key: str) -> dict:
    """Run all queries and collect results."""
    results = {
        "domain": domain,
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(queries),
        "queries_with_citation": 0,
        "citation_rate": 0.0,
        "query_results": [],
    }

    for i, query in enumerate(queries, 1):
        print(f"  [{i}/{len(queries)}] Testing: {query[:50]}...")

        try:
            response = query_perplexity(query, api_key)
            citations = extract_citations(response)
            found, matching_urls = domain_in_citations(domain, citations)

            # Extract the response text
            answer = ""
            choices = response.get("choices", [])
            if choices:
                answer = choices[0].get("message", {}).get("content", "")

            result = {
                "query": query,
                "cited": found,
                "matching_urls": matching_urls,
                "total_citations": len(citations),
                "all_citations": citations,
                "answer_preview": answer[:500] if answer else "",
                "domain_mentioned_in_text": domain.lower() in answer.lower() if answer else False,
            }

            if found:
                results["queries_with_citation"] += 1
                print(f"      ✓ CITED - Found in {len(matching_urls)} source(s)")
            else:
                print(f"      ✗ Not cited ({len(citations)} sources checked)")

        except requests.exceptions.RequestException as e:
            result = {
                "query": query,
                "cited": False,
                "error": str(e),
            }
            print(f"      ⚠ Error: {e}")

        results["query_results"].append(result)

    # Calculate citation rate
    if results["total_queries"] > 0:
        results["citation_rate"] = results["queries_with_citation"] / results["total_queries"]

    return results


def compare_results(baseline: dict, current: dict) -> dict:
    """Compare current results against baseline."""
    comparison = {
        "domain": current["domain"],
        "baseline_date": baseline["timestamp"],
        "current_date": current["timestamp"],
        "baseline_citation_rate": baseline["citation_rate"],
        "current_citation_rate": current["citation_rate"],
        "citation_rate_change": current["citation_rate"] - baseline["citation_rate"],
        "baseline_citations": baseline["queries_with_citation"],
        "current_citations": current["queries_with_citation"],
        "total_queries": current["total_queries"],
        "improvements": [],
        "regressions": [],
        "unchanged": [],
    }

    # Build lookup for baseline results
    baseline_by_query = {r["query"]: r for r in baseline.get("query_results", [])}

    for result in current.get("query_results", []):
        query = result["query"]
        baseline_result = baseline_by_query.get(query, {})

        was_cited = baseline_result.get("cited", False)
        is_cited = result.get("cited", False)

        if not was_cited and is_cited:
            comparison["improvements"].append(query)
        elif was_cited and not is_cited:
            comparison["regressions"].append(query)
        else:
            comparison["unchanged"].append(query)

    return comparison


def generate_report(comparison: dict) -> str:
    """Generate a markdown report from comparison data."""
    rate_change = comparison["citation_rate_change"] * 100
    direction = "↑" if rate_change > 0 else "↓" if rate_change < 0 else "→"

    report = f"""# GEO Validation Report: {comparison["domain"]}

**Baseline:** {comparison["baseline_date"]}
**Current:** {comparison["current_date"]}

## Summary

| Metric | Baseline | Current | Change |
|--------|----------|---------|--------|
| Citation Rate | {comparison["baseline_citation_rate"]*100:.1f}% | {comparison["current_citation_rate"]*100:.1f}% | {direction} {abs(rate_change):.1f}% |
| Queries Cited | {comparison["baseline_citations"]}/{comparison["total_queries"]} | {comparison["current_citations"]}/{comparison["total_queries"]} | {comparison["current_citations"] - comparison["baseline_citations"]:+d} |

## Changes

### Improvements ({len(comparison["improvements"])} queries now cited)
"""

    if comparison["improvements"]:
        for q in comparison["improvements"]:
            report += f"- ✓ `{q}`\n"
    else:
        report += "_None_\n"

    report += f"""
### Regressions ({len(comparison["regressions"])} queries no longer cited)
"""

    if comparison["regressions"]:
        for q in comparison["regressions"]:
            report += f"- ✗ `{q}`\n"
    else:
        report += "_None_\n"

    report += f"""
### Unchanged ({len(comparison["unchanged"])} queries)
"""

    cited_unchanged = [q for q in comparison["unchanged"]
                       if any(r["query"] == q and r.get("cited")
                              for r in [])]  # Would need current results

    report += f"_{len(comparison['unchanged'])} queries with no change in citation status_\n"

    return report


def load_queries(filepath: str) -> list[str]:
    """Load queries from a text file (one per line)."""
    with open(filepath, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def main():
    parser = argparse.ArgumentParser(description="GEO Validation - Test AI visibility via Perplexity")
    parser.add_argument("--domain", required=True, help="Target domain to check for (e.g., example.com)")
    parser.add_argument("--queries", required=True, help="Path to queries file (one query per line)")
    parser.add_argument("--output", required=True, help="Output JSON file for results")
    parser.add_argument("--baseline", help="Previous baseline JSON to compare against")
    parser.add_argument("--report", help="Output markdown report file (when comparing)")

    args = parser.parse_args()

    # Check for API key
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        print("Error: PERPLEXITY_API_KEY environment variable not set")
        print("Get your API key from: https://www.perplexity.ai/settings/api")
        sys.exit(1)

    # Load queries
    queries = load_queries(args.queries)
    print(f"Loaded {len(queries)} queries from {args.queries}")

    # Run validation
    print(f"\nTesting AI visibility for: {args.domain}")
    print("-" * 50)

    results = run_validation(args.domain, queries, api_key)

    # Save results
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {args.output}")

    # Print summary
    print(f"\n{'='*50}")
    print(f"SUMMARY: {args.domain}")
    print(f"{'='*50}")
    print(f"Queries tested: {results['total_queries']}")
    print(f"Queries with citation: {results['queries_with_citation']}")
    print(f"Citation rate: {results['citation_rate']*100:.1f}%")

    # Compare with baseline if provided
    if args.baseline:
        with open(args.baseline, "r") as f:
            baseline = json.load(f)

        comparison = compare_results(baseline, results)

        print(f"\nCOMPARISON TO BASELINE:")
        print(f"  Baseline citation rate: {comparison['baseline_citation_rate']*100:.1f}%")
        print(f"  Current citation rate:  {comparison['current_citation_rate']*100:.1f}%")
        print(f"  Change: {comparison['citation_rate_change']*100:+.1f}%")
        print(f"  Improvements: {len(comparison['improvements'])}")
        print(f"  Regressions: {len(comparison['regressions'])}")

        # Generate report if requested
        report_path = args.report or args.output.replace(".json", "-report.md")
        report = generate_report(comparison)
        with open(report_path, "w") as f:
            f.write(report)
        print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
