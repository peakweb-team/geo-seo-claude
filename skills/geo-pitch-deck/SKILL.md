---
name: geo-pitch-deck
description: Generate a Peakweb-branded pitch deck PDF from GEO audit data. Creates a professional 12-page PDF presentation ready to email to prospects.
---

# GEO Pitch Deck Generator

## Purpose

Generate a professional, Peakweb-branded pitch deck PDF from GEO audit data. This PDF is designed to be emailed to prospects as a sales deliverable, translating technical audit findings into a compelling business case for GEO optimization services.

## Command

```
/geo-peakweb pitch-deck <domain> [--client-name "Name"] [--contact-name "Name"] [--contact-title "Title"]
```

**Examples:**
```
/geo-peakweb pitch-deck denversprinklerservices.com
/geo-peakweb pitch-deck denversprinklerservices.com --client-name "Denver Sprinkler & Landscape" --contact-name "Ramon Robles" --contact-title "Owner"
```

---

## Prerequisites

1. **Run audit first** — The pitch deck pulls data from:
   - `GEO-AUDIT-REPORT.md` (scores, detailed findings)
   - `CLIENT-REPORT.md` (business-friendly content)

2. **ReportLab installed** — `pip install reportlab`

3. **Peakweb assets available** — Logo files in `assets/` directory

---

## Workflow

### Step 1: Load Audit Data

Look for existing audit files in the current directory or `~/.geo-prospects/audits/`:
- `GEO-AUDIT-REPORT.md`
- `CLIENT-REPORT.md`
- Or `*-audit-*.md` files

If no audit exists, prompt user to run `/geo-peakweb audit <domain>` first.

### Step 2: Extract Data for Pitch Deck

Parse the audit reports to extract:

**Client Info:**
- Company name (from audit or `--client-name` flag)
- Contact name (from `--contact-name` flag)
- Contact title (from `--contact-title` flag)
- Website URL
- Report date

**Scores:**
- Overall GEO Score (0-100)
- Category scores (Citability, Brand, E-E-A-T, Technical, Schema, Platform)
- Score label (Excellent/Good/Fair/Poor/Critical)
- Projected score after optimization

**Business Context:**
- Business type (Local, SaaS, E-commerce, Publisher, Agency)
- Industry/service type
- City/location
- Years in business
- Key credentials (BBB rating, certifications, etc.)

**Issues (Top 6):**
- Issue title
- Plain English description
- Business impact
- Callout/example

**What's Working (5 items):**
- Key strengths from the audit

**Quick Wins:**
- List of fast fixes with time estimates

**ROI Projections:**
- Estimated additional leads/month
- Estimated new customers/month
- Estimated additional revenue
- Annual impact

### Step 3: Build JSON Data Structure

Structure the extracted data as JSON for the PDF generator.

**Note:** The script accepts both `snake_case` and `UPPER_SNAKE_CASE` keys. Arrays are also supported for lists (e.g., `working: [...]` becomes `WORKING_1`, `WORKING_2`, etc.).

```json
{
  "client_name": "Denver Sprinkler & Landscape",
  "contact_name": "Ramon Robles",
  "contact_title": "Owner",
  "client_website": "denversprinklerservices.com",
  "report_date": "March 17, 2026",

  "geo_score": 53,
  "score_label": "FAIR",
  "score_description": "Your website is functional but not optimized for AI systems...",
  "projected_score": 85,

  "sample_query": "Who does sprinkler repair in Denver?",
  "years": "25",
  "bbb_rating": "A+",
  "city": "Denver",
  "industry": "landscaping",
  "service_type": "sprinkler",

  "working": [
    "Your website is accessible - AI systems can read your content",
    "Strong reputation - BBB A+ rating, Trees.com #6 in Denver",
    "Complete contact info - address, phone, hours clearly listed",
    "Professional website - clean design, mobile-friendly, secure",
    "Real experience - 25+ years in the industry"
  ],

  "means": [
    "Lost phone calls from potential customers who never hear your name",
    "Competitors who optimize for AI get recommended instead of you",
    "Your 25 years of experience and A+ rating are invisible"
  ],

  "issues": [
    {
      "title": "AI Systems Don't Know Who You Are",
      "body": "Your business has no 'identity' in AI databases...",
      "callout": "Impact: Lost leads from 30-40% of people using AI"
    }
  ],

  "nothing_short": [
    "Competitors who optimize will get recommended more often",
    "You'll continue missing leads from AI search (30-40%)",
    "The gap between you and optimized competitors widens"
  ],

  "nothing_long": [
    "AI search becomes the dominant way people find services",
    "Businesses without AI visibility become invisible",
    "Playing catch-up gets harder as competitors build authority"
  ],

  "opportunities": [
    {"area": "Technical Configuration", "desc": "Deploy AI configuration files"},
    {"area": "Content & Authority", "desc": "Build verified presence on platforms"},
    {"area": "Trust & Consistency", "desc": "Resolve conflicting information"},
    {"area": "Freshness & Relevance", "desc": "Add dates and current data"}
  ],

  "week_scores": [65, 72, 80, 85],

  "roi": {
    "leads_per_month": "7-8",
    "customers_per_month": "2-3",
    "monthly_rev": "$1,000-6,000",
    "annual_impact": "$12,000-72,000"
  },

  "before_lines": [
    "Customer: 'Hey ChatGPT, who should I call for sprinkler repair in Denver?'",
    "ChatGPT: 'Here are some well-reviewed options:'",
    "- GreenCo Irrigation (mentioned in multiple sources)",
    "- Colorado Sprinkler Pros (4.8 stars)",
    "Your business: Not mentioned"
  ],

  "after_lines": [
    "Customer: 'Hey ChatGPT, who should I call for sprinkler repair in Denver?'",
    "ChatGPT: 'Here are some well-reviewed options:'",
    "- Denver Sprinkler and Landscape (25+ years, BBB A+, serving Denver since 2011)",
    "- GreenCo Irrigation",
    "Your business: Mentioned FIRST with specific details"
  ],

  "faqs": [
    {
      "q": "Is this really necessary? My business is doing fine.",
      "a": "Your business IS doing fine. But consider: in 2005, many said 'I don't need a website'..."
    }
  ],

  "bottom_line": [
    "You've built an excellent business over 25 years.",
    "The only thing holding you back is that AI systems don't know about it yet."
  ]
}
```

### Step 4: Generate PDF

Run the pitch deck generator script:

```bash
# Set repo root (adjust if needed)
GEO_REPO="$HOME/gitRepos/geo-seo-claude"

# Generate the PDF
python3 "$GEO_REPO/scripts/generate_pitch_deck.py" /tmp/pitch-deck-data.json
# Or with custom output filename:
python3 "$GEO_REPO/scripts/generate_pitch_deck.py" /tmp/pitch-deck-data.json "PeakwebGEOProposal-ClientName.pdf"
```

**Note:** The script is located at `scripts/generate_pitch_deck.py` in the geo-seo-claude repository.

This script:
1. Accepts JSON with either snake_case or UPPER_SNAKE_CASE keys
2. Programmatically generates a 12-page branded PDF using ReportLab
3. Applies Peakweb brand guidelines (colors, fonts, logo)
4. Creates all visualizations (score bars, charts, callout boxes)

### Step 5: Return Results

Report success to user:
```
Pitch deck generated: PeakwebGEOProposal-DenverSprinklerLandscape.pdf

12 pages including:
- Cover page with Peakweb branding
- Executive summary with GEO score (53/100)
- 6 key issues identified
- 30-day implementation roadmap
- Pricing options ($1,000-$3,000)
- ROI projections

Ready to email to the prospect!
```

---

## PDF Structure (12 Pages)

| Page | Title | Content |
|------|-------|---------|
| 1 | Cover | Peakweb logo, "Website Visibility Audit", client name, date |
| 2 | Executive Summary | Key problem statement, AI search context, What is GEO |
| 3 | Your Current Score | Score bar, what's working well, business impact |
| 4 | The 6 Key Issues (Part 1) | Issues 1-3 with titles, descriptions, impact callouts |
| 5 | The 6 Key Issues (Part 2) | Issues 4-6 + What Happens If You Do Nothing |
| 6 | The Opportunity | Current vs projected score, 4 improvement areas |
| 7 | How Peakweb Gets You There | 4-week implementation roadmap |
| 8 | Working With Peakweb | Pricing packages + ROI stats + compounding effect |
| 9 | Traditional SEO vs GEO | Comparison table, "You Still Win" section |
| 10 | Before/After + FAQs | Real conversation example, common questions |
| 11 | Next Steps | 5-step process + "The Bottom Line" box |
| 12 | Final CTA | "Ready to Get Started?", contact info, W icon |

---

## Peakweb Brand Guidelines

### Colors

| Color | Hex | Usage |
|-------|-----|-------|
| Deep Blue | #0A2C49 | Headers, primary dark |
| Aquamarine | #01EFA0 | CTAs, accents, success |
| Light Green | #BCFF8A | Secondary accent |
| Midnight Green | #0A3E3C | Dark teal accent |
| Lilac | #9892B5 | Subtle accent |
| Stone | #FCF7E6 | Light background |

### Typography

- **Headings:** Outfit SemiBold (fallback: Helvetica-Bold)
- **Body:** Outfit Light (fallback: Helvetica)

### Logo

- Primary: `assets/PeakWeb-Green-RGB.jpg` or `.svg`
- Minimum width: 150px digital
- Clear space: height of 'C' in logo

---

## Pricing Packages in Pitch Deck

The pitch deck presents three Peakweb service tiers:

### GEO Essentials — $1,000
- All priority technical fixes
- AI configuration files deployed
- Structured data implementation
- Validation across all AI platforms
- 30-day post-launch monitoring

### GEO Growth — $2,000-$3,000
- Everything in Essentials
- Authority-building across platforms
- AI-optimized content creation
- 90-day monitoring dashboard

### GEO Partner — $500/month
- Ongoing monthly optimization
- Fresh content for relevance signals
- Strategy adaptation as AI evolves

---

## Output

- **PDF file:** `PeakwebGEOProposal-{ClientName}.pdf` in current directory
- **File size:** Typically 50-80 KB
- **Format:** 12 pages, US Letter size (8.5" x 11")

---

## Error Handling

1. **No audit data found:**
   ```
   No GEO audit found for this domain.
   Please run `/geo-peakweb audit <domain>` first, then try again.
   ```

2. **Missing ReportLab:**
   ```
   ReportLab not installed. Run: pip install reportlab
   ```

3. **Missing logo:**
   ```
   Peakweb logo not found. Expected: assets/PeakWeb-Green-RGB.jpg
   ```
