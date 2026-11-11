# Árvore de tratamento — interface consolidada

Estado: **versão visual escolhida — Corte**, implementada no ICDASQuiz. A validação clínica dos percursos com o professor Rodrigo Varella de Carvalho continua pendente.

## Direção visual adotada

- **Uma única árvore vertical**, sem os spikes horizontal, stepper ou outros modos.
- **Um único SVG esquemático em corte dental** para cada alternativa radiográfica; não há botão de alternância nem visualização “Camadas”.
- Os desenhos locais ilustram esmalte, dentina e, quando aplicável, uma região escurecida indicando extensão aproximada. **Não são radiografias reais nem representam regras clínicas validadas.**
- As caixas ajustam largura e altura conforme conteúdo e espaço disponível; códigos ICDAS são círculos com diâmetro responsivo.
- Perguntas, escolhas e resultados permanecem centralizados. Se o ramo tiver somente 1 ou 3 códigos disponíveis, nenhum espaço é reservado para opções ausentes.
- Alternativas não selecionadas permanecem **cinzas, visíveis e clicáveis**. Clicar em outra alternativa recalcula os passos descendentes.
- O SVG de conexões usa somente dois paths (linhas e pontas) e desenha apenas o caminho escolhido: pergunta → opção → próxima pergunta ou desfecho.
- As etiquetas são por extenso; resultados compostos mantêm a separação do slide sem presumir o significado da barra.
- Tudo funciona sem requisições novas, dependências JavaScript externas, cookies ou escrita no banco.

## Arquivos e ownership

- `app.py` e `templates/arvore_tratamento.html`: rota GET e estrutura HTML.
- `static/js/arvore_modelo.js`: grafo declarativo de transcrição e filtro que evita percursos sem saída.
- `static/js/arvore_tratamento.js`: estado, interação, geração única de SVG em corte e posicionamento das setas.
- `static/css/arvore_tratamento.css`: estilo responsivo isolado da árvore.
- `tools/test_arvore_modelo.cjs` e `tests.py`: testes de lógica e integração.

As seções existentes do guia de classificação ICDAS, quiz, galeria e dashboard não foram substituídas pela árvore de tratamento.

## Ressalvas acadêmicas

Os slides fornecidos por Alan são a fonte da transcrição. A referência citada é Meyer-Lueckel H, Paris S. *When and How to Intervene in the Caries Process.* Oper Dent. 2016;41(S7):S35–S47. DOI 10.2341/15-022-O.

**Ainda exige confirmação do orientador:**
1. Se S/N corresponde à atividade e B/A ao risco de cárie; as palavras atuais são interpretações provisórias.
2. Significado de saídas separadas por barra.
3. Lacunas dos slides: oclusal ICDAS 4–6 com N; proximal sem radiolucidez com ICDAS 3–6.
4. Terminologia radiográfica, equivalência exata com os slides, autoria das figuras e forma de citação no TCC.

Combinações sem desfecho foram **omitidas dos botões**, não preenchidas com condutas inventadas; isso **não significa impossibilidade clínica**. Não apresentar no TCC como protocolo de tratamento validado.

## Validação

- `node --test tools/test_arvore_modelo.cjs`: percursos transcritos e exclusão dos ramos sem saída.
- `python -m pytest -p no:cacheprovider tests.py -q`: rotas, segurança e quiz com SQLite descartável.
- Teste em navegador real: corte em oclusal e proximal, ausência de seletor Camadas, edição de ramos, redimensionamento de caixas, números circulares, ausência de overflow, alinhamento das setas e dimensões mobile/desktop.
- Imagem Docker construída e rotas GET da prévia local verificadas sem utilização do banco de produção.

**Produção, estado PostgreSQL e TCC:** preservar até decisão explícita de publicação e validação clínica.
