from pydantic import BaseModel


class HealthDimension(BaseModel):
    savings_rate: float
    budget_adherence: float
    debt_ratio: float
    emergency_fund: float
    consistency: float


class HealthScoreRead(BaseModel):
    overall_score: float
    dimensions: HealthDimension
    insights: list[str]
