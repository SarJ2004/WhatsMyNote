-- WhatsMyNote schema. This file is the only description of the database.
-- The staging tables were empty when this was written, so it drops and recreates.

drop table if exists confirmations, fx_rates, transfer_records, lending_records,
    income_records, budget_records, expense_records, account_records,
    records cascade;
drop type if exists recordtype cascade;
drop type if exists lendingdirection cascade;

create type recordtype as enum
    ('LENDING', 'EXPENSE', 'ACCOUNT', 'BUDGET', 'TRANSFER', 'INCOME', 'REMINDER', 'TASK');
create type lendingdirection as enum ('LENT', 'BORROWED');

create table records (
    id          bigint generated always as identity primary key,
    user_id     uuid not null,
    record_type recordtype not null,
    raw_text    text not null,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),
    settled_at  timestamptz
);

create table expense_records (
    record_id       bigint primary key references records(id) on delete cascade,
    amount          integer not null,
    amount_minor    integer not null,
    currency        char(3) not null,
    converted_minor integer not null,
    fx_rate         numeric,
    category        text not null,
    merchant        text,
    payment_source  text,
    item            text,
    expense_date    date not null,
    notes           text
);

create table account_records (
    record_id        bigint primary key references records(id) on delete cascade,
    name             text not null,
    currency         char(3) not null,
    opening_balance  integer not null default 0,
    current_balance  integer not null default 0,
    is_default       boolean not null default false,
    notes            text
);

create table budget_records (
    record_id   bigint primary key references records(id) on delete cascade,
    category    text not null,
    amount      integer not null,
    amount_minor integer not null,
    currency    char(3) not null,
    period      text not null default 'monthly',
    budget_date date,
    notes       text
);

create table income_records (
    record_id       bigint primary key references records(id) on delete cascade,
    amount          integer not null,
    amount_minor    integer not null,
    currency        char(3) not null,
    converted_minor integer not null,
    fx_rate         numeric,
    source          text not null,
    deposit_account text,
    income_date     date not null,
    notes           text
);

create table transfer_records (
    record_id           bigint primary key references records(id) on delete cascade,
    amount              integer not null,
    amount_minor        integer not null,
    currency            char(3) not null,
    source_account      text not null,
    destination_account text not null,
    transfer_date       date not null,
    notes               text
);

create table lending_records (
    record_id           bigint primary key references records(id) on delete cascade,
    amount              integer not null,
    amount_minor        integer not null,
    currency            char(3) not null,
    converted_minor     integer not null,
    fx_rate             numeric,
    person              text not null,
    direction           lendingdirection not null,
    account             text,
    expected_payback_by date,
    notes               text
);

create table fx_rates (
    rate_date date not null,
    base      char(3) not null,
    quote     char(3) not null,
    rate      numeric not null,
    primary key (rate_date, base, quote)
);

create table confirmations (
    token      text primary key,
    user_id    uuid not null,
    action     jsonb not null,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null,
    used_at    timestamptz
);

-- The role Supabase provides. Created here so plain Postgres behaves the same.
do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'authenticated') then
        create role authenticated;
    end if;
end $$;
grant usage on schema public to authenticated;
grant select, insert, update, delete on all tables in schema public to authenticated;

-- Isolation. A row is visible only to the user the transaction role names.
alter table records enable row level security;
create policy records_owner on records
    using (user_id = current_setting('request.jwt.claim.sub', true)::uuid)
    with check (user_id = current_setting('request.jwt.claim.sub', true)::uuid);

-- The definer function must not be callable by anonymous or signed-in clients.
-- It exists only on Supabase, so the guard keeps this file runnable on plain Postgres.
do $$
begin
    if exists (select 1 from pg_proc where proname = 'rls_auto_enable') then
        revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
    end if;
end $$;
