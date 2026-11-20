# ICDASQuiz — Handoff da abertura animada 3D (17/11/2026)

## Estado consolidado — 20/11/2026, V0.10.1

**Baseline visual aprovado pelo usuário:** V0.10. **Snapshot operacional otimizado:** V0.10.1, mantendo exatamente o roteiro e a interação, com redução de assets, cache de amostragem, compressão HTTP e painel opcional de telemetria. A fidelidade perceptiva das texturas 2K ainda requer inspeção no Legion. Relatório de performance com evidências, riscos, reversão e próximos gates: [TCC_ABERTURA_PERFORMANCE_20261120.md](TCC_ABERTURA_PERFORMANCE_20261120.md).

**Sequência efetiva atual:** título com breathing de Quiz; primeiro avanço manual = título → Dobra espacial → molar ASCII (4,25s, só nove letras); espera no molar girando; segundo avanço manual = dente ASCII → PBR/oclusão → cor creme e fotografia no monitor (5s) → quiz demonstrativo 3 errado / 4 certo (7s) → vídeo/aceno/slide (4s). **20,25s ativos mais as esperas manuais.** Quatro opções do primeiro morph continuam disponíveis, a 04 Dobra espacial permanece preferida. A seleção simulada não representa diagnóstico clínico.

**Acesso privado ativo:** http://100.71.144.115:54173/ (Tailscale), servindo `tools/tcc-opening-prototype/dist` por `tools/preview_server.py`; gzip e Range para vídeo. Código da prévia isolado, mídia pessoal privada ignorada no Git. Sem deploy de produção e sem `git push`.

**Importante:** a seção a seguir, datada inicialmente de 17/11, preserva histórico das decisões. Não confundir suas durações/estados antigos com este resumo atual.

## Propósito e estado

Material de continuidade desta seção de desenvolvimento, a ser usado em nova conversa caso o contexto se esgote. O projeto principal é **ICDASQuiz**, TCC de Odontologia UFJF-GV, sobre desenvolvimento de software para ensino do ICDAS. A apresentação do TCC será uma **experiência web interativa** (com PDF/PPTX de contingência). O pedido desta seção é criar **uma abertura cinematográfica curta**, antes do primeiro slide, não redesenhar o sistema clínico ou o quiz.

**Estado na data deste handoff:** storyboard aprovado em suas linhas gerais; trecho de câmera pessoal + monitor já prototipado no Gemini e composto em Python; novo trabalho é a **primeira parte ASCII → modelo dentário 3D → foto do quiz**, usando ZIP fornecido em 17/11/2026. O usuário está no notebook Lenovo Legion e quer avaliar a página de protótipo via Tailscale. Não publicar alterações na aplicação principal sem necessidade.

## Sequência narrativa aprovada

0. **Tela de espera (duração indefinida, loop):** molar construído por caracteres ASCII, flutuando e girando em ângulo diagonal, identidade digital já utilizada pelo usuário (efeito similar no universo ArcadaFlow).
1. **Disparo manual:** os caracteres ASCII começam a se soltar / desaparecer em estilo glitch sutil, revelando progressivamente **a mesma geometria** como malha anatômica de alta resolução com textura real, sem troca brusca de objeto.
2. **Rotação simultânea:** enquanto é revelada a malha, o dente gira suavemente até apresentar a **superfície oclusal diretamente voltada à câmera**.
3. **Monitor por fade-in:** monitor de mesa minimalista surge atrás do dente, com fundo branco neutro como nas fotografias reais do apresentador, sem decoração e com branding ArcadaFlow apenas se discreto.
4. **Quiz por fade-in:** dentro do monitor aparece imagem clínica oclusal real e botões circulares de 0 a 6, com o dente 3D alinhado por cima.
5. **Desaparecimento do mesh por fade-out:** a fotografia clínica fica visível no lugar do objeto tridimensional, sem cortes duros nem mudança grosseira de escala/posição.
6. **Vídeo já prototipado (~4 segundos):** câmera virtual gira horizontalmente 180° em seu **próprio eixo fixo**, revela o apresentador real de scrub azul-claro e óculos acenando brevemente, retorna 180° ao monitor, agora com o **primeiro slide** do TCC, e faz zoom até o slide cobrir a tela inteira. Não haverá quiz interativo obrigatório na abertura; interface do quiz é apenas uma evocação visual. A possibilidade de interação real durante a defesa permanece separada/indefinida.

**Durações:** os ~4 segundos referem-se à parte filmada de monitor/aceno/retorno/zoom, não necessariamente à tela de espera ou ao trecho ASCII; o início 3D deve ter controle de progresso, duração a decidir na revisão.

## Direção de arte e câmera

- Minimalismo extremo; white/neutral background, escrivaninha simples, sem objetos decorativos extras.
- Dente 3D realista; estética ASCII computacional e glitch **controlado**, sem glitches destrutivos exagerados.
- Cores de ArcadaFlow apenas acentos, sem alterar cores da fotografia clínica e sem interferir na identificação ICDAS.
- Câmera do modelo digital mantém o dente centralizado durante a transformação, movimento orgânico, aceleração suave; vista oclusal correta deve ser definida/testada, não presumida por orientação do glTF.
- Qualidade da apresentação web: animações responsivas, baixa latência; preservar um fallback em vídeo/slide para defesa offline.

## Materiais já produzidos anteriormente na conversa

**Fotografias do apresentador:** duas fotos reais com fundo branco, uma mão levantada e outra pose frontal, scrub azul-claro. Vídeos pessoais originais com aceno ~1,6 e ~1,8 s (arquivos de conversa `IMG20261116174916.jpg`, `IMG20261116174833.jpg`, `VID20261116174903.mp4`, `VID20261116174837.mp4`).

**Referências de monitor (geradas na conversa):**
- Monitor branco, webcam, teclado e mouse, sem decoração: `monitor_preto_com_teclado_e_mouse_minimalistas.png`.
- Versão com padrões ArUco 4x4_50, IDs 0,1,2,3 nos cantos internos da tela: `monitor_marcadores_aruco.png`; detectados com OpenCV na imagem de referência, mas vídeo gerativo pode deformá-los.
- Monitor com interface quiz (imagem oclusal clínica e botões 0–6): `quiz_odontológico_em_estação_de_trabalho.png`.
- Monitor com primeiro slide: `estação_de_trabalho_com_slide_acadêmico.png`.
- Fotografia clínica oclusal original: `80864.png`.
- Imagem do primeiro slide original: `80861.png`.

**Vídeo Gemini:** `gemini_generated_video_8e9f1055.mp4`; gerado com referência monitor/ArUco + foto do apresentador. O giro de 180°, aceno e retorno ao monitor já foram considerados aproveitáveis.

**Composição Python (produzida na conversa):** `ICDASQuiz_abertura_4s.mp4`, prévia 1280x720 24 fps H.264 silenciosa; tela quiz no início, aceno, tela de introdução no retorno, zoom final fullscreen. Script/arquivos compactados em `ICDASQuiz_abertura_fontes_python.zip`. Esses arquivos podem precisar ser importados explicitamente ao repositório; sua existência na conversa não os torna automaticamente arquivos versionados do servidor.

**Novo recurso 3D entregue pelo usuário:** `maxillary_first_molar.zip` (arquivo de conversa). O ZIP foi inspecionado: `scene.gltf`, `scene.bin`, `textures/defaultMat_baseColor.png`, `textures/defaultMat_normal.png`, `license.txt`. Modelo **Maxillary First Molar**, University of Dundee, School of Dentistry, Sketchfab: https://sketchfab.com/3d-models/maxillary-first-molar-e719a474ef7e4bd7abec508f85f1e984. **Licença CC BY 4.0 — atribuição obrigatória**; preservar e exibir créditos em página de projeto, documentação ou créditos da apresentação.

## Arquitetura sugerida para a nova etapa

1. Criar protótipo autocontido **Three.js / WebGL** dentro do repositório, isolado da aplicação principal. Carregar glTF e suas texturas localmente sem dependência externa durante a apresentação.
2. Obter o mesmo modelo matemático em dois modos de renderização: ASCII (preferível texturização/overlay baseada em geometria/pontos ou pós-processamento) e mesh PBR, com progressivo `mix` em shader, máscara ou dither. Não trocar para outra geometria incompatível.
3. Testar e ajustar orientação inicial do modelo e orientação oclusal final; calibrar luz, câmera, escala e enquadramento.
4. Criar controle de play/replay e loop de espera. Os dois modos devem poder ser observados e comparados; incluir ajustes de duração/posição se úteis para aprovação.
5. Montar plano de tela/monitor e a imagem clínica original, fade-in e desaparecimento do dente, com mapeamento respeitando a foto e o alinhamento.
6. Disponibilizar **somente via Tailscale** para avaliação no Legion, sem exposição pública e sem mudança desnecessária da aplicação principal.
7. Confirmar visualmente a tela com o usuário. Depois integrar à abertura de 4 segundos (pré-renderizada ou em fluxo web) e ao slide fullscreen.

## Incertezas, verificações e não-objetivos

- Sem acesso ao monitor/coluna do usuário: apenas validar por build/HTTP e pedir avaliação visual.
- Importação de arquivos de conversa ao servidor pode exigir mecanismo autorizado de upload; evitar downloads públicos ou cópia de secretos.
- Antes de escolher quanto dura a transformação, experimentar 2–4 s, mantendo a tela de espera em loop.
- As duas fases (Three.js e vídeo Gemini) **não precisam ser renderizadas pela mesma ferramenta**; continuidade perceptiva é o critério.
- Não inventar classificação ICDAS da imagem clínica.
- Não alterar app principal, deploy de produção ou `git push` sem pedido específico.
- Preservar crédito CC BY 4.0 do glTF ao redistribuir derivados.

## Próximo checkpoint

Repositório canônico: `/srv/repos/owned/ICDASQuiz`. Descobrir via `zezin where icdasquiz`, root específico já conhecido. Construir protótipo Three.js, servir em endpoint privado da tailnet, reportar URL e instruções de avaliação; registrar evidências e atualizações neste documento.

## Atualização operacional: protótipo V0.1 já servido em 17/11/2026

- Código e README: `tools/tcc-opening-prototype/`.
- Acesso **privado Tailscale** a partir do Legion conectado à mesma tailnet: **http://100.71.144.115:54173/** (host `zezin`). Python HTTP server vinculado estritamente ao IP Tailscale, sem publicação pública.
- Build: Vite 8.3.8 + Three.js 0.187.0, Node 24.22.3, saída estática `tools/tcc-opening-prototype/dist/`; `npm run build` passou.
- Geometria e texturas glTF extraídas em `tools/tcc-opening-prototype/public/assets/molar/`; foto clínica, slide, referências do monitor e vídeo anterior importados em `public/assets/`; ZIP de origem em `assets/maxillary_first_molar.zip`.
- Checagem HTTP: página, glTF, binário, textura de cor, monitor branco, monitor com quiz e MP4 retornaram **200** no endereço Tailscale.
- Funções: ASCII 3D em espera; revelação progressiva por fragment dither do mesmo mesh; rotação progressiva para oclusal; fade-in de monitor e do quiz; fade-out da malha; continuação opcional do MP4 de 4 segundos; slide final fullscreen.
- Controles de aprovação: **Iniciar sequência**, **Reiniciar**, **Pausar**, **Ver vídeo aprovado**, duração de 2 a 8 segundos, densidade ASCII, rotação oclusal X/Y/Z, auto-continuação e cópia de parâmetros.
- Código e handoff ficam no repositório; por prudência, os arquivos privados de referência e o vídeo com rosto do usuário estão ignorados no Git do protótipo.
- **Ainda pendente:** aprovação visual real no navegador do Legion e calibração de rotação/escala/alinhamento com a fotografia. Não afirmar fidelidade visual antes dessa revisão.
- Para reiniciar o servidor estático depois de um reboot: ver `tools/tcc-opening-prototype/README.md`. PID provisório em `/var/tmp/icdasquiz-tcc-prototype.pid`; não é uma unidade persistente.
- Não houve `git push` nem alterações na produção do ICDASQuiz.

## Revisão V0.2 — Feedback de alinhamento / caracteres / orientação

Feedback do usuário: ASCII pequeno, molar entrando de cabeça para baixo, duas representações aparentemente desalinhadas durante a transição.

Correções técnicas realizadas em `tools/tcc-opening-prototype/src/main.js` e `index.html`:

- Os caracteres passaram de aproximadamente 9–13 px para **32 px por padrão**, com ajuste visual 14–48 px; densidade padrão reduzida para **1800** para manter caracteres legíveis.
- Inspeção das seis projeções da geometria glTF mostrou que a **face oclusal está voltada para o eixo local -Z**. A conversão do importador a coloca aproximadamente para o eixo -Y do mundo; portanto, a orientação final inicial foi alterada de **X +90°** (mostrava raízes) para **X -90°** (oclusal voltada à câmera).
- As máscaras de transformação usam agora uma função espacial compartilhada, no espaço de coordenadas **local do pivô**, para que o ASCII desapareça na mesma região em que a malha texturizada é revelada.
- Os caracteres são amostrados diretamente das superfícies triangulares do próprio glTF e **não recebem mais deslocamento/partículas** durante a transformação. Os dois modos partilham pivô, posição, escala e rotação.
- Corrigido o erro de duplo giro: antes a regeneração de densidade podia capturar `matrixWorld` já rotacionada e aplicar transformação novamente. Agora a matriz `mesh → pivot` é fixada no carregamento.
- Acrescentados: controle do tamanho de letras, posicionamento X/Y/escala frente à fotografia, slider de inspeção de progresso e checkbox para ver simultaneamente ASCII + malha e calibrar a sobreposição.
- A posição/alinhamento **entre dois dentes anatomicamente diferentes** (glTF e fotografia clínica) continua uma aproximação, não um registro anatômico exato. O objetivo de sobreposição geométrica exata se aplica às representações ASCII e mesh do **mesmo** glTF.
- `node --check`, `npm run build` e resposta HTTP no endpoint Tailscale passaram. Ainda requer inspeção visual no navegador do Legion para validação final.

## Revisão V0.3 — sequência, rotação e sólido sem vazamentos

Feedback do usuário: dar mais ênfase à metamorfose, **manter rotação durante a transformação**, mover o dente ao monitor **somente depois** da malha estar totalmente revelada; eliminar transparência falsa que permite ver raízes atravessando a coroa e ASCII na parte de trás; usar **5 segundos como duração padrão**.

Implementação `tools/tcc-opening-prototype/src/main.js`:

- A transição ASCII → mesh ocupa aproximadamente os primeiros **70% de 5 segundos**, com giro horizontal contínuo de **1,1 volta**. Na sequência, orienta a face oclusal, e **somente após ~84%** inicia o movimento e a redução para encaixar no monitor.
- Monitor aparece no final, quiz aparece após o movimento e a fotografia é revelada pela saída pontilhada da malha, sem misturar transparências físicas.
- O PBR odontológico agora usa `transparent=false`, `opacity=1`, `side=FrontSide` e `depthWrite=true`; revelação e dissolução final são mascaradas por **fragment discard**.
- Cada mesh ganhou uma geometria duplicada **invisível, depth-only**, sempre opaca para o z-buffer e renderizada antes das letras. Isso oclui amostras do lado posterior que, na versão anterior, vazavam pela coroa. A amostragem de ASCII recebe pequeno deslocamento ao longo da normal para prevenir z-fighting.
- O ciclo ASCII e a máscara de revelação compartilham posição e função de ruído no espaço do pivô.
- O controle de duração agora inicia em **5 s**, permanecendo editável.
- Build Vite, sintaxe Node e checagem HTTP Tailscale passaram; avaliação visual no navegador do Legion continua necessária.

## Revisão V0.4 — continuidade do giro e clique simulado no quiz

Feedback: não iniciar uma nova rotação ao clicar em **Iniciar sequência**; reutilizar o movimento já contínuo da espera, ampliar o molar na sua posição sobre a imagem clínica e dar ao público tempo para entender a tela do quiz, possivelmente mostrando um cursor clicando em 4 e uma breve confirmação.

Implementação no protótipo isolado `tools/tcc-opening-prototype/`:

- A função única `waitingQuaternionAt(time)` define a rotação tanto durante a espera quanto durante os primeiros 70% da transformação; o ângulo e a velocidade mantêm continuidade no momento do clique, sem a rotação adicional de 1,1 volta usada na V0.3. A partir dos 70%, há apenas a orientação final para a oclusal já prevista.
- Ajustes padrão para o encaixe sobre a foto: `scale=0.78` (antes 0.56), `Y=0.72` (antes 0.6), mantendo X=0 e os controles disponíveis para calibração fina.
- O término da fase 3D deixa a imagem do quiz em tela por **2,5 segundos** (ajustável de 1,5 a 5 s), antes de iniciar o vídeo de 4 segundos. Assim a duração da transformação 3D permanece **5 segundos** e o vídeo aprovado não é modificado.
- Durante a pausa, um cursor animado move-se até o botão circular **4**, simula o clique e exibe a confirmação neutra **“Código 4 selecionado”**. Isso **não indica correção clínica** e não altera o aplicativo real.
- Overlay construído em HTML/CSS determinístico (sem IA de imagem), sobre a imagem de referência do monitor; preserva foto, enquadramento e botões.
- Após a confirmação, a apresentação continua automaticamente para o vídeo do giro e o primeiro slide, conforme opção já presente no painel. Há um crossfade breve na entrada do vídeo para reduzir saltos visuais.
- O efeito exige inspeção visual no navegador do Legion; build Vite e checagem do endpoint foram realizados, mas não são prova de fidelidade visual.

## Revisão V0.5 — ASCII uniformizado, feedback visual e continuidade do clipe

Solicitações do usuário: os caracteres ASCII devem ser distribuídos uniformemente sem se sobrepor; o alfabeto principal passa a ser **ICDASQuiz**, os dígitos de **0 a 6** e caracteres especiais. Manter o tamanho atual do molar, mas encaixá-lo um pouco mais baixo na fotografia e aumentar a rapidez/força de sua centralização. Após clicar em 4, sinalizar o acerto **sem texto**. Eliminar o salto de enquadramento e a tela branca no início do vídeo de giro, usando o quiz definitivo como quadro de partida.

Implementado:

- No modo ASCII, um atlas de **34 caracteres** em 8 colunas × 5 linhas, com `ICDASQuiz0123456@#%&*+=-/?<>[]{}~:`. A cada quadro, os pontos de superfície do mesmo glTF são projetados na tela; somente a amostra mais próxima da câmera por célula é exibida. O shader posiciona as letras no centro de uma grade, com `step=1,16 × tamanho`, o que evita sobreposição e distribuições aleatórias desiguais durante o giro. A qualidade perceptiva depende de avaliação na GPU do Legion.
- Encaixe padrão passou de **Y=0,72** para **Y=0,58**, mantendo **escala=0,78**. A interpolação do deslocamento final mudou de `smoothstep(.84,.96)` para `easeOutCubic((p-.84)/.095)`, mais rápida no final da rotação.
- Ao clicar no botão 4, animação **verde com check branco e pulso circular** sem mensagem textual na cena. Trata-se apenas de um exemplo simulado; **não** significa que a fotografia clínica foi validada como ICDAS 4.
- Refeito o início do MP4 `intro_video_4s.mp4` a partir do **quiz com código 4 já selecionado** e da filmagem prévia. O código `tools/tcc-opening-prototype/tools/recompose_video.py` gera um clipe de 4 segundos com a mesma imagem no primeiro quadro; depois um movimento desfocado para a esquerda esconde a passagem para o plano de câmera original. Assim não aparece mais o monitor branco nem o layout discrepante na emenda. Origem preservada como `public/assets/intro_video_raw_4s.mp4`; vídeo usado no protótipo em `public/assets/intro_video_4s.mp4`.
- O player espera o primeiro quadro decodificado antes de exibir o vídeo e usa uma transição curta de opacidade; o overlay do clique sai quando a imagem do vídeo está visível.
- Build/sintaxe/HTTP/Tailscale passaram. Visualização real do resultado no Legion e calibração final continuam pendentes.

## Reversão pontual do ASCII após V0.5

O usuário considerou o ASCII da V0.5 visivelmente pior e solicitou voltar ao visual anterior. Foi restaurada **apenas a renderização ASCII da V0.4**, incluindo atlas horizontal original de 16 glifos, distribuição dos pontos amostrados na superfície do molar sem grade em tela, tamanho perspectivo de sprites e ausência de filtragem por célula. A seleção `ICDASQuiz0123456` e a distribuição em grade da V0.5 deixam de valer. Mantidos o giro contínuo, o alinhamento mais baixo, a centralização mais incisiva, o feedback visual de clique em 4 e o MP4 recomposto com raccord correto. Sintaxe, build e HTTP privado passaram. Falta aprovação visual no Legion.

## Ajuste subsequente: preservar as letras solicitadas

Após a reversão, o usuário esclareceu: **“as letras podem ficar do jeito que estava”**. Portanto, manter a apresentação visual/espacial anterior (pontos amostrados sobre a malha, sprites perspectivos, sem grid nem filtro) mas recuperar o conjunto da V0.5: `ICDASQuiz0123456@#%&*+=-/?<>[]{}~:`. O atlas de textura é 8 × 5 e mantém a seleção de caracteres vinculada aos pontos da superfície. Nenhuma outra fase da abertura foi alterada.

## V0.6 — prólogo tipográfico em três momentos

O usuário aprovou criar **três momentos narrativos** antes de continuar a abertura existente:

1. O título **ICDASQuiz** centralizado como tela inicial de espera, estático ou semiestático, com iluminação discreta e sem elementos decorativos excessivos;
2. **somente as nove letras** `I C D A S Q u i z` se desprendem e se multiplicam, migrando para formar o dente ASCII 3D;
3. A própria animação já desenvolvida (ASCII girando → malha anatômica → monitor → fotografia/quiz → clique 4 → giro/aceno → slide) continua automaticamente.

**Tempos V0.6 para avaliação:** espera no título indefinida até comando manual; após clicar: título legível **0,5 s**, formação progressiva **1,25 s**, dente ASCII completo **0,25 s**; segue metamorfose 3D **5 s**, quiz **2,5 s**, vídeo já aprovado **4 s**. Total após iniciar: **13,5 s** nas configurações padrão.

**Implementação:** `tools/tcc-opening-prototype/src/main.js` recebeu atributos `aTitleIndex` (0 a 8) e `aHero` (as nove letras legíveis), com uniformes `uTitleProgress`, `uTitleSpacing`, `uHeroGlyphSize` e `uInversePivot`. O mesmo `THREE.Points` que já renderizava o dente possui nove âncoras de título: inicialmente só os nove pontos heróis são visíveis. Durante a formação, novos glifos aparecem junto às âncoras e se deslocam para os pontos da superfície anatômica amostrada. O uniforme de rotação inversa impede que o título gire com o dente enquanto continua legível. Ao finalizar, todas as partículas ocupam a superfície do molar e continuam usando o glTF original, sem trocar de objetos nem duplicar geometria. Na formação inicial são usadas **apenas as letras de ICDASQuiz**; na renderização final do dente ASCII permanece o atlas inteiro de 34 caracteres previamente aprovado. Uma aura leve CSS anima apenas a iluminação atrás do título, nunca a disposição tipográfica.

**Arquivos:** `src/main.js`, `index.html` e `src/intro.css` (novo), servidos pelo mesmo protótipo privado no Tailscale, sem alterar o ICDASQuiz principal ou publicar assets privados em Git. O pipeline principal V0.5 permanece inalterado após o prólogo. A validação visual no navegador do Legion continua necessária; a compilação Vite não comprova a aparência final de shaders WebGL.

**Validação técnica da V0.6:** `node --check src/main.js` e `npm run build` passaram; testes de contratos confirmaram os três estados, o atlas `ICDASQuiz`, ausência da grade ASCII rejeitada, alinhamento matemático de título estático sob rotação do pivô e largura responsiva do texto. HTTP Tailscale retornou 200 para a página, glTF e vídeo anterior. A URL privada permanece `http://100.71.144.115:54173/`. Não foi executado teste visual WebGL automatizado por falta de navegador/headless no servidor. **Aprovação estética e continuidade visual ainda dependem do Legion.**

## V0.7 — avanço de slides independente e formação desacelerada (20/11/2026)

Decisão do usuário: **simular a passagem de slides com dois comandos explícitos**. Na tela inicial, o título `ICDASQuiz` aguarda indefinidamente. Ao primeiro **Próximo**, o título se converte no dente ASCII e **fica parado nessa etapa narrativa**, embora o molar continue girando lentamente. Apenas um **segundo Próximo** dispara a metamorfose ASCII → mesh → monitor → quiz com clique 4 → vídeo de câmera/aceno → primeiro slide efetivo do TCC. A separação é obrigatória: não iniciar o segundo movimento automaticamente.

O usuário também considerou a conversão anterior de letras para dente **rápida demais e pouco elegante**. O prólogo agora contém: **0,6 s** de título, **2,8 s** de formação e **0,45 s** de estabilização, total **3,85 s** após o primeiro avanço. Os mesmos caracteres WebGL são interpolados por uma curva `smoothstep` mais longa, com deslocamento `smooth`/Hermite e pequeno arco que começa e termina em zero. As cópias adicionais só se tornam visíveis depois que deixam a posição inicial, evitando o acúmulo repentino de letras sobre o título. A renderização do dente ASCII após a formação continua a técnica aprovada, sem grade em tela.

**Controles V0.7:** botão contextual `Próximo: formar dente` → `Próximo: iniciar animação`, clique na área da cena, seta direita, `Page Down`, espaço e Enter (desde que não haja campo em edição). `Reiniciar` volta ao título. O botão Próximo fica inativo enquanto a formação ou sequência automática estão em andamento, reabilitando-se quando o dente está pronto. O segundo avanço leva **11,5 s** no padrão atual: 5 s mesh, 2,5 s quiz, 4 s vídeo. O tempo de espera entre o primeiro e o segundo avanço depende do apresentador e **não** é contabilizado como animação.

Arquivos: `tools/tcc-opening-prototype/src/main.js`, `index.html` e `intro.css`; servidor privado Tailscale permanece em `http://100.71.144.115:54173/`. `node --check`, build Vite e testes de contratos dos estados/teclas executados com sucesso; HTTP retornou 200. Ainda falta validar visualmente o novo ritmo no Legion antes de considerar a estética aprovada. Não houve mudança na produção do ICDASQuiz nem `git push`.

## V0.8 — cromatismo de Quiz e coreografia em duas fases (20/11/2026)

Pedido do usuário: **`Quiz` em uma cor diferente no título**, com breathing sutil de luz/cor, e uma transformação mais bonita entre a palavra e o dente. Manter o comportamento de **dois avanços manuais** da V0.7, inclusive a pausa no dente ASCII antes da animação anatômica.

**Direção implementada:**
- `ICDAS` permanece em branco frio estável; `Quiz` usa verde-água/menta com uma oscilação luminosa lenta de período aproximado de 3,7 segundos. O breathing é do pigmento/brilho, não da escala ou da posição do texto.
- O primeiro avanço agora tem 4,25 segundos: título ainda legível **0,8 s**, **1,4 s de desdobramento** das cópias de `ICDASQuiz` em torno da palavra, **1,6 s de condensação magnética** dessas cópias na superfície do molar e **0,45 s** de acomodação com o ASCII girando.
- As nove letras principais permanecem ancoradas durante o desdobramento; as cópias surgem com atrasos discretos e alpha reduzido. Na segunda fase, grupos de caracteres passam por arcos curtos de profundidade, com easing suave, até seus pontos já amostrados na geometria. O verde das cópias originárias de `Quiz` acompanha parte da formação, dissipando-se para a cor unificada do dente perto do final.
- O **mesmo objeto THREE.Points e o mesmo glTF** sustentam a transformação, sem troca visual de geometria; permanece o ASCII V0.4 espacial com o alfabeto de 34 glifos já solicitado. A malha anatômica, posicionamento do dente no monitor, o clique 4 e o vídeo de quatro segundos permanecem sem alterações.

**Locais:** `tools/tcc-opening-prototype/src/main.js` (vertex/fragment shader e cronômetro), `src/intro.css` (aura discreta deslocada para o lado `Quiz`) e `index.html` (V0.8 e tempos). Build Vite, sintaxe JS e testes de contratos dos estados, dois avanços e novos componentes de shader passaram; o endpoint privado Tailscale retorna HTTP 200. Ainda não houve avaliação visual em navegador real/Legion. Nenhum `git push` ou alteração na produção ICDASQuiz.

## V0.9 — laboratório comparativo de transições título → ASCII (20/11/2026)

Pedido: o usuário deseja **diferentes opções efetivamente executáveis** de transformar o título `ICDASQuiz` no dente ASCII, para experimentar e aprovar uma delas no Legion. Não basta descrever sugestões abstratas ou alterar o segundo avanço.

**Quatro coreografias implementadas no mesmo shader `THREE.Points`, com uniforme `uMorphVariant`:**

1. **Magnética / V0.8 (0):** desdobramento suave ao redor das nove letras e atração progressiva para a forma anatômica; referência para comparar a mudança.
2. **Órbita (1):** cópias descrevem elipses em torno das letras, incluindo profundidade e arcos de rotação, antes de ocupar as amostras do molar.
3. **Cascata (2):** letras se desprendem em ondas **da esquerda para a direita**, com fitas ascendentes e entrada escalonada por índice tipográfico, depois convergindo para os mesmos pontos do molar.
4. **Dobra espacial (3):** o título se desdobra em um plano de partículas tipográficas, que se dobra no eixo de profundidade e assenta na anatomia do molar.

**Comparabilidade:** os quatro modos têm o mesmo destino geométrico (o glTF da University of Dundee com pontos já amostrados), o mesmo atlas aprovado `ICDASQuiz0123456@#%&*+=-/?<>[]{}~:`, mesmas cores do título (ICDAS branco frio/Quiz menta breathing), densidade e escala do dente, e **4,25 s** de duração do primeiro avanço. Os quatro modos retornam à aparência espacial de ASCII da V0.4 após a formação, preservando a metamorfose mesh/quiz/vídeo. Apenas a coreografia título → dente varia.

**UX do comparador:** quatro cartões selecionáveis no inspetor, com indicação da opção ativa; clicar na opção retorna para o título, sem carregar novos modelos. O botão **Testar transformação selecionada** reinicia e executa **somente o primeiro avanço**, terminando na tela do dente ASCII girando, em espera. O segundo avanço continua manual via botão Próximo, cena ou tecla. **Marcar como preferida** persiste a escolha *apenas no localStorage do navegador* e exibe uma estrela na opção favorita; não envia a escolha ao servidor e não substitui a aprovação explícita do usuário no chat. Exportação de parâmetros inclui nome e índice do modo.

**Evidência:** validação de sintaxe e `npm run build` Vite passaram; 20 checks dos contratos de seleção, quatro ramos de shader, HTML, acessibilidade, persistência opcional e integridade do segundo avanço passaram; página servida no Tailscale `http://100.71.144.115:54173/` respondeu 200 e mostrou `V0.9`. **Sem navegador WebGL disponível no servidor para revisar o movimento renderizado**; a escolha estética depende de aprovação no Legion. Nenhuma mudança no ICDASQuiz de produção e nenhum `git push`.

## V0.9.1 — Dobra espacial com emissão a partir dos traços das letras

O usuário preferiu visualmente a **opção 04, Dobra espacial**, mas solicitou que as letras pequenas aparecessem saindo com mais clareza das letras grandes e que fossem mais apagadas/translúcidas. Foi ajustada **somente a variante 04**, sem eliminar as outras três opções ou alterar a malha/quiz/vídeo.

**Novo método:** durante a criação do atlas Canvas 2D, são amostrados pixels com tinta real dos nove caracteres `ICDASQuiz` (alfa > 145). Para cada partícula, é guardado `aBirthOffset` dentro do desenho de sua letra-mãe `aTitleIndex`. No shader, as cópias **nascem dentro do traço tipográfico**, partem primeiro para um pequeno arco próximo à letra e só então integram uma folha de partículas e a dobram até o molar ASCII. A letra principal continua maior, legível e opaca durante o desprendimento. As cópias são menores (29% do tamanho da letra principal na fase inicial, contra 44% anteriormente).

**Opacidade:** as cópias da Dobra têm alfa inicial baixo e gradual, com padrão **0,24** na fase de emissão e controle `Opacidade das mini letras` de **12% a 50%** na interface; a folha continua tênue, recuperando 100% da opacidade apenas ao se aproximar da forma final do dente. Esse controle atualiza o uniforme WebGL `uFoldGhostAlpha` sem gerar novamente a geometria. Após a transformação, o dente ASCII mantém o visual previamente aprovado.

**Experiência de avaliação:** a variante 04 passa a ser a seleção padrão, salvo quando houver preferência previamente salva no navegador. O mesmo botão `Testar transformação selecionada` permite repetir e comparar com as outras opções; o primeiro avanço continua durando 4,25 segundos, terminando no dente ASCII em espera, e apenas o segundo avanço aciona a animação até o slide real.

**Verificação técnica:** `node --check`, `npm run build`, testes de presença de atributos, uniformes, estados, seletor e persistência passaram; a página, modelo e vídeo responderam 200 no Tailscale em `http://100.71.144.115:54173/`, versão `V0.9.1`. A correção estética ainda depende de inspeção no Legion. Sem mudanças na aplicação principal e sem `git push`.

## V0.9.2 — dente ASCII com apenas as nove letras do título

Decisão do usuário: tanto o dente ASCII já formado quanto a transição que o constrói devem usar exclusivamente os caracteres do título `I C D A S Q u i z`; sem números nem símbolos especiais. Em `src/main.js`, o sorteio por amostra foi limitado a `TITLE_LETTERS.length` (nove primeiras posições do atlas), preservando o atlas maior existente para compatibilidade. As quatro coreografias, especialmente a Dobra espacial 04, mantêm seus percursos e o efeito de transparência aprovado; o segundo avanço, glTF e vídeo não foram modificados. A seleção do conjunto deve permanecer sem números e símbolos em futuras revisões.

## V0.10 — raccord cromático 3D → 2D e quiz com erro/acerto (20/11/2026)

O usuário pediu para trabalhar **somente a etapa final do dente 3D para a foto clínica**, pois o glTF mostra esmalte branco enquanto a foto possui esmalte amarelo-creme. Também solicitou mais tempo de observação do quiz, mouse passando sobre outros números, tentativa no **3** com erro vermelho e tremor que desaparece, seguida do clique correto demonstrativo no **4**.

**Cor:** foi inspecionado o recurso privado `public/assets/monitor_quiz_reference.png` (1672×941); os pixels em faixa quente na região central de esmalte apresentaram mediana aproximada de RGB **211, 167, 128** (medida exploratória, não calibração de cor ou diagnóstico). O modelo usa matiz de referência `#e6bd96` e três uniformes no shader PBR: `uWarmth`, `uWarmStrength`, `uWarmTint`. O aquecimento acontece só perto do monitor, de `smooth(.78,.965,p)`, após o tone mapping e antes da conversão de cor final; a mistura preserva a luminância do 3D para manter brilho e relevo. O controle **Cor 3D → fotografia** regula a força entre 0 e 85%, padrão **60%**. O arquivo de fotografia não é alterado.

**Quiz:** a permanência padrão aumentou de 2,5 para **7 segundos**, ajustável de 5,5 a 10 segundos. A sequência é calculada em proporções da duração: pausa inicial sem cursor; mouse entra pela direita e passa por **5** e **2**, com borda sutil de hover; desloca-se ao **3**, clica, o botão fica vermelho e treme por cerca de meio segundo; o efeito vermelho se apaga; o cursor segue para **4**, clica e exibe o mesmo círculo/check verde da versão anterior. A saída preserva o primeiro quadro do MP4 já recomposto com a opção 4 marcada. **O erro no 3 e acerto no 4 são exclusivamente dramatização do quiz para a abertura, não determinação clínica do código ICDAS na imagem.**

**Prévia isolada:** botão `Testar 3D → foto e quiz` disponível após o glTF carregar. Começa no progresso 73% do segundo avanço, com malha já revelada, e reproduz a gradação de cor, o encaixe e a interação completa. Evita repetir o prólogo a cada ajuste. A apresentação normal com dois avanços manuais continua intacta. Arquivos alterados: `tools/tcc-opening-prototype/src/main.js`, `src/quiz.css`, `index.html`, `README.md` e este handoff. Nenhuma mudança na produção principal ou `git push`.

**Validação técnica:** `node --check`, `npm run build`, verificação de tokens de shader Three.js, HTML/CSS e HTTP privado Tailscale executados. O efeito renderizado e o ritmo final ainda precisam da aprovação visual no Legion.

## V0.10.1 — relatório de otimização e congelamento operacional

As mudanças de performance preservam a V0.10 aprovada: redução das duas texturas 4096² → 2048² (original 4K preservado no ZIP), retirada de fontes redundantes do diretório público, amostrador de superfície glTF reutilizado, DOM não atualizado desnecessariamente e WebGL não desenhado atrás de vídeo/slide. Novo servidor estático leve no mesmo IP Tailscale, com pré-compressão gzip de HTML/JS/CSS/glTF/binário e HTTP Range 206 para MP4. O inspetor oferece telemetria opcional de FPS/p95/draw calls e seleção de escala de renderização. Números, benchmark, integridade, regressões e pontos ainda não medidos constam do relatório canônico `docs/TCC_ABERTURA_PERFORMANCE_20261120.md`. O processo continua não persistente após reboot; assets privados permanecem só no host e não devem ir a repositório público.
