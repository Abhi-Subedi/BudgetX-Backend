from datetime import date

from tests.conftest import get_categories, register_and_login


def _seed_activity(client, headers):
    accounts = client.get("/api/accounts", headers=headers).json()["items"]
    account_id = accounts[0]["id"]
    all_cats = get_categories(client, headers)
    food = next(c for c in all_cats if c["name"] == "Food & Drink")["id"]
    salary = next(c for c in get_categories(client, headers, "income") if c["name"] == "Salary")["id"]

    client.post(
        "/api/transactions",
        headers=headers,
        json={"amount": 5000, "type": "income", "account_id": account_id, "category_id": salary, "occurred_at": date.today().isoformat()},
    )
    for amount in (120, 80.5):
        client.post(
            "/api/transactions",
            headers=headers,
            json={"amount": amount, "type": "expense", "account_id": account_id, "category_id": food, "occurred_at": date.today().isoformat()},
        )
    return account_id, food, salary


def test_dashboard_aggregates(client):
    auth = register_and_login(client)
    h = auth["headers"]
    _seed_activity(client, h)

    dash = client.get("/api/dashboard", headers=h).json()
    assert abs(dash["balance_total"] - (5000 - 120 - 80.5)) < 0.01
    assert dash["month_totals"]["income"] == 5000
    assert abs(dash["month_totals"]["expense"] - 200.5) < 0.01
    assert abs(dash["month_totals"]["saved"] - 4799.5) < 0.01
    assert len(dash["spending_series"]) >= 28
    assert len(dash["recent_transactions"]) == 3


def test_analytics_overview_and_trends(client):
    auth = register_and_login(client)
    h = auth["headers"]
    _seed_activity(client, h)

    month_key = f"{date.today().year}-{date.today().month:02d}"
    overview = client.get(f"/api/analytics/overview?month={month_key}", headers=h).json()
    assert overview["totals"]["income"] == 5000
    assert len(overview["by_category"]) >= 1
    top = overview["by_category"][0]
    assert top["name"] == "Food & Drink"
    assert len(overview["largest_expenses"]) == 2

    trends = client.get("/api/analytics/trends?months=6", headers=h).json()["items"]
    assert len(trends) == 6
    current = trends[-1]
    assert current["expense"] > 0

    bad_month = client.get("/api/analytics/overview?month=2026-13", headers=h)
    assert bad_month.status_code == 422


def test_recurring_materializes_transactions(client):
    auth = register_and_login(client)
    h = auth["headers"]
    accounts = client.get("/api/accounts", headers=h).json()["items"]
    rent_cat = next(c for c in get_categories(client, h) if c["name"] == "Housing")

    created = client.post(
        "/api/recurring",
        headers=h,
        json={
            "amount": 900,
            "type": "expense",
            "account_id": accounts[0]["id"],
            "category_id": rent_cat["id"],
            "frequency": "monthly",
            "next_run_date": "2025-07-01",
            "payee": "Landlord",
        },
    )
    assert created.status_code == 201
    rule_id = created.json()["id"]

    dash = client.get("/api/dashboard", headers=h).json()
    txns = client.get("/api/transactions", headers=h).json()
    assert txns["total"] >= 1
    assert any(t["payee"] == "Landlord" and t["recurring_id"] == rule_id for t in txns["items"])

    notifications = client.get("/api/notifications", headers=h).json()
    assert any(n["type"] == "recurring" for n in notifications["items"])

    listed_rules = client.get("/api/recurring", headers=h).json()["items"]
    assert listed_rules[0]["next_run_date"] == "2026-09-01"

    deleted = client.delete(f"/api/recurring/{rule_id}", headers=h)
    assert deleted.status_code == 204


def test_budget_notification_on_threshold(client):
    auth = register_and_login(client)
    h = auth["headers"]
    accounts = client.get("/api/accounts", headers=h).json()["items"]
    food = get_categories(client, h)[0]
    today = date.today()

    client.post(
        "/api/budgets",
        headers=h,
        json={
            "month": date(today.year, today.month, 1).isoformat(),
            "items": [{"category_id": food["id"], "amount": 100}],
        },
    )
    client.post(
        "/api/transactions",
        headers=h,
        json={"amount": 85, "type": "expense", "account_id": accounts[0]["id"], "category_id": food["id"], "occurred_at": today.isoformat()},
    )
    notes = client.get("/api/notifications", headers=h).json()["items"]
    budget_notes = [n for n in notes if n["type"] == "budget"]
    assert budget_notes, "expected a budget threshold notification"
