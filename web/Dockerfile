# AL-Web production image: the static Vite build served by nginx on port 80.
# (Local development does not use this: docker-compose.yml runs the Vite dev server.)
#
#   docker build -t al-web ./web \
#     --build-arg VITE_API_BASE_URL=https://al-core.example.com \
#     --build-arg VITE_FIREBASE_API_KEY=... --build-arg VITE_FIREBASE_APP_ID=...
#
# The VITE_* values end up in the JavaScript bundle (they are public by design: the Firebase web
# config and the API address), so build arguments are fine here; never pass real secrets this way.

FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
ARG VITE_FIREBASE_MODE=cloud
ARG VITE_FIREBASE_PROJECT_ID=agentic-lender
ARG VITE_FIREBASE_AUTH_DOMAIN=agentic-lender.firebaseapp.com
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_APP_ID
ARG VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
