---
name: nextjs-pwa-proxy-stabilization
description: "Debug and fix Next.js production deployment failures on Docker/EasyPanel monorepos: PWA Service Worker redirect loops, API proxy 500s, Prisma P2025 in proxied endpoints, and Tailwind v3/v4 migration CSS-missing-in-production. Covers middleware SW exclusion, getRawBody body forwarding, existence-before-mutation, PostCSS/@theme v4 alignment, and EasyPanel API remote diagnosis."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [nextjs, pwa, service-worker, proxy, middleware, getrawbody, prisma, easypanel, docker, sw-js, redirect, securityerror, content-length, tailwind, tailwindcss, postcss, css, standalone, html-no-styles, tailwind-v4]
    related_skills: [vite-nginx-container-stabilization, systematic-debugging, prisma-schema-migrations]
---

# Next.js PWA Proxy & Infra Stabilization

## When to Use

Use when a Next.js app (Pages Router or App Router) deployed in a Docker/EasyPanel container exhibits any of:

- **Service Worker registration fails** with `SecurityError: Failed to register a ServiceWorker... The script resource is behind a redirect, which is disallowed.` — the SW file (`/sw.js`) is being intercepted by middleware and redirected to a login/auth page.
- **API proxy returns 500** — a `pages/api/proxy/[...path].ts` (or similar) route that forwards requests to a backend (NestJS, Express, etc.) returns HTTP 500 when sending POST/PUT bodies.
- **Backend 500 from Prisma P2025** — a proxied endpoint calls `prisma.update()` with a `where` clause referencing an entity that doesn't exist, and without a global exception filter, NestJS converts the `PrismaClientKnownRequestError` into an unhandled 500.
- **Portal renders HTML with no styles / Tailwind CSS missing in production** — the browser shows unstyled HTML, `.next/static/css/` is either absent or empty, but JS chunks are generated fine. Almost always a Tailwind **v3→v4 migration gap** in one portal of the monorepo while siblings already migrated. See **Pattern 5** below.

Distinct from `vite-nginx-container-stabilization` which covers **Vite SPA + Nginx** static-served SW 404 issues — this skill covers **Next.js middleware + API routes** where the SW and proxy are served by Next.js's own server, plus Next.js standalone CSS/static-asset generation.

## Pattern 1: SW Redirect → SecurityError (Middleware Exclusion)

### Root cause

Next.js `middleware.ts` with an auth-guard matcher intercepts `/sw.js` because the negative-lookahead regex in `matcher` doesn't list it. The auth guard sees no session cookie and redirects to `/login` (302). The browser's SW registration API rejects any script behind a redirect → `SecurityError`.

### Detection

Read `middleware.ts` and look at the `matcher` config:

```typescript
// BROKEN — sw.js is NOT excluded, so middleware runs on it
export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|_next/data|favicon.svg|manifest.json|icons/).*)',
  ],
};
```

Any path NOT in the exclusion list goes through the middleware. If the middleware has auth redirects, `/sw.js` gets redirected.

### Fix — add SW + Workbox to the exclusion regex

```typescript
// FIXED — sw.js, workbox-*.js, and other PWA assets bypass middleware
export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|_next/data|favicon\\.svg|manifest\\.json|sw\\.js|workbox-.*\\.js|icons/).*)',
  ],
};
```

Key points:
- **Escape dots** in the regex: `favicon\\.svg`, `manifest\\.json`, `sw\\.js` — unescaped dots match any char, which works by accident but is technically wrong.
- **`workbox-.*\\.js`** covers Workbox chunks like `workbox-abc123.js`.
- Also add an early-return guard at the top of the middleware function for defense-in-depth:

```typescript
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Defense-in-depth: never redirect PWA assets even if matcher misses
  if (pathname === '/sw.js' || pathname.startsWith('/workbox-') ||
      pathname === '/manifest.json') {
    return NextResponse.next();
  }
  // ... rest of auth logic
}
```

### Verification

Test the regex as Next.js interprets it (anchored, with leading `/`):

```bash
node -e "
const re = new RegExp('^/((?!api|_next/static|_next/image|_next/data|favicon\\\\.svg|manifest\\\\.json|sw\\\\.js|workbox-.*\\\\.js|icons/).*)$');
['/sw.js', '/workbox-abc.js', '/manifest.json', '/driver/dashboard', '/driver/login']
  .forEach(t => console.log((!re.test(t) ? 'EXCLUDED' : 'CAUGHT  ') + ': ' + t));
"
```

Expected: `/sw.js`, `/workbox-*`, `/manifest.json` → EXCLUDED; protected routes → CAUGHT.

## Pattern 2: API Proxy 500 — Body Forwarding Fix

### Root cause

A Next.js API proxy route with `bodyParser: false` (for streaming) passes `req` (the raw `IncomingMessage` stream) directly as `fetch()` body:

```typescript
// BROKEN — raw stream passed without content-length recalculation
if (req.method !== 'GET' && req.method !== 'HEAD') {
  fetchOptions.body = req as any;
  (fetchOptions as any).duplex = 'half';
}
```

The proxy's header logic typically deletes `content-length` (to let fetch recalculate it), but Node.js `fetch()` doesn't automatically compute `content-length` for stream bodies when it's been explicitly deleted. The backend receives a body without valid `content-length` → Express/NestJS body parser may truncate or reject → 500.

### Fix — read body to Buffer with getRawBody

```typescript
if (req.method !== 'GET' && req.method !== 'HEAD') {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const getRawBody = require('next/dist/compiled/raw-body');
    const rawBody = await getRawBody(req, {
      length: req.headers['content-length'],
      limit: '5mb',
    });
    fetchOptions.body = rawBody;
    (fetchOptions.headers as Record<string, string>)['content-length'] = String(rawBody.length);
    (fetchOptions as any).duplex = 'half';
  } catch (bodyError: unknown) {
    const errMsg = bodyError instanceof Error ? bodyError.message : String(bodyError);
    console.error(`[PROXY] Body parse error: ${errMsg}`);
    return res.status(400).json({
      error: 'Invalid request body',
      message: 'Body malformed or exceeds size limit',
      detail: errMsg,
    });
  }
}
```

Key points:
- **`next/dist/compiled/raw-body`** ships with Next.js — no extra dependency needed. It's the same library Next uses internally for `bodyParser: true`.
- **`require()` not `import()`** — the module has no TypeScript declarations. Use `require()` with an eslint-disable comment to avoid TS7016.
- **Recalculate `content-length`** from `rawBody.length` and set it explicitly on `fetchOptions.headers`.
- **Cast headers to `Record<string, string>`** — `RequestInit.headers` is `HeadersInit`, which doesn't support index assignment without a cast.
- **400 on body parse failure** — return a descriptive 400, not a 500, when the body is malformed or exceeds the limit.

### What NOT to change

- CORS headers and credentials forwarding (`Access-Control-Allow-Origin`, `Access-Control-Allow-Credentials`) must be preserved.
- The fallback/retry logic (internal URL → public URL) should remain intact.
- Auth token forwarding (`Authorization` header, cookie-to-bearer conversion) should not be touched.

## Pattern 3: Prisma P2025 Prevention in Proxied Endpoints

### Root cause

A NestJS (or any) backend endpoint receives a request via the proxy, calls `prisma.entity.update({ where: { id: receivedId } })`, but the entity doesn't exist in the DB. Prisma throws `PrismaClientKnownRequestError` with code `P2025` ("Record to update not found"). Without a global exception filter catching Prisma errors, NestJS's default exception filter converts this to HTTP 500.

This is especially common in telemetry/ingestion endpoints where the `deviceId` or `driverId` in the payload might be stale, wrong, or from a device that was never registered.

### Fix — validate existence before mutation, in parallel

```typescript
async ingestTelemetryBatch(data: TrackBatchDto) {
  // Validate BOTH driver AND device exist before touching any table
  const [driver, device] = await Promise.all([
    this.prisma.driver.findUnique({
      where: { id: data.driverId },
      select: { id: true, subscriptionPaid: true, status: true, fullName: true },
    }),
    this.prisma.device.findUnique({
      where: { deviceId: data.deviceId },
      select: { id: true, deviceId: true },
    }),
  ]);

  if (!driver) {
    throw new HttpException('Driver Not Found', HttpStatus.NOT_FOUND);
  }
  if (!device) {
    throw new HttpException('Device Not Found', HttpStatus.NOT_FOUND);
  }

  // Now safe to update — entity existence verified
  await this.prisma.device.update({
    where: { deviceId: data.deviceId },
    data: { lastSeen: new Date(), /* ... */ },
  });
}
```

Key points:
- **`Promise.all` for parallel validation** — validates both entities in one round-trip, not two sequential queries. Respects RAM caps (no array iteration, just two PK lookups).
- **Return 404, not 500** — a missing entity is a client error (the payload references something that doesn't exist), not a server error.
- **Still wrap the `update()` in try/catch** — even after existence validation, the DB state could change between the `findUnique` and `update` (race condition). The catch should log but not re-throw if the mutation is non-critical (e.g., updating a "last seen" snapshot after the main data was already persisted).

## Verification Protocol

After applying fixes, run these checks **fresh** (never cite prior results as current evidence):

```bash
# 1. API (NestJS) — full build compiles
cd apps/api && npm run build
# Expected: exit 0

# 2. API — no new TS errors in changed files
cd apps/api && node_modules/.bin/tsc --noEmit -p tsconfig.json 2>&1 | grep "<changed-file>"
# Expected: 0 matches

# 3. Driver (Next.js) — no new TS errors in changed files
cd apps/driver && ../../node_modules/.bin/tsc --noEmit -p tsconfig.json 2>&1 | grep -E "middleware\.ts|proxy/"
# Expected: 0 matches

# 4. Middleware regex test (runtime)
node -e "new RegExp('^/((?!...sw\\\\.js...).*)$').test('/sw.js')"
# Expected: false (excluded)

# 5. raw-body module exists and is callable
node -e "const r = require('next/dist/compiled/raw-body'); console.log(typeof r)"
# Expected: function
```

## Pattern 4: Monorepo Proxy Replication — Fix ALL Copies

### Root cause

In a monorepo (Nx, turborepo, or plain workspaces), multiple Next.js apps often **copy-paste** the same API proxy file (`pages/api/proxy/[...path].ts`). When you fix a proxy bug in one app (e.g., `apps/driver`), the **identical bug still lives** in sibling apps (e.g., `apps/admin`). A 500 reported on `proyecto-ia-tad-dashboard.rewvid.easypanel.host/api/proxy/campaigns` may come from a proxy that is structurally identical to the one you just fixed in `apps/driver` — but in `apps/admin`.

### Detection

After fixing a proxy pattern in one app, immediately search for ALL copies in the monorepo:

```bash
# Find all proxy route files across the monorepo
search_files pattern="[...path].ts" target="files"
# or
search_files pattern="proxy" target="files" path="apps"
```

If multiple results come back, check each one for the same `req as any` body forwarding pattern.

### Fix — apply the identical patch to every copy

Apply the `getRawBody` fix (from Pattern 2 above) to **every** proxy file found. Do not assume "this app doesn't use telemetry, so its proxy is fine" — the proxy is a generic forwarding layer; ALL POST/PUT/PATCH requests through it suffer the same `content-length` issue.

### Verification — check each app individually

```bash
# For each app with a proxy file:
cd apps/admin && ../../node_modules/.bin/tsc --noEmit -p tsconfig.json 2>&1 | grep "proxy/"
# Expected: 0 matches (no errors in any proxy file)
```

## Pattern 6: Build Self-Corruption — `.next/server/pages/_app.js.nft.json` ENOENT

### Root cause

`next build` completes successfully (all pages compiled, static generation finishes) but the final tracing step fails with:

```
[Error: ENOENT: no such file or directory, open '.next\server\pages\_app.js.nft.json']
npm error Lifecycle script `build` failed with error
```

The compile step writes `.nft.json` files (Next.js File Tracing metadata) into `.next/server/pages/`. The final tracing phase reads them back to produce the standalone manifest. If the write and read race — because the `.next/` directory is stale from a prior interrupted build, or because two builds ran concurrently in the same workspace — the file disappears between write and read, producing ENOENT. This is **not** a code regression; it's a build cache integrity issue.

This pattern is specific to **Windows + OneDrive-synced monorepos** (path length, file locking, OneDrive's opportunistic file hydration) but can appear on any host where `.next/` is shared across concurrency.

### Detection

The error always surfaces at the very end of `next build`, after:

```
✓ Compiled successfully
 Collecting page data ...
 Generating static pages ...
 Finalizing page optimization ...
 Collecting build traces ...
[Error: ENOENT ...]
```

If `tsc --noEmit` is clean and the compile step succeeded, the failure is in the tracing phase, not in your code.

### Fix — clean `.next` and rebuild

```bash
cd apps/<portal> && rm -rf .next && npm run build
```

On Windows / git-bash, `rm -rf` works. On PowerShell, use `Remove-Item -Recurse -Force .next`.

### Verification

```bash
cd apps/<portal> && npm run build 2>&1 | tail -20
# Expected: BUILD_EXIT: 0, no "ENOENT" or "nft.json" errors
ls .next/server/pages/_app.js.nft.json
# Expected: file exists (43-114 bytes)
```

### Pitfalls
### Pitfalls
- **`rm -rf .next` inside `npm run build` via a single shell command can hit timeout on Windows** — the delete + rebuild on a large monorepo portal takes 60-180s. Use `terminal(background=true, notify_on_complete=true)` or split into two commands: first `rm -rf .next` (fast), then `npm run build` in a second call.
- **Do not skip the `rm -rf` step** — `npm run build` alone will reproduce the same ENOENT if `.next/` is already corrupted. The stale `.nft.json` files from a prior incomplete build are the trigger.
- **Concurrent `next build` in sibling workspaces** — if two agents or CI jobs run `next build` in different portal apps of the same monorepo simultaneously, they can share the root `node_modules/.cache` and interfere with each other's tracing. Serialize builds in CI or use isolated `NEXT_BUILD_CACHE_DIR` per app.
- **OneDrive-synced directories are especially vulnerable** — OneDrive's file hydration (placeholder → real file) and opportunistic locking can cause `ENOENT` moments where a file exists in the filesystem cache but the OS reports it missing to the Node.js fs module. `rm -rf .next` forces a fresh write that avoids the race.
- **`next build` can silently hang on Windows/OneDrive monorepos with no output at all** — if `npm run build` produces zero stdout for 60-300s and eventually times out (exit 124), it is almost certainly an environmental filesystem issue, not a code error. The build process is blocked during compilation or SWC transform by OneDrive file-locking or path-resolution overhead. `tsc --noEmit` will still pass clean because the TS compiler is not affected. **Do not loop on blind retries**. Confirm environment sanity with `npx next info` first; if that works, the issue is build-time filesystem contention. Workarounds: (a) build from a non-OneDrive working tree, (b) use CI/EasyPanel remote build instead of local, or (c) accept `tsc --noEmit` as the verification gate when local build is unusable.
- **`node_modules` hoisted to monorepo root means per-app `node_modules` may be empty** — in npm workspaces, `apps/<portal>/node_modules` is often absent or minimal; the actual packages live at the root `node_modules/`. `npm run build` from `apps/<portal>` still works because npm resolves upward. Do not treat an empty per-app `node_modules` as a missing-dependency blocker. Use `ls node_modules/next` at the repo root to confirm install exists.

## Pitfalls

- **TAD monorepo: Dockerfiles for portal services live in `apps/driver/`, not under each app's directory.** The repo co-locates all portal Dockerfiles under `apps/driver/` — `Dockerfile.advertiser`, `Dockerfile.admin`, `Dockerfile.driver`, plus a generic `Dockerfile`. Do NOT assume `apps/advertiser/Dockerfile` exists; always `ls apps/driver/` first when targeting a portal's Dockerfile for EasyPanel build fixes. The API service follows the expected convention (`apps/api/Dockerfile`), but all Next.js portals use this co-located pattern.
- **Proxy files are copy-pasted across monorepo apps** — when you fix a proxy bug in `apps/driver`, the identical bug lives in `apps/admin`, `apps/advertiser`, etc. Always `search_files` for all copies after fixing one. A 500 reported on one app's proxy may originate from a sibling app's identical proxy that was never patched.
- **`next build` may fail on missing `@sentry/nextjs` or other optional deps** — this is a pre-existing local environment issue (the package isn't installed in dev `node_modules` but is in CI). Don't treat it as a regression from your changes. Use `tsc --noEmit` on specific changed files as the verification gate if `next build` is blocked by missing modules.
- **Unescaped dots in middleware matcher regex** — `favicon.svg` (unescaped) technically matches `faviconXsvg` too. It works by accident because no such paths exist, but escape them (`favicon\\.svg`) for correctness.
- **`import()` vs `require()` for internal Next.js modules** — `next/dist/compiled/raw-body` has no `.d.ts`. Using `import()` triggers TS7016. Use `require()` with `// eslint-disable-next-line @typescript-eslint/no-var-requires` instead.
- **`fetchOptions.headers` is `HeadersInit`, not `Record<string, string>`** — you can't do `fetchOptions.headers['key'] = 'value'` without casting. Cast to `Record<string, string>` or build headers as a plain object before assigning.
- **Prisma P2025 surfaces as 500, not 404** — without an exception filter, NestJS doesn't know that P2025 means "not found." The client sees 500 and assumes the server is broken, when really the payload references a nonexistent entity. Always validate existence first.
- **Indentation drift from patch tools** — `patch` mode='replace' can introduce 4-space indentation shifts when the old/new strings have different leading whitespace. After patching a block, re-read the region to verify indentation matches the surrounding code style. If it drifts, use `write_file` for the entire enclosing function rather than a third `patch` attempt.
- **`patch` tool writes literal diff markers into source files** — when `old_string` or `new_string` contains lines starting with `-` or `+` (e.g. replacing an import that starts with `-import`), the `patch` tool can emit those as literal diff markers (`-`/`+` prefixes) into the actual file instead of interpreting them as content. This corrupts the source with parse errors (`Expression expected`) that `next lint` catches but `tsc` may not. **Workaround**: after any `patch` call that touches lines starting with `-` or `+`, immediately `read_file` the region and grep for `^-` or `^+` at column 1. If found, use `sed -i` from `terminal` to repair the lines, or `git checkout HEAD -- <file>` to restore and re-apply with `sed` instead of `patch`. Prefer `sed -i` for line-level deletions/replacements on Windows/git-bash; reserve `patch` for multi-line contextual edits where `sed` would be unwieldy.
- **`awk` for block deletion over `sed` for multi-line function removal** — when you need to delete an entire function block (`function Foo() { ... }`), `sed` range deletion (`sed '/^function Foo/,/^}$/d'`) is fragile because the closing `}$` pattern matches any function. Use `awk '/^function ActionButton/{f=1} f&&/^}$/{f=0;next} !f'` which tracks brace depth implicitly via the `f` flag and only deletes the first matching block. Verify with `grep -c "FunctionName" file` after.
- **TAD repo `ignoreBuildErrors: true`** — the driver's `next.config.ts` has `typescript.ignoreBuildErrors: true` and `eslint.ignoreDuringBuilds: true`. So `npm run build` won't catch TS errors in the driver app. Always use `tsc --noEmit -p tsconfig.json` as the real verification for driver changes.
- **Git rebase add/add conflicts on new files in TAD monorepo** — when your local commit adds new files (e.g. `DriverShell.tsx`, `WalletTab.tsx`) and `origin/main` also has commits touching the same paths (or renames), `git pull --rebase` produces `CONFLICT (add/add)` on those files. Resolve with `git checkout --theirs <file>` (theirs = your commit being replayed during rebase) for each new file, `git add` them, then `git rebase --continue`. For content conflicts in existing files (e.g. `<div>` vs `<>` wrapper), manually edit out the `<<<<<<<` / `=======` / `>>>>>>>` markers with `sed` or `python3 -c` regex replacement, then `git add` + `git rebase --continue`. Use `GIT_EDITOR=true git rebase --continue` to skip the interactive editor on Windows/git-bash where the default editor may hang.
- **`tsconfig.tsbuildinfo` blocks `git pull`** — `tsconfig.tsbuildinfo` is often git-tracked but locally modified by `tsc --noEmit`. It causes `error: Your local changes would be overwritten by merge` during `git pull --rebase`. Fix: `git checkout -- <path>/tsconfig.tsbuildinfo` before pulling, or add it to `.gitignore` permanently. If untracked (`apps/api/tsconfig.tsbuildinfo`), `rm -f` it before pull.
- **Tailwind v1-3 deps silently hoisted from monorepo root** — `apps/<portal>/package.json` may NOT list `tailwindcss` / `postcss` / `@tailwindcss/postcss` / `autoprefixer` at all, and the portal still builds locally via npm hoisting from the root workspace. In Docker the same hoisting can resolve to different versions, especially if the Dockerfile does `rm -rf package-lock.json && npm install` (antipattern, see below). Always pin Tailwind/PostCSS deps in each portal's own `package.json` — do not rely on the root workspace alone for a portal that uses Tailwind.
- **Dockerfile `rm -rf package-lock.json && npm install`** — several TAD portal Dockerfiles (`Dockerfile.advertiser`, `Dockerfile.admin`, `Dockerfile.driver`) delete the lockfile before installing. This makes the build **non-reproducible**: each `docker build` can resolve different versions of Tailwind/PostCSS and silently change CSS output. Replace with `COPY package.json package-lock.json ./` + `RUN npm install` (or `npm ci`) so the lockfile is honored. Deleting node_modules is okay; deleting the lockfile is not.
- **TAD portal routes are served from the admin app and require the `/admin/:path*` prefix** — the dashboard at `proyecto-ia-tad-dashboard.rewvid.easypanel.host` renders from `apps/admin/pages/admin/**`. Public portal paths such as `/campaigns/new`, `/campaigns/:id/report`, `/media?openUpload=true`, and `/fleet?search=...` are all Pages Router routes under `/admin/...` (e.g. `/admin/campaigns/new.tsx`). Client-side shortcuts bypassing `/admin/` produce 404 even when the underlying page exists. Fix at two layers: update internal `<Link>`/`router.push()` calls to use absolute `/admin/...` paths, and add next.config redirects like `{ source: `/campaigns/:path*`, destination: `/admin/campaigns/:path*`, permanent: false }` so bookmarked old paths keep working.
- **Adding catch-all redirects in older `next.config.js` configs can silently break newer TypeScript configs** — the TAD monorepo has both `apps/admin/next.config.ts` (current) and `apps/admin/next.config.js` (legacy). Debugging/editing the active TS version is futile if EasyPanel, npm scripts, or a leftover service config still consumes the JS file. Before assuming a redirect was ignored, confirm which config path is the real build entrypoint and delete/align the duplicate; otherwise restart attempts will silently behave as though no change happened.
- **Tailwind v4 ignores `tailwind.config.js` by default** — v4 is CSS-first. An old `tailwind.config.js` with `content: [...]` + `module.exports` is silently ignored unless you explicitly `@config "../tailwind.config.js"` in CSS. Prefer the v4 way: move `content`, theme colors, keyframes into an `@theme { --color-*, --animate-*, @keyframes ... }` block in `globals.css` and delete the JS config. Custom colors used in `@apply` directives (e.g. `bg-tad-accent`) must be defined as `--color-tad-accent` in `@theme` or v4 will not resolve the utility class.
- **Missing `postcss.config.mjs` = no Tailwind CSS output at all** — Tailwind v4 needs an explicit PostCSS plugin registration (`"@tailwindcss/postcss": {}`) in `postcss.config.mjs`/`.js`/`.cjs`. Without this file, Next.js won't run Tailwind's PostCSS plugin and `.next/static/css/` will contain **zero CSS files** — the entire portal renders unstyled, not just a few classes. When debugging "no styles in prod", first diff the broken portal's `postcss.config.*` / `tailwind.config.*` / `styles/globals.css` against a sibling portal that renders correctly.
- **EasyPanel hostname pattern is `proyecto-{name}-{service}`, not `{service}`** — EasyPanel generates Traefik hostnames using the project name as a prefix with hyphens replacing underscores (`proyecto_ia` → `proyecto-ia`). Probing `tad-advertiser.rewvid.easypanel.host` will hit Traefik's catch-all 404 page even when the service IS running under `proyecto-ia-tad-advertiser.rewvid.easypanel.host`. Always call `domains.listDomains` (POST `{"json": {}}`) via the EasyPanel API to discover the actual hostnames before curl-probing URLs.
- **EasyPanel RPC endpoints often reject GET query params but accept POST JSON** — `inspectService`, `queryServiceLogs`, `listActions`, and several others return 400 `"Input validation failed"` with empty `zodErrors` when using GET + query params, even though OpenAPI declares them as GET. The working shape is POST with body `{"json": {...params}}`. See `references/easypanel-api-rpc-debug.md` for a full endpoint catalog.

## Pattern 8: NestJS GlobalExceptionFilter Swallows Prisma UnknownRequestError

### Root cause

The `PrismaClientExceptionFilter` correctly catches `PrismaClientKnownRequestError`, `PrismaClientValidationError`, `PrismaClientInitializationError`, and `PrismaClientUnknownRequestError` — but the `else` branch (for `UnknownRequestError` and `InitializationError`) only calls `logger.error()` without setting `message` or `errorCode`. The response therefore has `message = 'An unexpected error occurred'` (the default from the outer scope) and `code = 'INTERNAL_ERROR'`.

The request then reaches `GlobalExceptionFilter`, which sees `exception instanceof Error` true (since `PrismaClientException` extends `Error`) but `exception instanceof HttpException` is false — so it falls through to `else { logger.error(...) }` with no `status`/`message` rewrite. Result: **500 with `{"statusCode":500,"code":"INTERNAL_ERROR","message":"An unexpected error occurred"}`** — completely opaque, with the real DB error swallowed.

### Detection

The error response contains no `errorCode` beyond `INTERNAL_ERROR` and no real message. The NestJS logs may show a truncated note but not the full error text. All you see in the response is:
```json
{"statusCode":500,"code":"INTERNAL_ERROR","message":"An unexpected error occurred","path":"/api/v1/campaigns"}
```

To confirm: temporarily add a debug log at the top of `GlobalExceptionFilter.catch()` that logs `exception.constructor.name` and `exception.message` for every caught exception. If you see `PrismaClientUnknownRequestError` or `PrismaClientInitializationError` in the logs without a corresponding detailed 4xx/5xx response, this is the pattern.

### Fix — PrismaClientExceptionFilter else branch must propagate the real message

```typescript
// BEFORE (broken — swallows the message):
} else {
  this.logger.error(`Prisma Unhandled Error: ${exception.message}`);
  // message stays as default 'Error interno de base de datos.' — returned as 500 INTERNAL_ERROR
}

// AFTER (fixed):
} else {
  // PrismaClientUnknownRequestError, PrismaClientInitializationError
  this.logger.error(`Prisma Unknown/Initialization Error: ${exception.message}`);
  message = exception.message;   // propagate real DB error to client
  errorCode = 'DB_ERROR';
  status = HttpStatus.BAD_REQUEST; // 400 for unknown DB errors, not 500
}
```

### Key points

- **Propagate `exception.message`** in the else branch — the client needs the real error, not the default fallback.
- **Use `errorCode = 'DB_ERROR'`** to distinguish from genuine 500s — clients can show a specific UI message.
- **Return 400, not 500** for `UnknownRequestError` / `InitializationError` — these are client-side or connection issues, not server bugs the client should treat as a crash.
- **The filter was already catching all four exception types** — the bug was in the `else` branch handling, not in the `@Catch()` decorator. The gap was the missing `message = exception.message` assignment.
- **Test by corrupting a payload** to an endpoint that uses `findUnique` with a malformed UUID or passes invalid data to Prisma — a known request error will return P2002/P2025/P2003 with proper message; an unknown error (e.g. connection failure mid-query) should return `DB_ERROR` + the real message, not "An unexpected error occurred".

### Verification

After applying the fix, trigger an error in the same endpoint:
```bash
curl -s http://localhost:3000/api/v1/campaigns \
  -H "Authorization: Bearer <token>" | jq .code, .message
# Before: "INTERNAL_ERROR", "An unexpected error occurred"
# After: "DB_ERROR", "<actual Prisma error message>"
```

## Pattern 7: Prisma Client Generation Drift — Stale Client in Production

### Root cause

The Prisma schema source file (`prisma/schema.prisma`) is updated — new relations, fields, or migrations are added — but the generated client (`prisma/client/` or `node_modules/@prisma/client`) is **not** regenerated. In development this often goes unnoticed because:
- `prisma generate` is run before `npm run dev`
- Dev DB state is often behind prod (no migrations applied locally vs prod)

In production (CI/CD or manual deploy), if the pipeline uses a **cached or pre-built `node_modules/@prisma/client`** and doesn't run `npx prisma generate` against the committed schema, the runtime client lacks the new fields/relations. Every query that references the new fields throws `PrismaClientKnownRequestError` (validation) at runtime → caught by the global exception filter → 500.

**This is especially insidious in monorepos** where the Prisma schema lives in `apps/api/prisma/` but the generated client is hoisted to the monorepo root `node_modules/@prisma/client/`. A schema change committed to `apps/api/prisma/schema.prisma` will not automatically refresh the root client unless `npx prisma generate` runs from `apps/api/` (where the schema is resolved from).

### Detection

```bash
# 1. Check if the generated client is stale
cat apps/api/prisma/client/schema.prisma | head -5          # generated copy
cat apps/api/prisma/schema.prisma | head -5                  # source truth
# If they differ in size, dates, or content → stale client.

# 2. Look for schema drift in the error
# If you have access to backend logs:
grep -E "P2025|P2009|P2010|Validation Error" /var/log/api.log
# PrismaClientValidationError ("Unknown argument") = almost certainly stale client
```

**Key field**: `@@map("campaigns")` and all relation definitions in the source schema. If the client lacks a relation that the controller `include`s, the query fails at serialization time, not at the DB level — which means the DB is fine and the fix is purely a client regeneration.

### Fix

Commit-pushed-schema → client regeneration → rebuild → deploy:

```bash
# 1. Regenerate client FROM the schema source directory (ensures correct schema resolution)
cd apps/api && npx prisma generate

# 2. Commit BOTH the schema.prisma (already changed) AND the regenerated client
git add apps/api/prisma/schema.prisma apps/api/prisma/client/ node_modules/.prisma/client/
git commit -m "chore: regenerate Prisma client for schema v12.2.5"

# 3. Rebuild the API container in EasyPanel
# Use EasyPanel RPC: deployService or restartService (see references/easypanel-api-rpc-debug.md)
```

**Do NOT** run `prisma generate` from the monorepo root — it will pick up whichever schema is closest to the execution cwd. Always `cd` into the app directory that owns the `prisma/schema.prisma`.

### Pitfalls

- **`prisma/client/schema.prisma` is a generated artifact** — Never hand-edit it. It will be overwritten by `prisma generate`. The source of truth is `prisma/schema.prisma` only. Inspecting the generated `schema.prisma` is a convenient diff target, but it is not the canonical schema.
- **Two `schema.prisma` files exist** in `apps/api/prisma/` — `schema.prisma` (source, in repo) and `client/schema.prisma` (generated output). The `diff` of these two files is the fastest way to detect drift.
- **CI/CD pipelines that skip `npx prisma generate` on deploy** will silently push stale clients. Add `npx prisma generate` as an explicit step in the API deploy pipeline before `npm run build`.
- **EasyPanel Docker build caching** — if the Dockerfile uses an npm cache layer that preserves `node_modules/.prisma/client` from a previous build, and the new build image doesn't include a fresh `npx prisma generate`, the runtime can still serve the stale client even after a rebuild. Use `npm ci` (not `npm install`) to ensure the runtime install matches the lockfile, and run `prisma generate` as a build step in the Dockerfile.
- **Browser-facing 500 from Prisma validation error is indistinguishable from a DB error** without the exception filter's log output. Always check the NestJS logs for `PrismaClientValidationError` (stale client) vs `PrismaClientKnownRequestError: P2002/P2025` (DB-level issue) before assuming schema or data corruption.

## Pattern 5: Tailwind v3→v4 Migration — Missing CSS in Production

### Root cause

The monorepo migrated some portals (e.g. `apps/admin`, `apps/driver`) from Tailwind v3 to **v4**, but one portal (e.g. `apps/advertiser`) was left behind with v3-style configuration. Tailwind v4 has a breaking architecture change:

- v3 directive `@tailwind base; @tailwind components; @tailwind utilities;` is **ignored** by v4 (replaced by `@import "tailwindcss"`).
- v3 `tailwind.config.js` with `content: [...]` + `module.exports` is **ignored** by default (v4 is CSS-first; theme goes in a `@theme { ... }` block inside CSS).
- PostCSS plugin key changed from `"tailwindcss": {}` to `"@tailwindcss/postcss": {}`.
- Without a `postcss.config.*` file, Next.js never runs the Tailwind PostCSS plugin → `.next/static/css/` stays **empty** → unstyled HTML in prod.

Local builds can still succeed because npm hoisting resolves the deps from the workspace root, but the Docker build (especially if the Dockerfile deletes `package-lock.json`) can resolve different versions and silently break CSS generation.

### Detection — diff against a working sibling portal

The fastest diagnostic is to diff the broken portal's three files against a sibling portal that renders correctly:

```bash
# Find the PostCSS / Tailwind configs in each portal
ls apps/*/postcss.config.* apps/*/tailwind.config.* 2>/dev/null
# Find globals.css in each portal
find apps -name "globals.css" -maxdepth 4 -not -path "*/node_modules/*"
```

A working v4 portal has:
- `apps/<portal>/postcss.config.mjs` — `{"@tailwindcss/postcss": {}}`
- `apps/<portal>/styles/globals.css` — `@import "tailwindcss"; ... @theme { ... }`
- **No** `apps/<portal>/tailwind.config.js`
- `apps/<portal>/package.json` lists `tailwindcss@^4`, `postcss`, `@tailwindcss/postcss`, `autoprefixer` explicitly.

A broken portal is missing `postcss.config.*`, has a `tailwind.config.js` in v3 shape, and/or `globals.css` uses `@tailwind base/components/utilities`.

Then confirm at the build level:

```bash
# Clean build the broken portal and inspect .next/static/css/
cd apps/<broken-portal> && npx next build
ls -la .next/static/css/  # absent or empty = Tailwind never ran
wc -c .next/static/css/*.css  # if 0 bytes or no file = silent CSS failure
```

### Fix — align the broken portal to the v4 pattern of a working sibling

Apply these four changes (exact recipe from the 2026-07-12 advertiser recovery):

1. **Create `apps/<broken>/postcss.config.mjs`** — identical to the sibling's:
   ```js
   const config = {
     plugins: { "@tailwindcss/postcss": {} },
   };
   export default config;
   ```

2. **Migrate `apps/<broken>/styles/globals.css`** from v3 directives to v4 CSS-first. Move every custom color, font, animation, and keyframe from the old `tailwind.config.js` into a `@theme { ... }` block:
   ```css
   @import "tailwindcss";

   /* stylelint-disable at-rule-no-unknown */
   @theme {
     --color-tad-bg: #0a0a0a;
     --color-tad-accent: #FFD400;
     --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
     --animate-spin-slow: spin-slow 10s linear infinite;
     @keyframes spin-slow { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
   }
   /* stylelint-enable at-rule-no-unknown */

   @layer base { body { @apply bg-[#0a0a0a] text-white antialiased; } }
   ```
   Custom colors referenced in `@apply bg-tad-accent` MUST be declared as `--color-tad-accent` in `@theme` or v4 won't resolve the utility.

3. **Delete `apps/<broken>/tailwind.config.js`** — v4 ignores it by default; keeping a v3 config that nothing references is dead weight and confuses future readers.

4. **Add the Tailwind/PostCSS deps explicitly to `apps/<broken>/package.json`**:
   ```json
   "@tailwindcss/postcss": "^4.2.1",
   "autoprefixer": "^10.4.0",
   "postcss": "^8.5.8",
   "tailwindcss": "^4.0.0"
   ```
   Then run `npm install` at the monorepo root to sync `package-lock.json`.

5. **(If applicable) Repair the portal Dockerfile** — remove `rm -rf package-lock.json` from the `RUN npm install` line and add `COPY package.json package-lock.json ./` so Docker builds are reproducible.

### Pitfalls specific to this pattern

- **Don't run `npm run build --workspace advertiser`** — the workspace name is `@tad/advertiser` (with scope), not `advertiser`. Use `npx next build` from inside the portal directory instead, or `npm run build --workspace apps/advertiser` (npm accepts the path).
- **`app/layout.tsx` (App Router) does NOT auto-import globals.css** — only `pages/_app.tsx` (Pages Router) imports it. If a portal has a hybrid setup, make sure `globals.css` is imported in `_app.tsx`; the App Router `layout.tsx` is fine without it as long as Pages Router is the entry for styled pages.
- **First v4 build after migration can still emit `@tailwind` deprecation noise** if any `@apply` references an undeclared theme token. Resolve by declaring the token in `@theme`, not by re-adding v3 directives.

## References

- `references/nextjs-sw-proxy-session-evidence.md` — Session-specific evidence from the TAD DOOH v12.1.4 fix: exact error strings, file:line traces, the three diffs applied, and the verification output.
- `references/driver-shell-refactor-2026-07-13.md` — Session-specific evidence from the TAD DOOH v12.1.4b Admin Dashboard proxy fix: the monorepo proxy replication pattern, how to find all proxy copies, what to check if the 500 persists after redeploy.
- `references/driver-shell-lint-cleanup-2026-07-14.md` — Session evidence from the lint cleanup + push: `patch` tool diff-marker corruption incident and `sed`/`git checkout` recovery, git rebase add/add conflict resolution workflow, `tsconfig.tsbuildinfo` blocking `git pull`, and the 152-line dead code removal (EarningsLedger/ActionButton).
- `references/nextjs-tailwind-v4-migration-session-evidence.md` — Session-specific evidence from the 2026-07-12 TAD advertiser CSS recovery: the 5-file fix, build output showing 105 KB CSS generated, tsc clean, Dockerfile diff. See the SKILL.md "Pattern 5" section above for the condensed transferable recipe.
- `references/nextjs-build-silent-hang-2026-07-14.md` — Session evidence from TAD DOOH on 2026-07-14: `next build` produces zero stdout and silently times out on Windows/OneDrive-synced monorepo paths (no ENOENT, just hang). Distinguishes this from the Pattern 6 `.nft.json` ENOENT issue and lists workarounds (non-OneDrive working tree, remote CI build, `tsc --noEmit` as local gate).
- `references/easypanel-api-rpc-debug.md` — EasyPanel API v2.32.0 RPC reference: auth/login flow, POST-vs-GET endpoint shape quirks, endpoint catalog (inspectService, deployService, restartService, listActions, listDomains, getServiceStats), subdomain generation pattern (`proyecto-ia-tad-*` NOT `tad-*`), background deploy-monitor Python script template, and common failure modes (`stats null`, `logs 500`, deploy timeout). Use this when diagnosing why a deployed service returns 404 at a hostname or needs a remote redeploy/restart.
