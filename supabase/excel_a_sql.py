#!/usr/bin/env python3
"""
Convierte la hoja de la v4 (descargada como .xlsx) en un archivo SQL para Supabase · v5.1.

    pip install openpyxl
    python supabase/excel_a_sql.py MI_HOJA.xlsx local/datos_excel.sql            # config, padrón y actividades
    python supabase/excel_a_sql.py MI_HOJA.xlsx local/datos_excel.sql --registros # además, las inscripciones ya hechas (corte)

En Google Sheets: Archivo → Descargar → Microsoft Excel (.xlsx).
Luego abre local/datos_excel.sql, cópialo en Supabase → SQL Editor → Run. El archivo NO es una migración: instalar.py
nunca lo ejecuta (no lleva el encabezado de migración). Puede traer datos reales: .gitignore lo excluye.
Con el panel, lo normal es cargar padrón y actividades con Sistema → Importar (documentación §19.7).

Normaliza los documentos igual que la v4 (mayúsculas, sin espacios/puntos/guiones, DNI numérico
completado a 8 dígitos) para que nadie quede fuera por cómo se escribió en la hoja.
El archivo REEMPLAZA el padrón y las actividades; con --registros también reemplaza las inscripciones.
"""
import datetime as dt
import json
import re
import sys
import unicodedata

from openpyxl import load_workbook

PREFIJO_GRUPO = 'https://chat.whatsapp.com/'



def separar_nombre(t):
    """"Ana María Quispe Rojas" → ("Ana María", "Quispe Rojas"): la misma regla que la migración 04."""
    w = t.split()
    if len(w) >= 3:
        return ' '.join(w[:-2]), ' '.join(w[-2:])
    if len(w) == 2:
        return w[0], w[1]
    return (w[0] if w else ''), ''

def q(v) -> str:
    """Literal SQL seguro."""
    if v is None:
        return 'null'
    return "'" + str(v).replace("'", "''") + "'"


def clave(v) -> str:
    s = unicodedata.normalize('NFD', str(v or '').strip().lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s)


def si_no(v, defecto):
    if isinstance(v, bool):
        return v
    s = clave(v)
    if s in ('si', 'true', 'verdadero', '1', 'x', 'abierto', 'abiertas'):
        return True
    if s in ('no', 'false', 'falso', '0', 'cerrado', 'cerradas'):
        return False
    return defecto


def normalizar_doc(v) -> str:
    if isinstance(v, float) or isinstance(v, int):
        v = str(round(v))
    s = re.sub(r'[\s.\-]', '', str(v or '').upper())
    if re.fullmatch(r'\d+', s) and len(s) < 8:
        s = s.rjust(8, '0')
    return s


def es_documento(s: str) -> bool:
    return bool(re.fullmatch(r'[A-Z0-9]{6,12}', s) and re.search(r'\d', s))


def fecha_txt(v) -> str:
    if isinstance(v, (dt.datetime, dt.date)):
        return v.strftime('%d/%m/%Y')
    return str(v or '').strip()


def hora_txt(v) -> str:
    if isinstance(v, (dt.datetime, dt.time)):
        return v.strftime('%H:%M')
    s = str(v or '').strip()
    m = re.fullmatch(r'(\d{1,2}):(\d{2})(?::\d{2})?', s)
    return f'{int(m.group(1)):02d}:{m.group(2)}' if m else s


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    origen, destino = sys.argv[1], sys.argv[2]
    con_registros = '--registros' in sys.argv
    wb = load_workbook(origen, data_only=True, read_only=True)
    sql = ['-- Generado por excel_a_sql.py desde ' + origen + ' · NO ES UNA MIGRACIÓN: instalar.py no lo ejecuta', 'begin;', "set local ciic.masivo = 'confirmado';   -- la carga reemplaza tablas enteras (R-40)"]
    avisos = []

    # Config
    if 'Config' in wb.sheetnames:
        val = {}
        for f in wb['Config'].iter_rows(values_only=True):
            if f and f[0] is not None and clave(f[0]) not in val:
                val[clave(f[0])] = f[1] if len(f) > 1 else None
        etapas = [n for n in (1, 2, 3) if si_no(val.get(f'etapa {n} habilitada'), False)]
        try:
            refresco = int(val.get('refresco de cupos (segundos)') or 20)
        except (TypeError, ValueError):
            refresco = 20
        refresco = min(120, max(10, refresco))
        modo = 'PRUEBA' if clave(val.get('modo')) == 'prueba' else 'PRODUCCION'
        sql.append(
            # v5.1: las visitas quedan solo para la Etapa 1 (decisión tomada); se amplían desde el Panel 1.
            "update public.config set abierto = {}, etapas = '{{{}}}', etapas_visita = '{{1}}', dos_talleres = {}, modo = {}, refresco = {} where id = 1;".format(
                str(si_no(val.get('inscripciones abiertas'), False)).lower(), ','.join(map(str, etapas)),
                str(si_no(val.get('permitir 2 talleres aunque queden visitas'), True)).lower(), q(modo), refresco))

    # Padrón (v5.5): una sola etapa por documento (D2); nombre y fecha de compra van a "datos"
    sql.append('delete from public.padron;')
    total = 0
    ya_en = {}
    for n in (1, 2, 3):
        hoja = f'DNI_Etapa{n}'
        if hoja not in wb.sheetnames:
            avisos.append(f'No está la pestaña {hoja}.')
            continue
        vistos = set()
        filas = []
        for f in wb[hoja].iter_rows(values_only=True):
            if not f or f[0] is None:
                continue
            d = normalizar_doc(f[0])
            if not es_documento(d) or d in vistos:
                continue
            vistos.add(d)
            if d in ya_en:
                avisos.append(f'{d} está en las etapas {ya_en[d]} y {n}: queda en la Etapa {ya_en[d]} (D2: una sola etapa).')
                continue
            ya_en[d] = n
            nombre = str((f[1] if len(f) > 1 else None) or '').strip()
            compra = fecha_txt(f[2]) if len(f) > 2 and f[2] is not None else None
            datos = {k: v for k, v in (('nombre', nombre), ('fecha_compra', compra)) if v}
            filas.append(f"({q(d)}, {n}, {q(json.dumps(datos, ensure_ascii=False)) + '::jsonb' if datos else 'null'})")
        total += len(filas)
        for i in range(0, len(filas), 500):
            sql.append('insert into public.padron (documento, etapa, datos) values\n  ' + ',\n  '.join(filas[i:i + 500]) + ';')
    print(f'Padrón: {total} documentos')

    # Actividades
    acts = []
    if 'Actividades' in wb.sheetnames:
        for f in wb['Actividades'].iter_rows(values_only=True):
            f = list(f) + [None] * 14   # M: descripción (opcional) · N: entrega del grupo, ENLACE o MANUAL (opcional)
            ident = str(f[0] or '').strip()
            cupo = str(f[7] if f[7] is not None else '').strip()
            if not ident or not re.fullmatch(r'\d+(\.0)?', cupo):
                continue
            grupo = str(f[11] or '').strip()
            acts.append('({}, {}, {}, {}, to_date({}, \'DD/MM/YYYY\'), {}, {}, {}, {}, {}, {}, {}, {})'.format(
                q(ident), q('VISITA' if 'visita' in clave(f[1]) else 'TALLER'), q(str(f[2] or '').strip()),
                q(str(f[3] or '').strip()), q(fecha_txt(f[4])), q(hora_txt(f[5])), q(hora_txt(f[6])),
                int(float(cupo)), int(float(cupo)), str(si_no(f[8], True)).lower(), q(grupo if grupo.startswith(PREFIJO_GRUPO) else ''),
                q(str(f[12] or '').strip()[:400]), q('MANUAL' if clave(f[13]) in ('manual', 'a mano') else 'ENLACE')))
    sql.append('delete from public.inscripciones;' if con_registros else '-- (inscripciones sin tocar)')
    sql.append('delete from public.actividades;')
    if acts:
        sql.append('insert into public.actividades (id, tipo, nombre, lugar, fecha, inicio, fin, cupo, cupo_inicial, publicada, grupo_whatsapp, descripcion, grupo_modo) values\n  '
                   + ',\n  '.join(acts) + ';')
    print(f'Actividades: {len(acts)}')

    # Inscripciones (solo en el corte desde la v4): una fila por persona + una por actividad.
    if con_registros and 'Registros' in wb.sheetnames:
        ins, acts_ins = [], []
        for f in list(wb['Registros'].iter_rows(values_only=True))[1:]:
            f = list(f) + [None] * 15
            if not f[1]:
                continue
            fecha = f[0]
            if isinstance(fecha, dt.datetime):
                fecha = fecha.strftime('%Y-%m-%d %H:%M:%S')
            fecha = str(fecha or '').strip() or None
            cod = str(f[1]).strip()
            nombres, apellidos = separar_nombre(str(f[3] or ''))
            ins.append('({}, {}, {}, {}, {}, {}, {}, {}, {}, true, {}, \'WEB\', 1)'.format(
                q(cod), f"({q(fecha)}::timestamp at time zone 'America/Lima')" if fecha else 'now()',
                q(normalizar_doc(f[2])), q(nombres), q(apellidos), q(str(f[4] or '').strip().lower()),
                int(float(f[5] or 0)) or 1, q(str(f[12] or '').strip()), q(str(f[13] or 'PE').strip()),
                q('CONFIRMADO' if str(f[11] or '').strip().upper() == 'CONFIRMADO' else 'ANULADO')))
            for k in (6, 8):
                if f[k]:
                    acts_ins.append(f'({q(cod)}, {q(str(f[k]).strip())}, {q(str(f[k + 1] or f[k]).strip())})')
        for i in range(0, len(ins), 500):
            sql.append('insert into public.inscripciones (codigo, creado_en, documento, nombres, apellidos, correo, etapa, celular, pais, acepta_whatsapp, estado, origen, ronda) values\n  '
                       + ',\n  '.join(ins[i:i + 500]) + ';')
        for i in range(0, len(acts_ins), 500):
            sql.append('insert into public.inscripcion_actividades (codigo, actividad_id, actividad_nombre) values\n  ' + ',\n  '.join(acts_ins[i:i + 500]) + ';')
        print(f'Inscripciones: {len(ins)}')

    sql.append('select privado.recalcular_inscritos();')
    sql.append('commit;')
    with open(destino, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(sql) + '\n')
    for a in avisos:
        print('⚠️ ', a)
    print(f'Listo: {destino}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
