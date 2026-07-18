# Multi-App Telemetry / Realtime Chain — Surgical Fix Playbook

Companion to `read-only-code-audit` SKILL.md. Use when a read-only audit (or
ad-hoc investigation) has fingered a defect that spans **schema → backend
endpoint → mobile/tablet hook → admin UI map or dashboard**, especially
anything involving Realtime broadcasts, GPS telemetry, batched uploads, or
`isOnline`/`status` flag binding. The audit identifies *what*; this file
gives the *how* for that specific class of break.

## When to load

- The finding involves a property name on a Prisma model being misused in JSX.
- A `@deprecated` hook in the driver app once published a Supabase Realtime
  broadcast, and the "canonical" successor hook visibly omits that publish.
- The driver/app batch ingestion header hits a backend controller whose
  service writes a history table **and** a `Device.lastLat/lastLng/lastSeen`
  snapshot, and the snapshot heuristic is order-dependent.
- A `tsc --noEmit` that should pass fails on changed-file scope only because
  of cross-app drift.

## The four-span pattern (recurring shape)

| Span | Type | Watch for |
|---|---|---|
| 1. Driver mobile | Hook + IndexedDB + Supabase Realtime broadcast | Deprecated vs canonical split; missing broadcast |
| 2. API proxy | Next.js catch-all forwarding to NestJS | `duplex: 'half'`, body parsing for streams; lost auth header |
| 3. NestJS controller/service | `Prisma.createMany` + `Device.update` snapshot + `throw HttpException` | Order-dependent snapshot selection; missing `lastSeen`/`isOnline` write; kill-switch allowed to bypass |
| 4. Admin UI | Leaflet/React map + `applyFleetFreshness` helper | Wrong field binding (`status === 'online'` vs `isOnline: boolean`); missing fallback for legacy data shapes |

Each span can look healthy in isolation. The bug lives in **the gap between**
any two spans.

## Verification recipe (per-app `tsc --noEmit`, scoped)

```bash
# From monorepo root. Universal recipe; works regardless of ignoreBuildErrors
# or unreliable `npm run` scripts.
cd apps/<app1>  && node_modules/.bin/tsc --noEmit --skipLibCheck -p tsconfig.json | grep -E "<changed-file>"
cd apps/<app2>  && node_modules/.bin/tsc --noEmit --skipLibCheck -p tsconfig.json | grep -E "<changed-file>"
cd apps/<app3>  && npx --no-install tsc --noEmit --skipLibCheck -p tsconfig.json | grep -E "<changed-file>"
# Zero matches ⇒ no new errors in that file. Pre-existing errors in other
# files (decorator metadata, `@types/node`) are intentionally ignored.

# After schema edits:
cd apps/api     && DATABASE_URL='postgresql://x:x@localhost:5432/x' \
                     DIRECT_URL='postgresql://x:x@localhost:5432/x' \
                     npx --no-install prisma validate
# Expect: "The schema at prisma/schema.prisma is valid 🚀"

# Final cross-app sanity:
git diff --stat
```

## Anti-patterns in this class

### 0. "localStorage identity key read but never persisted after QR check-in"

When a driver tablet app gets its `deviceId` from a QR URL param (`?deviceId=...`)
and passes it to a tracking gateway, but **never writes** `localStorage['TAD_DEVICE_ID']`
(or equivalent), every other hook in the app that reads that key falls back to
`'unknown'` or a stale value after a page reload.

**Diagnostic**: Search the mobile app codebase for `setItem` with the identity key
name — if zero results exist but `getItem` appears in 3+ sites, the key is read-only
and the identity is ephemeral.

```bash
# Zero setItem hits = confirmed bug
search_files pattern="setItem.*TAD_DEVICE_ID" target="content" path="apps/driver"

# Compare against read sites
search_files pattern="getItem.*TAD_DEVICE_ID" target="content" path="apps/driver"
```

**DB evidence**: Query the `devices` table — if real tablets exist but have
`lastSeen: null` and zero telemetry rows in `driverLocation`, the identity
gap is the root cause. Check with:

```ts
// All devices, focus on lastSeen
const devices = await prisma.device.findMany({
  select: { deviceId: true, taxiNumber: true, lastSeen: true },
  orderBy: { lastSeen: 'desc' },
});

// Recent telemetry — any real deviceIds present?
const locs = await prisma.driverLocation.findMany({
  orderBy: { timestamp: 'desc' }, take: 20,
  select: { deviceId: true, timestamp: true },
});
```

**Fix**: In the QR check-in flow (`check-in.tsx` or equivalent), immediately after
extracting `deviceId` from the URL param and validating it's non-empty, persist it:

```ts
const id = params.get('deviceId');
if (!id) { setInvalidQR(true); return; }
localStorage.setItem('TAD_DEVICE_ID', id);  // ← MISSING: persist identity
setDeviceId(id);
```

The `startTadTracking(id, baseUrl)` call stores it in-memory; the localStorage write
makes it survive reloads for all hooks that read `TAD_DEVICE_ID`.

### 1. "Canonical hook killed the broadcast"

When a `@deprecated` hook (e.g. `useBackgroundTelemetry`) is replaced by a
"canonical" successor (e.g. `useTelemetry`), the canonical hook may inherit
the *function* but lose the *publishing* side effects.

**Diagnostic**: Search both hooks for `channel.send`, `navigator.serviceWorker`,
`getItem`, `setItem`, `dispatchEvent`. Whatever the deprecated hook published
*must* appear inside the canonical hook — or be hoisted to a shared helper.

**Fix shape**: Add the broadcast inside `addCoord`/`addPoint`, byte-equivalent
to the legacy version, but routed through the canonical hook's existing
references. Throttle (e.g. 30s for one ping per device per 30s) prevents
battery exhaustion. Open the channel in `startTracking`, close it in
`stopTracking`. Closing it in `stopTracking` aligns with whatever kills
tracking on receipt of a 402 — so the kill-switch implicitly tears down
the broadcast too.

```ts
// setup (additive to existing refs)
const liveChannelRef = useRef<ReturnType<typeof supabase.channel> | null>(null);
const lastLivePingRef = useRef<number>(0);
const LIVE_PING_THROTTLE_MS = 30_000;

// in startTracking
if (!liveChannelRef.current) {
  const ch = supabase.channel('fleet_tracking_live', { config: { broadcast: { ack: true } } });
  ch.subscribe((status) => { /* log CHANNEL_ERROR / TIMED_OUT / CLOSED */ });
  liveChannelRef.current = ch;
}

// in addCoord, throttled publish
if (Date.now() - lastLivePingRef.current >= LIVE_PING_THROTTLE_MS) {
  lastLivePingRef.current = Date.now();
  const ch = liveChannelRef.current;
  if (ch /* && driverId && deviceId */) {
    void ch.send({ type: 'broadcast', event: 'telemetry_ping', payload: ping })
      .catch((err) => console.error('[useTelemetry] telemetry_ping publish failed', err));
  }
}

// in stopTracking — tear down channel
if (liveChannelRef.current) {
  void supabase.removeChannel(liveChannelRef.current);
  liveChannelRef.current = null;
}
```

**Never** mutate the legacy hook just to keep the publish alive — the
deprecation exists for a reason (duplicated geolocation workers, battery drain).
The broadcast belongs in the canonical hook.

### 2. "Wrong field type from a typed enum"

Frontend binds a marker color / status pill to `item.status === 'online'`
while backend serializes `status: SystemStatus` (an enum like `OPERATIVO |
PENDIENTE_PAGO | BLOQUEADO`). The map looks "broken" but the JSON is fine —
only the **frontend binding is wrong**.

Always read the actual `select` block in the Prisma query that feeds the
endpoint, then compare to the field each frontend component reads.

```ts
// BUG: assumes a flat string enum like "online"/"offline"
const isOnline = item.status === 'online' || item.online === true;

// FIX: read the real field, keep a fallback for legacy data shapes
const isOnline =
  !!item.isOnline ||
  item.online === true ||
  String(item.status).toLowerCase() === 'online';
```

Color binding (TAD palette by convention):
- Online → `#22c55e` (emerald)
- Offline → `#ef4444` (red)
- Selected highlight → brand yellow `tad-yellow`

### 3. "Last-point heuristic breaks after offline"

After an offline → online flush, batched telemetry arrives with timestamps
that **don't preserve insertion order** to the backend. A
`points[points.length - 1]` heuristic selects the **wrong** snapshot for
`Device.lastLat/lastLng`. Always derive the snapshot from the **maximum
timestamp in the batch**:

```ts
const lastPoint = data.points.reduce(
  (a, b) => (b.timestamp > a.timestamp ? b : a),
  data.points[0]
);
```

The `createMany` of the history table is unaffected — only the snapshot
update needs the fix. Do not mutate `telemetryData` (it feeds `createMany`).

Wrap the snapshot `Device.update` in `try/catch` with a logger:

```ts
try {
  await this.prisma.device.update({
    where: { deviceId: data.deviceId },
    data: { lastSeen: new Date(), lastLat: lastPoint.lat, lastLng: lastPoint.lng },
  });
} catch (e) {
  // History is already persisted; never break the batch ack over a snapshot.
  logger.error(`[FleetService] Snapshot update failed: ${e.message}`);
}
```

### 4. Surgical patch brittleness — extra `}` after `mode=replace`

When `old_string` doesn't include the trailing `}` of the enclosing method,
and `new_string` ends with one, the result is unbalanced — `TS1128: Declaration
or statement expected`. The lint warns about this; the symptom is sometimes
that **other files in the project** show new errors that look unrelated.

**Diagnostic**:

```bash
tail -5 apps/api/src/modules/<module>/<service>.ts
# Should end with exactly one closing `}` per class.
```

If you see two closing braces at the bottom, patch again to remove the
duplicate. To make this trap impossible to hit, include the trailing `}` in
your `old_string` whenever you're replacing the last method of a class.

## When verification is "green" but the bug persists

Two ways green verification can mask a real defect in this class:

1. **`tsc --noEmit` is full-project, not file-scoped.** The repo's
   `ignoreBuildErrors` or wide `include: ["**/*.ts"]` glob can mask your
   forgetting to delete a now-unused import. Always `grep -E "<changed-file>"`
   the output. If you only check "is the exit code 0", you'll miss per-file
   drift.

2. **`prisma validate` without dummy env vars fails confusingly.** The
   validator complains about missing `DATABASE_URL` even when the schema is
   syntactically fine. Pipe `DATABASE_URL='postgresql://x:x@localhost:5432/x'`
   to satisfy it; the schema is what you're checking, not connectivity.

3. **Produgct compile passes, runtime fails.** `skipDuplicates: true` on
   `createMany` is a **NO-OP** without a matching UNIQUE constraint in the DB.
   Adding `skipDuplicates` to a service without the UNIQUE migration silently
   allows duplicate inserts to grow the table unbounded. Always confirm the
   UNIQUE migration exists in `schema.prisma` (and has a matching
   `apps/api/prisma/migrations/.../migration.sql`) before trusting
   `skipDuplicates`.

## Real-world traversal (audit caption to plan actionable)

When you find a chain-span defect during an audit, the plan that fixes it
usually consists of three discrete edits:

1. **In the mobile hook** — re-establish the missing publish/side-effect with
   the same throttle / channel / payload shape as the legacy version. Cite
   `kill-switch` alignment.
2. **In the backend service** — fix the order-dependent heuristic in the
   snapshot write with a `reduce` over `timestamp`. Wrap the snapshot update
   in `try/catch` and keep the history-table write intact.
3. **In the frontend component** — read the actual Prisma `select` block,
   bind to the right field, preserve a fallback for any legacy data shape
   that co-exists in the same component.

A single plan covering all three is correct; splitting into per-span plans
loses atomicity (deploying only one of them masks the bug as "still broken"
or introduces a different inconsistency).

## Related references

- `references/prisma-and-mv-staleness.md` — three-tier staleness detection
  (schema, generated client, materialized views). Critical for any fix that
  touches `lastLat`/`lastLng` columns.
- `references/split-sql-dollar-quoted.md` — required when migrations use
  `$$..$$` PL/pgSQL bodies; the naive `split(';')` shreds them.
- `references/audit-to-plan-handoff.md` — applies to auditor's "do finding #N"
  handoff; same discipline of citing audit IDs in the fix plan applies.
