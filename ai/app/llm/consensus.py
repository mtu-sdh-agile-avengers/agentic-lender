"""Multi-model voting for the underwriting decision (backlog ALG4-85 / AGT-08).

Why vote at all: asked the same mortgage question, our three providers gave
three different answers, and the local model miscalculated the ratios. A single
model is therefore not a safe basis for a lending recommendation.

How ties are broken: the most conservative verdict wins. A bank that
accidentally approves is exposed; one that accidentally declines loses a
customer and can be overruled by the human underwriter, who sees every vote.
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.llm.providers import Provider

logger = logging.getLogger(__name__)

VALID_DECISIONS = ("Approve", "Conditionally Approve", "Decline")

# Most conservative last: used to break ties and to rank severity
SEVERITY = {"Approve": 0, "Conditionally Approve": 1, "Decline": 2}


def parse_decision(raw: str) -> dict[str, Any]:
    """Models like to wrap JSON in code fences or add a sentence first."""
    cleaned = raw.strip()
    for fence in ("```json", "```"):
        cleaned = cleaned.removeprefix(fence)
    cleaned = cleaned.removesuffix("```").strip()

    # Fall back to the outermost braces if there is chatter around the JSON
    if not cleaned.startswith("{"):
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("no JSON object in model output")
        cleaned = cleaned[start:end + 1]

    parsed = json.loads(cleaned)
    if parsed.get("decision") not in VALID_DECISIONS:
        raise ValueError(f"unexpected decision {parsed.get('decision')!r}")
    return parsed


def ask_one(provider: Provider, prompt: str) -> dict[str, Any]:
    """One provider's vote, never raising: a failure is itself a result."""
    started = time.perf_counter()
    vote: dict[str, Any] = {"provider": provider.name, "model": provider.model,
                            "local": provider.is_local}
    try:
        raw = provider.call(prompt)
        parsed = parse_decision(raw)
        vote.update(ok=True, decision=parsed["decision"],
                    conditions=parsed.get("conditions", []),
                    key_risks=parsed.get("key_risks", []),
                    reason=parsed.get("reason", ""))
    except Exception as exc:
        logger.warning("%s vote failed: %s", provider.name, exc)
        vote.update(ok=False, decision=None, error=f"{type(exc).__name__}: {exc}"[:200])
    vote["seconds"] = round(time.perf_counter() - started, 2)
    return vote


def tally(votes: list[dict[str, Any]]) -> dict[str, Any]:
    """Majority wins; a tie goes to the more conservative verdict."""
    valid = [vote for vote in votes if vote.get("ok")]
    if not valid:
        return {"decision": "Unavailable",
                "reason": "no provider returned a usable decision",
                "agreement": 0.0, "unanimous": False}

    counts: dict[str, int] = {}
    for vote in valid:
        counts[vote["decision"]] = counts.get(vote["decision"], 0) + 1

    top = max(counts.values())
    leaders = [decision for decision, count in counts.items() if count == top]
    winner = max(leaders, key=lambda decision: SEVERITY[decision])

    supporters = [vote for vote in valid if vote["decision"] == winner]
    conditions = sorted({condition for vote in supporters
                         for condition in vote.get("conditions", [])})
    risks = sorted({risk for vote in valid for risk in vote.get("key_risks", [])})

    return {
        "decision": winner,
        "conditions": conditions,
        "key_risks": risks,
        "reason": supporters[0].get("reason", ""),
        "agreement": round(top / len(valid), 2),
        "unanimous": len(counts) == 1,
        "tie_broken": len(leaders) > 1,
        "counts": counts,
        "voters": len(valid),
        "failed": [vote["provider"] for vote in votes if not vote.get("ok")],
    }


def vote(prompt: str, providers: list[Provider]) -> dict[str, Any]:
    """Ask every provider at once; total time is the slowest, not the sum."""
    if not providers:
        return {"consensus": {"decision": "Unavailable",
                              "reason": "no providers configured"},
                "votes": []}

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(providers)) as pool:
        votes = list(pool.map(lambda provider: ask_one(provider, prompt), providers))

    consensus = tally(votes)
    consensus["seconds"] = round(time.perf_counter() - started, 2)
    logger.info("consensus %s (%s/%s agreed, %s failed)", consensus["decision"],
                int(consensus.get("agreement", 0) * consensus.get("voters", 0)),
                consensus.get("voters", 0), len(consensus.get("failed", [])))
    return {"consensus": consensus, "votes": votes}
