#!/usr/bin/env python3
"""
Phase 0 evidence collector for GEO audits.

Fetches key pages via curl, extracts JSON-LD schema blocks, measures
body text, and parses robots.txt. Produces verified ground-truth facts
that are injected into subagent prompts to prevent hallucination.

Usage:
    python3 scripts/collect_evidence.py https://example.com
    python3 scripts/collect_evidence.py https://example.com --output evidence.json
    python3 scripts/collect_evidence.py https://example.com --markdown  # print markdown block only
"""

import argparse
import json
import re
import subprocess
import sys
from urllib.parse import urljoin, urlparse


def curl_fetch(url, timeout=20):
    """Fetch a URL via curl, returning (status_code, headers_str, body_str)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-D", "-", "--max-time", str(timeout),
             "-A", "Mozilla/5.0 (compatible; GEOAudit/1.0)", url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        raw = result.stdout
        # Split headers from body at the first blank line
        if "\r\n\r\n" in raw:
            headers_part, body = raw.split("\r\n\r\n", 1)
        elif "\n\n" in raw:
            headers_part, body = raw.split("\n\n", 1)
        else:
            headers_part, body = "", raw

        # Extract status code from first header line
        status_line = headers_part.strip().split("\n")[0]
        status_match = re.search(r"HTTP/\S+ (\d+)", status_line)
        status_code = int(status_match.group(1)) if status_match else 0

        return status_code, headers_part, body
    except Exception as e:
        return 0, "", f"ERROR: {e}"


def extract_jsonld_blocks(html):
    """Extract all JSON-LD script blocks from HTML. Returns list of dicts."""
    pattern = r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
    blocks = []
    for m in matches:
        try:
            data = json.loads(m.strip())
            blocks.append(data)
        except json.JSONDecodeError:
            blocks.append({"@type": "PARSE_ERROR", "raw": m.strip()[:200]})
    return blocks


def get_schema_types(blocks):
    """Extract @type values from a list of JSON-LD blocks."""
    types = []
    for block in blocks:
        t = block.get("@type")
        if isinstance(t, list):
            types.extend(t)
        elif isinstance(t, str):
            types.append(t)
    return types


def measure_body_text(html):
    """Strip tags and measure approximate body text length."""
    # Remove script and style blocks entirely
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    # Remove remaining HTML tags
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
    # Collapse whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return len(cleaned), len(cleaned.split())


def extract_headings(html):
    """Find H1–H3 tags in raw HTML (server-rendered only)."""
    headings = {}
    for level in [1, 2, 3]:
        pattern = rf'<h{level}[^>]*>(.*?)</h{level}>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        # Strip inner tags
        cleaned = [re.sub(r'<[^>]+>', '', m).strip() for m in matches]
        headings[f"h{level}"] = cleaned[:5]  # cap at 5 per level
    return headings


def parse_robots(body, domain):
    """Parse robots.txt for AI crawler directives and sitemap URLs."""
    ai_crawlers = [
        "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot",
        "PerplexityBot", "Amazonbot", "Google-Extended", "Bytespider",
        "CCBot", "Applebot-Extended", "FacebookBot", "Cohere-ai"
    ]

    # Find sitemap URLs
    sitemaps = re.findall(r'(?i)^Sitemap:\s*(.+)$', body, re.MULTILINE)
    sitemaps = [s.strip() for s in sitemaps]

    # Parse into user-agent blocks
    crawler_status = {}
    lines = body.splitlines()
    current_agents = []
    disallows = {}
    allows = {}

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.lower().startswith('user-agent:'):
            current_agents = [line.split(':', 1)[1].strip()]
        elif line.lower().startswith('disallow:') and current_agents:
            path = line.split(':', 1)[1].strip()
            for agent in current_agents:
                disallows.setdefault(agent, []).append(path)
        elif line.lower().startswith('allow:') and current_agents:
            path = line.split(':', 1)[1].strip()
            for agent in current_agents:
                allows.setdefault(agent, []).append(path)

    # Global wildcard rules
    global_disallows = disallows.get('*', [])

    for crawler in ai_crawlers:
        # Check for explicit block
        crawler_disallows = disallows.get(crawler, [])
        if '/' in crawler_disallows:
            status = "Blocked"
        elif crawler_disallows:
            status = "Restricted"
        elif crawler in disallows:
            status = "Restricted"
        else:
            # Inherits global rules; check if global blocks root
            if '/' in global_disallows:
                status = "Blocked (via *)"
            else:
                status = "Allowed (inherits *)"
        crawler_status[crawler] = status

    return {
        "sitemaps": sitemaps,
        "crawler_status": crawler_status,
        "global_disallows": global_disallows[:10],
    }


def collect_page_evidence(url, label):
    """Collect all evidence for a single page URL."""
    status, headers, body = curl_fetch(url)
    if not body or status == 0:
        return {"url": url, "label": label, "status": status, "error": "Fetch failed"}

    jsonld_blocks = extract_jsonld_blocks(body)
    schema_types = get_schema_types(jsonld_blocks)
    char_count = len(body)
    text_chars, word_count = measure_body_text(body)
    headings = extract_headings(body)

    return {
        "url": url,
        "label": label,
        "status": status,
        "raw_html_chars": char_count,
        "body_text_chars": text_chars,
        "body_text_words": word_count,
        "schema_types": schema_types,
        "schema_block_count": len(jsonld_blocks),
        "headings": headings,
        "ssr_assessment": assess_ssr(body, text_chars, schema_types),
    }


def assess_ssr(html, text_chars, schema_types):
    """Quick SSR signal assessment."""
    has_react_root = bool(re.search(r'<div[^>]+id=["\'](?:root|app)["\'][^>]*>\s*</div>', html))
    has_next_data = '__NEXT_DATA__' in html
    has_nuxt_data = '__NUXT__' in html or '__NUXT_DATA__' in html

    if text_chars > 5000:
        return "Server-rendered (substantial text in raw HTML)"
    elif text_chars > 1000:
        return "Partially server-rendered (some text present)"
    elif has_next_data or has_nuxt_data:
        return "SSR framework detected (Next.js/Nuxt) but low visible text"
    elif has_react_root and text_chars < 500:
        return "Client-side rendered (empty root div, minimal text)"
    else:
        return f"Minimal text ({text_chars} chars) — verify manually"


def discover_key_pages(domain_url, robots_body):
    """Find key page URLs to sample: homepage, about, FAQ, blog post, PDP, collection."""
    base = domain_url.rstrip('/')
    parsed = urlparse(base)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    # Try to get sitemap for smarter page discovery
    pages = [
        {"url": base + "/", "label": "Homepage"},
        {"url": base + "/pages/about", "label": "About"},
        {"url": base + "/pages/faq", "label": "FAQ"},
        {"url": base + "/about", "label": "About (alt)"},
        {"url": base + "/faq", "label": "FAQ (alt)"},
    ]

    # Pull sitemap URLs for product/collection/blog samples
    sitemap_urls = re.findall(r'(?i)^Sitemap:\s*(.+)$', robots_body, re.MULTILINE)
    for sitemap_url in sitemap_urls[:1]:
        sitemap_url = sitemap_url.strip()
        status, _, sitemap_body = curl_fetch(sitemap_url, timeout=15)
        if status == 200 and sitemap_body:
            # Find child sitemaps
            child_sitemaps = re.findall(r'<loc>(.*?)</loc>', sitemap_body)
            for child in child_sitemaps:
                child = child.strip()
                if 'product' in child.lower():
                    _, _, child_body = curl_fetch(child, timeout=15)
                    if child_body:
                        product_urls = re.findall(r'<loc>(.*?)</loc>', child_body)
                        if product_urls:
                            pages.append({"url": product_urls[0].strip(), "label": "Product PDP (sample)"})
                elif 'collection' in child.lower():
                    _, _, child_body = curl_fetch(child, timeout=15)
                    if child_body:
                        collection_urls = re.findall(r'<loc>(.*?)</loc>', child_body)
                        if collection_urls:
                            pages.append({"url": collection_urls[0].strip(), "label": "Collection (sample)"})
                elif 'blog' in child.lower() or 'post' in child.lower() or 'article' in child.lower():
                    _, _, child_body = curl_fetch(child, timeout=15)
                    if child_body:
                        blog_urls = re.findall(r'<loc>(.*?)</loc>', child_body)
                        if blog_urls:
                            pages.append({"url": blog_urls[0].strip(), "label": "Blog post (sample)"})

    # Deduplicate by URL
    seen = set()
    unique = []
    for p in pages:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique.append(p)

    return unique


def render_markdown(evidence):
    """Render evidence as a markdown block for injection into subagent prompts."""
    lines = []
    lines.append("## VERIFIED EVIDENCE — Collected via curl (treat as ground truth)")
    lines.append("")
    lines.append("> This evidence was collected by the orchestrator via direct curl requests")
    lines.append("> before subagent launch. **Do NOT contradict these findings based on")
    lines.append("> WebFetch results or assumptions. Use WebFetch only for content you")
    lines.append("> cannot extract from this evidence block.**")
    lines.append("")

    # SSR / body text table
    lines.append("### Server-Side Rendering & Body Text")
    lines.append("")
    lines.append("| Page | Status | Raw HTML | Body Text | Schema Types Found |")
    lines.append("|---|---|---|---|---|")
    for p in evidence["pages"]:
        if "error" in p:
            lines.append(f"| {p['label']} | {p['status']} (error) | — | — | — |")
            continue
        schema_str = ", ".join(p["schema_types"]) if p["schema_types"] else "None"
        lines.append(
            f"| {p['label']} | {p['status']} | "
            f"{p['raw_html_chars']:,} chars | "
            f"~{p['body_text_words']:,} words | "
            f"{schema_str} |"
        )
    lines.append("")

    # SSR assessment per page
    lines.append("### SSR Assessment")
    lines.append("")
    for p in evidence["pages"]:
        if "error" not in p:
            lines.append(f"- **{p['label']}** (`{p['url']}`): {p['ssr_assessment']}")
    lines.append("")

    # Schema blocks detail
    lines.append("### Schema Blocks by Page")
    lines.append("")
    for p in evidence["pages"]:
        if "error" in p or not p.get("schema_types"):
            continue
        lines.append(f"**{p['label']}** — {p['schema_block_count']} JSON-LD block(s): {', '.join(p['schema_types'])}")
    lines.append("")

    # Headings
    lines.append("### Server-Rendered Headings (H1)")
    lines.append("")
    for p in evidence["pages"]:
        if "error" in p:
            continue
        h1s = p.get("headings", {}).get("h1", [])
        if h1s:
            lines.append(f"- **{p['label']}**: {' | '.join(h1s)}")
        else:
            lines.append(f"- **{p['label']}**: (no H1 found in server-rendered HTML)")
    lines.append("")

    # Robots.txt
    robots = evidence.get("robots", {})
    lines.append("### robots.txt Summary")
    lines.append("")
    if robots.get("sitemaps"):
        lines.append(f"**Sitemaps:** {', '.join(robots['sitemaps'])}")
    else:
        lines.append("**Sitemaps:** None found in robots.txt")
    lines.append("")
    lines.append("**AI Crawler Access:**")
    lines.append("")
    lines.append("| Crawler | Status |")
    lines.append("|---|---|")
    for crawler, status in robots.get("crawler_status", {}).items():
        lines.append(f"| {crawler} | {status} |")
    lines.append("")
    if robots.get("global_disallows"):
        lines.append(f"**Global Disallow rules (User-agent: \\*):** `{'`, `'.join(robots['global_disallows'])}`")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Collect GEO audit evidence via curl")
    parser.add_argument("url", help="Target URL to audit (e.g. https://example.com)")
    parser.add_argument("--output", help="Save JSON evidence to this file path")
    parser.add_argument("--markdown", action="store_true", help="Print markdown block only")
    args = parser.parse_args()

    url = args.url.rstrip('/')
    parsed = urlparse(url)
    domain = parsed.netloc

    print(f"[Phase 0] Collecting curl evidence for {domain}...", file=sys.stderr)

    # Fetch robots.txt
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    print(f"  Fetching robots.txt...", file=sys.stderr)
    robots_status, _, robots_body = curl_fetch(robots_url, timeout=15)
    robots_evidence = parse_robots(robots_body if robots_status == 200 else "", domain)
    robots_evidence["status"] = robots_status

    # Discover key pages
    print(f"  Discovering key pages from sitemap...", file=sys.stderr)
    key_pages = discover_key_pages(url, robots_body if robots_status == 200 else "")

    # Collect evidence for each page (skip 404s after checking)
    page_evidence = []
    seen_labels = set()
    for page in key_pages:
        label = page["label"]
        # Skip duplicate alt-path checks if we already have a good result for this type
        base_label = label.replace(" (alt)", "")
        if base_label in seen_labels:
            continue

        print(f"  Fetching {label}: {page['url']}...", file=sys.stderr)
        ev = collect_page_evidence(page["url"], label)

        if ev.get("status") == 200:
            seen_labels.add(base_label)
            seen_labels.add(label)
            page_evidence.append(ev)
        elif "(alt)" not in label:
            # Include failed non-alt fetches so agents know to look elsewhere
            page_evidence.append(ev)

    evidence = {
        "domain": domain,
        "target_url": url,
        "robots": robots_evidence,
        "pages": page_evidence,
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(evidence, f, indent=2)
        print(f"  Evidence saved to {args.output}", file=sys.stderr)

    if args.markdown:
        print(render_markdown(evidence))
    else:
        # Default: print both JSON and markdown
        if not args.output:
            print(json.dumps(evidence, indent=2))

    return evidence


if __name__ == "__main__":
    main()
