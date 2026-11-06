# Inscripciones · CIIC 2026 · paquete v5.5 (contrato cerrado)

Sistema de inscripción a visitas técnicas y talleres: el participante entra con su documento; el equipo, con cuenta, código del celular y rol por nivel. Todo lo que no puede fallar vive en la base de datos (Supabase/PostgreSQL).

## Estado

| Pieza | Estado |
|---|---|
| Contrato | **v5.5, cerrado**: `documentacion/CIIC2026-inscripciones-v5.5-documentacion.md` |
| Páginas (`docs/`) | **v5.5 completas**. Funcionan ya en modo demo, sin Supabase, con la base ficticia |
| Base ficticia | 3201 personas en el padrón, 28 actividades, 700 inscripciones y 20 anuladas, generadas por `local/generar_datos.py` |
| Base de datos (`supabase/`) | v5.1 construida: 154 de 154 pruebas sobre la base ficticia, desde una instalación limpia. Los sprints 1 a 4 la llevan a v5.5 |
| Tester (`tester/`) | v5.1; cada sprint le agrega bloques |
| Plan | `sprints/PLAN.md`: tareas y aceptación de cada sprint, del 5 al 10 de noviembre |

Mientras la base no llegue a v5.5 (Sprint 2 para lo esencial, Sprint 4 para todo), las páginas en modo real no funcionan completas contra ella: para diseñar y probar, usa el modo demo.

## Para diseñar las páginas

Abre `demo/demo-participante.html` y `demo/demo-panel.html` con doble clic: son las dos interfaces completas, con la base ficticia adentro y un selector para ver cada estado (espera, sin conexión, cuenta regresiva, error, saturación, inicio de sesión). Cuando cambies el diseño en `docs/`, vuelve a armarlas con `python local/armar_demos.py`.

Lee `docs/LEEME-DISENO.md`: qué puedes cambiar, qué ids y atributos conservar, los estados que hay que diseñar, los formatos admitidos y los datos de prueba. En `docs/config.js`, `MODO: 'demo'`; abre `docs/index.html` y `docs/panel.html` en el mismo navegador (mejor con `python -m http.server 8000` dentro de `docs/`).

## De la base ficticia a la real

Desde el panel, pestaña Sistema, sin SQL: respaldo → vaciar datos de prueba → importar padrón → importar actividades → revisar → respaldo → pasar a producción. Detalle en la documentación, sección 19.7. Los CSV de `local/` sirven para ensayarlo con la base ficticia.

## Para implementar con Claude Code

1. Abre la carpeta del paquete con Claude Code. Lee `CLAUDE.md` y las skills de `.claude/skills/` (se cargan solas).
2. Cada sprint llega desde la conversación de diseño a `sprints/sprint-N/`.
3. Pide: "aplica y prueba el sprint N". Claude Code sigue la skill `ciic-desarrollo` y devuelve un reporte corto.
4. Pega ese reporte en la conversación de diseño para las correcciones.

`.claude/settings.json` le impide abrir los archivos grandes que no necesita (datos generados y lámina), para ahorrar tokens.

## Probar en tu computadora

```bash
pip install requests playwright psycopg2-binary openpyxl && python -m playwright install chromium
createdb ciic
psql -d ciic -f local/supabase_local.sql -f supabase/01_esquema.sql -f supabase/02_api.sql -f local/datos_prueba.sql
psql -d ciic -f local/inscripciones_prueba.sql                    # opcional: 720 inscripciones para explorar el panel
psql -d ciic -tAc "select privado.crear_clave_admin();"          # copia la clave
python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787   # http://127.0.0.1:8787/ (en modo real)
python tester/tester.py --api http://127.0.0.1:8787 --anon local --key CLAVE --local --dsn "dbname=ciic"   # sobre una base sin inscripciones_prueba
```

## Contenido

| Ruta | Qué es |
|---|---|
| `CLAUDE.md` | Contexto breve para Claude Code |
| `.claude/skills/ciic-desarrollo/` | Cómo ejecutar y reportar un sprint |
| `.claude/skills/sql-ciic-inscripciones/` | Reglas para proponer, revisar y aplicar SQL (también para otras IA) |
| `demo/` | Demos autónomas de las dos interfaces (un archivo cada una), para diseñar |
| `docs/` | Páginas, estilos, configuración, modo demo y guía de diseño |
| `docs/demo/demo-api.js` | Referencia ejecutable del contrato v5.5: la base debe responder igual |
| `supabase/` | Esquema, API y carga desde Excel (v5.1) |
| `local/` | Base local que imita a Supabase, servidor local, generador y archivos de la base ficticia |
| `tester/` | Tester automático |
| `.github/workflows/` | Tester en GitHub y "Mantener Supabase activo" |
| `documentacion/` | Documentación v5.5 y lámina INS-07 |
| `sprints/` | Plan y entregas de cada sprint |

## Reglas

- El contrato solo cambia en la conversación de diseño.
- Nunca datos reales, respaldos ni claves secretas en el repositorio (`.gitignore` ya los excluye; la base ficticia es inventada y sí va).
- Producción: congelamiento desde 24 horas antes de abrir hasta el fin del congreso (documentación §20).
