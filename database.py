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


def expire_stale_attempts(*, max_age_hours: int = 4, database_url: str | None = None,
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
