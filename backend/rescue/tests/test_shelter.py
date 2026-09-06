"""Unit tests for the `Shelter` Pydantic model."""

from pydantic import ValidationError
import pytest

from backend.rescue.models.shelter import Shelter


def _base_kwargs() -> dict:
    return {
        "shelter_id": "s-123",
        "name": "Community Shelter",
        "latitude": 40.0,
        "longitude": -70.0,
        "capacity": 100,
        "occupied": 40,
        "emergency_available": True,
    }


def test_valid_shelter_can_be_created() -> None:
    shelter = Shelter(**_base_kwargs())
    assert shelter.shelter_id == "s-123"
    assert shelter.name == "Community Shelter"


@pytest.mark.parametrize("latitude", [90.1, -90.1, 100.0])
def test_invalid_latitude_is_rejected(latitude: float) -> None:
    data = _base_kwargs()
    data["latitude"] = latitude
    with pytest.raises(ValidationError):
        Shelter(**data)


@pytest.mark.parametrize("longitude", [180.1, -180.1, 200.0])
def test_invalid_longitude_is_rejected(longitude: float) -> None:
    data = _base_kwargs()
    data["longitude"] = longitude
    with pytest.raises(ValidationError):
        Shelter(**data)


def test_negative_capacity_is_rejected() -> None:
    data = _base_kwargs()
    data["capacity"] = -1
    with pytest.raises(ValidationError):
        Shelter(**data)


def test_negative_occupied_is_rejected() -> None:
    data = _base_kwargs()
    data["occupied"] = -1
    with pytest.raises(ValidationError):
        Shelter(**data)


def test_occupied_greater_than_capacity_is_rejected() -> None:
    data = _base_kwargs()
    data["capacity"] = 5
    data["occupied"] = 6
    with pytest.raises(ValidationError):
        Shelter(**data)


def test_available_spaces_is_calculated() -> None:
    shelter = Shelter(**_base_kwargs())
    assert shelter.available_spaces == 60