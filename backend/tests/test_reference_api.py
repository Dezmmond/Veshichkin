from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from veshichkin.db.models import Climate, Condition, Purpose
from veshichkin.db.session import get_session
from veshichkin.main import create_app


@pytest.mark.parametrize(
    "kind,model,order",
    [
        ("purposes", Purpose, "sort_order"),
        ("conditions", Condition, "rank"),
        ("climates", Climate, "sort_order"),
    ],
)
def test_reference_contract_and_order_query(kind: str, model: type, order: str) -> None:
    app = create_app()
    session = Mock(spec=Session)
    values = {"id": 7, "code": "custom", "name": "Custom", order: 2}
    if kind == "conditions":
        values["description"] = None
    session.scalars.return_value.all.return_value = [model(**values)]
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        response = client.get(f"/api/reference/{kind}")
        assert response.status_code == 200
        assert response.json() == [values]
        assert client.post(f"/api/reference/{kind}", json=values).status_code == 405
    query = str(session.scalars.call_args.args[0])
    assert f"ORDER BY {kind}.{order}, {kind}.name, {kind}.id" in query
    session.commit.assert_not_called()
