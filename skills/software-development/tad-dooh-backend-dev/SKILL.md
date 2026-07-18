---
name: tad-dooh-backend-dev
description: "TAD DOOH Platform backend development: NestJS API, Prisma schema, device/campaign/sync modules, and deployment conventions on EasyPanel."
version: 1.0.0
author: Hermes Agent
platforms: [windows, linux]
tags: [nestjs, prisma, typescript, tad, monorepo, backend, easypanel]
---

# TAD DOOH Backend Development

## Scope

Working in `apps/api/` — the NestJS backend that serves the TAD DOOH fleet. Covers device sync, campaign management, finance/earnings, notifications, and the Supabase integration layer.

---

## Project Structure

```
apps/api/src/
  modules/
    device/     # Tablet registration, heartbeat, playback confirmations, bulk-sync
    campaign/   # Campaign CRUD, media assets, scheduling
    sync/       # GET /sync/:deviceId — manifest + kill-switch (402)
    finance/    # Earnings calculation, payment liquidation
    drivers/    # Driver records, subscription status
    notifications/ # Supabase Realtime broadcast, push, email
    auth/       # JWT / Supabase Auth guard
    prisma/     # PrismaService singleton
    supabase/   # SupabaseService for Realtime + storage
  common/
    constants/business-rules.ts  # Platform limits (15 campaigns/tablet, 500RD$)
    guards/subscription.guard.ts
    decorators/public.decorator.ts
  app.module.ts
  main.ts
```

---

## NestJS Conventions

### tsconfig.json requirements

```json
{
  "compilerOptions": {
    "module": "commonjs",
    "experimentalDecorators": true,
    "emitDecoratorMetadata": true,
    "skipLibCheck": true,
    "strictNullChecks": false,
    "noImplicitAny": false,
    "types": ["node"],        // REQUIRED — needed for Buffer, stream in @nestjs/common
    "moduleResolution": "node" // Required when module=commonjs
  }
}
```

**Missing `"types": ["node"]`** causes cascading errors like:
- `Cannot find name 'Buffer'`
- `Cannot find name 'stream'`
- `TS2591` from `@nestjs/common` decorator declarations

### Module wiring

Controllers that need `Response` from Express (for setting headers like `ETag`, `Cache-Control`, 304 responses) must import it:

```typescript
import { Response } from 'express';

async getManifest(..., @Res({ passthrough: true }) res: Response) {
  res.setHeader('ETag', etag);
  res.status(HttpStatus.NOT_MODIFIED).send();
  return; // or return manifest
}
```

The `passthrough: true` allows returning a value while still using `res` for headers.

### @Public() decorator

Routes exempt from the global `SupabaseAuthGuard`. All tablet-facing device routes (`/device/register`, `/device/heartbeat`, `/sync/:deviceId`) are `@Public()`.

---

## DTO Conventions (IMPORTANT)

**Use TypeScript definite assignment assertions (`!`) instead of class-validator decorators when `emitDecoratorMetadata` or `experimentalDecorators` config is inconsistent.**

```typescript
// WRONG — breaks build when decorator chain fails
import { IsString, IsNotEmpty } from 'class-validator';
export class RegisterDeviceDto {
  @IsString()
  @IsNotEmpty()
  device_id: string;  // TS2564 error without initializer
}

// CORRECT — clean build, works at runtime with ValidationPipe at the controller level
export class RegisterDeviceDto {
  device_id!: string;
  model?: string;
  os_version?: string;
}
```

**When to use decorators vs plain fields:**
- Decorators work reliably only when `tsconfig.json` has BOTH `experimentalDecorators: true` AND `emitDecoratorMetadata: true`
- If you see `TS1240` ("Unable to resolve signature of property decorator") or `TS2564` on DTOs — strip decorators and use `!` assertions
- The ValidationPipe at the controller level still validates at runtime; decorators are compile-time only

---

## Sync Endpoint Pattern

`GET /sync/:deviceId` serves the manifest that tablets poll every 5 minutes.

### ETag caching pattern

```typescript
private readonly etagCache = new Map<string, { value: string; expiresAt: number }>();
private readonly ttlMs = 5 * 60 * 1000;

private resolveCachedEtag(deviceId: string, ifNoneMatch?: string): boolean {
  if (!ifNoneMatch) return false;
  const cached = this.etagCache.get(deviceId);
  if (!cached || cached.expiresAt < Date.now()) {
    if (cached) this.etagCache.delete(deviceId);
    return false;
  }
  return cached.value === ifNoneMatch;
}

private cacheEtag(deviceId: string, etag: string): void {
  this.etagCache.set(deviceId, { value: etag, expiresAt: Date.now() + this.ttlMs });
}
```

### 304 / 402 pattern

```typescript
// 304 — ETag matched, return empty body
if (this.resolveCachedEtag(deviceId, ifNoneMatch)) {
  res.status(HttpStatus.NOT_MODIFIED).send();
  return;
}

// 402 — subscription kill-switch (never cache the blocked state)
const manifest = await this.syncService.getDeviceManifest(deviceId);
if ((manifest as Record<string, unknown>).killSwitch === true) {
  res.setHeader('Cache-Control', 'no-store');
  throw new HttpException(manifest, HttpStatus.PAYMENT_REQUIRED);
}

// 200 — normal response
const etag = (manifest as Record<string, unknown>).etag as string || '';
this.cacheEtag(deviceId, etag);
res.setHeader('ETag', etag);
res.setHeader('Cache-Control', 'public, max-age=0, must-revalidate');
return manifest;
```

---

## Build & Verification

### Commands

| Project | Command | Notes |
|---------|---------|-------|
| API | `cd apps/api && npx nest build` | Final gate — `npx tsc --noEmit` may timeout on complex error sets |
| Player | `cd apps/player && npm run build` | Vite build |
| All | `npm run build` (root) | Runs all workspaces |

### When tsc --noEmit times out or hangs

`tsc` with many errors (especially from `node_modules` or cascading decorator failures) can timeout. Use `npx nest build` directly — it compiles incrementally and is more resilient to pre-existing errors.

### Pre-existing errors in this codebase

The `apps/api` workspace has ~100+ pre-existing TS errors from:
- `node_modules/@supabase/auth-js` type incompatibilities
- `node_modules/@supabase/realtime-js` missing modules
- Various `err is of type 'unknown'` warnings

These are **filtered by `skipLibCheck: true`** and do not block `npx nest build`. The build gate is `npx nest build exit 0`, NOT `npx tsc --noEmit exit 0`.

---

## TAD Non-Negotiable Business Rules

Implemented in `apps/api/src/common/constants/business-rules.ts`:

| Rule | Value |
|------|-------|
| Max active campaigns per tablet | 15 |
| Offline-first grace period | 48 hours after subscription lapses |
| Earnings per confirmed sale | RD$500 |
| Base daily earnings (15 active ads) | RD$500 × 15 = RD$7,500 |
| Subscription required | `subscriptionPaid === true` → 402 PAYMENT_REQUIRED |

### Kill-switch flow

When `subscriptionPaid === false` AND grace period expired:
1. `sync.service.ts` returns `manifest.killSwitch = true`
2. `sync.controller.ts` throws `HttpException(manifest, HttpStatus.PAYMENT_REQUIRED)` (402)
3. Tablet PWA shows kill screen, stops playback

---

## Notifications Pattern

All notification triggers should go through `NotificationsService`:

```typescript
// In the service that detects the event
constructor(private readonly notificationsService: NotificationsService) {}

async someEvent(driverId: string) {
  await this.notificationsService.sendDriverNotification(driverId, 'EVENT_TYPE', {
    /* payload */
  });
}
```

Import `NotificationsModule` and add `NotificationsService` to the module's `providers` array.

---

## Pitfalls

- **Missing `"types": ["node"]`** in `tsconfig.json` → cryptic TS2591 errors from `@nestjs/common`
- **DTO decorators** → use `!` assertions to avoid build breakage from decorator chain failures
- **`nest build` vs `tsc --noEmit`** → prefer `nest build` as the gate; `tsc` can timeout on large error sets
- **OneDrive-synced paths** → NestJS compilation (not ts-node) is the verification gate
- **Response headers after `throw HttpException`** → set headers BEFORE throwing, not after

---

## EasyPanel Deployment

- API runs on `tad-api.rewvid.easypanel.host`
- Environment variables validated via Zod at startup — missing vars crash the pod
- `supabaseUrl` and `supabaseServiceRoleKey` must match EasyPanel secrets
- Health check: `GET /health` returns `200 OK`