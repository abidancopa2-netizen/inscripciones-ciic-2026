-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones · 11 · SPRINT 6 · TEXTOS LIMPIOS     contrato v5.5
--  Va después de 10. Se puede volver a correr.
--
--  La prueba de ataque del Sprint 6 encontró que nombres y apellidos guardaban caracteres invisibles y de dirección
--  (U+200B…U+200F, U+202A…U+202E, U+2060…U+2064, U+2066…U+2069, U+FEFF): con U+202E un nombre se puede mostrar al
--  revés en el panel y en el CSV. texto_limpio ahora los quita, además de los de control. Lo usan los datos de la
--  persona (página y panel), las actividades y el padrón.
-- ════════════════════════════════════════════════════════════════════════
begin;

do $$ begin
  if exists (select 1 from public.config where id = 1 and modo = 'PRODUCCION' and abierto) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
end $$;

create or replace function privado.version() returns text language sql immutable as $$ select '5.5-s6'::text $$;

create or replace function privado.texto_limpio(v jsonb, p_max int) returns text language sql immutable as $$
  select left(btrim(regexp_replace(
           btrim(regexp_replace(regexp_replace(regexp_replace(privado.jtext(v),
             '[​-‏‪-‮⁠-⁤⁦-⁩﻿]', '', 'g'),     -- invisibles y de dirección (Sprint 6)
             E'[\\x01-\\x1F\\x7F]', ' ', 'g'), '\s+', ' ', 'g')),
           '^[=+\-@]+', '')), p_max)
$$;

revoke all on all functions in schema privado from public, anon, authenticated;

commit;
