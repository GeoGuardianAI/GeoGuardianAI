"""Unit tests for the `Hospital` Pydantic model.

Uses pytest and Pydantic v2 validation behaviour.
"""

from pydantic import ValidationError
import pytest

from backend.rescue.models.hospital import Hospital


def _base_kwargs() -> dict:
    return {
        "hospital_id": "h-123",
        "name": "Example Hospital",
        "latitude": 40.0,
        "longitude": -70.0,
        "bed_capacity": 10,
        "available_beds": 5,
        "icu_capacity": 2,
        "available_icu": 1,
        "emergency_available": True,
    }


def test_valid_hospital_can_be_created() -> None:
    h = Hospital(**_base_kwargs())
    assert h.hospital_id == "h-123"
    assert h.name == "Example Hospital"


@pytest.mark.parametrize("lat", [90.1, -90.1, 100.0])
def test_invalid_latitude_is_rejected(lat: float) -> None:
    data = _base_kwargs()
    data["latitude"] = lat
    with pytest.raises(ValidationError):
        Hospital(**data)


@pytest.mark.parametrize("lon", [180.1, -180.1, 200.0])
def test_invalid_longitude_is_rejected(lon: float) -> None:
    data = _base_kwargs()
    data["longitude"] = lon
    with pytest.raises(ValidationError):
        Hospital(**data)


def test_negative_bed_capacity_is_rejected() -> None:
    data = _base_kwargs()
    data["bed_capacity"] = -1
    with pytest.raises(ValidationError):
        Hospital(**data)


def test_negative_icu_capacity_is_rejected() -> None:
    data = _base_kwargs()
    data["icu_capacity"] = -5
    with pytest.raises(ValidationError):
        Hospital(**data)


def test_available_beds_greater_than_capacity_is_rejected() -> None:
    data = _base_kwargs()
    data["bed_capacity"] = 5
    data["available_beds"] = 6
    with pytest.raises(ValidationError):
        Hospital(**data)


def test_available_icu_greater_than_capacity_is_rejected() -> None:
    data = _base_kwargs()
    data["icu_capacity"] = 1
    data["available_icu"] = 2
    with pytest.raises(ValidationError):
        Hospital(**data)


def test_zero_available_beds_and_icu_is_valid() -> None:
    data = _base_kwargs()
    data["available_beds"] = 0
    data["available_icu"] = 0
    h = Hospital(**data)
    assert h.available_beds == 0
    assert h.available_icu == 0


def test_full_capacity_available_is_valid() -> None:
    data = _base_kwargs()
    data["bed_capacity"] = 8
    data["available_beds"] = 8
    data["icu_capacity"] = 3
    data["available_icu"] = 3
    h = Hospital(**data)
    assert h.available_beds == h.bed_capacity
    assert h.available_icu == h.icu_capacity
