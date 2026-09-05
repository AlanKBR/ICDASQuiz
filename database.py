from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.config import Config
from sqlalchemy import Integer, String, create_engine, event, select, text
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

ROOT = Path(__file__).resolve().parent


class Base(DeclarativeBase):
    pass


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data: Mapped[str] = mapped_column(String, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    acertos: Mapped[int] = mapped_column(Integer, nullable=False)
    nome: Mapped[str] = mapped_column(String, nullable=False, default="")
    ip: Mapped[str] = mapped_column(String, nullable=False, default="")
    ip_hash: Mapped[str] = mapped_column(String, nullable=False, default="")


_engine: Engine | None = None
_engine_url: str | None = None


def resolve_database_url(*, database_url: str | None = None, db_path: str | None = None) -> URL:
    """Resolve o backend sem amarrar a aplicação a SQLite ou PostgreSQL.

    DATABASE_URL tem precedência. Sem ela, DB_PATH continua compatível com o
    comportamento histórico e aponta para um SQLite embedded.
    """
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
    """Mantém a coluna legada vazia mesmo após importações externas antigas."""
    with get_engine(database_url=database_url, db_path=db_path).begin() as connection:
        connection.execute(text("UPDATE scores SET ip = '' WHERE ip <> ''"))


@contextmanager
def session_scope(*, database_url: str | None = None, db_path: str | None = None) -> Iterator[Session]:
    with Session(get_engine(database_url=database_url, db_path=db_path), expire_on_commit=False) as db:
        yield db


def latest_name_for_ip_hash(ip_hash: str, *, database_url: str | None = None, db_path: str | None = None) -> str:
    if not ip_hash:
        return ""
    with session_scope(database_url=database_url, db_path=db_path) as db:
        return db.scalar(
            select(Score.nome)
            .where(Score.ip_hash == ip_hash, Score.nome != "")
            .order_by(Score.id.desc())
            .limit(1)
        ) or ""


def save_score(
    *,
    data: str,
    total: int,
    acertos: int,
    nome: str,
    ip_hash: str,
    database_url: str | None = None,
    db_path: str | None = None,
) -> Score:
    with session_scope(database_url=database_url, db_path=db_path) as db:
        score = Score(
            data=data,
            total=total,
            acertos=acertos,
            nome=nome,
            ip="",
            ip_hash=ip_hash,
        )
        db.add(score)
        db.commit()
        return score


def recent_scores(*, limit: int = 20, database_url: str | None = None, db_path: str | None = None) -> list[Score]:
    with session_scope(database_url=database_url, db_path=db_path) as db:
        return list(db.scalars(select(Score).order_by(Score.id.desc()).limit(limit)).all())


def valid_scores(*, database_url: str | None = None, db_path: str | None = None) -> list[Score]:
    with session_scope(database_url=database_url, db_path=db_path) as db:
        return list(db.scalars(select(Score).where(Score.total > 0).order_by(Score.id.desc())).all())


def database_healthy(*, database_url: str | None = None, db_path: str | None = None) -> bool:
    try:
        with get_engine(database_url=database_url, db_path=db_path).connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
