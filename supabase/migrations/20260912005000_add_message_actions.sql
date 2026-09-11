alter table public.messages
  add column action_fact_ids jsonb not null default '[]'::jsonb;
