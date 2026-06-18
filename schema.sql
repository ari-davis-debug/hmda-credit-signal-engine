-- HMDA Credit-Signal Engine — system of record (Supabase / Postgres)
-- Scored accounts + contacts + CRM-sync log, with dedup and credit signal attached.

-- The national credit map: one row per ZIP, built from HMDA + Census.
create table credit_map (
    zip             text primary key,
    denial_rate     numeric(4,3)  not null,   -- HMDA, e.g. 0.270
    median_income   integer,                  -- Census
    households      integer,                  -- Census
    credit_tier     text,                     -- derived: low / mid / high-denial
    updated_at      timestamptz default now()
);

-- Scraped target businesses (the ICP), with the credit signal joined on.
create table companies (
    id              uuid primary key default gen_random_uuid(),
    name            text not null,
    vertical        text,                     -- med_spa | dental | beauty | hrt
    address         text,
    zip             text references credit_map(zip),
    state           text,
    denial_rate     numeric(4,3),             -- denormalized from credit_map at enrich time
    monthly_patients integer,                 -- per-vertical default, overridable
    avg_ticket      integer,                  -- per-vertical default, overridable
    lost_revenue_mo integer,                  -- revenue_model output, $/month
    source          text default 'apify',
    created_at      timestamptz default now(),
    unique (name, zip)                        -- dedup: same practice, same ZIP, once
);

-- Decision-makers resolved via the Clay waterfall.
create table contacts (
    id              uuid primary key default gen_random_uuid(),
    company_id      uuid references companies(id) on delete cascade,
    full_name       text,
    title           text,
    email           text,
    email_verified  boolean default false,
    enriched_by     text,                     -- which waterfall provider hit
    created_at      timestamptz default now(),
    unique (email)                            -- dedup: never store an email twice
);

-- Every CRM push, so the signal stays idempotent and auditable.
create table crm_sync_log (
    id              uuid primary key default gen_random_uuid(),
    company_id      uuid references companies(id) on delete cascade,
    crm             text,                     -- hubspot | salesforce
    denial_rate     numeric(4,3),             -- snapshot of the signal pushed
    lost_revenue_mo integer,
    synced_at       timestamptz default now()
);

create index on companies (zip);
create index on companies (vertical, state);
create index on contacts (company_id);
create index on crm_sync_log (company_id);
