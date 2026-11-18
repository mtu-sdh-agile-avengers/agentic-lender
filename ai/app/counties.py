"""The 26 counties of the Republic of Ireland, spelled as in the training data.

Every county that reaches the engine is normalised here, so " limerick",
"CORK" or "Co. Cork" all become the canonical name and an unknown county is
rejected with 422 instead of failing later inside a committee run.

AL-Core keeps the same list (api/src/loan_applications/enums.py, County).
tests/test_counties.py fails if the two lists or app/data/county_centroids.json
ever drift apart.
"""

import re

COUNTIES: tuple[str, ...] = (
    "Carlow",
    "Cavan",
    "Clare",
    "Cork",
    "Donegal",
    "Dublin",
    "Galway",
    "Kerry",
    "Kildare",
    "Kilkenny",
    "Laois",
    "Leitrim",
    "Limerick",
    "Longford",
    "Louth",
    "Mayo",
    "Meath",
    "Monaghan",
    "Offaly",
    "Roscommon",
    "Sligo",
    "Tipperary",
    "Waterford",
    "Westmeath",
    "Wexford",
    "Wicklow",
)

_BY_KEY = {county.lower(): county for county in COUNTIES}
_PREFIX = re.compile(r"^(co\.?|county)\s+", re.IGNORECASE)


def normalize_county(value: str) -> str:
    """Return the canonical spelling of a county.

    Accepts any case, extra spaces and a "Co."/"County" prefix:
    " limerick", "CORK" and "Co. Cork" become "Limerick" and "Cork".

    Raises:
        ValueError: the value is not one of the 26 counties.
    """
    key = _PREFIX.sub("", " ".join(str(value).split())).lower()
    try:
        return _BY_KEY[key]
    except KeyError:
        raise ValueError(
            f"unknown county '{value}'. Known counties: {', '.join(COUNTIES)}"
        ) from None
