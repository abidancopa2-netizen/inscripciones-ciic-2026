# Sprint 3 · De local a Supabase y GitHub · contrato v5.5

Dos partes:
1. **Fase A, local (solo Claude Code):** esta entrega, probada en el entorno de diseño. 302 de 302 con navegador, dos veces desde una base nueva. Además, en "modo Supabase" (sin `--local`, con `--dsn`) corrieron todas las pruebas de la base y fallaron **solo** las 3 de IP, como debe ser sin proxy.
2. **Fases B a F, con Supabase y GitHub:** paso a paso en **`GUIA.md`**, que dice qué haces tú y qué hace Claude Code.

## Qué trae

| Del reporte del Sprint 2.1 o del plan | Qué hace |
|---|---|
| Documentos al azar del tester podían coincidir con personas reales | El tester usa `ZQX` + 7 dígitos, un formato que nadie real tiene, y `admin_limpiar` **solo** borra del padrón documentos con ese formato (migración 05). Con el padrón real en el proyecto de prueba, nadie real puede ser borrado |
| Lotes de la importación sin documentar | R-42 y §14.6: lotes de 2000, cada uno atómico y en la bitácora con su número ("lote 2/5"); reimportar es seguro |
| AE más lento dentro del tester en Windows | En el entorno de diseño, dentro y fuera del tester miden lo mismo (0,5 a 0,6 s): la diferencia es de ese equipo. La importación ahora devuelve `duracionMs` y el tester muestra "total X s · en la base Y s", para saber si el tiempo se va en la base o en el camino |
| (hallado en este sprint) Participantes lento con muchas inscripciones | Índice de inscripciones por documento: con 720 inscripciones, 207 ms → 27 ms |
| (hallado en este sprint) Un "ocupado" ocasional de `admin_muestra`, que no se pudo reproducir | "ocupado" ahora dice su motivo (código del error) y el tester lo muestra en los reintentos: así, en Supabase se sabrá si fue tiempo agotado o un bloqueo |
| (hallado en este sprint) Falso positivo posible en la prueba de privilegios contra Supabase | Si la conexión no puede actuar como `anon`, la prueba se omite y lo dice, en vez de pasar sin haber probado |
| 3.1 · Instalar en Supabase | `supabase/instalar.py`: migraciones en orden, cada una en su transacción; se detiene en el primer error; exige `--confirmar <ref>` en una base remota; solo carga datos ficticios en una base de prueba vacía |
| 3.5 · IP real (bloqueante) | Contra Supabase, el tester exige: una IP falsa no cambia la red; `ip_cabecera` no es `auto`; la red es tu IP pública |
| 3.6 · GitHub | El flujo del tester prueba siempre PRUEBA (variables `PRUEBA_*` y secreto `ADMIN_KEY`); "Mantener activo" consulta los dos proyectos. El navegador prueba la página publicada contra PRUEBA aunque `config.js` apunte a otro proyecto |
| Secretos | `.env.local` (excluido por `.gitignore` y prohibido al visor de Claude Code); la skill explica cómo cargarlo sin mostrarlo |

## Fase A

```bash
python sprints/sprint-3/aplicar.py

dropdb --if-exists ciic && createdb ciic
psql -d ciic -q -f local/supabase_local.sql
python supabase/instalar.py --dsn "dbname=ciic" --datos local/datos_prueba.sql      # el instalador nuevo, también en local
CLAVE=$(psql -d ciic -tAc "select privado.crear_clave_admin();")
python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787 > srv.log 2>&1 &
python tester/tester.py --api http://127.0.0.1:8787 --anon local --key "$CLAVE" --local --dsn "dbname=ciic" \
  --web http://127.0.0.1:8787/ --personas 150 --salida resultados
```

Esperado: `instalar.py` termina con "versión 5.5-s3 · padrón 3201 · integridad OK" y tres pendientes (propietario, clave, IP), que son para Supabase. Tester: **302 de 302**.

Con la Fase A en verde, el reporte puede venir aquí o seguir directo con `GUIA.md` (Fase B en adelante).
