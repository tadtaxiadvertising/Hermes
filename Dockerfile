# =============================================================================
# Dockerfile — Hermes Gateway for Easypanel (submodule-aware build)
# =============================================================================
# Easypanel does NOT run git submodule init during clone.
# This Dockerfile handles it: if hermes-agent/ is empty (Easypanel clone),
# it clones from GitHub during build. If it has files (local build with
# submodule init), it copies them directly.
#
# Image: ~400-500MB (slim, no Playwright/Node.js/s6-overlay)
# RAM: 512MB hard limit
# Port: 8642 (OpenAI-compatible API + /health endpoint)
# =============================================================================

# ---------- Stage 1: Source acquisition ----------
# If hermes-agent/ is empty (Easypanel clone without submodule init),
# clone it from GitHub. Otherwise, just copy from build context.
FROM debian:13.4-slim AS source

ARG HERMES_AGENT_REPO=https://github.com/tadtaxiadvertising/hermes-agent.git
ARG HERMES_AGENT_REF=main

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Try copying from build context first. If the dir is empty (Easypanel),
# .dockerignore still allows the empty dir marker, and we fall back to clone.
COPY hermes-agent/ /opt/hermes-agent-context/

# Check if context has actual source files. If not, clone from GitHub.
RUN if [ ! -f "/opt/hermes-agent-context/pyproject.toml" ]; then \
    echo "[build] hermes-agent/ empty — cloning from GitHub" && \
    git clone --depth 1 --branch "${HERMES_AGENT_REF}" "${HERMES_AGENT_REPO}" /opt/hermes-agent && \
    rm -rf /opt/hermes-agent/.git; \
    else \
    echo "[build] hermes-agent/ from build context (submodule)" && \
    cp -a /opt/hermes-agent-context/. /opt/hermes-agent/; \
    fi

# ---------- Stage 2: uv + gosu ----------
FROM ghcr.io/astral-sh/uv:0.11.6-python3.13-bookworm-slim AS uv_source

FROM debian:13.4-slim AS gosu_source
ARG GOSU_VERSION=1.17
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && \
    curl -fsSL -o /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/${GOSU_VERSION}/gosu-$(dpkg --print-architecture)" && \
    chmod +x /usr/local/bin/gosu && \
    rm -rf /var/lib/apt/lists/*

# ---------- Stage 3: Runtime ----------
FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates curl git ffmpeg tini procps libolm-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=uv_source /usr/local/bin/uv /usr/local/bin/uvx /usr/local/bin/
COPY --from=gosu_source /usr/local/bin/gosu /usr/local/bin/gosu

RUN useradd -u 1000 -m -d /opt/data -s /bin/bash hermes

WORKDIR /opt/hermes

# ---------- Python deps (layer-cached) ----------
COPY --from=source /opt/hermes-agent/pyproject.toml /opt/hermes-agent/uv.lock ./
RUN touch ./README.md
RUN uv sync --frozen --no-install-project \
    --extra all --extra messaging --extra web --extra anthropic --extra matrix

# ---------- Source code ----------
COPY --from=source /opt/hermes-agent/ .

# ---------- Config overlay from root repo ----------
COPY SOUL.md     /opt/data-seed/SOUL.md
COPY config.yaml /opt/data-seed/config.yaml

RUN uv pip install --no-cache-dir --no-deps -e "." && \
    printf 'docker-easypanel\n' > /opt/hermes/.install_method

# ---------- Entrypoint ----------
COPY --from=source /opt/hermes-agent/docker/easypanel-entrypoint.sh /opt/hermes/docker/easypanel-entrypoint.sh
RUN chmod +x /opt/hermes/docker/easypanel-entrypoint.sh

RUN printf '\n# --- Overlay seed ---\n' >> /opt/hermes/docker/easypanel-entrypoint.sh && \
    printf 'if [ ! -f "$HERMES_HOME/SOUL.md" ] && [ -f "/opt/data-seed/SOUL.md" ]; then\n' >> /opt/hermes/docker/easypanel-entrypoint.sh && \
    printf '    cp /opt/data-seed/SOUL.md "$HERMES_HOME/SOUL.md"\n' >> /opt/hermes/docker/easypanel-entrypoint.sh && \
    printf '    chown hermes:hermes "$HERMES_HOME/SOUL.md"\n' >> /opt/hermes/docker/easypanel-entrypoint.sh && \
    printf 'fi\n' >> /opt/hermes/docker/easypanel-entrypoint.sh && \
    printf 'if [ ! -f "$HERMES_HOME/config.yaml" ] && [ -f "/opt/data-seed/config.yaml" ]; then\n' >> /opt/hermes/docker/easypanel-entrypoint.sh && \
    printf '    cp /opt/data-seed/config.yaml "$HERMES_HOME/config.yaml"\n' >> /opt/hermes/docker/easypanel-entrypoint.sh && \
    printf '    chown hermes:hermes "$HERMES_HOME/config.yaml"\n' >> /opt/hermes/docker/easypanel-entrypoint.sh && \
    printf '    chmod 640 "$HERMES_HOME/config.yaml"\n' >> /opt/hermes/docker/easypanel-entrypoint.sh && \
    printf 'fi\n' >> /opt/hermes/docker/easypanel-entrypoint.sh

# ---------- Runtime ----------
ENV HERMES_HOME=/opt/data
ENV HERMES_WRITE_SAFE_ROOT=/opt/data
ENV HERMES_DISABLE_LAZY_INSTALLS=1
ENV HERMES_LAZY_INSTALL_TARGET=/opt/data/lazy-packages
ENV PATH="/opt/hermes/.venv/bin:${PATH}"

RUN mkdir -p /opt/data /opt/data-seed && chown hermes:hermes /opt/data

VOLUME [ "/opt/data" ]
EXPOSE 8642

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${API_SERVER_PORT:-8642}/health || exit 1

ENTRYPOINT [ "tini", "--", "/opt/hermes/docker/easypanel-entrypoint.sh" ]
CMD [ "hermes", "gateway", "run" ]
