# Copilot Instructions — ICDAS Educacional

## Project Overview

Educational Flask web app for learning the ICDAS dental caries classification system (codes 0–6). TCC (bachelor's thesis) for Odontology at UFJF-GV. All user-facing text **and code comments** must be in **Brazilian Portuguese**.

## Architecture

Flask monolith: `app.py` contains routes, quiz/session logic, helpers, and security config. Database models/repository live in `database.py`; schema migrations live in `migrations/`.

| Layer | Detail |
|---|---|
| Templates | Jinja2 in `templates/`, inheriting `base.html`. Use `_macros.html` for shared components. |
| Static assets | `static/css/tailwind.css` (Tailwind compilado) + CSS local, `static/js/` (vanilla JS only), `static/imagens/` (`.webp` only) |
| Database | SQLAlchemy 2 + Alembic; SQLite embedded for standalone/local and PostgreSQL for server deployments |
| Config | `descricoes.json` — ICDAS clinical descriptions keyed by **string** (`"0"`–`"6"`), loaded at startup into `DESCRICOES` |

## Critical Patterns

**Production detection:** `FLASK_DEBUG=0` (or absent) = production. Missing/default `SECRET_KEY` crashes the app on startup intentionally — this is by design.

**DB access:** Use the functions/models in `database.py`; do not open application databases with raw `sqlite3` in production code. Schema changes require an Alembic revision. SQLite-specific PRAGMAs stay isolated in the SQLAlchemy engine setup.

**Quiz state** is fully session-based (no DB during play): `quiz_fila` (queue), `quiz_atual` (current image ID), `quiz_feedback` (PRG payload), `score_acertos`, `score_total`. The quiz uses Post/Redirect/Get to make F5 safe.

**Image cache:** `get_imagens()` caches by `(mtime, file_count)` of `static/imagens/`. Only `.webp` files are served; files matching `"logo-ufjf-gv"` are excluded. ICDAS code is parsed from the filename via `re.search(r'ICDAS\s*(\d+)', nome)`.

**Asset versioning:** Use `versioned_url('css/custom.css')` (a Jinja2 context processor) — never hardcode `url_for('static', ...)` for CSS/JS in templates. Hashes are MD5-precomputed at startup.

**Rate limiting:** POST `/quiz` = 60/min, POST `/quiz/modo` = 20/min, `/scores` = 30/min, `/health` is exempt. Produção usa `CF-Connecting-IP` validado como chave; não reintroduza confiança direta em `X-Forwarded-For`/`ProxyFix`. Tests use `RATELIMIT_ENABLED = False` on the default `client` fixture.

**Security headers** are applied in `set_security_headers()` (`@app.after_request`). The CSP allows only `'self'`. Do not add inline scripts or external CDN resources without updating the CSP string.

**Production data:** production uses PostgreSQL; local `icdas.db` files are runtime/state data and must never be committed. The legacy `ip` column remains only for schema compatibility and is scrubbed to an empty string; `ip_hash` is the only technical client identifier retained.

## Developer Workflows

```bash
# Run locally (development)
$env:FLASK_DEBUG="1"; $env:SECRET_KEY="any-local-key"; python app.py

# Run tests (isolated SQLite per test via tmp_path)
python -m pytest tests.py -v

# Run tests with short tracebacks
python -m pytest tests.py -v --tb=short

# Production process (the Zezin Dockerfile is authoritative)
gunicorn --worker-tmp-dir /dev/shm --worker-class gthread --workers 1 --threads 4 --timeout 30 --graceful-timeout 30 --no-control-socket --bind 0.0.0.0:$PORT app:app
```

**Environment variables** (`.env` locally; secrets/state are supplied by the Zezin deployment in production):
- `SECRET_KEY` — required in production; app crashes on startup if missing or default
- `FLASK_DEBUG` — `1` for dev, `0` (or absent) for production
- `DATABASE_URL` — optional SQLAlchemy URL; highest-priority backend selector
- `DB_PATH` — SQLite path when no server backend is configured (default: `icdas.db`)
- `POSTGRES_HOST`/`POSTGRES_PORT`/`POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD` — optional PostgreSQL components when `DATABASE_URL` is empty

**Production ownership:** this repository owns application code only. On the Zezin server, deployment/network/state/backup/rollback are owned by `/srv/zezin/services/icdasquiz`. Do not add a second Traefik/Cloudflare/backup control plane here.

## Test Fixtures

Three fixtures in `tests.py`:
- `client` — CSRF disabled, rate limiting disabled (standard use)
- `csrf_client` — CSRF enabled (test token validation)
- `rate_client` — rate limiting enabled (test throttling)

Each test gets an isolated SQLite DB via `_setup_db(tmp_path)` (autouse). Set `os.environ["FLASK_DEBUG"] = "0"` and `SECRET_KEY` **before** importing `app` — `tests.py` already does this at module level.

## Adding Features

- **New route:** Add to `app.py`; add corresponding tests in `tests.py` under an appropriate `class Test*`.
- **New template:** Extend `base.html`; use `versioned_url()` for any new static asset.
- **New images:** Convert to `.webp` with `tools/convert_images.py` (requires Pillow); drop into `static/imagens/` following the naming pattern `*ICDAS N*`.
- **New ICDAS descriptions:** Edit `descricoes.json` — keys must be strings (`"0"`–`"6"`).
