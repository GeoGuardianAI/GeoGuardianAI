"""Unit tests for the route request/response models."""

import pytest
from pydantic import ValidationError

from backend.rescue.models.route import RouteRequest, RouteResponse, RouteStatus


def test_route_request_valid_request_can_be_created() -> None:
    request = RouteRequest(
        origin_latitude=40.7128,
        origin_longitude=-74.0060,
        destination_latitude=34.0522,
        destination_longitude=-118.2437,
    )

    assert request.origin_latitude == 40.7128
    assert request.origin_longitude == -74.0060
    assert request.destination_latitude == 34.0522
    assert request.destination_longitude == -118.2437
    assert request.disaster_id is None


@pytest.mark.parametrize("latitude", [-90.0, 90.0])
def test_route_request_boundary_latitudes_are_accepted(latitude: float) -> None:
    request = RouteRequest(
        origin_latitude=latitude,
        origin_longitude=-74.0060,
        destination_latitude=34.0522,
        destination_longitude=-118.2437,
    )

    assert -90.0 <= request.origin_latitude <= 90.0


@pytest.mark.parametrize("longitude", [-180.0, 180.0])
def test_route_request_boundary_longitudes_are_accepted(longitude: float) -> None:
    request = RouteRequest(
        origin_latitude=40.7128,
        origin_longitude=longitude,
        destination_latitude=34.0522,
        destination_longitude=-118.2437,
    )

    assert -180.0 <= request.origin_longitude <= 180.0


def test_route_request_latitude_greater_than_90_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RouteRequest(
            origin_latitude=90.1,
            origin_longitude=-74.0060,
            destination_latitude=34.0522,
            destination_longitude=-118.2437,
        )


def test_route_request_latitude_less_than_negative_90_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RouteRequest(
            origin_latitude=-90.1,
            origin_longitude=-74.0060,
            destination_latitude=34.0522,
            destination_longitude=-118.2437,
        )


def test_route_request_longitude_greater_than_180_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RouteRequest(
            origin_latitude=40.7128,
            origin_longitude=180.1,
            destination_latitude=34.0522,
            destination_longitude=-118.2437,
        )


def test_route_request_longitude_less_than_negative_180_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RouteRequest(
            origin_latitude=40.7128,
            origin_longitude=-180.1,
            destination_latitude=34.0522,
            destination_longitude=-118.2437,
        )


def test_route_request_optional_disaster_id_can_be_omitted() -> None:
    request = RouteRequest(
        origin_latitude=40.7128,
        origin_longitude=-74.0060,
        destination_latitude=34.0522,
        destination_longitude=-118.2437,
    )

    assert request.disaster_id is None


def test_route_request_valid_disaster_id_is_accepted() -> None:
    request = RouteRequest(
        origin_latitude=40.7128,
        origin_longitude=-74.0060,
        destination_latitude=34.0522,
        destination_longitude=-118.2437,
        disaster_id="disaster-001",
    )

    assert request.disaster_id == "disaster-001"


def test_route_request_blank_disaster_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RouteRequest(
            origin_latitude=40.7128,
            origin_longitude=-74.0060,
            destination_latitude=34.0522,
            destination_longitude=-118.2437,
            disaster_id="",
        )


def test_route_request_whitespace_only_disaster_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RouteRequest(
            origin_latitude=40.7128,
            origin_longitude=-74.0060,
            destination_latitude=34.0522,
            destination_longitude=-118.2437,
            disaster_id="   ",
        )


def test_route_response_valid_response_can_be_created() -> None:
    response = RouteResponse(
        distance_km=150.25,
        estimated_duration_minutes=257.14,
        route_risk_score=0.25,
        route_status=RouteStatus.OK,
        explanation="Route is within a safe operating range for the current conditions.",
    )

    assert response.distance_km == 150.25
    assert response.estimated_duration_minutes == 257.14
    assert response.route_risk_score == 0.25
    assert response.route_status == RouteStatus.OK


def test_route_response_distance_km_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        RouteResponse(
            distance_km=-1.0,
            estimated_duration_minutes=30.0,
            route_risk_score=0.3,
            route_status=RouteStatus.OK,
            explanation="This route is safe.",
        )


def test_route_response_estimated_duration_minutes_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        RouteResponse(
            distance_km=50.0,
            estimated_duration_minutes=-1.0,
            route_risk_score=0.3,
            route_status=RouteStatus.OK,
            explanation="This route is safe.",
        )


def test_route_response_route_risk_score_cannot_be_below_zero() -> None:
    with pytest.raises(ValidationError):
        RouteResponse(
            distance_km=50.0,
            estimated_duration_minutes=30.0,
            route_risk_score=-0.1,
            route_status=RouteStatus.OK,
            explanation="This route is safe.",
        )


def test_route_response_route_risk_score_cannot_be_above_one() -> None:
    with pytest.raises(ValidationError):
        RouteResponse(
            distance_km=50.0,
            estimated_duration_minutes=30.0,
            route_risk_score=1.1,
            route_status=RouteStatus.OK,
            explanation="This route is safe.",
        )


def test_route_status_ok_is_accepted() -> None:
    response = RouteResponse(
        distance_km=50.0,
        estimated_duration_minutes=30.0,
        route_risk_score=0.2,
        route_status=RouteStatus.OK,
        explanation="This route is safe.",
    )

    assert response.route_status == RouteStatus.OK


def test_route_status_caution_is_accepted() -> None:
    response = RouteResponse(
        distance_km=50.0,
        estimated_duration_minutes=30.0,
        route_risk_score=0.8,
        route_status=RouteStatus.CAUTION,
        explanation="This route should be approached with caution.",
    )

    assert response.route_status == RouteStatus.CAUTION


def test_route_response_blank_explanation_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RouteResponse(
            distance_km=50.0,
            estimated_duration_minutes=30.0,
            route_risk_score=0.2,
            route_status=RouteStatus.OK,
            explanation="",
        )


def test_route_response_whitespace_only_explanation_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RouteResponse(
            distance_km=50.0,
            estimated_duration_minutes=30.0,
            route_risk_score=0.2,
            route_status=RouteStatus.OK,
            explanation="   ",
        )


def test_route_response_normal_explanation_is_accepted() -> None:
    response = RouteResponse(
        distance_km=50.0,
        estimated_duration_minutes=30.0,
        route_risk_score=0.2,
        route_status=RouteStatus.OK,
        explanation="This route is safe.",
    )

    assert response.explanation == "This route is safe."
