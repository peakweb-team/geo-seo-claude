---
name: geo-sow
description: Generate a Peakweb-branded Statement of Work PDF for GEO services. Creates a professional 8-page SOW document with scope, deliverables, timeline, pricing, and signature blocks.
allowed-tools: Read, Write, Bash, Glob
---

# GEO Statement of Work Generator

## Purpose

Generate a professional, Peakweb-branded Statement of Work (SOW) PDF from audit data and engagement parameters. This PDF is designed to be sent to prospects who have reviewed a pitch deck and are ready to move forward with an engagement.

## Command

```
/geo-sow <domain> --package <type> --duration <time> [options]
```

**Examples:**
```
/geo-sow sigsauer.com --package essentials --duration "30 days"
/geo-sow sigsauer.com --package growth --duration "90 days"
/geo-sow sigsauer.com --package partner --duration "6 months"
/geo-sow sigsauer.com --package custom --duration "60 days" --price "$1,800"
```

---

## Prerequisites

1. **Run audit first** — The SOW pulls data from:
   - `GEO-AUDIT-REPORT.md` (scores, findings)
   - `CLIENT-REPORT.md` (client info)
   - Or pitch deck JSON if available

2. **ReportLab installed** — `pip install reportlab`

3. **Peakweb assets available** — Logo files in `assets/` directory

---

## Required Parameters

| Flag | Values | Description |
|------|--------|-------------|
| `--package` | `essentials`, `growth`, `partner`, `custom` | Service package type |
| `--duration` | e.g., `"30 days"`, `"90 days"`, `"6 months"` | Engagement duration |

## Optional Parameters (Auto-Pulled from Audit)

| Flag | Description | Default |
|------|-------------|---------|
| `--client-name` | Client company name | From audit |
| `--contact-name` | Contact person name | From audit |
| `--contact-title` | Contact's job title | From audit |
| `--price` | Custom total price | Package default |
| `--monthly-price` | Monthly retainer (partner only) | `$500` |
| `--access-needed` | Required site access | `"CMS access, Google Analytics"` |
| `--team-interaction` | Interaction level | `"Weekly progress updates"` |
| `--start-date` | Engagement start date | 7 days from today |
| `--sow-ref` | Custom reference number | Auto-generated |

---

## Workflow

### Step 1: Load Audit Data

Look for existing audit files in `~/.geo-prospects/audits/{domain}/`:
- `GEO-AUDIT-REPORT.md`
- `CLIENT-REPORT.md`
- `pitch-deck-data.json` (if pitch deck was generated)

If no audit exists, prompt user to run `/geo-peakweb audit <domain>` first.

### Step 2: Validate Required Parameters

Ensure `--package` and `--duration` are provided. If missing, show usage help.

### Step 3: Apply Package Defaults

Load package-specific defaults for:
- Deliverables and descriptions
- In-scope and out-of-scope items
- Pricing and payment schedule
- Milestones and timeline

### Step 4: Build JSON Data Structure

Structure the data as JSON for the PDF generator:

```json
{
  "sow_ref": "SOW-2026-0323-SIGSAUER",
  "effective_date": "March 30, 2026",
  "expiration_date": "April 30, 2026",

  "client": {
    "company_name": "SIG SAUER Inc.",
    "contact_name": "Jack Morris",
    "contact_title": "Sr. Manager, Web / Email",
    "website": "sigsauer.com"
  },

  "provider": {
    "company_name": "Peakweb LLC",
    "contact_name": "Nathan Perry",
    "contact_email": "nathan@peakweb.io"
  },

  "project": {
    "name": "GEO Optimization Engagement",
    "package": "growth",
    "package_display": "GEO Growth",
    "description": "Comprehensive Generative Engine Optimization services."
  },

  "engagement": {
    "type": "one-time",
    "duration": "90 days",
    "start_date": "March 30, 2026",
    "end_date": "June 28, 2026"
  },

  "context": {
    "geo_score": 58,
    "score_label": "Fair",
    "key_issues": [
      "JavaScript rendering blocks AI access",
      "Zero Product schema markup",
      "Limited AI-optimized content"
    ]
  },

  "objectives": [
    "Improve GEO Score from 58 to 75+ within 90 days",
    "Deploy AI configuration files",
    "Implement comprehensive Schema.org markup"
  ],

  "scope": {
    "in_scope": [
      "Full technical GEO audit and implementation",
      "AI configuration file deployment",
      "Schema.org markup implementation"
    ],
    "out_of_scope": [
      "Server-side rendering implementation",
      "Core website redesign",
      "Traditional SEO services"
    ]
  },

  "deliverables": [
    {
      "number": 1,
      "name": "Technical Foundation",
      "description": "AI configuration files, crawler access optimization",
      "due": "Week 1-2"
    }
  ],

  "milestones": [
    {"week": "Week 2", "milestone": "Technical foundation complete", "score_target": "65"}
  ],

  "resources": {
    "peakweb": ["GEO Specialist", "Technical implementation team"],
    "client": [
      "CMS access credentials",
      "Google Analytics access",
      "Timely feedback (within 48 hours)"
    ]
  },

  "pricing": {
    "type": "one-time",
    "total": "$2,500",
    "breakdown": [
      {"item": "Technical Foundation", "amount": "$750"}
    ],
    "payment_schedule": [
      {"milestone": "Upon signing", "percentage": "50%", "amount": "$1,250"}
    ]
  },

  "assumptions": [
    "Client will provide CMS access within 5 business days",
    "Client feedback on content within 48 hours"
  ],

  "term": {
    "duration": "90 days from Effective Date",
    "termination_notice": "14 days written notice"
  }
}
```

### Step 5: Generate PDF

Run the SOW generator script:

```bash
GEO_REPO="$HOME/gitRepos/geo-seo-claude"
python3 "$GEO_REPO/scripts/generate_sow.py" /tmp/sow-data.json
# Or with custom output:
python3 "$GEO_REPO/scripts/generate_sow.py" /tmp/sow-data.json "PeakwebSOW-ClientName.pdf"
```

### Step 6: Return Results

Report success to user:
```
Statement of Work generated: PeakwebSOW-SIGSauer-2026-03-23.pdf

8 pages including:
- Cover page with SOW reference
- Scope of services and objectives
- Deliverables and timeline
- Pricing and payment schedule
- Terms and signature blocks

Ready to send to client for signature!
```

---

## Package Configurations

### GEO Essentials — $1,000 (One-Time)

**Duration:** 30 days

**Deliverables:**
| # | Deliverable | Description | Due |
|---|-------------|-------------|-----|
| 1 | Technical Foundation | AI configuration files, crawler optimization | Week 1 |
| 2 | Structured Data | Organization/LocalBusiness schema | Week 2 |
| 3 | Platform Validation | Cross-platform testing (ChatGPT, Perplexity, Google AIO) | Week 3 |
| 4 | Handoff & Monitoring | 30-day monitoring dashboard, documentation | Week 4 |

**In Scope:**
- AI configuration files (llms.txt, robots.txt optimization)
- Basic Schema.org implementation
- Platform validation across major AI systems
- 30-day post-launch monitoring

**Out of Scope:**
- Server-side rendering implementation
- Content creation or rewriting
- Traditional SEO services
- Ongoing optimization

**Payment:** 100% upon signing

---

### GEO Growth — $2,500 (One-Time)

**Duration:** 90 days

**Deliverables:**
| # | Deliverable | Description | Due |
|---|-------------|-------------|-----|
| 1 | Technical Foundation | AI configuration files, comprehensive schema | Week 1-2 |
| 2 | Authority Building | Platform presence, directory submissions | Week 3-4 |
| 3 | Content Optimization | AI-optimized content (up to 10 pages) | Week 5-8 |
| 4 | Validation & Launch | Platform testing, 90-day monitoring dashboard | Week 9-12 |

**In Scope:**
- Everything in Essentials
- Authority-building across AI-indexed platforms
- AI-optimized content creation (up to 10 pages)
- 90-day monitoring dashboard
- Weekly progress reports

**Out of Scope:**
- Server-side rendering implementation
- Core website redesign
- Traditional SEO services
- Content beyond 10 pages

**Payment:** 50% upon signing / 25% Week 6 / 25% final delivery

---

### GEO Partner — $500/month (Ongoing)

**Duration:** 6 months minimum

**Deliverables:**
| # | Deliverable | Description | Due |
|---|-------------|-------------|-----|
| 1 | Monthly Audit | Full GEO score audit and delta report | Monthly |
| 2 | Content Refresh | 2-4 pieces of fresh AI-optimized content | Monthly |
| 3 | Strategy Call | 60-minute review and planning session | Monthly |
| 4 | Platform Monitoring | Continuous monitoring across all AI platforms | Ongoing |

**In Scope:**
- Monthly full GEO audit with delta tracking
- Fresh content for relevance signals (2-4 pieces/month)
- Strategy adaptation as AI evolves
- Priority support (4-hour response)
- Slack channel for communication

**Out of Scope:**
- Major technical implementations
- Website redesign or development
- Traditional SEO services
- Content beyond monthly allotment

**Payment:** Monthly on the 1st

---

## PDF Structure (8 Pages)

| Page | Title | Content |
|------|-------|---------|
| 1 | Cover | Peakweb logo, "Statement of Work", client name, SOW ref, effective date |
| 2 | Overview | Purpose, project summary box, audit context (score, key issues) |
| 3 | Scope of Services | Objectives, In Scope list, Out of Scope list |
| 4 | Deliverables & Timeline | Deliverables table, milestone timeline |
| 5 | Resource Requirements | Peakweb team, Client responsibilities |
| 6 | Pricing & Payment | Fees breakdown, payment schedule table |
| 7 | Terms & Conditions | Change management, assumptions, acceptance, termination |
| 8 | Signatures | Two-column signature block (Peakweb + Client) |

---

## Peakweb Brand Guidelines

### Colors

| Color | Hex | Usage |
|-------|-----|-------|
| Deep Blue | #0A2C49 | Headers, primary dark |
| Aquamarine | #01EFA0 | CTAs, accents |
| Light Green | #BCFF8A | Secondary accent |
| Stone | #FCF7E6 | Light background |

### Typography

- **Headings:** Outfit SemiBold (fallback: Helvetica-Bold)
- **Body:** Outfit Light (fallback: Helvetica)

### Logo

- Primary: `assets/PeakWeb-Green-RGB.png`

---

## Standard Terms

### Change Management
Changes to scope must be submitted in writing. Peakweb will provide a change order with revised timeline and pricing within 48 hours. No work on changes begins until written approval is received.

### Assumptions
- Client will provide CMS access within 5 business days of signing
- Client feedback on content drafts within 48 business hours
- No major website redesign during engagement period
- Current hosting and domain remain stable
- Client has authority to make content and technical changes

### Acceptance Criteria
Deliverables are considered accepted if no written objections are received within 5 business days of delivery. Final acceptance confirmed by documented GEO score improvement.

### Termination
Either party may terminate with 14 days written notice. Payment for completed work through termination date is due immediately.

---

## Output

- **PDF file:** `PeakwebSOW-{ClientName}-{Date}.pdf` in current directory
- **File size:** Typically 30-50 KB
- **Format:** 8 pages, US Letter size (8.5" x 11")

---

## Error Handling

1. **No audit data found:**
   ```
   No GEO audit found for this domain.
   Please run `/geo-peakweb audit <domain>` first, then try again.
   ```

2. **Missing required parameters:**
   ```
   Missing required parameters.
   Usage: /geo-sow <domain> --package <essentials|growth|partner|custom> --duration <time>
   ```

3. **Missing ReportLab:**
   ```
   ReportLab not installed. Run: pip install reportlab
   ```

4. **Missing logo:**
   ```
   Peakweb logo not found. Expected: assets/PeakWeb-Green-RGB.png
   ```
