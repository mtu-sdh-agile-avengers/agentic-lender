# Firebase Emulator Suite: Auth (9099), Firestore (8080), Emulator UI (4000).
# (The UI starts on its own because firebase.json enables it.)
#
# Shared by the whole team so everyone runs identical emulators. The config is
# not baked in: compose mounts api/firebase.json and the Firestore rules.
#
# The Firestore emulator and the UI are Java/Node downloads; they are fetched
# at build time so `docker compose up` works offline afterwards.

FROM node:22-bookworm-slim AS node

# Firestore emulator needs Java 21
FROM eclipse-temurin:21-jre

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

ARG FIREBASE_TOOLS_VERSION=15.35.0
RUN npm install --global --no-fund --no-audit firebase-tools@${FIREBASE_TOOLS_VERSION} \
 && firebase setup:emulators:firestore \
 && firebase setup:emulators:ui \
 && npm cache clean --force

WORKDIR /firebase

# "demo-" projects never touch real Firebase; no login or credentials needed
ENV FIREBASE_PROJECT_ID=demo-agentic-lender

EXPOSE 4000 4400 4500 8080 9099

HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --start-interval=2s --retries=3 \
    CMD node -e "Promise.all([fetch('http://127.0.0.1:9099/'),fetch('http://127.0.0.1:8080/')]).then(r=>process.exit(r.every(x=>x.ok)?0:1)).catch(()=>process.exit(1))"

CMD ["sh", "-c", "exec firebase emulators:start --project \"$FIREBASE_PROJECT_ID\" --only auth,firestore"]
