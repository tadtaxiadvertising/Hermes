# Prisma + Postgres Staleness Audit Reference

Companion to `read-only-code-audit` Step 2d. Three repeatable failure classes
found in Prisma-backed monorepos. Each section: symptom → command to confirm
→ minimum fix at the right layer.

These are the **highest-yield backend findings** the type checker surfaces
cheaply. Run the three checks up front, before sampling business logic.

---

## 1. Type checker as Prisma client-staleness detector

`tsc --noEmit` is the only line that catches "model added to schema but client
never regenerated". Three symptoms smell like this:

| Symptom (from `tsc --noEmit`) | Root cause | Layer |
|---|---|---|
| `TS2339: Property '<Model>' does not exist on type 'PrismaService'` | Code references a model in `schema.prisma` whose generated client was never refreshed. **Runtime: `undefined.X is not a function`.** | `npx prisma generate` |
| `TS2353: Object literal may only specify known properties, and '<Field>' does not exist in type '...WhereInput' / '...CreateInput'` | Field renamed/dropped in schema but generated `index.d.ts` (the inputs section) still old. Common when the field was added later and a service used it to query directly. | `npx prisma generate` after confirming schema reflects intent |
| `TS2339` on a `@relation` field, OR `Property 'select' is missing in type` on a raw select | Schema relations moved; client types stale. | `npx prisma generate` |

**The `npx prisma generate` flag.** The default output directory is
`node_modules/.prisma/client`. If a project committed a `prisma/client/` (or
`apps/api/prisma/client/`) directory, the generator may have been redirected
there — check for an `output = "..."` directive in the generator block. A
committed `prisma/client/` directory is itself a generated-artifact hygiene
finding (covered in `read-only-code-audit` Step 2b). Fix the output directive
**and** the tracked tree, **and** the generate command, in that order.

**Trap to avoid:** recommending "rewrite the code to use the new model name"
when the issue is just `prisma generate`. The smallest fix at the most
upstream layer is the answer; do not prescribe code changes when codegen is.

**One-command triage:**

```bash
# Backend in apps/api/, frontend passed type-check.
cd apps/api && node_modules/.bin/tsc -p tsconfig.json --noEmit 2>&1 | head -80
# Group TS2339 by missing property — that's your real-world client staleness list.
```

---

## 2. `ON CONFLICT` and `skipDuplicates` without a UNIQUE constraint

Postgres requires the target of `ON CONFLICT (...)` to match an existing
**unique index or unique constraint**. Prisma's `createMany({ skipDuplicates: true })`
delegates to the same `ON CONFLICT` machinery. If the schema doesn't declare
the matching `@@unique(...)`, **the statement throws** with:

```
ERROR: there is no unique or exclusion constraint matching the ON CONFLICT specification
```

(or `skipDuplicates` becomes a silent no-op in some Prisma versions — the
duplicates are written anyway). Both behaviors are bad. Pattern:

```ts
// file: services/telemetry/telemetry.service.ts
await prisma.$executeRawUnsafe(
  `INSERT INTO telemetry (driver_id, coords, speed, timestamp)
   VALUES ${values.join(', ')}
   ON CONFLICT (driver_id, timestamp) DO NOTHING`,   // ← references UNIQUE the schema does NOT have
  ...params,
);
```

**Fix is at SCHEMA layer, not code layer.** Add:

```prisma
model Telemetry {
  id        String   @id @default(uuid())
  driverId  String   @map("driver_id")
  // ... other fields ...
  coords    Unsupported("geography(Point, 4326)")

  @@unique([driverId, timestamp])   // ← enables ON CONFLICT (driver_id, timestamp)
  @@index([driverId])
  @@map("telemetry")
}
```

**Pre-migration safety net.** Existing duplicate rows will fail the
`@@unique` migration in Postgres. Run a dedupe script first:

```sql
-- Run before the migration lands in any environment.
DELETE FROM telemetry a
USING telemetry b
WHERE a.id < b.id
  AND a.driver_id = b.driver_id
  AND a.timestamp = b.timestamp;
```

(or via a one-off `apps/api/scripts/dedupe-telemetry.ts` in Prisma).
The general rule: **never ship a `@@unique` migration onto a table that may
already contain duplicates** — it will fail at `prisma migrate deploy` and
leave the production DB half-migrated. Surface this in the FASE 2 plan,
do not let it become an ex-post surprise.

---

## 3. Two `.sql` files, one materialized view

The fast-fail signal:

```bash
find . -path "*/node_modules" -prune -o -name "*.sql" -print \
  | xargs grep -l "MATERIALIZED VIEW" 2>/dev/null
```

Two files defining `mv_active_campaigns` (or similar canonical name) means
_two sources of truth_ for the same DB object. Whichever file ran last wins.
Subtle drift:

| Tell | Risk |
|---|---|
| Different SELECT column lists | Queries rely on a column that only one definition has → silent empty result in the other env |
| One file `DROP IF EXISTS` + `CREATE`, the other `CREATE IF NOT EXISTS` only | Running the IF-NOT-EXISTS one in an env whose table has columns the live code relies on → breakage |
| One file declares GIN indexes on `jsonb` arrays, the other doesn't | `WHERE assigned_device_uuids @> ...` becomes a seq scan |
| `REFRESH MATERIALIZED VIEW CONCURRENTLY` in one, plain `REFRESH` in the other | Concurrent needs `UNIQUE INDEX` on the leading column; without it the refresh takes an `ACCESS EXCLUSIVE` lock and stalls traffic |

**Consolidation recipe:**

1. Pick the canonical `.sql` (whichever has the full column list + GIN
   indexes + concurrent refresh helper function). Confirm by file mtime +
   git log: the one that's been edited more recently is usually right.
2. Open the runner script (or `package.json` `scripts.migrate`) and force
   it to the canonical file. If both filenames are referenced, redirect
   one to a deprecation comment or delete it.
3. Make sure the canonical file starts with `DROP MATERIALIZED VIEW IF EXISTS <name>;`
   so re-runs are idempotent on environments that already have the older
   version materialized.
4. Search the codebase for calls to refresh functions
   (`refresh_active_campaigns`, etc.) — they should reference the canonical
   helper, not a parallel one in the dead file.

---

## 4. Quick-triage script (paste into terminal)

```bash
# Run from repo root. ~10 seconds. Outputs the most common staleness tells.
echo "=== Prisma models referenced by code ==="
git grep -hE "prisma\.[a-zA-Z]+" -- 'apps/api/src/**/*.ts' 2>/dev/null \
  | sed -E 's/.*prisma\.([a-zA-Z]+).*/\1/' | sort -u > /tmp/used_models.txt
echo "=== Prisma models declared in schema ==="
grep -oE "^model [A-Z][a-zA-Z]+" apps/api/prisma/schema.prisma \
  | awk '{print $2}' | sort -u > /tmp/declared_models.txt
echo "=== Models referenced but not declared (🔴) ==="
comm -23 /tmp/used_models.txt /tmp/declared_models.txt

echo
echo "=== ON CONFLICT columns vs UNIQUE indexes ==="
# Try to keep this lean; if it grows into many lines, read line by line.
git grep -nE "ON CONFLICT \(" -- 'apps/api/**/*.ts' 2>/dev/null
git grep -nE "@@unique\(" apps/api/prisma/schema.prisma 2>/dev/null

echo
echo "=== Duplicate materialized-view definitions ==="
find . -path "*/node_modules" -prune -o -name "*.sql" -print \
  | xargs grep -lE "MATERIALIZED VIEW" 2>/dev/null

echo
echo "=== ts --noEmit (backend) ==="
cd apps/api && node_modules/.bin/tsc -p tsconfig.json --noEmit 2>&1 | head -30
```

This run is the cheapest way to start any Prisma-heavy audit. If it returns
nothing actionable, you have ruled out the three highest-yield backend
failure classes in one shot. Spend the rest of the session on business rules
and naming drift instead.

---

## 5. What NOT to do (these are signs of a bad audit)

- ❌ Suggest "wrap the SQL call in a try/catch and log the error" — that
  masks the root cause (missing UNIQUE index). The right fix is upstream.
- ❌ Recommend Prisma model renames when the symptom is a stale generated
  client. Verify with `node_modules/.prisma/client/index.d.ts` exists and
  has the field before asking the user to change the schema.
- ❌ Treat `tsc` warnings as noise because the repo has
  `ignoreBuildErrors: true` set on the **frontend**. The **backend**'s
  `tsconfig.json` may have `strictNullChecks: false` but still catches
  Prisma client staleness. Always re-check the actual backend config.
- ❌ Conclude "Prisma is fine" without running the type checker. Many
  staleness issues pass unit tests because the tests use a different query
  shape than production. `tsc` is the only thing that exercises the input
  shapes uniformly.
