-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones · 13 · SPRINT 6.4 · YA INSCRITO: VER TUS GRUPOS     contrato v5.5
--  Va después de 12. Se puede volver a correr. Versión 5.5-s6.4.
--
--  Cambio de contrato aprobado por el propietario el 17/11/2026 (excepción §20.1): varias cuentas de WhatsApp del
--  equipo quedaron bloqueadas por agregar personas a mano y los inscritos no podían volver a ver el enlace de su grupo.
--  Desde ahora, verificar con un documento que tiene una inscripción CONFIRMADA responde "duplicado" con lo necesario
--  para que la página muestre sus grupos: documento, etapa y, por actividad, id, tipo, nombre, fecha, inicio, fin,
--  lugar, grupoModo y grupo (el enlace solo si la entrega es ENLACE). NUNCA código, celular, correo ni nombre.
--  Las anuladas no cuentan. Funciona también con las inscripciones cerradas (la revisión de "ya inscrito" ya iba antes
--  que la de "cerrado"). No cuenta como intento fallido (igual que antes).
--
--  Solo cambia privado.duplicado y agrega privado.ya_inscrito. verificar, registrar y public.api no cambian.
--  El texto del aviso no cambia: entre esta migración y la publicación de la página nueva, la página anterior sigue
--  mostrando el mismo aviso de siempre. registrar sigue respondiendo el aviso solo (lo llama sin código); la página
--  nueva, en ese caso, vuelve a verificar y muestra los grupos.
-- ════════════════════════════════════════════════════════════════════════
begin;

do $$ begin
  if exists (select 1 from public.config where id = 1 and modo = 'PRODUCCION' and abierto) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
end $$;

create or replace function privado.version() returns text language sql immutable as $$ select '5.5-s6.4'::text $$;

-- Lo que ve quien verifica un documento ya inscrito: sus grupos, sin datos personales ni código.
create or replace function privado.ya_inscrito(p_codigo text) returns jsonb language sql stable as $$
  select privado.fallo('duplicado', 'Este documento ya está inscrito. Si necesitas ayuda, escríbenos.',
    jsonb_build_object('yaInscrito', true, 'doc', i.documento, 'etapa', i.etapa,
      'actividades', coalesce((
        select jsonb_agg(jsonb_build_object(
                 'id', ia.actividad_id,
                 'tipo', coalesce(a.tipo, ''),
                 'nombre', coalesce(a.nombre, ia.actividad_nombre),
                 'fecha', coalesce(privado.fecha_txt(a.fecha), ''),
                 'inicio', coalesce(privado.hora_txt(a.inicio), ''),
                 'fin', coalesce(privado.hora_txt(a.fin), ''),
                 'lugar', coalesce(a.lugar, ''),
                 'grupoModo', coalesce(a.grupo_modo, 'ENLACE'),
                 'grupo', case when a.grupo_modo = 'ENLACE' then nullif(a.grupo_whatsapp, '') end)
               order by a.fecha, a.inicio, ia.actividad_id)
        from public.inscripcion_actividades ia left join public.actividades a on a.id = ia.actividad_id
        where ia.codigo = i.codigo), '[]'::jsonb)))
  from public.inscripciones i
  where i.codigo = p_codigo and i.estado = 'CONFIRMADO'
$$;

-- verificar la llama con el código de la inscripción CONFIRMADA; registrar, sin código (el aviso solo, como antes).
create or replace function privado.duplicado(p_codigo text) returns jsonb language sql stable as $$
  select coalesce(case when p_codigo is not null then privado.ya_inscrito(p_codigo) end,
                  privado.fallo('duplicado', 'Este documento ya está inscrito. Si necesitas ayuda, escríbenos.'))
$$;

revoke all on function privado.ya_inscrito(text) from public, anon, authenticated;
revoke all on all functions in schema privado from public, anon, authenticated;

do $$ begin  -- comprobación posterior: integridad de contadores (esta migración no los toca)
  if exists (select 1 from public.actividades a
             where a.inscritos <> (select count(*) from public.inscripcion_actividades ia
                                   join public.inscripciones i using (codigo)
                                   where ia.actividad_id = a.id and i.estado = 'CONFIRMADO')) then
    raise exception 'Integridad rota: no se aplica la migración.';
  end if;
end $$;

commit;
