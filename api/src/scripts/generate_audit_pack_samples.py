"""Writes sample audit packs (PDF and CSV) for a made-up decided application into `docs/api/mocks/` (ALG4-236).

The samples are produced by the real renderers, so they always match what `GET .../audit-pack` returns. AL-Web can
use them while the download UI is built (ALG4-239). No Firebase or network access is needed.

Usage (from `api/`):
    uv run python -m src.scripts.generate_audit_pack_samples
"""

import datetime
from pathlib import Path

from src.assessments.enums import AIDecision, AssessmentStatus
from src.assessments.models import (
    AgentStepModel,
    AssessmentModel,
    DecisionModel,
    VoteModel,
)
from src.audit_packs.content import build_content
from src.audit_packs.models import AuditPackModel
from src.audit_packs.rendering import render_csv, render_pdf
from src.auth.enums import UserRole
from src.loan_applications import calculations
from src.loan_applications.enums import (
    BerRating,
    County,
    LoanApplicationStatus,
    PropertyType,
    UnderwritingOutcome,
)
from src.loan_applications.models import (
    LoanApplicationModel,
    LoanApplicationStatusChangeModel,
    PropertySpecModel,
    UnderwritingDecisionModel,
    UserInfoModel,
)

OUT_DIR = Path(__file__).resolve().parents[3] / "docs" / "api" / "mocks"


def at(day: int, hour: int, minute: int = 0) -> datetime.datetime:
    return datetime.datetime(2026, 11, day, hour, minute, tzinfo=datetime.UTC)


def sample_pack() -> AuditPackModel:
    application = LoanApplicationModel(
        loan_application_id="demo-app-0001",
        borrower_id="demo-borrower",
        borrower_full_name="Bríd Borrower (demo)",
        broker_id="demo-broker",
        bank_officer_id="demo-officer",
        annual_gross_income=85_000,
        annual_debt_repayments=2_400,
        deposit=50_000,
        loan_amount=300_000,
        term_years=30,
        first_time_buyer=True,
        ltv=300_000 / 350_000,
        ltv_group=calculations.ltv_group(300_000 / 350_000),
        property_spec=PropertySpecModel(
            county=County.CORK,
            address="12 Main Street, Cork",
            floor_area_m2=110,
            bedrooms=3,
            bathrooms=2,
            property_type=PropertyType.SEMI_D,
            ber=BerRating.B2,
            asking_price=350_000,
        ),
        status=LoanApplicationStatus.UNDERWRITER_APPROVED,
        status_history=[
            LoanApplicationStatusChangeModel(
                status=LoanApplicationStatus.APPLIED,
                changed_by_id="demo-borrower",
                changed_at=at(2, 9),
            ),
            LoanApplicationStatusChangeModel(
                status=LoanApplicationStatus.AI_DELIBERATED,
                changed_by_id="system",
                changed_at=at(2, 9, 16),
            ),
            LoanApplicationStatusChangeModel(
                status=LoanApplicationStatus.UNDERWRITER_APPROVED,
                changed_by_id="demo-officer",
                changed_at=at(3, 14),
            ),
        ],
        assessment_id="demo-assessment",
        risk_tier="Low",
        decision=UnderwritingDecisionModel(
            outcome=UnderwritingOutcome.APPROVED,
            reason="Affordable with a healthy margin; the property is fairly priced.",
            conditions=[
                "Final payslip before drawdown",
                "Valuation report from a panel valuer",
            ],
            decided_by="demo-officer",
            decided_at=at(3, 14),
        ),
        created_at=at(2, 9),
        updated_at=at(3, 14),
    )
    assessment = AssessmentModel(
        assessment_id="demo-assessment",
        loan_application_id="demo-app-0001",
        requested_by_id="demo-broker",
        job_id="demo-job",
        status=AssessmentStatus.DONE,
        rate_percent=3.9,
        affordability={
            "monthly_repayment": 1415,
            "stressed_repayment": 1590,
            "annual_debt_service": 21_480,
            "dti_percent": 25.3,
            "lti_multiple": 3.53,
            "breaches": [],
        },
        collateral={
            "estimate": 352_000,
            "asking_price": 350_000,
            "gap_percent": -0.6,
            "overvalued": False,
            "ltv_percent": 85.7,
            "model_version": "lgbm-2026-10",
        },
        decision=DecisionModel(
            decision=AIDecision.CONDITIONALLY_APPROVE,
            reason="Stressed repayments are well under the 40% limit; LTV is high for a first-time buyer.",
            conditions=["Confirm employment status"],
            key_risks=["LTV above 85%"],
            votes=[
                VoteModel(
                    provider="groq",
                    decision=AIDecision.CONDITIONALLY_APPROVE,
                    reason="High LTV, affordable",
                ),
                VoteModel(
                    provider="gemini",
                    decision=AIDecision.APPROVE,
                    reason="Comfortable margins",
                ),
                VoteModel(
                    provider="ollama",
                    decision=AIDecision.CONDITIONALLY_APPROVE,
                    reason="Check employment",
                ),
            ],
        ),
        risk={"tier": "Low", "score": 28, "approval_chance_percent": 94},
        created_at=at(2, 9, 15),
        finished_at=at(2, 9, 16),
    )
    steps = [
        AgentStepModel(
            step_number=1,
            agent="affordability",
            summary="Stressed DTI 25.3%, LTI 3.53: within limits",
        ),
        AgentStepModel(
            step_number=2,
            agent="valuation",
            summary="Estimate €352,000; asking price 0.6% below",
        ),
        AgentStepModel(
            step_number=3,
            agent="market",
            summary="ECB deposit rate 2.00%; Irish new mortgages 3.95%",
        ),
        AgentStepModel(
            step_number=4,
            agent="strategist",
            summary="Conditionally Approve by vote (2 of 3)",
        ),
        AgentStepModel(
            step_number=5, agent="risk", summary="Low risk, 94% approval chance"
        ),
    ]
    return AuditPackModel(
        application=application,
        borrower=UserInfoModel(
            uid="demo-borrower",
            full_name="Bríd Borrower (demo)",
            role=UserRole.BORROWER,
            email="brid.borrower@example.ie",
            phone="+353871234567",
        ),
        assessment=assessment,
        agent_steps=steps,
        generated_by_id="demo-officer",
        generated_at=at(4, 10),
    )


def main() -> None:
    content = build_content(sample_pack())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "audit-pack-sample.pdf").write_bytes(render_pdf(content))
    (OUT_DIR / "audit-pack-sample.csv").write_bytes(render_csv(content))
    print(
        f"wrote audit-pack-sample.pdf and .csv to {OUT_DIR} (SHA-256 {content.fingerprint})"
    )


if __name__ == "__main__":
    main()
