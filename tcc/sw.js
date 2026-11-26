// Service worker da apresentação: na primeira visita baixa tudo para o cache do navegador.
// A página revalida pela rede (para receber atualizações); o resto vem do cache.
const VER = 'tcc-00f714b4d351';
const LIST = ["./", "fonts/caveat-latin-500-normal.woff2", "fonts/caveat-latin-700-normal.woff2", "fonts/caveat-latin-ext-500-normal.woff2", "fonts/caveat-latin-ext-700-normal.woff2", "fonts/fonts.css", "fonts/im-fell-english-latin-400-normal.woff2", "fonts/jetbrains-mono-latin-400-normal.woff2", "fonts/jetbrains-mono-latin-600-normal.woff2", "fonts/jetbrains-mono-latin-ext-400-normal.woff2", "fonts/jetbrains-mono-latin-ext-600-normal.woff2", "fonts/onest-latin-400-normal.woff2", "fonts/onest-latin-500-normal.woff2", "fonts/onest-latin-600-normal.woff2", "fonts/onest-latin-700-normal.woff2", "fonts/onest-latin-ext-400-normal.woff2", "fonts/onest-latin-ext-500-normal.woff2", "fonts/onest-latin-ext-600-normal.woff2", "fonts/onest-latin-ext-700-normal.woff2", "fonts/special-elite-latin-400-normal.woff2", "fonts/special-elite-latin-ext-400-normal.woff2", "img/01-landing-desktop.png", "img/03-quiz-pergunta-mobile.png", "img/04-quiz-feedback-acerto-mobile.png", "img/acervo/a00.jpg", "img/acervo/a01.jpg", "img/acervo/a02.jpg", "img/acervo/a03.jpg", "img/acervo/a04.jpg", "img/acervo/a05.jpg", "img/acervo/a06.jpg", "img/acervo/a07.jpg", "img/acervo/a08.jpg", "img/acervo/a09.jpg", "img/acervo/a10.jpg", "img/acervo/a11.jpg", "img/acervo/a12.jpg", "img/acervo/a13.jpg", "img/acervo/a14.jpg", "img/acervo/a15.jpg", "img/acervo/a16.jpg", "img/acervo/a17.jpg", "img/acervo/a18.jpg", "img/acervo/a19.jpg", "img/acervo/a20.jpg", "img/acervo/a21.jpg", "img/acervo/a22.jpg", "img/acervo/a23.jpg", "img/acervo/a24.jpg", "img/acervo/a25.jpg", "img/acervo/a26.jpg", "img/c0.jpg", "img/c1.jpg", "img/c2.jpg", "img/c2livre.jpg", "img/c3.jpg", "img/c4.jpg", "img/c5.jpg", "img/c6.jpg", "img/ficha.jpg", "img/icdas1a.jpg", "img/site-arvore.jpg", "img/site-hero.jpg", "img/site-proj.jpg", "img/unisa.png", "opening/assets/first_slide_original.png", "opening/assets/index-C8BQEKNi.css", "opening/assets/index-HGDAp0eH.js", "opening/assets/intro_video_4s.mp4", "opening/assets/molar/scene.bin.wasm", "opening/assets/molar/scene.json", "opening/assets/molar/textures/defaultMat_baseColor.png", "opening/assets/molar/textures/defaultMat_normal.png", "opening/assets/monitor_blank.png", "opening/assets/monitor_quiz_reference.png", "opening/index.html"];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(VER).then(c => c.addAll(LIST)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('tcc-') && k !== VER).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET' || r.headers.has('range')) return;
  const u = new URL(r.url);
  if (u.origin !== location.origin) return;
  const base = new URL('./', location.href).pathname;
  if (!u.pathname.startsWith(base)) return;
  if (r.mode === 'navigate') {
    e.respondWith(fetch(r).then(res => {
      const key = u.pathname === base ? './' : u.pathname;
      if (res.ok) { const cp = res.clone(); caches.open(VER).then(c => c.put(key, cp)); }
      return res;
    }).catch(() => caches.match(u.pathname === base ? './' : r, { ignoreSearch: true })));
    return;
  }
  e.respondWith(caches.match(r, { ignoreSearch: u.pathname.endsWith('.html') }).then(hit => hit || fetch(r).then(res => {
    if (res.ok && res.type === 'basic') { const cp = res.clone(); caches.open(VER).then(c => c.put(r, cp)); }
    return res;
  })));
});
