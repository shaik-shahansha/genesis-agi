# syntax=docker/dockerfile:1
# =============================================================================
# Genesis Minds — single-container image
#
#   one container, one port:  nginx (front door)
#                               ├── /            -> Next.js web workspace (3000)
#                               └── /api,/health -> FastAPI (8000)
#                             redis (optional) -> LLM response cache (6379)
#
# Supervised by deploy/docker/entrypoint.sh, PID 1 = tini.
# Runs as non-root (uid 10001). All persistent state lives under /data.
# =============================================================================


# -----------------------------------------------------------------------------
# Stage 1 — build the web workspace (Next.js standalone)
# -----------------------------------------------------------------------------
FROM node:20-bookworm-slim AS web-build

WORKDIR /web

# A package-lock.json is now committed, so `npm ci` gives a reproducible,
# lockfile-exact install (evolution-plan item A5).
COPY web-playground/package.json web-playground/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY web-playground/ ./

# NOTE: NEXT_PUBLIC_* values are inlined into the client bundle at BUILD time,
# so they must be supplied as build args (not runtime env).
# NEXT_PUBLIC_API_URL is intentionally EMPTY: the browser then calls /api/v1/...
# on the same origin, which is what makes the single-container, single-port
# deployment work (no CORS, no baked hostname, no TLS bypass).
ARG NEXT_PUBLIC_API_URL=""
ARG NEXT_PUBLIC_ENVIRONMENT=production
ARG NEXT_PUBLIC_FIREBASE_API_KEY=""
ARG NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=""
ARG NEXT_PUBLIC_FIREBASE_PROJECT_ID=""
ARG NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=""
ARG NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=""
ARG NEXT_PUBLIC_FIREBASE_APP_ID=""
ARG NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID=""

ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_ENVIRONMENT=${NEXT_PUBLIC_ENVIRONMENT} \
    NEXT_PUBLIC_FIREBASE_API_KEY=${NEXT_PUBLIC_FIREBASE_API_KEY} \
    NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=${NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN} \
    NEXT_PUBLIC_FIREBASE_PROJECT_ID=${NEXT_PUBLIC_FIREBASE_PROJECT_ID} \
    NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=${NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET} \
    NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=${NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID} \
    NEXT_PUBLIC_FIREBASE_APP_ID=${NEXT_PUBLIC_FIREBASE_APP_ID} \
    NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID=${NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID}

# Invoke `next build` directly rather than `npm run build`, so the repo's
# NODE_TLS_REJECT_UNAUTHORIZED=0 wrapper (SEC-18) is NOT applied to the build.
RUN ./node_modules/.bin/next build


# -----------------------------------------------------------------------------
# Stage 2 — install Python dependencies into a virtualenv
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS python-deps

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app
COPY pyproject.toml README.md alembic.ini ./
COPY genesis ./genesis
COPY alembic ./alembic

# `cache` extra adds the optional redis client used by genesis/models/cache.py.
# Vision (opencv/deepface/fer) and browser (browser-use/playwright) extras are
# deliberately NOT installed: they are optional, large (deepface pulls
# TensorFlow), and unused in production mode (DISABLE_MULTIMODAL=true).
RUN pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -e ".[cache]"


# -----------------------------------------------------------------------------
# Stage 3 — runtime
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PATH="/opt/venv/bin:$PATH" \
    HOME=/home/genesis \
    GENESIS_HOME=/data/.genesis \
    DATA_DIR=/data/.genesis/data \
    MINDS_DIR=/data/.genesis/minds \
    LOGS_DIR=/data/.genesis/logs \
    API_HOST=127.0.0.1 \
    API_PORT=8000 \
    WEB_PORT=3000 \
    FRONT_PORT=8080

# nginx  -> single front door
# redis  -> optional LLM cache (see ENABLE_REDIS)
# tini   -> PID 1, correct signal forwarding + zombie reaping
# curl   -> healthcheck
# libstdc++6/libatomic1 -> runtime deps of the Node binary copied in below
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        nginx \
        redis-server \
        tini \
        curl \
        ca-certificates \
        libstdc++6 \
        libatomic1 \
 && rm -rf /var/lib/apt/lists/* /var/www/html

# Non-root runtime user. nginx and redis are configured to write only to
# /tmp and /data so they can run unprivileged.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin genesis \
 && mkdir -p \
        /data/.genesis/data \
        /data/.genesis/minds \
        /data/.genesis/logs \
        /data/redis \
        /tmp/nginx/client_body \
        /tmp/nginx/proxy \
        /tmp/nginx/fastcgi \
        /tmp/nginx/uwsgi \
        /tmp/nginx/scgi \
 && chown -R genesis:genesis /data /tmp/nginx /home/genesis

WORKDIR /app

# Python env + source (source stays root-owned: the runtime user cannot modify
# its own code, which also blocks recursive self-modification of policy code).
COPY --from=python-deps /opt/venv /opt/venv
COPY --from=python-deps /app /app

# Web workspace build output (standalone server + static assets)
COPY --from=web-build /web/.next/standalone /webapp
COPY --from=web-build /web/.next/static /webapp/.next/static

# Node runtime for the standalone server.
# The runtime base is python:3.11-slim, which has no Node.js. Copying just the
# `node` binary is far cheaper than installing a second toolchain (the Next.js
# standalone bundle already contains its own node_modules). Both stages are
# Debian bookworm, so the binary's shared-library deps are satisfied by
# libstdc++6/libatomic1 installed above.
COPY --from=web-build /usr/local/bin/node /usr/local/bin/node

# Container plumbing
COPY deploy/docker/nginx.conf /app/deploy/docker/nginx.conf
COPY deploy/docker/entrypoint.sh /app/deploy/docker/entrypoint.sh
RUN chmod +x /app/deploy/docker/entrypoint.sh

USER genesis

# The only exposed port: everything is served through nginx.
EXPOSE 8080

VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:8080/health" || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/deploy/docker/entrypoint.sh"]
