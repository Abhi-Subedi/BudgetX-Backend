from pydantic import BaseModel


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    new_registrations_this_month: int
    total_transactions: int
    total_accounts: int
