#!/usr/bin/env python3
"""
Arma las DEMOS AUTÓNOMAS: un solo archivo HTML por página, con estilos, configuración,
datos ficticios y backend de demostración adentro. Se abren con doble clic, sin servidor
ni Supabase, y sirven para diseñar. Vuelve a correrlo después de cambiar docs/.

    python local/armar_demos.py   →   demo/demo-participante.html · demo/demo-panel.html
"""
import base64
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
def escribir(ruta, texto):
    """Siempre UTF-8 y finales de línea LF, también en Windows: así las huellas de aplicar.py no cambian."""
    with open(ruta, 'w', encoding='utf-8', newline='\n') as f:
        f.write(texto)


docs = RAIZ / 'docs'
css = (docs / 'base.css').read_text(encoding='utf-8')
config = (docs / 'config.js').read_text(encoding='utf-8')
config = re.sub(r"(?m)^(\s*)MODO\s*:\s*'[^']*'", r"\1MODO: 'demo'", config)
datos = (docs / 'demo/datos-demo.js').read_text(encoding='utf-8')
api = (docs / 'demo/demo-api.js').read_text(encoding='utf-8')
cabecera = ('<!-- DEMO AUTÓNOMA · generada por local/armar_demos.py desde docs/%s. No editar aquí: edita docs/ y vuelve a armar. '
            'Funciona con doble clic; comparte datos con la otra demo si están en la misma carpeta. -->\n')
def tema_en_linea(h):
    """El tema (docs/tema/) entra en la demo: su CSS y su JS en línea, y sus imágenes como data:, para que siga siendo un solo archivo."""
    img = lambda ruta: 'data:image/webp;base64,' + base64.b64encode((docs / ruta).read_bytes()).decode()
    def css(m):
        txt = (docs / m.group(1)).read_text(encoding='utf-8')
        txt = re.sub(r'url\("img/([\w.-]+\.webp)"\)', lambda u: 'url("' + img('tema/img/' + u.group(1)) + '")', txt)
        return '<style>\n' + txt + '</style>'
    def fuente(m):                         # Sprint 5.1: la fuente vive en docs/tema/fuentes/ (la baja sprints/sprint-5.1/fuente.py)
        ruta = docs / m.group(1)
        if not ruta.exists():
            print('  aviso: falta ' + m.group(1) + ' (corre python sprints/sprint-5.1/fuente.py): la demo usa la letra del sistema')
            return ''
        woff2 = lambda u: 'url(data:font/woff2;base64,' + base64.b64encode((ruta.parent / u.group(1)).read_bytes()).decode() + ')'
        return '<style>\n' + re.sub(r'url\(([\w.-]+\.woff2)\)', woff2, ruta.read_text(encoding='utf-8')) + '</style>'
    h = re.sub(r'<link rel="stylesheet" href="(tema/fuentes/[\w.-]+\.css)">\n?', fuente, h)
    h = re.sub(r'<link rel="stylesheet" href="(tema/[\w.-]+\.css)">', css, h)
    h = re.sub(r'<script src="(tema/[\w.-]+\.js)"></script>', lambda m: '<script>\n' + (docs / m.group(1)).read_text(encoding='utf-8') + '</script>', h)
    return re.sub(r'src="(tema/img/[\w.-]+\.webp)"', lambda m: 'src="' + img(m.group(1)) + '"', h)


for origen, destino, otra in [('index.html', 'demo-participante.html', ('panel.html', 'demo-panel.html')), ('panel.html', 'demo-panel.html', ('index.html', 'demo-participante.html'))]:
    h = (docs / origen).read_text(encoding='utf-8')
    h = h.replace('<link rel="stylesheet" href="base.css">', '<style>\n' + css + '\n</style>', 1)
    h = tema_en_linea(h)
    h = h.replace('<script src="config.js"></script>', '<script>\n' + config + '\n</script>\n<script>\n' + datos + '\n</script>\n<script>\n' + api + '\n</script>', 1)
    h = h.replace("href: '%s'" % otra[0], "href: '%s'" % otra[1])
    h = re.sub(r'(<html lang="es"[^>]*>\n)', lambda m: m.group(1) + cabecera % origen, h, count=1)
    (RAIZ / 'demo').mkdir(exist_ok=True)
    escribir(RAIZ / 'demo' / destino, h)
    print(destino, len(h) // 1024, 'KB')
