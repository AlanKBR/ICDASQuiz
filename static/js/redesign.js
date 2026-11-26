/* Progressive enhancement for the approved responsive interface. */
(() => {
 'use strict';
 // The server shuffles every public image independently for each track.
 // Set durations through CSSOM (allowed by the strict CSP); HTML style
 // attributes are deliberately disallowed in production.
 document.querySelectorAll('.marquee-row').forEach((row, index) => {
   const count = Math.floor(row.querySelectorAll('img').length / 2);
   if (!count) return;
   row.style.setProperty('--marquee-duration', `${count * (index ? 6 : 5)}s`);
   row.style.setProperty('--marquee-duration-mobile', `${count * (index ? 5 : 4)}s`);
 });
 // Two-answer introduction: only public gallery examples are used.
 const demo = document.querySelector('[data-mini-quiz]');
 if (demo) {
   const cards = [...demo.querySelectorAll('[data-demo-photo]')];
   const keys = [...demo.querySelectorAll('.demo-codes button[data-demo-code]')];
   const hint = demo.querySelector('[data-demo-hint]');
   const lock = demo.querySelector('[data-demo-lock]');
   const front = demo.querySelector('.hero-deck-front');
   const badge = demo.querySelector('[data-demo-result-badge]');
   const tally = demo.querySelector('[data-demo-score]');
   let current = 0, correctCount = 0, checking = false;
   const show = () => {
     cards.forEach((card, index) => { card.hidden = index !== current; });
     front.classList.remove('is-correct', 'is-wrong', 'is-changing');
     front.removeAttribute('data-feedback');
     badge.hidden = true;
     badge.textContent = '';
     keys.forEach(key => {
       key.disabled = false;
       key.classList.remove('is-correct', 'is-wrong', 'is-dim');
       key.setAttribute('aria-pressed', 'false');
       key.setAttribute('aria-label', `ICDAS ${key.dataset.demoCode}`);
     });
     checking = false;
     if (hint) hint.textContent = `Classifique esta imagem · ${current + 1} de 2`;
   };
   keys.forEach(key => key.addEventListener('click', () => {
     if (current >= cards.length || checking) return;
     checking = true;
     const correct = cards[current]?.dataset.demoCode;
     const selected = key.dataset.demoCode;
     const isRight = correct === selected;
     if (isRight) correctCount += 1;
     front.classList.add(isRight ? 'is-correct' : 'is-wrong');
     front.setAttribute('data-feedback', isRight ? 'correct' : 'wrong');
     badge.textContent = isRight ? `✓ ICDAS ${correct}` : `Era ICDAS ${correct}`;
     badge.classList.toggle('is-correct', isRight);
     badge.classList.toggle('is-wrong', !isRight);
     badge.hidden = false;
     keys.forEach(item => {
       const isAnswer = item.dataset.demoCode === correct;
       const isChoice = item === key;
       item.classList.toggle('is-correct', isAnswer);
       item.classList.toggle('is-wrong', isChoice && !isRight);
       item.classList.toggle('is-dim', !isAnswer && !isChoice);
       item.setAttribute('aria-pressed', String(isChoice));
       item.setAttribute('aria-label', `ICDAS ${item.dataset.demoCode}${isAnswer ? ', resposta correta' : isChoice ? ', sua resposta, incorreta' : ''}`);
       item.disabled = true;
     });
     if (hint) hint.textContent = isRight
       ? `Correto! ICDAS ${correct}.`
       : `Você marcou ${selected}. A resposta correta é ICDAS ${correct}.`;
     if (tally) {
       tally.hidden = false;
       tally.textContent = `Acertos ${correctCount}/${current + 1}`;
       tally.setAttribute('aria-label', `${correctCount} acertos em ${current + 1} imagens respondidas`);
     }
     // The answer remains visible long enough to distinguish the two states.
     // Animate only the transition; never sacrifice legibility for motion.
     setTimeout(() => {
       current += 1;
       if (current >= cards.length) {
         front.classList.add('is-locked');
         lock?.classList.add('is-on');
         if (hint) hint.textContent = 'Experimente agora o quiz completo.';
         keys.forEach(item => { item.disabled = true; });
         // A disabled answer key can no longer receive keyboard focus. Move
         // focus to the action that becomes available after both answers.
         lock?.querySelector('.go')?.focus({preventScroll: true});
       } else {
         front.classList.add('is-changing');
         setTimeout(show, window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 220);
       }
     }, isRight ? 2200 : 2750);
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
     if (point.tagName.toLowerCase() === 'rect') {
       point.addEventListener('keydown', event => {
         if (event.key === 'Enter' || event.key === ' ') {
           event.preventDefault();
           show();
         }
       });
     }
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
 // Reveal below-fold educational sections once, without making them depend
 // on JavaScript to remain readable. Reduced-motion users see them immediately.
 if (document.querySelector('.landing-page') && 'IntersectionObserver' in window &&
     !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
   const candidates = [...document.querySelectorAll(
     '.landing-section .section-title, .landing-section .project-grid, ' +
     '.landing-section .scale-card, .landing-section .step-card, .landing-section .diff-card'
   )].filter(el => el.getBoundingClientRect().top > window.innerHeight * .8);
   if (candidates.length) {
     const reveal = new IntersectionObserver(entries => {
       entries.forEach(entry => {
         if (!entry.isIntersecting) return;
         entry.target.classList.add('is-visible');
         reveal.unobserve(entry.target);
       });
     }, {threshold: .08, rootMargin: '0px 0px -18px 0px'});
     candidates.forEach(el => { el.classList.add('polish-reveal'); reveal.observe(el); });
   }
 }
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
