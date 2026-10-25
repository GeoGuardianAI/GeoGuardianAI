from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from pathlib import Path
from models.schemas import DetectionJob, Incident

class DetectionRepository:
    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
    def initialize(self) -> None:
        self.connection.execute("CREATE TABLE IF NOT EXISTS incidents (id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL)")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS assets (id TEXT PRIMARY KEY, path TEXT NOT NULL, filename TEXT NOT NULL, kind TEXT NOT NULL, content_type TEXT NOT NULL, bytes INTEGER NOT NULL, created_at TEXT NOT NULL)"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS detection_jobs (id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        self.connection.commit()
    def save(self, incident: Incident) -> None:
        self.connection.execute("INSERT OR REPLACE INTO incidents VALUES (?, ?, ?)", (incident.incident_id, incident.model_dump_json(by_alias=True), incident.timestamp.isoformat()))
        self.connection.commit()
    def list(self, limit: int = 100) -> list[Incident]:
        rows = self.connection.execute("SELECT payload FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [Incident.model_validate_json(row["payload"]) for row in rows]
    def get(self, incident_id: str) -> Incident | None:
        row = self.connection.execute("SELECT payload FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        return Incident.model_validate_json(row["payload"]) if row else None
    def save_asset(self, asset: dict[str, str | int]) -> None:
        self.connection.execute(
            "INSERT INTO assets VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (asset["asset_id"], asset["path"], asset["filename"], asset["kind"], asset["content_type"], asset["bytes"]),
        )
        self.connection.commit()
    def list_assets(self) -> list[dict[str, str | int]]:
        rows = self.connection.execute("SELECT id, path FROM assets").fetchall()
        return [{"asset_id": row["id"], "path": row["path"]} for row in rows]
    def get_asset(self, asset_id: str) -> dict[str, str | int] | None:
        row = self.connection.execute(
            "SELECT id, path, filename FROM assets WHERE id = ?", (asset_id,)
        ).fetchone()
        if row is None:
            return None
        return {"asset_id": row["id"], "path": row["path"], "filename": row["filename"]}
    def save_job(self, job: DetectionJob) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO detection_jobs VALUES (?, ?, ?)",
            (job.job_id, job.model_dump_json(), job.created_at.isoformat()),
        )
        self.connection.commit()
    def get_job(self, job_id: str) -> DetectionJob | None:
        row = self.connection.execute(
            "SELECT payload FROM detection_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return DetectionJob.model_validate_json(row["payload"]) if row else None
    def fail_active_jobs(self, message: str) -> None:
        rows = self.connection.execute(
            "SELECT payload FROM detection_jobs"
        ).fetchall()
        for row in rows:
            job = DetectionJob.model_validate_json(row["payload"])
            if job.status in {"queued", "running"}:
                job.status = "failed"
                job.error = message
                job.updated_at = datetime.now(timezone.utc)
                self.save_job(job)
    def close(self) -> None: self.connection.close()
