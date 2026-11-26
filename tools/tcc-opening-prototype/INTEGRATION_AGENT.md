# ICDASQuiz — Handoff para o agente da apresentação (pacote OFFLINE)

**Pacote:** abertura cinematográfica do TCC, V0.10.2 portátil.
**Conteúdo visual aprovado:** V0.10; otimizações e adaptação offline posteriores não mudam o roteiro aprovado.
**Data de corte:** 20/11/2026.
**Escopo:** apenas a abertura, não todo o ICDASQuiz.

## Como testar sem rede

1. Extraia TODO o arquivo ZIP para uma pasta local. Não abra o HTML diretamente por `file://`: o modelo glTF precisa ser carregado por HTTP.
2. Linux/CachyOS (Legion): execute `./start-linux.sh`, ou `python3 run_offline.py`. Windows: `start-windows.cmd`, com Python 3 instalado.
3. O inicializador abre um navegador no endereço `http://127.0.0.1:PORTA/`, com porta livre selecionada automaticamente. Para testar só a apresentação: `python3 run_offline.py --presentation`.
4. O pacote não usa API, CDN, login, banco de dados, Tailscale ou internet. Python 3 é usado apenas para servir os arquivos locais, e pode ser substituído pelo servidor estático da própria aplicação final.
5. Pressione Ctrl+C no terminal para encerrar.

## Sequência e temporizações

- **Cena inicial:** título ICDASQuiz; ICDAS em branco frio, Quiz em menta com breathing discreto. Espera pelo primeiro avanço.
- **Avanço 1 (4,25 segundos):** as letras-mãe emitem cópias translúcidas, que se dobram e formam o molar ASCII; somente letras I C D A S Q u i z. A versão preferida é Dobra Espacial 04, outras três variantes são opções de revisão.
- **Pausa manual:** molar ASCII permanece girando até o segundo comando do apresentador.
- **Avanço 2 (5 segundos):** molar ASCII → glTF anatômico opaco → orientação oclusal → monitor e coloração creme → foto clínica.
- **Quiz visual (7 segundos):** observação inicial; cursor passa por códigos 5 e 2, clica 3 (vermelho com tremor, erro dramático), depois 4 (check verde).
- **Vídeo final (4 segundos):** câmera gira até o apresentador/aceno, volta ao monitor, e a primeira imagem do slide real ocupa a tela. Ao terminar, não há troca automática para outros slides. **A atribuição 3 incorreto/4 correto é cenográfica, e não um diagnóstico ICDAS da fotografia.**

Duração ativa padrão: **20,25 segundos + duas esperas manuais indefinidas**.

## Modos de execução

- `/` — painel de prototipagem completo, com controles e telemetria.
- `/?presentation=1` — somente a cena 16:9, sem cabeçalho, inspetor ou controles. É o modo preferível para integrar como abertura da apresentação.

A pasta `site/` é o build estático final e inclui modelos, texturas, imagens, vídeo e licença. Os caminhos de recursos são **relativos** (não dependem da raiz do domínio). Pode-se servir a pasta em `/opening/` no mesmo servidor HTTP da apresentação e abrir `/opening/index.html?presentation=1`.

A pasta `source/` contém arquivos-fonte JavaScript/CSS/HTML e package.json/package-lock.json para alterações futuras. Para reconstruir, é necessário instalar as dependências com npm e copiar `site/assets/` para `source/public/assets/` antes de compilar. **Não é necessário npm, Node ou build para EXECUTAR a apresentação do pacote.**

## Comunicação com o deck principal (iframe de mesma origem)

Exemplo de integração:

```html
<iframe id="opening" src="/opening/index.html?presentation=1"
        style="width:100vw;height:100vh;border:0" allow="autoplay"></iframe>
```

O deck pode enviar comandos à abertura:

```js
const frame = document.querySelector('#opening');
frame.contentWindow.postMessage({
  source: 'icdasquiz-presentation-controller',
  action: 'next'
}, window.location.origin);

// Primeiro 'next': título → molar ASCII.
// Segundo 'next': molar → vídeo → primeiro slide.
frame.contentWindow.postMessage({
  source: 'icdasquiz-presentation-controller',
  action: 'reset'
}, window.location.origin);
```

A abertura emite eventos de estado para `window.parent`:

```js
window.addEventListener('message', event => {
  if (event.origin !== location.origin) return;
  if (event.data?.source !== 'icdasquiz-opening') return;
  if (event.data.event !== 'phase') return;
  // event.data.phase pode ser:
  // title, forming, asciiReady, mesh, finished
  if (event.data.phase === 'finished') {
    // A abertura terminou. O deck deve prosseguir quando apropriado.
  }
});
```

**Segurança:** os comandos são aceitos apenas da janela-mãe na mesma origem; não adicionar controle cross-origin sem revisar permissões. No modo direto, teclado, botão Próximo e clique continuam funcionando.

## Licenças, privacidade e artefatos

- Modelo glTF: **Maxillary First Molar** — University of Dundee, School of Dentistry, Sketchfab — **CC BY 4.0**. Preservar atribuição na apresentação final. Licença integral em `site/assets/molar/license.txt`.
- Fotos, vídeo e personagem são recursos pessoais do autor. Este pacote foi preparado para **uso privado e envio ao agente autorizado a produzir a apresentação**. Não publicar assets em Git público, CDN ou página pública sem decisão explícita do titular.
- A imagem clínica e a textura odontológica são referências visuais; não usar a cena como avaliação clínica ou resposta oficial do sistema ICDASQuiz.
- O original 4K do dente **não** está neste pacote leve; o runtime usa texturas 2K otimizadas. O arquivo-fonte original permanece preservado no Zezin.

## Diagnóstico e testes

- Teste visual deve ocorrer no Legion/projetor, com resolução final, FPS e vídeo.
- No modo de protótipo há telemetria opcional de FPS/p95 e opções de resolução.
- `manifest.json` traz hashes SHA-256 por arquivo; `manifest.sha256` permite validar integridade.
- Antes da defesa, preparar um vídeo da abertura e um PDF/PPTX de contingência caso o navegador do local falhe.
- Não reescrever as animações sem necessidade: a prioridade agora é integrar e ensaiar o TCC completo.
