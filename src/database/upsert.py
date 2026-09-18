from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session


def upsert_rows(
    db: Session,
    model: type,
    rows: Iterable[dict[str, Any]],
    *,
    conflict_columns: Sequence[str],
    update_columns: Sequence[str],
) -> None:
    """Atomically insert or update snapshot rows on supported production databases."""
    table_columns = set(model.__table__.columns.keys())
    configured_columns = set(conflict_columns) | set(update_columns)
    unknown_columns = configured_columns - table_columns
    if unknown_columns:
        raise ValueError(
            f"Upsert columns are not present on {model.__name__}: "
            f"{', '.join(sorted(unknown_columns))}"
        )

    values = [
        {column: value for column, value in row.items() if column in table_columns}
        for row in rows
    ]
    if not values:
        return

    for value in values:
        missing_conflict_columns = set(conflict_columns) - set(value)
        if missing_conflict_columns:
            raise ValueError(
                f"Upsert row for {model.__name__} is missing conflict columns: "
                f"{', '.join(sorted(missing_conflict_columns))}"
            )

    dialect_name = db.get_bind().dialect.name
    insert_factory = {
        "postgresql": postgresql_insert,
        "sqlite": sqlite_insert,
    }.get(dialect_name)

    try:
        if insert_factory is not None:
            statement = insert_factory(model).values(values)
            statement = statement.on_conflict_do_update(
                index_elements=[model.__table__.c[column] for column in conflict_columns],
                set_={column: getattr(statement.excluded, column) for column in update_columns},
            )
            db.execute(statement)
        else:
            for value in values:
                filters = {
                    column: value[column]
                    for column in conflict_columns
                }
                existing = db.query(model).filter_by(**filters).one_or_none()
                if existing is None:
                    db.add(model(**value))
                    continue
                for column in update_columns:
                    setattr(existing, column, value[column])
        db.commit()
    except Exception:
        db.rollback()
        raise
