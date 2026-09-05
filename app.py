import hashlib
import hmac
import ipaddress
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask, jsonify, make_response, render_template, request,
    redirect, url_for, session, send_from_directory,
)
from flask_compress import Compress
from flask_limiter import Limiter
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.exc import OperationalError
from werkzeug.exceptions import SecurityError

from database import (
    clear_legacy_ips,
    database_healthy,
    latest_name_for_ip_hash,
    recent_scores,
    reset_engine,
    save_score,
    upgrade_schema,
    valid_scores,
)

load_dotenv()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
Compress(app)

_secret = os.environ.get("SECRET_KEY", "")
# True quando FLASK_DEBUG não está definido (padrão) ou é "0".
# Ausência da variável é intencionalmente tratada como produção.
_is_production = os.environ.get("FLASK_DEBUG", "0") == "0"

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

app.secret_key = _secret
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Habilita Secure flag apenas fora do modo debug (HTTPS em produção)
app.config["SESSION_COOKIE_SECURE"] = _is_production
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=4)
app.config["WTF_CSRF_TIME_LIMIT"] = 3600  # token válido por 1h
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024  # 32 KB — formulários do quiz
if _is_production:
    app.config["TRUSTED_HOSTS"] = [
        "icdasquiz.tech",
        "www.icdasquiz.tech",
        "localhost",
        "127.0.0.1",
    ]

csrf = CSRFProtect(app)


def _client_ip():
    """Retorna o IP original informado pela borda Cloudflare.

    Produção só recebe tráfego público pelo Cloudflare Tunnel -> Traefik.
    O header específico da Cloudflare evita depender da contagem variável de
    hops de X-Forwarded-For. Em desenvolvimento/testes, usa remote_addr.
    """
    forwarded = (request.headers.get("CF-Connecting-IP") or "").strip()
    if forwarded:
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return (request.remote_addr or "").strip()


limiter = Limiter(
    app=app,
    key_func=_client_ip,
    storage_uri="memory://",
    default_limits=["200 per minute"],
)

DB_PATH = os.environ.get("DB_PATH", str(Path(__file__).parent / "icdas.db"))
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Carrega descrições clínicas do JSON
DESCRICOES_PATH = Path(__file__).parent / "descricoes.json"
try:
    with open(DESCRICOES_PATH, encoding="utf-8") as f:
        DESCRICOES = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as exc:
    logger.warning("descricoes.json não encontrado ou inválido: %s", exc)
    DESCRICOES = {}


# ---------------------------------------------------------------------------
# Banco de dados — SQLAlchemy + Alembic
# ---------------------------------------------------------------------------

def _db_options():
    """Retorna a configuração atual do backend.

    DATABASE_URL seleciona PostgreSQL (ou outro dialeto SQLAlchemy). Sem ela,
    DB_PATH mantém o modo SQLite embedded e portátil.
    """
    return {"database_url": DATABASE_URL or None, "db_path": DB_PATH}


def init_db():
    """Aplica migrations Alembic e invariantes de privacidade."""
    reset_engine()
    upgrade_schema(**_db_options())
    clear_legacy_ips(**_db_options())


# Inicializa/migra o banco ao carregar o módulo (funciona com Gunicorn preload).
init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

IMAGEM_EXTENSOES = {".webp"}

# Cache simples para get_imagens(): (pasta_mtime, contagem, resultado)
_imagens_cache: tuple = (None, None, [])


def get_imagens():
    """Retorna lista de imagens ICDAS. Resultado é cacheado por mtime."""
    global _imagens_cache
    pasta = Path(__file__).parent / "static" / "imagens"
    try:
        if not pasta.exists():
            return []
        stat = pasta.stat()
        mtime = stat.st_mtime
        arquivos = sorted(pasta.iterdir(), key=lambda p: p.name)
        count = len(arquivos)
        cached_mtime, cached_count, cached = _imagens_cache
        if mtime == cached_mtime and count == cached_count:
            return list(cached)
        imagens = []
        for arquivo in arquivos:
            if (arquivo.suffix.lower() in IMAGEM_EXTENSOES
                    and "logo-ufjf-gv" not in arquivo.name):
                nome = arquivo.stem
                caminho = f"imagens/{arquivo.name}"
                match = re.search(r'ICDAS\s*(\d+)', nome)
                icdas_code = int(match.group(1)) if match else None
                if icdas_code is not None:
                    imagens.append({
                        "id": len(imagens),
                        "nome": nome,
                        "caminho": caminho,
                        "icdas_code": icdas_code,
                    })
        _imagens_cache = (mtime, count, imagens)
        return list(imagens)
    except OSError as exc:
        logger.error("Erro ao ler pasta de imagens: %s", exc)
        return []


def _safe_int(value, default=-1):
    """Converte valor para int de forma segura."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _hash_ip(ip):
    """Gera identificador estável de IP sem gravar o IP bruto."""
    if not ip:
        return ""
    secret = str(app.secret_key or "").encode("utf-8")
    return hmac.new(secret, ip.encode("utf-8"), hashlib.sha256).hexdigest()


def _ultimo_nome_por_ip_hash(ip_hash):
    """Busca o último nome usado pelo mesmo identificador técnico."""
    return latest_name_for_ip_hash(ip_hash, **_db_options())


def _imagens_destaque_home(imagens, limite=6):
    """Seleciona exemplos variados para a landing page."""
    selecionadas = []
    vistos = set()
    for codigo in (0, 1, 2, 3, 4, 5, 6):
        imagem = next(
            (
                img for img in imagens
                if img["icdas_code"] == codigo and img["id"] not in vistos
            ),
            None,
        )
        if imagem is not None:
            item = dict(imagem)
            item["legenda_condicao"] = _legenda_condicao_imagem(item["nome"])
            selecionadas.append(item)
            vistos.add(item["id"])
        if len(selecionadas) >= limite:
            break
    return selecionadas


def _legenda_condicao_imagem(nome):
    """Deriva legenda simples de condição clínica pelo nome do arquivo."""
    nome_normalizado = nome.lower()
    if "molhad" in nome_normalizado or "umid" in nome_normalizado:
        return "Foto em campo molhado/úmido"
    if "seco" in nome_normalizado:
        return "Foto em campo seco"
    return ""


# ---------------------------------------------------------------------------
# Context processor — injeta `now` em todos os templates automaticamente
# ---------------------------------------------------------------------------

# O footer usa apenas `now.year`. Precomputar evita datetime.now() em
# cada request — o ano não muda durante a vida do servidor.
_STARTUP_YEAR = datetime.now().year


class _FakeNow:
    """Objeto mínimo que expõe .year sem instanciar datetime por request."""
    year = _STARTUP_YEAR


_NOW = _FakeNow()


_asset_hashes: dict[str, str] = {}


def _get_asset_hash(filename: str) -> str:
    """Calcula e cacheia o hash MD5 (8 chars) de um asset estático."""
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
    def versioned_url(filename):
        """Retorna URL do asset com query string de cache-busting."""
        return url_for("static", filename=filename) + "?v=" + _get_asset_hash(filename)

    return {"now": _NOW, "versioned_url": versioned_url}


# Pré-aquece o cache de hashes na inicialização do processo (--preload safe).
for _f in (
    "css/custom.css",
    "css/ui.css",
    "css/landing.css",
    "css/tailwind.css",
    "js/base.js",
    "js/landing.js",
    "js/galeria.js",
    "js/quiz.js",
):
    _get_asset_hash(_f)


# ---------------------------------------------------------------------------
# Segurança — headers para produção
# ---------------------------------------------------------------------------

# CSP: permite apenas recursos do próprio servidor
_CSP = (
    "default-src 'self'; "
    "style-src 'self'; "
    "font-src 'self'; "
    "script-src 'self'; "
    "img-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)


@app.after_request
def set_security_headers(response):
    response.headers["Content-Security-Policy"] = _CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    if _is_production:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
    # Cache de assets estáticos (Bloco 7)
    if request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        response.headers["Cache-Control"] = "no-store"
    return response


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    imagens = get_imagens()
    return render_template(
        "index.html",
        descricoes=DESCRICOES,
        imagens_destaque=_imagens_destaque_home(imagens),
        total_imagens=len(imagens),
    )


@app.route("/galeria")
def galeria():
    imagens = get_imagens()
    imagens.sort(
        key=lambda x: (x["icdas_code"] if x["icdas_code"] is not None else 99)
    )
    contagem_codigos = {
        codigo: sum(1 for imagem in imagens if imagem["icdas_code"] == codigo)
        for codigo in range(7)
    }
    return render_template(
        "galeria.html",
        imagens=imagens,
        descricoes=DESCRICOES,
        contagem_codigos=contagem_codigos,
    )


@app.route("/quiz", methods=["GET", "POST"])
@limiter.limit("60 per minute", methods=["POST"])
def quiz():
    imagens = get_imagens()

    session.permanent = True
    session.setdefault("score_acertos", 0)
    session.setdefault("score_total", 0)

    if not imagens:
        return render_template(
            "quiz.html",
            imagem=None,
            mensagem="Nenhuma imagem disponível para o quiz.",
            correto=None,
            descricao_codigo=None,
            respondido=False,
            score_acertos=0,
            score_total=0,
            modo_sequencial=False,
        )

    if not session.get("quiz_nome"):
        if request.method == "POST":
            return redirect(url_for("quiz"))
        ip_hash = _hash_ip(_client_ip())
        return render_template(
            "quiz.html",
            imagem=None,
            mensagem=None,
            correto=None,
            descricao_codigo=None,
            respondido=False,
            score_acertos=session.get("score_acertos", 0),
            score_total=session.get("score_total", 0),
            modo_sequencial=session.get("quiz_modo") == "sequencial",
            pedir_nome=True,
            nome_sugerido=_ultimo_nome_por_ip_hash(ip_hash),
            quiz_nome=None,
        )

    modo_seq = session.get("quiz_modo") == "sequencial"

    if request.method == "POST":
        imagem_id = _safe_int(request.form.get("imagem_id"), -1)
        resposta = _safe_int(request.form.get("resposta"), -1)
        imagem = next(
            (img for img in imagens if img["id"] == imagem_id), None
        )

        if imagem is None:
            return redirect(url_for("quiz"))

        if resposta < 0 or resposta > 6:
            return render_template(
                "quiz.html",
                imagem=imagem,
                mensagem="Selecione uma opção antes de verificar.",
                correto=None,
                descricao_codigo=None,
                respondido=False,
                score_acertos=session["score_acertos"],
                score_total=session["score_total"],
                modo_sequencial=modo_seq,
                quiz_nome=session.get("quiz_nome"),
            )

        session["score_total"] += 1
        if resposta == imagem["icdas_code"]:
            correto = True
            session["score_acertos"] += 1
            mensagem = (
                f"Correto! Esta imagem mostra ICDAS {imagem['icdas_code']}."
            )
        else:
            correto = False
            mensagem = (
                f"Incorreto. A resposta correta é ICDAS "
                f"{imagem['icdas_code']}."
            )
        session.modified = True

        # Avança: limpa a imagem atual → próximo GET carrega a seguinte
        session.pop("quiz_atual", None)
        # Fila vazia após limpar o atual → todas as imagens respondidas
        quiz_completo = session.get("quiz_fila") == []

        # PRG — armazena feedback na sessão e redireciona;
        # F5 na página de feedback é um GET inofensivo.
        session["quiz_feedback"] = {
            "imagem_id": imagem["id"],
            "correto": correto,
            "mensagem": mensagem,
            "descricao_key": str(imagem["icdas_code"]),
            "quiz_completo": quiz_completo,
        }
        session.modified = True
        return redirect(url_for("quiz"))

    # GET — 1) feedback pendente do POST anterior (PRG, F5-safe)
    feedback = session.pop("quiz_feedback", None)
    if feedback is not None:
        imagem = next(
            (img for img in imagens if img["id"] == feedback["imagem_id"]),
            None,
        )
        if imagem is not None:
            return render_template(
                "quiz.html",
                imagem=imagem,
                mensagem=feedback["mensagem"],
                correto=feedback["correto"],
                descricao_codigo=DESCRICOES.get(feedback["descricao_key"]),
                respondido=True,
                score_acertos=session.get("score_acertos", 0),
                score_total=session.get("score_total", 0),
                modo_sequencial=modo_seq,
                quiz_completo=feedback["quiz_completo"],
                quiz_nome=session.get("quiz_nome"),
            )

    # GET — 2) imagem atual (recarregar página sem reenviar)
    valid_ids = {img["id"] for img in imagens}
    atual_id = session.get("quiz_atual")
    if atual_id is not None and atual_id in valid_ids:
        imagem = next(img for img in imagens if img["id"] == atual_id)
    else:
        imagem = _quiz_pop(imagens)
        if imagem is None:
            return render_template(
                "quiz.html",
                imagem=None,
                mensagem=None,
                correto=None,
                descricao_codigo=None,
                respondido=False,
                score_acertos=session.get("score_acertos", 0),
                score_total=session.get("score_total", 0),
                modo_sequencial=modo_seq,
                quiz_completo=True,
                quiz_nome=session.get("quiz_nome"),
            )
        session["quiz_atual"] = imagem["id"]
        session.modified = True

    return render_template(
        "quiz.html",
        imagem=imagem,
        mensagem=None,
        correto=None,
        descricao_codigo=None,
        respondido=False,
        score_acertos=session.get("score_acertos", 0),
        score_total=session.get("score_total", 0),
        modo_sequencial=modo_seq,
        quiz_completo=False,
        quiz_nome=session.get("quiz_nome"),
    )


@app.route("/quiz/iniciar", methods=["POST"])
@limiter.limit("20 per minute")
def quiz_iniciar():
    """Identifica o aluno antes de iniciar o quiz."""
    session.permanent = True
    nome = request.form.get("nome", "").strip()[:100]
    if not nome:
        ip_hash = _hash_ip(_client_ip())
        return render_template(
            "quiz.html",
            imagem=None,
            mensagem="Informe seu nome para começar.",
            correto=None,
            descricao_codigo=None,
            respondido=False,
            score_acertos=session.get("score_acertos", 0),
            score_total=session.get("score_total", 0),
            modo_sequencial=session.get("quiz_modo") == "sequencial",
            pedir_nome=True,
            nome_sugerido=_ultimo_nome_por_ip_hash(ip_hash),
            quiz_nome=None,
        ), 400

    session["quiz_nome"] = nome
    session["score_acertos"] = 0
    session["score_total"] = 0
    session["quiz_fila"] = None
    session.pop("quiz_atual", None)
    session.pop("quiz_feedback", None)
    session.modified = True
    return redirect(url_for("quiz"))


def _quiz_pop(imagens):
    """Retorna a próxima imagem da fila, inicializando-a se necessário.

    Fila (quiz_fila) na sessão:
    - None : não inicializada → cria agora com todos os IDs
    - []   : esgotada → quiz completo, retorna None
    - [...]: pop do início e retorna a imagem

    Modo aleatório : IDs embaralhados com random.shuffle.
    Modo sequencial: IDs ordenados pelo código ICDAS crescente.
    """
    valid_ids = {img["id"] for img in imagens}
    fila = session.get("quiz_fila")

    if fila is None:
        if session.get("quiz_modo") == "sequencial":
            fila = [
                img["id"]
                for img in sorted(
                    imagens,
                    key=lambda x: x["icdas_code"] if x["icdas_code"]
                    is not None else 99,
                )
            ]
        else:
            fila = [img["id"] for img in imagens]
            random.shuffle(fila)

    # Remove IDs que não existem mais (proteção se imagens forem removidas)
    fila = [iid for iid in fila if iid in valid_ids]

    if not fila:
        session["quiz_fila"] = []
        session.modified = True
        return None

    next_id, *fila = fila
    session["quiz_fila"] = fila
    session.modified = True
    return next((img for img in imagens if img["id"] == next_id), None)


@app.route("/quiz/modo", methods=["POST"])
@limiter.limit("20 per minute")
def quiz_modo():
    """Alterna entre modo aleatório e sequencial e reinicia a fila."""
    session.permanent = True
    modo = request.form.get("modo", "aleatorio")
    session["quiz_modo"] = modo if modo == "sequencial" else "aleatorio"
    session["quiz_fila"] = None
    session.pop("quiz_atual", None)
    session.pop("quiz_feedback", None)
    session["score_acertos"] = 0
    session["score_total"] = 0
    session.modified = True
    return redirect(url_for("quiz"))


@app.route("/quiz/finalizar", methods=["POST"])
@limiter.limit("10 per minute")
def quiz_finalizar():
    """Salva a sessão no banco e reseta o placar."""
    acertos = max(0, session.get("score_acertos", 0))
    total = max(0, session.get("score_total", 0))
    acertos = min(acertos, total)

    nome = (
        session.get("quiz_nome")
        or request.form.get("nome", "").strip()[:100]
        or "Anônimo"
    )

    ip_real = _client_ip()
    ip_hash = _hash_ip(ip_real)

    if total > 0:
        for tentativa in range(3):
            try:
                save_score(
                    data=datetime.now().strftime("%Y-%m-%d %H:%M"),
                    total=total,
                    acertos=acertos,
                    nome=nome,
                    ip_hash=ip_hash,
                    **_db_options(),
                )
                break
            except OperationalError as exc:
                # SQLite pode serializar writes muito próximos. PostgreSQL e
                # outros backends devem propagar seus próprios erros.
                if (
                    "locked" not in str(exc).lower()
                    or DATABASE_URL
                    or tentativa == 2
                ):
                    raise
                time.sleep(0.1)
    session["score_acertos"] = 0
    session["score_total"] = 0
    session["quiz_fila"] = None
    session.pop("quiz_atual", None)
    session.pop("quiz_feedback", None)
    session.modified = True
    return redirect(url_for("scores"))


@app.route("/quiz/resetar", methods=["POST"])
@limiter.limit("20 per minute")
def quiz_resetar():
    """Reseta a fila e o placar sem salvar."""
    session["score_acertos"] = 0
    session["score_total"] = 0
    session["quiz_fila"] = None
    session.pop("quiz_atual", None)
    session.pop("quiz_feedback", None)
    session.modified = True
    return redirect(url_for("quiz"))


@app.route("/scores")
@limiter.limit("30 per minute")
def scores():
    historico = recent_scores(limit=20, **_db_options())
    tentativas_validas = valid_scores(**_db_options())

    ranking_por_aluno = {}
    for tentativa in tentativas_validas:
        nome = (tentativa.nome or "Anônimo").strip() or "Anônimo"
        chave = nome.casefold()
        pct = round(tentativa.acertos / tentativa.total * 100)
        item = ranking_por_aluno.setdefault(
            chave,
            {
                "nome": nome,
                "tentativas": 0,
                "melhor": None,
                "pior": None,
                "ultima_data": tentativa.data,
            },
        )
        item["tentativas"] += 1
        candidato = {
            "pct": pct,
            "acertos": tentativa.acertos,
            "total": tentativa.total,
            "data": tentativa.data,
            "id": tentativa.id,
        }
        if (
            item["melhor"] is None
            or (pct, tentativa.acertos, tentativa.id)
            > (item["melhor"]["pct"], item["melhor"]["acertos"], item["melhor"]["id"])
        ):
            item["melhor"] = candidato
        if (
            item["pior"] is None
            or (pct, tentativa.acertos, -tentativa.id)
            < (item["pior"]["pct"], item["pior"]["acertos"], -item["pior"]["id"])
        ):
            item["pior"] = candidato

    ranking = sorted(
        ranking_por_aluno.values(),
        key=lambda item: (
            item["melhor"]["pct"],
            item["melhor"]["acertos"],
            item["tentativas"],
        ),
        reverse=True,
    )[:10]

    aproveitamentos = [
        round(s.acertos / s.total * 100)
        for s in historico
        if s.total > 0
    ]
    total_questoes = sum(s.total for s in historico)
    stats = {
        "sessoes": len(historico),
        "questoes": total_questoes,
        "media": round(sum(aproveitamentos) / len(aproveitamentos))
        if aproveitamentos else None,
        "melhor": max(aproveitamentos) if aproveitamentos else None,
    }
    return render_template(
        "scores.html",
        historico=historico,
        ranking=ranking,
        stats=stats,
    )


@app.route("/sobre")
def sobre():
    return render_template("sobre.html")


# ---------------------------------------------------------------------------
# Handlers de erro
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def nao_encontrado(e):
    return render_template("404.html"), 404


@app.errorhandler(429)
def ratelimit_handler(e):
    response = make_response(render_template("429.html"), 429)
    response.headers["Retry-After"] = "60"
    return response


@app.errorhandler(SecurityError)
def host_nao_confiavel(e):
    # Não renderizar template: url_for depende do host já rejeitado.
    return "Bad Request", 400


@app.errorhandler(400)
def bad_request(e):
    return render_template("400.html"), 400


@app.errorhandler(405)
def metodo_nao_permitido(e):
    return render_template("405.html"), 405


@app.errorhandler(500)
def erro_interno(e):
    return render_template("500.html"), 500


@app.get("/health")
@limiter.exempt
def health():
    db_ok = database_healthy(**_db_options())
    status = "ok" if db_ok else "degraded"
    return jsonify({"status": status, "db": db_ok}), 200 if db_ok else 503


@app.route("/robots.txt")
def robots_txt():
    return send_from_directory(app.static_folder, "robots.txt")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug)
