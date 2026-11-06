/* ════════════════════════════════════════════════════════════════════════
   CIIC 2026 · Inscripciones · contrato v5.5 · BACKEND DE DEMOSTRACIÓN
   Implementa en el navegador la misma puerta api(p) que la base real, con
   datos de prueba (datos-demo.js), para diseñar y probar index.html y
   panel.html sin Supabase. Es también la REFERENCIA EJECUTABLE del contrato:
   el SQL de los sprints debe responder lo mismo (documentación v5.5).

   · Se activa con MODO: 'demo' en config.js.
   · Guarda el estado en localStorage: la página y el panel abiertos en el
     mismo navegador comparten la misma base de prueba.
   · window.CIIC_DEMO.api(p, ctx) → Promise<respuesta>
       ctx = { dispositivo, red }  (página)   ·   { sesion }  (panel)
   · window.CIIC_DEMO.reiniciar() vuelve a los datos de prueba.
   ════════════════════════════════════════════════════════════════════════ */
(() => {
  'use strict';
  const CLAVE = 'ciic_demo_v55';
  const VERSION = '5.5';
  const D = window.CIIC_DATOS_DEMO;
  if (!D) { console.error('Falta datos-demo.js'); return; }

  // ── utilidades (las mismas reglas que 02_api.sql) ──
  const fallo = (tipo, mensaje, extra) => Object.assign({ ok: false, tipo, mensaje }, extra || {});
  const copia = (x) => JSON.parse(JSON.stringify(x));
  const limpiarDoc = (v) => String(typeof v === 'number' ? Math.round(v) : (v == null ? '' : v)).toUpperCase().replace(/[\s.\-]/g, '');
  const normalizarDoc = (v) => { const s = limpiarDoc(v); return /^\d+$/.test(s) && s.length < 8 ? s.padStart(8, '0') : s; };
  const esDocumento = (s) => /^[A-Z0-9]{6,12}$/.test(s) && /\d/.test(s);
  const limpio = (v, max) => String(v == null ? '' : v).replace(/[\u0000-\u001F\u007F]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, max);
  const esUUID = (s) => /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(s || ''));
  const esCorreo = (s) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(s);
  const PAISES = { PE: '51', CL: '56', CO: '57', EC: '593', BO: '591', AR: '54', MX: '52', BR: '55', VE: '58', PY: '595', UY: '598', ES: '34', US: '1' };
  function celular(pais, valor) {
    const p = String(pais || 'PE').toUpperCase(), cod = PAISES[p];
    if (!cod) return null;
    const crudo = String(valor || '').trim();
    let d = crudo.replace(/\D/g, '');
    if (/^(\+|00)/.test(crudo) || (p === 'PE' && d.length === 11 && d.startsWith('519'))) {
      d = d.replace(/^00/, '');
      if (!d.startsWith(cod)) return null;
      d = d.slice(cod.length);
    }
    if ((p === 'PE' && /^9\d{8}$/.test(d)) || (p !== 'PE' && /^\d{6,14}$/.test(d))) return { numero: '+' + cod + d, pais: p };
    return null;
  }
  const min = (h) => { const [a, b] = h.split(':').map(Number); return a * 60 + b; };
  const claveFecha = (f) => +(f.slice(6) + f.slice(3, 5) + f.slice(0, 2));
  const texto = (e) => !e.length ? 'ninguna etapa' : e.length === 1 ? 'la Etapa ' + e[0] : 'las Etapas ' + e.slice(0, -1).join(', ') + ' y ' + e[e.length - 1];
  const ahoraTxt = () => new Date().toLocaleString('sv-SE', { timeZone: 'America/Lima' });
  const nInscritos = (n) => n + (n === 1 ? ' inscrito' : ' inscritos');
  async function sha256(t) {
    if (!(window.crypto && crypto.subtle)) return 'sin-huella';
    const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(t));
    return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('');
  }

  // ── estado (localStorage) ──
  let S = null;
  function inicial() {
    const s = copia(D.estado);
    s.acts.forEach((a) => { a.inscritos = s.ins.filter((i) => i.estado === 'CONFIRMADO' && i.acts.includes(a.id)).length; });
    s.bit = s.bit || []; s.intentos = {}; s.solicitudes = {}; s.incidencias = []; s.trafico = {}; s.alerta = false; s.pico = 0; s.nInc = 0; s.ultimoRespaldo = null;
    return s;
  }
  function cargar() {
    try { const t = localStorage.getItem(CLAVE); S = t ? JSON.parse(t) : null; } catch (e) { S = null; }
    if (!S || S.version !== VERSION) { S = inicial(); S.version = VERSION; guardar(); }
  }
  function guardar() { try { localStorage.setItem(CLAVE, JSON.stringify(S)); } catch (e) { /* sin almacenamiento: queda en memoria */ } }
  window.addEventListener('storage', (e) => { if (e.key === CLAVE) cargar(); });
  cargar();

  const act = (id) => S.acts.find((a) => a.id === id);
  const confirmada = (doc) => S.ins.find((i) => i.documento === doc && i.estado === 'CONFIRMADO');
  const enPadron = (doc) => S.padron.find((p) => p.documento === doc);
  const par = (a, b) => (a < b ? a + '|' + b : b + '|' + a);
  const cruza = (a, b) => a.fecha === b.fecha && !(min(a.fin) + S.cfg.margenMin <= min(b.inicio) || min(b.fin) + S.cfg.margenMin <= min(a.inicio));
  const ordenar = (lista) => lista.slice().sort((x, y) => claveFecha(x.fecha) - claveFecha(y.fecha) || min(x.inicio) - min(y.inicio) || x.id.localeCompare(y.id));
  function bit(quien, accion, detalle, antes, despues) {
    S.bit.unshift({ fecha: ahoraTxt(), quien, accion, detalle: detalle || '', antes: antes === undefined ? null : antes, despues: despues === undefined ? null : despues });
    if (S.bit.length > 2000) S.bit.length = 2000;
  }
  const cruzaCon = (a) => !S.cfg.mismoDia ? [] : S.acts.filter((x) => x.publicada && x.id !== a.id && !(x.tipo === 'VISITA' && a.tipo === 'VISITA') &&
    cruza(a, x) && !S.cruces.includes(par(a.id, x.id))).map((x) => x.id).sort();
  const publica = (a) => ({ id: a.id, tipo: a.tipo, nombre: a.nombre, lugar: a.lugar, fecha: a.fecha, inicio: a.inicio, fin: a.fin, descripcion: a.descripcion,
    capacidad: a.cupo, inscritos: a.inscritos, disponibles: Math.max(0, a.cupo - a.inscritos), lleno: a.cupo - a.inscritos <= 0, cruzaCon: cruzaCon(a) });
  const publicas = () => ordenar(S.acts.filter((a) => a.publicada)).map(publica);
  const resumen = (a) => ({ id: a.id, tipo: a.tipo, nombre: a.nombre, lugar: a.lugar, fecha: a.fecha, inicio: a.inicio, fin: a.fin, descripcion: a.descripcion,
    grupoModo: a.grupoModo, grupo: a.grupoModo === 'ENLACE' ? (a.grupo || null) : null });
  const cruces = (a) => S.acts.filter((x) => x.id !== a.id && !(x.tipo === 'VISITA' && a.tipo === 'VISITA') && cruza(a, x)).map((x) => x.id);
  const completa = (a) => Object.assign(publica(a), { cupoInicial: a.cupoInicial, publicada: a.publicada, grupoModo: a.grupoModo, grupo: a.grupo, cruces: cruces(a) });
  function listaCruces() {
    const r = [], acts = ordenar(S.acts);
    acts.forEach((a, i) => acts.slice(i + 1).forEach((b) => {
      if (!(a.tipo === 'VISITA' && b.tipo === 'VISITA') && cruza(a, b)) r.push({ a: a.id < b.id ? a.id : b.id, b: a.id < b.id ? b.id : a.id, fecha: a.fecha, permitido: S.cruces.includes(par(a.id, b.id)) });
    }));
    return r;
  }

  // ── cierre avisado (R-27), tráfico (R-34) e intentos (R-25) ──
  function aplicarCierreProgramado() {
    const c = S.cfg;
    if (c.abierto && c.cierreEn && Date.now() >= c.cierreEn) { c.abierto = false; c.ronda += 1; c.cierreEn = null; bit('Sistema', 'Cierre programado', 'ronda ' + (c.ronda - 1) + ' → ' + c.ronda); }
  }
  const segundos = () => S.cfg.abierto && S.cfg.cierreEn ? Math.max(0, Math.ceil((S.cfg.cierreEn - Date.now()) / 1000)) : null;
  const VENTANA = 10000;
  function contarLlamada() {
    const w = Math.floor(Date.now() / VENTANA);
    S.trafico[w] = (S.trafico[w] || 0) + 1;
    Object.keys(S.trafico).forEach((k) => { if (+k < w - 2 * 8640) delete S.trafico[k]; });   // 2 días
    const v = [0, 1, 2, 3].map((k) => S.trafico[w - k] || 0);
    S.pico = Math.max(S.pico || 0, v[0]);
    const sostenida = [v[1], v[2], v[3]].every((x) => x > S.cfg.umbral) || [v[0], v[1], v[2]].every((x) => x > S.cfg.umbral);
    if (sostenida && !S.alerta) { S.alerta = true; bit('Sistema', 'Alerta de saturación', '3 ventanas seguidas sobre ' + S.cfg.umbral); }
    if (S.alerta && v.slice(0, 3).every((x) => x <= S.cfg.umbral)) S.alerta = false;
  }
  const trafico = () => { const w = Math.floor(Date.now() / VENTANA); return { ventana10s: S.trafico[w] || 0, pico10s: S.pico || 0, alerta: !!S.alerta, umbral: S.cfg.umbral }; };
  const ventanaIntentos = () => Math.floor(Date.now() / (S.cfg.ventanaMin * 60000));
  const fallosDe = (k) => { const x = S.intentos[k]; return x && x.v === ventanaIntentos() ? x.n : 0; };
  function frenado(ctx) {
    if (ctx.dispositivo && fallosDe('disp:' + ctx.dispositivo) >= S.cfg.limiteDispositivo) return 'dispositivo';
    if (fallosDe('red:' + (ctx.red || 'demo')) >= S.cfg.limiteRed) return 'red';
    return null;
  }
  function sumarFallo(ctx) {
    const v = ventanaIntentos();
    ['red:' + (ctx.red || 'demo'), ctx.dispositivo ? 'disp:' + ctx.dispositivo : null].filter(Boolean).forEach((k) => {
      S.intentos[k] = { v, n: fallosDe(k) + 1 };
    });
    return ctx.dispositivo ? Math.max(0, S.cfg.limiteDispositivo - fallosDe('disp:' + ctx.dispositivo)) : null;
  }
  const quedan = (r) => r == null ? '' : r > 1 ? ' Te quedan ' + r + ' intentos.' : r === 1 ? ' Te queda 1 intento.' :
    ' Llegaste al límite: espera ' + S.cfg.ventanaMin + ' minutos o escríbenos para ayudarte.';

  // ── participante ──
  const duplicado = () => fallo('duplicado', 'Este documento ya está inscrito. Si necesitas ayuda, escríbenos.');   // R-31: sin datos
  function verificar(entrada, sinDuplicado, ctx) {
    const f = frenado(ctx);
    if (f) return fallo('demasiados_intentos', f === 'dispositivo' ? 'Hiciste ' + S.cfg.limiteDispositivo + ' intentos con documentos que no encontramos. Espera ' + S.cfg.ventanaMin +
      ' minutos o escríbenos para ayudarte.' : 'Hay demasiados intentos fallidos desde tu red. Espera ' + S.cfg.ventanaMin + ' minutos o escríbenos.', { motivo: f, esperaMinutos: S.cfg.ventanaMin });
    if (!esDocumento(limpiarDoc(entrada))) {
      const r = sumarFallo(ctx);
      return fallo('formato', 'Revisa el número: escribe tu DNI de 8 dígitos, o tu carnet de extranjería o pasaporte, sin espacios.' + quedan(r), { intentosRestantes: r });
    }
    const doc = normalizarDoc(entrada);
    if (!sinDuplicado && confirmada(doc)) { if (ctx.dispositivo) delete S.intentos['disp:' + ctx.dispositivo]; return duplicado(); }
    if (!S.cfg.abierto) return fallo('cerrado', 'Las inscripciones están cerradas en este momento. Esta página se actualiza sola cuando abran.');
    const p = enPadron(doc);
    if (!p) {
      const r = sumarFallo(ctx);
      return fallo('no_encontrado', 'No encontramos este documento en el padrón del congreso. Revisa el número o escríbenos.' + quedan(r), { intentosRestantes: r });
    }
    if (ctx.dispositivo) delete S.intentos['disp:' + ctx.dispositivo];
    if (!S.cfg.etapas.includes(p.etapa)) return fallo('etapa_no_habilitada', 'Tu entrada al congreso es de Etapa ' + p.etapa + '. En este momento la inscripción está habilitada para ' +
      texto(S.cfg.etapas) + '. Espera el anuncio oficial.', { etapa: p.etapa });
    const puedeVisita = S.cfg.etapasVisita.includes(p.etapa);
    return { ok: true, tipo: 'ok', doc, etapa: p.etapa, puedeVisita, ronda: S.cfg.ronda,
      mensaje: puedeVisita ? 'Documento verificado · Etapa ' + p.etapa + '.' : 'Documento verificado · Etapa ' + p.etapa +
        '. Por ahora tu etapa se inscribe en 2 talleres: las visitas están habilitadas para ' + texto(S.cfg.etapasVisita) + '.' };
  }
  function combinacion(ids, panel) {
    if (!Array.isArray(ids)) return fallo('combinacion_invalida', 'Elige 2 actividades: una visita y un taller, o dos talleres.', { motivo: 'cantidad' });
    ids = ids.map((x) => String(x || '').trim()).filter(Boolean);
    if (ids.length !== 2 || ids[0] === ids[1]) return fallo('combinacion_invalida', 'Elige 2 actividades: una visita y un taller, o dos talleres.', { motivo: 'cantidad' });
    const sel = ordenar(ids.map(act).filter((a) => a && (a.publicada || panel)));
    if (sel.length !== 2) return fallo('no_disponible', 'Una de las actividades elegidas ya no está disponible. Elige otra combinación.', { actividades: publicas() });
    const visitas = sel.filter((a) => a.tipo === 'VISITA').length;
    if (visitas > 1) return fallo('combinacion_invalida', 'Solo se puede elegir una visita técnica. La otra actividad debe ser un taller.', { motivo: 'dos_visitas' });
    const [a, b] = sel;
    if (a.fecha === b.fecha) {
      if (!S.cfg.mismoDia) return fallo('combinacion_invalida', 'Las 2 actividades deben ser en días distintos: una por día.', { motivo: 'mismo_dia' });
      if (cruza(a, b) && !S.cruces.includes(par(a.id, b.id))) return fallo('combinacion_invalida', '"' + a.nombre + '" (' + a.inicio + '–' + a.fin + ') y "' + b.nombre + '" (' +
        b.inicio + '–' + b.fin + ') se cruzan: entre una y otra debe haber al menos ' + S.cfg.margenMin + ' minutos.', { motivo: 'cruce' });
    }
    return { sel, visitas };
  }
  function nuevoCodigo() {
    const L = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let c;
    do { c = 'CIIC-' + Array.from({ length: 5 }, () => L[Math.floor(Math.random() * L.length)]).join(''); } while (S.ins.some((i) => i.codigo === c));
    return c;
  }
  // En la base real, el trigger de inscripcion_actividades mueve los contadores (R-33).
  function guardar_(doc, datos, etapa, sel, origen, quien) {
    const codigo = nuevoCodigo();
    sel.forEach((a) => { a.inscritos += 1; });
    S.ins.push({ codigo, documento: doc, nombres: datos.nombres, apellidos: datos.apellidos, correo: datos.correo, etapa, celular: datos.celular, pais: datos.pais,
      aceptaPrivacidad: true, aceptaWhatsapp: true, avisoVersion: S.cfg.avisoVersion, estado: 'CONFIRMADO', origen, ronda: S.cfg.ronda,
      registradoPor: quien || null, creado: ahoraTxt(), acts: sel.map((a) => a.id), enGrupo: {} });
    return codigo;
  }
  function datosPersona(b) {
    const nombres = limpio(b.nombres, 60), apellidos = limpio(b.apellidos, 60), correo = limpio(b.correo, 100).toLowerCase();
    if (nombres.length < 2) return fallo('datos_invalidos', 'Escribe tus nombres.', { campo: 'nombres' });
    if (apellidos.length < 2) return fallo('datos_invalidos', 'Escribe tus apellidos.', { campo: 'apellidos' });
    if (!esCorreo(correo)) return fallo('datos_invalidos', 'Escribe tu correo institucional.', { campo: 'correo' });
    const tel = celular(b.pais, b.celular);
    if (!tel) return fallo('celular_invalido', String(b.pais || 'PE').toUpperCase() === 'PE' ? 'Revisa tu celular: en Perú son 9 dígitos y empiezan con 9.' :
      'Revisa tu celular: escribe entre 6 y 14 dígitos, sin el código de país.', { campo: 'celular' });
    if (b.aceptaPrivacidad !== true || b.aceptaWhatsapp !== true) return fallo('sin_consentimiento', 'Para inscribirte necesitamos que aceptes el aviso de privacidad y el contacto por WhatsApp.');
    return { ok: true, nombres, apellidos, correo, celular: tel.numero, pais: tel.pais };
  }
  function registrar(b, ctx) {
    const dp = datosPersona(b);
    if (!dp.ok) return dp;
    const v = verificar(b.dni, true, ctx);
    if (!v.ok) return v;
    if (!S.cfg.abierto) return fallo('cerrado', 'Las inscripciones se cerraron antes de que confirmaras. Tu elección no se guardó.');
    if (b.ronda !== S.cfg.ronda) return fallo('recargar', 'El sistema se actualizó mientras elegías. Vuelve a verificar tu documento para ver las opciones vigentes.', { ronda: S.cfg.ronda });
    const k = combinacion(b.actividades, false);
    if (!k.sel) return k;
    if (k.visitas && !v.puedeVisita) return fallo('visita_no_habilitada', 'Las visitas técnicas están habilitadas para ' + texto(S.cfg.etapasVisita) + '. Elige 2 talleres.');
    if (confirmada(v.doc)) return duplicado();
    const llena = k.sel.find((a) => a.inscritos >= a.cupo);
    if (llena) return fallo('lleno', '"' + llena.nombre + '" se acaba de llenar. Elige otra combinación, por favor.', { actividadId: llena.id, actividades: publicas() });
    if (!k.visitas && !S.cfg.dosTalleres && v.puedeVisita && S.acts.some((a) => a.publicada && a.tipo === 'VISITA' && a.inscritos < a.cupo))
      return fallo('combinacion_invalida', 'Mientras queden visitas con cupo, tu combinación debe incluir una visita técnica.', { motivo: 'falta_visita' });
    guardar_(v.doc, dp, v.etapa, k.sel, 'WEB', null);
    return { ok: true, tipo: 'registrado', doc: v.doc, etapa: v.etapa, celular: dp.celular, actividades: k.sel.map(resumen), mensaje: 'Inscripción confirmada.' };
  }

  // ── panel: sesión y niveles (R-26) ──
  const RANGO = { operador: 1, admin: 2, propietario: 3 };
  const NIVEL = { panel_resumen: 1, panel_participantes: 1, panel_buscar: 1, panel_verificar_celular: 1, panel_lista: 1, panel_grupo_marcar: 1, panel_exportar: 1,
    panel_actividad: 2, panel_crear: 2, panel_editar: 2, panel_quitar: 2, panel_cruce: 2, panel_inscribir: 2, panel_cambiar: 2, panel_anular: 2,
    panel_padron_agregar: 2, panel_padron_quitar: 2, panel_incidencias: 2, panel_sincronizar: 2, panel_registros: 2,
    panel_horarios: 3, panel_equipo: 3, panel_equipo_rol: 3, panel_equipo_activo: 3, panel_respaldo: 3, panel_padron_importar: 3, panel_preparar_produccion: 3,
    panel_vaciar_prueba: 3, panel_actividades_importar: 3 };
  const nivelConfig = (b) => (b.abierto === true || Array.isArray(b.etapas) || Array.isArray(b.etapasVisita) || typeof b.dosTalleres === 'boolean' ||
    b.refresco != null || b.umbral != null || b.limiteDispositivo != null || b.limiteRed != null) ? 3 : 2;
  const ESCRITURAS = new Set(['registrar', 'panel_config', 'panel_actividad', 'panel_anular', 'panel_inscribir', 'panel_cambiar', 'panel_padron_agregar', 'panel_padron_quitar',
    'panel_crear', 'panel_editar', 'panel_quitar', 'panel_horarios', 'panel_cruce', 'panel_equipo_rol', 'panel_equipo_activo', 'panel_grupo_marcar', 'panel_sincronizar',
    'panel_padron_importar', 'panel_preparar_produccion', 'panel_vaciar_prueba', 'panel_actividades_importar']);
  const requiereCierre = () => fallo('requiere_cierre', 'Este cambio quita opciones a quien está eligiendo. Cierra las inscripciones, haz el cambio y vuelve a abrir.');
  function sesion(ctx) {
    const u = S.equipo.find((x) => x.id === ctx.sesion);
    if (!u) return fallo('sin_sesion', 'Inicia sesión para usar el panel.');
    if (!u.activo) return fallo('sin_permiso', 'Tu cuenta está desactivada. Habla con el propietario.');
    if (!u.rol) return fallo('sin_permiso', 'Tu cuenta aún no tiene rol: pide al propietario que te lo asigne en Sistema → Equipo.');
    return { uid: u.id, nombre: u.nombre, rol: u.rol, quien: u.nombre + ' · ' + u.rol };
  }
  function integridad() {
    const d = S.acts.filter((a) => a.inscritos !== S.ins.filter((i) => i.estado === 'CONFIRMADO' && i.acts.includes(a.id)).length).map((a) => a.id);
    return { ok: !d.length, descuadres: d };
  }
  const configJson = () => ({ abierto: S.cfg.abierto, ronda: S.cfg.ronda, cierraEn: segundos(), etapas: S.cfg.etapas.slice(), etapasVisita: S.cfg.etapasVisita.slice(),
    dosTalleres: S.cfg.dosTalleres, mismoDia: S.cfg.mismoDia, margenMin: S.cfg.margenMin, pasoCupo: S.cfg.pasoCupo, refresco: S.cfg.refresco, modo: S.cfg.modo,
    limiteDispositivo: S.cfg.limiteDispositivo, limiteRed: S.cfg.limiteRed, ventanaMin: S.cfg.ventanaMin, umbral: S.cfg.umbral, limiteMasivo: S.cfg.limiteMasivo,
    avisoVersion: S.cfg.avisoVersion });
  const registro = (i) => ({ fecha: i.creado, codigo: i.codigo, doc: i.documento, nombres: i.nombres, apellidos: i.apellidos, correo: i.correo, celular: i.celular,
    etapa: i.etapa, estado: i.estado, origen: i.origen, ronda: i.ronda, actividades: i.acts.map((id) => ({ id, nombre: (act(id) || {}).nombre || id })) });
  function necesitaCupo(sel, yaTiene, ampliar, s) {
    const llenas = sel.filter((a) => !yaTiene.includes(a.id) && a.inscritos >= a.cupo);
    if (!llenas.length) return { llenas: [] };
    if (ampliar !== true) return fallo('advertencia', llenas.map((a) => '"' + a.nombre + '" está llena (' + a.inscritos + '/' + a.cupo + ')').join(' y ') + '. Continuar ampliará su cupo en 1.',
      { accion: 'ampliar_cupo', ids: llenas.map((a) => a.id) });
    llenas.forEach((a) => { bit(s.quien, 'Actividad ' + a.id, 'cupo ampliado en 1', { cupo: a.cupo }, { cupo: a.inscritos + 1 }); a.cupo = a.inscritos + 1; });
    return { llenas };
  }
  function datosActividad(b, base) {
    const d = { tipo: b.tipo != null ? String(b.tipo).toUpperCase() : base.tipo, nombre: b.nombre != null ? limpio(b.nombre, 120) : base.nombre,
      lugar: b.lugar != null ? limpio(b.lugar, 120) : base.lugar, fecha: b.fecha != null ? String(b.fecha).trim() : base.fecha,
      inicio: b.inicio != null ? String(b.inicio).trim() : base.inicio, fin: b.fin != null ? String(b.fin).trim() : base.fin,
      descripcion: b.descripcion != null ? limpio(b.descripcion, 400) : base.descripcion || '', grupoModo: b.grupoModo != null ? String(b.grupoModo).toUpperCase() : base.grupoModo || 'ENLACE',
      grupo: b.grupo != null ? String(b.grupo).trim() : base.grupo || '' };
    if (!S.tipos[d.tipo]) return fallo('datos_invalidos', 'Tipo de actividad desconocido.');
    if (d.nombre.length < 3) return fallo('datos_invalidos', 'Escribe el nombre de la actividad.');
    const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(d.fecha);
    const fecha = m && new Date(+m[3], +m[2] - 1, +m[1]);
    if (!m || fecha.getDate() !== +m[1] || fecha.getMonth() !== +m[2] - 1) return fallo('datos_invalidos', 'La fecha debe escribirse como dd/mm/aaaa.');
    d.fecha = String(m[1]).padStart(2, '0') + '/' + String(m[2]).padStart(2, '0') + '/' + m[3];
    const hora = (h) => { const x = /^(\d{1,2}):(\d{2})$/.exec(h); return x && +x[1] < 24 && +x[2] < 60 ? x[1].padStart(2, '0') + ':' + x[2] : null; };
    d.inicio = hora(d.inicio); d.fin = hora(d.fin);
    if (!d.inicio || !d.fin) return fallo('datos_invalidos', 'Las horas deben escribirse como hh:mm (por ejemplo 08:30).');
    if (min(d.fin) <= min(d.inicio)) return fallo('datos_invalidos', 'La hora de fin debe ser posterior a la de inicio.');
    if (!['ENLACE', 'MANUAL'].includes(d.grupoModo)) return fallo('datos_invalidos', 'Entrega del grupo: ENLACE o MANUAL.');
    if (d.grupo && (!d.grupo.startsWith('https://chat.whatsapp.com/') || d.grupo.length < 32 || /\s/.test(d.grupo)))
      return fallo('enlace_invalido', 'El enlace del grupo debe empezar con https://chat.whatsapp.com/ (cópialo desde WhatsApp → Invitar al grupo mediante enlace).');
    return { datos: d };
  }
  function lista(b) {
    const ids = b.id ? [b.id] : S.acts.map((a) => a.id), etapa = b.etapa ? +b.etapa : null;
    const q = String(b.q || '').trim().toUpperCase(), dig = q.replace(/\D/g, '');
    const filas = [];
    ids.forEach((id) => S.ins.filter((i) => i.estado === 'CONFIRMADO' && i.acts.includes(id) && (!etapa || i.etapa === etapa)).forEach((i) => {
      if (q && !(i.documento.includes(normalizarDoc(q)) || (dig.length >= 6 && i.celular.replace(/\D/g, '').endsWith(dig.slice(-9))) ||
        (i.apellidos + ' ' + i.nombres).toUpperCase().includes(q))) return;
      filas.push({ actividad: id, apellidos: i.apellidos, nombres: i.nombres, doc: i.documento, correo: i.correo, celular: i.celular, etapa: i.etapa,
        codigo: i.codigo, origen: i.origen, enGrupo: !!(i.enGrupo && i.enGrupo[id]) });
    }));
    filas.sort((x, y) => x.actividad.localeCompare(y.actividad) || x.apellidos.localeCompare(y.apellidos, 'es') || x.nombres.localeCompare(y.nombres, 'es'));
    return filas;
  }

  function panel(b, s) {
    const c = S.cfg;
    switch (b.action) {
      case 'panel_resumen': {
        const conf = S.ins.filter((i) => i.estado === 'CONFIRMADO');
        const vis = S.acts.filter((a) => a.tipo === 'VISITA' && a.publicada);
        const v = ventanaIntentos();
        const fallos = Object.entries(S.intentos).filter(([k, x]) => k.startsWith('disp:') && x.v === v).reduce((t, [, x]) => t + x.n, 0);
        const frenados = Object.entries(S.intentos).filter(([k, x]) => x.v === v && ((k.startsWith('disp:') && x.n >= c.limiteDispositivo) || (k.startsWith('red:') && x.n >= c.limiteRed))).length;
        const porCel = {};
        conf.forEach((i) => { (porCel[i.celular] = porCel[i.celular] || []).push({ codigo: i.codigo, doc: i.documento, nombre: i.nombres + ' ' + i.apellidos }); });
        return { ok: true, tipo: 'panel', version: VERSION, hora: ahoraTxt(), sesion: { nombre: s.nombre, rol: s.rol, tester: false }, config: configJson(),
          totales: { inscritos: conf.length, anulados: S.ins.length - conf.length,
            porEtapa: { 1: conf.filter((i) => i.etapa === 1).length, 2: conf.filter((i) => i.etapa === 2).length, 3: conf.filter((i) => i.etapa === 3).length },
            porOrigen: { WEB: conf.filter((i) => i.origen === 'WEB').length, PANEL: conf.filter((i) => i.origen === 'PANEL').length },
            padron: { 1: S.padron.filter((p) => p.etapa === 1).length, 2: S.padron.filter((p) => p.etapa === 2).length, 3: S.padron.filter((p) => p.etapa === 3).length },
            visitas: { ocupados: vis.reduce((t, a) => t + a.inscritos, 0), cupo: vis.reduce((t, a) => t + a.cupo, 0) }, fallos10min: fallos, frenados },
          integridad: integridad(), trafico: trafico(), ultimoRespaldo: S.ultimoRespaldo,
          actividades: ordenar(S.acts).map(completa), cruces: listaCruces(),
          repetidos: Object.entries(porCel).filter(([, l]) => l.length > 1).map(([celular, personas]) => ({ celular, personas })),
          ultimos: conf.slice(-15).reverse().map((i) => ({ fecha: i.creado, codigo: i.codigo, doc: i.documento, nombre: i.nombres + ' ' + i.apellidos, etapa: i.etapa, origen: i.origen, actividades: i.acts.slice() })) };
      }
      case 'panel_config': {
        if (b.abierto === false && c.abierto) {
          if (b.confirmar !== true) return fallo('advertencia', 'Nadie nuevo podrá pasar de la pantalla 1. Quien esté eligiendo y no haya confirmado vuelve al inicio sin inscribirse. Se habilitan los cambios que quitan opciones.', { accion: 'cerrar' });
          c.abierto = false; c.ronda += 1; c.cierreEn = null;
          bit(s.quien, 'Cierre y depuración', 'ronda ' + (c.ronda - 1) + ' → ' + c.ronda);
          return { ok: true, tipo: 'panel', config: configJson() };
        }
        if (b.abierto === true && !c.abierto) { c.abierto = true; bit(s.quien, 'Apertura', 'ronda ' + c.ronda); return { ok: true, tipo: 'panel', config: configJson() }; }
        if (b.avisarCierreMin != null) {
          if (!c.abierto) return fallo('valor_invalido', 'Las inscripciones ya están cerradas.');
          const n = parseInt(b.avisarCierreMin, 10);
          if (!(n >= 1 && n <= 10)) return fallo('valor_invalido', 'El aviso debe ser de 1 a 10 minutos.');
          c.cierreEn = Date.now() + n * 60000; bit(s.quien, 'Aviso de cierre', 'cierre en ' + n + ' min');
          return { ok: true, tipo: 'panel', config: configJson() };
        }
        if (b.cancelarAviso === true) { c.cierreEn = null; bit(s.quien, 'Aviso de cierre', 'cancelado'); return { ok: true, tipo: 'panel', config: configJson() }; }
        const antes = configJson(), cambios = [];
        const lista3 = (x) => [...new Set(x.map(Number).filter((e) => [1, 2, 3].includes(e)))].sort();
        if (Array.isArray(b.etapas)) { const q = lista3(b.etapas); if (c.abierto && c.etapas.some((e) => !q.includes(e))) return requiereCierre(); c.etapas = q; cambios.push('etapas'); }
        if (Array.isArray(b.etapasVisita)) { const q = lista3(b.etapasVisita); if (c.abierto && c.etapasVisita.some((e) => !q.includes(e))) return requiereCierre(); c.etapasVisita = q; cambios.push('etapas con visitas'); }
        if (typeof b.dosTalleres === 'boolean') { if (c.abierto && c.dosTalleres && !b.dosTalleres) return requiereCierre(); c.dosTalleres = b.dosTalleres; cambios.push('2 talleres'); }
        const num = (k, lo, hi, campo, txt) => {
          if (b[k] == null) return null;
          const n = parseInt(b[k], 10);
          if (!(n >= lo && n <= hi)) return fallo('valor_invalido', txt);
          c[campo] = n; cambios.push(campo); return null;
        };
        for (const r of [num('pasoCupo', 1, 100, 'pasoCupo', 'El paso de cupo debe estar entre 1 y 100.'), num('refresco', 10, 120, 'refresco', 'El refresco debe estar entre 10 y 120 segundos.'),
          num('umbral', 100, 100000, 'umbral', 'El umbral debe estar entre 100 y 100000 llamadas por ventana.'), num('limiteDispositivo', 1, 100, 'limiteDispositivo', 'El límite por dispositivo debe estar entre 1 y 100.'),
          num('limiteRed', 1, 100000, 'limiteRed', 'El límite por red debe estar entre 1 y 100000.')]) if (r) return r;
        if (cambios.length) bit(s.quien, 'Configuración', cambios.join(' · '), antes, configJson());
        return { ok: true, tipo: 'panel', config: configJson() };
      }
      case 'panel_actividad': {
        const a = act(b.id);
        if (!a) return fallo('actividad_invalida', 'No existe la actividad ' + b.id + '.');
        if (b.delta != null) return fallo('valor_invalido', 'Envía el cupo final (cupo), no un incremento.');
        let cupo = b.cupo != null ? parseInt(b.cupo, 10) : a.cupo;
        if (!(cupo >= 1)) return fallo('cupo_invalido', 'El cupo debe ser un número mayor que 0.');
        if (c.abierto && (cupo < a.cupo || (b.publicada === false && a.publicada))) return requiereCierre();
        const antes = { cupo: a.cupo, publicada: a.publicada };
        if (cupo !== a.cupo) {
          if (cupo < a.inscritos) {
            if (b.confirmar !== true) return fallo('advertencia', '"' + a.nombre + '" tiene ' + nInscritos(a.inscritos) + '. No se puede bajar a ' + cupo + ' sin anular a ' + (a.inscritos - cupo) +
              ' personas. Puedes dejarla en ' + a.inscritos + ': queda llena y no entra nadie más.', { accion: 'cerrar_cupo', minimo: a.inscritos });
            cupo = a.inscritos;
          }
          a.cupo = cupo;
        }
        if (typeof b.publicada === 'boolean') a.publicada = b.publicada;
        if (antes.cupo !== a.cupo || antes.publicada !== a.publicada) bit(s.quien, 'Actividad ' + a.id, 'cupo o visibilidad', antes, { cupo: a.cupo, publicada: a.publicada });
        return { ok: true, tipo: 'panel', actividad: completa(a) };
      }
      case 'panel_buscar': {
        const q = String(b.q || '').trim(), doc = normalizarDoc(q), dig = q.replace(/\D/g, '');
        const porCel = dig.length >= 7 && !/[A-Za-z]/.test(q) && (q.startsWith('+') || dig.length >= 9);
        const p = enPadron(doc);
        return { ok: true, tipo: 'panel', doc, etapa: p ? p.etapa : null, porCelular: porCel,
          registros: S.ins.filter((i) => i.documento === doc || (porCel && i.celular.replace(/\D/g, '').endsWith(dig))).map(registro) };
      }
      case 'panel_anular': {
        const i = S.ins.find((x) => x.codigo === String(b.codigo || '').toUpperCase() && x.estado === 'CONFIRMADO');
        if (!i) return fallo('no_encontrado', 'No hay una inscripción confirmada con el código ' + b.codigo + '.');
        i.estado = 'ANULADO'; i.acts.forEach((id) => { const a = act(id); if (a) a.inscritos = Math.max(0, a.inscritos - 1); });
        bit(s.quien, 'Anulación', i.codigo + ' · ' + i.documento + ' · libera ' + i.acts.join(' y '));
        return { ok: true, tipo: 'panel', codigo: i.codigo };
      }
      case 'panel_inscribir': {
        const doc = normalizarDoc(b.dni);
        if (!esDocumento(doc)) return fallo('formato', 'Revisa el documento: 6 a 12 letras y números.');
        const p = enPadron(doc);
        if (!p) return fallo('no_encontrado', 'Este documento no está en el padrón. Agrégalo primero en Participantes.');
        const ya = confirmada(doc);
        if (ya) return fallo('duplicado', 'Ya tiene una inscripción confirmada (' + ya.codigo + '). Usa "Cambiar inscripción".');
        const dp = datosPersona(b);
        if (!dp.ok) return dp;
        const k = combinacion(b.actividades, true);
        if (!k.sel) return k;
        const n = necesitaCupo(k.sel, [], b.ampliarCupo, s);
        if (!n.llenas) return n;
        const codigo = guardar_(doc, dp, p.etapa, k.sel, 'PANEL', s.uid);
        bit(s.quien, 'Inscripción desde el panel', codigo + ' · ' + doc + ' · ' + k.sel.map((a) => a.id).join(' + '));
        return { ok: true, tipo: 'registrado', origen: 'PANEL', codigo, doc, etapa: p.etapa, celular: dp.celular, ampliadas: n.llenas.map((a) => a.id),
          actividades: k.sel.map(resumen), mensaje: 'Inscrito con el código ' + codigo + '.' };
      }
      case 'panel_cambiar': {
        const i = S.ins.find((x) => x.codigo === String(b.codigo || '').toUpperCase() && x.estado === 'CONFIRMADO');
        if (!i) return fallo('no_encontrado', 'No hay una inscripción confirmada con el código ' + b.codigo + '.');
        const k = combinacion(b.actividades, true);
        if (!k.sel) return k;
        const nuevas = k.sel.map((a) => a.id);
        if (nuevas.slice().sort().join() === i.acts.slice().sort().join()) return fallo('sin_cambios', 'Es la misma combinación que ya tiene.');
        const n = necesitaCupo(k.sel, i.acts, b.ampliarCupo, s);
        if (!n.llenas) return n;
        const antes = i.acts.slice();
        antes.filter((id) => !nuevas.includes(id)).forEach((id) => { act(id).inscritos -= 1; delete i.enGrupo[id]; });
        nuevas.filter((id) => !antes.includes(id)).forEach((id) => { act(id).inscritos += 1; });
        i.acts = nuevas;
        bit(s.quien, 'Cambio de inscripción', i.codigo, antes, nuevas);
        return { ok: true, tipo: 'panel', codigo: i.codigo, antes, ahora: nuevas, ampliadas: n.llenas.map((a) => a.id) };
      }
      case 'panel_participantes': {
        const q = String(b.q || '').trim().toUpperCase(), porDoc = new Map();
        S.ins.forEach((x) => { const y = porDoc.get(x.documento); if (!y || (x.estado === 'CONFIRMADO' && y.estado !== 'CONFIRMADO')) porDoc.set(x.documento, x); });
        const base = S.padron.filter((p) => !b.etapa || p.etapa === +b.etapa).map((p) => {
          const i = porDoc.get(p.documento);
          return { doc: p.documento, etapa: p.etapa, origen: p.origen, nombre: i ? i.apellidos + ', ' + i.nombres : '', estado: i ? i.estado : 'SIN_INSCRIBIR',
            codigo: i ? i.codigo : null, actividades: i ? i.acts.slice() : [] };
        }).filter((f) => !q || f.doc.includes(normalizarDoc(q)) || f.nombre.toUpperCase().includes(q));
        const filtrado = base.filter((f) => !b.estado || f.estado === b.estado);
        const pag = Math.max(1, parseInt(b.pagina, 10) || 1);
        return { ok: true, tipo: 'panel', total: filtrado.length, pagina: pag, porPagina: 50,
          resumen: { padron: base.length, inscritos: base.filter((f) => f.estado === 'CONFIRMADO').length, sinInscribir: base.filter((f) => f.estado === 'SIN_INSCRIBIR').length,
            agregados: base.filter((f) => f.origen === 'PANEL').length }, filas: filtrado.slice((pag - 1) * 50, pag * 50) };
      }
      case 'panel_padron_agregar': {
        const doc = normalizarDoc(b.documento), etapa = +b.etapa;
        if (!esDocumento(doc)) return fallo('formato', 'Revisa el documento: 6 a 12 letras y números.');
        if (![1, 2, 3].includes(etapa)) return fallo('valor_invalido', 'Elige la etapa de venta: 1, 2 o 3.');
        const ya = enPadron(doc);
        if (ya) return fallo('ya_existe', 'El documento ' + doc + ' ya está en el padrón con la Etapa ' + ya.etapa + '. La etapa no se cambia: si es un error, quítalo (sin inscripción y con el sistema cerrado) y vuelve a agregarlo.', { etapa: ya.etapa });
        S.padron.push({ documento: doc, etapa, origen: 'PANEL', datos: null });
        bit(s.quien, 'Padrón', 'agregado ' + doc + ' a la Etapa ' + etapa);
        return { ok: true, tipo: 'panel', doc, etapa };
      }
      case 'panel_padron_quitar': {
        const doc = normalizarDoc(b.documento);
        if (c.abierto) return requiereCierre();
        if (confirmada(doc)) return fallo('tiene_inscripcion', 'Esta persona tiene una inscripción confirmada: anúlala primero.');
        const n = S.padron.length;
        S.padron = S.padron.filter((p) => p.documento !== doc);
        if (S.padron.length === n) return fallo('no_encontrado', 'No está en el padrón.');
        bit(s.quien, 'Padrón', 'quitado ' + doc);
        return { ok: true, tipo: 'panel', doc };
      }
      case 'panel_padron_importar': {   // R-42: documento y etapa; no cambia etapas existentes
        const filas = Array.isArray(b.filas) ? b.filas : [];
        if (!filas.length || filas.length > 10000) return fallo('valor_invalido', 'Envía entre 1 y 10 000 filas.');
        const r = { agregados: 0, existentes: 0, conflictos: [], invalidos: [] }, vistos = new Map();
        filas.forEach((f, k) => {
          const doc = normalizarDoc(f.documento), m = /([123])\s*$/.exec(String(f.etapa == null ? '' : f.etapa).trim()), etapa = m ? +m[1] : NaN;
          if (!esDocumento(doc) || ![1, 2, 3].includes(etapa)) { r.invalidos.push({ fila: k + 1, documento: String(f.documento || ''), etapa: String(f.etapa || '') }); return; }
          const ya = enPadron(doc) || (vistos.has(doc) ? { etapa: vistos.get(doc) } : null);
          if (!vistos.has(doc)) vistos.set(doc, ya ? ya.etapa : etapa);
          if (ya) { if (ya.etapa === etapa) r.existentes++; else r.conflictos.push({ documento: doc, etapaActual: ya.etapa, etapaPedida: etapa }); return; }
          S.padron.push({ documento: doc, etapa, origen: 'PANEL', datos: null }); r.agregados++;
        });
        bit(s.quien, 'Importar padrón', r.agregados + ' agregados · ' + r.existentes + ' ya existían · ' + r.conflictos.length + ' conflictos · ' + r.invalidos.length + ' inválidos');
        return Object.assign({ ok: true, tipo: 'panel' }, r, { invalidos: r.invalidos.slice(0, 200), conflictos: r.conflictos.slice(0, 200),
          totalConflictos: r.conflictos.length, totalInvalidos: r.invalidos.length });
      }
      case 'panel_crear': {
        const v = datosActividad(b, { tipo: 'TALLER', nombre: '', lugar: '', fecha: '', inicio: '', fin: '' });
        if (!v.datos) return v;
        const cupo = parseInt(b.cupo, 10);
        if (!(cupo >= 1 && cupo <= 1000)) return fallo('cupo_invalido', 'El cupo inicial debe estar entre 1 y 1000.');
        const pref = v.datos.tipo === 'VISITA' ? 'VIS' : v.datos.tipo === 'TALLER' ? 'TAL' : v.datos.tipo.slice(0, 3);
        const n = S.acts.filter((a) => new RegExp('^' + pref + '\\d+$').test(a.id)).reduce((m, a) => Math.max(m, +a.id.slice(pref.length)), 0) + 1;
        const a = Object.assign({ id: pref + String(n).padStart(2, '0'), cupo, cupoInicial: cupo, inscritos: 0, publicada: false }, v.datos);
        S.acts.push(a);
        bit(s.quien, 'Actividad ' + a.id, 'creada (oculta): ' + a.tipo + ' · ' + a.nombre + ' · ' + a.fecha + ' ' + a.inicio + '–' + a.fin + ' · cupo ' + cupo);
        return { ok: true, tipo: 'panel', actividad: completa(a), cruces: cruces(a) };
      }
      case 'panel_editar': {
        const a = act(b.id);
        if (!a) return fallo('actividad_invalida', 'No existe la actividad ' + b.id + '.');
        const v = datosActividad(b, a);
        if (!v.datos) return v;
        const toca = ['tipo', 'fecha', 'inicio', 'fin'].some((k) => v.datos[k] !== a[k]);
        if (toca && a.inscritos > 0) return fallo('tiene_inscritos', '"' + a.nombre + '" ya tiene ' + nInscritos(a.inscritos) + ': su tipo, fecha y horario quedan fijos. Si de verdad cambia, crea otra actividad y mueve a cada persona con "Cambiar inscripción".');
        if (toca && a.publicada && c.abierto) return requiereCierre();
        const antes = copia(a);
        Object.assign(a, v.datos);
        const cambios = Object.keys(v.datos).filter((k) => antes[k] !== a[k]);
        if (cambios.length) bit(s.quien, 'Actividad ' + a.id, 'editado: ' + cambios.join(', '));
        return { ok: true, tipo: 'panel', actividad: completa(a), cruces: cruces(a) };
      }
      case 'panel_quitar': {
        const a = act(b.id);
        if (!a) return fallo('actividad_invalida', 'No existe la actividad ' + b.id + '.');
        if (a.inscritos > 0) return fallo('tiene_inscritos', '"' + a.nombre + '" tiene ' + nInscritos(a.inscritos) + ': no se puede quitar.');
        if (a.publicada) return fallo('esta_visible', 'Ocúltala primero en Operación (requiere cerrar inscripciones).');
        S.acts = S.acts.filter((x) => x.id !== a.id);
        S.cruces = S.cruces.filter((k) => !k.split('|').includes(a.id));
        bit(s.quien, 'Actividad ' + a.id, 'quitada: ' + a.tipo + ' · ' + a.nombre);
        return { ok: true, tipo: 'panel', id: a.id };
      }
      case 'panel_horarios': {
        if (b.mismoDia === false && c.mismoDia && c.abierto) return requiereCierre();
        const antes = { mismoDia: c.mismoDia, margenMin: c.margenMin };
        if (b.margenMin != null) {
          const m = parseInt(b.margenMin, 10);
          if (!(m >= 0 && m <= 240)) return fallo('valor_invalido', 'El margen debe estar entre 0 y 240 minutos.');
          if (m > c.margenMin && c.abierto) return requiereCierre();
          c.margenMin = m;
        }
        if (typeof b.mismoDia === 'boolean') c.mismoDia = b.mismoDia;
        bit(s.quien, 'Horarios', 'mismo día y margen', antes, { mismoDia: c.mismoDia, margenMin: c.margenMin });
        return { ok: true, tipo: 'panel', mismoDia: c.mismoDia, margenMin: c.margenMin, cruces: listaCruces() };
      }
      case 'panel_cruce': {
        const x = act(b.a), y = act(b.b);
        if (!x || !y || x === y) return fallo('actividad_invalida', 'Elige dos actividades existentes y distintas.');
        const k = par(x.id, y.id);
        if (b.permitido === true) { if (!S.cruces.includes(k)) S.cruces.push(k); } else {
          if (S.cruces.includes(k) && c.abierto) return requiereCierre();
          S.cruces = S.cruces.filter((z) => z !== k);
        }
        bit(s.quien, 'Cruce ' + k.replace('|', ' × '), b.permitido === true ? 'permitido' : 'bloqueado');
        return { ok: true, tipo: 'panel', a: k.split('|')[0], b: k.split('|')[1], permitido: b.permitido === true };
      }
      case 'panel_verificar_celular': {
        const a = act(b.id);
        if (!a) return fallo('actividad_invalida', 'Elige la actividad del grupo.');
        const dig = String(b.celular || '').replace(/\D/g, '');
        if (dig.length < 9) return fallo('celular_invalido', 'Escribe el celular que aparece en la solicitud (al menos 9 dígitos).');
        const i = S.ins.find((x) => x.estado === 'CONFIRMADO' && x.acts.includes(a.id) && x.celular.replace(/\D/g, '').endsWith(dig.slice(-9)));
        return { ok: true, tipo: 'panel', id: a.id, inscrito: !!i, nombre: i ? i.nombres + ' ' + i.apellidos : null, codigo: i ? i.codigo : null };
      }
      case 'panel_lista': {
        const filas = lista(b);
        return { ok: true, tipo: 'panel', total: filas.length, pendientes: filas.filter((f) => !f.enGrupo).length, filas };
      }
      case 'panel_grupo_marcar': {
        const a = act(b.id);
        if (!a) return fallo('actividad_invalida', 'Elige la actividad.');
        let n = 0;
        (Array.isArray(b.codigos) ? b.codigos : []).forEach((cod) => {
          const i = S.ins.find((x) => x.codigo === cod && x.acts.includes(a.id) && x.estado === 'CONFIRMADO');
          if (i) { i.enGrupo[a.id] = b.agregado !== false; n++; }
        });
        bit(s.quien, 'Grupo ' + a.id, n + (b.agregado !== false ? ' marcados en el grupo' : ' marcados por agregar'));
        return { ok: true, tipo: 'panel', id: a.id, marcados: n, agregado: b.agregado !== false };
      }
      case 'panel_exportar': {   // nivel 1 · solo lee · queda en la bitácora (R-39)
        const filas = lista({ id: b.id || null, etapa: b.etapa || null });
        bit(s.quien, 'Exportación', 'CSV · actividad ' + (b.id || 'todas') + ' · etapa ' + (b.etapa || 'todas') + ' · ' + filas.length + ' filas');
        return { ok: true, tipo: 'panel', encabezados: ['Actividad', 'Nombre de la actividad', 'Fecha', 'Horario', 'DNI', 'Apellidos', 'Nombres', 'Correo', 'Celular', 'Etapa', 'Código', 'Origen', 'En el grupo'],
          filas: filas.map((f) => { const a = act(f.actividad); return [f.actividad, a.nombre, a.fecha, a.inicio + '–' + a.fin, f.doc, f.apellidos, f.nombres, f.correo, f.celular, String(f.etapa), f.codigo, f.origen, f.enGrupo ? 'SI' : 'NO']; }) };
      }
      case 'panel_registros': {
        if (b.formato === 'padron') {
          bit(s.quien, 'Exportación', 'CSV del padrón · ' + S.padron.length + ' filas');
          return { ok: true, tipo: 'panel', encabezados: ['Documento', 'Etapa', 'Origen', 'Estado', 'Código'],
            filas: S.padron.map((p) => { const i = confirmada(p.documento); return [p.documento, String(p.etapa), p.origen, i ? 'CONFIRMADO' : 'SIN_INSCRIBIR', i ? i.codigo : '']; }) };
        }
        bit(s.quien, 'Exportación', 'CSV de inscripciones · ' + S.ins.length + ' filas');
        return { ok: true, tipo: 'panel', encabezados: ['Fecha/Hora', 'Código', 'Documento', 'Apellidos', 'Nombres', 'Correo', 'Celular', 'País', 'Etapa', 'ID Actividad 1', 'Actividad 1', 'ID Actividad 2', 'Actividad 2', 'Estado', 'Origen', 'Ronda'],
          filas: S.ins.map((i) => { const a = ordenar(i.acts.map(act).filter(Boolean)); return [i.creado, i.codigo, i.documento, i.apellidos, i.nombres, i.correo, i.celular, i.pais, String(i.etapa),
            a[0] ? a[0].id : '', a[0] ? a[0].nombre : '', a[1] ? a[1].id : '', a[1] ? a[1].nombre : '', i.estado, i.origen, String(i.ronda)]; }) };
      }
      case 'panel_sincronizar': {
        S.acts.forEach((a) => { a.inscritos = S.ins.filter((i) => i.estado === 'CONFIRMADO' && i.acts.includes(a.id)).length; });
        bit(s.quien, 'Recontar inscritos', 'contadores recalculados desde las inscripciones');
        return { ok: true, tipo: 'panel', integridad: integridad() };
      }
      case 'panel_incidencias': return { ok: true, tipo: 'panel', incidencias: S.incidencias.slice(0, 50) };
      case 'panel_equipo': return { ok: true, tipo: 'panel', cuentas: S.equipo.map((u) => ({ usuario: u.id, correo: u.correo, nombre: u.nombre, rol: u.rol, activo: u.activo, totp: u.totp })) };
      case 'panel_equipo_rol': {
        const u = S.equipo.find((x) => x.id === b.usuario);
        if (!u) return fallo('no_encontrado', 'No existe esa cuenta.');
        if (b.rol === 'propietario') return fallo('no_permitido', 'El propietario es único (el creador) y solo se asigna en SQL.');
        if (u.rol === 'propietario') return fallo('no_permitido', 'La cuenta del propietario no se modifica desde el panel.');
        const rol = [null, '', 'operador', 'admin'].includes(b.rol) ? (b.rol || null) : undefined;
        if (rol === undefined) return fallo('valor_invalido', 'Rol desconocido.');
        const antes = { rol: u.rol, nombre: u.nombre };
        u.rol = rol; if (b.nombre != null && limpio(b.nombre, 80)) u.nombre = limpio(b.nombre, 80);
        bit(s.quien, 'Equipo', u.correo, antes, { rol: u.rol, nombre: u.nombre });
        return { ok: true, tipo: 'panel', usuario: u.id, rol };
      }
      case 'panel_equipo_activo': {
        const u = S.equipo.find((x) => x.id === b.usuario);
        if (!u) return fallo('no_encontrado', 'No existe esa cuenta.');
        if (u.rol === 'propietario') return fallo('no_permitido', 'La cuenta del propietario no se desactiva desde el panel.');
        const antes = { activo: u.activo };
        u.activo = b.activo === true;
        bit(s.quien, 'Equipo', u.correo, antes, { activo: u.activo });
        return { ok: true, tipo: 'panel', usuario: u.id, activo: u.activo };
      }
      case 'panel_preparar_produccion': {   // R-43
        if (c.modo !== 'PRUEBA') return fallo('modo_produccion', 'La base ya está en modo PRODUCCION.');
        if (c.abierto) return requiereCierre();
        if (String(b.llave || '') !== 'PRODUCCION') return fallo('valor_invalido', 'Para confirmar, escribe PRODUCCION.');
        const n = S.ins.length;
        S.ins = []; S.bit = []; S.intentos = {}; S.solicitudes = {}; S.trafico = {}; S.incidencias = []; S.alerta = false; S.pico = 0;
        S.acts.forEach((a) => { a.inscritos = 0; });
        c.modo = 'PRODUCCION';
        bit(s.quien, 'Pasar a producción', n + ' inscripciones de prueba eliminadas · clave del tester borrada · padrón y actividades intactos');
        return { ok: true, tipo: 'panel', eliminadas: n, config: configJson() };
      }
      case 'panel_vaciar_prueba': {   // R-44: deja la base vacía para cargar los datos reales; conserva configuración y equipo
        if (c.modo !== 'PRUEBA') return fallo('modo_produccion', 'Solo se puede vaciar en modo PRUEBA.');
        if (c.abierto) return requiereCierre();
        if (String(b.llave || '') !== 'VACIAR') return fallo('valor_invalido', 'Para confirmar, escribe VACIAR.');
        const n = { padron: S.padron.length, actividades: S.acts.length, inscripciones: S.ins.length };
        S.padron = []; S.acts = []; S.cruces = []; S.ins = []; S.bit = []; S.intentos = {}; S.solicitudes = {}; S.trafico = {}; S.incidencias = []; S.alerta = false; S.pico = 0;
        bit(s.quien, 'Vaciar datos de prueba', n.padron + ' en el padrón, ' + n.actividades + ' actividades y ' + n.inscripciones + ' inscripciones eliminadas · configuración y equipo intactos');
        return { ok: true, tipo: 'panel', eliminados: n };
      }
      case 'panel_actividades_importar': {   // R-45: catálogo desde CSV; no modifica las que ya existen
        const filas = Array.isArray(b.filas) ? b.filas : [];
        if (!filas.length || filas.length > 500) return fallo('valor_invalido', 'Envía entre 1 y 500 actividades.');
        const r = { agregadas: 0, existentes: [], invalidas: [] };
        filas.forEach((f, k) => {
          const id = String(f.id || '').trim();
          if (id && !/^[A-Za-z0-9_-]{1,20}$/.test(id)) { r.invalidas.push({ fila: k + 1, motivo: 'ID inválido: usa letras, números, guion o guion bajo (hasta 20).' }); return; }
          if (id && act(id)) { r.existentes.push(id); return; }
          const v = datosActividad({ tipo: f.tipo, nombre: f.nombre, lugar: f.lugar || '', fecha: f.fecha, inicio: f.inicio, fin: f.fin, descripcion: f.descripcion || '',
            grupoModo: f.entrega || 'ENLACE', grupo: f.enlace || '' }, { tipo: 'TALLER', nombre: '', lugar: '', fecha: '', inicio: '', fin: '' });
          if (!v.datos) { r.invalidas.push({ fila: k + 1, motivo: v.mensaje }); return; }
          const cupo = parseInt(f.cupo, 10);
          if (!(cupo >= 1 && cupo <= 1000)) { r.invalidas.push({ fila: k + 1, motivo: 'El cupo debe estar entre 1 y 1000.' }); return; }
          const pref = v.datos.tipo === 'VISITA' ? 'VIS' : v.datos.tipo === 'TALLER' ? 'TAL' : v.datos.tipo.slice(0, 3);
          const nuevo = id || pref + String(S.acts.filter((a) => new RegExp('^' + pref + '\\d+$').test(a.id)).reduce((m, a) => Math.max(m, +a.id.slice(pref.length)), 0) + 1).padStart(2, '0');
          const visible = /^(SI|SÍ|S|1|TRUE|VERDADERO)$/i.test(String(f.visible || '').trim());
          S.acts.push(Object.assign({ id: nuevo, cupo, cupoInicial: cupo, inscritos: 0, publicada: visible }, v.datos));
          r.agregadas++;
        });
        bit(s.quien, 'Importar actividades', r.agregadas + ' agregadas · ' + r.existentes.length + ' ya existían · ' + r.invalidas.length + ' inválidas');
        return Object.assign({ ok: true, tipo: 'panel' }, r);
      }
      default: return fallo('accion_invalida', 'Acción no reconocida.');
    }
  }

  async function respaldo(s) {   // R-41
    const tablas = { config: configJson(), tipos_actividad: copia(S.tipos), padron: copia(S.padron), actividades: copia(S.acts), cruces_permitidos: copia(S.cruces),
      inscripciones: copia(S.ins), organizadores: S.equipo.map((u) => ({ usuario: u.id, nombre: u.nombre, rol: u.rol, activo: u.activo })), bitacora: copia(S.bit), incidencias: copia(S.incidencias) };
    const cuerpo = JSON.stringify(tablas);
    const r = { ok: true, tipo: 'panel', version: VERSION, generadoEn: ahoraTxt(), generadoPor: s.quien,
      filas: Object.fromEntries(Object.entries(tablas).map(([k, v]) => [k, Array.isArray(v) ? v.length : 1])), huella: await sha256(cuerpo), tablas };
    S.ultimoRespaldo = { fecha: r.generadoEn, quien: s.quien, bytes: cuerpo.length };
    bit(s.quien, 'Respaldo', 'descargado · ' + Math.round(cuerpo.length / 1024) + ' KB');
    return r;
  }

  // ── LA PUERTA ──
  async function api(p, ctx) {
    ctx = ctx || {};
    await new Promise((r) => setTimeout(r, 120 + Math.random() * 180));   // latencia de red simulada
    cargar();
    contarLlamada();
    aplicarCierreProgramado();
    let r;
    try {
      if (!p || typeof p !== 'object') r = fallo('peticion_invalida', 'Petición inválida.');
      else if (p.action === 'prueba_error') throw new Error('division by zero (error de ejemplo)');
      else if (p.action === 'estado') r = Object.assign({ ok: true, tipo: 'estado', abierto: S.cfg.abierto, ronda: S.cfg.ronda, cierraEn: segundos(), etapas: S.cfg.etapas.slice(),
        etapasVisita: S.cfg.etapasVisita.slice(), mismoDia: S.cfg.mismoDia, margenMin: S.cfg.margenMin, dosTalleres: S.cfg.dosTalleres, refresco: S.cfg.refresco,
        modo: S.cfg.modo, version: VERSION, hora: ahoraTxt() }, p.conActividades ? { actividades: publicas() } : {});
      else if (p.action === 'actividades') r = { ok: true, tipo: 'actividades', actividades: publicas() };
      else if (p.action === 'verificar') { r = verificar(p.dni, false, ctx); if (r.ok) r.actividades = publicas(); }
      else if (/^panel_/.test(p.action) || p.action === 'registrar') {
        let s = null, actor;
        if (p.action === 'registrar') actor = 'doc:' + normalizarDoc(p.dni);
        else {
          s = sesion(ctx);
          if (s.tipo) { guardar(); return s; }
          const nivel = p.action === 'panel_config' ? nivelConfig(p) : (NIVEL[p.action] || 3);
          if (RANGO[s.rol] < nivel) { guardar(); return fallo('sin_permiso', 'Esta acción ' + (nivel === 3 ? 'es del propietario' : 'requiere rol admin o superior') + '.', { nivel }); }
          actor = 'uid:' + s.uid;
        }
        if (ESCRITURAS.has(p.action)) {   // R-32: idempotencia con ámbito
          if (!esUUID(p.solicitud)) { guardar(); return fallo('valor_invalido', 'Falta la solicitud (UUID) de esta operación.'); }
          const clave = actor + '|' + p.action + '|' + p.solicitud;
          const huella = JSON.stringify(Object.assign({}, p, { solicitud: undefined, dispositivo: undefined }));
          Object.keys(S.solicitudes).forEach((k) => { if (Date.now() - S.solicitudes[k].t > 86400000) delete S.solicitudes[k]; });
          const previa = S.solicitudes[clave];
          if (previa) { guardar(); return previa.huella === huella ? Object.assign({}, previa.r, { repetida: true }) : fallo('solicitud_repetida', 'Esta solicitud ya se usó con otros datos. Vuelve a intentarlo.'); }
          r = p.action === 'registrar' ? registrar(p, ctx) : panel(p, s);
          if (r.ok) S.solicitudes[clave] = { huella, r, t: Date.now() };
        } else r = p.action === 'panel_respaldo' ? await respaldo(s) : panel(p, s);
      } else r = fallo('accion_invalida', 'Acción no reconocida.');
    } catch (e) {   // R-36: solo el número; el detalle queda privado
      const id = 'INC-' + String(++S.nInc).padStart(4, '0');
      S.incidencias.unshift({ id, fecha: ahoraTxt(), accion: p && p.action, detalle: String(e.message) });
      r = fallo('error_servidor', 'Ocurrió un error en el sistema. Intenta de nuevo en unos segundos.', { incidencia: id });
    }
    guardar();
    return copia(r);
  }

  window.CIIC_DEMO = {
    api,
    reiniciar() { S = inicial(); S.version = VERSION; guardar(); },
    documentosDePrueba: D.documentosDePrueba,
    cuentas: () => S.equipo.map((u) => ({ id: u.id, nombre: u.nombre, rol: u.rol, activo: u.activo })),
    _estado: () => S,
  };
})();
