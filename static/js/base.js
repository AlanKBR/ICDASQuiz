(function () {
  "use strict";
  /* ── Barra offline ── */
  var bar = document.getElementById("offline-bar");
  function syncOnline() { if (bar) bar.hidden = navigator.onLine; }
  window.addEventListener("online",  syncOnline);
  window.addEventListener("offline", syncOnline);
  syncOnline();

  /* ── Previne duplo submit; bloqueia POSTs offline ── */
  document.addEventListener("submit", function (e) {
    if (!navigator.onLine) {
      e.preventDefault();
      if (bar) bar.hidden = false;
      return;
    }
    e.target.querySelectorAll('[type="submit"]').forEach(function (btn) {
      btn.disabled = true;
      btn.setAttribute("aria-busy", "true");
    });
  });

  /* ── Shimmer: remove quando a imagem do quiz termina de carregar ── */
  document.querySelectorAll(".quiz-image-panel img").forEach(function (img) {
    var panel = img.parentElement;
    if (!panel) return;
    function markLoaded() { panel.classList.add("img-loaded"); }
    if (img.complete) {
      if (img.naturalWidth > 0) { markLoaded(); }
      else {
        panel.classList.add("img-loaded", "has-broken-img");
        img.classList.add("img-broken");
      }
    } else {
      img.addEventListener("load", markLoaded);
      img.addEventListener("error", function () {
        panel.classList.add("img-loaded", "has-broken-img");
        img.classList.add("img-broken");
      });
    }
  });

  /* ── Fallback para imagens quebradas na galeria ── */
  document.querySelectorAll(".galeria img").forEach(function (img) {
    function broken() {
      img.classList.add("img-broken");
      if (img.parentElement) img.parentElement.classList.add("has-broken-img");
    }
    if (img.complete && img.naturalWidth === 0 && img.src) { broken(); }
    else { img.addEventListener("error", broken); }
  });
}());
