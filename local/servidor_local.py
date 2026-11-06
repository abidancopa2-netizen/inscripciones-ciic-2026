#!/usr/bin/env python3
"""
SERVIDOR LOCAL (opcional, para quien programe): imita lo que hace Supabase con la función api()
y sirve las páginas de docs/, para probar todo en tu computadora sin cuenta de Supabase.

  1) PostgreSQL 15+ local:
       createdb ciic
       psql -d ciic -f local/supabase_local.sql -f supabase/01_esquema.sql -f supabase/02_api.sql
       python supabase/excel_a_sql.py datos_prueba_CIIC2026_v4.xlsx 03_datos.sql && psql -d ciic -f 03_datos.sql
       psql -d ciic -c "select privado.crear_clave_admin();"        # copia la clave
  2) pip install psycopg2-binary
     python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787
  3) Página: http://127.0.0.1:8787/        Panel: http://127.0.0.1:8787/panel.html
     Tester: python tester/tester.py --api http://127.0.0.1:8787 --anon local --key LA_CLAVE --web http://127.0.0.1:8787/

Imita a Supabase en lo que importa: cada llamada usa el rol "anon" (o "authenticated" con sesión), con
statement_timeout de 3 s, en un pool de conexiones limitado (--conexiones, 60 por defecto), y pasa las
cabeceras como un proxy: agrega la IP del cliente al final de x-forwarded-for y deja pasar
cf-connecting-ip y x-real-ip si vienen (para probar privado.red(), §8).

Rendimiento en local (no representa a Supabase):
  · El pool abre todas sus conexiones al arrancar y las conserva (minconn = maxconn = --conexiones).
    psycopg2 CIERRA cada conexión devuelta que supere minconn; con minconn = 1, casi cada llamada abría una
    conexión nueva, y getconn la abre dentro del candado del pool. En Windows (≈40 ms por conexión, un
    proceso por conexión) eso ponía en fila toda la carga: era la causa del p95 de 20 s (hallado en el Sprint 1).
  · Por defecto cada llamada usa synchronous_commit = off: no espera la escritura en disco del registro
    (en Windows, con antivirus, puede costar decenas de ms y poner en fila las inscripciones). No cambia
    ningún resultado; solo la durabilidad ante un apagón, que en local no importa. --commit-seguro lo apaga.
  · TCP_NODELAY en cada conexión: evita la espera del ACK retrasado entre cabeceras y cuerpo (hasta 200 ms
    por llamada en Windows).
  · Diagnóstico de la lentitud: python local/medir_local.py --dsn "…" --api http://127.0.0.1:8787

SOLO EN LOCAL, para probar el panel con cuentas sin Supabase Auth:
  Authorization: Bearer local:<uuid-de-auth.users>:aal2     → sesión de esa cuenta con código verificado
  X-Red-Prueba: 10.0.0.7                                     → simula otra IP (pruebas del límite por red)
"""
import argparse
import sys
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import psycopg2
from psycopg2.pool import ThreadedConnectionPool

RAIZ = Path(__file__).resolve().parent.parent / 'docs'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dsn', default='dbname=ciic')
    ap.add_argument('--puerto', type=int, default=8787)
    ap.add_argument('--conexiones', type=int, default=60)
    ap.add_argument('--commit-seguro', action='store_true', help='espera la escritura en disco en cada llamada (como un servidor real)')
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(line_buffering=True)      # con la salida redirigida a un archivo, que se vea al instante
    except AttributeError:
        pass

    import time as _t
    t0 = _t.perf_counter()
    pool = ThreadedConnectionPool(a.conexiones, a.conexiones, a.dsn)      # abre y conserva todas: nunca abre una en plena carga
    abiertas = range(a.conexiones)
    arranque = _t.perf_counter() - t0
    # Como Supabase (session_preload_libraries del rol authenticator): safeupdate rechaza DELETE/UPDATE sin WHERE.
    # Si la extensión no está instalada (por ejemplo en Windows), el tester lo cubre con su escáner (bloque R).
    conexiones = [pool.getconn() for _ in abiertas]
    safeupdate = True
    for con in conexiones:
        try:
            with con.cursor() as cur:
                cur.execute("load 'safeupdate'")
            con.commit()
        except psycopg2.Error:
            con.rollback()
            safeupdate = False
    for con in conexiones:
        pool.putconn(con)
    cupos = threading.BoundedSemaphore(a.conexiones)

    class H(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'
        # Sin esto, cabeceras y cuerpo salen en dos paquetes y el ACK retrasado del sistema añade ~40 ms (Linux)
        # o hasta ~200 ms (Windows) a CADA llamada.
        disable_nagle_algorithm = True

        def log_message(self, *args):
            pass

        def cors(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Headers', 'apikey, authorization, content-type, x-client-info, x-red-prueba, x-forwarded-for, cf-connecting-ip, x-real-ip')
            self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

        def enviar(self, codigo, cuerpo: bytes, tipo='application/json'):
            self.send_response(codigo)
            self.cors()
            self.send_header('Content-Type', tipo)
            self.send_header('Content-Length', str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def do_OPTIONS(self):
            self.enviar(204, b'')

        def do_GET(self):
            ruta = self.path.split('?')[0]
            if ruta == '/':
                ruta = '/index.html'
            if ruta == '/config.js':                  # la página local apunta a este mismo servidor
                txt = (RAIZ / 'config.js').read_text(encoding='utf-8')
                host = f'http://{self.headers.get("Host")}'
                import re
                txt = re.sub(r"API_URL\s*:\s*'[^']*'", f"API_URL: '{host}'", txt)
                txt = re.sub(r"ANON_KEY\s*:\s*'[^']*'", "ANON_KEY: 'local'", txt)
                txt = re.sub(r"(?m)^(\s*)MODO\s*:\s*'[^']*'", r"\1MODO: 'real'", txt)   # el servidor local sirve la base de verdad
                return self.enviar(200, txt.encode('utf-8'), 'application/javascript; charset=utf-8')
            f = (RAIZ / ruta.lstrip('/')).resolve()
            if RAIZ in f.parents and f.is_file():
                return self.enviar(200, f.read_bytes(), (mimetypes.guess_type(str(f))[0] or 'text/plain') + '; charset=utf-8')
            self.enviar(404, b'{"message":"not found"}')

        def do_POST(self):
            largo = int(self.headers.get('Content-Length') or 0)
            cuerpo = self.rfile.read(largo)
            if self.path.split('?')[0] != '/rest/v1/rpc/api':
                return self.enviar(404, b'{"code":"PGRST202","message":"function not found"}')
            if not self.headers.get('apikey'):
                return self.enviar(401, b'{"message":"No API key found in request"}')
            try:
                p = json.loads(cuerpo or b'{}').get('p')
            except ValueError:
                return self.enviar(400, b'{"code":"PGRST102","message":"Empty or invalid json"}')
            with cupos:
                con = pool.getconn()
                try:
                    con.autocommit = False
                    with con.cursor() as cur:
                        auth = self.headers.get('Authorization') or ''
                        claims = {'role': 'anon'}
                        if auth.startswith('Bearer local:'):
                            _, uid, aal = (auth[len('Bearer '):].split(':') + ['aal1'])[:3]
                            claims = {'role': 'authenticated', 'sub': uid, 'aal': aal}
                        # Como un proxy: X-Red-Prueba simula otro cliente; si no, agrega la IP real al final de x-forwarded-for.
                        if self.headers.get('X-Red-Prueba'):
                            xff = self.headers.get('X-Red-Prueba')
                        else:
                            previa = (self.headers.get('X-Forwarded-For') or '').strip()
                            xff = (previa + ', ' if previa else '') + self.client_address[0]
                        cab = {'x-forwarded-for': xff}
                        for k in ('cf-connecting-ip', 'x-real-ip'):
                            if self.headers.get(k):
                                cab[k] = self.headers.get(k)
                        cur.execute("select set_config('request.jwt.claims', %s, true), set_config('request.headers', %s, true)",
                                    (json.dumps(claims), json.dumps(cab)))
                        cur.execute("set local role " + ('authenticated' if claims['role'] == 'authenticated' else 'anon') + "; set local statement_timeout = '3s'"
                                    + ("" if a.commit_seguro else "; set local synchronous_commit = off"))
                        cur.execute('select public.api(%s::jsonb)', (json.dumps(p),))
                        r = cur.fetchone()[0]
                    con.commit()
                    self.enviar(200, json.dumps(r, ensure_ascii=False).encode('utf-8'))
                except psycopg2.Error as e:
                    con.rollback()
                    self.enviar(500, json.dumps({'code': e.pgcode, 'message': str(e)}).encode('utf-8'))
                finally:
                    pool.putconn(con)

    print(f'Servidor local en http://127.0.0.1:{a.puerto}/  (API: /rest/v1/rpc/api · {len(abiertas)} conexiones abiertas en {arranque:.1f} s'
          + ('' if a.commit_seguro else ' · commit sin esperar el disco')
          + (' · safeupdate cargado, como Supabase' if safeupdate else ' · sin safeupdate: lo cubre el escáner del tester') + ')', flush=True)
    class Servidor(ThreadingHTTPServer):
        request_queue_size = 1024              # muchas conexiones a la vez, como en la avalancha
        daemon_threads = True

    Servidor(('127.0.0.1', a.puerto), H).serve_forever()


if __name__ == '__main__':
    main()
