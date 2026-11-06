# Sprint 2.1 · corrección con lo encontrado en el reporte del Sprint 2

**Cambia `04_sprint2_datos.sql`: instalar la base desde cero.** Aún no hay proyecto real, así que la migración se reemplaza; desde el Sprint 3, toda corrección irá en una migración nueva.

Probado en el entorno de diseño: **302 de 302, con navegador, en tres colaciones** (C, ICU español de Perú, ICU inglés de EE. UU.). El tester nuevo, corrido contra el SQL anterior en colación española, **detecta los tres defectos** del reporte (orden con Ñ, CSV en ese orden, 10 000 filas → "ocupado" a los 18 s).

| Del reporte | Qué hace esta entrega |
|---|---|
| Importar padrón cuadrático (arreglo hecho aquí) | Incorporado y llevado más lejos: **por conjuntos**, sin recorrer fila por fila. 10 000 filas en 0,48 s (antes del arreglo, "ocupado"; con el bucle corregido, 2,19 s en tu Windows). Mismos resultados que antes en todos los casos |
| Orden con Ñ y tildes (arreglo hecho aquí) | Incorporado: la Ñ se traduce en `clave_orden` y el `collate "C"` va en cada `ORDER BY` |
| Máscara del documento en el nombre de la prueba (arreglo hecho aquí) | Incorporado: el nombre de la prueba ya no lleva el documento, `ok()` enmascara también el nombre, y la máscara cubre documentos con puntos o guion (`12.345.678`, `1234-5678`) sin tocar las fechas |
| Agregar pruebas para esos defectos | AA: orden en español con 7 apellidos difíciles, en la lista y en el CSV. AE: 10 000 filas en una llamada, en menos de 3 s |
| Panel: "ocupado" terminaba en "No hay conexión" | Ahora dice "El sistema está ocupado…; no se hizo dos veces" y avisa que reintenta. La importación de padrón va **en lotes de 2000 con progreso**; si un lote falla, dice cuántas filas quedaron y que reimportar el mismo archivo es seguro |
| 10 000 filas cerca de los 3 s | Por conjuntos queda en 0,5 s; además, se mide en Supabase (Sprint 3, tarea 3.7) |
| `panel_exportar` sin ORDER BY | Agregado (y en `panel_lista`) |
| `generar_datos.py` escribía CRLF en Windows | Escribe siempre LF (y `armar_demos.py` también). Además: `.gitattributes` con `eol=lf`, y `aplicar.py` compara las huellas **sin finales de línea**: un archivo convertido a CRLF ya no parece un cambio local |
| `padron_prueba.csv` 3200 vs padrón 3201 | Aclarado en §21.2: la persona 3201 es el ejemplo de alta de último momento (origen PANEL) |
| Carga con menos inscripciones completas | Antes de la carga, el tester amplía el cupo de los talleres (y `limpiar()` lo restaura): vuelve a medir unas 145 a 150 inscripciones completas |
| Reintentos sin causa | El reporte ahora dice cuáles: `Reintentos: 1 (estado: sin_conexion ×1)`. Uno de ellos era la espera inicial del arranque, que ya no se cuenta |

**`aplicar.py` más estricto:** "incorpora" ya no acepta cualquier cambio local; acepta solo las huellas exactas de tus arreglos (`a69c643e6618` para la migración, `2c6f0690a522` para el tester). Si tu archivo fuera otro, se detiene sin copiar nada.

## Cómo aplicarlo y probarlo

```bash
python sprints/sprint-2.1/aplicar.py        # 2 archivos aparecen como "incorpora" (tus arreglos): es lo esperado

dropdb --if-exists ciic && createdb ciic
for f in local/supabase_local.sql supabase/01_esquema.sql supabase/02_api.sql supabase/0[3-9]_*.sql local/datos_prueba.sql; do
  psql -d ciic -v ON_ERROR_STOP=1 -q -f "$f" || { echo "FALLÓ $f"; break; }
done
CLAVE=$(psql -d ciic -tAc "select privado.crear_clave_admin();")
python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787 > srv.log 2>&1 &
python tester/tester.py --api http://127.0.0.1:8787 --anon local --key "$CLAVE" --local --dsn "dbname=ciic" \
  --web http://127.0.0.1:8787/ --personas 150 --salida resultados
```

Si puedes, repítelo también con la base en `Spanish_Peru.1252` (como en tu reporte): el orden debe ser el mismo.

## Qué esperar

- Tester: **302 de 302, 0 omitidas**. Reintentos 0 en la mayoría de las corridas; si aparece alguno, el reporte dice de qué acción y por qué.
- El bloque AE informa el tiempo de las 10 000 filas: en tu Windows debería quedar muy por debajo de 1 s.
