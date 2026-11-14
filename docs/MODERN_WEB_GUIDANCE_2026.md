# Modern Web Guidance — decisões do ICDASQuiz (14/11/2026)

## Fonte

Guias oficiais em https://github.com/GoogleChrome/modern-web-guidance-src, revisão consultada `5e5cd33a7738f21281e3027732bcbd58cfa82bf1` (14/11/2026). A referência é um catálogo de recomendações, não uma dependência de execução. A ferramenta `legacy-scan` foi usada sob demanda e não foi instalada no runtime.

## Adoção

- **Prioridade de imagens:** foto principal da landing e imagem clínica do quiz usam `fetchpriority="high"`, sem `loading="lazy"`; fotos do acervo fora da dobra usam lazy nativo. Foto do segundo cartão inicial usa prioridade baixa. O marquee usa apenas duas repetições por direção em vez de quatro.
- **Fontes:** Onest WOFF2 auto-hospedada, `font-display:swap`; preload e `@font-face` resolvem a mesma URL com nome derivado do SHA-256. Evita duas requisições da mesma fonte. Fontes externas não são usadas.
- **CSS:** `src/css/{design-tokens,design-components,redesign}.css` são a fonte editável; `python3 tools/build_web_css.py` gera `static/css/app.css`. A navegação carrega um único CSS do app, mais a árvore apenas nas rotas que a usam. Foram removidas a cadeia CSS antiga (Tailwind/custom/UI/landing) e as dependências Node/Tailwind que não eram mais necessárias.
- **JS:** funcionalidades progressivas são carregadas apenas nas páginas relevantes; não existe bundle de framework de frontend.
- **UI nativa:** `<dialog>` modal com `closedby="any"` e fallback mínimo; `commandfor`/`command` no zoom do quiz com fallback de invoker; `<progress>` nativo com representação segmentada decorativa; `details/summary` no menu; controles de formulário nativos e Enter compatível com IME.
- **Acessibilidade:** link de pular para o conteúdo, nomes semânticos, foco visível, contraste revisado, gráfico de atividade teclado/foco, cabeçalhos de tabela não vazios, células interativas rotuladas, `prefers-reduced-motion` mantido. Em telas de até 380px, as sete opções do quiz são distribuídas em duas linhas para manter alvos de toque de 44px.
- **Renderização:** `content-visibility:auto` e `contain-intrinsic-size` apenas para a árvore embutida e referências, abaixo da primeira dobra, evitando trabalho inicial desnecessário sem sacrificar a árvore acessível.
- **Backend:** o dashboard deixa de calcular a função legada de métricas além da nova. Consultas dos relatórios de 30/90 dias filtram o intervalo no SQL; o modo “tudo” preserva o histórico completo, sem mudança de schema. Expiração lazy das tentativas ativas continua preservada.

## Limites e validação

Os guias considerados *experimentais* ou que requerem API com suporte instável (ex.: CSS `@function` e Cross-Origin Storage) não foram introduzidos: aumentariam a superfície de compatibilidade sem benefício concreto para este site. Não foram instalados polyfills nem Service Worker.

A regressão é verificada por `python -m pytest tests.py -q`, `python3 tools/build_web_css.py --check` e pelo `legacy-scan` oficial quando disponível. O navegador de QA deve verificar 390×844 e 320×568, fluxo quiz, foto ampliada, galeria, área do professor, ausência de overflow e auditoria axe; testes automatizados não substituem avaliação com tecnologia assistiva humana. O servidor permanece em Flask + PostgreSQL/SQLite, sem DNS, migrations nem exposição adicionais.
