# Agentic Lender

[![CI](https://github.com/mtu-sdh-agile-avengers/agentic-lender/actions/workflows/ci.yml/badge.svg)](https://github.com/mtu-sdh-agile-avengers/agentic-lender/actions/workflows/ci.yml)

**Agentic Lender (AL)** is a prototype digital lending platform that automates process of arranging a mortgage 
or home equity line of credit (HELOC) through **Distributed Ledger Technology (DLT)**, combining 
**automated property valuation models (AVM)** with **multiagent AI committees** and **smart contracts**.

> [!WARNING]
> This page is still `in progress`. If you have spotted any errors or
> would like to suggest something to us [please open an issue](CONTRIBUTING.md#what-about-a-issues).

---

It consists of the four subsystems:

| Part | Type | Folder | Stack |
|------|------|--------|-------|
| AL-Core (REST API, Blockchain) | Core | `api/`, `contracts/` | FastAPI, Firebase Admin SDK, Etherum (Solidity, Hardhat, web3.py),  |
| AL-AI Engine | Internal Service |`ai/` | FastAPI, scikit-learn, LangGraph |
| AL-Web (brokers, underwriters) | Client (web) | `web/` | React, Vite |
| AL-Mobile (borrowers) | Client (android) | `mobile/` | Kotlin, Jetpack Compose |

> [!TIP]
> If you really have interest in this project we would reccomend you to study our [documentation](docs).

## Quick start

To run our system locally you would need a [Docker](https://www.docker.com/products/docker-desktop/), use following command:

```bash
docker compose up --build
```

Then open http://localhost:5173 (web client) and sign in as `broker@demo.agenticlender.ie` with password: "`Password1`".

Full instructions, demo accounts and mobile setup are available in: [docs/run-guide.md](docs/run-guide.md). Deployment (Azure for Students) 
and CI/CD details located in: [docs/deploy.md](docs/deploy.md).

## Contributing

Pull requests are very welcome! Please take a look a [CONTRIBUTING.md](CONTRIBUTING.md) and [team_workflow.md](docs/team-workflow.md) for
detailed guidelines and conventions used!

## License

This project is under [MIT license](https://choosealicense.com/licenses/mit/). Please familiarize yourself with [license file](LICENSE.md) for more
information.
