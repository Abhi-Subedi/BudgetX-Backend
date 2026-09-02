from datetime import date

from tests.conftest import get_categories, register_and_login


def _make_budget(client, headers, amounts_by_cat):
    month = date.today().replace(day=1).isoformat()
    items = [{"category_id": cid, "amount": amt} for cid, amt in amounts_by_cat.items()]
    return client.post("/api/budgets", headers=headers, json={"name": "August", "month": month, "items": items})


def test_budget_create_progress_update_delete(client):
    auth = register_and_login(client)
    h = auth["headers"]
    cats = get_categories(client, h)
    accounts = client.get("/api/accounts", headers=h).json()["items"]

    food, transport = cats[0], cats[1]
    response = _make_budget(client, h, {food["id"]: 500, transport["id"]: 200})
    assert response.status_code == 201

    duplicate = _make_budget(client, h, {food["id"]: 100})
    assert duplicate.status_code == 409

    income_only = client.post(
        "/api/budgets",
        headers=h,
        json={"month": "2026-09-01", "items": [{"category_id": 0, "amount": 1}]},
    )
    assert income_only.status_code in (404, 422)

    listed = client.get("/api/budgets", headers=h).json()["items"]
    assert len(listed) == 1
    budget = listed[0]
    assert budget["total_budget"] == 700

    for item in budget["items"]:
        assert item["spent"] == 0
        assert item["pct_used"] == 0

    client.post(
        "/api/transactions",
        headers=h,
        json={"amount": 400, "type": "expense", "account_id": accounts[0]["id"], "category_id": food["id"], "occurred_at": date.today().isoformat()},
    )
    listed2 = client.get("/api/budgets", headers=h).json()["items"][0]
    food_item = next(i for i in listed2["items"] if i["category_id"] == food["id"])
    assert food_item["spent"] == 400
    assert food_item["pct_used"] == 80.0
    assert abs(food_item["remaining"] - 100) < 0.01

    updated = client.put(
        f"/api/budgets/{listed2['id']}",
        headers=h,
        json={"items": [{"category_id": food["id"], "amount": 800}]},
    )
    assert updated.status_code == 200
    listed3 = client.get("/api/budgets", headers=h).json()["items"][0]
    assert listed3["total_budget"] == 800

    deleted = client.delete(f"/api/budgets/{listed3['id']}", headers=h)
    assert deleted.status_code == 204
    assert client.get("/api/budgets", headers=h).json()["items"] == []


def test_income_category_rejected_in_budget(client):
    auth = register_and_login(client)
    h = auth["headers"]
    salary = get_categories(client, h, "income")[0]
    bad = client.post(
        "/api/budgets",
        headers=h,
        json={"month": date.today().replace(day=1).isoformat(), "items": [{"category_id": salary["id"], "amount": 1000}]},
    )
    assert bad.status_code == 422


def test_budget_isolation_between_users(client):
    owner = register_and_login(client)
    intruder = register_and_login(client, name="Mia", email="mia@example.com")
    cats = get_categories(client, owner["headers"])
    created = _make_budget(client, owner["headers"], {cats[0]["id"]: 300})
    assert created.status_code == 201

    other_list = client.get("/api/budgets", headers=intruder["headers"]).json()
    assert other_list["items"] == []
