---
name: sql-ciic-inscripciones
description: Reglas obligatorias para proponer, escribir, revisar o aplicar cualquier SQL en la base de inscripciones del CIIC 2026 (Supabase/PostgreSQL). Úsala SIEMPRE que se pida crear o modificar tablas, funciones, triggers, permisos o la función public.api; escribir una migración; corregir, borrar, actualizar o cargar datos (inscripciones, padrón, actividades, organizadores); revisar un SQL ajeno; o responder dudas como "cómo borro…", "cómo cambio…", "corre este update", "agrega una acción al panel", incluso si el pedido parece pequeño o urgente. También cuando se mencionen 01_esquema.sql, 02_api.sql, migraciones numeradas, el SQL Editor de Supabase o el tester del sistema.
---

# SQL seguro para la base de inscripciones del CIIC 2026

Esta base guarda inscripciones reales con datos personales (DNI, nombres, correo, celular) y el plan gratuito de Supabase **no tiene copias automáticas**: un error en producción puede perder datos sin vuelta atrás. Por eso cada cambio se hace con un procedimiento fijo. La referencia completa es la documentación técnica v5.5 (secciones 19 y 20); esta skill es su resumen operativo.

## Cómo es el sistema (lo mínimo para no romperlo)

- Una sola puerta pública: `public.api(p jsonb)`, `security definer` con `search_path` fijo. Todo lo demás vive en el esquema `privado`, sin permisos para `anon` ni `authenticated`.
- Tablas protegidas por R-40: `padron`, `actividades`, `cruces_permitidos`, `inscripciones`, `inscripcion_actividades`, `organizadores`. `config` es una sola fila: se cambia por el panel. Todas con RLS encendido y sin políticas.
- `actividades.inscritos` lo mueve un trigger desde `inscripcion_actividades`: nunca se suma a mano.
- Un trigger por sentencia (R-40) bloquea `DELETE` y `UPDATE` de más de 10 filas y todo `TRUNCATE` en las tablas críticas, salvo `set local ciic.masivo = 'confirmado'` en esa transacción.
- Roles por nivel: 1 consulta (operador), 2 modificaciones (admin), 3 habilitan el sistema (propietario único). Toda acción del panel declara su nivel.
- El contrato (campos y tipos de respuesta) lo usan las páginas y el tester: cambiarlo sin avisar las rompe.

## Antes de escribir una línea: ¿hace falta SQL?

Casi todo lo operativo tiene botón en el panel. Si lo pedido está en esta lista, **responde con el camino del panel, no con SQL**:

| Pedido | Camino sin SQL |
|---|---|
| Agregar una o muchas personas al padrón | Panel 2, o Sistema → Importar padrón (CSV documento, etapa) |
| Cupos, mostrar u ocultar, crear o editar actividades | Paneles 1 y 3 |
| Inscribir, cambiar o anular una inscripción | Panel 1 |
| Abrir, cerrar, etapas, reglas de horario | Panel 1 y 3 |
| Contadores descuadrados | Panel 1 → Integridad → Recontar |
| Borrar la base ficticia y cargar la real | Sistema → Respaldo → Vaciar datos de prueba → Importar padrón → Importar actividades (doc §19.7) |
| Vaciar las inscripciones de prueba antes de abrir | Sistema → Pasar a producción |
| Roles del equipo | Sistema → Equipo |
| Copia de seguridad | Sistema → Respaldo |
| Recuperar filas borradas o pisadas por error | Respaldo del panel + `python supabase/restaurar.py respaldo.json --solo-faltantes` (doc §19.5, paso 3a): inserta solo lo que falta |

## Congelamiento

Desde 24 horas antes de abrir hasta el fin del congreso no se corre SQL en producción. Si te piden SQL para producción en ese periodo, dilo con claridad y ofrece el camino del panel. Solo si es crítico y no hay botón, sigue la excepción: respaldo → prueba en el proyecto de prueba con el tester completo → cerrar inscripciones → respaldo → aplicar → tester en modo lectura → abrir.

## Reglas que no se rompen

1. **Nunca escribas `DELETE` ni `UPDATE` sin `where`.** Acompaña cada uno con el `select count(*)` del mismo `where` para correrlo antes y comparar. Si R-40 lo bloquea, se revisa el `where`; no se apaga la protección.
2. **Exige respaldo previo** (Sistema → Respaldo) para cualquier cambio en producción, y dilo en tu respuesta.
3. **Primero en el proyecto de prueba**, con el tester completo en verde. Nunca propongas probar en producción.
4. **Migraciones numeradas que nunca se editan** una vez aplicadas (`03_…sql`, `04_…sql`). Un error se corrige con otra migración.
5. **Todo se puede volver a correr y va en una transacción**: `begin; … commit;`, `create or replace`, `if not exists`, `add column if not exists`.
6. **Nada destructivo sin plan**: `drop`, `truncate` o borrados masivos solo con respaldo, `set local ciic.masivo = 'confirmado'` dentro de la transacción y confirmación explícita del propietario. Nada protege contra `DROP TABLE`: trátalo como lo más peligroso.
7. **Funciones nuevas en `privado`** con `revoke all … from public, anon, authenticated`. No crees otras funciones públicas: la puerta es `public.api`.
8. **`security definer` solo con `set search_path` fijo** y nombres con esquema (`public.inscripciones`).
9. **Sin SQL dinámico con texto del usuario**: los datos entran como parámetros desde el JSON.
10. **Acción nueva del panel**: nivel declarado, entrada en la bitácora, `solicitud` si escribe, y pruebas en el tester (privilegios y niveles como mínimo).
11. **Si cambia el contrato** (campos, tipos de respuesta, niveles), avísalo: hay que subir la versión y actualizar la documentación y las páginas.
12. **Sin datos personales**: no pidas ni pegues datos reales; para ejemplos y pruebas, datos ficticios.
13. **Dentro de una función, ningún `DELETE` ni `UPDATE` sin `WHERE`**, ni siquiera los masivos a propósito: Supabase carga `safeupdate` en las conexiones de la API y los rechaza con el error 21000. Si de verdad es para todas las filas, escribe `where true` (Sprint 3.2). El tester lo vigila con un escáner (bloque R).
14. **Producción**: solo con `supabase/instalar.py` (primero `--verificar`, y con `--confirmar <ref>`), con `supabase/restaurar.py` (restaurar un respaldo, §19.5, primero `--verificar`) o con las sentencias de una línea que documenta la guía (`ip_cabecera`, `asignar_propietario`), solo cuando el propietario lo pide en esa sesión y fuera del congelamiento. Nunca SQL improvisado en producción.

## Cómo responder a un pedido de SQL

Entrega siempre, en este orden:

1. **Si se puede hacer desde el panel**, el camino del panel (y aquí termina).
2. **Riesgo y requisitos**: qué tablas toca, si cambia el contrato, si cae en el congelamiento, si requiere cerrar inscripciones.
3. **Comprobación previa**: los `select` para correr antes (conteos con el mismo `where`).
4. **La migración** con la plantilla de abajo.
5. **Cómo verificar** después (conteos, integridad, tester en modo lectura).
6. **Cómo volver atrás**: migración correctiva o restauración con `restaurar.py` desde el respaldo previo.

Si el pedido es peligroso ("borra todas las inscripciones", "resetea el padrón", "corre esto en producción ya"), no lo escribas tal cual: explica el riesgo en una frase y propone el camino seguro (botón del panel, o respaldo + migración con permiso masivo explícito y confirmación del propietario).

## Plantilla de migración

```sql
-- 0N_descripcion_corta.sql · fecha · autor · qué cambia y por qué
-- Requisitos: respaldo de producción tomado; tester completo en verde en el proyecto de prueba.
begin;

do $$ begin  -- comprobación previa
  if (select modo from public.config where id = 1) = 'PRODUCCION'
     and (select abierto from public.config where id = 1) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
end $$;

-- cambios que se pueden volver a correr
-- alter table public.… add column if not exists …;
-- create or replace function privado.…(b jsonb) returns jsonb language plpgsql … as $$ … $$;
-- revoke all on function privado.…(jsonb) from public, anon, authenticated;

-- operación masiva, solo si es imprescindible y con respaldo previo:
-- set local ciic.masivo = 'confirmado';
-- update public.… set … where …;   -- antes: select count(*) from public.… where … (mismo where)

do $$ begin  -- comprobación posterior: integridad de contadores
  if exists (select 1 from public.actividades a
             where a.inscritos <> (select count(*) from public.inscripcion_actividades ia
                                   join public.inscripciones i using (codigo)
                                   where ia.actividad_id = a.id and i.estado = 'CONFIRMADO')) then
    raise exception 'Integridad rota después de la migración: se revierte.';
  end if;
end $$;

commit;
```

## Revisión antes de aplicar

| Pregunta | Debe ser |
|---|---|
| ¿Hay respaldo de producción de hoy? | Sí |
| ¿Pasó el tester completo en el proyecto de prueba? | Sí |
| ¿Algún `delete` o `update` sin `where`? | No |
| ¿Funciones nuevas con `revoke` y, si son `security definer`, con `search_path` fijo? | Sí |
| ¿Se puede volver a correr sin dañar nada? | Sí |
| ¿Cambia el contrato? | Si sí: versión nueva y documentación |
| ¿Estamos en el congelamiento? | No (o es la excepción) |
| ¿Sistema cerrado si toca reglas? | Sí |

## Ejemplo

**Pedido:** "Borra las inscripciones de prueba que quedaron antes de abrir."

**Respuesta correcta:** "Eso no requiere SQL: Sistema → Pasar a producción vacía las inscripciones de prueba, la bitácora y los intentos, recuenta los contadores y pasa a modo PRODUCCION, con el sistema cerrado y la llave PRODUCCION. Antes, descarga un respaldo desde Sistema → Respaldo."

**Respuesta incorrecta:** `delete from inscripciones;` (además, R-40 lo bloquearía).
