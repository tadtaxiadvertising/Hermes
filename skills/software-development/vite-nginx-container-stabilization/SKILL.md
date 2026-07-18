---
name: vite-nginx-container-stabilization
description: "Debug and fix Vite SPA + Nginx static container deployments: Service Worker precache/404 issues, Nginx crash-loops under EasyPanel/Docker, healthcheck failures, and hashed-asset path mismatches."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [vite, nginx, docker, easypanel, service-worker, spa, deployment, crash-loop, 404, static-assets]
    related_skills: [systematic-debugging, plan]
---

# Vite + Nginx Container Stabilization

## When to Use

Use when a Vite SPA served by Nginx in a Docker container (EasyPanel, Nixpacks, or raw Docker) exhibits any of:

- **404 on static assets** requested by a Service Worker (SW) that precaches paths Vite doesn't produce.
- **Nginx crash-loop** — container receives repeated SIGQUIT / restarts, healthchecks fail, or the process won't stay in foreground.
- **SW install failures** — `cache.addAll()` rejects because a precached path returns 404.
- **Hashed asset path mismatch** — the SW hardcodes unhashed asset names (e.g., `/assets/player.css`) but Vite emits hashed names (e.g., `assets/main-6jpdjePn.css`).

## Overview

Vite SPA + Nginx static is a common deployment pattern for kiosk/DOOH apps (no Node.js runtime in production — just `nginx:alpine` serving `dist/`). Two failure classes dominate:

1. **Asset path mismatch between SW expectations and Vite output** — Vite content-hashes all assets by default (`assetFileNames: 'assets/[name]-[hash][extname]'`), but Service Workers often hardcode unhashed paths for precaching. This causes `cache.addAll()` to reject, breaking the SW install — and every navigation retries, creating a failure loop.

2. **Nginx container instability under healthcheck-orchestrated platforms** — Dockerfiles that only write `conf.d/default.conf` but never override `/etc/nginx/nginx.conf` lack explicit `worker_processes`, `pid`, logging, and `HEALTHCHECK`. EasyPanel (or any orchestrator) sends SIGQUIT when probes fail, restarting the container.

## The Fix Patterns

### Pattern 1: SW Precache Tolerance — Don't Hardcode Hashed Paths

**Root cause:** Vite rewrites `<link>` and `<script>` tags in `index.html` to use hashed filenames at build time. The SW, compiled as a separate Rollup input entry, carries hardcoded string literals (`'/assets/player.css'`) that reference the *source* path — a file that never exists in `dist/`.

**Fix strategy (in order of preference):**

1. **Shell-only precache** — reduce `SHELL_ASSETS` to `['/', '/index.html']` only. The SW's fetch handler (stale-while-revalidate) caches hashed assets on-demand when the browser loads `index.html` (which references the correct hashes). This is the cleanest approach.

2. **Fault-tolerant install** — replace `cache.addAll(SHELL_ASSETS)` with `Promise.allSettled()` wrapping individual `fetch()` + `cache.put()`. A single 404 no longer aborts the entire install event. Essential even with shell-only precache, since transient network errors could otherwise break the SW.

```typescript
// BAD — cache.addAll rejects entirely on any single failure
caches.open(SHELL_CACHE).then(cache => cache.addAll(SHELL_ASSETS))

// GOOD — individual fetches, tolerant to failures
caches.open(SHELL_CACHE).then(cache =>
  Promise.allSettled(
    SHELL_ASSETS.map(asset =>
      fetch(asset, { cache: 'no-cache' })
        .then(resp => resp.ok ? cache.put(asset, resp.clone()) : null)
        .catch(() => null)
    )
  )
)
```

3. **Dedicated SW location in Nginx** — the SW file itself (`sw.js`) must be served with `no-cache, must-revalidate` headers so clients always get the latest version:

```nginx
location = /sw.js {
    add_header Cache-Control "no-cache, must-revalidate";
    try_files $uri =404;
}
```

### Pattern 2: Nginx Config Hardening for Docker/EasyPanel

**Root cause:** The default `nginx.conf` in the `nginx:alpine` image may not include `daemon off;` reliably across versions, and Dockerfiles that only write `conf.d/default.conf` leave the main config undefined. Without an explicit `HEALTHCHECK`, Docker/EasyPanel can't verify nginx is alive and may kill/restart it.

**Fix — write BOTH `/etc/nginx/nginx.conf` AND `/etc/nginx/conf.d/default.conf`:**

The Dockerfile must override the main `nginx.conf` with explicit worker config, PID path, logging to stdout/stderr, and `include /etc/nginx/conf.d/*.conf`:

```dockerfile
# Write main nginx.conf (not just conf.d/default.conf)
RUN printf '%s\n' \
  'worker_processes auto;' \
  'pid /var/run/nginx.pid;' \
  'events { worker_connections 1024; }' \
  'http {' \
  '    include /etc/nginx/mime.types;' \
  '    default_type application/octet-stream;' \
  '    access_log /dev/stdout;' \
  '    error_log /dev/stderr warn;' \
  '    sendfile on;' \
  '    tcp_nopush on;' \
  '    keepalive_timeout 65;' \
  '    gzip on;' \
  '    gzip_types text/plain text/css application/javascript application/json image/svg+xml;' \
  '    gzip_min_length 1024;' \
  '    include /etc/nginx/conf.d/*.conf;' \
  '}' \
  > /etc/nginx/nginx.conf
```

**Essential server block elements:**

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Health endpoint (for EasyPanel/Docker probes)
    location /health {
        access_log off;
        add_header Content-Type application/json;
        add_header Cache-Control "no-store";
        return 200 '{"status":"OK","service":"tad-player"}';
    }

    # Vite hashed assets — immutable cache
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }

    # Service Worker — no aggressive cache
    location = /sw.js {
        add_header Cache-Control "no-cache, must-revalidate";
        try_files $uri =404;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-store, must-revalidate";
    }

    # 404 fallback to SPA (prevents raw nginx 404 to client)
    error_page 404 /index.html;
}
```

**Docker HEALTHCHECK directive:**

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:80/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

`daemon off;` is critical — it keeps nginx as PID 1 in the foreground. Without it, nginx daemonizes, the CMD returns, and Docker sees the container as "exited."

## Verification Protocol

After applying fixes, run these checks (fresh — never cite prior results):

```bash
# 1. TypeScript compiles
cd apps/<service> && ./node_modules/.bin/tsc --noEmit -p tsconfig.json

# 2. Vite build succeeds
cd apps/<service> && npm run build

# 3. SW no longer references non-existent paths
grep -c "player.css" dist/sw.js  # should be 0

# 4. SW uses fault-tolerant install
grep -c "allSettled" dist/sw.js  # should be 1

# 5. Dockerfile has critical Nginx stability directives
grep -c "daemon off" Dockerfile.<service>    # >= 1
grep -c "HEALTHCHECK" Dockerfile.<service>   # 1
grep -c "worker_processes" Dockerfile.<service>  # 1
grep -c "= /sw.js" Dockerfile.<service>      # 1 (if SW used)
grep -c "error_page 404" Dockerfile.<service> # 1
```

## Pitfalls

- **`grep -c` returns exit code 1 when count is 0** — this breaks `&&` chains in bash. Wrap with `|| true` or `|| echo "0"` when asserting absence.
- **Vite `assetFileNames` hashes ALL assets** — there's no per-asset override. Don't try to force an unhashed name for the SW; fix the SW instead.
- **`vite-plugin-static-copy`** may be listed in `package.json` but never imported — check `vite.config.ts` before assuming it's active.
- **The source `index.html` references unhashed paths** (e.g., `<link href="/assets/player.css">`) which Vite rewrites to hashed names at build time. The *source* file is fine; only the *SW* (which compiles separately) sees the uncompiled literal.
- **Ignoring SIGQUIT semantics** — SIGQUIT is Nginx's graceful shutdown signal. Iterative SIGQUIT always means an external orchestrator (EasyPanel, Docker, Kubernetes) is killing it, not that Nginx itself is crashing. Fix the healthcheck/config, don't look for a crash in nginx source.
- **Writing `nginx.conf` with `printf` in Dockerfile** — use `printf '%s\n'` with one argument per line to avoid shell escaping issues with `\n`. Don't use `echo -e` (not portable in Alpine's `sh`).

## References

- `references/vite-sw-nginx-debug-patterns.md` — Detailed session evidence: asset pipeline trace, SW install failure mechanics, Nginx config anatomy, and the exact diffs applied to the TAD DOOH Player.
- **Related skill**: `nextjs-pwa-proxy-stabilization` — covers the analogous SW registration and proxy 500 patterns for **Next.js** apps (middleware-based SW exclusion, `getRawBody` proxy body forwarding, Prisma P2025 prevention). Use that skill when the app is Next.js (not Vite + Nginx).
