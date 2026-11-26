# Protótipo da abertura 3D — ICDASQuiz

**Handoff canônico:** [../../docs/TCC_ABERTURA_3D_HANDOFF_20261117.md](../../docs/TCC_ABERTURA_3D_HANDOFF_20261117.md)

Protótipo isolado da aplicação ICDASQuiz. Não altera rotas, produção ou dados clínicos.

## URL de revisão

Enquanto o processo estiver ativo no servidor Zezin e o Legion estiver conectado ao Tailscale:

http://100.71.144.115:54173/

Servidor HTTP vinculado exclusivamente ao endereço Tailscale (`100.71.144.115`), porta `54173`, servindo `dist/`. Não há Cloudflare Tunnel nem DNS público para este protótipo.

## Fluxo

- **V0.10.1 — baseline consolidado/otimização sem alteração de coreografia:** preservados dois avanços manuais, Dobra espacial como padrão, dente ASCII formado somente por `I C D A S Q u i z`, modelo PBR com aquecimento para a foto e quiz simulado 3 → 4. Texturas de trabalho reduzidas de 4K a 2K, originais intocados no ZIP; arquivos redundantes retirados da pasta pública (fontes originais privadas preservadas em `assets/`); amostradores de superfície reutilizados; DOM só é modificado quando o texto efetivamente muda; WebGL suspenso enquanto o vídeo/slide final cobrem a cena.
- **Telemetria opcional:** no inspetor, **Medir FPS e renderização** apresenta FPS médio, p95 do intervalo entre quadros, CPU de chamada a renderização (não GPU), draw calls, triângulos e número de texturas. Escala interna de resolução ajustável **Alta 1,7× (padrão)**, **Equilibrada 1,35×** e **Econômica 1×**, limitada ao DPR físico do navegador. Não são recolhidos resultados no servidor.
- **V0.10 — raccord 3D → fotografia e quiz demonstrativo:** durante a parte final da transformação, o esmalte PBR do modelo é aquecido gradualmente para um creme mais próximo da fotografia. O shader atua após tone mapping, mantendo a luminância dos relevos e reflexos. A fotografia original permanece intacta. Controle **Cor 3D → fotografia** de 0% a 85% (padrão 60%).
- **V0.10 — interação do quiz:** tempo padrão passa a **7 segundos** (ajustável 5,5–10s). Após uma pausa inicial sem cursor, o mouse entra, passa pelos códigos **5** e **2**, tenta **3** (círculo vermelho, tremor e desaparecimento), desloca-se ao **4** e confirma com check verde. Tudo é cenográfico, sem diagnóstico ou gabarito clínico validado da fotografia; o vídeo mantém o primeiro quadro com 4 já selecionado.
- **Prévia rápida da V0.10:** **Testar 3D → foto e quiz** começa aos 73% da sequência anatômica, mostrando a mudança gradual de cor e a interação sem repetir o título e o ASCII. Preserva os dois avanços manuais no percurso completo.
- **V0.9.2 — caracteres exclusivos do título:** todas as amostras do dente ASCII usam somente os nove glifos `I C D A S Q u i z`; foram removidos números e símbolos especiais do **sorteio**, inclusive no molar completo e durante a transformação para a malha. Preservado o atlas original de 34 células para não afetar a indexação do shader, a amostragem anatômica, as quatro coreografias e o segundo avanço. Nenhuma mudança no dente anatômico, quiz ou vídeo.
- **V0.9.1 — Dobra espacial refinada (opção 04):** os caracteres pequenos agora **emergem dos pixels desenhados da própria letra grande** correspondente: o atlas tipográfico é amostrado uma vez com Canvas 2D e os pontos de nascimento são fixados em atributos da geometria WebGL. Eles partem de dentro dos traços, se afastam brevemente ao redor da letra original e só depois formam a lâmina tipográfica que dobra para o dente. A emissão é mais apagada (opacidade padrão **24%**, ajustável de **12% a 50%** apenas nesta variante), e os caracteres recuperam a opacidade integral quando o dente fica pronto. Mini letras menores que na V0.9, facilitando distinguir as letras-mãe. A opção **04 é a selecionada por padrão** na ausência de preferência já guardada no navegador. As opções 01–03 e o segundo avanço manual seguem disponíveis e intactos.
- **V0.9 — comparador de quatro coreografias título → molar:** o inspetor ganhou quatro opções selecionáveis: **01 Magnética**, **02 Órbita**, **03 Cascata** e **04 Dobra espacial**. A opção 01 preserva a coreografia V0.8 para comparação direta; 02 faz cópias orbitarem em profundidade; 03 desprende caracteres em sequência horizontal; 04 abre uma lâmina tipográfica e a dobra sobre o volume dental. As quatro partem do mesmo título e chegam aos **mesmos pontos finais do glTF**, mantendo o mesmo tempo padrão de 4,25 s.
- **Teste/seleção:** escolher uma opção retorna ao título sem perder a opção escolhida. O botão **Testar transformação selecionada** reproduz apenas o primeiro avanço e termina no dente ASCII girando, aguardando o segundo avanço manual. **Marcar como preferida** guarda a escolha apenas no `localStorage` do navegador (não registra aprovação no servidor; informe o nome escolhido no chat para fixação definitiva). Os botões com seleção ativa e opção favorita são visualmente distintos; a preferência fica no JSON de **Copiar parâmetros do protótipo**.
- **V0.8 — título e transição refinados:** `ICDAS` fica em branco frio estável; `Quiz` em menta/teal com oscilação suave de luminosidade e saturação, implementada no shader de glifos, sem alterar a geometria ou o tamanho das letras. As cópias das letras `ICDASQuiz` primeiro se desdobram num halo discreto e, depois, convergem para os mesmos pontos 3D do molar por curvas curtas e easing progressivo. A cor menta das cópias de `Quiz` acompanha a formação e se uniformiza no dente concluído.
- **Duração do primeiro avanço V0.8:** 0,8 s título estável + 1,4 s desdobramento + 1,6 s condensação + 0,45 s assentamento = **4,25 segundos**. Ao terminar, continua aguardando o **segundo avanço manual** no dente ASCII girando. Nenhuma mudança no ciclo seguinte.
- **V0.7 — dois avanços manuais de slide:** a tela inicial é o título `ICDASQuiz`, composto pelos nove glifos reais do mesmo atlas WebGL. **Primeiro avanço** (botão `Próximo`, clique na cena, seta direita, espaço ou Page Down) transforma o título no dente ASCII; ao concluir, **para e aguarda** no dente girando. **Segundo avanço** inicia o ciclo antigo até o primeiro slide da apresentação. Não há passagem automática entre as duas ações.
- **Primeiro avanço, formação mais elegante:** 0,6 s de título legível, 2,8 s de formação progressiva e 0,45 s de acomodação, totalizando **3,85 s**. Pontos extras emergem gradualmente após começarem a se deslocar, seguindo trajetórias curvas pequenas e easing suave. As letras continuam sendo os mesmos pontos do glTF utilizados no dente ASCII, sem troca de modelo.
- **Iniciar sequência (padrão 5 s):** o mesmo molar continua girando durante toda a passagem ASCII → malha glTF; só depois da revelação completa ele vira para a oclusal e se desloca/reduz para o monitor. A foto clínica substitui a malha no último trecho.
- **Continuidade de giro (V0.4):** o início agora reaproveita a mesma função temporal da rotação da tela de espera, sem introduzir um segundo giro acelerado durante a transformação.
- **Encaixe ampliado:** escala final padrão aumentada de 0,56 para 0,78, com alinhamento vertical atual em **0,58**. Ajustável no inspetor.
- **Quiz simulado:** permanece visível por 2,5 s (ajustável de 1,5 a 5 s); cursor se move até o botão 4, simula um clique e mostra um check verde sem texto. Não há avaliação clínica nem afirmação de acerto.
- **ASCII ajustado após V0.5:** distribuição e tamanho continuam no estilo da V0.4, com pontos livres amostrados na superfície do glTF, sem grade de tela nem filtragem por célula. Apenas o alfabeto da V0.5 foi recuperado: `ICDASQuiz0123456@#%&*+=-/?<>[]{}~:`, agora em atlas de 8 colunas × 5 linhas. Permanecem as melhorias não relacionadas ao ASCII.
- **V0.5 — alinhamento e força:** Y final reduzido de 0,72 para **0,58** (ligeiramente mais baixo), mesma escala 0,78. Centralização usa uma curva `easeOutCubic` entre aproximadamente 84% e 93,5% do trecho, com aceleração visualmente mais incisiva.
- **V0.5 — indicação visual de acerto:** clique em 4 exibe somente um círculo verde, check e pulso; **sem texto de confirmação** na cena. É uma simulação visual, sem correção clínica da imagem.
- **V0.5 — passagem refeita para o vídeo:** o vídeo original começava com monitor branco e quiz de outra escala. Uma versão recomposta de 4s começa na **imagem exata do monitor com a seleção 4**, espera brevemente e esconde a troca para a câmera original dentro de um whip-pan desfocado. Script determinístico: `tools/recompose_video.py` (FFmpeg + Pillow); origem privada preservada como `public/assets/intro_video_raw_4s.mp4`. O MP4 servido continua em `public/assets/intro_video_4s.mp4`.
- **Opacidade e profundidade:** esmalte real é renderizado com material PBR **opaco**, `depthWrite` ativo e `FrontSide`. Um depth-only occluder da geometria completa impede que raízes e letras ASCII do lado de trás sejam visíveis pela coroa. A saída para a fotografia usa `discard` pontilhado, sem tornar a malha translúcida.
- **Continuação opcional:** vídeo de quatro segundos com monitor, aceno, retorno, intro e slide em fullscreen.
- **Tempos com dois avanços:** primeiro avanço = **4,25 s na V0.8**; aguarda indefinidamente no dente ASCII. Segundo avanço = **5 s** de metamorfose 3D + **2,5 s** de quiz simulado + **4 s** de vídeo, totalizando **11,5 s**. O tempo de espera entre cliques não é fixo.
- **Parâmetros revisáveis na tela:** duração da transformação (2–8 s), densidade de caracteres e rotação final X/Y/Z, além de opção de emendar o vídeo.
- **Reiniciar:** retorna ao título `ICDASQuiz`, pronto para o primeiro avanço.

## Rodar em desenvolvimento

```bash
cd /srv/repos/owned/ICDASQuiz/tools/tcc-opening-prototype
npm install
npm run dev -- --host 127.0.0.1
```

## Build estático e servidor Tailscale

```bash
cd /srv/repos/owned/ICDASQuiz/tools/tcc-opening-prototype
npm run build
python3 tools/preview_server.py --bind 100.71.144.115 --port 54173 --directory dist
```

`npm run build` gera automaticamente arquivos `.gz` para JavaScript, CSS, HTML, glTF e geometria. O servidor Python da prévia oferece **gzip** ao navegador, cache longo apenas para arquivos com hash de conteúdo e suporte a **HTTP 206 Range** para o MP4. O servidor se vincula explicitamente ao endereço da tailnet, sujeito às ACLs e firewall locais. Processo/PID de prévia gerenciados de forma provisória em `/var/tmp/icdasquiz-tcc-prototype.pid`; ainda não há serviço persistente após reboot.

Para reproduzir as texturas reduzidas **a partir do ZIP original** (requer Pillow) e o microbenchmark de CPU:

```bash
python3 tools/optimize_textures.py
node tools/bench_sampling.mjs
```

Revisão e números detalhados: `../../docs/TCC_ABERTURA_PERFORMANCE_20261120.md`.

## Pacote offline para o agente da apresentação

O comando abaixo gera um ZIP portátil contendo a versão de execução estática, texturas, vídeo e imagens usados, código-fonte, instruções de integração, servidor local Python (biblioteca padrão) e documentação. Os arquivos pessoais entram **somente no ZIP local privado**, não no Git:

```bash
cd /srv/repos/owned/ICDASQuiz/tools/tcc-opening-prototype
npm run build
npm run test:smoke
python3 tools/package_offline.py
```

Saída ignorada pelo Git: `assets/ICDASQuiz_TCC_Abertura_V0.10.2_OFFLINE.zip`. Extrair e executar `start-linux.sh` (CachyOS/Legion) ou `start-windows.cmd` com Python 3. O modo de apresentação integral, sem painel, é `?presentation=1`, e o contrato de integração via iframe de mesma origem encontra-se em `INTEGRATION_AGENT.md`.

Medida real no browser stack do Zezin: formação título/ASCII cerca de 53 FPS e passagem ASCII→malha cerca de 50 FPS em 1×; em 0,75×, cerca de 59,3 e 56 FPS, respectivamente, no ambiente de teste. **Não usar isso como benchmark do Legion**: as características do Cloak/Chromium diferem da RTX 5080. Modo 0,75× é alternativa de emergência, não padrão. Mais detalhes em `docs/TCC_ABERTURA_PERFORMANCE_20261120.md`.

## Recursos

- ZIP de origem: `assets/maxillary_first_molar.zip` (recebido do usuário)
- Modelo glTF extraído: `public/assets/molar/scene.gltf`, `scene.bin`, `textures/`
- Fotos e vídeo utilizados pela prévia: `public/assets/` (privados; **não versionar/publicar sem decisão explícita**). Referências originais, ZIP e vídeo original necessários para reproduzir versões ficam em `assets/` (também ignorados pelo Git), não em `dist/`.
- Script: `src/main.js`; CSS: `src/style.css`; fonte: `index.html`
- `npm run build` gera `dist/`, incluindo assets locais.

## Atribuição obrigatória

**Maxillary First Molar** (https://sketchfab.com/3d-models/maxillary-first-molar-e719a474ef7e4bd7abec508f85f1e984) by **University of Dundee, School of Dentistry** (https://sketchfab.com/DundeeDental) is licensed under **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/).

Licença original preservada em `public/assets/molar/license.txt` e crédito exibido no protótipo.

## Limitações atuais

- Posição oclusal inicial é uma aproximação técnica; deve ser aprovada visualmente e ajustada pelo usuário no painel.
- Alinhamento dente 3D → foto clínica é uma aproximação; depende da orientação/escala aprovada.
- Não há teste de browser real no servidor, apenas build, integridade de assets e resposta HTTP.
- A integração definitiva ao site da apresentação e ao arquivo de fallback ainda não foi realizada.
