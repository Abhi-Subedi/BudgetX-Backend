import enum


class AccountType(str, enum.Enum):
    cash = "cash"
    bank = "bank"
    wallet = "wallet"
    credit = "credit"
    savings = "savings"
    investment = "investment"


class TransactionType(str, enum.Enum):
    expense = "expense"
    income = "income"


class CategoryKind(str, enum.Enum):
    expense = "expense"
    income = "income"


class GroupRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class InvitationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"


class InvestmentType(str, enum.Enum):
    stock = "stock"
    mutual_fund = "mutual_fund"
    bond = "bond"
    fixed_deposit = "fixed_deposit"
    crypto = "crypto"
    other = "other"


class Frequency(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class AuditAction(str, enum.Enum):
    create = "create"
    update = "update"
    delete = "delete"


class DebtType(str, enum.Enum):
    loan = "loan"
    credit_card = "credit_card"
    personal = "personal"
    education = "education"
    car = "car"
    other = "other"


class DebtStatus(str, enum.Enum):
    active = "active"
    paid_off = "paid_off"
    defaulted = "defaulted"


class BillFrequency(str, enum.Enum):
    monthly = "monthly"
    weekly = "weekly"
    yearly = "yearly"
    one_time = "one_time"


class BillStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    overdue = "overdue"
    skipped = "skipped"


class SubscriptionFrequency(str, enum.Enum):
    monthly = "monthly"
    yearly = "yearly"
    weekly = "weekly"
    quarterly = "quarterly"


DEFAULT_EXPENSE_CATEGORIES: list[tuple[str, str]] = [
    ("Food & Drink", "#0C5B45"),
    ("Groceries", "#2F7D5C"),
    ("Housing", "#8A6D3B"),
    ("Transport", "#33628C"),
    ("Utilities", "#5B7A99"),
    ("Entertainment", "#7A4E8C"),
    ("Health", "#1F7A6B"),
    ("Shopping", "#A85D4A"),
    ("Education", "#4A6FA5"),
    ("Travel", "#3E7C59"),
    ("Subscriptions", "#6E685C"),
    ("Other", "#6E685C"),
]

DEFAULT_INCOME_CATEGORIES: list[tuple[str, str]] = [
    ("Salary", "#0C5B45"),
    ("Freelance", "#2F7D5C"),
    ("Investments", "#33628C"),
    ("Gifts", "#A85D4A"),
    ("Other Income", "#6E685C"),
]
