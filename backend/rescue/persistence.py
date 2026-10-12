"""Small SQLite persistence layer for rescue-module operational state."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
from threading import RLock, local
from typing import Generator, Mapping, Sequence, TypeVar

from pydantic import BaseModel

from backend.rescue.models.audit_event import OperationalAuditEvent

TModel = TypeVar("TModel", bound=BaseModel)

_TABLES = {
    "missions",
    "resources",
    "allocations",
    "vehicles",
    "rescue_teams",
    "shelters",
    "emergency_shelters",
    "detection_links",
}
_DEFAULT_PATH = Path(__file__).resolve().parent / "data" / "rescue.sqlite3"
_database_path = os.environ.get("GEOGUARDIAN_DATABASE_PATH", str(_DEFAULT_PATH))
_state = local()
_database_lock = RLock()
_memory_connection: sqlite3.Connection | None = None


def _connect() -> sqlite3.Connection:
    global _memory_connection
    if _database_path == ":memory:":
        with _database_lock:
            if _memory_connection is None:
                _memory_connection = sqlite3.connect(
                    ":memory:", check_same_thread=False, timeout=30
                )
                _memory_connection.row_factory = sqlite3.Row
            connection = _memory_connection
    else:
        database_file = Path(_database_path).expanduser().resolve()
        database_file.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            str(database_file), timeout=30, check_same_thread=False
        )
        connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


@contextmanager
def transaction() -> Generator[sqlite3.Connection, None, None]:
    """Run database operations in an atomic transaction, supporting nesting."""
    existing = getattr(_state, "connection", None)
    if existing is not None:
        savepoint = f"nested_{getattr(_state, 'savepoint_counter', 0)}"
        _state.savepoint_counter = getattr(_state, "savepoint_counter", 0) + 1
        existing.execute(f"SAVEPOINT {savepoint}")
        try:
            yield existing
            existing.execute(f"RELEASE SAVEPOINT {savepoint}")
        except BaseException:
            existing.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            existing.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise
        return

    with _database_lock:
        connection = _connect()
        _state.connection = connection
        _state.savepoint_counter = 0
        try:
            connection.execute("BEGIN IMMEDIATE")
            _initialize_schema(connection)
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            _state.connection = None
            if _database_path != ":memory:":
                connection.close()


def load_records(
    connection: sqlite3.Connection,
    entity_type: str,
    model_type: type[TModel],
) -> list[TModel]:
    """Load the current committed entity snapshot using an active transaction."""
    _validate_table(entity_type)
    rows = connection.execute(
        "SELECT payload FROM rescue_records WHERE entity_type = ? ORDER BY position",
        (entity_type,),
    ).fetchall()
    return [model_type.model_validate_json(row["payload"]) for row in rows]


def next_record_id(
    connection: sqlite3.Connection,
    entity_type: str,
    prefix: str,
) -> str:
    """Return the next numeric ID while the caller holds a write transaction."""
    _validate_table(entity_type)
    rows = connection.execute(
        "SELECT record_id FROM rescue_records WHERE entity_type = ?",
        (entity_type,),
    ).fetchall()
    numbers = [
        int(record_id.removeprefix(prefix))
        for row in rows
        if (record_id := row["record_id"]).startswith(prefix)
        and record_id.removeprefix(prefix).isdigit()
    ]
    return f"{prefix}{max(numbers, default=0) + 1:04d}"


def _initialize_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS rescue_records (
            entity_type TEXT NOT NULL,
            record_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY (entity_type, record_id),
            UNIQUE (entity_type, position)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS operational_audit_events (
            event_id TEXT PRIMARY KEY,
            occurred_at TEXT NOT NULL,
            event_type TEXT NOT NULL,
            actor TEXT NOT NULL,
            mission_id TEXT,
            disaster_id TEXT,
            resource_id TEXT,
            vehicle_id TEXT,
            detection_id TEXT,
            payload TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_mission_time
        ON operational_audit_events (mission_id, occurred_at DESC, event_id DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_disaster_time
        ON operational_audit_events (disaster_id, occurred_at DESC, event_id DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_type_time
        ON operational_audit_events (event_type, occurred_at DESC, event_id DESC)
        """
    )


def initialize() -> None:
    """Create the SQLite schema without changing existing operational records."""
    with transaction():
        pass


def configure_database(path: str | os.PathLike[str]) -> None:
    """Select a database file, primarily for isolated persistence tests."""
    global _database_path, _memory_connection
    with _database_lock:
        if _memory_connection is not None:
            _memory_connection.close()
            _memory_connection = None
        _database_path = str(path)
    initialize()


def load_or_seed(
    entity_type: str,
    defaults: Sequence[TModel],
    model_type: type[TModel],
) -> list[TModel]:
    """Load stored records or initialize an empty entity set from defaults."""
    _validate_table(entity_type)
    with transaction() as connection:
        rows = connection.execute(
            "SELECT payload FROM rescue_records WHERE entity_type = ? ORDER BY position",
            (entity_type,),
        ).fetchall()
        if not rows and defaults:
            connection.executemany(
                """
                INSERT INTO rescue_records (entity_type, record_id, position, payload)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        entity_type,
                        _record_id(model),
                        position,
                        model.model_dump_json(),
                    )
                    for position, model in enumerate(defaults)
                ],
            )
            return [model.model_copy(deep=True) for model in defaults]
        return [model_type.model_validate_json(row["payload"]) for row in rows]


def persist_state(
    entities: Mapping[str, Sequence[BaseModel]],
    *,
    audit_events: Sequence[OperationalAuditEvent] = (),
) -> None:
    """Replace selected collections atomically, preserving input order.

    For shared operational updates, callers must load the current collection
    through the active transaction before passing the replacement; this helper
    does not merge snapshots or detect stale writers.
    """
    for entity_type in entities:
        _validate_table(entity_type)
    with transaction() as connection:
        for entity_type, records in entities.items():
            connection.execute(
                "DELETE FROM rescue_records WHERE entity_type = ?", (entity_type,)
            )
            connection.executemany(
                """
                INSERT INTO rescue_records (entity_type, record_id, position, payload)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        entity_type,
                        _record_id(record),
                        position,
                        record.model_dump_json(),
                    )
                    for position, record in enumerate(records)
                ],
            )
        connection.executemany(
            """
            INSERT INTO operational_audit_events (
                event_id, occurred_at, event_type, actor, mission_id, disaster_id,
                resource_id, vehicle_id, detection_id, payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    event.event_id,
                    event.occurred_at.isoformat(),
                    event.event_type.value,
                    event.actor,
                    event.mission_id,
                    event.disaster_id,
                    event.resource_id,
                    event.vehicle_id,
                    event.detection_id,
                    event.model_dump_json(),
                )
                for event in audit_events
            ],
        )


def list_audit_events(
    *,
    limit: int,
    offset: int,
    mission_id: str | None = None,
    disaster_id: str | None = None,
    event_type: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> tuple[list[OperationalAuditEvent], int]:
    """Return deterministic, filtered audit-event pages and the match count."""
    clauses: list[str] = []
    parameters: list[str | int] = []
    for column, value in (
        ("mission_id", mission_id),
        ("disaster_id", disaster_id),
        ("event_type", event_type),
    ):
        if value is not None:
            clauses.append(f"{column} = ?")
            parameters.append(value)
    if start_time is not None:
        clauses.append("occurred_at >= ?")
        parameters.append(start_time)
    if end_time is not None:
        clauses.append("occurred_at <= ?")
        parameters.append(end_time)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

    with transaction() as connection:
        total = connection.execute(
            f"SELECT COUNT(*) FROM operational_audit_events{where}", parameters
        ).fetchone()[0]
        rows = connection.execute(
            f"""
            SELECT payload FROM operational_audit_events{where}
            ORDER BY occurred_at DESC, event_id DESC
            LIMIT ? OFFSET ?
            """,
            [*parameters, limit, offset],
        ).fetchall()
    return [
        OperationalAuditEvent.model_validate_json(row["payload"])
        for row in rows
    ], total


def _record_id(model: BaseModel) -> str:
    for field_name in (
        "allocation_id",
        "detection_id",
        "mission_id",
        "resource_id",
        "vehicle_id",
        "team_id",
        "shelter_id",
    ):
        value = getattr(model, field_name, None)
        if value is not None:
            return str(value)
    raise ValueError(f"Cannot persist {type(model).__name__} without a stable identifier")


def _validate_table(entity_type: str) -> None:
    if entity_type not in _TABLES:
        raise ValueError(f"Unsupported rescue entity type '{entity_type}'")
