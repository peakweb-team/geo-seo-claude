---
name: geo-validate
description: Automated AI visibility validation using Perplexity API. Tests before/after GEO implementation to measure citation rate changes. Run baseline before fixes, then validation after to quantify improvement.
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
metadata:
  filePattern: "**/geo-validate*"
  bashPattern: "geo.validate|perplexity.*api"
---

# GEO Validation Skill

Automated before/after testing of AI visibility using Perplexity's API. Perplexity is the only major AI search engine with a public API that returns source citations, making it ideal for programmatic validation.

## Prerequisites

1. **Perplexity API Key** - Get from https://www.perplexity.ai/settings/api
2. Set environment variable: `export PERPLEXITY_API_KEY=pplx-xxxxx`

## Workflow

### Step 1: Create Query File

Create a file with test queries relevant to the client's business (one per line):

```bash
# Example: queries/acme-corp.txt

# Brand queries
What is Acme Corp?
Tell me about Acme Corp services
Acme Corp reviews

# Category queries
Best widget manufacturers in Ohio
Top industrial automation companies
Widget suppliers for manufacturing

# Comparison queries
Acme Corp vs WidgetCo comparison
Acme Corp alternatives

# Problem/solution queries
How to reduce widget defects in manufacturing
Industrial automation best practices
```

**Query selection tips:**
- Include 5-10 brand-specific queries
- Include 5-10 category/industry queries where they should appear
- Include 2-3 comparison queries
- Include 3-5 problem/solution queries matching their content
- Total of 15-25 queries is ideal for meaningful data

### Step 2: Run Baseline (Before GEO Fixes)

```bash
cd /Users/nathan/gitRepos/geo-seo-claude

python scripts/geo_validate.py \
  --domain acme-corp.com \
  --queries queries/acme-corp.txt \
  --output audits/acme-corp/baseline.json
```

Save this baseline before implementing any GEO fixes.

### Step 3: Implement GEO Fixes

Deploy the recommended changes from the GEO audit:
- Schema markup improvements
- Content citability enhancements
- llms.txt creation
- robots.txt updates for AI crawlers

**Wait 2-4 weeks** for AI systems to recrawl and reindex.

### Step 4: Run Validation (After GEO Fixes)

```bash
python scripts/geo_validate.py \
  --domain acme-corp.com \
  --queries queries/acme-corp.txt \
  --baseline audits/acme-corp/baseline.json \
  --output audits/acme-corp/validation.json \
  --report audits/acme-corp/validation-report.md
```

This generates:
- `validation.json` - Raw results
- `validation-report.md` - Human-readable comparison

## Output Example

```markdown
# GEO Validation Report: acme-corp.com

**Baseline:** 2026-03-01T10:00:00
**Current:** 2026-03-23T14:30:00

## Summary

| Metric | Baseline | Current | Change |
|--------|----------|---------|--------|
| Citation Rate | 12.0% | 36.0% | ↑ 24.0% |
| Queries Cited | 3/25 | 9/25 | +6 |

## Changes

### Improvements (6 queries now cited)
- ✓ `What is Acme Corp?`
- ✓ `Best widget manufacturers in Ohio`
- ✓ `Industrial automation best practices`
...

### Regressions (0 queries no longer cited)
_None_
```

## Interpreting Results

| Citation Rate Change | Interpretation |
|---------------------|----------------|
| +20% or more | Excellent - GEO fixes having major impact |
| +10-19% | Good - Meaningful improvement |
| +5-9% | Moderate - Some improvement, consider additional fixes |
| 0-4% | Minimal - May need more time or different approach |
| Negative | Regression - Investigate what changed |

## Limitations

- **Perplexity only** - Does not test ChatGPT or Google AIO (no APIs available)
- **Citation != Recommendation** - Being cited doesn't mean being recommended favorably
- **Timing** - AI reindexing takes 2-4 weeks; testing too early shows false negatives
- **Query sensitivity** - Results vary by exact query phrasing
- **API costs** - Perplexity API charges per request (~$0.005/query with sonar model)

## Complementary Manual Testing

For ChatGPT and Google AIO, use manual testing:

### ChatGPT (Manual)
1. Open ChatGPT with browsing enabled
2. Run same queries from your query file
3. Document: Was brand mentioned? Was site cited? What source was used?

### Google AIO (Manual)
1. Google each query
2. Check if AI Overview appears
3. Note if client content appears in overview or "Learn more" links

## Cost Estimate

- Perplexity sonar model: ~$0.005 per query
- 25 queries × 2 runs (baseline + validation) = 50 queries
- Estimated cost: ~$0.25 per client validation cycle
