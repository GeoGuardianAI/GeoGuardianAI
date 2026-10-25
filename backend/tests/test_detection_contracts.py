from datetime import datetime, timezone

from models.schemas import Coordinates, DetectedObject, Incident
from services.damage_service import DamageAssessmentService
from services.changeformer_service import ChangeFormerService


def test_unlocated_incident_does_not_invent_coordinates() -> None:
    incident = DamageAssessmentService().assess([], None, None, "image-test", "scene.png")

    assert incident.coordinates is None
    assert incident.geojson_geometry is None
    assert incident.source_asset_id == "image-test"
    assert incident.source_file == "scene.png"


def test_incident_emits_geojson_point_for_known_coordinates() -> None:
    incident = Incident(
        incident_id="INC-TEST",
        disaster="Flood",
        confidence=0.8,
        affected_area_sqkm=0,
        damaged_buildings=0,
        coordinates=Coordinates(lat=0, lng=0),
        timestamp=datetime.now(timezone.utc),
    )

    assert incident.geojson_geometry == {"type": "Point", "coordinates": [0, 0]}
    assert incident.model_dump(mode="json")["geojson_geometry"] == {
        "type": "Point",
        "coordinates": [0, 0],
    }


def test_repository_round_trips_incidents_and_assets(tmp_path) -> None:
    from services.repository import DetectionRepository

    repository = DetectionRepository(tmp_path / "detections.db")
    repository.initialize()
    incident = DamageAssessmentService().assess(
        [DetectedObject(class_name="damaged building", confidence=0.91)], None, None
    )
    repository.save(incident)
    repository.save_asset(
        {
            "asset_id": "image-test",
            "path": str(tmp_path / "scene.png"),
            "filename": "scene.png",
            "kind": "image",
            "content_type": "image/png",
            "bytes": 12,
        }
    )

    assert repository.get(incident.incident_id) == incident
    assert repository.list_assets() == [
        {"asset_id": "image-test", "path": str(tmp_path / "scene.png")}
    ]
    assert repository.get_asset("image-test") == {
        "asset_id": "image-test",
        "path": str(tmp_path / "scene.png"),
        "filename": "scene.png",
    }
    repository.close()


def test_detected_objects_are_kept_in_incident() -> None:
    objects = [DetectedObject(class_name="damaged building", confidence=0.91)]
    incident = DamageAssessmentService().assess(objects, None, None)

    assert incident.damaged_buildings == 1
    assert incident.detected_objects == objects


def test_incident_defaults_legacy_optional_fields() -> None:
    incident = Incident(
        incident_id="INC-LEGACY",
        disaster="No significant disaster",
        confidence=0,
        affected_area_sqkm=0,
        damaged_buildings=0,
        timestamp=datetime.now(timezone.utc),
    )

    assert incident.coordinates is None
    assert incident.detected_objects == []
    assert incident.damaged_roads == []


def test_change_detection_rejects_images_that_are_not_aligned() -> None:
    import numpy as np
    import pytest

    service = ChangeFormerService()
    before = np.zeros((8, 8, 3), dtype=np.uint8)
    after = np.zeros((10, 8, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="matching dimensions and be pre-aligned"):
        service.compare(before, after)


def test_change_detection_returns_bounded_preview_and_baseline_label() -> None:
    import base64
    import numpy as np

    before = np.zeros((16, 16, 3), dtype=np.uint8)
    after = before.copy()
    after[4:8, 4:8] = 255

    result = ChangeFormerService().compare(before, after)

    assert result["model"] == "opencv-baseline"
    assert 0 < result["changed_pixel_ratio"] < 1
    assert base64.b64decode(result["change_preview"].split(",", 1)[1]).startswith(b"\x89PNG")


def test_sam_service_requires_runtime_configuration(monkeypatch) -> None:
    import numpy as np
    import pytest
    from services.sam_service import SamService

    monkeypatch.delenv("GEOGUARDIAN_SAM2_CHECKPOINT", raising=False)
    monkeypatch.delenv("GEOGUARDIAN_SAM2_CONFIG", raising=False)

    with pytest.raises(RuntimeError, match="SAM2 is not configured"):
        SamService().segment(np.zeros((8, 8, 3), dtype=np.uint8), [], None)


def test_detection_job_round_trips_and_interrupted_jobs_fail(tmp_path) -> None:
    from models.schemas import DetectionJob
    from services.repository import DetectionRepository

    repository = DetectionRepository(tmp_path / "jobs.db")
    repository.initialize()
    now = datetime.now(timezone.utc)
    queued = DetectionJob(
        job_id="JOB-QUEUED",
        status="queued",
        created_at=now,
        updated_at=now,
    )
    repository.save_job(queued)
    assert repository.get_job(queued.job_id) == queued

    running = queued.model_copy(update={"job_id": "JOB-RUNNING", "status": "running"})
    repository.save_job(running)
    repository.fail_active_jobs("API restarted")

    interrupted = repository.get_job(running.job_id)
    assert interrupted is not None
    assert interrupted.status == "failed"
    assert interrupted.error == "API restarted"
    assert repository.get_job(queued.job_id).status == "failed"
    repository.close()
