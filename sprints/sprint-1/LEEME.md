# Sprint 1 · Seguridad · contrato v5.5

Probado en el entorno de diseño sobre una base limpia con la base ficticia (PostgreSQL 16): **235 de 235** pruebas, en cuatro corridas seguidas, con 1 omitida (navegador, que vuelve en el Sprint 2). La migración se aplicó dos veces seguidas sin error y también sobre una base con las 720 inscripciones ficticias.

## Qué trae

| # | Tarea | Dónde | Cómo se prueba |
|---|---|---|---|
| 1.1 | **Sin comprobantes**: `duplicado` público solo con el aviso; `registrado` sin código y con el celular. En el panel, `duplicado` sí trae el código | `03` · `privado.duplicado`, `duplicado_panel`, `confirmacion`, `registrar`, `panel_inscribir` | Bloque S |
| 1.2 | **Incidencias**: el error interno guarda el detalle en `privado.incidencias`; la persona ve `INC-0001`; `panel_incidencias` (nivel 2); `admin_error` para probarlo | `03` · `api()` | Bloque X |
| 1.3 | **IP real**: `privado.red()` según `config.ip_cabecera` (`auto` por ahora); `admin_cabeceras` para el Sprint 3 | `03` · `privado.red`, `admin_cabeceras`; servidor local | Bloque R · IP |
| 1.4 | **Producción sin clave**: al pasar a PRODUCCION se borra la clave del tester | `03` · disparador `produccion_sin_clave` | Bloque Z |
| 1.5 | **Propietario único**: índice único; el panel no asigna ni modifica al propietario; `privado.asignar_propietario(correo)` y `privado.cambiar_propietario(correo)` para el SQL Editor | `03` | Bloques O y Z |
| 1.6 | **Niveles de rol**: `privado.nivel(acción, datos)`; `panel_config` por campo; `sin_permiso` con `nivel`. Las acciones de los sprints siguientes ya tienen su nivel | `03` · `api()` | Bloque AB: 29 acciones × 3 roles + 7 casos de `panel_config` |
| 1.7 | **Bitácora con antes y después** en configuración, actividades, horarios y equipo | `03` · columnas `antes`, `despues` | Bloque AG |
| 1.8 | **Protección masiva**: 18 disparadores (6 tablas × UPDATE, DELETE, TRUNCATE); `config.limite_masivo` | `03` | Bloque AD |
| 1.9 | **Integridad del script**: supabase-js 2.45.4 desde su archivo real (`dist/umd/supabase.js`) con hash SRI verificado en jsDelivr y unpkg | `docs/config.js`, `docs/panel.html` | Probado en Chrome: con el hash correcto carga; alterado, el navegador lo bloquea |
| 1.10 | **Tester**: bloques S, X, AB, R, Z, AD y AG; pruebas viejas ajustadas al contrato (el código se obtiene del panel) | `tester/tester.py` | — |
| extra | **Lentitud en Windows**: el servidor local enviaba cabeceras y cuerpo en dos paquetes y cada llamada esperaba el ACK retrasado del sistema (~40 ms en Linux, hasta ~200 ms en Windows). Corregido con TCP_NODELAY: 44 ms → 1,6 ms por llamada. Además abre las conexiones al arrancar y no espera el disco al confirmar (solo en local) | `local/servidor_local.py`, `local/medir_local.py` | `medir_local.py` |

También se actualizan `supabase/excel_a_sql.py` (la carga declara el permiso masivo), la documentación (§8, §12.3, §15, §16, §19.6), `CLAUDE.md`, `sprints/PLAN.md` y la skill `ciic-desarrollo`.

## Cómo aplicarlo y probarlo

```bash
# 1. Copiar los archivos a su lugar (guarda los anteriores y rearma las demos)
python sprints/sprint-1/aplicar.py

# 2. Base desde cero (el bucle de la skill ya incluye supabase/03_*.sql)
dropdb --if-exists ciic && createdb ciic
for f in local/supabase_local.sql supabase/01_esquema.sql supabase/02_api.sql supabase/0[3-9]_*.sql local/datos_prueba.sql; do
  psql -d ciic -v ON_ERROR_STOP=1 -q -f "$f" || { echo "FALLÓ $f"; break; }
done
CLAVE=$(psql -d ciic -tAc "select privado.crear_clave_admin();")

# 3. Reiniciar el servidor local (cambió) y medir
python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787 > srv.log 2>&1 &
python local/medir_local.py --dsn "dbname=ciic" --api http://127.0.0.1:8787

# 4. Tester completo, SIN --web (el navegador vuelve en el Sprint 2)
python tester/tester.py --api http://127.0.0.1:8787 --anon local --key "$CLAVE" --local --dsn "dbname=ciic" --personas 150 --salida resultados
```

`--local --dsn` son necesarios: los bloques R, Z, AD y AG revisan la base directamente. Sin ellos esas pruebas se omiten.

## Qué esperar

| Medida | Entorno de diseño (Linux) | En tu Windows |
|---|---|---|
| Instalación | Sin errores; `select privado.version()` → `5.5-s1` | Igual |
| Tester | 235 de 235, 1 omitida (navegador) | Igual. Si alguna falla, va al reporte |
| Duración del tester | 11 a 17 s | Debería bajar mucho frente a los 31 s de la línea base |
| p95 de la carga (150) | 3,9 a 4,6 s | Debería bajar mucho frente a 19,9 s. Si no baja, el reporte lleva la salida de `medir_local.py` |
| `medir_local.py` · API 50 seguidas | 1,6 ms | Unos pocos ms. Si da 40 ms o más, el servidor que corre es el viejo: reinícialo |

## Cambios de comportamiento que hay que saber

- **La respuesta pública ya no trae el código de inscripción.** La página v5.5 ya no lo usa. El equipo lo ve en el panel.
- **`delta` en `panel_actividad` sigue aceptándose** hasta el Sprint 2 (D4), porque el tester viejo lo usa.
- **La estrategia de IP es `auto`** hasta que el Sprint 3 la confirme en Supabase con `admin_cabeceras`. No se toma el último valor de `x-forwarded-for` sin confirmarlo: si fuera un proxy interno, juntaría a todos en una sola red y el límite por red los bloquearía a todos.
- **El propietario ya no se asigna con un `insert`**: se usa `select privado.asignar_propietario('correo');` (documentación §12.3).
- **Un `DELETE` o `UPDATE` de más de 10 filas en las tablas críticas falla** con "Operación masiva bloqueada", salvo `set local ciic.masivo = 'confirmado'` en la misma transacción. Los archivos de datos ficticios y de carga ya lo declaran.

## Si algo sale mal

- `python sprints/sprint-1/aplicar.py --revertir` restaura los archivos anteriores. Luego se instala la base desde cero sin `03_sprint1_seguridad.sql`.
- No se corrige nada grande aquí: el reporte (formato de la skill `ciic-desarrollo`) va a la conversación de diseño. Incluye la salida de `medir_local.py`.
