---
generated_at: 2026-07-15
context: TAD DOOH production incident — 500 Internal Server Error on GET /api/v1/campaigns
---

# Prisma Client Generation Drift — Server-Side Session Evidence

## Incident summary

- **Service:** `tad-api` (NestJS)
- **Endpoint:** `GET /api/v1/campaigns`
- **Symptom:** 500 Internal Server Error from backend on campaign list
- **Root cause:** Prisma client in production was generated against an **older schema** at runtime. Controller `include` references to relations/fields that don't exist in the stale client → Prisma throws `PrismaClientValidationError` at query planning time (not DB execution time) → caught by `PrismaClientExceptionFilter` → 500.
- **Fix applied:** `cd apps/api && npx prisma generate` to regenerate client against the committed source schema. EasyPanel must rebuild the API container after pushing the regenerated client.

## Drift evidence (client vs source schema)

Source `apps/api/prisma/schema.prisma` (latest migrations applied 2026-07-13) had these but the generated client (from 2026-06-28 build) lacked:

**Campaign model additions:**
- `hasSeenTutorial Boolean @default(false) @map("has_seen_tutorial")`
- `scheduleDays String? @default("[]") @map("schedule_days")`
- `scheduleHours String? @default("[]") @map("schedule_hours")`
- `frequencyCap Int @default(0) @map("frequency_cap")`

**MediaAsset model additions:**
- `processingStatus String @default("ACTIVE") @map("processing_status")`
- `validationError String? @map("validation_error")`
- `weight Int @default(1) @map("weight")`

**Responsible migration:** `20260628_add_schedule_and_weight_fields`

## Exact commands for future detection

```bash
# Compare line counts (drift = different line counts)
wc -l apps/api/prisma/client/schema.prisma apps/api/prisma/schema.prisma

# Or full diff
diff apps/api/prisma/client/schema.prisma apps/api/prisma/schema.prisma

# Quick field-staleness check (false = client is stale)
grep 'scheduleDays' apps/api/prisma/client/schema.prisma apps/api/prisma/schema.prisma

# Regenerate client from correct schema-owning app directory
cd apps/api && npx prisma generate
```

## Key code references

- **Schema source:** `apps/api/prisma/schema.prisma`
- **Generated client:** `apps/api/prisma/client/schema.prisma` (hoisted to monorepo root `node_modules/@prisma/client`)
- **Exception filter:** `apps/api/src/common/filters/prisma-exception.filter.ts` — converts all Prisma client errors to 500 and logs the error code
- **Campaign controller:** `apps/api/src/modules/campaign/campaign.controller.ts` — `include: { mediaAssets: { select: mediaAssetSafeSelect } }`
- **Fix command:** `cd apps/api && npx prisma generate`

## Diagnostic protocol for future 500s on GET endpoints in tad-api

1. Check NestJS logs first: `PrismaClientValidationError` = stale client; `PrismaClientKnownRequestError` = DB-level failure (P2002 / P2025).
2. If validation error: diff `prisma/schema.prisma` vs `prisma/client/schema.prisma`. Any `<` lines in diff = fields in source not in client = stale client.
3. Regenerate with `npx prisma generate` **from `apps/api/`**, NOT monorepo root (schema resolution depends on cwd).
4. Commit regenerated client + source schema together, then rebuild API container in EasyPanel.

## EasyPanel rebuild note

EasyPanel "Restart" alone won't pick up a regenerated Prisma client unless it was baked into the image during build. Use EasyPanel's **Deploy/Rebuild** (not just restart) after pushing the regenerated client to the repo.
