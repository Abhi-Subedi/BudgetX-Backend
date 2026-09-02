from datetime import date

from tests.conftest import register_and_login


def _create_group(client, headers, name="Household"):
    return client.post("/api/groups", headers=headers, json={"name": name, "currency": "USD"})


def test_group_create_invite_join_flow(client):
    owner = register_and_login(client)
    invitee = register_and_login(client, name="Ben", email="ben@example.com")
    h = owner["headers"]

    created = _create_group(client, h)
    assert created.status_code == 201
    group = created.json()
    assert group["member_count"] == 1

    detail = client.get(f"/api/groups/{group['id']}", headers=h).json()
    assert detail["your_role"] == "owner"
    open_code = detail["invite_code"]

    invited = client.post(f"/api/groups/{group['id']}/invite", headers=h, json={"email": "ben@example.com"})
    assert invited.status_code == 201
    code = invited.json()["code"]

    dup_invite = client.post(f"/api/groups/{group['id']}/invite", headers=h, json={"email": "ben@example.com"})
    assert dup_invite.status_code == 409

    joined = client.post("/api/groups/join", headers=invitee["headers"], json={"code": code})
    assert joined.status_code == 200

    already = client.post("/api/groups/join", headers=invitee["headers"], json={"code": code})
    assert already.status_code == 409

    via_open_code = register_and_login(client, name="Cleo", email="cleo@example.com")
    joined_open = client.post("/api/groups/join", headers=via_open_code["headers"], json={"code": open_code})
    assert joined_open.status_code == 200

    groups_for_invitee = client.get("/api/groups", headers=invitee["headers"]).json()["items"]
    assert any(g["id"] == group["id"] for g in groups_for_invitee)


def test_wrong_email_cannot_use_personal_invite(client):
    owner = register_and_login(client)
    stranger = register_and_login(client, name="Eve", email="eve@example.com")
    group = _create_group(client, owner["headers"]).json()
    invite = client.post(f"/api/groups/{group['id']}/invite", headers=owner["headers"], json={"email": "ben@example.com"})
    code = invite.json()["code"]
    denied = client.post("/api/groups/join", headers=stranger["headers"], json={"code": code})
    assert denied.status_code == 403


def test_shared_expense_split_and_balances(client):
    owner = register_and_login(client)
    partner = register_and_login(client, name="Ben", email="ben@example.com")
    h = owner["headers"]
    group = _create_group(client, h).json()

    client.post("/api/groups/join", headers=partner["headers"], json={"code": group["invite_code"]})

    expense = client.post(
        f"/api/groups/{group['id']}/expenses",
        headers=h,
        json={"description": "Groceries run", "amount": 100.01, "occurred_at": date.today().isoformat()},
    )
    assert expense.status_code == 201

    balances = client.get(f"/api/groups/{group['id']}/balances", headers=h).json()["items"]
    by_user = {b["user_id"]: b for b in balances}
    assert abs(by_user[owner["user"]["id"]]["net"] - 50.005) < 0.02
    assert abs(by_user[partner["user"]["id"]]["net"] + 50.005) < 0.02
    owes_edges = by_user[partner["user"]["id"]]["owes"]
    assert len(owes_edges) == 1
    assert owes_edges[0]["to_user_id"] == owner["user"]["id"]

    activity = client.get(f"/api/groups/{group['id']}/activity", headers=h).json()["items"]
    assert activity[0]["description"] == "Groceries run"
    assert activity[0]["paid_by_name"] == "Asha Rai"
    assert abs(activity[0]["your_share"] - 50.005) < 0.02


def test_member_cannot_invite_or_change_roles(client):
    owner = register_and_login(client)
    member = register_and_login(client, name="Ben", email="ben@example.com")
    group = _create_group(client, owner["headers"]).json()
    client.post("/api/groups/join", headers=member["headers"], json={"code": group["invite_code"]})

    forbidden_invite = client.post(
        f"/api/groups/{group['id']}/invite", headers=member["headers"], json={"email": "x@y.com"}
    )
    assert forbidden_invite.status_code == 403

    promote_self = client.patch(
        f"/api/groups/{group['id']}/members/{member['user']['id']}/role",
        headers=member["headers"],
        json={"role": "admin"},
    )
    assert promote_self.status_code == 403

    promoted_by_owner = client.patch(
        f"/api/groups/{group['id']}/members/{member['user']['id']}/role",
        headers=owner["headers"],
        json={"role": "admin"},
    )
    assert promoted_by_owner.status_code == 200
    assert promoted_by_owner.json()["role"] == "admin"


def test_owner_cannot_be_removed_and_can_leave_guard(client):
    owner = register_and_login(client)
    member = register_and_login(client, name="Ben", email="ben@example.com")
    group = _create_group(client, owner["headers"]).json()
    client.post("/api/groups/join", headers=member["headers"], json={"code": group["invite_code"]})

    remove_owner_attempt = client.delete(
        f"/api/groups/{group['id']}/members/{owner['user']['id']}", headers=member["headers"]
    )
    assert remove_owner_attempt.status_code in (400, 403)

    leave_denied = client.delete(
        f"/api/groups/{group['id']}/members/{owner['user']['id']}", headers=owner["headers"]
    )
    assert leave_denied.status_code == 400

    leave_ok = client.delete(
        f"/api/groups/{group['id']}/members/{member['user']['id']}", headers=member["headers"]
    )
    assert leave_ok.status_code == 204


def test_outsider_cannot_see_group(client):
    owner = register_and_login(client)
    outsider = register_and_login(client, name="Zoe", email="zoe@example.com")
    group = _create_group(client, owner["headers"]).json()
    assert client.get(f"/api/groups/{group['id']}", headers=outsider["headers"]).status_code == 404
    assert client.get(f"/api/groups/{group['id']}/balances", headers=outsider["headers"]).status_code == 404
