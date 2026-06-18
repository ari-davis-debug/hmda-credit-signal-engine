# HMDA Credit-Signal Engine

**Turn federal credit data into a per-account revenue signal — and write it straight into
the client's CRM.**

This engine converts two public federal datasets into a per-ZIP "credit denial" score,
calculates the exact revenue a practice is losing to financing denials, writes the email
that proves it, and **pushes the whole signal back into the client's CRM** so their reps
work a list that already carries the number and the message. It powered an outbound program
that moved a patient-financing company's meeting rate from **1% → 5%**.

> The core idea: **the data does the selling.** When you can tell a med-spa owner that
> *27 out of 100 patients in their ZIP can't get financing — $27,000/month walking out the
> door* — you're not pitching. You're describing their situation with federal data.

---

## The thesis (one sentence)

> If people in a ZIP can't get approved for a **mortgage**, they can't get approved for
> **healthcare financing** either — so mortgage-denial data is a free, public proxy for the
> revenue a practice loses every month to point-of-care financing denials.

CareCredit and its competitors deny **40–50% of applicants** at the point of care. That's
revenue the practice never sees and never quantifies. This engine quantifies it for **every
ZIP code in the country** and turns the number into a CRM-ready signal.

---

## Architecture (the DAG)

```
              ┌──────────────────────────────┐
              │   PUBLIC FEDERAL DATA LAYER   │
              │  HMDA (FFIEC/CFPB)  +  Census │
              └───────────────┬──────────────┘
                              │  national credit map
                              │  42,000 ZIPs · denial 1–31%
                              ▼
   Apify ────────►  Credit-Signal Enrichment  ────────►  Revenue-Impact Model
 (scrape ICP by ZIP)   (business → ZIP →                 (denial% × patients ×
  med spa / dental /      denial rate)                     avg ticket = $/mo lost)
  beauty / HRT)                                                  │
                                                                 ▼
                                                      Message Generation (LLM)
                                                      ZIP-specific subject + body
                                                                 │
                            ┌─────────────────────────────────────┤
                            ▼                                      ▼
                    Clay (12-provider                     Supabase (system of
                    contact waterfall →                   record: scored accounts,
                    decision-maker + email)               dedup, history)
                            └────────────────┬─────────────────────┘
                                             ▼
                              ┌──────────────────────────────┐
                              │   CRM ENRICHMENT HAND-OFF     │
                              │  Push each scored account +   │
                              │  the messaging into the       │
                              │  client's CRM — their reps     │
                              │  open a list that already      │
                              │  carries the signal + pitch.   │
                              └──────────────────────────────┘
```

A one-way pipeline (a DAG): every stage feeds the next, no loops.

---

## How it works, stage by stage

### 1. Scrape the ICP by ZIP — `src/scrape.py`
Apify (Google Maps scraper) pulls every business matching the ICP — med spas, dental,
beauty clinics, hormone-therapy centers — **iterating ZIP by ZIP**. That casts a wider net
than scraping by city/state and lines records up for the credit join.

### 2. Enrich with the credit signal — `src/enrich_credit.py`
Match each business to its ZIP's mortgage-denial rate from the **national credit map**
(HMDA + Census — see `data/`). Every record comes out with a **denial rate** and a
**revenue-impact number**. ZIPs that don't resolve fall back to county-level aggregates so
nothing is dropped silently.

### 3. Model the revenue they're losing — `src/revenue_model.py`
The math that makes the email land:

```
denial_rate (from HMDA for their ZIP)   = 27%
monthly_new_patients                    = 100
avg_treatment_value                     = $1,000
─────────────────────────────────────────────────
lost_treatments  = 100 × 27%            = 27 / month
lost_revenue     = 27 × $1,000          = $27,000 / month
```

Computed per ZIP, for all 42,000 ZIPs, via API. Conservative by design — under-claiming the
loss is more credible than over-claiming it.

### 4. Generate the message — `src/personalize.py`
An LLM writes a ZIP-specific subject and body. The **subject carries the real number**:

> `RE: 27 out of 100 patients can't get financing in 78701`

Both numbers are real — calculated from federal data for that exact ZIP. The body frames it
as revenue lost and positions the product as a **layer on top of** the practice's existing
financing, not a replacement: *"essentially free money you're currently leaving on the
table."* The model fills vertical-specific language but **never invents a number.**

### 5. Find the human — `src/contacts.py` (Clay)
A **12-provider waterfall** resolves the decision-maker (practice manager / owner), verifies
the email, gets the title — the actual person, never `info@`.

### 6. Store as system of record — `schema.sql` (Supabase / Postgres)
Scored accounts + contacts, deduplicated, with history.

### 7. **Enrich the client's CRM — `src/crm_sync.py`** ← the output
This is the real deliverable. The engine doesn't just generate emails — it **upgrades the
client's own CRM.** Every target account is upserted with:
- the HMDA-derived **denial rate**,
- the calculated **monthly revenue at risk**,
- and the **ready-to-use messaging**, written onto the record.

Their reps open their CRM and the signal *and* the pitch are already there. The engine
becomes the client's GTM data layer — not just a one-off campaign.

---

## The story behind it

The client was a patient-financing company (a CareCredit alternative with higher approval
rates) selling to healthcare practices — med spas, dental, beauty, hormone-therapy — across
7 verticals and 28 states. Their outbound was generic: *"we offer patient financing"* —
exactly what every competitor said. Meeting rate stuck at **1%**.

The unlock was a question: *how do you find practices where patients actually need
financing — and prove it to the owner with data before they reply?* HMDA answered it. By
treating mortgage-denial rates as a credit proxy and layering Census on top, every practice
got a real, local, federal number about its own lost revenue. The data did the selling, and
the same signal — pushed into the client's CRM — kept selling long after the campaign.

---

## Results

| Metric | Value |
|---|---|
| Meeting rate before | 1% |
| **Meeting rate after** | **5%** |
| Time to see lift | 2 weeks |
| Meetings booked | ~300 |
| Pipeline generated | ~$20M |

A/B tested against control groups, with pre-committed kill/park/scale gates on reply-rate
thresholds.

---

## The transferable pattern

The architecture is signal-agnostic. Swap the federal dataset, keep the machine:

| Public signal | Reveals | Sells to |
|---|---|---|
| **HMDA mortgage denials** | who can't get financing | patient financing, BNPL, lenders |
| **OSHA violations** | safety pain | industrial safety, compliance |
| **WARN Act filings** | financial distress | restructuring, staffing, M&A |
| **SEC EDGAR** | compliance/disclosure triggers | legal, audit, GRC |
| **EPA enforcement** | environmental violations | remediation, ESG |
| **State licensing** | credential gaps | regtech, insurance |

The pattern: **find public data that reveals *why* they'd buy right now → automate the
enrichment → calculate the revenue impact → write it into their CRM.**

---

## Tech stack

| Layer | Tool |
|---|---|
| Scraping | Apify (Google Maps, by ZIP) |
| Credit data | HMDA (FFIEC/CFPB), US Census Bureau |
| Contact enrichment | Clay (12-provider waterfall) |
| Database | Supabase (Postgres) |
| CRM sync | HubSpot / Salesforce upsert |
| Bot hosting | Railway (Python) |
| Generation | LLM personalization pipeline |

---

## Repo structure

```
hmda-credit-signal-engine/
├── README.md                  ← you are here
├── ARCHITECTURE.md            ← deep dive: data model, join logic, design decisions
├── requirements.txt
├── schema.sql                 ← Supabase: scored accounts + contacts
├── data/
│   └── README.md              ← how the 42K-ZIP national credit map is built (HMDA+Census)
└── src/
    ├── scrape.py              ← Apify ICP scrape, by ZIP
    ├── enrich_credit.py       ← business → ZIP → denial rate
    ├── revenue_model.py       ← denial% × patients × ticket = $/mo lost
    ├── personalize.py         ← LLM: ZIP-specific subject + body
    ├── contacts.py            ← Clay waterfall → decision-maker + email
    └── crm_sync.py            ← push the signal + messaging into the client's CRM
```

---

## A note on data & privacy

This is a **reference architecture** of a shipped system. It contains **no client data, no
contact lists, and no proprietary credit map** — only the public federal data sources
(HMDA, Census), the pipeline design, and representative code. The credit map is rebuildable
by anyone from the linked public APIs.

## Data sources

- **HMDA / FFIEC** — federal mortgage denial rates: https://ffiec.cfpb.gov/data-browser/
- **US Census Bureau** — demographics + income by ZIP: https://data.census.gov/
- Combined → national credit map: 42,000 ZIPs, denial rates 1–31%
