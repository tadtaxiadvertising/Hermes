# NestJS Exception Filter Chain — TAD DOOH 500 Debug Session (2026-07-15)

## The problem

`GET /api/v1/campaigns` returned:
```json
{"statusCode":500,"code":"INTERNAL_ERROR","message":"An unexpected error occurred","path":"/api/v1/campaigns"}
```

No error detail in response. Real error completely hidden.

## Root cause chain

1. `CampaignController.getAllCampaigns()` calls `CampaignService.getAllCampaigns()`
2. Service executes Prisma query (findMany with include)
3. Prisma throws `PrismaClientUnknownRequestError` (or similar)
4. `PrismaClientExceptionFilter` catches it — `@Catch(PrismaClientKnownRequestError | PrismaClientUnknownRequestError | PrismaClientValidationError | PrismaClientInitializationError)`
5. The `else` branch (for `UnknownRequestError` / `InitializationError`) only did `logger.error()` — did NOT set `message` or `errorCode` on the response object
6. Response defaults: `message = 'Error interno de base de datos.'`, `status = 500`, `errorCode = 'UNKNOWN'`
7. Then `GlobalExceptionFilter` sees `exception instanceof Error` (Prisma exceptions extend Error), but NOT `HttpException`, so it hits the `else` block and overwrites with its own defaults: `status = 500`, `code = 'INTERNAL_ERROR'`, `message = 'An unexpected error occurred'`
8. Client gets the opaque 500.

## The fix applied

In `apps/api/src/common/filters/prisma-exception.filter.ts` — `else` branch changed from:
```typescript
} else {
  this.logger.error(`Prisma Unhandled Error: ${exception.message}`);
}
```
to:
```typescript
} else {
  // PrismaClientUnknownRequestError, PrismaClientInitializationError
  this.logger.error(`Prisma Unknown/Initialization Error: ${exception.message}`);
  message = exception.message;
  errorCode = 'DB_ERROR';
}
```

## Key lesson

The `@Catch()` decorator catches the right exception types — but the `else` branch must ALSO propagate the message. A catch clause that logs but doesn't assign response fields silently falls through to the outer filter. Always ensure every branch of an exception filter sets `message`, `status`, and `errorCode` explicitly.

## Prisma client drift — related contributing factor

`prisma/client/schema.prisma` (generated, Jun 4) was 4 KB smaller than `prisma/schema.prisma` (source, Jul 13). The source schema had new fields (`scheduleDays`, `scheduleHours`, `frequencyCap` on Campaign; `processingStatus`, `validationError`, `weight` on MediaAsset) that the generated client lacked. This can cause `PrismaClientValidationError` ("Unknown argument") at runtime when the query references those fields.

Fix: `cd apps/api && npx prisma generate`

## Files changed (this session)

- `apps/api/src/common/filters/prisma-exception.filter.ts` — else branch now propagates exception.message + DB_ERROR code
- `apps/api/tsconfig.json` — `ignoreDeprecations: "6.0"` (for SWC binary unavailability on Windows/MSYS)
- `apps/advertiser/pages/api/proxy/[...path].ts` — new proxy route created
- `apps/advertiser/next.config.js` — added redirect `/api/v1/:path*` → `/api/proxy/:path*`

## Verification

```bash
cd apps/api && npx tsc --noEmit
# exit 0 — clean
```