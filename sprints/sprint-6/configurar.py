#!/usr/bin/env python3
"""
Sprint 6 · docs/config.js pasa a apuntar a PRODUCCIÓN (apertura).

    python sprints/sprint-6/configurar.py              # comprueba y muestra qué cambiaría; no escribe
    python sprints/sprint-6/configurar.py --aplicar    # lo escribe (guarda antes tu config.js en sprints/sprint-6/anteriores/)
    python sprints/sprint-6/configurar.py --revertir   # vuelve a tu config.js anterior (el de PRUEBA)

Cambia solo API_URL y ANON_KEY (a los de PRODUCCIÓN) y agrega PANEL_PRUEBA: false (el panel publicado ya no ofrece
"Entrar con la clave de prueba"). MODO, NOMBRE_EVENTO, CONTACTO, AVISO_PRIVACIDAD, SUPABASE_JS y su SRI quedan iguales.

Los valores de PRODUCCIÓN NO pasan por el chat: se leen de .env.local (o de variables de entorno):
    PRODUCCION_API_URL=https://<ref>.supabase.co      (o REF_PRODUCCION=<ref>)
    PRODUCCION_ANON_KEY=<clave anon o "publishable" de PRODUCCIÓN: Supabase → Project Settings → API Keys>
y, si está, REF_PRUEBA (para negarse si por error son los de PRUEBA).

Antes de escribir, llama a esa API con esa clave y exige: que responda, que tenga la migración 11 (5.5-s6) y que esté
CERRADA. Si algo no cuadra, no escribe nada.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[2]
CONFIG = RAIZ / 'docs' / 'config.js'
ANTERIOR = Path(__file__).resolve().parent / 'anteriores' / 'docs' / 'config.js'   # junto a las de aplicar.py (.gitignore)
BASE_ESPERADA = 'fa8884d5a6f7'          # la huella que informó Claude Code al cerrar el Sprint 5.1
VERSION_MINIMA = '5.5-s6'


def huella(b):
    return hashlib.sha256(b.replace(b'\r\n', b'\n')).hexdigest()[:12]


def entorno():
    """.env.local (KEY=valor) y, por encima, las variables de entorno."""
    v = {}
    f = RAIZ / '.env.local'
    if f.exists():
        for linea in f.read_text(encoding='utf-8').splitlines():
            m = re.match(r'\s*(?:export\s+)?([A-Z0-9_]+)\s*=\s*(.*?)\s*$', linea)
            if m and not linea.lstrip().startswith('#'):
                v[m.group(1)] = m.group(2).strip('\'"')
    v.update({k: x for k, x in os.environ.items() if k.startswith(('PRODUCCION_', 'REF_'))})
    return v


def corto(x):
    return (x[:4] + '…' + x[-4:]) if len(x) > 12 else '…'


def valor(t, clave):
    m = re.search(r'(?m)^[ \t]*' + clave + r"[ \t]*:[ \t]*(['\"])(.*?)\1", t)
    return m.group(2) if m else None


def poner(t, clave, nuevo):
    """Reemplaza el valor entre comillas de una propiedad de una línea; deja igual la coma y el comentario."""
    patron = re.compile(r'(?m)^([ \t]*' + clave + r"[ \t]*:[ \t]*)(['\"])(.*?)\2")
    if len(patron.findall(t)) != 1:
        sys.exit(f'No reconozco {clave} en docs/config.js: no se cambió nada. Lleva este mensaje a la conversación de diseño.')
    return patron.sub(lambda m: m.group(1) + "'" + nuevo + "'", t, count=1)


def demos():
    armar = RAIZ / 'local' / 'armar_demos.py'
    if armar.exists():
        r = subprocess.run([sys.executable, str(armar)], capture_output=True, text=True, encoding='utf-8', errors='replace',
                           env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        print('  demos           ' + (r.stdout.strip().replace('\n', ' · ') if r.returncode == 0 else 'ERROR: ' + r.stderr.strip()[-200:]))


def comprobar(api, anon):
    h = {'apikey': anon, 'Content-Type': 'application/json', **({'Authorization': 'Bearer ' + anon} if anon.startswith('eyJ') else {})}
    try:
        v = requests.post(api + '/rest/v1/rpc/api', data=json.dumps({'p': {}}), headers=h, timeout=20).json()
        e = requests.post(api + '/rest/v1/rpc/api', data=json.dumps({'p': {'action': 'estado'}}), headers=h, timeout=20).json()
    except (requests.RequestException, ValueError) as x:
        sys.exit(f'PRODUCCIÓN no responde con esa URL y esa clave ({str(x)[:80]}): no se escribió nada.')
    version = str(v.get('version', ''))
    print(f'  PRODUCCIÓN      responde · versión {version} · {"ABIERTA" if e.get("abierto") else "cerrada"} · modo {e.get("modo")}')
    if version < VERSION_MINIMA:
        sys.exit(f'PRODUCCIÓN está en {version or "?"}: primero instala las migraciones 10 a 12 (instalar.py). No se escribió nada.')
    if e.get('abierto'):
        sys.exit('PRODUCCIÓN está ABIERTA: el cambio de config.js se hace con las inscripciones cerradas. No se escribió nada.')


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    aplicar = '--aplicar' in sys.argv
    if '--revertir' in sys.argv:
        if not ANTERIOR.exists():
            sys.exit('No hay copia de tu config.js en sprints/sprint-6/anteriores/: no se cambió nada.')
        CONFIG.write_bytes(ANTERIOR.read_bytes())
        print(f'✔ docs/config.js devuelto como estaba (huella {huella(ANTERIOR.read_bytes())}): apunta otra vez a PRUEBA.')
        demos()
        return
    env = entorno()
    api = (env.get('PRODUCCION_API_URL') or (f"https://{env['REF_PRODUCCION']}.supabase.co" if env.get('REF_PRODUCCION') else '')).rstrip('/')
    anon = env.get('PRODUCCION_ANON_KEY', '')
    if not re.fullmatch(r'https://[a-z0-9]{10,40}\.supabase\.co', api) or len(anon) < 20 or 'PEGA_AQUI' in anon:
        sys.exit('Faltan los datos de PRODUCCIÓN en .env.local: PRODUCCION_API_URL (o REF_PRODUCCION) y PRODUCCION_ANON_KEY. '
                 'Pídele al propietario que los copie de Supabase (PRODUCCIÓN → Project Settings → API Keys) en .env.local; nunca en el chat.')
    if env.get('REF_PRUEBA') and api == f"https://{env['REF_PRUEBA']}.supabase.co":
        sys.exit('Esa URL es la de PRUEBA (REF_PRUEBA): no se escribió nada.')
    crudo = CONFIG.read_bytes()
    antes = huella(crudo)
    t = crudo.decode('utf-8').replace('\r\n', '\n')
    api_antes, anon_antes = valor(t, 'API_URL') or '', valor(t, 'ANON_KEY') or ''
    ya = api_antes.rstrip('/') == api                      # ya se aplicó antes: se permite repetir (idempotente)
    print(f'docs/config.js · huella actual {antes}' + ('' if antes == BASE_ESPERADA or ya else f' (se esperaba {BASE_ESPERADA})'))
    if antes != BASE_ESPERADA and not ya:
        sys.exit(f'Tu config.js no es el que cerró el Sprint 5.1 ({BASE_ESPERADA}): alguien lo cambió. No se escribió nada. '
                 'Lleva esta huella a la conversación de diseño.')
    print(f'  API_URL         {corto(api_antes.split("//")[-1])}  →  {corto(api.split("//")[-1])} (PRODUCCIÓN)')
    print(f'  ANON_KEY        {corto(anon_antes)}  →  {corto(anon)}')
    comprobar(api, anon)
    if ya:
        print('  (ya apuntaba a PRODUCCIÓN)')
    t = poner(t, 'API_URL', api)
    t = poner(t, 'ANON_KEY', anon)
    if re.search(r'(?m)^[ \t]*PANEL_PRUEBA[ \t]*:', t):
        t = re.sub(r'(?m)^([ \t]*PANEL_PRUEBA[ \t]*:[ \t]*)[^,\n]*', r'\1false', t, count=1)
    else:
        t = re.sub(r"(?m)^([ \t]*)(ANON_KEY[ \t]*:[^\n]*\n)", r"\1\2\1PANEL_PRUEBA: false,   // Sprint 6: el panel publicado no ofrece la clave de prueba (PRODUCCIÓN)\n", t, count=1)
    print('  PANEL_PRUEBA    false (el panel publicado oculta "Entrar con la clave de prueba")')
    claves = lambda s: [k for k in re.findall(r'(?m)^\s*([A-Z_]+)\s*:', s) if k != 'PANEL_PRUEBA']
    if claves(crudo.decode('utf-8')) != claves(t):
        sys.exit('La estructura de config.js cambiaría: no se escribió nada. Lleva este mensaje a la conversación de diseño.')
    for clave in ('MODO', 'NOMBRE_EVENTO', 'CONTACTO', 'SUPABASE_JS', 'SUPABASE_JS_SRI'):
        if valor(crudo.decode('utf-8').replace('\r\n', '\n'), clave) != valor(t, clave):
            sys.exit(f'{clave} cambiaría: no debería. No se escribió nada.')
    aviso = lambda s: s[s.find('AVISO_PRIVACIDAD'):s.find('SUPABASE_JS')]
    if aviso(crudo.decode('utf-8').replace('\r\n', '\n')) != aviso(t):
        sys.exit('El aviso de privacidad cambiaría: no debería. No se escribió nada.')
    if (valor(t, 'MODO') or '').lower() != 'real':
        sys.exit(f"MODO es '{valor(t, 'MODO')}': para la apertura debe ser 'real'. No se escribió nada.")
    nueva = huella(t.encode('utf-8'))
    if antes == nueva:
        print('Ya estaba así: no hay nada que cambiar.')
        return
    if not aplicar:
        print('Nada escrito todavía. Para escribirlo: python sprints/sprint-6/configurar.py --aplicar')
        return
    if not ANTERIOR.exists():
        ANTERIOR.parent.mkdir(parents=True, exist_ok=True)
        ANTERIOR.write_bytes(crudo)
    with open(CONFIG, 'w', encoding='utf-8', newline='\n') as f:
        f.write(t)
    print(f'✔ Escrito: config.js apunta a PRODUCCIÓN. Huella nueva {nueva} (anótala en el reporte).')
    print('  copia anterior  sprints/sprint-6/anteriores/docs/config.js (para --revertir; no se sube a GitHub)')
    demos()


if __name__ == '__main__':
    main()
