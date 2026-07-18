---
name: prisma-schema-migrations
description: "Deploy Prisma schema changes to a managed Postgres (Supabase, Neon, RDS) from a Windows or Linux Node host without psql installed. Handles pooler URL quirks, snake_case column discovery, dedupe-before-unique dedupe pattern, and aligning repo migration conname with live pg_catalog state via ALTER INDEX ... RENAME + USING INDEX."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [prisma, migrations, supabase, postgres, schema, deploy, dedupe, unique-constraint, snake-case, pooler, management-api]
    related_skills: [read-only-code-audit, systematic-debugging, spike]
prerequisites:
  packages: ["pg"]
---

# Prisma Schema Migrations Without psql

Deploy Prisma migrations to a managed Postgres database (Supabase, Neon, RDS, etc.) from a host that **does not have `psql` installed** — typically a Windows dev box or a container that only ships Node. Reuses the project's existing `pg` Node module (it ships as a dependency of `@nestjs/core` and `@prisma/client` apps).

## When to Use

- User says "apply these migrations to my Supabase/Neon/Postgres" and the host has no psql.
- A Prisma `@@unique` was added to `schema.prisma` but the live DB still rejects `ON CONFLICT DO NOTHING`.
- New schema entities need UNIQUE indices that did not exist at production deploy time.
- Two repo migration SQLs reference different names than what `pg_indexes` / `pg_constraint` show in the live DB.

## Do NOT Use

- Local dev DB (use `npx prisma migrate dev`).
- If `psql` IS available on the host — that's always faster and produces output the user can read.
- For schema changes that Prisma CLI itself can push (`npx prisma db push` works on a fresh project).

## Core technique: Management API for raw SQL

The Supabase Management API exposes `POST /v1/projects/{ref}/database/query` which accepts `{ query: "..." }` and returns JSON. Authenticate with a **Personal Access Token** (https://supabase.com/dashboard/account/tokens), NOT the service_role key — the API rejects service_role tokens.

```js
const res = await fetch(`https://api.supabase.com/v1/projects/${ref}/database/query`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${PAT}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ query: sql }),
});
// 201 = success, 400 = SQL error, 401/403 = token bad
```

This works even when the project has no Supabase CLI installed. Returns the rows as JSON for SELECTs, empty `[]` for INSERT/UPDATE/DELETE.

## The 6 repos real-world pitfalls

These came up *in production* during a v12.1.3 schema migration on TAD DOOH. Each would have silently broken the deploy without a skill to flag them.

### Pitfall 1: snake_case column names vs PascalCase Prisma model names

**Symptom**: SQL `42P01 relation "Telemetry" does not exist` or `42703 column "driverId" does not exist`.

**Cause**: Prisma models are PascalCase and field names are camelCase, BUT live Postgres tables are typically `snake_case` mapped via `@@map("snake_name")` and `@map("field_name")`. Quoted identifiers create case-sensitive lookup; unquoted are folded to lowercase.

**Fix**: Use the *actual* DB column names. Discover them first:

```sql
SELECT table_schema, table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;

SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'telemetry' ORDER BY ordinal_position;
```

**Rule of thumb**: read the existing repo migration SQL files — they will already use snake_case because Prisma migrations ship with what actually deploys to the DB. Match those names.

### Pitfall 2: CTID-based dedupe before UNIQUE — and ordering

**Symptom**: `CREATE UNIQUE INDEX` fails with `could not create unique index` because of existing duplicates.

**Fix**: Dedupe first using `WITH duplicated AS (..., ROW_NUMBER() OVER (...))` — keep ONLY the lowest `ctid` per partition:

```sql
WITH duplicated AS (
  SELECT ctid,
    ROW_NUMBER() OVER (PARTITION BY "driver_id", "timestamp" ORDER BY ctid) AS rn
  FROM telemetry
)
DELETE FROM telemetry
WHERE ctid IN (SELECT ctid FROM duplicated WHERE rn > 1);

CREATE UNIQUE INDEX ... ON telemetry ("driver_id", "timestamp");
```

`ORDER BY ctid ASC` (default) keeps the **oldest** row per group — usually what you want for telemetry playback data.

### Pitfall 3: `ALTER TABLE ADD CONSTRAINT` is not index backfilled

**Symptom**: After running the dedupe + `CREATE UNIQUE INDEX`, `pg_constraint` shows nothing (`SELECT FROM pg_constraint WHERE conname = '...'`) but `pg_indexes` shows the index.

**Cause**: `CREATE UNIQUE INDEX` and `ALTER TABLE ... ADD CONSTRAINT ... UNIQUE` are functionally equivalent for enforcing uniqueness but populate different system catalogs. Repo migrations often use `ADD CONSTRAINT` (PR-friendly, atomic), but ad-hoc deployments use `CREATE INDEX` (no transaction lock, faster).

**Fix when you need them to match the repo**: convert index → constraint:

```sql
ALTER TABLE telemetry
  DROP CONSTRAINT IF EXISTS telemetry_driver_timestamp_unique;
ALTER TABLE telemetry
  ADD CONSTRAINT telemetry_driver_timestamp_unique
  UNIQUE USING INDEX "telemetry_driver_timestamp_unique";
```

To rename the index first (if you created it under a different conname):

```sql
ALTER INDEX IF EXISTS "telemetry_driverId_timestamp_key"
  RENAME TO "telemetry_driver_timestamp_unique";
```

**Verify**: `SELECT conname FROM pg_constraint WHERE conname = '<expected>'` returns the row — what the Prisma client expects at runtime.

### Pitfall 4: Pooler hostname is regional and username format has a dot

**Symptom**: Direct connection timeout, or pooler returns `XX000: tenant/user postgres.ltdcdhqixvbpdcitthqf not found`.

**Correct pooler URL**:

```
postgresql://postgres.{PROJECT_REF}:{PASSWORD}@aws-0-{REGION}.pooler.supabase.com:6543/postgres?pgbouncer=true
```

- Region is **project-specific** (`us-east-1`, `us-west-2`, etc. — read it from `.env`, not from generic examples).
- Username = `postgres.{project_ref}` (with a literal dot, not the project ref alone).
- `?pgbouncer=true` enables transaction-mode pooling.
- Port 6543 is pooler-only; port 5432 direct may have certificate validation that fails on `pg`'s default `sslmode`.

**Always probe connection first**:

```js
const pool = new Pool({ connectionString, max: 1, connectionTimeoutMillis: 15000 });
const client = await pool.connect();
await client.query('SELECT version()');
```

If this succeeds, you have the right URL. If it returns `28P01 password authentication failed`, the password is wrong (different from what user claims). If TCP timeout, the host is wrong (likely region).

### Pitfall 5: pg-Bouncer transaction mode requires explicit BEGIN/COMMIT for ALTER TABLE

**Symptom**: `ALTER TABLE ... ADD CONSTRAINT` hangs or fails with implicit transaction error.

**Cause**: Pooler's transaction mode does not allow implicit transactions for DDL.

**Fix**:
```js
await client.query('BEGIN');
await client.query(`ALTER TABLE ...`);
await client.query('COMMIT');
// Catch 42P07 (duplicate_object) for idempotency
```

### Pitfall 6: 400 Bad Request body shape

**Symptom**: Management API returns 400 "missing query field" with no detail.

**Cause**: Send `{ query: "..." }` as a JSON body, NOT as raw SQL or as query-string.

```js
body: JSON.stringify({ query: sql })  // correct
// NOT:
body: sql                           // wrong, will be stringified to "..." 
body: `query=${encodeURIComponent(sql)}` // wrong, endpoint is POST with JSON body
```

## Pitfall 7: Generated client drift vs live DB / runtime `PrismaClientValidationError`

**Symptom**: `500 INTERNAL_ERROR` with generic message, even though the DB column exists and the query looks correct.

**Cause**: A Prisma migration was applied to production, but `prisma generate` was never re-run in the deploy pipeline (or was run in a different workspace). The generated client at `prisma/client/` still maps an *older* schema. At runtime, Prisma validates the query shape against the generated client — not the live DB — and throws `PrismaClientValidationError` for fields/relations that exist in DB but are absent from the stale client.

**Common triggers**:
- New scalar columns added by migration (e.g., `schedule_days`, `frequency_cap`) but missing from generated client.
- New relation fields (e.g., `processingStatus` on `MediaAsset`) used in `include` / `select`.
- A teammate ran `prisma migrate dev` locally without committing the regenerated client.

**Local repro**:
```bash
cd apps/api && npx prisma generate
npx tsc --noEmit
```

**Production fix**: Rebuild the API service so `prisma generate` runs inside the container before Nest starts. Do **not** try to patch queries to avoid the missing fields — that shadows the real schema and accumulates tech debt.

**Diagnostic shortcut**: if a Nest `GlobalExceptionFilter` is returning `{"code":"INTERNAL_ERROR","message":"An unexpected error occurred"}` for every DB endpoint, the root cause is likely one of:
1. Stale Prisma client (Pitfall 7).
2. A stale `views.sql` that overwrites a materialized view with an older column set on every cold start (Pitfall 8 below).

## Pitfall 8: `views.sql` drift vs applied migrations for materialized views

**Symptom**: Backend boots fine, but `GET /api/v1/campaigns` (or any endpoint that touches `mv_active_campaigns`) returns 500 with `INTERNAL_ERROR`. Nest logs may show nothing useful.

**Cause**: The app's `onModuleInit` reads `prisma/views.sql` and **drops + recreates** the materialized view on every cold start. If a migration added columns to `campaigns` / `media_assets` and `views.sql` was never updated, the recreated view lacks those columns. Queries that project or filter on the new columns then fail at the DB layer, bubbling up as an unhandled Prisma error caught by the global filter.

**Fix**:
1. Update `prisma/views.sql` so it matches the **latest migration** that touched the MV definition.
2. Rebuild the API service so the new SQL file is baked into the image.
3. For robustness, keep the `DROP ... IF EXISTS` + `CREATE MATERIALIZED VIEW` idempotent pattern (already present); the real protection is **source-of-truth alignment**, not idempotency alone.

**Verification**:
```sql
-- After deploy / restart, confirm the MV exposes the expected columns:
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'mv_active_campaigns'
ORDER BY ordinal_position;
```

**Rule**: whenever a migration alters tables referenced by `mv_active_campaigns`, update `prisma/views.sql` in the *same PR*.

## Statically re-runnable scripts

The umbrella ships one runnable script under `scripts/` that handles all 6 pitfalls in canonical order:

- `scripts/apply-prisma-unique-migration.js` — discover schema, dedupe via ctid, create UNIQUE INDEX, convert to CONSTRAINT so `pg_constraint` matches the repo migration conname, then verify in both `pg_indexes` and `pg_constraint`. Copy to repo root, fill the 3-field HEADER (`SUPABASE_URL`, `PAT`, `TABLE_QUAL`) and run with `node script.js`.

## Quick reference doc

- `references/pooler-management-api.md` — pooler URL syntax (regional hostname, `postgres.{ref}` user), Management API request shape, valid-vs-invalid auth tokens, and the `pg_constraint` vs `pg_indexes` distinction.

## Quick-start template

```js
const SUPABASE_URL = 'https://api.supabase.com/v1/projects/YOUR_REF';
const PAT = 'sbp_...';  // Personal Access Token, not service_role

async function exec(sql, label) {
  const res = await fetch(`${SUPABASE_URL}/database/query`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${PAT}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: sql }),
  });
  if (!res.ok) {
    const err = await res.text();
    console.error(`${label} → HTTP ${res.status}: ${err}`);
    return false;
  }
  console.log(`${label} → OK`);
  return true;
}

await exec(`
  -- Step 1: discover schema
  SELECT table_name FROM information_schema.tables WHERE table_schema='public';
`, 'discover');
```

## Verification always includes

1. **Verify creations in `pg_constraint` (after ALIGN) or `pg_indexes` (after index-only)**:

   ```sql
   SELECT conname FROM pg_constraint
   WHERE conname IN ('expected_conname_1', 'expected_conname_2');
   ```

2. **Remove the temporary script from `apps/api/`** after deploy — never commit a one-off `run_migrations.js` or `align_names.js`. Use Git cleanups or `.gitignore` patterns if these must live somewhere.

3. **Run repo's own `tsc --noEmit` and `prisma validate`** on the source tree once you return — the deploy does not affect local TS state.

## Notes on Windows-git-bash env

- The project's package scripts run via bash on Windows (not PowerShell). Use POSIX syntax (`&&`, `|`, `$ENV`).
- Long shell commands with quoted paths and embedded `${...}` may exceed `terminal`'s path-token limit. For those, write a temporary `.js` to `apps/api/` and execute via `node` directly — DO NOT pass `--env-file` to npm on Windows (CJS resolution path issues).
- For destructive operations (DROP / DELETE), always wrap in `BEGIN`/`COMMIT` and add an **`;` separator between CTAS (DELETE+CREATE)** — pg-bouncer aggressively batches statements.

---

## Phase-1 evidence: read-only Prisma diagnostic script (no `psql`)

A different use case than deploying migrations: **investigating an existing live-DB bug**. When a `404 Not Found` / `P2025` / FK violation references a row that "should" exist, you need evidence from the live DB before you can fix anything. This is a debugging-tool layered on top of the same "no psql available" constraint.

### When to use (vs the migration section above)

- You're investigating a runtime error, not deploying a schema change.
- The bug is data-shape related ("why does this query find nothing?", "are these rows really missing?").
- The repo already has `@prisma/client` installed — typical Next/Nest monorepo.
- Reach for it as Phase 1 of `systematic-debugging` BEFORE proposing a fix.

### Pattern (one-shot `.cjs` script)

Read `DATABASE_URL` by parsing the existing `.env` directly — `dotenv` adds a transitive dep for a one-shot use:

```js
// apps/api/scripts/probe-evidence.cjs
const { PrismaClient } = require('@prisma/client');
const fs = require('fs');
const path = require('path');

// Load DATABASE_URL from local .env without dotenv.
const envContent = fs.readFileSync(
  path.join(__dirname, '..', '.env'),
  'utf8'
);
for (const line of envContent.split('\n')) {
  const m = line.match(/^DATABASE_URL\s*=\s*"?([^"\n]+)"?/);
  if (m) { process.env.DATABASE_URL = m[1]; break; }
}
if (!process.env.DATABASE_URL) {
  console.error('ERROR: DATABASE_URL missing'); process.exit(1);
}

async function main() {
  const prisma = new PrismaClient();
  try {
    // Select bare-minimum columns. Use `.limit()` if the table can be large.
    const rows = await prisma.device.findMany({
      select: { id: true, deviceId: true, lastSeen: true, status: true },
      orderBy: { lastSeen: 'desc' },
    });
    console.log(`Total: ${rows.length}`);
    for (const r of rows) console.log(JSON.stringify(r));
  } finally {
    await prisma.$disconnect();
  }
}
main();
```

Run from repo root (where `node_modules/@prisma/client` is hoisted):

```bash
node apps/api/scripts/probe-evidence.cjs
```

### Cleanup discipline

**Delete the script the same turn, before any commit.** A diagnostic script is evidence tool, not a repo asset. Leaving it pushes dead code and pollutes `git status` long-term. Compare with the migration rule above (don't commit `run_migrations.js`) — same principle, different use case.

```bash
rm apps/api/scripts/probe-evidence.cjs
```

### Safety rules specific to diagnostic mode

- **Read-only.** This script never `INSERT/UPDATE/DELETE`s from production. If you need a mutation to prove a theory, do it through the actual API endpoint or wrap in a transactional `BEGIN`/`ROLLBACK` you can abort.
- **`console.log` large tables hang the script and may exhaust the pool.** Always add `.limit(N)` and select only the columns you need.
- **Never echo the URL itself.** If Prisma warns about the URL on a connection failure, scrub the query for the `DATABASE_URL` substring first.
- **Run `root -> apps` not `apps -> root`.** In a workspace monorepo, the nested `apps/api/node_modules/@prisma/client` may not exist after a partial install. The hoisted root `node_modules` always has it. Use `node <relative-path>` from the repo root, not `cd apps/api && node scripts/...`.
- **On Windows + OneDrive:** file system writes serialize through Microsoft's sync layer, so remove the file BEFORE any background sync can create a `.tmp` clobber.

### Filtering the output (bash one-liner)

```bash
node apps/api/scripts/probe-evidence.cjs 2>&1 | grep -E "deviceId|lastSeen" | head -50
```

For large investigations, run `node ... > probe.out.txt`, then `grep`/`head`/`wc` afterwards — saves re-running the query.

### Connection to systematic-debugging

This is Phase 1 evidence collection per the `systematic-debugging` skill — never the fix. After gathering rows, return to:
1. List a ranked hypothesis set per Phase 3.
2. Test with the smallest possible probe, NOT another big `findMany`.
3. Apply the actual fix (often a code change in the wrong caller, NOT a schema/migration change).
4. Write a regression test.

### Alternative: Supabase Management API for read-only queries

If the project has `@supabase/supabase-js` already (most TAD-style repos do), calling POSTGREST via Management API gives JSON you can pipe straight to `jq` without a script file. See the [references/pooler-management-api.md](references/pooler-management-api.md) file for the auth header shape. Trade-off: slower (HTTP round-trip vs Prisma's connection-reuse) but produces zero on-disk artifacts to clean up.
