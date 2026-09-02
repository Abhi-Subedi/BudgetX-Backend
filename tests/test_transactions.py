from tests.conftest import get_categories, register_and_login


def _create_txn(client, headers, account_id, category_id, amount, type_="expense", day=5):
    return client.post(
        "/api/transactions",
        headers=headers,
        json={
            "amount": amount,
            "type": type_,
            "account_id": account_id,
            "category_id": category_id,
            "occurred_at": f"2026-08-{day:02d}",
            "payee": "Test Merchant",
        },
    )


def test_accounts_crud_and_balance(client):
    auth = register_and_login(client)
    h = auth["headers"]

    accounts = client.get("/api/accounts", headers=h).json()["items"]
    cash_id = accounts[0]["id"]

    created = client.post(
        "/api/accounts",
        headers=h,
        json={"name": "Salary Bank", "type": "bank", "opening_balance": 1000},
    )
    assert created.status_code == 201
    bank = created.json()
    assert bank["balance"] == 1000

    categories = get_categories(client, h, "expense")
    salary_cat = get_categories(client, h, "income")[0]

    r1 = _create_txn(client, h, bank["id"], categories[0]["id"], 250.50)
    assert r1.status_code == 201
    r2 = _create_txn(client, h, bank["id"], salary_cat["id"], 4000, type_="income")
    assert r2.status_code == 201

    refreshed = client.get(f"/api/accounts", headers=h).json()
    by_name = {a["name"]: a for a in refreshed["items"]}
    assert abs(by_name["Salary Bank"]["balance"] - (1000 - 250.50 + 4000)) < 0.01
    assert refreshed["total_balance"] > 0


def test_account_delete_blocked_with_transactions(client):
    auth = register_and_login(client)
    h = auth["headers"]
    accounts = client.get("/api/accounts", headers=h).json()["items"]
    cat = get_categories(client, h)[0]
    _create_txn(client, h, accounts[0]["id"], cat["id"], 10)
    response = client.delete(f"/api/accounts/{accounts[0]['id']}", headers=h)
    assert response.status_code == 409


def test_transaction_validation_and_filters(client):
    auth = register_and_login(client)
    h = auth["headers"]
    accounts = client.get("/api/accounts", headers=h).json()["items"]
    cats = get_categories(client, h)

    bad = client.post(
        "/api/transactions",
        headers=h,
        json={"amount": -5, "type": "expense", "account_id": accounts[0]["id"], "occurred_at": "2026-08-01"},
    )
    assert bad.status_code == 422

    foreign_cat = client.post(
        "/api/transactions",
        headers=h,
        json={"amount": 10, "type": "expense", "account_id": accounts[0]["id"], "category_id": 99999, "occurred_at": "2026-08-01"},
    )
    assert foreign_cat.status_code == 404

    _create_txn(client, h, accounts[0]["id"], cats[0]["id"], 120, day=2)
    _create_txn(client, h, accounts[0]["id"], cats[1]["id"], 80, day=3)

    listed = client.get("/api/transactions", headers=h).json()
    assert listed["total"] == 2
    assert float(listed["items"][0]["amount"]) == 80

    filtered = client.get(
        "/api/transactions", headers=h, params={"category_id": cats[0]["id"]}
    ).json()
    assert filtered["total"] == 1
    assert float(filtered["items"][0]["amount"]) == 120

    searched = client.get("/api/transactions", headers=h, params={"q": "Merchant"}).json()
    assert searched["total"] == 2


def test_update_and_delete_transaction(client):
    auth = register_and_login(client)
    h = auth["headers"]
    accounts = client.get("/api/accounts", headers=h).json()["items"]
    cat = get_categories(client, h)[0]

    txn_id = _create_txn(client, h, accounts[0]["id"], cat["id"], 100).json()["id"]
    updated = client.put(
        f"/api/transactions/{txn_id}",
        headers=h,
        json={"amount": 150.75, "note": "Updated note"},
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == 150.75
    assert updated.json()["note"] == "Updated note"

    deleted = client.delete(f"/api/transactions/{txn_id}", headers=h)
    assert deleted.status_code == 204
    missing = client.get(f"/api/transactions/{txn_id}", headers=h)
    assert missing.status_code == 404


def test_cross_user_access_denied(client):
    owner = register_and_login(client)
    other = register_and_login(client, name="Ravi", email="ravi@example.com")
    accounts = client.get("/api/accounts", headers=owner["headers"]).json()["items"]
    cat = get_categories(client, owner["headers"])[0]
    txn_id = _create_txn(client, owner["headers"], accounts[0]["id"], cat["id"], 42).json()["id"]

    peek = other and client.get(f"/api/transactions/{txn_id}", headers=other["headers"])
    assert peek.status_code == 404

    hijack = client.put(
        f"/api/transactions/{txn_id}",
        headers=other["headers"],
        json={"amount": 999},
    )
    assert hijack.status_code == 404
