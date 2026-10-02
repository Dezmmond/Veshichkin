from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.test_category_reference_integration import test_engine as test_engine
from veshichkin.db.models import MeasurementProfile
from veshichkin.db.session import get_session
from veshichkin.main import create_app
from veshichkin.profile import operations
from veshichkin.profile.schemas import MEASUREMENT_FIELDS

PATH = "/api/profile/measurements"


@pytest.fixture
def profile_client(test_engine: Engine) -> Iterator[tuple[TestClient, Engine]]:
    def clear_profile() -> None:
        with Session(test_engine) as session:
            session.execute(delete(MeasurementProfile))
            session.commit()

    clear_profile()
    app = create_app()

    def request_session() -> Iterator[Session]:
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = request_session
    try:
        with TestClient(app) as client:
            yield client, test_engine
    finally:
        clear_profile()


def assert_count(engine: Engine, count: int) -> None:
    with Session(engine) as fresh:
        assert fresh.scalar(select(func.count()).select_from(MeasurementProfile)) == count


def test_empty_get_does_not_create_profile(profile_client: tuple[TestClient, Engine]) -> None:
    client, engine = profile_client
    for _ in range(2):
        response = client.get(PATH)
        assert response.status_code == 200 and response.json() is None
        assert_count(engine, 0)


@pytest.mark.parametrize("field", MEASUREMENT_FIELDS)
def test_first_patch_creates_singleton_and_persists_one_measurement(
    profile_client: tuple[TestClient, Engine], field: str
) -> None:
    client, engine = profile_client
    response = client.patch(PATH, json={field: 178.25})
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {*MEASUREMENT_FIELDS, "extra_measurements", "updated_at"}
    assert Decimal(data[field]) == Decimal("178.25")
    assert all(data[other] is None for other in MEASUREMENT_FIELDS if other != field)
    assert data["extra_measurements"] == {} and data["updated_at"]
    assert client.get(PATH).json() == data
    with Session(engine) as fresh:
        stored = fresh.get(MeasurementProfile, 1)
        assert stored is not None and getattr(stored, field) == Decimal("178.25")
        assert all(getattr(stored, other) is None for other in MEASUREMENT_FIELDS if other != field)
        assert stored.extra_measurements == {}
    assert_count(engine, 1)


def test_empty_patch_creates_then_is_noop(profile_client: tuple[TestClient, Engine]) -> None:
    client, engine = profile_client
    response = client.patch(PATH, json={})
    assert response.status_code == 200
    data = response.json()
    assert all(data[field] is None for field in MEASUREMENT_FIELDS)
    assert data["extra_measurements"] == {}
    assert client.patch(PATH, json={}).json() == data
    assert client.get(PATH).json() == data
    assert_count(engine, 1)


def test_partial_update_omission_null_and_singleton(
    profile_client: tuple[TestClient, Engine],
) -> None:
    client, engine = profile_client
    values = {field: Decimal("50.25") + index for index, field in enumerate(MEASUREMENT_FIELDS)}
    first = client.patch(PATH, json={field: str(value) for field, value in values.items()})
    assert first.status_code == 200
    changed = client.patch(PATH, json={"weight_kg": "75.50"})
    assert changed.status_code == 200
    for field, value in values.items():
        assert Decimal(changed.json()[field]) == (
            Decimal("75.50") if field == "weight_kg" else value
        )
    cleared = client.patch(PATH, json={"weight_kg": None})
    assert cleared.status_code == 200 and cleared.json()["weight_kg"] is None
    assert client.patch(PATH, json={}).json() == cleared.json()
    with Session(engine) as fresh:
        stored = fresh.get(MeasurementProfile, 1)
        assert stored is not None and stored.weight_kg is None
        for field, value in values.items():
            if field != "weight_kg":
                assert getattr(stored, field) == value
    assert_count(engine, 1)


def test_extra_measurements_replace_clear_and_omission(
    profile_client: tuple[TestClient, Engine],
) -> None:
    client, engine = profile_client
    attributes = {"neck_cm": 39, "shoulder_width_cm": 47, "nested": {"left": True}}
    first = client.patch(PATH, json={"height_cm": 180, "extra_measurements": attributes})
    assert first.status_code == 200 and first.json()["extra_measurements"] == attributes
    omitted = client.patch(PATH, json={"chest_cm": 95})
    assert omitted.json()["extra_measurements"] == attributes
    replaced = client.patch(PATH, json={"extra_measurements": {"neck_cm": 40}})
    assert replaced.status_code == 200 and replaced.json()["extra_measurements"] == {"neck_cm": 40}
    with Session(engine) as fresh:
        assert fresh.get(MeasurementProfile, 1).extra_measurements == {"neck_cm": 40}
    cleared = client.patch(PATH, json={"extra_measurements": {}})
    assert cleared.status_code == 200 and cleared.json()["extra_measurements"] == {}
    assert Decimal(cleared.json()["height_cm"]) == Decimal("180.00")
    with Session(engine) as fresh:
        assert fresh.get(MeasurementProfile, 1).extra_measurements == {}
    assert_count(engine, 1)


@pytest.mark.parametrize(
    "value,expected", [("0.005", "0.01"), ("39.125", "39.13"), ("9999.99", "9999.99")]
)
def test_decimal_rounding_and_range_boundary(
    profile_client: tuple[TestClient, Engine], value: str, expected: str
) -> None:
    client, engine = profile_client
    response = client.patch(PATH, json={"height_cm": value})
    assert response.status_code == 200 and Decimal(response.json()["height_cm"]) == Decimal(
        expected
    )
    with Session(engine) as fresh:
        assert fresh.get(MeasurementProfile, 1).height_cm == Decimal(expected)


@pytest.mark.parametrize(
    "payload",
    [
        {"height_cm": 0},
        {"height_cm": -1},
        {"height_cm": 10000},
        {"height_cm": True},
        {"height_cm": "NaN"},
        {"height_cm": "Infinity"},
        {"height_cm": "0.001"},
        {"extra_measurements": None},
        {"extra_measurements": []},
    ],
)
def test_invalid_patch_is_422_without_creating_or_mutating(
    profile_client: tuple[TestClient, Engine], payload: dict
) -> None:
    client, engine = profile_client
    assert client.patch(PATH, json=payload).status_code == 422
    assert_count(engine, 0)
    original = client.patch(PATH, json={"height_cm": 180, "weight_kg": 75}).json()
    assert client.patch(PATH, json=payload).status_code == 422
    assert client.get(PATH).json() == original
    assert_count(engine, 1)


def test_updated_at_changes_and_noop_keeps_timestamp(
    profile_client: tuple[TestClient, Engine],
) -> None:
    client, engine = profile_client
    # A fixed earlier timestamp avoids timing sleeps and precision-sensitive assertions.
    earlier = datetime(2000, 1, 1, tzinfo=UTC)
    with Session(engine) as session:
        session.add(MeasurementProfile(id=1, height_cm=Decimal("170.00"), updated_at=earlier))
        session.commit()
    before = client.get(PATH).json()
    changed = client.patch(PATH, json={"height_cm": 175})
    assert changed.status_code == 200 and changed.json()["updated_at"] != before["updated_at"]
    with Session(engine) as fresh:
        assert fresh.get(MeasurementProfile, 1).updated_at > earlier
    assert client.patch(PATH, json={}).json() == changed.json()
    assert client.patch(PATH, json={"height_cm": 175}).json() == changed.json()


@pytest.mark.parametrize("existing", [False, True])
def test_failure_after_flush_rolls_back_create_or_update(
    profile_client: tuple[TestClient, Engine], existing: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, engine = profile_client
    original = None
    if existing:
        original = client.patch(
            PATH, json={"height_cm": 170, "extra_measurements": {"neck_cm": 39}}
        ).json()
    patch = operations.patch_measurements

    def fail_after_flush(session, payload):
        patch(session, payload)
        raise IntegrityError("secret SQL", {}, Exception("secret constraint"))

    monkeypatch.setattr(operations, "patch_measurements", fail_after_flush)
    response = client.patch(PATH, json={"height_cm": 180, "extra_measurements": {"neck_cm": 40}})
    assert (
        response.status_code == 500 and response.json()["error"]["code"] == "profile_write_failed"
    )
    assert "secret" not in response.text
    assert client.get(PATH).json() == original
    assert_count(engine, 1 if existing else 0)
