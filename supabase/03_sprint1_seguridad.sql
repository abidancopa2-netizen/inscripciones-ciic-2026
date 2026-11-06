-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones · 03 · SPRINT 1 · SEGURIDAD          contrato v5.5
--  Va después de 01_esquema.sql y 02_api.sql. Se puede volver a correr.
--
--  1.1 Sin comprobantes (R-01, R-31): "duplicado" y "registrado" públicos sin código.
--  1.2 Incidencias (R-36): un error interno guarda el detalle en privado.incidencias
--      y la persona solo ve el número. Acción panel_incidencias (nivel 2).
--  1.3 IP real (§8): privado.red() según config.ip_cabecera; acción admin_cabeceras.
--  1.4 Producción sin clave (R-37): al pasar a PRODUCCION se borra la ADMIN_KEY.
--  1.5 Propietario único (D9): índice único; el panel no asigna ni toca al propietario.
--      privado.asignar_propietario(correo) y privado.cambiar_propietario(correo).
--  1.6 Niveles de rol (R-26): nivel por acción y, en panel_config, por campo.
--  1.7 Bitácora con antes y después (R-30).
--  1.8 Protección masiva (R-40): DELETE/UPDATE de más de config.limite_masivo filas
--      y TRUNCATE bloqueados en 6 tablas, salvo set local ciic.masivo = 'confirmado'.
--
--  Requisitos: respaldo tomado (si hay datos reales); probado antes en local con el tester.
-- ════════════════════════════════════════════════════════════════════════
begin;

-- Comprobación previa: no se aplica con inscripciones abiertas en producción.
do $$ begin
  if exists (select 1 from public.config where id = 1 and modo = 'PRODUCCION' and abierto) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
  if (select count(*) from public.organizadores where rol = 'propietario') > 1 then
    raise exception 'Hay más de un propietario. Deja uno solo antes de aplicar (D9): update organizadores set rol = ''admin'' where user_id = ''…'';';
  end if;
end $$;

create or replace function privado.version() returns text language sql immutable as $$ select '5.5-s1'::text $$;


-- ═════════ Esquema ════════════════════════════════════════════════════════

alter table public.config   add column if not exists limite_masivo int  not null default 10;
alter table public.config   add column if not exists ip_cabecera   text not null default 'auto';
do $$ begin
  alter table public.config add constraint config_limite_masivo check (limite_masivo between 1 and 100000);
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.config add constraint config_ip_cabecera check (ip_cabecera in ('auto', 'cf-connecting-ip', 'x-real-ip', 'xff-primero', 'xff-ultimo'));
exception when duplicate_object then null; end $$;

alter table public.bitacora add column if not exists antes   jsonb;
alter table public.bitacora add column if not exists despues jsonb;

-- 1.2 Incidencias: el detalle técnico de cada error interno, sin datos personales.
create table if not exists privado.incidencias (
  id         bigint generated always as identity primary key,
  creado_en  timestamptz not null default now(),
  accion     text not null default '',
  sqlstate   text not null default '',
  mensaje    text not null default ''
);
alter table privado.incidencias enable row level security;
revoke all on privado.incidencias from public, anon, authenticated;

-- 1.5 Un solo propietario.
create unique index if not exists un_propietario on public.organizadores ((true)) where rol = 'propietario';


-- ═════════ 1.7 Bitácora con antes y después ═══════════════════════════════

create or replace function privado.bitacora(p_user uuid, p_quien text, p_accion text, p_detalle text, p_antes jsonb, p_despues jsonb) returns void
language sql as $$
  insert into public.bitacora (user_id, quien, accion, detalle, antes, despues)
  values (p_user, p_quien, p_accion, coalesce(p_detalle, ''), p_antes, p_despues)
$$;


-- ═════════ 1.8 Protección contra operaciones masivas (R-40) ═══════════════

create or replace function privado.masivo_permitido() returns boolean language sql stable as $$
  select coalesce(current_setting('ciic.masivo', true), '') = 'confirmado'
$$;

-- Permite una operación masiva solo dentro de la función que la llama; devuelve el valor anterior para restaurarlo.
create or replace function privado.permitir_masivo() returns text language plpgsql volatile as $$
declare v_prev text := coalesce(current_setting('ciic.masivo', true), '');
begin
  perform set_config('ciic.masivo', 'confirmado', true);
  return v_prev;
end $$;
create or replace function privado.restaurar_masivo(p_prev text) returns void language plpgsql volatile as $$
begin
  perform set_config('ciic.masivo', coalesce(p_prev, ''), true);
end $$;

create or replace function privado.proteger_masivo() returns trigger language plpgsql as $$
declare n bigint; lim int;
begin
  if privado.masivo_permitido() then return null; end if;
  select count(*) into n from viejas;
  select limite_masivo into lim from public.config where id = 1;
  if n > coalesce(lim, 10) then
    raise exception 'Operación masiva bloqueada: % de % filas en %.', lower(tg_op), n, tg_table_name
      using errcode = 'P0001',
            hint = 'Revisa el WHERE con un SELECT count(*). Si de verdad es masiva: haz un respaldo y, en la misma transacción, set local ciic.masivo = ''confirmado''; (documentación §20).';
  end if;
  return null;
end $$;

create or replace function privado.proteger_truncate() returns trigger language plpgsql as $$
begin
  if privado.masivo_permitido() then return null; end if;
  raise exception 'Operación masiva bloqueada: truncate de %.', tg_table_name
    using errcode = 'P0001',
          hint = 'Haz un respaldo y, en la misma transacción, set local ciic.masivo = ''confirmado''; (documentación §20).';
end $$;

do $$
declare t text;
begin
  foreach t in array array['padron', 'actividades', 'cruces_permitidos', 'inscripciones', 'inscripcion_actividades', 'organizadores'] loop
    execute format('drop trigger if exists masivo_update on public.%I', t);
    execute format('drop trigger if exists masivo_delete on public.%I', t);
    execute format('drop trigger if exists masivo_truncate on public.%I', t);
    execute format('create trigger masivo_update after update on public.%I referencing old table as viejas for each statement execute function privado.proteger_masivo()', t);
    execute format('create trigger masivo_delete after delete on public.%I referencing old table as viejas for each statement execute function privado.proteger_masivo()', t);
    execute format('create trigger masivo_truncate before truncate on public.%I for each statement execute function privado.proteger_truncate()', t);
  end loop;
end $$;

-- Las funciones internas que tocan muchas filas a propósito declaran el permiso (y lo restauran).
create or replace function privado.recalcular_inscritos() returns void language plpgsql volatile as $$
declare v_prev text := privado.permitir_masivo();
begin
  update public.actividades a set inscritos = coalesce(c.n, 0)
  from public.actividades a2
  left join (select ia.actividad_id id, count(*)::int n
             from public.inscripcion_actividades ia join public.inscripciones i using (codigo)
             where i.estado = 'CONFIRMADO' group by ia.actividad_id) c on c.id = a2.id
  where a.id = a2.id and a.inscritos is distinct from coalesce(c.n, 0);
  perform privado.restaurar_masivo(v_prev);
end $$;

create or replace function privado.admin_limpiar(b jsonb) returns jsonb language plpgsql volatile as $$
declare
  docs text[];
  padr text[];
  n int;
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
  delete from public.padron where documento = any (padr) and origen = 'PANEL';
  perform privado.restaurar_masivo(v_prev);
  if (b -> 'intentos') = 'true'::jsonb then delete from public.intentos; end if;
  perform privado.recalcular_inscritos();
  return jsonb_build_object('ok', true, 'tipo', 'admin', 'eliminados', n);
end $$;


-- ═════════ 1.4 Producción sin clave de prueba (R-37) ══════════════════════

create or replace function privado.al_pasar_a_produccion() returns trigger language plpgsql as $$
begin
  delete from privado.claves where nombre = 'ADMIN_KEY';
  perform privado.bitacora(null, 'Sistema', 'Modo PRODUCCION', 'clave del tester borrada', jsonb_build_object('modo', old.modo), jsonb_build_object('modo', new.modo));
  return null;
end $$;
drop trigger if exists produccion_sin_clave on public.config;
create trigger produccion_sin_clave after update of modo on public.config
  for each row when (new.modo = 'PRODUCCION' and old.modo is distinct from 'PRODUCCION')
  execute function privado.al_pasar_a_produccion();


-- ═════════ 1.3 IP real (§8) ═══════════════════════════════════════════════

create or replace function privado.cabeceras() returns jsonb language sql stable as $$
  select coalesce(nullif(current_setting('request.headers', true), '')::jsonb, '{}'::jsonb)
$$;

-- 'auto': cf-connecting-ip → x-real-ip → primer valor de x-forwarded-for. Se fija en el Sprint 3 con admin_cabeceras.
create or replace function privado.red() returns text language sql stable as $$
  with h as (select privado.cabeceras() j, (select ip_cabecera from public.config where id = 1) modo),
       x as (select j, modo, string_to_array(regexp_replace(coalesce(j ->> 'x-forwarded-for', ''), '\s', '', 'g'), ',') xff from h)
  select coalesce(nullif(left(case modo
      when 'cf-connecting-ip' then j ->> 'cf-connecting-ip'
      when 'x-real-ip'        then j ->> 'x-real-ip'
      when 'xff-primero'      then xff[1]
      when 'xff-ultimo'       then xff[cardinality(xff)]
      else coalesce(nullif(j ->> 'cf-connecting-ip', ''), nullif(j ->> 'x-real-ip', ''), xff[1]) end, 64), ''), 'desconocida')
  from x
$$;

create or replace function privado.admin_cabeceras() returns jsonb language sql stable as $$
  select jsonb_build_object('ok', true, 'tipo', 'admin',
    'cabeceras', (select coalesce(jsonb_agg(k order by k), '[]'::jsonb) from jsonb_object_keys(privado.cabeceras()) k),
    'cf-connecting-ip', privado.cabeceras() ->> 'cf-connecting-ip',
    'x-real-ip', privado.cabeceras() ->> 'x-real-ip',
    'x-forwarded-for', privado.cabeceras() ->> 'x-forwarded-for',
    'ipCabecera', (select ip_cabecera from public.config where id = 1),
    'red', privado.red(),
    'nota', 'Compara estos valores con tu IP pública (por ejemplo, la que muestra ifconfig.me) y fija config.ip_cabecera en el Sprint 3.')
$$;


-- ═════════ 1.1 Sin comprobantes (R-01, R-31) ══════════════════════════════

-- Público: un único mensaje, sin código, actividades ni enlaces. El parámetro se conserva por compatibilidad.
create or replace function privado.duplicado(p_codigo text) returns jsonb language sql immutable as $$
  select privado.fallo('duplicado', 'Este documento ya está inscrito. Si necesitas ayuda, escríbenos.')
$$;

-- Panel: el equipo sí ve el código, para ir a "Cambiar inscripción".
create or replace function privado.duplicado_panel(p_codigo text) returns jsonb language sql immutable as $$
  select privado.fallo('duplicado', 'Ya tiene una inscripción confirmada (' || p_codigo || '). Usa "Cambiar inscripción".', jsonb_build_object('codigo', p_codigo))
$$;

-- Confirmación pública (pantalla 3): sin código; con el celular para "te agregaremos con tu número".
create or replace function privado.confirmacion(p_codigo text) returns jsonb language sql stable as $$
  select (privado.comprobante(p_codigo) - 'codigo') || jsonb_build_object('celular', i.celular)
  from public.inscripciones i where i.codigo = p_codigo
$$;

-- registrar: igual que en 02, salvo la respuesta final (sin código).
create or replace function privado.registrar(b jsonb, p_disp text) returns jsonb language plpgsql volatile as $$
declare
  v_nombre text := privado.texto_limpio(b -> 'nombre', 80);
  v_correo text := lower(privado.texto_limpio(b -> 'correo', 100));
  v_tel jsonb := privado.normalizar_celular(b -> 'pais', b -> 'celular');
  v jsonb;
  k jsonb;
  c public.config;
  v_ids text[];
  a public.actividades;
  v_cod text;
  v_restr text;
begin
  if length(v_nombre) < 3 then return privado.fallo('datos_invalidos', 'Escribe tu nombre completo.'); end if;
  if v_correo <> '' and v_correo !~ '^[^\s@]+@[^\s@]+\.[^\s@]+$' then return privado.fallo('datos_invalidos', 'El correo no parece válido.'); end if;
  if v_tel is null then
    return privado.fallo('celular_invalido', case when upper(coalesce(nullif(privado.jtext(b -> 'pais'), ''), 'PE')) = 'PE'
      then 'Revisa tu celular: en Perú son 9 dígitos y empiezan con 9.' else 'Revisa tu celular: escribe entre 6 y 14 dígitos, sin el código de país.' end);
  end if;
  if (b -> 'aceptaWhatsapp') is distinct from 'true'::jsonb then
    return privado.fallo('sin_consentimiento', 'Para coordinar tus actividades necesitamos tu autorización para escribirte por WhatsApp.');
  end if;

  v := privado.verificar(b -> 'dni', true, p_disp);
  if (v ->> 'ok')::boolean is not true then return v; end if;

  perform set_config('lock_timeout', '2000', true);
  begin
    select * into c from public.config where id = 1 for share;
    if not c.abierto then return privado.fallo('cerrado', 'Las inscripciones se cerraron antes de que confirmaras. Tu elección no se guardó.'); end if;
    if privado.entero(b -> 'ronda') is distinct from c.ronda then
      return privado.fallo('recargar', 'El sistema se actualizó mientras elegías. Vuelve a verificar tu documento para ver las opciones vigentes.',
                           jsonb_build_object('ronda', c.ronda));
    end if;
    k := privado.combinacion(b -> 'actividades', false);
    if (k ->> 'ok')::boolean is not true then return k; end if;
    v_ids := array(select jsonb_array_elements_text(k -> 'ids'));
    if (k ->> 'visitas')::int > 0 and not (v ->> 'puedeVisita')::boolean then
      return privado.fallo('visita_no_habilitada', 'Las visitas técnicas están habilitadas para ' || privado.texto_etapas(c.etapas_visita) || '. Elige 2 talleres.');
    end if;
    perform 1 from public.actividades x where x.id = any (v_ids) order by x.id for update;
    select codigo into v_cod from public.inscripciones where documento = v ->> 'doc' and estado = 'CONFIRMADO';
    if found then return privado.duplicado(v_cod); end if;
    for a in select * from public.actividades x where x.id = any (v_ids) order by x.fecha, x.inicio loop
      if not a.publicada then return privado.fallo('no_disponible', 'Una de las actividades elegidas ya no está disponible. Elige otra combinación.',
                                                   jsonb_build_object('actividades', privado.actividades_publicas())); end if;
      if a.inscritos >= a.cupo then
        return privado.fallo('lleno', '"' || a.nombre || '" se acaba de llenar. Elige otra combinación, por favor.',
                             jsonb_build_object('actividadId', a.id, 'actividades', privado.actividades_publicas()));
      end if;
    end loop;
    if (k ->> 'visitas')::int = 0 and not c.dos_talleres and (v ->> 'puedeVisita')::boolean
       and exists (select 1 from public.actividades x where x.publicada and x.tipo = 'VISITA' and x.inscritos < x.cupo) then
      return privado.fallo('combinacion_invalida', 'Mientras queden visitas con cupo, tu combinación debe incluir una visita técnica.', '{"motivo":"falta_visita"}');
    end if;
    v_cod := privado.guardar(v ->> 'doc', v_nombre, v_correo, (v ->> 'etapa')::smallint, v_ids, v_tel, 'WEB', c.ronda, null);
  exception
    when lock_not_available then
      return privado.fallo('ocupado', 'Estás en la fila: hay muchas personas inscribiéndose. Seguimos intentando por ti.');
    when unique_violation then
      get stacked diagnostics v_restr = constraint_name;
      if v_restr = 'un_confirmado_por_documento' then return privado.duplicado(null); end if;
      return privado.fallo('ocupado', 'Estás en la fila: hay muchas personas inscribiéndose. Seguimos intentando por ti.');
    when check_violation then
      return privado.fallo('lleno', 'Una de tus actividades se acaba de llenar. Elige otra combinación, por favor.',
                           jsonb_build_object('actividades', privado.actividades_publicas()));
  end;
  return jsonb_build_object('ok', true, 'tipo', 'registrado', 'mensaje', 'Inscripción confirmada.') || privado.confirmacion(v_cod);
end $$;

-- panel_inscribir: igual que en 02, salvo que el duplicado del panel trae el código.
create or replace function privado.panel_inscribir(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_doc text := privado.normalizar_doc(b -> 'dni');
  v_nombre text := privado.texto_limpio(b -> 'nombre', 80);
  v_tel jsonb := privado.normalizar_celular(b -> 'pais', b -> 'celular');
  v_etapas smallint[];
  v_cod text;
  k jsonb;
  amp jsonb;
  v_ids text[];
begin
  if not privado.es_documento(v_doc) then return privado.fallo('formato', 'Revisa el documento: 6 a 12 letras y números.'); end if;
  v_etapas := privado.etapas_de_doc(v_doc);
  if coalesce(array_length(v_etapas, 1), 0) = 0 then return privado.fallo('no_encontrado', 'Este documento no está en el padrón. Agrégalo primero en Participantes.'); end if;
  select codigo into v_cod from public.inscripciones where documento = v_doc and estado = 'CONFIRMADO';
  if found then return privado.duplicado_panel(v_cod); end if;
  if length(v_nombre) < 3 then return privado.fallo('datos_invalidos', 'Escribe el nombre completo.'); end if;
  if v_tel is null then return privado.fallo('celular_invalido', 'Revisa el celular: en Perú son 9 dígitos y empiezan con 9.'); end if;
  if (b -> 'aceptaWhatsapp') is distinct from 'true'::jsonb then return privado.fallo('sin_consentimiento', 'Marca que la persona autorizó el contacto por WhatsApp.'); end if;
  k := privado.combinacion(b -> 'actividades', true);
  if (k ->> 'ok')::boolean is not true then return k; end if;
  v_ids := array(select jsonb_array_elements_text(k -> 'ids'));
  perform 1 from public.actividades x where x.id = any (v_ids) order by x.id for update;
  amp := privado.revisar_cupos(v_ids, '{}', b, s, 'inscripción desde el panel');
  if amp ->> 'tipo' = 'advertencia' then return amp; end if;
  begin
    v_cod := privado.guardar(v_doc, v_nombre, lower(privado.texto_limpio(b -> 'correo', 100)), v_etapas[1], v_ids, v_tel, 'PANEL',
                             (select ronda from public.config where id = 1), (s ->> 'uid')::uuid);
  exception when unique_violation then
    select codigo into v_cod from public.inscripciones where documento = v_doc and estado = 'CONFIRMADO';
    return privado.duplicado_panel(v_cod);
  end;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Inscripción desde el panel', v_cod || ' · ' || v_doc || ' · ' || array_to_string(v_ids, ' + '));
  return jsonb_build_object('ok', true, 'tipo', 'registrado', 'origen', 'PANEL', 'ampliadas', amp,
    'mensaje', 'Inscrito con el código ' || v_cod || '.') || privado.comprobante(v_cod);
end $$;


-- ═════════ 1.6 Niveles de rol (R-26) ══════════════════════════════════════
-- 1 consulta (operador) · 2 modificaciones (admin) · 3 habilitan el sistema (propietario).
-- Acciones que aún no existen ya tienen su nivel: así nadie las usa por debajo cuando lleguen.

create or replace function privado.nivel(accion text, p jsonb) returns int language sql immutable as $$
  select case
    when accion = 'panel_config' then
      case when (p -> 'abierto') = 'true'::jsonb or privado.tiene(p, 'etapas') or privado.tiene(p, 'etapasVisita') or privado.tiene(p, 'dosTalleres')
             or privado.tiene(p, 'refresco') or privado.tiene(p, 'umbral') or privado.tiene(p, 'limiteDispositivo') or privado.tiene(p, 'limiteRed')
           then 3 else 2 end
    when accion in ('panel_resumen', 'panel_participantes', 'panel_buscar', 'panel_verificar_celular', 'panel_lista', 'panel_grupo_marcar', 'panel_exportar') then 1
    when accion in ('panel_actividad', 'panel_crear', 'panel_editar', 'panel_quitar', 'panel_cruce', 'panel_inscribir', 'panel_cambiar', 'panel_anular',
                    'panel_padron_agregar', 'panel_padron_quitar', 'panel_incidencias', 'panel_sincronizar', 'panel_registros') then 2
    else 3 end      -- panel_horarios, panel_equipo*, panel_respaldo, panel_padron_importar, panel_actividades_importar,
                    -- panel_vaciar_prueba, panel_preparar_produccion y cualquier acción nueva
$$;

-- Se conserva por compatibilidad con 02; ya no se usa.
create or replace function privado.rol_minimo(accion text) returns int language sql immutable as $$ select privado.nivel(accion, '{}'::jsonb) $$;

create or replace function privado.sin_permiso(p_nivel int) returns jsonb language sql immutable as $$
  select privado.fallo('sin_permiso', case when p_nivel >= 3 then 'Esta acción es del propietario.' else 'Esta acción requiere rol admin o superior.' end,
                       jsonb_build_object('nivel', p_nivel))
$$;


-- ═════════ 1.2 Incidencias (R-36) ═════════════════════════════════════════

create or replace function privado.panel_incidencias() returns jsonb language sql stable as $$
  select jsonb_build_object('ok', true, 'tipo', 'panel', 'incidencias', coalesce((
    select jsonb_agg(jsonb_build_object('id', 'INC-' || lpad(i.id::text, 4, '0'),
                                        'fecha', to_char(i.creado_en at time zone 'America/Lima', 'YYYY-MM-DD HH24:MI:SS'),
                                        'accion', i.accion, 'detalle', i.sqlstate || ' · ' || i.mensaje) order by i.id desc)
    from (select * from privado.incidencias order by id desc limit 50) i), '[]'::jsonb))
$$;


-- ═════════ 1.5 y 1.7 Equipo: propietario único, bitácora con antes y después ══

create or replace function privado.panel_equipo_rol(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_u uuid;
  v_rol text := nullif(privado.jtext(b -> 'rol'), '');
  v_nombre text := privado.texto_limpio(b -> 'nombre', 80);
  v_correo text;
  o public.organizadores;
begin
  if v_rol = 'propietario' then return privado.fallo('no_permitido', 'El propietario es único (el creador) y solo se asigna en SQL.'); end if;
  if v_rol is not null and v_rol not in ('admin', 'operador') then return privado.fallo('valor_invalido', 'Rol desconocido.'); end if;
  begin v_u := privado.jtext(b -> 'usuario')::uuid; exception when others then return privado.fallo('no_encontrado', 'No existe esa cuenta.'); end;
  select email into v_correo from auth.users where id = v_u;
  if not found then return privado.fallo('no_encontrado', 'No existe esa cuenta.'); end if;
  select * into o from public.organizadores where user_id = v_u for update;
  if o.rol = 'propietario' then return privado.fallo('no_permitido', 'La cuenta del propietario no se modifica desde el panel.'); end if;
  insert into public.organizadores (user_id, nombre, rol) values (v_u, coalesce(nullif(v_nombre, ''), split_part(v_correo, '@', 1)), v_rol)
  on conflict (user_id) do update set rol = excluded.rol, nombre = case when v_nombre <> '' then v_nombre else public.organizadores.nombre end;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Equipo', v_correo || ' · rol: ' || coalesce(o.rol, 'sin rol') || ' → ' || coalesce(v_rol, 'sin rol'),
                           jsonb_build_object('rol', o.rol, 'nombre', o.nombre),
                           (select jsonb_build_object('rol', x.rol, 'nombre', x.nombre) from public.organizadores x where x.user_id = v_u));
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'usuario', v_u, 'rol', v_rol);
end $$;

create or replace function privado.panel_equipo_activo(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_u uuid;
  v_act boolean := (b -> 'activo') = 'true'::jsonb;
  v_correo text;
  o public.organizadores;
begin
  begin v_u := privado.jtext(b -> 'usuario')::uuid; exception when others then return privado.fallo('no_encontrado', 'No existe esa cuenta.'); end;
  select email into v_correo from auth.users where id = v_u;
  if not found then return privado.fallo('no_encontrado', 'No existe esa cuenta.'); end if;
  select * into o from public.organizadores where user_id = v_u for update;
  if o.rol = 'propietario' then return privado.fallo('no_permitido', 'La cuenta del propietario no se desactiva desde el panel.'); end if;
  insert into public.organizadores (user_id, nombre, activo) values (v_u, split_part(v_correo, '@', 1), v_act)
  on conflict (user_id) do update set activo = excluded.activo;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Equipo', v_correo || case when v_act then ' activada' else ' desactivada' end,
                           jsonb_build_object('activo', coalesce(o.activo, true)), jsonb_build_object('activo', v_act));
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'usuario', v_u, 'activo', v_act);
end $$;

-- Solo en el SQL Editor (§12.3): la primera cuenta de propietario. Falla si ya hay otro.
create or replace function privado.asignar_propietario(p_correo text) returns text language plpgsql volatile as $$
declare v_u uuid; v_actual uuid;
begin
  select id into v_u from auth.users where lower(email) = lower(btrim(p_correo));
  if v_u is null then raise exception 'No hay una cuenta con el correo %. Invítala primero en Authentication → Users.', p_correo; end if;
  select user_id into v_actual from public.organizadores where rol = 'propietario';
  if v_actual is not null and v_actual <> v_u then
    raise exception 'Ya hay un propietario. Para cambiarlo usa: select privado.cambiar_propietario(''%'');', p_correo;
  end if;
  insert into public.organizadores (user_id, nombre, rol, activo) values (v_u, split_part(p_correo, '@', 1), 'propietario', true)
  on conflict (user_id) do update set rol = 'propietario', activo = true;
  perform privado.bitacora(null, 'SQL', 'Propietario', p_correo || ' es el propietario', null, jsonb_build_object('propietario', p_correo));
  return p_correo || ' es el propietario.';
end $$;

-- Solo en el SQL Editor (§19.6, pérdida de acceso): pasa el rol en una sola transacción; el anterior queda como admin.
create or replace function privado.cambiar_propietario(p_correo text) returns text language plpgsql volatile as $$
declare v_u uuid; v_actual uuid;
begin
  select id into v_u from auth.users where lower(email) = lower(btrim(p_correo));
  if v_u is null then raise exception 'No hay una cuenta con el correo %.', p_correo; end if;
  select user_id into v_actual from public.organizadores where rol = 'propietario' for update;
  update public.organizadores set rol = 'admin' where rol = 'propietario' and user_id <> v_u;
  insert into public.organizadores (user_id, nombre, rol, activo) values (v_u, split_part(p_correo, '@', 1), 'propietario', true)
  on conflict (user_id) do update set rol = 'propietario', activo = true;
  perform privado.bitacora(null, 'SQL', 'Propietario', 'el rol pasa a ' || p_correo,
                           jsonb_build_object('propietario', (select email from auth.users where id = v_actual)), jsonb_build_object('propietario', p_correo));
  return p_correo || ' es el nuevo propietario; el anterior quedó como admin.';
end $$;


-- ═════════ 1.7 Configuración, actividades y horarios con antes y después ══

create or replace function privado.panel_config(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
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

create or replace function privado.panel_actividad(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_id text := btrim(privado.jtext(b -> 'id'));
  a public.actividades;
  v_cupo int;
  cambios text[] := '{}';
begin
  select * into a from public.actividades where id = v_id for update;
  if not found then return privado.fallo('actividad_invalida', 'No existe la actividad ' || v_id || '.'); end if;
  v_cupo := a.cupo;
  if privado.tiene(b, 'cupo') then v_cupo := privado.entero(b -> 'cupo'); end if;
  if privado.tiene(b, 'delta') then v_cupo := a.cupo + privado.entero(b -> 'delta'); end if;      -- se quita en el Sprint 2 (D4)
  if v_cupo is null or v_cupo < 1 then return privado.fallo('cupo_invalido', 'El cupo debe ser un número mayor que 0.'); end if;
  if privado.abierto() and (v_cupo < a.cupo or (b -> 'publicada') = 'false'::jsonb and a.publicada) then return privado.requiere_cierre(); end if;
  if v_cupo <> a.cupo then
    if v_cupo < a.inscritos then
      if (b -> 'confirmar') is distinct from 'true'::jsonb then
        return privado.fallo('advertencia', '"' || a.nombre || '" tiene ' || privado.n_inscritos(a.inscritos) || '. No se puede bajar a ' || v_cupo ||
          ' sin anular a ' || (a.inscritos - v_cupo) || ' personas. Puedes dejarla en ' || a.inscritos || ': queda llena y no entra nadie más.',
          jsonb_build_object('accion', 'cerrar_cupo', 'minimo', a.inscritos));
      end if;
      v_cupo := a.inscritos;
    end if;
    update public.actividades set cupo = v_cupo where id = v_id;
    cambios := cambios || ('cupo ' || a.cupo || ' → ' || v_cupo);
  end if;
  if jsonb_typeof(b -> 'publicada') = 'boolean' and (b ->> 'publicada')::boolean <> a.publicada then
    update public.actividades set publicada = (b ->> 'publicada')::boolean where id = v_id;
    cambios := cambios || case when (b ->> 'publicada')::boolean then 'mostrada' else 'oculta' end;
  end if;
  if array_length(cambios, 1) > 0 then
    perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Actividad ' || v_id, array_to_string(cambios, ' · '),
                             jsonb_build_object('cupo', a.cupo, 'publicada', a.publicada),
                             (select jsonb_build_object('cupo', x.cupo, 'publicada', x.publicada) from public.actividades x where x.id = v_id));
  end if;
  select * into a from public.actividades where id = v_id;
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'actividad', privado.actividad_completa(a));
end $$;

create or replace function privado.panel_horarios(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  c public.config;
  m int;
  antes jsonb;
begin
  select * into c from public.config where id = 1 for update;
  antes := jsonb_build_object('mismoDia', c.mismo_dia, 'margenMin', c.margen_min);
  if (b -> 'mismoDia') = 'false'::jsonb and c.mismo_dia and c.abierto then return privado.requiere_cierre(); end if;
  if privado.tiene(b, 'margenMin') then
    m := privado.entero(b -> 'margenMin');
    if m is null or m < 0 or m > 240 then return privado.fallo('valor_invalido', 'El margen debe estar entre 0 y 240 minutos.'); end if;
    if m > c.margen_min and c.abierto then return privado.requiere_cierre(); end if;
    update public.config set margen_min = m where id = 1;
  end if;
  if jsonb_typeof(b -> 'mismoDia') = 'boolean' then update public.config set mismo_dia = (b ->> 'mismoDia')::boolean where id = 1; end if;
  select * into c from public.config where id = 1;
  if antes is distinct from jsonb_build_object('mismoDia', c.mismo_dia, 'margenMin', c.margen_min) then
    perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Horarios', 'mismo día ' || case when c.mismo_dia then 'SI' else 'NO' end || ' · margen ' || c.margen_min || ' min',
                             antes, jsonb_build_object('mismoDia', c.mismo_dia, 'margenMin', c.margen_min));
  end if;
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'mismoDia', c.mismo_dia, 'margenMin', c.margen_min, 'cruces', privado.lista_cruces());
end $$;


-- ═════════ LA PUERTA: public.api(p) ═══════════════════════════════════════

create or replace function public.api(p jsonb) returns jsonb
language plpgsql volatile security definer set search_path = public, privado, extensions, pg_temp as $$
declare
  accion text;
  s jsonb;
  chk jsonb;
  n int;
  v_estado text;
  v_msg text;
  v_inc bigint;
begin
  if p is null or jsonb_typeof(p) <> 'object' then return privado.fallo('peticion_invalida', 'Petición inválida.'); end if;
  accion := coalesce(p ->> 'action', '');
  perform privado.aplicar_cierre_programado();

  if accion = '' then return jsonb_build_object('ok', true, 'servicio', 'CIIC 2026 · API de inscripciones', 'version', privado.version()); end if;
  if accion = 'estado' then return privado.estado_publico(); end if;
  if accion = 'actividades' then return jsonb_build_object('ok', true, 'tipo', 'actividades', 'actividades', privado.actividades_publicas()); end if;
  if accion = 'verificar' then
    chk := privado.verificar(p -> 'dni', false, privado.dispositivo(p -> 'dispositivo'));
    if (chk ->> 'ok')::boolean then chk := chk || jsonb_build_object('actividades', privado.actividades_publicas()); end if;
    return chk;
  end if;
  if accion = 'registrar' then return privado.registrar(p, privado.dispositivo(p -> 'dispositivo')); end if;

  if accion like 'panel\_%' then
    s := privado.sesion(p);
    if s ? 'tipo' then return s; end if;
    n := privado.nivel(accion, p);
    if privado.rango(s ->> 'rol') < n then return privado.sin_permiso(n); end if;
    return case accion
      when 'panel_resumen'           then privado.panel_resumen(s)
      when 'panel_config'            then privado.panel_config(p, s)
      when 'panel_actividad'         then privado.panel_actividad(p, s)
      when 'panel_buscar'            then privado.panel_buscar(p)
      when 'panel_anular'            then privado.panel_anular(p, s)
      when 'panel_inscribir'         then privado.panel_inscribir(p, s)
      when 'panel_cambiar'           then privado.panel_cambiar(p, s)
      when 'panel_participantes'     then privado.panel_participantes(p)
      when 'panel_padron_agregar'    then privado.panel_padron_agregar(p, s)
      when 'panel_padron_quitar'     then privado.panel_padron_quitar(p, s)
      when 'panel_crear'             then privado.panel_crear(p, s)
      when 'panel_editar'            then privado.panel_editar(p, s)
      when 'panel_quitar'            then privado.panel_quitar(p, s)
      when 'panel_horarios'          then privado.panel_horarios(p, s)
      when 'panel_cruce'             then privado.panel_cruce(p, s)
      when 'panel_verificar_celular' then privado.panel_verificar_celular(p)
      when 'panel_registros'         then privado.panel_registros(p)
      when 'panel_sincronizar'       then privado.panel_sincronizar(s)
      when 'panel_incidencias'       then privado.panel_incidencias()
      when 'panel_equipo'            then privado.panel_equipo()
      when 'panel_equipo_rol'        then privado.panel_equipo_rol(p, s)
      when 'panel_equipo_activo'     then privado.panel_equipo_activo(p, s)
      else privado.fallo('accion_invalida', 'Acción no reconocida.') end;
  end if;

  -- Tester: clave ADMIN_KEY; todo menos admin_ping exige modo PRUEBA.
  if accion in ('admin_ping', 'admin_muestra', 'admin_limpiar', 'admin_cabeceras', 'admin_error') then
    chk := privado.con_admin(p, accion <> 'admin_ping');
    if chk is not null then return chk; end if;
    if accion = 'admin_error' then perform 1 / 0; end if;           -- error a propósito para probar las incidencias (R-36)
    return case accion
      when 'admin_ping'      then jsonb_build_object('ok', true, 'tipo', 'admin', 'version', privado.version(), 'config', privado.config_json())
      when 'admin_muestra'   then privado.admin_muestra(p)
      when 'admin_cabeceras' then privado.admin_cabeceras()
      else privado.admin_limpiar(p) end;
  end if;

  return privado.fallo('accion_invalida', 'Acción no reconocida.');
exception
  when lock_not_available or query_canceled or deadlock_detected or serialization_failure then
    return privado.fallo('ocupado', 'Sistema ocupado, reintenta.');
  when others then
    -- R-36: el detalle queda privado; la persona solo recibe el número.
    get stacked diagnostics v_estado = returned_sqlstate, v_msg = message_text;
    insert into privado.incidencias (accion, sqlstate, mensaje) values (left(accion, 60), v_estado, left(v_msg, 500)) returning id into v_inc;
    return privado.fallo('error_servidor', 'Ocurrió un error en el sistema. Intenta de nuevo en unos segundos.',
                         jsonb_build_object('incidencia', 'INC-' || lpad(v_inc::text, 4, '0')));
end $$;


-- ═════════ Permisos: solo la puerta es pública ════════════════════════════
revoke all on all functions in schema privado from public, anon, authenticated;
revoke all on function public.api(jsonb) from public;
grant execute on function public.api(jsonb) to anon, authenticated;
revoke all on all tables in schema privado from anon, authenticated;


-- Comprobación posterior: la integridad de los contadores sigue intacta.
do $$ begin
  if exists (select 1 from public.actividades a
             where a.inscritos <> (select count(*) from public.inscripcion_actividades ia join public.inscripciones i using (codigo)
                                   where ia.actividad_id = a.id and i.estado = 'CONFIRMADO')) then
    raise exception 'Integridad rota después de la migración: se revierte.';
  end if;
end $$;

commit;
