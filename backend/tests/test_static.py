from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from veshichkin.core.config import Settings
from veshichkin.main import create_app


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    (tmp_path / "index.html").write_text("<!doctype html><html>SPA entrypoint</html>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('asset');")
    return tmp_path


def test_spa_routes_and_assets(static_dir: Path) -> None:
    with TestClient(create_app(Settings(static_dir=static_dir))) as client:
        for path in ("/", "/catalog"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.text == (static_dir / "index.html").read_text()
            assert response.headers["content-type"].startswith("text/html")
        asset = client.get("/assets/app.js")
        assert asset.status_code == 200
        assert asset.text == "console.log('asset');"
        assert "javascript" in asset.headers["content-type"]
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/api/health").status_code == 200
        for path in ("/api", "/api/nonexistent", "/assets/missing.js", "/missing.js"):
            response = client.get(path)
            assert response.status_code == 404
            assert response.json() == {"detail": "Not Found"}


def test_development_without_static_serving() -> None:
    with TestClient(create_app(Settings(static_dir=None))) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/").status_code == 404
        assert client.get("/catalog").status_code == 404


def test_static_routes_do_not_change_openapi(static_dir: Path) -> None:
    assert create_app(Settings(static_dir=static_dir)).openapi() == create_app(
        Settings(static_dir=None)
    ).openapi()
