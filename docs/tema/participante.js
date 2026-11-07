/* Tema CIDEIC v3.1: modo "inicio" (escena completa) en la pantalla 1 o el acceso al panel, e interruptor claro/oscuro.
   Solo cambia una clase de <body> y el atributo data-tema de <html>. */
(() => {
  const vistas = [...document.querySelectorAll('[data-pantalla="1"]')];
  if (!vistas.length && document.getElementById('vista-login')) vistas.push(document.getElementById('vista-login'));
  const sync = () => document.body.classList.toggle('en-inicio', vistas.some((v) => !v.hidden));
  sync();
  const obs = new MutationObserver(sync);
  vistas.forEach((v) => obs.observe(v, { attributes: true, attributeFilter: ['hidden'] }));

  const html = document.documentElement, btn = document.querySelector('.tema-btn');
  const luz = matchMedia('(prefers-color-scheme: light)'), quieto = matchMedia('(prefers-reduced-motion: reduce)');
  const actual = () => (html.dataset.tema === 'claro' ? 'claro' : 'oscuro');
  const rotulo = () => btn.setAttribute('aria-checked', String(actual() === 'oscuro'));
  let turno = 0;
  // Cambia de modo: con View Transitions, fundido de toda la página hecho por la tarjeta gráfica;
  // sin ellas, los colores se funden. La escena siempre funde sus dos versiones (ya cargadas).
  const cambiar = (t, desde) => {
    const poner = () => { html.dataset.tema = t; rotulo(); };
    if (quieto.matches) { poner(); return; }
    if (desde && document.startViewTransition) {
      const mio = ++turno;
      const vt = document.startViewTransition(() => { html.classList.add('tema-vt'); poner(); });
      vt.finished.finally(() => { if (mio === turno) html.classList.remove('tema-vt'); });
      return;
    }
    poner();
  };
  btn.addEventListener('click', () => {
    const t = actual() === 'claro' ? 'oscuro' : 'claro';
    cambiar(t, btn);
    try { localStorage.setItem('cideic_tema', t); } catch (e) { /* sin almacenamiento */ }
  });
  // Sin elección guardada, sigue al sistema (también con fundido).
  luz.addEventListener('change', (e) => {
    let g = null; try { g = localStorage.getItem('cideic_tema'); } catch (er) { /* sin almacenamiento */ }
    if (g !== 'claro' && g !== 'oscuro') cambiar(e.matches ? 'claro' : 'oscuro', null);
  });
  rotulo();

  // Pie: el contacto de soporte (CONTACTO en config.js) se vuelve un enlace de WhatsApp; el texto queda igual.
  const pie = document.getElementById('pie'), contacto = String((window.CIIC_CONFIG || {}).CONTACTO || '');
  const numero = contacto.replace(/[^0-9]/g, '');
  if (pie && numero.length >= 9 && numero.length <= 15 && pie.textContent.includes(contacto)) {
    const [antes, ...resto] = pie.textContent.split(contacto);
    const a = document.createElement('a');
    a.href = 'https://wa.me/' + numero; a.target = '_blank'; a.rel = 'noopener'; a.textContent = contacto;
    pie.textContent = antes; pie.append(a, resto.join(contacto));
  }

  // La cinemática arranca cuando la página terminó de cargar y las imágenes del modo visible están
  // decodificadas (con un tope de 1,6 s), para que no compita con la carga y no vaya a tirones.
  const arrancar = () => { if (!html.classList.contains('escena-lista')) requestAnimationFrame(() => requestAnimationFrame(() => html.classList.add('escena-lista'))); };
  const tope = setTimeout(arrancar, 1600);
  const cargada = new Promise((ok) => (document.readyState === 'complete' ? ok() : addEventListener('load', ok, { once: true })));
  const decodificar = (src) => { const i = new Image(); i.src = src; return i.decode ? i.decode().catch(() => {}) : Promise.resolve(); };
  const v = '.v-' + actual();
  const fondos = [...document.querySelectorAll('.c-cielo ' + v + ', .c-paisaje ' + v + ' b')]
    .map((e) => (/url\(["']?([^"')]+)/.exec(getComputedStyle(e).backgroundImage) || [])[1]).filter(Boolean);
  const logos = [...document.querySelectorAll('.escena-logo ' + v + ' img')].map((i) => (i.decode ? i.decode().catch(() => {}) : null));
  Promise.all([cargada, ...fondos.map(decodificar), ...logos]).then(() => { clearTimeout(tope); arrancar(); });
})();
