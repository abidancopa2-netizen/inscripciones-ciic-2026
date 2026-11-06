# Sprint 4.1 · corrección con lo encontrado en el reporte del Sprint 4

Probado en el entorno de diseño (PostgreSQL 16, con navegador): **364 de 364**, 1 omitida (la página publicada, que solo se prueba contra GitHub Pages). Lo corrí desde cero y sobre una base 5.5-s4 puesta al día con `instalar.py`, que es lo que pasará en PRUEBA y en PRODUCCIÓN.

## Lo principal: "Pasar a producción" ya se prueba por la API real, sin cambiar el modo de PRUEBA

Tu reporte tenía razón: "Pasar a producción" solo se iba a ejecutar de verdad el día de la apertura, y es justo el tipo de paso que falló con "Vaciar" (safeupdate de Supabase). En vez de cambiar PRUEBA a PRODUCCION y volver atrás a mano, la **migración 09** agrega `admin_ensayo`, que solo puede usar el tester (con su clave y en modo PRUEBA):

1. Por la API real cierra, ejecuta "Pasar a producción" (o "Vaciar datos de prueba") y mide cómo quedó la base. La llamada pasa por el mismo camino que usará el propietario: rol, safeupdate, disparadores y R-40.
2. Lo deshace todo dentro de la misma llamada: el modo, la clave del tester, el padrón y las inscripciones quedan como estaban.
3. Si algo fallara (por ejemplo, un borrado sin WHERE), devuelve el error con su código (21000) y el tester lo marca como FALLA.

El tester lo corre siempre, en el bloque AF, también desde GitHub. En PRODUCCIÓN no existe la clave del tester, así que ahí `admin_ensayo` no hace nada. Lo comprobé aquí también al revés: con una función que falla como safeupdate, el ensayo lo reporta con su código.

## Respuestas al reporte del Sprint 4

| Del reporte | Qué hace esta entrega |
|---|---|
| "Pasar a producción" sin probar por la API real | `admin_ensayo` (arriba). Es mejor que ensayar cambiando el modo de PRUEBA: no hay vuelta atrás manual ni clave nueva que crear |
| W desde la PC: `OSError 24` y `SSLEOFError` | Tres cambios en el tester. (1) En Windows amplía el límite de archivos (`_setmaxstdio(8192)`, como comprobaste). (2) Reutiliza las conexiones: el pool de `requests` era de 10, así que con 1000 personas casi cada llamada abría una conexión TLS nueva. Esa es la causa probable de los `SSLEOFError`, y quizá de los 114 `sin_conexion` del Sprint 3. (3) Las 1000 personas llegan repartidas en 3 s (`--rampa-w`), como en una apertura real, y no en el mismo milisegundo. **La medición de referencia de W es la de GitHub.** Si desde tu PC siguen fallando conexiones, es la PC o su red: córrelo con `--personas-w 0` |
| "Confirmar" con p95 3,9 s y límite de 3 s para anon | El límite de 3 s es por sentencia **dentro de la base**. Los 3,9 s son de punta a punta: la cola de Supabase, la red y TLS. Si una sentencia pasara de 3 s, verías `ocupado` con motivo 57014, y hubo cero. En el evento real la gente llega desde muchas redes y repartida en el tiempo, así que es más suave que esta prueba |
| Umbral 2000 con pico de 2342 | Recomiendo dejarlo. El pico fue **una** ventana con 1000 personas apretadas en 18 s, y la alerta exige **3 ventanas seguidas** (más de 6000 llamadas en 30 s). 1000 personas reales con la página abierta hacen unas 500 llamadas por ventana. La alerta no bloquea a nadie: solo avisa. Si quieres cambiarlo desde el panel, falta un campo en Sistema. Es un cambio chico para el Sprint 5, si lo pides |
| `restaurar.py` tomaba como dañado un respaldo sano con decimales (1.50) | El panel ahora guarda el respaldo **tal como lo entrega la base**, sin volver a escribirlo en el navegador, y `restaurar.py` lee los decimales tal cual. Para un respaldo guardado con el panel del Sprint 4 que tenga decimales existe una salida de emergencia: `--aceptar-huella-distinta` restaura si las filas de cada tabla cuadran (siempre con `--simular` primero) |
| `--simular` avanzaba la secuencia de la bitácora | Ya no escribe en la bitácora ni toca los contadores de ids |
| Botón de respaldo sin probar en el navegador | Prueba nueva en P: el botón baja el archivo y `restaurar.py --verificar` lo da por íntegro |

## Cómo aplicarlo y probarlo

**1 · En local (🤖)**

```bash
python sprints/sprint-4.1/aplicar.py
python supabase/instalar.py --dsn "dbname=ciic" --verificar     # debe decir: pendiente solo 09
python supabase/instalar.py --dsn "dbname=ciic"
python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787 > srv.log 2>&1 &
python tester/tester.py --api http://127.0.0.1:8787 --anon local --key "$CLAVE" --local --dsn "dbname=ciic" \
  --web http://127.0.0.1:8787/ --personas 150 --salida resultados
```

**2 · En PRUEBA (🤖)**

1. `instalar.py --dsn "$DSN_PRUEBA" --confirmar "$REF_PRUEBA" --verificar` → pendiente solo la 09; luego sin `--verificar`.
2. Commit y push (cambia `docs/panel.html`: el botón de respaldo).
3. Tester contra PRUEBA desde tu equipo, con `--dsn` y `--web`. Prueba primero con el W completo; si fallan conexiones, usa `--personas-w 0`. Lo que importa aquí es el bloque **AF: los dos ensayos por la API real deben pasar en Supabase**.
4. GitHub → "Tester del sistema" (completo, 150, W 1000). Es la medición de referencia de las 1000 personas.

**3 · En PRODUCCIÓN (🤖, solo si el propietario lo pide)**

`instalar.py --dsn "$DSN_PRODUCCION" --confirmar "$REF_PRODUCCION" --verificar` → pendiente solo la 09; luego sin `--verificar`. Es seguro: no toca datos, y `admin_ensayo` necesita la clave del tester, que en PRODUCCIÓN no existe. Así los dos proyectos siguen en la misma versión (5.5-s4.1).

## Qué esperar

| Medida | Entorno de diseño | En Supabase (para el reporte) |
|---|---|---|
| Versión | `5.5-s4.1` | Igual en los dos proyectos |
| Tester local | 364 de 364, 1 omitida | — |
| AF · ensayos por la API real | En verde | **En verde contra PRUEBA, desde la PC y desde GitHub.** Es la prueba que faltaba |
| W · 1000 personas | Entre p95 3,8 y 10,3 s de punta a punta, según la carga de la máquina | GitHub: compara con p95 15,9 s del Sprint 4. PC: anota si ya no hay `OSError 24` ni `SSLEOFError` |

## Si algo sale mal

`python sprints/sprint-4.1/aplicar.py --revertir` restaura los archivos. La 09 solo agrega una función del tester y vuelve a crear la puerta: si fallara en Supabase, `instalar.py` no deja nada a medias. El reporte va a la conversación de diseño con el formato de la skill.
