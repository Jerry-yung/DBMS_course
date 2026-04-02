"""集成测试：需要本机 MongoDB 与 app 配置一致。未启动时自动跳过。"""

import uuid

import pytest
from pymongo.errors import ServerSelectionTimeoutError
from pymongo import MongoClient

from app.core.config import settings


def _mongo_available():
    try:
        c = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=1500)
        c.admin.command("ping")
        c.close()
        return True
    except (ServerSelectionTimeoutError, Exception):
        return False


pytestmark = pytest.mark.skipif(
    not _mongo_available(),
    reason="MongoDB 不可用，跳过集成测试",
)


from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_register_create_publish_fill_stats(client):
    u = "u_" + uuid.uuid4().hex[:8]
    p = "secret12"
    r = client.post(
        "/api/v1/auth/register", json={"username": u, "password": p}
    )
    assert r.status_code == 200
    r = client.post("/api/v1/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200
    token = r.json()["data"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/api/v1/surveys",
        json={"title": "T", "description": "D"},
        headers=h,
    )
    assert r.status_code == 200
    sid = r.json()["data"]["id"]

    r = client.post(
        f"/api/v1/surveys/{sid}/questions",
        json={
            "title": "Q1",
            "type": "single_choice",
            "required": True,
            "options": [{"value": "A", "label": "A", "order": 0}],
        },
        headers=h,
    )
    assert r.status_code == 200

    r = client.post(f"/api/v1/surveys/{sid}/publish", headers=h)
    assert r.status_code == 200
    code = r.json()["data"]["short_code"]

    r = client.get(f"/api/v1/public/surveys/{code}")
    assert r.status_code == 200

    session_id = str(uuid.uuid4())
    r = client.get(
        f"/api/v1/public/surveys/{code}/next",
        params={"session_id": session_id},
    )
    assert r.status_code == 200
    qid = r.json()["data"]["next_question"]["id"]

    r = client.post(
        f"/api/v1/public/surveys/{code}/answer",
        json={"session_id": session_id, "question_id": qid, "value": "A"},
    )
    assert r.status_code == 200

    r = client.post(
        f"/api/v1/public/surveys/{code}/submit",
        json={"session_id": session_id},
    )
    assert r.status_code == 200

    r = client.get(f"/api/v1/surveys/{sid}/statistics", headers=h)
    assert r.status_code == 200
    assert r.json()["data"]["total_responses"] >= 1
