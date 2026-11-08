---
name: ciic-desarrollo
description: Procedimiento para ejecutar un sprint del sistema de inscripciones CIIC 2026 (contrato v5.5) en Claude Code con el mínimo de tokens. Úsala cuando se pida aplicar, compilar, instalar, probar o validar un sprint ("aplica el sprint 1", "corre el tester", "instala la migración 03", "prueba las páginas", "¿pasó todo?"), cuando lleguen archivos nuevos a sprints/sprint-N/, o cuando haya que reportar resultados de pruebas para llevarlos a la conversación de diseño.
---

# Ejecutar un sprint del CIIC 2026

El código pesado se escribe en otra conversación (la de diseño) y llega listo en `sprints/sprint-N/`. Aquí se **aplica, prueba y reporta**. Cada token cuenta: lee lo justo, no reescribas archivos grandes y no rediseñes.

## Antes de empezar (Windows, Git Bash) [Sprint 6]

La PC del propietario es Windows y Claude Code usa Git Bash. **Una vez por terminal:**

```bash
export PGHOST=localhost PGUSER=postgres PGCLIENTENCODING=UTF8 PYTHONUTF8=1
mkdir -p resultados
set -a; . ./.env.local; set +a        # secretos, sin mostrarlos (ver "Secretos")
```

| Variable | Por qué |
|---|---|
| `PGHOST`, `PGUSER` | `psql`, `createdb` y `dropdb` de Windows no usan el socket de Linux. Los valores de esta PC están en `local-privado/TRASPASO.md`. La contraseña de PostgreSQL local va en `pgpass.conf`, nunca en un comando |
| `PGCLIENTENCODING=UTF8` | Sin ella, `psql` de Windows usa WIN1252, y las tildes y la ñ de las migraciones fallan o se ven mal |
| `PYTHONUTF8=1` | Sin ella, Python de Windows escribe en cp1252, y los ✔, ✘ y emojis del tester dan `UnicodeEncodeError` |

- Rutas: todo lo que generan las pruebas va en `resultados/`, que está en `.gitignore`. No uses `/tmp`: Git Bash lo traduce distinto para Python y para `psql`.
- En Windows, el comando es `python`, no `python3`.
- **Bitácora:** cada paso (comando, resultado en una línea, hora) va en la bitácora de `local-privado/INCIDENCIAS.md`. Las entradas de la bitácora no se numeran: el reporte las cita por fecha y hora. Las incidencias sí van con su número (#40, #41…). `local-privado/` no se sube a GitHub: compruébalo con `git check-ignore -v local-privado/INCIDENCIAS.md`.

## Procedimiento

1. **Leer la tarea, no todo el proyecto.** Abre `sprints/PLAN.md` solo en la sección del sprint (`grep -n "^## Sprint" sprints/PLAN.md` y lee ese rango) y el `LEEME.md` de `sprints/sprint-N/` si existe.
2. **Aplicar los archivos** con `python sprints/sprint-N/aplicar.py`. Copia cada archivo a su ruta final, guarda la versión anterior en `sprints/sprint-N/anteriores/` y rearma las demos. No copies a mano, ni reformatees, ni "mejores" el código recibido. Para deshacer: `python sprints/sprint-N/aplicar.py --revertir`.
3. **Base local desde cero**, siempre, para que la prueba sea limpia:
   ```bash
   dropdb --if-exists ciic && createdb ciic
   psql -d ciic -q -f local/supabase_local.sql
   python supabase/instalar.py --dsn "dbname=ciic" --datos local/datos_prueba.sql      # todas las migraciones, en una transacción
   CLAVE=$(psql -d ciic -tAc "select privado.crear_clave_admin();")
   ```
   Para probar además la puesta al día (lo que pasará en Supabase): sobre la base del sprint anterior, corre `python supabase/instalar.py --dsn "dbname=ciic" --verificar` (debe listar solo lo nuevo) y luego el mismo comando sin `--verificar`. Al final, `instalar.py` dice si la limpieza programada (pg_cron) está activa: en local no hay pg_cron, y eso es normal.
4. **Servidor y tester en local:**
   ```bash
   python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787 > resultados/srv.log 2>&1 &     # reinícialo si cambió en el sprint
   # sin pausa fija: el tester y medir_local.py esperan hasta 30 s a que el servidor responda
   python tester/tester.py --api http://127.0.0.1:8787 --anon local --key "$CLAVE" --local --dsn "dbname=ciic" \
     --web http://127.0.0.1:8787/ --personas 150 --salida resultados/local > resultados/tester.log 2>&1
   grep -E "FALLA|AVISO|OMITE|pruebas|Duración|⛔|… " resultados/tester.log
   ```
   - **El bloque W** inscribe además 1000 personas sintéticas y prueba la alerta de saturación (unos 2 minutos más). `--personas-w 0` lo salta en corridas rápidas, nunca en la de aceptación.
   - **Las líneas "… "** traen las mediciones (p50 y p95) que van al reporte. Si hubo reintentos, el final del registro dice la causa del primero de cada tipo.
   - **Solo las fallas:** `grep -A2 "FALLA" resultados/tester.log`. No pegues el registro completo.
   - **Enmascarado:** el tester enmascara documentos, nombres, correos, celulares, códigos e IP en lo que imprime y guarda. Solo para depurar en local: `--sin-mascara`.
   - **Navegador:** desde el Sprint 2 va siempre (`--web`). Requiere `pip install playwright` y `python -m playwright install chromium`.
5. **Contra PRUEBA, desde la PC:**
   ```bash
   python tester/tester.py --api <URL de PRUEBA> --anon <ANON_KEY de PRUEBA> --key "$ADMIN_KEY" --dsn "$DSN_PRUEBA" \
     --web https://abidancopa2-netizen.github.io/inscripciones-ciic-2026/ --personas-w 300 --salida resultados/prueba > resultados/tester-prueba.log 2>&1
   ```
   - **Siempre `--personas-w 300` desde la PC** (Sprint 5.1). Con 300 conexiones a la vez, la PC y su red dan 0 errores; con 1000, lo que se mide es la PC.
   - **La referencia de W con 1000** es el tester de GitHub: Actions → "Tester del sistema" (completo, 150, W 1000).
   - **AVISO:** si una carga falla solo por conexión (`SSLEOFError`, `OSError 24`) y la base no dio ningún error, T, W y AE salen como AVISO. Anota cuántos hubo.
   - **Desde el Sprint 6,** si `docs/config.js` ya apunta a PRODUCCIÓN, el tester completo exige `--api` y `--anon` de PRUEBA.
6. **Otras pruebas [Sprint 6]:**
   - **Página publicada, sin cambiar nada:** `python tester/tester.py --modo lectura --api <URL> --anon <ANON_KEY> --web <página publicada>`. Sirve en PRODUCCIÓN.
   - **Prueba de ataque, solo contra PRUEBA y con PRUEBA abierta:** `python tester/ataque.py --api <URL de PRUEBA> --anon <ANON_KEY de PRUEBA> --key "$ADMIN_KEY" --web <página publicada>`. Deja el resultado en `resultados/ataque/ataque.md`; al reporte va su resumen.
7. **Si algo falla:**
   - **Error de instalación SQL:** copia solo el mensaje de `psql` (archivo, línea, error).
   - **Prueba que falla:** el nombre, lo esperado, lo obtenido y el detalle (3 líneas por falla).
   - **Arreglos:** si la causa es evidente y el arreglo es pequeño (hasta unas 20 líneas, sin cambiar el contrato), corrígelo, vuelve a correr y anótalo. Si no, **no adivines**: reporta.
8. **Datos ficticios.** Llegan regenerados con cada sprint que cambia el esquema. Si hiciera falta: `python local/generar_datos.py` (esquema v5.5 por defecto) y vuelve al paso 3. Nunca edites a mano `datos_prueba.sql`, `inscripciones_prueba.sql` ni `datos-demo.js`.
9. **Comparar con la referencia** cuando haya dudas sobre una respuesta. El comportamiento correcto está en `docs/demo/demo-api.js` (busca la acción con `grep -n "case 'panel_x'"`). La base debe responder lo mismo: tipo, campos y mensajes equivalentes.
10. **Reportar** con el formato de abajo, y nada más.

## Formato del reporte

```
SPRINT N · <fecha>
Instalación: OK | FALLÓ <archivo:línea · error> · limpieza programada: activa | sin pg_cron
Tester local: <pasan>/<total> · omitidas <n> · <duración>
Tester PC (PRUEBA, W 300): <pasan>/<total> · avisos <n> · p95 carga <s> · W: p50/p95 de principio a fin y al confirmar · reintentos <n> (causa)
Tester GitHub: <pasan>/<total> · <enlace a la corrida>
Ataque (si se corrió): resistió <n> de <m> · notas <k>
Huellas: config.js <12 caracteres> (si cambió)
Fallas:
  - <bloque> · <prueba> · esperado <x> · obtenido <y> · <detalle corto>
Arreglos hechos aquí:
  - <archivo> · <qué y por qué, una línea>
Bitácora: INCIDENCIAS.md, entradas del <dd/mm hh:mm>–<hh:mm> · incidencias #<n> nuevas · #<n> cerradas
Dudas para la conversación de diseño:
  - <una línea cada una>
```

Ese reporte se pega tal cual en la conversación de diseño: con eso basta para corregir. Nunca lleva datos de personas, claves, cadenas de conexión ni respaldos.

## Prueba rápida del backend de demostración (sin base)

```bash
node -e '
const fs=require("fs"),{webcrypto}=require("crypto");const m={};
global.window={addEventListener(){}};global.localStorage={getItem:k=>m[k]??null,setItem:(k,v)=>{m[k]=v}};
global.crypto=webcrypto;window.crypto=webcrypto;
eval(fs.readFileSync("docs/demo/datos-demo.js","utf8"));eval(fs.readFileSync("docs/demo/demo-api.js","utf8"));
window.CIIC_DEMO.api({action:"verificar",dni:"04567812"},{dispositivo:"d1"}).then(r=>console.log(r.tipo,r.doc,r.etapa));'
```

## Secretos (desde el Sprint 3)

Las cadenas de conexión de Supabase y la clave del tester están en `.env.local`, en la raíz. Cárgalas en la terminal **sin mostrarlas**:

```bash
set -a; . ./.env.local; set +a       # DSN_PRUEBA, DSN_PRODUCCION, REF_*, PRODUCCION_API_URL, PRODUCCION_ANON_KEY, ADMIN_KEY…
```

- **Nunca muestres su contenido** (`echo $DSN_PRUEBA`, `cat .env.local`, `env`), ni lo pegues en el reporte o en un commit.
- **Comillas simples:** `.env.local` las usa (`DSN_PRUEBA='postgresql://…'`). Con dobles, un `$` en la contraseña se expandiría al cargarlo.
- **Guardar la clave del tester:**
  `CLAVE=$(psql -d "$DSN_PRUEBA" -tAc "select privado.crear_clave_admin();") && [ -n "$CLAVE" ] && printf "\nADMIN_KEY='%s'\n" "$CLAVE" >> .env.local; unset CLAVE`.
  - El salto inicial evita pegarla a la última línea si el archivo no termina en salto (arreglo del Sprint 3).
  - La cadena va con `-d` y **al principio**: en Windows, `psql` ignora las opciones que vienen después de la cadena, y la clave quedaba vacía (arreglo del Sprint 3, Fase C).
- **Antes de usarla,** comprueba que no está vacía sin mostrarla: `[ -n "$ADMIN_KEY" ] && echo "ADMIN_KEY cargada (${#ADMIN_KEY} caracteres)"`.
- **Antes de cada commit:** `git check-ignore -v .env.local` debe responder que está ignorado.
- **`instalar.py`** aplica solo las migraciones pendientes, todas en una transacción. Para ver qué haría sin cambiar nada: `--verificar`.

## Lo que no se hace aquí

- **El contrato no se cambia** (campos, tipos de respuesta, niveles, reglas). Si algo del contrato parece incorrecto, va como duda en el reporte.
- **`docs/config.js` es del propietario:** solo cambia con el `configurar.py` de una entrega, con vista previa y su aprobación.
- **Producción:**
  - Solo cuando el propietario lo pide en esa sesión, y fuera del congelamiento: desde 24 h antes de abrir, que para la Etapa 1 es el 10/11 a las 20:00.
  - Solo con `supabase/instalar.py` (primero `--verificar`, con `--confirmar "$REF_PRODUCCION"`), con `restaurar.py --verificar`, con el tester en modo lectura o con las sentencias de una línea que documenta la guía (`ip_cabecera`, `asignar_propietario`).
  - Durante el congelamiento, solo la excepción de la doc §20.1, y con la autorización del propietario en esa sesión.
  - Nunca SQL improvisado, nunca la base ficticia ni la clave del tester, y nunca la prueba de ataque.
- **PRUEBA en Supabase:** si la limpieza del tester falla, la base queda con datos del tester. Se recarga con `datos_prueba.sql` (que reemplaza la base ficticia) y se anota en el reporte.
- **No se reescriben archivos grandes** para "ordenarlos". Si un archivo necesita reestructurarse, se pide en la conversación de diseño.
- **No se agregan dependencias nuevas** sin anotarlo en el reporte.
