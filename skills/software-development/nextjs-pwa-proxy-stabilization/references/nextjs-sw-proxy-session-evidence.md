# Next.js SW + Proxy Stabilization — Session Evidence

Session: 2026-07-12 — TAD DOOH v12.1.4 "Operación Resiliencia V12"

## The Three Bugs

### Bug 1: SW Registration `SecurityError`

**Error string:**
```
Uncaught (in promise) SecurityError: Failed to register a ServiceWorker...
The script resource is behind a redirect, which is disallowed.
```

**File:line trace:**
- `apps/driver/next.config.ts` — uses `@ducanh2912/next-pwa` which registers `/sw.js` from `public/`
- `apps/driver/middleware.ts:56-59` — matcher regex did NOT exclude `sw.js`:
  ```typescript
  // BROKEN
  '/((?!api|_next/static|_next/image|_next/data|favicon.svg|manifest.json|icons/).*)'
  ```
- `apps/driver/middleware.ts:46-51` — auth guard: if `!isPublicRoute && (!session || role !== 'DRIVER')` → redirect to `/driver/login`
- Browser requests `/sw.js` → middleware runs → no session cookie → 302 redirect to `/driver/login` → browser rejects registration

**Fix applied:** Added `sw\\.js`, `workbox-.*\\.js` to the exclusion regex, and escaped dots in `favicon\\.svg` and `manifest\\.json`.

### Bug 2: Proxy 500 on `/api/proxy/fleet/track-batch`

**Error string:**
```
/api/proxy/fleet/track-batch:1 Failed to load resource: the server responded with a status of 500 ()
```

**File:line trace:**
- `apps/driver/pages/api/proxy/[...path].ts:41` — `bodyParser: false` (streaming mode)
- `apps/driver/pages/api/proxy/[...path].ts:114` — `delete headers['content-length']` in `getForwardHeaders()`
- `apps/driver/pages/api/proxy/[...path].ts:137-139` (original) — passes raw stream as body:
  ```typescript
  // BROKEN
  fetchOptions.body = req as any;
  (fetchOptions as any).duplex = 'half';
  ```
- `fetch()` to backend NestJS → Express/NestJS body parser receives body without valid `content-length` → 500

**Fix applied:** Replaced `req as any` with `getRawBody` from `next/dist/compiled/raw-body`, which reads the full body to a Buffer and recalculates `content-length`. Returns 400 on parse failure instead of 500.

### Bug 3: Backend 500 from Prisma P2025

**File:line trace:**
- `apps/api/src/modules/fleet/fleet.service.ts:714` — `ingestTelemetryBatch(data)`
- `apps/api/src/modules/fleet/fleet.service.ts:776` (original) — `this.prisma.device.update({ where: { deviceId: data.deviceId } })`
- If `deviceId` doesn't exist in DB → `PrismaClientKnownRequestError` (P2025) → no global exception filter → NestJS default → 500

**Fix applied:** Added `device.findUnique` in `Promise.all` alongside the existing `driver.findUnique` at the top of the method. Returns 404 (`Device Not Found`) if device doesn't exist, before any mutation.

## Verification Evidence (Fresh)

### API (`apps/api`)
```
tsc --noEmit -p tsconfig.json | grep "fleet.service.ts"  → 0 matches
nest build (npm run build)                               → EXIT=0
```
Full project `tsc` returns 0 errors total — clean build.

### Driver (`apps/driver`)
```
tsc --noEmit -p tsconfig.json | grep "middleware.ts"     → 0 matches
tsc --noEmit -p tsconfig.json | grep "proxy/"            → 0 matches
```
Driver `tsc` has 37 pre-existing errors — all missing module declarations (`react-leaflet`, `qrcode.react`, `idb`, `@sentry/nextjs`, `@ducanh2912/next-pwa`, `@tanstack/*`, `@playwright/test`, CSS side-effect imports). Zero in changed files.

`next build` blocked by `Cannot find module '@sentry/nextjs'` in `next.config.ts:2` — pre-existing, not introduced by changes. The package is not in local `node_modules` but is installed in CI/EasyPanel.

### Middleware regex test
```
EXCLUDED: /sw.js
EXCLUDED: /workbox-abcd.js
EXCLUDED: /manifest.json
EXCLUDED: /icons/icon-192.png
EXCLUDED: /api/proxy/fleet/track-batch
EXCLUDED: /_next/static/chunk.js
EXCLUDED: /favicon.svg
CAUGHT  : /driver/dashboard
CAUGHT  : /driver/login
```

### raw-body module check
```
node -e "const r = require('next/dist/compiled/raw-body'); console.log(typeof r)"
→ function
```
Module exists at `node_modules/next/dist/compiled/raw-body/index.js` (291 KB), callable at runtime.

## Files Changed

1. `apps/driver/middleware.ts` — matcher regex: added `sw\\.js`, `workbox-.*\\.js`, escaped dots
2. `apps/driver/pages/api/proxy/[...path].ts` — replaced `req as any` body with `getRawBody` + `content-length` recalculation
3. `apps/api/src/modules/fleet/fleet.service.ts` — added `device.findUnique` in parallel with `driver.findUnique`, 404 on missing device
4. `03_changelog_logs_tad.md` — changelog entry inserted at top

## Payload Signature (Preserved)

The telemetry payload from `useTelemetry.ts` was NOT modified:
```typescript
{
  driverId: string,
  deviceId: string,
  points: { lat: number, lng: number, speed: number, timestamp: number }[]
}
```
CORS/Credentials headers, fallback public URL retry, and auth token forwarding in the proxy were all preserved.
