-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones · 04 · SPRINT 2 · INTEGRIDAD Y DATOS     contrato v5.5
--  Va después de 03_sprint1_seguridad.sql. Se puede volver a correr.
--
--  2.1  Padrón mínimo (R-22, R-35): una etapa por documento; datos libres en jsonb.
--  2.2  Inscripciones con nombres, apellidos, correo obligatorio y aviso de privacidad (R-13, R-14, D6).
--  2.3  Idempotencia con ámbito (R-32): solicitud UUID + acción + quien llama.
--  2.4  Cupo final (D4): panel_actividad ya no acepta "delta".
--  2.5  Contadores por disparador (R-33): actividades.inscritos lo mueven solo los disparadores.
--  2.6  Listas y grupo (R-38): panel_lista, panel_grupo_marcar.
--  2.7  Exportar con registro en la bitácora (R-39): panel_exportar, panel_registros.
--  2.8  Importar padrón (R-42).
--  2.11 De prueba a real (R-44, R-45): panel_vaciar_prueba, panel_actividades_importar.
--  +    estado con conActividades (D3) y config.aviso_version (D6), adelantados del Sprint 4.
-- ════════════════════════════════════════════════════════════════════════
begin;

do $$ begin
  if exists (select 1 from public.config where id = 1 and modo = 'PRODUCCION' and abierto) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
  if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'padron' and column_name = 'nombre')
     and exists (select documento from public.padron group by documento having count(*) > 1) then
    raise exception 'Hay documentos en más de una etapa del padrón (% casos). D2 exige una sola: decide cuál queda y borra las otras filas antes de aplicar.',
      (select count(*) from (select documento from public.padron group by documento having count(*) > 1) x);
  end if;
end $$;

create or replace function privado.version() returns text language sql immutable as $$ select '5.5-s2'::text $$;

-- Esta migración reescribe tablas enteras a propósito (R-40): permiso solo dentro de esta transacción.
set local ciic.masivo = 'confirmado';


-- ═════════ 2.1 Padrón mínimo ══════════════════════════════════════════════
alter table public.padron add column if not exists datos jsonb;
do $$ begin
  if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'padron' and column_name = 'nombre') then
    update public.padron set datos = nullif(jsonb_strip_nulls(jsonb_build_object('nombre', nullif(btrim(nombre), ''), 'fecha_compra', fecha_compra)), '{}'::jsonb);
    alter table public.padron drop column nombre, drop column fecha_compra;
  end if;
  if exists (select 1 from pg_constraint where conname = 'padron_pkey' and array_length(conkey, 1) = 2) then
    alter table public.padron drop constraint padron_pkey;
    alter table public.padron add constraint padron_pkey primary key (documento);
  end if;
end $$;


-- ═════════ 2.2 Inscripciones ══════════════════════════════════════════════
alter table public.inscripciones add column if not exists nombres           text    not null default '';
alter table public.inscripciones add column if not exists apellidos         text    not null default '';
alter table public.inscripciones add column if not exists acepta_privacidad boolean not null default false;
alter table public.inscripciones add column if not exists aviso_version     int;
do $$ begin
  if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'inscripciones' and column_name = 'nombre' and is_generated = 'NEVER') then
    -- "Ana María Quispe Rojas" → nombres "Ana María", apellidos "Quispe Rojas"; 2 palabras → 1 y 1; 1 palabra → solo nombres.
    update public.inscripciones i set nombres = x.n, apellidos = x.a
    from (select codigo,
                 case when cardinality(w) >= 3 then array_to_string(w[1:cardinality(w) - 2], ' ') else w[1] end n,
                 case when cardinality(w) >= 3 then w[cardinality(w) - 1] || ' ' || w[cardinality(w)] when cardinality(w) = 2 then w[2] else '' end a
          from (select codigo, regexp_split_to_array(btrim(nombre), '\s+') w from public.inscripciones) t) x
    where x.codigo = i.codigo;
    alter table public.inscripciones drop column nombre;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'inscripciones' and column_name = 'nombre') then
    -- Se conserva "nombre" como columna calculada: las funciones y reportes que la leen siguen funcionando.
    alter table public.inscripciones add column nombre text generated always as (btrim(nombres || ' ' || apellidos)) stored;
  end if;
end $$;

alter table public.config add column if not exists aviso_version int not null default 1;
do $$ begin
  alter table public.config add constraint config_aviso_version check (aviso_version >= 1);
exception when duplicate_object then null; end $$;


-- ═════════ 2.6 Marca de grupo ═════════════════════════════════════════════
alter table public.inscripcion_actividades add column if not exists en_grupo     boolean not null default false;
alter table public.inscripcion_actividades add column if not exists en_grupo_por uuid;
alter table public.inscripcion_actividades add column if not exists en_grupo_en  timestamptz;


-- ═════════ 2.3 Idempotencia ═══════════════════════════════════════════════
create table if not exists privado.solicitudes (
  actor      text not null,          -- 'doc:<documento>' en la página · 'uid:<cuenta>' o 'tester:<rol>' en el panel
  accion     text not null,
  id         text not null,          -- la solicitud (UUID) que mandó la página o el panel
  huella     text not null,          -- SHA-256 del resto de la petición
  respuesta  jsonb not null,
  creado_en  timestamptz not null default now(),
  primary key (actor, accion, id)
);
create index if not exists solicitudes_creado on privado.solicitudes (creado_en);
alter table privado.solicitudes enable row level security;
revoke all on privado.solicitudes from public, anon, authenticated;

create or replace function privado.es_uuid(t text) returns boolean language sql immutable as $$
  select coalesce(t, '') ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
$$;

create or replace function privado.es_escritura(accion text) returns boolean language sql immutable as $$
  select accion in ('registrar', 'panel_config', 'panel_actividad', 'panel_anular', 'panel_inscribir', 'panel_cambiar', 'panel_padron_agregar',
                    'panel_padron_quitar', 'panel_crear', 'panel_editar', 'panel_quitar', 'panel_horarios', 'panel_cruce', 'panel_equipo_rol',
                    'panel_equipo_activo', 'panel_grupo_marcar', 'panel_sincronizar', 'panel_padron_importar', 'panel_actividades_importar',
                    'panel_vaciar_prueba', 'panel_preparar_produccion')
$$;


-- ═════════ 2.5 Contadores por disparador (R-33) ═══════════════════════════
-- Fuente de verdad: inscripcion_actividades de inscripciones CONFIRMADO. Ninguna función suma ni resta a mano.

create or replace function privado.contar_actividad() returns trigger language plpgsql as $$
begin
  if tg_op = 'INSERT' then
    if exists (select 1 from public.inscripciones where codigo = new.codigo and estado = 'CONFIRMADO') then
      update public.actividades set inscritos = inscritos + 1 where id = new.actividad_id;
    end if;
  elsif tg_op = 'DELETE' then
    -- Si la inscripción se está borrando, ya no se ve: lo descontó su propio disparador antes de borrarse.
    if exists (select 1 from public.inscripciones where codigo = old.codigo and estado = 'CONFIRMADO') then
      update public.actividades set inscritos = inscritos - 1 where id = old.actividad_id;
    end if;
  elsif new.actividad_id is distinct from old.actividad_id then
    if exists (select 1 from public.inscripciones where codigo = new.codigo and estado = 'CONFIRMADO') then
      update public.actividades set inscritos = inscritos - 1 where id = old.actividad_id;
      update public.actividades set inscritos = inscritos + 1 where id = new.actividad_id;
    end if;
  end if;
  return null;
end $$;

create or replace function privado.contar_inscripcion() returns trigger language plpgsql as $$
begin
  if tg_op = 'DELETE' then                              -- BEFORE DELETE: sus actividades todavía existen
    if old.estado = 'CONFIRMADO' then
      update public.actividades a set inscritos = a.inscritos - 1
      from public.inscripcion_actividades ia where ia.codigo = old.codigo and ia.actividad_id = a.id;
    end if;
    return old;
  end if;
  if new.estado is distinct from old.estado then         -- AFTER UPDATE OF estado
    update public.actividades a set inscritos = a.inscritos + case when new.estado = 'CONFIRMADO' then 1 else -1 end
    from public.inscripcion_actividades ia where ia.codigo = new.codigo and ia.actividad_id = a.id;
  end if;
  return null;
end $$;

drop trigger if exists contar on public.inscripcion_actividades;
create trigger contar after insert or update of actividad_id or delete on public.inscripcion_actividades
  for each row execute function privado.contar_actividad();
drop trigger if exists contar_borrado on public.inscripciones;
create trigger contar_borrado before delete on public.inscripciones for each row execute function privado.contar_inscripcion();
drop trigger if exists contar_estado on public.inscripciones;
create trigger contar_estado after update of estado on public.inscripciones for each row execute function privado.contar_inscripcion();

create or replace function privado.integridad() returns jsonb language sql stable as $$
  select jsonb_build_object('ok', count(*) = 0, 'descuadres', coalesce(jsonb_agg(a.id order by a.id), '[]'::jsonb))
  from public.actividades a
  where a.inscritos <> (select count(*) from public.inscripcion_actividades ia join public.inscripciones i using (codigo)
                        where ia.actividad_id = a.id and i.estado = 'CONFIRMADO')
$$;


-- ═════════ Datos de la persona (página y panel) ═══════════════════════════

create or replace function privado.datos_persona(b jsonb) returns jsonb language plpgsql stable as $$
declare
  v_nombres text := privado.texto_limpio(b -> 'nombres', 60);
  v_apellidos text := privado.texto_limpio(b -> 'apellidos', 60);
  v_correo text := lower(privado.texto_limpio(b -> 'correo', 100));
  v_tel jsonb := privado.normalizar_celular(b -> 'pais', b -> 'celular');
begin
  if length(v_nombres) < 2 then return privado.fallo('datos_invalidos', 'Escribe tus nombres.', '{"campo":"nombres"}'); end if;
  if length(v_apellidos) < 2 then return privado.fallo('datos_invalidos', 'Escribe tus apellidos.', '{"campo":"apellidos"}'); end if;
  if v_correo !~ '^[^\s@]+@[^\s@]+\.[^\s@]{2,}$' then return privado.fallo('datos_invalidos', 'Escribe tu correo institucional.', '{"campo":"correo"}'); end if;
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

drop function if exists privado.guardar(text, text, text, smallint, text[], jsonb, text, int, uuid);
create or replace function privado.guardar(p_doc text, p jsonb, p_etapa smallint, p_ids text[], p_origen text, p_ronda int, p_user uuid)
returns text language plpgsql volatile as $$
declare v_codigo text := privado.nuevo_codigo();
begin
  insert into public.inscripciones (codigo, documento, nombres, apellidos, correo, etapa, celular, pais, acepta_whatsapp, acepta_privacidad, aviso_version,
                                    origen, ronda, registrado_por)
  values (v_codigo, p_doc, p ->> 'nombres', p ->> 'apellidos', p ->> 'correo', p_etapa, p -> 'tel' ->> 'numero', p -> 'tel' ->> 'pais', true, true,
          (select aviso_version from public.config where id = 1), p_origen, p_ronda, p_user);
  insert into public.inscripcion_actividades (codigo, actividad_id, actividad_nombre)       -- el disparador suma los inscritos
  select v_codigo, a.id, a.nombre from public.actividades a where a.id = any (p_ids);
  return v_codigo;
end $$;

create or replace function privado.registrar(b jsonb, p_disp text) returns jsonb language plpgsql volatile as $$
declare
  dp jsonb := privado.datos_persona(b);
  v jsonb;
  k jsonb;
  c public.config;
  v_ids text[];
  a public.actividades;
  v_cod text;
  v_restr text;
begin
  if (dp ->> 'ok')::boolean is not true then return dp; end if;
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
    if exists (select 1 from public.inscripciones where documento = v ->> 'doc' and estado = 'CONFIRMADO') then return privado.duplicado(null); end if;
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
    v_cod := privado.guardar(v ->> 'doc', dp, (v ->> 'etapa')::smallint, v_ids, 'WEB', c.ronda, null);
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

create or replace function privado.panel_inscribir(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_doc text := privado.normalizar_doc(b -> 'dni');
  v_etapas smallint[];
  v_cod text;
  dp jsonb;
  k jsonb;
  amp jsonb;
  v_ids text[];
begin
  if not privado.es_documento(v_doc) then return privado.fallo('formato', 'Revisa el documento: 6 a 12 letras y números.'); end if;
  v_etapas := privado.etapas_de_doc(v_doc);
  if coalesce(array_length(v_etapas, 1), 0) = 0 then return privado.fallo('no_encontrado', 'Este documento no está en el padrón. Agrégalo primero en Participantes.'); end if;
  select codigo into v_cod from public.inscripciones where documento = v_doc and estado = 'CONFIRMADO';
  if found then return privado.duplicado_panel(v_cod); end if;
  dp := privado.datos_persona(b);
  if (dp ->> 'ok')::boolean is not true then return dp; end if;
  k := privado.combinacion(b -> 'actividades', true);
  if (k ->> 'ok')::boolean is not true then return k; end if;
  v_ids := array(select jsonb_array_elements_text(k -> 'ids'));
  perform 1 from public.actividades x where x.id = any (v_ids) order by x.id for update;
  amp := privado.revisar_cupos(v_ids, '{}', b, s, 'inscripción desde el panel');
  if amp ->> 'tipo' = 'advertencia' then return amp; end if;
  begin
    v_cod := privado.guardar(v_doc, dp, v_etapas[1], v_ids, 'PANEL', (select ronda from public.config where id = 1), (s ->> 'uid')::uuid);
  exception when unique_violation then
    select codigo into v_cod from public.inscripciones where documento = v_doc and estado = 'CONFIRMADO';
    return privado.duplicado_panel(v_cod);
  end;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Inscripción desde el panel', v_cod || ' · ' || v_doc || ' · ' || array_to_string(v_ids, ' + '));
  return jsonb_build_object('ok', true, 'tipo', 'registrado', 'origen', 'PANEL', 'ampliadas', amp,
    'mensaje', 'Inscrito con el código ' || v_cod || '.') || privado.comprobante(v_cod) || jsonb_build_object('celular', dp -> 'tel' ->> 'numero');
end $$;

create or replace function privado.panel_anular(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_cod text := upper(btrim(privado.jtext(b -> 'codigo')));
  i public.inscripciones;
  v_acts text;
begin
  select * into i from public.inscripciones where codigo = v_cod and estado = 'CONFIRMADO' for update;
  if not found then return privado.fallo('no_encontrado', 'No hay una inscripción confirmada con el código ' || v_cod || '.'); end if;
  perform 1 from public.actividades where id in (select actividad_id from public.inscripcion_actividades where codigo = v_cod) order by id for update;
  select string_agg(actividad_id, ' y ' order by actividad_id) into v_acts from public.inscripcion_actividades where codigo = v_cod;
  update public.inscripciones set estado = 'ANULADO', modificado_por = (s ->> 'uid')::uuid, modificado_en = now() where codigo = v_cod;   -- el disparador libera los cupos
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Anulación', v_cod || ' · ' || i.documento || ' · libera ' || v_acts);
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'codigo', v_cod);
end $$;

create or replace function privado.panel_cambiar(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_cod text := upper(btrim(privado.jtext(b -> 'codigo')));
  i public.inscripciones;
  k jsonb;
  amp jsonb;
  v_nuevas text[];
  v_viejas text[];
begin
  select * into i from public.inscripciones where codigo = v_cod and estado = 'CONFIRMADO' for update;
  if not found then return privado.fallo('no_encontrado', 'No hay una inscripción confirmada con el código ' || v_cod || '.'); end if;
  k := privado.combinacion(b -> 'actividades', true);
  if (k ->> 'ok')::boolean is not true then return k; end if;
  v_nuevas := array(select jsonb_array_elements_text(k -> 'ids'));
  v_viejas := array(select actividad_id from public.inscripcion_actividades where codigo = v_cod);
  if (select array_agg(x order by x) from unnest(v_nuevas) x) = (select array_agg(x order by x) from unnest(v_viejas) x) then
    return privado.fallo('sin_cambios', 'Es la misma combinación que ya tiene.');
  end if;
  perform 1 from public.actividades x where x.id = any (v_nuevas || v_viejas) order by x.id for update;
  amp := privado.revisar_cupos(v_nuevas, v_viejas, b, s, 'cambio de inscripción');
  if amp ->> 'tipo' = 'advertencia' then return amp; end if;
  delete from public.inscripcion_actividades where codigo = v_cod and not (actividad_id = any (v_nuevas));          -- el disparador resta
  insert into public.inscripcion_actividades (codigo, actividad_id, actividad_nombre)                             -- y suma
  select v_cod, a.id, a.nombre from public.actividades a where a.id = any (v_nuevas) and not (a.id = any (v_viejas));
  update public.inscripciones set modificado_por = (s ->> 'uid')::uuid, modificado_en = now() where codigo = v_cod;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Cambio de inscripción',
    v_cod || ' · ' || array_to_string(v_viejas, ' + ') || ' → ' || array_to_string(v_nuevas, ' + '), to_jsonb(v_viejas), to_jsonb(v_nuevas));
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'codigo', v_cod, 'antes', to_jsonb(v_viejas), 'ahora', to_jsonb(v_nuevas), 'ampliadas', amp);
end $$;

create or replace function privado.panel_sincronizar(s jsonb) returns jsonb language plpgsql volatile as $$
declare n int;
begin
  perform 1 from public.actividades order by id for update;
  perform privado.recalcular_inscritos();
  select count(*) into n from public.inscripciones where estado = 'CONFIRMADO';
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Recontar inscritos', 'contadores recalculados desde las inscripciones (' || n || ' confirmadas)');
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'inscritos', n, 'integridad', privado.integridad());
end $$;


-- ═════════ 2.4 Cupo final (D4) ════════════════════════════════════════════

create or replace function privado.panel_actividad(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_id text := btrim(privado.jtext(b -> 'id'));
  a public.actividades;
  v_cupo int;
  cambios text[] := '{}';
begin
  if privado.tiene(b, 'delta') then return privado.fallo('valor_invalido', 'Envía el cupo final (cupo), no un incremento.'); end if;
  select * into a from public.actividades where id = v_id for update;
  if not found then return privado.fallo('actividad_invalida', 'No existe la actividad ' || v_id || '.'); end if;
  v_cupo := a.cupo;
  if privado.tiene(b, 'cupo') then v_cupo := privado.entero(b -> 'cupo'); end if;
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


-- ═════════ Padrón: alta, baja, participantes e importación ════════════════

create or replace function privado.panel_padron_agregar(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_doc text := privado.normalizar_doc(b -> 'documento');
  v_etapa int := privado.entero(b -> 'etapa');
  ya smallint;
begin
  if not privado.es_documento(v_doc) then return privado.fallo('formato', 'Revisa el documento: 6 a 12 letras y números.'); end if;
  if v_etapa is null or v_etapa not in (1, 2, 3) then return privado.fallo('valor_invalido', 'Elige la etapa de venta: 1, 2 o 3.'); end if;
  select etapa into ya from public.padron where documento = v_doc;
  if found then
    return privado.fallo('ya_existe', 'El documento ' || v_doc || ' ya está en el padrón con la Etapa ' || ya ||
      '. La etapa no se cambia: si es un error, quítalo (sin inscripción y con el sistema cerrado) y vuelve a agregarlo.', jsonb_build_object('etapa', ya));
  end if;
  insert into public.padron (documento, etapa, origen, creado_por) values (v_doc, v_etapa, 'PANEL', (s ->> 'uid')::uuid);
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Padrón', 'agregado ' || v_doc || ' a la Etapa ' || v_etapa);
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'doc', v_doc, 'etapa', v_etapa);
end $$;

create or replace function privado.panel_padron_quitar(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_doc text := privado.normalizar_doc(b -> 'documento');
  ya smallint;
begin
  if privado.abierto() then return privado.requiere_cierre(); end if;
  if exists (select 1 from public.inscripciones where documento = v_doc and estado = 'CONFIRMADO') then
    return privado.fallo('tiene_inscripcion', 'Esta persona tiene una inscripción confirmada: anúlala primero.');
  end if;
  delete from public.padron where documento = v_doc returning etapa into ya;
  if not found then return privado.fallo('no_encontrado', 'No está en el padrón.'); end if;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Padrón', 'quitado ' || v_doc || ' (Etapa ' || ya || ')');
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'doc', v_doc);
end $$;

create or replace function privado.panel_participantes(b jsonb) returns jsonb language plpgsql stable as $$
declare
  v_etapa int := privado.entero(b -> 'etapa');
  v_estado text := nullif(privado.jtext(b -> 'estado'), '');
  q text := upper(btrim(privado.jtext(b -> 'q')));
  v_pag int := greatest(coalesce(privado.entero(b -> 'pagina'), 1), 1);
  r jsonb;
begin
  with base as (
    select p.documento, p.etapa, p.origen, p.orden, ul.codigo, coalesce(ul.estado, 'SIN_INSCRIBIR') estado, ul.acts, coalesce(ul.nom, '') nombre
    from public.padron p
    left join lateral (select i.codigo, i.estado, i.apellidos || ', ' || i.nombres nom,
                              (select jsonb_agg(ia.actividad_id order by ia.actividad_id) from public.inscripcion_actividades ia where ia.codigo = i.codigo) acts
                       from public.inscripciones i where i.documento = p.documento order by (i.estado = 'CONFIRMADO') desc, i.orden desc limit 1) ul on true
    where (v_etapa is null or p.etapa = v_etapa)
      and (q = '' or p.documento like '%' || privado.normalizar_doc(to_jsonb(q)) || '%' or upper(coalesce(ul.nom, '')) like '%' || q || '%')),
  filtrado as (select * from base where v_estado is null or estado = v_estado)
  select jsonb_build_object('ok', true, 'tipo', 'panel', 'total', (select count(*) from filtrado), 'pagina', v_pag, 'porPagina', 50,
    'resumen', (select jsonb_build_object('padron', count(*), 'inscritos', count(*) filter (where estado = 'CONFIRMADO'),
                 'sinInscribir', count(*) filter (where estado = 'SIN_INSCRIBIR'), 'agregados', count(*) filter (where origen = 'PANEL')) from base),
    'filas', coalesce((select jsonb_agg(jsonb_build_object('doc', f.documento, 'etapa', f.etapa, 'nombre', f.nombre, 'origen', f.origen,
                        'estado', f.estado, 'codigo', f.codigo, 'actividades', coalesce(f.acts, '[]'::jsonb)) order by f.orden)
                       from (select * from filtrado order by orden offset (v_pag - 1) * 50 limit 50) f), '[]'::jsonb)) into r;
  return r;
end $$;

-- R-42: documento y etapa; nunca cambia la etapa de quien ya está. Hasta 10 000 filas por llamada.
-- Por conjuntos (sin recorrer fila por fila): 10 000 filas en una sola operación. Sprint 2.1: antes, un bucle con un
-- objeto que crecía en cada fila (cuadrático) agotaba el límite de 3 s con 5000 filas (hallado en el reporte del Sprint 2).
-- Reglas: la PRIMERA aparición válida de un documento nuevo lo agrega; la etapa vigente es la del padrón o la de esa
-- primera aparición; cada otra fila válida es "ya existía" (misma etapa) o "conflicto" (otra etapa, que no se cambia).
create or replace function privado.panel_padron_importar(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare r jsonb;
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
    (r ->> 'agregados') || ' agregados · ' || (r ->> 'existentes') || ' ya existían · ' || (r ->> 'totalConflictos') || ' conflictos · ' || (r ->> 'totalInvalidos') || ' inválidos');
  return jsonb_build_object('ok', true, 'tipo', 'panel') || r;
end $$;


-- ═════════ 2.6 y 2.7 Listas, grupo y exportación ══════════════════════════

-- Orden alfabético igual en cualquier servidor: sin tildes, sin mayúsculas, y la ñ después de la n (como en español).
-- Sprint 2.1: la Ñ se traduce aquí (no depende de lower() en cada codificación) y el collate "C" va en cada ORDER BY:
-- el de dentro de la función no se hereda (hallado en el reporte del Sprint 2: con locale español, Ñahui y Nuñez salían antes de Nunez).
create or replace function privado.clave_orden(t text) returns text language sql immutable as $$
  select replace(lower(translate(coalesce(t, ''), 'ÁÉÍÓÚÜÑáéíóúü', 'AEIOUUñaeiouu')), 'ñ', 'n{')
$$;

create or replace function privado.filas_lista(b jsonb) returns table (actividad text, apellidos text, nombres text, doc text, correo text, celular text,
                                                                      etapa smallint, codigo text, origen text, en_grupo boolean)
language plpgsql stable as $$
declare
  v_id text := nullif(btrim(privado.jtext(b -> 'id')), '');
  v_etapa int := privado.entero(b -> 'etapa');
  q text := upper(btrim(coalesce(privado.jtext(b -> 'q'), '')));
  dig text := regexp_replace(q, '\D', '', 'g');
begin
  return query
  select ia.actividad_id, i.apellidos, i.nombres, i.documento, i.correo, i.celular, i.etapa, i.codigo, i.origen, ia.en_grupo
  from public.inscripcion_actividades ia join public.inscripciones i using (codigo)
  where i.estado = 'CONFIRMADO' and (v_id is null or ia.actividad_id = v_id) and (v_etapa is null or i.etapa = v_etapa)
    and (q = '' or i.documento like '%' || privado.normalizar_doc(to_jsonb(q)) || '%'
         or (length(dig) >= 6 and right(regexp_replace(i.celular, '\D', '', 'g'), least(9, length(dig))) = right(dig, least(9, length(dig))))
         or upper(i.apellidos || ' ' || i.nombres) like '%' || q || '%')
  order by ia.actividad_id, privado.clave_orden(i.apellidos) collate "C", privado.clave_orden(i.nombres) collate "C", i.codigo;
end $$;

create or replace function privado.panel_lista(b jsonb) returns jsonb language sql stable as $$
  select jsonb_build_object('ok', true, 'tipo', 'panel', 'total', count(*), 'pendientes', count(*) filter (where not f.en_grupo),
    'filas', coalesce(jsonb_agg(jsonb_build_object('actividad', f.actividad, 'apellidos', f.apellidos, 'nombres', f.nombres, 'doc', f.doc, 'correo', f.correo,
                                'celular', f.celular, 'etapa', f.etapa, 'codigo', f.codigo, 'origen', f.origen, 'enGrupo', f.en_grupo)
                                order by f.actividad, privado.clave_orden(f.apellidos) collate "C", privado.clave_orden(f.nombres) collate "C", f.codigo), '[]'::jsonb))
  from privado.filas_lista(b) f
$$;

create or replace function privado.panel_grupo_marcar(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_id text := btrim(privado.jtext(b -> 'id'));
  v_ag boolean := (b -> 'agregado') is distinct from 'false'::jsonb;
  n int;
  v_prev text;
begin
  if not exists (select 1 from public.actividades where id = v_id) then return privado.fallo('actividad_invalida', 'Elige la actividad.'); end if;
  v_prev := privado.permitir_masivo();          -- "marcar todos" puede tocar más de 10 filas a propósito
  update public.inscripcion_actividades ia set en_grupo = v_ag, en_grupo_por = (s ->> 'uid')::uuid, en_grupo_en = now()
  where ia.actividad_id = v_id and ia.codigo in (select jsonb_array_elements_text(case when jsonb_typeof(b -> 'codigos') = 'array' then b -> 'codigos' else '[]'::jsonb end))
    and exists (select 1 from public.inscripciones i where i.codigo = ia.codigo and i.estado = 'CONFIRMADO');
  get diagnostics n = row_count;
  perform privado.restaurar_masivo(v_prev);
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Grupo ' || v_id, n || case when v_ag then ' marcados en el grupo' else ' marcados por agregar' end);
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'id', v_id, 'marcados', n, 'agregado', v_ag);
end $$;

-- R-39: nivel 1; solo lee, pero cada descarga queda en la bitácora.
create or replace function privado.panel_exportar(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare r jsonb; n int;
begin
  select coalesce(jsonb_agg(jsonb_build_array(f.actividad, a.nombre, privado.fecha_txt(a.fecha), privado.hora_txt(a.inicio) || '–' || privado.hora_txt(a.fin),
                                             f.doc, f.apellidos, f.nombres, f.correo, f.celular, f.etapa::text, f.codigo, f.origen,
                                             case when f.en_grupo then 'SI' else 'NO' end)
                            order by f.actividad, privado.clave_orden(f.apellidos) collate "C", privado.clave_orden(f.nombres) collate "C", f.codigo), '[]'::jsonb), count(*)
  into r, n
  from privado.filas_lista(jsonb_build_object('id', b -> 'id', 'etapa', b -> 'etapa')) f join public.actividades a on a.id = f.actividad;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Exportación',
    'CSV · actividad ' || coalesce(nullif(btrim(privado.jtext(b -> 'id')), ''), 'todas') || ' · etapa ' || coalesce(privado.entero(b -> 'etapa')::text, 'todas') || ' · ' || n || ' filas');
  return jsonb_build_object('ok', true, 'tipo', 'panel',
    'encabezados', '["Actividad","Nombre de la actividad","Fecha","Horario","DNI","Apellidos","Nombres","Correo","Celular","Etapa","Código","Origen","En el grupo"]'::jsonb,
    'filas', r);
end $$;

create or replace function privado.panel_registros(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  f text := coalesce(nullif(privado.jtext(b -> 'formato'), ''), 'inscripciones');
  r jsonb;
begin
  if f = 'padron' then
    r := jsonb_build_object('ok', true, 'tipo', 'panel', 'encabezados', '["Documento","Etapa","Origen","Estado","Código"]'::jsonb,
      'filas', coalesce((select jsonb_agg(jsonb_build_array(p.documento, p.etapa::text, p.origen, coalesce(i.estado, 'SIN_INSCRIBIR'), coalesce(i.codigo, '')) order by p.orden)
                         from public.padron p left join public.inscripciones i on i.documento = p.documento and i.estado = 'CONFIRMADO'), '[]'::jsonb));
    perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Exportación', 'CSV del padrón · ' || jsonb_array_length(r -> 'filas') || ' filas');
    return r;
  end if;
  r := jsonb_build_object('ok', true, 'tipo', 'panel',
    'encabezados', '["Fecha/Hora","Código","Documento","Apellidos","Nombres","Correo","Celular","País","Etapa","ID Actividad 1","Actividad 1","ID Actividad 2","Actividad 2","Estado","Origen","Ronda"]'::jsonb,
    'filas', coalesce((select jsonb_agg(jsonb_build_array(to_char(i.creado_en at time zone 'America/Lima', 'YYYY-MM-DD HH24:MI:SS'), i.codigo, i.documento,
                         i.apellidos, i.nombres, i.correo, i.celular, i.pais, i.etapa::text, coalesce(x.ids[1], ''), coalesce(x.noms[1], ''),
                         coalesce(x.ids[2], ''), coalesce(x.noms[2], ''), i.estado, i.origen, i.ronda::text) order by i.orden)
                       from public.inscripciones i
                       left join lateral (select array_agg(ia.actividad_id order by a.fecha, a.inicio, ia.actividad_id) ids,
                                                 array_agg(ia.actividad_nombre order by a.fecha, a.inicio, ia.actividad_id) noms
                                          from public.inscripcion_actividades ia left join public.actividades a on a.id = ia.actividad_id
                                          where ia.codigo = i.codigo) x on true), '[]'::jsonb));
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Exportación', 'CSV de inscripciones · ' || jsonb_array_length(r -> 'filas') || ' filas');
  return r;
end $$;

create or replace function privado.registro_json(i public.inscripciones) returns jsonb language sql stable as $$
  select jsonb_build_object('fecha', to_char(i.creado_en at time zone 'America/Lima', 'YYYY-MM-DD HH24:MI:SS'), 'codigo', i.codigo,
    'doc', i.documento, 'nombre', i.nombre, 'nombres', i.nombres, 'apellidos', i.apellidos, 'correo', i.correo, 'celular', i.celular,
    'etapa', i.etapa, 'estado', i.estado, 'origen', i.origen, 'ronda', i.ronda,
    'actividades', (select coalesce(jsonb_agg(jsonb_build_object('id', ia.actividad_id, 'nombre', ia.actividad_nombre) order by ia.actividad_id), '[]'::jsonb)
                    from public.inscripcion_actividades ia where ia.codigo = i.codigo))
$$;


-- ═════════ 2.11 De la base de prueba a la real (R-44, R-45) ═══════════════

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
  delete from public.inscripciones;                -- con sus actividades (en cascada)
  delete from public.cruces_permitidos;
  delete from public.actividades;
  delete from public.padron;
  delete from public.bitacora;
  delete from public.intentos;
  delete from privado.solicitudes;
  delete from privado.incidencias;
  perform privado.restaurar_masivo(v_prev);
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Vaciar datos de prueba',
    (n ->> 'padron') || ' en el padrón, ' || (n ->> 'actividades') || ' actividades y ' || (n ->> 'inscripciones') || ' inscripciones eliminadas · configuración y equipo intactos',
    n, jsonb_build_object('padron', 0, 'actividades', 0, 'inscripciones', 0));
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'eliminados', n);
end $$;

-- R-45: catálogo desde CSV; valida cada fila como panel_crear; las que ya existen no se modifican; nacen ocultas salvo visible = SI.
create or replace function privado.panel_actividades_importar(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  f jsonb;
  k int := 0;
  dv jsonb;
  d jsonb;
  v_id text;
  v_cupo int;
  v_pref text;
  agregadas int := 0;
  existentes jsonb := '[]'::jsonb;
  invalidas jsonb := '[]'::jsonb;
begin
  if jsonb_typeof(b -> 'filas') <> 'array' or jsonb_array_length(b -> 'filas') not between 1 and 500 then
    return privado.fallo('valor_invalido', 'Envía entre 1 y 500 actividades.');
  end if;
  perform pg_advisory_xact_lock(hashtext('ciic_crear_actividad'));
  for f in select * from jsonb_array_elements(b -> 'filas') loop
    k := k + 1;
    v_id := btrim(coalesce(privado.jtext(f -> 'id'), ''));
    if v_id <> '' and v_id !~ '^[A-Za-z0-9_-]{1,20}$' then
      invalidas := invalidas || jsonb_build_object('fila', k, 'motivo', 'ID inválido: usa letras, números, guion o guion bajo (hasta 20).');
      continue;
    end if;
    if v_id <> '' and exists (select 1 from public.actividades where id = v_id) then existentes := existentes || to_jsonb(v_id); continue; end if;
    dv := privado.datos_actividad(jsonb_build_object('tipo', f -> 'tipo', 'nombre', f -> 'nombre', 'lugar', coalesce(f -> 'lugar', '""'), 'fecha', f -> 'fecha',
                                                     'inicio', f -> 'inicio', 'fin', f -> 'fin', 'descripcion', coalesce(f -> 'descripcion', '""'),
                                                     'grupoModo', coalesce(nullif(f ->> 'entrega', ''), 'ENLACE'), 'grupo', coalesce(f -> 'enlace', '""')),
                                  '{"tipo":"TALLER","nombre":"","lugar":"","fecha":"","inicio":"","fin":""}');
    if dv ? 'error' then invalidas := invalidas || jsonb_build_object('fila', k, 'motivo', dv ->> 'error'); continue; end if;
    v_cupo := privado.entero(f -> 'cupo');
    if v_cupo is null or v_cupo < 1 or v_cupo > 1000 then invalidas := invalidas || jsonb_build_object('fila', k, 'motivo', 'El cupo debe estar entre 1 y 1000.'); continue; end if;
    d := dv -> 'datos';
    if v_id = '' then
      v_pref := case d ->> 'tipo' when 'VISITA' then 'VIS' when 'TALLER' then 'TAL' else left(d ->> 'tipo', 3) end;
      select v_pref || lpad((coalesce(max(substring(x.id from '^' || v_pref || '(\d+)$')::int), 0) + 1)::text, 2, '0') into v_id
      from public.actividades x where x.id ~ ('^' || v_pref || '\d+$');
    end if;
    insert into public.actividades (id, tipo, nombre, lugar, fecha, inicio, fin, cupo, cupo_inicial, publicada, descripcion, grupo_modo, grupo_whatsapp, creado_por)
    values (v_id, d ->> 'tipo', d ->> 'nombre', d ->> 'lugar', to_date(d ->> 'fecha', 'DD/MM/YYYY'), (d ->> 'inicio')::time, (d ->> 'fin')::time, v_cupo, v_cupo,
            upper(btrim(coalesce(f ->> 'visible', ''))) in ('SI', 'SÍ', 'S', '1', 'TRUE', 'VERDADERO'), d ->> 'descripcion', d ->> 'grupoModo', d ->> 'grupo',
            (s ->> 'uid')::uuid);
    agregadas := agregadas + 1;
  end loop;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Importar actividades',
    agregadas || ' agregadas · ' || jsonb_array_length(existentes) || ' ya existían · ' || jsonb_array_length(invalidas) || ' inválidas');
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'agregadas', agregadas, 'existentes', existentes, 'invalidas', invalidas);
end $$;


-- ═════════ Configuración en las respuestas ════════════════════════════════

create or replace function privado.config_json() returns jsonb language sql stable as $$
  select jsonb_build_object('abierto', c.abierto, 'ronda', c.ronda, 'cierraEn', privado.cierra_en_seg(), 'etapas', to_jsonb(c.etapas),
    'etapasVisita', to_jsonb(c.etapas_visita), 'dosTalleres', c.dos_talleres, 'mismoDia', c.mismo_dia, 'margenMin', c.margen_min,
    'pasoCupo', c.paso_cupo, 'refresco', c.refresco, 'modo', c.modo,
    'limiteDispositivo', c.limite_dispositivo, 'limiteRed', c.limite_red, 'ventanaMin', c.ventana_min,
    'limiteMasivo', c.limite_masivo, 'avisoVersion', c.aviso_version)
  from public.config c where c.id = 1
$$;


-- ═════════ LA PUERTA: public.api(p) ═══════════════════════════════════════

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
    return privado.fallo('ocupado', 'Sistema ocupado, reintenta.');
  when others then
    get stacked diagnostics v_estado = returned_sqlstate, v_msg = message_text;
    insert into privado.incidencias (accion, sqlstate, mensaje) values (left(accion, 60), v_estado, left(v_msg, 500)) returning id into v_inc;
    return privado.fallo('error_servidor', 'Ocurrió un error en el sistema. Intenta de nuevo en unos segundos.',
                         jsonb_build_object('incidencia', 'INC-' || lpad(v_inc::text, 4, '0')));
end $$;


-- ═════════ Permisos ═══════════════════════════════════════════════════════
revoke all on all functions in schema privado from public, anon, authenticated;
revoke all on function public.api(jsonb) from public;
grant execute on function public.api(jsonb) to anon, authenticated;
revoke all on all tables in schema privado from anon, authenticated;

-- Los contadores quedan exactos desde ahora: se recalculan una vez y luego solo los mueven los disparadores.
select privado.recalcular_inscritos();

do $$ begin
  if not (privado.integridad() ->> 'ok')::boolean then raise exception 'Integridad rota después de la migración: se revierte.'; end if;
end $$;

commit;
