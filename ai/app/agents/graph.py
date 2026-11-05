"""The credit committee graph (backlog ALG4-80).

    affordability ──► auto_decline ──► END          (hard limit breached)
                 └──► valuation ──► market ──► strategist ──► END

Each node is a plain function that receives the shared state and returns the
keys it wants to add. Affordability and valuation are deterministic Python;
only the strategist calls a language model. Market and strategist are filled
in by ALG4-83 and ALG4-84; here they are wired and working but minimal.
"""

import json
import logging
import time
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.state import CommitteeState
from app.agents.tools import assess_affordability, assess_collateral

logger = logging.getLogger(__name__)


def _step(agent: str, summary: str, **extra) -> list[dict[str, Any]]:
    return [{"agent": agent, "summary": summary, **extra}]


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
def affordability_node(state: CommitteeState) -> CommitteeState:
    """AGT/ALG4-81. Deterministic: stressed repayment, DTI, LTI, caps."""
    app = state["application"]
    result = assess_affordability(
        income=app["income"],
        existing_debt=app["existing_debt"],
        loan=app["loan"],
        rate_percent=app["rate_percent"],
        term_years=app["term_years"],
    ).as_dict()

    return {
        "affordability": result,
        "trail": _step("affordability",
                       f"DTI {result['dti_percent']}%, LTI {result['lti_multiple']}, "
                       f"{len(result['breaches'])} breach(es)"),
    }


def valuation_node(state: CommitteeState, *, model_bundle: dict | None = None
                   ) -> CommitteeState:
    """ALG4-82. Reuses the same valuation service as POST /v1/valuations."""
    from app.schemas import ValuationRequest
    from app.services.valuation import value_property

    app = state["application"]
    started = time.perf_counter()

    if model_bundle is None:
        estimate, version = app["asking_price"], "unavailable"
        note = "model not loaded, asking price used"
    else:
        request = ValuationRequest(**app["property"])
        valuation = value_property(request, model_bundle)
        estimate, version = valuation.estimate, valuation.model_version
        note = f"coordinates from {valuation.coordinates_source}"

    result = assess_collateral(app["loan"], app["asking_price"], estimate)
    result["model_version"] = version
    result["note"] = note

    return {
        "valuation": result,
        "trail": _step("valuation",
                       f"estimate EUR {result['estimate']:,}, "
                       f"gap {result['gap_percent']:+.1f}%, "
                       f"LTV {result['ltv_percent']}% on {result['ltv_basis']}",
                       model=version,
                       seconds=round(time.perf_counter() - started, 2)),
    }


def market_node(state: CommitteeState) -> CommitteeState:
    """ALG4-83 placeholder: external rate and market research goes here.

    Returns a clearly marked stub so the graph runs end to end and AL-Web can
    already render the section.
    """
    result = {
        "ecb_base_rate_percent": None,
        "trend": "unknown",
        "sources": [],
        "stub": True,
    }
    return {"market": result,
            "trail": _step("market", "stub: external research not implemented yet")}


STRATEGIST_PROMPT = """You are a mortgage underwriting strategist at an Irish \
retail bank. The figures below were produced by verified calculators.

RULES:
- Do NOT recalculate or invent any number. Use only the facts given.
- Decline if any regulatory limit is breached.
- Conditionally Approve when the case is sound but needs evidence or changes.

Affordability: {affordability}
Collateral: {valuation}
Market context: {market}

Return ONLY valid JSON, no markdown fences:
{{"decision": "Approve" | "Conditionally Approve" | "Decline",
  "conditions": [string],
  "key_risks": [string],
  "reason": string}}"""


def strategist_node(state: CommitteeState, *, llm=None, providers=None
                    ) -> CommitteeState:
    """ALG4-84. The only node that talks to language models.

    With `providers`, the decision is a vote across every configured model
    (ALG4-85). With a single `llm`, it is one call, which is what the unit
    tests and the original spike use.
    """
    if providers:
        return _vote_for_decision(state, providers)
    if llm is None:
        return {"decision": {"decision": "Unavailable",
                             "reason": "no LLM provider configured"},
                "trail": _step("strategist", "skipped: no provider")}

    prompt = STRATEGIST_PROMPT.format(
        affordability=json.dumps(state["affordability"]),
        valuation=json.dumps(state["valuation"]),
        market=json.dumps(state.get("market", {})))

    started = time.perf_counter()
    try:
        raw = llm(prompt).strip()
    except Exception as exc:                      # provider outage, see AGT-02
        logger.warning("strategist provider failed: %s", exc)
        return {"decision": {"decision": "Unavailable", "reason": str(exc)[:200]},
                "trail": _step("strategist", f"provider failed: {type(exc).__name__}")}

    cleaned = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        decision = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("strategist returned unparseable output")
        decision = {"decision": "Error", "reason": "model did not return valid JSON",
                    "raw": raw[:500]}

    seconds = round(time.perf_counter() - started, 2)
    return {"decision": decision,
            "trail": _step("strategist", str(decision.get("decision")),
                           seconds=seconds)}


def _vote_for_decision(state: CommitteeState, providers) -> CommitteeState:
    """Run the strategist prompt across every provider and tally the votes."""
    from app.llm.consensus import vote

    prompt = STRATEGIST_PROMPT.format(
        affordability=json.dumps(state["affordability"]),
        valuation=json.dumps(state["valuation"]),
        market=json.dumps(state.get("market", {})))

    outcome = vote(prompt, providers)
    consensus = outcome["consensus"]
    decision = dict(consensus)
    decision["votes"] = outcome["votes"]   # kept for the AL-Web audit console

    models = ", ".join(f"{v['provider']}={v.get('decision') or 'failed'}"
                       for v in outcome["votes"])
    return {"decision": decision,
            "trail": _step("strategist",
                           f"{consensus['decision']} by vote ({models})",
                           seconds=consensus.get("seconds"))}


def auto_decline_node(state: CommitteeState) -> CommitteeState:
    """No model call when a hard regulatory limit is already breached."""
    breaches = state["affordability"]["breaches"]
    return {
        "decision": {
            "decision": "Decline",
            "conditions": [],
            "key_risks": breaches,
            "reason": "Regulatory limit breached: " + "; ".join(breaches),
            "automatic": True,
        },
        "trail": _step("auto_decline", f"declined on {len(breaches)} hard breach(es)"),
    }


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------
def route_after_affordability(state: CommitteeState) -> str:
    return "auto_decline" if state["affordability"]["breaches"] else "valuation"


def build_committee(model_bundle: dict | None = None, llm=None, providers=None):
    """Compile the graph. Dependencies are injected so tests can pass fakes.

    Pass `providers` for multi-model voting, or `llm` for a single model.
    """
    graph = StateGraph(CommitteeState)

    graph.add_node("affordability", affordability_node)
    graph.add_node("valuation",
                   lambda state: valuation_node(state, model_bundle=model_bundle))
    graph.add_node("market", market_node)
    graph.add_node("strategist",
                   lambda state: strategist_node(state, llm=llm,
                                                 providers=providers))
    graph.add_node("auto_decline", auto_decline_node)

    graph.set_entry_point("affordability")
    graph.add_conditional_edges("affordability", route_after_affordability,
                                {"valuation": "valuation",
                                 "auto_decline": "auto_decline"})
    graph.add_edge("valuation", "market")
    graph.add_edge("market", "strategist")
    graph.add_edge("strategist", END)
    graph.add_edge("auto_decline", END)
    return graph.compile()
