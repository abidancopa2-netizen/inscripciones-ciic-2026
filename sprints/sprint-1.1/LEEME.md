# Sprint 1.1 · corrección con lo encontrado en el reporte del Sprint 1

No hay SQL: la base no cambia. Incorpora los dos arreglos hechos en Claude Code y resuelve las dudas del reporte.

| Duda del reporte | Qué hace esta entrega | Archivo |
|---|---|---|
| Incorporar el arreglo del pool | Incorporado y llevado más lejos: el pool abre **y conserva** todas sus conexiones (`minconn = maxconn = --conexiones`). Con `minconn = precalentar`, cada conexión por encima de ese número se seguía cerrando al devolverse. Se quita `--precalentar` | `local/servidor_local.py` |
| Incorporar el arreglo de idioma | Incorporado sin depender de ningún idioma: las incidencias se comprueban por el SQLSTATE `22012` y el permiso denegado por `42501` | `tester/tester.py` |
| TCP_NODELAY no explicaba la concurrencia | Correcto: la causa principal era el pool. TCP_NODELAY se queda porque sí corrige las llamadas seguidas (44 ms → 1,6 ms) | — |
| `medir_local.py` repetido y "no cambia datos" | Quitado el hallazgo repetido y la tabla temporal sin uso; el texto ahora dice que crea y borra `public._medida_local` | `local/medir_local.py` |
| `ip_cabecera = auto` y el primer valor de `x-forwarded-for` | De acuerdo. El Sprint 3.5 pasa a ser **bloqueante para abrir**: contra Supabase el tester envía una IP falsa en `X-Forwarded-For`, `X-Real-IP` y `CF-Connecting-IP` y exige que la red no cambie, y exige que `ip_cabecera` ya no sea `auto` | `tester/tester.py`, `sprints/PLAN.md` |
| `tester.yml` publicaba capturas | Ahora sube solo `reporte.md` y `resultados.json` (7 días) y borra las capturas del servidor de GitHub | `.github/workflows/tester.yml` |
| La skill SQL decía 7 tablas | Corregido: R-40 protege 6; `config` es una fila que se cambia por el panel | `.claude/skills/sql-ciic-inscripciones/SKILL.md` |
| ¿Subir `archivos/` y `anteriores/`? | No: Git ya guarda el historial. `.gitignore` los excluye; se suben `LEEME.md`, `aplicar.py` y `manifiesto.json`. Además incorpora tus líneas (`.env.*`, `*.pem`, `*.key`, `.venv/`, `settings.local.json`) | `.gitignore` |
| Que el próximo `aplicar.py` no pise arreglos locales | **`aplicar.py` nuevo con `manifiesto.json`**: sabe sobre qué versión se escribió cada archivo. Si el del proyecto es distinto y la entrega no lo incorpora, se detiene **sin copiar nada** y lista los archivos | `aplicar.py` (este y todos los siguientes) |

## Cómo aplicarlo

```bash
python sprints/sprint-1.1/aplicar.py            # 3 archivos aparecen como "incorpora" (tus arreglos): es lo esperado
# reiniciar el servidor local (cambió) y medir
python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787 > srv.log 2>&1 &
python local/medir_local.py --dsn "dbname=ciic" --api http://127.0.0.1:8787
python tester/tester.py --api http://127.0.0.1:8787 --anon local --key "$CLAVE" --local --dsn "dbname=ciic" --personas 150 --salida resultados
```

No hace falta instalar la base de nuevo. Si `aplicar.py` se detiene por un archivo que no esperaba, no uses `--forzar`: lleva la lista al reporte.

## Qué esperar

- Tester: 235 de 235, 1 omitida (navegador). En Linux, 10 a 14 s.
- Al arrancar, el servidor local dice "60 conexiones abiertas" (en Windows puede tardar unos 3 s en abrirlas).
- `medir_local.py`: 100 llamadas a la vez con un p95 bastante menor que los 45 ms de tu reporte.
