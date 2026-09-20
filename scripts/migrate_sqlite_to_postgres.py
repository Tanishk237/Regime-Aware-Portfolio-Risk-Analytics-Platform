from __future__ import annotations

import argparse
from collections.abc import Iterable

from sqlalchemy import MetaData, create_engine, func, inspect, select, text

from src.config import get_settings
from src.database.base import Base
from src.database.migrations import run_migrations
import src.database.models  # noqa: F401


def chunks(rows: list[dict], size: int) -> Iterable[list[dict]]:
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


def migrate(
    source_url: str,
    target_url: str,
    *,
    batch_size: int,
    dry_run: bool,
    ssl_mode: str,
) -> None:
    if not source_url.startswith("sqlite"):
        raise SystemExit("Source URL must point to SQLite.")
    if not target_url.startswith("postgresql"):
        raise SystemExit("Target URL must point to PostgreSQL.")

    run_migrations(target_url, ssl_mode=ssl_mode)
    source_engine = create_engine(source_url)
    target_engine = create_engine(
        target_url,
        pool_pre_ping=True,
        connect_args={"sslmode": ssl_mode},
    )
    source_metadata = MetaData()
    target_metadata = MetaData()
    source_metadata.reflect(bind=source_engine)
    target_metadata.reflect(bind=target_engine)

    source_tables = set(inspect(source_engine).get_table_names())
    target_tables = set(inspect(target_engine).get_table_names())
    ordered_names = [
        table.name
        for table in Base.metadata.sorted_tables
        if table.name in source_tables and table.name in target_tables
    ]

    with target_engine.connect() as target:
        populated = {
            name: target.execute(
                select(func.count()).select_from(target_metadata.tables[name])
            ).scalar_one()
            for name in ordered_names
        }
    nonempty = {name: count for name, count in populated.items() if count}
    if nonempty:
        raise SystemExit(
            "Target database is not empty; refusing to merge records: "
            + ", ".join(f"{name}={count}" for name, count in nonempty.items())
        )

    copied: dict[str, int] = {}
    with source_engine.connect() as source, target_engine.begin() as target:
        for name in ordered_names:
            source_table = source_metadata.tables[name]
            target_table = target_metadata.tables[name]
            rows = [dict(row) for row in source.execute(select(source_table)).mappings()]
            copied[name] = len(rows)
            if dry_run or not rows:
                continue
            for batch in chunks(rows, batch_size):
                target.execute(target_table.insert(), batch)

        if not dry_run:
            preparer = target.dialect.identifier_preparer
            for name in ordered_names:
                table = target_metadata.tables[name]
                if "id" not in table.c:
                    continue
                quoted_table = preparer.quote(name)
                target.execute(
                    text(
                        "SELECT setval(pg_get_serial_sequence(:table_name, 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {quoted_table}), 1), "
                        f"EXISTS(SELECT 1 FROM {quoted_table}))"
                    ),
                    {"table_name": name},
                )

    source_engine.dispose()
    target_engine.dispose()
    mode = "would copy" if dry_run else "copied"
    print(f"SQLite to PostgreSQL migration {mode}:")
    for name, count in copied.items():
        print(f"  {name}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy an existing Latent SQLite database into an empty PostgreSQL database."
    )
    parser.add_argument("--source", default="sqlite:///./data/regime.db")
    parser.add_argument("--target", default=get_settings().database_url)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument(
        "--ssl-mode",
        default=get_settings().database_ssl_mode,
        choices=("disable", "allow", "prefer", "require", "verify-ca", "verify-full"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    migrate(
        args.source,
        args.target,
        batch_size=max(1, args.batch_size),
        dry_run=args.dry_run,
        ssl_mode=args.ssl_mode,
    )


if __name__ == "__main__":
    main()
