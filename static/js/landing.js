(function () {
  "use strict";

  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  /* Reveal on scroll */
  (function initReveal() {
    if (prefersReducedMotion() || !("IntersectionObserver" in window)) {
      document.querySelectorAll("[data-reveal]").forEach(function (element) {
        element.classList.add("is-visible");
      });
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    document.querySelectorAll("[data-reveal]").forEach(function (element) {
      observer.observe(element);
    });
  }());

  /* Accordion de material teórico */
  (function initAccordion() {
    var group = document.querySelector("[data-accordion]");
    if (!group) return;

    function setOpen(item, isOpen) {
      var button = item.querySelector(".acc-trigger");
      if (!button) return;
      button.setAttribute("aria-expanded", isOpen ? "true" : "false");
      item.classList.toggle("is-open", isOpen);
    }

    group.addEventListener("click", function (event) {
      var button = event.target.closest(".acc-trigger");
      if (!button) return;
      var item = button.closest(".acc-item");
      if (item) setOpen(item, button.getAttribute("aria-expanded") !== "true");
    });

    document.querySelectorAll("[data-accordion-action]").forEach(function (button) {
      button.addEventListener("click", function () {
        var open = button.getAttribute("data-accordion-action") === "open-all";
        group.querySelectorAll(".acc-item").forEach(function (item) {
          setOpen(item, open);
        });
      });
    });
  }());
}());
