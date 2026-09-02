"""Load sample data into the BudgetX SQLite database.

Run from the backend directory:
    cd backend
    python load_sample_data.py

Idempotent — skips creation if the sample user already exists.
"""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    Account,
    AccountType,
    Budget,
    BudgetItem,
    Category,
    CategoryKind,
    Debt,
    DebtStatus,
    DebtType,
    DEFAULT_EXPENSE_CATEGORIES,
    DEFAULT_INCOME_CATEGORIES,
    Investment,
    InvestmentType,
    SavingsGoal,
    Subscription,
    SubscriptionFrequency,
    Transaction,
    TransactionType,
    User,
)

SAMPLE_EMAIL = "abhinandan@budgetx.com"


def main() -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == SAMPLE_EMAIL).first()
        if existing:
            print(f"User {SAMPLE_EMAIL} already exists (id={existing.id}). Skipping.")
            user = existing
        else:
            user = create_user(db)
            print(f"Created user: {user.name} (id={user.id})")

        accounts = create_accounts(db, user)
        categories = create_categories(db, user)
        create_transactions(db, user, accounts, categories)
        create_budgets(db, user, categories)
        create_goals(db, user)
        create_debts(db, user)
        create_subscriptions(db, user, accounts)
        create_investments(db, user, accounts)

        db.commit()
        print("Sample data loaded successfully!")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_category(db, user_id: int, name: str, kind: CategoryKind, color: str) -> Category:
    cat = db.query(Category).filter_by(user_id=user_id, name=name, kind=kind).first()
    if cat:
        return cat
    cat = Category(user_id=user_id, name=name, kind=kind, color=color)
    db.add(cat)
    db.flush()
    return cat


# ---------------------------------------------------------------------------
# 1. User
# ---------------------------------------------------------------------------

def create_user(db) -> User:
    user = User(
        email=SAMPLE_EMAIL,
        name="Abhinandan Subedi",
        password_hash=hash_password("password123"),
        currency="NPR",
        locale="ne-NP",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


# ---------------------------------------------------------------------------
# 2. Accounts
# ---------------------------------------------------------------------------

ACCOUNT_DATA = [
    ("Nabil Bank", AccountType.bank, 250000),
    ("Global IME Bank", AccountType.bank, 180000),
    ("eSewa", AccountType.wallet, 15000),
    ("Khalti", AccountType.wallet, 8500),
    ("Cash", AccountType.cash, 25000),
    ("Investment Account", AccountType.investment, 450000),
]


def create_accounts(db, user: User) -> dict[str, Account]:
    accounts: dict[str, Account] = {}
    for name, acc_type, balance in ACCOUNT_DATA:
        acc = Account(
            user_id=user.id,
            name=name,
            type=acc_type,
            currency="NPR",
            opening_balance=balance,
        )
        db.add(acc)
        db.flush()
        accounts[name] = acc
    return accounts


# ---------------------------------------------------------------------------
# 4. Transactions (last ~6 months, ~100 items)
# ---------------------------------------------------------------------------

MERCHANTS = {
    "Food & Drink": [
        "Foodmandu", "BhatBhateni", "Himalayan Java", "Starbucks",
        "Thakali Kitchen", "Yangling Tibetan", "Dilli Bhojanalaya",
        "Momocafe", "KFC Nepal", "Pizza Hut",
    ],
    "Transport": [
        "Pathao", "InDrive", "Nepal Yatayat", "Sajha Yatayat",
        "Bus Ticket", "Tootle", "Nepal Oil Corporation", "Total Nepal",
    ],
    "Shopping": [
        "Daraz", "Sastodeal", "BhatBhateni Mart", "Big Mart",
        "Nepalaxmi Mart", "Thamel House", "Jawalakhel Handicraft",
    ],
    "Entertainment": [
        "Netflix", "Spotify", "CG Cinemas", "QFX Cinemas",
        "BookMyShow", "Hamro Movie", "Steam",
    ],
    "Education": [
        "Tribhuvan University", "Kathmandu University", "Coursera",
        "Udemy", "edX", "IT Training Nepal", "Broadway Infosys",
    ],
    "Utilities": [
        "Nepal Telecom", "Ncell", "Himalayan Power", "Kathmandu Upatyaka",
        "NWCL", "Suspended Cable",
    ],
    "Health": [
        "Nepal Medical College", "Grande International Hospital",
        "Medicare Hospital", "Bir Hospital", "Pharmacy Plus",
        "Quality Nepal Medicine",
    ],
}

EXPENSE_RANGES = {
    "Food & Drink": (3000, 8000),
    "Transport": (1500, 4000),
    "Shopping": (5000, 20000),
    "Entertainment": (2000, 5000),
    "Education": (10000, 30000),
    "Utilities": (3000, 5000),
    "Health": (2000, 8000),
}


def create_transactions(db, user: User, accounts: dict[str, Account], categories: dict[str, Category]) -> None:
    today = date.today()
    start = today - timedelta(days=180)
    bank = accounts["Nabil Bank"]
    wallet = accounts["eSewa"]

    txns = []

    # Monthly salary on 25th
    current = start
    while current <= today:
        if current.day == 25 and current <= today:
            txns.append(Transaction(
                user_id=user.id,
                account_id=bank.id,
                category_id=categories["Salary"].id,
                type=TransactionType.income,
                amount=150000,
                occurred_at=current,
                payee="Employer Nepal Pvt Ltd",
                note="Monthly salary",
            ))
        current += timedelta(days=1)

    # Random freelance income (~2 per month)
    for month_offset in range(6):
        month_start = start + timedelta(days=30 * month_offset)
        for _ in range(2):
            day_offset = random.randint(5, 25)
            txn_date = month_start + timedelta(days=day_offset)
            if txn_date <= today:
                txns.append(Transaction(
                    user_id=user.id,
                    account_id=bank.id,
                    category_id=categories["Freelance"].id,
                    type=TransactionType.income,
                    amount=random.randint(25000, 40000),
                    occurred_at=txn_date,
                    payee=random.choice(["Upwork Client", "Fiverr Client", "Private Project"]),
                    note="Freelance payment",
                ))

    # Expenses across categories
    expense_weights = {
        "Food & Drink": 6,
        "Transport": 4,
        "Shopping": 3,
        "Entertainment": 2,
        "Education": 1,
        "Utilities": 2,
        "Health": 1,
    }
    all_expense_cats = list(expense_weights.keys())
    all_weights = [expense_weights[c] for c in all_expense_cats]

    for _ in range(80):
        cat_name = random.choices(all_expense_cats, weights=all_weights, k=1)[0]
        low, high = EXPENSE_RANGES[cat_name]
        txn_date = start + timedelta(days=random.randint(0, 179))
        merchant = random.choice(MERCHANTS[cat_name])
        acc = wallet if random.random() < 0.3 else bank
        txns.append(Transaction(
            user_id=user.id,
            account_id=acc.id,
            category_id=categories[cat_name].id,
            type=TransactionType.expense,
            amount=random.randint(low, high),
            occurred_at=txn_date,
            payee=merchant,
            note=f"{merchant} purchase",
        ))

    db.add_all(txns)


# ---------------------------------------------------------------------------
# 3. Categories (using defaults)
# ---------------------------------------------------------------------------

def create_categories(db, user: User) -> dict[str, Category]:
    categories: dict[str, Category] = {}
    for name, color in DEFAULT_EXPENSE_CATEGORIES:
        cat = _get_or_create_category(db, user.id, name, CategoryKind.expense, color)
        categories[name] = cat
    for name, color in DEFAULT_INCOME_CATEGORIES:
        cat = _get_or_create_category(db, user.id, name, CategoryKind.income, color)
        categories[name] = cat
    return categories


# ---------------------------------------------------------------------------
# 5. Budgets
# ---------------------------------------------------------------------------

BUDGET_DATA = [
    ("Food & Drink", 25000),
    ("Transport", 10000),
    ("Entertainment", 8000),
    ("Shopping", 20000),
    ("Education", 30000),
]


def create_budgets(db, user: User, categories: dict[str, Category]) -> None:
    today = date.today()
    month_start = today.replace(day=1)
    budget = Budget(user_id=user.id, name="Monthly Budget", month=month_start)
    db.add(budget)
    db.flush()

    for cat_name, amount in BUDGET_DATA:
        cat = categories.get(cat_name)
        if cat:
            db.add(BudgetItem(budget_id=budget.id, category_id=cat.id, amount=amount))


# ---------------------------------------------------------------------------
# 6. Goals
# ---------------------------------------------------------------------------

GOAL_DATA = [
    ("Emergency Fund", 500000, 180000, "#0C5B45"),
    ("New Laptop", 200000, 85000, "#33628C"),
    ("Travel Fund", 100000, 32000, "#A85D4A"),
]


def create_goals(db, user: User) -> None:
    today = date.today()
    for name, target, current, color in GOAL_DATA:
        goal = SavingsGoal(
            user_id=user.id,
            name=name,
            target_amount=target,
            current_amount=current,
            deadline=today + timedelta(days=365),
            color=color,
        )
        db.add(goal)


# ---------------------------------------------------------------------------
# 7. Debts
# ---------------------------------------------------------------------------

DEBT_DATA = [
    {
        "name": "Education Loan",
        "debt_type": DebtType.education,
        "principal": 500000,
        "remaining_balance": 380000,
        "interest_rate": 12,
        "minimum_payment": 8000,
        "due_day": 15,
        "start_date": date(2023, 1, 1),
    },
    {
        "name": "Credit Card",
        "debt_type": DebtType.credit_card,
        "principal": 50000,
        "remaining_balance": 15000,
        "interest_rate": 18,
        "minimum_payment": 3000,
        "due_day": 5,
        "start_date": date(2024, 6, 1),
    },
]


def create_debts(db, user: User) -> None:
    for data in DEBT_DATA:
        debt = Debt(
            user_id=user.id,
            status=DebtStatus.active,
            **data,
        )
        db.add(debt)


# ---------------------------------------------------------------------------
# 8. Subscriptions
# ---------------------------------------------------------------------------

SUB_DATA = [
    ("Netflix", 699, SubscriptionFrequency.monthly, "Entertainment"),
    ("Spotify", 199, SubscriptionFrequency.monthly, "Entertainment"),
    ("Canva", 500, SubscriptionFrequency.monthly, "Education"),
    ("Ncell Data Pack", 999, SubscriptionFrequency.monthly, "Utilities"),
]


def create_subscriptions(db, user: User, accounts: dict[str, Account]) -> None:
    today = date.today()
    bank = accounts["Nabil Bank"]
    for name, amount, freq, category in SUB_DATA:
        sub = Subscription(
            user_id=user.id,
            name=name,
            amount=amount,
            frequency=freq,
            category=category,
            next_billing_date=today.replace(day=min(today.day + 5, 28)),
            start_date=today - timedelta(days=180),
            is_active=True,
            account_id=bank.id,
        )
        db.add(sub)


# ---------------------------------------------------------------------------
# 9. Investments
# ---------------------------------------------------------------------------

INVESTMENT_DATA = [
    {
        "name": "Nabil Bank Stock",
        "investment_type": InvestmentType.stock,
        "symbol": "NABIL",
        "units": 50,
        "buy_price": 800,
        "current_price": 950,
    },
    {
        "name": "NIC Asia Mutual Fund",
        "investment_type": InvestmentType.mutual_fund,
        "symbol": "NICF",
        "units": 100,
        "buy_price": 150,
        "current_price": 165,
    },
    {
        "name": "Government Bond",
        "investment_type": InvestmentType.bond,
        "symbol": None,
        "units": 200000,
        "buy_price": 1,
        "current_price": 1.12,
    },
]


def create_investments(db, user: User, accounts: dict[str, Account]) -> None:
    inv_account = accounts["Investment Account"]
    today = date.today()
    for data in INVESTMENT_DATA:
        inv = Investment(
            user_id=user.id,
            account_id=inv_account.id,
            buy_date=today - timedelta(days=365),
            notes=f"Sample investment: {data['name']}",
            **data,
        )
        db.add(inv)


if __name__ == "__main__":
    main()
