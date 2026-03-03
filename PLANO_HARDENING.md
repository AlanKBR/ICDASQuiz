# Plano de Hardening & Deploy Readiness — ICDAS Educacional

**Data da auditoria:** 2026-03-02  
**Status:** Pendente de implementação

O app tem boa estrutura base, mas possui **2 falhas críticas que quebram funcionalidade em produção** (CSP bloqueando todos os scripts inline; SECRET_KEY com fallback hardcoded no repo), além de riscos de segurança e robustez que precisam ser corrigidos antes do go-live. O plano está ordenado por prioridade.

---

## Bloco 1 — Crítico (resolver primeiro)

### 1.1 — Mover inline `<script>` de `templates/base.html` para `static/js/base.js`

O bloco `<script>` com ~45 linhas (offline detection, double-submit prevention, shimmer, broken-image fallback) está sendo **silenciosamente bloqueado** pela própria CSP `script-src 'self'` do app em todos os browsers modernos. O usuário não vê erro — a funcionalidade simplesmente não existe.

**Ação:** Extrair todo o conteúdo do bloco `<script>` inline para `static/js/base.js` e substituir o bloco por:
```html
<script src="{{ url_for('static', filename='js/base.js') }}"></script>
```
posicionado no final do `<body>` de `base.html`.

**Verificação:** DevTools → Console → ausência de erros `Refused to execute inline script`.

---

### 1.2 — Tornar o app incapaz de subir em produção sem `SECRET_KEY`

O fallback `"dev-secret-key-mude-em-producao"` está no código fonte commitado (`app.py` linhas 30–41). Se a env var `SECRET_KEY` não estiver configurada na plataforma, o app sobe silenciosamente com uma chave pública e conhecida, permitindo **forjamento de cookies de sessão**.

**Ação:** Substituir o bloco de fallback por:
```python
if not _secret or _secret == "troque-por-uma-chave-segura-em-producao":
    if _is_production:
        print(
            "ERRO: SECRET_KEY não definido ou usa valor padrão inválido.\n"
            "  Defina SECRET_KEY como variável de ambiente antes de iniciar em produção.\n"
            "  Gere com: python -c 'import secrets; print(secrets.token_hex(32))'",
            file=sys.stderr,
        )
        sys.exit(1)  # ← impede o app de subir
    _secret = "dev-secret-key-mude-em-producao"
```

O fallback continua existindo para ambiente de desenvolvimento local, mas **produção (FLASK_DEBUG não setado) recusa subir** sem uma chave válida.

**Verificação:** Iniciar app sem `SECRET_KEY` na env e sem `FLASK_DEBUG=1` → deve abortar com mensagem de erro clara.

---

## Bloco 2 — Alto

### 2.1 — Atualizar Flask 2.3.3 → 3.x e Werkzeug 2.3.7 → 3.x

`flask==2.3.3` e `Werkzeug==2.3.7` são de agosto de 2023 e estão **fora de suporte de segurança ativo**. Qualquer CVE contra Flask/Werkzeug 2.x após outubro de 2023 está sem patch.

**Ação:**
1. No `requirements.txt`, trocar os pins:
   ```
   flask==3.1.0
   Werkzeug==3.1.3
   ```
2. Verificar se algum trecho de `app.py` usa APIs removidas no Flask 3.x (`before_first_request`, `flask.ext`, etc.).
3. Rodar `pytest tests.py -v` — deve passar 100%.

### 2.2 — Fixar todos os pins em `requirements.txt`

Cinco pacotes usam `>=` sem upper bound (`python-dotenv`, `gunicorn`, `brotli`, `Flask-Compress`, `Flask-Limiter`, `Flask-WTF`). Um `pip install` futuro em um deploy limpo pode instalar uma versão major com breaking changes.

**Ação:** Após concluir o item 2.1, em um venv limpo:
```bash
pip install -r requirements.txt
pip freeze > requirements.txt
```
Isso captura versões exatas de todos os pacotes (incluindo transitivos), tornando os builds **reproduzíveis**.

### 2.3 — Implementar cache-busting para assets estáticos

`Cache-Control: max-age=31536000, immutable` sem fingerprinting de arquivos significa que usuários com cache quente continuarão vendo `custom.css`, `galeria.js` e outros assets **antigos por até 1 ano** após qualquer redeploy que os modifique. O `PLANO_DEPLOY.md` menciona cache-busting via `url_for('static', ...)` — isso não é mais automático no Flask 2.x/3.x.

**Ação:** Adicionar um filtro Jinja2 `versioned_url` no context processor de `app.py`:
```python
import hashlib

_asset_hashes: dict[str, str] = {}

def _get_asset_hash(filename: str) -> str:
    if filename not in _asset_hashes:
        filepath = Path(__file__).parent / "static" / filename
        try:
            digest = hashlib.md5(filepath.read_bytes()).hexdigest()[:8]
        except FileNotFoundError:
            digest = "0"
        _asset_hashes[filename] = digest
    return _asset_hashes[filename]

@app.context_processor
def inject_globals():
    # ... globals existentes ...
    def versioned_url(filename):
        return url_for("static", filename=filename) + "?v=" + _get_asset_hash(filename)
    return dict(..., versioned_url=versioned_url)
```
Substituir chamadas de `url_for('static', filename=...)` nos templates por `versioned_url(...)` para `custom.css`, `galeria.js`, `quiz.js`.

**Verificação:** DevTools → Network → confirmar que `custom.css?v=<hash>` muda de hash após editar o arquivo.

---

## Bloco 3 — Médio: Robustez e Edge Cases

### 3.1 — Corrigir caminhos CWD-relativos

`app.py` usa `Path("static/imagens")` e `"icdas.db"` como caminhos relativos ao diretório de trabalho atual. Se gunicorn for iniciado de um diretório diferente da raiz do projeto (comum em containers onde o CWD é `/`), o gallery, o quiz e o banco de dados **falham silenciosamente**.

**Ações em `app.py`:**

- Linha com `Path("static/imagens")`:
  ```python
  pasta = Path(__file__).parent / "static" / "imagens"
  ```
- Linha com `DB_PATH`:
  ```python
  DB_PATH = os.environ.get("DB_PATH", str(Path(__file__).parent / "icdas.db"))
  ```

### 3.2 — Reduzir tamanho do payload de sessão do quiz

`quiz_fila` armazena **nomes completos de arquivo** (ex: `"ICDAS 1a.webp"`) no cookie de sessão Flask (client-side, limite ~4 KB). Com crescimento da biblioteca de imagens, o cookie pode silenciosamente transbordar — Flask descarta a modificação sem avisar o usuário, causando reset de fila e perda de score no meio do quiz.

**Ação:** Substituir nomes de arquivo por **índices inteiros** (posição na lista retornada por `get_imagens()`):
```python
# Ao montar a fila:
imagens = get_imagens()
fila_indices = list(range(len(imagens)))
random.shuffle(fila_indices)
session["quiz_fila"] = fila_indices  # [2, 7, 0, 5, ...] em vez de ["ICDAS 2.webp", ...]

# Ao consumir:
def _quiz_pop(session):
    fila = session.get("quiz_fila", [])
    if not fila:
        return None
    idx = fila.pop(0)
    imagens = get_imagens()
    return imagens[idx] if idx < len(imagens) else None
```
Reduz de ~15 bytes/item para 1–3 bytes/item. Adicionar também um warning de log se o cookie ultrapassar 3 KB.

### 3.3 — Confirmar que apenas `.webp` existe em `static/imagens/` na produção

As imagens `.png` são arquivos legados que permanecem apenas localmente e **não devem ir para produção**. A função `get_imagens()` retorna todos os arquivos que batem com o regex — se `.png` e `.webp` do mesmo assunto estiverem presentes, a mesma foto clínica aparecerá **duas vezes no quiz** como itens separados.

**Ações:**
1. Adicionar `.png` ao `.gitignore` dentro de `static/imagens/` para garantir que arquivos PNG nunca sejam commitados:
   ```gitignore
   # static/imagens/.gitignore
   *.png
   ```
2. Verificar via `git status` que nenhum `.png` está atualmente rastreado no repositório. Se estiverem: `git rm --cached static/imagens/*.png`.
3. Como defesa-em-profundidade, restringir `IMAGEM_EXTENSOES` em `get_imagens()` para aceitar **apenas `.webp`**:
   ```python
   IMAGEM_EXTENSOES = {".webp"}
   ```

**Verificação:** Abrir o quiz e confirmar que cada ICDAS aparece uma única vez por código.

### 3.4 — Adicionar handler HTTP 400

Falhas de validação CSRF retornam HTTP 400 com a **resposta padrão do Flask-WTF** — sem os headers de segurança adicionados pelo `after_request` hook, sem template do app, potencialmente expondo informação de versão no header `Server`.

**Ação:** Adicionar ao `app.py` junto dos outros error handlers:
```python
@app.errorhandler(400)
def bad_request(e):
    return render_template("400.html"), 400
```
Criar `templates/400.html` com estrutura análoga ao `templates/404.html`, com mensagem: `"Requisição inválida. Por favor, volte e tente novamente."`. O header CSRF será revalidado na próxima submissão normal do formulário.

### 3.5 — Capturar `OperationalError` em `quiz_finalizar`

A rota `/quiz/finalizar` (POST) abre uma conexão SQLite, insere um registro de score e fecha. Sob carga concorrente com 2 workers, contention de lock SQLite pode elevar `OperationalError: database is locked` — que sobe sem tratamento até o handler de 500. O usuário perde o score após completar o quiz.

**Ação:** Envolver o bloco de INSERT com retry simples:
```python
import time

for tentativa in range(3):
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO scores (nome, acertos, total, percentual, data) VALUES (?,?,?,?,?)",
                (nome, acertos, total, percentual, datetime.now().isoformat()),
            )
        break
    except sqlite3.OperationalError as e:
        if tentativa == 2:
            raise
        time.sleep(0.1)
```

### 3.6 — Guard de divisão por zero em `templates/scores.html`

A linha `{{ (s["acertos"] / s["total"] * 100) | round | int }}` levanta `ZeroDivisionError` se `total=0` (possível via inserção manual no DB, migration, ou fixture de teste). A página `/scores` crasha com 500.

**Ação em `scores.html`:**
```jinja
{% if s["total"] > 0 %}
  {{ (s["acertos"] / s["total"] * 100) | round | int }}%
{% else %}
  —
{% endif %}
```

### 3.7 — Adicionar header `Retry-After` nas respostas 429

O handler `@app.errorhandler(429)` não inclui o header `Retry-After`. Clientes bem-comportados (crawlers, bibliotecas HTTP, fetch com retry) não sabem quando podem tentar novamente, resultando em tempestades de retry que continuam recebendo 429 e aumentando a pressão.

**Ação em `app.py`:**
```python
@app.errorhandler(429)
def too_many_requests(e):
    response = make_response(render_template("429.html"), 429)
    response.headers["Retry-After"] = "60"
    return response
```

---

## Bloco 4 — Deploy e Infraestrutura

### 4.1 — Verificar e completar o `.gitignore`

Garantir que o `.gitignore` da raiz cubra os seguintes padrões (sem incluir `icdas.db`, que contém apenas scores e é conveniente manter no repositório):

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/

# Ambiente virtual
.venv/
venv/
env/

# Variáveis de ambiente (segredos)
.env
.env.local

# SQLite WAL (artefatos temporários de transação — não o .db principal)
*.db-wal
*.db-shm

# Imagens legadas (apenas WebP vai para produção)
static/imagens/*.png
```

**Verificar:** `git status` não deve mostrar `__pycache__/`, `.env` ou arquivos `*.db-wal` como não-rastreados ou modificados.

### 4.2 — Adicionar endpoint `/health`

DigitalOcean App Platform usa health checks HTTP. Atualmente, o probe padrão bate em `GET /` que renderiza um template Jinja2 completo, executa o context processor e carrega `DESCRICOES` — overhead desnecessário para uma simples verificação de liveness.

**Ação em `app.py`:**
```python
from flask import jsonify

@app.get("/health")
@limiter.exempt
def health():
    db_ok = False
    try:
        with get_db() as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass
    status = "ok" if db_ok else "degraded"
    return jsonify({"status": status, "db": db_ok}), 200 if db_ok else 503
```
Configurar `/health` como o endpoint de health check na plataforma.

**Verificação:** `GET /health` → `200 {"status": "ok", "db": true}`.

### 4.3 — HSTS com diretiva `preload`

O header HSTS atual é `max-age=31536000; includeSubDomains`. Sem `preload`, visitantes pela primeira vez ou após limpar o cache HSTS não são protegidos contra SSLStrip até a primeira visita bem-sucedida.

**Ação em `app.py`:**
```python
response.headers["Strict-Transport-Security"] = (
    "max-age=31536000; includeSubDomains; preload"
)
```
Quando o domínio estiver estável em produção, submeter à [HSTS Preload List](https://hstspreload.org/).

### 4.4 — Ativar `session.permanent` onde o quiz é iniciado

`PERMANENT_SESSION_LIFETIME = timedelta(hours=4)` está configurado mas **não tem efeito** porque `session.permanent` nunca é definido como `True` em nenhuma rota. A sessão expira ao fechar o browser, independente da config.

**Ação:** Na rota `quiz_modo` (onde a sessão de quiz é inicializada), adicionar:
```python
session.permanent = True
```
Isso aplica o lifetime de 4h, mantendo o estado do quiz caso o usuário feche e reabra o browser dentro desse período.

Se o comportamento desejado for **sessão temporária** (reinicia ao fechar o browser), remover `PERMANENT_SESSION_LIFETIME` do config para evitar confusão de manutenção.

### 4.5 — Workers dinâmicos no Procfile

O número de workers `--workers 2` está hardcoded. Se o plano da DigitalOcean for upgradeado para uma instância maior, o processo de ajuste é manual.

**Ação no `Procfile`:**
```
web: gunicorn app:app --workers ${WEB_CONCURRENCY:-2} --preload --timeout 30 --bind 0.0.0.0:$PORT
```
Assim a plataforma pode injetar `WEB_CONCURRENCY` automaticamente baseado nos recursos disponíveis.

---

## Bloco 5 — Baixo / Qualidade

| # | Arquivo | Achado | Ação |
|---|---------|--------|------|
| Q-01 | `app.py` (linha ~31) | `_is_production = FLASK_DEBUG == "0"` — ativo quando a variável está **ausente**, comportamento contra-intuitivo | Adicionar comentário explicativo ou renomear para `_is_dev_mode = FLASK_DEBUG == "1"` e inverter os `if` |
| Q-02 | `tools/convert_images.py` (linha 14) | `QUALIDADE = 90` no script vs. `82` documentado no `PLANO_DEPLOY.md` | Alinhar para um valor único; atualizar ambos os arquivos |
| Q-03 | `app.py` (função `get_imagens`) | `pasta.iterdir()` chamado duas vezes por cache miss — TOCTOU window e chamada de syscall duplicada | Materializar em lista uma única vez: `arquivos = list(pasta.iterdir())` e reusar |
| Q-04 | `app.py` (linha ~62) | `logging.basicConfig(level=logging.INFO)` sem formato estruturado; logs difíceis de parsear na plataforma | Adicionar `format='%(asctime)s %(levelname)s %(name)s: %(message)s'` |
| Q-05 | `requirements.txt` | `Pillow` ausente — usado por `tools/convert_images.py`, silenciosamente ausente no ambiente de produção | Adicionar linha comentada: `# Pillow>=10.0  # ferramenta dev (tools/convert_images.py)` |

---

## Checklist de Verificação Final

Antes de marcar o deploy como pronto, verificar cada item abaixo:

- [ ] `pytest tests.py -v` — 100% de aprovação
- [ ] DevTools → Console → sem erros `Refused to execute inline script` (valida item 1.1)
- [ ] Iniciar app sem `SECRET_KEY` na env e sem `FLASK_DEBUG=1` → app recusa subir com mensagem de erro (valida item 1.2)
- [ ] DevTools → Application → Cookies → medir tamanho do cookie de sessão após quiz com 10+ questões (valida item 3.2)
- [ ] `git ls-files static/imagens/` → retorna apenas arquivos `.webp`, nenhum `.png` (valida item 3.3)
- [ ] Cada código ICDAS aparece uma única vez no quiz (valida item 3.3)
- [ ] `GET /health` → `200 {"status": "ok", "db": true}` (valida item 4.2)
- [ ] DevTools → Network → `custom.css?v=<hash>` — hash muda após editar o arquivo (valida item 2.3)
- [ ] `git status` não mostra `__pycache__/`, `.env`, `*.db-wal` ou `*.png` de imagens (valida item 4.1)
- [ ] `GET /quiz` (via browser), F5 após resposta inválida → não duplica submissão (valida item S-06, não crítico mas observar)
