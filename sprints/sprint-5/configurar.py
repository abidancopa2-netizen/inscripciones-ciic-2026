#!/usr/bin/env python3
"""
Sprint 5 · pone en docs/config.js el nombre del congreso, el contacto y el aviso de privacidad final.

    python sprints/sprint-5/configurar.py              # muestra qué cambiaría; no escribe
    python sprints/sprint-5/configurar.py --aplicar    # lo escribe (guarda antes tu config.js en sprints/sprint-5/anteriores/)
    python sprints/sprint-5/configurar.py --revertir   # devuelve tu config.js como estaba

Solo cambia tres valores: NOMBRE_EVENTO, CONTACTO y AVISO_PRIVACIDAD. Todo lo demás de tu config.js (MODO, API_URL,
ANON_KEY, SUPABASE_JS y su SRI) queda exactamente igual. Por eso va como script y no en el manifiesto: config.js es tuyo
(apunta a PRUEBA desde la Fase D) y la conversación de diseño no tiene tu versión.
Se puede correr dos veces: la segunda no cambia nada.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CONFIG = RAIZ / 'docs' / 'config.js'
ANTERIOR = Path(__file__).resolve().parent / 'anteriores' / 'docs' / 'config.js'   # junto a las de aplicar.py: su --revertir también lo devuelve (.gitignore)
BASE_ESPERADA = 'e6883d992eda'          # la huella que informó Claude Code al cerrar el Sprint 3 (D4)

NOMBRE_EVENTO = 'VII Congreso Internacional de Estudiantes de Ingeniería Civil · CIDEIC'
CONTACTO = '+51 927 457 291 (WhatsApp)'
AVISO = [
    'Aviso de privacidad · Inscripción a visitas técnicas y talleres del VII Congreso Internacional de Estudiantes de Ingeniería Civil (CIDEIC)',
    'Responsable. La Universidad Católica de Santa María (UCSM), con RUC 20141637941 y domicilio en Urb. San José s/n, Umacollo, Arequipa, '
    'es responsable del tratamiento de los datos personales que registras en este formulario. Se guardan en el banco de datos de inscripciones '
    'del congreso, a cargo de la UCSM.',
    'Qué datos y para qué. Registramos tu documento de identidad, nombres, apellidos, correo institucional, país, número de celular y las '
    'actividades que eliges. Los usamos para: (1) gestionar tu inscripción a visitas técnicas y talleres; (2) coordinar contigo por WhatsApp '
    'los detalles de tus actividades; (3) registrar tu asistencia; y (4) enviarte por correo solo avisos importantes sobre tu inscripción '
    '(cambios de fecha, hora o lugar, o cancelación de una actividad), cuando no podamos comunicarlo por WhatsApp. Todos los datos del '
    'formulario son obligatorios: sin ellos no podemos inscribirte. Para proteger el formulario de abusos guardamos por unos minutos datos '
    'técnicos de tu conexión, como la dirección IP. No tomamos decisiones automatizadas ni elaboramos perfiles: los cupos se asignan por orden '
    'de inscripción.',
    'Quién accede. Solo el equipo organizador, con cuentas individuales; los encargados de cada visita o taller reciben únicamente la lista '
    'de su actividad. No vendemos tus datos ni los compartimos con terceros para otros fines. Si te unes al grupo de WhatsApp de tu actividad, '
    'sus demás integrantes verán tu número.',
    'Dónde se guardan. En los servidores de Supabase (Supabase, Inc.), el proveedor de la plataforma, ubicados fuera del Perú. Supabase solo '
    'los guarda por encargo nuestro; es una transferencia internacional (flujo transfronterizo) de datos.',
    'Cuánto tiempo. Hasta 90 días después del congreso; luego los eliminamos.',
    'Tus derechos. Puedes ejercer tus derechos de información, acceso, rectificación, cancelación, oposición y portabilidad (recibir tus datos '
    'en un formato estructurado, de uso común y lectura mecánica) escribiendo a logisticacideic@gmail.com. Si consideras que no atendimos tu '
    'solicitud, puedes acudir a la Autoridad Nacional de Protección de Datos Personales del Ministerio de Justicia y Derechos Humanos. Este aviso '
    'se rige por la Ley N.º 29733, Ley de Protección de Datos Personales, y su reglamento, aprobado por el Decreto Supremo N.º 016-2024-JUS.',
]


def huella(b):
    return hashlib.sha256(b.replace(b'\r\n', b'\n')).hexdigest()[:12]


def js(texto):
    return json.dumps(texto, ensure_ascii=False)          # una cadena JSON es una cadena JavaScript válida


def fin_valor(t, i):
    """Avanza desde el inicio del valor sobre cadenas JavaScript ('…', "…", `…`) unidas con +, espacios y comentarios,
    hasta la coma (o la llave) que cierra la propiedad. Si encuentra otra cosa, no adivina: se detiene."""
    while i < len(t):
        c = t[i]
        if c in '\'"`':
            j = i + 1
            while j < len(t) and t[j] != c:
                if c != '`' and t[j] == '\n':
                    break
                j += 2 if t[j] == '\\' else 1
            if j >= len(t) or t[j] != c:
                return None
            i = j + 1
        elif t.startswith('//', i):
            i = t.find('\n', i)
            if i < 0:
                return None
        elif t.startswith('/*', i):
            i = t.find('*/', i)
            if i < 0:
                return None
            i += 2
        elif c in ' \t\r\n+':
            i += 1
        elif c in ',}':
            return i
        else:
            return None
    return None


def poner(t, clave, valor_js):
    """Reemplaza el valor (una cadena o varias unidas con +) de `clave:`; deja igual la coma y lo que sigue."""
    m = re.search(r'(?m)^([ \t]*)' + clave + r'[ \t]*:[ \t]*', t)
    fin = fin_valor(t, m.end()) if m else None
    if fin is None:
        sys.exit(f'No reconozco el valor de {clave} en docs/config.js: no se cambió nada. Lleva este mensaje a la conversación de diseño.')
    sep = ':' if valor_js.startswith('\n') else ': '
    crudo = t[m.end():fin]
    antes = crudo.rstrip()
    cola = crudo[len(antes):]                  # el salto de línea antes de "}" si era la última propiedad
    return t[:m.start()] + f'{m.group(1)}{clave}{sep}{valor_js}{cola}' + t[fin:], antes


def demos():
    armar = RAIZ / 'local' / 'armar_demos.py'
    if armar.exists():                     # las demos llevan config.js adentro: se vuelven a armar con el aviso nuevo
        import os
        import subprocess
        r = subprocess.run([sys.executable, str(armar)], capture_output=True, text=True, encoding='utf-8', errors='replace',
                           env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        print('  demos           ' + (r.stdout.strip().replace('\n', ' · ') if r.returncode == 0 else 'ERROR: ' + r.stderr.strip()[-200:]))


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')          # la consola de Windows (cp1252) no imprime "→" ni "✔"
    aplicar = '--aplicar' in sys.argv
    if '--revertir' in sys.argv:
        if not ANTERIOR.exists():
            sys.exit('No hay copia de tu config.js en sprints/sprint-5/anteriores/: no se cambió nada.')
        CONFIG.write_bytes(ANTERIOR.read_bytes())
        print(f'✔ docs/config.js devuelto como estaba (huella {huella(ANTERIOR.read_bytes())}).')
        demos()
        return
    crudo = CONFIG.read_bytes()
    antes = huella(crudo)
    t = crudo.decode('utf-8').replace('\r\n', '\n')
    aviso_js = ' +\n    '.join(js(p + ('\n\n' if i < len(AVISO) - 1 else '')) for i, p in enumerate(AVISO))
    t, v1 = poner(t, 'NOMBRE_EVENTO', js(NOMBRE_EVENTO))
    t, v2 = poner(t, 'CONTACTO', js(CONTACTO))
    t, v3 = poner(t, 'AVISO_PRIVACIDAD', '\n    ' + aviso_js)
    nueva = huella(t.encode('utf-8'))
    print(f'docs/config.js · huella actual {antes}' + ('' if antes in (BASE_ESPERADA, nueva) else f' (se esperaba {BASE_ESPERADA}: revisa que sea tu config.js)'))
    print(f'  NOMBRE_EVENTO   {v1[:70]}  →  {NOMBRE_EVENTO}')
    print(f'  CONTACTO        {v2[:70]}  →  {CONTACTO}')
    print(f'  AVISO           {len(AVISO)} párrafos · ' + ('quedan [corchetes]' if re.search(r'\[[^\]\n]{3,60}\]', t) else 'sin [corchetes]'))
    claves = lambda s: re.findall(r'(?m)^\s*([A-Z_]+)\s*:', s)
    if claves(crudo.decode('utf-8')) != claves(t):           # misma lista de propiedades, en el mismo orden: no se comió ninguna
        sys.exit('La estructura de config.js cambiaría (propiedades distintas): no se escribió nada. Lleva este mensaje a la conversación de diseño.')
    for clave in ('MODO', 'API_URL', 'ANON_KEY', 'SUPABASE_JS', 'SUPABASE_JS_SRI'):
        a = re.search(r'(?m)^\s*' + clave + r"\s*:\s*'([^']*)'", crudo.decode('utf-8'))
        b = re.search(r'(?m)^\s*' + clave + r"\s*:\s*'([^']*)'", t)
        if (a and a.group(1)) != (b and b.group(1)):
            sys.exit(f'{clave} cambiaría: no debería. No se escribió nada.')
    if antes == nueva:
        print('Ya estaba así: no hay nada que cambiar.')
        return
    if not aplicar:
        print('\nTexto del aviso, como lo verá el participante:\n')
        print('\n\n'.join(AVISO))
        print(f'\nHuella del texto del aviso: {huella(chr(10).join(AVISO).encode())} (la misma que aprobó el propietario en la conversación de diseño)')
        print('Nada escrito todavía. Si el propietario lo aprueba: python sprints/sprint-5/configurar.py --aplicar')
        return
    if not ANTERIOR.exists():              # la primera copia es la tuya original; una segunda corrida no la pisa
        ANTERIOR.parent.mkdir(parents=True, exist_ok=True)
        ANTERIOR.write_bytes(crudo)
    with open(CONFIG, 'w', encoding='utf-8', newline='\n') as f:
        f.write(t)
    print(f'✔ Escrito. Huella nueva de docs/config.js: {nueva} (anótala en el reporte: es la base de la próxima entrega que lo toque).')
    print('  copia anterior  sprints/sprint-5/anteriores/docs/config.js (para --revertir; no se sube a GitHub)')
    demos()


if __name__ == '__main__':
    main()
