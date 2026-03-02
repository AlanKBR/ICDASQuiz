import json
import logging
import os
import random
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, session,
)

load_dotenv()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

_secret = os.environ.get("SECRET_KEY", "")
_is_production = os.environ.get("FLASK_DEBUG", "0") == "0"

if not _secret or _secret == "troque-por-uma-chave-segura-em-producao":
    if _is_production:
        print(
            "AVISO DE SEGURANÇA: SECRET_KEY não definido ou inválido.\n"
            "  Defina SECRET_KEY no .env antes de usar em produção.\n"
            "  Gere com: python -c "
            "'import secrets; print(secrets.token_hex(32))'",
            file=sys.stderr,
        )
    _secret = "dev-secret-key-mude-em-producao"

app.secret_key = _secret
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Habilita Secure flag apenas fora do modo debug (HTTPS em produção)
app.config["SESSION_COOKIE_SECURE"] = _is_production
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=4)

DB_PATH = os.environ.get("DB_PATH", "icdas.db")

# Logging
logging.basicConfig(level=logging.INFO)
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
# Banco de dados SQLite
# ---------------------------------------------------------------------------

def get_db():
    """Retorna conexão SQLite. Caller deve fechar via try/finally."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                data    TEXT    NOT NULL,
                total   INTEGER NOT NULL,
                acertos INTEGER NOT NULL
            )
        """)
        db.commit()
    finally:
        db.close()


# Inicializa o banco ao carregar o módulo (funciona com gunicorn também)
init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

IMAGEM_EXTENSOES = (".png", ".jpg", ".jpeg", ".webp")

# Cache simples para get_imagens(): (pasta_mtime, contagem, resultado)
_imagens_cache: tuple = (None, None, [])


def get_imagens():
    """Retorna lista de imagens ICDAS. Resultado é cacheado por mtime."""
    global _imagens_cache
    pasta = Path("static/imagens")
    try:
        if not pasta.exists():
            return []
        stat = pasta.stat()
        mtime = stat.st_mtime
        count = sum(1 for _ in pasta.iterdir())
        cached_mtime, cached_count, cached = _imagens_cache
        if mtime == cached_mtime and count == cached_count:
            return cached
        imagens = []
        arquivos = sorted(pasta.iterdir(), key=lambda p: p.name)
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
        return imagens
    except OSError as exc:
        logger.error("Erro ao ler pasta de imagens: %s", exc)
        return []


def _safe_int(value, default=-1):
    """Converte valor para int de forma segura."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Context processor — injeta `now` em todos os templates automaticamente
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    return {"now": datetime.now()}


# ---------------------------------------------------------------------------
# Segurança — headers para produção
# ---------------------------------------------------------------------------

# CSP: permite apenas recursos do próprio servidor e jsdelivr (Pico CSS)
_CSP = (
    "default-src 'self'; "
    "style-src 'self' https://cdn.jsdelivr.net; "
    "font-src 'self' https://cdn.jsdelivr.net; "
    "script-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)


@app.after_request
def set_security_headers(response):
    response.headers["Content-Security-Policy"] = _CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    if _is_production:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html", descricoes=DESCRICOES)


@app.route("/galeria")
def galeria():
    imagens = get_imagens()
    imagens.sort(
        key=lambda x: (x["icdas_code"] if x["icdas_code"] is not None else 99)
    )
    return render_template(
        "galeria.html", imagens=imagens, descricoes=DESCRICOES
    )


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    imagens = get_imagens()

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
    )


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
def quiz_modo():
    """Alterna entre modo aleatório e sequencial e reinicia a fila."""
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
def quiz_finalizar():
    """Salva a sessão no banco e reseta o placar."""
    acertos = max(0, session.get("score_acertos", 0))
    total = max(0, session.get("score_total", 0))
    acertos = min(acertos, total)
    if total > 0:
        db = get_db()
        try:
            db.execute(
                "INSERT INTO scores (data, total, acertos) VALUES (?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M"), total, acertos),
            )
            db.commit()
        finally:
            db.close()
    session["score_acertos"] = 0
    session["score_total"] = 0
    session["quiz_fila"] = None
    session.pop("quiz_atual", None)
    session.pop("quiz_feedback", None)
    session.modified = True
    return redirect(url_for("scores"))


@app.route("/quiz/resetar", methods=["POST"])
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
def scores():
    db = get_db()
    try:
        historico = db.execute(
            "SELECT * FROM scores ORDER BY id DESC LIMIT 20"
        ).fetchall()
    finally:
        db.close()
    return render_template("scores.html", historico=historico)


@app.route("/sobre")
def sobre():
    return render_template("sobre.html")


# ---------------------------------------------------------------------------
# Handlers de erro
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def nao_encontrado(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def erro_interno(e):
    return render_template("500.html"), 500


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug)
