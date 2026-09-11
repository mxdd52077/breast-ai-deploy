drop table if exists public.generations cascade;
drop table if exists public.project_products cascade;
drop table if exists public.assets cascade;
drop table if exists public.projects cascade;
create table public.users (id varchar(32) primary key, username varchar(100) not null unique, password_hash text not null, name varchar(60) not null, demo boolean not null default false, institution_access boolean not null default false, created double precision not null);
create table public.sessions (token_hash varchar(64) primary key, user_id varchar(32) not null references public.users(id) on delete cascade, csrf varchar(64) not null, expires double precision not null);
create index sessions_user_id_idx on public.sessions(user_id);
create table public.documents (id varchar(32) primary key, user_id varchar(32) not null references public.users(id) on delete cascade, name varchar(200) not null, digest varchar(64) not null, extension varchar(10) not null, size integer not null, pages jsonb not null default '[]'::jsonb, status varchar(32) not null default 'queued', error text not null default '', method varchar(60) not null default '', created double precision not null, unique(user_id,digest));
create index documents_user_id_idx on public.documents(user_id);
create table public.jobs (id varchar(32) primary key, document_id varchar(32) not null unique references public.documents(id) on delete cascade, state varchar(32) not null default 'queued', lease double precision not null default 0, claim varchar(32) not null default '', attempts integer not null default 0);
create index jobs_state_idx on public.jobs(state);
create table public.facts (id varchar(32) primary key, document_id varchar(32) not null references public.documents(id) on delete cascade, user_id varchar(32) not null references public.users(id) on delete cascade, category varchar(30) not null, value text not null, quote text not null, page integer not null, location varchar(120) not null default '', status varchar(20) not null default 'pending', scheduled_date varchar(10), scheduled_time varchar(5), conflict boolean not null default false, note text not null default '', version integer not null default 1);
create index facts_document_id_idx on public.facts(document_id);
create index facts_user_id_idx on public.facts(user_id);
create table public.tasks (id varchar(32) primary key, user_id varchar(32) not null references public.users(id) on delete cascade, fact_id varchar(32) not null unique references public.facts(id) on delete cascade, title text not null, due_date varchar(10) not null, due_time varchar(5), category varchar(30) not null, status varchar(20) not null default 'pending', active boolean not null default true, version integer not null default 1, updated double precision not null);
create index tasks_user_id_idx on public.tasks(user_id);
create table public.messages (id varchar(32) primary key, user_id varchar(32) not null references public.users(id) on delete cascade, role varchar(12) not null, text text not null, citations jsonb not null default '[]'::jsonb, status varchar(32) not null default 'supported', created double precision not null);
create index messages_user_id_idx on public.messages(user_id);
create table public.audit (id varchar(32) primary key, user_id varchar(32) not null references public.users(id) on delete cascade, action varchar(60) not null, resource varchar(32) not null, detail jsonb not null default '{}'::jsonb, created double precision not null);
create index audit_user_id_idx on public.audit(user_id);
create table public.simulations (id varchar(32) primary key, user_id varchar(32) not null references public.users(id) on delete cascade, name varchar(100) not null, inputs jsonb not null, results jsonb not null, analysis jsonb not null, created double precision not null);
create index simulations_user_id_idx on public.simulations(user_id);

alter table public.users enable row level security;
alter table public.sessions enable row level security;
alter table public.documents enable row level security;
alter table public.jobs enable row level security;
alter table public.facts enable row level security;
alter table public.tasks enable row level security;
alter table public.messages enable row level security;
alter table public.audit enable row level security;
alter table public.simulations enable row level security;
revoke all on all tables in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;

insert into storage.buckets (id,name,public,file_size_limit,allowed_mime_types)
values ('patient-documents','patient-documents',false,10485760,array['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','text/plain','image/jpeg','image/png','image/webp'])
on conflict (id) do nothing;
