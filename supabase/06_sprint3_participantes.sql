-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones · 06 · SPRINT 3.1 · PARTICIPANTES EN UNA PASADA     contrato v5.5
--  Va después de 05_sprint3_supabase.sql. Se puede volver a correr. Primera migración nueva bajo el
--  registro de migraciones: 05 ya pudo aplicarse en una base, así que no se edita.
--
--  panel_participantes buscaba la inscripción de CADA persona del padrón por separado (una subconsulta
--  por fila), aunque devolviera solo 50. Con 13 201 personas tardaba 230 ms en local y, con la máquina
--  cargada, superó el límite de 3 s ("ocupado 57014" en el tester del Sprint 3.1). Ahora lee las
--  inscripciones una sola vez y busca las actividades solo de las filas de la página. Mismo contrato y
--  mismas respuestas.
-- ════════════════════════════════════════════════════════════════════════
begin;

do $$ begin
  if exists (select 1 from public.config where id = 1 and modo = 'PRODUCCION' and abierto) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
end $$;

create or replace function privado.version() returns text language sql immutable as $$ select '5.5-s3.1'::text $$;

create or replace function privado.panel_participantes(b jsonb) returns jsonb language plpgsql stable as $$
declare
  v_etapa int := privado.entero(b -> 'etapa');
  v_estado text := nullif(privado.jtext(b -> 'estado'), '');
  q text := upper(btrim(privado.jtext(b -> 'q')));
  q_doc text;
  v_pag int := greatest(coalesce(privado.entero(b -> 'pagina'), 1), 1);
  r jsonb;
begin
  q_doc := case when q = '' then '' else privado.normalizar_doc(to_jsonb(q)) end;
  with ul as (            -- una sola pasada: la inscripción que manda por documento (la confirmada; si no, la más reciente)
    select distinct on (i.documento) i.documento, i.codigo, i.estado, i.apellidos || ', ' || i.nombres nom
    from public.inscripciones i
    order by i.documento, (i.estado = 'CONFIRMADO') desc, i.orden desc),
  base as (
    select p.documento, p.etapa, p.origen, p.orden, ul.codigo, coalesce(ul.estado, 'SIN_INSCRIBIR') estado, coalesce(ul.nom, '') nombre
    from public.padron p left join ul on ul.documento = p.documento
    where (v_etapa is null or p.etapa = v_etapa)
      and (q = '' or p.documento like '%' || q_doc || '%' or upper(coalesce(ul.nom, '')) like '%' || q || '%')),
  filtrado as (select * from base where v_estado is null or estado = v_estado),
  pagina as (select * from filtrado order by orden offset (v_pag - 1) * 50 limit 50)
  select jsonb_build_object('ok', true, 'tipo', 'panel', 'total', (select count(*) from filtrado), 'pagina', v_pag, 'porPagina', 50,
    'resumen', (select jsonb_build_object('padron', count(*), 'inscritos', count(*) filter (where estado = 'CONFIRMADO'),
                 'sinInscribir', count(*) filter (where estado = 'SIN_INSCRIBIR'), 'agregados', count(*) filter (where origen = 'PANEL')) from base),
    'filas', coalesce((select jsonb_agg(jsonb_build_object('doc', f.documento, 'etapa', f.etapa, 'nombre', f.nombre, 'origen', f.origen,
                        'estado', f.estado, 'codigo', f.codigo,
                        'actividades', coalesce((select jsonb_agg(ia.actividad_id order by ia.actividad_id)
                                                 from public.inscripcion_actividades ia where ia.codigo = f.codigo), '[]'::jsonb)) order by f.orden)
                       from pagina f), '[]'::jsonb)) into r;
  return r;
end $$;

revoke all on all functions in schema privado from public, anon, authenticated;

commit;
