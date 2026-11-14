/* ICDASQuiz redesign: the server remains the sole source of scoring truth. */
(() => {
  'use strict';
  const name = document.getElementById('quiz-nome');
  if (name) {
    const button = document.querySelector('.quiz-start-button');
    const sync = () => { button.disabled = !name.value.trim(); };
    name.addEventListener('input', sync);
    sync();
  }

  const form = document.getElementById('quiz-answer-form');
  if (form && form.querySelector('input[name="resposta"]')) {
    const radios = [...form.querySelectorAll('input[name="resposta"]')];
    const button = document.querySelector('.quiz-submit');
    const hint = document.getElementById('quiz-code-hint');
    const descriptions = [
      'Superfície dental saudável',
      'Primeira alteração visual no esmalte',
      'Alteração visual distinta no esmalte',
      'Descontinuidade localizada do esmalte',
      'Sombreamento de dentina subjacente',
      'Cavidade distinta com dentina visível',
      'Cavidade extensa com dentina visível'
    ];
    const sync = () => {
      const active = radios.find(r => r.checked);
      button.disabled = !active;
      if (hint) hint.textContent = active ? `ICDAS ${active.value} · ${descriptions[+active.value]}` : 'Toque no código';
    };
    radios.forEach(r => r.addEventListener('change', sync));
    sync();
    let submitted = false;
    form.addEventListener('submit', event => {
      if (submitted) { event.preventDefault(); return; }
      if (!radios.some(r => r.checked)) { event.preventDefault(); return; }
      submitted = true;
      button.disabled = true;
      button.textContent = 'Verificando…';
    });
    document.addEventListener('keydown', event => {
      if (event.ctrlKey || event.metaKey || event.altKey || /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || '')) return;
      if (/^[0-6]$/.test(event.key)) {
        const radio = radios.find(r => r.value === event.key);
        if (radio) { radio.checked = true; radio.dispatchEvent(new Event('change', {bubbles: true})); event.preventDefault(); }
      } else if (event.key === 'Enter' && radios.some(r => r.checked) && !submitted) {
        form.requestSubmit(); event.preventDefault();
      }
    });
  }

  const viewer = document.getElementById('quiz-viewer');
  if (viewer) {
    const open = document.querySelector('[data-photo-open]');
    const close = viewer.querySelector('[data-photo-close]');
    const img = viewer.querySelector('img');
    const shut = () => { viewer.hidden = true; img.classList.remove('zoomed'); if (open) open.focus(); };
    open?.addEventListener('click', () => { viewer.hidden = false; close.focus(); });
    close?.addEventListener('click', shut);
    viewer.addEventListener('click', event => { if (event.target === viewer) shut(); });
    img.addEventListener('click', () => { img.classList.toggle('zoomed'); img.style.transform = img.classList.contains('zoomed') ? 'scale(1.9)' : ''; });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !viewer.hidden) { event.preventDefault(); shut(); }
    });
  }

  const thumbs = [...document.querySelectorAll('[data-review-index]')];
  if (thumbs.length) {
    thumbs.forEach(btn => btn.addEventListener('click', () => {
      thumbs.forEach(other => {
        const chosen = other === btn;
        other.classList.toggle('selected', chosen);
        other.setAttribute('aria-pressed', String(chosen));
      });
      document.querySelectorAll('[data-review-detail]').forEach(detail => {
        detail.hidden = detail.dataset.reviewDetail !== btn.dataset.reviewIndex;
      });
    }));
  }
})();
