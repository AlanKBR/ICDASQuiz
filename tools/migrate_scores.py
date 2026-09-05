from __future__ import annotations

import argparse
from pathlib import Path
import sys

from sqlalchemy import delete, func, select, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import (  # noqa: E402
    Score,
    get_engine,
    reset_engine,
    resolve_database_url,
    upgrade_schema,
)


def copy_scores(source_url: str, destination_url: str, *, replace: bool = False) -> int:
    reset_engine()
    source = get_engine(database_url=source_url)
    with Session(source) as db:
        rows = list(db.scalars(select(Score).order_by(Score.id)).all())
        payload = [
            {
                "id": row.id,
                "data": row.data,
                "total": row.total,
                "acertos": row.acertos,
                "nome": row.nome,
                "ip": "",
                "ip_hash": row.ip_hash,
            }
            for row in rows
        ]

    reset_engine()
    upgrade_schema(database_url=destination_url)
    destination = get_engine(database_url=destination_url)
    with Session(destination) as db:
        existing = db.scalar(select(func.count()).select_from(Score)) or 0
        if existing and not replace:
            raise RuntimeError(
                f"destino contém {existing} registro(s); use --replace somente após backup"
            )
        if existing:
            db.execute(delete(Score))
        if payload:
            db.bulk_insert_mappings(Score, payload)
        db.commit()

    # PostgreSQL mantém a sequence separada quando IDs são inseridos
    # explicitamente. SQLite não precisa de ajuste para o próximo AUTOINCREMENT.
    if destination.dialect.name == "postgresql" and payload:
        with destination.begin() as connection:
            connection.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('scores', 'id'), "
                    "(SELECT MAX(id) FROM scores), true)"
                )
            )
    return len(payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copia a tabela scores entre backends SQLAlchemy, sem persistir IP bruto."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source", help="DATABASE_URL de origem")
    source.add_argument("--source-sqlite", help="caminho para arquivo SQLite de origem")
    parser.add_argument(
        "--destination",
        help="DATABASE_URL de destino; sem esta opção usa DATABASE_URL/POSTGRES_* do ambiente",
    )
    parser.add_argument("--replace", action="store_true", help="substitui dados existentes no destino")
    args = parser.parse_args()

    source_url = args.source
    if args.source_sqlite:
        source_path = Path(args.source_sqlite).resolve()
        source_url = URL.create(
            "sqlite+pysqlite", database=str(source_path)
        ).render_as_string(hide_password=False)
    destination_url = args.destination or resolve_database_url().render_as_string(hide_password=False)

    copied = copy_scores(source_url, destination_url, replace=args.replace)
    print(f"migrate-scores: OK copied={copied}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
