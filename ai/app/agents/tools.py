"""Deterministic calculators used by the agents (backlog AGT-03).

Agents never do arithmetic. Our own provider tests showed three models
producing three different debt-to-income figures for the same application, so
every number the committee reasons about is computed here, in Python, and
passed to the model as a fact.

These limits are configuration, not hardcoded truths: the Central Bank of
Ireland changes them, and the stress rate is lender policy.
"""

from dataclasses import dataclass, field

# Central Bank of Ireland mortgage measures (first-time buyer defaults)
LTI_LIMIT = 4.0            # loan as a multiple of gross annual income
LTV_LIMIT_PCT = 90.0       # loan as a percentage of property value
# Lender policy
DTI_LIMIT_PCT = 40.0       # total debt service as a share of gross income
STRESS_BPS = 200           # repayments are tested 2 percentage points higher
OVERVALUED_THRESHOLD_PCT = 10.0


@dataclass
class Affordability:
    monthly_repayment: float
    stressed_repayment: float
    annual_debt_service: float
    dti_percent: float
    lti_multiple: float
    disposable_annual: float
    breaches: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "monthly_repayment": round(self.monthly_repayment),
            "stressed_repayment": round(self.stressed_repayment),
            "annual_debt_service": round(self.annual_debt_service),
            "dti_percent": round(self.dti_percent, 1),
            "lti_multiple": round(self.lti_multiple, 2),
            "disposable_annual": round(self.disposable_annual),
            "breaches": self.breaches,
            "limits": {"lti": LTI_LIMIT, "dti_percent": DTI_LIMIT_PCT,
                       "stress_bps": STRESS_BPS},
        }


def monthly_repayment(principal: float, annual_rate: float, years: int) -> float:
    """Standard annuity payment. A zero rate degrades to simple division."""
    if annual_rate <= 0:
        return principal / (years * 12)
    monthly_rate = annual_rate / 12
    payments = years * 12
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -payments)


def assess_affordability(income: float, existing_debt: float, loan: float,
                         rate_percent: float, term_years: int) -> Affordability:
    """Can the borrower service this loan if rates rise by STRESS_BPS?"""
    rate = rate_percent / 100
    stressed_rate = rate + STRESS_BPS / 10_000

    payment = monthly_repayment(loan, rate, term_years)
    stressed = monthly_repayment(loan, stressed_rate, term_years)
    annual_service = stressed * 12 + existing_debt

    result = Affordability(
        monthly_repayment=payment,
        stressed_repayment=stressed,
        annual_debt_service=annual_service,
        dti_percent=annual_service / income * 100,
        lti_multiple=loan / income,
        disposable_annual=income - annual_service,
    )

    if result.lti_multiple > LTI_LIMIT:
        result.breaches.append(
            f"loan-to-income {result.lti_multiple:.2f} exceeds the limit of {LTI_LIMIT}")
    if result.dti_percent > DTI_LIMIT_PCT:
        result.breaches.append(
            f"stressed debt-to-income {result.dti_percent:.1f}% exceeds "
            f"{DTI_LIMIT_PCT}%")
    return result


def assess_collateral(loan: float, asking_price: float,
                      estimate: float) -> dict:
    """Loan-to-value against the LOWER of asking price and model estimate.

    Lending against the higher number is how a bank ends up over-exposed when
    a buyer overpays, so the conservative figure is used.
    """
    gap_percent = (asking_price - estimate) / estimate * 100
    basis = min(asking_price, estimate)
    ltv = loan / basis * 100

    breaches = []
    if ltv > LTV_LIMIT_PCT:
        breaches.append(f"loan-to-value {ltv:.1f}% exceeds {LTV_LIMIT_PCT}%")

    return {
        "estimate": round(estimate),
        "asking_price": round(asking_price),
        "gap_percent": round(gap_percent, 1),
        "overvalued": gap_percent > OVERVALUED_THRESHOLD_PCT,
        "ltv_percent": round(ltv, 1),
        "ltv_basis": "model estimate" if estimate < asking_price else "asking price",
        "breaches": breaches,
        "limits": {"ltv_percent": LTV_LIMIT_PCT,
                   "overvalued_threshold_percent": OVERVALUED_THRESHOLD_PCT},
    }
