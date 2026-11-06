# Sprint 4 · Carga y operación · contrato v5.5

Probado en el entorno de diseño (PostgreSQL 16, con navegador): **355 de 355**, 1 omitida (la página publicada, que solo se prueba contra GitHub Pages). Lo corrí desde cero, dos veces seguidas y también sobre una base 5.5-s3.2 puesta al día con `instalar.py`, como ocurrirá en Supabase. La migración 08 también se aplicó sobre una base 5.5-s3.2 con las 720 inscripciones ficticias, y luego otra vez encima: sin errores e integridad OK.

Antes de entregarlo, una revisión independiente revisó la migración 08 y `restaurar.py` y encontró defectos reales. Están corregidos y cada uno tiene su prueba (al final de este archivo).

## Qué trae

| # | Tarea | Dónde | Cómo se prueba |
|---|---|---|---|
| 4.3 | **Tráfico y alerta de saturación** (R-34): cada llamada suma 1 a una secuencia; la primera de cada ventana de 10 s toma la foto, sin esperar nunca a otra. La alerta se enciende con 3 ventanas seguidas sobre el umbral y se apaga con 3 por debajo, y queda en la bitácora. `panel_resumen.trafico` y `config.umbral` (nivel 3) | `08` | W: una ráfaga no alerta; si se sostiene, sí |
| 4.4 | **Respaldo** (R-41): `panel_respaldo` (nivel 3) con las 10 tablas, filas y huella SHA-256 por tabla y total; `ultimoRespaldo` en el panel. **`supabase/restaurar.py`**: `--verificar`, `--solo-faltantes`, `--completo`, `--simular` (muestra qué volvería, sin cambiar nada) y `--tablas`, como SQL para el SQL Editor o directo con `--dsn` | `08`, `supabase/restaurar.py` | Y |
| 4.5 | **Pasar a producción** (R-43): `panel_preparar_produccion` (nivel 3), con la llave PRODUCCION, cerrado y en PRUEBA. Quita además del padrón los documentos del tester (`ZQX…`). Todos sus borrados con `where true` (safeupdate) | `08` | AF |
| 4.6 | **Carga de 1000**: 1000 personas sintéticas (`ZQX`) navegan y confirman a la vez. Se importan con `panel_padron_importar` en una sola llamada, así que `admin_sembrar` no hizo falta | `tester/tester.py` | W |
| 4.7 | **Simulacro de restauración**: respaldo → base nueva instalada con `instalar.py` → `--completo` → huella por tabla idéntica. Luego se borran filas a propósito y se cambia una inscripción → `--simular` no cambia nada → `--solo-faltantes` devuelve lo borrado sin duplicar ni tocar la inscripción cambiada; repetirlo no agrega nada | `tester/tester.py` | Y (solo en local) |
| — | "Vaciar datos de prueba" también vacía el tráfico. `instalar.py` conoce la versión 5.5-s4 | `08`, `supabase/instalar.py` | AJ |

El bloque X (incidencias) ya estaba desde el Sprint 1.

## Respuestas al reporte del Sprint 3

| Del reporte | Qué hace esta entrega |
|---|---|
| (a) Aviso oculto en el panel tras el código | Corregido: si la cuenta no puede entrar, el aviso va al paso de inicio de sesión, visible. En el modo demo ocurría lo mismo con la cuenta "sin rol", y también quedó corregido. Prueba nueva en P con Supabase Auth **simulado**, sin cuentas reales (solo en local): con el panel del Sprint 3 la prueba falla, con el nuevo pasa |
| (a) `#error=…otp_expired` en la URL | Tu inferencia era correcta: supabase-js 2.45, al ver un error en la URL, descarta la sesión guardada. Ahora el panel quita el `#error` **antes** de iniciar supabase-js y explica: "El enlace del correo ya se usó o venció: sirve una sola vez…". La prueba simulada reproduce ese comportamiento de supabase-js |
| (b) GUIA, Fase E: el enlace sirve una vez | Agregado |
| Escáner: `UPDATE … SET x = (SELECT … WHERE …)` | Corregido: el WHERE de una subconsulta ya no cuenta. El tester se prueba primero con 22 casos, incluidos los dos del punto ciego, y recién después revisa las funciones |
| "Marcar en el grupo" con timeout de 10 s | Había una carrera en el panel: dos cargas de la lista seguidas podían pintar la vieja al final. Ahora solo se pinta la respuesta más reciente. La prueba espera la lista de esa actividad y la fila por su código |
| Reintentos sin causa (114 `sin_conexion`) | No se pudo reproducir: aquí hubo 0 en las tres corridas. El reporte ahora trae la causa del primero de cada tipo ("primer registrar: sin_conexion: …"), así la próxima vez se sabrá si fue la red, un timeout o Cloudflare |
| Prueba de la página publicada sin inyectar `config.js` | Nueva, en P y en modo lectura: abre la página con **su** `config.js` y comprueba modo real, URL y clave configuradas, que responde y que tiene el hash SRI. Además informa a qué proyecto apunta. En local se omite |
| GUIA, Fase F: "postgresql://" | Ahora dice "ninguna cadena de conexión **con contraseña**" (las plantillas no cuentan) |
| `srv.log` sin excluir | `.gitignore`: `srv.log`, `*.log` y `restaurar*.sql` (el SQL de una restauración tiene datos personales) |
| Aviso de privacidad con corchetes | El tester lo vigila: contra PRUEBA lo marca como pendiente (OMITE); contra un proyecto en PRODUCCION, como FALLA. El texto lo completas tú antes de la apertura |
| Botón "Entrar con la clave de prueba" visible | El panel lo oculta cuando la base está en PRODUCCION, porque esa clave ya no existe (R-37) |
| Base de `docs/config.js` = `e6883d992eda` | Esta entrega **no toca** `config.js`: tu versión, la que apunta a PRUEBA, queda igual |
| Ya señalado antes: `CLAUDE.md` decía que producción solo la toca el propietario | Alineado con la skill y §20.2: Claude Code la toca cuando el propietario lo pide en la sesión, solo con `instalar.py`, `restaurar.py` o las sentencias de una línea de la guía |

## Cómo aplicarlo y probarlo

**1 · En local (🤖)**

```bash
python sprints/sprint-4/aplicar.py                       # 14 archivos; rearma las demos
python supabase/instalar.py --dsn "dbname=ciic" --verificar     # debe decir: pendiente solo 08
python supabase/instalar.py --dsn "dbname=ciic"                 # aplica la 08
python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787 > srv.log 2>&1 &
python tester/tester.py --api http://127.0.0.1:8787 --anon local --key "$CLAVE" --local --dsn "dbname=ciic" \
  --web http://127.0.0.1:8787/ --personas 150 --salida resultados
```

Si la base local tiene datos del tester de corridas viejas, instálala desde cero (skill `ciic-desarrollo`, paso 3). El bloque W suma unos 2 minutos.

**2 · En PRUEBA (🤖, con `.env.local` cargado)**

1. `python supabase/instalar.py --dsn "$DSN_PRUEBA" --confirmar "$REF_PRUEBA" --verificar` → pendiente solo la 08. Luego sin `--verificar`.
2. Commit y push (incluye `docs/panel.html`). Espera a que GitHub Pages publique: el panel nuevo usa acciones que recién existen con la 08, por eso va después del paso 1.
3. Tester contra PRUEBA desde tu equipo, con `--dsn "$DSN_PRUEBA"` y `--web` con la página publicada, sin `--local`, como en C4. Esperado: todo en verde salvo lo que solo corre en local (Y restaurar, P inicio de sesión simulado). El aviso de privacidad aparece como OMITE: está pendiente para la apertura.
4. GitHub → "Tester del sistema" (completo, 150, W 1000) y "Mantener Supabase activo". Los dos en verde.

**3 · En PRODUCCIÓN (🤖, solo si el propietario lo pide en esa sesión)**

`python supabase/instalar.py --dsn "$DSN_PRODUCCION" --confirmar "$REF_PRODUCCION" --verificar` → pendiente solo la 08; luego sin `--verificar`. Sigue vacía, cerrada, en modo PRUEBA y sin clave del tester. **No** se pasa a producción en este sprint: eso es la apertura (Sprint 6).

**4 · Prueba del botón de respaldo (👤 + 🤖, opcional, 2 minutos)**

En el panel publicado (PRUEBA), Sistema → Respaldo → Descargar respaldo. Después pide: "verifica el respaldo que descargué con restaurar.py --verificar y simula --solo-faltantes contra PRUEBA". Debe decir "Respaldo íntegro" y, en la simulación, que no volvería nada (la base no perdió filas). El archivo solo trae datos ficticios, igual **no se sube**: `respaldo-*.json` está en `.gitignore`.

## Qué esperar

| Medida | Entorno de diseño (Linux) | En Supabase (para el reporte) |
|---|---|---|
| Versión | `5.5-s4` | Igual en PRUEBA y PRODUCCIÓN |
| Tester local | 355 de 355, 1 omitida | — |
| W · 1000 personas | De principio a fin p50 2,2 a 8,7 s, p95 3,8 a 10,3 s; confirmar p95 1,1 a 3,0 s; 0 reintentos (varía con la carga de la máquina) | Anota p50 y p95 desde tu equipo y desde GitHub, y los reintentos con su causa |
| Respaldo | Base ficticia con 720 inscripciones: 1,2 MB en 0,2 s. Base de 25 MB: 16 MB en 1,1 s | Tamaño y tiempo (línea "… respaldo de N KB en X s" del bloque Y). El límite del propietario en Supabase es 8 s |
| Restauración completa | 0,4 s | Solo se prueba en local |

## Cambios de comportamiento

- **Cada llamada a la API suma al contador de tráfico.** Una vez cada 10 s, la primera llamada escribe una fila en `privado.trafico`. Si eso fallara, la llamada se atiende igual.
- **`panel_resumen` trae `trafico` y `ultimoRespaldo`** (antes `null`), y `config` trae `umbral`.
- **El respaldo queda en la bitácora**, y el panel muestra el último.
- **Pasar a producción** vacía inscripciones, bitácora, intentos, solicitudes, tráfico e incidencias; el padrón y las actividades quedan. La primera entrada de la bitácora es "Pasar a producción".
- **Panel:** el aviso de una cuenta que no puede entrar siempre se ve; un enlace de correo ya usado se explica; la clave de prueba se oculta en PRODUCCION.

## Lo que encontró la revisión independiente (corregido)

| Hallazgo | Corrección | Prueba |
|---|---|---|
| **Grave.** `--solo-faltantes` devolvía la actividad vieja a una inscripción cambiada después del respaldo: quedaba con 3 actividades, y la integridad igual daba OK | Una inscripción vuelve entera solo si ya no existe; a una que existe nunca se le agregan actividades | Y: "Una inscripción cambiada después del respaldo queda como está" |
| Un respaldo de PRUEBA se podía aplicar sobre la base de PRODUCCION y devolvía 720 inscripciones de prueba | `--solo-faltantes` exige el mismo modo que el respaldo | Y: "no se mezcla" |
| Las actividades quitadas a propósito volvían visibles | Vuelven ocultas y el informe las lista. `--simular` muestra todo antes de aplicar | Y: "vuelve oculta", "--simular" |
| El contador de tráfico podía frenar otra llamada hasta "ocupado" cuando una llamada larga cruzaba el cambio de ventana | Una sola llave para toda la base: quien no la obtiene sigue de largo | Reproducido a mano: la llamada corta tardó 5 ms |
| `--completo` perdía los valores de `tipos_actividad` y las actividades de inscripciones anuladas cuya actividad ya no existe, y las informaba como "ya estaban" | Ahora toma los tipos del respaldo y conserva esas filas. Si la base nueva ya tenía bitácora (`asignar_propietario`), la entrada que choca entra con otro número | Reproducido a mano en bases nuevas |
| El respaldo de una base de 25 MB tardaba 5,9 s, cerca del límite de 8 s | La huella usa el texto nativo de jsonb: 1,1 s | Medido |
| Menores: las secuencias podían retroceder; el mensaje de cupo no decía qué regla fallaba; la nota de cuentas salía de más; nadie impedía abrir durante una restauración | Las secuencias solo avanzan; el mensaje nombra la regla; la nota sale solo si falta el usuario; `config` queda bloqueada mientras se restaura | — |

## Si algo sale mal

- `python sprints/sprint-4/aplicar.py --revertir` restaura los archivos. La 08 no se "desinstala": si la base local quedó con ella, instálala desde cero sin la 08. En Supabase, una corrección iría en una migración 09.
- Si `aplicar.py` se detiene por un archivo que no esperaba, no uses `--forzar`: lleva la lista al reporte.
- El reporte va a la conversación de diseño con el formato de la skill `ciic-desarrollo`, más las mediciones de la tabla de arriba.
