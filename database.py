from __future__ import annotations

import os
import re
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Iterator

from alembic import command
from alembic.config import Config
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    event,
    select,
    text,
)
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, selectinload

ROOT = Path(__file__).resolve().parent


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def clean_display_name(value: str) -> str:
    """Normaliza um nome declarado sem aceitar controles invisíveis/NUL."""
    normalized = unicodedata.normalize("NFKC", value or "")
    visible = "".join(
        " " if unicodedata.category(char).startswith("C") else char
        for char in normalized
    )
    return " ".join(visible.split())[:100]


def normalize_name(value: str) -> str:
    """Chave de agrupamento; não afirma identidade civil do participante."""
    compact = clean_display_name(value)
    normalized = unicodedata.normalize("NFKD", compact.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))[:120]


class Base(DeclarativeBase):
    pass


class Score(Base):
    """Tabela legada mantida somente para importação/compatibilidade."""

    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data: Mapped[str] = mapped_column(String, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    acertos: Mapped[int] = mapped_column(Integer, nullable=False)
    nome: Mapped[str] = mapped_column(String, nullable=False, default="")
    ip: Mapped[str] = mapped_column(String, nullable=False, default="")
    ip_hash: Mapped[str] = mapped_column(String, nullable=False, default="")


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    attempts: Mapped[list["Attempt"]] = relationship(back_populates="participant")


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mode: Mapped[str] = mapped_column(String(24), nullable=False, default="aleatorio")
    quiz_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", index=True)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    acertos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    legacy_score_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)

    participant: Mapped[Participant] = relationship(back_populates="attempts")
    answers: Mapped[list["Answer"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("attempt_id", "image_key", name="uq_answer_attempt_image"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    image_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    correct_code: Mapped[int] = mapped_column(Integer, nullable=False)
    answered_code: Mapped[int] = mapped_column(Integer, nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    question_order: Mapped[int] = mapped_column(Integer, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    attempt: Mapped[Attempt] = relationship(back_populates="answers")


_engine: Engine | None = None
_engine_url: str | None = None


def resolve_database_url(*, database_url: str | None = None, db_path: str | None = None) -> URL:
    raw_url = database_url if database_url is not None else os.environ.get("DATABASE_URL", "")
    if raw_url:
        url = make_url(raw_url)
        backend = url.get_backend_name()
        if backend == "postgresql" and "+" not in url.drivername:
            url = url.set(drivername="postgresql+psycopg")
        elif backend == "sqlite" and "+" not in url.drivername:
            url = url.set(drivername="sqlite+pysqlite")
        return url

    pg_host = os.environ.get("POSTGRES_HOST", "")
    if pg_host:
        required = {
            "POSTGRES_DB": os.environ.get("POSTGRES_DB", ""),
            "POSTGRES_USER": os.environ.get("POSTGRES_USER", ""),
            "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"PostgreSQL incompleto; faltando: {', '.join(missing)}")
        return URL.create(
            "postgresql+psycopg",
            username=required["POSTGRES_USER"],
            password=required["POSTGRES_PASSWORD"],
            host=pg_host,
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            database=required["POSTGRES_DB"],
        )

    path = Path(db_path if db_path is not None else os.environ.get("DB_PATH", "icdas.db"))
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    return URL.create("sqlite+pysqlite", database=str(path))


def _build_engine(url: URL) -> Engine:
    kwargs: dict = {"pool_pre_ping": True}
    if url.get_backend_name() == "sqlite":
        kwargs["connect_args"] = {"timeout": 10, "check_same_thread": False}
    engine = create_engine(url, **kwargs)

    if url.get_backend_name() == "sqlite":
        @event.listens_for(engine, "connect")
        def _configure_sqlite(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()
    return engine


def get_engine(*, database_url: str | None = None, db_path: str | None = None) -> Engine:
    global _engine, _engine_url
    url = resolve_database_url(database_url=database_url, db_path=db_path)
    rendered = url.render_as_string(hide_password=False)
    if _engine is None or _engine_url != rendered:
        if _engine is not None:
            _engine.dispose()
        _engine = _build_engine(url)
        _engine_url = rendered
    return _engine


def reset_engine() -> None:
    global _engine, _engine_url
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _engine_url = None


def upgrade_schema(*, database_url: str | None = None, db_path: str | None = None) -> None:
    engine = get_engine(database_url=database_url, db_path=db_path)
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")


def clear_legacy_ips(*, database_url: str | None = None, db_path: str | None = None) -> None:
    with get_engine(database_url=database_url, db_path=db_path).begin() as connection:
        connection.execute(text("UPDATE scores SET ip = '' WHERE ip <> ''"))


@contextmanager
def session_scope(*, database_url: str | None = None, db_path: str | None = None) -> Iterator[Session]:
    with Session(get_engine(database_url=database_url, db_path=db_path), expire_on_commit=False) as db:
        yield db


# ---------------------------------------------------------------------------
# Compatibilidade da tabela legada
# ---------------------------------------------------------------------------

def latest_name_for_ip_hash(ip_hash: str, *, database_url: str | None = None, db_path: str | None = None) -> str:
    if not ip_hash:
        return ""
    with session_scope(database_url=database_url, db_path=db_path) as db:
        latest = db.scalar(
            select(Participant.name)
            .join(Attempt, Attempt.participant_id == Participant.id)
            .where(Attempt.ip_hash == ip_hash)
            .order_by(Attempt.id.desc())
            .limit(1)
        )
        if latest:
            return latest
        return db.scalar(
            select(Score.nome)
            .where(Score.ip_hash == ip_hash, Score.nome != "")
            .order_by(Score.id.desc())
            .limit(1)
        ) or ""


def save_score(*, data: str, total: int, acertos: int, nome: str, ip_hash: str,
               database_url: str | None = None, db_path: str | None = None) -> Score:
    """Somente para importadores/testes legados; o app novo usa Attempt/Answer."""
    with session_scope(database_url=database_url, db_path=db_path) as db:
        score = Score(data=data, total=total, acertos=acertos, nome=nome, ip="", ip_hash=ip_hash)
        db.add(score)
        db.commit()
        return score


def recent_scores(*, limit: int = 20, database_url: str | None = None, db_path: str | None = None) -> list[Score]:
    with session_scope(database_url=database_url, db_path=db_path) as db:
        return list(db.scalars(select(Score).order_by(Score.id.desc()).limit(limit)).all())


def valid_scores(*, database_url: str | None = None, db_path: str | None = None) -> list[Score]:
    with session_scope(database_url=database_url, db_path=db_path) as db:
        return list(db.scalars(select(Score).where(Score.total > 0).order_by(Score.id.desc())).all())


# ---------------------------------------------------------------------------
# Modelo atual
# ---------------------------------------------------------------------------

def create_participant(name: str, *, database_url: str | None = None, db_path: str | None = None) -> Participant:
    clean = clean_display_name(name)
    if not clean:
        raise ValueError("nome vazio")
    with session_scope(database_url=database_url, db_path=db_path) as db:
        participant = Participant(name=clean, name_key=normalize_name(clean))
        db.add(participant)
        db.commit()
        return participant


def participant_exists(participant_id: int | None, *, database_url: str | None = None,
                       db_path: str | None = None) -> bool:
    if not participant_id:
        return False
    with session_scope(database_url=database_url, db_path=db_path) as db:
        return db.get(Participant, participant_id) is not None


def start_attempt(*, participant_id: int, mode: str, quiz_version: str, ip_hash: str,
                  database_url: str | None = None, db_path: str | None = None) -> Attempt:
    with session_scope(database_url=database_url, db_path=db_path) as db:
        participant = db.get(Participant, participant_id)
        if participant is None:
            raise ValueError("participante inexistente")
        attempt = Attempt(
            participant_id=participant_id,
            mode="sequencial" if mode == "sequencial" else "aleatorio",
            quiz_version=quiz_version,
            ip_hash=ip_hash,
            status="active",
        )
        db.add(attempt)
        db.commit()
        return attempt


def attempt_is_active(attempt_id: int | None, *, database_url: str | None = None, db_path: str | None = None) -> bool:
    if not attempt_id:
        return False
    with session_scope(database_url=database_url, db_path=db_path) as db:
        attempt = db.get(Attempt, attempt_id)
        return bool(attempt and attempt.status == "active")


def record_answer(*, attempt_id: int, image_key: str, correct_code: int, answered_code: int,
                  response_time_ms: int | None, question_order: int,
                  database_url: str | None = None, db_path: str | None = None) -> tuple[bool, bool]:
    if not 0 <= correct_code <= 6 or not 0 <= answered_code <= 6:
        raise ValueError("código ICDAS fora do intervalo")
    if response_time_ms is not None:
        response_time_ms = max(0, min(int(response_time_ms), 24 * 60 * 60 * 1000))
    question_order = max(1, int(question_order))

    with session_scope(database_url=database_url, db_path=db_path) as db:
        # Serializa respostas da mesma tentativa em PostgreSQL. Isso evita
        # lost update dos contadores e torna POST concorrente idempotente.
        attempt = db.execute(
            select(Attempt).where(Attempt.id == attempt_id).with_for_update()
        ).scalar_one_or_none()
        if attempt is None or attempt.status != "active":
            raise ValueError("tentativa não está ativa")
        existing = db.scalar(
            select(Answer).where(Answer.attempt_id == attempt_id, Answer.image_key == image_key).limit(1)
        )
        if existing is not None:
            return False, existing.correct
        is_correct = answered_code == correct_code
        answer = Answer(
            attempt_id=attempt_id,
            image_key=image_key[:255],
            correct_code=correct_code,
            answered_code=answered_code,
            correct=is_correct,
            response_time_ms=response_time_ms,
            question_order=question_order,
        )
        db.add(answer)
        attempt.total += 1
        if is_correct:
            attempt.acertos += 1
        db.commit()
        return True, is_correct


def end_attempt(attempt_id: int | None, status: str, *, database_url: str | None = None,
                db_path: str | None = None) -> None:
    if not attempt_id:
        return
    allowed = {"completed", "reset", "mode_change", "student_change", "empty", "expired"}
    if status not in allowed:
        raise ValueError("status final inválido")
    with session_scope(database_url=database_url, db_path=db_path) as db:
        attempt = db.execute(
            select(Attempt).where(Attempt.id == attempt_id).with_for_update()
        ).scalar_one_or_none()
        if attempt is None or attempt.status != "active":
            return
        # Finalizar uma tentativa sem nenhuma resposta não é conclusão.
        attempt.status = "empty" if status == "completed" and attempt.total == 0 else status
        attempt.finished_at = utcnow()
        db.commit()


def expire_stale_attempts(*, max_age_hours: int = 1, database_url: str | None = None,
                          db_path: str | None = None) -> int:
    """Fecha tentativas que sobreviveram ao tempo máximo da sessão web."""
    cutoff = utcnow() - timedelta(hours=max(1, max_age_hours))
    with session_scope(database_url=database_url, db_path=db_path) as db:
        active = list(
            db.scalars(
                select(Attempt)
                .where(Attempt.status == "active")
                .with_for_update()
            ).all()
        )
        stale = []
        for attempt in active:
            started = attempt.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            else:
                started = started.astimezone(timezone.utc)
            if started < cutoff:
                stale.append(attempt)
        finished = utcnow()
        for attempt in stale:
            attempt.status = "expired"
            attempt.finished_at = finished
        if stale:
            db.commit()
        return len(stale)


def scoreboard_snapshot(*, database_url: str | None = None, db_path: str | None = None) -> dict:
    expire_stale_attempts(database_url=database_url, db_path=db_path)
    with session_scope(database_url=database_url, db_path=db_path) as db:
        attempts = list(
            db.scalars(
                select(Attempt)
                .options(selectinload(Attempt.participant))
                .where(Attempt.status == "completed", Attempt.total > 0)
                .order_by(Attempt.id.desc())
            ).all()
        )

    history = []
    ranking_by_name: dict[str, dict] = {}
    for attempt in attempts:
        item = {
            "id": attempt.id,
            "nome": attempt.participant.name,
            "data": attempt.finished_at or attempt.started_at,
            "total": attempt.total,
            "acertos": attempt.acertos,
            "mode": attempt.mode,
            "quiz_version": attempt.quiz_version,
        }
        if len(history) < 20:
            history.append(item)
        pct = round(attempt.acertos / attempt.total * 100)
        key = attempt.participant.name_key or normalize_name(attempt.participant.name)
        if key == normalize_name("Anônimo"):
            continue
        group = ranking_by_name.setdefault(
            key,
            {"nome": attempt.participant.name, "tentativas": 0, "melhor": None, "pior": None},
        )
        group["tentativas"] += 1
        candidate = {"pct": pct, "acertos": attempt.acertos, "total": attempt.total, "id": attempt.id}
        if group["melhor"] is None or (pct, attempt.acertos, attempt.id) > (
            group["melhor"]["pct"], group["melhor"]["acertos"], group["melhor"]["id"]
        ):
            group["melhor"] = candidate
        if group["pior"] is None or (pct, attempt.acertos, -attempt.id) < (
            group["pior"]["pct"], group["pior"]["acertos"], -group["pior"]["id"]
        ):
            group["pior"] = candidate

    ranking = sorted(
        ranking_by_name.values(),
        key=lambda item: (item["melhor"]["pct"], item["melhor"]["acertos"], item["tentativas"]),
        reverse=True,
    )[:10]
    pcts = [round(a.acertos / a.total * 100) for a in attempts]
    return {
        "historico": history,
        "ranking": ranking,
        "stats": {
            "sessoes": len(attempts),
            "questoes": sum(a.total for a in attempts),
            "media": round(sum(pcts) / len(pcts)) if pcts else None,
            "melhor": max(pcts) if pcts else None,
        },
    }


def analytics_snapshot(*, database_url: str | None = None, db_path: str | None = None) -> dict:
    expire_stale_attempts(database_url=database_url, db_path=db_path)
    with session_scope(database_url=database_url, db_path=db_path) as db:
        participants = list(db.scalars(select(Participant).order_by(Participant.id)).all())
        attempts = list(
            db.scalars(select(Attempt).options(selectinload(Attempt.participant)).order_by(Attempt.id)).all()
        )
        answers = list(db.scalars(select(Answer).order_by(Answer.id)).all())

    completed = [a for a in attempts if a.status == "completed" and a.total > 0]
    pcts = [round(a.acertos / a.total * 100, 1) for a in completed]
    response_times = [a.response_time_ms for a in answers if a.response_time_ms is not None]

    by_code = {
        code: {"code": code, "total": 0, "correct": 0, "accuracy": None, "mean_ms": None, "times": []}
        for code in range(7)
    }
    confusion = [[0 for _ in range(7)] for _ in range(7)]
    by_image: dict[str, dict] = {}
    for answer in answers:
        if 0 <= answer.correct_code <= 6 and 0 <= answer.answered_code <= 6:
            confusion[answer.correct_code][answer.answered_code] += 1
        code = by_code.get(answer.correct_code)
        if code is not None:
            code["total"] += 1
            code["correct"] += int(answer.correct)
            if answer.response_time_ms is not None:
                code["times"].append(answer.response_time_ms)
        image = by_image.setdefault(
            answer.image_key,
            {"image_key": answer.image_key, "total": 0, "correct": 0, "times": []},
        )
        image["total"] += 1
        image["correct"] += int(answer.correct)
        if answer.response_time_ms is not None:
            image["times"].append(answer.response_time_ms)

    for item in by_code.values():
        if item["total"]:
            item["accuracy"] = round(item["correct"] / item["total"] * 100, 1)
        if item["times"]:
            item["mean_ms"] = round(sum(item["times"]) / len(item["times"]))
        del item["times"]

    images = []
    for item in by_image.values():
        item["accuracy"] = round(item["correct"] / item["total"] * 100, 1) if item["total"] else None
        item["mean_ms"] = round(sum(item["times"]) / len(item["times"])) if item["times"] else None
        del item["times"]
        images.append(item)
    images.sort(key=lambda item: (item["accuracy"] if item["accuracy"] is not None else 101, -item["total"]))

    mode_groups: dict[str, list[float]] = {}
    version_groups: dict[str, int] = {}
    name_groups: dict[str, list[Attempt]] = {}
    for attempt in completed:
        mode_groups.setdefault(attempt.mode, []).append(attempt.acertos / attempt.total * 100)
        version_groups[attempt.quiz_version] = version_groups.get(attempt.quiz_version, 0) + 1
        if attempt.participant.name_key != normalize_name("Anônimo"):
            name_groups.setdefault(attempt.participant.name_key, []).append(attempt)

    modes = [
        {"mode": mode, "attempts": len(values), "mean": round(sum(values) / len(values), 1)}
        for mode, values in sorted(mode_groups.items())
    ]
    evolution = []
    for group in name_groups.values():
        if len(group) < 2:
            continue
        group.sort(key=lambda a: a.id)
        first, last = group[0], group[-1]
        first_pct = round(first.acertos / first.total * 100, 1)
        last_pct = round(last.acertos / last.total * 100, 1)
        evolution.append({
            "nome": last.participant.name,
            "attempts": len(group),
            "first": first_pct,
            "last": last_pct,
            "delta": round(last_pct - first_pct, 1),
        })
    evolution.sort(key=lambda item: item["delta"], reverse=True)

    recent = [
        {
            "id": attempt.id,
            "nome": attempt.participant.name,
            "status": attempt.status,
            "mode": attempt.mode,
            "version": attempt.quiz_version,
            "total": attempt.total,
            "acertos": attempt.acertos,
            "started_at": attempt.started_at,
            "finished_at": attempt.finished_at,
            "ip_hash": attempt.ip_hash,
        }
        for attempt in reversed(attempts[-30:])
    ]

    return {
        "summary": {
            "participants": len(participants),
            "attempts": len(attempts),
            "completed": len(completed),
            "answers": len(answers),
            "mean_score": round(sum(pcts) / len(pcts), 1) if pcts else None,
            "completion_rate": round(len(completed) / len(attempts) * 100, 1) if attempts else None,
            "median_response_ms": round(median(response_times)) if response_times else None,
        },
        "by_code": list(by_code.values()),
        "confusion": confusion,
        "images": images[:20],
        "modes": modes,
        "versions": sorted(version_groups.items(), key=lambda pair: pair[1], reverse=True),
        "evolution": evolution[:20],
        "recent": recent,
    }


def export_attempt_rows(*, database_url: str | None = None, db_path: str | None = None) -> list[dict]:
    expire_stale_attempts(database_url=database_url, db_path=db_path)
    with session_scope(database_url=database_url, db_path=db_path) as db:
        attempts = list(
            db.scalars(
                select(Attempt).options(selectinload(Attempt.participant)).order_by(Attempt.id)
            ).all()
        )
    return [
        {
            "attempt_id": a.id,
            "participant_id": a.participant_id,
            "nome": a.participant.name,
            "started_at": a.started_at.isoformat() if a.started_at else "",
            "finished_at": a.finished_at.isoformat() if a.finished_at else "",
            "status": a.status,
            "mode": a.mode,
            "quiz_version": a.quiz_version,
            "total": a.total,
            "acertos": a.acertos,
            "percentual": round(a.acertos / a.total * 100, 1) if a.total else "",
            "ip_hash": a.ip_hash,
            "legacy_score_id": a.legacy_score_id or "",
        }
        for a in attempts
    ]


def database_healthy(*, database_url: str | None = None, db_path: str | None = None) -> bool:
    try:
        with get_engine(database_url=database_url, db_path=db_path).connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Read-only views for the 2026 responsive redesign. No schema changes.
# ---------------------------------------------------------------------------

def attempt_review_snapshot(*, attempt_id: int, participant_id: int,
                            database_url: str | None = None, db_path: str | None = None) -> dict | None:
    """Return only a completed attempt belonging to this browser's participant.

    Never use a client-provided attempt ID without verifying ownership here.
    """
    if not attempt_id or not participant_id:
        return None
    with session_scope(database_url=database_url, db_path=db_path) as db:
        attempt = db.scalar(
            select(Attempt).options(selectinload(Attempt.answers), selectinload(Attempt.participant))
            .where(Attempt.id == attempt_id, Attempt.participant_id == participant_id)
        )
        if attempt is None or attempt.status != "completed":
            return None
        return {
            "id": attempt.id, "nome": attempt.participant.name,
            "total": attempt.total, "acertos": attempt.acertos,
            "answers": [
                {"image_key": a.image_key, "correct_code": a.correct_code,
                 "answered_code": a.answered_code, "correct": a.correct,
                 "question_order": a.question_order}
                for a in sorted(attempt.answers, key=lambda a: (a.question_order, a.id))
            ],
        }


def dashboard_redesign_snapshot(*, period: str = "30", database_url: str | None = None,
                                db_path: str | None = None, now: datetime | None = None) -> dict:
    """Aggregate de-identified analytics for the professor's responsive dashboard.

    All grouping uses Sao Paulo civil dates. This view performs no writes and
    deliberately emits no raw IP address, only a truncated HMAC in recent rows.
    """
    from collections import Counter, defaultdict
    from zoneinfo import ZoneInfo
    from datetime import date

    tz = ZoneInfo("America/Sao_Paulo")
    current = now or utcnow()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    today = current.astimezone(tz).date()
    period = str(period) if str(period) in ("30", "90", "tudo") else "30"
    days = None if period == "tudo" else int(period)

    def local(ts):
        if ts is None:
            return None
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(tz)

    def select_period(items, offset=0):
        if days is None:
            return list(items)
        start = today - timedelta(days=days * (offset + 1) - 1)
        end = today - timedelta(days=days * offset)
        return [a for a in items if (dt := local(a.started_at)) and start <= dt.date() <= end]

    with session_scope(database_url=database_url, db_path=db_path) as db:
        attempts_all = list(db.scalars(select(Attempt).options(selectinload(Attempt.participant)).order_by(Attempt.started_at, Attempt.id)).all())
        answers_all = list(db.scalars(select(Answer).order_by(Answer.id)).all())
    attempts = select_period(attempts_all)
    previous = select_period(attempts_all, 1) if days is not None else []
    ids = {a.id for a in attempts}
    answers = [a for a in answers_all if a.attempt_id in ids]
    answer_by_attempt = defaultdict(list)
    for a in answers:
        answer_by_attempt[a.attempt_id].append(a)
    completed = [a for a in attempts if a.status == "completed" and a.total > 0]

    def metrics(items):
        done = [a for a in items if a.status == "completed" and a.total > 0]
        ids_ = {a.id for a in items}
        resp = [a.response_time_ms for a in answers_all if a.attempt_id in ids_ and a.response_time_ms is not None]
        return [len({a.participant_id for a in items}), len(items),
                round(len(done) / len(items) * 100, 1) if items else None,
                round(sum(a.acertos / a.total for a in done) / len(done) * 100, 1) if done else None,
                round(median(resp) / 1000, 1) if resp else None,
                len({a.ip_hash for a in items if a.ip_hash})]

    values, prev_values = metrics(attempts), metrics(previous)
    # Hash de IP não distingue dispositivos atrás da mesma rede; não atribua
    # identidade individual a esse sinal técnico.
    names = ("Participantes", "Tentativas", "Concluídas", "Acerto médio", "Tempo mediano por foto", "Origens de rede distintas")
    summary = []
    for i, (name, value) in enumerate(zip(names, values)):
        prior = prev_values[i] if days is not None else None
        delta = round(value - prior, 1) if value is not None and prior is not None else None
        summary.append({"name": name, "value": value, "delta": delta,
                        "unit": "%" if i in (2, 3) else ("s" if i == 4 else ""),
                        "compare": days is not None})

    # The time series is daily for 30 days, weekly for 90 days / all history.
    buckets = defaultdict(lambda: [0, 0])
    if period == "30":
        keys = [today - timedelta(days=i) for i in range(29, -1, -1)]
        for d in keys:
            buckets[d]
        label = lambda d: d.strftime("%d/%m")
        group = lambda d: d
    else:
        first = min((local(a.started_at).date() for a in attempts), default=today)
        if days:
            first = today - timedelta(days=days - 1)
        first = first - timedelta(days=first.weekday())
        keys = []
        d = first
        while d <= today:
            keys.append(d)
            buckets[d]
            d += timedelta(days=7)
        label = lambda d: d.strftime("%d/%m")
        group = lambda d: d - timedelta(days=d.weekday())
    for a in attempts:
        if a.started_at:
            k = group(local(a.started_at).date())
            buckets[k][0 if a.status == "completed" and a.total > 0 else 1] += 1
    activity = [{"label": label(k), "complete": buckets[k][0], "incomplete": buckets[k][1]} for k in keys]
    max_activity = max((sum(v) for v in buckets.values()), default=1) or 1

    heat = [[0 for _ in range(8)] for _ in range(7)]
    # 8-24 in two-hour buckets, starts at Monday.
    for a in attempts:
        t = local(a.started_at)
        if t and 8 <= t.hour < 24:
            heat[t.weekday()][(t.hour - 8) // 2] += 1
    heat_max = max((v for row in heat for v in row), default=1) or 1

    codes = []
    confusion = [[0] * 7 for _ in range(7)]
    for a in answers:
        if 0 <= a.correct_code < 7 and 0 <= a.answered_code < 7:
            confusion[a.correct_code][a.answered_code] += 1
    for c in range(7):
        rows = [a for a in answers if a.correct_code == c]
        wrong = Counter(a.answered_code for a in rows if not a.correct)
        times = [a.response_time_ms for a in rows if a.response_time_ms is not None]
        codes.append({"code": c, "n": len(rows),
                      "pct": round(sum(a.correct for a in rows) / len(rows) * 100) if rows else 0,
                      "sec": round(sum(times) / len(times) / 1000, 1) if times else None,
                      "confused": wrong.most_common(1)[0][0] if wrong else None,
                      "confused_pct": round(wrong.most_common(1)[0][1] / sum(wrong.values()) * 100) if wrong else None})
    confusion_pct = [[round(v / sum(row) * 100) if sum(row) else 0 for v in row] for row in confusion]

    grades = Counter(min(10, max(0, a.acertos)) for a in completed)
    histogram = [grades.get(i, 0) for i in range(11)]
    per_person = defaultdict(list)
    for a in completed:
        per_person[a.participant.name_key].append(a)
    evolution = []
    for i in range(4):
        subset = [a for group_ in per_person.values() for a in (group_[i:i+1] if i < 3 else group_[3:])]
        evolution.append({"label": str(i + 1) + ("ª" if i < 3 else "+"),
                          "n": len(subset),
                          "pct": round(sum(a.acertos / a.total for a in subset) / len(subset) * 100) if subset else 0})
    ranges = [(0, 4000), (4000, 8000), (8000, 12000), (12000, 20000), (20000, 10**12)]
    time_accuracy = []
    for lo, hi in ranges:
        subset = [a for a in answers if a.response_time_ms is not None and lo <= a.response_time_ms < hi]
        time_accuracy.append({"n": len(subset), "pct": round(sum(a.correct for a in subset) / len(subset) * 100) if subset else 0})
    by_order = []
    for i in range(1, 11):
        subset = [a for a in answers if a.question_order == i]
        by_order.append({"order": i, "n": len(subset), "pct": round(sum(a.correct for a in subset) / len(subset) * 100) if subset else 0})
    statuses = [(name, sum(a.status == key for a in attempts)) for key, name in
                (("completed", "Concluída"), ("reset", "Reiniciada"),
                 ("student_change", "Troca de aluno"), ("expired", "Expirada"),
                 ("mode_change", "Troca de modo"), ("empty", "Sem respostas"), ("active", "Em andamento"))]
    versions = []
    for ver in sorted({a.quiz_version for a in attempts}):
        group_ = [a for a in attempts if a.quiz_version == ver]
        done = [a for a in group_ if a.status == "completed" and a.total > 0]
        versions.append({"name": ver, "n": len(group_),
                         "first": min(local(a.started_at) for a in group_).strftime("%d/%m/%Y"),
                         "last": max(local(a.started_at) for a in group_).strftime("%d/%m/%Y"),
                         "pct": round(sum(a.acertos / a.total for a in done) / len(done) * 100) if done else None})
    versions.sort(key=lambda v: v["n"], reverse=True)

    photos = []
    grouped = defaultdict(list)
    for a in answers:
        grouped[a.image_key].append(a)
    for key, group_ in grouped.items():
        if len(group_) < 3:
            continue
        wrong = Counter(a.answered_code for a in group_ if not a.correct)
        times = [a.response_time_ms for a in group_ if a.response_time_ms is not None]
        photos.append({"image_key": key, "code": group_[0].correct_code, "n": len(group_),
                       "pct": round(sum(a.correct for a in group_) / len(group_) * 100),
                       "sec": round(sum(times) / len(times) / 1000, 1) if times else None,
                       "wrong": wrong.most_common(1)[0][0] if wrong else None})
    photos.sort(key=lambda item: (item["pct"], -item["n"]))

    students = []
    grouped_students = defaultdict(list)
    for a in attempts:
        grouped_students[a.participant.name_key].append(a)
    for key, group_ in grouped_students.items():
        done = [a for a in group_ if a.total and a.status == "completed"]
        if not done:
            continue
        group_.sort(key=lambda a: (a.started_at, a.id))
        done.sort(key=lambda a: (a.started_at, a.id))
        first = round(done[0].acertos / done[0].total * 100)
        last = round(done[-1].acertos / done[-1].total * 100)
        bycode = []
        all_ans = [x for a in group_ for x in answer_by_attempt[a.id]]
        for i in range(7):
            valid = [x for x in all_ans if x.correct_code == i]
            bycode.append(round(sum(x.correct for x in valid) / len(valid) * 100) if valid else None)
        students.append({"name": group_[-1].participant.name, "n": len(group_),
                         "best": max(round(a.acertos / a.total * 100) for a in done),
                         "last": last, "delta": last - first,
                         "date": local(group_[-1].started_at).strftime("%d/%m/%Y"),
                         "_sort_date": local(group_[-1].started_at),
                         "bycode": bycode,
                         "recent": [{"date": local(a.started_at).strftime("%d/%m %H:%M"),
                                     "status": a.status, "score": f"{a.acertos}/{a.total}" if a.total else "—"}
                                    for a in reversed(group_[-4:])]})
    # A apresentação usa dd/mm/aaaa, que não pode servir como chave de
    # ordenação cronológica. Ordene pelo datetime verdadeiro, sem expô-lo.
    students.sort(key=lambda s: s["_sort_date"], reverse=True)
    for item in students:
        del item["_sort_date"]

    recent = []
    for a in reversed(attempts[-30:]):
        start, end = local(a.started_at), local(a.finished_at)
        duration = round((a.finished_at - a.started_at).total_seconds()) if a.finished_at and a.started_at else None
        recent.append({"id": a.id, "name": a.participant.name, "status": a.status,
                       "score": f"{a.acertos}/{a.total}" if a.total else "—", "duration": duration,
                       "version": a.quiz_version[:12], "when": start.strftime("%d/%m %H:%M") if start else "—",
                       "ip": a.ip_hash[:10] if a.ip_hash else "—"})

    return {"period": period, "days": days, "summary": summary, "activity": activity,
            "activity_max": max_activity, "heat": heat, "heat_max": heat_max,
            "codes": codes, "confusion": confusion, "confusion_pct": confusion_pct,
            "histogram": histogram, "evolution": evolution, "time_accuracy": time_accuracy,
            "by_order": by_order, "statuses": statuses, "versions": versions,
            "photos": photos, "students": students, "recent": recent,
            "completed": len(completed), "attempts": len(attempts)}
