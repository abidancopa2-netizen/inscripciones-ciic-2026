-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones · 12 · SPRINT 6 · LIMPIEZA PROGRAMADA     contrato v5.5
--  Va después de 11. Se puede volver a correr. No cambia la versión (sigue 5.5-s6) ni el contrato.
--
--  Incidencia #40: GitHub atrasa o se salta el horario de "Mantener activo" (el horario de GitHub es de mejor
--  esfuerzo). Sin visitas, las filas de intentos (IP e identificador del navegador) podían quedar horas.
--  Ahora la base misma, con pg_cron, llama cada 5 minutos a privado.limpiar_intentos(): una fila dura a lo más su
--  ventana de 10 minutos más 5. "Mantener activo" queda solo para que Supabase no pause el proyecto.
--
--  Si pg_cron no está disponible (la base local), la migración NO falla: avisa y la limpieza sigue como antes
--  (estado cada 20 s con páginas abiertas, y "Mantener activo"). instalar.py muestra al final si quedó programada.
--  Un segundo trabajo borra cada día el historial de pg_cron de más de 7 días (cron.job_run_details).
--  Para quitarlos: select cron.unschedule('ciic-limpiar-intentos'); select cron.unschedule('ciic-limpiar-historial-cron');
-- ════════════════════════════════════════════════════════════════════════
begin;

do $$ begin
  if exists (select 1 from public.config where id = 1 and modo = 'PRODUCCION' and abierto) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
end $$;

do $$
begin
  if to_regnamespace('cron') is null then
    begin
      create extension if not exists pg_cron with schema pg_catalog;      -- como indica Supabase (Integrations → Cron)
    exception when others then
      raise notice 'pg_cron no está disponible en esta base (%): la limpieza sigue con estado y "Mantener activo".', sqlerrm;
      return;
    end;
  end if;
  begin
    grant usage on schema cron to postgres;
    grant all privileges on all tables in schema cron to postgres;
  exception when others then
    raise notice 'Permisos de cron no cambiados (%): se intenta programar igual.', sqlerrm;
  end;
  begin
    perform cron.schedule('ciic-limpiar-intentos', '*/5 * * * *', 'select privado.limpiar_intentos()');
    -- el historial de corridas de pg_cron crece unas 290 filas al día: se guarda una semana
    perform cron.schedule('ciic-limpiar-historial-cron', '17 3 * * *',
                          $c$delete from cron.job_run_details where end_time < now() - interval '7 days'$c$);
  exception when others then
    raise notice 'No se pudo programar la limpieza (%): sigue con estado y "Mantener activo".', sqlerrm;
  end;
end $$;

commit;
