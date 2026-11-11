/* Transcrição provisória dos fluxogramas de Meyer-Lueckel e Paris (2016).
 * Não equivale à validação clínica e não deve ser usada como prescrição.
 * Os destinos "unrepresented" são lacunas REAIS dos slides, não defaults.
 * Este arquivo não toca em banco, pontuações ou sessão do quiz.
 */
(function (root, factory) {
  "use strict";
  var model = factory();
  if (typeof module === "object" && module.exports) module.exports = model;
  if (root) root.ICDASArvoreModelo = model;
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var FIELDS = {
    surface: {
      label: "Superfície",
      help: "Selecione onde está a lesão.",
      options: { oclusal: "Oclusal", proximal: "Proximal" }
    },
    code: {
      label: "Classificação ICDAS",
      help: "Informe o código observado.",
      options: { "0": "0", "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6" }
    },
    rx: {
      label: "Profundidade na radiografia",
      help: "Indique até onde a alteração se estende.",
      options: {
        nenhuma: "Sem alteração visível",
        e1: "Metade externa do esmalte",
        e2d1: "Esmalte interno ou dentina superficial",
        d2d3: "Dentina média ou profunda"
      }
    },
    activity: {
      label: "Atividade da lesão",
      help: "Interpretação provisória da atividade usada nos slides.",
      options: { S: "Ativa", N: "Inativa" }
    },
    depth: {
      label: "Profundidade na radiografia",
      help: "Selecione a região alcançada pela alteração.",
      options: { esmalte: "Sem alteração ou somente esmalte", dentina: "Atinge a dentina" }
    },
    risk: {
      label: "Risco de cárie",
      help: "Interpretação provisória do risco nos slides.",
      options: { B: "Baixo", A: "Alto" }
    }
  };

  /* Grafo dirigido, declarativo e verificável. Não preencher destinos omissos. */
  var GRAPH = {
    surface: { field: "surface", edges: { oclusal: "oc_code", proximal: "prox_rx" } },

    oc_code: { field: "code", edges: {
      "0": "oc0_risk", "1": "oc12_activity", "2": "oc12_activity",
      "3": "oc3_activity", "4": "oc456_activity", "5": "oc456_activity", "6": "oc456_activity"
    } },
    oc0_risk: { field: "risk", edges: { B: "result:P", A: "result:NI/MI" } },
    oc12_activity: { field: "activity", edges: { S: "oc12_depth", N: "result:P" } },
    oc12_depth: { field: "depth", edges: { esmalte: "oc12_esmalte_risk", dentina: "oc12_dentina_risk" } },
    oc12_esmalte_risk: { field: "risk", edges: { B: "result:NI", A: "result:MI" } },
    oc12_dentina_risk: { field: "risk", edges: { B: "result:NI", A: "result:MI/I" } },
    oc3_activity: { field: "activity", edges: { S: "oc3_depth", N: "result:P" } },
    oc3_depth: { field: "depth", edges: { esmalte: "oc3_esmalte_risk", dentina: "oc3_dentina_risk" } },
    oc3_esmalte_risk: { field: "risk", edges: { B: "result:MI/I", A: "result:MI/I" } },
    oc3_dentina_risk: { field: "risk", edges: { B: "result:MI/I", A: "result:I" } },
    oc456_activity: { field: "activity", edges: { S: "result:I", N: "unrepresented:Oclusal 4–6 com N" } },

    prox_rx: { field: "rx", edges: {
      nenhuma: "prox_none_code", e1: "prox_e1_code",
      e2d1: "prox_e2d1_code", d2d3: "result:I"
    } },
    prox_none_code: { field: "code", edges: {
      "0": "prox_none_risk", "1": "prox_none_activity", "2": "prox_none_activity",
      "3": "unrepresented:Proximal sem radiolucidez, ICDAS 3–6",
      "4": "unrepresented:Proximal sem radiolucidez, ICDAS 3–6",
      "5": "unrepresented:Proximal sem radiolucidez, ICDAS 3–6",
      "6": "unrepresented:Proximal sem radiolucidez, ICDAS 3–6"
    } },
    prox_none_risk: { field: "risk", edges: { B: "result:P", A: "result:NI" } },
    prox_none_activity: { field: "activity", edges: { S: "result:NI", N: "result:P" } },
    prox_e1_code: { field: "code", edges: {
      "0": "prox_e1_activity", "1": "prox_e1_activity", "2": "prox_e1_activity",
      "3": "result:I", "4": "result:I", "5": "result:I", "6": "result:I"
    } },
    prox_e1_activity: { field: "activity", edges: { S: "prox_e1_risk", N: "result:P" } },
    prox_e1_risk: { field: "risk", edges: { B: "result:NI", A: "result:NI/MI" } },
    prox_e2d1_code: { field: "code", edges: {
      "0": "prox_e2d1_activity", "1": "prox_e2d1_activity", "2": "prox_e2d1_activity",
      "3": "result:I", "4": "result:I", "5": "result:I", "6": "result:I"
    } },
    prox_e2d1_activity: { field: "activity", edges: { S: "prox_e2d1_risk", N: "result:P" } },
    prox_e2d1_risk: { field: "risk", edges: { B: "result:NI", A: "result:MI" } }
  };

  function evaluate(values) {
    var nodeId = "surface";
    var fields = [];
    values = values || {};
    for (var i = 0; i < 12; i += 1) {
      var node = GRAPH[nodeId];
      if (!node) throw new Error("Nó inválido: " + nodeId);
      var selected = values[node.field];
      var valid = selected !== undefined && selected !== null &&
        Object.prototype.hasOwnProperty.call(node.edges, String(selected));
      fields.push({ field: node.field, selected: valid ? String(selected) : null });
      if (!valid) return { status: "pending", nextField: node.field, fields: fields };
      var destination = node.edges[String(selected)];
      if (destination.indexOf("result:") === 0) {
        return { status: "result", outcome: destination.slice(7), fields: fields };
      }
      if (destination.indexOf("unrepresented:") === 0) {
        return { status: "unrepresented", reason: destination.slice(14), fields: fields };
      }
      nodeId = destination;
    }
    throw new Error("Grafo com possível ciclo");
  }

  /* Apenas ramos com desfecho transcrito são oferecidos na interface.
   * "Não representado" não significa clinicamente impossível — é apenas
   * uma lacuna do material original, documentada para revisão acadêmica.
   */
  function hasRepresentedOutcome(destination, visited) {
    if (destination.indexOf("result:") === 0) return true;
    if (destination.indexOf("unrepresented:") === 0) return false;
    if (visited[destination]) throw new Error("Ciclo no grafo: " + destination);
    var node = GRAPH[destination];
    if (!node) throw new Error("Destino desconhecido: " + destination);
    var nextVisited = Object.assign({}, visited);
    nextVisited[destination] = true;
    return Object.keys(node.edges).some(function (value) {
      return hasRepresentedOutcome(node.edges[value], nextVisited);
    });
  }

  function availableOptions(values, targetField) {
    values = values || {};
    var nodeId = "surface";
    for (var i = 0; i < 12; i += 1) {
      var node = GRAPH[nodeId];
      if (!node) throw new Error("Nó inválido: " + nodeId);
      if (node.field === targetField) {
        return Object.keys(node.edges).filter(function (value) {
          return hasRepresentedOutcome(node.edges[value], {});
        });
      }
      var selected = values[node.field];
      if (selected === null || selected === undefined ||
          !Object.prototype.hasOwnProperty.call(node.edges, String(selected))) return [];
      var destination = node.edges[String(selected)];
      if (destination.indexOf("result:") === 0 ||
          destination.indexOf("unrepresented:") === 0) return [];
      nodeId = destination;
    }
    return [];
  }

  return {
    fields: FIELDS,
    evaluate: evaluate,
    availableOptions: availableOptions,
    graph: GRAPH,
    source: "Meyer-Lueckel H, Paris S. Oper Dent. 2016;41(S7):S35–S47. doi:10.2341/15-022-O",
    status: "Transcrição de slides, ainda não validada clinicamente"
  };
}));
