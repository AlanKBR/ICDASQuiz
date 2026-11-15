# ICDASQuiz — acabamento e QA do handoff de 14/11/2026

Referência visual: pacote original `icdasquiz-design-handoff.zip`, entregável `telas/` e `HANDOFF_GPT.md` (design aprovado nas fases 0–2). A implementação usa Flask/Jinja e os mesmos dados clínicos do repositório. Não foram criadas migrações nem dependências permanentes de frontend.

## Alinhamento implementado

- Landing: título com animação em sequência por palavra, blobs com movimento lento e CTA pós-miniquiz pulsante; somente com `prefers-reduced-motion: no-preference`. Indicador de 5 segundos com anel animado. O miniquiz de duas imagens preserva o uso de fotografias públicas sem revelar respostas de tentativas privadas.
- Escala: miniaturas agora abrem visualizador por código com todas as fotos públicas do código (sem buscar gabarito por API), navegação anterior/próxima, texto clínico de `descricoes.json` e indicação de secagem para 1/2. Link separado preserva acesso direto ao filtro na galeria.
- Galeria/zoom: modal nativo, com lightbox em tela cheia; no celular, folha inferior exibe o código, título, critério e controles, evitando texto clínico longo. O componente progressivo `static/js/image-zoom.js` suporta pinça de dois dedos, arraste da imagem quando ampliada, clique duplo, Ctrl+roda e teclado (+/−/0), sem bibliotecas extras. O CSS mantém `touch-action:none` no canvas quando o manipulador está ativo, e restaura o estado ao fechar.
- Árvore de tratamento: acrescenta um esquema SVG de corte dentário com rótulos Esmalte/Dentina/Polpa, prévia tracejada de profundidade/radiografia durante hover/foco e breadcrumbs de escolha para regressar. O **grafo original `static/js/arvore_modelo.js` e seus 53 destinos representados/7 lacunas não foram alterados**; a prévia visual não muda o estado clínico até clique. Avisos de revisão permanecem.
- Todas as outras rotas, correção do quiz no servidor, CSRF, rate limits, `noindex`, autorização do dashboard e exportação CSV continuam com o mesmo contrato.

## Gates

- `python -m pytest tests.py -q`: validar após cada mudança de código.
- `python3 tools/build_web_css.py --check`: o bundle acompanha o CSS editável.
- `node --check static/js/{scale,image-zoom,arvore_tratamento,galeria,quiz}.js`.
- Browser Stack real: 390×844, 320×568 e 1440×900, sem overflow horizontal; fluxo público e modal com teclado/foco; axe-core sem violações nos testes automatizados. Teste sintético de pinça com dois PointerEvents converteu escala 1× em 2,5×. **Não substitui teste no dispositivo Android físico com dois dedos.**
- Chrome `vitals --json`: medir LCP/CLS/FCP em condições de laboratório e verificar console, não apresentar como métricas de usuários reais. A API Google PageSpeed Insights retornou HTTP 429 por quota no dia da implementação; sem pontuação Lighthouse atribuível.

## Limites de aceitação

- **Professor:** `docs/REVIEW_CLINICA_ORIENTADOR.md` foi preparado, com todos os trajetos para conferência e sete lacunas. Ainda não há parecer/assinatura; o texto e a árvore permanecem marcados como didáticos e em revisão.
- **Placar público:** mantém a regra anterior de nomes declarados no ranking e nas sessões recentes. A mudança para pseudônimos/opt-in é decisão de produto e privacidade, não inferida do redesign; nenhuma identidade foi reclassificada silenciosamente.
- **Cloudflare Workers/D1:** migração e DNS ficam fora deste acabamento. A produção continua no Zezin (Flask/PostgreSQL, scale-to-zero por Sablier).
- **Offsite:** um backup criptografado foi transmitido ao Google Drive com SHA-256 verificado; monitoramento recorrente remoto ainda requer credencial e automação dedicados. Os backups e restore canary locais continuam configurados.
