"""End-to-end checks for real workspaces and tenant isolation."""

import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./data/test_multitenant.db"
os.environ["POSTGRES_URL"] = ""

from fastapi.testclient import TestClient

from app.auth import AuthUser, optional_current_user, require_current_user
from app.database import engine
from app.main import app


TEST_DB = Path("data/test_multitenant.db")


def run() -> None:
    TEST_DB.unlink(missing_ok=True)
    current = {"user": None}

    def optional_user():
        return current["user"]

    def required_user():
        assert current["user"] is not None
        return current["user"]

    app.dependency_overrides[optional_current_user] = optional_user
    app.dependency_overrides[require_current_user] = required_user

    with TestClient(app) as client:
        public = client.get("/api/dashboard")
        assert public.status_code == 200 and public.json()["is_demo"] is True

        current["user"] = AuthUser("user-one", "one@example.com")
        created = client.post("/api/workspace", json={
            "brand_name": "Real Brand", "website": "https://real.example",
            "competitor_names": ["Rival One"],
        })
        assert created.status_code == 200
        dashboard = client.get("/api/dashboard").json()
        assert dashboard["is_demo"] is False
        assert dashboard["summary"]["competitors"] == 2
        assert dashboard["summary"]["posts"] == 0

        current["user"] = AuthUser("user-two", "two@example.com")
        assert client.get("/api/dashboard").status_code == 404
        assert client.post("/api/workspace", json={"brand_name": "Real Brand"}).status_code == 200
        names = [item["name"] for item in client.get("/competitors").json()]
        assert names == ["Real Brand"]

    app.dependency_overrides.clear()
    engine.dispose()
    TEST_DB.unlink(missing_ok=True)
    print("multitenant checks passed")


if __name__ == "__main__":
    run()
