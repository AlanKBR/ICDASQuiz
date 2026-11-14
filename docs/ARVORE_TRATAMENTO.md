# Árvore de tratamento — integração à página inicial

Estado: **versão visual com SVG de corte consolidada no ICDASQuiz** e incorporada à home. A transcrição clínica continua pendente de validação com o professor Rodrigo Varella de Carvalho.

## Experiência adotada

- A home apresenta a árvore diretamente após a introdução do estudo, dentro da própria página, **sem iframe** nem navegação obrigatória para outra tela.
- Em desktop, uma apresentação compacta fica à esquerda e a árvore à direita; em tablets/celulares os elementos ficam empilhados. O link **Tratamento** na navegação leva ao trecho correspondente da home.
- A rota /arvore-de-tratamento permanece disponível para leitura isolada. Ambas usam **um único template compartilhado**, templates/_arvore_tratamento_widget.html, com o mesmo JS, CSS e dados.
- **Etapas sem numeração:** apenas os títulos dos achados permanecem. Os números 0–6 dentro dos círculos são códigos ICDAS, não números das fases.
- O questionário antigo de *classificação ICDAS* da home foi retirado para evitar dois fluxos distintos na mesma tela. O conteúdo teórico, incluindo a **tabela de códigos ICDAS**, segue disponível no acordeão.
- A árvore mantém um único desenho radiográfico **em corte** e não oferece o antigo modo Camadas. São ilustrações esquemáticas, **não radiografias reais**.
- As alternativas não selecionadas continuam cinzas e clicáveis. O SVG conecta apenas o trajeto ativo com duas formas reutilizáveis (traço e pontas), ancoradas nos elementos efetivos da interface.
- Os códigos são círculos responsivos cuja largura acompanha o **próprio container** para caberem na mesma linha mesmo quando a árvore está dentro da seção da home.
- Alternativas só aparecem quando existe saída representada nos slides; omissões do material não foram convertidas em recomendações clínicas.

## Ownership

- app.py — rota dedicada Flask.
- templates/index.html — integração nativa da seção na home.
- templates/arvore_tratamento.html — rota de estudo isolada.
- templates/_arvore_tratamento_widget.html — única composição HTML da árvore.
- static/js/arvore_modelo.js — grafo do material e filtro das saídas transcritas.
- static/js/arvore_tratamento.js — interação, desenho em corte e posicionamento das setas.
- `static/css/arvore_tratamento.css` e o bundle `static/css/app.css` — árvore e composição responsiva da home.
- `static/js/redesign.js` — interações progressivas da landing; o questionário antigo foi removido.
- tests.py e tools/test_arvore_modelo.cjs — testes de integração e do grafo.

Não foi introduzida nenhuma migração, escrita de banco, chamada externa ou dependência JS nova.

## Limitações acadêmicas

Fonte indicada nos slides: Meyer-Lueckel H, Paris S. *When and How to Intervene in the Caries Process.* Oper Dent. 2016;41(S7):S35–S47. DOI 10.2341/15-022-O.

Permanecem para confirmação com o orientador:
1. S/N como atividade e B/A como risco.
2. Sentido das saídas separadas por barra.
3. Ramos ausentes: oclusal ICDAS 4–6 com N; proximal sem radiolucidez e ICDAS 3–6.
4. Termos radiográficos, equivalência exata com os slides e autoria/atribuição das figuras para o TCC.

O código da home e da árvore **não deve ser descrito no TCC como protocolo de tratamento clinicamente validado** antes dessa revisão.

## Validação

- Testes Python e do grafo com SQLite descartável e Docker construído sem acesso ao PostgreSQL de produção.
- Navegador real em 320, 390, 768, 1024 e 1440 px: a árvore funciona na home e na rota isolada, não causa overflow horizontal, mantém todos os códigos circulares na mesma linha e preserva o comportamento de mudança de ramo/resultado.
- Produção, PostgreSQL e documento do TCC permanecem fora do escopo desta integração.
