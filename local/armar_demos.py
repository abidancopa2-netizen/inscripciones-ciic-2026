#!/usr/bin/env python3
"""
Arma las DEMOS AUTÓNOMAS: un solo archivo HTML por página, con estilos, configuración,
datos ficticios y backend de demostración adentro. Se abren con doble clic, sin servidor
ni Supabase, y sirven para diseñar. Vuelve a correrlo después de cambiar docs/.

    python local/armar_demos.py   →   demo/demo-participante.html · demo/demo-panel.html
"""
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
for origen, destino, otra in [('index.html', 'demo-participante.html', ('panel.html', 'demo-panel.html')), ('panel.html', 'demo-panel.html', ('index.html', 'demo-participante.html'))]:
    h = (docs / origen).read_text(encoding='utf-8')
    h = h.replace('<link rel="stylesheet" href="base.css">', '<style>\n' + css + '\n</style>', 1)
    h = h.replace('<script src="config.js"></script>', '<script>\n' + config + '\n</script>\n<script>\n' + datos + '\n</script>\n<script>\n' + api + '\n</script>', 1)
    h = h.replace("href: '%s'" % otra[0], "href: '%s'" % otra[1])
    h = h.replace('<html lang="es">\n', '<html lang="es">\n' + cabecera % origen, 1)
    (RAIZ / 'demo').mkdir(exist_ok=True)
    escribir(RAIZ / 'demo' / destino, h)
    print(destino, len(h) // 1024, 'KB')
