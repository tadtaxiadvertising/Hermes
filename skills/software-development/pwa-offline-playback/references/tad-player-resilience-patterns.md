# TAD Player Resilience Patterns — Session Evidence

Source: TAD DOOH player audit (`apps/player/`), `apps/api/src/modules/sync/`, `apps/api/src/modules/campaign/campaign.service.ts`.

## SPRINT 1: Core offline resilience fixes (confirmed in session)

### LEAK-1: Timer leak in `setPlaylist()`
**File:** `apps/player/src/playlist-engine.ts`
**Symptom:** `watchdogTimer` and `_scheduleCheckTimer` survived across `FORCE_SYNC` cycles, creating duplicate timers per sync.
**Fix:** At the top of `setPlaylist()`, call `clearWatchdog()` and `clearInterval(_scheduleCheckTimer)` before rebuilding.

```typescript
// playlist-engine.ts — before rebuilding, kill old timers
this.clearWatchdog();
if (this._scheduleCheckTimer) {
  clearInterval(this._scheduleCheckTimer);
  this._scheduleCheckTimer = null;
}
this.playlist = assets;
```

### LEAK-2: CDN URL instead of blob URL in `playNext()`
**File:** `apps/player/src/playlist-engine.ts`
**Symptom:** `this.videoElement.src = asset.url` streams from CDN on every playback, not from IndexedDB. Offline playback impossible.
**Fix:** Resolve blob from CacheManager before assignment:

```typescript
// playlist-engine.ts — resolve blob URL before assigning to video.src
try {
  const blobUrl = await this.cacheManager.getVideoSource(asset);
  this.videoElement.src = blobUrl;
} catch (err) {
  // Fallback to CDN if cache miss (may fail if offline)
  this.videoElement.src = asset.url;
}
```

**Prerequisite:** `PlaylistEngine` must receive `CacheManager` in its constructor. Pass from `main.ts`:

```typescript
const playlistEngine = new PlaylistEngine(playbackQueue, cacheManager, onStatusChange);
```

### OFFLINE-1: Blob URL lifecycle management
**File:** `apps/player/src/cache-manager.ts`
**Symptom:** `URL.createObjectURL()` creates blob URLs that leak if not revoked on asset eviction.
**Fix:** Track active blob URLs in a Map and revoke on evict:

```typescript
private activeObjectUrls = new Map<string, string>();

private trackBlobUrl(key: string, blob: Blob): string {
  const existing = this.activeObjectUrls.get(key);
  if (existing) URL.revokeObjectURL(existing);
  const objectUrl = URL.createObjectURL(blob);
  this.activeObjectUrls.set(key, objectUrl);
  return objectUrl;
}

// In evict():
const activeUrl = this.activeObjectUrls.get(url);
if (activeUrl) {
  URL.revokeObjectURL(activeUrl);
  this.activeObjectUrls.delete(url);
}
```

### OFFLINE-2: `hasAssetAvailable()` checks integrity
**File:** `apps/player/src/cache-manager.ts`
**Purpose:** Returns true only if the cached blob passes checksum validation. Used by SyncManager to know if an asset is truly playable offline.

---

## SPRINT 2: Web Worker for background downloads

### Worker architecture (`.js` — not `.ts`)
**File:** `apps/player/src/workers/video-downloader.worker.js`

Vite/rollup will parse worker files for the production bundle. TypeScript syntax (`type`, `interface`, `as`, generics) in a `.ts` worker **passes `tsc --noEmit`** but **fails Vite build** with "Expected ';', '}' or <eof>" because rollup's JS parser chokes on TypeScript type annotations before Vite's SWC transform can strip them. The fix: use `.js` + JSDoc annotations.

**Worker registration in `main.ts`:**

```typescript
const worker = new Worker(
  new URL('./workers/video-downloader.worker.js', import.meta.url),
  { type: 'module' },
);
(window as unknown as Record<string, unknown>).__tadVideoWorker = worker;
```

### Worker postMessage contract (TAD-specific)

**Main thread → Worker:**
1. `SYNC_ASSETS` — enqueue assets into worker's IndexedDB queue. Worker responds with `SYNC_ASSETS_RESULT` (enqueued count, skipped count).
2. `DOWNLOAD_ASSETS { concurrency }` — actually start downloads. Worker responds with `DOWNLOAD_STATUS` (finished, failed).
3. `GET_STATUS` — poll current state (non-critical).

**Worker → Main thread:**
- `SYNC_ASSETS_RESULT { ok, enqueued, skipped, tasks }`
- `DOWNLOAD_STATUS { ok, finished, failed, tasks }`
- `PROGRESS { taskId, filename, status }` (informational)
- `ERROR { ok: false, message }`

### CacheManager wiring for worker delegation
**File:** `apps/player/src/cache-manager.ts`

`cacheVideos()` checks for `window.__tadVideoWorker` and delegates; falls back to main-thread download if worker not available.

**Key constraint:** `CacheManager` has no `deviceId` field. The device ID lives on `SyncManager`. Do NOT read `this.deviceId` from `CacheManager` — either omit it from the worker message or use a hardcoded `deviceId` on the main.ts side.

---

## Verification baseline

| Command | Scope | Expected |
|---------|-------|---------|
| `cd apps/player && npx tsc --noEmit` | TypeScript type check | exit 0 (pre-existing env/Window errors OK — they existed before this session) |
| `cd apps/player && npm run build` | Full bundle + worker | exit 0; worker JS in dist/assets/ |

**Important:** Do NOT reuse prior verification output. Re-run after every architectural change.