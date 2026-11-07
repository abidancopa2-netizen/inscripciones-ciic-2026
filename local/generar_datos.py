#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════════
  GENERADOR DE LA BASE FICTICIA · Inscripciones CIIC 2026 · contrato v5.5
  Todo es inventado (nombres, documentos, correos, celulares). Siempre genera
  lo mismo (semilla fija), así las pruebas son repetibles.

  python local/generar_datos.py                 # esquema de la base v5.5 (desde el Sprint 2)
  python local/generar_datos.py --esquema v51   # solo para una base anterior al Sprint 2

  Escribe:
    docs/demo/datos-demo.js          estado completo del modo demo (padrón, actividades, ~700 inscripciones)
    local/datos_prueba.sql           padrón + actividades + configuración, SIN inscripciones (para el tester)
    local/inscripciones_prueba.sql   ~700 inscripciones para explorar el panel (opcional, después del anterior)
    local/padron_prueba.csv          el padrón completo en formato de importación (documento;etapa)
    local/padron_importar_ejemplo.csv  200 documentos nuevos + casos difíciles para probar "Importar padrón"
    local/actividades_prueba.csv     el catálogo en formato de importación (para probar "Importar actividades")
════════════════════════════════════════════════════════════════════════
"""
import argparse
import json
import random
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
R = random.Random(2026)

# ── Actividades (28: 14 por día; 2 ocultas) ──
D1, D2 = '12/11/2026', '13/11/2026'
ACTS = [
    # id, tipo, nombre, lugar, fecha, inicio, fin, cupo, publicada, descripcion, modo, enlace?
    ('VIS01', 'VISITA', 'Planta de tratamiento de agua potable La Atarjea', 'El Agustino, Lima', D1, '08:00', '12:00', 25, True, 'Punto de encuentro: puerta principal del congreso, 30 minutos antes. Casco y chaleco obligatorios.', 'ENLACE', True),
    ('VIS02', 'VISITA', 'Obra vial: intercambio Av. Periférica', 'San Juan de Lurigancho, Lima', D1, '08:30', '12:30', 20, True, '', 'ENLACE', True),
    ('VIS03', 'VISITA', 'Presa de derivación Huachipa', 'Lurigancho-Chosica, Lima', D1, '07:30', '13:00', 15, True, 'Llevar DNI físico: la presa exige registro en la entrada.', 'ENLACE', True),
    ('VIS04', 'VISITA', 'Metro de Lima · túnel de la Línea 2', 'Ate, Lima', D1, '09:00', '12:00', 30, True, 'Calzado de seguridad obligatorio.', 'ENLACE', True),
    ('VIS05', 'VISITA', 'Puente vehicular Villa El Salvador', 'Villa El Salvador, Lima', D1, '14:00', '17:00', 20, True, '', 'ENLACE', True),
    ('VIS06', 'VISITA', 'Planta de prefabricados de concreto', 'Lurín, Lima', D1, '08:00', '12:00', 20, True, 'Salida en bus a las 07:15 desde la puerta principal.', 'ENLACE', True),
    ('VIS07', 'VISITA', 'Edificio corporativo con aisladores sísmicos', 'San Isidro, Lima', D1, '09:30', '12:00', 25, True, '', 'ENLACE', True),
    ('TAL01', 'TALLER', 'Modelado BIM para obras viales', 'Auditorio A', D1, '15:00', '18:00', 150, True, 'Trae laptop con el software indicado en el grupo de WhatsApp.', 'ENLACE', True),
    ('TAL02', 'TALLER', 'Diseño de mezclas de concreto de alta resistencia', 'Laboratorio 1', D1, '15:00', '18:00', 120, True, '', 'ENLACE', True),
    ('TAL03', 'TALLER', 'Geotecnia aplicada a cimentaciones profundas', 'Auditorio B', D1, '15:00', '18:00', 140, True, '', 'ENLACE', True),
    ('TAL04', 'TALLER', 'Topografía y fotogrametría con drones', 'Aula 204', D1, '15:00', '18:00', 110, True, '', 'ENLACE', True),
    ('TAL05', 'TALLER', 'Gestión de riesgos de desastres en obras', 'Auditorio C', D1, '15:00', '18:00', 130, True, '', 'ENLACE', True),
    ('TAL06', 'TALLER', 'Programación de obras con Primavera P6', 'Laboratorio de cómputo 2', D1, '15:30', '18:30', 120, True, 'Trae laptop con Primavera P6 instalado (versión de prueba).', 'ENLACE', True),
    ('VIS13', 'VISITA', 'Viaducto Costa Verde (en preparación)', 'Magdalena del Mar, Lima', D1, '08:00', '11:00', 15, False, '', 'ENLACE', False),
    ('VIS08', 'VISITA', 'Central hidroeléctrica Callahuanca', 'Huarochirí, Lima', D2, '07:00', '14:00', 15, True, 'Salida en bus a las 06:30. Retorno aproximado a las 16:00.', 'ENLACE', True),
    ('VIS09', 'VISITA', 'Proyecto de saneamiento integral', 'Carabayllo, Lima', D2, '09:00', '12:00', 25, True, '', 'ENLACE', True),
    ('VIS10', 'VISITA', 'Laboratorio de suelos e hidráulica', 'Rímac, Lima', D2, '10:00', '13:00', 20, True, '', 'ENLACE', True),
    ('VIS11', 'VISITA', 'Planta de asfalto industrial', 'Lurín, Lima', D2, '08:30', '12:00', 20, True, '', 'MANUAL', False),
    ('VIS12', 'VISITA', 'Torre Bicentenario · edificio inteligente', 'San Isidro, Lima', D2, '08:00', '11:30', 20, True, '', 'ENLACE', True),
    ('VIS14', 'VISITA', 'Nuevo Puerto del Callao · muelle de contenedores', 'Callao', D2, '08:00', '12:30', 30, True, 'Llevar DNI físico y chaleco reflectivo.', 'ENLACE', True),
    ('VIS15', 'VISITA', 'Hospital de alta complejidad en construcción', 'Ate, Lima', D2, '09:00', '12:00', 20, True, '', 'MANUAL', False),
    ('TAL07', 'TALLER', 'Gestión de proyectos con Last Planner', 'Auditorio A', D2, '15:00', '18:00', 150, True, '', 'ENLACE', True),
    ('TAL08', 'TALLER', 'Análisis sísmico de edificaciones con ETABS', 'Laboratorio de cómputo 1', D2, '15:00', '18:00', 120, True, 'Trae laptop con ETABS instalado (versión educativa).', 'ENLACE', True),
    ('TAL09', 'TALLER', 'Hidráulica de canales con HEC-RAS', 'Aula 301', D2, '15:00', '18:00', 130, True, '', 'ENLACE', True),
    ('TAL10', 'TALLER', 'Pavimentos: diseño y mantenimiento', 'Auditorio B', D2, '15:00', '18:00', 140, True, '', 'ENLACE', False),
    ('TAL11', 'TALLER', 'Estructuras de acero y conexiones', 'Aula 204', D2, '15:00', '18:00', 110, True, '', 'ENLACE', True),
    ('TAL12', 'TALLER', 'Norma E.030 y diseño sismorresistente', 'Auditorio C', D2, '15:00', '18:00', 120, True, '', 'ENLACE', True),
    ('VIS16', 'VISITA', 'Túnel Trasandino (por confirmar)', 'Matucana, Lima', D2, '07:00', '15:00', 15, False, '', 'ENLACE', False),
]

NOMBRES = ['Lucía', 'Jorge', 'María', 'Carlos', 'Rosa', 'Luis', 'Ana', 'Pedro', 'Elena', 'Diego', 'Valeria', 'Andrés', 'Camila', 'Renzo', 'Fiorella',
           'Kevin', 'Milagros', 'Brayan', 'Gianella', 'Joel', 'Sofía', 'Mateo', 'Daniela', 'Sebastián', 'Ximena', 'Alonso', 'Nicole', 'Fabricio', 'Andrea',
           'Gabriel', 'Paola', 'Rodrigo', 'Karla', 'Jhon', 'Yesenia', 'Piero', 'Rocío', 'Franco', 'Lizbeth', 'Edwin', 'Melissa', 'Christian', 'Katherine',
           'Alexis', 'Jimena', 'Bruno', 'Antonella', 'Marco Antonio', 'Ana Lucía', 'José Luis', 'María Fernanda', 'Juan Carlos', 'Luz Marina', 'Miguel Ángel']
APELLIDOS = ['Quispe', 'Mamani', 'Huamán', 'Flores', 'Rojas', 'Torres', 'Vargas', 'Castillo', 'Ramos', 'Chávez', 'Condori', 'Mendoza', 'Salazar',
             'Paredes', 'Gutiérrez', 'Ccori', 'Huanca', 'Apaza', 'Espinoza', 'Ríos', 'Soto', 'Díaz', 'Ruiz', 'León', 'Paz', 'Cruz', 'Vega', 'Luna',
             'Rivas', 'Ortiz', 'Sánchez', 'Ramírez', 'García', 'Rodríguez', 'López', 'Pérez', 'Gonzales', 'Fernández', 'Cárdenas', 'Valverde', 'Ñahui',
             'Tito', 'Cusi', 'Villanueva', 'Medina', 'Aguilar', 'Silva', 'Romero', 'Herrera', 'Delgado', 'Zapata', 'Navarro', 'Cabrera', 'Pacheco']
DOMINIOS = ['uni.edu.pe', 'unmsm.edu.pe', 'pucp.edu.pe', 'urp.edu.pe', 'upc.edu.pe', 'unfv.edu.pe', 'usmp.pe', 'ucv.edu.pe', 'uncp.edu.pe', 'unsa.edu.pe']
ESPECIALES = [   # documentos con un caso que mostrar (los de la cinta del modo demo)
    ('04567812', 1, 'DNI que empieza con 0. Se inscribe y puede elegir visitas'),
    ('04123456', 1, 'DNI guardado sin el 0 inicial (escribe 4123456): la base lo completa'),
    ('12345678K', 1, 'Documento extranjero con letra (RUT de Chile)'),
    ('78695681', 1, 'Ya inscrito: solo aparece el aviso, sin datos'),
    ('68133993', 2, 'Ya inscrito, Etapa 2'),
    ('001234567', 2, 'Carnet de extranjería, Etapa 2: por ahora solo talleres'),
    ('PA5566778', 2, 'Pasaporte, Etapa 2'),
    ('42048123', 3, 'Etapa 3: la inscripción aún no está habilitada'),
]
CINTA = [('04567812', 1, ESPECIALES[0][2]), ('4123456', 1, ESPECIALES[1][2]), ('12345678K', 1, ESPECIALES[2][2]), ('78695681', 1, ESPECIALES[3][2]),
         ('001234567', 2, ESPECIALES[5][2]), ('PA5566778', 2, ESPECIALES[6][2]), ('42048123', 3, ESPECIALES[7][2]),
         ('99999999', None, 'No está en el padrón: descuenta intentos (4 por dispositivo)'), ('12 3', None, 'Formato inválido: descuenta intentos')]

def escribir(ruta, texto):
    """Siempre UTF-8 y finales de línea LF, también en Windows: así las huellas de aplicar.py no cambian."""
    with open(ruta, 'w', encoding='utf-8', newline='\n') as f:
        f.write(texto)



def sin_tilde(t):
    return t.translate(str.maketrans('áéíóúÁÉÍÓÚñÑ', 'aeiouAEIOUnN')).lower().replace(' ', '')


def padron():
    usados = {d for d, _, _ in ESPECIALES} | {'99999999', '04123456'}
    filas = [{'documento': d, 'etapa': e, 'origen': 'CARGA', 'datos': {'caso': c}} for d, e, c in ESPECIALES]
    objetivo = {1: 1800, 2: 1000, 3: 400}
    for etapa, n in objetivo.items():
        k = sum(1 for f in filas if f['etapa'] == etapa)
        while k < n:
            x = R.random()
            if x < 0.94:
                d = str(R.randint(10_000_000, 79_999_999))
            elif x < 0.98:
                d = '00' + str(R.randint(1_000_000, 9_999_999))          # carnet de extranjería
            else:
                d = R.choice(['PA', 'PE', 'AB', 'XC']) + str(R.randint(1_000_000, 9_999_999))   # pasaporte
            if d in usados:
                continue
            usados.add(d)
            compra = '%02d/%02d/2026' % (R.randint(1, 28), {1: 7, 2: 8, 3: 9}[etapa])
            filas.append({'documento': d, 'etapa': etapa, 'origen': 'CARGA', 'datos': {'fecha_compra': compra}})
            k += 1
    filas.append({'documento': '71234500', 'etapa': 1, 'origen': 'PANEL', 'datos': None})   # agregado de último momento
    return filas


def inscripciones(pad, acts):
    restante = {a['id']: a['cupo'] for a in acts if a['publicada']}
    dia = {a['id']: a['fecha'] for a in acts}
    tipo = {a['id']: a['tipo'] for a in acts}
    candidatos = [p for p in pad if p['etapa'] in (1, 2) and p['documento'] not in {'04567812', '04123456', '12345678K', '001234567', 'PA5566778', '71234500'}]
    R.shuffle(candidatos)
    POP = {'VIS03': 6, 'VIS08': 6, 'VIS04': 4, 'VIS14': 4, 'VIS12': 3, 'VIS01': 2, 'TAL01': 2.5, 'TAL07': 2.5, 'TAL08': 1.5}   # las más pedidas se llenan
    elegir = lambda ids: R.choices(ids, weights=[restante[i] * POP.get(i, 1) for i in ids])[0] if ids and sum(restante[i] for i in ids) > 0 else None
    letras = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    codigos, celulares, ins = set(), set(), []
    reloj = 8 * 3600

    def nuevo_codigo():
        while True:
            c = 'CIIC-' + ''.join(R.choice(letras) for _ in range(5))
            if c not in codigos:
                codigos.add(c)
                return c

    fijos = {'78695681': ('Miguel', 'Navarro Mamani', '+51987112233', ['VIS01', 'TAL07']), '68133993': ('Roberto', 'Espinoza Espinoza', '+51986554411', ['TAL02', 'TAL08'])}
    orden = [p for p in pad if p['documento'] in fijos] + candidatos
    meta, anuladas = 700, 20
    for p in orden:
        if len(ins) >= meta + anuladas:
            break
        doc = p['documento']
        if doc in fijos:
            nom, ape, cel, sel = fijos[doc]
        else:
            quiere_visita = p['etapa'] == 1 and R.random() < 0.62
            dia_visita = R.choice([D1, D2])
            sel = []
            for f in (D1, D2):
                ids = [i for i, r in restante.items() if dia[i] == f and r > 0 and (tipo[i] == 'TALLER' or (quiere_visita and f == dia_visita))]
                vis = [i for i in ids if tipo[i] == 'VISITA']
                i = elegir(vis) if vis and R.random() < 0.85 else elegir([i for i in ids if tipo[i] == 'TALLER'])
                if i is None:
                    break
                sel.append(i)
            if len(sel) < 2:
                continue
            nom = R.choice(NOMBRES)
            ape = R.choice(APELLIDOS) + ' ' + R.choice(APELLIDOS)
            if R.random() < 0.02:
                cel = '+569' + str(R.randint(10_000_000, 99_999_999))
            else:
                cel = '+519' + str(R.randint(10_000_000, 99_999_999))
            if len(ins) in (40, 41, 90, 91, 300, 301):        # tres pares de celulares repetidos (hermanos, padres)
                cel = '+51955000' + str(100 + len(ins) // 2)
            elif cel in celulares:
                continue
        celulares.add(cel)
        estado = 'ANULADO' if len(ins) >= meta else 'CONFIRMADO'
        if estado == 'CONFIRMADO':
            for i in sel:
                restante[i] -= 1
        reloj += max(1, int(R.expovariate(1 / (6 if len(ins) < 300 else 40))))
        h, m, s = reloj // 3600, reloj % 3600 // 60, reloj % 60
        dom = R.choice(DOMINIOS)
        primer = ape.split()[0]
        ins.append({'codigo': 'CIIC-7K4Q2' if doc == '78695681' else 'CIIC-P3MXA' if doc == '68133993' else nuevo_codigo(), 'documento': doc,
                    'nombres': nom, 'apellidos': ape, 'correo': sin_tilde(nom.split()[0]) + '.' + sin_tilde(primer) + str(R.randint(1, 99)) + '@' + dom,
                    'etapa': p['etapa'], 'celular': cel, 'pais': 'CL' if cel.startswith('+56') else 'PE', 'aceptaPrivacidad': True, 'aceptaWhatsapp': True,
                    'avisoVersion': 1, 'estado': estado, 'origen': 'PANEL' if R.random() < 0.05 else 'WEB', 'ronda': 1, 'registradoPor': None,
                    'creado': '2026-11-10 %02d:%02d:%02d' % (min(h, 23), m, s), 'acts': sel,
                    'enGrupo': {i: True for i in sel if R.random() < 0.5}})
    for i in ins:
        if i['origen'] == 'PANEL':
            i['registradoPor'] = 'u-ana'
    return ins


def bitacora(ins):
    b = [('2026-11-09 18:20:11', 'Tú (propietario) · propietario', 'Importar padrón', '3200 agregados · 0 ya existían · 0 conflictos · 0 inválidos'),
         ('2026-11-09 18:31:40', 'Tú (propietario) · propietario', 'Importar actividades', '28 agregadas (2 ocultas)'),
         ('2026-11-09 19:02:05', 'Tú (propietario) · propietario', 'Respaldo', 'descargado · 410 KB'),
         ('2026-11-10 07:58:30', 'Tú (propietario) · propietario', 'Configuración', 'etapas · etapas con visitas'),
         ('2026-11-10 08:00:00', 'Tú (propietario) · propietario', 'Apertura', 'ronda 1'),
         ('2026-11-10 08:41:12', 'Ana Rojas · admin', 'Actividad VIS04', 'cupo o visibilidad'),
         ('2026-11-10 09:15:47', 'Luis Paz · operador', 'Grupo VIS01', '9 marcados en el grupo'),
         ('2026-11-10 10:02:09', 'Ana Rojas · admin', 'Padrón', 'agregado 71234500 a la Etapa 1'),
         ('2026-11-10 11:20:33', 'Ana Rojas · admin', 'Cambio de inscripción', ins[5]['codigo']),
         ('2026-11-10 12:00:00', 'Tú (propietario) · propietario', 'Respaldo', 'descargado · 455 KB'),
         ('2026-11-10 13:44:51', 'Luis Paz · operador', 'Exportación', 'CSV · actividad VIS08 · etapa todas · 15 filas')]
    for x in ins:
        if x['estado'] == 'ANULADO':
            b.append((x['creado'], 'Ana Rojas · admin', 'Anulación', x['codigo'] + ' · ' + x['documento'] + ' · libera ' + ' y '.join(x['acts'])))
    b.sort()
    return [{'fecha': f, 'quien': q, 'accion': a, 'detalle': d, 'antes': None, 'despues': None} for f, q, a, d in reversed(b)]


def q(v):
    return 'null' if v is None else "'" + str(v).replace("'", "''") + "'"


def sql_v51(pad, acts, ins):
    cfg = ("update public.config set abierto = true, etapas = '{1,2}', etapas_visita = '{1}', dos_talleres = true, mismo_dia = false, margen_min = 30, "
           "modo = 'PRUEBA', refresco = 20 where id = 1;")
    s = ['-- Base ficticia de prueba (padrón y actividades, sin inscripciones). Generado por local/generar_datos.py · esquema v51.',
         '-- Todo es inventado. Se reemplaza por los datos reales desde el panel: Sistema → Vaciar datos de prueba → Importar.', 'begin;',
         "set local ciic.masivo = 'confirmado';   -- permiso para la protección masiva (R-40), cuando exista",
         cfg, 'delete from public.inscripciones;', 'delete from public.cruces_permitidos;', 'delete from public.actividades;', 'delete from public.padron;']
    filas = ['(%s, %d, %s, %s)' % (q(p['documento']), p['etapa'], q((p['datos'] or {}).get('caso', '')), q((p['datos'] or {}).get('fecha_compra'))) for p in pad]
    for i in range(0, len(filas), 500):
        s.append('insert into public.padron (documento, etapa, nombre, fecha_compra) values\n  ' + ',\n  '.join(filas[i:i + 500]) + ';')
    s.append('insert into public.actividades (id, tipo, nombre, lugar, fecha, inicio, fin, cupo, cupo_inicial, publicada, descripcion, grupo_modo, grupo_whatsapp) values\n  ' +
             ',\n  '.join("(%s, %s, %s, %s, to_date(%s, 'DD/MM/YYYY'), %s, %s, %d, %d, %s, %s, %s, %s)" % (
                 q(a['id']), q(a['tipo']), q(a['nombre']), q(a['lugar']), q(a['fecha']), q(a['inicio']), q(a['fin']), a['cupo'], a['cupo'],
                 'true' if a['publicada'] else 'false', q(a['descripcion']), q(a['grupoModo']), q(a['grupo'])) for a in acts) + ';')
    s += ['select privado.recalcular_inscritos();', 'commit;']
    i_sql = ['-- Inscripciones ficticias para explorar el panel (opcional; después de datos_prueba.sql). Esquema v51.', 'begin;',
             "set local ciic.masivo = 'confirmado';"]
    filas = ["(%s, %s, %s, %s, %d, %s, %s, true, %s, %s, 1, (%s::timestamp at time zone 'America/Lima'))" % (
        q(x['codigo']), q(x['documento']), q(x['nombres'] + ' ' + x['apellidos']), q(x['correo']), x['etapa'], q(x['celular']), q(x['pais']),
        q(x['estado']), q(x['origen']), q(x['creado'])) for x in ins]
    i_sql.append('insert into public.inscripciones (codigo, documento, nombre, correo, etapa, celular, pais, acepta_whatsapp, estado, origen, ronda, creado_en) values\n  ' + ',\n  '.join(filas) + ';')
    nombre = {a['id']: a['nombre'] for a in acts}
    filas = ['(%s, %s, %s)' % (q(x['codigo']), q(i), q(nombre[i])) for x in ins for i in x['acts']]
    i_sql.append('insert into public.inscripcion_actividades (codigo, actividad_id, actividad_nombre) values\n  ' + ',\n  '.join(filas) + ';')
    i_sql += ['select privado.recalcular_inscritos();', 'commit;']
    return '\n'.join(s) + '\n', '\n'.join(i_sql) + '\n'


def sql_v55(pad, acts, ins):
    cfg = ("update public.config set abierto = true, etapas = '{1,2}', etapas_visita = '{1}', dos_talleres = true, mismo_dia = false, margen_min = 30, "
           "modo = 'PRUEBA', refresco = 20 where id = 1;")
    s = ['-- Base ficticia de prueba (padrón y actividades, sin inscripciones). Generado por local/generar_datos.py · esquema v5.5.',
         '-- Todo es inventado. Se reemplaza por los datos reales desde el panel: Sistema → Vaciar datos de prueba → Importar.', 'begin;',
         "set local ciic.masivo = 'confirmado';   -- la carga reemplaza tablas enteras (R-40)",
         cfg, 'delete from public.inscripciones;', 'delete from public.cruces_permitidos;', 'delete from public.actividades;', 'delete from public.padron;']
    filas = ['(%s, %d, %s, %s)' % (q(p['documento']), p['etapa'], q(json.dumps(p['datos'], ensure_ascii=False)) + '::jsonb' if p['datos'] else 'null', q(p['origen'])) for p in pad]
    for i in range(0, len(filas), 500):
        s.append('insert into public.padron (documento, etapa, datos, origen) values\n  ' + ',\n  '.join(filas[i:i + 500]) + ';')
    s.append('insert into public.actividades (id, tipo, nombre, lugar, fecha, inicio, fin, cupo, cupo_inicial, publicada, descripcion, grupo_modo, grupo_whatsapp) values\n  ' +
             ',\n  '.join("(%s, %s, %s, %s, to_date(%s, 'DD/MM/YYYY'), %s, %s, %d, %d, %s, %s, %s, %s)" % (
                 q(a['id']), q(a['tipo']), q(a['nombre']), q(a['lugar']), q(a['fecha']), q(a['inicio']), q(a['fin']), a['cupo'], a['cupo'],
                 'true' if a['publicada'] else 'false', q(a['descripcion']), q(a['grupoModo']), q(a['grupo'])) for a in acts) + ';')
    s += ["insert into public.cruces_permitidos (a, b) values ('TAL06', 'VIS05');", 'select privado.recalcular_inscritos();', 'commit;']
    i_sql = ['-- Inscripciones ficticias para explorar el panel (opcional; después de datos_prueba.sql). Esquema v5.5.',
             '-- Los contadores los mueven los disparadores (R-33).', 'begin;', "set local ciic.masivo = 'confirmado';"]
    filas = ["(%s, %s, %s, %s, %s, %d, %s, %s, true, true, 1, %s, %s, 1, (%s::timestamp at time zone 'America/Lima'))" % (
        q(x['codigo']), q(x['documento']), q(x['nombres']), q(x['apellidos']), q(x['correo']), x['etapa'], q(x['celular']), q(x['pais']),
        q(x['estado']), q(x['origen']), q(x['creado'])) for x in ins]
    i_sql.append('insert into public.inscripciones (codigo, documento, nombres, apellidos, correo, etapa, celular, pais, acepta_whatsapp, acepta_privacidad, '
                 'aviso_version, estado, origen, ronda, creado_en) values\n  ' + ',\n  '.join(filas) + ';')
    nombre = {a['id']: a['nombre'] for a in acts}
    filas = ['(%s, %s, %s, %s)' % (q(x['codigo']), q(i), q(nombre[i]), 'true' if x['enGrupo'].get(i) else 'false') for x in ins for i in x['acts']]
    i_sql.append('insert into public.inscripcion_actividades (codigo, actividad_id, actividad_nombre, en_grupo) values\n  ' + ',\n  '.join(filas) + ';')
    i_sql += ['select privado.recalcular_inscritos();', 'commit;']
    return '\n'.join(s) + '\n', '\n'.join(i_sql) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--esquema', default='v55', choices=['v51', 'v55'])
    a = ap.parse_args()
    acts = [{'id': i, 'tipo': t, 'nombre': n, 'lugar': l, 'fecha': f, 'inicio': h1, 'fin': h2, 'cupo': c, 'cupoInicial': c, 'inscritos': 0, 'publicada': pub,
             'descripcion': d, 'grupoModo': m, 'grupo': ('https://chat.whatsapp.com/PRUEBA' + i + 'x' + ''.join(R.choice('abcdefghjkmnpqrstuvwxyz23456789') for _ in range(14))) if e else ''}
            for i, t, n, l, f, h1, h2, c, pub, d, m, e in ACTS]
    pad = padron()
    ins = inscripciones(pad, acts)
    for x in acts:
        n = sum(1 for i in ins if i['estado'] == 'CONFIRMADO' and x['id'] in i['acts'])
        assert n <= x['cupo'], (x['id'], n, x['cupo'])
    estado = {
        'cfg': {'abierto': True, 'ronda': 1, 'cierreEn': None, 'etapas': [1, 2], 'etapasVisita': [1], 'dosTalleres': True, 'mismoDia': False, 'margenMin': 30,
                'pasoCupo': 5, 'refresco': 20, 'modo': 'PRUEBA', 'limiteDispositivo': 4, 'limiteRed': 300, 'ventanaMin': 10, 'umbral': 2000, 'limiteMasivo': 10, 'avisoVersion': 1},
        'tipos': {'VISITA': {'nombre': 'Visita técnica', 'max': 1}, 'TALLER': {'nombre': 'Taller', 'max': 2}},
        'acts': acts, 'cruces': ['TAL06|VIS05'], 'padron': pad, 'ins': ins,
        'equipo': [{'id': 'u-tu', 'correo': 'tu@ciic.pe', 'nombre': 'Tú (propietario)', 'rol': 'propietario', 'activo': True, 'totp': True},
                   {'id': 'u-ana', 'correo': 'ana.rojas@ciic.pe', 'nombre': 'Ana Rojas', 'rol': 'admin', 'activo': True, 'totp': True},
                   {'id': 'u-luis', 'correo': 'luis.paz@ciic.pe', 'nombre': 'Luis Paz', 'rol': 'operador', 'activo': True, 'totp': True},
                   {'id': 'u-rosa', 'correo': 'rosa.vilchez@ciic.pe', 'nombre': 'Rosa Vílchez', 'rol': 'operador', 'activo': True, 'totp': True},
                   {'id': 'u-carla', 'correo': 'carla.diaz@ciic.pe', 'nombre': 'Carla Díaz', 'rol': None, 'activo': True, 'totp': False},
                   {'id': 'u-marco', 'correo': 'marco.salas@ciic.pe', 'nombre': 'Marco Salas', 'rol': 'operador', 'activo': False, 'totp': True}],
        'bit': bitacora(ins)}
    docs = [{'doc': d, 'etapa': e, 'caso': c} for d, e, c in CINTA]
    js = ('/* Base ficticia del modo demo · contrato v5.5 · todo es inventado.\n   Generado por local/generar_datos.py (no editar a mano). */\n'
          'window.CIIC_DATOS_DEMO = ' + json.dumps({'estado': estado, 'documentosDePrueba': docs}, ensure_ascii=False, separators=(',', ':')) + ';\n')
    escribir(RAIZ / 'docs/demo/datos-demo.js', js)
    sql, isql = (sql_v55 if a.esquema == 'v55' else sql_v51)(pad, acts, ins)
    escribir(RAIZ / 'local/datos_prueba.sql', sql)
    escribir(RAIZ / 'local/inscripciones_prueba.sql', isql)
    escribir(RAIZ / 'local/padron_prueba.csv', 'documento;etapa\n' + ''.join('%s;%d\n' % (p['documento'], p['etapa']) for p in pad if p['origen'] == 'CARGA'))
    nuevos = ['%d;%d' % (80_000_000 + k * 7, 1 + k % 3) for k in range(200)]
    dificiles = ['8.000.007;Etapa 2', '4999999;1', '04567812;3', 'AB-123456;2', 'hola;1', '  80 123 999 ; 3 ', '80000000;1']
    escribir(RAIZ / 'local/padron_importar_ejemplo.csv', '\ufeffDNI;Etapa\n' + '\n'.join(nuevos + dificiles) + '\n')
    enc = 'id;tipo;nombre;lugar;fecha;inicio;fin;cupo;descripcion;entrega;enlace;visible\n'
    escribir(RAIZ / 'local/actividades_prueba.csv', enc + ''.join(
        '%s;%s;%s;%s;%s;%s;%s;%d;%s;%s;%s;%s\n' % (x['id'], x['tipo'], x['nombre'], x['lugar'], x['fecha'], x['inicio'], x['fin'], x['cupo'],
                                                  x['descripcion'].replace(';', ','), x['grupoModo'], x['grupo'], 'SI' if x['publicada'] else 'NO') for x in acts))
    conf = [i for i in ins if i['estado'] == 'CONFIRMADO']
    print('Padrón: %d (E1 %d · E2 %d · E3 %d) · Actividades: %d · Inscripciones: %d confirmadas + %d anuladas · datos-demo.js: %d KB' % (
        len(pad), *(sum(1 for p in pad if p['etapa'] == e) for e in (1, 2, 3)), len(acts), len(conf), len(ins) - len(conf), len(js) // 1024))
    llenas = [x['id'] for x in acts if sum(1 for i in conf if x['id'] in i['acts']) >= x['cupo']]
    print('Actividades llenas:', ', '.join(llenas) or 'ninguna')


if __name__ == '__main__':
    main()
