# Sprint 2 · Integridad y datos · contrato v5.5

Probado en el entorno de diseño sobre una base limpia: **299 de 299, con navegador y sin omitidas**, en dos corridas seguidas. La migración 04 se aplicó dos veces seguidas sin error, y también **sobre una base v5.1 con 720 inscripciones**: separa los nombres, pasa el nombre del padrón a `datos` y deja los contadores exactos.

**Cambia el esquema**: después de aplicar hay que instalar la base desde cero. Los datos ficticios llegan ya en v5.5.

## Qué trae

| # | Tarea | Cómo se prueba |
|---|---|---|
| 2.1 | **Padrón mínimo**: clave = documento (una sola etapa, D2); nombre y fecha de compra pasan a `datos` (jsonb) | Bloques AC y N |
| 2.2 | **Inscripciones**: `nombres`, `apellidos`, `correo` obligatorio, `acepta_privacidad`, `aviso_version`. `nombre` queda como columna calculada (lo que la leía sigue funcionando) | Bloques D, AH y navegador |
| 2.3 | **Idempotencia con ámbito**: toda escritura exige `solicitud` UUID; la misma solicitud, persona y acción devuelve la misma respuesta con `repetida: true`; con otros datos, `solicitud_repetida` | Bloques U y AI |
| 2.4 | **Cupo final**: `panel_actividad` rechaza `delta` | Bloque F |
| 2.5 | **Contadores por disparador**: ninguna función suma o resta a mano; `panel_resumen.integridad`; recontar devuelve la integridad | Bloques V y T |
| 2.6 | **Listas y grupo**: `panel_lista` (orden alfabético igual en cualquier servidor) y `panel_grupo_marcar` (nivel 1) | Bloque AA y navegador |
| 2.7 | **Exportar**: `panel_exportar` (nivel 1) y `panel_registros` (nivel 2) con las columnas nuevas; cada descarga queda en la bitácora | Bloque AA |
| 2.8 | **Importar padrón** (nivel 3) con informe de agregados, existentes, conflictos e inválidos | Bloque AE |
| 2.9 | **Datos v5.5**: `generar_datos.py` (v5.5 por defecto), `datos_prueba.sql`, `inscripciones_prueba.sql` y `excel_a_sql.py` | Instalación |
| 2.10 | **Tester**: bloques T, U, V, AA, AC, AE, AH, AI, AJ, AK y navegador reescrito para las páginas v5.5 | — |
| 2.11 | **De prueba a real**: `panel_vaciar_prueba` y `panel_actividades_importar` (nivel 3) | Bloques AJ y AK; además probado en Chrome desde la pestaña Sistema: importar, vaciar y volver a cargar |
| + | Adelantados del Sprint 4: `estado` con `conActividades` (D3) y `config.aviso_version` (D6) | Navegador |

## Respuestas al reporte del Sprint 1.1

| Duda | Resuelta en |
|---|---|
| Datos personales en `reporte.md`, `resultados.json` y el resumen de GitHub | El tester **enmascara** documentos, nombres, correos, celulares y códigos en todo lo que imprime y guarda (ejemplos: `26•••72`, `+519•••660`, `m•••@uni.edu.pe`, `CIIC-•••••`). Solo para depurar en local: `--sin-mascara` |
| `sleep 2` fijo | El tester y `medir_local.py` esperan hasta 30 s a que el servidor responda; la skill ya no tiene la pausa |
| `srv.log` vacío | El servidor imprime su arranque con `flush` y salida por líneas |

## Cómo aplicarlo y probarlo

```bash
python sprints/sprint-2/aplicar.py

pip install playwright && python -m playwright install chromium     # si aún no está: el navegador va desde este sprint

dropdb --if-exists ciic && createdb ciic
for f in local/supabase_local.sql supabase/01_esquema.sql supabase/02_api.sql supabase/0[3-9]_*.sql local/datos_prueba.sql; do
  psql -d ciic -v ON_ERROR_STOP=1 -q -f "$f" || { echo "FALLÓ $f"; break; }
done
CLAVE=$(psql -d ciic -tAc "select privado.crear_clave_admin();")

python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787 > srv.log 2>&1 &
python tester/tester.py --api http://127.0.0.1:8787 --anon local --key "$CLAVE" --local --dsn "dbname=ciic" \
  --web http://127.0.0.1:8787/ --personas 150 --salida resultados
```

Opcional, para explorar el panel con datos: `psql -d ciic -f local/inscripciones_prueba.sql` **después** de correr el tester (el tester espera una base sin esas 720 inscripciones).

## Qué esperar

- `select privado.version()` → `5.5-s2`.
- Tester: **299 de 299, 0 omitidas**, unos 20 s en Linux.
- `resultados/capturas/` con las pantallas del navegador (solo en local; en GitHub se borran).
- Con el servidor local, en `MODO: 'real'`, la página y el panel funcionan igual que en modo demo.

## Cambios de comportamiento

- **Toda escritura exige `solicitud` (UUID)**: la página y el panel v5.5 ya la envían. Quien llame a la API a mano debe incluirla.
- **`delta` ya no se acepta**: se envía el cupo final.
- **El padrón tiene una sola etapa por documento.** Si una base anterior tuviera un documento en dos etapas, la migración se detiene y lo dice.
- **El nombre de la persona son dos campos** (`nombres`, `apellidos`). La migración separa los existentes: las dos últimas palabras son los apellidos.

## Si algo sale mal

`python sprints/sprint-2/aplicar.py --revertir` y reinstalar la base sin `04_sprint2_datos.sql` (y con los datos del Sprint 1, que quedan en `sprints/sprint-2/anteriores/local/`). El reporte va a la conversación de diseño con el formato de la skill.
