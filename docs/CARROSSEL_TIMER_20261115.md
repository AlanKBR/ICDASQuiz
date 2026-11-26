# ICDASQuiz — carrossel completo e cronômetro de 5 s (15/11/2026)

## Mudanças

- O carrossel da landing não reutiliza mais a lista fixa de sete imagens, uma por código, usada na escala. A rota `home()` monta duas **permutações aleatórias independentes de todas as fotos públicas válidas** de `get_imagens()`, uma para cada faixa. O conjunto completo aparece uma vez em cada faixa antes da duplicação visual necessária ao ciclo contínuo. A ordem é nova em cada resposta HTML; nenhum gabarito do quiz privado é exposto.
- A animação mantém o loop sem salto de meio espaçamento usando `translateX(calc(-50% - var(--marquee-gap)/2))`. As faixas seguem direções e durações diferentes: 5/6 segundos por foto no desktop, 4/5 no celular. Os tempos são aplicados por CSSOM no JavaScript já carregado (`redesign.js`), respeitando o CSP sem estilos inline. Há uma duração CSS de fallback caso JS não rode.
- As fotografias continuam em WebP, com `loading="lazy"`, `decoding="async"`, tamanho declarado e `aria-hidden` na faixa decorativa. O navegador reaproveita as mesmas URLs de imagem nas duas cópias de cada sequência. A animação para totalmente com `prefers-reduced-motion: reduce`.
- A animação circular de 5 segundos antes era um `conic-gradient` girando infinitamente, sem representar uma contagem. Foi substituída por um botão de cronômetro real: clique/teclado inicia ou reinicia 5 segundos, número atualiza, anel SVG esvazia proporcionalmente, conclusão fica indicada com um ✓ e texto acessível. A contagem é baseada em `performance.now()`/`requestAnimationFrame`, não em contagem de frames; a aba oculta pausa e retoma sem descontar o tempo oculto. Há `role="status"` para início/pausa/conclusão.
- O cronômetro é um auxílio de estudo para o requisito de secagem; **não** atesta que uma superfície clínica esteja adequadamente seca.

## Verificações

- Testes automatizados confirmam que cada faixa tem todos os IDs do acervo sem duplicatas no primeiro ciclo, que as sequências são diferentes e que cada ciclo contém duas cópias idênticas para o loop. A imagem destacada da escala segue escolhida independentemente.
- Chrome 155: com 34 imagens reconhecidas no acervo após a inclusão de mais cinco fotografias, cada faixa rendeu 68 elementos com 34 URLs distintas e sequência duplicada exatamente; nenhuma rolagem horizontal. O passo da cópia visual e a translação calculada coincidiram (erro de borda = 0 px). Duração proporcional: móvel 4/5 s por foto, desktop 5/6 s por foto; testada em navegador após atualização do acervo. Chrome confirmou execução do timer, progresso parcial, conclusão e reinício, sem erros de JS nem violações automáticas de acessibilidade na landing. Com movimento reduzido, a animação do carrossel é `none` e o cronômetro continua operável.
- `python -m pytest tests.py -q`, `node --check` em `static/js/{redesign,dry-timer}.js`, `python3 tools/build_web_css.py --check`, build Docker isolado e verificações pós-deploy.

## Limites

O carrossel é decorativo e a ordem é aleatória por requisição HTML, mas pode ficar fixa durante a exibição da mesma página, como esperado para não causar rearranjo brusco de imagens. Cabeçalhos `Cache-Control: no-store` e `cf-cache-status: DYNAMIC` na landing foram verificados; um reload solicita uma nova ordenação. A avaliação clínica da árvore permanece separada.
