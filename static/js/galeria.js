/* Public gallery with client-side filtering and an accessible detail viewer. */
(() => {
  'use strict';
  const cards = [...document.querySelectorAll('[data-gallery-card]')];
  const filters = [...document.querySelectorAll('[data-gallery-filter]')];
  const count = document.querySelector('[data-gallery-count]');
  const modal = document.getElementById('gallery-lightbox');
  let visible = cards, index = 0, trigger = null;
  const apply = code => {
    visible = cards.filter(card => code === 'todos' || card.dataset.icdas === code);
    cards.forEach(card => { card.hidden = !visible.includes(card); });
    filters.forEach(btn => btn.setAttribute('aria-pressed', String(btn.dataset.galleryFilter === code)));
    if (count) count.textContent = visible.length;
  };
  filters.forEach(btn => btn.addEventListener('click', () => apply(btn.dataset.galleryFilter)));
  const fromQuery = new URLSearchParams(location.search).get('codigo');
  apply(/^[0-6]$/.test(fromQuery || '') ? fromQuery : 'todos');
  if (!modal) return;
  const img = modal.querySelector('[data-lightbox-photo]');
  const set = (selector, value) => { modal.querySelector(selector).textContent = value || ''; };
  const render = () => {
    const card = visible[index];
    if (!card) return;
    img.src = card.dataset.src;
    img.alt = `Fotografia ampliada, código ${card.dataset.icdas}`;
    set('[data-lightbox-code]', `ICDAS ${card.dataset.icdas}`);
    set('[data-lightbox-title]', card.dataset.title);
    set('[data-lightbox-criterion]', card.dataset.criterion);
    set('[data-lightbox-clinical]', card.dataset.clinical);
    set('[data-lightbox-pos]', `${index + 1} de ${visible.length}`);
  };
  cards.forEach(card => card.addEventListener('click', () => {
    trigger = card; index = visible.indexOf(card); render(); modal.showModal();
    modal.querySelector('[data-lightbox-close]').focus();
  }));
  const close = () => { modal.close(); trigger?.focus(); };
  modal.querySelector('[data-lightbox-close]').addEventListener('click', close);
  modal.querySelector('[data-lightbox-prev]').addEventListener('click', () => {index = (index - 1 + visible.length) % visible.length;render();});
  modal.querySelector('[data-lightbox-next]').addEventListener('click', () => {index = (index + 1) % visible.length;render();});
  modal.addEventListener('click', event => { if (event.target === modal) close(); });
  modal.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft') { index = (index - 1 + visible.length) % visible.length; render(); event.preventDefault(); }
    if (event.key === 'ArrowRight') { index = (index + 1) % visible.length; render(); event.preventDefault(); }
  });
})();
