from fastapi import APIRouter

from app.api.routes import (
    account,
    accounts,
    admin,
    audit,
    auth,
    bills,
    budgets,
    debts,
    exchange,
    forecasts,
    goals,
    groups,
    health,
    households,
    insights,
    investments,
    login_history,
    net_worth,
    notifications,
    oauth,
    preferences,
    profile,
    recommendations,
    recurring,
    reports,
    security,
    subscriptions,
    tags,
    totp,
    transactions,
    transfers,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(accounts.router)
api_router.include_router(transactions.router)
api_router.include_router(budgets.router)
api_router.include_router(goals.router)
api_router.include_router(groups.router)
api_router.include_router(recurring.router)
api_router.include_router(bills.router)
api_router.include_router(subscriptions.router)
api_router.include_router(notifications.router)
api_router.include_router(insights.router)
api_router.include_router(net_worth.router)
api_router.include_router(debts.router)
api_router.include_router(transfers.router)
api_router.include_router(tags.router)
api_router.include_router(investments.router)
api_router.include_router(forecasts.router)
api_router.include_router(health.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
api_router.include_router(recommendations.router)
api_router.include_router(exchange.router)
api_router.include_router(admin.router)
api_router.include_router(security.router)
api_router.include_router(totp.router)
api_router.include_router(login_history.router)
api_router.include_router(profile.router)
api_router.include_router(preferences.router)
api_router.include_router(oauth.router)
api_router.include_router(households.router)
api_router.include_router(account.router)


@api_router.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
