/* Progressive enhancement for the approved responsive interface. */
(() => {
 'use strict';
 // Two-answer introduction: only public gallery examples are used.
 const demo = document.querySelector('[data-mini-quiz]');
 if (demo) {
   const cards = [...demo.querySelectorAll('[data-demo-photo]')];
   const keys = [...demo.querySelectorAll('[data-demo-code]')];
   const hint = demo.querySelector('[data-demo-hint]');
   const lock = demo.querySelector('[data-demo-lock]');
   let current = 0;
   const show = () => {
     cards.forEach((card, index) => { card.hidden = index !== current; });
     keys.forEach(key => { key.disabled = false; key.classList.remove('selected'); });
     if (hint) hint.textContent = `Classifique esta imagem · ${current + 1} de 2`;
   };
   keys.forEach(key => key.addEventListener('click', () => {
     if (current >= 2) return;
     const correct = cards[current]?.dataset.demoCode;
     const isRight = correct === key.dataset.demoCode;
     key.classList.add(isRight ? 'is-correct' : 'is-wrong');
     cards[current]?.classList.add(isRight ? 'is-correct' : 'is-wrong');
     if (hint) hint.textContent = isRight ? `Correto! Esta foto mostra ICDAS ${correct}.` : `A resposta correta é ICDAS ${correct}.`;
     keys.forEach(item => { item.disabled = true; });
     // Hold the feedback long enough to be read before the next example.
     setTimeout(() => {
       current += 1;
       if (current >= 2) { lock?.classList.add('is-on'); }
       else {
         cards.forEach(card => card.classList.remove('is-correct', 'is-wrong'));
         keys.forEach(item => item.classList.remove('is-correct', 'is-wrong'));
         show();
       }
     }, 1650);
   }));
   show();
 }
 // Accessible readouts for visual analytics (click, keyboard focus, touch).
 document.querySelectorAll('[data-chart-region]').forEach(region => {
   const readout = region.querySelector('[data-chart-readout]');
   if (!readout) return;
   region.querySelectorAll('[data-reading]').forEach(point => {
     const show = () => { readout.textContent = point.dataset.reading; };
     point.addEventListener('focus', show);
     point.addEventListener('click', show);
     point.addEventListener('pointerenter', show);
   });
 });
 document.querySelectorAll('[data-show-student]').forEach(button => {
   button.addEventListener('click', () => {
     const target = document.getElementById(button.getAttribute('aria-controls'));
     if (!target) return;
     const opening = target.hidden;
     document.querySelectorAll('.student-detail').forEach(panel => { panel.hidden = true; });
     document.querySelectorAll('[data-show-student]').forEach(other => { other.setAttribute('aria-expanded','false'); });
     target.hidden = !opening;
     button.setAttribute('aria-expanded', String(opening));
   });
 });
 document.querySelectorAll('[data-photo-filter]').forEach(btn => btn.addEventListener('click', () => {
   document.querySelectorAll('[data-photo-filter]').forEach(other => other.setAttribute('aria-pressed', String(other === btn)));
   const ascending = btn.dataset.photoFilter === 'hard';
   document.querySelectorAll('[data-photo-list]').forEach(list => {
     const children = [...list.children];
     children.sort((a,b) => ascending ? +a.dataset.pct - +b.dataset.pct : +b.dataset.pct - +a.dataset.pct);
     children.forEach(child => list.append(child));
   });
 }));
})();
(() => {
 const tabs = document.querySelector('.score-tabs');
 if (!tabs) return;
 tabs.dataset.enhanced = 'true';
 tabs.dataset.active = 'ranking';
 tabs.querySelectorAll('[data-score-tab]').forEach(button => button.addEventListener('click', () => {
   tabs.dataset.active = button.dataset.scoreTab;
   tabs.querySelectorAll('[data-score-tab]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
 }));
})();
