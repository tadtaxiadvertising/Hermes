# Supabase Pooler & Management API Cheatsheet

Verified against `ltdcdhqixvbpdcitthqf` project, 2026-01-10 deploy session.

## Pooler connection string — correct syntax

```
postgresql://postgres.{PROJECT_REF}:{PASSWORD}@aws-0-{REGION}.pooler.supabase.com:6543/postgres?pgbouncer=true
```

Errors when wrong:

| Wrong | Error code | Why |
|-------|-----------|-----|
| `aws-0-us-east-1.pooler.supabase.com` (regional guess) | `28P01`/`XX000 timeout` | Region is project-specific; must match `.env` |
| `postgres.ltdcdhqixvbpdcitthqf` (with extra dot) | `XX000: tenant/user postgres.ltdcdhqixvbpdcitthqf.ltdcdhqixvbpdcitthqf not found` | Username must be `postgres.{ref}`, not `postgres` + `{ref}` |
| direct port 5432 with `sslmode=require` | `Connection terminated` | pg's `verify-full` default vs libpq semantics mismatch; not a fixable bug — use pooler |

## Management API endpoints

```
POST https://api.supabase.com/v1/projects/{ref}/database/query
Authorization: Bearer <Personal Access Token>
Content-Type: application/json
Body: { "query": "<raw SQL>" }
```

Success:
- `201 Created` with rows as JSON array on SELECT, `[]` on DML.
- `400 Bad Request` with `{ "message": "Failed to run sql query: ERROR: <pg_code>: <msg>" }`.

Auth failure:
- `401 Unauthorized` — token is from a different Supabase account.
- The `service_role` key (`sb_secret_...` or `eyJ...`) is **not** a valid Management API token. Use the **Personal Access Token** (`sbp_...` from https://supabase.com/dashboard/account/tokens).

## Reading what columns/tables actually exist

```sql
-- List tables
SELECT table_schema, table_name FROM information_schema.tables
WHERE table_schema='public' ORDER BY table_name;

-- List columns of one table
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema='public' AND table_name='<table>' ORDER BY ordinal_position;
```

This is the only reliable way to know the actual snake_case names when the Prisma schema uses camelCase.

## pg_constraint vs pg_indexes

```sql
SELECT conname FROM pg_constraint WHERE conname = '<expected>';
SELECT indexname FROM pg_indexes  WHERE indexname = '<expected>';
```

`CREATE UNIQUE INDEX` populates `pg_indexes`. `ALTER TABLE ... ADD CONSTRAINT ... UNIQUE` populates `pg_constraint`. To align with what Prisma migrations use, convert via:

```sql
ALTER TABLE "<tbl>" ADD CONSTRAINT "<name>" UNIQUE USING INDEX "<existing_index_name>";
```

## Idempotent dedupe-before-unique

```sql
WITH duplicated AS (
  SELECT ctid,
    ROW_NUMBER() OVER (PARTITION BY "<pk1>", "<pk2>" ORDER BY ctid) AS rn
  FROM "<tbl>"
)
DELETE FROM "<tbl>"
WHERE ctid IN (SELECT ctid FROM duplicated WHERE rn > 1);
```

`ORDER BY ctid` keeps the **lowest ctid** (= oldest row in the heap) — desirable for telemetry.
