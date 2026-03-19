# GEO Audit Report: Wild Reflections Studio

**Target:** https://www.wildreflectionsstudio.com/
**Business Type:** Taxidermy Studio (Local Service)
**Location:** Chugiak/Peters Creek, Alaska (Anchorage metro)
**Platform:** Wix (Thunderbolt renderer)
**Audit Date:** March 18, 2026

---

## Executive Summary

| Metric | Score | Rating |
|--------|-------|--------|
| **Composite GEO Score** | **44/100** | Poor |
| AI Citability & Visibility | 46/100 | Fair |
| Brand Authority Signals | 40/100 | Poor |
| Content Quality & E-E-A-T | 52/100 | Fair |
| Technical Foundations | 62/100 | Fair |
| Structured Data | 5/100 | Critical |
| Platform Optimization | 38/100 | Poor |

**Critical Issues:**
1. Zero schema markup (5/100)
2. Wix JavaScript rendering blocks AI content extraction
3. No Google Business Profile verified
4. Missing from Yelp, LinkedIn, YouTube
5. No llms.txt file

---

## Site Discovery

### Pages Analyzed
| URL | Title | Status |
|-----|-------|--------|
| / | Taxidermy Anchorage \| Chugiak \| Wild Reflections | 200 |
| /prices | Prices \| Anchorage \| Wild Reflections | 200 |
| /our-work | Our-work \| Chugiak \| Wild Reflections | 200 |
| /trophy-care | Trophy-care \| Chugiak \| Wild Reflections | 200 |
| /trophy-expediting | Trophy-expediting \| Anchorage \| Wild Reflections | 200 |
| /old-photos | (legacy page) | 200 |
| /shop-life | (legacy page) | 200 |

### Business Profile
- **Business Name:** Wild Reflections Studio / Wild Reflections LLC
- **Owner:** Grant Gullicks (Master Taxidermist)
- **Years Experience:** 23+
- **Training:** Animal Artistry (Reno, Nevada)
- **Specialization:** Sheep, Alaskan big game
- **Address:** 22444 Northwoods Dr, Chugiak, AK 99567
- **LLC Registered:** December 21, 2016
- **Status:** Good Standing

---

## AI Crawler Access

### robots.txt Analysis

```
User-agent: *
Allow: /
Disallow: *?lightbox=

User-agent: PetalBot
Disallow: /

User-agent: dotbot
Crawl-delay: 10

User-agent: AhrefsBot
Crawl-delay: 10

Sitemap: https://www.wildreflectionsstudio.com/sitemap.xml
```

### AI Crawler Status

| Crawler | Status | Notes |
|---------|--------|-------|
| GPTBot (OpenAI) | **Allowed** | No blocking rules |
| OAI-SearchBot | **Allowed** | No blocking rules |
| ChatGPT-User | **Allowed** | No blocking rules |
| ClaudeBot (Anthropic) | **Allowed** | No blocking rules |
| PerplexityBot | **Allowed** | No blocking rules |
| Amazonbot | **Allowed** | No blocking rules |
| Google-Extended | **Allowed** | No blocking rules |
| Bytespider (TikTok) | **Allowed** | No blocking rules |
| CCBot (Common Crawl) | **Allowed** | No blocking rules |
| Applebot-Extended | **Allowed** | No blocking rules |
| Cohere-ai | **Allowed** | No blocking rules |
| PetalBot | **Blocked** | Explicitly blocked |

**Crawler Access Score:** 85/100

**Critical Caveat:** While robots.txt allows all AI crawlers, the Wix platform renders content via JavaScript. AI crawlers receive mostly framework code, not actual business content.

### llms.txt Status

- `/llms.txt` — **404 Not Found**
- `/llms-full.txt` — **400 Bad Request**

**llms.txt Score:** 0/100

---

## AI Citability Analysis

### Citability Score: 35/100

**Assessment Method:** Evaluated content blocks for AI citation readiness based on:
- Self-containment (can be quoted without context)
- Statistical density (specific data points)
- Answer block quality (directly answers questions)
- Structural readability (heading hierarchy)
- Uniqueness (original insights)

### Best Citable Content Found

| Source | Content Block | Score |
|--------|---------------|-------|
| Hunt Alaska Magazine | "Grant Gullicks is the owner and master taxidermist of Wild Reflections, a small custom taxidermy studio based in Peters Creek, Alaska. With over 23 years of experience working and training with the best taxidermists in the world, Grant brings cutting edge techniques together with sharp artistic design." | 62/100 |
| Trophy Expediting meta | "Personal, professional, and hassle free trophy care. Wild Reflections ensures your trophy gets the care required and safely arrives at its destination." | 55/100 |
| Location info | "Conveniently located in Peters Creek, just 5 minutes from Birchwood Airport and 30 minutes from Lake Hood." | 55/100 |
| Business model | "They only accept premium, well-cared-for trophies and have a limited number of projects they accept each year." | 50/100 |

### Citability Gaps

| Area | Issue | Impact |
|------|-------|--------|
| Pricing | No actual prices in meta descriptions or extractable HTML | AI can't answer "How much does taxidermy cost in Alaska?" |
| Process | No detailed field care instructions accessible to AI | AI can't cite trophy care expertise |
| Credentials | Training/experience not in structured format | AI can't verify expertise claims |
| Contact | Phone/email not in extractable HTML | AI can't provide contact info |

---

## Brand Mention Analysis

### Brand Mention Score: 40/100

| Platform | Status | Quality |
|----------|--------|---------|
| Wikipedia | Absent | — |
| Reddit | Absent | — |
| YouTube | Absent | — |
| LinkedIn (Company) | Absent | — |
| LinkedIn (Personal) | Absent | — |
| Yelp | Absent | — |
| Google Business Profile | Unverified/Not found | — |
| Facebook | **Present** | Active, 503 likes, @WRalaska |
| Instagram | **Present** | @wildreflectionstaxidermy |
| Hunt Alaska Magazine | **Present** | Expert quote in taxidermy tips article |
| Alaska Outdoors Forums | **Present** | Positive recommendation |
| Rokslide Forums | **Present** | "Great guy and excellent taxidermist" |
| Alaska Company Directory | **Present** | LLC registered, good standing |

### Missing Critical Platforms

1. **Google Business Profile** — Essential for local AI visibility
2. **Yelp** — Frequently cited by AI for local business info
3. **LinkedIn** — Critical for Bing Copilot entity recognition
4. **YouTube** — Video content highly cited by AI

---

## Platform Readiness Analysis

### Platform Scores

| Platform | Score | Key Gaps |
|----------|-------|----------|
| Google AI Overviews | 42/100 | No schema, no featured snippet content, weak local signals |
| ChatGPT Web Search | 35/100 | JS-rendered content invisible, no dates, thin content |
| Perplexity AI | 38/100 | No Reddit presence, limited citable data |
| Google Gemini | 45/100 | No GBP, weak entity signals, missing sameAs |
| Bing Copilot | 32/100 | No LinkedIn, no Microsoft ecosystem presence |

### Platform-Specific Requirements

**Google AI Overviews:**
- [ ] LocalBusiness schema with geo coordinates
- [ ] FAQ content with question-based headings
- [ ] Featured snippet-eligible answer blocks
- [ ] Verified Google Business Profile

**ChatGPT Web Search:**
- [ ] Server-rendered content (not JS-dependent)
- [ ] Publication dates on content
- [ ] Specific data points (prices, timelines)
- [ ] Author credentials visible

**Perplexity AI:**
- [ ] Reddit mentions/participation
- [ ] Forum presence (have some)
- [ ] Factual, citable statements
- [ ] Source attribution signals

**Bing Copilot:**
- [ ] LinkedIn company page
- [ ] LinkedIn personal profile for owner
- [ ] Microsoft ecosystem presence
- [ ] IndexNow implementation

---

## Technical SEO Analysis

### Technical Score: 62/100

### Server-Side Rendering

**Platform:** Wix Thunderbolt (React-based, version 1.17036.0)
**Rendering:** Hybrid (some SSR, heavy JS dependency)

**What AI Crawlers Receive:**
- Page titles — Yes
- Meta descriptions — Yes
- Navigation structure — Partial
- Body content — Minimal (mostly JS config)
- Images with alt text — Some (many empty)

**Critical Issue:** `"isSEO":false` flag detected in Wix viewer model.

### Meta Tags

| Page | Title | Description | Issues |
|------|-------|-------------|--------|
| Homepage | "Taxidermy Anchorage \| Chugiak \| Wild Reflections" (51 chars) | "Stunningly realistic taxidemy. Based in Chugiak..." (97 chars) | **TYPO: "taxidemy"** |
| Prices | "Prices \| Anchorage \| Wild Reflections" (38 chars) | "Wild Reflections current price lists." (37 chars) | Description too short |
| Our Work | "Our-work \| Chugiak \| Wild Reflections" (38 chars) | "The closer you look, the better our work appears..." (114 chars) | OK |
| Trophy Care | "Trophy-care \| Chugiak \| Wild Reflections" (41 chars) | "Wild Reflections trophy care presentation..." (96 chars) | OK |
| Trophy Expediting | "Trophy-expediting \| Anchorage \| Wild Reflections" (49 chars) | "Personal, professional, and hassle free trophy care..." (145 chars) | Good |

### Open Graph / Social

| Tag | Status |
|-----|--------|
| og:title | Present |
| og:description | Present |
| og:url | Present |
| og:site_name | Present |
| og:type | Present |
| og:image | **Missing** |
| twitter:card | Present |
| twitter:title | Present |
| twitter:description | Present |
| twitter:image | **Missing** |

### Security Headers

| Header | Status |
|--------|--------|
| HTTPS | Yes |
| HSTS | Present (1 year) |
| Content-Type-Options | Present (nosniff) |
| Content-Security-Policy | Missing |
| X-Frame-Options | Missing |
| Referrer-Policy | Missing |
| Permissions-Policy | Missing |

### Core Web Vitals Risk

| Vital | Risk Level | Indicators |
|-------|------------|------------|
| LCP | HIGH | Large images (4608x3456), render-blocking JS, React hydration |
| INP | MEDIUM | Heavy JS bundles, React 18 hydration |
| CLS | LOW-MEDIUM | Images have dimensions, fonts use swap |

### URL Structure

| URL | Assessment |
|-----|------------|
| /prices | Clean, could be more descriptive |
| /our-work | Good |
| /trophy-care | Good |
| /trophy-expediting | Good |

**Score:** 90/100

---

## Content & E-E-A-T Analysis

### E-E-A-T Score: 62/100

| Dimension | Score | Evidence |
|-----------|-------|----------|
| Experience | 18/25 | 23+ years, Animal Artistry training, quoted in Hunt Alaska Magazine |
| Expertise | 16/25 | Master taxidermist, species-specific knowledge, technical quotes |
| Authoritativeness | 14/25 | Magazine feature, forum recommendations, but no awards/certifications |
| Trustworthiness | 14/25 | Registered LLC, physical address, but no visible reviews or contact info |

### Content Score: 52/100

**Gaps:**
- Thin content on all pages
- No blog or educational content hub
- No species-specific pages
- No FAQ page
- No visible publication dates
- No customer testimonials on website
- Missing privacy policy / terms of service

### Topical Authority

**Current Coverage:** ~20-30% of expected taxidermy topics

**Missing Content:**
- Species-specific guides (Dall Sheep, Moose, Caribou, Bear)
- Detailed field care instructions
- Process documentation
- FAQ addressing common hunter questions
- Case studies with before/after
- Pricing guide with context
- Alaska hunting regulations/tips
- "How to choose a taxidermist" guide

---

## Schema Markup Analysis

### Schema Score: 5/100 (Critical)

### Detected Schema

**Total:** 0 schema blocks detected

| Schema Type | Status |
|-------------|--------|
| LocalBusiness | Missing |
| Organization | Missing |
| Person | Missing |
| Service | Missing |
| FAQPage | Missing |
| HowTo | Missing |
| BreadcrumbList | Missing |
| ImageGallery | Missing |
| Review/AggregateRating | Missing |

### sameAs Entity Linking

**Current:** 0 entity links

**Needed:**
- [ ] Google Business Profile URL
- [ ] Facebook URL
- [ ] Instagram URL
- [ ] Yelp URL (when created)
- [ ] LinkedIn URL (when created)

---

## Priority Actions

### Critical (Week 1)

| Action | Impact | Effort |
|--------|--------|--------|
| Fix "taxidemy" typo in homepage meta | Trust | 1 min |
| Add LocalBusiness schema | AI visibility, local search | 30 min |
| Claim Google Business Profile | Local AI results | 30 min |
| Create Yelp listing | Citation source | 15 min |
| Create llms.txt | AI understanding | 15 min |

### High (Week 2)

| Action | Impact | Effort |
|--------|--------|--------|
| Create LinkedIn company page | Bing Copilot, entity recognition | 30 min |
| Create LinkedIn profile for Grant | Authority signals | 30 min |
| Add Service schema to Prices page | Rich results eligibility | 30 min |
| Add og:image / twitter:image | Social sharing | 15 min |
| Add visible contact info to HTML | AI citation | 15 min |

### Medium (Week 3-4)

| Action | Impact | Effort |
|--------|--------|--------|
| Expand Trophy Care content | Topical authority | 4-6 hrs |
| Create FAQ page with schema | Featured snippets | 2-3 hrs |
| Add species-specific portfolio descriptions | Content depth | 3-4 hrs |
| Request customer reviews on Google | Trust signals | Ongoing |
| Create YouTube channel with 1-2 videos | Video citations | 4-6 hrs |

### Low (Ongoing)

| Action | Impact | Effort |
|--------|--------|--------|
| Engage on hunting forums | Brand mentions | Ongoing |
| Add privacy policy | Trust | 30 min |
| Add publication dates to content | Freshness signals | 15 min |
| Consider blog content strategy | Long-term authority | Ongoing |

---

## JSON-LD Templates

### LocalBusiness (Homepage)

```json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "@id": "https://www.wildreflectionsstudio.com/#organization",
  "name": "Wild Reflections Studio",
  "description": "Alaska's premier custom taxidermy studio specializing in Alaskan big game mounts with an emphasis on sheep. Master Taxidermist Grant Gullicks brings 23+ years of experience and training from world-famous Animal Artistry in Reno, Nevada.",
  "url": "https://www.wildreflectionsstudio.com",
  "telephone": "[PHONE]",
  "email": "[EMAIL]",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "22444 Northwoods Dr",
    "addressLocality": "Chugiak",
    "addressRegion": "AK",
    "postalCode": "99567",
    "addressCountry": "US"
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": 61.3922,
    "longitude": -149.4794
  },
  "areaServed": [
    {"@type": "State", "name": "Alaska"},
    {"@type": "City", "name": "Anchorage"},
    {"@type": "City", "name": "Chugiak"}
  ],
  "priceRange": "$$",
  "sameAs": [
    "https://www.facebook.com/WRalaska/",
    "https://www.instagram.com/wildreflectionstaxidermy/"
  ],
  "founder": {
    "@type": "Person",
    "name": "Grant Gullicks",
    "jobTitle": "Master Taxidermist"
  }
}
```

### Service (Prices Page)

```json
{
  "@context": "https://schema.org",
  "@type": "Service",
  "name": "Professional Taxidermy Services",
  "description": "Expert taxidermy services for Alaskan big game including Dall Sheep, Moose, Caribou, and Bear. Shoulder mounts, life-size mounts, bird taxidermy, fish taxidermy, and European skull mounts.",
  "provider": {
    "@type": "LocalBusiness",
    "@id": "https://www.wildreflectionsstudio.com/#organization"
  },
  "serviceType": "Taxidermy",
  "areaServed": {"@type": "State", "name": "Alaska"},
  "url": "https://www.wildreflectionsstudio.com/prices"
}
```

### FAQPage (Trophy Care)

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "How should I field dress my trophy for taxidermy?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "[Add detailed answer]"
      }
    },
    {
      "@type": "Question",
      "name": "How do I properly cape a big game animal?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "[Add detailed answer]"
      }
    }
  ]
}
```

---

## Wix Implementation Notes

### Adding JSON-LD Schema

1. Go to **Settings > Custom Code**
2. Click **Add Custom Code**
3. Paste JSON-LD wrapped in `<script type="application/ld+json">` tags
4. Set placement to **Head**
5. Apply to **All pages** or specific pages

### Creating llms.txt

Wix doesn't natively support custom files at root. Options:
1. Use Wix Velo (code) to serve the file
2. Host on subdomain
3. Add to /llms.txt route manually

### Testing Schema

- Google Rich Results Test: https://search.google.com/test/rich-results
- Schema.org Validator: https://validator.schema.org/

---

## Monitoring Queries

Test monthly in ChatGPT and Perplexity:

1. "Who's a good taxidermist in Anchorage Alaska?"
2. "Best sheep taxidermist in Alaska"
3. "How much does taxidermy cost in Alaska?"
4. "How to field dress a moose for taxidermy"
5. "Wild Reflections Studio taxidermy"

Track whether your business appears and how it's described.

---

## Sources Referenced

- https://www.wildreflectionsstudio.com/
- https://www.wildreflectionsstudio.com/robots.txt
- https://www.wildreflectionsstudio.com/sitemap.xml
- https://www.facebook.com/WRalaska/
- https://www.instagram.com/wildreflectionstaxidermy/
- https://www.huntalaskamagazine.com/taxidermy-tips-alaska/
- https://forums.outdoorsdirectory.com/threads/taxidermy-recommendations.153480/
- https://rokslide.com/forums/threads/wasilla-anchorage-taxidermist-recommendation.263792/
- https://www.alaskacompanydir.com/companies/wild-reflections-llc/

---

*Report generated March 18, 2026 by Peakweb GEO Analysis Tool*
