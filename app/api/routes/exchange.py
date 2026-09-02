from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/exchange", tags=["exchange"])

# Rates relative to USD (hardcoded for simplicity)
_RATES: dict[str, float] = {
    "USD": 1.0,
    "NPR": 133.50,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 83.12,
    "AUD": 1.53,
    "CAD": 1.36,
}


@router.get("/rates")
def get_rates():
    return {"base": "USD", "rates": _RATES}


@router.get("/convert")
def convert(
    amount: float = Query(gt=0),
    fr: str = Query(alias="from"),
    to: str = Query(),
):
    from_cur = fr.upper()
    to_cur = to.upper()
    if from_cur not in _RATES:
        raise HTTPException(422, f"Unsupported currency: {from_cur}")
    if to_cur not in _RATES:
        raise HTTPException(422, f"Unsupported currency: {to_cur}")
    result = amount * _RATES[to_cur] / _RATES[from_cur]
    return {"amount": amount, "from": from_cur, "to": to_cur, "result": round(result, 2)}
