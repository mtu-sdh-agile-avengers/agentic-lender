"""
AL: Agentic Lender - LangGraph spike (backlog task ALG4-61 / AGT-01).

A deliberately small version of the credit committee, built to answer one
question: is LangGraph the right framework for AL-AI Engine?

What it demonstrates:
  1. shared state  - every node reads and writes one dictionary, which is
                     exactly what the AL-Web audit console needs to display
  2. tools vs LLM  - affordability and valuation are plain Python (exact
                     numbers); only the final judgement goes to a model
  3. conditional   - hopeless applications are declined without spending
     routing         tokens on the LLM
  4. observability - the state after the run IS the reasoning trail

Not included on purpose: the Market & Macro agent, multi-model voting,
retries. Those belong to ALG4-80 and later.

Run:
    pip install langgraph
    python spikes/langgraph_spike.py
    python spikes/langgraph_spike.py --income 40000 --loan 400000   # declined early
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

# Reuse the provider layer we built for ALG4-62 instead of duplicating it
sys.path.append(str(Path(__file__).resolve().parents[1]))
try:
    from llm_smoke_test import call_groq  # noqa: E402
except ImportError:
    call_groq = None

MODEL_PATH = Path(__file__).resolve().parents[1] / "ml" / "models" / "avm_v1.joblib"

# Central Bank of Ireland limits. Config values, not hardcoded rules.
LTI_LIMIT = 4.0          # loan to income, first-time buyer
LTV_LIMIT = 90.0         # loan to value, percent
DTI_LIMIT = 40.0         # debt service to gross income, percent (lender policy)
STRESS_BPS = 200         # repayments are tested 2% above the offered rate


# ---------------------------------------------------------------------------
# 1. The state: one dictionary flowing through the graph
# ---------------------------------------------------------------------------
class CreditState(TypedDict, total=False):
    # input
    application: dict[str, Any]
    # written by nodes
    affordability: dict[str, Any]
    valuation: dict[str, Any]
    decision: dict[str, Any]
    trail: list[str]          # human-readable log for the audit console


# ---------------------------------------------------------------------------
# 2. Deterministic tools. The LLM never does arithmetic.
# ---------------------------------------------------------------------------
def monthly_repayment(principal: float, annual_rate: float, years: int) -> float:
    """Standard annuity formula."""
    r = annual_rate / 12
    n = years * 12
    return principal * r / (1 - (1 + r) ** -n)


def affordability_node(state: CreditState) -> CreditState:
    app = state["application"]
    rate = app["rate"] / 100
    stressed = rate + STRESS_BPS / 10_000

    payment = monthly_repayment(app["loan"], rate, app["term_years"])
    stressed_payment = monthly_repayment(app["loan"], stressed, app["term_years"])
    annual_debt = stressed_payment * 12 + app["existing_debt"]

    result = {
        "monthly_repayment": round(payment),
        "stressed_repayment": round(stressed_payment),
        "dti_percent": round(annual_debt / app["income"] * 100, 1),
        "lti_multiple": round(app["loan"] / app["income"], 2),
        "disposable_annual": round(app["income"] - annual_debt),
        "breaches": [],
    }
    if result["lti_multiple"] > LTI_LIMIT:
        result["breaches"].append(
            f"LTI {result['lti_multiple']} exceeds limit {LTI_LIMIT}")
    if result["dti_percent"] > DTI_LIMIT:
        result["breaches"].append(
            f"stressed DTI {result['dti_percent']}% exceeds {DTI_LIMIT}%")

    return {"affordability": result,
            "trail": state.get("trail", []) + [
                f"affordability: DTI {result['dti_percent']}%, "
                f"LTI {result['lti_multiple']}, "
                f"{len(result['breaches'])} breach(es)"]}


def valuation_node(state: CreditState) -> CreditState:
    """Calls the trained AVM, or falls back to the asking price if absent."""
    app = state["application"]
    estimate, source = None, "asking price (model not found)"

    if MODEL_PATH.exists():
        import joblib
        import pandas as pd
        bundle = joblib.load(MODEL_PATH)
        row = {f: float("nan") for f in
               bundle["numeric_features"] + bundle["categorical_features"]}
        row.update({k: v for k, v in app["property"].items() if k in row})
        row["ber_score"] = bundle["ber_score"].get(app["property"]["ber"])
        row["ber_known"] = int(row["ber_score"] is not None)
        row["area_known"] = 1
        estimate = float(bundle["model"].predict(pd.DataFrame([row]))[0])
        source = bundle["version"]

    asking = app["asking_price"]
    estimate = estimate or asking
    gap = (asking - estimate) / estimate * 100
    ltv = app["loan"] / min(asking, estimate) * 100   # lend against the lower

    result = {
        "estimate": round(estimate),
        "asking_price": asking,
        "gap_percent": round(gap, 1),
        "overvalued": gap > 10,
        "ltv_percent": round(ltv, 1),
        "ltv_breach": ltv > LTV_LIMIT,
        "model_version": source,
    }
    return {"valuation": result,
            "trail": state.get("trail", []) + [
                f"valuation: estimate EUR {result['estimate']:,}, "
                f"gap {result['gap_percent']:+.1f}%, LTV {result['ltv_percent']}%"]}


# ---------------------------------------------------------------------------
# 3. The only node that talks to a model
# ---------------------------------------------------------------------------
STRATEGIST_PROMPT = """You are a mortgage underwriting strategist in Ireland.
The figures below were computed by verified calculators. Do NOT recalculate
them and do NOT invent new numbers. Judge the case on these facts alone.

Affordability: {affordability}
Collateral: {valuation}

Return ONLY valid JSON, no markdown:
{{"decision": "Approve" | "Conditionally Approve" | "Decline",
  "conditions": [string],
  "reason": string}}"""


def strategist_node(state: CreditState) -> CreditState:
    prompt = STRATEGIST_PROMPT.format(
        affordability=json.dumps(state["affordability"]),
        valuation=json.dumps(state["valuation"]))

    if call_groq is None:
        return {"decision": {"decision": "Unavailable",
                             "reason": "no LLM provider configured"},
                "trail": state.get("trail", []) + ["strategist: skipped"]}

    started = time.perf_counter()
    try:
        raw = call_groq(prompt).strip()
    except Exception as exc:
        # A provider outage must not kill the deliberation (see AGT-02)
        return {"decision": {"decision": "Unavailable", "reason": str(exc)[:200]},
                "trail": state.get("trail", []) + [f"strategist: failed, {type(exc).__name__}"]}

    cleaned = raw.removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        decision = json.loads(cleaned)
    except json.JSONDecodeError:
        decision = {"decision": "Unparseable", "raw": raw[:300]}
    decision["seconds"] = round(time.perf_counter() - started, 1)

    return {"decision": decision,
            "trail": state.get("trail", []) + [
                f"strategist: {decision.get('decision')} "
                f"({decision['seconds']}s)"]}


def auto_decline_node(state: CreditState) -> CreditState:
    """Hard regulatory breach: no need to ask a model."""
    breaches = state["affordability"]["breaches"]
    return {"decision": {"decision": "Decline",
                         "conditions": [],
                         "reason": "Regulatory limit breached: " + "; ".join(breaches)},
            "trail": state.get("trail", []) + ["auto-decline: hard limit breached"]}


# ---------------------------------------------------------------------------
# 4. Wiring: nodes + edges, with one conditional branch
# ---------------------------------------------------------------------------
def route_after_affordability(state: CreditState) -> str:
    """This is what CrewAI's sequential process cannot express cleanly."""
    return "auto_decline" if state["affordability"]["breaches"] else "valuation"


def build_graph():
    graph = StateGraph(CreditState)
    graph.add_node("affordability", affordability_node)
    graph.add_node("valuation", valuation_node)
    graph.add_node("strategist", strategist_node)
    graph.add_node("auto_decline", auto_decline_node)

    graph.set_entry_point("affordability")
    graph.add_conditional_edges("affordability", route_after_affordability,
                                {"valuation": "valuation",
                                 "auto_decline": "auto_decline"})
    graph.add_edge("valuation", "strategist")
    graph.add_edge("strategist", END)
    graph.add_edge("auto_decline", END)
    return graph.compile()


# ---------------------------------------------------------------------------
# 5. Run it
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--income", type=float, default=85_000)
    parser.add_argument("--loan", type=float, default=300_000)
    parser.add_argument("--asking", type=float, default=350_000)
    parser.add_argument("--debt", type=float, default=4_000)
    args = parser.parse_args()

    application = {
        "income": args.income,
        "existing_debt": args.debt,
        "loan": args.loan,
        "asking_price": args.asking,
        "rate": 3.9,
        "term_years": 30,
        "property": {"county": "Cork", "floor_area_m2": 110, "bedrooms": 3,
                     "bathrooms": 2, "property_type": "Semi-D", "ber": "B2",
                     "latitude": 51.90, "longitude": -8.47},
    }

    app_graph = build_graph()
    started = time.perf_counter()
    final = app_graph.invoke({"application": application, "trail": []})
    total = time.perf_counter() - started

    print("Reasoning trail")
    for line in final["trail"]:
        print(f"  - {line}")

    print("\nState after the run (this is what the audit console would show)")
    print(json.dumps({k: v for k, v in final.items()
                      if k in ("affordability", "valuation", "decision")},
                     indent=2))
    print(f"\ntotal {total:.1f}s")


if __name__ == "__main__":
    main()