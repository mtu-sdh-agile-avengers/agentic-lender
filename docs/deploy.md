# Deploy and CI/CD

Free for students: GitHub Actions (public repo), Azure for Students, Firebase Spark.

```
GitHub ── CI (every PR) ── tests, builds, Docker smoke test
   │
   └── Deploy (manual) ──► Azure for Students
                             ├─ Container Apps: al-web ........ AL-Web (nginx, public HTTPS)
                             ├─ Container Apps: al-core ....... AL-Core (public HTTPS)
                             ├─ Container Apps: al-ai ......... AI engine (internal only)
                             └─ Container Registry ............ images
                         ──► GitHub Releases .................. AL-Mobile APK
Firebase (agentic-lender) .... sign-in (Auth) + database (Firestore), as before
```

## What it costs

Nothing, as long as it stays a student demo:

| Piece | Free because |
|-------|--------------|
| GitHub Actions | free on public repositories |
| Container Apps | always-free grant (180,000 vCPU-s, 360,000 GiB-s, 2 M requests a month); all three apps scale to zero when idle |
| Container Registry | Standard registry free for 12 months in Azure for Students |
| Anything else | paid from the $100 Azure for Students credit; no credit card, so no surprise bill. When the credit or the year runs out, Azure stops the services until the subscription is renewed |
| Firebase | Spark plan for Auth; Firestore within its free quota |

Trade-off of scale to zero: the first request after ~5 idle minutes takes a few extra seconds.
Check spending any time in the Azure portal → Cost Management.

## CI: `.github/workflows/ci.yml`

Runs on every pull request and every push to `main`, in parallel:

| Job | What |
|-----|------|
| AI engine · tests | `pytest` on Python 3.11 |
| AL-Core · tests | `uv sync --frozen` + `pytest` on Python 3.14 |
| AL-Web · build | `npm ci` + `vite build` on Node 24 |
| AL-Mobile · build + unit tests | `assembleDebug testDebugUnitTest`; the APK is attached to the run for 7 days |
| Docker stack · smoke test | `docker compose up` (emulators), seeds the demo accounts, then `infra/ci/smoke-test.sh`: sign-in for all three roles → AL-Core `/users/me`, and AL-Core → AI engine with the shared key and the model loaded |

No secrets are needed for CI.

## One-time setup (≈15 minutes)

### 1. Azure for Students

Sign up at <https://azure.microsoft.com/free/students> with your MTU email (no credit card).

### 2. Create the Azure resources

Open <https://shell.azure.com> (Bash) and run:

```bash
git clone https://github.com/mtu-sdh-agile-avengers/agentic-lender.git
cd agentic-lender && git switch feat/ALG4-XXX-integration
bash infra/azure/setup.sh
```

Azure for Students only allows a few regions. If a step fails with `RequestDisallowedByAzure` or
`RequestDisallowedByPolicy`, list the allowed ones and run again with one of them (safe to re-run):

```bash
az policy assignment list --disable-scope-strict-match \
  --query "[].parameters.listOfAllowedLocations.value" -o json
LOCATION=swedencentral bash infra/azure/setup.sh
```

Our subscription allows `francecentral` (the default), `switzerlandnorth`, `belgiumcentral`,
`germanywestcentral` and `denmarkeast`. That is also why AL-Web is a container app and not an
Azure Static Web App: Static Web Apps exists in none of those regions.

The script prints the values for step 3.

### 3. GitHub environment `production`

Repo → Settings → Environments → New environment → `production` (needs repo admin).
Optionally add yourself as a required reviewer, so every deploy waits for a click.

**Variables** (printed by the script, plus the Firebase web app config):

| Name | Value |
|------|-------|
| `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | from the script |
| `AZURE_RESOURCE_GROUP`, `AZURE_CONTAINERAPPS_ENV`, `AZURE_ACR_NAME`, `AZURE_PULL_IDENTITY` | from the script |
| `FIREBASE_WEB_API_KEY`, `FIREBASE_WEB_APP_ID` | Firebase Console → Project settings → Your apps → Web app |

**Secrets:**

| Name | Value |
|------|-------|
| `FIREBASE_SERVICE_ACCOUNT_JSON` | the whole content of `api/secrets/service-account.json` |
| `INTERNAL_API_KEY` | a new random value, e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"` (not the dev default) |
| `GOOGLE_SERVICES_JSON` | the whole content of `mobile/app/google-services.json` |
| `HF_TOKEN`, `GROQ_API_KEY`, `GEMINI_API_KEY` | optional |

With the GitHub CLI, from the repo folder:

```bash
gh secret set FIREBASE_SERVICE_ACCOUNT_JSON --env production < api/secrets/service-account.json
gh secret set GOOGLE_SERVICES_JSON --env production < mobile/app/google-services.json
gh secret set INTERNAL_API_KEY --env production --body "$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

Azure login uses OIDC: no Azure password or key is stored in GitHub, and only jobs in the
`production` environment of this repo can log in.

### 4. Firebase Console

- Authentication → Sign-in method: **Email/Password** enabled
- Authentication → Settings → Authorized domains: add the web address printed by the script
  (`al-web.<environment domain>`)
- Demo accounts in the real project, once (from your machine, `FIREBASE_MODE=cloud` in `.env`):
  `docker compose run --rm seed python -m src.scripts.seed_demo_accounts --cloud`

## Deploying

Actions → **Deploy (Azure)** → Run workflow → pick the branch → tick what to deploy.

`workflow_dispatch` buttons only appear once the workflow file is on the default branch (`main`).
Until then, deploy any branch by pushing a tag:

```bash
git tag deploy-2026-11-20 && git push origin deploy-2026-11-20
```

The run ends with the addresses:

- **Web**: `https://al-web.<random>.francecentral.azurecontainerapps.io`
- **AL-Core**: `https://al-core.<random>.francecentral.azurecontainerapps.io` (`/docs/swagger`, `/health/dependencies`)
- **APK**: GitHub → Releases → `mobile-<run number>` (pre-release). Android: allow installing from
  this source; uninstall an older demo build first if it refuses to update.

The AI engine has no public address; only AL-Core can reach it.

## Operating it

```bash
az containerapp logs show -n al-core -g agentic-lender-rg --follow   # live logs
az containerapp logs show -n al-ai   -g agentic-lender-rg --follow
az containerapp revision list -n al-core -g agentic-lender-rg -o table
```

Roll back: run the deploy workflow on an older commit (each deploy is tagged with its commit SHA).

Production settings differ from Docker Compose: AL-Core runs with `RUN_MODE=prod` (real Firebase,
rate limiting on), and the AI engine key is the `INTERNAL_API_KEY` secret.
