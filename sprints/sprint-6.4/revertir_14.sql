-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones · 14 · SPRINT 6.4 · MARCHA ATRÁS DEL "YA INSCRITO"     contrato v5.5
--  NO es una migración pendiente: vive en sprints/sprint-6.4/ y instalar.py no la ve.
--  Solo si el propietario decide dejar de mostrar los grupos por DNI: copiarla a supabase/14_sprint64_revertir.sql
--  y aplicarla con instalar.py siguiendo la misma secuencia §20.1 (respaldo, cerrar, respaldo, aplicar, abrir).
--
--  Vuelve privado.duplicado al aviso solo (como en 5.5-s6). privado.ya_inscrito queda, sin uso. Versión 5.5-s6.4-r.
--  La página del 6.4 sigue funcionando: sin "actividades" muestra el aviso, como antes.
-- ════════════════════════════════════════════════════════════════════════
begin;

do $$ begin
  if exists (select 1 from public.config where id = 1 and modo = 'PRODUCCION' and abierto) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
end $$;

create or replace function privado.version() returns text language sql immutable as $$ select '5.5-s6.4-r'::text $$;

create or replace function privado.duplicado(p_codigo text) returns jsonb language sql immutable as $$
  select privado.fallo('duplicado', 'Este documento ya está inscrito. Si necesitas ayuda, escríbenos.')
$$;

revoke all on all functions in schema privado from public, anon, authenticated;

commit;
