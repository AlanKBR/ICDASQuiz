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
- **Histórico de pontuações** salvo em banco de dados (SQLite)
- **Dois modos de quiz:** aleatório e sequencial (percorre todas as imagens uma vez)

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.10+ |
| Framework web | Flask 2.3.3 |
| Templates | Jinja2 (incluso no Flask) |
| Banco de dados | SQLite (biblioteca padrão do Python) |
| CSS | [Pico CSS](https://picocss.com/) — minimalista, responsivo, sem classes |
| JavaScript | Vanilla JS mínimo (filtros da galeria) |
| Servidor WSGI | Gunicorn (produção) |
| Configuração | python-dotenv |

---

## Estrutura do Projeto

```
icdas-educacional/
├── app.py                  # Aplicação Flask: rotas, lógica, banco de dados
├── tests.py                # Suite de testes (pytest)
├── requirements.txt        # Dependências Python
├── descricoes.json         # Descrições clínicas dos códigos ICDAS 0–6
├── .env.example            # Template de variáveis de ambiente (commitar)
├── .env                    # Variáveis locais/produção (NÃO commitar)
├── .gitignore
├── static/
│   ├── css/
│   │   └── custom.css      # Customizações sobre o Pico CSS
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

---

## Variáveis de Ambiente

Copie `.env.example` para `.env` e preencha:

| Variável | Descrição | Padrão |
|---|---|---|
| `FLASK_DEBUG` | `1` para dev, `0` para produção | `0` |
| `SECRET_KEY` | Chave criptográfica para sessões | *obrigatório em produção* |
| `DB_PATH` | Caminho do arquivo SQLite | `icdas.db` |

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
- Persistência de scores no SQLite
- Tratamento de entradas inválidas
- Headers de segurança
- Funções auxiliares (`get_imagens`, `_safe_int`, `_quiz_pop`)

Cada teste usa um banco de dados temporário isolado via `tmp_path` do pytest.

---

## Deploy em Produção (DigitalOcean Droplet)

> Recomenda-se um Droplet (VPS) em vez do App Platform pois o SQLite precisa de disco persistente.

### 1. Preparar o servidor (Ubuntu 22.04)

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx

# Clonar o repositório
git clone https://github.com/<seu-usuario>/icdas-educacional.git /var/www/icdas
cd /var/www/icdas

# Ambiente virtual e dependências
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
nano .env  # preencher SECRET_KEY e DB_PATH
```

### 2. Configurar Gunicorn como serviço systemd

Crie `/etc/systemd/system/icdas.service`:

```ini
[Unit]
Description=ICDAS Educacional — Gunicorn
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/icdas
EnvironmentFile=/var/www/icdas/.env
ExecStart=/var/www/icdas/venv/bin/gunicorn -w 2 -b 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now icdas
```

### 3. Configurar Nginx como proxy reverso

```nginx
server {
    server_name seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/icdas/static/;
        expires 7d;
    }
}
```

### 4. HTTPS com Let's Encrypt

```bash
sudo certbot --nginx -d seu-dominio.com
```

### 5. Deploy de atualizações

```bash
cd /var/www/icdas
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart icdas
```

---

## Exposição via ngrok (demos ao orientador)

```bash
# Com o app rodando localmente na porta 5000:
ngrok http 5000
# Envie a URL gerada ao orientador — válida enquanto o processo estiver rodando
```

---

## Segurança

A aplicação implementa as seguintes medidas:

- **Content Security Policy (CSP)** restrita — permite apenas recursos do próprio servidor e jsdelivr.net
- **X-Content-Type-Options: nosniff**
- **X-Frame-Options: SAMEORIGIN**
- **Referrer-Policy: strict-origin-when-cross-origin**
- **Permissions-Policy** desativa câmera, microfone, geolocalização e pagamento
- **HSTS** (Strict-Transport-Security) ativado apenas em produção (`FLASK_DEBUG=0`)
- **SESSION_COOKIE_SECURE** ativo em produção (requer HTTPS)
- **SESSION_COOKIE_HTTPONLY** e **SESSION_COOKIE_SAMESITE=Lax** sempre ativos
- Validação de todos os inputs do quiz no servidor
- Padrão PRG (Post/Redirect/Get) no quiz para evitar reenvio de formulário com F5

---

## Licença

Este projeto foi desenvolvido para fins acadêmicos como TCC. Para outros usos, entre em contato com o autor.

---

## Referências

- Ismail AI, Sohn W, Tellez M, et al. *The International Caries Detection and Assessment System (ICDAS): an integrated system for measuring dental caries.* Community Dent Oral Epidemiol. 2007;35(3):170-178.
- Pitts NB. *ICDAS — a foundation for innovation in caries management.* Dental Update. 2009;36(5):268-272.
- Diniz MB, et al. *Validity of ICDAS clinical criteria for caries detection in occlusal surfaces in vitro.* Caries Res. 2009;43(5):405-409.
