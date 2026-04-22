#!/usr/bin/env python3
"""
Phase 0 evidence collector for GEO audits.

Fetches key pages via curl and extracts everything agents need to score:
- Full JSON-LD blocks (complete content, not just type names)
- Body text word counts (SSR verification)
- Meta tags (title, description, canonical, OG tags)
- robots.txt AI crawler directives

Agents receive this pre-collected data and score from it directly.
They should NEVER use WebFetch or curl for anything covered here.

Usage:
    python3 scripts/collect_evidence.py https://example.com
    python3 scripts/collect_evidence.py https://example.com --output evidence.json
    python3 scripts/collect_evidence.py https://example.com --markdown
"""

import argparse
import json
import re
import subprocess
import sys
from urllib.parse import urlparse


def curl_fetch(url, timeout=20):
    """Fetch a URL via curl, returning (status_code, headers_str, body_str)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-D", "-", "--max-time", str(timeout),
             "-A", "Mozilla/5.0 (compatible; GEOAudit/1.0)", url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        raw = result.stdout
        if "\r\n\r\n" in raw:
            headers_part, body = raw.split("\r\n\r\n", 1)
        elif "\n\n" in raw:
            headers_part, body = raw.split("\n\n", 1)
        else:
            headers_part, body = "", raw

        status_line = headers_part.strip().split("\n")[0]
        status_match = re.search(r"HTTP/\S+ (\d+)", status_line)
        status_code = int(status_match.group(1)) if status_match else 0

        return status_code, headers_part, body
    except Exception as e:
        return 0, "", f"ERROR: {e}"


def extract_jsonld_blocks(html):
    """Extract all JSON-LD script blocks from HTML. Returns list of parsed dicts."""
    pattern = r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
    blocks = []
    for m in matches:
        try:
            data = json.loads(m.strip())
            blocks.append(data)
        except json.JSONDecodeError:
            blocks.append({"@type": "PARSE_ERROR", "raw": m.strip()[:300]})
    return blocks


def extract_meta_tags(html):
    """Extract key meta tags from HTML."""
    meta = {}

    # Title tag
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
    meta["title"] = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else None

    # Meta name tags
    for name in ["description", "robots", "viewport"]:
        m = re.search(
            rf'<meta[^>]+name=["\']?{name}["\']?[^>]+content=["\']([^"\']*)["\']',
            html, re.IGNORECASE
        ) or re.search(
            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']?{name}["\']?',
            html, re.IGNORECASE
        )
        meta[name] = m.group(1).strip() if m else None

    # Canonical
    canon = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    meta["canonical"] = canon.group(1).strip() if canon else None

    # Open Graph tags
    for og in ["og:title", "og:description", "og:image", "og:type", "og:url"]:
        m = re.search(
            rf'<meta[^>]+property=["\']?{re.escape(og)}["\']?[^>]+content=["\']([^"\']*)["\']',
            html, re.IGNORECASE
        ) or re.search(
            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']?{re.escape(og)}["\']?',
            html, re.IGNORECASE
        )
        key = og.replace(":", "_")
        meta[key] = m.group(1).strip() if m else None

    # Twitter card
    tc = re.search(
        r'<meta[^>]+name=["\']?twitter:card["\']?[^>]+content=["\']([^"\']*)["\']',
        html, re.IGNORECASE
    )
    meta["twitter_card"] = tc.group(1).strip() if tc else None

    return meta


def measure_body_text(html):
    """Strip tags and measure approximate visible text."""
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return len(cleaned), len(cleaned.split())


def extract_headings(html):
    """Find H1–H2 tags in raw HTML."""
    headings = {}
    for level in [1, 2]:
        pattern = rf'<h{level}[^>]*>(.*?)</h{level}>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        cleaned = [re.sub(r'<[^>]+>', '', m).strip() for m in matches]
        headings[f"h{level}"] = [h for h in cleaned if h][:5]
    return headings


def assess_ssr(text_chars, html):
    """Classify rendering approach from body text size and HTML signals."""
    if text_chars > 5000:
        return "Server-rendered"
    elif text_chars > 1000:
        return "Partially server-rendered"
    elif '__NEXT_DATA__' in html or '__NUXT__' in html:
        return "SSR framework — low visible text"
    elif re.search(r'<div[^>]+id=["\'](?:root|app)["\'][^>]*>\s*</div>', html):
        return "Client-side rendered (empty root div)"
    else:
        return f"Minimal text ({text_chars} chars)"


def parse_robots(body):
    """Parse robots.txt for AI crawler directives and sitemap URLs."""
    ai_crawlers = [
        "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot",
        "PerplexityBot", "Amazonbot", "Google-Extended", "Bytespider",
        "CCBot", "Applebot-Extended", "FacebookBot", "Cohere-ai"
    ]

    sitemaps = [s.strip() for s in re.findall(r'(?i)^Sitemap:\s*(.+)$', body, re.MULTILINE)]

    disallows = {}
    current_agents = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.lower().startswith('user-agent:'):
            current_agents = [line.split(':', 1)[1].strip()]
        elif line.lower().startswith('disallow:') and current_agents:
            path = line.split(':', 1)[1].strip()
            for agent in current_agents:
                disallows.setdefault(agent, []).append(path)

    global_disallows = disallows.get('*', [])

    crawler_status = {}
    for crawler in ai_crawlers:
        cd = disallows.get(crawler, [])
        if '/' in cd:
            crawler_status[crawler] = "Blocked"
        elif cd:
            crawler_status[crawler] = "Restricted"
        elif '/' in global_disallows:
            crawler_status[crawler] = "Blocked (via *)"
        else:
            crawler_status[crawler] = "Allowed (inherits *)"

    return {
        "sitemaps": list(dict.fromkeys(sitemaps)),  # deduplicate
        "crawler_status": crawler_status,
        "global_disallows": global_disallows[:15],
    }


def collect_page_evidence(url, label):
    """Collect full evidence for a single page URL."""
    status, headers, body = curl_fetch(url)
    if not body or status == 0:
        return {"url": url, "label": label, "status": status, "error": "Fetch failed"}

    jsonld_blocks = extract_jsonld_blocks(body)
    schema_types = [b.get("@type", "unknown") for b in jsonld_blocks if "@type" in b]
    text_chars, word_count = measure_body_text(body)

    return {
        "url": url,
        "label": label,
        "status": status,
        "raw_html_chars": len(body),
        "body_text_chars": text_chars,
        "body_text_words": word_count,
        "ssr_assessment": assess_ssr(text_chars, body),
        "schema_types": schema_types,
        "schema_blocks": jsonld_blocks,          # full JSON-LD content
        "meta_tags": extract_meta_tags(body),
        "headings": extract_headings(body),
    }


def discover_key_pages(base_url, robots_body):
    """Discover key page URLs covering all page types agents will score."""
    base = base_url.rstrip('/')

    # Start with common paths
    candidates = [
        {"url": base + "/", "label": "Homepage"},
        {"url": base + "/pages/about", "label": "About"},
        {"url": base + "/about", "label": "About"},
        {"url": base + "/pages/faq", "label": "FAQ"},
        {"url": base + "/faq", "label": "FAQ"},
    ]

    # Pull one sample of each content type from sitemaps
    sitemap_urls = [s.strip() for s in re.findall(r'(?i)^Sitemap:\s*(.+)$', robots_body, re.MULTILINE)]
    # Deduplicate sitemap URLs
    sitemap_urls = list(dict.fromkeys(sitemap_urls))

    for sitemap_url in sitemap_urls[:1]:
        status, _, sitemap_body = curl_fetch(sitemap_url, timeout=15)
        if status != 200:
            continue
        child_sitemaps = re.findall(r'<loc>(https?://[^<]+)</loc>', sitemap_body)
        for child in child_sitemaps:
            child = child.strip()
            _, _, child_body = curl_fetch(child, timeout=15)
            if not child_body:
                continue
            # All <loc> URLs from child sitemap — filter out root
            urls = [u.strip() for u in re.findall(r'<loc>(https?://[^<]+)</loc>', child_body)
                    if u.strip().rstrip('/') != base]

            if not urls:
                continue

            if 'product' in child.lower():
                candidates.append({"url": urls[0], "label": "Product PDP (sample)"})
            elif 'collection' in child.lower():
                candidates.append({"url": urls[0], "label": "Collection (sample)"})
            elif 'blog' in child.lower() or 'article' in child.lower():
                # urls[0] from a blog sitemap is an individual post, not the index
                # Filter out bare /blogs/xxx index URLs (no second path segment)
                post_urls = [u for u in urls if u.count('/') >= 5]
                if post_urls:
                    candidates.append({"url": post_urls[0], "label": "Blog post (sample)"})
            elif 'page' in child.lower():
                # Already covered by static candidates, skip
                pass

    # Deduplicate: one entry per label, first URL wins
    seen_labels = set()
    seen_urls = set()
    unique = []
    for p in candidates:
        if p["label"] not in seen_labels and p["url"] not in seen_urls:
            seen_labels.add(p["label"])
            seen_urls.add(p["url"])
            unique.append(p)

    return unique


def render_markdown(evidence):
    """Render evidence as a self-contained markdown block for subagent prompts."""
    lines = []
    lines.append("## VERIFIED EVIDENCE — Collected via curl (ground truth)")
    lines.append("")
    lines.append("> **Instructions for agents:** Score from this block. Do NOT use WebFetch or")
    lines.append("> curl to re-derive anything already listed here. If a schema type appears")
    lines.append("> in the JSON-LD blocks below, it IS present and server-rendered — score it")
    lines.append("> as present. If it does not appear, score it as absent.")
    lines.append("")

    # SSR summary table
    lines.append("### Page Inventory")
    lines.append("")
    lines.append("| Page | Status | Body Text | SSR | Schema Types |")
    lines.append("|---|---|---|---|---|")
    for p in evidence["pages"]:
        if "error" in p:
            lines.append(f"| {p['label']} | {p['status']} error | — | — | — |")
            continue
        schema_str = ", ".join(p["schema_types"]) if p["schema_types"] else "None"
        lines.append(
            f"| {p['label']} | {p['status']} | ~{p['body_text_words']:,} words | "
            f"{p['ssr_assessment']} | {schema_str} |"
        )
    lines.append("")

    # Full JSON-LD blocks per page
    lines.append("### JSON-LD Schema Blocks (complete content)")
    lines.append("")
    lines.append("> These are the exact JSON-LD blocks served in raw HTML. Use these to score")
    lines.append("> schema quality, identify missing fields, and validate data accuracy.")
    lines.append("")
    for p in evidence["pages"]:
        if "error" in p or not p.get("schema_blocks"):
            continue
        lines.append(f"#### {p['label']} — `{p['url']}`")
        lines.append("")
        for i, block in enumerate(p["schema_blocks"]):
            btype = block.get("@type", "unknown")
            if btype == "PARSE_ERROR":
                lines.append(f"**Block {i+1} (PARSE ERROR):** {block.get('raw', '')}")
            else:
                lines.append(f"**Block {i+1}: {btype}**")
                lines.append("```json")
                lines.append(json.dumps(block, indent=2, ensure_ascii=False))
                lines.append("```")
            lines.append("")

    # Meta tags
    lines.append("### Meta Tags")
    lines.append("")
    lines.append("| Page | Title | Description | Canonical | OG Image | Twitter Card |")
    lines.append("|---|---|---|---|---|---|")
    for p in evidence["pages"]:
        if "error" in p:
            continue
        m = p.get("meta_tags", {})
        title = (m.get("title") or "—")[:60]
        desc = ("✓" if m.get("description") else "—")
        canon = ("✓" if m.get("canonical") else "—")
        og_img = ("✓" if m.get("og_image") else "—")
        tc = (m.get("twitter_card") or "—")
        lines.append(f"| {p['label']} | {title} | {desc} | {canon} | {og_img} | {tc} |")
    lines.append("")

    # robots.txt
    robots = evidence.get("robots", {})
    lines.append("### robots.txt")
    lines.append("")
    sitemaps = robots.get("sitemaps", [])
    lines.append(f"**Sitemaps:** {', '.join(sitemaps) if sitemaps else 'None found'}")
    lines.append("")
    lines.append("| AI Crawler | Status |")
    lines.append("|---|---|")
    for crawler, status in robots.get("crawler_status", {}).items():
        lines.append(f"| {crawler} | {status} |")
    lines.append("")
    if robots.get("global_disallows"):
        disallows_str = "`, `".join(robots["global_disallows"])
        lines.append(f"**Global Disallow (User-agent: \\*):** `{disallows_str}`")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Collect GEO audit evidence via curl")
    parser.add_argument("url", help="Target domain URL (e.g. https://example.com)")
    parser.add_argument("--output", help="Save JSON evidence to this file path")
    parser.add_argument("--markdown", action="store_true", help="Print markdown block to stdout")
    args = parser.parse_args()

    url = args.url.rstrip('/')
    parsed = urlparse(url)
    domain = parsed.netloc

    print(f"[Phase 0] Collecting evidence for {domain}...", file=sys.stderr)

    # Fetch robots.txt
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    print(f"  robots.txt...", file=sys.stderr)
    robots_status, _, robots_body = curl_fetch(robots_url, timeout=15)
    robots_evidence = parse_robots(robots_body if robots_status == 200 else "")
    robots_evidence["status"] = robots_status

    # Discover key pages
    print(f"  Discovering pages from sitemap...", file=sys.stderr)
    key_pages = discover_key_pages(url, robots_body if robots_status == 200 else "")

    # Fetch each page
    page_evidence = []
    for page in key_pages:
        print(f"  {page['label']}: {page['url']}...", file=sys.stderr)
        ev = collect_page_evidence(page["url"], page["label"])
        if ev.get("status") == 200:
            page_evidence.append(ev)
        else:
            # Only include failed fetches for non-fallback candidates
            if not any(p["url"] == page["url"] and p.get("status") == 200
                       for p in page_evidence):
                page_evidence.append(ev)

    evidence = {
        "domain": domain,
        "target_url": url,
        "robots": robots_evidence,
        "pages": page_evidence,
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(evidence, f, indent=2, ensure_ascii=False)
        print(f"  Saved to {args.output}", file=sys.stderr)

    if args.markdown:
        print(render_markdown(evidence))
    elif not args.output:
        print(json.dumps(evidence, indent=2, ensure_ascii=False))

    return evidence


if __name__ == "__main__":
    main()
