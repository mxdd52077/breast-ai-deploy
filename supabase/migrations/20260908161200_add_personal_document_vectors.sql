create extension if not exists vector with schema extensions;

create table public.document_chunks (
  id varchar(32) primary key,
  user_id varchar(32) not null references public.users(id) on delete cascade,
  document_id varchar(32) not null references public.documents(id) on delete cascade,
  fact_id varchar(32) unique references public.facts(id) on delete cascade,
  page integer not null check (page >= 1),
  location varchar(120) not null default '',
  content text not null,
  content_hash varchar(64) not null,
  review_status varchar(20) not null default 'pending' check (review_status in ('pending','confirmed','rejected')),
  embedding_model varchar(40) not null default 'apex-zh-char-v1',
  embedding extensions.vector(384)
);

create index document_chunks_user_status_idx
  on public.document_chunks(user_id, review_status);
create index document_chunks_document_id_idx
  on public.document_chunks(document_id);

alter table public.document_chunks enable row level security;
revoke all on table public.document_chunks from anon, authenticated;

insert into public.document_chunks (
  id, user_id, document_id, fact_id, page, location, content,
  content_hash, review_status, embedding_model, embedding
)
select
  md5('fact:' || f.id), f.user_id, f.document_id, f.id, f.page,
  f.location, f.quote, md5(f.quote),
  f.status, 'apex-zh-char-v1', null
from public.facts f
on conflict (fact_id) do nothing;

comment on table public.document_chunks is
  'Account-scoped, review-gated evidence chunks for exact hybrid retrieval.';
comment on column public.document_chunks.embedding is
  '384-dimensional normalized apex-zh-char-v1 vector; exact search is used at current scale.';
