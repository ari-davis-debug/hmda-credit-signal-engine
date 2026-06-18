# Architecture — HMDA Credit-Signal Engine

A deeper look at the data model, the join logic, and the design decisions behind the
pipeline. The high-level DAG is in the [README](README.md); this is the engineering detail.

## Design goal

One requirement drove every decision: **the signal must be a real, defensible number about
the recipient's own business — and it must live where their reps already work (the CRM),
not just in a one-off send.** Everything else exists to deliver that number to the right
account.

## The data layer — building the national credit map

The credit map is a single table keyed by ZIP, joining two public federal sources.

**1. HMDA (Home Mortgage Disclosure Act), via FFIEC/CFPB.**
Every US mortgage application with disposition (originated / approved / denied) and denial
reason codes. Pulled from the [FFIEC Data Browser API](https://ffiec.cfpb.gov/data-browser/),
filtered to denials, and aggregated to ZIP-level denial rates. This is the credit signal —
the share of applicants in a ZIP who can't get approved.

**2. US Census Bureau.**
Demographic and income data layered on top to size the addressable population per ZIP and
sharpen targeting (a high denial rate in a dense, high-volume ZIP is worth more than the
same rate in a sparse one).

The output is a map of **~42,000 ZIPs, each scored with a denial rate from 1% to 31%.**

| Field | Source | Example |
|---|---|---|
| `zip` | key | `78701` |
| `denial_rate` | HMDA | `0.27` |
| `median_income` | Census | `$54,300` |
| `households` | Census | `12,840` |
| `credit_tier` | derived | `high-denial` |

## The join — business → ZIP → signal

Scraped businesses arrive with an address. The engine extracts the ZIP, joins to the credit
map, and attaches `denial_rate` + the revenue-impact number to every record. ZIPs that don't
resolve cleanly fall back to county-level aggregates so no record is dropped silently.

## The revenue model

The model is intentionally simple and transparent — a practice owner can check the math:

```
lost_revenue_per_month = denial_rate × monthly_new_patients × avg_treatment_value
```

Defaults (`monthly_new_patients`, `avg_treatment_value`) are set per vertical (a med spa's
ticket ≠ a dental office's) and can be overridden per account when better data exists. The
output is deliberately conservative — under-claiming the loss is more credible than
over-claiming it.

## The messaging layer

The personalization pipeline is constrained, not freeform:
- **Subject** is templated around the real number (`{denied} out of 100 patients can't get
  financing in {zip}`) so the strongest fact leads.
- **Body** follows a fixed frame: name the loss → quantify it → position as a *layer on top
  of* existing financing → soft CTA. The LLM fills the vertical-specific language; it does
  not invent numbers.

## The CRM hand-off — the real output

The engine's deliverable is not a send list, it's an **upgraded CRM.** `crm_sync.py` upserts
each scored account into the client's CRM (HubSpot / Salesforce-style), writing the
HMDA-derived denial rate, the monthly revenue at risk, and the pre-written messaging onto the
record — keyed by domain, so it's idempotent and never duplicates an account.

Design decisions:
- **Keyed by domain, upsert not insert** — re-running the engine refreshes the signal on
  existing accounts instead of creating duplicates.
- **Generic field map** (`FIELD_MAP`) — the engine's fields translate to whatever custom
  properties the client's CRM uses, so it drops into an existing CRM without a schema fight.
- **Never push a signal-less account** — if a ZIP has no denial rate, the account isn't
  synced. Reps only ever see accounts that carry a real number.

The result: the client's reps open their own CRM and find target accounts that already say
*how many of their patients can't get financing* and *how many dollars/month they're
losing* — with the message to send already attached. The signal keeps working long after
the campaign.

## System of record

Supabase (Postgres) holds scored accounts + contacts with deduplication, before and
alongside the CRM push. See [`schema.sql`](schema.sql).

## Why it generalizes

Nothing above is specific to credit data. Replace the HMDA + Census layer with any public
signal (OSHA, WARN, EDGAR, EPA, state licensing) and the rest of the pipeline — scrape,
enrich, model the revenue impact, generate, sync to CRM — is unchanged. The engine is a
template for **public-data-to-revenue-signal CRM enrichment.**
