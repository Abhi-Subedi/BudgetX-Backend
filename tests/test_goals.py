from datetime import date

from tests.conftest import register_and_login


def _goal(client, headers, name="Emergency Fund", target=1000):
    return client.post(
        "/api/goals",
        headers=headers,
        json={"name": name, "target_amount": target, "deadline": "2026-12-31", "color": "#0C5B45"},
    )


def test_goal_lifecycle_and_contribution(client):
    auth = register_and_login(client)
    h = auth["headers"]

    created = _goal(client, h)
    assert created.status_code == 201
    goal = created.json()
    assert goal["current_amount"] == 0

    contrib = client.post(f"/api/goals/{goal['id']}/contributions", headers=h, json={"amount": 600.55})
    assert contrib.status_code == 200
    assert contrib.json()["current_amount"] == 600.55

    client.post(f"/api/goals/{goal['id']}/contributions", headers=h, json={"amount": 399.45})
    notifications = client.get("/api/notifications", headers=h).json()
    assert any(n["type"] == "goal" for n in notifications["items"])

    renamed = client.put(
        f"/api/goals/{goal['id']}", headers=h, json={"name": "Rainy Day", "target_amount": 500}
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Rainy Day"

    deleted = client.delete(f"/api/goals/{goal['id']}", headers=h)
    assert deleted.status_code == 204


def test_goal_validation(client):
    auth = register_and_login(client)
    h = auth["headers"]
    bad = client.post("/api/goals", headers=h, json={"name": "", "target_amount": -5})
    assert bad.status_code == 422
    missing = client.post(f"/api/goals/9999/contributions", headers=h, json={"amount": 10})
    assert missing.status_code == 404
