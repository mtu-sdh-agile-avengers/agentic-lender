"""ALG4-237: GET /api/v1/loan-applications/{id}/audit-pack."""

import asyncio
import csv
import dataclasses
import io

import pytest

from src.audit_packs.content import build_content
from src.audit_packs.dependencies import get_audit_pack_service
from src.audit_packs.exceptions import AuditPackNotAvailableError
from src.audit_packs.rendering import render_csv, render_pdf
from src.audit_packs.service import AuditPackService
from src.loan_applications.exceptions import (
    LoanApplicationAccessError,
    LoanApplicationNotFoundError,
)
from tests import fakes

URL = "/api/v1/loan-applications/app-1/audit-pack"


def service(decided: bool = True) -> AuditPackService:
    return AuditPackService(
        fakes.FakeApplications(fakes.application(decided=decided)),
        fakes.FakeUsers(),
        fakes.FakeAssessments(fakes.assessment(), steps=fakes.STEPS),
    )


def build(uid: str = fakes.OFFICER, decided: bool = True, app_id: str = "app-1"):
    return asyncio.run(service(decided).build(fakes.user(uid), app_id))


def test_pack_collects_application_assessment_and_steps():
    pack = build()
    assert pack.application.decision.outcome == "Approved"
    assert pack.assessment.assessment_id == "assessment-1"
    assert len(pack.agent_steps) == 2
    assert pack.generated_by_id == fakes.OFFICER
    assert len(pack.fingerprint) == 64


def test_pack_rules():
    with pytest.raises(AuditPackNotAvailableError):
        build(decided=False)
    with pytest.raises(LoanApplicationAccessError):
        build(uid=fakes.OTHER_OFFICER)
    with pytest.raises(LoanApplicationNotFoundError):
        build(app_id="missing")


def test_fingerprint_depends_only_on_the_record():
    pack = build()
    later = dataclasses.replace(pack, generated_by_id="someone-else")
    assert later.fingerprint == pack.fingerprint

    changed = pack.application.model_copy(
        update={"loan_amount": pack.application.loan_amount + 1}
    )
    assert (
        dataclasses.replace(pack, application=changed).fingerprint != pack.fingerprint
    )


def csv_rows(pack) -> list[list[str]]:
    data = render_csv(build_content(pack))
    assert data.startswith("﻿".encode())  # BOM for Excel
    return list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))


def test_csv_has_one_row_per_value():
    pack = build()
    rows = csv_rows(pack)
    assert rows[0] == ["section", "field", "value"]
    assert ["Financials", "Loan amount (EUR)", "300000"] in rows
    assert ["Audit pack", "Fingerprint (SHA-256)", pack.fingerprint] in rows
    assert ["Lending decision", "Outcome", "Approved"] in rows
    history = [row for row in rows if row[0] == "Status history"]
    assert [row[1] for row in history] == ["1", "2", "3"]
    assert history[0][2].startswith("Status: Applied; Changed at: ")
    steps = [row for row in rows if row[0] == "Reasoning steps"]
    assert [row[1] for row in steps] == ["1", "2"]  # ordered by step number
    assert ["Committee votes", "gemini", "Vote: No usable answer; Reason: "] in rows


def test_pack_without_ai_assessment_still_renders():
    pack = dataclasses.replace(build(), assessment=None, agent_steps=[])
    rows = csv_rows(pack)
    assert [
        "AI committee assessment",
        "",
        "The AI committee was not asked to assess this application.",
    ] in rows
    assert render_pdf(build_content(pack)).startswith(b"%PDF")


def test_pdf_is_a_document():
    data = render_pdf(build_content(build()))
    assert data.startswith(b"%PDF") and data.rstrip().endswith(b"%%EOF")
    assert data.count(b"/Type /Page\n") + data.count(b"/Type /Page ") >= 1


def client(uid: str = fakes.OFFICER):
    shared = service()  # one record for every request of the test
    return fakes.client_as(uid, {get_audit_pack_service: lambda: shared})


def test_route_downloads_csv_and_pdf():
    with client() as c:
        csv_response = c.get(URL, params={"format": "csv"})
        pdf_response = c.get(URL)

    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert (
        csv_response.headers["content-disposition"]
        == 'attachment; filename="audit-pack-app-1.csv"'
    )
    assert len(csv_response.headers["x-audit-pack-sha256"]) == 64

    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")
    assert (
        pdf_response.headers["x-audit-pack-sha256"]
        == csv_response.headers["x-audit-pack-sha256"]
    )


def test_route_status_codes():
    with client(fakes.BROKER) as c:
        assert c.get(URL).status_code == 403  # bank officers only
    with client(fakes.OTHER_OFFICER) as c:
        assert c.get(URL).status_code == 403  # not assigned
    with client() as c:
        assert c.get(URL, params={"format": "xlsx"}).status_code == 422
        assert c.get("/api/v1/loan-applications/missing/audit-pack").status_code == 404
