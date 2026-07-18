# splitSqlStatements — Dollar-quoted-string-aware SQL splitter

## Problem

When a monorepo's backend initializes materialized views at startup via a `.sql` file
(e.g. `prisma/views.sql`), the file often contains PL/pgSQL function definitions:

```sql
CREATE OR REPLACE FUNCTION refresh_active_campaigns()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_active_campaigns;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'refresh_active_campaigns: fallback (%)', SQLERRM;
        REFRESH MATERIALIZED VIEW mv_active_campaigns;
END;
$$;
```

The naive `sql.split(';').map(q => q.trim()).filter(q => q.length > 0)` splits the
function body in half:

```
Fragment 1: "BEGIN\n    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_active_campaigns"
Fragment 2: "EXCEPTION"
Fragment 3: "WHEN OTHERS THEN\n        RAISE NOTICE..."
```

When `$executeRawUnsafe()` sends these fragments individually through PgBouncer
(Supabase's connection pooler on port 6543), Postgres returns:

- `ERROR: unterminated dollar-quoted string at or near "$$...REFRESH..."`
- `ERROR: syntax error at or near "EXCEPTION"`

## Root Cause

`$$` is a dollar-quoted string delimiter in PL/pgSQL — the content between the
first `$$` and the second `$$` is a string literal where `;` characters are NOT
statement boundaries. The splitter must track dollar-quote pairs.

## Fix: `splitSqlStatements()` TypeScript method

```typescript
/**
 * Divide SQL en statements individuales respetando bloques de código
 * PL/pgSQL delimitados por $$ (dollar-quoted strings). El split simple
 * por `;` rompe definiciones de función en medio.
 */
private splitSqlStatements(sql: string): string[] {
  const statements: string[] = [];
  let current = '';
  let dollarDepth = 0;
  for (let i = 0; i < sql.length; i++) {
    const c = sql[i];
    current += c;
    // Track dollar-quote depth: "$$" toggles inside/outside PL block
    if (c === '$' && i + 1 < sql.length && sql[i + 1] === '$') {
      dollarDepth++;
      i++;
      current += sql[i];
    } else if (c === ';' && dollarDepth % 2 === 0) {
      // Semicolon outside dollar-quoted block → statement boundary
      const trimmed = current.replace(/;\s*$/, '').trim();
      if (trimmed.length > 0) statements.push(trimmed + ';');
      current = '';
    }
  }
  const trimmed = current.trim();
  if (trimmed.length > 0) statements.push(trimmed);
  return statements;
}
```

### Usage in NestJS `onModuleInit`:

```typescript
private async initializeSreViews() {
  const viewsFile = path.resolve(process.cwd(), 'prisma/views.sql');
  if (!fs.existsSync(viewsFile)) return;

  const sql = fs.readFileSync(viewsFile, 'utf8');
  const statements = this.splitSqlStatements(sql);

  for (const query of statements) {
    await this.$executeRawUnsafe(query).catch(e => {
      if (!e.message.includes('already exists')) {
        this.logger.error(`Error SQL en vista: ${e.message}`);
      }
    });
  }
}
```

## Verification

- `tsc --noEmit` on the backend project: 0 errors
- `npm run build` (NestJS): exit 0
- Post-deploy startup log: `✅ Master Sync Views configuradas.` — no dollar-quoted errors

## Why NOT multi-statement (sending the whole file as one `$executeRaw`)

PgBouncer (Supabase Pooler, port 6543) does NOT support multi-statement queries in
simple query protocol — even sending the entire file as a single string fails.
Individual statements per `$executeRawUnsafe()` is the only PgBouncer-compatible path.

## Edge case: nested `$$` with custom tags

PL/pgSQL supports tagged dollar-quotes (`$func$`, `$body$`, etc.). The simple
depth tracker above works because `$$` appears exactly twice per function body
(on-site). If the SQL file uses tagged delimiters, extend the tracker to handle
them by matching the tag: `$tag$` ... `$tag$`.