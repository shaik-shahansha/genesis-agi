#!/usr/bin/env bash
# =============================================================================
# Genesis Minds — single-container supervisor
#
# Starts and supervises, inside ONE container:
#   redis      (optional)  LLM response cache
#   api        (critical)  FastAPI / uvicorn on 127.0.0.1:8000
#   web        (critical)  Next.js standalone server on 127.0.0.1:3000
#   nginx      (critical)  single front door on 0.0.0.0:8080
#   mind-*     (optional) 24/7 Mind daemons (START_MINDS)
#
# If a critical process exits, the container exits non-zero so the Docker
# restart policy brings the whole unit back in a known-good state.
# =============================================================================
set -Eeuo pipefail

log() { printf '[genesis] %s\n' "$*"; }
warn() { printf '[genesis][warn] %s\n' "$*" >&2; }

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
FRONT_PORT="${FRONT_PORT:-8080}"
ENABLE_REDIS="${ENABLE_REDIS:-true}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-false}"
START_MINDS="${START_MINDS:-}"

export GENESIS_HOME="${GENESIS_HOME:-/data/.genesis}"
export DATA_DIR="${DATA_DIR:-$GENESIS_HOME/data}"
export MINDS_DIR="${MINDS_DIR:-$GENESIS_HOME/minds}"
export LOGS_DIR="${LOGS_DIR:-$GENESIS_HOME/logs}"

# ---------------------------------------------------------------------------
# Process bookkeeping
# ---------------------------------------------------------------------------
critical_names=(); critical_pids=()
optional_names=(); optional_pids=()

start_critical() {
    local name="$1"; shift
    log "starting ${name}: $*"
    "$@" &
    critical_names+=("$name"); critical_pids+=("$!")
}

start_optional() {
    local name="$1"; shift
    log "starting ${name} (optional): $*"
    "$@" &
    optional_names+=("$name"); optional_pids+=("$!")
}

shutdown() {
    log "shutting down"
    for pid in "${critical_pids[@]:-}" "${optional_pids[@]:-}"; do
        [ -n "${pid:-}" ] || continue
        kill -TERM "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
}
trap 'shutdown; exit 0' TERM INT

# ---------------------------------------------------------------------------
# Persistent state checks
# ---------------------------------------------------------------------------
mkdir -p "$DATA_DIR" "$MINDS_DIR" "$LOGS_DIR" /data/redis
log "state: GENESIS_HOME=$GENESIS_HOME"
log "state: DATA_DIR=$DATA_DIR MINDS_DIR=$MINDS_DIR LOGS_DIR=$LOGS_DIR"

# Surface the defaults that must never reach production (SEC-08 / T-16).
secret="${API_SECRET_KEY:-${SECRET_KEY:-}}"
if [ -z "$secret" ] || [ "$secret" = "your-secret-key-change-this-in-production" ]; then
    warn "API_SECRET_KEY is unset or still the default value."
    warn "JWTs are forgeable. Set API_SECRET_KEY in .env before exposing this host."
fi

# ---------------------------------------------------------------------------
# 1. Redis (optional LLM response cache)
# ---------------------------------------------------------------------------
if [ "$ENABLE_REDIS" = "true" ]; then
    start_optional redis redis-server \
        --bind 127.0.0.1 --port 6379 \
        --daemonize no \
        --save "" --appendonly no \
        --dir /data/redis \
        --logfile "" \
        --loglevel warning
    export REDIS_URL="redis://127.0.0.1:6379"
    log "REDIS_URL=$REDIS_URL"
else
    log "redis disabled (ENABLE_REDIS=$ENABLE_REDIS)"
fi

# ---------------------------------------------------------------------------
# 2. Database migrations
#
# Default is OFF because the application self-initialises the schema through
# SQLAlchemy `Base.metadata.create_all()` (genesis/database/base.py:init_db).
# Enable with RUN_MIGRATIONS=true for a versioned deployment.
#
# Safety: a database created by create_all() has no `alembic_version` table.
# Running `alembic upgrade head` against it would fail on "table already
# exists", so we detect that case and `alembic stamp head` instead.
# ---------------------------------------------------------------------------
if [ "$RUN_MIGRATIONS" = "true" ]; then
    db_file="$GENESIS_HOME/genesis.db"
    if [ -f "$db_file" ]; then
        state="$(python - <<'PY'
import os, sqlite3, sys
from pathlib import Path

db = Path(os.environ.get("GENESIS_HOME", "/data/.genesis")) / "genesis.db"
try:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.close()
except Exception as exc:            # pragma: no cover - defensive
    print(f"unknown:{exc}")
    sys.exit(0)

if "minds" in tables and "alembic_version" not in tables:
    print("stamp")
elif "alembic_version" in tables:
    print("upgrade")
else:
    print("fresh")
PY
)"
        case "$state" in
            stamp)
                log "existing un-versioned database detected -> alembic stamp head"
                alembic stamp head
                ;;
            unknown*)
                warn "could not inspect database (${state}); skipping migrations"
                state="skip"
                ;;
        esac
        if [ "$state" = "skip" ]; then :; else
            log "applying database migrations"
            alembic upgrade head
        fi
    else
        log "no existing database found; applying migrations from scratch"
        alembic upgrade head
    fi
else
    log "migrations disabled (RUN_MIGRATIONS=$RUN_MIGRATIONS); app will self-initialise schema"
fi

# ---------------------------------------------------------------------------
# 3. Genesis API
# ---------------------------------------------------------------------------
start_critical api \
    genesis server --host 127.0.0.1 --port "$API_PORT"

# ---------------------------------------------------------------------------
# 4. Web workspace (Next.js standalone)
# ---------------------------------------------------------------------------
if [ -f /webapp/server.js ]; then
    start_critical web \
        env HOSTNAME=127.0.0.1 PORT="$WEB_PORT" NODE_ENV=production \
        node /webapp/server.js
else
    warn "/webapp/server.js not found - the web workspace was not built."
    warn "nginx will still serve the API, but / will return 502."
fi

# ---------------------------------------------------------------------------
# 5. nginx (front door) — started last so upstreams are already listening
# ---------------------------------------------------------------------------
start_critical nginx \
    nginx -c /app/deploy/docker/nginx.conf -g "daemon off;"

# ---------------------------------------------------------------------------
# 6. Optional 24/7 Mind daemons
#    START_MINDS="GMD-2025-XXXX-XXXX,GMD-2025-YYYY-YYYY"
#
#    These are non-critical: a crashing Mind daemon must not take down the API
#    or the web workspace. Daemons started through the UI/API behave the same way.
# ---------------------------------------------------------------------------
if [ -n "$START_MINDS" ]; then
    IFS=',' read -ra _minds <<< "$START_MINDS"
    for _m in "${_minds[@]}"; do
        _m="$(printf '%s' "$_m" | tr -d '[:space:]')"
        [ -n "$_m" ] || continue
        start_optional "mind:$_m" python -m genesis.daemon --mind-id "$_m"
    done
fi

log "all services started (critical: ${critical_names[*]})"
log "front door listening on 0.0.0.0:${FRONT_PORT}"

# ---------------------------------------------------------------------------
# Supervision loop: poll critical processes; exit if one dies so the
# container restart policy reinstates a clean state.
# ---------------------------------------------------------------------------
while true; do
    sleep 2
    for i in "${!critical_pids[@]}"; do
        pid="${critical_pids[$i]}"
        if ! kill -0 "$pid" 2>/dev/null; then
            warn "critical process '${critical_names[$i]}' (pid $pid) exited"
            shutdown
            exit 1
        fi
    done
    # Optional processes are restarted once if they die unexpectedly.
    for i in "${!optional_pids[@]}"; do
        pid="${optional_pids[$i]}"
        name="${optional_names[$i]}"
        if ! kill -0 "$pid" 2>/dev/null; then
            warn "optional process '$name' (pid $pid) exited (not restarting automatically)"
            unset 'optional_pids[i]'
        fi
    done
done
