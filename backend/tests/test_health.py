from collections.abc import Iterator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from veshichkin.db import session as db
from veshichkin.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_does_not_access_database(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_on_database_access() -> None:
        pytest.fail("Liveness must not access the database")

    app.dependency_overrides[db.get_session] = fail_on_database_access
    monkeypatch.setattr(db.engine, "connect", fail_on_database_access)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_success(client: TestClient) -> None:
    session = Mock(spec=Session)
    app.dependency_overrides[db.get_session] = lambda: session
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    session.execute.assert_called_once()
    assert str(session.execute.call_args.args[0]) == "SELECT 1"


@pytest.mark.parametrize("debug", [False, True])
def test_ready_failure_has_safe_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, debug: bool
) -> None:
    monkeypatch.setattr(app, "debug", debug)
    session = Mock(spec=Session)
    session.execute.side_effect = OperationalError(
        "SELECT 1", {}, Exception("postgresql+psycopg://secret_user:secret_password@private/db")
    )
    app.dependency_overrides[db.get_session] = lambda: session
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "database_unavailable", "message": "Database is unavailable"}
    }
    for detail in ("secret_user", "secret_password", "private", "Traceback", "SELECT 1"):
        assert detail not in response.text
    assert client.get("/api/health").status_code == 200


@pytest.mark.parametrize("endpoint_fails", [False, True])
def test_session_dependency_closes_session(
    monkeypatch: pytest.MonkeyPatch, endpoint_fails: bool
) -> None:
    session = Session(bind=db.engine)
    close = Mock(wraps=session.close)
    monkeypatch.setattr(session, "close", close)
    monkeypatch.setattr(db, "SessionLocal", lambda: session)
    dependency = db.get_session()
    assert next(dependency) is session
    if endpoint_fails:
        with pytest.raises(RuntimeError, match="endpoint failure"):
            dependency.throw(RuntimeError("endpoint failure"))
    else:
        with pytest.raises(StopIteration):
            next(dependency)
    close.assert_called_once()
