---
name: geo-perplexity
description: Generate targeted Perplexity test queries from audit data and run them to measure AI citation visibility. Produces a baseline JSON and summary. Run again later with a previous baseline to measure improvement.
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
---

# GEO Perplexity Citation Test

Generates a tailored query set from existing audit data and tests them against Perplexity's API to measure how often the client's domain is cited. Designed for before/after measurement of GEO work.

## Prerequisites

- Existing audit JSON in `/Users/nathan/.geo-prospects/audits/{domain}/`
- `PERPLEXITY_API_KEY` set in `/Users/nathan/gitRepos/geo-seo-claude/.env`

## Invocation

```
/geo-perplexity modernnomadhome.com
/geo-perplexity modernnomadhome.com --baseline  # compare against previous run
```

---

## Step 1: Find the Audit Data

Look for an audit JSON in the client's audit folder:

```
/Users/nathan/.geo-prospects/audits/{domain}/
```

Check for files matching: `*audit*.json`, `*GEO*.json`, `geo-report-data.json`, `pitch-deck-data.json` — in that order of preference. Read the first match. Extract:

- `domain`
- `client_name`
- `business_profile.type` and `business_profile.subtype`
- `business_profile.location.city` and `.state`
- `business_profile.categories` (array)
- `critical_issues` (array of issue objects)
- `opportunities` (array)
- Any competitor names if present
- Any content topics or service names if present

If no audit JSON exists, tell the user and stop.

---

## Step 2: Generate Queries

Using the extracted audit data, generate **20–25 queries** covering these categories:

### Brand Queries (4–5)
Direct questions about the business by name:
- "What is [Client Name]?"
- "Tell me about [Client Name] in [City]"
- "[Client Name] reviews"
- "Is [Client Name] a good [business type]?"
- "[Client Name] [City] — is it worth visiting?" (for local/retail)

### Category / Local Queries (5–6)
Queries where they *should* appear if well-optimized:
- "Best [business subtype] in [City]"
- "Top [business subtype] stores in [City, State]"
- "[City] [business subtype] recommendations"
- For each major product category: "Where to buy [category] in [City]"
- "Best [category] shops in [City]"

### Product / Service Queries (4–5)
Based on specific categories or services from the audit:
- "Best [specific category] for [use case]"
- "Where to find [specific product type] online"
- "[Category] buying guide"
- "Affordable [category] [City]"

### Problem / Solution Queries (3–4)
Questions the business's content should answer:
- "How to [relevant problem their products solve]"
- "Tips for [relevant topic]"
- "[Common question in their niche]"

### Comparison Queries (2–3)
- "[Client Name] vs [common competitor type]"
- "Alternatives to [Client Name]"
- "Similar stores to [Client Name] in [City]"

**Query writing rules:**
- Write natural conversational questions, not keyword strings
- Vary phrasing — don't repeat the same pattern
- Keep them under 15 words each
- Avoid overly specific queries that only this one business could answer

---

## Step 3: Save the Queries File

Save to:
```
/Users/nathan/.geo-prospects/audits/{domain}/perplexity-queries.txt
```

Format:
```
# Perplexity Citation Test Queries — {Client Name}
# Generated: {date}
# Domain: {domain}

# Brand Queries
What is Modern Nomad Home?
...

# Category / Local Queries
Best home decor stores in Denver
...
```

Tell the user the queries file has been saved and show the full list. Ask if they want to adjust any queries before running. If they confirm, proceed to Step 4.

---

## Step 4: Check for Existing Baseline

Look for a previous results file:
```
/Users/nathan/.geo-prospects/audits/{domain}/perplexity-baseline.json
```

- If it **does not exist**: this is a baseline run. Proceed to Step 5.
- If it **does exist**: ask the user whether to run a new validation (comparing against the baseline) or overwrite the baseline. Default to validation run.

---

## Step 5: Run the Validation Script

Run from the project root:

```bash
cd /Users/nathan/gitRepos/geo-seo-claude

# Baseline run (no previous baseline exists):
python scripts/geo_validate.py \
  --domain {domain} \
  --queries /Users/nathan/.geo-prospects/audits/{domain}/perplexity-queries.txt \
  --output /Users/nathan/.geo-prospects/audits/{domain}/perplexity-baseline.json

# Validation run (comparing against baseline):
python scripts/geo_validate.py \
  --domain {domain} \
  --queries /Users/nathan/.geo-prospects/audits/{domain}/perplexity-queries.txt \
  --baseline /Users/nathan/.geo-prospects/audits/{domain}/perplexity-baseline.json \
  --output /Users/nathan/.geo-prospects/audits/{domain}/perplexity-validation.json \
  --report /Users/nathan/.geo-prospects/audits/{domain}/perplexity-validation-report.md
```

The script auto-loads `PERPLEXITY_API_KEY` from `.env` in the project root.

---

## Step 6: Report Results

After the script completes, read the output JSON and present a clean summary:

```
## Perplexity Citation Results — {Client Name}

**Run date:** {date}
**Queries tested:** {n}
**Queries where domain was cited:** {n} ({pct}%)

### Cited queries:
- ✓ "..."
- ✓ "..."

### Not cited:
- ✗ "..."
- ✗ "..."

**Estimated cost:** ~${cost} (at $0.005/query)
```

For a **validation run**, also show the change table from the report:
```
| Metric         | Baseline | Current | Change |
|----------------|----------|---------|--------|
| Citation Rate  | X%       | Y%      | +Z%    |
| Queries Cited  | n/N      | n/N     | +n     |
```

And list any improvements and regressions by query.

---

## Cost Reference

| Queries | Estimated Cost |
|---------|---------------|
| 20      | ~$0.10        |
| 25      | ~$0.13        |
| 25 × 2 runs | ~$0.25   |
