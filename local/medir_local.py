#!/usr/bin/env python3
"""
DIAGNÓSTICO DE RENDIMIENTO LOCAL · ¿por qué la carga es lenta en esta computadora?

    python local/medir_local.py --dsn "dbname=ciic" --api http://127.0.0.1:8787

Mide, por separado, cada pieza que puede frenar la prueba de carga en local:
  1. Abrir una conexión a PostgreSQL (en Windows crea un proceso cada vez).
  2. Ida y vuelta de una consulta mínima.
  3. Confirmar una escritura esperando el disco (synchronous_commit on) y sin esperarlo (off).
  4. La API por HTTP: 50 llamadas seguidas a "estado".
  5. La API por HTTP: 100 llamadas a la vez a "estado".
Al final dice cuál es el cuello de botella y qué hacer. No toca ningún dato del sistema: para el punto 3 crea la
tabla public._medida_local, escribe 80 filas y la borra al terminar.
"""
import argparse
import concurrent.futures as cf
import statistics
import time

import psycopg2
import requests


def ms(x):
    return f'{x * 1000:.1f} ms'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dsn', default='dbname=ciic')
    ap.add_argument('--api', default='http://127.0.0.1:8787')
    a = ap.parse_args()
    r = {}

    t = []
    for _ in range(5):
        t0 = time.perf_counter(); c = psycopg2.connect(a.dsn); t.append(time.perf_counter() - t0); c.close()
    r['conexion'] = statistics.median(t)

    con = psycopg2.connect(a.dsn)
    con.autocommit = True
    cur = con.cursor()
    t = []
    for _ in range(50):
        t0 = time.perf_counter(); cur.execute('select 1'); cur.fetchone(); t.append(time.perf_counter() - t0)
    r['consulta'] = statistics.median(t)

    con.autocommit = False
    cur.execute('create table if not exists public._medida_local (x int)')
    con.commit()
    for modo in ('on', 'off'):
        t = []
        for i in range(40):
            t0 = time.perf_counter()
            cur.execute(f"set local synchronous_commit = {modo}")
            cur.execute('insert into public._medida_local values (%s)', (i,))
            con.commit()
            t.append(time.perf_counter() - t0)
        r['commit_' + modo] = statistics.median(t)
    cur.execute('drop table public._medida_local')
    con.commit()
    con.close()

    s = requests.Session()
    url = a.api.rstrip('/') + '/rest/v1/rpc/api'
    h = {'apikey': 'local'}
    for _ in range(60):                     # espera hasta 30 s a que el servidor local termine de arrancar
        try:
            s.post(url, json={'p': {'action': 'estado'}}, headers=h, timeout=2)
            break
        except requests.RequestException:
            time.sleep(0.5)
    try:
        t = []
        for _ in range(50):
            t0 = time.perf_counter(); s.post(url, json={'p': {'action': 'estado'}}, headers=h, timeout=30).json(); t.append(time.perf_counter() - t0)
        r['api_seguida'] = statistics.median(t)

        def una(_):
            t0 = time.perf_counter(); requests.post(url, json={'p': {'action': 'estado'}}, headers=h, timeout=60).json(); return time.perf_counter() - t0
        with cf.ThreadPoolExecutor(100) as ex:
            t = sorted(ex.map(una, range(100)))
        r['api_paralela_p50'], r['api_paralela_p95'] = t[49], t[94]
    except requests.RequestException as e:
        print(f'⚠ La API no responde en {a.api}: {e}. ¿Está corriendo local/servidor_local.py?')

    print('\nMEDICIÓN LOCAL')
    print(f"  1. Abrir una conexión ............ {ms(r['conexion'])}")
    print(f"  2. Consulta mínima ............... {ms(r['consulta'])}")
    print(f"  3. Confirmar esperando el disco .. {ms(r['commit_on'])}   ·   sin esperarlo: {ms(r['commit_off'])}")
    if 'api_seguida' in r:
        print(f"  4. API, 50 seguidas (mediana) .... {ms(r['api_seguida'])}")
        print(f"  5. API, 100 a la vez ............. p50 {ms(r['api_paralela_p50'])} · p95 {ms(r['api_paralela_p95'])}")

    print('\nDIAGNÓSTICO')
    hallazgos = []
    if r['commit_on'] > 0.008:
        hallazgos.append(f"La escritura en disco es lenta ({ms(r['commit_on'])} por confirmación). Las inscripciones de una misma actividad se confirman en fila, "
                         "así que este tiempo se multiplica. Causa típica en Windows: el antivirus revisa la carpeta de datos de PostgreSQL. "
                         "Solución local: el servidor local ya usa commit sin esperar el disco (no uses --commit-seguro), o excluye del antivirus la carpeta "
                         "data de PostgreSQL (por ejemplo C:\\Program Files\\PostgreSQL\\16\\data).")
    if r['conexion'] > 0.15:
        hallazgos.append(f"Abrir una conexión tarda {ms(r['conexion'])} (normal en Windows). No afecta a la carga: el servidor local abre todas las del pool al arrancar y las conserva.")
    if 'api_seguida' in r and r['api_seguida'] > 0.03:
        hallazgos.append(f"Cada llamada a la API tarda {ms(r['api_seguida'])} aunque la base responde en {ms(r['consulta'])}: es la espera del ACK retrasado de TCP. "
                         "El servidor local del Sprint 1 la evita con TCP_NODELAY; si ves esto, el servidor que corre es una versión anterior: reinícialo.")
    if 'api_paralela_p95' in r and r['api_paralela_p95'] > 2:
        hallazgos.append('La API se pone en fila con 100 llamadas a la vez: el límite está en el servidor local de Python, no en la base. Para medir de verdad, usa Supabase (Sprint 4).')
    if not hallazgos:
        hallazgos.append('Nada anormal: si la prueba de carga sigue lenta, envía esta salida a la conversación de diseño.')
    for x in hallazgos:
        print('  · ' + x)
    print('\nNinguna de estas cifras representa a Supabase: la medición que cuenta es la del Sprint 4 en el proyecto real.')


if __name__ == '__main__':
    main()
