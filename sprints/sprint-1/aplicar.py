#!/usr/bin/env python3
"""
Aplica el Sprint 1 al proyecto, desde la raíz del repositorio:

    python sprints/sprint-1/aplicar.py              # copia los archivos a su lugar
    python sprints/sprint-1/aplicar.py --verificar  # solo dice qué cambiaría
    python sprints/sprint-1/aplicar.py --revertir   # vuelve a las versiones anteriores

Copia cada archivo de archivos/ a la misma ruta en la raíz, guarda la versión anterior en anteriores/
(para poder revertir) y rearma las demos (demo/*.html) porque cambian docs/config.js y docs/panel.html.
No toca la base de datos: eso lo hace la instalación desde cero de la skill ciic-desarrollo.
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
ARCH = AQUI / 'archivos'
ANT = AQUI / 'anteriores'


def huella(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:10] if p.exists() else '—'


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else ''
    if not (RAIZ / 'CLAUDE.md').exists():
        sys.exit(f'No encuentro la raíz del proyecto (busqué CLAUDE.md en {RAIZ}).')
    nuevos = sorted(p for p in ARCH.rglob('*') if p.is_file())
    if modo == '--revertir':
        if not ANT.exists():
            sys.exit('No hay versiones anteriores guardadas: el sprint no se aplicó con este script.')
        for p in sorted(x for x in ANT.rglob('*') if x.is_file()):
            rel = p.relative_to(ANT)
            if p.name.endswith('.no_existia'):
                destino = RAIZ / str(rel)[:-len('.no_existia')]
                destino.unlink(missing_ok=True)
                print(f'  quitado    {destino.relative_to(RAIZ)}')
            else:
                shutil.copy2(p, RAIZ / rel)
                print(f'  restaurado {rel}')
        armar_demos()
        print('Sprint revertido. Vuelve a instalar la base desde cero (sin la migración de este sprint).')
        return
    cambios = 0
    print(f'Sprint 1 → {RAIZ}')
    for p in nuevos:
        rel = p.relative_to(ARCH)
        destino = RAIZ / rel
        antes, despues = huella(destino), huella(p)
        estado = 'igual' if antes == despues else ('nuevo' if antes == '—' else 'cambia')
        print(f'  {estado:7} {rel}  ({antes} → {despues})')
        if estado == 'igual' or modo == '--verificar':
            continue
        cambios += 1
        respaldo = ANT / rel
        if not respaldo.exists() and not Path(str(respaldo) + '.no_existia').exists():
            respaldo.parent.mkdir(parents=True, exist_ok=True)
            if destino.exists():
                shutil.copy2(destino, respaldo)
            else:
                Path(str(respaldo) + '.no_existia').write_text('', encoding='utf-8')
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, destino)
    if modo == '--verificar':
        print('Solo verificación: no se copió nada.')
        return
    if cambios:
        armar_demos()
    print(f'Listo: {cambios} archivos copiados. Versiones anteriores en {ANT.relative_to(RAIZ)}/.')
    print('Siguiente: instala la base desde cero (incluye supabase/03_*.sql), reinicia el servidor local y corre el tester (skill ciic-desarrollo).')


def armar_demos():
    script = RAIZ / 'local' / 'armar_demos.py'
    if script.exists():
        r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        print('  demos      ' + (r.stdout.strip().replace('\n', ' · ') if r.returncode == 0 else 'ERROR: ' + r.stderr.strip()[-200:]))


if __name__ == '__main__':
    main()
