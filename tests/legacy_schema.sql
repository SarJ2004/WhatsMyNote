-- The staging database as the old backend left it, for testing that 0002 applies
-- over it. It differs from 0001: user ids are varchar (text in confirmations),
-- ids and amounts are integer, timestamps are without time zone and have no
-- default, and the old tenant_isolation policies compare the claim as text.

drop table if exists confirmations, fx_rates, transfer_records, lending_records,
    income_records, budget_records, expense_records, account_records,
    records, model_usage cascade;
drop type if exists recordtype cascade;
drop type if exists lendingdirection cascade;

create type recordtype as enum
    ('LENDING', 'EXPENSE', 'ACCOUNT', 'BUDGET', 'TRANSFER', 'INCOME', 'REMINDER', 'TASK');
create type lendingdirection as enum ('LENT', 'BORROWED');

create table records (
    id          serial primary key,
    record_type recordtype not null,
    raw_text    text not null,
    created_at  timestamp not null,
    updated_at  timestamp not null,
    settled_at  timestamp,
    user_id     varchar(36) not null
);

create table lending_records (
    record_id           integer primary key references records(id) on delete cascade,
    person              varchar(255) not null,
    account             varchar(255),
    amount              integer not null,
    direction           lendingdirection not null,
    expected_payback_by date,
    source_account      varchar(255),
    amount_minor        integer,
    currency            char(3) not null default 'INR',
    converted_minor     integer,
    fx_rate             numeric
);

create table expense_records (
    record_id       integer primary key references records(id) on delete cascade,
    amount          integer not null,
    category        varchar(255) not null,
    merchant        varchar(255),
    payment_source  varchar(255),
    expense_date    date not null,
    item            varchar(255),
    notes           text,
    amount_minor    integer,
    currency        char(3) not null default 'INR',
    converted_minor integer,
    fx_rate         numeric
);

create table account_records (
    record_id       integer primary key references records(id) on delete cascade,
    name            varchar(255) not null,
    is_default      boolean not null,
    opening_balance integer not null,
    current_balance integer not null,
    currency        varchar(16),
    notes           text
);

create table budget_records (
    record_id    integer primary key references records(id) on delete cascade,
    category     varchar(255) not null,
    amount       integer not null,
    period       varchar(32) not null,
    budget_date  date,
    notes        text,
    amount_minor integer,
    currency     char(3) not null default 'INR'
);

create table income_records (
    record_id       integer primary key references records(id) on delete cascade,
    source          varchar(255) not null,
    deposit_account varchar(255),
    amount          integer not null,
    income_date     date not null,
    notes           text,
    amount_minor    integer,
    currency        char(3) not null default 'INR',
    converted_minor integer,
    fx_rate         numeric
);

create table transfer_records (
    record_id           integer primary key references records(id) on delete cascade,
    source_account      varchar(255) not null,
    destination_account varchar(255) not null,
    amount              integer not null,
    transfer_date       date not null,
    notes               text,
    amount_minor        integer,
    currency            char(3) not null default 'INR'
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
    user_id    text not null,
    action     jsonb not null,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null,
    used_at    timestamptz
);

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'anon') then
        create role anon;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'authenticated') then
        create role authenticated;
    end if;
end $$;
-- Supabase grants every public table to both roles by default.
grant usage on schema public to anon, authenticated;
grant all on all tables in schema public to anon, authenticated;
grant all on all sequences in schema public to anon, authenticated;

do $$
declare
    detail text;
begin
    alter table records enable row level security;
    create policy tenant_isolation on records for all
        using (user_id = current_setting('request.jwt.claim.sub', true))
        with check (user_id = current_setting('request.jwt.claim.sub', true));
    foreach detail in array array['account_records', 'expense_records', 'lending_records',
                                  'income_records', 'budget_records', 'transfer_records']
    loop
        execute format('alter table %I enable row level security', detail);
        execute format(
            'create policy tenant_isolation on %I for all '
            'using (record_id in (select id from records '
            'where user_id = current_setting(''request.jwt.claim.sub'', true))) '
            'with check (record_id in (select id from records '
            'where user_id = current_setting(''request.jwt.claim.sub'', true)))', detail);
    end loop;
    alter table confirmations enable row level security;
    create policy tenant_isolation on confirmations for all
        using (user_id = current_setting('request.jwt.claim.sub', true))
        with check (user_id = current_setting('request.jwt.claim.sub', true));
    alter table fx_rates enable row level security;
end $$;
