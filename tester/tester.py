#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════════
  TESTER AUTOMÁTICO · Inscripciones CIIC 2026 · v5.1 (Supabase)
  Prueba el sistema REAL ya instalado: la API (public.api), y, si das la URL
  de la página, la página y el panel en un navegador.

  Modo completo (la base debe estar en modo PRUEBA): ~180 pruebas. Inscribe
  personas del padrón de prueba y al final borra SOLO lo que inscribió y deja
  configuración, cupos y actividades como estaban (la ronda queda más alta).
  Modo lectura: no cambia nada; sirve en producción.

  Uso:
    python tester/tester.py                         # lee API_URL y ANON_KEY de docs/config.js
    python tester/tester.py --modo lectura
    python tester/tester.py --api http://127.0.0.1:8787 --anon local --key CLAVE --local --dsn "dbname=ciic"
      --local   activa pruebas que solo el servidor local permite (otra IP simulada)
      --dsn     además, prueba la pestaña Equipo creando cuentas de prueba en auth.users (solo local)
  Variables de entorno: API_URL, ANON_KEY, ADMIN_KEY, WEB_URL, MODO, CARGA_PERSONAS.
  Referencia: documentación v5.1, sección 18.
════════════════════════════════════════════════════════════════════════
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import uuid
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
NOMBRE = 'TEST Tester Automático'
NOMBRES, APELLIDOS = 'Persona', 'De Prueba Tester'
VERDE, ROJO, AMARILLO, GRIS, AZUL, FIN = '\033[32m', '\033[31m', '\033[33m', '\033[90m', '\033[34m', '\033[0m'


def pinta(c, t):
    return f'{c}{t}{FIN}' if sys.stdout.isatty() else t


class Abortar(Exception):
    pass


# ─────────────────────────────────────────────────────────────────────────
#  Cliente: misma política que la página (reintenta solo con "ocupado" o sin red)
# ─────────────────────────────────────────────────────────────────────────
ESCRITURAS = {'registrar', 'panel_config', 'panel_actividad', 'panel_anular', 'panel_inscribir', 'panel_cambiar', 'panel_padron_agregar',
              'panel_padron_quitar', 'panel_crear', 'panel_editar', 'panel_quitar', 'panel_horarios', 'panel_cruce', 'panel_equipo_rol',
              'panel_equipo_activo', 'panel_grupo_marcar', 'panel_sincronizar', 'panel_padron_importar', 'panel_actividades_importar',
              'panel_vaciar_prueba', 'panel_preparar_produccion'}
SIN = '__sin__'      # solicitud=SIN: no se envía (para probar que la base la exige)


def sin_where(src):
    """Sentencias DELETE/UPDATE sin WHERE en el código de una función (Supabase las rechaza con safeupdate, error 21000).
    Se ignoran comentarios y literales; INSERT … ON CONFLICT DO UPDATE no cuenta (no es un UPDATE)."""
    txt = re.sub(r'/\*.*?\*/', ' ', src, flags=re.S)
    txt = re.sub(r'--[^\n]*', ' ', txt)
    txt = re.sub(r"'(?:[^']|'')*'", "''", txt)
    hallados = []
    for seg in txt.split(';'):
        t = ' '.join(seg.lower().split())
        for m in re.finditer(r'\bdelete\s+from\b|(?<!do )(?<!for )(?<!key )\bupdate\s+(?:only\s+)?[a-z_][a-z0-9_."]*(?:\s+(?:as\s+)?[a-z_]\w*)?\s+set\b', t):
            resto = t[m.end():]
            if m.start() > 0 and t[:m.start()].count('(') > t[:m.start()].count(')'):
                # dentro de un paréntesis (CTE, subconsulta): su WHERE está hasta el paréntesis que lo cierra
                prof, fin = 0, len(resto)
                for i, ch in enumerate(resto):
                    prof += ch == '('
                    prof -= ch == ')'
                    if prof < 0:
                        fin = i
                        break
                resto = resto[:fin]
            while re.search(r'\([^()]*\)', resto):          # el WHERE de una subconsulta no cuenta: Sprint 3.2, punto ciego
                resto = re.sub(r'\([^()]*\)', ' ', resto)
            if not re.search(r'\bwhere\b', resto):
                hallados.append(t[m.start():m.start() + 70])
    return hallados


CASOS_ESCANER = [   # (código, ¿debe detectarse?) · el tester se prueba a sí mismo antes de revisar las funciones
    ("delete from public.inscripciones;", True),
    ("delete from public.inscripciones where true;", False),
    ("update public.config set abierto = false;", True),
    ("update public.config set abierto = false where id = 1;", False),
    ("update public.actividades a set inscritos = (select count(*) from x where x.id = a.id);", True),
    ("update public.actividades a set inscritos = (select count(*) from x where x.id = a.id) where a.id = 'V';", False),
    ("update t set a = coalesce((select max(b) from u where u.c = t.c), 0);", True),
    ("delete from public.padron where documento in (select d from t where d like 'Z%');", False),
    ("delete from public.padron returning (select 1 where true);", True),
    ("insert into t (a) values (1) on conflict (a) do update set a = excluded.a;", False),
    ("insert into t (a) values (1) on conflict on constraint t_pk do update set b = 2;", False),
    ("-- delete from t;\nselect 1;", False),
    ("/* update t set a = 1; */ select 1;", False),
    ("perform x('delete from t;');", False),
    ("with borrar as (delete from t where id = 1 returning id) select count(*) from borrar;", False),
    ("with borrar as (delete from t returning id) select count(*) from borrar where id > 0;", True),
    ("update only t set a = 1 where b = 2;", False),
    ("update t as x set a = 1;", True),
    ("delete from t using u where t.id = u.id;", False),
    ("for r in select * from t loop update t set a = r.a where id = r.id; end loop;", False),
    ("execute format('update %I set a = 1', tbl);", False),
    ("if exists (select 1 from t where a) then delete from t; end if;", True),
]


class Cliente:
    def __init__(self, api: str, anon: str):
        self.url = api.rstrip('/') + '/rest/v1/rpc/api'
        self.anon = anon
        self.ronda = None
        self.latencias, self.reintentos, self.saturado, self.motivos, self.ejemplos = [], 0, 0, {}, {}
        self._c = threading.Lock()
        self.s = requests.Session()
        # Conexiones que se reutilizan: con el pool de 10 de requests, 1000 personas abrían una conexión TLS nueva por llamada,
        # y desde una PC con Windows eso agotaba archivos (OSError 24) y conexiones (SSLEOFError) antes que el sistema (Sprint 4).
        from requests.adapters import HTTPAdapter
        for esquema in ('https://', 'http://'):
            self.s.mount(esquema, HTTPAdapter(pool_connections=4, pool_maxsize=1200))

    def llamar(self, datos: dict, paciente=False, cab=None, ronda_auto=True) -> dict:
        d = dict(datos)
        if d.get('action') in ('verificar', 'registrar') and 'dispositivo' not in d:
            d['dispositivo'] = 't-' + uuid.uuid4().hex[:16]            # cada llamada, un dispositivo: no gasta el límite
        if d.get('action') == 'registrar' and 'ronda' not in d and ronda_auto:
            d['ronda'] = self.ronda
        if d.get('solicitud') == SIN:
            del d['solicitud']
        elif d.get('action') in ESCRITURAS and 'solicitud' not in d:
            d['solicitud'] = str(uuid.uuid4())          # los reintentos de abajo reusan la misma: R-32
        h = {'apikey': self.anon, **({'Authorization': f'Bearer {self.anon}'} if self.anon.startswith('eyJ') else {}), **(cab or {})}
        inicio, ultimo = time.perf_counter(), {}
        for i in range(1, (400 if paciente else 4) + 1):
            t0 = time.perf_counter()
            try:
                r = self.s.post(self.url, json={'p': d}, headers=h, timeout=90)
                with self._c:
                    self.latencias.append(time.perf_counter() - t0)
                try:
                    j = r.json()
                except ValueError:
                    j = None
                if not isinstance(j, dict) or ('tipo' not in j and 'ok' not in j):
                    with self._c:
                        self.saturado += 1
                    ultimo = {'ok': False, 'tipo': 'respuesta_no_api', 'mensaje': f'HTTP {r.status_code}: {r.text[:140]}'}
                elif j.get('tipo') == 'ocupado':
                    ultimo = j
                else:
                    if 'ronda' in j and j.get('tipo') in ('estado', 'ok', 'recargar'):
                        self.ronda = j['ronda']
                    if j.get('tipo') == 'recargar' and ronda_auto and 'ronda' not in datos and i == 1:
                        d['ronda'] = j['ronda']
                        continue
                    return j
            except requests.RequestException as e:
                ultimo = {'ok': False, 'tipo': 'sin_conexion', 'mensaje': str(e)[:200]}
            if paciente and time.perf_counter() - inicio > 180:
                break
            with self._c:
                self.reintentos += 1
                k = f"{d.get('action')}: {ultimo.get('tipo')}" + (f" {ultimo['motivo']}" if ultimo.get('motivo') else '')
                self.motivos[k] = self.motivos.get(k, 0) + 1
                if k not in self.ejemplos and ultimo.get('mensaje'):        # la causa del primero de cada tipo, para el reporte
                    self.ejemplos[k] = re.sub(r'\s+', ' ', str(ultimo['mensaje']))[:160]
            time.sleep(0.5 + random.random() * 1.5 if paciente else 0.6 * i)
        return ultimo


class Tester:
    def __init__(self, a):
        self.a = a
        self.cli = Cliente(a.api, a.anon)
        self.key = a.key
        self.res, self.seccion_actual = [], ''
        self.usados, self.padron_nuevo = set(), set()
        self.cfg0, self.acts0, self.creadas, self.cruces_nuevos = None, {}, [], set()
        self.salida = Path(a.salida)
        self.salida.mkdir(parents=True, exist_ok=True)

    # ── utilidades de reporte ──
    def seccion(self, t):
        self.seccion_actual = t
        print(pinta(AZUL, f'\n▶ {t}'))

    MASCARAS = [
        (re.compile(r"(['\"](?:nombre|nombres|apellidos)['\"]\s*:\s*['\"])[^'\"]*"), r'\1•••'),
        (re.compile(r'([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})'), r'\1•••@\2'),
        (re.compile(r'(\+\d{2,3})\d{3,}(\d{3})\b'), r'\1•••\2'),
        (re.compile(r'\bCIIC-[A-Z0-9]{5}\b'), 'CIIC-•••••'),
        (re.compile(r'\b\d{1,3}\.\d{3}\.\d{3}\b|\b\d{4}[.\-]\d{4}\b'), '••••••'),      # documento con puntos o guion
        (re.compile(r'\b([A-Z]{1,2})\d{5,10}\b'), r'\1•••••'),
        (re.compile(r'\b(\d{2})\d{2,8}(\d{2}[A-Z]?)\b(?![-:])'), r'\1•••\2'),
    ]

    def mascara(self, v):
        """Datos personales fuera de los reportes y del registro de GitHub (el repositorio es público)."""
        t = str(v)
        if self.a.sin_mascara:
            return t
        for patron, cambio in self.MASCARAS:
            t = patron.sub(cambio, t)
        return t

    def ok(self, nombre, cond, esperado='', obtenido='', detalle=''):
        nombre, esperado, obtenido, detalle = self.mascara(nombre), self.mascara(esperado), self.mascara(obtenido), self.mascara(detalle) if detalle else detalle
        self.res.append({'bloque': self.seccion_actual, 'prueba': nombre, 'ok': bool(cond), 'esperado': str(esperado), 'obtenido': str(obtenido)})
        print(('  ' + pinta(VERDE, '✔ PASA ') if cond else '  ' + pinta(ROJO, '✘ FALLA')) + f'  {nombre}')
        if not cond:
            print(pinta(GRIS, f'           esperado: {esperado}  ·  obtenido: {obtenido}'))
            if detalle:
                print(pinta(GRIS, f'           detalle : {str(detalle)[:220]}'))
        return bool(cond)

    def tipo(self, nombre, r, esperado):
        esp = esperado if isinstance(esperado, (list, tuple)) else [esperado]
        return self.ok(nombre, r.get('tipo') in esp, ' o '.join(esp), r.get('tipo'), r.get('mensaje') or r.get('detalle'))

    def omitir(self, nombre, motivo):
        self.res.append({'bloque': self.seccion_actual, 'prueba': nombre, 'ok': None, 'esperado': '', 'obtenido': motivo})
        print('  ' + pinta(AMARILLO, '○ OMITE') + f'  {nombre} · {motivo}')

    # ── llamadas ──
    def api(self, **d):
        return self.cli.llamar(d)

    def panel(self, accion, **d):
        return self.cli.llamar({'action': accion, 'key': self.key, **d})

    def estado(self):
        return self.cli.llamar({'action': 'estado'})

    def resumen(self):
        r = self.panel('panel_resumen')
        if r.get('tipo') != 'panel':
            raise Abortar('El panel no responde: ' + str(r.get('mensaje')))
        return r

    def acts(self):
        return {a['id']: dict(a, cupo=a['capacidad']) for a in self.resumen()['actividades']}

    def cerrar(self):
        r = self.panel('panel_config', abierto=False, confirmar=True)
        self.estado()
        return r

    def abrir(self):
        r = self.panel('panel_config', abierto=True)
        self.estado()
        return r

    def config(self, **c):
        """Cambia configuración aunque quite opciones: cierra si hace falta y deja el estado de apertura como estaba."""
        r = self.panel('panel_config', **c)
        if r.get('tipo') == 'requiere_cierre':
            self.cerrar()
            r = self.panel('panel_config', **c)
            self.abrir()
        return r

    @staticmethod
    def celular(doc):
        return '9' + str(int(hashlib.md5(doc.encode()).hexdigest(), 16))[-8:]

    def reg(self, doc, ids, **kw):
        d = {'action': 'registrar', 'dni': doc, 'nombres': kw.pop('nombres', NOMBRES), 'apellidos': kw.pop('apellidos', APELLIDOS),
             'correo': kw.pop('correo', f'prueba.{doc.lower()}@tester.edu.pe'), 'pais': 'PE', 'celular': kw.pop('celular', self.celular(doc)),
             'aceptaPrivacidad': kw.pop('aceptaPrivacidad', True), 'aceptaWhatsapp': kw.pop('acepta', True), 'actividades': ids, **kw}
        paciente = d.pop('paciente', False)
        r = self.cli.llamar(d, paciente=paciente, ronda_auto='ronda' not in kw)
        if r.get('tipo') == 'registrado':
            self.usados.add(r['doc'])
        return r

    def doc_prueba(self):
        """Documento que ninguna persona real tiene (ZQX + 7 dígitos): el tester puede crearlo y borrarlo sin riesgo.
        admin_limpiar solo borra del padrón documentos con ese formato (migración 05)."""
        while True:
            d = 'ZQX' + str(random.randint(0, 9999999)).zfill(7)
            if d not in self.padron_nuevo:
                self.padron_nuevo.add(d)
                return d

    def inscribir_panel(self, doc, ids, rol=None, **kw):
        d = {'dni': doc, 'nombres': NOMBRES, 'apellidos': APELLIDOS, 'correo': f'panel.{doc.lower()}@tester.edu.pe', 'celular': self.celular(doc),
             'pais': 'PE', 'aceptaPrivacidad': True, 'aceptaWhatsapp': True, 'actividades': ids, **kw}
        return self.cli.llamar({'action': 'panel_inscribir', 'key': self.key, **({'comoRol': rol} if rol else {}), **d})

    def codigo_de(self, doc):
        """R-31: la respuesta pública ya no trae el código; el equipo lo ve en el panel."""
        b = self.panel('panel_buscar', q=doc)
        conf = [x for x in b.get('registros', []) if x.get('estado') == 'CONFIRMADO']
        return conf[0]['codigo'] if conf else None

    def sql(self):
        """Conexión directa (solo en local, con --dsn) para las pruebas de privilegios, protección masiva y bitácora."""
        if not self.a.dsn:
            return None
        import psycopg2
        con = psycopg2.connect(self.a.dsn)
        con.autocommit = False
        return con

    def tomar(self, etapa=1):
        lista = self.muestra[str(etapa)]
        while lista:
            d = lista.pop(0)
            if d not in self.usados:
                self.usados.add(d)
                return d
        raise Abortar(f'Se acabaron los documentos de prueba de la Etapa {etapa}.')

    def dias(self, acts):
        return sorted({a['fecha'] for a in acts.values() if a['publicada']}, key=lambda f: (f[6:], f[3:5], f[:2]))

    def libre(self, acts, tipo, fecha, excluir=(), minimo=1):
        cand = [a for a in acts.values() if a['publicada'] and a['tipo'] == tipo and a['fecha'] == fecha and a['id'] not in excluir
                and a['disponibles'] >= minimo]
        if not cand:
            raise Abortar(f'No hay {tipo} con cupo el {fecha} para armar combinaciones.')
        return max(cand, key=lambda a: a['disponibles'])

    def combo(self, acts=None, visita=True, excluir=()):
        acts = acts or self.acts()
        d1, d2 = self.dias(acts)[:2]
        a = self.libre(acts, 'VISITA' if visita else 'TALLER', d1, excluir)
        b = self.libre(acts, 'TALLER', d2, excluir)
        return [a['id'], b['id']]

    # ═════════════════════════════════════════════════════════════════════
    def preparar(self):
        self.seccion('Preparación')
        for _ in range(60):                       # hasta 30 s: en Windows el servidor local tarda en abrir sus conexiones
            e = self.estado()
            if e.get('tipo') == 'estado':
                break
            time.sleep(0.5)
        self.cli.reintentos, self.cli.motivos, self.cli.ejemplos = 0, {}, {}      # la espera del arranque no cuenta como reintento
        if not self.ok('La API responde', e.get('tipo') == 'estado', 'estado', e.get('tipo'), e.get('mensaje')):
            raise Abortar('La API no responde. Revisa API_URL y ANON_KEY en docs/config.js y que 02_api.sql esté instalado.')
        if not self.ok('Backend v5.5 (Sprint 1 o posterior)', str(e.get('version', '')).startswith('5.5'), '5.5-s1 o mayor', e.get('version')):
            raise Abortar('El backend no tiene el Sprint 1: corre supabase/03_sprint1_seguridad.sql después de 01 y 02.')
        p = self.cli.llamar({'action': 'admin_ping', 'key': self.key})
        if p.get('tipo') == 'admin_deshabilitado':
            raise Abortar('No hay ADMIN_KEY. En el SQL Editor: select privado.crear_clave_admin(); y cópiala al secreto ADMIN_KEY.')
        if p.get('tipo') != 'admin':
            raise Abortar('La ADMIN_KEY no coincide: vuelve a copiarla al secreto ADMIN_KEY.')
        if not self.ok('Modo PRUEBA', p['config']['modo'] == 'PRUEBA', 'PRUEBA', p['config']['modo']):
            raise Abortar('La base está en modo PRODUCCION: usa --modo lectura, o en el SQL Editor: update config set modo = \'PRUEBA\';')
        self.cfg0 = p['config']
        self.acts0 = self.acts()
        m = self.cli.llamar({'action': 'admin_muestra', 'key': self.key, 'n': 500})
        self.muestra, self.inexistente = m['etapas'], m['inexistente']
        print(pinta(GRIS, f"  … padrón disponible: E1 {len(self.muestra['1'])} · E2 {len(self.muestra['2'])} · E3 {len(self.muestra['3'])}"))
        self.cerrar()
        self.panel('panel_config', etapas=[1, 2], etapasVisita=[1], dosTalleres=True, limiteRed=100000, limiteDispositivo=4)
        self.panel('panel_horarios', mismoDia=False, margenMin=30)
        self.abrir()

    def a_conexion(self, solo_lectura=False):
        self.seccion('A · Conexión')
        e = self.estado()
        self.ok('estado trae ronda, cierraEn, etapasVisita y refresco', all(k in e for k in ('ronda', 'cierraEn', 'etapasVisita', 'refresco')), 'campos', list(e))
        r = self.api(action='actividades')
        acts = r.get('actividades', [])
        self.ok('Hay actividades publicadas de al menos 2 días', len({a['fecha'] for a in acts}) >= 2, '≥ 2 días', len({a['fecha'] for a in acts}))
        self.ok('La lista pública nunca trae el enlace del grupo (R-16)', all('grupo' not in a for a in acts), 'sin grupo', 'con grupo')
        self.ok('Ninguna actividad con sobrecupo', all(a['inscritos'] <= a['capacidad'] for a in acts), 'ninguna', '')
        self.tipo('El panel sin sesión pide iniciar sesión', self.api(action='panel_resumen'), 'sin_sesion')
        self.tipo('El panel rechaza una clave falsa', self.api(action='panel_resumen', key='clave-falsa'), 'no_autorizado')
        self.tipo('Acción desconocida', self.api(action='hackear'), 'accion_invalida')

    def b_documentos(self):
        self.seccion('B · Documentos')
        for d in ['12 3', '', 'ABCDEFGHI', '1234567890123', '<script>']:
            r = self.api(action='verificar', dni=d)
            self.ok(f'Formato inválido «{d}» → formato con intentos restantes', r.get('tipo') == 'formato' and 'intentosRestantes' in r, 'formato', r.get('tipo'))
        r = self.api(action='verificar', dni=self.inexistente)
        self.ok('Documento que no está → no_encontrado', r.get('tipo') == 'no_encontrado' and r.get('intentosRestantes') == 3, 'no_encontrado · 3', f"{r.get('tipo')} · {r.get('intentosRestantes')}")
        d = self.muestra['1'][0]
        for variante in (f' {d} ', f'{d[:2]}.{d[2:5]}.{d[5:]}', f'{d[:4]}-{d[4:]}'):
            r = self.api(action='verificar', dni=variante)
            self.ok('Variante con ' + ('espacios' if ' ' in variante else 'puntos' if '.' in variante else 'guion') + ' se normaliza al mismo documento',
                    r.get('tipo') == 'ok' and r.get('doc') == d, d, r.get('doc') or r.get('tipo'))
        if d.startswith('0') and d.isdigit():
            r = self.api(action='verificar', dni=int(d))
            self.ok('Enviado como número pierde el 0 y la base lo recupera', r.get('doc') == d, d, r.get('doc'))

    def c_etapas(self):
        self.seccion('C · Etapas de inscripción y de visitas (R-06, R-07)')
        d2, d3 = self.tomar(2), self.tomar(3)
        self.tipo('Etapa 3 sin inscripción → etapa_no_habilitada', self.api(action='verificar', dni=d3), 'etapa_no_habilitada')
        r = self.api(action='verificar', dni=d2)
        self.ok('Etapa 2 inscrita sin visitas → puedeVisita false', r.get('tipo') == 'ok' and r.get('puedeVisita') is False, 'ok · false', f"{r.get('tipo')} · {r.get('puedeVisita')}")
        acts = self.acts()
        self.tipo('Etapa 2 elige visita + taller → visita_no_habilitada', self.reg(d2, self.combo(acts)), 'visita_no_habilitada')
        self.tipo('Etapa 2 elige 2 talleres → registrado', self.reg(d2, self.combo(acts, visita=False)), 'registrado')
        self.tipo('Habilitar visitas para la Etapa 2 con el sistema abierto (agrega)', self.panel('panel_config', etapasVisita=[1, 2]), 'panel')
        r = self.api(action='verificar', dni=self.tomar(2))
        self.ok('Ahora la Etapa 2 puede elegir visitas', r.get('puedeVisita') is True, True, r.get('puedeVisita'))
        self.tipo('Quitar visitas a la Etapa 2 abierto → requiere_cierre (R-10)', self.panel('panel_config', etapasVisita=[1]), 'requiere_cierre')
        self.tipo('Habilitar la Etapa 3 abierto (agrega)', self.panel('panel_config', etapas=[1, 2, 3]), 'panel')
        self.ok('La Etapa 3 ya verifica', self.api(action='verificar', dni=d3).get('tipo') == 'ok', 'ok', '')
        self.tipo('Quitar la Etapa 3 abierto → requiere_cierre', self.panel('panel_config', etapas=[1, 2]), 'requiere_cierre')
        self.config(etapas=[1, 2], etapasVisita=[1])

    def d_combinaciones(self):
        self.seccion('D · Combinaciones y datos (R-02, R-03, R-13, R-14)')
        acts = self.acts()
        dia1, dia2 = self.dias(acts)[:2]
        v1 = self.libre(acts, 'VISITA', dia1)
        v2 = self.libre(acts, 'VISITA', dia2)
        t1 = self.libre(acts, 'TALLER', dia1)
        t2 = self.libre(acts, 'TALLER', dia2)
        d = self.tomar(1)
        self.ok('Una sola actividad → cantidad', self.reg(d, [v1['id']]).get('motivo') == 'cantidad', 'cantidad', '')
        self.ok('La misma actividad dos veces → cantidad', self.reg(d, [v1['id'], v1['id']]).get('motivo') == 'cantidad', 'cantidad', '')
        self.ok('Dos visitas → dos_visitas', self.reg(d, [v1['id'], v2['id']]).get('motivo') == 'dos_visitas', 'dos_visitas', '')
        self.ok('Mismo día con "una por día" → mismo_dia', self.reg(d, [v1['id'], t1['id']]).get('motivo') == 'mismo_dia', 'mismo_dia', '')
        ocultas = [a for a in acts.values() if not a['publicada']]
        if ocultas:
            self.tipo('Actividad oculta → no_disponible', self.reg(d, [ocultas[0]['id'], t2['id']]), 'no_disponible')
        else:
            self.omitir('Actividad oculta → no_disponible', 'no hay actividades ocultas')
        self.tipo('Nombres de 1 letra', self.reg(d, [v1['id'], t2['id']], nombres='A'), 'datos_invalidos')
        self.tipo('Sin apellidos', self.reg(d, [v1['id'], t2['id']], apellidos=''), 'datos_invalidos')
        self.tipo('Correo inválido', self.reg(d, [v1['id'], t2['id']], correo='no-es-correo'), 'datos_invalidos')
        r = self.reg(d, [v1['id'], t2['id']], correo='')
        self.ok('Sin correo → datos_invalidos en el campo correo (R-13)', r.get('tipo') == 'datos_invalidos' and r.get('campo') == 'correo', 'correo', r.get('campo'))
        self.tipo('Sin aceptar el aviso de privacidad', self.reg(d, [v1['id'], t2['id']], aceptaPrivacidad=False), 'sin_consentimiento')
        self.tipo('Celular peruano que no empieza con 9', self.reg(d, [v1['id'], t2['id']], celular='812345678'), 'celular_invalido')
        self.tipo('Sin consentimiento de WhatsApp', self.reg(d, [v1['id'], t2['id']], acepta=False), 'sin_consentimiento')
        r = self.reg(d, [v1['id'], t2['id']], nombres='=HYPERLINK("x")  María ')
        self.ok('Visita + taller válidos → registrado', r.get('tipo') == 'registrado', 'registrado', r.get('tipo'), r.get('mensaje'))
        self.ok('El comprobante trae las 2 actividades con su grupo', len(r.get('actividades', [])) == 2 and all('grupoModo' in x for x in r.get('actividades', [])), '2', '')
        b = self.panel('panel_buscar', q=d)
        self.ok('El nombre se guarda sin fórmula al inicio (CSV seguro)', b['registros'] and not b['registros'][0]['nombre'].startswith('='), 'sin =', b['registros'] and b['registros'][0]['nombre'])
        self.tipo('Volver a verificar → duplicado (solo el aviso, R-31)', self.api(action='verificar', dni=d), 'duplicado')
        self.tipo('Registrar otra vez → duplicado', self.reg(d, [v1['id'], t2['id']]), 'duplicado')

    def e_cupos(self):
        self.seccion('E · Cupos bajo concurrencia (R-04, R-05)')
        acts = self.acts()
        dia1, dia2 = self.dias(acts)[:2]
        v = self.libre(acts, 'VISITA', dia1, minimo=1)
        t = self.libre(acts, 'TALLER', dia2, minimo=20)
        self.cerrar()
        self.panel('panel_actividad', id=v['id'], cupo=v['inscritos'] + 15, confirmar=True)
        self.abrir()
        docs = [self.tomar(1) for _ in range(18)]
        with cf.ThreadPoolExecutor(18) as ex:
            rs = list(ex.map(lambda d: self.reg(d, [v['id'], t['id']], paciente=True), docs))
        tipos = [r.get('tipo') for r in rs]
        self.ok('18 personas por 15 cupos: entran 15 exactas', tipos.count('registrado') == 15, 15, tipos.count('registrado'), str(set(tipos)))
        self.ok('Las otras 3 reciben lleno', tipos.count('lleno') == 3, 3, tipos.count('lleno'))
        ahora = self.acts()
        self.ok(f"{v['id']} queda llena, sin sobrecupo", ahora[v['id']]['inscritos'] == ahora[v['id']]['cupo'], ahora[v['id']]['cupo'], ahora[v['id']]['inscritos'])
        self.ok('Todo o nada: el taller solo sumó 15', ahora[t['id']]['inscritos'] == t['inscritos'] + 15, t['inscritos'] + 15, ahora[t['id']]['inscritos'])
        d = self.tomar(1)
        otras = [self.libre(ahora, 'TALLER', dia1)['id'], t['id']]
        with cf.ThreadPoolExecutor(4) as ex:
            rs = list(ex.map(lambda ids: self.reg(d, ids, paciente=True), [otras, otras, [otras[0], self.libre(ahora, 'TALLER', dia2, excluir=[t['id']])['id']], otras]))
        self.ok('Mismo DNI 4 veces a la vez: una sola inscripción', [r.get('tipo') for r in rs].count('registrado') == 1, 1, [r.get('tipo') for r in rs].count('registrado'))

    def f_panel(self):
        self.seccion('F · Panel: cupos, cierre, anulación (R-10, R-11)')
        acts = self.acts()
        ids = self.combo(acts)
        d = self.tomar(1)
        self.tipo('Inscripción para las pruebas del panel', self.reg(d, ids), 'registrado')
        self.reg(self.tomar(1), ids)      # al menos 2 inscritos: así "bajar bajo los inscritos" siempre se puede probar
        a = self.acts()[ids[0]]
        r = self.panel('panel_actividad', id=a['id'], cupo=a['cupo'] + 5)
        self.ok('+5 con el sistema abierto se aplica (cupo final)', r.get('actividad', {}).get('capacidad') == a['cupo'] + 5, a['cupo'] + 5, r.get('actividad', {}).get('capacidad'))
        self.tipo('Con "delta" → valor_invalido: se envía el cupo final (D4)', self.panel('panel_actividad', id=a['id'], delta=5), 'valor_invalido')
        self.tipo('−5 con el sistema abierto → requiere_cierre', self.panel('panel_actividad', id=a['id'], cupo=a['cupo']), 'requiere_cierre')
        self.tipo('Ocultar con el sistema abierto → requiere_cierre', self.panel('panel_actividad', id=a['id'], publicada=False), 'requiere_cierre')
        ronda = self.estado()['ronda']
        self.tipo('Cerrar sin confirmar → advertencia', self.panel('panel_config', abierto=False), 'advertencia')
        self.tipo('Cerrar confirmando', self.cerrar(), 'panel')
        e = self.estado()
        self.ok('Cerrar sube la ronda en 1', e['ronda'] == ronda + 1 and e['abierto'] is False, ronda + 1, e['ronda'])
        r = self.panel('panel_actividad', id=a['id'], cupo=max(1, a['inscritos'] - 1))
        self.ok('Bajar bajo los inscritos (cerrado) → advertencia, no error', r.get('tipo') == 'advertencia' and r.get('minimo') == a['inscritos'], 'advertencia', r.get('tipo'))
        r = self.panel('panel_actividad', id=a['id'], cupo=max(1, a['inscritos'] - 1), confirmar=True)
        self.ok('Confirmando, queda en los inscritos (llena)', r.get('actividad', {}).get('capacidad') == a['inscritos'], a['inscritos'], r.get('actividad', {}).get('capacidad'))
        self.panel('panel_actividad', id=a['id'], cupo=a['cupo'])
        self.tipo('Abrir', self.abrir(), 'panel')
        b = self.panel('panel_buscar', q=d)
        self.ok('Buscar por documento', len(b.get('registros', [])) == 1, 1, len(b.get('registros', [])))
        b2 = self.panel('panel_buscar', q='+51' + self.celular(d))
        self.ok('Buscar por celular', any(x['doc'] == d for x in b2.get('registros', [])), d, '')
        antes = self.acts()
        self.tipo('Anular', self.panel('panel_anular', codigo=b['registros'][0]['codigo']), 'panel')
        despues = self.acts()
        self.ok('Anular libera los 2 cupos', all(despues[i]['inscritos'] == antes[i]['inscritos'] - 1 for i in ids), '−1 y −1', '')
        self.tipo('La persona puede volver a inscribirse', self.reg(d, ids), 'registrado')
        r = self.panel('panel_registros')
        self.ok('CSV de inscripciones con celular, origen y ronda', 'Celular' in r.get('encabezados', []) and 'Ronda' in r.get('encabezados', []), 'columnas', r.get('encabezados'))

    def h_cierre(self):
        self.seccion('H · Cerrar y depurar, ronda y aviso (R-09, R-27)')
        d = self.tomar(1)
        v = self.api(action='verificar', dni=d)
        ronda = v['ronda']
        ids = self.combo()
        self.cerrar()
        self.tipo('Confirmar con el sistema cerrado → cerrado', self.reg(d, ids, ronda=ronda), 'cerrado')
        self.tipo('Verificar con el sistema cerrado → cerrado', self.api(action='verificar', dni=self.tomar(1)), 'cerrado')
        self.abrir()
        self.tipo('Página vieja confirma tras reabrir → recargar', self.reg(d, ids, ronda=ronda), 'recargar')
        v2 = self.api(action='verificar', dni=d)
        self.ok('Al volver a verificar, recibe la ronda nueva', v2.get('ronda') == ronda + 1, ronda + 1, v2.get('ronda'))
        self.tipo('Con la ronda nueva, se inscribe', self.reg(d, ids, ronda=v2['ronda']), 'registrado')
        # cierre en medio de inscripciones simultáneas
        docs = [self.tomar(1) for _ in range(20)]
        ronda = self.estado()['ronda']
        acts = self.acts()
        dia1, dia2 = self.dias(acts)[:2]
        tall = [a['id'] for a in acts.values() if a['publicada'] and a['tipo'] == 'TALLER' and a['disponibles'] > 5]
        t1 = [x for x in tall if acts[x]['fecha'] == dia1][0]
        t2 = [x for x in tall if acts[x]['fecha'] == dia2][0]
        ins0 = acts[t1]['inscritos']
        with cf.ThreadPoolExecutor(21) as ex:
            fut = [ex.submit(self.reg, x, [t1, t2], ronda=ronda, paciente=True) for x in docs]
            time.sleep(0.05)
            ex.submit(self.cerrar).result()
            rs = [f.result() for f in fut]
        tipos = [r.get('tipo') for r in rs]
        self.ok('Cierre en medio de 20 inscripciones: cada una es registrado o cerrado', set(tipos) <= {'registrado', 'cerrado'}, '{registrado, cerrado}', set(tipos))
        self.ok('Los contadores coinciden con las registradas', self.acts()[t1]['inscritos'] == ins0 + tipos.count('registrado'), ins0 + tipos.count('registrado'), self.acts()[t1]['inscritos'])
        self.tipo('Después del cierre, nadie más entra', self.reg(self.tomar(1), [t1, t2], ronda=ronda), ['cerrado'])
        self.abrir()
        r = self.panel('panel_config', avisarCierreSeg=60)
        e = self.estado()
        self.ok('Avisar y cerrar: estado.cierraEn cuenta los segundos', e.get('cierraEn') is not None and 50 <= e['cierraEn'] <= 60, '≈60', e.get('cierraEn'))
        self.panel('panel_config', cancelarAviso=True)
        self.ok('Cancelar el aviso', self.estado().get('cierraEn') is None, None, self.estado().get('cierraEn'))
        ronda = self.estado()['ronda']
        self.panel('panel_config', avisarCierreSeg=2)
        time.sleep(2.6)
        e = self.estado()
        self.ok('Al llegar la hora se cierra solo y sube la ronda', e['abierto'] is False and e['ronda'] == ronda + 1, f'cerrado · {ronda + 1}', f"{e['abierto']} · {e['ronda']}")
        self.abrir()

    def i_horarios(self):
        self.seccion('I · Horarios y cruces (R-03)')
        self.tipo('Permitir combinar el mismo día (agrega, abierto)', self.panel('panel_horarios', mismoDia=True), 'panel')
        acts = self.acts()
        cruces = [c for c in self.resumen()['cruces'] if not c['permitido'] and {acts[c['a']]['tipo'], acts[c['b']]['tipo']} == {'VISITA', 'TALLER'}
                  and acts[c['a']]['publicada'] and acts[c['b']]['publicada'] and acts[c['a']]['disponibles'] > 0 and acts[c['b']]['disponibles'] > 0]
        if cruces:
            c = cruces[0]
            d = self.tomar(1)
            r = self.reg(d, [c['a'], c['b']])
            self.ok(f"{c['a']} + {c['b']} se cruzan → cruce", r.get('motivo') == 'cruce', 'cruce', r.get('motivo') or r.get('tipo'))
            self.tipo('Permitir ese par (agrega, abierto)', self.panel('panel_cruce', a=c['a'], b=c['b'], permitido=True), 'panel')
            self.cruces_nuevos.add((c['a'], c['b']))
            self.tipo('Con el par permitido, se inscribe', self.reg(d, [c['a'], c['b']]), 'registrado')
            self.tipo('Bloquear el par abierto → requiere_cierre', self.panel('panel_cruce', a=c['a'], b=c['b'], permitido=False), 'requiere_cierre')
        else:
            self.omitir('Pares que se cruzan', 'los datos no tienen una visita y un taller del mismo día que se crucen')
        compat = [(v, t) for v in acts.values() for t in acts.values() if v['tipo'] == 'VISITA' and t['tipo'] == 'TALLER' and v['fecha'] == t['fecha']
                  and v['publicada'] and t['publicada'] and v['disponibles'] > 0 and t['disponibles'] > 0
                  and not any({x['a'], x['b']} == {v['id'], t['id']} for x in self.resumen()['cruces'])]
        if compat:
            v, t = compat[0]
            self.tipo(f"Mismo día sin cruce ({v['id']} {v['inicio']}–{v['fin']} + {t['id']} {t['inicio']}–{t['fin']})", self.reg(self.tomar(1), [v['id'], t['id']]), 'registrado')
        else:
            self.omitir('Mismo día sin cruce', 'no hay un par compatible en los datos')
        self.tipo('Subir el margen abierto → requiere_cierre', self.panel('panel_horarios', margenMin=60), 'requiere_cierre')
        self.tipo('Volver a una por día abierto → requiere_cierre', self.panel('panel_horarios', mismoDia=False), 'requiere_cierre')
        self.cerrar()
        self.tipo('Cerrado: volver a una por día', self.panel('panel_horarios', mismoDia=False), 'panel')
        self.abrir()
        acts = self.acts()
        dia1 = self.dias(acts)[0]
        r = self.inscribir_panel(self.tomar(1),
                       [self.libre(acts, 'VISITA', dia1)['id'], self.libre(acts, 'TALLER', dia1)['id']])
        self.ok('El panel también respeta el horario (mismo_dia)', r.get('motivo') == 'mismo_dia', 'mismo_dia', r.get('motivo') or r.get('tipo'))

    def j_intentos(self):
        self.seccion('J · Límite de intentos (R-25)')
        disp = 'tj-' + uuid.uuid4().hex[:10]
        restantes = []
        for k in range(4):
            r = self.api(action='verificar', dni=str(20000000 + random.randint(0, 9999999)), dispositivo=disp)
            restantes.append(r.get('intentosRestantes'))
        self.ok('Cada fallo descuenta un intento: 3, 2, 1, 0', restantes == [3, 2, 1, 0], [3, 2, 1, 0], restantes)
        r = self.api(action='verificar', dni=self.muestra['1'][0], dispositivo=disp)
        self.ok('Al quinto, el dispositivo queda frenado', r.get('tipo') == 'demasiados_intentos' and r.get('motivo') == 'dispositivo', 'dispositivo', r.get('motivo') or r.get('tipo'))
        disp2 = 'tj-' + uuid.uuid4().hex[:10]
        for _ in range(3):
            self.api(action='verificar', dni=str(20000000 + random.randint(0, 9999999)), dispositivo=disp2)
        self.api(action='verificar', dni=self.muestra['1'][0], dispositivo=disp2)
        r = self.api(action='verificar', dni=str(20000000 + random.randint(0, 9999999)), dispositivo=disp2)
        self.ok('Un acierto reinicia el contador del dispositivo', r.get('intentosRestantes') == 3, 3, r.get('intentosRestantes'))
        if not self.a.local:
            self.omitir('Límite por red', 'solo con --local (simula otra IP)')
            return
        self.panel('panel_config', limiteRed=5)
        ip = f'10.{random.randint(1, 250)}.{random.randint(1, 250)}.{random.randint(1, 250)}'
        for _ in range(5):
            self.cli.llamar({'action': 'verificar', 'dni': str(20000000 + random.randint(0, 9999999))}, cab={'X-Red-Prueba': ip})
        r = self.cli.llamar({'action': 'verificar', 'dni': self.muestra['1'][0]}, cab={'X-Red-Prueba': ip})
        self.ok('30 (aquí 5) fallos desde una red con dispositivos distintos la frenan', r.get('motivo') == 'red', 'red', r.get('motivo') or r.get('tipo'))
        r = self.cli.llamar({'action': 'verificar', 'dni': self.muestra['1'][0]}, cab={'X-Red-Prueba': '10.255.0.1'})
        self.ok('Otra red sigue libre', r.get('tipo') == 'ok', 'ok', r.get('tipo'))
        self.panel('panel_config', limiteRed=100000)

    def k_soporte(self):
        self.seccion('K · Soporte: cambiar inscripción (R-20, R-21)')
        acts = self.acts()
        dia1, dia2 = self.dias(acts)[:2]
        v1 = self.libre(acts, 'VISITA', dia1)
        t2 = self.libre(acts, 'TALLER', dia2)
        llena = self.libre(acts, 'VISITA', dia2)
        t1 = self.libre(acts, 'TALLER', dia1)
        self.reg(self.tomar(1), [t1['id'], llena['id']])          # al menos 1 inscrito en la que se llenará
        d = self.tomar(1)
        r = self.reg(d, [v1['id'], t2['id']])
        cod = self.codigo_de(d)
        llena = self.acts()[llena['id']]
        self.cerrar()
        self.panel('panel_actividad', id=llena['id'], cupo=max(1, llena['inscritos']), confirmar=True)
        self.abrir()
        antes = self.acts()
        nuevas = [t1['id'], llena['id']]
        r = self.panel('panel_cambiar', codigo=cod, actividades=nuevas)
        self.ok('Cambiar a una actividad llena → advertencia con su ID', r.get('tipo') == 'advertencia' and llena['id'] in (r.get('ids') or []), llena['id'], r.get('ids') or r.get('tipo'))
        r = self.panel('panel_cambiar', codigo=cod, actividades=nuevas, ampliarCupo=True)
        self.ok('Con ampliarCupo, se cambia y conserva el código', r.get('tipo') == 'panel' and r.get('codigo') == cod, cod, r.get('codigo') or r.get('tipo'), r.get('mensaje'))
        despues = self.acts()
        self.ok('Contadores exactos: salen −1, entran +1', despues[v1['id']]['inscritos'] == antes[v1['id']]['inscritos'] - 1 and
                despues[t2['id']]['inscritos'] == antes[t2['id']]['inscritos'] - 1 and despues[t1['id']]['inscritos'] == antes[t1['id']]['inscritos'] + 1 and
                despues[llena['id']]['inscritos'] == antes[llena['id']]['inscritos'] + 1, 'exactos', '')
        self.ok('La llena se amplió en 1', despues[llena['id']]['cupo'] == antes[llena['id']]['cupo'] + 1, antes[llena['id']]['cupo'] + 1, despues[llena['id']]['cupo'])
        self.tipo('La misma combinación → sin_cambios', self.panel('panel_cambiar', codigo=cod, actividades=nuevas), 'sin_cambios')
        c = self.panel('panel_buscar', q=d)
        act_c = sorted(x['id'] for x in (c.get('registros') or [{}])[0].get('actividades', []))
        self.ok('El panel muestra las actividades nuevas', act_c == sorted(nuevas), sorted(nuevas), act_c)
        self.cerrar()
        self.panel('panel_actividad', id=llena['id'], cupo=self.acts0[llena['id']]['cupo'], confirmar=True)
        self.abrir()
        p = self.inscribir_panel(self.inexistente, self.combo())
        self.tipo('Inscribir desde el panel a alguien fuera del padrón → no_encontrado', p, 'no_encontrado')
        d3 = self.tomar(3)
        p = self.inscribir_panel(d3, self.combo())
        self.ok('Inscribir desde el panel ignora etapas: Etapa 3 con visita', p.get('tipo') == 'registrado' and p.get('origen') == 'PANEL', 'registrado · PANEL', f"{p.get('tipo')} · {p.get('origen')}")
        if p.get('tipo') == 'registrado':
            self.usados.add(d3)

    def l_whatsapp(self):
        self.seccion('L · Grupos de WhatsApp (R-16, R-29)')
        d = self.tomar(1)
        ids = self.combo()
        r = self.reg(d, ids)
        self.ok('El comprobante trae grupoModo y grupo de sus actividades', all('grupoModo' in a and 'grupo' in a for a in r.get('actividades', [])), 'ambos', '')
        a0 = self.acts()[ids[0]]
        self.tipo('Cambiar la entrega a MANUAL (abierto)', self.panel('panel_editar', id=ids[0], grupoModo='MANUAL'), 'panel')
        r2 = self.reg(self.tomar(1), ids)
        x = ([a for a in r2.get('actividades', []) if a['id'] == ids[0]] or [{}])[0]
        self.ok('Con entrega MANUAL, la confirmación no trae enlace y sí el celular', x.get('grupoModo') == 'MANUAL' and x.get('grupo') is None and str(r2.get('celular', '')).startswith('+51'),
                'MANUAL · null · +51…', f"{x.get('grupoModo')} · {x.get('grupo')} · {r2.get('celular')}")
        self.panel('panel_editar', id=ids[0], grupoModo=a0['grupoModo'])
        v = self.panel('panel_verificar_celular', id=ids[0], celular='+51 ' + self.celular(d))
        self.ok('Verificar solicitud: celular inscrito en esa actividad', v.get('inscrito') is True, True, v.get('inscrito'))
        otra = [a for a in self.acts() if a not in ids][0]
        self.ok('El mismo celular en otra actividad → no inscrito', self.panel('panel_verificar_celular', id=otra, celular=self.celular(d)).get('inscrito') is False, False, '')
        self.tipo('Enlace que no es de WhatsApp → enlace_invalido', self.panel('panel_editar', id=ids[0], grupo='https://ejemplo.com/grupo'), 'enlace_invalido')

    def m_roles(self):
        self.seccion('M · Roles (R-26)')
        op = lambda accion, **d: self.cli.llamar({'action': accion, 'key': self.key, 'comoRol': 'operador', **d})
        ad = lambda accion, **d: self.cli.llamar({'action': accion, 'key': self.key, 'comoRol': 'admin', **d})
        self.tipo('Operador ve el resumen', op('panel_resumen'), 'panel')
        self.tipo('Operador busca', op('panel_buscar', q='12345678'), 'panel')
        self.tipo('Operador verifica solicitudes de WhatsApp', op('panel_verificar_celular', id=list(self.acts0)[0], celular='987654321'), 'panel')
        for accion in ('panel_anular', 'panel_inscribir', 'panel_cambiar', 'panel_padron_agregar', 'panel_crear', 'panel_editar', 'panel_horarios', 'panel_registros'):
            self.tipo(f'Operador → {accion}: sin_permiso', op(accion), 'sin_permiso')
        self.tipo('Operador no cambia límites de intentos', op('panel_config', limiteRed=10), 'sin_permiso')
        self.tipo('Admin no entra a Equipo', ad('panel_equipo'), 'sin_permiso')
        self.tipo('Admin sí busca participantes', ad('panel_participantes'), 'panel')

    def n_padron_catalogo(self):
        self.seccion('N · Padrón y catálogo (R-17, R-18, R-22 a R-24)')
        nuevo = self.doc_prueba()
        r = self.panel('panel_padron_agregar', documento=nuevo, etapa=1)
        self.ok('Agregar al padrón de último momento', r.get('tipo') == 'panel', 'panel', r.get('tipo'), r.get('mensaje'))
        self.padron_nuevo.add(nuevo)
        self.tipo('Ya puede verificarse en la página', self.api(action='verificar', dni=nuevo), 'ok')
        r = self.panel('panel_padron_agregar', documento=nuevo, etapa=2)
        self.ok('Agregar el mismo a otra etapa → ya_existe con su etapa (D2: la etapa no cambia)', r.get('tipo') == 'ya_existe' and r.get('etapa') == 1, 'ya_existe · 1', f"{r.get('tipo')} · {r.get('etapa')}")
        self.tipo('Mismo documento y etapa → ya_existe', self.panel('panel_padron_agregar', documento=nuevo, etapa=1), 'ya_existe')
        self.tipo('Quitar del padrón abierto → requiere_cierre', self.panel('panel_padron_quitar', documento=nuevo), 'requiere_cierre')
        p = self.panel('panel_participantes', q=nuevo)
        self.ok('Panel 2 lo muestra con origen PANEL y sin inscribir', p['filas'] and p['filas'][0]['origen'] == 'PANEL' and p['filas'][0]['estado'] == 'SIN_INSCRIBIR', 'PANEL · SIN_INSCRIBIR', p['filas'][:1])
        dias = self.dias(self.acts())
        r = self.panel('panel_crear', tipo='VISITA', nombre='TEST visita del tester', lugar='Lima', fecha=dias[0], inicio='09:00', fin='11:00', cupo=10, descripcion='Prueba')
        nid = r.get('actividad', {}).get('id')
        self.ok('Crear actividad: nace oculta con cupo inicial', r.get('tipo') == 'panel' and r['actividad']['publicada'] is False and r['actividad']['cupoInicial'] == 10,
                'oculta · 10', r.get('actividad'))
        if nid:
            self.creadas.append(nid)
            self.ok('La respuesta dice con qué se cruza', isinstance(r.get('cruces'), list), 'lista', r.get('cruces'))
            self.tipo('Editar horario de una oculta sin inscritos', self.panel('panel_editar', id=nid, inicio='10:00', fin='12:00'), 'panel')
            self.tipo('Mostrarla (agrega, abierto)', self.panel('panel_actividad', id=nid, publicada=True), 'panel')
            self.tipo('Editar horario de una visible abierto → requiere_cierre', self.panel('panel_editar', id=nid, inicio='09:30'), 'requiere_cierre')
            self.tipo('Quitar una visible → esta_visible', self.panel('panel_quitar', id=nid), 'esta_visible')
        con = [a for a in self.acts().values() if a['inscritos'] > 0][0]
        self.tipo('Editar horario con inscritos → tiene_inscritos (nunca)', self.panel('panel_editar', id=con['id'], fin='23:00'), 'tiene_inscritos')
        self.tipo('Fecha mal escrita', self.panel('panel_crear', tipo='TALLER', nombre='x x x', fecha='31/02/2026', inicio='09:00', fin='10:00', cupo=5), 'datos_invalidos')

    def o_equipo(self):
        self.seccion('O · Equipo: cuentas y roles (R-30)')
        if not (self.a.local and self.a.dsn):
            self.omitir('Pestaña Equipo con cuentas reales', 'solo en local con --local y --dsn')
            return
        import psycopg2
        con = psycopg2.connect(self.a.dsn)
        con.autocommit = True
        ids = {}
        with con.cursor() as c:
            c.execute("select count(*) from organizadores where rol = 'propietario'")
            if c.fetchone()[0]:
                con.close()
                self.omitir('Pestaña Equipo con cuentas reales', 'ya hay un propietario en esta base (D9: es único); en una base local limpia sí se prueba')
                return
            for n in ('dueno', 'colega', 'nuevo'):
                c.execute('insert into auth.users (email) values (%s) returning id', (f'tester-{n}-{uuid.uuid4().hex[:6]}@ejemplo.com',))
                ids[n] = str(c.fetchone()[0])
            c.execute("insert into organizadores (user_id, nombre, rol) values (%s, 'Dueño de prueba', 'propietario')", (ids['dueno'],))
        self._equipo = (con, ids)
        como = lambda quien, aal='aal2': {'Authorization': f'Bearer local:{ids[quien]}:{aal}'}
        llama = lambda quien, accion, aal='aal2', **d: self.cli.llamar({'action': accion, **d}, cab=como(quien, aal))
        self.tipo('Cuenta sin código verificado (aal1) → falta_codigo', llama('dueno', 'panel_resumen', aal='aal1'), 'falta_codigo')
        self.tipo('Cuenta sin rol → sin_permiso', llama('nuevo', 'panel_resumen'), 'sin_permiso')
        e = llama('dueno', 'panel_equipo')
        self.ok('El propietario lista las cuentas', e.get('tipo') == 'panel' and any(x['usuario'] == ids['nuevo'] for x in e.get('cuentas', [])), 'lista', e.get('tipo'))
        self.tipo('Asignar operador a la cuenta nueva', llama('dueno', 'panel_equipo_rol', usuario=ids['nuevo'], rol='operador'), 'panel')
        self.tipo('Con rol, ya ve el panel', llama('nuevo', 'panel_resumen'), 'panel')
        self.tipo('Como operador no anula', llama('nuevo', 'panel_anular', codigo='CIIC-XXXXX'), 'sin_permiso')
        self.tipo('Nadie modifica al propietario desde el panel (D9)', llama('dueno', 'panel_equipo_rol', usuario=ids['dueno'], rol='admin'), 'no_permitido')
        self.tipo('Ni lo desactiva', llama('dueno', 'panel_equipo_activo', usuario=ids['dueno'], activo=False), 'no_permitido')
        self.tipo('El panel no asigna "propietario" a nadie (D9)', llama('dueno', 'panel_equipo_rol', usuario=ids['colega'], rol='propietario'), 'no_permitido')
        self.tipo('Desactivar a otro', llama('dueno', 'panel_equipo_activo', usuario=ids['nuevo'], activo=False), 'panel')
        self.tipo('La cuenta desactivada pierde acceso', llama('nuevo', 'panel_resumen'), 'sin_permiso')
        self.tipo('Un no propietario no administra el equipo', llama('nuevo', 'panel_equipo'), 'sin_permiso')
        r = llama('dueno', 'panel_config', pasoCupo=self.cfg0['pasoCupo'])
        self.ok('La bitácora guarda el nombre de la cuenta', r.get('tipo') == 'panel', 'panel', r.get('tipo'))


    # ═════════ Sprint 1 · seguridad ═════════════════════════════════════════
    def s_comprobantes(self):
        self.seccion('S · Sin comprobantes (R-01, R-31)')
        d = self.tomar(1)
        ids = self.combo()
        r = self.reg(d, ids)
        self.ok('registrado sin código', r.get('tipo') == 'registrado' and 'codigo' not in r and 'CIIC-' not in str(r.get('mensaje', '')), 'sin código', {k: r.get(k) for k in ('tipo', 'codigo', 'mensaje')})
        self.ok('registrado trae documento, etapa, celular y 2 actividades', r.get('doc') == d and r.get('etapa') == 1 and str(r.get('celular', '')).startswith('+51') and len(r.get('actividades', [])) == 2,
                'doc · etapa · celular · 2', {k: r.get(k) for k in ('doc', 'etapa', 'celular')})
        v = self.api(action='verificar', dni=d)
        self.ok('duplicado solo trae el aviso (ok, tipo, mensaje)', v.get('tipo') == 'duplicado' and set(v) <= {'ok', 'tipo', 'mensaje'} and 'CIIC-' not in v.get('mensaje', ''), 'ok · tipo · mensaje', sorted(v))
        x = self.reg(d, ids)
        self.ok('registrar otra vez: duplicado igual de mudo', x.get('tipo') == 'duplicado' and set(x) <= {'ok', 'tipo', 'mensaje'}, 'ok · tipo · mensaje', sorted(x))
        p = self.inscribir_panel(d, ids)
        self.ok('En el panel, duplicado sí trae el código (para soporte)', p.get('tipo') == 'duplicado' and str(p.get('codigo', '')).startswith('CIIC-'), 'CIIC-…', p.get('codigo'))

    def x_incidencias(self):
        self.seccion('X · Incidencias (R-36)')
        r = self.cli.llamar({'action': 'admin_error', 'key': self.key})
        self.ok('Un error interno devuelve error_servidor con número de incidencia', r.get('tipo') == 'error_servidor' and str(r.get('incidencia', '')).startswith('INC-'), 'INC-…', r.get('incidencia'))
        txt = json.dumps(r, ensure_ascii=False).lower()
        self.ok('…y sin detalle técnico', 'detalle' not in r and '22012' not in txt and 'divis' not in txt and 'zero' not in txt and 'cero' not in txt, 'sin detalle', sorted(r))
        ad = self.cli.llamar({'action': 'panel_incidencias', 'key': self.key, 'comoRol': 'admin'})
        inc = [x for x in ad.get('incidencias', []) if x.get('id') == r.get('incidencia')]
        self.ok('El admin ve el detalle en panel_incidencias', bool(inc) and inc[0].get('detalle', '').startswith('22012'), '22012 · división por cero (en el idioma del servidor)', inc[:1])
        self.tipo('El operador no ve las incidencias', self.cli.llamar({'action': 'panel_incidencias', 'key': self.key, 'comoRol': 'operador'}), 'sin_permiso')

    NIVELES = [   # acción, nivel, datos inofensivos (validan y no cambian nada)
        ('panel_resumen', 1, {}), ('panel_participantes', 1, {}), ('panel_buscar', 1, {'q': '00000000'}),
        ('panel_verificar_celular', 1, {'id': 'NO-EXISTE', 'celular': '987654321'}),
        ('panel_lista', 1, {}), ('panel_grupo_marcar', 1, {}), ('panel_exportar', 1, {}),
        ('panel_actividad', 2, {'id': 'NO-EXISTE'}), ('panel_crear', 2, {}), ('panel_editar', 2, {'id': 'NO-EXISTE'}), ('panel_quitar', 2, {'id': 'NO-EXISTE'}),
        ('panel_cruce', 2, {'a': 'NO-EXISTE', 'b': 'NO-EXISTE-2'}), ('panel_inscribir', 2, {}), ('panel_cambiar', 2, {'codigo': 'CIIC-NOEXISTE'}),
        ('panel_anular', 2, {'codigo': 'CIIC-NOEXISTE'}), ('panel_padron_agregar', 2, {'documento': 'x'}), ('panel_padron_quitar', 2, {'documento': 'NOEXISTE1'}),
        ('panel_incidencias', 2, {}), ('panel_sincronizar', 2, {}), ('panel_registros', 2, {}),
        ('panel_horarios', 3, {}), ('panel_equipo', 3, {}), ('panel_equipo_rol', 3, {'usuario': 'x'}), ('panel_equipo_activo', 3, {'usuario': 'x'}),
        ('panel_respaldo', 3, {}), ('panel_padron_importar', 3, {}), ('panel_actividades_importar', 3, {}), ('panel_vaciar_prueba', 3, {}),
        ('panel_preparar_produccion', 3, {}),
    ]

    def ab_niveles(self):
        self.seccion('AB · Niveles de rol: cada acción con cada rol (R-26)')
        rango = {'operador': 1, 'admin': 2, 'propietario': 3}
        for accion, nivel, datos in self.NIVELES:
            mal = []
            for rol, r_n in rango.items():
                r = self.cli.llamar({'action': accion, 'key': self.key, 'comoRol': rol, **datos})
                negado = r.get('tipo') == 'sin_permiso'
                if negado != (r_n < nivel) or (negado and r.get('nivel') != nivel):
                    mal.append(f"{rol}: {r.get('tipo')}")
            self.ok(f'{accion} · nivel {nivel}', not mal, 'operador ' + ('sí' if nivel <= 1 else 'no') + ' · admin ' + ('sí' if nivel <= 2 else 'no') + ' · propietario sí', '; '.join(mal))
        cfg = lambda rol, **c: self.cli.llamar({'action': 'panel_config', 'key': self.key, 'comoRol': rol, **c})
        self.tipo('panel_config · cerrar como admin: permitido (pide confirmar)', cfg('admin', abierto=False), 'advertencia')
        self.tipo('panel_config · cerrar como operador: no', cfg('operador', abierto=False), 'sin_permiso')
        self.tipo('panel_config · abrir como admin: no (propietario)', cfg('admin', abierto=True), 'sin_permiso')
        self.tipo('panel_config · etapas como admin: no', cfg('admin', etapas=[1, 2]), 'sin_permiso')
        self.tipo('panel_config · refresco como admin: no', cfg('admin', refresco=20), 'sin_permiso')
        self.tipo('panel_config · paso de cupo como admin: sí', cfg('admin', pasoCupo=self.cfg0['pasoCupo']), 'panel')
        self.tipo('panel_config · paso de cupo como operador: no', cfg('operador', pasoCupo=self.cfg0['pasoCupo']), 'sin_permiso')

    def r_privilegios(self):
        self.seccion('R · Privilegios: nadie entra por fuera de la API')
        base = self.a.api.rstrip('/') + '/rest/v1/'
        h = {'apikey': self.a.anon, **({'Authorization': f'Bearer {self.a.anon}'} if self.a.anon.startswith('eyJ') else {})}
        expuestos = []
        for t in ('padron', 'inscripciones', 'inscripcion_actividades', 'organizadores', 'bitacora', 'config', 'intentos', 'actividades'):
            try:
                r = self.cli.s.get(base + t + '?select=*&limit=1', headers=h, timeout=20)
                if r.status_code == 200 and r.text.strip() not in ('[]', ''):
                    expuestos.append(t)
            except requests.RequestException:
                pass
        self.ok('REST: ninguna tabla se lee con la clave pública', not expuestos, 'ninguna', expuestos)
        expuestas = []
        for f in ('verificar', 'registrar', 'crear_clave_admin', 'panel_resumen', 'asignar_propietario', 'admin_limpiar'):
            try:
                r = self.cli.s.post(base + 'rpc/' + f, json={}, headers=h, timeout=20)
                if r.status_code == 200:
                    expuestas.append(f)
            except requests.RequestException:
                pass
        self.ok('REST: ninguna función interna se llama directo', not expuestas, 'ninguna', expuestas)
        self.tipo('Panel con comoRol pero sin clave ni sesión → sin_sesion', self.api(action='panel_resumen', comoRol='propietario'), 'sin_sesion')
        con = self.sql()
        if not con:
            self.omitir('Privilegios en la base (roles anon y authenticated)', 'requiere --dsn')
            return
        tablas = ['public.' + t for t in ('config', 'tipos_actividad', 'padron', 'actividades', 'cruces_permitidos', 'inscripciones', 'inscripcion_actividades',
                                           'asistencias', 'organizadores', 'intentos', 'bitacora')] + ['privado.claves', 'privado.incidencias']
        with con.cursor() as c:
            for rol in ('anon', 'authenticated'):
                c.execute('select t from unnest(%s::text[]) t where has_table_privilege(%s, t, \'SELECT,INSERT,UPDATE,DELETE,TRUNCATE\')', (tablas, rol))
                self.ok(f'{rol}: sin permisos sobre ninguna tabla', not c.fetchall(), 'ninguna', '')
                c.execute("""select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid = p.pronamespace
                             where n.nspname = 'privado' and has_function_privilege(%s, p.oid, 'EXECUTE')""", (rol,))
                f = [x[0] for x in c.fetchall()]
                self.ok(f'{rol}: no ejecuta ninguna función de privado', not f, 'ninguna', f[:5])
                c.execute("select has_schema_privilege(%s, 'privado', 'USAGE'), has_function_privilege(%s, 'public.api(jsonb)', 'EXECUTE')", (rol, rol))
                usa, api = c.fetchone()
                self.ok(f'{rol}: sin acceso al esquema privado y con acceso a api()', not usa and api, 'privado no · api sí', f'privado {usa} · api {api}')
            con.rollback()
            for rol in ('anon', 'authenticated'):
                try:                       # primero cambiar de rol: si eso falla, la prueba no probaría nada (también da 42501)
                    c.execute(f'set local role {rol}')
                except Exception as e:  # noqa: BLE001
                    con.rollback()
                    self.omitir(f'{rol}: leer el padrón directo falla', f'esta conexión no puede actuar como {rol}: {str(e)[:60]}')
                    continue
                try:
                    c.execute('select count(*) from public.padron')
                    self.ok(f'{rol}: leer el padrón directo falla', False, 'permiso denegado', 'lo leyó')
                except Exception as e:  # noqa: BLE001
                    self.ok(f'{rol}: leer el padrón directo falla', getattr(e, 'pgcode', None) == '42501', '42501 · permiso denegado', f"{getattr(e, 'pgcode', None)} · {str(e)[:60]}")
                con.rollback()
            c.execute("""select c.relnamespace::regnamespace::text || '.' || c.relname from pg_class c
                         where c.relnamespace in ('public'::regnamespace, 'privado'::regnamespace) and c.relkind = 'r' and not c.relrowsecurity""")
            sin_rls = [x[0] for x in c.fetchall()]
            self.ok('Todas las tablas con RLS encendido', not sin_rls, 'todas', sin_rls)
            c.execute("""select n.nspname || '.' || p.proname, p.prosrc from pg_proc p join pg_namespace n on n.oid = p.pronamespace
                         where n.nspname in ('privado', 'public') and p.prolang in (select oid from pg_language where lanname in ('plpgsql', 'sql'))""")
            malas = [f'{nombre}: {x}' for nombre, src in c.fetchall() for x in sin_where(src)]
            fallos = [f"{'no detectó' if e else 'falso positivo'}: {s[:50]}" for s, e in CASOS_ESCANER if bool(sin_where(s)) != e]
            self.ok(f'El escáner acierta en sus {len(CASOS_ESCANER)} casos (incluido UPDATE … SET x = (SELECT … WHERE …) sin WHERE propio)',
                    not fallos, f'{len(CASOS_ESCANER)} de {len(CASOS_ESCANER)}', fallos[:3])
            self.ok('Ninguna función con DELETE o UPDATE sin WHERE (Supabase los rechaza: safeupdate, error 21000)', not malas, 'ninguna', malas[:4])
            c.execute("select prosecdef, array_to_string(proconfig, ',') from pg_proc where oid = 'public.api(jsonb)'::regprocedure")
            sd, cfg = c.fetchone()
            self.ok('api() es security definer con search_path fijo', sd and 'search_path=' in (cfg or ''), 'definer · search_path', f'{sd} · {cfg}')
        con.rollback()
        con.close()

    def r_ip_real(self):
        self.seccion('R · IP del límite por red (§8)')
        r = self.cli.llamar({'action': 'admin_cabeceras', 'key': self.key})
        self.ok('admin_cabeceras muestra las cabeceras y la red resuelta', r.get('tipo') == 'admin' and 'red' in r and 'x-forwarded-for' in r, 'admin', r.get('tipo'))
        if not self.a.local:
            print(pinta(GRIS, f"  … cabeceras: {r.get('cabeceras')} · cf-connecting-ip {r.get('cf-connecting-ip')} · x-real-ip {r.get('x-real-ip')} · x-forwarded-for {r.get('x-forwarded-for')} · red {r.get('red')} · ip_cabecera {r.get('ipCabecera')}"))
            h = {'apikey': self.a.anon, **({'Authorization': f'Bearer {self.a.anon}'} if self.a.anon.startswith('eyJ') else {})}
            for cab, valor in (('X-Forwarded-For', '198.51.100.7'), ('X-Real-IP', '198.51.100.8'), ('CF-Connecting-IP', '198.51.100.9')):
                try:            # llamada directa, sin reintentos: el proxy de Supabase puede rechazarla, y eso también es seguro
                    x = self.cli.s.post(self.cli.url, json={'p': {'action': 'admin_cabeceras', 'key': self.key}}, headers={**h, cab: valor}, timeout=30)
                    estado, red = x.status_code, (x.json().get('red') if x.headers.get('content-type', '').startswith('application/json') else None)
                except (requests.RequestException, ValueError):
                    estado, red = 0, None
                rechazada = estado in (400, 403)
                self.ok(f'Supabase: {cab} falso no cambia la red (o el proxy rechaza la llamada)', rechazada or (estado == 200 and red == r.get('red') and red not in (None, 'desconocida')),
                        'misma red o rechazo del proxy', 'rechazada por el proxy (HTTP %d)' % estado if rechazada else f'HTTP {estado} · red {"igual" if red == r.get("red") else "distinta"}')
            self.ok('Supabase: ip_cabecera ya no es "auto"', r.get('ipCabecera') != 'auto', 'fijada', r.get('ipCabecera'))
            try:
                publica = requests.get('https://api.ipify.org', timeout=8).text.strip()
            except requests.RequestException:
                publica = ''
            if re.fullmatch(r'[0-9a-fA-F:.]{7,45}', publica or ''):
                self.ok('Supabase: la red detectada es la IP pública de quien llama', r.get('red') == publica, 'tu IP pública', 'otra (' + str(r.get('red'))[:3] + '…)')
            else:
                self.omitir('Supabase: la red detectada es la IP pública de quien llama', 'no se pudo consultar api.ipify.org')
            return
        ip = lambda cab: self.cli.llamar({'action': 'admin_cabeceras', 'key': self.key}, cab=cab).get('red')
        self.ok('auto: cf-connecting-ip manda sobre x-forwarded-for', ip({'cf-connecting-ip': '203.0.113.9', 'X-Forwarded-For': '198.51.100.7'}) == '203.0.113.9', '203.0.113.9', ip({'cf-connecting-ip': '203.0.113.9'}))
        self.ok('auto: sin cf, x-real-ip', ip({'x-real-ip': '192.0.2.44', 'X-Forwarded-For': '198.51.100.7'}) == '192.0.2.44', '192.0.2.44', '')
        self.ok('auto: sin ninguna, el primer valor de x-forwarded-for', ip({'X-Forwarded-For': '198.51.100.7'}) == '198.51.100.7', '198.51.100.7', ip({'X-Forwarded-For': '198.51.100.7'}))
        con = self.sql()
        if con:
            with con.cursor() as c:
                c.execute("update config set ip_cabecera = 'xff-ultimo' where id = 1")
            con.commit()
            ultima = ip({'X-Forwarded-For': '198.51.100.7'})
            with con.cursor() as c:
                c.execute("update config set ip_cabecera = 'auto' where id = 1")
            con.commit()
            con.close()
            self.ok('xff-ultimo: toma la IP que agrega el proxy, no la del cliente', ultima not in ('198.51.100.7', 'desconocida', None), 'IP del proxy', ultima)

    def z_equipo(self):
        self.seccion('Z · Propietario único y producción sin clave (D8, D9)')
        self.tipo('El panel no asigna "propietario" (ni el propietario)', self.panel('panel_equipo_rol', usuario=str(uuid.uuid4()), rol='propietario'), 'no_permitido')
        con = self.sql() if self.a.local else None          # crea cuentas en auth.users: solo en la base local
        if not con:
            self.omitir('Propietario único y clave en PRODUCCION', 'solo en local con --local y --dsn')
            return
        import psycopg2
        with con.cursor() as c:
            c.execute("insert into auth.users (email) values (%s), (%s) returning id", (f'z1-{uuid.uuid4().hex[:6]}@ejemplo.com', f'z2-{uuid.uuid4().hex[:6]}@ejemplo.com'))
            u1, u2 = [str(x[0]) for x in c.fetchall()]
            c.execute("select count(*) from organizadores where rol = 'propietario'")
            hay = c.fetchone()[0]
            c.execute("savepoint a")
            try:
                c.execute("insert into organizadores (user_id, rol) values (%s, 'propietario'), (%s, 'propietario')", (u1, u2))
                self.ok('La base no acepta dos propietarios', False, 'unique_violation', 'aceptó dos')
            except psycopg2.Error as e:
                self.ok('La base no acepta dos propietarios', e.pgcode == '23505', 'unique_violation', e.pgcode)
                c.execute("rollback to savepoint a")
            c.execute("select email from auth.users where id = %s", (u1,))
            e1 = c.fetchone()[0]
            if hay:      # dentro de esta transacción, que se deshace al final: el propietario actual pasa a admin para probar desde cero
                c.execute("update organizadores set rol = 'admin' where rol = 'propietario'")
            c.execute("select privado.asignar_propietario(%s)", (e1,))
            c.execute("select rol from organizadores where user_id = %s", (u1,))
            self.ok('asignar_propietario da el rol en SQL (§12.3)', c.fetchone()[0] == 'propietario', 'propietario', '')
            c.execute("savepoint b")
            try:
                c.execute("select email from auth.users where id = %s", (u2,))
                c.execute("select privado.asignar_propietario(%s)", (c.fetchone()[0],))
                self.ok('asignar_propietario no crea un segundo', False, 'error', 'lo creó')
            except psycopg2.Error:
                self.ok('asignar_propietario no crea un segundo', True)
                c.execute("rollback to savepoint b")
            c.execute("select email from auth.users where id = %s", (u2,))
            c.execute("select privado.cambiar_propietario(%s)", (c.fetchone()[0],))
            c.execute("select count(*) filter (where rol = 'propietario'), bool_or(user_id = %s and rol = 'propietario'), bool_or(user_id = %s and rol = 'admin') from organizadores", (u2, u1))
            n, es, anterior = c.fetchone()
            self.ok('cambiar_propietario pasa el rol en una sola operación; el anterior queda admin', n == 1 and es and anterior, '1 · nuevo · anterior admin', f'{n} · {es} · {anterior}')
            c.execute("update config set modo = 'PRODUCCION' where id = 1")
            c.execute("select count(*) from privado.claves where nombre = 'ADMIN_KEY'")
            self.ok('Al pasar a PRODUCCION la clave del tester desaparece sola (R-37)', c.fetchone()[0] == 0, 0, '')
        con.rollback()          # nada de lo anterior queda: ni cuentas, ni propietario, ni modo
        con.close()
        self.ok('Después de deshacer, la clave del tester sigue funcionando', self.cli.llamar({'action': 'admin_ping', 'key': self.key}).get('tipo') == 'admin', 'admin', '')

    def ad_masiva(self):
        self.seccion('AD · Protección contra operaciones masivas (R-40)')
        con = self.sql()
        if not con:
            self.omitir('Protección masiva', 'requiere --dsn')
            return
        import psycopg2

        def intento(nombre, sentencia, bloquea, previo=None):
            with con.cursor() as c:
                try:
                    if previo:
                        c.execute(previo)
                    c.execute(sentencia)
                    self.ok(nombre, not bloquea, 'bloqueada' if bloquea else 'permitida', f'pasó ({c.rowcount} filas)')
                except psycopg2.Error as e:
                    self.ok(nombre, bloquea and 'masiva bloqueada' in str(e).lower(), 'bloqueada' if bloquea else 'permitida', str(e).split('\n')[0][:90])
            con.rollback()

        with con.cursor() as c:
            c.execute('select count(*) from inscripciones')
            n_ins = c.fetchone()[0]
        con.rollback()
        if n_ins > 10:
            intento('DELETE sin WHERE en inscripciones → bloqueado', 'delete from inscripciones', True)
        else:
            self.omitir('DELETE sin WHERE en inscripciones', 'hay 10 o menos inscripciones')
        intento('UPDATE sin WHERE en padrón → bloqueado', 'update padron set etapa = etapa', True)
        intento('UPDATE masivo en actividades → bloqueado', 'update actividades set cupo = cupo', True)
        intento('TRUNCATE de cruces → bloqueado', 'truncate cruces_permitidos', True)
        intento('DELETE de una sola fila → permitido', "delete from padron where documento = '00000000'", False)
        intento('Con set local ciic.masivo = confirmado → permitido', 'update padron set etapa = etapa', False, previo="set local ciic.masivo = 'confirmado'")
        with con.cursor() as c:
            c.execute('select count(*) from inscripciones')
            self.ok('Después de todo, ninguna fila cambió', c.fetchone()[0] == n_ins, n_ins, '')
        con.rollback()
        con.close()

    def ag_bitacora(self):
        self.seccion('AG · Bitácora con antes y después (R-30)')
        con = self.sql()
        if not con:
            self.omitir('Bitácora con antes y después', 'requiere --dsn')
            return
        paso0 = self.cfg0['pasoCupo']
        nuevo = paso0 + 1 if paso0 < 100 else paso0 - 1
        self.panel('panel_config', pasoCupo=nuevo)
        a = list(self.acts().values())[0]
        self.panel('panel_actividad', id=a['id'], cupo=a['cupo'] + 1)
        with con.cursor() as c:
            c.execute("select antes ->> 'pasoCupo', despues ->> 'pasoCupo' from bitacora where accion = 'Configuración' order by id desc limit 1")
            x = c.fetchone() or (None, None)
            self.ok('Configuración: guarda el valor anterior y el nuevo', x == (str(paso0), str(nuevo)), f'{paso0} → {nuevo}', x)
            c.execute("select antes ->> 'cupo', despues ->> 'cupo' from bitacora where accion = %s order by id desc limit 1", ('Actividad ' + a['id'],))
            x = c.fetchone() or (None, None)
            self.ok('Actividad: cupo anterior y nuevo', x == (str(a['cupo']), str(a['cupo'] + 1)), f"{a['cupo']} → {a['cupo'] + 1}", x)
            if hasattr(self, '_equipo'):
                c.execute("select antes ->> 'rol', despues ->> 'rol' from bitacora where accion = 'Equipo' and despues ->> 'rol' = 'operador' order by id desc limit 1")
                x = c.fetchone() or ('?', None)
                self.ok('Equipo: rol anterior (sin rol) y nuevo (operador)', x == (None, 'operador'), 'None → operador', x)
            else:
                self.omitir('Equipo: rol anterior y nuevo', 'el bloque de Equipo no corrió')
        con.rollback()
        con.close()
        self.panel('panel_config', pasoCupo=paso0)
        self.panel('panel_actividad', id=a['id'], cupo=a['cupo'], confirmar=True)


    # ═════════ Sprint 2 · integridad y datos ════════════════════════════════
    @staticmethod
    def clave_orden(t):
        """Mismo orden que privado.clave_orden: sin tildes ni mayúsculas, ñ después de n."""
        return (t or '').translate(str.maketrans('ÁÉÍÓÚÜÑáéíóúü', 'AEIOUUñaeiouu')).lower().replace('ñ', 'n{')

    def integra(self):
        return self.resumen().get('integridad', {}).get('ok') is True

    def t_carreras(self):
        self.seccion('T · Carreras: muchos a la vez por lo mismo')
        acts = self.acts()
        dia1, dia2 = self.dias(acts)[:2]
        t1 = self.libre(acts, 'TALLER', dia1)
        t2 = self.libre(acts, 'TALLER', dia2, minimo=1)
        self.panel('panel_actividad', id=t1['id'], cupo=t1['inscritos'] + 120)            # sobra lugar el día 1
        self.cerrar()
        self.panel('panel_actividad', id=t2['id'], cupo=t2['inscritos'] + 10, confirmar=True)
        self.abrir()
        docs = [self.tomar(1) for _ in range(50)] + [self.tomar(2) for _ in range(50)]
        with cf.ThreadPoolExecutor(100) as ex:
            rs = list(ex.map(lambda d: self.reg(d, [t1['id'], t2['id']], paciente=True), docs))
        tipos = [r.get('tipo') for r in rs]
        ahora = self.acts()
        self.ok('100 personas por los últimos 10 cupos: entran 10 exactas', tipos.count('registrado') == 10, 10, tipos.count('registrado'), str(set(tipos)))
        self.ok('Las otras 90 reciben lleno', tipos.count('lleno') == 90, 90, tipos.count('lleno'))
        self.ok('Sin sobrecupo y todo o nada (el día 1 solo sumó 10)', ahora[t2['id']]['inscritos'] == ahora[t2['id']]['cupo'] and ahora[t1['id']]['inscritos'] == t1['inscritos'] + 10,
                'lleno · +10', f"{ahora[t2['id']]['inscritos']}/{ahora[t2['id']]['cupo']} · +{ahora[t1['id']]['inscritos'] - t1['inscritos']}")
        # dos cambios simultáneos de la misma inscripción
        tal1 = [a['id'] for a in ahora.values() if a['publicada'] and a['tipo'] == 'TALLER' and a['fecha'] == dia1 and a['disponibles'] > 3]
        tal2 = [a['id'] for a in ahora.values() if a['publicada'] and a['tipo'] == 'TALLER' and a['fecha'] == dia2 and a['disponibles'] > 3]
        d = self.tomar(1)
        self.reg(d, [tal1[0], tal2[0]])
        cod = self.codigo_de(d)
        with cf.ThreadPoolExecutor(2) as ex:
            rs = list(ex.map(lambda ids: self.panel('panel_cambiar', codigo=cod, actividades=ids, ampliarCupo=True), [[tal1[1], tal2[0]], [tal1[0], tal2[1]]]))
        b = self.panel('panel_buscar', q=d)['registros'][0]
        self.ok('Dos cambios simultáneos de la misma inscripción: ambos se aplican en orden, sin mezclas', all(r.get('tipo') in ('panel', 'sin_cambios') for r in rs)
                and len(b['actividades']) == 2 and self.integra(), '2 actividades · integridad', f"{[r.get('tipo') for r in rs]} · {len(b['actividades'])}")
        # anular mientras otros toman los cupos
        z = self.acts()[tal2[2] if len(tal2) > 2 else tal2[0]]
        x = self.tomar(1)
        self.reg(x, [tal1[0], z['id']])
        z = self.acts()[z['id']]
        self.cerrar()
        self.panel('panel_actividad', id=z['id'], cupo=z['inscritos'], confirmar=True)
        self.abrir()
        cx = self.codigo_de(x)
        otros = [self.tomar(2) for _ in range(5)]
        with cf.ThreadPoolExecutor(6) as ex:
            fut = [ex.submit(self.reg, o, [tal1[0], z['id']], paciente=True) for o in otros] + [ex.submit(self.panel, 'panel_anular', codigo=cx)]
            rs = [f.result() for f in fut]
        fin = self.acts()[z['id']]
        self.ok('Anular mientras 5 toman el cupo liberado: entra como mucho 1 y sin sobrecupo', [r.get('tipo') for r in rs[:5]].count('registrado') <= 1
                and fin['inscritos'] <= fin['cupo'] and self.integra(), '≤ 1 · sin sobrecupo', [r.get('tipo') for r in rs[:5]])
        # cerrar y reducir mientras otros confirman
        y = self.acts()[tal1[1]]
        docs = [self.tomar(2) for _ in range(10)]
        ronda = self.estado()['ronda']
        def cerrar_y_reducir():
            self.cerrar()
            return self.panel('panel_actividad', id=y['id'], cupo=self.acts()[y['id']]['inscritos'], confirmar=True)
        with cf.ThreadPoolExecutor(11) as ex:
            fut = [ex.submit(self.reg, dd, [y['id'], tal2[0]], ronda=ronda, paciente=True) for dd in docs]
            time.sleep(0.05)
            ex.submit(cerrar_y_reducir).result()
            rs = [f.result() for f in fut]
        fin = self.acts()[y['id']]
        self.ok('Cerrar y reducir mientras 10 confirman: cada una registrado o cerrado; sin sobrecupo', set(r.get('tipo') for r in rs) <= {'registrado', 'cerrado'}
                and fin['inscritos'] <= fin['cupo'] and self.integra(), 'registrado|cerrado', set(r.get('tipo') for r in rs))
        self.abrir()

    def u_idempotencia(self):
        self.seccion('U · Idempotencia: la misma solicitud no hace dos veces lo mismo (R-32)')
        ids = self.combo()
        d = self.tomar(1)
        sol = str(uuid.uuid4())
        r1 = self.reg(d, ids, solicitud=sol)
        antes = self.acts()
        r2 = self.reg(d, ids, solicitud=sol)
        despues = self.acts()
        self.ok('Reenviar la misma solicitud (respuesta perdida): misma respuesta, marcada repetida', r1.get('tipo') == 'registrado' and r2.get('tipo') == 'registrado' and r2.get('repetida') is True,
                'registrado · repetida', f"{r2.get('tipo')} · {r2.get('repetida')}")
        self.ok('…y ningún cambio doble', all(despues[i]['inscritos'] == antes[i]['inscritos'] for i in ids) and len(self.panel('panel_buscar', q=d)['registros']) == 1, 'igual', '')
        self.tipo('La misma solicitud con otros datos → solicitud_repetida', self.reg(d, ids, solicitud=sol, nombres='Otra Persona'), 'solicitud_repetida')
        self.tipo('Sin solicitud → valor_invalido', self.reg(self.tomar(1), ids, solicitud=SIN), 'valor_invalido')
        self.tipo('Solicitud que no es UUID → valor_invalido', self.reg(self.tomar(1), ids, solicitud='abc-123'), 'valor_invalido')
        cod = self.codigo_de(d)
        s2 = str(uuid.uuid4())
        a1 = self.panel('panel_anular', codigo=cod, solicitud=s2)
        a2 = self.panel('panel_anular', codigo=cod, solicitud=s2)
        self.ok('Anular dos veces con la misma solicitud: la segunda es la misma respuesta, no "no encontrado"', a1.get('tipo') == 'panel' and a2.get('tipo') == 'panel' and a2.get('repetida') is True,
                'panel · panel repetida', f"{a1.get('tipo')} · {a2.get('tipo')} {a2.get('repetida')}")
        a = list(self.acts().values())[0]
        s3 = str(uuid.uuid4())
        self.panel('panel_actividad', id=a['id'], cupo=a['cupo'] + 3, solicitud=s3)
        x = self.panel('panel_actividad', id=a['id'], cupo=a['cupo'] + 3, solicitud=s3)
        self.ok('Cupo final con la misma solicitud dos veces: queda en el mismo valor', x.get('repetida') is True and self.acts()[a['id']]['cupo'] == a['cupo'] + 3, a['cupo'] + 3, self.acts()[a['id']]['cupo'])

    def ai_ambito(self):
        self.seccion('AI · Idempotencia con ámbito: cada quien tiene sus solicitudes (R-32)')
        sol = str(uuid.uuid4())
        ids = self.combo()
        r1, r2 = self.reg(self.tomar(1), ids, solicitud=sol), self.reg(self.tomar(1), ids, solicitud=sol)
        self.ok('La misma solicitud desde dos documentos distintos: dos inscripciones, sin chocar', r1.get('tipo') == r2.get('tipo') == 'registrado' and not r2.get('repetida'),
                'registrado · registrado', f"{r1.get('tipo')} · {r2.get('tipo')} {r2.get('repetida')}")
        a = list(self.acts())[0]
        x = self.cli.llamar({'action': 'panel_grupo_marcar', 'key': self.key, 'comoRol': 'admin', 'id': a, 'codigos': [], 'solicitud': sol})
        y = self.cli.llamar({'action': 'panel_grupo_marcar', 'key': self.key, 'comoRol': 'operador', 'id': a, 'codigos': [], 'solicitud': sol})
        self.ok('La misma solicitud desde dos cuentas distintas: cada una la suya', x.get('tipo') == y.get('tipo') == 'panel' and not y.get('repetida'), 'panel · panel', f"{x.get('tipo')} · {y.get('tipo')}")

    def v_integridad(self):
        self.seccion('V · Integridad: contadores = inscripciones (R-33)')
        self.ok('Después de todas las carreras, cada contador coincide', self.integra(), 'ok', self.resumen().get('integridad'))
        r = self.panel('panel_sincronizar')
        self.ok('Recontar (nivel 2) devuelve la integridad', r.get('tipo') == 'panel' and r.get('integridad', {}).get('ok') is True, 'ok', r.get('integridad'))
        con = self.sql()
        if not con:
            self.omitir('Inserción a mano mantiene la integridad', 'requiere --dsn')
            return
        acts = self.acts()
        ids = self.combo(acts)
        doc = self.tomar(2)
        with con.cursor() as c:
            c.execute("insert into inscripciones (codigo, documento, nombres, apellidos, correo, etapa, celular, pais, acepta_whatsapp, ronda) "
                      "values ('CIIC-VVVVV', %s, 'A', 'Mano', 'a@b.pe', 2, '+51911111111', 'PE', true, 1)", (doc,))
            c.execute("insert into inscripcion_actividades (codigo, actividad_id, actividad_nombre) values ('CIIC-VVVVV', %s, 'x'), ('CIIC-VVVVV', %s, 'y')", tuple(ids))
            c.execute('select id, inscritos from actividades where id = any(%s)', (ids,))
            sube = all(n == acts[i]['inscritos'] + 1 for i, n in c.fetchall())
            c.execute("update inscripciones set estado = 'ANULADO' where codigo = 'CIIC-VVVVV'")
            c.execute('select id, inscritos from actividades where id = any(%s)', (ids,))
            baja = all(n == acts[i]['inscritos'] for i, n in c.fetchall())
            c.execute("update inscripciones set estado = 'CONFIRMADO' where codigo = 'CIIC-VVVVV'")
            c.execute("delete from inscripciones where codigo = 'CIIC-VVVVV'")
            c.execute('select id, inscritos from actividades where id = any(%s)', (ids,))
            borra = all(n == acts[i]['inscritos'] for i, n in c.fetchall())
            c.execute("select (privado.integridad() ->> 'ok')::boolean")
            ok = c.fetchone()[0]
        con.rollback()
        con.close()
        self.ok('Inscribir a mano suma; anular resta; borrar resta (disparadores)', sube and baja and borra and ok, 'suma · resta · resta · ok', f'{sube} · {baja} · {borra} · {ok}')

    def aa_listas(self):
        self.seccion('AA · Listas por actividad y CSV (R-38, R-39)')
        acts = self.acts()
        a = max(acts.values(), key=lambda x: x['inscritos'])
        op = lambda accion, **d: self.cli.llamar({'action': accion, 'key': self.key, 'comoRol': 'operador', **d})
        l = op('panel_lista', id=a['id'])
        filas = l.get('filas', [])
        self.ok('El operador ve la lista con todos sus inscritos', l.get('tipo') == 'panel' and l.get('total') == a['inscritos'] == len(filas), a['inscritos'], l.get('total'))
        campos = {'actividad', 'apellidos', 'nombres', 'doc', 'correo', 'celular', 'etapa', 'codigo', 'origen', 'enGrupo'}
        self.ok('Cada fila trae los campos de R-38', all(campos <= set(f) for f in filas), sorted(campos), sorted(filas[0]) if filas else '')
        claves = [(self.clave_orden(f['apellidos']), self.clave_orden(f['nombres'])) for f in filas]
        self.ok('Ordenada por apellidos y nombres', claves == sorted(claves), 'ordenada', '')
        ids2 = self.combo()
        ape = ['Zúñiga Paz', 'Ñahui Ccori', 'Nuñez Ríos', 'Nunez Ríos', 'álvarez Soto', 'Álvarez Luna', 'Navarro León']
        docs = {}
        for x in ape:
            dd = self.tomar(1)
            self.reg(dd, ids2, apellidos=x, nombres='Orden')
            docs[dd] = x
        lst = [f for f in op('panel_lista', id=ids2[0])['filas'] if f['doc'] in docs]
        esperado = ['Álvarez Luna', 'álvarez Soto', 'Navarro León', 'Nunez Ríos', 'Nuñez Ríos', 'Ñahui Ccori', 'Zúñiga Paz']
        self.ok('Orden en español con tildes y Ñ: Álvarez … Nunez, Nuñez, Ñahui, Zúñiga (igual en cualquier servidor)', [f['apellidos'] for f in lst] == esperado,
                ' · '.join(esperado), ' · '.join(f['apellidos'] for f in lst))
        exp = [f[5] for f in op('panel_exportar', id=ids2[0])['filas'] if f[5] in ape]
        self.ok('El CSV sale en el mismo orden que la lista', exp == esperado, 'mismo orden', ' · '.join(exp))
        e2 = op('panel_lista', id=a['id'], etapa=2)
        self.ok('Filtro por etapa', all(f['etapa'] == 2 for f in e2.get('filas', [])) and e2.get('total') == sum(1 for f in filas if f['etapa'] == 2), 'solo Etapa 2', '')
        if filas:
            f0 = filas[0]
            b = op('panel_lista', id=a['id'], q=f0['celular'][-9:])
            self.ok('Buscar por celular encuentra a la persona', any(x['codigo'] == f0['codigo'] for x in b.get('filas', [])), f0['codigo'], '')
            sol = str(uuid.uuid4())
            m = op('panel_grupo_marcar', id=a['id'], codigos=[f0['codigo']], agregado=not f0['enGrupo'], solicitud=sol)
            relee = [x for x in op('panel_lista', id=a['id'])['filas'] if x['codigo'] == f0['codigo']][0]
            self.ok('Marcar en el grupo queda en la base y se relee', m.get('marcados') == 1 and relee['enGrupo'] is (not f0['enGrupo']), not f0['enGrupo'], relee['enGrupo'])
            m2 = op('panel_grupo_marcar', id=a['id'], codigos=[f0['codigo']], agregado=not f0['enGrupo'], solicitud=sol)
            self.ok('Reenviar la misma marca no la cambia dos veces', m2.get('repetida') is True, 'repetida', m2.get('repetida'))
            op('panel_grupo_marcar', id=a['id'], codigos=[f0['codigo']], agregado=f0['enGrupo'])
        x = op('panel_exportar', id=a['id'])
        enc = ['Actividad', 'Nombre de la actividad', 'Fecha', 'Horario', 'DNI', 'Apellidos', 'Nombres', 'Correo', 'Celular', 'Etapa', 'Código', 'Origen', 'En el grupo']
        self.ok('CSV por actividad como operador, con las columnas de R-39', x.get('encabezados') == enc and len(x.get('filas', [])) == a['inscritos'], len(enc), len(x.get('encabezados', [])))
        x2 = op('panel_exportar', id=a['id'], etapa=2)
        self.ok('CSV por etapa', len(x2.get('filas', [])) == sum(1 for f in filas if f['etapa'] == 2), 'filtrado', len(x2.get('filas', [])))
        todas = op('panel_exportar')
        conf = self.resumen()['totales']['inscritos']
        self.ok('CSV de todas: una fila por actividad de cada inscrito', len(todas.get('filas', [])) == 2 * conf, 2 * conf, len(todas.get('filas', [])))
        con = self.sql()
        if con:
            with con.cursor() as c:
                c.execute("select detalle from bitacora where accion = 'Exportación' and quien like '%operador%' order by id desc limit 1")
                fila = c.fetchone()
            con.rollback(); con.close()
            self.ok('Cada descarga queda en la bitácora', bool(fila) and 'filas' in fila[0], 'Exportación · … filas', fila)

    def ac_padron_minimo(self):
        self.seccion('AC · Padrón mínimo y correo obligatorio (R-35, R-13)')
        nuevo = self.doc_prueba()
        r = self.panel('panel_padron_agregar', documento=nuevo, etapa=2, nombre='Este campo se ignora')
        self.ok('Alta solo con documento y etapa', r.get('tipo') == 'panel' and r.get('etapa') == 2, 'panel · 2', r.get('tipo'))
        self.padron_nuevo.add(nuevo)
        r = self.panel('panel_padron_agregar', documento=nuevo, etapa=3)
        self.ok('Repetido con otra etapa → ya_existe y la etapa no cambia', r.get('tipo') == 'ya_existe' and r.get('etapa') == 2, 'ya_existe · 2', f"{r.get('tipo')} · {r.get('etapa')}")
        self.panel('panel_padron_importar', filas=[{'documento': nuevo, 'etapa': '3'}])
        p = self.panel('panel_participantes', q=nuevo)
        self.ok('Ni la importación cambia la etapa', p['filas'] and p['filas'][0]['etapa'] == 2, 2, p['filas'][:1])

    def ah_correo_panel(self):
        self.seccion('AH · Correo obligatorio también en el panel')
        r = self.inscribir_panel(self.tomar(1), self.combo(), correo='')
        self.ok('Inscribir desde el panel sin correo → datos_invalidos (campo correo)', r.get('tipo') == 'datos_invalidos' and r.get('campo') == 'correo', 'correo', f"{r.get('tipo')} · {r.get('campo')}")

    def ae_importar_padron(self):
        self.seccion('AE · Importar padrón (R-42)')
        nuevos = [self.doc_prueba() for _ in range(5)]
        existente1 = self.tomar(1)
        filas = [{'documento': n, 'etapa': 'Etapa 1'} for n in nuevos[:3]] + [{'documento': '%s.%s' % (nuevos[3][:4], nuevos[3][4:]), 'etapa': '2'},
                 {'documento': nuevos[4], 'etapa': 'E3'}, {'documento': nuevos[4], 'etapa': '1'}, {'documento': existente1, 'etapa': '1'},
                 {'documento': existente1, 'etapa': '2'}, {'documento': 'hola', 'etapa': '1'}, {'documento': nuevos[0], 'etapa': '9'}]
        self.tipo('Como admin → sin_permiso (es del propietario)', self.cli.llamar({'action': 'panel_padron_importar', 'key': self.key, 'comoRol': 'admin', 'filas': filas}), 'sin_permiso')
        r = self.panel('panel_padron_importar', filas=filas)
        self.padron_nuevo.update(nuevos)
        self.ok('Informe: 5 agregados, 1 ya existía, 2 conflictos, 2 inválidos', (r.get('agregados'), r.get('existentes'), len(r.get('conflictos', [])), len(r.get('invalidos', []))) == (5, 1, 2, 2),
                '(5, 1, 2, 2)', (r.get('agregados'), r.get('existentes'), len(r.get('conflictos', [])), len(r.get('invalidos', []))))
        self.tipo('Un documento importado ya puede verificarse', self.api(action='verificar', dni=nuevos[0]), 'ok')
        self.tipo('El documento con puntos se guardó normalizado', self.api(action='verificar', dni=nuevos[3]), 'ok')
        r = self.panel('panel_padron_importar', filas=filas)
        self.ok('Repetir la misma importación no duplica nada', r.get('agregados') == 0, 0, r.get('agregados'))
        grande = [self.doc_prueba() for _ in range(10000)]
        t0 = time.perf_counter()
        r = self.panel('panel_padron_importar', filas=[{'documento': x, 'etapa': str(1 + k % 3)} for k, x in enumerate(grande)])
        dur = time.perf_counter() - t0
        self.padron_nuevo.update(grande)
        self.ok('10 000 filas en una llamada, dentro del límite de 3 s', r.get('tipo') == 'panel' and r.get('agregados', 0) + r.get('existentes', 0) == 10000 and dur < 3,
                '10 000 · < 3 s', f"{r.get('tipo')} · {r.get('agregados')} · total {dur:.2f} s · en la base {(r.get('duracionMs') or 0) / 1000:.2f} s")

    def ak_importar_actividades(self):
        self.seccion('AK · Importar actividades (R-45)')
        dias = self.dias(self.acts())
        uno = list(self.acts())[0]
        filas = [{'id': 'TSTI1', 'tipo': 'TALLER', 'nombre': 'Taller importado uno', 'lugar': 'Aula 1', 'fecha': dias[0], 'inicio': '19:00', 'fin': '20:00', 'cupo': '30', 'visible': 'NO'},
                 {'id': 'TSTI2', 'tipo': 'VISITA', 'nombre': 'Visita importada dos', 'fecha': dias[1], 'inicio': '07:00', 'fin': '08:00', 'cupo': '10', 'entrega': 'MANUAL', 'visible': 'NO'},
                 {'id': '', 'tipo': 'TALLER', 'nombre': 'Taller sin ID', 'fecha': dias[1], 'inicio': '19:00', 'fin': '20:00', 'cupo': '5'},
                 {'id': uno, 'tipo': 'TALLER', 'nombre': 'Ya existe', 'fecha': dias[0], 'inicio': '09:00', 'fin': '10:00', 'cupo': '5'},
                 {'id': '', 'tipo': 'TALLER', 'nombre': 'Fecha mala', 'fecha': '31/02/2026', 'inicio': '09:00', 'fin': '10:00', 'cupo': '5'},
                 {'id': 'MAL ID', 'tipo': 'TALLER', 'nombre': 'ID con espacio', 'fecha': dias[0], 'inicio': '09:00', 'fin': '10:00', 'cupo': '5'}]
        self.tipo('Como admin → sin_permiso', self.cli.llamar({'action': 'panel_actividades_importar', 'key': self.key, 'comoRol': 'admin', 'filas': filas}), 'sin_permiso')
        antes = set(self.acts())
        r = self.panel('panel_actividades_importar', filas=filas)
        nuevas = set(self.acts()) - antes
        self.creadas += sorted(nuevas)
        self.ok('Informe: 3 agregadas, 1 ya existía, 2 inválidas con su motivo', (r.get('agregadas'), len(r.get('existentes', [])), len(r.get('invalidas', []))) == (3, 1, 2)
                and all(x.get('motivo') for x in r.get('invalidas', [])), '(3, 1, 2)', (r.get('agregadas'), len(r.get('existentes', [])), len(r.get('invalidas', []))))
        acts = self.acts()
        self.ok('Nacen ocultas; la sin ID recibe el siguiente TALnn', all(not acts[i]['publicada'] for i in nuevas) and any(i.startswith('TAL') for i in nuevas - {'TSTI1', 'TSTI2'}),
                'ocultas · TALnn', sorted(nuevas))
        self.ok('La que ya existía no se modificó', acts[uno]['nombre'] != 'Ya existe', 'sin cambios', acts[uno]['nombre'])

    def aj_vaciar(self):
        self.seccion('AJ · Vaciar datos de prueba y cargar la real (R-44, §19.7)')
        self.tipo('Abierto → requiere_cierre', self.panel('panel_vaciar_prueba', llave='VACIAR'), 'requiere_cierre')
        self.tipo('Como admin → sin_permiso', self.cli.llamar({'action': 'panel_vaciar_prueba', 'key': self.key, 'comoRol': 'admin', 'llave': 'VACIAR'}), 'sin_permiso')
        con = self.sql()
        if not con:
            self.omitir('Vaciar de verdad y volver a inscribir', 'requiere --dsn (se hace dentro de una transacción que se deshace)')
            return
        api = lambda **d: (c.execute('select public.api(%s::jsonb)', (json.dumps({'key': self.key, **({'solicitud': str(uuid.uuid4())} if d.get('action') in ESCRITURAS else {}), **d}),)), c.fetchone()[0])[1]
        dias = self.dias(self.acts())
        with con.cursor() as c:
            c.execute('update config set abierto = false where id = 1')
            self.tipo('Sin la llave → valor_invalido', api(action='panel_vaciar_prueba', llave='otra'), 'valor_invalido')
            r = api(action='panel_vaciar_prueba', llave='VACIAR')
            c.execute('select (select count(*) from padron), (select count(*) from actividades), (select count(*) from inscripciones), (select count(*) from organizadores), (select count(*) from config)')
            n = c.fetchone()
            self.ok('Vaciar deja padrón, actividades e inscripciones en cero; config intacta', r.get('tipo') == 'panel' and n[:3] == (0, 0, 0) and n[4] == 1, '(0, 0, 0) · config', n)
            api(action='panel_actividades_importar', filas=[{'id': 'R1', 'tipo': 'VISITA', 'nombre': 'Visita real', 'fecha': dias[0], 'inicio': '08:00', 'fin': '12:00', 'cupo': '20', 'visible': 'SI'},
                                                           {'id': 'R2', 'tipo': 'TALLER', 'nombre': 'Taller real', 'fecha': dias[1], 'inicio': '15:00', 'fin': '18:00', 'cupo': '20', 'visible': 'SI'}])
            dz = self.doc_prueba()
            api(action='panel_padron_importar', filas=[{'documento': dz, 'etapa': '1'}])
            c.execute('update config set abierto = true where id = 1')
            v = api(action='verificar', dni=dz)
            r = api(action='registrar', dni=dz, nombres='Ana', apellidos='Real Prueba', correo='ana@uni.edu.pe', pais='PE', celular='987654321',
                    aceptaPrivacidad=True, aceptaWhatsapp=True, actividades=['R1', 'R2'], ronda=v.get('ronda'))
            self.ok('Con padrón y actividades importados, la base vuelve a inscribir', r.get('tipo') == 'registrado', 'registrado', r.get('tipo'))
        con.rollback()                           # nada de esto queda: la base de prueba sigue como estaba
        con.close()
        self.ok('Después de deshacer, la base de prueba sigue completa', self.resumen()['totales']['padron']['1'] > 100, '> 100 en Etapa 1', self.resumen()['totales']['padron'])

    # ── respaldo y restauración (R-41, §19.5) ──
    def _dsn_con_base(self, base):
        d = self.a.dsn
        if re.match(r'postgres(ql)?://', d):
            return re.sub(r'(://[^/?]*)(/[^?]*)?', lambda m: m.group(1) + '/' + base, d, count=1)
        return d + f' dbname={base}'

    @staticmethod
    def _python(script, *args):
        # UTF-8 en la tubería: en Windows la salida capturada sería cp1252 y "✔" haría fallar al programa
        return subprocess.run([sys.executable, str(RAIZ / 'supabase' / script), *map(str, args)], capture_output=True, text=True, encoding='utf-8',
                              errors='replace', timeout=300, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})

    def _restaurar(self, *args):
        return self._python('restaurar.py', *args)

    def y_respaldo(self):
        self.seccion('Y · Respaldo y restauración (R-41, §19.5)')
        self.tipo('Respaldo como admin → sin_permiso (es del propietario)', self.cli.llamar({'action': 'panel_respaldo', 'key': self.key, 'comoRol': 'admin'}), 'sin_permiso')
        t0 = time.perf_counter()
        h = {'apikey': self.a.anon, **({'Authorization': f'Bearer {self.a.anon}'} if self.a.anon.startswith('eyJ') else {})}
        texto = self.cli.s.post(self.cli.url, json={'p': {'action': 'panel_respaldo', 'key': self.key}}, headers=h, timeout=90).text
        dur = time.perf_counter() - t0
        try:
            r = json.loads(texto)
        except ValueError:
            r = {'tipo': 'respuesta_no_api', 'mensaje': texto[:120]}
        tablas = {'config', 'tipos_actividad', 'padron', 'actividades', 'cruces_permitidos', 'inscripciones', 'inscripcion_actividades', 'organizadores', 'bitacora', 'incidencias'}
        if not self.ok('El propietario descarga el respaldo con las 10 tablas, filas y huellas', r.get('tipo') == 'panel' and set(r.get('tablas', {})) == tablas
                       and set(r.get('huellas', {})) == tablas and len(str(r.get('huella', ''))) == 64, '10 tablas · huellas', sorted(r.get('tablas', {}))):
            return
        print(pinta(GRIS, f"  … respaldo de {len(json.dumps(r)) // 1024} KB en {dur:.1f} s"))
        res = self.resumen()
        t = res['totales']
        self.ok('Las filas del respaldo coinciden con el panel', r['filas']['padron'] == sum(t['padron'].values()) and r['filas']['actividades'] == len(res['actividades'])
                and r['filas']['inscripciones'] == t['inscritos'] + t['anulados'], 'iguales', r['filas'])
        u = res.get('ultimoRespaldo') or {}
        self.ok('El panel muestra el último respaldo (fecha, quién, tamaño)', bool(u.get('fecha')) and 'Tester' in str(u.get('quien')) and u.get('bytes', 0) > 0, 'fecha · Tester · KB', u)
        with tempfile.TemporaryDirectory() as tmp:            # nunca en resultados/: el respaldo tiene datos personales
            f = Path(tmp) / 'respaldo.json'
            f.write_text(texto, encoding='utf-8')        # tal como lo da la base (así lo guarda el panel desde el Sprint 4.1)
            v = self._restaurar(f, '--verificar')
            self.ok('restaurar.py --verificar: huella, filas y versión correctas', v.returncode == 0 and 'íntegro' in v.stdout, 'íntegro', (v.stdout + v.stderr)[-160:])
            g0 = Path(tmp) / 'reescrito.json'
            g0.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding='utf-8')     # como lo guardaba el panel del Sprint 4
            v = self._restaurar(g0, '--verificar')
            self.ok('Un respaldo vuelto a escribir (con otros espacios) también se verifica', v.returncode == 0, 'íntegro', (v.stdout + v.stderr)[-120:])
            mal = json.loads(json.dumps(r))
            fila = (mal['tablas']['padron'] or mal['tablas']['tipos_actividad'])[0]
            fila[next(iter(fila))] = str(fila[next(iter(fila))]) + 'X'
            g = Path(tmp) / 'editado.json'
            g.write_text(json.dumps(mal, ensure_ascii=False), encoding='utf-8')
            v = self._restaurar(g, '--verificar')
            self.ok('Un respaldo editado no pasa la verificación', v.returncode == 1 and 'huella' in v.stdout, 'rechazado por huella', (v.stdout + v.stderr)[-120:])
            v = self._restaurar(g, '--completo')
            self.ok('…ni genera SQL para restaurarlo', v.returncode == 1 and not v.stdout, 'nada', v.stdout[:60])
            if not (self.a.local and self.a.dsn):
                self.omitir('Restaurar en una base nueva y devolver filas borradas', 'solo en local con --local y --dsn (crea y borra una base de prueba)')
                return
            import psycopg2
            nueva = 'ciic_y_' + uuid.uuid4().hex[:8]
            adm = psycopg2.connect(self.a.dsn)
            adm.autocommit = True
            with adm.cursor() as c:
                c.execute(f'create database {nueva}')
            dsn_y = self._dsn_con_base(nueva)
            try:
                y = psycopg2.connect(dsn_y)
                y.autocommit = True
                with y.cursor() as c:
                    c.execute((RAIZ / 'local' / 'supabase_local.sql').read_text(encoding='utf-8'))
                inst = self._python('instalar.py', '--dsn', dsn_y)
                if not self.ok('Base nueva instalada con instalar.py (sin datos)', inst.returncode == 0, 'instalada', inst.stdout[-160:] + inst.stderr[-160:]):
                    y.close()
                    return
                t0 = time.perf_counter()
                v = self._restaurar(f, '--completo', '--dsn', dsn_y)
                print(pinta(GRIS, f'  … --completo en {time.perf_counter() - t0:.1f} s'))
                self.ok('restaurar.py --completo en la base nueva', v.returncode == 0, 'aplicada', (v.stdout + v.stderr)[-200:])
                with y.cursor() as c:
                    c.execute('select privado.crear_clave_admin()')
                    k2 = c.fetchone()[0]
                    c.execute('select public.api(%s::jsonb)', (json.dumps({'action': 'panel_respaldo', 'key': k2}),))
                    r2 = c.fetchone()[0]
                    c.execute("select (privado.integridad() ->> 'ok')::boolean, abierto, ronda, modo from public.config where id = 1")
                    integ, abierto, ronda, modo = c.fetchone()
                comunes = ['tipos_actividad', 'padron', 'actividades', 'cruces_permitidos', 'inscripciones', 'inscripcion_actividades', 'incidencias']
                dist = [x for x in comunes if r2['huellas'][x] != r['huellas'][x]]
                self.ok('Datos restaurados idénticos al respaldo (huella por tabla)', not dist, 'iguales', dist)
                self.ok('Bitácora: la del respaldo más la entrada de la restauración', r2['filas']['bitacora'] == r['filas']['bitacora'] + 1, r['filas']['bitacora'] + 1, r2['filas']['bitacora'])
                self.ok('Restaurada cerrada, con la ronda +1, el mismo modo e integridad OK', integ and not abierto and ronda == r['tablas']['config'][0]['ronda'] + 1
                        and modo == r['tablas']['config'][0]['modo'], 'cerrada · ronda +1 · OK', f'{abierto} · {ronda} · {integ}')
                self.ok('Las cuentas del equipo no se restauran sin su usuario (se invitan de nuevo)', r2['filas']['organizadores'] == 0, 0, r2['filas']['organizadores'])
                v = self._restaurar(f, '--completo', '--dsn', dsn_y)
                self.ok('--completo sobre una base con datos se niega sin cambiar nada', v.returncode == 1 and 'no está vacía' in v.stdout, 'no está vacía', v.stdout[-120:])
                with y.cursor() as c:                  # pérdida parcial a propósito, y un cambio legítimo hecho después del respaldo
                    c.execute("""select i.codigo, (select array_agg(ia.actividad_id order by ia.actividad_id) from public.inscripcion_actividades ia where ia.codigo = i.codigo)
                                 from public.inscripciones i where i.estado = 'CONFIRMADO'
                                   and (select count(*) from public.inscripcion_actividades ia where ia.codigo = i.codigo) = 2 order by i.codigo desc limit 1""")
                    cambiada, acts_antes = c.fetchone()
                    c.execute("""select a.id from public.actividades a where a.tipo = 'TALLER' and a.inscritos < a.cupo and a.id <> all(%s)
                                   and a.fecha = (select fecha from public.actividades where id = %s) order by a.id limit 1""", (acts_antes, acts_antes[-1]))
                    fila = c.fetchone()
                    nueva_act = fila[0] if fila else None
                    if nueva_act:          # como panel_cambiar: la inscripción pasa a otra actividad
                        c.execute('update public.inscripcion_actividades set actividad_id = %s where codigo = %s and actividad_id = %s', (nueva_act, cambiada, acts_antes[-1]))
                    c.execute("""select a.id from public.actividades a where a.publicada
                                   and not exists (select 1 from public.inscripcion_actividades ia where ia.actividad_id = a.id) order by a.id limit 1""")
                    fila = c.fetchone()
                    quitada = fila[0] if fila else None
                    c.execute("""begin; set local ciic.masivo = 'confirmado';
                                 delete from public.inscripciones where codigo in (select codigo from public.inscripciones where codigo <> %s order by codigo limit 10);
                                 delete from public.padron p where p.documento in (select x.documento from public.padron x
                                   where not exists (select 1 from public.inscripciones i where i.documento = x.documento) order by x.documento desc limit 5);
                                 delete from public.bitacora where id in (select id from public.bitacora order by id limit 3);
                                 delete from public.actividades where id = %s; commit;""", (cambiada, quitada))
                    c.execute('select (select count(*) from public.padron), (select count(*) from public.inscripciones), (select count(*) from public.inscripcion_actividades)')
                    falta = c.fetchone()
                    v = self._restaurar(f, '--solo-faltantes', '--simular', '--dsn', dsn_y)
                    c.execute('select (select count(*) from public.padron), (select count(*) from public.inscripciones), (select count(*) from public.inscripcion_actividades)')
                    self.ok('--simular muestra qué volvería y no cambia nada', v.returncode == 0 and 'SIMULACIÓN' in v.stdout and 'agregaría' in v.stdout and c.fetchone() == falta,
                            'informe · sin cambios', (v.stdout + v.stderr)[-160:])
                    s = Path(tmp) / 'faltantes.sql'
                    v = self._restaurar(f, '--solo-faltantes', '--salida', s)
                    c.execute(s.read_text(encoding='utf-8'))          # como en el SQL Editor
                    inf = {x[0]: x for x in c.fetchall()}
                    c.execute("select (select count(*) from public.padron), (select count(*) from public.inscripciones), (select count(*) from public.inscripcion_actividades), "
                              "(privado.integridad() ->> 'ok')::boolean")
                    *despues, integ = c.fetchone()
                    esperado = (r['filas']['padron'], r['filas']['inscripciones'], r['filas']['inscripcion_actividades'])
                    self.ok('--solo-faltantes devuelve lo borrado sin duplicar (SQL Editor)', tuple(despues) == esperado and integ
                            and inf['inscripciones'][2] == esperado[1] - falta[1], f'{esperado} · integridad OK', f'antes {falta} · después {tuple(despues)} · {integ}')
                    c.execute('select array_agg(actividad_id order by actividad_id) from public.inscripcion_actividades where codigo = %s', (cambiada,))
                    ahora = c.fetchone()[0]
                    esperado_c = sorted(acts_antes[:-1] + [nueva_act]) if nueva_act else acts_antes
                    self.ok('Una inscripción cambiada después del respaldo queda como está (no recupera su actividad vieja)', ahora == esperado_c, esperado_c, ahora)
                    if quitada:
                        c.execute('select publicada from public.actividades where id = %s', (quitada,))
                        fila = c.fetchone()
                        self.ok('Una actividad que vuelve, vuelve oculta y figura en el informe', fila is not None and fila[0] is False and quitada in (inf['actividades'][4] or ''),
                                'oculta · en el informe', f'{fila} · {inf["actividades"][4]}')
                    c.execute(s.read_text(encoding='utf-8'))
                    segunda = sum(x[2] for x in c.fetchall() if x[0] != 'config')
                    self.ok('Correrlo otra vez no agrega nada', segunda == 0, 0, segunda)
                    c.execute('update public.config set abierto = true where id = 1')
                    v = self._restaurar(f, '--solo-faltantes', '--dsn', dsn_y)
                    self.ok('Con las inscripciones abiertas, restaurar se niega', v.returncode == 1 and 'Cierra las inscripciones' in v.stdout, 'cerrar antes', v.stdout[-120:])
                    c.execute("update public.config set abierto = false, modo = 'PRODUCCION' where id = 1")
                    v = self._restaurar(f, '--solo-faltantes', '--dsn', dsn_y)
                    self.ok('Un respaldo de PRUEBA no se mezcla con una base en PRODUCCION', v.returncode == 1 and 'no se mezclan' in v.stdout, 'se niega', v.stdout[-120:])
                y.close()
            finally:
                with adm.cursor() as c:
                    c.execute('select pg_terminate_backend(pid) from pg_stat_activity where datname = %s and pid <> pg_backend_pid()', (nueva,))
                    c.execute(f'drop database if exists {nueva}')
                adm.close()

    # ── pasar a producción (R-43) ──
    def af_produccion(self):
        self.seccion('AF · Pasar a producción (R-43)')
        if not self.estado().get('abierto'):
            self.abrir()
        self.tipo('Abierto → requiere_cierre', self.panel('panel_preparar_produccion', llave='PRODUCCION'), 'requiere_cierre')
        self.tipo('Como admin → sin_permiso (es del propietario)', self.cli.llamar({'action': 'panel_preparar_produccion', 'key': self.key, 'comoRol': 'admin', 'llave': 'PRODUCCION'}), 'sin_permiso')
        self.af_ensayo()
        con = self.sql()
        if not con:
            self.cerrar()
            self.tipo('Cerrado y sin la llave → valor_invalido', self.panel('panel_preparar_produccion', llave='otra'), 'valor_invalido')
            self.abrir()
            self.omitir('Pasar a producción de verdad', 'requiere --dsn (se hace dentro de una transacción que se deshace)')
            return
        with con.cursor() as c:
            api = lambda **d: (c.execute('select public.api(%s::jsonb)', (json.dumps({'key': self.key, **({'solicitud': str(uuid.uuid4())} if d.get('action') in ESCRITURAS else {}), **d}),)), c.fetchone()[0])[1]
            c.execute('update config set abierto = false where id = 1')
            self.tipo('Sin la llave → valor_invalido', api(action='panel_preparar_produccion', llave='otra'), 'valor_invalido')
            cuenta = ('select (select count(*) from padron), (select count(*) from actividades), (select count(*) from inscripciones), (select count(*) from inscripcion_actividades), '
                      '(select count(*) from intentos), (select count(*) from privado.trafico), (select count(*) from privado.incidencias), '
                      '(select coalesce(sum(inscritos), 0) from actividades), (select count(*) from privado.claves where nombre = \'ADMIN_KEY\'), '
                      '(select modo from config where id = 1), (select accion from bitacora order by id limit 1), (select count(*) from bitacora)')
            c.execute(cuenta)
            a0 = c.fetchone()
            c.execute("select count(*) from padron where privado.es_doc_de_prueba(documento)")
            zqx = c.fetchone()[0]
            r = api(action='panel_preparar_produccion', llave='PRODUCCION')
            c.execute(cuenta)
            pad, act, ins, ia, intentos, traf, inc, suma, clave, modo, primera, nbit = c.fetchone()
            self.ok('Responde con las inscripciones de prueba eliminadas', r.get('tipo') == 'panel' and r.get('eliminadas') == a0[2], a0[2], r.get('eliminadas', r.get('tipo')))
            self.ok('Vacía inscripciones, intentos, tráfico e incidencias', (ins, ia, intentos, traf, inc) == (0, 0, 0, 0, 0), '(0, 0, 0, 0, 0)', (ins, ia, intentos, traf, inc))
            self.ok('El padrón y las actividades quedan (salvo los documentos del tester, ZQX); los contadores en 0', (pad, act, suma) == (a0[0] - zqx, a0[1], 0)
                    and r.get('padronPrueba') == zqx, (a0[0] - zqx, a0[1], 0), (pad, act, suma))
            self.ok('Modo PRODUCCION y la clave del tester desaparece (R-37)', modo == 'PRODUCCION' and clave == 0, 'PRODUCCION · 0', f'{modo} · {clave}')
            self.ok('La bitácora empieza con "Pasar a producción"', primera == 'Pasar a producción' and nbit <= 2, 'Pasar a producción', f'{primera} ({nbit} entradas)')
            self.tipo('La clave del tester ya no abre el panel', api(action='panel_resumen'), ['no_autorizado', 'modo_produccion'])
            c.execute("select user_id from organizadores where rol = 'propietario' and activo limit 1")
            fila = c.fetchone()
            if not fila and self.a.local:       # solo en local se crean cuentas en auth.users (dentro de esta transacción)
                c.execute('insert into auth.users (email) values (%s) returning id', (f'af-{uuid.uuid4().hex[:6]}@ejemplo.com',))
                fila = c.fetchone()
                c.execute("insert into organizadores (user_id, nombre, rol) values (%s, 'Propietario AF', 'propietario')", (fila[0],))
            if fila:
                c.execute("select set_config('request.jwt.claims', %s, true)", (json.dumps({'role': 'authenticated', 'sub': str(fila[0]), 'aal': 'aal2'}),))
                self.tipo('Ya en PRODUCCION → modo_produccion', api(action='panel_preparar_produccion', llave='PRODUCCION'), 'modo_produccion')
            else:
                self.omitir('Ya en PRODUCCION → modo_produccion', 'sin cuenta de propietario en esta base')
        con.rollback()                           # nada de esto queda: la base de prueba sigue como estaba
        con.close()
        p = self.cli.llamar({'action': 'admin_ping', 'key': self.key})
        self.ok('Después de deshacer: modo PRUEBA y la clave del tester funciona', p.get('tipo') == 'admin' and p['config']['modo'] == 'PRUEBA', 'admin · PRUEBA', p.get('tipo'))

    def af_ensayo(self):
        """Pasar a producción y Vaciar POR LA API REAL (con safeupdate en Supabase), deshechos en la misma llamada (migración 09)."""
        res = self.resumen()
        ins0, abierto0 = res['totales']['inscritos'] + res['totales']['anulados'], res['config']['abierto']
        pad0 = sum(res['totales']['padron'].values())
        self.tipo('Ensayo de otra acción → valor_invalido', self.cli.llamar({'action': 'admin_ensayo', 'key': self.key, 'que': 'panel_quitar'}), 'valor_invalido')
        for que, nombre in (('panel_preparar_produccion', 'Pasar a producción'), ('panel_vaciar_prueba', 'Vaciar datos de prueba')):
            e = self.cli.llamar({'action': 'admin_ensayo', 'key': self.key, 'que': que})
            d, desp = e.get('durante') or {}, e.get('despues') or {}
            if not self.ok(f'Ensayo de "{nombre}" por la API real: funciona (safeupdate y disparadores incluidos)',
                           e.get('tipo') == 'admin' and e.get('ok') is True and (e.get('respuesta') or {}).get('tipo') == 'panel', 'panel',
                           e.get('error') or (e.get('respuesta') or {}).get('tipo') or e.get('tipo')):
                continue
            if que == 'panel_preparar_produccion':
                bien = (d.get('modo') == 'PRODUCCION' and d.get('clave') is False and d.get('inscripciones') == 0 and d.get('inscritos') == 0
                        and d.get('padronPrueba') == 0 and d.get('actividades', 0) > 0 and d.get('bitacoraPrimera') == 'Pasar a producción' and d.get('integridad'))
                self.ok('…durante: modo PRODUCCION, sin clave, sin inscripciones ni documentos del tester, actividades intactas', bien, 'así', d)
            else:
                bien = d.get('modo') == 'PRUEBA' and d.get('clave') is True and (d.get('padron'), d.get('actividades'), d.get('inscripciones')) == (0, 0, 0)
                self.ok('…durante: padrón, actividades e inscripciones en 0; modo y clave intactos', bien, 'así', d)
            self.ok(f'…y se deshizo: modo PRUEBA, clave del tester, padrón e inscripciones como antes', desp.get('modo') == 'PRUEBA' and desp.get('clave') is True
                    and desp.get('inscripciones') == ins0 and desp.get('padron') == pad0 and desp.get('abierto') == abierto0, f'PRUEBA · {pad0} · {ins0}', desp)

    # ── navegador ──
    def p_navegador(self):
        self.seccion('P · Página y panel en un navegador (v5.5)')
        if not self.a.web:
            self.omitir('Pruebas en navegador', 'sin --web (o sin WEB_URL)')
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.omitir('Pruebas en navegador', 'falta playwright: pip install playwright && python -m playwright install chromium')
            return
        fotos = self.salida / 'capturas'
        fotos.mkdir(exist_ok=True)
        web = self.a.web.rstrip('/') + '/'
        config_js = ('window.CIIC_CONFIG = ' + json.dumps({'MODO': 'real', 'API_URL': self.a.api, 'ANON_KEY': self.a.anon, 'NOMBRE_EVENTO': 'Tester',
                     'AVISO_PRIVACIDAD': 'Aviso de prueba del tester.', 'SUPABASE_JS': leer_de_config('SUPABASE_JS') or '',
                     'SUPABASE_JS_SRI': leer_de_config('SUPABASE_JS_SRI') or ''}) + ';')
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            ctx = nav.new_context()
            # La página publicada apunta al proyecto de su config.js (en producción, el real): el tester la prueba contra --api.
            ctx.route('**/config.js', lambda ruta: ruta.fulfill(status=200, content_type='application/javascript; charset=utf-8', body=config_js))

            def pagina(ancho, alto):
                x = ctx.new_page()
                x.set_viewport_size({'width': ancho, 'height': alto})
                return x
            pg = pagina(1280, 900)
            errores = []
            pg.on('pageerror', lambda e: errores.append(str(e)))
            try:
                pg.goto(web + 'index.html')
                pg.wait_for_selector('#form-doc', timeout=15000)
                pg.screenshot(path=str(fotos / '01-inicio.png'))
                d = self.tomar(1)
                pg.fill('#doc', d)
                pg.click('#btn-verificar')
                pg.wait_for_selector('[data-pantalla="2"]:not([hidden])', timeout=20000)
                self.ok('Página: un documento válido pasa a la pantalla 2', True)
                ids = self.combo(self.acts())
                for i in ids:
                    pg.click(f'[data-actividad="{i}"]')
                pg.fill('#nombres', NOMBRES)
                pg.fill('#apellidos', APELLIDOS)
                pg.fill('#celular', self.celular(d))
                pg.check('#acepta')
                pg.click('#btn-confirmar')
                pg.wait_for_selector('#msg-2 [data-tipo="datos_invalidos"]', timeout=10000)
                self.ok('Página: sin correo no deja confirmar', True)
                pg.fill('#correo', f'navegador.{d}@tester.edu.pe')
                pg.screenshot(path=str(fotos / '02-eleccion.png'), full_page=True)
                pg.click('#btn-confirmar')
                pg.wait_for_selector('[data-pantalla="3"]:not([hidden])', timeout=30000)
                self.usados.add(d)
                txt = pg.inner_text('[data-pantalla="3"]')
                self.ok('Página: confirmación única, sin código y con las 2 actividades', 'CIIC-' not in txt and d in txt and pg.locator('#comprobante [data-actividad]').count() == 2,
                        'sin código · 2', pg.locator('#comprobante [data-actividad]').count())
                pg.screenshot(path=str(fotos / '03-confirmacion.png'), full_page=True)
                pg.click('#btn-inicio')
                pg.fill('#doc', d)
                pg.click('#btn-verificar')
                pg.wait_for_selector('#msg-1 [data-tipo="duplicado"]', timeout=15000)
                self.ok('Página: el mismo documento → solo el aviso de ya inscrito', 'CIIC-' not in pg.inner_text('#msg-1'), 'sin datos', '')
                d2 = self.tomar(1)
                pg.fill('#doc', d2)
                pg.click('#btn-verificar')
                pg.wait_for_selector('[data-pantalla="2"]:not([hidden])', timeout=20000)
                self.cerrar()
                pg.evaluate('document.dispatchEvent(new Event("visibilitychange"))')
                pg.wait_for_selector('[data-pantalla="1"]:not([hidden]) [data-tipo="cerrado"]', timeout=15000)
                self.ok('Página: al cerrar mientras elige, vuelve al inicio con "cerrado"', True)
                self.abrir()
                pg.fill('#doc', '00000001')
                pg.click('#btn-verificar')
                pg.wait_for_selector('#msg-1 [data-tipo="no_encontrado"]', timeout=15000)
                self.ok('Página: muestra los intentos restantes', 'intento' in pg.inner_text('#msg-1'), 'intentos', '')
                m = pagina(390, 844)
                m.goto(web + 'index.html')
                m.wait_for_selector('#form-doc')
                self.ok('Página en celular sin desplazamiento lateral', m.evaluate('document.documentElement.scrollWidth') <= 392, '≤ 390', m.evaluate('document.documentElement.scrollWidth'))
                pp = pagina(1360, 900)
                pp.on('pageerror', lambda e: errores.append(str(e)))
                pp.goto(web + 'panel.html')
                pp.click('#modo-prueba')
                pp.fill('#clave-prueba', self.key)
                pp.select_option('#como-rol', 'propietario')
                pp.click('#btn-entrar-prueba')
                pp.wait_for_function("document.querySelector('#estado-sis') && document.querySelector('#estado-sis').textContent.includes('ABIERTO')", timeout=20000)
                self.ok('Panel: entra con la clave de prueba', True)
                pp.screenshot(path=str(fotos / '04-panel.png'), full_page=True)
                a = list(self.acts().values())[0]
                paso = self.resumen()['config']['pasoCupo']
                pp.click(f'[data-mas="{a["id"]}"]')
                pp.wait_for_timeout(1500)
                self.ok('Panel: +paso amplía el cupo', self.acts()[a['id']]['cupo'] == a['cupo'] + paso, a['cupo'] + paso, self.acts()[a['id']]['cupo'])
                pp.click(f'[data-menos="{a["id"]}"]')
                pp.wait_for_selector('#avisos [data-tipo="requiere_cierre"]', timeout=10000)
                self.ok('Panel: −paso abierto avisa requiere_cierre', True)
                self.cerrar()
                self.panel('panel_actividad', id=a['id'], cupo=a['cupo'], confirmar=True)
                self.abrir()
                pp.click('[data-tab="listas"]')
                pp.select_option('#l-act', ids[0])
                # Espera la lista de ESA actividad (la de la pestaña puede llegar después): antes, el clic caía en una fila vieja (Sprint 3, GitHub)
                pp.wait_for_function("(id) => { const f = [...document.querySelectorAll('#l-tabla tr[data-codigo]')];"
                                     " return f.length > 0 && f.every((x) => x.children[1].textContent === id); }", arg=ids[0], timeout=20000)
                primero = pp.locator('#l-tabla [data-grupo]').first
                cod, antes = primero.get_attribute('data-grupo'), primero.get_attribute('data-en-grupo')
                primero.click()
                marca = "([c, a]) => { const b = document.querySelector('#l-tabla [data-grupo=\"' + c + '\"]'); return !!b && b.getAttribute('data-en-grupo') !== a; }"
                pp.wait_for_function(marca, arg=[cod, antes], timeout=20000)
                self.ok('Panel: marcar en el grupo se guarda y se relee', True)
                pp.locator(f'#l-tabla [data-grupo="{cod}"]').click()
                pp.wait_for_function(marca, arg=[cod, 'true' if antes == 'false' else 'false'], timeout=20000)
                for t in ('participantes', 'actividades', 'listas', 'sistema'):
                    pp.click(f'[data-tab="{t}"]')
                    pp.wait_for_timeout(700)
                    pp.screenshot(path=str(fotos / f'05-panel-{t}.png'), full_page=True)
                self.ok('Panel: las cinco pestañas abren sin errores', not errores, 'sin errores', errores[:2])
                pp.click('[data-tab="sistema"]')
                with pp.expect_download(timeout=30000) as descarga:
                    pp.click('#btn-respaldo')
                with tempfile.TemporaryDirectory() as tmp:          # el respaldo nunca queda en resultados/
                    f = Path(tmp) / 'respaldo.json'
                    descarga.value.save_as(str(f))
                    v = self._restaurar(f, '--verificar')
                    self.ok('Panel: "Descargar respaldo" baja un archivo que restaurar.py verifica', v.returncode == 0, 'íntegro', (v.stdout + v.stderr)[-120:])
            except Exception as e:  # noqa: BLE001
                self.ok('Navegador sin errores', False, 'sin errores', str(e)[:200])
                pg.screenshot(path=str(fotos / 'error.png'))
            self.p_inicio_sesion(nav, web)
            self.p_publicada(nav, web)
            nav.close()

    SUPABASE_FALSO = """(() => {
  const UID = '__UID__', K = 'ciic-falso-sesion';
  const leer = () => { try { return JSON.parse(localStorage.getItem(K)); } catch (e) { return null; } };
  const poner = (s) => { if (s) localStorage.setItem(K, JSON.stringify(s)); else localStorage.removeItem(K); };
  window.supabase = { createClient(url, key, o) {
    // Como supabase-js 2.45: si la URL trae un error (#error=…) y detectSessionInUrl, descarta la sesión guardada.
    if (o && o.auth && o.auth.detectSessionInUrl && /error/.test(location.hash + location.search)) poner(null);
    return { auth: {
      async getSession() { return { data: { session: leer() } }; },
      async signInWithPassword() { poner({ access_token: 'local:' + UID + ':aal1' }); return { data: {}, error: null }; },
      async signOut() { poner(null); return {}; },
      async resetPasswordForEmail() { return {}; },
      async updateUser() { return { error: null }; },
      mfa: {
        async listFactors() { return { data: { totp: [{ id: 'f1', status: 'verified' }] } }; },
        async enroll() { return { data: null, error: { message: 'sin alta' } }; },
        async challenge() { return { data: { id: 'c1' }, error: null }; },
        async verify() { poner({ access_token: 'local:' + UID + ':aal2' }); return { error: null }; },
      } } };
  } };
})();"""

    def p_inicio_sesion(self, nav, web):
        """Inicio de sesión del panel con Supabase Auth simulado (sin cuentas reales): el aviso de 'sin rol' y el #error de un enlace usado."""
        if not (self.a.local and self.a.dsn):
            self.omitir('Panel: inicio de sesión con una cuenta sin rol (Auth simulado)', 'solo en local con --local y --dsn')
            return
        import psycopg2
        con = psycopg2.connect(self.a.dsn)
        con.autocommit = True
        with con.cursor() as c:
            c.execute('insert into auth.users (email) values (%s) returning id', (f'sinrol-{uuid.uuid4().hex[:6]}@ejemplo.com',))
            uid = str(c.fetchone()[0])
        cfg = 'window.CIIC_CONFIG = ' + json.dumps({'MODO': 'real', 'API_URL': self.a.api, 'ANON_KEY': self.a.anon, 'NOMBRE_EVENTO': 'Tester',
                                                    'SUPABASE_JS': 'https://supabase.prueba.invalid/supabase.js', 'SUPABASE_JS_SRI': ''}) + ';'
        ctx = nav.new_context()
        ctx.route('**/config.js', lambda r: r.fulfill(status=200, content_type='application/javascript; charset=utf-8', body=cfg))
        ctx.route('https://supabase.prueba.invalid/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=self.SUPABASE_FALSO.replace('__UID__', uid)))
        pp = ctx.new_page()
        visible = lambda tipo: pp.wait_for_selector(f'#msg-login [data-tipo="{tipo}"]', state='visible', timeout=15000)
        try:
            pp.goto(web + 'panel.html')
            pp.fill('#correo', 'sin.rol@ejemplo.com')
            pp.fill('#clave', 'una-clave-de-prueba')
            pp.click('#btn-entrar')
            pp.wait_for_selector('#paso-codigo:not([hidden])', timeout=15000)
            pp.fill('#codigo6', '123456')
            pp.click('#btn-codigo')
            visible('sin_permiso')
            self.ok('Panel: tras el código, una cuenta sin rol VE el aviso (Sprint 3: quedaba oculto)', 'rol' in pp.inner_text('#msg-login'), 'aviso visible', pp.inner_text('#msg-login')[:80])
            pp.goto('about:blank')
            pp.goto(web + 'panel.html#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid+or+has+expired')
            visible('sin_permiso')
            self.ok('Panel: con #error en la URL y la sesión guardada, no la pierde y limpia la URL', pp.evaluate('location.hash') == '', 'sin #error', pp.evaluate('location.hash'))
            pp.evaluate("localStorage.removeItem('ciic-falso-sesion')")
            pp.goto('about:blank')
            pp.goto(web + 'panel.html#error=access_denied&error_code=otp_expired')
            visible('enlace_usado')
            self.ok('Panel: el enlace de invitación ya usado explica que se entra con correo y contraseña', 'una sola vez' in pp.inner_text('#msg-login'), 'una sola vez', pp.inner_text('#msg-login')[:80])
        except Exception as e:  # noqa: BLE001
            self.ok('Panel: inicio de sesión simulado sin errores', False, 'sin errores', str(e)[:200])
        finally:
            ctx.close()
            with con.cursor() as c:
                c.execute('delete from auth.users where id = %s', (uid,))
            con.close()

    def config_publicada(self, nav, web):
        """La página publicada con SU config.js, sin inyectar nada (Sprint 3: una publicación quedó en demo y no se veía)."""
        ctx = nav.new_context()
        pg = ctx.new_page()
        try:
            pg.goto(web + 'index.html')
            pg.wait_for_selector('#form-doc', timeout=20000)
            pg.wait_for_timeout(3000)
            cfg = pg.evaluate('window.CIIC_CONFIG || {}')
            demo = pg.evaluate("(() => { const c = document.getElementById('demo-cinta'); return !!c && !c.hidden && c.offsetParent !== null; })()")
            error = pg.evaluate("[...document.querySelectorAll('[data-tipo=\"config\"], [data-tipo=\"sin_conexion\"]')].filter((x) => x.offsetParent !== null).map((x) => x.textContent).join(' | ')")
        finally:
            ctx.close()
        api = str(cfg.get('API_URL', ''))
        self.ok('Página publicada en modo real (sin la cinta de demo)', str(cfg.get('MODO', '')).lower() == 'real' and not demo, 'real', cfg.get('MODO'))
        self.ok('Página publicada con API_URL y ANON_KEY', api.startswith('https://') and 'PEGA_AQUI' not in api + str(cfg.get('ANON_KEY', '')), 'configuradas', api[:40])
        self.ok('Página publicada responde con su configuración', not error, 'sin error de conexión', error[:100])
        self.ok('supabase-js con hash de integridad (SRI, §18)', str(cfg.get('SUPABASE_JS_SRI', '')).startswith('sha384-'), 'sha384-…', str(cfg.get('SUPABASE_JS_SRI', ''))[:20])
        modo = None
        try:
            r = requests.post(api.rstrip('/') + '/rest/v1/rpc/api', json={'p': {'action': 'estado'}}, timeout=20,
                              headers={'apikey': cfg.get('ANON_KEY', ''), **({'Authorization': 'Bearer ' + cfg['ANON_KEY']} if str(cfg.get('ANON_KEY', '')).startswith('eyJ') else {})})
            modo = r.json().get('modo')
        except Exception:  # noqa: BLE001
            pass
        destino = 'al proyecto que prueba este tester' if api.rstrip('/') == self.a.api.rstrip('/') else 'a otro proyecto'
        print(pinta(GRIS, f'  … la página publicada apunta {destino} (modo {modo})'))
        corchetes = re.findall(r'\[[^\]\n]{3,60}\]', str(cfg.get('AVISO_PRIVACIDAD', '')))
        if modo == 'PRODUCCION':
            self.ok('Aviso de privacidad completo, sin [corchetes] (D6, §11.3)', not corchetes, 'completo', corchetes[:3])
        elif corchetes:
            self.omitir('Aviso de privacidad completo', f'aún con {len(corchetes)} [corchetes]: completarlo antes de la apertura (Sprint 6)')
        else:
            self.ok('Aviso de privacidad completo, sin [corchetes] (D6, §11.3)', True)

    def p_publicada(self, nav, web):
        if re.search(r'//(127\.0\.0\.1|localhost)[:/]', web):
            self.omitir('Página publicada con su propio config.js', 'solo contra la página publicada (GitHub Pages)')
            return
        try:
            self.config_publicada(nav, web)
        except Exception as e:  # noqa: BLE001
            self.ok('Página publicada con su propio config.js', False, 'carga', str(e)[:200])

    def q_carga(self):
        n = self.a.personas
        self.seccion(f'Q · Carga: {n} personas confirman a la vez')
        if n <= 0:
            self.omitir('Carga', 'personas = 0')
            return
        self.config(etapas=[1, 2], etapasVisita=[1, 2])
        docs = []
        for e in ('1', '2'):
            while len(docs) < n and self.muestra[e]:
                d = self.muestra[e].pop(0)
                if d not in self.usados:
                    docs.append(d)
        for x in self.acts().values():          # sobra cupo en los talleres: la carga mide inscripciones completas (limpiar() restaura)
            if x['publicada'] and x['tipo'] == 'TALLER':
                self.panel('panel_actividad', id=x['id'], cupo=x['cupo'] + n)
        acts0 = self.acts()
        dias = self.dias(acts0)[:2]
        lat = []

        def persona(d):
            t0 = time.perf_counter()
            v = self.cli.llamar({'action': 'verificar', 'dni': d}, paciente=True)
            if v.get('tipo') != 'ok':
                return v.get('tipo'), 0
            a = self.acts_cache
            opciones = [x for x in a.values() if x['publicada'] and x['disponibles'] > 0]
            v1 = [x['id'] for x in opciones if x['fecha'] == dias[0] and (x['tipo'] == 'TALLER' or v.get('puedeVisita'))]
            v2 = [x['id'] for x in opciones if x['fecha'] == dias[1] and x['tipo'] == 'TALLER']
            ids = [random.choice(v1), random.choice(v2)]
            r = self.reg(d, ids, ronda=v['ronda'], paciente=True)
            return r.get('tipo'), time.perf_counter() - t0

        self.acts_cache = acts0
        with cf.ThreadPoolExecutor(n) as ex:
            rs = list(ex.map(persona, docs))
        tipos = [r[0] for r in rs]
        lat = sorted(r[1] for r in rs if r[1])
        p95 = lat[int(len(lat) * 0.95) - 1] if lat else 0
        print(pinta(GRIS, f"  … registradas {tipos.count('registrado')} · llenas {tipos.count('lleno')} · otras {len(tipos) - tipos.count('registrado') - tipos.count('lleno')} · p95 {p95:.1f} s"))
        self.ok('Nadie termina con error', set(tipos) <= {'registrado', 'lleno', 'combinacion_invalida'}, 'registrado o lleno', set(tipos))
        acts = self.acts()
        self.ok('Ninguna actividad con sobrecupo', all(a['inscritos'] <= a['cupo'] for a in acts.values()), 'ninguna', '')
        self.ok('95 % con respuesta en menos de 60 s', p95 < 60, '< 60 s', f'{p95:.1f} s')
        reg = self.panel('panel_registros')
        i_doc, i_est = reg['encabezados'].index('Documento'), reg['encabezados'].index('Estado')
        docs_conf = [f[i_doc] for f in reg['filas'] if f[i_est] == 'CONFIRMADO']
        self.ok('Nadie quedó inscrito dos veces', len(docs_conf) == len(set(docs_conf)), 'únicos', len(docs_conf) - len(set(docs_conf)))
        self.config(etapas=[1, 2], etapasVisita=[1])

    def w_carga(self):
        n = self.a.personas_w
        self.seccion(f'W · {n} personas navegan y confirman a la vez (llegan en {self.a.rampa_w:g} s); alerta de saturación (R-34)')
        if n <= 0:
            self.omitir('Carga de W y alerta de saturación', 'personas-w = 0')
            return
        docs = [self.doc_prueba() for _ in range(n)]          # padrón sintético (ZQX…): admin_limpiar lo borra al final
        r = self.panel('panel_padron_importar', filas=[{'documento': d, 'etapa': '1'} for d in docs])
        if not self.ok(f'Padrón sintético de {n} personas (ZQX, se borra al final)', r.get('agregados') == n, n, r.get('agregados', r.get('tipo'))):
            return
        self.config(etapas=[1, 2], etapasVisita=[1, 2])
        for x in self.acts().values():          # cupo de sobra en los talleres (limpiar() lo restaura)
            if x['publicada'] and x['tipo'] == 'TALLER':
                self.panel('panel_actividad', id=x['id'], cupo=x['cupo'] + n)
        dias = self.dias(self.acts())[:2]

        def persona(d):
            time.sleep(random.random() * self.a.rampa_w)   # llegan repartidas en unos segundos (--rampa-w)
            t0 = time.perf_counter()
            for _ in range(random.randint(1, 3)):       # navega como la página: estado con actividades, cada tanto
                self.cli.llamar({'action': 'estado', 'conActividades': True}, paciente=True)
                time.sleep(random.random() * 0.4)
            v = self.cli.llamar({'action': 'verificar', 'dni': d}, paciente=True)
            if v.get('tipo') != 'ok':
                return v.get('tipo'), 0, 0, []
            ops = [x for x in v.get('actividades', []) if x['disponibles'] > 0]
            v1 = [x['id'] for x in ops if x['fecha'] == dias[0] and (x['tipo'] == 'TALLER' or v.get('puedeVisita'))]
            v2 = [x['id'] for x in ops if x['fecha'] == dias[1] and x['tipo'] == 'TALLER']
            if not v1 or not v2:
                return 'sin_opciones', 0, 0, []
            t1 = time.perf_counter()
            ids = [random.choice(v1), random.choice(v2)]
            r = self.reg(d, ids, ronda=v['ronda'], paciente=True)
            return r.get('tipo'), time.perf_counter() - t0, time.perf_counter() - t1, ids

        t0 = time.perf_counter()
        with cf.ThreadPoolExecutor(n) as ex:
            rs = list(ex.map(persona, docs))
        dur = time.perf_counter() - t0
        tipos = [x[0] for x in rs]
        tot = sorted(x[1] for x in rs if x[1])
        con = sorted(x[2] for x in rs if x[2])
        pct = lambda l, q: l[max(int(len(l) * q) - 1, 0)] if l else 0
        print(pinta(GRIS, f"  … {dur:.0f} s · registradas {tipos.count('registrado')} · llenas {tipos.count('lleno')} · otras {len(tipos) - tipos.count('registrado') - tipos.count('lleno')}"
                          f" · de principio a fin p50 {pct(tot, .5):.1f} s, p95 {pct(tot, .95):.1f} s · confirmar p50 {pct(con, .5):.1f} s, p95 {pct(con, .95):.1f} s"))
        self.ok('Nadie termina con error', set(tipos) <= {'registrado', 'lleno', 'combinacion_invalida'}, 'registrado o lleno', sorted(set(tipos) - {'registrado', 'lleno', 'combinacion_invalida'}))
        acts = self.acts()
        falsos = [x[3] for x in rs if x[0] == 'lleno' and not any(acts[i]['inscritos'] >= acts[i]['cupo'] for i in x[3])]
        self.ok('Cada "lleno" corresponde a una actividad que de verdad se llenó', not falsos, 'ninguno falso', falsos[:3])
        self.ok('Quien eligió talleres con cupo de sobra quedó inscrito', all(x[0] == 'registrado' for x in rs
                if x[3] and all(acts[i]['tipo'] == 'TALLER' for i in x[3])), 'todos', '')
        self.ok('Ninguna actividad con sobrecupo', all(a['inscritos'] <= a['cupo'] for a in acts.values()), 'ninguna', [a['id'] for a in acts.values() if a['inscritos'] > a['cupo']])
        reg = self.panel('panel_registros')
        i_doc, i_est = reg['encabezados'].index('Documento'), reg['encabezados'].index('Estado')
        conf = [f[i_doc] for f in reg['filas'] if f[i_est] == 'CONFIRMADO']
        self.ok('Nadie quedó inscrito dos veces', len(conf) == len(set(conf)), 'únicos', len(conf) - len(set(conf)))
        self.ok('Integridad de contadores después de la carga', self.resumen()['integridad']['ok'], 'OK', self.resumen()['integridad'])
        self.ok('95 % con respuesta en menos de 60 s', pct(tot, .95) < 60, '< 60 s', f'{pct(tot, .95):.1f} s')
        self.config(etapas=[1, 2], etapasVisita=[1])
        self.w_trafico()

    def w_trafico(self):
        """R-34 con el umbral bajado por el tester: una ráfaga de una ventana no alerta; 3 ventanas seguidas, sí."""
        u0 = self.cfg0.get('umbral', 2000)
        umbral = 100
        print(pinta(GRIS, '  … 31 s de calma para que la carga anterior no cuente (ventanas de 10 s)'))
        time.sleep(31)
        r = self.config(umbral=umbral)
        if not self.ok(f'El propietario baja el umbral a {umbral}', r.get('tipo') == 'panel' and r['config'].get('umbral') == umbral, umbral, r.get('config', {}).get('umbral', r.get('tipo'))):
            return
        self.tipo('Cambiar el umbral como admin → sin_permiso (nivel 3)', self.cli.llamar({'action': 'panel_config', 'key': self.key, 'comoRol': 'admin', 'umbral': 500}), 'sin_permiso')
        self.tipo('Umbral fuera de rango → valor_invalido', self.panel('panel_config', umbral=50), 'valor_invalido')
        t0 = time.perf_counter()
        with cf.ThreadPoolExecutor(20) as ex:                  # ráfaga: 3 veces el umbral, todo lo rápido posible
            list(ex.map(lambda _: self.cli.llamar({'action': 'estado'}), range(3 * umbral)))
        rafaga = time.perf_counter() - t0
        vio = []
        fin = time.time() + 32
        while time.time() < fin:                               # 3 ventanas más, mirando el panel cada 5 s (2 llamadas por ventana)
            tr = self.resumen().get('trafico', {})
            vio.append(bool(tr.get('alerta')))
            time.sleep(5)
        if rafaga < 12:
            self.ok(f'Una ráfaga de {3 * umbral} llamadas en {rafaga:.1f} s no enciende la alerta', not any(vio), 'sin alerta', vio)
        else:
            self.omitir('Ráfaga sin alerta', f'la ráfaga tardó {rafaga:.0f} s: no cabe en una o dos ventanas')
        alto = threading.Event()

        def sostener():
            while not alto.is_set():
                self.cli.llamar({'action': 'estado'})

        t0 = time.time()
        with cf.ThreadPoolExecutor(12) as ex:                  # ritmo sostenido muy por encima del umbral durante 4 ventanas y media
            for _ in range(12):
                ex.submit(sostener)
            time.sleep(45)
            alto.set()
        tr = self.resumen().get('trafico', {})
        print(pinta(GRIS, f"  … tráfico: ventana actual {tr.get('ventana10s')} · pico {tr.get('pico10s')} por ventana de 10 s"))
        self.ok('Sostenido 3 ventanas sobre el umbral → alerta en el panel', tr.get('alerta') is True, 'alerta', tr)
        self.ok('El pico por ventana se informa', (tr.get('pico10s') or 0) > umbral, f'> {umbral}', tr.get('pico10s'))
        con = self.sql()
        if con:
            with con.cursor() as c:
                c.execute("select count(*) from bitacora where accion = 'Alerta de saturación' and creado_en > to_timestamp(%s)", (t0 - 5,))
                self.ok('La alerta queda en la bitácora', c.fetchone()[0] >= 1, '≥ 1', '')
            con.rollback()
            con.close()
        r = self.config(umbral=u0)
        self.ok('El umbral vuelve a su valor', r.get('config', {}).get('umbral') == u0, u0, r.get('config', {}).get('umbral'))

    def limpiar(self):
        self.seccion('Limpieza (deja todo como estaba)')
        r = self.cli.llamar({'action': 'admin_limpiar', 'key': self.key, 'docs': sorted(self.usados), 'padron': sorted(self.padron_nuevo), 'intentos': True})
        self.ok('Se borraron solo las inscripciones del tester', r.get('tipo') == 'admin', 'admin', r.get('tipo'))
        self.cerrar()
        for nid in self.creadas:
            self.panel('panel_actividad', id=nid, publicada=False)
            self.panel('panel_quitar', id=nid)
        for a, b in self.cruces_nuevos:
            self.panel('panel_cruce', a=a, b=b, permitido=False)
        for i, a0 in self.acts0.items():
            self.panel('panel_actividad', id=i, cupo=a0['cupo'], publicada=a0['publicada'], confirmar=True)
            self.panel('panel_editar', id=i, grupoModo=a0['grupoModo'], grupo=a0['grupo'], descripcion=a0['descripcion'])
        c = self.cfg0
        self.panel('panel_config', etapas=c['etapas'], etapasVisita=c['etapasVisita'], dosTalleres=c['dosTalleres'], pasoCupo=c['pasoCupo'],
                   refresco=c['refresco'], limiteDispositivo=c['limiteDispositivo'], limiteRed=c['limiteRed'], **({'umbral': c['umbral']} if 'umbral' in c else {}))
        self.panel('panel_horarios', mismoDia=c['mismoDia'], margenMin=c['margenMin'])
        if c['abierto']:
            self.abrir()
        if hasattr(self, '_equipo'):
            con, ids = self._equipo
            with con.cursor() as cur:
                cur.execute('delete from auth.users where id = any(%s::uuid[])', (list(ids.values()),))
            con.close()
        fin = self.acts()
        self.ok('Cupos, visibilidad y entrega del grupo como al inicio', all(fin[i]['cupo'] == a['cupo'] and fin[i]['publicada'] == a['publicada'] and fin[i]['grupoModo'] == a['grupoModo']
                                                                            for i, a in self.acts0.items()), 'iguales', '')
        self.ok('Inscritos como al inicio', all(fin[i]['inscritos'] == a['inscritos'] for i, a in self.acts0.items()), 'iguales', '')
        self.ok('Las actividades del tester se quitaron', not any(i in fin for i in self.creadas), 'quitadas', [i for i in self.creadas if i in fin])
        p = self.cli.llamar({'action': 'admin_ping', 'key': self.key})['config']
        claves = [k for k in ('abierto', 'etapas', 'etapasVisita', 'dosTalleres', 'mismoDia', 'margenMin', 'pasoCupo', 'refresco', 'limiteDispositivo',
                              'limiteRed', 'umbral') if k in c]
        self.ok('Configuración como al inicio (la ronda queda más alta)', all(p.get(k) == c[k] for k in claves), 'igual', {k: p.get(k) for k in claves if p.get(k) != c[k]})

    def lectura(self):
        self.a_conexion(solo_lectura=True)
        self.seccion('Lectura · página')
        r = self.api(action='verificar', dni='1')
        self.tipo('Formato inválido responde formato', r, 'formato')
        if self.a.web:                      # en la apertura: la página publicada con su config.js (no cambia nada)
            self.seccion('Lectura · página publicada')
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                self.omitir('Página publicada', 'falta playwright')
                return
            with sync_playwright() as pw:
                nav = pw.chromium.launch()
                try:
                    self.config_publicada(nav, self.a.web.rstrip('/') + '/')
                except Exception as e:  # noqa: BLE001
                    self.ok('Página publicada con su propio config.js', False, 'carga', str(e)[:200])
                nav.close()

    def reporte(self, error, dur):
        pasan = sum(1 for r in self.res if r['ok'] is True)
        fallan = sum(1 for r in self.res if r['ok'] is False)
        omit = sum(1 for r in self.res if r['ok'] is None)
        lat = sorted(self.cli.latencias)
        prom = sum(lat) / len(lat) if lat else 0
        print(pinta(AZUL, '\n' + '═' * 70))
        if error:
            print(pinta(ROJO, f'  ⛔ {error}'))
        print((pinta(VERDE, f'  ✅ {pasan} de {pasan + fallan} pruebas pasaron.') if not fallan and not error
               else pinta(ROJO, f'  ❌ {fallan} de {pasan + fallan} pruebas fallaron.')) + (f' ({omit} omitidas)' if omit else ''))
        print(f'  Duración: {int(dur // 60)} min {int(dur % 60)} s · Respuesta promedio de la API: {prom:.2f} s · Llamadas: {len(lat)} · Reintentos: {self.cli.reintentos}'
              + (' (' + ', '.join(f'{k} ×{v}' for k, v in sorted(self.cli.motivos.items())) + ')' if self.cli.motivos else ''))
        for k, v in sorted(self.cli.ejemplos.items()):
            print(pinta(GRIS, f'  · primer {k}: {self.mascara(v)}'))
        print(pinta(AZUL, '═' * 70))
        (self.salida / 'resultados.json').write_text(json.dumps({'pasan': pasan, 'fallan': fallan, 'omitidas': omit, 'error': error, 'reintentos': self.cli.motivos,
                                                                 'causas': {k: self.mascara(v) for k, v in self.cli.ejemplos.items()}, 'pruebas': self.res},
                                                                ensure_ascii=False, indent=1), encoding='utf-8')
        md = ['# Reporte del tester · v5.5 (Sprint 4)', '', f'**{pasan} de {pasan + fallan} pruebas pasaron**' + (f' · {omit} omitidas' if omit else ''), '']
        if error:
            md += [f'> ⛔ {error}', '']
        md += ['| | Bloque | Prueba | Esperado | Obtenido |', '|---|---|---|---|---|']
        for r in self.res:
            md.append(f"| {'✅' if r['ok'] else '❌' if r['ok'] is False else '○'} | {r['bloque']} | {r['prueba']} | {r['esperado'][:40]} | {r['obtenido'][:60]} |")
        (self.salida / 'reporte.md').write_text('\n'.join(md), encoding='utf-8')
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
                f.write('\n'.join(md) + '\n')
        return 0 if not fallan and not error else 1


def leer_de_config(campo):
    f = RAIZ / 'docs' / 'config.js'
    if f.exists():
        m = re.search(campo + r"\s*:\s*['\"]([^'\"]+)['\"]", f.read_text(encoding='utf-8'))
        if m and 'PEGA_AQUI' not in m.group(1):
            return m.group(1).strip()
    return None


def main():
    ap = argparse.ArgumentParser(description='Tester automático · Inscripciones CIIC 2026 v5.5')
    ap.add_argument('--api', default=os.environ.get('API_URL') or leer_de_config('API_URL'))
    ap.add_argument('--anon', default=os.environ.get('ANON_KEY') or leer_de_config('ANON_KEY'))
    ap.add_argument('--key', default=os.environ.get('ADMIN_KEY'))
    ap.add_argument('--web', default=os.environ.get('WEB_URL') or None)
    ap.add_argument('--modo', default=os.environ.get('MODO') or 'completo')
    ap.add_argument('--personas', type=int, default=int(os.environ.get('CARGA_PERSONAS') or 150))
    ap.add_argument('--personas-w', type=int, default=int(os.environ.get('CARGA_W') or 1000),
                    help='bloque W: personas que navegan y confirman a la vez (0 = sin el bloque W)')
    ap.add_argument('--rampa-w', type=float, default=float(os.environ.get('RAMPA_W') or 3),
                    help='bloque W: las personas llegan repartidas en estos segundos, como en una apertura real (0 = todas en el mismo instante)')
    ap.add_argument('--salida', default='resultados')
    ap.add_argument('--local', action='store_true', help='servidor local: permite simular otra IP')
    ap.add_argument('--dsn', default=os.environ.get('TESTER_DSN') or None,
                    help='conexión directa (local o Supabase, "Session pooler"): privilegios, protección masiva, bitácora, integridad y vaciar (todo se deshace)')
    ap.add_argument('--sin-mascara', action='store_true', help='solo para depurar en local: muestra documentos, nombres, correos y celulares')
    a = ap.parse_args()
    if os.name == 'nt':                 # Windows limita a 512 los archivos abiertos de un programa: 1000 personas a la vez lo superan
        try:
            import ctypes
            ctypes.cdll.ucrtbase._setmaxstdio(8192)
        except Exception:  # noqa: BLE001
            pass
    if not a.api or not a.anon:
        print('⛔ Falta API_URL o ANON_KEY: pégalos en docs/config.js o usa --api y --anon.')
        return 2
    t = Tester(a)
    print(pinta(AZUL, '═' * 70) + '\n' + pinta(AZUL, f'  🧪 TESTER · Inscripciones CIIC 2026 v5.5 (Sprint 4) · modo {a.modo}') + '\n' + pinta(GRIS, f'  API: {a.api}  ·  Página: {a.web or "(sin navegador)"}'))
    inicio, error = time.perf_counter(), None
    try:
        if a.modo == 'lectura':
            t.lectura()
        else:
            if not a.key:
                raise Abortar('Falta ADMIN_KEY (secreto de GitHub o --key).')
            t.preparar()
            try:
                for b in (t.a_conexion, t.b_documentos, t.c_etapas, t.d_combinaciones, t.e_cupos, t.f_panel, t.h_cierre, t.i_horarios,
                          t.j_intentos, t.k_soporte, t.l_whatsapp, t.m_roles, t.n_padron_catalogo, t.o_equipo,
                          t.s_comprobantes, t.x_incidencias, t.ab_niveles, t.r_privilegios, t.r_ip_real, t.z_equipo, t.ad_masiva, t.ag_bitacora,
                          t.t_carreras, t.u_idempotencia, t.ai_ambito, t.v_integridad, t.aa_listas, t.ac_padron_minimo, t.ah_correo_panel,
                          t.ae_importar_padron, t.ak_importar_actividades, t.aj_vaciar, t.y_respaldo, t.af_produccion,
                          t.p_navegador, t.q_carga, t.w_carga):
                    try:
                        b()
                    except Abortar:
                        raise
                    except Exception as e:  # noqa: BLE001
                        traceback.print_exc()
                        t.ok(f'{b.__name__} sin errores del tester', False, '', str(e)[:200])
            finally:
                t.limpiar()
    except Abortar as e:
        error = str(e)
    return t.reporte(error, time.perf_counter() - inicio)


if __name__ == '__main__':
    sys.exit(main())
