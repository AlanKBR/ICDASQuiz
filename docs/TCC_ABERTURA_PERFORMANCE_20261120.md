# ICDASQuiz — Auditoria de performance, Browser Stack e entrega offline V0.10.2

**Data:** 20/11/2026
**Owner:** ICDASQuiz / TCC (somente protótipo Three.js)
**Root:** /srv/repos/owned/ICDASQuiz
**Protótipo:** tools/tcc-opening-prototype/
**Acesso:** http://100.71.144.115:54173/ (privado no Tailscale)

## 1. Estado criativo preservado

**V0.10 foi a versão visual aprovada pelo usuário.** V0.10.1 alterou desempenho e infraestrutura; V0.10.2 adapta o runtime para distribuição offline, mantendo o roteiro aprovado.

1. **Título:** ICDAS branco frio, Quiz em menta com breathing; aguarda primeiro avanço manual.
2. **Primeiro avanço (4,25 s):** título 0,8 s; desdobramento 1,4 s; condensação 1,6 s; acomodação 0,45 s. Quatro coreografias continuam disponíveis; preferida na prática: **04 Dobra espacial** com mini letras translúcidas originadas dos traços das letras principais.
3. **Dente ASCII:** espera pelo segundo avanço enquanto gira. Usa apenas as nove letras `I C D A S Q u i z`.
4. **Segundo avanço (5 s):** ASCII → glTF 3D PBR sólido → oclusal/monitor → aquecimento gradual do esmalte branco para creme → fotografia real.
5. **Quiz demonstrativo (7 s padrão):** tempo de leitura; cursor passa por 5 e 2, clica no 3 (erro vermelho/tremor), depois no 4 (check verde). Isso **não valida clinicamente** o código ICDAS da fotografia.
6. **Vídeo (~4 s):** giro de câmera, apresentador/aceno, retorno e primeiro slide do TCC. Raccord de quadro com o quiz preservado.

**Duração ativa:** 4,25 + 5 + 7 + 4 = **20,25 segundos**, excluindo as duas esperas manuais.

## 2. Medições (antes/depois)

Medições dos arquivos e servidor de 20/11/2026. As medidas de renderização no Chromium do Browser Stack estão documentadas na seção 2.1. **Ainda não são medições na GPU do Legion**.

| Item | V0.10 | V0.10.1 | Resultado |
|---|---:|---:|---|
| Texturas do molar | 2 × 4096² | 2 × 2048² | −75% de texels |
| PNG base color | 1.054.818 B | 513.359 B | −51,3% |
| PNG normal | 924.786 B | 397.479 B | −57,0% |
| VRAM teórica das 2 texturas, com mipmaps, RGB8–RGBA8 | 128–171 MiB | 32–43 MiB | −75% estimados |
| Pasta public/ | 14.560 KiB | 7.172 KiB | −50,7% |
| Pasta dist/ (inclui novos .gz) | 15.216 KiB | aproximadamente 9.360 KiB | ~−38,5% |
| JavaScript bruto → gzip | 648.006 B | 163.178 B | −74,8% transferido |
| Geometria binária bruta → gzip | 2.532.096 B | 1.385.965 B | −45,3% transferido |
| HTTP Range do vídeo | 200 (arquivo todo) | 206 Partial Content | Seeking correto |
| Geometria do glTF | 28.875 vértices / 57.008 triângulos | Idêntica | Sem perda geométrica |
| Microbenchmark CPU, mudança de densidade ASCII (Node) | ~4,04 ms | ~0,56 ms | ~−86% nesse teste |

**Qualidade da textura:** base color reduzida por LANCZOS, normal map por BOX. Comparação da textura de 2K reampliada contra a original de 4K: PSNR **39,30 dB** (base color) e **65,26 dB** (normal map). São métricas de pixel, **não** avaliação estética do modelo renderizado. Fonte 4K íntegra no ZIP original.

**VRAM:** estimativa de RGB8/RGBA8 com mipmaps, não leitura real do driver. Render targets e outros recursos não incluídos.

**Pasta pública:** a redução de arquivos não acessados reduz ocupação e exposição, mas não deve ser atribuída integralmente à redução de tráfego da página. O tráfego realmente melhora por texturas menores e HTTP gzip.

**CPU:** microbenchmark Node sobre o glTF real, mediana de 5 execuções, 1.800 pontos. Preparação antiga reconstruía pesos de áreas e MeshSurfaceSampler a cada ajuste de densidade; versão nova reutiliza amostradores. Isso não equivale a uma medição de FPS no navegador. Reproduzir com `node tools/bench_sampling.mjs`.

## 3. Alterações executadas

- Texturas de trabalho 4K → 2K pelo script `tools/optimize_textures.py`; fonte inalterada em `assets/maxillary_first_molar.zip`.
- Quatro cópias desnecessárias retiradas de `public/assets/`; arquivos originais permanecem em `assets/` ou correspondem ao vídeo final ainda servido. `tools/recompose_video.py` lê o original da pasta privada.
- Reutilização do MeshSurfaceSampler; otimização da área para modelo de apenas uma malha; sem alterar posições finais ou efeitos.
- Redução de mutações DOM: escrever texto somente quando diferente; não executar draws WebGL ocultos pelo vídeo, slide final, quiz estático ou aba oculta.
- Painel de telemetria **desativado por padrão**: FPS médio, intervalo de quadro p95, custo de CPU de renderer.render (não tempo GPU), draw calls, triângulos e número de texturas. Escala de renderização 1,7× original / 1,35× / 1×; alternativa de emergência em 0,75×. Outras escalas são limitadas ao DPR físico.
- `npm run build` gera arquivos comprimidos via `tools/prepare_dist.mjs`. Servidor `tools/preview_server.py` usa HTTP/1.1, gzip, caching longo somente para JS/CSS versionados com hash, byte-range 206/416 para MP4. Sem dependências externas, vinculado exclusivamente ao IP Tailscale.
- Originais privados, ZIP, vídeo e foto permanecem fora do Git; sem alteração no aplicativo principal.

## 4. Evidências de validação

- JavaScript verificado por `node --check`; build Vite e precompressão executados.
- Arquivos gzip foram descompactados e comparados por SHA-256 com os arquivos originais (iguais).
- Servidor testado primeiro em porta privada temporária 54174; respostas **200**, gzip, **206** (intervalo de 10 bytes entregou 10 bytes) e **416**; depois ativado na porta privada 54173. Porta temporária fechada.
- Ponto de acesso atual: `http://100.71.144.115:54173/`.
- Texto, glTF, vídeo e scripts validados estaticamente.
- **O Browser Stack V2 permitiu teste real WebGL** após liberar a origem de loopback do protótipo pelo mecanismo próprio `zezin-browser loopback grant`. Os números estão na seção 2.1. Esses testes são do browser compartilhado Cloak, **não** do Legion; as métricas do notebook ainda devem ser coletadas localmente.

## 5. Limites, riscos e prioridades

1. **Alta / antes da defesa:** inspecionar paridade visual do dente com textura 2K no Legion. Se perceptivelmente inferior, restaurar as texturas originais 4K do ZIP (reversível).
2. **Alta / antes da defesa:** testar FPS médio, p95 e reprodução do vídeo no Legion/projetor real. Objetivo orientativo em tela de 60 Hz: ~60 FPS e p95 perto ou abaixo de ~20 ms, sem garantia; ajustar escala 1,7× → 1,35× caso necessário.
3. **Alta / apresentação real:** usar o pacote offline entregue e ensaiar a versão incorporada ao deck, além de manter um vídeo de contingência.
4. **Média:** a prévia HTTP é provisória após reboot; existe comando de reinício no README. Não foi criado serviço permanente nem rota pública.
5. **Média:** preservar fontes privadas fora de repositório, com cópia segura antes de migrações; não expor fotos pessoais em hospedagem pública sem autorização.
6. **Baixa:** compressões avançadas Draco/KTX2, mudança de framework, remoção agressiva de geometria. Não justificadas sem benchmark gráfico real, pois introduzem complexidade e risco de alterar o resultado.

**Decisão documentada:** V0.10 = conteúdo visual aprovado; V0.10.1 = execução otimizada; V0.10.2 = versão portátil e integrável offline. A paridade estética após redução da textura e a performance final dependem de inspeção no Legion.

## 2.1. Perfil real no Browser Stack — Chromium Cloak

O Browser Stack foi acessado pelo seu mecanismo de sessão, com a prévia servida via loopback autorizado (o contêiner Chromium não tinha rota direta para o IP Tailscale). Medição em aba visível, viewport 1928×963, DPR reportado 1. A coleta usa intervalos de `requestAnimationFrame` com fases identificadas pelo texto de estado da aplicação, sem inferir tempo de GPU.

| Fase | FPS médio (escala interna 1×) | p95 | FPS médio (0,75×) | p95 (0,75×) |
|---|---:|---:|---:|---:|
| Título em espera | 56,9 | 33,2 ms | — | — |
| Formação título → ASCII | 53,0 | 33,3 ms | 59,3 | 16,7 ms |
| Dente ASCII em espera | 56,7 | 33,3 ms | 58,1 | 16,8 ms |
| ASCII → modelo texturizado | 50,0 | 33,4 ms | 56,0 | 33,3 ms |
| Orientação oclusal | 52,9 | 33,3 ms | 57,1 | 16,8 ms |
| Encaixe no monitor | 58,0 | 16,7 ms | 60,0 | 16,7 ms |
| Fotografia final | 60,0 | 16,8 ms | — | — |
| Quiz cenográfico | 60,0 | 16,7 ms | 60,0 | 16,7 ms |
| Vídeo | 60,0 | 16,7 ms | 60,0 | 16,7 ms |

**Leitura:** a fase ASCII → malha e a formação tipográfica concentraram as quedas de quadros, não o quiz/vídeo. Reduzir a resolução interna para **0,75×**, mantendo a mesma geometria, levou a formação de 53,0 para 59,3 FPS e o ASCII → mesh de 50,0 para 56,0 FPS nesse ambiente. Os quadros acima de 33,3 ms no segundo trecho caíram de 12 para 4. Isso justifica um **modo de emergência opcional**, mas não alterar a qualidade alta padrão no Legion.

**Limite de inferência:** o Cloak apresenta à página um identificador ANGLE/Intel UHD 630/D3D11 associado ao perfil; o usuário utiliza hardware diferente, e esse identificador pode ser mascarado. Portanto, os valores não representam a RTX 5080 do Legion nem demonstram desempenho em projetor. Não houve long tasks acima de 50 ms nos trechos amostrados. FPS deriva de intervalos entre callbacks de renderização, não de GPU timestamp queries. O modo 0,75× reduz a quantidade de pixels internos e pode diminuir nitidez; só usar se houver dificuldade na máquina da defesa.

**Integração offline:** Vite agora usa `--base ./` com recursos estáticos relativos no build; `?presentation=1` entrega apenas a cena 16:9, adequada a iframe no deck de mesma origem. `postMessage` aceita comandos de avanço e reset exclusivamente da janela-mãe mesma origem e emite estados `title`, `forming`, `asciiReady`, `mesh` e `finished`. O launcher offline é Python 3 stdlib vinculado a 127.0.0.1, com Range para MP4. O script `tools/package_offline.py` gera o pacote ZIP, com build, fonte, scripts, mídias autorizadas, licença e documentos de integração. O runtime não exige npm/internet.

## 7. Teste efetivo de portabilidade do ZIP

O pacote `ICDASQuiz_TCC_Abertura_V0.10.2_OFFLINE.zip` foi extraído para uma pasta temporária, e os arquivos de seu manifesto foram conferidos individualmente por SHA-256. O launcher `python3 run_offline.py --no-browser --port 54176` iniciou o servidor exclusivamente em 127.0.0.1, com **HTTP 200** para HTML/glTF, **206** para intervalo de MP4 e **gzip** para HTML. O vídeo aprovado do pacote foi comparado por SHA-256 com o MP4 fonte da versão criativa; corresponde exatamente.

O **Browser Stack Chromium real** abriu o pacote extraído em `/?presentation=1`: cena 16:9, inspetor oculto, WebGL2 inicializado, nenhum erro JavaScript e nenhum recurso carregado de origem externa à porta localhost. Para simular a integração do agente, um segundo servidor local serviu `site/index.html?presentation=1` sob subpasta e um documento-pai no mesmo domínio enviou dois comandos `postMessage` de avanço. Os eventos retornados foram, nesta ordem, **title → forming → asciiReady → mesh → finished**, sem erros no console de exceções. Isso valida o contrato do iframe, não o comportamento específico do deck definitivo do outro agente.

O pacote contém o build estático com assets/mídia, código-fonte editável, scripts de início para Linux/Windows, servidor Python stdlib, instruções de integração, créditos de licença e relatórios. Nenhum npm, servidor Zezin, Tailscale ou internet é necessário para **executar** os arquivos extraídos, desde que haja Python 3 e um navegador com WebGL2. Os originais 4K permanecem no Zezin, fora deste pacote portátil de produção.
