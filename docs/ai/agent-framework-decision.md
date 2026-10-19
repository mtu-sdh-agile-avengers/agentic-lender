# Agent framework decision: multi-agent credit committee (AL-AI Engine)

**Jira:** ALG4-61 · **Author:** Pavlo · **Status:** decided

Terms used in this document: AVM (Automated Valuation Model), LLM (Large
Language Model), LTI (Loan-to-Income), LTV (Loan-to-Value), DTI
(Debt-to-Income), API (Application Programming Interface), JSON (JavaScript
Object Notation).

## Summary

Build the credit committee with **LangGraph**. The deciding factor is that
LangGraph keeps the whole deliberation in one explicit state object, which is
exactly what the AL-Web audit console has to display, and it supports
conditional routing so hopeless applications are declined without spending
tokens.

| Framework | Decision | Reason |
|---|---|---|
| **LangGraph** | **Selected** | Explicit shared state gives the audit trail for free; conditional edges allow early decline; nodes are plain Python functions, so each agent can use a different provider and deterministic calculators sit alongside LLM calls |
| CrewAI | Rejected | Faster to a first demo and the role/goal vocabulary reads well, but reasoning has to be recovered through callbacks, the sequential process does not express conditional routing cleanly, and its pinned dependency tree risks disturbing our scikit-learn environment |
| AutoGen | Rejected | Built around conversational message passing between agents; our committee is a fixed pipeline with a defined order, so the conversational model adds complexity without benefit |

A working spike is committed at `ai/spikes/langgraph_spike.py`. LangGraph was
prototyped; CrewAI and AutoGen were assessed against the same criteria from
their documentation. Details below.

## What the AL-AI Engine actually needs

The framework choice is driven by five requirements from the project
specification and our backlog, not by general popularity.

1. **Four agents in a defined order** (ALG4-81 to ALG4-84): Affordability,
   Valuation, Market & Macro Researcher, Underwriting Strategist.
2. **A visible reasoning trail.** AL-Web contains an "AI Audit & Deliberation
   Console" showing each agent's output, the models used, individual decision
   trails and consensus. Whatever we build must expose that data structurally.
3. **Mixed deterministic and generative steps.** Affordability and LTV are
   arithmetic and must be exact; only the final judgement is a language task.
4. **Several providers in one run** (ALG4-85): two cloud LLMs plus a local
   model through Ollama, with the final decision taken across models.
5. **Long-running background execution.** A deliberation takes seconds to
   minutes, so it runs as a background job with status polling, not inside a
   user request.

## Evaluation criteria

| Criterion | Why it matters here |
|---|---|
| Access to intermediate reasoning | Feeds the audit console (AL-Web) |
| Conditional routing | Skip the LLM when a regulatory limit is already breached |
| Per-agent model choice | Required by ALG4-85 |
| Deterministic tools alongside agents | Our own tests showed models miscalculating DTI |
| Pause, resume, inspect | Needed for background jobs and status polling |
| Dependency weight | Must coexist with scikit-learn, pandas and the trained model |
| Time to first working run | Sprint time is limited |

## The spike

`ai/spikes/langgraph_spike.py` implements a reduced committee: an affordability
node, a valuation node and an underwriting strategist, with a conditional edge
that routes to an automatic decline when a hard limit is breached. The Market &
Macro agent and multi-model voting were deliberately left out; they belong to
ALG4-80 and later.

Design points proven by the spike:

- Affordability and valuation are plain Python. The annuity formula, stressed
  repayment at +200 basis points, DTI, LTI and LTV are computed exactly. The
  LLM receives those numbers and is instructed not to recalculate them.
- The valuation node loads our trained AVM (`hist_gb_log-v1`) and computes LTV
  against the **lower** of asking price and model estimate, which is the
  conservative choice a lender would make.
- The strategist returns structured JSON, so the result can be stored and
  rendered rather than parsed out of prose.
- A provider failure returns a decision of "Unavailable" instead of crashing
  the graph, matching the retry and fallback behaviour built in ALG4-62.

### Measured results

Normal path (income €85,000, loan €300,000, asking price €350,000):

```
affordability: DTI 29.8%, LTI 3.53, 0 breach(es)
valuation: estimate EUR 414,646, gap -15.6%, LTV 85.7%
strategist: Approve (1.6s)
total 3.7s
```

Early-decline path (income €40,000, loan €400,000):

```
affordability: DTI 81.2%, LTI 10.0, 2 breach(es)
auto-decline: hard limit breached
total 0.0s
```

The second run is the clearest argument for the framework. The conditional edge
detected an LTI of 10.0 against the 4.0 limit and a stressed DTI of 81.2%
against 40%, then declined the application without making any model call at
all. With four agents and multi-model voting, that saves roughly a dozen API
calls on applications that could never be approved.

The full state after a run contains the affordability figures, the valuation
with model version, the decision with its reasoning, and a human-readable trail
— the exact payload the audit console needs.

### How the alternatives were assessed

LangGraph was prototyped. CrewAI and AutoGen were assessed against the same
criteria from their documentation and public examples rather than built, since
the requirements above already separate them clearly and sprint time was better
spent on the orchestration ticket.

| Criterion | LangGraph | CrewAI | AutoGen |
|---|---|---|---|
| Access to per-agent reasoning | Read the state object after the run | Recovered through step and task callbacks | Held in the conversation history between agents |
| Conditional routing | First-class conditional edges, proven in the spike | Expressible, but awkward inside a sequential process | Driven by agent conversation rather than an explicit graph |
| Deterministic tools beside agents | Nodes are plain Python functions, so a calculator is just a node | Tools attached to agents | Tools attached to agents |
| Different model per agent | Yes, each node chooses its own provider | Yes, `llm=` per agent | Yes, per agent configuration |
| Pause, resume, inspect | Checkpointing supports background jobs and status polling | Oriented to run-to-completion | Oriented to run-to-completion |
| Dependency weight | One package alongside our existing stack | Larger pinned dependency tree, risk of conflicts with scikit-learn and pandas | Larger, and brings a conversational runtime we do not need |
| Time to first working run | Around one hour including the deterministic calculators | Faster for a simple crew | Comparable to CrewAI |

CrewAI is genuinely the quicker route to a first demonstration, and its role,
goal and backstory vocabulary maps neatly onto a "committee" narrative. That
advantage matters less for us because the audit console is an explicit project
requirement: the deliberation must be inspectable as data, not merely produced.
AutoGen is strong where agents negotiate in open-ended conversation; our
committee is a fixed pipeline with a defined order, so that strength does not
apply.

## Consequences of this decision

- ALG4-80 (multi-agent orchestration) starts from the spike rather than from
  scratch; the graph and state schema are already defined.
- The state schema becomes part of the API contract: whatever the graph writes
  is what AL-Core stores in Firestore and AL-Web renders.
- Every arithmetic step stays in Python modules shared between the AVM service
  and the agents, so the same formulas serve both.
- Multi-model voting (ALG4-85) will be a node that calls several providers and
  writes all votes into the state, not a framework feature.

## Risks and open questions

1. **Latency with the full committee.** The spike makes one model call in 1.6s.
   Four agents with multi-model voting will be considerably slower, especially
   with the local model on CPU, which took 8-12s in our ALG4-62 tests. This is
   why deliberation runs as a background job.
2. **Prompt reliability.** The strategist returned valid JSON here, but our
   provider tests showed models wrapping JSON in markdown fences. Output
   schemas and a retry on parse failure are required (AGT-10).
3. **Final arbitration design is not settled.** Majority vote across three
   models, or a separate judge model, or escalation to a judge only on
   disagreement. To be decided with evidence from the evaluation set (AGT-11).

## Next steps

- ALG4-79: FastAPI service skeleton
- ALG4-77: expose the AVM at `POST /v1/valuations`
- ALG4-80: extend the spike into the full four-agent graph
- ALG4-81 to ALG4-84: implement the agents
- ALG4-85: provider layer from ALG4-62 wired into the graph, with voting

## Sources

- LangGraph documentation: https://langchain-ai.github.io/langgraph/
- CrewAI documentation: https://docs.crewai.com/
- AutoGen: https://microsoft.github.io/autogen/
- Spike implementation: `ai/spikes/langgraph_spike.py`
- Provider layer and model comparison: `ai/llm_smoke_test.py`