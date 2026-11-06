-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones · 05 · SPRINT 3 · PREPARACIÓN PARA SUPABASE     contrato v5.5
--  Va después de 04_sprint2_datos.sql. Se puede volver a correr. Es la primera migración que
--  se instala en un proyecto real: desde aquí, cada corrección va en una migración NUEVA.
--
--  · admin_limpiar (tester) solo borra del padrón documentos de prueba (prefijo ZQX): nunca a una
--    persona real, aunque el proyecto de prueba tenga el padrón real (reporte del Sprint 2.1).
--  · panel_padron_importar: acepta "lote" (por ejemplo "2/5") para la bitácora y devuelve duracionMs,
--    el tiempo dentro de la base (para separarlo del tiempo de red y del cliente).
--  · Índice de inscripciones por documento (Participantes 8 veces más rápido).
--  · "ocupado" incluye su motivo (SQLSTATE).
-- ════════════════════════════════════════════════════════════════════════
begin;

do $$ begin
  if exists (select 1 from public.config where id = 1 and modo = 'PRODUCCION' and abierto) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
end $$;

create or replace function privado.version() returns text language sql immutable as $$ select '5.5-s3'::text $$;

-- Documentos que solo puede crear el tester: tres letras que ningún documento real usa, y siete dígitos.
create or replace function privado.es_doc_de_prueba(d text) returns boolean language sql immutable as $$
  select coalesce(d, '') ~ '^ZQX[0-9]{7}$'
$$;

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
  if (b -> 'intentos') = 'true'::jsonb then delete from public.intentos; end if;
  perform privado.recalcular_inscritos();
  return jsonb_build_object('ok', true, 'tipo', 'admin', 'eliminados', n, 'padronEliminados', np,
    'padronIgnorados', cardinality(padr) - np);
end $$;

create or replace function privado.panel_padron_importar(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  r jsonb;
  t0 timestamptz := clock_timestamp();
  v_lote text := substring(coalesce(privado.jtext(b -> 'lote'), '') from '^\d{1,3}/\d{1,3}$');
begin
  if jsonb_typeof(b -> 'filas') <> 'array' or jsonb_array_length(b -> 'filas') not between 1 and 10000 then
    return privado.fallo('valor_invalido', 'Envía entre 1 y 10 000 filas.');
  end if;
  with entrada as (
    select t.ord::int fila, t.x -> 'documento' doc_j, t.x -> 'etapa' et_j from jsonb_array_elements(b -> 'filas') with ordinality t(x, ord)),
  norm as (
    select fila, doc_j, et_j, privado.normalizar_doc(doc_j) doc,
           (substring(btrim(privado.jtext(et_j)) from '([123])$'))::int et from entrada),
  validas as (select * from norm where et is not null and privado.es_documento(doc)),
  primeras as (select distinct on (doc) doc, et, fila from validas order by doc, fila),
  vigente as (                                   -- etapa que manda para cada documento del archivo
    select p.doc, coalesce(x.etapa, p.et)::int etapa, (x.documento is null) es_nuevo, p.fila primera
    from primeras p left join public.padron x on x.documento = p.doc),
  nuevas as (
    insert into public.padron (documento, etapa, origen, creado_por)
    select v.doc, v.etapa, 'PANEL', (s ->> 'uid')::uuid from vigente v where v.es_nuevo
    on conflict (documento) do nothing
    returning documento),
  clasif as (
    select q.fila, q.doc, q.et, v.etapa,
           case when v.es_nuevo and q.fila = v.primera then 'agregado' when q.et = v.etapa then 'existente' else 'conflicto' end clase
    from validas q join vigente v on v.doc = q.doc)
  select jsonb_build_object(
    'agregados', (select count(*) from nuevas),
    'existentes', (select count(*) from clasif where clase = 'existente'),
    'conflictos', coalesce((select jsonb_agg(jsonb_build_object('documento', doc, 'etapaActual', etapa, 'etapaPedida', et) order by fila)
                            from (select * from clasif where clase = 'conflicto' order by fila limit 200) c), '[]'::jsonb),
    'totalConflictos', (select count(*) from clasif where clase = 'conflicto'),
    'invalidos', coalesce((select jsonb_agg(jsonb_build_object('fila', fila, 'documento', left(privado.jtext(doc_j), 30), 'etapa', left(privado.jtext(et_j), 20)) order by fila)
                           from (select * from norm where et is null or not privado.es_documento(doc) order by fila limit 200) i), '[]'::jsonb),
    'totalInvalidos', (select count(*) from norm where et is null or not privado.es_documento(doc)))
  into r;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Importar padrón',
    coalesce('lote ' || v_lote || ' · ', '') || (r ->> 'agregados') || ' agregados · ' || (r ->> 'existentes') || ' ya existían · ' || (r ->> 'totalConflictos') || ' conflictos · ' || (r ->> 'totalInvalidos') || ' inválidos');
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'duracionMs', round(extract(epoch from clock_timestamp() - t0) * 1000)::int) || r;
end $$;

-- Participantes, buscar y admin_muestra buscan inscripciones por documento (no solo las confirmadas):
-- con 720 inscripciones, Participantes pasa de 207 ms a 27 ms; sin índice, crece con cada inscripción.
create index if not exists inscripciones_documento on public.inscripciones (documento);

-- La puerta, igual que en 04 salvo que "ocupado" dice su motivo (para medir en Supabase, tarea 3.7).
create or replace function public.api(p jsonb) returns jsonb
language plpgsql volatile security definer set search_path = public, privado, extensions, pg_temp as $$
declare
  accion text;
  s jsonb;
  chk jsonb;
  n int;
  r jsonb;
  v_actor text;
  v_sol text;
  v_huella text;
  prev privado.solicitudes;
  v_estado text;
  v_msg text;
  v_inc bigint;
begin
  if p is null or jsonb_typeof(p) <> 'object' then return privado.fallo('peticion_invalida', 'Petición inválida.'); end if;
  accion := coalesce(p ->> 'action', '');
  perform privado.aplicar_cierre_programado();

  if accion = '' then return jsonb_build_object('ok', true, 'servicio', 'CIIC 2026 · API de inscripciones', 'version', privado.version()); end if;
  if accion = 'estado' then                                   -- D3: una sola llamada en la pantalla 2
    return privado.estado_publico() || case when (p -> 'conActividades') = 'true'::jsonb then jsonb_build_object('actividades', privado.actividades_publicas()) else '{}'::jsonb end;
  end if;
  if accion = 'actividades' then return jsonb_build_object('ok', true, 'tipo', 'actividades', 'actividades', privado.actividades_publicas()); end if;
  if accion = 'verificar' then
    chk := privado.verificar(p -> 'dni', false, privado.dispositivo(p -> 'dispositivo'));
    if (chk ->> 'ok')::boolean then chk := chk || jsonb_build_object('actividades', privado.actividades_publicas()); end if;
    return chk;
  end if;

  if accion = 'registrar' or accion like 'panel\_%' then
    if accion = 'registrar' then
      v_actor := 'doc:' || privado.normalizar_doc(p -> 'dni');
    else
      s := privado.sesion(p);
      if s ? 'tipo' then return s; end if;
      n := privado.nivel(accion, p);
      if privado.rango(s ->> 'rol') < n then return privado.sin_permiso(n); end if;
      v_actor := coalesce('uid:' || (s ->> 'uid'), 'tester:' || (s ->> 'rol'));
    end if;

    -- R-32: idempotencia con ámbito. La misma solicitud de la misma persona y acción devuelve la misma respuesta.
    if privado.es_escritura(accion) then
      v_sol := lower(coalesce(p ->> 'solicitud', ''));
      if not privado.es_uuid(v_sol) then return privado.fallo('valor_invalido', 'Falta la solicitud (UUID) de esta operación.'); end if;
      v_huella := encode(extensions.digest(convert_to((p - 'solicitud' - 'dispositivo' - 'key' - 'comoRol')::text, 'UTF8'), 'sha256'), 'hex');
      perform pg_advisory_xact_lock(hashtextextended(v_actor || '|' || accion || '|' || v_sol, 0));
      select x.* into prev from privado.solicitudes x where x.actor = v_actor and x.accion = (p ->> 'action') and x.id = v_sol;
      if found then
        if prev.huella = v_huella then return prev.respuesta || '{"repetida":true}'::jsonb; end if;
        return privado.fallo('solicitud_repetida', 'Esta solicitud ya se usó con otros datos. Vuelve a intentarlo.');
      end if;
    end if;

    r := case accion
      when 'registrar'                  then privado.registrar(p, privado.dispositivo(p -> 'dispositivo'))
      when 'panel_resumen'              then privado.panel_resumen(s) || jsonb_build_object('integridad', privado.integridad(), 'ultimoRespaldo', null)
      when 'panel_config'               then privado.panel_config(p, s)
      when 'panel_actividad'            then privado.panel_actividad(p, s)
      when 'panel_buscar'               then privado.panel_buscar(p)
      when 'panel_anular'               then privado.panel_anular(p, s)
      when 'panel_inscribir'            then privado.panel_inscribir(p, s)
      when 'panel_cambiar'              then privado.panel_cambiar(p, s)
      when 'panel_participantes'        then privado.panel_participantes(p)
      when 'panel_padron_agregar'       then privado.panel_padron_agregar(p, s)
      when 'panel_padron_quitar'        then privado.panel_padron_quitar(p, s)
      when 'panel_padron_importar'      then privado.panel_padron_importar(p, s)
      when 'panel_crear'                then privado.panel_crear(p, s)
      when 'panel_editar'               then privado.panel_editar(p, s)
      when 'panel_quitar'               then privado.panel_quitar(p, s)
      when 'panel_actividades_importar' then privado.panel_actividades_importar(p, s)
      when 'panel_horarios'             then privado.panel_horarios(p, s)
      when 'panel_cruce'                then privado.panel_cruce(p, s)
      when 'panel_verificar_celular'    then privado.panel_verificar_celular(p)
      when 'panel_lista'                then privado.panel_lista(p)
      when 'panel_grupo_marcar'         then privado.panel_grupo_marcar(p, s)
      when 'panel_exportar'             then privado.panel_exportar(p, s)
      when 'panel_registros'            then privado.panel_registros(p, s)
      when 'panel_sincronizar'          then privado.panel_sincronizar(s)
      when 'panel_incidencias'          then privado.panel_incidencias()
      when 'panel_equipo'               then privado.panel_equipo()
      when 'panel_equipo_rol'           then privado.panel_equipo_rol(p, s)
      when 'panel_equipo_activo'        then privado.panel_equipo_activo(p, s)
      when 'panel_vaciar_prueba'        then privado.panel_vaciar_prueba(p, s)
      else privado.fallo('accion_invalida', 'Acción no reconocida.') end;

    if v_sol is not null and (r ->> 'ok')::boolean then
      insert into privado.solicitudes (actor, accion, id, huella, respuesta) values (v_actor, accion, v_sol, v_huella, r);
      if random() < 0.02 then delete from privado.solicitudes where creado_en < now() - interval '24 hours'; end if;
    end if;
    return r;
  end if;

  if accion in ('admin_ping', 'admin_muestra', 'admin_limpiar', 'admin_cabeceras', 'admin_error') then
    chk := privado.con_admin(p, accion <> 'admin_ping');
    if chk is not null then return chk; end if;
    if accion = 'admin_error' then perform 1 / 0; end if;
    return case accion
      when 'admin_ping'      then jsonb_build_object('ok', true, 'tipo', 'admin', 'version', privado.version(), 'config', privado.config_json())
      when 'admin_muestra'   then privado.admin_muestra(p)
      when 'admin_cabeceras' then privado.admin_cabeceras()
      else privado.admin_limpiar(p) end;
  end if;

  return privado.fallo('accion_invalida', 'Acción no reconocida.');
exception
  when lock_not_available or query_canceled or deadlock_detected or serialization_failure then
    -- El motivo (SQLSTATE) dice si fue tiempo agotado (57014), un bloqueo (55P03), un interbloqueo (40P01) o serialización (40001).
    get stacked diagnostics v_estado = returned_sqlstate;
    return privado.fallo('ocupado', 'Sistema ocupado, reintenta.', jsonb_build_object('motivo', v_estado));
  when others then
    get stacked diagnostics v_estado = returned_sqlstate, v_msg = message_text;
    insert into privado.incidencias (accion, sqlstate, mensaje) values (left(accion, 60), v_estado, left(v_msg, 500)) returning id into v_inc;
    return privado.fallo('error_servidor', 'Ocurrió un error en el sistema. Intenta de nuevo en unos segundos.',
                         jsonb_build_object('incidencia', 'INC-' || lpad(v_inc::text, 4, '0')));
end $$;

revoke all on all functions in schema privado from public, anon, authenticated;
revoke all on function public.api(jsonb) from public;
grant execute on function public.api(jsonb) to anon, authenticated;

commit;
