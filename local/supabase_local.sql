-- ════════════════════════════════════════════════════════════════════════
--  SOLO PARA PROBAR EN TU COMPUTADORA (no se corre en Supabase).
--  Crea en un PostgreSQL local lo que Supabase ya trae: los roles anon y
--  authenticated, el esquema extensions y una versión mínima de auth.users
--  y auth.mfa_factors. Correr ANTES de 01_esquema.sql.
-- ════════════════════════════════════════════════════════════════════════
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
end $$;
create schema if not exists extensions;
create schema if not exists auth;
create extension if not exists pgcrypto with schema extensions;
create table if not exists auth.users (
  id     uuid primary key default extensions.gen_random_uuid(),
  email  text unique not null
);
create table if not exists auth.mfa_factors (
  id       uuid primary key default extensions.gen_random_uuid(),
  user_id  uuid not null references auth.users (id) on delete cascade,
  status   text not null default 'verified'
);
