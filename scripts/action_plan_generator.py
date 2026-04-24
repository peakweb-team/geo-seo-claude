#!/usr/bin/env python3
"""
GEO Action Plan Generator
=========================
Reads existing audit markdown files from an audit directory, extracts structured
findings, maps them to a ranked action plan, and outputs JSON suitable for
roadmap markdown generation and PDF rendering.

Usage:
    python3 action_plan_generator.py <audit_dir> [--output /tmp/roadmap.json]
    python3 action_plan_generator.py ~/.geo-prospects/audits/example.com
    python3 action_plan_generator.py ~/.geo-prospects/audits/example.com --output /tmp/roadmap.json

Design notes:
    - All ranking is deterministic — no LLM calls in this script.
    - The skill (geo-roadmap/SKILL.md) adds the LLM layer for executive summary prose.
    - PRIORITY_WEIGHTS constants are intentionally exposed at module level so they
      can be tuned without understanding the internals.
    - parse_audit_findings() uses keyword/pattern matching against markdown text.
      This is intentionally simple and tolerates partial/missing audit files.
"""

import argparse
import copy
import json
import os
import re
import sys
from datetime import date


# ---------------------------------------------------------------------------
# Priority weight constants — tune these to adjust ranking behaviour
# ---------------------------------------------------------------------------
# Raw score components and their maximum contributions:
#   impact:              up to 40 pts
#   control:             up to 20 pts
#   speed (time horizon): up to 15 pts
#   difficulty penalty:  -0 to -20 pts
#   foundational bonus:  +10 pts
#   multi-platform bonus: +5 pts (if 3+ platforms affected)
#   peakweb bonus:       +3 pts (if direct_service)
# Max possible raw = 40+20+15+0+10+5+3 = 93 → normalised to 0-100

PRIORITY_WEIGHTS = {
    "impact": {"very_high": 40, "high": 30, "medium": 20, "low": 10},
    "control": {"direct": 20, "mixed": 8, "indirect": 0},
    "speed": {"immediate": 15, "near_term": 8, "long_term": 0},
    "difficulty_penalty": {"low": 0, "medium": -5, "high": -12, "very_high": -20},
    "foundational_bonus": 10,
    "multi_platform_bonus": 5,   # awarded when len(affectedPlatforms) >= 3
    "peakweb_bonus": 3,          # awarded when peakwebFit == "direct_service"
    "raw_max": 93,               # used for normalisation
}


# ---------------------------------------------------------------------------
# Action catalog — every possible action item with its baseline metadata.
# These are templates; map_findings_to_actions() copies and enriches them
# with evidence and customer-specific notes.
# ---------------------------------------------------------------------------
ACTION_CATALOG = {
    "unblock_ai_crawlers": {
        "id": "unblock_ai_crawlers",
        "title": "Unblock AI Crawlers in robots.txt",
        "category": "technical",
        "scoreComponent": "technical",
        "description": "Remove Disallow directives that prevent GPTBot, ClaudeBot, PerplexityBot, and similar AI agents from crawling the site.",
        "whyItMatters": "AI systems can only cite content they can access. If their crawlers are blocked, your site is invisible to them regardless of content quality.",
        "controlLevel": "direct",
        "difficultyLevel": "low",
        "estimatedScoreImpact": "very_high",
        "timeHorizon": "immediate",
        "peakwebFit": "direct_service",
        "isFoundational": True,
        "affectedPlatforms": ["ChatGPT", "Perplexity", "Claude", "Gemini", "Bing Copilot"],
        "implementationNotes": "Edit robots.txt. Remove or scope Disallow rules for: GPTBot, ClaudeBot, PerplexityBot, CCBot, Applebot-Extended, anthropic-ai. Test at https://search.google.com/search-console/robots.txt-tester and equivalent.",
        "dependencies": [],
        "status": "not_started",
    },
    "publish_llms_txt": {
        "id": "publish_llms_txt",
        "title": "Publish an llms.txt File",
        "category": "technical",
        "scoreComponent": "ai_citability",
        "description": "Create a /llms.txt file at the site root that summarises the business, key pages, and content for AI systems that read it directly.",
        "whyItMatters": "The llms.txt standard is still emerging and adoption by AI platforms is limited. A small number of LLM-powered agents read it as a structured site index, but the major AI search engines (ChatGPT, Perplexity, Gemini) do not rely on it for citation decisions. It is a low-cost signal worth adding once higher-impact items are addressed.",
        "controlLevel": "direct",
        "difficultyLevel": "low",
        "estimatedScoreImpact": "low",
        "timeHorizon": "near_term",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["Claude", "some Perplexity configurations"],
        "implementationNotes": "Follow the llms.txt standard (https://llmstxt.org). Include: business name, one-paragraph description, key URLs, primary contact, service categories. Keep under 2KB for best compatibility.",
        "dependencies": [],
        "status": "not_started",
    },
    "add_organization_schema": {
        "id": "add_organization_schema",
        "title": "Add Organization Schema (JSON-LD)",
        "category": "schema",
        "scoreComponent": "schema",
        "description": "Implement an Organization schema block in the site's <head> that names the business, provides its URL, logo, contact details, and sameAs links to authoritative profiles.",
        "whyItMatters": "Organization schema is how AI systems confirm a business's identity and connect your site to your entity records on Wikipedia, Wikidata, LinkedIn, and other sources. Without it, AI has to guess.",
        "controlLevel": "direct",
        "difficultyLevel": "low",
        "estimatedScoreImpact": "medium",
        "timeHorizon": "immediate",
        "peakwebFit": "direct_service",
        "isFoundational": True,
        "affectedPlatforms": ["Google AI Overviews", "ChatGPT", "Gemini", "Bing Copilot"],
        "implementationNotes": "Add JSON-LD to <head>. Required fields: @type, name, url, logo, contactPoint, sameAs (list at least LinkedIn, Google Business Profile, and any Wikipedia/Wikidata entries).",
        "dependencies": [],
        "status": "not_started",
    },
    "add_local_business_schema": {
        "id": "add_local_business_schema",
        "title": "Add LocalBusiness Schema (JSON-LD)",
        "category": "schema",
        "scoreComponent": "schema",
        "description": "Implement a LocalBusiness (or appropriate sub-type) schema block with full NAP details, opening hours, geo-coordinates, and service area.",
        "whyItMatters": "Local AI queries rely heavily on structured location data. Without LocalBusiness schema, AI systems often skip or mis-categorise local service providers in conversational recommendations.",
        "controlLevel": "direct",
        "difficultyLevel": "low",
        "estimatedScoreImpact": "high",
        "timeHorizon": "immediate",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["Google AI Overviews", "ChatGPT", "Gemini", "Bing Copilot"],
        "implementationNotes": "Use the most specific sub-type available (e.g. PlumbingBusiness, LegalService, MedicalBusiness). Include: name, address (PostalAddress), telephone, openingHours, geo (GeoCoordinates), areaServed, priceRange, aggregateRating if applicable.",
        "dependencies": ["add_organization_schema"],
        "status": "not_started",
    },
    "add_faq_schema": {
        "id": "add_faq_schema",
        "title": "Add FAQPage Schema to Key Pages",
        "category": "schema",
        "scoreComponent": "schema",
        "description": "Mark up FAQ content with FAQPage schema so AI systems can extract individual Q&A pairs directly.",
        "whyItMatters": "FAQ schema makes your answers directly machine-readable. AI systems that generate answers to common questions actively prefer sources where they can extract clean Q&A pairs.",
        "controlLevel": "direct",
        "difficultyLevel": "low",
        "estimatedScoreImpact": "high",
        "timeHorizon": "immediate",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["Google AI Overviews", "ChatGPT", "Perplexity", "Gemini"],
        "implementationNotes": "Add FAQPage JSON-LD to any page with 3+ Q&A pairs. Each Question must have acceptedAnswer.text. Keep answers under 300 words and direct. Validate at schema.org/FAQPage.",
        "dependencies": [],
        "status": "not_started",
    },
    "add_article_author_schema": {
        "id": "add_article_author_schema",
        "title": "Add Article and Author (Person) Schema",
        "category": "schema",
        "scoreComponent": "schema",
        "description": "Implement Article schema on blog posts and content pages, linking each to a Person schema for the author with credentials and sameAs links.",
        "whyItMatters": "AI systems assess authorship to judge expertise and trustworthiness. Article + Person schema directly connects content to a credentialled real person, strengthening E-E-A-T signals.",
        "controlLevel": "direct",
        "difficultyLevel": "medium",
        "estimatedScoreImpact": "high",
        "timeHorizon": "near_term",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["Google AI Overviews", "Perplexity", "ChatGPT"],
        "implementationNotes": "On each article: add Article schema with author linking to a Person schema. Person should include name, jobTitle, knowsAbout, sameAs (LinkedIn, Twitter/X, Google Scholar if applicable). Author page URL should resolve to a real bio.",
        "dependencies": ["create_author_pages"],
        "status": "not_started",
    },
    "add_sameas_links": {
        "id": "add_sameas_links",
        "title": "Add sameAs Links to All Schema",
        "category": "schema",
        "scoreComponent": "schema",
        "description": "Ensure all Organization and Person schema blocks include comprehensive sameAs arrays pointing to authoritative third-party profiles.",
        "whyItMatters": "sameAs links are how AI systems build entity graphs. They connect your site to your Wikipedia page, Wikidata entry, LinkedIn profile, and other trusted sources — dramatically improving entity recognition accuracy.",
        "controlLevel": "direct",
        "difficultyLevel": "low",
        "estimatedScoreImpact": "medium",
        "timeHorizon": "immediate",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["ChatGPT", "Google AI Overviews", "Gemini", "Bing Copilot"],
        "implementationNotes": "Priority sameAs targets: Wikipedia, Wikidata, LinkedIn Company, Google Business Profile, YouTube channel, Twitter/X, Facebook, Crunchbase (if applicable), GitHub (if applicable). Use full canonical URLs.",
        "dependencies": ["add_organization_schema"],
        "status": "not_started",
    },
    "add_software_application_schema": {
        "id": "add_software_application_schema",
        "title": "Add SoftwareApplication Schema",
        "category": "schema",
        "scoreComponent": "schema",
        "description": "Implement SoftwareApplication schema to describe the product, its features, pricing model, and supported platforms.",
        "whyItMatters": "When someone asks an AI to recommend software tools in your category, SoftwareApplication schema gives AI systems structured data to extract — making your product more likely to appear in tool recommendations.",
        "controlLevel": "direct",
        "difficultyLevel": "low",
        "estimatedScoreImpact": "medium",
        "timeHorizon": "immediate",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["ChatGPT", "Perplexity", "Google AI Overviews"],
        "implementationNotes": "Required fields: name, applicationCategory, operatingSystem, offers (with price/priceCurrency or 'Free'), aggregateRating if you have reviews, featureList, screenshot.",
        "dependencies": ["add_organization_schema"],
        "status": "not_started",
    },
    "add_product_schema": {
        "id": "add_product_schema",
        "title": "Add Product Schema to Key Product Pages",
        "category": "schema",
        "scoreComponent": "schema",
        "description": "Add Product schema to product pages with full pricing, availability, and review data.",
        "whyItMatters": "AI shopping assistants use Product schema to surface products in recommendation responses. Without it, your products are much harder to feature in AI-generated buying guides.",
        "controlLevel": "direct",
        "difficultyLevel": "medium",
        "estimatedScoreImpact": "high",
        "timeHorizon": "near_term",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["Google AI Overviews", "ChatGPT", "Gemini"],
        "implementationNotes": "Required: name, image, description, sku, brand, offers (price, priceCurrency, availability), aggregateRating. Validate with Google Rich Results Test.",
        "dependencies": ["add_organization_schema"],
        "status": "not_started",
    },
    "add_website_searchaction_schema": {
        "id": "add_website_searchaction_schema",
        "title": "Add WebSite + SearchAction Schema",
        "category": "schema",
        "scoreComponent": "schema",
        "description": "Add a WebSite schema block with a SearchAction to enable sitelinks search box in Google.",
        "whyItMatters": "WebSite schema is primarily a Google Search feature (sitelinks search box). It has minimal direct impact on AI citation decisions but is a low-effort addition.",
        "controlLevel": "direct",
        "difficultyLevel": "low",
        "estimatedScoreImpact": "low",
        "timeHorizon": "near_term",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["Google AI Overviews", "Bing Copilot"],
        "implementationNotes": "Add to homepage only. SearchAction target URL should match your site's search URL pattern. Minimal additional effort if other schema is already in place.",
        "dependencies": ["add_organization_schema"],
        "status": "not_started",
    },
    "implement_ssr": {
        "id": "implement_ssr",
        "title": "Expose Content in Server-Rendered HTML",
        "category": "technical",
        "scoreComponent": "technical",
        "description": "Ensure all primary content — headlines, body copy, key facts, navigation — is present in the server-rendered HTML response, not dependent on JavaScript execution.",
        "whyItMatters": "AI crawlers generally do not execute JavaScript. Content that exists only in JS-rendered DOM — such as product descriptions, editorial text, or entire page sections — is not available to them. The severity depends on what specifically is missing from the server-rendered HTML; always verify before assuming all content is invisible.",
        "controlLevel": "direct",
        "difficultyLevel": "high",
        "estimatedScoreImpact": "very_high",
        "timeHorizon": "immediate",
        "peakwebFit": "direct_service",
        "isFoundational": True,
        "affectedPlatforms": ["ChatGPT", "Perplexity", "Claude", "Gemini", "Google AI Overviews", "Bing Copilot"],
        "implementationNotes": "Options by stack: Next.js → ensure pages use SSR or SSG (not client-only). React SPA → add SSR via Next.js migration or Astro. Vue → Nuxt.js. Angular → Angular Universal. Headless CMS → verify the rendering layer outputs HTML. Verify by running `curl -s <URL>` and checking what content is present in the raw HTML — note specifically what IS and ISN'T server-rendered.",
        "dependencies": [],
        "status": "not_started",
    },
    "restructure_content_answer_blocks": {
        "id": "restructure_content_answer_blocks",
        "title": "Restructure Key Pages with Direct Answer Blocks",
        "category": "content",
        "scoreComponent": "ai_citability",
        "description": "Rewrite or restructure core service/product pages so each major question a customer might ask is answered in a self-contained, direct paragraph of 100-200 words.",
        "whyItMatters": "AI systems extract passage-level content, not whole pages. They look for content that answers a question directly within a single readable block. Poorly structured pages with buried answers rarely get cited.",
        "controlLevel": "direct",
        "difficultyLevel": "medium",
        "estimatedScoreImpact": "high",
        "timeHorizon": "immediate",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["ChatGPT", "Perplexity", "Google AI Overviews", "Gemini"],
        "implementationNotes": "For each key page: identify the 3-5 questions a visitor/AI is trying to answer. Give each its own H2 or H3 subheading phrased as a question or clear statement. Write a 100-200 word answer block immediately below. Include one concrete fact, figure, or example per block.",
        "dependencies": [],
        "status": "not_started",
    },
    "create_author_pages": {
        "id": "create_author_pages",
        "title": "Create or Improve Author Bio Pages",
        "category": "content",
        "scoreComponent": "content_eeat",
        "description": "Build dedicated author biography pages for each person who writes or contributes content, including credentials, experience, and links to professional profiles.",
        "whyItMatters": "AI systems assessing expertise look for visible, credentialled authors. A faceless website looks untrustworthy. Author pages establish the human expertise behind your content and are a strong E-E-A-T signal.",
        "controlLevel": "direct",
        "difficultyLevel": "medium",
        "estimatedScoreImpact": "high",
        "timeHorizon": "near_term",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["Google AI Overviews", "Perplexity", "ChatGPT"],
        "implementationNotes": "Each author page should include: full name, photo, job title/role, credentials and certifications, years of experience, specific areas of expertise, links to LinkedIn and other professional profiles, and a list of authored content. Minimum 150 words of bio content.",
        "dependencies": [],
        "status": "not_started",
    },
    "create_original_research": {
        "id": "create_original_research",
        "title": "Publish Original Research, Data, or Case Studies",
        "category": "content",
        "scoreComponent": "content_eeat",
        "description": "Create at least one piece of proprietary research, industry data analysis, or detailed case study that third parties can cite.",
        "whyItMatters": "AI systems heavily weight original, citable data sources. Content that presents original findings gets cited far more often than content that summarises what others have said. This is one of the highest-leverage content investments possible.",
        "controlLevel": "direct",
        "difficultyLevel": "high",
        "estimatedScoreImpact": "high",
        "timeHorizon": "near_term",
        "peakwebFit": "advisory_only",
        "isFoundational": False,
        "affectedPlatforms": ["ChatGPT", "Perplexity", "Google AI Overviews"],
        "implementationNotes": "Starting points: survey your customers and publish results; analyse your own service/product data; document a real case study with before/after metrics. Make data findable: give it a dedicated URL, include schema markup (Dataset or Article), and promote it so others link to it.",
        "dependencies": ["create_author_pages"],
        "status": "not_started",
    },
    "claim_google_business_profile": {
        "id": "claim_google_business_profile",
        "title": "Claim and Optimise Google Business Profile",
        "category": "brand",
        "scoreComponent": "brand_authority",
        "description": "Claim, verify, and fully optimise the Google Business Profile listing with accurate NAP, photos, categories, products/services, and regular posts.",
        "whyItMatters": "Google Business Profile is a primary trust signal for Google AI Overviews and Gemini for local queries. It is also used as an authoritative data source by Bing Copilot. An unclaimed or incomplete profile is a significant visibility gap.",
        "controlLevel": "direct",
        "difficultyLevel": "low",
        "estimatedScoreImpact": "high",
        "timeHorizon": "immediate",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["Google AI Overviews", "Gemini", "Bing Copilot"],
        "implementationNotes": "At business.google.com: verify ownership, complete all fields (description, categories, attributes, hours, service area), upload 10+ photos, add all services/products, set up Q&A, enable messaging. Ongoing: respond to reviews, post updates monthly.",
        "dependencies": [],
        "status": "not_started",
    },
    "optimize_linkedin": {
        "id": "optimize_linkedin",
        "title": "Create or Optimise LinkedIn Company Page",
        "category": "brand",
        "scoreComponent": "brand_authority",
        "description": "Ensure there is an active, complete LinkedIn Company page with accurate description, industry, size, logo, and regular content posts.",
        "whyItMatters": "LinkedIn is one of the most-cited sources in AI training data for business information. Bing Copilot specifically weighs LinkedIn presence. An absent or sparse LinkedIn page is a notable trust gap for B2B and professional services businesses.",
        "controlLevel": "direct",
        "difficultyLevel": "low",
        "estimatedScoreImpact": "medium",
        "timeHorizon": "near_term",
        "peakwebFit": "advisory_only",
        "isFoundational": False,
        "affectedPlatforms": ["Bing Copilot", "ChatGPT", "Perplexity"],
        "implementationNotes": "Complete all fields: tagline, about section (minimum 500 characters), industry, company size, website URL. Upload logo and banner. Add all products/services. Post at minimum 2× per month. Encourage team members to link their profiles to the company page.",
        "dependencies": [],
        "status": "not_started",
    },
    "build_brand_citations": {
        "id": "build_brand_citations",
        "title": "Build Brand Citations and Third-Party Mentions",
        "category": "brand",
        "scoreComponent": "brand_authority",
        "description": "Proactively seek brand mentions and citations from relevant industry sites, directories, and media — places that AI training data draws from.",
        "whyItMatters": "AI systems use third-party mentions as a proxy for authority and trustworthiness. A brand mentioned positively across multiple independent sources is treated as more credible than one whose only voice is its own website.",
        "controlLevel": "mixed",
        "difficultyLevel": "high",
        "estimatedScoreImpact": "high",
        "timeHorizon": "near_term",
        "peakwebFit": "partner_referral",
        "isFoundational": False,
        "affectedPlatforms": ["ChatGPT", "Perplexity", "Google AI Overviews"],
        "implementationNotes": "Prioritise: relevant industry directories (paid and free), guest contributions to industry publications, podcast appearances, press releases for genuinely newsworthy events, partnerships with complementary businesses that mention each other. Quality over quantity — one mention on a respected site beats ten on low-quality directories.",
        "dependencies": [],
        "status": "not_started",
    },
    "build_reddit_presence": {
        "id": "build_reddit_presence",
        "title": "Build Genuine Reddit Presence",
        "category": "brand",
        "scoreComponent": "brand_authority",
        "description": "Participate in relevant subreddits through genuine, helpful contributions — not promotional posts. Establish brand name recognition in communities your customers frequent.",
        "whyItMatters": "Reddit is heavily weighted in AI training data, particularly for ChatGPT and Perplexity. Brands that appear in Reddit discussions in a helpful, non-promotional context are cited far more often in conversational AI responses.",
        "controlLevel": "mixed",
        "difficultyLevel": "medium",
        "estimatedScoreImpact": "medium",
        "timeHorizon": "near_term",
        "peakwebFit": "advisory_only",
        "isFoundational": False,
        "affectedPlatforms": ["ChatGPT", "Perplexity"],
        "implementationNotes": "Find the 3-5 subreddits where your ideal customers ask questions. Participate with substantive, helpful answers — never self-promotional. If appropriate, answer questions where your service/product is the genuine best answer, disclosed transparently. This is a long-term effort requiring consistency.",
        "dependencies": [],
        "status": "not_started",
    },
    "build_youtube_presence": {
        "id": "build_youtube_presence",
        "title": "Establish YouTube Presence",
        "category": "brand",
        "scoreComponent": "brand_authority",
        "description": "Create a YouTube channel with a consistent series of valuable videos relevant to your customers' questions and needs.",
        "whyItMatters": "YouTube is a significant source in AI training data, and Google AI Overviews and Gemini actively surface and cite YouTube content. Video presence also strengthens entity recognition and multiplies the surfaces where you can appear in AI responses.",
        "controlLevel": "mixed",
        "difficultyLevel": "high",
        "estimatedScoreImpact": "medium",
        "timeHorizon": "long_term",
        "peakwebFit": "advisory_only",
        "isFoundational": False,
        "affectedPlatforms": ["Google AI Overviews", "Gemini", "ChatGPT"],
        "implementationNotes": "Start with 6-10 videos answering the most common questions in your industry. Optimise titles and descriptions for the exact phrases your customers search. Add VideoObject schema to any page that embeds a YouTube video. Consistency matters more than production quality.",
        "dependencies": [],
        "status": "not_started",
    },
    "build_wikidata_entity": {
        "id": "build_wikidata_entity",
        "title": "Create a Wikidata Entity for the Business",
        "category": "brand",
        "scoreComponent": "brand_authority",
        "description": "Create or claim a Wikidata item for the business with accurate, cited data about the company, its location, founding, and key facts.",
        "whyItMatters": "Wikidata is a primary structured knowledge source for AI entity resolution. A Wikidata entry — even without a Wikipedia article — significantly improves how accurately AI systems identify and describe your business.",
        "controlLevel": "indirect",
        "difficultyLevel": "medium",
        "estimatedScoreImpact": "high",
        "timeHorizon": "near_term",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["ChatGPT", "Google AI Overviews", "Gemini"],
        "implementationNotes": "Create at wikidata.org/wiki/Special:NewItem. Required: instance of (Q4830453 for business), official name, official website, country, industry, founded date. Add as many cited facts as possible. Link back from your website's Organization sameAs. This is feasible for any business regardless of size.",
        "dependencies": ["add_sameas_links"],
        "status": "not_started",
    },
    "build_wikipedia_presence": {
        "id": "build_wikipedia_presence",
        "title": "Establish Wikipedia Presence",
        "category": "brand",
        "scoreComponent": "brand_authority",
        "description": "Work toward a notable Wikipedia article about the business or its founders — or contribute to existing relevant articles.",
        "whyItMatters": "Wikipedia is the single strongest trust signal for AI entity recognition. Businesses with Wikipedia articles are dramatically more likely to be cited accurately and confidently by AI systems. However, Wikipedia has strict notability requirements.",
        "controlLevel": "indirect",
        "difficultyLevel": "very_high",
        "estimatedScoreImpact": "very_high",
        "timeHorizon": "long_term",
        "peakwebFit": "advisory_only",
        "isFoundational": False,
        "affectedPlatforms": ["ChatGPT", "Google AI Overviews", "Gemini", "Perplexity"],
        "implementationNotes": "Notability criteria require significant third-party coverage. Prerequisites: substantive press coverage in recognised publications, industry recognition, or academic citations. Don't attempt to create an article without meeting notability criteria — it will be deleted and may harm your reputation with Wikipedia editors. Indirect approach: contribute to related Wikipedia articles where your business is genuinely relevant.",
        "dependencies": ["earn_press_coverage", "build_brand_citations"],
        "status": "not_started",
    },
    "earn_press_coverage": {
        "id": "earn_press_coverage",
        "title": "Earn Third-Party Press Coverage",
        "category": "brand",
        "scoreComponent": "brand_authority",
        "description": "Secure coverage in recognised industry publications, regional press, or national outlets through newsworthy stories, data releases, or expert commentary.",
        "whyItMatters": "Press coverage from recognised outlets is a prerequisite for Wikipedia notability and a strong independent signal of authority. AI systems trained on web data weight mentions in established publications significantly higher than self-published content.",
        "controlLevel": "indirect",
        "difficultyLevel": "high",
        "estimatedScoreImpact": "high",
        "timeHorizon": "long_term",
        "peakwebFit": "partner_referral",
        "isFoundational": False,
        "affectedPlatforms": ["ChatGPT", "Google AI Overviews", "Perplexity"],
        "implementationNotes": "Newsworthy angles: proprietary data/research, unusual business story, community impact, awards and recognition, significant milestones. Use HARO (Help a Reporter Out) or Qwoted for reactive PR. For proactive coverage, invest in a PR firm with relevant trade publication relationships.",
        "dependencies": [],
        "status": "not_started",
    },
    "improve_core_web_vitals": {
        "id": "improve_core_web_vitals",
        "title": "Improve Core Web Vitals",
        "category": "technical",
        "scoreComponent": "technical",
        "description": "Bring LCP under 2.5s, INP under 200ms, and CLS under 0.1 as measured by Google PageSpeed Insights.",
        "whyItMatters": "Core Web Vitals primarily affect Google crawl budget allocation. They do not directly influence whether AI systems cite your content, but very slow pages may be deprioritised in crawl queues.",
        "controlLevel": "direct",
        "difficultyLevel": "medium",
        "estimatedScoreImpact": "low",
        "timeHorizon": "near_term",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["Google AI Overviews", "Gemini"],
        "implementationNotes": "Run PageSpeed Insights at pagespeed.web.dev. Biggest wins: optimise and compress images (convert to WebP), defer non-critical JS, preload LCP image, eliminate layout-shift-causing resources (fonts, ads). For WordPress: use a caching plugin (WP Rocket) and a CDN.",
        "dependencies": [],
        "status": "not_started",
    },
    "improve_bing_coverage": {
        "id": "improve_bing_coverage",
        "title": "Improve Bing Index Coverage and Webmaster Tools",
        "category": "platform",
        "scoreComponent": "platform_optimization",
        "description": "Submit the sitemap to Bing Webmaster Tools, verify the site, and ensure key pages are indexed by Bing.",
        "whyItMatters": "Bing Copilot draws on Bing's index. Many businesses focus exclusively on Google and are poorly indexed in Bing, making them invisible to Bing Copilot users — a significant and growing AI audience.",
        "controlLevel": "direct",
        "difficultyLevel": "low",
        "estimatedScoreImpact": "medium",
        "timeHorizon": "near_term",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["Bing Copilot"],
        "implementationNotes": "Sign up at bing.com/webmasters. Verify site ownership. Submit XML sitemap. Use URL Inspection to check indexing of key pages. Check for crawl errors. Bing also accepts IndexNow notifications for fast indexing of new/updated content.",
        "dependencies": [],
        "status": "not_started",
    },
    "optimize_mobile": {
        "id": "optimize_mobile",
        "title": "Ensure Mobile Responsiveness",
        "category": "technical",
        "scoreComponent": "technical",
        "description": "Verify the site renders correctly and is fully usable on mobile devices, with appropriate viewport settings and touch-friendly interfaces.",
        "whyItMatters": "AI crawlers often use mobile user-agent strings. A non-responsive site degrades the crawled content quality and signals poor technical health.",
        "controlLevel": "direct",
        "difficultyLevel": "low",
        "estimatedScoreImpact": "medium",
        "timeHorizon": "near_term",
        "peakwebFit": "direct_service",
        "isFoundational": False,
        "affectedPlatforms": ["Google AI Overviews", "Gemini"],
        "implementationNotes": "Test at search.google.com/test/mobile-friendly. Check viewport meta tag is present. Ensure tap targets are at least 48x48px. No horizontal scrolling at 375px width. Images scale to container width.",
        "dependencies": [],
        "status": "not_started",
    },
}


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def detect_platform_from_html(html_content: str) -> str:
    """
    Infer the site's CMS/platform from homepage HTML.
    Returns one of: 'wordpress', 'shopify', 'wix', 'squarespace', 'webflow', 'unknown'.
    Best-effort — uncertainty is handled by returning 'unknown'.
    """
    if not html_content:
        return "unknown"
    h = html_content.lower()

    # WordPress: generator meta tag or wp-content paths
    if 'name="generator" content="wordpress' in h or '/wp-content/' in h or '/wp-json/' in h:
        return "wordpress"

    # Shopify: CDN references
    if 'cdn.shopify.com' in h or 'shopify.com/s/' in h:
        return "shopify"

    # Wix: static asset CDN
    if 'static.wixstatic.com' in h or 'wix.com' in h:
        return "wix"

    # Squarespace
    if 'squarespace.com' in h or 'static1.squarespace.com' in h:
        return "squarespace"

    # Webflow
    if 'webflow.com' in h or 'assets-global.website-files.com' in h:
        return "webflow"

    return "unknown"


PLATFORM_NOTES = {
    "wordpress": {
        "add_organization_schema": "Implement via Rank Math Pro (Structured Data > Schema > Organization) or a custom JSON-LD snippet in functions.php or a plugin like WP Code.",
        "add_local_business_schema": "Use Rank Math's Local SEO module or the Schema & Structured Data for WP plugin. Alternatively, inject JSON-LD directly in the theme's header.php.",
        "add_faq_schema": "Rank Math auto-generates FAQPage schema when you use its FAQ block in the Gutenberg editor. Alternatively, use the Yoast FAQ block.",
        "publish_llms_txt": "Upload the llms.txt file to your server root via FTP/SFTP or cPanel File Manager. Alternatively, use a plugin like Custom Permalinks or a page at /llms.txt with no template.",
        "implement_ssr": "WordPress already renders server-side. If the site uses a JS-heavy theme or custom React front-end, evaluate whether that layer can be replaced with standard WP templates.",
        "improve_core_web_vitals": "Install WP Rocket or LiteSpeed Cache. Use Imagify or ShortPixel for image optimisation. Consider a CDN such as Cloudflare.",
    },
    "shopify": {
        "add_organization_schema": "Add JSON-LD to theme.liquid inside the <head> tag. Use Shopify's Liquid variables for dynamic values ({{ shop.name }}, {{ shop.url }}).",
        "add_local_business_schema": "Inject LocalBusiness JSON-LD in theme.liquid or use a Shopify app such as JSON-LD for SEO.",
        "add_faq_schema": "Add FAQPage JSON-LD to FAQ pages in theme.liquid or use a structured data app from the Shopify App Store.",
        "publish_llms_txt": "Create a Shopify page with handle 'llms-txt' and add a URL redirect /llms.txt → /pages/llms-txt, or use a file upload app.",
        "add_product_schema": "Shopify generates basic Product schema automatically. Enhance it via theme.liquid product template or a schema app for richer data (aggregateRating, brand, etc.).",
    },
    "wix": {
        "add_organization_schema": "Use Wix's built-in structured data settings under SEO > Structured Data Markup, or add JSON-LD via Wix Velo (custom code).",
        "add_local_business_schema": "Wix has limited built-in LocalBusiness schema. Use Wix Velo to inject JSON-LD, or use a third-party SEO app from the Wix App Market.",
        "publish_llms_txt": "Upload via Wix Dashboard > Media Manager, then create a page redirect. Note: Wix's URL handling may require a support workaround for /llms.txt.",
        "implement_ssr": "Wix renders server-side for standard pages. If using Wix Velo client-side rendering, ensure key content is in static page elements, not dynamic JS-only components.",
    },
    "squarespace": {
        "add_organization_schema": "Inject JSON-LD via Settings > Advanced > Code Injection > Header. Use this for all JSON-LD additions on Squarespace.",
        "publish_llms_txt": "Squarespace does not support arbitrary file uploads at root. Upload via Settings > Advanced > Code Injection, or consider hosting llms.txt on a subdomain or CDN and redirecting.",
        "implement_ssr": "Squarespace is server-rendered. If using Third-party JS blocks extensively, audit which content is in static vs dynamic blocks.",
    },
    "webflow": {
        "add_organization_schema": "Add JSON-LD in Project Settings > Custom Code > Head Code. For per-page schema, use Page Settings > Custom Code on each page.",
        "publish_llms_txt": "Upload to Webflow Hosting via the Assets panel or inject content via a Custom Code Embed block on a dedicated /llms-txt page with a 301 redirect.",
        "implement_ssr": "Webflow is server-rendered. If using Webflow's JS interactions or third-party tools that inject content client-side, review which elements are visible in page source.",
    },
}


def _get_platform_note(action_id: str, platform: str) -> str:
    """Return a platform-specific implementation note, or empty string."""
    return PLATFORM_NOTES.get(platform, {}).get(action_id, "")


# ---------------------------------------------------------------------------
# Business type detection
# ---------------------------------------------------------------------------

def detect_business_type_from_audit(audit_text: str) -> str:
    """
    Infer business type from audit report text.
    Returns: 'local' | 'saas' | 'ecommerce' | 'publisher' | 'agency' | 'unknown'
    """
    if not audit_text:
        return "unknown"
    t = audit_text.lower()

    # Direct labels from audit reports
    if re.search(r"business type[:\s]+local", t) or "local service" in t:
        return "local"
    if re.search(r"business type[:\s]+saas", t) or "software as a service" in t:
        return "saas"
    if re.search(r"business type[:\s]+e.?commerce", t) or "e-commerce" in t or "ecommerce" in t:
        return "ecommerce"
    if re.search(r"business type[:\s]+publisher", t) or "publishing" in t:
        return "publisher"
    if re.search(r"business type[:\s]+agency", t) or "marketing agency" in t:
        return "agency"

    # Heuristic signals
    if re.search(r"\b(plumber|dentist|lawyer|restaurant|salon|clinic|gym|contractor|electrician)\b", t):
        return "local"
    if re.search(r"\b(saas|subscription|free trial|sign up|dashboard|api)\b", t):
        return "saas"
    if re.search(r"\b(add to cart|checkout|product page|shopify|woocommerce)\b", t):
        return "ecommerce"

    return "unknown"


# ---------------------------------------------------------------------------
# Audit findings parser
# ---------------------------------------------------------------------------

def _read_file_safe(path: str) -> str:
    """Read a file, returning empty string on any error."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, IOError):
        return ""


def _extract_score(text: str, label: str) -> int:
    """
    Try to extract a numeric score (0-100) associated with a label.
    Returns -1 if not found.
    """
    patterns = [
        rf"{re.escape(label)}[:\s]+(\d{{1,3}})/100",
        rf"{re.escape(label)}[:\s]+(\d{{1,3}})\b",
        rf"\|\s*{re.escape(label)}\s*\|\s*(\d{{1,3}})\s*\|",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 0 <= val <= 100:
                return val
    return -1


def parse_audit_findings(audit_dir: str) -> dict:
    """
    Read all GEO-*.md and related audit files in audit_dir.
    Returns a structured findings dict for use by map_findings_to_actions().

    All fields have safe defaults so the generator works even with partial audits.
    """
    # Load available files
    crawler_text = _read_file_safe(os.path.join(audit_dir, "GEO-CRAWLER-ACCESS.md"))
    schema_text = _read_file_safe(os.path.join(audit_dir, "GEO-SCHEMA-REPORT.md"))
    brand_text = _read_file_safe(os.path.join(audit_dir, "GEO-BRAND-MENTIONS.md"))
    technical_text = _read_file_safe(os.path.join(audit_dir, "GEO-TECHNICAL-AUDIT.md"))
    content_text = _read_file_safe(os.path.join(audit_dir, "GEO-CONTENT-ANALYSIS.md"))
    audit_text = _read_file_safe(os.path.join(audit_dir, "GEO-AUDIT-REPORT.md"))
    client_text = _read_file_safe(os.path.join(audit_dir, "CLIENT-REPORT.md"))
    llmstxt_text = _read_file_safe(os.path.join(audit_dir, "llms.txt"))

    all_text = "\n".join([crawler_text, schema_text, brand_text, technical_text,
                          content_text, audit_text, client_text])

    # --- Crawler access ---
    blocked_crawlers = []
    for bot in ["GPTBot", "ClaudeBot", "PerplexityBot", "CCBot", "Applebot-Extended", "anthropic-ai"]:
        blocked_pattern = rf"\|\s*{re.escape(bot)}\s*\|[^|]*[Bb]lock"
        if re.search(blocked_pattern, crawler_text) or (
            bot.lower() in crawler_text.lower() and "block" in crawler_text.lower()
            and bot.lower() in crawler_text[max(0, crawler_text.lower().find(bot.lower())-10):
                                            crawler_text.lower().find(bot.lower())+50].lower()
        ):
            blocked_crawlers.append(bot)

    # Fallback: if crawler text mentions "blocked" or "disallow" broadly
    if not blocked_crawlers and re.search(r"(blocked|disallow).{0,60}(GPTBot|ClaudeBot|PerplexityBot|AI crawler)", all_text, re.IGNORECASE):
        blocked_crawlers = ["GPTBot"]  # conservative default

    # --- llms.txt ---
    has_llms_txt = bool(llmstxt_text.strip()) or bool(
        re.search(r"llms\.txt.{0,100}(found|present|exists|valid)", all_text, re.IGNORECASE)
    )
    # Negative signal overrides
    if re.search(r"(no|missing|not found).{0,30}llms\.txt", all_text, re.IGNORECASE):
        has_llms_txt = False

    # --- Schema types ---
    schema_lower = schema_text.lower() + audit_text.lower()
    schema_types_present = []
    for stype in ["organization", "localbusiness", "faqpage", "article", "person",
                  "product", "softwareapplication", "website", "breadcrumb", "review"]:
        if stype in schema_lower:
            schema_types_present.append(stype)

    has_local_business_schema = "localbusiness" in schema_lower and not bool(
        re.search(r"(missing|no|absent).{0,30}localbusiness", schema_lower, re.IGNORECASE)
    )
    has_organization_schema = "organization" in schema_lower and not bool(
        re.search(r"(missing|no|absent).{0,30}organization", schema_lower, re.IGNORECASE)
    )
    has_faq_schema = "faqpage" in schema_lower
    has_article_schema = "article" in schema_lower

    has_sameas_links = bool(
        re.search(r"sameas", schema_lower) and
        not re.search(r"(missing|no|absent).{0,30}sameas", schema_lower, re.IGNORECASE)
    )

    # --- Technical: SSR / JS heavy ---
    is_js_heavy = bool(
        re.search(r"(js.only|javascript.only|client.side rendering|no ssr|content.hidden.behind.js|"
                  r"js.rendered|react spa|spa without ssr|single.page app)", all_text, re.IGNORECASE)
    )
    has_ssr = bool(
        re.search(r"(server.side rendering|ssr|server.rendered|static html)", all_text, re.IGNORECASE)
    ) and not is_js_heavy

    # Core Web Vitals issues
    has_cwv_issues = bool(
        re.search(r"(lcp|fid|cls|inp|core web vitals).{0,100}(poor|fail|needs improvement|slow)",
                  all_text, re.IGNORECASE)
    )

    # Mobile
    has_mobile_issues = bool(
        re.search(r"(mobile.{0,30}(issue|fail|problem|not responsive)|not mobile.friendly)",
                  all_text, re.IGNORECASE)
    )

    # --- Brand / authority signals ---
    wikipedia_present = bool(
        re.search(r"wikipedia.{0,50}(found|present|exists|yes|✓|✅)", all_text, re.IGNORECASE)
    ) and not bool(
        re.search(r"(no|missing|not found).{0,30}wikipedia", all_text, re.IGNORECASE)
    )

    wikidata_present = bool(
        re.search(r"wikidata.{0,50}(found|present|yes|✓|✅)", all_text, re.IGNORECASE)
    )

    linkedin_score = _extract_score(brand_text + audit_text, "linkedin")
    if linkedin_score < 0:
        linkedin_score = 0 if re.search(r"(no|missing|weak).{0,20}linkedin", all_text, re.IGNORECASE) else 50

    reddit_score = _extract_score(brand_text + audit_text, "reddit")
    if reddit_score < 0:
        reddit_score = 0 if re.search(r"(no|weak|minimal).{0,20}reddit", all_text, re.IGNORECASE) else 40

    youtube_score = _extract_score(brand_text + audit_text, "youtube")
    if youtube_score < 0:
        youtube_score = 0 if re.search(r"(no|weak|minimal).{0,20}youtube", all_text, re.IGNORECASE) else 40

    has_google_business_profile = bool(
        re.search(r"google business profile.{0,50}(found|present|claimed|verified|yes)",
                  all_text, re.IGNORECASE)
    )

    # --- Content quality ---
    has_author_pages = bool(
        re.search(r"author (page|bio|profile).{0,50}(found|present|yes|✓|✅)", all_text, re.IGNORECASE)
    ) and not bool(
        re.search(r"(no|missing).{0,20}author (page|bio)", all_text, re.IGNORECASE)
    )

    has_original_research = bool(
        re.search(r"(original research|case stud|proprietary data|survey results)",
                  all_text, re.IGNORECASE)
    )

    answer_block_quality = "weak"
    if re.search(r"answer block.{0,50}(strong|excellent|good)", all_text, re.IGNORECASE):
        answer_block_quality = "strong"
    elif re.search(r"answer block.{0,50}(moderate|fair|partial)", all_text, re.IGNORECASE):
        answer_block_quality = "moderate"

    # Bing coverage
    has_bing_issues = bool(
        re.search(r"(bing.{0,30}(not indexed|missing|weak|poor)|poor bing)", all_text, re.IGNORECASE)
    )

    # --- Scores ---
    geo_score = _extract_score(all_text, "GEO Score")
    if geo_score < 0:
        geo_score = _extract_score(all_text, "Overall")
    if geo_score < 0:
        geo_score = 50  # unknown default

    category_scores = {
        "ai_citability": max(0, _extract_score(all_text, "AI Citability") if _extract_score(all_text, "AI Citability") >= 0 else 50),
        "brand_authority": max(0, _extract_score(all_text, "Brand Authority") if _extract_score(all_text, "Brand Authority") >= 0 else 50),
        "content_eeat": max(0, _extract_score(all_text, "E-E-A-T") if _extract_score(all_text, "E-E-A-T") >= 0 else 50),
        "technical": max(0, _extract_score(all_text, "Technical") if _extract_score(all_text, "Technical") >= 0 else 50),
        "schema": max(0, _extract_score(all_text, "Schema") if _extract_score(all_text, "Schema") >= 0 else 50),
        "platform_optimization": max(0, _extract_score(all_text, "Platform") if _extract_score(all_text, "Platform") >= 0 else 50),
    }

    # --- Business type and brand name ---
    business_type = detect_business_type_from_audit(all_text)

    brand_name = ""
    for pattern in [r"(?:brand|company|client|business)[:\s]+([A-Z][^\n,|]{2,50})",
                    r"# GEO.+?—\s*([^\n]+)"]:
        m = re.search(pattern, all_text)
        if m:
            brand_name = m.group(1).strip()
            break

    url = ""
    m = re.search(r"https?://[^\s|\"'<>]+", all_text)
    if m:
        url = m.group(0).strip(".,)")

    return {
        "has_llms_txt": has_llms_txt,
        "blocked_crawlers": blocked_crawlers,
        "schema_types_present": schema_types_present,
        "has_local_business_schema": has_local_business_schema,
        "has_organization_schema": has_organization_schema,
        "has_faq_schema": has_faq_schema,
        "has_article_schema": has_article_schema,
        "has_sameas_links": has_sameas_links,
        "is_js_heavy": is_js_heavy,
        "has_ssr": has_ssr,
        "has_cwv_issues": has_cwv_issues,
        "has_mobile_issues": has_mobile_issues,
        "has_author_pages": has_author_pages,
        "wikipedia_present": wikipedia_present,
        "wikidata_present": wikidata_present,
        "linkedin_score": linkedin_score,
        "reddit_score": reddit_score,
        "youtube_score": youtube_score,
        "has_google_business_profile": has_google_business_profile,
        "has_original_research": has_original_research,
        "answer_block_quality": answer_block_quality,
        "has_bing_issues": has_bing_issues,
        "geo_score": geo_score,
        "category_scores": category_scores,
        "business_type": business_type,
        "brand_name": brand_name,
        "url": url,
        "platform": "unknown",  # populated later from HTML if available
    }


# ---------------------------------------------------------------------------
# Priority scoring
# ---------------------------------------------------------------------------

def compute_priority_score(item: dict) -> int:
    """
    Compute a 0-100 priority score for a single action item.
    Higher = act sooner. Fully deterministic.

    Tune behaviour by adjusting PRIORITY_WEIGHTS at the top of this file.
    """
    w = PRIORITY_WEIGHTS
    raw = 0

    raw += w["impact"].get(item.get("estimatedScoreImpact", "low"), 0)
    raw += w["control"].get(item.get("controlLevel", "indirect"), 0)
    raw += w["speed"].get(item.get("timeHorizon", "long_term"), 0)
    raw += w["difficulty_penalty"].get(item.get("difficultyLevel", "low"), 0)

    if item.get("isFoundational", False):
        raw += w["foundational_bonus"]

    if len(item.get("affectedPlatforms", [])) >= 3:
        raw += w["multi_platform_bonus"]

    if item.get("peakwebFit") == "direct_service":
        raw += w["peakweb_bonus"]

    # Normalise to 0-100
    score = round((max(0, raw) / w["raw_max"]) * 100)
    return min(100, max(0, score))


# ---------------------------------------------------------------------------
# Finding rules → action items
# ---------------------------------------------------------------------------

# Customer-specific recommendation templates
# {business_type} → tailored copy; falls back to generic
_CUSTOMER_RECS: dict[str, dict[str, str]] = {
    "unblock_ai_crawlers": {
        "_default": "Review your robots.txt file immediately. Remove Disallow rules for GPTBot, ClaudeBot, PerplexityBot, and CCBot. This is typically a 5-minute edit with very high impact.",
        "local": "Review your robots.txt and remove AI crawler blocks. For a local business, AI visibility directly affects whether customers who ask an AI assistant for recommendations find you.",
        "saas": "Remove AI crawler blocks from robots.txt. SaaS tools are frequently recommended by AI assistants — being blocked means you're absent from those recommendations entirely.",
    },
    "publish_llms_txt": {
        "_default": "Create an llms.txt file at your site root. This takes under an hour and immediately improves how AI systems understand and describe your business.",
        "local": "An llms.txt file lets AI systems quickly understand your service area, specialties, and key pages — directly relevant when they recommend local services to users.",
        "saas": "An llms.txt file is especially valuable for SaaS products, giving AI tools a structured description of your features and use cases to reference when recommending tools.",
    },
    "add_local_business_schema": {
        "_default": "Add LocalBusiness schema with your full address, phone, hours, and service area. This is one of the highest-impact schema additions for any location-based business.",
        "local": "Add LocalBusiness schema immediately. This directly supports how Google AI Overviews and Gemini surface local service providers when users ask for recommendations near them.",
    },
    "add_organization_schema": {
        "_default": "Add Organization schema with your business name, URL, logo, and sameAs links to your LinkedIn, Google Business Profile, and any other authoritative profiles.",
    },
    "implement_ssr": {
        "_default": "Ensure your primary page content — headlines, body copy, key facts — is present in the HTML that the server sends, before any JavaScript runs. Test by viewing page source (Cmd+U in browser).",
        "saas": "For a SaaS product, it's especially important that your feature descriptions, pricing, and key value propositions appear in server-rendered HTML so AI tools can accurately describe your product.",
    },
    "restructure_content_answer_blocks": {
        "_default": "Rewrite your most important service/product pages so each key question gets its own section with a direct, factual answer paragraph of 100-200 words.",
        "local": "Rewrite your service pages so each service has a clear, direct section answering: what is it, who needs it, how much does it cost, and why choose you. These answer blocks are exactly what AI systems extract.",
        "saas": "Structure your features and use-case pages with direct answer blocks for the questions your buyers ask: what does it do, how does it compare, what's the pricing, who uses it.",
    },
    "create_author_pages": {
        "_default": "Create bio pages for each person who creates content on your site. Include credentials, experience, and links to professional profiles.",
        "saas": "Add author bios linking to LinkedIn profiles for all blog and resource content. Technical buyers rely on author credibility, and AI systems use it to assess expertise.",
        "publisher": "Comprehensive author profiles are essential for a publisher. Include writing specialisations, credentials, experience, and links to Google Scholar or professional publications where applicable.",
    },
    "build_wikidata_entity": {
        "_default": "Create a Wikidata item for your business at wikidata.org. Unlike Wikipedia, Wikidata has no notability requirements — any business can have an entry — and it significantly improves AI entity recognition.",
    },
    "build_wikipedia_presence": {
        "_default": "Building a Wikipedia presence is a long-term, high-impact goal. Prerequisites are significant third-party press coverage. Focus first on earning that coverage, then revisit Wikipedia. Do not attempt a Wikipedia article prematurely — it will be deleted and may flag your business to editors.",
    },
    "claim_google_business_profile": {
        "_default": "If you haven't already claimed and verified your Google Business Profile, do this first. It's free, takes 1-2 weeks to verify, and has immediate impact on local AI recommendations.",
        "local": "A claimed, complete Google Business Profile is foundational for any local business. It is a primary data source for Google AI Overviews and Gemini when answering 'near me' queries.",
    },
    "optimize_linkedin": {
        "_default": "Ensure your LinkedIn Company Page is complete, accurate, and updated. This is a direct Bing Copilot ranking factor and an important entity signal for other AI platforms.",
        "saas": "A complete LinkedIn Company Page is important for SaaS businesses — your target buyers likely use LinkedIn and AI tools trained on LinkedIn data are more likely to surface businesses with strong profiles.",
        "agency": "Agency clients and AI tools alike look for LinkedIn presence as a trust signal. Ensure your page includes your full service offering, client industries, and case study links.",
    },
    "improve_bing_coverage": {
        "_default": "Set up Bing Webmaster Tools and submit your sitemap. With Bing Copilot growing in usage, Bing index coverage is increasingly important.",
    },
}


def _get_customer_rec(action_id: str, business_type: str) -> str:
    recs = _CUSTOMER_RECS.get(action_id, {})
    return recs.get(business_type) or recs.get("_default") or ""


def map_findings_to_actions(findings: dict) -> list:
    """
    Apply deterministic rules to convert audit findings into a list of action items.
    Each rule either includes or excludes a catalog item based on the findings.
    Items not triggered by findings are omitted — the roadmap only surfaces relevant actions.
    """
    actions = []
    bt = findings.get("business_type", "unknown")

    def include(action_id: str, evidence: str, source_finding: str = ""):
        """Copy catalog item and add contextual fields."""
        if action_id not in ACTION_CATALOG:
            return
        item = copy.deepcopy(ACTION_CATALOG[action_id])
        item["evidence"] = evidence
        item["sourceFinding"] = source_finding
        item["customerSpecificRecommendation"] = _get_customer_rec(action_id, bt)
        item["priorityScore"] = compute_priority_score(item)
        item["status"] = "not_started"
        actions.append(item)

    # --- TECHNICAL ---
    if findings.get("blocked_crawlers"):
        bots = ", ".join(findings["blocked_crawlers"])
        include("unblock_ai_crawlers",
                evidence=f"Blocked bots detected: {bots}",
                source_finding="GEO-CRAWLER-ACCESS.md: blocked AI crawlers")

    if findings.get("is_js_heavy") and not findings.get("has_ssr"):
        include("implement_ssr",
                evidence="Audit detected content rendered client-side only (JS-heavy); primary content not in server HTML.",
                source_finding="GEO-TECHNICAL-AUDIT.md: SSR not detected")

    if findings.get("has_cwv_issues"):
        include("improve_core_web_vitals",
                evidence="Core Web Vitals metrics are below recommended thresholds.",
                source_finding="GEO-TECHNICAL-AUDIT.md: Core Web Vitals issues")

    if findings.get("has_mobile_issues"):
        include("optimize_mobile",
                evidence="Mobile responsiveness issues detected.",
                source_finding="GEO-TECHNICAL-AUDIT.md: mobile issues")

    # --- SCHEMA ---
    if not findings.get("has_llms_txt"):
        include("publish_llms_txt",
                evidence="No llms.txt file found at site root.",
                source_finding="GEO-CRAWLER-ACCESS.md / llms.txt: not found")

    if not findings.get("has_organization_schema"):
        include("add_organization_schema",
                evidence="No Organization schema detected in crawled pages.",
                source_finding="GEO-SCHEMA-REPORT.md: Organization schema absent")

    if not findings.get("has_local_business_schema") and bt == "local":
        include("add_local_business_schema",
                evidence="No LocalBusiness schema detected; site appears to serve a local area.",
                source_finding="GEO-SCHEMA-REPORT.md: LocalBusiness schema absent")

    if not findings.get("has_faq_schema"):
        include("add_faq_schema",
                evidence="No FAQPage schema detected.",
                source_finding="GEO-SCHEMA-REPORT.md: FAQPage schema absent")

    if not findings.get("has_article_schema") and bt in ("publisher", "saas", "agency"):
        include("add_article_author_schema",
                evidence="No Article/Author schema detected on content pages.",
                source_finding="GEO-SCHEMA-REPORT.md: Article schema absent")

    if not findings.get("has_sameas_links"):
        include("add_sameas_links",
                evidence="Organization/Person schema lacks sameAs links to authoritative profiles.",
                source_finding="GEO-SCHEMA-REPORT.md: sameAs links missing")

    if bt == "saas" and "softwareapplication" not in findings.get("schema_types_present", []):
        include("add_software_application_schema",
                evidence="No SoftwareApplication schema detected on a SaaS site.",
                source_finding="GEO-SCHEMA-REPORT.md: SoftwareApplication schema absent")

    if bt == "ecommerce" and "product" not in findings.get("schema_types_present", []):
        include("add_product_schema",
                evidence="No Product schema detected on an e-commerce site.",
                source_finding="GEO-SCHEMA-REPORT.md: Product schema absent")

    if "website" not in findings.get("schema_types_present", []):
        include("add_website_searchaction_schema",
                evidence="No WebSite schema with SearchAction detected.",
                source_finding="GEO-SCHEMA-REPORT.md: WebSite schema absent")

    # --- CONTENT ---
    if findings.get("answer_block_quality") in ("weak", "moderate"):
        include("restructure_content_answer_blocks",
                evidence=f"Answer block quality rated '{findings.get('answer_block_quality')}'. Content is not structured for AI passage extraction.",
                source_finding="GEO-CONTENT-ANALYSIS.md: weak answer block structure")

    if not findings.get("has_author_pages"):
        include("create_author_pages",
                evidence="No visible author bio pages found.",
                source_finding="GEO-CONTENT-ANALYSIS.md: author pages absent")

    if not findings.get("has_original_research"):
        include("create_original_research",
                evidence="No original research, surveys, or detailed case studies detected.",
                source_finding="GEO-CONTENT-ANALYSIS.md: no original data")

    # --- BRAND ---
    if not findings.get("has_google_business_profile") and bt == "local":
        include("claim_google_business_profile",
                evidence="Google Business Profile not detected or not claimed.",
                source_finding="GEO-BRAND-MENTIONS.md: no Google Business Profile")

    if findings.get("linkedin_score", 0) < 40:
        include("optimize_linkedin",
                evidence=f"LinkedIn presence score: {findings.get('linkedin_score', 0)}/100.",
                source_finding="GEO-BRAND-MENTIONS.md: weak LinkedIn presence")

    if not findings.get("wikidata_present"):
        include("build_wikidata_entity",
                evidence="No Wikidata entity found for this business.",
                source_finding="GEO-BRAND-MENTIONS.md: no Wikidata entry")

    if findings.get("reddit_score", 0) < 30:
        include("build_reddit_presence",
                evidence=f"Reddit presence score: {findings.get('reddit_score', 0)}/100.",
                source_finding="GEO-BRAND-MENTIONS.md: minimal Reddit presence")

    # Brand citations: trigger if brand score is generally weak
    brand_score = findings.get("category_scores", {}).get("brand_authority", 50)
    if brand_score < 50:
        include("build_brand_citations",
                evidence=f"Brand Authority score: {brand_score}/100. Insufficient third-party mentions.",
                source_finding="GEO-BRAND-MENTIONS.md: weak brand citations")

    if findings.get("youtube_score", 0) < 20:
        include("build_youtube_presence",
                evidence=f"YouTube presence score: {findings.get('youtube_score', 0)}/100.",
                source_finding="GEO-BRAND-MENTIONS.md: no YouTube presence")

    if not findings.get("wikipedia_present"):
        include("build_wikipedia_presence",
                evidence="No Wikipedia article found for this business.",
                source_finding="GEO-BRAND-MENTIONS.md: no Wikipedia presence")

    if not findings.get("wikipedia_present") and brand_score < 60:
        include("earn_press_coverage",
                evidence="No Wikipedia presence and weak brand authority suggest insufficient third-party coverage.",
                source_finding="GEO-BRAND-MENTIONS.md: insufficient press coverage")

    if findings.get("has_bing_issues"):
        include("improve_bing_coverage",
                evidence="Bing index coverage issues detected.",
                source_finding="GEO-TECHNICAL-AUDIT.md: Bing coverage weak")

    # Deduplicate (edge case: multiple rules could include the same item)
    seen_ids = set()
    unique_actions = []
    for action in actions:
        if action["id"] not in seen_ids:
            seen_ids.add(action["id"])
            unique_actions.append(action)

    return unique_actions


# ---------------------------------------------------------------------------
# Platform context enrichment
# ---------------------------------------------------------------------------

def enrich_with_platform_context(action_items: list, findings: dict) -> list:
    """
    Add platform-specific implementation notes to each action item based on
    the detected CMS/platform.
    """
    platform = findings.get("platform", "unknown")
    if platform == "unknown":
        return action_items

    for item in action_items:
        note = _get_platform_note(item["id"], platform)
        if note:
            item["platformSpecificNotes"] = note

    return action_items


# ---------------------------------------------------------------------------
# Sorting / ranking
# ---------------------------------------------------------------------------

def rank_action_items(action_items: list) -> list:
    """
    Sort action items by priority_score descending.
    Ties broken by: foundational first, then direct control first, then low difficulty first.
    """
    control_order = {"direct": 0, "mixed": 1, "indirect": 2}
    difficulty_order = {"low": 0, "medium": 1, "high": 2, "very_high": 3}

    def sort_key(item):
        return (
            -item.get("priorityScore", 0),
            0 if item.get("isFoundational") else 1,
            control_order.get(item.get("controlLevel", "indirect"), 2),
            difficulty_order.get(item.get("difficultyLevel", "low"), 0),
        )

    return sorted(action_items, key=sort_key)


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

SCORE_LABELS = {
    (90, 100): "Excellent",
    (75, 89): "Good",
    (60, 74): "Fair",
    (40, 59): "Poor",
    (0, 39): "Critical",
}

IMPACT_ICONS = {"very_high": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}
CONTROL_LABELS = {"direct": "Direct control", "mixed": "Partial control", "indirect": "Indirect / earned"}
PEAKWEB_LABELS = {
    "direct_service": "Peakweb can implement",
    "partner_referral": "Partner / specialist",
    "advisory_only": "Client / team",
}
HORIZON_LABELS = {"immediate": "Immediate", "near_term": "Near-term (1-3 months)", "long_term": "Long-term (3+ months)"}


def _score_label(score: int) -> str:
    for (lo, hi), label in SCORE_LABELS.items():
        if lo <= score <= hi:
            return label
    return "Unknown"


def _fmt_difficulty(d: str) -> str:
    return {"low": "Low", "medium": "Medium", "high": "High", "very_high": "Very High"}.get(d, d)


def _fmt_impact(i: str) -> str:
    return {"low": "Low", "medium": "Medium", "high": "High", "very_high": "Very High"}.get(i, i)


def generate_roadmap_markdown(action_items: list, findings: dict) -> str:
    """
    Produce the full GEO-ROADMAP.md content from ranked action items + findings.
    The executive summary section is intentionally left as a placeholder for the
    skill's LLM layer to fill in with tailored prose.
    """
    brand = findings.get("brand_name") or "Your Business"
    url = findings.get("url") or ""
    geo_score = findings.get("geo_score", 0)
    score_label = _score_label(geo_score)
    today = date.today().strftime("%B %d, %Y")
    bt = findings.get("business_type", "unknown")
    platform = findings.get("platform", "unknown")

    quick_wins = [a for a in action_items
                  if a.get("controlLevel") == "direct"
                  and a.get("difficultyLevel") in ("low", "medium")]

    high_impact_long_term = [a for a in action_items
                              if a.get("controlLevel") == "indirect"
                              or a.get("difficultyLevel") == "very_high"]

    top_5 = action_items[:5]
    peakweb_items = [a for a in action_items if a.get("peakwebFit") == "direct_service"]
    partner_items = [a for a in action_items if a.get("peakwebFit") != "direct_service"]

    lines = []
    answer_share_score = findings.get("answer_share_score")
    answer_share_rating = findings.get("answer_share_rating")

    lines.append(f"# AI Visibility Roadmap — {brand}")
    lines.append(f"> Generated {today} | GEO Readiness Score: {geo_score}/100 ({score_label})")
    if answer_share_score is not None:
        lines.append(f"> AI Answer Share Score: {answer_share_score}/100 ({answer_share_rating})")
    if url:
        lines.append(f"> Site: {url}")
    if bt != "unknown":
        lines.append(f"> Business type: {bt.replace('_', ' ').title()}")
    if platform != "unknown":
        lines.append(f"> Platform detected: {platform.title()}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("<!-- SKILL: Replace this block with a 4-6 sentence tailored summary. -->")
    lines.append(f"<!-- Context: {brand} scored {geo_score}/100 ({score_label}) on the GEO readiness assessment. -->")
    lines.append(f"<!-- Business type: {bt}. Platform: {platform}. -->")
    lines.append(f"<!-- Top action: {top_5[0]['title'] if top_5 else 'N/A'} -->")
    lines.append(f"<!-- Total action items: {len(action_items)} ({len(quick_wins)} quick wins, {len(high_impact_long_term)} long-term) -->")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## How to Read This Roadmap")
    lines.append("")
    lines.append("This roadmap is based on the signals that AI systems — including ChatGPT, Google AI Overviews,")
    lines.append("Perplexity, Claude, and Bing Copilot — rely on when deciding whether to cite or recommend")
    lines.append(f"a business like {brand}.")
    lines.append("")
    lines.append("Each action is scored by how much it is expected to move the needle on AI visibility,")
    lines.append("how much control you have over implementing it, and how quickly it can be done.")
    lines.append("Where relevant, we note whether Peakweb can implement this directly, whether it needs")
    lines.append("a specialist partner, or whether it is best led by your own team.")
    lines.append("")
    lines.append("**This roadmap is intended to work alongside your existing SEO provider and web team,**")
    lines.append("**not replace them.** GEO optimisation is additive — it layers on top of good SEO foundations.")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Top Priorities")
    lines.append("")
    lines.append(f"The following {len(top_5)} actions have the highest combined score impact, feasibility, and urgency.")
    lines.append("")

    for i, item in enumerate(top_5, 1):
        icon = IMPACT_ICONS.get(item.get("estimatedScoreImpact", "low"), "⚪")
        lines.append(f"### {i}. {item['title']} {icon}")
        lines.append("")
        lines.append(f"**Priority score:** {item.get('priorityScore', 0)}/100 &nbsp;|&nbsp; "
                     f"**Impact:** {_fmt_impact(item.get('estimatedScoreImpact',''))} &nbsp;|&nbsp; "
                     f"**Difficulty:** {_fmt_difficulty(item.get('difficultyLevel',''))} &nbsp;|&nbsp; "
                     f"**Timeline:** {HORIZON_LABELS.get(item.get('timeHorizon',''), item.get('timeHorizon',''))}")
        lines.append("")
        lines.append(f"**Why it matters:** {item.get('whyItMatters', '')}")
        lines.append("")
        if item.get("evidence"):
            lines.append(f"**Audit evidence:** {item['evidence']}")
            lines.append("")
        rec = item.get("customerSpecificRecommendation") or item.get("implementationNotes", "")
        if rec:
            lines.append(f"**Recommended next step:** {rec}")
            lines.append("")
        if item.get("platformSpecificNotes"):
            lines.append(f"**Platform note ({findings.get('platform', 'general')}):** {item['platformSpecificNotes']}")
            lines.append("")
        lines.append(f"**Peakweb fit:** {PEAKWEB_LABELS.get(item.get('peakwebFit',''), item.get('peakwebFit',''))}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Quick Wins")
    lines.append("")
    lines.append("These actions are under direct control and are low-to-medium difficulty. They can typically")
    lines.append("be completed in days to weeks and should be prioritised alongside the Top Priorities above.")
    lines.append("")

    if quick_wins:
        lines.append("| Action | Impact | Difficulty | Timeline | Peakweb Fit |")
        lines.append("|--------|--------|------------|----------|-------------|")
        for item in quick_wins[:8]:
            lines.append(
                f"| {item['title']} | {_fmt_impact(item.get('estimatedScoreImpact',''))} | "
                f"{_fmt_difficulty(item.get('difficultyLevel',''))} | "
                f"{HORIZON_LABELS.get(item.get('timeHorizon',''), '')} | "
                f"{PEAKWEB_LABELS.get(item.get('peakwebFit',''), '')} |"
            )
    else:
        lines.append("_No quick wins identified — most available improvements require moderate or high effort._")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## High-Impact, Long-Term Opportunities")
    lines.append("")
    lines.append("These actions have significant impact but are either outside direct control, require sustained")
    lines.append("effort over months, or depend on prerequisites being completed first.")
    lines.append("")

    if high_impact_long_term:
        for item in high_impact_long_term[:6]:
            control_label = CONTROL_LABELS.get(item.get("controlLevel", "indirect"), "")
            lines.append(f"**{item['title']}**")
            lines.append(f"- Impact: {_fmt_impact(item.get('estimatedScoreImpact',''))} | Control: {control_label} | Difficulty: {_fmt_difficulty(item.get('difficultyLevel',''))}")
            lines.append(f"- {item.get('whyItMatters', '')}")
            if item.get("customerSpecificRecommendation"):
                lines.append(f"- *{item['customerSpecificRecommendation']}*")
            lines.append("")
    else:
        lines.append("_No long-term / indirect opportunities identified from current audit data._")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Full Ranked Action Plan")
    lines.append("")
    lines.append(f"All {len(action_items)} action items ranked by priority score.")
    lines.append("")
    lines.append("| Rank | Action | Category | Impact | Difficulty | Control | Timeline | Priority | Peakweb Fit |")
    lines.append("|------|--------|----------|--------|------------|---------|----------|----------|-------------|")
    for i, item in enumerate(action_items, 1):
        lines.append(
            f"| {i} | {item['title']} | {item.get('category','').title()} | "
            f"{_fmt_impact(item.get('estimatedScoreImpact',''))} | "
            f"{_fmt_difficulty(item.get('difficultyLevel',''))} | "
            f"{CONTROL_LABELS.get(item.get('controlLevel',''), item.get('controlLevel',''))} | "
            f"{HORIZON_LABELS.get(item.get('timeHorizon',''), '')} | "
            f"{item.get('priorityScore', 0)}/100 | "
            f"{PEAKWEB_LABELS.get(item.get('peakwebFit',''), '')} |"
        )
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## What Peakweb Can Implement")
    lines.append("")
    if peakweb_items:
        lines.append("The following actions are within Peakweb's direct service scope:")
        lines.append("")
        for item in peakweb_items:
            lines.append(f"- **{item['title']}** — {item.get('implementationNotes', '')[:120]}...")
    else:
        lines.append("_All identified actions require client team or specialist partners._")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Actions for Your Team or Partners")
    lines.append("")
    if partner_items:
        lines.append("These actions are best led by your internal team, your existing SEO/web provider, or a specialist:")
        lines.append("")
        for item in partner_items:
            label = PEAKWEB_LABELS.get(item.get("peakwebFit", ""), "")
            lines.append(f"- **{item['title']}** ({label}) — {item.get('implementationNotes', '')[:120]}...")
    else:
        lines.append("_All identified actions are within Peakweb's implementation scope._")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Appendix: GEO Readiness Score Breakdown")
    lines.append("")
    lines.append("| Component | Weight | Your Score | Benchmark |")
    lines.append("|-----------|--------|------------|-----------|")
    cat_scores = findings.get("category_scores", {})
    components = [
        ("AI Citability & Visibility", "25%", "ai_citability"),
        ("Brand Authority Signals", "20%", "brand_authority"),
        ("Content Quality & E-E-A-T", "20%", "content_eeat"),
        ("Technical Foundations", "15%", "technical"),
        ("Structured Data", "10%", "schema"),
        ("Platform Optimisation", "10%", "platform_optimization"),
    ]
    for name, weight, key in components:
        score = cat_scores.get(key, "N/A")
        score_str = f"{score}/100" if isinstance(score, int) else "N/A"
        benchmark = "75+" if weight in ("25%", "20%") else "70+"
        lines.append(f"| {name} | {weight} | {score_str} | {benchmark} |")
    lines.append("")
    lines.append("_Scores derived from GEO-AUDIT-REPORT.md. Run `/geo-peakweb audit` to refresh._")
    lines.append("")

    # AI Answer Share appendix (if data available)
    if answer_share_score is not None:
        lines.append("---")
        lines.append("")
        lines.append("## Appendix: AI Answer Share Score")
        lines.append("")
        lines.append(f"**AI Answer Share Score: {answer_share_score}/100 ({answer_share_rating})**")
        lines.append("")
        lines.append("This score measures how much of AI-generated answers is attributable to")
        lines.append(f"{brand} across a basket of test queries run against Perplexity Sonar.")
        lines.append("Citations appearing earlier in answers are weighted more heavily (position-adjusted impression).")
        lines.append("")
        lines.append("_Run `/geo-perplexity` to measure or update this score._")
        lines.append("")
    else:
        lines.append("---")
        lines.append("")
        lines.append("## Appendix: AI Answer Share Score")
        lines.append("")
        lines.append("**Not yet measured.** Run `/geo-perplexity` to test how much of AI answers")
        lines.append(f"references {brand} across a basket of real queries.")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate a GEO Action Plan from audit files in an audit directory."
    )
    parser.add_argument(
        "audit_dir",
        help="Path to the audit directory (e.g. ~/.geo-prospects/audits/example.com)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write JSON output (default: stdout)"
    )
    parser.add_argument(
        "--markdown",
        default=None,
        help="Path to write Markdown roadmap output (optional)"
    )
    parser.add_argument(
        "--platform",
        default=None,
        help="Override platform detection (wordpress|shopify|wix|squarespace|webflow|unknown)"
    )
    args = parser.parse_args()

    audit_dir = os.path.expanduser(args.audit_dir)

    if not os.path.isdir(audit_dir):
        print(f"Error: audit directory not found: {audit_dir}", file=sys.stderr)
        sys.exit(1)

    findings = parse_audit_findings(audit_dir)

    if args.platform:
        findings["platform"] = args.platform

    action_items = map_findings_to_actions(findings)
    action_items = enrich_with_platform_context(action_items, findings)
    action_items = rank_action_items(action_items)

    output_data = {
        "generated_at": date.today().isoformat(),
        "brand_name": findings.get("brand_name", ""),
        "url": findings.get("url", ""),
        "geo_score": findings.get("geo_score", 0),
        "geo_readiness_score": findings.get("geo_score", 0),  # alias for new terminology
        "ai_answer_share_score": findings.get("answer_share_score"),
        "ai_answer_share_rating": findings.get("answer_share_rating"),
        "business_type": findings.get("business_type", "unknown"),
        "platform": findings.get("platform", "unknown"),
        "category_scores": findings.get("category_scores", {}),
        "action_items": action_items,
        "summary": {
            "total_actions": len(action_items),
            "immediate_actions": sum(1 for a in action_items if a.get("timeHorizon") == "immediate"),
            "quick_wins": sum(1 for a in action_items
                              if a.get("controlLevel") == "direct"
                              and a.get("difficultyLevel") in ("low", "medium")),
            "peakweb_deliverable": sum(1 for a in action_items if a.get("peakwebFit") == "direct_service"),
            "top_priority": action_items[0]["title"] if action_items else None,
        }
    }

    json_output = json.dumps(output_data, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(json_output)
        print(f"JSON written to {args.output}", file=sys.stderr)
    else:
        print(json_output)

    if args.markdown:
        md = generate_roadmap_markdown(action_items, findings)
        with open(args.markdown, "w") as f:
            f.write(md)
        print(f"Markdown written to {args.markdown}", file=sys.stderr)


if __name__ == "__main__":
    main()
