# Agentic Lender

[![CI](https://github.com/mtu-sdh-agile-avengers/agentic-lender/actions/workflows/ci.yml/badge.svg)](https://github.com/mtu-sdh-agile-avengers/agentic-lender/actions/workflows/ci.yml)

| Part | Folder | Stack |
|------|--------|-------|
| AL-Core (REST API) | `api/` | FastAPI, Firebase Admin |
| AL-AI Engine | `ai/` | FastAPI, scikit-learn, LangGraph |
| AL-Web (brokers, underwriters) | `web/` | React, Vite |
| AL-Mobile (borrowers) | `mobile/` | Kotlin, Jetpack Compose |

## Quick start

```bash
docker compose up --build
```

Then open http://localhost:5173 and sign in as `broker@demo.agenticlender.ie` / `Password1`.
Full instructions, demo accounts and mobile setup: [docs/run-guide.md](docs/run-guide.md).
Deployment (Azure for Students) and CI/CD: [docs/deploy.md](docs/deploy.md).

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md).
