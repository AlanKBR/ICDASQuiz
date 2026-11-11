/* Árvore clínica: opções irmãs permanecem visíveis e clicáveis.
 * As linhas são ancoradas nas bordas REAIS dos botões e perguntas.
 * A lógica clínica pertence a arvore_modelo.js, não à interface.
 */
(function () {
  "use strict";

  var model = window.ICDASArvoreModelo;
  var root = document.querySelector("[data-treatment-tree]");
  if (!model || !root) return;

  var board = root.querySelector("[data-tree-board]");
  var content = root.querySelector("[data-tree-content]");
  var svg = root.querySelector("[data-tree-lines]");
  if (!board || !content || !svg) return;

  var SVG_NS = "http://www.w3.org/2000/svg";
  var state = { surface: "oclusal", code: "2", rx: null, activity: null, depth: null, risk: null };
  var dependents = {
    surface: ["rx", "code", "activity", "depth", "risk"],
    rx: ["code", "activity", "depth", "risk"],
    code: ["activity", "depth", "risk"],
    activity: ["depth", "risk"],
    depth: ["risk"],
    risk: []
  };
  var treatments = { P: "Profilaxia", NI: "Não invasivo", MI: "Microinvasivo", I: "Invasivo" };
  // Corte radiográfico didático único; não representa uma radiografia real.
  var CUT_PATHS = {
    enamel: "M17 13 C25 6 34 9 42 15 C48 19 55 11 62 10 C74 6 87 12 96 22 C106 32 105 52 97 64 C89 77 70 80 55 77 C38 78 22 71 15 58 C10 46 10 27 17 13 Z",
    dentin: "M28 24 C38 19 43 27 51 28 C60 20 72 18 82 25 C93 32 94 51 84 60 C74 69 43 71 33 61 C23 51 23 34 28 24 Z",
    pulp: "M45 42 C48 36 56 35 62 38 C67 41 68 52 62 58 C55 62 48 59 44 55 C41 51 41 46 45 42 Z"
  };
  var RX_EXTENT_PATHS = {
    nenhuma: null,
    e1: "M103 29 Q97 29 93 35 L94 47 Q100 47 103 50 Z",
    e2d1: "M103 27 Q93 28 87 32 L76 40 L87 48 Q95 49 104 51 Z",
    d2d3: "M103 25 Q87 28 78 32 L64 41 L78 53 Q94 51 104 52 Z"
  };
  var OCCLUSAL_EXTENT_PATHS = {
    esmalte: "M103 29 Q98 29 89 34 L90 48 Q97 46 103 50 Z",
    dentina: "M103 28 Q92 28 83 33 L71 41 L84 49 Q96 50 104 52 Z"
  };
  var frame = null;
  var shaftPath = document.createElementNS(SVG_NS, "path");
  var arrowheadsPath = document.createElementNS(SVG_NS, "path");
  shaftPath.setAttribute("class", "tree-edge--active");
  shaftPath.setAttribute("data-tree-active-shafts", "");
  arrowheadsPath.setAttribute("class", "tree-arrowheads");
  arrowheadsPath.setAttribute("data-tree-active-tips", "");
  svg.replaceChildren(shaftPath, arrowheadsPath);

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function svgEl(tag, attributes) {
    var node = document.createElementNS(SVG_NS, tag);
    Object.keys(attributes).forEach(function (key) {
      node.setAttribute(key, String(attributes[key]));
    });
    return node;
  }

  function radiographicCut(field, value) {
    var drawing = svgEl("svg", {
      class: "tree-rx-diagram",
      viewBox: "0 0 118 84",
      "data-diagram-field": field,
      "data-diagram-value": value,
      "aria-hidden": "true",
      focusable: "false"
    });
    // Corte proximal esquemático: exterior (esmalte), dentina e polpa.
    // A mancha escura representa apenas a profundidade indicada pelos slides,
    // não uma imagem radiográfica real ou diagnóstico de cavitação.
    drawing.appendChild(svgEl("path", { d: CUT_PATHS.enamel, class: "tree-rx-enamel" }));
    drawing.appendChild(svgEl("path", { d: CUT_PATHS.dentin, class: "tree-rx-dentin" }));
    drawing.appendChild(svgEl("path", { d: CUT_PATHS.pulp, class: "tree-rx-pulp" }));
    var extent = field === "rx" ? RX_EXTENT_PATHS[value] : OCCLUSAL_EXTENT_PATHS[value];
    if (extent) {
      drawing.appendChild(svgEl("path", { d: extent, class: "tree-rx-radiolucency" }));
    }
    return drawing;
  }

  function icon(field, value) {
    if (field === "rx" || field === "depth") return radiographicCut(field, value);
    var symbols = {
      surface: { oclusal: "◎", proximal: "◧" },
      activity: { S: "◉", N: "◌" },
      risk: { B: "◌", A: "◉" }
    };
    if (!symbols[field] || !symbols[field][value]) return null;
    var glyph = el("span", "tree-symbol", symbols[field][value]);
    glyph.setAttribute("aria-hidden", "true");
    return glyph;
  }

  function option(field, value, selected, hasSelection) {
    var button = el("button", "tree-option tree-option--" + field +
      (selected ? " is-selected" : hasSelection ? " is-muted" : ""));
    button.type = "button";
    button.dataset.field = field;
    button.dataset.value = value;
    button.setAttribute("aria-pressed", selected ? "true" : "false");
    if (field === "code") button.setAttribute("aria-label", "Código ICDAS " + value);
    var symbol = icon(field, value);
    if (symbol) button.appendChild(symbol);
    button.appendChild(el("span", "tree-option-label", model.fields[field].options[value]));
    if (selected) {
      var tick = el("span", "tree-tick", "✓");
      tick.setAttribute("aria-hidden", "true");
      button.appendChild(tick);
    }
    return button;
  }

  function level(entry) {
    var section = el("section", "tree-level" + (entry.selected === null ? " is-current" : " is-complete"));
    section.dataset.field = entry.field;
    var question = el("div", "tree-question");
    question.tabIndex = -1;
    question.appendChild(el("h3", "", model.fields[entry.field].label));

    section.appendChild(question);
    var choices = model.availableOptions(state, entry.field);
    var group = el("div", "tree-choices tree-choices--" + entry.field);
    // O layout decide o tamanho pela largura do conteúdo e pelo espaço
    // disponível; a contagem é mantida para inspeção e testes.
    group.dataset.count = String(choices.length);
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", model.fields[entry.field].label);
    choices.forEach(function (value) {
      group.appendChild(option(entry.field, value, entry.selected === value, entry.selected !== null));
    });
    section.appendChild(group);
    return section;
  }

  function outcome(result) {
    var card = el("article", "tree-result");
    card.tabIndex = -1;
    card.setAttribute("role", "status");
    card.appendChild(el("span", "tree-result-mark", "✓"));
    var names = result.outcome.split("/").map(function (code) {
      return treatments[code] || code;
    });
    var words = el("div", "tree-result-words");
    names.forEach(function (name, index) {
      if (index) words.appendChild(el("span", "tree-result-separator", "/"));
      words.appendChild(el("strong", "", name));
    });
    card.appendChild(words);
    return card;
  }

  function point(element, side, origin) {
    var rect = element.getBoundingClientRect();
    return {
      x: Math.round((rect.left + rect.width / 2 - origin.left) * 100) / 100,
      y: Math.round(((side === "top" ? rect.top : rect.bottom) - origin.top) * 100) / 100
    };
  }

  function pathBetween(source, target, origin) {
    var start = point(source, "bottom", origin);
    var targetTop = point(target, "top", origin);
    // Ponta 2 px antes do cartão. O fim do traço se sobrepõe ao triângulo,
    // com tangente vertical, sem depender de marker-end/refX do navegador.
    var tipY = targetTop.y - 2;
    var shaftY = tipY - 5;
    var curve = Math.min(32, Math.max(5, (shaftY - start.y) / 2));
    return {
      d: "M " + start.x + " " + start.y +
        " C " + start.x + " " + (start.y + curve) +
        ", " + targetTop.x + " " + (shaftY - curve) +
        ", " + targetTop.x + " " + shaftY,
      arrow: "M " + targetTop.x + " " + tipY +
        " L " + (targetTop.x - 4) + " " + (tipY - 8) +
        " L " + (targetTop.x + 4) + " " + (tipY - 8) + " Z"
    };
  }

  function drawLines() {
    frame = null;
    if (!board.isConnected) return;
    var origin = board.getBoundingClientRect();
    if (!origin.width || !origin.height) return;
    var width = board.clientWidth;
    var height = board.scrollHeight;
    var viewBox = "0 0 " + width + " " + height;
    if (svg.getAttribute("viewBox") !== viewBox) svg.setAttribute("viewBox", viewBox);
    var shafts = [];
    var tips = [];
    var steps = Array.from(content.querySelectorAll(".tree-level"));
    steps.forEach(function (step, index) {
      var question = step.querySelector(".tree-question");
      var selected = step.querySelector(".tree-option.is-selected");
      // Sem seleção não existe conexão. Irmãos inativos seguem clicáveis,
      // mas não originam nem recebem linhas.
      if (!selected) return;
      var next = steps[index + 1];
      var target = next ? next.querySelector(".tree-question") : content.querySelector(".tree-result");
      [[question, selected], [selected, target]].forEach(function (pair) {
        if (!pair[1]) return;
        var route = pathBetween(pair[0], pair[1], origin);
        shafts.push(route.d);
        tips.push(route.arrow);
      });
    });

    // Dois únicos paths SVG, independentemente do número de etapas.
    // As pontas são desenhadas com a mesma coordenada x que encerra a curva.
    shaftPath.setAttribute("d", shafts.join(" "));
    arrowheadsPath.setAttribute("d", tips.join(" "));
    svg.dataset.activeConnections = String(shafts.length);
  }

  function scheduleLines() {
    if (frame !== null) window.cancelAnimationFrame(frame);
    frame = window.requestAnimationFrame(drawLines);
  }

  function render(reveal) {
    var evaluated = model.evaluate(state);
    if (evaluated.status === "unrepresented") {
      throw new Error("Caminho sem desfecho não pode ser selecionado");
    }
    var nodes = evaluated.fields.map(level);
    if (evaluated.status === "result") nodes.push(outcome(evaluated));
    content.replaceChildren.apply(content, nodes);
    // Desenhar neste mesmo ciclo evita o frame inicial sem conectores.
    drawLines();

    if (reveal) {
      var target = content.querySelector(".tree-level.is-current .tree-question") ||
        content.querySelector(".tree-result");
      if (target) {
        window.requestAnimationFrame(function () {
          target.scrollIntoView({
            block: "nearest", inline: "nearest",
            behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth"
          });
        });
      }
    }
  }

  content.addEventListener("click", function (event) {
    var button = event.target.closest("button[data-field][data-value]");
    if (!button || !content.contains(button)) return;
    var field = button.dataset.field;
    var value = button.dataset.value;
    if (!Object.prototype.hasOwnProperty.call(dependents, field)) return;
    if (!model.availableOptions(state, field).includes(value)) return;

    if (state[field] !== value) {
      dependents[field].forEach(function (descendant) { state[descendant] = null; });
      state[field] = value;
      render(true);
    }
  });

  var reset = root.querySelector("[data-tree-reset]");
  if (reset) reset.addEventListener("click", function () {
    Object.keys(state).forEach(function (field) { state[field] = null; });
    render(false);
  });

  if (typeof ResizeObserver !== "undefined") {
    new ResizeObserver(scheduleLines).observe(content);
  }
  window.addEventListener("resize", scheduleLines);
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(scheduleLines);
  }
  render(false);
}());
