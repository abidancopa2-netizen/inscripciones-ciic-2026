#!/usr/bin/env python3
"""
Aplica una entrega de sprint al proyecto. Desde la raíz del repositorio:

    python sprints/<sprint>/aplicar.py              # revisa y copia
    python sprints/<sprint>/aplicar.py --verificar  # solo dice qué haría
    python sprints/<sprint>/aplicar.py --revertir   # vuelve a las versiones anteriores
    python sprints/<sprint>/aplicar.py --forzar     # copia aunque haya cambios locales no previstos (no recomendado)

manifiesto.json dice, para cada archivo, sobre qué versión se escribió (base) y cuál trae (nuevo). Si el archivo
del proyecto no es ni la base ni la nueva, alguien lo cambió aquí: se detiene SIN copiar nada y lo informa,
salvo que su huella esté entre las "locales" que la entrega ya incorpora (arreglos reportados). Las huellas
ignoran los finales de línea (CRLF = LF). Guarda las versiones anteriores en anteriores/ y rearma las demos
si cambió algo de docs/.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
ARCH = AQUI / 'archivos'
ANT = AQUI / 'anteriores'
NOMBRE = AQUI.name


def huellas(p: Path):
    """Huella sin finales de línea y huella cruda (la que reportaba la versión anterior de este script)."""
    if not p.exists():
        return {None}
    b = p.read_bytes()
    return {hashlib.sha256(b.replace(b'\r\n', b'\n')).hexdigest()[:12], hashlib.sha256(b).hexdigest()[:12]}


def huella(p: Path):
    return sorted(x for x in huellas(p) if x)[0] if p.exists() else None


def armar_demos():
    script = RAIZ / 'local' / 'armar_demos.py'
    if script.exists():
        r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        print('  demos       ' + (r.stdout.strip().replace('\n', ' · ') if r.returncode == 0 else 'ERROR: ' + r.stderr.strip()[-200:]))


def revertir():
    if not ANT.exists():
        sys.exit('No hay versiones anteriores guardadas: esta entrega no se aplicó con este script.')
    for p in sorted(x for x in ANT.rglob('*') if x.is_file()):
        rel = p.relative_to(ANT)
        if p.name.endswith('.no_existia'):
            destino = RAIZ / str(rel)[:-len('.no_existia')]
            destino.unlink(missing_ok=True)
            print(f'  quitado     {destino.relative_to(RAIZ)}')
        else:
            shutil.copy2(p, RAIZ / rel)
            print(f'  restaurado  {rel}')
    armar_demos()
    print(f'{NOMBRE} revertido. Si tenía migraciones SQL, instala la base desde cero sin ellas.')


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else ''
    if not (RAIZ / 'CLAUDE.md').exists():
        sys.exit(f'No encuentro la raíz del proyecto (busqué CLAUDE.md en {RAIZ}).')
    if modo == '--revertir':
        return revertir()
    man = json.loads((AQUI / 'manifiesto.json').read_text(encoding='utf-8'))
    plan, conflictos = [], []
    print(f'{NOMBRE} → {RAIZ}')
    for rel, m in sorted(man['archivos'].items()):
        destino, origen = RAIZ / rel, ARCH / rel
        actual = huellas(destino)
        if m['nuevo'] not in huellas(origen):
            sys.exit(f'La entrega está dañada: {rel} no coincide con el manifiesto. Vuelve a descomprimir el zip.')
        if m['nuevo'] in actual:
            print(f'  igual       {rel}')
            continue
        locales = set(m.get('locales', []))
        if m['base'] in actual:
            plan.append((rel, 'nuevo' if m['base'] is None else 'cambia', ''))
        elif m.get('incorpora') and (actual & locales or not locales):
            plan.append((rel, 'incorpora', m['incorpora']))
        else:
            conflictos.append((rel, huella(destino), m['base']))
    for rel, estado, nota in plan:
        print(f'  {estado:11} {rel}' + (f'  · {nota}' if nota else ''))
    if conflictos:
        print('\n⚠ Archivos cambiados aquí que esta entrega no conoce (no se copió NADA):')
        for rel, actual, base in conflictos:
            print(f'    {rel}  (aquí {actual}, se esperaba {base})')
        print('  Lleva esta lista a la conversación de diseño para que la entrega incorpore esos cambios.')
        if modo != '--forzar':
            sys.exit(1)
        print('  --forzar: se copian igual y los cambios locales quedan en anteriores/.')
        plan += [(rel, 'forzado', '') for rel, _, _ in conflictos]
    if modo == '--verificar':
        print('Solo verificación: no se copió nada.')
        return
    for rel, _, _ in plan:
        destino, respaldo = RAIZ / rel, ANT / rel
        if not respaldo.exists() and not Path(str(respaldo) + '.no_existia').exists():
            respaldo.parent.mkdir(parents=True, exist_ok=True)
            if destino.exists():
                shutil.copy2(destino, respaldo)
            else:
                Path(str(respaldo) + '.no_existia').write_text('', encoding='utf-8')
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ARCH / rel, destino)
    if any(rel.startswith('docs/') for rel, _, _ in plan):
        armar_demos()
    print(f'Listo: {len(plan)} archivos copiados. Anteriores en {ANT.relative_to(RAIZ)}/.')
    if man.get('siguiente'):
        print('Siguiente: ' + man['siguiente'])


if __name__ == '__main__':
    main()
