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

## Sprint 4 · Carga y operación · 08/11 · ✅ en verde el 06/11 (08 en PRUEBA y PRODUCCIÓN; 4.1 con la 09)

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
| 4.10 | **Sprint 4.1**, del reporte del Sprint 4: ensayo de "Pasar a producción" y "Vaciar" por la API real, deshecho en la misma llamada (migración 09, `admin_ensayo`, bloque AF); respaldo guardado tal como lo da la base (decimales exactos) y `--aceptar-huella-distinta` para emergencias; `--simular` sin tocar bitácora ni ids; W desde Windows (conexiones reutilizadas, límite de archivos, llegada en 3 s) | — | — |
| 4.9 | Del reporte del Sprint 3: aviso oculto tras el código y `#error` del enlace usado en el panel; escáner con subconsulta; marcar en el grupo sin carrera; página publicada sin inyectar `config.js`; causa de cada reintento en el reporte | — | — |

**Aceptación.** Tester completo en verde en local y en el proyecto de prueba; P95 de la carga anotado; restauración completa y parcial comprobadas.

---

## Sprint 5 · Diseño de autor y ensayo · 09/11 y 10/11 · entregado el 06/11

| # | Tarea |
|---|---|
| 5.1 | Tu diseño sobre las páginas: Tema CIDEIC (participante v3.1, panel v1.2) en `docs/tema/`, sin cambiar ids ni `data-*` ✅ |
| 5.2 | Tester de navegador en verde con tu diseño ✅ (en diseño) |
| 5.3 | Equipo invitado con sus roles: 2 admin y 4 operadores (`sprints/sprint-5/GUIA.md`, parte B) |
| 5.4 | Ensayo con diez personas (GUIA, parte C): inscripción, lleno, repetido, sin conexión, etapa no habilitada, fuera del padrón, cierre con aviso, anular, alta y cambio por soporte, listas y CSV, respaldo; al final, vaciar e importar (ensayo de §19.7) |
| 5.5 | Aviso de privacidad final, nombre del congreso y contacto en `config.js` (`sprints/sprint-5/configurar.py`) |
| 5.6 | Del reporte del 4.1: rampa en Q. Desde una PC (no en GitHub ni en local), es aviso y no falla: el tiempo pasado solo por fallas de conexión del equipo, y hasta un 2 % de personas sin conexión tras 3 min de reintentos, sin ningún error de la base |

## Sprint 5.1 · Correcciones antes del ensayo · entregado el 07/11

Del reporte del Sprint 5 (local 364/364, GitHub 295/295, PRUEBA con el tema y el aviso) y de las decisiones del propietario.

| # | Tarea |
|---|---|
| 5.1.1 | **Migración 10:** los intentos (IP e identificador del navegador) se borran al terminar su ventana de 10 min, con la consulta `estado` (de a una, con `SKIP LOCKED`), y "Mantener Supabase activo" corre cada hora. El aviso dice que se usan solo para el límite de 10 minutos y que después se borran |
| 5.1.2 | **Redes con intentos fallidos** en Operación (admin y propietario): IP enmascarada, fallos, % del límite, minutos para reiniciar, estado; avisos en la franja al 80 % y al frenar; "Liberar red" del propietario, con bitácora; límites editables desde el panel. Límite por red: 300 |
| 5.1.3 | Fuente Saira alojada en `docs/tema/fuentes/` (`sprints/sprint-5.1/fuente.py`): las páginas ya no llaman a Google |
| 5.1.4 | Aviso corregido (IP, GitHub Pages, correo electrónico) con `sprints/sprint-5.1/configurar.py`; "correo electrónico" también en la página, el panel y la base |
| 5.1.5 | Tester: bloque AL (redes y limpieza); desde una PC, T y W (sin conexión) y AE (tiempo en la base) son aviso; la página y el panel no llaman a Google y todos sus archivos cargan |
| 5.1.6 | GUIA: prueba de la red de la UCSM, correo para TI, caso de freno por red en el ensayo, plan de contingencia, quién vigila qué, texto de difusión y hora de apertura |

## Sprint 6 · Apertura de la Etapa 1 · 09/11 a 11/11 · entregado el 07/11

Fechas: ensayo el 10/11; apertura de la Etapa 1 el miércoles 11/11 (hora del propietario; recomendada 20:00); congreso del 16 al 21/11 (viicideic.space); borrado de datos a más tardar el 19/02/2027. Guía: `sprints/sprint-6/GUIA.md`.

| # | Tarea |
|---|---|
| 6.1 | **Correos de Supabase:** SMTP propio en PRUEBA y PRODUCCIÓN. Sin él, las invitaciones al equipo no llegan: el correo de Supabase solo envía a los miembros de la organización, y 2 por hora |
| 6.2 | Migraciones 11 (textos sin caracteres invisibles, R-47) y 12 (limpieza de intentos con pg_cron cada 5 min, incidencia #40) en PRUEBA; migraciones 10 a 12 en PRODUCCIÓN (Fase 1, 09/11). El mismo día, la cuenta del propietario en PRODUCCIÓN (Create new user y `asignar_propietario`): la única sentencia SQL queda antes del congelamiento |
| 6.3 | Panel: no se deja enmarcar; "Copiar mensaje" en Buscar (procedimiento 2); un doble toque en "Guardar" ya no crea dos actividades; con `PANEL_PRUEBA: false`, sin "Entrar con la clave de prueba" |
| 6.4 | Prueba de ataque en PRUEBA (`tester/ataque.py`, doc §22.4), antes del ensayo |
| 6.5 | Fase 2 (10/11, después del ensayo): `sprints/sprint-6/configurar.py` → `config.js` a PRODUCCIÓN; tester en lectura comprueba con el tráfico real que la página y el panel publicados llaman a PRODUCCIÓN; el propietario registra su código y el equipo entra por invitación (desde el panel, aun en el congelamiento) |
| 6.6 | Fase 3 (11/11): padrón, actividades y enlaces desde el panel; revisión; respaldo → Pasar a producción → respaldo → tester en lectura → congelamiento → abrir |
| 6.7 | Opcional: dominio `inscripciones.viicideic.space`, solo si queda listo antes del 10/11 a las 12:00; si no, github.io |
| 6.8 | Congelamiento: todo el SQL de PRODUCCIÓN el 09/11; desde el 10/11 a las 20:00, solo el panel. Problemas del ensayo: tabla de la GUIA (parte 4.1) y decisión de seguir o no el 11/11 a las 11:30 |
| 6.9 | Skill `ciic-desarrollo` al día para Windows (variables de PostgreSQL y Python, rutas en `resultados/`, `--personas-w 300` desde la PC, bitácora en `INCIDENCIAS.md`) |

## Sprint 6.1 · Recuperar la contraseña con el autenticador · entregado el 08/11

Panel, tester, `instalar.py` (solo lo que muestra) y textos: no cambia la base (sigue en `5.5-s6`) ni `config.js`. Va después de la Fase 1 de PRUEBA y de las migraciones en PRODUCCIÓN, y antes de invitar al equipo en PRUEBA; todo antes del congelamiento.

| # | Tarea |
|---|---|
| 6.1.1 | Panel: con el autenticador activo, el enlace de "¿Olvidaste tu contraseña?" pide primero el código de 6 dígitos (nivel `aal2`) y después la contraseña nueva. Antes daba "AAL2 session is required…". La invitación (sin autenticador) sigue igual |
| 6.1.2 | Tester: el Auth simulado ahora exige `aal2` para cambiar la contraseña con factor y guarda la sesión por proyecto, como Supabase. 3 pruebas nuevas: recuperación con autenticador, invitación, y la sesión de PRUEBA que no se usa al pasar a PRODUCCIÓN (390 en local) |
| 6.1.3 | GUIA: correo de Supabase con la cuenta propia del propietario y cómo cambiarla; contraseña o celular perdidos sin SQL ("Remove MFA factors", parte 4.2); red de la UCSM probada y correo a TI descartado; cronograma adelantado. Doc revisión 13 |
| 6.1.4 | `instalar.py` (#44): `--verificar` y el final de la instalación muestran la IP real y los límites (por red, por dispositivo, ventana), modo y si está abierta. Antes no había cómo leerlos en PRODUCCIÓN sin SQL |
| 6.1.5 | Skill `ciic-desarrollo`: la bitácora se cita por fecha y hora (no se numera); las incidencias, por su número. GUIA 5.1 y doc §24: "Permitir 2 talleres aunque queden visitas" encendido en PRODUCCIÓN (08/11) |

## Apertura

1. Migraciones 10 a 12 en PRODUCCIÓN (Fase 1 del Sprint 6), antes del congelamiento.
2. Respaldo → Sistema → Pasar a producción → respaldo → tester en modo lectura → empieza el congelamiento (doc §20.1).
