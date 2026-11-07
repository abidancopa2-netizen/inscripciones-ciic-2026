#!/usr/bin/env python3
"""
Sprint 5.1 · La fuente Saira pasa a docs/tema/fuentes/: las páginas dejan de llamar a Google Fonts.

Hasta el Sprint 5, index.html y panel.html cargaban Saira desde fonts.googleapis.com, y Google recibía la IP de
cada participante. Este script baja UNA vez, desde tu PC, la misma fuente que el tema pedía (Saira, ejes de ancho
75–125 y de peso 300–800, solo los juegos de letras latinos: español, tildes, eñes) y la deja en docs/tema/fuentes/:

    saira.css · saira-latin.woff2 · saira-latin-ext.woff2 · OFL.txt (licencia SIL Open Font License 1.1)

La licencia OFL permite alojarla y servirla junto con las páginas. Después vuelve a armar las demos.

    python sprints/sprint-5.1/fuente.py            # baja y escribe; si ya está, solo muestra sus huellas
    python sprints/sprint-5.1/fuente.py --forzar   # la vuelve a bajar

Escribe todo o nada: si Google responde algo inesperado, no deja archivos a medias.
"""
import hashlib
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DEST = RAIZ / 'docs' / 'tema' / 'fuentes'
CSS_URL = 'https://fonts.googleapis.com/css2?family=Saira:wdth,wght@75..125,300..800&display=swap'   # la misma que pedía el tema
OFL_URL = 'https://raw.githubusercontent.com/google/fonts/main/ofl/saira/OFL.txt'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'   # así Google entrega woff2
SUBCONJUNTOS = ('latin-ext', 'latin')
CABECERA = """/* Saira · Copyright The Saira Project Authors · SIL Open Font License 1.1 (OFL.txt, https://openfontlicense.org).
   Alojada aquí desde el Sprint 5.1 para no llamar a Google Fonts. La generó sprints/sprint-5.1/fuente.py desde:
   %s */
"""


def huella(b):
    return hashlib.sha256(b.replace(b'\r\n', b'\n')).hexdigest()[:12]


def bajar(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30) as r:
        return r.read()


def demos():
    armar = RAIZ / 'local' / 'armar_demos.py'
    if armar.exists():
        r = subprocess.run([sys.executable, str(armar)], capture_output=True, text=True, encoding='utf-8', errors='replace',
                           env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        print('  demos      ' + (r.stdout.strip().replace('\n', ' · ') if r.returncode == 0 else 'ERROR: ' + r.stderr.strip()[-200:]))


def mostrar():
    for p in sorted(DEST.iterdir()):
        print(f'  {p.name:22} {p.stat().st_size // 1024:>4} KB · huella {huella(p.read_bytes())}')


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if (DEST / 'saira.css').exists() and '--forzar' not in sys.argv:
        print('La fuente ya está en docs/tema/fuentes/ (para bajarla otra vez: --forzar):')
        mostrar()
        return
    try:
        css = bajar(CSS_URL).decode('utf-8')
    except Exception as e:  # noqa: BLE001
        sys.exit(f'No pude leer {CSS_URL}: {e}. Revisa tu conexión: no se escribió nada.')
    bloques = [(s, b) for s, b in re.findall(r'/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{[^}]*\})', css) if s in SUBCONJUNTOS]
    if [s for s, _ in bloques] != list(SUBCONJUNTOS):
        sys.exit(f'Google Fonts respondió algo inesperado (juegos: {[s for s, _ in bloques]}): no se escribió nada. '
                 'Lleva este mensaje a la conversación de diseño.')
    archivos, partes = {}, [CABECERA % CSS_URL]
    for sub, bloque in bloques:
        m = re.search(r'url\((https://fonts\.gstatic\.com/[^)\s]+\.woff2)\)', bloque)
        if not m or 'font-family: \'Saira\'' not in bloque.replace('"', "'"):
            sys.exit(f'El bloque {sub} no tiene la forma esperada: no se escribió nada.')
        datos = bajar(m.group(1))
        if datos[:4] != b'wOF2' or len(datos) < 10_000:
            sys.exit(f'{m.group(1)} no es un woff2 válido ({len(datos)} bytes): no se escribió nada.')
        nombre = f'saira-{sub}.woff2'
        archivos[nombre] = datos
        partes.append(f'/* {sub} */\n' + bloque.replace(m.group(1), nombre) + '\n')
    archivos['saira.css'] = '\n'.join(partes).encode('utf-8')
    try:
        ofl = bajar(OFL_URL)
        if b'SIL OPEN FONT LICENSE' not in ofl.upper():
            raise ValueError('no parece la licencia OFL')
        archivos['OFL.txt'] = ofl
    except Exception as e:  # noqa: BLE001
        print(f'  aviso: no pude bajar la licencia ({e}); saira.css la nombra en su cabecera. Puedes copiarla después desde {OFL_URL}')
    DEST.mkdir(parents=True, exist_ok=True)
    for nombre, datos in archivos.items():
        (DEST / nombre).write_bytes(datos)
    print('✔ Fuente alojada en docs/tema/fuentes/ (anota estas huellas en el reporte):')
    mostrar()
    demos()


if __name__ == '__main__':
    main()
