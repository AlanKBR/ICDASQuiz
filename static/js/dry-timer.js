/* Functional five-second teaching timer. The ring represents elapsed time,
 * not an endlessly looping decoration. No libraries or network requests. */
(() => {
  'use strict';
  const button = document.querySelector('[data-dry-timer]');
  if (!button) return;
  const circle = button.querySelector('[data-dry-progress]');
  const value = button.querySelector('[data-dry-value]');
  const hint = document.querySelector('[data-dry-hint]');
  const status = document.querySelector('[data-dry-status]');
  const duration = 5000;
  const circumference = 2 * Math.PI * 22;
  let remaining = duration;
  let previous = 0;
  let frame = 0;
  let state = 'ready';

  const render = () => {
    const fraction = Math.max(0, Math.min(1, remaining / duration));
    circle.style.strokeDashoffset = String(circumference * (1 - fraction));
    value.textContent = state === 'complete' ? '✓' : `${Math.ceil(remaining / 1000)} s`;
  };

  const finish = () => {
    state = 'complete';
    remaining = 0;
    frame = 0;
    button.dataset.state = state;
    button.setAttribute('aria-label', 'Cinco segundos concluídos. Reiniciar cronômetro');
    hint.textContent = 'Concluído · toque para repetir';
    status.textContent = 'Cinco segundos concluídos.';
    render();
  };

  const tick = now => {
    if (state !== 'running' || document.hidden) return;
    remaining = Math.max(0, remaining - (now - previous));
    previous = now;
    if (remaining === 0) { finish(); return; }
    render();
    frame = requestAnimationFrame(tick);
  };

  const start = () => {
    cancelAnimationFrame(frame);
    state = 'running';
    remaining = duration;
    previous = performance.now();
    button.dataset.state = state;
    button.setAttribute('aria-label', 'Reiniciar cronômetro de 5 segundos');
    hint.textContent = 'Contando · toque para reiniciar';
    status.textContent = 'Cronômetro iniciado. Cinco segundos.';
    render();
    if (!document.hidden) frame = requestAnimationFrame(tick);
  };

  button.addEventListener('click', start);
  document.addEventListener('visibilitychange', () => {
    if (state !== 'running') return;
    cancelAnimationFrame(frame);
    if (document.hidden) {
      hint.textContent = 'Contagem pausada nesta aba';
      status.textContent = 'Cronômetro pausado.';
    } else {
      previous = performance.now();
      hint.textContent = 'Contando · toque para reiniciar';
      status.textContent = 'Cronômetro retomado.';
      frame = requestAnimationFrame(tick);
    }
  });
  render();
})();
