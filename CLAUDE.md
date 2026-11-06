# Inscripciones CIIC 2026 · contexto para Claude Code

Sistema de inscripción a visitas técnicas y talleres. Supabase (PostgreSQL + PostgREST + Auth) y páginas estáticas en GitHub Pages. **El contrato v5.5 está cerrado**: no se rediseña nada, se implementa y se prueba.

## Tu papel (ahorra tokens)

El diseño y el código pesado se escriben en otra conversación y llegan a este repositorio como archivos listos en `sprints/sprint-N/`. Aquí: **aplicar (`python sprints/sprint-N/aplicar.py`), compilar, probar y reportar**.

- No leas archivos completos si no hace falta: usa `grep -n` y lee rangos.
- **Nunca abras** `docs/demo/datos-demo.js` (570 KB), `local/inscripciones_prueba.sql` (250 KB), `local/datos_prueba.sql` (130 KB) ni `documentacion/lamina-*.html` (260 KB), ni `demo/*.html` (copias armadas de docs/, 700 KB cada una). Para saber qué contienen: `python local/generar_datos.py` imprime el resumen.
- La documentación (`documentacion/CIIC2026-inscripciones-v5.5-documentacion.md`, 1750 líneas) se consulta por sección: `grep -n "^## \|^### " documentacion/*.md` y luego lee solo el rango que necesitas.
- Arreglos pequeños (hasta unas 20 líneas, claramente acotados): hazlos y anótalos en el reporte. Cambios mayores o dudas de contrato: **no improvises**; reporta y espera.
- Reporta con el formato de la skill `ciic-desarrollo`.

## Mapa

| Ruta | Qué es |
|---|---|
| `supabase/01_esquema.sql`, `02_api.sql`, `03_…` | Base construida (v5.1) y migraciones de cada sprint, en orden (`03_sprint1_seguridad.sql` … `09_sprint4_ensayo.sql`) |
| `supabase/instalar.py` | Instala o pone al día una base: aplica solo las migraciones pendientes, todas en una transacción (registro `privado.migraciones`) |
| `supabase/restaurar.py` | Restaura un respaldo del panel: `--verificar`, `--solo-faltantes`, `--completo`, `--simular` (documentación §19.5) |
| `local/armar_demos.py` | Arma `demo/*.html` (un archivo por página) a partir de docs/. No se editan a mano |
| `local/generar_datos.py` | Genera la base ficticia (demo, SQL y CSV). No edites a mano sus salidas: cambia el generador y vuelve a correrlo |
| `docs/index.html`, `docs/panel.html`, `docs/base.css`, `docs/config.js` | Páginas ya en v5.5 (participante y panel) |
| `docs/demo/demo-api.js` | **Referencia ejecutable del contrato v5.5**: si dudas qué debe responder la base, mira la función correspondiente aquí |
| `tester/tester.py` | Tester (364 pruebas en local desde el Sprint 4.1; los sprints agregan bloques) |
| `local/` | PostgreSQL local que imita a Supabase + servidor local |
| `sprints/PLAN.md` | Tareas y criterios de aceptación de cada sprint |
| `.claude/skills/` | `ciic-desarrollo` (cómo ejecutar un sprint) y `sql-ciic-inscripciones` (reglas para tocar SQL) |

## Comandos

```bash
# Base local desde cero (PostgreSQL 15+): esquema, todas las migraciones y la base ficticia (3201 en el padrón, 28 actividades)
dropdb --if-exists ciic && createdb ciic
psql -d ciic -q -f local/supabase_local.sql
python supabase/instalar.py --dsn "dbname=ciic" --datos local/datos_prueba.sql
# poner al día una base que ya existe (solo lo pendiente): python supabase/instalar.py --dsn "dbname=ciic"
# opcional, para explorar el panel con datos (el tester NO lo necesita):
# psql -d ciic -v ON_ERROR_STOP=1 -f local/inscripciones_prueba.sql     # 700 + 20 inscripciones ficticias
python local/generar_datos.py                                          # regenera todo lo ficticio (esquema v5.5)
psql -d ciic -tAc "select privado.crear_clave_admin();"        # guarda la clave en $CLAVE

# Servidor local (sirve docs/ y la API en el mismo puerto)
python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787 &

# Tester completo en local
python tester/tester.py --api http://127.0.0.1:8787 --anon local --key "$CLAVE" --local --dsn "dbname=ciic" --web http://127.0.0.1:8787/ --personas 150 --salida /tmp/r
#   el bloque W inscribe 1000 personas más (--personas-w 1000 por defecto; --personas-w 0 para una corrida rápida)
python local/medir_local.py --dsn "dbname=ciic" --api http://127.0.0.1:8787   # si la carga se ve lenta

# Backend de demostración (sin base): prueba rápida en Node
node -e "…"   # ver ejemplo en la skill ciic-desarrollo
```

Dependencias: `pip install requests playwright psycopg2-binary openpyxl && python -m playwright install chromium` (el navegador es obligatorio desde el Sprint 2).

## Supabase y GitHub (desde el Sprint 3)

- Dos proyectos: PRUEBA (base ficticia, tester) y PRODUCCIÓN (esquema; datos reales por el panel). Guía: `sprints/sprint-3/GUIA.md`.
- Instalar o poner al día: `python supabase/instalar.py --dsn "$DSN_PRUEBA" --confirmar "$REF_PRUEBA" [--datos local/datos_prueba.sql]`.
- Tester contra PRUEBA: `python tester/tester.py --api "$URL_PRUEBA" --anon "$ANON_PRUEBA" --key "$ADMIN_KEY" --dsn "$DSN_PRUEBA" --web https://<usuario>.github.io/<repo>/ --personas 150` (sin `--local`).
- Secretos solo en `.env.local` (ver la skill `ciic-desarrollo`, sección Secretos).

## Reglas que no se rompen

- Lo que no cambia el sprint, no se toca. El contrato solo cambia en la conversación de diseño.
- SQL: siempre la skill `sql-ciic-inscripciones` (migraciones numeradas, transacción, sin `DELETE`/`UPDATE` sin `where`, funciones nuevas en `privado` con `revoke`).
- Nunca datos reales de personas en el repositorio, en commits ni en mensajes.
- Nunca claves `service_role` o `secret` en archivos. `config.js` solo lleva `API_URL` y `ANON_KEY`.
- Producción: Claude Code la toca solo cuando el propietario lo pide en esa sesión, fuera del congelamiento, y solo con `supabase/instalar.py` (primero `--verificar`), `supabase/restaurar.py` o las sentencias de una línea de la guía. Nunca SQL improvisado, nunca la base ficticia ni la clave del tester allí (documentación §20.2, regla 16; skill `sql-ciic-inscripciones`, regla 14).
