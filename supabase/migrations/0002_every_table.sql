-- Isolation on every table, not only records, plus the columns and tables the
-- chat needs. Additive and idempotent: it can be applied more than once, and over
-- a database that already carries its own policies, without losing data.

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'anon') then
        create role anon;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'authenticated') then
        create role authenticated;
    end if;
end $$;

-- The account currency a converted amount is in, so reads never mix currencies.
alter table expense_records add column if not exists converted_currency char(3);
alter table income_records add column if not exists converted_currency char(3);
alter table lending_records add column if not exists converted_currency char(3);
alter table transfer_records add column if not exists converted_minor bigint;
alter table transfer_records add column if not exists converted_currency char(3);
alter table transfer_records add column if not exists fx_rate numeric;

-- When a loan happened, and whether a row pays an earlier loan back.
alter table lending_records add column if not exists lending_date date;
alter table lending_records add column if not exists is_repayment boolean not null default false;

-- Minor units overflow integer at about 21 million in the major unit.
alter table expense_records
    alter column amount type bigint, alter column amount_minor type bigint,
    alter column converted_minor type bigint;
alter table account_records
    alter column opening_balance type bigint, alter column current_balance type bigint;
alter table budget_records
    alter column amount type bigint, alter column amount_minor type bigint;
alter table income_records
    alter column amount type bigint, alter column amount_minor type bigint,
    alter column converted_minor type bigint;
alter table transfer_records
    alter column amount type bigint, alter column amount_minor type bigint;
alter table lending_records
    alter column amount type bigint, alter column amount_minor type bigint,
    alter column converted_minor type bigint;

create index if not exists records_user_type on records (user_id, record_type);

-- The old backend filled these timestamps in code, so an older database has no default.
alter table records alter column created_at set default now();
alter table records alter column updated_at set default now();

-- Every money table keeps a legacy `amount` column in whole major units, the way
-- the old backend wrote it. The engine writes amount_minor // 100 there and reads
-- only amount_minor and converted_minor, which hold exact minor units.

-- Model calls per user per day, for the daily ceiling. Only the engine's own
-- connection role reads or writes it; a signed-in user cannot reset a counter.
create table if not exists model_usage (
    user_id uuid    not null,
    day     date    not null,
    calls   integer not null default 0,
    primary key (user_id, day)
);

-- A detail row is visible only when the record it belongs to is the caller's.
-- A pooled connection keeps an emptied claim as '' rather than null, hence nullif.
do $$
declare
    detail text;
begin
    foreach detail in array array['expense_records', 'account_records', 'budget_records',
                                  'income_records', 'transfer_records', 'lending_records']
    loop
        execute format('alter table %I enable row level security', detail);
        execute format('drop policy if exists tenant_isolation on %I', detail);
        execute format('drop policy if exists %I on %I', detail || '_owner', detail);
        execute format(
            'create policy %1$I on %2$I '
            'using (exists (select 1 from records r where r.id = %2$I.record_id '
            'and r.user_id = nullif(current_setting(''request.jwt.claim.sub'', true), '''')::uuid)) '
            'with check (exists (select 1 from records r where r.id = %2$I.record_id '
            'and r.user_id = nullif(current_setting(''request.jwt.claim.sub'', true), '''')::uuid))',
            detail || '_owner', detail);
    end loop;
end $$;

alter table records enable row level security;
drop policy if exists tenant_isolation on records;
drop policy if exists records_owner on records;
create policy records_owner on records
    using (user_id = nullif(current_setting('request.jwt.claim.sub', true), '')::uuid)
    with check (user_id = nullif(current_setting('request.jwt.claim.sub', true), '')::uuid);

alter table confirmations enable row level security;
drop policy if exists tenant_isolation on confirmations;
drop policy if exists confirmations_owner on confirmations;
create policy confirmations_owner on confirmations
    using (user_id = nullif(current_setting('request.jwt.claim.sub', true), '')::uuid)
    with check (user_id = nullif(current_setting('request.jwt.claim.sub', true), '')::uuid);

-- Reference rates are public data. Users may read them; only the engine writes.
alter table fx_rates enable row level security;
drop policy if exists tenant_isolation on fx_rates;
drop policy if exists fx_rates_read on fx_rates;
create policy fx_rates_read on fx_rates for select to authenticated using (true);
revoke insert, update, delete on fx_rates from authenticated;

alter table model_usage enable row level security;
drop policy if exists tenant_isolation on model_usage;
revoke all on model_usage from authenticated;

-- Clients reach data only through the engine, never through the REST API with
-- the public key, and truncate would skip row-level security entirely.
revoke all on all tables in schema public from anon;
revoke all on all sequences in schema public from anon;
alter default privileges in schema public revoke all on tables from anon;
revoke truncate, references, trigger on all tables in schema public from authenticated;
