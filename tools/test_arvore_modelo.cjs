/* Executar: node --test tools/test_arvore_modelo.cjs */
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const model = require("../static/js/arvore_modelo.js");

const oc = (code, activity, depth, risk) => ({
  surface: "oclusal", code: String(code), activity, depth, risk
});
const pr = (rx, code, activity, risk) => ({
  surface: "proximal", rx, code: code == null ? null : String(code), activity, risk
});

test("todos os percursos oclusais transcritos têm as saídas corretas", () => {
  const cases = [
    [oc(0, null, null, "B"), "P"],
    [oc(0, null, null, "A"), "NI/MI"],
    [oc(1, "S", "esmalte", "B"), "NI"],
    [oc(1, "S", "esmalte", "A"), "MI"],
    [oc(2, "S", "dentina", "B"), "NI"],
    [oc(2, "S", "dentina", "A"), "MI/I"],
    [oc(1, "N"), "P"],
    [oc(3, "S", "esmalte", "B"), "MI/I"],
    [oc(3, "S", "esmalte", "A"), "MI/I"],
    [oc(3, "S", "dentina", "B"), "MI/I"],
    [oc(3, "S", "dentina", "A"), "I"],
    [oc(3, "N"), "P"],
    [oc(4, "S"), "I"],
    [oc(5, "S"), "I"],
    [oc(6, "S"), "I"]
  ];
  cases.forEach(([input, outcome]) => {
    const actual = model.evaluate(input);
    assert.equal(actual.status, "result", JSON.stringify(input));
    assert.equal(actual.outcome, outcome, JSON.stringify(input));
  });
});

test("todos os percursos proximais transcritos têm as saídas corretas", () => {
  const cases = [
    [pr("nenhuma", 0, null, "B"), "P"],
    [pr("nenhuma", 0, null, "A"), "NI"],
    [pr("nenhuma", 1, "S"), "NI"],
    [pr("nenhuma", 2, "N"), "P"],
    [pr("e1", 0, "S", "B"), "NI"],
    [pr("e1", 1, "S", "A"), "NI/MI"],
    [pr("e1", 2, "N"), "P"],
    [pr("e1", 3), "I"],
    [pr("e1", 6), "I"],
    [pr("e2d1", 0, "S", "B"), "NI"],
    [pr("e2d1", 1, "S", "A"), "MI"],
    [pr("e2d1", 2, "N"), "P"],
    [pr("e2d1", 3), "I"],
    [pr("e2d1", 6), "I"],
    [pr("d2d3", null), "I"]
  ];
  cases.forEach(([input, outcome]) => {
    const actual = model.evaluate(input);
    assert.equal(actual.status, "result", JSON.stringify(input));
    assert.equal(actual.outcome, outcome, JSON.stringify(input));
  });
});

test("lacunas dos slides não viram recomendações fabricadas", () => {
  for (const code of [4, 5, 6]) {
    const actual = model.evaluate(oc(code, "N"));
    assert.equal(actual.status, "unrepresented");
    assert.equal(actual.outcome, undefined);
  }
  for (const code of [3, 4, 5, 6]) {
    const actual = model.evaluate(pr("nenhuma", code));
    assert.equal(actual.status, "unrepresented");
    assert.equal(actual.outcome, undefined);
  }
});

test("o formulário mostra somente critérios aplicáveis ao ramo selecionado", () => {
  assert.equal(model.evaluate({ surface: "oclusal" }).nextField, "code");
  assert.equal(model.evaluate({ surface: "oclusal", code: "0" }).nextField, "risk");
  assert.equal(model.evaluate(oc(1, "S")).nextField, "depth");
  assert.equal(model.evaluate(oc(3, "S", "dentina")).nextField, "risk");
  assert.equal(model.evaluate({ surface: "proximal" }).nextField, "rx");
  assert.equal(model.evaluate({ surface: "proximal", rx: "e1" }).nextField, "code");
  assert.equal(model.evaluate(pr("e1", 1, "S")).nextField, "risk");
  assert.equal(model.evaluate({ surface: "proximal", rx: "d2d3" }).outcome, "I");
});

test("nenhum nó do grafo aponta para nó inexistente", () => {
  for (const node of Object.values(model.graph)) {
    for (const destination of Object.values(node.edges)) {
      if (!destination.startsWith("result:") && !destination.startsWith("unrepresented:")) {
        assert.ok(model.graph[destination], destination);
      }
    }
  }
});

test("opções sem saída no slide ficam ocultas, sem alterar o grafo original", () => {
  const opts = model.availableOptions;
  assert.deepEqual(opts({ surface: "oclusal", code: "4" }, "activity"), ["S"]);
  assert.deepEqual(opts({ surface: "oclusal", code: "5" }, "activity"), ["S"]);
  assert.deepEqual(opts({ surface: "proximal", rx: "nenhuma" }, "code"), ["0", "1", "2"]);
  assert.deepEqual(opts({ surface: "proximal", rx: "e1" }, "code"), ["0", "1", "2", "3", "4", "5", "6"]);
  assert.deepEqual(opts({ surface: "proximal", rx: "d2d3" }, "code"), []);
  assert.equal(model.evaluate({ surface: "oclusal", code: "4", activity: "N" }).status, "unrepresented");
  assert.equal(model.evaluate({ surface: "proximal", rx: "nenhuma", code: "6" }).status, "unrepresented");
});

test("toda opção oferecida leva a pelo menos um desfecho do slide", () => {
  const graph = model.graph;
  function walk(nodeId, values) {
    const node = graph[nodeId];
    const filtered = model.availableOptions(values, node.field);
    for (const option of filtered) {
      const destination = node.edges[option];
      assert.notEqual(destination.startsWith("unrepresented:"), true, JSON.stringify(values));
      const next = { ...values, [node.field]: option };
      if (destination.startsWith("result:")) {
        assert.equal(model.evaluate(next).status, "result", JSON.stringify(next));
      } else {
        walk(destination, next);
      }
    }
    assert.ok(filtered.length > 0, "nó sem desfecho: " + nodeId);
  }
  walk("surface", {});
});

test("rótulos do usuário não exibem códigos radiográficos ou abreviações de manejo", () => {
  for (const value of Object.values(model.fields.rx.options)) {
    assert.doesNotMatch(value, /^(E[12]|D[123])/);
  }
  assert.equal(model.fields.activity.options.S, "Ativa");
  assert.equal(model.fields.activity.options.N, "Inativa");
  assert.equal(model.fields.risk.options.B, "Baixo");
  assert.equal(model.fields.risk.options.A, "Alto");
});
