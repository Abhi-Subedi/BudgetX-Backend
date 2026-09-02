from pydantic import BaseModel


class Recommendation(BaseModel):
    title: str
    description: str
    impact: str
    category: str
