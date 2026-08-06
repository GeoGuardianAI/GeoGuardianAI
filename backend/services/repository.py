import json
import sqlite3
from pathlib import Path
from models.schemas import Incident

class DetectionRepository:
    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
    def initialize(self) -> None:
        self.connection.execute("CREATE TABLE IF NOT EXISTS incidents (id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL)")
        self.connection.commit()
    def save(self, incident: Incident) -> None:
        self.connection.execute("INSERT OR REPLACE INTO incidents VALUES (?, ?, ?)", (incident.incident_id, incident.model_dump_json(by_alias=True), incident.timestamp.isoformat()))
        self.connection.commit()
    def list(self, limit: int = 100) -> list[Incident]:
        rows = self.connection.execute("SELECT payload FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [Incident.model_validate_json(row["payload"]) for row in rows]
    def close(self) -> None: self.connection.close()
