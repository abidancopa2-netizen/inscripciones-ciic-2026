-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones · 10 · SPRINT 5.1 · REDES Y DATOS DE CONEXIÓN     contrato v5.5
--  Va después de 09. Se puede volver a correr.
--
--  R-25 · Los intentos fallidos (IP de la red e identificador del navegador) se borran en cuanto termina su ventana
--         (10 min). Lo hace la consulta "estado", que es corta y la repiten las páginas abiertas cada 20 s y "Mantener
--         Supabase activo" cada hora: una sola a la vez (llave), con SKIP LOCKED (nunca espera ni hace esperar en el
--         camino de verificar o registrar) y en su propio bloque (si falla, lo intenta la siguiente). Antes se borraban
--         recién al día siguiente y solo si había otro fallo.
--  R-46 · Redes con intentos fallidos: panel_redes (nivel 2) lista las redes de la ventana actual con 50 fallos o
--         más, o con el 80 % del límite si el límite es bajo; la IP va enmascarada (190.234.•.•) y cada red se
--         identifica con un id opaco (HMAC con una sal de la base): la IP completa nunca sale de la base.
--         panel_liberar_red (nivel 3) vuelve a 0 el contador de una red y queda en la bitácora.
--         panel_resumen trae el mismo resumen para admin y propietario (la franja avisa al 80 % y al frenar).
--  Límite por red: 300 por omisión; si la fila seguía en el valor de fábrica (30), pasa a 300.
--  Correo: el mensaje de error dice "correo electrónico" (no se restringe el dominio, §24).
--  Ningún DELETE ni UPDATE sin WHERE (safeupdate de Supabase; lo vigila el tester, bloque R).
-- ════════════════════════════════════════════════════════════════════════
begin;

do $$ begin
  if exists (select 1 from public.config where id = 1 and modo = 'PRODUCCION' and abierto) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
end $$;

create or replace function privado.version() returns text language sql immutable as $$ select '5.5-s5.1'::text $$;

-- ── R-25 · Limpieza de intentos al terminar la ventana ──
-- sumar_fallo ya no borra (bajo una ráfaga, muchos fallos borrando las mismas filas se esperarían entre sí).
create or replace function privado.sumar_fallo(p_disp text) returns int language plpgsql volatile as $$
declare v_f int; v_lim int;
begin
  select limite_dispositivo into v_lim from public.config where id = 1;
  insert into public.intentos (clave, ventana, fallos) values ('red:' || privado.red(), privado.ventana(), 1)
  on conflict (clave, ventana) do update set fallos = public.intentos.fallos + 1;
  if p_disp is null then return null; end if;
  insert into public.intentos (clave, ventana, fallos) values ('disp:' || p_disp, privado.ventana(), 1)
  on conflict (clave, ventana) do update set fallos = public.intentos.fallos + 1
  returning fallos into v_f;
  return greatest(0, v_lim - v_f);
end $$;

-- Borra lo de ventanas terminadas. La llama "estado" solo si hay algo que borrar (un vistazo al índice por ventana).
-- Una a la vez; SKIP LOCKED: nunca espera por una fila que otra llamada esté usando (la borra la siguiente); y si algo
-- falla, la consulta igual responde. No va en contar_llamada: ahí cualquier llamada larga (registrar, respaldo) podía
-- quedarse con las filas borradas y hacer esperar a un verificar (revisión del Sprint 5.1).
create or replace function privado.limpiar_intentos() returns void language plpgsql volatile as $$
begin
  if not pg_try_advisory_xact_lock(2026, 1) then return; end if;
  delete from public.intentos where (clave, ventana) in
    (select x.clave, x.ventana from public.intentos x where x.ventana < privado.ventana() for update skip locked);
exception
  when query_canceled then raise;
  when others then null;
end $$;

-- Lo que ya estaba guardado de ventanas anteriores se borra ahora.
delete from public.intentos where ventana < privado.ventana();

-- ── R-46 · Redes con intentos fallidos ──
create table if not exists privado.sal (
  id    int primary key check (id = 1),
  valor bytea not null
);
alter table privado.sal enable row level security;
revoke all on privado.sal from public, anon, authenticated;
insert into privado.sal (id, valor) values (1, extensions.gen_random_bytes(32)) on conflict (id) do nothing;

-- Id opaco de una red: con él se libera, sin que la IP salga de la base (tampoco se puede recalcular sin la sal).
create or replace function privado.red_id(p_clave text) returns text language sql stable as $$
  select left(encode(extensions.hmac(convert_to(p_clave, 'UTF8'), (select valor from privado.sal where id = 1), 'sha256'), 'hex'), 16)
$$;

-- 190.234.17.5 → 190.234.•.• · 2800:200:e840:… → 2800:200:• · otra cosa → desconocida
create or replace function privado.red_oculta(p_ip text) returns text language sql immutable as $$
  select case
    when p_ip ~ '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$' then split_part(p_ip, '.', 1) || '.' || split_part(p_ip, '.', 2) || '.•.•'
    when p_ip ~ '^[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{0,4}:' then lower(split_part(p_ip, ':', 1) || ':' || split_part(p_ip, ':', 2)) || ':•'
    else 'desconocida' end
$$;

-- Redes de la ventana actual. Se listan desde 50 fallos, o desde el 80 % del límite si el límite es bajo (para que
-- con un límite de 5, como en el ensayo, la red aparezca antes de frenarse). cerca = 80 % o más; frenada = el límite.
create or replace function privado.redes_json() returns jsonb language sql stable as $$
  with c as (select limite_red l, ventana_min m, least(50, ceil(limite_red * 0.8)::int) desde from public.config where id = 1),
       w as (select privado.ventana() w),
       r as (select t.clave, t.fallos from public.intentos t, w where t.ventana = w.w and t.clave like 'red:%')
  select jsonb_build_object(
    'limite', c.l, 'ventanaMin', c.m, 'desde', c.desde,
    'reiniciaEnSeg', greatest(0, ceil(extract(epoch from (w.w + make_interval(mins => c.m)) - clock_timestamp())))::int,
    'cerca', (select count(*) from r where r.fallos >= 0.8 * c.l and r.fallos < c.l),
    'frenadas', (select count(*) from r where r.fallos >= c.l),
    'redes', coalesce((select jsonb_agg(jsonb_build_object('id', privado.red_id(x.clave), 'red', privado.red_oculta(substr(x.clave, 5)),
                                                           'fallos', x.fallos, 'pct', floor(100.0 * x.fallos / c.l)::int,
                                                           'estado', case when x.fallos >= c.l then 'frenada' when x.fallos >= 0.8 * c.l then 'cerca' else 'normal' end)
                                        order by x.fallos desc)
                       from (select * from r where r.fallos >= c.desde order by r.fallos desc limit 50) x), '[]'::jsonb))
  from c, w
$$;

create or replace function privado.panel_liberar_red(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_id text := lower(btrim(coalesce(privado.jtext(b -> 'id'), '')));
  v_clave text;
  v_fallos int;
  v_red text;
begin
  select t.clave, t.fallos into v_clave, v_fallos from public.intentos t
  where t.clave like 'red:%' and t.ventana = privado.ventana() and privado.red_id(t.clave) = v_id;
  if not found then
    return privado.fallo('no_encontrado', 'Esa red ya no tiene intentos fallidos en esta ventana: no hay nada que liberar.');
  end if;
  v_red := privado.red_oculta(substr(v_clave, 5));
  delete from public.intentos where clave = v_clave;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Liberar red', v_red || ' · ' || v_fallos || ' fallos en la ventana');
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'liberada', v_red, 'fallos', v_fallos) || privado.redes_json();
end $$;

-- Niveles: igual que en 03, más panel_redes (nivel 2). panel_liberar_red queda en 3, como toda acción nueva.
create or replace function privado.nivel(accion text, p jsonb) returns int language sql immutable as $$
  select case
    when accion = 'panel_config' then
      case when (p -> 'abierto') = 'true'::jsonb or privado.tiene(p, 'etapas') or privado.tiene(p, 'etapasVisita') or privado.tiene(p, 'dosTalleres')
             or privado.tiene(p, 'refresco') or privado.tiene(p, 'umbral') or privado.tiene(p, 'limiteDispositivo') or privado.tiene(p, 'limiteRed')
           then 3 else 2 end
    when accion in ('panel_resumen', 'panel_participantes', 'panel_buscar', 'panel_verificar_celular', 'panel_lista', 'panel_grupo_marcar', 'panel_exportar') then 1
    when accion in ('panel_actividad', 'panel_crear', 'panel_editar', 'panel_quitar', 'panel_cruce', 'panel_inscribir', 'panel_cambiar', 'panel_anular',
                    'panel_padron_agregar', 'panel_padron_quitar', 'panel_incidencias', 'panel_sincronizar', 'panel_registros', 'panel_redes') then 2
    else 3 end      -- panel_horarios, panel_equipo*, panel_respaldo, panel_padron_importar, panel_actividades_importar,
                    -- panel_vaciar_prueba, panel_preparar_produccion, panel_liberar_red y cualquier acción nueva
$$;

-- Escrituras (R-32): igual que en 04, más panel_liberar_red.
create or replace function privado.es_escritura(accion text) returns boolean language sql immutable as $$
  select accion in ('registrar', 'panel_config', 'panel_actividad', 'panel_anular', 'panel_inscribir', 'panel_cambiar', 'panel_padron_agregar',
                    'panel_padron_quitar', 'panel_crear', 'panel_editar', 'panel_quitar', 'panel_horarios', 'panel_cruce', 'panel_equipo_rol',
                    'panel_equipo_activo', 'panel_grupo_marcar', 'panel_sincronizar', 'panel_padron_importar', 'panel_actividades_importar',
                    'panel_vaciar_prueba', 'panel_preparar_produccion', 'panel_liberar_red')
$$;

-- ── Límite por red: 300 (decisión del propietario para la apertura; Wi-Fi de la UCSM con una IP por pabellón) ──
-- (Sin entrada en la bitácora: una base recién instalada debe quedar con la bitácora vacía, y restaurar.py lo supone.)
alter table public.config alter column limite_red set default 300;
update public.config set limite_red = 300 where id = 1 and limite_red = 30;

-- ── Correo: cualquier dominio (§24); el mensaje ya no dice "institucional" ──
create or replace function privado.datos_persona(b jsonb) returns jsonb language plpgsql stable as $$
declare
  v_nombres text := privado.texto_limpio(b -> 'nombres', 60);
  v_apellidos text := privado.texto_limpio(b -> 'apellidos', 60);
  v_correo text := lower(privado.texto_limpio(b -> 'correo', 100));
  v_tel jsonb := privado.normalizar_celular(b -> 'pais', b -> 'celular');
begin
  if length(v_nombres) < 2 then return privado.fallo('datos_invalidos', 'Escribe tus nombres.', '{"campo":"nombres"}'); end if;
  if length(v_apellidos) < 2 then return privado.fallo('datos_invalidos', 'Escribe tus apellidos.', '{"campo":"apellidos"}'); end if;
  if v_correo !~ '^[^\s@]+@[^\s@]+\.[^\s@]{2,}$' then return privado.fallo('datos_invalidos', 'Escribe tu correo electrónico.', '{"campo":"correo"}'); end if;
  if v_tel is null then
    return privado.fallo('celular_invalido', case when upper(coalesce(nullif(privado.jtext(b -> 'pais'), ''), 'PE')) = 'PE'
      then 'Revisa tu celular: en Perú son 9 dígitos y empiezan con 9.' else 'Revisa tu celular: escribe entre 6 y 14 dígitos, sin el código de país.' end,
      '{"campo":"celular"}');
  end if;
  if (b -> 'aceptaPrivacidad') is distinct from 'true'::jsonb or (b -> 'aceptaWhatsapp') is distinct from 'true'::jsonb then
    return privado.fallo('sin_consentimiento', 'Para inscribirte necesitamos que aceptes el aviso de privacidad y el contacto por WhatsApp.');
  end if;
  return jsonb_build_object('ok', true, 'nombres', v_nombres, 'apellidos', v_apellidos, 'correo', v_correo, 'tel', v_tel);
end $$;

-- La puerta: igual que en 09, más panel_redes y panel_liberar_red (R-46); el resumen trae las redes para admin y propietario.
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
    if exists (select 1 from public.intentos where ventana < privado.ventana()) then perform privado.limpiar_intentos(); end if;   -- R-25
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
                                                 || case when privado.rango(s ->> 'rol') >= 2 then jsonb_build_object('redes', privado.redes_json())
                                                         else '{}'::jsonb end
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
      when 'panel_redes'                then jsonb_build_object('ok', true, 'tipo', 'panel') || privado.redes_json()
      when 'panel_liberar_red'          then privado.panel_liberar_red(p, s)
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
