# Vite SW + Nginx Container Debug Patterns

Session: 2026-07-11 — TAD DOOH Player crash-loop + 404 assets stabilization.

## The Exact Failure

### 404 `/assets/player.css` — Asset Pipeline Trace

**Source files:**
- `apps/player/src/index.html:8` → `<link rel="stylesheet" href="/assets/player.css" />`
- `apps/player/src/assets/player.css` → the actual CSS source
- `apps/player/vite.config.ts:21` → `assetFileNames: 'assets/[name]-[hash][extname]'`
- `apps/player/src/sw.ts:16` → `const SHELL_ASSETS = ['/', '/index.html', '/assets/player.css']`

**What happens at build time:**
1. Vite resolves the `<link>` in `src/index.html`, finds `src/assets/player.css`, processes it.
2. Vite emits the CSS to `dist/assets/main-6jpdjePn.css` (hashed filename).
3. Vite rewrites `<link>` in `dist/index.html:9` to `href="/assets/main-6jpdjePn.css"` — ✅ correct.
4. Vite compiles `sw.ts` as a **separate Rollup entry** (`rollupOptions.input.sw`). The string literal `'/assets/player.css'` is compiled as-is — **no rewriting** because it's not an HTML asset reference, it's a TS string constant.
5. `dist/sw.js` carries `["/","/index.html","/assets/player.css"]` — a path that doesn't exist.

**What happens at runtime:**
1. Browser loads `/` → gets `dist/index.html` → references `main-6jpdjePn.css` (hashed, exists) → ✅.
2. `main.ts` registers `/sw.js` → SW install event fires.
3. `caches.open(SHELL_CACHE).then(cache => cache.addAll(SHELL_ASSETS))`.
4. `cache.addAll()` does `fetch('/assets/player.css')` → Nginx `location /assets/` → `try_files $uri =404` → **404**.
5. `cache.addAll()` rejects → entire `install` event rejects → SW goes redundant.
6. Next navigation retries → same failure → **SW install loop**.

**The fix applied:**
```typescript
// Before — brittle
const SHELL_ASSETS = ['/', '/index.html', '/assets/player.css'];
caches.open(SHELL_CACHE).then(cache => cache.addAll(SHELL_ASSETS))

// After — fault-tolerant, shell-only
const SHELL_ASSETS = ['/', '/index.html'];
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

Why this works: the hashed CSS/JS are cached on-demand by the existing SWR fetch handler when the browser loads `index.html` (which references the correct hashes). No precache needed.

### Nginx Crash-Loop (SIGQUIT) — Config Anatomy

**The original Dockerfile.player** only wrote `/etc/nginx/conf.d/default.conf` via inline `printf`, leaving the image's default `/etc/nginx/nginx.conf` untouched. Problems:

1. No explicit `HEALTHCHECK` directive → Docker/EasyPanel can't verify nginx is alive within a timeout window → sends SIGQUIT (graceful shutdown) → restarts → crash-loop.
2. No explicit `worker_processes`, `pid`, or logging config → relies on image defaults which vary across `nginx:alpine` tags.
3. No `error_page 404 /index.html` → raw nginx 404 for unknown paths (though `try_files` in `location /` catches most).
4. No dedicated `location = /sw.js` → the SW could be cached aggressively by intermediate proxies.

**The fix — write both nginx.conf AND default.conf:**

The Dockerfile now:
- Writes `/etc/nginx/nginx.conf` with `worker_processes auto`, `pid`, `access_log /dev/stdout`, `error_log /dev/stderr`, `gzip`, `keepalive_timeout`, and `include /etc/nginx/conf.d/*.conf`.
- Writes `/etc/nginx/conf.d/default.conf` with `location /health` (200 JSON), `location /assets/` (immutable cache), `location = /sw.js` (no-cache), `location /` (SPA fallback), `error_page 404 /index.html`.
- Adds `HEALTHCHECK` Docker directive using `wget -qO- http://localhost:80/health`.
- CMD is `["nginx", "-g", "daemon off;"]` keeping nginx as PID 1.

## Verification Evidence (Fresh)

```
tsc --noEmit -p tsconfig.json          → EXIT=0 (0 errors)
npm run build (tsc + vite build)      → EXIT=0, 53 modules, sw.js=1.52 KB
grep -c "player.css" dist/sw.js        → 0 (path eliminated)
grep -c "allSettled" dist/sw.js        → 1 (fault-tolerant install)
grep -c "daemon off" Dockerfile.player → 3
grep -c "HEALTHCHECK" Dockerfile.player → 1
grep -c "worker_processes" Dockerfile  → 1
grep -c "= /sw.js" Dockerfile.player    → 1
grep -c "error_page 404" Dockerfile    → 1
```

## Files Changed

- `apps/player/src/sw.ts` — SHELL_ASSETS reduced to shell-only, `cache.addAll` → `Promise.allSettled`
- `Dockerfile.player` — full rewrite of nginx config section: inline `nginx.conf` + `default.conf` + `HEALTHCHECK` + `error_page` + `sw.js` location

## Applicability to Other TAD Services

The same pattern applies to any Vite SPA + Nginx container in the TAD monorepo:
- `Dockerfile.player` (this fix)
- `Dockerfile.tablet-player` (similar structure, simpler — no SW, but lacks HEALTHCHECK and nginx.conf override)

When stabilizing `Dockerfile.tablet-player` or similar, apply Pattern 2 (nginx.conf hardening + HEALTHCHECK) even if there's no Service Worker.
