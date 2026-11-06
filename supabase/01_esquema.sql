-- ════════════════════════════════════════════════════════════════════════
--  CIIC 2026 · Inscripciones a visitas y talleres · v5.1 (Supabase)
--  01 · ESQUEMA: tablas, restricciones y seguridad.
--  Supabase → SQL Editor → New query → pegar todo → Run. Se corre UNA vez,
--  en un proyecto nuevo. Referencia: lámina INS-05 y documentación v5.1 (sección 13).
--
--  SEGURIDAD: RLS encendido en TODAS las tablas y SIN políticas. Con la clave
--  pública (anon) nadie lee ni escribe tablas: solo puede llamar a public.api().
-- ════════════════════════════════════════════════════════════════════════

create extension if not exists pgcrypto with schema extensions;
create schema if not exists privado;
revoke all on schema privado from public;

-- Configuración: una sola fila.
create table if not exists public.config (
  id                  int primary key default 1 check (id = 1),
  abierto             boolean    not null default false,
  ronda               int        not null default 1 check (ronda >= 1),       -- sube en cada cierre (R-09)
  cierre_en           timestamptz,                                           -- cierre avisado (R-27)
  etapas              smallint[] not null default '{}',                      -- pueden inscribirse (R-06)
  etapas_visita       smallint[] not null default '{1}',                     -- pueden elegir visitas (R-07)
  dos_talleres        boolean    not null default true,                      -- R-08
  mismo_dia           boolean    not null default false,                     -- R-03
  margen_min          int        not null default 30 check (margen_min between 0 and 240),
  paso_cupo           int        not null default 5  check (paso_cupo between 1 and 100),
  refresco            int        not null default 20 check (refresco between 10 and 120),
  total_por_persona   int        not null default 2  check (total_por_persona = 2),
  limite_dispositivo  int        not null default 4  check (limite_dispositivo between 1 and 100),
  limite_red          int        not null default 30 check (limite_red between 1 and 100000),
  ventana_min         int        not null default 10 check (ventana_min between 1 and 120),
  modo                text       not null default 'PRUEBA' check (modo in ('PRUEBA', 'PRODUCCION'))
);
insert into public.config (id) values (1) on conflict (id) do nothing;

-- Tipos de actividad y su máximo por persona (R-02). Mañana: conferencias, cursos…
create table if not exists public.tipos_actividad (
  codigo                 text primary key check (codigo ~ '^[A-Z_]{3,20}$'),
  nombre                 text    not null,
  max_por_persona        int     not null check (max_por_persona between 0 and 10),
  requiere_etapa_visita  boolean not null default false                      -- true: aplica R-07
);
insert into public.tipos_actividad values ('VISITA', 'Visita técnica', 1, true), ('TALLER', 'Taller', 2, false)
on conflict (codigo) do nothing;

-- Padrón: documentos con entrada, por etapa de venta.
create table if not exists public.padron (
  documento     text     not null check (documento ~ '^[A-Z0-9]{6,12}$'),
  etapa         smallint not null check (etapa in (1, 2, 3)),
  nombre        text     not null default '',
  fecha_compra  text,
  origen        text     not null default 'CARGA' check (origen in ('CARGA', 'PANEL')),
  creado_por    uuid,
  creado_en     timestamptz not null default now(),
  orden         bigint generated always as identity,
  primary key (documento, etapa)
);

-- Actividades. "inscritos" solo lo mueven las funciones; el CHECK impide el sobrecupo.
create table if not exists public.actividades (
  id              text primary key check (id ~ '^[A-Za-z0-9_-]{1,20}$'),
  tipo            text    not null references public.tipos_actividad (codigo),
  nombre          text    not null,
  lugar           text    not null default '',
  fecha           date    not null,
  inicio          time    not null,
  fin             time    not null,
  cupo            int     not null check (cupo >= 0),
  cupo_inicial    int     not null check (cupo_inicial >= 0),
  inscritos       int     not null default 0,
  publicada       boolean not null default false,
  descripcion     text    not null default '' check (length(descripcion) <= 400),
  grupo_modo      text    not null default 'ENLACE' check (grupo_modo in ('ENLACE', 'MANUAL')),
  grupo_whatsapp  text    not null default '' check (grupo_whatsapp = '' or grupo_whatsapp like 'https://chat.whatsapp.com/%'),
  creado_por      uuid,
  creado_en       timestamptz not null default now(),
  orden           bigint generated always as identity,
  constraint sin_sobrecupo check (inscritos between 0 and cupo),
  constraint horario_valido check (fin > inicio)
);

-- Pares autorizados aunque se crucen (R-03). Siempre a < b.
create table if not exists public.cruces_permitidos (
  a              text not null references public.actividades (id) on delete cascade,
  b              text not null references public.actividades (id) on delete cascade,
  permitido_por  uuid,
  creado_en      timestamptz not null default now(),
  primary key (a, b),
  check (a < b)
);

-- Inscripciones: una por persona.
create table if not exists public.inscripciones (
  codigo           text primary key,
  documento        text     not null,
  nombre           text     not null,
  correo           text     not null default '',
  etapa            smallint not null,
  celular          text     not null,
  pais             text     not null,
  acepta_whatsapp  boolean  not null check (acepta_whatsapp),             -- R-14
  estado           text     not null default 'CONFIRMADO' check (estado in ('CONFIRMADO', 'ANULADO')),
  origen           text     not null default 'WEB' check (origen in ('WEB', 'PANEL')),
  ronda            int      not null,
  registrado_por   uuid,
  modificado_por   uuid,
  modificado_en    timestamptz,
  creado_en        timestamptz not null default now(),
  orden            bigint generated always as identity
);
-- R-01: un solo registro confirmado por documento.
create unique index if not exists un_confirmado_por_documento on public.inscripciones (documento) where estado = 'CONFIRMADO';
create index if not exists inscripciones_celular on public.inscripciones (celular);

-- Una fila por actividad de cada inscripción (lista para la asistencia del Panel 4).
-- El nombre se guarda como foto para que el CSV siga legible aunque la actividad se quite.
create table if not exists public.inscripcion_actividades (
  codigo            text not null references public.inscripciones (codigo) on delete cascade,
  actividad_id      text not null,
  actividad_nombre  text not null,
  primary key (codigo, actividad_id)
);
create index if not exists inscripcion_actividades_act on public.inscripcion_actividades (actividad_id);

-- Reservada para el Panel 4 (asistencia). Se crea vacía para que el modelo no cambie después.
create table if not exists public.asistencias (
  codigo        text not null,
  actividad_id  text not null,
  marcado_en    timestamptz not null default now(),
  marcado_por   uuid,
  metodo        text not null check (metodo in ('DNI', 'QR', 'MANUAL')),
  observacion   text not null default '',
  primary key (codigo, actividad_id),
  foreign key (codigo, actividad_id) references public.inscripcion_actividades (codigo, actividad_id) on delete cascade
);

-- Equipo de organización: cuenta de Supabase Auth + rol (R-26, R-30).
create table if not exists public.organizadores (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  nombre     text    not null default '',
  rol        text    check (rol in ('propietario', 'admin', 'operador')),   -- null = sin rol
  activo     boolean not null default true,
  creado_en  timestamptz not null default now()
);

-- Límite de intentos (R-25): fallos por dispositivo y por red en ventanas de N minutos.
create table if not exists public.intentos (
  clave    text        not null,     -- 'disp:<id>' o 'red:<ip>'
  ventana  timestamptz not null,
  fallos   int         not null default 0,
  primary key (clave, ventana)
);
create index if not exists intentos_ventana on public.intentos (ventana);

-- Bitácora: cada acción del panel y cada cierre.
create table if not exists public.bitacora (
  id         bigint generated always as identity primary key,
  creado_en  timestamptz not null default now(),
  user_id    uuid,
  quien      text not null,
  accion     text not null,
  detalle    text not null default ''
);

-- Clave del tester (solo funciona en modo PRUEBA). Se guarda su huella, nunca la clave.
create table if not exists privado.claves (
  nombre  text primary key check (nombre in ('ADMIN_KEY')),
  huella  text not null
);

-- ── Seguridad ───────────────────────────────────────────────────────────
alter table public.config                  enable row level security;
alter table public.tipos_actividad         enable row level security;
alter table public.padron                  enable row level security;
alter table public.actividades             enable row level security;
alter table public.cruces_permitidos       enable row level security;
alter table public.inscripciones           enable row level security;
alter table public.inscripcion_actividades enable row level security;
alter table public.asistencias             enable row level security;
alter table public.organizadores           enable row level security;
alter table public.intentos                enable row level security;
alter table public.bitacora                enable row level security;
alter table privado.claves                 enable row level security;

revoke all on public.config, public.tipos_actividad, public.padron, public.actividades, public.cruces_permitidos,
              public.inscripciones, public.inscripcion_actividades, public.asistencias, public.organizadores,
              public.intentos, public.bitacora from anon, authenticated;
revoke all on all tables in schema privado from anon, authenticated;
