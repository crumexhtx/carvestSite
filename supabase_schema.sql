create table if not exists public.buyer_reports (
  id text primary key,
  access_token_hash text not null,
  vin text not null,
  email text,
  request_json jsonb not null,
  preview_json jsonb not null,
  full_json jsonb,
  status text not null,
  stripe_session_id text,
  stripe_payment_intent_id text,
  created_at double precision not null,
  paid_at double precision,
  updated_at double precision not null
);

create index if not exists idx_buyer_reports_stripe_session
  on public.buyer_reports (stripe_session_id);

alter table public.buyer_reports enable row level security;

-- Soft-launch waitlist for paid-report notifications.
create table if not exists public.waitlist_emails (
  email text primary key,
  source text,
  created_at double precision not null
);

alter table public.waitlist_emails enable row level security;

create table if not exists public.product_feedback (
  id text primary key,
  email text,
  category text not null,
  message text not null,
  page_path text,
  created_at double precision not null
);

alter table public.product_feedback enable row level security;

-- The FastAPI backend uses the Supabase service-role key and bypasses RLS.
-- Do not expose that key to the frontend.
