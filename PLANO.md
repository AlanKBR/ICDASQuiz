# PLANO DO PROJETO — ICDAS Educacional (TCC)

> Documento de referência: resumo técnico, decisões de stack, boas práticas e roadmap completo.
> Atualizado em: março/2026

---

## 1. Visão Geral

Site educativo sobre o **ICDAS (International Caries Detection and Assessment System)**, desenvolvido como TCC do curso de Odontologia da UFJF-GV. O objetivo é ensinar estudantes e profissionais a identificar e classificar lesões cariosas visualmente, através de material explicativo e um quiz interativo.

**Autor:** Alan Anjos Miranda  
**Orientador:** Prof. Dr. Rodrigo Varella de Carvalho  
**Instituição:** UFJF-GV

---

## 2. Stack Atual e Decisões Técnicas

### Backend
| Camada | Tecnologia | Justificativa |
|---|---|---|
| Linguagem | Python 3 | Simplicidade, ecossistema robusto |
| Framework web | Flask 2.3.3 | Leve, sem overhead desnecessário |
| Templates | Jinja2 (incluso no Flask) | Integração nativa |
| Banco de dados | SQLite (via `sqlite3` padrão do Python) | Zero dependências externas, suficiente para o escopo |

### Frontend
| Camada | Tecnologia | Justificativa |
|---|---|---|
| CSS framework | **Pico CSS** | Minimalista (~10KB), responsivo por padrão, estiliza tags HTML semânticas sem adicionar classes, visual limpo e acadêmico |
| JavaScript | Mínimo (vanilla) | Apenas para interações pontuais do quiz quando necessário |

### Hospedagem
| Etapa | Ferramenta | Observações |
|---|---|---|
| Protótipos ao orientador | **ngrok** | URL temporária, roda local |
| Produção (TCC e além) | **DigitalOcean Droplet** | Créditos via GitHub Education Pack; deploy via repositório Git; disco persistente (SQLite não some no redeploy) |

> **Por que Droplet e não App Platform?**  
> O App Platform do DigitalOcean usa disco efêmero — o arquivo `.db` do SQLite seria apagado a cada redeploy. O Droplet é uma VPS onde o arquivo persiste no disco, sem custo adicional de banco gerenciado.

---

## 3. Estrutura Atual do Projeto

```
app.py                  # Rotas Flask
requirements.txt        # Dependências Python
static/
    css/style.css       # CSS atual (será migrado para Pico CSS)
    imagens/            # Imagens ICDAS (lidas dinamicamente pelo app)
templates/
    base.html           # Layout base (header, nav, footer)
    index.html          # Página inicial — tabela explicativa ICDAS 0-6
    galeria.html        # Grid de imagens
    quiz.html           # Quiz interativo
```

### Imagens disponíveis (março/2026)
- ✅ ICDAS 0 — Superfície Livre, Oclusal
- ✅ ICDAS 1 — Superfície Livre
- ✅ ICDAS 2 — Superfície Livre (2x), Oclusal
- ✅ ICDAS 3 — Superfície Oclusal (2x)
- ❌ **ICDAS 4 — ausente** (aguardando professor)
- ✅ ICDAS 5 — Superfície Livre
- ✅ ICDAS 6 — Superfície Livre

---

## 4. Bugs Conhecidos

### ✅ Bug crítico — Quiz exibia imagem errada após resposta (CORRIGIDO)
**Onde:** `app.py`, rota `/quiz`, método POST  
**O que acontecia:** Após o usuário submeter a resposta, o servidor validava corretamente via `imagem_id`, mas em seguida sorteava uma **nova imagem aleatória** antes de renderizar.  
**Correção aplicada:** Reutiliza a imagem do POST ao renderizar o feedback; sorteia nova imagem apenas no GET.

---

## 5. Boas Práticas Pendentes

| Problema | Impacto | Status |
|---|---|---|
| `debug=True` hardcoded em `app.run()` | Expunha tracebacks em produção | ✅ Resolvido |
| Sem variáveis de ambiente (`.env`) | Configuração misturada ao código | ✅ Resolvido |
| Sem `.gitignore` | `__pycache__`, `.env`, `.db` iam para o repositório | ✅ Resolvido |
| Sem tratamento de erro 404/500 | UX ruim em erros | ✅ Resolvido |
| Imagem do quiz sem fallback (`None`) | Quebrava a página se pasta estivesse vazia | ✅ Resolvido |
| `alt` genérico na imagem do quiz | Acessibilidade ruim | ✅ Resolvido |
| ICDAS 4 ausente | Conteúdo incompleto | ⏳ Aguarda professor |
| Headers de segurança ausentes | Segurança em produção | ✅ Adicionado |
| Validação de input no quiz | Possível crash com dados inválidos | ✅ Resolvido |

---

## 6. Roadmap

As fases são **priorizáveis independentemente**. Fase 0 deve ser feita antes de qualquer outra.

---

### Fase 0 — Fundação (fazer antes de tudo) ✅
*Tempo estimado: 1–2 horas*

- [x] Corrigir bug do quiz (imagem trocada após resposta)
- [x] Criar `.gitignore` (`__pycache__/`, `.env`, `*.db`, `*.pyc`)
- [x] Mover `debug=True` para variável de ambiente (`FLASK_DEBUG=1`)
- [x] Criar arquivo `.env.example` documentando as variáveis necessárias
- [x] Instalar `python-dotenv` e carregar `.env` no `app.py`
- [x] Adicionar tratamento de erro quando pasta de imagens estiver vazia

**Resultado:** Base limpa, segura e pronta para evolução.

---

### Fase 1 — Quiz Evoluído (prioridade máxima — peça central) ✅
*Tempo estimado: 4–8 horas*

- [x] **Placar por sessão:** exibir acertos/total durante a sessão usando `flask.session` (sem banco de dados, reseta ao fechar o browser)
- [x] **Fluxo corrigido:** botão "Verificar Resposta" → exibe feedback com a imagem correta → botão "Próxima Imagem" para sortear nova
- [x] **Modo sequencial:** opção de percorrer todas as imagens sem repetir, em ordem aleatória fixa para a sessão
- [x] **Descrição clínica após resposta:** ao acertar ou errar, exibir a definição do código ICDAS correspondente (texto já existe na `index.html` — só reutilizar)
- [x] **Feedback visual melhorado:** destaque claro para resposta certa/errada (verde/vermelho com Pico CSS)
- [x] **Persistência de scores com SQLite:** ao finalizar uma rodada, salvar `(data, total_questoes, acertos)` no banco — sem identificação de usuário por enquanto

---

### Fase 2 — Design e Responsividade ✅
*Tempo estimado: 3–6 horas*

- [x] **Migrar para Pico CSS:** substituir o `style.css` atual, ajustar o `base.html` para incluir o CDN ou arquivo local do Pico CSS
- [x] Adaptar `base.html`: nav mobile-friendly (Pico CSS já oferece navbar responsiva)
- [x] Adaptar galeria para funcionar bem no celular (grid já é responsivo com CSS Grid, ajustar breakpoints)
- [x] Adaptar quiz para tela pequena (botões de opção grandes, fáceis de tocar)
- [x] Adicionar favicon (pode ser um dente simples em SVG)
- [x] Revisar tipografia e espaçamentos com variáveis do Pico CSS

---

### Fase 3 — Conteúdo e Galeria ✅
*Tempo estimado: 2–4 horas + tempo do professor para assets*

- [ ] Adicionar ICDAS 4 assim que o professor enviar a imagem *(aguardando professor)*
- [x] Galeria com **filtro por código ICDAS** (ex: botões 0–6 para filtrar)
- [x] Cada imagem na galeria exibe o código e a descrição clínica abaixo
- [x] Criar um arquivo `descricoes.json` (ou tabela SQLite) para gerenciar descrições por imagem — facilita adicionar novas imagens sem mudar o código
- [x] Página `/sobre` com contexto acadêmico: orientador, instituição, metodologia, referências bibliográficas

---

### Fase 4 — Deploy e Apresentação
*Tempo estimado: 2–4 horas*

- [ ] Configurar Droplet no DigitalOcean (Ubuntu + Python + Gunicorn + Nginx)
- [ ] Script de deploy via Git (pull + restart do Gunicorn)
- [ ] Configurar HTTPS com Let's Encrypt (Certbot — gratuito)
- [ ] Testar fluxo completo em celular no servidor real
- [ ] Criar `README.md` do repositório com instruções de instalação e contexto do projeto (para a banca e para o portfólio)
- [ ] Testar ngrok para demos ao orientador antes do deploy final

---

### Fase 5 — Futuro (pós-TCC, opcional)
*Sem estimativa de tempo*

- [ ] Painel do professor: upload de novas imagens sem precisar acessar o servidor
- [ ] Histórico detalhado: quais imagens o aluno mais erra
- [ ] Múltiplos modos de quiz: cronometrado, por dificuldade
- [ ] Vídeos ou animações explicativas por código ICDAS
- [ ] Autenticação simples para o professor (login/senha)
- [ ] Exportar relatório de desempenho (CSV ou PDF)

---

## 7. Guia Rápido — Rodar Localmente

```bash
# 1. Clonar o repositório
git clone <url-do-repo>
cd tcc

# 2. Criar ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Copiar variáveis de ambiente
cp .env.example .env
# editar .env conforme necessário

# 5. Rodar o app
python app.py
# Acesse: http://localhost:5000
```

## 8. Guia Rápido — Protótipo com ngrok

```bash
# Com o app rodando localmente na porta 5000:
ngrok http 5000
# Copiar a URL pública gerada e enviar ao orientador
```

---

## 9. Estrutura Futura do Projeto (após Fase 2)

```
app.py
requirements.txt
.env                    # NÃO commitar
.env.example            # Commitar — documenta as variáveis
.gitignore
icdas.db                # Banco SQLite — NÃO commitar
descricoes.json         # Metadados das imagens
static/
    css/                # Estilo customizado sobre o Pico CSS (mínimo)
    imagens/            # Imagens ICDAS
templates/
    base.html
    index.html
    galeria.html
    quiz.html
    sobre.html          # Novo
    404.html            # Novo
    500.html            # Novo
```

---

## 10. Dependências Planejadas

| Pacote | Uso | Quando adicionar |
|---|---|---|
| `flask` | Framework web | Já instalado |
| `python-dotenv` | Carregar `.env` | Fase 0 |
| `Werkzeug` | Já incluso no Flask | Já instalado |
| *(sem ORM)* | SQLite via `sqlite3` nativo do Python | Fase 1 |
| `gunicorn` | Servidor WSGI para produção | Fase 4 |
