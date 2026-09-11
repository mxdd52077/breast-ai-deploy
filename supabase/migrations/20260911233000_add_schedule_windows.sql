alter table public.facts
  add column scheduled_end_date varchar(10),
  add column scheduled_end_time varchar(5),
  add column schedule_basis text not null default '';

alter table public.tasks
  add column due_end_date varchar(10),
  add column due_end_time varchar(5);
