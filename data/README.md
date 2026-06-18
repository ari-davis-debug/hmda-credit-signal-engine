# data/ — building the national credit map

This engine runs on one derived table: **`credit_map.csv`**, ~42,000 ZIPs each scored with
a mortgage-denial rate from 1% to 31%. It is **not checked in** — it's rebuildable by anyone
from the public APIs below, and shipping it would bake in stale data.

## How it's built

1. **Pull HMDA denials** from the FFIEC Data Browser API
   (https://ffiec.cfpb.gov/data-browser/), filtered to denied applications, aggregated to
   ZIP-level denial rates.
2. **Pull Census** demographics + income by ZIP (https://data.census.gov/) to size the
   addressable population and derive a `credit_tier`.
3. **Join** on ZIP → write `credit_map.csv` with the columns the engine expects.

## Schema

| column | source | example |
|---|---|---|
| `zip` | key | `78701` |
| `denial_rate` | HMDA | `0.270` |
| `median_income` | Census | `54300` |
| `households` | Census | `12840` |
| `credit_tier` | derived | `high-denial` |

## Refresh

HMDA publishes annually; Census on its own cadence. Rebuild the map when either updates —
the rest of the pipeline reads the CSV and needs no changes.
