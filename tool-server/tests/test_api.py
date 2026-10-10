"""API tests using a fake generator (no model download needed)."""

import os

os.environ.setdefault("TOOL_API_KEY", "test-key")

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings, get_settings
from app.main import app

AUTH = {"Authorization": "Bearer test-key"}


class FakeGenerator:
    def start(self): ...
    def stop(self): ...

    def generate(self, prompt, negative_prompt, width, height, steps, seed):
        return Image.new("RGB", (width, height), "teal"), seed or 123


@pytest.fixture
def client(tmp_path):
    settings = Settings(tool_api_key="test-key", image_dir=tmp_path, public_base_url="http://t")
    app.dependency_overrides[get_settings] = lambda: settings
    app.state.generator = FakeGenerator()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_is_open(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_generate_requires_key(client):
    assert client.post("/generate_image", json={"prompt": "a cat"}).status_code == 401
    bad = client.post("/generate_image", json={"prompt": "a cat"}, headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401


def test_generate_and_fetch_image(client):
    r = client.post("/generate_image", json={"prompt": "a cat"}, headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    assert data["image_url"].startswith("http://t/images/")
    assert data["markdown"].startswith("![a cat](http://t/images/")

    name = data["image_url"].rsplit("/", 1)[1]
    img = client.get(f"/images/{name}")  # no auth needed, URL is the capability
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"


def test_rejects_bad_dimensions(client):
    r = client.post("/generate_image", json={"prompt": "x", "width": 1000}, headers=AUTH)
    assert r.status_code == 422


@pytest.mark.parametrize("name", ["../etc/passwd", "short.png", "A" * 22 + ".txt", "..%2f..%2fetc"])
def test_image_name_validation(client, name):
    assert client.get(f"/images/{name}").status_code == 404


def test_openapi_declares_bearer_auth_and_operation_id(client):
    spec = client.get("/openapi.json").json()
    assert spec["paths"]["/generate_image"]["post"]["operationId"] == "generate_image"
    assert spec["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
