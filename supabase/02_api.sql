-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones · v5.1 (Supabase)
--  02 · API: todas las reglas del sistema, dentro de la base.
--  Supabase → SQL Editor → Run, DESPUÉS de 01_esquema.sql. Se puede volver a
--  correr cuando cambie: reemplaza funciones, no toca datos.
--
--  UNA puerta pública: public.api(p jsonb). Referencia: documentación v5.1.
--    · Participante: clave anon. Acciones estado, actividades, verificar, registrar.
--    · Paneles: sesión de Supabase Auth con código TOTP (aal2) y rol en organizadores.
--    · Tester: ADMIN_KEY, solo en modo PRUEBA.
-- ════════════════════════════════════════════════════════════════════════

-- ═════════ Utilidades ═════════════════════════════════════════════════════

create or replace function privado.version() returns text language sql immutable as $$ select '5.1'::text $$;

create or replace function privado.ahora() returns text language sql stable as $$
  select to_char(now() at time zone 'America/Lima', 'YYYY-MM-DD HH24:MI:SS')
$$;

create or replace function privado.fallo(p_tipo text, p_mensaje text, p_extra jsonb default '{}'::jsonb)
returns jsonb language sql immutable as $$
  select jsonb_build_object('ok', false, 'tipo', p_tipo, 'mensaje', p_mensaje) || coalesce(p_extra, '{}'::jsonb)
$$;

create or replace function privado.jtext(v jsonb) returns text language sql immutable as $$
  select case when v is null or jsonb_typeof(v) = 'null' then ''
              when jsonb_typeof(v) = 'string' then v #>> '{}'
              else v::text end
$$;

create or replace function privado.tiene(b jsonb, k text) returns boolean language sql immutable as $$
  select b ? k and jsonb_typeof(b -> k) <> 'null'
$$;

create or replace function privado.entero(v jsonb) returns int language sql immutable as $$
  select (substring(privado.jtext(v) from '^\s*([+-]?\d{1,9})'))::int
$$;

create or replace function privado.limpiar_doc(v jsonb) returns text language sql immutable as $$
  select upper(regexp_replace(
    case when jsonb_typeof(v) = 'number' then round((v #>> '{}')::numeric)::text else privado.jtext(v) end,
    '[\s.\-]', '', 'g'))
$$;

create or replace function privado.normalizar_doc(v jsonb) returns text language sql immutable as $$
  select case when s ~ '^\d+$' and length(s) < 8 then lpad(s, 8, '0') else s end
  from (select privado.limpiar_doc(v) as s) x
$$;

create or replace function privado.es_documento(s text) returns boolean language sql immutable as $$
  select coalesce(s ~ '^[A-Z0-9]{6,12}$' and s ~ '\d', false)
$$;

-- Limpia texto escrito por personas: sin caracteres de control ni fórmulas al inicio (CSV).
create or replace function privado.texto_limpio(v jsonb, p_max int) returns text language sql immutable as $$
  select left(btrim(regexp_replace(
           btrim(regexp_replace(regexp_replace(privado.jtext(v), E'[\\x01-\\x1F\\x7F]', ' ', 'g'), '\s+', ' ', 'g')),
           '^[=+\-@]+', '')), p_max)
$$;

create or replace function privado.normalizar_celular(p_pais jsonb, p_celular jsonb) returns jsonb
language plpgsql immutable as $$
declare
  paises constant jsonb := '{"PE":"51","CL":"56","CO":"57","EC":"593","BO":"591","AR":"54","MX":"52","BR":"55","VE":"58","PY":"595","UY":"598","ES":"34","US":"1"}';
  p text := upper(btrim(coalesce(nullif(privado.jtext(p_pais), ''), 'PE')));
  codigo text := paises ->> p;
  crudo text := btrim(privado.jtext(p_celular));
  d text;
begin
  if codigo is null then return null; end if;
  d := regexp_replace(crudo, '\D', '', 'g');
  if crudo ~ '^(\+|00)' or (p = 'PE' and length(d) = 11 and d like '519%') then
    d := regexp_replace(d, '^00', '');
    if left(d, length(codigo)) <> codigo then return null; end if;
    d := substr(d, length(codigo) + 1);
  end if;
  if (p = 'PE' and d ~ '^9\d{8}$') or (p <> 'PE' and d ~ '^\d{6,14}$') then
    return jsonb_build_object('numero', '+' || codigo || d, 'pais', p);
  end if;
  return null;
end $$;

create or replace function privado.texto_etapas(e smallint[]) returns text language sql immutable as $$
  select case coalesce(array_length(e, 1), 0)
    when 0 then 'ninguna etapa'
    when 1 then 'la Etapa ' || e[1]
    else 'las Etapas ' || array_to_string(e[1:array_length(e, 1) - 1], ', ') || ' y ' || e[array_length(e, 1)] end
$$;

create or replace function privado.fecha_txt(d date) returns text language sql immutable as $$ select to_char(d, 'DD/MM/YYYY') $$;
create or replace function privado.hora_txt(t time) returns text language sql immutable as $$ select to_char(t, 'HH24:MI') $$;
create or replace function privado.min_txt(seg int) returns text language sql immutable as $$
  select (seg / 60) || ':' || lpad((seg % 60)::text, 2, '0')
$$;

create or replace function privado.n_inscritos(n int) returns text language sql immutable as $$
  select n || case when n = 1 then ' inscrito' else ' inscritos' end
$$;

create or replace function privado.bitacora(p_user uuid, p_quien text, p_accion text, p_detalle text) returns void
language sql as $$
  insert into public.bitacora (user_id, quien, accion, detalle) values (p_user, p_quien, p_accion, coalesce(p_detalle, ''))
$$;

-- Recuenta inscritos desde las inscripciones confirmadas (tras editar tablas a mano o limpiar pruebas).
create or replace function privado.recalcular_inscritos() returns void language sql as $$
  update public.actividades a set inscritos = coalesce(c.n, 0)
  from public.actividades a2
  left join (select ia.actividad_id id, count(*)::int n
             from public.inscripcion_actividades ia join public.inscripciones i using (codigo)
             where i.estado = 'CONFIRMADO' group by ia.actividad_id) c on c.id = a2.id
  where a.id = a2.id and a.inscritos is distinct from coalesce(c.n, 0)
$$;


-- ═════════ Cierre avisado (R-27) ══════════════════════════════════════════
-- Se llama al inicio de cada api(): si ya pasó la hora del aviso, cierra y sube la ronda.
create or replace function privado.aplicar_cierre_programado() returns void language plpgsql volatile as $$
declare v_ronda int;
begin
  if exists (select 1 from public.config where id = 1 and abierto and cierre_en is not null and cierre_en <= now()) then
    update public.config set abierto = false, ronda = ronda + 1, cierre_en = null
     where id = 1 and abierto and cierre_en is not null and cierre_en <= now()
    returning ronda into v_ronda;
    if found then perform privado.bitacora(null, 'Sistema', 'Cierre programado', 'ronda ' || (v_ronda - 1) || ' → ' || v_ronda); end if;
  end if;
end $$;

create or replace function privado.cierra_en_seg() returns int language sql stable as $$
  select case when abierto and cierre_en is not null then greatest(0, ceil(extract(epoch from cierre_en - now()))::int) end
  from public.config where id = 1
$$;


-- ═════════ Límite de intentos (R-25) ══════════════════════════════════════

create or replace function privado.red() returns text language sql stable as $$
  select coalesce(nullif(btrim(split_part(coalesce(nullif(current_setting('request.headers', true), '')::json ->> 'x-forwarded-for', ''), ',', 1)), ''), 'desconocida')
$$;

create or replace function privado.ventana() returns timestamptz language sql stable as $$
  select to_timestamp(floor(extract(epoch from now()) / (c.ventana_min * 60)) * (c.ventana_min * 60)) from public.config c where c.id = 1
$$;

-- El identificador de dispositivo lo crea la página; se limpia y se acota.
create or replace function privado.dispositivo(v jsonb) returns text language sql immutable as $$
  select nullif(left(regexp_replace(privado.jtext(v), '[^A-Za-z0-9_-]', '', 'g'), 64), '')
$$;

create or replace function privado.frenado(p_disp text) returns text language sql stable as $$
  select case
    when p_disp is not null and coalesce((select fallos from public.intentos where clave = 'disp:' || p_disp and ventana = privado.ventana()), 0) >= c.limite_dispositivo then 'dispositivo'
    when coalesce((select fallos from public.intentos where clave = 'red:' || privado.red() and ventana = privado.ventana()), 0) >= c.limite_red then 'red'
  end
  from public.config c where c.id = 1
$$;

-- Suma un fallo al dispositivo y a la red. Devuelve los intentos que le quedan al dispositivo.
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
  delete from public.intentos where ventana < now() - interval '1 day';
  return greatest(0, v_lim - v_f);
end $$;

create or replace function privado.texto_intentos(r int) returns text language sql stable as $$
  select case when r is null then ''
              when r > 1 then ' Te quedan ' || r || ' intentos.'
              when r = 1 then ' Te queda 1 intento.'
              else ' Llegaste al límite: espera ' || (select ventana_min from public.config where id = 1) || ' minutos o escríbenos para ayudarte.' end
$$;


-- ═════════ Actividades en JSON ════════════════════════════════════════════

-- Con qué actividades no se puede combinar el mismo día (cruce sin permiso). Vacío con "una por día".
create or replace function privado.cruza_con(a public.actividades) returns jsonb language sql stable as $$
  select coalesce(jsonb_agg(x.id order by x.id), '[]'::jsonb)
  from public.actividades x, public.config c
  where c.id = 1 and c.mismo_dia and x.publicada and x.id <> a.id and not (x.tipo = 'VISITA' and a.tipo = 'VISITA')
    and x.fecha = a.fecha and not (a.fin + make_interval(mins => c.margen_min) <= x.inicio or x.fin + make_interval(mins => c.margen_min) <= a.inicio)
    and not exists (select 1 from public.cruces_permitidos cp where cp.a = least(a.id, x.id) and cp.b = greatest(a.id, x.id))
$$;

-- Pública (lista para elegir): sin enlace del grupo (R-16).
create or replace function privado.actividad_publica(a public.actividades) returns jsonb language sql stable as $$
  select jsonb_build_object('id', a.id, 'tipo', a.tipo, 'nombre', a.nombre, 'lugar', a.lugar,
    'fecha', privado.fecha_txt(a.fecha), 'inicio', privado.hora_txt(a.inicio), 'fin', privado.hora_txt(a.fin),
    'descripcion', a.descripcion, 'capacidad', a.cupo, 'inscritos', a.inscritos,
    'disponibles', greatest(0, a.cupo - a.inscritos), 'lleno', a.cupo - a.inscritos <= 0, 'cruzaCon', privado.cruza_con(a))
$$;

-- Comprobante: con el enlace solo para inscritos en esa actividad y entrega ENLACE (R-16, R-29).
create or replace function privado.resumen_actividad(a public.actividades) returns jsonb language sql stable as $$
  select jsonb_build_object('id', a.id, 'tipo', a.tipo, 'nombre', a.nombre, 'lugar', a.lugar,
    'fecha', privado.fecha_txt(a.fecha), 'inicio', privado.hora_txt(a.inicio), 'fin', privado.hora_txt(a.fin),
    'descripcion', a.descripcion, 'grupoModo', a.grupo_modo,
    'grupo', case when a.grupo_modo = 'ENLACE' then nullif(a.grupo_whatsapp, '') end)
$$;

-- Dos actividades se cruzan si son el mismo día y entre el fin de una y el inicio de la otra hay menos que el margen.
create or replace function privado.cruza(a public.actividades, b public.actividades, p_margen int) returns boolean language sql immutable as $$
  select a.fecha = b.fecha and not (a.fin + make_interval(mins => p_margen) <= b.inicio or b.fin + make_interval(mins => p_margen) <= a.inicio)
$$;

create or replace function privado.cruces_de(a public.actividades) returns jsonb language sql stable as $$
  select coalesce(jsonb_agg(x.id order by x.orden), '[]'::jsonb)
  from public.actividades x, public.config c
  where c.id = 1 and x.id <> a.id and not (x.tipo = 'VISITA' and a.tipo = 'VISITA') and privado.cruza(a, x, c.margen_min)
$$;

-- Panel: todos los campos.
create or replace function privado.actividad_completa(a public.actividades) returns jsonb language sql stable as $$
  select privado.actividad_publica(a) || jsonb_build_object('fila', a.orden, 'cupoInicial', a.cupo_inicial, 'publicada', a.publicada,
    'grupoModo', a.grupo_modo, 'grupo', a.grupo_whatsapp, 'cruces', privado.cruces_de(a))
$$;

create or replace function privado.actividades_publicas() returns jsonb language sql stable as $$
  select coalesce(jsonb_agg(privado.actividad_publica(a) order by a.fecha, a.inicio, a.orden), '[]'::jsonb)
  from public.actividades a where a.publicada
$$;

create or replace function privado.lista_cruces() returns jsonb language sql stable as $$
  select coalesce(jsonb_agg(jsonb_build_object('a', a.id, 'b', b.id, 'fecha', privado.fecha_txt(a.fecha),
           'permitido', exists (select 1 from public.cruces_permitidos cp where cp.a = a.id and cp.b = b.id)) order by a.fecha, a.id, b.id), '[]'::jsonb)
  from public.actividades a join public.actividades b on a.id < b.id, public.config c
  where c.id = 1 and not (a.tipo = 'VISITA' and b.tipo = 'VISITA') and privado.cruza(a, b, c.margen_min)
$$;


-- ═════════ Participante ═══════════════════════════════════════════════════

create or replace function privado.estado_publico() returns jsonb language sql stable as $$
  select jsonb_build_object('ok', true, 'tipo', 'estado', 'abierto', c.abierto, 'ronda', c.ronda, 'cierraEn', privado.cierra_en_seg(),
    'etapas', to_jsonb(c.etapas), 'etapasVisita', to_jsonb(c.etapas_visita), 'mismoDia', c.mismo_dia, 'margenMin', c.margen_min,
    'dosTalleres', c.dos_talleres, 'refresco', c.refresco, 'modo', c.modo, 'version', privado.version(), 'hora', privado.ahora())
  from public.config c where c.id = 1
$$;

create or replace function privado.etapas_de_doc(p_doc text) returns smallint[] language sql stable as $$
  select coalesce(array_agg(etapa order by etapa), '{}') from public.padron where documento = p_doc
$$;

-- Comprobante de una inscripción (registrado o duplicado).
create or replace function privado.comprobante(p_codigo text) returns jsonb language sql stable as $$
  select jsonb_build_object('codigo', i.codigo, 'doc', i.documento, 'etapa', i.etapa,
    'actividades', coalesce((select jsonb_agg(coalesce(privado.resumen_actividad(a),
                     jsonb_build_object('id', ia.actividad_id, 'nombre', ia.actividad_nombre, 'tipo', '', 'fecha', '', 'inicio', '', 'fin', '',
                                        'lugar', '', 'descripcion', '', 'grupoModo', 'ENLACE', 'grupo', null))
                     order by a.fecha, a.inicio)
              from public.inscripcion_actividades ia left join public.actividades a on a.id = ia.actividad_id
              where ia.codigo = i.codigo), '[]'::jsonb))
  from public.inscripciones i where i.codigo = p_codigo
$$;

create or replace function privado.duplicado(p_codigo text) returns jsonb language sql stable as $$
  select privado.fallo('duplicado', 'Este documento ya está inscrito (código ' || p_codigo || ').', privado.comprobante(p_codigo))
$$;

-- Pantalla 1. p_sin_dup: registrar vuelve a verificar sin mostrar el comprobante.
create or replace function privado.verificar(p_entrada jsonb, p_sin_dup boolean, p_disp text) returns jsonb
language plpgsql volatile as $$
declare
  c public.config;
  v_doc text;
  v_cod text;
  v_etapas smallint[];
  v_hab smallint[];
  v_etapa smallint;
  v_frenado text;
  r int;
begin
  select * into c from public.config where id = 1;
  v_frenado := privado.frenado(p_disp);
  if v_frenado is not null then
    return privado.fallo('demasiados_intentos', case when v_frenado = 'dispositivo'
      then 'Hiciste ' || c.limite_dispositivo || ' intentos con documentos que no encontramos. Espera ' || c.ventana_min || ' minutos o escríbenos para ayudarte.'
      else 'Hay demasiados intentos fallidos desde tu red. Espera ' || c.ventana_min || ' minutos o escríbenos.' end,
      jsonb_build_object('motivo', v_frenado, 'esperaMinutos', c.ventana_min));
  end if;
  if not privado.es_documento(privado.limpiar_doc(p_entrada)) then
    r := privado.sumar_fallo(p_disp);
    return privado.fallo('formato', 'Revisa el número: escribe tu DNI de 8 dígitos, o tu carnet de extranjería o pasaporte, sin espacios.' ||
      privado.texto_intentos(r), jsonb_build_object('intentosRestantes', r));
  end if;
  v_doc := privado.normalizar_doc(p_entrada);

  if not p_sin_dup then
    select codigo into v_cod from public.inscripciones where documento = v_doc and estado = 'CONFIRMADO';
    if found then
      if p_disp is not null then delete from public.intentos where clave = 'disp:' || p_disp; end if;
      return privado.duplicado(v_cod);
    end if;
  end if;
  if not c.abierto then
    return privado.fallo('cerrado', 'Las inscripciones están cerradas en este momento. Esta página se actualiza sola cuando abran.');
  end if;
  v_etapas := privado.etapas_de_doc(v_doc);
  if coalesce(array_length(v_etapas, 1), 0) = 0 then
    r := privado.sumar_fallo(p_disp);
    return privado.fallo('no_encontrado', 'No encontramos este documento en el padrón del congreso. Revisa el número o escríbenos.' ||
      privado.texto_intentos(r), jsonb_build_object('intentosRestantes', r));
  end if;
  if p_disp is not null then delete from public.intentos where clave = 'disp:' || p_disp; end if;
  select coalesce(array_agg(e order by e), '{}') into v_hab from unnest(v_etapas) e where e = any (c.etapas);
  if coalesce(array_length(v_hab, 1), 0) = 0 then
    return privado.fallo('etapa_no_habilitada', 'Tu entrada al congreso es de Etapa ' || v_etapas[1] || '. En este momento la inscripción está habilitada para ' ||
      privado.texto_etapas(c.etapas) || '. Espera el anuncio oficial.', jsonb_build_object('etapa', v_etapas[1]));
  end if;
  select e into v_etapa from unnest(v_hab) e where e = any (c.etapas_visita) order by e limit 1;
  if v_etapa is null then v_etapa := v_hab[1]; end if;
  return jsonb_build_object('ok', true, 'tipo', 'ok', 'doc', v_doc, 'etapa', v_etapa, 'puedeVisita', v_etapa = any (c.etapas_visita),
    'ronda', c.ronda,
    'mensaje', case when v_etapa = any (c.etapas_visita) then 'Documento verificado · Etapa ' || v_etapa || '.'
      else 'Documento verificado · Etapa ' || v_etapa || '. Por ahora tu etapa se inscribe en 2 talleres: las visitas están habilitadas para ' ||
           privado.texto_etapas(c.etapas_visita) || '.' end);
end $$;

-- Reglas de combinación (R-02, R-03), comunes a la página y al panel.
-- Devuelve {"ok":true,"ids":[…ordenados por día y hora],"visitas":n} o un fallo.
create or replace function privado.combinacion(p_ids jsonb, p_panel boolean) returns jsonb language plpgsql stable as $$
declare
  c public.config;
  v_ids text[];
  v_n int;
  sel public.actividades[];
  t record;
  va public.actividades;
  vb public.actividades;
begin
  select * into c from public.config where id = 1;
  if jsonb_typeof(p_ids) <> 'array' then
    return privado.fallo('combinacion_invalida', 'Elige 2 actividades: una visita y un taller, o dos talleres.', '{"motivo":"cantidad"}');
  end if;
  select coalesce(array_agg(distinct btrim(privado.jtext(x))), '{}'), count(*) into v_ids, v_n
  from jsonb_array_elements(p_ids) x where btrim(privado.jtext(x)) <> '';
  if coalesce(array_length(v_ids, 1), 0) <> c.total_por_persona or v_n <> c.total_por_persona then
    return privado.fallo('combinacion_invalida', 'Elige 2 actividades: una visita y un taller, o dos talleres.', '{"motivo":"cantidad"}');
  end if;
  select array_agg(x order by x.fecha, x.inicio, x.orden) into sel
  from public.actividades x where x.id = any (v_ids) and (x.publicada or p_panel);
  if coalesce(array_length(sel, 1), 0) <> c.total_por_persona then
    return privado.fallo('no_disponible', 'Una de las actividades elegidas ya no está disponible. Elige otra combinación.',
                         jsonb_build_object('actividades', privado.actividades_publicas()));
  end if;
  for t in select ta.codigo, ta.nombre, ta.max_por_persona, count(*) n
           from unnest(sel) s join public.tipos_actividad ta on ta.codigo = s.tipo group by ta.codigo, ta.nombre, ta.max_por_persona loop
    if t.n > t.max_por_persona then
      return case when t.codigo = 'VISITA'
        then privado.fallo('combinacion_invalida', 'Solo se puede elegir una visita técnica. La otra actividad debe ser un taller.', '{"motivo":"dos_visitas"}')
        else privado.fallo('combinacion_invalida', 'Elegiste demasiadas actividades del tipo ' || t.nombre || '.', '{"motivo":"tipo"}') end;
    end if;
  end loop;
  va := sel[1]; vb := sel[2];
  if va.fecha = vb.fecha then
    if not c.mismo_dia then
      return privado.fallo('combinacion_invalida', 'Las 2 actividades deben ser en días distintos: una por día.', '{"motivo":"mismo_dia"}');
    end if;
    if privado.cruza(va, vb, c.margen_min)
       and not exists (select 1 from public.cruces_permitidos cp where cp.a = least(va.id, vb.id) and cp.b = greatest(va.id, vb.id)) then
      return privado.fallo('combinacion_invalida', '"' || va.nombre || '" (' || privado.hora_txt(va.inicio) || '–' || privado.hora_txt(va.fin) || ') y "' || vb.nombre ||
        '" (' || privado.hora_txt(vb.inicio) || '–' || privado.hora_txt(vb.fin) || ') se cruzan: entre una y otra debe haber al menos ' || c.margen_min || ' minutos.',
        '{"motivo":"cruce"}');
    end if;
  end if;
  return jsonb_build_object('ok', true, 'ids', to_jsonb(array[va.id, vb.id]),
    'visitas', (va.tipo = 'VISITA')::int + (vb.tipo = 'VISITA')::int);
end $$;

create or replace function privado.nuevo_codigo() returns text language plpgsql volatile as $$
declare
  letras constant text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  v text;
begin
  loop
    v := 'CIIC-';
    for i in 1..5 loop v := v || substr(letras, 1 + floor(random() * 32)::int, 1); end loop;
    exit when not exists (select 1 from public.inscripciones where codigo = v);
  end loop;
  return v;
end $$;

-- Guarda una inscripción ya validada (las filas de sus actividades deben estar bloqueadas).
create or replace function privado.guardar(p_doc text, p_nombre text, p_correo text, p_etapa smallint, p_ids text[], p_tel jsonb,
                                           p_origen text, p_ronda int, p_user uuid) returns text language plpgsql volatile as $$
declare v_codigo text := privado.nuevo_codigo();
begin
  insert into public.inscripciones (codigo, documento, nombre, correo, etapa, celular, pais, acepta_whatsapp, origen, ronda, registrado_por)
  values (v_codigo, p_doc, p_nombre, p_correo, p_etapa, p_tel ->> 'numero', p_tel ->> 'pais', true, p_origen, p_ronda, p_user);
  insert into public.inscripcion_actividades (codigo, actividad_id, actividad_nombre)
  select v_codigo, a.id, a.nombre from public.actividades a where a.id = any (p_ids);
  update public.actividades set inscritos = inscritos + 1 where id = any (p_ids);
  return v_codigo;
end $$;

-- Pantalla 2 → 3.
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

  -- Bloqueo compartido de la configuración: un cierre espera a que esta inscripción termine (R-09).
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

    -- Bloquea solo las 2 actividades elegidas, siempre en el mismo orden.
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
      if v_restr = 'un_confirmado_por_documento' then
        select codigo into v_cod from public.inscripciones where documento = v ->> 'doc' and estado = 'CONFIRMADO';
        return privado.duplicado(v_cod);
      end if;
      return privado.fallo('ocupado', 'Estás en la fila: hay muchas personas inscribiéndose. Seguimos intentando por ti.');
    when check_violation then
      return privado.fallo('lleno', 'Una de tus actividades se acaba de llenar. Elige otra combinación, por favor.',
                           jsonb_build_object('actividades', privado.actividades_publicas()));
  end;
  return jsonb_build_object('ok', true, 'tipo', 'registrado', 'mensaje', 'Inscripción confirmada. Tu código es ' || v_cod || '.') || privado.comprobante(v_cod);
end $$;


-- ═════════ Sesión del panel y roles ═══════════════════════════════════════

-- Claves del tester: se guarda su huella SHA-256.
create or replace function privado.huella(k text) returns text language sql immutable as $$
  select encode(extensions.digest(convert_to(k, 'UTF8'), 'sha256'), 'hex')
$$;
create or replace function privado.clave_ok(p_nombre text, p_key text) returns boolean language sql stable as $$
  select exists (select 1 from privado.claves where nombre = p_nombre and huella = privado.huella(coalesce(p_key, '')))
$$;
create or replace function privado.crear_clave_admin() returns text language plpgsql volatile as $$
declare k text := translate(encode(extensions.gen_random_bytes(24), 'base64'), '+/=', 'xyz');
begin
  insert into privado.claves (nombre, huella) values ('ADMIN_KEY', privado.huella(k)) on conflict (nombre) do update set huella = excluded.huella;
  return k;
end $$;
create or replace function privado.borrar_clave_admin() returns text language sql volatile as $$
  delete from privado.claves where nombre = 'ADMIN_KEY'; select 'Funciones del tester apagadas.'::text
$$;

-- Quién llama al panel. Devuelve {"uid","nombre","rol","tester"} o un fallo.
create or replace function privado.sesion(p jsonb) returns jsonb language plpgsql volatile as $$
declare
  claims jsonb := nullif(current_setting('request.jwt.claims', true), '')::jsonb;
  v_uid uuid;
  o public.organizadores;
  k text := privado.jtext(p -> 'key');
  v_rol text;
begin
  if claims ->> 'role' = 'authenticated' and claims ? 'sub' then
    v_uid := (claims ->> 'sub')::uuid;
    if coalesce(claims ->> 'aal', 'aal1') <> 'aal2' then
      return privado.fallo('falta_codigo', 'Ingresa el código de 6 dígitos de tu app de verificación para continuar.');
    end if;
    select * into o from public.organizadores where user_id = v_uid;
    if not found or o.rol is null then
      return privado.fallo('sin_permiso', 'Tu cuenta aún no tiene rol: pide al propietario que te lo asigne en Equipo.');
    end if;
    if not o.activo then return privado.fallo('sin_permiso', 'Tu cuenta está desactivada. Habla con el propietario.'); end if;
    return jsonb_build_object('uid', v_uid, 'nombre', coalesce(nullif(o.nombre, ''), 'Sin nombre'), 'rol', o.rol, 'tester', false);
  end if;
  if k <> '' then
    if privado.clave_ok('ADMIN_KEY', k) then
      if (select modo from public.config where id = 1) <> 'PRUEBA' then
        return privado.fallo('modo_produccion', 'La base está en modo PRODUCCION: la clave de prueba ya no funciona.');
      end if;
      v_rol := coalesce(nullif(privado.jtext(p -> 'comoRol'), ''), 'propietario');
      if v_rol not in ('propietario', 'admin', 'operador') then v_rol := 'propietario'; end if;
      return jsonb_build_object('uid', null, 'nombre', 'Tester', 'rol', v_rol, 'tester', true);
    end if;
    perform pg_sleep(1.5);                     -- frena a quien intente adivinar la clave
    return privado.fallo('no_autorizado', 'Clave incorrecta.');
  end if;
  return privado.fallo('sin_sesion', 'Inicia sesión para usar el panel.');
end $$;

create or replace function privado.rango(r text) returns int language sql immutable as $$
  select case r when 'propietario' then 3 when 'admin' then 2 when 'operador' then 1 else 0 end
$$;

-- Rol mínimo de cada acción del panel.
create or replace function privado.rol_minimo(accion text) returns int language sql immutable as $$
  select case
    when accion in ('panel_equipo', 'panel_equipo_rol', 'panel_equipo_activo') then 3
    when accion in ('panel_inscribir', 'panel_cambiar', 'panel_anular', 'panel_padron_agregar', 'panel_padron_quitar', 'panel_crear',
                    'panel_editar', 'panel_quitar', 'panel_horarios', 'panel_cruce', 'panel_registros', 'panel_sincronizar') then 2
    else 1 end
$$;

create or replace function privado.requiere_cierre() returns jsonb language sql immutable as $$
  select privado.fallo('requiere_cierre', 'Este cambio quita opciones a quien está eligiendo. Cierra las inscripciones, haz el cambio y vuelve a abrir.')
$$;

create or replace function privado.abierto() returns boolean language sql stable as $$ select abierto from public.config where id = 1 $$;
create or replace function privado.quien(s jsonb) returns text language sql immutable as $$ select (s ->> 'nombre') || ' · ' || (s ->> 'rol') $$;


-- ═════════ Panel 1 · Operación ════════════════════════════════════════════

create or replace function privado.config_json() returns jsonb language sql stable as $$
  select jsonb_build_object('abierto', c.abierto, 'ronda', c.ronda, 'cierraEn', privado.cierra_en_seg(), 'etapas', to_jsonb(c.etapas),
    'etapasVisita', to_jsonb(c.etapas_visita), 'dosTalleres', c.dos_talleres, 'mismoDia', c.mismo_dia, 'margenMin', c.margen_min,
    'pasoCupo', c.paso_cupo, 'refresco', c.refresco, 'modo', c.modo,
    'limiteDispositivo', c.limite_dispositivo, 'limiteRed', c.limite_red, 'ventanaMin', c.ventana_min)
  from public.config c where c.id = 1
$$;

create or replace function privado.panel_resumen(s jsonb) returns jsonb language sql stable as $$
  select jsonb_build_object('ok', true, 'tipo', 'panel', 'version', privado.version(), 'hora', privado.ahora(),
    'sesion', jsonb_build_object('nombre', s ->> 'nombre', 'rol', s ->> 'rol', 'tester', (s ->> 'tester')::boolean),
    'config', privado.config_json(),
    'totales', (select jsonb_build_object(
        'inscritos', count(*) filter (where estado = 'CONFIRMADO'),
        'anulados', count(*) filter (where estado = 'ANULADO'),
        'porEtapa', jsonb_build_object('1', count(*) filter (where estado = 'CONFIRMADO' and etapa = 1),
                                       '2', count(*) filter (where estado = 'CONFIRMADO' and etapa = 2),
                                       '3', count(*) filter (where estado = 'CONFIRMADO' and etapa = 3)),
        'porOrigen', jsonb_build_object('WEB', count(*) filter (where estado = 'CONFIRMADO' and origen = 'WEB'),
                                        'PANEL', count(*) filter (where estado = 'CONFIRMADO' and origen = 'PANEL')),
        'padron', (select jsonb_build_object('1', count(*) filter (where etapa = 1), '2', count(*) filter (where etapa = 2), '3', count(*) filter (where etapa = 3)) from public.padron),
        'visitas', (select jsonb_build_object('ocupados', coalesce(sum(inscritos), 0), 'cupo', coalesce(sum(cupo), 0)) from public.actividades where tipo = 'VISITA' and publicada),
        'fallos10min', (select coalesce(sum(fallos), 0) from public.intentos where clave like 'disp:%' and ventana = privado.ventana()),
        'frenados', (select count(*) from public.intentos t, public.config c where c.id = 1 and t.ventana = privado.ventana()
                     and ((t.clave like 'disp:%' and t.fallos >= c.limite_dispositivo) or (t.clave like 'red:%' and t.fallos >= c.limite_red))))
      from public.inscripciones),
    'actividades', (select coalesce(jsonb_agg(privado.actividad_completa(a) order by a.fecha, a.inicio, a.orden), '[]'::jsonb) from public.actividades a),
    'cruces', privado.lista_cruces(),
    'repetidos', (select coalesce(jsonb_agg(jsonb_build_object('celular', celular, 'personas', personas) order by primero), '[]'::jsonb)
      from (select celular, min(orden) primero, jsonb_agg(jsonb_build_object('codigo', codigo, 'doc', documento, 'nombre', nombre) order by orden) personas
            from public.inscripciones where estado = 'CONFIRMADO' group by celular having count(*) > 1) r),
    'ultimos', (select coalesce(jsonb_agg(u.j order by u.orden desc), '[]'::jsonb) from (
       select i.orden, jsonb_build_object('fecha', to_char(i.creado_en at time zone 'America/Lima', 'YYYY-MM-DD HH24:MI:SS'),
         'codigo', i.codigo, 'doc', i.documento, 'nombre', i.nombre, 'etapa', i.etapa, 'origen', i.origen,
         'actividades', (select jsonb_agg(ia.actividad_id order by ia.actividad_id) from public.inscripcion_actividades ia where ia.codigo = i.codigo)) j
       from public.inscripciones i where i.estado = 'CONFIRMADO' order by i.orden desc limit 15) u))
$$;

create or replace function privado.panel_config(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  c public.config;
  quiero smallint[];
  n int;
  cambios text[] := '{}';
  uid uuid := (s ->> 'uid')::uuid;
begin
  select * into c from public.config where id = 1 for update;     -- espera a las inscripciones en curso
  -- Cerrar ahora (R-09)
  if (b -> 'abierto') = 'false'::jsonb and c.abierto then
    if (b -> 'confirmar') is distinct from 'true'::jsonb then
      return privado.fallo('advertencia', 'Nadie nuevo podrá pasar de la pantalla 1. Quien esté eligiendo y no haya confirmado vuelve al inicio sin inscribirse. Se habilitan los cambios que quitan opciones.',
                           '{"accion":"cerrar"}');
    end if;
    update public.config set abierto = false, ronda = ronda + 1, cierre_en = null where id = 1;
    perform privado.bitacora(uid, privado.quien(s), 'Cierre y depuración', 'ronda ' || c.ronda || ' → ' || (c.ronda + 1));
    return jsonb_build_object('ok', true, 'tipo', 'panel', 'config', privado.config_json());
  end if;
  if (b -> 'abierto') = 'true'::jsonb and not c.abierto then
    update public.config set abierto = true where id = 1;
    perform privado.bitacora(uid, privado.quien(s), 'Apertura', 'ronda ' || c.ronda);
    return jsonb_build_object('ok', true, 'tipo', 'panel', 'config', privado.config_json());
  end if;
  -- Avisar y cerrar (R-27). avisarCierreSeg solo para el tester.
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

  -- Quitar opciones exige cerrar (R-10).
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
  if privado.tiene(b, 'limiteDispositivo') or privado.tiene(b, 'limiteRed') then
    if privado.rango(s ->> 'rol') < 3 then return privado.fallo('sin_permiso', 'Solo el propietario cambia los límites de intentos.'); end if;
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
  end if;
  if array_length(cambios, 1) > 0 then perform privado.bitacora(uid, privado.quien(s), 'Configuración', array_to_string(cambios, ' · ')); end if;
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
  if privado.tiene(b, 'delta') then v_cupo := a.cupo + privado.entero(b -> 'delta'); end if;
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
  if array_length(cambios, 1) > 0 then perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Actividad ' || v_id, array_to_string(cambios, ' · ')); end if;
  select * into a from public.actividades where id = v_id;
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'actividad', privado.actividad_completa(a));
end $$;

create or replace function privado.registro_json(i public.inscripciones) returns jsonb language sql stable as $$
  select jsonb_build_object('fecha', to_char(i.creado_en at time zone 'America/Lima', 'YYYY-MM-DD HH24:MI:SS'), 'codigo', i.codigo,
    'doc', i.documento, 'nombre', i.nombre, 'correo', i.correo, 'celular', i.celular, 'etapa', i.etapa, 'estado', i.estado,
    'origen', i.origen, 'ronda', i.ronda,
    'actividades', (select coalesce(jsonb_agg(jsonb_build_object('id', ia.actividad_id, 'nombre', ia.actividad_nombre) order by ia.actividad_id), '[]'::jsonb)
                    from public.inscripcion_actividades ia where ia.codigo = i.codigo))
$$;

create or replace function privado.panel_buscar(b jsonb) returns jsonb language plpgsql stable as $$
declare
  q text := btrim(coalesce(nullif(privado.jtext(b -> 'q'), ''), privado.jtext(b -> 'doc')));
  v_doc text := privado.normalizar_doc(to_jsonb(q));
  dig text := regexp_replace(q, '\D', '', 'g');
  por_cel boolean := length(dig) >= 7 and q !~ '[A-Za-z]' and (left(q, 1) = '+' or length(dig) >= 9);
begin
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'doc', v_doc, 'etapas', to_jsonb(privado.etapas_de_doc(v_doc)), 'porCelular', por_cel,
    'registros', (select coalesce(jsonb_agg(privado.registro_json(i) order by i.orden), '[]'::jsonb) from public.inscripciones i
                  where i.documento = v_doc or (por_cel and right(regexp_replace(i.celular, '\D', '', 'g'), length(dig)) = dig)));
end $$;

create or replace function privado.panel_anular(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_cod text := upper(btrim(privado.jtext(b -> 'codigo')));
  i public.inscripciones;
begin
  select * into i from public.inscripciones where codigo = v_cod and estado = 'CONFIRMADO' for update;
  if not found then return privado.fallo('no_encontrado', 'No hay una inscripción confirmada con el código ' || v_cod || '.'); end if;
  perform 1 from public.actividades where id in (select actividad_id from public.inscripcion_actividades where codigo = v_cod) order by id for update;
  update public.inscripciones set estado = 'ANULADO', modificado_por = (s ->> 'uid')::uuid, modificado_en = now() where codigo = v_cod;
  update public.actividades set inscritos = greatest(0, inscritos - 1) where id in (select actividad_id from public.inscripcion_actividades where codigo = v_cod);
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Anulación',
    v_cod || ' · ' || i.documento || ' · libera ' || (select string_agg(actividad_id, ' y ' order by actividad_id) from public.inscripcion_actividades where codigo = v_cod));
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'codigo', v_cod);
end $$;

-- Si alguna actividad nueva está llena: sin ampliarCupo → advertencia; con ampliarCupo → cupo = inscritos + 1 (R-20).
create or replace function privado.revisar_cupos(p_ids text[], p_ya_tiene text[], b jsonb, s jsonb, p_motivo text) returns jsonb language plpgsql volatile as $$
declare
  llenas jsonb;
  a public.actividades;
begin
  select jsonb_agg(jsonb_build_object('id', x.id, 'txt', '"' || x.nombre || '" está llena (' || x.inscritos || '/' || x.cupo || ')') order by x.id) into llenas
  from public.actividades x where x.id = any (p_ids) and not (x.id = any (p_ya_tiene)) and x.inscritos >= x.cupo;
  if llenas is null then return '[]'::jsonb; end if;
  if (b -> 'ampliarCupo') is distinct from 'true'::jsonb then
    return privado.fallo('advertencia', (select string_agg(e ->> 'txt', ' y ') from jsonb_array_elements(llenas) e) || '. Continuar ampliará su cupo en 1.',
      jsonb_build_object('accion', 'ampliar_cupo', 'ids', (select jsonb_agg(e -> 'id') from jsonb_array_elements(llenas) e)));
  end if;
  for a in select * from public.actividades x where x.id in (select e ->> 'id' from jsonb_array_elements(llenas) e) loop
    update public.actividades set cupo = a.inscritos + 1 where id = a.id;
    perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Actividad ' || a.id, 'cupo ' || a.cupo || ' → ' || (a.inscritos + 1) || ' (' || p_motivo || ')');
  end loop;
  return (select jsonb_agg(e -> 'id') from jsonb_array_elements(llenas) e);
end $$;

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
  if coalesce(array_length(v_etapas, 1), 0) = 0 then return privado.fallo('no_encontrado', 'Este documento no está en el padrón. Agrégalo primero en el Panel 2.'); end if;
  select codigo into v_cod from public.inscripciones where documento = v_doc and estado = 'CONFIRMADO';
  if found then return privado.duplicado(v_cod); end if;
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
    return privado.duplicado(v_cod);
  end;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Inscripción desde el panel', v_cod || ' · ' || v_doc || ' · ' || array_to_string(v_ids, ' + '));
  return jsonb_build_object('ok', true, 'tipo', 'registrado', 'origen', 'PANEL', 'ampliadas', amp,
    'mensaje', 'Inscrito con el código ' || v_cod || '.') || privado.comprobante(v_cod);
end $$;

-- Soporte: cambia las actividades en una sola transacción y conserva el código (R-21).
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
  update public.actividades set inscritos = inscritos - 1 where id = any (v_viejas) and not (id = any (v_nuevas));
  update public.actividades set inscritos = inscritos + 1 where id = any (v_nuevas) and not (id = any (v_viejas));
  delete from public.inscripcion_actividades where codigo = v_cod and not (actividad_id = any (v_nuevas));
  insert into public.inscripcion_actividades (codigo, actividad_id, actividad_nombre)
  select v_cod, a.id, a.nombre from public.actividades a where a.id = any (v_nuevas) and not (a.id = any (v_viejas));
  update public.inscripciones set modificado_por = (s ->> 'uid')::uuid, modificado_en = now() where codigo = v_cod;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Cambio de inscripción',
    v_cod || ' · ' || array_to_string(v_viejas, ' + ') || ' → ' || array_to_string(v_nuevas, ' + '));
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'codigo', v_cod, 'antes', to_jsonb(v_viejas), 'ahora', to_jsonb(v_nuevas), 'ampliadas', amp);
end $$;


-- ═════════ Panel 2 · Participantes ════════════════════════════════════════

create or replace function privado.panel_participantes(b jsonb) returns jsonb language plpgsql stable as $$
declare
  v_etapa int := privado.entero(b -> 'etapa');
  v_estado text := nullif(privado.jtext(b -> 'estado'), '');
  q text := upper(btrim(privado.jtext(b -> 'q')));
  v_pag int := greatest(coalesce(privado.entero(b -> 'pagina'), 1), 1);
  r jsonb;
begin
  with base as (
    select p.documento, p.etapa, p.nombre, p.origen, p.orden, ul.codigo, coalesce(ul.estado, 'SIN_INSCRIBIR') estado, ul.acts
    from public.padron p
    left join lateral (select i.codigo, i.estado,
                              (select jsonb_agg(ia.actividad_id order by ia.actividad_id) from public.inscripcion_actividades ia where ia.codigo = i.codigo) acts
                       from public.inscripciones i where i.documento = p.documento order by (i.estado = 'CONFIRMADO') desc, i.orden desc limit 1) ul on true
    where (v_etapa is null or p.etapa = v_etapa)
      and (q = '' or p.documento like '%' || privado.normalizar_doc(to_jsonb(q)) || '%' or upper(p.nombre) like '%' || q || '%')),
  filtrado as (select * from base where v_estado is null or estado = v_estado)
  select jsonb_build_object('ok', true, 'tipo', 'panel', 'total', (select count(*) from filtrado), 'pagina', v_pag, 'porPagina', 50,
    'resumen', (select jsonb_build_object('padron', count(*), 'inscritos', count(*) filter (where estado = 'CONFIRMADO'),
                 'sinInscribir', count(*) filter (where estado = 'SIN_INSCRIBIR'), 'agregados', count(*) filter (where origen = 'PANEL')) from base),
    'filas', coalesce((select jsonb_agg(jsonb_build_object('doc', f.documento, 'etapa', f.etapa, 'nombre', f.nombre, 'origen', f.origen,
                        'estado', f.estado, 'codigo', f.codigo, 'actividades', coalesce(f.acts, '[]'::jsonb)) order by f.orden)
                       from (select * from filtrado order by orden offset (v_pag - 1) * 50 limit 50) f), '[]'::jsonb)) into r;
  return r;
end $$;

create or replace function privado.panel_padron_agregar(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_doc text := privado.normalizar_doc(b -> 'documento');
  v_etapa int := privado.entero(b -> 'etapa');
  v_nombre text := privado.texto_limpio(b -> 'nombre', 80);
  otras smallint[];
begin
  if not privado.es_documento(v_doc) then return privado.fallo('formato', 'Revisa el documento: 6 a 12 letras y números.'); end if;
  if v_etapa is null or v_etapa not in (1, 2, 3) then return privado.fallo('valor_invalido', 'Elige la etapa de venta: 1, 2 o 3.'); end if;
  if length(v_nombre) < 3 then return privado.fallo('datos_invalidos', 'Escribe el nombre completo.'); end if;
  if exists (select 1 from public.padron where documento = v_doc and etapa = v_etapa) then
    return privado.fallo('ya_existe', 'El documento ' || v_doc || ' ya está en el padrón de la Etapa ' || v_etapa || '.');
  end if;
  otras := privado.etapas_de_doc(v_doc);
  if coalesce(array_length(otras, 1), 0) > 0 and (b -> 'confirmar') is distinct from 'true'::jsonb then
    return privado.fallo('advertencia', 'El documento ' || v_doc || ' ya está en la Etapa ' || array_to_string(otras, ' y ') ||
      '. ¿Agregarlo también a la Etapa ' || v_etapa || '?', '{"accion":"otra_etapa"}');
  end if;
  insert into public.padron (documento, etapa, nombre, origen, creado_por) values (v_doc, v_etapa, v_nombre, 'PANEL', (s ->> 'uid')::uuid);
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Padrón', 'agregado ' || v_doc || ' a la Etapa ' || v_etapa);
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'doc', v_doc, 'etapa', v_etapa);
end $$;

create or replace function privado.panel_padron_quitar(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_doc text := privado.normalizar_doc(b -> 'documento');
  v_etapa int := privado.entero(b -> 'etapa');
begin
  if privado.abierto() then return privado.requiere_cierre(); end if;
  if exists (select 1 from public.inscripciones where documento = v_doc and estado = 'CONFIRMADO') then
    return privado.fallo('tiene_inscripcion', 'Esta persona tiene una inscripción confirmada: anúlala primero.');
  end if;
  delete from public.padron where documento = v_doc and etapa = v_etapa;
  if not found then return privado.fallo('no_encontrado', 'No está en el padrón de esa etapa.'); end if;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Padrón', 'quitado ' || v_doc || ' de la Etapa ' || v_etapa);
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'doc', v_doc);
end $$;


-- ═════════ Panel 3 · Actividades, horarios y grupos ═══════════════════════

-- Valida datos de una actividad. Devuelve {"error":…} o {"datos":…}.
create or replace function privado.datos_actividad(b jsonb, base jsonb) returns jsonb language plpgsql stable as $$
declare
  v_tipo text := case when b ? 'tipo' then upper(btrim(privado.jtext(b -> 'tipo'))) else base ->> 'tipo' end;
  v_nombre text := case when b ? 'nombre' then privado.texto_limpio(b -> 'nombre', 120) else base ->> 'nombre' end;
  v_lugar text := case when b ? 'lugar' then privado.texto_limpio(b -> 'lugar', 120) else base ->> 'lugar' end;
  v_fecha text := case when b ? 'fecha' then btrim(privado.jtext(b -> 'fecha')) else base ->> 'fecha' end;
  v_inicio text := case when b ? 'inicio' then btrim(privado.jtext(b -> 'inicio')) else base ->> 'inicio' end;
  v_fin text := case when b ? 'fin' then btrim(privado.jtext(b -> 'fin')) else base ->> 'fin' end;
  v_desc text := case when b ? 'descripcion' then privado.texto_limpio(b -> 'descripcion', 400) else coalesce(base ->> 'descripcion', '') end;
  v_modo text := case when b ? 'grupoModo' then upper(btrim(privado.jtext(b -> 'grupoModo'))) else coalesce(base ->> 'grupoModo', 'ENLACE') end;
  v_grupo text := case when b ? 'grupo' then btrim(privado.jtext(b -> 'grupo')) else coalesce(base ->> 'grupo', '') end;
  d date;
  mi int; mf int; m text[];
begin
  if not exists (select 1 from public.tipos_actividad where codigo = v_tipo) then return jsonb_build_object('error', 'Tipo de actividad desconocido.'); end if;
  if length(coalesce(v_nombre, '')) < 3 then return jsonb_build_object('error', 'Escribe el nombre de la actividad.'); end if;
  if coalesce(v_fecha, '') !~ '^\d{1,2}/\d{1,2}/\d{4}$' then return jsonb_build_object('error', 'La fecha debe escribirse como dd/mm/aaaa.'); end if;
  begin
    d := to_date(v_fecha, 'DD/MM/YYYY');
    if privado.fecha_txt(d) <> lpad(split_part(v_fecha, '/', 1), 2, '0') || '/' || lpad(split_part(v_fecha, '/', 2), 2, '0') || '/' || split_part(v_fecha, '/', 3) then
      raise exception 'fecha';
    end if;
  exception when others then return jsonb_build_object('error', 'La fecha debe escribirse como dd/mm/aaaa.');
  end;
  m := regexp_match(coalesce(v_inicio, ''), '^(\d{1,2}):(\d{2})$');
  mi := case when m is not null and m[1]::int < 24 and m[2]::int < 60 then m[1]::int * 60 + m[2]::int else -1 end;
  m := regexp_match(coalesce(v_fin, ''), '^(\d{1,2}):(\d{2})$');
  mf := case when m is not null and m[1]::int < 24 and m[2]::int < 60 then m[1]::int * 60 + m[2]::int else -1 end;
  if mi < 0 or mf < 0 then return jsonb_build_object('error', 'Las horas deben escribirse como hh:mm (por ejemplo 08:30).'); end if;
  if mf <= mi then return jsonb_build_object('error', 'La hora de fin debe ser posterior a la de inicio.'); end if;
  if v_modo not in ('ENLACE', 'MANUAL') then return jsonb_build_object('error', 'Entrega del grupo: ENLACE o MANUAL.'); end if;
  if v_grupo <> '' and (left(v_grupo, 26) <> 'https://chat.whatsapp.com/' or length(v_grupo) < 32 or v_grupo ~ '\s') then
    return jsonb_build_object('error', 'El enlace del grupo debe empezar con https://chat.whatsapp.com/ (cópialo desde WhatsApp → Invitar al grupo mediante enlace).', 'tipo', 'enlace_invalido');
  end if;
  return jsonb_build_object('datos', jsonb_build_object('tipo', v_tipo, 'nombre', v_nombre, 'lugar', coalesce(v_lugar, ''),
    'fecha', privado.fecha_txt(d), 'inicio', lpad(v_inicio, 5, '0'), 'fin', lpad(v_fin, 5, '0'), 'descripcion', v_desc, 'grupoModo', v_modo, 'grupo', v_grupo));
end $$;

create or replace function privado.panel_crear(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  dv jsonb := privado.datos_actividad(b, '{"tipo":"TALLER","nombre":"","lugar":"","fecha":"","inicio":"","fin":""}');
  d jsonb;
  v_cupo int := privado.entero(b -> 'cupo');
  v_pref text;
  v_id text;
  a public.actividades;
begin
  if dv ? 'error' then return privado.fallo(coalesce(dv ->> 'tipo', 'datos_invalidos'), dv ->> 'error'); end if;
  if v_cupo is null or v_cupo < 1 or v_cupo > 1000 then return privado.fallo('cupo_invalido', 'El cupo inicial debe estar entre 1 y 1000.'); end if;
  d := dv -> 'datos';
  v_pref := case d ->> 'tipo' when 'VISITA' then 'VIS' when 'TALLER' then 'TAL' else left(d ->> 'tipo', 3) end;
  perform pg_advisory_xact_lock(hashtext('ciic_crear_actividad'));
  select v_pref || lpad((coalesce(max(substring(x.id from '^' || v_pref || '(\d+)$')::int), 0) + 1)::text, 2, '0') into v_id
  from public.actividades x where x.id ~ ('^' || v_pref || '\d+$');
  insert into public.actividades (id, tipo, nombre, lugar, fecha, inicio, fin, cupo, cupo_inicial, publicada, descripcion, grupo_modo, grupo_whatsapp, creado_por)
  values (v_id, d ->> 'tipo', d ->> 'nombre', d ->> 'lugar', to_date(d ->> 'fecha', 'DD/MM/YYYY'), (d ->> 'inicio')::time, (d ->> 'fin')::time,
          v_cupo, v_cupo, false, d ->> 'descripcion', d ->> 'grupoModo', d ->> 'grupo', (s ->> 'uid')::uuid)
  returning * into a;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Actividad ' || v_id,
    'creada (oculta): ' || (d ->> 'tipo') || ' · ' || (d ->> 'nombre') || ' · ' || (d ->> 'fecha') || ' ' || (d ->> 'inicio') || '–' || (d ->> 'fin') || ' · cupo ' || v_cupo);
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'actividad', privado.actividad_completa(a), 'cruces', privado.cruces_de(a));
end $$;

create or replace function privado.panel_editar(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_id text := btrim(privado.jtext(b -> 'id'));
  a public.actividades;
  base jsonb;
  dv jsonb;
  d jsonb;
  toca boolean;
  cambios text[] := '{}';
  k text;
begin
  select * into a from public.actividades where id = v_id for update;
  if not found then return privado.fallo('actividad_invalida', 'No existe la actividad ' || v_id || '.'); end if;
  base := jsonb_build_object('tipo', a.tipo, 'nombre', a.nombre, 'lugar', a.lugar, 'fecha', privado.fecha_txt(a.fecha), 'inicio', privado.hora_txt(a.inicio),
                             'fin', privado.hora_txt(a.fin), 'descripcion', a.descripcion, 'grupoModo', a.grupo_modo, 'grupo', a.grupo_whatsapp);
  dv := privado.datos_actividad(b, base);
  if dv ? 'error' then return privado.fallo(coalesce(dv ->> 'tipo', 'datos_invalidos'), dv ->> 'error'); end if;
  d := dv -> 'datos';
  toca := d ->> 'tipo' <> base ->> 'tipo' or d ->> 'fecha' <> base ->> 'fecha' or d ->> 'inicio' <> base ->> 'inicio' or d ->> 'fin' <> base ->> 'fin';
  if toca and a.inscritos > 0 then
    return privado.fallo('tiene_inscritos', '"' || a.nombre || '" ya tiene ' || privado.n_inscritos(a.inscritos) || ': su tipo, fecha y horario quedan fijos. ' ||
      'Si de verdad cambia, crea otra actividad y mueve a cada persona con "Cambiar inscripción".');
  end if;
  if toca and a.publicada and privado.abierto() then return privado.requiere_cierre(); end if;
  update public.actividades set tipo = d ->> 'tipo', nombre = d ->> 'nombre', lugar = d ->> 'lugar', fecha = to_date(d ->> 'fecha', 'DD/MM/YYYY'),
         inicio = (d ->> 'inicio')::time, fin = (d ->> 'fin')::time, descripcion = d ->> 'descripcion', grupo_modo = d ->> 'grupoModo',
         grupo_whatsapp = d ->> 'grupo'
   where id = v_id returning * into a;
  update public.inscripcion_actividades set actividad_nombre = a.nombre where actividad_id = v_id and actividad_nombre <> a.nombre;
  foreach k in array array['tipo', 'nombre', 'lugar', 'fecha', 'inicio', 'fin', 'descripcion', 'grupoModo', 'grupo'] loop
    if d ->> k is distinct from base ->> k then cambios := cambios || k; end if;
  end loop;
  if array_length(cambios, 1) > 0 then perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Actividad ' || v_id, 'editado: ' || array_to_string(cambios, ', ')); end if;
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'actividad', privado.actividad_completa(a), 'cruces', privado.cruces_de(a));
end $$;

create or replace function privado.panel_quitar(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_id text := btrim(privado.jtext(b -> 'id'));
  a public.actividades;
begin
  select * into a from public.actividades where id = v_id for update;
  if not found then return privado.fallo('actividad_invalida', 'No existe la actividad ' || v_id || '.'); end if;
  if a.inscritos > 0 then return privado.fallo('tiene_inscritos', '"' || a.nombre || '" tiene ' || privado.n_inscritos(a.inscritos) || ': no se puede quitar.'); end if;
  if a.publicada then return privado.fallo('esta_visible', 'Ocúltala primero en el Panel 1 (requiere cerrar inscripciones).'); end if;
  delete from public.actividades where id = v_id;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Actividad ' || v_id, 'quitada: ' || a.tipo || ' · ' || a.nombre);
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'id', v_id);
end $$;

create or replace function privado.panel_horarios(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  c public.config;
  m int;
begin
  select * into c from public.config where id = 1 for update;
  if (b -> 'mismoDia') = 'false'::jsonb and c.mismo_dia and c.abierto then return privado.requiere_cierre(); end if;
  if privado.tiene(b, 'margenMin') then
    m := privado.entero(b -> 'margenMin');
    if m is null or m < 0 or m > 240 then return privado.fallo('valor_invalido', 'El margen debe estar entre 0 y 240 minutos.'); end if;
    if m > c.margen_min and c.abierto then return privado.requiere_cierre(); end if;
    update public.config set margen_min = m where id = 1;
  end if;
  if jsonb_typeof(b -> 'mismoDia') = 'boolean' then update public.config set mismo_dia = (b ->> 'mismoDia')::boolean where id = 1; end if;
  select * into c from public.config where id = 1;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Horarios', 'mismo día ' || case when c.mismo_dia then 'SI' else 'NO' end || ' · margen ' || c.margen_min || ' min');
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'mismoDia', c.mismo_dia, 'margenMin', c.margen_min, 'cruces', privado.lista_cruces());
end $$;

create or replace function privado.panel_cruce(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  x text := btrim(privado.jtext(b -> 'a'));
  y text := btrim(privado.jtext(b -> 'b'));
  v_a text := least(x, y);
  v_b text := greatest(x, y);
  si boolean := (b -> 'permitido') = 'true'::jsonb;
begin
  if not exists (select 1 from public.actividades where id = v_a) or not exists (select 1 from public.actividades where id = v_b) or v_a = v_b then
    return privado.fallo('actividad_invalida', 'Elige dos actividades existentes y distintas.');
  end if;
  if si then
    insert into public.cruces_permitidos (a, b, permitido_por) values (v_a, v_b, (s ->> 'uid')::uuid) on conflict do nothing;
  else
    if exists (select 1 from public.cruces_permitidos cp where cp.a = v_a and cp.b = v_b) and privado.abierto() then return privado.requiere_cierre(); end if;
    delete from public.cruces_permitidos cp where cp.a = v_a and cp.b = v_b;
  end if;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Cruce ' || v_a || ' × ' || v_b, case when si then 'permitido' else 'bloqueado' end);
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'a', v_a, 'b', v_b, 'permitido', si);
end $$;

-- Al aprobar solicitudes de un grupo de WhatsApp (R-29): ¿este celular está inscrito en esta actividad?
create or replace function privado.panel_verificar_celular(b jsonb) returns jsonb language plpgsql stable as $$
declare
  v_id text := btrim(privado.jtext(b -> 'id'));
  dig text := regexp_replace(privado.jtext(b -> 'celular'), '\D', '', 'g');
  i public.inscripciones;
begin
  if not exists (select 1 from public.actividades where id = v_id) then return privado.fallo('actividad_invalida', 'Elige la actividad del grupo.'); end if;
  if length(dig) < 9 then return privado.fallo('celular_invalido', 'Escribe el celular que aparece en la solicitud (al menos 9 dígitos).'); end if;
  select ins.* into i from public.inscripciones ins join public.inscripcion_actividades ia using (codigo)
  where ia.actividad_id = v_id and ins.estado = 'CONFIRMADO' and right(regexp_replace(ins.celular, '\D', '', 'g'), 9) = right(dig, 9) limit 1;
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'id', v_id, 'inscrito', found,
    'nombre', case when found then i.nombre end, 'codigo', case when found then i.codigo end);
end $$;

-- CSV: inscripciones, padrón con estado, o lista de una actividad (nombre y celular).
create or replace function privado.panel_registros(b jsonb) returns jsonb language plpgsql stable as $$
declare f text := coalesce(nullif(privado.jtext(b -> 'formato'), ''), 'inscripciones');
begin
  if f = 'padron' then
    return jsonb_build_object('ok', true, 'tipo', 'panel', 'encabezados', '["Documento","Etapa","Nombre","Origen","Estado","Código"]'::jsonb,
      'filas', coalesce((select jsonb_agg(jsonb_build_array(p.documento, p.etapa::text, p.nombre, p.origen, coalesce(i.estado, 'SIN_INSCRIBIR'), coalesce(i.codigo, ''))
                         order by p.orden)
                         from public.padron p left join public.inscripciones i on i.documento = p.documento and i.estado = 'CONFIRMADO'), '[]'::jsonb));
  end if;
  if f = 'actividad' then
    return jsonb_build_object('ok', true, 'tipo', 'panel', 'encabezados', '["Nombre","Celular","Código"]'::jsonb,
      'filas', coalesce((select jsonb_agg(jsonb_build_array(i.nombre, i.celular, i.codigo) order by i.nombre)
                         from public.inscripciones i join public.inscripcion_actividades ia using (codigo)
                         where ia.actividad_id = btrim(privado.jtext(b -> 'id')) and i.estado = 'CONFIRMADO'), '[]'::jsonb));
  end if;
  return jsonb_build_object('ok', true, 'tipo', 'panel',
    'encabezados', '["Fecha/Hora","Código","Documento","Nombre","Correo","Etapa","ID Actividad 1","Actividad 1","ID Actividad 2","Actividad 2","Estado","Celular","País","Origen","Ronda"]'::jsonb,
    'filas', coalesce((select jsonb_agg(jsonb_build_array(to_char(i.creado_en at time zone 'America/Lima', 'YYYY-MM-DD HH24:MI:SS'), i.codigo, i.documento, i.nombre,
                         i.correo, i.etapa::text, coalesce(x.ids[1], ''), coalesce(x.noms[1], ''), coalesce(x.ids[2], ''), coalesce(x.noms[2], ''), i.estado,
                         i.celular, i.pais, i.origen, i.ronda::text) order by i.orden)
                       from public.inscripciones i
                       left join lateral (select array_agg(ia.actividad_id order by a.fecha, a.inicio, ia.actividad_id) ids,
                                                 array_agg(ia.actividad_nombre order by a.fecha, a.inicio, ia.actividad_id) noms
                                          from public.inscripcion_actividades ia left join public.actividades a on a.id = ia.actividad_id
                                          where ia.codigo = i.codigo) x on true), '[]'::jsonb));
end $$;

create or replace function privado.panel_sincronizar(s jsonb) returns jsonb language plpgsql volatile as $$
declare n int;
begin
  perform 1 from public.actividades order by id for update;
  perform privado.recalcular_inscritos();
  select count(*) into n from public.inscripciones where estado = 'CONFIRMADO';
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Sincronizar', 'recuento de inscritos (' || n || ' confirmadas)');
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'inscritos', n);
end $$;


-- ═════════ Equipo (solo propietario) ══════════════════════════════════════

create or replace function privado.panel_equipo() returns jsonb language sql stable as $$
  select jsonb_build_object('ok', true, 'tipo', 'panel', 'cuentas', coalesce(jsonb_agg(jsonb_build_object(
      'usuario', u.id, 'correo', u.email, 'nombre', coalesce(o.nombre, ''), 'rol', o.rol, 'activo', coalesce(o.activo, true),
      'totp', exists (select 1 from auth.mfa_factors f where f.user_id = u.id and f.status::text = 'verified')) order by u.email), '[]'::jsonb))
  from auth.users u left join public.organizadores o on o.user_id = u.id
$$;

create or replace function privado.panel_equipo_rol(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_u uuid;
  v_rol text := nullif(privado.jtext(b -> 'rol'), '');
  v_nombre text := privado.texto_limpio(b -> 'nombre', 80);
  v_correo text;
begin
  begin v_u := privado.jtext(b -> 'usuario')::uuid; exception when others then return privado.fallo('no_encontrado', 'No existe esa cuenta.'); end;
  select email into v_correo from auth.users where id = v_u;
  if not found then return privado.fallo('no_encontrado', 'No existe esa cuenta.'); end if;
  if v_rol is not null and v_rol not in ('propietario', 'admin', 'operador') then return privado.fallo('valor_invalido', 'Rol desconocido.'); end if;
  if v_u = (s ->> 'uid')::uuid and v_rol is distinct from 'propietario' then
    return privado.fallo('no_permitido', 'No puedes quitarte tu propio rol de propietario: otro propietario debe hacerlo.');
  end if;
  insert into public.organizadores (user_id, nombre, rol) values (v_u, coalesce(nullif(v_nombre, ''), split_part(v_correo, '@', 1)), v_rol)
  on conflict (user_id) do update set rol = excluded.rol, nombre = case when v_nombre <> '' then v_nombre else public.organizadores.nombre end;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Equipo', v_correo || ' → ' || coalesce(v_rol, 'sin rol'));
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'usuario', v_u, 'rol', v_rol);
end $$;

create or replace function privado.panel_equipo_activo(b jsonb, s jsonb) returns jsonb language plpgsql volatile as $$
declare
  v_u uuid;
  v_act boolean := (b -> 'activo') = 'true'::jsonb;
  v_correo text;
begin
  begin v_u := privado.jtext(b -> 'usuario')::uuid; exception when others then return privado.fallo('no_encontrado', 'No existe esa cuenta.'); end;
  select email into v_correo from auth.users where id = v_u;
  if not found then return privado.fallo('no_encontrado', 'No existe esa cuenta.'); end if;
  if v_u = (s ->> 'uid')::uuid then return privado.fallo('no_permitido', 'No puedes desactivar tu propia cuenta.'); end if;
  insert into public.organizadores (user_id, nombre, activo) values (v_u, split_part(v_correo, '@', 1), v_act)
  on conflict (user_id) do update set activo = excluded.activo;
  perform privado.bitacora((s ->> 'uid')::uuid, privado.quien(s), 'Equipo', v_correo || case when v_act then ' activada' else ' desactivada' end);
  return jsonb_build_object('ok', true, 'tipo', 'panel', 'usuario', v_u, 'activo', v_act);
end $$;


-- ═════════ Tester (ADMIN_KEY + modo PRUEBA) ═══════════════════════════════

create or replace function privado.con_admin(b jsonb, requiere_prueba boolean) returns jsonb language plpgsql volatile as $$
begin
  if not exists (select 1 from privado.claves where nombre = 'ADMIN_KEY') then
    return privado.fallo('admin_deshabilitado', 'No hay ADMIN_KEY configurada: las funciones del tester están apagadas.');
  end if;
  if not privado.clave_ok('ADMIN_KEY', privado.jtext(b -> 'key')) then
    perform pg_sleep(1.5);
    return privado.fallo('no_autorizado', 'Clave de administración incorrecta.');
  end if;
  if requiere_prueba and (select modo from public.config where id = 1) <> 'PRUEBA' then
    return privado.fallo('modo_produccion', 'La base está en modo PRODUCCION: el tester solo puede hacer pruebas de lectura.');
  end if;
  return null;
end $$;

create or replace function privado.admin_muestra(b jsonb) returns jsonb language plpgsql volatile as $$
declare
  n int := least(greatest(coalesce(nullif(privado.entero(b -> 'n'), 0), 30), 1), 500);
  v_inex text := '';
  d text;
begin
  for k in 1..200 loop
    d := (10000000 + floor(random() * 89999999))::bigint::text;
    if not exists (select 1 from public.padron where documento = d) and not exists (select 1 from public.inscripciones where documento = d) then v_inex := d; exit; end if;
  end loop;
  return jsonb_build_object('ok', true, 'tipo', 'admin', 'inexistente', v_inex,
    'etapas', (select jsonb_object_agg(e::text, coalesce((select jsonb_agg(documento order by orden) from (
        select p.documento, p.orden from public.padron p where p.etapa = e
          and (select count(*) from public.padron p2 where p2.documento = p.documento) = 1
          and not exists (select 1 from public.inscripciones i where i.documento = p.documento)
        order by p.orden limit n) s), '[]'::jsonb)) from unnest(array[1, 2, 3]) e));
end $$;

-- Borra lo que el tester creó: inscripciones de sus documentos, padrón agregado y su configuración de intentos.
create or replace function privado.admin_limpiar(b jsonb) returns jsonb language plpgsql volatile as $$
declare
  docs text[];
  padr text[];
  n int;
begin
  select coalesce(array_agg(privado.normalizar_doc(x)), '{}') into docs
  from jsonb_array_elements(case when jsonb_typeof(b -> 'docs') = 'array' then b -> 'docs' else '[]'::jsonb end) x;
  select coalesce(array_agg(privado.normalizar_doc(x)), '{}') into padr
  from jsonb_array_elements(case when jsonb_typeof(b -> 'padron') = 'array' then b -> 'padron' else '[]'::jsonb end) x;
  perform 1 from public.actividades order by id for update;
  delete from public.inscripciones where documento = any (docs);
  get diagnostics n = row_count;
  delete from public.padron where documento = any (padr) and origen = 'PANEL';
  if (b -> 'intentos') = 'true'::jsonb then delete from public.intentos; end if;
  perform privado.recalcular_inscritos();
  return jsonb_build_object('ok', true, 'tipo', 'admin', 'eliminados', n);
end $$;


-- ═════════ LA PUERTA: public.api(p) ═══════════════════════════════════════
--  POST https://TU-PROYECTO.supabase.co/rest/v1/rpc/api   {"p": {"action": "…", …}}

create or replace function public.api(p jsonb) returns jsonb
language plpgsql volatile security definer set search_path = public, privado, extensions, pg_temp as $$
declare
  accion text;
  s jsonb;
  chk jsonb;
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
    if privado.rango(s ->> 'rol') < privado.rol_minimo(accion) then
      return privado.fallo('sin_permiso', case privado.rol_minimo(accion) when 3 then 'Solo el propietario administra el equipo.'
                                              else 'Tu cuenta es de operador: esta acción la hace un admin.' end);
    end if;
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
      when 'panel_equipo'            then privado.panel_equipo()
      when 'panel_equipo_rol'        then privado.panel_equipo_rol(p, s)
      when 'panel_equipo_activo'     then privado.panel_equipo_activo(p, s)
      else privado.fallo('accion_invalida', 'Acción no reconocida.') end;
  end if;

  if accion in ('admin_ping', 'admin_muestra', 'admin_limpiar') then
    chk := privado.con_admin(p, accion <> 'admin_ping');
    if chk is not null then return chk; end if;
    return case accion
      when 'admin_ping'    then jsonb_build_object('ok', true, 'tipo', 'admin', 'version', privado.version(), 'config', privado.config_json())
      when 'admin_muestra' then privado.admin_muestra(p)
      else privado.admin_limpiar(p) end;
  end if;

  return privado.fallo('accion_invalida', 'Acción no reconocida.');
exception
  when lock_not_available or query_canceled or deadlock_detected or serialization_failure then
    return privado.fallo('ocupado', 'Sistema ocupado, reintenta.');
  when others then
    return privado.fallo('error_servidor', 'Ocurrió un error en el sistema. Intenta de nuevo en unos segundos.', jsonb_build_object('detalle', sqlerrm));
end $$;

-- ── Permisos: solo la puerta es pública ─────────────────────────────────
revoke all on all functions in schema privado from public, anon, authenticated;
revoke all on function public.api(jsonb) from public;
grant execute on function public.api(jsonb) to anon, authenticated;
