# Plan de sprints · v5.1 construida → v5.5

**Punto de partida.** El SQL y el tester están en v5.1 (163 de 163 pruebas en local). Las páginas (`docs/`) ya están en v5.5 y funcionan completas en modo demo, con la base ficticia. Los sprints llevan la base a v5.5, de modo que las páginas funcionen igual en modo real.

**Cómo se trabaja.**
1. En la conversación de diseño se escriben los archivos de cada sprint y llegan en `sprints/sprint-N/`, con su `LEEME.md`.
2. En Claude Code se aplican, se prueban con la skill `ciic-desarrollo` y se devuelve el reporte.
3. Con el reporte, la conversación de diseño corrige, hasta que el sprint queda en verde.

**Referencias.** "Doc §N" es la sección de `documentacion/CIIC2026-inscripciones-v5.5-documentacion.md`. "Demo `x`" es la función o el `case` correspondiente en `docs/demo/demo-api.js`, que es el comportamiento esperado.

**Regla de cada sprint.** Todo cambio de SQL es una migración nueva `supabase/0N_nombre.sql` (doc §20.3). Nunca se editan `01` ni `02` ya aplicados en un proyecto real. Mientras no haya proyecto real, se pueden reemplazar con los archivos que lleguen del sprint.

---

## Sprint 1 · Seguridad · 05/11 · cerrado: 235 de 235 en Windows (p95 de carga 0,4 s) · corrección 1.1 aplicada

| # | Tarea | Doc | Demo |
|---|---|---|---|
| 1.1 | **Sin comprobantes**: `duplicado` solo con mensaje en `verificar` y `registrar`; `registrado` sin `codigo` y con `celular` | R-01, R-31, §13.3 | `duplicado`, `registrar` |
| 1.2 | **Incidencias**: tabla `privado.incidencias`; el `exception` de `api()` guarda el error y responde `incidencia`, sin `detalle`; acción `panel_incidencias` (nivel 2) | R-36, §15.13 | bloque `catch` de `api`, `panel_incidencias` |
| 1.3 | **IP real**: `privado.red()` según `config.ip_cabecera` (`auto` = `cf-connecting-ip`, luego `x-real-ip`, luego el primer valor de `x-forwarded-for`); se fija en el Sprint 3 con `admin_cabeceras`. No se usa el último valor sin confirmarlo: podría juntar a todos en una red | §8, §16 | — |
| 1.4 | **Producción sin clave**: trigger en `config` que borra `ADMIN_KEY` al pasar a PRODUCCION | R-37 | — |
| 1.5 | **Propietario único**: índice único parcial en `organizadores (rol) where rol = 'propietario'`; `panel_equipo_rol` y `panel_equipo_activo` no tocan al propietario ni asignan "propietario" | R-30, D9 | `panel_equipo_rol`, `panel_equipo_activo` |
| 1.6 | **Niveles de rol**: nivel por acción y, en `panel_config`, por campo; `sin_permiso` con `nivel` y mensaje "requiere rol admin o superior" / "es del propietario" | R-26, §16 | `NIVEL`, `nivelConfig` |
| 1.7 | **Bitácora con antes y después**: columnas `antes`, `despues` (jsonb) en `bitacora`; cambios de rol, de cuenta y de configuración las llenan | R-30, §15.11 | `bit(…, antes, despues)` |
| 1.8 | **Protección masiva**: triggers por sentencia (tablas de transición) en las 6 tablas críticas; `config.limite_masivo`; las funciones internas que tocan muchas filas declaran `set local ciic.masivo = 'confirmado'` | R-40, §15.15 | — |
| 1.9 | **Integridad del script**: hash SRI de supabase-js 2.45.4 en `config.js` (`SUPABASE_JS_SRI`) | §18 | — |
| 1.10 | **Tester**: bloques R (privilegios por REST: anónimo contra tablas, funciones de `privado` y acciones de panel), S, Z, AB, AD y AG | §22 | — |

**Aceptación.** Instalación limpia sin errores; tester en verde **sin** el bloque de navegador (se corre sin `--web`): las 163 anteriores, ajustadas a los cambios de contrato, más los bloques nuevos. El bloque de navegador vuelve en el Sprint 2, cuando la base acepte los campos que ya envían las páginas v5.5 (nombres, apellidos, correo, solicitud).

---

## Sprint 2 · Integridad y datos · 06/11 · cerrado: 302 de 302 en Windows (C, Spanish_Peru y English) con la corrección 2.1

| # | Tarea | Doc | Demo |
|---|---|---|---|
| 2.1 | **Padrón mínimo**: `padron (documento PK, etapa, datos jsonb, origen, creado_por, creado_en)`; migra lo existente (`nombre` y `fecha_compra` pasan a `datos`) | R-22, R-35, §15.2 | `panel_padron_agregar` |
| 2.2 | **Inscripciones con los campos nuevos**: `nombres`, `apellidos`, `correo` obligatorio, `acepta_privacidad`, `aviso_version`; `registrar` y `panel_inscribir` con esos campos | R-13, R-14, §13.2 | `datosPersona`, `registrar`, `panel_inscribir` |
| 2.3 | **Idempotencia con ámbito**: `privado.solicitudes (actor, accion, id, huella, respuesta, creado_en)`; la envoltura de `api()` exige UUID en escrituras, devuelve la respuesta guardada con `repetida: true` y responde `solicitud_repetida`; limpieza a las 24 h | R-32, §15.12 | bloque "R-32" de `api` |
| 2.4 | **Cupo final**: `panel_actividad` rechaza `delta` | D4 | `panel_actividad` |
| 2.5 | **Contadores por trigger**: trigger en `inscripcion_actividades` e `inscripciones`; quitar las sumas manuales; `panel_resumen.integridad`; `panel_sincronizar` (nivel 2) | R-33, §15.15 | `integridad`, `panel_sincronizar` |
| 2.6 | **Listas y grupo**: columnas `en_grupo`, `en_grupo_por`, `en_grupo_en`; acciones `panel_lista` y `panel_grupo_marcar` (nivel 1) | R-38, §14.5 | `lista`, `panel_lista`, `panel_grupo_marcar` |
| 2.7 | **Exportar**: `panel_exportar` (nivel 1, filtros de actividad y etapa) y `panel_registros` (nivel 2) registran cada descarga | R-39 | `panel_exportar`, `panel_registros` |
| 2.8 | **Importar padrón**: `panel_padron_importar` (nivel 3) con su informe | R-42 | `panel_padron_importar` |
| 2.9 | **Datos**: `generar_datos.py --esquema v55` (padrón sin nombre; inscripciones con nombres y apellidos) y `excel_a_sql.py` al esquema nuevo | §21.2 | — |
| 2.11 | **De prueba a real**: `panel_vaciar_prueba` y `panel_actividades_importar` (nivel 3) | R-44, R-45, §19.7 | `panel_vaciar_prueba`, `panel_actividades_importar` |
| 2.10 | **Tester**: bloques T, U, V, AA, AC, AE, AH, AI, AJ, AK; ajustar el bloque P a los campos nuevos de las páginas | §22 | — |

**Aceptación.** Tester completo en verde; páginas en `MODO: 'real'` contra el servidor local con el mismo comportamiento que en modo demo (inscripción completa, listas, CSV, importar).

---

## Sprint 3 · Proyecto real · 07/11 · ✅ cerrado el 06/11 (PRUEBA en verde en Supabase y GitHub; PRODUCCIÓN instalada vacía)

Guía paso a paso, con lo que haces tú y lo que hace Claude Code: `sprints/sprint-3/GUIA.md`.

| # | Tarea | Doc |
|---|---|---|
| 3.0 | Local: migración 05 (limpieza segura del tester, índice por documento, lote y tiempo en la importación, motivo de "ocupado"), `instalar.py`, tester con documentos `ZQX` y conexión directa a Supabase | §21.3 |
| 3.1 | Crear en Supabase los proyectos PRUEBA y PRODUCCIÓN (São Paulo) e instalar con `instalar.py` (PRUEBA con la base ficticia; PRODUCCIÓN vacía) | §21.3 |
| 3.2 | Configurar Auth en los dos: sin registro abierto, TOTP, Site URL y Redirect URLs del panel publicado | §12.4 |
| 3.3 | Tu cuenta de propietario en PRUEBA (`asignar_propietario`) | §12.3 |
| 3.4 | Los datos reales en PRODUCCIÓN entran por el panel cuando estén listos (§19.7); no hacen falta para cerrar este sprint | §19.7 |
| 3.5 | **Bloqueante para abrir.** `admin_cabeceras` en Supabase: fijar `config.ip_cabecera` en los dos proyectos (nunca `auto`). El tester exige que una IP falsa no cambie la red, que `ip_cabecera` no sea `auto` y que la red sea la IP pública de quien llama | §8 |
| 3.6 | GitHub: repositorio público, Pages desde `/docs` (apuntando a PRUEBA), variables `PRUEBA_API_URL` y `PRUEBA_ANON_KEY`, secreto `ADMIN_KEY`; flujos "Tester del sistema" y "Mantener Supabase activo" en verde | §21.1, §21.3 |
| 3.7 | Medir en Supabase: importar 10 000 filas (total y en la base) y la carga de 150 | §22 |

**Aceptación.** Las comprobaciones de la Fase F de la guía: tester contra PRUEBA en verde desde tu equipo (con `--dsn` y `--web`) y desde GitHub, incluidas las 3 pruebas de IP; panel publicado con tu cuenta de propietario; PRODUCCIÓN instalada, vacía y sin clave del tester; ningún secreto en el repositorio.

---

## Sprint 4 · Carga y operación · 08/11 · entregado el 06/11 (migración 08)

| # | Tarea | Doc | Demo |
|---|---|---|---|
| 4.1 | ~~`estado` con `conActividades`~~ adelantado al Sprint 2 | D3 | `api` → `estado` |
| 4.2 | ~~Aviso de privacidad: `config.aviso_version`~~ adelantado al Sprint 2 (se guarda en cada inscripción) | D6, §11 | — |
| 4.3 | **Tráfico**: secuencia `privado.llamadas`, tabla `privado.trafico` por ventana de 10 s, alerta sostenida en 3 ventanas, limpieza a los 2 días; `panel_resumen.trafico`; `config.umbral` (nivel 3) | R-34, §15.14 | `contarLlamada`, `trafico` |
| 4.4 | **Respaldo**: `panel_respaldo` (nivel 3) y `supabase/restaurar.py` (`--verificar`, `--completo`, `--solo-faltantes`) | R-41, §19.3–19.5 | `respaldo` |
| 4.5 | **Pasar a producción**: `panel_preparar_produccion` (nivel 3). Sus borrados masivos con `where true` (safeupdate, Sprint 3.2) | R-43 | `panel_preparar_produccion` |
| 4.6 | **Carga de 1000**: padrón sintético (`ZQX`, con `panel_padron_importar` en una llamada: no hizo falta `admin_sembrar`) y bloque W con 1000 personas; el tester baja el umbral para ver la alerta y lo restaura | §22 | — |
| 4.7 | **Simulacro de restauración**: bloque Y | §19.5 | — |
| 4.8 | Tester: bloques W, Y y AF (X ya está desde el Sprint 1) | §22 | — |
| 4.9 | Del reporte del Sprint 3: aviso oculto tras el código y `#error` del enlace usado en el panel; escáner con subconsulta; marcar en el grupo sin carrera; página publicada sin inyectar `config.js`; causa de cada reintento en el reporte | — | — |

**Aceptación.** Tester completo en verde en local y en el proyecto de prueba; P95 de la carga anotado; restauración completa y parcial comprobadas.

---

## Sprint 5 · Diseño de autor y ensayo · 09/11 y 10/11

| # | Tarea |
|---|---|
| 5.1 | Tu diseño sobre las páginas, respetando `docs/LEEME-DISENO.md` |
| 5.2 | Tester de navegador en verde con tu diseño |
| 5.3 | Equipo invitado con sus roles |
| 5.4 | Ensayo con diez personas: inscripción, cierre en medio, reapertura, cambio por soporte, alta de último momento, importación, listas y CSV |

## Apertura

Respaldo → Sistema → Pasar a producción → respaldo → tester en modo lectura → empieza el congelamiento (doc §20.1).
