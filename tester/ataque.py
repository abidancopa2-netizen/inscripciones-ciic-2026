#!/usr/bin/env python3
"""
Prueba de ataque · Sprint 6 · SOLO contra PRUEBA (se niega si la base está en modo PRODUCCION).

Hace lo que intentaría alguien de afuera con lo que la página publica (la ANON_KEY está en config.js, a la vista de todos)
y comprueba que el sistema resiste. La ADMIN_KEY del tester solo se usa para preparar (tomar documentos del padrón ficticio),
para mirar cómo quedaron los datos y para limpiar al final. Ningún ataque de saturación (DoS): eso no se prueba.

    python tester/ataque.py --api URL_DE_PRUEBA --anon ANON_KEY_DE_PRUEBA --key ADMIN_KEY [--web URL_PUBLICADA] [--salida resultados/ataque]
    python tester/ataque.py --api http://127.0.0.1:8787 --anon local --key CLAVE --local --web http://127.0.0.1:8787/     (servidor local)

Bloques: 1 tablas y servicios de Supabase · 2 enumerar documentos y saltarse los límites · 3 documentos raros ·
4 inscribir de más o duplicar · 5 campos raros · 6 panel sin rol y sesiones falsas · 7 verificar celular y exportar ·
8 enmarcar el panel (clickjacking). Dura unos 3 a 5 minutos. Deja PRUEBA como estaba (borra lo que creó y los intentos).
"""
import argparse
import base64
import concurrent.futures as cf
import hashlib
import hmac
import json
import os
import random
import re
import sys
import time
import uuid
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tester import NOMBRES, APELLIDOS, Cliente, leer_de_config  # noqa: E402

VERDE, ROJO, AMARILLO, GRIS, AZUL, FIN = '\033[32m', '\033[31m', '\033[33m', '\033[90m', '\033[34m', '\033[0m'
NO_FALLA = {'formato', 'no_encontrado', 'peticion_invalida', 'valor_invalido', 'demasiados_intentos', 'datos_invalidos', 'ok'}
CAMPOS_PERSONALES = ('nombre', 'nombres', 'apellidos', 'correo', 'celular', 'codigo')


def b64(d):
    return base64.urlsafe_b64encode(json.dumps(d, separators=(',', ':')).encode()).rstrip(b'=').decode()


class Ataque:
    def __init__(self, a):
        self.a = a
        self.cli = Cliente(a.api, a.anon)
        self.url = a.api.rstrip('/')
        self.h = {'apikey': a.anon, **({'Authorization': f'Bearer {a.anon}'} if a.anon.startswith('eyJ') else {}), 'Content-Type': 'application/json'}
        self.res, self.bloque, self.docs = [], '', set()
        self.red = {'X-Red-Prueba': f'10.66.{random.randint(1, 250)}.{random.randint(1, 250)}'} if a.local else {}

    # ── informe ──
    def seccion(self, t):
        self.bloque = t
        print('\n' + AZUL + '▶ ' + t + FIN)

    def ok(self, nombre, cond, detalle=''):
        self.res.append({'bloque': self.bloque, 'prueba': nombre, 'ok': bool(cond), 'detalle': str(detalle)[:160]})
        print(f'  {VERDE + "✔ RESISTE" if cond else ROJO + "✘ FALLA  "}{FIN}  {nombre}' + ('' if cond else f'\n           {detalle}'))
        return bool(cond)

    def info(self, nombre, detalle):
        self.res.append({'bloque': self.bloque, 'prueba': nombre, 'ok': None, 'detalle': str(detalle)[:160]})
        print(f'  {AMARILLO}○ INFO{FIN}     {nombre} · {detalle}')

    # ── llamadas ──
    def rpc(self, p, cab=None, auth=None, timeout=30):
        """Llamada directa a la API, sin reintentos: devuelve (HTTP, JSON o texto, segundos)."""
        h = dict(self.h, **(cab or {}), **self.red)
        if auth is not None:
            h['Authorization'] = auth
        t0 = time.perf_counter()
        try:
            x = requests.post(self.url + '/rest/v1/rpc/api', data=json.dumps({'p': p}), headers=h, timeout=timeout)
            try:
                cuerpo = x.json()
            except ValueError:
                cuerpo = x.text[:200]
            return x.status_code, cuerpo, time.perf_counter() - t0
        except requests.RequestException as e:
            return 0, str(e)[:120], time.perf_counter() - t0

    def tester(self, accion, **d):
        return self.cli.llamar({'action': accion, 'key': self.a.key, **d}, cab=self.red or None)

    def tipo(self, r):
        return r.get('tipo') if isinstance(r, dict) else None

    # ═════════════════════════════════════════════════════════════════════
    def preparar(self):
        self.seccion('Preparación (con la clave del tester)')
        r = self.tester('admin_ping')
        if r.get('tipo') != 'admin':
            sys.exit(f'⛔ La clave del tester no responde ({r.get("tipo")}): esta prueba es solo para PRUEBA.')
        c = r.get('config', {})
        if c.get('modo') != 'PRUEBA':
            sys.exit('⛔ La base está en modo PRODUCCION: la prueba de ataque no se corre ahí.')
        self.cfg = c
        m = self.tester('admin_muestra', n=60)
        self.muestra = m.get('etapas', {})
        self.cli.llamar({'action': 'admin_limpiar', 'key': self.a.key, 'intentos': True})
        print(GRIS + f"  … límites: {c.get('limiteDispositivo')} por dispositivo, {c.get('limiteRed')} por red · abierto: {c.get('abierto')} · etapas {c.get('etapas')}" + FIN)
        if not c.get('abierto'):
            sys.exit('⛔ PRUEBA está cerrada: ábrela desde el panel (o corre antes el tester) para probar las inscripciones.')

    # ── 1 · Tablas y servicios de Supabase ──
    def b1_supabase(self):
        self.seccion('1 · Leer o escribir las tablas sin pasar por la API')
        if self.a.local:
            self.info('Tablas, GraphQL y registro de cuentas', 'solo contra Supabase (el servidor local solo expone la API)')
            return
        for tabla in ('padron', 'inscripciones', 'inscripcion_actividades', 'actividades', 'config', 'bitacora', 'intentos', 'organizadores'):
            x = requests.get(f'{self.url}/rest/v1/{tabla}?select=*&limit=1', headers=self.h, timeout=20)
            filas = x.json() if x.headers.get('content-type', '').startswith('application/json') else None
            self.ok(f'GET /rest/v1/{tabla} no devuelve filas', not (x.status_code == 200 and isinstance(filas, list) and filas), f'HTTP {x.status_code} · {str(filas)[:80]}')
        x = requests.post(f'{self.url}/rest/v1/inscripciones', headers={**self.h, 'Prefer': 'return=minimal'},
                          data=json.dumps({'documento': '00000000', 'nombre': 'x'}), timeout=20)
        self.ok('Insertar directo en inscripciones está prohibido', x.status_code not in (200, 201, 204), f'HTTP {x.status_code}')
        x = requests.post(f'{self.url}/rest/v1/rpc/panel_buscar', headers=self.h, data=json.dumps({'b': {'q': '1'}}), timeout=20)
        self.ok('Las funciones internas (privado.*) no se pueden llamar', x.status_code in (401, 403, 404), f'HTTP {x.status_code}')
        x = requests.post(f'{self.url}/graphql/v1', headers=self.h, data=json.dumps({'query': '{ __schema { types { name } } }'}), timeout=20)
        expuesto = [n for n in ('inscripciones', 'padron', 'organizadores', 'bitacora') if n in x.text.lower()]
        self.ok('GraphQL no muestra las tablas', not expuesto, f'HTTP {x.status_code} · {expuesto}')
        try:
            s = requests.get(f'{self.url}/auth/v1/settings', headers={'apikey': self.a.anon}, timeout=20).json()
            self.ok('Nadie puede crear su propia cuenta (Auth → "Allow new users to sign up" apagado)', s.get('disable_signup') is True,
                    f"disable_signup = {s.get('disable_signup')}: apágalo en Authentication → Sign In / Providers")
        except (requests.RequestException, ValueError) as e:
            self.info('Registro de cuentas', f'no se pudo leer /auth/v1/settings ({e})')

    # ── 2 · Enumerar documentos y saltarse los límites ──
    def b2_enumerar(self):
        self.seccion('2 · Probar documentos al azar (enumerar) y saltarse los límites')
        lim = int(self.cfg.get('limiteRed') or 300)
        dni = lambda: str(20000000 + random.randint(0, 79999999))

        def intento(_):
            return self.rpc({'action': 'verificar', 'dni': dni(), 'dispositivo': 'atk-' + uuid.uuid4().hex[:12]})
        t0 = time.perf_counter()
        with cf.ThreadPoolExecutor(10) as ex:
            rs = list(ex.map(intento, range(lim + 40)))
        tipos = [self.tipo(r[1]) for r in rs]
        pasaron = tipos.count('no_encontrado') + tipos.count('formato')
        print(GRIS + f'  … {len(rs)} intentos en {time.perf_counter() - t0:.0f} s · no_encontrado {tipos.count("no_encontrado")} · '
                     f'frenados {tipos.count("demasiados_intentos")} · otros {sorted(set(tipos) - {"no_encontrado", "demasiados_intentos"})}' + FIN)
        self.ok(f'Cambiar de "dispositivo" en cada intento no sirve: la red se frena cerca de {lim}', 'demasiados_intentos' in tipos and pasaron <= lim + 10,
                f'{pasaron} intentos contestados antes del freno')
        filtrado = [r[1] for r in rs if isinstance(r[1], dict) and any(k in r[1] for k in CAMPOS_PERSONALES)]
        self.ok('Ninguna respuesta trae datos personales', not filtrado, str(filtrado[:1])[:120])
        doc = self.muestra['1'][0]
        r = self.rpc({'action': 'verificar', 'dni': doc})[1]
        self.ok('Frenada la red, ni un documento válido pasa (motivo red)', isinstance(r, dict) and r.get('motivo') == 'red', r)
        for cab in ({'X-Forwarded-For': '203.0.113.50'}, {'X-Real-IP': '203.0.113.51'}, {'True-Client-IP': '203.0.113.52'}, {'CF-Connecting-IP': '203.0.113.53'}):
            if self.a.local:
                self.info('Falsear la IP con cabeceras', 'solo contra Supabase: el servidor local no es Cloudflare')
                break
            estado, r, _ = self.rpc({'action': 'verificar', 'dni': doc}, cab=cab)
            nombre = next(iter(cab))
            self.ok(f'Falsear {nombre} no saca a la red del freno', estado in (400, 403) or (isinstance(r, dict) and r.get('motivo') == 'red'), f'HTTP {estado} · {r}')
        for disp in (None, '', 'x' * 500, '../../etc', '<b>'):
            p = {'action': 'verificar', 'dni': doc} if disp is None else {'action': 'verificar', 'dni': doc, 'dispositivo': disp}
            r = self.rpc(p)[1]
            self.ok(f'Un "dispositivo" raro ({"sin" if disp is None else repr(disp)[:12]}) tampoco', isinstance(r, dict) and r.get('tipo') == 'demasiados_intentos', r)
        self.cli.llamar({'action': 'admin_limpiar', 'key': self.a.key, 'intentos': True})
        r = self.rpc({'action': 'verificar', 'dni': doc})[1]
        self.ok('Limpiados los intentos, la red vuelve a verificar', isinstance(r, dict) and r.get('tipo') == 'ok', r)

    # ── 3 · Documentos raros ──
    def b3_documentos(self):
        self.seccion('3 · Documentos raros (tipos, largos, Unicode, inyección)')
        raros = [12345678, ['12345678'], {'a': 1}, None, '', ' ', '1' * 5000, '１２３４５６７８', '١٢٣٤٥٦٧٨', "' OR 1=1 --", '12345678; drop table padron',
                 '<script>alert(1)</script>', 'abc\u0000def', '😀😀😀😀', '1e8', '-12345678', '0x1234567']
        malos = []
        for v in raros:
            estado, r, s = self.rpc({'action': 'verificar', 'dni': v, 'dispositivo': 'atk-' + uuid.uuid4().hex[:12]})
            if isinstance(v, str) and '\x00' in v:          # PostgreSQL no admite el carácter nulo: se rechaza antes de llegar a la API
                if estado == 200 and self.tipo(r) not in NO_FALLA:
                    malos.append(f'{repr(v)[:20]} → {self.tipo(r)}')
                continue
            if estado != 200 or not isinstance(r, dict) or r.get('tipo') not in NO_FALLA or s > 3 or r.get('tipo') == 'error_servidor':
                malos.append(f'{repr(v)[:20]} → HTTP {estado} · {self.tipo(r)} · {s:.1f} s')
        self.ok(f'{len(raros)} documentos raros: respuesta controlada en menos de 3 s, sin error interno', not malos, '; '.join(malos[:3]))
        estado, r, _ = self.rpc('esto no es un objeto')
        self.ok('Un pedido que no es un objeto → peticion_invalida', self.tipo(r) == 'peticion_invalida' or estado in (400, 404), f'HTTP {estado} · {r}')
        self.cli.llamar({'action': 'admin_limpiar', 'key': self.a.key, 'intentos': True})

    # ── 4 · Inscribir de más o duplicar ──
    def actividades(self):
        r = self.rpc({'action': 'actividades'})[1]
        return [x for x in r.get('actividades', []) if x.get('disponibles', 0) > 0]

    def combo(self, acts, visita=False):
        dias = sorted({x['fecha'] for x in acts}, key=lambda f: f[6:] + f[3:5] + f[:2])
        a = next(x for x in acts if x['fecha'] == dias[0] and x['tipo'] == ('VISITA' if visita else 'TALLER'))
        b = next(x for x in acts if x['fecha'] == dias[1] and x['tipo'] == 'TALLER')
        return [a['id'], b['id']], dias

    def registrar(self, doc, ids, **extra):
        e = self.rpc({'action': 'estado'})[1]
        p = {'action': 'registrar', 'dni': doc, 'actividades': ids, 'nombres': NOMBRES, 'apellidos': APELLIDOS, 'correo': f'ataque.{doc}@ejemplo.com',
             'pais': 'PE', 'celular': '9' + str(random.randint(10000000, 99999999)), 'aceptaPrivacidad': True, 'aceptaWhatsapp': True,
             'ronda': e.get('ronda'), 'solicitud': str(uuid.uuid4()), 'dispositivo': 'atk-' + uuid.uuid4().hex[:12]}
        p.update(extra)
        p = {k: v for k, v in p.items() if v is not ...}
        self.docs.add(doc)
        return self.rpc(p)[1]

    def b4_inscribir(self):
        self.seccion('4 · Inscribir de más, duplicar o saltarse las reglas')
        acts = self.actividades()
        ids, dias = self.combo(acts)
        d1 = self.muestra['1'].pop()
        self.docs.add(d1)
        with cf.ThreadPoolExecutor(20) as ex:
            rs = list(ex.map(lambda _: self.registrar(d1, ids), range(20)))
        tipos = [self.tipo(r) for r in rs]
        self.ok('El mismo documento 20 veces a la vez: una sola inscripción', tipos.count('registrado') == 1, tipos)
        self.ok('Repetirlo después → duplicado, sin datos de la inscripción', self.tipo(self.registrar(d1, ids)) == 'duplicado')
        d2 = self.muestra['1'].pop()
        otro = next(x['id'] for x in acts if x['id'] not in ids and x['fecha'] in dias[:2])
        casos = [('3 actividades', {'actividades': ids + [otro]}), ('la misma actividad dos veces', {'actividades': [ids[1], ids[1]]}),
                 ('una actividad que no existe', {'actividades': [ids[0], 'NOEXISTE9']}), ('una sola actividad', {'actividades': [ids[1]]}),
                 ('actividades como texto', {'actividades': 'TAL01,TAL02'}), ('sin aceptar el aviso', {'aceptaPrivacidad': ...}),
                 ('aviso aceptado como texto "true"', {'aceptaPrivacidad': 'true'}), ('una ronda vieja', {'ronda': -1}),
                 ('sin solicitud', {'solicitud': ...}), ('solicitud que no es UUID', {'solicitud': "1' or '1'='1"})]
        for nombre, extra in casos:
            r = self.registrar(d2, extra.pop('actividades', ids), **extra)
            self.ok(f'Con {nombre} no se inscribe', self.tipo(r) not in ('registrado', 'error_servidor'), r)
        visitas = [x for x in acts if x['tipo'] == 'VISITA']
        if len({x['fecha'] for x in visitas}) >= 2:
            v1 = next(x for x in visitas if x['fecha'] == dias[0])
            v2 = next(x for x in visitas if x['fecha'] != dias[0])
            self.ok('Con 2 visitas no se inscribe', self.tipo(self.registrar(d2, [v1['id'], v2['id']])) != 'registrado')
        sol = str(uuid.uuid4())
        r1 = self.registrar(d2, ids, solicitud=sol)
        r2 = self.registrar(d2, ids, solicitud=sol, nombres='Otra Persona')
        self.ok('Reusar la solicitud con otros datos → solicitud_repetida', self.tipo(r1) == 'registrado' and self.tipo(r2) == 'solicitud_repetida', (self.tipo(r1), self.tipo(r2)))
        if self.muestra.get('3') and 3 not in (self.cfg.get('etapas') or []):
            self.ok('Una etapa no habilitada no se inscribe llamando directo a registrar', self.tipo(self.registrar(self.muestra['3'][0], ids)) != 'registrado')
        self.ok('Un documento fuera del padrón no se inscribe llamando directo a registrar', self.tipo(self.registrar('ZQX' + uuid.uuid4().hex[:6].upper(), ids)) != 'registrado')

    # ── 5 · Campos raros ──
    def b5_campos(self):
        self.seccion('5 · Campos raros al inscribirse (HTML, fórmulas, largos, caracteres invisibles)')
        acts = self.actividades()
        ids, _ = self.combo(acts)
        d = self.muestra['1'].pop()
        r = self.registrar(d, ids, nombres='<img src=x onerror=alert(1)>', apellidos='=HYPERLINK("https://x.invalid","clic")‮​',
                           correo='a@b.cc', celular='+51 987-654-321')
        self.ok('HTML y fórmulas en los nombres: se inscribe como texto, sin error', self.tipo(r) == 'registrado', r)
        b = self.tester('panel_buscar', q=d)
        reg = (b.get('registros') or [{}])[0]
        self.ok('Se guarda como texto, sin caracteres invisibles', reg.get('nombres', '').startswith('<img') and '‮' not in reg.get('apellidos', '')
                and '​' not in reg.get('apellidos', ''), repr(reg.get('apellidos', ''))[:60])
        self.info('Al mostrarlo', 'el panel pinta con textContent (no ejecuta HTML) y el CSV antepone \' a =, +, - y @ (R-39)')
        d = self.muestra['1'].pop()
        for nombre, extra, esperado in (('nombres de 5000 letras', {'nombres': 'A' * 5000}, ('registrado', 'datos_invalidos')),
                                       ('celular con letras', {'celular': '9abc12345'}, ('celular_invalido',)),
                                       ('correo sin @', {'correo': 'sin-arroba.com'}, ('datos_invalidos',)),
                                       ('país inventado', {'pais': 'ZZ', 'celular': '12'}, ('celular_invalido', 'datos_invalidos', 'valor_invalido'))):
            r = self.registrar(d, ids, **extra)
            self.ok(f'Con {nombre} → {" o ".join(esperado)}', self.tipo(r) in esperado, r)
            if self.tipo(r) == 'registrado':
                reg = (self.tester('panel_buscar', q=d).get('registros') or [{}])[0]
                self.ok('…y se recorta a 60 letras', len(reg.get('nombres', '')) <= 60, len(reg.get('nombres', '')))
                self.tester('admin_limpiar', docs=[d])

    # ── 6 · Panel sin rol y sesiones falsas ──
    def b6_panel(self):
        self.seccion('6 · Acciones del panel sin sesión, con sesión falsa o con un rol menor')
        acciones = ['panel_resumen', 'panel_buscar', 'panel_exportar', 'panel_registros', 'panel_lista', 'panel_verificar_celular', 'panel_config',
                    'panel_anular', 'panel_inscribir', 'panel_redes', 'panel_liberar_red', 'panel_respaldo', 'panel_equipo', 'panel_equipo_rol',
                    'panel_padron_importar', 'panel_vaciar_prueba', 'panel_preparar_produccion']
        mal = [a for a in acciones if self.tipo(self.rpc({'action': a, 'solicitud': str(uuid.uuid4()), 'q': '1'})[1]) != 'sin_sesion']
        self.ok(f'{len(acciones)} acciones del panel sin sesión → sin_sesion', not mal, mal)
        mal = [a for a in acciones if self.tipo(self.rpc({'action': a, 'comoRol': 'propietario', 'rol': 'propietario', 'solicitud': str(uuid.uuid4())})[1]) != 'sin_sesion']
        self.ok('Pedir un rol en el cuerpo ("comoRol", "rol") sin clave no sirve', not mal, mal)
        t0 = time.perf_counter()
        tipos = [self.tipo(self.rpc({'action': 'panel_resumen', 'key': 'clave-' + uuid.uuid4().hex})[1]) for _ in range(3)]
        dur = (time.perf_counter() - t0) / 3
        self.ok('Adivinar la clave del tester: no_autorizado y al menos 1,5 s por intento', tipos == ['no_autorizado'] * 3 and dur >= 1.4, f'{tipos} · {dur:.1f} s')
        self.ok('Las acciones del tester sin clave → no_autorizado', all(self.tipo(self.rpc({'action': a})[1]) in ('no_autorizado', 'admin_deshabilitado')
                                                                         for a in ('admin_muestra', 'admin_limpiar', 'admin_cabeceras', 'admin_ensayo')))
        if self.a.local:
            uid = str(uuid.uuid4())
            r = self.rpc({'action': 'panel_resumen'}, auth=f'Bearer local:{uid}:aal1')[1]
            self.ok('Sesión sin el código de 6 dígitos (aal1) → falta_codigo', self.tipo(r) == 'falta_codigo', r)
            r = self.rpc({'action': 'panel_resumen'}, auth=f'Bearer local:{uid}:aal2')[1]
            self.ok('Sesión válida de alguien que no es del equipo → sin_permiso', self.tipo(r) == 'sin_permiso', r)
            self.info('Tokens falsificados', 'solo contra Supabase (el servidor local no firma tokens)')
        else:
            ahora = int(time.time())
            reclamos = {'sub': str(uuid.uuid4()), 'role': 'authenticated', 'aal': 'aal2', 'aud': 'authenticated', 'iat': ahora, 'exp': ahora + 3600}
            sin_firma = b64({'alg': 'none', 'typ': 'JWT'}) + '.' + b64(reclamos) + '.'
            firma = lambda d, clave: (lambda c: c + '.' + base64.urlsafe_b64encode(hmac.new(clave, c.encode(), hashlib.sha256).digest()).rstrip(b'=').decode())(
                b64({'alg': 'HS256', 'typ': 'JWT'}) + '.' + b64(d))
            falsos = [('sin firma (alg none)', sin_firma), ('firmado con otra clave', firma(reclamos, b'una-clave-cualquiera')),
                      ('como service_role', firma(dict(reclamos, role='service_role'), b'otra-clave')),
                      ('vencido', firma(dict(reclamos, exp=ahora - 3600), b'otra-clave'))]
            for nombre, tok in falsos:
                estado, r, _ = self.rpc({'action': 'panel_resumen'}, auth='Bearer ' + tok)
                self.ok(f'Token falso {nombre} → rechazado', estado in (401, 403) or self.tipo(r) in ('sin_sesion', 'sin_permiso', 'falta_codigo'), f'HTTP {estado} · {str(r)[:80]}')
        mal = []
        for rol, prohibidas in (('operador', ['panel_anular', 'panel_inscribir', 'panel_registros', 'panel_redes', 'panel_config']),
                                ('admin', ['panel_respaldo', 'panel_equipo_rol', 'panel_liberar_red', 'panel_vaciar_prueba', 'panel_preparar_produccion'])):
            for a in prohibidas:
                r = self.cli.llamar({'action': a, 'key': self.a.key, 'comoRol': rol, 'abierto': True, 'solicitud': str(uuid.uuid4())}, cab=self.red or None)
                if self.tipo(r) != 'sin_permiso':
                    mal.append(f'{rol} · {a}: {self.tipo(r)}')
        self.ok('Un rol menor no hace lo del rol mayor (10 acciones)', not mal, mal)

    # ── 7 · Verificar celular y exportar ──
    def b7_celular(self):
        self.seccion('7 · Abuso de "Verificar celular" y de exportar')
        acts = self.actividades()
        self.ok('Sin sesión, verificar celular → sin_sesion', self.tipo(self.rpc({'action': 'panel_verificar_celular', 'id': acts[0]['id'], 'celular': '987654321'})[1]) == 'sin_sesion')
        self.ok('Sin sesión, exportar → sin_sesion', self.tipo(self.rpc({'action': 'panel_exportar', 'id': acts[0]['id']})[1]) == 'sin_sesion')
        t0 = time.perf_counter()
        n = sum(1 for _ in range(30) if self.cli.llamar({'action': 'panel_verificar_celular', 'key': self.a.key, 'comoRol': 'operador', 'id': acts[0]['id'],
                                                         'celular': '9' + str(random.randint(10000000, 99999999))}, cab=self.red or None).get('ok'))
        self.info('Un operador puede probar celulares sin límite', f'{n} de 30 en {time.perf_counter() - t0:.0f} s. Riesgo aceptado: el operador ya ve la lista completa de su actividad; '
                                                                  'cada cuenta es individual y se puede desactivar')
        r = self.cli.llamar({'action': 'panel_exportar', 'key': self.a.key, 'comoRol': 'operador', 'id': acts[0]['id']}, cab=self.red or None)
        self.info('Un operador exporta la lista de una actividad', f'{self.tipo(r)} · queda en la bitácora con su cuenta (R-39)')

    # ── 8 · Enmarcar el panel ──
    def b8_marco(self):
        self.seccion('8 · Enmarcar el panel en otra página (clickjacking)')
        if not self.a.web:
            self.info('Panel dentro de un iframe', 'sin --web')
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.info('Panel dentro de un iframe', 'falta playwright')
            return
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            pg = nav.new_page()
            pg.set_content(f'<iframe id="f" src="{self.a.web.rstrip("/")}/panel.html" width="900" height="600"></iframe>')
            pg.wait_for_timeout(4000)
            marco = pg.frame_locator('#f')
            try:
                texto = marco.locator('html').inner_text(timeout=5000)
            except Exception:  # noqa: BLE001
                texto = ''
            nav.close()
        self.ok('Dentro de un iframe de otro sitio, el panel no se muestra', 'Inicia sesión' not in texto and 'Entrar' not in texto, texto[:80])

    def limpiar(self):
        self.seccion('Limpieza')
        r = self.cli.llamar({'action': 'admin_limpiar', 'key': self.a.key, 'docs': sorted(self.docs), 'intentos': True}, cab=self.red or None)
        print(GRIS + f"  … inscripciones borradas: {r.get('eliminados')} · intentos borrados" + FIN)

    def reporte(self, dur):
        pasan = sum(1 for r in self.res if r['ok'] is True)
        fallan = [r for r in self.res if r['ok'] is False]
        info = sum(1 for r in self.res if r['ok'] is None)
        print(AZUL + '\n' + '═' * 70 + FIN)
        print((VERDE + f'  ✅ Resistió {pasan} de {pasan + len(fallan)} ataques' if not fallan else ROJO + f'  ❌ {len(fallan)} de {pasan + len(fallan)} ataques no los resistió') + FIN
              + f' · {info} notas · {int(dur // 60)} min {int(dur % 60)} s')
        out = Path(self.a.salida)
        out.mkdir(parents=True, exist_ok=True)
        md = ['# Prueba de ataque · Sprint 6', '', f'**Resistió {pasan} de {pasan + len(fallan)}** · {info} notas', '', '| | Bloque | Ataque | Detalle |', '|---|---|---|---|']
        md += [f"| {'✅' if r['ok'] else '❌' if r['ok'] is False else '○'} | {r['bloque']} | {r['prueba']} | {r['detalle'][:90]} |" for r in self.res]
        (out / 'ataque.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
        return 1 if fallan else 0


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='Prueba de ataque contra PRUEBA (Sprint 6)')
    ap.add_argument('--api', default=os.environ.get('API_URL'))
    ap.add_argument('--anon', default=os.environ.get('ANON_KEY'))
    ap.add_argument('--key', default=os.environ.get('ADMIN_KEY'))
    ap.add_argument('--web', default=os.environ.get('WEB_URL') or None)
    ap.add_argument('--local', action='store_true')
    ap.add_argument('--salida', default='resultados/ataque')     # resultados/ está en .gitignore
    a = ap.parse_args()
    if not (a.api and a.anon and a.key):
        sys.exit('⛔ Faltan --api, --anon y --key de PRUEBA (no se toman de config.js: puede apuntar a PRODUCCIÓN).')
    if leer_de_config('API_URL') and a.api.rstrip('/') == leer_de_config('API_URL').rstrip('/') and \
            re.search(r'PANEL_PRUEBA\s*:\s*false', (Path(__file__).resolve().parent.parent / 'docs' / 'config.js').read_text(encoding='utf-8')):
        sys.exit('⛔ Esa API es la de PRODUCCIÓN (config.js del Sprint 6): la prueba de ataque es solo para PRUEBA.')
    x = Ataque(a)
    print(AZUL + '═' * 70 + '\n  🛡  PRUEBA DE ATAQUE · Inscripciones CIIC 2026 · solo PRUEBA\n' + FIN + GRIS + f'  API: {a.api}' + FIN)
    t0 = time.perf_counter()
    x.preparar()
    try:
        for b in (x.b1_supabase, x.b2_enumerar, x.b3_documentos, x.b4_inscribir, x.b5_campos, x.b6_panel, x.b7_celular, x.b8_marco):
            try:
                b()
            except Exception as e:  # noqa: BLE001
                x.ok(f'{b.__name__} terminó sin errores del script', False, repr(e)[:160])
    finally:
        x.limpiar()
    return x.reporte(time.perf_counter() - t0)


if __name__ == '__main__':
    sys.exit(main())
