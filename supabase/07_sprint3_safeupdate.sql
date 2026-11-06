-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones · 07 · SPRINT 3.2 · COMPATIBLE CON SAFEUPDATE DE SUPABASE     contrato v5.5
--  Va después de 06. Se puede volver a correr.
--
--  Supabase carga la extensión safeupdate en las conexiones de la API (session_preload_libraries del rol
--  authenticator): todo DELETE o UPDATE sin WHERE falla con 21000 "DELETE requires a WHERE clause".
--  En local no estaba, así que el tester no lo veía (hallado en la Fase C del Sprint 3, contra PRUEBA):
--  "Vaciar datos de prueba" (R-44, §19.7) y la limpieza del tester fallaban por la API.
--  Las 9 sentencias afectadas pasan a "where true", que safeupdate acepta y no cambia lo que hacen.
--  Desde ahora: ninguna función lleva DELETE o UPDATE sin WHERE (lo vigila el tester, bloque R).
-- ════════════════════════════════════════════════════════════════════════
begin;

do $$ begin
  if exists (select 1 from public.config where id = 1 and modo = 'PRODUCCION' and abierto) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
end $$;

create or replace function privado.version() returns text language sql immutable as $$ select '5.5-s3.2'::text $$;

create or replace function privado.admin_limpiar(b jsonb) returns jsonb language plpgsql volatile as $$
declare
  docs text[];
  padr text[];
  n int;
  np int;
  v_prev text;
begin
  select coalesce(array_agg(privado.normalizar_doc(x)), '{}') into docs
  from jsonb_array_elements(case when jsonb_typeof(b -> 'docs') = 'array' then b -> 'docs' else '[]'::jsonb end) x;
  select coalesce(array_agg(privado.normalizar_doc(x)), '{}') into padr
  from jsonb_array_elements(case when jsonb_typeof(b -> 'padron') = 'array' then b -> 'padron' else '[]'::jsonb end) x;
  perform 1 from public.actividades order by id for update;
  v_prev := privado.permitir_masivo();
  delete from public.inscripciones where documento = any (docs);
  get diagnostics n = row_count;
  -- Del padrón, solo lo que creó el tester: origen PANEL y documento de prueba (ZQX…). Nunca una persona real.
  delete from public.padron where documento = any (padr) and origen = 'PANEL' and privado.es_doc_de_prueba(documento);
  get diagnostics np = row_count;
  perform privado.restaurar_masivo(v_prev);
  if (b -> 'intentos') = 'true'::jsonb then delete from public.intentos where true; end if;
  perform privado.recalcular_inscritos();
  return jsonb_build_object('ok', true, 'tipo', 'admin', 'eliminados', n, 'padronEliminados', np,
    'padronIgnorados', cardinality(padr) - np);
end $$;

create or replace function privado.panel_vaciar_prueba(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  c public.config;
  n jsonb;
  v_prev text;
begin
  select * into c from public.config where id = 1 for update;
  if c.modo <> 'PRUEBA' then return privado.fallo('modo_produccion', 'Solo se puede vaciar en modo PRUEBA.'); end if;
  if c.abierto then return privado.requiere_cierre(); end if;
  if coalesce(privado.jtext(b -> 'llave'), '') <> 'VACIAR' then return privado.fallo('valor_invalido', 'Para confirmar, escribe VACIAR.'); end if;
  n := jsonb_build_object('padron', (select count(*) from public.padron), 'actividades', (select count(*) from public.actividades),
                          'inscripciones', (select count(*) from public.inscripciones));
  v_prev := privado.permitir_masivo();
  delete from public.inscripciones where true;                -- con sus actividades (en cascada)
  delete from public.cruces_permitidos where true;
  delete from public.actividades where true;
  delete from public.padron where true;
  delete from public.bitacora where true;
  delete from public.intentos where true;
  delete from privado.solicitudes where true;
  delete from privado.incidencias where true;
  perform privado.restaurar_masivo(v_prev);
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Vaciar datos de prueba',
    (n ->> 'padron') || ' en el padrón, ' || (n ->> 'actividades') || ' actividades y ' || (n ->> 'inscripciones') || ' inscripciones eliminadas · configuración y equipo intactos',
    n, jsonb_build_object('padron', 0, 'actividades', 0, 'inscripciones', 0));
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'eliminados', n);
end $$;

revoke all on all functions in schema privado from public, anon, authenticated;

commit;
