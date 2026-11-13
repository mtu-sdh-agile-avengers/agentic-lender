# Run guide: the whole stack locally

One command starts everything the clients need: the Firebase emulators, AL-Core,
the AI engine and the web app. Mobile runs from Android Studio and connects to it.

## 1. Prerequisites

- **Docker Desktop** (Windows/macOS) or Docker Engine + Compose v2
- **Android Studio** with an emulator image that has Google APIs (mobile only)
- Free ports: `8000 8001 5173 9099 8080 4000 4400 4500`
- Running AL-Web outside Docker: **Node 24.12+** (the Firebase JS SDK requires it)

## 2. Start it

```bash
cp .env.example .env        # optional: every value has a working default
docker compose up --build   # first run builds the images (a few minutes)
```

Later runs: `docker compose up`. Stop: `Ctrl+C`, or `docker compose down`.

What starts:

| Service    | URL                                   | What it is                                   |
|------------|---------------------------------------|----------------------------------------------|
| `firebase` | http://localhost:4000                 | Emulator UI (Auth :9099, Firestore :8080)    |
| `seed`     | (exits after a few seconds)           | Creates the demo accounts below              |
| `api`      | http://localhost:8000/docs/swagger    | AL-Core                                      |
| `ai`       | http://localhost:8001/ready           | AL-AI Engine (localhost only)                |
| `web`      | http://localhost:5173                 | AL-Web (hot reload)                          |

First start of `ai` downloads the valuation model from Hugging Face (cached in a
volume afterwards), so it takes a little longer to become ready.

## 3. Demo accounts

Created by `seed` on every start (the emulators keep data in memory only):

| Role                        | Email                             | Password    | Use on |
|-----------------------------|-----------------------------------|-------------|--------|
| `retail_borrower`           | `borrower@demo.agenticlender.ie`  | `Password1` | mobile |
| `mortgage_broker`           | `broker@demo.agenticlender.ie`    | `Password1` | web    |
| `underwriting_bank_officer` | `officer@demo.agenticlender.ie`   | `Password1` | web    |

New accounts registered from the mobile app get a borrower profile automatically.

## 4. Mobile

1. Keep `docker compose up` running.
2. Open `mobile/` in Android Studio, run on an **Android emulator**.
   The app reaches your computer at `10.0.2.2` (AL-Core `:8000`, Auth emulator `:9099`).
3. Sign in as the borrower.

Physical phone on the same Wi-Fi: add your computer's LAN IP to
`~/.gradle/gradle.properties` and rebuild:

```properties
al.apiBaseUrl=http://192.168.1.20:8000
al.emulatorHost=192.168.1.20
```

## 5. Check the wiring

```bash
curl http://localhost:8000/health                 # AL-Core is up
curl http://localhost:8000/health/dependencies    # AL-Core -> AI engine: reachable, key accepted, model loaded
curl http://localhost:8001/ready                  # AI engine: model_loaded: true
```

Get an ID token without a client and call AL-Core like the apps do:

```bash
TOKEN=$(curl -s -X POST "http://localhost:9099/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=any" \
  -H "Content-Type: application/json" \
  -d '{"email":"broker@demo.agenticlender.ie","password":"Password1","returnSecureToken":true}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['idToken'])")
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/users/me
```

## 6. Sprint demo script

1. `docker compose up`
2. Web, http://localhost:5173: sign in as the **broker**. The top bar and
   Settings show the profile fetched from AL-Core (name, role).
3. Mobile emulator: sign in as the **borrower**. Home greets the borrower by
   the name stored in Firestore.
4. http://localhost:8001/ready shows `"model_loaded": true`;
   http://localhost:8000/health/dependencies shows `"internal_key_accepted": true`.

## 7. Working on one service

Run the rest in Docker and your own service natively:

```bash
docker compose up firebase seed ai      # then run AL-Core yourself on :8000
docker compose up firebase seed api ai  # then `npm run dev` in web/
```

Each service's own `.env.example` (`api/`, `ai/`, `web/`) has the values for a
native run; they point at `localhost`, which reaches the containers' ports.

## 8. Real Firebase (cloud mode)

By default everything runs on the emulators. To use the real Firebase project
`agentic-lender` instead (real accounts, data that survives restarts):

**One-time setup in Firebase Console** (whoever owns the project)

- Authentication → Sign-in method → enable **Email/Password**
- Firestore: the database ID must match `FIRESTORE_PROD_DATABASE_NAME` (default `default`)
- Project settings → Service accounts → **Generate new private key**
- Project settings → Your apps → Android app `io.github.mtu_sdh_agile_avengers.agenticlender.client` (for mobile)

**On your machine** (get the values privately from Pavlo/Hlib, never commit them)

1. Save the key as `api/secrets/service-account.json` (gitignored).
2. In the root `.env`:
   ```properties
   FIREBASE_MODE=cloud
   FIREBASE_WEB_API_KEY=AIza...
   FIREBASE_WEB_APP_ID=1:158281929652:web:...
   ```
3. `docker compose up --build`. AL-Core logs `Firebase initialized successfully (real project: agentic-lender)`.
4. Demo accounts are not created automatically in the real project. Once, by hand:
   ```bash
   docker compose run --rm seed python -m src.scripts.seed_demo_accounts --cloud
   ```
5. Mobile: put the Android app's `google-services.json` in `mobile/app/` (gitignored, share it
   privately; the app is registered as `io.github.mtu_sdh_agile_avengers.agenticlender.client`) and
   add to `~/.gradle/gradle.properties`:
   ```properties
   al.firebaseMode=cloud
   ```
   Then Sync and Run. Remove `al.firebaseMode` to go back to the emulator (the JSON file can stay).

Back to the emulators: `FIREBASE_MODE=emulator` (or delete the line) and restart.
All three parts must use the same mode: a token from the real project is rejected
by AL-Core in emulator mode, and the other way round.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `port is already allocated` | Something else uses the port (often a local `firebase emulators:start` or uvicorn). Stop it. |
| Web: "Your session could not be verified" | Project IDs differ. AL-Core, web and mobile must all use `demo-agentic-lender`. |
| `/health/dependencies`: `internal_key_accepted: false` | `INTERNAL_API_KEY` differs between AL-Core and the AI engine. Set it once in the root `.env`. |
| `/ready` answers 503, `model_loaded: false` | Model download failed. Check `docker compose logs ai`; set `HF_TOKEN` if the repo is private. |
| Mobile: "Can't reach the server" | Use an emulator (not a phone) or set `al.apiBaseUrl`; check `docker compose ps`. |
| Mobile: "This app is for borrowers" | Expected for broker/officer accounts: they use the web app. |
| Emulator data is gone after restart | By design. `seed` recreates the demo accounts on every `up`. |
| Cloud mode: AL-Core exits with `Service account key not found` | Put the key at `api/secrets/service-account.json`. |
| Cloud mode, web: "Email and password sign-in is not enabled" | Enable Email/Password in Firebase Console → Authentication. |
| Cloud mode: `/users/me` answers 404 for a demo account | Run the `--cloud` seed command above. |
