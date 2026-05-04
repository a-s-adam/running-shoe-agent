-- Run this in the Supabase SQL editor before setting SHOE_CATALOG_BACKEND=supabase.
-- It keeps image thumbnails small enough for the Free plan by storing compressed WebP data URIs.

create table if not exists public.running_shoes (
    shoe_key text primary key,
    brand text not null,
    model text not null,
    category jsonb not null default '[]'::jsonb,
    price_usd numeric not null default 0,
    plate text not null default 'none',
    drop_mm numeric,
    weight_g integer,
    cushioning_level text,
    support_type text,
    heel_stack_mm numeric,
    forefoot_stack_mm numeric,
    best_for_distances jsonb not null default '[]'::jsonb,
    has_wide_options boolean,
    description text,
    image_url text,
    image_thumbnail_data_uri text,
    image_mime_type text,
    source_url text,
    source_name text,
    popularity_score numeric,
    review_count integer,
    average_rating numeric,
    sources jsonb not null default '[]'::jsonb,
    extra jsonb not null default '{}'::jsonb,
    scraped_at timestamptz,
    updated_at timestamptz not null default now()
);

create index if not exists idx_running_shoes_brand on public.running_shoes (brand);
create index if not exists idx_running_shoes_price on public.running_shoes (price_usd);
create index if not exists idx_running_shoes_source on public.running_shoes (source_name);
create index if not exists idx_running_shoes_category on public.running_shoes using gin (category);

alter table public.running_shoes enable row level security;

drop policy if exists "Public read running shoes" on public.running_shoes;
create policy "Public read running shoes"
on public.running_shoes
for select
using (true);

-- Use SUPABASE_SERVICE_ROLE_KEY for scraper upserts, or create a stricter write policy
-- if you need browser/client-side writes later.
