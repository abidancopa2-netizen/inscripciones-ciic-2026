#!/usr/bin/env python3
"""
Restaura un respaldo del panel (Sistema → Respaldo, R-41) · documentación §19.5.

    python supabase/restaurar.py respaldo.json --verificar                                # huella, versión y filas; no toca nada
    python supabase/restaurar.py respaldo.json --solo-faltantes --salida restaurar.sql   # pérdida parcial: devuelve lo borrado
    python supabase/restaurar.py respaldo.json --completo --salida restaurar.sql         # pérdida total: base nueva, instalada y vacía
    python supabase/restaurar.py respaldo.json --solo-faltantes --simular --dsn "$DSN_PRODUCCION" --confirmar "$REF_PRODUCCION"

Sin --dsn escribe el SQL para pegarlo en el SQL Editor de Supabase (todo en una transacción). Con --dsn lo aplica
directamente (mejor si el archivo es grande); en una base remota exige --confirmar <ref>.
--simular hace todo y lo deshace al final: muestra qué volvería, sin cambiar nada. Úsalo siempre primero.
--tablas padron,inscripciones restringe qué tablas se devuelven (por defecto, todas).
--aceptar-huella-distinta (EMERGENCIA): restaura aunque la huella no coincida, si las filas de cada tabla cuadran;
  p. ej. un respaldo guardado con el panel del Sprint 4 que tenga decimales en datos. Siempre con --simular primero.

Siempre verifica primero la huella: si el archivo está dañado o se modificó sin recalcularla, no genera nada.
Antes de cambiar nada, el SQL exige las inscripciones cerradas, un esquema igual o más nuevo que el del respaldo y,
con --solo-faltantes, el mismo modo (PRUEBA o PRODUCCION) que el respaldo; con --completo, una base sin datos.

--solo-faltantes devuelve filas BORRADAS; no repara filas modificadas (las que existen no se tocan):
  · una inscripción vuelve entera, con sus actividades, solo si ya no existe; a una inscripción que existe nunca se le
    agregan actividades (si se cambió después del respaldo, queda como está);
  · las actividades que vuelven, vuelven ocultas (revísalas y muéstralas desde el Panel 1);
  · todo lo que vuelve queda en el informe y en la bitácora.
Las cuentas del equipo (Supabase Auth) no están en el respaldo: en un proyecto nuevo se invitan de nuevo (§19.5, paso 4).

El respaldo y el SQL tienen datos personales: nunca en GitHub, en chats ni en correos.
"""
import argparse
import decimal
import hashlib
import json
import re
import secrets
import sys
from pathlib import Path

TABLAS = ['tipos_actividad', 'padron', 'actividades', 'cruces_permitidos', 'inscripciones', 'inscripcion_actividades',
          'organizadores', 'bitacora', 'incidencias']          # orden de las referencias
TODAS = TABLAS + ['config']


def clave_jsonb(k):
    b = k.encode('utf-8')
    return (len(b), b)


def texto_jsonb(v):
    """El texto que PostgreSQL da a un jsonb (migración 08): claves por largo y luego por bytes, ", " y ": "."""
    if isinstance(v, dict):
        return '{' + ', '.join(json.dumps(k, ensure_ascii=False) + ': ' + texto_jsonb(v[k]) for k in sorted(v, key=clave_jsonb)) + '}'
    if isinstance(v, list):
        return '[' + ', '.join(texto_jsonb(x) for x in v) + ']'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if v is None:
        return 'null'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, decimal.Decimal):          # los decimales se leen tal cual vienen (1.50 sigue siendo 1.50)
        return format(v, 'f')
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    return json.dumps(v, ensure_ascii=False)


def json_compacto(v):
    """JSON sin espacios para el SQL, con los decimales exactos (json.dumps no sabe escribir Decimal)."""
    if isinstance(v, dict):
        return '{' + ','.join(json.dumps(k, ensure_ascii=False) + ':' + json_compacto(x) for k, x in v.items()) + '}'
    if isinstance(v, list):
        return '[' + ','.join(json_compacto(x) for x in v) + ']'
    if isinstance(v, decimal.Decimal):
        return format(v, 'f')
    return json.dumps(v, ensure_ascii=False)


def sha(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def leer(ruta):
    try:
        r = json.loads(Path(ruta).read_text(encoding='utf-8-sig'), parse_float=decimal.Decimal)
    except (OSError, ValueError) as e:
        sys.exit(f'✘ No se pudo leer {ruta}: {e}')
    if not isinstance(r, dict) or not isinstance(r.get('tablas'), dict):
        sys.exit('✘ No es un respaldo del panel (falta "tablas"). Descárgalo desde Sistema → Respaldo.')
    return r


def verificar(r, ver=True):
    """Devuelve (problemas, solo_huella): la lista de problemas y si todos son de huella (las filas cuadran)."""
    t, problemas = r['tablas'], []
    if r.get('formato') != 'ciic-respaldo-1':
        problemas.append(f'formato {r.get("formato")!r}: este programa lee ciic-respaldo-1 (respaldos del Sprint 4 en adelante)')
    if not re.fullmatch(r'5\.5-s\d+(\.\d+)?', str(r.get('version', ''))):
        problemas.append(f'versión del esquema desconocida: {r.get("version")!r}')
    for nom in TODAS:
        if not isinstance(t.get(nom), list):
            problemas.append(f'falta la tabla {nom}')
    if problemas:
        return problemas, False
    if len(t['config']) != 1 or t['config'][0].get('modo') not in ('PRUEBA', 'PRODUCCION'):
        problemas.append('la configuración del respaldo no es válida')
    filas, huellas = r.get('filas') or {}, r.get('huellas') or {}
    de_huella = []
    if ver:
        print(f"Respaldo {r.get('version')} · modo {t['config'][0].get('modo')} · generado {r.get('generadoEn')} · {r.get('generadoPor')}")
    for nom in sorted(t, key=clave_jsonb):
        n_ok = filas.get(nom) == len(t[nom])
        h_ok = huellas.get(nom) == sha(texto_jsonb(t[nom]))
        if ver:
            print(f"  {'✔' if n_ok and h_ok else '✘'} {nom:24} {len(t[nom]):6} filas" + ('' if n_ok else f' (el respaldo dice {filas.get(nom)})')
                  + ('' if h_ok else ' · huella distinta'))
        if not n_ok:
            problemas.append(f'{nom}: {len(t[nom])} filas y el respaldo dice {filas.get(nom)}')
        if not h_ok:
            de_huella.append(f'{nom}: la huella no coincide (archivo dañado o modificado)')
    total = sha(texto_jsonb(t))
    if total != r.get('huella'):
        de_huella.append('la huella total no coincide (archivo dañado o modificado)')
    if ver:
        print(f"  {'✔' if total == r.get('huella') else '✘'} huella total {total[:12]}…")
    return problemas + de_huella, bool(de_huella) and not problemas


def etiqueta(texto):
    while True:
        e = 'r' + secrets.token_hex(6)
        if f'${e}$' not in texto:
            return e


PLANTILLA = r"""-- Restauración __MODO__ de las inscripciones (supabase/restaurar.py): NO es una migración y no va en supabase/.
-- Respaldo __VERSION__ (modo __MODO_RESPALDO__) del __FECHA__ · huella __HUELLA12__ · archivo __ARCHIVO__
-- Tiene datos personales: no lo subas a GitHub ni lo compartas (.gitignore excluye restaurar*.sql).
-- Todo va en una transacción: si algo falla, la base queda como estaba (los contadores de ids solo avanzan).
begin;
create temp table ciic_respaldo (tabla text primary key, filas jsonb not null) on commit drop;
insert into ciic_respaldo (tabla, filas) values
__DATOS__
create temp table if not exists ciic_informe (orden int, tabla text, en_respaldo int, agregadas int, ya_estaban int, nota text);
delete from ciic_informe where true;
create temp table ciic_nuevas (codigo text primary key) on commit drop;       -- inscripciones que vuelven en esta corrida
create temp table ciic_act_nuevas (id text primary key) on commit drop;       -- actividades que vuelven en esta corrida

do $ciic$
declare
  v_modo text := '__MODO__';
  v_version text := '__VERSION__';
  v_modo_respaldo text := '__MODO_RESPALDO__';
  v_huella text := '__HUELLA__';
  v_fecha text := '__FECHA__';
  v_tablas text[] := array[__TABLAS__];
  v_simular boolean := __SIMULAR__;
  c public.config;
  t text;
  tbl regclass;
  cols text;
  sel text;
  filtro text;
  extra text;
  n_resp int;
  n_ins int;
  n_dos int;
  k int := 0;
  vb int[];
  vt int[];
  id_rel regclass;
  id_col name;
  v_seq text;
  v_max bigint;
  v_txt text;
  v_err text;
begin
  select * into c from public.config where id = 1 for update;            -- nadie abre mientras tanto
  if c.abierto then
    raise exception 'Cierra las inscripciones (Panel 1 → Cerrar ahora) antes de restaurar. No se cambió nada.';
  end if;
  vb := (select array[coalesce(m[1], '0')::int, coalesce(m[2], '0')::int] from regexp_match(v_version, 's(\d+)(?:\.(\d+))?$') m);
  vt := (select array[coalesce(m[1], '0')::int, coalesce(m[2], '0')::int] from regexp_match(privado.version(), 's(\d+)(?:\.(\d+))?$') m);
  if vt < vb then
    raise exception 'La base está en % y el respaldo es de %: instala primero las migraciones con supabase/instalar.py. No se cambió nada.', privado.version(), v_version;
  end if;
  if v_modo = 'solo-faltantes' and c.modo <> v_modo_respaldo then
    raise exception 'El respaldo es de una base en modo % y esta base está en modo %: no se mezclan (por ejemplo, datos de prueba en producción). No se cambió nada.', v_modo_respaldo, c.modo;
  end if;
  if v_modo = 'completo' then
    select string_agg(x, ', ') into v_txt from (
      select 'padrón' x where exists (select 1 from public.padron) union all
      select 'actividades' where exists (select 1 from public.actividades) union all
      select 'cruces permitidos' where exists (select 1 from public.cruces_permitidos) union all
      select 'inscripciones' where exists (select 1 from public.inscripciones) union all
      select 'actividades de inscripciones' where exists (select 1 from public.inscripcion_actividades)) s;
    if v_txt is not null then
      raise exception 'La base no está vacía (tiene %): para devolver filas borradas usa --solo-faltantes (§19.5, paso 3a). No se cambió nada.', v_txt;
    end if;
  end if;
  perform set_config('ciic.masivo', 'confirmado', true);

  foreach t in array array['tipos_actividad', 'padron', 'actividades', 'cruces_permitidos', 'inscripciones', 'inscripcion_actividades',
                           'organizadores', 'bitacora', 'incidencias'] loop
    k := k + 1;
    if not t = any (v_tablas) then
      insert into ciic_informe values (k, t, 0, 0, 0, 'no se pidió (--tablas)');
      continue;
    end if;
    tbl := (case when t = 'incidencias' then 'privado.' else 'public.' end || t)::regclass;
    select jsonb_array_length(filas) into n_resp from ciic_respaldo where tabla = t;
    if coalesce(n_resp, 0) = 0 then
      insert into ciic_informe values (k, t, 0, 0, 0, '');
      continue;
    end if;
    select string_agg(quote_ident(a.attname), ', ' order by a.attnum),
           string_agg(case when t = 'actividades' and a.attname = 'inscritos' then '0'                              -- los recuentan los disparadores
                           when t = 'actividades' and a.attname = 'publicada' and v_modo = 'solo-faltantes' then 'false'   -- vuelven ocultas
                           else 'x.' || quote_ident(a.attname) end, ', ' order by a.attnum)
      into cols, sel
    from pg_attribute a
    where a.attrelid = tbl and a.attnum > 0 and not a.attisdropped and a.attgenerated = ''
      and exists (select 1 from ciic_respaldo r where r.tabla = t and (r.filas -> 0) ? a.attname);
    filtro := case t
      when 'actividades' then 'exists (select 1 from public.tipos_actividad y where y.codigo = x.tipo)'
      when 'cruces_permitidos' then 'exists (select 1 from public.actividades y where y.id = x.a) and exists (select 1 from public.actividades y where y.id = x.b)'
      -- una inscripción vuelve ENTERA: sus actividades solo si la inscripción volvió en esta corrida (sin FK a actividades, a propósito)
      when 'inscripcion_actividades' then 'exists (select 1 from ciic_nuevas y where y.codigo = x.codigo)'
      when 'organizadores' then 'exists (select 1 from auth.users y where y.id = x.user_id)'
      else 'true' end;
    extra := case
      when t = 'tipos_actividad' and v_modo = 'completo' then
        'on conflict (codigo) do update set ' || (select string_agg(quote_ident(a.attname) || ' = excluded.' || quote_ident(a.attname), ', ')
          from pg_attribute a where a.attrelid = tbl and a.attnum > 0 and not a.attisdropped and a.attname <> 'codigo'
            and exists (select 1 from ciic_respaldo r where r.tabla = t and (r.filas -> 0) ? a.attname))
      else 'on conflict do nothing' end;
    begin
      if t in ('inscripciones', 'actividades') then
        execute format('with i as (insert into %s (%s) overriding system value select %s from jsonb_populate_recordset(null::%s, (select filas from ciic_respaldo where tabla = %L)) x where %s %s returning %s) insert into %s select * from i',
                       tbl, cols, sel, tbl, t, filtro, extra, case when t = 'inscripciones' then 'codigo' else 'id' end,
                       case when t = 'inscripciones' then 'ciic_nuevas' else 'ciic_act_nuevas' end);
      else
        execute format('insert into %s (%s) overriding system value select %s from jsonb_populate_recordset(null::%s, (select filas from ciic_respaldo where tabla = %L)) x where %s %s',
                       tbl, cols, sel, tbl, t, filtro, extra);
      end if;
    exception when check_violation then
      get stacked diagnostics v_err = constraint_name;
      raise exception 'Al devolver % no se cumple la regla %: si es un cupo (inscritos ≤ cupo), amplía esa actividad en el Panel 1 y vuelve a correr. No se cambió nada.', t, v_err;
    end;
    get diagnostics n_ins = row_count;
    n_dos := 0;
    if t in ('bitacora', 'incidencias') and v_modo = 'completo' then
      -- en una base nueva puede haber ya alguna entrada (p. ej. asignar_propietario): las del respaldo cuyo id está ocupado
      -- por otra entrada entran igual, con un id nuevo
      execute format('select setval(pg_get_serial_sequence(%L, ''id''), greatest(coalesce((select max(id) from %s), 0), 1))', tbl::text, tbl);
      select string_agg(quote_ident(a.attname), ', ' order by a.attnum), string_agg('x.' || quote_ident(a.attname), ', ' order by a.attnum) into cols, sel
      from pg_attribute a where a.attrelid = tbl and a.attnum > 0 and not a.attisdropped and a.attgenerated = '' and a.attname <> 'id'
        and exists (select 1 from ciic_respaldo r where r.tabla = t and (r.filas -> 0) ? a.attname);
      execute format('insert into %s (%s) select %s from jsonb_populate_recordset(null::%s, (select filas from ciic_respaldo where tabla = %L)) x '
                     'where exists (select 1 from %s y where y.id = x.id and (to_jsonb(y) - ''id'') is distinct from (to_jsonb(x) - ''id'')) order by x.id',
                     tbl, cols, sel, tbl, t, tbl);
      get diagnostics n_dos = row_count;
    end if;
    insert into ciic_informe values (k, t, n_resp, n_ins + n_dos, n_resp - n_ins - n_dos,
      case
        when t = 'organizadores' and (select count(*) from ciic_respaldo r, jsonb_array_elements(r.filas) f(x)
                                      where r.tabla = t and not exists (select 1 from auth.users u where u.id = (f.x ->> 'user_id')::uuid)) > 0
          then 'cuentas sin usuario en este proyecto: invita al equipo y asigna roles (§19.5, paso 4)'
        when t = 'actividades' and v_modo = 'solo-faltantes' and n_ins > 0
          then 'vuelven OCULTAS: ' || (select string_agg(id, ', ' order by id) from ciic_act_nuevas) || ' · revísalas y muéstralas en el Panel 1'
        when t = 'inscripciones' and v_modo = 'solo-faltantes' and n_ins < n_resp
          then 'las que existen no se tocan (ni sus actividades, aunque hayan cambiado)'
        when t = 'tipos_actividad' and v_modo = 'completo' then 'con los valores del respaldo'
        when n_dos > 0 then n_dos || ' con un id nuevo (el suyo estaba ocupado)'
        else '' end);
  end loop;

  -- ids: las secuencias solo avanzan (nunca por debajo de lo ya entregado, aunque haya inserciones sin confirmar).
  -- En una simulación no se tocan (setval no se deshace con la transacción).
  for id_rel, id_col in select a.attrelid::regclass, a.attname from pg_attribute a
                        where a.attidentity <> '' and a.attrelid in ('public.padron'::regclass, 'public.actividades'::regclass, 'public.inscripciones'::regclass,
                                                                    'public.bitacora'::regclass, 'privado.incidencias'::regclass)
                          and not v_simular loop
    v_seq := pg_get_serial_sequence(id_rel::text, id_col);
    execute format('select greatest(coalesce((select max(%I) from %s), 0), coalesce(pg_sequence_last_value(%L::regclass), 0))', id_col, id_rel, v_seq) into v_max;
    if v_max > 0 then perform setval(v_seq, v_max, true); end if;
  end loop;

  if v_modo = 'completo' then
    select string_agg(quote_ident(a.attname), ', ' order by a.attnum), string_agg('x.' || quote_ident(a.attname), ', ' order by a.attnum)
      into cols, sel
    from pg_attribute a
    where a.attrelid = 'public.config'::regclass and a.attnum > 0 and not a.attisdropped and a.attgenerated = '' and a.attname <> 'id'
      and exists (select 1 from ciic_respaldo r where r.tabla = 'config' and (r.filas -> 0) ? a.attname);
    execute format('update public.config c set (%s) = (select %s from jsonb_populate_recordset(null::public.config, (select filas from ciic_respaldo where tabla = %L)) x) where c.id = 1',
                   cols, sel, 'config');
    update public.config set abierto = false, cierre_en = null, ronda = ronda + 1 where id = 1;   -- se abre a mano, después de revisar (§19.5, paso 6)
    insert into ciic_informe values (0, 'config', 1, 1, 0, 'restaurada cerrada y con la ronda +1: abre desde el panel cuando revises');
  else
    insert into ciic_informe values (0, 'config', 1, 0, 1, 'no se toca');
  end if;

  perform privado.recalcular_inscritos();
  if not (privado.integridad() ->> 'ok')::boolean then
    raise exception 'La integridad no cuadra después de restaurar: se revierte todo.';
  end if;
  if not v_simular then perform privado.bitacora(null, 'Restauración', 'Restaurar respaldo',
    v_modo || ' · respaldo del ' || v_fecha || ' · huella ' || left(v_huella, 12) || ' · ' || (select coalesce(sum(agregadas), 0) from ciic_informe where tabla <> 'config') || ' filas agregadas',
    null, (select jsonb_object_agg(tabla, agregadas) from ciic_informe)); end if;
  if v_simular then
    raise exception using errcode = 'P0001', message = 'SIMULACIÓN · no se cambió nada. Con ' || v_modo || ' volvería:' || chr(10) ||
      (select string_agg(format('  %-24s respaldo %6s · agregaría %6s · ya están %6s', tabla, en_respaldo, agregadas, ya_estaban) || coalesce(' · ' || nullif(nota, ''), ''), chr(10) order by orden)
       from ciic_informe);
  end if;
end $ciic$;

commit;
select tabla, en_respaldo, agregadas, ya_estaban, nota from ciic_informe order by orden;
"""


def generar_sql(r, modo, origen, tablas, simular):
    t = r['tablas']
    fecha = re.sub(r'[^0-9: -]', '', str(r.get('generadoEn', '')))[:19]
    datos = []
    for nom in TODAS:
        txt = json_compacto(t[nom])
        e = etiqueta(txt)
        datos.append(f"  ('{nom}', ${e}${txt}${e}$::jsonb)")
    reemplazos = {
        '__MODO__': modo, '__VERSION__': r['version'], '__MODO_RESPALDO__': t['config'][0]['modo'], '__FECHA__': fecha,
        '__HUELLA12__': r['huella'][:12], '__HUELLA__': r['huella'], '__ARCHIVO__': re.sub(r'[^\w.\- ]', '_', Path(origen).name),
        '__TABLAS__': ', '.join(f"'{x}'" for x in tablas), '__SIMULAR__': 'true' if simular else 'false',
    }
    sql = PLANTILLA
    for k, v in reemplazos.items():
        sql = sql.replace(k, v)
    return sql.replace('__DATOS__', ',\n'.join(datos) + ';')       # los datos al final: nunca se reemplaza nada dentro de ellos


def es_local(dsn):
    return not re.search(r'supabase\.(co|com)', dsn) and bool(re.search(r'(localhost|127\.0\.0\.1|host=/|::1)', dsn) or ('host=' not in dsn and '@' not in dsn))


def ref_del_dsn(dsn):
    m = re.search(r'postgres\.([a-z0-9]{15,30})[:@]', dsn) or re.search(r'db\.([a-z0-9]{15,30})\.supabase\.co', dsn)
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser(description='Restaura un respaldo del panel (documentación §19.5).')
    ap.add_argument('respaldo')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--verificar', action='store_true', help='solo comprueba huella, filas y versión')
    g.add_argument('--completo', action='store_true', help='base nueva, instalada con instalar.py y sin datos')
    g.add_argument('--solo-faltantes', action='store_true', help='devuelve solo lo borrado; no pisa nada')
    ap.add_argument('--simular', action='store_true', help='hace todo y lo deshace: muestra qué volvería')
    ap.add_argument('--aceptar-huella-distinta', action='store_true',
                    help='EMERGENCIA: restaura aunque la huella no coincida, si las filas de cada tabla sí cuadran (p. ej. un respaldo '
                         'del Sprint 4 con decimales en datos). Úsalo con --simular primero')
    ap.add_argument('--tablas', help='solo estas tablas, separadas por comas (inscripciones incluye sus actividades)')
    ap.add_argument('--dsn', help='aplica directamente en esta base, en vez de escribir el SQL')
    ap.add_argument('--confirmar', help='identificador del proyecto: obligatorio con --dsn remoto')
    ap.add_argument('--salida', help='escribe el SQL en este archivo (por defecto, en la salida estándar)')
    a = ap.parse_args()
    for f in (sys.stdout, sys.stderr):       # el SQL y los mensajes siempre en UTF-8 (en Windows, la salida redirigida sería cp1252)
        try:
            f.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    r = leer(a.respaldo)
    if a.verificar:
        p, solo_huella = verificar(r)
        if p:
            print('✘ Respaldo NO válido:\n  - ' + '\n  - '.join(p))
            if solo_huella:
                print('  Las filas de cada tabla cuadran: si es una emergencia y confías en el archivo, --aceptar-huella-distinta (con --simular primero).')
            return 1
        print('✔ Respaldo íntegro: se puede restaurar.')
        return 0
    p, solo_huella = verificar(r, ver=False)
    if p and not (solo_huella and a.aceptar_huella_distinta):
        print('✘ Respaldo NO válido, no se generó nada:\n  - ' + '\n  - '.join(p), file=sys.stderr)
        return 1
    if p:
        print('⚠ Huella distinta, aceptada a pedido (--aceptar-huella-distinta): las filas de cada tabla cuadran.\n  - ' + '\n  - '.join(p), file=sys.stderr)
    tablas = list(TABLAS)
    if a.tablas:
        tablas = [x.strip() for x in a.tablas.split(',') if x.strip()]
        malas = [x for x in tablas if x not in TABLAS]
        if malas:
            sys.exit(f'✘ Tablas desconocidas: {", ".join(malas)}. Son: {", ".join(TABLAS)}.')
        if 'inscripciones' in tablas and 'inscripcion_actividades' not in tablas:
            tablas.append('inscripcion_actividades')
    modo = 'completo' if a.completo else 'solo-faltantes'
    sql = generar_sql(r, modo, a.respaldo, tablas, a.simular)
    if not a.dsn:
        if a.salida:
            Path(a.salida).write_text(sql, encoding='utf-8')
            print(f'✔ {a.salida}: pégalo en el SQL Editor (o usa --dsn si es grande).', file=sys.stderr)
        else:
            sys.stdout.write(sql)
        return 0
    if not es_local(a.dsn):
        ref = ref_del_dsn(a.dsn)
        if not a.confirmar:
            sys.exit(f'Base remota: agrega --confirmar {ref or "<id-del-proyecto>"} para confirmar que es el proyecto correcto. No se conectó.')
        if ref and a.confirmar != ref:
            sys.exit(f'--confirmar {a.confirmar} no coincide con el proyecto de la cadena de conexión ({ref}). No se conectó.')
    import psycopg2
    con = psycopg2.connect(a.dsn, connect_timeout=15)
    con.autocommit = True
    cur = con.cursor()
    try:
        cur.execute(sql)
        filas = cur.fetchall()
    except psycopg2.Error as e:
        msg = str(e).strip()
        con.close()
        if 'SIMULACIÓN' in msg:
            print(msg[msg.index('SIMULACIÓN'):].split('\nCONTEXT')[0].rstrip())
            return 0
        print('✘ ' + msg.splitlines()[0])
        print('  No se cambió nada: todo iba en una sola transacción.')
        return 1
    con.close()
    print(f'✔ Restauración {modo} aplicada.')
    for tabla, n, ag, ya, nota in filas:
        print(f'  {tabla:24} respaldo {n:6} · agregadas {ag:6} · ya estaban {ya:6}' + (f' · {nota}' if nota else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
