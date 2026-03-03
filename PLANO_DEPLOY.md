# PLANO DE DEPLOY — Otimização para DigitalOcean App Platform

> Plataforma-alvo: **DigitalOcean App Platform** (buildpack Heroku-Python)  
> App: Flask educacional ICDAS — SQLite, ~10 imagens, PicoCSS via CDN  
> Atualizado em: março/2026

---

## Visão Geral

O DO App Platform detecta automaticamente apps Python via `requirements.txt` e usa o buildpack `heroku-buildpack-python`. O deploy acontece a cada push na branch configurada. O objetivo deste plano é garantir: zero atrito na plataforma, performance máxima, proteção contra abuso e cobranças inesperadas, e segurança reforçada em produção.

**Decisões registradas**
- SQLite versionado no git: banco viaja no repo, writes de runtime não persistem entre redeploys — aceito para TCC
- Concurrent writes com múltiplos workers: resolvido via WAL mode + `timeout=10`
- CSRF: Flask-WTF `CSRFProtect` com macro Jinja2 compartilhada
- Runtime: Python 3.13.2 fixado via `runtime.txt`
- Imagens: convertidas para WebP via pipeline automatizado

---

## Bloco 1 — Arquivos de Plataforma (DO App Platform)

### `runtime.txt`
Fixar versão Python evita upgrade silencioso pelo buildpack entre deploys.

```
python-3.13.2
```

### `Procfile`
O DO exige o flag `--worker-tmp-dir /dev/shm` para o gunicorn funcionar corretamente em container (sem ele, o process falha silenciosamente). `$PORT` é injetado automaticamente pelo App Platform. `--workers 2` é o máximo seguro para 512 MB RAM.

```
web: gunicorn --worker-tmp-dir /dev/shm --workers 2 --bind 0.0.0.0:$PORT app:app
```

### `.gitignore`
O `icdas.db` **não entra no gitignore** — o banco é versionado e faz parte do deploy com dados iniciais. Apenas arquivos genuinamente excluídos:

```
__pycache__/
*.pyc
.env
.venv/
*.egg-info/
```

---

## Bloco 2 — SQLite com WAL (Escritas Simultâneas)

Com 2 workers gunicorn (`--workers 2`), escritas simultâneas em SQLite podem resultar em `database is locked`. A solução é ativar **WAL mode** (Write-Ahead Logging), que permite leituras concorrentes durante um write ativo.

Em `get_db()` no `app.py`:

```python
db = sqlite3.connect(DB_PATH, timeout=10)
db.execute("PRAGMA journal_mode=WAL")
db.execute("PRAGMA synchronous=NORMAL")
db.row_factory = sqlite3.Row
```

- `timeout=10`: aguarda até 10s antes de lançar `OperationalError` — evita erro imediato sob contenção leve
- `synchronous=NORMAL`: durabilidade suficiente para dados não-críticos, com melhor performance que `FULL`
- O arquivo `icdas.db` com WAL ativo gera um `icdas.db-wal` e `icdas.db-shm` temporários que **não devem ser commitados** — adicionar ao `.gitignore`:

```
icdas.db-wal
icdas.db-shm
```

---

## Bloco 3 — Dependências

Adicionar ao `requirements.txt`:

```
Flask-Compress>=1.15
Flask-Limiter>=3.5
Flask-WTF>=1.2
```

---

## Bloco 4 — Compressão HTTP

`Flask-Compress` aplica gzip automaticamente em HTML, CSS, JS e JSON sem configuração adicional. Redução típica de 60–75% no tamanho dos responses.

```python
from flask_compress import Compress
Compress(app)
```

Inicializar logo após `app = Flask(__name__)`.

---

## Bloco 5 — Rate Limiting

`Flask-Limiter` protege rotas que geram DB writes ou processamento, evitando abuso que gere cobranças de largura de banda ou esgote recursos do plano gratuito.

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["200 per minute"],
)
```

Limites específicos por rota (via decorator):

| Rota                  | Método | Limite          |
|-----------------------|--------|-----------------|
| `/quiz`               | POST   | 60 per minute   |
| `/quiz/finalizar`     | POST   | 10 per minute   |
| `/quiz/modo`          | POST   | 20 per minute   |
| `/quiz/resetar`       | POST   | 20 per minute   |
| `/scores`             | GET    | 30 per minute   |

Customizar o handler 429:

```python
@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template("429.html"), 429
```

---

## Bloco 6 — CSRF com Flask-WTF

`CSRFProtect` protege automaticamente todos os formulários POST. O token é injetado via sessão Flask já existente — sem custo extra.

```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
app.config["WTF_CSRF_TIME_LIMIT"] = 3600  # token válido por 1h
```

### Macro Jinja2 compartilhada

Criar `templates/_macros.html`:

```jinja
{% macro csrf() %}<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">{% endmacro %}
```

Importar e invocar em cada `<form method="post">` dos templates afetados (`quiz.html`):

```jinja
{% from "_macros.html" import csrf %}
...
<form method="post">
    {{ csrf() }}
    ...
</form>
```

### Testes

Adicionar `app_module.app.config["WTF_CSRF_ENABLED"] = False` no fixture `client` do `tests.py` para que os testes continuem passando sem simular tokens.

---

## Bloco 7 — Cache de Assets Estáticos

Arquivos em `/static/` são cacheados por 1 ano no browser. O Flask já faz cache-busting via query string no `url_for('static', ...)`. Rotas dinâmicas nunca são cacheadas.

Dentro do `after_request` `set_security_headers` no `app.py`:

```python
if request.path.startswith("/static/"):
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
else:
    response.headers["Cache-Control"] = "no-store"
```

---

## Bloco 8 — Conversão de Imagens para WebP

### Pipeline automatizado

Ao invés de converter cada imagem manualmente, usar o script `tools/convert_images.py` que processa toda a pasta `static/imagens/` de uma vez:

```
python tools/convert_images.py
```

O script:
1. Encontra todos os PNGs e JPEGs em `static/imagens/`
2. Converte cada um para WebP com qualidade 82 via Pillow (sem dependência externa do `cwebp`)
3. Exibe tamanho antes/depois e percentual de redução
4. Não apaga os originais (manter até validar em produção)

Após validar que tudo funciona no deploy, remover os PNGs originais e commitar apenas os WebPs.

O `app.py` já aceita `.webp` em `IMAGEM_EXTENSOES` — nenhuma mudança no backend necessária.

### Pasta `imagens/` raiz

Deletar `imagens/` da raiz do projeto. É um duplicado de `static/imagens/` não servido pelo Flask — ocupa espaço desnecessário no deploy.

---

## Bloco 9 — Headers de Segurança Complementares

O `app.py` já tem boa base (CSP, HSTS, X-Frame-Options, Referrer-Policy, Permissions-Policy). Adicionar ao `set_security_headers`:

```python
response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
```

### Subresource Integrity (SRI) no Pico CSS

No `base.html`, adicionar `integrity` e `crossorigin` no `<link>` do CDN para garantir que um CDN comprometido não sirva CSS malicioso:

```html
<link rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css"
      integrity="sha384-HASH_AQUI"
      crossorigin="anonymous">
```

Gerar o hash em [srihash.org](https://www.srihash.org/) com a URL exata do Pico v2.

---

## Bloco 10 — robots.txt e Lazy Loading

### robots.txt

Criar `static/robots.txt` e uma rota dedicada para servi-lo. Bloqueia crawlers nas rotas dinâmicas que geram DB writes, economizando recursos e largura de banda:

```
User-agent: *
Disallow: /quiz
Disallow: /scores
Allow: /
```

### Lazy loading nas imagens do quiz

No `quiz.html`, adicionar `loading="lazy" decoding="async"` na tag `<img>` da imagem clínica (a galeria já tem `loading="lazy"`).

---

## Bloco 11 — Variáveis de Ambiente no Painel DO

Configurar no dashboard do App Platform (Settings → Environment Variables):

| Variável     | Valor                                                               |
|--------------|---------------------------------------------------------------------|
| `SECRET_KEY` | Gerar: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_DEBUG`| `0`                                                                 |
| `DB_PATH`    | `icdas.db` (já é o default — confirmar que o arquivo viaja no repo)|

---

## Checklist de Verificação Pré-Deploy

- [ ] `python -m pytest tests.py -v` passa 100% localmente
- [ ] `runtime.txt` e `Procfile` presentes na raiz
- [ ] `icdas.db` commitado (com WAL mode ativado ao menos uma vez localmente)
- [ ] `icdas.db-wal` e `icdas.db-shm` no `.gitignore`
- [ ] Imagens convertidas para WebP e validadas
- [ ] `SECRET_KEY`, `FLASK_DEBUG=0` definidos no painel DO
- [ ] Formulários POST todos com `{{ csrf() }}`
- [ ] `WTF_CSRF_ENABLED = False` nos fixtures de teste

## Checklist de Verificação Pós-Deploy

- [ ] Build log sem warnings de `--worker-tmp-dir`
- [ ] `curl -I https://SEU-APP.ondigitalocean.app/` → `Strict-Transport-Security` presente
- [ ] `curl -I https://SEU-APP.ondigitalocean.app/` → `Content-Security-Policy` presente
- [ ] `curl -I https://SEU-APP.ondigitalocean.app/static/css/custom.css` → `Cache-Control: public, max-age=31536000`
- [ ] `curl -I https://SEU-APP.ondigitalocean.app/` → `Cache-Control: no-store`
- [ ] 61 POSTs rápidos em `/quiz` retornam HTTP 429
- [ ] POST em `/quiz` sem `csrf_token` retorna HTTP 400
- [ ] Página `/galeria` exibe imagens WebP sem quebrar
