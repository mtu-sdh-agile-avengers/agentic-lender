"""Stress test calculations (ALG4-92 interest rate shocks, ALG4-93 property market downturns).

Deterministic Python, no LLM: the same portfolio and scenario always give the same answer.
"""

from src.loan_applications.calculations import monthly_repayment
from src.loan_applications.models import LoanApplicationModel
from src.stress_tests.models import StressTestResultModel

# lender policy; the same limit is used by the AI Engine affordability agent (`ai/app/agents/tools.py`)
DTI_LIMIT_PERCENT = 40.0


def debt_to_income_percent(
    monthly_payment: float, annual_debt: float, annual_income: float
) -> float:
    """Debt-To-Income (DTI): yearly mortgage repayments plus other debt, as a share of gross income; in %."""
    return (monthly_payment * 12 + annual_debt) / annual_income * 100


def stress_application(
    application: LoanApplicationModel,
    *,
    rate_shock_bps: int,
    price_change_percent: float,
    base_rate_percent: float,
    dti_limit_percent: float = DTI_LIMIT_PERCENT,
) -> StressTestResultModel:
    """Applies a rate shock and/or a property price change to one loan application.

    Args:
        application: loan application to stress.
        rate_shock_bps: interest rate rise in basis points (`100` = +1 percentage point).
        price_change_percent: property value change in % (`-20` = values fall by 20%).
        base_rate_percent: interest rate before the shock; in %.
        dti_limit_percent: DTI above which the borrower can no longer afford the repayments; in %.

    Returns:
        StressTestResultModel: repayments, DTI and LTV before and after the scenario.
    """
    loan = application.loan_amount
    income = application.annual_gross_income
    debt = application.annual_debt_repayments

    # higher rate -> higher repayment -> higher DTI
    stressed_rate_percent = base_rate_percent + rate_shock_bps / 100
    base_repayment = monthly_repayment(loan, base_rate_percent, application.term_years)
    stressed_repayment = monthly_repayment(
        loan, stressed_rate_percent, application.term_years
    )
    stressed_dti = debt_to_income_percent(stressed_repayment, debt, income)

    # lower property value -> higher LTV; above 100% the loan is larger than the home's value
    property_value = application.property_spec.asking_price
    stressed_value = property_value * (1 + price_change_percent / 100)
    stressed_ltv = loan / stressed_value * 100

    return StressTestResultModel(
        loan_application_id=application.loan_application_id,
        borrower_id=application.borrower_id,
        borrower_full_name=application.borrower_full_name,
        loan_amount=round(loan, 2),
        property_value=round(property_value, 2),
        base_repayment=round(base_repayment, 2),
        stressed_repayment=round(stressed_repayment, 2),
        base_dti_percent=round(debt_to_income_percent(base_repayment, debt, income), 1),
        stressed_dti_percent=round(stressed_dti, 1),
        affordable=stressed_dti <= dti_limit_percent,
        base_ltv_percent=round(loan / property_value * 100, 1),
        stressed_ltv_percent=round(stressed_ltv, 1),
        negative_equity=stressed_ltv > 100,
    )


def stress_portfolio(
    applications: list[LoanApplicationModel],
    *,
    rate_shock_bps: int,
    price_change_percent: float,
    base_rate_percent: float,
    dti_limit_percent: float = DTI_LIMIT_PERCENT,
) -> list[StressTestResultModel]:
    """Stresses every application; the borrowers hit hardest come first.

    Returns:
        list[StressTestResultModel]: not affordable or in negative equity first, then by stressed DTI (highest first).
    """
    results = [
        stress_application(
            application,
            rate_shock_bps=rate_shock_bps,
            price_change_percent=price_change_percent,
            base_rate_percent=base_rate_percent,
            dti_limit_percent=dti_limit_percent,
        )
        for application in applications
    ]
    return sorted(
        results,
        key=lambda r: (r.affordable and not r.negative_equity, -r.stressed_dti_percent),
    )
