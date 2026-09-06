"""Unit tests for the shelter service."""

import pytest

from backend.rescue.models.shelter import Shelter
from backend.rescue.services import shelter_service


def test_get_nearest_shelter_returns_nearest_suitable_shelter() -> None:
    result = shelter_service.get_nearest_shelter(40.730610, -73.935242)
    assert isinstance(result, Shelter)
    assert result.shelter_id == "shelter-nyc-01"


def test_unavailable_shelters_are_ignored() -> None:
    result = shelter_service.get_nearest_shelter(41.8781, -87.6298)
    assert result.shelter_id != "shelter-chi-01"
    assert result.emergency_available is True


def test_full_shelters_are_ignored() -> None:
    result = shelter_service.get_nearest_shelter(34.0522, -118.2437)
    assert result.shelter_id != "shelter-la-01"
    assert result.available_spaces > 0


@pytest.mark.parametrize("latitude", [-90.1, 90.1])
def test_get_nearest_shelter_rejects_invalid_latitude(latitude: float) -> None:
    with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
        shelter_service.get_nearest_shelter(latitude, -100.0)


@pytest.mark.parametrize("longitude", [-180.1, 180.1])
def test_get_nearest_shelter_rejects_invalid_longitude(longitude: float) -> None:
    with pytest.raises(ValueError, match="longitude must be between -180 and 180"):
        shelter_service.get_nearest_shelter(0.0, longitude)


def test_no_suitable_shelter_available_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shelter_service, "_SHELTERS", [])
    with pytest.raises(ValueError, match="no suitable shelter available"):
        shelter_service.get_nearest_shelter(0.0, 0.0)


def test_get_nearest_shelter_is_deterministic() -> None:
    first = shelter_service.get_nearest_shelter(40.730610, -73.935242)
    second = shelter_service.get_nearest_shelter(40.730610, -73.935242)
    assert first.shelter_id == second.shelter_id