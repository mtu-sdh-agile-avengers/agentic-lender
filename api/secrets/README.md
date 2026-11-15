# api/secrets (never committed)

Put the Firebase **service account key** here as `service-account.json` to run
AL-Core against the real Firebase project (`FIREBASE_MODE=cloud`).

1. Firebase Console → Project settings → Service accounts → **Generate new private key**
2. Save the downloaded file here as `service-account.json`

Everything in this folder except this README is gitignored, and `api/.dockerignore`
keeps `*.json` out of the image: Docker Compose mounts the folder read-only at
`/run/secrets/firebase` instead. Share the key with teammates privately, never in git or chat history you don't control.
