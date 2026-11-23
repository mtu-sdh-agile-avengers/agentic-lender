import datetime
import hashlib
import json
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from src.assessments.models import AgentStepModel, AssessmentModel
from src.loan_applications.models import LoanApplicationModel, UserInfoModel


def canonical_json(data: Any) -> str:
    """Serializes data the same way every time: sorted keys, no spaces, UTF-8 kept as is."""
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )


@dataclass(frozen=True)
class AuditPackModel:
    """Everything recorded about a decided loan application, as exported in the audit pack (ALG4-237).

    Not stored: built from Firestore on every download, so it always shows the current record.
    """

    application: LoanApplicationModel
    borrower: UserInfoModel | None
    assessment: (
        AssessmentModel | None
    )  # latest AI committee run; `None` if it was never asked
    agent_steps: list[AgentStepModel] = field(default_factory=list)
    generated_by_id: str = ""
    generated_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )

    def record(self) -> dict[str, Any]:
        """The record the pack is about (no generation details), as plain JSON data."""
        return {
            "loan_application": self.application.model_dump(mode="json"),
            "assessment": (
                self.assessment.model_dump(mode="json") if self.assessment else None
            ),
            "agent_steps": [
                step.model_dump(mode="json", exclude={"agent_step_id"})
                for step in sorted(self.agent_steps, key=lambda s: s.step_number)
            ],
        }

    @cached_property
    def fingerprint(self) -> str:
        """SHA-256 of the canonical JSON of `record()`.

        The same record always gives the same fingerprint, so an auditor can tell whether two packs (or a pack
        and the database) describe exactly the same data. Hex, 64 characters.
        """
        return hashlib.sha256(canonical_json(self.record()).encode("utf-8")).hexdigest()
