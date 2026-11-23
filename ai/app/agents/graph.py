"""The credit committee graph (backlog ALG4-80).

    affordability ──► auto_decline ──────────────────────────► risk ──► END
                 └──► valuation ──► market ──► strategist ──► risk ──► END

(auto_decline: a hard limit is breached, no model is called.)

Each node is a plain function that receives the shared state and returns the
keys it wants to add. Affordability (ALG4-81), valuation (ALG4-82) and risk
are deterministic Python; market (ALG4-83) reads ECB statistics; only the
strategist calls a language model.
"""

import json
import logging
import time
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.risk import assess_risk
from app.agents.state import CommitteeState
from app.agents.tools import assess_affordability, assess_collateral
from app.services.market import MarketSource, default_market_source
from app.services.market import unavailable as market_unavailable

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
        first_time_buyer=app.get("first_time_buyer", True),
    ).as_dict()

    return {
        "affordability": result,
        "trail": _step(
            "affordability",
            f"DTI {result['dti_percent']}%, LTI {result['lti_multiple']}, "
            f"{len(result['breaches'])} breach(es)",
        ),
    }


def valuation_node(
    state: CommitteeState, *, model_bundle: dict | None = None
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
        "trail": _step(
            "valuation",
            f"estimate EUR {result['estimate']:,}, "
            f"gap {result['gap_percent']:+.1f}%, "
            f"LTV {result['ltv_percent']}% on {result['ltv_basis']}",
            model=version,
            seconds=round(time.perf_counter() - started, 2),
        ),
    }


def market_node(
    state: CommitteeState, *, market: MarketSource | None = None
) -> CommitteeState:
    """ALG4-83. Current ECB rates and the mortgage benchmark (services/market.py).

    Never fails the run: without the ECB the snapshot says `available: false`
    and the strategist decides on the calculators alone.
    """
    started = time.perf_counter()
    try:
        source = market or default_market_source()
        snapshot = source(state["application"].get("rate_percent"))
    except Exception as exc:  # a research outage must not stop the committee
        logger.warning("market research failed: %s", exc)
        snapshot = market_unavailable(f"{type(exc).__name__}: {exc}"[:200])

    return {
        "market": snapshot.model_dump(),
        "trail": _step(
            "market",
            _market_summary(snapshot),
            seconds=round(time.perf_counter() - started, 2),
        ),
    }


def _market_summary(snapshot) -> str:
    if not snapshot.available:
        reason = snapshot.errors[0] if snapshot.errors else "no data"
        return f"market data unavailable ({reason})"
    parts = []
    if snapshot.ecb_deposit_rate:
        parts.append(f"ECB deposit {snapshot.ecb_deposit_rate.value_percent:.2f}%")
    if snapshot.euribor_3m:
        trend = f" ({snapshot.euribor_3m.trend})" if snapshot.euribor_3m.trend else ""
        parts.append(f"Euribor 3M {snapshot.euribor_3m.value_percent:.2f}%{trend}")
    if snapshot.mortgage_rate:
        parts.append(
            f"new mortgages {snapshot.mortgage_rate.value_percent:.2f}% "
            f"({snapshot.mortgage_area})"
        )
    if snapshot.offered_vs_market_points is not None:
        parts.append(f"offered {snapshot.offered_vs_market_points:+.2f} pts vs market")
    return ", ".join(parts)


def _market_for_prompt(market: dict[str, Any]) -> dict[str, Any]:
    """Only the facts, not the source URLs: keeps the prompt short."""
    if not market:
        return {}
    return {
        "available": market.get("available", False),
        "facts": market.get("observations", []),
        "offered_vs_market_points": market.get("offered_vs_market_points"),
    }


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


def strategist_node(
    state: CommitteeState, *, llm=None, providers=None
) -> CommitteeState:
    """ALG4-84. The only node that talks to language models.

    With `providers`, the decision is a vote across every configured model
    (ALG4-85). With a single `llm`, it is one call, which is what the unit
    tests and the original spike use.
    """
    if providers:
        return _vote_for_decision(state, providers)
    if llm is None:
        return {
            "decision": {
                "decision": "Unavailable",
                "reason": "no LLM provider configured",
            },
            "trail": _step("strategist", "skipped: no provider"),
        }

    prompt = STRATEGIST_PROMPT.format(
        affordability=json.dumps(state["affordability"]),
        valuation=json.dumps(state["valuation"]),
        market=json.dumps(_market_for_prompt(state.get("market", {}))),
    )

    started = time.perf_counter()
    try:
        raw = llm(prompt).strip()
    except Exception as exc:  # provider outage, see AGT-02
        logger.warning("strategist provider failed: %s", exc)
        return {
            "decision": {"decision": "Unavailable", "reason": str(exc)[:200]},
            "trail": _step("strategist", f"provider failed: {type(exc).__name__}"),
        }

    cleaned = (
        raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    )
    try:
        decision = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("strategist returned unparseable output")
        decision = {
            "decision": "Error",
            "reason": "model did not return valid JSON",
            "raw": raw[:500],
        }

    seconds = round(time.perf_counter() - started, 2)
    return {
        "decision": decision,
        "trail": _step("strategist", str(decision.get("decision")), seconds=seconds),
    }


def _vote_for_decision(state: CommitteeState, providers) -> CommitteeState:
    """Run the strategist prompt across every provider and tally the votes."""
    from app.llm.consensus import vote

    prompt = STRATEGIST_PROMPT.format(
        affordability=json.dumps(state["affordability"]),
        valuation=json.dumps(state["valuation"]),
        market=json.dumps(_market_for_prompt(state.get("market", {}))),
    )

    outcome = vote(prompt, providers)
    consensus = outcome["consensus"]
    decision = dict(consensus)
    decision["votes"] = outcome["votes"]  # kept for the AL-Web audit console

    models = ", ".join(
        f"{v['provider']}={v.get('decision') or 'failed'}" for v in outcome["votes"]
    )
    return {
        "decision": decision,
        "trail": _step(
            "strategist",
            f"{consensus['decision']} by vote ({models})",
            seconds=consensus.get("seconds"),
        ),
    }


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


def risk_node(state: CommitteeState) -> CommitteeState:
    """Risk tier and approval chance (see agents/risk.py). Runs on both paths.

    After an automatic decline there is no valuation, so LTV is taken on the
    asking price, the same fallback the valuation node uses without a model.
    """
    app = state["application"]
    collateral = state.get("valuation") or assess_collateral(
        app["loan"], app["asking_price"], app["asking_price"]
    )
    risk = assess_risk(state["affordability"], collateral)
    return {
        "risk": risk.model_dump(),
        "trail": _step(
            "risk",
            f"{risk.tier}, score {risk.score}/100, "
            f"approval chance {risk.approval_chance_percent}%",
        ),
    }


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------
def route_after_affordability(state: CommitteeState) -> str:
    return "auto_decline" if state["affordability"]["breaches"] else "valuation"


def build_committee(
    model_bundle: dict | None = None,
    llm=None,
    providers=None,
    market: MarketSource | None = None,
):
    """Compile the graph. Dependencies are injected so tests can pass fakes.

    Pass `providers` for multi-model voting, or `llm` for a single model.
    `market` replaces the ECB-backed market research (tests, offline demos).
    """
    graph = StateGraph(CommitteeState)

    graph.add_node("affordability", affordability_node)
    graph.add_node(
        "valuation", lambda state: valuation_node(state, model_bundle=model_bundle)
    )
    graph.add_node("market", lambda state: market_node(state, market=market))
    graph.add_node(
        "strategist", lambda state: strategist_node(state, llm=llm, providers=providers)
    )
    graph.add_node("auto_decline", auto_decline_node)
    graph.add_node("risk", risk_node)

    graph.set_entry_point("affordability")
    graph.add_conditional_edges(
        "affordability",
        route_after_affordability,
        {"valuation": "valuation", "auto_decline": "auto_decline"},
    )
    graph.add_edge("valuation", "market")
    graph.add_edge("market", "strategist")
    graph.add_edge("strategist", "risk")
    graph.add_edge("auto_decline", "risk")
    graph.add_edge("risk", END)
    return graph.compile()
