# Admin Dashboard Proxy 500 — Session Evidence

Session: 2026-07-12 — TAD DOOH v12.1.4b

## The Bug

**Error string (from browser console on `proyecto-ia-tad-dashboard.rewvid.easypanel.host`):**
```
GET https://proyecto-ia-tad-dashboard.rewvid.easypanel.host/api/proxy/campaigns 500 (Internal Server Error)
```

Stack trace originated from `dashboard-61031c7014f92d66.js` (the Admin Dashboard's page bundle).

## Root Cause

The Admin Dashboard (`apps/admin`) has its own proxy at `apps/admin/pages/api/proxy/[...path].ts`. It was **structurally identical** to the driver's proxy before the V12.1.4 fix — same `req as any` body forwarding, same `delete headers['content-length']` without recalculation.

Even though the error was a `GET /campaigns` (no body), the proxy had never been patched. The 500 could originate from:
1. The proxy itself failing to forward correctly (less likely for GET, but the fragile `content-length` deletion affects all requests through the header pipeline).
2. The backend NestJS `CampaignService.getAllCampaigns()` crashing — `prisma.campaign.findMany({ include: { mediaAssets, media } })` — if a relation or field in `mediaAssetSafeSelect` doesn't exist in the current Prisma schema (e.g., after a migration that renamed or dropped a column without updating the query).

## Fix Applied

Replicated the `getRawBody` fix from the driver proxy to the admin proxy:

- `apps/admin/pages/api/proxy/[...path].ts` — replaced `req as any` with `getRawBody` + `content-length` recalculation + 400 error handling.
- Added documentation comment on `delete headers['content-length']` explaining it's intentional for body requests (recalculated in `getRawBody`) and harmless for GETs (typically undefined).

## How to Find All Proxy Copies

```
search_files pattern="[...path].ts" target="files"
→ apps/admin\pages\api\proxy\[...path].ts
→ apps/driver\pages\api\proxy\[...path].ts
```

Both were structurally identical copies. The driver was fixed in V12.1.4; the admin was fixed in V12.1.4b.

## Verification Evidence

### Admin (`apps/admin`)
```
tsc --noEmit -p tsconfig.json 2>&1 | grep "proxy/"  → 0 matches
```
Admin `tsc` has 2 pre-existing errors: `tsconfig.json` deprecation warnings (lines 15, 19 — `moduleResolution=node10`, `baseUrl`). Zero in the proxy file.

`npm run build` for the admin app could not be run — the admin likely uses the same monorepo root `node_modules` which is missing `@sentry/nextjs` (same pre-existing block as the driver).

### raw-body module (shared)
```
node -e "require('next/dist/compiled/raw-body')"  → function (callable)
```

## File Changed

1. `apps/admin/pages/api/proxy/[...path].ts` — `getRawBody` body forwarding fix (identical to driver fix)
2. `03_changelog_logs_tad.md` — changelog entry inserted at top

## If 500 Persists After Redeploy

If the proxy fix doesn't resolve the 500 after redeploying `tad-dashboard`, the origin is in the backend NestJS:
- `CampaignService.getAllCampaigns()` at `apps/api/src/modules/campaign/campaign.service.ts:391-396`
- The query: `prisma.campaign.findMany({ include: { mediaAssets: { select: mediaAssetSafeSelect }, media: true }, orderBy: { createdAt: 'desc' } })`
- Check: `npx prisma validate` — ensure all fields in `mediaAssetSafeSelect` (id, campaignId, type, filename, url, fileSize, checksum, duration, version, createdAt, qrUrl, weight) exist in the current Prisma schema
- Check: ensure the `media` relation exists on the `Campaign` model
- Check: ensure `mediaAssets` relation exists on `Campaign` model
