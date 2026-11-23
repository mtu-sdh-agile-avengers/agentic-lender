from src.loan_applications.enums import LtvGroup

_LTV_GROUP_UPPER_BOUNDS: tuple[tuple[float, LtvGroup], ...] = (
    (0.6, LtvGroup.UP_TO_60),
    (0.8, LtvGroup.FROM_60_TO_80),
    (0.9, LtvGroup.FROM_80_TO_90),
)

# Rate offered by the lender; AL-AI Engine uses the same default (`ApplicationInput.rate_percent`).
OFFERED_RATE_PERCENT = 3.9


def monthly_repayment(
    principal: float, annual_rate_percent: float, years: int
) -> float:
    """Monthly annuity repayment (same formula as the AI Engine affordability agent).

    Args:
        principal: loan amount; in euro.
        annual_rate_percent: annual interest rate; in % (e.g., `3.9`).
        years: loan term in years.

    Returns:
        float: monthly repayment; in euro. Without interest, the principal is divided evenly.
    """
    if principal <= 0:
        return 0.0

    payments = years * 12
    if annual_rate_percent <= 0:
        return principal / payments

    monthly_rate = annual_rate_percent / 100 / 12
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -payments)


def loan_amount(asking_price: float, deposit: float) -> float:
    return asking_price - deposit


def loan_to_value(loan_amount: float, property_value: float) -> float:
    return round(loan_amount / property_value, 4)


def ltv_group(ltv: float) -> LtvGroup:
    for upper_bound, group in _LTV_GROUP_UPPER_BOUNDS:
        if ltv <= upper_bound:
            return group

    return LtvGroup.OVER_90
