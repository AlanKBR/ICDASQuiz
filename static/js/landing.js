(function () {
  "use strict";

  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  /* ── Reveal on scroll (leve) ── */
  (function initReveal() {
    if (prefersReducedMotion()) {
      document.querySelectorAll("[data-reveal]").forEach(function (el) {
        el.classList.add("is-visible");
      });
      return;
    }

    if (!("IntersectionObserver" in window)) {
      document.querySelectorAll("[data-reveal]").forEach(function (el) {
        el.classList.add("is-visible");
      });
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    document.querySelectorAll("[data-reveal]").forEach(function (el) {
      io.observe(el);
    });
  }());

  /* ── Accordion acessível (botões + ARIA) ── */
  (function initAccordion() {
    var group = document.querySelector("[data-accordion]");
    if (!group) return;

    function setOpen(item, isOpen) {
      var btn = item.querySelector(".acc-trigger");
      if (!btn) return;
      btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
      item.classList.toggle("is-open", isOpen);
    }

    function closeAll() {
      group.querySelectorAll(".acc-item").forEach(function (item) {
        setOpen(item, false);
      });
    }

    function openAll() {
      group.querySelectorAll(".acc-item").forEach(function (item) {
        setOpen(item, true);
      });
    }

    group.addEventListener("click", function (e) {
      var btn = e.target.closest(".acc-trigger");
      if (!btn) return;

      var item = btn.closest(".acc-item");
      if (!item) return;

      var expanded = btn.getAttribute("aria-expanded") === "true";
      setOpen(item, !expanded);
    });

    document.querySelectorAll("[data-accordion-action]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var action = btn.getAttribute("data-accordion-action");
        if (action === "open-all") openAll();
        if (action === "close-all") closeAll();
      });
    });
  }());

  /* ── Árvore de decisão ICDAS ── */
  (function initDecisionGuide() {
    var guide = document.querySelector("[data-decision-guide]");
    if (!guide) return;

    var stepEl = guide.querySelector("[data-decision-step]");
    var titleEl = guide.querySelector("[data-decision-title]");
    var copyEl = guide.querySelector("[data-decision-copy]");
    var optionsEl = guide.querySelector("[data-decision-options]");
    var resultEl = guide.querySelector("[data-decision-result]");

    if (!stepEl || !titleEl || !copyEl || !optionsEl || !resultEl) return;

    var steps = [
      {
        label: "Etapa 1 de 6",
        title: "O campo está pronto?",
        copy: "Confirme superfície limpa, seca, bem iluminada e sem biofilme antes de classificar.",
        options: [
          { text: "Sim, seguir para avaliação visual", next: 1 },
          { text: "Ainda não, revisar preparo", result: "Prepare o campo antes de decidir. Umidade e biofilme podem mascarar alterações iniciais, principalmente ICDAS 1 e 2." }
        ]
      },
      {
        label: "Etapa 2 de 6",
        title: "Após secagem, há alteração visual?",
        copy: "Compare a superfície úmida e seca por cerca de 5 segundos, observando opacidade, coloração e fissuras.",
        options: [
          { text: "Não há alteração", result: "Provável ICDAS 0: superfície sem evidência visual de cárie após secagem." },
          { text: "Há alteração", next: 2 }
        ]
      },
      {
        label: "Etapa 3 de 6",
        title: "A alteração aparece apenas após secagem?",
        copy: "Lesões iniciais podem ficar visíveis somente quando o esmalte é seco ou permanecer restritas a fossas e fissuras.",
        options: [
          { text: "Sim, só após secagem", result: "Provável ICDAS 1: primeira alteração visual no esmalte." },
          { text: "Não, visível mesmo úmida", next: 3 }
        ]
      },
      {
        label: "Etapa 4 de 6",
        title: "Existe cavidade ou quebra de esmalte?",
        copy: "Se a alteração é distinta, mas a superfície está íntegra, priorize esmalte sem cavitação.",
        options: [
          { text: "Não há cavidade", result: "Provável ICDAS 2: alteração visual distinta no esmalte, sem cavitação." },
          { text: "Há quebra ou cavidade", next: 4 }
        ]
      },
      {
        label: "Etapa 5 de 6",
        title: "A dentina está visível?",
        copy: "Diferencie quebra localizada de esmalte de lesões com sombra escura ou dentina exposta.",
        options: [
          { text: "Não, só quebra de esmalte", result: "Provável ICDAS 3: descontinuidade localizada do esmalte sem dentina visível." },
          { text: "Há sombra ou dentina", next: 5 }
        ]
      },
      {
        label: "Etapa 6 de 6",
        title: "Sombra sob esmalte ou cavidade com dentina?",
        copy: "A extensão e a exposição de dentina separam sombra subjacente, cavidade distinta e cavidade extensa.",
        options: [
          { text: "Sombra sem cavidade evidente", result: "Provável ICDAS 4: sombreamento de dentina sob esmalte aparentemente intacto." },
          { text: "Cavidade com dentina visível", result: "Provável ICDAS 5 ou 6: diferencie pela extensão; ICDAS 6 envolve cavidade ampla, geralmente metade ou mais da superfície." }
        ]
      }
    ];

    function setResult(text) {
      resultEl.textContent = text;
      resultEl.hidden = false;
    }

    function renderStep(index) {
      var step = steps[index] || steps[0];
      stepEl.textContent = step.label;
      titleEl.textContent = step.title;
      copyEl.textContent = step.copy;
      resultEl.hidden = true;
      resultEl.textContent = "";
      optionsEl.innerHTML = "";

      step.options.forEach(function (option) {
        var button = document.createElement("button");
        button.type = "button";
        button.textContent = option.text;
        if (typeof option.next === "number") {
          button.setAttribute("data-next", String(option.next));
        }
        if (option.result) {
          button.setAttribute("data-result", option.result);
        }
        optionsEl.appendChild(button);
      });
    }

    optionsEl.addEventListener("click", function (event) {
      var button = event.target.closest("button");
      if (!button) return;

      var next = button.getAttribute("data-next");
      var result = button.getAttribute("data-result");

      if (next !== null) {
        renderStep(Number(next));
        return;
      }

      if (result) {
        setResult(result);
        if (!optionsEl.querySelector("[data-reset-decision]")) {
          var reset = document.createElement("button");
          reset.type = "button";
          reset.className = "decision-reset";
          reset.setAttribute("data-reset-decision", "true");
          reset.textContent = "Recomeçar";
          optionsEl.appendChild(reset);
        }
      }
    });

    guide.addEventListener("click", function (event) {
      if (!event.target.closest("[data-reset-decision]")) return;
      renderStep(0);
    });

    renderStep(0);
  }());
}());
