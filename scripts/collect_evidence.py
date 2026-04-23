#!/usr/bin/env python3
"""
Phase 0 evidence collector for GEO audits.

Fetches key pages via curl and extracts everything agents need to score:
- Full JSON-LD blocks (complete content, not just type names)
- Body text word counts (SSR verification)
- Meta tags (title, description, canonical, OG tags)
- robots.txt AI crawler directives
- Page coverage: nav/footer links cross-referenced against sitemap

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
        "global_disallows": global_disallows[:20],
    }


def extract_nav_links(html, base_url):
    """
    Extract unique internal page paths from homepage HTML (nav + footer).
    Returns sorted list of path strings like '/pages/about', '/policies/privacy-policy'.
    Filters to non-product/collection paths — these are the pages most likely to be
    meaningful trust/info pages worth checking against the sitemap.
    """
    parsed = urlparse(base_url)
    domain = parsed.netloc

    hrefs = re.findall(r'href=["\']([^"\'#\s]+)["\']', html, re.IGNORECASE)

    paths = set()
    for href in hrefs:
        href = href.strip()
        if not href or href.startswith(('javascript:', 'mailto:', 'tel:', 'data:')):
            continue
        if href.startswith('http'):
            if domain not in href:
                continue
            path = urlparse(href).path
        elif href.startswith('/') and not href.startswith('//'):
            path = href.split('?')[0].split('#')[0]
        else:
            continue

        path = path.rstrip('/')
        if not path or path == '':
            continue

        # Skip high-volume dynamic paths — these are expected to be sitemapped separately
        skip_prefixes = ('/products/', '/collections/', '/cdn/', '/assets/', '/cart',
                         '/checkout', '/account', '/search', '/admin')
        if any(path.startswith(p) for p in skip_prefixes):
            continue

        paths.add(path)

    return sorted(paths)


def collect_sitemap_data(sitemap_urls, timeout=15):
    """
    Fetch all child sitemaps and collect every URL they contain.
    Returns (all_urls, child_sitemap_info) where:
      all_urls: set of full URL strings across all child sitemaps
      child_sitemap_info: list of {url, count, type} per child sitemap
    """
    all_urls = set()
    child_info = []

    for sitemap_url in sitemap_urls:
        sitemap_url = sitemap_url.strip()
        status, _, body = curl_fetch(sitemap_url, timeout=timeout)
        if status != 200 or not body:
            continue

        # Check if this is a sitemap index
        if '<sitemapindex' in body:
            child_sitemaps = re.findall(r'<loc>(https?://[^<]+)</loc>', body)
            for child in child_sitemaps:
                child = child.strip()
                _, _, child_body = curl_fetch(child, timeout=timeout)
                if not child_body:
                    continue
                urls = [u.strip() for u in re.findall(r'<loc>(https?://[^<]+)</loc>', child_body)]
                all_urls.update(urls)
                child_info.append({"url": child, "count": len(urls)})
        else:
            # Direct sitemap
            urls = [u.strip() for u in re.findall(r'<loc>(https?://[^<]+)</loc>', body)]
            all_urls.update(urls)
            child_info.append({"url": sitemap_url, "count": len(urls)})

    return all_urls, child_info


def analyze_page_coverage(nav_paths, sitemap_urls, robots_global_disallows, base_url):
    """
    Cross-reference navigation links against sitemap URLs and robots.txt disallows.

    Identifies:
    - Nav pages not found in the sitemap (potential indexing gaps)
    - Which robots.txt disallow rules apply to real, confirmed pages

    This is the ground truth that prevents agents from making recommendations
    based on robots.txt rules alone without knowing whether real pages exist.
    """
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Normalize sitemap URLs to paths for comparison
    sitemap_paths = set()
    for u in sitemap_urls:
        try:
            path = urlparse(u).path.rstrip('/')
            if path:
                sitemap_paths.add(path)
        except Exception:
            pass

    # For each nav path: is it in the sitemap? is it blocked by robots.txt?
    nav_analysis = []
    for path in nav_paths:
        in_sitemap = path in sitemap_paths

        # Check if any global disallow rule covers this path
        blocked_by = None
        for rule in robots_global_disallows:
            if not rule:
                continue
            # Strip wildcard suffix for prefix matching
            prefix = rule.rstrip('*')
            if prefix and (path == prefix.rstrip('/') or path.startswith(prefix.rstrip('/') + '/')):
                blocked_by = rule
                break

        nav_analysis.append({
            "path": path,
            "full_url": base + path,
            "in_sitemap": in_sitemap,
            "robots_blocked_by": blocked_by,
        })

    # Disallow rules that have confirmed real pages behind them
    disallow_with_real_pages = []
    for rule in robots_global_disallows:
        if not rule:
            continue
        prefix = rule.rstrip('*').rstrip('/')
        if not prefix:
            continue
        matching = [p for p in nav_paths if p == prefix or p.startswith(prefix + '/')]
        if matching:
            disallow_with_real_pages.append({
                "rule": rule,
                "confirmed_pages": matching[:5],
                "any_in_sitemap": any(p in sitemap_paths for p in matching),
            })

    return {
        "sitemap_url_count": len(sitemap_urls),
        "nav_paths_found": len(nav_paths),
        "nav_analysis": nav_analysis,
        "disallow_rules_with_real_pages": disallow_with_real_pages,
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
        "schema_blocks": jsonld_blocks,
        "meta_tags": extract_meta_tags(body),
        "headings": extract_headings(body),
    }


def discover_key_pages(base_url, robots_body):
    """
    Discover key page URLs covering all page types agents will score.
    Returns (key_pages, all_sitemap_urls) so sitemap data is not fetched twice.
    """
    base = base_url.rstrip('/')

    # Start with common paths
    candidates = [
        {"url": base + "/", "label": "Homepage"},
        {"url": base + "/pages/about", "label": "About"},
        {"url": base + "/about", "label": "About"},
        {"url": base + "/pages/faq", "label": "FAQ"},
        {"url": base + "/faq", "label": "FAQ"},
    ]

    sitemap_urls_declared = [s.strip() for s in re.findall(r'(?i)^Sitemap:\s*(.+)$', robots_body, re.MULTILINE)]
    sitemap_urls_declared = list(dict.fromkeys(sitemap_urls_declared))

    all_sitemap_urls = set()

    for sitemap_url in sitemap_urls_declared[:1]:
        status, _, sitemap_body = curl_fetch(sitemap_url, timeout=15)
        if status != 200:
            continue
        child_sitemaps = re.findall(r'<loc>(https?://[^<]+)</loc>', sitemap_body)
        for child in child_sitemaps:
            child = child.strip()
            _, _, child_body = curl_fetch(child, timeout=15)
            if not child_body:
                continue

            urls = [u.strip() for u in re.findall(r'<loc>(https?://[^<]+)</loc>', child_body)
                    if u.strip().rstrip('/') != base]
            all_sitemap_urls.update(urls)

            if not urls:
                continue

            if 'product' in child.lower():
                candidates.append({"url": urls[0], "label": "Product PDP (sample)"})
            elif 'collection' in child.lower():
                candidates.append({"url": urls[0], "label": "Collection (sample)"})
            elif 'blog' in child.lower() or 'article' in child.lower():
                # Filter for individual post URLs (5+ path segments), not index pages
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

    return unique, all_sitemap_urls


def render_markdown(evidence):
    """Render evidence as a self-contained markdown block for subagent prompts."""
    lines = []
    lines.append("## VERIFIED EVIDENCE — Collected via curl (ground truth)")
    lines.append("")
    lines.append("> **Instructions for agents:** Score from this block. Do NOT use WebFetch or")
    lines.append("> curl to re-derive anything already listed here. If a schema type appears")
    lines.append("> in the JSON-LD blocks below, it IS present and server-rendered — score it")
    lines.append("> as present. If it does not appear, score it as absent.")
    lines.append("> ")
    lines.append("> For robots.txt recommendations: only recommend changes for paths where")
    lines.append("> the Page Coverage section below confirms real pages exist at those paths.")
    lines.append("> Do not infer page existence from robots.txt disallow rules alone.")
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

    # Page coverage analysis
    coverage = evidence.get("page_coverage", {})
    if coverage:
        lines.append("### Page Coverage Analysis")
        lines.append("")
        lines.append(f"**Sitemap URLs found:** {coverage.get('sitemap_url_count', 0)}")
        lines.append(f"**Navigation paths discovered:** {coverage.get('nav_paths_found', 0)}")
        lines.append("")

        nav_analysis = coverage.get("nav_analysis", [])
        not_in_sitemap = [p for p in nav_analysis if not p["in_sitemap"]]
        if not_in_sitemap:
            lines.append("**Navigation pages NOT in sitemap** (confirmed to exist via link discovery):")
            lines.append("")
            lines.append("| Path | In Sitemap | robots.txt |")
            lines.append("|---|---|---|")
            for item in not_in_sitemap[:25]:
                blocked = f"Blocked by `{item['robots_blocked_by']}`" if item["robots_blocked_by"] else "Allowed"
                lines.append(f"| `{item['path']}` | No | {blocked} |")
            lines.append("")

        disallow_real = coverage.get("disallow_rules_with_real_pages", [])
        if disallow_real:
            lines.append("**robots.txt disallow rules with confirmed real pages:**")
            lines.append("")
            lines.append("| Rule | Confirmed Pages | Any in Sitemap? |")
            lines.append("|---|---|---|")
            for item in disallow_real:
                pages = ", ".join(f"`{p}`" for p in item["confirmed_pages"])
                in_sm = "Yes" if item["any_in_sitemap"] else "No"
                lines.append(f"| `{item['rule']}` | {pages} | {in_sm} |")
            lines.append("")
        else:
            lines.append("**robots.txt disallow rules:** No confirmed real pages found behind any disallow rule (pages may exist but were not linked from the homepage).")
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

    # Discover key pages (also collects all sitemap URLs as a side effect)
    print(f"  Discovering pages from sitemap...", file=sys.stderr)
    key_pages, all_sitemap_urls = discover_key_pages(url, robots_body if robots_status == 200 else "")

    # Fetch each page, keeping the homepage HTML for nav link extraction
    page_evidence = []
    homepage_html = None
    for page in key_pages:
        print(f"  {page['label']}: {page['url']}...", file=sys.stderr)
        ev = collect_page_evidence(page["url"], page["label"])
        if ev.get("status") == 200:
            if page["label"] == "Homepage" and homepage_html is None:
                # Re-fetch homepage to get raw HTML for nav analysis
                # (collect_page_evidence doesn't store raw HTML to keep evidence lean)
                _, _, homepage_html = curl_fetch(page["url"])
            page_evidence.append(ev)
        else:
            if not any(p["url"] == page["url"] and p.get("status") == 200
                       for p in page_evidence):
                page_evidence.append(ev)

    # Page coverage: nav links vs sitemap
    page_coverage = None
    if homepage_html:
        print(f"  Analyzing page coverage (nav vs sitemap)...", file=sys.stderr)
        nav_paths = extract_nav_links(homepage_html, url)
        page_coverage = analyze_page_coverage(
            nav_paths,
            all_sitemap_urls,
            robots_evidence.get("global_disallows", []),
            url,
        )

    evidence = {
        "domain": domain,
        "target_url": url,
        "robots": robots_evidence,
        "pages": page_evidence,
        "page_coverage": page_coverage,
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
