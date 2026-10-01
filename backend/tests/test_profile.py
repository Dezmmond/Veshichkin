from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veshichkin.db.models import MeasurementProfile
from veshichkin.db.session import get_session
from veshichkin.main import create_app
from veshichkin.profile.schemas import MEASUREMENT_FIELDS, MeasurementProfilePatch


@pytest.mark.parametrize("field", MEASUREMENT_FIELDS)
@pytest.mark.parametrize(
    "value", [0, -1, "10000", "9999.995", True, False, "NaN", "Infinity", "-Infinity", "0.001"]
)
def test_measurement_invalid(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        MeasurementProfilePatch.model_validate({field: value})


@pytest.mark.parametrize("field", MEASUREMENT_FIELDS)
@pytest.mark.parametrize(
    "value,expected",
    [
        (178.25, "178.25"),
        ("9999.99", "9999.99"),
        ("0.01", "0.01"),
        ("39.125", "39.13"),
        (None, None),
    ],
)
def test_measurement_positive_decimal_and_null(
    field: str, value: object, expected: str | None
) -> None:
    patch = MeasurementProfilePatch.model_validate({field: value})
    assert getattr(patch, field) == (Decimal(expected) if expected is not None else None)
    assert patch.model_fields_set == {field}


def test_optional_fields_and_extra_measurements() -> None:
    patch = MeasurementProfilePatch()
    assert all(getattr(patch, field) is None for field in MEASUREMENT_FIELDS)
    assert patch.extra_measurements == {} and patch.model_dump(exclude_unset=True) == {}
    attributes = {"neck_cm": 39, "nested": {"values": [None, True, 47]}}
    assert MeasurementProfilePatch(extra_measurements=attributes).extra_measurements == attributes
    assert MeasurementProfilePatch(extra_measurements={}).model_dump(exclude_unset=True) == {
        "extra_measurements": {}
    }


@pytest.mark.parametrize(
    "payload", [{"extra_measurements": None}, {"extra_measurements": []}, {"id": 2}, {"user_id": 1}]
)
def test_invalid_extra_and_unsupported_fields(payload: dict) -> None:
    with pytest.raises(ValidationError):
        MeasurementProfilePatch.model_validate(payload)


@pytest.fixture
def mock_client() -> Iterator[tuple[TestClient, Mock]]:
    app = create_app()
    session = Mock(spec=Session)
    session.get.return_value = MeasurementProfile(
        id=1, height_cm=Decimal("170.00"), extra_measurements={}, updated_at=datetime.now(UTC)
    )
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        yield client, session


@pytest.mark.parametrize("phase", ["flush", "commit"])
def test_unexpected_integrity_error_rolls_back_and_hides_details(
    mock_client: tuple[TestClient, Mock], phase: str
) -> None:
    client, session = mock_client
    getattr(session, phase).side_effect = IntegrityError("secret SQL", {}, Exception("constraint"))
    response = client.patch("/api/profile/measurements", json={"height_cm": 180})
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "profile_write_failed", "message": "Unable to save measurement profile"}
    }
    assert "secret" not in response.text and "constraint" not in response.text
    session.rollback.assert_called_once()


def test_openapi_profile_contract() -> None:
    schema = create_app().openapi()
    path = schema["paths"]["/api/profile/measurements"]
    assert set(path) == {"get", "patch"}
    response = path["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert {"type": "null"} in response["anyOf"]
    assert {"$ref": "#/components/schemas/MeasurementProfileResponse"} in response["anyOf"]
    patch = schema["components"]["schemas"]["MeasurementProfilePatch"]
    assert not patch.get("required")
    for field in MEASUREMENT_FIELDS:
        assert {"type": "null"} in patch["properties"][field]["anyOf"]
    assert patch["properties"]["extra_measurements"]["type"] == "object"
    assert "id" not in schema["components"]["schemas"]["MeasurementProfileResponse"]["properties"]
