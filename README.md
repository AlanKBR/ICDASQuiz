# ICDAS Educacional

Plataforma web educativa para o aprendizado do sistema **ICDAS (International Caries Detection and Assessment System)**, desenvolvida como Trabalho de Conclusão de Curso (TCC) do curso de Odontologia da **UFJF-GV**.

> **Autor:** Alan Anjos Miranda  
> **Orientador:** Prof. Dr. Rodrigo Varella de Carvalho  
> **Instituição:** Universidade Federal de Juiz de Fora — Campus Governador Valadares (UFJF-GV)

---

## Sobre o Projeto

O ICDAS é um sistema internacional padronizado de detecção e classificação de lesões cariosas (cáries dentárias) em escala de 0 a 6, permitindo diagnósticos mais precisos e uniformes na Odontologia.

Esta aplicação oferece:

- **Página informativa** com a tabela completa dos códigos ICDAS 0–6 e suas descrições clínicas
- **Galeria de imagens clínicas** filtráveis por código, com descrição de cada lesão
- **Quiz interativo** que exibe imagens reais e pede ao usuário que classifique o código ICDAS correto, com feedback imediato e descrição clínica após a resposta
- **Histórico de pontuações** salvo em banco relacional, com SQLite embedded para uso local e PostgreSQL para produção
- **Dois modos de quiz:** aleatório e sequencial (percorre todas as imagens uma vez)

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.10+ (Python 3.13 na imagem de produção) |
| Framework web | Flask 3.1.x |
| Templates | Jinja2 (incluso no Flask) |
| Banco de dados | SQLAlchemy 2 + Alembic; SQLite embedded ou PostgreSQL |
| CSS | Tailwind CSS 4 (artefato compilado) + CSS local |
| JavaScript | Vanilla JS mínimo (filtros da galeria) |
| Servidor WSGI | Gunicorn (produção) |
| Configuração | python-dotenv |

---

## Estrutura do Projeto

```
icdas-educacional/
├── app.py                  # Aplicação Flask e rotas
├── database.py             # Modelos/repositório SQLAlchemy e seleção do backend
├── alembic.ini             # Configuração das migrations
├── migrations/             # Schema versionado e portável
├── tests.py                # Suite de testes (pytest)
├── requirements.txt        # Dependências Python pinadas
├── Dockerfile              # Imagem de produção, executada sem root
├── descricoes.json         # Descrições clínicas dos códigos ICDAS 0–6
├── .env.example            # Template de variáveis de ambiente (commitar)
├── .env                    # Variáveis locais/produção (NÃO commitar)
├── .gitignore
├── static/
│   ├── css/
│   │   ├── tailwind.css    # Tailwind compilado e versionado para produção
│   │   ├── custom.css      # Ajustes locais
│   │   └── ui.css          # Componentes e polimento visual
│   ├── js/
│   │   ├── galeria.js      # Filtros interativos da galeria
│   │   └── quiz.js         # Interações do quiz
│   └── imagens/            # Imagens clínicas ICDAS (adicionadas manualmente)
└── templates/
    ├── base.html           # Layout base (nav, header, footer)
    ├── index.html          # Página inicial com tabela ICDAS
    ├── galeria.html        # Galeria de imagens com filtro
    ├── quiz.html           # Quiz interativo
    ├── scores.html         # Histórico de pontuações
    ├── sobre.html          # Sobre o projeto e referências
    ├── 404.html            # Página de erro 404
    └── 500.html            # Página de erro 500
```

---

## Pré-requisitos

- Python 3.10 ou superior
- pip

---

## Instalação e Uso Local

```bash
# 1. Clonar o repositório
git clone https://github.com/<seu-usuario>/icdas-educacional.git
cd icdas-educacional

# 2. Criar e ativar o ambiente virtual
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Abra o .env e ajuste conforme necessário (ver seção Variáveis de Ambiente)

# 5. Iniciar a aplicação
python app.py
```

Acesse em: **http://localhost:5000**

### Backends de banco

O código da aplicação não depende de um banco específico. A seleção é feita nesta ordem:

1. `DATABASE_URL`, quando definida;
2. variáveis `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD`;
3. SQLite embedded em `DB_PATH` (padrão: `icdas.db`).

Isso permite entregar o projeto para execução local sem instalar um servidor de banco: basta deixar `DATABASE_URL` e `POSTGRES_HOST` ausentes e o próprio processo abre um arquivo SQLite. Em um servidor institucional ou serviço gerenciado, basta apontar para PostgreSQL sem alterar o código.

O schema é controlado pelo **Alembic**. A aplicação aplica `alembic upgrade head` automaticamente ao iniciar. A migration inicial também adota bancos SQLite antigos que já possuíam a tabela `scores`.

### Produção no Zezin

A aplicação de produção é hospedada no servidor Zezin com PostgreSQL. Este repositório é o owner do **código da aplicação**; configuração de infraestrutura, rota, lifecycle, state, backup e rollback pertencem ao owner operacional `/srv/zezin/services/icdasquiz` no servidor.

Banco, segredos e arquivos SQLite locais **nunca devem ser commitados**. Não replique Cloudflare, Traefik, firewall ou configuração de backup dentro deste repositório. Para um redeploy no Zezin, altere o código aqui e use o runbook do owner operacional.

### Sincronização entre máquinas

`origin/main` é a referência compartilhada para cópias de desenvolvimento. Antes de começar trabalho em outra máquina, execute:

```bash
python tools/sync_repo.py
```

No Windows, `sync.cmd` faz a mesma operação com duplo clique. O sincronizador só aceita `main`, exige working tree limpa e usa **fast-forward only**: se houver mudanças locais, commits ainda não publicados ou histórico divergente, ele para sem sobrescrever nada.

Produção não faz auto-deploy de `main`: o Zezin implanta um commit explícito e registra esse SHA no owner operacional.

---

## Variáveis de Ambiente

Copie `.env.example` para `.env` e preencha:

| Variável | Descrição | Padrão |
|---|---|---|
| `FLASK_DEBUG` | `1` para dev, `0` para produção | `0` |
| `SECRET_KEY` | Chave criptográfica para sessões | *obrigatório em produção* |
| `DATABASE_URL` | URL SQLAlchemy; use para PostgreSQL externo/gerenciado | vazio |
| `DB_PATH` | Caminho do SQLite embedded quando não há backend servidor | `icdas.db` |
| `POSTGRES_HOST` | Host PostgreSQL; ativa montagem de URL por componentes | vazio |
| `POSTGRES_PORT` | Porta PostgreSQL | `5432` |
| `POSTGRES_DB` | Banco PostgreSQL | obrigatório com `POSTGRES_HOST` |
| `POSTGRES_USER` | Usuário PostgreSQL | obrigatório com `POSTGRES_HOST` |
| `POSTGRES_PASSWORD` | Senha PostgreSQL | obrigatório com `POSTGRES_HOST` |

### Gerando uma SECRET_KEY segura

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> **Aviso:** nunca use `FLASK_DEBUG=1` em produção. O app detecta isso e ativa headers de segurança adicionais (HSTS, Secure cookies) apenas quando `FLASK_DEBUG=0`.

---

## Adicionando Imagens

As imagens clínicas são lidas dinamicamente da pasta `static/imagens/`. Para adicionar uma nova imagem:

1. Nomeie o arquivo com o padrão `ICDAS_<codigo>_<descricao>.jpg` (ex: `ICDAS_2_oclusal.jpg`)
2. Coloque o arquivo em `static/imagens/`
3. O app detecta automaticamente na próxima requisição (cache por mtime)

Formatos suportados: `.png`, `.jpg`, `.jpeg`, `.webp`

---

## Testes

O projeto usa **pytest**. Para rodar a suite completa:

```bash
pip install pytest  # já incluso se instalou requirements.txt de dev
python -m pytest tests.py -v
```

Os testes cobrem:

- Rotas básicas (status code e conteúdo)
- Lógica do quiz (fluxo POST→redirect→GET, placar, fila, modos aleatório e sequencial)
- Persistência e migrations sobre SQLite; produção é validada também contra PostgreSQL
- Tratamento de entradas inválidas
- Headers de segurança
- Funções auxiliares (`get_imagens`, `_safe_int`, `_quiz_pop`)

Cada teste usa um banco de dados temporário isolado via `tmp_path` do pytest.

---

## Segurança

A aplicação implementa as seguintes medidas:

- **Content Security Policy (CSP)** restrita a recursos do próprio servidor
- **X-Content-Type-Options: nosniff**
- **X-Frame-Options: DENY**
- **Referrer-Policy: strict-origin-when-cross-origin**
- **Permissions-Policy** desativa câmera, microfone, geolocalização e pagamento
- **HSTS** (Strict-Transport-Security) ativado apenas em produção (`FLASK_DEBUG=0`)
- **SESSION_COOKIE_SECURE** ativo em produção (requer HTTPS)
- **SESSION_COOKIE_HTTPONLY** e **SESSION_COOKIE_SAMESITE=Lax** sempre ativos
- Validação de todos os inputs do quiz no servidor
- Validação de host em produção (`TRUSTED_HOSTS`)
- Rate limiting pelo IP original validado da borda Cloudflare, sem confiar em `X-Forwarded-For`
- Persistência apenas de HMAC do IP para a sugestão local de nome; o IP não é armazenado em claro nem mascarado
- Padrão PRG (Post/Redirect/Get) no quiz para evitar reenvio de formulário com F5

---

## Licença

Este projeto foi desenvolvido para fins acadêmicos como TCC. Para outros usos, entre em contato com o autor.

---

## Referências

- Ismail AI, Sohn W, Tellez M, et al. *The International Caries Detection and Assessment System (ICDAS): an integrated system for measuring dental caries.* Community Dent Oral Epidemiol. 2007;35(3):170-178.
- Pitts NB. *ICDAS — a foundation for innovation in caries management.* Dental Update. 2009;36(5):268-272.
- Diniz MB, et al. *Validity of ICDAS clinical criteria for caries detection in occlusal surfaces in vitro.* Caries Res. 2009;43(5):405-409.
