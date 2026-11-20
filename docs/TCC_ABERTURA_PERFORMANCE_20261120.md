# ICDASQuiz — Auditoria de performance e estado consolidado V0.10.1

**Data:** 20/11/2026
**Owner:** ICDASQuiz / TCC (somente protótipo Three.js)
**Root:** /srv/repos/owned/ICDASQuiz
**Protótipo:** tools/tcc-opening-prototype/
**Acesso:** http://100.71.144.115:54173/ (privado no Tailscale)

## 1. Estado criativo preservado

**V0.10 foi a versão visual aprovada pelo usuário.** V0.10.1 modifica apenas desempenho, preparação de assets, serviço HTTP e instrumentação.

1. **Título:** ICDAS branco frio, Quiz em menta com breathing; aguarda primeiro avanço manual.
2. **Primeiro avanço (4,25 s):** título 0,8 s; desdobramento 1,4 s; condensação 1,6 s; acomodação 0,45 s. Quatro coreografias continuam disponíveis; preferida na prática: **04 Dobra espacial** com mini letras translúcidas originadas dos traços das letras principais.
3. **Dente ASCII:** espera pelo segundo avanço enquanto gira. Usa apenas as nove letras `I C D A S Q u i z`.
4. **Segundo avanço (5 s):** ASCII → glTF 3D PBR sólido → oclusal/monitor → aquecimento gradual do esmalte branco para creme → fotografia real.
5. **Quiz demonstrativo (7 s padrão):** tempo de leitura; cursor passa por 5 e 2, clica no 3 (erro vermelho/tremor), depois no 4 (check verde). Isso **não valida clinicamente** o código ICDAS da fotografia.
6. **Vídeo (~4 s):** giro de câmera, apresentador/aceno, retorno e primeiro slide do TCC. Raccord de quadro com o quiz preservado.

**Duração ativa:** 4,25 + 5 + 7 + 4 = **20,25 segundos**, excluindo as duas esperas manuais.

## 2. Medições (antes/depois)

Medições dos arquivos e servidor de 20/11/2026. Não foram obtidas métricas WebGL reais do Legion.

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
- Painel de telemetria **desativado por padrão**: FPS médio, intervalo de quadro p95, custo de CPU de renderer.render (não tempo GPU), draw calls, triângulos e número de texturas. Escala de renderização 1,7× original / 1,35× / 1×; limitada ao DPR real.
- `npm run build` gera arquivos comprimidos via `tools/prepare_dist.mjs`. Servidor `tools/preview_server.py` usa HTTP/1.1, gzip, caching longo somente para JS/CSS versionados com hash, byte-range 206/416 para MP4. Sem dependências externas, vinculado exclusivamente ao IP Tailscale.
- Originais privados, ZIP, vídeo e foto permanecem fora do Git; sem alteração no aplicativo principal.

## 4. Evidências de validação

- JavaScript verificado por `node --check`; build Vite e precompressão executados.
- Arquivos gzip foram descompactados e comparados por SHA-256 com os arquivos originais (iguais).
- Servidor testado primeiro em porta privada temporária 54174; respostas **200**, gzip, **206** (intervalo de 10 bytes entregou 10 bytes) e **416**; depois ativado na porta privada 54173. Porta temporária fechada.
- Ponto de acesso atual: `http://100.71.144.115:54173/`.
- Texto, glTF, vídeo e scripts validados estaticamente.
- **Nenhum navegador WebGL disponível no servidor**: não há número comprovado de FPS, jank ou tempo de GPU no Legion neste relatório. Os indicadores devem ser coletados com o painel da própria prévia.

## 5. Limites, riscos e prioridades

1. **Alta / antes da defesa:** inspecionar paridade visual do dente com textura 2K no Legion. Se perceptivelmente inferior, restaurar as texturas originais 4K do ZIP (reversível).
2. **Alta / antes da defesa:** testar FPS médio, p95 e reprodução do vídeo no Legion/projetor real. Objetivo orientativo em tela de 60 Hz: ~60 FPS e p95 perto ou abaixo de ~20 ms, sem garantia; ajustar escala 1,7× → 1,35× caso necessário.
3. **Alta / apresentação real:** preparar fallback **offline** independente de rede/Tailscale, com vídeo/slide e assets legalmente autorizados.
4. **Média:** a prévia HTTP é provisória após reboot; existe comando de reinício no README. Não foi criado serviço permanente nem rota pública.
5. **Média:** preservar fontes privadas fora de repositório, com cópia segura antes de migrações; não expor fotos pessoais em hospedagem pública sem autorização.
6. **Baixa:** compressões avançadas Draco/KTX2, mudança de framework, remoção agressiva de geometria. Não justificadas sem benchmark gráfico real, pois introduzem complexidade e risco de alterar o resultado.

**Decisão documentada:** V0.10 = conteúdo visual aprovado; V0.10.1 = execução otimizada mantendo roteiro e estilos. A paridade estética após redução da textura depende de última inspeção no Legion.
