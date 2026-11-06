-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones · 08 · SPRINT 4 · CARGA Y OPERACIÓN     contrato v5.5
--  Va después de 07. Se puede volver a correr.
--
--  R-34 · Tráfico: secuencia privado.llamadas y una foto por ventana de 10 s (privado.trafico). La alerta se
--         enciende con 3 ventanas seguidas sobre config.umbral_ventana y se apaga con 3 seguidas por debajo.
--  R-41 · Respaldo: panel_respaldo (nivel 3) con todas las tablas de datos, filas y huella SHA-256 por tabla y
--         total, que supabase/restaurar.py vuelve a calcular. Queda en la bitácora.
--  R-43 · Pasar a producción: panel_preparar_produccion (nivel 3), con la llave PRODUCCION, cerrado y en PRUEBA.
--         Quita además del padrón los documentos del tester (ZQX…), que ninguna persona real tiene.
--  Además: "Vaciar datos de prueba" también vacía el tráfico; panel_config acepta "umbral" (nivel 3).
--  Ningún DELETE ni UPDATE sin WHERE (safeupdate de Supabase; lo vigila el tester, bloque R).
-- ════════════════════════════════════════════════════════════════════════
begin;

do $$ begin
  if exists (select 1 from public.config where id = 1 and modo = 'PRODUCCION' and abierto) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
end $$;

create or replace function privado.version() returns text language sql immutable as $$ select '5.5-s4'::text $$;

-- ── Configuración: umbral de saturación (R-34, D10) ──
alter table public.config add column if not exists umbral_ventana integer not null default 2000;
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'config_umbral_ventana' and conrelid = 'public.config'::regclass) then
    alter table public.config add constraint config_umbral_ventana check (umbral_ventana between 100 and 100000);
  end if;
end $$;

create or replace function privado.config_json() returns jsonb language sql stable as $$
  select jsonb_build_object('abierto', c.abierto, 'ronda', c.ronda, 'cierraEn', privado.cierra_en_seg(), 'etapas', to_jsonb(c.etapas),
    'etapasVisita', to_jsonb(c.etapas_visita), 'dosTalleres', c.dos_talleres, 'mismoDia', c.mismo_dia, 'margenMin', c.margen_min,
    'pasoCupo', c.paso_cupo, 'refresco', c.refresco, 'modo', c.modo,
    'limiteDispositivo', c.limite_dispositivo, 'limiteRed', c.limite_red, 'ventanaMin', c.ventana_min,
    'limiteMasivo', c.limite_masivo, 'avisoVersion', c.aviso_version, 'umbral', c.umbral_ventana)
  from public.config c where c.id = 1
$$;

create or replace function privado.panel_config(b jsonb, s jsonb) returns jsonb language plpgsql as $$
declare
  c public.config;
  quiero smallint[];
  n int;
  cambios text[] := '{}';
  uid uuid := (s ->> 'uid')::uuid;
  antes jsonb;
begin
  select * into c from public.config where id = 1 for update;     -- espera a las inscripciones en curso
  antes := privado.config_json() - 'cierraEn';
  if (b -> 'abierto') = 'false'::jsonb and c.abierto then
    if (b -> 'confirmar') is distinct from 'true'::jsonb then
      return privado.fallo('advertencia', 'Nadie nuevo podrá pasar de la pantalla 1. Quien esté eligiendo y no haya confirmado vuelve al inicio sin inscribirse. Se habilitan los cambios que quitan opciones.',
                           '{"accion":"cerrar"}');
    end if;
    update public.config set abierto = false, ronda = ronda + 1, cierre_en = null where id = 1;
    perform privado.bitacora(uid, privado.quien(s), 'Cierre y depuración', 'ronda ' || c.ronda || ' → ' || (c.ronda + 1),
                             jsonb_build_object('abierto', true, 'ronda', c.ronda), jsonb_build_object('abierto', false, 'ronda', c.ronda + 1));
    return jsonb_build_object('ok', true, 'tipo', 'panel', 'config', privado.config_json());
  end if;
  if (b -> 'abierto') = 'true'::jsonb and not c.abierto then
    update public.config set abierto = true where id = 1;
    perform privado.bitacora(uid, privado.quien(s), 'Apertura', 'ronda ' || c.ronda, jsonb_build_object('abierto', false), jsonb_build_object('abierto', true));
    return jsonb_build_object('ok', true, 'tipo', 'panel', 'config', privado.config_json());
  end if;
  if privado.tiene(b, 'avisarCierreMin') or (privado.tiene(b, 'avisarCierreSeg') and (s ->> 'tester')::boolean) then
    if not c.abierto then return privado.fallo('valor_invalido', 'Las inscripciones ya están cerradas.'); end if;
    n := case when privado.tiene(b, 'avisarCierreSeg') then privado.entero(b -> 'avisarCierreSeg') else privado.entero(b -> 'avisarCierreMin') * 60 end;
    if n is null or n < 1 or n > 600 then return privado.fallo('valor_invalido', 'El aviso debe ser de 1 a 10 minutos.'); end if;
    update public.config set cierre_en = now() + make_interval(secs => n) where id = 1;
    perform privado.bitacora(uid, privado.quien(s), 'Aviso de cierre', 'cierre en ' || privado.min_txt(n));
    return jsonb_build_object('ok', true, 'tipo', 'panel', 'config', privado.config_json());
  end if;
  if (b -> 'cancelarAviso') = 'true'::jsonb then
    update public.config set cierre_en = null where id = 1;
    perform privado.bitacora(uid, privado.quien(s), 'Aviso de cierre', 'cancelado');
    return jsonb_build_object('ok', true, 'tipo', 'panel', 'config', privado.config_json());
  end if;

  if jsonb_typeof(b -> 'etapas') = 'array' then
    select coalesce(array_agg(distinct e::smallint order by e::smallint), '{}') into quiero
    from jsonb_array_elements_text(b -> 'etapas') t(e) where e ~ '^\s*[123]\s*$';
    if c.abierto and not (c.etapas <@ quiero) then return privado.requiere_cierre(); end if;
    update public.config set etapas = quiero where id = 1;
    cambios := cambios || ('etapas de inscripción: ' || coalesce(nullif(array_to_string(quiero, ', '), ''), 'ninguna'));
  end if;
  if jsonb_typeof(b -> 'etapasVisita') = 'array' then
    select coalesce(array_agg(distinct e::smallint order by e::smallint), '{}') into quiero
    from jsonb_array_elements_text(b -> 'etapasVisita') t(e) where e ~ '^\s*[123]\s*$';
    if c.abierto and not (c.etapas_visita <@ quiero) then return privado.requiere_cierre(); end if;
    update public.config set etapas_visita = quiero where id = 1;
    cambios := cambios || ('etapas con visitas: ' || coalesce(nullif(array_to_string(quiero, ', '), ''), 'ninguna'));
  end if;
  if jsonb_typeof(b -> 'dosTalleres') = 'boolean' then
    if c.abierto and c.dos_talleres and not (b ->> 'dosTalleres')::boolean then return privado.requiere_cierre(); end if;
    update public.config set dos_talleres = (b ->> 'dosTalleres')::boolean where id = 1;
    cambios := cambios || ('permitir 2 talleres: ' || case when (b ->> 'dosTalleres')::boolean then 'SI' else 'NO' end);
  end if;
  if privado.tiene(b, 'pasoCupo') then
    n := privado.entero(b -> 'pasoCupo');
    if n is null or n < 1 or n > 100 then return privado.fallo('valor_invalido', 'El paso de cupo debe estar entre 1 y 100.'); end if;
    update public.config set paso_cupo = n where id = 1; cambios := cambios || ('paso de cupo: ' || n);
  end if;
  if privado.tiene(b, 'refresco') then
    n := privado.entero(b -> 'refresco');
    if n is null or n < 10 or n > 120 then return privado.fallo('valor_invalido', 'El refresco debe estar entre 10 y 120 segundos.'); end if;
    update public.config set refresco = n where id = 1; cambios := cambios || ('refresco: ' || n || ' s');
  end if;
  if privado.tiene(b, 'umbral') then                           -- R-34 · nivel 3 (privado.nivel ya lo declaraba)
    n := privado.entero(b -> 'umbral');
    if n is null or n < 100 or n > 100000 then return privado.fallo('valor_invalido', 'El umbral debe estar entre 100 y 100000 llamadas por ventana.'); end if;
    update public.config set umbral_ventana = n where id = 1; cambios := cambios || ('umbral de saturación: ' || n || ' por ventana de 10 s');
  end if;
  if privado.tiene(b, 'limiteDispositivo') then
    n := privado.entero(b -> 'limiteDispositivo');
    if n is null or n < 1 or n > 100 then return privado.fallo('valor_invalido', 'El límite por dispositivo debe estar entre 1 y 100.'); end if;
    update public.config set limite_dispositivo = n where id = 1; cambios := cambios || ('límite por dispositivo: ' || n);
  end if;
  if privado.tiene(b, 'limiteRed') then
    n := privado.entero(b -> 'limiteRed');
    if n is null or n < 1 or n > 100000 then return privado.fallo('valor_invalido', 'El límite por red debe estar entre 1 y 100000.'); end if;
    update public.config set limite_red = n where id = 1; cambios := cambios || ('límite por red: ' || n);
  end if;
  if array_length(cambios, 1) > 0 then
    perform privado.bitacora(uid, privado.quien(s), 'Configuración', array_to_string(cambios, ' · '), antes, privado.config_json() - 'cierraEn');
  end if;
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'config', privado.config_json());
end $$;

-- ── Tráfico (R-34, §15.14) ──
-- Cada llamada suma 1 a la secuencia (no escribe filas). La primera llamada de cada ventana de 10 s guarda una foto del
-- contador, cierra la ventana anterior (llamadas = foto nueva − foto anterior) y evalúa la alerta. Solo esa llamada
-- escribe, y nunca espera: una sola llave para toda la base (pg_try_advisory_xact_lock); si otra llamada está tomando
-- una foto (de esta ventana o de la anterior, aún sin confirmar), sigue de largo y la toma una llamada siguiente.
create sequence if not exists privado.llamadas;
create table if not exists privado.trafico (
  ventana   bigint primary key,            -- floor(epoch / 10)
  total     bigint not null,               -- valor de privado.llamadas en la primera llamada de la ventana
  llamadas  bigint,                        -- llamadas de la ventana (se llena al abrir la siguiente)
  alerta    boolean not null default false,
  creado_en timestamptz not null default now()
);
alter table privado.trafico enable row level security;
revoke all on privado.trafico from public, anon, authenticated;
revoke all on sequence privado.llamadas from public, anon, authenticated;

create or replace function privado.contar_llamada() returns void language plpgsql volatile as $$
declare
  n bigint := nextval('privado.llamadas');
  w bigint := floor(extract(epoch from clock_timestamp()) / 10)::bigint;
  u int;
  prev privado.trafico;
  v bigint[];
  al boolean;
begin
  if exists (select 1 from privado.trafico where ventana = w) then return; end if;         -- lo habitual: ya hay foto
  if not pg_try_advisory_xact_lock(2026, 0) then return; end if;                           -- otra llamada está tomando una foto
  begin
    select * into prev from privado.trafico where ventana < w order by ventana desc limit 1;
    if found and prev.llamadas is null then
      update privado.trafico set llamadas = greatest(n - prev.total, 0) where ventana = prev.ventana;
    end if;
    select umbral_ventana into u from public.config where id = 1;
    select array_agg(coalesce(t.llamadas, 0) order by g.x desc) into v       -- las 3 ventanas completas anteriores (sin foto = 0 llamadas)
    from generate_series(w - 3, w - 1) g(x) left join privado.trafico t on t.ventana = g.x;
    al := case when v[1] > u and v[2] > u and v[3] > u then true
               when v[1] <= u and v[2] <= u and v[3] <= u then false
               else coalesce(prev.alerta, false) end;
    insert into privado.trafico (ventana, total, alerta) values (w, n, al) on conflict (ventana) do nothing;
    if al and not coalesce(prev.alerta, false) then
      perform privado.bitacora(null, 'Sistema', 'Alerta de saturación', '3 ventanas seguidas sobre ' || u || ' llamadas por ventana de 10 s');
    end if;
    delete from privado.trafico where ventana < w - 17280;                    -- R-34: solo los últimos 2 días
  exception
    when query_canceled then raise;          -- el tiempo agotado se respeta
    when others then null;                    -- contar nunca impide atender la llamada
  end;
end $$;

create or replace function privado.trafico_json() returns jsonb language sql stable as $$
  with w as (select floor(extract(epoch from clock_timestamp()) / 10)::bigint w),
       ult as (select t.ventana, t.alerta from privado.trafico t order by t.ventana desc limit 1)
  select jsonb_build_object(
    'ventana10s', coalesce((select greatest((select last_value from privado.llamadas) - t.total + 1, 0) from privado.trafico t, w where t.ventana = w.w), 0),
    'pico10s', coalesce((select max(t.llamadas) from privado.trafico t), 0),
    'alerta', coalesce((select u.alerta and u.ventana >= w.w - 3 from ult u, w), false),
    'umbral', (select c.umbral_ventana from public.config c where c.id = 1))
$$;

-- ── Respaldo (R-41, §19.3) ──
-- Huella: SHA-256 del texto que PostgreSQL da a cada jsonb (claves ordenadas por largo y luego por bytes, ", " y ": ").
-- Es nativo (rápido aun con muchos MB) y supabase/restaurar.py lo reproduce desde el archivo, aunque el navegador
-- lo haya vuelto a escribir con sus propios espacios. En estas tablas todos los números son enteros.
drop function if exists privado.json_canonico(jsonb);

create or replace function privado.respaldo_tablas() returns jsonb language sql stable as $$
  select jsonb_build_object(
    'config',                  (select coalesce(jsonb_agg(to_jsonb(x)), '[]'::jsonb) from public.config x),
    'tipos_actividad',         (select coalesce(jsonb_agg(to_jsonb(x) order by x.codigo collate "C"), '[]'::jsonb) from public.tipos_actividad x),
    'padron',                  (select coalesce(jsonb_agg(to_jsonb(x) order by x.documento collate "C"), '[]'::jsonb) from public.padron x),
    'actividades',             (select coalesce(jsonb_agg(to_jsonb(x) order by x.id collate "C"), '[]'::jsonb) from public.actividades x),
    'cruces_permitidos',       (select coalesce(jsonb_agg(to_jsonb(x) order by x.a collate "C", x.b collate "C"), '[]'::jsonb) from public.cruces_permitidos x),
    'inscripciones',           (select coalesce(jsonb_agg(to_jsonb(x) order by x.codigo collate "C"), '[]'::jsonb) from public.inscripciones x),
    'inscripcion_actividades', (select coalesce(jsonb_agg(to_jsonb(x) order by x.codigo collate "C", x.actividad_id collate "C"), '[]'::jsonb) from public.inscripcion_actividades x),
    'organizadores',           (select coalesce(jsonb_agg(to_jsonb(x) order by x.user_id), '[]'::jsonb) from public.organizadores x),
    'bitacora',                (select coalesce(jsonb_agg(to_jsonb(x) order by x.id), '[]'::jsonb) from public.bitacora x),
    'incidencias',             (select coalesce(jsonb_agg(to_jsonb(x) order by x.id), '[]'::jsonb) from privado.incidencias x))
$$;

create or replace function privado.panel_respaldo(s jsonb) returns jsonb language plpgsql volatile as $$
declare
  t jsonb := privado.respaldo_tablas();      -- primero la foto; la entrada de la bitácora va después y no entra en este respaldo
  nom text;
  todo text;
  hx text;
  h jsonb := '{}';
  f jsonb := '{}';
begin
  for nom in select k from jsonb_object_keys(t) k loop
    h := h || jsonb_build_object(nom, encode(extensions.digest(convert_to((t -> nom)::text, 'UTF8'), 'sha256'), 'hex'));
    f := f || jsonb_build_object(nom, jsonb_array_length(t -> nom));
  end loop;
  todo := t::text;
  hx := encode(extensions.digest(convert_to(todo, 'UTF8'), 'sha256'), 'hex');
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Respaldo',
    'descargado · ' || greatest(round(octet_length(todo) / 1024.0), 1) || ' KB · huella ' || left(hx, 12), null,
    jsonb_build_object('bytes', octet_length(todo), 'huella', hx, 'filas', f));
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'formato', 'ciic-respaldo-1', 'version', privado.version(),
    'generadoEn', privado.ahora(), 'generadoPor', privado.quien(s), 'filas', f, 'huellas', h, 'huella', hx, 'tablas', t);
end $$;

create or replace function privado.ultimo_respaldo() returns jsonb language sql stable as $$
  select (select jsonb_build_object('fecha', to_char(b.creado_en at time zone 'America/Lima', 'YYYY-MM-DD HH24:MI:SS'), 'quien', b.quien,
                                    'bytes', coalesce((b.despues ->> 'bytes')::int, 0))
          from public.bitacora b where b.accion = 'Respaldo' order by b.id desc limit 1)
$$;

-- ── Pasar a producción (R-43) ──
create or replace function privado.panel_preparar_produccion(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  c public.config;
  n int;
  nz int;
  v_prev text;
begin
  select * into c from public.config where id = 1 for update;
  if c.modo <> 'PRUEBA' then return privado.fallo('modo_produccion', 'La base ya está en modo PRODUCCION.'); end if;
  if c.abierto then return privado.requiere_cierre(); end if;
  if coalesce(privado.jtext(b -> 'llave'), '') <> 'PRODUCCION' then return privado.fallo('valor_invalido', 'Para confirmar, escribe PRODUCCION.'); end if;
  perform 1 from public.actividades order by id for update;
  select count(*) into n from public.inscripciones;
  v_prev := privado.permitir_masivo();
  delete from public.inscripciones where true;                -- con sus actividades (en cascada); los disparadores descuentan
  delete from public.bitacora where true;
  delete from public.intentos where true;
  delete from privado.solicitudes where true;
  delete from privado.trafico where true;
  delete from privado.incidencias where true;
  delete from public.padron where privado.es_doc_de_prueba(documento);   -- solo documentos del tester (ZQX…): ninguna persona real
  get diagnostics nz = row_count;
  perform privado.restaurar_masivo(v_prev);
  perform privado.recalcular_inscritos();
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Pasar a producción',
    n || ' inscripciones de prueba eliminadas · clave del tester borrada · padrón y actividades intactos'
      || case when nz > 0 then ' (salvo ' || nz || ' documentos del tester, ZQX…)' else '' end,
    jsonb_build_object('modo', 'PRUEBA', 'inscripciones', n), jsonb_build_object('modo', 'PRODUCCION', 'inscripciones', 0));
  update public.config set modo = 'PRODUCCION' where id = 1;    -- R-37: el disparador borra la clave del tester
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'eliminadas', n, 'padronPrueba', nz, 'config', privado.config_json());
end $$;

-- ── Vaciar datos de prueba (R-44): igual que en 07, más el tráfico ──
create or replace function privado.panel_vaciar_prueba(b jsonb, s jsonb) returns jsonb language plpgsql as $$
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
  delete from privado.trafico where true;
  perform privado.restaurar_masivo(v_prev);
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Vaciar datos de prueba',
    (n ->> 'padron') || ' en el padrón, ' || (n ->> 'actividades') || ' actividades y ' || (n ->> 'inscripciones') || ' inscripciones eliminadas · configuración y equipo intactos',
    n, jsonb_build_object('padron', 0, 'actividades', 0, 'inscripciones', 0));
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'eliminados', n);
end $$;

-- ── La puerta: igual que en 05, más contar cada llamada, el tráfico y el último respaldo en el resumen,
--    y las acciones panel_respaldo y panel_preparar_produccion ──
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

do $$ begin  -- comprobación posterior: integridad de contadores
  if not (privado.integridad() ->> 'ok')::boolean then
    raise exception 'Integridad rota después de la migración: se revierte.';
  end if;
end $$;

commit;
