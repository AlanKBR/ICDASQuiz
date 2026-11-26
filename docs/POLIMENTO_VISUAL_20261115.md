# ICDASQuiz — auditoria visual e microinterações (15/11/2026)

## Referência e escopo

Comparação em navegador Chrome com o handoff aprovado em `icdasquiz-design-handoff.zip` (capturas 01–11 desktop/mobile e arquivos HTML/CSS/JS do pacote). O objetivo foi corrigir pequenas inconsistências visuais sem alterar critérios clínicos, gabarito, banco de dados, autorização ou o fluxo do quiz.

## Falhas confirmadas e correções

1. **Miniquiz da landing, resposta errada:** o estado anterior apenas pintava a escolha incorreta e não destacava o número correto. Agora o correto é menta com contorno, o erro escolhido é lilás, os demais ficam discretos, e o chip sobre a foto informa `Era ICDAS X` ou `✓ ICDAS X`. O texto acessível esclarece ambas as alternativas; nenhuma resposta do quiz privado foi exposta.
2. **Feedback rápido demais:** a correção desaparecia em 1,65 segundo. O feedback permanece 2,2 segundos após acerto e 2,75 segundos após erro. A foto muda suavemente e os botões permanecem desabilitados durante a transição; o resultado final leva o foco ao CTA do quiz completo. O placar passa a informar `Acertos X/Y`.
3. **Animações ausentes ou discretas demais:** foram adicionados pop de acerto, shake discreto de erro, entrada do chip, feedback do quiz, fotografia, progresso e aparecimento pontual do botão Confirmar. A entrada de conteúdo educativo abaixo da primeira dobra usa IntersectionObserver e `opacity/transform`, com movimento reduzido respeitado. Não foram adicionados loops ou efeitos de confete ao fluxo clínico.
4. **Borda dos círculos recortada:** folga interna acima e ao redor das opções transforma o círculo sem encostar no topo do contêiner rolável. Os estados `correto`, `incorreto` e `esmaecido` receberam borda/cores consistentes. Verificação de geometria e captura após a transição em 320, 390, 768 e 1440 px.
5. **Pilha de fotos da landing:** os dois cartões decorativos voltaram a usar fotografias do acervo, como no handoff, com alt vazio e sem capturar clique. Nenhum asset de protótipo sintético foi publicado.
6. **Área de toque inconsistente:** navegação, links da escala, reset da árvore, ações secundárias e filtros ganharam altura mínima de 44 px. As opções de código da árvore agora mantêm 44 px mesmo em celulares estreitos, quebrando em duas linhas quando necessário.
7. **Regressão de layout durante o polish:** a regra global de altura mínima reexibia links ocultos do menu móvel e provocava rolagem horizontal. A precedência de `display:none` foi corrigida e revalidada em 320, 390, 768 e 1440 px.
8. **Painel de feedback em 320×568:** algumas explicações clínicas são longas demais para caber sem rolagem interna. Em vez de truncá-las ou sacrificar totalmente a foto, a região agora é focável, possui nome acessível e exibe uma barra de rolagem fina nesses dispositivos. O CTA continua fixo e visível. Na referência principal 390×844, o feedback foi validado sem rolagem adicional.

## Verificações

- `python3 tools/build_web_css.py --check`, `node --check` nos scripts alterados, `python -m pytest tests.py -q` e `git diff --check`.
- Navegador: miniquiz acertando, errando e bloqueando após duas respostas; foco levado ao CTA; Chrome em 320×568, 390×844, 768×900, 1440×900. Nenhuma rolagem horizontal nas páginas públicas inspecionadas. Estados de seleção, feedback e próximo passo visíveis, sem bordas cortadas.
- A11y: axe-core nos estados de acerto/erro do miniquiz, no quiz e no painel rolável de 320 px. `prefers-reduced-motion: reduce` mantém o feedback legível sem as animações.
- Testes de layout visual em emulação não equivalem a um teste com dois dedos em telefone físico, nem a um parecer clínico do orientador. O protocolo do ICDAS continua sob revisão acadêmica.

## Restrições operacionais

- A versão publicada usa o serviço Flask/PostgreSQL existente em Zezin; nenhuma migration foi adicionada.
- Antes do deploy, criar e testar um backup local/restore-canary, preservar a imagem anterior, atualizar `compose.yaml` e `service.toml`, executar `reconcile` e validar o site real.
- Código local pode ser publicado no host por fast-forward. **Não executar `git push` sem pedido explícito**. Indicar a divergência do GitHub se ocorrer.
