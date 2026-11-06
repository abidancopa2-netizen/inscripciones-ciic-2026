# Sprint 3.2 · compatible con `safeupdate` de Supabase

Corrige el defecto que el tester encontró en PRUEBA (Fase C): **Supabase carga la extensión `safeupdate`** en las conexiones de la API, y esta rechaza todo `DELETE` o `UPDATE` sin `WHERE` (error 21000). "Vaciar datos de prueba" (R-44) y la limpieza del tester fallaban; en local no se veía.

## Qué trae

| Del reporte | Qué hace |
|---|---|
| 9 sentencias sin `WHERE` (`admin_limpiar` 1, `panel_vaciar_prueba` 8) | **Migración 07**: las 9 con `where true`, que `safeupdate` acepta y que no cambia lo que hacen. Comprobado con `safeupdate` real: "Vaciar" por la API ahora funciona |
| El tester no lo detectaba | 1) **Escáner** en el bloque R (con `--dsn`): lee el código de todas las funciones y falla si alguna tiene `DELETE` o `UPDATE` sin `WHERE`; acierta en 11 casos de prueba, incluidos `ON CONFLICT DO UPDATE`, texto entre comillas y comentarios. 2) **El servidor local carga `safeupdate`** cuando está instalado, como Supabase: en el entorno de diseño se compiló, y el tester contra una base sin la 07 falla igual que en PRUEBA (escáner + 3 de limpieza). Con la 07: **303 de 303**. En Windows, si no está instalada, el servidor lo dice y el escáner lo cubre |
| Prueba de IP falsa imposible de pasar (Cloudflare responde 403 a `CF-Connecting-IP`) | Cada cabecera falsa se prueba por separado, con una llamada directa sin reintentos; el rechazo del proxy (400 o 403) cuenta como seguro |
| Skill: psql con `-d` al inicio (tu arreglo) | Incorporado, con la comprobación de valor no vacío |
| Skill y guía en conflicto sobre producción | Alineadas: Claude Code toca PRODUCCIÓN solo cuando el propietario lo pide en esa sesión, fuera del congelamiento, y solo con `instalar.py` (primero `--verificar`) o las sentencias de una línea de la guía. Regla 14 en la skill SQL y regla 16 en §20.2 |
| Versiones y fallas esperadas en la guía | C2 y C6: "la versión más reciente (hoy 5.5-s3.2)". C4: antes de C5 falla solo "ip_cabecera ya no es auto". C5: lo observado en PRUEBA (`cf-connecting-ip`) |
| `panel_preparar_produccion` (Sprint 4) | Anotado en el plan: sus borrados llevarán `where true`; el escáner lo vigilará igual |

## Cómo aplicarlo

**En local:**

```bash
python sprints/sprint-3.2/aplicar.py              # la skill de desarrollo aparece como "incorpora" (tu arreglo)
python supabase/instalar.py --dsn "dbname=ciic"   # aplica solo la 07
python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787 > srv.log 2>&1 &     # dirá si hay safeupdate
python tester/tester.py --api http://127.0.0.1:8787 --anon local --key "$CLAVE" --local --dsn "dbname=ciic" \
  --web http://127.0.0.1:8787/ --personas 150 --salida resultados
```

Esperado: versión `5.5-s3.2`; **303 de 303** (una prueba nueva: el escáner).

**En PRUEBA (Supabase), siguiendo la guía:**

1. C2: `instalar.py --dsn "$DSN_PRUEBA" --confirmar "$REF_PRUEBA" --verificar` → pendiente solo la 07; luego sin `--verificar`.
2. C4: el tester contra PRUEBA con `--dsn`. Esperado: **todo en verde**, porque `ip_cabecera` ya quedó en `cf-connecting-ip` en tu C5, y la limpieza ahora funciona. Si queda algún dato del tester en PRUEBA, ya no debería pasar.
3. Con eso en verde, C6 (PRODUCCIÓN) y la Fase D.
