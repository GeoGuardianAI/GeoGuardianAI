"""Unit tests for the hospital service.

Tests validate nearest hospital selection, input validation, boundary handling,
and the private Haversine helper.
"""

import math

import pytest

from backend.rescue.models.hospital import Hospital
from backend.rescue.services import hospital_service


def test_get_nearest_hospital_returns_hospital_instance() -> None:
    result = hospital_service.get_nearest_hospital(12.9716, 77.5946)
    assert isinstance(result, Hospital)


def test_get_nearest_hospital_returns_correct_nearest_hospital() -> None:
    result = hospital_service.get_nearest_hospital(12.9716, 77.5946)
    assert result.hospital_id == "blr-central-test"


def test_get_nearest_hospital_returns_different_hospitals_for_different_locations() -> None:
    first = hospital_service.get_nearest_hospital(12.9716, 77.5946)
    second = hospital_service.get_nearest_hospital(12.9698, 77.7499)
    assert first.hospital_id != second.hospital_id
    assert first.hospital_id == "blr-central-test"
    assert second.hospital_id == "blr-whitefield-test"


@pytest.mark.parametrize("latitude", [-90.1, 90.1])
def test_get_nearest_hospital_rejects_invalid_latitude(latitude: float) -> None:
    with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
        hospital_service.get_nearest_hospital(latitude, -100.0)


@pytest.mark.parametrize("longitude", [-180.1, 180.1])
def test_get_nearest_hospital_rejects_invalid_longitude(longitude: float) -> None:
    with pytest.raises(ValueError, match="longitude must be between -180 and 180"):
        hospital_service.get_nearest_hospital(0.0, longitude)


@pytest.mark.parametrize(
    "latitude, longitude",
    [(-90.0, 0.0), (90.0, 0.0), (0.0, -180.0), (0.0, 180.0)],
)
def test_get_nearest_hospital_accepts_boundary_coordinates(latitude: float, longitude: float) -> None:
    result = hospital_service.get_nearest_hospital(latitude, longitude)
    assert isinstance(result, Hospital)


def test_haversine_helper_knows_zero_distance_and_simple_quarter_earth_distance() -> None:
    zero_distance = hospital_service._haversine_km(0.0, 0.0, 0.0, 0.0)
    assert zero_distance == 0.0

    expected_quarter = math.pi / 2 * 6371.0
    actual_quarter = hospital_service._haversine_km(0.0, 0.0, 0.0, 90.0)
    assert math.isclose(actual_quarter, expected_quarter, rel_tol=1e-9)
