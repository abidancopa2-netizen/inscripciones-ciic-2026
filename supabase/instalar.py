#!/usr/bin/env python3
"""
INSTALAR (o poner al día) la base en un proyecto de Supabase o en PostgreSQL local.

    python supabase/instalar.py --dsn "$DSN_PRUEBA" --confirmar "$REF_PRUEBA" --datos local/datos_prueba.sql
    python supabase/instalar.py --dsn "$DSN_PRODUCCION" --confirmar "$REF_PRODUCCION"
    python supabase/instalar.py --dsn "…" --confirmar "…" --verificar        # solo dice qué aplicaría

  --dsn        cadena de conexión. En Supabase: botón "Connect" → "Session pooler". Nunca en un archivo del repositorio.
  --confirmar  el identificador del proyecto. Obligatorio si la base no es local: se revisa ANTES de conectarse.
  --datos      datos ficticios: solo en modo PRUEBA y con padrón, actividades e inscripciones vacíos.
  --verificar  no cambia nada: muestra la versión, las migraciones aplicadas y las pendientes.

REGISTRO DE MIGRACIONES (Sprint 3.1). privado.migraciones guarda qué archivo se aplicó y con qué huella. Se aplica
SOLO lo pendiente, y todo lo pendiente en UNA transacción: si un archivo falla, la base queda exactamente como estaba
(nunca con 02 reaplicado y una migración posterior a medias, que dejaba una API vieja en vivo). En una base instalada
antes del registro, lo aplicado se deduce de privado.version(). Si un archivo ya aplicado cambió, se avisa y no se
reaplica: las correcciones van en una migración nueva.

QUÉ ES UNA MIGRACIÓN. Un archivo supabase/NN_nombre.sql cuyas primeras líneas llevan "CIIC 2026" y su número ("NN ·").
Un archivo generado por excel_a_sql.py (que puede traer datos reales) no lleva ese encabezado: nunca se ejecuta aquí.
Nunca corre local/supabase_local.sql.

Arreglos del reporte del Sprint 3 (Fase A): no se toca nada si la base está en PRODUCCION y abierta; --datos exige
padrón, actividades e inscripciones vacíos; los archivos de datos sueltos se excluyen.
"""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import psycopg2

RAIZ = Path(__file__).resolve().parent.parent
POR_VERSION = {'5.1': 2, '5.5-s1': 3, '5.5-s2': 4, '5.5-s3': 5, '5.5-s3.1': 6, '5.5-s3.2': 7, '5.5-s4': 8, '5.5-s4.1': 9, '5.5-s5.1': 10, '5.5-s6': 12}     # versión → hasta qué migración tenía aplicada (bases sin registro)


def limpieza(cur, local, pendiente=False):
    """Sprint 6 · migración 12: si la base borra sola los intentos (pg_cron), su última corrida y cuántos quedan viejos. Solo lee."""
    if pendiente:
        return 'pendiente (migración 12)'
    try:
        cur.execute("select to_regclass('cron.job') is not null, to_regprocedure('privado.ventana()') is not null")
        hay_cron, hay_ventana = cur.fetchone()
        extra = ''
        if hay_ventana:
            cur.execute("select count(*) from public.intentos where ventana < privado.ventana() - interval '10 minutes'")
            extra = f' · intentos terminados hace más de 10 min: {cur.fetchone()[0]}'
        if not hay_cron:
            return ('esta base no tiene pg_cron (normal en local); la hacen estado y "Mantener activo"' if local
                    else 'pg_cron NO está activo: la limpieza sigue con estado y "Mantener activo" (anótalo en el reporte)') + extra
        cur.execute("""select j.active, j.schedule,
                              (select d.status || ' hace ' || round(extract(epoch from now() - d.start_time) / 60) || ' min'
                                 from cron.job_run_details d where d.jobid = j.jobid order by d.start_time desc limit 1)
                         from cron.job j where j.jobname = 'ciic-limpiar-intentos'""")
        j = cur.fetchone()
        if not j:
            return 'NO programada (pg_cron está, pero el trabajo no): anótalo en el reporte' + extra
        return (f'activa, {j[1]}' if j[0] else 'PAUSADA') + (f' · última corrida: {j[2]}' if j[2] else ' · todavía sin corridas') + extra
    except Exception as e:  # noqa: BLE001
        return f'no se pudo leer ({str(e).strip().splitlines()[0][:80]})'


def configuracion(cur):
    """Sprint 6.1 (#44): lo que no se ve sin SQL. De dónde sale la IP real y los límites de intentos, solo leyendo.
    Con row_to_json no falla aunque a una versión vieja le falte alguna columna."""
    cur.execute('select row_to_json(c) from public.config c where id = 1')
    fila = cur.fetchone()
    c = fila[0] if fila else None
    if isinstance(c, str):
        c = json.loads(c)
    if not c:
        return None, 'sin la fila de configuración'
    ip = c.get('ip_cabecera')
    return ip, (f"IP real desde {ip if ip and ip != 'auto' else 'auto (pendiente)'} · límite por red {c.get('limite_red', '?')} · "
                f"por dispositivo {c.get('limite_dispositivo', '?')} · ventana {c.get('ventana_min', '?')} min · "
                f"modo {c.get('modo', '?')} · {'ABIERTA' if c.get('abierto') else 'cerrada'}")


def ref_del_dsn(dsn):
    m = re.search(r'postgres\.([a-z0-9]{15,30})[:@]', dsn) or re.search(r'db\.([a-z0-9]{15,30})\.supabase\.co', dsn)
    return m.group(1) if m else None


def es_local(dsn):
    return not re.search(r'supabase\.(co|com)', dsn) and bool(re.search(r'(localhost|127\.0\.0\.1|host=/|::1)', dsn) or ('host=' not in dsn and '@' not in dsn))


def huella(texto):
    return hashlib.sha256(texto.replace('\r\n', '\n').encode('utf-8')).hexdigest()[:12]


def migraciones():
    lista, ignorados = [], []
    for p in sorted((RAIZ / 'supabase').glob('*.sql')):
        m = re.fullmatch(r'(\d\d)_[A-Za-z0-9_]+\.sql', p.name)
        if not m:
            continue
        cabeza = '\n'.join(p.read_text(encoding='utf-8').splitlines()[:5])
        if 'CIIC 2026' not in cabeza or not re.search(rf'\b{m.group(1)} ·', cabeza) or 'excel_a_sql' in cabeza:
            ignorados.append(p.name)
            continue
        lista.append(p)
    return lista, ignorados


def sin_transaccion(texto):
    """Quita los begin;/commit; propios del archivo: aquí todo lo pendiente va en una sola transacción."""
    return '\n'.join('' if re.fullmatch(r'\s*(begin|commit)\s*;\s*', x, re.I) else x for x in texto.replace('\r\n', '\n').split('\n'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dsn', required=True)
    ap.add_argument('--confirmar', default=None)
    ap.add_argument('--datos', default=None)
    ap.add_argument('--verificar', action='store_true')
    a = ap.parse_args()

    local, ref = es_local(a.dsn), ref_del_dsn(a.dsn)
    if not local:
        if not a.confirmar:
            sys.exit(f'Base remota: agrega --confirmar {ref or "<id-del-proyecto>"} para confirmar que es el proyecto correcto. No se conectó.')
        if ref and a.confirmar != ref:
            sys.exit(f'--confirmar {a.confirmar} no coincide con el proyecto de la cadena de conexión ({ref}). No se conectó.')

    lista, ignorados = migraciones()
    for x in ignorados:
        print(f'  ○ {x}: no es una migración (sin el encabezado "CIIC 2026 · … · NN ·"): no se ejecuta')

    con = psycopg2.connect(a.dsn, connect_timeout=15)
    con.autocommit = False
    cur = con.cursor()
    cur.execute("select exists (select 1 from pg_namespace where nspname = 'auth'), current_setting('server_version'), current_database(), "
                "to_regprocedure('privado.version()') is not null, to_regclass('privado.migraciones') is not null, to_regclass('public.config') is not null")
    tiene_auth, version_pg, base, hay_version, hay_registro, hay_config = cur.fetchone()
    if not tiene_auth:
        sys.exit('La base no tiene el esquema "auth" de Supabase. En local, corre antes local/supabase_local.sql (imita a Supabase).')
    version = None
    if hay_version:
        cur.execute('select privado.version()')
        version = cur.fetchone()[0]
    if hay_config:
        cur.execute("select modo, abierto from public.config where id = 1")
        fila = cur.fetchone()
        if fila and fila[0] == 'PRODUCCION' and fila[1]:
            sys.exit('La base está en PRODUCCION con las inscripciones ABIERTAS: no se aplica nada. Ciérralas desde el panel y vuelve a correr.')
    print(f'Base: {base} · PostgreSQL {version_pg} · {"local" if local else "Supabase " + (ref or "")} · versión actual: {version or "sin instalar"}')

    aplicadas, forma = {}, 'registro'
    if hay_registro:
        cur.execute('select nombre, huella from privado.migraciones')
        aplicadas = dict(cur.fetchall())
    elif version:
        if version not in POR_VERSION:
            sys.exit(f'Versión {version} sin registro de migraciones y desconocida para este instalador: no se aplica nada.')
        aplicadas = {p.name: None for p in lista if int(p.name[:2]) <= POR_VERSION[version]}
        forma = f'deducido de la versión {version}'
    pendientes = [p for p in lista if p.name not in aplicadas]
    for p in lista:
        if p.name in aplicadas and aplicadas[p.name] and aplicadas[p.name] != huella(p.read_text(encoding='utf-8')):
            print(f'  ⚠ {p.name} cambió después de aplicarse: no se reaplica. Si hace falta corregir algo, va en una migración nueva.')
    print(f'Aplicadas ({forma}): {", ".join(sorted(aplicadas)) or "ninguna"}')
    print(f'Pendientes: {", ".join(p.name for p in pendientes) or "ninguna"}')

    if a.verificar:
        if hay_config:
            ip, texto = configuracion(cur)
            print('Configuración: ' + texto)
            if ip == 'auto':
                print('  · Pendiente: IP real → fija config.ip_cabecera (GUIA, C5).')
        print('Limpieza programada de intentos: ' + limpieza(cur, local, any(p.name.startswith('12_') for p in pendientes)))
        con.rollback()
        print('Solo verificación: no se cambió nada.')
        return

    if pendientes or not hay_registro:
        t0 = time.perf_counter()
        actual = None
        try:
            for p in pendientes:
                actual = p.name
                cur.execute(sin_transaccion(p.read_text(encoding='utf-8')))
            actual = 'registro de migraciones'
            cur.execute("""create table if not exists privado.migraciones (
                             nombre text primary key, huella text, aplicada_en timestamptz not null default now(), forma text not null)""")
            cur.execute('alter table privado.migraciones enable row level security')
            cur.execute('revoke all on privado.migraciones from public, anon, authenticated')
            for p in lista:
                if p.name in aplicadas and not hay_registro:
                    cur.execute("insert into privado.migraciones (nombre, huella, forma) values (%s, null, 'deducida') on conflict do nothing", (p.name,))
            for p in pendientes:
                cur.execute("insert into privado.migraciones (nombre, huella, forma) values (%s, %s, 'aplicada')", (p.name, huella(p.read_text(encoding='utf-8'))))
            con.commit()
            for n in getattr(con, 'notices', []):       # los avisos de la migración 12 (pg_cron), si los hubo
                if 'cron' in n.lower() or 'limpieza' in n.lower():
                    print('  ' + n.strip())
        except psycopg2.Error as e:
            con.rollback()
            print(f'  ✘ {actual}: {str(e).strip().splitlines()[0]}')
            print('    No se aplicó NADA: todo lo pendiente iba en una sola transacción y la base quedó exactamente como estaba.')
            sys.exit(1)
        for p in pendientes:
            print(f'  ✔ {p.name}')
        print(f'  ({time.perf_counter() - t0:.1f} s, en una sola transacción)')
    else:
        con.rollback()
        print('  La base ya está al día.')

    con.autocommit = True
    if a.datos:
        cur.execute("select modo, (select count(*) from public.padron), (select count(*) from public.actividades), (select count(*) from public.inscripciones) "
                    "from public.config where id = 1")
        modo, n_pad, n_act, n_ins = cur.fetchone()
        if modo != 'PRUEBA' or n_pad or n_act or n_ins:
            print(f'  ○ Datos NO cargados: modo {modo} · padrón {n_pad} · actividades {n_act} · inscripciones {n_ins}. '
                  'Solo se cargan en una base de PRUEBA vacía (para no borrar datos reales).')
        else:
            t0 = time.perf_counter()
            cur.execute(Path(a.datos).read_text(encoding='utf-8'))
            print(f'  ✔ {Path(a.datos).name}  ({time.perf_counter() - t0:.1f} s)')

    cur.execute("""select privado.version(), (select modo from public.config where id = 1), (select count(*) from public.padron),
                          (select count(*) from public.actividades), (select count(*) from public.inscripciones),
                          (privado.integridad() ->> 'ok'), (select count(*) from privado.claves where nombre = 'ADMIN_KEY'),
                          (select count(*) from public.organizadores where rol = 'propietario'), (select ip_cabecera from public.config where id = 1)""")
    v, modo, pad, act, ins, integ, clave, prop, ip = cur.fetchone()
    print(f'\nListo: versión {v} · modo {modo} · padrón {pad} · actividades {act} · inscripciones {ins} · integridad {"OK" if integ == "true" else "ROTA"}')
    if not prop:
        print("  · Pendiente: propietario → invítate en Authentication → Users y luego: select privado.asignar_propietario('tu@correo');")
    if modo == 'PRUEBA' and not clave:
        print('  · Pendiente: clave del tester (solo PRUEBA) → select privado.crear_clave_admin(); y guárdala como ADMIN_KEY (GUIA, C3).')
    if ip == 'auto':
        print('  · Pendiente: IP real → fija config.ip_cabecera (GUIA, C5).')
    print('  · Configuración: ' + configuracion(cur)[1])
    print('  · Limpieza programada de intentos: ' + limpieza(cur, local))
    con.close()


if __name__ == '__main__':
    main()
