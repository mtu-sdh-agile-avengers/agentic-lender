"""Tests for multi-model voting (backlog ALG4-85 / AGT-08).

All providers here are fakes, so the suite stays offline and deterministic.
"""

import json

import pytest

from app.llm.consensus import parse_decision, tally, vote
from app.llm.providers import Provider


def fake(name: str, decision: str | None = None, *, raises=None,
         raw: str | None = None, local: bool = False) -> Provider:
    def call(_prompt: str) -> str:
        if raises:
            raise raises
        if raw is not None:
            return raw
        return json.dumps({"decision": decision, "conditions": [],
                           "key_risks": [], "reason": f"{name} says {decision}"})

    return Provider(name=name, model=f"{name}-test", call=call, is_local=local)


# --- parsing --------------------------------------------------------------
def test_plain_json_is_parsed():
    assert parse_decision('{"decision": "Approve"}')["decision"] == "Approve"


def test_markdown_fences_are_stripped():
    raw = '```json\n{"decision": "Decline"}\n```'
    assert parse_decision(raw)["decision"] == "Decline"


def test_chatter_around_the_json_is_tolerated():
    raw = 'Sure! Here is my answer:\n{"decision": "Approve"}\nHope that helps.'
    assert parse_decision(raw)["decision"] == "Approve"


def test_unknown_decision_is_rejected():
    with pytest.raises(ValueError):
        parse_decision('{"decision": "Maybe"}')


def test_prose_without_json_is_rejected():
    with pytest.raises(ValueError):
        parse_decision("I think you should approve this one.")


# --- tallying -------------------------------------------------------------
def test_unanimous_vote():
    result = vote("prompt", [fake("a", "Approve"), fake("b", "Approve"),
                             fake("c", "Approve", local=True)])
    consensus = result["consensus"]
    assert consensus["decision"] == "Approve"
    assert consensus["unanimous"] is True
    assert consensus["agreement"] == 1.0


def test_majority_wins():
    result = vote("prompt", [fake("a", "Decline"), fake("b", "Decline"),
                             fake("c", "Approve")])
    consensus = result["consensus"]
    assert consensus["decision"] == "Decline"
    assert consensus["agreement"] == pytest.approx(0.67, abs=0.01)
    assert consensus["unanimous"] is False


def test_tie_goes_to_the_more_conservative_verdict():
    """Two providers, one Approve and one Decline: the bank declines."""
    result = vote("prompt", [fake("a", "Approve"), fake("b", "Decline")])
    consensus = result["consensus"]
    assert consensus["decision"] == "Decline"
    assert consensus["tie_broken"] is True


def test_conditional_beats_approve_in_a_tie():
    result = vote("prompt", [fake("a", "Approve"),
                             fake("b", "Conditionally Approve")])
    assert result["consensus"]["decision"] == "Conditionally Approve"


def test_a_failed_provider_does_not_block_the_vote():
    result = vote("prompt", [fake("a", "Approve"), fake("b", "Approve"),
                             fake("broken", raises=ConnectionError("down"))])
    consensus = result["consensus"]
    assert consensus["decision"] == "Approve"
    assert consensus["voters"] == 2
    assert consensus["failed"] == ["broken"]


def test_unparseable_output_counts_as_a_failure():
    result = vote("prompt", [fake("a", "Decline"),
                             fake("noisy", raw="no idea honestly")])
    assert result["consensus"]["voters"] == 1
    assert result["consensus"]["failed"] == ["noisy"]


def test_all_providers_failing_yields_unavailable():
    result = vote("prompt", [fake("a", raises=TimeoutError("slow")),
                             fake("b", raises=ConnectionError("down"))])
    assert result["consensus"]["decision"] == "Unavailable"


def test_no_providers_configured():
    assert vote("prompt", [])["consensus"]["decision"] == "Unavailable"


def test_every_vote_is_recorded_for_the_audit_console():
    result = vote("prompt", [fake("a", "Approve"), fake("b", "Decline"),
                             fake("c", raises=ValueError("boom"))])
    assert len(result["votes"]) == 3
    assert {v["provider"] for v in result["votes"]} == {"a", "b", "c"}
    assert all("seconds" in v for v in result["votes"])


def test_tally_collects_risks_from_every_voter():
    votes = [
        {"provider": "a", "ok": True, "decision": "Approve",
         "conditions": ["proof of income"], "key_risks": ["high LTV"]},
        {"provider": "b", "ok": True, "decision": "Approve",
         "conditions": [], "key_risks": ["rate sensitivity"]},
    ]
    consensus = tally(votes)
    assert consensus["key_risks"] == ["high LTV", "rate sensitivity"]
    assert consensus["conditions"] == ["proof of income"]
