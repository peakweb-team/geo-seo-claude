---
name: geo-audit
description: Full website GEO+SEO audit with parallel subagent delegation. Orchestrates a comprehensive Generative Engine Optimization audit across AI citability, platform analysis, technical infrastructure, content quality, and schema markup. Produces a composite GEO Score (0-100) with prioritized action plan.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - WebFetch
  - Write
---

# GEO Audit Orchestration Skill

## Purpose

This skill performs a comprehensive Generative Engine Optimization (GEO) audit of any website. GEO is the practice of optimizing web content so that AI systems (ChatGPT, Claude, Perplexity, Gemini, etc.) can discover, understand, cite, and recommend it. This audit measures how well a site performs across all GEO dimensions and produces an actionable improvement plan.

## Key Insight

Traditional SEO optimizes for search engine rankings. GEO optimizes for AI citation and recommendation. Sites that score high on GEO metrics see 30-115% more visibility in AI-generated responses (Georgia Tech / Princeton / IIT Delhi 2024 study). The two disciplines overlap but have distinct requirements.

---

## Audit Workflow

### Phase 1: Discovery and Reconnaissance

**Step 1: Fetch Homepage and Detect Business Type**

1. Use WebFetch to retrieve the homepage at the provided URL.
2. Extract the following signals:
   - Page title, meta description, H1 heading
   - Navigation menu items (reveals site structure)
   - Footer content (reveals business info, location, legal pages)
   - Schema.org markup on homepage (Organization, LocalBusiness, etc.)
   - Pricing page link (SaaS indicator)
   - Product listing patterns (E-commerce indicator)
   - Blog/resource section (Publisher indicator)
   - Service pages (Agency indicator)
   - Address/phone/Google Maps embed (Local business indicator)

3. Classify the business type using these patterns:

| Business Type | Detection Signals |
|---|---|
| **SaaS** | Pricing page, "Sign up" / "Free trial" CTAs, app.domain.com subdomain, feature comparison tables, integration pages |
| **Local Business** | Physical address on homepage, Google Maps embed, "Near me" content, LocalBusiness schema, service area pages |
| **E-commerce** | Product listings, shopping cart, product schema, category pages, price displays, "Add to cart" buttons |
| **Publisher** | Blog-heavy navigation, article schema, author pages, date-based archives, RSS feeds, high content volume |
| **Agency/Services** | Case studies, portfolio, "Our Work" section, team page, client logos, service descriptions |
| **Hybrid** | Combination of above signals -- classify by dominant pattern |

**Step 2: Crawl Sitemap and Internal Links**

1. Attempt to fetch `/sitemap.xml` and `/sitemap_index.xml`.
2. If sitemap exists, extract up to 50 unique page URLs prioritized by:
   - Homepage (always include)
   - Top-level navigation pages
   - High-value pages (pricing, about, contact, key service/product pages)
   - Blog posts (sample 5-10 most recent)
   - Category/landing pages
3. If no sitemap exists, crawl internal links from the homepage:
   - Extract all `<a href>` links pointing to the same domain
   - Follow up to 2 levels deep
   - Prioritize pages linked from main navigation
4. Respect `robots.txt` directives -- do not fetch disallowed paths.
5. Enforce a maximum of 50 pages and a 30-second timeout per fetch.

**Step 3: Collect Page-Level Data**

For each page in the crawl set, record:
- URL, title, meta description, canonical URL
- H1-H6 heading structure
- Word count of main content
- Schema.org types present
- Internal/external link counts
- Images with/without alt text
- Open Graph and Twitter Card meta tags
- Response status code
- Whether the page has structured data

---

### Phase 2: Parallel Subagent Delegation

Delegate analysis to 5 specialized subagents. Each subagent operates on the collected page data and produces a category score (0-100) plus findings.

**Subagent 1: AI Citability Analysis (geo-citability)**
- Analyze content blocks for quotability by AI systems
- Score passage self-containment, answer block quality, statistical density
- Identify high-value pages that could be reformatted for better AI citation

**Subagent 2: Platform & Brand Analysis (geo-brand-mentions)**
- Check brand presence across YouTube, Reddit, Wikipedia, LinkedIn
- Assess third-party mention volume and sentiment
- Score brand authority signals that AI models use for entity recognition

**Subagent 3: Technical GEO Infrastructure (geo-crawlers + geo-llmstxt)**
- Analyze robots.txt for AI crawler access
- Check for llms.txt presence and quality
- Verify meta tags, headers, and technical accessibility for AI systems
- Check page speed and rendering (JS-heavy sites are harder for AI crawlers)

**Subagent 4: Content E-E-A-T Quality (geo-content)**
- Evaluate Experience, Expertise, Authoritativeness, Trustworthiness signals
- Check author bios, credentials, source citations
- Assess content freshness, depth, and originality
- Verify "About" page quality and team credentials

**Subagent 5: Schema & Structured Data (geo-schema)**
- Validate all schema.org markup
- Check for GEO-critical schema types (FAQ, HowTo, Organization, Product, Article)
- Assess schema completeness and accuracy
- Identify missing schema opportunities

---

### Phase 3: Score Aggregation and Report Generation

#### Composite GEO Score Calculation

The overall GEO Score (0-100) is a weighted average of six category scores:

| Category | Weight | What It Measures |
|---|---|---|
| **AI Citability** | 25% | How quotable/extractable content is for AI systems |
| **Brand Authority** | 20% | Third-party mentions, entity recognition signals |
| **Content E-E-A-T** | 20% | Experience, Expertise, Authoritativeness, Trustworthiness |
| **Technical GEO** | 15% | AI crawler access, llms.txt, rendering, speed |
| **Schema & Structured Data** | 10% | Schema.org markup quality and completeness |
| **Platform Optimization** | 10% | Presence on platforms AI models train on and cite |

**Formula:**
```
GEO_Score = (Citability * 0.25) + (Brand * 0.20) + (EEAT * 0.20) + (Technical * 0.15) + (Schema * 0.10) + (Platform * 0.10)
```

#### Score Interpretation

| Score Range | Rating | Interpretation |
|---|---|---|
| 90-100 | Excellent | Top-tier GEO optimization; site is highly likely to be cited by AI |
| 75-89 | Good | Strong GEO foundation with room for improvement |
| 60-74 | Fair | Moderate GEO presence; significant optimization opportunities exist |
| 40-59 | Poor | Weak GEO signals; AI systems may struggle to cite or recommend |
| 0-39 | Critical | Minimal GEO optimization; site is largely invisible to AI systems |

---

## Issue Severity Classification

Every issue found during the audit is classified by severity:

### Critical (Fix Immediately)
- All AI crawlers blocked in robots.txt
- No indexable content (JavaScript-rendered only with no SSR)
- Domain-level noindex directive
- Site returns 5xx errors on key pages
- Complete absence of any structured data
- Brand not recognized as an entity by any AI system

### High (Fix Within 1 Week)
- Key AI crawlers (GPTBot, ClaudeBot, PerplexityBot) blocked
- No llms.txt file present
- Zero question-answering content blocks on key pages
- Missing Organization or LocalBusiness schema
- No author attribution on content pages
- All content behind login/paywall with no preview

### Medium (Fix Within 1 Month)
- Partial AI crawler blocking (some allowed, some blocked)
- llms.txt exists but is incomplete or malformed
- Content blocks average under 50 citability score
- Missing FAQ schema on pages with FAQ content
- Thin author bios without credentials
- No Wikipedia or Reddit brand presence

### Low (Optimize When Possible)
- Minor schema validation errors
- Some images missing alt text
- Content freshness issues on non-critical pages
- Missing Open Graph tags
- Suboptimal heading hierarchy on some pages
- LinkedIn company page exists but is incomplete

---

## Output Format

Generate a file called `GEO-AUDIT-REPORT.md` with the following structure:

```markdown
# GEO Audit Report: [Site Name]

**Audit Date:** [Date]
**URL:** [URL]
**Business Type:** [Detected Type]
**Pages Analyzed:** [Count]

---

## Executive Summary

**Overall GEO Score: [X]/100 ([Rating])**

[2-3 sentence summary of the site's GEO health, biggest strengths, and most critical gaps.]

### Score Breakdown

| Category | Score | Weight | Weighted Score |
|---|---|---|---|
| AI Citability | [X]/100 | 25% | [X] |
| Brand Authority | [X]/100 | 20% | [X] |
| Content E-E-A-T | [X]/100 | 20% | [X] |
| Technical GEO | [X]/100 | 15% | [X] |
| Schema & Structured Data | [X]/100 | 10% | [X] |
| Platform Optimization | [X]/100 | 10% | [X] |
| **Overall GEO Score** | | | **[X]/100** |

---

## Critical Issues (Fix Immediately)

[List each critical issue with specific page URLs and recommended fix]

## High Priority Issues

[List each high-priority issue with details]

## Medium Priority Issues

[List each medium-priority issue]

## Low Priority Issues

[List each low-priority issue]

---

## Category Deep Dives

### AI Citability ([X]/100)
[Detailed findings, examples of good/bad passages, rewrite suggestions]

### Brand Authority ([X]/100)
[Platform presence map, mention volume, sentiment]

### Content E-E-A-T ([X]/100)
[Author quality, source citations, freshness, depth]

### Technical GEO ([X]/100)
[Crawler access, llms.txt, rendering, headers]

### Schema & Structured Data ([X]/100)
[Schema types found, validation results, missing opportunities]

### Platform Optimization ([X]/100)
[Presence on YouTube, Reddit, Wikipedia, etc.]

---

## Quick Wins (Implement This Week)

1. [Specific, actionable quick win with expected impact]
2. [Another quick win]
3. [Another quick win]
4. [Another quick win]
5. [Another quick win]

## 30-Day Action Plan

### Week 1: [Theme]
- [ ] Action item 1
- [ ] Action item 2

### Week 2: [Theme]
- [ ] Action item 1
- [ ] Action item 2

### Week 3: [Theme]
- [ ] Action item 1
- [ ] Action item 2

### Week 4: [Theme]
- [ ] Action item 1
- [ ] Action item 2

---

## Appendix: Pages Analyzed

| URL | Title | GEO Issues |
|---|---|---|
| [url] | [title] | [issue count] |
```

---

## CLIENT-REPORT.md — Business-Friendly Summary

In addition to the technical `GEO-AUDIT-REPORT.md`, generate a `CLIENT-REPORT.md` written for **business owners, not developers**. This report translates technical findings into plain English and business impact.

### Writing Guidelines

- **No jargon** — explain technical concepts simply
- **Business impact first** — every issue should explain what it costs the business
- **Actionable** — connect findings to specific fixes
- **Conversational tone** — write as a consultant, not a tool
- **Use analogies** — help non-technical readers understand (e.g., "It's like having a store with no sign")

### CLIENT-REPORT.md Structure

```markdown
# Website Visibility Audit for [Business Name]

**Prepared for:** [Contact Name], [Title]
**Date:** [Date]
**Your Website:** [URL]

---

## What This Report Is About (In Plain English)

### The Short Version

When someone asks **ChatGPT, Google AI, or Perplexity** a question like *"[Sample query relevant to their business]"* — **your business is rarely mentioned**, even though you have [key credibility facts].

**This audit explains why and shows you exactly how to fix it.**

---

## Why This Matters to Your Business

### The New Way People Find Businesses

**Traditional Google Search (Still Important):**
- Customer searches "[relevant query]"
- Gets a list of 10 blue links
- Clicks through to websites

**AI Search (Growing Fast):**
- Customer asks ChatGPT: "[natural language question]"
- AI gives a direct answer with 2-3 specific recommendations
- Customer calls those businesses directly

### The Problem

Right now, when AI systems answer questions about [industry/location], **they rarely mention your business** — not because you're not qualified, but because your website doesn't "speak AI" yet.

**What this means for you:**
- Lost phone calls from potential customers who never hear your name
- Competitors who optimize for AI get recommended instead of you
- Your [years] of experience and [credentials] are invisible to these systems

---

## What Is "GEO"? (And Why Should You Care?)

**GEO = Generative Engine Optimization**

- **SEO** = Making your website show up in Google search results
- **GEO** = Making your website get recommended by ChatGPT, Claude, Google AI, and Perplexity

Studies show that **30-115% more people** see businesses that are optimized for AI search compared to those that aren't.

---

## Your Current Score: [X]/100

**What this means:**
- [Score interpretation in plain language]
- [What the score means for their business]

### Think of it like curb appeal for your website:
[Analogy that explains the score in relatable terms]

---

## What's Working Well ✅

[5 bullet points of strengths, starting with ✅]

**The foundation is solid.** We just need to make AI systems *notice* it.

---

## The 6 Biggest Problems (And What They Cost You)

### 1. ❌ [Issue Title]

**The Issue:** [Plain English explanation]

**What This Costs You:** [Business impact — lost leads, lost calls, competitors winning]

**Business Impact:** [Specific, quantified if possible]

[Repeat for issues 2-6]

---

## What Happens If You Do Nothing?

**Short-term (Next 6 months):**
- [Consequence 1]
- [Consequence 2]
- [Consequence 3]

**Long-term (1-2 years):**
- [Consequence 1]
- [Consequence 2]
- [Consequence 3]

**Think of it like websites in 2005:** Early adopters dominated. Those who waited struggled to catch up.

---

## The Good News: This Is All Fixable

Unlike some business problems, **every issue in this audit has a clear solution** with a known ROI.

### Quick Wins (1 Hour of Work = Immediate Impact)

[7 numbered quick fixes with time estimates and expected score improvement]

---

## Your 30-Day Implementation Plan

### Week 1: Fix Critical Technical Issues
**Time Required:** [X] hours
**Can Be Done By:** [Who]
- [Action items]
**Expected Impact:** Score improves to ~[X]

### Week 2: Build Your Online Identity
**Time Required:** [X] hours
**Can Be Done By:** [Who]
- [Action items]
**Expected Impact:** Score improves to ~[X]

### Week 3: Add Depth and Data
**Time Required:** [X] hours
**Can Be Done By:** [Who]
- [Action items]
**Expected Impact:** Score improves to ~[X]

### Week 4: Polish and Test
**Time Required:** [X] hours
**Can Be Done By:** [Who]
- [Action items]
**Expected Impact:** Score reaches ~[X]

---

## The Investment

### Option 1: Do It Yourself
**Time Required:** [X] hours over 30 days
**Cost:** Your time + maybe [X] hours of web developer help ($X)
**Best For:** If you enjoy this stuff and have the time

### Option 2: Hire Someone to Implement
**Estimated Cost:** $[X]-[X] for full implementation
**Time Required from You:** [X] hours
**Best For:** If you'd rather focus on running the business

### Option 3: Hybrid Approach
**You do:** Write the content (you're the expert)
**Developer does:** All technical implementation
**Estimated Cost:** $[X]-[X]
**Best For:** Most business owners

---

## Expected Return on Investment

### Conservative Estimate:

**Assumptions:**
- [Traffic assumptions]
- [Conversion assumptions]

**Result:**
- [X] additional leads per month
- **Additional monthly revenue: $[X]-[X]**
- **Annual impact: $[X]-[X]**

**Break-even:** Implementation pays for itself in the first month.

---

## Frequently Asked Questions

### "[Common objection/question]"
[Answer in conversational tone]

[Repeat for 4-5 FAQs]

---

## Real-World Example: What This Looks Like

### Before Optimization:

**Customer:** "Hey ChatGPT, [sample question]"
**ChatGPT:** "[Response that doesn't mention client's business]"
*[Your business: Not mentioned]*

### After Optimization:

**Customer:** "Hey ChatGPT, [same question]"
**ChatGPT:** "[Response that recommends client's business with specific details]"
*[Your business: Mentioned first with specific details]*

**That's the difference.** Same customer, same question. One scenario: they never hear about you. Other scenario: you're recommended with supporting details.

---

## Next Steps: What to Do Right Now

### Step 1: Review the Full Technical Report
The detailed audit report is included (GEO-AUDIT-REPORT.md).

### Step 2: Decide Your Approach
- **DIY:** Set aside [X] hours over next month
- **Hire it out:** Budget $[X]-[X] for full implementation
- **Hybrid:** You write content, developer handles code

### Step 3: Start with Quick Wins (This Week)
Even before deciding on the full plan, these quick fixes deliver immediate value.

### Step 4: Schedule the 30-Day Plan
Block time on your calendar or schedule it with your implementation team.

---

## The Bottom Line

You've built an excellent business. You have the experience, the reputation, and the satisfied customers to prove it.

**The only thing holding you back is that AI systems don't know about it yet.**

This audit is your roadmap to change that — with specific fixes, clear timelines, and measurable results.

**The question isn't whether to do this.** Your competitors will figure this out eventually.

**The question is: Do you want to be ahead of them or catching up to them?**

---

*This report was prepared [Date] specifically for [Business Name]. Results and timelines are based on current AI search landscape and typical implementation speeds.*
```

---

## Quality Gates

- **Page Limit:** Never crawl more than 50 pages per audit. Prioritize high-value pages.
- **Timeout:** 30-second maximum per page fetch. Skip pages that exceed this.
- **Robots.txt:** Always check and respect robots.txt before crawling. Note any AI-specific directives.
- **Rate Limiting:** Wait at least 1 second between page fetches to avoid overloading the server.
- **Error Handling:** Log failed fetches but continue the audit. Report fetch failures in the appendix.
- **Content Type:** Only analyze HTML pages. Skip PDFs, images, and other binary content.
- **Deduplication:** Canonicalize URLs before crawling. Skip duplicate content (e.g., HTTP vs HTTPS, www vs non-www, trailing slashes).

---

## Business-Type-Specific Audit Adjustments

### SaaS Sites
- Extra weight on: Feature comparison tables (high citability), integration pages, documentation quality
- Check for: API documentation structure, changelog pages, knowledge base organization
- Key schema: SoftwareApplication, FAQPage, HowTo

### Local Businesses
- Extra weight on: NAP consistency, Google Business Profile signals, local schema
- Check for: Service area pages, location-specific content, review markup
- Key schema: LocalBusiness, GeoCoordinates, OpeningHoursSpecification

### E-commerce Sites
- Extra weight on: Product descriptions (citability), comparison content, buying guides
- Check for: Product schema completeness, review aggregation, FAQ sections on product pages
- Key schema: Product, AggregateRating, Offer, BreadcrumbList

### Publishers
- Extra weight on: Article quality, author credentials, source citation practices
- Check for: Article schema, author pages, publication date freshness, original research
- Key schema: Article, NewsArticle, Person (author), ClaimReview

### Agency/Services
- Extra weight on: Case studies (citability), expertise demonstration, thought leadership
- Check for: Portfolio schema, team credentials, industry-specific expertise signals
- Key schema: Organization, Service, Person (team), Review
