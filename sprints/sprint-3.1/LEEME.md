# Sprint 3.1 · corrección con lo encontrado en la Fase A del Sprint 3

Probado en el entorno de diseño: las seis migraciones instaladas desde cero en una sola transacción, y el tester con navegador en **302 de 302, dos veces, 0 reintentos**. El instalador nuevo pasó 9 escenarios (abajo).

## Qué trae

| Del reporte | Qué hace esta entrega |
|---|---|
| `instalar.py`: tus 3 arreglos | Incorporados: no toca nada con PRODUCCION abierta; `--datos` exige padrón, actividades e inscripciones vacíos; un archivo de datos suelto nunca se ejecuta |
| `instalar.py` reaplicaba 01 y 02 en cada corrida | **Registro de migraciones** (`privado.migraciones`): aplica **solo lo pendiente**, y todo lo pendiente en **una transacción**. Si algo falla, la base queda exactamente como estaba. En una base sin registro, lo aplicado se deduce de la versión. Avisa si un archivo ya aplicado cambió y no lo reaplica. `--verificar` muestra qué haría sin cambiar nada |
| Qué es una migración | Un archivo `supabase/NN_*.sql` con el encabezado "CIIC 2026 · … · NN ·". Lo que genera `excel_a_sql.py` no lo lleva (y ahora se escribe en `local/datos_excel.sql`, excluido por `.gitignore`) |
| Skill: salto antes de `ADMIN_KEY` (tu arreglo) | Incorporado. Además, `.env.local` pasa a **comillas simples** y la skill dice cómo comprobar que la clave quedó cargada sin mostrarla |
| `mantener-activo.yml` no consultaba PRODUCCIÓN | Consulta los proyectos de `config.js`, `PRUEBA_*` y `PRODUCCION_*`, sin repetir. **Si falta alguna variable, falla y GitHub avisa por correo**: ningún proyecto se pausa en silencio. Guía D5: cuatro variables |
| Acciones por etiqueta y dependencias con `>=` | Acciones fijadas por SHA de commit: checkout v6.1.0, setup-python v6.3.0, upload-artifact v6.0.0. Dependencias exactas: requests 2.34.2, playwright 1.64.0 (la 1.64.1 tiene menos de dos semanas), psycopg2-binary 2.9.13, openpyxl 3.1.5. El job del tester con permiso de solo lectura y sin credenciales persistidas |
| Contraseña con `$` o símbolos | Guía B3: contraseña solo con letras y números (si no, regenerarla); C1: comillas simples y copiar la cadena tal como la muestra Supabase |
| `api.ipify.org` | Documentado en la guía (C5) y en §21.3: solo recibe la IP de quien corre el tester |
| (hallado en esta entrega) "ocupado 57014" en Participantes | El motivo nuevo de "ocupado" lo delató: la pestaña superó 3 s con la máquina cargada y el padrón grande. **Migración 06**: Participantes lee las inscripciones una sola vez. Con 13 201 personas: **230 ms → 10 ms**, con respuestas idénticas en 20 combinaciones de filtros (comparadas byte a byte). Es la primera migración nueva bajo el registro: 05 no se edita |

## Los 9 escenarios del instalador

| # | Escenario | Resultado |
|---|---|---|
| 1 | Base nueva | 01 a 06 en una transacción |
| 2 | Volver a correr | "Ya está al día" |
| 3 | Base 5.5-s2 sin registro, con 720 inscripciones | Deduce 01 a 04; aplica **solo** 05 (y 06); las 720 intactas |
| 4 | Una migración nueva que falla a la mitad | **Nada** aplicado: ni la versión ni la columna de prueba |
| 5 | PRODUCCION abierta | Se detiene antes de tocar nada |
| 6 | `--datos` con padrón existente | No carga; lo explica |
| 7 | Un archivo de Excel nombrado `06_desde_excel.sql` | Ignorado: no es una migración |
| 8 | Una migración aplicada que luego cambió | Aviso; no se reaplica |
| 9 | `--verificar` en una base nueva | No crea nada |

## Cómo aplicarlo y probarlo

```bash
python sprints/sprint-3.1/aplicar.py            # 2 archivos aparecen como "incorpora" (tus arreglos)
pip install -r tester/requirements.txt          # versiones exactas
python supabase/instalar.py --dsn "dbname=ciic" --verificar     # debe decir: pendiente 06 (y deducir lo demás de la versión)
python supabase/instalar.py --dsn "dbname=ciic"                 # aplica solo la 06
python local/servidor_local.py --dsn "dbname=ciic" --puerto 8787 > srv.log 2>&1 &
python tester/tester.py --api http://127.0.0.1:8787 --anon local --key "$CLAVE" --local --dsn "dbname=ciic" \
  --web http://127.0.0.1:8787/ --personas 150 --salida resultados
```

Esperado: `privado.version()` → `5.5-s3.1`; tester **302 de 302**.

Con esto en verde, sigue `GUIA.md` desde la **Fase B** (cuentas y proyectos): ahí empieza tu parte.
