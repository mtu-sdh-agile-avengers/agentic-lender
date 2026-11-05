from enum import StrEnum
from typing import Any


class Role(StrEnum):
    UNSPECIFIED = ""
    BORROWER = "retail_borrower"
    BROKER = "mortgage_broker"
    BANK_OFFICER = "underwriting_bank_officer"

    @classmethod
    def parse(cls, value: Any) -> Role:
        try:
            return cls(value)
        except ValueError:
            return cls.UNSPECIFIED


class SignInProvider(StrEnum):
    PASSWORD_EMAIL = "password"
    GOOGLE = "google.com"
    GITHUB = "github.com"
    OTHER = "other"

    @classmethod
    def parse(cls, value: Any) -> SignInProvider:
        try:
            return cls(value)
        except ValueError:
            return cls.OTHER
