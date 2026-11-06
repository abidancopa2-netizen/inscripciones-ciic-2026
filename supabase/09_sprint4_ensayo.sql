-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones · 09 · SPRINT 4.1 · ENSAYO POR LA API REAL     contrato v5.5
--  Va después de 08. Se puede volver a correr.
--
--  "Pasar a producción" (R-43) solo se ejecuta de verdad una vez, en la apertura. Supabase carga safeupdate en las
--  conexiones de la API y una conexión directa no lo reproduce (Sprint 3.2: así falló "Vaciar"). admin_ensayo
--  (solo el tester: ADMIN_KEY y modo PRUEBA) ejecuta panel_preparar_produccion o panel_vaciar_prueba POR LA API,
--  con todo lo que eso implica (rol, safeupdate, disparadores, R-40), mide cómo quedó la base, y lo deshace todo
--  dentro de la misma llamada. En PRODUCCIÓN no existe la clave del tester: ahí no hace nada.
-- ════════════════════════════════════════════════════════════════════════
begin;

do $$ begin
  if exists (select 1 from public.config where id = 1 and modo = 'PRODUCCION' and abierto) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
end $$;

create or replace function privado.version() returns text language sql immutable as $$ select '5.5-s4.1'::text $$;

create or replace function privado.admin_ensayo(b jsonb) returns jsonb language plpgsql volatile as $$
declare
  que text := coalesce(privado.jtext(b -> 'que'), '');
  s jsonb := '{"uid": null, "nombre": "Tester (ensayo)", "rol": "propietario", "tester": true}';
  r jsonb;
  durante jsonb;
  v_estado text;
  v_msg text;
  error jsonb;
begin
  if que not in ('panel_preparar_produccion', 'panel_vaciar_prueba') then
    return privado.fallo('valor_invalido', 'Ensayo de panel_preparar_produccion o panel_vaciar_prueba.');
  end if;
  begin
    update public.config set abierto = false, cierre_en = null where id = 1;          -- las dos exigen el sistema cerrado
    r := case que when 'panel_preparar_produccion' then privado.panel_preparar_produccion('{"llave": "PRODUCCION"}', s)
                  else privado.panel_vaciar_prueba('{"llave": "VACIAR"}', s) end;
    durante := jsonb_build_object(
      'modo', (select modo from public.config where id = 1),
      'clave', exists (select 1 from privado.claves where nombre = 'ADMIN_KEY'),
      'padron', (select count(*) from public.padron),
      'padronPrueba', (select count(*) from public.padron where privado.es_doc_de_prueba(documento)),
      'actividades', (select count(*) from public.actividades),
      'inscritos', (select coalesce(sum(inscritos), 0) from public.actividades),
      'inscripciones', (select count(*) from public.inscripciones),
      'inscripcionActividades', (select count(*) from public.inscripcion_actividades),
      'intentos', (select count(*) from public.intentos),
      'trafico', (select count(*) from privado.trafico),
      'incidencias', (select count(*) from privado.incidencias),
      'bitacora', (select count(*) from public.bitacora),
      'bitacoraPrimera', (select accion from public.bitacora order by id limit 1),
      'integridad', (privado.integridad() ->> 'ok')::boolean);
    raise exception using errcode = 'CE001', message = 'ensayo: se deshace';           -- deshace TODO lo de este bloque
  exception
    when sqlstate 'CE001' then null;
    when query_canceled then raise;
    when others then
      get stacked diagnostics v_estado = returned_sqlstate, v_msg = message_text;    -- p. ej. 21000 de safeupdate: es lo que se busca
      error := jsonb_build_object('sqlstate', v_estado, 'mensaje', left(v_msg, 300));
  end;
  return jsonb_build_object('ok', error is null, 'tipo', 'admin', 'que', que, 'respuesta', r, 'durante', durante, 'error', error,
    'despues', jsonb_build_object('modo', (select modo from public.config where id = 1), 'abierto', (select abierto from public.config where id = 1),
                                  'clave', exists (select 1 from privado.claves where nombre = 'ADMIN_KEY'),
                                  'padron', (select count(*) from public.padron), 'inscripciones', (select count(*) from public.inscripciones)));
end $$;

-- La puerta: igual que en 08, más la acción del tester admin_ensayo.
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
  perform privado.contar_llamada();                           -- R-34
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
      when 'panel_resumen'              then privado.panel_resumen(s) || jsonb_build_object('integridad', privado.integridad(),
                                                                                           'trafico', privado.trafico_json(),
                                                                                           'ultimoRespaldo', privado.ultimo_respaldo())
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
      when 'panel_respaldo'             then privado.panel_respaldo(s)
      when 'panel_preparar_produccion'  then privado.panel_preparar_produccion(p, s)
      else privado.fallo('accion_invalida', 'Acción no reconocida.') end;

    if v_sol is not null and (r ->> 'ok')::boolean then
      insert into privado.solicitudes (actor, accion, id, huella, respuesta) values (v_actor, accion, v_sol, v_huella, r);
      if random() < 0.02 then delete from privado.solicitudes where creado_en < now() - interval '24 hours'; end if;
    end if;
    return r;
  end if;

  if accion in ('admin_ping', 'admin_muestra', 'admin_limpiar', 'admin_cabeceras', 'admin_error', 'admin_ensayo') then
    chk := privado.con_admin(p, accion <> 'admin_ping');
    if chk is not null then return chk; end if;
    if accion = 'admin_error' then perform 1 / 0; end if;
    return case accion
      when 'admin_ping'      then jsonb_build_object('ok', true, 'tipo', 'admin', 'version', privado.version(), 'config', privado.config_json())
      when 'admin_muestra'   then privado.admin_muestra(p)
      when 'admin_cabeceras' then privado.admin_cabeceras()
      when 'admin_ensayo'    then privado.admin_ensayo(p)
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
