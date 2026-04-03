---
name: geo-roadmap
description: Generate a prioritized GEO AI Visibility Roadmap and Action Plan from audit data. Produces GEO-ROADMAP.md and optionally GEO-ROADMAP.pdf. Use after running /geo-peakweb audit.
allowed-tools: Read, Write, Bash, Glob
---

# GEO Roadmap Generator

## Purpose

Transform existing GEO audit findings into a **ranked, customer-facing action plan** — the "what should we do next?" deliverable that bridges the audit and the SOW.

This is not another score summary. The roadmap answers:
- What actions will move the needle most on AI visibility?
- Which are under the client's direct control vs. earned/indirect?
- Which are quick wins vs. longer-term plays?
- Which can Peakweb implement vs. client team vs. specialist partner?

---

## Command

```
/geo-peakweb roadmap <domain> [--pdf] [--client-name "Name"]
```

**Examples:**
```
/geo-peakweb roadmap resilientmartialarts.com
/geo-peakweb roadmap denversprinklerservices.com --pdf
/geo-peakweb roadmap example.com --client-name "Acme Corp" --pdf
```

---

## Prerequisites

At least one of these files must exist in `~/.geo-prospects/audits/<domain>/`:
- `GEO-AUDIT-REPORT.md` (preferred — contains scores and findings)
- `CLIENT-REPORT.md`
- Any `GEO-*.md` audit subagent files

If no audit exists, prompt the user to run `/geo-peakweb audit <domain>` first.

---

## Workflow

### Step 1: Locate Audit Directory

```bash
DOMAIN="<domain>"
AUDIT_DIR="$HOME/.geo-prospects/audits/$DOMAIN"
ls "$AUDIT_DIR"
```

If the directory does not exist or is empty, tell the user to run the audit first.

### Step 2: Run the Deterministic Generator

```bash
python3 ~/.claude/skills/geo/scripts/action_plan_generator.py "$AUDIT_DIR" \
  --output /tmp/geo-roadmap-data.json
```

This script:
- Reads all `GEO-*.md` and `CLIENT-REPORT.md` files in the audit directory
- Parses structured findings (scores, schema presence, crawler access, brand signals, etc.)
- Applies deterministic rules to generate relevant action items
- Computes a priority score (0-100) for each action item
- Outputs ranked JSON to `/tmp/geo-roadmap-data.json`

Read the JSON output to understand what was found:
```bash
cat /tmp/geo-roadmap-data.json
```

### Step 3: Generate Tailored Executive Summary (LLM Layer)

Read the JSON and the audit reports to write a **4-6 sentence executive summary** for this specific client. Use this to replace the placeholder comment in the markdown output.

The summary should:
- State the overall GEO score and what it means in plain terms
- Name the single most impactful issue the client faces
- Note one or two strengths (if any)
- End with a forward-looking statement about what the roadmap will achieve

**Language rules:**
- Do NOT say "you are not ranking for prompt X"
- DO say "these are the signals AI systems rely on when deciding whether to cite or recommend your business"
- Frame actions as complementary to existing SEO, not replacements
- Suitable for a business owner to read directly — no jargon

### Step 4: Generate the Roadmap Markdown

```bash
python3 ~/.claude/skills/geo/scripts/action_plan_generator.py "$AUDIT_DIR" \
  --markdown /tmp/geo-roadmap-draft.md
```

Read the draft markdown, fill in the executive summary, and write the final file:

```bash
# Final output location
OUTPUT_DIR="$HOME/.geo-prospects/audits/$DOMAIN"
cp /tmp/geo-roadmap-draft.md "$OUTPUT_DIR/GEO-ROADMAP.md"
# Then edit the executive summary section in the file
```

### Step 5: (Optional) Generate PDF

If the user requested `--pdf`:

```bash
# Write enriched JSON with executive summary to temp file
cat > /tmp/geo-roadmap-data.json << 'EOF'
{ ...updated JSON with executive_summary field populated... }
EOF

python3 ~/.claude/skills/geo/scripts/generate_roadmap_pdf.py \
  /tmp/geo-roadmap-data.json \
  "GEO-ROADMAP-${DOMAIN}.pdf"
```

The PDF will be generated in the current working directory.

### Step 6: Report to User

Tell the user:
- Path to `GEO-ROADMAP.md`
- Path to `GEO-ROADMAP.pdf` (if generated) and file size
- Summary: total actions, top priority, number of quick wins, number Peakweb can implement
- Suggested next steps (e.g., review roadmap with client, generate SOW)

---

## Platform Detection (Optional Enhancement)

If the audit reports contain references to a CMS (WordPress, Shopify, Wix, etc.), pass the `--platform` flag:

```bash
python3 ~/.claude/skills/geo/scripts/action_plan_generator.py "$AUDIT_DIR" \
  --platform wordpress \
  --output /tmp/geo-roadmap-data.json
```

Alternatively, if you have HTML from the site, you can run:
```python
from action_plan_generator import detect_platform_from_html
platform = detect_platform_from_html(html_content)
```

---

## Output Files

| File | Location | Description |
|------|----------|-------------|
| `GEO-ROADMAP.md` | `~/.geo-prospects/audits/<domain>/` | Ranked markdown action plan |
| `GEO-ROADMAP-<domain>.pdf` | Current working directory | Branded PDF version |
| `/tmp/geo-roadmap-data.json` | Temp | Structured JSON (input to PDF generator) |

---

## Roadmap Sections

The generated `GEO-ROADMAP.md` contains:

1. **Header** — Brand, score, business type, platform
2. **Executive Summary** — 4-6 sentence tailored overview (LLM-generated)
3. **How to Read This Roadmap** — Framing text about AI signals
4. **Top Priorities** — Top 5 items with full detail cards
5. **Quick Wins** — Direct control, low-to-medium difficulty, any impact
6. **High-Impact, Long-Term Opportunities** — Indirect/very difficult items worth planning for
7. **Full Ranked Action Plan** — Complete table of all items
8. **What Peakweb Can Implement** — Filtered by `peakwebFit: direct_service`
9. **Actions for Your Team or Partners** — Remaining items with guidance
10. **Appendix** — GEO scoring components

---

## Priority Scoring

Each action item is scored 0-100 by `compute_priority_score()` in `action_plan_generator.py`.

| Factor | Points |
|--------|--------|
| Score impact: Very High | 40 |
| Score impact: High | 30 |
| Score impact: Medium | 20 |
| Score impact: Low | 10 |
| Control: Direct | +20 |
| Control: Mixed | +8 |
| Control: Indirect | +0 |
| Speed: Immediate | +15 |
| Speed: Near-term | +8 |
| Speed: Long-term | +0 |
| Difficulty: Low | -0 |
| Difficulty: Medium | -5 |
| Difficulty: High | -12 |
| Difficulty: Very High | -20 |
| Is foundational/blocking | +10 |
| Affects 3+ AI platforms | +5 |
| Peakweb direct service | +3 |

Score is normalised to 0-100. Weights can be tuned in `PRIORITY_WEIGHTS` in `action_plan_generator.py`.

---

## Action Categories

| Category | Examples |
|----------|---------|
| **Technical** | Unblock AI crawlers, implement SSR, Core Web Vitals |
| **Schema** | LocalBusiness, Organization, FAQPage, Article/Author, sameAs links |
| **Content** | Answer block structure, author pages, original research |
| **Brand** | Google Business Profile, LinkedIn, Wikidata, Wikipedia, press coverage |
| **Platform** | Bing Webmaster Tools, platform-specific optimisations |

---

## Notes

- The skill uses a **two-layer design**: deterministic Python for structure and ranking, LLM for tailored prose.
- If the audit data is sparse or partial, the generator falls back to safe defaults and surfaces only actions supported by available evidence.
- All action item IDs are stable strings (`unblock_ai_crawlers`, `publish_llms_txt`, etc.) — suitable for tracking in a CRM or web app.
- To test the generator standalone: `python3 scripts/action_plan_generator.py <audit_dir>`
- To test the PDF generator standalone: `python3 scripts/generate_roadmap_pdf.py` (uses built-in sample data)
