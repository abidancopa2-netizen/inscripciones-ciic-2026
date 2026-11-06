---
name: ciic-desarrollo
description: Procedimiento para ejecutar un sprint del sistema de inscripciones CIIC 2026 (contrato v5.5) en Claude Code con el mínimo de tokens. Úsala cuando se pida aplicar, compilar, instalar, probar o validar un sprint ("aplica el sprint 1", "corre el tester", "instala la migración 03", "prueba las páginas", "¿pasó todo?"), cuando lleguen archivos nuevos a sprints/sprint-N/, o cuando haya que reportar resultados de pruebas para llevarlos a la conversación de diseño.
---

# Ejecutar un sprint del CIIC 2026

El código pesado se escribe en otra conversación (la de diseño) y llega listo en `sprints/sprint-N/`. Aquí se **aplica, prueba y reporta**. Cada token cuenta: lee lo justo, no reescribas archivos grandes y no rediseñes.

## Procedimiento

1. **Leer la tarea, no todo el proyecto.** Abre `sprints/PLAN.md` solo en la sección del sprint (`grep -n "^## Sprint" sprints/PLAN.md` y lee ese rango) y el `LEEME.md` de `sprints/sprint-N/` si existe.
2. **Aplicar los archivos** con `python sprints/sprint-N/aplicar.py`: copia cada archivo a su ruta final, guarda la versión anterior en `sprints/sprint-N/anteriores/` y rearma las demos. No copies a mano ni reformatees ni "mejores" el código recibido. Para deshacer: `python sprints/sprint-N/aplicar.py --revertir`.
3. **Base local desde cero**, siempre, para que la prueba sea limpia:
   ```bash
   dropdb --if-exists ciic && createdb ciic
   for f in local/supabase_local.sql supabase/01_esquema.sql supabase/02_api.sql supabase/0[3-9]_*.sql local/datos_prueba.sql; do
     [ -f "$f" ] && psql -d ciic -v ON_ERROR_STOP=1 -q -f "$f" || { echo "FALLÓ $f"; break; }
   done
   CLAVE=$(psql -d ciic -tAc "select privado.crear_clave_admin();")
   ```
4. **Servidor y tester:**
   ```bash
   python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787 > /tmp/srv.log 2>&1 &     # reinícialo si cambió en el sprint
   # sin pausa fija: el tester y medir_local.py esperan hasta 30 s a que el servidor responda
   python tester/tester.py --api http://127.0.0.1:8787 --anon local --key "$CLAVE" --local --dsn "dbname=ciic" \
     --web http://127.0.0.1:8787/ --personas 150 --salida /tmp/r > /tmp/tester.log 2>&1
   grep -E "FALLA|OMITE|pruebas|Duración|⛔" /tmp/tester.log
   ```
   Para leer solo las fallas: `grep -A2 "FALLA" /tmp/tester.log`. No pegues el registro completo.
   El tester enmascara documentos, nombres, correos, celulares y códigos en lo que imprime y guarda. Solo para depurar en local: `--sin-mascara`.
   Desde el Sprint 2 el navegador va siempre (`--web`): requiere `pip install playwright` y `python -m playwright install chromium`.
5. **Si algo falla:**
   - Error de instalación SQL: copia solo el mensaje de `psql` (archivo, línea, error).
   - Prueba que falla: el nombre, lo esperado, lo obtenido y el detalle (3 líneas por falla).
   - Si la causa es evidente y el arreglo es pequeño (hasta unas 20 líneas, sin cambiar el contrato), corrígelo, vuelve a correr y anótalo. Si no, **no adivines**: reporta.
6. **Datos ficticios.** Llegan regenerados con cada sprint que cambia el esquema. Si hiciera falta: `python local/generar_datos.py` (esquema v5.5 por defecto) y vuelve al paso 3. Nunca edites a mano `datos_prueba.sql`, `inscripciones_prueba.sql` ni `datos-demo.js`.
7. **Comparar con la referencia** cuando haya dudas sobre una respuesta: el comportamiento correcto está en `docs/demo/demo-api.js` (busca la acción con `grep -n "case 'panel_x'"`). La base debe responder lo mismo: tipo, campos y mensajes equivalentes.
8. **Reportar** con el formato de abajo, y nada más.

## Formato del reporte

```
SPRINT N · <fecha>
Instalación: OK | FALLÓ <archivo:línea · error>
Tester: <pasan>/<total> · omitidas <n> · <duración> · p95 carga <s>
Fallas:
  - <bloque> · <prueba> · esperado <x> · obtenido <y> · <detalle corto>
Arreglos hechos aquí:
  - <archivo> · <qué y por qué, una línea>
Dudas para la conversación de diseño:
  - <una línea cada una>
```

Ese reporte se pega tal cual en la conversación de diseño: con eso basta para corregir.

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
set -a; . ./.env.local; set +a       # DSN_PRUEBA, DSN_PRODUCCION, REF_*, URL_*, ANON_*, ADMIN_KEY
```

- Nunca imprimas su contenido (`echo $DSN_PRUEBA`, `cat .env.local`, `env`), ni lo pegues en el reporte o en un commit.
- `.env.local` usa **comillas simples** (`DSN_PRUEBA='postgresql://…'`): con dobles, un `$` en la contraseña se expandiría al cargarlo.
- Para guardar la clave del tester (el salto inicial evita pegarla a la última línea si el archivo no termina en salto; arreglo del Sprint 3):
  `CLAVE=$(psql -d "$DSN_PRUEBA" -tAc "select privado.crear_clave_admin();") && [ -n "$CLAVE" ] && printf "\nADMIN_KEY='%s'\n" "$CLAVE" >> .env.local; unset CLAVE`.
  La cadena va con `-d` y **al principio**: en Windows, psql ignora las opciones que vienen después de la cadena, y la clave quedaba vacía (arreglo del Sprint 3, Fase C).
- Antes de usarla, comprueba que no está vacía sin mostrarla: `[ -n "$ADMIN_KEY" ] && echo "ADMIN_KEY cargada (${#ADMIN_KEY} caracteres)"`.
- Antes de cada commit: `git check-ignore -v .env.local` debe responder que está ignorado.
- `instalar.py` aplica solo las migraciones pendientes, todas en una transacción. Para ver qué haría sin cambiar nada: `--verificar`.

## Lo que no se hace aquí

- No se cambia el contrato (campos, tipos de respuesta, niveles, reglas). Si algo del contrato parece incorrecto, va como duda en el reporte.
- **Producción**: solo cuando el propietario lo pide en esa sesión, fuera del congelamiento, y solo con `supabase/instalar.py` (primero `--verificar`, con `--confirmar "$REF_PRODUCCION"`) o con las sentencias de una línea que documenta la guía (`ip_cabecera`, `asignar_propietario`). Nunca SQL improvisado en producción, y nunca la base ficticia ni la clave del tester allí.
- PRUEBA en Supabase: si la limpieza del tester falla, la base queda con datos del tester; se recarga con `datos_prueba.sql` (que reemplaza la base ficticia) y se anota en el reporte.
- No se reescriben archivos grandes para "ordenarlos". Si un archivo necesita reestructurarse, se pide en la conversación de diseño.
- No se agregan dependencias nuevas sin anotarlo en el reporte.
