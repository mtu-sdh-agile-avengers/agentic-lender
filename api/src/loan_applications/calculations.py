from src.loan_applications.enums import LtvGroup

_LTV_GROUP_UPPER_BOUNDS: tuple[tuple[float, LtvGroup], ...] = (
    (0.6, LtvGroup.UP_TO_60),
    (0.8, LtvGroup.FROM_60_TO_80),
    (0.9, LtvGroup.FROM_80_TO_90),
)


def loan_amount(asking_price: float, deposit: float) -> float:
    return asking_price - deposit


def loan_to_value(loan_amount: float, property_value: float) -> float:
    return round(loan_amount / property_value, 4)


def ltv_group(ltv: float) -> LtvGroup:
    for upper_bound, group in _LTV_GROUP_UPPER_BOUNDS:
        if ltv <= upper_bound:
            return group

    return LtvGroup.OVER_90
