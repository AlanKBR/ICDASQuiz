/* Public ICDAS gallery samples, embedded by the server in the home page.
 * No quiz answers or unlisted clinical data are ever fetched here.
 */
(() => {
  'use strict';
  const modal = document.getElementById('scale-lightbox');
  if (!modal) return;
  const photos = [...document.querySelectorAll('[data-scale-photo]')];
  const buttons = [...document.querySelectorAll('[data-scale-open]')];
  const image = modal.querySelector('[data-scale-image]');
  let subset = [], index = 0, trigger = null;
  const set = (selector, text) => { modal.querySelector(selector).textContent = text ?? ''; };
  const render = () => {
    const photo = subset[index];
    if (!photo) return;
    image.src = photo.dataset.src;
    image.alt = `Exemplo clínico ${index + 1} do código ICDAS ${photo.dataset.code}`;
    set('[data-scale-counter]', `${index + 1} de ${subset.length}`);
  };
  const shift = delta => {
    if (subset.length) { index = (index + delta + subset.length) % subset.length; render(); }
  };
  buttons.forEach(button => button.addEventListener('click', () => {
    subset = photos.filter(photo => photo.dataset.code === button.dataset.scaleOpen);
    if (!subset.length) return;
    trigger = button;
    index = 0;
    set('[data-scale-title]', `ICDAS ${button.dataset.scaleOpen}`);
    set('[data-scale-description]', button.dataset.scaleName);
    set('[data-scale-criterion]', button.dataset.scaleShort);
    set('[data-scale-clinical]', button.dataset.scaleLong);
    modal.querySelector('[data-scale-dry]').hidden = !['1', '2'].includes(button.dataset.scaleOpen);
    render();
    modal.showModal();
    modal.querySelector('[data-scale-close]').focus();
  }));
  modal.querySelector('[data-scale-prev]').addEventListener('click', () => shift(-1));
  modal.querySelector('[data-scale-next]').addEventListener('click', () => shift(1));
  if (!('commandForElement' in HTMLButtonElement.prototype)) {
    modal.querySelector('[data-scale-close]').addEventListener('click', () => modal.close());
  }
  if (!('closedBy' in HTMLDialogElement.prototype)) {
    modal.addEventListener('click', e => { if (e.target === modal) modal.close(); });
  }
  modal.addEventListener('close', () => trigger?.focus());
  modal.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft') { shift(-1); event.preventDefault(); }
    if (event.key === 'ArrowRight') { shift(1); event.preventDefault(); }
  });
})();
