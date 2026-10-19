"""Request and response models for the AL-AI Engine API.

These classes are the contract with AL-Core: FastAPI validates every incoming
request against them and publishes them in /openapi.json, which AL-Core and the
mobile app use to generate their clients.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

# The 15 Irish BER grades, best to worst. "SI_666" is an exemption code, not a
# rating, so it is not accepted here.
BER_GRADES = Literal[
    "A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3",
    "D1", "D2", "E1", "E2", "F", "G",
]

# Dwelling types present in the training data. Sites (land) are not valued.
PROPERTY_TYPES = Literal[
    "Detached", "Semi-D", "Terrace", "End of Terrace",
    "Apartment", "Bungalow", "Townhouse", "Duplex", "Studio",
]


class ValuationRequest(BaseModel):
    """What the borrower enters in the fair-price checker (AL-Mobile)."""

    county: str = Field(..., examples=["Cork"],
                        description="Republic of Ireland county")
    floor_area_m2: float = Field(..., ge=20, le=600, examples=[110])
    bedrooms: int = Field(..., ge=1, le=10, examples=[3])
    bathrooms: int = Field(1, ge=0, le=10, examples=[2])
    property_type: PROPERTY_TYPES = Field(..., examples=["Semi-D"])
    ber: BER_GRADES | None = Field(None, examples=["B2"],
                                   description="Omit if the rating is unknown "
                                               "or the property is exempt")

    # Optional: the app may know exact coordinates. If not, the county centroid
    # is used, because the model relies heavily on location.
    latitude: float | None = Field(None, ge=51.4, le=55.5)
    longitude: float | None = Field(None, ge=-10.6, le=-5.8)

    # Optional: the seller's price, so the Valuation Agent can compare
    asking_price: float | None = Field(None, gt=0, examples=[350000])

    @model_validator(mode="after")
    def coordinates_come_in_pairs(self) -> "ValuationRequest":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be given together")
        return self


class PriceRange(BaseModel):
    low: int
    high: int
    basis: str = Field(description="How the range was derived")


class AskingPriceComparison(BaseModel):
    asking_price: int
    gap_percent: float = Field(description="Positive means above our estimate")
    overvalued: bool = Field(description="True when more than 10% above")


class ValuationResponse(BaseModel):
    estimate: int = Field(description="Estimated market asking value in EUR")
    range: PriceRange
    currency: str = "EUR"
    model_version: str
    coordinates_source: Literal["request", "county_centroid"]
    ber_known: bool
    comparison: AskingPriceComparison | None = None
    disclaimer: str = (
        "Estimated market asking value from listing data. Not a valuation "
        "for lending purposes."
    )
