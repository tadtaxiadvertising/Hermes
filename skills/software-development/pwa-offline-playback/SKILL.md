---
name: pwa-offline-playback
title: "PWA Offline-First Playback Resilience"
description: "Hardening media playback apps for offline reliability, low-bandwidth tablets, and constrained memory: blob URL resolution, timer leak prevention, background download workers, and playlist rebuild contracts."
triggers:
  - Offline-first video playback
  - Playback worker / Web Worker downloads
  - Blob URL / IndexedDB video caching
  - Memory leaks in playlist engines
  - Player service audits
  - Tablet PWA resilience
---

# PWA Offline-First Playback Resilience

Use when the task involves hardening a player, kiosk, or DOOH tablet app so it plays media reliably without constant connectivity and without leaking resources over many sync cycles.

## Core principles (non-negotiable)

1. **Resolve blobs, don’t stream CDN URLs blindly.** Assigning a remote CDN URL directly to a `<video>` element bypasses local caching and breaks offline playback.
2. **Playlist rebuilds must be timer-safe.** Every `setPlaylist()` is a replace operation; no prior timer should survive into the new configuration.
3. **Make background downloads cooperative, not greedy.** Workers should enqueue, not hammer the network on their own; the main thread owns playback state.
4. **Verify offline behavior with fresh evidence.** Re-run build/type checks after each architectural change; never reuse prior verification output.

## Preferred architecture

```
Main thread
  PlaylistEngine
    └─ cacheManager.getVideoSource(asset) -> blob URL -> video.src
  CacheManager
    └─ IndexedDB video store + blob URL lifecycle
  PlaybackQueue
    └─ IndexedDB event store (PoP / telemetry)
  DownloadWorker
    └─ postMessage protocol for asset enqueue/dl/status
```

## Workflow

1. Audit first: locate manifest download path, ETag/304 handling, JWT offline token issuance, and existing IndexedDB usage.
2. Fix cache resolution before adding workers. If `video.src` is still a CDN URL, no worker change will make playback offline-capable.
3. Inject dependencies explicitly (e.g. `CacheManager` into `PlaylistEngine`) instead of reaching for implicit globals.
4. Add the Web Worker only after the fix above is verified.
5. Keep sync flow and download flow separate: sync stays request/response, downloads become async tasks with progress events.
6. Use existing session verification commands (`tsc --noEmit` for TS, project build for bundling) after every structural change.

## Pitfalls

- **Blob URL assignment is a one-line fix, but easy to miss.** Look for `videoElement.src = asset.url` — this is the smoking gun of "claims offline, actually streams CDN."
- **Re-attach media element listeners after element replacement.** If `videoElement` can change reference, existing listeners are lost.
- **Worker build setup is often the surprise blocker.** Add a dedicated worker entry in the build config before writing significant worker code.
- **TypeScript strictness in workers is usually DOM/Node type collisions, not logic errors.** Isolate worker APIs; don’t import browser bundles into worker context.
- **Workers must be `.js`, not `.ts`, in a Vite project with strict tsconfig.** The player workspace has `tsconfig.json` that type-checks `.ts` files but Vite/rollup will also parse them for the production bundle. TypeScript syntax (`type`, `interface`, `as`, generics) in a `.ts` worker will pass `tsc --noEmit` but fail the Vite build with "Expected ';', '}' or <eof>". Fix: rename to `.js` and use JSDoc `@param` / `@type` annotations instead. The `new Worker(new URL('./path.worker.js', import.meta.url), { type: 'module' })` Vite convention still works for `.js` workers.
- **CacheManager has no `deviceId` field.** The device ID lives on `SyncManager`, not `CacheManager`. When wiring `cacheVideos()` to post to the worker, do NOT read `this.deviceId` from `CacheManager` — use the deviceId from the caller's scope or pass it separately. The worker does not need it for the SYNC_ASSETS message (it enqueues by URL); omit it rather than passing undefined.
- **Worker postMessage shapes must match what the worker actually uses.** The worker reads `message.payload.assets` and `message.payload.deviceId`. Sending `{ deviceId: this.deviceId }` when `CacheManager` has no such property throws TS6133 (unused variable in original TS worker) or silently missing at runtime in the JS worker. Always match the payload to the worker's `handleSyncAssets` function signature.

## Minimum verification checklist

- [ ] `video.src` is resolved from `CacheManager` before playback
- [ ] `setPlaylist()` clears watchdog + schedule timers before rebuilding
- [ ] Offline token expiry is enforced client-side with kill-switch fallback
- [ ] Worker integrates into existing sync callback, no new sync protocol

## Support files

- `references/tad-player-resilience-patterns.md` — canonical fixes from the TAD DOOH player audit (blob URL leak, timer leak, worker contract)
