# Revisão clínica necessária — ICDASQuiz (UFJF-GV)

**Situação:** material didático **não validado clinicamente**. Este documento é um pacote para revisão pelo Prof. Dr. Rodrigo Varella de Carvalho, não um parecer clínico.

## Fontes usadas para este pacote

- `static/js/arvore_modelo.js` — transcrição provisória do grafo e destinos atuais, fonte do quadro abaixo.
- `descricoes.json` — títulos e explicações clínicas mostradas no quiz e na galeria.
- `docs/ARVORE_TRATAMENTO.md` — limitações declaradas na transcrição e interfaces do projeto.
- Referência indicada no handoff e na árvore: Meyer-Lueckel H, Paris S. *When and How to Intervene in the Caries Process.* Oper Dent. 2016;41(S7):S35–S47. doi:10.2341/15-022-O. **A correspondência ao artigo ainda precisa ser conferida pelo orientador.**

A enumeração do modelo atual contém **53 trajetos com saída registrada** e **7 trajetos explicitamente sem desfecho transcrito**. A ausência de ramo não significa conduta clinicamente impossível. Nenhum desfecho foi inventado ou liberado nesta implementação.

## Itens para conferência e assinatura

- [ ] Comparar os códigos ICDAS 0–6 e os textos de `descricoes.json` com os critérios de classificação aceitos na disciplina, especialmente os requisitos de secagem para 1 e 2.
- [ ] Conferir a semântica de cada desfecho **P / NI / MI / I** e destinos compostos **NI/MI**, **MI/I**.
- [ ] Conferir os ramos oclusais e proximais, incluindo atividade, risco e profundidade radiográfica, utilizando as referências originais.
- [ ] Resolver ou manter explicitamente como *não representados* os sete trajetos abaixo; não preenchê-los sem fonte.
- [ ] Confirmar os textos de conduta que podem soar prescritivos no código 5 e no código 6; manter a ressalva de uso didático.
- [ ] Verificar o desenho do corte esquemático (esmalte, dentina, polpa) e a prévia de extensão — são **ilustrações**, não radiografias nem mensuração anatômica.
- [ ] Autorizar expressamente o uso em contexto acadêmico com as ressalvas adequadas, ou solicitar correções por escrito.

## Lacunas atuais do grafo

1. Superfície: Oclusal → Classificação ICDAS: 4 → Atividade da lesão: Inativa — Lacuna — Oclusal 4–6 com N
2. Superfície: Oclusal → Classificação ICDAS: 5 → Atividade da lesão: Inativa — Lacuna — Oclusal 4–6 com N
3. Superfície: Oclusal → Classificação ICDAS: 6 → Atividade da lesão: Inativa — Lacuna — Oclusal 4–6 com N
4. Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 3 — Lacuna — Proximal sem radiolucidez, ICDAS 3–6
5. Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 4 — Lacuna — Proximal sem radiolucidez, ICDAS 3–6
6. Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 5 — Lacuna — Proximal sem radiolucidez, ICDAS 3–6
7. Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 6 — Lacuna — Proximal sem radiolucidez, ICDAS 3–6

## Inventário completo dos trajetos a conferir

| Nº | Percurso registrado no grafo | Desfecho atual |
|---:|---|---|
| 1 | Superfície: Oclusal → Classificação ICDAS: 0 → Risco de cárie: Baixo | P |
| 2 | Superfície: Oclusal → Classificação ICDAS: 0 → Risco de cárie: Alto | NI/MI |
| 3 | Superfície: Oclusal → Classificação ICDAS: 1 → Atividade da lesão: Ativa → Profundidade na radiografia: Sem alteração ou somente esmalte → Risco de cárie: Baixo | NI |
| 4 | Superfície: Oclusal → Classificação ICDAS: 1 → Atividade da lesão: Ativa → Profundidade na radiografia: Sem alteração ou somente esmalte → Risco de cárie: Alto | MI |
| 5 | Superfície: Oclusal → Classificação ICDAS: 1 → Atividade da lesão: Ativa → Profundidade na radiografia: Atinge a dentina → Risco de cárie: Baixo | NI |
| 6 | Superfície: Oclusal → Classificação ICDAS: 1 → Atividade da lesão: Ativa → Profundidade na radiografia: Atinge a dentina → Risco de cárie: Alto | MI/I |
| 7 | Superfície: Oclusal → Classificação ICDAS: 1 → Atividade da lesão: Inativa | P |
| 8 | Superfície: Oclusal → Classificação ICDAS: 2 → Atividade da lesão: Ativa → Profundidade na radiografia: Sem alteração ou somente esmalte → Risco de cárie: Baixo | NI |
| 9 | Superfície: Oclusal → Classificação ICDAS: 2 → Atividade da lesão: Ativa → Profundidade na radiografia: Sem alteração ou somente esmalte → Risco de cárie: Alto | MI |
| 10 | Superfície: Oclusal → Classificação ICDAS: 2 → Atividade da lesão: Ativa → Profundidade na radiografia: Atinge a dentina → Risco de cárie: Baixo | NI |
| 11 | Superfície: Oclusal → Classificação ICDAS: 2 → Atividade da lesão: Ativa → Profundidade na radiografia: Atinge a dentina → Risco de cárie: Alto | MI/I |
| 12 | Superfície: Oclusal → Classificação ICDAS: 2 → Atividade da lesão: Inativa | P |
| 13 | Superfície: Oclusal → Classificação ICDAS: 3 → Atividade da lesão: Ativa → Profundidade na radiografia: Sem alteração ou somente esmalte → Risco de cárie: Baixo | MI/I |
| 14 | Superfície: Oclusal → Classificação ICDAS: 3 → Atividade da lesão: Ativa → Profundidade na radiografia: Sem alteração ou somente esmalte → Risco de cárie: Alto | MI/I |
| 15 | Superfície: Oclusal → Classificação ICDAS: 3 → Atividade da lesão: Ativa → Profundidade na radiografia: Atinge a dentina → Risco de cárie: Baixo | MI/I |
| 16 | Superfície: Oclusal → Classificação ICDAS: 3 → Atividade da lesão: Ativa → Profundidade na radiografia: Atinge a dentina → Risco de cárie: Alto | I |
| 17 | Superfície: Oclusal → Classificação ICDAS: 3 → Atividade da lesão: Inativa | P |
| 18 | Superfície: Oclusal → Classificação ICDAS: 4 → Atividade da lesão: Ativa | I |
| 19 | Superfície: Oclusal → Classificação ICDAS: 4 → Atividade da lesão: Inativa | **Lacuna — Oclusal 4–6 com N** |
| 20 | Superfície: Oclusal → Classificação ICDAS: 5 → Atividade da lesão: Ativa | I |
| 21 | Superfície: Oclusal → Classificação ICDAS: 5 → Atividade da lesão: Inativa | **Lacuna — Oclusal 4–6 com N** |
| 22 | Superfície: Oclusal → Classificação ICDAS: 6 → Atividade da lesão: Ativa | I |
| 23 | Superfície: Oclusal → Classificação ICDAS: 6 → Atividade da lesão: Inativa | **Lacuna — Oclusal 4–6 com N** |
| 24 | Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 0 → Risco de cárie: Baixo | P |
| 25 | Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 0 → Risco de cárie: Alto | NI |
| 26 | Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 1 → Atividade da lesão: Ativa | NI |
| 27 | Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 1 → Atividade da lesão: Inativa | P |
| 28 | Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 2 → Atividade da lesão: Ativa | NI |
| 29 | Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 2 → Atividade da lesão: Inativa | P |
| 30 | Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 3 | **Lacuna — Proximal sem radiolucidez, ICDAS 3–6** |
| 31 | Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 4 | **Lacuna — Proximal sem radiolucidez, ICDAS 3–6** |
| 32 | Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 5 | **Lacuna — Proximal sem radiolucidez, ICDAS 3–6** |
| 33 | Superfície: Proximal → Profundidade na radiografia: Sem alteração visível → Classificação ICDAS: 6 | **Lacuna — Proximal sem radiolucidez, ICDAS 3–6** |
| 34 | Superfície: Proximal → Profundidade na radiografia: Metade externa do esmalte → Classificação ICDAS: 0 → Atividade da lesão: Ativa → Risco de cárie: Baixo | NI |
| 35 | Superfície: Proximal → Profundidade na radiografia: Metade externa do esmalte → Classificação ICDAS: 0 → Atividade da lesão: Ativa → Risco de cárie: Alto | NI/MI |
| 36 | Superfície: Proximal → Profundidade na radiografia: Metade externa do esmalte → Classificação ICDAS: 0 → Atividade da lesão: Inativa | P |
| 37 | Superfície: Proximal → Profundidade na radiografia: Metade externa do esmalte → Classificação ICDAS: 1 → Atividade da lesão: Ativa → Risco de cárie: Baixo | NI |
| 38 | Superfície: Proximal → Profundidade na radiografia: Metade externa do esmalte → Classificação ICDAS: 1 → Atividade da lesão: Ativa → Risco de cárie: Alto | NI/MI |
| 39 | Superfície: Proximal → Profundidade na radiografia: Metade externa do esmalte → Classificação ICDAS: 1 → Atividade da lesão: Inativa | P |
| 40 | Superfície: Proximal → Profundidade na radiografia: Metade externa do esmalte → Classificação ICDAS: 2 → Atividade da lesão: Ativa → Risco de cárie: Baixo | NI |
| 41 | Superfície: Proximal → Profundidade na radiografia: Metade externa do esmalte → Classificação ICDAS: 2 → Atividade da lesão: Ativa → Risco de cárie: Alto | NI/MI |
| 42 | Superfície: Proximal → Profundidade na radiografia: Metade externa do esmalte → Classificação ICDAS: 2 → Atividade da lesão: Inativa | P |
| 43 | Superfície: Proximal → Profundidade na radiografia: Metade externa do esmalte → Classificação ICDAS: 3 | I |
| 44 | Superfície: Proximal → Profundidade na radiografia: Metade externa do esmalte → Classificação ICDAS: 4 | I |
| 45 | Superfície: Proximal → Profundidade na radiografia: Metade externa do esmalte → Classificação ICDAS: 5 | I |
| 46 | Superfície: Proximal → Profundidade na radiografia: Metade externa do esmalte → Classificação ICDAS: 6 | I |
| 47 | Superfície: Proximal → Profundidade na radiografia: Esmalte interno ou dentina superficial → Classificação ICDAS: 0 → Atividade da lesão: Ativa → Risco de cárie: Baixo | NI |
| 48 | Superfície: Proximal → Profundidade na radiografia: Esmalte interno ou dentina superficial → Classificação ICDAS: 0 → Atividade da lesão: Ativa → Risco de cárie: Alto | MI |
| 49 | Superfície: Proximal → Profundidade na radiografia: Esmalte interno ou dentina superficial → Classificação ICDAS: 0 → Atividade da lesão: Inativa | P |
| 50 | Superfície: Proximal → Profundidade na radiografia: Esmalte interno ou dentina superficial → Classificação ICDAS: 1 → Atividade da lesão: Ativa → Risco de cárie: Baixo | NI |
| 51 | Superfície: Proximal → Profundidade na radiografia: Esmalte interno ou dentina superficial → Classificação ICDAS: 1 → Atividade da lesão: Ativa → Risco de cárie: Alto | MI |
| 52 | Superfície: Proximal → Profundidade na radiografia: Esmalte interno ou dentina superficial → Classificação ICDAS: 1 → Atividade da lesão: Inativa | P |
| 53 | Superfície: Proximal → Profundidade na radiografia: Esmalte interno ou dentina superficial → Classificação ICDAS: 2 → Atividade da lesão: Ativa → Risco de cárie: Baixo | NI |
| 54 | Superfície: Proximal → Profundidade na radiografia: Esmalte interno ou dentina superficial → Classificação ICDAS: 2 → Atividade da lesão: Ativa → Risco de cárie: Alto | MI |
| 55 | Superfície: Proximal → Profundidade na radiografia: Esmalte interno ou dentina superficial → Classificação ICDAS: 2 → Atividade da lesão: Inativa | P |
| 56 | Superfície: Proximal → Profundidade na radiografia: Esmalte interno ou dentina superficial → Classificação ICDAS: 3 | I |
| 57 | Superfície: Proximal → Profundidade na radiografia: Esmalte interno ou dentina superficial → Classificação ICDAS: 4 | I |
| 58 | Superfície: Proximal → Profundidade na radiografia: Esmalte interno ou dentina superficial → Classificação ICDAS: 5 | I |
| 59 | Superfície: Proximal → Profundidade na radiografia: Esmalte interno ou dentina superficial → Classificação ICDAS: 6 | I |
| 60 | Superfície: Proximal → Profundidade na radiografia: Dentina média ou profunda | I |

## Registro de aprovação

Orientador responsável: __________________________________  Data: ____ / ____ / ______

Parecer / correções requeridas: ______________________________________________

**Não alterar as condutas no software nem retirar o aviso “em revisão clínica” sem essa conferência.**