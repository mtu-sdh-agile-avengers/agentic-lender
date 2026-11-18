from enum import StrEnum


class LtvGroup(StrEnum):
    UP_TO_60 = "up_to_60"
    FROM_60_TO_80 = "from_60_to_80"
    FROM_80_TO_90 = "from_80_to_90"
    OVER_90 = "over_90"


# --- property_spec related


class County(StrEnum):
    """26 counties of the Republic of Ireland. Match `county_centroid.json` of AL-AI Engine."""

    CARLOW = "Carlow"
    CAVAN = "Cavan"
    CLARE = "Clare"
    CORK = "Cork"
    DONEGAL = "Donegal"
    DUBLIN = "Dublin"
    GALWAY = "Galway"
    KERRY = "Kerry"
    KILDARE = "Kildare"
    KILKENNY = "Kilkenny"
    LAOIS = "Laois"
    LEITRIM = "Leitrim"
    LIMERICK = "Limerick"
    LONGFORD = "Longford"
    LOUTH = "Louth"
    MAYO = "Mayo"
    MEATH = "Meath"
    MONAGHAN = "Monaghan"
    OFFALY = "Offaly"
    ROSCOMMON = "Roscommon"
    SLIGO = "Sligo"
    TIPPERARY = "Tipperary"
    WATERFORD = "Waterford"
    WESTMEATH = "Westmeath"
    WEXFORD = "Wexford"
    WICKLOW = "Wicklow"


class PropertyType(StrEnum):
    DETACHED = "Detached"
    SEMI_D = "Semi-D"
    TERRACE = "Terrace"
    END_OF_TERRACE = "End of Terrace"
    APARTMENT = "Apartment"
    BUNGALOW = "Bungalow"
    TOWNHOUSE = "Townhouse"
    DUPLEX = "Duplex"
    STUDIO = "Studio"


class BerRating(StrEnum):
    """15 Irish Building Energy Rating grades, best to worst (`A1`, `A2`, ..., `G`)"""

    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    B1 = "B1"
    B2 = "B2"
    B3 = "B3"
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    D1 = "D1"
    D2 = "D2"
    E1 = "E1"
    E2 = "E2"
    F = "F"
    G = "G"


class LoanApplicationStatus(StrEnum):
    APPLIED = "Applied"
    AI_DELIBERATED = "AI Deliberated"
    UNDERWRITER_APPROVED = "Underwriter Approved"
    FUNDED = "Funded"
    CLOSED = "Closed"


class RiskTier(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class UnderwritingOutcome(StrEnum):
    APPROVED = "Approved"
    DECLINED = "Declined"
