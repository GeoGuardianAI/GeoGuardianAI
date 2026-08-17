"""Unit tests for the mock routing service."""

import math

import pytest
from pydantic import ValidationError

from backend.rescue.models.route import RouteRequest, RouteResponse, RouteStatus
from backend.rescue.services.routing_service import (
    DEFAULT_AVERAGE_SPEED_KMH,
    DEFAULT_RISK_BASELINE,
    MockRoutingService,
    RoutingServiceConfig,
    calculate_route,
)
from backend.rescue.utils.geo import haversine_km


def _valid_request(**overrides: object) -> RouteRequest:
    data: dict[str, object] = {
        "origin_latitude": 40.7128,
        "origin_longitude": -74.0060,
        "destination_latitude": 34.0522,
        "destination_longitude": -118.2437,
        "disaster_id": "disaster-001",
    }
    data.update(overrides)
    return RouteRequest(**data)


def test_calculate_route_accepts_a_valid_route_request() -> None:
    request = _valid_request()
    response = calculate_route(request)

    assert isinstance(response, RouteResponse)


def test_calculate_route_returns_a_route_response_instance() -> None:
    response = calculate_route(_valid_request())

    assert isinstance(response, RouteResponse)


def test_zero_distance_route_produces_distance_km_zero() -> None:
    request = _valid_request(
        origin_latitude=40.7128,
        origin_longitude=-74.0060,
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    response = calculate_route(request)

    assert response.distance_km == 0


def test_zero_distance_route_produces_estimated_duration_minutes_zero() -> None:
    request = _valid_request(
        origin_latitude=40.7128,
        origin_longitude=-74.0060,
        destination_latitude=40.7128,
        destination_longitude=-74.0060,
    )

    response = calculate_route(request)

    assert response.estimated_duration_minutes == 0


def test_known_coordinate_pair_produces_positive_geographic_distance() -> None:
    request = _valid_request(
        origin_latitude=40.7128,
        origin_longitude=-74.0060,
        destination_latitude=34.0522,
        destination_longitude=-118.2437,
    )

    response = calculate_route(request)

    assert response.distance_km > 0


def test_estimated_duration_follows_configured_average_speed() -> None:
    request = _valid_request(
        origin_latitude=0.0,
        origin_longitude=0.0,
        destination_latitude=0.0,
        destination_longitude=1.0,
    )

    response = calculate_route(request, average_speed_kmh=60.0)
    expected = (response.distance_km / 60.0) * 60.0

    assert response.estimated_duration_minutes == pytest.approx(expected)


def test_default_average_speed_of_35_kmh_is_used() -> None:
    request = _valid_request(
        origin_latitude=0.0,
        origin_longitude=0.0,
        destination_latitude=0.0,
        destination_longitude=1.0,
    )

    distance = haversine_km(0.0, 0.0, 0.0, 1.0)
    expected = round((distance / DEFAULT_AVERAGE_SPEED_KMH) * 60.0, 2)

    response = calculate_route(request)

    assert response.estimated_duration_minutes == pytest.approx(expected)


def test_custom_average_speed_kmh_changes_estimated_duration() -> None:
    request = _valid_request(
        origin_latitude=0.0,
        origin_longitude=0.0,
        destination_latitude=0.0,
        destination_longitude=1.0,
    )

    slow = calculate_route(request, average_speed_kmh=10.0)
    fast = calculate_route(request, average_speed_kmh=100.0)

    assert slow.estimated_duration_minutes > fast.estimated_duration_minutes


def test_route_risk_score_is_between_zero_and_one() -> None:
    response = calculate_route(_valid_request())

    assert 0.0 <= response.route_risk_score <= 1.0


def test_risk_increases_as_distance_increases() -> None:
    short = calculate_route(_valid_request(
        origin_latitude=40.7128,
        origin_longitude=-74.0060,
        destination_latitude=40.7128,
        destination_longitude=-74.0061,
    ))
    long = calculate_route(_valid_request(
        origin_latitude=40.7128,
        origin_longitude=-74.0060,
        destination_latitude=34.0522,
        destination_longitude=-118.2437,
    ))

    assert long.route_risk_score > short.route_risk_score


def test_risk_is_capped_at_one() -> None:
    far_request = _valid_request(
        origin_latitude=0.0,
        origin_longitude=0.0,
        destination_latitude=89.0,
        destination_longitude=179.0,
    )

    response = calculate_route(far_request)

    assert response.route_risk_score <= 1.0


def test_low_risk_routes_return_route_status_ok() -> None:
    request = _valid_request(
        origin_latitude=40.7128,
        origin_longitude=-74.0060,
        destination_latitude=40.7128,
        destination_longitude=-74.0061,
    )

    response = calculate_route(request)

    assert response.route_status == RouteStatus.OK


def test_high_risk_routes_return_route_status_caution() -> None:
    request = _valid_request(
        origin_latitude=0.0,
        origin_longitude=0.0,
        destination_latitude=89.0,
        destination_longitude=179.0,
    )

    response = calculate_route(request)

    assert response.route_status == RouteStatus.CAUTION


def test_response_contains_non_empty_explanation() -> None:
    response = calculate_route(_valid_request())

    assert isinstance(response.explanation, str)
    assert response.explanation.strip() != ""


def test_explanation_identifies_deterministic_mock_routing_calculation() -> None:
    response = calculate_route(_valid_request())

    assert "Development/mock routing provider" in response.explanation
    assert "deterministic" in response.explanation.lower()


def test_valid_disaster_id_in_route_request_is_accepted() -> None:
    request = _valid_request(disaster_id="incident-42")

    response = calculate_route(request)

    assert response is not None
    assert request.disaster_id == "incident-42"


def test_invalid_geographic_coordinates_are_rejected_by_route_request() -> None:
    with pytest.raises(ValidationError):
        RouteRequest(
            origin_latitude=91.0,
            origin_longitude=0.0,
            destination_latitude=0.0,
            destination_longitude=0.0,
        )

    with pytest.raises(ValidationError):
        RouteRequest(
            origin_latitude=0.0,
            origin_longitude=-181.0,
            destination_latitude=0.0,
            destination_longitude=0.0,
        )


def test_same_route_request_produces_deterministic_results_across_repeated_calls() -> None:
    request = _valid_request()

    first = calculate_route(request)
    second = calculate_route(request)

    assert first == second


def test_custom_routing_service_config_can_be_used_with_mock_routing_service() -> None:
    config = RoutingServiceConfig(average_speed_kmh=40.0, risk_baseline=0.20)
    service = MockRoutingService(config)

    response = service.route(_valid_request())

    assert isinstance(response, RouteResponse)
    assert response.route_status in {RouteStatus.OK, RouteStatus.CAUTION}


def test_configured_risk_baseline_affects_resulting_risk_score() -> None:
    request = _valid_request(
        origin_latitude=0.0,
        origin_longitude=0.0,
        destination_latitude=0.0,
        destination_longitude=10.0,
    )

    baseline_default = calculate_route(request)
    baseline_custom = MockRoutingService(
        RoutingServiceConfig(average_speed_kmh=35.0, risk_baseline=0.50)
    ).route(request)

    assert baseline_custom.route_risk_score > baseline_default.route_risk_score
    assert baseline_default.route_risk_score >= 0.0
    assert baseline_custom.route_risk_score <= 1.0


def test_default_risk_baseline_matches_expected_constant() -> None:
    assert DEFAULT_RISK_BASELINE == 0.15
