"""What an audit pack contains, independent of the file format (ALG4-236).

`build_content` turns an `AuditPackModel` into an ordered list of blocks; the CSV and PDF renderers only decide how
each value looks. Values keep their type (numbers stay numbers) and carry a `Kind`, so the CSV can stay
machine-readable (`300000.0`) while the PDF is easy to read (`€300,000`).
"""

import datetime
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from src.audit_packs.models import AuditPackModel


class Kind(StrEnum):
    TEXT = "text"
    MONEY = "money"  # euro
    PERCENT = "percent"
    NUMBER = "number"
    BOOL = "bool"
    DATETIME = "datetime"
    LIST = "list"  # list of strings


@dataclass(frozen=True)
class Value:
    raw: Any
    kind: Kind = Kind.TEXT


@dataclass(frozen=True)
class Fields:
    """A titled list of label / value pairs."""

    title: str
    rows: list[tuple[str, Value]]


@dataclass(frozen=True)
class Table:
    """A titled table; `rows` hold one `Value` per column."""

    title: str
    columns: list[str]
    rows: list[list[Value]]
    empty_text: str = "None"


@dataclass(frozen=True)
class Note:
    """A titled paragraph of plain text."""

    title: str
    text: str


Block = Fields | Table | Note


@dataclass(frozen=True)
class AuditPackContent:
    title: str
    subtitle: str
    generated_at: datetime.datetime
    generated_by_id: str
    fingerprint: str
    blocks: list[Block] = field(default_factory=list)


def _get(source: dict[str, Any] | None, key: str) -> Any:
    return (source or {}).get(key)


def build_content(pack: AuditPackModel) -> AuditPackContent:
    """Orders the data of an audit pack into the sections every format shows."""
    app = pack.application
    spec = app.property_spec
    decision = app.decision
    assessment = pack.assessment
    ai_decision = assessment.decision if assessment else None
    risk = assessment.risk if assessment else None
    borrower = pack.borrower

    blocks: list[Block] = [
        Fields(
            "Summary",
            [
                ("Loan application ID", Value(app.loan_application_id)),
                ("Status", Value(app.status)),
                ("Lending decision", Value(decision.outcome if decision else None)),
                (
                    "Decided by (bank officer)",
                    Value(decision.decided_by if decision else None),
                ),
                (
                    "Decided at",
                    Value(decision.decided_at if decision else None, Kind.DATETIME),
                ),
                (
                    "AI committee decision",
                    Value(ai_decision.decision if ai_decision else None),
                ),
                ("Risk tier", Value(_get(risk, "tier") or app.risk_tier)),
                (
                    "Approval chance",
                    Value(_get(risk, "approval_chance_percent"), Kind.PERCENT),
                ),
            ],
        ),
        Fields(
            "Borrower",
            [
                (
                    "Full name",
                    Value(
                        (borrower.full_name if borrower else None)
                        or app.borrower_full_name
                    ),
                ),
                ("Email", Value(borrower.email if borrower else None)),
                ("Phone", Value(borrower.phone if borrower else None)),
                ("Borrower ID", Value(app.borrower_id)),
                ("First-time buyer", Value(app.first_time_buyer, Kind.BOOL)),
                ("Mortgage broker ID", Value(app.broker_id)),
                ("Bank officer ID", Value(app.bank_officer_id)),
            ],
        ),
        Fields(
            "Financials",
            [
                ("Annual gross income", Value(app.annual_gross_income, Kind.MONEY)),
                (
                    "Annual debt repayments",
                    Value(app.annual_debt_repayments, Kind.MONEY),
                ),
                ("Deposit", Value(app.deposit, Kind.MONEY)),
                ("Loan amount", Value(app.loan_amount, Kind.MONEY)),
                ("Term (years)", Value(app.term_years, Kind.NUMBER)),
                ("Loan-to-value", Value(app.ltv * 100, Kind.PERCENT)),
                ("LTV group", Value(app.ltv_group)),
            ],
        ),
        Fields(
            "Property",
            [
                ("County", Value(spec.county)),
                ("Address", Value(spec.address)),
                ("Property type", Value(spec.property_type)),
                ("Floor area (m2)", Value(spec.floor_area_m2, Kind.NUMBER)),
                ("Bedrooms", Value(spec.bedrooms, Kind.NUMBER)),
                ("Bathrooms", Value(spec.bathrooms, Kind.NUMBER)),
                ("BER", Value(spec.ber)),
                ("Asking price", Value(spec.asking_price, Kind.MONEY)),
                (
                    "Coordinates",
                    Value(
                        f"{spec.latitude}, {spec.longitude}"
                        if spec.latitude is not None and spec.longitude is not None
                        else None
                    ),
                ),
            ],
        ),
        Table(
            "Status history",
            ["#", "Status", "Changed at", "Changed by"],
            [
                [
                    Value(number, Kind.NUMBER),
                    Value(change.status),
                    Value(change.changed_at, Kind.DATETIME),
                    Value(change.changed_by_id),
                ]
                for number, change in enumerate(app.status_history, start=1)
            ],
        ),
        Fields(
            "Lending decision",
            [
                ("Outcome", Value(decision.outcome if decision else None)),
                ("Reason", Value(decision.reason if decision else None)),
                (
                    "Conditions",
                    Value(decision.conditions if decision else [], Kind.LIST),
                ),
                ("Decided by", Value(decision.decided_by if decision else None)),
                (
                    "Decided at",
                    Value(decision.decided_at if decision else None, Kind.DATETIME),
                ),
            ],
        ),
    ]

    if assessment is None:
        blocks.append(
            Note(
                "AI committee assessment",
                "The AI committee was not asked to assess this application.",
            )
        )
    else:
        affordability = assessment.affordability
        collateral = assessment.collateral
        blocks += [
            Fields(
                "AI committee assessment",
                [
                    ("Assessment ID", Value(assessment.assessment_id)),
                    ("Run status", Value(assessment.status)),
                    (
                        "Interest rate used",
                        Value(assessment.rate_percent, Kind.PERCENT),
                    ),
                    ("Decision", Value(ai_decision.decision if ai_decision else None)),
                    ("Reason", Value(ai_decision.reason if ai_decision else None)),
                    (
                        "Declined automatically",
                        Value(
                            ai_decision.automatic if ai_decision else None, Kind.BOOL
                        ),
                    ),
                    (
                        "Conditions",
                        Value(ai_decision.conditions if ai_decision else [], Kind.LIST),
                    ),
                    (
                        "Key risks",
                        Value(ai_decision.key_risks if ai_decision else [], Kind.LIST),
                    ),
                    ("Error", Value(assessment.error)),
                    ("Requested at", Value(assessment.created_at, Kind.DATETIME)),
                    ("Finished at", Value(assessment.finished_at, Kind.DATETIME)),
                ],
            ),
            Fields(
                "Verified figures",
                [
                    (
                        "Monthly repayment",
                        Value(_get(affordability, "monthly_repayment"), Kind.MONEY),
                    ),
                    (
                        "Stressed monthly repayment",
                        Value(_get(affordability, "stressed_repayment"), Kind.MONEY),
                    ),
                    (
                        "Debt-to-income (stressed)",
                        Value(_get(affordability, "dti_percent"), Kind.PERCENT),
                    ),
                    (
                        "Loan-to-income",
                        Value(_get(affordability, "lti_multiple"), Kind.NUMBER),
                    ),
                    (
                        "Affordability breaches",
                        Value(_get(affordability, "breaches") or [], Kind.LIST),
                    ),
                    (
                        "Valuation estimate",
                        Value(_get(collateral, "estimate"), Kind.MONEY),
                    ),
                    (
                        "Asking price vs estimate",
                        Value(_get(collateral, "gap_percent"), Kind.PERCENT),
                    ),
                    ("Overvalued", Value(_get(collateral, "overvalued"), Kind.BOOL)),
                    (
                        "Loan-to-value (AI)",
                        Value(_get(collateral, "ltv_percent"), Kind.PERCENT),
                    ),
                    ("Valuation model", Value(_get(collateral, "model_version"))),
                    ("Risk tier", Value(_get(risk, "tier"))),
                    ("Risk score (0-100)", Value(_get(risk, "score"), Kind.NUMBER)),
                    (
                        "Approval chance",
                        Value(_get(risk, "approval_chance_percent"), Kind.PERCENT),
                    ),
                ],
            ),
            Table(
                "Committee votes",
                ["Model", "Vote", "Reason"],
                [
                    [
                        Value(vote.provider),
                        Value(vote.decision or "No usable answer"),
                        Value(vote.reason),
                    ]
                    for vote in (ai_decision.votes if ai_decision else [])
                ],
                empty_text="No votes (declined automatically or no model answered)",
            ),
            Table(
                "Reasoning steps",
                ["#", "Agent", "Summary"],
                [
                    [
                        Value(step.step_number, Kind.NUMBER),
                        Value(step.agent),
                        Value(step.summary),
                    ]
                    for step in sorted(pack.agent_steps, key=lambda s: s.step_number)
                ],
                empty_text="No reasoning steps recorded",
            ),
        ]

    blocks.append(
        Note(
            "Integrity",
            "Fingerprint (SHA-256) of the record in this pack: "
            f"{pack.fingerprint}. It is computed over the canonical JSON (sorted keys) of the loan application, "
            "its latest AI assessment and the reasoning steps, so the same record always gives the same "
            "fingerprint and any change to it gives a different one. Generation time and the person who "
            "downloaded the pack are not part of it.",
        )
    )

    return AuditPackContent(
        title="Lending decision audit pack",
        subtitle=f"Loan application {app.loan_application_id}",
        generated_at=pack.generated_at,
        generated_by_id=pack.generated_by_id,
        fingerprint=pack.fingerprint,
        blocks=blocks,
    )
