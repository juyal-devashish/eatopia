from fastapi.testclient import TestClient

from app.health.members import MEMBER_IDS, load_member
from app.main import create_app

client = TestClient(create_app())


def test_form_returns_screens_for_the_mode() -> None:
    response = client.get("/form", params={"mode": "health_first"})

    assert response.status_code == 200
    body = response.json()
    ids = [screen["id"] for screen in body["screens"]]
    assert body["mode"] == "health_first"
    assert "health_review" in ids
    assert "health_permission_late" not in ids
    assert len(body["sections"]) == 7


def test_form_rejects_an_unknown_mode() -> None:
    assert client.get("/form", params={"mode": "fastest"}).status_code == 422


def test_condition_catalog_is_served() -> None:
    body = client.get("/catalog/conditions").json()

    assert len(body["conditions"]) >= 30


def test_members_list_shows_labels_but_no_health_values() -> None:
    response = client.get("/members")

    assert [m["id"] for m in response.json()] == list(MEMBER_IDS)
    for member_id in MEMBER_IDS:
        for canary in load_member(member_id).canary_values:
            assert canary not in response.text
