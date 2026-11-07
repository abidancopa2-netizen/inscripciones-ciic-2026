/* Tema CIDEIC · Panel: marca el acceso (portada con el logo), interruptor claro/oscuro y tarjetas plegables en Operación.
   Solo cambia clases, el atributo data-tema de <html> y añade botones de plegar (sin data-*). */
(() => {
  const acceso = document.getElementById('vista-login');
  const sync = () => document.body.classList.toggle('en-login', !!acceso && !acceso.hidden);
  sync();
  if (acceso) new MutationObserver(sync).observe(acceso, { attributes: true, attributeFilter: ['hidden'] });

  const html = document.documentElement, btn = document.querySelector('.tema-btn');
  const noche = matchMedia('(prefers-color-scheme: dark)'), quieto = matchMedia('(prefers-reduced-motion: reduce)');
  const actual = () => (html.dataset.tema === 'oscuro' ? 'oscuro' : 'claro');
  const rotulo = () => btn.setAttribute('aria-checked', String(actual() === 'oscuro'));
  let turno = 0;
  // Con View Transitions, fundido de toda la página hecho por la tarjeta gráfica; sin ellas, cambio directo.
  const cambiar = (t, desde) => {
    const poner = () => { html.dataset.tema = t; rotulo(); };
    if (quieto.matches || !desde || !document.startViewTransition) { poner(); return; }
    const mio = ++turno;
    const vt = document.startViewTransition(() => { html.classList.add('tema-vt'); poner(); });
    vt.finished.finally(() => { if (mio === turno) html.classList.remove('tema-vt'); });
  };
  btn.addEventListener('click', () => {
    const t = actual() === 'oscuro' ? 'claro' : 'oscuro';
    cambiar(t, btn);
    try { localStorage.setItem('cideic_tema', t); } catch (e) { /* sin almacenamiento */ }
  });
  noche.addEventListener('change', (e) => {
    let g = null; try { g = localStorage.getItem('cideic_tema'); } catch (er) { /* sin almacenamiento */ }
    if (g !== 'claro' && g !== 'oscuro') cambiar(e.matches ? 'oscuro' : 'claro', null);
  });
  rotulo();

  // El logo del acceso arranca cuando la página terminó de cargar y sus imágenes están decodificadas (tope 1,6 s).
  const lista = () => { if (!html.classList.contains('portada-lista')) requestAnimationFrame(() => requestAnimationFrame(() => html.classList.add('portada-lista'))); };
  const tope = setTimeout(lista, 1600);
  const cargada = new Promise((ok) => (document.readyState === 'complete' ? ok() : addEventListener('load', ok, { once: true })));
  const logos = [...document.querySelectorAll('.portada img')].map((i) => (i.decode ? i.decode().catch(() => {}) : null));
  Promise.all([cargada, ...logos]).then(() => { clearTimeout(tope); lista(); });

  // Operación: cada tarjeta se pliega o despliega desde su título; se recuerda en este navegador.
  const ops = document.querySelector('[data-panel="operacion"]');
  const CLAVE = 'cideic_plegadas';
  let plegadas = [];
  try { plegadas = JSON.parse(localStorage.getItem(CLAVE) || '[]'); } catch (e) { plegadas = []; }
  const guardar = () => { try { localStorage.setItem(CLAVE, JSON.stringify(plegadas)); } catch (e) { /* sin almacenamiento */ } };
  const FLECHA = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
  const poner = (t, b, plegar) => {
    t.classList.toggle('plegada', plegar);
    b.setAttribute('aria-expanded', String(!plegar));
    b.title = plegar ? 'Desplegar' : 'Plegar';
  };
  const alternar = (t, h, b) => {
    const plegar = !t.classList.contains('plegada');
    const nombre = h.textContent.trim();
    plegadas = plegadas.filter((x) => x !== nombre); if (plegar) plegadas.push(nombre); guardar();
    if (quieto.matches || !t.animate) { poner(t, b, plegar); return; }
    const h0 = t.getBoundingClientRect().height;
    poner(t, b, plegar); const h1 = t.getBoundingClientRect().height;
    if (plegar) t.classList.remove('plegada');            // al plegar, el contenido se ve mientras se cierra
    t.style.overflow = 'hidden';
    const a = t.animate([{ height: h0 + 'px' }, { height: h1 + 'px' }], { duration: 320, easing: 'cubic-bezier(.4, 0, .2, 1)' });
    const fin = () => { t.style.overflow = ''; if (plegar) t.classList.add('plegada'); };
    a.onfinish = fin; a.oncancel = fin;
  };
  if (ops) ops.querySelectorAll('.tarjeta').forEach((t) => {
    const h = t.querySelector(':scope > h3');
    if (!h) return;
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'plegar'; b.innerHTML = FLECHA;
    b.setAttribute('aria-label', 'Plegar o desplegar: ' + h.textContent.trim());
    h.classList.add('plegable'); h.after(b);
    poner(t, b, plegadas.includes(h.textContent.trim()));
    b.addEventListener('click', () => alternar(t, h, b));
    h.addEventListener('click', () => alternar(t, h, b));
  });
})();
